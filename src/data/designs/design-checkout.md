# Design Amazon Checkout — Multi-Service Order Orchestration

## The question

> *"Design checkout for Amazon. A customer has things in a cart, hits Place Order, and at some point a box shows up at their door. Design everything between those two moments."*

**The product.** A customer has been adding things to a cart, possibly for weeks, across a phone and a laptop. When they decide to buy, they pick an address, pick a shipping speed, pick a card, look at a total, and press one button. What they expect after that is a confirmation with an order number, a delivery date they can plan around, a charge that matches the number they were shown, and the ability to change their mind — for a while. What they must never get is a charge for something that never arrives, a second charge because they pressed the button twice, or a total that turns out to be different from the one on the screen.

**What a working system delivers**

- The order number appears fast enough that nobody presses the button twice — and if they do, they still get one order.
- The amount on the card is the amount that was on the screen, even if the price changed while they were choosing an address.
- "Cancel" works right up until someone in a warehouse physically picks the item off a shelf, and then says so honestly instead of pretending.
- When the last one on the shelf turns out to be broken, the money comes back without the customer having to ask.
- The delivery date shown at checkout is the date the box actually arrives.

**Why this gets asked.** Everything before this moment — search, ranking, the product page — is a read problem that a cache solves. Place Order is the one write in the entire product, it has to land in several systems that don't share a database, and the last of those systems is a building full of people and robots that will not participate in your rollback.

---

**Archetype:** multi-service order orchestration — one user action committed across inventory, payment, and a warehouse, where the final step is physical and cannot be undone.
**Cousins that reuse ~70% of this page:** Shopify and every hosted checkout, Instacart and DoorDash order placement, Wayfair, grocery delivery, Apple Store pickup, and — with the parts renamed — any travel booking that has to hold a flight, a hotel, and a car at once.

**What's actually being graded:** whether you notice that **there is no transaction available here, and stop looking for one.** Inventory is sharded by SKU, orders by customer, payment lives at a third party, and fulfilment is a warehouse. No two of those share a commit. The candidates who struggle reach for a distributed transaction, discover it doesn't reach the warehouse, and then hand-wave. The answer is to **order the steps by how expensive they are to undo, commit at the one point where you own all the state, and make everything after that at-least-once with a compensation that is an apology rather than a rollback.**

**The admission that scores highest:** *cancellation is a race you can lose, and you should say so on the button.* Somewhere around thirty minutes after the order is placed, a human or a robot picks the item off a shelf, and from that instant "cancel" is not a cancel — it's a return, and it costs the reverse-logistics price of the object. A design that models cancellation as deleting a row has not noticed that the physical world already started.

**The contrast to have ready:** *Ticketmaster is this problem with the inventory made impossible and the fulfilment made free — sixty thousand non-fungible seats, a hundred and sixty-six people per seat, and a PDF at the end. Amazon is the exact inverse. Its §15 says outright that fungible inventory turns its hardest section into a `DECR`, and that's true: inventory here is a counter with contention near one. What replaces it is that the last step is a box on a truck. Ticketmaster can un-issue a ticket; nobody can un-ship a box.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "This is an orchestration problem, not a scale problem, and the numbers say so — thirteen million orders a day is about a hundred and fifty writes a second, which one database could do. What makes it hard is that Place Order has to land in **four systems that share no transaction**: inventory sharded by SKU, orders sharded by customer, a payment processor I don't own, and a warehouse, which is a building. So my plan is to **order the steps by how expensive they are to undo** — reserve inventory, authorize the card, then commit the order, which is my one atomic point, and only then hand it to fulfilment through an outbox. Money is authorized at Place Order and **captured when the box ships**, which is often days later, and that gap is a design problem of its own. I want to go deep on the saga and its compensations, and on authorize-versus-capture. I'll treat which warehouse serves the order, how a cart splits into shipments, search, and the recommendation surfaces as named subsystems and leave them out."

**Why open this way:** it kills the scale question in one sentence with an actual number, which buys you the whole hour for correctness. It names the four-way split, which is the insight the problem exists to test. And it pre-commits two dives you can hold for ten minutes each, before you have drawn a box.

---

## 1 · Functional requirements

1. **Place an order** — turn a cart plus an address, a shipping choice, and a payment method into a durable order, reserving stock and authorizing payment, exactly once no matter how many times the button is pressed.
2. **Honour the quoted total** — the amount charged is the amount displayed, including price, promotions, shipping, and tax, and it does not move underneath the customer while they check out.
3. **Take the order to a terminal state** — ship it and capture the money, or cancel it and release everything, with a defined point after which cancellation is no longer free and the customer is told.

Requirement 1 contains the word *exactly*, which makes it a correctness invariant wearing a feature costume. State it as a requirement anyway; every later decision gets justified against it.

**Out of scope (say them):** browse, search, ranking, and recommendations — that's the read side of the product and it shares nothing with this page but a SKU id; **which fulfilment centre serves an order and how a cart splits into shipments and packages** — that's a real optimization problem with its own page; carrier selection and route planning; returns and reverse logistics beyond the point where a cancel becomes a return; fraud scoring, which is a model and a queue that this flow calls and blocks on; tax *calculation*, which is a vendor (Vertex, Avalara) and a filing obligation; digital goods and subscriptions (see §15); and the payment processor's own internals — **that's its own page, and it's the inverse of this one.**

**Below the line, likely follow-ups:** gift cards and split tender across two payment instruments, promotional and coupon stacking rules, address validation and correction, buy-now-pay-later, backorders and preorders, one-click ordering, and multi-currency.

**Why the out-of-scope list is worth a full minute here:** an interviewer who says "design Amazon" and gets a lecture on search ranking has learned nothing. Naming browse and fulfilment optimization as things you *considered and cut* is what turns "checkout" from a suspiciously small problem into a deliberate one.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Order durability** | **Zero acknowledged orders lost.** Once an order id is returned, the order exists and will reach a terminal state | The one guarantee with no degraded mode. A customer holding a confirmation number for an order that isn't in the system is unrecoverable — they have no way to retry and no way to prove it |
| **Exactly-once placement** | **Zero duplicate orders** from client retries, double-clicks, or a second tab — enforced by a key derived from the checkout session, not by client discipline | At p99 800 ms on a submit button, some fraction of customers *will* click twice. Duplicate orders are the single most visible failure of a checkout and every one of them is a refund, a return label, and a contact |
| **Place Order latency** | **p50 ≤ 300 ms, p99 ≤ 800 ms** | A payment authorization is 200–500 ms of that and it's a third party. Above ~1 s the double-click rate rises sharply, which is the same requirement as the row above, seen from the other end |
| **Price integrity** | **100% — the total charged equals the total quoted.** Quote TTL **15 minutes**, re-quoted on the review page | Not a reliability target, a legal and trust one. If the two ever differ we eat the difference; §8 is the mechanism that makes that cheap rather than routine |
| **Oversell rate** | **≤2 per 10,000 order lines**, measured continuously, with an owned compensation path | *Assumption, and a product choice.* Zero oversell means holding stock pessimistically for every add-to-cart, which strands inventory and costs more than the apologies do. **The target is a number, not zero, and having a number is the point** |
| **Charged but not shipped** | **≤1 per 10,000 orders**, and every one auto-refunds within **24 h** without the customer contacting us | At ~13M orders/day and ~$6 per support contact (assumed), 0.1% is ~13k contacts/day — **~$28M/year** in support alone, before the trust cost. This figure is the business case for the whole of §9 |
| **Cancellation** | Free cancel honoured if the request is **received before the pick**; the race resolves within **2 s** and the customer is told which way it went | The window is real (~30 min, §3) and it closes. A "cancel" that silently becomes a return is worse than a cancel that says it lost |
| **Fault tolerance** | Survives loss of **fulfilment** (orders queue in the outbox), **the payment processor** (orders are accepted with authorization deferred, and nothing releases to fulfilment until authorized), and the **pricing service** (the quote is already minted). **Does not survive loss of the order store** | Naming the one component that isn't allowed to fail is what forces the order store to be the boring, replicated, transactional thing in §12. A design where everything survives everything hasn't been sized under failure |
| **Availability — Place Order** | **99.99%** | Amazon's own oft-quoted framing: a checkout outage is measured in revenue per minute. At ~$10M/hour of gross merchandise value (assumed), a minute is ~$170k |
| **Security** | **No card data touches our systems** — PCI **SAQ-A**, tokenized at the processor's hosted field (the mechanism is argued on the LLM API billing page, §5); addresses encrypted at rest; order history authorized per customer on every read | Checkout is the highest-value PII surface in the product. Scoping card data out at the API boundary is a design decision, not a compliance chore |

**The sentence that earns the point:** *"I'm not going to put inventory, payment, and the warehouse in one transaction, because the warehouse cannot be in one — there is no such thing as rolling back a box on a truck. What I'll do instead is sort the steps by how expensive they are to undo, commit the order at the single point where I own all the state, and accept that everything after that point is at-least-once with a compensation that is a refund and an email rather than a rollback."*

---

## 3 · Numbers that reframe the problem

**Assume** ~13M orders/day worldwide (≈1.6B packages/year at ~2.4 units per order), ~300M active SKUs, ~180 fulfilment centres, and ~400M active customers. All four are assumptions; every figure below is derived from them, and each one changes a decision.

**The reframe, and it's the first thing you should say**

- **13M orders/day = ~150 orders/s average, ~1,500/s at Prime Day peak** (assume 10× diurnal and event spike). **That is a single database's worth of writes.** Set it against the read side — product page views run three orders of magnitude higher — and the conclusion is unavoidable: **checkout is not a scale problem, it's a correctness problem**, and the browse path that *is* a scale problem shares nothing with it but a SKU id. Say this out loud in the first two minutes. It's what licenses you to spend the remaining forty on sagas instead of on sharding.

**Per SKU — the number that kills Ticketmaster's mechanism**

- **13M orders/day across 300M SKUs is ~0.04 units/day for the average SKU.** Contention is **approximately one**. There is no thundering herd, no queue, and no seat map: the correct primitive is a counter and a conditional decrement, and any design that reaches for per-unit rows or a lock service has paid Ticketmaster's price without buying anything. **→ this is the cell `Ticketmaster §15` predicts, and collecting on that prediction out loud is worth ten seconds.**
- **The exception, and you should name it before the interviewer does:** a Lightning Deal — 10,000 units against ~500k shoppers in five minutes — is **~1,600 attempts/s against one SKU**. That is Ticketmaster, exactly, and the honest answer is that those SKUs get routed onto that page's mechanism rather than this one. **It is well under 0.01% of order lines, and the design decision is to not let it distort the other 99.99%.**

**The gap between the money and the goods — the number that creates §11**

- **A card authorization is good for about 7 days** for card-not-present transactions, and expires after that. **Assume ~3% of orders don't ship inside that window** — backorders, preorders, made-to-order, slow third-party sellers. That's **~390k orders/day requiring re-authorization**, each of which can decline on a card that worked a week ago. *A re-authorization queue with a decline path is a component, not an edge case*, and the 3% assumption is what promotes it from a footnote to §11.

**The point of no return**

- **Median time from order placed to item picked: ~30 minutes** in a same-day network (assumption). That is the entire free-cancellation window, and it is far shorter than most candidates assume. It means the cancel path is **a race against a physical process measured in minutes**, not a nightly batch job, and it's why §10 models cancellation as a request that can lose rather than as a state transition that always succeeds.

**The cost of getting the saga wrong**

- **0.1% of orders ending charged-but-not-shipped = ~13,000/day.** At ~$6 per support contact (assumed), that's **~$78k/day, ~$28M/year**, before counting the customers who simply stop coming back. Quote this when someone proposes charging the card first because it's simpler.

---

## 4 · Core entities

- **Cart** — customer, list of `(sku, quantity, added_at)`. **No prices, no totals** — see below
- **CheckoutSession** — the cart snapshot, address, shipping option, payment method token, the minted **Quote**, and the key that makes placement idempotent
- **Quote** — line prices, promotions applied, shipping, tax, total, `expires_at`. Minted server-side, referenced by id
- **InventoryReservation** — `(sku, fc_id)`, quantity, `order_id`, `expires_at`
- **Order** — customer, lines, quote reference, totals, `state`, `placed_at`
- **OrderLine** — sku, quantity, unit price at placement, tax, promised ship-by date, shipment reference
- **PaymentAuthorization** — order, processor intent id, authorized amount, `authorized_at`, `expires_at`, captured amount so far
- **Shipment** — fulfilment centre, lines, carrier, tracking, `shipped_at`
- **OrderEvent** — append-only record of every state transition with actor, reason, and request id

**Load-bearing details:**

- **The cart holds no money.** It is a list of intents — SKUs and quantities — and every price is computed at quote time. A cart that caches prices is a cart that shows a customer a total from three weeks ago, and worse, it makes the cart a thing that has to be invalidated by a pricing change across 400M customers. **Carts are cheap and disposable; quotes are expensive and short-lived.** That split is the whole of §8.
- **`CheckoutSession.id` is the idempotency key for Place Order, and it is derived, not random.** A double-click, a retry after a timeout, and a second browser tab all carry the same session, so all three collapse into one order. A client-generated random key does not have this property — it makes the *client* responsible for recognising its own retry, which is exactly the thing a client with a flaky network cannot do. The general mechanism is in `system-design.md §04 C`; what's specific here is the choice of *which* existing id to use, and the rule that **the best idempotency key is one that already exists for another reason.**
- **`InventoryReservation` carries a quantity against a `(sku, fc)` pair, not a status against a unit.** This is the single biggest structural difference from `Ticketmaster §4`, where the entity is a seat with three states. Amazon's customer never picks a specific physical object, so there is nothing to hold — only a number to move. It is still **a row with an expiry**, and the lazy-expiry mechanism from `Ticketmaster §7` transfers unchanged; only the shape of the thing being held is different.
- **`PaymentAuthorization` is a separate entity from `Order`, with its own lifecycle and its own expiry.** Modelling payment as a column on the order is what makes re-authorization, partial capture across shipments, and a second attempt on a declined card impossible to express. One order can have several authorizations over its life, and their sum is not the order total.
- **`OrderEvent` is append-only.** No transition is ever recorded by mutating `Order.state` alone. Support, dispute handling, and "why did this order cancel itself" all need the sequence, and a current-state column can't answer any of them — the same argument the LLM API billing page makes for its ledger in `§4`.

---

## 5 · API

```http
# Customer-facing
POST   /carts/{cartId}/items                { sku, quantity }
POST   /checkout/sessions                   { cartId } → { sessionId }
PATCH  /checkout/sessions/{sessionId}       { addressId?, shippingOption?, paymentMethodToken? }
GET    /checkout/sessions/{sessionId}       → { lines, shipping, tax, total, quoteId, expiresAt }
POST   /orders                              { sessionId, quoteId }
                                            Idempotency-Key: {sessionId}
                                            → 201 { orderId, state, promisedShipBy }
POST   /orders/{orderId}/cancel             → 202 { state: CANCEL_REQUESTED }
GET    /orders/{orderId}                    → order + shipments + tracking

# Internal — service to service, never reachable by a customer
POST   /inventory/reservations              { orderId, lines[] } → { reservationId, expiresAt }
DELETE /inventory/reservations/{id}
POST   /payments/authorizations             { orderId, amount, paymentMethodToken }
POST   /payments/authorizations/{id}/capture{ amount, shipmentId }
POST   /payments/authorizations/{id}/void

# Processor → us
POST   /webhooks/payments                   signature-verified; 200 means "durably queued", not "applied"
```

**Decisions to narrate, unprompted:**

- **`POST /orders` takes a `quoteId`, and rejects a stale one.** The client cannot submit a total; it can only submit a reference to a total the server minted. This is what makes requirement 2 enforceable rather than aspirational, and it turns "the price changed while I was checking out" from a silent mischarge into a 409 and a re-quote.
- **The `Idempotency-Key` is the session id.** See §4. Say the reason out loud — a key that already exists for another reason cannot be lost by the client that needs it.
- **Reservation is internal, and there is no customer-facing "hold my cart" call.** `Ticketmaster §5` makes holding an explicit user action because the seat *is* the product and the customer chose it. Here the customer chose a SKU, not an object, so reservation is an implementation detail inside Place Order. **Exposing it would let anyone strand inventory for free.**
- **Cancel returns `202` and a `CANCEL_REQUESTED` state, not `200 CANCELLED`.** The API is telling the truth about a race it may lose (§10). This is one of the few places where a slightly worse-looking API is the correct one, and interviewers notice.
- **Authorize and capture are separate endpoints, and capture takes a shipment id.** A single `charge` call cannot express "ship two of the four items today and charge for those" — see §11.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 800" role="img" aria-label="Amazon checkout architecture, split horizontally by reversibility. A client tier with the cart and the checkout session. Above the dashed commit line, a synchronous tier: the order service calling inventory for a conditional reserve against available-to-promise in DynamoDB, and the payment service authorizing at a third-party processor. At the centre, the order store in Postgres and Citus holding orders, lines, payment references and an outbox row committed in one transaction. Below the line, an outbox pump feeding Kafka order events, consumed by fulfilment, which picks, packs and ships, and by the notification and capture workers that capture money per shipment.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">The dashed line is the commit point. Above it everything is reversible; below it nothing is, and the last step is a warehouse.</text>
  <rect class="dg-box" x="20" y="100" width="170" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="105" y="126.5">Client</text>
  <text class="dg-s dg-c" x="105" y="142.5">cart · review · submit</text>
  <rect class="dg-box" x="230" y="100" width="230" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="345" y="118.5">Checkout Session</text>
  <text class="dg-s dg-c" x="345" y="134.5">quote + expires_at, 15 min</text>
  <text class="dg-s dg-c" x="345" y="150.5">quoteId submitted, never a total</text>
  <path class="dg-box" d="M 500,107 L 500,153 A 105,7 0 0 0 710,153 L 710,107 A 105,7 0 0 0 500,107 Z"></path>
  <path class="dg-box" d="M 500,107 A 105,7 0 0 0 710,107" style="fill:none"></path>
  <text class="dg-t dg-c" x="605" y="130">DynamoDB</text>
  <text class="dg-s dg-c" x="605" y="146">carts · sessions · TTL</text>
  <rect class="dg-box" x="750" y="100" width="230" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="865" y="126.5">Idempotency store</text>
  <text class="dg-s dg-c" x="865" y="142.5">key = checkout session id</text>
  <path class="dg-line" d="M 190,130 L 222,130"></path>
  <path class="dg-head" d="M 222,135 L 222,125 L 230,130 Z"></path>
  <path class="dg-line" d="M 460,130 L 492,130"></path>
  <path class="dg-head" d="M 492,135 L 492,125 L 500,130 Z"></path>
  <path class="dg-line" d="M 345,160 L 345,188"></path>
  <path class="dg-head" d="M 340,188 L 350,188 L 345,196 Z"></path>
  <rect class="dg-group" x="20" y="196" width="960" height="150" rx="12"></rect>
  <text class="dg-group-t" x="36" y="218">REVERSIBLE — INSIDE THE REQUEST, UNDONE FOR FREE</text>
  <rect class="dg-box" x="36" y="228" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="176" y="248.5">Inventory Service</text>
  <text class="dg-s dg-c" x="176" y="264.5">conditional decrement per line</text>
  <text class="dg-s dg-c" x="176" y="280.5">sharded by sku</text>
  <path class="dg-box" d="M 340,235 L 340,285 A 125,7 0 0 0 590,285 L 590,235 A 125,7 0 0 0 340,235 Z"></path>
  <path class="dg-box" d="M 340,235 A 125,7 0 0 0 590,235" style="fill:none"></path>
  <text class="dg-t dg-c" x="465" y="260">ATP — DynamoDB</text>
  <text class="dg-s dg-c" x="465" y="276">on_hand - reserved &gt;= qty</text>
  <rect class="dg-box" x="614" y="228" width="350" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="789" y="248.5">Payment Service</text>
  <text class="dg-s dg-c" x="789" y="264.5">authorize the quote total</text>
  <text class="dg-s dg-c" x="789" y="280.5">voidable at zero cost</text>
  <path class="dg-line" d="M 316,260 L 332,260"></path>
  <path class="dg-head" d="M 332,265 L 332,255 L 340,260 Z"></path>
  <path class="dg-line" d="M 590,260 L 606,260"></path>
  <path class="dg-head" d="M 606,265 L 606,255 L 614,260 Z"></path>
  <text class="dg-s" x="36" y="316">1. reserve — cheapest to undo, and the most likely ordinary failure.   2. authorize — reversible, and it must not be inside an inventory lock.</text>
  <path class="dg-good" d="M 230,403 L 230,461 A 270,7 0 0 0 770,461 L 770,403 A 270,7 0 0 0 230,403 Z"></path>
  <path class="dg-good" d="M 230,403 A 270,7 0 0 0 770,403" style="fill:none"></path>
  <text class="dg-t dg-c" x="500" y="424">Order Store — Postgres + Citus</text>
  <text class="dg-s dg-c" x="500" y="440">orders · lines · payment refs · first event · OUTBOX ROW</text>
  <text class="dg-s dg-c" x="500" y="456">one local transaction, sharded by customer_id</text>
  <path class="dg-line" d="M 176,292 L 176,432 L 222,432"></path>
  <path class="dg-head" d="M 222,437 L 222,427 L 230,432 Z"></path>
  <path class="dg-line" d="M 789,292 L 789,432 L 778,432"></path>
  <path class="dg-head" d="M 778,427 L 778,437 L 770,432 Z"></path>
  <path class="dg-div" d="M 20,500 L 980,500"></path>
  <text class="dg-lane" x="30" y="494">THE COMMIT POINT — ABOVE IT, ABANDONABLE. BELOW IT, RETRIED FOREVER</text>
  <rect class="dg-box" x="230" y="528" width="540" height="56" rx="8"></rect>
  <path class="dg-qbar" d="M 243,537 L 243,575"></path>
  <path class="dg-qbar" d="M 252,537 L 252,575"></path>
  <path class="dg-qbar" d="M 261,537 L 261,575"></path>
  <text class="dg-t dg-c" x="518" y="552.5">Kafka  order.placed</text>
  <text class="dg-s dg-c" x="518" y="568.5">outbox pump · keyed by order_id · at-least-once</text>
  <path class="dg-line" d="M 640,468 L 640,520"></path>
  <path class="dg-head" d="M 635,520 L 645,520 L 640,528 Z"></path>
  <rect class="dg-group" x="20" y="620" width="960" height="118" rx="12"></rect>
  <text class="dg-group-t" x="36" y="642">IRREVERSIBLE — OUTSIDE THE REQUEST, PAID FOR IN RETURNS</text>
  <rect class="dg-box" x="36" y="652" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="186" y="672.5">Fulfilment</text>
  <text class="dg-s dg-c" x="186" y="688.5">plan · pick · pack · ship</text>
  <text class="dg-s dg-c" x="186" y="704.5">the pick is the point of no return</text>
  <rect class="dg-box" x="360" y="652" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="680.5">Capture worker</text>
  <text class="dg-s dg-c" x="500" y="696.5">per shipment, derived key</text>
  <rect class="dg-box" x="664" y="652" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="814" y="680.5">Payment processor</text>
  <text class="dg-s dg-c" x="814" y="696.5">its own page — the inverse</text>
  <path class="dg-line" d="M 350,584 L 350,620 L 186,620 L 186,644"></path>
  <path class="dg-head" d="M 181,644 L 191,644 L 186,652 Z"></path>
  <path class="dg-line" d="M 640,684 L 656,684"></path>
  <path class="dg-head" d="M 656,689 L 656,679 L 664,684 Z"></path>
  <path class="dg-line" d="M 336,684 L 352,684"></path>
  <path class="dg-head" d="M 352,689 L 352,679 L 360,684 Z"></path>
  <text class="dg-note" x="20" y="778">Reserve, authorize, commit, ship, capture — sorted by how expensive each is to undo. Nothing rolls a box back off a truck, so the box goes last.</text>
</svg>
</div>

<p class="diagram-cap">Draw the dashed line before anything else, and label it the commit point. Above it the steps are ordered by how cheap they are to undo; below it nothing is undoable and every failure is compensated with an apology rather than a rollback. The order store is the only component that belongs to both halves, and its outbox row is why the hand-off downstream is reliable.</p>

**The two properties to point at before walking an order through it:**

1. **The dashed line is the commit point.** Everything above it is reversible and happens synchronously inside the customer's request: reserving stock, authorizing a card. The order row is the commit. Everything below it is at-least-once, asynchronous, and increasingly expensive to undo, ending at a warehouse where undo is not available at any price.
2. **No two stores in this picture share a transaction.** Inventory is keyed by SKU, orders by customer, payment is at a third party, fulfilment is a building. The outbox in the order database is the only thing that makes the hand-off downstream reliable, and it works precisely because it is *in* the transaction that commits the order.

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 660" role="img" aria-label="Place Order flow, as a sequence with its branches. The idempotency check comes first and short-circuits a double click. Then the quote is validated, with an expired quote branching to a 409 and a re-quote. Then inventory is reserved, with out-of-stock branching to a clean failure. Then payment is authorized, with a decline releasing the reservation. Then the order commits in one transaction. Below the commit, the outbox publishes to fulfilment, which picks and ships, and capture happens per shipment. A separate branch shows the cancel request racing the pick, winning or losing.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Every branch above the commit line ends with nothing having happened. Every branch below it ends with an apology.</text>
  <rect class="dg-good" x="30" y="68" width="300" height="40" rx="8"></rect>
  <text class="dg-good-t dg-c" x="180" y="92.5">POST /orders  Idempotency-Key = sessionId</text>
  <rect class="dg-good" x="400" y="68" width="250" height="40" rx="8"></rect>
  <text class="dg-good-t dg-c" x="525" y="92.5">key seen → replay the stored response</text>
  <path class="dg-line" d="M 330,88 L 392,88"></path>
  <path class="dg-head" d="M 392,93 L 392,83 L 400,88 Z"></path>
  <text class="dg-lbl dg-c" x="365" y="80">hit</text>
  <rect class="dg-box" x="30" y="132" width="300" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="156.5">validate the quote</text>
  <path class="dg-line" d="M 180,108 L 180,124"></path>
  <path class="dg-head" d="M 175,124 L 185,124 L 180,132 Z"></path>
  <rect class="dg-warn" x="400" y="132" width="250" height="40" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="525" y="156.5">409 + a fresh quote, re-confirm</text>
  <path class="dg-line" d="M 330,152 L 392,152"></path>
  <path class="dg-head" d="M 392,157 L 392,147 L 400,152 Z"></path>
  <text class="dg-lbl dg-c" x="365" y="144">expired</text>
  <rect class="dg-box" x="30" y="196" width="300" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="220.5">reserve inventory — conditional decrement</text>
  <path class="dg-line" d="M 180,172 L 180,188"></path>
  <path class="dg-head" d="M 175,188 L 185,188 L 180,196 Z"></path>
  <rect class="dg-warn" x="400" y="196" width="250" height="40" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="525" y="220.5">409 out_of_stock — nothing to undo</text>
  <path class="dg-line" d="M 330,216 L 392,216"></path>
  <path class="dg-head" d="M 392,221 L 392,211 L 400,216 Z"></path>
  <rect class="dg-box" x="30" y="260" width="300" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="284.5">authorize payment</text>
  <path class="dg-line" d="M 180,236 L 180,252"></path>
  <path class="dg-head" d="M 175,252 L 185,252 L 180,260 Z"></path>
  <rect class="dg-warn" x="400" y="260" width="250" height="40" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="525" y="284.5">decline → release the reservation</text>
  <path class="dg-line" d="M 330,280 L 392,280"></path>
  <path class="dg-head" d="M 392,285 L 392,275 L 400,280 Z"></path>
  <rect class="dg-good" x="30" y="324" width="620" height="56" rx="8"></rect>
  <text class="dg-good-t dg-c" x="340" y="348.5">COMMIT — order + lines + payment ref + event + outbox row</text>
  <text class="dg-s dg-c" x="340" y="364.5">one local transaction, one database</text>
  <path class="dg-line" d="M 180,300 L 180,316"></path>
  <path class="dg-head" d="M 175,316 L 185,316 L 180,324 Z"></path>
  <path class="dg-div" d="M 20,400 L 980,400"></path>
  <text class="dg-lane dg-c dg-c" x="500" y="396">BELOW HERE, FAILURE IS COMPENSATED — NEVER ROLLED BACK</text>
  <rect class="dg-box" x="30" y="424" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="448.5">outbox → Kafka → fulfilment</text>
  <text class="dg-s dg-c" x="180" y="464.5">at-least-once, idempotent consumer</text>
  <path class="dg-line" d="M 180,380 L 180,416"></path>
  <path class="dg-head" d="M 175,416 L 185,416 L 180,424 Z"></path>
  <rect class="dg-warn" x="400" y="424" width="250" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="525" y="448.5">pick</text>
  <text class="dg-s dg-c" x="525" y="464.5">THE POINT OF NO RETURN</text>
  <path class="dg-line" d="M 330,452 L 392,452"></path>
  <path class="dg-head" d="M 392,457 L 392,447 L 400,452 Z"></path>
  <rect class="dg-box" x="700" y="424" width="270" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="835" y="448.5">ship → capture that shipment</text>
  <text class="dg-s dg-c" x="835" y="464.5">void the remainder at the end</text>
  <path class="dg-line" d="M 650,452 L 692,452"></path>
  <path class="dg-head" d="M 692,457 L 692,447 L 700,452 Z"></path>
  <rect class="dg-box" x="30" y="512" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="536.5">POST /cancel → CANCEL_REQUESTED</text>
  <text class="dg-s dg-c" x="180" y="552.5">202, because it is a race</text>
  <rect class="dg-box" x="400" y="512" width="570" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="685" y="528.5">the race resolves, and either way is normal</text>
  <text class="dg-s dg-c" x="685" y="544.5">won  →  void the auth, release the stock, order CANCELLED</text>
  <text class="dg-s dg-c" x="685" y="560.5">lost  →  a prepaid return label, which is a different product</text>
  <path class="dg-line" d="M 330,540 L 392,540"></path>
  <path class="dg-head" d="M 392,545 L 392,535 L 400,540 Z"></path>
  <text class="dg-note" x="30" y="610">The unfulfillable line — a picker finds the last one damaged — is compensated, not rolled back: a void or a refund, and an email before the customer notices.</text>
</svg>
</div>

<p class="diagram-cap">The four boxes down the left are ordered by cost to undo, and every one of them can fail into the column on the right with nothing having happened. Below the divider that is no longer true — the pick has started and the compensation is an email, a refund, or a return label.</p>

### Flow A — Place Order

1. The customer presses the button. `POST /orders` arrives with the session id as its `Idempotency-Key` and the `quoteId` the review page was showing.
2. **The idempotency check runs first.** If this key has a stored terminal response, return it byte-for-byte and stop — this is the double-click, and it never reaches step 3.
3. **Validate the quote.** Expired or superseded → `409` with a fresh quote, and the review page re-renders with the new total. **This is the only place a price change is allowed to surprise anyone**, and it happens before any money moves (§8).
4. **Reserve inventory** — one conditional decrement per line against `(sku, fc)` available-to-promise (§7). Cheap, reversible, and it goes first because it is the step most likely to fail for an ordinary reason. Failure here is a clean `409 out_of_stock` with nothing to undo.
5. **Authorize payment** for the quote total (§11). Reversible — an authorization can be voided. Decline is a clean failure: release the reservation and return a card error. **Note the ordering: we take the reversible-and-likely-to-fail step before the reversible-and-expensive one.**
6. **Commit the order.** One local transaction in the order database writes the `Order`, its `OrderLine`s, the `PaymentAuthorization` reference, the first `OrderEvent`, **and an outbox row** for fulfilment. **This is the atomic point of the entire page** — everything before it can be abandoned, everything after it will be retried until it succeeds.
7. Return `201` with the order id and the promised ship-by date. From the customer's point of view, checkout is over.
8. **The outbox pump publishes `order.placed` to Kafka**, keyed by order id. Fulfilment consumes it, plans shipments, and eventually picks. At-least-once delivery, idempotent consumer — the standard triple, argued in full at `system-design.md §06 D` and in `Billing §7`; there is nothing new about it here and you should say so and move on.
9. **On each shipment, capture that shipment's share of the authorization** (§11). The last shipment closes the order and voids any remainder.

**Failure path — the process dies between step 5 and step 6.** The card is authorized and no order exists. The authorization is never captured, so no money ever actually moves; it expires on its own in ~7 days, and a reaper voids orphaned authorizations within the hour so the customer's available balance isn't held hostage. **The customer sees a pending charge that vanishes** — annoying, recoverable, and strictly better than the alternative ordering.

**Failure path — the outbox pump is down at step 8.** Orders keep being accepted and committed; they simply queue. This is the fault-tolerance row in §2 made concrete, and it is the entire reason the outbox row is written **inside** the transaction rather than published after it. **→ ties to the fault-tolerance NFR.**

**Failure path — the payment processor is unreachable at step 5.** We accept the order anyway, in an `AWAITING_AUTHORIZATION` state, and nothing releases to fulfilment until authorization succeeds. **This is a decision, and the alternative deserves saying out loud:** refusing the order is the safe engineering choice and the wrong business one — it converts a processor's bad five minutes into our lost revenue and a customer who buys elsewhere. The exposure is bounded because no goods move before the money is authorized, and the retry has a deadline after which the order self-cancels with an email.

### Flow B — the last one on the shelf is broken

1. The order is committed, captured nothing yet, and is with fulfilment. A picker finds the unit damaged, or the bin is empty because the count was wrong.
2. Fulfilment emits `line.unfulfillable`. The order service moves the line to `CANCELLED_BY_SUPPLY` and **corrects inventory** — this is real shrinkage, not a reservation release, and the correction is what keeps available-to-promise honest (§7).
3. **Compensation runs, and it is a business action, not a rollback:** the line's share of the authorization is voided or refunded depending on whether it was already captured, the customer is emailed before they notice, and a replacement is offered from another fulfilment centre if one has stock.
4. Nothing is deleted. The order keeps its line with a terminal state and an `OrderEvent` explaining it.

**Failure path — the line was already captured because it shipped with an earlier shipment's capture.** Then the compensation is a **refund**, which costs us the payment processing fee that does not come back. That fee is the price of having captured optimistically, and it is why §11 captures per shipment rather than at placement.

### Flow C — a cancel that races the pick

1. `POST /orders/{id}/cancel` sets `CANCEL_REQUESTED` and emits an event. **It does not set `CANCELLED`.**
2. Fulfilment attempts to halt the pick. Two outcomes, and both are normal.
3. **Won the race:** the pick is stopped, inventory is released back to available-to-promise, the authorization is voided, and the order lands in `CANCELLED`. The customer sees confirmation within ~2 s.
4. **Lost the race:** the item is already picked or packed. The order continues to `SHIPPED`, and the cancel is converted into a **prepaid return label** — which is a different product with a different cost, and the customer is told so plainly.

**Failure path — the cancel and the pick commit simultaneously.** One of them wins, decided at the fulfilment side, and the API's `202` was honest about that from the beginning. **The failure mode this design prevents is the one where the UI says "cancelled" and a box arrives anyway**, which is the version customers actually complain about.

### Flow D — capture at ship, days later

1. A shipment leaves the fulfilment centre. Fulfilment emits `shipment.shipped` with the lines it contains.
2. The payment service **captures exactly that shipment's share** of the authorization (§11), using an idempotency key derived from `(authorization_id, shipment_id)` — stable across our own retries, exactly as `Billing §10` derives its own.
3. The order's remaining authorized balance drops. When the final shipment captures, any remainder is voided.

**Failure path — the authorization has expired because the item was on backorder for nine days.** A re-authorization is attempted against the stored token before the shipment is released. If it declines, **the shipment is held, not sent**, and the customer is asked for a different card. **This is the one place where we deliberately stop the physical process rather than compensate afterwards, because it's the last moment where stopping is still cheap.**

**Failure path — the capture fails after the box has shipped.** Keep the shipment. Record the shortfall as debt against the customer account and retry asynchronously. **The reasoning is the same one `Ticketmaster §11` gives for keeping a sale after a capture failure and `Uber §9` gives for its debt record: never let a payment failure undo a commitment a human is already relying on.** Chasing $40 is cheaper than recalling a box and far cheaper than the trust cost of doing so.

---

## 7 · Deep dive — inventory when it's a counter, not a seat map

### What you'd reach for first

`SELECT … FOR UPDATE` on a row per SKU, or — with Ticketmaster fresh in mind — a row per physical unit with a status flip from `AVAILABLE` to `HELD`.

### What breaks, specifically

**The per-unit model breaks on arithmetic.** Amazon holds billions of individual units. A row per unit is a table with more rows than the order history, mutated constantly by receipts, transfers, damage, and cycle counts, and **it buys nothing** — the customer never selects a specific object, so unit identity is a fiction the database is paying to maintain.

**The pessimistic lock breaks on being pointless.** At ~0.04 units/day for the average SKU (§3), contention is approximately one. `FOR UPDATE` serializes writers that were never going to collide, and the cost isn't the lock — it's that the lock has to be held across whatever else is in the transaction, which drags the payment call inside it if you're not careful.

**And both break on a false premise:** that the number in the database is the number on the shelf. It isn't. Stock is wrong all the time — theft, damage, misplacement, receiving errors. **Any design whose correctness depends on the count being exact is describing a warehouse that doesn't exist.**

### What replaces it

**Available-to-promise as a counter per `(sku, fulfilment_centre)`, moved by a conditional update, with a deliberate non-zero oversell rate.**

```sql
UPDATE atp
   SET reserved = reserved + :qty
 WHERE sku = :sku AND fc_id = :fc
   AND on_hand - reserved >= :qty
```

Three properties do the work:

- **The conditional is the correctness.** No lock is taken and no read precedes the write; either the row satisfies the predicate at write time or the statement affects zero rows and the line fails cleanly. This is the same shape as `Ticketmaster §7`'s conditional update, with a quantity where that page has a status.
- **Reservations expire lazily, exactly as they do on the Ticketmaster page.** A reservation row carries `expires_at`, and the release is a predicate evaluated by the next writer rather than a sweeper job. That page argues the mechanism in full and there is no reason to re-derive it — **cite it and spend the time here instead.**
- **Sharding by SKU is what makes this trivially parallel**, and it's also what makes the saga necessary: inventory's partition key and the order store's partition key are different, so they can never share a transaction (§12).

**The oversell target is a number, and stating it is the point.** We accept **≤2 oversells per 10,000 order lines** (§2). Driving it to zero would mean reserving on add-to-cart rather than at Place Order, which strands stock across hundreds of millions of abandoned carts. **The line to say:** *"Available-to-promise is a forecast with a measured error rate, not a fact. I'd rather apologise twice in ten thousand lines than strand inventory for every cart that never converts."* **→ ties to the oversell-rate row in §2**, which is a number precisely so that this trade can be argued rather than asserted.

**The hot-SKU exception is routed, not absorbed.** A Lightning Deal at ~1,600 attempts/s against one row (§3) is genuinely Ticketmaster's problem, and it gets Ticketmaster's answer — a queue in front, and inventory pre-sharded into per-partition allotments. **The decision worth defending is not letting 0.01% of order lines dictate the mechanism for the other 99.99%.**

### What it costs

Overselling is now a thing that happens on purpose, which means **a compensation path with an owner** — the flow in §6B, an email template, and a replacement-sourcing step. It also means available-to-promise disagrees with physical reality continuously, so **cycle counts become a correctness component rather than a warehouse chore**: the reconciliation that keeps the counter honest is a scheduled physical process, and its findings are inventory corrections, not bugs. And splitting by fulfilment centre means "is this in stock" is a fan-out across ~180 partitions rather than one read, which the promise service caches with a short TTL and accepts as approximate.

---

## 8 · Deep dive — the checkout session, and the price you honour

### What you'd reach for first

Compute the total on every page render from current prices, current promotions, and current tax rates. The number is always fresh, and the cart stays a simple list.

### What breaks

**Fresh is the wrong property.** A checkout takes two to five minutes across four screens. In that window a price can change, a promotion can expire, a coupon budget can exhaust, and a tax rate can flip because the customer changed the address. With per-render computation, **the total on the review page and the total charged at submit are computed at different instants and can differ**, and the customer's evidence is a screenshot.

**It is also expensive in the wrong place.** A full price computation is a fan-out — pricing, promotions, tax vendor, shipping — on every keystroke-triggered re-render, on the one path in the product that has a hard latency budget.

**And it makes the failure modes unbounded:** if the tax vendor is down at submit, an order that was fully priced thirty seconds ago cannot be placed.

### What replaces it

**A server-minted Quote with an explicit TTL, referenced by id, and re-minted only at defined moments.**

- **The quote is computed once**, when the customer reaches the review step or changes something material (address, shipping speed, cart contents), and it is stored with `expires_at = now() + 15 minutes`.
- **`POST /orders` submits a `quoteId`, never a total.** A quote that is expired or superseded is a `409`, the review page re-renders with the new numbers, and the customer re-confirms. **A price change becomes an explicit re-confirmation rather than a silent mischarge.**
- **Inside the TTL, the quote is what we honour, full stop** — including if the price went *up*. We eat the delta, and the 15-minute window is chosen to make the exposure small enough that eating it is cheaper than arguing about it. **→ ties to the price-integrity row in §2**, which is the only NFR on the page set at 100%.
- **The quote is the unit of durability, and the cart is not.** The cart survives for months and holds no money; the quote lives for fifteen minutes and holds all of it. **That split is what lets the cart be a cheap, eventually-consistent, cross-device blob while the money-shaped object gets a strong store.**

### What it costs

You are now storing a short-lived object per checkout attempt — small, but it's a write on a path that previously had none, and it needs a TTL sweep. Customers who leave the review page open past fifteen minutes get a re-quote, which is a real UX papercut and the reason for the TTL being minutes rather than seconds. And **you have accepted an adverse-selection window**: if a price rises inside the TTL, the customers who complete are disproportionately the ones who benefit. At fifteen minutes and Amazon's price-change rate this is small; on a product with volatile pricing — travel, energy — it is not, and the TTL has to shrink until it is.

---

## 9 · Deep dive — Place Order as a saga

### What you'd reach for first

A distributed transaction. Inventory, payment, and order in one atomic unit, two-phase commit across the services, so that either everything happens or nothing does.

### What breaks

**The warehouse cannot enlist.** This is the mechanical reason, and it is sufficient on its own. 2PC requires every participant to be able to hold a prepared state and then commit or abort on instruction. A fulfilment centre cannot prepare-to-ship; the moment a box is on a truck there is no abort. **Any protocol that requires all participants to be reversible is unavailable the instant one participant is a physical process.**

**The processor cannot enlist either.** It is a third party with an HTTP API and no XA support, and it wouldn't offer one — its whole design (`Billing §10`) is built around the *absence* of a shared transaction, which is why it hands you an idempotency key instead.

**And 2PC's failure mode is the wrong one for a checkout.** A coordinator crash between prepare and commit leaves participants blocked holding locks. On a path where the customer is watching a spinner and inventory rows are held, that is precisely the outage you were trying to prevent.

### What replaces it

**An ordered saga with a single atomic commit point, and compensations that are business actions.**

The ordering rule is the whole thing, and `system-design.md §07 D` states it in one line — *if the flow must charge a card and ship a box, charge last*. Made concrete:

| Step | Reversible? | Cost to undo | Therefore |
|---|---|---|---|
| Reserve inventory | Yes | Free — a counter moves back, or a TTL expires | **First**, and it's also the most likely ordinary failure |
| Authorize payment | Yes | Free — void the auth; no money moved | Second |
| **Commit the order** | — | — | **The atomic point.** One local transaction, one database |
| Publish to fulfilment | No, but retryable | Retry until it lands | After the commit, via outbox |
| Pick and ship | **No** | Reverse logistics — a return label and a truck | **Last** |
| Capture the money | Effectively no | A refund, minus a fee that never comes back | With the ship, per shipment |

**The commit is one local transaction, not a saga step.** Order, lines, payment reference, first event, and the outbox row all go in together, in the order database. Everything upstream of it can be abandoned with no trace; everything downstream will be retried forever. **Locating that single point, and being able to say why it is where it is, is the highest-value thirty seconds on this page.**

**Idempotency is not re-derived here.** The key is the checkout session id (§4), the mechanism is `system-design.md §04 C`, and our own retries against the processor use derived keys exactly as `Billing §10` does. Say which existing pattern you're using and move on — spending five minutes re-deriving idempotency is time taken from the part of this problem that's actually novel.

**Compensation is a business action, not a rollback.** Releasing a reservation is a counter moving. But an unfulfillable line is *an email, a refund, and an offer of a replacement*; a lost cancel race is *a prepaid return label*. Neither of them restores a prior state, and describing them as rollbacks is how designs end up with a compensating step that quietly cannot exist.

**On durable execution:** `Airbnb §9` argues the case for Temporal on a booking saga and explicitly rules it **overkill** for a Ticketmaster-shaped checkout — short, hot-path, enormously frequent. Amazon's Place Order is that profile. The synchronous portion is three steps and sub-second; the asynchronous portion is a state machine driven by events that already exist. **A hand-rolled state machine plus an outbox is the right weight here, and being able to say *why* — rather than reaching for the orchestrator because it's the impressive answer — is the signal.**

### What it costs

**There is a window where an order exists and money is authorized but fulfilment hasn't acknowledged it.** It's bounded by outbox lag, but it's real, and it needs a reaper: orders sitting in `AWAITING_FULFILMENT` beyond a threshold get alarmed on, because a silently stuck outbox is invisible from the customer side until the promised delivery date passes. **You have also given up the ability to say "nothing happened".** Every failure after the commit point leaves visible residue — an order in a terminal-but-unhappy state, an email the customer received, a refund on a statement. That residue is the honest cost of not having a transaction, and it's better than the alternative, which is pretending you do.

---

## 10 · Deep dive — the order state machine and the point of no return

### What you'd reach for first

`DELETE FROM orders WHERE id = ?`, or a `cancelled` boolean. Cancellation is the customer changing their mind, so undo the order.

### What breaks

**A physical process already started, and it doesn't read your database.** At a median of ~30 minutes from placement to pick (§3), a large fraction of cancellations arrive **after** the item is in a tote. There is no state you can write that un-picks it.

**And the cancellation itself is a race with two writers**, one of which is a warehouse. Modelling it as a synchronous transition means the API must either lie (`200 CANCELLED`, box arrives anyway) or block on the warehouse (which cannot answer in 200 ms).

**A boolean also destroys the history**, and this is the object support and disputes ask about most. "Why was I charged for something I cancelled" is answerable only from the sequence.

### What replaces it

**An explicit state machine with a named point of no return, and cancellation modelled as a request that races it.**

```text
                                    ┌──▶ CANCELLED
PENDING ─▶ AWAITING_AUTH ─▶ PLACED ─┼──▶ RELEASED ─▶ PICKED ─▶ SHIPPED ─▶ DELIVERED
                │                   │                  ▲                     │
                └──▶ CANCELLED      └──▶ CANCEL_REQUESTED                    └──▶ RETURNED
                                                       │
                                    the point of no return sits here
```

- **`CANCEL_REQUESTED` is a real state, not a flag.** It is the honest representation of "we have asked, and we don't know yet." The API returns `202` from it (§5).
- **The point of no return is `PICKED`, and it is named on the page and in the UI.** Before it, cancel is free and the compensation is a void plus a counter moving. After it, **cancel is a different product** — a return — with a different cost, a different flow, and a different customer message.
- **Every transition writes an `OrderEvent`** with actor, reason, and request id. `Order.state` is a materialization of the last event, not the source of truth.
- **Cancellation after the point of no return converts rather than fails.** The customer asked for their money back; the system's job is to route that to the mechanism that can deliver it, not to return an error.

### What it costs

**The UI has to tell the truth about a race**, which is a harder screen to design than a confirmation. "We're trying to cancel — we'll email you within a minute" tests worse than "Cancelled!" and is the only version that isn't occasionally a lie. **You also inherit a state machine that support tooling has to understand**, and every new fulfilment capability adds states to it — which is an argument for keeping the customer-visible state set small and deriving it from a richer internal one. And **the event log grows unboundedly**: ~13M orders/day with a dozen events each is ~160M rows/day, which is why §12 gives it a lifecycle rather than a table.

---

## 11 · Deep dive — authorize at place, capture at ship

### What you'd reach for first

Charge the card at Place Order. The customer bought it, take the money, done — one call, one state.

### What breaks

**You have taken money for goods you have not shipped and might not be able to.** Every unfulfillable line (§6B) then becomes a refund rather than a void, and **a refund costs the payment processing fee, which is not returned.** At ~2–3% of the transaction, on the fraction of orders that fail to fulfil, that is a real number being set on fire for no benefit.

**Partial shipments cannot be expressed.** A four-item cart routinely ships from three fulfilment centres over several days. One charge at placement means charging for items that ship next week, which in several jurisdictions you are not allowed to do, and which customers reasonably object to.

**And the authorization has a clock you didn't account for.** Card-not-present authorizations expire in about seven days (§3). An order that ships on day nine has no valid authorization left, and discovering that at the loading dock is the worst possible moment.

### What replaces it

**Authorize the full quoted amount at Place Order; capture per shipment at ship; void the remainder; re-authorize before expiry.**

- **Authorization at placement** proves the money exists and reserves it against the customer's credit line without moving it. It is voidable at zero cost, which is what makes it safe to do *before* the commit point in §9's ordering.
- **Capture is per shipment**, keyed idempotently on `(authorization_id, shipment_id)` so our own retries are safe — the same derived-key discipline `Billing §10` applies to its invoice attempts. Each capture reduces the authorization's remaining balance.
- **The final shipment voids the remainder**, which is how a cancelled line stops costing anything.
- **A re-authorization job runs against orders whose authorization expires within 48 hours** and which haven't fully shipped. ~390k/day at the assumed 3% backorder rate (§3) — a real component with a real decline path. **The decline path holds the shipment rather than shipping and hoping**, because a held shipment is recoverable and an unpaid one is a collections problem.
- **Capture failure after shipping keeps the shipment** and records the shortfall as debt, per §6D. `Ticketmaster §11` and `Uber §9` both land on this rule for the same reason: a payment failure must never undo a commitment a human is already acting on.

**The alternative worth naming, because it's what a marketplace does:** capture everything at placement and hold the funds in a pending balance until fulfilment, releasing to the seller at ship. That is the right answer when *you* are the platform and the money must be held anyway — and it's exactly the shape the payment-processor page is built around. Here, where we are the merchant and the money is simply ours once earned, authorize-and-capture-later is cheaper and less regulated.

### What it costs

**Customers see a pending authorization** for the full amount, which on a debit card reduces their available balance for days and generates support contacts that are entirely about a thing working correctly. **Partial capture support varies by processor and by card network**, so the design has a per-processor capability matrix and a fallback to void-and-re-authorize where partial capture isn't available — genuinely annoying, and worth naming because it's the sort of vendor reality that separates a designed system from a drawn one. And **the re-authorization decline path is a customer-hostile moment by construction**: someone who ordered nine days ago is being asked for a card again, and the design's job is to make that email arrive before the promised delivery date, not after.

---

## 12 · Data model, sharding, and storage decisions

**Two partition keys, and the gap between them is why this page exists.** Orders, carts, and checkout sessions shard by **`customer_id`** — every customer-facing read ("my orders", "my cart", "this order's status") is then a single-shard query, and a customer is a natural, evenly-distributed, non-hot key. Inventory shards by **`sku`**, because its access pattern is entirely per-SKU decrements and its contention profile is per-SKU. **These two keys cannot be reconciled**, and that is not a flaw to fix: it is the structural fact that makes the saga in §9 necessary rather than optional. A candidate who notices it unprompted has understood the problem.

**The hot shard is a SKU, not a customer.** There is no whale customer — the largest account is one person ordering a few times a week. The hot partition is a Lightning Deal SKU at ~1,600 attempts/s (§3), and it is **intentional and routed**: those SKUs move to the pre-sharded allotment mechanism from §7 rather than being allowed to define the general case.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Cart** | Read and write per customer, long-lived, tiny, no money | Loss is survivable | **DynamoDB**, partition key `customer_id` | "A cart holds intents, not prices, so it can be an eventually-consistent blob. Losing one is annoying, not incorrect" |
| **CheckoutSession + Quote** | Written a few times over minutes, read at submit, then dead | Must not be lost mid-checkout | **DynamoDB with a TTL** on `expires_at` | "Short-lived and money-shaped. The TTL is the whole lifecycle — no sweeper" |
| **Available-to-promise** | Conditional decrements per `(sku, fc)`, ~1.5k/s peak | Correctness-critical, but reconciled physically | **DynamoDB conditional writes**, key `sku`, sort key `fc_id` | "One conditional update per line, sharded by SKU. The condition *is* the correctness; no lock is ever taken" |
| **Inventory reservations** | Written with the order, expired lazily | Recoverable — expiry is a predicate | Same table, item per reservation with `expires_at` | "A reservation is a row with an expiry, evaluated by the next writer — Ticketmaster's mechanism with a quantity instead of a status" |
| **Orders, lines, payment refs, outbox** | ~150 writes/s, single-shard reads by customer | **Zero acknowledged loss.** No degraded mode | **Postgres + Citus**, sharded by `customer_id`, synchronous replica | "A hundred and fifty writes a second of money-adjacent state wants the most boring, most auditable transactional engine available — and the outbox has to be in the same transaction, which rules out anything that isn't" |
| **Order events** | Append-only, ~160M rows/day, read by support and disputes | 7-year retention | Same Postgres for 90 days, then **S3 in Parquet**, queried by Athena | "Append-only, and the current state is a materialization of it. Support reads the recent tail; disputes read the archive" |
| **Idempotency keys** | Read-before-write on every Place Order | **A lost key is a duplicate order** | **DynamoDB**, TTL 24 h, strongly consistent reads | "The one cache whose miss is a correctness bug, so it isn't a cache — it's a small strongly-consistent store with a TTL that outlives any client's retry budget" |
| **Order event stream** | Fan-out to fulfilment, notifications, analytics | At-least-once, replayable | **Kafka**, keyed by `order_id`, 7-day retention | "Keyed by order id so one order's events stay ordered, which is the only ordering guarantee any consumer actually needs" |
| **Payment authorizations** | Written at placement, updated per capture | Must survive; reconciled daily against the processor | **Postgres**, same cluster as orders | "Its own entity with its own expiry, because an order can outlive several authorizations" |
| **Order history search** | "Find my order from March" | Derived, rebuildable | **OpenSearch**, fed from the event stream | "Derived and rebuildable from Kafka, so it's allowed to be down" |

### Data lifecycle — the append-only entities

| Entity | Hot | Warm | Cold | Why the boundary is there |
|---|---|---|---|---|
| **Order + lines** | 90 days in Postgres, ms reads | 2 years in Postgres, partitioned by month | 7 years in S3 Parquet, seconds to query | Returns run 30–90 days; disputes and chargebacks reach back years; tax authorities reach back seven. **The 7-year floor is a legal obligation, not a preference** |
| **Order events** | 90 days | — | 7 years in S3, Athena | Support handles the recent tail; everything older is answering a dispute, where seconds of query latency is fine |
| **Payment authorizations** | 1 year | — | 7 years, alongside the orders | Chargeback windows under card-network rules run to 540 days in some categories, so a year of hot is not generous |
| **Carts / sessions** | Live only | — | **Deleted** | A cart is not a record of anything. Sessions TTL out at 15 minutes and quotes with them |

**Restore cost, stated:** rebuilding order history search from Kafka is hours; restoring an archived order is a single Athena query. **The order store itself has no restore story that is acceptable** — that's what "does not survive loss of the order store" in §2 means, and it's why it is the one component with a synchronous replica.

---

## 13 · Traps — the ranked list

**Design traps**

1. **Reaching for a distributed transaction.** It is the instinct that correctness requires atomicity, and it is unavailable here because one participant is a building. Naming 2PC to reject it, with the reason, is good; proposing it is the single clearest way to fail this problem.
2. **Charging the card before securing inventory.** Produces the worst outcome the system can produce — a charged customer with nothing to ship — and it costs a fee that never comes back. Reversible first, always.
3. **Capturing at placement instead of at ship.** Turns every unfulfillable line into a refund, cannot express partial shipments, and in several jurisdictions isn't legal.
4. **Ignoring authorization expiry.** Seven days, and ~3% of orders don't ship inside it. Discovering that at the loading dock is a design that never asked what an authorization actually is.
5. **Modelling cancel as a synchronous transition.** It races a physical process. `202` and `CANCEL_REQUESTED` are the honest API; `200 CANCELLED` is occasionally a lie, and the customer finds out when a box arrives.
6. **No point of no return.** If the design can't name the moment cancellation stops being free, it hasn't modelled the warehouse at all.
7. **Storing prices on the cart.** The total then depends on when each item was added, and a pricing change has to invalidate 400M carts.
8. **Letting the client submit a total.** The client submits a quote id. Anything else is a mischarge waiting for a screenshot, and a trivially exploitable API.
9. **A random client-generated idempotency key.** It makes the client responsible for recognising its own retry, which is the one thing a client with a flaky network cannot do. Derive it from the checkout session.
10. **Publishing to fulfilment outside the order transaction.** Classic dual write: the order commits, the publish fails, and the box is never picked. The outbox row goes in the same transaction or the design has a silent hole.
11. **Per-unit inventory rows.** Billions of rows maintaining an identity the customer never selects.
12. **Claiming zero oversell.** It requires reserving on add-to-cart, which strands stock across every abandoned cart. The target is a measured number with a compensation path.
13. **Letting the Lightning Deal define the mechanism.** Under 0.01% of order lines. Route it to Ticketmaster's design; don't pay its cost on everything else.
14. **A single `payment` column on the order.** Cannot express re-authorization, partial capture, or a second attempt after a decline.
15. **Deleting a cancelled order.** The one object disputes and support most need is the sequence of what happened.

**Performance traps**

16. **Recomputing the full price fan-out on every checkout render.** Pricing, promotions, tax vendor, and shipping on the one path with a latency budget.
17. **Holding an inventory lock across the payment call.** Puts a third party's p99 inside your database's lock hold time.
18. **A synchronous call to fulfilment on the request path.** It's a system you don't control, and the outbox exists precisely so you don't have to wait for it.
19. **Fanning out an in-stock check across ~180 fulfilment centres per page view.** Cache it with a short TTL and let it be approximate — it's a hint, and the reservation is the only source of truth.
20. **An unbounded order-event table.** ~160M rows/day. It needs a lifecycle before it needs an index.

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

21. **Spending the round on inventory.** It's the part that looks like the hard part because Ticketmaster made it the hard part, and here it's a conditional update against a counter with contention near one. The interviewer chose this problem for the saga and for the money-versus-goods gap; the numbers in §3 are how you know that, and quoting them is how you tell the interviewer you know it too.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 586" role="img" aria-label="Amazon checkout five-minute skeleton. Rows for the cart and the quote, the idempotent Place Order call, the reserve and authorize pair, the single commit transaction spanning the full width, the outbox to fulfilment, the pick as the point of no return, and capture per shipment. A margin lane below carries the two partition keys, the oversell target, and the order rate.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-box" x="30" y="68" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="92.5">Cart — DynamoDB by customer_id</text>
  <text class="dg-s dg-c" x="260" y="108.5">a list of intents. NO PRICES</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="510" y="68" width="450" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="92.5">Checkout session + quote</text>
  <text class="dg-s dg-c" x="735" y="108.5">server-minted total, 15-min TTL</text>
  <circle class="dg-num" cx="510" cy="68" r="9"></circle>
  <text class="dg-num-t" x="510" y="71.4">2</text>
  <rect class="dg-box" x="30" y="144" width="930" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="168.5">POST /orders   Idempotency-Key = the checkout session id — derived, not random</text>
  <circle class="dg-num" cx="30" cy="144" r="9"></circle>
  <text class="dg-num-t" x="30" y="147.4">3</text>
  <rect class="dg-box" x="30" y="204" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="228.5">Reserve inventory</text>
  <text class="dg-s dg-c" x="260" y="244.5">UPDATE ... WHERE on_hand - reserved &gt;= qty</text>
  <circle class="dg-num" cx="30" cy="204" r="9"></circle>
  <text class="dg-num-t" x="30" y="207.4">4</text>
  <rect class="dg-box" x="510" y="204" width="450" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="228.5">Authorize payment</text>
  <text class="dg-s dg-c" x="735" y="244.5">reversible — a void costs nothing</text>
  <circle class="dg-num" cx="510" cy="204" r="9"></circle>
  <text class="dg-num-t" x="510" y="207.4">5</text>
  <rect class="dg-good" x="30" y="280" width="930" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="304.5">COMMIT: order + lines + payment ref + event + OUTBOX ROW — one local transaction</text>
  <text class="dg-s dg-c" x="495" y="320.5">this is the atomic point of the whole design</text>
  <circle class="dg-num" cx="30" cy="280" r="9"></circle>
  <text class="dg-num-t" x="30" y="283.4">6</text>
  <rect class="dg-box" x="30" y="356" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="380.5">Outbox pump → Kafka</text>
  <text class="dg-s dg-c" x="180" y="396.5">order.placed, keyed by order_id</text>
  <circle class="dg-num" cx="30" cy="356" r="9"></circle>
  <text class="dg-num-t" x="30" y="359.4">7</text>
  <rect class="dg-warn" x="350" y="356" width="300" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="500" y="380.5">Fulfilment picks</text>
  <text class="dg-s dg-c" x="500" y="396.5">POINT OF NO RETURN, ~30 min</text>
  <circle class="dg-num" cx="350" cy="356" r="9"></circle>
  <text class="dg-num-t" x="350" y="359.4">8</text>
  <rect class="dg-box" x="670" y="356" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="380.5">Capture per shipment</text>
  <text class="dg-s dg-c" x="815" y="396.5">re-auth anything past 7 days</text>
  <circle class="dg-num" cx="670" cy="356" r="9"></circle>
  <text class="dg-num-t" x="670" y="359.4">9</text>
  <rect class="dg-good" x="30" y="432" width="930" height="40" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="456.5">Compensations, not rollbacks — void or refund plus an email; a lost cancel race is a return label</text>
  <circle class="dg-num" cx="30" cy="432" r="9"></circle>
  <text class="dg-num-t" x="30" y="435.4">10</text>
  <text class="dg-lane" x="30" y="500">IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="512" width="300" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="530.5">Two partition keys</text>
  <text class="dg-s dg-c" x="180" y="546.5">customer_id vs sku — WHY there's a saga</text>
  <rect class="dg-box" x="350" y="512" width="300" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="530.5">Oversell is a number</text>
  <text class="dg-s dg-c" x="500" y="546.5">2 per 10,000 lines, with an owner</text>
  <rect class="dg-box" x="670" y="512" width="290" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="530.5">~150 orders/s</text>
  <text class="dg-s dg-c" x="815" y="546.5">so this was never a scale problem</text>
</svg>
</div>

<p class="diagram-cap">Badge 6 is the one to draw first and the one to defend: a single local transaction that carries the outbox row with it. Everything above it is chosen for being cheap to undo, and everything below it is chosen for being retried until it lands.</p>

1. **Cart** — a list of SKUs and quantities in DynamoDB, keyed by customer. **No prices.** Long-lived, cheap, allowed to be eventually consistent.
2. **Checkout session + quote** — server-minted total with a 15-minute TTL. The client submits a `quoteId`, never a number. A stale quote is a `409` and a re-confirm, never a silent mischarge.
3. **`POST /orders`, `Idempotency-Key` = the session id.** Derived, not random. The double-click never reaches step 4.
4. **Reserve inventory** — one conditional `UPDATE … WHERE on_hand - reserved >= qty` per line, sharded by SKU. Cheap, reversible, first. Reservations expire lazily.
5. **Authorize payment** for the quote total. Reversible — a void costs nothing. Second.
6. **Commit the order** — one local transaction: order, lines, payment reference, first event, **and the outbox row**. **This is the atomic point of the whole design; draw the line here.**
7. **Outbox pump → Kafka `order.placed`**, keyed by order id. At-least-once, idempotent consumer.
8. **Fulfilment picks, packs, ships.** Not reversible. The **point of no return is the pick**, ~30 minutes in.
9. **Capture per shipment** on `shipment.shipped`, key derived from `(auth, shipment)`. Void the remainder on the last one. Re-authorize anything not shipped inside 7 days.
10. **Compensations, not rollbacks** — an unfulfillable line is a void-or-refund plus an email; a lost cancel race is a return label.

**In the margin — said, not drawn:** the two partition keys (`customer_id` for orders, `sku` for inventory) and the fact that their incompatibility is *why* there's a saga · the oversell target of 2 per 10,000 lines, as a number · "cancel is a race we can lose, and the API says `202` because of it" · ~150 orders/s, which is why none of this is a scale problem.

---

## 15 · Variants — what actually changes

**The axis that governs this family: how long the gap is between taking the money and handing over the goods, and whether the handover can be undone.** Everything on this page — the quote, the saga ordering, the state machine, authorize-versus-capture — is machinery for surviving that gap. When the gap is zero and the handover is reversible, all of it collapses.

| Product | Money-to-goods gap | What changes |
|---|---|---|
| **Digital download / software licence** | **Zero, and fully reversible** | **The entire page collapses.** No inventory (infinite), no reservation, no saga, no capture-at-ship — charge and grant in one transaction, because for the first time all the state is yours. Revocation is an entitlement flip. This is the cleanest proof that the difficulty here comes from the physical step and nothing else |
| **Amazon retail — this page** | **Hours to days, irreversible once picked** | The full machinery: reserve, authorize, commit, ship, capture per shipment |
| **Grocery / food delivery** | **Minutes, irreversible and perishable** | The window is so short that cancellation is essentially never free, and **substitution replaces compensation** — the customer approves a swap in real time rather than getting an apology afterwards. Weight-variable items mean the final total differs from the quote by design, which inverts §8: the quote becomes an estimate plus an authorized ceiling |
| **Marketplace with third-party sellers** | Days, and **you don't control the handover** | You are no longer the merchant, so the money must be *held* rather than earned — capture at placement into a pending balance and pay the seller after delivery. **That's the payment-processor page's model, and it's why marketplaces build one.** Disputes now have three parties |
| **Ticketed event inventory** | Zero gap, but **inventory is non-fungible and contended** | §7 inverts completely — a seat map, a hold as a user action, and a thundering herd. **That's `Ticketmaster`**, and the contrast is the most useful one on this page: same money flow, opposite inventory |
| **Made-to-order / preorder** | **Weeks to months** | Authorization expiry stops being an edge case and becomes the primary mechanism — you cannot hold an auth for six weeks, so you charge a deposit at placement and the balance at ship, and §11 splits into two payment events with a legal difference between them |

**The lesson:** every one of these has a cart, a quote, a commitment, and a handover, and if you've built one you can draw all six. The only question that reorganizes the design is **how much time and irreversibility sits between the money and the goods** — and when the answer is "none," this stops being a distributed systems problem at all.
