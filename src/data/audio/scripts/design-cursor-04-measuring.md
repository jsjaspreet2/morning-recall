---
id: design-cursor-04-measuring
title: "Cursor Tab, part four — measuring a product with no correct answer"
source: src/data/designs/design-cursor.md §11-12
minutes: 8
---
How do you evaluate a product where there is no correct output? There's no groundedness metric here. There's no reference answer to compare against. Two different completions can both be excellent and share not a single token.

So the metric has to be behavioral — what the user did — and that turns out to have a trap in it that's worth the whole episode.

Three things. <break time="0.8s" /> First, the metrics, including why the obvious one is gameable. <break time="0.7s" /> Second, offline evaluation and the flywheel, which has a selection bias built into it. <break time="0.7s" /> And third, the storage decisions, where what's absent is more interesting than what's present.

So, metrics. Four of them.

Acceptance rate — accepted divided by shown — is the north star, and twenty to thirty-five percent is healthy.

But characters retained after some number of seconds is the better metric, and here's why. Acceptance alone catches a suggestion the user took. It does not catch a suggestion the user took and then immediately deleted.

And that gap matters more than it sounds, because raw acceptance is gameable. A model can raise it by suggesting short, safe, low-value completions — closing a bracket, finishing an obvious word. Those get accepted constantly and are worth almost nothing.

So a team optimizing raw acceptance will drift toward triviality without anybody deciding to. Nobody makes that call; the metric makes it for them. Measuring retained characters is what keeps the metric pointed at value rather than at agreement.

Third metric: suggestion latency correlated against acceptance. And this one has a specific job — it's how you prove the latency requirement instead of asserting it. Acceptance falls off measurably as latency rises, and that curve is the actual justification for the entire architecture. Anybody can claim two hundred milliseconds matters. Showing the curve is different.

Fourth: suppression precision. Of the triggers your filter killed, how many would actually have been accepted? Without that, your filter is unfalsifiable — it looks like a pure cost win because you never see what it cost you.

Second thing. Offline evaluation, and then the flywheel.

Offline is straightforward and cheap. Hold out real edit sequences and measure whether the model predicts the edit the developer actually made. It's fast, it costs nothing per iteration, and it correlates well enough with acceptance to let you iterate without shipping to users.

The honest caveat, which you should volunteer: exact match under-counts. A different-but-equally-good completion scores as a miss. So pair it with human review on a sample — the same way you'd pair an automated judge with human labels anywhere else.

Now the flywheel. Every accept and every dismiss is training data. The product generates its own improvement signal, continuously and for free, which is a genuinely lovely property.

And here is the trap, which is the best thing in this section. That signal is biased by what you chose to show.

You only ever observe outcomes for suggestions you decided to make. So if you train naively on accepted completions, you narrow the model toward what it already does. It gets better and better at the region it already occupies, and learns nothing about the region your filter decided not to explore. The system converges on its own habits and calls it improvement.

The mitigation is a small randomized holdout that deliberately fires in suppressed contexts. You accept a little waste and a little user annoyance in exchange for continuing to learn about the space you've stopped sampling.

Naming that feedback-loop bias before you're asked is a strong signal, because it is the same selection-bias problem that ranking and recommendation systems have when they train on their own impressions. It shows you recognize the shape rather than just this instance of it.

Third thing. Storage — and start with what's absent, because that's the interesting part.

There is no transactional store. No cross-shard consistency. No durability requirement anywhere on the hot path. Everything Tab touches is either ephemeral or rebuildable.

And that is a direct consequence of the no-correctness-invariant line from the requirements. Because a wrong suggestion costs a keystroke, nothing on this path needs to be durable. Those two facts are the same fact, seen from opposite ends of the design.

Now the components, quickly.

The local index is an embedded database plus an in-memory symbol table, living in the editor process. The sentence: Tab's context path must never cross the network, so the authoritative index for completion is local.

The server vector index serves chat and agent, not Tab, and it's keyed by chunk content hash per workspace. Keying by content hash means branches and forks deduplicate automatically, and deletion becomes a hash lookup rather than a scan.

Merkle tree state is a simple key-value store mapping path to hash. Logarithmic diffing is the entire point, and the tree itself is small.

The key-value cache lives in accelerator memory with spillover to host memory, keyed on the context prefix, evicted least-recently-used by editor session. That's what makes successive keystrokes cheap.

Completion events go to a log, then object storage, then a warehouse. That's both the training signal and the metrics dataset — columnar batch access, and never a serving store.

And authorization uses signed short-lived tokens validated at the edge, with a relational database as the source of truth behind them. The reasoning is pure budget arithmetic: a per-request database lookup would consume a third of your latency budget. So you don't do one.

Which brings us to the decision worth defending, and it's the one to close on.

There is no database on the completion path at all. Not one. Authorization is a signature check. Context is local. The cache is in memory. The only network hop in the entire path is the inference call itself.

And the discipline that follows: if you find yourself adding a lookup to that path, you are spending the budget that makes the product feel instant. That's the sentence to say — because it turns the architecture into a rule that somebody could actually apply in a code review six months later.

<break time="0.8s" /> So, three things to carry.

Acceptance is gameable and retained characters aren't. A model can raise acceptance by suggesting trivia, and a team optimizing it will drift there without anyone choosing to.

The flywheel trains on what you chose to show, so it narrows toward what it already does. A randomized holdout firing in suppressed contexts is how you keep learning about the space your filter stopped sampling.

And there's no database on the completion path. Auth is a signature, context is local, cache is memory, and the only network hop is inference itself. Everything Tab touches is ephemeral or rebuildable — which is the same fact as having no correctness invariant, viewed from the other end.
