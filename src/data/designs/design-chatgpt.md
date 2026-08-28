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

> "The chat product itself is CRUD — conversations, messages, a sidebar — and I'll build that in about five minutes and not linger. What makes this hard is that the answer is produced by a fixed pool of GPUs, takes ten seconds, and costs real money, which gives me three problems. **First, the generation outlives the request that started it** — so I'm going to make a `Run` a first-class entity, split submit from stream, and make the stream resumable, because a refresh or a deploy must not cost a generation we're already paying for. **Second, capacity is fixed** — 20-odd thousand prompts a second against GPUs I can't buy more of today, so I need a queue and admission control, not autoscaling. **Third, cost is per token and conversations grow forever**, so context management is a real design problem rather than a footnote. I'd like to spend most of my time on the run lifecycle and on scheduling — roughly five minutes each — and I'll tie every choice back to the non-functional requirements as I go."

**Why open this way:** it does three things at once — it *deprioritises* the CRUD out loud, which buys you the clock; it names the seam that makes the problem interesting; and it pre-commits two dives, so you choose the ground you fight on. Anyone who opens by designing the message table has spent their best minutes on the least interesting part of the system.

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
| A run survives losing its GPU worker | **Best-effort, and say so:** restart from scratch if < 50 tokens were emitted; otherwise finalise what we have and emit `error` | The one place we accept a partial failure, because restarting a 900-token generation costs more than it saves |
| Chat state consistency | **Read-your-writes for the author. ≤ 1 s staleness for everything else** | The sidebar may be a second stale on a second device; the tab you typed in may never be. Forces a stronger read (`LOCAL_QUORUM`) on exactly one query and the cheap read everywhere else |
| Chat title freshness | Generated async, visible **≤ 2 s**, "New chat" until then | An extra model call must never sit in the send path |
| Message durability | The assistant message is durable **≤ 1 s after `done`**, asynchronously. **Individual tokens are not durable** | Deliberate twice over: the token log is a replay buffer with a TTL, and persistence is buffered so a GPU never waits on the store (§8). The gap is covered by the client's own buffer |
| Availability | 99.9% for send and stream; **99.99% for reading history** | Reading yesterday's chat must survive a bad day in the inference tier entirely. Forces the read path to share nothing with the generation path |
| Capacity | Fixed GPU pool. Under overload, **queue the free tier; never kill an in-flight run** | Forces admission control (§9) and tier-weighted scheduling (§10) |
| Cost | Measured in **GPU-seconds per run**, ~$1M+/day (§3) | Forces token-based quotas (§10) and context pruning (§11) |
| Scale | ~57k generations/sec average; **~570k concurrent open streams** | Forces a separate, stateless streaming tier (§7) |

**The sentence that earns the point:** *"Almost everything here is a latency or a capacity target and degrades gracefully. Exactly one thing doesn't: a generation we are already paying for must never be lost by anything on our side — not a refresh, not a tunnel, not our own deploy. That's the only place I'll spend real correctness machinery, and everything in the run lifecycle follows from it."*

---

## 3 · Numbers that reframe the problem

**Traffic, with the assumption labelled**

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

- ~5B messages/day × ~1 KB ≈ **5 TB/day, ~1.8 PB/year**, append-only, never deleted, and growing. §12 has the lifecycle, because "unbounded growth with no plan" is a real finding at this scale.

---

## 4 · Core entities

- **User** — id, **tier** (`free` | `plus` | `pro`). The tier is not a billing detail here; it's an input to the scheduler (§10)
- **Chat** — id, userId, title, createdAt, `lastMessageAt`
- **Message** — id, chatId, **role** (`user` | `assistant`), content, createdAt, tokenCount
- **Run** — id, chatId, messageId, **status** (`queued` | `running` | `done` | `cancelled` | `failed`), model, promptVersion, inputTokens, outputTokens, workerId

**Load-bearing details:**

- **`Run` is the entity nobody creates, and creating it is most of the answer.** A `Message` is finished text; a run is *one attempt to produce it*, and that attempt has a life of its own — it can queue, start, stall, be cancelled, fail at token 300, and be retried, all before any assistant message exists to write down. Every hard thing on this page (resumable streams, cancellation, quotas, scheduling, cost attribution) is an operation on a run. **If your entity list is User/Chat/Message, you have no noun to hang any of it on**, and you'll end up smuggling run state into the message row as nullable columns.
- **`Run.status` is the thing the client polls when it has no stream**, and it's how "the tab closed but the answer finished" is even expressible.
- **`Chat.lastMessageAt` is denormalised on purpose** — the sidebar is `ORDER BY lastMessageAt DESC` and computing it from messages on every sidebar load is the one query that would actually hurt.
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
<svg viewBox="0 0 1000 640" role="img" aria-label="ChatGPT architecture. A request row: clients, a stateless API tier of gateway and chat service, a scheduler, and a fixed GPU pool. Each GPU makes two independent writes: token-by-token into Redis Streams for the live view, and one finished message into Kafka for durability. Redis Streams feeds a streaming tier of stateless SSE instances; Kafka feeds a persister that batch-writes to ScyllaDB. Redis also holds quota counters and the priority queues; S3 holds cold chats.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Three tiers, ~50 machines against ~9,000 — and two independent writes out of every GPU, one lossy, one durable.</text>
  <rect class="dg-box" x="20" y="118" width="140" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="90" y="154.5">Clients</text>
  <rect class="dg-group" x="190" y="86" width="360" height="130" rx="12"></rect>
  <text class="dg-group-t" x="206" y="108">API — STATELESS CRUD</text>
  <rect class="dg-box" x="206" y="118" width="150" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="281" y="154.5">API Gateway</text>
  <rect class="dg-box" x="376" y="118" width="158" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="455" y="146.5">Chat Service</text>
  <text class="dg-s dg-c" x="455" y="162.5">CRUD + enqueue</text>
  <path class="dg-line" d="M 356,150 L 368,150"></path>
  <path class="dg-head" d="M 368,155 L 368,145 L 376,150 Z"></path>
  <rect class="dg-group" x="580" y="86" width="180" height="130" rx="12"></rect>
  <text class="dg-group-t" x="596" y="108">SCHEDULER</text>
  <rect class="dg-box" x="596" y="118" width="148" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="670" y="146.5">Scheduler</text>
  <text class="dg-s dg-c" x="670" y="162.5">weights + aging</text>
  <rect class="dg-group" x="790" y="86" width="190" height="130" rx="12"></rect>
  <text class="dg-group-t" x="806" y="108">INFERENCE</text>
  <rect class="dg-box" x="806" y="118" width="158" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="885" y="146.5">GPU workers</text>
  <text class="dg-s dg-c" x="885" y="162.5">continuous batching</text>
  <path class="dg-line" d="M 160,150 L 198,150"></path>
  <path class="dg-head" d="M 198,155 L 198,145 L 206,150 Z"></path>
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
  <path class="dg-box" d="M 190,297 L 190,347 A 140,7 0 0 0 470,347 L 470,297 A 140,7 0 0 0 190,297 Z"></path>
  <path class="dg-box" d="M 190,297 A 140,7 0 0 0 470,297" style="fill:none"></path>
  <text class="dg-t dg-c" x="330" y="314">Redis Streams</text>
  <text class="dg-s dg-c" x="330" y="330">run:{runId}, XADD per token</text>
  <text class="dg-s dg-c" x="330" y="346">lossy, 10-minute TTL</text>
  <rect class="dg-box" x="730" y="290" width="250" height="64" rx="8"></rect>
  <path class="dg-qbar" d="M 743,299 L 743,345"></path>
  <path class="dg-qbar" d="M 752,299 L 752,345"></path>
  <path class="dg-qbar" d="M 761,299 L 761,345"></path>
  <text class="dg-t dg-c" x="873" y="318.5">Kafka</text>
  <text class="dg-s dg-c" x="873" y="334.5">key = chatId · one message</text>
  <rect class="dg-box" x="190" y="400" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="330" y="428.5">Streaming instances</text>
  <text class="dg-s dg-c" x="330" y="444.5">stateless · XREAD from last id</text>
  <rect class="dg-box" x="730" y="400" width="250" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="855" y="428.5">Persister</text>
  <text class="dg-s dg-c" x="855" y="444.5">batches writes</text>
  <path class="dg-line" d="M 330,354 L 330,392"></path>
  <path class="dg-head" d="M 325,392 L 335,392 L 330,400 Z"></path>
  <path class="dg-line" d="M 855,354 L 855,392"></path>
  <path class="dg-head" d="M 850,392 L 860,392 L 855,400 Z"></path>
  <path class="dg-box" d="M 190,517 L 190,567 A 140,7 0 0 0 470,567 L 470,517 A 140,7 0 0 0 190,517 Z"></path>
  <path class="dg-box" d="M 190,517 A 140,7 0 0 0 470,517" style="fill:none"></path>
  <text class="dg-t dg-c" x="330" y="542">Redis</text>
  <text class="dg-s dg-c" x="330" y="558">quota · priority queues · aging</text>
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
  <path class="dg-line" d="M 455,182 L 455,232 L 178,232 L 178,542 L 182,542"></path>
  <path class="dg-head" d="M 182,547 L 182,537 L 190,542 Z"></path>
  <path class="dg-line" d="M 534,150 L 560,150 L 560,486 L 710,486 L 710,542 L 722,542"></path>
  <path class="dg-head" d="M 722,547 L 722,537 L 730,542 Z"></path>
  <text class="dg-lbl" x="566" y="478">read history</text>
  <path class="dg-line" d="M 190,432 L 170,432 L 170,200 L 168,200"></path>
  <path class="dg-head" d="M 168,195 L 168,205 L 160,200 Z"></path>
  <text class="dg-note" x="20" y="610">Redis carries tokens for the live view and is allowed to lose them; Kafka carries one finished message and is not. Different failure, different blast radius.</text>
</svg>
</div>

<p class="diagram-cap">The fork under the GPU is the whole board. Two arrows leave every worker, to two different systems, for two different reasons — and neither is a backup for the other. Lose Redis and the animation breaks while the answer is still stored; lose Kafka and the user watches a perfect answer you then fail to keep.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 872" role="img" aria-label="ChatGPT high-level design. Write path: client, API gateway, chat service, ScyllaDB, with a quota check at the door before enqueue. The chat service enqueues to a scheduler, priority queues by tier, and a fixed pool of inference workers. Each worker makes two independent writes that never meet: token-by-token XADD into Redis Streams for the lossy live view, which the streaming tier tails and forwards over SSE, and one finished message into Kafka keyed by chat id for durability, which a persister batch-writes to ScyllaDB. Read path: client to gateway to chat service to ScyllaDB.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Two independent writes out of the GPU — different systems, different reasons, and neither is a backup for the other.</text>
  <text class="dg-lane" x="30" y="76">WRITE / GENERATE</text>
  <rect class="dg-box" x="30" y="90" width="110" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="85" y="122.5">Client</text>
  <rect class="dg-box" x="170" y="90" width="140" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="240" y="122.5">API Gateway</text>
  <rect class="dg-box" x="340" y="90" width="180" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="430" y="114.5">Chat Service</text>
  <text class="dg-s dg-c" x="430" y="130.5">CRUD + enqueue</text>
  <rect class="dg-box" x="550" y="90" width="200" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="650" y="114.5">ScyllaDB</text>
  <text class="dg-s dg-c" x="650" y="130.5">chats, messages, runs</text>
  <rect class="dg-good" x="780" y="90" width="180" height="56" rx="8"></rect>
  <text class="dg-good-t dg-c" x="870" y="114.5">Quota at the door</text>
  <text class="dg-s dg-c" x="870" y="130.5">rejection costs 0 GPU-seconds</text>
  <path class="dg-line" d="M 140,118 L 162,118"></path>
  <path class="dg-head" d="M 162,123 L 162,113 L 170,118 Z"></path>
  <path class="dg-line" d="M 310,118 L 332,118"></path>
  <path class="dg-head" d="M 332,123 L 332,113 L 340,118 Z"></path>
  <path class="dg-line" d="M 520,118 L 542,118"></path>
  <path class="dg-head" d="M 542,123 L 542,113 L 550,118 Z"></path>
  <path class="dg-line" d="M 430,146 L 430,172"></path>
  <path class="dg-head" d="M 425,172 L 435,172 L 430,180 Z"></path>
  <text class="dg-lbl" x="445" y="168">enqueue</text>
  <rect class="dg-box" x="340" y="180" width="180" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="430" y="202.5">Scheduler</text>
  <text class="dg-s dg-c" x="430" y="218.5">tier weight + aging</text>
  <path class="dg-line" d="M 430,232 L 430,258"></path>
  <path class="dg-head" d="M 425,258 L 435,258 L 430,266 Z"></path>
  <rect class="dg-box" x="300" y="266" width="260" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="430" y="288.5">Priority queues</text>
  <text class="dg-s dg-c" x="430" y="304.5">free / plus / pro</text>
  <path class="dg-line" d="M 430,318 L 430,344"></path>
  <path class="dg-head" d="M 425,344 L 435,344 L 430,352 Z"></path>
  <rect class="dg-box" x="280" y="352" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="430" y="380.5">Inference workers</text>
  <text class="dg-s dg-c" x="430" y="396.5">fixed GPU pool · continuous batching</text>
  <path class="dg-line" d="M 430,416 L 430,450"></path>
  <path class="dg-line" d="M 200,450 L 720,450"></path>
  <path class="dg-line" d="M 200,450 L 200,478"></path>
  <path class="dg-head" d="M 195,478 L 205,478 L 200,486 Z"></path>
  <path class="dg-line" d="M 720,450 L 720,478"></path>
  <path class="dg-head" d="M 715,478 L 725,478 L 720,486 Z"></path>
  <text class="dg-lbl dg-c" x="460" y="470">two independent writes — neither is a backup for the other</text>
  <rect class="dg-box" x="80" y="486" width="240" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="200" y="506.5">Redis Streams</text>
  <text class="dg-s dg-c" x="200" y="522.5">key run:{runId} · XADD per token</text>
  <text class="dg-s dg-c" x="200" y="538.5">lossy and TTL'd — costs the animation</text>
  <path class="dg-line" d="M 200,550 L 200,576"></path>
  <path class="dg-head" d="M 195,576 L 205,576 L 200,584 Z"></path>
  <rect class="dg-box" x="60" y="584" width="310" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="215" y="604.5">Streaming Tier</text>
  <text class="dg-s dg-c" x="215" y="620.5">~570 k SSE connections, no run state</text>
  <text class="dg-s dg-c" x="215" y="636.5">XREAD from last-seen id → SSE</text>
  <path class="dg-line" d="M 200,648 L 200,668"></path>
  <path class="dg-head" d="M 195,668 L 205,668 L 200,676 Z"></path>
  <rect class="dg-box" x="60" y="676" width="310" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="215" y="700.5">Client — SSE, Last-Event-ID replays</text>
  <rect class="dg-box" x="600" y="486" width="240" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="720" y="506.5">Kafka</text>
  <text class="dg-s dg-c" x="720" y="522.5">topic messages, key = chatId</text>
  <text class="dg-s dg-c" x="720" y="538.5">exactly one finished message</text>
  <path class="dg-line" d="M 720,550 L 720,576"></path>
  <path class="dg-head" d="M 715,576 L 725,576 L 720,584 Z"></path>
  <rect class="dg-box" x="600" y="584" width="240" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="720" y="606.5">Persister</text>
  <text class="dg-s dg-c" x="720" y="622.5">batches writes</text>
  <path class="dg-line" d="M 720,636 L 720,660"></path>
  <path class="dg-head" d="M 715,660 L 725,660 L 720,668 Z"></path>
  <rect class="dg-box" x="600" y="668" width="240" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="720" y="692.5">ScyllaDB</text>
  <rect class="dg-ghost" x="395" y="560" width="180" height="110" rx="8"></rect>
  <text class="dg-lane dg-c" x="485" y="584">THEY NEVER MEET</text>
  <text class="dg-s dg-c" x="485" y="605">the streaming tier reads</text>
  <text class="dg-s dg-c" x="485" y="622">Redis and only Redis</text>
  <text class="dg-s dg-c" x="485" y="639">Kafka never feeds a stream</text>
  <path class="dg-div" d="M 20,740 L 980,740"></path>
  <text class="dg-lane" x="30" y="766">READ / HISTORY</text>
  <rect class="dg-box" x="30" y="780" width="110" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="85" y="816.5">Client</text>
  <rect class="dg-box" x="170" y="780" width="150" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="245" y="816.5">API Gateway</text>
  <rect class="dg-box" x="350" y="780" width="180" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="440" y="816.5">Chat Service</text>
  <rect class="dg-box" x="560" y="780" width="260" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="690" y="800.5">ScyllaDB</text>
  <text class="dg-s dg-c" x="690" y="816.5">LOCAL_ONE for the sidebar</text>
  <text class="dg-s dg-c" x="690" y="832.5">your own chat: LOCAL_QUORUM</text>
  <path class="dg-line" d="M 140,812 L 162,812"></path>
  <path class="dg-head" d="M 162,817 L 162,807 L 170,812 Z"></path>
  <path class="dg-line" d="M 320,812 L 342,812"></path>
  <path class="dg-head" d="M 342,817 L 342,807 L 350,812 Z"></path>
  <path class="dg-line" d="M 530,812 L 552,812"></path>
  <path class="dg-head" d="M 552,817 L 552,807 L 560,812 Z"></path>
</svg>
</div>

<p class="diagram-cap">Draw the fork under the GPU first. Redis carries tokens for the live view and is allowed to lose them; Kafka carries one finished message and is not. Lose Redis and the animation breaks while the answer still gets stored — lose Kafka and the user watches a perfect answer you then fail to keep.</p>

Three tiers, and the split is the design:

- **Chat Service** — stateless CRUD plus enqueue. Cheap, scales on request rate.
- **Streaming Tier** — holds ~570k SSE connections, owns no run state, tails the token log. Scales on *connection count* and deploys on its own schedule (§7).
- **Inference Workers** — the GPU pool. Fixed size, scheduled rather than autoscaled (§9).

**The two write paths out of the worker are independent, and neither is a backup for the other.** Redis carries tokens for the *live view* and is deliberately lossy; Kafka carries one finished message for *durability* and must not drop it. **The streaming tier reads Redis and only Redis** — it never touches Kafka, and Kafka never feeds a stream. Lose Redis and the live view breaks while the answer still gets stored (§8); lose Kafka and the user watches a perfectly good answer that we then fail to persist. **Different failure, different blast radius, which is exactly why they aren't the same system.**

### Flow A — a turn

1. Client **optimistically renders** the user's bubble and an empty assistant bubble in `pending`. Nothing has been confirmed yet; this is what hides the extra round trip from §5.
2. `POST /chats/{id}/messages` with an `Idempotency-Key`. Chat Service dedupes on it, writes the user message, bumps `lastMessageAt`, creates a `Run` in `queued`, returns `{ userMessageId, runId }`.
3. **Quota check happens here, before enqueue** — token budget for this user and tier (§10). A rejection at this point costs zero GPU-seconds, which is the entire point of checking at the door.
4. Client opens `GET /runs/{runId}/stream`. The load balancer routes it to *any* streaming instance; none of them is special.
5. Scheduler dequeues by tier weight, assigns the run to an **inference worker** — a GPU node — with a free batch slot, and flips the status to `running`. **"Worker" on this page always means a GPU node; the streaming tier has no workers, only connection holders.**
6. The inference worker builds the prompt — stable prefix first (§11) — and generates. Each token is `XADD`ed to `run:{runId}` in Redis Streams.
7. The streaming instance holding this client `XREAD`s from the last id it sent and forwards each entry as an SSE event. The browser appends.
8. On completion the inference worker does **two cheap writes and no database call**: it appends a terminal `done` entry to the token log carrying the `messageId`, and it produces the finished message to **Kafka**, partitioned by `chatId`. It then frees its batch slot immediately. A separate **persister** consumer batch-writes those messages into ScyllaDB. The streaming instance forwards the terminal entry, closes the SSE stream, and the client swaps its live buffer for the canonical message. **Neither of those two writes is redundant, and the GPU is not on the hook for either** — §8 says why.
9. **Failure path — client disconnects.** Nothing happens to the run. It keeps generating, tokens keep landing in the log, the message gets persisted. **A closed socket is not a cancel** (§8).
10. **Failure path — client reconnects.** The browser resends `Last-Event-ID`; whichever instance it lands on replays from that offset and continues live. The user sees a brief pause, not a truncated answer.
11. **Failure path — a streaming instance is redeployed.** It drains, its clients reconnect elsewhere, and no run is affected — because no run state ever lived there (§7).
12. **Failure path — an inference worker dies mid-generation.** Under 50 tokens emitted, requeue the run from scratch. Past that, finalise the partial message and emit `error` with `retryable: true` so the UI can offer regenerate. **Say which side of that line you're on and why** — it's an explicit cost trade, not an oversight.
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

- **The user refreshes.** The connection dies, and with it the only channel the answer was travelling down. The tokens already generated are gone; the ones still coming have nowhere to go.
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

Bolt them together and every routine API deploy severs hundreds of thousands of live connections. Split them and the streaming tier becomes **stateless with respect to runs** — it holds sockets, but every byte it sends comes from the token log, so any instance can serve any run and a drain is just "reconnect somewhere else." **This is the single most practical thing on the page**, and it generalises: *any* tier holding stateful client connections wants to be its own deploy unit, whether the payload is tokens, presence, or collaborative edits.

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

The obvious objection: we just wrote the assistant message durably, so why append a `done` entry to a buffer we're about to expire?

**Because the streaming tier cannot see that write.** It is sitting in a blocking `XREAD` on `run:{runId}` and knows nothing about the run except what arrives on the log — that's the whole point of §8, and it's what lets any instance serve any run. Without an in-band terminator it has exactly two options, and both are bad: block until a timeout fires, so every successful answer ends in a spurious hang; or **poll the run's status, which is 570k polls in flight against the message store forever.** One extra log entry replaces both.

Three things ride on that entry:

- **It makes success distinguishable from failure.** A stream that just stops looks identical to a crashed worker, a severed connection, and a completed answer. The client must be able to tell them apart — an unterminated stream should be retried, a terminated one must not be. *(This is the "treating a closed connection as success" trap, #3 in §13.)*
- **It carries the `messageId`**, which is the handle the client needs to swap its live token buffer for the canonical row. Without it the client has assembled the right text and has no idea what to reconcile it against.
- **It's the signal to close cleanly**, so the streaming instance releases the socket instead of holding it until a read timeout. At 570k concurrent connections, reclaiming them promptly is the difference between ~50 machines and considerably more.

The general shape, worth naming because it recurs: **a log-based fanout needs an explicit end-of-stream marker, because "no more data" and "not yet" are the same observation to a reader.** The durable write is for the *next* request; the log entry is for the request that's still open.

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

**Why Kafka here when §8 rejected it for tokens** — worth pre-empting, because it looks like a contradiction. The rejection was about *granularity*: 570k concurrent short-lived per-run streams is the wrong shape for Kafka's long-lived coarse partitions. **This is a different workload wearing the same word.** One message per completed run, ~57k/sec, on a handful of partitions keyed by `chatId`, durable and ordered — that is precisely what Kafka is for. **Same system, opposite verdict, and the discriminator is granularity rather than throughput.** Being able to say that is better than being consistent for its own sake.

**What it costs, and this is the real trade:** the message is now durable *asynchronously*, so there is a **sub-second window where the run is `done` and the message is not yet queryable.** A client that refetched instantly could miss it. Three things close that, and you should name them rather than hope:

1. **The client already has the text** — it assembled it from tokens — so it renders from its own buffer and reconciles on the next load, by which point the persister is caught up.
2. **The `Run` row is written directly, not through Kafka.** It's tiny and low-volume next to messages, and it makes `GET /runs/{id}` authoritative for "finished, storage catching up."
3. **Keying the topic by `chatId` preserves per-chat ordering**, so turns can never be persisted out of sequence — which is the failure that would actually be visible to a user.

**→ ties to the capacity NFR** (a GPU must never wait on storage) **and to the message-durability NFR**, which is why that row says ~1 s and not ~200 ms.

### Cancel is a signal; a closed socket is not

**Closing the tab is not a stop.** We built this whole mechanism precisely so that a dropped connection doesn't end a run — the user is meant to be able to reopen the chat and find the answer waiting. So cancellation has to be **explicit**: `POST /runs/{id}/cancel` flips the run's status and publishes on a control channel keyed by run id. The inference worker checks that channel between token batches and drops the sequence.

**And it must reach the GPU.** A stop button that only stops rendering leaves a batch slot occupied for the rest of a 30-second generation. At this scale that's the difference between reclaiming capacity and paying for tokens nobody will ever read — **cancellation is a capacity feature wearing a UI costume.** **→ ties to the cost and capacity NFRs.**

---

## 9 · Deep dive — scheduling a GPU pool you cannot autoscale

### What you'd reach for first

Chat Service calls a worker directly, round-robin across the pool. Add workers when it gets busy.

### What breaks

**You cannot add workers.** Not in the ten seconds a spike lasts, and often not this quarter — these are ~72,000 GPUs on multi-year contracts. So the pool is a fixed-size resource, and calling it directly means **no admission control**: when every worker is full, requests either pile up in connection queues until things time out, or get spread across workers so evenly that every generation is slow instead of some being fast. There's no component whose job is to decide *who gets compute and who waits*, so under load the system degrades everywhere at once.

Worse, naive per-request dispatch wastes the hardware even when it *isn't* busy — and the reason is the one piece of model mechanics worth actually understanding, because every scheduling decision below follows from it.

### The mechanical floor — what a weight is and why one request wastes a GPU

*You do not need this in an interview. You need it so the rest of §9 is derived rather than memorised, and so you can answer "why?" one level down without bluffing.*

**A weight is just a number, and the model is a pile of them.** "70 billion parameters" means literally 70 billion numbers, arranged into matrices. Training decides what those numbers are; **after training they are frozen and byte-for-byte identical for every request, forever.** The weights *are* the model — there is nothing else to it.

**Generating text is repeated matrix multiplication against those frozen numbers.** Your text becomes a list of integers (tokens), each token becomes a vector, and that vector is multiplied through every layer's weight matrices in turn. Out the far end comes a score for every word in the vocabulary; pick one, append it to the input, **and run the entire thing again from the top.** That loop is why generation is one token at a time and why a long answer takes ten seconds — there are ~500 full passes through 70 billion numbers in a 500-token reply.

**Now the ratio that decides everything.** The weights sit in the GPU's high-bandwidth memory. The compute units can't do arithmetic on them there — they work out of a tiny on-chip scratchpad that holds nothing like 70 billion numbers. So each pass must **stream the entire weight set through the compute units.** On one H100:

| | One decode step, batch of 1 |
|---|---|
| Weights to move | ~140 GB (70B params at 2 bytes) |
| Time to move them | ~140 GB ÷ ~3.3 TB/s ≈ **40 ms** |
| Arithmetic that enables | 2 FLOPs per weight ≈ 140 GFLOP |
| Time to do that arithmetic | 140 GFLOP ÷ ~1000 TFLOP/s ≈ **0.14 ms** |

**Forty milliseconds of hauling to enable a seventh of a millisecond of math.** The compute units sit idle for ~99.7% of the step. *(Sharding the model across 8 GPUs cuts both numbers by 8 and leaves the ratio untouched — which is what makes it a fact about the hardware rather than about your deployment.)* **That ~300× gap is the entire economic case for batching**, and "memory-bandwidth bound" is just the name for it.

### How batching closes the gap — and why identical weights are the *reason* it works

The intuition that trips people up: *if every request runs the same frozen weights and only the inputs differ, what is actually being shared?* **The inputs are never shared. The trip to fetch the weights is.**

Every layer is `y = x @ W`, where `W` is a frozen weight matrix and `x` is your sequence's current vector:

```
BATCH OF 1  ── matrix × VECTOR ───────────────────────────
   x [1 × 8192]  @  W [8192 × 8192]   →  y [1 × 8192]
   read all of W (memory: 100%) to produce ONE row.

BATCH OF 32 ── matrix × MATRIX ───────────────────────────
   X [32 × 8192] @  W [8192 × 8192]   →  Y [32 × 8192]
       ▲ row 0  = Alice's sequence          ▲ row 0 = Alice's next token
       ▲ row 1  = Bob's sequence            ▲ row 1 = Bob's next token
       ▲ …                                  ▲ …
   read all of W ONCE (memory: still 100%) to produce THIRTY-TWO rows.
```

Same 140 GB moved. Same ~40 ms. **Thirty-two tokens out instead of one.** The math got 32× more expensive, but the math was never the bottleneck — it was 0.14 ms out of 40. You are spending the idle 99.7%.

**And the sequences cannot contaminate each other**, which is the part that feels like it should be a problem and isn't: in a matrix multiply, output row *i* depends only on input row *i*. Alice's tokens are computed from Alice's vector and the shared `W`, full stop. Thirty-two strangers ride the same fetch of the weights and never touch. **They are thirty-two mathematically independent computations that happen to share one trip to memory.**

*(One precision, since the next section leans on it: **attention does mix information across positions — but only within a single sequence**, and each sequence attends against its own private KV cache. Positions talk to each other; sequences never do.)*

**So what *is* per-sequence?** The **KV cache** — the attention state for every token that sequence has seen so far. Weights are shared; this is not, and **it is what actually caps the batch.** At roughly 320 KB per token for a 70B model, a chat carrying 20k tokens of history holds ~6 GB of KV cache *by itself*. An 8-GPU server has ~640 GB of memory, ~140 GB of it weights, so the remaining ~500 GB divided by 6 GB is where **~64 concurrent sequences** comes from. Two consequences worth saying out loud:

- **Batch size is a memory budget, not a tuning knob.** You cannot simply raise it.
- **Long conversations literally consume batch slots.** Every turn of history is KV cache that isn't available to another user — which is why §11's context pruning is a *capacity* lever, not just a cost one.

### Prefill vs decode, from first principles

**Start with the correct instinct: prefill is the more parallelisable half.** That is not a quirk — it is the definition, and it is exactly why prefill is compute-bound while decode is not. But "prefill is the first word" undersells what it does, and the gap is where the confusion lives.

**How a matrix multiply becomes a word, end to end.**

1. **Tokens become vectors by lookup, not multiplication.** The vocabulary is ~128k tokens; the embedding matrix is `[128000 × 8192]`. Token `5432` means "take row 5432" — one vector of 8192 numbers. No math yet.
2. **Every layer maps `[N × 8192] → [N × 8192]`.** Inside a layer, the **MLP** puts each position independently through the big weight matrices — that's the `y = x @ W` from above and it's where nearly all the weights live. **Attention** is the only place positions look at each other.
3. **Causal masking is what makes prefill possible.** Position *i* may only attend to positions ≤ *i*. **So computing all N positions simultaneously gives bit-identical results to having produced them one at a time** — the parallelism is free rather than an approximation. This is the fact your instinct was reaching for.
4. **The last row becomes a word.** After the final layer take row *N*, multiply by the unembedding matrix `[8192 × 128000]` → **128,000 scores, one per vocabulary token**. Softmax them into probabilities, sample one. That is the next word. *"Multiplying produces a word"* resolves to: it produces a score for every possible word, and you pick.

**The thing you were missing: prefill computes all N positions' predictions and throws away all but the last one.**

Position 3 predicts what follows position 3 — but you already *know* that; it's word 4 of the prompt. Only position *N*'s prediction is new information. So a 2,000-token prefill runs 2,000 positions through 80 layers and discards 1,999 of the answers. *(Training keeps all of them, which is why training is so much more efficient per FLOP than inference — a nice aside if an interviewer pulls the thread.)*

**So what is prefill actually for? The KV cache.** At every layer, every one of the N positions produces a key and a value vector, and those get **stored**. That store is the ~320 KB/token from the batching section. **Prefill's real product is that cache; the first token is a by-product.** Which is precisely why decode never re-reads the prompt — the prompt is already sitting there as cached K/V.

**And now decode.** One new token in, so a `[1 × 8192]` vector: through 80 layers, attending against the N cached positions and matrix-multiplying against the full weight set, out to logits, sample, **append its own K/V to the cache**, repeat.

**Why decode cannot be parallelised within one request — and it genuinely cannot.** Token *N+2* depends on token *N+1* having been *sampled*. There is no vector to feed in until the previous step chose one. It is a true serial dependency, not an engineering shortcoming. **Prefill parallelises across positions; decode has only one position, so its only available parallelism is across *other users*.** That single sentence is why batching is a decode optimisation and barely matters for prefill.

**The asymmetry in numbers**, for a 2,000-token prompt and a 500-token answer on a 70B model:

| | Prefill (2,000 tokens) | Decode (500 tokens) |
|---|---|---|
| Forward passes | **1** | **500, strictly sequential** |
| Weights moved | 140 GB, **once** | 140 GB × 500 = **~70 TB** |
| Arithmetic | 2,000 × 140 GFLOP ≈ **280 TFLOP** | 500 × 140 GFLOP ≈ **70 TFLOP** |
| **Arithmetic intensity** | **~2,000 FLOP/byte** | **~1 FLOP/byte** |
| An H100's own ratio is ~300 FLOP/byte | Well above → **compute-bound** | Far below → **memory-bound** |

**Read the last two rows out loud in an interview and you have derived the whole thing:** prefill does **four times the arithmetic** of decode while moving **five hundred times less memory**. Same model, same weights, same operation — and they land on opposite sides of the hardware's break-even point. That is why TTFT and inter-token latency are separate problems with separate fixes, why context length hurts TTFT specifically, and why a batch is the only lever decode has.

**One payoff worth naming, because it now explains itself:** speculative decoding works by **turning decode back into prefill.** A small draft model guesses the next four tokens; with four candidate positions in hand the large model can verify all four in a **single** forward pass — a matrix-*matrix* multiply instead of four starved matrix-vector ones. It buys back parallelism that the serial dependency had taken away.

### What replaces it

**A queue in front of a fixed pool, and continuous batching inside each worker.**

- **Batching pays for the haul** — the mechanism above. One fetch of the weights advances every sequence in the batch by one token, so throughput scales with batch size while wall-clock barely moves.
- **"Continuous" is the scheduling half, and it's the part that's actually a design decision.** *Static* batching forms a batch of 64, runs it to completion, and only then starts the next — so a one-line reply finishes in 10 steps and its slot **sits empty for the remaining 1,990** while a 2,000-token essay grinds on beside it. The batch decays toward one active sequence, which is exactly the starved case you built the batch to avoid. **Continuous batching re-forms the batch every single decode step**: a finished sequence is evicted the moment it emits its stop token and a queued one takes the slot on the next step. Utilisation stays flat instead of sawtoothing. *(vLLM and TGI are the production implementations; naming one is fine, but the mechanism is the point.)*
- **The wrinkle worth volunteering:** a joining sequence needs its prefill done, and prefill is a big compute-bound burst (see above). Run it as one step and **every other sequence in the batch stalls for it** — one user pasting a 30k-token document adds a visible hitch to sixty-three other people's inter-token latency. The fix is **chunked prefill**: split the newcomer's prompt across several steps and interleave it with decode. **This is the concrete mechanism behind "one huge prompt degrades everyone," which is why §10 meters tokens rather than requests.**
- **Prefill and decode are different workloads** — derived above from the same matrix multiply. **Prefill** is compute-bound and scales with input length; it is essentially all of your TTFT. **Decode** is memory-bandwidth bound and scales with output length. **The consequence: every token of context you add is paid at exactly the moment the user is staring at a blank screen** — and, because KV cache caps the batch, it's also paid by everyone else in the form of a slot. That's why §11 is a capacity dive as much as a cost dive.
- **Speculative decoding** — derived above: a draft model's guesses give the large model several positions at once, converting a starved matrix-vector step back into a matrix-matrix one. Roughly 2× on decode for identical output, and it works especially well on code and boilerplate because they're highly predictable. **An optimisation inside the worker, not a change to anything above it.**
- **Admission control at the door.** When queue depth exceeds what the pool can drain within the target wait, reject *new* runs with a clear, retryable state. **Never kill an in-flight run** — it has already consumed GPU-seconds, and killing it converts spent money into zero value. Shedding at the door is the only kind of shedding that saves anything.
- **Route by KV-cache affinity where you can.** A follow-up turn in a chat shares almost all of its prefix with the previous turn; land it on the worker that still has that prefix cached and you skip most of prefill. Best-effort — a worker can be full — and worth naming as a routing *preference* rather than a rule.

### What it costs

Queueing is added latency, and it's the honest trade: **under load the free tier waits, and the wait is visible.** You also now operate a scheduler, and a scheduler is a stateful component that can become its own bottleneck and needs its own failover. And KV-affinity routing is in tension with load balancing — sometimes the warm worker is the wrong worker, and you take the prefill hit rather than the queue.

---

## 10 · Deep dive — fairness across tiers, and why requests-per-minute is the wrong unit

### What you'd reach for first

A rate limit: N requests per minute per user, maybe a higher N for paid tiers.

### What breaks

**A request is not a unit of cost.** One user pasting a 30,000-token document and asking for a long summary consumes more GPU-seconds than a hundred users asking one-line questions. A requests-per-minute cap prices those identically, which means it fails at both jobs at once: it does not stop the expensive user from monopolising the pool, and it *does* throttle the cheap user who's doing nothing wrong. **The limiter is measuring the wrong thing, so no value of N is correct.**

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

**2. Summarise asynchronously, never in the send path.** When a chat crosses a token threshold, a background job asks a *small, cheap* model to fold the oldest turns into the existing summary, and caches the result on the chat. Doing this inline would add a second model call to the moment the user is waiting, which trades the cost problem for a worse latency problem. **Update it incrementally** — fold new turns into the previous summary rather than re-summarising the whole transcript — or the summariser's own cost grows quadratically with conversation length, which is the failure mode of the naive version wearing a disguise.

**3. Order the prompt static → dynamic, and know exactly why.** Inference caches KV state by prefix: an identical leading span skips prefill for that span. The ordering above is stable-prefix-first, so turn N's system prompt and summary are already warm and only the tail needs prefilling. **Put anything volatile early — a timestamp, the user's name, a retrieved snippet — and you invalidate the entire prefix on every single turn.** Same tokens, same bill on paper, several hundred milliseconds of TTFT difference. **It is the highest ratio of impact to effort on this page and it is invisible unless you know to look.** **→ ties directly to the TTFT NFR.**

### What it costs

**Summarisation loses detail, and it loses it silently.** Something in turn 3 that the summary dropped is gone, and the assistant will confidently proceed without it — this is the real cost and it's a product decision, not an engineering one. Mitigations to name: keep more verbatim turns, tune the threshold, or (the next step up, and the bridge to the RAG variant in §15) index the full transcript and retrieve from it semantically instead of summarising, which trades a summariser for a retriever. And the summary is now a cached derived value with an invalidation story you own.

---

## 12 · Data model, sharding, and storage decisions

**Partition key: `chatId`.** Every access pattern is per-chat — load a chat's messages, append to a chat, stream a chat's run — so co-locating a chat's rows makes the hot path a single-partition range scan. Sharding by `userId` looks tempting for the sidebar, but it makes one heavy user's data one shard's problem and gives nothing to the query that actually dominates.

**Is there a hot shard?** No, and that's worth saying out loud. **Every write goes to exactly one chat owned by exactly one user, so this workload has no write contention at all** — there is no celebrity tweet, no stadium onsale, no fifty-thousand-member channel.

**And no time bucket in the key, which is the contrast with Discord.** That page partitions on `(channel_id, bucket)` because a channel is unbounded and permanently hot. **A chat is neither: it has one writer taking turns with itself, and it stops being usable somewhere in the low hundreds of turns**, so `chatId` alone is a partition of a few hundred small rows and will never need splitting. Same data shape, different key, and the reason is a product fact rather than a database fact. *(This is the whole value of having both pages: the storage layer looks identical and the correct key isn't.)*

### The store, which is a genuine three-way debate

**The data model does not discriminate here — say that first.** Partition on the chat, cluster on time descending, range-scan the newest N. Cassandra, ScyllaDB, DynamoDB, and Bigtable all express that identically, so re-deriving the key for each one is wasted clock. **What actually decides it is the storage bill at petabyte scale and whether you have a team that runs a database.**

| Option | Fit | Why it wins or loses |
|---|---|---|
| **Postgres** (even + Citus) | Models it perfectly | **Rejected on operations.** At 1.8 PB/yr and ~114k message writes/sec I'd be committing the team to hand-managed sharding, rebalancing, and a vacuum story forever. That's an ongoing tax paid in headcount, and none of the relational power I'd be buying is used on this path — there are no joins in "give me the last 50 messages of one chat" |
| **DynamoDB** | Fits exactly. PK `chatId`, SK `createdAt#id` | **The right answer at a tenth of this scale, and the right answer at any scale if I don't have a wide-column team.** Zero operations. It loses here on price: ~1.8 PB of *year one* alone is millions a year in storage, it compounds every year against append-only data, and there's no lever to pull because the bill is the product |
| **ScyllaDB / Cassandra** | Fits exactly. `PRIMARY KEY ((chat_id), created_at, message_id)`, clustering DESC | **Chosen.** LSM storage makes an append the cheapest write there is, a chat is one narrow sequential scan, and self-hosting a petabyte is a hardware bill rather than a per-GB rate. Scylla over Cassandra specifically to avoid JVM GC pauses in the p99, which is the reported failure at this size — **the same call the Discord page makes, for the same reason** |
| **Bigtable / HBase** | Fits exactly | A fine answer, and mostly a cloud-allegiance decision rather than a technical one. Say so instead of pretending there's a deep distinction |

**The sentence that carries it:** *"All four model this identically, so I'm not choosing on the data model — I'm choosing on who pays for a petabyte. Managed storage at this volume is a bill that compounds annually against data nobody reads, and at 200 M DAU I have the team to run Scylla, so I'd take the operational cost and keep the money. Flip that last clause and DynamoDB is immediately the better answer — that's the specific thing that would change my mind."*

**What the choice costs, volunteered:** repair, compaction tuning, and node replacement become someone's job; you get no ad-hoc queries, so every access pattern needs a table designed for it up front; and there are no transactions across partitions, which is fine here because nothing in this product needs one.

| Component | Access pattern | Durability | Choice | The debate, in one sentence |
|---|---|---|---|---|
| **Messages** | Range scan by `chatId`, newest first; append-only; ~1.8 PB/yr | Must not lose an acked write | **ScyllaDB**, `PRIMARY KEY ((chat_id), created_at, message_id)`, clustering DESC | The three-way debate above — chosen on the petabyte bill, not the data model |
| **Runs** | Point read/write by `runId` from three different services | High, but small and short-lived | **ScyllaDB**, separate table, `PRIMARY KEY (run_id)` | "It gets its own table rather than living under `chat_id`, because the streaming tier and the cancel endpoint both arrive holding a `runId` and nothing else. In a wide-column store the answer to a second access pattern is a second table, not a secondary index" |
| **Chat sidebar** | Newest-first list per user, ~50 rows | High | **ScyllaDB**, `chats_by_user`, `PRIMARY KEY ((user_id), last_message_at, chat_id)` DESC | "Query-driven denormalisation — the wide-column answer to a second access pattern. Bumping `last_message_at` is a delete-plus-insert of a mutable clustering key, normally an anti-pattern; **it's fine at ~200 bytes across a partition of dozens of rows**, and if the tombstones ever bit I'd move the ordering into a Redis sorted set per user and keep Scylla for the rows" |
| **Token log** | Append + replay-from-offset, 10-min TTL | **None, deliberately** | **Redis Streams**, `run:{runId}`, `EXPIRE` after `done` | The §8 debate — chosen for replay-from-offset, which is what makes reconnect free |
| Queue + scheduler state | Enqueue/dequeue by tier, ~57k/sec | Low — a lost queued run is retryable | **Redis sorted sets** per tier, score = enqueue time adjusted by aging | "Kafka is durable and ordered but I want priority and aging, and reordering is exactly what a log doesn't do. SQS has no priority. A sorted set is a priority queue with a score I control" |
| Quota counters | Read-modify-write per send | None | **Redis**, sliding window, **fails open** | "A quota check is not worth an outage. If it's down I lose metering for a minute; §9's admission control still protects the pool" |
| Cold chats | Rare full-chat reads | High, cheap | **S3**, one object per chat, pointer row retained in `chats_by_user` | See the lifecycle below |
| **Message persistence buffer** | Produce once per finished run (~57k/s), consume in batches | **High — this is the durability path** | **Kafka**, topic `messages`, `key = chatId` | "It exists so a GPU never waits on a database, and it's keyed by chat so turns can't persist out of order. Rejected for token fanout in §8 on granularity, and correct here for exactly that reason — one durable message per run is Kafka's shape; 570k ephemeral per-run streams is not" |
| Run/usage ledger | Append-heavy, analytical | High | **Object storage + a warehouse** | "This is billing, capacity planning, and abuse detection — columnar batch access, not a serving store. It should never share a database with the send path" |

### Data lifecycle, because append-only at 5 TB/day is a plan or it's a problem

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
6. **A connection registry so workers can push to the right server.** Rebuilds the coupling a log exists to remove, as a distributed-state problem.
7. **Pub/Sub instead of a replayable log.** Reconnect gets whatever arrives next, and the gap is silently lost tokens.
8. **Rate-limiting requests instead of tokens.** A request is not a unit of cost; no value of N is correct.
9. **Strict priority between tiers.** Free traffic starves completely the first time paid demand exceeds capacity.
10. **Killing in-flight runs to shed load.** Converts spent GPU-seconds into zero value. Shed at the door only.
11. **Autoscaling the GPU pool.** You cannot buy 9,000 servers during a spike. It's a scheduling problem, not a capacity problem.
12. **Volatile content early in the prompt.** Destroys prefix caching and hundreds of milliseconds of TTFT for free.
13. **Replaying the full transcript every turn.** Cost and TTFT grow with conversation length, and it hits a hard ceiling.
14. **Summarising synchronously in the send path.** Trades a cost problem for a worse latency problem.
15. **Offset pagination on messages.** A growing list makes offsets skip and repeat, and deep offsets are slow.
16. **No idempotency key on send.** A retried submit double-charges a scarce resource and streams two answers into one bubble.
17. **The GPU worker writing to the database itself.** Couples the most expensive resource in the system to the availability of the cheapest, so a storage p99 spike becomes a capacity outage.
18. **Assuming a Redis outage loses the generation.** It loses the live *view*. The answer survives — provided the worker never blocks on `XADD` and durability doesn't route through Redis.
19. **Unbounded token-log memory.** A Redis OOM takes out every live stream simultaneously. Bound the buffer, TTL the key.
20. **No data lifecycle.** 1.8 PB/year of append-only chat with no tiering is a bill that compounds.
21. **Pricing your own serving cost off published API rates.** Overstates it by more than 10×; the unit is GPU-seconds.
22. **Optimising total completion time instead of TTFT.** Users tolerate ten seconds of streaming and not three seconds of blank screen.

**Interview-performance traps** → `00-interview-mechanics.md` §6. The two specific to this problem:

23. **Spending fifteen minutes inside the model.** Attention, quantisation, and fine-tuning are a different interview. The model is a black box with a latency, a cost, and a capacity; the engineering is everything around it.
24. **Designing the message schema first.** It's the most familiar part and the least interesting, and the clock it eats comes straight out of §9 and §10.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 606" role="img" aria-label="ChatGPT five-minute skeleton. A numbers banner, then the three tiers, the Run entity, the two-call submit and stream split, SSE, the Redis stream path, the two cheap writes on completion, cancellation, shedding, prefill versus decode, metering, context assembly and the storage layout.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="92.5">57k generations/sec · 570 k concurrent streams · ~72 k GPUs · ~$3.5 M/day · 1.8 PB/yr</text>
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
  <text class="dg-s dg-c" x="500" y="439.5">never kill work in flight</text>
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
2. **`Run` is an entity.** Queued → running → done / cancelled / failed. Everything hard is an operation on it.
3. **Submit and stream are two calls.** `POST /messages` returns `{ userMessageId, runId }` immediately; `GET /runs/{id}/stream` is SSE. Optimistic echo hides the round trip.
4. **SSE over WebSocket** — one-way tokens, free reconnect via `Last-Event-ID`; cancel is a separate POST and that's the price.
5. **Inference worker → Redis Stream `run:{runId}` → streaming tier.** Neither side knows the other. **SSE event id = Redis entry id**, so reconnect is a replay from an offset.
6. **On completion, two cheap writes and no database call**: terminal entry to the log (the user sees it now) + the message to **Kafka keyed by `chatId`**, which a persister batch-writes to Scylla. **A GPU never waits on storage.**
7. **A closed socket is not a cancel.** Cancel is explicit and must reach the GPU.
8. **Fixed GPU pool + priority queue + continuous batching.** You cannot autoscale it. Shed at the door, never kill in-flight.
9. **Prefill is compute-bound (that's your TTFT); decode is bandwidth-bound.** Every context token is paid while the user watches a blank screen.
10. **Meter tokens, not requests**, per user; **weighted queues with aging**, not strict priority, per tier. Fairness and priority are different mechanisms.
11. **Context: system prompt → rolling summary → last K turns → new prompt.** Async incremental summariser, stable prefix first for the KV cache.
12. **ScyllaDB partitioned on `chatId`** (no time bucket — unlike Discord, a chat has one writer and is bounded), a second table for the sidebar, **hot/warm/cold at 30 and 180 days** with whole chats to S3.
13. **Numbers to have in the margin:** 57k gen/sec · **570k concurrent streams** · ~72k GPUs · **~$3.5M/day** · 1.8 PB/yr.

---

## 15 · Variants — what actually changes

**The axis that governs this family: what does the model need besides the conversation, and who is allowed to see it?** As you move down, the hard problem migrates from *the run lifecycle* to *authorization and termination* — but §7 and §8 survive every row unchanged, which is why this page is the foundation for the rest.

| Variant | What it adds | What changes |
|---|---|---|
| **This page — pure conversation** | Nothing | Run lifecycle, scheduling, and context cost are the whole design |
| **Chat over private documents** (internal assistant, support bot) | **Retrieval, and permissions** | Retrieval quality now bounds answer quality, and the model must never receive a chunk the asker can't read — **filter before prompt assembly, never after generation, and never cache an answer under a key that omits permission context.** The run lifecycle is unchanged; the hard invariant moves from "don't lose the run" to "don't leak the document" |
| **Editing or branching a message** | A conversation is a tree, not a list | Messages get a `parentId`; the sidebar shows a path through the tree. Cheap on the read side, and it makes prefix caching *better* — siblings share a prefix by construction |
| **Multimodal input** | Images and audio in | Tokenisation changes and inputs get much larger, so **prefill dominates and TTFT degrades**. Upload becomes its own async pipeline; the streaming half is untouched |
| **Tool calling / agent runs** | The model acts | A run becomes **multi-step with unpredictable duration**, so the token log carries step events, not just tokens. New problems: **authorization per tool call**, idempotency on retried actions, **termination conditions**, and cost explosion via loops. Everything on this page still applies and is no longer sufficient |
| **Inline code completion** | A ~200 ms ceiling | **Too tight for a queue, a large model, or retrieval.** Small specialised model, aggressive suppression, cancellation as the dominant cost lever. A different architecture — see the Cursor Tab page, which is this row worked out in full |
| **Batch / offline generation** | No user waiting | **The latency requirement vanishes entirely.** No streaming, no TTFT, no run lifecycle — batch the pool to ~100% utilisation and optimise purely for throughput per GPU-hour. The inverse of this page |

**The general lesson:** pure conversation is the *simplest* point in this family and the only one where the run lifecycle is the whole story. Everything below it inherits §7 through §11 intact and adds either an authorization problem or a termination problem on top.
