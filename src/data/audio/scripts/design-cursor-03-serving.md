---
id: design-cursor-03-serving
title: "Cursor Tab, part three — the small model is better, and cancellation must reach the accelerator"
source: src/data/designs/design-cursor.md §9-10
minutes: 9
---
Two dives here, and they're two halves of the same economic argument. The first is how you serve a hundred thousand inference requests a second inside a two-hundred-millisecond ceiling. The second is the observation that most of those requests should never have been issued in the first place.

Three things. <break time="0.8s" /> First, why the model is small, and why that is a feature rather than a compromise. <break time="0.7s" /> Second, the serving stack, and the plumbing detail that's worth more than all the rest of it. <break time="0.7s" /> And third, suppression — because the cheapest inference is the one you don't run.

So. The model is small. Single-digit billions of parameters, trained on fill-in-the-middle over edit sequences rather than over static files.

The forced reason is obvious: a large model cannot meet this budget, because its prefill alone exceeds the entire thing. So you have no choice.

But here's the non-obvious part, and it's how you should frame it. The small model is often genuinely better at this task, not merely faster.

Think about what the task actually is. Finish this line. Propagate this rename. Add the obvious next field. It is narrow and highly patterned. A model trained specifically on edit prediction beats a general-purpose large model at edit prediction — and separately, it beats it by roughly ten times on latency.

So present it as a specialisation win with a latency bonus, not as a compromise you were forced into. That framing is more accurate and it lands much better.

Second thing. The serving stack — five techniques, and I'll rank them by leverage.

Continuous batching is the biggest. Requests join and leave the batch at every decode step, rather than every sequence waiting for the slowest one in its batch to finish. This is the single largest throughput lever available and it's what makes a hundred thousand queries a second affordable at all.

Prefix key-value caching is next. Successive keystrokes share almost all of their context — you typed one character, the other four thousand tokens are identical. So cache the key-value state keyed on the context prefix, and you skip most of the prefill entirely. And this is precisely why the context ordering has to stay stable across keystrokes. Reordering your context blocks for tidiness would silently destroy this, which is the kind of change that looks harmless in review and shows up as a doubled compute bill.

Speculative decoding. A tiny draft model proposes several tokens ahead, and the main model verifies all of them in a single pass. That's roughly a two-times speedup on decode, for bit-identical output. And it works especially well here because code is highly predictable — far more so than prose. Closing braces, expected parameter names, obvious next lines.

Regional routing. Sixty milliseconds of transcontinental round trip is a third of your entire budget. So inference runs near the user. That's not an optimisation, that's arithmetic.

And admission control, with a twist. Under overload you shed load by not suggesting, rather than by queueing. And the reasoning is worth stating: a completion that arrives eight hundred milliseconds late is worse than no completion at all. It isn't degraded service, it's actively disruptive — the user has typed past it and now something is flickering at them.

So you degrade the product rather than delaying it. That's the same load-shedding instinct as an admission queue in front of a ticketing system, applied to a completely different currency.

Now the highest-value plumbing detail on this page, and it's easy to skip.

Cancellation must reach the accelerator.

When the client aborts, the connection drops. And that drop has to actually free the batch slot. If your cancellation only stops rendering on the client, the G.P.U. carries on faithfully generating tokens for a suggestion that no human being will ever see.

And remember that eighty percent of requests are abandoned. So this is not a rounding error. This is most of your compute. A cancellation path that stops at the web tier means you are paying full price for the waste you already knew about.

Third thing. Suppression, which follows directly from that eighty percent.

Three mechanisms.

First, should-fire filtering on the client, before anything else happens. Suppress when the cursor is mid-identifier, because the user is typing a name rather than finishing a thought. Suppress inside strings and comments, where suggestions are rarely accepted. Suppress immediately after a dismissal at the same position — they already said no. Suppress during rapid continuous typing, because someone typing fast already knows what they're writing. And suppress when the context is unchanged since the last suggestion.

A well-tuned filter of that kind suppresses twenty to forty percent of triggers with a negligible drop in acceptance rate.

Sit with that for a second. That is a larger cost win than any inference optimisation on this entire page. And it costs you one function on the client. No new infrastructure, no model change, no serving work.

Second mechanism, caching, in three layers.

A client cache keyed on a hash of the assembled context. Backspace-and-retype is constant developer behaviour, so the hit rate is meaningful — and a client hit costs zero latency and zero dollars, which no server-side cache can match.

A server key-value cache keyed on the context prefix, with a high hit rate, for the reason already covered.

And a server result cache keyed on an exact context hash, shared across users. The hit rate is low but genuinely nonzero, because boilerplate and common idioms really do repeat across a whole userbase.

But that third one carries a sharp edge, and you should raise it yourself. It is only safe on context that contains no user code. Otherwise you have built a mechanism that serves one customer's source code inside another customer's suggestion. That is the same shape as a cross-tenant leak in a semantic cache, and it is the kind of bug that becomes a public incident.

Third mechanism, and it reframes something people treat as a user-interface constant. Debounce is a cost lever. Thirty milliseconds of debounce is a user-experience decision and simultaneously a spending decision, because it collapses a burst of keystrokes into a single request. Tuning it is explicitly trading latency against money — and being able to describe it that way, rather than as a fixed number somebody picked, is a better answer.

<break time="0.8s" /> So, three things to carry.

The small model is a specialisation win, not a compromise. Trained on edit sequences it beats a general large model at edit prediction, and it beats it tenfold on latency.

Cancellation has to reach the accelerator. With eighty percent of requests abandoned, a cancel that only stops rendering means you're paying full price for all of that waste — it's the highest-value plumbing on the page.

And suppression beats optimisation. A client-side filter that kills twenty to forty percent of triggers, at negligible acceptance cost, is worth more than every serving trick combined — and under overload you shed by not suggesting, because a late completion is worse than none.
