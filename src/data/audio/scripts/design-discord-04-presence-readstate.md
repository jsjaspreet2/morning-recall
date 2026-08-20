---
id: design-discord-04-presence-readstate
title: "Discord, part four — presence nobody scopes, and the biggest table in the product"
source: src/data/designs/design-discord.md §9-10
minutes: 8
---
These are the two subsystems candidates skip. Presence gets waved away as a small feature attached to messaging. Read state gets waved away as a column. Both are wrong, and in the same direction — each is larger than the thing it's attached to.

Two deep dives. <break time="0.8s" /> First, presence, which is plausibly the highest-volume event stream in the entire system. <break time="0.7s" /> And second, read state, which is the largest table in the product by row count — larger than messages.

So, presence. The obvious answer is that it's a boolean in a table, and when it changes you tell everyone who cares.

Here's what breaks, and it's just arithmetic. One user, in twenty servers averaging two thousand online members each, produces forty thousand delivery events. From one bit flipping.

And people flip that bit constantly. Laptops sleep. Phones background. Networks change on a train. That bit is not a rare event, it is the most frequently changing state in the product.

So presence is not a small feature attached to messaging. It is plausibly the largest event stream in the system — and treating it with messaging's delivery guarantees means paying messaging's cost, for data that will be stale one second later.

Three moves fix it, and all three are the same move: be deliberately lossy.

First, heartbeat with a time-to-live, and never an explicit delete. Online means "has heartbeated within the window." And I want to be careful here, because this sounds like an optimisation and it isn't. It is the only correct model. The common way a session ends is that its host disappeared — so there is nothing left to send you a goodbye. A design that requires a clean disconnect is permanently, quietly wrong about some fraction of its users, forever.

Second, coalesce and rate-limit at the guild process. Presence changes within a window collapse into a single event, so a user whose connection is flapping produces one transition rather than thirty.

And the justification is worth memorising, because it generalises. A stale presence is invisible to users. A presence storm is not. Nobody notices that their friend showed online three seconds late. Everybody notices when the app stutters.

Third, don't send what nobody will render. A client displaying a two-hundred-thousand-member server is not rendering two hundred thousand avatars — it renders a screenful and asks for more when you scroll. So presence for large servers is lazy, and scoped to what the client actually asked for. That is exactly what the intents field exists to express.

Now the cost, and state it as a trade rather than letting it be discovered. Presence is now eventually consistent and briefly wrong — somebody can appear online for up to the full time-to-live after they've actually vanished.

Here's the sentence. I am choosing to be wrong about presence for up to thirty seconds, in exchange for not paying messaging's delivery cost on the highest-volume event in the system.

Lazy presence has a second cost that's worth naming because it's a product consequence rather than a technical one. A client's view now depends on what it happens to have subscribed to. So "why does my friend show offline on my phone and online on my desktop" becomes a real support burden — and an acceptable one, but you should be the person who said it first.

Second dive. Read state.

The obvious answer: store the last-read message identifier per user per channel, and update it when they read.

What breaks is cardinality. Read state is per user, per channel. That makes it the largest table in the product by row count — larger than the messages table itself. And it is written far more often than it is read, because every channel switch and every scroll to the bottom is a write.

It's also latency-sensitive in a way messages simply aren't. Unread badges are the first thing rendered when the app opens. So a slow read state query is a slow app launch — not occasionally, but on every single launch, for every user.

What replaces it is three decisions.

Store the last-read message identifier, not a count. Because identifiers are snowflakes with time in the high bits, "is this unread" becomes a comparison, and "how many unread" becomes a bounded count against the channel partition. There is no counter to keep consistent and therefore no counter to drift. That's a lovely consequence of the identifier choice made several episodes ago, and it's worth pointing at.

Write behind, aggressively. Coalesce a user's read state updates over a few seconds and batch them. And price the failure honestly: losing the last few seconds of read state in a crash costs one user one already-read channel showing a badge. That is the cheapest possible failure in this entire system. Trading durability for write cost is obviously right here, and it's obviously wrong two tables over on messages — knowing which is which is the skill.

And put a coalescing cache in front of the hot path. When a large number of clients request the same hot partition at the same moment, the service in front should recognise them as one request, issue a single query, and fan that single result back to every waiter.

Notice the shape of that, because it's the same shape as batching fanout by node. Many waiters, one source, one distribution loop. Once you see that pattern you find it everywhere in this design, and naming the repetition is a strong signal.

Two costs. Write-behind means read state is eventually consistent across a user's own devices — so a channel you just read on your phone can stay unread on your desktop for a few seconds. That's noticeable, and acceptable.

And coalescing has a subtler cost that's worth raising before an interviewer finds it. It adds a latency floor equal to the batch window. Worse, it converts a single slow query into a slow query for every coalesced waiter. You have created a correlated failure that didn't exist before. That's a genuine trade rather than a free win, and saying so is the difference between having read about request coalescing and having operated it.

<break time="0.8s" /> So, three things to carry.

Presence is the largest event stream in the system, not a feature bolted onto messaging. One person logging in is forty thousand delivery events, and the answer is deliberate lossiness at every layer — expiry instead of deletion, coalescing instead of immediacy, and lazy scoping instead of completeness.

A stale presence is invisible to users and a presence storm is not. That asymmetry is what licenses every one of those choices.

And read state is the biggest table in the product and the first thing rendered on launch. Store an identifier rather than a count so there's no counter to drift, write behind because losing seconds costs a stale badge, and know that coalescing buys you throughput at the price of a correlated failure.
