# Design an LLM Knowledge Assistant — RAG, Permissions, Latency & Evals

## The question

> *"Design an internal knowledge assistant. Employees ask questions in plain English and get answers drawn from the company's own documents — the wiki, Drive, tickets, the codebase — with links back to the sources."*

**The product.** A chat box inside an internal tool. Someone types "what's our on-call escalation policy" or "how do I get access to prod" and gets a written answer assembled from the company's actual documents, with citations they can click to check. Roughly 10,000 employees, each asking a handful of questions a day.

The constraint that shapes everything: **not everyone can see every document.** Salary reviews, unreleased plans, legal threads and security incidents all live in the same corpus, and an answer must never quote something the person asking wasn't allowed to open. There is no version of this product where that is a follow-up.

**What a working system delivers**

- An answer grounded in real internal documents, with citations that go to the document and are worth checking.
- Nothing in that answer sourced from a document the asker couldn't have opened themselves — including the fact that such a document exists.
- Text that starts appearing quickly enough that people stop going back to searching the wiki by hand.
- Some way of knowing whether a change made it better or worse that isn't somebody's impression.

**Why this gets asked.** Uniquely among these problems, it is genuinely not a scale problem: 10,000 people × 20 questions a day is about two queries per second, which one database serves on a laptop. All of the engineering is in answer quality, permissions, cost per query, and proving any of it works — which is exactly where people who have only read about these systems run out of things to say.

---

**Archetype:** LLM application — a non-deterministic, slow, expensive, context-bounded component wrapped in a product.
**Cousins that reuse ~70% of this page:** ChatGPT over documents, customer support assistants, code assistants, Glean/internal search, any "chat with your data" product, the retrieval half of most agents.

**What's actually being graded:** whether you treat the model as **a component with a latency, cost, and quality budget** rather than as magic. Three specific signals separate people who have shipped one of these from people who have read about them: (1) you know **retrieval quality dominates model quality**, (2) you have a real **evaluation** story rather than "we'd check the outputs," and (3) you know that **permissions are the thing that kills these projects in production**, not scale.

**Contrast to have ready:** *Every other page in this set is a scale problem in disguise. This one genuinely isn't — 10,000 employees asking 20 questions a day is **2 queries per second**. Postgres could serve the metadata on a laptop. The engineering is entirely in quality, latency perception, cost per query, and not leaking documents.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "I want to set expectations on scale first, because it's the opposite of most systems: this is roughly 2 QPS, so throughput is a non-issue and I'm not going to spend time sharding anything. What's hard is four things. **Retrieval quality** — the model can only be as good as what I put in the context, and this is where most of the wins are. **Permissions** — the retrieval layer must never hand the model a document the user can't read, and post-filtering is too late. **Perceived latency** — total generation is 10+ seconds, so time-to-first-token and streaming are what make it feel fast. And **evaluation** — a prompt change can silently regress quality, so I need a golden set and a regression gate or I can't safely ship anything twice. I'd like to go deep on retrieval and permissions."

**Why open this way:** it immediately signals you've built one of these. Anyone who starts by sharding a vector database has revealed they're pattern-matching to a scale problem.

---

## 1 · Functional requirements

1. **Ask a natural-language question** and get an answer grounded in company documents, **with citations.**
2. **Stream the response** so it appears progressively.
3. **Multi-turn conversation** — follow-ups understand prior context.

**Out of scope (say them):** document authoring, model fine-tuning or training, tool use / agentic actions, voice.

**Below the line, likely follow-ups:** feedback capture, evaluation harness (§11 — I'd cover it anyway, it's the differentiator), agentic tool calls (§15).

---

## 2 · Non-functional requirements

| Property | Target | Why |
|---|---|---|
| **Time to first token** | **p95 < 500ms** | The metric that determines whether it feels fast. Total completion time barely matters if streaming starts quickly |
| Total completion | 5–30s, acceptable | Only because it streams. Without streaming this product is unusable |
| **Permission correctness** | **Absolute. Zero tolerance** | A user must never see content — or a citation, or a title — from a document they can't access. This is the invariant the design serves |
| Groundedness | Answers cite retrieved sources; unsupported claims minimized | Cannot be 100%. Design for verifiability rather than for perfection |
| Freshness | Document edits searchable within ~5 minutes | Stale answers about current policy are worse than no answer |
| Cost | Tracked per query, budgeted | ~$0.02/query × 200k/day is **$1.4M/year** — a real constraint that changes designs (§10) |
| Scale | ~2 QPS average, ~20 peak | Deliberately listed last. It constrains nothing |

**The sentence that earns the point:** *"The only hard invariant here is permissions. Everything else — latency, cost, even answer quality — degrades gracefully. A permission leak doesn't degrade, it ends the product."*

---

## 3 · Numbers that reframe the problem

**Traffic (the anti-number)**

- 10k employees × 20 queries/day = 200k/day ≈ **2.3 QPS average, ~20 peak.** State it early and move on. *Nothing here needs to be distributed for throughput.*

**Corpus and index**

- 1M documents × ~5k tokens ≈ **5B tokens**, chunked at ~500 tokens ≈ **10M chunks.**
- Embeddings at 1536 dims × 4 bytes = 6KB/chunk → **~61GB float32**, or **~15GB at int8 quantization.**
- **That fits in RAM on a single large machine.** Say this explicitly: the entire semantic index of a large enterprise is one box. Vector search at this scale is a library, not a cluster, and reaching for a distributed vector database is over-engineering you should name and reject.

**Latency budget — where the 500ms goes**

| Stage | Budget |
|---|---|
| Embed the query | ~20ms |
| ANN search over 10M vectors | ~30ms |
| Cross-encoder rerank, 50 → 8 | ~100ms |
| Permission resolution | ~20ms (cached) |
| **Model prefill → first token** | **~350ms** |
| **Total TTFT** | **~520ms** |
| Then decode at ~50 tok/s | 500 tokens ≈ 10s |

**Cost per query**

- 8 chunks × 500 tokens ≈ 4k input + ~500 output. At roughly $3/M input and $15/M output: **~$0.012 + $0.0075 ≈ $0.02/query.**
- **200k queries/day ≈ $4k/day ≈ $1.4M/year.** This single number justifies caching, model routing, and context budgeting (§10) — and it's the number most candidates never compute, which is why they can't justify any of those decisions.

---

## 4 · Core entities

- **Document** — id, source system, uri, title, `acl_ref`, content_hash, updated_at
- **Chunk** — id, document_id, ordinal, text, **embedding**, token_count, heading_path
- **Conversation** / **Message** — standard chat history, plus the retrieved chunk ids per turn
- **AclRef** — pointer to the source system's permission object (*not* a copied list — §8)
- **EvalCase** — question, ideal answer, expected source doc ids, tags
- **QueryLog** — question, retrieved ids, model version, prompt version, latency, cost, feedback

**Load-bearing details:**

- **`Chunk.heading_path`** — the document title and section headers, prepended to the chunk text *before embedding*. A chunk reading "This must be filed within 30 days" is meaningless alone; embedded with "Expense Policy › International Travel › Receipts" it's retrievable. **This one detail moves retrieval quality more than most model upgrades.**
- **`Document.content_hash`** — re-embed only when content actually changes. Embedding is the expensive part of ingestion, and most document "updates" are metadata.
- **`AclRef` is a reference, not a snapshot.** Copying permissions into the index means every group-membership change requires reindexing, and stale ACLs are leaks (§8).
- **`QueryLog.model_version` and `prompt_version`** — without these you cannot attribute a quality regression to anything. **Prompts are code and need versioning.**

---

## 5 · API

```
POST /v1/conversations                      → { conversationId }

POST /v1/conversations/{id}/messages        → SSE stream
  body: { text }
  headers: Idempotency-Key
  ← event: token      { delta: "..." }
  ← event: citation   { chunkId, docId, title, uri }
  ← event: done       { messageId, usage, latencyMs }
  ← event: error      { code, retryable }

POST /v1/messages/{id}/feedback             → { thumbs, comment }
GET  /v1/documents/{id}                     → doc metadata (ACL-checked)
```

**Decisions to narrate, unprompted:**

- **SSE, not WebSocket.** The stream is server→client only; SSE is plain HTTP, passes through proxies cleanly, and has built-in reconnect semantics. A WebSocket buys bidirectionality you don't need and costs you connection management. **The one wrinkle worth naming:** you need a request *body*, so the browser's `EventSource` API won't work — you use `fetch()` with a `ReadableStream` reader. *(This is the exact thing a frontend round will ask you to build.)*
- **Citations stream as their own event type**, not embedded in the text. Keeps rendering clean and lets the UI show sources as they're resolved rather than parsing markdown for links.
- **Cancellation is a first-class path.** Client aborts → the server must actually cancel the upstream model call. Otherwise you keep generating and paying for tokens nobody will read (§10).
- **Idempotency-Key on message send**, because a retried send that generates a second expensive completion is a real cost bug, not just a duplicate row.

---

## 6 · High-level design — flows

```
  INGESTION (async, continuous)
  Sources (Drive/Confluence/Slack) ──CDC──▶ Parser ──▶ Chunker ──▶ Embedder ──▶ Vector index
                                              │                                  + Chunk store
                                              └──▶ Doc metadata + acl_ref ──────▶ Metadata DB

  QUERY (interactive)
  Client ──SSE──▶ Orchestrator
                     ├─1─▶ Query rewrite (multi-turn → standalone question)
                     ├─2─▶ Embed + hybrid search (vector + BM25) → top 50
                     ├─3─▶ Permission filter (resolve user's groups live)
                     ├─4─▶ Cross-encoder rerank → top 8
                     ├─5─▶ Assemble prompt (static prefix first — §9)
                     ├─6─▶ LLM, streaming
                     └─7─▶ Stream tokens + citations, log everything
```

### Flow A — ingestion

1. CDC or a polling connector detects a changed document in the source system.
2. Parse to text; preserve heading structure. PDFs and slides are where this gets ugly — say so, it's the unglamorous 30% of the real work.
3. Compute `content_hash`. **Unchanged → stop.** Most "updates" are metadata churn and re-embedding them is pure waste.
4. Chunk on structure (headings, paragraphs) with ~10% overlap, targeting ~500 tokens. Prepend `heading_path` to each chunk's embedded text.
5. Embed changed chunks in batches. **Store the embedding model version with each vector** — you cannot mix embeddings from two models in one index, and forgetting this makes a model upgrade a full-corpus re-embed with no way to do it incrementally.
6. Upsert into the vector index and chunk store; update `acl_ref` and `updated_at`.
7. **Failure path — a document is deleted or its ACL narrows:** write a tombstone immediately rather than waiting for a reindex. Retrieval filters tombstones at query time. **Deletion must be fast even when reindexing is slow**, because a deleted document that's still answerable is both a correctness bug and a compliance problem.
8. **Failure path — embedding provider is down:** queue and retry with backoff. Ingestion lag degrades freshness, not correctness. Never block the query path on ingestion.

### Flow B — query

1. `POST /messages` opens an SSE stream. Orchestrator loads conversation history.
2. **Query rewrite:** a small, fast model turns "what about for contractors?" into a standalone question using prior turns. **Retrieval cannot work on a pronoun** — this step is invisible and load-bearing.
3. **Hybrid retrieval:** embed the rewritten query, run ANN over the vector index *and* BM25 over the text index, fuse with reciprocal rank fusion → top ~50 candidates (§7).
4. **Permission filter:** resolve the user's group memberships (cached ~60s), filter candidates against each chunk's `acl_ref` **against the live source of truth** (§8). This happens *before* anything reaches the model.
5. **Rerank:** cross-encoder scores the surviving candidates against the query → top 8. Biggest single quality lever (§7).
6. **Assemble the prompt** in cache-friendly order: static system instructions → retrieved chunks → conversation history → question (§9).
7. Call the model with streaming enabled. Emit `token` events as they arrive; emit `citation` events for chunks the answer actually references.
8. Log question, retrieved ids, prompt version, model version, latency, and cost. **This log is your eval corpus** (§11) — without it you're flying blind on day two.
9. **Failure path — retrieval returns nothing above threshold:** do not call the model with an empty context. **Say "I don't have anything on that."** A confident hallucination is far worse than an admission, and this is the cheapest hallucination mitigation available.
10. **Failure path — client disconnects mid-stream:** propagate the cancellation upstream and stop generation. Otherwise you pay for the full completion (§10).
11. **Failure path — model provider errors or times out:** retry once on a different provider or a smaller model, and stream an error event the UI can render inline rather than dropping the connection.

---

## 7 · Deep dive — retrieval, which is where the quality actually lives

**The framing to lead with:** *the model can only reason over what you put in its context, so retrieval quality bounds answer quality. Upgrading the model is the expensive way to buy a small improvement; fixing chunking and adding a reranker is the cheap way to buy a large one.*

### Why naive vector search fails

"Embed the query, ANN over chunk embeddings, take top 5" is the demo architecture and it breaks in four specific ways:

| Failure | Why | Fix |
|---|---|---|
| **Exact terms miss** | Embeddings are semantic. Product codes, error strings, ticket IDs, and unusual acronyms have no meaningful semantic neighborhood | **Hybrid search:** BM25 alongside vectors, fused |
| **Chunks lack context** | "This must be filed within 30 days" — filed where? Under what policy? | Prepend `heading_path`; overlap chunks |
| **Top-k is imprecise** | Bi-encoders embed query and document *independently*, so they can't model interaction between them | **Cross-encoder rerank** |
| **Lost in the middle** | Models attend less reliably to content in the middle of a long context | Fewer, better chunks — which reranking enables |

### Hybrid search and fusion

Run both retrievers, then combine with **reciprocal rank fusion**: score each document as `Σ 1/(k + rank_i)` across retrievers. RRF works on *ranks* rather than scores, which matters because BM25 scores and cosine similarities aren't on comparable scales and normalizing them is fiddly and brittle. **Rank fusion sidesteps the calibration problem entirely** — that's the reason to prefer it, and it's a nice thing to be able to explain.

### Reranking — the highest-leverage component

Retrieval uses a **bi-encoder**: query and chunk are embedded separately, so search is a fast nearest-neighbor lookup, but the model never sees the pair together. A **cross-encoder** takes `(query, chunk)` jointly and outputs a relevance score — far more accurate, far too slow to run over 10M chunks.

**So: bi-encoder for recall over millions, cross-encoder for precision over 50.** Retrieve top-50 cheaply, rerank to top-8 expensively.

**Cost, volunteered:** ~100ms of latency and a second model to operate. It buys the ability to use *fewer* chunks at higher quality, which reduces prompt tokens — so it partially pays for itself in cost and TTFT. **This funnel is the same shape as the Uber page's k-ring → haversine → routing:** cheap filter over everything, expensive scorer over the survivors.

### Chunking

Fixed-size chunking is the default and the weakest choice. Prefer structure-aware splitting on headings and paragraphs, ~500 tokens with ~10% overlap, never splitting mid-sentence, and always with `heading_path` prepended.

**The one to mention if pushed:** for tables and structured content, embed a *summary* of the table alongside the raw rows — raw table markup embeds terribly because its semantics live in the layout rather than the tokens.

---

## 8 · Deep dive — permissions, the thing that kills these projects

Every other failure on this page degrades quality. This one leaks confidential documents into a chat window with an audit trail, and it is the reason most internal RAG deployments stall before launch.

### The rule

**The model must never receive a chunk the user cannot read.** Everything follows from that one sentence.

| Approach | Verdict |
|---|---|
| Filter the **answer** after generation | **Catastrophic.** The model already saw it; it will paraphrase confidential content without quoting it, and no filter catches that |
| Filter **retrieved chunks** before prompt assembly | **Correct.** The only acceptable design |
| Filter at **query time against the live ACL source** | Correct *and* handles the stale-permission case below |

### Over-fetch and filter

Post-retrieval filtering shrinks your result set — retrieve 8, filter to 2, and the answer is thin. So **retrieve top-50 before filtering, then rerank the survivors.** The reranking stage was already narrowing 50 → 8, so permission filtering slots in for free between them. Two requirements that looked independent share one mechanism.

**When ACLs are highly restrictive** (most users can see a small slice of the corpus), over-fetching 50 isn't enough and you should push the filter *into* the vector search as a metadata pre-filter. Note the tradeoff honestly: **filtered ANN degrades as selectivity increases** — the index walks its graph and discards most neighbors, so recall drops and latency rises. Some vector stores handle this far better than others, and it's a real selection criterion (§12).

### The stale-permission problem

Alice is removed from `#finance` at 10:00. Your index snapshot says she's a member until the next reindex. **Between those two moments, she can retrieve finance documents** — and a reindex measured in hours is a leak measured in hours.

**Resolve permissions at query time against the source of truth.** Store an `acl_ref` on each chunk (a pointer to the source system's permission object), and at query time expand the user's group memberships and evaluate. Cache the user→groups expansion for ~60 seconds, not longer — **that cache TTL is your leak window, so state it as a number and make it small.**

### Three leaks people forget

1. **Citations.** A citation showing a document *title* the user can't access is a leak. Filter citations with the same check as chunks.
2. **Conversation history.** Turn 1 retrieves a doc; Alice's access is revoked; turn 5 references turn 1's context. **Re-validate historical context on every turn**, or don't carry retrieved chunks forward across turns at all.
3. **Caches.** A semantic cache keyed only on the question will happily serve Bob an answer computed from Alice's documents. **The cache key must include the permission context** (§10) — this is the single most likely place to build a leak while trying to save money.

---

## 9 · Deep dive — latency, TTFT, and prompt cache ordering

### TTFT is the metric

Total generation takes 10+ seconds and users tolerate it — provided something appears in under a second. **Optimize time to first token; total time is a distant second.** Every product decision here follows from that.

### Prefill vs decode — know the difference

| Phase | What it does | Bound by | Scales with |
|---|---|---|---|
| **Prefill** | Processes the entire prompt to produce the first token | **Compute** — all input tokens processed in parallel | Input length, roughly linearly |
| **Decode** | Generates each subsequent token | **Memory bandwidth** — sequential, one token at a time | Output length |

**The consequence that changes your design: every chunk you add to the context increases TTFT.** Context isn't only a dollar cost, it's a latency cost paid at exactly the moment the user is waiting. This is why reranking to 8 good chunks beats stuffing 40 mediocre ones on *three* axes at once — quality, cost, and perceived speed.

### Prompt cache ordering — free TTFT

Providers cache prompt prefixes. A cache hit skips prefill for the cached portion, which is most of your TTFT.

**Therefore order the prompt most-static to most-dynamic:**

```
1. System instructions      ← identical every request, always cached
2. Few-shot examples        ← identical every request
3. Retrieved chunks         ← varies per query
4. Conversation history     ← varies, grows
5. The user's question      ← always unique
```

Put retrieved chunks *before* the system prompt and you've invalidated the cacheable prefix on every request. **Same tokens, same cost on paper, several hundred milliseconds of difference in TTFT.** It's the highest ratio of impact to effort on this page, and it's invisible unless you know to look.

### Streaming and cancellation

- **SSE over `fetch` + `ReadableStream`** (not `EventSource`, which can't send a body).
- **Optimistic echo:** render the user's message immediately, then a placeholder assistant message that fills in. *(Identical to the messaging page's local echo — same reconciliation problem.)*
- **AbortController on the client must propagate to the upstream model call.** A stop button that only stops rendering still bills you for every token.
- **Reconnection:** SSE reconnects automatically, but a resumed stream needs the server to either replay from a buffer or the client to fetch the completed message over HTTP. **Pick one and say so** — otherwise a subway tunnel silently truncates the answer with no error.

---

## 10 · Deep dive — cost

$1.4M/year (§3) makes this a design constraint rather than an afterthought. Four levers, roughly in order of payoff:

**1. Context budgeting.** Prompt tokens dominate — 4k input vs 500 output. Reranking to 8 chunks instead of 40 cuts input cost ~5×. **The cheapest token is the one you don't send**, and reranking is how you send fewer without losing quality.

**2. Model routing.** Not every query needs the largest model. Classify difficulty — a simple lookup, a summarization, a multi-document synthesis — and route accordingly. Requires evals per tier (§11) or you'll silently degrade quality to save money and not notice.

**3. Caching, carefully.**

| Type | Mechanism | Hit rate | Danger |
|---|---|---|---|
| Exact match | Hash the question | Low — few people phrase things identically | Minimal |
| **Semantic** | Embed the question, serve a cached answer if cosine > ~0.95 | Meaningful | **The permission leak in §8.** Cache key *must* include the user's permission context |
| **Prompt prefix** | Provider-side, via ordering (§9) | Very high | None — this is free money |

**4. Cancellation.** Abandoned generations are pure waste. If 10% of queries are abandoned halfway, that's ~5% of your bill for tokens nobody read.

**The honest caveat to volunteer:** aggressive caching on a permissioned corpus is where cost optimization and the §8 invariant collide, and **the invariant wins.** Say that explicitly — the willingness to leave money on the table for a security property is itself a signal.

---

## 11 · Deep dive — evaluation, which is what makes this an engineering project

Without evals you cannot change the prompt, upgrade the model, or swap the embedding without guessing. **"We'll look at some outputs" is the answer that marks someone who has only built a demo.**

### Separate retrieval metrics from generation metrics

This is the structural point, and it matters more than which metrics you pick:

| Layer | Metrics | Answers |
|---|---|---|
| **Retrieval** | Recall@k, MRR, hit rate on expected doc ids | "Did we even fetch the right material?" |
| **Generation** | Groundedness/faithfulness, answer relevance, citation accuracy | "Given the right material, did we produce a good answer?" |

**If you only measure end-to-end quality, a regression tells you something broke and nothing about where.** Retrieval failures and generation failures have completely different fixes — one is a chunking or reranker problem, the other is a prompt or model problem — and you need the split to know which lever to pull.

### The golden set

200–500 `(question, ideal answer, expected source docs)` cases, **curated from real query logs** rather than invented. Cover the head (common questions), the tail (rare but important), and known failure modes. Refresh it as the corpus and the questions drift — a golden set that never changes stops measuring reality.

### LLM-as-judge, with its eyes open

Groundedness at scale is graded by a model. Two disciplines make it trustworthy: **calibrate the judge against a few hundred human labels** and track its agreement rate, and **use a different model family than the generator** where you can, since a model grading its own output has a measurable self-preference bias. Report judge agreement alongside the scores — a metric whose reliability you haven't measured isn't a metric.

### Online signals

Offline evals don't predict everything. Watch: thumbs up/down (low volume, high signal), **citation click-through** (are people verifying, which means they don't trust it?), **follow-up rephrase rate** (a strong proxy for a failed answer), and escalation-to-human rate.

### Treat prompts as code

Version them, review them, and **gate changes on the golden set in CI.** Pin the model version explicitly — a provider silently updating a model behind the same alias will change your behavior with no deploy on your side, and without pinning plus a regression gate you'll discover it from user complaints.

---

## 12 · Data model, sharding, and storage decisions

**No sharding for throughput anywhere.** At 2 QPS with a 15GB index, partition for operational reasons only (per-source-system indexes, or per-tenant isolation in a multi-tenant deployment). **Say this and move on** — time spent partitioning here is time not spent on retrieval or permissions.

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Vector index** | ANN over 10M vectors, **with ACL metadata filtering** | Rebuildable from chunks | **pgvector with HNSW** — genuinely the right call here | "15GB fits in memory, and the killer feature is that ACL filters are a plain SQL `WHERE` in the same query. A dedicated vector DB forces me to either duplicate permission metadata or post-filter" |
| Chunk + doc store | Point reads by id, full re-read on reindex | High | **Postgres**, same instance | "One system, transactional consistency between chunks and their metadata, no sync problem" |
| Text index (BM25) | Keyword search for hybrid | Rebuildable | **Postgres FTS**, or OpenSearch if you outgrow it | "Postgres FTS is adequate at 10M chunks and avoids a second system. I'd move to OpenSearch when I need better analyzers, not before" |
| Conversations | Append-only per conversation, read recent | High | **Postgres** | "It's a chat log at 2 QPS. This is not a Cassandra problem" |
| Semantic cache | Embedded question → answer | None | **Redis**, key includes permission context | "The permission context in the key is not optional (§8)" |
| Query + eval logs | Append-heavy, analytical reads | High | **Object storage + a warehouse** | "This is the eval corpus and the cost-attribution dataset — it wants columnar batch access, not a serving store" |

**The decision worth defending: one Postgres, not a stack of specialized systems.** At this corpus size, pgvector, FTS, chunk storage, and metadata all fit in one instance, and **the ACL join is the reason** — permission filtering is a `WHERE` clause against tables that live in the same transaction rather than a metadata sync problem across two systems. Name the point where you'd change your mind: roughly 100M+ chunks, or when filtered-ANN recall degrades measurably, at which point a dedicated store with first-class filtered search earns its complexity. **"Here's my simplest sufficient architecture and here's the number that would change it" is a stronger answer than reaching for the specialized tool immediately.**

---

## 13 · Traps — the ranked list

**Design traps**

1. **Treating this as a scale problem.** 2 QPS. Sharding a vector database here reveals pattern-matching.
2. **Filtering permissions after generation.** The model already saw it and will paraphrase it.
3. **Caching without permission context in the key.** The most likely way to build a leak while optimizing cost.
4. **Snapshotting ACLs into the index.** Every group change becomes a reindex, and the gap is a leak window.
5. **Vector-only retrieval.** Misses exact terms — codes, IDs, acronyms. Hybrid + RRF.
6. **No reranker.** The single highest-leverage component, and it's cheap.
7. **Chunks without heading context.** "File within 30 days" is unretrievable and unusable.
8. **Calling the model with empty or weak retrieval.** Return "I don't know." Cheapest hallucination fix available.
9. **Optimizing total latency instead of TTFT.** Users tolerate 10s of streaming, not 3s of blank screen.
10. **Retrieved chunks before the system prompt.** Destroys prefix caching and hundreds of ms of TTFT for free.
11. **Stuffing maximum context.** Costs money, raises TTFT, and *lowers* quality via lost-in-the-middle.
12. **Cancellation that only stops rendering.** You keep paying.
13. **Re-embedding unchanged documents.** Content-hash first; most updates are metadata.
14. **Mixing embedding model versions in one index.** Silently broken similarity. Version-tag every vector.
15. **Unpinned model versions.** The provider changes behavior under you with no deploy on your side.
16. **No evals, or end-to-end-only evals.** The second is subtler and nearly as bad — you learn that something broke, never what.
17. **Carrying retrieved context across turns without re-validating permissions.**

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific here:

18. **Talking about models instead of systems.** The interesting engineering is retrieval, permissions, latency budgeting, cost, and evals. Model selection is a paragraph, and candidates who spend fifteen minutes comparing model benchmarks have answered a different question than the one asked.

---

## 14 · The five-minute skeleton (draw this cold)

1. **~2 QPS.** Not a scale problem. Say it first and don't shard anything.
2. Four real problems: **retrieval quality, permissions, TTFT, cost** — plus evals as the thing that lets you change any of them safely.
3. Ingestion: CDC → parse → **content-hash gate** → structure-aware chunk with `heading_path` → embed → index. Tombstone on delete immediately.
4. Query: rewrite → **hybrid (vector + BM25, RRF)** top-50 → **permission filter** → **cross-encoder rerank** to 8 → prompt → stream.
5. **Permissions before the model, never after.** Over-fetch 50 so filtering doesn't starve the result. Resolve against live ACLs; the group cache TTL *is* the leak window.
6. Leaks people forget: citations, conversation history, semantic cache keys.
7. **TTFT ~500ms is the metric.** Prefill is compute-bound and grows with input, so context length costs latency, not just money.
8. **Order the prompt static → dynamic** for prefix caching. Free TTFT.
9. Cost ~$0.02/query ≈ $1.4M/yr. Levers: fewer chunks, model routing, permission-aware caching, real cancellation.
10. Evals: golden set from real logs, **retrieval metrics separate from generation metrics**, LLM-judge calibrated against humans, regression gate in CI, pinned model versions.
11. Storage: **one Postgres** — pgvector + FTS + metadata — because the ACL filter is a `WHERE` clause. Name the size where you'd switch.

---

## 15 · Variants — what actually changes

**The axis that governs this family: how much autonomy does the model have?** As autonomy rises, the hard problem migrates from *retrieval* to *authorization, termination, and cost control*.

| Autonomy | Problem | What changes |
|---|---|---|
| **None — retrieval Q&A** | This page | Retrieval quality and permissions dominate |
| **Read-only tools** | Assistant that queries dashboards or APIs | Retrieval matters less; **tool selection and argument validation** matter more. Latency becomes multi-hop and unpredictable |
| **Write-capable tools** | Agent that files tickets, sends messages, updates records | **Authorization per tool call**, not per query. Idempotency for retried actions. Confirmation gates on destructive operations. Now every trap from the transactional pages applies |
| **Multi-step autonomous** | Research agent, coding agent | **Error compounding** (95% per step is 60% over 10 steps), **termination conditions**, cost explosion via loops, and human-in-the-loop checkpoints. Evals shift from answer quality to *trajectory* quality |
| **Batch / offline** | Bulk classification, extraction, summarization | **Latency requirement vanishes entirely.** Batch APIs at ~50% cost, no streaming, no TTFT. Evals become nearly the whole design |
| **Ultra-low-latency** | Inline code completion | Budget drops to ~200ms — **too tight for retrieval or a large model.** Small model, local context only. Fundamentally a different architecture — see the Cursor page, which is this row worked out in full |

**The general lesson:** RAG is the *lowest*-autonomy point in this family and the only one where retrieval is the whole story. Everything to the right inherits these problems and adds authorization and termination on top — which is why this page is the right foundation for the others.

---

## 16 · Active recall — answer these cold, no scrolling

**Protocol:** out loud, in full sentences. Check the pointer only after attempting. Schedule in `00-interview-mechanics.md` §8.

| # | Prompt | Check |
|---|---|---|
| 1 | What's the QPS, and what does that number tell you not to do? | §3 |
| 2 | Cost per query and per year. Which three decisions does that number justify? | §3, §10 |
| 3 | Why does vector-only retrieval fail? Give two distinct failure modes. | §7 |
| 4 | What is RRF and why fuse on ranks rather than scores? | §7 |
| 5 | Bi-encoder vs cross-encoder: what's the difference and why use both? | §7 |
| 6 | What is `heading_path` and why does it matter more than a model upgrade? | §4, §7 |
| 7 | Why is post-generation permission filtering catastrophic rather than merely late? | §8 |
| 8 | Why over-fetch 50 before filtering? Which two requirements share that mechanism? | §8 |
| 9 | Alice loses group access at 10:00. Trace the leak and the fix. What is your leak window, numerically? | §8 |
| 10 | Name three permission leaks that aren't the retrieved chunks themselves. | §8 |
| 11 | Prefill vs decode: what bounds each, and what does that imply about context length? | §9 |
| 12 | Give the correct prompt ordering and explain what it buys. | §9 |
| 13 | Why SSE rather than WebSocket — and what's the browser API wrinkle? | §5, §9 |
| 14 | A user hits stop. What must happen beyond stopping the render? | §5, §10 |
| 15 | Retrieval returns nothing good. What do you do, and why is it the cheapest fix available? | §6 |
| 16 | Why separate retrieval metrics from generation metrics? What can't you do without the split? | §11 |
| 17 | Two disciplines that make LLM-as-judge trustworthy. | §11 |
| 18 | Name three online signals and what each one indicates. | §11 |
| 19 | Why one Postgres instead of a dedicated vector database? Name the number that would change your mind. | §12 |
| 20 | Why must embeddings carry a model version, and what breaks without it? | §6, §13 |
| 21 | Moving from Q&A to a write-capable agent — what becomes the hard problem, and why? | §15 |
