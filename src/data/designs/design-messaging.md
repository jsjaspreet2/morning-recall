# Design WhatsApp — Real-Time Messaging & Delivery Semantics

**Archetype:** persistent-connection fanout with delivery guarantees over an unreliable network.
**Cousins that reuse ~70% of this page:** Slack, Discord, Messenger, Signal, Twitch chat, live comments, notification infrastructure. **Also the client half of any LLM chat product** — optimistic echo, reconnect reconciliation, and ordering under retry are the same problems in a streaming UI.

**What's actually being graded:** whether you understand that **exactly-once delivery does not exist**, and that the correct design therefore makes the *client* part of the correctness boundary rather than trying to make the server perfect. The two previous archetypes had a hard part in the infrastructure — throughput for a geospatial marketplace, row contention for an onsale. Here the infrastructure is comparatively easy and the hard part is *semantics*: ordering, deduplication, and what "delivered" means when the recipient's phone is in a tunnel.

**Contrast to have ready:** *Uber is a throughput problem. Ticketmaster is a contention problem. Messaging is neither — a message-send is a single write to an uncontended row. It's a **fanout and guarantees** problem, and the guarantees are the part you can get wrong quietly.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "The write path here is easy — a message is one durable append to a conversation log, and nobody is contending for it. Three things are hard. **Fanout**: one write becomes N deliveries, and N ranges from 1 to 100,000 depending on the product. **Ordering**: every participant must see the same sequence, and I can't use timestamps to get it. **Delivery over an unreliable network**: phones are offline constantly, so exactly-once is unachievable and I'll build at-least-once with client-side deduplication instead. I'd like to scope to 1:1 and group text messaging and go deep on ordering and the delivery/sync protocol. I'll name media, encryption, and calls as subsystems."

**Why open this way:** it steers away from the trap of treating this as a scale problem, and it puts the words "exactly-once is not achievable" on the table in minute one — which is the single highest-signal sentence available on this problem.

---

## 1 · Functional requirements

1. **Send a message** to a 1:1 or group conversation; it is durably persisted and delivered to every member.
2. **Receive in real time when online**, and receive everything missed on reconnect.
3. **Consistent ordering within a conversation**, plus delivered/read state.

**Out of scope (say them):** voice/video calls, media upload pipeline, contact discovery, stories/status, moderation.

**Below the line, likely follow-ups:** end-to-end encryption (changes the storage model fundamentally — §12), presence and typing indicators, multi-device (§10), search.

---

## 2 · Non-functional requirements

| Property | Target | Why |
|---|---|---|
| **Durability** | **Absolute. A sent-and-acked message is never lost** | The one true invariant. Everything else can degrade |
| **Delivery guarantee** | **At-least-once + idempotent dedupe** | Exactly-once is impossible across an unreliable network (§7). Say this rather than promising it |
| **Ordering** | Total order **per conversation**, identical for all participants | Users perceive order within a thread. Global ordering is unnecessary and expensive |
| Latency | p99 < 500ms send→receive when both online | Above ~1s the conversation stops feeling live |
| Availability | 99.99% send path; favor availability | A delayed message is fine, a lost one is not |
| Offline tolerance | Client may be offline for weeks; resync must be **bounded** | Unbounded catch-up is a real outage cause (§10) |
| Scale | ~2B users, ~1B concurrent connections, ~100B messages/day | Drives the connection tier, not the database |

**The sentence that earns the point:** *"I'm not going to claim exactly-once delivery, because it isn't achievable here. I'll do at-least-once on the wire and make dedupe idempotent at both ends, which gives the user exactly-once semantics even though the transport doesn't."*

---

## 3 · Numbers that reframe the problem

**Per conversation / per shard**

- 100B messages/day ÷ 86,400 ≈ **1.2M messages/sec average, ~3M peak.** Large, but it's an append to a log — the easiest possible write.
- Shard by `conversation_id`. Across even 10k shards that's **~120 writes/sec per shard.** *The database is not the problem.* Note the contrast with Ticketmaster, where the per-shard number was the binding constraint.
- **A single conversation is the serialization point** for sequence assignment (§8) — and a busy group chat does maybe 10 messages/sec. Trivially serial.

**Fanout — the number that actually matters**

- Average delivery amplification for 1:1-dominant traffic is ~2× → **~2.5M deliveries/sec average.**
- But amplification is the whole story: a 100,000-member channel turns **one write into 100,000 deliveries.** A single message can cost more than a thousand ordinary ones.
- **This is why products cap group size** (WhatsApp caps groups in the low thousands). *A product limit is a system design decision*, and noticing that out loud is a strong signal.

**Connections — the real infrastructure cost**

- ~1B concurrent WebSockets. At ~100k connections per tuned node, that's **~10,000 gateway nodes.**
- Per connection: kernel buffers plus app state ≈ 10–50KB → **~3GB of memory per node just to hold idle sockets.** The connection tier is sized by *memory and file descriptors*, not CPU. Most idle connections do nothing but consume RAM.

**Storage — depends entirely on a fork you must name (§12)**

- 100B × ~200B ≈ **20TB/day** if you retain everything. If the server is a transient queue that deletes on delivery, steady-state storage is a rounding error. **Same problem, three orders of magnitude apart in cost, decided by one product choice.**

---

## 4 · Core entities

- **User** — id, profile
- **Device** — id, user_id, push_token, platform *(multi-device makes this first-class, not an attribute)*
- **Conversation** — id, type (`DIRECT | GROUP`), created_at
- **Membership** — conversation_id, user_id, joined_at_seq, role
- **Message** — id, conversation_id, **seq**, sender_id, payload, server_ts, client_message_id
- **Cursor** — (device_id, conversation_id) → **last_delivered_seq, last_read_seq**
- **ConnectionRegistry** — device_id → gateway_id, heartbeat TTL

**Load-bearing details:**

- **`Message.seq`** — a per-conversation monotonic integer. This single field provides ordering, cursors, gap detection, and sync, all at once. It is the backbone of the whole design.
- **`Message.client_message_id`** — sender-generated UUID with a unique index on `(conversation_id, client_message_id)`. This is what makes retries safe (§7).
- **`Cursor` is per *device*, not per user, and stores a `seq` rather than a set of message ids.** One row per device per conversation, O(1) regardless of message count. Modeling read state per message is the amplification trap in §11.
- **`Membership.joined_at_seq`** — how you decide whether new members see history. One integer answers a whole product question.

---

## 5 · API

```
WS   /v1/connect                        auth → persistent socket, heartbeats

→ send        { clientMessageId, conversationId, payload }
← sendAck     { clientMessageId, messageId, seq, serverTs }
← message     { conversationId, seq, senderId, payload, serverTs }
→ cursor      { conversationId, deliveredSeq?, readSeq? }
← cursorUpdate{ conversationId, userId, deliveredSeq, readSeq }

GET  /v1/sync?syncToken=<token>         → [{ conversationId, latestSeq, memberCursors }], nextSyncToken
GET  /v1/conversations/{id}/messages?after_seq=&limit=
POST /v1/conversations                  → { conversationId }
```

**Decisions to narrate, unprompted:**

- **`clientMessageId` is generated by the sender, before the send.** It's the idempotency key. The client persists it in its local outbox at compose time so it survives an app kill and gets *reused* on retry; **enforcement lives on the server**, as a unique index on `(conversation_id, client_message_id)` (§7). Generating a fresh id on retry defeats the whole mechanism.
- **The ack returns the server-assigned `seq`.** That's what lets the client replace its optimistic local echo with the authoritative ordering (§8).
- **Read state is a position, not a set of acknowledgements.** Reading 500 messages emits **one** integer, not 500 acks — because `seq` is totally ordered (§8), "I've read up to 4,210" implies every message before it. Deriving state from a position instead of enumerating it is the move; §11 is the full cost analysis.

**Three different position values appear above, and it's worth pinning down which is which — they are not interchangeable:**

| Value | Scope | What it means | Comparable to |
|---|---|---|---|
| `deliveredSeq` | per (device, conversation) | Highest `seq` this device has *received* | Other seqs in the same conversation only |
| `readSeq` | per (device, conversation) | Highest `seq` the user has *seen* on this device | Same |
| `syncToken` | per device, global | Opaque watermark over the device's change log | Nothing — it's not a `seq` at all |

Two consequences that catch people out:

- **`seq` is namespaced to a conversation.** Seq 42 in one thread has no relationship to seq 42 in another. There is no global sequence (§8 explains why you don't want one), so any comparison across conversations is meaningless.
- **`syncToken` is a different kind of thing entirely**, which is why it's an opaque token rather than an integer. Per-conversation cursors answer *"where am I inside this thread?"*; the sync token answers *"which threads changed while I was gone?"* It's what makes reconnect cost one round trip in the common case where nothing changed, and it can expire independently of your cursors when a device has been away longer than retention (§10). Both are needed: the sync token finds the conversations, the cursors find the position within each.
- **`/sync` returns per-conversation *metadata*, not messages** — `latestSeq` so the client knows whether it missed anything, and `memberCursors` so delivered/read ticks are correct after a reconnect (Flow A step 12). The client diffs against its local state and pulls only what actually changed — usually nothing. This keeps reconnect cheap for the 99% case where you missed two messages, and bounded for the case where you missed 100,000 (§10).
- **Everything over the socket also exists as HTTP.** The socket is a latency optimization; the REST endpoints are the recovery path. Same principle as the Uber page — pushes are never the source of truth.

---

## 6 · High-level design — flows

```
                    ┌─────────────────────────────────────────┐
  1B devices ───────▶  Connection Gateways (~10k nodes, WS)   │
                    └──────┬───────────────────────▲──────────┘
                           │ send                  │ deliver
                           ▼                       │
                    Message Service ───────────────┘
                       │        │           (registry lookup:
                       │        │            device → gateway)
                       ▼        ▼
              Message Store   Connection Registry (Redis, TTL)
           (sharded by conv)         │
                       │             └── offline? ──▶ APNs / FCM push
                       ▼
              outbox → Kafka ──▶ receipts, search index, analytics
```

**The two properties to point at:**

1. **The Message Store is boring and the Gateway tier is enormous.** 120 writes/sec per shard versus 10,000 nodes holding sockets. If you spend your time sharding the database you've optimized the cheap half.
2. **Delivery is a lookup, not a broadcast.** The Message Service resolves recipients → devices → gateways, then sends one batched RPC per gateway. Nothing subscribes to conversations (§9 explains why that alternative collapses).

### Flow A — send and deliver

1. Client persists the message locally with a `clientMessageId` and status `PENDING`, and **renders it immediately** — optimistic local echo (§8).
2. Client sends over the socket. If the socket is down, it queues locally and retries with the *same* `clientMessageId`.
3. Message Service authenticates, resolves the conversation's shard, and verifies the sender is a member.
4. **Sequence assignment and durable append happen in one atomic step** on the conversation's shard: `seq = last_seq + 1`, insert with unique constraint on `(conversation_id, client_message_id)`.
5. **If that constraint fires, this is a retry of a message already stored.** Return the *original* `messageId` and `seq`. Do not create a second message. This is the entire dedupe mechanism (§7).
6. Ack to the sender. **The message is now durable; everything after this point is delivery, and delivery is allowed to fail and retry.**
7. Client swaps its optimistic entry for the acked one, reorders locally if the assigned `seq` disagrees with its provisional placement, and marks it `SENT`.
8. Message Service loads the member list, expands to devices, and looks up `device → gateway` in the registry. Devices are **grouped by gateway** so a 500-member group is a few dozen batched RPCs, not 500 individual ones.
9. Each gateway pushes to its connected sockets. **Any device with no registry entry is offline** → enqueue a push notification (APNs/FCM) carrying only a wake-up hint, not the message body.
10. Receiving client appends by `seq`. **If `seq > local_max + 1`, it has detected a gap** and pulls the missing range over HTTP rather than assuming it received everything.
11. **Receipts travel the same machinery, in reverse.** The receiving client sends `cursor { conversationId, deliveredSeq }` over its own socket. The server persists it to that device's `Cursor` row, then fans it out as a `cursorUpdate` to the *other* members' devices — the identical registry lookup and per-gateway batching from step 8, just carrying an integer instead of a message body. The sender's client receives that frame **on the socket it already holds** and renders the tick.
    - **Everyone in a conversation is simultaneously a sender and a receiver on one bidirectional socket.** There is no separate "sender connection" — the roles are per-message, not per-connection, and the same gateway push path serves both directions.
    - **This fanout is subject to the same amplification as the message itself**, and worse: every member emits a cursor update for every message. That's the §11 trap in its natural habitat — a 100-member group turns one message into ~100 receipts, each fanning out to ~100 devices.
    - **It's lossy on purpose.** If the `cursorUpdate` push is dropped, nothing retries it. The tick simply appears when a later cursor update supersedes it, because cursors are monotonic (§11).
12. **If the sender is offline** when the receipt arrives, there is no socket to push to — and a delivery tick isn't worth a wake-up notification. The sender picks up current state on its next sync, which is why `/sync` returns each conversation's member cursor state alongside `latestSeq`. Without that, a reconnecting sender would show stale ticks until someone happened to send a new message.
13. **Failure path:** gateway RPC fails, or the device disconnected between registry lookup and push. **Nothing is retried at the delivery layer.** The message is durable in the log, and the device will pull it on reconnect via §10. **Delivery is best-effort precisely because sync is authoritative** — that's the design, not a gap in it.

### Flow B — reconnect and catch up

1. Socket drops. Client reconnects with backoff and jitter — **jitter is load-bearing**: 10M devices reconnecting in lockstep after a gateway restart is a self-inflicted thundering herd.
2. Gateway authenticates and writes `device → gateway` into the registry with a heartbeat TTL.
3. Client calls `GET /v1/sync` with its **sync token** — the per-device watermark, not a per-conversation `seq`. Server returns `(conversationId, latestSeq, memberCursors)` for conversations with activity since that point.
4. Client diffs against local state and requests `after_seq` only for conversations that actually moved. **Usually this is zero conversations and the whole reconnect costs one round trip.**
5. For a long absence, the server caps the response and returns a truncation marker; the client shows a "catch up" affordance and lazily backfills instead of downloading 100,000 messages at once (§10).
6. Client flushes its outbound queue — pending sends, with original `clientMessageId`s, deduped server-side per step 5 of Flow A.
7. Client uploads any locally advanced cursors.
8. **Failure path:** the device has been gone long enough that its **sync token** predates retention. Server returns "token expired," client resets to the current head and backfills from there — note this strands its per-conversation cursors too, so those reset alongside. **A bounded gap in history beats an unbounded sync that never completes** — and never completing is how this fails in production, since the client retries the same enormous sync forever.

---

## 7 · Deep dive — why exactly-once doesn't exist, and what to do instead

### The obvious answer and why it fails

"Send the message, wait for an ack, retry if no ack." Consider: the server stores the message and its ack is lost. The client cannot distinguish *"the server never got it"* from *"the server got it and the ack died."* It has exactly two options, and **both are wrong**:

- **Don't retry** → at-most-once. Messages are silently lost. Unacceptable given §2.
- **Retry** → at-least-once. Duplicates. Annoying but survivable.

This is the Two Generals problem, and it isn't an engineering gap you can close with a better protocol — no finite exchange of messages over a lossy channel establishes common knowledge. **Any system claiming exactly-once *delivery* is actually doing at-least-once delivery plus deduplication somewhere.** Say that sentence; it's the whole dive in one line.

### What to build

**At-least-once transport, idempotent at both ends.**

**Sender side — two halves, on two different machines.** Conflating them is the usual confusion:

| Where | What | Why it must live there |
|---|---|---|
| **Client** | Generates `clientMessageId` at compose time and **persists it in its local outbox** | It must survive an app kill and be *reused* on retry. A fresh id on retry means the server sees a brand-new message and dedupe silently does nothing |
| **Server** | Unique index on `(conversation_id, client_message_id)` in the messages table | The database is the only place that can atomically decide "first write wins" across concurrent retries arriving on different connections |

The client's local copy is not the dedupe mechanism — it's what makes the *same* id available to retry with. **The enforcement is entirely server-side**, which is what makes the retry safe: the client can send as many times as it likes, and the constraint guarantees at most one row.

**Why the index is scoped to `conversation_id` rather than globally unique:** the message store is sharded by conversation (§12), and a unique constraint can only be enforced *within* a shard. A globally unique index on `client_message_id` alone would need cross-shard coordination on every send. Scoping it to the conversation makes it a local, single-shard constraint — which is why it's cheap enough to sit in the hot path at all.

A retry hits the constraint and returns the original `messageId` and `seq` — **the retry is indistinguishable from the original, from the client's perspective.** Note the index has to *be* the dedupe mechanism, not merely a guard: catching the violation and returning the existing row is the behavior; treating it as an error is the bug.

*Receiver side (client-side, and that's fine here):* dedupe on `messageId`, and more robustly on `seq` — a message with `seq ≤ local_max` for that conversation has already been seen and is dropped. **The `seq` gives you dedupe for free**, which is a nice property to point out, since it means the receiver needs no separate dedupe table.

**Cost, which you should volunteer:** correctness now depends on client behavior. A buggy client that regenerates `clientMessageId` on retry will duplicate, and you cannot fix that server-side. You've traded an impossible guarantee for a possible one that requires cooperation — and that's the right trade, but it means the client SDK is part of the system, not a consumer of it.

**The ordering of steps that matters:** durability before delivery. Step 6 of Flow A acks as soon as the message is stored, *before* any delivery is attempted. If you ack after delivery, a send fails whenever a recipient is offline — which is most of the time.

---

## 8 · Deep dive — ordering, and why timestamps can't do it

### Why timestamps fail

- **Client clocks are adversarial.** Wrong by minutes, user-settable, and a client that sets its clock forward pins its messages to the top of every thread forever.
- **Server clocks are merely bad.** NTP-synced hosts still drift by milliseconds; two messages hitting different servers can be assigned timestamps in the wrong order.
- **Ties are common.** At millisecond resolution and millions of messages/sec, collisions happen constantly, and tie-breaking by id is arbitrary — meaning **two clients can render the same two messages in different orders**, which users notice and report as a bug.

### What to build: per-conversation sequence numbers

Every message gets a monotonic integer, assigned atomically by the shard that owns the conversation (Flow A step 4). Because a conversation lives on exactly one shard, that shard is a **single writer**, and single writers produce total order for free — no consensus protocol, no vector clocks. **Where that atomic increment physically happens is a real decision, not a detail** — an LSM store can't give you one cheaply, and §12 works through the three options.

Four properties from one integer:
- **Total order per conversation**, identical for every participant.
- **Gap detection** — `seq > local_max + 1` means something was missed, so the client *knows* rather than silently rendering an incomplete thread.
- **Cursors** — delivered/read state is one integer per device per conversation (§11).
- **Dedupe** — as above, `seq ≤ local_max` is a duplicate.

**Why not global ordering across conversations?** It would require consensus across shards, and it buys nothing observable: nobody can perceive whether a message in one thread preceded a message in a different thread. **Order only needs to be consistent where it's observable** — the general principle worth stating, and it generalizes well beyond messaging.

**Cost:** the conversation is a serialization point. At ~10 messages/sec for even a busy group this is irrelevant, but say it anyway — it shows you know you introduced one.

### Local echo: the client-side half

The message must render instantly, before any server round trip. So the client appends it optimistically with a provisional position, then reconciles when the ack returns a real `seq` — which may place it *after* messages that arrived in the interim, causing a visible reorder.

Handle it deliberately: render optimistic messages in a pending zone at the bottom of the thread, then settle them into position on ack. **The alternative — waiting for the server before rendering — makes the app feel broken on a slow network**, which is why every real messaging client does this.

> **This is the same problem as a streaming LLM chat UI:** optimistic user message, provisional assistant message, reconciliation on completion, and correct handling when the connection drops mid-stream. If you've built one, you've built the other.

---

## 9 · Deep dive — fanout, and why messaging inverts the feed answer

One write becomes N deliveries. There are two ways to spend that, and **the right answer here is the opposite of the right answer for a news feed** — which is exactly why interviewers ask it.

### Fanout-on-write (push into per-recipient inboxes)

Each recipient gets their own materialized mailbox row. Reads are trivial: read your own inbox. **This is correct for feeds**, because a feed read is a merge across thousands of authors you follow, and doing that merge at read time is prohibitive.

For messaging it's wrong: a 100,000-member channel means 100,000 writes for one message, and you've duplicated storage per recipient for content they'll all read from the same place. You've also made ordering harder, since each inbox is now its own log that must be kept consistent with the others.

### Fanout-on-read (one log per conversation, cursors per device) ✓

One append. Each client reads from the shared conversation log at its own cursor.

Why it wins here and loses for feeds:
- **Membership is small and enumerable.** You read from the ~10 conversations you're in, not from 5,000 authors.
- **Ordering comes free** from the shared log (§8). Per-recipient copies would each need it re-established.
- **Storage is O(messages)**, not O(messages × recipients).

**The hybrid that's actually right:** fan out **notifications** on write, keep **content** on read. The delivery push (Flow A steps 8–9) is a lightweight fanout telling each device that its cursor moved; the message body lives once in the log. **You get the latency of push with the storage of pull.**

### Why not pub/sub per conversation?

Tempting: gateways subscribe to the conversations their users are in, and the Message Service just publishes. It collapses at scale — a gateway holding 100k users who are collectively in 500k conversations needs 500k subscriptions, churning on every connect and disconnect. The subscription table becomes larger and more volatile than the connection registry it replaced.

**Use the registry instead** — `device → gateway`, one entry per connection, updated only on connect/disconnect — and do recipient resolution at send time. Recipient lists are small and cheap to expand; subscription sets are neither. *(Registry-vs-pub/sub is the same decision as the Uber page's §10, resolved the same way for the same reason. See `primitives/websocket-fanout.md`.)*

**Cost:** send-time work scales with recipient count, so a huge group is a genuinely expensive send. Mitigate by batching per gateway (Flow A step 8) and, above a threshold, treating large channels as a different product with a different delivery path — which is precisely why group size caps exist.

---

## 10 · Deep dive — sync, and the unbounded catch-up outage

### The naive approach and how it takes down your service

"On reconnect, send me everything since my cursor." Fine for a two-minute subway ride. Now consider a device offline for six months across 500 conversations with 100,000 missed messages: the client requests it, the server assembles it, the transfer fails partway on mobile, the client **retries the same enormous request**, and it never completes. The device is now permanently broken and permanently generating expensive requests. Multiply by every device that comes back after a long outage — **and note that a long outage is exactly when many devices reconnect at once**, so the failure correlates with the moment you can least afford it.

### What to build

**A two-phase, bounded sync (Flow B steps 3–5):**

1. **Metadata first.** Return `(conversationId, latestSeq, memberCursors)` for changed conversations only. Small, cheap, and *idempotent* — a failed sync retries harmlessly.
2. **Client diffs and pulls selectively.** Only conversations where `latestSeq > localSeq`, paginated by `after_seq`, most-recently-active first so the user sees something useful immediately.
3. **Cap and truncate.** Beyond a limit, return a truncation marker. The client shows a gap affordance and backfills lazily on scroll. **A visible bounded gap beats an invisible infinite retry.**
4. **Sync token expiry.** If the token predates retention, reset to head and backfill. Handle it explicitly or you get clients wedged forever on a token the server can no longer honor.

**Reconnect storms:** exponential backoff **with jitter**, plus server-side admission control on the sync endpoint. When a gateway restarts, its 100k devices reconnect simultaneously; without jitter that's a coordinated stampede against `/sync`. *(Admission control here is the same primitive as Ticketmaster's waiting room, applied to reconnects rather than to demand.)*

### Multi-device

A message is delivered to a *user*, but must land on N devices with independent connection states — phone online, laptop asleep, tablet offline for a month. So **cursors are per-device**, and read state is a merge: a message is "read" if any device read it, but each device still tracks its own delivery position.

Two consequences worth naming: a new device needs a history bootstrap policy (all history, or only from pairing time?), and **under end-to-end encryption each device is a separate cryptographic identity**, so the sender encrypts N times for one recipient. That's the real reason multi-device E2E is hard, and it's a good thing to name and then explicitly defer.

---

## 11 · Deep dive — read receipts, the write amplification trap

Receipts look trivial and are the most common place this design quietly explodes.

**The naive model:** a row per `(message_id, user_id, state)`. In a 100-member group, one message read by everyone is 100 rows. A 1,000-message conversation is 100,000 receipt rows for 1,000 messages. **Receipt volume exceeds message volume by the group size** — and then each receipt fans out to every member, so the *event* volume is amplified by group size a second time. One message can generate 10,000 receipt events.

**What to build:**

- **Store a cursor, not per-message state.** `(device_id, conversation_id) → last_read_seq`. Reading 500 messages is **one** integer update. Since order is total (§8), a cursor implies the state of every message before it — *the sequence number pays for itself a third time here.*
- **Debounce client-side.** Don't emit on every scroll; batch every few seconds and on blur. Read state is not urgent.
- **Degrade by group size.** 1:1 shows per-message ticks. Small groups show an avatar list. Large groups show a count computed lazily on request, or nothing at all — which is what real products do, and it's a **product decision made for systems reasons**, exactly like the group size cap in §3.
- **Receipts are lossy by design.** Never retry a receipt; the next cursor update supersedes it. Anything monotonic doesn't need reliable delivery, because a later value contains all earlier ones.

That last point generalizes: **monotonic state is cheap to sync and safe to drop.** It's why cursors beat per-message acknowledgement everywhere in this design.

---

## 12 · Data model, sharding, and the retention fork

**Shard by `conversation_id`.** Every message, sequence counter, and membership row for a conversation lives on one shard.

This gives you the single writer that §8 depends on, keeps message reads single-shard, and keeps hot-*write* partitions mild — a conversation's write rate is bounded by group size, so there's no equivalent of Ticketmaster's unsplittable hot event.

**Be precise about what the choice is for.** The store is partitioned regardless; a partition key is mandatory in Cassandra. What's being decided is *which* key, and `conversation_id` wins on ordering and read locality, not on throughput. At ~120 writes/sec per shard (§3), throughput constrains nothing — if it were the driver you'd pick something with better distribution, like a hash of `message_id`, and lose the single writer that §8 is built on. **The small write volume is why you can afford this key, not the reason you picked it.**

**The real partitioning risk here is size, not rate.** A conversation's write *rate* is bounded, but its total row count isn't — a years-old group chat accumulates millions of messages in one partition, and Cassandra degrades badly past roughly 100MB or ~100k rows per partition (compaction cost, repair time, and a single wide row that can't be split across nodes). So bucket the key: `PK: (conversation_id, bucket)` where `bucket` is a coarse time window or a `seq` range, clustering on `seq DESC` within it. **Time windows are right here specifically because the read is newest-first** — you walk buckets backwards and stop as soon as you have enough. (Full mechanics, including why the scheme depends on the read pattern, are in the feed page's §10, which has the extreme version of this problem.) Reads start at the newest bucket and walk backwards, which matches how people actually scroll. Sequence assignment is unaffected — the counter stays per conversation, independent of which bucket a message lands in. **Naming the size limit unprompted is a strong signal, because it's the failure that shows up in year three rather than at launch.**

The one genuinely awkward query is "list my conversations, most recent first," which is inherently cross-shard. Solve it with a per-user conversation index — a denormalized `(user_id, conversation_id, last_activity_ts)` updated on the outbox path. Eventually consistent by a second, which is unnoticeable on a conversation list.

> **The ordering key here must be a timestamp, not a `seq`.** This is a genuinely easy mistake: `seq` is namespaced *per conversation* (§8), so seq 900 in a chatty group and seq 12 in a quiet one aren't comparable. Sorting a conversation list by `seq` orders by message count, not recency. Use the server timestamp of the conversation's latest message. **Any cross-conversation comparison needs a globally comparable value, and `seq` is by construction not one.**

### Storage decisions — every stateful component, explicitly

Most of these are 15-second items in an interview. **That doesn't mean skipping them — it means being able to derive each one fast**, so you name the access pattern and the tradeoff rather than just the product. A dive is only warranted where reasonable engineers would disagree; the last two rows are the ones that qualify.

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Message log** | Append-only, never mutated, range scan by `seq` desc | Absolute | **Cassandra** (or ScyllaDB — same data model, better tail latency), `PK: conversation_id`, clustering `seq DESC` | "Write-once with range reads is the ideal LSM workload — the usual LSM read penalty comes from mutation, and here there is none" |
| **Connection registry** | `device_id → gateway_id`, ~1B keys, extreme churn, TTL-native | **None — rebuilt by reconnects** | Redis Cluster, heartbeat TTL | "Ephemeral, tiny values, needs TTL semantics. ~1B keys × ~100B ≈ 100GB sharded. Losing a node means those devices are briefly unreachable until they heartbeat — acceptable, because delivery is best-effort anyway" |
| **Cursors** (delivered/read) | Point write per device+conversation; read *all* members' cursors on sync | Low — a lost update is superseded | **Cassandra, co-partitioned with the log** (`PK: conversation_id`, clustering `device_id`) | "Same partition as the messages, so a sync reads both in one hit. I'd write with `USING TIMESTAMP = seq` so Cassandra's own last-write-wins resolves by sequence number instead of wall clock — otherwise a delayed write carrying an older `seq` but a newer clock timestamp regresses the cursor" |
| **Conversation list index** | Per-user, read on app open, inherently cross-shard | Rebuildable from the log | **Redis sorted set**, key `convs:{user_id}`, member = `conversation_id`, score = `last_activity_ts` (see key schema below). Cassandra as the cold rebuild source | "~20 members per user and only needed for *online* users, so the hot set is small. The score has to be a timestamp — `seq` isn't comparable across conversations" |
| **Outbox / event stream** | Ordered, replayable, multi-consumer | High, bounded retention | Kafka | "Fans one commit out to receipts, search indexing, and analytics without coupling them to the write path" |
| **Push queue** | Fire-and-forget to APNs/FCM, retryable | Low | **Kafka topic per platform** + consumer group, failures re-queued to a delay topic (SQS is equally fine if you're not already running Kafka) | "Carries a wake-up hint, never the body — the body is not the notification's job" |
| **Sequence counter** | Atomic increment per conversation | Derivable — see below | **Needs a single writer.** See the tension below | The one that actually needs discussing |

### Redis key schema — exact operations

Every Redis structure has a key, a member, and sometimes a score, and leaving any of the three implicit is where these designs get hand-wavy. Spelled out:

| Purpose | Structure | Key | Member / value | Score | Operations |
|---|---|---|---|---|---|
| Connection registry | String + TTL | `conn:{device_id}` | `{gateway_id}` | — | `SET conn:{device_id} {gateway_id} EX 30` on connect, re-issued on each heartbeat. Fanout reads a whole recipient list in one round trip: `MGET conn:{d1} conn:{d2} …`. Absent key ⇒ device offline ⇒ push notification |
| Gateway teardown index | Set | `gw:{gateway_id}` | `{device_id}` | — | `SADD` on connect, `SREM` on disconnect. On gateway crash, `SMEMBERS` gives you the devices to evict rather than waiting out ~1B individual TTLs |
| Conversation list | Sorted set | `convs:{user_id}` | `{conversation_id}` | `last_activity_ts` (ms epoch) | `ZADD convs:{user_id} {ts} {conversation_id}` from the outbox; `ZREVRANGE convs:{user_id} 0 49 WITHSCORES` on app open. `ZADD` is an upsert, so a conversation never appears twice |

**Why the TTL is 30s against a heartbeat of ~10s:** the key must outlive a couple of missed heartbeats or a brief network blip evicts a perfectly healthy connection. Too long and dead devices linger as false "online" targets — you're trading wasted pushes against premature eviction, and ~3× the heartbeat interval is the usual landing spot.

**Why not a second Redis cluster with AOF for cursors?** Reasonable instinct — it's exactly right for the connection registry — but cursors are the opposite workload. Roughly 1B devices × ~20 conversations is **~20B rows, multiple TB of RAM**, for data that's read only when a conversation is opened or a device syncs. Redis earns its cost when data is hot, small, and ephemeral; cursors are warm, large, and semi-durable. Co-partitioning them with the message log makes the sync read single-partition and adds no new system to operate. **The general test: reach for Redis when the working set is genuinely hot and losing it is survivable — not merely because the writes are frequent.**

### The sequence-assignment tension (say this before you're asked)

§8 depends on an atomic per-conversation increment, and **an LSM store doesn't give you one.** Cassandra's counter columns aren't safe under retry, and lightweight transactions cost several round trips per message. So naming Cassandra for the log and then waving at "assigned atomically" is a contradiction. Three resolutions:

| Approach | How | Cost |
|---|---|---|
| **Relational shard** | `UPDATE conv SET seq = seq+1 RETURNING seq`, then insert, one transaction | Simplest and honestly fine — §3 says ~120 writes/sec per shard. You give up the LSM append profile |
| **Single-writer service** ✓ | The process owning the conversation's shard holds the counter in memory and assigns serially; recovery reads `MAX(seq)` from the log on startup | Stateful, partitioned service — same primitive as the Uber matcher. You own membership and rebalancing |
| **LWT / Paxos per message** | Compare-and-set on the counter row | Correct but tens of ms per send. Rejected on latency |

The middle one is the production shape, and it's worth noticing that **it's the same "partition ownership instead of coordination" move** that removes the distributed lock from the Uber page. Two very different problems, one primitive: *when you need a serialization point, own it rather than lock it.*

**Cost, volunteered:** an in-memory counter means a conversation is briefly unavailable during failover while the new owner reads `MAX(seq)`. Sends queue client-side and retry with the same `clientMessageId` (§7), so nothing is lost — the dedupe mechanism is what makes the failover safe.

### The retention fork — name it explicitly

**Start by saying what *doesn't* change**, because it's most of the system and volunteering that shows you know where the fork actually bites:

> Identical on both sides: the message store and its partition key, sequence assignment, dedupe, the connection registry and gateway fanout, cursors, the sync protocol, and the Kafka outbox. **Messages are written durably to the same store either way** — WhatsApp is not skipping the database, it's setting a TTL on it. And Kafka is present in both; in the archive case it simply has one more consumer.

What actually differs is a retention policy **plus three subsystems that exist on only one side**:

| | **Transient queue** (WhatsApp/Signal) | **Durable archive** (Slack/Teams) |
|---|---|---|
| Retention | Row TTL, plus opportunistic delete once all devices have delivered | Indefinite, subject to per-workspace policy |
| Steady-state storage | Near zero | ~20TB/day and growing; needs hot/warm/cold tiering to S3 |
| **Search index** | **Doesn't exist** — server holds ciphertext | **Elasticsearch fed off the outbox.** A whole subsystem, and usually the second-most-discussed part of a Slack design |
| **New-device bootstrap** | Encrypted cloud backup or device-to-device transfer — **a client-side protocol, not a server feature** | `GET /messages` with no cursor. Free |
| **Compliance** | Nothing to export; that's the selling point | Legal hold, eDiscovery, admin export, audit log — **a real subsystem with its own access path** |
| Forced by | End-to-end encryption. The server *cannot* read plaintext, so archive and search aren't policy choices — they're unavailable | Compliance and discovery requirements make them mandatory |

**The forcing function is encryption, not storage cost.** Under E2E the server holds ciphertext, so "should we archive and index this?" isn't a decision anyone gets to make. That's why the fork is upstream of the storage sizing rather than downstream of it, and why picking one silently contradicts everything else you say about the system.

**The one non-obvious mechanic on the transient side:** "delete once delivered to all devices" needs a device that might never return. You can't wait forever, so a max TTL is the real deletion mechanism and the all-delivered check is only an early-release optimization. Say it that way round — candidates who describe delete-on-delivery as the primary mechanism get asked about the device that fell in a lake, and don't have an answer.

**Say which one you're building in the first two minutes**, because §10, §12, and your entire storage estimate depend on it, and a candidate who designs an archive while describing WhatsApp has a contradiction sitting in their design the whole round.

---

## 13 · Traps — the ranked list

**Design traps**

1. **Claiming exactly-once delivery.** It doesn't exist. At-least-once plus idempotent dedupe is the answer, and saying so early is worth more than anything else on this page.
2. **Ordering by timestamp.** Clock skew and ties mean two clients render the same thread differently. Per-conversation `seq`.
3. **Fanout-on-write.** Right for feeds, wrong here. Fan out notifications, not content.
4. **Per-message read receipts.** Amplifies by group size twice — storage *and* events. Cursors.
5. **Pub/sub subscriptions per conversation on gateways.** The subscription set dwarfs the connection set and churns constantly.
6. **Unbounded catch-up sync.** The classic outage: a client that can never finish syncing retries forever, correlated across devices.
7. **Acking after delivery instead of after durability.** Makes sends fail whenever a recipient is offline — i.e. most of the time.
8. **Generating `clientMessageId` at transmit time.** It must be created at compose time and survive restarts, or dedupe silently does nothing.
9. **Treating a constraint violation on `client_message_id` as an error.** It's the mechanism — return the original row.
10. **Ignoring multi-device.** Cursors are per-device; read state is a merge; E2E multiplies encryption by device count.
11. **No gap detection.** Without checking `seq > local_max + 1`, clients render incomplete threads and never notice.
12. **Reconnect without jitter.** A gateway restart becomes a coordinated stampede.
13. **Not naming the retention fork.** Designing an archive while describing a transient queue is a contradiction that sits in your design all round.
14. **Justifying the partition key by write throughput.** The store is partitioned either way — Cassandra requires a partition key, so "unpartitioned" isn't an option. The trap is the *reasoning*: at ~120 writes/sec per shard, throughput doesn't constrain anything, and if it were your driver you'd choose a key with better distribution (hash of `message_id`, say) and destroy the single-writer ordering §8 depends on. **`conversation_id` is chosen for ordering and read locality; the write volume is an argument for why you can afford that choice, not the reason for it.**

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this page:

15. **Spending twenty minutes on the database.** It's the easy half. If you haven't reached ordering or delivery semantics by minute 25, you've spent the round on the part nobody is testing.

---

## 14 · The five-minute skeleton (draw this cold)

1. Not a throughput problem, not a contention problem. **Fanout + guarantees.**
2. **Exactly-once is impossible** → at-least-once + idempotent dedupe at both ends.
3. `clientMessageId` at compose time; unique index `(conv_id, client_msg_id)`; violation returns the original.
4. Per-conversation `seq`, assigned by the single-writer shard. Gives order, gaps, cursors, dedupe — one integer, four jobs.
5. **Durability before delivery.** Ack on store, then attempt delivery; delivery is best-effort because sync is authoritative.
6. Connection registry `device → gateway`, ~10k gateway nodes, batch pushes per gateway. **Not pub/sub per conversation.**
7. Fanout-on-**read** for content (inverse of feeds), fanout-on-write for notifications only.
8. Offline → APNs/FCM wake-up hint, no body. Reconnect → two-phase bounded sync, backoff with jitter.
9. Read state = per-device cursor, debounced, lossy by design. Monotonic state is safe to drop.
10. Shard by `conversation_id` for single-writer ordering. **Name the retention fork:** transient queue vs durable archive.

---

## 15 · Variants — what actually changes

**The axis that governs this family: fanout ratio — how many deliveries per write.** Every threshold crossing forces a different design, and durability requirements are the secondary axis.

| Fanout | Problem | What changes |
|---|---|---|
| **~2** | 1:1 chat (Signal, DMs) | The base case. E2E is easy — one recipient, few devices |
| **~10–1,000** | Group chat (WhatsApp) | This page. Caps exist *because* of fanout cost |
| **~10k–100k** | Slack/Discord channels | Fanout-on-read becomes mandatory. Membership is too large to enumerate per send — invert to "who's currently connected and subscribed." Presence becomes its own hard problem |
| **~1M+, ephemeral** | Twitch chat, live comments | **Durability requirement disappears**, and that changes everything. Drop messages freely, sample under load, no history, no cursors, no receipts. Fanout via regional relay trees rather than per-recipient resolution |
| **~1M+, durable** | Twitter/feed | **Inverts the fanout answer.** Read pattern is a merge across thousands of authors, so fanout-on-write into materialized timelines wins — with a read-time hybrid for celebrity accounts |
| **~2, no real-time** | Email (SMTP) | Store-and-forward, minutes of latency acceptable. Same at-least-once + dedupe (Message-ID), no connection tier at all |
| **~10, convergent** | Google Docs / collab editing | Ordering becomes *convergence*: concurrent edits must merge, not just sequence. OT or CRDTs. A `seq` is insufficient because operations conflict |

**The general lesson:** ordering, durability, and fanout are three independent knobs. Messaging needs all three, which is why it's the richest page in the family — Twitch chat drops durability, email drops real-time, feeds invert fanout, and each removal makes the problem dramatically easier.

---

## 16 · Active recall — answer these cold, no scrolling

**Protocol:** out loud, in full sentences. Check the pointer only after attempting. Schedule in `00-interview-mechanics.md` §8.

| # | Prompt | Check |
|---|---|---|
| 1 | Why is exactly-once delivery impossible, and what do you build instead? | §7 |
| 2 | The server stores a message and the ack is lost. What are the client's two options and why is one clearly better? | §7 |
| 3 | Where must `clientMessageId` be generated, and what breaks if it's generated later? | §5, §7 |
| 4 | A unique constraint fires on `(conv_id, client_msg_id)`. What's the correct server behavior? | §7 |
| 5 | Give three reasons timestamps can't order a conversation. | §8 |
| 6 | Name the four separate jobs a per-conversation `seq` does. | §8 |
| 7 | Why don't you need global ordering across conversations? State the general principle. | §8 |
| 8 | What's the cost of assigning `seq` on the conversation's shard? | §8, §12 |
| 9 | Why is fanout-on-read right for messaging and wrong for a news feed? | §9 |
| 10 | What's the hybrid, and what does each half buy? | §9 |
| 11 | Why does pub/sub-per-conversation collapse on the gateway tier? | §9 |
| 12 | A device is offline for six months. Trace the naive sync and how it takes down your service. | §10 |
| 13 | Why must reconnect backoff have jitter? What correlates the failure? | §6, §10 |
| 14 | Read receipts as per-message rows: quantify the amplification and say where it hits twice. | §11 |
| 15 | Why are receipts safe to drop? State the property that makes that true. | §11 |
| 16 | Name the retention fork and three things that change depending on which side you pick. | §12 |
| 17 | Why ack on durability rather than on delivery? What fails if you invert it? | §6, §7 |
| 18 | What does a client do when it receives `seq > local_max + 1`, and why does that matter? | §6, §8 |
| 19 | Twitch chat has 1M-fanout. Which requirement disappears, and what does removing it let you drop? | §15 |
| 20 | Name the three position-tracking values in the API, their scope, and why the sync token isn't a `seq`. | §5 |
| 21 | Receiver marks a message delivered. Trace exactly how the sender's tick appears — and what happens if the sender is offline. | §6, §11 |
| 22 | Dedupe has a client half and a server half. Which is which, and which one actually enforces correctness? | §7 |
| 23 | Why is the unique index scoped to `(conversation_id, client_message_id)` rather than globally unique? | §7, §12 |
| 24 | Name the storage choice for the connection registry and derive it in one sentence. What breaks if a node dies? | §12 |
| 25 | Why can't a Cassandra-family store assign `seq`? Give three resolutions and pick one with its cost. | §12 |
| 26 | Why are cursors safe to merge with last-write-wins when most state isn't? | §11, §12 |
| 27 | Why do cursors live in Cassandra rather than a second Redis cluster? Give the number that decides it. | §12 |
| 28 | What does `USING TIMESTAMP = seq` fix, and what goes wrong without it? | §12 |
| 29 | Why can't `seq` be the score on the conversation-list sorted set? What does sorting by it actually produce? | §12 |
| 30 | Give the key, member, and score for each Redis structure, and why the registry TTL is ~3× the heartbeat. | §12 |
| 31 | The store is partitioned no matter what. So what is choosing `conversation_id` actually buying, and what would a throughput-driven key cost you? | §12 |
| 32 | A conversation's write rate is bounded but something else isn't. What, why does it matter, and what's the fix? | §12 |
| 33 | Between transient queue and durable archive, name what's shared and the three subsystems that aren't. | §12 |
| 34 | Why is the retention fork forced by encryption rather than by storage cost? | §12 |
| 35 | "Delete once all devices have delivered." What's the flaw, and what's the actual deletion mechanism? | §12 |
