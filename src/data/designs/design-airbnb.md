# Design Airbnb — Interval Inventory & Search-Dominant Booking

## The question

> *"Design Airbnb. A guest searches for a place to stay in a city over some dates, filters it down, and books it — and the host who owns that place never gets two guests for the same night."*

**The product.** A marketplace of homes. Hosts list a place, set nightly prices, and block off dates they aren't available. Guests search by location and a date range, narrow by the things that matter to them — how many it sleeps, price, a hot tub — browse the results on a map, and book one for a run of nights. A session is dozens of searches and, at most, one booking.

**What a working system delivers**

- "Tahoe, March 3–7, sleeps 6, under $300, hot tub" comes back fast, with places that are genuinely free those exact nights.
- The cabin you book is yours for precisely those nights, and nobody else's.
- A host who blocks a week, or takes a booking on another site, sees those nights leave search almost immediately.

**Why this gets asked.** It looks like a ticketing problem and isn't. Inventory here is a *range of nights* rather than a single seat, and essentially nobody is racing you for a specific cabin — so the difficulty quietly relocates from the write to the query, and noticing that relocation is the exercise.

---

**Archetype:** non-fungible **interval** inventory with near-zero contention and a search-dominant read path.
**Cousins that reuse ~70% of this page:** Vrbo, Booking.com (with the fungibility caveat in §15), campsite and venue rental, equipment hire, meeting-room booking, doctor-appointment scheduling with variable durations.

**What's actually being graded:** whether you notice that **the hard problem moved.** Ticketmaster is a contention problem where search is trivial. Airbnb is the inverse: nobody is racing you for a specific cabin, but "available places in Lake Tahoe, March 3–7, sleeps 6, under $300, with a hot tub" is a **geo + multi-attribute + interval-availability** query that has to return in 300ms. The correctness problem is real but small; the search problem is the design.

**Contrast to have ready:** *A ticket is a point in time and the invariant is a row lock under 166:1 contention. A stay is an **interval**, and overlap — not row identity — is what conflicts. Contention drops to roughly 1, which deletes the entire waiting-room and `SKIP LOCKED` apparatus, and the freed complexity budget goes to search and to a booking saga that spans days.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "Two things make this different from a ticketing system. First, inventory is an **interval**, not a point — booking the 3rd through the 7th conflicts with the 5th through the 9th, so conflict is range overlap rather than row contention, and I want the database to enforce that declaratively rather than checking it in application code. Second, **contention is essentially one** — nobody else is trying to book that specific cabin at that moment — so I don't need queues or admission control, and the complexity budget moves to **search**, which is genuinely hard here: geospatial, multi-attribute, and filtered by availability over a date range. I'd like to scope to search, booking, and the availability model, go deep on search and on the overlap constraint, and name pricing, messaging, and payouts as subsystems."

**Why open this way:** it demonstrates you've recognized the archetype *and* its inverse, and it moves the round toward search before an interviewer can park you on double-booking, which is the smaller problem here.

---

## 1 · Functional requirements

1. **Search listings** by location, date range, and filters; see results with prices.
2. **Book a listing** for a date range — no double-booking, ever.
3. **Hosts manage availability and pricing**, including blocking dates.

**Out of scope (say them):** messaging, reviews, payouts and host banking, identity verification, Experiences, dynamic pricing models.

**Below the line, likely follow-ups:** instant-book vs request-to-book (§6 Flow C and §9 — the two have genuinely different concurrency), external calendar sync (§10 — the actual dominant source of double-bookings), cancellation policies.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Search latency** | **p95 < 300ms** | It's the product. Every session is many searches and at most one booking |
| **Booking correctness** | **No overlapping confirmed reservations. Absolute** | Two guests at one cabin is unrecoverable in person. But note contention is ~1, so this is *cheap* to guarantee |
| Search freshness | Booked dates disappear within ~1 min | Showing an unavailable listing wastes a click; showing it for an hour is a support ticket |
| Availability (search) | 99.99% | Search down = no revenue |
| Availability (booking) | Prefer consistency; a failed booking is retryable | Unlike an onsale, the guest will simply try again in a minute |
| Read:write ratio | **~1000:1 at peak** | 100k searches/sec against ~100 bookings/sec. This ratio *is* the architecture — but see §3, it's the *contention* ratio that picks the write mechanism |
| Scale | ~7M listings, ~2M bookings/day, ~100k searches/sec peak | Drives §3 |

**The sentence that earns the point:** *"Correctness here is easy and search is hard, which is the opposite of a ticketing system — so I'm going to spend my time proportionally, and I'll use a database constraint for the correctness part rather than building a concurrency mechanism I don't need."*

---

## 3 · Numbers that reframe the problem

**The ratio that decides everything**

- ~2M bookings/day ≈ **23 writes/sec.** Peak maybe 100/s. **This is nothing.** One Postgres instance handles it with room to spare.
- ~100k searches/sec peak against ~100 bookings/sec peak: **a read:write ratio near 1000:1 peak-to-peak**, or ~4,000:1 comparing peak reads to the daily write average. **Separate those two levels out loud** — the peak figure is the one that sizes the search tier.
- **Contention ratio ≈ 1.** Two guests racing for the same listing *and* overlapping dates within the same few seconds is genuinely rare — and the design still has to handle it, but with a constraint, not an architecture.
- **The contrast with Ticketmaster is not the ratio.** That system is read-dominant too — 5M QPS of seat-map polling against 1–2k writes/sec on the hot shard. What differs is **contention**: 166 users per seat there, ~1 here. Two systems can share a read:write ratio and still need completely different write paths, and saying that is worth more than either number.

**Search — where the cost actually is**

- 7M listings × ~2KB of searchable attributes ≈ **14GB.** The entire searchable corpus fits in memory on one large machine; it's sharded for query throughput and blast radius, not capacity.
- **Availability is the expensive dimension.** 7M listings × 365 nights ≈ **2.5B night-rows** if materialized per-night. That's the number that decides §7's data model.
- A typical query filters geo + dates + 5–10 attributes and sorts by a ranking score. **Availability filtering is the part that doesn't fit a normal inverted index**, and saying so identifies the actual difficulty.

**Storage**

- Reservations: ~700M/year × ~500B ≈ **350GB/year.** Small.
- **Nothing here is large.** Say it plainly — the interesting engineering is query shape and correctness, not volume, and pretending otherwise wastes the round.

---

## 4 · Core entities

- **Listing** — id, host_id, lat/lng, capacity, amenities[], base_price, instant_book_enabled
- **Reservation** — id, listing_id, guest_id, **`stay_range` (a date range type)**, status, total_price, idempotency_key
- **AvailabilityRule** — listing_id, date range, blocked / price_override / min_nights
- **CalendarSync** — listing_id, external platform, ical_url, last_synced_at, sync_token
- **SearchDocument** — denormalized listing + a compact availability representation (§7)

**Load-bearing details:**

- **`Reservation.stay_range` is a range type, not two columns.** `daterange(check_in, check_out, '[)')` — half-open, so a checkout on the 7th and a check-in on the 7th do *not* overlap. **Getting that boundary wrong makes same-day turnover impossible, and it's the most common modeling bug on this problem.** A range type also lets the database enforce overlap directly (§8), which two loose columns cannot.
- **Availability is derived, not stored** — computed from confirmed reservations plus host block rules. Materializing 2.5B night-rows as the source of truth means every booking rewrites a range of them and any bug produces phantom availability. **Derive for correctness; materialize only into the search index** (§7).
- **`instant_book_enabled`** splits the booking flow into two genuinely different concurrency stories (§9).

---

## 5 · API

```text
GET  /v1/search?bbox=&checkIn=&checkOut=&guests=&filters=&cursor=
                                        → { listings: [...], nextCursor }

GET  /v1/listings/{id}/availability?from=&to=   → { blockedRanges, prices, minNights }

POST /v1/bookings                       → { bookingId, status }
  body: { listingId, checkIn, checkOut, guests, quoteId }
  header: Idempotency-Key

GET  /v1/bookings/{id}                  → { status, ... }     // poll the workflow
DELETE /v1/bookings/{id}                → cancel
```

**Decisions to narrate, unprompted:**

- **Search returns approximate availability; the booking call is authoritative.** Same principle as a seat map — the index is a hint with a bounded staleness, and the constraint at write time is the truth. Users will occasionally click a just-booked listing, and that must be a clean, fast rejection rather than something you try to prevent.
- **`POST /bookings` returns immediately with a pending status**, because the flow behind it can take seconds (instant-book) or **24 hours** (request-to-book). The client polls or subscribes. **Never hold an HTTP connection open across a host's approval decision.**
- **Idempotency-Key is mandatory** — a retried booking that creates a second reservation charges a guest twice for one stay.
- **Availability is its own endpoint** because the listing page needs a whole calendar, while search needs one boolean per listing. Different shapes, different caching.

---

## 6 · High-level design — flows

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 600" role="img" aria-label="Airbnb high-level design. A search lane carrying 99.9% of traffic: client to search service to Elasticsearch with a geo bounding box and availability bitmap, then hydration. A booking lane: client to booking API to a Temporal workflow whose four steps end at a reservations database with an exclusion constraint. An outbox feeds Kafka, which updates the search index seconds later. A third lane polls external iCal calendars, the real source of double bookings.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">1000:1 read:write — 100k searches/sec against 23 bookings/sec. Search is the hard problem; correctness is one line of DDL.</text>
  <text class="dg-lane" x="30" y="76">SEARCH — 99.9% OF TRAFFIC</text>
  <rect class="dg-box" x="30" y="90" width="110" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="85" y="126.5">Client</text>
  <rect class="dg-box" x="180" y="90" width="160" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="118.5">Search Service</text>
  <text class="dg-s dg-c" x="260" y="134.5">one ES query</text>
  <rect class="dg-box" x="380" y="90" width="250" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="505" y="110.5">Elasticsearch</text>
  <text class="dg-s dg-c" x="505" y="126.5">geo bbox + attrs + availability bitmap</text>
  <text class="dg-s dg-c" x="505" y="142.5">ranked; cursor on (score, listing_id)</text>
  <rect class="dg-box" x="670" y="90" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="110.5">Hydrate</text>
  <text class="dg-s dg-c" x="815" y="126.5">per-night price with host overrides</text>
  <text class="dg-s dg-c" x="815" y="142.5">fees, photos, review aggregates</text>
  <path class="dg-line" d="M 140,122 L 172,122"></path>
  <path class="dg-head" d="M 172,127 L 172,117 L 180,122 Z"></path>
  <path class="dg-line" d="M 340,122 L 372,122"></path>
  <path class="dg-head" d="M 372,127 L 372,117 L 380,122 Z"></path>
  <path class="dg-line" d="M 630,122 L 662,122"></path>
  <path class="dg-head" d="M 662,127 L 662,117 L 670,122 Z"></path>
  <text class="dg-s dg-c" x="505" y="180">no post-filtering — pagination stays correct</text>
  <text class="dg-s dg-c" x="815" y="180">prices computed at hydration, not indexed</text>
  <path class="dg-div" d="M 20,206 L 980,206"></path>
  <text class="dg-lane" x="30" y="232">BOOKING — RARE, TRANSACTIONAL</text>
  <rect class="dg-box" x="30" y="246" width="110" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="85" y="276.5">Client</text>
  <rect class="dg-box" x="180" y="246" width="160" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="268.5">Booking API</text>
  <text class="dg-s dg-c" x="260" y="284.5">idempotency key</text>
  <rect class="dg-box" x="380" y="246" width="290" height="110" rx="8"></rect>
  <text class="dg-t dg-c" x="525" y="273.5">Temporal workflow</text>
  <text class="dg-s dg-c" x="525" y="289.5">1 · insert PENDING — constraint arbitrates</text>
  <text class="dg-s dg-c" x="525" y="305.5">2 · authorize payment, before any wait</text>
  <text class="dg-s dg-c" x="525" y="321.5">3 · confirm → outbox event</text>
  <text class="dg-s dg-c" x="525" y="337.5">4 · durable timer → capture at check-in</text>
  <rect class="dg-good" x="710" y="246" width="250" height="110" rx="8"></rect>
  <text class="dg-t dg-c" x="835" y="281.5">Reservations DB</text>
  <text class="dg-s dg-c" x="835" y="297.5">EXCLUDE USING gist</text>
  <text class="dg-s dg-c" x="835" y="313.5">(listing_id =, stay_range &amp;&amp;)</text>
  <text class="dg-s dg-c" x="835" y="329.5">half-open ranges '[)'</text>
  <path class="dg-line" d="M 140,272 L 172,272"></path>
  <path class="dg-head" d="M 172,277 L 172,267 L 180,272 Z"></path>
  <path class="dg-line" d="M 340,272 L 372,272"></path>
  <path class="dg-head" d="M 372,277 L 372,267 L 380,272 Z"></path>
  <path class="dg-line" d="M 670,301 L 702,301"></path>
  <path class="dg-head" d="M 702,306 L 702,296 L 710,301 Z"></path>
  <rect class="dg-box" x="380" y="380" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="525" y="396.5">outbox → Kafka</text>
  <text class="dg-s dg-c" x="525" y="412.5">search index · notifications</text>
  <text class="dg-s dg-c" x="525" y="428.5">push blocked dates to external calendars</text>
  <path class="dg-line" d="M 525,356 L 525,372"></path>
  <path class="dg-head" d="M 520,372 L 530,372 L 525,380 Z"></path>
  <path class="dg-line" d="M 380,408 L 358,408 L 358,140 L 372,140"></path>
  <path class="dg-head" d="M 372,145 L 372,135 L 380,140 Z"></path>
  <text class="dg-lbl" x="180" y="200">index updates (~seconds)</text>
  <path class="dg-div" d="M 20,460 L 980,460"></path>
  <text class="dg-lane" x="30" y="486">HOST / EXTERNAL — WHERE DOUBLE BOOKINGS ACTUALLY COME FROM</text>
  <rect class="dg-box" x="30" y="500" width="150" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="105" y="522.5">iCal poller</text>
  <text class="dg-s dg-c" x="105" y="538.5">every few minutes</text>
  <rect class="dg-box" x="220" y="500" width="170" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="305" y="522.5">Calendar Sync</text>
  <text class="dg-s dg-c" x="305" y="538.5">detect, don't prevent</text>
  <rect class="dg-box" x="430" y="500" width="180" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="520" y="530.5">Block ranges</text>
  <path class="dg-line" d="M 180,526 L 212,526"></path>
  <path class="dg-head" d="M 212,531 L 212,521 L 220,526 Z"></path>
  <path class="dg-line" d="M 390,526 L 422,526"></path>
  <path class="dg-head" d="M 422,531 L 422,521 L 430,526 Z"></path>
  <path class="dg-line" d="M 610,526 L 835,526 L 835,372"></path>
  <path class="dg-head" d="M 840,372 L 830,372 L 835,364 Z"></path>
  <text class="dg-note" x="660" y="516">conflicts arrive after the fact</text>
  <text class="dg-note" x="30" y="580">A stale search result is fine. Three layers, each fresher than the last: search bitmap → listing calendar → constraint. Only the last is truth.</text>
</svg>
</div>

<p class="diagram-cap">Two paths that touch in exactly one place — an outbox, read seconds later. Draw that gap deliberately: the search lane never reads the reservations database, and saying so is worth more than any box on the board.</p>

**The two properties to point at:**

1. **The search path never touches the reservations database.** It reads an index updated from the change stream — the same read/write split as every other page, at a 1000:1 ratio that makes it especially stark.
2. **The booking path is a long-running workflow, not a request handler.** Steps span services and, in the request-to-book case, days. That shape is what makes durable orchestration worth its cost here (§9).

### Flow A — search

1. `GET /v1/search` with a **viewport bbox** — the lat/lng rectangle the user's map is currently showing, `{north, south, east, west}` — plus dates, guest count, and filters. Pan or zoom sends a new bbox and re-queries, which is why this kind of search feels map-driven rather than city-name-driven.
   - **Why a rectangle rather than a radius:** it's four range comparisons against a BKD tree, cheaper than `geo_distance`, and it matches what the user is literally looking at.
   - **It's also what makes geo-sharding work** (§12): most viewports sit inside one region, so most queries hit one shard.
   - **Edge cases to name:** a viewport crossing the antimeridian must be split into two boxes, and a fully zoomed-out viewport has to be capped or rejected or you're scanning all 7M listings.
2. Search Service builds one Elasticsearch query: **geo_bounding_box** on the viewport, term/range filters on attributes, and an availability filter over the requested nights (§7).
3. Elasticsearch returns candidates with a ranking score. Pagination is cursor-based on `(score, listing_id)` — offset paging drifts as the index updates underneath.
4. **Hydrate:** per-night prices with host overrides, fees and taxes, photos, review aggregates. *(Same insight as the feed page — the index query is cheap and hydration is the real read cost.)*
5. Return. Results are cacheable by (bbox, dates, filters) for ~60s; popular destination-plus-weekend combinations repeat heavily across users.
6. **Failure path — the availability filter is stale:** a just-booked listing appears in results. The listing page's availability call catches it, and failing that the booking call rejects it. **Three layers, each fresher than the last** — accept the staleness rather than trying to make search strongly consistent at 100k QPS.

### Flow B — booking (instant-book)

1. `POST /v1/bookings` with an idempotency key. API validates the quote and starts a **Temporal workflow** keyed on the idempotency key, then returns `PENDING` immediately.
2. Workflow step 1 — **insert the reservation as `PENDING` and let the exclusion constraint arbitrate** (§8). Constraint violation → terminate with `UNAVAILABLE`, and the guest sees a clean rejection. **This is the entire double-booking defense**, and it's one line of DDL.
3. Workflow step 2 — **authorize** the payment. Failure → compensate by deleting the pending reservation, freeing the dates.
4. Workflow step 3 — transition to `CONFIRMED` and emit an outbox event.
5. Consumers: search index update (dates disappear from search), host notification, guest confirmation, **push blocked dates out to external calendars** (§10).
6. Workflow step 4 — **durable timer until check-in**, then capture the payment. Days or months later, and expressing that as a timer rather than a scheduled-job table is exactly what durable execution is for.
7. **Failure path — payment provider is down:** Temporal retries the activity with backoff. The reservation stays `PENDING`, holding the dates. A workflow-level timeout eventually compensates and releases them, so a provider outage can't strand inventory forever.
8. **Failure path — the workflow worker crashes mid-flow:** Temporal replays from its event history on another worker. **This is the actual reason to use it** — a booking half-committed across payment and reservation state is a support nightmare with no clean automated recovery.

### Flow C — request-to-book

1. Same start, but after the constraint check the reservation is `PENDING_HOST_APPROVAL` and **the dates are held** — an interval hold, exactly like a seat hold but measured in hours.
2. **Authorize the payment *before* the wait, not after.** A card declining twenty-four hours later — after the host has already said yes — is the worst possible moment to discover it, and the authorization is what makes the request credible to the host. Card authorizations hold for several days, so a 24-hour window sits comfortably inside one. **This is why §9's decline branch has an authorization to void.**
3. Workflow waits on a **24-hour durable timer** racing a host-decision signal (§9).
4. Approve → rejoin instant-book at step 4: confirm and emit the outbox event. Decline or timer expiry → compensate: void the auth, release the dates, notify both sides.
5. **The hold blocks other bookings for up to 24 hours**, which is a real product cost — hence Airbnb's push toward instant-book. **Say that**: it's a case where a systems constraint drove a product strategy.

---

## 7 · Deep dive — search, where the difficulty actually is

**The framing:** *this is a multi-dimensional filter — geo, attributes, and interval availability — and the third one is the one that doesn't fit a normal inverted index.* Geo and attributes are solved problems; availability is the interesting part.

### Why the obvious approaches fail

**Filter in the database.** `WHERE ST_Within(...) AND capacity >= 6 AND NOT EXISTS (overlapping reservation)` on 7M listings at 100k QPS. The correlated subquery per candidate is fatal, and the query shape is wrong for a B-tree world: `ts_rank` is not a learned ranker, faceting is a second aggregate pass over the same rows, and a dozen *optional* attribute predicates is precisely what an inverted index makes cheap and a composite index cannot.

**Materialize a per-night availability table and join.** 2.5B rows, and a 5-night search becomes a 5-way intersection. Works at small scale; the join cost and index size grow badly, and every booking rewrites a range of rows.

**Search first, then filter availability.** Retrieve 1,000 geo/attribute matches, check availability per listing. Now you're doing 1,000 availability lookups per query, and after filtering you may have 3 results left — so you re-query with a wider net. **Post-filtering that changes result counts breaks pagination**, which is the subtle killer.

### What to build: an availability bitmap in the search index

Encode each listing's availability as a **bitmap over the next ~365–500 nights** — one bit per night, so **46–63 bytes per listing; call it ~50** — and **~350MB for the whole corpus.** Store it on the search document.

A date-range query becomes one bit test. Build a mask with a bit set for each requested night; the listing is a candidate iff **`mask AND bits == mask`** — every requested night available. That's evaluated during the search scan rather than as a join.

**How you actually express that in Elasticsearch — because "AND the two bitmaps" is not a stock filter, and knowing that is the difference between a real answer and a hand-wave:**

- **One indexed term per available night** (`avail: 2026-03-03`, `2026-03-04`, …), and the query is a `must` conjunction over the requested nights. **Lucene intersecting those postings lists *is* the bitwise AND**, skip-list accelerated, and it needs no plugin. **Propose this one first.** It costs index size: ~365 terms per listing.
- **A `binary` doc-values field holding the packed bitmap, plus a filter script.** Tiny index, but you pay script execution per candidate document — so it only wins once geo and attribute filters have already cut the candidate set hard.

*And pre-empt the obvious objection*, because a good interviewer will raise it: yes, night-terms is the same ~2.5B (listing, night) pairs the per-night **table** was rejected for. **The difference is what they are and who owns them** — compressed postings entries in an index built for exactly this intersection, rebuildable from Postgres at any time, rather than rows that a join has to visit and that a booking has to keep correct.

**Why it wins:** availability becomes just another filter dimension evaluated inline, so relevance scoring, faceting, and pagination all keep working normally. **No post-filtering, so result counts are correct and pagination is stable** — which was the real defect in the third approach.

**Cost, volunteered:** the bitmap is denormalized, so it's eventually consistent — a listing booked five seconds ago may still appear. Three-layer defense from Flow A step 6 handles it. And updates require touching the search document on every booking, which at 23 writes/sec is nothing.

### Geo

**Elasticsearch `geo_bounding_box` / `geo_distance`**, backed by BKD trees. Note the difference from Uber: **that page had 2.5M writes/sec into a mutable index and needed H3 cells in memory; here the index is nearly static** — listings rarely move — so a general-purpose search engine's spatial index is exactly right. *Same problem class, opposite write profile, opposite answer.* Being able to say why you're **not** using the Uber approach is a strong signal.

### Ranking and pricing

Ranking is ML-driven (personalization, quality, booking likelihood) and slots on top of retrieval without changing it — same separation as the feed page. **Pricing can't be precomputed into the index** because it depends on the specific date range, length-of-stay discounts, and guest count, so it's computed during hydration for the returned page only. **Sorting by price is therefore genuinely awkward** — either approximate with a precomputed nightly base price or compute prices for a wider candidate set before sorting. Naming that tension is worth a point.

---

## 8 · Deep dive — interval overlap, and letting the database enforce it

### Why this isn't Ticketmaster's problem

A seat is a **point**: one row, one status, conflict is row identity, and at 166:1 you need `SKIP LOCKED` and careful lock ordering. A stay is an **interval**: conflict is *range overlap*, and at contention ~1 you need correctness without throughput engineering. **Different conflict shape, different mechanism.**

### The mechanism: an exclusion constraint

```sql
CREATE EXTENSION btree_gist;

ALTER TABLE reservations ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (
    listing_id WITH =,
    stay_range WITH &&
  ) WHERE (status IN ('PENDING', 'PENDING_HOST_APPROVAL', 'CONFIRMED'));
```

Read it aloud as: *for rows with the same `listing_id`, no two `stay_range` values may overlap, among rows in a blocking status.* Two concurrent inserts for overlapping ranges → one commits, one raises a constraint violation. **The database arbitrates, and there is no application-level check to get wrong.**

**Why this beats a `SELECT ... WHERE overlaps` then `INSERT`:** that read-then-write has a window between the check and the insert, so you'd need `SERIALIZABLE` or an explicit lock on the listing to close it. The constraint has no window — it's evaluated at insert time inside the index. **Declarative beats defensive**, and this is the cleanest example of it in the whole set of pages.

**The half-open range matters.** `'[)'` means `[Mar 3, Mar 7)` and `[Mar 7, Mar 11)` do *not* overlap, so same-day turnover works. Use `'[]'` and you've silently forbidden back-to-back bookings — a costly bug that a test suite of single bookings will never catch.

### The tension with lazy expiry

The Ticketmaster page argued *against* a sweeper: correctness lived in a conditional update that evaluated `hold_expires_at < now()` inline. **You can't do that here**, and the reason is worth stating precisely: **a constraint cannot evaluate `now()`.** The `WHERE status IN (...)` predicate is static, so an expired `PENDING` reservation still blocks — it's in a blocking status until something changes it.

So the trade genuinely inverts:

| | Ticketmaster | Airbnb |
|---|---|---|
| Correctness in | Conditional update with an inline expiry predicate | **Declarative exclusion constraint** |
| Expiry handled by | **Lazy** — evaluated by the next writer | **Active** — a workflow timer or sweeper transitions the status |
| Why | 30s of sweeper lag = lost revenue at peak scarcity | Contention ~1, so lag costs approximately nothing |

**And here Temporal does the expiring**, which is tidier than a sweeper: the workflow owns its own timeout (Flow C step 3), so there's no external job scanning for stale rows. **The expiry is part of the process rather than a separate system inspecting it.**

---

## 9 · Deep dive — the booking saga and why durable execution earns its place here

### What Temporal does and doesn't do

**It does not prevent double-booking.** Say this before anything else, because it's the common confusion: two overlapping bookings are two independent workflow instances, and an orchestrator will happily run both. **Mutual exclusion comes from the constraint in §8; durable execution wraps around it.**

What it does provide is **durable execution**: the workflow's state and history are persisted, so a crashed worker resumes on another machine mid-flow, retries are automatic and configurable, and compensations are ordinary code rather than a hand-rolled state machine plus a reconciliation job.

### Why this flow is worth it and Ticketmaster's isn't

| | Ticketmaster checkout | Airbnb booking |
|---|---|---|
| Duration | Minutes | Seconds to **24 hours** |
| Steps | Hold → authorize → commit → capture | Constraint → authorize → *approval wait* → confirm → external calendar push → **capture at check-in, possibly months later** |
| Services involved | 2 | 5+ |
| Volume | **1–2k writes/sec on one shard** through an onsale (~500k conditional updates) | **~23/sec globally** |
| Verdict | **Overkill** — every workflow event is persisted, so you'd durably record hundreds of thousands of *failed* hold attempts | **Well matched** — long, multi-service, failure-prone, and low-volume |

**The general rule to state:** *durable orchestration is for workflows that are long, cross-service, and rare. It is not for hot paths, and it is never a substitute for a constraint.* Ticketmaster's checkout is short, contended, and enormously frequent — exactly the wrong profile. Airbnb's is long, quiet, and spans days.

**And the durable timers are the clincher.** "Wait 24 hours for host approval," "capture payment at check-in," "release the hold if the guest doesn't complete payment" are all first-class timer constructs rather than rows in a `scheduled_jobs` table that someone has to poll, monitor, and back up.

### How a 24-hour wait actually works

The mechanism is worth being able to explain, because "it waits 24 hours" sounds like something is running for 24 hours, and nothing is.

The workflow blocks on a race:

```java
selector.await(hostDecisionSignal, Duration.ofHours(24))
```

1. **The workflow is evicted from memory.** No thread, no process, no held connection. What persists is a row in Temporal's datastore: a timer task with a fire-at timestamp.
2. **The host's approval is a signal.** Their `POST /bookings/{id}/approve` calls `signalWorkflow(workflowId, "hostDecision", APPROVED)`, which appends an event to that workflow's history and makes it runnable.
3. **The timeout is a task queue entry.** When the timestamp passes, Temporal enqueues a task; **any available worker picks it up, replays the workflow's event history to rebuild state, and resumes at the line after the `await`.**
4. **Whichever arrives first wins**, deterministically. A host approving at 23h59m racing the timer at 24h00m is resolved by Temporal, not by defensive code you write.

**The replay is the whole trick:** "sleeping for a day" and "crashed and recovered" are the same code path. That's why the wait survives a deploy, a worker restart, or an entire cluster rotation — and why you can't get the same property from an in-process `sleep()` or an HTTP request held open.

### Where the non-forward-path actions live

The compensations and notifications for a *failed* approval aren't out-of-band machinery. **They're the else branch, written as ordinary sequential code:**

```java
if (decision == APPROVED) {
    confirmReservation(bookingId);
    captureAtCheckIn(bookingId);           // durable timer, possibly months
} else {
    releaseReservation(bookingId);          // compensation — dates free immediately
    voidAuthorization(authId);              // compensation
    notifyGuestDeclined(bookingId);         // user-facing conclusion
    notifyHostExpired(bookingId);
}
```

**This is what durable execution actually buys.** Without it, "release the dates *and* void the auth *and* email the guest *and* email the host — exactly once, with retries, surviving a crash between any two steps" needs a state-machine table, a scheduler, per-step idempotency keys, and a reconciliation job. With it, it's an `if`/`else`.

Each call is an **activity**, so Temporal retries it independently with backoff and records its completion in history. **A crash after `voidAuthorization` resumes at `notifyGuestDeclined` rather than voiding the authorization twice** — the history *is* the checkpoint.

**Where to draw the line, which is a real design decision:**

| Action type | Where | Why |
|---|---|---|
| **Compensations** (release dates, void auth) | **Inside the workflow** | They're part of the transaction's outcome and must happen. Losing one strands inventory or money |
| **User-facing conclusions** (decline email) | **Inside the workflow** | Guaranteed and ordered, and it's the visible end of the flow the guest is waiting on |
| **Downstream fanout** (analytics, ranking-model updates, search index) | **Outbox → Kafka** | Decoupled, at-least-once, no ordering guarantee needed, and adding consumers shouldn't mean editing the workflow |

**The test:** if the flow is *wrong* when the action doesn't happen, it belongs in the workflow. If the flow is merely *less informed*, it belongs on the event stream.

### Payment ordering

**Authorize before confirming, and treat capture as a separate, much later step.** Be precise about the policy rather than asserting one, because they genuinely differ: **Airbnb charges at booking** (splitting into two payments for far-out stays), while hotels and most whole-home rental platforms authorize now and capture at or near check-in. **The systems consequence is identical either way, and it's the one that matters:** there is a gap of days to months between the authorization and the money finally moving, and something durable has to own that gap. State which policy you're assuming and move on — that's a stronger answer than picking one and defending it as universal.

**Compensations, explicitly:** auth fails → delete the pending reservation, dates free immediately. Confirm fails after auth → void the auth. Capture fails at check-in → **keep the reservation** and pursue the payment out of band, because the guest is standing at the door. *(Same instinct as every other page: never let a payment failure undo a commitment a human is currently relying on.)*

---

## 10 · Deep dive — external calendar sync, the real source of double-bookings

**The honest framing, and a strong thing to volunteer:** *most real double-bookings on this platform don't come from a database race. They come from a host listing the same property on three sites.*

Cross-listing hosts sync via **iCal URLs**, which are polled — typically every 15 minutes to a few hours — and are lossy: the format carries busy ranges, not stable identifiers or reasons. So there's a real window in which a property is booked on Vrbo and still bookable here.

**Mitigations, and none of them close the window fully:**

- Poll frequently for high-value listings, back off for dormant ones.
- Push outbound changes immediately (Flow B step 5) so *your* bookings propagate fast even though inbound is slow.
- Prefer **API-based channel-manager integrations** over iCal where the partner supports them — real identifiers, push updates.
- **Design the reconciliation path**, because the window can't be eliminated: detect the conflict, and have a defined product response — relocate the guest, compensate, penalize the host. **The system's job here is fast detection and clean recovery, not prevention.**

**Why this belongs in a system design answer at all:** it demonstrates you distinguish *the failure mode that dominates in production* from *the failure mode that's fun to design for.* The exclusion constraint is elegant and handles a rare case; calendar sync is unglamorous and handles the common one.

---

## 11 · Deep dive — the availability read path

Three consumers, three representations, and conflating them is a modeling mistake:

| Consumer | Needs | Representation |
|---|---|---|
| **Search** | One boolean per listing for a specific range | **Bitmap on the search document** (§7) |
| **Listing page calendar** | Every blocked date + per-night prices for months ahead | Computed on demand from reservations + rules, cached ~1 min |
| **Booking** | Authoritative yes/no for exactly these dates | **The exclusion constraint** — the only source of truth |

**Freshness increases as you move down**, and each layer is allowed to be wrong in a way the next catches. **State the layering explicitly** — it's the same "optimistic hint plus authoritative write" pattern as the seat map and the feed timeline, and recognizing it as a recurring shape rather than a per-problem trick is exactly what an interviewer wants to hear.

**Deriving the calendar:** confirmed and pending reservations, host block rules, min-night constraints, and advance-notice windows, merged into blocked ranges. This is more subtle than it looks — **a 3-night minimum makes a 2-night gap between bookings unbookable**, so the derived calendar isn't simply "nights without a reservation." Mention it; it's the detail that shows you've thought about real hosts.

---

## 12 · Data model, sharding, and storage decisions

**Shard reservations and listings by `listing_id`.** Every booking transaction touches exactly one listing, so it's single-shard by construction, and the exclusion constraint is enforceable within a partition — **which is the constraint on the constraint: cross-partition exclusion is not a thing**, so the partition key must contain everything the invariant spans. It does here, cleanly.

**No hot shard**, unlike Ticketmaster — the busiest listing on the platform takes maybe a few hundred bookings a year. Say it; the contrast is instructive.

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Reservations** | Range-overlap insert, low volume, strict | Absolute — money | **Postgres**, `EXCLUDE USING gist`, sharded by `listing_id` | "The exclusion constraint is a Postgres feature and it's the entire correctness story. At 23 writes/sec I need no throughput engineering, so I'd take the constraint over anything clever" |
| **Listings** | Read-heavy, rarely mutated | High | **Postgres**, same cluster and same `listing_id` shard key | "Source of truth, co-sharded with reservations so a listing and its bookings stay on one node; the search index is derived from it" |
| **Search index** | 100k QPS, geo + attrs + availability bitmap | Rebuildable from Postgres | **Elasticsearch**, sharded geographically | "Geo sharding keeps most queries single-shard, since searches are bounded by a viewport" |
| **Availability bitmaps** | Updated per booking, read per search | Derived | **A binary field on the ES document** | "Denormalized into the search doc so availability is an inline filter, not a join" |
| **Booking workflows** | Durable state, long timers | High | **Temporal**, backed by its own store | "Long, multi-service, low-volume — the profile durable execution is designed for" |
| **Price cache** | Computed per query, high reuse | None | **Redis**, key `(listing, date range, guests)` | "Pricing can't be precomputed into the index because it depends on the range, so cache it after computing" |
| **Outbox / events** | Ordered, multi-consumer | High, bounded | **Kafka** | "One booking commit fans out to index updates, notifications, and external calendar pushes" |

**The decision worth defending:** Postgres, not a distributed SQL store or a NoSQL design. The exclusion constraint is a Postgres capability, the write volume is trivial, and the transactional boundary is a single listing. **The specific feature drove the choice**, which is a much better answer than "relational because bookings are relational." Name where you'd reconsider: if a single region's listings outgrew one instance, shard by geography — you'd still be running Postgres, just more of them.

---

## 13 · Traps — the ranked list

**Design traps**

1. **Modeling a stay as two date columns instead of a range.** You lose the constraint and hand-roll overlap logic in application code.
2. **Getting the range boundary wrong.** Inclusive-inclusive silently forbids same-day turnover. `'[)'`.
3. **Materializing per-night availability as the source of truth.** 2.5B rows, every booking rewrites a range, and any bug creates phantom availability. Derive for correctness; materialize only into search.
4. **Post-filtering availability after search.** Breaks result counts and pagination — the subtle failure, not the slow one.
5. **Importing Ticketmaster's machinery.** No waiting room, no `SKIP LOCKED`, no admission control. Contention is ~1. Bringing them reveals pattern-matching over reading the problem.
6. **Expecting an orchestrator to prevent double-booking.** Temporal gives durable execution, not mutual exclusion.
7. **Using durable orchestration on a hot path.** Every workflow event is persisted; that's the wrong bill for a 3ms operation.
8. **Applying lazy expiry here.** A constraint can't evaluate `now()`, so expiry must be active — a workflow timer.
9. **Ignoring external calendar sync.** It's the dominant real-world source of double-bookings, and it can't be fully prevented — design the detection and recovery.
10. **Making search strongly consistent.** Three layers, each fresher; the constraint is the only truth.
11. **Reaching for Uber's H3-in-memory index.** That was for 2.5M writes/sec into a mutable index. Listings barely move — a search engine's spatial index is correct here.
12. **Precomputing prices into the search index.** Price depends on the date range and guest count; it can't be a static field. Know that sorting by price is genuinely awkward as a result.
13. **Forgetting min-night rules when deriving the calendar.** A 2-night gap under a 3-night minimum is unbookable, so "no reservation" ≠ "available."
14. **Holding an HTTP connection across host approval.** It's up to 24 hours.

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific here:

15. **Spending the round on double-booking.** It's one line of DDL and near-zero contention. The interviewer chose this problem for search and for the multi-day saga; a candidate who spends 25 minutes on concurrency has answered the ticketing question.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 470" role="img" aria-label="Airbnb five-minute skeleton. Search lane: client, search service, Elasticsearch, hydrate. Booking lane: client, booking API, Temporal workflow, reservations database with an exclusion constraint. Three notes on durable execution, active expiry and derived availability. An external calendar lane, and the three availability layers ordered by freshness.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <circle class="dg-num" cx="22" cy="68" r="9"></circle>
  <text class="dg-num-t" x="22" y="71.4">1</text>
  <text class="dg-lane" x="38" y="72">SEARCH — 100k/SEC</text>
  <rect class="dg-box" x="30" y="86" width="100" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="80" y="118.5">Client</text>
  <rect class="dg-box" x="168" y="86" width="140" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="238" y="118.5">Search Service</text>
  <rect class="dg-box" x="346" y="86" width="250" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="471" y="110.5">Elasticsearch</text>
  <text class="dg-s dg-c" x="471" y="126.5">geo bbox + availability bitmap</text>
  <circle class="dg-num" cx="346" cy="86" r="9"></circle>
  <text class="dg-num-t" x="346" y="89.4">5</text>
  <rect class="dg-box" x="634" y="86" width="200" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="734" y="110.5">Hydrate</text>
  <text class="dg-s dg-c" x="734" y="126.5">prices computed here</text>
  <circle class="dg-num" cx="634" cy="86" r="9"></circle>
  <text class="dg-num-t" x="634" y="89.4">6</text>
  <path class="dg-line" d="M 130,114 L 160,114"></path>
  <path class="dg-head" d="M 160,119 L 160,109 L 168,114 Z"></path>
  <path class="dg-line" d="M 308,114 L 338,114"></path>
  <path class="dg-head" d="M 338,119 L 338,109 L 346,114 Z"></path>
  <path class="dg-line" d="M 596,114 L 626,114"></path>
  <path class="dg-head" d="M 626,119 L 626,109 L 634,114 Z"></path>
  <circle class="dg-num" cx="22" cy="190" r="9"></circle>
  <text class="dg-num-t" x="22" y="193.4">2</text>
  <text class="dg-lane" x="38" y="194">BOOKING — 23/SEC, CONTENTION ≈ 1</text>
  <rect class="dg-box" x="30" y="208" width="100" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="80" y="244.5">Client</text>
  <rect class="dg-box" x="168" y="208" width="140" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="238" y="236.5">Booking API</text>
  <text class="dg-s dg-c" x="238" y="252.5">idempotency key</text>
  <rect class="dg-box" x="346" y="208" width="250" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="471" y="228.5">Temporal workflow</text>
  <text class="dg-s dg-c" x="471" y="244.5">constraint → auth → approve</text>
  <text class="dg-s dg-c" x="471" y="260.5">confirm → timer → capture</text>
  <circle class="dg-num" cx="346" cy="208" r="9"></circle>
  <text class="dg-num-t" x="346" y="211.4">7</text>
  <rect class="dg-good" x="634" y="208" width="200" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="734" y="228.5">Reservations DB</text>
  <text class="dg-s dg-c" x="734" y="244.5">EXCLUDE USING gist</text>
  <text class="dg-s dg-c" x="734" y="260.5">half-open '[)'</text>
  <circle class="dg-num" cx="634" cy="208" r="9"></circle>
  <text class="dg-num-t" x="634" y="211.4">3</text>
  <path class="dg-line" d="M 130,240 L 160,240"></path>
  <path class="dg-head" d="M 160,245 L 160,235 L 168,240 Z"></path>
  <path class="dg-line" d="M 308,240 L 338,240"></path>
  <path class="dg-head" d="M 338,245 L 338,235 L 346,240 Z"></path>
  <path class="dg-line" d="M 596,240 L 626,240"></path>
  <path class="dg-head" d="M 626,245 L 626,235 L 634,240 Z"></path>
  <circle class="dg-num" cx="30" cy="298" r="9"></circle>
  <text class="dg-num-t" x="30" y="301.4">8</text>
  <text class="dg-s" x="48" y="302">Temporal is durable execution, not mutual exclusion — the constraint does the arbitrating.</text>
  <circle class="dg-num" cx="30" cy="322" r="9"></circle>
  <text class="dg-num-t" x="30" y="325.4">9</text>
  <text class="dg-s" x="48" y="326">Expiry is active here, a workflow timer. A constraint cannot evaluate now().</text>
  <circle class="dg-num" cx="30" cy="346" r="9"></circle>
  <text class="dg-num-t" x="30" y="349.4">4</text>
  <text class="dg-s" x="48" y="350">Availability is derived from reservations + rules, and materialised only into the index.</text>
  <path class="dg-div" d="M 440,376 L 440,452"></path>
  <circle class="dg-num" cx="22" cy="384" r="9"></circle>
  <text class="dg-num-t" x="22" y="387.4">11</text>
  <text class="dg-lane" x="38" y="388">EXTERNAL</text>
  <rect class="dg-box" x="30" y="400" width="140" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="100" y="426.5">iCal poller</text>
  <rect class="dg-box" x="210" y="400" width="160" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="290" y="418.5">Calendar Sync</text>
  <text class="dg-s dg-c" x="290" y="434.5">detect, don't prevent</text>
  <path class="dg-line" d="M 170,422 L 202,422"></path>
  <path class="dg-head" d="M 202,427 L 202,417 L 210,422 Z"></path>
  <circle class="dg-num" cx="462" cy="384" r="9"></circle>
  <text class="dg-num-t" x="462" y="387.4">10</text>
  <text class="dg-lane" x="478" y="388">AVAILABILITY — LEAST TO MOST FRESH</text>
  <rect class="dg-box" x="470" y="400" width="150" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="545" y="426.5">search bitmap</text>
  <rect class="dg-box" x="650" y="400" width="150" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="725" y="426.5">listing calendar</text>
  <rect class="dg-good" x="830" y="400" width="140" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="900" y="426.5">constraint</text>
  <path class="dg-line" d="M 620,422 L 642,422"></path>
  <path class="dg-head" d="M 642,427 L 642,417 L 650,422 Z"></path>
  <path class="dg-line" d="M 800,422 L 822,422"></path>
  <path class="dg-head" d="M 822,427 L 822,417 L 830,422 Z"></path>
</svg>
</div>

<p class="diagram-cap">Draw it cold, then check the badges. The three text lines are the ones with no box to hang on — they get said, not drawn, and they are where most candidates go quiet.</p>

1. **~1000:1 read:write.** 23 bookings/sec, 100k searches/sec. **Search is the problem**, correctness is cheap.
2. Inventory is an **interval**, not a point. Conflict is overlap. Contention ≈ 1.
3. **`EXCLUDE USING gist (listing_id WITH =, stay_range WITH &&)`** — the database enforces no-overlap. Half-open ranges `'[)'` for same-day turnover.
4. Availability is **derived** from reservations + rules; only *materialized* into the search index.
5. Search = Elasticsearch: geo bbox + attribute filters + **availability bitmap** (~50B/listing) as an inline filter. **No post-filtering**, so pagination stays correct.
6. Prices computed at hydration, not indexed — they depend on the range.
7. Booking = **Temporal workflow**: constraint check → authorize → (24h host approval) → confirm → durable timer → capture at check-in.
8. **Temporal ≠ mutual exclusion.** It's durable execution around a constraint that does the arbitrating.
9. Expiry is **active** here (workflow timer), not lazy — a constraint can't evaluate `now()`.
10. Three availability layers, increasing freshness: search bitmap → listing calendar → constraint. Only the last is truth.
11. **External iCal sync is the real double-booking source.** Detect and recover; you can't prevent it.

---

## 15 · Variants — what actually changes

**Two axes govern this family: is inventory fungible, and is it a point or an interval?** Fungibility deletes the contention problem; intervals create the overlap problem.

| | **Point** (a moment) | **Interval** (a range) |
|---|---|---|
| **Non-fungible** (this exact unit) | **Ticketmaster** — row contention, `SKIP LOCKED`, admission control | **Airbnb** — this page. Overlap constraints, search-dominant |
| **Fungible** (any unit of a type) | **Flash sale** — a counter. `DECR` is atomic and the whole problem evaporates | **Hotels** — count per room-type per night |

| Problem | What's identical | What's genuinely different |
|---|---|---|
| **Hotels / Booking.com** | Search, dates, the booking saga | **Rooms of a type are fungible**, so it's `count(available) > 0` per date rather than a per-unit overlap constraint. **And hotels deliberately overbook** against a modeled no-show rate — the invariant inverts from "never double-book" to "double-book within tolerance" |
| **Vrbo / Booking (whole-home)** | Nearly everything | This page. The cross-listing sync problem in §10 is *mutual* |
| **OpenTable** | Interval inventory, holds | Much shorter intervals, table-combination logic (a party of 6 = one 6-top or two 3-tops), and turn-time prediction. Search is trivial — you know the city |
| **Equipment / car rental** | Interval overlap, exclusion constraint | Fungible within a class, plus **location logistics**: a unit returned in a different city changes future availability. Genuinely harder inventory |
| **Meeting rooms** | Exclusion constraint, same DDL | No search, no payment, no external sync. **This page's §8 is the entire problem** — a good sanity check that you understand the constraint in isolation |
| **Doctor appointments** | Interval booking | Variable durations, provider-specific rules, and **the interval isn't chosen by the customer** — it's derived from the appointment type |

**The general lesson:** *the conflict shape determines the mechanism.* Point + contended → row locks and admission control. Interval + uncontended → an overlap constraint. Fungible → a counter. Identify which box you're in during the first minute and the mechanism follows.

---

## 16 · Active recall — answer these cold, no scrolling

**Protocol:** out loud, in full sentences. Check the pointer only after attempting. Schedule in `00-interview-mechanics.md` §8.

| # | Prompt | Check |
|---|---|---|
| 1 | Give the read:write ratio and the contention ratio. What do they jointly tell you to work on? | §3 |
| 2 | Why is a stay a range type rather than two date columns? Name two things you'd lose. | §4, §8 |
| 3 | What does `'[)'` mean and what breaks with `'[]'`? | §4, §8 |
| 4 | Write the exclusion constraint and read it aloud in English. | §8 |
| 5 | Why does the constraint beat `SELECT overlapping` then `INSERT`? | §8 |
| 6 | Ticketmaster argued against a sweeper. Why can't that argument apply here? | §8 |
| 7 | Three ways to filter availability in search — name each and its specific failure. | §7 |
| 8 | Describe the availability bitmap: size, the exact bit test, and what it fixes about pagination. | §7 |
| 9 | Elasticsearch has no bitmap-AND filter. Give the two ways to express it and which you'd ship. | §7 |
| 10 | Why is Elasticsearch's geo index right here when H3-in-memory was right for Uber? | §7 |
| 11 | Why can't prices be precomputed into the search index, and what does that make awkward? | §7 |
| 12 | What does Temporal give you, and what does it explicitly *not* give you? | §9 |
| 13 | Why does durable orchestration fit this booking flow but not a ticketing checkout? Give four dimensions. | §9 |
| 14 | Trace the compensations for: auth fails, confirm fails after auth, capture fails at check-in. | §9 |
| 15 | What is the dominant real-world source of double-bookings, and why can't you prevent it? | §10 |
| 16 | Name the three availability representations and which one is authoritative. | §11 |
| 17 | A 3-night minimum with a 2-night gap. What's available, and why does it matter? | §11 |
| 18 | Why must the partition key contain everything the exclusion constraint spans? | §12 |
| 19 | Place Ticketmaster, Airbnb, hotels, and flash sales on the two-axis grid and give each mechanism. | §15 |
| 20 | How do hotels invert the core invariant, and why is that acceptable there? | §15 |
| 21 | Request-to-book holds dates for 24 hours. What's the product consequence? | §6 |
| 22 | What is a viewport bbox, why a rectangle rather than a radius, and what does it enable architecturally? | §6, §12 |
| 23 | What is literally running during a 24-hour host-approval wait? Trace resume by signal and by timeout. | §9 |
| 24 | Host approves at 23h59m; the timer fires at 24h00m. What resolves that race? | §9 |
| 25 | Give the test for whether an action belongs in the workflow or on the event stream. | §9 |
| 26 | Why authorize *before* the 24-hour approval wait rather than after? | §6, §9 |
| 27 | Ticketmaster is read-dominant too. So what actually distinguishes the two write paths? | §3 |
