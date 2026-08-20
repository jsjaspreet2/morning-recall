# System Design Field Guide

> A decision reference for Staff+ product and infrastructure interviews. Not a course, and not a
> set of worked problems — the thing you reach for when you know *what* you're building and have
> to defend *which* and *why*.

## 01 — How to use this guide

### A. WHAT THIS IS, AND WHAT IT DELIBERATELY ISN'T

Most system design material teaches by worked example: here is Twitter, here is Uber, here is the
design. That format is good at building intuition and bad at retrieval — you cannot look anything
up in it, and the moment the prompt is a system nobody wrote a chapter about, you are reasoning
from memory of a specific answer rather than from a method.

This guide is the other half. Every section answers *given this need, what do I choose, what does
it cost me, and what signal tells me to revisit it.* Use it alongside a worked-example resource,
not instead of one:

| Resource | Good at | Use it for |
|---|---|---|
| Alex Xu, *System Design Interview* Vol 1–2 | End-to-end walkthroughs of canonical systems | Building intuition; seeing a whole design assembled |
| Hello Interview | Walkthroughs plus a delivery framework and live-round coaching | Rehearsing the room; problem-specific depth |
| **This guide** | Decision tables, estimation anchors, failure and operational depth, AI-native systems | Look-up during practice; the closing drill; the parts courses skip |
| `Technology Choices` (companion guide) | One page per technology, server and browser: mechanism, when it flips, the line to say | Any question of the form "why Postgres and not X" — and, from §17, "why IndexedDB and not localStorage" |

The division with `Technology Choices` is worth stating plainly, because they used to overlap:
**that guide picks the technology, this one shapes the system.** When a section here needs a store,
it names the *category* and points there rather than re-litigating the comparison.

### B. THE STAFF+ DIFFERENCE

Strong candidates draw a system that scales. The separation happens above that line, and it is
consistent enough to be a checklist:

- **Decide what not to build.** Cutting scope with a reason is a design act, not an omission.
- **Connect technical choices to product semantics.** "Eventually consistent" is meaningless until
  you say *what the user may see stale, and for how long.*
- **Quantify the risk.** A named number beats an adjective every time.
- **Expose failure modes unprompted.** Every box you add is a box that can fail.
- **Describe a credible migration path.** Greenfield answers are the most common senior-level tell.

### C. THE META-PATTERN

For **every box you draw**, be ready with three sentences:

1. **The constraint that forced it.** If you can't name one, you don't need the box.
2. **The failure mode it introduces.** A cache adds staleness and a stampede path. A queue adds lag
   and a poison-message path. Nothing is free.
3. **The simpler fallback at one-tenth the scale.** This proves you added it deliberately rather
   than by reflex, and it is the single most reliable way to sound senior rather than rehearsed.

Run this pattern out loud two or three times in a round and you will not need to say the phrase
"it depends" once.

### D. WHERE TO LOOK

| § | Section | What you retrieve from it |
|---|---|---|
| 02 | Run the room | The 45-minute shape, scoping, the decision log, signals vs anti-signals |
| 03 | Estimate and set SLOs | Capacity math, a worked estimate, latency anchors, RPO/RTO |
| 04 | APIs and data | Contracts, idempotency, schemas, indexes, pagination, IDs |
| 05 | Scale reads and writes | Escalation order, caching, replicas, partitioning, hot keys |
| 06 | Asynchrony | Queue vs log, delivery semantics, outbox, backpressure |
| 07 | Correctness | Invariants, contention, isolation, consistency, CAP, replication |
| 08 | Realtime and search | Delivery ladder, connection plane, fanout, search, geo, collaboration |
| 09 | Failure and regions | Timeouts, retries, shedding, topologies, multi-region, DR |
| 10 | Operate and evolve | Observability, security, privacy, rollout, migration, ownership |
| 11 | AI-native systems | Model calls, chat, RAG, agents, injection, evals |
| 12 | The LLM blueprint | A ChatGPT-shaped walk-through, LLM estimation anchors, cost levers |
| 13 | A worked design | One system taken end to end, showing the sections in use |
| 14 | Matrices and the drill | Prompt → likely deep dive, the closing check, lines to rehearse |

**On every number in this guide:** they are estimation anchors for reasoning out loud, not capacity
promises. Real throughput depends on payload, access pattern, indexes, durability settings,
hardware, and your tail-latency target. Saying a number and then saying *what would change it* is
the point; saying a number as if it were a fact is worse than saying nothing.

## 02 — Run the room

### A. THE 45-MINUTE SHAPE

| Minutes | Phase | What "done" looks like |
|---|---|---|
| 0–5 | **Frame** | Users, the top three or four capabilities, what's explicitly out of scope, and *the one product invariant that must never break* |
| 5–10 | **Quantify** | Read/write QPS, payload and storage growth, fanout, p95/p99 targets, availability, durability, geography |
| 10–20 | **Contract** | Core entities, 2–4 representative APIs or events, the data model, and which side owns what |
| 20–35 | **Design the critical path** | The one or two flows that carry the product, drawn and *walked* |
| 35–42 | **Deep dive** | The hardest thing, taken to the level of a mechanism |
| 42–45 | **Close** | Biggest risk, what you'd build first, what you'd measure |

The two reliable ways to lose the round are starting to draw at minute three, and touring every box
shallowly until the clock runs out. Watch the 35-minute mark: if you are not deep in something
specific by then, cut breadth yourself and go deep without being asked.

### B. REQUIREMENTS THAT CHANGE THE ARCHITECTURE

Most clarifying questions are decoration. These change the drawing, which is what makes them worth
the minutes:

| Ask | If the answer is yes, the design gains |
|---|---|
| What must never break, even during an outage? | The invariant that decides your consistency mechanism |
| Is any of this multi-region or residency-constrained? | Home regions, routing, replication topology, failover plan |
| Can two actors touch the same entity at once? | A contention mechanism (§07 B) and a stated isolation level |
| Is there a hard latency target on a specific flow? | Caching, precomputation, denormalization, edge placement |
| Does anything need replay, audit, or reconstruction? | An append-only log and derived projections |
| What is the read:write ratio? | Whether you pay at write time or read time (§08 C) |

Naming one that *doesn't* apply and saying so also scores — *"there's no multi-writer editing here,
so I'm not going near CRDTs"* shows you considered and rejected rather than never knew.

### C. THE DECISION LOG

Keep a small running table in a corner of the board and add to it as you go. It costs about five
seconds per row, it makes the conversation auditable, it stops you designing in circles, and at the
end you read it back as a summary you didn't have to compose under pressure.

| Decision | Why | Cost / revisit signal |
|---|---|---|
| Cache-aside on the feed | 100:1 read ratio; 30 s staleness acceptable | Invalidation complexity; revisit under 80% hit rate |
| Single-region primary | Writes need one authoritative order | RTO too high; revisit when a second region needs local writes |
| Queue the thumbnailing | The user need not wait for it | Lag; revisit when queue age exceeds the SLO |

The third column is the one that makes this a Staff+ artifact. Anyone can list decisions; naming
the *measurable signal that would reverse each one* is the part that reads as having operated
something.

### D. SIGNALS VS ANTI-SIGNALS

| Signal | Anti-signal |
|---|---|
| Makes a decision after naming the tradeoff | "It depends" with no choice at the end |
| Takes the two risky paths deep | A uniform shallow tour of every box |
| Connects a failure to user impact | Lists replicas with no failure story |
| Names ownership and a migration path | Assumes greenfield forever |
| Pushes back with quantified scope | Adds Kafka, a cache, and sharding by reflex |
| Says a number, then what would change it | Recites a memorized vendor throughput figure |

### E. WALK THE SYSTEM, DON'T JUST DRAW IT

A diagram narrated as an inventory ("here's the gateway, here's the service, here's the database")
is worth much less than the same diagram narrated as a path. Walk three:

**Write path** — auth → validation → idempotency check → authoritative commit → event publication →
projections updated → client confirmation.

**Read path** — routing → authorization → cache or index → source of truth on miss → pagination →
freshness annotation.

**Failure path** — dependency timeout → retry budget consumed → degraded response or enqueue →
alert → recovery and replay.

At each hop, say five things: **latency, consistency, failure behaviour, ownership, and the metric
that proves it works.** You will not do all five at every hop, and you shouldn't — but doing it at
the two hops that matter is what depth sounds like.

### F. WHEN THE INTERVIEWER REDIRECTS

> Summarize your current decision in one sentence, accept the new constraint, and state which
> component or invariant changes as a result.

Steering is almost always signal rather than interruption: they are either testing whether you can
hold a design in your head while it changes, or moving you toward the part they actually want to
score. Defending a decision they have just constrained away is the expensive mistake.

## 03 — Estimate and set SLOs

### A. THE FOUR-LINE CAPACITY MODEL

Use powers of ten, show the equation, round visibly. Precision without measurement is false
confidence, and interviewers hear the difference.

```javascript
avg_qps     = active_users × actions_per_user / 86_400
peak_qps    = avg_qps × peak_factor            // test 2×, 5×, 10×
storage/day = writes_per_day × bytes_per_item × replication_factor
concurrency = arrival_rate × time_in_system    // Little's Law
```

The fourth line is the one people forget, and it is the one that matters most for anything with a
long-lived connection — streams, uploads, WebSockets, LLM responses. A system at 100 requests per
second where each request lives for 10 seconds is a system holding 1,000 things open at once, and
that number sizes the gateway even though QPS says nothing about it.

### B. A WORKED ESTIMATE, END TO END

The point of showing this in full is that the *sequence* is the skill. Any one line is arithmetic.

**Prompt:** a social feed. 100M daily actives, each opening the app and reading the feed ~10 times
a day, posting ~0.2 times a day.

**Reads.**
100M × 10 = 1B feed reads/day. Divide by 86,400 — call it 100,000 seconds, which is close enough
and much faster to say — and you get **≈10k average QPS**. Apply a 5× peak factor for the evening
diurnal hump: **≈50k peak QPS**. At a 2 KB response that's **100 MB/s** leaving the read path
before any cache amplification, which is already the number that tells you a CDN or an edge cache
is not optional.

**Writes.**
100M × 0.2 = **20M posts/day ≈ 230 writes/s average**, maybe 1,000/s at peak. That is a number a
single well-tuned relational primary handles without an argument — so the interesting problem here
was never write throughput, it is fanout. Saying that out loud, at this point, is the whole reason
to do the arithmetic.

**Storage.**
20M posts/day × 1 KB ≈ 20 GB/day of logical post data → **~7 TB/year** before indexes, replication,
and backups. Multiply by ~3 for replication and another meaningful factor for indexes and you are
in the tens of terabytes per year: large, entirely ordinary, and not by itself a reason to shard.

**The conclusion the numbers force.** Read:write is roughly 50:1, so this design pays at write time
— precomputed inboxes — and the celebrity account is the exception that needs a read-time path.
That conclusion came from two divisions, and it is a much stronger opening than asserting "I'd use
fanout-on-write because that's what feeds do."

### C. SIZE ANCHORS

- One day is 86,400 s — **use 100k** for interview math. One year ≈ 31.5M s.
- 64-bit integer: 8 B. UUID: 16 B raw, 36 chars as text. Always add row and index overhead.
- UTF-8 characters are 1–4 bytes. One character is not one byte.
- 1M records × 1 KB ≈ **1 GB logical**, before indexes, row versions, replication, and backups.
- A ~1,500-dimension float32 embedding ≈ 6 KB. 10M of them ≈ 60 GB of raw vectors.
- Always separate three numbers and say which one you mean: **logical data**, **working set** (what
  must be in memory for the hot path), and **physical footprint** (with replication and backups).

### D. LATENCY, ORDER OF MAGNITUDE

| Operation | Rough order | What it means for the design |
|---|---|---|
| CPU, cache, RAM | ns to low µs | Not your bottleneck in a networked system |
| Local SSD read | 100 µs to a few ms | Access pattern and queueing dominate, not the device |
| Same-region RPC or cache hit | sub-ms to a few ms | Fanout multiplies tail latency — see below |
| Indexed database query | a few to tens of ms | Query shape and lock contention decide it, not "the DB" |
| Cross-region round trip | tens to 100+ ms | Writes across regions pay physics; no tuning removes it |
| LLM response | 100 ms to many seconds | Stream it, cancel it, budget it (§12) |

**The fanout consequence is worth internalising:** if a request fans out to 50 dependencies and each
has a 1% chance of being slow, the request is *very likely* to hit at least one slow call. Tail
latency compounds, which is why p99 of a fanout system is dominated by fanout width rather than by
the average dependency.

### E. SLI → SLO → ERROR BUDGET

- **SLI** is a measured user outcome. "Successful checkout completed under 500 ms" — not "database
  CPU."
- **SLO** is the target on that indicator. "99.9% of eligible checkouts in a rolling 30 days."
- **Error budget** is 1 − SLO. It is a *budget*: it funds deliberate risk like faster rollouts.
  Targeting 100% is usually economically wrong and always operationally miserable.

Two definitions do most of the work and most candidates skip both. **Define the eligible
population** — do invalid requests count, does a dependency's failure count against you? And make
availability **end-to-end**: a 200 response carrying the wrong cart is not a success, and an SLI
that can't tell the difference is measuring your servers rather than your product.

### F. AVAILABILITY, RPO, RTO

| Term | The question it answers | Example target |
|---|---|---|
| Availability | How often does the user journey work? | 99.9% monthly |
| RPO | How much committed data may we lose? | ≤ 1 minute |
| RTO | How long until service is restored? | ≤ 30 minutes |
| Durability | Will accepted data survive? | No paid order is ever lost |

RPO and RTO are the two that turn a vague "multi-region for reliability" into an actual
architecture, because they are the only inputs that decide between async replication (cheap, RPO >
0) and synchronous (expensive, RPO = 0). Ask for them before drawing a second region.

> **The line to have ready.** *"I won't size nodes from a memorized vendor QPS figure. I'll derive
> the workload and the bandwidth, choose an initial topology, then benchmark the exact payload and
> query shape at the target p99 with headroom."*

### G. DISTRIBUTIONS THAT CHANGE THE ANSWER

Averages are where designs go to die. Four distributions do the damage:

- **Burstiness.** Diurnal peaks, launches, synchronized cron jobs, retry storms, regional skew. Ask
  what the peak-to-average ratio is; if nobody knows, design for 5× and say so.
- **Power-law popularity.** A handful of celebrity keys carry a wildly disproportionate share of
  fanout and reads. Design for the **p99 account size**, not the average follower count — the
  average follower count in a social system is a number that describes nobody.
- **Tail compounding.** See §D. Fanout width sets p99.
- **Capacity target.** Expected peak, plus failure headroom (you lose a node or a zone and the rest
  absorb it), plus growth runway. State which of the three you are budgeting for, because "we're
  provisioned for peak" and "we're provisioned for peak with a zone down" are different systems.

## 04 — Shape APIs and data around access patterns

### A. CONTRACT BEFORE COMPONENTS

Define the contract before you draw boxes. It forces the entity model into the open, and half the
hard questions in a design surface as soon as you try to write down what a request actually
carries.

- Core resources, identifiers, ownership, the state machine each entity moves through, and the
  invariants that must hold across it.
- **2–4 representative APIs or events** — not an exhaustive REST catalogue. Pick the ones that
  carry the product.
- **Mutations** need: validation, authorization, an idempotency story, a concurrency token, and
  defined response semantics.
- **Reads** need: filters, a sort key, a cursor, freshness, field visibility, and a maximum page
  size.
- **Async work** returns 202 plus a job resource, then a webhook, SSE, or notification. Do not hold
  a request open for minutes.

### B. API DEFAULTS

- **Resource-oriented HTTP** for external APIs; **gRPC** for typed internal RPC; **GraphQL** only
  when client-driven shaping and aggregation genuinely pay for their complexity.
- **Cursor pagination** over a stable total order, commonly `(created_at, id)`. Encode the cursor
  as opaque, and define whether the page set is a snapshot or live.
- **Rate limits** need a scope (user, tenant, IP, token cost), an algorithm, a burst size, and a
  `429` with `Retry-After`. Bound page size and query cost too — an unbounded query is a rate limit
  you forgot to write.
- **Errors** carry an HTTP status, a stable machine-readable code, a safe human message, and a
  request/trace ID. Only explicitly transient classes are retryable, and the client should be able
  to tell which from the code alone.

### C. IDEMPOTENCY, PROPERLY

Idempotency is a property you **enforce and test**, not one you inherit from a verb. `PUT` is
defined as idempotent at the protocol level, and a buggy `PUT` handler will still charge a card
twice — the definition constrains what the method *means*, not what your code *does*.

The mechanism that actually works:

1. The **initiator** generates an idempotency key and sends it with the unsafe request.
2. The receiver binds that key to **caller + operation + a hash of the payload**, so the same key
   with different content is an error rather than a silent replay of the wrong thing.
3. The receiver stores the **terminal response** against the key, with a retention window longer
   than the caller's maximum retry horizon.
4. A replay within the window returns the stored response and performs no new side effect.

The failure everyone hits: the request that timed out *ambiguously*. The server may have committed.
The initiator must be able to retry safely, which is exactly what the key buys — and it is why
"idempotency" and "retry policy" are one design decision, not two.

**Who generates the key — the rule, and why it isn't always the client.** The key must be *stable
across every retry of the same logical operation*. That single constraint decides ownership: it
belongs to **whoever owns the retry loop**, because only they can guarantee the second attempt
carries the same key as the first. A server that minted the key on arrival would mint a fresh one
on the retry and defeat the entire mechanism.

That plays out three different ways, and conflating them is a common muddle:

| Situation | Who supplies the key | What it is |
|---|---|---|
| Browser or mobile client → your API | The client | A UUID generated once, before the first attempt, and reused on retry |
| Your service → a downstream service | **Your service** — it is the client here | Usually *derived* rather than random: `hash(order_id + "capture")` |
| Consuming a message off a log or queue | **Nobody generates one** — you derive it | The producer's event ID, or `(topic, partition, offset)`, or a natural business key |

The third row is the one worth being precise about, because it is where the word "idempotency key"
starts to mislead. A Kafka consumer is not handed a key by a caller and there is no request to
replay — at-least-once delivery means the *same message* can be redelivered, so the dedupe
identifier has to be something already inside it. In practice that is an event ID the producer
assigned at publish time, which is exactly what the outbox pattern gives you for free: the outbox
row's primary key **is** the event ID, minted inside the same transaction as the business write
(§06 D). Falling back to `(topic, partition, offset)` works but is more brittle — it breaks under
partition reassignment and can't survive a topic being rebuilt.

**Derived beats random, wherever you can manage it.** A random UUID must be persisted by the
initiator *before* the first attempt, or a crash between generating and sending loses it and the
retry duplicates. A key derived deterministically from stable inputs — the entity ID plus the
operation name — needs no such storage and reconstructs itself identically after any crash. Reach
for a random key only when the operation has no natural identity, which is mostly "create a new
thing" and mostly solvable by having the client name the thing it is creating.

Two smaller consequences worth having ready. A server **can** legitimately generate keys — for the
hop it is about to make, deterministically from the inbound request, which is how idempotency
composes across a chain of services rather than stopping at the first hop. And the retention window
is a real design parameter: it must outlive the longest retry horizon of anything upstream,
including a message that has been sitting in a DLQ for three days before somebody replays it.

### D. QUERY-FIRST MODELING

List the dominant reads and writes **first**, then pick the store and the keys. In a non-relational
model this usually means one table or projection per access pattern; the model *is* the query list.

| If the dominant need is | Start with | And watch for |
|---|---|---|
| Transactions, joins, constraints | Relational | Hot rows, connection count |
| Key-based scale, predictable latency | Dynamo-style KV | Rigid access patterns, hot partitions |
| Wide, write-heavy rows | Wide-column / LSM | Compaction cost, read amplification |
| Text relevance and facets | Search index | Indexing lag; never the source of truth |
| Multi-hop traversal | Graph | Partitioning, supernodes |
| Large immutable bytes | Object store | Metadata and ACLs live elsewhere |

This table picks a *category*. For which specific technology inside a category and why — Postgres
versus Cassandra versus DynamoDB, the numbers, and where each one flips — see the `Technology
Choices` guide, which exists to answer exactly that and does it in more depth than belongs here.

### E. NORMALIZATION IS A DIAL

- **Normalize authoritative mutable state.** It exists to prevent update anomalies, and that is a
  correctness argument, not an aesthetic one.
- **Denormalize read paths** when the read:write ratio and the latency target justify the staleness
  and the repair machinery you are taking on.
- Some duplication is not a performance hack at all: a purchased line item copying the price and
  product name is a **historical snapshot**, and normalizing it away would be a correctness bug.
  Know which kind of duplication you are creating.
- For every duplicated field, name four things: **the owner, the propagation mechanism, the
  acceptable lag, and the reconciliation job.** A duplicated field with no reconciliation job is a
  field that will be wrong.

### F. INDEXES: MATCH THE QUERY

| Index type | Serves | Cost to know |
|---|---|---|
| B-tree | Equality and range | Composite order matters: equality columns first, then range/sort; check leftmost-prefix behaviour |
| Covering / index-only | A hot narrow query, with no heap fetch | Extra write amplification and storage |
| Partial | Only the hot subset — active rows, recent rows | Planner must actually match the predicate |
| Unique | Making an invariant race-safe | It's a constraint first and an index second |
| GIN / inverted | Terms, arrays, JSON | Write cost; index size |
| GiST / R-tree | Spatial and range types | Tuning is workload-specific |
| BRIN | Huge, physically ordered tables | Useless if physical order doesn't correlate |
| HNSW / IVF | Approximate vector search | Memory-bound; recall/latency is a tuning dial |

Two habits: avoid standalone low-cardinality indexes (an index on a boolean rarely earns its write
cost), and build large indexes with an **online/concurrent** migration plan while watching write
amplification. "Add an index" is a write-path decision wearing a read-path costume.

### G. IDS, TENANCY, AND LIFECYCLE

- **Time-sortable globally unique IDs** — UUIDv7 or Snowflake-like — when you need decentralized
  creation *plus* index locality. Random UUIDv4 as a primary key scatters B-tree inserts across the
  whole index, which is a real write-throughput cost. Hide internal sequential IDs wherever
  enumeration would leak volume.
- **Multi-tenancy** usually means carrying `tenant_id` through keys, indexes, authorization,
  quotas, and shard routing — every one of those, not just the `WHERE` clause.
- **Lifecycle** is part of the design: retention, soft versus hard delete, tombstones, legal hold,
  backup expiry, compaction, and — the one that is always skipped — **tested restore**.
- **Schema evolution** is always the same five steps: **expand → backfill → dual-read and verify →
  cut over → contract.** Never design a change that requires an atomic fleet-wide deploy.

## 05 — Scale reads and writes deliberately

### A. THE ESCALATION ORDER

Move down these ladders only when a number, an SLO, or an operational constraint forces you to.
Skipping rungs is the most common over-engineering tell in the round, and starting at the top with
a stated trigger for the next rung is one of the cheapest senior signals available.

| # | Reads | Writes |
|---|---|---|
| 1 | Fix the query, the index, the connection use | Fix the transaction and query; take vertical headroom |
| 2 | CDN and client/browser cache | Batch within one transaction or round trip |
| 3 | Cache-aside on hot objects | Queue the non-interactive work |
| 4 | Read replicas and projections | Partition by access pattern |
| 5 | Denormalize and precompute | Adopt a write-optimized log/LSM store |

> *"Before I shard, I'd validate the query shape, one-node headroom, caching, and replicas with a
> benchmark. Sharding is the most expensive thing on this list and the least reversible."*

### B. THE CACHE DECISION CARD

Five questions. Answer all five and you have said everything a cache answer needs.

- **What** are you caching — an object, a query result, a page fragment, a computation, a negative
  result, or a model response?
- **Where** — browser/CDN, process-local, distributed cache, or a materialized projection?
- **Freshness** — TTL, explicit invalidation, versioned key, or never-expire with async refresh?
- **Ownership** — the source of truth stays elsewhere; define the refill path and the repair path.
- **Economics** — expected hit rate, object size, eviction behaviour, the extra network hop, and
  crucially *whether the origin can survive a miss storm*.

### C. CACHE PATTERNS

| Pattern | How it works | Buys you | Costs you |
|---|---|---|---|
| **Cache-aside** | App checks cache, loads from source on miss, populates | The default; resilient to cache loss | First miss is slow; invalidation is your problem |
| **Read-through** | The cache library loads on miss | Cleaner call sites | Tighter coupling to the cache layer |
| **Write-through** | The write path updates the cache too | Fresher reads | Higher write latency; dual-write care |
| **Write-behind** | Buffer writes, flush asynchronously | Very fast writes | Durability, ordering, and recovery get hard |

### D. CACHE FAILURE MODES

| Failure | What happens | The fix |
|---|---|---|
| **Stampede** | A hot key expires; a thousand requests miss simultaneously and all hit the origin | Request coalescing / single-flight, jittered TTL, probabilistic early refresh, stale-while-revalidate |
| **Hot key** | One key exceeds a single cache node's capacity | Local cache in front, replicate the key across nodes, coalesce, split the object, special-case the celebrity path |
| **Cold start** | Cache restarts empty; origin sees 100% of traffic | Warm critical keys, ramp traffic, keep origin headroom, shed optional work |
| **Poisoned or stale data** | A bad value is served long after the source is fixed | Schema/version in the key, bounded TTL, invalidate on rollback, reconciliation |
| **Cache outage** | The cache tier goes away entirely | Bypass at a *safe rate* only — otherwise a cache failure becomes a database failure |

> *"The cache is an optimization, not a correctness dependency. I'll define a bounded-staleness
> contract and an origin-protection mode before I rely on its steady-state hit rate."*

That last failure mode deserves the emphasis. A system that cannot survive its cache being empty
does not have a cache — it has an undeclared tier of its database with no durability.

### E. READ REPLICAS AND PROJECTIONS

Replicas scale read QPS and isolate workloads. They introduce replication lag, stale reads, failover
behaviour, and connection routing — four things that were not previously your problem.

**Read-your-writes** is the requirement that catches people, and there are four standard answers:
pin the author to the primary for a short window; carry a write timestamp or LSN token and wait for
a replica to reach it; read from a write-through cache; or block until the replica catches up. Pick
one and say why — the choice is usually about how much you're willing to spend on the *author's*
latency to protect everyone else's.

A materialized view or a search index is the same idea taken further: a read-optimized copy. Name
its **freshness SLO, its rebuild path, its source of truth, and how you detect drift.** A projection
without a rebuild path is a projection that will eventually be wrong and unrecoverable.

### F. PARTITIONING / SHARDING

Choose the shard key from access patterns and distribution, with two goals: common queries hit
**one** shard, and hot entities do not share a partition.

| Scheme | Good at | Bad at |
|---|---|---|
| Hash | Even point access | Range scans |
| Range | Efficient scans, natural ordering | Hot tail — the newest range takes all the writes |
| Directory | Flexible placement, easy rebalance | A metadata service you now depend on |

**Consistent hashing** reduces how much data moves when nodes change, and virtual nodes improve
balance. It does not solve a single hot key — that is a different problem with different fixes
(§05 D).

The costs are the part to volunteer: cross-shard joins and transactions, scatter-gather tail
latency, global uniqueness becoming hard, resharding, backup/restore fanout, and the operational
multiplication of everything. Plan the resharding path up front — **virtual buckets, dual-write,
dual-read, backfill, checksum, cutover, rollback** — because a shard key you cannot change is a
decision you have to get right the first time.

### G. WRITE-HOT DATA

- **Batch inserts and group commits**; keep transactions short. Most "the database can't take our
  writes" turns out to be lock hold time, not throughput.
- **Append events, aggregate later**, when in-place update isn't required.
- **Shard the counter** into N cells and sum on read (or materialize periodically). A single row
  taking serialized increments is a hard ceiling in the hundreds-to-low-thousands per second, and
  no amount of table-level capacity moves it.
- **Route a hot entity to one serialized worker** when ordering and contention dominate — you trade
  latency and ownership complexity for the disappearance of contention.
- **LSM stores** trade very high sequential write throughput for compaction cost and read
  amplification. Mention them when the workload shape justifies it, not as a general answer to
  "lots of writes."

## 06 — Go asynchronous without losing control

### A. QUEUE OR LOG?

| | Work queue | Durable log / stream |
|---|---|---|
| **Primary goal** | Distribute jobs to workers | Retain an ordered history |
| **Consumption** | One worker handles each item | Many independent consumer groups read everything |
| **Replay** | Limited; usually just a DLQ | A core capability |
| **Ordering** | Often best-effort or scoped | Guaranteed within a partition |
| **Typical use** | Email, thumbnails, webhooks | CDC, analytics, projections, event sourcing |

The distinction has softened at the edges — modern log systems can acknowledge per message — but
the decisive questions are unchanged: *does anyone need to read this twice, and does anyone need to
read it later?* Two yeses means a log.

### B. ACKNOWLEDGMENT SEMANTICS

- **"Request accepted" means persisted to a durable queue or log.** The client sees *pending*, not
  the success of the downstream effect. Conflating these is how you end up telling a user their
  order succeeded when it is sitting in a DLQ.
- **At-most-once** may lose messages and avoids duplicates. **At-least-once** retries and may
  duplicate. Most business pipelines start at least-once, and should.
- **Exactly-once *processing*** is achievable inside some bounded systems with transactional state.
  **Exactly-once *business effect*** still requires idempotency, dedupe, or atomic sink semantics
  end to end. Be precise about which one you're claiming — an interviewer who knows the difference
  is specifically listening for it.
- **Choose the acknowledgment boundary from product truth.** "Payment authorized," "order
  recorded," "email queued," and "email delivered" are four different states, and the product cares
  which one your 200 response meant.

### C. THE IDEMPOTENT CONSUMER

A consumer does not *receive* an idempotency key and cannot mint one — a redelivered message would
get a different one each time. It **derives** the dedupe identifier from the message itself, which
is why the producer's job is to put a stable event ID in there at publish time (§04 C).

- Key dedupe on a **stable event ID plus a semantic operation ID**, scoped correctly, retained
  longer than your maximum replay window.
- Prefer a **database uniqueness constraint or an atomic compare-and-set** over a read-then-write
  check. The check-then-act version has a race in it by construction.
- If the external side effect supports idempotency keys, **propagate one**. If it doesn't, record
  intent before the call and reconcile ambiguous timeouts afterwards.
- Handlers must tolerate **duplicate, late, and out-of-order** events. Version your event schemas,
  and never reuse a field name with a new meaning — that is the bug that survives every test suite
  and appears in production six months later.

### D. TRANSACTIONAL OUTBOX / CDC

The dual-write problem: you need to commit business state *and* publish an event, and you cannot do
both atomically across two systems.

**Outbox:** write the business state and an outbox row in **one local transaction**; a relay reads
the outbox and publishes to the broker; consumers dedupe. The atomicity you need is inside one
database, which is where you can actually get it.

**CDC** turns database changes into a stream with no application dual-write at all — powerful, and
with one caveat worth voicing: raw row changes are a poor *public* domain contract, because you
have now coupled every consumer to your schema.

**Inbox** is the consumer-side mirror, for when processing and dedupe must commit atomically.

> **The dual-write test.** If the process crashes after system A commits and before system B
> commits, can you repair deterministically? If not, the design isn't finished. Ask this of every
> place two systems change together.

### E. PARTITIONS AND ORDER

- **Ordering is scoped, always.** Key events by entity so the broker hashes the same entity to the
  same partition. Do not create one physical partition per entity — that is a different, worse
  problem.
- **Partition count bounds parallelism.** A hot entity can still monopolize its partition; isolate
  or special-case if it matters.
- **Retries reorder.** If per-key order must survive retries, you need sequence/version checks, a
  retry topic, or key-level blocking — and each costs throughput. Choose explicitly.
- **Global total order is expensive and usually not a product requirement.** Ask what actually needs
  to be compared with what. Usually the answer is "events for one user," which is cheap.

### F. BACKPRESSURE, RETRIES, AND DLQ

- **Bound everything**: queue depth, in-flight work, concurrency, payload size, retry count, and
  per-tenant share. An unbounded queue converts a throughput problem into a memory problem and then
  into an outage.
- **Exponential backoff + jitter + a retry budget.** Retry only transient errors, and put the retry
  policy at **one** layer — three layers each retrying three times is twenty-seven attempts.
- **A DLQ is quarantine, not resolution.** Alert on it, inspect it, fix the cause, replay safely,
  and track age and count *by reason*. A DLQ nobody reads is a data-loss mechanism with extra steps.
- **Autoscale on queue age and service time**, not message count. Message count tells you nothing
  about whether you are falling behind.

### G. PIPELINE OPERATIONS

- **Metrics that matter:** ingress and egress rate, oldest message age, lag by partition, attempt
  counts, poison rate, processing latency, and sink errors. Oldest-age is the one that maps to user
  impact.
- **Replay plan:** source retention, schema compatibility, side-effect suppression or dedupe,
  rate-limited catch-up so the replay doesn't take out the live path, and progress checkpoints.
- **Stream windows:** event time versus processing time, watermarks, allowed lateness, how
  corrections are emitted, and state retention. "We'll use a five-minute window" is not a design
  until you have said what happens to an event that arrives six minutes late.

## 07 — Protect correctness under concurrency

### A. START WITH THE INVARIANT

Name the thing that must never be false, in the product's language, before choosing any mechanism:

- Inventory never goes below zero.
- One booking per slot.
- Ledger entries balance.
- A message edit must not overwrite a later edit.

Then pick the **cheapest mechanism that enforces it at the authoritative boundary.** Almost every
over-engineered concurrency answer comes from skipping this sentence and reaching for a distributed
lock when a unique constraint would have done it.

### B. THE CONTENTION TOOLBOX

| Mechanism | Shape | Best when | Cost |
|---|---|---|---|
| **Atomic statement** | `UPDATE inventory SET qty = qty - 1 WHERE id = ? AND qty > 0`, then check rows affected | The invariant fits in one row | None worth mentioning — reach here first |
| **Constraint** | Unique, exclusion, check, foreign key | The invariant is structural | Turns races into explicit errors you must handle |
| **Optimistic concurrency** | Compare version/ETag, retry or return 409 | Low contention | Retry storm at high contention |
| **Pessimistic lock** | Lock the row or range in a short transaction | Hot contention, predictable | Deadlocks, throughput cost, lock-hold discipline |
| **Serialized actor** | One logical executor per key | Ordering *and* contention both dominate | Latency, ownership, recovery complexity |
| **Distributed lock** | Lease across systems | Genuine cross-system critical section | Last resort; needs a **fencing token** the protected resource checks |

The fencing token is the detail that separates people who have read about distributed locks from
people who have debugged one. A lease can expire while its holder is paused; without a
monotonically increasing token that the *resource* validates, the zombie holder still writes.

### C. TRANSACTION ISOLATION

| Level | What to remember |
|---|---|
| **Read committed** | Each statement sees committed data. Read-modify-write still races. |
| **Repeatable read / snapshot** | A stable snapshot for the transaction. **Write skew is still possible** depending on the database's semantics. |
| **Serializable** | Equivalent to some serial execution. Expect aborts and retries, and lower throughput. |

Name the **anomaly you are preventing** — lost update, write skew, phantom — rather than reaching
for the phrase "strong consistency," which is not an isolation level and does not answer the
question. Write skew is the one to be able to describe: two transactions each read a valid state,
each make a change that is individually fine, and together they violate an invariant neither could
see. The doctor-on-call problem is the canonical example, and snapshot isolation does not prevent
it.

### D. CROSS-SERVICE WORKFLOWS

- **Saga** — local transactions plus durable workflow state plus compensating actions. The critical
  reframe: **compensation is a business action, not a database rollback.** Refunding a payment is
  not un-charging it, and the ledger must show both.
- **Orchestration vs choreography** — one workflow owner makes state visible and retries explicit;
  choreography has less central coupling but flows become genuinely hard to understand and change.
  For anything with money or a support team, orchestration.
- **2PC** — real atomic commit across participants, with availability and operational costs and
  limited participant support. Don't select it or dismiss it by slogan; say what it costs.
- **Model irreversible steps late.** Use pending and reserved states, and reconcile ambiguous
  outcomes. If the flow must charge a card and ship a box, charge last.

### E. THE CONSISTENCY MENU

| Model | What it guarantees | Use for |
|---|---|---|
| **Linearizable** | Operations appear in one real-time order | A single authoritative decision — the seat, the balance |
| **Sequential / per-key** | All observers agree on the order, not necessarily on recency | Ordered feeds, per-entity event streams |
| **Session** | Read-your-writes and monotonic reads for one user | Very often the right *product* contract |
| **Bounded staleness** | No older than a stated time or version bound | Dashboards, counts — explainable to a PM |
| **Eventual** | Replicas converge given no new writes | Only with a defined conflict rule and user experience |

Session consistency is under-used in interviews and is frequently the correct answer: users
overwhelmingly notice their *own* writes disappearing and rarely notice someone else's arriving a
second late.

### F. CAP, USED CORRECTLY

> CAP constrains behaviour **during a network partition**: you either preserve consistency by
> refusing or limiting operations, or preserve availability by accepting divergent or stale
> behaviour.

It is not a three-way feature score for databases, it does not describe normal operation, and it
does not replace the latency tradeoffs you make when nothing is broken. Using "we'll go AP" as a
substitute for saying what a user sees during a partition is the version interviewers mark down.

### G. REPLICATION AND CONFLICTS

- **Single-leader** — one simple write order. The risks are leader failover and cross-region write
  latency.
- **Multi-leader** — local writes and regional survival, at the cost of conflicts, duplicate
  effects, and convergence all becoming *application* problems.
- **Leaderless / quorum** — tune R, W, N with R + W > N; you also inherit read repair, hinted
  handoff, and the fact that quorums alone do not give linearizability under every failure.

**Conflict policies**, in ascending order of effort: reject; last-write-wins (cheap, and it silently
loses data — say so); field-level merge; domain-specific merge; CRDT where the operations genuinely
fit. Choosing last-write-wins is fine. Choosing it without acknowledging that it discards a real
user's write is not.

### H. MONEY AND INVENTORY

The highest-stakes special case, and it comes up constantly:

- **Keep an append-only ledger.** Balances are derived or materialized from it. Never overwrite
  financial history — an `UPDATE` on a balance is an audit failure.
- **Reserve with an expiry, then confirm or cancel.** The reservation is what makes overselling
  impossible without holding a lock for the length of a checkout flow.
- **Separate authorization, capture, refund, and settlement** as distinct states, and reconcile
  against the external provider. They will disagree; the design must have a place for that.
- **Audit every transition** with actor, request ID, operation ID, timestamp, and reason.

## 08 — Realtime delivery, fanout, search, and geo

### A. THE CLIENT DELIVERY LADDER

| Mechanism | Fits | Costs |
|---|---|---|
| **Polling** | Freshness measured in seconds or minutes | Wasted requests; simplest and stateless |
| **Long polling** | Near-realtime over plain HTTP | Held requests, reconnect churn |
| **SSE** | Server → client streams, tokens, notifications | One direction only; connection limits and proxy behaviour |
| **WebSocket** | Genuinely bidirectional, low latency | Connection state, heartbeat, resume, routing all become yours |
| **Push** | Background and mobile wake-up | Best-effort; platform limits |

Start with the simplest mechanism that meets the freshness and interaction requirement. And keep
one distinction clean: **realtime delivery does not imply realtime durable storage.** They are
separate systems with separate guarantees, and conflating them is how presence data ends up in a
transactional database.

For what each rung is from the browser's side — and what the client owes you in return, since
reconnect and resumption are where these designs actually fail — see `Technology Choices` §22–25.

### B. THE CONNECTION PLANE

- A **gateway** authenticates, rate limits, maintains heartbeats, and tracks subscriptions.
  Application workers stay stateless behind it wherever possible.
- A **registry** maps user/session → gateway with a TTL — or you invert it and have gateways
  subscribe only to the channels for their locally connected users, which avoids the registry
  entirely at the cost of broader subscriptions.
- **On reconnect**, the client sends its last cursor or sequence number; the server replays from a
  durable log, then resumes live delivery. This is the mechanism that makes a dropped connection a
  non-event, and it should be in the design from the start rather than added when someone asks.
- **Slow consumers** need bounded buffers plus a policy: coalesce, drop, fall back to a snapshot, or
  disconnect. Never allow unbounded per-socket memory — one slow client should not be able to
  exhaust a gateway.
- **Separate the contracts.** Presence, typing indicators, and read receipts are lossy TTL state.
  Chat messages are durable. Designing them with one mechanism gets you either an expensive
  presence system or an unreliable message system.

### C. FANOUT

| Strategy | Mechanism | Buys | Costs |
|---|---|---|---|
| **On write** | Precompute each recipient's inbox at publish time | Fast, cheap reads | Write and storage amplification; the celebrity problem |
| **On read** | Fetch from sources and merge at request time | Cheap writes | Expensive read path and ranking latency |
| **Hybrid** | Push for normal producers, pull for high-fanout ones, merge on read | Both, mostly | A threshold you have to justify |

The hybrid threshold should come from the follower distribution and the read ratio, not from
folklore. Say how you'd pick it: *"I'd take the follower-count distribution, find where write
amplification per post exceeds the read cost of merging at request time, and set the cut there —
then measure it."*

Protect against fanout storms with chunked jobs, per-producer quotas, queue backpressure, and
delayed delivery for lower-priority recipients.

### D. SEARCH AS A PROJECTION

The shape is always: **source of truth → outbox/CDC → indexer → search cluster.** Expose the
indexing lag as a metric, and be able to rebuild the whole index from the authority.

- Decide **lexical vs semantic relevance** (usually both, fused), typo tolerance, filters and
  facets, freshness targets, languages, and pagination stability.
- **Access control is the kill shot.** Authorization-aware indexing, tombstones, a real delete
  pipeline, and periodic reconciliation — because a search index that returns a document title the
  user is not allowed to see has leaked the document.
- **Rank in stages**: candidate retrieval → filters → feature hydration → cheap ranking → expensive
  rerank on a small set. Cache by query only when permissions allow it, which is less often than
  people assume.

### E. GEO / PROXIMITY

- **Geohash, S2, or H3 cells** produce a coarse candidate set: search the current cell plus its
  neighbours, then compute exact distances on the survivors. Searching neighbours is not optional —
  the nearest point is frequently just across a cell boundary.
- **Cell size trades candidate count against boundary misses.** Adaptive or multi-resolution cells
  handle density skew, which is what you get in any real map (dense cities, empty ocean).
- **Location is sensitive data.** Store the precision the product needs and no more, with a
  retention policy to match.

### F. COLLABORATIVE EDITING

- A **central sequencer** (a room server that assigns an order) is the simplest correct thing when
  users are online and region-local. Reach for it first.
- **OT or CRDT** support concurrent edits and offline merges. Both need operation IDs, version
  vectors or causal context, compaction, and a reconnect protocol — the algorithm is the smaller
  half of the work.
- Pick from **product** needs: are offline edits required, how many concurrent collaborators, how
  large is the object, what should undo do, and should conflicts be visible to the user or resolved
  silently?

### G. MEDIA UPLOAD AND PROCESSING

- Client obtains a **short-lived presigned URL** and sends bytes **directly to object storage**.
  Gigabytes must never transit your API tier.
- A metadata row tracks upload state; an object-created **event** triggers scanning, transcoding,
  and thumbnailing. Publish only completed, safe variants — never trust the client's "done."
- **Multipart and resumable** upload for large files; a content hash for integrity and dedupe; a
  CDN for delivery.
- Quotas, MIME sniffing, malware scanning, moderation, lifecycle tiering, and orphan cleanup are
  part of the design, not operational afterthoughts.

> *"I separate durable truth from delivery presence. A reconnecting client can always recover from
> a cursor, while ephemeral typing indicators may be dropped under pressure — those are different
> guarantees and I don't want to pay for the stronger one twice."*

## 09 — Design for failure, overload, and regions

### A. FAILURE IS A PATH, NOT A STATE

For each critical dependency, name seven things: **timeout, retry eligibility, retry budget, circuit
behaviour, fallback, data consistency during the failure, and the alert.** Seven sounds like a lot
until you notice that most designs specify zero of them.

Distinguish the failure classes, because they need different defences: **partial** (some requests
fail), **slow** (nothing fails, everything queues — usually worse), **correlated** (the thing you
thought was independent wasn't), and **bad-data** (the system is up and returning wrong answers).
Replication helps with some crash failures and none of the others.

Health checks deserve their own sentence: a health check must reflect the **ability to serve**;
readiness prevents traffic before warmup; and liveness must not be able to cause a restart loop
under load, which is a spectacular way to convert a slowdown into an outage.

### B. TIMEOUTS, RETRIES, HEDGING

- **Set the timeout from the caller's end-to-end deadline and propagate the remaining budget
  downstream.** Otherwise one slow dependency spends the whole budget repeatedly at every layer.
  A fixed per-hop timeout with no deadline propagation is the default and it is wrong.
- **Retry only idempotent, transient operations**, with exponential backoff, jitter, a maximum
  attempt count, and a global retry budget expressed as a fraction of traffic.
- **Retry at exactly one layer.** Three retries at three layers is up to twenty-seven requests for
  one user action, arriving precisely when the dependency is least able to take them.
- **Hedging** — issue a second request after a delay and take the first response — cuts tail latency
  for safe reads and increases load. Use it only with capacity headroom and working cancellation.

### C. OVERLOAD CONTROL

- **Bound everything**: queues, pools, batches, request size, query complexity, per-tenant share.
- **Admission control before expensive work.** Shed low-priority and optional requests quickly, with
  an explicit overload status the client can act on. Rejecting in 1 ms is a gift; timing out at 30 s
  is an attack on yourself.
- **Degrade rather than fail**: backpressure upstream, serve stale cache, reduce fanout, sample
  non-critical writes, turn off recommendations.
- **Bulkheads** isolate dependencies, tenants, and work classes so one hot path cannot consume every
  thread and connection.
- **Autoscaling is not instantaneous** and cannot rescue a saturated database or a bad dependency.
  It is a capacity tool, not an incident tool. Keep headroom.

### D. THE CASCADING FAILURE LOOP

> One replica fails → the remaining replicas take more load → latency rises → callers hit timeouts
> and retry → load rises again → more replicas fail.

This is a positive feedback loop, which means it does not stabilize on its own and adding capacity
mid-incident often doesn't reach it in time. You break it in exactly four places: **load shedding**
(reduce work admitted), **retry budgets** (stop amplification), **concurrency limits** (bound
in-flight work per dependency), and **capacity headroom** (survive the first failure without
crossing the threshold). Being able to draw this loop and name the four interventions is one of the
highest-value ninety seconds available in a design round.

### E. AVAILABILITY TOPOLOGIES

| Topology | Good for | The hard part |
|---|---|---|
| **Multi-zone, one region** | The common HA baseline | A regional outage takes you down |
| **Active–passive regions** | Lower complexity and cost | Failover correctness, stale replica, and actually drilling it |
| **Active–active reads** | Global read latency | Cache and data freshness across regions |
| **Active–active writes** | Global write availability | Conflicts, ordering, and cost |

### F. THE MULTI-REGION DECISION

Start from **RTO, RPO, write latency, data residency, and the outage scope you're insuring
against.** Multi-region is not automatically better; it is a large, permanent increase in
complexity that buys a specific thing, and you should be able to say which.

- **Home region per tenant or entity** is the underrated middle path: local writes where they
  matter, no conflict resolution, routed via a directory. Then define what happens when a home
  region is lost.
- **Async replication** gives low local write latency and a non-zero RPO. **Synchronous** gives
  stronger durability and ordering, and pays physics on every write.
- **Failover is a procedure, not a switch**: fence the old primary, switch traffic, promote the
  replica, confirm dependency readiness, warm caches, and have a failback plan. Untested failover
  is a plan to discover all six of those during an incident.

### G. DISASTER RECOVERY

- **Backups are not DR until a restore has been tested.** Replication is not a backup — it
  replicates your corruption and your accidental `DELETE` faithfully and immediately.
- Define backup frequency, **immutability**, encryption, retention, restore *order*, credential and
  config recovery, and the maximum restore duration. Restore order is the one people find out about
  the hard way.
- **Run game days.** Measure achieved RPO and RTO rather than the ones on the document. Predefine
  who has decision authority and what users are told.
- For **derived stores**, rebuild from the authority rather than paying to back up every projection
  — unless the rebuild takes longer than your RTO, in which case that is the tradeoff to state.

### H. GRACEFUL DEGRADATION

Rank features before the incident, not during: **must-work**, **important**, **optional**. Protect
write correctness ahead of recommendations, counts, presence, and freshness — a user will forgive a
stale like count and will not forgive a lost order.

Concrete degradations worth naming: serve the cached catalogue without personalization; accept the
upload and process it later; enter read-only mode; disable expensive search facets.

Two properties the degraded mode itself needs: it must be **observable** (you can tell you're in
it) and **reversible** (you can leave it). And avoid mode switches that flip every node at the same
instant — add jitter, or you have built a synchronized thundering herd into your recovery path.

## 10 — Operate, secure, and evolve the system

### A. OBSERVABILITY BY USER JOURNEY

Instrument the journey, not the box. "Checkout succeeded" is a signal; "service B CPU" is a clue.

- **Metrics**: rate, errors, duration, saturation — plus *business correctness* signals like orders
  recorded, duplicate charges, and indexing lag.
- **Logs**: structured, sampled, privacy-safe, carrying operation/request/tenant IDs. Never secrets
  or raw sensitive payloads.
- **Traces**: propagate context through RPC *and* async events, and record queue wait separately
  from processing time — otherwise a latency regression from a backed-up queue looks like slow code.
- **Profiles**: CPU, allocation, and blocking, when the resource cost isn't explicable from metrics.
- **Alerts fire on user-impacting SLO burn**, not on every noisy metric. An alert nobody can act on
  trains people to ignore alerts.

### B. GOLDEN SIGNALS PLUS DOMAIN SIGNALS

| System signal | The domain signal that pairs with it |
|---|---|
| p50 / p95 / p99 latency | Checkout success rate; duplicate-effect rate |
| Error rate by class | Feed and search freshness |
| CPU, memory, connection saturation | Payment reconciliation delta |
| Queue age, replication lag | Abuse-block rate and false-positive rate |
| Cache hit rate, origin load | Model quality and groundedness (§11 F) |

The right-hand column is the one that distinguishes an operable system. Every entry in it can be
wrong while every entry on the left looks perfect.

### C. THE SECURITY THREAT PASS

- **Identity**: authentication, token and session lifecycle, service identity, key rotation.
- **Authorization**: object-level *and* field-level on every read and write; tenant isolation; least
  privilege. Unguessable UUIDs are not authorization — object-level authz failures remain the most
  common serious API vulnerability.
- **Input and resource abuse**: schema validation, injection defence, file scanning, query and page
  limits, per-principal quota *and cost* limits.
- **Data**: TLS, encryption at rest, who owns the keys, a secrets manager, and an audit trail on
  sensitive-field access.
- **Supply chain and operations**: dependency provenance, signed artifacts, secure defaults, audit
  trail, and a revocation path for an incident.

### D. PRIVACY AND COMPLIANCE

- **Classify and minimize**: collect what the product needs, separate sensitive fields, and limit
  what can be joined to what.
- **Deletion has to reach everywhere**: primary database, replicas, caches, search indexes,
  analytics, logs, **embeddings**, and backups, each according to policy. The embeddings line is the
  one that is newly easy to forget and increasingly asked about.
- **Residency and transfer constraints** affect sharding and failover — they are architecture, not
  paperwork. Consent and purpose limitation can constrain downstream uses.
- **Audit access without leaking values.** Design export and delete as durable workflows with
  progress and evidence, because they are legally time-bound and must be provable.

### E. SAFE ROLLOUT

Feature flag → internal or dark traffic → small canary → staged percentage, region, or tenant →
full rollout.

- Define success metrics **and the automatic rollback trigger** before launching. Compare canary
  against control on p99 and on correctness, not just error rate.
- **Backward-compatible protocol and schema first.** Old and new binaries will coexist during the
  rollout; a change that requires them not to is a change that requires downtime.
- **Shadow reads and writes** validate a new path against real traffic — with side effects
  suppressed, and with the extra load budgeted.

### F. ZERO-DOWNTIME DATA MIGRATION

The five steps, in order, every time:

1. **Expand** — add the optional field, table, or index. Deploy writers that remain compatible with
   old readers.
2. **Backfill** — chunked, throttled, checkpointed, idempotent, watching lag and load.
3. **Verify** — dual-read, or compare sampled checksums and invariants. Reconcile mismatches before
   proceeding.
4. **Cut over** — switch reads behind a flag, and keep a rollback window open.
5. **Contract** — stop old writes, then remove the old schema only once the fleet and the rollback
   window are clear.

The discipline is that steps 3 and 5 are the ones under time pressure people skip, and they are the
two that make the migration reversible.

### G. OWNERSHIP AND OPERABILITY

- Name the **service owner, the data owner, the on-call boundary, the dependency SLOs, the runbook,
  and the capacity owner.** A design with no named owner is a design nobody can operate.
- **Minimize operational fanout.** A thousand per-tenant databases give beautiful isolation and
  multiply schema rollout, backup, alerting, and incident work by a thousand. That is a real cost,
  paid by people.
- **Build versus buy**: differentiate on product-critical logic, and use managed primitives wherever
  they meet your correctness, cost, lock-in, and compliance requirements.

> *"The architecture isn't done when steady state works. I need a safe rollout, a repair path for
> derived data, an overload mode, and an owner who can operate it at 3 a.m."*

## 11 — AI-native and LLM application systems

### A. THE MODEL CALL AS AN EXPENSIVE DEPENDENCY

Treat it as the slowest, priciest, least reliable dependency in the system, because it is.

- **Budget time and tokens end to end.** Stream early output when it improves perceived latency, and
  propagate cancellation so a user who navigates away stops costing money mid-generation.
- **Timeout, bounded retry for transient failures, per-user token and rate quota, a concurrency
  limit, and a degraded mode** — the same five controls you'd put on any dependency, except the
  quota here is denominated in money.
- **Persist request state before long work.** Use an async job or background mode when the client
  connection doesn't need to stay open.
- **Version everything**: model, prompt, tools, retrieval config, safety policy, and response
  schema. Without versioning you cannot reproduce a bad output or roll back a regression, and both
  will happen.

### B. CHAT AND CONTEXT

- A conversation is **append-only messages plus mutable metadata**. Define what edit, delete, and
  partial-generation mean before designing storage — they are product decisions with storage
  consequences, not the reverse.
- **Context assembly** is a budgeted pipeline: system policy + relevant user state + recent turns +
  summary or retrieval, packed to a token budget, with provenance for each piece. It is not string
  concatenation, and treating it as a pipeline is what makes it cacheable and auditable.
- **Never trust client-provided history** for authorization or billing. The authoritative
  conversation and tool outcomes live server-side.
- **The streaming protocol** needs event types, sequence numbers, a resume cursor, final usage, an
  error channel, and cancellation. Decide deliberately whether partial output is persisted — the
  answer is usually yes, because users read cancelled responses.

### C. THE RAG PIPELINE

**Ingest:** parse → chunk → enrich with metadata and ACLs → embed → index. Keep the original source
and its version, and make every stage restartable.

**Query:** authorization filter → lexical *and* vector retrieval → dedupe → rerank → context pack →
generate with citations.

Three things to say that most answers miss:

- **Evaluate retrieval separately from generation.** Recall@k, ranking quality, freshness, and
  permission leakage are retrieval metrics. Groundedness and task success are generation metrics.
  Conflating them means you cannot tell which half is broken.
- **Updates and deletes propagate through durable jobs**, and the index is periodically reconciled
  against the source. Cache only with tenant, ACL, and version in the key.
- **Chunk size, overlap, and top-k are workload parameters**, not universal constants. Anyone
  quoting 512 tokens with 50 overlap as a general truth is quoting a tutorial.

### D. THE TOOL-USING AGENT LOOP

The loop: model proposes a **typed** tool call → policy and authorization validate it → the executor
runs it with an idempotency key and a timeout → the result is recorded → the model continues.

- **Treat model output as untrusted input.** Validate the JSON schema, the allowed tool, argument
  bounds, resource ownership, and require user confirmation for high-impact actions. The model is a
  user who can be talked into things by a document.
- **Bound everything**: steps, wall-clock, tokens, spend, fanout, and recursion depth. Detect
  repeated or no-progress calls and stop.
- **Durable state machine with checkpoints** for long jobs, so a worker crash resumes without
  repeating external effects.
- **Human approval at irreversible or high-risk boundaries**, with the pending action and the audit
  trail visible.

### E. PROMPT INJECTION AND DATA BOUNDARIES

- **Separate trusted instructions from untrusted retrieved content.** A retrieved document must
  never be able to grant tool authority. This is the central security property of an agent system
  and it is architectural, not a prompt-engineering trick.
- Defence in depth: least-privilege tools, scoped credentials, sandboxing, network and domain
  restrictions, output encoding, and confirmation gates.
- The specific attacks to name: **cross-tenant retrieval, secret exfiltration, excessive tool
  parameters, and unsafe content propagation** into downstream systems.
- Log decisions and tool metadata safely; redact sensitive prompt and tool payloads to policy.

### F. QUALITY, SAFETY, AND EVALS

- **An offline golden set before any prompt or model change**, stratified by critical slices and
  adversarial cases. Without it, "we improved the prompt" is an unfalsifiable claim.
- Use **deterministic checks** where the output allows, **model graders with calibration** where it
  doesn't, and **human review** for high-impact quality.
- **Online signals**: task completion, user correction rate, groundedness, safety violations,
  latency, token cost, abandonment — with rollback guardrails wired to them.
- **Canary model and prompt versions**, and retain a comparison and replay corpus within your
  privacy policy. Prompts and configs are versioned production artifacts, deployed like code.

> *"The model is probabilistic; the system around it doesn't have to be. Tool authority, state
> transitions, budgets, and side effects are all deterministic and auditable — the uncertainty is
> confined to the text."*

## 12 — The LLM product blueprint

### A. A CHATGPT-SHAPED WALK-THROUGH

**Send path.** Client POST → gateway (auth, per-user rate and token quota) → chat service persists
the user message **and an assistant-message placeholder** with status `generating` → context builder
(system policy + recent turns + summary + ACL-filtered retrieval, packed to the token budget) →
inference orchestrator (model routing, admission queue, streaming) → model pool.

The placeholder is the detail that makes everything else possible: it gives the stream somewhere to
land, gives reconnect something to resume from, and gives failure somewhere to record itself.

**Stream path.** Tokens flow back through the gateway to the client over SSE with sequence numbers.
The orchestrator appends chunks to the placeholder with **buffered writes, not one write per
token**. On completion it persists the final text, usage, and finish reason.

**Failure path.** A client disconnect is **not** a generation failure — decide explicitly whether
generation continues server-side (usually yes, and it's what makes the response there when they come
back). On reconnect the client sends its message ID plus a cursor and replays from the persisted
partial, then resumes live. A provider timeout means bounded retry, or degrade to a smaller model,
or an explicit error state that preserves enough context to retry.

**Async siblings.** Title generation, conversation summarization, moderation, and eval sampling all
hang off the *completed-message* event. None of them belong in the interactive path.

**Source of truth** is the conversation store. The retrieval index, summaries, and analytics are all
rebuildable projections, and §08 D applies to them unchanged.

### B. LLM ESTIMATION ANCHORS

- **Latency splits in two.** Time-to-first-token ≈ queueing + prefill, and prefill grows with prompt
  length. Decode is commonly tens of tokens per second per stream. A 500-token answer therefore
  takes seconds to tens of seconds — which is why streaming is structural rather than a nicety.
- **Connections are the scarce resource, not QPS.** Little's Law on streams: 100 requests/s × 10 s
  average stream = **1,000 concurrent open connections**. Size gateways by concurrency and
  per-connection memory. Long-lived SSE also changes load balancer and proxy behaviour, which is a
  real operational surprise.
- **Cost is per token and asymmetric.** Output tokens typically cost several times input tokens, and
  long context inflates both cost *and* time-to-first-token. Trim, summarize, and cap output length
  before touching model choice.
- **Prefix caching.** A stable system prompt and tool definitions can be cached by the provider —
  which means context order is an architectural decision: stable content first, volatile content
  last.
- **Vector math.** A ~1,500-dim float32 embedding ≈ 6 KB, so 10M chunks ≈ 60 GB of raw vectors plus
  index overhead. That is memory-bound, which is what brings quantization, IVF or disk-backed
  indexes, and tiering into the design.

### C. COST AND LATENCY LEVERS

In roughly the order you should reach for them:

1. **Reduce round trips**, parallelize independent work, and stream.
2. **Trim output and compact context** — the cheapest wins, and they improve latency and cost
   together.
3. **Batch offline workloads** rather than running them interactively.
4. **Route by difficulty or risk** to a model tier; escalate only when the cheap model is unsure.
5. **Cache** stable prefixes, embeddings, and safe deterministic results.
6. **Speculative or parallel calls** trade cost for latency — cancel the losers and cap the fanout.

And measure **cost per successful user outcome**, not cost per request. A cheap answer that fails is
the most expensive thing in the system, because the user retries it.

### D. DEEP-DIVE PROMPTS TO EXPECT

| Prompt | Where they'll press |
|---|---|
| Internal knowledge assistant | ACL-aware retrieval (permission leakage is the kill shot), ingestion from changing sources, freshness SLO, eval design for internal facts |
| Recruiting or HR copilot | Sensitive data classes in prompts, logs, and embeddings; human approval before external effects; auditability of every model-influenced decision |
| Chat with org data | The hybrid lexical + vector decision, context budget under long documents, citation faithfulness, cost per seat |

> *"Two numbers shape this design: streams live for seconds, so I size the connection plane by
> concurrency rather than QPS; and tokens are the cost unit, so context assembly is a budgeted,
> ordered, cacheable pipeline — not string concatenation."*

## 13 — A worked design, end to end

One system, taken through the sections, to show what "using this guide" actually looks like. Ticket
sales is the right choice because it exercises the four things that are hard at once: a real
invariant, extreme burstiness, an async path, and a failure story with money in it.

> **Prompt.** *"Design ticket sales for live events. When a popular show goes on sale, hundreds of
> thousands of people arrive in the same minute for a few thousand seats."*

**Frame (§02 A).** Users: buyers, and event organizers. Core flows: browse events, hold a seat,
purchase. Out of scope, stated aloud: dynamic pricing, resale, and recommendations. **The
invariant: a seat is sold at most once.** That one sentence is the design's spine, and naming it in
minute two is what everything downstream gets justified against.

**Quantify (§03).** A 50,000-seat show, 500,000 people arriving inside 60 seconds. That is
**~8,000 requests/s of arrival against ~50,000 units of inventory** — a ratio of ten to one, which
tells you immediately that the system's main job is *rejecting* people correctly, not serving them.
Steady-state traffic between on-sales is trivial. So the design target is a burst two to three
orders of magnitude above baseline, which means provisioned headroom and a queue, not autoscaling
(§09 C — autoscaling is not an incident tool).

**The invariant mechanism (§07 A–B).** Reach for the cheapest thing that enforces it. A seat is one
row, so this is an **atomic conditional update**: `UPDATE seats SET state='held', hold_id=?,
expires_at=? WHERE seat_id=? AND state='available'`, then check rows affected. No distributed lock,
no Redis lock with the fencing-token problem — a single-row compare-and-set in the authoritative
store. Say why the alternatives are unnecessary; that is the senior move here.

**Holds, not purchases (§07 H).** The user needs a few minutes to enter payment details, and you
cannot hold a database lock for that. So: **reserve with an expiry, then confirm or cancel.** The
hold row carries `expires_at`; a sweeper releases expired holds; confirmation is a separate state
transition. This is the same reserve-then-confirm pattern as inventory, and saying so out loud
connects it to a general principle rather than a trick.

**The queue (§09 C).** Admission control in front, not load balancing behind. Arrivals get a
position in a virtual waiting room and are admitted at a rate the seat-selection path can actually
serve. This is the design decision that makes the ten-to-one ratio survivable, and it is a *product*
decision as much as a technical one: a queue with an honest position is a much better experience
than a site that returns 503s.

**Async work (§06).** Payment capture, confirmation email, ticket rendering, and analytics all hang
off the *confirmed* event, through a durable log. None of them are in the interactive path. Payment
gets an **idempotency key** (§04 C) because the ambiguous timeout — did the charge go through? — is
guaranteed to happen at this volume.

**Reads (§05).** Event browsing is cacheable and enormously read-heavy: CDN it. Seat *availability*
is the opposite — it is the one thing that must not be stale, so it reads through to the
authoritative store, and the UI is designed to expect a hold to fail. Naming that split, rather than
applying one caching answer to the whole system, is the point.

**Failure (§09).** Payment provider down → holds must not silently expire while the provider is
unreachable; extend the hold and surface the state. Database primary fails mid-on-sale → this is the
RTO question, and for a 60-second event the honest answer is that failover is slower than the sale,
so the design needs pre-warmed standby and an accepted pause rather than a fantasy of seamlessness.
Sweeper falls behind → seats stay held after expiry, so the sweeper's lag is a **user-impacting SLI**
and belongs on the dashboard (§10 B).

**Close (§14 B).** Biggest risk is the hold-expiry sweeper — it is the least glamorous component and
the one whose failure silently removes inventory from sale. First thing to build is the atomic
seat-state transition plus the hold lifecycle, because every other component is a consumer of it.

Notice what this walk-through never did: it never picked a database vendor, and it never drew a box
that the invariant or a number didn't force. That is the whole method.

## 14 — Decision matrices and the closing drill

### A. PROMPT → LIKELY DEEP DIVE

Interviewers reuse a small set of prompts and press on a predictable place in each. Knowing where
the pressure lands lets you steer there yourself.

| Prompt | Where they'll press |
|---|---|
| Feed / timeline | Fanout hybrid, ranking, hot creators, pagination stability |
| Chat / notifications | Realtime resume, ordering, presence, push delivery |
| Ticketing / inventory | Atomic reserve, contention, hold expiry, fairness (§13) |
| Payments / ledger | Idempotency, state machine, reconciliation, audit |
| File / photo / video | Direct upload, async processing, CDN, moderation |
| Search / maps | Index freshness, ranking stages, geo cells, ACL filtering |
| Metrics / trending | Stream windows, lateness, rollups, hot keys |
| Collaboration | Sequencing, OT vs CRDT, offline reconnect, compaction |
| LLM assistant | Streaming, context assembly, tools, RAG, evals, budgets (§11–12) |

For **which store or technology** each of these implies, and the argument for one over another, use
the `Technology Choices` guide — it is the companion to this table and goes a level deeper than a
matrix can.

### B. THE FIVE-MINUTE CLOSING CHECK

Run this in the last minutes, out loud. It is five questions and it catches the omissions that lose
otherwise-strong rounds.

1. **Scope** — did I satisfy the stated user journeys, and did I cut the non-essential ones
   *explicitly*?
2. **Numbers** — did scale, latency, SLO, RPO/RTO, and geography actually force my major choices, or
   did I assert them?
3. **Correctness** — source of truth, the invariant, duplicate/order/staleness semantics,
   reconciliation?
4. **Failure** — timeouts, retry budget, an overload mode, region and data recovery?
5. **Evolution** — observability, security and privacy, rollout, a migration seam, ownership, cost?

### C. TRADEOFF LINES WORTH REHEARSING

These are load-bearing sentences. Say them in your own words, but have the shape ready:

- *"I'm choosing the simple baseline, and here's the measurable trigger for replacing it."*
- *"That's a product consistency decision: what exactly may this user see stale, and for how long?"*
- *"This improves steady state and adds a failure mode. Here's the blast radius and the degraded
  behaviour."*
- *"We can pay at write time or at read time. The read ratio and the freshness target decide it."*
- *"Before sharding, I'd validate query shape, one-node headroom, caching, and replicas with a
  benchmark."*
- *"I'd launch behind a flag, backfill idempotently, compare results, cut over, and keep rollback."*

> **The final test.** Can you explain not only why the system scales, but why the organization can
> safely launch it, operate it, repair it, migrate it, and eventually simplify it?

### D. PRIMARY REFERENCES

The sources worth reading directly rather than through a summary:

- **Google SRE Book** — SLOs, handling overload, addressing cascading failures. `sre.google/sre-book/`
- **Amazon Builders' Library** — timeouts and retries with jitter, idempotent APIs, load shedding.
  `aws.amazon.com/builders-library/`
- **PostgreSQL docs** — indexes, partitioning, locking, isolation. `postgresql.org/docs/current/`
- **OpenTelemetry** — signals and context propagation. `opentelemetry.io/docs/concepts/`
- **OWASP API Security Top 10** — object-level authorization, resource consumption.
  `owasp.org/API-Security/`
- **Google Cloud Architecture Center** — DR planning, RPO/RTO, multi-region.
  `cloud.google.com/architecture/`
- **OpenAI platform docs** — streaming, background mode, prompt caching, evals, latency and cost.
  `platform.openai.com/docs/`
