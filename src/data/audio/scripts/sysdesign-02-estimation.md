---
id: sysdesign-02-estimation
title: "Estimation — the four-line model, and the conclusion the numbers force"
source: src/data/guides/system-design.md — Estimate and set SLOs
minutes: 9
---
Most people do capacity math because they think they're supposed to. They produce some numbers, nobody challenges them, and the numbers change nothing about the design that follows. That is wasted time, and an interviewer can hear it. This episode is about doing the arithmetic so that it forces a conclusion you couldn't have asserted without it.

Four things. <break time="0.8s" /> First, the four-line capacity model, and the line everybody forgets. <break time="0.7s" /> Second, a worked estimate end to end, where the sequence matters more than any single division. <break time="0.7s" /> Third, service levels, and the two definitions almost everyone skips. <break time="0.7s" /> And fourth, the distributions that quietly make an average useless.

So. The capacity model is four lines, and you should be able to write them without thinking.

Average queries per second is active users, times actions per user, divided by the number of seconds in a day. Peak queries per second is that average times a peak factor — and you should test a few, say two, five, and ten, rather than picking one. Storage per day is writes per day, times bytes per item, times your replication factor.

And the fourth line is the one people forget. Concurrency equals arrival rate times time in system. That's Little's Law, and it is the line that matters most for anything holding a long-lived connection — streams, uploads, sockets, model responses.

Here's why it matters. A system taking a hundred requests a second, where each request lives for ten seconds, is a system holding a thousand things open at once. A thousand. That number sizes your gateway, and your queries-per-second figure says absolutely nothing about it. If you only ever do the first three lines, you will size a system that falls over on connections while the throughput graph looks fine.

Second thing. The worked estimate — and the reason to do this in full is that the sequence is the skill. Any one line is just arithmetic.

Take a social feed. A hundred million daily active users. Each one opens the app and reads the feed about ten times a day, and posts about once every five days.

Reads first. A hundred million times ten is a billion feed reads a day. Now divide by the seconds in a day — and here's a trick worth stealing: don't divide by eighty-six thousand four hundred. Call it a hundred thousand. It's close enough, and it's very much faster to say out loud. That gives you roughly ten thousand queries a second on average. Apply a five times peak factor for the evening hump and you're at about fifty thousand at peak. At a two kilobyte response, that's a hundred megabytes a second leaving your read path before any cache amplification at all — and that is already the number that tells you an edge cache is not optional.

Now writes. A hundred million times a fifth is twenty million posts a day, which is about two hundred and thirty writes a second on average, maybe a thousand at peak.

Stop there for a second, because this is the moment the arithmetic earns its keep. Two hundred and thirty writes a second is a number that one well-tuned relational primary handles without an argument. So write throughput was never the interesting problem here. Fanout is. Saying that out loud, at exactly this point, is the entire reason you did the division.

Storage. Twenty million posts a day at a kilobyte each is about twenty gigabytes a day of logical post data, which is roughly seven terabytes a year before indexes, replication, and backups. Multiply by three for replication, add a meaningful factor for indexes, and you land in the tens of terabytes a year. That is large, entirely ordinary, and not by itself a reason to shard anything.

And now the conclusion the numbers force. Your read to write ratio is roughly fifty to one. So this design pays at write time — you precompute inboxes — and the celebrity account is the exception that needs a read-time path instead. That conclusion came out of two divisions. And it is a dramatically stronger opening than asserting you'd use fanout-on-write because that's what feeds do.

Third thing. Service levels, and here the vocabulary does real work.

An indicator is a measured user outcome. Successful checkout completed under five hundred milliseconds. Not database processor utilisation — that's a machine metric, and no user has ever cared about it. An objective is the target on that indicator: three nines of eligible checkouts over a rolling thirty days. And the error budget is simply one minus the objective.

Treat that budget as an actual budget. It funds deliberate risk — faster rollouts, riskier deploys. Targeting perfection is usually economically wrong and always operationally miserable.

Two definitions do most of the work, and most candidates skip both.

Define the eligible population. Do invalid requests count against you? Does a dependency's failure count against you? If you haven't said, your objective doesn't mean anything yet.

And make availability end to end. A success response carrying the wrong shopping cart is not a success. An indicator that can't tell the difference is measuring your servers rather than your product, and that distinction is worth saying unprompted.

While we're here, two more terms that turn vague reliability talk into an actual architecture. Recovery point objective is how much committed data you may lose. Recovery time objective is how long until service is restored. Those two are the only inputs that decide between asynchronous replication, which is cheap but loses data, and synchronous replication, which costs you latency but loses nothing. Ask for both before you draw a second region.

Fourth and last. The distributions, because averages are where designs go to die.

Burstiness. Diurnal peaks, launches, synchronised scheduled jobs, retry storms. Ask what the peak to average ratio is, and if nobody knows, design for five times and say that you're doing it.

Power-law popularity. A handful of celebrity keys carry a wildly disproportionate share of the reads and the fanout. So design for the ninety-ninth percentile account size, not the average follower count — because the average follower count in a social system is a number that describes precisely nobody.

Tail compounding. If a request fans out to fifty dependencies, and each has a one percent chance of being slow, that request is very likely to hit at least one slow call. Which means the tail latency of a fanout system is set by fanout width, not by the average dependency. That's the one to internalise.

And finally, be explicit about which capacity target you're budgeting for. Expected peak, plus failure headroom, plus growth runway are three different numbers. Provisioned for peak, and provisioned for peak with a zone down, are two different systems.

<break time="0.8s" /> So, four things to carry.

Little's Law is the line people forget. Concurrency is arrival rate times time in system, and it sizes everything that holds a connection open.

Do the arithmetic until it forces a conclusion. Read to write of fifty to one is what tells you to pay at write time — you don't assert it, you derive it.

An indicator is a user outcome, measured end to end, with the eligible population defined. Both of those get skipped, and both are cheap points.

And design for the tail, never the average. Fanout width sets your ninety-ninth percentile, and the average follower count describes nobody.
