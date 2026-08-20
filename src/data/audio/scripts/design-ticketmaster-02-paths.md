---
id: design-ticketmaster-02-paths
title: "Ticketmaster, part three — two paths that barely touch"
source: src/data/designs/design-ticketmaster.md §5-6
minutes: 9
---
In part one we said the plan was to separate browse from purchase completely. This episode is what that actually looks like when you draw it — the interface, and the two request flows end to end. And there's one architectural move hiding in here that is the real answer to the whole problem.

Three things. <break time="0.8s" /> First, the interface decisions worth narrating before anyone asks. <break time="0.7s" /> Second, the browse path, and the single setting that absorbs five million queries a second. <break time="0.7s" /> And third, the purchase path, all the way from joining a queue to the point of no return.

So, the interface. Five decisions, and each one is a place people go wrong.

Availability is a separate resource from the event. Venue topology — sections, rows, seat positions — is immutable, so it caches essentially forever. Availability is volatile and caches for a second or two. Bundle them into one response and you can't cache either one well. Splitting them is what makes the read path possible at all.

Holding and ordering are two separate calls, deliberately. Holding is cheap and reversible. Charging is expensive and hard to reverse. So always take the reversible action first. Invert those two and you will eventually charge somebody's card and then discover the seat is gone.

There are two request shapes for a hold. Either the user clicked specific seats on a map and you send seat identifiers, or the user just wants four together and you send a quantity with a best-available strategy. Those two have completely different concurrency profiles, and noticing that out loud is worth real credit.

Both holds and orders carry an idempotency key. During an onsale, users mash the button. Without that key, one user consumes four seats' worth of inventory in retries alone.

And the session token issued by the queue is what authorises a hold. No token, no hold. That single rule is what makes admission control enforceable rather than decorative — and we'll come back to why that matters.

Second thing. The browse path.

Two properties to point at, and they're the whole design.

The read path never touches the inventory database. Not once. It reads a cache that is updated from the database's change stream. That is what lets five million queries a second coexist with a database that has a single writer per event.

And the edge admission worker is the only thing standing between the herd and the booking tier. Everything downstream of it is built for two thousand requests a second, not five million, because it will never see more than that. Scaling by admission control instead of by capacity is the actual architectural move here, and it's worth saying in exactly those words.

Now the flow. A request for the event returns venue topology from the content delivery network. It's immutable, so a long expiry serves essentially all of that traffic for free.

A request for availability hits an edge cache with a one to five second expiry. And that expiry is the thing that absorbs five million queries a second — because within any one-second window, millions of requests collapse into a handful of fetches to the origin. That's not a tuning detail. That's the mechanism.

On a cache miss, the availability service serves the seat bitmap from its own memory, rebuilt from the inventory change stream. It never queries the inventory database. Never.

During a live onsale the client also opens a socket and receives deltas — a version number, plus a list of which seat ordinals changed to which status. And here's the detail that makes this safe: the client applies a delta only if its version is exactly one greater than what it already has. Any gap at all, and it throws away its state and refetches the whole bitmap.

That version-gap check is what lets you push lossy deltas without ever risking a client that quietly believes something false. You don't need guaranteed delivery. You need detectable loss.

Every inventory commit emits an outbox event, which flows through the log to the availability service, which flips the bits, bumps the version, broadcasts the delta, and republishes the blob to the edge. End to end, a seat greys out for everyone in about a second.

Third thing. The purchase path, and there are a lot of steps, so I'll keep them in order.

The onsale opens and the client asks to join the queue. The edge worker increments a counter for a position and hands back a signed token carrying the user, the event, the position, and when they joined. Signed, so the edge can validate it later without asking anyone.

The client then polls for its position — and the poll interval scales with that position. Thirty seconds if you're four millionth in line, two seconds if you're fiftieth. Crucially, the edge validates the signature and compares the position against an admitted watermark, which means a waiting user generates no origin traffic at all. Millions of people waiting, and the booking tier doesn't know they exist.

The admission controller advances that watermark at a rate sized to measured booking-tier capacity — measured, not guessed. Once your position is at or under the watermark, you're issued a session token good for about ten minutes.

You load the seat map, you pick seats, and you post a hold with that session token and an idempotency key. The booking service rejects any request without a valid session token. That is the line that makes the queue real rather than theatre.

Then one transaction. Seats acquired in sorted order, so two users grabbing overlapping sets can't deadlock each other. Each seat gets the conditional update — claim it only if it's available, or if it's held and already expired. If every row updates, commit, and return a hold identifier with an expiry about eight minutes out. If any row comes back zero, roll back the entire set and return a conflict with refreshed availability. Partial holds are not a thing. You either get all four seats or none of them.

The commit emits an outbox event, the delta broadcasts, and everyone else watching sees those seats grey out inside a second.

Now the order. Verify the hold belongs to this user and hasn't expired. Enforce purchase limits — on the user and on the payment instrument, because those are different things and bots exploit the difference. Then transition the hold into a pending-payment state, which suspends expiry, with a hard ceiling of about two minutes so a hung payment provider can't strand a seat forever.

Authorise with the payment provider under its own idempotency key. If that fails, release the hold immediately — seats go back to available, delta broadcasts, and the client gets a payment-required response.

If it succeeds, one transaction flips the seats from held to sold, marks the order confirmed, and consumes the hold. That commit is the point of no return, and it is the only place in the entire system where inventory becomes permanently unavailable. Worth naming it as such.

Everything after that is asynchronous. Capture the authorisation, mint the tickets, send the confirmation. And note the asymmetry: a capture failure keeps the sale and retries out of band. You do not un-sell a seat because a capture hiccupped.

Finally, the abandonment path — and this is my favourite part of the whole design, because nothing happens. No job runs. No timer fires. The seat is simply reclaimed by whichever writer next evaluates the expiry predicate. The sweeper eventually corrects the displayed status, purely so the seat map doesn't look needlessly pessimistic.

<break time="0.8s" /> So, three things to carry.

Split availability from topology, and hold from order. Immutable and volatile data cache differently, and you always take the reversible action before the irreversible one.

The read path never touches the inventory database, and a one-to-five-second cache expiry is what collapses five million queries into a handful of origin fetches.

And the real architectural move is scaling by admission control rather than by capacity. Everything behind the edge is built for two thousand a second, because the session token means it will never see more.
