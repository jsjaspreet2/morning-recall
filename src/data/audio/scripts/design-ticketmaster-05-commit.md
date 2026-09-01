---
id: design-ticketmaster-05-commit
title: "Ticketmaster, part five — optimistic hints, the payment saga, and bots"
source: src/data/designs/design-ticketmaster.md §10-11
minutes: 8
---
Two things left that decide whether this design survives contact with reality. One is how you answer five million people asking which seats are left. The other is what happens when money enters the picture — and, unusually for a system design problem, what happens when some of your users are actively hostile.

Three things. <break time="0.8s" /> First, the read path, and a sentence about staleness that's worth memorizing. <break time="0.7s" /> Second, the payment saga, where the order of operations is the entire answer. <break time="0.7s" /> And third, bots, which are a first-class requirement here rather than an afterthought.

So, five million queries a second asking which seats are left.

The rule is: never answer that per user from the database. Not with a read replica, not with a clever index. Compute one artifact and broadcast it.

That artifact is a bitmap indexed by seat ordinal, plus a monotonically increasing version number. One bit per seat — selectable or not — is about seven and a half kilobytes for a stadium. Two bits, distinguishing available from held from sold, costs fifteen kilobytes and buys you a noticeably better onsale interface plus room for a fourth state later.

Pick either one, say which you picked and why, and then move on. The design does not hinge on that choice, and treating it as though it does is a tell — it signals you're optimizing the thing you know how to optimize rather than the thing that's hard.

The client already has the static seat topology cached, so all it does is overlay status onto geometry it already has.

For distribution, publish that bitmap to an edge cache with a one to five second expiry, so every request inside that window costs the origin nothing. During a live onsale, additionally push deltas over a socket — only the seat ordinals that changed, which is a few hundred bytes even at peak churn. Any client that misses a delta notices the version gap and resyncs by refetching the whole bitmap.

Now the important part, and it's a mindset rather than a mechanism. Staleness here is a feature you design around, not a bug you apologize for.

Users will click seats that are already gone. That is not a defect. It is the unavoidable consequence of ten million people looking at a shared resource, and no amount of engineering removes it. The correct handling is a fast, honest failure from the hold endpoint, plus an immediate map refresh. It is not an attempt to keep ten million clients consistent.

Here's the line to have ready. The seat map is an optimistic hint with a well-defined staleness bound. The hold endpoint is the only source of truth, and the interface is built to lose that race gracefully.

Candidates who try to make the read path strongly consistent end up designing something that cannot work at this volume — and the interviewer usually knows it several minutes before they do.

Second thing. The payment saga. And the order of operations here is not a detail, it is the whole answer.

Hold, which is cheap and reversible. Then authorize, which is still reversible. Then commit the sale, which is durable. Then capture, which happens afterwards and asynchronously.

Charge before you have secured inventory and you produce the single worst failure this system can produce: a charged customer with no seat, resolved by a refund and a support ticket and a very bad day for somebody. Always take the reversible action first — same principle as splitting hold from order, one layer down.

Now compensation, and note that it is asymmetric in a way that's worth explaining.

If the sale commit fails after a successful authorization, void the authorization. Clean rollback, nobody is charged, the seat returns to available.

But if the capture fails after the sale has already committed — keep the sale. Retry the capture out of band. The customer is in the building either way, and reversing a confirmed ticket is a far worse outcome than chasing a payment through your finance team.

That asymmetry is the interesting bit. The compensating action is not the mirror image of the forward action, because the business consequences aren't symmetric. Compensation is a business decision, not a database rollback.

Third thing. Bots.

This is unusual. In most system design problems, adversarial users are somebody else's department. Here they are a first-class requirement, and the purely technical answer is insufficient on its own.

Four measures, in roughly ascending order of how much they actually work.

Purchase limits enforced at order commit, keyed on the user, the payment instrument, and the device — three different things, because a bot operator will happily create a thousand accounts sharing one card. And enforce them at commit, never in the interface, which is trivially bypassed by anyone who can open developer tools.

Proof of work, or a challenge, at queue entry rather than at purchase. This is the one people get backwards. You want the expensive step to be the one a bot must do ten thousand times, not the one it does once after already winning.

Account age and verification gates, and presale codes. This is what the industry actually relies on, and the reasoning is worth stating: you move the scarcity onto an identity that can't be cheaply minted. If the bottleneck is a verified account with history, the arms race moves somewhere you can actually police.

And rate limits on the availability endpoint. Scrapers hammering the seat map are a meaningful slice of that five million queries a second, and they are also the cheapest traffic you will ever shed — nobody's purchase fails because you throttled a scraper.

<break time="0.8s" /> So, three things to carry.

Compute one artifact and broadcast it. The seat map is an optimistic hint with a defined staleness bound, the hold endpoint is the only truth, and the interface is built to lose that race gracefully.

Order of operations is the payment answer. Hold, authorize, commit, capture — reversible before irreversible. And compensation is asymmetric: void a failed sale, but keep a sale whose capture failed, because the customer is in the building either way.

And put the cost where the bot has to pay it repeatedly. A challenge at queue entry beats a challenge at purchase, and moving scarcity onto a verified identity beats both.
