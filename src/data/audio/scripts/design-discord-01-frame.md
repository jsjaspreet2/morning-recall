---
id: design-discord-01-frame
title: "Discord, part one — ingest is trivial, fanout is not"
source: src/data/designs/design-discord.md §0-4
minutes: 9
---
Here is the mistake that costs people this round, and it happens in the first five minutes. You hear chat, you hear billions of messages, and you start sharding the message table. You have just designed the easy half of the problem and spent your best twenty minutes on it.

Discord's message write rate is unremarkable. A few tens of thousands a second. A single well-partitioned cluster handles that without an argument. The numbers that actually matter are the connection count and the delivery count, and those are two and three orders of magnitude larger.

Four things. <break time="0.8s" /> First, the frame, and the contrast that stops you designing the wrong system. <break time="0.7s" /> Second, requirements, and the one sentence that earns the point. <break time="0.7s" /> Third, the numbers, where three of them reframe everything. <break time="0.7s" /> And fourth, the entities, where two design decisions are hiding in field definitions.

So, the frame. Discord is several products sharing one connection — text, voice, presence, roles, search. Scope to text messaging plus presence over a persistent gateway, because that is where the constraint lives.

Two things dominate.

The recipients are already connected. This is not a mailbox problem. A message published to a channel has to become socket writes to everyone in that channel who is online right now — and the fanout ratio, not the write rate, is what sizes the system.

And the connection is stateful and long-lived. Which means the interesting failures are not slow queries. They are a deploy dropping four million sockets at once, and every one of those clients reconnecting and asking for a full state resync.

Now the contrast worth having ready, because it stops an interviewer steering you into a mailbox design. Take a mobile messaging product like WhatsApp. Same archetype, opposite constraint. There, recipients are mostly offline, fanout goes to a handful of devices, and the hard problems are delivery semantics, ordering, and the catch-up queue.

Here, recipients are online right now, fanout goes to thousands, and the hard problem is that one message becomes fifty thousand socket writes.

And this is the part to say out loud: the mobile messaging answer — durable per-recipient queues — is not merely unnecessary here, it is actively wrong. You would be writing fifty thousand queue entries for a message that fifty thousand people are already holding a socket open to receive. Naming that inversion early is worth a lot.

Second thing. Requirements.

Three functional ones. A user opens a client and receives, in real time, messages sent to any channel they can see, across every server they belong to, over one connection. A user sends a message to a channel and it is durably stored and delivered to every online member. And a user's status propagates to everyone who would care — which is every member of every server they belong to.

Out of scope, said out loud: voice and video, which is a genuinely different system, and search, and moderation. But note one careful exclusion. Roles and permission administration are out. Permission evaluation stays in — because it gates fanout, and anything that gates fanout is on the critical path here.

On the non-functional side, the ones that carry weight. Delivery latency from sender to online recipient under five hundred milliseconds at the tail, because under that threshold a conversation stops feeling live, and this is a chat product. Around fifteen million concurrent connections at peak. No acknowledged message may ever be lost, because users scroll back years. Ordering is total within a channel and nonexistent across channels. And a whole gateway node's clients must reconnect within sixty seconds without cascading — because deploys happen, and that is the routine failure, not the exotic one.

Here is the sentence that earns the point. The only hard consistency requirement in this system is per-channel ordering, and I get that for free by having a single writer per channel. Everything else — presence, read state, unread counts — is allowed to be eventually consistent, and I am going to spend that slack deliberately.

Third thing. The numbers. Three of them reframe the problem.

Fifteen million concurrent connections at peak. At even ten kilobytes of per-connection state, that is a hundred and fifty gigabytes of memory across the fleet before a single message moves. Connections, not messages, size the gateway.

Four billion messages a day is about forty-six thousand a second average, call it a hundred and fifty thousand at peak. That is a small write rate. And that is precisely the number that misleads people into designing the wrong system.

The fanout ratio is the real number. A message in a channel with five thousand online members is five thousand socket writes. Across the system, deliveries run one to two orders of magnitude above sends — somewhere in the range of five to fifteen million deliveries a second at peak. Every architectural decision on this page follows from that ratio, and none of them follow from the hundred and fifty thousand.

And then presence, which outruns messages entirely. One user coming online, in twenty servers averaging two thousand online members each, generates forty thousand delivery events. From a single state change. Multiply that by login churn and presence is plausibly the highest-volume event type in the entire system.

Two more worth carrying. Discord stores trillions of messages, and they publicly moved from a hundred and seventy-seven Cassandra nodes to seventy-two Scylla nodes — and the migration was driven by garbage collection pause latency, not by throughput or capacity. That's a useful detail because it's a latency story wearing a capacity story's clothes.

And server size is wildly skewed. The median server is a few dozen people. The largest run to hundreds of thousands. Which means a uniform design is necessarily wrong at one end or the other.

Fourth thing. Entities — and two of them have a design decision buried in a field.

A message identifier is a snowflake: a sixty-four-bit number whose high bits are a timestamp. So it sorts by time, it carries its own creation time, and it can be minted without a round trip to anything. Three properties for the price of one field.

A session carries a resume token and the last sequence number the client acknowledged. That pair is what turns a reconnect from a full state resync into a replay — and at fifteen million connections, that distinction is the difference between a deploy and an outage.

And presence has a time-to-live and no delete path at all. A session that stops heartbeating expires, rather than being cleaned up. And the reasoning is worth stating: the common way a session ends is that its node died. There is nobody left to run the cleanup. So don't design a cleanup path — design an expiry.

Three of these are load-bearing. Session, because its count is fifteen million and its state has to be reconstructible after its host disappears. Channel, because it is the unit of both ordering and fanout — the same key partitions the message table and addresses the publish-subscribe topic, and that is not a coincidence, that is the design. And presence, because it is the highest-volume entity and the only one where the correct answer is to be deliberately lossy.

<break time="0.8s" /> So, four things to carry.

Ingest is trivial and fanout is not. A hundred and fifty thousand writes a second is easy; five to fifteen million deliveries a second is the system.

The recipients are already connected, so durable per-recipient queues are actively wrong here — you'd be writing fifty thousand rows for a message fifty thousand people are already waiting on a socket for.

Per-channel ordering is the only hard consistency requirement, and a single writer per channel gives it to you for free. Everything else is slack you spend on purpose.

And presence is the highest-volume event type in the system, not a nice-to-have. One person logging in can be forty thousand delivery events.
