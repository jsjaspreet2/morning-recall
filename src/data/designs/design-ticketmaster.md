# Design Ticketmaster — High-Contention Inventory

**Archetype:** non-fungible inventory reservation under thundering herd, with money attached.
**Cousins that reuse ~70% of this page:** airline seat selection, StubHub, hotel booking, OpenTable, exam/DMV slot booking, vaccine appointments, IPO allocation, Amazon flash sale (with one big simplification — see §15).

**What's actually being graded:** whether you notice this is the *inverse* of a scale problem. A stadium onsale resolves to **60,000 successful sales** — a single Postgres box does that in under a second. The challenge is that ten million people want those 60,000 rows in the same sixty seconds, and you are not allowed to sell one of them twice.

**Do the global number too, because an interviewer will push on it.** Ticketmaster runs thousands of events concurrently and moves on the order of 500M+ tickets a year — roughly 16 sales/sec averaged. Even at a punishing peak (say ~50 simultaneous hot onsales across time zones, each doing ~1–2k writes/sec once holds and releases are counted) you land near **50–100k writes/sec globally, spread across 50 different shards.** That's a well-understood number. Compare a geospatial marketplace pushing 2.5M writes/sec into a single logical index: different problem entirely.

**So you do shard — but be precise about what sizes the sharding.** Not throughput. You shard by `event_id` because it's the natural transactional boundary, and you size for *isolation between concurrent hot events*, deliberately accepting load so uneven that one shard is pinned while a thousand sit idle (§12). Sharding for throughput would push you toward hash distribution, which turns every multi-seat order into a distributed transaction — the wrong trade. **Naming which of those two you're doing, and why, is the actual point being tested.**

**The one-line contrast to have ready if you've also prepped Uber:** *Uber is enormous write throughput with almost no contention. Ticketmaster is modest write throughput with catastrophic contention concentrated on a handful of rows. Opposite designs.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "Two workloads live in this system and they want opposite things. **Browse** is ~99.9% of traffic, read-only, and perfectly happy being a few seconds stale — that's a caching and fan-out problem. **Purchase** is a rounding error in volume but demands strict serializability on individual rows, because selling one seat twice is a business-ending bug and selling it zero times is lost revenue. My plan: separate those paths completely, put an admission-control layer in front of the purchase path so it never sees the full herd, and go deep on the seat reservation lifecycle — which is where correctness actually lives. I'll treat search, payments, and ticket delivery as named subsystems."

**Why open this way:** it reframes the problem away from "scale" (where most candidates default) toward contention and consistency, which is what the interviewer chose this problem to test. It also pre-commits your deep dive.

---

## 1 · Functional requirements

1. **Browse an event and see which seats are available.**
2. **Reserve specific seats** — a temporary hold — then **complete purchase** within a time limit.
3. **Never sell the same seat twice**, at any traffic level.

That third one is unusual: it's a correctness invariant masquerading as a feature. State it as a requirement anyway — it's the thing the whole design is organized around, and naming it up front means every later decision has something to be justified against.

**Out of scope (say them):** event creation/promoter tools, dynamic pricing, resale marketplace, ticket transfer, refunds, seat-map rendering.

**Below the line, likely follow-ups:** virtual waiting room (I'll cover it — it's load-bearing), bot mitigation, "best available N adjacent seats."

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Consistency on seat sale** | **Strictly serializable, no exceptions** | Double-selling a seat means two people in one chair at a stadium. There is no eventual-consistency version of this |
| Consistency on seat *display* | Eventually consistent, ≤5s stale, explicitly acceptable | 10M readers can't share a consistent snapshot. The UI is a hint; the hold API is the truth |
| Availability — browse | 99.99%, degrade gracefully | Read path should survive the purchase path falling over |
| Availability — purchase | Prefer **consistency over availability** | Refusing a sale is recoverable. Double-selling is not. This is the rare CP answer, and it's correct here |
| Onsale burst | ~10M concurrent users, 60k seats, ~60s | Publicly reported figures for major onsales run into billions of requests in a day |
| Hold latency | p99 < 500ms once admitted | Past ~1s users double-tap, and now you have a duplicate-request problem too |
| Fairness | A real requirement, not a nicety | See §11. Regulators and press treat this as a product failure, not a technical one |

**The sentence that earns the point:** *"This is one of the few systems where I'd knowingly choose CP over AP on the write path — and I'd scope that choice tightly to seat reservation, not to the whole system."*

---

## 3 · Numbers that reframe the problem

Assume a 60,000-seat stadium and 10M users showing up at onsale. **Do these at three levels — per event, per shard, global — because collapsing them is exactly the imprecision an interviewer will probe.**

**Per event**

- **Successful sales for the entire onsale: 60,000.** Not per second. Total.
- **Contention ratio: ~166 users per seat.** *This* is the number that matters. Every design decision downstream is about managing 166:1 contention on individual rows.
- **Read traffic:** 10M users polling a seat map every 2s = **5M QPS.** Four orders of magnitude above the write path, and the reason the read architecture is entirely separate.
- **Seat map payload:** one bit per seat is enough for the client — *selectable or not* — so 60k seats ≈ **7.5 KB**, or 15 KB at two bits if you want the UI to distinguish `HELD` from `SOLD` (worth it during an onsale, and it leaves room for a fourth state later). **That's a product choice, not a derivation.** Either way it gzips to a couple of KB. **The number that matters isn't the bit count — it's that the entire live availability state of a stadium is one small broadcastable blob, so you serve 5M QPS by shipping one object rather than answering 5M queries.**

**Per shard (the number that actually sizes your hardware)**

- Successful sales undercount real database work. Admission control lets ~200k users through at ~30% conversion; with retries and abandoned holds that's **~500k conditional updates plus ~60k sale commits over 5–10 minutes ≈ 1–2k writes/sec on one shard.**
- **Most of that work is *failed* attempts** — conditional updates returning zero rows because someone else won the row. They're cheap individually and murderous in aggregate *because they collide*, not because there are many of them. Contention, not volume.
- **You cannot split this.** A four-seat order needs a single transaction, so an event's shard is one node, and one node's capacity is the hard ceiling. **This is precisely why admission control exists** — the queue is what makes demand fit an unsplittable shard. State that causal chain out loud; it links §9 and §12 into one argument.

**Global**

- ~500M+ tickets/year ≈ **16 sales/sec averaged.** Peak of ~50 concurrent hot onsales × 1–2k writes/sec = **50–100k writes/sec across ~50 shards.** Ordinary. The system is not throughput-bound at any level.
- **Admission sizing:** at ~2,000 holds/sec, draining 10M queued users would take ~83 minutes — but you only drain until inventory is gone, ~200k admissions ≈ **100 seconds.** Useful for arguing your queue rate is derived rather than arbitrary.

---

## 4 · Core entities

- **Event** — id, venue_id, onsale_at, status
- **Venue / Section / Row** — static topology, changes ~never, aggressively cacheable
- **Seat** — id, event_id, section, row, number, price_tier *(one row per seat per event)*
- **SeatInventory** — seat_id, **status** (`AVAILABLE | HELD | SOLD`), **hold_id**, **hold_expires_at**, version
- **Hold** — id, user_id, event_id, seat_ids[], expires_at, status
- **Order** — id, hold_id, user_id, payment_intent_id, status, total
- **Ticket** — order_id, seat_id, barcode/rotating token
- **QueueToken** — signed, carries user_id, event_id, joined_at, admitted_at

**Load-bearing details:**
- `SeatInventory.hold_expires_at` is the field that makes §7 work. A hold is **a row with an expiry**, not a lock in a lock service.
- `Seat` is per-event, not global. Seat 12A exists once per show. Obvious in hindsight, frequently modeled wrong, and getting it wrong makes every query cross-join awkwardly.
- **Three states, not two.** Held inventory is neither available nor sold. Systems that model availability as a boolean oversell during the hold window.

---

## 5 · API

```
GET  /v1/events/{id}                       → event + venue topology (CDN, long TTL)
GET  /v1/events/{id}/availability          → bitmap + version (edge cache, ~1-5s TTL)
WS   /v1/events/{id}/availability/stream   ← delta updates during onsale

POST /v1/events/{id}/queue                 → { queueToken, position, etaSeconds }
GET  /v1/queue/{token}                     → { position } | { admitted, sessionToken }

POST /v1/holds                             → { holdId, seatIds, expiresAt }
  body: { eventId, seatIds } | { eventId, quantity, strategy: "BEST_AVAILABLE" }
  headers: Authorization: <sessionToken>, Idempotency-Key: <uuid>

DELETE /v1/holds/{id}                      → release early

POST /v1/orders                            → { orderId, status }
  body: { holdId, paymentMethodId }
  header: Idempotency-Key: <uuid>
```

**Decisions to narrate, unprompted:**

- **Availability is a separate resource from the event.** Different cache TTLs — topology is immutable, availability is volatile. Bundling them means you can't cache either well.
- **Hold and order are separate calls.** Holding is cheap and reversible; charging is expensive and hard to reverse. **Always take the reversible action first.** If you invert these, you can charge a card and then discover the seat is gone.
- **Two request shapes for holds.** Explicit `seatIds` (user clicked a seat map) and `quantity + BEST_AVAILABLE` (user just wants 4 together). These have *completely different* concurrency profiles — see §8 — and interviewers love that you noticed.
- **`Idempotency-Key` on both holds and orders.** During an onsale, users mash the button. Without it, one user consumes four seats worth of inventory in retries.
- **The `sessionToken` from the queue is what authorizes a hold.** No token, no hold. This is what makes the admission control in §9 actually enforceable rather than cosmetic.

---

## 6 · High-level design — two paths that barely touch

```
                        ┌──────────────────────────────────────┐
  10M users ────────────▶  EDGE: CDN + queue/admission worker  │
                        └───────┬──────────────────┬───────────┘
                    ~5M QPS     │                  │  ~2k/s admitted
                                ▼                  ▼
                   Availability read path    Booking Service
                   (cache/CDN + WS deltas)         │
                                ▲                  ▼
                                │           Inventory DB (per-event shard)
                                │                  │
                                └──── deltas ──────┤ status changes
                                                   ▼
                                        outbox → Kafka → orders,
                                        notifications, analytics
                                                   │
                                                   ▼
                                          Payment Service (PSP)
```

**The two properties to point at on your own diagram:**

1. **The read path never touches the inventory DB.** It reads a cache that is updated from the DB's change stream. This is what lets 5M QPS coexist with a single-writer-per-event database.
2. **The edge admission worker is the only thing between the herd and the booking tier.** Everything downstream of it is designed for 2k/s, not 5M/s, because it will never see more than that. Scaling by admission control instead of by capacity is the actual architectural move here.

### Flow A — browse (5M QPS, stale-tolerant)

1. `GET /v1/events/{id}` → CDN hit. Venue topology is immutable, so a long TTL serves essentially all of this for free.
2. `GET /v1/events/{id}/availability` → edge cache, 1–5s TTL. **That TTL is what absorbs the 5M QPS**: within any one-second window, millions of requests collapse into a handful of origin fetches.
3. On a cache miss, Availability Service serves the bitmap **from its own memory** — rebuilt from the inventory change stream — never by querying the inventory DB.
4. During an active onsale the client also opens `WS /v1/events/{id}/availability/stream` and receives deltas: `{version, changes: [[ordinal, status], ...]}`.
5. Client applies a delta only if `version == local + 1`. Any gap → refetch the full bitmap and resync. **Version-gap detection is what makes lossy delta push safe.**
6. Every inventory commit emits an outbox event → Kafka → Availability Service flips the bits, bumps the version, broadcasts the delta, and republishes the blob to the edge. End-to-end visibility: ~1s.

### Flow B — queue → hold → purchase

1. Onsale opens. Client calls `POST /v1/events/{id}/queue`. The edge worker runs `INCR queue:seq:{event_id}` for a position and returns a **signed** `queueToken {userId, eventId, position, joinedAt}`. (For the rare onsale that exceeds a single key's ~150k ops/sec, workers switch to reserved blocks — §9.)
2. Client polls `GET /v1/queue/{token}` — interval scaled to position, 30s at #4,000,000, 2s at #50 — or holds an SSE connection. The edge validates the signature and compares position against the admitted watermark. **No origin traffic at all for a waiting user.**
3. The admission controller advances `queue:admitted:{event_id}` at rate R, sized to *measured* booking-tier capacity. (**What happens if that watermark is lost on a Redis failover** is a real question with a non-obvious answer — §12.) Once `position ≤ watermark`, the client is issued a `sessionToken` with a ~10 min TTL.
4. Client loads the seat map (Flow A) and picks seats.
5. `POST /v1/holds {eventId, seatIds}` with the session token and an `Idempotency-Key`. **The Booking Service rejects any request lacking a valid session token — this is the line that makes the queue real rather than decorative.**
6. One transaction, seats acquired **in sorted `seat_id` order** to prevent deadlock between users grabbing overlapping sets. Each seat gets the conditional update from §7 (`AND (status='AVAILABLE' OR (status='HELD' AND hold_expires_at < now()))`). All N rows updated → commit, return `holdId` + `expiresAt` (~8 min). Any row returns zero → **roll back the whole set** and 409 with refreshed availability. Partial holds are not a thing.
   - *Best-available variant:* same transaction, but the seats come from `SELECT ... WHERE status='AVAILABLE' ORDER BY quality DESC LIMIT N FOR UPDATE SKIP LOCKED` (§8) instead of a client-supplied list.
7. The commit emits an outbox event → Availability Service → delta broadcast. Other users see those seats gray out within about a second.
8. `POST /v1/orders {holdId, paymentMethodId}` with an `Idempotency-Key`. Order Service verifies the hold belongs to this user and hasn't expired, enforces **purchase limits on user + payment instrument**, and transitions the hold to `PENDING_PAYMENT` — which suspends expiry, with a hard 2-minute ceiling so a hung PSP can't strand inventory.
9. Authorize with the PSP under its own idempotency key. **Failure → release the hold**, seats return to `AVAILABLE`, delta broadcast, 402 to the client.
10. Success → one transaction: seats `HELD → SOLD`, order `CONFIRMED`, hold consumed. **This commit is the point of no return** and the only place inventory becomes permanently unavailable.
11. Outbox → Kafka → capture the authorization asynchronously, mint tickets, send confirmation. A capture failure **keeps the sale** and retries out of band (§11).
12. **Abandonment path: nothing happens.** No job runs, no timer fires. The seat is reclaimed by whichever writer next evaluates the expiry predicate. The sweeper eventually corrects the displayed status, purely so the seat map doesn't look pessimistic.

---

## 7 · Deep dive — the hold, and why expiry is the hard part

A hold exists because payment takes human time. The user needs 3–10 minutes to enter a card, and during that window the seat must be neither sellable nor sold.

### The naive expiry mechanisms, and why they're wrong

**A background sweeper job** (`UPDATE ... WHERE status='HELD' AND expires_at < now()` every 30s). Correctness now depends on the sweeper's lag. During the 30 seconds before it runs, expired seats are invisible to buyers — lost revenue at exactly the moment revenue is scarcest. If the sweeper dies, inventory silently disappears. Worse: if you *also* let holds be reclaimed elsewhere, you have two writers with different clocks racing on the same rows.

**A Redis key with a TTL plus keyspace notifications.** Fast, but keyspace notifications are fire-and-forget — Redis does not guarantee delivery, and a dropped notification means a permanently stranded seat. You've made durability of your inventory contingent on a pub/sub message arriving.

**A distributed lock with a TTL.** Notice that this is just a hold with worse properties: not durable, not queryable, not auditable, and you now need the lock service to be as available as the sale itself.

### The right answer: lazy expiration

**Never actively expire anything.** Make the expiry a predicate that every write evaluates:

```sql
UPDATE seat_inventory
   SET status='HELD', hold_id=:new, hold_expires_at=now()+interval '8 minutes', version=version+1
 WHERE seat_id=:id
   AND (status='AVAILABLE'
        OR (status='HELD' AND hold_expires_at < now()))
-- 0 rows ⇒ genuinely unavailable. Not an error — the protocol working.
```

An expired hold is *automatically* claimable by the next writer, atomically, in the same statement that claims it. There is no window, no lag, no sweeper in the correctness path.

**You still run a sweeper — but only for UI freshness and reporting**, never for correctness. If it lags, nothing breaks; the seat map is just briefly pessimistic. **Say that distinction explicitly.** "Correctness is in the conditional; the sweeper is a cosmetic optimization" is exactly the kind of layering interviewers are listening for, and it's the same defense-in-depth instinct as the conditional update in the Uber page.

**Follow-up you should pre-empt: what if the user is mid-payment when the hold expires?** Transition the hold to `PENDING_PAYMENT` when the order is submitted, which suspends expiry, with a hard ceiling (~2 min) so a hung PSP can't strand a seat forever. The general principle: *expiry protects inventory from abandoned users, so it should pause when the user demonstrably hasn't abandoned.*

---

## 8 · Deep dive — concurrency at 166:1

Two request shapes, two different concurrency problems. Handling them identically is the most common mistake on this problem.

### Case 1 — user picked specific seats (contention is naturally spread)

Optimistic concurrency, as above. 166 users race for seat 12A; one wins, 165 get zero rows affected and a clean "that seat just went — here's an updated map." **This is fine**, because those 165 users wanted *that seat*; telling them it's gone is a truthful answer, not a failure. Retries scatter across other seats naturally.

Multi-seat orders need all-or-nothing: wrap the N conditional updates in one transaction, **acquire in a deterministic order** (sorted by seat_id) to avoid deadlocks between users grabbing overlapping sets in different orders. That ordering detail is a cheap, high-signal thing to mention.

### Case 2 — "best available, 4 together" (contention collapses onto one row)

Here optimistic concurrency degrades badly. Every request runs the same query, every request identifies the *same* best seats, one wins and 165 fail — then all 165 retry and immediately collide on the new best seats. You've built a retry storm that gets worse as inventory shrinks.

Naive pessimistic locking is worse:

```sql
SELECT seat_id FROM seat_inventory
 WHERE event_id=:e AND status='AVAILABLE'
 ORDER BY quality DESC LIMIT 4 FOR UPDATE;     -- ✗ 166 transactions queue on the same 4 rows
```

**The fix is `SKIP LOCKED`:**

```sql
SELECT seat_id FROM seat_inventory
 WHERE event_id=:e AND status='AVAILABLE'
 ORDER BY quality DESC LIMIT 4
   FOR UPDATE SKIP LOCKED;                     -- ✓ each txn grabs a *different* 4
```

`SKIP LOCKED` tells the database to ignore rows another transaction currently holds and take the next ones instead. Concurrent requests fan out across distinct rows rather than queueing on identical ones — throughput scales with concurrency instead of collapsing under it. **This one clause converts a serialization bottleneck into parallel work**, and it's the single highest-signal detail on this page. It's the same primitive that makes SQL-backed job queues work.

**Cost, which you should volunteer:** you get *a* good set of seats, not provably *the* best available, since another transaction may be holding better ones it later abandons. That's an entirely acceptable product trade, and saying so demonstrates you know it's a trade rather than having gotten lucky.

**Adjacency:** "4 together" is a contiguity constraint, not a top-N. Precompute contiguous blocks per row, or keep a per-row availability bitmap and scan for N consecutive set bits — cheap, since a row is ~40 seats.

### Why not do reservations in Redis?

You can, and at extreme contention it's genuinely attractive: a Lua script executes atomically, so check-and-set on seat state is trivially race-free and vastly faster than a DB transaction. The catch is durability — Redis AOF `everysec` can lose up to a second of writes on failover.

The clean way to have both: **Redis is authoritative for holds; the DB is authoritative for sales.** Losing a hold on failover is recoverable (the seat reverts to available, the user re-picks). Losing a *sale* is not, so the order commit goes through the durable store. Splitting durability requirements by how recoverable each state is — rather than picking one store for everything — is the reasoning that makes this a strong answer instead of a risky one.

---

## 9 · Deep dive — the virtual waiting room

**The premise:** you cannot make the booking tier handle 10M concurrent users, and you shouldn't try. You make it handle 2,000/sec and hold everyone else at the door. **Admission control instead of capacity is the load-shedding answer**, and it's the difference between a system that degrades and one that collapses.

**Placement matters more than mechanism.** The queue must live at the **edge** — CDN worker, or a dedicated stateless tier that touches nothing but Redis. Put it behind the same load balancer as your booking service and the herd takes down the thing whose job is to protect you from the herd.

**Mechanism:**
1. On arrival, `INCR queue:seq:{event_id}` → a ticket number. A single atomic op on a small integer, and one primary absorbs every onsale except the extreme tail — see below for where the ceiling actually is.

   The full key schema, so nothing is implicit:

   | Purpose | Structure | Key | Value | Operations |
   |---|---|---|---|---|
   | Position issuer | Counter | `queue:seq:{event_id}` | monotonic integer | `INCR` — the returned value *is* the position. `INCRBY` to reserve a block, for megaevents or for the durability ceiling (§12) |
   | Admission watermark | Counter | `queue:admitted:{event_id}` | monotonic integer | `INCRBY … R` by the controller; `GET` on every position poll. Admitted iff `position ≤ watermark` |
   | Session deny-list | Set + TTL | `revoked:{event_id}` | `{session_id}` | `SADD` on revoke, `SISMEMBER` on each hold. Only revocations are stored, so it stays tiny |

   **Both counters are per-event, and neither is ever read across events** — which is what keeps the queue tier horizontally trivial.
2. Issue a **signed** queue token (position, event, joined_at). Signed so it can be validated statelessly at the edge and can't be forged into a better position.
3. Client polls or holds an SSE connection for its position. Poll interval scales with position — someone at #4,000,000 gets a 30s interval; someone at #50 gets 2s. Free 10× reduction in queue-poll traffic.
4. An admission controller drains at rate R, sized to *measured* booking-tier capacity, and mints a session token valid ~10 minutes.
5. **The booking API rejects any request without a valid session token.** Without this, the queue is theater — a determined client just calls `/holds` directly.

### The counter: fine by default, a hot key only at the tail

`INCR queue:seq:{event_id}` per arrival is the right default, and you should say so before you say anything else. **One key is one slot, one node, one core** — Redis serializes those increments single-threaded, which is what makes them atomic — and a single primary handles roughly **100–250k simple ops/sec.**

Now put real events against that ceiling:

| Event | Arrivals at onsale | Rate | vs ceiling |
|---|---|---|---|
| 5k-seat theater | ~20k over minutes | ~100/s | 0.1% |
| 20k arena | ~200k over 5 min | ~700/s | <1% |
| Large stadium show | ~1M over 5 min | ~3.3k/s | ~2% |
| Once-a-year megaevent | ~10M over ~30s | **~330k/s** | **Over budget 2–10×** |

**So: plain `INCR` for essentially every event, and know the number where it stops working.** Volunteering "this holds to ~150k arrivals/sec, which covers everything except a handful of onsales a year" is a much stronger answer than pre-emptively sharding a counter that will never be hot.

**For the handful that do exceed it** — and you know which ones weeks ahead, so this is a per-event flag, not a runtime decision:

| Escalation | Mechanism | Cost |
|---|---|---|
| **Block reservation (Hi-Lo)** ✓ | Workers reserve 10k positions per `INCRBY` and serve them locally | ~10,000× fewer ops, and the cross-region round trip amortizes across a block instead of being paid per user. But positions go approximate — a worker on a stale block hands a *lower* number to a later arrival, and unused remainders leave gaps |
| **Sharded counters** | N keys, global position = `local_seq × N + shard` | Spreads throughput, still one round trip per arrival — fixes the ceiling, not the latency |
| **No counter at all** | Random 64-bit value per joiner; admission is `value < threshold` | Zero coordinated writes. You lose "you're #12,431" entirely |

**Two consequences if you do escalate** (and reasons not to escalate by default):

- **Gaps make position arithmetic lie.** Advancing the watermark by 1,000 no longer admits 1,000 people, so the controller must run a closed loop on *measured* admissions rather than watermark deltas. With plain `INCR`, positions are dense and the arithmetic just works.
- **Strict FIFO degrades.** Which matters less than it sounds — see immediately below — and **if you've chosen a lottery anyway, the third option becomes strictly better**, since a lottery has no use for a monotonic counter at all.

> Note that **reserve-ahead is needed regardless**, but for a different reason: §12 uses a periodically persisted ceiling so a Redis failover can't reissue positions. That's a recovery mechanism and it works fine alongside per-arrival `INCR`. Escalating to Hi-Lo just extends the same reservation to serve positions locally too.

**Fairness — worth 60 seconds, and rarely mentioned:**

Strict FIFO by arrival looks fair and isn't. It rewards low latency and fast automation, which means datacenter bots beat humans on phones. The alternative is a **lottery**: accept joins for a fixed window (say 2 minutes), then randomly permute. Bots lose their structural advantage because arriving 40ms earlier stops mattering.

The trade to name: FIFO is *legible* — "you're #12,431, here's your ETA" is something users trust and can plan around. A lottery is *fairer* but opaque, and a user who is told "wait, you might get in" experiences it as worse even when it isn't. **Perceived fairness and actual fairness diverge here, and that's a product decision the architecture has to serve either way.** Interviewers remember candidates who separate those two things.

---

## 10 · Deep dive — 5M QPS of "which seats are left"

**Never answer this per-user from the database.** Compute one artifact and broadcast it.

- **Shape:** a bitmap indexed by seat ordinal plus a monotonic `version`. One bit per seat (selectable or not) is sufficient at ~7.5 KB; two bits (available / held / sold) costs 15 KB and buys a better onsale UI plus room for a future state. Pick either and say which and why — **the design doesn't hinge on it, and treating it as though it does is a tell.** Client already has the static seat topology cached, so it just overlays status.
- **Distribution:** publish the bitmap to an edge cache with a 1–5s TTL. Every request in that window is served from the edge at zero origin cost. During an active onsale, additionally push **deltas** over WebSocket — only changed seat ordinals — which is a few hundred bytes even during peak churn. Clients that miss deltas resync by fetching the full bitmap and comparing versions.
- **Staleness is a feature you design around, not a bug you apologize for.** Users *will* click seats that are already gone. The correct handling is a fast, honest failure from `POST /holds` plus an immediate map refresh — not an attempt to keep 10M clients consistent.

**The line to say:** *"The seat map is an optimistic hint with a well-defined staleness bound. The hold endpoint is the only source of truth, and the UI is built to lose that race gracefully."* Candidates who try to make the read path strongly consistent end up designing something that cannot work at 5M QPS, and the interviewer knows it before they do.

---

## 11 · Deep dive — order commit, payment, and bots

### The saga

```
HELD ──▶ order created ──▶ payment authorized ──▶ seats SOLD ──▶ tickets issued
   │              │                  │
   │              │                  └─ auth fails ──▶ release hold, seat AVAILABLE
   │              └─ hold expired ──▶ 409, seat already gone
   └─ user abandons ──▶ lazy expiry (§7)
```

**Order of operations is the whole point:** hold (cheap, reversible) → authorize (reversible) → commit sale (durable) → capture. Charging before securing inventory produces the worst possible failure: a charged customer with no seat, resolved by a refund and a support ticket.

**Compensation:** if the sale commit fails after a successful authorization, void the auth. If capture fails after the sale commits, **keep the sale** and retry capture asynchronously — the customer is in the building either way, and reversing a confirmed ticket is worse than chasing a payment.

### Bot mitigation — a real requirement here

Unusually for a system design problem, adversarial users are a first-class concern, and the technical answer alone is insufficient:

- **Purchase limits enforced at order commit**, keyed on user + payment instrument + device — never in the UI, which is trivially bypassed.
- **Proof-of-work or CAPTCHA at queue entry**, not at purchase. Make the *expensive* step the one bots must do ten thousand times.
- **Account age / verification gates** and presale codes, which is what the industry actually relies on: move the scarcity to an identity you can't cheaply mint.
- **Rate limits on the availability endpoint** — scrapers hammering the seat map are a meaningful slice of that 5M QPS, and they're the cheapest traffic to shed.

---

## 12 · Data model and sharding — the deliberate hot shard

**Shard by `event_id`.** Every seat, hold, and order for an event lives on one shard. Yes, you shard — the question worth being precise about is *what the sharding is sized by*, because the two possible answers give different keys, different shard counts, and different failure behavior.

| | Sharding for throughput | Sharding for isolation ✓ |
|---|---|---|
| Key | Hash of seat_id / order_id | `event_id` — the transactional boundary |
| Shard count set by | Total writes ÷ node capacity | Number of concurrent hot events to isolate |
| Load distribution | Even, by design | **Wildly uneven, by design** — one shard pinned, a thousand idle |
| Multi-seat order | Distributed transaction / 2PC | Single-shard transaction |
| Blast radius | A node failure degrades every event a little | A node failure kills one event completely |

The global write volume (§3) is ~50–100k/sec across ~50 shards, which no one needs a clever partitioning scheme to survive. So throughput isn't the driver. **Isolation and transactional locality are**, and both point at `event_id`.

**The consequence you must own:** an event cannot be split, so its shard's capacity is a hard ceiling on how fast that event can sell — which is exactly why §9 exists. **Admission control is not a UX feature; it's the mechanism that makes demand fit an unsplittable shard.** If you can state that link unprompted, you've connected two sections most candidates present as unrelated components.

Mitigations for the hot shard, in order:

1. **Dedicated capacity for known-hot events.** You know the schedule weeks ahead. This is a scheduling problem, not a runtime one — a rare case where the operational answer beats the architectural one, and saying so is a point in your favor.
2. **Sub-partition by section** if a single event genuinely exceeds one node, accepting that cross-section orders become multi-partition. Note this doesn't help the common case, since contention concentrates in the *good* sections.
3. Read replicas for anything analytical; **never for the sale path.**

> **Generalize it:** partition on the entity that bounds your transactions, unless throughput genuinely forces you off it. Hash distribution optimizes the metric that's easy to measure (evenness) at the cost of the one that determines correctness cost (locality).

### Storage decisions — every stateful component, explicitly

Most of these are 15-second items. **That doesn't mean skipping them** — it means deriving each fast. Only the last row has enough disagreement to earn prose.

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Seat inventory** | Conditional updates under 166:1 contention, `FOR UPDATE SKIP LOCKED` for best-available | Absolute | **Postgres/MySQL, sharded by `event_id`** | "`SKIP LOCKED` and transactional multi-row acquisition are the whole design (§8). That's a relational feature — a KV store can't give me either, which is why the write volume being small matters so much" |
| **Holds** | Same rows as inventory, TTL semantics via `hold_expires_at` | Recoverable — a lost hold reverts to available | Same rows, **not** a separate store | "A hold is a state on the seat, not a separate object. Splitting it across stores means two things can disagree about one seat" |
| **Availability bitmap** | Rebuilt from the change stream, read 5M QPS | Rebuildable | In-process in the Availability Service, published to a **CDN with a 1–5s TTL** (CloudFront/Fastly; Fastly if you want instant purge on version bump) | "The origin never touches the inventory DB for reads — that's what lets 5M QPS coexist with a single-writer shard" |
| **Queue counter + admitted watermark** | `INCR` and a monotonic watermark, millions of ops in seconds | See below | The one that actually needs discussing | — |
| **Queue token** | Validated at the edge, never looked up | **None — stateless by design** | HMAC-signed, self-describing | "Signing means the edge holds no per-user state, which is what lets the queue tier absorb the herd on commodity nodes" |
| **Session token** | Checked on every hold request | None, but revocation matters | Signed with short TTL, **plus** a Redis deny-list | "Stateless validation for speed; the deny-list is small because it only holds revocations, not sessions" |
| **Orders & payments** | Low volume, strict, saga state | Absolute | Relational, same shard as the event | "Keeping the order on the event's shard means sale commit is a single-shard transaction with the inventory" |
| **Outbox** | Ordered, multi-consumer, replayable | High, bounded | Kafka | "Availability updates, ticket issuance, and analytics all fan out from one commit without coupling to it" |

### The queue state durability tension (say this before you're asked)

§9 puts the queue counter and admitted watermark in Redis, which is right for the throughput. Redis can lose writes, so be precise about how, what happens meanwhile, and what it costs.

**How writes are lost — two separate channels:**
- **Async replication.** The master acks your `INCR` before shipping it to the replica. A master that dies in that window takes those writes with it when a replica is promoted. Typically milliseconds, but unbounded in principle.
- **AOF `everysec`.** Disk fsync happens once per second, so a full restart loses up to a second. This is where the "one second" figure actually comes from.

**What happens during the outage — the line stops, and that's correct.** `INCR queue:seq:{event_id}` fails, so new arrivals get no position. `GET queue:admitted:{event_id}` fails, so waiting clients can't learn their position and keep polling with backoff. **Fail closed on both.** Nobody is admitted who shouldn't be, and the degradation is "the queue stalls" — the most benign failure this component can produce.

**Why this isn't a revenue outage: the session token is stateless.** Anyone already admitted holds a signed token validated by signature and expiry at the booking service, with **no Redis lookup on the hold path**. They keep buying straight through the incident. **Redis going down stops new admissions and nothing else** — which is the single most important property of this design and the reason the queue tier can be run on cheap, lossy infrastructure at all.

**What each rewind actually costs** (the counter is the worse one, which is not the intuitive answer):

| Lost | What happens | Severity |
|---|---|---|
| **`queue:admitted:{event_id}`** rewinds | The watermark re-advances through positions it already covered. Those users **already hold tokens**, so re-admitting them is a no-op — this is *idempotent replay*, not over-admission. Cost is a temporary stall in the effective admission rate while it re-covers ground | Low |
| **`queue:seq:{event_id}`** rewinds | The next arrivals are issued positions **already assigned to other people**. When the watermark passes a duplicated position, *both* users are admitted. That's genuine over-admission, bounded by loss-window × arrival rate | Moderate |

**And even the bad case is survivable, for the reason that runs through this whole page:** over-admission adds load to the booking tier, degrading latency. **It cannot cause a double-sale**, because the conditional update in §7 remains the only thing that decides who gets a seat. Contention, never corruption.

**Concretely, two fixes:**
1. **Counter block reservation (Hi-Lo).** Periodically bump the counter by a large block and persist that ceiling; on recovery, resume above any value that could have been issued. Costs you gaps in the position sequence, which nobody can observe — positions are a display value, not an inventory.
2. **Persist the watermark every few hundred ms and resume from the last persisted value**, deliberately replaying rather than estimating forward. Replaying is idempotent; guessing ahead is not.

*The general shape, shared with the other pages: the fast path is allowed to be lossy precisely because a durable check sits behind it — and because the credential it issues is self-validating, so losing the issuer doesn't invalidate what it already issued.*

---

## 13 · Traps — the ranked list

**Design traps**

1. **Sizing the shards by throughput.** You *do* shard — but ~50–100k writes/sec globally across ~50 shards is unremarkable. If your justification for the partition scheme is write volume rather than transactional locality and isolation, you've picked the right answer for the wrong reason, and the follow-up will expose it.
2. **Two-state inventory (available/sold).** Held seats must be a distinct state or you oversell during every hold window.
3. **A sweeper job as the correctness mechanism for expiry.** Lag becomes lost revenue or double-sells. Lazy expiration in the conditional; sweeper for cosmetics only.
4. **Distributed lock for a hold.** A hold is already a lock with a TTL — make it a durable, queryable row.
5. **`SELECT ... FOR UPDATE` without `SKIP LOCKED`** on best-available. Every transaction queues on the same rows and throughput goes to zero exactly when it matters most.
6. **Optimistic concurrency for best-available.** Correct but produces a retry storm; it's the right tool only for user-selected seats.
7. **Charging before holding.** Charged customer, no seat.
8. **No admission control.** Your booking tier meets 5M QPS and dies; the queue is not optional decoration.
9. **The waiting room behind your own LB.** It must be at the edge or it fails with everything else.
10. **A queue you don't enforce.** If `/holds` accepts requests without a session token, the queue is theater.
10b. **Sharding the queue counter by reflex — or never knowing when to.** One key is one core, ~150k ops/sec, which covers every onsale except a few a year. Pre-sharding it costs you dense positions and clean admission arithmetic for nothing; *not knowing the ceiling* leaves you unable to answer when the megaevent comes up. Name the number, default to `INCR`, escalate per event.
11. **Trying to make the seat map strongly consistent.** Physically impossible at 5M QPS, and unnecessary — the hold call is the arbiter.
12. **Hash-sharding the inventory**, turning every multi-seat order into a distributed transaction.
13. **Purchase limits in the UI only.**

**Interview-performance traps** → see `00-interview-mechanics.md` §6. The three that bite *specifically* here:

14. **Not saying "no double-selling" out loud in the first two minutes.** It's the invariant the whole design serves; leaving it implicit reads as not knowing it.
15. **Defaulting to AP because "availability is always right."** This is one of the few problems where CP on the write path is correct, and reflexively reaching for eventual consistency is a real signal.
16. **Ignoring fairness and bots.** Uniquely for this problem they're first-class requirements with public consequences — an interviewer who has read the news expects them.

---

## 14 · The five-minute skeleton (draw this cold)

1. Two workloads: browse (5M QPS, stale-OK) and buy (60k total writes, strictly serializable). **Separate them completely.**
2. Contention ratio 166:1 is the real problem, not volume.
3. Edge waiting room: Redis `INCR` → signed token → drain at measured capacity → session token required by the booking API.
4. Read path: ~10KB status bitmap + version, edge-cached 1–5s, WebSocket deltas during onsale, clients resync on version gap.
5. Inventory: three states. Hold = row with `hold_expires_at`. **Lazy expiry in the conditional update**, sweeper is cosmetic.
6. User-selected seats → optimistic conditional update. Best-available → `FOR UPDATE SKIP LOCKED`.
7. Multi-seat: one transaction, seats acquired in sorted order to avoid deadlock.
8. Saga: hold → authorize → commit sale → capture async. Reversible actions first.
9. Shard by `event_id`; hot shard is intentional; dedicate capacity for known-hot onsales.

---

## 15 · Variants — what actually changes

**The axis that governs this whole family: is the inventory fungible?**

| Problem | What's identical | What's genuinely different |
|---|---|---|
| **Flash sale (10k of one SKU)** | Queue, admission control, saga | **Fungible inventory** → it's a counter, not a seat map. `DECR` in Redis is atomic and the entire §8 problem evaporates. If you get this one, the hard part is the queue, not the inventory |
| **Airline seats** | Seat map, holds, saga | Hold windows are hours-to-days, not minutes. And airlines **deliberately oversell** — the invariant inverts from "never double-sell" to "double-sell within a modeled no-show rate." Genuinely fun to discuss |
| **Hotel rooms** | Booking flow, payment | Rooms of a type are fungible; you're decrementing a count per date-range. The hard part moves to **interval overlap** across a calendar, not row contention |
| **OpenTable** | Slot inventory, holds | Low contention, so most of §8 is unnecessary. Complexity moves to table-combination logic and turn-time prediction |
| **StubHub / resale** | Inventory, payment | Two-sided: sellers create inventory continuously. Listings go stale across venues; the hard problem is cross-listing sync, not onsale burst |
| **IPO allocation / lottery** | Queue, fairness | No real-time element at all. Batch allocation, and fairness becomes the *entire* problem rather than a section |

---

## 16 · Active recall — answer these cold, no scrolling

**Protocol:** answer **out loud**, in full sentences, as though someone asked. Only after attempting, check the section pointer. Full schedule in `00-interview-mechanics.md` §8.

| # | Prompt | Check |
|---|---|---|
| 1 | How many successful writes does a 60k-seat onsale generate, and why does that number change the design? | §3 |
| 2 | What's the contention ratio, and what does it imply that raw volume doesn't? | §3 |
| 3 | Give three ways to expire a hold. Which keeps correctness out of the background job, and how? | §7 |
| 4 | Why is a distributed lock a strictly worse hold than a database row? | §7 |
| 5 | Two request shapes need two concurrency strategies. Name both, and say why the wrong pairing produces a retry storm. | §8 |
| 6 | What does `SKIP LOCKED` do, what does it cost you, and why is the cost acceptable here? | §8 |
| 7 | Why must the waiting room live at the edge? What makes it enforceable rather than decorative? | §9 |
| 8 | FIFO vs lottery admission: which is fairer, which *feels* fairer, and why is that gap a design problem? | §9 |
| 9 | How do you serve 5M QPS of seat availability? What's the payload, and what's the staleness contract? | §10 |
| 10 | A user clicks a seat that's already sold. Whose job is it to catch that, and what should the UX be? | §10 |
| 11 | State the order of operations for hold → payment → sale, and what breaks if you invert any two. | §11 |
| 12 | Payment capture fails *after* the sale commits. What's the state of the ticket, and why? | §11 |
| 13 | Why shard by `event_id` knowing it creates a hot shard? What's the mitigation, and why is it not architectural? | §12 |
| 14 | What single property of the inventory makes a flash sale dramatically easier than an onsale? | §15 |
| 15 | Which is the CAP choice on the write path, and how do you scope it so it doesn't infect the read path? | §2 |
| 16 | A user abandons at the payment screen. Walk through what happens to that seat, step by step. | §6, §7 |
| 17 | "Ticketmaster runs thousands of events at once — surely the write path needs sharding for volume?" Answer it with numbers. | Header, §3 |
| 18 | Sharding for throughput vs sharding for isolation: different key, count, and failure behavior. Give all three. | §12 |
| 19 | Why does an event's shard capacity determine your admission rate? State the causal chain. | §3, §9, §12 |
| 20 | Why does seat inventory need a relational store specifically? Name the two features. | §12 |
| 21 | Redis dies mid-onsale. What happens to people in the queue, and to people already admitted? Why the difference? | §12 |
| 21b | Which rewind is worse — the position counter or the admitted watermark — and why is it the counterintuitive one? | §12 |
| 21c | At what arrival rate does a single `INCR` counter stop working, and what fraction of real events reach it? | §9 |
| 21d | If you escalate to block reservation, why can't the admission controller drive off watermark arithmetic? | §9 |
| 22 | Why is the queue token stateless but the session token backed by a deny-list? | §12 |
| 23 | Name both queue counters, their exact keys, and the comparison that decides admission. | §9 |
