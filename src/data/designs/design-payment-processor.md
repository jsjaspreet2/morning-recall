# Design a Payment Processor — Money Movement & Settlement

## The question

> *"Design Stripe. Merchants integrate an API, their customers pay by card, and at some point the merchant's bank account has money in it that wasn't there before."*

**The product.** A business wants to take money from its customers and would rather not build any of what that requires. They add a few lines of code, and from then on: a customer's card is charged, the business can see the payment appear, refund it if they need to, and every couple of days a deposit lands in their bank account with a statement explaining exactly what it was made of. When a customer calls their bank and says "I didn't buy this," the business hears about it in time to argue, and knows what happens to the money if they lose.

**What a working system delivers**

- The charge either happened or it didn't, and a retry after a lost connection never produces a second one.
- The balance shown is the money that actually exists, split into what has settled and what hasn't, and every number in it can be traced to something that happened.
- A refund of a payment from three weeks ago works, and works for part of it.
- The deposit that arrives on Thursday is explainable to the cent: these payments, minus these fees, minus this refund.
- A disputed payment surfaces with enough time to respond, and the outcome — either way — shows up in the balance without anyone reconciling a spreadsheet.

**Why this gets asked.** Nothing here is allowed to be approximately right, the money spends days inside systems that answer slowly and sometimes not at all, and the most common operation in the whole product — a client that didn't get a response and tries again — is also the one that most easily takes someone's money twice.

---

**Archetype:** money movement & settlement — exactly-once movement of real funds through rails you don't own, where the books must balance to the cent and every retry is a potential double charge.
**Cousins that reuse ~70% of this page:** Adyen, Braintree, Square, PayPal, Checkout.com; any marketplace that holds funds for two parties (Shopify Payments, Uber's driver payouts); neobank and wallet ledgers; brokerage cash management; and, with the rails renamed, ACH and real-time-payment platforms.

**What's actually being graded:** whether you know that **a balance is a query, not a column.** Almost everyone models merchant funds as a number that goes up and down. That design cannot answer "why is my balance this," cannot be audited, cannot detect a double-applied event, and serializes every whale merchant onto one row. The answer is **double-entry bookkeeping: money is only ever moved between accounts in balanced groups, entries are inserted and never updated, and every balance in the product is derived from them.** Getting to that, and stating the invariant — *every transfer sums to zero, so the whole system sums to zero* — is most of the answer.

**The second admission that scores, and it's the inverse of a claim most candidates make:** *an authorization is not money.* Money moves at settlement, a day or two later, in a file from the acquirer. Everything between the `200 OK` and that file is a promise, and a design that credits a merchant's spendable balance on the authorization has invented funds that do not exist yet.

**The contrast to have ready:** *the LLM API billing page's §10 treats a payment processor as four named failure modes behind an opaque API — the unknown-outcome timeout, retries without a stable key, webhooks that arrive twice and out of order, and state that originates on the processor's side days later. This page is the other side of every one of those sentences. That page has to defend against a black box; this one has to be a black box worth trusting, which means owning the idempotency store, being the sender of those webhooks, and being the party that knows about a dispute first.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "Three things live here and they want different properties. **Authorization** is synchronous, sits inside somebody else's checkout — so I've got maybe a second, and most of that is the card network. **The ledger** is the system of record: double-entry, append-only, and it's where I'll spend most of my time, because the invariant that every transfer sums to zero is what makes everything else auditable. **Settlement and payout** are batch, days long, and driven by a file from the acquirer rather than by anything I control. Joining them: **an authorization is not money** — nothing reaches a merchant's spendable balance until settlement says it did. I'd like to go deep on the ledger and on idempotency from the server side, since I'm the one storing the keys rather than sending them. I'll treat card-network internals, the acquiring relationship, fraud scoring, tax, and KYC and onboarding as named subsystems and leave them out."

**Why open this way:** it separates three subsystems that candidates habitually merge, it pre-commits the one dive with no prior art anywhere else in this repo, and it plants *an authorization is not money* in the first minute — which is the sentence the rest of the hour keeps collecting on.

---

## 1 · Functional requirements

1. **Take a payment** — accept a charge request from a merchant, authorize it against the card networks, capture it, and do all of that **exactly once** no matter how many times the merchant's client retries.
2. **Keep the books** — maintain a double-entry ledger from which every merchant-visible balance is derived, and reconcile it daily against what the acquirer says actually moved.
3. **Move money out** — refunds and disputes back toward the cardholder, payouts to the merchant's bank on a schedule, with reserves held against money that may have to come back.

Requirement 1 says *exactly once* about an operation whose failure mode is a network timeout at a third party. That makes it a correctness invariant, not a feature, and §7 is where it gets paid for.

**Out of scope (say them):** the card networks' own internals — message formats, routing, and the issuing side are a different industry and you should say the words *ISO 8583* once and move on; the acquiring relationship and interchange rate negotiation; fraud and risk scoring, which is a model this flow calls and blocks on; KYC, onboarding, and underwriting; tax; PCI *certification* as a program (the architectural consequence is in §2 and §12); currency conversion and treasury; and the merchant's own checkout — **that's its own page, and it's the inverse of this one.**

**Below the line, likely follow-ups:** 3-D Secure and the SCA liability shift, network tokens and account updater, multi-currency presentment and settlement, split payments to connected accounts, subscriptions and stored-credential rules, smart retries on soft declines, and instant payouts.

**Why the scope line matters more here than on most pages:** "design Stripe" invites a tour of the payments industry, and a candidate who spends fifteen minutes on interchange has spent it on domain trivia rather than on system design. Naming the networks as a boundary you call — and then designing everything on your side of it properly — is the choice that leaves room for the ledger.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Exactly-once charge creation** | **Zero double charges** from client retries, enforced by a `(merchant, idempotency-key)` record written **before** the money call, with a documented **24 h** minimum retention | The single defining requirement. A double charge is the failure that ends the relationship, and the retry that causes it is the correct client behavior — so the guarantee has to live on our side |
| **Ledger integrity** | **Every transfer sums to zero; the global sum per currency is zero, checked continuously.** Append-only, no `UPDATE`, ever | This is the invariant that makes the product auditable at all. It is cheap to check and it catches classes of bug — a partially applied transfer, a double-applied event — that no amount of testing finds |
| **Authorization latency** | **p99 ≤ 1 s end to end**, of which the network round trip is 300–600 ms and ours is **≤ 150 ms** | We sit inside the merchant's Place Order, which the Amazon checkout page budgets at p99 800 ms for the whole saga. **Our budget is set by somebody else's page**, and saying so is the correct framing |
| **Availability — authorization** | **99.99%**, and **it fails closed** | Everywhere else in this repo the answer is fail open. Here failing open means approving a payment we cannot prove was authorized, and eating it. A decline is recoverable; a fabricated approval is not |
| **Balance freshness** | Merchant-visible balance **≤5 s** behind the ledger; **exact and reconciled at payout time** | Merchants watch payments land. Five seconds is a product choice; the payout number is the one that must be exact, and it is computed from the ledger, never from the cache |
| **Settlement reconciliation** | **Daily, three-way** — our ledger ↔ the acquirer's settlement file ↔ our bank account — with **zero unexplained variance carried past 48 h** and an exception queue that has an owner | The mechanism is argued in full on the LLM API billing page, `§11`. What's added here is the settlement file itself, which that page treats as a black box: it arrives daily, it is the truth about money moved, and its fee lines are the difference between gross and net |
| **Webhook delivery** | **≥99.9% delivered within 60 s**; retried with backoff for **3 days**; **at-least-once and unordered, and documented that way** | ~220M deliveries/day (§3). Promising ordering would be a lie we'd have to maintain forever; promising at-least-once and telling merchants to fetch current state is the honest contract — and it is exactly what `Billing §10` does on the receiving end |
| **Dispute response** | Evidence submitted before the network deadline for **100%** of disputes, with alerts at **7 days** and **2 days** remaining | Missing a network deadline is an **automatic loss** regardless of merits. It is the one deadline in the system enforced by someone else, and a timer that fires late costs the full transaction |
| **Fault tolerance** | Survives loss of the **webhook senders** (deliveries queue and replay), the **balance cache** (recomputed from the ledger), and **payout processing** (money accrues). **Does not survive loss of the ledger** | The ledger is the one component with no degraded mode. Naming it forces the storage choice in §12 and the archive policy — and a design where everything degrades gracefully has not been sized under failure |
| **Card data** | **PANs exist only inside the vault**, tokenized at a hosted field; the ledger, the API tier, and every log carry a token. PCI **SAQ-D / Level 1** | Merchants integrate with us *specifically* so they can stay at SAQ-A — the position the LLM API billing page argues for in its `§5`. **We are the counterparty that makes their SAQ-A possible**, so the compliance burden is the product, not an overhead |

**The sentence that earns the point:** *"The core of this system is a double-entry ledger, and everything else is either a way of getting events into it or a view derived from it. A merchant's balance is a query over entries, not a column I update — because a column can tell you a number and it can never tell you why, and 'why' is what a dispute, an audit, and an angry founder on a Saturday are all actually asking."*

---

## 3 · Numbers that reframe the problem

**Assume** ~$1T/year of gross payment volume across ~100k merchants, an average transaction of ~$50, and a T+2 settlement cycle. All three are assumptions; every figure below derives from them and each changes a decision.

**Transaction rate — and why it isn't the story**

- **$1T/yr at $50 = ~20B transactions/year = ~640/s average, ~5,000/s on Black Friday** (assume an 8× peak). **That is not a large number of writes**, and saying so early is what stops the round becoming a sharding exercise. The difficulty is not volume; it is that each of those 640 has to be exactly right, twice — once when it happens and once when the money actually moves.

**The ledger is the volume, and it's ~8× the transaction rate**

- **A single $50 payment produces about eight ledger entries over its life**: three at capture (clearing debit, merchant payable credit, fee revenue credit), two when settlement confirms, two at payout, and one more on average for the refunds and disputes spread across all payments. **~640/s × 8 ≈ 5,100 entries/s, ~440M rows/day, ~160B rows/year.** *This is the number that picks the ledger's storage and its partitioning*, and it's the number that separates this page from the LLM API billing page, whose ledger moves **55 entries/s** because it aggregates an hour of metering into one row. **Same structure, four orders of magnitude apart, and the reason is that here every entry is a distinct real-world money movement that someone can dispute individually.**

**The float — the number that makes this a regulated business**

- **T+2 on $1T/year means ~$5.5B of other people's money is inside the system at any moment** ($1T ÷ 365 × 2). That single figure is why payouts have schedules rather than being instant, why reserves exist, and why the ledger's integrity is a legal requirement and not an engineering preference. **Quote it when someone asks why you don't just pay merchants immediately.**

**Disputes — the number that sizes the reserve**

- **Card networks put a merchant into a monitoring program at roughly 0.9% dispute rate**, and *assume* a healthy portfolio averages ~0.1%. At $1T/yr that's **~$1B/year in disputed volume** flowing backwards through the system, arriving **up to 540 days after the payment**. A design that pays out 100% of a merchant's balance on schedule has no way to claw that back from a merchant who has since disappeared — **which is the entire argument for reserves, and it's a number, not a policy preference.**

**Webhooks — the number that forces per-endpoint isolation**

- **~55M charges/day × ~4 lifecycle events = ~220M deliveries/day ≈ 2,500/s**, before retries. Merchant endpoints are code we don't control with latencies we can't predict; **assume 1% of endpoints are slow or down at any moment.** On a shared worker pool with a 30 s timeout, **that 1% consumes the pool** and the other 99% stop receiving anything. *Head-of-line blocking by a stranger's server is the failure mode §10 exists to prevent*, and it's why delivery is partitioned by endpoint rather than by event.

**Money type — and the contrast worth drawing**

- **Every amount is an integer in the currency's minor unit** — cents, yen, fils — because that is the unit the card networks settle in, and there is no such thing as a fraction of one moving between banks. This is the *opposite* of the LLM API billing page, which needs nano-dollars because a single API call costs a fraction of a cent. **Two money systems, two money types, and each is wrong for the other**: nano-dollars here would invent precision the rails cannot express, and cents there would round every request to zero.

---

## 4 · Core entities

- **Merchant** — id, country, settlement bank account, payout schedule, reserve policy, risk state
- **PaymentMethod** — a **token** referencing a vaulted card. The PAN exists in one place and this is not it
- **PaymentIntent** — merchant, amount, currency, state, the idempotency key that created it, the authorization it holds
- **Authorization** — network auth code, amount, `expires_at`, amount captured so far
- **Capture / Refund** — each a discrete money event with its own id, its own idempotency key, and its own ledger transfer
- **Account** — `(merchant_id | platform, type)` where type ∈ `pending · available · reserve · fee_revenue · network_cost · loss · clearing`
- **Transfer** — the atomic unit of the ledger: a group of entries that **sums to zero**, with a source event id and a reason
- **LedgerEntry** — transfer, account, signed `amount_minor`, currency, `posted_at`. **Inserted, never updated**
- **IdempotencyRecord** — `(merchant_id, key)`, request hash, state (`in_flight | complete`), stored response, `expires_at`
- **Dispute** — the payment, the network reason code, the evidence deadline, state, outcome
- **Payout** — merchant, amount, bank rail reference, state, the settlement window it covers
- **WebhookEndpoint / WebhookDelivery** — url, signing secret, health; per-attempt state and `next_attempt_at`
- **SettlementRecord** — a line from the acquirer's daily file: what actually moved, gross, fees, net

**Load-bearing details:**

- **`Transfer` is the unit, not `LedgerEntry`.** Entries are never written alone. A capture is one transfer of three entries, and it commits atomically or not at all. **The invariant — `SUM(amount) = 0` per transfer, therefore zero across the whole ledger per currency — is checkable in one query, continuously, and it is the cheapest possible detector for a whole class of bugs.** A partially applied transfer, a double-consumed event, a bad migration: all of them break the sum, and nothing else in the system would notice.
- **`Account` types are the design.** `pending` is captured money the network hasn't settled yet. `available` is settled money the merchant can be paid. `reserve` is money we are holding back against future disputes. `fee_revenue`, `network_cost`, and `loss` are ours. **A merchant's "balance" is not one number** — it is at least three, and the product surfaces them separately because they mean genuinely different things about when the money can be spent.
- **`IdempotencyRecord` is written before the side effect, not after**, and it carries a `request_hash` and an `in_flight` state. Writing it afterwards is a design that has no answer for a crash mid-charge; without the hash there is no way to distinguish a retry from a different request that reused a key. See §7.
- **`Authorization` is separate from `PaymentIntent`** and carries its own expiry, because one intent can outlive several authorizations — a re-authorization on a delayed shipment is the merchant-side story on the Amazon checkout page's `§11`, and this is the entity that makes it expressible.
- **`SettlementRecord` is the truth about money, and our ledger is a claim about money.** They are reconciled daily and **the settlement file wins** on anything about whether funds moved. The LLM API billing page treats this file as an opaque input to reconciliation; here it is a first-class entity, because we're the party that reads it line by line.

---

## 5 · API

```http
# Merchant-facing — every money-mutating call requires an Idempotency-Key
POST   /v1/payment_intents          { amount, currency, payment_method, capture: auto|manual }
                                    Idempotency-Key: {merchant-chosen}
                                    → 201 { id, status, amount_capturable }
POST   /v1/payment_intents/{id}/capture   { amount? }        Idempotency-Key: required
POST   /v1/payment_intents/{id}/cancel                       Idempotency-Key: required
POST   /v1/refunds                  { payment_intent, amount? }  Idempotency-Key: required

GET    /v1/balance                  → { available[], pending[], reserved[] } per currency
GET    /v1/balance_transactions     → the ledger, as the merchant sees it — cursor-paginated
GET    /v1/payouts/{id}             → amount, arrival date, and the transactions it covers

POST   /v1/webhook_endpoints        { url, enabled_events[] } → { id, signing_secret }
GET    /v1/events                   → the same events, pollable. The backstop for §10

POST   /v1/disputes/{id}/evidence   { files[], text }        deadline enforced by the network

# Us → the acquirer                 authorization, capture, refund, reversal advice
# The acquirer → us                 daily settlement file (SFTP/S3), and dispute notifications
```

**Decisions to narrate, unprompted:**

- **`Idempotency-Key` is required, not optional, on every money-mutating call** — and it is scoped to the merchant, so two merchants can both use `"1"` without colliding and neither can probe the other's. A missing key is a `400`. **Making it mandatory is a product decision that prevents a whole category of merchant bug**, and it costs nothing but an error message.
- **A key reused with a different body returns `409`, never the first response.** Silently replaying the old response for a *different* request is a data-loss bug in the caller's code that we would be hiding. `Billing §5` states the same rule from the client's side; here we are the one enforcing it.
- **Capture is a separate call, and `amount` is optional.** Partial capture is what lets a merchant ship half an order and charge for half — the Amazon checkout page's `§11` in API form. A single `charge` primitive cannot express it.
- **`GET /v1/events` exists because webhooks are not a guarantee.** Every event we send is also fetchable. **Say this out loud:** any design that treats webhook delivery as the only path has made a merchant's outage into permanent data loss.
- **`GET /v1/balance` returns three arrays, not one number.** `pending`, `available`, `reserved`. The API refuses to flatten a distinction the money actually has.
- **No endpoint anywhere accepts a PAN.** The card reaches the vault through a hosted field in the cardholder's browser and everything downstream carries a token — which is precisely the mechanism that keeps *our merchants* at PCI SAQ-A, and the reason they're integrating with us at all.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 810" role="img" aria-label="Payment processor architecture, split horizontally by the settlement boundary. A top row: the merchant's server calling the API tier, the card vault, and — in its own right-hand column — the acquirer. Above the boundary, a synchronous tier holding the idempotency claim in Postgres, colocated with the ledger, plus risk scoring, and authorization against the acquirer, which fails closed. At the center, the double-entry ledger in Postgres and Citus, with a Redis balance cache beside it. Below the boundary, an outbox feeding Kafka, the acquirer's daily settlement file in S3 with Object Lock, and three consumers: webhook senders partitioned by endpoint, daily three-way reconciliation, and payouts.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">The dashed line is the settlement boundary. Above it, permission. Below it, money that has actually moved.</text>
  <rect class="dg-box" x="20" y="100" width="170" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="105" y="126.5">Merchant server</text>
  <text class="dg-s dg-c" x="105" y="142.5">Idempotency-Key required</text>
  <rect class="dg-box" x="220" y="100" width="240" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="340" y="126.5">API tier</text>
  <text class="dg-s dg-c" x="340" y="142.5">every money call claims a key first</text>
  <rect class="dg-box" x="500" y="100" width="190" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="595" y="126.5">Card vault</text>
  <text class="dg-s dg-c" x="595" y="142.5">the only PAN in the system</text>
  <rect class="dg-box" x="790" y="100" width="190" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="885" y="126.5">Acquirer</text>
  <text class="dg-s dg-c" x="885" y="142.5">a black box you call</text>
  <path class="dg-line" d="M 190,130 L 212,130"></path>
  <path class="dg-head" d="M 212,135 L 212,125 L 220,130 Z"></path>
  <path class="dg-line" d="M 460,130 L 492,130"></path>
  <path class="dg-head" d="M 492,135 L 492,125 L 500,130 Z"></path>
  <path class="dg-line" d="M 340,160 L 340,188"></path>
  <path class="dg-head" d="M 335,188 L 345,188 L 340,196 Z"></path>
  <rect class="dg-group" x="20" y="196" width="740" height="140" rx="12"></rect>
  <text class="dg-group-t" x="36" y="218">SYNCHRONOUS — PERMISSION, NOT MONEY</text>
  <path class="dg-box" d="M 36,235 L 36,285 A 115,7 0 0 0 266,285 L 266,235 A 115,7 0 0 0 36,235 Z"></path>
  <path class="dg-box" d="M 36,235 A 115,7 0 0 0 266,235" style="fill:none"></path>
  <text class="dg-t dg-c" x="151" y="252">Postgres — claim</text>
  <text class="dg-s dg-c" x="151" y="268">(merchant_id, key), colocated</text>
  <text class="dg-s dg-c" x="151" y="284">written BEFORE the money call</text>
  <rect class="dg-box" x="290" y="228" width="170" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="375" y="256.5">Risk</text>
  <text class="dg-s dg-c" x="375" y="272.5">a terminal decline</text>
  <rect class="dg-box" x="484" y="228" width="260" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="614" y="248.5">Authorization</text>
  <text class="dg-s dg-c" x="614" y="264.5">300–600 ms · FAILS CLOSED</text>
  <text class="dg-s dg-c" x="614" y="280.5">timeout → reversal advice</text>
  <path class="dg-line" d="M 266,260 L 282,260"></path>
  <path class="dg-head" d="M 282,265 L 282,255 L 290,260 Z"></path>
  <path class="dg-line" d="M 460,260 L 476,260"></path>
  <path class="dg-head" d="M 476,265 L 476,255 L 484,260 Z"></path>
  <path class="dg-line" d="M 744,260 L 770,260 L 770,180 L 830,180 L 830,168"></path>
  <path class="dg-head" d="M 835,168 L 825,168 L 830,160 Z"></path>
  <text class="dg-s" x="36" y="322">A unique violation on the claim is not an error — it is the answer: complete replays, in_flight returns 409, a hash mismatch always returns 409.</text>
  <path class="dg-line" d="M 390,336 L 390,388"></path>
  <path class="dg-head" d="M 385,388 L 395,388 L 390,396 Z"></path>
  <path class="dg-good" d="M 230,403 L 230,465 A 220,7 0 0 0 670,465 L 670,403 A 220,7 0 0 0 230,403 Z"></path>
  <path class="dg-good" d="M 230,403 A 220,7 0 0 0 670,403" style="fill:none"></path>
  <text class="dg-t dg-c" x="450" y="426">Ledger — Postgres + Citus</text>
  <text class="dg-s dg-c" x="450" y="442">DR clearing / CR merchant:pending / CR fee_revenue</text>
  <text class="dg-s dg-c" x="450" y="458">double-entry, append-only, sharded by merchant_id</text>
  <path class="dg-box" d="M 20,403 L 20,465 A 90,7 0 0 0 200,465 L 200,403 A 90,7 0 0 0 20,403 Z"></path>
  <path class="dg-box" d="M 20,403 A 90,7 0 0 0 200,403" style="fill:none"></path>
  <text class="dg-t dg-c" x="110" y="426">Redis</text>
  <text class="dg-s dg-c" x="110" y="442">balance cache</text>
  <text class="dg-s dg-c" x="110" y="458">a SUM, never the payout</text>
  <path class="dg-line" d="M 230,434 L 208,434"></path>
  <path class="dg-head" d="M 208,429 L 208,439 L 200,434 Z"></path>
  <path class="dg-line" d="M 930,160 L 930,520"></path>
  <path class="dg-head" d="M 925,520 L 935,520 L 930,528 Z"></path>
  <text class="dg-lbl dg-c" x="950" y="350">daily file</text>
  <path class="dg-div" d="M 20,500 L 980,500"></path>
  <text class="dg-lane" x="20" y="494">THE SETTLEMENT BOUNDARY — AN AUTHORIZATION IS NOT MONEY</text>
  <rect class="dg-box" x="230" y="528" width="440" height="56" rx="8"></rect>
  <path class="dg-qbar" d="M 243,537 L 243,575"></path>
  <path class="dg-qbar" d="M 252,537 L 252,575"></path>
  <path class="dg-qbar" d="M 261,537 L 261,575"></path>
  <text class="dg-t dg-c" x="468" y="552.5">Kafka — outbox pump</text>
  <text class="dg-s dg-c" x="468" y="568.5">keyed by object id · at-least-once</text>
  <path class="dg-box" d="M 790,535 L 790,577 A 95,7 0 0 0 980,577 L 980,535 A 95,7 0 0 0 790,535 Z"></path>
  <path class="dg-box" d="M 790,535 A 95,7 0 0 0 980,535" style="fill:none"></path>
  <text class="dg-t dg-c" x="885" y="556">S3 Object Lock</text>
  <text class="dg-s dg-c" x="885" y="572">the settlement file</text>
  <path class="dg-line" d="M 560,472 L 560,520"></path>
  <path class="dg-head" d="M 555,520 L 565,520 L 560,528 Z"></path>
  <rect class="dg-group" x="20" y="620" width="960" height="118" rx="12"></rect>
  <text class="dg-group-t" x="36" y="642">ASYNCHRONOUS — MONEY ACTUALLY MOVING</text>
  <rect class="dg-box" x="36" y="652" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="186" y="672.5">Webhook senders</text>
  <text class="dg-s dg-c" x="186" y="688.5">partitioned by endpoint_id</text>
  <text class="dg-s dg-c" x="186" y="704.5">signed · 3-day backoff · circuit-broken</text>
  <rect class="dg-box" x="360" y="652" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="672.5">Reconciliation</text>
  <text class="dg-s dg-c" x="500" y="688.5">ledger ↔ file ↔ bank, daily</text>
  <text class="dg-s dg-c" x="500" y="704.5">an exception queue with an owner</text>
  <rect class="dg-box" x="664" y="652" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="814" y="672.5">Payouts</text>
  <text class="dg-s dg-c" x="814" y="688.5">available less reserve</text>
  <text class="dg-s dg-c" x="814" y="704.5">computed from the ledger, not the cache</text>
  <path class="dg-line" d="M 450,584 L 450,604 L 186,604 L 186,644"></path>
  <path class="dg-head" d="M 181,644 L 191,644 L 186,652 Z"></path>
  <path class="dg-line" d="M 930,584 L 930,604 L 500,604 L 500,644"></path>
  <path class="dg-head" d="M 495,644 L 505,644 L 500,652 Z"></path>
  <text class="dg-note" x="20" y="768">Only a line in the settlement file moves a transfer from merchant:pending to merchant:available. There is no code path that sets SETTLED from an HTTP response.</text>
  <text class="dg-s" x="20" y="790">Everything shards by merchant_id, which is why the payment row, the ledger transfer and the idempotency response commit in one local transaction — and why this page has no saga.</text>
</svg>
</div>

<p class="diagram-cap">Draw the dashed line first and label it: above it a card issuer is granting permission, below it banks are moving funds, and the two are days apart. The ledger spans both, and which account a transfer lands in — pending above, available below — is how it records which side of the line the money is on.</p>

**The two properties to point at before walking a payment through it:**

1. **The horizontal band is the settlement boundary.** Above it, everything is synchronous, sub-second, and about *permission* — an authorization is a promise from an issuer that money exists. Below it, everything is batch, daily, and about *money actually moving*. The ledger spans both, and the account a transfer lands in — `pending` above, `available` below — is how it records which side of the line it's on.
2. **Nothing on the request path writes to the ledger synchronously except the transfer that must be atomic with the charge.** The idempotency record and the transfer commit together in one local transaction; everything else — webhooks, balance materialization, analytics — hangs off the event stream downstream of it.

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 700" role="img" aria-label="The payment lifecycle as a sequence with its branches. Down the left: the API call, the idempotency claim, risk, authorization, and a single commit transaction. To the right of each, the ways it can end without money moving — a replayed response, a 409, a decline, a timeout that becomes a reversal advice rather than an approval. Below a divider, the money path: a transfer into pending, the settlement file moving it to available, and payout. A final band shows refunds, disputes and negative balances, each a new transfer rather than an edit.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Every branch above the divider ends without money moving. Below it, money moves — and only a file says so.</text>
  <rect class="dg-good" x="30" y="68" width="330" height="56" rx="8"></rect>
  <text class="dg-good-t dg-c" x="195" y="92.5">POST /v1/payment_intents</text>
  <text class="dg-s dg-c" x="195" y="108.5">Idempotency-Key required, or 400</text>
  <rect class="dg-box" x="430" y="68" width="540" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="700" y="84.5">the key already exists — two answers, never one</text>
  <text class="dg-s dg-c" x="700" y="100.5">complete  →  replay the stored response byte for byte</text>
  <text class="dg-s dg-c" x="700" y="116.5">in_flight  →  409 · a different request hash  →  409</text>
  <path class="dg-line" d="M 360,96 L 422,96"></path>
  <path class="dg-head" d="M 422,101 L 422,91 L 430,96 Z"></path>
  <rect class="dg-box" x="30" y="144" width="330" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="195" y="168.5">claim the key</text>
  <text class="dg-s dg-c" x="195" y="184.5">INSERT, and let the unique index decide</text>
  <rect class="dg-warn" x="430" y="144" width="540" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="700" y="168.5">the claim carries a lease</text>
  <text class="dg-s dg-c" x="700" y="184.5">without one, a crash wedges that key forever</text>
  <path class="dg-line" d="M 195,124 L 195,136"></path>
  <path class="dg-head" d="M 190,136 L 200,136 L 195,144 Z"></path>
  <path class="dg-line" d="M 360,172 L 422,172"></path>
  <path class="dg-head" d="M 422,177 L 422,167 L 430,172 Z"></path>
  <rect class="dg-box" x="30" y="220" width="330" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="195" y="244.5">risk</text>
  <path class="dg-line" d="M 195,200 L 195,212"></path>
  <path class="dg-head" d="M 190,212 L 200,212 L 195,220 Z"></path>
  <rect class="dg-box" x="30" y="284" width="330" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="195" y="308.5">authorize at the acquirer</text>
  <text class="dg-s dg-c" x="195" y="324.5">nothing is booked to the ledger yet</text>
  <rect class="dg-warn" x="430" y="284" width="540" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="700" y="300.5">the two failures, and they are not the same</text>
  <text class="dg-s dg-c" x="700" y="316.5">decline  →  terminal, no transfer, no retry</text>
  <text class="dg-s dg-c" x="700" y="332.5">timeout  →  reversal advice, REQUIRES_ACTION, never approved</text>
  <path class="dg-line" d="M 195,260 L 195,276"></path>
  <path class="dg-head" d="M 190,276 L 200,276 L 195,284 Z"></path>
  <path class="dg-line" d="M 360,312 L 422,312"></path>
  <path class="dg-head" d="M 422,317 L 422,307 L 430,312 Z"></path>
  <rect class="dg-good" x="30" y="360" width="940" height="56" rx="8"></rect>
  <text class="dg-good-t dg-c" x="500" y="384.5">COMMIT — intent + authorization + LEDGER TRANSFER + idempotency response + outbox row</text>
  <text class="dg-s dg-c" x="500" y="400.5">one local transaction, because everything shards by merchant_id</text>
  <path class="dg-line" d="M 195,340 L 195,352"></path>
  <path class="dg-head" d="M 190,352 L 200,352 L 195,360 Z"></path>
  <path class="dg-div" d="M 20,440 L 980,440"></path>
  <text class="dg-lane" x="20" y="434">BELOW HERE, MONEY MOVES</text>
  <path class="dg-line" d="M 280,416 L 280,456"></path>
  <path class="dg-head" d="M 275,456 L 285,456 L 280,464 Z"></path>
  <rect class="dg-box" x="30" y="464" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="488.5">transfer → merchant:pending</text>
  <text class="dg-s dg-c" x="180" y="504.5">visible, and not payable</text>
  <rect class="dg-good" x="360" y="464" width="300" height="56" rx="8"></rect>
  <text class="dg-good-t dg-c" x="510" y="488.5">the settlement file, T+1/T+2</text>
  <text class="dg-s dg-c" x="510" y="504.5">pending → available</text>
  <rect class="dg-box" x="690" y="464" width="280" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="830" y="488.5">payout, less reserve</text>
  <text class="dg-s dg-c" x="830" y="504.5">computed from the ledger</text>
  <path class="dg-line" d="M 330,492 L 352,492"></path>
  <path class="dg-head" d="M 352,497 L 352,487 L 360,492 Z"></path>
  <path class="dg-line" d="M 660,492 L 682,492"></path>
  <path class="dg-head" d="M 682,497 L 682,487 L 690,492 Z"></path>
  <text class="dg-lane" x="30" y="548">MONEY GOING BACK — EACH ONE A NEW TRANSFER, NEVER AN EDIT</text>
  <rect class="dg-box" x="30" y="562" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="586.5">refund, weeks later</text>
  <text class="dg-s dg-c" x="180" y="602.5">a reversing transfer</text>
  <rect class="dg-warn" x="360" y="562" width="300" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="510" y="586.5">dispute opens</text>
  <text class="dg-s dg-c" x="510" y="602.5">debit available immediately</text>
  <rect class="dg-warn" x="690" y="562" width="280" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="830" y="586.5">the balance goes negative</text>
  <text class="dg-s dg-c" x="830" y="602.5">legal — the payout stalls</text>
  <text class="dg-s" x="30" y="654">Every transfer sums to zero, so the whole ledger sums to zero. That query, run continuously, is the cheapest bug detector in the system.</text>
  <text class="dg-note" x="30" y="676">Nothing here is ever an UPDATE. A refund, a won dispute, a failed payout — each is new entries, and the originals stay exactly as they were.</text>
</svg>
</div>

<p class="diagram-cap">The three boxes across the top are the whole of §7: a claim written before the side effect, and a unique violation treated as an answer rather than an error. The divider is §9 — an authorization is not money, a capture is not money, and only a line in a file moves anything to available.</p>

### Flow A — a payment, from API call to settled funds

1. `POST /v1/payment_intents` arrives with an `Idempotency-Key`. **Step one is the idempotency claim** (§7): insert `(merchant, key)` with the request hash in state `in_flight`. A unique-violation here means this is a retry or a concurrent duplicate, and we answer from the stored record instead of proceeding.
2. Validate, resolve the payment-method token to a vaulted card **inside the vault's boundary**, and run risk. A risk decline is a terminal, non-retryable state.
3. **Authorize against the acquirer.** 300–600 ms, and it is the only synchronous external call in the flow. The response is an approval with an auth code, a decline with a network reason code, or — the case that matters — nothing.
4. On approval, **capture** (immediately for auto-capture merchants, later for manual).
5. **Commit one local transaction:** the `PaymentIntent` row, the `Authorization`, the **ledger transfer**, the terminal idempotency response, and an **outbox row** for the event stream. **This is the atomic point of the page.**
6. The transfer books the money into `pending`, not `available`:
   ```text
   DR  clearing:acquirer              5000
     CR  merchant:42:pending           4855
     CR  platform:fee_revenue           145
   ```
   **The merchant can see it and cannot be paid it**, which is the ledger encoding the fact that no money has actually moved yet.
7. The outbox pump publishes `payment_intent.succeeded`. Webhook delivery (§10), balance materialization, and analytics all consume from there. **Nothing in the customer's request waits for any of it.**
8. **T+1 or T+2, the acquirer's settlement file lands.** Each line is matched to a payment, and a second transfer moves the money from `pending` to `available` — and books the difference between our estimated fee and the actual interchange to `network_cost`. **This is the only moment in the system that the word "settled" is true.**
9. On the merchant's payout schedule, a payout transfer moves `available` → `clearing:bank_payouts`, less anything routed to `reserve` (§11), and a bank transfer is initiated.

**Failure path — the authorization times out with no response (step 3).** We do not know whether the issuer approved. **Send a reversal advice** to release any hold the cardholder may be carrying, mark the intent `requires_action` rather than approved or declined, and **let the settlement file adjudicate**: if the authorization was real, it appears there, and reconciliation books it. **We never approve on a timeout — §2 says this path fails closed**, because a fabricated approval is money we have promised and cannot collect.

**Failure path — we crash between step 4 and step 5.** The money moved at the acquirer and nothing in our system records it. The idempotency record is still `in_flight` and expires on its lease (§7), so the merchant's retry proceeds — and the acquirer, which received our derived key on the capture, returns the *original* result rather than capturing twice. **The settlement file then catches whatever the retry didn't**, which is why reconciliation is a component and not a report.

**Failure path — the settlement file is late or malformed (step 8).** Nothing moves from `pending` to `available` and payouts for that window don't run. **The correct behavior is to stall, not to estimate**: paying out against unsettled money is lending, and we are not a lender. The exception queue gets an entry with an owner and an SLA.

### Flow B — a refund, three weeks later

1. `POST /v1/refunds` with its own idempotency key. The payment is long settled and, quite possibly, long paid out.
2. A **reversing transfer** is booked — new entries, opposite directions. **Nothing about the original transfer is touched**, which is the same rule the LLM API billing page's `§4` applies to its ledger and for the same reason: the question a dispute asks is "what did you believe, and when."
3. The refund is submitted to the acquirer and moves back toward the cardholder over its own settlement cycle.
4. **The processing fee on the original payment does not come back.** It is booked as a real cost to the merchant, and this is exactly the fee the Amazon checkout page's `§11` is avoiding when it captures per shipment instead of at placement — **the two pages are describing the same dollar from opposite sides.**

**Failure path — the refund takes the merchant's `available` balance negative.** This is a normal state, not an error. The balance is allowed to go negative; the payout job will not run while it is; and if it stays negative past a threshold we debit the merchant's bank account and, failing that, book the shortfall to `loss`. **A design in which balances cannot be negative has to reject legitimate refunds, which is worse.**

### Flow C — a dispute arrives

1. The acquirer notifies us of a chargeback with a network reason code and **a deadline that is not ours to set**.
2. A transfer immediately debits the merchant's `available` for the disputed amount plus the dispute fee. **The money leaves the merchant's balance the moment the dispute opens, not when it resolves** — because the issuer has already given it back to the cardholder.
3. The merchant is notified, and a timer is armed with alerts at 7 and 2 days remaining (§2).
4. Evidence is submitted; weeks later an outcome arrives. **Won** books a reversing transfer that returns the amount. **Lost** leaves the debit in place and the transfer that already happened is the final word.

**Failure path — the deadline passes with no evidence.** It is an automatic loss, full stop, and the only defense is the timer. **This is the one deadline in the system enforced by an external party with no appeal**, and it is why dispute deadlines are a first-class scheduled component rather than a field on a row.

### Flow D — payout day

1. The scheduler selects merchants whose payout window has closed. **The amount is computed from the ledger, never from the materialized balance** — the cache is for screens, not for money leaving.
2. Reserve policy withholds a percentage or a rolling window (§11); the remainder becomes a payout transfer and a bank instruction.
3. The payout appears in the API with the exact list of balance transactions composing it. **"Explainable to the cent" is a query over the ledger, and it is only possible because the ledger exists.**

**Failure path — the bank rail rejects the transfer** (closed account, wrong details). The payout goes to `failed`, a reversing transfer returns the funds to `available`, and the merchant is asked for new details. **The money never left an account we control, and the ledger shows both movements** — which is the difference between a payout that failed and a payout that vanished.

---

## 7 · Deep dive — idempotency, from the side that stores the keys

### What you'd reach for first

A map from key to response. On each request, look up the key; if it's there, return the stored response; if not, do the work and store it.

### What breaks

**The lookup and the write are not atomic, and that gap is exactly where the double charge lives.** Two requests carrying the same key arrive 5 ms apart — a client retry racing its own original after a timeout, which is *the single most common way this key is used*. Both miss the store. Both authorize. **The naive design fails in precisely the scenario it was built for.**

**Key scoping is a security bug, not a correctness one.** A global key namespace means one merchant can guess or brute-force another's key and receive their stored response — which contains a customer's payment details.

**Same key, different body has no answer.** A merchant reuses a key by accident on a $500 charge that was previously a $5 charge. Returning the stored $5 response silently is a data-loss bug in their code that we have chosen to conceal.

**And retention shorter than the caller's retry budget is a time bomb.** A client with a 48-hour retry queue against a 1-hour retention window will eventually retry past the expiry and be charged again — a double charge that is *entirely* our fault and looks, from every log we have, like two legitimate requests.

### What replaces it

**A claim written before the side effect, uniquely keyed by `(merchant_id, key)`, carrying the request hash and a state.**

1. **`INSERT (merchant_id, key, request_hash, state='in_flight', lease_expires_at)`.** The unique index does the mutual exclusion — no lock service, no read-then-write.
2. **A unique violation is not an error, it's the answer.** Load the existing record: `complete` → replay the stored response byte-for-byte. `in_flight` → return **`409 request_in_progress`** and let the caller retry; we do not queue behind it, because holding a connection open behind an in-flight charge turns one slow authorization into two.
3. **Hash mismatch → `409`, always**, whatever the state. The key identifies a request, and a different body is a different request.
4. **The terminal response is written in the same transaction as the ledger transfer** (§6, step 5). If they can be written separately, there is a window in which the money moved and the retry doesn't know it.
5. **The `in_flight` claim carries a lease**, not just a TTL. A process that dies mid-charge would otherwise wedge that key forever — the merchant's retries would receive `409` indefinitely for a payment that never completed. The lease expires in ~60 s and the key becomes claimable again.
6. **Retention is 24 hours minimum and it is documented**, because it is a contract: it must outlive any client retry policy we tell merchants to use, and `system-design.md §04 C` makes the general form of that argument — *the retention window must outlive the dead-letter queue.* **→ ties to the exactly-once-charge-creation row in §2**, which is the only requirement here that names its own storage.

**And the key covers the operation, not the endpoint.** A capture and an authorization sharing a key are different side effects; scoping the record by `(merchant, key)` alone and letting two different operations collide is a subtle version of the hash-mismatch bug.

### What it costs

**A strongly-consistent read-modify-write on the hottest path in the product** — every money call now begins with a write to a store that cannot be eventually consistent, which rules out several otherwise attractive databases (§12). **You have also taken ownership of the merchant's retry semantics**: `409 request_in_progress` is a response their client has to handle, and if the documentation is bad they will handle it by retrying in a tight loop. And the store is pure overhead — ~55M records/day holding nothing anyone will ever read in the happy path, kept alive purely because a fraction of a percent of requests time out.

---

## 8 · Deep dive — the double-entry ledger

### What you'd reach for first

A `balance` column on the merchant row, and an `UPDATE merchants SET balance = balance + ?` on every payment, refund, dispute, and payout. Simple, obvious, and it's what almost everyone draws.

### What breaks

**It cannot answer "why".** A merchant sees $48,320.15 and asks what it's made of. The column has no answer, and neither does any log, because the log records requests and the balance records the sum of some subset of them that nobody can now identify. **Every support conversation about money becomes an archaeology project.**

**A double-applied event is undetectable and unfixable.** Consume a settlement event twice and the balance is $50 too high, permanently, with nothing anywhere that says so. There is no invariant to check — any number is a valid number for a column.

**It serializes the whale.** A merchant doing 500 payments/s during Black Friday is 500 read-modify-writes per second against **one row**, which a Postgres row under contention will not do (`Billing §3` puts the practical ceiling at roughly 500–2,000/s and the tail is much worse than the average).

**And it lets money be created and destroyed.** A crash between "debit the customer" and "credit the merchant" leaves the system holding funds that belong to nobody, and nothing notices — because there is no rule being violated. **This is the deepest problem: a balance column has no concept of money being conserved.**

### What replaces it

**Double-entry bookkeeping. Money is only ever moved between accounts, in balanced groups, by insert.**

**The accounts**, per merchant and per platform: `pending`, `available`, `reserve`, and the platform's `fee_revenue`, `network_cost`, `loss`, and `clearing` accounts standing in for money in flight at the acquirer or the bank.

**The unit is a `Transfer` — a set of entries that sums to zero**, committed atomically. A $50 capture at a 2.9% + 30¢ fee:

```text
Transfer  t_8f21   source: capture ch_9k2   currency: USD
  DR  clearing:acquirer              5000
  CR  merchant:42:pending           -4855
  CR  platform:fee_revenue           -145
                                    ─────
                                        0
```

Settlement two days later moves it across the line:

```text
Transfer  t_c04a   source: settlement_line sl_77
  DR  merchant:42:pending            4855
  CR  merchant:42:available         -4855
```

And a lost dispute takes it back, plus the fee:

```text
Transfer  t_e91b   source: dispute dp_31
  DR  merchant:42:available          6500
  CR  clearing:acquirer             -5000
  CR  platform:fee_revenue          -1500
```

Four properties do all the work:

- **The invariant is one query.** `SELECT currency, SUM(amount) FROM ledger_entries GROUP BY currency` must return zero for every currency, always. Run it continuously. **It catches a partially applied transfer, a double-consumed event, and a bad backfill — none of which any test suite would find**, and it costs a materialized aggregate.
- **A balance is a query**: `SUM(amount) WHERE account = 'merchant:42:available'`. Materialized incrementally for the dashboard's 5-second freshness target, **and recomputed from entries for anything involving money leaving** (§6D). The materialization is a cache and is treated like one.
- **Entries are inserts, so there is no contention.** The whale merchant's 500/s is 500 appends, not 500 updates to one row. The write amplification (~8 entries per payment, §3) buys the removal of the hottest lock in the naive design.
- **Every transfer names its source event**, with `UNIQUE (source_type, source_id)`. Replaying a settlement line, a webhook, or a Kafka partition is then a no-op at the database level rather than a matter of consumer discipline — the same mechanism `Billing §4` uses, applied to four orders of magnitude more rows.

**Amounts are integers in the currency's minor unit**, and never floats. Deliberately unlike the LLM API billing page's nano-dollars (§3): the networks settle in cents, and inventing sub-cent precision here would produce numbers that cannot be paid.

### What it costs

**~440M rows/day, ~160B/year** (§3), which is a partitioning and archival problem from day one, not from year three — §12 gives it a lifecycle. **Every read is now an aggregate**, so the materialization layer is mandatory rather than an optimization, and it brings its own reconciliation: the cache and the ledger must agree, the ledger wins, and there is a job that checks. **And the model has to be learned.** Engineers who have never written accounting code will try to "fix" a negative balance, will add an eighth account rather than a transfer, and will at some point propose an `UPDATE`. The invariant check is what makes that survivable — it turns a whole class of misunderstanding into an alert instead of a slow leak.

---

## 9 · Deep dive — authorize, capture, settle: three money events, not one

### What you'd reach for first

One `charge` call. It returns 200, the payment succeeded, credit the merchant.

### What breaks

**An authorization is not money.** It is an issuer saying funds exist and holding them against the cardholder's credit line. **Nothing has moved.** A design that credits `available` on an authorization has created spendable balance out of a promise, and will pay a merchant for a payment that never settles.

**A `200 OK` is not an authorization either**, and this is the same hole `Billing §10` names from the other side: the request can time out with the money already held. Except here we're the one who has to decide, and there is no upstream to blame.

**Capture has rules we don't set.** Partial capture, over-capture tolerance, and the window in which capture is allowed all vary by network and by acquirer, and an authorization expires in about seven days — the constraint the Amazon checkout page's `§11` builds its whole re-authorization job around, seen from the side that enforces it.

**And the acquirer's answer isn't final.** Adjustments, reversals, and fee corrections arrive in the settlement file days later, and a system that stopped listening after the `200` never sees them.

### What replaces it

**Three states with three distinct meanings about money, an explicit machine between them, and the settlement file as the only authority on what actually moved.**

```text
                    ┌──────────────▶ CANCELED (auth reversed, nothing moved)
                    │
REQUIRES_AUTH ─▶ AUTHORIZED ─▶ CAPTURED ─▶ SETTLED ─▶ PAID_OUT
      │              │            │           │
      ▼              ▼            ▼           └──▶ DISPUTED ─▶ WON | LOST
   DECLINED     EXPIRED       REFUNDED
                (7 days)
```

- **`AUTHORIZED` books nothing to the ledger.** No transfer, no balance change. The money doesn't exist yet and the ledger says so by being silent.
- **`CAPTURED` books to `pending`.** We have instructed the money to move; it hasn't.
- **`SETTLED` is booked only by a line in the acquirer's file**, and it is the transition that moves `pending → available`. **There is no code path anywhere that sets `SETTLED` from an HTTP response.** `Billing §10` puts the same rule as "no transition fires on a 200"; the inversion worth saying out loud is that **we are now the party whose `200` other people are being told not to trust, which obliges us to publish a state that is actually true.**
- **An unknown-outcome timeout sends a reversal advice** and moves to `REQUIRES_ACTION`, never to approved or declined (§6, Flow A). **→ ties to the authorization-availability row in §2**, which is the one place in this repo where the answer is fail closed rather than fail open.
- **Fee estimation is separate from fee truth.** At capture we book our *estimated* fee to `fee_revenue`; the settlement file carries the actual interchange, and the difference is booked to `network_cost`. **Pretending the estimate was right is how a P&L drifts from reality by a rounding error a hundred million times.**

### What it costs

**Merchants see money as "pending" for days and find it baffling**, and the support load from that is real and permanent — the honest answer, "we don't have it yet either," is not one people enjoy. **You have taken a hard batch dependency**: the settlement file is a daily deadline owned by someone else, and when it is late nothing settles and no payouts run (§6). **Reversal advices are best-effort** — the network may not honor one, so a cardholder can carry a hold for days on a payment that never existed, which generates its own complaints. And the three-state model has to be **exposed in the API rather than hidden**, because a merchant who can't distinguish captured from settled will build their own accounting on the wrong number.

---

## 10 · Deep dive — being the webhook sender

### What you'd reach for first

On each event, `POST` it to the merchant's URL from a worker pool. Retry a few times on failure.

### What breaks

**One slow merchant takes down delivery for everyone.** At ~2,500 deliveries/s across ~100k endpoints (§3), with an assumed 1% of endpoints slow or down and a 30 s timeout, **the shared pool fills with requests to servers that will never answer.** The 99% of merchants whose endpoints are healthy stop receiving events, and the cause is somebody else's outage. This is head-of-line blocking and it is the dominant failure mode of naive webhook systems.

**Ordering is assumed and cannot be delivered.** Merchants will write code that assumes `payment_intent.succeeded` precedes `charge.refunded`. Across retries, partitions, and multiple event producers, it won't — and a `refunded` processed before `succeeded` leaves their database saying a refunded payment is outstanding.

**Recovery stampedes.** An endpoint down for six hours accumulates ~50M queued deliveries. The moment it returns, releasing them at full rate takes it down again — and now the outage is our fault.

**And an unsigned webhook is an open door.** Anyone who learns the URL can post a fabricated `payment_intent.succeeded` and ship goods for free.

### What replaces it

**Delivery partitioned by endpoint, bounded per endpoint, signed, and honestly documented as at-least-once and unordered — with a poll API as the backstop.**

- **Partition the delivery stream by `endpoint_id`**, with bounded concurrency per partition. A slow endpoint backs up **its own** partition and nothing else. This one decision removes the dominant failure mode, and it is worth drawing on the board.
- **Retry with exponential backoff and jitter for ~3 days** — seconds, then minutes, then hours. Three days is chosen to cover a weekend plus a business day, which is how long it actually takes a small merchant to notice.
- **Circuit-break on sustained failure**: after a threshold, the endpoint is marked unhealthy, delivery attempts drop to a trickle, and a human at the merchant gets an email. **Continuing to hammer a dead endpoint at full rate is a denial-of-service attack we are conducting on our own customer.**
- **On recovery, drain rate-limited**, not at full speed. The backlog is released at a multiple of the endpoint's normal rate, not instantly.
- **Sign every payload** with a timestamp and an HMAC over `timestamp + body`, with a tolerance window (5 minutes) so a captured request cannot be replayed later. Publish the verification code in every SDK.
- **Document the contract as at-least-once and unordered, and tell merchants to fetch current state rather than apply the event's payload as a delta.** This is precisely the advice `Billing §10` follows when it says *apply by reading the state of the referenced object rather than trusting the event's implied sequence* — **and there is something worth saying about the fact that this page and that one are the two ends of the same integration.**
- **`GET /v1/events` is not optional.** Webhooks are an optimization over polling; a merchant who lost a day of deliveries must be able to recover without contacting support. **→ ties to the webhook-delivery row in §2**, whose 99.9% is deliberately not 100% — and the poll API is what makes the missing tenth of a percent recoverable rather than lost.

### What it costs

**Per-endpoint partitioning at 100k endpoints** is a partition-count problem — you don't get 100k Kafka partitions, so it's a consistent hash onto a few thousand partitions with per-endpoint concurrency limits inside each, which means a very unlucky pair of endpoints can still share a queue. That's an accepted, bounded residual rather than a solved problem, and saying so is better than claiming perfect isolation. **The delivery-attempt table is enormous** — hundreds of millions of rows a day, most of them a single successful attempt — and needs its own retention policy. **And the honest contract has a support cost**: "at-least-once and unordered" means a share of merchants will build something that assumes otherwise, and their bug will arrive in our inbox as our bug.

---

## 11 · Deep dive — money leaving: refunds, disputes, payouts, and reserves

### What you'd reach for first

Refund is a negative charge. A dispute subtracts from the balance. A payout sends whatever the balance says. Three simple operations.

### What breaks

**The money may already be gone.** A refund on a three-week-old payment is money we paid out two weeks ago. Subtracting from a balance that is now $200 produces a negative number, and a system that treats negative balances as impossible has to reject a legitimate refund.

**Disputes arrive after the merchant does not.** Up to **540 days** later (§3), by which time a fraudulent merchant has collected their payouts and closed the account. **Paying out 100% on schedule means the clawback has nothing to claw from**, and the loss is ours — that's the `loss` account, and it's a real line in the P&L.

**Deadlines are external and absolute.** Miss the evidence window and the dispute is lost regardless of merits.

**And instant payouts are lending.** Paying a merchant before settlement means advancing our own funds against money we believe will arrive, which is a credit product with a credit product's risk.

### What replaces it

**Reversing transfers, a reserve policy sized by risk, a scheduled payout with a deliberate lag, and dispute deadlines as first-class timers.**

- **Every reversal is a new transfer, never an edit.** A refund, a won dispute, a failed payout — all of them book opposite entries and leave the originals untouched (§8).
- **Negative balances are legal.** The payout job refuses to run on a negative balance; past a threshold and a grace period we debit the merchant's bank account; failing that, it books to `loss`. **Making negative a valid state is what lets refunds always succeed**, and refunds always succeeding is the correct priority — the cardholder is not the party we should be pushing the risk onto.
- **Reserves hold back a slice of `available`**, either a rolling window (funds held N days beyond settlement) or a percentage, sized by the merchant's dispute rate, chargeback history, and how far in advance they deliver goods. **A merchant selling concert tickets a year out is a fundamentally different credit exposure from a merchant shipping tomorrow, and the reserve is where that judgment is expressed** — an appeals path is required, because getting it wrong strangles a legitimate business's cash flow.
- **The payout schedule has a deliberate lag** (T+2 default, longer for new or risky merchants), and the amount is always computed from the ledger rather than the cache (§6D).
- **Dispute deadlines are scheduled timers with escalating alerts**, not a field someone queries. A missed deadline is an automatic, unappealable loss, so this is the one place where a cron job's reliability is directly a dollar figure.

### What it costs

**Reserves are the single largest source of merchant anger in this entire product**, and they are correct anyway — which makes the appeals process and the clarity of the explanation part of the design, not a support concern. **The `loss` account is a real cost of doing business** and it has to be forecast and budgeted, which means someone owns the number. **Risk-based reserve sizing needs a model**, and a model applied to money movement needs an audit trail of its own — why this merchant, on this date, was moved to a 10% rolling reserve. And **the payout lag is a competitive disadvantage** that every competitor advertises against, which is why "instant payout" exists as a paid product: it's the same lag, with us taking the credit risk for a fee.

---

## 12 · Data model, sharding, and storage decisions

**Everything shards by `merchant_id`.** Unlike the Amazon checkout page — where orders shard by customer and inventory by SKU, and the incompatibility of those two keys is *why* it needs a saga — this system has one natural key and every important query is inside it: this merchant's payments, this merchant's balance, this merchant's payouts. **That single-key property is what lets the ledger transfer and the idempotency record and the payment row commit in one local transaction**, and it's the biggest structural simplification on the page. Say it out loud, because it's the reason this design has no saga.

**Colocation is the property, not sharding.** Citus does not shard Postgres for you — you declare the distribution column and live with it; what it automates is routing and online rebalancing. What it buys here is that tables distributed on `merchant_id` with the same shard count have their shards **on the same node**, so a payment intent, its authorization, the ledger transfer's several entries, the stored idempotency response and the outbox row all commit **locally**. §6's "one local transaction" is a claim about colocation, and it is the reason this page never needs a saga.

**The hot shard is a whale merchant on Black Friday** — a single merchant at ~500 payments/s, ~4,000 ledger entries/s. It's real and it's intentional: they are on their own shard, and because ledger writes are **appends rather than updates** (§8) the shard absorbs it. The design that couldn't survive this is the one with a balance column, which is the point.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Ledger — transfers + entries** | ~5,100 appends/s, aggregate reads per account, ~440M rows/day | **Zero loss. No degraded mode. 7–10 year retention** | **Postgres**, distributed with **Citus** on `merchant_id`, **colocated** with intents and idempotency records, monthly partitions, synchronous replica | "Money at five thousand appends a second wants the most boring, most auditable transactional engine that exists — and unlike the checkout page, here the write rate justifies distributing it on its own. Colocation is what keeps a transfer's entries, the intent and the idempotency response in **one local commit**. Appends parallelize; the balance column they replace does not" |
| **Balance materialization** | Read on every dashboard load, updated per transfer | **Rebuildable** — it's a cache | **Redis**, per `(merchant, account, currency)`, rebuilt from the ledger | "A cache of a `SUM`. It's allowed to be five seconds stale and it is never allowed to be the number we pay out" |
| **Idempotency records** | Read-before-write on **every** money call, ~55M/day | **A lost record is a double charge** | **Postgres**, colocated with the ledger on `merchant_id`, `UNIQUE (merchant_id, key)`, swept at 24 h | "It has to be Postgres, and colocated, for one reason: §7 requires the stored response to commit **in the same transaction as the ledger transfer**. Put it in a separate store and that's a dual write — the exact failure the outbox exists to prevent, sitting on the money path. The unique index gives the claim without a lock" |
| **Card vault** | Tokenize on write, detokenize only inside the authorization path | Loss is catastrophic; exposure is worse | **Isolated service**, separate account and network segment, HSM-backed keys, its own audit log | "The only component that sees a PAN. Everything else in this diagram handles tokens, and that boundary is what keeps our merchants at SAQ-A" |
| **Payment intents / authorizations / refunds** | Written once, read by merchant and support | High; reconciled against settlement | **Postgres**, same cluster as the ledger | "Same transaction as the ledger transfer, which is only possible because they share a shard key" |
| **Event stream + outbox** | Fan-out to webhooks, materialization, analytics | At-least-once, replayable | **Outbox in Postgres → Kafka**, keyed by object id, 7-day retention | "The outbox row commits with the transfer, so there is no dual write. Keyed by object id, which is the only ordering any consumer needs" |
| **Webhook delivery attempts** | ~220M writes/day, read only when debugging | Low — reconstructible from events | **Cassandra**, partitioned by `endpoint_id`, TTL 30 days | "Enormous, append-only, and disposable. Partitioned by endpoint because that's also how delivery is isolated" |
| **Settlement files** | Written daily by the acquirer, read once by reconciliation, kept forever | **Immutable evidence** | **S3 with Object Lock**, plus parsed lines in Postgres | "The file is the truth about money. It gets stored WORM, because in a dispute with our own acquirer it's the evidence" |
| **Disputes + evidence** | Low volume, long-lived, deadline-driven | 7 years | **Postgres**, with evidence files in S3 | "Low volume and high consequence — the timer matters more than the storage" |
| **Reconciliation exceptions** | Written by the daily job, worked by humans | Must not be lost | **Postgres**, a queue with an owner and an SLA | "Not a dashboard — a queue with a person attached, which is the same conclusion the billing page reaches in its §11" |

### Data lifecycle — the append-only entities

| Entity | Hot | Warm | Cold | Why the boundary is there |
|---|---|---|---|---|
| **Ledger entries** | 90 days in Postgres, ms aggregate reads | 2 years, monthly partitions, detached but attached-on-demand | **7–10 years** in S3 Parquet, Athena, seconds per query | Chargeback windows reach 540 days; financial audit and tax reach seven years; some jurisdictions ten. **Nothing is ever deleted** — a gap in a double-entry ledger is indistinguishable from fraud |
| **Payment intents** | 90 days | 2 years | 7 years alongside the ledger | Support reads the recent tail; disputes and audits read the archive |
| **Webhook deliveries** | 30 days, then **deleted** | — | — | Debugging material, not evidence. The events themselves are durable in Kafka and re-derivable |
| **Settlement files** | Parsed lines hot for 90 days | — | **Raw files forever**, WORM | It is the one artifact we did not author, which is exactly why we keep the original bytes |

**Restore cost, stated:** the balance cache rebuilds from the ledger in minutes. Webhook history is not restored at all — it is regenerated from the event stream. **The ledger has no acceptable restore story**, which is what "does not survive loss of the ledger" in §2 means, and why it is the one component running synchronous replication and continuous archiving.

**Reconciliation** is the daily three-way diff argued in `Billing §11` — our ledger against the acquirer's settlement file against our own bank statement — with the same conclusion about the exception queue needing an owner rather than a log line. **What this page adds is the fee dimension**: the file carries actual interchange per transaction, so reconciliation checks not only *did the money move* but *did it cost what we said it cost*, and the drift between estimated and actual fees is a monitored number.

---

## 13 · Traps — the ranked list

**Design traps**

1. **A balance column.** It cannot say why, cannot be audited, cannot detect a double-applied event, and serializes the whale onto one row. This is the trap the problem exists to catch.
2. **Crediting `available` on authorization.** An authorization is not money. This creates spendable balance out of a promise and pays merchants for payments that never settle.
3. **Marking anything settled from an HTTP response.** Settlement is a line in a file. There must be no code path that sets it any other way.
4. **Mutating a ledger entry.** A refund is a reversing transfer. An `UPDATE` on money destroys the only record of what was believed and when — the same rule `Billing §4` states, and the reason is identical.
5. **Storing the idempotency record after the side effect.** A crash in between and the retry charges again. The claim goes first, with the request hash.
6. **A global idempotency key namespace.** Cross-merchant collision, and worse, cross-merchant read of a stored response containing payment details.
7. **Replaying a stored response for a different request body.** Silently hides a merchant's bug and produces the wrong charge. `409`, always.
8. **No lease on the `in_flight` claim.** A crashed request wedges that key permanently, and every subsequent retry gets `409` for a payment that never happened.
9. **Approving on an unknown-outcome timeout.** Fail closed. A fabricated approval is money promised and uncollectable — this is the one place in this repo where fail-open is the wrong answer.
10. **Promising ordered webhook delivery.** You cannot deliver it, merchants will depend on it, and their corrupted state will be your incident.
11. **A shared webhook worker pool.** One slow merchant's endpoint starves every other merchant. Partition by endpoint.
12. **Unsigned webhooks.** A forged `payment_intent.succeeded` ships goods for free.
13. **No poll API.** A merchant's four-hour outage becomes permanent data loss.
14. **Forbidding negative balances.** Then refunds have to be rejected, which pushes the risk onto the cardholder — the wrong party.
15. **Paying out 100% on schedule with no reserve.** Disputes arrive up to 540 days later, and a departed merchant's clawback lands on the `loss` account.
16. **Treating a dispute deadline as a field rather than a timer.** Missing it is an automatic, unappealable loss.
17. **Booking the estimated fee and never reconciling it.** Actual interchange arrives in the settlement file; the drift is real money and nobody notices it accumulating.
18. **Floats, or nano-precision.** Integer minor units. The networks settle in cents and inventing precision produces amounts that cannot be paid.

**Performance traps**

19. **A synchronous ledger aggregate on the dashboard path.** `SUM` over a merchant's lifetime of entries. Materialize, and reconcile the materialization.
20. **Detokenizing outside the vault.** Every extra service that can see a PAN expands the PCI boundary, which is a compliance cost measured in quarters.
21. **Releasing a recovered endpoint's backlog at full rate.** You take it down again, and this time it's your fault.
22. **Unbounded webhook-attempt storage.** Hundreds of millions of rows a day of debugging material. TTL it.

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

23. **Spending the round on the card networks.** ISO 8583, interchange tiers, and the four-party model are domain trivia that feel like depth. The interviewer is listening for the ledger, the idempotency store, and the settlement boundary — say the network is a black box you call, name what it can do to you, and spend the time on your own side of the wire.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 600" role="img" aria-label="Payment processor five-minute skeleton. Rows for the mandatory idempotency key and the claim, the vault, authorization that fails closed, the single commit transaction spanning the full width, the double-entry ledger, the pending-to-available settlement step, the webhook senders and payouts, and reconciliation. A margin band below carries the balance-is-a-query line, the float figure and the dispute window.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-box" x="30" y="68" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="92.5">Idempotency-Key required on every money call</text>
  <text class="dg-s dg-c" x="260" y="108.5">a missing key is a 400</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="510" y="68" width="450" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="92.5">Claim first — INSERT (merchant_id, key, hash)</text>
  <text class="dg-s dg-c" x="735" y="108.5">unique violation IS the answer · lease it</text>
  <circle class="dg-num" cx="510" cy="68" r="9"></circle>
  <text class="dg-num-t" x="510" y="71.4">2</text>
  <rect class="dg-box" x="30" y="144" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="168.5">Vault</text>
  <text class="dg-s dg-c" x="260" y="184.5">the only PAN. This is why merchants get SAQ-A</text>
  <circle class="dg-num" cx="30" cy="144" r="9"></circle>
  <text class="dg-num-t" x="30" y="147.4">3</text>
  <rect class="dg-warn" x="510" y="144" width="450" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="735" y="168.5">Authorize at the acquirer</text>
  <text class="dg-s dg-c" x="735" y="184.5">FAILS CLOSED · timeout → reversal advice</text>
  <circle class="dg-num" cx="510" cy="144" r="9"></circle>
  <text class="dg-num-t" x="510" y="147.4">4</text>
  <rect class="dg-good" x="30" y="220" width="930" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="244.5">COMMIT: intent + authorization + LEDGER TRANSFER + idempotency response + OUTBOX ROW</text>
  <text class="dg-s dg-c" x="495" y="260.5">one local transaction — everything shards by merchant_id, so there is no saga</text>
  <circle class="dg-num" cx="30" cy="220" r="9"></circle>
  <text class="dg-num-t" x="30" y="223.4">5</text>
  <rect class="dg-good" x="30" y="296" width="930" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="320.5">The ledger — DR clearing / CR merchant:pending / CR fee_revenue, summing to zero</text>
  <text class="dg-s dg-c" x="495" y="336.5">append-only · UNIQUE (source_type, source_id) · a balance is a query over this</text>
  <circle class="dg-num" cx="30" cy="296" r="9"></circle>
  <text class="dg-num-t" x="30" y="299.4">6</text>
  <rect class="dg-box" x="30" y="372" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="396.5">pending, NOT available</text>
  <text class="dg-s dg-c" x="260" y="412.5">an authorization is not money</text>
  <circle class="dg-num" cx="30" cy="372" r="9"></circle>
  <text class="dg-num-t" x="30" y="375.4">7</text>
  <rect class="dg-box" x="510" y="372" width="450" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="396.5">Settlement file T+1/T+2 → available</text>
  <text class="dg-s dg-c" x="735" y="412.5">and book estimated-vs-actual fee drift</text>
  <circle class="dg-num" cx="510" cy="372" r="9"></circle>
  <text class="dg-num-t" x="510" y="375.4">8</text>
  <rect class="dg-box" x="30" y="448" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="472.5">Webhooks partitioned by endpoint_id</text>
  <text class="dg-s dg-c" x="260" y="488.5">signed · 3-day backoff · GET /v1/events backstop</text>
  <circle class="dg-num" cx="30" cy="448" r="9"></circle>
  <text class="dg-num-t" x="30" y="451.4">9</text>
  <rect class="dg-box" x="510" y="448" width="450" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="472.5">Payouts from available less reserve</text>
  <text class="dg-s dg-c" x="735" y="488.5">reversing transfers · daily 3-way reconcile</text>
  <circle class="dg-num" cx="510" cy="448" r="9"></circle>
  <text class="dg-num-t" x="510" y="451.4">10</text>
  <text class="dg-lane" x="30" y="526">IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="538" width="300" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="556.5">A balance is a query</text>
  <text class="dg-s dg-c" x="180" y="572.5">not a column. That is the answer</text>
  <rect class="dg-box" x="350" y="538" width="300" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="556.5">~$5.5B of float</text>
  <text class="dg-s dg-c" x="500" y="572.5">why payouts have a lag</text>
  <rect class="dg-box" x="670" y="538" width="290" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="556.5">Disputes reach back 540 days</text>
  <text class="dg-s dg-c" x="815" y="572.5">which is what reserves are for</text>
</svg>
</div>

<p class="diagram-cap">Badges 5 and 6 are the page. One local transaction, and a ledger that only ever grows — draw those two and the rest is consequence. Badge 7 is the one candidates skip: the money is visible and it is not payable, and saying why is the difference between a diagram and a design.</p>

1. **API tier, `Idempotency-Key` required** on every money-mutating call. Missing key is a `400`.
2. **Idempotency claim first** — `INSERT (merchant_id, key, request_hash, in_flight, lease)`. Unique violation *is* the answer: `complete` replays, `in_flight` returns `409`, hash mismatch returns `409`.
3. **Vault** — the only component that sees a PAN. Everything downstream carries a token. This boundary is why merchants get SAQ-A.
4. **Authorize at the acquirer** — the one synchronous external call, 300–600 ms. **Fails closed.** A timeout sends a reversal advice and goes to `REQUIRES_ACTION`, never to approved.
5. **One local transaction:** payment intent + authorization + **ledger transfer** + terminal idempotency response + **outbox row**. Possible because everything shards by `merchant_id`. **Draw the box around it.**
6. **The ledger — double entry.** `DR clearing / CR merchant:pending / CR fee_revenue`, summing to zero. Append-only, `UNIQUE (source_type, source_id)`, sharded by merchant. **Every transfer sums to zero, so the system does.**
7. **`pending`, not `available`.** An authorization is not money and a capture isn't either. Only the settlement file moves the line.
8. **Settlement file, T+1/T+2** → transfer `pending → available`, and book estimated-versus-actual fee drift to `network_cost`. **The only thing in the system that makes "settled" true.**
9. **Outbox → Kafka → webhook senders, partitioned by endpoint**, bounded per endpoint, signed, 3-day backoff, circuit-broken. Plus `GET /v1/events` as the backstop.
10. **Money out:** payouts on a schedule from `available` less `reserve`, computed from the ledger not the cache; refunds and disputes as reversing transfers; negative balances legal; daily three-way reconciliation into a queue with an owner.

**In the margin — said, not drawn:** a balance is a query, not a column · an authorization is not money · ~$5.5B of float is why payouts have a lag · disputes arrive up to 540 days later, which is what reserves are for · fail closed here, unlike everywhere else in this repo · integer minor units, not nano-dollars, because the networks settle in cents.

---

## 15 · Variants — what actually changes

**The axis that governs this family: who holds the money, and for how long, between the payer and the payee.** The ledger, the idempotency store, and the event fanout are identical in all six rows. What changes is how long funds sit in an account you control — and every regulatory obligation, every reserve, and every payout mechanism on this page is a consequence of that one duration.

| Product | Who holds the funds, and for how long | What changes |
|---|---|---|
| **Pure gateway** — you route to the merchant's own acquirer | **Never.** Money goes merchant-acquirer to merchant-bank | **§8 and §11 mostly evaporate.** No merchant balance, no payouts, no reserves, no float, and no money-transmitter licensing. You are an API, a vault, and a webhook sender — which is the cleanest proof that the ledger's difficulty comes from *holding funds* and nothing else |
| **Payment processor — this page** | **~2 days**, T+2 settlement into a payout | The full machinery: pending/available split, reserves, payouts, disputes, settlement reconciliation |
| **Merchant of record** — Paddle, app stores | Days, and **you are the legal seller** | The ledger is unchanged, but **tax becomes yours** — calculation, collection, and remittance in every jurisdiction — and so does dispute liability. A systems page becomes a compliance page, which is exactly why merchants pay a premium for it |
| **Marketplace / connected accounts** — Shopify, Uber, DoorDash | Days to weeks, **for two parties at once** | Every transfer now splits across the platform *and* the seller, so §8 grows an account tree rather than a flat set, and §11 doubles: two payout schedules, two reserve policies, and a dispute where the liable party may not be the one who was paid. **This is the row the Amazon checkout page's marketplace variant lands in** |
| **Stored-value wallet** — PayPal balance, e-money | **Indefinitely** | The ledger stops being infrastructure and *becomes the product*, and holding customer funds without a maturity date makes you an e-money institution: safeguarding requirements, capital, audits. Payouts become withdrawals, and the float is now regulated rather than merely large |
| **ACH / bank debits** | Days, and **reversible for up to 60 days** on consumer debits | Settlement is slow and **failure arrives after success** — a return can land two months later, which is the inverse of card risk. The dispute machinery in §11 becomes the primary path rather than the exception, and reserves get much larger relative to volume |

**The lesson:** every one of these has an idempotency store, a double-entry ledger, an event fanout, and a reconciliation job, and if you've built one you can draw all six. The only question that reorganizes the design is **how long you are holding money that isn't yours** — and when the answer is "not at all," most of this page stops being necessary.
