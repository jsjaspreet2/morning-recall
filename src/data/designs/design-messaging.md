# Design Slack — Durable Channels, Ordering & Reconnect

## The question

> *"Design Slack. People send messages in workspace channels and direct messages, receive them live, and catch up on the conversation when they return."*

**The product.** A team has shared channels for projects and direct conversations for smaller discussions. You can leave your laptop overnight, open another device tomorrow, and read what happened while you were away. Sending should feel immediate. A flaky connection should not post your message twice, lose someone else's message, or make two people see a different settled conversation order.

**What a working system delivers**

- A sent message appears once in shared history and reaches connected participants promptly.
- Reopening a channel recovers the messages the device missed, within the workspace's retention policy.
- Each device catches up independently; reading on one device clears the user's unread position on another.
- Private-channel content is available only to authorized members, including through history and search.

**Why this gets asked.** One durable message becomes many live deliveries, but the two have different failure semantics. The system must accept a message safely even when recipients are offline, and the client must recover correctly when live delivery is incomplete. The interesting boundary is between durable history and disposable connection state.

---

**Archetype:** Real-time messaging & delivery.
**Cousins that reuse ~70% of this page:** Teams, Discord text channels, enterprise chat, direct messaging.

**What's actually being graded:** whether you can separate message acceptance, ordering, delivery, and recovery; size the database without confusing logical shards with machines; and use transactions where they simplify correctness.

**Contrast to have ready:** *A feed materializes a merge across many authors. A Slack channel is already one shared history, so store its content once and fan out live events. Discord's largest channels push the fanout much harder; WhatsApp adds end-to-end encryption and different history/bootstrap policies.*

**Scope note.** This is a proposed Slack-like interview design, not a reconstruction of Slack's internals. Slack has publicly described **MySQL with Vitess**, including persistence before WebSocket delivery and migration away from workspace-only sharding. We use **sharded Postgres** to make the transaction concrete. [Slack's datastore architecture](https://slack.engineering/scaling-datastores-at-slack-with-vitess/)

---

## 0 · The 60-second frame

> "I'll scope to channels and DMs, live delivery, retained history, and unread state. I'll store one shared message history per conversation, with channels and DMs using the same path. At the assumed scale, sharded Postgres lets me commit the retry key, channel sequence, message, and outbox event together. I'll acknowledge that durable commit, then fan out to connected devices. WebSockets are the fast path; bounded history sync repairs missed events. I'd like to go deep on idempotent acceptance and ordering, then reconnect correctness. I'll cover channel fanout and name search, permissions, and retention without designing every Slack feature."

The central trade: **a manageable relational fleet buys simpler correctness; a larger write/storage workload may justify a different engine and more recovery machinery.** Dense numbering is a choice, not a product requirement or a reason to ignore database cost.

---

## 1 · Functional requirements

1. **Send channel messages and DMs**, enforcing membership and making retries produce one accepted message.
2. **Receive online and retrieve retained history**, including bounded recovery after disconnect or device restart.
3. **Show a consistent settled order and unread position**, with independent device recovery and user-level read state.

**Out of scope:** calls, file upload, bots, reactions, threads, edits, enterprise federation, and full search implementation. The base text-message path is immutable; deletion/retention boundaries are still required for recovery. Search and edits are follow-ups, not additional hot-path dependencies.

**Product choices for this round:** server-readable text, private-channel membership checks, 90-day history retention, and no public per-message delivered/read ticks. A transport acknowledgement is internal; Slack-style unread state does not require broadcasting everyone's receipt to everyone else.

---

## 2 · Non-functional requirements

| Property | Interview target | Why / failure policy |
|---|---|---|
| Acceptance durability | RPO 0 for a single database node or availability-zone failure | Ack only after local WAL flush and synchronous WAL flush on a replica in another AZ; promote a replica known to contain acknowledged commits |
| Fault tolerance | Gateway loss recovers within 30s; database failover target ≤60s | Client retries with jitter. Without a safe writable primary, affected sends remain pending; do not acknowledge speculative writes |
| Regional disaster | Cross-region WAL archive lag target ≤5min; restore target ≤4h | Whole-region loss is outside the zero-loss promise. Restores are tested; tighter requirements require a different replication/latency trade |
| Online latency | p99 send→display <500ms within the home region under admitted load | Storage and delivery consume this budget; direct post-commit delivery can bypass relay lag for small conversations |
| Availability | 99.95% monthly send-path target | Measured service objective, not permission to lose accepted data; degraded shards reject or delay writes |
| Ordering and retries | One committed order per conversation; retry guarantee for 7 days | No cross-channel order. Same sender/key returns the same accepted result within the retry window |
| Recovery and freshness | Active-channel reconciliation ≤30s; read-state convergence ≤5s normally | Catches a lost final push. Background history loads lazily; no full-account download on reconnect |
| Bounded work | ≤50 conversations per metadata page; ≤100 messages and 256KiB per history page; ≤4 concurrent history pulls/device | Long absences and reconnect storms must produce incremental progress rather than oversized retries |

**The sentence that earns the point:** *"The accepted message is durable under a stated failure model. Delivery may repeat, and the client's durable local state makes those repeats harmless."*

---

## 3 · Numbers that reframe the problem

**These are interview assumptions, not current Slack usage or database benchmarks.** Agree on them before selecting a fleet. DAU alone does not determine writes, reads, or retention cost.

1. **20M daily active users × 50 sends/day = 1B messages/day.** About **12k sends/sec average**, with an assumed 5× peak rounded to **60k/sec**. Size the latency-sensitive write path for that peak plus headroom; average traffic determines daily storage growth.
2. **10k complete sends/sec per primary is a sizing hypothesis.** At 60% planned utilization, `60k / (10k × 0.6) = 10 primaries`, or **30 instances** with two replicas each. If the measured capacity is only 1k, this becomes **100 primaries / 300 instances**. These are throughput estimates, not the final fleet. Benchmark the counter, dedupe, message, outbox, indexes, synchronous replication, and competing reads together.
3. **Logical shards are placement units, not machines.** For example, 256 logical shards can share those primaries and move as capacity grows. A busy channel at an assumed **10 sends/sec** is easy to serialize; that is typical workload, not a bound. Bots and exceptional channels need rate limits and hot-channel monitoring.
4. **5M concurrent device connections ÷ 50k/node = 100 gateway nodes before headroom.** Validate TLS, buffers, bandwidth, and reconnect load, not just file descriptors. With an assumed five online recipient devices per send, peak fanout is **300k deliveries/sec**; one announcement to 50k online devices is a separate burst.
5. **1B messages/day × 1KB stored content/metadata ≈ 1TB/day.** Ninety days is **90TB raw**, or **270TB at three copies**, before indexes, outbox, dedupe, and free space. Storage capacity and history reads may require more nodes than item 2. Smaller write volume does not mean a tiny archive.
6. **100 typical conversation memberships/user means two 50-channel metadata pages on reconnect.** Fetch heads first, bodies only where needed. At 50k devices on one failed gateway, even metadata-only recovery needs jitter, admission control, and paginated progress.

**Why Postgres is plausible:** writes for different conversations distribute well, while local transactions remove several failure cases. **Why it is not automatically right:** storage, read amplification, failure capacity, and shard operations can dominate. There is no universal "Postgres 10k versus ScyllaDB 50k" multiplier.

---

## 4 · Core entities

- **Workspace / User / Device** — tenant, authenticated actor, and independently reconnecting client.
- **Conversation** — `id`, `workspace_id`, `type: CHANNEL | DM`, `last_seq`, `retained_from_seq`.
- **Membership** — `(conversation_id, user_id)`, role, allowed history boundary; changes are authorized and serialized with sends when they affect send eligibility.
- **Message** — `(conversation_id, seq)`, `message_id`, `sender_id`, body, `accepted_at`.
- **SendDedup** — `(conversation_id, sender_id, client_message_id)` → canonical message ID, sequence, request hash, acceptance time.
- **OutboxEvent** — stable event ID and enough information to deliver or reconstruct the committed change.
- **ReadCursor** — `(conversation_id, user_id)` → `last_read_seq`, merged with `MAX`.
- **Device recovery state** — locally persisted messages, covered sequence ranges, and outbound retry records.

**Three load-bearing distinctions:** the retry ID is not authority; a per-user read cursor is not a device-delivery cursor; and the largest received sequence is not necessarily the largest contiguous received sequence.

---

## 5 · API

```text
WS   /v1/connect                      authenticated device session
→ send        { conversationId, clientMessageId, body }
← sendAck     { clientMessageId, messageId, seq, acceptedAt }
← message     { conversationId, messageId, seq, senderId, body }
→ readCursor  { conversationId, readSeq }
← readState   { conversationId, readSeq }

POST /v1/conversations/{id}/messages   same send semantics over HTTP
GET  /v1/conversations?after=&limit=   authorized membership list, paginated
POST /v1/sync/heads                   { conversationIds: [...] } (max 50)
                                      → [{ id, headSeq, retainedFromSeq, readSeq }]
GET  /v1/conversations/{id}/messages?afterSeq=&throughSeq=&limit=
                                      → messages, nextPage, coverage, retention boundary
PUT  /v1/conversations/{id}/read       monotonic read cursor
```

- **Generate and persist `clientMessageId` before the first send.** A retry reuses it across app restarts. The server parses a bounded UUID, derives the sender from authentication, checks permissions, and never uses the client ID's timestamp as authoritative acceptance time.
- **Same key and same request returns the original ack; changed content returns a conflict.** Compute a hash over canonical request fields on the server. Rate-limit both new sends and retries.
- **Pagination tokens identify bounded work, not delivery completion.** A device advances coverage only after it durably stores the returned page. `throughSeq` pins an upper bound so a busy channel cannot extend one catch-up forever.
- **The base sync uses paginated membership plus batched channel heads.** It does not promise an unexplained global change token or an O(1) reconnect. A durable per-user change feed is an optimization if this scan becomes expensive (§10).
- **Authorize every history, send, and sync access.** A conversation ID or an old subscription is not permission to see private messages.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 610" role="img" aria-label="Slack-like messaging architecture. Clients send through WebSocket gateways to the Message Service. A conversation-sharded Postgres group commits message, retry result, counter and outbox before acknowledgement. After commit, the Message Service can deliver small conversations directly to recipient gateways. Independently, an outbox relay publishes to Kafka, then a channel fanout service pushes to subscribed gateways. Both paths use the same message identity. Search is an asynchronous consumer. A separate History and Sync API reads channel history and heads from Postgres and memberships from a durable directory. Live pushes are repaired by bounded sync.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">One durable acceptance transaction; live delivery can repeat or fail because bounded sync repairs it.</text>
  <text class="dg-lane" x="20" y="86">ACCEPT — ACK AFTER THE REPLICATED COMMIT</text>
  <rect class="dg-box" x="20" y="110" width="140" height="74" rx="8"></rect>
  <text class="dg-t dg-c" x="90" y="135.5">Clients</text>
  <text class="dg-s dg-c" x="90" y="151.5">retry ID</text>
  <text class="dg-s dg-c" x="90" y="167.5">local outbox</text>
  <rect class="dg-box" x="210" y="110" width="180" height="74" rx="8"></rect>
  <text class="dg-t dg-c" x="300" y="135.5">Gateways</text>
  <text class="dg-s dg-c" x="300" y="151.5">WebSocket sessions</text>
  <text class="dg-s dg-c" x="300" y="167.5">bounded send queues</text>
  <rect class="dg-box" x="450" y="110" width="200" height="74" rx="8"></rect>
  <text class="dg-t dg-c" x="550" y="135.5">Message Service</text>
  <text class="dg-s dg-c" x="550" y="151.5">auth + shard routing</text>
  <text class="dg-s dg-c" x="550" y="167.5">idempotent send</text>
  <path class="dg-box" d="M 730,107 L 730,197 A 120,7 0 0 0 970,197 L 970,107 A 120,7 0 0 0 730,107 Z"></path>
  <path class="dg-box" d="M 730,107 A 120,7 0 0 0 970,107" style="fill:none"></path>
  <text class="dg-t dg-c" x="850" y="136">Postgres shard group</text>
  <text class="dg-s dg-c" x="850" y="152">message + dedupe</text>
  <text class="dg-s dg-c" x="850" y="168">counter + outbox</text>
  <text class="dg-s dg-c" x="850" y="184">cross-AZ replication</text>
  <path class="dg-line" d="M 160,147 L 202,147"></path>
  <path class="dg-head" d="M 202,152 L 202,142 L 210,147 Z"></path>
  <path class="dg-line" d="M 390,147 L 442,147"></path>
  <path class="dg-head" d="M 442,152 L 442,142 L 450,147 Z"></path>
  <path class="dg-line" d="M 650,147 L 722,147"></path>
  <path class="dg-head" d="M 722,152 L 722,142 L 730,147 Z"></path>
  <text class="dg-lbl dg-c" x="690" y="137">transaction</text>
  <path class="dg-line" d="M 480,184 L 480,220 L 370,220 L 370,192"></path>
  <path class="dg-head" d="M 375,192 L 365,192 L 370,184 Z"></path>
  <text class="dg-lbl dg-c" x="610" y="218">DM fast path · only after commit</text>
  <text class="dg-lane" x="390" y="254">DELIVER — DURABLE BACKGROUND PATH</text>
  <rect class="dg-box" x="730" y="290" width="240" height="70" rx="8"></rect>
  <text class="dg-t dg-c" x="850" y="313.5">Outbox relay</text>
  <text class="dg-s dg-c" x="850" y="329.5">publish committed events</text>
  <text class="dg-s dg-c" x="850" y="345.5">retry with stable event ID</text>
  <rect class="dg-box" x="450" y="290" width="200" height="70" rx="8"></rect>
  <path class="dg-qbar" d="M 463,299 L 463,351"></path>
  <path class="dg-qbar" d="M 472,299 L 472,351"></path>
  <path class="dg-qbar" d="M 481,299 L 481,351"></path>
  <text class="dg-t dg-c" x="568" y="313.5">Kafka</text>
  <text class="dg-s dg-c" x="568" y="329.5">at-least-once events</text>
  <text class="dg-s dg-c" x="568" y="345.5">bounded replay retention</text>
  <rect class="dg-box" x="210" y="290" width="180" height="70" rx="8"></rect>
  <text class="dg-t dg-c" x="300" y="313.5">Channel fanout</text>
  <text class="dg-s dg-c" x="300" y="329.5">channel / device routes</text>
  <text class="dg-s dg-c" x="300" y="345.5">leased subscriptions</text>
  <path class="dg-line" d="M 850,204 L 850,282"></path>
  <path class="dg-head" d="M 845,282 L 855,282 L 850,290 Z"></path>
  <text class="dg-lbl dg-c" x="920" y="237">committed outbox</text>
  <path class="dg-line" d="M 730,325 L 658,325"></path>
  <path class="dg-head" d="M 658,320 L 658,330 L 650,325 Z"></path>
  <path class="dg-line" d="M 450,325 L 398,325"></path>
  <path class="dg-head" d="M 398,320 L 398,330 L 390,325 Z"></path>
  <path class="dg-line" d="M 300,290 L 300,192"></path>
  <path class="dg-head" d="M 305,192 L 295,192 L 300,184 Z"></path>
  <text class="dg-lbl dg-c" x="235" y="238">message bodies</text>
  <rect class="dg-box" x="450" y="400" width="200" height="54" rx="8"></rect>
  <text class="dg-t dg-c" x="550" y="423.5">Search consumer</text>
  <text class="dg-s dg-c" x="550" y="439.5">Elasticsearch · optional</text>
  <path class="dg-line" d="M 550,360 L 550,392"></path>
  <path class="dg-head" d="M 545,392 L 555,392 L 550,400 Z"></path>
  <text class="dg-lane" x="20" y="463">RECOVER — HTTPS</text>
  <path class="dg-box" d="M 20,492 L 20,548 A 95,7 0 0 0 210,548 L 210,492 A 95,7 0 0 0 20,492 Z"></path>
  <path class="dg-box" d="M 20,492 A 95,7 0 0 0 210,492" style="fill:none"></path>
  <text class="dg-t dg-c" x="115" y="512">Membership directory</text>
  <text class="dg-s dg-c" x="115" y="528">Postgres projection</text>
  <text class="dg-s dg-c" x="115" y="544">paginated per user</text>
  <rect class="dg-box" x="280" y="485" width="280" height="70" rx="8"></rect>
  <text class="dg-t dg-c" x="420" y="508.5">History / Sync API</text>
  <text class="dg-s dg-c" x="420" y="524.5">authorize · heads · range pages</text>
  <text class="dg-s dg-c" x="420" y="540.5">active channel check ≤30s</text>
  <path class="dg-line" d="M 280,520 L 218,520"></path>
  <path class="dg-head" d="M 218,515 L 218,525 L 210,520 Z"></path>
  <path class="dg-line" d="M 560,520 L 990,520 L 990,150 L 978,150"></path>
  <path class="dg-head" d="M 978,145 L 978,155 L 970,150 Z"></path>
  <text class="dg-lbl dg-c" x="803" y="500">authoritative heads + history</text>
  <path class="dg-line" d="M 90,184 L 90,385 L 245,385 L 245,468 L 420,468 L 420,477"></path>
  <path class="dg-head" d="M 415,477 L 425,477 L 420,485 Z"></path>
  <text class="dg-lbl dg-c" x="142" y="375">HTTPS sync</text>
  <text class="dg-note" x="20" y="590">A lost final push needs a periodic head check. Dense sequence numbers alone cannot reveal it.</text>
</svg>
</div>

<p class="diagram-cap">The Postgres cylinder is a sharded fleet, not one machine. Its local transaction establishes acceptance. Small sends may go directly to recipient gateways after commit; the outbox path always runs and can deliver duplicates with the same identity. Sync reads durable history when a push is missed.</p>

### Flow A — accept, then deliver

1. The client saves an outbound record and shows an optimistic pending message. Socket or HTTP sends carry the same retry ID.
2. The Message Service authenticates, resolves the conversation's logical shard, and executes the local transaction in §7: verify membership, resolve retry, update the counter, insert message/dedupe/outbox.
3. After the required durable commit, return `sendAck` and, for DMs or a small bounded recipient set, attempt direct delivery in parallel. The Message Service resolves authorized participants to their online devices and gateways, then sends the canonical message body to those gateways. Include the sender's other devices. The client replaces its pending entry with the canonical message and sequence. **Neither the ack nor the database transaction waits for recipient delivery.**
4. Independently, a relay reads the committed outbox and publishes to Kafka. Consumers deliver through the fanout service to subscribed gateways. This is the durable delivery-work path for every message and the normal path for large channels; a successful direct attempt does not suppress it. Both paths carry the same canonical message ID and sequence (§9).
5. Receiving clients persist messages under unique identity and update covered ranges. Read cursors are separate user state. Mention/DM notifications for offline users are asynchronous hints, not message storage.
6. **Failure path:** a lost ack triggers the same send again. A crash after commit but before direct delivery, a stale route, or a failed gateway RPC leaves the committed outbox available for delivery. A relay crash replays it; duplicate events are harmless. A lost final push is recovered by active-channel reconciliation within 30s, or by sync on focus/reconnect. Never rely solely on a later message exposing the gap.

### Flow B — reconnect and catch up

1. Reconnect with exponential backoff and jitter; the gateway authenticates and establishes a new session generation.
2. Refresh authorized memberships in pages, then request heads for at most 50 conversations at a time. Rebuild subscriptions; the directory is an optimization, not durable history.
3. For the open conversation, pin a `headSeq` and pull missing ranges through that head. Cap pages and concurrency; persist each page before saving progress.
4. Show the latest page first after a long absence, with an explicit unloaded-history boundary. Backfill older pages on demand; do not mark skipped history as delivered or read.
5. Merge the user's server read cursor, resend locally pending read updates, and flush outbound sends with their original retry IDs. Other conversations initially need only sidebar metadata.
6. **Failure path:** resume a failed page from durable progress. If history has expired, use the server's explicit retention boundary; do not infer deletion from an empty or timed-out read. Removed memberships disappear and further reads are denied.

---

## 7 · Deep dive — idempotent acceptance in one transaction

### Why the obvious answer fails

"Insert the message and retry if no ack" duplicates a send when the first commit succeeded but its reply was lost. "Put the retry ID in Redis first" creates a different failure: the Redis claim survives while the message insert fails, so a retry can be suppressed without any message existing.

**Keep acceptance and its retry result in the same database transaction.** Route all conversation-owned tables to the same Postgres primary. A concrete implementation is:

```text
BEGIN
  lock the conversation row (SELECT ... FOR UPDATE)
  verify authenticated user's send permission
  look up SendDedup(conversation, authenticated sender, clientMessageId)
  if present:
    compare canonical request hash; return original ack or conflict
    finish without incrementing the counter
  otherwise:
    UPDATE conversation SET last_seq = last_seq + 1 RETURNING last_seq
    INSERT message with that seq and a server-generated message_id
    INSERT SendDedup with a UNIQUE(conversation_id, sender_id, client_message_id)
    INSERT outbox event with a stable event_id
COMMIT with the configured synchronous replication policy
```

The conversation lock serializes this path, including concurrent retries. Membership changes that affect acceptance take the same lock. Unique constraints remain defensive invariants. Every failure rolls back the counter and inserts together. An ordinary Postgres `SEQUENCE`/`nextval()` does **not** provide this rollback behavior. [Postgres sequence semantics](https://www.postgresql.org/docs/16/functions-sequence.html)

**The client ID can be malicious without becoming powerful.** Scope it to the authenticated sender, bound its format, and reject a different request under an accepted key. Alice choosing Bob's ID does not address Bob's dedupe row. Parameterized queries and authorization still apply; UUID randomness is collision avoidance, not access control.

**The outbox is a table, not another name for Kafka.** A relay publishes committed rows and marks them published after broker acknowledgement. Crash between publish and marking means duplicate publication, so consumers use stable event IDs or idempotent state updates. Monitor relay lag and retained outbox bytes; throttle acceptance before an unavailable broker fills the database. [Transactional outbox mechanism](https://debezium.io/blog/2019/02/19/reliable-microservices-data-exchange-with-the-outbox-pattern/)

**Cost:** multiple row/index writes, synchronous replication latency, and one serial acceptance point per conversation. Benchmark complete sends, not bare inserts. Redis can cache accepted responses but is not the authority. Dedupe metadata lives for 90 days; the supported client retry window is seven days. Beyond dedupe retention, the API cannot promise to recognize an old request as a retry.

**→ Ties to acceptance durability and the retry guarantee in §2.** A partition can delay acceptance; it must not manufacture an acknowledgement.

---

## 8 · Deep dive — ordering and completeness are different properties

### Why timestamps alone are insufficient

Client clocks can be wrong or deliberately manipulated. Server timestamps plus a deterministic tie-breaker can provide a stable sort order, but **sort order is not commit order or proof of completeness**. If ID 100 commits after 101, a client querying only `id > 101` can miss 100 forever.

For this baseline, use the transactional per-conversation counter from §7. The transaction assigning 43 cannot commit ahead of the earlier transaction holding the conversation lock. Participants eventually settle into the same sequence; optimistic pending messages may move when acknowledged. Different conversations need no common ordering.

### A dense sequence helps only if the client uses it correctly

A client receives **41, then 43, then 42**. Dropping everything at or below its largest seen value loses 42. Instead:

- Persist under a unique `(conversation_id, seq)` or message ID; duplicate identity is harmless.
- Track **covered ranges**. The contiguous prefix stays at 41 until 42 arrives, even if 43 is already visible.
- Request the missing range from an authoritative history read. Temporary errors leave the gap pending; they do not establish that the message never existed.
- Handle explicit retention boundaries and deletion markers as resolved non-content positions. Keep the counter independent of retained message rows; never recover it from `MAX(seq)` after history deletion.

**Dense sequences detect middle gaps, not a missing final message.** Head reconciliation in §10 is necessary either way. Density also does not make read receipts correct: opening a recent page does not prove every earlier message was read.

### When to choose sparse IDs instead

If the relational fleet or serialized write path becomes too expensive, use sparse IDs with a separately defined durable delivery/change cursor. That cursor tracks committed events; the largest display ID does not. A replayable ingestion path must connect accepted messages to recovery state. Re-fetching the latest 50 IDs is a heuristic, not a completeness guarantee.

Cassandra/ScyllaDB ordinary inserts upsert an existing primary key, making identical stable-key retries cheap. First-write-wins with payload conflict detection requires conditional acceptance (`IF NOT EXISTS`/LWT) or an equivalent authoritative ingestion stage. **Discarding density does not discard idempotency cost**, and ordinary-write benchmarks do not measure that stronger protocol. [Cassandra insert semantics](https://cassandra.apache.org/doc/stable/cassandra/developing/cql/dml.html)

**Cost and decision:** keep the dense counter here because it fits the transaction we already want. It is not worth an arbitrarily large Postgres fleet just for gap detection. Engine choice also depends on retention, range reads, replication, and operations—not merely dense versus sparse IDs.

---

## 9 · Deep dive — shared history, live fanout

### Why per-recipient content copies are the wrong default here

Materializing a full message into every member's inbox makes one 1,000-member channel send into 1,000 content writes. Most of those members may not open the channel today. All readers are asking for the same channel history, so there is no feed-style merge to precompute.

**Store one shared history; push the body to online subscribers.** Storage fanout and network fanout are independent: one durable copy does not require every live recipient to issue an immediate HTTP fetch. Recovering clients pull history; connected clients receive message events.

### Direct delivery after commit for small conversations

**The Message Service can try delivery itself once the transaction commits.** For a DM, resolve the other participant's devices (plus the sender's companion devices) through a cached device→gateway directory and send directly to their gateways. This avoids waiting for outbox polling, Kafka consumption, and channel fanout scheduling on the latency path. It does not remove the outbox write or the eventual background delivery work.

Keep the attempt bounded: for example, at most ten target devices and a 50ms RPC deadline, on an execution pool isolated from acceptance. If capacity or a route is unavailable, skip the attempt. These are tuning assumptions; large groups go straight to the asynchronous fanout path. The same authorization rules apply to both paths, and a device route is never proof of membership.

**Keep the outbox unconditional.** The direct push may succeed while its RPC reply is lost, or the process may crash before recording success. Avoid a second delivery-status transaction solely to suppress the replay. Let clients dedupe both arrivals by canonical identity; a gateway may also use a short-lived dedupe cache as an optimization. Apply unread increments and notifications idempotently too—one visible message is not enough if every duplicate rings another alert.

Messages can arrive out of order when the direct and asynchronous paths race. The server-assigned sequence and client range tracking already handle this; render in sequence order, not arrival order. The outbox path still has its own delivery lag objective because the direct attempt can be skipped or fail.

**Tradeoff:** lower latency for common small sends, in exchange for duplicate network work and route lookups in the Message Service. If the asynchronous path already meets the latency target, it remains a valid simpler baseline. Direct delivery is an optimization after durable acceptance, not a new acceptance guarantee.

### Route channels to gateways

A fanout service maintains `conversation_id → subscribed gateways` and exposes a rebuildable device→gateway directory for direct-send route lookups. The Message Service may cache these routes briefly; session generations prevent stale routing from targeting a replaced connection. Gateways hold the local mapping to authorized device sessions. Send one event per gateway with interested clients, then let that gateway write to its sockets. This is an in-memory subscription layer with leases, not one Kafka topic or consumer group per conversation. Kafka uses a bounded set of partitions to distribute events among fanout workers.

For the baseline, subscribe a device to its authorized joined conversations; clients may suppress bodies for inactive channels and retain only head hints. Membership revocation removes subscriptions and invalidates cached authorization before subsequent delivery; history endpoints always check permission. Treat stale authorization as a security failure, unlike a stale connection mapping.

**Batching depends on locality.** Five hundred recipients spread uniformly over 100 gateways touch about 99 gateways; over 10,000 gateways they touch about 488. Do not claim that grouping always reduces hundreds of recipients to a few RPCs. Large-channel fanout still consumes bandwidth and CPU.

Slack has publicly described channel servers and gateway subscriptions; that is evidence that subscriptions are a valid design, not proof of every detail proposed here. [Slack's real-time architecture](https://slack.engineering/real-time-messaging/)

**What it costs:** subscription memory/churn, outbox-to-fanout lag, and slow-client backpressure. Bound per-socket queues. If a client falls behind, send a resync hint or close the connection so bounded recovery takes over; never let one socket stall a channel. The direct DM path avoids waiting for this fanout stage, while its durable replay still uses it.

**→ Ties to the online latency target.** Large channels may need gateway/regional relay trees and read caching. That is the Discord follow-up; it does not require changing the acceptance transaction first.

---

## 10 · Deep dive — bounded recovery and unread state

### Why "send everything I missed" fails

A device returns after weeks, requests an enormous response, times out, and retries from the start. During an outage thousands of devices do this together. The durable history is intact, yet clients make no progress and overload the recovery tier.

**Use metadata first and resumable pages.** Enumerate memberships and fetch channel heads in bounded batches. Prioritize the open channel and recent history. Pin an upper sequence for each catch-up and persist pages incrementally. Later head advances start another pass; they do not enlarge the current one indefinitely. Missing middle ranges and unloaded older history are explicit local state, not one `local_max` integer.

On reconnect and foregrounding, refresh metadata; reconcile active channels at jittered intervals of at most 30s. A periodic authorization/membership refresh repairs missed joins or removals, while access checks prevent stale lists from granting access. Rate-limit sync separately from sends and return backoff guidance under overload.

A read replica can serve ordinary old-history pages. If a requested range is not visible there, retry against the primary or wait for the required replication position. A stale replica's empty response cannot close a gap. Responses state coverage and the current authorized retention boundary; requests after expiry receive an explicit history-unavailable result.

### Read position is not delivery position

Each device owns its local recovery ranges. The user's `last_read_seq` is merged with `MAX` so another device cannot move it backward. Define it as **"mark read through this position"**, including an explicit mark-as-read action, rather than proof the person viewed every row.

Debounce updates for roughly two seconds and on leaving the channel. Persist the latest pending update locally and retry until acknowledged; server-to-device hints may be coalesced because periodic sync fetches authoritative state. **Monotonic updates can supersede intermediate values; a final update still needs a delivery path.** No public read-receipt fanout is required for this product scope.

### The optimization to defer

At hundreds or thousands of memberships, repeated head scans become costly. Introduce a durable per-user change feed with an opaque continuation token for messages, membership changes, and read-state changes. It needs idempotent event application, retention, and a paginated snapshot on token expiry. A Redis sorted set ordered by last-message time is not that feed. Expiring a change token does not invalidate correctly stored message or read cursors.

**Cost:** metadata reads, client range bookkeeping, and eventually a change-feed subsystem if measurements justify it. **→ Ties to bounded work and the freshness target in §2.** Avoid the extra subsystem until the simpler scan is insufficient.

---

## 11 · Follow-up — retained history, search, and access control

### Why search should not join the send transaction

If indexing must finish before a send succeeds, a search outage becomes a messaging outage. Instead, an idempotent outbox consumer indexes messages by canonical ID in **Elasticsearch**, with an assumed freshness target of ≤5s. History remains authoritative when indexing lags. Start with Postgres text search at smaller scale; use a separate index when search competes with acceptance and history reads.

Private-channel access applies to search too. Scope candidates by tenant/channel, recheck current authorization before returning content, and propagate deletions. An old indexed document is not permission to disclose a message. Do not attempt a full search design during the base hour.

Retention is a workspace policy, not an incidental disk cleanup job. The baseline retains 90 days. A removal inside that interval leaves a non-content marker so clients can resolve the sequence. Expiring the oldest prefix advances `retained_from_seq`; the UI shows that older history is unavailable. Edits would introduce message versions and a change feed, since polling only the latest message sequence cannot discover an edit to an old message.

Longer retention is a variant: keep recent history in Postgres and archive immutable segments to S3 with a manifest and a separate restore/read path. Legal hold changes deletion, archive, and search policies together. **Cold history and expired history are different product states.**

**Cost:** duplicated indexed data, delayed search visibility, and coordinated lifecycle handling. This is the Slack-specific follow-up; E2EE key distribution is not part of the baseline.

---

## 12 · Data model, sharding, and lifecycle

### Choose placement from the transaction and read path

**Hash `conversation_id` into logical shards**, each mapped to a physical Postgres primary group. Co-locate conversation metadata, membership, messages, dedupe, read cursors, and outbox rows. One send and one thread read stay local. A workspace can span shards, so one unusually large customer does not have to fit on a single database.

Use a maintained routing map with a placement generation. Migrations copy data and perform a controlled write cutover; stale owners must stop accepting writes. Hashing alone is not failover or fencing. Database automation, connection pooling, backups, and staged schema changes are part of operating a sharded system, even when each shard is lightly loaded. Citus is one possible Postgres sharding layer; it needs workload and operational validation, not just a name on the diagram.

**The counter is hot per conversation; capacity is shared per primary.** Move busy logical shards, cache high-read history, and rate-limit automated senders. Moving a channel cannot split its own serial counter. If a single channel saturates acceptance, reassess the sequencing requirement; do not promise more shards will fix it.

The per-user membership directory is the cross-shard query: maintain a durable Postgres projection from membership events, keyed by user, and use conversation-local membership as authorization authority. Reordered membership events apply only when their membership version increases. New channels can appear optimistically for the initiating client while the directory catches up (target ≤5s). The directory can be rebuilt from canonical memberships.

### Storage decisions

| Component | Access and durability | Choice and rejected alternative |
|---|---|---|
| Conversations, membership, messages | Local acceptance transaction; `(conversation_id, seq)` range reads; survive one AZ loss | **Sharded Postgres**, synchronous cross-AZ standby, pooled connections. "Cassandra fits immutable history, but at these assumptions I value atomic acceptance more than an unmeasured throughput advantage" |
| SendDedup and counter | Unique sender/key lookup; counter locked per conversation | **Same Postgres shard.** "Redis would split the retry result from the accepted message; Postgres commits both" |
| Read cursors | Point update with `GREATEST`; user state fetched on sync | **Same Postgres shard.** "Persist the final read position; Redis-only state can lose an update that is never superseded" |
| Membership directory | Paginated per-user lookup; recoverable derived state | **Postgres projection**, shard by user. "A Redis-only list is cheap until reconnect correctness depends on rebuilding it during an outage" |
| Outbox and event bus | Atomic local event creation, then at-least-once publication | **Postgres outbox → Kafka**, replication factor 3, producer `acks=all`, minimum in-sync replicas 2. "Kafka alone does not atomically participate in the Postgres commit" |
| Live routing directory | Channel→gateways and device→gateway; rebuildable on reconnect | **Fanout workers' memory**, gateway leases and session generations; cached route lookups for direct sends. "Stale routes can fail a fast delivery attempt; the outbox and sync still recover the message" |
| Search, if requested | Text queries, derived from message events | **Elasticsearch**, target ≤5s indexing lag. "Keep search indexing off the acceptance transaction" |
| Backups / longer-history variant | Recovery and optional archived segments | **S3** for base backups/WAL and optional history archives. "A database replica is not protection against accidental deletion" |

### Lifecycle — what happens after day 90

| State | Baseline policy | User-visible or operational consequence |
|---|---|---|
| Messages | Online for 90 days, then expire by policy; recent history p99 target <300ms | Explicit retention boundary, not a false missing-message error. Admission control may delay bulk catch-up |
| SendDedup | Retain compact result/hash for 90 days; promise retries for 7 days | Independent of body deletion; privacy policy must cover this retained metadata. No indefinite retry guarantee |
| Sequence and membership | Retain while conversation exists; counter never rewinds | Deleting bodies cannot cause sequence reuse. Deleted conversations reject new sends |
| Read cursors | Retain while membership exists; clean up after removal | A new device gets unread state but still fetches its own message bodies |
| Outbox | Delete published rows after 24h; never age out unpublished events | Unpublished growth triggers alerts/backpressure. Relay lag is part of latency monitoring |
| Kafka | Seven-day replay retention | A consumer behind retention requires explicit backfill/rebuild, not silent offset reset |
| Search | Same logical retention/deletion policy as messages | Rebuildable; temporarily stale search does not change authorization or history |
| Backups | Thirty-day rolling recovery window; tested WAL replay | Backup deletion policy and restore procedure must reapply expired/deleted data rules before serving |
| Optional S3 history archive | Beyond 90 days only if the product offers longer history; archive by channel/time segment | Manifest maps ranges to objects; old-page target 1–5s, separate from interactive hot-history latency |

Partition large message tables by acceptance time **within each physical shard** to ease expiration, retaining an index on conversation/sequence in each time partition. A bounded history query can visit relevant partitions. Keep the retry-key uniqueness in a separate co-located dedupe table: adding time to the message table's partition key must not make one retry appear new in another partition. Postgres partitioned-table unique constraints must include the partition key. [Postgres partitioning limitations](https://www.postgresql.org/docs/17/ddl-partitioning.html)

Size the physical fleet from the **maximum of write capacity, read capacity, retained storage, and failure requirements**. If that fleet becomes uneconomic, benchmark Cassandra/ScyllaDB or DynamoDB with the actual idempotency and recovery protocol. Do not compare a bare upsert benchmark to a complete relational transaction and call the ratio a database law.

---

## 13 · Traps — the ranked list

1. **Sizing from DAU or average writes alone.** State messages/day, peak multiplier, retention, and complete-transaction capacity. Logical shards are not physical machines.
2. **Declaring the database trivial after assuming thousands of shards.** Throughput distributes; fleet operations and storage still cost money and engineering time.
3. **Acking before the message and outbox commit durably.** A successful send must survive the failure model you stated.
4. **Trusting a client retry ID or dropping older sequences.** Scope IDs to authenticated senders, compare payloads, and dedupe by identity—not by `seq ≤ local_max`.
5. **Skipping a gap after a few empty reads.** Only authoritative coverage/deletion/retention information closes it.
6. **Assuming dense numbering eliminates sync.** A lost final event has no successor to expose it.
7. **Treating Kafka as the transaction's outbox.** Name the local outbox row and the retrying relay; make downstream effects idempotent.
8. **Resetting read state to the head on reconnect.** Recovery position, unloaded history, and user read position mean different things.
9. **Broadcasting per-message read receipts to the whole channel.** Slack-style unread state needs no such feature or amplification.
10. **Promising subscriptions or batching are free.** Account for membership churn, actual gateway distribution, and slow-client queues.
11. **Building the WhatsApp branch inside a Slack answer.** E2EE changes key distribution and search; transient delivery retention is a separate policy. Both products still need durable acceptance.

For general interview mechanics, see [the interview mechanics page](#/designs/interview-mechanics). Keep the hour on the two committed dives; sparse IDs, archive restoration, and search internals are follow-ups.

---

## 14 · The five-minute skeleton

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 644" role="img" aria-label="Slack five-minute skeleton with ten numbered points. Scope and sizing, client and acceptance transaction, durability and channel fanout, recovery and unread state, retention and storage alternatives. Numbers match the accompanying interview outline.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Slack: shared retained history + transactional acceptance + recoverable live delivery.</text>
  <rect class="dg-box" x="30" y="88" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="257.5" y="114.5">Scope</text>
  <text class="dg-s dg-c" x="257.5" y="130.5">channels / DMs · 90-day history</text>
  <text class="dg-s dg-c" x="257.5" y="146.5">unread state, no public read receipts</text>
  <circle class="dg-num" cx="30" cy="88" r="9"></circle>
  <text class="dg-num-t" x="30" y="91.4">1</text>
  <rect class="dg-box" x="515" y="88" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="742.5" y="114.5">Size the whole workload</text>
  <text class="dg-s dg-c" x="742.5" y="130.5">assume 1 B messages/day → 60 k peak/s</text>
  <text class="dg-s dg-c" x="742.5" y="146.5">writes + reads + storage + failure capacity</text>
  <circle class="dg-num" cx="515" cy="88" r="9"></circle>
  <text class="dg-num-t" x="515" y="91.4">2</text>
  <rect class="dg-box" x="30" y="194" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="257.5" y="220.5">Client</text>
  <text class="dg-s dg-c" x="257.5" y="236.5">persist retry ID before sending</text>
  <text class="dg-s dg-c" x="257.5" y="252.5">optimistic echo → canonical ack</text>
  <circle class="dg-num" cx="30" cy="194" r="9"></circle>
  <text class="dg-num-t" x="30" y="197.4">3</text>
  <rect class="dg-box" x="515" y="194" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="742.5" y="220.5">Conversation-local transaction</text>
  <text class="dg-s dg-c" x="742.5" y="236.5">permission + dedupe + counter</text>
  <text class="dg-s dg-c" x="742.5" y="252.5">message + outbox</text>
  <circle class="dg-num" cx="515" cy="194" r="9"></circle>
  <text class="dg-num-t" x="515" y="197.4">4</text>
  <rect class="dg-box" x="30" y="300" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="257.5" y="326.5">Durability before acknowledgement</text>
  <text class="dg-s dg-c" x="257.5" y="342.5">cross-AZ replicated commit</text>
  <text class="dg-s dg-c" x="257.5" y="358.5">no safe primary → pending send</text>
  <circle class="dg-num" cx="30" cy="300" r="9"></circle>
  <text class="dg-num-t" x="30" y="303.4">5</text>
  <rect class="dg-box" x="515" y="300" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="742.5" y="326.5">Live delivery</text>
  <text class="dg-s dg-c" x="742.5" y="342.5">DM: direct gateway attempt after commit</text>
  <text class="dg-s dg-c" x="742.5" y="358.5">always outbox → Kafka → fanout</text>
  <circle class="dg-num" cx="515" cy="300" r="9"></circle>
  <text class="dg-num-t" x="515" y="303.4">6</text>
  <rect class="dg-box" x="30" y="406" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="257.5" y="432.5">Bounded recovery</text>
  <text class="dg-s dg-c" x="257.5" y="448.5">membership / heads → range pages</text>
  <text class="dg-s dg-c" x="257.5" y="464.5">periodic active-channel reconciliation</text>
  <circle class="dg-num" cx="30" cy="406" r="9"></circle>
  <text class="dg-num-t" x="30" y="409.4">7</text>
  <rect class="dg-box" x="515" y="406" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="742.5" y="432.5">Client and unread state</text>
  <text class="dg-s dg-c" x="742.5" y="448.5">identity dedupe + covered ranges</text>
  <text class="dg-s dg-c" x="742.5" y="464.5">user read cursor = MAX; retry final update</text>
  <circle class="dg-num" cx="515" cy="406" r="9"></circle>
  <text class="dg-num-t" x="515" y="409.4">8</text>
  <rect class="dg-box" x="30" y="512" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="257.5" y="538.5">Lifecycle</text>
  <text class="dg-s dg-c" x="257.5" y="554.5">explicit history expiry; preserve counter</text>
  <text class="dg-s dg-c" x="257.5" y="570.5">dedupe retention; asynchronous search</text>
  <circle class="dg-num" cx="30" cy="512" r="9"></circle>
  <text class="dg-num-t" x="30" y="515.4">9</text>
  <rect class="dg-box" x="515" y="512" width="455" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="742.5" y="538.5">Storage tradeoff</text>
  <text class="dg-s dg-c" x="742.5" y="554.5">Postgres for local transaction simplicity</text>
  <text class="dg-s dg-c" x="742.5" y="570.5">sparse + another store if measured need</text>
  <circle class="dg-num" cx="515" cy="512" r="9"></circle>
  <text class="dg-num-t" x="515" y="515.4">10</text>
  <text class="dg-note" x="30" y="625">Sparse IDs change completeness detection, not the need for idempotency or reliable recovery.</text>
</svg>
</div>

<p class="diagram-cap">Keep acceptance, delivery, and recovery separate on the board. The transaction is the correctness shortcut; the bounded recovery path is still required.</p>

1. **Scope:** channels/DMs, shared 90-day history, live delivery, unread state; no calls or public read receipts.
2. **Size:** assumed 1B messages/day → 60k peak sends/sec; benchmark complete sends and also size storage/read capacity.
3. **Client:** persist retry ID and pending message; reconcile optimistic echo on ack.
4. **Acceptance:** route by conversation; one Postgres transaction for membership check, dedupe, counter, message, and outbox.
5. **Durability:** cross-AZ commit before ack; no safe primary means pending sends, not speculative success.
6. **Delivery:** after commit, try direct gateway delivery for DMs; always retain outbox → Kafka → fanout for durable delivery work. Both paths carry the same message identity.
7. **Recovery:** bounded membership/head scan, paginated missing ranges, and periodic active-channel reconciliation.
8. **State:** unique local message identity and covered ranges; per-user read cursor merged with `MAX` and retried until acknowledged.
9. **Lifecycle:** history expires explicitly; dedupe and counter survive body cleanup; search consumes events asynchronously.
10. **Tradeoff:** sharded Postgres is a workload choice. Consider sparse IDs and another store if measured fleet cost justifies additional recovery machinery.

---

## 15 · Variants — what actually changes

**The governing axis: live delivery breadth per accepted message.** History and encryption are independent modifiers; they do not follow automatically from recipient count.

| Delivery breadth | Variant | Delta from the baseline |
|---|---|---|
| A few devices | DMs / small-team chat | Direct device→gateway lookup may be simpler than channel subscriptions; same acceptance and sync protocol |
| Tens to hundreds online | Slack-like channels | This page: shared retained history, channel subscriptions, unread state, relational transactions |
| Tens of thousands online | Discord / very large channels | Hierarchical fanout, read caching/coalescing, slow-client isolation, selective presence; storage choice needs a separate capacity analysis |
| Hundreds of thousands, lossy product | Live comments | If product permits dropping messages and no history, relax delivery/retention and sample under overload |
| Many authors per personalized read | News feed | Materialized per-user timelines can win because the read is a merge, unlike one shared channel |

**If the interviewer pivots to WhatsApp:** retain the distinction between durable acceptance and eventual device delivery, but introduce cryptographic device identities, key distribution, and history/bootstrap policy. WhatsApp describes per-device encryption for individual messaging and Sender Keys for groups. **The server can store ciphertext without reading it; E2EE does not itself prohibit shared group ciphertext or encrypted archives.** Store-and-forward systems retain pending messages under a deletion/expiry policy rather than keeping a Slack-style readable history. [WhatsApp multi-device design](https://engineering.fb.com/2021/07/14/security/whatsapp-multi-device/), [encrypted server-side history example](https://engineering.fb.com/2023/12/06/security/building-end-to-end-security-for-messenger/)

**If the interviewer raises the volume to 100B messages/day:** redo the fleet and storage calculation. Do not preserve dense numbering at any cost. Compare relational transactions with sparse message IDs plus a durable recovery cursor, and include conditional acceptance, replication, and operational overhead in both benchmarks.
