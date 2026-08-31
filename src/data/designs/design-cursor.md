# Design Cursor — AI Coding Assistant (Tab Completion)

## The question

> *"Design Cursor's Tab completion. As a developer types, the editor predicts the rest of the edit and shows it inline in grey — Tab accepts it, anything else dismisses it."*

**The product.** Cursor is an AI-enabled code editor with several distinct AI surfaces: chat on the side, inline edit on a selection, an agent that goes off and does a task — and Tab. **This question is about Tab only.** Tab is the greyed-out "ghost text" that appears ahead of your cursor as you type, predicting the rest of the line, the rest of the block, or the change you were clearly about to make. You press Tab and it's inserted; you type anything else and it disappears.

It fires constantly — potentially on every keystroke — and the great majority of what it produces is never looked at, because the developer kept typing. Meanwhile the code it's predicting from is on the developer's own machine, and for a lot of companies it is not allowed to leave the building.

**What a working system delivers**

- The suggestion is on screen before you've typed past the point where it would have been useful.
- It knows about the rest of the codebase — a function you defined in another file, the conventions of the project — not just the twenty lines around the cursor.
- A wrong suggestion costs one keystroke to dismiss and nothing else.
- A suggestion never references code the developer just renamed a second ago.
- Enterprise code doesn't leave the network when the customer says it can't.

**Why this gets asked.** The interactive latency budget — a couple of hundred milliseconds, because the user is still typing — is small enough to rule out the retrieve-then-rerank-then-large-model pipeline that everyone reaches for. And a system that discards most of its own work by design ends up organized around not paying for the part it throws away.

---

**Archetype:** ultra-low-latency inference in the interaction loop, over a local, constantly-mutating corpus.
**Cousins that reuse ~70% of this page:** GitHub Copilot, Windsurf, Zed's AI, JetBrains AI, any inline completion product. Also **any inference that sits inside a keystroke loop** rather than behind a submit button.

**What's actually being graded:** whether you notice that **the latency budget destroys the standard RAG architecture** and rebuild around that. ~200ms end to end means no reranker, no cross-encoder, no large model, and no round trip you don't absolutely need. Candidates who describe a retrieval pipeline here have answered the chat question instead of the Tab question. The second signal is that you know **most inference in this product is wasted by design** — the user types on and discards it — so the whole system is organized around *predicting whether to run at all* and *not paying for the ones you cancel.*

**Contrast to have ready:** *A RAG assistant is a request-response product with a ten-second budget where retrieval quality is everything. Tab is a keystroke-loop product with a 200ms budget where **cancellation, caching, and knowing when not to fire** are everything. The model is smaller, the context is local, and the acceptance rate — not the answer quality — is the metric.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "Cursor is really four products with different budgets — Tab completion at a couple hundred milliseconds, inline edit at a few seconds, chat at ten-plus, and agent mode at minutes. They share an indexing layer and almost nothing else, so I'd like to scope to **Tab**, because it's the one where the latency constraint actually forces the architecture. At 200ms I can't do retrieval-then-rerank-then-large-model; I need context assembled locally from editor signals, a small fast model, and aggressive caching. Two things dominate: **most completions are never accepted**, so I'm designing to avoid paying for them, and **the codebase is on the user's machine**, so privacy and sync shape the indexing layer. I'll go deep on the latency budget and context assembly."

**Why open this way:** naming the four surfaces and picking one demonstrates you understand the product rather than the category, and it pre-empts the interviewer steering you into a generic RAG answer.

---

## 1 · Functional requirements

1. **Predict the next edit** as the user types, and render it inline as a ghost-text suggestion.
2. **Accept on Tab**, dismiss on any other keystroke.
3. **Suggestions are aware of the wider codebase**, not just the current file.

**Out of scope (say them):** chat, agent mode, terminal integration, code review, the editor itself.

**Below the line, likely follow-ups:** multi-line and multi-location edits (Cursor's actual differentiator — §11), the apply/diff problem for the edit surfaces (§15), enterprise on-prem deployment.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **End-to-end latency** | **p50 < 150ms, p95 < 300ms** | Above ~300ms the suggestion arrives after the user has typed past it. **This is the requirement that determines every other decision** |
| Acceptance rate | 20–35% is realistic and good | The product metric. Not "quality" — *accepted* completions |
| Correctness | **No hard invariant** | Uniquely on this page: a wrong suggestion costs one keystroke to dismiss. This buys enormous architectural freedom |
| Privacy | **Code must not be retained; enterprise mode must not let it leave the network** | The constraint that actually blocks enterprise deals |
| Freshness | **Index reflects edits within a keystroke or two** | Suggesting a function the user just renamed is the most visible possible failure |
| Availability | Degrade to nothing, silently | If the service is down, the editor still edits. **Never block the keystroke path** |
| Scale | ~1M DAU, but see §3 — the interesting number is requests *per user* | Concurrency is driven by typing, not by user count |

**The sentence that earns the point:** *"There's no correctness invariant here, which is unusual — a bad suggestion costs a keystroke. That means I can be aggressive about caching, speculation, and using a small model, in ways I'd never accept on a transactional system."*

---

## 3 · Numbers that reframe the problem

**The request volume is much larger than DAU suggests**

- A developer types ~200 chars/min while actively coding, and a debounced trigger fires perhaps **20–40 times/minute.**
- 1M DAU × ~2 active hours × ~30/min ≈ **3.6B requests/day ≈ 40k QPS average, 100k+ peak.**
- **This is a genuinely high-QPS inference workload** — the opposite of the RAG assistant's 2 QPS. Say the comparison out loud; it's the reason the two products share almost no architecture.

**Most of that work is thrown away**

- At a ~25% acceptance rate, **75% of completions are never used.** Add the ones cancelled mid-flight by the next keystroke and well over 80% of issued inference produces nothing.
- **This is the central economic fact of the product.** Everything in §9 and §10 follows: predicting *whether to fire*, cancelling fast, and caching so a re-fire is free.

**The latency budget — and why it forbids the RAG architecture**

| Stage | Budget | Note |
|---|---|---|
| Debounce | ~30ms | Not latency exactly — a deliberate wait to see if more keystrokes arrive |
| Context assembly | **~10ms** | **Local, in the editor.** No network, no vector search |
| Network round trip | 20–60ms | Regional routing is doing real work here |
| Prefill | ~30ms | Small model, few thousand tokens |
| Decode | ~40ms | ~30 tokens at high throughput |
| Render | ~5ms | |
| **Total** | **~150–180ms** | |

**Now price the RAG page's pipeline against that budget:** embedding the query ~20ms, ANN ~30ms, cross-encoder rerank ~100ms, large-model prefill ~350ms. **The rerank alone eats half the budget and the model prefill blows through it twice over.** That comparison is the single most useful thing to be able to state in this interview — it's a quantitative reason for a structural decision.

**Cost**

- ~30 output tokens on a small model ≈ **$0.0001–0.0005/request.** Trivially cheap per request; ×3.6B/day it's a **seven-figure annual GPU bill**, and ~80% of it is spent on completions nobody used.
- **Therefore the cheapest optimization is not firing.** A filter that suppresses 30% of low-value requests is worth more than any inference optimization on this page.

---

## 4 · Core entities

- **Workspace** — id, user_id, root path, index state
- **File** — path, `content_hash`, language, last_modified
- **Chunk** — file, byte range, **AST node type**, symbol name, embedding *(server-side only in indexed mode)*
- **MerkleNode** — path → hash, for sync (§8)
- **CompletionRequest** — prefix, suffix, assembled context, cursor position, `request_id`
- **CompletionEvent** — request_id, shown, accepted, chars_accepted, latency, model_version
- **EditHistory** — the user's recent edits, in order *(the highest-signal context source — §7)*

**Load-bearing details:**

- **`Chunk.ast_node_type`** — code chunks on syntactic boundaries (function, class, method), never on a fixed token count. A chunk that ends mid-function is nearly useless as context, and unlike prose there's a real grammar to split on. **Use it.**
- **`EditHistory` is a first-class entity, not telemetry.** What the user changed in the last 60 seconds predicts what they're about to change next, better than anything semantic. Cursor's Tab model is trained specifically on edit sequences rather than static file snapshots.
- **`CompletionEvent.accepted`** — the entire product metric and the training signal. Everything else on the page is instrumentation around this field.
- **The prefix/suffix split** — code completion is **fill-in-the-middle**, not left-to-right continuation. The model needs what comes *after* the cursor too, which is a different prompt format (FIM tokens) and a different training objective from a chat model. Naming FIM is a strong, cheap signal.

---

## 5 · API

```
POST /v1/completions                      → streamed or single-shot
  body: {
    requestId, prefix, suffix, filePath, language,
    context: [{ path, snippet, reason }],   // assembled client-side
    recentEdits: [...]
  }
  header: Idempotency-Key: {requestId}

DELETE /v1/completions/{requestId}         → cancel (or just abort the HTTP request)

POST /v1/events                            → batched: shown / accepted / dismissed

// indexing (separate lifecycle)
POST /v1/workspaces/{id}/sync              → { missingHashes: [...] }
POST /v1/workspaces/{id}/chunks            → upload only what's missing
```

**Decisions to narrate, unprompted:**

- **The client assembles the context, not the server.** The editor already knows the open tabs, the cursor position, the LSP symbol table, and the recent edits. Shipping that up is one round trip; asking the server to figure it out is several. **This is the inversion that makes the budget work** — and it's the opposite of the RAG design, where the server owns retrieval entirely.
- **`requestId` is generated per keystroke-trigger** and is how cancellation and dedupe both work. In-flight request superseded → abort it; identical context seen before → serve from cache.
- **Events are batched and fire-and-forget.** Telemetry must never sit in the latency path.
- **No response is a valid response.** If the model has nothing good, return empty rather than something plausible. **A bad suggestion is worse than none**, because it costs a dismiss keystroke *and* trains the user to ignore ghost text.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 776" role="img" aria-label="Cursor Tab architecture. A client tier holding the editor, a context assembler running on a worker thread, a local completion cache, ghost-text decorations and a file watcher. An edge tier with a regional edge doing cached auth and rate limiting, and an auth cache. An inference tier with a regional router, a GPU worker fleet running a small FIM model with continuous batching, a prefix KV cache in GPU memory, and a shared result cache in Redis holding hashed contexts and no user code. Below, an asynchronous indexing tier: index API, AST chunker, embedding service, a Merkle store and a vector index. Below that, a telemetry tier: event collector, a Kafka queue, and a warehouse.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Three paths leave the editor: one synchronous, budgeted at 200 ms; two asynchronous and off the hot path.</text>
  <rect class="dg-group" x="20" y="86" width="210" height="332" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">CLIENT — THE EDITOR</text>
  <rect class="dg-box" x="35" y="118" width="180" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="125" y="134.5">Editor / extension host</text>
  <text class="dg-s dg-c" x="125" y="150.5">HTTPS, abortable</text>
  <rect class="dg-box" x="35" y="170" width="180" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="125" y="194.5">Context assembler</text>
  <text class="dg-s dg-c" x="125" y="210.5">worker thread, ~10 ms</text>
  <path class="dg-box" d="M 35,245 L 35,285 A 90,7 0 0 0 215,285 L 215,245 A 90,7 0 0 0 35,245 Z"></path>
  <path class="dg-box" d="M 35,245 A 90,7 0 0 0 215,245" style="fill:none"></path>
  <text class="dg-t dg-c" x="125" y="265">Completion cache</text>
  <text class="dg-s dg-c" x="125" y="281">LRU · hash(context)</text>
  <rect class="dg-box" x="35" y="304" width="180" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="125" y="328.5">Ghost-text decorations</text>
  <rect class="dg-box" x="35" y="356" width="180" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="125" y="377.5">File watcher</text>
  <text class="dg-s dg-c" x="125" y="393.5">Merkle tree · .cursorignore</text>
  <path class="dg-line" d="M 125,158 L 125,162"></path>
  <path class="dg-head" d="M 120,162 L 130,162 L 125,170 Z"></path>
  <path class="dg-line" d="M 125,226 L 125,238"></path>
  <path class="dg-line" d="M 125,292 L 125,304"></path>
  <rect class="dg-group" x="340" y="86" width="160" height="178" rx="12"></rect>
  <text class="dg-group-t" x="356" y="108">EDGE</text>
  <rect class="dg-box" x="354" y="118" width="132" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="420" y="134.5">Regional edge</text>
  <text class="dg-s dg-c" x="420" y="150.5">POST /completion</text>
  <text class="dg-s dg-c" x="420" y="166.5">auth + rate limit</text>
  <text class="dg-s dg-c" x="420" y="182.5">request coalescing</text>
  <path class="dg-box" d="M 354,209 L 354,245 A 66,7 0 0 0 486,245 L 486,209 A 66,7 0 0 0 354,209 Z"></path>
  <path class="dg-box" d="M 354,209 A 66,7 0 0 0 486,209" style="fill:none"></path>
  <text class="dg-t dg-c" x="420" y="227">Auth cache</text>
  <text class="dg-s dg-c" x="420" y="243">at the edge</text>
  <rect class="dg-group" x="610" y="86" width="370" height="262" rx="12"></rect>
  <text class="dg-group-t" x="626" y="108">INFERENCE</text>
  <rect class="dg-box" x="625" y="118" width="150" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="700" y="146.5">Router</text>
  <text class="dg-s dg-c" x="700" y="162.5">by region</text>
  <path class="dg-box" d="M 795,125 L 795,175 A 85,7 0 0 0 965,175 L 965,125 A 85,7 0 0 0 795,125 Z"></path>
  <path class="dg-box" d="M 795,125 A 85,7 0 0 0 965,125" style="fill:none"></path>
  <text class="dg-t dg-c" x="880" y="150">Prefix KV cache</text>
  <text class="dg-s dg-c" x="880" y="166">in HBM</text>
  <rect class="dg-box" x="625" y="194" width="340" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="795" y="218.5">Inference workers — GPU</text>
  <text class="dg-s dg-c" x="795" y="234.5">small FIM model · continuous batching</text>
  <text class="dg-s dg-c" x="795" y="250.5">speculative decoding · single-shot</text>
  <path class="dg-box" d="M 625,285 L 625,329 A 170,7 0 0 0 965,329 L 965,285 A 170,7 0 0 0 625,285 Z"></path>
  <path class="dg-box" d="M 625,285 A 170,7 0 0 0 965,285" style="fill:none"></path>
  <text class="dg-t dg-c" x="795" y="307">Shared result cache</text>
  <text class="dg-s dg-c" x="795" y="323">Redis · hashed contexts, no user code</text>
  <path class="dg-line" d="M 700,182 L 700,186"></path>
  <path class="dg-head" d="M 695,186 L 705,186 L 700,194 Z"></path>
  <path class="dg-line" d="M 880,194 L 880,182"></path>
  <path class="dg-line" d="M 795,266 L 795,278"></path>
  <path class="dg-line" d="M 230,140 L 346,140"></path>
  <path class="dg-head" d="M 346,145 L 346,135 L 354,140 Z"></path>
  <text class="dg-lbl dg-c" x="292" y="132">completion request</text>
  <path class="dg-line" d="M 354,166 L 238,166"></path>
  <path class="dg-head" d="M 238,161 L 238,171 L 230,166 Z"></path>
  <text class="dg-lbl dg-c" x="292" y="190">ghost text</text>
  <path class="dg-line" d="M 486,140 L 617,140"></path>
  <path class="dg-head" d="M 617,145 L 617,135 L 625,140 Z"></path>
  <text class="dg-lbl dg-c" x="555" y="132">routed by region</text>
  <path class="dg-line" d="M 625,166 L 494,166"></path>
  <path class="dg-head" d="M 494,161 L 494,171 L 486,166 Z"></path>
  <text class="dg-lbl dg-c" x="555" y="190">tokens</text>
  <rect class="dg-group" x="250" y="430" width="730" height="180" rx="12"></rect>
  <text class="dg-group-t" x="266" y="452">INDEXING — ASYNCHRONOUS, OFF THE HOT PATH</text>
  <rect class="dg-box" x="268" y="462" width="170" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="353" y="478.5">Index API</text>
  <text class="dg-s dg-c" x="353" y="494.5">POST /index</text>
  <text class="dg-s dg-c" x="353" y="510.5">Merkle diff</text>
  <rect class="dg-box" x="468" y="462" width="180" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="558" y="486.5">AST chunker</text>
  <text class="dg-s dg-c" x="558" y="502.5">chunk on syntax bounds</text>
  <rect class="dg-box" x="678" y="462" width="180" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="768" y="494.5">Embedding service</text>
  <path class="dg-box" d="M 268,547 L 268,589 A 85,7 0 0 0 438,589 L 438,547 A 85,7 0 0 0 268,547 Z"></path>
  <path class="dg-box" d="M 268,547 A 85,7 0 0 0 438,547" style="fill:none"></path>
  <text class="dg-t dg-c" x="353" y="568">Merkle store</text>
  <text class="dg-s dg-c" x="353" y="584">per repo, server-side</text>
  <path class="dg-box" d="M 678,547 L 678,589 A 90,7 0 0 0 858,589 L 858,547 A 90,7 0 0 0 678,547 Z"></path>
  <path class="dg-box" d="M 678,547 A 90,7 0 0 0 858,547" style="fill:none"></path>
  <text class="dg-t dg-c" x="768" y="568">Vector index</text>
  <text class="dg-s dg-c" x="768" y="584">keyed by content hash</text>
  <path class="dg-line" d="M 438,490 L 460,490"></path>
  <path class="dg-head" d="M 460,495 L 460,485 L 468,490 Z"></path>
  <path class="dg-line" d="M 648,490 L 670,490"></path>
  <path class="dg-head" d="M 670,495 L 670,485 L 678,490 Z"></path>
  <path class="dg-line" d="M 353,518 L 353,532"></path>
  <path class="dg-head" d="M 348,532 L 358,532 L 353,540 Z"></path>
  <path class="dg-line" d="M 768,518 L 768,532"></path>
  <path class="dg-head" d="M 763,532 L 773,532 L 768,540 Z"></path>
  <path class="dg-line" d="M 215,381 L 240,381 L 240,490 L 260,490"></path>
  <path class="dg-head" d="M 260,495 L 260,485 L 268,490 Z"></path>
  <rect class="dg-group" x="250" y="630" width="730" height="110" rx="12"></rect>
  <text class="dg-group-t" x="266" y="652">TELEMETRY — WHAT THE NEXT MODEL IS TRAINED ON</text>
  <rect class="dg-box" x="268" y="662" width="150" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="343" y="678.5">Event collector</text>
  <text class="dg-s dg-c" x="343" y="694.5">POST /events</text>
  <text class="dg-s dg-c" x="343" y="710.5">batched</text>
  <rect class="dg-box" x="448" y="662" width="160" height="56" rx="8"></rect>
  <path class="dg-qbar" d="M 461,671 L 461,709"></path>
  <path class="dg-qbar" d="M 470,671 L 470,709"></path>
  <path class="dg-qbar" d="M 479,671 L 479,709"></path>
  <text class="dg-t dg-c" x="546" y="686.5">Kafka</text>
  <text class="dg-s dg-c" x="546" y="702.5">shown · accepted</text>
  <path class="dg-box" d="M 638,669 L 638,711 A 75,7 0 0 0 788,711 L 788,669 A 75,7 0 0 0 638,669 Z"></path>
  <path class="dg-box" d="M 638,669 A 75,7 0 0 0 788,669" style="fill:none"></path>
  <text class="dg-t dg-c" x="713" y="690">Warehouse</text>
  <text class="dg-s dg-c" x="713" y="706">retained chars</text>
  <rect class="dg-box" x="818" y="662" width="148" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="892" y="686.5">Offline eval</text>
  <text class="dg-s dg-c" x="892" y="702.5">→ next model</text>
  <path class="dg-line" d="M 418,690 L 440,690"></path>
  <path class="dg-head" d="M 440,695 L 440,685 L 448,690 Z"></path>
  <path class="dg-line" d="M 608,690 L 630,690"></path>
  <path class="dg-head" d="M 630,695 L 630,685 L 638,690 Z"></path>
  <path class="dg-line" d="M 788,690 L 810,690"></path>
  <path class="dg-head" d="M 810,695 L 810,685 L 818,690 Z"></path>
  <path class="dg-line" d="M 966,690 L 988,690 L 988,230 L 973,230"></path>
  <path class="dg-head" d="M 973,225 L 973,235 L 965,230 Z"></path>
  <path class="dg-line" d="M 125,418 L 125,690 L 260,690"></path>
  <path class="dg-head" d="M 260,695 L 260,685 L 268,690 Z"></path>
  <text class="dg-note" x="20" y="762">Neither lower tier is allowed to make the top row slower. Tab reads the editor's own signals and its own local cache — never the vector index.</text>
</svg>
</div>

<p class="diagram-cap">The board to draw first, and the one an interviewer is looking for: components you could point at in production. Three arrows leave the client and only the top one has a latency budget — drawing the other two <em>below</em> it, in their own boxes, is how you say “off the hot path” without saying it.</p>

<div class="diagram" data-board="hot-path">
<svg viewBox="0 0 1000 838" role="img" aria-label="Tab completion hot path. Client column: keystroke, should-fire filter which suppresses twenty to forty percent, debounce, local context assembly in about ten milliseconds, a cache check whose hit renders ghost text at zero milliseconds, then a cancellable request. Server column: regional edge, then a small FIM model. A dashed box lists what the budget makes illegal: no retrieval service, no reranker, no large model. The response returns to the client, which renders ghost text only if the cursor has not moved.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">200 ms, keystroke to ghost text. Every box below is downstream of that one number.</text>
  <text class="dg-lane" x="55" y="78">CLIENT — THE EDITOR, WHERE MOST OF THE WORK HAPPENS</text>
  <text class="dg-lane" x="550" y="78">SERVER</text>
  <path class="dg-div" d="M 505,90 L 505,812"></path>
  <rect class="dg-ghost" x="550" y="110" width="420" height="92" rx="8"></rect>
  <text class="dg-lane dg-c" x="760" y="134">NOT IN THIS PATH</text>
  <text class="dg-s dg-c" x="760" y="155">no retrieval service · no reranker (100 ms on its own)</text>
  <text class="dg-s dg-c" x="760" y="172">no large model (≈350 ms just to prefill)</text>
  <text class="dg-s dg-c" x="760" y="189">the budget makes these illegal, not merely expensive</text>
  <rect class="dg-box" x="55" y="100" width="230" height="34" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="121.5">Keystroke</text>
  <path class="dg-line" d="M 170,134 L 170,150"></path>
  <path class="dg-head" d="M 165,150 L 175,150 L 170,158 Z"></path>
  <rect class="dg-box" x="55" y="158" width="230" height="66" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="179.5">Should-fire filter</text>
  <text class="dg-s dg-c" x="170" y="195.5">in a comment? mid-identifier?</text>
  <text class="dg-s dg-c" x="170" y="211.5">just dismissed at this position?</text>
  <path class="dg-line" d="M 285,191 L 302,191"></path>
  <path class="dg-head" d="M 302,196 L 302,186 L 310,191 Z"></path>
  <rect class="dg-warn" x="310" y="171" width="175" height="40" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="397.5" y="187.5">suppress · never fires</text>
  <text class="dg-s dg-c" x="397.5" y="203.5">20–40% of keystrokes</text>
  <path class="dg-line" d="M 170,224 L 170,240"></path>
  <path class="dg-head" d="M 165,240 L 175,240 L 170,248 Z"></path>
  <rect class="dg-box" x="55" y="248" width="230" height="34" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="269.5">Debounce ~30 ms</text>
  <path class="dg-line" d="M 170,282 L 170,298"></path>
  <path class="dg-head" d="M 165,298 L 175,298 L 170,306 Z"></path>
  <rect class="dg-box" x="55" y="306" width="230" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="330.5">Assemble context locally</text>
  <text class="dg-s dg-c" x="170" y="346.5">prefix + suffix (FIM), recent edits</text>
  <text class="dg-s dg-c" x="170" y="362.5">open tabs, LSP symbols in scope</text>
  <text class="dg-lbl" x="300" y="336">~10 ms · no network</text>
  <text class="dg-lbl" x="300" y="352">2–4k token budget</text>
  <path class="dg-line" d="M 170,378 L 170,394"></path>
  <path class="dg-head" d="M 165,394 L 175,394 L 170,402 Z"></path>
  <rect class="dg-box" x="55" y="402" width="230" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="423.5">Cache check</text>
  <text class="dg-s dg-c" x="170" y="439.5">key = hash(assembled context)</text>
  <path class="dg-line" d="M 285,427 L 302,427"></path>
  <path class="dg-head" d="M 302,432 L 302,422 L 310,427 Z"></path>
  <rect class="dg-good" x="310" y="409" width="175" height="36" rx="8"></rect>
  <text class="dg-good-t dg-c" x="397.5" y="431.5">HIT → ghost text at ~0 ms</text>
  <path class="dg-line" d="M 170,452 L 170,468"></path>
  <path class="dg-head" d="M 165,468 L 175,468 L 170,476 Z"></path>
  <rect class="dg-box" x="55" y="476" width="230" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="497.5">Send request</text>
  <text class="dg-s dg-c" x="170" y="513.5">requestId · abort any in-flight</text>
  <text class="dg-lbl dg-c" x="415" y="493">one request, cancellable</text>
  <path class="dg-line" d="M 285,501 L 542,501"></path>
  <path class="dg-head" d="M 542,506 L 542,496 L 550,501 Z"></path>
  <rect class="dg-box" x="550" y="476" width="420" height="66" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="497.5">Regional edge</text>
  <text class="dg-s dg-c" x="760" y="513.5">auth + rate limit, cached at the edge</text>
  <text class="dg-s dg-c" x="760" y="529.5">coalesce duplicate in-flight requests</text>
  <path class="dg-line" d="M 760,542 L 760,558"></path>
  <path class="dg-head" d="M 755,558 L 765,558 L 760,566 Z"></path>
  <rect class="dg-box" x="550" y="566" width="420" height="80" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="594.5">Inference — small FIM model</text>
  <text class="dg-s dg-c" x="760" y="610.5">continuous batching · prefix KV cache · speculative decoding</text>
  <text class="dg-s dg-c" x="760" y="626.5">single-shot at ~30 tokens: no partial-render flicker</text>
  <path class="dg-line" d="M 760,646 L 760,676 L 170,676 L 170,692"></path>
  <path class="dg-head" d="M 165,692 L 175,692 L 170,700 Z"></path>
  <text class="dg-note" x="190" y="668">later than ~300 ms → drop it, never render stale</text>
  <rect class="dg-box" x="55" y="700" width="230" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="721.5">Render ghost text</text>
  <text class="dg-s dg-c" x="170" y="737.5">only if the cursor hasn’t moved</text>
  <path class="dg-line" d="M 170,750 L 170,766"></path>
  <path class="dg-head" d="M 165,766 L 175,766 L 170,774 Z"></path>
  <rect class="dg-box" x="55" y="774" width="230" height="34" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="795.5">Tab = accept · else dismiss</text>
  <path class="dg-line" d="M 285,791 L 542,791"></path>
  <path class="dg-head" d="M 542,796 L 542,786 L 550,791 Z"></path>
  <rect class="dg-box" x="550" y="772" width="420" height="38" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="795.5">Events, batched — acceptance + retained characters</text>
  <text class="dg-note" x="55" y="830">Server unavailable → fail silent. No toast, no per-keystroke retry: the editor must feel exactly like a normal editor.</text>
</svg>
</div>

<p class="diagram-cap">The same system as a sequence, because the two branches are the economics and no architecture board can show a branch: the filter that suppresses a third of all keystrokes, and the cache that answers in zero.</p>

<div class="diagram" data-board="indexing">
<svg viewBox="0 0 1000 242" role="img" aria-label="Indexing pipeline, asynchronous and separate from the Tab hot path. Client side: a file watcher respecting .cursorignore feeds a Merkle tree of file hashes. Server side: a root-hash diff returns only the missing subtrees, an AST chunker splits on syntax boundaries, and chunks are embedded into a vector index keyed by content hash.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Indexing — a separate, asynchronous lifecycle. Tab never waits on it.</text>
  <text class="dg-lane" x="20" y="68">CLIENT</text>
  <text class="dg-lane" x="420" y="68">SERVER</text>
  <path class="dg-div" d="M 400,78 L 400,158"></path>
  <rect class="dg-box" x="20" y="88" width="160" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="100" y="112.5">File watcher</text>
  <text class="dg-s dg-c" x="100" y="128.5">respects .cursorignore</text>
  <path class="dg-line" d="M 180,116 L 197,116"></path>
  <path class="dg-head" d="M 197,121 L 197,111 L 205,116 Z"></path>
  <rect class="dg-box" x="205" y="88" width="160" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="285" y="112.5">Merkle tree</text>
  <text class="dg-s dg-c" x="285" y="128.5">of file hashes</text>
  <path class="dg-line" d="M 365,116 L 412,116"></path>
  <path class="dg-head" d="M 412,121 L 412,111 L 420,116 Z"></path>
  <rect class="dg-box" x="420" y="88" width="170" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="505" y="112.5">Root-hash diff</text>
  <text class="dg-s dg-c" x="505" y="128.5">→ missing subtrees only</text>
  <path class="dg-line" d="M 590,116 L 612,116"></path>
  <path class="dg-head" d="M 612,121 L 612,111 L 620,116 Z"></path>
  <rect class="dg-box" x="620" y="88" width="160" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="700" y="112.5">AST chunker</text>
  <text class="dg-s dg-c" x="700" y="128.5">chunk on syntax bounds</text>
  <path class="dg-line" d="M 780,116 L 802,116"></path>
  <path class="dg-head" d="M 802,121 L 802,111 L 810,116 Z"></path>
  <rect class="dg-box" x="810" y="88" width="170" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="895" y="112.5">Embed → vector index</text>
  <text class="dg-s dg-c" x="895" y="128.5">keyed by content hash</text>
  <text class="dg-s" x="20" y="182">▸  A one-line change in a 100k-file monorepo uploads one chunk — that is the entire point of the Merkle diff.</text>
  <text class="dg-s" x="20" y="204">▸  Vectors are keyed by content hash, not file path, so identical code across branches and forks dedupes for free.</text>
  <text class="dg-s" x="20" y="226">▸  Local edits update a local index immediately; the server index catches up. Tab’s context never comes from here.</text>
</svg>
</div>

<p class="diagram-cap">Drawn beside the hot path, not inside it. If your board makes indexing look like a step in the completion flow you have designed the wrong system — say “separate lifecycle” out loud as you draw the gap between them.</p>

### Flow A — a keystroke becomes a suggestion

1. Keystroke lands. **The should-fire filter runs first** (§10): in a comment? mid-identifier? just dismissed a suggestion at this position? **Suppress and stop.** This is the cheapest possible optimization and it runs before anything else.
2. Debounce ~30ms. More keystrokes within the window reset it — no point completing a half-typed token.
3. **Assemble context locally (§7):** prefix and suffix around the cursor, recent edits, open tabs, LSP-resolved symbols for identifiers in scope. Budget ~2–4k tokens, ~10ms, **no network.**
4. **Check the local cache**, keyed on a hash of the assembled context (§10). Hit → render immediately at ~0ms. Backspace and re-typing the same character is extremely common, so this hit rate is higher than intuition suggests.
5. Miss → issue the request with `requestId`, **aborting any in-flight request for this editor.**
6. Edge routes to the nearest inference region. Auth and rate-limit checks are cached at the edge — a database lookup here would consume a third of the budget.
7. Model does FIM completion with continuous batching. Stream or single-shot; at ~30 tokens the difference is small, and **single-shot avoids partial-render flicker**, which is a real UX consideration.
8. Client renders ghost text — **but only if the cursor hasn't moved.** A response that arrives after the user has typed on is discarded silently.
9. Tab → accept, insert, log `accepted`. Any other key → dismiss, log `shown`.
10. **Failure path — response arrives late (>300ms):** drop it. Never render a stale suggestion; it will be wrong and it will be jarring.
11. **Failure path — service unavailable:** fail silent. No error toast, no retry storm. The editor must feel exactly like a normal editor when the AI is down. **Retry with jitter on a background cadence, not per keystroke.**
12. **Failure path — user types through the suggestion:** abort the in-flight request. **This is the common case, not an edge case** — design the client for it and make sure the abort actually propagates to the GPU (§10), or you pay for tokens nobody will see.

### Flow B — indexing a codebase

1. Editor walks the workspace, respecting `.gitignore` and `.cursorignore`, and builds a **Merkle tree** of file hashes.
2. Client sends the root hash. Server compares against its stored tree and returns **only the subtree hashes it's missing** (§8).
3. Client uploads only those chunks. **A one-line change to a 100k-file monorepo uploads one chunk**, which is the whole point.
4. Server chunks on **AST boundaries**, embeds, and stores vectors keyed by hash — **not by file path**, so identical code across branches or forks dedupes naturally.
5. Local edits update a **local** index immediately; the server index catches up asynchronously. **Tab must never wait on the server index**, which is why §7's context comes from editor signals rather than from retrieval.
6. **Failure path — huge repo:** cap the index, prioritize recently-edited and frequently-opened files, and index the rest lazily. Say the cap out loud rather than pretending it scales unbounded.
7. **Failure path — user revokes / enables privacy mode:** delete server-side vectors and fall back to local-only context. **This must be a supported product state, not a degraded one.**

---

## 7 · Deep dive — context assembly, which is retrieval without a retriever

**The framing:** *at 200ms I can't run a retrieval pipeline, so I don't. The editor already knows what's relevant — the question is how to rank and pack signals it has locally, in about ten milliseconds.*

### The signals, ranked by value per token

| Signal | Why it's strong | Cost |
|---|---|---|
| **Prefix + suffix at the cursor** | The literal thing being completed. FIM needs both | Free |
| **Recent edit history** | **The strongest predictor.** What you just changed predicts what you'll change next — renames propagate, a new field needs a new accessor | Free, local |
| **Open tabs** | The user curated these. A human's working set beats a similarity score | Free, local |
| **LSP symbols** | Exact type signatures and definitions for identifiers in scope. **Precise, not probabilistic** | ~ms, local |
| **Imports / dependency graph** | Structurally guaranteed relevance | Free, local |
| **Semantic (embedding) search** | Finds conceptually similar code elsewhere | **Too slow for Tab.** Used by chat and agent surfaces |

**The point to make explicitly: embedding search is the *last* resort here, not the first.** For prose, semantic similarity is the only structure available. Code has a *real* dependency graph, a type system, and an explicit user working set — **exploit the structure you actually have before falling back to a fuzzy proxy for it.** That's the transferable idea, and it's the inverse of the RAG page's conclusion for a stateable reason.

### Packing the budget

~2–4k tokens, filled in priority order until full: immediate prefix/suffix → recent edits → LSP definitions of in-scope symbols → relevant open tabs → imports. Truncate the lowest priority, never the cursor's immediate surroundings.

**Two details worth saying:** put the most relevant context *closest to the cursor*, since attention is stronger near the point of prediction — the code analogue of lost-in-the-middle. And **keep the prefix ordering stable across keystrokes** so the KV cache from the previous request stays partially valid (§10). Small reordering churn destroys cache reuse for no benefit.

---

## 8 · Deep dive — the codebase is on someone else's computer

The RAG page's §8 was permissions. **Here it's privacy**, and it's the constraint that decides enterprise adoption.

**Scope this before you draw it: none of what follows is on the Tab path.** Tab's context is assembled in the editor from prefix and suffix, recent edits, open tabs, and LSP symbols (§7), so it never queries a server index and never needs one to be fresh. The sync below exists for **chat and agent**, the surfaces that must reach code *outside* the user's working set — the one thing local signals structurally cannot provide. If an interviewer asks why Tab needs a Merkle tree, the answer is that it doesn't, and noticing that boundary is the point.

### Merkle sync

Naive: upload the repo, re-upload on change. A 100k-file monorepo makes that untenable, and every upload is a privacy event.

**Merkle tree instead.** Hash every file, hash directories over their children, up to a root. Client sends the root; if it matches, **nothing has changed and zero bytes move.** If not, descend only into subtrees whose hashes differ. **A one-line change results in one chunk uploaded**, and the comparison cost is logarithmic in repo size rather than linear.

*(This is the same primitive as Git's object model and Dropbox's sync — good to name, since it shows the idea is borrowed rather than invented.)*

### Not storing the code

Three postures, worth presenting as a ladder because different customers sit on different rungs:

| Posture | Mechanism | Tradeoff |
|---|---|---|
| **Default** | Chunks embedded, **embeddings retained, plaintext discarded**. Store obfuscated paths and the hash | Server can retrieve *which* chunk matches without holding readable source. Embeddings are not perfectly one-way — inversion attacks exist — so this is risk reduction, not a guarantee. **Say that honestly** |
| **Privacy mode** | Nothing persisted server-side. Context is client-assembled per request and dropped after inference | Costs you semantic search across the repo for the chat surface. **Tab is unaffected**, because Tab never used server retrieval anyway — a nice property to point out |
| **Enterprise / on-prem** | Model and index both inside the customer's network | Solves it completely, at the cost of running deployments you don't control |

**The observation that makes this design coherent:** Tab's context comes from the editor, so **Tab works identically in privacy mode.** The architecture forced by the latency budget happens to be the architecture that's best for privacy. That's not luck worth claiming — but noticing the alignment is worth a sentence.

### Boundaries and secrets

Respect `.gitignore` and `.cursorignore`; scan for credential patterns before upload and before including anything in context. **A model suggesting another user's API key is the catastrophic failure mode here** — the analogue of the RAG page's permission leak, and worth naming as such.

---

## 9 · Deep dive — serving inference at 100k QPS with a 200ms ceiling

### Why the model is small, and why that's a feature

A large model cannot meet this budget — its prefill alone exceeds it. So Tab uses a **specialized small model** (single-digit billions of parameters), trained on fill-in-the-middle over **edit sequences** rather than static files.

**The non-obvious part: the small model is often *better* here, not merely faster.** The task is narrow and highly patterned — finish this line, propagate this rename, add the obvious next field. A model trained specifically on edit prediction beats a general large model at it, and it beats it by 10× on latency. **Say this rather than framing the small model as a compromise.**

### The serving stack

- **Continuous batching.** Requests join and leave the batch every decode step rather than waiting for the slowest sequence. This is the single biggest throughput lever and the thing that makes 100k QPS affordable.
- **Prefix KV caching.** Successive keystrokes share nearly all their context. Cache the KV state keyed on the context prefix and you skip most of the prefill — the direct analogue of the RAG page's prompt-prefix ordering, and the reason context ordering must stay stable (§7).
- **Speculative decoding.** A tiny draft model proposes several tokens, the main model verifies them in one pass. Roughly 2× on decode for identical output, and it works especially well on code because code is highly predictable.
- **Regional routing.** 60ms of transcontinental round trip is a third of the budget. Inference goes near the user.
- **Admission control.** Under overload, **shed load by not suggesting** rather than by queueing. A queued completion that arrives in 800ms is worse than nothing — it's actively disruptive. *(Load-shedding by degrading the product rather than delaying it, the same instinct as Ticketmaster's admission control applied to a different currency.)*

### Cancellation must reach the GPU

Client aborts → HTTP connection drops → **that must actually free the batch slot.** A cancellation that only stops rendering leaves the GPU generating tokens for a suggestion nobody will see, and with 80% of requests abandoned, this is not a rounding error — it's most of your compute. **This is the highest-value plumbing detail on the page.**

---

## 10 · Deep dive — the cheapest inference is the one you don't run

With 80% waste, suppression beats optimization. Three mechanisms:

### Should-fire filtering (client-side, before anything)

Suppress when: the cursor is mid-identifier (the user is typing a name, not finishing a thought), inside a string or comment where suggestions are rarely accepted, immediately after a dismissal at the same position (they said no), during rapid continuous typing (they know what they're writing), or when the context is unchanged since the last suggestion.

**A well-tuned filter suppresses 20–40% of triggers with a negligible acceptance-rate drop.** That is a larger cost win than any inference optimization on this page, and it costs one function on the client.

### Caching, three layers

| Layer | Key | Hit rate | Why it works |
|---|---|---|---|
| **Client cache** | Hash of assembled context | Moderate | Backspace-and-retype is constant. **Costs zero latency and zero dollars** |
| **Server KV cache** | Context prefix | High | Successive keystrokes share almost everything |
| **Server result cache** | Exact context hash, shared across users | Low but nonzero | Boilerplate and common idioms genuinely repeat. **Only safe on context that contains no user code** — otherwise you leak one user's source into another's suggestion. *(Same shape as the RAG page's semantic-cache leak.)* |

### Debounce as a cost lever

30ms of debounce is a UX decision *and* a cost decision — it collapses a burst of keystrokes into one request. **Tuning it is trading latency against spend**, and being able to frame it that way is better than treating it as a UI constant.

---

## 11 · Deep dive — measuring a product with no correct answer

There's no groundedness metric here and no ideal output. **The metric is behavioral.**

### The primary metrics

- **Acceptance rate** (accepted ÷ shown) — the north star. 20–35% is healthy.
- **Characters retained after N seconds** — the better metric, because it catches suggestions accepted and then immediately deleted. **Acceptance alone is gameable by suggesting short, safe, low-value completions**, and a team optimizing raw acceptance will drift there without noticing.
- **Suggestion latency vs acceptance**, correlated. This is how you prove the latency requirement rather than asserting it — acceptance falls off measurably as latency rises, and that curve is what justifies the whole architecture.
- **Suppression precision** — of the triggers the filter killed, how many would have been accepted?

### Offline evaluation

Hold out real edit sequences and measure whether the model predicts the edit the developer actually made. **Cheap, fast, and it correlates with acceptance** — which is what lets you iterate without shipping to users.

The honest caveat: exact-match on held-out edits under-counts, because a different-but-equally-good completion scores as a miss. Pair it with human review on a sample, the same way the RAG page pairs LLM-judge scores with human labels.

### The flywheel, and its trap

Accept/dismiss events are training data — the product generates its own improvement signal. **The trap: it's biased by what you showed.** You only observe outcomes for suggestions you chose to make, so training naively on accepted completions narrows the model toward what it already does. Mitigate with a small randomized holdout that fires in suppressed contexts, so you keep learning about the region your filter has decided not to explore. **Naming that feedback-loop bias unprompted is a strong signal** — it's the same selection-bias problem as ranking systems training on their own impressions.

---

## 12 · Data model, sharding, and storage decisions

Note what's *absent*: no transactional store, no cross-shard consistency, no durability requirement on the hot path. **Everything Tab touches is either ephemeral or rebuildable**, which is a direct consequence of the "no correctness invariant" line in §2.

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Local index** | Read every keystroke, written on every edit | Rebuildable from disk | **SQLite + an in-memory symbol table**, in the editor process | "Tab's context path must never cross the network, so the authoritative index for completion is local" |
| **Server vector index** | ANN for chat/agent surfaces, **not Tab** | Rebuildable via Merkle re-sync | **Vector store keyed by chunk hash**, per workspace | "Keyed by content hash so branches and forks dedupe, and so deletion is a hash lookup rather than a scan" |
| **Merkle tree state** | Compared on every sync | Rebuildable | **KV store**, path → hash per workspace | "Logarithmic diffing is the whole point; the tree itself is small" |
| **KV cache** | Read/written per inference step | None — pure cache | **GPU memory + host spillover**, keyed on context prefix | "This is what makes successive keystrokes cheap. Eviction is LRU by editor session" |
| **Completion events** | Append-heavy, analytical reads, training corpus | High | **Kafka → object storage → warehouse** | "This is the training signal and the metrics dataset. Columnar batch access, never a serving store" |
| **Auth / entitlement** | Checked per request at the edge | High | **Edge-cached tokens**, Postgres as source of truth | "A per-request database lookup would consume a third of the latency budget. Signed short-TTL tokens validated at the edge" |

**The decision worth defending: no database on the completion path at all.** Auth is a signature check, context is local, the cache is in memory. **The only network hop is the inference call itself** — and if you find yourself adding a lookup to that path, you're spending the budget that makes the product feel instant.

---

## 13 · Traps — the ranked list

**Design traps**

1. **Describing a RAG pipeline.** Embed → search → rerank → large model is 500ms+. It's the right answer for chat and the wrong answer for Tab. **Price it against the budget out loud** rather than just asserting it's too slow.
2. **Server-side context assembly.** The editor already has the signals; shipping the question up instead of the context costs round trips you don't have.
3. **Semantic search as the primary retriever.** Code has a dependency graph, a type system, and an explicit working set. Use the real structure before a fuzzy proxy for it.
4. **Fixed-size chunking.** Chunk on AST boundaries. A chunk ending mid-function is nearly worthless.
5. **Ignoring the suffix.** Completion here is fill-in-the-middle, not continuation. FIM is a different prompt format and a different objective.
6. **Treating cancellation as an edge case.** It's the majority path. And it must free the GPU slot, not just stop rendering.
7. **No should-fire filter.** The cheapest inference is the one you skip; suppression outperforms every optimization in §9.
8. **A shared result cache containing user code.** One user's source leaking into another's suggestion.
9. **Queueing under overload.** Shed load by not suggesting. A late suggestion is worse than none.
10. **Rendering a stale response.** If the cursor moved, discard it.
11. **Error UI when the service is down.** Fail silent. The editor must feel like an editor.
12. **Retry per keystroke.** Backoff on a background cadence, or an outage becomes a self-inflicted DDoS.
13. **Re-uploading the repo on change.** Merkle diff.
14. **Optimizing raw acceptance rate.** It's gameable by suggesting short and safe. Measure retained characters.
15. **Training on accepted completions only.** Selection bias narrows the model toward what it already does.

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific here:

16. **Designing all four surfaces at once.** Tab, inline edit, chat, and agent have budgets three orders of magnitude apart. Scope to one, name the others, and say what they'd share.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 516" role="img" aria-label="Cursor Tab five-minute skeleton. A banner scoping to the 200 millisecond budget, then the QPS and waste figures, why the budget makes a RAG pipeline illegal, client-side context assembly, the should-fire filter, the three caches, the small FIM model and its serving stack, cancellation, indexing as a separate lifecycle, the privacy ladder, and the metrics that matter.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="92.5">Four products, four budgets — scope to Tab at ~200 ms and let that constraint drive everything</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="30" y="140" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="164.5">~40 k QPS average, 100 k peak</text>
  <text class="dg-s dg-c" x="260" y="180.5">80%+ of inference is wasted — the economic centre</text>
  <circle class="dg-num" cx="30" cy="140" r="9"></circle>
  <text class="dg-num-t" x="30" y="143.4">2</text>
  <rect class="dg-warn" x="510" y="140" width="450" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="735" y="164.5">The budget kills the RAG pipeline</text>
  <text class="dg-s dg-c" x="735" y="180.5">rerank 100 ms alone · large-model prefill 350 ms</text>
  <circle class="dg-num" cx="510" cy="140" r="9"></circle>
  <text class="dg-num-t" x="510" y="143.4">3</text>
  <rect class="dg-box" x="30" y="216" width="600" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="330" y="236.5">Context assembled client-side in ~10 ms</text>
  <text class="dg-s dg-c" x="330" y="252.5">prefix/suffix (FIM) → recent edits → open tabs → LSP symbols → imports</text>
  <text class="dg-s dg-c" x="330" y="268.5">embeddings are the last resort, not the first</text>
  <circle class="dg-num" cx="30" cy="216" r="9"></circle>
  <text class="dg-num-t" x="30" y="219.4">4</text>
  <rect class="dg-box" x="650" y="216" width="310" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="805" y="236.5">Should-fire filter, before debounce</text>
  <text class="dg-s dg-c" x="805" y="252.5">suppressing 20–40% beats any</text>
  <text class="dg-s dg-c" x="805" y="268.5">inference optimisation</text>
  <circle class="dg-num" cx="650" cy="216" r="9"></circle>
  <text class="dg-num-t" x="650" y="219.4">5</text>
  <rect class="dg-box" x="30" y="300" width="460" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="320.5">Three caches</text>
  <text class="dg-s dg-c" x="260" y="336.5">client (context hash) · server KV (prefix)</text>
  <text class="dg-s dg-c" x="260" y="352.5">shared results, containing no user code</text>
  <circle class="dg-num" cx="30" cy="300" r="9"></circle>
  <text class="dg-num-t" x="30" y="303.4">6</text>
  <rect class="dg-box" x="510" y="300" width="450" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="320.5">Small FIM model, trained on edits</text>
  <text class="dg-s dg-c" x="735" y="336.5">continuous batching · prefix KV cache</text>
  <text class="dg-s dg-c" x="735" y="352.5">speculative decoding · regional routing</text>
  <circle class="dg-num" cx="510" cy="300" r="9"></circle>
  <text class="dg-num-t" x="510" y="303.4">7</text>
  <rect class="dg-box" x="30" y="384" width="300" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="405.5">Cancellation frees the slot</text>
  <text class="dg-s dg-c" x="180" y="421.5">it is the common path</text>
  <circle class="dg-num" cx="30" cy="384" r="9"></circle>
  <text class="dg-num-t" x="30" y="387.4">8</text>
  <rect class="dg-box" x="350" y="384" width="300" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="405.5">Indexing is separate</text>
  <text class="dg-s dg-c" x="500" y="421.5">Merkle diff · Tab never waits</text>
  <circle class="dg-num" cx="350" cy="384" r="9"></circle>
  <text class="dg-num-t" x="350" y="387.4">9</text>
  <rect class="dg-box" x="670" y="384" width="290" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="405.5">Privacy ladder</text>
  <text class="dg-s dg-c" x="815" y="421.5">Tab is unaffected by privacy mode</text>
  <circle class="dg-num" cx="670" cy="384" r="9"></circle>
  <text class="dg-num-t" x="670" y="387.4">10</text>
  <rect class="dg-box" x="30" y="454" width="930" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="480.5">Metrics: acceptance rate · retained characters (acceptance is gameable) · the latency-vs-acceptance curve</text>
  <circle class="dg-num" cx="30" cy="454" r="9"></circle>
  <text class="dg-num-t" x="30" y="457.4">11</text>
</svg>
</div>

<p class="diagram-cap">Eleven marks, and badge 3 is the one that wins the round: price the RAG pipeline out loud rather than asserting it away. At 200 ms a reranker is illegal, not merely expensive.</p>

1. Four products, four budgets. **Scope to Tab: ~200ms**, and let that constraint drive everything.
2. ~40k QPS average, 100k peak. **80%+ of inference is wasted** — that's the economic center of the design.
3. **Budget kills the RAG pipeline:** rerank alone is 100ms, large-model prefill is 350ms. Price it, don't assert it.
4. **Context is assembled client-side in ~10ms**: prefix/suffix (FIM) → recent edits → open tabs → LSP symbols → imports. Embeddings are the *last* resort, not the first.
5. Should-fire filter *before* debounce. Suppressing 20–40% beats any inference optimization.
6. Three caches: client (context hash), server KV (prefix), shared results (no user code).
7. Small FIM model trained on edit sequences. Continuous batching + prefix KV cache + speculative decoding + regional routing.
8. **Cancellation must free the GPU slot.** It's the common path.
9. Indexing is a separate lifecycle: **Merkle diff**, AST chunking, keyed by content hash. Tab never waits on it.
10. Privacy ladder: discard plaintext → privacy mode → on-prem. **Tab is unaffected by privacy mode**, because its context was never server-side.
11. Metrics: acceptance rate, **retained characters** (acceptance is gameable), latency-vs-acceptance curve. Watch the training feedback loop for selection bias.

---

## 15 · Variants — what actually changes

**The axis that governs this family: the latency budget.** Every order of magnitude changes what architecture is even available.

| Budget | Surface | What becomes possible / required |
|---|---|---|
| **~200ms** | **Tab completion** | This page. No retrieval, no rerank, small model, client-side context |
| **~1–3s** | Inline edit ("make this async") | Retrieval becomes affordable. A **larger model** fits. Introduces the **apply problem**: generating a diff that lands cleanly is its own subsystem, often a second fast model that reconciles a loose edit against exact file state |
| **~10s** | Chat over the codebase | **Now it's the RAG page**, with code-specific retrievers. Semantic search finally earns its place; conversation state and citations return |
| **Minutes** | Agent mode | Latency stops mattering; **termination, cost control, and authorization** take over. Multi-step error compounding, checkpointing, and human approval gates. Evals shift from output quality to *trajectory* quality |
| **Async / offline** | PR review, batch refactor | No interactivity at all. Batch APIs at ~50% cost, and evaluation becomes nearly the whole design |

**The general lesson, and the reason this page pairs with the RAG one:** *the latency budget is not a requirement you satisfy at the end — it's the input that determines which architectures are legal.* At 200ms retrieval is illegal; at 10s it's mandatory. Same product, same company, same codebase, opposite designs.
