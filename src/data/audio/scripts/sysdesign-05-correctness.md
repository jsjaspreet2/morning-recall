---
id: sysdesign-05-correctness
title: "Correctness under concurrency — the invariant, the fencing token, and write skew"
source: src/data/guides/system-design.md — Protect correctness under concurrency
minutes: 9
---
Here's a question that sorts people quickly. Two users try to buy the last seat at the same instant. What stops both of them succeeding? Most answers reach straight for a mechanism — a lock, a transaction, a queue. This episode is about why that's the wrong first move, and what the right first move is.

Four things. Start with the invariant. Then the toolbox, in ascending order of cost. Then the one isolation anomaly you have to be able to describe. And finally money, which is the special case that comes up constantly.

So, the invariant. Before you choose any mechanism at all, name the thing that must never be false, and name it in the product's language, not the database's.

Inventory never goes negative. One booking per slot. Ledger entries balance. A message edit must not overwrite a later edit.

Now pick the cheapest mechanism that enforces that at the authoritative boundary. And here's the line worth keeping: almost every over-engineered concurrency answer comes from skipping that sentence. Someone reaches for a distributed lock when a unique constraint would have done the whole job.

That brings us to the toolbox. Six mechanisms, and they're in order of cost, so you want to reach for the earliest one that actually works.

The cheapest is an atomic statement. One update that decrements the quantity only where the quantity is still positive, and then you check how many rows came back. Zero rows means the seat genuinely isn't yours. That's the protocol working, not an error. Reach here first, every time. It costs nothing worth mentioning.

Second, a constraint. Unique, exclusion, check, foreign key. Use this when the invariant is structural. What it costs you is that races now surface as explicit errors you have to handle — which is usually an improvement, because the alternative is a race you don't find out about.

Third, optimistic concurrency. Compare a version or an entity tag, and either retry or hand back a conflict. Right when contention is low. At high contention you get a retry storm, and the retries make the contention worse.

Fourth, a pessimistic lock. Lock the row or the range inside a short transaction. Right when contention is hot and predictable. It costs you deadlocks, throughput, and the discipline of never holding a lock across anything slow.

Fifth, a serialized actor — one logical executor per key. Right when ordering and contention both dominate. It costs latency, ownership, and a real recovery story when that executor dies.

And sixth, a distributed lock — a lease held across systems. Genuine last resort, for a real cross-system critical section.

If you take the distributed lock, there's one detail that separates people who have read about them from people who have debugged one. A lease can expire while its holder is paused — garbage collection, a slow disk, a stopped process. That holder wakes up still believing it owns the lock. So the lock needs a fencing token: a number that only ever increases, handed out with the lease, and validated by the protected resource itself. Not by the client. The resource. Without that, the zombie holder still writes, and it writes over the top of whoever legitimately took the lock next.

Third thing on my list. Transaction isolation, and specifically the one anomaly to be able to describe cold.

Read committed means each statement sees committed data. Sounds safe, and read-modify-write still races underneath it. Repeatable read, or snapshot, gives your transaction a stable snapshot — and write skew is still possible, depending on the database. Serializable is equivalent to some serial execution, and you pay for it with aborts, retries, and lower throughput.

Now, the habit worth building: name the anomaly you're preventing. Lost update. Write skew. Phantom. Do not reach for the phrase strong consistency — it isn't an isolation level and it doesn't answer the question that was asked.

Write skew is the one to be able to describe. Two transactions each read a state that's perfectly valid. Each makes a change that is individually fine. And together they violate an invariant that neither transaction could see. The canonical example is the doctor on call: two doctors are on call, each checks that the other is still on call, each takes themselves off, and now nobody is. Each read was valid. Each write was fine. The hospital has no doctor. And snapshot isolation does not prevent it — that's the part people get wrong.

Fourth and last. Money and inventory, the highest stakes special case.

Keep an append-only ledger. Balances are derived from it, or materialized from it, but never authored directly. Never overwrite financial history. An update statement against a balance column is an audit failure, not a design choice.

Reserve with an expiry, then confirm or cancel. That reservation is the thing that makes overselling impossible without holding a database lock for the entire length of a human checkout flow. It converts a locking problem into a state machine with a timer, and that is almost always the right trade.

Separate authorization, capture, refund, and settlement into genuinely distinct states, and reconcile against the external provider. They will disagree with you. Your design needs a place to put that disagreement, and if it doesn't have one, somebody finds out from a customer.

And audit every transition — actor, request identifier, operation identifier, timestamp, and reason. When money moves and nobody can say why, the design was wrong regardless of whether the numbers came out right.

So, four things to carry.

Name the invariant in the product's language before you touch a mechanism, because most over-engineering starts by skipping that sentence.

Reach for the cheapest mechanism that enforces it — the atomic conditional update first, the distributed lock genuinely last.

If you do take a distributed lock, it needs a fencing token that the resource validates, because a paused holder wakes up still believing it owns the lease.

And name the anomaly, not the adjective. Write skew is two individually-valid changes that together break an invariant neither one could see, and a snapshot won't save you from it.
