# Design Uber — Real-Time Ride Matching

## The question

> *"Design the backend for Uber. A rider opens the app, sees cars near them, requests a ride, and gets matched with a driver — then both of them watch each other move on a map until the trip ends."*

**The product.** Two apps against one backend. Drivers drive around all day with the app open, and their phone reports its position every few seconds whether or not anyone is in the car. Riders open the app occasionally, see nearby cars on a map, tap request, and wait ten or fifteen seconds for a driver to accept. Then the ride runs for twenty minutes and ends.

**What a working system delivers**

- The cars a rider sees are genuinely nearby and genuinely free — not a stale picture from a minute ago.
- A rider who taps request gets exactly one driver, and that driver gets exactly one rider. Two riders never end up in the same car.
- Both sides watch a position that moves smoothly for the whole trip, and the trip survives a tunnel.

**Why this gets asked.** The system's dominant load — millions of drivers emitting a location every four seconds — has almost nothing to do with its dominant product action, and the two have opposite requirements about what happens if you lose the data. Then matching, which looks like a geometry question, turns out to be a race.

---

**Archetype:** two-sided geospatial marketplace with a hard real-time matching loop.
**Cousins that reuse ~70% of this page:** DoorDash, Lyft, Instacart, Find My Friends, Yelp/proximity search, on-call dispatch, Google Maps live traffic.

**What's actually being graded:** not "can you name Redis." It's whether you understand that (a) the location firehose and the ride lifecycle have *opposite* durability requirements and must not share a datastore, (b) matching is a concurrency problem before it's a geometry problem, and (c) you can pick one of those and go three layers deep without being led.

---

## 0 · The 60-second frame (say this before you draw anything)

> "Uber is two independent real-time systems that meet at one point. There's a *supply-tracking* system ingesting a location firehose from millions of drivers — high write volume, zero durability requirement, last-write-wins. And there's a *ride lifecycle* system — low volume, strict durability, money attached, state machine semantics. The interesting engineering is at the seam: matching. I'd like to scope to the rider-request-to-driver-assigned path and go deep on the geospatial index and the matching concurrency. I'll treat payments, pricing, and maps routing as named subsystems and come back if you want them."

**Why open this way:** it demonstrates scoping (the staff signal), pre-empts the "you designed everything shallowly" failure, and puts *you* in control of which deep dive happens. Interviewers almost always accept a well-argued scope.

---

## 1 · Functional requirements

Keep to three. Number them; you'll refer back.

1. **Rider requests a ride** from pickup → dropoff, sees a fare estimate and ETA before committing.
2. **System matches** the request to exactly one nearby available driver, who can accept or decline.
3. **Both parties track the trip in real time** through the ride lifecycle to completion.

**Explicitly out of scope (say them, don't just omit them):** payments processing, ratings, Uber Eats, pooled rides, driver onboarding/background checks, fraud.

**Below the line but worth naming:** surge pricing (I'll cover it as a deep dive because it's a common follow-up), airport/venue queues, scheduled rides.

> **Trap:** listing eight functional requirements. Every one you list is a promise to design it. Three is the number that fits the clock.

---

## 2 · Non-functional requirements

State them as *numbers with a justification*, not adjectives. "Highly available" is worth zero points.

| Property | Target | Why this number |
|---|---|---|
| Matching latency | p99 < 5s from request to driver offer | Rider abandons past ~10s; leaves budget for driver accept |
| Location freshness | ≤ 5s staleness for matching | A car at 30mph moves 40m in 3s — finer than that is noise |
| Availability (matching) | 99.99%, favor availability over consistency | A stale/suboptimal match beats no match. Losing a request is revenue |
| Consistency (ride assignment) | **Strong.** One driver ↔ one rider, always | This is the one place you must not be eventually consistent |
| Durability | Ride records: durable. Location pings: disposable | Different systems. This split is the whole design |
| Scale | ~10M concurrent online drivers peak, ~1.5M rides/min peak | Drives the write-path math in §7 |
| Geo-distribution | Region-local; a city never depends on another continent | Latency + blast radius |

**The sentence that earns the point:** *"Availability and consistency have different answers in different parts of this system, so I'm going to split them explicitly rather than pick one globally."*

---

## 3 · Back-of-envelope (memorize these — they should be instant)

Assume, and say you're assuming: 5M daily-active drivers, 10M peak concurrent online, 30M trips/day.

- **Location writes:** 10M drivers × 1 ping / 4s = **2.5M writes/sec.**
  → This single number kills every "just use Postgres/PostGIS" answer. Lead with it.
- **Payload:** ~50 bytes (driver_id, lat, lng, heading, ts, accuracy) → 2.5M × 50B ≈ **125 MB/s** ingest, ~10 TB/day if you retained it all. You won't.
- **Active state in memory:** 10M drivers × ~200B of index entry ≈ **2 GB.** *The entire live supply of the planet fits in RAM on one large box.* That's the insight that justifies an in-memory index and lets you shard for throughput and blast radius, not capacity.
- **Ride writes:** 30M/day ÷ 86400 ≈ 350/s average, ~1.5–3k/s peak with ~10 state transitions each → **~30k writes/s peak.** Trivially handled by a sharded RDBMS. Say so — it stops you over-engineering the ride store.
- **Ratio to internalize:** location traffic is **~1000× the ride traffic.** Any design that routes both through the same path is wrong.

---

## 4 · Core entities

Keep this to a list of nouns first; add fields only where a field carries a design decision.

- **Rider** — id, payment method token, home region
- **Driver** — id, status (`OFFLINE | AVAILABLE | OFFERED | ON_TRIP`), vehicle class, current ride_id
- **DriverLocation** *(ephemeral, not a row in your ride DB)* — driver_id, lat/lng, heading, updated_at, cell_id
- **Ride** — id, rider_id, driver_id (nullable), status, pickup, dropoff, fare_quote_id, timestamps, **version**
- **FareQuote** — id, estimated fare, surge multiplier, route polyline, **expires_at**, signature
- **RideEvent** *(append-only)* — ride_id, type, payload, ts — the audit log + the outbox

**The two fields that are actually load-bearing:**
- `Ride.version` — optimistic concurrency for the state machine (§8).
- `FareQuote.expires_at` + signature — the price the rider saw is a *server-issued, time-boxed, tamper-proof promise* (§11). Candidates almost always model fare as a number on the ride and get caught by "what if the client edits it?"

---

## 5 · API

Small, boring, and correct beats clever. Three endpoints plus a stream.

```
POST /v1/fare-quotes            → { quoteId, fare, surge, etaSeconds, expiresAt }
  body: { pickup: {lat,lng}, dropoff: {lat,lng}, vehicleClass }

POST /v1/rides                  → { rideId, status: "MATCHING" }
  body: { quoteId }
  header: Idempotency-Key: <client-generated uuid>

PATCH /v1/rides/{id}            → { rideId, status }
  body: { action: "CANCEL" }

WS   /v1/rides/{id}/events      ← server-pushed lifecycle events

# driver side
POST /v1/drivers/location       (batched, fire-and-forget, no response body needed)
POST /v1/offers/{offerId}       → accept | decline
```

**Design decisions to narrate, unprompted:**

- **The quote is a separate resource, not a query param.** Two reasons: the rider must commit to a price they were shown, and it gives you a natural place to hang the expiry and the signature. `POST` not `GET` because it has side effects (it reserves/records a price).
- **`Idempotency-Key` on ride creation.** Mobile networks retry. Without this, one tap = two rides = two drivers dispatched = a very expensive bug. Server stores key → rideId for 24h; a repeat key returns the original ride, it does not create a new one.
- **Driver ID never comes from the request body.** It comes from the auth token. Say this once, anywhere in the interview, and you get a free security point.
- **Location POST returns 202 and no body.** It's telemetry, not a transaction.

---

## 6 · High-level design — walk the two flows

Draw two flows, not one box diagram. Boxes without a flow read as memorization.

### Flow A — the supply firehose (write-heavy, disposable)

```
Driver app ──ping/4s──▶ Location Gateway (WS) ──▶ Location Service
                                                    │
                                    ┌───────────────┴───────────────┐
                                    ▼ hot path                      ▼ cold path
                          In-memory geo index               Kafka → S3 / warehouse
                          (sharded by cell, Redis-          (traffic modeling, trip
                           backed for failover)              reconstruction, disputes)
```

**The point of the fork:** the hot path is a mutable, last-write-wins index that only ever answers one question — *who is near here, right now.* The cold path is the durable stream. They have nothing in common except the source. **Never route matching queries through Kafka**; Kafka is a log, not an index, and you'd be adding queue latency to the one thing that must be fresh.

**Step by step:**

1. Driver goes online → `POST /v1/drivers/status {AVAILABLE}`. Driver Service persists status and notifies the matcher that owns that cell.
2. App opens a persistent WebSocket to the nearest regional Location Gateway.
3. Every ~4s the app sends `{lat, lng, heading, accuracy, ts}`. **Driver id comes from the auth token, never the body.** Gateway responds 202, no payload.
4. Location Service computes `h3.latLngToCell(lat, lng, 8)` and compares to the driver's last known cell.
5. **Same cell (~90% of pings):** overwrite lat/lng in place — one O(1) hash write, no index mutation. **Different cell:** remove from the old cell's set, add to the new one; if the two cells have different owners, hand off ownership on the ring.
6. In parallel, the raw frame is produced to Kafka `driver.locations` — fire-and-forget, never in the matching path — landing in S3/warehouse for traffic modeling, trip reconstruction, and disputes.
7. No ping for 30s → mark stale and deprioritize in matching. 60s → evict from the index entirely. Tunnels and dead apps must not appear as available supply.

### Flow B — the demand path (low volume, transactional)

```
Rider app ──▶ API GW ──▶ Ride Service ──▶ Ride DB (sharded by region)
                              │                 │
                              │                 └──▶ outbox → Kafka → notifications, analytics
                              ▼
                        Matching Service ──queries──▶ geo index
                              │
                              └──offer──▶ Notification/Push ──▶ Driver app
```

**The seam:** Matching Service is the only component that reads the supply index and writes to the ride state machine. Making it the single owner of that decision is what makes §8 tractable.

**Step by step — request to assigned driver:**

1. Rider enters a destination → `POST /v1/fare-quotes`. Pricing Service gets a route + ETA from Routing Service, reads the surge multiplier for the pickup cell, and returns a **signed quote with an `expiresAt`**.
2. Rider confirms → `POST /v1/rides {quoteId}` with an `Idempotency-Key`. Ride Service validates the quote is unexpired, unconsumed, and belongs to this rider; inserts the ride as `REQUESTED`; returns **201 immediately without waiting for a match**.
3. Rider app opens `WS /v1/rides/{id}/events`. The gateway registers `user:R → G7` in the connection registry with a heartbeat TTL.
4. Ride Service resolves the pickup cell's owner on the consistent-hash ring and enqueues the match request there. Status → `MATCHING`.
5. Matcher runs the funnel: k-ring → ~200 candidates → filter to `AVAILABLE` + vehicle class → ~50 → haversine sort → top 10 → real road-network ETAs → batch-solve against other requests in the 2–5s window → driver **D**.
6. Matcher marks D `OFFERED` **in its own local state** — single writer, so no lock — and pushes the offer to D with a 15s TTL.
7. **Decline or timeout:** D becomes ineligible *for this request only*; cascade to the next ranked candidate. After ~60s total, fail the request visibly rather than leaving the rider spinning.
8. **Accept:** `POST /v1/offers/{offerId}` → Matcher issues the conditional update `... SET status='DRIVER_ASSIGNED', driver_id=D WHERE id=? AND status='MATCHING' AND version=?`. Zero rows means another matcher already assigned this ride (failover); tell the driver it's no longer available. **This is where "exactly one driver" is actually enforced.**
9. The commit writes a `RideEvent` to the outbox → Kafka → notification fanout and analytics.
10. Push to the rider: look up `user:R → G7`, RPC to G7, emit `{type: DRIVER_ASSIGNED, driver, plate, eta}`. If the push is dropped or the socket reconnects, **the client calls `GET /v1/rides/{id}` and reconciles** — the push is an optimization, not the source of truth.
11. During the trip, D's location frames are routed *directly* to the rider's socket as targeted pushes, bypassing the geo index entirely — different consumer, different path.
12. On completion, status → `COMPLETED` and an outbox event kicks off the async payment capture saga (§9). The trip never blocks on payment.

---

## 7 · Deep dive — the geospatial index

This is the highest-yield dive because most candidates hand-wave it.

### Why the obvious answers fail

**"`SELECT * FROM drivers WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?`"**
A B-tree index on `lat` and a B-tree index on `lng` are two independent 1-D indexes. The planner picks one, scans every driver in a horizontal band across the continent, and filters. Composite `(lat, lng)` doesn't save you — the second column only helps within an exact first-column match, and lat is effectively unique. **The fundamental problem: B-trees are 1-D, geography is 2-D.** Say that sentence.

**"PostGIS with a GiST index."** Correct data structure (R-tree), wrong write volume. 2.5M UPDATEs/sec against an R-tree means constant node splits and rebalancing, plus WAL, plus vacuum on a table where every row is rewritten every 4 seconds. PostGIS is the right answer for *static* geometry (zones, geofences, service areas) — use it there, and say so, which shows you're rejecting it for a reason rather than reflex.

### The actual approach: reduce 2-D to 1-D with a space-filling curve, then shard on it

| Scheme | Mechanism | Strength | Weakness |
|---|---|---|---|
| **Geohash** | Interleave lat/lng bits → base32 string; Z-order curve | Prefix = containment, works in any KV/sorted store, dead simple | Z-order has bad discontinuities; neighbors can share no prefix. Must query 8 surrounding cells. Cells distort badly toward the poles |
| **S2 (Google)** | Project sphere → cube → Hilbert curve → 64-bit cell id | Hilbert preserves locality far better than Z-order; near-uniform cell area; multi-resolution range queries | Squares: the 4 edge-neighbors and 4 corner-neighbors are at *different* distances |
| **H3 (Uber's own)** | Hexagonal hierarchical grid, 64-bit index | **All 6 neighbors are equidistant** — k-ring expansion is a true distance ring; excellent for smoothing/aggregation | Hexagons don't tile hierarchically perfectly (children aren't exact subsets); 12 pentagons exist globally |
| **Quadtree** | Recursive subdivision, splits on density | Adapts to density — one node per Manhattan block, one per Wyoming county | It's a mutable tree: rebalancing under 2.5M writes/s, and it's awkward to shard |

**Pick H3 and justify it with the hexagon property, not because Uber uses it.** The reason hexagons matter is that k-ring queries and surge smoothing both need "everything within distance N," and with squares your diagonal neighbor is 1.41× farther than your edge neighbor, so a square ring isn't a distance ring. With hexagons it is.

**Concrete resolutions to have on hand:** H3 res 8 ≈ 0.74 km² per cell (~460m edge) — a good dense-urban matching cell. Res 9 ≈ 0.1 km² (~175m edge) for very dense zones. Choose so a cell holds tens-to-low-hundreds of drivers at peak.

### The write path, made cheap

Storing every ping is not the problem; *reindexing* on every ping is. Three mitigations, in order of impact:

1. **Only touch the index when the cell changes.** A driver stopped at a light re-pings the same cell 15 times a minute. Compare `new_cell == old_cell`; if equal, update the location value in place (an O(1) hash write) and skip the index mutation entirely. This alone removes ~90% of index churn.
2. **Adaptive ping rate.** 1s on-trip (the rider is watching the car move), 4s available-and-moving, 30s stationary-and-available, backoff on poor connectivity. Frame it as: *ping rate should track information gain, not wall-clock.*
3. **Shard by cell prefix.** Partition the index by H3 res-5/6 parent cell so a shard ≈ a chunk of a city. Now 2.5M writes/s becomes a few thousand writes/s per shard across hundreds of shards, and the failure of one shard takes out one neighborhood, not the planet.

### Physical storage

Redis `GEOADD`/`GEOSEARCH` is a legitimate answer — and you should know **it's implemented as a sorted set scored by a 52-bit geohash**, which is exactly the 1-D reduction above. Knowing the implementation is the difference between naming a tool and reasoning about one.

**Keying.** The key is an H3 cell id; the value is the sorted set of drivers in that cell. Redis Cluster hashes the key to a slot, so **your key choice is your shard choice.** A key like `city:sf` would put every driver in San Francisco on one node and pin a single core at peak — the classic hot key.

Exactly, so there's no ambiguity about what lives where:

| Purpose | Structure | Key | Member | Operations |
|---|---|---|---|---|
| Supply index | Geo set (sorted set under the hood) | `drivers:{h3_cell_res8}` | `{driver_id}` | `GEOADD drivers:{cell} {lng} {lat} {driver_id}` — **note the argument order is longitude first**, which trips people up. Read with `GEOSEARCH drivers:{cell} FROMLONLAT {lng} {lat} BYRADIUS 2 km ASC`, once per cell in the k-ring, merged client-side |
| Cell membership | String + TTL | `driver_cell:{driver_id}` | `{h3_cell}` | Read before every ping to answer "did the cell change?" (§7 step 5). `SET … EX 60`, so a driver who stops pinging ages out of the index without a sweeper |
| Fare quote | Hash + TTL | `quote:{quote_id}` | fare, surge, pickup cell, rider_id, `consumed` | `HSET` on issue with `EXPIRE 300`; single-use enforced at ride creation with `HSETNX quote:{id} consumed 1` — atomic, so two concurrent ride creations can't both spend one quote |

**Sharp edge — keying resolution ≠ query resolution.** These are separate knobs and conflating them is the usual confusion:

- *Keying resolution* decides which node owns the data. Pick it so no single key is hot: res 7–8 in practice.
- *Query resolution* decides how wide the k-ring expands to find candidates. Expand until you have enough drivers, independent of how things are keyed.

**Why not vary keying resolution by density?** Tempting — res 6 in Wyoming, res 9 in Manhattan — but Redis Cluster won't resplit a hot key for you, so you'd need a control plane mapping region → resolution, and every query would have to learn a region's resolution before it could build a k-ring. Not worth it. Key uniformly and fine, and let dense areas simply span more keys. `GEOSEARCH` only searches within one key anyway, so cross-cell queries are already a client-side fan-out and merge — more keys costs you more of something you're doing regardless. **Fan-out is parallel; hot keys are not fixable.**

**Or skip Redis in the read path entirely.** Recall §3: global supply is ~2GB. If the matching service owns cell ranges (§8), it can hold its own slice in process memory and drop a network hop from the hottest loop. That makes it a **stateful, partitioned service, not a stateless one** — instances aren't interchangeable, requests for cell C must route to C's owner via the consistent-hash ring.

**Why local state is acceptable here and would be indefensible for the ride DB:** driver locations are *regenerable*. On crash, the ring reassigns the range and every driver in it re-pings within ~4s, so the new owner's index self-heals — no replication, no replica lag, no consensus, just a few seconds of degraded matching in one neighborhood. Warm-start from a Redis snapshot if you want to shrink that window. This is the same pattern as Kafka brokers owning partitions or Flink keyed state.

**These are a package, not a menu:**

| | Index location | Double-assignment fix | Cost |
|---|---|---|---|
| **A** | External Redis, stateless matchers | Distributed lock (§8 Option A) | Extra hop; defending Redlock |
| **B** | In-process, partitioned matchers | Exclusive ownership (§8 Option B) | You own membership + rebalancing |

You cannot take B's lock-free property with A's stateless scaling. Say which one you're picking and why before you draw it.

> **Trap:** proposing a quadtree because it's the textbook answer, then being asked "how do you rebalance it at 2.5M writes/sec across a cluster." Quadtrees are great for read-mostly spatial data (map tiles, static POIs). Uber's supply is write-mostly.

> **Trap:** forgetting the boundary query. A driver 50m from you can be in an adjacent cell. Every candidate search is a **k-ring**, not a single cell lookup. Mention it before they ask.

---

## 8 · Deep dive — matching, which is a concurrency problem

**The bug the interviewer is hunting for:** two riders request simultaneously in the same neighborhood, both matchers find driver D as nearest, both send an offer, D accepts one, the other rider silently waits for a driver who's already gone.

### Option A — distributed lock (the answer everyone gives)

`SET driver:D:lock <offerId> NX PX 15000` before offering. Works. But: what happens when the lock holder crashes after acquiring? (TTL covers it — but now your correctness depends on a timeout being longer than any GC pause.) What about the lock expiring *while* the driver is deciding? What about Redis failover losing the lock? You end up explaining Redlock and its criticisms. **Usable, but you're now defending a distributed lock, which is a defensive position.**

### Option B — partitioned single-writer (the answer that wins)

Make each geographic shard **owned by exactly one matcher process**, assigned via consistent hashing over the cell space (this is essentially what Uber's DISCO does with ringpop).

- All requests for cell C route to the one matcher that owns C.
- That matcher holds C's supply in local memory and makes matching decisions **serially**.
- Two riders in the same neighborhood are now two items in one queue on one thread. The race *cannot happen*, because there's no concurrency to race.

**The general principle, stated out loud:** *"Rather than coordinate concurrent writers with a lock, I'd rather partition ownership so there's only one writer. Locks are what you reach for when you can't partition."* This transfers to a dozen other problems and interviewers notice it.

**The honest caveat, which you should volunteer rather than be caught on:** exclusivity is only as strong as the mechanism that agrees on ownership. Gossip-based membership converges in seconds, and *during* convergence two matchers can both believe they own a cell — §9 works through why that's survivable.

**Then handle the follow-ups you've just invited:**
- *Cross-boundary requests?* A rider at a cell edge needs candidates from neighbors owned by other matchers. Read from neighbors (reads are safe, stale-tolerant), but **the offer must be issued by the owner of the driver's cell.** So: gather candidates broadly, delegate the offer to the owning matcher. Ownership follows the driver, not the rider.
- *Matcher dies?* Consistent-hash ring reassigns the range; new owner warm-starts its index from Redis/log replay in seconds. In-flight offers expire by TTL and the requests retry. Availability > perfection: a re-offered ride is fine, a double-assigned driver is not.
- *Hot shard (airport, stadium, concert letting out)?* Cells are hierarchical, so split res-6 → res-7/8 for that region under load. Airports usually get a separate policy anyway: a **FIFO virtual queue** per geofence, because "nearest driver" is unfair and gameable when 300 cars are parked in one lot.

### Greedy nearest ≠ good matching

Offer the geometrically nearest driver to each request as it arrives and you get a locally optimal, globally poor assignment: driver A goes to the request that arrived first even though driver B was 30 seconds away from it and A was the only viable option for the request 2 seconds later.

**Batched matching:** accumulate requests over a short window (~2–5s), then solve a **min-cost bipartite matching** (Hungarian algorithm, or a greedy/auction approximation at scale) over the window's riders × candidate drivers. Cost function isn't just distance — it's ETA (road network, not straight line), driver accept-probability, vehicle class, ride duration, and rider wait so far.

**The tradeoff to name:** you're buying a few seconds of latency for a meaningfully better global assignment. That's a *product* decision as much as a technical one, and framing it that way is the staff signal.

### The candidate funnel (cost control)

```
k-ring cell lookup       →  ~200 drivers   (in-memory, microseconds)
filter: AVAILABLE, class →  ~50 drivers    (in-memory)
haversine distance sort  →  top ~10        (cheap math, straight-line)
real road-network ETA    →  10 routing calls (expensive — this is why the funnel exists)
rank + batch solve       →  1 offer
```

**Why haversine before routing:** straight-line distance is wrong (rivers, one-ways, freeways) but it's *monotonically correlated enough* to prune 50 → 10, and routing is 10³–10⁴× more expensive. **Never** route the whole candidate set. Say the words "I'm using cheap geometry as a pre-filter for expensive routing."

### The offer protocol

`OFFERED` is a real state with a real timeout (~15s). On decline or timeout: mark driver ineligible *for this request only* (not globally — declining shouldn't punish supply), and cascade to the next candidate. Cap total attempts and the total time; after ~60s, tell the rider no drivers are available rather than leaving them in a spinner. **A visible failure beats an invisible hang** — that's a real staff instinct, not a platitude.

---

## 9 · Deep dive — ride state, correctness, and money

### The state machine

```
REQUESTED → MATCHING → DRIVER_ASSIGNED → EN_ROUTE → ARRIVED → IN_PROGRESS → COMPLETED
                │            │              │          │
                └────────────┴──────────────┴──────────┴──▶ CANCELLED (with liability rules)
```

Persist transitions with **conditional updates**, not read-modify-write:

```sql
UPDATE rides SET status='DRIVER_ASSIGNED', driver_id=?, version=version+1
WHERE id=? AND status='MATCHING' AND version=?
-- 0 rows affected ⇒ someone beat you. That's not an error, it's the protocol working.
```

**Why optimistic concurrency and not a transaction with `SELECT FOR UPDATE`:** contention on any single ride row is near zero (two writers at most, briefly), so pessimistic locking buys nothing and costs connection-holding time. Optimistic is the right default when conflicts are *rare but catastrophic*.

**Why not just trust the single-writer matcher from §8?** Because the matcher can be partitioned off and a replacement can take over while the old one still believes it's the owner. The DB conditional update is the **last line of defense** — the place where "exactly one driver" is actually enforced. Defense in depth: partition to make conflicts rare, conditional-update to make them impossible. Saying this shows you know that consistent-hash ownership is not a consensus protocol.

### Sharding the ride DB

Shard by **region/city**, not by ride_id hash. Rides are geographically local — rider, driver, matcher, and support ops are all in one region. Region sharding makes every query single-shard, keeps data near its users, and gives you a natural blast radius and a natural compliance boundary (data residency laws are real). The cost is hot shards for large cities, which you handle by splitting a city into sub-regions. *Ride_id hashing gives perfect load distribution and cross-shard everything — the wrong trade here.*

### Payments — do not block the ride on the payment

**Pre-authorize** a hold at ride start (validates the card, reserves funds, catches the fraud case early). **Capture** at completion, asynchronously, via a saga. If capture fails: the ride is still `COMPLETED`, a debt record is created, and the rider is blocked from new rides until it resolves. The alternative — refusing to end a trip because a card declined, with a driver and rider sitting in a car — is a product catastrophe.

**Two idempotency layers, and they're different:** the `Idempotency-Key` on ride creation dedupes *client retries*; the payment idempotency key dedupes *your own internal retries* against the PSP. Distinguish them explicitly; conflating them is a common tell.

### Storage decisions — every stateful component, explicitly

Most of these are 15-second items. **That doesn't mean skipping them** — it means deriving each fast, so you name the access pattern and the tradeoff rather than just the product. Only the last row has enough disagreement to earn prose.

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Geo index (hot)** | 2.5M w/s, point overwrite + k-ring read, last-write-wins | **None — regenerable in ~4s** | In-process per owned cell range, Redis as warm-start (§7) | "Locations regenerate themselves, so I get to trade durability for a dropped network hop in the hottest loop" |
| **Ride store** | ~30k w/s peak, conditional updates with `version`, single-entity transactions | Absolute — money | **Postgres sharded by region** (Citus, or Vitess on MySQL). CockroachDB/Spanner if you'd rather buy the sharding than run it | "I need `WHERE status=? AND version=?` to be atomic — that's a transactional store. 30k/s is small enough that I don't have to be clever, so I'd take the boring option and spend the complexity budget elsewhere" |
| **Fare quotes** | Write once, read once, TTL 2–5 min | None — reissue on expiry | Redis with TTL, **or** stateless HMAC-signed token | "Signed means zero storage and zero lookup, but I can't revoke or enforce single-use. Redis costs a lookup and gets me both — and single-use matters here, so Redis" |
| **Connection registry** | `user/device → gateway`, heartbeat TTL, high churn | None — rebuilt on reconnect | Redis Cluster | "Losing it means brief undeliverable pushes until heartbeat, which is fine because clients reconcile via `GET /rides/{id}` anyway" |
| **Cold location stream** | Append-only firehose, 125 MB/s, replayed in batch | High, bounded retention | **Kafka** (short retention) → **S3 in Parquet**, queried by Spark/Trino | "Never read by matching. It's the traffic model's input and the dispute record, so it wants columnar batch access, not a serving store" |
| **Road graph** | Read-only, rebuilt offline, memory-resident | Rebuildable | Precomputed contraction hierarchies per region, mmap'd | "Immutable between builds, so it replicates trivially and needs no consistency story" |
| **Ring membership** | Which matcher owns which cells | See below | The one that actually needs discussing | — |

### The ring membership tension (say this before you're asked)

§8 claims lock-free matching because ownership is exclusive. **That claim is only as strong as the mechanism that agrees on ownership**, and I glossed it. Two options that disagree meaningfully:

| Approach | Property | Cost |
|---|---|---|
| **Gossip membership** (SWIM, as in ringpop) ✓ | AP — converges in seconds, no external dependency, no coordination on the hot path | **During convergence, two matchers can both believe they own cell C.** Exclusivity is temporarily violated |
| **Consensus-backed** (etcd / ZooKeeper) | CP — ownership is strongly agreed | Adds a coordination service to the critical path whose unavailability halts matching. Availability of the whole system now bounded by it |

Take gossip, and then **say why the violation is survivable**: the DB conditional update in this section is the actual enforcement point. Two matchers can both offer driver D; only one `UPDATE ... WHERE status='MATCHING' AND version=?` succeeds. **Ownership makes conflicts rare; the conditional update makes them impossible.** That's the honest version of §8 — partitioning is an optimization that removes lock contention, not a correctness proof — and volunteering it is far stronger than being caught claiming exclusivity you can't guarantee.

---

## 10 · Deep dive — pushing updates to phones

The rider needs "driver assigned," "driver arriving," and a moving dot at ~1Hz. This is a **fanout-to-a-specific-connection** problem, and it's underrated as a dive because it's where "how does the box on the left talk to the box on the right" gets real.

**Transport:** WebSocket both directions. SSE is a fine argument for the rider (server→client only, auto-reconnect built in, plain HTTP) but drivers need bidirectional anyway for location + offers, so one protocol is simpler operationally. **Polling loses:** at 1Hz across millions of trips you've built a worse WebSocket with more overhead and worse latency.

**The routing problem:** rider R holds a socket on gateway G7. The matcher that needs to notify R is a different process on a different host. How does it find G7?

| Approach | How | Tradeoff |
|---|---|---|
| Connection registry | `user:R → G7` in Redis w/ heartbeat TTL; matcher RPCs G7 directly | Lowest latency, one hop. Registry can be stale during reconnect storms |
| Pub/sub channel per user | All gateways subscribe for their connected users; publisher doesn't care who's listening | Dead simple, no registry. Fire-and-forget: **no delivery guarantee** |
| Kafka topic per gateway | Durable, replayable | Latency + partition management overhead. Overkill for ephemeral pushes |

**Pick the registry, then admit the hole and close it:** pushes are best-effort, so **the client reconciles on reconnect** by fetching current ride state (`GET /v1/rides/{id}`). Design the push as an *optimization over polling*, not as the source of truth. That's the sentence: *"the WebSocket is a latency optimization; correctness comes from the client being able to re-derive state on reconnect."* Candidates who treat pushed events as guaranteed delivery get taken apart on the "what if the phone goes through a tunnel" follow-up — which is not a hypothetical in this domain.

**Bonus that's easy to say:** during an active trip, the driver's location pings should route directly to the rider's socket (a targeted push), not through the general geo index. Different consumer, different path.

---

## 11 · Deep dive — surge pricing (common follow-up)

**Computation:** per H3 cell, over a sliding window (~1–5 min), compute demand (open requests + app-opens) ÷ supply (available drivers). Map the ratio to a multiplier through a step function with a cap.

**Three details that separate a real answer from a hand-wave:**

1. **Spatial smoothing.** A raw per-cell multiplier produces a checkerboard where crossing the street changes the price 1.8×. Smooth over the k-ring of neighbors — *and this is the second place hexagons earn their keep*, because equidistant neighbors make the smoothing kernel actually uniform.
2. **Hysteresis.** Without it the multiplier flaps as the ratio oscillates around a threshold, and riders watching the price jump between 1.4× and 1.6× lose trust. Require the ratio to cross a wider band to change state, and rate-limit changes.
3. **The quote is a signed, expiring promise.** The server computes the fare, signs `{quoteId, fare, surge, expiresAt}` (HMAC) or stores it server-side under `quoteId` in Redis with a TTL (~2–5 min). At ride creation, validate: unexpired, unconsumed, belongs to this rider. This is why `FareQuote` is a first-class entity in §4 rather than a number the client sends back. **The client never tells the server what the price is.**

---

## 12 · ETA and routing (name it, don't rebuild Maps)

- **The graph:** road network, nodes = intersections, edges = segments weighted by traversal time.
- **Why not Dijkstra live:** too slow on a continental graph at millions of QPS. Production uses **contraction hierarchies** or CRP-style precomputed overlays — heavy offline preprocessing, then queries in the millisecond range.
- **The elegant loop worth mentioning:** the driver location firehose from §7 *is* the live traffic feed. Millions of GPS traces continuously reweight the edges. Uber's supply-tracking system and its routing system feed each other. Interviewers like this because it shows systems thinking rather than component recall.
- **In an interview:** treat routing as a black-box service with a latency budget and a cost, and spend your words on the funnel in §8 that limits how often you call it.

---

## 13 · Traps — the ranked list

**Design traps**

1. **One datastore for locations and rides.** The single most common fatal move. 2.5M writes/s of disposable data does not belong in the same system as money. Split it in your first diagram.
2. **Kafka in the matching read path.** Kafka is a durable log, not a spatial index. Use it for the cold path and the outbox; never query it to find nearby drivers.
3. **Ignoring the double-assignment race.** If your design never says the words "exactly one driver," you've missed the actual hard part.
4. **Greedy nearest-driver as the final answer.** Fine as v1 if you *name it as v1* and describe batched matching as the improvement. Fatal if you don't know there's a difference.
5. **Single-cell lookup with no k-ring.** Betrays that you've memorized "use geohash" without thinking about boundaries.
6. **Quadtree without a write story.** Right structure, wrong workload; you will be asked about rebalancing.
7. **Trusting client-supplied fare or driver_id.** Free security points, easily lost.
8. **Blocking ride completion on payment capture.** Reveals you're thinking about data flow, not the human in the car.
9. **Treating pushed WebSocket events as guaranteed.** Phones lose signal constantly; design the reconciliation path.
10. **Sharding rides by hash instead of region.** Optimizes the metric that doesn't matter (even distribution) at the cost of the one that does (locality).

**Performance traps**

11. **Reindexing on every ping.** The cell-unchanged fast path is ~90% of your write load.
12. **Fixed ping rate.** Information gain, not wall-clock.
13. **Routing the full candidate set.** Haversine pre-filter, then route ~10.
14. **One Redis key per city.** Hot key = one core = your bottleneck is a single CPU in a datacenter somewhere.

**Interview-performance traps** → see `00-interview-mechanics.md` §6. The one that bites *specifically* here:

15. **Designing for 10M drivers before one ride works end to end.** This problem's numbers are seductive — 2.5M writes/sec invites you to start at the hardest version. Get a single rider matched to a single driver correctly, then scale it. Interviewers will follow you down; they rarely pull you back up.

---

## 14 · The five-minute skeleton (what you must be able to draw cold)

1. Two systems: supply firehose (disposable, 2.5M w/s) + ride lifecycle (durable, 30k w/s). **1000× ratio.**
2. Supply: H3 index, sharded by parent cell, in memory, cold path forks to Kafka.
3. Demand: quote → ride (idempotency key) → matcher.
4. Matcher owns a cell range via consistent hashing → **single writer, no distributed lock.**
5. Funnel: k-ring → filter → haversine top-10 → real ETA → batched min-cost assignment.
6. Offer with 15s TTL, cascade on decline, DB conditional update as the last line of defense.
7. WebSocket push for updates; client reconciles on reconnect.
8. Region-sharded ride DB; payment pre-auth at start, async capture at end.

---

## 15 · Variants — what actually changes

**The axis that governs this family: does the system have a *demand* side that must be matched, or only supply to track?** Tracking millions of moving things is the easy half — §7 solves it. The hard half is matching, and it only exists when two parties must be paired under contention.

| Problem | What's identical | What's genuinely different |
|---|---|---|
| **DoorDash** | Geo index, matching, real-time tracking | Three-sided (restaurant too); prep-time prediction becomes the hard ML problem; batching multiple orders per courier |
| **Lyft / Grab / Bolt** | Essentially everything | Nothing. If you get this, you're being tested on the same page |
| **Uber Pool** | Supply tracking | Matching becomes a routing/insertion problem: can rider B be inserted into A's route within a detour budget? Much harder optimization |
| **Find My Friends** | Location ingest, geo index | No matching. Read-heavy instead of write-heavy. Privacy/permissions become the design center |
| **Yelp / nearby search** | Geo index, k-ring | Static data → PostGIS/Elasticsearch geo queries are now *correct*. Read-optimized, index rarely mutates |
| **Google Maps live traffic** | The location firehose | No demand side at all. It's an aggregation + graph-weighting pipeline |

---

## 16 · Active recall — answer these cold, no scrolling

**Protocol:** answer **out loud**, in full sentences, as though someone asked. Only after attempting, check the section pointer. Fluent-in-your-head and fluent-out-loud are different skills and only one of them is graded. Full schedule in `00-interview-mechanics.md` §8.

| # | Prompt | Check |
|---|---|---|
| 1 | Why does a composite B-tree index on `(lat, lng)` not solve nearest-driver search? | §7 |
| 2 | What's the write volume for location updates, and what one number do you derive it from? | §3 |
| 3 | Give the specific property of hexagons that makes H3 better than S2 here. Where does it matter twice? | §7, §11 |
| 4 | A driver sits at a red light for 60s pinging every 4s. How many index mutations should occur, and why? | §7 |
| 5 | Two riders, one nearest driver, simultaneous requests. Give two solutions and say why one is better. | §8 |
| 6 | Why is a DB conditional update still necessary if a single matcher owns the cell? | §9 |
| 7 | Why haversine before road-network routing, if haversine is the wrong distance? | §8 |
| 8 | What's wrong with greedy nearest-driver assignment? What replaces it and what does it cost? | §8 |
| 9 | Rider's phone loses signal for 90s mid-trip. Trace what happens and how state converges. | §10 |
| 10 | Why is the fare quote a separate resource with an expiry and a signature? | §5, §11 |
| 11 | Card capture fails at trip end. What is the ride's status one second later, and why? | §9 |
| 12 | Why shard the ride DB by region rather than by ride_id hash? Name the cost. | §9 |
| 13 | Where does Kafka belong in this design, and where would putting it be a mistake? | §6 |
| 14 | Name the two idempotency keys in this system and what each protects against. | §5, §9 |
| 15 | Why can't you have the lock-free matcher *and* a stateless matching service? | §7 |
| 16 | Where does the fare quote live, and what does signing buy vs. cost versus storing it? | §9 |
| 17 | Gossip vs consensus for ring membership: which do you take, and what does it cost you? | §9 |
| 18 | If two matchers can transiently own the same cell, what stops a double-assignment? | §9 |
| 19 | Give the exact Redis key, member, and command for the supply index — including the argument order gotcha. | §7 |
| 20 | How is single-use enforced on a fare quote, and why does that specific command matter? | §7 |
