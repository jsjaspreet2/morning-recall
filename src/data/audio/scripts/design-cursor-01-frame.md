---
id: design-cursor-01-frame
title: "Cursor Tab, part one — the latency budget that destroys retrieval"
source: src/data/designs/design-cursor.md §0-4
minutes: 9
---
This problem has a single sentence at its center, and if you can say it with numbers attached you have essentially passed. It is this: the latency budget destroys the standard retrieval architecture, and everything else in the design is a consequence of rebuilding around that.

Two hundred milliseconds end to end means no reranker. No cross-encoder. No large model. And no network round trip you don't absolutely need. Candidates who walk in and describe a retrieval pipeline have answered the chat question instead of the Tab question, and the interviewer knows it immediately.

Four things. <break time="0.8s" /> First, the frame, and why naming four products matters. <break time="0.7s" /> Second, the requirement that is unusual enough to change everything. <break time="0.7s" /> Third, the arithmetic — where the budget goes, and what it forbids. <break time="0.7s" /> And fourth, the entities, where two of them are quietly the whole product.

So, the frame. Cursor is really four products with four different budgets. Tab completion at a couple of hundred milliseconds. Inline edit at a few seconds. Chat at ten seconds or more. And agent mode at minutes.

They share an indexing layer and almost nothing else. So scope to Tab — because Tab is the one where the latency constraint genuinely forces the architecture, rather than merely influencing it.

Naming all four and then picking one does two jobs. It demonstrates you understand the product rather than the category. And it pre-empts an interviewer steering you toward a generic retrieval answer, which is the failure mode of this entire question.

The contrast to have ready is sharp. A retrieval assistant is a request-response product with a ten-second budget, where retrieval quality is essentially everything. Tab is a keystroke-loop product with a two-hundred-millisecond budget, where cancellation, caching, and knowing when not to fire are everything. Smaller model, local context, and the metric is the acceptance rate rather than the answer quality.

Second thing. The requirements, and one of them is genuinely unusual.

Functionally it's simple. Predict the next edit as the user types and render it inline as ghost text. Accept on Tab, dismiss on any other keystroke. And make suggestions aware of the wider codebase, not just the current file.

Non-functionally, the numbers that matter. Median latency under a hundred and fifty milliseconds, and the ninety-fifth percentile under three hundred — because past roughly three hundred milliseconds the suggestion arrives after the user has already typed past it. A late suggestion isn't degraded, it's worthless.

Acceptance rate of twenty to thirty-five percent is realistic and good. Note the metric is accepted completions, not quality.

And now the unusual one. There is no correctness invariant. None. A wrong suggestion costs the user exactly one keystroke to dismiss.

That is remarkable, and it should change how you design. Here's the sentence: there's no correctness invariant here, which is unusual — a bad suggestion costs a keystroke. Which means I can be aggressive about caching, about speculation, and about using a small model, in ways I would never accept on a transactional system.

Compare that to a ticketing system where a double sale is business-ending. Same interviewer, opposite freedom. Recognizing which kind of system you're in is most of the skill.

Two more requirements worth naming. Privacy — code must not be retained, and enterprise mode must not let it leave the network. That's the constraint that actually blocks deals. And availability degrades to nothing, silently: if the service is down, the editor still edits. You never block the keystroke path. Never.

Third thing. The arithmetic, which is the best material on this page.

Start with volume, because it's larger than the user count suggests. A developer types around two hundred characters a minute while actively coding, and a debounced trigger fires maybe twenty to forty times a minute. A million daily actives, at roughly two active hours each, at thirty triggers a minute, is about three and a half billion requests a day. Call it forty thousand queries a second average, and over a hundred thousand at peak.

That is a genuinely high-volume inference workload — and it is the exact opposite of a retrieval assistant, which runs at a couple of queries a second. Say that comparison out loud, because it is the reason those two products share almost no architecture despite sounding similar.

Now the second fact, which is the economic center of the product. At a twenty-five percent acceptance rate, three quarters of completions are never used. Add the ones canceled mid-flight because the next keystroke arrived, and well over eighty percent of all issued inference produces nothing at all.

Most of this product's work is thrown away by design.

Now the budget itself. Debounce takes about thirty milliseconds — which isn't latency exactly, it's a deliberate wait to see whether more keystrokes are coming. Context assembly takes about ten milliseconds, and it happens locally, in the editor, with no network and no vector search. The network round trip is twenty to sixty milliseconds, which is why regional routing is doing real work. Prefill is around thirty milliseconds on a small model with a few thousand tokens. Decode is about forty for roughly thirty tokens. Render, five. Total, somewhere around a hundred and fifty to a hundred and eighty milliseconds.

And now price a standard retrieval pipeline against that same budget. Embedding the query, twenty milliseconds. Approximate nearest neighbour search, thirty. Cross-encoder reranking, a hundred. Large-model prefill, three hundred and fifty.

The reranking alone eats half your budget. The model prefill blows through the entire budget twice over, by itself.

That comparison is the single most useful thing you can state in this interview, because it is a quantitative reason for a structural decision. You are not asserting that retrieval is wrong here. You are showing the arithmetic that makes it impossible.

One more number. Thirty output tokens on a small model costs a fraction of a cent per request. Trivially cheap. Multiply by three and a half billion a day and it is a seven-figure annual compute bill — of which roughly eighty percent is spent on completions nobody ever used.

Which gives you the conclusion: the cheapest optimization available is not firing. A filter that suppresses thirty percent of low-value requests is worth more than any inference optimization on this entire page.

Fourth thing. Entities, and two of them are quietly the product.

Chunks are split on syntactic boundaries — function, class, method — and never on a fixed token count. A chunk that ends mid-function is nearly useless as context, and unlike prose, code has a real grammar to split on. So use it.

Edit history is a first-class entity, not telemetry. What the user changed in the last sixty seconds predicts what they are about to change next, better than anything semantic does. Cursor's Tab model is trained specifically on edit sequences rather than on static file snapshots, and that's the difference between a completion product and an autocomplete feature.

The accepted flag on a completion event is both the entire product metric and the training signal. Everything else in the design is instrumentation around that one field.

And the prefix-suffix split, which is a cheap strong signal. Code completion is fill-in-the-middle, not left-to-right continuation. The model needs what comes after the cursor as well as before it. That is a different prompt format and a different training objective from a chat model, and naming it costs you five seconds.

<break time="0.8s" /> So, four things to carry.

The latency budget destroys retrieval, and you should be able to prove it with numbers: reranking eats half the budget and a large model's prefill exceeds the whole thing twice over.

There is no correctness invariant. A bad suggestion costs one keystroke, and that buys architectural freedom you'd never have on a transactional system.

Over eighty percent of issued inference is wasted, so the cheapest optimization is not running at all. Suppressing low-value requests beats optimizing the ones you run.

And edit history beats semantics. What somebody changed in the last minute predicts the next change better than any embedding of their codebase.
