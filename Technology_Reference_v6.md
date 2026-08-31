# Technology Decision Reference v6 — Staff+ Interview

*One page per technology, server and browser. The mechanism that drives the tradeoff, when to reach for it, when it flips, and the line to say in the room.*

> This sheet answers **"which technology and why"** — the axis a pattern-organized system design sheet doesn't cover. Every entry follows the same skeleton so it's scannable under pressure: **mechanism → reach for / avoid → numbers → CAP → interview line → pushback.** The interview line is the choosing-not-pattern-matching signal; the pushback is where the obvious answer reverses, which is the staff tell.

> **Two halves.** `§01–16` is infrastructure you provision. `§17–28` is the browser — storage, transport, and coordination on a device you do not own. Same skeleton throughout; each half closes with its own decision matrix.

> **Verified August 2026** against primary sources (AWS, Apache, PostgreSQL, MDN, and the relevant W3C/WHATWG specs).

> **On the numbers:** these are interview anchors — order-of-magnitude figures to reason with out loud, not spec-sheet facts. Treat ranges as talking points, not exact values to be tested against.

---

## Contents

1. PostgreSQL — the default; ACID, joins, one node does more than you think
2. Cassandra — query-first, masterless, multi-region writes; you give up joins
3. DynamoDB — managed Dynamo-lineage KV; write-scaling with no cluster to run
4. Redis — in-memory speed; cache, counter, lock, queue, ephemeral state
5. Kafka — durable ordered log; decouple, buffer, replay, fan-out
6. Flink — stateful stream processing; windows, joins, exactly-once state
7. Message Queue (SQS / RabbitMQ) — per-message work dispatch; ack, retry, DLQ
8. S3 / Blob Storage — infinite cheap bytes; the bytes never touch your API
9. CDN — push bytes to the edge; the answer to "global" and "read-heavy static"
10. Vector DB — ANN over embeddings; the retrieval half of RAG
11. Workflow Orchestrator — durable fan-out/fan-in, exactly-once continuation
12. ZooKeeper / etcd — consensus-backed coordination; leader election, locks, config
13. Elasticsearch — inverted index; full-text + faceted search, not a primary store
14. OLAP / Columnar — scan-and-aggregate read model for analytics at scale
15. Push Notifications — the only channel that reaches a closed app; best-effort by construction
16. Decision matrix — workload → pick, at a glance

*The client side — the browser as a runtime you deploy to but do not control.*

17. localStorage / sessionStorage — synchronous, string-only, tiny; blocks the main thread
18. Cookies — the only client store the server sees; 4 KB, and CSRF is the price
19. IndexedDB — the browser's real database; async, transactional, indexed, evictable
20. Cache API & Service Worker — a programmable proxy for your own origin; the offline answer
21. OPFS & File System Access — synchronous bytes in a worker; why SQLite-in-WASM works
22. Polling & long polling — simulate push with HTTP; the cursor is the hard part
23. Server-Sent Events — a response that never ends; resumption for free via `Last-Event-ID`
24. WebSocket — bidirectional frames; you inherit reconnect, heartbeat, and resumption
25. WebRTC data channel — peer-to-peer, and the only unreliable-by-choice transport
26. Web Worker / SharedWorker — a second thread; `postMessage` is a deep copy
27. BroadcastChannel & cross-tab — one browser is N tabs; Web Locks decides who acts
28. Client-side decision matrix — need → pick, at a glance

---

## 01 · PostgreSQL

*The correct default. Reach for something else only when you can name the specific thing Postgres can't do at your scale.*

### Mechanism

B-tree indexes, MVCC, single-leader replication. Crucially, Postgres does not update in place — an `UPDATE` writes a new row version and marks the old one dead, so readers get a consistent snapshot without blocking writers. `VACUUM` reclaims the dead versions (and is why bloat, HOT updates, and index write-amplification are things you tune). One primary takes writes; read replicas stream the WAL (write-ahead log), asynchronously by default. Write ceiling is set by local WAL fsync throughput and hot-row lock contention, not by replicas.

**Version note.** PG 18 has an asynchronous I/O subsystem (faster sequential scans, bitmap heap scans, vacuum), B-tree skip scan, and native `uuidv7()` for time-ordered keys with better index locality. Connections are still process-per-connection, which is why the pooling advice below matters.

### Reach for it when

- You need multi-row / multi-table ACID transactions — money, inventory, multi-entity publish.
- Read patterns are ad-hoc or unpredictable — the planner + indexes handle new `WHERE` clauses for free.
- You need joins, aggregations, secondary indexes.
- Scale is anything below "genuinely global + huge." Which is almost always.

### Avoid / augment when

- Write volume genuinely exceeds one primary (see the trigger numbers) → shard or LSM store.
- You need active-active multi-region writes — retrofitted, painful.
- Append-only firehose (metrics, events) — LSM fits better.
- **Connection storms** — each connection is ~a backend process (megabytes of RAM); a few thousand direct connections will exhaust it. Put PgBouncer in front. The single most common real-world Postgres scaling gotcha, and it hits well before you run out of raw throughput.

### Triggers to break out (name the number)

The trigger is almost always a specific hot table or row, or a write pattern — not aggregate database size. 100M+ rows on one primary is routine.

- **< ~5k writes/s to one logical table** → you're fine on one primary. Don't move; you're solving a problem you don't have.
- **~5k–15k writes/s sustained** → tune first: batch inserts, offload the hot counter to Redis, faster-fsync disk (NVMe), fewer indexes on the hot table (HOT updates). Most "Postgres is slow" cases die here without an architecture change.
- **~15k–50k writes/s sustained to one table** → shard Postgres by a good key (app-level or Citus). You keep SQL and transactions within a shard; you give up cross-shard joins and painless rebalancing.
- **> ~50k writes/s sustained to one table**, append-only firehose (metrics/events), or active-active multi-region writes → move that hot table to an LSM / wide-column store (Cassandra / DynamoDB) or a purpose-built TSDB. Here the write *pattern*, not the size, forces the change.
- **A single hot row taking > ~500–1k serialized updates/s** (a global counter, one inventory row) → the ceiling is row-lock contention, not table throughput. Offload that one value to Redis (`INCR`) or shard the counter; the rest of the table stays in Postgres.

### Durability layers (know cold)

- **Local WAL fsync** survives a crash (power loss, panic) — recovery replays it. It does *not* survive losing the disk/node.
- **Synchronous replication** (`ANY 1` of several standbys, ideally another AZ) means no acknowledged write lives on a single disk. Use `ANY 1` quorum-with-slack, not a single named standby — requiring a specific replica means its failure blocks all writes.
- **WAL archiving to object storage + PITR** survives logical corruption (a bad `DELETE` replicates faithfully to every replica; only point-in-time recovery saves you).

**Numbers to anchor**

| | |
|---|---|
| Point read (indexed) | < 1 ms |
| Writes/s, one primary | ~5k–15k |
| Shard trigger (one table) | ~15k–50k w/s |
| LSM / firehose trigger | > ~50k w/s |
| Serialized updates / hot row | ~500–1k/s |
| Rows before sharding hurts | ~10–100M+ |
| Connections | pool it (~100s) |

### CAP / consistency

CP-leaning, but really ACID on one node + tunable replication. Transactional consistency (isolation up to `SERIALIZABLE`) is a native capability. Replication consistency is a separate knob: async replicas are eventually consistent; `synchronous_commit = remote_apply` or reading the primary gives strong.

### Interview line

I default to Postgres and make something else justify itself — transactions, joins, and query flexibility for free, one primary does 5–15k writes/s, reads scale on replicas. I only move off it when I can name the exact property it can't provide at my scale — a specific hot table past ~15–50k writes/s, a firehose, or a multi-region write — and I pool connections and tune the hot table before I touch the architecture.

### Pushback / when it flips

"Postgres doesn't scale" is usually wrong — a single hot row, a multi-region write, or connection exhaustion flips it, not raw size. Sharded Postgres by a good key gets most of Cassandra's write distribution; what you lose is automatic rebalancing and painless geo-replication, not the sharding itself.

---

## 02 · Cassandra

*Query-first, masterless, born multi-region. You trade joins and ad-hoc queries for cheap global replication and painless rebalancing.*

### Mechanism

LSM tree + consistent hashing + masterless replication. Writes append to a memtable + commitlog, flush to immutable SSTables — sequential I/O, so the write ceiling is high. Compaction merges SSTables in the background. Consistent hashing (with vnodes) places partitions on a ring — adding a node auto-rebalances token ranges. Any node can coordinate a write and forward to the replica set; there's no special primary. Consistency is tunable per query (`ONE`, `QUORUM`, `ALL`); multi-datacenter replication is a config declaration.

### Reach for it when

- Access is known, key-based lookups — "everything for this id," "this partition sorted by time."
- Global reads needing local-region latency — multi-DC replication out of the box.
- Very high write throughput, append-heavy.
- You want capacity-by-adding-nodes with no manual reshard.

### The model tax (know cold)

- **No joins, and no genuinely ad-hoc queries.** **Storage Attached Indexes (SAI)** give real secondary indexes on most column types, so "query by non-partition column = full scan" is too strong. But a query that doesn't hit the partition key still fans out across the ring: cheaper than a scan, never free.
- One table per query — denormalize, dual-write, own consistency across copies yourself.
- No general transactions. LWT (Paxos) does single-partition compare-and-set only, and it's slow. General-purpose transactions (Accord, CEP-15) have been in development for years and are *still not GA* — don't claim them in a design.
- Incomplete clustering key silently upserts (clobbers rows).
- **Tombstones:** deletes don't remove data, they write a marker that lingers until compaction. Read across many tombstones and latency craters — this is why Cassandra is a terrible queue (write-then-delete churns tombstones). The #1 footgun after clustering-key upserts.
- **Hot partition:** throughput and storage are spread by partition key, so one oversized or over-read partition (a celebrity user, a global bucket) pins load to one replica set while the cluster looks idle. Keep partitions bounded — a working ceiling is ~100 MB / ~100k rows — and bucket by time or hash suffix when a natural key grows unbounded.

### Mutation cost — the read tax

- **Writes are cheap, and an update is just a write** — appended to the memtable, no read-before-write. Cassandra absorbs update volume fine; the write path is not where you pay.
- **The cost lands on reads.** SSTables are immutable, so each update leaves another fragment of that row in another SSTable. A read merges fragments across SSTables — bloom filters skip most, not all — so an overwrite-heavy row gets steadily more expensive to read until compaction consolidates it.
- **Deletes are the worst case:** a tombstone is a write that makes reads slower and only disappears after compaction plus `gc_grace`.
- **So the fit isn't "written rarely" — it's mutated rarely.** Write-once-and-read and append-and-read are ideal; repeated read-modify-write on one row is where the tax shows up, as read latency and compaction I/O.

### Compaction strategy is the lever

- **STCS** (historical default) — merges similarly-sized SSTables. Cheap writes (~2–4× write amplification), high read and space amplification. Suits write-heavy / append-only.
- **LCS** — non-overlapping levels, roughly one SSTable per level per read. The answer for update-heavy or read-heavy tables, at ~10–30× write amplification.
- **TWCS** — time-windowed, for TTL'd time-series; expires whole windows without dragging reads through tombstones.
- **UCS** (5.0) — unified; configurable to behave like any of the above and changeable in flight. The current recommended default.
- Naming the compaction strategy when you propose Cassandra is a strong signal — it's where the update-vs-read tradeoff actually gets decided.

**Numbers to anchor**

| | |
|---|---|
| Write throughput | very high, scales out |
| Single-partition read | low ms |
| Add capacity | join a node |
| Consistency | tunable per query |
| Strong reads | R + W > N |
| Partition size target | < ~100 MB |
| Write amp: STCS / LCS | ~2–4× / ~10–30× |
| Default compaction (5.0) | UCS |

### CAP / consistency

AP by design, tunable toward CP. `QUORUM` reads + `QUORUM` writes satisfy R + W > N, so the read overlaps the latest write → strong consistency, at the cost of latency and availability during partitions. Even at `ALL`, you get replication consistency, never transactional — no "update these three rows or none."

### Interview line

Cassandra fits keyed lookups that are read globally and *mutated* rarely — append-and-read, not read-modify-write. Its edge over sharded Postgres isn't write throughput at my volume — it's that consistent hashing makes rebalancing automatic and multi-region replication a config line, not a project. I accept no joins and eventual consistency, tunable to strong via QUORUM/QUORUM. If the table does take frequent updates I'd move it to leveled compaction and say why: immutable SSTables mean every update fragments the row, and reads pay to merge those fragments.

### Pushback / when it flips

Below genuine global scale, Postgres is the better default even for keyed data — you keep transactions and query flexibility and defer the operational tax (repair, compaction, tombstone tuning, eventual-consistency reasoning). Cassandra is right when scale × geo-distribution × access-pattern-simplicity all hold at once. And never model a queue or high-churn delete workload on it — tombstones will punish you. Be precise about the write story too: Cassandra absorbs writes beautifully, updates included. The penalty for an overwrite-heavy table lands on read latency and compaction I/O, not on write throughput — "Cassandra is bad at these writes" is the wrong diagnosis and an interviewer will catch it.

---

## 03 · DynamoDB

*The managed, serverless member of the Dynamo family. You buy Cassandra-style write-scaling and multi-region replication without running a cluster — and pay in partition-key discipline and per-request pricing.*

### Mechanism

The partition key is hashed to place an item on a partition; an optional sort key orders items within a partition. Storage auto-shards as data and throughput grow — no nodes to manage. Reads default to eventually consistent (cheaper, served from any replica); you opt into strongly consistent reads per request (more cost, leader replica; cross-Region only under MRSC — see CAP). Capacity is on-demand (pay-per-request, auto-scales to spikes) or provisioned (RCU/WCU you set, cheaper at steady load). Secondary indexes: **GSI** (different partition key, its own throughput, eventually consistent) and **LSI** (same partition key, alternate sort key, fixed at table creation). DynamoDB Streams emits an ordered per-item change log — CDC for triggers, replication, and fan-out.

### Reach for it when

- Known key-based access at scale and you want zero ops — no cluster to run, patch, or rebalance.
- Serverless / spiky workloads — on-demand capacity tracks traffic without a capacity plan.
- Predictable single-digit-ms latency at any scale for keyed lookups.
- Multi-region active-active (global tables) as a config option, not a project.

### The model tax (know cold)

- **Hot partition:** throughput is spread across partitions by key. A skewed key (one celebrity, one tenant) concentrates load on a single partition and throttles — even when the table has spare total capacity. Same failure class as Cassandra's hot partition; pick a high-cardinality, evenly-accessed partition key.
- **Item size cap 400 KB** — large blobs go to S3 with the key stored in Dynamo.
- **Single-table design** — model access patterns up front and overload one table with composite keys; ad-hoc queries aren't a thing.
- **No joins; transactions are limited** — `TransactWriteItems` caps at 100 actions and 4 MB aggregate, costs ~2× throughput, works only within one account and Region, and is *unavailable entirely* on MRSC global tables. Not a substitute for relational transactions.
- **Cost surprises** — `Scan` and unbounded GSIs get expensive fast. Model your reads as key lookups; never design around scanning.

**Numbers to anchor**

| | |
|---|---|
| Latency (keyed) | single-digit ms |
| Item size cap | 400 KB |
| Read default | eventual (strong opt-in) |
| Transaction | ≤ 100 actions / 4 MB |
| Global tables | MREC or MRSC |
| MRSC topology | exactly 3 Regions |
| Scale | auto-shard, no ops |

### CAP / consistency

AP by default, CP on request. Within a Region, reads are eventually consistent unless you set `ConsistentRead`. Across Regions there are *two* modes. **MREC** (multi-Region eventual consistency) is the default: last-writer-wins, async replication. **MRSC** (multi-Region strong consistency) acknowledges a write only once it is durable across the Region set — RPO zero, and any Region can read the latest value.

MRSC is tightly constrained, and the constraints are the interesting part: exactly three Regions (three replicas, or two replicas plus a DynamoDB-managed **witness** that holds data but serves no traffic); all within one Region set (US / EU / AP — no mixing); the table must be empty when you enable it; the transaction APIs are unavailable; and writes and strongly-consistent reads pay a cross-Region round trip. Conflicting concurrent writes surface as `ReplicatedWriteConflictException`.

### Interview line

DynamoDB is the managed Dynamo-lineage store: partition-key scaling and global replication with no cluster to operate, in exchange for designing every access pattern into the key up front. Reads are eventually consistent unless I ask for strong per request, and my one real job is a high-cardinality partition key so I don't hot-spot one partition while the table looks under-utilized. If the requirement is a global write with zero RPO, I'd name MRSC global tables and its cost in the same breath: three Regions inside one Region set, cross-Region latency on every write, and no transaction APIs.

### Pushback / when it flips

Below real scale, Postgres still wins — you keep joins, transactions, and the ad-hoc queries Dynamo's single-table model forbids. DynamoDB vs Cassandra is mostly buy vs run: same data model and tradeoffs, DynamoDB is managed/serverless with per-request cost, Cassandra is self-hosted with fixed cluster cost. The classic incident is the hot partition — a skewed key throttles one partition while the table looks under-provisioned. Note that global tables are not eventually consistent full stop: MRSC gives you a strongly consistent multi-Region table when the requirement genuinely needs one. The real question is whether the workload will pay a cross-Region round trip on every write to get it — usually only money and inventory will.

---

## 04 · Redis

*In-memory, microsecond ops. A Swiss-army knife: cache, counter, lock, rate limiter, ephemeral queue, leaderboard. Rarely your source of truth.*

### Mechanism

RAM-resident data structures with single-threaded command execution — every command (and every Lua script) runs atomically with no locks, which is the load-bearing property. (Modern Redis uses I/O threads for network, but execution of the actual commands is still serialized, so the atomicity guarantee holds.) Durability is optional: RDB snapshots + AOF append log (`everysec` is the usual). Replicas + Sentinel/Cluster for HA. Treat it as a fast cache that can persist, not a database that happens to be fast.

### Reach for it when

- Cache in front of a slower store (the default use).
- Atomic counters — `INCR` / `DECR` for rate limits, inventory admission, fan-in completion.
- Distributed lock (short-lived; `SET NX PX` + fencing token).
- ZSET for leaderboards, waiting-room ordering, timer queues.
- Ephemeral state with TTL auto-expiry (sessions, holds).

### Cache patterns to name

- **Cache-aside (lazy):** app checks cache, on miss reads DB and populates. The default. Risk: stale entries → set TTLs / invalidate on write.
- **Write-through / write-behind:** write hits cache (and DB sync/async). Stronger freshness, more coupling.
- **Stampede / thundering herd:** a hot key expires and thousands of requests hit the DB simultaneously to refill. Mitigate with a short lock around the refill (one request repopulates), request coalescing, or probabilistic early expiry. Directly relevant to any "hot cached value" design.

### Avoid / careful when

- It's your only copy of important data — a failover to a lagging replica loses recent writes.
- Dataset > RAM. It's memory-bound; that's the cost model.
- **TTL as a business trigger:** expiry deletes a key, it doesn't run your compensation. Keyspace notifications are at-most-once — don't rely on them for correctness.

### Redis vs Valkey (know the one-liner)

- Redis is licensed RSALv2/SSPL, with AGPLv3 as a third option from Redis 8. The Linux Foundation forked 7.2.4 as **Valkey**, which is BSD and backed by AWS, Google and Oracle.
- AWS ElastiCache now defaults new clusters to Valkey and prices it below Redis. Valkey is wire-compatible — same commands, same clients.
- Nothing on this page changes between them. Just don't be surprised when an interviewer says "Valkey."

**Numbers to anchor**

| | |
|---|---|
| Op latency | ~0.1–0.5 ms |
| Throughput, one node | ~100k+ ops/s |
| Bound | RAM + network |

### CAP / consistency

CP within a shard for single-key ops (atomic execution), but the durability/HA story is weak by default — async replication + Sentinel failover can lose recently-acknowledged writes. Redis Cluster shards by key; multi-key atomicity only within a hash slot.

### Interview line

I reach for Redis when I need one thing very fast and can tolerate losing it: a cache, an atomic counter, a TTL'd hold. Serialized command execution means every op and every Lua script is atomic, which is why it's the right place for admission control and rate limiting. I keep the durable truth in Postgres behind it, and I plan for cache stampede on hot keys.

### Pushback / when it flips

For a hold/expiry pattern, Redis TTL only wins if the key *is* the hold (its disappearance is the release). If Postgres owns the counter, a DB sweeper beats Redis notifications — durable and self-healing. Use Redis for the ticket-onsale scale (100k holds/s, visible countdown); keep the sweeper for the hotel scale.

---

## 05 · Kafka

*A durable, ordered, replayable log. Not a queue you drain — a commit log consumers read at their own offset. The backbone for decoupling and buffering.*

### Mechanism

Partitioned append-only log; consumers track offsets. Each topic splits into partitions; order is guaranteed within a partition, not across. Messages persist for a retention window — consumers replay by rewinding their offset. Producers key messages to control partition (same key → same partition → ordered). Delivery is at-least-once by default; consumers must be idempotent.

### Reach for it when

- Decouple producers from consumers — upload service emits, transcode fleet consumes independently.
- Buffer a firehose — absorb spikes, consumers process at their own rate (load leveling).
- Fan-out one event to many consumer groups (analytics + search index + notifications).
- Event sourcing / CDC — the log is the source of truth; replay to rebuild.

### Operational realities (know cold)

- **Partition count is your parallelism ceiling:** within a consumer group, consumers ≤ partitions (extra consumers sit idle). You pick partition count up front and it's awkward to reduce — size for peak parallelism.
- **Consumer-group rebalancing:** when a consumer joins or leaves, partitions are reassigned. Under the classic protocol this is a stop-the-world pause, and frequent rebalances (flapping consumers, long processing) are a classic Kafka incident. The newer protocol (KIP-848) makes reassignment incremental and broker-driven, so the global pause is largely gone — name which protocol you're assuming.
- **KRaft, not ZooKeeper:** metadata lives in an internal Raft quorum of controller nodes. ZooKeeper was removed outright in Kafka 4.0, so describing Kafka as needing a ZooKeeper ensemble describes a version nobody deploys new.
- **Ordering vs. parallelism tension:** you get order within a partition, so more partitions = more parallelism but coarser ordering. Key by the entity whose order matters.

### Avoid / careful when

- You need priority or delayed/scheduled delivery — still absent; that's a task queue. (Per-message ack is not a clean separator — see share groups.)
- You need global ordering — you only get per-partition.
- Low-volume simple job dispatch — Kafka is operational weight you may not need.

### Share groups (KIP-932) — where Kafka can queue

- A **share group** lets multiple consumers read the *same* partition cooperatively, with per-message acknowledgement, a broker-side delivery count, and poison messages archived after a configurable limit (default 5).
- Consumer count is not capped by partition count for a share group — the parallelism ceiling above applies to classic consumer groups only.
- It narrows the log-vs-queue gap without closing it: no priority, no delay, and recent enough that "use a real queue" is still the safe interview answer. Knowing it exists is the differentiator.

**Numbers to anchor**

| | |
|---|---|
| Throughput | very high (MB/s+/part.) |
| Ordering | per-partition only |
| Delivery | ≥ once (be idempotent) |
| Parallelism | ≤ partitions (classic) |
| Metadata (4.0+) | KRaft, no ZooKeeper |
| Retention | hours → forever |

### CAP / consistency

CP-leaning: a partition has a leader + ISR (in-sync replicas); `acks=all` waits for the ISR, trading latency for no-loss. Exactly-once semantics (EOS) exist but only *within* Kafka — read-process-write across Kafka topics. It does not extend exactly-once to external side effects (your DB, an API), which still need idempotency.

### Interview line

I use Kafka to decouple and buffer: producers append, consumer groups read independently at their own offset, and retention lets me replay to rebuild a downstream or add a consumer. I key by entity for per-partition ordering, size partitions for peak consumer parallelism, and make consumers idempotent because delivery is at-least-once — Kafka's exactly-once doesn't cover my database write.

### Pushback / when it flips

Reaching for Kafka on a simple job queue is over-engineering — if you want per-message ack, retry, priority, and a DLQ without replay or fan-out, a task queue is simpler. Kafka earns its operational cost when you need replay, multiple independent consumers, or firehose buffering — name which one. Note the ground has shifted slightly: share groups give Kafka per-message ack, so the honest distinction is now replay and fan-out (log) versus priority, delay, and mature DLQ tooling (queue). And Kafka only transports the stream; the moment you need to window, aggregate, or join it, that's Flink's job, not a hand-rolled consumer.

---

## 06 · Flink

*Stateful stream processing with event-time windows and exactly-once state. Kafka moves the events; Flink computes over them — running aggregations, joins, and windows on the stream itself.*

### Mechanism

A dataflow graph of operators runs continuously over unbounded streams. Operators hold **keyed state** (per-key aggregates, join buffers) in a local state backend — RocksDB on local disk when state is large. Fault tolerance is **distributed checkpointing**: Chandy–Lamport barriers flow through the graph and snapshot each operator's state consistently; on failure the job rewinds to the last checkpoint and replays from the source offset → exactly-once state. **Event-time** processing with **watermarks** handles out-of-order and late events: a watermark asserts "no more events older than T," which fires time windows correctly regardless of arrival order — versus processing-time (wall clock, simpler, but wrong under lateness).

### Reach for it when

- Streaming aggregations / windows — per-minute counts, sliding-window rates, sessionization.
- Stream joins and enrichment — join two topics, or a stream against a slowly-changing table.
- Real-time analytics / alerting where batch latency is too slow.
- Stateful complex-event processing (pattern detection) over a firehose.

### The distinctions to say

- **Kafka vs Flink:** Kafka is transport + storage (the log); Flink is compute over it. "Kafka moves and retains; Flink windows, aggregates, and joins." Kafka Streams is the lighter embedded library for simpler per-app transforms.
- **Event-time vs processing-time:** event-time + watermarks is correct under out-of-order / late data; processing-time is simpler but wrong when events arrive late. Naming watermarks is the signal you actually understand streaming.
- **Stream vs batch:** Flink treats batch as a bounded stream; reach for it when you need continuous low-latency results, not a nightly job.

### Avoid / careful when

- Simple stateless transform or fan-out — Kafka consumers / Kafka Streams are lighter.
- Small volume or an occasional job — a cron batch is far less operational weight.
- Large keyed state is real ops: state-backend sizing, checkpoint tuning, savepoint / restore on redeploy.

**Numbers to anchor**

| | |
|---|---|
| Latency | ms → sub-second |
| Guarantee | exactly-once state |
| Time model | event-time + watermarks |
| State | local + checkpointed |

### CAP / consistency

Gives exactly-once *state* internally via checkpoint-and-replay; end-to-end exactly-once needs a transactional / idempotent sink (two-phase-commit connector) or the output is at-least-once. Same caveat as Kafka EOS: the guarantee holds within the processing boundary; external side effects still need idempotency.

### Interview line

When I need to compute over a stream — windowed aggregations, joins, sessionization in real time — I reach for Flink, not a Kafka consumer with a hand-rolled counter. It keeps large keyed state locally, checkpoints it for exactly-once recovery, and uses event-time watermarks so late events still land in the right window. End-to-end exactly-once still needs an idempotent sink.

### Pushback / when it flips

Flink is real operational weight — state backends, checkpoints, savepoints. If the transform is stateless or the window is trivial, Kafka Streams or plain consumers are simpler. It earns its cost only when you have large, long-lived, keyed state and need correctness under out-of-order events — name the window and the state, or you don't need Flink.

---

## 07 · Message Queue

***SQS / RabbitMQ.** Per-message work dispatch with ack, redelivery, and dead-lettering. The "distribute tasks to workers" primitive — distinct from Kafka's replayable log.*

### Mechanism

A broker holds messages; workers pull (or are pushed) one, process it, and **ack** to delete it. No ack (worker crash/timeout) → the message becomes visible again and is redelivered. After N failed attempts it goes to a **dead-letter queue (DLQ)** for inspection. Unlike a log, a consumed+acked message is gone — there's no offset to rewind, no replay, no second consumer group reading the same message.

### Reach for it when

- Task/job dispatch to a worker pool — resize emails, thumbnails, webhooks, background jobs.
- You want per-message retry + DLQ without building it (the broker owns redelivery).
- Priority or delayed/scheduled delivery (native in RabbitMQ / SQS).
- Decoupling where you don't need replay or fan-out — competing consumers draining one queue.

### Log vs. queue — the distinction to say

- **Kafka (log):** retained, replayable, multiple independent consumer groups, ordering per partition. "Many readers, rewindable history."
- **Queue (SQS/RabbitMQ):** consumed-and-deleted, per-message ack/retry/DLQ, work distributed across competing consumers. "One logical reader, work drains."
- **Rule of thumb:** need replay or multiple consumers of the same event → log. Need work distribution with retry/DLQ → queue.
- **Caveat worth voicing:** Kafka share groups (KIP-932) give per-message ack and redelivery, so that half of the distinction is soft. Priority, delay, and mature DLQ tooling are still queue territory.

### Avoid / careful when

- You need to replay history or add a new consumer that sees past events — that's a log.
- Strict global ordering — most queues don't guarantee it (SQS standard is best-effort; SQS FIFO trades throughput for order).
- Very high fan-out to many independent subscribers — pub/sub or a log fits better.

**Numbers to anchor**

| | |
|---|---|
| Delivery | ≥ once (FIFO: ~exactly) |
| Ordering | best-effort (FIFO opt-in) |
| Retry | built-in (vis. timeout) |
| DLQ | built-in after N attempts |
| Replay | none (consumed = gone) |

### CAP / consistency

Managed queues (SQS) prioritize availability and at-least-once delivery; ordering and dedup are opt-in (FIFO) at a throughput cost. Design consumers to be idempotent regardless — redelivery is normal, not exceptional.

### Interview line

For distributing background work to a pool with automatic retry and dead-lettering, I use a task queue, not Kafka. Workers ack on success; a crash just redelivers after the visibility timeout, and poison messages fall to a DLQ. I reach for Kafka instead only when I need replay or multiple independent consumers of the same stream.

### Pushback / when it flips

The mistake is defaulting to Kafka for everything "async." If there's one logical consumer draining work and you want retry/DLQ semantics for free, a queue is simpler and cheaper to operate. Flip to a log the moment you need replay, event fan-out, or an audit trail of what happened.

---

## 08 · S3 / Blob Storage

*Effectively infinite, cheap, durable bytes over HTTP. The rule: large binaries live here, your DB stores the pointer, and the bytes never transit your API tier.*

### Mechanism

Key→object store over HTTP, ~11-nines durability. Not a filesystem — flat keyspace, objects are immutable blobs (overwrite, don't edit). Standard classes replicate across ≥3 AZs (One Zone classes deliberately don't — cheaper, less durable). Tiered storage (hot → infrequent → archive) trades retrieval latency for cost. **Presigned URLs** let clients read/write directly with time-limited credentials — your server signs, the client transfers. **Multipart upload** splits large objects into parts (parallel, resumable).

### Reach for it when

- Any large binary: video, images, uploads, backups, ML artifacts, logs.
- Static assets to serve via CDN (S3 as origin).
- Data-lake / event archive (cheap, queryable later via Athena/etc).
- Decoupling upload transfer from your app servers entirely.

### The two patterns to say

- **Presigned direct upload** — client PUTs straight to S3; API only issues URLs. Bytes bypass your tier.
- **Multipart for big files** — one presigned URL per part, parallel, per-part retry, resumable via `ListParts`. Client picks part size subject to 5 MB min / 10k parts max.
- **Conditional writes** — `If-None-Match: *` writes only if the key is absent; `If-Match: <etag>` is compare-and-swap against the current version; conditional copy works the same way. Failure is a 412. This is what makes S3-only leader election, optimistic locking, and lock-free table formats possible with no separate coordination service.

**Numbers to anchor**

| | |
|---|---|
| Durability | ~11 nines (multi-AZ) |
| Single PUT cap (S3) | 5 GB |
| Max object size | 5 TB (multipart) |
| Multipart part min / max | 5 MB / 10k parts |
| First-byte latency | tens of ms |

### CAP / consistency

**Strongly read-after-write consistent** for all operations — a GET after a PUT returns the latest object. What it does *not* have: cross-object transactions, multi-key atomicity, or querying inside objects. It *does* have single-object conditional writes, which is genuine compare-and-swap on one key. It's a durable key→blob store with a CAS primitive, not a database.

### Interview line

Large binaries go to blob storage and the DB keeps only the key. Clients upload via presigned URLs so gigabytes never touch my API tier, and anything big uses multipart — one URL per part, parallel, resumable. I front it with a CDN for reads and drive state transitions off object-created events rather than trusting the client's "done."

### Pushback / when it flips

S3 is now strongly consistent *and* supports conditional writes, so two old talking points are dead: the eventual-consistency caveat and "you need a lock service to coordinate writers on S3." The real limits are no multi-object atomicity and no querying inside objects. Don't store data you'll filter/join on as blobs. And it's the pointer-in-DB pattern: an object with no DB row is an orphan you pay for — reconcile with a sweeper.

---

## 09 · CDN

*Cache bytes at edge PoPs close to users. The answer to "global users" and "read-heavy static/cacheable content." Turns 20k QPS for one object into ~one origin fetch per PoP.*

### Mechanism

Geographically distributed edge caches. User hits the nearest PoP; on a cache hit it serves locally (low latency, zero origin load). On a miss it fetches from origin, caches per TTL/headers, serves. `Cache-Control` / `ETag` govern freshness. Collapses read fan-out: N users pulling the same object = ~1 origin fetch per PoP per TTL. Also absorbs traffic spikes and DDoS at the edge.

### Reach for it when

- Static assets: JS/CSS/images, video segments, downloads.
- Global read audience for the same content.
- A hot cacheable value read enormously — e.g. the waiting-room "admitted" counter cached 2s collapses 500k polls to near-zero origin.
- Shielding origin from spikes.

### Avoid / careful when

- Personalized / per-user responses — low hit rate, little benefit (edge compute is the escape hatch).
- Highly dynamic data where staleness is unacceptable.
- **Invalidation is the hard part** — short TTL (let it expire) beats active purge where you can tolerate seconds of staleness.

**Numbers to anchor**

| | |
|---|---|
| Edge hit latency | single-digit → tens ms |
| Origin offload | often > 95% |
| Invalidation | TTL > active purge |

### CAP / consistency

Deliberately eventually consistent — the edge serves possibly-stale content bounded by TTL. That staleness is the tradeoff you accept for latency and origin offload; design around "what's cacheable and for how long," not "how do I make the edge fresh."

### Interview line

A CDN pushes cacheable bytes to edge PoPs so global reads hit a nearby cache instead of my origin — that's how one popular object survives 20k QPS at ~one origin fetch per PoP. I lean on short TTLs over active invalidation whenever seconds of staleness are acceptable, which is most static and near-static content.

### Pushback / when it flips

A CDN does nothing for personalized or write paths — don't wave it at a dynamic problem. The real design question is always invalidation: reason about what's cacheable and for how long. Staleness tolerance is the actual variable.

---

## 10 · Vector Database

*Approximate nearest-neighbor search over embedding vectors. The retrieval half of RAG: "find the k chunks most semantically similar to this query."*

### Mechanism

ANN index over high-dim vectors. Text/images → embeddings (e.g. 768–3072 dims) via a model. Query is embedded the same way; the DB finds nearest neighbors by cosine/dot distance. Exact search is O(N) per query, so it uses an approximate index — usually **HNSW** (navigable small-world graph): logarithmic-ish search, tunable recall vs. latency. Metadata filtering (tenant, date, ACL) runs alongside vector search — critical and easy to get wrong.

### Reach for it when

- RAG: ground an LLM in your corpus — retrieve top-k chunks, stuff into context.
- Semantic search (meaning, not keywords).
- Recommendations / dedup / similarity by embedding.

### Pipeline to say

- **Ingest:** chunk → embed → upsert with metadata.
- **Query:** embed → ANN top-k → filter by ACL → rerank → into prompt.
- Chunking strategy and reranking move quality more than the DB choice.

### Avoid / careful when

- Keyword/exact-match is what users want — BM25/Elasticsearch may beat or hybridize with vectors.
- Small corpus — a library (FAISS) or pgvector in Postgres beats a new system.
- **Permission leakage:** embeddings ignore ACLs. Filter by permission at query time or you retrieve across tenants.

**Numbers to anchor**

| | |
|---|---|
| Embedding dims | ~768–3072 |
| Raw vector size | dims × 4 B (float32) |
| Quantization | int8 ~4×, binary ~32× |
| 1M × 1536-dim | ~6 GB raw + graph |
| Index | HNSW (recall↔latency) |

### CAP / consistency

Usually eventually consistent and read-optimized; a just-upserted vector may not be immediately searchable. Fine for RAG (corpus changes slowly). **The deployed memory footprint is the real gotcha** — the HNSW graph frequently exceeds the raw vectors, and quantization is how you fit large corpora in RAM.

### Interview line

For RAG I embed and index chunks with HNSW, then at query time embed the question, pull top-k by cosine, filter by the user's ACL, and rerank before building the prompt. Chunking and reranking drive quality more than which vector DB. Below a few million vectors I'd just use pgvector; above that I'd budget for the index memory and consider quantization.

### Pushback / when it flips

Vector search isn't always the answer — hybrid (BM25 + vector) often wins because pure semantic misses exact terms (names, IDs, codes). And the sharp failure mode is permissions: sensitive data in embeddings/logs and cross-tenant retrieval. Raise ACL-at-query-time unprompted — it's the People-Innovation kill-shot.

---

## 11 · Workflow Orchestrator

***Temporal / Step Functions.** Durable multi-step workflows with fan-out/fan-in and exactly-once continuation. The answer to "coordinate N async tasks and know when all are done."*

### Mechanism

Event-sourced state machine + replay. Every state transition is appended to a durable history log — that log is truth, not in-memory state. On crash, the workflow re-executes from the top, but completed steps return their *recorded* results from the log instead of re-running; real execution resumes only past the end of history. Fan-in is a read over the ordered log ("is there a completion for every scheduled task"), decided by a single evaluator — so no concurrent-counter race. Requires deterministic workflow code (no clocks/random outside activities).

### Reach for it when

- Fan-out/fan-in: spawn N tasks, run one step when all finish (transcode ladder → mark READY).
- Long-running, multi-step, must survive crashes (order saga, provisioning).
- Steps need retries, timeouts, compensation without hand-rolled state.
- You'd otherwise build a status table + counter + reaper by hand.

### Avoid / careful when

- Single-step / fire-and-forget — a queue is enough.
- Ultra-low-latency synchronous paths (replay + persistence add overhead).
- Activities are at-least-once — the *continuation* is exactly-once, but activity code must be idempotent.

**Two flavors + numbers**

| | |
|---|---|
| Temporal | your code + replay |
| Step Functions | declarative JSON FSM |
| Fan-in | built-in primitive |
| Guarantee | exactly-once continuation |

### CAP / consistency

The orchestrator's own durability comes from its backing store (Temporal: Cassandra/Postgres/MySQL; Step Functions: managed). What it gives you is **exactly-once continuation** — the workflow advances as if each step ran once — layered on at-least-once activity execution. The two are different; your activities still need idempotency.

### Interview line

When I need to fan out N tasks and fire one step when all complete, I reach for an orchestrator instead of a hand-rolled counter-and-reaper. It persists every transition to a durable log and decides completion with a single reader over that ordered log, so the fan-in race is gone by construction. Continuation is exactly-once; I still make activities idempotent.

### Pushback / when it flips

Don't reach for it for a single async job — that's a queue, and the replay/determinism model is real cognitive + operational cost. The mechanism to name even if you hand-roll: atomic `DECR` for "am I last," a guarded status transition for idempotent completion, and a reaper for stalls.

---

## 12 · ZooKeeper / etcd

*Strongly-consistent coordination for small metadata: leader election, distributed locks, config, membership. Not a data store — a consensus-backed source of truth for "who's the leader" and "who's alive." (etcd is the modern, Raft-based equivalent.)*

### Mechanism

A replicated in-memory tree of znodes (etcd: a flat key space), kept consistent across a small ensemble by an atomic-broadcast/consensus protocol — ZAB for ZooKeeper, Raft for etcd. Writes go through a leader and commit only on a quorum (majority), so an ensemble of 2f+1 tolerates f failures (5 nodes → survive 2). Three primitives carry all the use cases: **ephemeral znodes** vanish when a client's session heartbeat lapses (→ liveness/membership); **watches** notify clients of changes (→ config push, leader-change notification); **sequential znodes** give globally ordered names (→ fair locks and leader election).

### Reach for it when

- Leader election / single-writer coordination — who owns this shard, who runs the singleton cron.
- Distributed locks / barriers that must be correct (ephemeral + sequential znodes).
- Service discovery / membership — ephemeral nodes as a live registry.
- Config that must be consistent and pushed to watchers on change.

### The distinctions to say

- **Not a database:** kilobytes per znode, whole tree in memory. Store pointers and coordination state, never bulk data.
- **Consistency over availability:** writes need quorum, so a minority partition can't write — CP by design. That's the point; you want the lock wrong-proof, not always-available.
- **Redis lock ≠ this:** `SET NX` + fencing is a best-effort lease (safe with a fencing token, but availability-first); ZooKeeper/etcd give consensus-backed correctness. Name the difference when a double-holder is a correctness bug.
- **Increasingly invisible — and increasingly etcd:** ZooKeeper sat under other systems for a decade, and that is receding. Kafka replaced it with its own Raft implementation (KRaft); HBase still uses it; and for most engineers today consensus coordination is met as etcd under Kubernetes.

**Numbers to anchor**

| | |
|---|---|
| Ensemble | 3 or 5 (2f+1) |
| Data size | KB per znode |
| Writes | quorum consensus |
| Consistency | linearizable writes (CP) |

### CAP / consistency

Strongly consistent / CP: linearizable writes via quorum; reads are sequentially consistent and can lag slightly (use a `sync`/quorum read for linearizable reads). It deliberately sacrifices availability in the minority partition — the ensemble stops accepting writes rather than risk split-brain, which is exactly what you want backing a lock or leader election.

### Interview line

For leader election, locks, or membership I want consensus-backed coordination — ZooKeeper or etcd — not a Redis lock. Ephemeral znodes give me liveness, sequential znodes give ordered fair locks, and quorum writes make it CP so the lock can't split-brain. I keep only kilobytes of coordination metadata there; the real data lives elsewhere.

### Pushback / when it flips

Reaching for ZooKeeper directly is now rare, and the trend is one-directional: Kafka, its most famous dependent, dropped it entirely in 4.0. etcd (Raft, behind Kubernetes) is the modern default — propose that, and treat ZooKeeper as the name for the pattern rather than the deployment you'd choose today. For a best-effort lock where an occasional double-run is tolerable, a Redis lease is simpler and cheaper; escalate to consensus only when a double-leader is a correctness bug, not a nuisance. And never put throughput or bulk data on it — every write is a consensus round.

---

## 13 · Elasticsearch

*An inverted index for full-text and faceted search. A secondary read model you feed from your primary store — not your source of truth.*

### Mechanism

Inverted index (Lucene) + distributed shards. Text is analyzed (tokenized, lowercased, stemmed) into terms; the inverted index maps term → documents, so full-text queries are fast. Relevance ranked by **BM25**. Indexes shard + replicate for scale and HA. Near-real-time, not immediate — a refresh interval (default ~1s) gates visibility. Async-fed from your primary DB via CDC or dual-write.

### Reach for it when

- Full-text search with relevance ranking (search bars, docs, logs).
- Faceted / filtered search — aggregations across many fields (e-commerce filters).
- Log / observability search at scale (the ELK stack).
- Hybrid with vectors for semantic + keyword.

### Avoid / careful when

- As a primary store — it's a derived index; rebuild from truth. Don't put data only here.
- You need strong consistency / transactions — near-real-time and no ACID.
- Simple exact lookups — a DB index is cheaper and simpler.
- Keeping it in sync is the real cost — CDC pipeline + reconciliation.

**Numbers to anchor**

| | |
|---|---|
| Visibility | near-real-time (~1s) |
| Ranking | BM25 |
| Role | derived read model |

### CAP / consistency

AP-leaning and eventually consistent with your primary by construction (async-fed, ~1s refresh). Treat divergence as normal: design the sync pipeline, a reconciliation path, and the ability to rebuild the index from the source of truth at any time.

### Interview line

Full-text and faceted search go to Elasticsearch as a secondary read model fed from my primary store via CDC — the inverted index and BM25 give relevance ranking a B-tree can't. It's near-real-time and not my source of truth, so I design the sync pipeline and a reconciliation path, and I can rebuild the index from the primary at any time.

### Pushback / when it flips

The trap is treating it as a database. It's a derived index — the hard part is the sync pipeline and its consistency, not the query. For semantic search, hybrid BM25 + vector usually beats either alone. For plain exact-match, a Postgres index is simpler and consistent.

---

## 14 · OLAP / Columnar Store

***ClickHouse / Snowflake / BigQuery.** Scan-and-aggregate over billions of rows. The read model behind dashboards, funnels, and ad-hoc analytics — never your transactional store.*

### Mechanism

Column-oriented storage: each column is stored contiguously and compressed, so a query touching 3 of 200 columns reads roughly 3/200 of the bytes — the whole reason a `GROUP BY` over a billion rows is feasible. Adjacent values in a column are similar, so compression is high. **Vectorized execution** processes batches of column values per instruction instead of row-at-a-time. Data is sorted/partitioned (usually by time) with per-block min/max, so range predicates prune entire blocks without reading them. Fed asynchronously from the primary store via CDC or batch ETL.

### Reach for it when

- Dashboards and reporting over large event/fact tables — aggregations across billions of rows.
- Ad-hoc analytical slicing where the query shape isn't known in advance.
- Funnel, retention, cohort analysis; time-series rollups.
- You're about to point heavy analytics at a Postgres replica and melt it.

### The distinctions to say

- **OLTP vs OLAP:** a row store is optimized for "all columns of one row"; a column store for "one column of all rows." That single sentence is the whole tradeoff.
- **vs Flink:** Flink pre-computes fixed aggregations continuously as events arrive; OLAP stores raw rows and answers *unanticipated* questions at read time. Real systems use both.
- **vs Elasticsearch:** ES is an inverted index for text relevance; OLAP is scan + aggregate over typed columns.
- **ClickHouse vs warehouse:** ClickHouse for sub-second, real-time-ingest, user-facing analytics; Snowflake/BigQuery for elastic, separated storage/compute, higher-latency internal analysis.

### Avoid / careful when

- Point lookups or per-row updates — updates mean rewriting/merging parts; use a row store or KV.
- Transactions, foreign keys, referential integrity — not the model.
- Results must be immediately consistent with the primary — it's async-fed and insert-batched.
- Small data — a Postgres index or materialized view is simpler and one fewer pipeline.

**Numbers to anchor**

| | |
|---|---|
| Compression | ~5–10× typical |
| Scan rate | 100M+ rows/s/node |
| Query latency | sub-second → seconds |
| Insert pattern | batched, not row-at-a-time |
| Role | derived read model |

### CAP / consistency

Eventually consistent with the primary by construction, and typically without multi-statement transactions. Same discipline as Elasticsearch: it's derived, so design the ingest pipeline, tolerate seconds-to-minutes of lag, and keep the ability to rebuild from the source of truth.

### Interview line

Analytics goes to a columnar store fed by CDC, not to a read replica — column storage plus vectorized execution means an aggregation over billions of rows only reads the columns it touches, and time partitioning prunes most blocks before they're read. I batch inserts rather than writing row-at-a-time, accept seconds of lag behind the OLTP store, and keep Postgres as truth.

### Pushback / when it flips

Don't add it before the data is big — Postgres with a materialized view or a rollup table absorbs a surprising amount, and a separate analytics store is another pipeline to keep in sync and reconcile. The real trigger is query shape plus volume: unbounded scans and aggregations over a fact table your OLTP primary can't serve without competing with production traffic.

---

## 15 · Push Notifications

*The only way to reach a user whose app is closed. You never talk to the device — you hand a message to Apple or Google and they decide whether it arrives. Best-effort by construction, which is the fact the whole design has to absorb.*

### Mechanism

You do not own the connection. The OS holds one persistent socket to its vendor's push service, shared by every app on the device, which is why push costs no battery per app. Your server authenticates to that service and posts a message addressed by **device token**.

- **APNs** (Apple) — HTTP/2, one POST per notification. Auth is a **JWT signed with a `.p8` key** (modern; one key works across all your apps and doesn't expire) or a per-app certificate (legacy; expires annually and has caused many outages).
- **FCM** (Google) — the **HTTP v1 API**, authenticated with a Google service account OAuth token. On iOS, FCM is a *wrapper*: it forwards to APNs on your behalf, so an iOS message through FCM inherits every APNs constraint.
- **Web Push** — an IETF standard rather than a vendor API. The browser gives you a subscription (endpoint URL + keys); you encrypt the payload to those keys (RFC 8291) and sign the request with **VAPID**. The endpoint host varies by browser — Mozilla's autopush, Google's, Apple's — and your code doesn't care, which is the point of the standard.

**The token lifecycle is the part that bites.** Tokens are per app-install, not per user, and they rotate on reinstall, restore, and sometimes OS upgrade. So the mapping is `user → many devices → one token each`, and a device may belong to several users. When the vendor tells you a token is dead — APNs `410 Unregistered`, FCM `UNREGISTERED`/`NOT_FOUND` — you must **delete it immediately**. Continuing to send to dead tokens is the single most common cause of getting rate-limited or throttled by a provider.

**Fan-out shape.** Notification service consumes an event → resolves recipients and their devices → applies preferences, quiet hours, and dedupe → renders per-locale content → enqueues one job per token → workers post to APNs/FCM with retry and backoff. The per-token send is the parallel part and the per-user preference lookup is the hot read, so cache it.

### Reach for it when

- The user is not in your app and the message is worth interrupting them for.
- You need OS-level delivery: lock screen, badge, sound, or a background wake-up.
- **Silent push** — `content-available` / a data-only message — to trigger a background sync or refresh without showing anything. Deliberately throttled by both vendors; it is a hint, not a command.
- You want a cheap edge-triggered refresh instead of holding a socket open to a backgrounded app.

### Avoid / careful when

- **You need delivery confirmation.** You don't get one. APNs and FCM report *accepted for delivery*, not *shown to a user*. Never build a flow whose correctness depends on a push arriving.
- **Anything sensitive in the payload.** It transits a third party and renders on a lock screen. Send an identifier and let the app fetch the content.
- **Ordering matters.** There is none. Two notifications sent in order can arrive in either, or one may be collapsed away.
- **You are fanning out to millions.** Bound it: per-token rate limits, per-tenant quotas, and a queue. A marketing blast and a security alert must not share a worker pool — the alert loses.
- **The user has opted out**, which on iOS they must first opt *in* to at all. Permission state lives on the device; your server's copy is a cache and can be wrong.

**Numbers to anchor**

| | |
|---|---|
| APNs payload | 4 KB (5 KB for VoIP) |
| FCM payload | 4 KB |
| APNs default storage | ~30 days, `apns-expiration: 0` means discard if offline |
| FCM TTL | 0 to 2,419,200 s (28 days) |
| FCM collapse keys held per token | 4 |
| FCM non-collapsible messages queued per offline device | 100, then dropped |
| APNs collapse ID | ≤ 64 bytes |
| Priority | APNs `apns-priority` 10 = immediate, 5 = power-efficient, 1 = lowest. FCM `high` wakes a dozing device, `normal` may be delayed |

### CAP / consistency

Not a store, so CAP doesn't apply — but the delivery contract is the equivalent question and it is **at-most-once, best-effort, unordered**. The vendor stores and forwards while the device is offline, then drops the message when TTL expires, when a newer message shares its collapse key, when the offline queue overflows, or when the app has been force-stopped.

The design consequence is a rule worth stating out loud: **the notification is a hint, and your database is the truth.** The badge count comes from the server on next launch, not from arithmetic on received pushes. The inbox is a queryable resource, and push is one delivery channel over it — which is also what makes multi-device coherent, since two devices that received different subsets of pushes still render the same inbox.

### Interview line

Push is the one channel that reaches a closed app, and it's best-effort — APNs and FCM tell me a message was accepted, never that it was seen. So I model notifications as a durable server-side inbox and treat push, in-app, email, and SMS as delivery channels over it; the payload carries an ID rather than content, both because 4 KB is the ceiling and because it renders on a lock screen. I'd use collapse keys so a user who was offline for an hour gets one current notification instead of forty stale ones, TTL so nothing arrives after it stopped being true, and separate queues per class so a marketing blast can't delay a security alert. And I'd delete tokens the instant APNs returns a 410 — sending to dead tokens is how you get throttled.

### Pushback / when it flips

**Build the fan-out, buy the last mile.** Talking to APNs and FCM directly is genuinely easy — an HTTP/2 POST and a JWT — and the hard parts are yours regardless: recipients, preferences, quiet hours, dedupe, localization, token hygiene, and rate limiting. What you buy from an aggregator is the campaign and analytics layer, not the protocol.

| Provider | Actually gives you |
|---|---|
| **Direct APNs + FCM + Web Push** | Full control, no per-message cost, all the token lifecycle work. The right default when notifications are transactional and product-owned |
| **AWS SNS mobile push / Azure Notification Hubs** | Cross-platform fan-out and token registries as managed infrastructure, without a marketing product bolted on |
| **OneSignal / Airship / Braze / Iterable** | Campaigns, segmentation, scheduling, A/B tests, delivery analytics — a marketing tool that also sends push |
| **Expo / Firebase directly** | The fast path for a small mobile team; Expo's service is a thin wrapper over both vendors |
| **Twilio / Courier / Knock** | Multi-channel orchestration: one API for push, SMS, email, and in-app, with preference management |

The flip: once notification *content* is owned by marketing rather than engineering, an aggregator stops being an abstraction over an easy API and starts being the product surface a non-engineer needs — and that, rather than protocol difficulty, is the real buy decision. The other flip is Web Push, where the standard is good enough that a library plus a subscription table is usually the whole implementation.

---

## 16 · Decision matrix

*Collapse the fifteen server-side entries into one glance. Match the workload on the left to the default pick; the "because" is the one-line justification.*

| Workload | Default pick | Because |
|---|---|---|
| Transactions, joins, ad-hoc queries | PostgreSQL | ACID + query flexibility; the default until something breaks |
| Keyed lookups, global reads, huge scale (self-run) | Cassandra | auto-rebalance + multi-region writes; you don't need joins |
| Keyed lookups at scale, serverless / zero-ops | DynamoDB | Dynamo-lineage auto-shard, managed, per-request cost; design the partition key |
| Write firehose / > ~50k writes/s to one table | Cassandra / DynamoDB / TSDB | LSM absorbs append-heavy volume one Postgres primary can't |
| Cache / counter / lock / TTL'd ephemeral state | Redis | in-memory, atomic ops, microsecond latency |
| Decouple + replay + multiple consumers | Kafka | retained ordered log, rewindable, fan-out |
| Windowed aggregation / stream join / sessionize | Flink | stateful stream compute, event-time watermarks, exactly-once state |
| Background jobs with retry + DLQ | Queue (SQS / RabbitMQ) | per-message ack/redelivery; no replay needed |
| Large binaries (video, images, uploads) | S3 / Blob | infinite cheap durable bytes; keep the pointer in the DB |
| Global static / hot read-heavy content | CDN | serve from the edge; collapse read fan-out |
| Semantic search / RAG retrieval | Vector DB | ANN over embeddings; hybrid with BM25 for exact terms |
| Coordinate N tasks, fan-in, sagas | Orchestrator | durable fan-out/fan-in, exactly-once continuation |
| Leader election / lock / membership / consistent config | ZooKeeper / etcd | consensus-backed coordination (CP); not a data store |
| Full-text / faceted search | Elasticsearch | inverted index + BM25; a derived read model, not truth |
| Dashboards / ad-hoc aggregation over billions of rows | OLAP / columnar | column scans + vectorized execution; derived from OLTP via CDC |
| Reach a user whose app is closed | APNs / FCM / Web Push | the only channel the OS will wake; best-effort, so keep a durable inbox as truth |

### The meta-rule

Most systems are **Postgres + one or two specialists**: Postgres as the transactional source of truth, plus a cache (Redis), a blob store (S3), a CDN, and maybe a search, vector, or analytics index fed from Postgres via CDC. Reach for Cassandra / DynamoDB / Kafka / Flink / an orchestrator only when a *named requirement* — a specific hot table past ~15–50k writes/s, global write scale, replay/fan-out, real-time stream compute, durable multi-step coordination — forces it. Naming the one store as truth and treating the rest as derived is the coherence signal.

---

> **The second half of this sheet is the browser.** Everything above is a system you provision, pay
> for, and can restart. Everything below is already on the user's device, was not chosen by you, and
> can be evicted, blocked, or opened in six tabs at once. The entries follow the same skeleton.

> **What lives here, and what lives elsewhere.** This chapter is the **mechanism**: what object the
> browser constructs, which thread it runs on, what the socket and the storage engine actually do,
> and how each one fails. The *selection* tables — which rung of the transport ladder to climb, which
> store to pick for an offline feature — stay in `Client-Side System Design` §01, and the production pathologies
> of streaming a model response stay in `OpenAI Screen` §05. If a sentence would fit in a cell of one
> of those tables, it belongs there; if it explains why the cell says what it says, it belongs here.

---

## 17 · localStorage / sessionStorage

*Synchronous, string-only, origin-scoped key-value. The right answer for a theme flag and the wrong answer for anything you would call data — because every read and write blocks the main thread.*

### Mechanism

A synchronous map of string keys to string values, persisted per **origin** (scheme + host + port), exposed as `window.localStorage`. `sessionStorage` is the same API with a lifetime bounded by the tab — it survives reload, dies with the tab, and is **not** shared between two tabs on the same site, though it *is* copied into a tab opened via `target="_blank"`.

The word that matters is **synchronous**. `getItem` and `setItem` return when the work is done, and on most engines that work includes hitting disk. The API stores strings only, so every real use is wrapped in `JSON.parse` and `JSON.stringify` — which means a 2 MB value costs you a 2 MB parse on the main thread, and that parse is not interruptible. This is why the store that looks cheapest is the one most likely to show up in a performance trace: reading a large blob during startup blocks first paint, and writing on every keystroke blocks input.

It is also **shared mutable state across tabs with no coordination**. Two tabs writing the same key is last-write-wins with no version, no compare-and-set, and no notification to the writer. The `storage` event fires in *other* tabs of the same origin — never in the tab that made the change — and carries the key, the old value, and the new value. That asymmetry is deliberate and is the only cross-tab signal the API offers; see §27 for what replaced it.

### Reach for it when

- The value is small, a string already, and losing it is a minor annoyance rather than a bug — theme, locale, sidebar collapsed, last-used tab.
- You need the value **before first paint** and an async read would cause a flash of the wrong theme. This is the one case where synchronous is a feature.
- You want a flag readable by a synchronous inline script in the document head.
- A feature flag or an onboarding-seen marker, where a stale value degrades gracefully.

### Avoid / careful when

- **Anything you would call data.** Documents, queues, cached responses, and lists all belong in §19.
- Writing on a high-frequency event. Debounce to a trailing write, or you pay a synchronous disk hit per keystroke.
- Storing tokens or anything secret — it is readable by any script that reaches the page, which is the whole XSS argument in §18.
- Assuming it exists. Safari's private mode historically threw on write, and some privacy modes present a zero-quota store, so a bare `setItem` needs a `try`/`catch`.
- Assuming it is big. The ~5 MB is per origin and is **not** part of the quota-managed bucket in §19 — it has its own, smaller, generally non-negotiable budget.

**Numbers to anchor**

| | |
|---|---|
| Capacity | ~5 MB per origin |
| Value type | string only |
| Access | synchronous, main thread |
| Cross-tab signal | `storage` event, other tabs only |
| Typical write | sub-ms small, ms+ at MB scale |

### CAP / consistency

Not a distributed store, so CAP doesn't apply — but the equivalent question is the **durability contract**, and it is *persistent until something clears it, with no guarantee that anything survives*. The user can clear it, the browser can clear it under privacy settings, a privacy mode can present it as empty, and an extension can write to it. Across tabs it is last-write-wins with no version and no conflict signal. The design consequence: treat it as a **hint that makes the next load nicer**, never as a record whose absence is an error.

### Interview line

I use `localStorage` for things I would be happy to lose — theme, locale, a collapsed sidebar — and specifically for the ones I need synchronously before first paint, because that's the only place its synchronous API is an advantage rather than a hazard. Everything I'd call data goes to IndexedDB instead, because `localStorage` is string-only and blocks the main thread, so a large value costs me a `JSON.parse` in the middle of startup. And I'd never put a token there; it's readable by any script that reaches the page.

### Pushback / when it flips

The reflex to say "never use `localStorage`" is as wrong as reaching for it by default. It flips back the moment the requirement is *"this must be readable before the first paint"* — an async store cannot satisfy that, and a theme flag read from IndexedDB gives you a flash of the wrong colours on every load. The real rule is about size and frequency, not about the API: small, rare, and tolerable-if-lost is exactly its niche, and moving a 40-byte string to IndexedDB to feel modern buys you nothing and costs you a frame.

---

## 18 · Cookies

*The only client store the server ever sees, because the browser attaches it to requests automatically. That automatic attachment is both the entire feature and the entire attack surface.*

### Mechanism

A cookie is a small name-value pair with attributes, set by a `Set-Cookie` response header or by `document.cookie`, and **sent by the browser on matching requests without anyone asking**. That is the one property nothing else on this page has: `localStorage` and IndexedDB are inert until your JavaScript reads them, and a cookie participates in requests your code never wrote — an image load, a form post, a `fetch` from another site.

Matching is by **domain and path**, not by origin, which is why cookies are a weaker boundary than every other store here: `https://a.example.com` and `http://b.example.com` can share a cookie set on `.example.com`, though the `Secure` attribute and cookie prefixes narrow that. The attributes are the whole security model:

**`HttpOnly`** removes the cookie from `document.cookie`, so injected script cannot read it — the reason a session cookie survives an XSS that would have leaked a token from `localStorage`. **`Secure`** sends it only over HTTPS. **`SameSite`** governs cross-site attachment: `Strict` never attaches on a cross-site request, `Lax` attaches on top-level GET navigation only (now the default in major browsers), and `None` attaches always but requires `Secure`. **`Partitioned`** (CHIPS) gives an embedded third-party cookie a separate jar per top-level site, which is how a legitimately embedded widget keeps state as third-party cookies are phased out. `Max-Age`/`Expires` decide whether it dies with the browser session.

The size ceiling is the other design constraint: roughly **4 KB per cookie** and a few dozen per domain, and every one of them rides on **every matching request**, so a fat cookie is a permanent tax on upload bandwidth for every asset request on the domain.

### Reach for it when

- You need the server to know who this is on a plain navigation, before any JavaScript runs — session identity, and effectively nothing else does this.
- You want the credential out of JavaScript's reach: `HttpOnly` plus `Secure` plus `SameSite` is a materially stronger posture than any token in `localStorage`.
- A CDN or edge worker needs to vary a response on something the client knows.
- A tiny piece of state must survive across subdomains, which origin-scoped stores cannot do.

### The distinctions to say

**Cookies get CSRF; `localStorage` gets XSS.** They are different attacks and you do not get to avoid both by choosing well. A cookie is attached automatically, so another site can cause an authenticated request — the defence is `SameSite` plus an anti-CSRF token on state-changing requests. A token in `localStorage` is never attached automatically, so CSRF is structurally impossible — but any injected script can read and exfiltrate it, and it is still valid on the attacker's machine afterwards.

**So the honest answer to "where do I put the auth token" is neither, exactly:** the refresh token goes in an `HttpOnly` `Secure` `SameSite` cookie, and the short-lived access token lives **in memory** and dies with the page. That gives you XSS resistance for the long-lived credential, CSRF resistance for the short-lived one, and a blast radius measured in minutes. It costs you a silent-refresh call on load, which is the trade.

### Avoid / careful when

- Storing anything of size. 4 KB, and it is uploaded on every request to the domain.
- Treating `SameSite=Lax` as complete CSRF protection — it is very good, but a top-level GET that changes state is still exposed, which is a reason state-changing GETs are a bug.
- Reading `document.cookie` for auth. If your JavaScript can read it, so can injected script; that cookie is not doing the job you think.
- Assuming third-party cookies work. They are blocked or partitioned by default in most browsers now; embedded widgets need `Partitioned`.

**Numbers to anchor**

| | |
|---|---|
| Size | ~4 KB per cookie |
| Count | ~50 per domain, ~180 total |
| Scope | domain + path, not origin |
| Overhead | uploaded on every matching request |
| `SameSite` default | `Lax` in major browsers |

### CAP / consistency

Not a store you query, so the equivalent question is the **attachment contract**: the browser decides, from domain, path, `Secure`, and `SameSite`, whether this cookie rides along — and your code is not consulted. That makes cookies the only client state with a *server-observable* consistency question, and the failure is asymmetric: a cookie that fails to attach logs the user out, which they will report, while a cookie that attaches when it shouldn't is CSRF, which they will not. The design consequence: decide attachment declaratively through the attributes, and never through JavaScript that runs after the request would already have been made.

### Interview line

Cookies are the only client store the server sees automatically, so I use them for session identity and almost nothing else — 4 KB, and it's uploaded on every request to the domain. For auth specifically I'd put the refresh token in an `HttpOnly` `Secure` `SameSite=Lax` cookie and keep the short-lived access token in memory, because that gets me XSS resistance on the long-lived credential and CSRF resistance on the one that's actually used. The tradeoff I'd name is that cookies buy XSS resistance and hand me a CSRF problem, and `localStorage` does exactly the inverse — you pick which attack you'd rather defend, and `SameSite` plus a token on state-changing requests is the cheaper defence.

### Pushback / when it flips

**"Never store tokens in `localStorage`" is right in general and wrong for a pure SPA against a third-party API on another origin**, where the cookie cannot attach anyway and you have an in-memory token with a refresh flow regardless. The genuinely load-bearing question is not which store, it is **how long the credential is valid and what revokes it** — a fifteen-minute access token in `localStorage` with server-side revocation is a smaller problem than a thirty-day `HttpOnly` cookie no one can invalidate. Say that, and the store choice stops being a shibboleth and becomes a consequence.

---

## 19 · IndexedDB

*The browser's real database: asynchronous, transactional, indexed, and measured in hundreds of megabytes. When a guide says an outbox or a cached document "survives a reload," this is the thing doing it.*

### Mechanism

An **origin-scoped, asynchronous, transactional object database**. A database has a numeric version and contains **object stores**, which are the tables. A store holds structured-cloneable values — objects, arrays, `Date`, `Blob`, `ArrayBuffer`, `Map`, `Set`; not functions, not DOM nodes — keyed either by an in-band **key path** (`{keyPath: 'id'}`) or by an out-of-band key you supply. Each store can carry **indexes** over other properties, and an index is itself queryable by key or by `IDBKeyRange`, which is what turns it from a key-value blob into something you can ask questions of.

Schema changes happen in exactly one place. You open with a version number, and if it is higher than what is on disk the browser fires **`upgradeneeded`**, and that handler is the *only* moment you may create or delete stores and indexes. Everything else — every read and write — happens inside a **transaction** scoped to a named set of stores, in `readonly` or `readwrite` mode. Transactions are ACID within the database, `readwrite` transactions over overlapping stores are serialized, and a failed request aborts the whole transaction and rolls it back.

The sharp edge, and the one that generates most real bugs: **a transaction auto-closes when its microtask queue drains.** If you `await` anything that is not an IndexedDB request inside a transaction — a `fetch`, a timer, an unrelated promise — the transaction commits out from under you and the next operation throws `TransactionInactiveError`. The mental model is that a transaction lives for as long as it has outstanding IndexedDB work and not one tick longer. Do your network call first, then open a transaction and write.

The API itself is event-based (`onsuccess`, `onerror`, `onupgradeneeded`) rather than promise-based, and predates `async`/`await` by years. That is the entire reason a wrapper such as `idb` exists — it is a thin promise adapter over the same objects, not a different database, and reaching for it is a convenience decision rather than an architectural one. **Cursors** (`openCursor`) iterate a store or index one record at a time, which is how you page through more data than you want in memory.

### Reach for it when

- Anything you would call data must survive a reload: cached documents, a message transcript, a downloaded dataset.
- You need an **outbox** — mutations queued locally, replayed when the network returns — because the queue must be durable and ordered, and losing it silently loses the user's work.
- The volume is beyond a few hundred kilobytes, which rules out §17 immediately.
- You need to query by something other than the primary key, which is the index story and the reason this is a database rather than a bucket.
- You are storing binary — `Blob` and `ArrayBuffer` go in directly, with no base64 tax.

### Quota and eviction (know cold)

This is the part of client storage that is not in any API doc's first paragraph and is the reason "offline-first" projects fail late.

- **One bucket per origin, shared.** IndexedDB, the Cache API (§20), and OPFS (§21) draw on a **single origin quota**. They do not have separate budgets, so a service worker caching aggressively can starve your database.
- **The quota is a fraction of free disk, not a fixed number.** `navigator.storage.estimate()` returns `{usage, quota}` at runtime. You cannot quote a constant, and you should not hard-code one — ask.
- **Eviction is all-or-nothing per origin.** Under storage pressure the browser does not drop your least-recently-used records; it clears the origin. Designing for "we'll lose some rows" is designing for a failure mode that does not happen.
- **`navigator.storage.persist()`** asks to move the origin from best-effort to persistent so it is not evicted under pressure. The grant is heuristic — installed PWAs and highly-engaged sites get it, a first visit does not — so treat it as a request, never a guarantee, and check `persisted()`.
- **Safari evicts script-writable storage after roughly seven days without interaction.** This is the single fact that breaks offline-first on iOS, and volunteering it is a strong signal.

### Avoid / careful when

- `await`-ing anything non-IndexedDB inside a transaction. Fetch first, then transact.
- Treating it as the source of truth. It is a cache of server truth plus a queue of intent; the origin can be cleared at any moment by a user, a privacy mode, or the eviction above.
- Doing large synchronous work in the success callback — the reads are async, but your `JSON.parse` and your render are not.
- Version-number races across tabs: one tab upgrading blocks the others, which fire `versionchange`. Listen for it and close, or the upgrade hangs forever.
- Using it for a 40-byte flag you need before first paint. That is §17's job.

**Numbers to anchor**

| | |
|---|---|
| Capacity | hundreds of MB → GB, quota-based |
| Quota basis | fraction of free disk |
| Access | async, transactional |
| Eviction | all-or-nothing per origin |
| Safari idle eviction | ~7 days |
| Shared bucket with | Cache API, OPFS |

### CAP / consistency

Genuinely transactional — ACID within one origin's database, with serialized `readwrite` transactions and real rollback — so the interesting question is not consistency but **durability, and the answer is best-effort by default**. The origin's entire bucket can be evicted under disk pressure, cleared by the user, or reclaimed by Safari after a week of inactivity, and `persist()` only upgrades that to *probably not*. Across tabs, transactions serialize correctly, but nothing tells tab B that tab A committed — see §27. The design consequence is the rule the whole client half of this sheet rests on: **client storage is a cache of server truth plus an outbox of intent, and never the only copy.**

### Interview line

IndexedDB is the browser's real database — asynchronous, transactional, indexed — so it's where anything I'd call data goes: cached documents, a message transcript, and especially an outbox of mutations that has to survive a reload. The two things I'd say without being asked are that a transaction auto-closes as soon as its microtask queue drains, so you do the `fetch` first and then open the transaction, and that eviction is all-or-nothing per origin rather than per record — which is why I treat it as a cache of server truth plus a queue of intent, never as the only copy. If durability actually matters I'd call `navigator.storage.persist()`, and I'd still expect Safari to reclaim it after about a week of no interaction.

### Pushback / when it flips

**It flips when the data is small enough that the ceremony costs more than the store saves** — version handlers, transactions, and a wrapper dependency for what is genuinely three keys is over-engineering, and §17 is the right answer. It flips the other way, toward §21, when the workload is file-shaped or when you want SQL: SQLite compiled to WASM over OPFS gives you real queries and synchronous access inside a worker, and people reach for it precisely because IndexedDB's index story runs out when the queries get relational. And the framing to resist is "IndexedDB gives us offline" — it gives you *storage*; offline is the sync protocol, the conflict policy, and the outbox around it, which is `Client-Side System Design` §01 F.

---

## 20 · Cache API & Service Worker

*A programmable HTTP proxy that runs in your own origin, plus the response store it reads from. The only way to answer a request when the network is gone — and the only client technology that keeps running after the tab closes.*

### Mechanism

Two things that are almost always discussed as one. The **Cache API** is a store of `Request` → `Response` pairs, async and origin-scoped, drawing on the same quota bucket as §19. It is not the browser's HTTP cache: it ignores `Cache-Control`, it never evicts on its own, and *you* decide what goes in and what comes out. The unit is a whole `Response`, which is why it is the natural home for assets and API payloads and the wrong home for a record you want to query.

A **service worker** is a JavaScript worker, with no DOM and its own lifecycle, that the browser installs against a **scope** (a path prefix) and then puts *in front of the network* for every request in that scope. Its `fetch` event handler receives a `Request` and may answer it however it likes — from the Cache API, from the network, from a synthesized `Response`. That is the whole power: your origin gets a programmable proxy that survives the page.

The lifecycle is where the bugs are. **Install** runs once per new worker byte-sequence and is where you pre-cache. **Activate** runs when the worker takes over and is where you delete old cache versions. Between them sits the trap: a new worker **waits** by default until every tab controlled by the old one closes — a reload is not enough — so users can sit on a stale worker for days. `skipWaiting()` plus `clients.claim()` takes over immediately, and the cost is that a page can find its worker swapped mid-session, serving assets from a build it did not load with. Pick one and say which.

The **strategies** are the vocabulary: *cache-first* for immutable hashed assets, *network-first* for content that must be fresh with an offline fallback, *stale-while-revalidate* for almost everything a UI shows, and *network-only* for anything you would be embarrassed to serve stale. They are the same four policies as `Client-Side System Design` §01 E, applied to `Response` objects instead of query results.

### Reach for it when

- The app must do something useful with no network — an offline shell, the last-synced view, a queued action.
- You are shipping an installable PWA, where a service worker is a requirement rather than a choice.
- You want **Background Sync**: a mutation queued while offline and replayed by the browser after the tab is gone, which is the only way to finish work the user has navigated away from.
- You need Web Push received on the client — the push event is delivered to a service worker, which is the client half of §15.
- Precise control over asset freshness that `Cache-Control` alone cannot express.

### Avoid / careful when

- **Caching anything user-specific without keying by user**, which is how one account sees another's data after a logout on a shared machine.
- Caching the HTML shell cache-first without a version strategy — the classic "users are stuck on last month's build and clearing the cache is the only fix".
- Treating it as a data store. It stores responses; queryable records are §19.
- Forgetting it shares §19's origin quota — an aggressive precache can evict the database.
- Debugging without checking the update lifecycle first. Most "my fix didn't ship" reports are a waiting worker.

**Numbers to anchor**

| | |
|---|---|
| Unit | whole `Request` → `Response` |
| Capacity | shared origin quota (§19) |
| Access | async, from page or worker |
| Scope | path prefix, HTTPS only |
| Update default | waits for all tabs to close |
| Eviction | never automatic; you version |

### CAP / consistency

Not a database, so the equivalent question is the **freshness contract**, and it is *whatever your fetch handler says it is* — which makes this the one client technology where staleness is entirely your bug rather than the platform's. Nothing expires on its own; a response cached in January is served in June unless you deleted it. Layer on the update lifecycle and you get two versions of the same app potentially running in two tabs. The design consequence is that **every cache needs a name with a version in it, and `activate` must delete the others** — versioning is not an optimization here, it is the only correctness mechanism the API offers.

### Interview line

A service worker is a programmable proxy for my own origin, and the Cache API is the response store it answers from — together they're the only way to serve something useful with no network. I'd version every cache name and delete the old ones on `activate`, because nothing in the Cache API expires on its own, so staleness is entirely mine to cause. The thing I'd flag early is the update lifecycle: a new worker waits until every controlled tab closes, so a reload doesn't ship your fix, and if I call `skipWaiting` to fix that I'm accepting that a live page can get its worker swapped underneath it. And I'd keep it to responses — anything I need to query goes to IndexedDB, which shares the same origin quota.

### Pushback / when it flips

**Most apps should not ship a service worker.** It is the one client technology that can break your site for returning users in a way a deploy cannot fix, because the broken thing is the code that decides whether to fetch new code. If the requirement is "fast repeat loads," a CDN and sensible `Cache-Control` do that with no lifecycle to get wrong. It earns its risk when the requirement is genuinely *offline* — usable with no network — or *background* work that must outlive the tab, and those are the two flags to listen for before reaching for it.

---

## 21 · OPFS & File System Access

*Two APIs with a shared vocabulary and opposite tradeoffs: one is a private, quota-managed, genuinely fast file system for your origin; the other hands you a durable handle to the user's real file. OPFS is the reason SQLite runs in a browser.*

### Mechanism

The **Origin Private File System** is a file system the browser gives your origin, invisible to the user, with no picker and no permission prompt, drawing on the same quota bucket as §19 and §20. You get directory and file handles, and you read and write bytes. It is faster than IndexedDB for large sequential I/O because there is no structured-clone step and no transaction machinery — you are writing bytes to a file.

Its headline feature is `createSyncAccessHandle()`, which returns **synchronous** `read` and `write` methods and is available **only inside a dedicated worker**. That combination looks like a step backwards until you see what it unlocks: a synchronous C API compiled to WebAssembly needs a synchronous byte store, and this is the only one the web platform offers. It is precisely why **SQLite-in-WASM works**, and why "we ran a real relational database in the browser" stopped being a stunt. The worker-only restriction is the safety mechanism — synchronous file I/O on the main thread would be a jank machine, so the platform simply does not offer it there.

The **File System Access API** shares the handle vocabulary and inverts every property. `showOpenFilePicker()` and `showSaveFilePicker()` require a user gesture, prompt for permission, and return a handle to a **real file on the user's disk** — the one they can see in Finder. Handles are serializable into IndexedDB, so an editor can offer "reopen last project" and write back to the original file, subject to re-granting permission. There is no quota, because it is the user's disk; there is friction, because it is the user's disk. Browser support is materially narrower than OPFS.

### The two file systems — the distinction to say

| | OPFS | File System Access |
|---|---|---|
| Whose file | yours, origin-private | the user's, on their disk |
| Picker / prompt | none | required, needs a gesture |
| Quota | shared origin bucket | none — real disk |
| Sync access | yes, in a worker | no |
| Survives eviction | no | yes — it is their file |
| Use for | SQLite-WASM, scratch, large caches | open/save real documents |

The one-liner: **OPFS is storage that happens to look like files; File System Access is files that happen to be reachable from a web page.**

### Reach for it when

- You are running SQLite-in-WASM or any WASM workload that expects a synchronous file interface.
- The data is genuinely file-shaped and large — video segments, a downloaded model, a scratch buffer — and IndexedDB's structured clone is pure overhead.
- You need append-heavy or random-access writes rather than whole-record replacement.
- **File System Access specifically:** the product is an editor and the user expects Open and Save to touch their real files, with "reopen last project" surviving a reload.

### Avoid / careful when

- Expecting `createSyncAccessHandle()` on the main thread. Dedicated worker only, by design.
- Reaching for OPFS when the access pattern is keyed records — that is §19, and you will end up reimplementing an index.
- Assuming durability. OPFS is in the same origin bucket as §19 and evicts with it, all-or-nothing; only File System Access escapes that, because the file is the user's.
- Counting on File System Access in Safari or Firefox, where support lags well behind OPFS.

**Numbers to anchor**

| | |
|---|---|
| OPFS capacity | shared origin quota (§19) |
| OPFS sync access | dedicated worker only |
| Sequential I/O | faster than IndexedDB |
| FSA quota | none — the user's disk |
| FSA gesture | required, re-prompts |
| Handle persistence | serializable into IndexedDB |

### CAP / consistency

Neither is a database, so the equivalent is the **durability contract**, and the two answers are opposite — which is the whole reason to know both. OPFS inherits §19's eviction exactly: best-effort, all-or-nothing per origin, upgradable with `persist()`. A File System Access handle points at a file the browser does not own and cannot evict, so it is as durable as the user's disk — but the *permission* is not, and a handle restored from IndexedDB may need re-granting. The design consequence: OPFS for anything you can rebuild, File System Access for anything the user would be upset to lose.

### Interview line

OPFS is an origin-private file system with one property nothing else on the platform has — `createSyncAccessHandle` gives you synchronous reads and writes inside a dedicated worker, which is exactly what a synchronous C API compiled to WASM needs, and it's why SQLite-in-WASM works at all. I'd reach for it when the data is file-shaped and large enough that IndexedDB's structured clone is pure overhead. File System Access is the opposite tool despite the shared vocabulary: it hands me a handle to the user's real file, so there's no quota and no eviction but there is a permission prompt, and I'd use it when the product is an editor and Save is supposed to mean their file.

### Pushback / when it flips

**OPFS is not the upgrade from IndexedDB; it's a different shape.** The moment you need to look something up by a field, you have chosen to write your own index, and IndexedDB already has one. It flips decisively only for WASM workloads that demand synchronous bytes, and for genuinely large sequential data. The other flip worth naming: if you are reaching for SQLite-WASM over OPFS to get relational queries, price the WASM payload and the worker plumbing against just asking the server — a round trip is often cheaper than a megabyte of database engine, and the offline requirement is what decides it.

---

## 22 · Polling & long polling

*Ordinary HTTP requests used to simulate push. Dismissed too quickly in interviews — long polling has one genuinely hard part, and it is the same part every push transport above it also has to solve.*

### Mechanism

**Short polling** is a timer that issues a request on an interval. That is the whole mechanism, and its properties follow arithmetically: average detection latency is half the interval, request volume is *clients ÷ interval* regardless of whether anything changed, and every request pays full HTTP overhead — headers, cookies (§18), TLS resumption — to usually learn nothing.

**Long polling** inverts it. The client issues a request and the **server holds it open** until either something happens or a timeout fires; the client immediately issues another. Latency drops to roughly the server's notification latency, and idle cost drops to one held connection per client instead of a request storm.

The hard part is **the gap**. Between the moment a long poll returns and the moment the client's next request arrives, the client is not listening — and anything the server emits in that window is gone. The fix is the one idea worth taking from this entry, because everything above it reuses it: **the server keeps a per-client cursor, the client sends it back, and the server replays from it.** `GET /events?since=1043` returns everything after 1043 or blocks until there is something. That is not an optimization; without it the transport silently drops messages under exactly the load where it matters. And it is precisely what SSE's `Last-Event-ID` (§23) standardizes and what a WebSocket (§24) makes you build yourself.

Two operational facts shape the timeout. **Proxies and load balancers kill idle connections**, commonly around 60 seconds, so the server's hold must expire *below* that threshold and return empty rather than let an intermediary sever it. And under HTTP/1.1 a held request **consumes one of the ~6 connections per origin** the browser allows, so two long polls plus a few asset loads can stall the page — a constraint HTTP/2 multiplexing removes.

For the reverse direction — a small payload the client must send as the page is unloading, such as a final analytics event — `navigator.sendBeacon()` or `fetch(url, {keepalive: true})` hands the request to the browser to complete after the document is gone. An ordinary `fetch` in `unload` is cancelled.

### Reach for it when

- The update rate is genuinely low and seconds of latency are fine — short polling, and it is often the correct engineering answer.
- You need push semantics through infrastructure that will not carry anything else: a corporate proxy, an ancient gateway, a platform with no socket support.
- The client count is small enough that a held connection each is not a capacity question.
- You want a fallback tier beneath a real push transport, with the same cursor contract so the application code does not change.

### Avoid / careful when

- Polling something with a real push channel available — the over-engineering tell in reverse, and just as visible.
- Long polling without a cursor. The gap is real and the resulting bug is intermittent and awful to diagnose.
- Setting the hold longer than the shortest timeout in the path. You will get severed connections you blame on the client.
- Forgetting each held request carries full cookie headers (§18), which at scale is real upload bandwidth for zero payload.
- Retrying instantly on error. Exponential backoff with jitter, or a server hiccup becomes a thundering herd.

**Numbers to anchor**

| | |
|---|---|
| Short-poll latency | interval ÷ 2 |
| Short-poll load | clients ÷ interval |
| Long-poll hold | ~25–50 s, under LB timeout |
| Typical LB idle timeout | ~60 s |
| HTTP/1.1 connections | ~6 per origin |

### CAP / consistency

Not a store, so the equivalent question is the **delivery contract**. Short polling gives you *at-most-once observation of state*, not of events — you see whatever is current when you ask, and anything that happened and reverted between polls never existed as far as the client is concerned. Long polling with a cursor gives you **at-least-once, ordered, resumable** delivery, which is a genuinely strong contract; without the cursor it silently degrades to lossy. The design consequence: if the client needs *events* rather than *current state*, you need the cursor no matter which transport you end up on.

### Interview line

I'd start at polling and only climb if the requirement forces it, because an interval and a timestamp is a lot less to operate than a socket. If latency matters I'd long-poll, and the thing I'd build first is a cursor — the server holds the request open, returns with an event id, and the client sends it back on the next request — because otherwise anything emitted between the response and the next request is silently dropped, and that's the bug you find in production. I'd size the hold under the load balancer's idle timeout, usually somewhere around thirty seconds, and back off with jitter on errors so a blip doesn't turn into a herd.

### Pushback / when it flips

**Polling is the right answer more often than its reputation suggests** — if the data changes every few minutes, a 30-second poll is a `setInterval` and a cache header, against a socket tier with reconnect, heartbeat, auth refresh, and resubscribe. It flips when *per-client* cost stops being the constraint and *aggregate* cost starts: at a hundred thousand clients, a 5-second poll is 20k req/s of mostly-empty responses, and that is the number that justifies the climb. The other flip is direction — the moment the client needs to send continuously rather than receive, polling stops being a simplification and becomes a workaround, which is §24.

---

## 23 · Server-Sent Events

*A long-lived HTTP response that never ends, framed as text events, with reconnection and resumption in the browser rather than in your code. One direction only — which is the entire point and the entire limit.*

### Mechanism

The server responds `Content-Type: text/event-stream` and simply **does not close the response body**, writing UTF-8 text frames as things happen. It is an ordinary HTTP response that goes on forever, which is why it inherits every HTTP property for free: your auth, your proxies, your load balancers, your compression negotiation, and your observability all work with no special case.

The framing is deliberately trivial — lines of `field: value`, with a blank line terminating an event:

```
id: 1043
event: delta
data: {"text":"Hel"}

data: partial
data: continued
```

`data:` accumulates across repeated lines and is joined with newlines. `event:` names the event so `addEventListener('delta', …)` works. `retry:` sets the reconnect delay in milliseconds. And `id:` is the mechanism that matters: the browser remembers the last id it saw, and **on reconnect it sends it back automatically as the `Last-Event-ID` request header**. That is §22's cursor, standardized and handled for you — which means resumption is something you implement on the server and get for free on the client.

`EventSource` is where the constraint lives, because **the browser owns the request**. You hand it a URL; you do not get to set headers, you do not get to send a body, and the method is always GET. So authentication must be a cookie (§18) or a query parameter, and anything with a request payload — a chat prompt, for instance — does not fit the API at all. The alternative is to make the same HTTP request yourself with `fetch`, read `response.body` as a stream, and parse the framing above by hand; you regain headers, POST, and `AbortController`, and you give up automatic reconnect and `Last-Event-ID`, which you then reimplement. `OpenAI Screen` §05 B is where that decision gets made for a streaming model response, along with the production pathologies — buffering proxies, compression flush boundaries, and connection limits — which that section covers in depth and this one deliberately does not repeat.

Reconnection is automatic: on a dropped connection `EventSource` waits `retry` milliseconds and reopens, forever, without your involvement. The one way to stop it is an HTTP error status or an explicit `close()`, so a server that wants the client to give up must say so with a status code rather than by hanging up.

### Reach for it when

- Data flows **server to client only** and is text: notifications, progress, live counters, model tokens, log tails.
- You want reconnection and gap-free resumption without writing either — the `id:`/`Last-Event-ID` pair is the cheapest resumable stream on the platform.
- The stream must traverse infrastructure you do not control, where an HTTP response passes and a protocol upgrade may not.
- You want the stream to be an ordinary observable HTTP request in your existing logging and tracing.

### Avoid / careful when

- The client needs to send continuously. That is §24, and forcing it here means a socket in one direction and POSTs in the other, which is sometimes right and should be a stated decision.
- The payload is binary. The format is UTF-8 text; base64 costs you a third more bytes.
- Auth is a bearer header. `EventSource` cannot set one — cookie, query param, or hand-rolled `fetch`.
- You need the connection to *stop* retrying on failure. Return a 4xx; otherwise it reconnects forever.
- You forget the server side of resumption. `Last-Event-ID` arrives whether or not you honour it, and ignoring it turns a reconnect into a silent gap.

**Numbers to anchor**

| | |
|---|---|
| Direction | server → client only |
| Payload | UTF-8 text |
| Framing | `id` / `event` / `data` / `retry` |
| Resumption | `Last-Event-ID` header, automatic |
| Reconnect | automatic, `retry` ms |
| HTTP/1.1 connections | ~6 per origin; HTTP/2 multiplexes |

### CAP / consistency

Not a store, so the equivalent is the **delivery contract**: *ordered within a connection, at-most-once by default, and at-least-once with resumption if — and only if — the server emits `id:` and honours `Last-Event-ID` on reconnect.* Without ids, every reconnection is a silent gap of unknown size, and the client cannot even detect it. With them, the client's resumption is automatic and the server's replay buffer becomes the design question: how far back can you serve, and what happens when a client asks for an id older than the buffer. The design consequence: **emit `id:` from day one** — it costs nothing when you do not need it and cannot be retrofitted onto a stream that is already in production.

### Interview line

SSE is a response that never ends: `text/event-stream`, text frames, one direction. I reach for it whenever the data only flows server to client, because it's plain HTTP so my auth, proxies, and tracing all work unchanged, and because the browser gives me reconnect and resumption for free — the server emits an `id` on each event and gets it back as `Last-Event-ID` on reconnect. The limit I'd name immediately is that `EventSource` owns the request, so no custom headers, no body, GET only; if I need to POST a payload I make the request with `fetch` and parse the framing myself, and I've accepted that I now own reconnect too.

### Pushback / when it flips

**The reflexive objection — "SSE is limited to six connections" — is an HTTP/1.1 fact people keep quoting into an HTTP/2 world**, where streams multiplex over one connection and the limit is effectively gone. The real flip is direction: the moment the client must send continuously — cursors, presence, an interrupt mid-generation — you are paying for a socket anyway and should just have one (§24). The subtler flip is toward hand-rolled `fetch` streaming, and it is not about capability but about *who owns reconnect*: `EventSource` gives you a good reconnect you cannot customize, and the moment you need backoff you control or an auth refresh mid-stream, that gift becomes a constraint.

---

## 24 · WebSocket

*One TCP connection, upgraded out of HTTP, carrying framed messages in both directions for as long as it lasts. You get true bidirectionality and you inherit every problem HTTP was solving on your behalf.*

### Mechanism

A WebSocket begins as an ordinary HTTP GET carrying `Upgrade: websocket` and a `Sec-WebSocket-Key`. The server answers `101 Switching Protocols`, and from that instant the bytes on that TCP connection are no longer HTTP — they are RFC 6455 frames. That handshake is why a WebSocket can traverse an HTTP infrastructure at all, and also why some infrastructure refuses it: an intermediary that does not understand `Upgrade` sees a request that never completes.

After the upgrade the unit is a **message**, delivered whole and in order, as text or binary. Framing handles fragmentation for you, so unlike §22 or §23 you are not parsing a byte stream. What you get is a bidirectional, ordered, message-oriented pipe. What you no longer get is everything HTTP was doing: there is **no status code**, no caching, no content negotiation, no per-request auth, no standard retry, and no resumption. Your load balancer must support sticky, long-lived connections, and a deploy that cycles the socket tier disconnects every client at once.

The protocol gives you exactly one built-in reliability primitive: **ping/pong control frames**, which exist because a TCP connection can be dead for minutes without either end noticing — a NAT table expiring or a phone changing networks produces a socket that is open, writable, and going nowhere. A heartbeat with a response deadline is the only way to detect that, and it is on you to implement.

So the code you own beyond `new WebSocket(url)` is a list worth reciting: **reconnect with exponential backoff and jitter**, **heartbeat with a liveness deadline**, **resubscribe** to whatever the old connection was watching, **auth refresh** for a token that expires mid-connection, and **resumption** — the cursor from §22, which SSE standardized and which here you must design yourself. That list, not the API, is what "we'll use WebSockets" actually commits you to.

Authentication deserves its own sentence: the browser API cannot set headers on the handshake either, so a bearer token goes in a query string (where it lands in logs), in a cookie, or — the usual answer — in a first message immediately after connect, with the server refusing to do anything until it arrives.

### Reach for it when

- The client genuinely sends continuously, not occasionally: cursor position, presence, typing, live collaboration, an interrupt mid-generation.
- Latency in *both* directions matters and a round trip per message is too much overhead.
- You are multiplexing many logical subscriptions over one connection and want to manage that yourself.
- The payload is binary and base64 over a text transport is a real cost.

### Where this is going — WebTransport (know the one-liner)

WebTransport runs over HTTP/3 and QUIC and fixes the two structural limits above. A WebSocket is **one ordered byte stream**, so a large message blocks everything behind it — head-of-line blocking you cannot design around. WebTransport gives you **many independent streams** over one connection plus **unreliable datagrams**, so a dropped position update does not delay a chat message, and it inherits QUIC's connection migration, which means a phone switching from wifi to cellular keeps its session instead of reconnecting.

The one-liner: *WebSockets when you need bidirectional today, WebTransport when head-of-line blocking or connection migration is the actual problem — and I'd check support before committing, because it is not universal yet.* Naming it is worth a sentence; betting a design on it is not.

### Avoid / careful when

- Reaching for it because "real-time." If the client only sends start and stop, §23 gives you more for less.
- Shipping without a heartbeat. A dead-but-open socket is the single most common production symptom.
- Forgetting that a deploy drops every connection simultaneously — reconnect must have jitter or you have built a self-inflicted DDoS.
- Assuming auth persists. The token that opened the connection expires while it is still open.
- Sending a large message on the same socket as latency-sensitive ones; head-of-line blocking is real.

**Numbers to anchor**

| | |
|---|---|
| Handshake | HTTP `101 Switching Protocols` |
| Unit | message, ordered, text or binary |
| Heartbeat | ping/pong, ~30 s typical |
| Server memory | ~10s of KB per connection |
| Head-of-line | one ordered stream |
| Yours to build | reconnect, resubscribe, resume, auth |

### CAP / consistency

Not a store, so the equivalent is the **delivery contract**, and it is *ordered and reliable within one connection, and nothing at all across a reconnect.* The protocol offers no ids, no acknowledgements, and no replay, so every disconnect is a gap of unknown size that the client cannot detect on its own — the failure mode is a UI that looks connected and is quietly missing the last thirty seconds. The design consequence: **application-level sequence numbers and an acknowledgement are not optional on a WebSocket, they are the part SSE gave you for free.** Build the cursor from §22 or accept lossy delivery, and say which.

### Interview line

A WebSocket is an HTTP request that upgrades into a raw framed connection, and after the `101` it's bidirectional, ordered, message-oriented — and no longer HTTP, so I lose status codes, caching, per-request auth, and any standard retry. I'd only reach for it when the client genuinely sends continuously, because what I'm signing up for isn't the API, it's reconnect with jittered backoff, a heartbeat to detect a dead-but-open socket, resubscribe, auth refresh mid-connection, and resumption — which SSE would have given me for free. And I'd add sequence numbers from the start, because the protocol has no replay, so every reconnect is a gap the client can't even detect.

### Pushback / when it flips

**"We'll use WebSockets for real-time" is the most common over-engineering tell on the client**, because it names a transport in answer to a requirement about latency, and most so-called real-time features are one-directional. It flips to SSE the moment you notice the client only sends start and stop. It flips *back* to WebSocket when a design starts accumulating workarounds — an SSE stream plus a POST endpoint plus a second stream for a different subscription is a socket you are paying for in pieces. And at very high connection counts the honest constraint is not the protocol but the connection tier: memory per connection, a deploy strategy that does not drop everyone at once, and stickiness — which is where this stops being a client decision and becomes `Designs → Discord`.

---

## 25 · WebRTC data channel

*Peer-to-peer, and the only transport here where the bytes need not touch your servers. Also the only one where "unreliable and unordered" is a feature you can ask for.*

### Mechanism

WebRTC is usually described as a media stack, but `RTCDataChannel` carries arbitrary application data over the same machinery, and that machinery is the interesting part. The data path is **SCTP over DTLS over UDP** — which is why it can offer what nothing above it can: per-channel choice of **ordered or unordered** and **reliable or unreliable** delivery. A position update that is superseded 40 ms later should not be retransmitted, and this is the only browser transport that will agree to drop it.

Getting a connection established is the cost, and it is entirely about the fact that two browsers are usually behind NATs with no reachable address. **ICE** gathers candidate paths: the host address, a **STUN**-discovered public address, and a **TURN** relay address. The peers exchange SDP offers and answers and their candidates over a **signalling channel you provide** — WebRTC specifies none, so you need a server anyway, usually a WebSocket (§24). They then attempt paths in preference order.

The number that decides the architecture: **roughly 10–20% of peer pairs cannot connect directly** and must fall back to TURN, where a server relays every byte. So "peer-to-peer, so no server cost" is false at the margin, and the marginal case is the expensive one — a TURN relay pays bandwidth for the whole session. Any honest WebRTC design includes TURN capacity as a line item.

Topology is the other decision. Full mesh has each peer connected to every other, which is `n(n−1)/2` connections and stops being viable past a handful of participants; beyond that you route through a server — an **SFU** that forwards streams without decoding them — at which point you have re-introduced the server you were avoiding, deliberately and for good reason.

### Reach for it when

- Latency below what a relay through your server allows, and the extra ~50–150 ms of a server round trip actually matters — competitive gaming, live cursors at high frequency.
- The data should not touch your infrastructure at all, for privacy, cost, or compliance reasons.
- **Unreliable, unordered delivery is genuinely what you want** — the case no other transport on this page serves.
- Direct file transfer between two users, where relaying gigabytes through your servers is the thing you are avoiding.

### Avoid / careful when

- You think it removes server cost. You still run signalling, and you still run TURN for the pairs that cannot connect.
- Participant count grows. Mesh dies quickly; plan the SFU before you need it.
- You need it to work everywhere. Restrictive corporate networks force TURN over TCP/443, which is a relay with extra steps.
- The data must be durable or ordered across a reconnect — there is no resumption story here either, and less standard tooling to build one with.
- You are reaching for it for one-directional server-to-client data, where it is dramatically more machinery than §23.

**Numbers to anchor**

| | |
|---|---|
| Data path | SCTP / DTLS / UDP |
| Delivery | ordered or not, reliable or not |
| TURN fallback | ~10–20% of pairs |
| Mesh limit | ~4–6 peers |
| Signalling | yours to provide |
| Setup | ~100s of ms, ICE negotiation |

### CAP / consistency

Not a store, so the equivalent is the **delivery contract**, and it is the only **configurable** one on this page: per channel you choose ordered or unordered, and reliable or bounded-retransmit. That is real power and it is also a real obligation, because choosing unreliable means the application must be correct when messages are missing — which works for state that is superseded continuously, like a cursor position, and breaks for anything cumulative, like an edit operation. The design consequence: **use unreliable only for state where the next message makes the last one irrelevant**, and put anything cumulative on a reliable channel or a different transport entirely.

### Interview line

A data channel is the one transport where I can ask for unreliable, unordered delivery — SCTP over DTLS over UDP — which is exactly right for something like a live cursor, where retransmitting a position that's already stale is worse than dropping it. What I'd flag straight away is that peer-to-peer doesn't mean serverless: I still need a signalling channel to exchange offers and ICE candidates, and something like ten to twenty percent of peer pairs can't connect directly and fall back to a TURN relay, which pays bandwidth for the whole session. So I'd budget TURN as real infrastructure, and I'd plan the move from mesh to an SFU before participant count forces it.

### Pushback / when it flips

**"Peer-to-peer, so it doesn't cost us anything" is the claim to attack, including in your own answer** — signalling is a server, TURN is a server with a bandwidth bill, and the fraction of users who need TURN skews toward exactly the corporate and mobile networks your enterprise customers are on. It flips back to a plain server relay sooner than people expect: past a handful of participants an SFU is simpler *and* cheaper than mesh, and once you are running an SFU the peer-to-peer argument has already been conceded. The genuine, non-negotiable case is the unreliable channel — if you need the platform to *drop* stale data rather than retransmit it, nothing else here will do it.

---

## 26 · Web Worker / SharedWorker

*A second JavaScript thread with its own heap and no DOM. The fix for main-thread work — provided the data is cheap to move, because by default every message is a deep copy.*

### Mechanism

A worker is a **separate JavaScript realm on its own thread**: its own global scope, its own heap, its own event loop. It has no `document`, no DOM, and no access to the page's variables. The only channel is `postMessage`, and understanding what `postMessage` *costs* is most of what this entry is for.

Messages are passed by **structured clone**, which is a genuine deep copy. It handles objects, arrays, `Date`, `Map`, `Set`, `RegExp`, `ArrayBuffer`, and cyclic references — and it cannot handle functions, DOM nodes, class identity, or anything with a prototype you care about. Because it is a copy, moving a 50 MB object to a worker allocates 50 MB on the other side **and blocks both threads while it serializes and deserializes**. The failure this produces is genuinely funny and genuinely common: you move expensive work off the main thread and the page gets *janker*, because the transfer costs more than the computation saved.

Two escapes. **Transferables** — `postMessage(buf, [buf])` — move an `ArrayBuffer` by handing over ownership rather than copying: O(1), and the sender's reference becomes unusable, which is the point. **`SharedArrayBuffer`** gives both threads a view of the same memory with no message at all, and it requires the page to be **cross-origin isolated** via `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` — a Spectre mitigation whose practical effect is that turning it on can break your third-party embeds, so it is a page-level decision rather than a local one.

A **dedicated worker** belongs to one page and dies with it. A **SharedWorker** is shared by every tab of the same origin — one instance, reached through a `port` per tab — which makes it the natural place to own a single WebSocket for the whole application instead of one per tab. Its practical limitation is support and debuggability, and the fact that a service worker (§20) can often do the same job with a better story.

The rule that decides everything: **the main thread is the only one that can paint.** Work belongs off it when it would otherwise block a frame — parsing megabytes of JSON, diffing a large document, image processing, running WASM. Work belongs on it when the data transfer would cost more than the work.

### Reach for it when

- A computation blocks a frame: large parse, diff, compression, image or audio processing, cryptography.
- You are running WASM that expects a thread of its own — and note that OPFS's synchronous handle (§21) is worker-only, so a SQLite-WASM setup requires this.
- The data is binary and transferable, so the move is O(1) and the argument is unambiguous.
- **SharedWorker specifically:** several tabs should share one connection or one cache rather than each opening their own.

### Avoid / careful when

- The payload is large and non-transferable. Measure the clone; it is frequently the whole cost.
- Chatty designs. Many small messages pay per-message overhead and scheduling latency; batch.
- Expecting DOM access. There is none, so a worker can compute a layout but never apply it.
- Assuming class instances survive. Structured clone preserves data, not prototypes — they arrive as plain objects.
- Turning on cross-origin isolation casually. It is a page-wide policy change that can break embeds.

**Numbers to anchor**

| | |
|---|---|
| Transfer | structured clone = deep copy |
| Transferable `ArrayBuffer` | O(1), ownership moves |
| `SharedArrayBuffer` | needs COOP + COEP |
| Frame budget | ~16 ms at 60 fps |
| Dedicated worker | one page, dies with it |
| SharedWorker | one per origin, port per tab |

### CAP / consistency

Not a store, so the equivalent is the **memory-model contract**: *no shared mutable state by default, message-ordered per channel.* Two threads cannot race on the same object because they do not have the same object — the copy is the isolation. Messages on one port arrive in order; messages across different ports have no ordering relationship at all. Opt into `SharedArrayBuffer` and you have opted into genuine shared-memory concurrency, with `Atomics` and every data race that implies, in JavaScript. The design consequence: **keep the copy semantics unless profiling forces you off them**, because they are the reason worker code is not concurrent code.

### Interview line

A worker is a separate realm on its own thread with no DOM, and the thing I'd say before reaching for one is that `postMessage` is a structured clone — a deep copy — so moving a big object costs the copy on both sides and can easily be slower than the work I was trying to move. If the data is an `ArrayBuffer` I'd transfer it instead, which is O(1) because ownership moves rather than the bytes. I'd use one when something genuinely blocks a frame — a large parse, a diff, WASM — and I'd reach for a SharedWorker when several tabs should share one connection instead of each opening their own, though a service worker often ends up being the better place for that.

### Pushback / when it flips

**"Move it to a worker" is not a performance strategy, it is a relocation** — and it only pays when the work is large relative to the transfer. The first move is almost always cheaper: do less work, do it incrementally across frames, or do it on the server. A worker earns its complexity when the computation is genuinely CPU-bound, genuinely large, and the data is either small or transferable. And SharedWorker specifically flips toward §20: if the reason you want it is one connection across tabs, a service worker or the lock in §27 usually gets you there with better tooling.

---

## 27 · BroadcastChannel & cross-tab coordination

*One browser is N tabs, and every client-side resource is shared between them. This is the entry that answers "who owns the socket" — and the primitive it turns on appears nowhere else in these guides.*

### Mechanism

Every tab of an origin runs the same application against the **same storage bucket, the same server, and the same user**, with no coordination unless you build it. Open three tabs of a chat app and you have three WebSockets, three sync loops, and three writers to one IndexedDB.

**`BroadcastChannel`** is the messaging half. `new BroadcastChannel('sync')` in each tab, and `postMessage` on one delivers a structured clone to every *other* context on the same origin subscribed to that name — other tabs, iframes, and workers, but never the sender. It is fire-and-forget: no history, no acknowledgement, no delivery guarantee to a tab that is not listening yet. It replaces the older trick of writing to `localStorage` purely to trigger the `storage` event in other tabs (§17), which worked, was synchronous, was limited to strings, and is now legacy — knowing it is why `BroadcastChannel` exists is the useful part.

**The Web Locks API is the coordination half, and it is the primitive worth memorizing:**

```js
navigator.locks.request('socket-owner', {mode: 'exclusive'}, async (lock) => {
  openTheSocket()
  await neverResolves          // held for as long as this tab lives
})
```

The browser grants the named lock to exactly one context at a time across the whole origin, queues the rest, and — the property that makes it correct rather than merely convenient — **releases it automatically when the holding context goes away**, including on a crash or a force-quit. A leader election built on `localStorage` timestamps has to guess at a heartbeat timeout and always has a window where the leader is dead and nobody knows. This has none, because the browser owns the lifetime.

So the pattern for "one tab owns the socket" is: every tab requests the lock, exactly one gets it and opens the connection, that tab broadcasts what arrives over a `BroadcastChannel`, and every other tab renders from the broadcast. When the leader closes, the lock releases, and the next tab in the queue takes over and reconnects — with no timeout to tune. `{ifAvailable: true}` lets a tab test for leadership without queueing, and `{mode: 'shared'}` gives you a read-write lock when you need many readers and one writer.

### Reach for it when

- A resource should exist once per browser rather than once per tab: a WebSocket, a poll loop, a background sync, a heavy timer.
- One tab writes to IndexedDB and the others must invalidate or re-render — broadcast the change rather than polling the database.
- Auth state changes and every tab must react: logging out in one tab should not leave five authenticated tabs open.
- A migration or a schema upgrade must happen exactly once (§19's `versionchange`), and the other tabs must stand down.

### Avoid / careful when

- Treating `BroadcastChannel` as reliable. No delivery guarantee, no replay, and the sender never receives its own message — a tab that opens later has missed everything, so it must read current state from the store rather than expect to be told.
- Broadcasting large payloads. It is a structured clone per receiving context, so N tabs means N copies (§26).
- Building leader election on `localStorage` heartbeats when Web Locks exists. The dead-leader window is a real bug and the lock does not have one.
- Forgetting `BroadcastChannel` is origin-scoped, so it does not reach a different subdomain.
- Assuming leadership is stable. Tabs close, get discarded under memory pressure, and get frozen in the background — leadership must be reacquirable, and the reconnect path is the normal path.

**Numbers to anchor**

| | |
|---|---|
| Scope | one origin, all contexts |
| `BroadcastChannel` | fire-and-forget, sender excluded |
| Payload | structured clone, per receiver |
| Web Locks | exclusive or shared, queued |
| Lock release | automatic on context loss |
| Legacy signal | `storage` event, other tabs |

### CAP / consistency

Not a store, so the equivalent is a **coordination contract**, and it splits cleanly. `BroadcastChannel` gives you *at-most-once, unordered across senders, no replay* — a genuinely weak channel, and the right posture is to treat every message as a **hint to go re-read the store** rather than as the data itself. Web Locks gives you the strong half: mutual exclusion across the origin with **automatic release on context loss**, which is exactly the guarantee a lease with a timeout is trying to approximate and cannot. The design consequence is a pairing worth stating: **locks for who acts, broadcast for telling everyone to re-read, and the store for what is true.**

### Interview line

One browser is N tabs, so before I open a socket I'd ask who owns it — three tabs means three connections, three sync loops, and three writers to the same database. The primitive I'd reach for is `navigator.locks.request` with an exclusive lock held for the lifetime of the tab: the browser grants it to exactly one context and releases it automatically if that context dies, so leader election has no heartbeat to tune and no dead-leader window. That tab owns the connection and rebroadcasts over a `BroadcastChannel`, and the others render from it. I'd treat the broadcast as a hint to go re-read IndexedDB rather than as the data, because it has no replay and a tab that opened late has missed everything.

### Pushback / when it flips

**Most apps genuinely do not need this, and the tell that you do is a bug report rather than a design review** — duplicate notifications, a logout that only took in one tab, a counter that double-increments. Until then, N sockets is a real but usually affordable cost, and coordination is complexity you have not yet earned. It flips hard when *per-connection* cost is the server's problem rather than the client's: at scale, users with eight tabs open are a meaningful slice of your connection tier, and one-socket-per-browser stops being a nicety. And it flips toward §20 when the work must continue with **no** tab open — a lock cannot help you there, because there is no context to hold it; that is Background Sync.

---

## 28 · Client-side decision matrix

*Collapse the eleven browser entries into one glance. Match the need on the left to the default pick; the "because" is the one-line justification.*

| Need | Default pick | Because |
|---|---|---|
| A flag you need before first paint | `localStorage` | synchronous is the feature here, and the value is tiny |
| Per-tab scratch state | `sessionStorage` | dies with the tab, which is the requirement |
| Server must know who this is on a plain navigation | Cookie | the only store attached to requests automatically |
| Long-lived auth credential | `HttpOnly` `Secure` `SameSite` cookie | out of JavaScript's reach; pair with an in-memory access token |
| Anything you would call data, surviving reload | IndexedDB | async, transactional, indexed, hundreds of MB |
| A queue of mutations to replay when online | IndexedDB outbox | durable and ordered; losing it loses the user's work |
| Serve something useful with no network | Service Worker + Cache API | the only way to answer a request the network can't |
| Work that must outlive the tab | Service Worker + Background Sync | no page context is required to run it |
| SQLite-in-WASM, or large sequential bytes | OPFS | synchronous access handles, worker-only, no clone tax |
| Open and save the user's real files | File System Access | a handle to their disk; no quota, but a permission prompt |
| Rare updates, seconds of latency tolerable | Polling | an interval and a cursor; nothing to operate |
| Server → client stream, text, resumable | SSE | plain HTTP, and `Last-Event-ID` gives resumption free |
| Client sends continuously, both directions | WebSocket | true bidirectionality; you own reconnect and resumption |
| Sub-relay latency, or drop-don't-retransmit | WebRTC data channel | unreliable unordered delivery, which nothing else offers |
| Work that blocks a frame | Web Worker | a second thread — if the data is small or transferable |
| One resource per browser, not per tab | Web Locks + BroadcastChannel | exclusive lock, auto-released when the holder dies |

### The meta-rule

Most clients are **`fetch` plus one store plus at most one push channel**: `fetch` for everything the user asks for, IndexedDB for anything that must survive a reload, and a single stream — usually SSE — for anything the server needs to volunteer. Reach past that only when a *named requirement* forces it: genuine offline (§20), a synchronous WASM byte store (§21), continuous client-to-server data (§24), unreliable delivery (§25), a frame-blocking computation (§26), or a resource that must be singular across tabs (§27). And price the climb honestly — every rung above `fetch` is a connection you must reopen, reauthenticate, and resubscribe, and that reconnect path, not the transport, is where the design work actually is.

---

## Cross-cutting principles

*Nine rules that reappear on every page above — five on the server, four on the client. If you only carry one thing into the room, carry these.*

**On the server**

- **Idempotency is non-negotiable** anywhere delivery is at-least-once (Kafka, queues, orchestrator activities, Flink sinks, retried writes).
- **One source of truth**; everything else (cache, search index, vector store, analytics store, denormalized copy) is derived and must be rebuildable + reconciled.
- **Reads tolerate staleness; writes must be correct** — the asymmetry behind CDNs, replicas, caches, and search indexes.
- **Move a guarantee out of the database only when arrival rate makes the DB physically unable to provide it** — the same rule for sharding (~15–50k writes/s to one table), Redis holds, and counter offloading (~500–1k/s to one hot row).
- **Consensus (ZooKeeper/etcd) for correctness-critical coordination; a lease (Redis) when an occasional double is tolerable** — pick the strength of guarantee the failure demands.

**On the client**

- **The client is not a trust boundary and not a durable store.** Anything on the device is readable by the user, editable by the user, and evictable by the browser — so client storage is a cache of server truth plus an outbox of intent, never the only copy. The mirror of "one source of truth," seen from the other end.
- **The main thread is the shared resource.** Every synchronous call on it — `localStorage`, a large `JSON.parse`, a structured clone of a big object — is paid in dropped frames and input latency. The fix is always one of three: move it off, make it async, or make it smaller.
- **Climb the transport ladder only as far as the requirement forces, and price the reconnect.** Every rung above `fetch` is a connection you must reopen, reauthenticate, and resubscribe — the transport is the easy part and the resumption is the design. `Client-Side System Design` §01 C is the ladder itself.
- **One browser is N tabs.** Every client-side resource — a socket, a lock, a sync loop, the origin's storage quota — is shared across tabs of the same origin, so decide who owns it before you open it.
