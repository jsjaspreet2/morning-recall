---
id: design-ticketmaster-03-dives-a
title: "Ticketmaster, part three — the hold, and concurrency at a hundred and sixty-six to one"
source: src/data/designs/design-ticketmaster.md §7-8
minutes: 9
---
A hold exists for one reason: payment takes human time. The user needs three to ten minutes to find their card and type it in, and for that entire window the seat has to be neither sellable nor sold. That sounds like a small piece of bookkeeping. It is actually where the correctness of the whole system lives, and almost every obvious way to build it is wrong.

Two deep dives. <break time="0.8s" /> First, the hold, and why expiring it is the hard part. <break time="0.7s" /> And second, concurrency — where two different request shapes turn out to need two completely different mechanisms.

If you keep one sentence from this episode, keep this one: correctness lives in the conditional, not in the sweeper. That will make sense shortly.

So. How do you expire a hold? Three obvious answers, and all three are wrong. It's worth knowing why, because an interviewer will offer you one of them.

The first is a background sweeper. A job that runs every thirty seconds and releases anything whose expiry has passed. The problem is that correctness now depends on how far behind that job is. During the thirty seconds before it runs, expired seats are invisible to buyers — which is lost revenue at exactly the moment revenue is scarcest. And if the sweeper dies, inventory silently disappears. Worse still, if holds can also be reclaimed anywhere else, you now have two writers with two different clocks racing on the same rows.

The second is a cache key with a time-to-live, plus keyspace notifications to tell you when it expired. This is fast, and it is genuinely tempting. But those notifications are fire-and-forget — delivery isn't guaranteed. So a single dropped message means a permanently stranded seat. You have made the durability of your inventory contingent on a publish-subscribe message arriving. That is not a trade you want.

The third is a distributed lock with a time-to-live. And the thing to notice here is that this is just a hold with worse properties. It isn't durable, it isn't queryable, it isn't auditable — and you now need the lock service to be as available as the sale itself. You've added a dependency and lost every useful property.

Now the right answer, which is smaller than all three. Lazy expiration. Never actively expire anything at all.

Instead, make the expiry a predicate that every write evaluates. One statement. Set the seat to held, with a fresh hold identifier and a fresh expiry — but only where the status is currently available, or where it's held and the expiry has already passed.

That's it. And look at what it buys you. An expired hold is automatically claimable by the next writer, atomically, in the very same statement that claims it. There is no window. There is no lag. There is no sweeper anywhere in the correctness path.

And when that statement comes back having changed zero rows, that is not an error. That is the protocol working. It means the seat genuinely isn't yours, and the honest thing to do is tell the user so.

You do still run a sweeper — but only for interface freshness and for reporting. Never for correctness. If it falls behind, nothing breaks; the seat map is just briefly pessimistic. And say that distinction out loud, because it's exactly the layering an interviewer is listening for. Correctness is in the conditional. The sweeper is a cosmetic optimisation.

One follow-up worth pre-empting before it's asked. What happens if the user is mid-payment when the hold expires? Transition the hold into a pending-payment state when the order is submitted, which suspends expiry — with a hard ceiling of a couple of minutes, so that a hung payment provider can't strand a seat forever. The general principle is worth stating in its own right: expiry protects inventory from abandoned users, so it should pause when the user has demonstrably not abandoned.

Second dive. Concurrency. And here's the mistake almost everyone makes — treating these two request shapes as the same problem.

Case one. The user picked specific seats. Here contention is naturally spread, and plain optimistic concurrency is the right answer. A hundred and sixty-six users race for seat twelve A. One wins. The other hundred and sixty-five get zero rows affected, and a clean message: that seat just went, here's an updated map.

And that is fine. Genuinely fine — because those hundred and sixty-five users wanted that specific seat. Telling them it's gone is a truthful answer, not a failure. Their retries scatter naturally across other seats.

For a multi-seat order you need all or nothing, so wrap the conditional updates in one transaction. And acquire them in a deterministic order — sorted by seat identifier — so that two users grabbing overlapping sets in different orders can't deadlock each other. That ordering detail is cheap to say and it signals a lot.

Case two is where it gets interesting. Best available, four seats together.

Now optimistic concurrency degrades badly, and it degrades in a specific way. Every request runs the same query. Every request identifies the same best seats. One wins, a hundred and sixty-five fail — and then all hundred and sixty-five retry and immediately collide on the new best seats. You have built a retry storm that gets worse as inventory shrinks.

So you reach for pessimistic locking instead. Select the best four available seats, for update. And that's worse. Now a hundred and sixty-six transactions are queued on the same four rows, one behind the other. You've converted a storm into a traffic jam.

The fix is one clause: skip locked. It tells the database to ignore any rows another transaction is currently holding, and take the next ones instead. So concurrent requests fan out across distinct rows rather than queueing on identical ones. Throughput now scales with concurrency instead of collapsing under it.

That single clause converts a serialisation bottleneck into parallel work, and it is the highest-signal detail on this entire problem. It's also the same primitive that makes database-backed job queues work, so it's worth having in your vocabulary generally.

Volunteer the cost, because there is one. You get a good set of seats, not provably the best available — because another transaction may be holding better ones that it later abandons. That's an entirely acceptable product trade, and saying so demonstrates that you know it is a trade rather than that you got lucky.

One more piece. Four together is a contiguity constraint, not a top-four query. So precompute contiguous blocks per row, or keep a per-row availability bitmap and scan it for consecutive set bits. That's cheap, because a row is only about forty seats wide.

Finally, the question you'll get asked: why not just do reservations in memory, in a cache? And you can — at extreme contention it's genuinely attractive, because a script executes atomically, so check-and-set on seat state is trivially race-free and far faster than a database transaction.

The catch is durability. Append-only logging that flushes once a second can lose up to a second of writes on failover.

The clean way to have both is to split by recoverability. The cache is authoritative for holds. The durable store is authoritative for sales. Losing a hold on failover is recoverable — the seat simply reverts to available and the user re-picks. Losing a sale is not. So the order commit goes through the durable store, always.

And that reasoning — splitting durability requirements by how recoverable each piece of state is, rather than picking one store for everything — is what makes this a strong answer instead of a risky one.

<break time="0.8s" /> So, three things to carry.

Never actively expire a hold. Make the expiry a predicate inside the claiming statement, so an expired hold is reclaimed atomically by whoever wants it next. Correctness is in the conditional; the sweeper is cosmetic.

Two request shapes, two mechanisms. Specific seats spread contention naturally, so optimistic concurrency is fine. Best-available collapses every request onto the same rows, and skip locked is what converts that bottleneck back into parallel work.

And split durability by how recoverable the state is. A lost hold is an inconvenience. A lost sale is a business-ending bug. Those two do not belong in the same store.
