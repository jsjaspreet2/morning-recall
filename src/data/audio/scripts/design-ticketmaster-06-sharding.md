---
id: design-ticketmaster-06-sharding
title: "Ticketmaster, part six — the deliberate hot shard, and a queue allowed to lose data"
source: src/data/designs/design-ticketmaster.md §12
minutes: 9
---
This is the episode where two sections that most candidates present as unrelated components turn out to be the same argument. The sharding decision and the waiting room are not two features. One of them exists because of the other. If you can state that link before you're asked, you've demonstrated something most people don't.

Three things. <break time="0.8s" /> First, what the sharding is actually sized by, which is not what you'd guess. <break time="0.7s" /> Second, the storage decisions, quickly, because every stateful component needs a named choice. <break time="0.7s" /> And third, the queue durability tension — a component deliberately built on infrastructure that loses data, and why that's correct.

So. You shard by event. Every seat, every hold, every order for one event lives on one shard.

But the interesting question isn't whether you shard. It's what the sharding is sized by — because there are two possible answers, and they give you different keys, different shard counts, and completely different failure behaviour.

If you shard for throughput, your key is a hash of the seat or order identifier. Your shard count comes from total writes divided by node capacity. Load distributes evenly, which is what hash distribution is for. But a multi-seat order now spans shards, so it becomes a distributed transaction. And a node failure degrades every event a little.

If you shard for isolation, your key is the event — because that is the transactional boundary. Your shard count comes from how many concurrent hot events you need to isolate from each other. Load distributes wildly unevenly, by design: one shard pinned while a thousand sit idle. A multi-seat order is a single-shard transaction. And a node failure kills one event completely, while every other event carries on untouched.

Now, which one? Recall the global write volume is fifty to a hundred thousand a second spread across about fifty shards. Nobody needs a clever partitioning scheme to survive that. So throughput is not the driver here. Isolation and transactional locality are, and both of them point at the event.

And here's the consequence you have to own, out loud, rather than waiting to be caught by it. An event cannot be split. So that shard's capacity is a hard ceiling on how fast the event can possibly sell.

Which is exactly why the waiting room exists.

Admission control is not a user-experience feature. It is the mechanism that makes demand fit an unsplittable shard. Those two sections are one argument, and connecting them unprompted is worth more than either one alone.

Three mitigations for the hot shard, in order.

First, dedicated capacity for known-hot events. You know the schedule weeks ahead of time. So this is a scheduling problem, not a runtime one — and this is a rare case where the operational answer genuinely beats the architectural one. Saying that is a point in your favour, because most candidates reach for a mechanism when a calendar would do.

Second, sub-partition by section, if a single event truly exceeds one node. You accept that cross-section orders become multi-partition. But note honestly that this doesn't help the common case, because contention concentrates in the good sections. Splitting the stadium doesn't split the demand.

Third, read replicas for anything analytical, and never for the sale path.

The generalisable version, worth carrying to other problems: partition on the entity that bounds your transactions, unless throughput genuinely forces you off it. Hash distribution optimises the metric that's easy to measure, which is evenness, at the cost of the one that actually determines your correctness cost, which is locality.

Second thing. Storage decisions, fast — because every stateful component needs a named choice and a one-line derivation, and skipping them is what reads as shallow.

Seat inventory is relational, sharded by event. And the reason is specific: skip-locked and transactional multi-row acquisition are the whole design. Those are relational features. A key-value store cannot give you either one — which is precisely why it matters so much that the write volume is small.

Holds live on the same rows as inventory. Not a separate store. A hold is a state on the seat, not an object in its own right, and splitting it across two stores means two systems can disagree about one seat.

The availability bitmap lives in the availability service's own memory and publishes to a content delivery network. Queue and session tokens are stateless — signed, self-describing, never looked up — which is what lets the queue tier hold no per-user state and absorb the herd on cheap nodes.

Orders and payments sit on the same shard as the event, which makes the sale commit a single-shard transaction with the inventory. And the outbox is a durable log, so availability updates, ticket issuance, and analytics all fan out from one commit without coupling to it.

Third thing, and this is the best part. The queue keeps its counter and its watermark in an in-memory store that can lose writes. Say this before you're asked, and be precise about it.

Writes are lost two ways. Asynchronous replication means the primary acknowledges your increment before shipping it to a replica, so a primary that dies in that window takes those writes with it. And a once-per-second disk flush means a restart loses up to a second — that's where the one-second figure comes from.

Now, what happens during the outage? The line stops. New arrivals get no position. Waiting clients can't learn their position and back off. And that is correct — you fail closed on both. Nobody is admitted who shouldn't be, and the degradation is simply that the queue stalls, which is the most benign failure this component can produce.

But here is the property that makes the whole approach defensible. This is not a revenue outage, because the session token is stateless. Anyone already admitted holds a signed token that the booking service validates by signature and expiry, with no lookup at all on the hold path. Those people keep buying straight through the incident.

The store going down stops new admissions and nothing else. That is the single most important property of this design, and it's the reason you're allowed to run the queue tier on lossy infrastructure in the first place.

Now, what does each rewind cost? Not the intuitive answer — the counter is the worse of the two.

If the admitted watermark rewinds, it re-advances through positions it already covered. But those users already hold their tokens. So re-admitting them is a no-op. That's idempotent replay, not over-admission. The cost is a temporary stall in the effective admission rate while it re-covers ground. Low severity.

If the position counter rewinds, the next arrivals are issued positions that were already assigned to other people. And when the watermark later passes one of those duplicated positions, both users get admitted. That is genuine over-admission, bounded by the loss window times the arrival rate. Moderate.

And even that bad case is survivable, for the reason that runs through this entire design. Over-admission adds load to the booking tier and degrades latency. It cannot cause a double sale — because the conditional update is still the only thing that decides who gets a seat. Contention, never corruption.

Two concrete fixes. Reserve counter positions in large blocks and persist that ceiling, so on recovery you resume above anything that could have been issued. The cost is gaps in the sequence, and nobody can observe those, because a position is a display value and not an inventory. Or persist the watermark every few hundred milliseconds and resume from the last persisted value — deliberately replaying rather than estimating forward. Replaying is idempotent. Guessing ahead is not.

<break time="0.8s" /> So, three things to carry.

Shard for isolation, not throughput. The event is the transactional boundary, the load is deliberately uneven, and one shard being pinned while a thousand sit idle is the intended outcome rather than a flaw.

An event can't be split, so its shard is a hard ceiling — and admission control is the mechanism that makes demand fit that ceiling. Those are one argument, not two components.

And the fast path is allowed to be lossy precisely because a durable check sits behind it, and because the credential it issues is self-validating. Losing the issuer does not invalidate what it already issued.
