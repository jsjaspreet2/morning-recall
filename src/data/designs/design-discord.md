# Design Discord — Guild Fanout, Sessions & Backpressure

## The question

> *"Design Discord text chat and presence. Communities have channels, and a large community can have tens of thousands of people connected at once. How do messages reach them, and what happens when connections fail?"*

**The product.** People join communities called servers, with public and private channels inside them. Messages become shared history. An open client receives new activity and shows who's around; opening another channel fetches its recent conversation. A sleeping laptop reconnects without downloading the entire community again.

**What a working system delivers**

- Accepted messages remain in channel history even when live delivery fails.
- Connected users receive activity relevant to what they can see and are watching.
- Brief disconnects can replay missed session events; longer failures recover through fresh state and history reads.
- Large communities stay responsive by limiting unnecessary fanout and isolating slow clients.

**Why this gets asked.** Shared history and live distribution are separate workloads. A popular channel can turn one stored message into thousands of deliveries and simultaneous history reads. The difficult decisions are how much work one guild owner performs, what can be dropped under pressure, and how clients recover.

---

**Archetype:** Real-time messaging & delivery.
**Cousins that reuse ~70% of this page:** Slack channels, community chat, live collaboration events, multiplayer lobbies.

**What's actually being graded:** selective fanout, state ownership, backpressure, and honest recovery guarantees. Message acceptance still needs permissions, idempotency, and durability; a modest per-channel write rate does not make the database free.

**Contrast to have ready:** *The Slack page emphasizes transactional acceptance and retained channel history. This page keeps that shared-history model but pushes online fanout, presence, and reconnect load harder. The distinction is workload emphasis—not "Slack uses an outbox, Discord uses BEAM." An outbox is durable dispatch work; BEAM is an actor runtime that can consume that work or receive direct calls.*

**Evidence boundary.** Discord's March 2026 engineering account describes **HTTP → API database write → gRPC into Elixir → guild/session processes → WebSockets**. This page uses that published live path, then labels proposed recovery and storage details as interview choices. That article does not document every retry mechanism inside Discord. [Published message flow](https://discord.com/blog/tracing-discords-elixir-systems-without-melting-everything)

---

## 0 · The 60-second frame

> "I'll scope to text channels and presence, with permissions on both sending and receiving. Store the message durably, then call the live fanout tier directly. A guild owner maintains shared community state; large guilds offload recipient work to relays, which push to session processes and sockets. I'll go deep on selective fanout and backpressure, then on reconnect: session replay repairs a surviving event stream, while fresh state and history reads handle lost sessions. Sparse message IDs and session sequence numbers do different jobs. I'll name the stronger durable-dispatch option if every accepted message must trigger downstream processing without relying on clients to reload."

**The decision to state:** the baseline preserves accepted history but treats live dispatch as best effort. It does not promise a durable per-device inbox or complete background delivery of every message to every offline client.

---

## 1 · Functional requirements

1. **Send and retrieve channel messages**, checking access and making supported retries return the same accepted message.
2. **Push relevant activity to authorized online sessions**, with resumable connections when session state survives.
3. **Show approximate presence**, aggregated across a user's devices and restricted to the community/member views being displayed.

**Out of scope:** voice/video, search implementation, moderation, reactions, threads, and role administration. Role evaluation and revocation remain in scope because they protect private-channel content. Attachments are authorized object-store references; their bytes do not pass through the event fanout tier.

**History policy for the exercise:** retain channel history until deletion under guild policy; no guaranteed offline per-recipient delivery. Edits and deletes are follow-ups requiring their own change events. Do not silently extend a message-only reconciliation scheme to mutable history.

---

## 2 · Non-functional requirements

| Property | Interview target | What it commits us to |
|---|---|---|
| Live latency | p99 <500ms from send to interested online recipient under admitted load | Includes storage, gRPC, mailbox wait, fanout, and socket queues; slow clients cannot hold up the guild |
| Acceptance durability | RPO 0 for a single node/AZ failure | Three replicas across AZs, quorum writes and reads, durable commit-log settings verified in the deployed version; ack only after successful persistence |
| Failure behavior | Survive one AZ loss if remaining replicas and compute have capacity | Without a storage quorum, reject/delay acceptance. A whole-region disaster is outside the zero-loss promise; add backup/restore policy in §12 |
| Availability | 99.95% monthly send/read target | A measured objective; selectively degrading live updates does not permit losing accepted history |
| Ordering | Stable message-ID order for settled channel history; monotonic event sequence per session | Neither promises that concurrent HTTP sends commit or arrive live in ID order |
| Replay | Proposed 60s window, bounded by bytes/events as well as age | Resume only when the original session stream is available; otherwise fresh identification and bounded state fetch |
| Recovery | Reconcile the open channel's recent page on focus/reconnect and every ≤30s, with jitter | Repairs the current view, not proof of complete offline delivery; stronger completeness needs durable change cursors (§7) |
| Presence | Proposed 20s heartbeat, 60s expiry, ≤2s coalescing | Explicit disconnects can update sooner; abrupt failure can appear online for roughly 62s |
| Bounded work | History pages ≤50 messages / 256KiB; ≤4 parallel pulls/client; gateway-loss recovery target ≤60s under admission control | Paginated progress, jitter, and load shedding rather than unlimited resync or queue growth |

**The sentence that earns the point:** *"Durable history, session replay, and a live push are three different promises. I'll specify which survives each failure rather than call all of them delivery."*

---

## 3 · Numbers that reframe the problem

**The workload below is assumed for the interview, not a claim about current Discord traffic.** Historical implementation reports are useful evidence, not today's capacity plan.

1. **4B messages/day ≈46k sends/sec average; assume 150k/sec peak.** Size the full acceptance path, including retry enforcement and replication. This is 20× below the Slack page's WhatsApp-scale variant of 3M/sec, but still a distributed workload.
2. **15M concurrent sessions at 50k/gateway implies 300 gateways before headroom.** Assume 500 provisioned gateways for this exercise, averaging 30k sessions each. Losing a typical gateway creates ~30k reconnects, not millions; correlated AZ failures are larger events.
3. **At 10KiB/session, base connection state alone is about 150GiB fleet-wide.** Replay is extra: even a 64KiB allowance per session adds nearly 1TiB if fully used. Measure observed event rates; do not describe buffers as a few free kilobytes.
4. **Assume 50 interested online recipients/send on average: 150k × 50 =7.5M deliveries/sec.** A single event for 50k recipients spread across 500 gateways reduces to at most 500 inter-node body transfers, plus recipient metadata and 50k final socket writes. A 100× reduction is this example's ratio, not a universal gain.
5. **Presence can dominate particular guilds.** One status change across 20 guilds with 2k interested sessions each would produce 40k deliveries before overlap/deduplication. Actual cost depends on churn and subscriptions; this does not establish that presence globally exceeds messages.
6. **At 1KB/message, history grows ~4TB/day or 1.46PB/year before indexes and replication.** Storage and hot history reads can dominate fleet sizing even when channel writes are modest. Retention, caching, repair capacity, and compaction belong in the database decision.

**The useful scale question:** how much work lands on the hottest guild, relay, session, or database partition? A global average cannot prove that any one of them is safe.

---

## 4 · Core entities

- **Guild** — community metadata and shared member/role state.
- **Channel** — visibility and history unit inside a guild.
- **Message** — canonical sparse `message_id`, `channel_id`, `author_id`, content, server acceptance metadata; time-bucketed history placement.
- **SendAttempt** — authenticated sender/channel/nonce → canonical ID, bucket, request hash, and payload during the retry window.
- **Session** — one client connection's identity, host/generation, subscriptions, last processed event sequence, bounded replay state.
- **Presence** — aggregate user status derived from live sessions plus explicit user preferences.
- **ReadState** — user/channel position indicating "mark read through this message," separate from delivery completeness.

**Keep three values separate:** the client's nonce identifies a retried send; the server's message ID identifies/sorts stored content; the session's event sequence identifies a position in that session's stream. A session stream includes presence and other events and is not a channel history log.

---

## 5 · API

```text
POST /channels/{id}/messages
     { content, nonce } -> { messageId, acceptedAt }
GET  /channels/{id}/messages?before=&limit=50
PUT  /channels/{id}/read { messageId }

WebSocket (conceptual first-party protocol):
→ identify { credentials }
← ready    { sessionId, resumeCredential, initialStatePages }
→ subscribe { guildId, channelIds, visibleMemberRange }
← dispatch { sessionSeq, type, data }
→ heartbeat { lastProcessedSessionSeq }
← heartbeatAck
→ resume   { sessionId, resumeCredential, lastProcessedSessionSeq }
← resumed OR invalidSession
```

**Why HTTP for sends:** explicit request/result and existing authentication/rate-limiting infrastructure. WebSocket sends are also valid if correlation, retries, and errors are defined. HTTP streaming can push too; this split is a design choice, not a transport impossibility.

**Nonce enforcement is server-side.** Authenticate, check send permission, parse a bounded key, and scope it to sender/channel. Identical retry returns the canonical result; different payload under the same accepted key is a conflict. Client matching of an optimistic echo is separate from server deduplication (§11).

**Public API versus this design:** Discord's developer Gateway documents server-provided heartbeat intervals, session IDs, sequence numbers, resume URLs, and invalid-session fallback. Its public message API supports `enforce_nonce`, with a same-author uniqueness window of a few minutes. Bot `intents` select event classes; they are not the same as a first-party client's visible-channel/member subscriptions. The protocol above is deliberately conceptual. [Gateway documentation](https://docs.discord.com/developers/events/gateway), [message API](https://docs.discord.com/developers/resources/message)

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 570" role="img" aria-label="Discord-inspired live path. HTTP API accepts an authenticated idempotent message into ScyllaDB through data services, then directly calls the BEAM guild service over gRPC. Guild owners route to relays that filter authorized interested sessions and batch by node. Session processes have bounded in-memory mailboxes, replay and socket queues. A Redis directory only locates surviving sessions. Postgres owns role metadata. This live path does not depict an atomic durable dispatch guarantee.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Durable history first; direct gRPC into BEAM for live fanout. Mailboxes are in memory.</text>
  <text class="dg-lane" x="20" y="86">ACCEPT — HTTP REQUEST / RESULT</text>
  <rect class="dg-box" x="20" y="110" width="240" height="78" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="137.5">API + data services</text>
  <text class="dg-s dg-c" x="140" y="153.5">auth + sender permission</text>
  <text class="dg-s dg-c" x="140" y="169.5">nonce → canonical message</text>
  <path class="dg-box" d="M 330,117 L 330,181 A 135,7 0 0 0 600,181 L 600,117 A 135,7 0 0 0 330,117 Z"></path>
  <path class="dg-box" d="M 330,117 A 135,7 0 0 0 600,117" style="fill:none"></path>
  <text class="dg-t dg-c" x="465" y="141">ScyllaDB</text>
  <text class="dg-s dg-c" x="465" y="157">send attempts + history</text>
  <text class="dg-s dg-c" x="465" y="173">channel / bucket placement</text>
  <path class="dg-line" d="M 260,149 L 322,149"></path>
  <path class="dg-head" d="M 322,154 L 322,144 L 330,149 Z"></path>
  <text class="dg-lbl dg-c" x="294" y="138">persist</text>
  <path class="dg-box" d="M 710,117 L 710,181 A 135,7 0 0 0 980,181 L 980,117 A 135,7 0 0 0 710,117 Z"></path>
  <path class="dg-box" d="M 710,117 A 135,7 0 0 0 980,117" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="141">Postgres metadata</text>
  <text class="dg-s dg-c" x="845" y="157">guilds · channels · roles</text>
  <text class="dg-s dg-c" x="845" y="173">versioned authorization</text>
  <text class="dg-lane" x="310" y="254">LIVE — ACTOR FANOUT</text>
  <rect class="dg-box" x="20" y="310" width="240" height="84" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="340.5">Guild owner (BEAM)</text>
  <text class="dg-s dg-c" x="140" y="356.5">shared guild state</text>
  <text class="dg-s dg-c" x="140" y="372.5">routing, not history ordering</text>
  <rect class="dg-box" x="365" y="310" width="270" height="84" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="340.5">Relays for large guilds</text>
  <text class="dg-s dg-c" x="500" y="356.5">recipient permission checks</text>
  <text class="dg-s dg-c" x="500" y="372.5">interested sessions · batch by node</text>
  <rect class="dg-box" x="740" y="310" width="240" height="84" rx="8"></rect>
  <text class="dg-t dg-c" x="860" y="340.5">Session processes</text>
  <text class="dg-s dg-c" x="860" y="356.5">bounded mailbox + replay</text>
  <text class="dg-s dg-c" x="860" y="372.5">per-session event sequence</text>
  <path class="dg-line" d="M 140,188 L 140,302"></path>
  <path class="dg-head" d="M 135,302 L 145,302 L 140,310 Z"></path>
  <text class="dg-lbl dg-c" x="225" y="227">gRPC after storage</text>
  <path class="dg-line" d="M 260,352 L 357,352"></path>
  <path class="dg-head" d="M 357,357 L 357,347 L 365,352 Z"></path>
  <path class="dg-line" d="M 635,352 L 732,352"></path>
  <path class="dg-head" d="M 732,357 L 732,347 L 740,352 Z"></path>
  <path class="dg-box" d="M 20,457 L 20,509 A 120,7 0 0 0 260,509 L 260,457 A 120,7 0 0 0 20,457 Z"></path>
  <path class="dg-box" d="M 20,457 A 120,7 0 0 0 260,457" style="fill:none"></path>
  <text class="dg-t dg-c" x="140" y="475">Redis session directory</text>
  <text class="dg-s dg-c" x="140" y="491">host + generation + lease</text>
  <text class="dg-s dg-c" x="140" y="507">does not preserve replay</text>
  <rect class="dg-box" x="365" y="450" width="270" height="66" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="471.5">Presence aggregation</text>
  <text class="dg-s dg-c" x="500" y="487.5">all devices · timeout + disconnect</text>
  <text class="dg-s dg-c" x="500" y="503.5">coalesced / visible members only</text>
  <rect class="dg-box" x="740" y="450" width="240" height="66" rx="8"></rect>
  <text class="dg-t dg-c" x="860" y="471.5">Clients over WebSocket</text>
  <text class="dg-s dg-c" x="860" y="487.5">message-identity dedupe</text>
  <text class="dg-s dg-c" x="860" y="503.5">settle into history order</text>
  <path class="dg-line" d="M 860,394 L 860,442"></path>
  <path class="dg-head" d="M 855,442 L 865,442 L 860,450 Z"></path>
  <path class="dg-line" d="M 710,150 L 670,150 L 670,280 L 580,280 L 580,302"></path>
  <path class="dg-head" d="M 575,302 L 585,302 L 580,310 Z"></path>
  <text class="dg-lbl dg-c" x="582" y="222">role / channel versions</text>
  <path class="dg-line" d="M 140,394 L 140,442"></path>
  <path class="dg-head" d="M 135,442 L 145,442 L 140,450 Z"></path>
  <text class="dg-lbl dg-c" x="208" y="426">session lookup</text>
  <path class="dg-line" d="M 500,450 L 500,402"></path>
  <path class="dg-head" d="M 505,402 L 495,402 L 500,394 Z"></path>
  <text class="dg-note" x="20" y="551">If storage succeeds but dispatch fails, RESUME cannot invent the missing event. See the recovery paths below.</text>
</svg>
</div>

<p class="diagram-cap">Published live-path shape, with proposed storage and recovery choices. BEAM implements the guild/relay/session tier; it does not replace a transactional outbox. Recipient authorization is separate from permission to send.</p>

### Flow A — durable acceptance, direct live dispatch

1. The client persists a nonce and pending message, then sends HTTP. The API authenticates and verifies send permission.
2. Resolve the canonical send attempt and persist the message in ScyllaDB through the data-service tier (§11). A retry must reuse the same canonical ID and bucket. Acknowledge only after durable history storage succeeds.
3. After storage, the API directly calls the guild service over gRPC with the canonical message. Use a bounded deadline and limited retries; recipient delivery is not part of the storage transaction.
4. The guild owner routes to interested sessions, or delegates to relays for large guilds. Relays evaluate recipient visibility from current role/channel state and group deliveries by destination node.
5. Session processes append dispatches to their bounded replay stream and push over WebSockets. Clients dedupe message identity and render using canonical history order, not arrival order.
6. **Failure path:** storage succeeds but API-to-guild dispatch fails. The message remains in history. Limited RPC retries may help; a process crash can end them. A recent-history refresh can repair the currently displayed page, but `RESUME` cannot replay an event that never reached the session. Durable dispatch recovery is a separate extension (§7).

### Flow B — transport reconnect versus session loss

1. A lost socket reconnects with exponential backoff and jitter, using the previous session identity and last processed event sequence.
2. If the original session process/replay buffer is still accessible and covers the gap, replay through its current head, then continue live events. Clients process duplicates safely.
3. If the host died, the buffer overflowed, or the session expired, return `invalidSession`. Authenticate a new session, fetch memberships/subscriptions in pages, and retrieve the active channel's recent history first.
4. **Failure path:** pause and resume paginated recovery under admission control. Do not promise that a Redis route entry resurrects a buffer destroyed with its host. A full-state fallback is required unless replay state is stored independently.

### Flow C — presence

1. Heartbeats maintain per-session liveness. Explicit status changes and clean disconnects can update it immediately.
2. Combine sessions into user status, respecting preferences such as invisible/idle. One device disconnecting does not take another active device offline.
3. Coalesce transitions and publish only to interested, authorized member views.
4. **Failure path:** no clean disconnect arrives after a crash. Session expiry eventually removes that contribution and triggers recomputation. The coalescing budget is included in the advertised staleness bound.

---

## 7 · Deep dive — mailboxes, replay, and durable recovery

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 590" role="img" aria-label="Recovery decision diagram. A disconnected client tries resume. A surviving session stream with retained coverage replays events. A lost or expired stream requires a fresh session and paginated state and history. Independently, a database message never dispatched has no session event to replay; history refresh repairs the current view, while stronger completeness requires durable dispatch and change cursors.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Session replay and history reconciliation cover different failures.</text>
  <rect class="dg-box" x="30" y="95" width="250" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="155" y="121.5">Connection lost</text>
  <text class="dg-s dg-c" x="155" y="137.5">reconnect with jitter</text>
  <text class="dg-s dg-c" x="155" y="153.5">session ID + last processed seq</text>
  <rect class="dg-box" x="375" y="95" width="260" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="505" y="121.5">Can the stream resume?</text>
  <text class="dg-s dg-c" x="505" y="137.5">session state survives</text>
  <text class="dg-s dg-c" x="505" y="153.5">buffer still covers the gap</text>
  <path class="dg-line" d="M 280,133 L 367,133"></path>
  <path class="dg-head" d="M 367,138 L 367,128 L 375,133 Z"></path>
  <rect class="dg-good" x="715" y="95" width="250" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="840" y="121.5">Replay session events</text>
  <text class="dg-s dg-c" x="840" y="137.5">then continue live</text>
  <text class="dg-s dg-c" x="840" y="153.5">duplicates remain possible</text>
  <path class="dg-line" d="M 635,133 L 707,133"></path>
  <path class="dg-head" d="M 707,138 L 707,128 L 715,133 Z"></path>
  <text class="dg-lbl dg-c" x="675" y="123">yes</text>
  <rect class="dg-box" x="375" y="240" width="260" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="505" y="266.5">New session + state</text>
  <text class="dg-s dg-c" x="505" y="282.5">invalid / expired / lost session</text>
  <text class="dg-s dg-c" x="505" y="298.5">bounded membership subscriptions</text>
  <path class="dg-line" d="M 505,171 L 505,232"></path>
  <path class="dg-head" d="M 500,232 L 510,232 L 505,240 Z"></path>
  <text class="dg-lbl dg-c" x="550" y="209">no</text>
  <rect class="dg-box" x="715" y="240" width="250" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="840" y="266.5">History API</text>
  <text class="dg-s dg-c" x="840" y="282.5">active channel first</text>
  <text class="dg-s dg-c" x="840" y="298.5">page older messages on demand</text>
  <path class="dg-line" d="M 635,278 L 707,278"></path>
  <path class="dg-head" d="M 707,283 L 707,273 L 715,278 Z"></path>
  <path class="dg-div" d="M 20,355 L 980,355"></path>
  <text class="dg-lane" x="30" y="390">SEPARATE FAILURE — STORED, BUT NEVER DISPATCHED</text>
  <rect class="dg-warn" x="30" y="415" width="280" height="82" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="444.5">No session event exists</text>
  <text class="dg-s dg-c" x="170" y="460.5">a successful RESUME can omit it</text>
  <text class="dg-s dg-c" x="170" y="476.5">refresh recent history to repair view</text>
  <rect class="dg-box" x="380" y="415" width="585" height="82" rx="8"></rect>
  <text class="dg-t dg-c" x="672.5" y="444.5">Stronger requirement: durable dispatch + recovery cursor</text>
  <text class="dg-s dg-c" x="672.5" y="460.5">acceptance-coupled record / change stream → retrying relay → guild</text>
  <text class="dg-s dg-c" x="672.5" y="476.5">direct gRPC may remain the fast path; define retention and dedupe</text>
  <path class="dg-line" d="M 310,456 L 372,456"></path>
  <path class="dg-head" d="M 372,461 L 372,451 L 380,456 Z"></path>
  <text class="dg-note" x="30" y="548">Sparse message IDs sort history. Session seq orders a session stream. Neither alone proves complete offline delivery.</text>
</svg>
</div>

<p class="diagram-cap">A lost socket can resume only if its event stream survives. A message that never reached that stream needs independent history or durable-dispatch recovery; replay cannot repair an event that does not exist.</p>

### Why "BEAM instead of Kafka" is the wrong comparison

BEAM is the Erlang runtime used by Elixir. Lightweight processes communicate through messages queued in memory. Guild ownership makes shared community state local; it does not make the mailbox durable or atomically connected to the message database. Successful submission does not prove the receiver processed the event. Erlang preserves signal order from one sender to one receiver, not one global order across independent API senders. [Erlang message passing](https://www.erlang.org/blog/message-passing/)

**The baseline calls the actor layer directly.** This avoids a durable broker hop on the latency path and keeps live routing close to session state. It still has gRPC buffers, process mailboxes, and socket queues. Monitor queue length/age and processing time; an actor runtime is not automatic backpressure.

### Two recovery paths, with different coverage

**Session replay** repairs events already in a surviving session stream. A brief network interruption is its ideal case. Age, event count, and byte limits bound memory; overflow or host failure forces a new session. Planned drains may preserve or hand off sessions, but unplanned destruction still needs fallback. A directory locates state; it does not replicate it.

**History reconciliation** fetches stored messages regardless of whether they were dispatched. Refresh the active channel on focus/reconnect and periodically; use bounded pagination for older history. A recent-page refresh repairs the current view but cannot prove every older message was delivered. Sparse IDs cannot reveal a missing middle row, and a late commit with a lower ID can be missed by an `after=max_seen` query.

### If the requirement is stronger, add durable dispatch work

If every accepted message must eventually reach downstream processors independently of client activity, persist a dispatch obligation with acceptance, or consume an appropriate database change stream with defined retention, replay, and dedupe. A relay can call the **same BEAM guild services**; direct post-store gRPC can remain the fast path. Both carry canonical event/message identity.

This is the Slack page's outbox tradeoff applied to another fanout implementation. Postgres makes the local outbox transaction straightforward; with ScyllaDB, specify the supported atomic write/change-stream mechanism and recovery model rather than drawing a second independent write and calling it reliable. Complete device catch-up additionally needs a durable change cursor or equivalent coverage protocol; replaying recent display IDs is insufficient.

**Cost:** durable dispatch adds writes/log retention and worker operations; memory-only dispatch needs explicit reconciliation and weaker guarantees. **→ Ties to the recovery and durability rows in §2.** The baseline is honest about this distinction; published direct gRPC is not evidence that Discord lacks other recovery mechanisms.

---

## 8 · Deep dive — selective fanout and large-guild relays

### Why the obvious answer fails

Sending every guild event to every connected member wastes serialization, permission checks, network capacity, and client work. Writing a full inbox copy per recipient additionally duplicates shared channel history. A connected user may belong to many communities while actively viewing only one.

**First reduce recipients; then distribute the remaining work.** Maintain active versus passive subscriptions. Interested sessions receive bodies and relevant presence; inactive views receive limited hints or refresh on activation. Authorization constrains both groups. This is a product/freshness trade, not license to omit events silently from a promised reliable stream.

Discord reported that about 90% of user–guild connections in large communities were passive, substantially reducing fanout. It retained a central guild process while moving session fanout and permission work into relays. That supports a layered design, not the claim that every large guild must abandon one central owner. [Large-guild architecture](https://discord.com/blog/maxjourney-pushing-discords-limits-with-a-million-plus-online-users-in-a-single-server)

### What the owner and relays each do

- **Guild owner:** coordinates shared guild state and routing. It is a stateful serialization point for its own processing, not automatically the writer of ordered channel history.
- **Relays:** own subsets of interested sessions, maintain the role/channel information needed for visibility, and perform recipient filtering. Revocation must update or invalidate that state; stale permission state is not merely a missed-delivery problem.
- **Node-local fanout:** sends one body per destination node with recipient metadata, then writes to local sessions. Savings depend on recipients per node; total socket writes and egress remain.

For hot guilds, add relays and offload expensive enumeration/serialization from the owner. Avoid copying the entire member population into every relay; replicate only needed state. Move ownership with a controlled generation/cutover so obsolete processes cannot remain authoritative.

### What it costs: mailbox and socket backpressure

Bound ingress and relay work. Coalesce replaceable presence updates; prioritize message events; isolate slow sockets with byte/age limits. When a client exceeds its replay/queue budget, require resync or disconnect rather than allowing its backlog to consume the node. Under sustained overload, reject new work or delay delivery while preserving already accepted history.

**Ordering trade:** API workers may commit and call the guild in different orders. Session sequence records that session's event order; clients settle messages into sparse-ID history order, with possible reordering. If the product requires a stable append order with no late insertion, introduce a per-channel ordered acceptance mechanism and account for its coordination/failover cost.

**→ Ties to live latency and bounded recovery.** The correct degraded state may be a delayed live update. "Never degrade live delivery" is not a feasible overload policy.

---

## 9 · Deep dive — presence as replaceable state

### Why the naive model explodes

A boolean update looks cheap until it fans out across every guild membership. Flapping connectivity can multiply a single user's transitions into thousands of recipient events. But its priority is lower than message history: the latest status supersedes earlier intermediate states.

**Use session liveness plus aggregation.** For this exercise, heartbeat every 20s, expire after 60s, and coalesce for up to 2s. Those are internally consistent assumptions; an actual protocol negotiates its interval. Refresh per-session state, not a single user key that one device can erase for every other device.

Explicit disconnect is a useful fast path. Expiry handles missing disconnects; it is not a reason to forbid cleanup. A liveness service or process monitor must actually detect expiry and publish the aggregate transition—deleting a cache key alone does not notify every subscriber reliably.

**Publish only what the client uses.** Scope member-list presence to visible or requested ranges, and suppress unnecessary inactive-guild updates. Presence preferences and authorization still apply. Coalescing the latest value requires versioning or ownership so an older delayed event cannot replace a newer one.

**Cost:** users can appear online briefly after vanishing, and independently refreshed views may temporarily disagree. This is an explicit staleness budget, not "stale presence is invisible." Whether presence exceeds message traffic depends on measured subscriptions and churn.

---

## 10 · Deep dive — hot reads and unread state

### Why a large announcement can hurt the database

Thousands of clients may open a channel and request the same recent messages simultaneously. Even if writes are cheap, concurrent reads against one channel/bucket can overload its replicas and affect unrelated traffic on those nodes.

**Coalesce identical in-flight queries and limit concurrency.** Route requests for a channel to a data-service instance that shares one in-flight result among equivalent waiters. Cache hot immutable pages/results with bounded staleness where appropriate, and cap concurrent database work per hot key. The first request can start immediately; in-flight coalescing does not require waiting for a batching window.

The cache/coalescing key must include the query parameters and relevant visibility boundary. Two requests touching the same partition are not necessarily equivalent. Discord's Rust data-service layer describes this exact sharing of identical requests and channel-based routing. [Discord's data services](https://discord.com/blog/how-discord-stores-trillions-of-messages)

### Read state is a different access pattern

Store a user/channel mark-read position and coalesce updates over a proposed two-second window. Persist the latest pending value on the client and retry until accepted. Across devices, merge monotonically; if the storage engine uses last-write-wins timestamps, do not assume that automatically computes `MAX(message_id)`. Use conditional updates or a serialized user-state writer.

Different users' read cursors are not an identical hot query. Their cardinality is the number of tracked user/channel pairs, which is not necessarily larger than retained messages. An unread badge can compare history head to mark-read position, but a sparse-ID comparison does not prove receipt of every preceding message. Exact unread counts may need maintained aggregates or capped range counts; they are not free.

**Cost:** read-state convergence can lag by a few seconds (target ≤5s normally). Coalescing correlates waiters behind one slow query, so use timeouts and concurrency limits. Client retry preserves the final update even if an intermediate server write-behind buffer is lost.

---

## 11 · Message storage and idempotency — enough for the hour

### Why choose ScyllaDB here, and what that does not prove

Bucketed channel history is a good wide-column access pattern. **ScyllaDB** is a plausible choice for large retained history and high read/write volume, but range scans alone do not rule out sharded Postgres. The Slack design remains a valid alternative when its transactional simplicity and fleet cost win.

Discord reported moving from 177 Cassandra nodes to 72 ScyllaDB nodes. Its account describes hot partitions, compaction backlogs, GC pauses, repair/operational concerns, and upstream data-service improvements. It is not a controlled Postgres comparison, and the migration was not solely about eliminating GC. [Discord's migration account](https://discord.com/blog/how-discord-stores-trillions-of-messages)

Use `PRIMARY KEY ((channel_id, bucket), message_id)` with descending clustering order. Bucket by a stable server-assigned time window. The newest page may span a boundary; quiet channels can require several buckets, so maintain bucket metadata or otherwise avoid scanning long runs of empty windows. Time bucketing limits accumulated partition size, not the write rate of the current hot bucket.

### Do not let every retry mint a new Snowflake

**Proposed interview mechanism:** conditionally create a short-lived `SendAttempt` keyed by `(channel_id, authenticated_sender_id, nonce)`, containing the canonical ID, bucket, payload, and request hash. `IF NOT EXISTS` chooses one result across concurrent attempts. Reuse that result to idempotently upsert history. Return success only once history storage has succeeded.

A crash between attempt creation and history insertion leaves an unacknowledged attempt with enough data for a retry to finish it. It must not be mistaken for an already completed history write. If history succeeded but the HTTP reply was lost, retrying writes the same identity and returns the same result. A conflicting payload is rejected. A conditional-write timeout is an unknown result, not permission to mint another ID.

For this exercise retain attempts for 24h and promise retries for ten minutes; size and clean this metadata separately. This is a proposed implementation, not a claim about Discord's nonce backend. Conditional writes cost more than plain upserts; include them in acceptance benchmarks. A second Redis "seen" flag would introduce another consistency boundary rather than solve it. [ScyllaDB lightweight transactions](https://docs.scylladb.com/manual/stable/features/lwt.html)

**Cost:** conditional acceptance plus a history projection is more machinery than one Postgres transaction. It is a trade for the chosen storage workload, not a free benefit of sparse IDs. Avoid spending the full hour deriving it; name the failure boundary and return to fanout.

---

## 12 · Placement, storage choices, and lifecycle

**Partition history by channel/bucket; distribute live work by guild and session.** These keys serve different purposes. A guild owner can live on another host from the database replicas. A hot bucket may need rate limiting or striped writes plus a merge on read, but choose that from observed limits rather than global averages.

| Component | Access / durability | Proposed choice and alternative |
|---|---|---|
| Message history | Channel range reads; acknowledged data survives one AZ loss | **ScyllaDB**, RF=3 across AZs, quorum operations and verified commit-log durability. "Postgres is viable; benchmark total retained storage and hot reads before giving up its transactions" |
| Send attempts | Conditional sender/nonce acceptance; stable retry result | **ScyllaDB LWT**, compact record with payload until expiry. "Redis cannot atomically stand in for durable acceptance" |
| Guild metadata and roles | Authoritative access decisions; cached in owner/relays | **Postgres** with HA and versioned cache invalidation. "A stale route can drop a push; stale authorization can disclose content" |
| Guilds, relays, session streams | Stateful routing and bounded in-memory queues | **Elixir/BEAM**, controlled ownership and process supervision. "This is live execution state, not a durable broker" |
| Session directory | Route resume to surviving session host/generation | **Redis Cluster**, rebuildable leases. "The directory does not preserve the replay buffer; invalid sessions need fallback" |
| Presence | Per-session liveness aggregated to user state | **BEAM liveness processes**, local timers/monitors and versioned aggregate updates. "An explicit disconnect accelerates the timeout path; neither alone is sufficient" |
| Read state | Per-user/channel monotonic update | **ScyllaDB** with conditional max update and client-side coalescing. "Ordinary last-write-wins does not imply maximum read position" |
| History data service | Identical-query coalescing and per-key concurrency limits | **Rust data services**, following the published pattern. "A shared result helps only equivalent requests; it cannot merge arbitrary queries" |
| Attachments / backups | Durable bytes and recovery copies | **Object storage + CDN**, e.g. S3; access-controlled URLs. "Keep large bytes outside the session event path" |
| Optional durable dispatch | Replayable obligation independent of API lifetime | **Acceptance-coupled record/change stream → retrying relay → guild services.** "Specify the atomic/replay boundary first; Kafka can transport events but cannot repair an unrecorded dual write" |

**Replication is not backup.** Proposed regional disaster policy: off-region incremental backups with ≤1h recovery-point objective and a tested ≤24h restore target for the required serving dataset. Validate these against actual data size; a whole-region loss may exceed normal availability targets. A stricter cross-region RPO requires additional replication and latency/cost analysis.

| State | Lifecycle | Recovery / product consequence |
|---|---|---|
| History | Retain according to guild policy; monitor bucket size and total storage | Keep recent history online. If archive tiering is offered, use channel/time segments and manifests in object storage, with a separate 1–5s old-page target rather than promising all history is instant |
| Deleted content | Propagate deletes through history, caches, indexes, and backup restoration policy | Sparse IDs do not require visible tombstones for each numerical gap; explicit unavailable history still needs a product response |
| Send attempts | 24h proposed retention for a ten-minute retry promise | Expiry ends dedupe protection; includes payload and must follow privacy/deletion rules |
| Replay buffers | ≤60s and bounded bytes/events; released on session expiry | Overflow/host failure means fresh session, not guaranteed replay |
| Presence/session leases | Expire after the liveness window | Directory loss is reconstructible; user presence aggregates surviving sessions |
| Read state | Retain for tracked memberships; delete when no longer needed | New devices fetch unread state but independently load message history |
| Backups | Proposed thirty-day recovery window | Reapply deletions before serving restored data; benchmark restore throughput |
| Optional durable dispatch | Define retention longer than the supported consumer outage | Falling behind retention requires explicit backfill, not silent offset reset |

---

## 13 · Traps — the ranked list

1. **Calling BEAM a durable queue replacement.** Its mailboxes organize live work; database-to-dispatch recovery is separate.
2. **Saying `RESUME` reads an un-dispatched message from history.** Replay only covers events in the surviving session stream.
3. **Promising replay after losing the only copy of the buffer.** Route surviving sessions; otherwise identify afresh and page state/history.
4. **Claiming one guild owner gives database order for free.** Sparse history IDs, guild processing, and session sequences are different orders.
5. **Checking permissions only for the sender.** Recipient visibility and revocation are required even when eligibility is cached.
6. **Sending everything to everyone online.** Connected does not mean interested; passive sessions and visible-member subscriptions can eliminate work.
7. **Assuming 100× batching, harmless hot partitions, or a trivial write fleet.** State the placement/load assumptions and calculate the hottest component.
8. **Treating nonce echo as server deduplication.** Enforce retries and account for its storage/coordination cost.
9. **Using a TTL shorter than the heartbeat interval, or letting one device erase another's presence.** Choose a consistent liveness model.
10. **Protecting live delivery by allowing unbounded queues.** Preserve accepted history; bound memory and recover slow clients.

For general interview mechanics, see [the mechanics page](#/designs/interview-mechanics). Prioritize fanout and reconnect; presence, read-state convergence, and storage alternatives support those dives rather than replacing them.

---

## 14 · The five-minute skeleton

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 570" role="img" aria-label="Discord interview skeleton. Acceptance and direct gRPC lead to guild routing, authorized selective relays, and bounded session delivery. Margin notes cover load, reconnect, presence, hot reads, and the distinction between durable history and best-effort live dispatch.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Draw shared history and live actors; explain the failure boundary between them.</text>
  <rect class="dg-box" x="30" y="90" width="260" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="160" y="116.5">HTTP acceptance</text>
  <text class="dg-s dg-c" x="160" y="132.5">permission + stable nonce</text>
  <text class="dg-s dg-c" x="160" y="148.5">durable canonical history</text>
  <circle class="dg-num" cx="30" cy="90" r="9"></circle>
  <text class="dg-num-t" x="30" y="93.4">2</text>
  <rect class="dg-box" x="370" y="90" width="250" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="116.5">Direct post-store gRPC</text>
  <text class="dg-s dg-c" x="495" y="132.5">bounded deadline / retries</text>
  <text class="dg-s dg-c" x="495" y="148.5">not a durable handoff</text>
  <circle class="dg-num" cx="370" cy="90" r="9"></circle>
  <text class="dg-num-t" x="370" y="93.4">3</text>
  <rect class="dg-box" x="700" y="90" width="270" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="835" y="116.5">Guild owner</text>
  <text class="dg-s dg-c" x="835" y="132.5">shared community state</text>
  <text class="dg-s dg-c" x="835" y="148.5">not database commit order</text>
  <circle class="dg-num" cx="700" cy="90" r="9"></circle>
  <text class="dg-num-t" x="700" y="93.4">4</text>
  <path class="dg-line" d="M 290,128 L 362,128"></path>
  <path class="dg-head" d="M 362,133 L 362,123 L 370,128 Z"></path>
  <path class="dg-line" d="M 620,128 L 692,128"></path>
  <path class="dg-head" d="M 692,133 L 692,123 L 700,128 Z"></path>
  <rect class="dg-box" x="700" y="240" width="270" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="835" y="266.5">Relays</text>
  <text class="dg-s dg-c" x="835" y="282.5">interested + authorized</text>
  <text class="dg-s dg-c" x="835" y="298.5">group recipients by node</text>
  <circle class="dg-num" cx="700" cy="240" r="9"></circle>
  <text class="dg-num-t" x="700" y="243.4">5</text>
  <rect class="dg-box" x="370" y="240" width="250" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="266.5">Session → WebSocket</text>
  <text class="dg-s dg-c" x="495" y="282.5">bounded replay and socket queues</text>
  <text class="dg-s dg-c" x="495" y="298.5">event seq + identity dedupe</text>
  <circle class="dg-num" cx="370" cy="240" r="9"></circle>
  <text class="dg-num-t" x="370" y="243.4">6</text>
  <rect class="dg-box" x="30" y="240" width="260" height="76" rx="8"></rect>
  <text class="dg-t dg-c" x="160" y="266.5">Reconnect</text>
  <text class="dg-s dg-c" x="160" y="282.5">resume surviving stream</text>
  <text class="dg-s dg-c" x="160" y="298.5">otherwise page state / history</text>
  <circle class="dg-num" cx="30" cy="240" r="9"></circle>
  <text class="dg-num-t" x="30" y="243.4">7</text>
  <path class="dg-line" d="M 835,166 L 835,232"></path>
  <path class="dg-head" d="M 830,232 L 840,232 L 835,240 Z"></path>
  <path class="dg-line" d="M 700,278 L 628,278"></path>
  <path class="dg-head" d="M 628,273 L 628,283 L 620,278 Z"></path>
  <path class="dg-line" d="M 370,278 L 298,278"></path>
  <path class="dg-head" d="M 298,273 L 298,283 L 290,278 Z"></path>
  <text class="dg-lane" x="30" y="368">IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="390" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="175" y="410.5">Workload assumptions</text>
  <text class="dg-s dg-c" x="175" y="426.5">15 M sessions / 150 k peak sends</text>
  <text class="dg-s dg-c" x="175" y="442.5">size storage, hot reads, fanout</text>
  <circle class="dg-num" cx="30" cy="390" r="9"></circle>
  <text class="dg-num-t" x="30" y="393.4">1</text>
  <rect class="dg-box" x="355" y="390" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="410.5">Presence</text>
  <text class="dg-s dg-c" x="500" y="426.5">aggregate devices; 20 s / 60 s</text>
  <text class="dg-s dg-c" x="500" y="442.5">coalesce / selective subscriptions</text>
  <circle class="dg-num" cx="355" cy="390" r="9"></circle>
  <text class="dg-num-t" x="355" y="393.4">8</text>
  <rect class="dg-box" x="680" y="390" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="825" y="410.5">Hot reads / read state</text>
  <text class="dg-s dg-c" x="825" y="426.5">coalesce identical history queries</text>
  <text class="dg-s dg-c" x="825" y="442.5">monotonic per-user read position</text>
  <circle class="dg-num" cx="680" cy="390" r="9"></circle>
  <text class="dg-num-t" x="680" y="393.4">9</text>
  <rect class="dg-warn" x="30" y="495" width="940" height="48" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="523.5">Durable history, best-effort live push. Stronger delivery needs a durable dispatch and recovery mechanism.</text>
  <circle class="dg-num" cx="30" cy="495" r="9"></circle>
  <text class="dg-num-t" x="30" y="498.4">10</text>
</svg>
</div>

<p class="diagram-cap">The large-fanout companion to Slack: spend the hour on selective recipients, relay work, bounded queues, and honest reconnect guarantees.</p>

1. **Scope and load:** shared channel history + selective live events; assume 15M sessions and 150k peak sends/sec.
2. **Accept:** HTTP API authenticates, checks send permission, resolves the retry key, and durably stores the canonical message.
3. **Dispatch:** post-store gRPC to the guild service; bounded attempts, separate from acceptance.
4. **Guild owner:** shared community state and routing; mailbox order is not database commit order.
5. **Relays:** interested sessions only, recipient authorization, then group by node for large fanout.
6. **Sessions:** bounded replay buffer and WebSocket queue; per-session event sequence, client message-identity dedupe.
7. **Reconnect:** surviving stream → resume; lost/expired stream → fresh identity and paginated state/history.
8. **Presence:** aggregate devices, explicit disconnect plus expiry, coalesce and restrict subscriptions.
9. **Hot reads:** coalesce identical history queries; read cursor is separate user state with monotonic updates.
10. **Failure contract:** best-effort live push, durable history; add durable dispatch/change cursors if stronger downstream/device completeness is required.

---

## 15 · Variants — what actually changes

**The axis: interested online recipients per event.** Presence, retention, encryption, and reliable downstream processing are separate modifiers.

| Breadth / workload | Variant | Delta |
|---|---|---|
| Few devices | DMs | Direct device-route lookup may beat guild/relay machinery; same retry and history obligations |
| Tens to hundreds | Slack-like channels | Relational acceptance may simplify the design; shared history and reconnect remain. Large Slack channels can still need relays |
| Thousands to millions | Large Discord communities | Selective subscriptions, central guild state plus relays, mailbox budgets, and hot-read protection dominate |
| Very wide, explicitly ephemeral | Live comments | Product may allow dropping/sample delivery and no archive; state that relaxation rather than assume it |
| Many authors per personalized read | News feed | Timeline materialization may win because reads merge sources, not simply because readers were offline |
| Strict downstream processing | Audit / trading events | Add durable replay and precise ordering guarantees; replaceable presence lossiness does not apply to business events |

**WhatsApp contrast:** encryption adds cryptographic device identity, key distribution, and different history/bootstrap policies. Servers still retain ciphertext for delivery; E2EE does not inherently forbid shared group ciphertext or encrypted archives. Do not use encryption to prove that every message requires a separate full content copy per recipient. [WhatsApp multi-device explanation](https://engineering.fb.com/2021/07/14/security/whatsapp-multi-device/)

**The reusable lesson:** a direct API call, actor mailbox, durable dispatch log, session replay buffer, and history store solve different parts of delivery. Pick their guarantees independently, then show how failures cross their boundaries.
