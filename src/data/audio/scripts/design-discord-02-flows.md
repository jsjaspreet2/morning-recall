---
id: design-discord-02-flows
title: "Discord, part two — two surfaces, and three flows that each end in failure"
source: src/data/designs/design-discord.md §5-6
minutes: 8
---
There are two interfaces in this system, and the split between them is not an implementation detail. It is the design. This episode is that split, and then the three request flows end to end — each of which I want to take all the way to its failure path, because in a system built on long-lived connections the failure path is where the actual thinking lives.

Three things. <break time="0.8s" /> First, the two surfaces and four decisions worth narrating unprompted. <break time="0.7s" /> Second, sending a message, and why publish never precedes the write. <break time="0.7s" /> And third, connecting and presence, where the right answer to two different failures is that nothing happens promptly.

So. Two surfaces. Ordinary request-response over H.T.T.P., and a socket for pushes.

And the first decision is that sends go over H.T.T.P., not down the socket. That surprises people — you already have a socket open, why not use it?

Because a send is request-response. It needs a status code. It needs to be rate limited per route. Push it down the socket and you are now building request correlation, error semantics, and retry logic on top of a transport that has none of them. So the rule is: the socket is for the thing H.T.T.P. cannot do, which is push. Everything else stays where the semantics already exist.

Second decision. The send carries a nonce — a client-supplied idempotency key — and the server echoes it back in the dispatch. That does two jobs at once. The client renders the message optimistically the moment you hit enter, and when the dispatch arrives it matches on the nonce instead of rendering a duplicate. And separately, it makes a retried send safe after a timeout, because the server can recognise it.

Third decision, and this is the load-bearing one. Every push carries a monotonically increasing sequence number, and the client heartbeats back the last one it saw. That pair is what makes resume possible, because the server knows exactly what a returning client missed.

Without a sequence number, every single reconnect is a full state resync. And at fifteen million connections, that is the difference between a routine deploy and an outage. We'll come back to why in the next episode.

Fourth. The client declares its intents on identify — which classes of event it actually wants. Presence is by far the most expensive stream in the system, so letting a client that doesn't render presence opt out of receiving it is a cheap change with an enormous saving. It's the kind of thing that looks like an interface nicety and is actually capacity planning.

Second thing. Sending a message, end to end.

The client posts to the interface service with its nonce. The service evaluates permissions for that user and that channel, and rejects if they aren't allowed.

Now notice where that check sits. It is on the write path, deliberately. If you evaluated permissions per recipient at fanout time, you would be multiplying that check by the fanout ratio — five thousand permission evaluations for one message instead of one. Anything that gets multiplied by fanout belongs on the write side of the system. That's a generalisable instinct.

Then the service mints a snowflake identifier and writes to the message store, partitioned by channel and time bucket. On a successful write — and only then — it publishes to the guild's owning process.

That process resolves which members of the channel are online, groups them by which gateway node holds them, and sends one batched message per node rather than one per session. Each gateway then writes the message to its local sockets, stamping each one with that session's next sequence number.

Now the failure path, which is the interesting part. Suppose the store write succeeds and the publish fails. The message exists, and nobody was told about it.

And the answer is: clients recover on their own. The next resume, or the next time somebody opens that channel, reads from the store — because the store is the source of truth and the push is an optimisation over it.

Then flip the order and see why it matters. If you published first and the write failed, you'd have told fifty thousand people about a message that doesn't exist and never will. That is unrecoverable. So publish never precedes the write, and the reason is not performance, it's that only one of those two orderings has a recovery story.

Third thing. Connecting, and presence — two flows whose failure paths rhyme.

Connecting is straightforward. The client opens a socket and identifies. The gateway authenticates, creates a session, registers it in a shared session registry with a heartbeat time-to-live, and subscribes that session to its guilds' processes. It sends back a ready payload with a resume token and the guild list, then backfills. The client heartbeats roughly every forty seconds with its last sequence number.

Now, the node dies. And here is the decision: sessions are not migrated. They are abandoned.

Their registry entries simply expire by time-to-live, which is what makes those users appear offline without anybody running a cleanup job. The clients notice a dead heartbeat and reconnect — with backoff and jitter, which matters enormously — and resume replays from a short-lived per-session buffer instead of doing a full resync.

Presence works the same way. A session heartbeats, the gateway refreshes the registry entry. On an actual change — a connect, a disconnect, an explicit status set — the gateway publishes a presence event to each of that user's guild processes, and each of those fans it out coalesced and rate limited, rather than immediately.

And now the failure path I like most in this whole design. A user's laptop goes to sleep.

No connection close arrives. Nothing announces the departure. The registry entry just expires, and the guild process emits the offline transition whenever it happens to notice.

So nothing happens promptly. And that is correct. Because a presence system that depends on a clean disconnect is a presence system that is permanently, quietly wrong — laptops sleep, phones lose signal, processes get killed, and none of those send you a polite goodbye. Design for expiry, not for notification.

That's the same instinct as abandoned sessions, and the same instinct as an inventory hold that expires rather than being swept. When the common way something ends is that its owner disappeared, there is nobody left to run your cleanup code.

<break time="0.8s" /> So, three things to carry.

The socket is for what H.T.T.P. can't do. Sends stay on request-response where status codes and rate limits already exist; the socket carries pushes, each stamped with a sequence number so a returning client can be told exactly what it missed.

Permission evaluation goes on the write path, because anything on the fanout path gets multiplied by the fanout ratio.

And publish never precedes the write. A message that exists and wasn't announced is recoverable by any client that reconnects. A message announced and never written is not.

And the one to carry furthest: nothing happens promptly when a session dies, and that's the design working. Expiry beats cleanup whenever the thing that failed is the thing that would have done the cleaning.
