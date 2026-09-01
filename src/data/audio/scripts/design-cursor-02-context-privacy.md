---
id: design-cursor-02-context-privacy
title: "Cursor Tab, part two — retrieval without a retriever, and a codebase you don't own"
source: src/data/designs/design-cursor.md §7-8
minutes: 9
---
If you can't run a retrieval pipeline, what do you do instead? The answer is more interesting than the constraint, and it contains an idea that transfers well past this problem: the editor already knows what's relevant. You don't need to go find out.

Two deep dives. <break time="0.8s" /> First, context assembly — retrieval without a retriever, in about ten milliseconds. <break time="0.7s" /> And second, the fact that the codebase is on somebody else's computer, which is the constraint that decides enterprise adoption.

So. The framing for the first one. At two hundred milliseconds I cannot run a retrieval pipeline, so I don't. The editor already knows what is relevant. The question is purely how to rank and pack the signals it has locally, in roughly ten milliseconds.

Six signals, ranked by value per token, and the ordering is the insight.

Strongest and free: the prefix and the suffix at the cursor. That's the literal thing being completed, and fill-in-the-middle needs both halves.

Next, recent edit history — and this is the single strongest predictor in the list. What you just changed predicts what you're about to change. Renames propagate. A new field needs a new accessor. It costs nothing and it's already sitting in the editor.

Then open tabs. And the reasoning here is lovely: the user curated these. A human's working set beats a similarity score, because a person already did the relevance judgment for you and you can just read the answer.

Then language server symbols — exact type signatures and definitions for every identifier in scope. Note the word exact. This is precise information, not probabilistic. You are not guessing what a type is; you are being told.

Then imports and the dependency graph, which give you structurally guaranteed relevance rather than inferred relevance.

And last — genuinely last — semantic embedding search. It finds conceptually similar code elsewhere in the repository, and it is simply too slow for Tab. It belongs to the chat and agent surfaces.

Now, the point to make explicitly, because it's the transferable idea. Embedding search is the last resort here, not the first.

For prose, semantic similarity is the only structure available to you. There's nothing else. But code has a real dependency graph, an actual type system, and an explicit user-curated working set. So exploit the structure you genuinely have before falling back on a fuzzy statistical proxy for it.

That is the exact inverse of the conclusion you'd reach on a document retrieval product — and it's inverted for a reason you can state, which is what makes it a strong answer rather than a contrarian one.

Then packing. You have two to four thousand tokens, and you fill them in priority order until full. Immediate prefix and suffix first, then recent edits, then language server definitions of in-scope symbols, then relevant open tabs, then imports. Truncate from the lowest priority upward, and never truncate the cursor's immediate surroundings.

Two details worth saying out loud. Put the most relevant context closest to the cursor, because attention is stronger near the point of prediction — that's the code analogue of the lost-in-the-middle effect in long prompts.

And keep the prefix ordering stable across keystrokes. This one sounds fussy and is worth real money: a stable ordering means the key-value cache from the previous request stays partially valid. Reordering churn destroys cache reuse and buys you nothing at all. We'll come back to why that matters in the next episode.

Second dive. The codebase is on someone else's computer.

And the first thing to do here is scope it, before you draw anything — because this is a trap. None of what follows is on the Tab path.

Tab's context is assembled in the editor from prefix, suffix, recent edits, open tabs, and language server symbols. It never queries a server index. It never needs one to be fresh.

The synchronization machinery exists for chat and agent — the surfaces that have to reach code outside the user's current working set, which is the one thing local signals structurally cannot provide. So if an interviewer asks why Tab needs a merkle tree, the correct answer is that it doesn't. Noticing that boundary is the point of the section.

Now, the sync itself. The naive approach is to upload the repository and re-upload on change. A hundred-thousand-file monorepo makes that untenable on cost alone — and separately, every upload is a privacy event, which is a different kind of expensive.

So, a merkle tree. Hash every file. Hash each directory over its children. Continue up to a single root hash.

The client sends the root. If it matches what the server has, nothing has changed and zero bytes move. If it doesn't match, you descend only into the subtrees whose hashes differ.

A one-line change results in exactly one chunk being uploaded, and the comparison cost is logarithmic in repository size rather than linear. It's worth naming that this is the same primitive underneath Git's object model and consumer file sync products — because it shows you're borrowing a known idea rather than inventing one on a whiteboard.

Then privacy, and present it as a ladder, because different customers genuinely sit on different rungs.

The default posture: chunks are embedded, the embeddings are retained, and the plaintext is discarded. You store obfuscated paths and a hash. So the server can determine which chunk matches a query without holding readable source.

And here you should be honest about something most people skate past. Embeddings are not perfectly one-way. Inversion attacks exist. So this is risk reduction, not a guarantee. Saying that unprompted is worth more than a confident overclaim, because the interviewer very likely knows.

Privacy mode: nothing is persisted server-side at all. Context is assembled on the client per request and dropped after inference. The cost is that you lose semantic search across the repository for the chat surface.

But Tab is completely unaffected — because Tab never used server retrieval in the first place.

And that's the observation that makes this whole design coherent, so give it a sentence. The architecture that the latency budget forced on you happens to be the architecture that's best for privacy. Tab works identically in privacy mode, not because anyone designed it that way for privacy, but because assembling context locally was already the only way to hit the budget. I wouldn't claim that as foresight. But noticing the alignment is worth pointing out.

Third rung: enterprise and on-premises. Model and index both live inside the customer's network. That solves the problem completely, at the cost of running deployments you don't control and can't debug.

Finally, boundaries and secrets. Respect the repository's ignore files. Scan for credential patterns both before upload and before including anything in a context window.

And name the catastrophic failure mode explicitly, because it's the one that ends the company: a model suggesting another user's credentials. That is the analogue of a permission leak in a retrieval system, and it deserves to be said out loud rather than assumed.

<break time="0.8s" /> So, three things to carry.

Exploit the structure you actually have before falling back on a fuzzy proxy for it. Code has a dependency graph, a type system, and a curated set of open tabs. Embedding search is the last resort here, and that's the inverse of a prose retrieval product for a reason you can state.

Recent edits beat everything, and open tabs beat similarity — because a human already did the relevance judgment and you can just read it.

And scope the sync before you draw it. Merkle trees and index freshness belong to chat and agent, not to Tab. Tab assembles locally, which is why it works unchanged in privacy mode.
