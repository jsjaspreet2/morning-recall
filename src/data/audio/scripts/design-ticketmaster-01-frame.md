---
id: design-ticketmaster-01-frame
title: "Ticketmaster, part one — the inverse of a scale problem"
source: src/data/designs/design-ticketmaster.md §0-4
minutes: 9
---
Here is the trap in this question, and almost everyone walks into it. You hear ticketing, you hear stadium onsale, you hear ten million people, and you start designing for scale. That is the wrong instinct, and noticing why is the entire thing being graded.

A stadium onsale resolves to sixty thousand successful sales. Not sixty thousand a second. Sixty thousand, total, for the whole event. A single well-tuned relational database does that in under a second. So throughput was never the problem. The problem is that ten million people want those sixty thousand rows inside the same sixty seconds, and you are not allowed to sell any one of them twice.

This is the inverse of a scale problem. Modest write throughput, catastrophic contention, concentrated on a handful of rows.

Four things. <break time="0.8s" /> First, the frame to open with, before you draw anything. <break time="0.7s" /> Second, the requirements, including one that isn't really a feature. <break time="0.7s" /> Third, the numbers, done at three separate levels. <break time="0.7s" /> And fourth, the entities, where one modelling choice quietly decides whether the whole design works.

So, the opening frame. What you say in the first minute.

Two workloads live in this system, and they want opposite things.

Browse is about ninety-nine point nine percent of all traffic. It's read-only, and it is perfectly happy being a few seconds stale. That's a caching and fan-out problem.

Purchase is a rounding error by volume, and it demands strict serialisability on individual rows — because selling one seat twice is a business-ending bug, and selling it zero times is lost revenue.

So the plan is: separate those two paths completely. Put an admission control layer in front of the purchase path so it never sees the full herd. And go deep on the seat reservation lifecycle, because that is where correctness actually lives. Search, payments, and ticket delivery get named as subsystems and set aside.

That opening does two jobs. It reframes the problem away from scale, which is where most candidates default, and toward contention and consistency — which is what the interviewer chose this problem to test. And it pre-commits your deep dive, so you control where the conversation goes next.

Second thing. Requirements.

Three functional ones. Browse an event and see which seats are available. Reserve specific seats — a temporary hold — then complete the purchase within a time limit. And never sell the same seat twice, at any traffic level.

That third one is unusual, and it's worth noticing out loud. It is a correctness invariant masquerading as a feature. State it as a requirement anyway, because it is the thing the entire design is organised around, and naming it early means every later decision has something concrete to be justified against.

Say your out-of-scope list too. Event creation, dynamic pricing, resale, transfers, refunds, seat-map rendering. Naming them is what stops an interviewer wondering whether you forgot.

Now the non-functional side, and this is where the interesting sentence lives.

Consistency on a seat sale is strictly serialisable, with no exceptions. There is no eventually-consistent version of two people in one chair.

But consistency on seat display is a completely different answer. Eventually consistent, up to about five seconds stale, and that is explicitly acceptable — because ten million readers cannot share a consistent snapshot, and trying to give them one is how you melt the system. The interface is a hint. The hold call is the truth.

For availability, browse targets four nines and should degrade gracefully. And the purchase path prefers consistency over availability. That is the rare case where the correct answer is to sacrifice availability, and here is the sentence that earns the point: this is one of the few systems where I would knowingly choose consistency over availability on the write path, and I would scope that choice tightly to seat reservation rather than to the whole system.

Refusing a sale is recoverable. Double-selling is not.

Third thing. The numbers — and do these at three separate levels, because collapsing them is exactly the imprecision an interviewer probes first.

Per event. Successful sales for the entire onsale: sixty thousand. Total. Contention ratio: about a hundred and sixty-six users per seat. That is the number that matters, and every downstream decision is about managing that ratio on individual rows.

Read traffic is a different universe. Ten million users polling a seat map every two seconds is five million queries a second — four orders of magnitude above the write path, which is precisely why the read architecture is entirely separate.

And here's the insight hiding in the payload. One bit per seat is enough for the client: selectable, or not. Sixty thousand seats is about seven and a half kilobytes. Two bits, if you want to distinguish held from sold, and it still compresses to a couple of kilobytes. But the number that matters isn't the bit count. It's that the entire live availability state of a stadium is one small broadcastable object. So you serve five million queries a second by shipping one object, rather than by answering five million queries.

Per shard is the level that actually sizes your hardware. Admission control lets roughly two hundred thousand users through, at about thirty percent conversion. With retries and abandoned holds, that's around five hundred thousand conditional updates plus sixty thousand sale commits, over five to ten minutes. Call it one to two thousand writes a second, on one shard.

And most of that work is failed attempts — conditional updates returning zero rows because somebody else won the row. They are cheap individually and murderous in aggregate, because they collide. Contention, not volume.

Now the causal chain worth stating explicitly. You cannot split this. A four-seat order needs a single transaction, so an event's shard is one node, and one node's capacity is a hard ceiling. That is precisely why admission control exists. The queue is the thing that makes demand fit an unsplittable shard.

And globally? Five hundred million tickets a year is about sixteen sales a second averaged. Even at a punishing peak — say fifty simultaneous hot onsales, each doing one to two thousand writes a second — you land near fifty to a hundred thousand writes a second, spread across fifty different shards. Completely ordinary. The system is not throughput-bound at any level.

Fourth and last. Entities, and three details that carry weight.

Hold expiry is a column, not a lock service. A hold is a row with an expiry timestamp on it, and that single choice is what makes the reservation lifecycle work.

A seat is per event, not global. Seat twelve A exists once per show, not once per stadium. Obvious in hindsight, frequently modelled wrong, and getting it wrong makes every query cross-join awkwardly.

And three states, not two. Held inventory is neither available nor sold. Any system that models availability as a boolean will oversell during the hold window.

<break time="0.8s" /> So, four things to carry.

This is the inverse of a scale problem. Sixty thousand total sales, a hundred and sixty-six people per seat. Contention, not throughput.

Separate browse from purchase completely, and say that browse is a hint while the hold call is the truth.

Choose consistency over availability, out loud, and scope it tightly to seat reservation — because refusing a sale is recoverable and double-selling isn't.

And the seat map is one small broadcastable object, which is how five million queries a second becomes a fan-out problem instead of a database problem.

And if you've prepped a geospatial marketplace, have this contrast ready. That is enormous write throughput with almost no contention. This is modest write throughput with catastrophic contention. Opposite designs.
