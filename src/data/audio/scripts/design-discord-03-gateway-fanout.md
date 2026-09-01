---
id: design-discord-03-gateway-fanout
title: "Discord, part three — reconnect is the real load, and why the feed answer is wrong"
source: src/data/designs/design-discord.md §7-8
minutes: 9
---
These are the two dives that carry this round. One is about why the routine thing — deploying your own software — is the failure you should design for. The other is about why the most familiar pattern in system design, the one that's correct for a social feed, is actively wrong here.

Two deep dives. <break time="0.8s" /> First, the gateway, and why reconnects rather than connections are the load. <break time="0.7s" /> And second, fanout, where the per-user inbox is the trap.

If you keep one sentence, keep this one: connections are cheap, reconnects are not.

So. The obvious gateway design. Put the sockets behind a load balancer, keep session state on the node, and if a node dies its clients reconnect and get a fresh session. And the supporting argument is true — connections genuinely are cheap. The kernel will happily hold a million of them.

Here's what breaks. The expensive thing isn't holding a connection, it's establishing one.

The ready payload a client gets on connect is large. Guild list, channel list, member and role data, initial presence. It costs a burst of reads and a lot of serialization, and it is the single most expensive response this system produces.

Now drop one node's share of fifteen million clients. That is several hundred thousand simultaneous identifies, each one demanding that most-expensive response. You have generated a thundering herd — and pointed it at your own cold path.

And here's what makes it genuinely bad rather than merely unfortunate. Deploys are routine. So this is not an exotic failure you might see once a year. It is a load you impose on yourself weekly, on purpose. The naive design's failure mode is that a normal deploy looks exactly like an outage — and the retry storm then prevents the fleet from coming back, so it looks like a long one.

Three fixes, and the order matters because they attack different things.

First and most important: resumable sessions. Every dispatch carries a sequence number, the gateway keeps a short replay buffer per session, and a returning client resumes by replaying only the gap. A reconnect inside that buffer window costs a few kilobytes instead of a full ready payload.

Notice what that does. It converts the herd from expensive to cheap without reducing its size at all. Same number of clients, same instant, dramatically less work. And that is the right order to attack a herd in — make each member cheap first, then worry about spreading them out.

Second, client-side backoff with jitter, plus a server-side hint in the close frame telling clients how long to wait. Without jitter, every client waits the same interval and reconnects at the same instant, and you have simply rebuilt the herd on a timer. Jitter is the difference between a queue and a stampede.

Third, roll the fleet rather than restarting it. Take a node out of rotation, close its sessions in batches using a close code that says resumable, and let them land elsewhere over a minute instead of a millisecond.

Now the costs, and there are three worth volunteering.

Replay buffers are memory you hold for clients that are not currently connected. Bounded, but real — and the buffer window is a tunable that trades memory against what fraction of reconnects stay cheap.

Resumability also means a returning client might land on a different node than the one it identified against. So the session registry has to be a shared store rather than node-local state. That's a direct architectural consequence of wanting cheap reconnects, and it's worth naming as such.

And the sequence number is now correctness-critical. A bug that skips one causes silent, permanent message loss for that client until they do a full resync. Silent is the operative word — nothing errors, the user just never sees a message. That's the kind of bug worth building an assertion around.

Second dive. Fanout.

The obvious answer is to treat this like a feed. Fan out on write into a per-user inbox, so that reading is a single-partition scan of your own timeline. This is a genuinely excellent pattern. It is the right answer for a social feed. It is wrong here, and the reason is precise.

Per-user inboxes exist for readers who are absent. The entire point is materializing a read before it happens, so that when someone shows up hours later the work is already done.

But here, the readers are already connected. They are holding a socket open right now.

So you would be writing fifty thousand inbox rows so that fifty thousand people who are online at this instant can each read exactly one of them. That is pure write amplification. At a system rate of five to fifteen million deliveries a second, it becomes the dominant cost in the entire design — and it buys nothing. Worse, it puts a durable write on the latency path of a live message, in a product whose requirement is half a second at the tail.

What replaces it: fan out to sessions, not to storage. Write the message once, to the channel's partition. Delivery is a publish-subscribe push to whichever sockets happen to exist at that instant.

Two refinements do the real work.

One owner per guild. A single process holds the subscriber lists for that guild's channels — which turns "who is online in this channel" from a distributed query into a local set read. And it hands you per-channel total ordering for free, because there is exactly one writer. That's two requirements satisfied by one structural choice.

And then the highest-leverage optimization on the page: batch by node, not by session. The guild process groups recipients by which gateway node holds them, and sends one message per node carrying a recipient list. A fifty-thousand-recipient fanout across a five-hundred-node fleet becomes five hundred inter-service messages instead of fifty thousand. A hundredfold reduction, and it works only because the guild process already knows the session-to-node mapping from the registry.

Then the hot-guild tier. Server sizes are wildly skewed, so a uniform design is necessarily wrong somewhere. A server with five hundred thousand members cannot be one process on one host — its fanout alone saturates a network card. So large servers get sharded fanout: the subscriber set is partitioned across several processes, each owning a slice, and the publish goes to all of them.

But say explicitly that this is a tier, not the general case. Paying that complexity for the median server of forty people is the classic over-design on this problem, and volunteering the distinction is what separates knowing the technique from knowing when to apply it.

Two costs to own. Without a durable inbox, a message sent while you are offline is never pushed to you — you get it when you next open the channel and read from the store. That is entirely fine for chat, and it would be wrong for anything requiring guaranteed per-recipient delivery. It is also exactly why mobile push notifications are a genuinely separate pipeline rather than a flag on this one.

And guild ownership introduces a single point of failure per guild. If that process dies, that server is undeliverable until it restarts elsewhere. That's a real availability tradeoff, and you bought it deliberately in exchange for ordering and locality.

<break time="0.8s" /> So, three things to carry.

Connections are cheap, reconnects are not. Resumable sessions make each member of the herd cheap, which is the right first move — jitter and rolling drains spread it out afterwards.

Per-user inboxes are for absent readers. When the recipients are already holding a socket, materializing a read they're about to make anyway is amplification with no benefit.

And batch by node rather than by session. Fifty thousand deliveries across five hundred nodes is five hundred messages, and that single grouping is the highest-leverage thing on this page.
