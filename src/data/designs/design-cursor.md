# Design Cursor — AI Coding Assistant (Tab Completion)

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

```
  EDITOR (client — where most of the work happens)
   keystroke ──▶ should-fire filter ──▶ debounce ──▶ context assembly ──▶ cache check
                      │                                    │                  │ hit
                      └── suppress                         │                  └──▶ render
                                                           ▼
                                          ┌──── Regional Edge ────┐
                                          │  auth, rate limit,    │
                                          │  request coalescing   │
                                          └───────────┬───────────┘
                                                      ▼
                                        Inference (small FIM model,
                                        continuous batching, KV cache)
                                                      │
                                                      ▼
                                       ghost text ──▶ accept/dismiss ──▶ events (batched)

  INDEXING (async, separate lifecycle)
   file watcher ──▶ Merkle diff ──▶ upload only changed chunks ──▶ AST chunker
                                                                   ──▶ embeddings ──▶ vector index
                                                                   (obfuscated / deletable — §8)
```

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

---

## 16 · Active recall — answer these cold, no scrolling

**Protocol:** out loud, in full sentences. Check the pointer only after attempting. Schedule in `00-interview-mechanics.md` §8.

| # | Prompt | Check |
|---|---|---|
| 1 | Name the four surfaces and their latency budgets. Why scope to Tab? | §0, §15 |
| 2 | Price the standard RAG pipeline against a 200ms budget, stage by stage. | §3 |
| 3 | What fraction of inference is wasted, and what three design decisions does that justify? | §3, §10 |
| 4 | Why is the request volume so much higher than DAU suggests? | §3 |
| 5 | Rank the context signals by value. Why is embedding search *last* here and *first* in RAG? | §7 |
| 6 | What is FIM and why does chat-style left-to-right completion get this wrong? | §4 |
| 7 | Why chunk code on AST boundaries rather than fixed size? | §4, §6 |
| 8 | Why must context ordering stay stable across keystrokes? | §7, §9 |
| 9 | Explain Merkle sync. What does a one-line change in a 100k-file repo cost? | §8 |
| 10 | Give the three privacy postures. Why is Tab unaffected by privacy mode? | §8 |
| 11 | Why is a small model *better* here rather than just faster? | §9 |
| 12 | Name three inference-serving optimizations and what each one buys. | §9 |
| 13 | Cancellation stops the render. What else must it do, and why does it dominate cost? | §9, §10 |
| 14 | What does the should-fire filter suppress, and how does it compare to inference optimization? | §10 |
| 15 | Three cache layers: key, hit rate, and which one can leak. | §10 |
| 16 | Why is acceptance rate gameable? What's the better metric? | §11 |
| 17 | Describe the training feedback loop's selection bias and how you'd counter it. | §11 |
| 18 | Service is down. What does the user see, and what must the client not do? | §6 |
| 19 | Why is there no database on the completion path? What's the only network hop? | §12 |
| 20 | What is the "apply problem," and which surface has it? | §15 |
| 21 | State the general lesson connecting this page to the RAG page in one sentence. | §15 |
