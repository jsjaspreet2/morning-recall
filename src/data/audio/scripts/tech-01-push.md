---
id: tech-01-push
title: "Push notifications — the hint, not the truth"
source: src/data/guides/technology.md — Push Notifications
minutes: 9
---
Push notification is the only channel that reaches a user whose app is closed. And it is the only channel where you never talk to the device at all. You hand a message to Apple or to Google, and they decide whether it arrives. Best effort, by construction. This episode is about what that one fact forces on the rest of your design.

Three things. How it actually works, and the part of it that bites. What the delivery contract really guarantees, which is less than you think. And the build-versus-buy line, which is not where most people draw it.

So, the mechanism. The thing to internalise is that you do not own the connection. The operating system holds one persistent socket to its vendor's push service, shared by every app on the device. That's why push costs almost no battery per app — there's only ever one socket. Your server authenticates to that service and posts a message addressed by device token.

On Apple's side that's A.P.N.S. — H.T.T.P. two, one post per notification. You authenticate with a J.W.T. signed by a p-eight key, which is the modern way: one key works across all your apps and it doesn't expire. The legacy alternative is a per-app certificate that expires annually, and that has caused a genuinely famous number of outages.

On Google's side that's F.C.M., using the H.T.T.P. version one A.P.I., authenticated with a service account token. And here's the detail people miss: on Apple devices, F.C.M. is a wrapper. It forwards to A.P.N.S. on your behalf. So a message to an Apple device sent through F.C.M. inherits every single A.P.N.S. constraint. You have not escaped anything.

And then Web Push, which is a standard rather than a vendor A.P.I. The browser hands you a subscription — an endpoint and a set of keys. You encrypt the payload to those keys and sign the request using vapid. The endpoint host varies by browser, and your code genuinely doesn't care. That indifference is the entire point of standardising it.

Now the part that bites, and it's the token lifecycle.

Tokens are per app install. Not per user. They rotate on reinstall, on restore from backup, and sometimes on an operating system upgrade. So the mapping you have to model is: one user, many devices, one token each — and a single device may belong to several users, because people share phones and people log out.

When the vendor tells you a token is dead — Apple returns a four-ten Unregistered, Google returns unregistered or not-found — you delete it immediately. Not on a weekly sweep. Immediately. Continuing to send to dead tokens is the single most common way to get yourself rate limited or throttled by a provider, and when that throttle lands it lands on your real notifications too.

Second thing. The delivery contract.

Push isn't a datastore, so the usual consistency vocabulary doesn't apply — but there's an equivalent question and you should be able to answer it in one line. The contract is at most once, best effort, and unordered.

The vendor stores and forwards while the device is offline, and then it drops your message. It drops it when the time to live expires. It drops it when a newer message shares the same collapse key. It drops it when the offline queue for that device overflows — Google holds roughly four collapse keys per token, and about a hundred non-collapsible messages before it starts discarding. And it drops it if the app has been force stopped by the user.

Ordering does not exist. Two notifications sent in order can arrive in either order, or one can be collapsed away entirely.

And you never get delivery confirmation. Apple and Google both report accepted for delivery. Neither one reports shown to a user. So never, ever build a flow whose correctness depends on a push arriving.

Which gives you the rule this whole episode is built around: the notification is a hint, and your database is the truth.

That's not a slogan, it's an architecture. The badge count comes from the server on next launch — never from arithmetic on the pushes a device happened to receive. The inbox is a queryable resource, and push is one delivery channel over it, sitting alongside in-app, email, and message. And that's also what makes multiple devices coherent: two phones that received completely different subsets of pushes still render exactly the same inbox, because neither one is keeping score.

Two more consequences worth saying unprompted. Nothing sensitive goes in the payload — it transits a third party and it renders on a lock screen, so send an identifier and let the app fetch the real content. And the payload ceiling is four kilobytes anyway, which means an identifier is usually all that fits.

Third thing, and this is the one where the conventional answer is wrong. Build or buy.

The instinct is that talking to Apple and Google directly is the hard part, so you buy that. It isn't the hard part. It's a post request and a signed token. It's genuinely easy.

The hard parts are yours no matter what you buy: resolving recipients, applying preferences and quiet hours, deduplication, localisation, token hygiene, and rate limiting. All of that stays on your side of the line.

So the rule is: build the fan-out, buy the last mile. What you actually purchase from an aggregator is the campaign and analytics layer — segmentation, scheduling, split tests, delivery reporting. You are not buying an abstraction over a difficult protocol, because there isn't one.

And the flip is not a technical flip at all. The moment notification content is owned by marketing rather than by engineering, an aggregator stops being an abstraction and starts being the product surface a non-engineer needs to operate. That, and not protocol difficulty, is the real buy decision. The second flip is Web Push, where the standard is good enough that a library plus a subscription table is basically the whole implementation.

One last piece of design worth naming before anyone asks: separate queues per class of message. A marketing blast and a security alert must never share a worker pool, because when they do, the alert is the one that loses.

So, three things to carry.

You don't own the connection, and you don't own the token either. Tokens belong to app installs, they rotate, and a dead token gets deleted the instant the vendor tells you it's dead — because sending to dead tokens is how you get throttled.

The contract is at most once, best effort, unordered, with no confirmation that anything was ever seen. Use collapse keys so somebody offline for an hour gets one current notification instead of forty stale ones, and use time to live so nothing arrives after it stopped being true.

And the sentence to say in the room: the notification is a hint, and your database is the truth. Model notifications as a durable server-side inbox, and treat push, in-app, email, and message as delivery channels over it.
