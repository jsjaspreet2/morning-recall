# Interview Mechanics — read once, applies to every problem

This page holds everything that is true regardless of which system you're designing. Problem pages link here instead of repeating it. Read it twice early, then once the week of a loop.

---

## 1 · The clock

A 60-minute round is really ~50 minutes of design. Budget it and **say your budget out loud** — it's the cheapest possible demonstration of the thing being tested.

| Minutes | Phase | What failure looks like |
|---|---|---|
| 0–5 | Frame + scope. Name the archetype, propose 3 functional requirements, name what you're cutting | Starting to draw. Asking a dozen clarifying questions with no hypothesis |
| 5–10 | NFRs with numbers + back-of-envelope | Adjectives instead of numbers. Estimating things that don't drive a decision |
| 10–15 | Entities + API | Modeling every field. Designing eleven endpoints |
| 15–25 | High-level design: flows, not boxes | Boxes with no request walking through them |
| 25–45 | **Deep dives — 2 or 3, chosen by you** | Waiting to be asked. Staying at the level of component names |
| 45–50 | Failure modes, bottlenecks, what you'd cut | Running out of clock because minutes 15–25 took twenty |

**The single biggest structural mistake is spending too long on the high-level design.** Nobody has ever failed a loop for a slightly thin API section. People fail constantly for never reaching a deep dive.

---

## 2 · The opening (the highest-leverage 60 seconds)

Every problem page has a scripted version. The shape is always:

1. **Name the archetype in one sentence.** "This is a two-sided geospatial marketplace." "This is non-fungible inventory under thundering herd."
2. **Name the tension.** The two things in the system that want opposite properties. Almost every good system design problem is chosen *because* it has one.
3. **Propose scope.** Three functional requirements, and explicitly what you're excluding.
4. **Pre-commit your deep dive.** "I'd like to go deep on X."

Point 4 is the one people skip and it's the most valuable. Interviewers overwhelmingly accept a well-argued plan — which means **you get to choose the ground you fight on.** Choose the thing you've drilled.

---

## 3 · Driving your own depth

Nobody will say "please go deeper." Silence is not approval; it's an evaluation.

At roughly minute 25, stop expanding breadth and say: *"I'd like to go deep on the reservation lifecycle now — I think that's where the correctness risk actually is."* Then go three layers:

1. **What's the naive approach?**
2. **What specifically breaks about it, with a number or a mechanism?**
3. **What replaces it, and what does the replacement cost?**

A dive that skips layer 2 is just a list of technologies. A dive that skips layer 3 reads as memorized — real engineers know what their choices cost.

---

## 4 · Managed services

Naming a service is not an answer. The rule: **describe the properties you need, then name the thing that has them, then volunteer the tradeoff unprompted.**

> ✗ "I'd use DynamoDB."
> ✓ "I need single-key point lookups with predictable p99 under a write-heavy load, and no relational queries — so a partitioned KV store, DynamoDB or Cassandra. The cost is that any access pattern I didn't design a key for becomes a scan, so I'm committing to knowing my queries up front."

Doing this once, early, changes how the rest of the interview is read. Not doing it is the most common reason strong engineers score as shallow.

---

## 5 · What "staff signal" concretely means

It is not deeper knowledge of Kafka. Reviewers are looking for four specific behaviors:

- **Scoping.** You cut things and said why. You named what's below the line rather than silently omitting it.
- **Tradeoffs volunteered, not extracted.** You said the cost of your own choice before being asked.
- **Prioritization under a clock.** You spent your minutes on the load-bearing part and said so.
- **Failure thinking.** You reached for "what happens when this node dies / this network partitions / this user abandons" without prompting.

The compact version: **juniors describe what they'd build; staff engineers describe what they'd build, what they'd cut, and what it costs.**

---

## 6 · Interview-performance traps

Ranked by how often they sink otherwise-strong candidates.

1. **Drawing before scoping.** Ten minutes of boxes, then "we're low on time," and no deep dive ever happens.
2. **Waiting to be asked for depth.** See §3.
3. **Naming services as a substitute for reasoning.** See §4.
4. **Designing for the final scale before one correct path exists.** Get the request working end to end for a thousand users, *then* scale it. Interviewers will follow you down; they rarely pull you back up.
5. **Estimating for its own sake.** Every number should change a decision. If it doesn't, skip it and say you're skipping it.
6. **Answering the question you prepped instead of the one asked.** Listen for the constraint that makes this variant different, and repeat it back.
7. **Not stating the core invariant out loud.** "No double-booking." "Exactly one driver." "At-least-once, deduped downstream." If the whole design serves an invariant, leaving it implicit reads as not knowing it.
8. **Silently correcting yourself.** Say "I want to revise that — here's why the first version breaks." Visible self-correction scores *higher* than never being wrong.
9. **Defaulting to AP reflexively.** Availability is usually right, which is exactly why picking CP correctly on the rare problem that needs it stands out so much.
10. **Going quiet while thinking.** Narrate the search, not just the result: "I'm deciding between partitioning ownership and taking a lock — the question is whether I can guarantee a single writer."
11. **Treating the interviewer's question as a correction.** It's usually a probe. Answer it, don't capitulate to it. If you were right, defend it once.
12. **Skipping the failure paths.** Every flow should end with at least one abandonment, timeout, or partition case.

---

## 7 · Phrases that carry weight

Not scripts to recite — patterns to internalize. Each one compresses a whole category of reasoning into a sentence.

- *"These two parts of the system want opposite properties, so I'm going to split them rather than pick one globally."*
- *"Rather than coordinate concurrent writers with a lock, I'd rather partition ownership so there's only one writer."*
- *"This is a hint with a defined staleness bound; the write path is the only source of truth."*
- *"That's cheap and reversible, so it goes first. The expensive irreversible step goes last."*
- *"I'm using cheap math as a pre-filter for an expensive call."*
- *"Correctness lives in the conditional update; the background job is a cosmetic optimization."*
- *"That's a hot shard, and it's intentional — here's what I get for it."*
- *"I'd start here for v1 and name the upgrade path, because the v1 is probably good enough to ship."*

---

## 8 · How to use the problem pages

Per problem, over about a week — this is a retrieval schedule, not a reading list.

1. **Day 1 — read fully**, slowly, including the "why the obvious answer fails" blocks. ~30 min.
   **Reading order within a page matters, because §6 references dives that come after it.** Read §6 straight through and *don't chase the forward references* — you're building a map, so it's fine that step 8 tells you where exactly-one-winner is enforced without yet telling you how. Then read the dives, each of which answers a question the flow raised. **Then return to §6 and try to reproduce the steps before re-reading them.** It's the only section you read twice, which mirrors the fact that it's written last, and the second pass turns it from reference material into recall material. Anything you can't reproduce points straight at a dive that didn't land.
2. **Day 2 — draw §14 (the five-minute skeleton) cold**, on paper, no reference. Diff against the page. Note *only* what you missed.
3. **Day 3 — answer the recall prompts out loud**, in full sentences, as though someone asked. Older pages carry them as a §16; newer ones don't, and for those the practice deck is the source. Out loud matters: fluent-in-your-head and fluent-out-loud are different skills, and only one of them is graded.
4. **Day 5 — pick one deep dive and explain it to a wall for five minutes**, unprompted, including its cost.
5. **Day 7 — one full 45-minute mock** on the problem or a §15 variant.

**Stop signal:** you can draw the skeleton in five minutes and answer every recall prompt without hesitation, twice on separate days. Then move on — re-reading a page you already know is the most comfortable and least useful thing available to you.
