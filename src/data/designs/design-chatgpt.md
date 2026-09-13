# Design ChatGPT — Streaming, Run Lifecycle & GPU Scheduling

## The question

> *"Design ChatGPT. Someone types a prompt, the answer streams back a few words at a time, and their conversations are still there tomorrow. Two hundred million people a day."*

**The product.** A text box and a transcript. You type a question, the answer appears progressively rather than all at once, and you can stop it half-way if it's going somewhere you didn't want. The conversation is saved, so you can come back next week, scroll it, and keep going — the assistant behaves as though it remembers everything the two of you said. A sidebar lists your past conversations, newest first.

The constraint that shapes everything: **the thing producing those words is a fixed pool of rented hardware, it is the most expensive resource we own, and it produces words slowly.** A single answer occupies a slice of that hardware for ten seconds or more. We can't buy our way out of a traffic spike on a Tuesday afternoon, so the interesting question is never "how do we go faster" — it's who gets the hardware, in what order, and how we avoid ever wasting a second of it.

**What a working system delivers**

- Words on screen within half a second of hitting enter. The wait *before* the first word is the entire perceived latency; the ten seconds after it are fine.
- An answer that keeps arriving through a refresh, a tunnel, a closed laptop lid, or a deploy of our own servers — and that is still there, complete, when you come back.
- A stop button that stops the machine, not just the animation.
- Yesterday's conversation, in order, with the assistant picking up mid-thought.

**Why this gets asked.** The product is a chat log, which is the most boring CRUD problem in this set. All of the difficulty sits in one seam: the thing generating the answer is slow, expensive, capacity-bounded, and outlives the HTTP request that started it. Every good answer to this question comes from taking that seam seriously; every weak one comes from treating the generation as a function call that happens to be slow.

---

**Archetype:** LLM application — a slow, expensive, capacity-bounded generator wrapped in an ordinary CRUD product, where every interesting decision lives at the seam between them.
**Cousins that reuse ~70% of this page:** Claude, Gemini, Perplexity, Copilot Chat, any agent chat UI, a support assistant at consumer scale, and the front half of most "add AI to our product" designs.

**What's actually being graded:** whether you notice that **the generation is a resource with a lifecycle, not an HTTP response.** Three specific signals separate people who have shipped one of these from people who have used one: (1) you make the **run a first-class entity** and split submit from stream, which is what makes resume, multi-device, and "the tab closed but the answer finished" possible at all; (2) you know the binding constraint is **GPU-seconds**, not QPS, and you schedule accordingly; (3) you rate-limit on **tokens rather than requests**, because a 30k-token prompt and a one-liner are the same request and a hundredfold different cost.

**Contrast to have ready:** *Every other page in this set spends its budget on getting data to the right place. This one spends it on a single ten-second unit of work that costs real money, can't be redone for free, and whose owner may have walked away. The closest cousin isn't a chat app — it's video transcoding.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "The chat product itself is CRUD — conversations, messages, a sidebar — and I'll build that in about five minutes and not linger. What makes this hard is that the answer is produced by a fixed pool of GPUs, takes ten seconds, and costs real money, which gives me three problems. **First, the generation outlives the request that started it** — so I'm going to make a `Run` a first-class entity, split submit from stream, and make the stream resumable, because a refresh or a deploy must not cost a generation we're already paying for. **Second, capacity is fixed** — call it fifty-odd thousand prompts a second against GPUs I can't buy more of today, so I need a queue and admission control, not autoscaling. **Third, cost is per token and conversations grow forever**, so context management is a real design problem rather than a footnote. I'd like to spend most of my time on the run lifecycle and on scheduling — roughly five minutes each — and I'll tie every choice back to the non-functional requirements as I go."

**Why open this way:** it does three things at once — it *deprioritizes* the CRUD out loud, which buys you the clock; it names the seam that makes the problem interesting; and it pre-commits two dives, so you choose the ground you fight on. Anyone who opens by designing the message table has spent their best minutes on the least interesting part of the system.

---

## 1 · Functional requirements

1. **Send a prompt in a chat and receive the response streamed back** token by token.
2. **Resume a prior conversation**, with its earlier turns carried into the new prompt so the assistant appears to remember.
3. **Stop a generation in progress**, and have that actually free the hardware.

**Out of scope (say them):** images, audio, and video in or out; editing or branching an existing message; sharing a chat; tools, function calling, and browsing; full-text search across history; custom instructions and cross-chat memory.

**Below the line, likely follow-ups:** multi-device — the same chat open on a phone and a laptop (§8 gets it almost for free); regenerate; moderation on the way in and on the way out (§13).

---

## 2 · Non-functional requirements

Every row is a number and the decision it forces. Where a row says "eventually", it says how long.

| Property | Target | Why, and what it forces |
|---|---|---|
| **Time to first token** | **p95 < 500 ms** | The only latency the user actually experiences. Forces the scheduling priority in §9 and the prompt ordering in §11 |
| Inter-token latency | p95 < 80 ms, ≥ 12 tokens/sec sustained | Must outpace reading speed. Below it the stream visibly stutters and feels broken even though total time is unchanged |
| Total completion | 5–30 s, acceptable | **Only because it streams.** Without streaming this product does not exist |
| **A run survives losing the client** | **100% of runs.** Reconnect resumes with **zero tokens lost**, within 2 s | Forces the token log in §8. A dropped connection is not a cancel |
| **A run survives losing our streaming server** | 100%. Streaming tier drains in ≤ 30 s and a deploy costs zero runs | Forces splitting the streaming tier from the API tier as its own deploy unit (§7) |
| A run survives losing its GPU worker | **Best-effort, and say so:** detected by log silence within ~10 s; restart from scratch if < 50 tokens were emitted, otherwise finalize what we have and emit `error` | The one place we accept a partial failure, because restarting a 900-token generation costs more than it saves. Who detects it and who writes the partial is §8 |
| Chat state consistency | **Read-your-writes for the author. ≤ 1 s staleness for everything else** | The sidebar may be a second stale on a second device; the tab you typed in may never be. Forces a stronger read (`LOCAL_QUORUM`) on exactly one query and the cheap read everywhere else |
| Chat title freshness | Generated async, visible **≤ 2 s**, "New chat" until then | An extra model call must never sit in the send path |
| Message durability | The assistant message is durable **≤ 1 s after `done`**, asynchronously. **Individual tokens are not durable** | Deliberate twice over: the token log is a replay buffer with a TTL, and persistence is buffered so a GPU never waits on the store (§8). The gap is covered by the client's own buffer |
| Availability | 99.9% for send and stream; **99.99% for reading history** | Reading yesterday's chat must survive a bad day in the inference tier entirely. Forces the read path to share nothing with the generation path |
| Capacity | Fixed GPU pool. Under overload, **queue the free tier; never kill an in-flight run** | Forces admission control (§9) and tier-weighted scheduling (§10) |
| Cost | Measured in **GPU-seconds per run**, ~$3.5M/day (§3) | Forces token-based quotas (§10) and context pruning (§11) |
| Scale | ~57k generations/sec average; **~570k concurrent open streams** | Forces a separate, stateless streaming tier (§7) |

**The sentence that earns the point:** *"Almost everything here is a latency or a capacity target and degrades gracefully. Exactly one thing doesn't: a generation we are already paying for must never be lost by anything on our side — not a refresh, not a tunnel, not our own deploy. That's the only place I'll spend real correctness machinery, and everything in the run lifecycle follows from it."*

---

## 3 · Numbers that reframe the problem

**Traffic, with the assumption labeled**

- 200M DAU × ~4 conversations × ~6 turns ≈ **5B generations/day ≈ 57k/sec average**, call it 2–3× at peak.
- That 25-prompts-per-user-per-day figure is an *assumption about heavy users*. A lighter one — a few prompts a day — lands nearer 20k/sec. **Say which you're using and then say that nothing on this page changes between them**, because the shape of the design is set by the concurrency and the fixed capacity, not by the exact arrival rate.

**Concurrency — the number the whole design hangs off**

- Little's law: 57k/sec arrivals × ~10 s per generation = **~570k concurrent open streams, sustained.** Write it in the margin. It's what makes the connection tier a first-class component, and it's what you point back at when they say "now make it 10× bigger."

**What that costs in hardware, which is the number most candidates never compute**

- A frontier model's weights don't fit on one GPU, so one model instance spans a server of ~8 GPUs. Under continuous batching (§9) such a server holds on the order of **64 concurrent sequences**.
- 570k ÷ 64 ≈ **9,000 servers ≈ ~72,000 GPUs.** At roughly $2/GPU-hour that's **~$3.5M/day, north of $1B/year.** *(Anchor worth naming: OpenAI's reported 2024 inference compute was around $1.8B.)*
- Per generation that's **~$0.0007 — well under a tenth of a cent.** **Do not price this off published per-token API rates.** Those are a product with margin baked in and overstate your own serving cost by more than an order of magnitude. **The unit here is GPU-seconds, and saying so is itself a signal.**

**The ratio that justifies splitting the tiers**

- 570k connections × ~40 KB of socket and buffer ≈ **~23 GB of memory, so roughly 50 machines** for the streaming tier — against ~9,000 for inference. **Two orders of magnitude apart, so they scale on different curves and fail for different reasons.** That ratio, not neatness, is the argument for making them separate services (§7).

**Context growth, which is where cost hides**

- A 50-turn chat at ~500 tokens a turn is **~25k input tokens on the next prompt**, re-sent every turn. Prefill is compute-bound and roughly linear in input length, **so the same model answers turn 50 with several times the TTFT of turn 1** — the conversation gets slower and more expensive the more the user likes it. That's the §11 dive.

**Storage**

- Every generation is two rows: a ~300-byte prompt and a ~2 KB reply (500 tokens at ~4 bytes each). 5B generations/day ≈ **10B rows and ~11 TB/day, ~4 PB/year**, append-only, never deleted, and growing. §12 has the lifecycle, because "unbounded growth with no plan" is a real finding at this scale.

---

## 4 · Core entities

- **User** — id, **tier** (`free` | `plus` | `pro`). The tier is not a billing detail here; it's an input to the scheduler (§10)
- **Chat** — id, userId, title, createdAt, `lastMessageAt`
- **Message** — id, chatId, **role** (`user` | `assistant`), content, createdAt, tokenCount
- **Run** — id, chatId, messageId, **status** (`queued` | `running` | `done` | `canceled` | `failed`), model, promptVersion, inputTokens, outputTokens, workerId

**Load-bearing details:**

- **`Run` is the entity nobody creates, and creating it is most of the answer.** A `Message` is finished text; a run is *one attempt to produce it*, and that attempt has a life of its own — it can queue, start, stall, be canceled, fail at token 300, and be retried, all before any assistant message exists to write down. Every hard thing on this page (resumable streams, cancellation, quotas, scheduling, cost attribution) is an operation on a run. **If your entity list is User/Chat/Message, you have no noun to hang any of it on**, and you'll end up smuggling run state into the message row as nullable columns.
- **`Run.status` is the thing the client polls when it has no stream**, and it's how "the tab closed but the answer finished" is even expressible.
- **`Chat.lastMessageAt` is denormalized on purpose** — the sidebar is `ORDER BY lastMessageAt DESC` and computing it from messages on every sidebar load is the one query that would actually hurt.
- **`Run.inputTokens` / `outputTokens`** are the quota ledger (§10) and the cost-attribution dataset. Without them you cannot answer "which users cost us money" or enforce anything but a request count.

---

## 5 · API

```
POST /v1/chats                                   → { chatId }

GET  /v1/chats?cursor=&limit=                    → Chat[]      (keyset, newest lastMessageAt first)
GET  /v1/chats/{id}/messages?before=&limit=      → Message[]   (keyset on (chatId, createdAt, id))

POST /v1/chats/{id}/messages                     → { userMessageId, runId }   ← returns immediately
  body:    { text }
  headers: Idempotency-Key: <uuid>

GET  /v1/runs/{runId}/stream                     → SSE
  headers: Last-Event-ID: <seq>                  ← replay from here on reconnect
  ← id: 41   event: token   { delta: "..." }
  ← id: 42   event: usage   { inputTokens, outputTokens }
  ←          event: done    { messageId }
  ←          event: error   { code, retryable }

POST /v1/runs/{runId}/cancel                     → 202
GET  /v1/runs/{runId}                            → Run          (status, for a client with no stream)
```

**Decisions to narrate, unprompted:**

- **Submit and stream are two calls, and this is the decision to dwell on.** One endpoint that both creates the message and streams the answer is simpler and it's what everyone writes first. It also conflates two different lifetimes: the message exists forever, the stream is *one client's view* of one attempt. Splitting them is what makes resume, multi-device, and "the generation outlived the tab" possible without a redesign, and it costs one extra round trip that the optimistic echo hides completely. **→ ties to the "a run survives losing the client" NFR.**
- **SSE, and here's the case against it before you ask.** The full debate is §7. The short version: the token stream is one-way, so SSE's simplicity wins — but a WebSocket would let one connection multiplex several runs and carry cancel on the same socket instead of a separate POST. I'd take SSE and revisit the moment the product needs genuinely bidirectional realtime.
- **`Last-Event-ID` is in the contract from the start**, not bolted on. It's a standard SSE header the browser resends automatically on reconnect, and designing the event ids to be meaningful offsets (§8) is what makes reconnect a replay rather than a restart.
- **`Idempotency-Key` on send.** A retried submit that starts a second generation isn't a duplicate row, it's a double charge against a scarce resource and a second answer streaming into the same bubble. **→ ties to the cost NFR.**
- **Keyset pagination, never offset.** A chat list and a message list both grow while you're paging them, so offsets skip and repeat rows; and `OFFSET 10000` makes the database count ten thousand rows it will throw away. Keyset on `(chatId, createdAt, id)` is O(log n) at any depth.
- **Cancel is its own POST**, because SSE is one-way. Naming that as the direct cost of choosing SSE is better than presenting the endpoint as if it were free.
- **`userId` appears in no path and no body.** It comes from the session, and chat ownership is checked server-side on every call. Anything the client sends can be forged.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 590" role="img" aria-label="ChatGPT architecture. A request row: clients, a stateless API tier of gateway and chat service, a scheduler, and a fixed GPU pool. Each GPU makes two independent writes: token-by-token into Redis Streams for the live view, and one finished message into Kafka for durability. Redis Streams feeds a streaming tier of stateless SSE instances; Kafka feeds a persister that batch-writes to ScyllaDB. Redis also holds quota counters and the priority queues; S3 holds cold chats.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Three tiers, ~50 machines against ~9,000. Every GPU makes two writes: one lossy for the live view, one durable for the record.</text>
  <rect class="dg-box" x="20" y="118" width="140" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="90" y="154.5">Clients</text>
  <rect class="dg-group" x="190" y="86" width="360" height="130" rx="12"></rect>
  <text class="dg-group-t" x="206" y="108">API — STATELESS CRUD</text>
  <rect class="dg-box" x="206" y="118" width="150" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="281" y="146.5">API Gateway</text>
  <text class="dg-s dg-c" x="281" y="162.5">HTTPS · auth · routing</text>
  <rect class="dg-box" x="376" y="118" width="158" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="455" y="138.5">Chat Service</text>
  <text class="dg-s dg-c" x="455" y="154.5">POST /chats/{id}/messages</text>
  <text class="dg-s dg-c" x="455" y="170.5">quota check, then enqueue</text>
  <path class="dg-line" d="M 356,150 L 368,150"></path>
  <path class="dg-head" d="M 368,155 L 368,145 L 376,150 Z"></path>
  <rect class="dg-group" x="580" y="86" width="180" height="130" rx="12"></rect>
  <text class="dg-group-t" x="596" y="108">SCHEDULER</text>
  <rect class="dg-box" x="596" y="118" width="148" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="670" y="138.5">Scheduler</text>
  <text class="dg-s dg-c" x="670" y="154.5">sorted sets by tier</text>
  <text class="dg-s dg-c" x="670" y="170.5">workers pull</text>
  <rect class="dg-group" x="790" y="86" width="190" height="130" rx="12"></rect>
  <text class="dg-group-t" x="806" y="108">INFERENCE</text>
  <rect class="dg-box" x="806" y="118" width="158" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="885" y="138.5">GPU workers</text>
  <text class="dg-s dg-c" x="885" y="154.5">continuous batching</text>
  <text class="dg-s dg-c" x="885" y="170.5">XADD tokens, then produce</text>
  <path class="dg-line" d="M 160,136 L 198,136"></path>
  <path class="dg-head" d="M 198,141 L 198,131 L 206,136 Z"></path>
  <text class="dg-lbl dg-c" x="183" y="128">POST</text>
  <path class="dg-line" d="M 550,150 L 588,150"></path>
  <path class="dg-head" d="M 588,155 L 588,145 L 596,150 Z"></path>
  <path class="dg-line" d="M 760,150 L 798,150"></path>
  <path class="dg-head" d="M 798,155 L 798,145 L 806,150 Z"></path>
  <path class="dg-line" d="M 885,216 L 885,244"></path>
  <path class="dg-line" d="M 330,244 L 885,244"></path>
  <path class="dg-line" d="M 330,244 L 330,282"></path>
  <path class="dg-head" d="M 325,282 L 335,282 L 330,290 Z"></path>
  <path class="dg-line" d="M 855,244 L 855,282"></path>
  <path class="dg-head" d="M 850,282 L 860,282 L 855,290 Z"></path>
  <text class="dg-lbl dg-c" x="700" y="282">two independent writes</text>
  <text class="dg-lbl" x="340" y="272">XADD per token</text>
  <text class="dg-lbl" x="866" y="272">one message</text>
  <text class="dg-lbl" x="340" y="384">XREAD from last id</text>
  <text class="dg-lbl" x="866" y="384">consume</text>
  <path class="dg-box" d="M 190,297 L 190,347 A 140,7 0 0 0 470,347 L 470,297 A 140,7 0 0 0 190,297 Z"></path>
  <path class="dg-box" d="M 190,297 A 140,7 0 0 0 470,297" style="fill:none"></path>
  <text class="dg-t dg-c" x="330" y="314">Redis Streams — token log</text>
  <text class="dg-s dg-c" x="330" y="330">run:{runId}, one entry per token</text>
  <text class="dg-s dg-c" x="330" y="346">lossy, 10-minute TTL</text>
  <rect class="dg-box" x="730" y="290" width="250" height="64" rx="8"></rect>
  <path class="dg-qbar" d="M 743,299 L 743,345"></path>
  <path class="dg-qbar" d="M 752,299 L 752,345"></path>
  <path class="dg-qbar" d="M 761,299 L 761,345"></path>
  <text class="dg-t dg-c" x="873" y="318.5">Kafka</text>
  <text class="dg-s dg-c" x="873" y="334.5">key = chatId · one message</text>
  <rect class="dg-box" x="190" y="400" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="330" y="420.5">Streaming instances</text>
  <text class="dg-s dg-c" x="330" y="436.5">GET /runs/{id}/stream — SSE</text>
  <text class="dg-s dg-c" x="330" y="452.5">holds the socket, owns no run state</text>
  <rect class="dg-box" x="730" y="400" width="250" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="855" y="428.5">Persister</text>
  <text class="dg-s dg-c" x="855" y="444.5">consumes Kafka, batch-writes</text>
  <path class="dg-line" d="M 330,354 L 330,392"></path>
  <path class="dg-head" d="M 325,392 L 335,392 L 330,400 Z"></path>
  <path class="dg-line" d="M 855,354 L 855,392"></path>
  <path class="dg-head" d="M 850,392 L 860,392 L 855,400 Z"></path>
  <path class="dg-box" d="M 190,517 L 190,567 A 140,7 0 0 0 470,567 L 470,517 A 140,7 0 0 0 190,517 Z"></path>
  <path class="dg-box" d="M 190,517 A 140,7 0 0 0 470,517" style="fill:none"></path>
  <text class="dg-t dg-c" x="330" y="534">Redis — scheduler + quota</text>
  <text class="dg-s dg-c" x="330" y="550">sorted set per tier, score = enqueue + aging</text>
  <text class="dg-s dg-c" x="330" y="566">quota counters, sliding window, fails open</text>
  <path class="dg-box" d="M 520,517 L 520,567 A 90,7 0 0 0 700,567 L 700,517 A 90,7 0 0 0 520,517 Z"></path>
  <path class="dg-box" d="M 520,517 A 90,7 0 0 0 700,517" style="fill:none"></path>
  <text class="dg-t dg-c" x="610" y="542">S3</text>
  <text class="dg-s dg-c" x="610" y="558">cold chats</text>
  <path class="dg-box" d="M 730,517 L 730,567 A 125,7 0 0 0 980,567 L 980,517 A 125,7 0 0 0 730,517 Z"></path>
  <path class="dg-box" d="M 730,517 A 125,7 0 0 0 980,517" style="fill:none"></path>
  <text class="dg-t dg-c" x="855" y="542">ScyllaDB</text>
  <text class="dg-s dg-c" x="855" y="558">chats · messages · runs</text>
  <path class="dg-line" d="M 855,464 L 855,502"></path>
  <path class="dg-head" d="M 850,502 L 860,502 L 855,510 Z"></path>
  <path class="dg-line" d="M 670,182 L 670,206 L 490,206 L 490,478 L 330,478 L 330,502"></path>
  <path class="dg-head" d="M 325,502 L 335,502 L 330,510 Z"></path>
  <text class="dg-lbl" x="500" y="455">pull</text>
  <path class="dg-line" d="M 455,182 L 455,232 L 178,232 L 178,542 L 182,542"></path>
  <path class="dg-head" d="M 182,547 L 182,537 L 190,542 Z"></path>
  <path class="dg-line" d="M 534,150 L 560,150 L 560,486 L 790,486 L 790,502"></path>
  <path class="dg-head" d="M 785,502 L 795,502 L 790,510 Z"></path>
  <text class="dg-lbl" x="566" y="478">read history</text>
  <path class="dg-line" d="M 190,432 L 170,432 L 170,164 L 168,164"></path>
  <path class="dg-head" d="M 168,159 L 168,169 L 160,164 Z"></path>
  <text class="dg-lbl dg-c" x="183" y="180">SSE</text>
</svg>
</div>

<p class="diagram-cap">The fork under the GPU is the whole board. Redis carries tokens for the live view and is allowed to lose them; Kafka carries one finished message and is not. Lose Redis and the animation breaks while the answer is still stored; lose Kafka and the user watches a perfect answer you then fail to keep.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 750" role="img" aria-label="ChatGPT run lifecycle. A run in flight: the GPU worker appends tokens to a Redis Stream keyed by run id, any streaming instance tails it and forwards over SSE with the entry id as the event id. Five branches. The client closes the tab: nothing happens, the run keeps generating. The client reconnects with Last-Event-ID: any instance replays from that offset. A streaming instance redeploys: it drains, clients reconnect elsewhere, no run is touched. The stop button: an explicit cancel POST removes a queued run from the tier queue for free, or sets a cancel key that the worker checks between decode steps. The worker dies: a reaper notices the log has gone silent and either requeues the run if under fifty tokens or finalizes the partial answer to Kafka and emits a retryable error.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Five things happen to a run in flight, and one mechanism covers them all: the run lives in the log, not on the socket.</text>
  <text class="dg-lane" x="30" y="76">A RUN IN FLIGHT</text>
  <rect class="dg-box" x="30" y="90" width="170" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="115" y="114.5">GPU worker</text>
  <text class="dg-s dg-c" x="115" y="130.5">XADD per token</text>
  <rect class="dg-box" x="240" y="90" width="230" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="355" y="114.5">Redis Stream run:{runId}</text>
  <text class="dg-s dg-c" x="355" y="130.5">monotonic entry ids</text>
  <rect class="dg-box" x="510" y="90" width="220" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="114.5">Any streaming instance</text>
  <text class="dg-s dg-c" x="620" y="130.5">blocking XREAD from last id</text>
  <rect class="dg-box" x="770" y="90" width="190" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="865" y="114.5">Client — SSE</text>
  <text class="dg-s dg-c" x="865" y="130.5">event id = entry id</text>
  <path class="dg-line" d="M 200,118 L 232,118"></path>
  <path class="dg-head" d="M 232,123 L 232,113 L 240,118 Z"></path>
  <path class="dg-line" d="M 470,118 L 502,118"></path>
  <path class="dg-head" d="M 502,123 L 502,113 L 510,118 Z"></path>
  <path class="dg-line" d="M 730,118 L 762,118"></path>
  <path class="dg-head" d="M 762,123 L 762,113 L 770,118 Z"></path>
  <path class="dg-div" d="M 20,170 L 980,170"></path>
  <text class="dg-lane" x="30" y="196">CLIENT CLOSES THE TAB</text>
  <rect class="dg-box" x="30" y="206" width="200" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="235.5">Socket drops</text>
  <path class="dg-line" d="M 230,231 L 262,231"></path>
  <path class="dg-head" d="M 262,236 L 262,226 L 270,231 Z"></path>
  <rect class="dg-good" x="270" y="206" width="200" height="50" rx="8"></rect>
  <text class="dg-good-t dg-c" x="370" y="235.5">Nothing happens</text>
  <path class="dg-line" d="M 470,231 L 502,231"></path>
  <path class="dg-head" d="M 502,236 L 502,226 L 510,231 Z"></path>
  <rect class="dg-box" x="510" y="206" width="450" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="227.5">A closed socket is not a cancel</text>
  <text class="dg-s dg-c" x="735" y="243.5">run keeps generating; the message still lands</text>
  <text class="dg-lane" x="30" y="282">CLIENT RECONNECTS</text>
  <rect class="dg-box" x="30" y="292" width="200" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="313.5">Browser resends</text>
  <text class="dg-s dg-c" x="130" y="329.5">Last-Event-ID: 41</text>
  <path class="dg-line" d="M 230,317 L 262,317"></path>
  <path class="dg-head" d="M 262,322 L 262,312 L 270,317 Z"></path>
  <rect class="dg-box" x="270" y="292" width="200" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="370" y="313.5">Any instance</text>
  <text class="dg-s dg-c" x="370" y="329.5">none is special</text>
  <path class="dg-line" d="M 470,317 L 502,317"></path>
  <path class="dg-head" d="M 502,322 L 502,312 L 510,317 Z"></path>
  <rect class="dg-box" x="510" y="292" width="450" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="313.5">XREAD from 41 — replay the gap, then live</text>
  <text class="dg-s dg-c" x="735" y="329.5">resuming a chat later is this path with an empty cursor</text>
  <text class="dg-lane" x="30" y="368">A STREAMING INSTANCE REDEPLOYS</text>
  <rect class="dg-box" x="30" y="378" width="200" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="407.5">Instance drains</text>
  <path class="dg-line" d="M 230,403 L 262,403"></path>
  <path class="dg-head" d="M 262,408 L 262,398 L 270,403 Z"></path>
  <rect class="dg-box" x="270" y="378" width="200" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="370" y="407.5">Sockets close</text>
  <path class="dg-line" d="M 470,403 L 502,403"></path>
  <path class="dg-head" d="M 502,408 L 502,398 L 510,403 Z"></path>
  <rect class="dg-box" x="510" y="378" width="450" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="399.5">Clients reconnect elsewhere — no run is touched</text>
  <text class="dg-s dg-c" x="735" y="415.5">no run state ever lived on the instance</text>
  <text class="dg-lane" x="30" y="454">THE STOP BUTTON</text>
  <rect class="dg-box" x="30" y="464" width="200" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="485.5">POST /runs/{id}/cancel</text>
  <text class="dg-s dg-c" x="130" y="501.5">explicit — the only stop</text>
  <path class="dg-line" d="M 230,489 L 292,489"></path>
  <path class="dg-head" d="M 292,494 L 292,484 L 300,489 Z"></path>
  <rect class="dg-box" x="300" y="464" width="260" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="430" y="485.5">running: SET cancel:{runId}</text>
  <text class="dg-s dg-c" x="430" y="501.5">short TTL — no pub/sub per run</text>
  <path class="dg-line" d="M 560,489 L 592,489"></path>
  <path class="dg-head" d="M 592,494 L 592,484 L 600,489 Z"></path>
  <rect class="dg-box" x="600" y="464" width="360" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="780" y="485.5">Worker checks it between decode steps</text>
  <text class="dg-s dg-c" x="780" y="501.5">drops the sequence, frees the batch slot now</text>
  <path class="dg-line" d="M 250,489 L 250,549 L 292,549"></path>
  <path class="dg-head" d="M 292,554 L 292,544 L 300,549 Z"></path>
  <rect class="dg-good" x="300" y="524" width="260" height="50" rx="8"></rect>
  <text class="dg-good-t dg-c" x="430" y="545.5">queued: ZREM from the tier queue</text>
  <text class="dg-s dg-c" x="430" y="561.5">costs 0 GPU-seconds</text>
  <text class="dg-lane" x="30" y="604">THE WORKER DIES MID-GENERATION</text>
  <rect class="dg-box" x="30" y="614" width="200" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="635.5">Log silent &gt; 10 s</text>
  <text class="dg-s dg-c" x="130" y="651.5">inter-token p95 is 80 ms</text>
  <path class="dg-line" d="M 230,639 L 262,639"></path>
  <path class="dg-head" d="M 262,644 L 262,634 L 270,639 Z"></path>
  <rect class="dg-box" x="270" y="614" width="160" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="350" y="635.5">Reaper</text>
  <text class="dg-s dg-c" x="350" y="651.5">scans running runs</text>
  <path class="dg-line" d="M 430,639 L 462,639"></path>
  <path class="dg-head" d="M 462,644 L 462,634 L 470,639 Z"></path>
  <rect class="dg-box" x="470" y="614" width="490" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="715" y="635.5">&lt; 50 tokens emitted: delete the stream, requeue</text>
  <text class="dg-s dg-c" x="715" y="651.5">the client sees a stall, then the answer restarts</text>
  <path class="dg-line" d="M 450,639 L 450,699 L 462,699"></path>
  <path class="dg-head" d="M 462,704 L 462,694 L 470,699 Z"></path>
  <rect class="dg-warn" x="470" y="674" width="490" height="50" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="715" y="695.5">≥ 50: read the partial from the log → Kafka, then error{retryable}</text>
  <text class="dg-s dg-c" x="715" y="711.5">best-effort — the partial lives only in Redis</text>
</svg>
</div>

<p class="diagram-cap">Draw the top row, then say the five branches out loud without drawing them. Four are free because the run lives in the log. The fifth is the one place a partial answer can be lost, and saying so is better than hiding it.</p>

Three tiers, and the split is the design:

- **Chat Service** — stateless CRUD plus enqueue. Cheap, scales on request rate.
- **Streaming Tier** — holds ~570k SSE connections, owns no run state, tails the token log. Scales on *connection count* and deploys on its own schedule (§7).
- **Inference Workers** — the GPU pool. Fixed size, and **workers pull** from the tier queues when a batch slot frees; nothing tracks slot state across 9,000 servers (§9).

**The two write paths out of the worker are independent.** Redis carries tokens for the *live view* and is deliberately lossy; Kafka carries one finished message for *durability* and must not drop it. **The streaming tier reads Redis and only Redis** — Kafka never feeds a stream. Different failure, different blast radius, which is why they aren't the same system (§8).

### Flow A — a turn

1. Client **optimistically renders** the user's bubble and an empty assistant bubble in `pending`. Nothing has been confirmed yet; this is what hides the extra round trip from §5.
2. `POST /chats/{id}/messages` with an `Idempotency-Key`. Chat Service dedupes on it, then **checks the token quota before it writes anything** (§10). A rejection here costs zero GPU-seconds and zero rows, which is the entire point of checking at the door.
3. It writes the user message, bumps `lastMessageAt`, creates a `Run` in `queued`, and returns `{ userMessageId, runId }`.
4. Client opens `GET /runs/{runId}/stream`. The load balancer routes it to *any* streaming instance; none of them is special.
5. An **inference worker** — a GPU node — with a free batch slot **pulls** the next run from the tier queues by weight (§9) and flips the status to `running`. **"Worker" on this page always means a GPU node; the streaming tier has no workers, only connection holders.**
6. The inference worker builds the prompt — stable prefix first (§11) — and generates. Each token is `XADD`ed to `run:{runId}` in Redis Streams.
7. The streaming instance holding this client `XREAD`s from the last id it sent and forwards each entry as an SSE event. The browser appends.
8. On completion the inference worker does **two cheap writes and no database call**: it appends a terminal `done` entry to the token log carrying the `messageId`, and it produces the finished message to **Kafka**, partitioned by `chatId`. It then frees its batch slot immediately. A separate **persister** consumer batch-writes those messages into ScyllaDB. The streaming instance forwards the terminal entry, closes the SSE stream, and the client swaps its live buffer for the canonical message. §8 says why the GPU is on the hook for neither write.
9. **Failure path — client disconnects.** Nothing happens to the run. It keeps generating, tokens keep landing in the log, the message gets persisted. **A closed socket is not a cancel** (§8).
10. **Failure path — client reconnects.** The browser resends `Last-Event-ID`; whichever instance it lands on replays from that offset and continues live. The user sees a brief pause, not a truncated answer.
11. **Failure path — a streaming instance is redeployed.** It drains, its clients reconnect elsewhere, and no run is affected — because no run state ever lived there (§7).
12. **Failure path — an inference worker dies mid-generation.** The stream goes silent; a reaper notices within ~10 s (§8). Under 50 tokens emitted, requeue the run from scratch. Past that, the reaper finalizes the partial message and emits `error` with `retryable: true` so the UI can offer regenerate. **Say which side of that line you're on and why** — it's an explicit cost trade, not an oversight.
13. **Failure path — the queue is over capacity.** Free tier gets `429` with a `Retry-After` and a visible "at capacity" state; paid tiers keep going. **We shed at the door and never kill work in flight** (§9).

### Flow B — resuming a conversation

1. `GET /chats` for the sidebar, keyset by `lastMessageAt`, read at **`LOCAL_ONE`**. One second of staleness is invisible here.
2. `GET /chats/{id}/messages?before=` newest-first, rendered reversed. **The author's own chat reads at `LOCAL_QUORUM`**, so you never watch your own message vanish on refresh — that's the read-your-writes half of the consistency NFR, and it applies to exactly one query. Everything else takes `LOCAL_ONE` and the ≤1 s staleness.
3. If the newest run is still `running`, open its stream **with no `Last-Event-ID`** and take the replay from offset 0. **That's the identical code path as reconnect** — resume isn't a feature, it's reconnect with an empty cursor, which is the payoff for having built §8 properly.
4. The next prompt carries context assembled per §11 — not the raw transcript.
5. **Failure path — the chat is older than the hot window.** It lives in cold storage; hydrate it (~1 s, with a skeleton) and serve (§12).

---

## 7 · Deep dive — the transport, and why streaming is its own service

### What you'd reach for first

One request: `POST /messages` that holds the connection open and streams the answer back as it's generated. It works on your laptop, it's the smallest amount of code, and it's what every prototype does.

### What breaks, specifically

The run and the connection now share a lifetime, and three ordinary events kill a generation you're paying for:

- **The user refreshes.** The connection dies, and with it the only channel the answer was traveling down. The tokens already generated are gone; the ones still coming have nowhere to go.
- **You deploy.** The instance holding that connection is also the instance holding the upstream call to the worker. A rolling deploy — several a day — kills every generation in flight on each instance it cycles. **At 570k concurrent streams, a deploy is a mass-extinction event.**
- **A second device opens the same chat.** It cannot see the run at all, because the run exists only as a connection to another machine.

The root cause is one sentence worth saying out loud: **the connection is a view of the run, and we built it as the run itself.**

### The transport debate, which you should have rather than assert

| | Long-polling | **SSE** | WebSocket |
|---|---|---|---|
| Direction | Half-duplex, one request per chunk | **Server → client, one long-lived HTTP response** | Full duplex |
| Reconnect | Manual, and you must track your own cursor | **Built in, with `Last-Event-ID` resent automatically** | Manual: you write the resume protocol yourself |
| Proxies / CDNs | Fine | **Fine — it's ordinary HTTP** | Needs `Upgrade` support end to end; more infra that can get it wrong |
| Multiplexing | No | One connection per run | **Many runs on one socket** |
| Cost of cancel | Separate request | **Separate request** | Same socket |
| Per-connection overhead | Reconnect churn at every chunk | Low | Low, plus ping/pong keepalive you own |

**The decision, and the reasoning I'd say out loud:** *"Tokens only ever flow one way, and the one thing I care most about — reconnect without losing tokens — is the thing SSE gives me for free in the browser and WebSocket makes me build. So SSE, and I'll pay for cancel with a separate POST. I'd flip to WebSocket the moment the product needs genuinely bidirectional realtime — voice, or a canvas the model and the user edit together — because then I'm writing a resume protocol either way and multiplexing starts to pay."* **→ ties to the "run survives losing the client" and TTFT NFRs.**

Long-polling stays on the table as the **degraded fallback** for a client behind a proxy that buffers responses, which does still happen. Naming a fallback is cheap and it's the kind of thing that separates a designed answer from a chosen one.

### The part people miss: the streaming tier is a separate deploy unit

Even with SSE and a token log, **holding 570k long-lived connections in the same process that serves your CRUD API is an operational trap.** Those two workloads have nothing in common:

| | API tier | Streaming tier |
|---|---|---|
| Scales on | Requests/sec | **Concurrent connections** |
| Deploys | Whenever, several times a day | **Rarely, and drains slowly** |
| Holds | Nothing | 570k sockets, ~23 GB of buffers |
| Sized at | Normal web fleet | **~50 machines** |

Bolt them together and every routine API deploy severs hundreds of thousands of live connections. Split them and the streaming tier becomes **stateless with respect to runs** — it holds sockets, but every byte it sends comes from the token log, so any instance can serve any run and a drain is just "reconnect somewhere else." **This is the single most practical thing on the page**, and it generalizes: *any* tier holding stateful client connections wants to be its own deploy unit, whether the payload is tokens, presence, or collaborative edits.

**What it costs:** an extra network hop and an extra service to operate, and the token log becomes a hard dependency on the read path — if Redis is down, live streams stop even though generation continues. The mitigation is that `GET /runs/{id}` and the persisted message still work, so the product degrades to "your answer will appear when it's done" rather than failing.

---

## 8 · Deep dive — the run outlives the connection

### What you'd reach for first

Have the inference worker push tokens directly to whichever streaming server holds the user's connection — look it up in a registry, forward over gRPC.

### What breaks

You've just made the streaming tier stateful again by another route: now the worker must *know* which instance holds this user, that mapping changes on every reconnect and every deploy, and a client that reconnects to a different instance mid-generation has no way to get the tokens it missed while it was gone. **You've rebuilt the coupling you split in §7, only now it's a distributed registry problem instead of a process-local one.**

### What replaces it: a log per run

The inference worker writes tokens **into a log keyed by run id** and never learns who's reading. The streaming tier reads that log and never learns who's generating. Neither side knows the other exists.

**Redis Streams,** one key per run, `run:{runId}`:

- The inference worker `XADD`s each token. Redis assigns a monotonic entry id.
- A streaming instance does a **blocking `XREAD`** from a given id — `0` for a fresh open, the client's `Last-Event-ID` on reconnect — and forwards entries as SSE events, **using the Redis entry id as the SSE event id.** That's the whole trick: the browser's automatic `Last-Event-ID` header and Redis's entry ids are the same cursor, so reconnect is a replay from an offset rather than a protocol you designed.
- `EXPIRE` the key ~10 minutes after `done`. It's a replay buffer, not storage.

**Why Redis Streams rather than the alternatives — the debate:**

| Option | Why not |
|---|---|
| **Kafka** | Right shape, wrong granularity. 570k concurrent runs means 570k short-lived topics-worth of state; Kafka's partitions are long-lived and coarse, and per-run offset tracking would be ours to build. Kafka is for durable pipelines, not for 570k ten-second buffers |
| **Redis Pub/Sub** | Fire-and-forget. A subscriber that reconnects one second late gets nothing, which fails the exact requirement the log exists for |
| **A row per token in the message store** | 57k/sec × ~200 tokens = **~11M writes/sec** of data we've already said is *not* durable. Pure waste, and it would dwarf the real workload by two orders of magnitude |
| **Redis Streams** | **Chosen.** Ordered, replayable from an offset, TTL-able, and cheap. The property that decides it is replay-from-offset — that's what makes reconnect free |

**What it costs, volunteered:** memory (570k runs × a few KB of buffered tokens is single-digit GB — comfortable, but it must be bounded and TTL'd or a Redis OOM takes out every live stream at once); one more system on the critical path; and **at-least-once delivery, so a client can see a token twice across a reconnect** — the client dedupes on event id, which is one line and worth saying you thought about.

### Why the log carries a terminal entry, when the message is already persisted

**Because the streaming tier cannot see that write.** It is sitting in a blocking `XREAD` on `run:{runId}` and knows nothing about the run except what arrives on the log; to a reader, "no more data" and "not yet" are the same observation. Without an in-band end marker it either hangs until a timeout on every successful answer, or polls run status — 570k polls in flight against the store, forever. One extra entry replaces both, and it carries the `messageId` the client needs to swap its live buffer for the canonical row. It's also what lets the client tell a finished stream from a severed one: an unterminated stream should be retried, a terminated one must not be.

### What happens when Redis dies, and why the answer survives it

Worth being precise, because "we lose the generation" is the intuitive answer and it's wrong.

**The token log is explicitly lossy — that was the deal in §2.** If Redis goes down, every in-flight live stream breaks and the buffered tokens are gone. What *doesn't* happen is losing the answer: the inference worker is still holding the sequence on the GPU, still generating, and its path to durability doesn't touch Redis at all. It finishes, produces the message, and the message gets stored. **The user loses the live view and gets the completed answer on reconnect or refresh** — the product degrades from "watch it type" to "it'll be there in a moment."

Two things make that true rather than aspirational, and both are worth saying:

- **The worker must never block on `XADD`.** Write with a short timeout and drop the token on failure. A GPU node stalling on a Redis write is the most expensive possible way to handle an outage in a cache.
- **Durability must not route through Redis.** Which is the next section, and the reason the completion path looks the way it does.

### Why the worker hands off to Kafka instead of writing the message itself

The obvious version is that the inference worker writes the finished assistant message straight to ScyllaDB and then frees its batch slot. One hop, no extra system, and it's what the naive flow does.

**What breaks: you have put the most expensive machine in the fleet on the far side of a database write.** A worker blocked on a Scylla `INSERT` is a GPU holding a batch slot to do I/O, and the failure mode compounds — the moment the store has a p99 spike, workers stall, slots don't free, the queue backs up, and **a storage hiccup turns into a capacity outage.** The most expensive resource in the system is now coupled to the availability of the cheapest.

**What replaces it: the worker's completion path does two fast, local writes and nothing else.**

| Write | Destination | Purpose | If it fails |
|---|---|---|---|
| Terminal `done` entry | Redis Stream | The user sees the answer **now** | Stream ends by timeout; the message still lands |
| The finished message | **Kafka**, `key = chatId` | The answer is **stored**, exactly once, in order | Retry in the worker; this one must not be dropped |

A **persister** consumer reads that topic and batch-writes into ScyllaDB. That buys four things:

- **The GPU is released the moment generation ends.** This is the whole point, and it's denominated in the currency of §9.
- **Storage outages stop being generation outages.** Scylla down for ten minutes means the topic grows by ten minutes and drains after. Nothing is lost and nothing stops generating. Without the buffer, that same ten minutes either loses messages or wedges the pool.
- **Batched writes instead of 114k individual inserts.** Cheaper on the store by a wide margin, and the batching is free because a consumer is already reading in batches.
- **Retries live somewhere durable** rather than in the memory of a process we want to be stateless.

**Why Kafka here when this section rejected it for tokens:** the rejection was about *granularity*. 570k short-lived per-run streams is the wrong shape for long-lived coarse partitions; one message per completed run on a handful of partitions keyed by `chatId` is exactly the right one. **Same system, opposite verdict, and the discriminator is granularity rather than throughput.** A second consumer on the same topic generates chat titles with a small model, which is how the ≤ 2 s title NFR is met without an extra call in the send path.

**What it costs, and this is the real trade:** the message is now durable *asynchronously*, so there is a **sub-second window where the run is `done` and the message is not yet queryable.** A client that refetched instantly could miss it. Three things close that, and you should name them rather than hope:

1. **The client already has the text** — it assembled it from tokens — so it renders from its own buffer and reconciles on the next load, by which point the persister is caught up.
2. **The `Run` row is written directly, not through Kafka.** It's tiny and low-volume next to messages, and it makes `GET /runs/{id}` authoritative for "finished, storage catching up."
3. **Keying the topic by `chatId` preserves per-chat ordering**, so turns can never be persisted out of sequence — which is the failure that would actually be visible to a user.

**→ ties to the capacity NFR** (a GPU must never wait on storage) **and to the message-durability NFR**, which is why that row says ~1 s and not ~200 ms.

### Cancel is a signal; a closed socket is not

**Closing the tab is not a stop.** We built this whole mechanism precisely so that a dropped connection doesn't end a run — the user is meant to be able to reopen the chat and find the answer waiting. So cancellation has to be **explicit**: `POST /runs/{id}/cancel` flips the run's status, and then does one of two things depending on where the run is. **Still queued:** `ZREM` it from the tier queue — it costs nothing and never touches a GPU. **Running:** set a `cancel:{runId}` key in Redis with a short TTL. The inference worker checks that key between decode steps for each sequence it holds — a cheap read of a key it already knows, no pub/sub subscription per run — and drops the sequence. **Already done:** a no-op that returns the terminal status; the client raced the finish and nothing needs undoing.

**And it must reach the GPU.** A stop button that only stops rendering leaves a batch slot occupied for the rest of a 30-second generation. At this scale that's the difference between reclaiming capacity and paying for tokens nobody will ever read — **cancellation is a capacity feature wearing a UI costume.** **→ ties to the cost and capacity NFRs.**

### A dead worker, and who notices

A worker that dies takes its batch with it, and nothing above it finds out: the `Run` row still says `running`, and the client's stream simply goes quiet — which is indistinguishable from a slow token. **The signal is silence on the log.** A **reaper** scans `running` runs and checks the age of the last entry on `run:{runId}`; with inter-token p95 at 80 ms, ten seconds of nothing is unambiguous. *(A worker heartbeat works too; the log is preferable because it's a signal we already have.)* Then it applies the §2 policy:

- **Under 50 tokens emitted:** delete the stream key, put the run back on its tier queue. The client sees a stall and then the answer restarts from the top — which is why the line is 50 tokens and not 500. The re-run is safe because the `Idempotency-Key` was consumed at submit, not at generation.
- **Past 50:** read the partial from the log, produce it to Kafka flagged `partial`, append `error { retryable: true }` to the stream so the client closes cleanly and offers regenerate.

**Say the honest part:** the partial lives only in Redis, the store we agreed is lossy. If the worker and Redis die together, the partial is gone, and that is the accepted loss — the answer was already going to be incomplete. What the reaper buys is that no run stays `running` forever and no batch slot is ever *thought* to be occupied when it isn't.

---

## 9 · Deep dive — scheduling a GPU pool you cannot autoscale

### What you'd reach for first

Chat Service calls a worker directly, round-robin across the pool. Add workers when it gets busy.

### What breaks

**You cannot add workers.** Not in the ten seconds a spike lasts, and often not this quarter — these are ~72,000 GPUs on multi-year contracts. So the pool is a fixed-size resource, and calling it directly means **no admission control**: when every worker is full, requests either pile up in connection queues until things time out, or get spread across workers so evenly that every generation is slow instead of some being fast. There's no component whose job is to decide *who gets compute and who waits*, so under load the system degrades everywhere at once.

Worse, naive per-request dispatch wastes the hardware even when it *isn't* busy — and the reason is the one piece of model mechanics worth actually understanding, because every scheduling decision below follows from it.

### The mechanical floor, in three numbers

*Enough to answer "why?" one level down, and no more — the model is a black box with a latency, a cost, and a capacity, and the engineering is everything around it (trap 21).*

**One request cannot keep a GPU busy.** Generating a token means streaming every weight in the model through the compute units once. On one H100, for a 70B model:

| | One decode step, batch of 1 |
|---|---|
| Weights to move | ~140 GB |
| Time to move them | ~140 GB ÷ ~3.3 TB/s ≈ **40 ms** |
| Time to do the arithmetic they enable | ≈ **0.14 ms** |

**Forty milliseconds of hauling for a seventh of a millisecond of math.** Batching is the fix: the weights are identical for every request, so thirty-two sequences ride one trip to memory and each get a token — the math gets 32× more expensive and the math was never the bottleneck. That ~300× gap is the entire case for batching, and "memory-bandwidth bound" is its name.

**What caps the batch is the KV cache, not a knob.** Each sequence carries private attention state for every token it has seen — ~320 KB per token for a 70B model, so a chat with 20k tokens of history holds ~6 GB by itself. An 8-GPU server has ~640 GB, ~140 GB of it weights; the remaining ~500 GB divided by ~6 GB is where **~64 concurrent sequences** comes from. **Long conversations literally consume batch slots**, which is why §11's pruning is a capacity lever and not just a cost one.

**Prefill and decode land on opposite sides of the hardware's break-even.** Prefill runs the whole prompt in one parallel pass; decode produces one token per pass and cannot parallelize within a request, because token *N+2* needs token *N+1* to have been sampled first.

| | Prefill (2,000 tokens) | Decode (500 tokens) |
|---|---|---|
| Forward passes | **1** | **500, strictly sequential** |
| Arithmetic per byte moved | ~2,000 FLOP/byte → **compute-bound** | ~1 FLOP/byte → **memory-bound** |
| What it costs the user | **TTFT**, linear in context length | inter-token latency, paid by everyone sharing the batch |

That table is why TTFT and inter-token latency are separate problems with separate fixes, why context length hurts TTFT specifically, and why a batch is the only lever decode has.

### What replaces it

**A queue in front of a fixed pool, and continuous batching inside each worker.**

- **Batching pays for the haul** — the mechanism above. One fetch of the weights advances every sequence in the batch by one token, so throughput scales with batch size while wall-clock barely moves.
- **"Continuous" is the scheduling half, and it's the part that's actually a design decision.** *Static* batching forms a batch of 64, runs it to completion, and only then starts the next — so a one-line reply finishes in 10 steps and its slot **sits empty for the remaining 1,990** while a 2,000-token essay grinds on beside it. The batch decays toward one active sequence, which is exactly the starved case you built the batch to avoid. **Continuous batching re-forms the batch every single decode step**: a finished sequence is evicted the moment it emits its stop token and a queued one takes the slot on the next step. Utilization stays flat instead of sawtoothing. *(vLLM and TGI are the production implementations; naming one is fine, but the mechanism is the point.)*
- **The wrinkle worth volunteering:** a joining sequence needs its prefill done, and prefill is a big compute-bound burst (see above). Run it as one step and **every other sequence in the batch stalls for it** — one user pasting a 30k-token document adds a visible hitch to sixty-three other people's inter-token latency. The fix is **chunked prefill**: split the newcomer's prompt across several steps and interleave it with decode. **This is the concrete mechanism behind "one huge prompt degrades everyone," which is why §10 meters tokens rather than requests.**
- **Speculative decoding** — a small draft model guesses the next few tokens and the large model verifies them in one pass, turning several starved decode steps into one prefill-shaped step. Roughly 2× on decode for identical output, best on code and boilerplate. **An optimization inside the worker, not a change to anything above it.**
- **Workers pull; the scheduler doesn't push.** Under continuous batching only the worker knows when a slot frees, so it takes the next run from the tier queues itself (§10 for the weights). The "scheduler" is the sorted sets plus that pull loop — no component tracks slot state across 9,000 servers, and none can become the thing that decides wrongly for all of them.
- **Admission control at the door.** When queue depth exceeds what the pool can drain within the target wait, reject *new* runs with a clear, retryable state. **Never kill an in-flight run** — it has already consumed GPU-seconds, and killing it converts spent money into zero value. Shedding at the door is the only kind of shedding that saves anything.
- **Route by KV-cache affinity where you can.** A follow-up turn in a chat shares almost all of its prefix with the previous turn; land it on the worker that still has that prefix cached and you skip most of prefill. Best-effort — a worker can be full — and worth naming as a routing *preference* rather than a rule.

### What it costs

Queueing is added latency, and it's the honest trade: **under load the free tier waits, and the wait is visible.** The queue state lives in Redis, which puts Redis on the submit path with a failover story you own — a lost queue is retryable, but a slow one is a TTFT regression for everyone. And KV-affinity routing is in tension with pulling from a shared queue — sometimes the warm worker is the wrong worker, and you take the prefill hit rather than the wait.

---

## 10 · Deep dive — fairness across tiers, and why requests-per-minute is the wrong unit

### What you'd reach for first

A rate limit: N requests per minute per user, maybe a higher N for paid tiers.

### What breaks

**A request is not a unit of cost.** One user pasting a 30,000-token document and asking for a long summary consumes more GPU-seconds than a hundred users asking one-line questions. A requests-per-minute cap prices those identically, which means it fails at both jobs at once: it does not stop the expensive user from monopolizing the pool, and it *does* throttle the cheap user who's doing nothing wrong. **The limiter is measuring the wrong thing, so no value of N is correct.**

It also can't express business priority. Free, Plus, and Pro are not "different N" — they're a claim on scarce capacity that should mean something specific when the pool is full, and a flat cap says nothing about who waits.

### What replaces it: two separate mechanisms, and keeping them separate is the point

**Fairness across users → cost-aware token budgets.** Meter **tokens, not requests.** A sliding-window counter in Redis keyed `quota:{userId}:{window}`, incremented by `inputTokens + k·outputTokens` from the run record — output weighted higher because decode occupies a batch slot for far longer per token than prefill does. Check the budget **before enqueue** (Flow A step 3), where a rejection costs nothing.

Two extra caps worth naming because they close real holes:

- **A per-chat context cap.** Independent of the user budget, because one pathological conversation shouldn't be able to consume a whole account's daily budget in three turns — and it's what makes §11's pruning a *requirement* rather than a nicety.
- **A concurrency cap per user.** Ten tabs is ten batch slots. Token budgets are cumulative and slow to bite; a concurrency cap is instant, and it's the one that actually stops scripted abuse.

**Priority across tiers → weighted queues.** One queue per tier, drained by weight (say 8 : 3 : 1 for Pro : Plus : Free) rather than strict priority. **Strict priority starves the free tier completely the moment paid demand exceeds capacity, which is a product decision nobody made on purpose.** Weighted draining means the free tier slows down and stays alive. Add **aging** — a run's effective weight rises with wait time — so nothing sits forever, and cap free-tier `max_output_tokens` so a free run occupies a slot for a bounded time.

**Say the general rule out loud:** *"Fairness and priority are different problems and I want different mechanisms for them. Fairness is per-user cost accounting so nobody starves everyone else. Priority is scheduling weight so the business gets what it sold. Collapsing them into one rate limit is why rate limits never work on this shape of system."*

### What it costs

A Redis counter on the send path — one round trip, and Redis becomes a dependency on submit, so decide now that **it fails open** for the quota check (a brief window of unmetered usage beats a total outage) while §9's admission control still protects the pool. Weighted queues need tuning, and the weights are a product decision you'll be asked to defend. And the honest one: **the free tier degrades first, visibly, by design.** Say that plainly — it's the correct answer, and willingness to state it is part of what's being graded. **→ ties directly to the capacity NFR.**

---

## 11 · Deep dive — the conversation that never stops growing

### What you'd reach for first

Concatenate every prior message and send the whole transcript with each new prompt. It's what the high-level design does, and the assistant genuinely appears to remember everything.

### What breaks

Two things, one gradual and one absolute:

- **Cost and latency grow with the conversation.** A 50-turn chat re-sends ~25k input tokens every turn (§3). Prefill is compute-bound and roughly linear in input, **so turn 50 has several times the TTFT of turn 1.** The product gets slower and more expensive precisely for the users who use it most — the opposite of what you want.
- **It hits a wall.** Past the model's context window the request simply cannot be built. Real products surface this ("this conversation is too long"), and that's a legitimate answer, but leaning on it *as the only answer* means the product stops working for power users.

### What replaces it: an async pruner, and a prompt ordered for the cache

**1. Tiered context assembly, cheapest first.**

```
[ system prompt          ]  ← fixed, identical every request
[ rolling summary        ]  ← the middle of the conversation, compressed
[ last K turns verbatim  ]  ← recency matters most, keep it exact
[ the new prompt         ]  ← always unique
```

**2. Summarize asynchronously, never in the send path.** When a chat crosses a token threshold, a background job asks a *small, cheap* model to fold the oldest turns into the existing summary, and caches the result on the chat. Doing this inline would add a second model call to the moment the user is waiting, which trades the cost problem for a worse latency problem. **Update it incrementally** — fold new turns into the previous summary rather than re-summarizing the whole transcript — or the summarizer's own cost grows quadratically with conversation length, which is the failure mode of the naive version wearing a disguise.

**3. Order the prompt static → dynamic, and know exactly why.** Inference caches KV state by prefix: an identical leading span skips prefill for that span. The ordering above is stable-prefix-first, so turn N's system prompt and summary are already warm and only the tail needs prefilling. **Put anything volatile early — a timestamp, the user's name, a retrieved snippet — and you invalidate the entire prefix on every single turn.** Same tokens, same bill on paper, several hundred milliseconds of TTFT difference. **It is the highest ratio of impact to effort on this page and it is invisible unless you know to look.** **→ ties directly to the TTFT NFR.**

### What it costs

**Summarization loses detail, and it loses it silently.** Something in turn 3 that the summary dropped is gone, and the assistant will confidently proceed without it — this is the real cost and it's a product decision, not an engineering one. Mitigations to name: keep more verbatim turns, tune the threshold, or (the next step up, and the bridge to the RAG variant in §15) index the full transcript and retrieve from it semantically instead of summarizing, which trades a summarizer for a retriever. And the summary is now a cached derived value with an invalidation story you own.

---

## 12 · Data model, sharding, and storage decisions

**Partition key: `chatId`.** Every access pattern is per-chat — load a chat's messages, append to a chat, stream a chat's run — so co-locating a chat's rows makes the hot path a single-partition range scan. Sharding by `userId` looks tempting for the sidebar, but it makes one heavy user's data one shard's problem and gives nothing to the query that actually dominates.

**Is there a hot shard?** No, and that's worth saying out loud. **Every write goes to exactly one chat owned by exactly one user, so this workload has no write contention at all** — there is no celebrity tweet, no stadium onsale, no fifty-thousand-member channel.

**And no time bucket in the key, which is the contrast with Discord.** That page partitions on `(channel_id, bucket)` because a channel is unbounded and permanently hot. **A chat is neither: it has one writer taking turns with itself, and it stops being usable somewhere in the low hundreds of turns**, so `chatId` alone is a partition of a few hundred small rows and will never need splitting. Same data shape, different key, and the reason is a product fact rather than a database fact. *(This is the whole value of having both pages: the storage layer looks identical and the correct key isn't.)*

### The store, which is a genuine three-way debate

**The data model does not discriminate here — say that first.** Partition on the chat, cluster on time descending, range-scan the newest N. Cassandra, ScyllaDB, DynamoDB, and Bigtable all express that identically, so re-deriving the key for each one is wasted clock. **What actually decides it is the storage bill at petabyte scale and whether you have a team that runs a database.**

| Option | Fit | Why it wins or loses |
|---|---|---|
| **Postgres** (even + Citus) | Models it perfectly | **Rejected on operations.** At ~4 PB/yr and ~114k message writes/sec I'd be committing the team to hand-managed sharding, rebalancing, and a vacuum story forever. That's an ongoing tax paid in headcount, and none of the relational power I'd be buying is used on this path — there are no joins in "give me the last 50 messages of one chat" |
| **DynamoDB** | Fits exactly. PK `chatId`, SK `createdAt#id` | **The right answer at a tenth of this scale, and the right answer at any scale if I don't have a wide-column team.** Zero operations. It loses here on price: ~4 PB of *year one* alone is millions a year in storage, it compounds every year against append-only data, and there's no lever to pull because the bill is the product |
| **ScyllaDB / Cassandra** | Fits exactly. `PRIMARY KEY ((chat_id), created_at, message_id)`, clustering DESC | **Chosen.** LSM storage makes an append the cheapest write there is, a chat is one narrow sequential scan, and self-hosting a petabyte is a hardware bill rather than a per-GB rate. Scylla over Cassandra specifically to avoid JVM GC pauses in the p99, which is the reported failure at this size — **the same call the Discord page makes, for the same reason** |
| **Bigtable / HBase** | Fits exactly | A fine answer, and mostly a cloud-allegiance decision rather than a technical one. Say so instead of pretending there's a deep distinction |

**The sentence that carries it:** *"All four model this identically, so I'm not choosing on the data model — I'm choosing on who pays for a petabyte. Managed storage at this volume is a bill that compounds annually against data nobody reads, and at 200 M DAU I have the team to run Scylla, so I'd take the operational cost and keep the money. Flip that last clause and DynamoDB is immediately the better answer — that's the specific thing that would change my mind."*

**What the choice costs, volunteered:** repair, compaction tuning, and node replacement become someone's job; you get no ad-hoc queries, so every access pattern needs a table designed for it up front; and there are no transactions across partitions, which is fine here because nothing in this product needs one.

| Component | Access pattern | Durability | Choice | The debate, in one sentence |
|---|---|---|---|---|
| **Messages** | Range scan by `chatId`, newest first; append-only; ~4 PB/yr | Must not lose an acked write | **ScyllaDB**, `PRIMARY KEY ((chat_id), created_at, message_id)`, clustering DESC | The three-way debate above — chosen on the petabyte bill, not the data model |
| **Runs** | Point read/write by `runId` from three different services | High, but small and short-lived | **ScyllaDB**, separate table, `PRIMARY KEY (run_id)` | "It gets its own table rather than living under `chat_id`, because the streaming tier and the cancel endpoint both arrive holding a `runId` and nothing else. In a wide-column store the answer to a second access pattern is a second table, not a secondary index" |
| **Chat sidebar** | Newest-first list per user, ~50 rows | High | **ScyllaDB**, `chats_by_user`, `PRIMARY KEY ((user_id), last_message_at, chat_id)` DESC | "Query-driven denormalization — the wide-column answer to a second access pattern. Bumping `last_message_at` is a delete-plus-insert of a mutable clustering key, normally an anti-pattern; **it's fine at ~200 bytes across a partition of dozens of rows**, and if the tombstones ever bit I'd move the ordering into a Redis sorted set per user and keep Scylla for the rows" |
| **Token log** | Append + replay-from-offset, 10-min TTL | **None, deliberately** | **Redis Streams**, `run:{runId}`, `EXPIRE` after `done` | The §8 debate — chosen for replay-from-offset, which is what makes reconnect free |
| Queue + scheduler state | Enqueue/dequeue by tier, ~57k/sec | Low — a lost queued run is retryable | **Redis sorted sets** per tier, score = enqueue time adjusted by aging | "Kafka is durable and ordered but I want priority and aging, and reordering is exactly what a log doesn't do. SQS has no priority. A sorted set is a priority queue with a score I control" |
| Quota counters | Read-modify-write per send | None | **Redis**, sliding window, **fails open** | "A quota check is not worth an outage. If it's down I lose metering for a minute; §9's admission control still protects the pool" |
| Idempotency keys | Point lookup per send | Low — 24 h is the retry horizon | **Redis**, `idem:{userId}:{key}` → `runId`, 24 h TTL, **fails closed** | "Opposite call to the quota counter, and say why: a missed quota check costs a minute of metering; a missed dedupe starts a second generation and streams two answers into one bubble" |
| Rolling summary | Read on every send for that chat; rewritten by the §11 job | Medium — recomputable from the transcript | **A column on the `chats` row** in ScyllaDB, with the token offset it covers | "It's per-chat, read with the chat, and derived — so it lives next to the thing it summarizes rather than in a cache I'd have to invalidate separately" |
| Cold chats | Rare full-chat reads | High, cheap | **S3**, one object per chat, pointer row retained in `chats_by_user` | See the lifecycle below |
| **Message persistence buffer** | Produce once per finished run (~57k/s), consume in batches | **High — this is the durability path** | **Kafka**, topic `messages`, `key = chatId` | "It exists so a GPU never waits on a database, and it's keyed by chat so turns can't persist out of order — the §8 debate" |
| Run/usage ledger | Append-heavy, analytical | High | **Object storage + a warehouse** | "This is billing, capacity planning, and abuse detection — columnar batch access, not a serving store. It should never share a database with the send path" |

### Data lifecycle, because append-only at 11 TB/day is a plan or it's a problem

Chats are written once and read rarely afterwards: **most reads land on chats touched in the last week, and the archive grows forever.** Three tiers, and the numbers are what make it a decision:

| Tier | Age | Where | Read latency |
|---|---|---|---|
| **Hot** | Active + last ~30 days | ScyllaDB, SSD-backed | Single-digit ms |
| **Warm** | 30–180 days | ScyllaDB, but the partition has aged out of cache | Tens of ms — a real disk read |
| **Cold** | > 180 days, untouched | **S3, one JSON object per chat**, metadata row retained so the sidebar still lists it | **~1 s hydrate**, behind a skeleton, and re-promoted on read |

**Why archive whole chats rather than trimming old messages inside one:** a chat is the natural read unit, so an object per chat is one `GET` to restore, and it keeps the sidebar working with no special cases. **The user-visible cost is that opening a two-year-old conversation is noticeably slower than opening yesterday's** — an acceptable trade you should state rather than hide, because the alternative is paying hot-storage prices for petabytes nobody reads.

Then the compliance edge that comes with it: **deletion must reach all three tiers**, and a delete of a cold chat is an S3 delete plus a Scylla tombstone, not a row update. **Tombstones are their own trap in a wide-column store** — they're written, not applied, and they don't go away until compaction passes `gc_grace_seconds`, so a bulk delete of old chats is a background operation you schedule rather than a statement you run. Naming that is the difference between a lifecycle policy and a lifecycle problem.

---

## 13 · Traps — the ranked list

**Design traps**

1. **No `Run` entity.** Everything downstream — resume, cancel, quotas, scheduling, cost attribution — has no noun to attach to, and run state ends up as nullable columns on the message row.
2. **One endpoint that both submits and streams.** Resume becomes impossible without a redesign, and a refresh costs a generation.
3. **Treating a closed connection as a cancel.** It's the opposite: the run must survive it. Cancellation is an explicit signal.
4. **Cancellation that doesn't reach the GPU.** The animation stops, the batch slot stays occupied for 30 seconds, and you pay for every token.
5. **Holding SSE connections in the API tier.** Every routine deploy severs hundreds of thousands of live streams.
6. **A push registry or pub/sub in place of a replayable log.** The registry rebuilds the coupling the log exists to remove, as a distributed-state problem; pub/sub hands a reconnecting client whatever arrives next and silently loses the gap.
7. **Nobody watching for a dead worker.** The run stays `running` forever, the stream just goes quiet, and the client cannot tell a crash from a slow token. Silence on the log is the signal; a reaper acts on it.
8. **Rate-limiting requests instead of tokens.** A request is not a unit of cost; no value of N is correct.
9. **Strict priority between tiers.** Free traffic starves completely the first time paid demand exceeds capacity.
10. **Killing in-flight runs to shed load.** Converts spent GPU-seconds into zero value. Shed at the door only.
11. **Autoscaling the GPU pool.** You cannot buy 9,000 servers during a spike. It's a scheduling problem, not a capacity problem.
12. **Volatile content early in the prompt.** Destroys prefix caching and hundreds of milliseconds of TTFT for free.
13. **Replaying the full transcript every turn, or summarizing it synchronously.** The first grows cost and TTFT with conversation length until it hits a hard ceiling; the second trades that for a worse latency problem in the send path.
14. **Offset pagination on messages.** A growing list makes offsets skip and repeat, and deep offsets are slow.
15. **No idempotency key on send.** A retried submit double-charges a scarce resource and streams two answers into one bubble.
16. **The GPU worker writing to the database itself.** Couples the most expensive resource in the system to the availability of the cheapest, so a storage p99 spike becomes a capacity outage.
17. **Misjudging the token log's blast radius.** Redis down loses the live *view*, not the answer — provided the worker never blocks on `XADD` and durability doesn't route through Redis. Unbounded, its OOM takes out every live stream at once: bound the buffer, TTL the key.
18. **No data lifecycle.** ~4 PB/year of append-only chat with no tiering is a bill that compounds.
19. **Pricing your own serving cost off published API rates.** Overstates it by more than 10×; the unit is GPU-seconds.
20. **Optimizing total completion time instead of TTFT.** Users tolerate ten seconds of streaming and not three seconds of blank screen.

**Interview-performance traps** → `00-interview-mechanics.md` §6. The two specific to this problem:

21. **Spending fifteen minutes inside the model.** Attention, quantization, and fine-tuning are a different interview. The model is a black box with a latency, a cost, and a capacity; the engineering is everything around it.
22. **Designing the message schema first.** It's the most familiar part and the least interesting, and the clock it eats comes straight out of §9 and §10.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 606" role="img" aria-label="ChatGPT five-minute skeleton. A numbers banner, then the three tiers, the Run entity, the two-call submit and stream split, SSE, the Redis stream path, the two cheap writes on completion, cancellation, shedding, prefill versus decode, metering, context assembly and the storage layout.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="92.5">57k generations/sec · 570 k concurrent streams · ~72 k GPUs · ~$3.5 M/day · ~4 PB/yr</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">13</text>
  <circle class="dg-num" cx="22" cy="132" r="9"></circle>
  <text class="dg-num-t" x="22" y="135.4">1</text>
  <text class="dg-lane" x="38" y="136">THREE TIERS — ~50 MACHINES AGAINST ~9,000</text>
  <rect class="dg-box" x="30" y="150" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="178.5">API — CRUD</text>
  <text class="dg-s dg-c" x="170" y="194.5">stateless, scales on requests</text>
  <rect class="dg-box" x="350" y="150" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="490" y="178.5">Streaming — sockets</text>
  <text class="dg-s dg-c" x="490" y="194.5">570 k connections, no run state</text>
  <rect class="dg-box" x="670" y="150" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="178.5">Inference — GPUs</text>
  <text class="dg-s dg-c" x="815" y="194.5">fixed pool, scheduled not scaled</text>
  <rect class="dg-box" x="30" y="234" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="262.5">Run</text>
  <text class="dg-s dg-c" x="170" y="278.5">queued → running → done / failed</text>
  <circle class="dg-num" cx="30" cy="234" r="9"></circle>
  <text class="dg-num-t" x="30" y="237.4">2</text>
  <rect class="dg-box" x="350" y="234" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="490" y="262.5">Submit ≠ stream</text>
  <text class="dg-s dg-c" x="490" y="278.5">POST returns runId; GET streams</text>
  <circle class="dg-num" cx="350" cy="234" r="9"></circle>
  <text class="dg-num-t" x="350" y="237.4">3</text>
  <rect class="dg-box" x="670" y="234" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="262.5">SSE, not WebSocket</text>
  <text class="dg-s dg-c" x="815" y="278.5">Last-Event-ID replay · cancel is a POST</text>
  <circle class="dg-num" cx="670" cy="234" r="9"></circle>
  <text class="dg-num-t" x="670" y="237.4">4</text>
  <rect class="dg-box" x="30" y="318" width="600" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="330" y="346.5">Worker → Redis Stream run:{runId} → streaming tier</text>
  <text class="dg-s dg-c" x="330" y="362.5">SSE event id = Redis entry id, so reconnect is a replay from an offset</text>
  <circle class="dg-num" cx="30" cy="318" r="9"></circle>
  <text class="dg-num-t" x="30" y="321.4">5</text>
  <rect class="dg-box" x="650" y="318" width="310" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="805" y="338.5">Two cheap writes, no DB call</text>
  <text class="dg-s dg-c" x="805" y="354.5">terminal entry + Kafka by chatId</text>
  <text class="dg-s dg-c" x="805" y="370.5">a GPU never waits on storage</text>
  <circle class="dg-num" cx="650" cy="318" r="9"></circle>
  <text class="dg-num-t" x="650" y="321.4">6</text>
  <rect class="dg-warn" x="30" y="402" width="300" height="50" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="180" y="423.5">A closed socket is not a cancel</text>
  <text class="dg-s dg-c" x="180" y="439.5">cancel must reach the GPU</text>
  <circle class="dg-num" cx="30" cy="402" r="9"></circle>
  <text class="dg-num-t" x="30" y="405.4">7</text>
  <rect class="dg-box" x="350" y="402" width="300" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="423.5">Shed at the door</text>
  <text class="dg-s dg-c" x="500" y="439.5">workers pull; never kill work in flight</text>
  <circle class="dg-num" cx="350" cy="402" r="9"></circle>
  <text class="dg-num-t" x="350" y="405.4">8</text>
  <rect class="dg-box" x="670" y="402" width="290" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="423.5">Prefill compute-bound</text>
  <text class="dg-s dg-c" x="815" y="439.5">decode is bandwidth-bound</text>
  <circle class="dg-num" cx="670" cy="402" r="9"></circle>
  <text class="dg-num-t" x="670" y="405.4">9</text>
  <rect class="dg-box" x="30" y="472" width="460" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="493.5">Meter tokens, not requests</text>
  <text class="dg-s dg-c" x="260" y="509.5">weighted queues with aging, not strict priority</text>
  <circle class="dg-num" cx="30" cy="472" r="9"></circle>
  <text class="dg-num-t" x="30" y="475.4">10</text>
  <rect class="dg-box" x="510" y="472" width="450" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="493.5">Context: system → summary → last K</text>
  <text class="dg-s dg-c" x="735" y="509.5">stable prefix first, for the KV cache</text>
  <circle class="dg-num" cx="510" cy="472" r="9"></circle>
  <text class="dg-num-t" x="510" y="475.4">11</text>
  <rect class="dg-box" x="30" y="542" width="930" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="568.5">ScyllaDB partitioned on chatId · a second table for the sidebar · hot/warm/cold at 30 and 180 days</text>
  <circle class="dg-num" cx="30" cy="542" r="9"></circle>
  <text class="dg-num-t" x="30" y="545.4">12</text>
</svg>
</div>

<p class="diagram-cap">Thirteen marks, and the top row carries the argument: ~50 machines against ~9,000 is why the tiers are separate deploys. Say the ratio before you draw the second box.</p>

1. **Three tiers: API (CRUD), Streaming (sockets), Inference (GPUs).** Say the ~50 machines vs ~9,000 ratio — that ratio is the reason they're separate.
2. **`Run` is an entity.** Queued → running → done / canceled / failed. Everything hard is an operation on it.
3. **Submit and stream are two calls.** `POST /messages` returns `{ userMessageId, runId }` immediately; `GET /runs/{id}/stream` is SSE. Optimistic echo hides the round trip.
4. **SSE over WebSocket** — one-way tokens, free reconnect via `Last-Event-ID`; cancel is a separate POST and that's the price.
5. **Inference worker → Redis Stream `run:{runId}` → streaming tier.** Neither side knows the other. **SSE event id = Redis entry id**, so reconnect is a replay from an offset.
6. **On completion, two cheap writes and no database call**: terminal entry to the log (the user sees it now) + the message to **Kafka keyed by `chatId`**, which a persister batch-writes to Scylla. **A GPU never waits on storage.**
7. **A closed socket is not a cancel.** Cancel is explicit and must reach the GPU; a dead worker is detected by silence on the log.
8. **Fixed GPU pool + priority queue + continuous batching.** You cannot autoscale it. Workers pull when a slot frees; shed at the door, never kill in-flight.
9. **Prefill is compute-bound (that's your TTFT); decode is bandwidth-bound.** Every context token is paid while the user watches a blank screen.
10. **Meter tokens, not requests**, per user; **weighted queues with aging**, not strict priority, per tier. Fairness and priority are different mechanisms.
11. **Context: system prompt → rolling summary → last K turns → new prompt.** Async incremental summarizer, stable prefix first for the KV cache.
12. **ScyllaDB partitioned on `chatId`** (no time bucket — unlike Discord, a chat has one writer and is bounded), a second table for the sidebar, **hot/warm/cold at 30 and 180 days** with whole chats to S3.
13. **Numbers to have in the margin:** 57k gen/sec · **570k concurrent streams** · ~72k GPUs · **~$3.5M/day** · ~4 PB/yr.

---

## 15 · Variants — what actually changes

**The axis that governs this family: what does the model need besides the conversation, and who is allowed to see it?** As you move down, the hard problem migrates from *the run lifecycle* to *authorization and termination* — but §7 and §8 survive every row unchanged, which is why this page is the foundation for the rest.

| Variant | What it adds | What changes |
|---|---|---|
| **This page — pure conversation** | Nothing | Run lifecycle, scheduling, and context cost are the whole design |
| **Chat over private documents** (internal assistant, support bot) | **Retrieval, and permissions** | Retrieval quality now bounds answer quality, and the model must never receive a chunk the asker can't read — **filter before prompt assembly, never after generation, and never cache an answer under a key that omits permission context.** The run lifecycle is unchanged; the hard invariant moves from "don't lose the run" to "don't leak the document" |
| **Editing or branching a message** | A conversation is a tree, not a list | Messages get a `parentId`; the sidebar shows a path through the tree. Cheap on the read side, and it makes prefix caching *better* — siblings share a prefix by construction |
| **Multimodal input** | Images and audio in | Tokenization changes and inputs get much larger, so **prefill dominates and TTFT degrades**. Upload becomes its own async pipeline; the streaming half is untouched |
| **Tool calling / agent runs** | The model acts | A run becomes **multi-step with unpredictable duration**, so the token log carries step events, not just tokens. New problems: **authorization per tool call**, idempotency on retried actions, **termination conditions**, and cost explosion via loops. Everything on this page still applies and is no longer sufficient |
| **Inline code completion** | A ~200 ms ceiling | **Too tight for a queue, a large model, or retrieval.** Small specialized model, aggressive suppression, cancellation as the dominant cost lever. A different architecture — see the Cursor Tab page, which is this row worked out in full |
| **Batch / offline generation** | No user waiting | **The latency requirement vanishes entirely.** No streaming, no TTFT, no run lifecycle — batch the pool to ~100% utilization and optimize purely for throughput per GPU-hour. The inverse of this page |

**The general lesson:** pure conversation is the *simplest* point in this family and the only one where the run lifecycle is the whole story. Everything below it inherits §7 through §11 intact and adds either an authorization problem or a termination problem on top.
