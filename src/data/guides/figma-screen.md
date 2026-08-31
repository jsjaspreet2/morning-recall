# Figma Screen — Wed 9/9, 3:00–4:00 PT

> One hour, one interviewer, one **multi-part** coding problem in CoderPad. You pick the language.
> **No AI tools.** Camera on, no filters. This guide is the twelve-day plan, the round script, and
> the one chapter of material that decides the hour: the mutable document model and its history.

Companion to `Coding Patterns` (which is the general shape library) and `Client-Side System
Design` (which is the client-architecture half, graded on entirely different axes). Neither covers what this screen
actually is: **a data-structure problem dressed as a design tool, extended in parts, where the
score is how far you get and how cleanly the seams hold when they add the next part.**

**Two things this guide deliberately does not contain.** There is no client-side system design
chapter — that round is not on 9/9, and if the loop continues, `Design Figma` under Designs is the
page for it. There is no React component chapter — `UIE Components` already has fourteen of them,
and the invitation lists "React" as one of six *language* options, which is a pad configuration,
not a signal that you will build UI. See §01 B.

## 01 — The hour, and what is actually graded

### A. THE FORMAT

| | Wed 9/9, 3:00–4:00 PM PT |
|---|---|
| **Round** | Coding — the only technical round on the invitation |
| **With** | Emily Kuhn, Figma. One interviewer, positioned explicitly as a partner |
| **Tool** | CoderPad, `app.coderpad.io/WDEFCXGR`, over Zoom |
| **Language** | Yours: *"Ruby, Python, Typescript, React, Java, Go"* — **TypeScript** for you, see §08 |
| **Deliverable** | A working solution to as many parts of one problem as you reach |
| **Stated design** | Multi-part · **not expected to finish** · no gotchas · no single correct path |
| **Rules** | No AI-enabled tools. Camera on. No Zoom filters, background, or blur. Full-screen share may be requested |
| **Also** | NDA to sign beforehand · Brighthire transcription with an opt-out link · join 5 minutes early |

### B. THE INVITATION, READ LITERALLY

Four sentences in that email are doing real work. Each one changes how you should play the hour.

**1. "The question may consist of multiple parts, and it is not expected that you will complete
all parts."**

This is the most important sentence in the email, and it is not reassurance — it is a description
of the instrument. A problem calibrated so that finishing is not expected is a problem that
measures **rate and quality per part**, not completion. Two consequences:

- Racing to finish part 1 in order to "get through more" is the wrong optimisation. A part 1 that
  is correct, tested, and cleanly factored beats a part 1 that is fast and brittle, because part 2
  is scored *on top of* part 1, not beside it.
- **Part 2 exists and it will pull on part 1.** In every reported version of this question, the
  later parts are of the form *"now make that reversible / batched / grouped / normalised."* The
  single highest-leverage thing you can do in minutes 13–32 is leave the seam that makes part 2
  cheap. §03 D is the whole technique, and it is the most transferable idea in this guide.

**2. "We avoid 'gotcha' questions and those with only one path to an answer."**

There is no trick to spot. Time spent hunting for the clever insight is time you don't have, and
the hunt reads as stalling. The flip side is the part people miss: if several paths work, then
**picking one and saying why is itself the graded behaviour.** *"I'm using inverse commands rather
than snapshots because undo has to be O(1) in document size and I'd rather pay the complexity in
the op type than in memory"* is a full answer. *"We could snapshot or we could do inverse ops"* is
a stall wearing an answer's clothes.

**3. "We strive to recreate a realistic team collaboration experience. View your interviewer as a
partner and feel comfortable asking any questions you may have."**

Real, and worth using — clarifying questions are free and expected, and the interviewer will
interject, rename things with you, and add edge cases live. But read the second half too. A partner
does not want to be asked permission for every decision. The calibration: **ask about the
problem, decide about the solution.** *"Are property values always strings, or can they be
objects?"* is a question. *"Should I use a Map or an object here?"* is a decision you should make
out loud and move past.

**4. "Select a general purpose programming language like Ruby, Python, Typescript, React, Java,
Go."**

*Reasoned inference, flagged as such:* a list that puts React beside Go and Ruby is a list of pad
runtime configurations, not a hint about the problem. Combined with every reported question being
a plain data-structure problem, treat a UI build as unlikely — but not impossible, and you have
`UIE Components` if it happens. Prepare for the document model.

### C. WHAT IS KNOWN ABOUT THE BAR, BY CONFIDENCE

Search results for "Figma interview" are badly polluted — a large fraction are about *using the
design tool*, and another large fraction are generated listicles that contradict each other. Only
these are load-bearing.

| Confidence | Claim | Source |
|---|---|---|
| **High** | The format in §01 A: 60 minutes, CoderPad, multi-part, finishing not expected, no gotchas, no single path, interviewer as partner, no AI, camera on. | The invitation itself — first-party |
| **High** | **Figma's signature phone screen is a `Document` of layers holding key/value properties: implement applying a property and undoing, then extend to redo, then to batched commits.** Reported independently by three sources and tagged as the highest-frequency coding question at this stage. | Candidate-report aggregators |
| **High** | *"Pretty standard algorithms and data structures questions, but they are all Figma-flavored."* LeetCode-medium, practical rather than puzzle-shaped. | interviewing.io, quoting a Figma engineer |
| **High** | At least one candidate found the pad **pre-seeded with a code skeleton and failing tests** for the undo part, and was asked to make them pass before adding redo. Plan for this — see §01 E. | Glassdoor report |
| **Medium** | **Reading order:** sort objects on a 2-D canvas into reading order, left-to-right and top-to-bottom; the follow-up handles rows whose elements are not perfectly aligned. Reported in 2026 screens. | Multiple aggregators |
| **Medium** | **Styled text ranges:** slice styled text given text plus style ranges; the follow-up overwrites a range's style and normalises the result. | GreatFrontend's Figma set |
| **Medium** | Interviewers actively collaborate — they push on naming, extract helpers with you, and add edge cases mid-solution. Expect the problem to change shape while you are in it. | Interview-guide aggregators |
| **Low** | Emily Kuhn is a full-stack engineer at Figma; CS at Michigan; previously SurveyMonkey and Minerva Project. Useful only for framing — do not open with it. | LinkedIn and data brokers |
| **Ignore** | Every "33 Figma interview questions" listicle. Every page whose questions turn out to be about auto layout and prototyping. Claims of a 3-hour or 96-hour take-home — those are not this round and are unsupported for it. | SEO content farms |

**The shape to internalise.** Every credible reported question is the same question wearing
different clothes: *one mutable document model, plus operations over it, extended in parts.* The
graded axis is clean handling of a messy object model with the invariants said out loud — not
algorithmic cleverness. That is why §04 and §06 are the long chapters and there is no chapter on
graphs.

### D. THE NO-AI RULE, THE CAMERA, AND HOW TO TRAIN FOR IT

The policy is unusually explicit: no AI-enabled tools, they may ask you to share your **full**
screen, and a suspected violation gets a reminder and may affect the decision. Take it at face
value and remove the ambiguity yourself — a clean browser profile, editor assistants disabled at
the settings level, nothing running in another window that would be awkward on a full-screen share.

Two motor skills degrade without your noticing, and both are load-bearing here:

- **Class and type boilerplate from blank.** You have not typed `private history: Change[][] = []`
  or a `Map` generic without a completion in months. In an hour where the first twelve minutes are
  data model and API, that tax lands at the worst possible moment.
- **Recovering from an error you can't see.** No quick-fix, no inline explanation. The loop is read
  the message, form a hypothesis, check — and it is slow if unpractised.

**The rule for the twelve days: every timed rep runs with AI off.** Not "I won't accept
suggestions" — disabled. §08 is the fluency drill; the schedule in §02 puts one in every day.

**The camera rules are procedural and easy to fumble under time pressure**, so handle them the
night before: filters, virtual background, and blur all off before you join. Sign the NDA in
advance — the email itself warns the link fails behind a VPN. Decide on Brighthire beforehand; the
opt-out is explicitly consequence-free, and deciding live costs you your first two minutes.

### E. CODERPAD: THE FIRST NINETY SECONDS

You have the pad link in advance. **Open it the day before**, set the language, and type a
throwaway line to confirm the runtime works. Discovering the pad's behaviour at 3:01 is a
self-inflicted wound.

The first thing to establish live is whether the pad already contains something:

| What you see | What you do |
|---|---|
| **Empty pad** | Normal case. Set language, then §03's clock from minute 0. |
| **A skeleton with tests already failing** | Reported, so plan for it. **Read all of it before typing** — three minutes of reading is not lost time, it is the requirements phase. Read the tests first: they are the spec, and they usually reveal the shape of parts 2 and 3. Say what you learned out loud. |
| **A prose prompt in a comment** | Read it aloud, then restate it in your own words and get it confirmed. |

Then ask, in the first minute, close to verbatim:

> *"Before I start — can this pad run tests, or should I just call functions and print? And is
> there a part 2 you'd like me to keep in mind while I structure part 1?"*

Both halves earn something. The first says you intend to verify rather than assert. The second is
the single best question you can ask in this specific interview: an interviewer who tells you what
is coming has just handed you the seam to leave, and one who declines has still heard you thinking
about extension. §07 covers what to do with each answer.

Pad mechanics worth knowing cold rather than discovering:

- The interviewer sees every keystroke, and CoderPad records **paste events with playback**. Type
  your code. A large paste is visible and reads badly in a no-AI round even when the content is
  entirely yours.
- Run early and often. A pad you have never executed at minute 30 is a pad that will not compile at
  minute 31.
- Long silent stretches read as stuck. Narrate — §03 E.
- Assume the **standard library only**, and ask before reaching for anything else. In TypeScript
  that means `Map`, `Set`, `Array`, `structuredClone`, and nothing you would normally `npm i`.

### F. RESOURCES, RANKED

Twelve days. In order, and the list is short on purpose:

1. **§04, §05, and §06 of this guide, plus the drills in `uie-practice` (§10).** Built for exactly
   this question family. Do the drills; reading this guide is not a rep.
2. **Figma itself, daily, between now and the 9th.** Not to become a designer — to have handled the
   nouns. Make a file, nest frames, make a component and a variant, style a range of text inside one
   text layer, reorder layers, group and ungroup, leave a comment, open it in two windows and watch
   the cursors. Every one of those is a candidate for the problem, and the object model becomes
   intuition rather than trivia.
3. **Three posts from Figma's engineering blog**, one evening total. *How Figma's multiplayer
   technology works* · *Realtime editing of ordered sequences* · *Building a professional design
   tool on the web*. Read them for the object model and the ordering scheme, not for distributed
   systems theory — see §09 B, which has the three-sentence version if the evening disappears.
4. **GreatFrontend's Figma question set**, which you own. Its reading-order and styled-text-range
   problems are the closest public analogues to the medium-confidence rows in §01 C.
5. **`Coding Patterns`**, for the general shapes — intervals, sweeps, stacks — if any of those feel
   cold.
6. **`Design Figma`** under Designs, for the *onsite*, not for the 9th. Do not spend a day of the
   twelve on it.

**Worth emailing Perpetua now**, because the answers change how you prepare and none are awkward:

- Will the CoderPad come pre-loaded with a skeleton or tests, or start empty?
- Is a test runner available in the pad for TypeScript, or should I plan to verify by printing?
- Is there anything specific about the team's work I should read up on beforehand?

### G. THE FIVE-MINUTE VERSION

If you read nothing else on the afternoon of the 9th:

- **Do not start coding for the first nine minutes.** Restate the problem, run one example by hand,
  and write the data model and API into the pad as types before any logic.
- **Route every mutation through one method.** That single choke point is what makes part 2 —
  undo, batching, logging, whatever they add — additive instead of a rewrite. Say that you're doing
  it and why. §03 D.
- **Say the invariant before you write the code that maintains it.** *"Runs stay sorted,
  non-overlapping, and no two adjacent runs share a style."* That sentence is the graded artifact.
- **Verify as you go**, even by printing. §07.
- **Decide, don't survey.** Every choice gets a reason and a switching condition.
- **At minute 54, stop and name the cuts** in priority order, whatever state you're in. Then ask
  your questions — the email promises you the time, so have three ready.

## 02 — The twelve-day schedule

Twelve days, Sat 8/29 through Wed 9/9, ~2 h each. The Cursor screen is behind you on 8/28 and its
AI-off fluency work transfers directly, so nothing here needs to happen before then.

Every day is **one timed rep and one fluency drill**. The rep is what moves the number.

| Day | Rep (≈60–75 min, AI off) | Fluency (≈15 min) | Read |
|---|---|---|---|
| **Sat 8/29 · D-11** | **Baseline. Do not read §05 first.** `figma-01-document-undo`, 45 min cold | — | Nothing until after. Then grade it and read §01 |
| Sun 8/30 · D-10 | `figma-01` again, now with the framework — §05 A | Retype kit 1–3 | §03, §04 A–D |
| Mon 8/31 · D-9 | `figma-02-undo-redo-batch` | Retype kit 4–5 | §06 A–C |
| Tue 9/1 · D-8 | `figma-03-reading-order`, both parts | Retype kit 6–8 | §04 E–F, §05 B |
| Wed 9/2 · D-7 | `figma-04-styled-text-ranges`, both parts | Kit, weakest three | §05 C |
| **Thu 9/3 · D-6** | **Full mock #1 — 3:00–4:00 PM, real clock, one hour, no pausing** | — | §11 the night before |
| Fri 9/4 · D-5 | Re-rep whatever the mock scored lowest. Only that. | Kit, weakest three | The section the mock exposed |
| Sat 9/5 · D-4 | `figma-05-layer-tree` | Full kit, timed | §05 D, §06 D–E |
| Sun 9/6 · D-3 | **`figma-08-sealed`, opened cold. 50 min.** Then `figma-06-command-stream` if time | Full kit, timed | §07 |
| Mon 9/7 · D-2 | `figma-07-coalescing-history` | Full kit, timed | §06 F, §08 |
| Tue 9/8 · D-1 | **Taper.** One light rep, nothing new. Open the pad, set the language, sign the NDA, decide on Brighthire. | Kit once, untimed | §03, §06 F, §11 only |
| **Wed 9/9 · D-0** | Runbook — §11 | — | §01 G |

**Rules for the twelve days.**

1. **Grade every rep the same day, against §03 G, before you look at anything.** An ungraded rep
   teaches you your existing habits.
2. **Reps are narrated out loud, alone.** The round grades reasoning you have to externalise while
   your hands are busy, and that is a separate skill from having the thought. Record one and watch
   the first ten minutes back — that is where the openings live, and openings are the most
   reliably fixable part of the hour.
3. **Never read a §05 model answer before the timer.** They are inside collapsibles for exactly
   that reason.
4. **The parts are the point.** When a drill's part 1 goes green, do not stop and admire it — start
   the next part on the same clock and find out what your part 1 cost you. That discovery is the
   entire training effect.
5. **If a day slips, drop the fluency drill, not the rep.**

## 03 — The sixty-minute shape

### A. THE CLOCK

The hour is not sixty minutes of coding. Intros are real, and the email explicitly promises you
time for questions at the end — which comes out of the same hour.

| Minutes | Phase | What "done" looks like |
|---|---|---|
| 0–4 | **Intros** | Short. Have a 45-second version of your background ready so it doesn't sprawl. |
| 4–9 | **Understand** | Problem restated in your words and confirmed. **One example run by hand**, out loud. Two or three clarifying questions asked and answered. |
| 9–13 | **Model and API** | Types and method signatures typed into the pad, before any logic. The invariants said out loud. |
| 13–32 | **Part 1** | Working, exercised at least twice, cleanly factored through one mutation choke point. |
| 32–46 | **Part 2** | The extension they add. Should cost you an addition, not a rewrite. |
| 46–54 | **Part 3 or hardening** | Whichever they steer to. If nothing is added, harden: edge cases, complexity, the test you skipped. |
| 54–57 | **Close** | What works, what you'd do next in priority order, what you'd revisit. |
| 57–60 | **Your questions** | Three ready. §09 C. |

**The hard rule:** if you are still writing part 1's core logic at minute 32, stop adding to it and
get it to a state you can demonstrate. A demonstrable part 1 plus a described part 2 outscores an
almost-working part 1 by a wide margin, and the email told you completion is not the metric.

### B. THE OPENING, CLOSE TO WORD FOR WORD

The first ninety seconds after the problem lands set the tone for the hour. Say something like:

> *"Let me make sure I have it. You want a document that holds layers, each layer has properties as
> key/value pairs, and I need to be able to set a property and undo that. Let me run an example —
> I create layer A, set `fill` to red, set `fill` to blue, then undo. After the undo, `fill` is red,
> not unset, because undo reverses the last change rather than clearing the key. Is that right?"*

Three things happened there and all three are graded. You restated the requirement, you ran a
concrete example, and **you surfaced the one genuinely ambiguous semantic in the problem** — undo
restores the previous value rather than deleting the key — which is exactly the sort of thing the
interviewer is waiting to see whether you notice.

Then the questions. Ask two or three, not eight. The ones that actually change your code:

| Question | Why it changes something |
|---|---|
| *"Can a property be set on a layer that doesn't exist — error, or create it?"* | Decides whether `apply` can fail, which decides whether failed ops enter history. |
| *"Are values just strings, or arbitrary?"* | Decides whether you can compare with `===` or need a deep equal. |
| *"How big does this get — tens of layers or hundreds of thousands?"* | Licenses or forbids the snapshot approach in one sentence. §06 A. |
| *"Is there a part 2 I should keep in mind while structuring this?"* | The best question in the interview. §01 E. |

Do **not** ask about performance targets, concurrency, or persistence unless they raise them. In a
sixty-minute pad problem those read as deflection.

### C. WHAT "COLLABORATIVE" ACTUALLY MEANS HERE

The invitation's word is *partner*, and the reports say interviewers push on naming, extract
helpers with you, and add edge cases mid-solution. That is a different round from one where you are
left alone to produce. Calibrate:

- **Ask about the problem. Decide about the solution.** Ambiguity in the requirements is theirs to
  resolve; ambiguity in your approach is yours.
- **When they suggest something, take it and say what it changes.** *"That's better — if the ops
  are self-inverting I don't need the `before` field at all, which also fixes the delete case."*
  Then actually change the code. Visibly adopting a suggestion is a positive signal; nodding and
  continuing unchanged is a strongly negative one.
- **When they add an edge case, say where it lands before you fix it.** *"That breaks the batch
  path, not the single-op path, because the rollback assumes the batch is non-empty."* Locating a
  bug out loud is worth more than fixing it silently.
- **Disagree when you have a reason.** *"I'd rather not store the inverse eagerly — it doubles the
  memory for the common case where nothing is ever undone. Would you rather I optimise for undo
  speed here?"* A reasoned disagreement is collaboration. Silent compliance is not.

### D. PART-BOUNDARY DISCIPLINE — THE ONE TECHNIQUE

This is the most transferable idea in the guide, and it exists because of one sentence in the
invitation: the question has multiple parts and you will not finish them.

**The observation.** In every reported version of this question family, the later parts are
transformations of the same kind: *now make it reversible · now make it batched · now make it
grouped · now normalise the result · now do it in one pass.* Every one of those is a change to
**when and how state mutates**, not to what the state is.

**The consequence.** If mutations are scattered across your methods — `this.layers.get(id).props.set(k, v)`
appearing in four places — then part 2 is a rewrite under time pressure, and you will do it badly.
If every mutation goes through one method, part 2 is an addition inside that method.

```ts
// Part 1 only needs this to set a value. Write it anyway.
private commit(change: Change): void {
  this.applyChange(change)
}
```

That is three lines and it costs you nothing. When part 2 arrives, undo is:

```ts
private commit(change: Change): void {
  this.applyChange(change)
  this.undoStack.push([change])
  this.redoStack.length = 0
}
```

and batching is a two-line branch inside the same method. Nothing else in the class moves.

**Three rules that generalise beyond this problem:**

1. **One choke point per mutable structure.** Every write goes through it. No exceptions, including
   the convenient one you're about to make in a helper.
2. **Represent the change as data before you need to.** A `Change` object you construct and then
   immediately apply looks like ceremony in part 1. It is the entire reason part 2 takes four
   minutes instead of twenty. The same object is later the history entry, the batch element, the
   coalescing unit, and the thing you'd send over the wire.
3. **Compute derived answers, don't store them.** If part 2 is "now also support X", stored derived
   state is a second place that has to learn about X.

**Say the seam out loud when you build it**, in one sentence:

> *"I'm routing every mutation through a single `commit` and representing each change as an object.
> Right now that's slightly more code than I need — I'm doing it because if you later want undo,
> batching, or a change log, they all hook in at that one point."*

That sentence scores **even if part 2 never comes**, because it demonstrates the judgment the
multi-part format exists to measure. And it pre-frames you as someone whose part 1 was designed,
not lucky.

**The counter-rule, so you don't overshoot:** leaving a seam is not implementing part 2. Do not
write an undo stack you aren't asked for, do not add a generic event bus, do not build an
abstraction with one implementation. The seam is a method and a type. Anything more is speculative
work on a clock, and it reads exactly as badly as it sounds.

### E. WHEN YOU STALL, AND WHEN THEY NUDGE

| Situation | Say |
|---|---|
| Choosing a representation | *"I'm using a `Map` keyed by id rather than an array — lookup dominates here and I'd otherwise be doing a linear scan on every op."* |
| Genuinely stuck | *"Let me think out loud for a second. The problem is that undo needs the previous value, and I'm not capturing it before I overwrite. So the capture has to move above the write."* Narrated stalling is debugging. Silent stalling is stalling. |
| A bug you just found | *"That's off by one — I'm slicing with the end exclusive but comparing inclusive."* Debugging out loud is a positive signal, not an admission. |
| Don't know a language detail | *"I don't remember whether `Map` preserves insertion order for deleted-then-reinserted keys. I'm going to assume it doesn't and not depend on it."* Never bluff; assuming-and-flagging is free. |
| They nudge | Take the nudge immediately. A nudge means you were about to spend five minutes on something they've decided isn't the point. |
| Deferring deliberately | *"I'm going to handle the invalid-index case with a guard clause and come back to what it should do inside a batch — flagging it so it doesn't look like I think it's finished."* |

**On silence.** More than about twenty seconds without speech, in a round explicitly designed as a
collaboration, is the most common way strong candidates underperform. If you need to think, say
that you are thinking and what about.

### F. THE CLOSE

At minute 54, stop, whatever state you are in. Never let the clock end mid-keystroke.

> *"Where I got to: set and undo both work and I've exercised them on the four cases in the
> comment, including undo-past-the-beginning. Redo is structurally there — the stack exists and
> gets cleared on a new commit — but I haven't written the pop. What I'd do next, in order: finish
> redo, which is about eight lines because it's the mirror of undo; then batching, which goes in
> `commit` as a branch and needs the rollback case we talked about; then coalescing consecutive
> sets on the same key, which is where I'd want to ask you what the intended granularity is. The
> thing I'd revisit is storing the whole previous value — for large properties I'd want a patch
> instead."*

Naming a cut precisely demonstrates most of the knowledge that building it would have, at a
fraction of the cost. Silently omitting it demonstrates nothing.

### G. SELF-GRADE RUBRIC — RUN THIS AFTER EVERY REP

Score honestly out of 100. Below 75, re-rep the same problem.

| | Points | Criterion |
|---|---:|---|
| 1 | 10 | Did not write logic for the first nine minutes. Restated the problem and **ran one example by hand**. |
| 2 | 10 | Types and signatures typed into the pad before the bodies. |
| 3 | 15 | **Invariants stated out loud** before the code that maintains them. |
| 4 | 20 | **Part 1 correct** on the happy path and on the two obvious edge cases, and **exercised**, not asserted. |
| 5 | 20 | **The seam held**: part 2 was an addition, not a rewrite. One mutation choke point, change represented as data. |
| 6 | 10 | Every non-obvious choice got a reason; no menus, no "it depends" left undecided. |
| 7 | 10 | Narrated continuously; no silence over ~20 seconds. |
| 8 | 5 | Closed by naming the cuts, specifically and in priority order, unprompted. |

**Automatic flags:** started typing logic in the first three minutes · never ran the code · scattered
mutations across methods · rewrote part 1 to make part 2 fit · stored derived state · silent
stretches · ran out of time with no summary · asked for permission on a decision that was yours.

## 04 — The document model: the one chapter that matters

### A. WHY EVERY FIGMA QUESTION IS THIS QUESTION

Figma's product is a tree of objects, each carrying a bag of properties, ordered among its
siblings, positioned in 2-D, with text that carries formatting over character ranges — and every
user action is a reversible mutation of that structure, replicated to other people in real time.

Their interview questions are slices of that sentence. The reported ones map one-to-one:

| Reported question | The slice |
|---|---|
| `Document` with layers and key/value properties, plus undo | The object store and its history |
| Reading order over canvas objects | The 2-D geometry |
| Styled text ranges | Intervals over a sequence |
| Layer tree / grouping / z-order | The tree and its sibling ordering |

So there is one thing to be fluent in, not four. §04 B is that thing, and §05 is it worked four
different ways so that a fifth one you have not seen is still familiar.

**What this means for your prep:** you are not revising graphs, DP, or binary search. You are
getting fast and precise at *mutable structures with stated invariants and reversible operations*.

### B. THE FOUR SHAPES

Every problem in this family is one of these, or two of them composed.

**1. Keyed object store.** Objects by id, each with a property bag.

```ts
type PropValue = string | number | boolean
type Layer = { id: string; props: Map<string, PropValue> }
type Store = Map<string, Layer>
```

*The operation that's hard:* deleting, because everything that referenced the id is now dangling.
*The invariant:* every id referenced anywhere — a tree's children, a selection, a history entry —
exists in the store, or is explicitly known to be a tombstone.

**2. Ordered sequence.** Siblings in z-order; children of a frame; the output of a reading-order
sort.

```ts
type Children = string[]   // index 0 = bottom of the z-stack, by your stated convention
```

*The operation that's hard:* moving an element, because the index you computed before the removal
is wrong after it. *The invariant:* no duplicates, and the order is total — every element has
exactly one position. **Say your z-order convention out loud**; it is genuinely ambiguous and
getting it backwards silently is a classic way to fail a test you wrote yourself.

**3. Intervals over a sequence.** Styled text: a string plus runs of formatting.

```ts
type Style = Readonly<Record<string, string | boolean>>
type Run = { start: number; end: number; style: Style }   // half-open [start, end)
```

*The operation that's hard:* applying a style to an arbitrary range, because it splits the runs it
partially covers and may make neighbours mergeable. *The invariant, and it is four clauses — say
all four:* runs are **sorted**, **non-overlapping**, **contiguous** (they tile the whole string with
no gaps), **non-empty**, and **normalised** — no two adjacent runs carry an equal style.

**Half-open intervals are not a style preference.** `[start, end)` makes empty ranges
representable as `start === end`, makes adjacency the clean test `a.end === b.start`, and makes
length `end - start` with no `+ 1` anywhere. Say you're using half-open in your first sentence
about the type and you will avoid roughly half the off-by-one errors available in this problem.

**4. 2-D geometry.** Objects with a bounding box; reading order, hit testing, alignment.

```ts
type Box = { id: string; x: number; y: number; w: number; h: number }
```

*The operation that's hard:* grouping into rows when nothing is perfectly aligned.
*The invariant, and this is the trap:* **your comparator must be a strict weak ordering.** See §05 B
— a "same row if the tops are within 5 pixels" comparator is not transitive, and feeding a
non-transitive comparator to `Array.prototype.sort` produces garbage that is very hard to debug
under time pressure. This is the single most valuable thing to know about the reading-order
question, and it is the kind of thing an interviewer probes deliberately.

### C. THE COMMAND / INVERSE PATTERN

The load-bearing idea for everything in §06, and worth being able to write from blank.

A change is **data**, not a method call. Each change knows enough to be undone.

```ts
type Change =
  | { kind: 'setProp'; layerId: string; key: string; before: PropValue | undefined; after: PropValue }
  | { kind: 'createLayer'; layerId: string }
  | { kind: 'deleteLayer'; layerId: string; props: Map<string, PropValue>; index: number }

function invert(c: Change): Change {
  switch (c.kind) {
    case 'setProp':
      // Note the asymmetry: `after` becomes `before`, and a `before` of undefined
      // means the inverse must *delete* the key, not set it to undefined.
      return { ...c, before: c.after, after: c.before as PropValue }
    case 'createLayer':
      return { kind: 'deleteLayer', layerId: c.layerId, props: new Map(), index: -1 }
    case 'deleteLayer':
      return { kind: 'createLayer', layerId: c.layerId }
  }
}
```

Three things to notice, because interviewers probe all three:

1. **A change captures the previous value at the moment it is created**, not when it is undone.
   Capturing late is the most common bug in this problem, and it only shows up when you undo twice.
2. **`undefined` is a real state and it is not the same as "some value".** Setting a key that did
   not exist and then undoing must *remove* the key. If your `before` field is typed
   `PropValue | undefined` you are forced to think about it; if it's typed `PropValue` you will get
   it wrong.
3. **Delete needs to remember position**, or undoing a delete restores the object in the wrong place
   in the z-order. This is the follow-up they add when the basic version works.

**Undoing a group of changes reverses twice**: the order of the list *and* each change in it.

```ts
function undoCommit(commit: Change[]): Change[] {
  return commit.slice().reverse().map(invert)
}
```

Getting only one of the two reversals is a bug that passes every single-change test and fails the
first batch test. Write the reverse in before you need it.

### D. INVARIANTS ARE THE GRADED THING

Reports converge on this: the coding signal rewards **clean handling of a messy object model**, not
algorithmic trickiness. The visible form of "clean handling" is that you say what must always be
true, and then your code obviously maintains it.

The habit, which costs ten seconds each time:

> *"Before I write this: after any operation, the runs still tile the whole string with no gaps or
> overlaps, and no two neighbours share a style. Those two are what I'll check after every mutation."*

Then, where it's cheap, encode it:

```ts
function assertInvariants(runs: Run[], textLength: number): void {
  let pos = 0
  for (const r of runs) {
    if (r.start !== pos) throw new Error(`gap or overlap at ${pos}`)
    if (r.end <= r.start) throw new Error(`empty run at ${r.start}`)
    pos = r.end
  }
  if (pos !== textLength) throw new Error(`runs cover ${pos} of ${textLength}`)
}
```

Six lines, and calling it after each operation turns "I think that's right" into a demonstration.
It is also the fastest debugging tool available in a pad with no debugger: an invariant check fails
at the operation that broke it, not three operations later where the symptom appears.

**The five invariants worth having memorised**, one per shape plus history:

| Structure | Always true |
|---|---|
| Object store | Every referenced id exists, or is a known tombstone |
| Ordered sequence | No duplicates; total order; one stated direction |
| Interval runs | Sorted · contiguous · non-empty · normalised |
| 2-D grouping | The comparator is transitive |
| History | `undo` then `redo` returns the document to the identical state, for any sequence |

That last one is the property test to state out loud in the undo problem, and it catches nearly
every history bug there is. §07 C.

### E. THE TYPESCRIPT KIT

Decisions to make once now, so you make none of them on the clock.

**`Map` over object literals for anything keyed by a runtime id.** Real `delete`, real `size`,
no prototype hazards, no string coercion of keys, and iteration order you can reason about. The
cost is that it doesn't `JSON.stringify`, which matters only for printing — see §07 B.

**Discriminated unions for changes and commands**, always with a `kind` field. It is what makes the
`switch` in `invert` exhaustive, and with `strict` on, TypeScript will tell you when you add a
variant and forget a case. That is free correctness in a round where you cannot run a type-checker
in your head.

**Copying, in one decision:**

| Need | Use | Cost |
|---|---|---|
| Snapshot a whole small document | `structuredClone(doc)` | O(document). Fine for tens of objects, indefensible for a hundred thousand — say which you're assuming |
| One level of a plain object | `{ ...obj }` | O(keys). What you want for a `Style` |
| Copy a `Map` | `new Map(m)` | O(size), shallow. The values are still shared |

**Say the copy cost out loud when you choose it.** *"I'm cloning the whole doc per commit because
the problem says tens of layers; if it were a real document I'd store inverse ops instead and I can
switch to that if you'd like."* That single sentence pre-empts the most likely follow-up in the
whole problem.

**Small things that cost real seconds when typed from blank** — these are the retype kit in §08 B:

```ts
const byId = new Map<string, Layer>()
const props = layer.props ?? new Map()
boxes.sort((a, b) => a.y - b.y || a.x - b.x)      // numeric, chained tie-break
const grouped = new Map<string, Box[]>()
grouped.set(key, [...(grouped.get(key) ?? []), box])
this.undoStack.length = 0                          // clear in place, no reassign
```

### F. THE COMPLEXITY FOLLOW-UP THAT ALWAYS COMES

Once the basic version works, the reliable next question is some form of *"what does this cost, and
what happens when the document is large?"* Have the answer ready rather than deriving it live.

| Approach | Per operation | Per undo | Memory |
|---|---|---|---|
| Snapshot the document each commit | O(n) to clone | O(1) to swap | O(n × history depth) — the one that dies first |
| Inverse commands | O(1) | O(size of the change) | O(total change size) |
| Patches / structural sharing | O(depth of the change) | O(depth) | O(changed nodes × depth) |

The sentence to have ready:

> *"Snapshotting is O(n) per edit in memory and time, so it stops being viable somewhere around a
> document you'd actually ship. Inverse commands make both the edit and the undo proportional to
> the size of the change rather than the document, at the cost of every operation needing an
> inverse — which is the trade I'd take, and it's why I represented changes as data up front."*

**Two bounded-memory follow-ups worth knowing exist**, in case they push further: cap the history
at a fixed depth and drop from the bottom (cheap, and what most editors actually do), or coalesce
adjacent same-target changes so a burst of typing is one entry (§06 D). Both are two-line answers
and neither needs implementing unless asked.

## 05 — Five problems, worked

Four are the reported question family; the fifth is deliberately not Figma-shaped, because the
point is to rehearse the *method*, not to have four answers memorised. If you get handed
"implement a spreadsheet's fill-down," E is why you'll be fine.

**Use these as reps, not as reading.** Set a timer, do the problem, then open the collapsible.

### A. DOCUMENT, LAYERS, PROPERTIES — UNDO, REDO, BATCHING

**This is the one to be able to write in your sleep.** It is the highest-confidence row in §01 C,
and it is reported both as a from-scratch build and as a pre-seeded skeleton with failing tests.

> **The prompt, roughly.** Build a document made of layers. Each layer holds properties as
> key/value pairs. Support setting a property on a layer. Then: support undo. Then: support redo.
> Then: support grouping several operations into a single undoable batch.

**Your first three questions.** Does setting a property on a missing layer create it or error? Does
undo restore the previous value or remove the key — and what if the key never existed? Roughly how
many layers?

**The API you commit to, typed into the pad before any logic:**

```ts
type PropValue = string | number | boolean

class Doc {
  createLayer(id: string): void
  deleteLayer(id: string): void
  set(layerId: string, key: string, value: PropValue): void
  get(layerId: string, key: string): PropValue | undefined
  undo(): void
  redo(): void
  beginBatch(): void
  commitBatch(): void
}
```

**Say this while you type it:** *"Every mutation is going to go through one private `commit` that
takes a change object. Right now that's more structure than setting a property needs — I'm doing it
because undo, redo, and batching all hook in at that one point, and I'd rather not restructure
later."* That is §03 D, delivered.

<details>
<summary><strong>Model answer — the whole thing, ~70 lines</strong></summary>

The load-bearing idea is that **every change is a triple of target, `before`, and `after`, so
inverting a change is swapping two fields.** That one decision collapses undo, redo, and batch
rollback into the same three lines.

```ts
type PropValue = string | number | boolean
type Props = Map<string, PropValue>

type Change =
  // A whole layer: after === undefined means delete, before === undefined means it didn't exist.
  | { kind: 'layer'; layerId: string; before: Props | undefined; after: Props | undefined }
  // One property: undefined on either side means the key is absent.
  | { kind: 'prop'; layerId: string; key: string; before: PropValue | undefined; after: PropValue | undefined }

type Commit = Change[]

function invert(c: Change): Change {
  // The assertion is load-bearing, and worth a sentence if they ask: spreading a
  // union widens `before` and `after` to the union of both variants' types, which
  // no longer matches either arm. The runtime shape is correct; TypeScript can't
  // see that the swap is variant-preserving.
  return { ...c, before: c.after, after: c.before } as Change
}

class Doc {
  private layers = new Map<string, Props>()
  private undoStack: Commit[] = []
  private redoStack: Commit[] = []
  private batch: Change[] | null = null

  // ---- public API -------------------------------------------------------

  createLayer(id: string): void {
    if (this.layers.has(id)) return
    this.commit({ kind: 'layer', layerId: id, before: undefined, after: new Map() })
  }

  deleteLayer(id: string): void {
    const props = this.layers.get(id)
    if (!props) return
    this.commit({ kind: 'layer', layerId: id, before: new Map(props), after: undefined })
  }

  set(layerId: string, key: string, value: PropValue): void {
    const props = this.layers.get(layerId)
    if (!props) throw new Error(`no such layer: ${layerId}`)
    if (props.get(key) === value) return           // no-op edits do not enter history
    this.commit({ kind: 'prop', layerId, key, before: props.get(key), after: value })
  }

  get(layerId: string, key: string): PropValue | undefined {
    return this.layers.get(layerId)?.get(key)
  }

  undo(): void {
    if (this.batch) return                          // history is frozen inside a batch
    const commit = this.undoStack.pop()
    if (!commit) return
    for (const c of [...commit].reverse()) this.applyChange(invert(c))
    this.redoStack.push(commit)
  }

  redo(): void {
    if (this.batch) return
    const commit = this.redoStack.pop()
    if (!commit) return
    for (const c of commit) this.applyChange(c)     // forward order, forward changes
    this.undoStack.push(commit)
  }

  beginBatch(): void {
    if (this.batch) return                          // nested begins are ignored, not errors
    this.batch = []
  }

  commitBatch(): void {
    const batch = this.batch
    if (!batch) return                              // stray commit is ignored
    this.batch = null
    if (batch.length === 0) return                  // an empty batch is not an undo step
    this.undoStack.push(batch)
    this.redoStack.length = 0
  }

  /** Not asked for, but two lines, and it's what "invalid op inside a batch" needs. */
  abortBatch(): void {
    const batch = this.batch
    if (!batch) return
    this.batch = null
    for (const c of [...batch].reverse()) this.applyChange(invert(c))
  }

  // ---- the choke point --------------------------------------------------

  private commit(change: Change): void {
    this.applyChange(change)
    if (this.batch) {
      this.batch.push(change)
      return
    }
    this.undoStack.push([change])
    this.redoStack.length = 0                       // new work invalidates the redo branch
  }

  private applyChange(c: Change): void {
    if (c.kind === 'layer') {
      if (c.after === undefined) this.layers.delete(c.layerId)
      else this.layers.set(c.layerId, new Map(c.after))   // copy: never alias history into state
      return
    }
    const props = this.layers.get(c.layerId)
    if (!props) throw new Error(`no such layer: ${c.layerId}`)
    if (c.after === undefined) props.delete(c.key)
    else props.set(c.key, c.after)
  }
}
```

**The five things in there that an interviewer is looking for.**

1. **`before` is captured at edit time**, inside `set`, not at undo time. Capturing late is the
   classic bug and only surfaces on the second consecutive undo.
2. **`undefined` means absent, and the inverse of "set a new key" is "delete it"** — handled by the
   same branch, because the type forced it.
3. **`[...commit].reverse().map(invert)` reverses twice.** Reversing only the order, or only each
   change, passes every single-op test and fails the first batch test.
4. **`new Map(c.after)` in `applyChange`.** Without the copy, the history entry and the live
   document are the same object, and undo silently does nothing. This is a genuinely nasty bug and
   worth pointing at while you type it.
5. **`redoStack.length = 0` lives in `commit`, not in `set`** — so it is impossible to add a
   mutation path later that forgets it.

</details>

**The follow-ups they will add, in the order they usually come:**

| Follow-up | The answer, in one line |
|---|---|
| *"Now redo."* | Mirror of undo: forward order, forward changes, push back onto the undo stack. |
| *"Now batching."* | A branch in `commit`, plus `beginBatch`/`commitBatch`. Nothing else moves. |
| *"What if an operation inside a batch is invalid?"* | Roll the batch back and discard it — `abortBatch` above. Say which semantics you chose and why; both "discard" and "keep what worked" are defensible, so pick one and name it. |
| *"What if `beginBatch` is called twice?"* | Ignore the nested one. Say it out loud — if you'd rather support real nesting, that's a depth counter, and say that too. |
| *"Does an invalid operation clear the redo stack?"* | **No.** Only committed work invalidates the redo branch. This is a favourite probe. |
| *"What does this cost on a large document?"* | §04 F, the prepared sentence. |
| *"Make undo O(1)."* | It already is, in document size — that's the payoff of inverse commands over snapshots, and it's why the `Change` type exists. |

**What a weak answer looks like**, so you can hear yourself doing it: cloning the whole document
into the undo stack on every set and calling it done; storing `before` by reading the document
inside `undo`; mutating `props` directly in `set` and adding history around the outside; treating a
key that didn't exist as if it held `undefined`; and — the one that costs the most — writing a
correct part 1 with the mutation inlined, then discovering at minute 35 that undo requires touching
every method.

### B. READING ORDER

> **The prompt, roughly.** Given objects on a canvas, each with a position and size, return them in
> reading order — left to right, top to bottom. Then: the objects in a row are not perfectly
> aligned. Handle that.

Part 1 is four minutes. **Part 2 is the whole question**, and it has a trap in it that is worth
more than the solution.

**Your first three questions.** Is the origin top-left with y increasing downward? Do I have width
and height, or just a point? What counts as "the same row" — is there a stated tolerance, or is
that mine to define?

<details>
<summary><strong>Model answer — both parts, and the trap</strong></summary>

**Part 1, when rows are perfectly aligned.** A chained numeric comparator, and say the tie-break
out loud:

```ts
type Box = { id: string; x: number; y: number; w: number; h: number }

function readingOrderAligned(boxes: Box[]): Box[] {
  return [...boxes].sort((a, b) => a.y - b.y || a.x - b.x)
}
```

`a.y - b.y || a.x - b.x` works because a comparator of `0` is falsy — the idiom every reviewer
recognises. Copy before sorting: `sort` mutates, and silently mutating the caller's array is a
free negative signal.

**Part 2, when they are not.** Here is the trap, and it is the reason this question exists.

The instinct is to widen the comparator: *"same row if `Math.abs(a.y - b.y) < 5`, then compare x."*
**That comparator is not transitive.** With tops at 0, 4, and 8, A and B are the same row, B and C
are the same row, and A and C are not. `Array.prototype.sort` requires a strict weak ordering, and
given a comparator that isn't one, V8 does not error — it returns a plausible-looking wrong answer
that depends on the input order. You will lose ten minutes to it.

**Say that out loud, then don't sort.** Group first, sort second:

```ts
function readingOrder(boxes: Box[]): Box[] {
  // 1. One pass top-down. The x tie-break only keeps the sweep deterministic.
  const byTop = [...boxes].sort((a, b) => a.y - b.y || a.x - b.x)

  // 2. Sweep: an object joins the current row if it starts before the row's
  //    lowest edge so far — i.e. if it vertically overlaps the row at all.
  const rows: Box[][] = []
  let rowBottom = -Infinity
  for (const box of byTop) {
    if (box.y >= rowBottom) rows.push([])
    rows[rows.length - 1].push(box)
    rowBottom = Math.max(rowBottom, box.y + box.h)
  }

  // 3. Within a row, left to right.
  return rows.flatMap((row) => row.sort((a, b) => a.x - b.x))
}
```

A sweep with running state is *allowed* to be non-transitive — that's the point. It never asks
"are these two in the same row," only "does this one still overlap the row I'm building."

**The limitation to name before they find it.** One tall object that spans the page chains every
row into a single row. That behaviour is defensible — a full-height sidebar arguably *is* beside
everything — but it should be a stated choice, not an accident:

> *"A tall element merges the rows it spans, because I'm extending the band as I go. If you'd
> rather it didn't, I'd compare against the first element's band instead of the running maximum,
> which caps the damage but makes the result depend on which element starts the row. I'd want to
> know what the objects actually are before picking."*

**If they hand you a tolerance instead of heights** — only points, no boxes — the same sweep works
with `if (box.y >= rowTop + tolerance)` and `rowTop` set when the row opens. Same structure, and
still not a comparator.

</details>

**The follow-ups:** nested containers, so reading order is recursive and each frame is ordered
independently (§05 D's `paintOrder` is the shape) · right-to-left languages, which is one flipped
comparator plus a note that the row grouping is unaffected · columns instead of rows, which is the
same sweep with the axes exchanged · "do it in one pass," where the honest answer is that the sort
dominates at O(n log n) and the sweep is already linear.

**What a weak answer looks like:** the tolerance comparator, fed to `sort`, with the
non-transitivity undetected · mutating the input · assuming y increases upward without asking ·
inventing a tolerance constant with no justification when heights were available all along.

### C. STYLED TEXT RANGES

> **The prompt, roughly.** Text is a string plus a list of style ranges. Implement slicing a
> substring, keeping the styles. Then: implement applying a style to a range, and make sure the
> result is normalised.

This is the interval problem, and the four-clause invariant from §04 B is the whole answer.

**Your first three questions.** Are the ranges guaranteed sorted and non-overlapping on the way in?
Does applying a style *merge* into what's there or *replace* it? Is a range inclusive or exclusive
at the end — *and if they don't care, say you're using half-open and why.*

<details>
<summary><strong>Model answer — slice, apply, normalise</strong></summary>

**State the invariant before writing anything:** runs are sorted, contiguous, non-empty, and no two
adjacent runs carry an equal style. Every function below returns runs satisfying all four, and
`normalize` is the only place that has to know it.

```ts
type Style = Readonly<Record<string, string | boolean>>
type Run = { start: number; end: number; style: Style }   // half-open [start, end)

function sameStyle(a: Style, b: Style): boolean {
  const ka = Object.keys(a), kb = Object.keys(b)
  return ka.length === kb.length && ka.every((k) => a[k] === b[k])
}

/** The only function that knows the invariant. Everything else just calls it. */
function normalize(runs: Run[]): Run[] {
  const out: Run[] = []
  for (const r of runs) {
    if (r.end <= r.start) continue                       // drop empties
    const last = out[out.length - 1]
    if (last && last.end === r.start && sameStyle(last.style, r.style)) last.end = r.end
    else out.push({ ...r })                              // copy: callers keep their runs
  }
  return out
}

function sliceStyled(text: string, runs: Run[], from: number, to: number) {
  const out: Run[] = []
  for (const r of runs) {
    const start = Math.max(r.start, from)
    const end = Math.min(r.end, to)
    if (start < end) out.push({ start: start - from, end: end - from, style: r.style })
  }
  return { text: text.slice(from, to), runs: normalize(out) }
}

function applyStyle(runs: Run[], from: number, to: number, patch: Style): Run[] {
  if (from >= to) return runs                            // empty range is a no-op, not an error
  const out: Run[] = []
  for (const r of runs) {
    const lo = Math.max(r.start, from)
    const hi = Math.min(r.end, to)
    if (lo >= hi) { out.push(r); continue }              // untouched
    if (r.start < lo) out.push({ start: r.start, end: lo, style: r.style })          // left keep
    out.push({ start: lo, end: hi, style: { ...r.style, ...patch } })                // middle patch
    if (hi < r.end) out.push({ start: hi, end: r.end, style: r.style })              // right keep
  }
  return normalize(out)
}
```

**The four things being graded here.**

1. **Clip, then rebase.** `start - from` is the step people forget: the returned runs are indexed
   into the *new* string, not the old one. Say it while you write it.
2. **`{ ...r.style, ...patch }` merges; `patch` alone replaces.** These are different products —
   Figma's "make this bold" does not clear the colour. Ask, then say which you implemented.
3. **The three-way split is left-keep, middle-patch, right-keep**, and a run can need all three at
   once when the range sits strictly inside it. Test that case first; it's the one that fails.
4. **Normalisation is a separate function, called at the end of everything.** Inlining merge logic
   into `applyStyle` is how you end up with two subtly different notions of "adjacent."

</details>

**The follow-ups:** insert and delete text, where every run after the edit point shifts and a
deletion can empty a run entirely — the reason `normalize` drops zero-length runs · "remove a
style," which is the same function with a delete instead of a spread · "what if ranges arrive
overlapping," which is a sweep over boundary events and worth naming even if you don't build it ·
"how would you store this for a real editor," where the honest answer is that a run list is O(n) per
edit and a real one uses a rope or piece table — one sentence, don't detour.

**What a weak answer looks like:** inclusive-vs-exclusive confusion that produces off-by-ones for
the rest of the hour · forgetting to rebase after slicing · producing adjacent duplicate runs and
calling it correct because the rendering would look the same · mutating the input runs.

### D. LAYER TREE — GROUPING, REPARENTING, Z-ORDER

> **The prompt, roughly.** A document is a tree of layers. Implement grouping a set of layers,
> ungrouping, and moving a layer to a new parent. Ordering among siblings is z-order and must be
> preserved.

**Your first three questions.** Is `children[0]` the bottom or the top of the z-stack? Can I group
layers that aren't siblings? When a group is created, where does it sit in the parent's order?

That last one has a right answer and interviewers wait for it: **the group takes the slot of its
topmost member.** Anything else changes what the canvas looks like, which is a correctness bug in a
design tool, not a preference.

<details>
<summary><strong>Model answer — group, ungroup, reparent, paint order</strong></summary>

```ts
type Id = string
type TreeNode = { id: Id; parent: Id | null; children: Id[] | null }  // null children = leaf

class Tree {
  private nodes = new Map<Id, TreeNode>()
  constructor(rootId: Id) { this.nodes.set(rootId, { id: rootId, parent: null, children: [] }) }

  /** Convention, stated up front: children[0] is the BOTTOM of the z-stack. */
  group(ids: Id[], groupId: Id): void {
    if (ids.length === 0) throw new Error('nothing to group')
    const parents = new Set(ids.map((id) => this.nodes.get(id)!.parent))
    if (parents.size !== 1) throw new Error('can only group siblings')
    const parentId = [...parents][0]!
    const siblings = this.childrenOf(parentId)
    const members = new Set(ids)

    // The group lands where the topmost member was, so the canvas is unchanged.
    const top = Math.max(...ids.map((id) => siblings.indexOf(id)))
    const next: Id[] = []
    siblings.forEach((cid, i) => {
      if (members.has(cid)) { if (i === top) next.push(groupId); return }
      next.push(cid)
    })

    // Members keep their relative order inside the group -- read it off the parent.
    const ordered = siblings.filter((cid) => members.has(cid))
    this.nodes.set(groupId, { id: groupId, parent: parentId, children: ordered })
    for (const cid of ordered) this.nodes.get(cid)!.parent = groupId
    siblings.length = 0
    siblings.push(...next)
  }

  ungroup(groupId: Id): void {
    const group = this.nodes.get(groupId)
    if (!group || !group.children) throw new Error(`not a group: ${groupId}`)
    if (group.parent === null) throw new Error('cannot ungroup the root')
    const siblings = this.childrenOf(group.parent)
    const at = siblings.indexOf(groupId)
    for (const cid of group.children) this.nodes.get(cid)!.parent = group.parent
    siblings.splice(at, 1, ...group.children)   // one splice does remove and insert
    this.nodes.delete(groupId)
  }

  reparent(id: Id, newParentId: Id, index: number): void {
    if (id === newParentId) throw new Error('cannot parent a node to itself')
    if (this.isAncestor(id, newParentId)) throw new Error('cannot parent a node into its own subtree')
    const node = this.nodes.get(id)
    if (!node || node.parent === null) throw new Error(`cannot move ${id}`)
    const from = this.childrenOf(node.parent)
    from.splice(from.indexOf(id), 1)            // remove BEFORE computing the insert
    const to = this.childrenOf(newParentId)
    to.splice(Math.max(0, Math.min(index, to.length)), 0, id)
    node.parent = newParentId
  }

  private isAncestor(maybeAncestor: Id, of: Id): boolean {
    let cur: Id | null = this.nodes.get(of)?.parent ?? null
    while (cur !== null) {
      if (cur === maybeAncestor) return true
      cur = this.nodes.get(cur)!.parent
    }
    return false
  }

  /** Leaves, bottom of the stack first. The order a renderer would paint them. */
  paintOrder(rootId: Id): Id[] {
    const out: Id[] = []
    const walk = (id: Id): void => {
      const n = this.nodes.get(id)!
      if (!n.children) { out.push(id); return }
      for (const c of n.children) walk(c)
    }
    walk(rootId)
    return out
  }

  private childrenOf(id: Id): Id[] {
    const n = this.nodes.get(id)
    if (!n) throw new Error(`no such node: ${id}`)
    if (!n.children) throw new Error(`${id} is a leaf, not a container`)
    return n.children
  }
}
```

**The four things being graded.**

1. **The cycle check.** Moving a node into its own descendant produces a tree that is no longer a
   tree, and every later traversal hangs. Walking up the parent pointers is O(depth) and three
   lines. Write it before they ask.
2. **Remove before you insert**, and never reuse an index computed before the removal. This is the
   ordered-sequence invariant from §04 B doing real work.
3. **The group takes the topmost slot**, and members keep relative order — read off the parent
   rather than off the caller's `ids`, which may be in selection order, not z-order.
4. **`splice(at, 1, ...children)`** does the ungroup in one operation, at the right position, with
   no index arithmetic. Reaching for it is a small fluency signal.

</details>

**The follow-ups:** *"move a layer within the same parent"* — the only case where it matters
whether the index is interpreted before or after the removal, and a real drag hits it constantly.
`[a,b,c,d,e]` moving `a` to index 3 gives `[b,c,d,a,e]` post-removal and `[b,c,a,d,e]` pre-removal;
both are defensible, and **naming which one you implemented is the entire point** ·
*"undo the grouping"* — which is why this problem often arrives *after* §05 A,
and the answer is that group and ungroup are inverses if you record the parent and index ·
*"what if two people reorder concurrently"* — the real answer is fractional indexing, which is what
Figma actually does and is written up on their engineering blog (§09 B); one sentence is enough ·
*"compute each node's absolute position"* — a DFS accumulating parent transforms.

**What a weak answer looks like:** appending the group to the end of the parent's children, which
silently reorders the canvas · no cycle check · computing the insertion index before the removal ·
storing a `depth` or `absoluteIndex` field on each node and having to maintain it — stored derived
state, §03 D rule 3.

### E. COMMAND STREAM WITH CHECKPOINTS

Deliberately **not** Figma-flavoured. If the method only works on problems you've seen, it isn't a
method.

> **The prompt, roughly.** You're given a log of commands as text lines. Replay them. Then: support
> answering "what was the state after the first n commands" many times, efficiently.

<details>
<summary><strong>Model answer — parse, step, checkpoint</strong></summary>

The move is the same as everywhere else in this guide: **turn the input into data first**, keep the
state transition in one function, then make the query fast without touching either.

```ts
type Op =
  | { kind: 'set'; key: string; value: number }
  | { kind: 'add'; key: string; delta: number }
  | { kind: 'clear' }

function parse(line: string): Op {
  const [cmd, ...rest] = line.trim().split(/\s+/)
  switch (cmd) {
    case 'set': return { kind: 'set', key: rest[0], value: Number(rest[1]) }
    case 'add': return { kind: 'add', key: rest[0], delta: Number(rest[1]) }
    case 'clear': return { kind: 'clear' }
    default: throw new Error(`unknown command: ${cmd}`)
  }
}

type State = Map<string, number>

function step(state: State, op: Op): void {
  switch (op.kind) {
    case 'set': state.set(op.key, op.value); return
    case 'add': state.set(op.key, (state.get(op.key) ?? 0) + op.delta); return
    case 'clear': state.clear(); return
  }
}

class Log {
  private ops: Op[] = []
  private checkpoints: Array<{ at: number; state: State }> = [{ at: 0, state: new Map() }]
  constructor(private readonly stride = 64) {}

  append(line: string): void {
    this.ops.push(parse(line))
    if (this.ops.length % this.stride === 0) {
      this.checkpoints.push({ at: this.ops.length, state: new Map(this.stateAt(this.ops.length)) })
    }
  }

  /** State after exactly the first `n` ops. */
  stateAt(n: number): State {
    const target = Math.max(0, Math.min(n, this.ops.length))
    let base = this.checkpoints[0]
    for (const c of this.checkpoints) if (c.at <= target) base = c
    const state = new Map(base.state)
    for (let i = base.at; i < target; i++) step(state, this.ops[i])
    return state
  }
}
```

**The trade to narrate, because it *is* the answer:** with checkpoints every `k` ops, a query
replays at most `k` ops and memory is O(n/k × state size). `k = 1` is a snapshot per op — instant
queries, unusable memory. `k = n` is no checkpoints — no memory, O(n) queries. Everything
interesting is in between, `k ≈ √n` balances them, and the right value depends on how big the state
is relative to an op. **That paragraph is the graded content**; the code is the setup for it.

Note the checkpoint list is naturally sorted, so the linear scan for `base` is a binary search if
they push on it — say so rather than writing it.

</details>

**Why this one is on the list:** it is §04 F's memory-versus-time table in a different costume, and
it is the same `parse → data → one step function → make the query fast` skeleton as everything
else. If the 9th hands you a problem nobody has reported, this is the shape to fall back on.

## 06 — Undo/redo, done properly

It is the highest-probability single topic in the hour. It is the reported part 2 of the highest-
confidence question, it is the natural part 2 of §05 D, and it is the thing most candidates
implement approximately. This chapter is what "properly" means.

### A. THE THREE MODELS

| | How | Edit cost | Undo cost | Memory | Reach for it when |
|---|---|---|---|---|---|
| **Snapshots** | Clone the whole document per commit | O(n) | O(1) | O(n × depth) | The document is genuinely tiny and you're out of time. Say it's a placeholder. |
| **Inverse commands** | Store `(target, before, after)` per change | O(1) | O(change) | O(total change) | **The default.** Cheap in both directions, and the change object is reusable as a log, a batch element, and a network message. |
| **Patches / structural sharing** | Store a path plus old and new values into an immutable tree | O(depth) | O(depth) | O(changed × depth) | Deeply nested documents, or when you also want time-travel and cheap diffing. |

**The one-sentence justification to have memorised**, because it is the most likely follow-up in
the whole interview:

> *"Snapshots are O(n) per edit in both time and memory, so they stop being viable well before a
> real document. Inverse commands make the edit and the undo proportional to the change rather than
> the document — the cost is that every operation needs an inverse, which is exactly why I made the
> change a data object up front."*

**Do not start with snapshots and plan to upgrade.** The upgrade is not a refactor of the history
code, it is a refactor of every mutation site, and that is precisely the rewrite §03 D exists to
prevent.

### B. THE STACK INVARIANTS

Five rules. Interviewers probe two or three of them, essentially always.

1. **Undo pops from undo and pushes to redo. Redo pops from redo and pushes to undo.** The commit
   object is the same object moving between stacks — do not rebuild it.
2. **New committed work clears the redo stack.** You have branched the history and the other branch
   is gone. Put the clear in the single `commit` choke point so no future mutation path can forget.
3. **An operation that did nothing does not clear redo, and does not enter history.** Setting a
   property to the value it already has, an invalid index, a no-op group of one — none of these are
   undo steps. This is a favourite probe and it is one `if` in `set`.
4. **Undoing a group reverses twice** — the order of the changes and each change itself. §04 C.
5. **`undo` then `redo` returns the document to the identical state, for any sequence.** State this
   as the property you'd test. It catches almost every bug in this chapter. §07 C.

### C. BATCHING

The reported part 3. The semantics have real choices in them and the graded behaviour is naming
which one you took.

| Situation | The choices | What to say |
|---|---|---|
| `beginBatch` while already batching | Ignore it · maintain a depth counter and commit on the outermost · error | *"I'll ignore the nested begin. Real nesting is a depth counter if you want it — it's two lines and I'd add it if batches could be opened by nested helpers."* |
| `commitBatch` with no batch open | Ignore · error | Ignore. An error here punishes the caller for something harmless. |
| An operation inside the batch is invalid | Roll the whole batch back and discard · keep what succeeded · abort at the first failure and commit the prefix | Pick one and justify. Rollback is the defensible default — a batch exists precisely so the group is atomic. |
| Empty batch committed | Push an empty commit · skip it | **Skip it.** An empty commit is an undo step that appears to do nothing, and users hit undo twice. |
| `undo` called while batching | Ignore · implicitly commit first · error | Ignore, and say why: the history is in an inconsistent intermediate state until the batch closes. |

Rollback is the same three lines as undo, which is the payoff of the change-as-data decision:

```ts
abort(): void {
  const batch = this.batch
  if (!batch) return
  this.batch = null
  for (const c of [...batch].reverse()) this.apply(this.invert(c))
}
```

### D. COALESCING

*"If I type ten characters, should undo remove all ten or one?"* Every real editor answers "all
ten," and this is the follow-up that separates people who have thought about the product from
people who have implemented a stack.

The mechanism is a merge test against the top of the undo stack at commit time:

```ts
/** Merge into the previous commit when both describe the same continuing gesture. */
private shouldCoalesce(prev: Change[], next: Change): boolean {
  if (prev.length !== 1) return false                       // never merge into a batch
  const last = prev[0]
  return last.kind === 'prop' && next.kind === 'prop'
      && last.layerId === next.layerId && last.key === next.key
      && next.at - last.at < 500                            // ms, or a sequence counter
}
```

and on a merge you keep the **older** `before` and the **newer** `after` — which is exactly the
inverse-command structure paying off again.

**Three things to say about it, without being asked:**

- The boundary needs a way to be forced. Selection changes, blur, and an explicit "checkpoint" all
  end a coalescing run, or an undo after clicking elsewhere reverts something the user thought was
  finished.
- Time-based merging makes undo depend on how fast someone types, which is not reproducible.
  Real editors use a gesture boundary — pointer up, selection change — and use time only as a
  fallback. Say this; it's a product judgment, not a coding one, and it's the sort of thing this
  round is looking for.
- Never coalesce into a batch. A batch is already a stated unit.

### E. THE EDGE CASES THEY WILL PROBE, RANKED

Rehearse the top five until the answers are instant.

1. **Undo past the beginning, redo past the end.** No-op, no throw. One `if` each. If you only test
   one thing, test this.
2. **Setting a key that did not exist, then undoing.** The key must be *absent*, not `undefined`.
   §04 C.
3. **Undo, then a new edit, then redo.** Redo must do nothing — the branch was discarded.
4. **A batch containing an operation that reverses an earlier one in the same batch.** The whole
   batch is still one undo step, and the double reversal must produce the original.
5. **Delete an object, then undo.** Restores its properties *and* its position in the z-order.
   Forgetting the position is the most common half-credit answer.
6. Undo while a batch is open. §06 C.
7. Committing an empty batch. §06 C.
8. A no-op edit — same value, empty range, group of one — clearing the redo stack. It must not.

### F. THE SKELETON YOU TYPE FROM BLANK

Target: **under three minutes, no AI, no reference.** It is generic over the change type, which is
the version worth memorising — the document-specific parts are then just `apply` and `invert`, and
you have already written those while building part 1.

```ts
class History<C> {
  private undoStack: C[][] = []
  private redoStack: C[][] = []
  private batch: C[] | null = null

  constructor(
    private readonly apply: (change: C) => void,
    private readonly invert: (change: C) => C,
  ) {}

  do(change: C): void {
    this.apply(change)
    if (this.batch) { this.batch.push(change); return }
    this.undoStack.push([change])
    this.redoStack.length = 0
  }

  undo(): boolean {
    if (this.batch) return false
    const commit = this.undoStack.pop()
    if (!commit) return false
    for (const c of [...commit].reverse()) this.apply(this.invert(c))
    this.redoStack.push(commit)
    return true
  }

  redo(): boolean {
    if (this.batch) return false
    const commit = this.redoStack.pop()
    if (!commit) return false
    for (const c of commit) this.apply(c)
    this.undoStack.push(commit)
    return true
  }

  begin(): void { this.batch ??= [] }

  commit(): void {
    const batch = this.batch
    if (!batch) return
    this.batch = null
    if (batch.length === 0) return
    this.undoStack.push(batch)
    this.redoStack.length = 0
  }

  abort(): void {
    const batch = this.batch
    if (!batch) return
    this.batch = null
    for (const c of [...batch].reverse()) this.apply(this.invert(c))
  }

  get canUndo(): boolean { return !this.batch && this.undoStack.length > 0 }
  get canRedo(): boolean { return !this.batch && this.redoStack.length > 0 }
}
```

**Returning `boolean` from `undo` and `redo` is not decoration** — it is what a UI needs to know
whether to flash, and it makes the "past the beginning" case testable in one line rather than by
inspecting the document. Interviewers notice.

Wire it to a model in three lines:

```ts
const state = new Map<string, number>()
const history = new History<Change>(
  (c) => { if (c.after === undefined) state.delete(c.key); else state.set(c.key, c.after) },
  (c) => ({ ...c, before: c.after, after: c.before }),
)
```

**When to reach for the generic version in the room:** only if the problem is clearly heading
toward "and now also undo the tree operations." For a single-structure problem, the inline version
from §05 A is less ceremony and reads better. Knowing both, and saying which you picked and why, is
the point.

## 07 — Correctness without a test runner

### A. ASK FIRST

You cannot plan the hour without knowing this, so it goes in your first minute (§01 E).

| Answer | What you do |
|---|---|
| **A runner is wired up** | Use it. Green tests on screen are the strongest evidence available, and they make part 2 safe to attempt because you'll know instantly if it broke part 1. |
| **No runner, just run the file** | Write the six-line harness in §07 B and call it after every operation. This is the common case and it is nearly as good. |
| **The pad came with failing tests** | They are the spec. Read them before writing anything, and read them for what parts 2 and 3 will be. |

Whatever the answer, **run the file before minute 20.** Code that has never executed is code with
an unknown number of syntax errors, and finding three of them at minute 50 is how a good hour ends
badly.

### B. THE HARNESS YOU TYPE IN SIXTY SECONDS

```ts
let failures = 0
function check(name: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual), e = JSON.stringify(expected)
  if (a === e) { console.log(`ok   ${name}`); return }
  failures++
  console.log(`FAIL ${name}\n  got  ${a}\n  want ${e}`)
}
```

Three notes that matter in practice:

- **`JSON.stringify` does not serialise a `Map`** — it produces `{}` for every one of them, so two
  different maps compare equal and every test passes. Spread first: `check('x', [...m], [['a',1]])`.
  This bites people mid-interview and looks like magic when it does.
- **Print the name on success too.** A silent pass and a test that never ran look identical, and
  you will be reading this output at a glance.
- **Count failures and print a total at the end.** Scrolling a pad output pane for the word FAIL is
  a waste of the thirty seconds you'll have.

### C. TEST INVARIANTS, NOT EXAMPLES

Three examples tell you three things. One invariant tells you about every input, and stating it is
the behaviour §04 D says is graded. The good ones for this problem family:

| Structure | The property to assert |
|---|---|
| History | For any sequence of ops: `undo` × k then `redo` × k gives back the identical document |
| History | `canUndo` is false exactly when the undo stack is empty — no undo silently does nothing |
| Interval runs | After any operation the runs still tile the string: sorted, contiguous, non-empty, and no two neighbours share a style |
| Tree | After any move, walking parent pointers from every node reaches the root — no cycles, no orphans |
| Reading order | The output is a permutation of the input — same length, same ids |

That last one is worth writing down because it catches the entire class of bugs where a sweep drops
or duplicates an element, and it is one line:

```ts
check('permutation', readingOrder(boxes).map((b) => b.id).sort(), boxes.map((b) => b.id).sort())
```

### D. THE WORKED-EXAMPLE TABLE

Before writing the body, put the cases in a comment at the top of the file. It takes ninety seconds
and it does three jobs: it is your requirements confirmation, it is your test list, and if you run
out of time it is written evidence of what you knew.

```ts
// create A; set fill=red; set fill=blue     -> blue
// ...undo                                   -> red        (previous value, not absent)
// ...undo                                   -> absent     (the key never existed)
// ...redo, redo                             -> blue
// ...undo, set fill=green, redo             -> green      (new work discards the redo branch)
// undo on an empty history                  -> no-op, no throw
```

Read that list out loud as you write it. Line three is the ambiguity from §03 B, and getting it
confirmed there costs nothing and prevents building the wrong thing for forty minutes.

## 08 — Typing fluency with AI off

### A. WHAT DEGRADES, AND WHY IT MATTERS HERE

The screen is sixty minutes with roughly nine of them spent on a data model and API you type from
blank. That is the worst possible place for a fluency tax, because it lands before you have any
momentum and while the interviewer is forming their first impression.

The four things that atrophy fastest with autocomplete on, in the order they will bite:

1. **Class and field declarations with generics.** `private undoStack: Change[][] = []` and
   `new Map<string, Map<string, PropValue>>()` are muscle memory or they are twenty seconds each.
2. **`Map` and `Set` method names under pressure.** `has` / `get` / `set` / `delete` / `size` —
   and `size` is a property, not a method, which is a real error you will make on the clock.
3. **Comparator syntax.** `(a, b) => a.y - b.y || a.x - b.x` typed correctly, first time, without
   thinking about which direction ascending is.
4. **Recovering from a red squiggle with no quick-fix.** Read the message, form a hypothesis,
   check. That loop is slow if unpractised, and it is the loop you will be in at minute 40.

### B. THE RETYPE KIT

**The mode is different from a drill.** Do not re-solve these — retype them cold on a stopwatch,
diff, note only what you got wrong, redo tomorrow. Two clean reps in a row and it's kitted; stop.

| # | Snippet | Target |
|---|---|---:|
| 1 | The `Change` union and `invert` — §04 C | 90 s |
| 2 | A class shell: three private fields with types, a constructor, one public method | 60 s |
| 3 | `check(name, actual, expected)` — the harness in §07 B | 60 s |
| 4 | `boxes.sort((a, b) => a.y - b.y \|\| a.x - b.x)` plus the row sweep — §05 B | 90 s |
| 5 | `normalize(runs)` — §05 C | 90 s |
| 6 | `History<C>` — §06 F | **180 s** |
| 7 | The cycle check `isAncestor` — §05 D | 45 s |
| 8 | `assertInvariants(runs, len)` — §04 D | 60 s |

Run the kit at the end of each study day (§02). It is fifteen minutes, and it is the only part of
prep that directly buys back time in the room.

### C. TYPESCRIPT ERGONOMICS THAT SAVE KEYSTROKES

Decide these now so they cost nothing later.

- **`private readonly x: T` in the constructor parameter list.** Declares and assigns in one place:
  `constructor(private readonly stride = 64) {}`.
- **`??=` and `??`.** `this.batch ??= []` is the whole of `begin()`. `state.get(k) ?? 0` is the
  accumulate idiom.
- **`arr.length = 0`** to clear in place, rather than reassigning — it keeps any other reference to
  the array correct, and it's shorter.
- **`[...arr].reverse()`** — `reverse` mutates, and mutating a history commit while iterating it is
  a bug you will not enjoy finding.
- **`Math.max(0, Math.min(i, arr.length))`** to clamp an index, typed as one unit.
- **Non-null assertion `!` on a `Map.get` you have just checked.** Use it, don't fight it — but say
  *"I've checked this exists above"* when you do, because an unexplained `!` reads as carelessness
  and an explained one reads as deliberate.
- **`strict` is on by default in a CoderPad TS pad.** Let it work for you: type `before` as
  `PropValue | undefined` and the compiler will force you through the absent-key case in §04 C
  rather than letting you skip it.

### D. ASSUME NO WEB SEARCH

The Cursor invitation explicitly allowed web search. **This one does not mention it**, and it does
say they may ask you to share your full screen. Prepare as though the answer is no: nothing in this
guide's code needs a lookup, and if you genuinely need one, ask — *"Do you mind if I check the
exact signature for `splice`?"* — rather than opening a tab and finding out afterwards that it
wasn't allowed.

The practical consequence is that §08 B is not optional polish. It is the mitigation.

## 09 — Figma, enough to be credible

The email says the challenge is *"aligned with the type of work you may encounter at Figma."* You
do not need to be a designer. You need the nouns to be familiar, so that when the problem says
"layer" or "frame" or "component" you hear a data structure rather than a vocabulary word.

### A. PRODUCT SURFACES TO HAVE TOUCHED BEFORE THE 9TH

Half an hour in a real file, once, is worth more than any amount of reading. In rough order of how
likely each is to appear in the problem:

| Do this | The structure underneath |
|---|---|
| Create nested frames, drag a layer between them, reorder in the layers panel | The tree and its sibling z-order — §05 D |
| Select a few layers and hit ⌘G, then ⌘⇧G | Grouping, and where the group lands in the stack |
| Select part of a text layer and bold just that part | Style runs over a range — §05 C |
| Make a component, make a variant, override a property on an instance | Property inheritance and overrides |
| Undo through a burst of edits and notice what counts as one step | Coalescing — §06 D |
| Open the same file in two windows and watch the cursors | Presence, and why ordering needs to be a property |
| Leave a comment pinned to an object | Anchoring an annotation to a moving target |

### B. THE ENGINEERING STORY, IN THREE PARAGRAPHS

From Figma's own engineering blog, which is unusually good and unusually specific. This is for
natural asides and for the *"why Figma"* answer — **do not volunteer it mid-problem**, and never
lead with it.

**The document model.** Figma's document is *"a tree of objects, similar to the HTML DOM,"* and
they describe the shared state as literally `Map<ObjectID, Map<Property, Value>>`. That is §05 A's
data structure, exactly. Their interview question is not Figma-*flavoured*; it is their actual type
signature. If it comes up, that observation is worth one sentence and no more — it lands as
attentive, and belaboured it lands as showing off.

**Sync.** They do **not** use Operational Transforms — the post says OTs were *"unnecessarily
complex for our problem space."* The system is CRDT-*inspired* but, in their words, *"Figma isn't
using true CRDTs"*: because the server is the central authority, they can drop the machinery a
decentralised CRDT needs. Conflicts resolve **last-writer-wins per property**, and clients discard
incoming server changes that conflict with their own unacknowledged edits, so your own edit doesn't
flicker back.

**Ordering, and why it's relevant to you.** Sibling order is **fractional indexing**: an object's
position among its parent's children is a fraction strictly between 0 and 1, so inserting between
two objects is averaging their indices, and there is always room. They store it as an
arbitrary-precision string in base 95 rather than a float, so it cannot run out of precision. Two
details worth having: **parent and position are stored atomically as one property**, so they can
never disagree; and **the server rejects a parent update that would create a cycle** — the same
check you wrote in §05 D, enforced one layer down. If asked "how would two people reorder
concurrently," that is the two-sentence answer.

**Rendering**, for completeness: the editor is a custom renderer running on WebGL rather than the
DOM, with the core compiled to WebAssembly. One sentence is enough unless they pull on it — and if
they do, that is a frontend deep-dive, not this hour.

### C. QUESTIONS TO ASK EMILY

The email promises you time, and running out of questions after "what's the team like" is a
flat ending to an otherwise good hour. Have three, pick by what happened:

| Ask | What it signals |
|---|---|
| *"How much of the team's work is in the core document model versus product surfaces built on top of it? Where would this role sit?"* | You understood what the problem was actually about, and you're thinking about the job. |
| *"What's the hardest thing to test about an editor like this? I found even the small version I just built had a state-space problem."* | Connects the hour you just spent to real work. The best of the three if the coding went well. |
| *"Where does design enter the loop here — do engineers pick up a spec, or build alongside?"* | Figma-specific and honest; design partnership is genuinely part of the job. |
| *"What's changed about how the team works in the time you've been here?"* | Open, personal, and invites the answer you actually want. Good closer. |

**Don't ask** about compensation, levelling, or the rest of the process — those are Perpetua's, and
asking the interviewer reads as misdirected. Don't ask anything answerable from the careers page.

### D. VALUES

Figma publishes both company values and a separate **engineering** values post, and the second is
the useful one — read it if you have twenty minutes. The recurring themes are collaboration over
individual heroics, taking initiative rather than running a playbook, building for builders, and
direct feedback given and received with humility.

*Flagged as medium confidence:* the exact wording of the value list varies across sources and some
aggregators paraphrase it into three bullets. Don't quote a list back at anyone. The behaviour is
what's assessed anyway, and this round assesses it directly: the invitation's *"view your
interviewer as a partner"* **is** the collaboration value, being run as a test. §03 C is how you
pass it.

## 10 — The drills, and how to run them

All eight live in `uie-practice`, under `src/exercises/`. Each ships as a stub plus a **failing**
spec suite:

```
npx vitest run src/exercises/figma-01-document-undo
```

Unlike the `cursor-*` drills, these are plain TypeScript modules — no component, no DOM. Run them
from the terminal; the dev server is only there if you want the prompt on screen.

### A. THE PROTOCOL

Non-negotiable, or the reps measure the wrong thing:

1. **AI off.** Disabled, not merely unused.
2. **Timer visible, started before you read the prompt.**
3. **Narrate out loud, alone, the whole time.**
4. **Do the parts in order, on one clock.** Each drill's spec file gates its later parts behind a
   `part2` / `part3` alias that resolves to `describe.skip`. When part 1 goes green, change
   `part2(` to `describe(` *immediately* and keep the clock running. **The discovery that part 1 made part 2 expensive is the entire training effect** —
   do not restart, do not tidy up first. Note what it cost you, then read §03 D again.
5. **Stop when the timer stops**, then deliver the §03 F closing summary out loud as though someone
   were there.
6. **Grade with §03 G before looking at anything.**
7. **Only then** open §05 and diff.

### B. THE EIGHT

| Slug | Min | What it drills | Why it's on the list |
|---|---:|---|---|
| `figma-01-document-undo` | 45 | Layers, key/value props, `apply`, `undo` | The highest-confidence reported question. Do it cold on D-11 before reading anything. |
| `figma-02-undo-redo-batch` | 40 | Redo · `beginBatch`/`commitBatch` · rollback · nesting | The reported parts 2 and 3, on the same clock |
| `figma-03-reading-order` | 35 | 2-D sort, then the row sweep | The non-transitive comparator trap, felt rather than read — §05 B |
| `figma-04-styled-text-ranges` | 40 | Slice, then apply-and-normalise | The four-clause invariant, and the three-way split |
| `figma-05-layer-tree` | 45 | Group, ungroup, reparent, z-order, cycles | Where the ordered-sequence invariant does real work |
| `figma-06-command-stream` | 35 | Parse → data → step → checkpoint | The unfamiliar-problem fallback shape — §05 E |
| `figma-07-coalescing-history` | 35 | Gesture coalescing, forced boundaries, bounded history | The two follow-ups most likely to arrive if you're fast — §06 D and §04 F |
| `figma-08-sealed` | 50 | **Unknown.** | **Do not read it before D-3.** Forces derivation rather than recall — the only rep that measures the method |

### C. THE FULL MOCK (D-6, Thu 9/3)

Run it at **3:00–4:00 PM**, the real slot, one uninterrupted hour, camera on and recording. Use a
drill you have not done, and treat the sealed one as reserved.

Do the things you would do live and would otherwise skip in practice: spend the first four minutes
on an intro to no one, write the worked-example table, ask your clarifying questions out loud and
answer them yourself, and stop at minute 54 to give the summary. Then watch the first ten minutes
back. Openings are where the round is won and they are the most reliably fixable part of it.

If you can get a person for it, do — an interviewer who interrupts, renames your variables, and
adds an edge case at minute 38 changes the round in ways a timer cannot simulate, and that
interruption pattern is specifically what §01 C says to expect.

## 11 — Day-of runbook

### A. THE NIGHT BEFORE (Tue 9/8)

- **Sign the NDA**, and do it off the VPN — the invitation itself warns the link fails behind one.
- **Decide on Brighthire.** Opting out is explicitly consequence-free. Deciding at 3:01 is not.
- **Open the CoderPad link**, set the language to TypeScript, type and run one line to confirm the
  runtime works, then clear it. Confirm whether tests can run.
- **Zoom: filters, virtual background, and blur all off.** Test the camera and mic. The invitation
  asks for them off at the start of the interview; having them off already is one less thing.
- **A clean desktop and a clean browser profile**, because a full-screen share may be requested.
  Close everything with an AI assistant in it. This is the single easiest way to create an
  unnecessary problem.
- **Retype kit once**, untimed. Nothing new. Do not read §05 for the first time tonight.
- **On one card, where you can see it:** *nine minutes before logic · one choke point · say the
  invariant · run it · stop at 54.*

### B. THE HOUR BEFORE

- Join five minutes early, as asked.
- **One warm-up rep, ten minutes, no pressure** — type `History<C>` from blank and delete it. Cold
  hands on a first data model is a real and avoidable tax.
- Water within reach. A notepad for the worked-example table if you'd rather write it by hand
  first — but it goes in the pad as a comment either way, because it's evidence.

### C. THE FIRST FIVE MINUTES

Camera on, filters off, introduce yourself in about forty-five seconds. Then, when the problem
lands: **do not type.** Restate it, run one example by hand out loud, ask your two or three
questions, and ask whether there's a part 2 you should keep in mind. §03 B.

### D. THE MIDDLE

- Types and signatures before bodies.
- One mutation choke point, and say why you're building it.
- Say the invariant before the code that maintains it.
- Run something by minute 20.
- Take every nudge immediately.
- Never silent for more than about twenty seconds.

### E. THE LAST TEN MINUTES

At **54**, stop wherever you are and give the §03 F summary: what works, what you'd do next in
priority order, what you'd revisit. Then ask your questions — you have three from §09 C and the
email promised you the time.

### F. AFTERWARDS

Write down, within an hour and before you do anything else: the problem, every part they added and
in what order, every question they asked, and the two moments you'd play differently. It is the
only record that exists, it decays fast, and if there is an onsite it is the most valuable single
page you will have.

Then reply-all to Perpetua's email if you haven't already, and open `Design Figma` under Designs —
that round is two system design hours, and it is a different guide.
