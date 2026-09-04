# Data Modeling Under Pressure

> The five minutes of a design round where you write down tables. Most candidates list nouns and
> wait to be asked; the staff bar is a model *derived from the reads and writes, defended by its
> invariants, and priced in rows*, produced fast enough that the interviewer's questions land on
> answers you already wrote. This guide is the procedure for producing that model, the notation to
> write it in, the four stores as modeling rules rather than mechanisms, the ten questions the model
> must survive, ten worked models, and the rep that makes it automatic.

---

## 01 — What a data model is graded on

### A. THE CLAIM

A data model is not a list of entities. **It is the list of reads and writes, made physical.** Every
table exists to serve a named access pattern; every key was chosen so that the hottest pattern is a
single-partition operation; every duplicated field has an owner and a repair job; every store was
picked against a rejected alternative; and every unbounded table has a plan for year three. If the
model can answer "which query does this index serve?" and "what's in the transaction?" and "why not
DynamoDB?" *before* the interviewer asks, it holds. If it answers them only when asked, it reads as
improvisation, however correct.

The failure the interviewer is listening for is the gap between the boxes on the whiteboard and the
rows in the database. "There's a users table and an orders table" is where most candidates stop; the
follow-ups — partition key, concurrency, the second access pattern, the index cost — are where the
round is actually decided.

### B. THE SIX ARTIFACTS, IN ORDER

This is the whole deliverable. Produce them in this order, out loud, in roughly this time.

| # | Artifact | Time | What it looks like on the board |
|---|---|---|---|
| 1 | **Entities and the aggregate root** | 30s | 4–7 nouns; one circled as the transaction boundary |
| 2 | **Access patterns** | 60s | 5–8 lines of `verb ENTITY by KEY, ordered by X`, each tagged hot/cold with a rate |
| 3 | **Tables in notation** | 120s | One block per table: PK, 5–8 columns, the index per hot read, a row estimate |
| 4 | **Invariants and transaction boundaries** | 45s | The one thing that cannot be eventually consistent, and the mechanism that enforces it |
| 5 | **Store per component, with the loser** | 45s | One row per stateful thing: pattern, durability, product, the alternative you rejected |
| 6 | **The big table in year three** | 30s | Which table grows without bound, its partition unit, retention, hot-key risk |

Five and a half minutes. In an interview you will do it in pieces — entities during requirements,
tables when you draw the storage box, the store table as the deep dive opens — but the six artifacts
are the same, and **the reason to practice them as one block is so that none of them gets skipped
when the pieces are spread across forty-five minutes.**

### C. WHERE THIS GUIDE SITS

Three resources on this site touch storage. They do different jobs.

| Resource | Job | Read it when |
|---|---|---|
| **This guide** | The procedure, the notation, the pressure questions, the reps | Practicing; the week before a loop |
| `Technology Choices` | Mechanism, numbers, CAP posture, and "when it flips" per store | You need the trigger numbers or the durability layers cold |
| The design pages, §12 | Full derivations of one problem's storage table, with the disagreements argued out | You want to see the compressed model here expanded to its reasoning |

The trigger numbers used below — one Postgres primary at ~5–15k writes/s, shard at ~15–50k, LSM
past ~50k, a hot row at ~500–1k serialized updates/s, a Cassandra partition at ~100MB — are the
ones `Technology Choices` anchors. They are repeated here only where a decision turns on them.

---

## 02 — The six-step procedure

Each step: the question to ask yourself, what to write, and the miss that costs points.

### A. ENTITIES AND THE AGGREGATE ROOT

**Ask:** what are the nouns, and which one bounds a transaction?

Write 4–7 entities. Then circle the **aggregate root** — the entity inside which writes must be
atomic and outside which they may be eventual. For an order system it is the order (order + lines +
payment ref commit together; inventory does not). For chat it is the conversation. For ticketing it
is the event. **The root becomes the partition key by default**, because a partition is the unit
inside which a store gives you cheap atomicity.

The miss: listing every noun in the product. Seven is the ceiling; the eighth is a column.

### B. ACCESS PATTERNS — THE MODEL IS THIS LIST

**Ask:** what does the system read and write, by what key, in what order, how often?

Write one line per pattern in a fixed shape:

```text
R  timeline for USER            by user_id, newest first, page 50     hot   300k/s
W  post TWEET                   by tweet_id                           hot   6k/s, 3M/s fanout
R  recent tweets by AUTHOR      by author_id, newest first, page 20   warm  20k/s
R  follower list for USER       by user_id, all                       cold  fanout only
```

`R`/`W`, the entity in caps, the key, the order, the page size, hot/warm/cold, and a rate. **The
order column is what decides the sort key; the page size is what decides pagination; the rate is
what decides the store.** A pattern without a key is a scan, and naming it as one is the point.

The miss: writing the API instead. `GET /users/{id}/timeline` says nothing about ordering or volume.
The access pattern list is the API translated into what the storage engine sees.

### C. TABLES IN NOTATION

**Ask:** for each pattern, which table and which key serve it in one operation?

Write one block per table in the notation from §03. Every block carries: the store, the primary key
(and partition/sort split where the store has one), 5–8 columns including `status` where there is a
lifecycle and `version` where there is contention, **one index per hot read with the read named
beside it**, and a row estimate.

Two tables that answer the same question in the same block are one table. One table that answers two
questions with two different keys is usually two tables — the second is a projection, and saying
"this is a derived copy, rebuilt from the first" is what stops it looking like a mistake.

The miss: columns that carry no decision. `first_name`, `last_name`, `email` cost you thirty seconds
and prove nothing. `status enum(...)`, `version`, `idempotency_key`, `expires_at`, `tenant_id` each
prove something.

### D. INVARIANTS AND TRANSACTION BOUNDARIES

**Ask:** what must never be false, and what mechanism makes it impossible rather than unlikely?

Write the one or two invariants — "a seat has at most one holder", "an idempotency key returns one
response", "debits equal credits per transfer" — and beside each, the enforcement:

| Invariant shape | Mechanism | Say |
|---|---|---|
| At most one of X | `UNIQUE` constraint, or a conditional `PutItem` with `attribute_not_exists` | "The database refuses the second one; the application never has to win a race" |
| Only one writer wins | `version` column, `WHERE version = ?`, or a DynamoDB condition expression | "Optimistic — a lost update is a retry, not a lock" |
| N rows change together | One transaction on one partition; if they can't share one, an outbox and a saga | "Everything inside this circle commits together; everything outside is eventual, and here's for how long" |
| A retry must not duplicate | Idempotency key stored **in the same transaction** as the write | "The key and the effect commit together, or a crash between them is a double charge" |

Then draw the transaction boundary as a sentence: *"The order, its lines, the payment reference and
the outbox row commit in one Postgres transaction on the customer's shard. Inventory is a separate
conditional write and the saga reconciles them."*

The miss: "we'll use a transaction" without saying what is in it. The interviewer's next question is
always "across which tables, on which shard?"

### E. STORE PER COMPONENT, WITH THE LOSER

**Ask:** for each stateful thing, what is the access pattern, what happens if it's lost, which product,
and what did I reject?

Write the storage decision table — the same shape every design page uses in §12:

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|

One row per stateful component, **including the caches and the queues.** The "What you say" cell
carries the loser: *"Postgres would model this perfectly and I'd use it at a tenth of this scale —
but at 3M writes/s of derived data I want Redis, and I'm giving up nothing because it's a cache."*
Run the decision ladder in §04 F on each row. Most rows take ten seconds; the one where reasonable
engineers disagree gets the deep dive.

The miss: naming the product without the pattern. "Cassandra for messages" is recall; "Cassandra
because messages are append-only, read newest-first by conversation, at a rate one Postgres primary
can't take — partitioned by conversation and time bucket" is a decision.

### F. THE BIG TABLE IN YEAR THREE

**Ask:** which table grows without bound, and what does it look like in three years?

Name it. Multiply the daily write rate by 1,000 days and the row size. Then say four things: the
**partition unit** (month, time bucket, tenant), the **hot/warm/cold ages** and the read latency of
each, the **archive target** (S3 Parquet, queried by Athena), and the **hot-key risk** — the one
partition that fills faster than the others (a prolific author, a busy conversation, a whale tenant)
and the bucketing that keeps it bounded.

The miss: not doing this at all. Unbounded growth with no tiering is the finding an interviewer
gets to make in one sentence, and pre-empting it is one of the cheapest strong signals available.

---

## 03 — The notation

A fixed, typeable format, so that the rep is about the decisions and never about the layout. Use it
in practice; in the interview, the same shape on a whiteboard.

The store tag after the table name is one of five, and it is the second thing on the line because it
is the second decision: `PG` PostgreSQL, `CASS` Cassandra, `DDB` DynamoDB, `REDIS` (the structure
name stands in for it — a line that starts `ZSET` or `HASH` is a Redis line), and `S3` for blobs.
Sidecars that are not the model — Kafka, ClickHouse, Elasticsearch — appear only in the storage table
of step five, written out in full.

### A. RELATIONAL FORM, ANNOTATED

```text
orders            PG   PK order_id uuidv7                     ← time-ordered id: index locality
  user_id, status enum(created|paid|fulfilled|cancelled),     ← lifecycle as an enum, not booleans
  total_cents, currency, idempotency_key, version int,        ← version: optimistic concurrency
  created_at, updated_at
  IDX (user_id, created_at DESC)                              ← serves R "my orders, newest first"
  UQ  (idempotency_key)                                       ← serves "retry must not duplicate"
  ~150/s × 86400 × 1000d ≈ 13B rows × 400B ≈ 5TB
  partition by created_at month; 90d hot, 2y warm, 7y S3     ← year-three line
```

Rules of the block: store and primary key on the first line; columns on the next one to three
lines, **only the ones that carry a decision**; one `IDX` or `UQ` line per hot read or invariant
with the pattern it serves after the arrow; then the size line and the lifecycle line. Six to nine
lines. If a table needs more, it is two tables.

### B. WIDE-COLUMN AND DYNAMO FORM

Partition and sort keys are the whole design, so they get the first line alone:

```text
messages          CASS   PK (conversation_id, bucket)   CLUSTER seq DESC
  bucket = day or seq/10000                              ← bounds the partition at ~100MB
  message_id, sender_id, body, sent_at
  serves R "messages in CONVERSATION, newest first, page 50" — single partition, walk buckets back
  ~10B rows/yr × 300B ≈ 3TB/yr; TTL 30d on the transient branch, tiered to S3 on the archive branch
```

```text
cart              DDB    PK customer_id   SK sku
  qty, added_at, ttl                                     ← TTL attribute: the whole lifecycle
  GSI1 —                                                 ← none: every read is by customer
  serves R "cart for CUSTOMER" (Query on PK) and W "set line" (PutItem, conditional on version)
```

For DynamoDB, write every access pattern beside the key or GSI that serves it, and **say what each
GSI costs**: an extra write per item per index, eventually consistent, its own throughput. A table
with four GSIs is a table you have paid for five times.

### C. REDIS FORM

Every Redis structure in the model names five things, because leaving any of them implicit is where
the design gets hand-wavy:

```text
timeline:{user_id}     ZSET   member=tweet_id   score=tweet_id (snowflake, time-ordered)
  ZADD on fanout (3M/s peak); ZREVRANGE 0 49 on read (300k/s); ZREMRANGEBYRANK to cap at 400
  derived — rebuilt from the author timeline index on miss; loss costs one slow read per user
```

Structure, key, member, score, the commands and their rates, and **the last line: is it derived, and
what happens when it's gone.** That line is the one the interviewer asks for.

`ZSET` is the example because it is the structure interviews reach for most — anything ordered by a
number: a timeline, a leaderboard, a sliding window, a delay queue. It is not the default. **The
structure is chosen by the command you need, not the other way round**, and the same five-line shape
holds for each one. The lock and the cache, written the same way:

```text
lock:{event_id}:{seat_id}    STRING   value=holder_token   SET … NX EX 600
  SET NX on hold (10k/s at onsale); DEL by token check on release; TTL is the expiry
  derived — the seat row's status is the truth; a lost lock re-opens a hold the DB will still refuse

user:{user_id}               HASH     fields=name,plan,avatar_url
  HSET on profile write (100/s); HGETALL on read (50k/s); EX 300
  derived — cache-aside from users PG; loss costs one slow read per user; stampede on a celebrity key
```

The full structure-by-command table, and the rule for picking one, are in §04 D.

### D. THE RULES

1. Every table names the index that serves each hot read. An index with no read beside it is a cost
   with no buyer.
2. Every unbounded table names its partition unit and its retention.
3. Every Redis key names structure, key, member, score, commands, and what happens when it is lost.
4. Every duplicated field names its owner and the mechanism that repairs it — outbox, CDC, or a
   nightly job.
5. Every `status` column is an enum with the terminal states marked; every entity with contention has
   a `version`.
6. Row estimates are order-of-magnitude and labeled as assumptions. Nobody is grading the arithmetic;
   they are grading whether you did it.

---

## 04 — The four stores as modeling rules

`Technology Choices` covers what each store *is* — the mechanism, the trigger numbers, the
durability layers. This section covers how each one changes *what you write down*. The same entity
is modeled four different ways, and the interviewer can tell within one table block whether you
have actually built on the store you named.

### A. POSTGRES — MODEL THE ENTITIES, THEN INDEX THE QUERIES

One table per entity, foreign keys between them, and joins are free. That is the modeling freedom
Postgres gives you: **you can write the tables before you know every query, and add an index when a
query arrives.** The things to write down are the ones the other stores can't do:

- **Constraints as invariants.** `UNIQUE`, `CHECK`, foreign keys. A unique index is a race-safe
  invariant that costs one line; on the other three stores it is a conditional write you must
  remember to make every time.
- **Transactions across rows and tables**, on one primary or one shard. The transaction boundary is
  a sentence in your model, and it is the sentence Postgres lets you say.
- **`version int` on any row two writers can touch**, with `UPDATE … WHERE version = ?`. Say
  "optimistic" and move on; pessimistic `SELECT … FOR UPDATE` is for the ticketing case where the
  contention is the whole problem.
- **Declarative partitioning by time** on the big table, so the year-three plan is `DETACH
  PARTITION` and a copy to S3, not a migration.
- **When sharded (Citus, Vitess), the shard key is the aggregate root and every table that commits
  with it is colocated on the same key.** Say "colocation", not "sharding" — colocation is the
  property that keeps the transaction local, and it is what the checkout and payments pages buy.

The modeling miss: bringing DynamoDB habits to Postgres — composite string keys like
`TENANT#123#ORDER#456`, denormalized copies of everything, no foreign keys. In Postgres those are
costs with no benefit, and they signal you have one model for every store.

### B. DYNAMODB — MODEL THE QUERIES; EVERY PATTERN IS A KEY

Write the access-pattern list first, then design one key or one GSI per pattern. There is no other
way to read DynamoDB, so **the model is the pattern list with keys attached**:

- **Partition key picks the item collection; sort key orders it.** `Query` on a partition key with a
  sort-key range is the only efficient read. Everything else is a `GetItem` by full key, a GSI, or
  a `Scan`, and a `Scan` in a design round is a confession.
- **Every GSI costs a write per item per index, is eventually consistent, and has its own capacity.**
  Two GSIs is normal; five means the workload wanted Postgres.
- **Single-table design when patterns share a partition**: order and its lines under
  `PK=ORDER#id` with `SK=ORDER` and `SK=LINE#n` read in one `Query`. Useful; not mandatory; say why
  you are doing it or don't.
- **Invariants are condition expressions.** `attribute_not_exists(pk)` for at-most-one,
  `version = :expected` for lost-update protection, `available >= :qty` for inventory. **The
  condition *is* the correctness** — there is no lock to take.
- **`TransactWriteItems` for up to 100 items across tables**, at double the write cost. Enough for
  order-plus-lines; not a substitute for a relational transaction over an unbounded set.
- **TTL attribute for anything with a lifetime** — sessions, holds, idempotency records, carts. The
  TTL is the sweeper.
- **Streams for CDC** into the search index, the cache, the analytics table.
- **Hot partition: ~1,000 writes/s or ~3,000 reads/s per physical partition.** A key hotter than that
  needs write sharding (`key#0..N`) and a scatter read — say the number and the mitigation together.
- **400KB item cap.** A growing list in an item is a bug waiting for year two.

The modeling miss: **adding a GSI for every "filter by X" the interviewer mentions.** The right
answer to the sixth access pattern is often "that one is a Postgres read model fed by Streams",
not a sixth index.

### C. CASSANDRA — MODEL THE PARTITION; ONE TABLE PER READ

The partition key picks the node; the clustering columns pick the order on disk within it. A read
that is a single partition scanned in clustering order is fast at any scale; everything else is not
available. So:

- **One table per read pattern**, written N times on every write. Denormalization is not a
  performance trick here; it is the only way to have a second query. The tables are named by the
  read they serve: `messages_by_conversation`, `tweets_by_author`.
- **Bound the partition.** Past ~100MB or ~100k rows per partition, compaction and repair degrade.
  An append-only entity partitioned by its owner is unbounded, so **the key is
  `(owner_id, bucket)`**, with `bucket` a time window or a sequence range. Time buckets are right when
  the read is newest-first, because the read walks buckets backward and stops early.
- **Clustering order is the sort in your access pattern.** `CLUSTER seq DESC` because the read is
  "newest first". Get this backward and every page is a reverse scan.
- **No joins, no ad-hoc queries, no useful secondary indexes.** A "filter by status" is a new table
  keyed by status, or it is a different store.
- **Lightweight transactions (Paxos) cost ~10× a normal write.** One per user action is fine; one
  per message is not. An invariant that needs LWT on the hot path is a sign the entity wanted
  Postgres.
- **Deletes are tombstones**, read until compaction. Model deletion as a TTL where you can.
- **Multi-datacenter replication is native** and is often the actual reason to be here.

The modeling miss: a partition key that is just the entity's owner, with no bucket, on an append-only
table. It works at launch and fails in year three; naming the bucket unprompted is the strongest
single signal in a Cassandra model.

### D. REDIS — MODEL THE OPERATION; EVERY STRUCTURE IS A COMMAND

Yes, Redis belongs in the model. It appears in nearly every real system — the counter, the lock,
the session, the leaderboard, the connection registry, the timeline cache — and **a model that
leaves it implicit is exactly where the interviewer finds the "what happens when Redis dies?"
hole.** The rule that keeps it honest: **Redis is in the model as a named row, and it is never the
system of record.** Every Redis key carries the line "derived from X, rebuilt by Y, loss costs Z".

The structures and the operations they are for — pick the structure by the *command* you need:

| Need | Structure | Key shape | The commands | Typical loss story |
|---|---|---|---|---|
| Cache an object | STRING or HASH | `user:{id}` | `SET … EX 300` / `HSET`, `GET` / `HGETALL` | Cache miss; one slow read |
| Counter, rate limit | STRING | `rl:{user}:{minute}` | `INCR`, `EXPIRE` | A minute of permissive limits |
| Sliding-window limit | ZSET | `rl:{user}` member=request_id score=ts | `ZADD`, `ZREMRANGEBYSCORE`, `ZCARD` in a `MULTI` | Same |
| Leaderboard, timeline, delay queue | ZSET | `lb:{game}` member=user score=points | `ZADD`, `ZREVRANGE`, `ZRANK`, `ZRANGEBYSCORE` | Rebuild from the truth table |
| Membership, dedupe | SET | `seen:{job}` | `SADD`, `SISMEMBER` | Reprocess; must be idempotent anyway |
| Session, presence, registry | STRING with TTL | `conn:{device}` → gateway | `SET … EX 30` on heartbeat, `MGET` for fanout | Devices look offline until the next heartbeat |
| Lock, lease | STRING | `lock:{resource}` | `SET … NX EX`, release by token check | A lock outlives its holder until TTL; the DB must still enforce the invariant |
| Driver location, nearby search | GEO (a ZSET) | `drivers:{cell}` | `GEOADD`, `GEOSEARCH` | Regenerates in seconds from the next heartbeat |
| Approximate uniques | HyperLogLog | `uniq:{day}` | `PFADD`, `PFCOUNT` | A day of analytics |
| FIFO work queue, recent-N list | LIST | `jobs:{queue}` | `LPUSH`, `BRPOP` (blocking pop), `LTRIM` to cap | Jobs in flight are lost; use a durable queue if that matters |
| Log with consumer groups | STREAM | `events:{shard}` | `XADD`, `XREADGROUP`, `XACK` | Use Kafka if losing it matters |
| Wake-up across gateways | PUB/SUB | channel `ns:{namespace_id}` | `PUBLISH`, `SUBSCRIBE` | Fire-and-forget: a subscriber that is not connected never sees it, so it is a hint, and the truth is somewhere durable |

**Picking the structure is one question: what is the operation?** Walk it in this order and stop at
the first yes.

1. One value by key — get, set, increment, expire: **STRING**. This covers the cache, the counter,
   the session, the lock, and the idempotency marker. It is most of Redis.
2. Several fields of one object you update independently: **HASH**. `HINCRBY` on one field beats
   rewriting a JSON string.
3. "Is X in the set?" or "give me the set": **SET**. Dedupe, membership, tags.
4. Anything ordered by a number — a timestamp, a score, a sequence — that you read by rank or by
   range: **ZSET**. This is the one people over-reach for: if you only need FIFO, a LIST is cheaper;
   if you only need a count per window, `INCR` on a bucketed key is cheaper; if you need it durable
   with consumers, it is a STREAM or Kafka.
5. Push one end, pop the other: **LIST**. A job queue with no retry semantics.
6. Distance from a point: **GEO**, which is a ZSET with a geohash score.
7. A count where ±1% is fine and exact would not fit: **HyperLogLog**.
8. Append-only with consumer groups and acknowledgement: **STREAM**, and then ask why it is not Kafka.
9. Tell everyone connected right now, and do not care who missed it: **PUB/SUB**.

**Then two questions of atomicity**, because "isn't that a race?" is the follow-up:

- One command is atomic by itself — Redis executes commands serially, so `INCR`, `SET NX`, `ZADD`,
  and `HINCRBY` never interleave. Say that, and most rate limiters and locks are done.
- A check-then-act across commands is not — read a value, decide, write. Wrap it in a **Lua script**
  (atomic, and the usual answer) or `MULTI`/`EXEC` (atomic, but it cannot branch on a read). In
  cluster mode every key the script touches must share a hash tag.

**How to say it, if Redis is not your daily tool.** One sentence per key, in this shape:
*"I keep the STRUCTURE at KEY, member M, score S. The write is COMMAND at RATE, the read is COMMAND
at RATE, TTL of T. It's derived from TABLE, rebuilt by MECHANISM, and losing it costs THIS."* For the
timeline cache above: *"A ZSET per user, member tweet id, score the snowflake. ZADD on fanout at
three million a second, ZREVRANGE of fifty on read, capped at four hundred. Derived from the
author's post index; a lost node costs one slow read per user."* You do not need to know Redis
internals to say that; you need the command name, the rate, and the loss story. If you cannot name
the command, you have not chosen a structure yet.

Three facts that always come up, so put them in the model before they are asked:

- **Durability is "up to about a second".** Replication is async, and AOF fsyncs every second. A
  failover loses the writes in that window. That is fine for every row above whose loss story is
  "rebuild"; it is not fine for a counter that decides who gets a seat — see the Ticketmaster page's
  §12 for what you say when Redis is briefly the truth.
- **Cluster mode hashes keys to slots**, so a multi-key operation needs a hash tag: `{user_id}` in
  both keys. Every `MULTI`, every Lua script, every `MGET` in your model either shares a tag or is
  N round trips.
- **Memory is the budget.** ~100 bytes of overhead per key plus the value. A billion keys is a
  hundred gigabytes before you store anything; that arithmetic is what decided against Redis for
  cursors on the messaging page.

The modeling miss: **Redis as the database.** "We'll keep it in Redis with persistence on" is a
slower cache with a story attached. If you cannot lose it, it goes in a database and Redis fronts it.

### E. ONE ENTITY, FOUR WAYS

The same thing — messages in a conversation, read newest-first, page 50 — written in each store, so
the differences are visible side by side.

| | Postgres | DynamoDB | Cassandra | Redis |
|---|---|---|---|---|
| **Layout** | `messages (PK message_id)`, `IDX (conversation_id, seq DESC)`, table partitioned by month | `PK=conversation_id#bucket`, `SK=seq` (numeric, descending `Query`) | `PK (conversation_id, bucket)`, `CLUSTER seq DESC` | `ZSET msgs:{conversation_id}` member=message_id score=seq, capped at 200 |
| **The read** | Index range scan, one partition if bucketed by time | `Query` with `ScanIndexForward=false`, `Limit 50` | Single-partition slice, walk buckets backward | `ZREVRANGE 0 49`, then hydrate from the truth store |
| **Dense `seq`** | `UPDATE conversations SET seq = seq+1 … RETURNING`, same transaction as the insert | A counter item with a conditional update, then the put — two writes, a burned number on failure | Only via LWT at ~10× cost; use a sortable id instead | `INCR seq:{conv}` — fast, and a failover can reissue a number |
| **Invariant: no duplicate `(conversation, seq)`** | `UNIQUE` | Condition `attribute_not_exists(SK)` | Not enforceable cheaply; make the id unique upstream | Not enforceable |
| **Year three** | Detach old monthly partitions to S3 | TTL attribute or an archive job off Streams | Row TTL, or bucket ages out and is copied to S3 | Cap the set; it was never the archive |
| **What flips you off it** | > ~15–50k writes/s to this table, or multi-region active-active | Needing a dense sequence or an ad-hoc query | Needing a transaction with the counter, or any read not by conversation | Needing to keep it |

**The thing to say:** *"The read is the same on all four. What differs is where the invariants live —
Postgres enforces them, DynamoDB lets me assert them per write, Cassandra makes me push them
upstream, and Redis has none. So the choice is really about which invariants I need and what write
rate I need them at."*

### F. THE DECISION LADDER

Four questions, asked in order, for every row of the storage table. Stop at the first yes.

1. **Does it need multi-row atomicity, `UNIQUE` constraints, or queries you can't enumerate today?**
   → **Postgres.** Shard it on the aggregate root with colocation when volume or write rate
   demands; that is still Postgres. Most rows stop here.
2. **Is every read by a known key, at a write rate one primary can't take (> ~15–50k writes/s to one
   table), or does it need multi-region writes?** → **Cassandra or DynamoDB.** Managed and
   pay-per-request with conditional writes and TTL: DynamoDB. Self-run, multi-DC, or you already
   operate it: Cassandra. The difference is operational, not architectural — say that.
3. **Is it derived, ephemeral, or TTL'd, and is losing it survivable?** → **Redis.** Name the
   structure, the command, and the loss story.
4. **Is it bytes, text relevance, or aggregation over billions of rows?** → a sidecar: **S3** for
   blobs with the pointer in the database; **Elasticsearch/OpenSearch** as a derived read model fed by
   CDC; a **columnar store** for analytics, also fed by CDC. One sentence each, never the truth.

If a row answers yes to question 1 *and* question 2 — a transactional entity at firehose rate —
that is the genuine tension, and it is the row that gets the deep dive: sharded Postgres with the
hot counter offloaded, or an LSM store with the invariant pushed to a conditional write.

### G. THE FLIP SENTENCES

One per store, in the voice you'd say it, each with the loser attached.

- **Postgres:** *"I default here and make the others justify themselves. It flips when I can name the
  table past fifteen to fifty thousand writes a second, the row past a thousand serialized updates a
  second, or the region I need to write from — not when someone says 'scale'."*
- **DynamoDB:** *"I take this when the access patterns are enumerable and I want conditional writes,
  TTL, and zero operations. It flips the moment I need a query I didn't design a key for — at which
  point I'm building Postgres out of GSIs, and I should just use Postgres for that read model."*
- **Cassandra:** *"Append-only, keyed reads, multi-datacenter, past the rate a primary can take.
  It flips when I need an invariant on the hot path — a unique constraint, a dense counter — because
  Paxos per write costs me the throughput I came for."*
- **Redis:** *"Anything derived, ephemeral, or hot enough that a disk round trip is the bottleneck,
  with a loss story I can state. It flips when I catch myself saying 'with persistence on' — that
  means I can't lose it, and then it isn't a cache, and Redis isn't a database."*

---

## 05 — The pressure test

These are the ten questions a staff-level interviewer asks about a data model, in roughly the order
they ask them. A model that pre-answers them survives; one that doesn't gets walked through them one
at a time, which uses up the deep-dive minutes on defense.

### A. THE TEN QUESTIONS, AS A RUBRIC

Score each 0–2 after a rep. **0** is no answer or a wrong one; **1** is a category, an adjective, or
a product name with no derivation; **2** is a key, a number, a mechanism, and the alternative you
rejected.

| # | The question, as they ask it | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | "What's the partition key, and why won't it go hot?" | No key, or "hash of the id" for everything | A key, no argument about skew | The key, the entity that bounds the transaction, the skewed case named (celebrity, whale tenant, hot SKU) and the bucket or spread that bounds it |
| 2 | "Show me the query for X. Which index serves it, and what does that index cost on writes?" | A scan, or "we'd add an index" | The right index, no cost | The index with column order matching equality-then-range, the write amplification named, and which reads were left unindexed on purpose |
| 3 | "Two of these arrive at the same time. What happens?" | "It works" | "A transaction" or "a lock", unspecified | `version` / condition expression / `UNIQUE`, which one wins, what the loser sees, and why the database rather than the app decides |
| 4 | "What's inside the transaction, and what's outside it?" | No boundary | "The order stuff" | The exact tables that commit together, the shard they share, the outbox row in it, and the duration of eventual consistency for what's outside |
| 5 | "What's duplicated? Who owns it, how does it propagate, how stale can it be?" | Doesn't know it's duplicated | Names the copy | Owner, mechanism (outbox, CDC, Streams), lag in seconds, and the repair job |
| 6 | "What's the biggest table in three years, and what do you do about it?" | Hasn't multiplied | A number, no plan | Rows × bytes, the partition unit, hot/warm/cold ages with latencies, archive target, and the hot-partition case |
| 7 | "How do you paginate this, stably?" | Offset | Cursor, unspecified | Cursor over `(sort_key, id)`, whether the page set is a snapshot or live, and the max page size |
| 8 | "Why not *the other store*?" | "It's what I know" | A property of the winner | The specific property the loser lacks *at this workload* — with the number or the invariant that decides it — and when the loser would win |
| 9 | "Redis is down. What breaks?" | Redis isn't in the model | "It's a cache" | Per key: derived from what, rebuilt how, what the user sees meanwhile, and the one key (if any) whose loss is not survivable — with its recovery |
| 10 | "You need to add a column and change the key. How, without downtime?" | "A migration" | Expand/contract, unnamed | Expand → backfill idempotently → dual-read and verify → cut over → contract; the new key as a new table fed by CDC; concurrent index builds |

### B. HOW TO SCORE

Twenty points. **Below 14, run the same problem again**, not a new one — the misses are specific to
this shape and a new problem hides them. At 14–17, move on and note which questions scored 1; the
ones that recur across problems are the sections of this guide and `Technology Choices` to reread.
At 18 or above on a problem you have not seen, the skill is there and the remaining work is doing it
out loud in five minutes.

Two patterns worth naming, because they are the common way to lose points while feeling fine:
**question 8 scored as a 1** — you named the winner's strengths rather than the loser's specific
inadequacy here; and **question 9 scored as a 0** — Redis was on the whiteboard as a box but not in
the storage table as a row.

---

## 06 — Ten worked models

Each one is a rep. **The prompt and the numbers are visible; everything else is behind the
collapsible.** Set a ten-minute timer, produce the six artifacts in the notation on a blank page,
then open the key and score yourself against §05. The keys are deliberately compressed — this is
the five-minute version you would produce in a round, not the full derivation. Where a design page
exists, its §12 has the argument behind each row.

The models are ordered so the store emphasis rotates: a key-value warm-up, then Postgres under
transactions, Cassandra under append volume, mixed stores under fanout, Postgres under contention,
Redis under geo, Redis as the primary, an append-only ledger, blobs plus metadata, and multi-tenancy.

### A. URL SHORTENER

**Prompt.** Shorten URLs; redirect on the short code; show an owner their links and click counts.
Numbers given: 1B stored URLs, 1k creates/s, 100k redirects/s, clicks are Zipf-distributed (a few
codes take most of the traffic).

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** URL, User, Click. Root: the URL row — there is nothing else to be atomic with.

**2. Access patterns.**

```text
R  redirect by SHORT_CODE                                          hot    100k/s
W  create URL for USER                                             warm   1k/s
R  URLs for USER, newest first, page 50                            cold
W  record CLICK on SHORT_CODE                                      hot    100k/s (async)
R  click count by SHORT_CODE; clicks by day                        warm
```

**3. Tables.**

```text
urls              PG   PK short_code char(7)                 ← base62 of a 42-bit counter
  long_url, owner_id, created_at, expires_at
  IDX (owner_id, created_at DESC)                            ← R "my URLs"
  UQ  (owner_id, url_hash)                                   ← idempotent create; same URL, same code
  1B × 500B ≈ 500GB; expired rows swept nightly

url:{code}        REDIS  STRING = long_url, EX 86400
  GET on every redirect (100k/s, ~95% hit under Zipf); SET on miss
  derived — loss sends 100k/s to Postgres replicas: survivable, warm-up takes minutes

clicks            COLUMNAR (ClickHouse)   ORDER BY (short_code, ts)
  ts, short_code, referrer, country, ua_hash
  written from Kafka in batches; 100k/s × 86400 ≈ 9B rows/day × 60B ≈ 500GB/day raw
  raw 90d, daily rollups (short_code, day, count) kept forever

clicks:{code}     REDIS  STRING, INCR on redirect; flushed to the rollup table every minute
  derived — loss costs under a minute of the live counter
```

**4. Invariants.** One code → one URL, forever: `PK` uniqueness, and codes are never reused after
expiry. Code generation is the only contended write: a Postgres sequence, or a Redis `INCR` counter
with **block reservation** (take 1,000 at a time, persist the ceiling) so a failover can't reissue —
gaps in codes are invisible, so this is the Ticketmaster queue-counter move and it's correct here.
The redirect path has no invariant and no transaction.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| URL table | Point read by code, keyed writes, one cold range read | Absolute | **Postgres** (DynamoDB is equally right) | "There's no join in this system, so DynamoDB loses nothing — I'd still start on Postgres because the owner and analytics reads are the ones I haven't fully enumerated. It flips to DynamoDB if I want zero ops and global tables" |
| Redirect cache | 100k/s reads, Zipf | Derived | **Redis**, `EX 1d` | "The cache is the system; the database is where misses go. A viral code is a single hot key — that's fine in Redis, and it's the case that would hurt an unreplicated Postgres" |
| Click log | Append-only firehose, aggregated by code and day | Recoverable from Kafka for 7 days | **Kafka → ClickHouse** | "Never read by the redirect path, so it wants a columnar store, not a serving one. Redis `INCR` gives the live count; the columnar rollup is the truth" |

**6. Year three.** Clicks: half a terabyte a day raw; keep 90 days, roll up daily forever. URLs are
bounded by creates and swept by expiry. No hot partition in the truth store — the hot code lives in
Redis.

**Where they press.** Code generation under two writers (block reservation); the cache stampede on a
new viral link (single-flight on miss, or a short negative-cache); 301 vs 302 — a 301 is cached by the
browser and you lose the click. **This is a warm-up; the point is doing all six artifacts in under
five minutes on a problem with no hard invariant.**

</details>

### B. ORDERS AND INVENTORY

**Prompt.** Checkout for a retailer: carts, place order, reserve inventory across fulfillment
centers, pay, fulfill. Numbers given: 150 orders/s steady, 1,500 reserve attempts/s peak, 200M
customers, one "lightning deal" SKU can take 1,600 attempts/s alone, orders must be kept seven years.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** Customer, Cart, CheckoutSession, Order, OrderLine, Inventory (per SKU per
fulfillment center), Reservation, PaymentAuthorization. Root: **the Order** — order, lines, payment
ref, and the outbox row commit together. Inventory is deliberately *not* inside the root.

**2. Access patterns.**

```text
R  cart for CUSTOMER                                               hot    50k/s
W  place ORDER for CUSTOMER (idempotent on checkout_session)       warm   150/s
W  reserve INVENTORY by (sku, fc)  qty                             hot    1.5k/s, 1.6k/s on one SKU
R  orders for CUSTOMER, newest first, page 20                      warm   5k/s
R  order by ORDER_ID (status page, support)                        warm
W  sweep expired RESERVATIONS                                      cold   every few seconds
R  find my order from March (search)                               cold
```

**3. Tables.** Two partition keys, and the gap between them is the design.

```text
orders            PG/Citus  distributed on customer_id     PK (customer_id, order_id uuidv7)
  status enum(placed|authorized|reserved|fulfilled|cancelled), total_cents, currency,
  checkout_session_id, version, placed_at
  UQ  (checkout_session_id)                                 ← one order per session, whatever the cache says
  IDX (customer_id, placed_at DESC)                         ← R "my orders"
  150/s × 86400 × 1000d ≈ 13B rows; monthly partitions; 90d hot, 2y warm, 7y S3 Parquet

order_lines       PG/Citus  colocated on customer_id       PK (customer_id, order_id, line_no)
  sku, qty, unit_price_cents (snapshot — not a foreign key to the price book), fc_id

outbox            PG/Citus  colocated on customer_id       PK (customer_id, event_id uuidv7)
  order_id, type, payload, published_at NULL               ← same transaction as the order

inventory         DDB    PK sku   SK fc_id
  on_hand, reserved, version                               ← available = on_hand − reserved
  W: UpdateItem SET reserved = reserved + :q  CONDITION on_hand − reserved >= :q
  the hot SKU gets a reservation pool: N pre-split rows, one taken per attempt

reservations      DDB    PK order_id   SK sku#fc
  qty, state enum(held|confirmed|released), expires_at
  GSI1 PK expires_minute                                    ← the sweeper's read; the only GSI

cart              DDB    PK customer_id   SK sku            qty, ttl 30d
idempotency       DDB    PK checkout_session_id             response, ttl 24h — a fast pre-check only

carts, sessions:  loss is survivable; orders: none acceptable — synchronous replica
```

**4. Invariants.** *Available never goes negative*: the DynamoDB condition expression, per line, no
lock. *One order per checkout session*: `UNIQUE (checkout_session_id)` on `orders` — **the
idempotency cache short-circuits the double-click, but correctness lives in the unique index**, so a
lost cache record cannot produce a second order. *Order, lines, payment ref, outbox commit together*:
one local transaction, possible only because all four are colocated on `customer_id`. Inventory is
outside that boundary, so placing an order is a **saga**: reserve → authorize → commit, with
reservations released by the sweeper on failure or expiry, and eventual consistency between "order
placed" and "stock decremented" of a few seconds.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| Orders, lines, outbox | 150 w/s, single-shard reads by customer, 13B rows | Zero loss | **Postgres + Citus on `customer_id`, colocated** | "I'm not sharding for throughput — 150 a second fits on one box. I'm sharding for volume and buying colocation, which is what keeps the order commit local. DynamoDB would make the outbox a dual write" |
| Inventory | Conditional decrements by SKU, 1.5k/s peak | Correctness-critical, reconciled physically | **DynamoDB conditional writes** | "The condition is the correctness. Postgres would do it too, and I'd take Postgres at a tenth of the SKU count; DynamoDB because there's no transaction with anything else and I want the hot SKU to be a capacity problem, not a lock problem" |
| Reservations | Written with the reserve, swept by expiry | Recoverable — a stranded hold costs a minute of availability | Same table, GSI on expiry minute | "A row with a state and a clock. Ticketmaster evaluates expiry inline on the seat row; I can't, because what I test is an aggregate" |
| Cart | Per customer, no money | Survivable | **DynamoDB**, TTL | "Intents, not prices" |
| Idempotency keys | Read-before-write on place order | A miss costs a wasted reserve, never a duplicate | **DynamoDB TTL 24h, backed by the unique index** | "The fast store is an optimization; the constraint is the guarantee" |
| Order search | "Find my order from March" | Derived | **OpenSearch** from the outbox stream | "Allowed to be down" |

**6. Year three.** Orders: 13 billion rows in the two-year hot window; monthly partitions, 90 days
hot, seven years in S3 because tax law says so. The hot partition is a SKU, not a customer, and it is
intentional and bounded by the reservation pool.

**Where they press.** "Why isn't inventory in the same Postgres?" — because it partitions by SKU and
orders by customer, and no key reconciles them; that gap is why the saga exists. "Why not put the
idempotency record in Postgres too?" — you could, and the payments page does, because there the
stored response must commit with the ledger; here the unique index is enough. Full derivation:
**the Amazon checkout design page, §12.**

</details>

### C. CHAT / MESSAGING

**Prompt.** One-to-one and group chat, delivered to every device, ordered, with read receipts and
sync after being offline. Numbers given: 1B devices, 100B messages/day, groups up to 1,000, a busy
conversation does ~10 messages/s, a conversation can be years old.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** Conversation, Member, Message, Cursor (per device per conversation), Device
connection. Root: **the Conversation** — ordering, membership, and the sequence counter live inside
it.

**2. Access patterns.**

```text
W  send MESSAGE to CONVERSATION (dedupe on client_message_id)      hot    1.2M/s global, ~10/s per conv
R  messages in CONVERSATION, newest first, page 50                 hot
R  messages in CONVERSATION since SEQ (sync)                       hot    on every reconnect
R  conversations for USER, most recent first                       warm   app open
W  advance CURSOR for (device, conversation)                       hot    per read
R  gateway for DEVICE (fanout)                                     hot    per message × members
```

**3. Tables.**

```text
conversations     PG   PK conversation_id            type, created_at, seq int   ← the counter row
members           PG   PK (conversation_id, user_id) role, joined_at

messages          CASS   PK (conversation_id, bucket)   CLUSTER seq DESC
  bucket = seq / 10000                                    ← ~100MB partitions even for a decade-old group
  message_id, sender_id, body, sent_at
  serves both hot reads: newest-first walks buckets back; sync reads WHERE seq > ? within a bucket
  100B/day × 300B ≈ 30TB/day on the archive branch; TTL 30d on the transient branch

cursors           CASS   PK conversation_id   CLUSTER device_id      delivered_seq, read_seq
  co-partitioned with the log so a sync reads both; USING TIMESTAMP = seq so LWW resolves by seq

conn:{device_id}  REDIS  STRING = gateway_id, EX 30, re-set on each 10s heartbeat
  MGET for a group's recipients in one round trip; absent ⇒ offline ⇒ push
  ~1B keys × 100B ≈ 100GB, sharded — none durable, rebuilt by reconnects

convs:{user_id}   REDIS  ZSET member=conversation_id score=last_activity_ts (not seq — not comparable)
  ZADD from the outbox, ZREVRANGE 0 49 on app open — derived, rebuilt from the log
```

**4. Invariants.** *No two messages share `(conversation_id, seq)`*: if `seq` is dense, the counter
row and the insert commit in **one Postgres transaction** — which means the log is in Postgres too,
sharded by conversation. If the log is Cassandra, `seq` cannot be dense: use a Snowflake or HLC id
and replace gap detection with cursor sync. **Density picks the store — this is the fork to name out
loud.** *A retried send does not duplicate*: `client_message_id` unique per conversation. *A cursor
never regresses*: write with the seq as the timestamp, or `WHERE seq > cursor`.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| Message log | Append-only, range by seq, ~120 w/s per shard, 30TB/day total | Absolute | **Cassandra** `(conversation_id, bucket)` if seq is sortable; **Postgres** sharded by conversation if seq must be dense | "Write-once with range reads is the ideal LSM workload — but a dense sequence needs the counter and the log in one transaction, and 120 writes a second per shard doesn't need an LSM anyway. I'd pick sortable and Cassandra, like Slack does" |
| Connection registry | 1B keys, extreme churn, TTL-native | None | **Redis Cluster** | "Losing it means a device looks offline until its next heartbeat, and delivery is best-effort anyway" |
| Cursors | Point write per device per conversation; read all on sync | Low | **Co-partitioned with the log** | "20B rows is terabytes of RAM — that's why it isn't Redis. Warm, large, semi-durable is the opposite of what Redis is for" |
| Conversation list | Cross-shard by nature, per user | Rebuildable | **Redis ZSET** | "The score has to be a timestamp; `seq` is per-conversation and not comparable" |
| Outbox → fanout | Ordered, replayable | High, bounded | **Kafka** | "Receipts, search, and analytics fan out from one commit" |

**6. Year three.** The log. A years-old group has millions of rows under one conversation, so the
bucket is what keeps the partition under ~100MB; time buckets are right because the read is
newest-first. Archive branch: 30TB/day tiered to S3 after 90 days with a search index; transient
branch: row TTL and the server holds ciphertext. **Say which branch in the first two minutes** —
the storage estimate differs by three orders of magnitude.

**Where they press.** Dense vs sortable `seq`, and where the counter lives; the conversation list
sort key; a Redis failover reissuing a `seq` (it can, which is why the counter is not in Redis).
Full derivation: **the WhatsApp design page, §12.**

</details>

### D. FEED / TIMELINE

**Prompt.** A home timeline of posts from accounts you follow, newest first. Numbers given: 500M
daily users, 6k posts/s, a timeline read is 300k/s at peak, some accounts have 50M followers, posts
are immutable.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** User, Post, Follow, Timeline (a materialized list per user). Root: **none worth
circling** — nothing needs to be atomic across entities, because the product accepts an eventually
consistent feed. Say that; it is why partitioning is unusually free here.

**2. Access patterns.**

```text
R  timeline for USER, newest first, page 50                        hot    300k/s
W  post by AUTHOR                                                  warm   6k/s
W  fan out POST to followers' timelines                            hot    ~3M/s (6k × avg 500)
R  recent posts by AUTHOR, newest first (profile, celebrity pull)  warm   20k/s
R  followers of USER (fanout), followees of USER (pull)            warm   per post / per read
R  hydrate POSTS by id, batch of 50                                hot    300k/s × 50
R  like count for POST                                             hot    approximate
```

**3. Tables.**

```text
posts             CASS   PK post_id (snowflake)
  author_id, body, media_ref, created_at                   ← immutable; a partition never grows after write
  serves R "hydrate by id" as bulk point reads; 6k/s × 86400 × 1000d ≈ 500B rows

posts_by_author   CASS   PK (author_id, time_bucket=week)   CLUSTER post_id DESC
  post_id only                                             ← ids, not bodies; the second access pattern gets a second layout
  serves R "recent by author" — walk weeks back; bounded even for a prolific account

follows           CASS   PK (user_id, bucket) → followee_id; and the reverse table followers (user_id, bucket) → follower_id
  50M followers ⇒ bucketed; single-hop adjacency only, no graph DB needed

timeline:{user_id}  REDIS  ZSET member=post_id score=post_id  capped at 400 (ZREMRANGEBYRANK)
  ZADD 3M/s on fanout; ZREVRANGE 0 49 at 300k/s
  derived — on miss, rebuild from posts_by_author for the user's followees; skip inactive users

likes:{post_id}   REDIS  STRING, INCR; async-persisted to a counts table — approximate by decision
```

**4. Invariants.** None that need a transaction. The two decisions to name: **hybrid fanout** — push
for authors under ~10k followers, pull-and-merge at read for the rest, so one celebrity post is 1
write, not 50M; and **the timeline is a cache of a computation**, so losing it costs latency, never
data. Pagination: cursor on `post_id` (time-ordered), page set is live — a new post appears at the
top, never inside a page.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| Post store | Write-once, bulk point reads, 500B rows | Absolute | **Cassandra** `PK post_id` | "Immutable, keyed, massive. Snowflake ids distribute perfectly — no hot partition is possible. Postgres would need sharding I'd run by hand, for no join I actually use" |
| Author index | Newest-first by author | Rebuildable from posts | **Cassandra** `(author_id, week)` | "Don't shard posts by author — a decade-old prolific account is an unbounded partition. Second access pattern, second layout, ids only" |
| Timeline cache | 3M/s ZADD, 300k/s ZREVRANGE | Derived | **Redis Cluster**, ZSET per user, cap 400 | "A cache of a computation — which is what lets me cap it and skip inactive users" |
| Follow graph | Adjacency both ways, extreme skew | High | **Cassandra** bucketed | "Single-hop, so wide-column not graph" |
| Fanout queue | Ordered, tiered by author size | High, bounded | **Kafka**, topics per tier | "Tiering stops one celebrity from starving every ordinary post" |
| Counts | Increment constantly | Approximate is fine | **Redis INCR** | "Exact like-counts cost a lot and are worth nothing" |

**6. Year three.** Posts: half a trillion immutable rows, never a hot partition, tiered by age to cheaper
nodes; the timeline is capped and never archives; the author index is bounded by the week bucket.

**Where they press.** Why not shard posts by author; the celebrity threshold and how the merge at read
works; what a timeline miss costs. Full derivation: **the Twitter feed design page, §12.**

</details>

### E. TICKET RESERVATION

**Prompt.** Sell seats for events; a user holds seats for ten minutes, then buys. Numbers given:
10k events, a hot on-sale is 1M people for 20k seats, 166 attempts per seat, no double-sale ever,
the availability map is read 5M/s during a sale.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** Event, Seat, Hold (a state on the seat, not an entity), Order, Queue position. Root:
**the Event** — every seat, hold, and order for an event lives on one shard, so a multi-seat order
is a single-shard transaction.

**2. Access patterns.**

```text
W  hold SEAT(s) for USER in EVENT (atomic, all-or-nothing)         hot    50–100k/s in the sale window
W  buy held SEATS → ORDER                                          warm
W  expire HOLDS                                                    inline — evaluated on the next attempt
R  availability map for EVENT                                      hot    5M/s — never from the DB
R  best available N seats in SECTION                               hot
R  my orders                                                       cold
```

**3. Tables.**

```text
seats             PG  sharded by event_id            PK (event_id, seat_id)
  section, row, status enum(available|held|sold), hold_owner, hold_expires_at, version
  W hold: UPDATE … SET status='held', hold_owner=?, hold_expires_at=now()+10m, version=version+1
          WHERE event_id=? AND seat_id IN (…) AND (status='available' OR (status='held' AND hold_expires_at < now()))
          — commit only if row count = requested count, else roll back
  W best-available: SELECT … WHERE status='available' AND section=? LIMIT n FOR UPDATE SKIP LOCKED
  20k rows per event; trivially small. The point is contention, not size

orders            PG  same shard as the event        PK (event_id, order_id)   user_id, seat_ids[], status, paid_at
  UQ (idempotency_key)

queue:seq:{event_id}, queue:admitted:{event_id}   REDIS  STRING, INCR / SET
  positions are display values; a rewind over-admits briefly and cannot double-sell

availability      in-process bitmap, rebuilt from the outbox, published to CDN with a 1–5s TTL
```

**4. Invariants.** *A seat has at most one holder*: the conditional `UPDATE` with the row lock — the
database decides, never the application. *A hold is a state, not a separate row*: splitting holds
into their own store means two things can disagree about one seat. *Expiry needs no sweeper*: the
predicate evaluates `hold_expires_at` on the next attempt. *Order commit is single-shard*: orders live
with the event. The queue counter in Redis is the one place a lossy store is briefly authoritative,
and the reason it is acceptable is that over-admission causes contention, never corruption.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| Seat inventory | Conditional multi-row updates under 166:1 contention | Absolute | **Postgres sharded by `event_id`** | "`SKIP LOCKED` and transactional multi-row acquisition are the whole design. A KV store gives me neither, and the write volume being small is what lets me afford a relational store" |
| Holds | Same rows | Recoverable | Not a separate store | "A hold is a state on the seat" |
| Availability map | 5M/s reads | Rebuildable | **CDN-cached bitmap**, 1–5s TTL | "The origin never touches the inventory DB for reads" |
| Queue counter, watermark | Millions of INCRs in seconds | Lossy, and that's acceptable — say why | **Redis** with block reservation | "A rewind over-admits; the conditional update still decides who gets a seat" |
| Orders | Low volume, strict | Absolute | Same shard | "Single-shard commit with the inventory" |

**6. Year three.** Nothing here is unbounded in a way that matters — orders archive by event date.
The hot shard is **intentional**: sharding is sized for isolation, not throughput, and an event
cannot be split, so its shard's capacity is the ceiling on how fast it sells — which is why the
queue exists. Sub-partition by section only if one event exceeds a node.

**Where they press.** Why shard by event when the load is wildly uneven (isolation and transactional
locality beat evenness); what Redis losing a second of writes does (over-admission, not double-sale);
why not a sweeper for expiry. Full derivation: **the Ticketmaster design page, §12.**

</details>

### F. RIDE MATCHING

**Prompt.** Riders request, nearby drivers are matched, a trip runs to completion and is paid.
Numbers given: 5M concurrent drivers reporting location every 2 seconds, 30k ride state changes/s
at peak, a match must not assign one driver to two rides, location history is kept for disputes.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** Rider, Driver, Location (live and historical — two different things), Ride,
FareQuote. Root: **the Ride** — a state machine with a version; the driver's assignment is a
conditional update on it.

**2. Access patterns.**

```text
W  update DRIVER location                                          hot    2.5M/s, last-write-wins
R  drivers near POINT (k-ring of geo cells), top 20                hot    per request
W  request RIDE; match RIDE to DRIVER (conditional)                hot    30k/s peak
R  ride by RIDE_ID (client reconcile after reconnect)              hot
R  rides for USER, newest first                                    cold
R  location history for RIDE (dispute, ETA model training)         cold   batch
R  fare quote by QUOTE_ID, single-use, 5 min                       warm
```

**3. Tables.**

```text
rides             PG/Citus  sharded by region_id           PK (region_id, ride_id uuidv7)
  rider_id, driver_id NULL, status enum(requested|matched|en_route|in_trip|completed|cancelled),
  quote_id, fare_cents, version, requested_at
  W match: UPDATE rides SET driver_id=?, status='matched', version=version+1
           WHERE ride_id=? AND status='requested' AND version=?
  IDX (rider_id, requested_at DESC); IDX (driver_id, requested_at DESC)
  30k/s peak but ~20M rides/day ≈ 7B/yr × 500B ≈ 3.5TB/yr; monthly partitions, 2y hot, 7y S3

drivers           PG  same shard                               PK driver_id   status, current_ride_id NULL, version
  W accept: UPDATE drivers SET current_ride_id=? WHERE driver_id=? AND current_ride_id IS NULL   ← one ride per driver

drivers:{cell}    REDIS GEO (a ZSET)  member=driver_id  score=geohash   — or in-process per owned cell range
  GEOADD on every update (2.5M/s across the cluster); GEOSEARCH BYRADIUS on match
  derived — regenerates in ~4s from the next heartbeats; loss costs a few seconds of matching

quote:{quote_id}  REDIS STRING = {fare, route_hash}, EX 300, GETDEL on use   ← single-use
conn:{device_id}  REDIS STRING = gateway, EX 30                              ← push to rider/driver

location_history  KAFKA (hours) → S3 Parquet partitioned by day, region      ← 2.5M/s × 50B ≈ 125MB/s
```

**4. Invariants.** *One driver per ride and one ride per driver*: the two conditional updates in one
transaction on the region shard — `status='requested' AND version=?` on the ride and
`current_ride_id IS NULL` on the driver. Matching can propose the same driver twice under partition
ownership churn; **the database makes the conflict impossible, the matcher only makes it rare.**
*A quote is used once*: `GETDEL`. Live location has **no invariant at all** — last write wins and a
lost update is replaced in two seconds, which is what lets it live in a lossy store.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| Ride store | 30k/s conditional updates, single-entity transactions | Absolute — money | **Postgres sharded by region** (Citus; CockroachDB if you'd rather buy the sharding) | "I need `WHERE status=? AND version=?` to be atomic. 30k a second is small enough not to be clever, so the boring option and the complexity budget goes elsewhere" |
| Live geo index | 2.5M w/s overwrite, k-ring reads | None — regenerable in seconds | **Redis GEO**, or in-process per cell with Redis as warm start | "Locations regenerate themselves, so I trade durability for a dropped hop in the hottest loop. Cassandra would persist 2.5M writes a second that nobody reads back" |
| Fare quotes | Write once, read once, TTL | None | **Redis TTL** (signed token if you don't need single-use) | "Signed means no storage but no revocation; single-use matters, so Redis" |
| Location history | Firehose, batch reads only | High, bounded | **Kafka → S3 Parquet** | "Never read by matching — it's the ETA model's input and the dispute record, so columnar batch, not a serving store" |
| Connection registry | Device → gateway, TTL | None | **Redis Cluster** | "Clients reconcile via the ride read anyway" |

**6. Year three.** Location history: 125MB/s, ~10TB/day, partitioned by day and region in S3, kept
for the dispute window then a sample for training. Rides: 3.5TB/yr, monthly partitions. No hot
partition in Postgres — the hot thing is a city's cell range in the geo index, and that is spread
by ownership, not by key.

**Where they press.** Why not persist location (nobody reads it back on the serving path); what two
matchers believing they own the same cell does (a proposal conflict the ride row rejects); the geo
index rebuild time on a Redis node loss. Full derivation: **the Uber design page, §11–12.**

</details>

### G. RATE LIMITER AND COUNTERS

**Prompt.** Limit API calls per key — 1,000/min, with bursts — across a fleet of gateways, and
show customers their usage. Numbers given: 1M checks/s, the check must add under 1 ms, a limit that
is briefly too generous is acceptable, a limit that blocks a paying customer is not.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** Rule (per scope: key, tenant, IP, endpoint), Bucket state (per rule per subject),
Usage rollup. Root: the bucket — one atomic check-and-consume per request. **This is the model where
Redis is the primary store, and the exercise is saying precisely what that costs.**

**2. Access patterns.**

```text
W  consume 1 token from BUCKET(scope, subject), atomically          hot    1M/s, < 1ms
R  rule for SCOPE                                                    hot    cached in-process
R  usage for SUBJECT by minute/day (dashboard, billing preview)     warm
W  update RULE                                                      cold   propagates in seconds
```

**3. Tables.**

```text
rules             PG   PK rule_id     scope enum, subject_pattern, limit, window_s, burst, version
  tiny; pushed to gateways via config stream; cached in-process with a 30s refresh

rl:{scope}:{subject}   REDIS HASH  {tokens float, ts ms}          ← token bucket
  one Lua script: refill by elapsed × rate, cap at burst, consume 1 or reject; EXPIRE window×2
  atomic because Redis is single-threaded per shard — no MULTI needed
  1M/s across the cluster; hash tag {subject} if a subject has several rules to check together
  derived — loss resets every bucket to full: a window of generosity, which the prompt allows

rl:{scope}:{subject}   REDIS ZSET  member=request_id score=ts     ← sliding-window alternative
  ZREMRANGEBYSCORE (now − window), ZADD, ZCARD in one script; exact, but O(limit) memory per subject
  choose the bucket for 1M/s; the sliding window when the limit is small and exactness matters

usage             COLUMNAR   (subject, minute, count)   from a Kafka stream the gateways emit
  the dashboard reads this, never Redis; rollup to day forever, minutes for 30d
```

**4. Invariants.** *Check-and-consume is atomic*: the Lua script, on one key, on one shard. There is
no cross-key invariant, so there is no transaction. *Redis down → fail open* for rate limits (the
prompt says generosity is acceptable, blocking is not); **say the opposite for quotas that bill** —
a quota is money and needs the durable ledger from the billing page, not this. *Clock*: use the Redis
server's `TIME` inside the script, not gateway clocks, so skew across the fleet does not refill
buckets.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| Bucket state | 1M/s atomic read-modify-write, sub-ms | Loss = a window of generosity | **Redis Cluster**, HASH + Lua | "This is the one model where Redis is the primary, and it's allowed to be because the prompt priced a loss at zero. Postgres would serialize on a hot row at a thousand updates a second — three orders of magnitude short" |
| In-process bucket | Zero-hop variant | None | Per-gateway token bucket, synced to Redis every 100ms | "Removes the hop at the cost of N gateways each holding 1/N of the budget or over-admitting by N×. Take it for coarse limits, not for exact ones" |
| Rules | Tiny, read constantly | Absolute | **Postgres**, pushed to gateways | "Config, not data — it lives in the boring store and is cached everywhere" |
| Usage | Aggregations by subject and time | Recoverable from the stream | **Kafka → ClickHouse** | "The dashboard is an analytics read; it never touches the limiter's keys" |

**6. Year three.** Nothing in Redis grows — every key has a TTL of twice its window. Usage rollups
are the unbounded table: minutes for 30 days, days forever, a few GB a year.

**Where they press.** Fail open vs fail closed, and the answer being different for limits and
quotas; a subject with rules in two scopes (hash tags or two round trips); the sliding window's
memory at a 100k/min limit; whether the local bucket is "good enough" (only if you can say the error
bound: N gateways over-admit by up to N×burst).

</details>

### H. PAYMENTS LEDGER

**Prompt.** Move money between accounts — charges, refunds, payouts — with an auditable record and a
balance per account. Numbers given: 5k transfers/s, every transfer must be idempotent, balances are
read on every dashboard load, records are kept ten years and nothing is ever deleted.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** Account, Transfer, Entry (two or more per transfer — double entry), PaymentIntent,
IdempotencyRecord. Root: **the Transfer** — its entries, the intent's state change, and the stored
idempotent response commit together.

**2. Access patterns.**

```text
W  create TRANSFER (entries, intent update, idempotency response)  hot    5k/s
R  balance for ACCOUNT                                             hot    every dashboard load
R  entries for ACCOUNT, newest first, page 50                      warm
R  transfer by TRANSFER_ID; intent by INTENT_ID                    warm   support, webhooks
R  transfers for MERCHANT in RANGE (export, reconciliation)        cold   daily batch
W  replay TRANSFER with same (merchant, key) → stored response     hot    every retry
```

**3. Tables.**

```text
transfers         PG/Citus  distributed on merchant_id     PK (merchant_id, transfer_id uuidv7)
  type enum(charge|refund|payout|fee), intent_id, amount_cents, currency, status, created_at
  5k/s × 86400 ≈ 440M/day; monthly partitions; 90d hot, 2y warm, 10y S3 Parquet — never deleted

entries           PG/Citus  colocated on merchant_id       PK (merchant_id, entry_id uuidv7)
  transfer_id, account_id, amount_cents signed, currency, created_at   ← immutable; corrections are new entries
  IDX (account_id, created_at DESC)                              ← R "entries for account"
  CHECK: SUM(amount_cents) per transfer = 0, asserted in the transaction before commit

idempotency       PG/Citus  colocated on merchant_id       PK (merchant_id, key)
  request_hash, response jsonb, status, created_at; swept after 24h
  UNIQUE gives the claim; same transaction as the transfer — the reason this is not DynamoDB

balance:{account} REDIS  STRING = cents, rebuilt from SUM(entries) — allowed to be 5s stale
  never the number we pay out; the payout path runs the SUM on Postgres

settlement_files  S3 Object Lock (WORM) + parsed lines in Postgres
```

**4. Invariants.** *Debits equal credits per transfer*: the entries are written together and the sum
is asserted in the transaction. *A transfer happens once*: the idempotency record — key,
request hash, and the terminal response — **commits in the same transaction as the entries.** Put it
in a separate store and a crash between the two is a double charge; that is a dual write on the money
path and it is the reason the record is Postgres and colocated. *Entries are immutable*: a refund
is a new transfer, never an update. *The balance in Redis is a cache of a `SUM`*: it is allowed to
be wrong for five seconds and is never allowed to be the number that authorizes a payout.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| Ledger (transfers, entries) | 5k appends/s, aggregate reads per account, 440M rows/day | Zero loss, 10-year retention | **Postgres + Citus on `merchant_id`**, monthly partitions, synchronous replica | "Money at five thousand appends a second wants the most auditable transactional engine there is. Unlike the checkout page, here the rate justifies distributing it. Appends parallelize; the balance column they replace serializes on a hot row — that's why there isn't one" |
| Idempotency records | Read-before-write on every money call | A lost record is a double charge | **Postgres, colocated, `UNIQUE (merchant_id, key)`** | "It has to commit with the transfer. DynamoDB with a TTL is right for checkout's idempotency because a unique index backs it there; here the stored response *is* the guarantee" |
| Balance | Read on every dashboard | Rebuildable | **Redis** | "A cache of a `SUM`, five seconds stale, never paid out from" |
| Intents, authorizations | Written once, read by merchant and support | High | **Postgres**, same cluster | "Same transaction as the transfer, which only works because they share a shard key" |
| Event stream | Fan-out to webhooks, analytics | At-least-once | **Outbox in Postgres → Kafka** | "The outbox row commits with the transfer, so no dual write" |
| Settlement files | Written daily, read once, kept forever | Immutable evidence | **S3 with Object Lock** | "The one artifact we didn't author; in a dispute it's the evidence" |

**6. Year three.** Entries: 440M rows a day, 160B a year. Monthly partitions; 90 days hot with
millisecond aggregate reads, two years warm, ten years in S3 Parquet queried by Athena in seconds.
**Nothing is deleted** — a gap in a double-entry ledger is indistinguishable from fraud. The hot
partition is a large merchant; Citus rebalances, and a whale gets its own node.

**Where they press.** Why no balance column (parallel appends vs a serialized hot row; if you keep
one, it's a materialization with a version and a nightly reconciliation); why the idempotency record
is not in DynamoDB here when it is on the checkout page; what happens when the acquirer's settlement
file disagrees with the ledger (a reconciliation queue with a human attached). Full derivation:
**the payment processor design page, §12.**

</details>

### I. FILE SYNC

**Prompt.** Sync files across a user's devices and shared folders — upload, download, rename, and
resolve edits from two devices. Numbers given: 500M users, 1B file changes/day, files average 1MB
with some at 50GB, most bytes uploaded are already stored somewhere (dedupe matters), a device can be
offline for weeks.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** User, Namespace (a root or shared folder — the unit of sharing and of the change
journal), File (metadata and current version), Block (a 4MB content-addressed chunk), Device, Cursor
(per device per namespace). Root: **the Namespace** — a file change and its journal entry commit
together, and a device syncs one namespace at a time.

**2. Access patterns.**

```text
R  changes in NAMESPACE since CURSOR, in order                      hot    every device, long-poll
W  commit FILE version (after blocks are present)                    hot    1B/day ≈ 12k/s
R  which BLOCKS of this list do you lack?                            hot    per upload
R  BLOCK by hash                                                     hot    downloads
W  put BLOCK (4MB)                                                   hot    bytes, not rows
R  list FOLDER; file by (namespace, path)                            warm
W  share NAMESPACE with USER                                         cold
```

**3. Tables.**

```text
files             PG  sharded by namespace_id             PK (namespace_id, file_id uuidv7)
  path, current_version, size, block_hashes text[], modified_at, deleted bool, version
  UQ  (namespace_id, path) WHERE NOT deleted                        ← live paths unique
  ~50B files × 300B ≈ 15TB across shards; rename is a metadata write, never a block rewrite

journal           PG  same shard                          PK (namespace_id, seq)
  file_id, op enum(add|modify|move|delete), version, at             ← the sync feed
  seq from a counter column on namespaces, in the same transaction  — dense, and cheap at this rate
  compacted: one entry per file is enough for a device that's been away for weeks

blocks            S3   key = sha256(content), 4MB              — the bytes, immutable, deduped by name
block_index       DDB  PK hash   size, refcount, created_at     ← R "which do you lack" is a BatchGetItem
  ~10B blocks × 100B ≈ 1TB; refcount decremented on file delete, GC'd after a grace period

cursors           PG  PK (device_id, namespace_id)   last_seq
notify:{namespace_id}   REDIS PUB/SUB — wakes long-polls; derived, a missed wake is caught by the next poll
```

**4. Invariants.** *A file version references only blocks that exist*: the client asks which hashes
are missing, uploads those, then commits metadata — **the commit is rejected if any hash is absent
from the index**, so the metadata store never points at bytes that aren't there. *Journal order is
total per namespace*: the counter column and the entry commit together on one shard. *Two devices
editing one file*: the commit carries the version it was based on; a mismatch is not a failure but a
**conflicted copy** — a second file, both kept, because the product decision is "never lose either
edit." *A block is never deleted while referenced*: refcount, with a grace period so a new reference
racing a GC cannot lose.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| File metadata + journal | 12k w/s, range reads by namespace and seq, path uniqueness | Absolute | **Postgres sharded by `namespace_id`** | "The journal needs a dense per-namespace sequence committed with the metadata, and the path needs a unique constraint — both relational. Sharded by the unit of sharing, so a sync is one shard" |
| Blocks | Immutable 4MB objects, keyed by content hash | Absolute, cheap | **S3** | "Content addressing makes dedupe a naming problem. Metadata and ACLs live in Postgres; S3 never decides who can read" |
| Block index | Point lookups by hash at upload and download, 10B keys | High; rebuildable from S3 listing, slowly | **DynamoDB** `PK hash` | "Pure key-value at ten billion keys with no query I can't name — exactly DynamoDB's shape. Postgres would be a 1TB index I'd shard by hand for a lookup that has no joins" |
| Cursors | Point read/write per device per namespace | Low — a stale cursor re-syncs | Postgres, same shard | "Small, and co-located with the journal it points into" |
| Long-poll wakeup | Fan-out per namespace | None | **Redis pub/sub** | "A hint; the journal is the truth, and a missed hint costs one poll interval" |

**6. Year three.** Blocks: the bytes, in S3, forever, with refcount GC — the storage bill is this
table. The journal is unbounded per namespace but compactable to one row per live file; keep the
raw tail for 30 days for version history. The hot partition is a shared namespace with thousands of
members — every member's device polls it, which is why the wake-up is pub/sub and not a scan.

**Where they press.** The refcount GC race; why rename doesn't move bytes; what a device offline for
a month reads (the compacted journal, not a month of entries); large files (block list of 12,500
hashes for 50GB — fine as an array, or a separate blocks-of-file table past a threshold).

</details>

### J. MULTI-TENANT SAAS WITH SHARING

**Prompt.** A workspace product: tenants, users, documents, and sharing — with users, groups, and
links — where every request must be authorized in under 5 ms. Numbers given: 100k tenants, one
tenant has 200k users, 10B permission checks/day, a revoked share must stop working within a minute,
audit history is kept for compliance.

<details>
<summary><strong>Key — the six artifacts</strong></summary>

**1. Entities.** Tenant, User, Membership, Group, GroupMember, Resource (document, folder),
Permission (principal → resource → role), AuditEvent. Root: **the Tenant** — `tenant_id` is the
first column of every primary key, every index, every cache key, and the shard key. **A row that
doesn't carry it is a cross-tenant leak waiting to happen.**

**2. Access patterns.**

```text
R  can USER do ACTION on RESOURCE (in TENANT)                       hot    115k/s, < 5ms
R  resources shared with USER in TENANT, newest first               warm   "shared with me"
R  who has access to RESOURCE                                       warm   the share dialog
W  grant / revoke PERMISSION                                        cold   idempotent; revoke visible ≤ 60s
R  members of GROUP; groups of USER                                 warm   part of the check
W  append AUDIT event                                               hot    per mutation
R  audit for RESOURCE / TENANT in RANGE                             cold   compliance export
```

**3. Tables.**

```text
tenants           PG   PK tenant_id     plan, shard_hint         ← a whale can be pinned to its own shard
memberships       PG   PK (tenant_id, user_id)    role

resources         PG  sharded by tenant_id        PK (tenant_id, resource_id uuidv7)
  parent_id, owner_id, type, created_at            ← inheritance walks parent_id; depth capped at ~10

permissions       PG  same shard                  PK (tenant_id, resource_id, principal_type, principal_id)
  role enum(viewer|commenter|editor|owner), granted_by, granted_at
  IDX (tenant_id, principal_id, granted_at DESC)   ← R "shared with me" — the reverse index
  the PK *is* the grant, so grant and revoke are naturally idempotent

groups / group_members   PG  same shard           PK (tenant_id, group_id, user_id)
  IDX (tenant_id, user_id)                          ← "groups of user", read on every check

perm:{tenant}:{user}:{resource}   REDIS STRING = role, EX 60
  read on every check; a revoke DELs it (write-through) and the TTL bounds a missed delete at 60s
  derived — loss sends 115k/s to Postgres reads, which is survivable on replicas

audit             PG  partitioned by month        PK (tenant_id, event_id uuidv7)   actor, action, resource_id, at
  append-only; 90d hot, then S3 Parquet, 7y

DynamoDB variant: PK=TENANT#t#RES#r  SK=PRINCIPAL#type#id  (role)    GSI1 PK=TENANT#t#PRINCIPAL#id (shared-with-me)
```

**4. Invariants.** *Every query is scoped by tenant*: enforced structurally — `tenant_id` leads every
key, Postgres row-level security as a backstop, and in the DynamoDB variant the partition key
contains it so a query cannot omit it. *Revoke is visible within 60 s*: write-through delete plus the
TTL as the bound; say the number. *A check resolves in one shard*: user's groups, the resource's
ancestors, and the grants are all under the tenant. *Grant is idempotent*: the primary key is the
grant, so a retry is an upsert. If sharing must cross tenants, that is a new problem — say so rather
than quietly relaxing the key.

**5. Storage decisions.**

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| Resources, permissions, groups | Point reads and small joins by tenant, 115k checks/s | Absolute | **Postgres sharded by `tenant_id`** | "The check is a small join — user's groups, resource's ancestors, grants — and I want it on one shard with constraints. DynamoDB single-table does it too, and I'd choose it for zero-ops; I'd lose the ad-hoc admin queries and the inheritance walk becomes N `GetItem`s" |
| Permission cache | 115k/s point reads, sub-ms | Derived | **Redis**, 60s TTL, write-through delete on revoke | "The TTL is the revocation SLA stated as a number. Losing the cache means Postgres takes the reads — a latency cost, not a security one" |
| Audit log | Append-only, read by range, rarely | Compliance, 7 years | **Postgres monthly partitions → S3** | "Never read by the check path, so it's allowed to be slow and cheap" |
| Whale tenant | 200k users, most of the checks | Same as the rest | **Own shard**, by the `shard_hint` | "Tenant is the right key and it skews — so I pin the whale rather than hash across tenants, because hashing would put half a tenant's join on the wrong node" |

**6. Year three.** Audit is the unbounded table: partitioned by month, 90 days hot, seven years in
S3. Permissions are bounded by resources × principals. The hot partition is the whale tenant, and it
is handled by placement, not by key design — the same "isolation over evenness" argument as the
Ticketmaster shard.

**Where they press.** Group nesting depth and cycle prevention (cap it, or move to relation tuples
in the Zanzibar shape when nesting is unbounded); the cost of "shared with me" without the reverse
index; noisy-neighbor isolation for the whale; whether `tenant_id` in the key is enough or you need
row-level security too (both — one is structure, the other is a backstop).

</details>

---

## 07 — The drill

The three-minute API drill in `Client-Side System Design` is the cheapest rep on this site; this is
its data-model equivalent, and it is slightly longer because the artifact is bigger.

### A. THE REP

1. Pick a problem. Blank page — paper or an empty text file, not this guide.
2. Ten-minute timer. Run §02 in order and write the six artifacts in the §03 notation. If the timer
   goes before artifact 6, stop anyway; the miss is part of the score.
3. Open the key (or the design page's §12) and score yourself against the ten questions in §05 A.
4. Write down every question that scored 0 or 1, with one line on what the answer should have been.
   **That list, accumulated across reps, is the reading list** — not the whole guide again.

Ten minutes is the practice budget. The interview budget for the same six artifacts is about five,
spread across the round; the rep is deliberately twice as long because writing is slower than
speaking and because the point is completeness first, speed second.

### B. PROGRESSION

- **Week one:** models A–E in §06, one a day, with the key.
- **Week two:** models F–J.
- **Then:** re-run any problem whose miss list was not empty, until it is. Below 14/20 on a rep means
  the same problem again the next day, not a new one.
- **Then:** the cold queue below. No key on this page; compare against the design page where one
  exists, and against §05 alone where none does.
- **Standing:** one rep a week on any problem, cold, for as long as the loop is ahead of you. The
  skill decays in the same place it was hard to build — artifact 6 and question 8 go first.

### C. THE COLD QUEUE

Search and booking with date ranges (the Airbnb page) · IDE settings sync with layered precedence
(the settings-sync page) · an LLM chat product with streaming and conversation history (the ChatGPT
page) · usage metering that converges on an invoice (the billing page) · a notification system with
per-channel preferences and an inbox · a leaderboard with per-region and all-time views · ad-click
aggregation with dedupe and hourly rollups · video metadata and view counts at YouTube scale · a
job scheduler with retries, leases, and exactly-once execution · a document collaboration backend
with an op log (the Figma page, §12).

For each: ten minutes, the six artifacts, then the ten questions. The last four have no page on this
site and no key here; they are the honest test.

### D. THE OUT-LOUD VERSION

Once a written rep on an unseen problem lands at 18/20, change the medium: **five minutes, speaking,
drawing only the table blocks.** The interview is spoken, and the sentence that scores is the one in
the "What you say" column — *"I'm sharding for volume and buying colocation"*, *"the condition is
the correctness"*, *"a cache of a `SUM`, never paid out from."* Those sentences do not come out of a
written model on their own; they have to be rehearsed as speech.

---

## 08 — Lines worth rehearsing

Load-bearing sentences specific to data modeling. Have the shape ready; say them in your own words.

- *"Here are the reads and writes, with rates. The tables follow from this list, so if the list is
  wrong the model is wrong — let me get it right first."*
- *"This entity bounds the transaction, so it's the partition key. Throughput doesn't force me off
  it; if it did, I'd say what I'm giving up."*
- *"The index serves this read and costs that write. I'm leaving the other two reads unindexed on
  purpose — here's why they can afford a scan."*
- *"The database refuses the second one. I'd rather the constraint decide than the application win a
  race."*
- *"Inside the circle, one transaction on one shard. Outside it, eventual — by about two seconds, and
  here's who sees the stale read."*
- *"That field is a copy. It's owned there, propagated by the outbox, stale by under a second, and
  the nightly job repairs it."*
- *"In three years this table is N billion rows. Monthly partitions, ninety days hot, then Parquet in
  S3 — and this partition key skews, so here's the bucket that bounds it."*
- *"Postgres models this perfectly and I'd use it at a tenth of the scale. At this rate I want an LSM
  store, and I'm giving up the constraint I'd have leaned on — so here's the conditional write that
  replaces it."*
- *"Redis holds this because it's derived. Losing it costs one slow read per user. The one key whose
  loss isn't survivable is this counter, and here's how it recovers."*
- *"Expand, backfill idempotently, dual-read and verify, cut over, contract. The new key is a new
  table fed by CDC, and the old one stays until the reads are gone."*
