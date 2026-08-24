# Design Discord — Persistent Connections and Guild Fanout

## The question

> *"Design Discord. Communities are organized into servers and channels, people leave the app open all day, and a busy channel can have tens of thousands of members watching it at the same moment."*

**The product.** Persistent group chat. You join a server — a gaming community, a company, a fandom — and inside it are channels you can read and post to. Unlike a messaging app, you don't open it to check messages and close it; it sits open in a tab for hours. Alongside the messages you see who's online, who's typing right now, and who's sitting in a voice channel. A large server's `#general` has thousands of people connected to it simultaneously.

**What a working system delivers**

- A message typed into a busy channel is on everyone else's screen before the sender has finished typing the next one.
- You can see at a glance who's around, and that dot flips the moment somebody closes their laptop.
- Closing a lid and reopening it doesn't lose the last ten minutes of a conversation.
- Scrolling back through a channel's history is instant, even years back.

**Why this gets asked.** It is the same archetype as WhatsApp with the constraint inverted: the recipients are already connected, so a single write has to become tens of thousands of socket writes in a few milliseconds. And presence — the little green dots — generates far more traffic than the messages do, which almost every candidate scopes out.

---

**Archetype:** real-time messaging & delivery, in the regime where **the recipients are already connected**. The cost is not storing the message or ordering it; it is that one write must reach tens of thousands of live sockets before the sender finishes typing the next one.
**Cousins that reuse ~70% of this page:** Slack, Twitch chat, IRC, Matrix, a live-ops event bus, a multiplayer game lobby, a trading-floor broadcast. Also **any product where a client holds a socket open for hours and expects to be pushed to**.

**What's actually being graded:** whether you notice that **ingest is trivial and fanout is not**. Discord's message write rate is unremarkable — a few tens of thousands per second — and every candidate who spends the round sharding the message table has designed the easy half. The interesting numbers are the *connection* count and the *delivery* count, and they are two and three orders of magnitude larger. The second signal is **presence**: it is the highest-volume event type in the system, it is almost always scoped out by candidates, and scoping it out is the wrong call because it is what makes the connection stateful in the first place.

**Contrast to have ready:** *WhatsApp is the same archetype with the opposite constraint. There, recipients are mostly **offline**, fanout is to a handful of devices, and the hard problems are delivery semantics, ordering, and the catch-up queue. Here recipients are **online right now**, fanout is to thousands, and the hard problem is that a single message becomes fifty thousand socket writes. WhatsApp's answer — durable per-recipient queues — is actively wrong at this fanout, because you would be writing fifty thousand queue entries for a message that fifty thousand people are already holding a socket open to receive.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "Discord is several products on one connection — text channels, voice, presence, roles and permissions, search. I'd like to scope to **text messaging plus presence over a persistent gateway**, because that's where the constraint lives. Two things dominate. First, **the recipients are already connected**, so this is not a mailbox problem — a message published to a channel has to become socket writes to everyone in that channel who is online *now*, and the fanout ratio, not the write rate, is what sizes the system. Second, **the connection is stateful and long-lived**, which means the interesting failures are not slow queries, they're a deploy dropping four million sockets at once and every one of them reconnecting with a full state resync. I'll go deep on channel fanout and on presence, because presence is the highest-volume event type here and it's the one people scope out."

**Why open this way:** it names the inversion against WhatsApp before the interviewer can steer you into a mailbox design, and it pre-commits the two dives that carry the round. It also plants "thundering-herd reconnect" early, which is where the good version of this conversation ends up.

---

## 1 · Functional requirements

1. **A user opens a client and receives, in real time, messages sent to any channel they can see** — across every guild they are a member of, over one connection.
2. **A user sends a message to a channel; it is durably stored and delivered to every online member of that channel.**
3. **A user's online/offline status propagates to everyone who would care** — which is every member of every guild they belong to.

**Explicitly out of scope, said out loud:** voice and video (a different system entirely — an SFU, not this pipeline) · search · roles and permission *administration*, though permission *evaluation* stays because it gates fanout · moderation · attachments beyond "they are an object store URL in the message body."

**Below the line, likely follow-ups:** unread counts and read state (`§10`) · message edit and delete · typing indicators · mobile push for offline users · very large guilds as a distinct tier (`§8`).

---

## 2 · Non-functional requirements

| Requirement | Number | Justification |
|---|---|---|
| Delivery latency, sender to online recipient | **p99 < 500 ms** | Below the threshold where a conversation stops feeling live. It is a chat product; this is the product |
| Peak concurrent connections | **~15 M** *(assumption)* | Sizes the gateway fleet and makes connection state the dominant cost line |
| Message durability | **No acknowledged message may be lost** | Users scroll back years. This is the one place where availability yields to durability |
| Ordering | **Per channel, total order. Cross-channel, none** | A channel is the unit people read. Global ordering would buy nothing and cost coordination |
| Availability | **Reads and sends stay up under a single-AZ loss** | Degrade presence before degrading messages |
| Reconnect storm capacity | **A whole gateway node's clients reconnect within 60 s without cascading** | Deploys happen; this is the routine failure, not the exotic one |
| History read latency | **p99 < 200 ms for a channel's last 50** | It is on the open-a-channel path, which is the most frequent read in the product |

**The sentence that earns the point:** *"The only hard consistency requirement here is per-channel ordering, and I get it for free by having a single writer per channel — everything else, including presence and read state, is allowed to be eventually consistent, and I'm going to spend that slack deliberately."*

---

## 3 · Numbers that reframe the problem

- **~15 M concurrent connections at peak** *(assumption)*. At even 10 KB of per-connection state that is 150 GB of RAM across the fleet before a single message moves. **Connections, not messages, size the gateway.**
- **~4 B messages/day** *(assumption)* ≈ **46 k/s average, call it 150 k/s peak**. That is a *small* write rate — a single well-partitioned cluster handles it. **This is the number that misleads people.**
- **The fanout ratio is the real number.** A message in a channel with 5 000 online members is **5 000 socket writes**. Across the system, deliveries run one to two orders of magnitude above sends — call it **5–15 M deliveries/s at peak**. Every architectural decision on this page follows from that ratio and not from the 150 k/s.
- **Presence outruns messages.** One user coming online, in 20 guilds averaging 2 000 online members, is **40 000 delivery events** from a single state change. Multiply by login churn and presence is plausibly the **highest-volume event type in the system**. *(Reasoned inference, flagged as such — the multiplier is arithmetic, the claim that it exceeds messages is mine.)*
- **Trillions of messages stored**, on a cluster that went from **177 Cassandra nodes to 72 ScyllaDB nodes** — publicly reported by Discord, and the migration was driven by **GC pause latency**, not by throughput or capacity.
- **Guild size is wildly skewed.** The median guild is a few dozen people; the largest run to hundreds of thousands. **A uniform design is therefore wrong at one end or the other**, which is what `§8` is about.

---

## 4 · Core entities

**User** · **Guild** (a server, in product language) · **Channel** · **Message** · **Session** (one connected client) · **Presence** · **ReadState**.

Fields only where the field carries a decision:

- **Message** — `id` is a **Snowflake**: a 64-bit id whose high bits are a timestamp. It sorts by time, it carries its own creation time, and it can be minted without a round trip. Also `channel_id`, `author_id`, `content`, `edited_at`.
- **Session** — `session_id`, `user_id`, the gateway node holding it, a **resume token**, and the last sequence number the client acknowledged. The resume token is what turns a reconnect from a full resync into a replay.
- **Presence** — `user_id`, `status`, `last_heartbeat`. **It has a TTL and no delete path**; a session that stops heartbeating expires rather than being cleaned up, because the common way a session ends is that its node died.

**The three load-bearing ones.** **Session** is load-bearing because it is the only entity whose count is 15 M and whose state must be reconstructible after its host disappears. **Channel** is load-bearing because it is the unit of both ordering and fanout — the same key partitions the message table and addresses the pub/sub topic, and that is not a coincidence, it is the design. **Presence** is load-bearing because it is the highest-volume entity and the only one where the correct answer is to be deliberately lossy.

---

## 5 · API

Two surfaces, and the split between them is the design.

```text
# HTTP — everything that is a request/response
POST /channels/{channel_id}/messages    { content, nonce }        -> Message
GET  /channels/{channel_id}/messages?before={message_id}&limit=50 -> [Message]
PUT  /channels/{channel_id}/read        { last_message_id }       -> 204

# WebSocket — everything that is a push
->  IDENTIFY   { token, intents }                 # client opens, declares what it wants
<-  READY      { session_id, resume_token, guilds, seq }
<-  DISPATCH   { seq, type: "MESSAGE_CREATE", d }  # every push carries a monotonic seq
<-  DISPATCH   { seq, type: "PRESENCE_UPDATE", d }
->  HEARTBEAT  { seq }                             # client's last seen seq, every ~40 s
<-  HEARTBEAT_ACK
->  RESUME     { session_id, resume_token, seq }   # after a drop: replay from seq
```

**Decisions to narrate, unprompted.**

- **Sends go over HTTP, not the socket.** They are request/response, they need a status code, and they are rate limited per route. Pushing them down the WebSocket would mean building request correlation, error semantics, and retry over a transport that has none. **The socket is for the thing HTTP cannot do**, which is push.
- **`nonce` on send, echoed back in the dispatch.** It is a client-supplied idempotency key: the client renders the message optimistically, and when the dispatch arrives it matches on `nonce` rather than duplicating. It also makes a retried send safe after a timeout.
- **Every push carries a monotonic `seq`, and the client heartbeats its last seen one.** This is what makes `RESUME` possible — the server knows exactly what the client missed. **Without a sequence number, every reconnect is a full state resync, and `§7` explains why that is fatal at this connection count.**
- **`intents` on identify.** The client declares which event classes it wants. Presence is by far the most expensive stream, and letting a client that does not render presence opt out of it is a cheap and very large saving.

---

## 6 · High-level design — flows

```text
                    ┌───────────────┐
  HTTP send ───────►│  API service  │──── write ───►  Message store (ScyllaDB)
                    └───────┬───────┘
                            │ publish(channel_id)
                            ▼
                  ┌─────────────────────┐
                  │  Guild/channel      │   one owner per guild; holds the
                  │  process (BEAM)     │   subscriber list for its channels
                  └──────────┬──────────┘
                             │ fanout to sessions
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Gateway  │   │ Gateway  │   │ Gateway  │  ~15M sockets total
        │  node    │   │  node    │   │  node    │
        └────┬─────┘   └────┬─────┘   └────┬─────┘
             │ WebSocket    │              │
           clients        clients        clients

  Session registry (Redis, heartbeat TTL) ── who is where, for routing and presence
```

### Flow A — sending a message

1. Client `POST`s to the API service with a `nonce`.
2. API evaluates permissions for `(user, channel)` and rejects if not allowed. **This is on the write path deliberately** — evaluating per recipient at fanout time would multiply the check by the fanout ratio.
3. API mints a Snowflake `id` and writes to the message store, partitioned by `(channel_id, bucket)` — `§12`.
4. On a successful write, API publishes to the guild's process.
5. The guild process resolves the channel's **online** members, groups them by gateway node, and sends one batched message per node rather than one per session — `§8`.
6. Each gateway node writes `MESSAGE_CREATE` to its local sockets, stamping each with that session's next `seq`.
7. **Failure path:** the store write succeeds and the publish fails. The message exists and nobody was told. Clients recover on their own — the next `RESUME` or channel open reads from the store, which is the source of truth, and the push is an optimisation over it. **The inverse ordering would be unrecoverable**, so publish never precedes the write.

### Flow B — connecting, and reconnecting

1. Client opens a WebSocket to a gateway node and sends `IDENTIFY`.
2. Gateway authenticates, creates a session, registers it in the session registry with a heartbeat TTL, and subscribes the session to its guilds' processes.
3. Gateway sends `READY` with a resume token and the guild list, then backfills.
4. Client heartbeats every ~40 s with its last `seq`.
5. **Failure path — the node dies.** Sessions are not migrated; they are abandoned. Their registry entries expire by TTL, which is what makes their users appear offline without anyone running a cleanup. Clients notice a dead heartbeat and reconnect **with backoff and jitter**, and `RESUME` replays from a short-lived per-session buffer instead of resyncing — `§7`.

### Flow C — presence

1. A session heartbeats; the gateway refreshes the registry TTL.
2. On a *change* — connect, disconnect, or an explicit status set — the gateway publishes a presence event to each of that user's guild processes.
3. Each guild process fans it out **coalesced and rate-limited**, not immediately — `§9`.
4. **Failure path:** a user's laptop sleeps. No FIN arrives, so nothing announces the departure; the registry entry simply expires and the guild process emits the offline transition when it notices. **Nothing happens promptly, and that is correct** — a presence system that requires a clean disconnect is a presence system that is permanently wrong.

---

## 7 · Deep dive — the gateway, and why reconnect is the real load

**The obvious answer:** put the sockets behind a load balancer, keep session state on the node, and if a node dies its clients reconnect and get a fresh session. Connections are cheap; the kernel will hold a million of them.

**What breaks.** Connections are cheap; **reconnects are not**. A `READY` payload is large — guild list, channel list, member and role data, initial presence — and it costs a burst of reads and serialisation. Dropping one node's share of 15 M clients means several hundred thousand simultaneous `IDENTIFY`s, each demanding the most expensive response the system produces. That is a **thundering herd against your own cold path**, and because deploys are routine, it is a load you will impose on yourself weekly. The naive design's failure mode is that a routine deploy looks exactly like an outage, and worse, the retry storm keeps the fleet from coming back.

**What replaces it.** Three things, in order of leverage:

1. **Resumable sessions.** Every dispatch carries a `seq`; the gateway keeps a short replay buffer per session, and `RESUME` replays the gap. A reconnect within the buffer window costs a few kilobytes instead of a full `READY`. **This converts the herd from expensive to cheap without reducing its size**, which is the right order to attack it in.
2. **Client-side backoff with jitter, and a server-side hint.** The close frame carries a reconnect delay. Without jitter, every client reconnects at the same instant and you have rebuilt the herd on a timer.
3. **Rolling drains, not restarts.** Take a node out of rotation, close its sessions in batches with a resumable close code, and let them land elsewhere over a minute rather than a millisecond.

**What it costs.** Replay buffers are memory you hold for clients that are not connected — bounded, but real, and the window is a tunable that trades memory against how many reconnects stay cheap. Resumability also means the gateway must be able to reconstruct or route a session that identified against a *different* node, which is why the session registry is a shared store rather than node-local. And the sequence number is now a correctness-critical field: a bug that skips one causes silent, permanent message loss for that client until they fully resync.

---

## 8 · Deep dive — fanout, and why the feed answer is wrong here

**The obvious answer:** treat it like a feed. Fan out on write to a per-user inbox, so a read is a single-partition scan of your own timeline.

**What breaks.** Per-user inboxes are for readers who are *absent* — the whole point is materialising the read before it happens. Here, the readers are **already connected and holding a socket open**. Writing 50 000 inbox rows so that 50 000 people who are online right now can each read one of them is pure write amplification, and at a 5–15 M deliveries/s system rate it is the dominant cost in the design for no benefit. Worse, it puts a durable write on the latency path of a live message.

**What replaces it.** **Fan out to sessions, not to storage.** The message is written once, to the channel's partition. Delivery is a pub/sub push to the sockets that exist at that instant. Two refinements do the actual work:

- **One owner per guild.** A single process holds the guild's channel-subscriber lists, which is what makes "who is online in this channel" a local set read rather than a distributed query. It also gives the per-channel total ordering in `§2` for free, because there is one writer.
- **Batch by node, not by session.** The guild process groups recipients by which gateway node holds them and sends **one message per node** carrying a recipient list. A 50 000-recipient fanout across a 500-node fleet becomes 500 inter-service messages, not 50 000. **This is the single highest-leverage optimisation on the page**, and it works because the guild process already knows the mapping from the session registry.

**And the hot-guild tier.** The skew in `§3` means a uniform design is wrong somewhere. A guild with 500 000 members cannot be one process on one host — its fanout alone saturates a NIC. Large guilds get sharded fanout: the subscriber set is partitioned across several processes, each responsible for a slice, with the publish going to all of them. **Say explicitly that this is a *tier*, not the general case**, because paying its complexity for the median guild of forty people is the classic over-design here.

**What it costs.** No durable inbox means **a message sent while you are offline is never pushed to you** — you get it when you next open the channel and read from the store. That is fine for chat and would be wrong for anything requiring guaranteed per-recipient delivery, and it is why mobile push notifications are a genuinely separate pipeline rather than a flag on this one. Guild ownership also introduces a single point of failure per guild: if that process dies, the guild is undeliverable until it is restarted elsewhere, which is a real availability tradeoff bought in exchange for ordering and locality.

---

## 9 · Deep dive — presence, the expensive part nobody scopes

**The obvious answer:** presence is a boolean in a table; when it changes, tell everyone who cares.

**What breaks.** The arithmetic in `§3`. One user in 20 guilds averaging 2 000 online members produces **40 000 delivery events from one bit flipping** — and users flip that bit constantly, because laptops sleep, phones background, and networks change. Presence is not a small feature attached to messaging; **it is plausibly the largest event stream in the system**, and treating it with messaging's delivery guarantees means paying messaging's cost for data that is stale a second later.

**What replaces it.** Three moves, and all three are deliberate lossiness:

1. **Heartbeat with TTL, never an explicit delete.** Online is "has heartbeated within the window." This is not an optimisation, it is the only correct model: the common way a session ends is that its host disappears, and a design that requires a clean goodbye is permanently wrong about a fraction of its users.
2. **Coalesce and rate-limit at the guild process.** Presence changes within a window collapse to one event; a flapping user produces one transition, not thirty. **A stale presence is invisible to users; a presence storm is not.**
3. **Do not send what nobody will render.** A client showing a 200 000-member guild is not rendering 200 000 avatars — it renders a screenful and asks for the rest. So presence for large guilds is **lazy and scoped to what the client has asked for**, which is what the `intents` field in `§5` exists to express.

**What it costs.** Presence is now **eventually consistent and briefly wrong** — someone can appear online for up to the TTL after they vanish. That is the correct trade and it should be stated as one: *"I'm choosing to be wrong about presence for up to thirty seconds in exchange for not paying messaging's delivery cost on the highest-volume event in the system."* Lazy presence also means the client's view depends on what it has subscribed to, which makes "why does my friend show offline here and online there" a real, and acceptable, support burden.

---

## 10 · Deep dive — read state, and the write amplification it hides

**The obvious answer:** store the last-read message id per user per channel, and update it when they read.

**What breaks.** The cardinality. **Read state is per user per channel**, so it is the largest table in the product by row count — larger than messages — and it is written far more often than it is read, because every channel switch and every scroll-to-bottom is a write. It is also latency-sensitive in a way messages are not: unread badges are the first thing rendered, so a slow read state read is a slow app launch, on every launch.

**What replaces it.**

- **Store the last-read `message_id`, not a count.** Because ids are Snowflakes, "unread" is a comparison and "how many unread" is a bounded count against the channel partition — no counter to keep consistent, and no drift.
- **Write behind, aggressively.** Read state updates are coalesced per user over a few seconds and batched. Losing the last few seconds of read state on a crash costs a user one already-read channel showing a badge, which is the cheapest possible failure in this system.
- **Put a coalescing cache in front of the hot path.** When a large number of clients request the same hot partition simultaneously, the service in front should recognise them as **one** request, issue a single query, and fan the single result back to every waiter. Discord's published data-services layer does exactly this in front of ScyllaDB — and it is worth naming because it is the same shape as `§8`'s fanout: many waiters, one source, one distribution loop.

**What it costs.** Write-behind means read state is eventually consistent across a user's own devices, so a channel read on a phone may stay unread on a desktop for a few seconds. Coalescing adds a latency floor equal to the batch window and turns a single slow query into a slow query for every coalesced waiter — a correlated failure you did not have before, and one worth mentioning before the interviewer finds it.

---

## 11 · Deep dive — message storage, and a migration that was about pauses

**The obvious answer:** a relational store, partitioned by channel, with an index on time.

**What breaks.** At trillions of rows the access pattern is narrow and brutal: **always a range scan over one channel, always descending by id, almost always the most recent page**. That is a wide-column workload, and a relational store's generality is cost you pay without using. Discord's actual path was MongoDB → Cassandra → ScyllaDB, and the reported reason for the last hop is the one worth remembering: **Java garbage-collection pauses showed up in tail latency** at that scale. The cluster went from **177 Cassandra nodes to 72 ScyllaDB nodes**.

**What replaces it.** **ScyllaDB, partitioned by `(channel_id, bucket)`**, where `bucket` is a coarse time window, clustered by `message_id` descending.

- **Why a compound key rather than `channel_id` alone.** A busy channel would otherwise grow one partition without bound, and an unbounded partition is the failure mode this class of store punishes hardest. Bucketing caps partition size and makes "the most recent page" a single-partition read of the newest bucket.
- **Why the bucket must be *coarse*.** Too fine and reading a quiet channel's last fifty messages means scanning many empty buckets. The bucket width is a tuning knob against the channel's message rate, and getting it wrong in either direction is a real, observable regression.
- **Why Snowflake ids make this work.** The clustering key already encodes time, so pagination is `WHERE message_id < ?` with no secondary index and no separate sort.

**What it costs.** Wide-column means **no joins and no ad-hoc queries** — every access pattern must be designed in advance, and a new one means a new table and a backfill. Search is therefore a separate system entirely, fed asynchronously. And the migration itself is the honest expense: dual-writing, historical backfill, and a verified cutover, which Discord did without downtime and which is weeks of work, not a config change.

---

## 12 · Data model, sharding, and storage decisions

**Partition key: `(channel_id, bucket)`.** Chosen because every read is scoped to one channel and ordered by time, and because `channel_id` alone grows without bound on exactly the channels you can least afford to be slow on.

**The hot-shard consequence, and whether it is intentional.** A single very busy channel concentrates writes on one partition at a time — the newest bucket. **This is intentional and acceptable**, because 150 k/s across the whole system means even a pathologically hot channel is a few thousand writes per second, which a single partition handles. It would stop being acceptable if the write rate were two orders of magnitude higher, and the fix would be a synthetic sub-key within the bucket, paid for with a merge on read.

| Component | Access pattern | Durability | Choice | The one sentence you'd say |
|---|---|---|---|---|
| Messages | Range scan by channel, newest first | Must not lose an ack'd write | **ScyllaDB**, `PRIMARY KEY ((channel_id, bucket), message_id)` desc | *"Wide-column because the access pattern is one narrow scan; Scylla specifically because GC pauses were the reported problem at this scale."* |
| Session registry | Point read and write, 15 M keys, high churn | **Losing it is survivable** | **Redis Cluster**, key `session:{id}`, heartbeat `EXPIRE` | *"TTL is the design, not a cleanup — a dead node's sessions have to expire, because nothing is alive to delete them."* |
| Presence | Same keys as sessions, read on fanout | Explicitly lossy | **Redis**, same heartbeat TTL, coalesced at the guild process | *"Presence is derived from the session TTL rather than stored separately, so there's one source of truth about liveness."* |
| Guild/channel metadata, roles | Small, read-heavy, read on every permission check | Must be correct | **Postgres**, cached aggressively at the API tier | *"Small, relational, and correctness-critical — this is the part that actually is a database problem."* |
| Read state | Per user per channel, write-heavy | Losing seconds is fine | **ScyllaDB**, `PRIMARY KEY (user_id, channel_id)`, write-behind | *"Biggest table in the product by rows, and the one where I'd trade durability for write cost first."* |
| Attachments | Write once, read many, large | Durable | **S3 + CDN**, URL in the message body | *"The message row carries a pointer; bytes never go through the gateway."* |
| Inter-service fanout | Publish to a topic per guild | In-memory, at most once | **The guild process itself**, over the cluster's own messaging | *"There's no broker in the delivery path — a broker would add a durable hop to something that is explicitly not durable."* |

---

## 13 · Traps — the ranked list

**Design traps.**

1. **Designing the message table for twenty minutes.** It is the easy half, the numbers say so, and it is the single most common way this round goes shallow. Get to fanout.
2. **Reaching for per-user inbox fanout-on-write.** It is the right answer for feeds and for WhatsApp and it is wrong here, for the reason in `§8`. Reciting it unprompted signals a memorised pattern rather than a read of the constraints.
3. **Scoping presence out.** It is the highest-volume event stream in the system. Scoping it out removes the most interesting part of the design and, worse, makes the connection look stateless when its statefulness is the whole point.
4. **Treating a deploy as an exotic failure.** Reconnect storms are the routine load. A design with no answer for "you just restarted a node holding 30 000 sockets" has not thought about operating the thing.
5. **A uniform design across guild sizes.** The skew is three orders of magnitude. Either the median guild pays for machinery it does not need, or the largest guild falls over. Name the tier.
6. **Putting permission evaluation on the fanout path.** It multiplies the check by the fanout ratio. Evaluate once, on write.

**Performance traps.**

7. **Fanning out per session instead of per node.** Correct, and it is a 100× difference in inter-service messages.
8. **A full `READY` on every reconnect.** Without `RESUME`, the cheapest event in the system becomes the most expensive.
9. **No jitter on client backoff.** You have rebuilt the thundering herd, on a schedule, with your own client code.
10. **An unbounded partition for a busy channel.** The bucket in the partition key is the whole answer, and forgetting it is invisible until it is not.

Interview-performance traps live in `Interview mechanics` — see that page rather than this one.

---

## 14 · The five-minute skeleton (draw this cold)

1. Clients hold **one WebSocket** to a **gateway node**. ~15 M concurrent. Sessions are registered in **Redis with a heartbeat TTL**.
2. Sends go over **HTTP** to an **API service**, not over the socket. Request/response wants status codes and rate limits.
3. API **evaluates permissions once**, mints a **Snowflake id**, writes to **ScyllaDB** partitioned by `(channel_id, bucket)`.
4. API **publishes to the guild's owning process**. One owner per guild → per-channel total order for free.
5. The guild process resolves **online** members, **groups them by gateway node**, and sends **one message per node**. This is the 100× win.
6. Gateway nodes write to local sockets, stamping a **monotonic `seq`** per session.
7. **Presence** is derived from the session TTL, **coalesced and rate-limited** at the guild process, and **lazy for large guilds**.
8. **Reconnect is `RESUME` from `seq`**, out of a short per-session replay buffer. Backoff with jitter; drain, don't restart.
9. **Read state** is a last-read Snowflake per user per channel, written behind, with a **coalescing cache** in front of the hot partitions.
10. Degradation order, stated: **presence first, then read state, then history depth. Never live message delivery.**

---

## 15 · Variants — what actually changes

**The governing axis: are the recipients present, and how many of them are there?** Everything in this family is the same publish; only the answer to that question changes, and it changes the whole design.

| Product | Recipients present? | Fanout breadth | What changes from this page |
|---|---|---|---|
| **Discord** | Yes, holding a socket | 10³–10⁵ | The baseline. Fan out to sessions; no durable inbox |
| **WhatsApp** | Mostly no | 1–10 | **Inverts it.** Durable per-recipient queues, delivery receipts, catch-up on reconnect. Fanout is trivial; semantics are the problem |
| **Slack** | Yes, but far fewer | 10–10³ | Same shape, an order of magnitude smaller, so the hot-guild tier in `§8` disappears entirely. Search and history become the interesting half |
| **Twitch chat** | Yes | 10⁵–10⁶ | **Only the hot tier exists.** Sharded fanout is the default, not a tier, and delivery becomes explicitly lossy — dropping chat messages under load is correct |
| **Twitter feed** | No | 10³–10⁸ | A different archetype. Absent readers make fanout-on-write vs on-read the whole question, and the hybrid for celebrities is the answer this page's `§8` rejects |
| **A trading broadcast** | Yes | 10²–10⁴ | Same fanout, but ordering and latency become hard requirements rather than product ones, so the coalescing and lossiness in `§9` are all forbidden |

---

## 16 · Active recall — answer these cold, no scrolling

1. Why is the message write rate the misleading number, and which number replaces it? → §3
2. State the contrast with WhatsApp in one sentence, in both directions. → header, §8
3. Why does a per-user inbox — the correct feed answer — actively hurt here? → §8
4. What is the single highest-leverage optimisation in the fanout path, and roughly what factor does it buy? → §8
5. Why do sends go over HTTP when the client already has a socket open? → §5
6. What does the `nonce` do, and name both things it buys. → §5
7. Give the arithmetic that makes presence the largest event stream. → §3, §9
8. Why is heartbeat-with-TTL the only correct presence model, rather than an optimisation? → §9
9. Name the three deliberate lossinesses in the presence design, and what each buys. → §9
10. Why is a routine deploy the load that sizes the gateway? → §7
11. What exactly does `RESUME` replace, and what new correctness risk does the `seq` introduce? → §5, §7
12. Why `(channel_id, bucket)` rather than `channel_id`, and what goes wrong if the bucket is too fine? → §12
13. What was the reported reason for the Cassandra → ScyllaDB move, and what is it *not*? → §11
14. Describe request coalescing, and name the other place on this page that has the same shape. → §10, §8
15. In flow A, the store write succeeds and the publish fails. What happens, and why is the reverse ordering unrecoverable? → §6
16. Name the degradation order, and defend the last item. → §14, §2
