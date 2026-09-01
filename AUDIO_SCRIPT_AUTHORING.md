# Audio Script Authoring Spec

The schema every narration episode follows, the standing rules that make one listenable, and the
steps to publish. **This is the file you hand to Claude Code when you want an episode written.**

Scripts live in `src/data/audio/scripts/` and are synthesized to mp3 by `npm run audio:synth`.

**For setup, commands, publishing, cost, and current state, see `AUDIO_PIPELINE.md`.** This file is
only about how an episode is written.

---

## What this format is for

Reading happens at a laptop. This format exists for the hours that aren't — driving, lifting,
walking. That single fact drives every rule below, because a listener:

- **cannot scroll back.** Anything they need later has to be restated, not referenced.
- **cannot see.** Tables, code, diagrams, bold, and section numbers do not exist.
- **cannot pause to parse.** `aria-activedescendant` costs a fluent reader nothing and a listener
  the next two sentences.
- **is doing something else.** Attention drops out for ten seconds at a time and has to be able to
  rejoin.

An episode is not a guide section read aloud. It is a **different artifact derived from the same
material**, and it is written, not generated.

---

## Layout on disk

```
src/data/audio/
  manifest.json                  the episode list — order, source, title, status
  pronunciations.json            alias rules uploaded to the ElevenLabs dictionary
  scripts/
    design-figma-03-dives-a.md   one file per episode
    sysdesign-05-correctness.md
    tech-02-queues.md
```

Episode ids are `<corpus>-<NN>-<slug>`, where corpus is `design-<page>`, `sysdesign`, or `tech`.
The number sets play order within the corpus. The id is the mp3 filename and the permanent RSS
`guid`, so **once an episode is published its id never changes.** Rewriting the script is fine;
renaming the file orphans it in every subscriber's app.

---

## The required header block

The pipeline parses this. Every script opens with exactly:

```markdown
---
id: design-figma-03-dives-a
title: "Figma — why not OT, and what last-write-wins costs"
source: src/data/designs/design-figma.md §7–9
minutes: 9
---
```

Everything after the front matter is **spoken text and nothing else**. No headings, no bullets, no
bold, no code fences, no links. If it can't be said, it doesn't belong in the file. Paragraph breaks
are the only structure, and they become breathing pauses.

---

## Episode shape

| beat | length | what it does |
|---|---|---|
| **Cold open** | ~20s | The question this episode answers, asked as a question. No throat-clearing. |
| **The count** | ~10s | "Three deep dives, and the third is the one people get wrong." |
| **Body** | 7–8 min | The beats below, in order, one idea at a time. |
| **Recap** | ~40s | The two or three things to carry. Restated in full, not referenced. |

Target **1,200–1,500 words**. The hard ceiling is **8,500 characters** — above that the episode no
longer fits in a single synthesis request, and `npm run audio:synth -- --dry-run` will fail it.

For a design-page deep dive, the body inherits the four beats the page already mandates: **the naive
answer → what breaks, with a mechanism or a number → what replaces it → what the replacement costs.**
Do not invent a different structure. It survives linearization because each beat sets up the next.

---

## Standing rules

**Announce the count, then deliver it.** "Three costs, and the third is the one people miss." A
listener who knows how many are coming can hold them; one who doesn't loses track at two.

**No visual deixis. Ever.** No "the table above," "as shown," "see section 11," "the diagram." Cross
references become temporal or restated: "we'll come back to this," "in the last episode," or — best —
say the thing again in six words.

**A number is only worth saying with its consequence attached.** `| APNs payload | 4 KB |` narrates
as "the payload ceiling is four kilobytes, which is why the notification is a hint and your database
is the truth." A number that doesn't change a decision gets cut, not narrated. This is the audio form
of the guide's own "numbers or nothing" rule.

**Identifiers get paraphrased, expanded, or dropped.** `fill` becomes "the fill property."
`410 Unregistered` becomes "a four-ten Unregistered response." `SKIP LOCKED` becomes "Postgres's
skip-locked clause." Anything left that must be said exactly goes in `pronunciations.json`.

**Code is described, never read.** One sentence for the shape — "the handler is four lines: clamp the
index, wrap at both ends, and bail early on anything you didn't handle" — or move the episode boundary
so the code falls outside it. Never spell out syntax.

**Write in spoken form; normalization is off.** The synthesizer's auto-normalization is disabled so
output is deterministic, which means **you** own it. Write "ninety-nine point nine percent," not
"99.9%". Write "two thousand twenty-four," not "2024". No URLs, no file paths, no bare symbols.

**Acronyms need a decision.** Either spell it with periods so it's read letter by letter — `O.T.`,
`C.R.D.T.`, `A.P.I.` — or write it as the word it's said as: "squeal" for SQL if that's how you say
it. Never leave a bare capitalized string and hope.

**One idea per paragraph, and the paragraph opens with it.** The listener who rejoined halfway
through needs the first clause to tell them what this one is about.

**Contractions and second person.** "You'd be paying for a problem you designed away" beats "one
would be paying." This is the register your design pages already use — keep it.

**End on the sentence you'd say in the room.** The last line of the body should be something worth
repeating to an interviewer. The recap then restates it.

---

## Cadence, and why lists fail

A list is where narration most reliably falls apart. "Three things. How it works. What it
guarantees. And the buy decision." reads fine and *sounds* like one long run-on, because nothing in
the text tells the model these are three separate beats. Announcing the count buys you nothing if
the delivery doesn't honor it.

Three levers, in order of how much you should lean on them.

**1. Ordinals, always.** Never a bare list of fragments. Every item opens with `First,` `Second,`
`And third,` — the word itself is the cadence cue, and it's also what lets a listener who drifted
out rejoin at item three.

**2. One sentence per item, ending in a full stop.** Fragments joined by commas get read as one
breath. A period is the strongest pacing signal in the text, and it costs nothing.

**3. `<break time="0.8s" />` at the beats that matter.** Supported on multilingual v2 (v3 does not
support break tags at all, which is one of several reasons this project stays on v2). Cap is three
seconds.

> **Use break tags sparingly.** ElevenLabs' own warning: "using too many break tags in a single
> generation can cause instability — the AI might speed up, or introduce additional noises or audio
> artifacts." The linter fails an episode over twelve. In practice you want them only after the
> count announcement, between list items, and before the closing recap. Nowhere else — paragraph
> breaks already give you a natural pause.

Before and after, from the push notifications episode:

```
Three things. How it actually works, and the part of it that bites. What the delivery
contract really guarantees, which is less than you think. And the build-versus-buy line,
which is not where most people draw it.
```

```
Three things. <break time="0.8s" /> First, how it actually works — and the part of it
that bites. <break time="0.7s" /> Second, what the delivery contract really guarantees.
Which is less than you think. <break time="0.7s" /> And third, the build-versus-buy line,
which is not where most people draw it.
```

**Global pace is a setting, not a script problem.** `voiceSettings.speed` in the manifest runs
0.7 to 1.2, default 1.0. Long-form technical narration wants roughly 0.9 — slow enough to hold a
definition, not so slow it drags over nine hours. Fix pace there; fix *rhythm* in the script. They
are different problems and the settings dial cannot solve the second one.

---

## Worked example

Source, from `src/data/designs/design-figma.md`:

> **What breaks.** OT requires a transformation function for **every ordered pair of operation
> types**. With a rich object model — set property, create, delete, reparent, reorder, group — that
> is quadratic in the number of operation types, and the functions are individually subtle. Figma's
> own writeup is blunt about it: OTs were *"unnecessarily complex for our problem space"*. The deeper
> point is that **OT is machinery for editing a sequence**, where an insert at position 4 changes
> what position 7 means. Setting `fill` on object `abc` does not change what any other property
> means. **You would be paying for a problem you designed away in §4.**

Script:

> So why not just use Operational Transformation? It's the obvious move — Google Docs does it, and
> it's the first thing most people reach for.
>
> Here's where it falls down. O.T. needs a transformation function for every ordered pair of
> operation types. Set property, create, delete, reparent, reorder, group — that's quadratic in the
> number of operation types, and every one of those functions is individually subtle. Figma's own
> engineering writeup is blunt about it. They call O.T., quote, unnecessarily complex for our problem
> space, end quote.
>
> But the deeper point is the one worth carrying out of this episode. O.T. is machinery for editing a
> sequence — where inserting at position four changes what position seven means. Setting the fill
> property on an object doesn't change what any other property means. So you'd be paying for a
> problem the data model already designed away.

What changed, and why:

| source | script | rule |
|---|---|---|
| `§4` | "the data model already designed away" | no visual deixis |
| `` `fill` `` on `` `abc` `` | "the fill property on an object" | identifiers paraphrased |
| "OT" | "O.T." | acronyms need a decision |
| bold lead-ins | spoken transitions | structure signaled by words |
| the block quote | "quote … end quote" | attribution has to be audible |
| — | "worth carrying out of this episode" | forward-announcement |

---

## Self-check before synthesizing

Run this against the finished script. Each line maps to a rule above.

- [ ] Front matter complete; `id` matches the filename and has never been published under another name
- [ ] Body is spoken text only — no headings, bullets, bold, fences, links, or markdown of any kind
- [ ] Under 8,500 characters (`npm run audio:synth -- --dry-run` confirms)
- [ ] Opens with the question, closes with a full restatement — not a reference
- [ ] Every list is preceded by its count **and every item opens with an ordinal**
- [ ] Break tags only at count announcements, between list items, and before the recap — twelve max
- [ ] **Zero** section numbers, file paths, URLs, or "above/below/as shown"
- [ ] Every number has a consequence attached, or is cut
- [ ] Every acronym is either dotted or written as the word it's said as
- [ ] Numerals, percentages, and dates are written out in words
- [ ] Read one paragraph at random aloud — if you stumble, the sentence is too long

---

## Generation prompt

> Write `src/data/audio/scripts/<id>.md` following `AUDIO_SCRIPT_AUTHORING.md`, from
> `<source file> <sections>`. Spoken text only after the front matter — no markdown in the body.
> Announce every count before delivering it. Convert tables to sentences with the consequence
> attached, and cut any number that doesn't change a decision. Replace every section cross-reference
> with a temporal one or a six-word restatement. Dot every acronym or write it as the word it's said
> as. Write all numerals out in words. Target 1,300 words, hard ceiling 8,500 characters. Close on a
> sentence worth saying in an interview, then recap it. Then run the self-check list.
