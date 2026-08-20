---
id: design-ticketmaster-04-waiting-room
title: "Ticketmaster, part four — the waiting room, and why first-come-first-served isn't fair"
source: src/data/designs/design-ticketmaster.md §9
minutes: 9
---
The virtual waiting room is the piece people treat as a product feature bolted on the side. It isn't. It is the load-shedding architecture, and without it every other decision in this design stops working. This episode is about how it's built, where the real ceiling is, and a fairness argument that almost nobody raises and that interviewers remember.

Three things. <break time="0.8s" /> First, the premise, and the placement decision that matters more than the mechanism. <break time="0.7s" /> Second, the counter — where it actually breaks, and what to do about it, which is usually nothing. <break time="0.7s" /> And third, fairness, where the obvious answer turns out to be the unfair one.

So, the premise. You cannot make the booking tier handle ten million concurrent users, and you should not try. You make it handle two thousand a second, and you hold everybody else at the door.

Admission control instead of capacity is the load-shedding answer. And it is precisely the difference between a system that degrades and a system that collapses.

Now, placement — which matters more than the mechanism does. The queue has to live at the edge. A worker in the content delivery network, or a dedicated stateless tier that touches nothing but a fast counter store.

Here's why. If you put the queue behind the same load balancer as your booking service, the herd takes down the very thing whose job is to protect you from the herd. You have built a shield and then put it inside the thing it's shielding. Say that out loud, because it's the kind of mistake that survives a whiteboard and dies in production.

The mechanism itself is small. On arrival, increment a counter for that event, and the value you get back is your ticket number. Issue a signed token carrying the position, the event, and when you joined — signed, so the edge can validate it statelessly and nobody can forge themselves a better place in line.

The client then polls for its position, and the poll interval scales with that position. Thirty seconds if you're four millionth. Two seconds if you're fiftieth. That alone is a free tenfold reduction in queue traffic, and it costs you nothing.

An admission controller drains at a rate sized to measured booking-tier capacity, and mints a session token good for about ten minutes.

And then the rule everything depends on: the booking interface rejects any request without a valid session token. Without that single check, the queue is theatre — a determined client just calls the hold endpoint directly and walks straight past your entire waiting room.

Second thing. The counter, and where it actually breaks. This is where a lot of candidates over-engineer.

One key is one slot, one node, one core. The store serialises those increments single-threaded, and that serialisation is exactly what makes them atomic. So a single primary handles roughly a hundred to two hundred and fifty thousand simple operations a second.

Now put real events against that ceiling. A five-thousand-seat theatre gets maybe twenty thousand arrivals over several minutes — call it a hundred a second. That is a tenth of one percent of your budget. A twenty-thousand-seat arena, two hundred thousand arrivals over five minutes, is about seven hundred a second — still under one percent. A large stadium show, a million arrivals over five minutes, is around three thousand a second. About two percent.

And then the once-a-year megaevent. Ten million people arriving in thirty seconds is three hundred and thirty thousand a second, which is over budget by somewhere between two and ten times.

So the answer is: use the plain counter for essentially every event, and know the number where it stops working. Volunteering that this holds up to about a hundred and fifty thousand arrivals a second — which covers everything except a handful of onsales a year — is a far stronger answer than pre-emptively sharding a counter that will never once be hot.

And for the handful that do exceed it, you know which ones weeks in advance. So this is a per-event configuration flag, not a runtime decision.

Three escalations, and they are not equal.

Block reservation is the good one. Workers reserve ten thousand positions at a time in a single increment and then hand them out locally. That's roughly ten thousand times fewer operations, and any cross-region round trip amortises across the whole block instead of being paid per user. The cost is that positions go approximate — a worker sitting on a stale block hands a lower number to someone who arrived later, and unused remainders leave gaps in the sequence.

Sharded counters spread throughput across several keys, with the global position computed from the local sequence and the shard number. But you still pay one round trip per arrival, so it fixes the ceiling without fixing the latency.

Or you drop the counter entirely. Give every joiner a random value, and admission is simply whether that value falls under a threshold. Zero coordinated writes at all. What you lose is the ability to say "you're number twelve thousand four hundred and thirty-one."

Two consequences if you do escalate, and they're both reasons not to escalate by default.

Gaps make position arithmetic lie. Advancing the watermark by a thousand no longer admits a thousand people, so the controller has to run a closed loop on measured admissions rather than on watermark deltas. With a plain counter, positions are dense and the arithmetic simply works.

And strict first-in-first-out degrades — which matters much less than it sounds, for reasons that are the third thing on my list.

So. Fairness. And this is worth a full minute in the room, because it's rarely mentioned and it separates people.

Strict first-come-first-served, ordered by arrival, looks fair. It is not fair. It rewards low latency and fast automation — which means a datacentre bot on a fat pipe beats a human on a phone on a train, every single time. You have built a system that is procedurally neutral and substantively rigged.

The alternative is a lottery. Accept joins for a fixed window — say two minutes — and then randomly permute everyone who joined. Bots immediately lose their structural advantage, because arriving forty milliseconds earlier stops meaning anything at all.

But name the trade, because there is a real one. First-come-first-served is legible. Telling somebody they're number twelve thousand four hundred and thirty-one, with an estimated wait, is something a person trusts and can plan around. A lottery is genuinely fairer and completely opaque. And a user who is told "wait here, you might get in" experiences that as worse, even when it is objectively better for them.

So perceived fairness and actual fairness diverge here. That is a product decision, not a technical one, and the architecture has to be able to serve either. Candidates who separate those two things get remembered.

<break time="0.8s" /> So, three things to carry.

Admission control instead of capacity. Two thousand a second behind the door, everyone else held at it — and the queue lives at the edge, because a shield placed inside the thing it protects is not a shield.

Use the plain counter, and know its ceiling. About a hundred and fifty thousand arrivals a second covers every event except a few a year, and saying that number is stronger than sharding something that will never be hot.

And first-come-first-served is not fair. It rewards automation and low latency. A lottery is fairer and less legible, and knowing which one the product wants is the actual question.
