---
id: design-discord-05-storage
title: "Discord, part five — a migration about pauses, and no broker in the delivery path"
source: src/data/designs/design-discord.md §11-12
minutes: 8
---
There's a migration in Discord's history that people quote for the wrong reason. They moved from one wide-column store to another and the node count dropped from a hundred and seventy-seven to seventy-two, and everyone remembers that as a capacity win. It wasn't. It was a latency story wearing a capacity story's clothes, and understanding which is which is the point of this episode.

Three things. <break time="0.8s" /> First, message storage, and why the access pattern picks the store. <break time="0.7s" /> Second, the partition key, and a hot shard that's intentional. <break time="0.7s" /> And third, every remaining stateful component with a named choice, including one where the right answer is to have no component at all.

So. Message storage. The obvious answer is a relational store, partitioned by channel, with an index on time. Reasonable instinct, and it's what most people reach for.

What breaks is that at trillions of rows, the access pattern turns out to be narrow and brutal. It is always a range scan over exactly one channel. Always descending by identifier. And almost always the single most recent page.

That is a wide-column workload. And a relational store's generality — joins, ad-hoc queries, flexible indexing — is cost you are paying for and never using. When the access pattern is that narrow, generality is overhead.

Discord's actual path was document store, then Cassandra, then Scylla. And the reported reason for that last hop is the detail worth carrying: garbage collection pauses in the Java runtime were showing up in tail latency at that scale. Not throughput. Not capacity. Pauses.

The cluster went from a hundred and seventy-seven nodes to seventy-two — but the driver was that the tail got quiet, and the smaller footprint came along for the ride. If you quote this in a room, quote it that way round, because the interviewer will know the difference.

Now the replacement. A wide-column store, partitioned by channel and a time bucket together, clustered by message identifier descending.

Three things about that key, and each one is a decision.

Why a compound key rather than just the channel? Because a busy channel would otherwise grow one partition without bound — and an unbounded partition is precisely the failure mode this class of store punishes hardest. Bucketing caps partition size, and it makes "give me the most recent page" a single-partition read of the newest bucket.

Why does the bucket have to be coarse? Because if it's too fine, reading a quiet channel's last fifty messages means scanning across a great many empty buckets to find them. So the bucket width is a real tuning knob, played against the channel's message rate — and getting it wrong in either direction produces an observable regression. Too wide and partitions bloat; too narrow and quiet channels get slow.

And why do snowflake identifiers make this work? Because the clustering key already encodes time. So pagination is just "give me messages with an identifier less than this one." No secondary index. No separate sort. The identifier scheme chosen back in the entity model is what makes the storage layer simple, and that connection is worth pointing at explicitly.

The costs are real and you should volunteer them. Wide-column means no joins and no ad-hoc queries — every access pattern has to be designed in advance, and a genuinely new one means a new table and a backfill. Search is therefore a completely separate system, fed asynchronously.

And the migration itself is the honest expense. Dual writing, historical backfill, and a verified cutover. Discord did it without downtime, and that is weeks of engineering, not a configuration change. Saying so signals you've done one.

Second thing. The hot shard, and whether it's intentional.

A single very busy channel concentrates its writes on one partition at a time — the newest bucket. Every message goes to the same place.

That is intentional, and it is acceptable. Here's the arithmetic that makes it acceptable: a hundred and fifty thousand writes a second across the entire system means even a pathologically hot channel is only a few thousand writes a second. One partition handles that comfortably.

But say where it stops being acceptable, because that's what turns an assertion into a derivation. If the write rate were two orders of magnitude higher, this would break — and the fix would be a synthetic sub-key inside the bucket, spreading writes across several partitions, paid for with a merge at read time. You're not doing that. You're explaining why you're not.

Third thing. Every remaining stateful component, quickly, each with one sentence of derivation. Skipping these is what reads as shallow; the trick is deriving each one fast.

Messages: the wide-column store, for the reasons just covered.

The session registry: an in-memory store, fifteen million keys, high churn, and losing it is survivable. The sentence is that the time-to-live is the design, not a cleanup mechanism — a dead node's sessions have to expire, because nothing is alive to delete them.

Presence: the same keys, the same heartbeat expiry, coalesced at the guild process. And note the choice: presence is derived from the session expiry rather than stored separately, so there is exactly one source of truth about whether somebody is alive. Two sources of liveness truth is two sources that can disagree.

Server and channel metadata, and roles: relational, cached aggressively at the interface tier. Small, read-heavy, read on every permission check, and it has to be correct. That's the part of this system that actually is a database problem, and it's worth saying so — because it makes clear you understand the rest of the system isn't.

Read state: the wide-column store again, keyed by user and channel, written behind. The biggest table in the product by rows, and the first place you'd trade durability for write cost.

Attachments: an object store behind a content delivery network, with only the pointer in the message row. Bytes never travel through the gateway.

And then the interesting one. Inter-service fanout: publish to a topic per server, in memory, at most once — and the component is the guild process itself. There is no broker.

That's worth dwelling on, because a broker is the reflexive answer and it's wrong here. Adding one would put a durable hop in the middle of a delivery path that is explicitly, deliberately not durable. You would be paying for a persistence guarantee on a message whose entire recovery story is "the client reconnects and reads from the store."

Choosing to have no component is a design decision, and it's one you have to justify out loud, or it looks like an omission.

<break time="0.8s" /> So, three things to carry.

The access pattern picks the store. One narrow descending range scan per channel is a wide-column workload, and the migration people remember for node count was actually about garbage collection pauses in the tail.

Bucket the partition key, and make the bucket coarse. Unbounded partitions are the failure this store punishes hardest, and snowflake identifiers mean pagination needs no secondary index at all.

And no broker in the delivery path. Fanout is explicitly not durable, so a durable hop would be paying for a guarantee the design has already decided it doesn't want.
