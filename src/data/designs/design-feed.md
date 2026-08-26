# Design Twitter — Read-Heavy Feed & Fanout

## The question

> *"Design the Twitter home timeline. You follow a few hundred accounts, you pull to refresh, and you get their recent posts, newest first."*

**The product.** People post short messages. People follow other people. Your home timeline is the merge of everything the accounts you follow have posted, newest first, and you pull to refresh it many times a day. Reading vastly outweighs posting.

The distribution is what makes it interesting. A typical person follows a couple hundred accounts and has a couple hundred followers — but a handful of accounts have tens or hundreds of millions of followers, and those accounts are not an edge case to handle later, they're the product's centre of gravity.

**What a working system delivers**

- Pull to refresh and posts are on screen in a couple hundred milliseconds, every single time.
- A post from someone you follow turns up within seconds of them posting it.
- Posting works identically whether you have twelve followers or a hundred million, and a celebrity posting doesn't slow down everyone else's app.
- Following someone new means their posts start appearing, without you having to reload the world.

**Why this gets asked.** There are exactly two obvious implementations — build everybody's timeline at the moment somebody posts, or assemble a timeline at the moment somebody reads — and the follower distribution above breaks each of them at a different end. Naming both and picking one is half the problem; knowing that neither survives on its own is the other half.

---

**Archetype:** read-heavy content distribution over a wildly skewed subscription graph.
**Cousins that reuse ~70% of this page:** Instagram feed, Facebook News Feed, LinkedIn, Reddit home, YouTube subscriptions, notification feeds, activity streams.

**What's actually being graded:** whether you reach for **fanout-on-write** and can say *why* — and then, the real test, whether you know that neither pure strategy survives the follower distribution, so the answer is a hybrid with a threshold you can defend. Candidates who name both strategies and pick one have done half the problem.

**Contrast to have ready — this is the inverse of the messaging page, deliberately:** *Messaging fans out on **read**: a reader pulls from ~10 conversations, so read-time merge is cheap and per-recipient copies would be waste. A feed fans out on **write**: a reader pulls from ~200 authors, so read-time merge is a 200-way query on every refresh. Same word, opposite answer. The deciding question is how many sources a single read has to merge.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "The write volume here is small — a few thousand tweets a second, which is nothing. What's large is the *amplification*: one tweet with 200 followers is 200 timeline updates, and one tweet from an account with 100M followers is 100M. So this is a fanout problem with an extremely skewed distribution, and the skew is what makes it interesting — the median account and the p99.999 account need different strategies. I'd like to scope to posting, the home timeline, and follow/unfollow, and go deep on the fanout hybrid and the timeline store. I'll name ranking, search, and media as subsystems and leave them out."

**Why open this way:** it establishes in one breath that you know the write path is trivial and the amplification isn't, and it pre-commits you to the hybrid before anyone can trap you into defending a pure strategy.

---

## 1 · Functional requirements

1. **Post a tweet.**
2. **Read a home timeline** — a reverse-chronological merge of the accounts you follow, paginated.
3. **Follow and unfollow** accounts.

**Out of scope (say them):** search, DMs, notifications, media upload, trends, ads, replies/threads.

**Below the line, likely follow-ups:** ML ranking instead of reverse-chron (§11 — the fanout design is unchanged, which is worth saying), deletes and privacy changes, blocked/muted accounts.

---

## 2 · Non-functional requirements

| Property | Target | Why |
|---|---|---|
| **Timeline read latency** | **p99 < 200ms** | It's the app's entire core loop. Everything else exists to protect this number |
| Availability | 99.99%, strongly favor availability | A missing tweet is a shrug; an unloadable timeline is an outage |
| Consistency | **Eventual, bounded ~seconds** for normal accounts | Nobody can detect that a tweet arrived 3s late. This is what buys you async fanout |
| Fanout completeness | Every follower eventually receives it | "Eventually" is doing real work for celebrity accounts — see §8 |
| Durability | Tweets: absolute. **Timelines: none — they're a cache** | The single most useful classification on this page (§9) |
| Scale | ~300M DAU, ~500M tweets/day, ~9B timeline reads/day | Drives §3 |

**The sentence that earns the point:** *"The timeline is a derived cache, not a system of record. It can be rebuilt at any time from tweets plus the follow graph, and treating it that way is what lets me lose it, cap it, skip it for inactive users, and repair it lazily."*

---

## 3 · Numbers that reframe the problem

**Global**

- 500M tweets/day ÷ 86,400 ≈ **6k writes/sec, ~15k peak.** Trivial. A single database could take this.
- 300M DAU × ~30 refreshes ≈ 9B timeline reads/day ≈ **100k reads/sec, ~300k peak.**
- Request-level read:write ratio is only ~17:1. **That is not where the asymmetry lives** — say this, because it pre-empts the assumption that a big ratio is the whole story.

**Amplification — the number that actually decides the design**

- Mean followers ≈ 200 (median is far lower; the mean is dragged by a long tail). **6k tweets/sec × 200 = ~1.2M timeline writes/sec, ~3M peak.**
- One 100M-follower account tweeting = **100M writes for a single post.** At a sustained 1M inserts/sec of fanout capacity, that's **~100 seconds to reach everyone** — so your followers see it at visibly different times.
- **The distribution is the problem, not the average.** Median account: 100 followers, fanout is free. p99.999 account: 100M followers, fanout is a small outage. One strategy cannot serve both, and saying that sentence is the pivot of the whole round.

**Per-shard / storage**

- Timeline store, materialized only for recently-active users: ~150M users × 400 entries × ~40B ≈ **2.4TB** — a Redis cluster of a few dozen nodes. Materializing all ~1.5B registered accounts at 800 entries would be ~15TB+ and mostly for people who will never log in. **Capping and skipping inactive users is what makes this affordable**, and both fall out of "the timeline is a cache."
- Follow graph: ~1.5B users × ~200 edges ≈ **300B edges**, stored twice (both directions, §10) ≈ 600B rows. This, not the tweets, is the large dataset.

---

## 4 · Core entities

- **User** — id, handle, profile, `follower_count`, `last_active_at`
- **Tweet** — **id (Snowflake)**, author_id, text, created_at, reply_to
- **Follow** — stored in **both directions** (§10): `following(user_id → followee_id)` and `followers(user_id → follower_id)`
- **Timeline** — `user_id → [tweet_id]`, capped, **a cache**
- **EngagementCounts** — tweet_id → likes, retweets, replies *(deliberately not in the timeline — §11)*

**Load-bearing details:**

- **Snowflake IDs are time-sortable 64-bit integers** (timestamp | machine | sequence). That single property means the tweet id *is* the sort key — no separate timestamp column, no clock-skew tie-breaking, and the timeline sorted set can score by id directly. **Compare the messaging page, which agonizes over whether its per-conversation `seq` needs to be *dense*. Here that question doesn't arise: a timeline reader can't detect a hole, so sortable is all you could ever use.** A thread reader can — `seq > local_max + 1` means something was missed — which is the one job that costs you a single writer. Same primitive, and the difference is what the reader can notice.
- **`follower_count` on the user row** is what routes an author down the normal or celebrity path (§8). It has to be cheap to read on every post, so it's denormalized and allowed to be slightly stale.
- **`last_active_at`** decides whether this user gets a materialized timeline at all.

---

## 5 · API

```
POST /v1/tweets                     → { tweetId, createdAt }
  body: { text }
  header: Idempotency-Key

GET  /v1/timeline?cursor=&limit=50  → { tweets: [...], nextCursor }

POST /v1/users/{id}/follow          → 204
DELETE /v1/users/{id}/follow        → 204
```

**Decisions to narrate, unprompted:**

- **Cursor pagination, never offset.** A feed is prepended to constantly, so `OFFSET 50` shifts underneath the reader — they see duplicates and miss items. The cursor is the last-seen Snowflake id, which is stable because ids are time-sortable and immutable. **This is the single most common API mistake on feed problems** and it costs nothing to get right.
- **`POST /tweets` returns as soon as the tweet is durable.** Fanout is asynchronous and explicitly not part of the response (§8). If you fan out synchronously, a celebrity's post request runs for a hundred seconds.
- **The timeline endpoint returns hydrated tweets, not ids**, but internally the timeline *is* ids — §11 covers why that indirection is deliberate rather than an inefficiency.

---

## 6 · High-level design — flows

```
                                        ┌──────────────┐
   POST /tweets ──▶ Tweet Service ──────▶  Tweet Store  │ (source of truth)
                         │              └──────────────┘
                         ▼ outbox
                       Kafka ──▶ Fanout Workers ──┬── normal author ──▶ Timeline Cache
                         │        (tiered queues) │                     (Redis zsets)
                         │                        └── celebrity ──▶ (skipped entirely)
                         ▼
                   Social Graph ("who follows X")

   GET /timeline ──▶ Timeline Service
                         ├── ZREVRANGE timeline:{user}          → ids
                         ├── + live query of followed celebrities → ids
                         ├── merge, dedupe, cap
                         └── hydrate ids → Tweet Cache, Author Cache, Counts Cache
```

**The two properties to point at:**

1. **The write path ends at the tweet store.** Everything after the outbox is asynchronous and best-effort, which is what keeps `POST /tweets` fast regardless of follower count.
2. **The read path merges two sources**, and that merge is the hybrid. A pure design would have one.

### Flow A — post and fan out

1. `POST /v1/tweets` with an idempotency key. Tweet Service assigns a **Snowflake id** and writes to the tweet store.
2. **Ack immediately.** The tweet is durable; everything downstream is delivery.
3. Outbox → Kafka. Fanout workers consume.
4. Worker reads the author's `follower_count` and routes: **below threshold → fan out; above → do nothing at all** (§8). The celebrity path is *the absence of work*, which is the elegant part.
5. Normal path: page through `followers(author_id)` from the graph store, in batches of ~1,000.
6. For each batch, filter to users **active in the last N days** — inactive users get no materialized timeline, which removes most of the write volume on a long-tail platform.
7. `ZADD timeline:{follower} {tweet_id} {tweet_id}` — score and member are both the Snowflake id, since it's time-sortable. Periodically `ZREMRANGEBYRANK` to cap at ~400.
8. Tiered queues by follower count so a 500k-follower account can't starve ordinary posts behind it (§8).
9. **Failure path — worker dies mid-fanout:** `ZADD` is idempotent by member, so replaying the batch is harmless. Restart from the last committed Kafka offset and re-fan the whole batch. **No checkpointing inside a batch is needed, because the operation is naturally idempotent** — worth designing for on purpose.
10. **Failure path — timeline cache node is down:** drop the writes for those users. The timeline is a cache; on read, a missing or cold timeline is rebuilt from the graph (§9). **Losing fanout writes degrades a timeline, it never loses a tweet.**

### Flow B — read a timeline

1. `GET /v1/timeline?cursor=`. Timeline Service reads `ZREVRANGEBYSCORE timeline:{user} {cursor} -inf LIMIT 0 50` → ~50 tweet ids.
2. In parallel, fetch the recent tweets of the **celebrities this user follows** — typically a handful of accounts, and their recent-tweets lists are cached so hard that millions of readers share one entry.
3. Merge both lists by id (time-sortable), dedupe, truncate to 50.
4. **Hydrate:** multi-get tweet bodies, author profiles, and engagement counts from their respective caches (§11). This is where the read cost actually is.
5. Filter at read time: deleted tweets, blocked/muted authors, protected accounts the reader can't see. **Doing this at read time rather than scrubbing timelines is what makes deletes cheap** (§9).
6. Return with `nextCursor` = the lowest id returned.
7. **Failure path — timeline is empty or cold** (new user, inactive returner, evicted key): fall back to read-time assembly — query recent tweets from everyone they follow, merge, and backfill the cache asynchronously. Slower, correct, and self-healing.
8. **Failure path — a hydration cache misses or a counts service is down:** serve the tweet with stale or omitted counts rather than failing the timeline. **Engagement counts are the most degradable thing on the screen**, and knowing what to shed under failure is the point.

---

## 7 · Deep dive — fanout-on-write vs fanout-on-read

### The two pure strategies

**Fanout-on-read (pull).** Store tweets by author. At read time, query the recent tweets of everyone the user follows and k-way merge.

- Write: one insert. Beautiful.
- Read: ~200 queries plus a merge, **on every single refresh**, at 300k reads/sec peak. That's 60M queries/sec against the tweet store.
- Verdict: **the read cost is paid over and over.** Fatal.

**Fanout-on-write (push).** At write time, insert the tweet id into every follower's materialized timeline.

- Write: ~200 inserts (1.2M/sec globally). Large but bounded and *asynchronous*.
- Read: one range read. ~1ms.
- Verdict: **correct default**, and the reason is one sentence — *a write happens once, a read happens every refresh, so precompute the thing that's read repeatedly.*

**The comparison that makes it obvious:** amortized over a tweet's life, fanout-on-write costs ~200 writes total. Fanout-on-read costs ~200 reads *per viewer per refresh* — thousands of times more work for the same tweet.

### Why the default is also the messaging page's answer inverted

Messaging concluded fanout-on-**read** using the same reasoning applied to different numbers. The variable that flips it is **how many sources one read must merge**: ~10 conversations (cheap merge, so don't precompute) versus ~200 followed accounts (expensive merge, so precompute). **State the variable, not the conclusion** — an interviewer who hears "feeds fan out on write" learns you memorized it; one who hears "merge width decides it" learns you understand it.

### Why neither pure strategy survives

Fanout-on-write breaks on the follower distribution. 100M followers = 100M writes for one tweet, ~100 seconds of fanout, and a queue that blocks everyone else's posts behind it. You cannot fix this by scaling the fanout tier — the work is inherently proportional to a number that has no upper bound.

**So: hybrid.** Push for normal accounts, pull for celebrities, merge at read time (Flow B steps 1–3). §8 works out the threshold.

---

## 8 · Deep dive — the celebrity problem and the hybrid threshold

### The insight that makes the hybrid cheap

The celebrity path is **not extra machinery — it's the removal of work.** Above the threshold, the fanout worker does nothing. The read path picks up the slack, and it does so almost for free, because **a celebrity's recent-tweets list is read by millions of people, so it has a near-perfect cache hit rate.** One cached list serves the entire audience.

That's the asymmetry to state out loud: *the accounts that are most expensive to push are exactly the accounts whose pull is most cacheable.* The follower distribution that creates the problem also creates the solution.

### Where to put the threshold

Not a magic number — a derivation:

- **Below ~10k followers**, fanout costs at most 10k writes, finishing in well under a second. Free.
- **Above ~1M followers**, fanout is minutes of work and a queue-monopolizing burst. Clearly pull.
- **In between**, it depends on how many of those followers are active and on your fanout headroom.

Land on **~100k as a starting threshold**, then say the two things that matter more than the number: it should be **per-author and dynamically adjustable** (so you can lower it under fanout backlog), and **hysteresis matters** — an account oscillating around the boundary shouldn't flip strategies repeatedly, because each flip leaves its tweets partially pushed and partially pulled.

**Cost, volunteered:** the read path is now a merge of two sources with different consistency characteristics, and celebrity tweets can appear *before* older normal tweets that are still mid-fanout. Users don't notice ordering anomalies of a few seconds. They would notice a 100-second gap, which is precisely what the hybrid avoids.

### Fanout mechanics for the accounts you do push

- **Tiered queues by follower count.** A 500k-follower account and a 200-follower account in one queue means the small account waits behind 500k inserts. Separate topics — small / medium / large — with independent worker pools so tail latency for ordinary posts stays flat.
- **Active-user filtering** (Flow A step 6) is the single biggest win: on a platform with 1.5B registered and 300M active accounts, most followers of most posts will never read them.
- **Idempotent inserts.** `ZADD` keyed by tweet id means replay is free, so crash recovery is "re-run the batch," with no intra-batch checkpointing.
- **Backpressure over dropping.** If fanout lags, let the queue grow and let reads fall back to pull for affected authors — degradation, not loss.

---

## 9 · Deep dive — the timeline store

### It is a cache, and everything follows from that

Say it before describing it: **the timeline is derived state, rebuildable at any time from tweets plus the follow graph.** That single classification licenses four things you'd otherwise have to justify separately:

1. **Cap it.** ~400 entries per user. Nobody scrolls past that in a session; beyond the cap you fall back to read-time assembly. Uncapped timelines grow without bound across 150M users.
2. **Skip inactive users.** No materialization for accounts that haven't logged in recently. They get read-time assembly on return, and a background backfill.
3. **Lose it safely.** A cache node failure degrades latency, never correctness (Flow A step 10).
4. **Never scrub it.** When a tweet is deleted or an account goes private, **do not** hunt through 100M timelines to remove ids — filter at read time (Flow B step 5). Deletes are rare and reads are filtered anyway for blocks and mutes, so the filter costs nothing extra.

Point four is the one candidates miss, and it's the most satisfying: **an expensive write-time cleanup problem disappears entirely by moving it to a read-time filter you were already performing.**

### Structure and sizing

| | |
|---|---|
| Structure | Redis **sorted set**, key `timeline:{user_id}`, member = `tweet_id`, score = `tweet_id` (Snowflake is time-sortable, so member and score are the same value) |
| Write | `ZADD timeline:{u} {tweet_id} {tweet_id}`, then `ZREMRANGEBYRANK timeline:{u} 0 -401` to cap |
| Read | `ZREVRANGEBYSCORE timeline:{u} ({cursor} -inf LIMIT 0 50` |
| Sizing | 150M active × 400 entries × ~40B ≈ **2.4TB** across a few dozen nodes |

**Why not Cassandra for timelines?** Cheaper per byte and durable — but you don't need durability (it's a cache) and you do need single-digit-millisecond reads on the app's hottest path. Paying Redis prices for the thing that defines your p99, while keeping the durable copy in a cheap store, is the right split. **Buy latency where latency is the product.**

---

## 10 · Deep dive — the follow graph

### Two access patterns, and a reverse index *is* a second copy

- **Fanout** needs `followers(author_id)` — "who should receive this?"
- **Read fallback and follow checks** need `following(user_id)` — "whose tweets do I want?"

One table serves one of these; the other becomes a full cluster scan.

**"Store it twice" and "build a reverse index" are the same thing**, and it's worth being precise about why, because the distinction people imagine doesn't exist in a partitioned store:

| Index type | How it works | Why it doesn't help |
|---|---|---|
| **Local secondary index** | Index lives inside each partition, alongside the data | Answering "who follows X" would still require hitting *every* partition and asking each one. You've turned one scan into thousands of small ones |
| **Global secondary index** | Index is partitioned by the *indexed* column | This works — and it works precisely because it **is a second copy of the edge, partitioned the other way.** DynamoDB GSIs and Cassandra materialized views are exactly this |

So the second copy isn't optional; **the only real question is who writes it — the database or you.**

**Here, write it yourself, and the deciding reason is specific to this page:** a 100M-follower list needs a bucketed partition key, `(author_id, bucket)` (below). An auto-maintained index gives you `author_id` and no say in the matter, so it recreates the unbounded partition you're trying to avoid. Custom physical layout is not something you can express through a managed index. Two secondary considerations reinforce it: Cassandra's materialized views have a long history of silent divergence and are widely avoided in production, and a DynamoDB GSI carries its own throughput budget that can throttle independently of the base table — during a fanout burst, exactly when you can least afford it.

**Making the double write safe:** don't write both tables and hope. Write the edge to the primary table plus an outbox record in one transaction, and let a worker apply the mirror. That's at-least-once with idempotent upserts, so the two directions converge without a reconciliation job doing the real work — the job becomes a safety net rather than the mechanism. A follow edge visible in one direction for a few seconds is invisible to users.

### The hot partition, again

An account with 100M followers is 100M rows under one partition key. **Same failure as the messaging page's years-long conversation** — and the same fix: bucket the partition key (`(author_id, bucket)`), and page through buckets during fanout rather than attempting one enormous scan.

**Note this is a partition *size* problem, not a rate problem** — the follow edges accumulated slowly over years. Write rate and partition size are independent risks, and this page has an extreme version of the second.

### How bucketing actually works

**Not every author gets multiple buckets.** Store `bucket_count` on the author row, defaulting to **1**. The ~99.9% of accounts with a few hundred followers have a single partition and never notice the mechanism exists. Bucketing is a tail feature that costs the median case nothing.

First, the thing I left undefined: **the "author row" is just the user's record** in the `users` table (`PK: user_id`) — the same row holding handle, profile, `follower_count`, and `last_active_at`. There's no separate metadata service.

| | |
|---|---|
| **Partition key** | `(author_id, bucket)` where `bucket` is an integer, `0 .. bucket_count-1` |
| **Write** | `n = INCR follow_seq:{author_id}` (atomic, monotonic, **never decremented**), then write the edge to `bucket = n / 50000` |
| **Read (fanout)** | `bucket_count = ceil(follow_seq / 50000)`, then query buckets `0 .. n-1` **in parallel**, streaming each into the fanout queue |
| **Read (point: does A follow B?)** | **Never touches this table.** It goes to the `following(A)` direction, which is small and unbucketed |

**Why a counter rather than "check whether the current bucket is full":** counting rows in a 50k-row partition is a scan, and you cannot afford one per follow. A single atomic increment gives you the position *and* the bucket in one operation, and the same counter tells readers how many buckets exist — so there's no separate `bucket_count` field to keep in sync. Put the counter wherever your atomic increment lives: Redis `INCR` is the obvious choice given it's already in the stack, and follows are low-volume (~10k/s globally) so it's nowhere near a hot key.

**And this is why the race you're describing disappears.** With "check size, then increment," two writers both observe bucket 3 as full, both increment, and you land at bucket 5 with bucket 4 empty — harmless, since readers query all buckets and an empty one returns nothing, but it's sloppy. With an atomic counter, two concurrent writers receive `n = 50000` and `n = 50001` and land **deterministically in the same bucket**. No jump, no gap, no coordination.

**The residual imperfection, which is genuinely fine:** a writer can take `n = 50001` and then crash before writing the edge, leaving that bucket one row short forever. And unfollows delete rows without decrementing the counter, so an old bucket may hold 40k live rows out of 50k ever issued. **Buckets get sparser over time and that's the end of it** — the counter tracks *edges ever created*, not edges currently alive, and only the former is safe to derive bucket boundaries from. Never decrement, never compact, never reuse.

**Why not `hash(follower_id) % N`?** It's the reflexive answer and it has a fatal flaw: **the moment you change N, every existing row hashes somewhere else.** You'd need a full migration to grow. Fixing N globally instead means a user with 50 followers is spread across N nearly-empty partitions and their fanout scan becomes N queries to collect 50 rows. Sequential fill-and-append avoids both — buckets are only created when earned, and existing rows never move.

**How the reader knows the count, for free:** fanout already reads the author row to check `follower_count` against the celebrity threshold (§8). `bucket_count` comes along in the same read. **No extra lookup, and no metadata service.**

**The safety asymmetry, which holds under either scheme:** **over-counting buckets is free, under-counting silently hides rows from readers.** A bucket readers don't know about is invisible followers who never receive the tweet — a correctness bug with no error message. So the counter only ever moves up, and any uncertainty resolves toward *more* buckets. *(Same reasoning as the admission watermark on the Ticketmaster page — when a counter can drift, work out which direction is survivable and bias there.)*

**The general rule, because the right scheme depends on the read pattern:**

| Read pattern | Bucket by | Example |
|---|---|---|
| Full scan of everything | Sequential fill-and-append — bucket identity is irrelevant | This page's follower lists |
| Newest-first range scan | **Time window**, and walk buckets backwards from newest | Messaging's conversation history |
| Point lookup by member | **Hash of the member**, so the bucket is computable without a lookup | Only viable when the bucket count is fixed |

**Choose the bucketing key to match how the partition is read**, not by habit. Sequential buckets would be wrong for message history (you'd have to scan every bucket to find the newest 50), and time buckets would be wrong here (a viral month produces one enormous bucket).

### Storage

Cassandra, partitioned by the owning user with bucketing for the tail. Twitter historically ran a purpose-built graph store (FlockDB) — worth naming to show awareness, but a wide-column store is the right general answer, and a graph database is *not*: you're doing single-hop adjacency lookups at massive scale, not traversals. **Graph databases earn their cost on multi-hop queries, and there are none here.**

---

## 11 · Deep dive — the read path: hydration is the real cost

The timeline read returns 50 ids in ~1ms. **That is not where your latency budget goes.** Turning 50 ids into a rendered feed requires:

- 50 tweet bodies
- ~50 author profiles (name, handle, avatar)
- 50 sets of engagement counts
- Per-viewer state: has this user liked/retweeted each one?

Four multi-gets, each fanning out across a cache cluster. **Say "the timeline lookup is cheap and hydration is the actual read cost"** — it reframes the whole read path and it's the part that most designs skip.

**Why ids and not denormalized content in the timeline:** storing the tweet body in every follower's timeline multiplies storage by ~200 and, worse, makes edits and deletes require rewriting millions of copies. **The indirection isn't inefficiency; it's what keeps mutable data in one place.** This is the same reasoning as the messaging page's fanout-on-read for content — store the thing once, reference it many times.

**Caching layers, from hottest:**

| Layer | Contents | TTL | Note |
|---|---|---|---|
| Tweet cache | id → body, author id | Long — tweets are immutable | Near-perfect hit rate; recent tweets are read by everyone |
| Author cache | id → profile | Minutes | Small dataset, enormous reuse |
| Counts | id → likes/retweets | Seconds | **Deliberately stale.** Counts change constantly and nobody can tell |
| Viewer state | (viewer, tweet) → liked? | Short | The only genuinely per-viewer fetch, and the least cacheable |

**Never bake counts into the timeline.** They mutate constantly; baking them in would mean rewriting timeline entries on every like — turning a read-mostly cache into a write-heavy one for data nobody perceives precisely.

**Ranking, if asked:** replacing reverse-chron with an ML-ranked feed changes the read path (fetch a larger candidate pool, score it, take the top 50) and **changes nothing about fanout.** The materialized timeline becomes a candidate source rather than the final answer. Say that — it shows you can separate the retrieval layer from the ranking layer, which is the actual architecture at every one of these companies.

---

## 12 · Data model, sharding, and storage decisions

**Shard tweets by `tweet_id`.** Snowflake ids distribute perfectly, every hydration lookup (§11) is a point read, and tweets are immutable so a partition never grows after it's written.

**Do not shard tweets by `author_id`** — the hedge that "either works" is wrong, for the reason that recurs across this whole family: a decade-old prolific account accumulates hundreds of thousands to millions of rows under one partition key, and you're back to the partition-*size* problem from §10. Write *rate* concentration is mild (even a very active human posts ~50/day), but size is unbounded, and size is the one that fails silently in year three.

**But there are two read patterns, so there are two tables.** Point-lookup-by-id can't answer "recent tweets by author X," which the celebrity pull path (Flow B step 2) and every profile page need:

| Table | Partition key | Serves |
|---|---|---|
| **Tweets** | `tweet_id` | Hydration — bulk point lookups of ~50 ids per timeline render |
| **Author timeline index** | `(author_id, time_bucket)`, clustering `tweet_id DESC` | "Recent tweets by X" — celebrity pull and profile pages |

**This is §10's lesson applied again:** a second access pattern over the same data means a second copy, physically partitioned to serve it. The index holds ids, not bodies, so it's small — and it's **time-bucketed rather than fill-and-append**, because the read is newest-first and you want to walk buckets backwards and stop early. That's the read-pattern rule from §10, and the two tables on this page land on opposite sides of it.

**Shard timelines by `user_id`** — every timeline operation is a single-key read or write.

There's no cross-shard transaction anywhere in this design, which is worth noticing out loud — **it's a direct consequence of accepting eventual consistency in §2.** Nothing needs to be atomic across entities, so partitioning is unusually free here compared to the inventory and messaging pages.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Tweet store** | Write-once, bulk point reads by id, never mutated | Absolute — the source of truth | **Cassandra**, `PK: tweet_id` (Snowflake) | "Immutable, keyed reads, massive volume. No updates means no LSM read penalty, and Snowflake ids distribute perfectly with no hot partition possible" |
| **Author timeline index** | Newest-first range scan by author | Rebuildable from the tweet store | **Cassandra**, `PK: (author_id, time_bucket)`, clustering `tweet_id DESC` | "The second access pattern needs a second physical layout. Ids only, time-bucketed so a prolific account's partition stays bounded and reads walk backwards from newest" |
| **Timeline cache** | `ZADD` at 3M/s peak, `ZREVRANGE` at 300k/s | **None — derived** | **Redis Cluster**, sorted set per user, capped at 400 | "It's a cache of a computation. Losing it costs latency, never data — which is what lets me cap it and skip inactive users" |
| **Follow graph** | Adjacency both directions, extreme partition skew | High | **Cassandra**, `PK: (user_id, bucket)` both directions | "Single-hop adjacency at scale, so a wide-column store, not a graph DB — there are no traversals to justify one" |
| **Tweet / author cache** | Read-mostly, immutable content, huge reuse | None | **Memcached** (or Redis) | "Memcached is the better fit for pure key-value with no data structures — simpler, lower memory overhead per entry, trivially shardable" |
| **Counts** | High-frequency increment, read constantly | Low — approximate is fine | **Redis `INCR`**, async-persisted to Cassandra | "Approximate counts are a product decision I'd make deliberately; exact like-counts are worth nothing and cost a lot" |
| **Fanout queue** | Ordered, replayable, tiered by author size | High, bounded | **Kafka**, separate topics per follower tier | "Tiering is what stops one celebrity post from starving every ordinary post behind it" |

**The one worth a sentence of tradeoff:** counts. Exact counts require a durable atomic increment per like, at like-volume, read on every timeline render. Approximate counts in Redis with periodic persistence cost a fraction and are indistinguishable to users. **This is a place where the "correct" engineering answer is worse than the deliberately sloppy one, and being able to say why is the point.**

---

## 13 · Traps — the ranked list

**Design traps**

1. **Picking a pure strategy.** Either one alone fails; the hybrid is the answer, and the threshold is the interesting part.
2. **Fanout-on-read as the default.** Right for messaging, wrong here. If you can't say *why* they differ (merge width), you've memorized rather than understood.
3. **Synchronous fanout in the write path.** A celebrity's `POST` runs for a hundred seconds.
4. **One fanout queue for all authors.** Big accounts starve small ones; tier by follower count.
5. **Scrubbing timelines on delete.** Filter at read time — you're already filtering for blocks and mutes.
6. **Materializing timelines for inactive users.** Most followers of most posts will never read them.
7. **Uncapped timelines.** Unbounded growth across 150M users.
8. **Offset pagination.** The feed shifts under the reader; use a Snowflake cursor.
9. **Storing tweet bodies in timelines.** ~200× storage, and edits/deletes become millions of rewrites.
10. **Baking engagement counts into the timeline.** Turns a read cache into a write-heavy one for data nobody perceives precisely.
11. **Storing the follow graph in one direction.** Fanout needs followers; read fallback needs following. Both, denormalized.
12. **Ignoring the 100M-row partition** on a celebrity's follower list. Bucket it.
13. **Reaching for a graph database.** Single-hop adjacency, no traversals — a wide-column store is correct.
14. **Treating the timeline as a system of record.** It's derived. Everything good on this page follows from that classification.

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific here:

15. **Naming both strategies and stopping.** "There's fanout-on-write and fanout-on-read" is table stakes. The signal is the threshold, the hysteresis, the tiered queues, and why the expensive-to-push accounts are the cheap-to-pull ones.

---

## 14 · The five-minute skeleton (draw this cold)

1. Writes are trivial (6k/s). **Amplification is the problem**: ×200 average, ×100M worst case.
2. Fanout-on-**write** by default — a write happens once, a read happens every refresh. *(Inverse of messaging; the deciding variable is merge width.)*
3. **Neither pure strategy works.** Hybrid: push below ~100k followers, pull above, merge at read.
4. Celebrity pull is nearly free because one cached recent-tweets list serves millions.
5. Async via Kafka, **tiered queues by follower count**, active-user filtering, idempotent `ZADD`.
6. Timeline = Redis sorted set, member and score both the Snowflake id, capped at ~400. **It's a cache.**
7. Therefore: skip inactive users, lose it safely, and **filter deletes at read time instead of scrubbing.**
8. Follow graph stored **both directions**, bucketed for 100M-follower partitions.
9. Read path: timeline lookup is ~1ms; **hydration is the real cost.** Ids not bodies; counts deliberately stale.
10. Cursor pagination on Snowflake ids, never offset.

---

## 15 · Variants — what actually changes

**The axis that governs this family: what determines the candidate set — the author's followers (push), the reader's subscriptions (pull), or a ranker (neither)?** As you move right, fanout stops being the problem and candidate generation becomes it.

| Problem | Candidate set from | What changes |
|---|---|---|
| **Instagram / Facebook feed** | Follow graph (push) | Essentially this page. Media makes hydration heavier; ranking sits on top |
| **LinkedIn feed** | Follow graph + connections | Lower volume, denser graph, ranking matters more than fanout |
| **Notifications** | A single recipient (push, N=1) | Fanout is trivial. The hard parts move to dedupe, batching ("3 people liked your post"), and delivery channels |
| **Reddit home** | Community membership + **global ranking per community** | **No per-user fanout at all.** One ranked list per subreddit, shared by everyone, personalized only by which subs you're in. Dramatically cheaper — the shared list is the whole trick |
| **RSS reader** | Reader's subscriptions (pure pull) | Client-side merge. The server has no idea who follows what |
| **TikTok For You** | **A ranker over a candidate pool** | The follow graph is nearly irrelevant. This is a recommendation system — candidate generation, embedding retrieval, and ranking — with no fanout problem at all |

**The lesson:** fanout is only a problem when the audience is *known at write time and large*. Remove either property — Reddit shares one list, TikTok doesn't know the audience, RSS makes the client do it — and this page's central difficulty evaporates.

---

## 16 · Active recall — answer these cold, no scrolling

**Protocol:** out loud, in full sentences. Check the pointer only after attempting. Schedule in `00-interview-mechanics.md` §8.

| # | Prompt | Check |
|---|---|---|
| 1 | Write volume is only 6k/s. So what exactly is the scaling problem? | §3 |
| 2 | Why is the request-level read:write ratio *not* the important asymmetry? | §3 |
| 3 | State the one-sentence reason fanout-on-write beats fanout-on-read. | §7 |
| 4 | Messaging chose fanout-on-read. Name the variable that flips the answer. | §7 |
| 5 | Why does pure fanout-on-write fail, and why can't more fanout capacity fix it? | §7 |
| 6 | Why is the celebrity pull path nearly free? State the asymmetry. | §8 |
| 7 | Derive a threshold. What two things matter more than the number itself? | §8 |
| 8 | What goes wrong if an account oscillates around the threshold? | §8 |
| 9 | Why tier the fanout queues? What's the failure without it? | §8 |
| 10 | A tweet is deleted. What do you do to the 100M timelines containing it, and why? | §9 |
| 11 | Name four things that "the timeline is a cache" licenses you to do. | §9 |
| 12 | Give the exact Redis structure: key, member, score, and the write and read commands. | §9 |
| 13 | Why is the score the same value as the member? What property makes that work? | §4, §9 |
| 14 | "Why store it twice instead of just building a reverse index?" Answer the question as posed. | §10 |
| 14b | Local vs global secondary index: why does only one of them help, and what is it actually made of? | §10 |
| 14c | What specific requirement on this page rules out a managed secondary index? | §10 |
| 14d | How does a reader know how many buckets an author has, without an extra lookup? | §10 |
| 14e | Why not `hash(follower_id) % N` for bucketing? Give both failure modes. | §10 |
| 14f | Why can't you decide bucket boundaries by checking whether the current bucket is full? | §10 |
| 14g | With an atomic counter, what happens when two follows race at the 50k boundary? | §10 |
| 14h | Unfollows never decrement the counter. What's the consequence, and why is it acceptable? | §10 |
| 15 | Why not a graph database for the follow graph? | §10 |
| 16 | Timeline lookup takes ~1ms. Where does the read latency budget actually go? | §11 |
| 17 | Why store ids rather than tweet bodies in the timeline? Give both reasons. | §11 |
| 18 | Why are engagement counts deliberately stale, and why never in the timeline? | §11, §12 |
| 19 | Why is offset pagination wrong here specifically? | §5 |
| 20 | Switching to ML ranking — what changes and what doesn't? | §11 |
| 21 | Reddit's home feed avoids this page's central problem. How? | §15 |
| 22 | Why does this design have no cross-shard transactions anywhere? | §12 |
| 23 | Why shard tweets by `tweet_id` and not `author_id`? Which kind of risk decides it? | §12 |
| 24 | Two tables hold tweet data, bucketed differently. Name both schemes and why each fits its read. | §10, §12 |
