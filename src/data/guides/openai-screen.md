# OpenAI Screen — Wed 9/16 (Architecture) & Thu 9/17 (Coding)

> Two sixty-minute rounds on consecutive days. **9/16 is architecture**, on a whiteboard.
> **9/17 is coding**, in CoderPad. This guide is the twenty-eight-day plan, both round scripts,
> a researched question bank ranked by probability, and the two chapters that decide the coding
> hour: **text streaming** and **text-editor concepts**.

Companion to `Cursor Screen` (the other AI-company two-round screen — read `§04` there for the
client-side design checklist, which transfers wholesale) and `UIE Components` (the component
library; `§14 Streaming message` is the single most load-bearing section in this repo for 9/17).
Neither covers what makes OpenAI different: **the loop is fullstack even when the title says
frontend**, and the coding round is a real product surface — a chat transcript, a composer, an
editor — not a component in isolation.

**What this guide deliberately does not repeat.** The general design loop lives in
`System Design` and `Designs → Interview mechanics`. The run lifecycle, resumable streaming, GPU
scheduling, and context cost live in `Designs → ChatGPT`. Retrieval and evals live in
`System Design §11–§12`. Inference serving under a latency ceiling lives in
`Designs → Cursor Tab`. Component ARIA contracts live in `UIE Components`. This guide is the
OpenAI-shaped delta on top of those, plus the coverage map in `§03 F` telling you exactly which
existing pages to reread and which material is new.

## 01 — The two rounds, and what is actually graded

### A. THE FORMAT

| | Wed 9/16 — Architecture | Thu 9/17 — Coding |
|---|---|---|
| **Length** | 60 minutes | 60 minutes |
| **Tool** | Online whiteboard, typically **Excalidraw** | **CoderPad** (occasionally CodeSignal or a local IDE) |
| **Shape** | One open-ended design, driven by your requirements pass | One practical problem, extended in parts by follow-up |
| **Interviewer** | One engineer, working-session posture | One engineer, working-session posture |
| **Scope** | UI wireframe → API contract → storage → scale | React + TypeScript, or plain TS |
| **Graded on** | Requirements discipline, trade-off reasoning, depth on chosen tech, behaviour at 10×/100×/1000× | Solution design, code quality, performance, **test coverage**, communication |
| **AI tools** | Assume not allowed unless the recruiter says otherwise — confirm | Same. CoderPad has no Copilot |

**Two rounds on two days is the standard OpenAI screen**, split for scheduling rather than
significance. Reported loops describe the screen as "two 60-minute rounds, coding plus system
design," sometimes same-day. Yours is split, which is a small gift: `§13` uses the evening of the
16th for a specific purpose.

**Order matters and it is in your favour.** Architecture first means that by the time you sit down
on the 17th you will have already said out loud, to an OpenAI engineer, how a streaming response
travels from a GPU to a DOM node. The coding round is then the same story at a smaller scale. Reuse
the vocabulary deliberately — see `§13 C`.

### B. THE ONE SENTENCE THAT REFRAMES BOTH ROUNDS

> **OpenAI's product-engineering loop is fullstack, and the title on the req does not change that.**

This is the single most repeated point across community reports, and it is the thing that fails
otherwise-strong frontend candidates. The evidence:

- Multiple Blind threads on the OpenAI front-end loop report the format changed, with one commenter
  stating flatly that the "frontend interview now is mainly focused on backend topics."
- Prep sites converge on the same read: newer reports suggest OpenAI frontend roles have shifted
  toward **fullstack loops more often than pure frontend loops**, with system design expected to
  cover backend data flow while still going deep on the client.
- OpenAI's Applied AI team is reported to expect all engineers to be fullstack, and recruiters say
  so explicitly.

**What that means concretely for 9/16.** If you are asked "design ChatGPT" and you draw a React
component tree, a state model, and a hook, you have answered a third of the question and will run
out of things to say at minute thirty. The expected arc is:

```
wireframe  →  client state model  →  API contract  →  transport  →  service boundaries
    →  storage schema  →  the GPU/queue reality behind it  →  10× / 100× / 1000×
```

You are allowed — encouraged — to be *deepest* on the client. You are not allowed to stop there.
`§04 C` is the script for saying this out loud in a way that reads as range rather than hedging.

### C. WHAT IS KNOWN ABOUT THE BAR, BY CONFIDENCE

Sources on OpenAI's frontend loop are thinner and noisier than for Figma or Discord. There is no
public candidate handbook and the invitation email is terse. Everything below is tiered so you know
what to bet on.

| Confidence | Claim | Basis |
|---|---|---|
| **High** | Two 60-min rounds, coding + system design, CoderPad and a whiteboard | Your own invitation, corroborated by every loop write-up |
| **High** | OpenAI's stated engineering bar: *well-designed solutions, high-quality code, performance, test coverage, communication, collaboration* | OpenAI's own careers guidance, quoted consistently across prep sites |
| **High** | The design round pushes 10× / 100× / 1000× and asks you to justify any named technology | Repeated in every OpenAI system-design write-up |
| **High** | Streaming is the house theme; a streaming chat surface is the most-reported frontend prompt | Converges across GreatFrontend, PracHub, TechPrep, Exponent |
| **Medium-high** | The loop is fullstack in practice for product/frontend roles | Blind commenters + multiple prep-site claims, no primary doc |
| **Medium-high** | Coding problems are **multi-part**: a core, then three or four extensions | Exponent and interviewing.io both describe "practical, multi-part questions" with heavy follow-up |
| **Medium** | Questions rotate every few months and vary a lot by interviewer | Exponent states this explicitly |
| **Medium** | Named design prompts in circulation: *Design the OpenAI Playground*, *Design Slack with 100×/1000× follow-ups*, *Design a ChatGPT-style assistant*, *design a streaming platform at aggressive growth* | Exponent's reported question list; PracHub's bank |
| **Medium** | Named coding prompts in circulation: streaming chat UI, iterator → 2D → async, spreadsheet cell references with propagation, time-based / versioned key-value store, refactor nested code while keeping tests green | Exponent + interviewing.io + PracHub |
| **Low-medium** | The specific Discord report you have — text streaming plus text-editor concepts | Single second-hand report. Treated seriously in `§01 D` because it is *consistent* with everything above, not because one report is evidence |
| **Low** | Anything about a take-home. Some OpenAI tracks use one; there is no sign yours does | Prep-site claims about "48-hour work trials" attach to applied/research tracks |

**How to use the tiering.** Prepare hard for High and Medium-high. Read the Medium rows once so no
prompt is a surprise. Do not build a study plan around Low rows — but note that the Low-medium row
is the reason `§09` exists, and `§09` is cheap insurance that also pays off on Tier-1 material.

### D. THE DISCORD REPORT, DECODED

The report you have: someone failed the OpenAI frontend screen on a problem involving **text
streaming and text-editor concepts.**

That is a thin datum, and second-hand. But it is worth taking seriously because it is not a
*surprising* datum — it is the intersection of two things that were independently predictable:

**1. Text streaming is OpenAI's signature frontend problem.** Every source agrees. The prompt is
some version of "build a minimal chat interface where the assistant's reply streams in token by
token." Requirements reported alongside it: incremental rendering, async state management, keeping
the UI responsive, preventing duplicate submits, loading/error/cancel states.

**2. "Text editor concepts" is what the *other* half of a chat surface is made of.** The half
people don't practise. Every ChatGPT-shaped product has an editing surface, and it is where the
fiddly correctness lives:

| Surface | Editor concepts it forces |
|---|---|
| The composer | Caret position, `selectionStart`/`selectionEnd`, `setRangeText`, auto-resize, Enter vs Shift+Enter, IME composition, preserving native undo |
| Edit a previous message | Controlled/uncontrolled swap, cancel restores the pre-image, resubmission truncates the transcript below it |
| `@`-mention / slash command | Trigger detection on a token before the caret, anchored popup, insertion that rewrites a *range*, not the whole value |
| Canvas / artifact editing | A document model with insert/delete ops, cursor transform across remote edits, undo/redo as inverse ops |
| Streaming *into* an editor | Two writers on one buffer: the model and the human |

**The most likely single problem, stated plainly.** If the report is accurate and the pattern
holds, the highest-probability shape for 9/17 is:

> **A chat surface where the assistant response streams in, and one part of the problem makes the
> text surface itself non-trivial** — either the composer gains behaviour (mentions, slash
> commands, Enter semantics, auto-resize), or the transcript becomes editable (edit-and-resubmit),
> or the streamed output lands in an editable document rather than a read-only bubble.

That is one problem, not two. `§08` and `§09` are its two halves, and `§08 J` is the seam.

**The failure mode this predicts.** Not "couldn't build a chat UI." It is running out of clock
because the streaming half consumed forty minutes, and then meeting a caret/selection extension
cold. Streaming is the part you can make automatic; `§08 F` is a skeleton to be able to type in
under six minutes so that the editor extension gets the time it needs.

### E. CODERPAD AND EXCALIDRAW: THE FIRST NINETY SECONDS

**CoderPad, 9/17.** Every report notes that candidates who lean on IDE completion struggle in the
transition, and that time is tight. Before you write a line:

1. **Set the pad to a React + TypeScript sandbox** if the interviewer hasn't. Say "give me ten
   seconds to get a preview running" — a visible render loop is worth minutes later.
2. **Confirm what runs.** Is there a preview pane? Does it have a test runner? Ask: *"Can I run
   tests in here, or should I write them as a spec I talk through?"* This one question changes your
   whole plan for the test-coverage axis, which OpenAI grades explicitly.
3. **Confirm the network story.** *"Should I assume a real endpoint, or write a mock stream
   generator?"* Nine times in ten the answer is mock it. **Have the mock in your fingers** —
   `§08 K` is twelve lines.
4. **Type a scaffold immediately.** Empty component, one `useState`, one render. A blank pad at
   minute six is a bad look; a rendering skeleton at minute two buys you narration room.

**Excalidraw, 9/16.** Same principle: reduce tool friction to zero.

1. **Make four regions before you draw anything**: `CLIENT` top-left, `API` top-right,
   `SERVICES` bottom-right, `NOTES / NUMBERS` down the left margin. Announce it: *"I'll keep
   requirements and numbers in this column so we can point back at them."*
2. **The notes column is the scoring surface.** Write functional requirements, non-functional
   requirements, and the two or three numbers you derive there, and **never erase them**. When the
   interviewer pushes to 1000×, you point at the number rather than re-deriving it.
3. **Rectangle, arrow, text. That is the whole tool.** Do not colour-code, do not use the library.
4. **Wireframe first, and literally.** For an OpenAI prompt, a small box-drawing of the actual
   screen — transcript, composer, model controls, stop button — earns more in the first five
   minutes than any box-and-arrow diagram, because it is what makes the requirements concrete.

### F. HOW THIS GUIDE RELATES TO THE OTHERS

You are four weeks out with a large amount of relevant material already written. The mistake would
be to treat this as a fresh subject. It is mostly a **re-index** of what you have.

| Need | Where it already lives | Status |
|---|---|---|
| Streaming component, full implementation | `UIE Components §14` | **Reread first. Highest-value page in the repo for 9/17** |
| Client-side design: transport ladder, backpressure, resumability, cache, failure pass | `Cursor Screen §04` | Transfers wholesale. Reread before 9/16 |
| Streaming multi-part edits, agent chat design | `Cursor Screen §05 B` | Closest existing worked design to the OpenAI prompt |
| Run lifecycle, resumable SSE, TTFT, prefill vs decode, prompt-cache ordering, cost | `Designs → ChatGPT §7–§11` | The backend depth for 9/16 |
| Inference serving, GPU scheduling, cancellation reaching the GPU | `Designs → Cursor Tab §9–§10` | Reuse for the queue/GPU half |
| Undo/redo, inverse ops, batching, coalescing | `Figma Screen §06` | The document-model half of `§09` |
| Command/inverse pattern, document invariants | `Figma Screen §04` | Same |
| Race guards: abort + generation counter | `UIE Components §17 F` | Memorise. It appears in both rounds |
| Debounce/throttle in React, key handler placement | `UIE Components §17 K, §17 M` | Composer behaviour |
| Roving tabindex, focus trap, live regions | `UIE Components §17 A, B, E` | The a11y extension |
| Combobox / typeahead full build | `UIE Components §06` | The `@`-mention popup is this component |
| Virtualized list | `UIE Components §13` | The "thousands of messages" follow-up |
| Requirements → NFR → numbers loop, the 45-minute clock | `System Design §01`, `Designs → Interview mechanics` | The 9/16 spine |
| Design a conversational AI service end to end | **New — `§06 A` here** | |
| Composer / caret / selection / IME | **New — `§09` here** | |
| Streaming into an editable document | **New — `§08 J` and `§09 F` here** | |
| Incremental markdown rendering | **New — `§08 I` here** | |
| Resumable streams, server-side | **New — `§05 E` here** | |

`§03 F` turns this into a per-problem checklist.

### G. THE FIVE-MINUTE VERSION

If you read nothing else in this guide, read this.

1. **The loop is fullstack.** Go deepest on the client, but reach storage and scale, or 9/16 stalls.
2. **Streaming is the house theme.** A token stream from a GPU to a DOM node is the mechanism
   under nearly every OpenAI prompt in both rounds. Know it end to end.
3. **On 9/17, expect a multi-part problem.** Core chat + stream, then extensions: stop, multi-turn,
   cancellation with stale-response guards, scroll pinning, accessibility, edit-and-resubmit,
   mentions. Build the core in twenty minutes so extensions have room.
4. **The four things that always earn on the coding round**: an explicit status enum (never
   `isLoading`), `AbortController` wired to lifecycle *and* to Stop, a generation counter so late
   tokens are dropped rather than merely un-requested, and batching so a 500-chunk response is not
   500 renders.
5. **Test coverage is a named axis at OpenAI.** Even if the pad can't run tests, say the five tests
   out loud and write two. Most candidates write zero.
6. **`TextDecoder` with `{ stream: true }`.** A multi-byte character split across two chunks is the
   canonical "did you actually stream" tell.
7. **On 9/16, put numbers in the margin and never erase them.** When they push 1000×, point.
8. **Anything you name, you own.** Say "SSE" and be ready for why not WebSocket, what happens on
   reconnect, and what a proxy does to it.
9. **An abort is not an error.** The user pressing Stop and the network dying produce the same
   rejected promise and must produce different UI.
10. **Mission questions are real.** OpenAI weights "why here, and where could this go wrong"
    heavily, and it is asked in technical rounds too. `§11 D` is your draft.

## 02 — The twenty-eight-day schedule

Today is Wed 8/19. Architecture is Wed 9/16, coding is Thu 9/17. That is four clean weeks, but they
are not empty weeks: **Discord is 8/26, Cursor is 8/28, Figma is 9/9.** The plan below assumes
those three screens own their surrounding days and takes what is left.

The good news is that the overlap is enormous. Cursor prep *is* OpenAI streaming prep. Figma prep
*is* OpenAI editor prep. Weeks 1 and 2 below are mostly labelled "borrowed" for that reason — you
are not adding four weeks of work, you are adding about six focused sessions plus two mocks.

| Window | Days | Focus | Session |
|---|---|---|---|
| **Week 1 — borrowed** | Thu 8/20 – Wed 8/26 | Discord screen owns this week | — |
| | Thu 8/20 | 45 min | Read `§01`, `§03`, `§08` of this guide. No coding. Just load the shape |
| | Sat 8/22 | 60 min | Type the `§08 F` streaming skeleton from blank. Twice. Time it |
| | Wed 8/26 | — | **Discord screen** |
| **Week 2 — borrowed** | Thu 8/27 – Wed 9/2 | Cursor screen owns this week | — |
| | Thu 8/27 | — | Cursor prep — `Cursor Screen §04` is OpenAI `§05` material. Read it as both |
| | Fri 8/28 | — | **Cursor screen.** Write down the design round's questions the same evening |
| | Sat 8/29 | 90 min | Drill 1: **Streaming chat, core** (`§12 B`). Target: working stream + stop in 30 min |
| | Sun 8/30 | 60 min | Drill 2: **The composer** (`§09 B`). Enter/Shift+Enter, auto-resize, IME |
| | Tue 9/1 | 60 min | Design rep 1: **Design a ChatGPT-style assistant** (`§06 A`), full hour, out loud |
| **Week 3 — Figma week, split** | Thu 9/3 – Wed 9/9 | Figma owns Mon–Wed | — |
| | Thu 9/3 | 90 min | Drill 3: **Streaming, part 2 — multi-turn + cancellation + stale guards** |
| | Sat 9/5 | 90 min | Drill 4: **`@`-mention autocomplete in a textarea** (`§09 C`). The caret-anchored popup |
| | Sun 9/6 | 60 min | Design rep 2: **Design the OpenAI Playground** (`§06 B`) |
| | Tue 9/8 | 30 min | Light. Reread `§08 D` (the reader loop) and `§17 F` of `UIE Components` |
| | Wed 9/9 | — | **Figma screen.** Its document-model work is `§09 E` here — note what transferred |
| **Week 4 — OpenAI week** | Thu 9/10 – Thu 9/17 | This is the only week that is fully yours | |
| | Thu 9/10 | 90 min | Drill 5: **Edit-and-resubmit a transcript message** (`§09 D`). The controlled-swap problem |
| | Fri 9/11 | 90 min | Design rep 3: **Design Canvas / artifact co-editing** (`§06 C`). The hardest of the five |
| | Sat 9/12 | 2 hr | **Full mock, coding.** One 60-min timed problem from `§03 B` picked blind, then a 30-min self-grade against `§07 F` |
| | Sun 9/13 | 2 hr | **Full mock, architecture.** 60 min on a prompt picked blind from `§03 C`, whiteboard, out loud, recorded. Self-grade against `§04 F` |
| | Mon 9/14 | 90 min | Drill 6: **Streaming markdown** (`§08 I`) + **scroll pinning** (`§08 H`). The two extensions people fumble |
| | Tue 9/15 | 60 min | Design rep 4: **Codex-style agent task run** (`§06 D`). Then `§11`: products, story, questions |
| | Wed 9/16 | — | **Architecture round.** `§13 A` is the runbook. That evening: `§13 C`, twenty minutes |
| | Thu 9/17 | — | **Coding round.** `§13 D` |

**If the schedule slips**, drop in this order: design rep 4, drill 6, design rep 2. **Never drop**
the two Week-4 mocks or drills 1 and 2 — they are the load-bearing reps.

**The standing daily commitment** is the `openai` track in Morning Recall, from 8/20. Twelve cards a
day, five minutes, no exceptions. It is what makes `§08` and `§09` retrievable under clock pressure
rather than merely read.

## 03 — The question bank

### A. HOW THIS BANK WAS BUILT, AND HOW MUCH TO TRUST IT

There is no leaked OpenAI question list. What exists is a set of reported prompts, scattered across
Blind threads, prep-site question banks, and interview-experience aggregators, plus OpenAI's own
public statement of what engineering interviews look for. The bank below is those reports, deduped,
grouped by the *technique* each demands, and ranked.

**Rank by technique, not by title.** Question titles rotate every few months; the techniques do
not. Two prompts that sound different — "build a streaming chat input" and "build a chatbot-style
chat interface with status tracking" — are the same four techniques with different framing. Prepare
techniques and you cover both plus the one that hasn't been reported yet.

**The four techniques that cover most of the coding bank:**

| # | Technique | Appears in |
|---|---|---|
| **1** | Consuming an async source incrementally and rendering it without melting | Streaming chat, autocomplete, iterators, progress |
| **2** | An explicit state machine with impossible states excluded | Every one of them. This is the code-quality axis |
| **3** | Cancellation and staleness: abort, generation counters, request ids | Streaming, autocomplete, any concurrent fetch |
| **4** | Text-surface mechanics: caret, selection, ranges, insert/delete | Composer, mentions, edit-in-place, canvas |

### B. THE CODING ROUND BANK (9/17), RANKED

**Tier 1 — prepare to build cold, under clock.** If one of these appears you should be at a
working core in twenty minutes.

| Prompt | What it really tests | Reported as |
|---|---|---|
| **Streaming chat interface** — user types a prompt, the assistant's reply streams in token by token below the input | Reader loop, `TextDecoder`, status enum, duplicate-submit guard, batching, abort, error/retry | The most-reported OpenAI frontend prompt, by a distance |
| **Stop generating** — added to the above | Abort *and* generation counter; abort ≠ error; keep the partial text | The canonical follow-up |
| **Multi-turn transcript** — extend the single turn into a conversation | Message list model, only one streaming assistant message at a time, keying, scroll | Reported as part 2 of the streaming problem |
| **Cancellation with request ids** — new submit while one is in flight | Stale-response suppression; the interleaving question | Reported as part 3 |
| **Autocomplete / typeahead with proper cancellation** | Debounce, abort, out-of-order response suppression, keyboard, ARIA combobox | Named repeatedly as an OpenAI frontend prompt |
| **The composer** — auto-resize, Enter to send, Shift+Enter for newline | Caret, `selectionStart`, IME composition, controlled input, key handling | "Editable text areas" is on every OpenAI frontend prep list |

**Tier 2 — know the shape, expect as an extension rather than the whole problem.**

| Prompt | What it really tests |
|---|---|
| **Scroll pinning** — stick to the bottom while streaming, but respect a user who scrolled up | `scrollHeight`/`scrollTop`/`clientHeight` arithmetic, an intent flag, a `ResizeObserver` |
| **Streaming markdown** — render the streamed text as markdown as it arrives | Incremental parse, unclosed fences and half-written emphasis, debounced reparse |
| **Edit a previous message and resubmit** | Controlled/uncontrolled swap, cancel restores the pre-image, truncating the transcript below the edited turn |
| **`@`-mention or `/`-command autocomplete in the composer** | Trigger token before the caret, `setRangeText`, anchored popup, combobox ARIA |
| **Accessible announcements for a stream** | *Not* `aria-live` on the streamed text. A batched `role="status"` line. See `UIE Components §14 C` |
| **Thousands of messages** — keep it responsive | Virtualization with variable heights, or a windowed transcript with a "jump to latest" |
| **Refactor deeply nested code to support a new requirement, keeping tests green** | Reported at OpenAI explicitly. Read the tests first; change structure, not behaviour |
| **Build an iterator: sequence → 2D → async** | Reported at OpenAI explicitly. `Symbol.iterator`, then `Symbol.asyncIterator`, laziness, early exit |

**Tier 3 — reported at OpenAI but off the frontend path. Read once; do not drill.**

- Spreadsheet-style cell references with formula propagation (a dependency graph plus cycle
  detection — the frontend version of this is a computed-value store).
- Time-based / versioned key-value store; a set with readable snapshots and `containsAt`.
- Encode and decode a list of strings; LRU cache; a sliding-window rate limiter.
- `debounce` from scratch and where you'd use it; `Promise.all`/`race` reimplementations.
- "Why is this React component rendering twice on every update" — a debugging prompt. The answer is
  usually StrictMode in dev, an unstable dependency identity, or a parent re-render with no memo.
- CORS: how you'd handle it safely from the frontend.

**The one-line rule for Tier 3.** If it appears, it will be *one* of these, it will be
self-contained, and it is a fundamentals check rather than the round's substance. Do not spend
Week 4 here.

### C. THE ARCHITECTURE ROUND BANK (9/16), RANKED

The strongest single signal about this round is that reported prompts cluster into **three
families**, and OpenAI's own products supply most of them.

**Family 1 — the streaming conversational product.** Highest probability, and the one `§06 A`
works end to end.

| Prompt | Where the depth lands |
|---|---|
| **Design a ChatGPT-style assistant** — UX, conversation state, message streaming, model invocation, safety | Transport choice, TTFT, conversation storage, context truncation, GPU scheduling, rate limits by tier |
| **Design a highly available conversational AI service** | The same, with failover, resumability, and what happens when a generation node dies mid-response |
| **Design a large-scale streaming AI product feature** for many concurrent users | Fanout, backpressure, cost per token, admission control |

**Family 2 — the developer-facing surface.** Reported by name.

| Prompt | Where the depth lands |
|---|---|
| **Design the OpenAI Playground** — UI through architecture | Model controls as state, shareable/versioned presets, streaming preview, request logs, key handling, quota display |
| **Design a prompt-management tool** — registry, playground UI, Git-style versioning | Versioning model, diffing, promotion between environments, eval hooks |
| **Design a sandboxed cloud IDE** / Codex-style workspace | Isolation, file sync, long-running jobs, streaming logs |

**Family 3 — the classic at OpenAI scale.** These are the "can you do normal distributed systems"
checks, asked with aggressive scale follow-ups.

| Prompt | Where the depth lands |
|---|---|
| **Design Slack**, with 100× and 1000× follow-ups | Fanout, presence, ordering, connection count. `Designs → Discord` is this page |
| **Design a job scheduler** / GPU job scheduler for text-to-video | Queues, priority, preemption, fairness under sustained overload |
| **Design a distributed webhook delivery system** | Retries, idempotency, ordering, poison messages |
| **Design a payment system with exactly-once charging** | Idempotency keys, sagas, reconciliation |
| **Design a token-usage / quota monitoring system** across millions of users | Metering accuracy vs cost, aggregation windows, late events |

**Bet allocation.** Family 1 is where to spend two-thirds of design prep, because it is the most
reported *and* the most transferable — a Playground answer is a ChatGPT answer with different
controls, and a Codex answer is a ChatGPT answer with an async job in the middle. Family 3 is
already covered by `Designs → Discord`, `Designs → Ticketmaster`, and `System Design`; one reread
each is enough.

### D. THE FUNDAMENTALS SUB-BANK

Reports consistently say the frontend screen "almost always focuses on JavaScript, sometimes React,
sometimes a bit of HTML/CSS." That is a warm-up, not the round — but a fumbled warm-up costs
minutes you need later. Have these cold, from `JavaScript` and `Coding Patterns`:

- `debounce` and `throttle`, with `leading`/`trailing` and cancel.
- Promise combinators from scratch: `all`, `allSettled`, `race`, `any`.
- A concurrency-limited task runner (`runConcurrently(tasks, n)`).
- An `EventEmitter` with `on`/`off`/`once`/`emit`.
- `deepEqual`, `deepClone`, `curry`, `memoize` with a custom key.
- An async iterator, and converting a callback stream into one.
- `AbortController` semantics: what `signal.aborted` means, what rejects, and why `fetch` rejects
  with an `AbortError` that you must not surface as an error.
- Event loop order: microtasks vs macrotasks vs `requestAnimationFrame`.

### E. WHAT THEY APPEAR NOT TO ASK

Useful because it tells you where *not* to spend September.

- **Hard algorithms.** interviewing.io's OpenAI page says plainly you will not get string-
  manipulation puzzles; every source describes the coding round as practical and work-shaped.
- **CSS trivia and layout puzzles.** Mentioned only as "sometimes a bit of HTML or CSS." Do not
  drill flexbox minutiae.
- **Framework internals quizzes.** No reports of "explain the React reconciler." Reports of
  "explain why this component renders twice" — a debugging skill, not a trivia one.
- **Library knowledge.** CoderPad, from scratch. No component library, no data-fetching library.
  If you want to *mention* TanStack Query or the AI SDK as what you'd reach for in production,
  do it as a one-line trade-off, then build it by hand. Have the names ready so the trade-off
  sounds lived-in rather than gestured at: the **Vercel AI SDK**'s `useChat` gives you the
  transcript, the token stream and the abort wiring in one hook, `useCompletion` is its
  single-turn sibling, and **AI Elements** ships the chat primitives on top. The sentence is
  *"in production I'd reach for `useChat` — it's this state machine with the transport already
  solved; here I'll build it by hand so you can see the model."* Then move on: naming it costs
  five seconds and buys you the "has shipped this" read.
  ([patterns.dev's AI UI patterns](https://www.patterns.dev/react/ai-ui-patterns/) is the
  tour of that stack; everything it covers is already in `§08`–`§09` below, minus the SDK.)

### F. COVERAGE MAP — WHAT YOU ALREADY HAVE, AND WHAT IS NEW

> **Read this table before writing a single new drill.** Roughly two-thirds of the bank is already
> built, in this repo or in `uie-practice`. The efficient path through the next four weeks is
> *reread and re-time* the covered rows, and *build* only the four uncovered ones.

| Bank item | Already covered? | Where |
|---|---|---|
| Streaming chat, core | ✅ **Fully** | `uie-practice/openai-01-streaming-chat` ← **the drill** · `UIE Components §14` · `uie-practice/streaming-message-reference` · `uie-practice/cursor-01-streaming-message` · `uie-practice/streaming-practice-8-17` |
| Stop / abort / generation counter | ✅ **Fully** | `UIE Components §14 D` and `§17 F` |
| Multi-turn transcript | ⚠️ **Partly** | `§14` is single-message. The transcript model is new — `§08 G` here |
| Autocomplete with cancellation | ✅ **Fully** | `UIE Components §06 Combobox` · `uie-practice/combobox-reference`, `combobox-interview`, `cursor-02-typeahead` |
| Virtualized transcript | ✅ **Fully** | `UIE Components §13` |
| Accessible stream announcements | ✅ **Fully** | `UIE Components §14 C` — the counter-intuitive one. Reread it |
| Live regions generally | ✅ **Fully** | `UIE Components §17 E` |
| Debounce/throttle in React | ✅ **Fully** | `UIE Components §17 K` |
| Key handler placement | ✅ **Fully** | `UIE Components §17 M` |
| Undo/redo, inverse ops, batching, coalescing | ✅ **Fully** | `Figma Screen §06` · `uie-practice/figma-02-undo-redo-batch`, `figma-07-coalescing-history`, `cursor-07-undo-redo` |
| Document model, command/inverse | ✅ **Fully** | `Figma Screen §04` · `uie-practice/figma-01-document-undo` |
| Styled text ranges | ✅ **Fully** | `Figma Screen §05 C` · `uie-practice/figma-04-styled-text-ranges` |
| Command palette | ✅ **Fully** | `UIE Components §12` · three `uie-practice` exercises |
| Test quality under clock | ✅ **Fully** | `Cursor Screen §08` · `uie-practice/cursor-05-write-the-tests`, `cursor-10-write-the-tests-ii` |
| Client design: transport, backpressure, resumability | ✅ **Fully** | `Cursor Screen §04 C–D` |
| Agent chat / streaming multi-file edits design | ✅ **Fully** | `Cursor Screen §05 B` |
| Run lifecycle, resumable SSE, TTFT, prefill/decode, prompt cache, cost | ✅ **Fully** | `Designs → ChatGPT §7–§11` |
| GPU serving, cancellation to the GPU | ✅ **Fully** | `Designs → Cursor Tab §9–§10` |
| Fanout / connection scale (the Slack prompt) | ✅ **Fully** | `Designs → Discord` |
| Refactor nested code, keep tests green | ⚠️ **Partly** | No dedicated drill. `Cursor Screen §08` covers reading tests. Low priority |
| Iterator → 2D → async | ⚠️ **Partly** | `JavaScript` covers iterators; no async-iterator drill. `§12 B` drill 7 |
| **The composer: caret, selection, Enter/Shift+Enter, IME, auto-resize** | ✅ **Built** | `§09 B` here · `uie-practice/openai-02-composer` |
| **`@`-mention / `/`-command autocomplete anchored to the caret** | ❌ **New** | `§09 C` here. **Build it — drill 4** |
| **Edit-and-resubmit a transcript message** | ❌ **New** | `§09 D` here. **Build it — drill 5** |
| **Streaming markdown, incremental** | ❌ **New** | `§08 I` here. **Build it — drill 6** |
| **Scroll pinning against a live stream** | ❌ **New** | `§08 H` here. Ships with drill 6 |
| **Streaming into an editable document (Canvas)** | ❌ **New** | `§08 J`, `§09 F`, `§06 C` here. Design-only unless time allows |
| Conversational AI service, end to end | ❌ **New** | `§06 A` here |
| Resumable streams, server side | ❌ **New** | `§05 E` here |

**The honest summary:** four new coding drills, one new design, and a lot of rereading. That is the
whole delta, and it fits in the four weeks with the other three screens still in them.

## 04 — Round 1 (Wed 9/16): the architecture hour

### A. THE CLOCK

| Minute | What is happening | If you are behind |
|---|---|---|
| 0–3 | Intros, the prompt, your restatement | — |
| 3–10 | **Requirements.** Functional, then non-functional, then the two numbers that matter | Cut to three functional requirements and move |
| 10–15 | **The wireframe and the core entities.** What is on the screen; what objects exist | Draw the screen, skip the entity list, name entities as you go |
| 15–22 | **API contract.** Endpoints, and the streaming one in detail | Do the streaming endpoint only |
| 22–35 | **High-level design.** Boxes and arrows for the two main flows | Draw one flow completely rather than two partially |
| 35–50 | **Deep dives.** Two or three, at least one client-side and one server-side | Let the interviewer pick; ask "where would you like me to go deep?" |
| 50–57 | **Scale.** 10×, 100×, 1000×. What breaks first, at each step | This is graded. Reserve the time even if a dive is unfinished |
| 57–60 | Wrap, your questions | — |

**The single most common failure is spending twenty-five minutes on requirements and wireframes.**
Set a hard internal gate: **by minute 15 there is a box diagram on the board.** If there isn't, you
are behind regardless of how good the requirements were.

### B. THE OPENING, CLOSE TO WORD FOR WORD

> "Let me restate it so we're aligned: we're building **X**. Before I draw, I want to pin down
> scope, then two or three numbers, because they'll decide the architecture.
>
> **Functionally**, I think the core is: [three things]. I'm going to treat [Y] as out of scope
> unless you want it — flag me if that's wrong.
>
> **Non-functionally**, the ones that will actually shape this are: **latency to first token**,
> because that's what users perceive in a generative product; **availability** during a generation,
> because dropping a half-finished answer is worse than never starting; and **cost per request**,
> because the expensive resource here is GPU seconds, not CPU or storage.
>
> **On numbers**: if we say [N] daily actives, [M] messages each, responses averaging [K] tokens —
> that's [derive one number out loud]. I'll keep these in the margin so we can point back at them.
>
> I'll go deepest on the client, because that's where I've spent the most time, but I want to get
> all the way to storage and the inference layer so the picture is complete. Does that order work?"

Four things that paragraph does. It **states scope and invites correction** (collaboration is a
named axis). It **puts TTFT first**, which is the correct non-functional requirement for a
generative product and marks you as having thought about this class of system. It **derives a
number** rather than listing assumptions. And it **declares the fullstack arc up front**, which
pre-empts the round's main failure mode — see `§04 C`.

### C. THE FULLSTACK MOVE, AND HOW TO MAKE IT WITHOUT OVERREACHING

You are strongest on the client. The round expects you to also reach the backend. The trap on both
sides is real: stop at the client and you look narrow; bluff the GPU layer and you look worse.

**The calibrated move is to be explicit about depth as you cross the boundary.**

> "I'll go deep on the client because that's my strongest surface. On the inference layer I know
> the shape — a queue, continuous batching, KV-cache reuse, and that TTFT and inter-token latency
> are separate problems with separate fixes — and I'll tell you where my knowledge gets thin rather
> than guessing. Push me wherever you want."

Then actually deliver depth on the server side you *do* own, which for this system is substantial:

| Server-side area | You genuinely own this |
|---|---|
| Transport: SSE vs WebSocket vs chunked, and proxy/buffering behaviour | ✅ Yes — `§05 B` |
| Conversation storage, message schema, pagination | ✅ Yes |
| Resumable generation, `Last-Event-ID`, a durable token log | ✅ Yes — `§05 E` |
| Idempotency on submit, exactly-once message creation | ✅ Yes |
| Rate limiting and quota by tier | ✅ Yes |
| Context-window truncation and summarisation policy | ✅ Yes — `LLM assistant §9` |
| Queueing and admission control under overload | ✅ Yes |
| Prompt-cache ordering for TTFT | ✅ Yes — `LLM assistant §9` |
| Continuous batching, KV cache, tensor parallelism internals | ⚠️ Shape only — say so |
| GPU cluster scheduling and placement | ⚠️ Shape only — say so |

That is nine rows of genuine depth and two honest edges. That reads as fullstack. Bluffing row ten
reads as neither.

### D. THE SCALE LADDER, WHICH IS THE ROUND'S SIGNATURE

Every OpenAI design write-up says the same thing: the interviewer will push scale, repeatedly, and
grade whether you **pinpoint the specific bottleneck at each threshold** rather than saying "add
more servers."

Have the ladder ready for the conversational product:

| Step | What breaks *first* | The fix, and its cost |
|---|---|---|
| **1×** — thousands of users | Nothing. One app server, one Postgres, direct call to the model API | — |
| **10×** | Long-lived connections pin app-server memory; a deploy kills every in-flight generation | Split the streaming tier from the API tier so you can deploy the API without dropping streams |
| **100×** | The model tier saturates. Queue depth grows and TTFT degrades before throughput does | Admission control + a per-tier queue. **Shed load at the door, not in the middle of a generation** |
| **100×** | Conversation reads hot-spot on recent messages | Cache the last N messages per conversation; page older ones from cold storage |
| **1000×** | Connection count exceeds what one region's LB tier can hold; cross-region latency shows up in TTFT | Regional streaming tiers, session affinity by conversation id, and a durable token log so a client can reconnect to a *different* region mid-generation |
| **1000×** | Cost, not capacity, becomes the binding constraint | Route by model tier, cache prefixes aggressively, cap max output tokens per tier. **Say that cost is a scaling limit** — at OpenAI it is the real one |

**The line that lands:** *"At 1000× the interesting failure isn't throughput, it's that a deploy or
a node loss now kills millions of in-flight generations. That's why I want the token log durable
and the stream resumable — it converts an availability problem into a reconnect."*

### E. THE FOUR PHRASES THAT CARRY THE ROUND

1. **"Latency to first token is the metric, not total completion time."** Says you understand
   generative UX. Follow with: *inter-token latency matters second, and it only has to beat reading
   speed — roughly 30–50 tokens/sec is indistinguishable from faster.*
2. **"I'll name the bottleneck before I name the fix."** Then do it, every time. This is the
   explicit grading criterion.
3. **"If I'm naming a technology I should own it — ask me why not the alternative."** Then survive
   the question. Never name Kafka, Redis Streams, or Postgres without a one-line reason and a
   one-line alternative.
4. **"That's the shape I know; here's where I'd need to look it up."** Once, deliberately, on the
   GPU internals. It buys credibility for everything you did assert.

### F. SELF-GRADE RUBRIC — RUN THIS AFTER EVERY DESIGN REP

Score each 0–2. Below 14/20 means run it again on the same prompt.

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | Restated scope and invited correction in the first three minutes | No | Partly | Yes |
| 2 | Non-functional requirements named TTFT first | No | Named latency vaguely | Yes, and distinguished TTFT from ITL |
| 3 | Derived a number, wrote it in the margin, referred back to it later | No | Wrote it | Referred back |
| 4 | A box diagram existed by minute 15 | No | ~20 | ≤15 |
| 5 | The streaming endpoint's contract was specified concretely (event shape, terminator, error frame) | No | Handwaved | Concretely |
| 6 | Reached storage schema | No | Named tables | Keys, indexes, access pattern |
| 7 | Reached the inference/queue layer | No | Mentioned | Admission control + batching named |
| 8 | Named a bottleneck before each fix | Rarely | Sometimes | Every time |
| 9 | Handled the 1000× step with a specific failure, not "shard it" | No | Generic | Specific |
| 10 | Owned every named technology under one follow-up | No | Mostly | Yes |

## 05 — The streaming spine

> One mechanism sits under nearly every OpenAI prompt in both rounds. Learn it once, end to end,
> and you can answer a design question and write the code from the same mental model.

### A. THE PATH, IN SEVEN HOPS

```
GPU decode loop  →  inference server (token callback)  →  gateway / API service
   →  [optional durable token log]  →  HTTP response body, chunked
      →  browser: fetch() → response.body (ReadableStream) → reader.read()
         →  TextDecoder({stream:true})  →  event framing  →  React state  →  DOM
```

**Where each round lives.** 9/16 is hops 1–5 with the client as one box. 9/17 is hops 5–8 with the
server as a mock. The vocabulary is identical, which is why doing them a day apart is an advantage.

### B. TRANSPORT: THE THREE-WAY CHOICE, AND THE ANSWER

| Transport | Fits | Against it |
|---|---|---|
| **Server-Sent Events** | One-directional server→client token push over plain HTTP. Auto-reconnect and `Last-Event-ID` are in the spec. Works with HTTP/2 multiplexing | Text only; no client→server channel; historically capped at 6 connections per origin on HTTP/1.1 |
| **Chunked `fetch` + `ReadableStream`** | The same thing without the `EventSource` API: you get headers, `POST` bodies, and `AbortController` | You hand-roll framing and reconnect |
| **WebSocket** | Genuinely bidirectional: live collaboration, voice, interrupting mid-generation with a new instruction | A stateful connection to operate, its own auth story, and no HTTP caching or proxy semantics |

**The answer to give, and the reason:** *"SSE, or plain chunked `fetch`. Token delivery is
one-directional — the only client→server messages are 'start' and 'stop', and both are fine as
ordinary requests. I don't need a persistent bidirectional socket to send two messages, and I'd
rather keep the HTTP semantics: auth, proxies, retries, and load balancing all work without
special-casing."*

**Then volunteer the nuance,** because it is the follow-up:

- **`EventSource` cannot POST.** A prompt is a request body. So in practice you use `fetch` with a
  `POST`, read `response.body` yourself, and parse SSE framing by hand — or you `POST` first to
  create a generation and then `EventSource` its id. Say which you are doing. This detail alone
  separates people who have built it from people who have read about it.
- **Buffering proxies are the classic production bug.** An intermediary that buffers the response
  destroys streaming while keeping everything technically correct. `Content-Type: text/event-stream`
  plus `X-Accel-Buffering: no` and disabled compression on the stream route.
- **Compression.** Gzip over a token stream can hold bytes waiting for a flush boundary. Either
  disable it on that route or ensure per-event flushing.
- **Head-of-line blocking.** Under HTTP/1.1 with six connections per origin, several open streams
  in several tabs starve everything else on the origin. Under HTTP/2 they multiplex.
- **When you'd flip to WebSocket:** voice mode, live multi-user collaboration on the same document,
  or a product where the user interrupts mid-generation with new content rather than merely
  stopping. Naming the flip condition is better than defending SSE absolutely.

This section is the decision and its production pathologies. If the interviewer goes one level
below it — what the `101` upgrade actually does, how `Last-Event-ID` resumption works on the
server, what a ping/pong heartbeat is detecting — that is `Technology Choices` §23–24.

### C. THE WIRE FORMAT, SPECIFIED

Interviewers on both days will accept "the server streams tokens." What earns is specifying it.

```
POST /v1/conversations/{id}/messages
Accept: text/event-stream
Idempotency-Key: <client-uuid>

→ 200 OK
   Content-Type: text/event-stream
   Cache-Control: no-cache
   X-Accel-Buffering: no

id: 1
event: delta
data: {"messageId":"m_42","text":"Hel"}

id: 2
event: delta
data: {"messageId":"m_42","text":"lo"}

event: done
data: {"messageId":"m_42","finishReason":"stop","usage":{"out":128}}
```

**Four decisions inside that block, each worth stating:**

1. **`Idempotency-Key` on submit.** The user's phone drops the response but the message was
   created. A retry must not create a second user message or a second generation. This is the
   cheapest correctness point in the whole design, and almost nobody says it.
2. **`id:` on each event** is what makes `Last-Event-ID` resumption possible later. It costs
   nothing now and enables `§05 E`.
3. **A terminal event, not just a closed socket.** A closed connection is ambiguous — completion
   and failure look identical. An explicit `done` (with `finishReason`) versus an `error` event
   makes the client's state machine total.
4. **Deltas carry text, not whole messages.** Sending the accumulated string each time is O(n²)
   bytes over the stream and is the naive thing people do.

### D. TTFT VERSUS INTER-TOKEN LATENCY

Two numbers, two entirely different fixes. Confusing them is the most common depth failure.

| | Time to first token | Inter-token latency |
|---|---|---|
| **What it is** | Request → first visible character | Steady-state gap between tokens |
| **Dominated by** | Queue wait + **prefill** over the whole prompt | **Decode**, one forward pass per token |
| **Scales with** | Prompt length; queue depth | Model size; batch size; memory bandwidth |
| **Fixes** | Prompt-cache the stable prefix, shorten context, admission control, route small requests to a fast tier | Smaller/quantized model, speculative decoding, better batching |
| **Target** | Under ~500 ms feels instant; over ~2 s feels broken | Beat reading speed. ~30–50 tok/s is enough |
| **Client-side fix** | Optimistic echo of the user's message + a visible "thinking" state the moment they submit | Batch renders; do not chase paint rate |

**The prompt-cache line, which is free depth:** *"System prompt first, then conversation history,
then the new turn — stable prefix first, so the cache hits. If you interleave anything volatile
early, like a timestamp, you invalidate the whole prefix and pay full prefill every turn."*
`Designs → ChatGPT §11` has the full version.

### E. RESUMABILITY: THE DEEP DIVE WORTH VOLUNTEERING

The scenario: a user submits, tokens start arriving, and then they refresh the tab, lose wifi in a
lift, or switch from laptop to phone. Naively, the generation is orphaned — it keeps burning GPU
and the user has lost it.

**Three postures, in increasing cost:**

| Posture | Mechanism | Cost | When |
|---|---|---|---|
| **Restart** | Re-issue the request | Full regeneration | Short, cheap responses |
| **Resume** | Server buffers emitted tokens keyed by generation id; client reconnects with `Last-Event-ID` and the server replays the gap, then continues live | A buffer with a TTL | Long or expensive generations. **The right default for a chat product** |
| **Persist-then-stream** | The generation writes tokens to durable storage as a first-class job; clients are readers of a log and the job completes whether or not anyone is watching | A durable write per chunk-batch | The answer must survive the client closing entirely — background agents, Codex tasks |

**The architecture for "resume", which is what to draw:**

```
POST /messages ──▶ API ──▶ enqueue generation(gen_id) ──▶ inference worker
                                                              │ tokens
                                            ┌─────────────────┘
                                            ▼
                                 Redis Stream  key=gen:{id}   (TTL ~1h)
                                            │
GET /generations/{id}/stream ◀── streaming tier reads from offset ──┘
   Last-Event-ID: 37     →  XRANGE from 37, replay, then tail live
```

**Say why the buffer is a stream and not a pub/sub topic:** *"Pub/sub is fire-and-forget — a
reconnecting client has missed everything sent while it was gone. I need a replayable log with
offsets so I can serve the gap. Redis Streams gives me that with a TTL; a partitioned log gives me
the same thing durably if the generation must outlive the buffer."*

**Three consequences worth naming unprompted:**

1. **The streaming tier becomes stateless and horizontally scalable** — it is a reader of the log,
   not the owner of the generation. That is what lets a client reconnect to a different instance,
   or a different region.
2. **Cancellation must reach the worker, not just the connection.** Closing the HTTP response does
   not stop the GPU. Stop is a *request* — `POST /generations/{id}/cancel` — that sets a flag the
   worker checks between tokens. Otherwise Stop saves the user's eyes and none of your money.
3. **Multi-device follow.** Once the token log exists, "open the same conversation on your phone
   mid-generation and watch it continue" is nearly free, and it is a great thing to volunteer.

### F. BACKPRESSURE, IN BOTH DIRECTIONS

**Server→client:** a slow client (a phone on 3G) cannot drain the stream as fast as the GPU fills
it. If you write unboundedly you buffer in the server process and eventually OOM. Options: bound
the per-connection buffer and drop the connection (the client resumes — see above), or let the
generation run ahead into the log and let the client read at its own pace. **The log posture makes
backpressure a non-problem**, which is another reason to volunteer it.

**Network→React:** the client-side half. Arrival rate is network-paced; paint is display-paced.
`setState` per chunk is a render per chunk. `Cursor Screen §04 D` has the full treatment with the
`requestAnimationFrame` buffer and its two footguns (background tabs don't fire rAF; flush the tail
on unmount). `§08 E` here is the same code in its OpenAI-shaped context.

## 06 — Four architectures, worked

Each is compressed to what fits in sixty minutes: the frame, requirements, the wireframe, the
contract, the flows, the two or three dives that earn, and the traps. `Designs → LLM knowledge
assistant` and `Designs → Cursor Tab` carry the long-form treatment of the retrieval and inference
layers; this section is the OpenAI product shape on top.

### A. DESIGN A CHATGPT-STYLE ASSISTANT

**The 60-second frame.** *"This is a product where the expensive resource is GPU seconds and the
perceived quality is dominated by time to first token. So the two things I want the architecture to
be good at are: getting the first token out fast, and never losing a generation that's already
being paid for. Everything else — storage, history, search — is a well-understood CRUD product
sitting behind that."*

**Functional requirements** (three, then stop):
1. Send a message in a conversation and receive a streamed response.
2. Resume a prior conversation with its context.
3. Stop a generation in progress.

Explicitly out of scope unless invited: file upload, tools/function calling, search, memory,
sharing, voice. **Name them as out of scope** — it shows you see the product, and it defends your
clock.

**Non-functional**, in order: TTFT p95 under ~1 s · a generation survives a client disconnect ·
one message creates exactly one generation · cost per conversation bounded.

**Numbers worth deriving.** With 200 M DAU (a public-ish figure worth using as an anchor), say 4
conversations each, 6 turns each → ~5 B generations/day → ~57 k generations/sec average, several
times that at peak. If a generation streams for 10 s, **concurrent open streams ≈ 57 k × 10 ≈
570 k, sustained.** Write that number in the margin. It is the number that makes the connection
tier a first-class component rather than an afterthought, and it is the one you point back at when
they say "1000×".

**Wireframe (draw this, small, top-left):** left rail of conversations · centre transcript of
alternating bubbles with the last one streaming · composer with a send/stop button · a model
picker.

**Core entities:** `User` · `Conversation` · `Message(role, content, createdAt)` ·
`Generation(id, messageId, status, model, tokensOut)`.

**API:**

| Endpoint | Notes |
|---|---|
| `POST /conversations` | Returns id |
| `GET /conversations?cursor=` | Keyset pagination, newest first |
| `GET /conversations/{id}/messages?before=` | Keyset on `(conversationId, createdAt, id)` |
| `POST /conversations/{id}/messages` | Body: text. Header: `Idempotency-Key`. Returns `{userMessageId, generationId}` **immediately** |
| `GET /generations/{id}/stream` | SSE. Honours `Last-Event-ID` |
| `POST /generations/{id}/cancel` | Sets the worker's stop flag |

**The split of submit from stream is the design decision to highlight.** One request that both
creates and streams is simpler, but it conflates two lifetimes: the message exists forever, the
stream is one client's view of it. Splitting them is what makes resume, multi-device, and
"generation outlives the tab" possible, and it costs one extra round trip you hide behind the
optimistic echo.

**Flow A — a turn.** Client optimistically appends the user's bubble and an empty assistant bubble
in `pending` → `POST /messages` → API writes the user message, dedupes on the idempotency key,
enqueues a generation, returns ids → client opens the stream → worker loads context, calls the
model, writes deltas into the token log → streaming tier tails the log to the client → on `done`,
the assistant message is persisted and the client swaps from live-buffer to canonical.

**Flow B — resume a conversation.** Keyset-paginate messages newest-first, render reversed. If the
newest generation is still `running`, open its stream with no `Last-Event-ID` and take the replay
from offset 0 — which is exactly the same code path as reconnect.

**Dive 1 — context management.** The prompt is bounded; conversations are not. The policy ladder:
keep the system prompt, keep the last K turns verbatim, summarise the middle into a rolling
summary, and optionally retrieve semantically from the rest. **Order the prompt stable-prefix-first
so the prompt cache hits.** The trade-off to state: summarisation costs an extra model call and
loses detail, so it should trigger on a token threshold, be cached on the conversation, and be
recomputed incrementally rather than from scratch each turn.

**Dive 2 — the connection tier at 570 k concurrent streams.** Separate it from the API tier so
deploys don't kill generations. Make it a stateless reader of the token log so any instance can
serve any generation. Route by `generation_id` so a reconnect is cheap. State the per-connection
memory budget out loud (tens of KB × 570 k is tens of GB — this is why the buffer must be bounded
and the log external).

**Dive 3 — cost and admission control.** Under overload, **shed at the door**: reject or queue new
generations with a clear "at capacity, retrying" state, and never kill an in-flight one. Free tier
queues, paid tier doesn't. Cap max output tokens per tier. Say the thing they want to hear: *"the
binding constraint here is GPU-seconds, so admission control is a product decision as much as an
engineering one."*

**Traps, ranked:**
1. Not splitting submit from stream, so resume is impossible without a redesign.
2. Treating a closed connection as success. Completion and failure must be distinguishable.
3. Cancelling the HTTP request and calling it Stop. The GPU keeps going.
4. Offset-based pagination on messages. Use keyset; a growing list makes offsets wrong and slow.
5. Forgetting the idempotency key, so a retried submit double-charges and double-generates.
6. Handwaving "we'll use WebSockets" without the reconnect story.

### B. DESIGN THE OPENAI PLAYGROUND

**Why it is a different problem from ChatGPT.** ChatGPT is a consumer product with one
configuration. The Playground's entire point is that **the configuration is the document.** Model,
temperature, top-p, max tokens, system prompt, tools, response format, seed — all of it is
user-editable state that must be shareable, versionable, and reproducible.

**The 60-second frame:** *"The interesting object here isn't the response, it's the request. This
is a config editor with a live preview attached, so I'll design the config as a first-class
versioned entity and treat streaming as a solved sub-problem I'll reuse from the chat design."*

**Functional:** edit a prompt and parameters · run it and stream the output · save as a named
preset · share a link that reproduces exactly what the author saw · view the equivalent API code.

**Core entities:** `Preset(id, ownerId, name)` · `PresetVersion(presetId, version, config, createdAt)`
· `Run(id, presetVersionId, output, usage, seed)`.

**The three decisions that make this answer:**

1. **Config is content-addressed and immutable per version.** A share link points at a
   `PresetVersion`, not a mutable preset — otherwise the recipient sees something the author never
   saw. Say: *"a share link must be a snapshot, or it's a bug report generator."*
2. **Client state is a single config object plus a derived request.** Every control writes one
   field. This makes "copy as code" a pure function of state, makes undo trivial, and makes
   URL-encoding the config for an unsaved share straightforward. **A parameter panel is a form, and
   `UIE Components §16` is the contract** — validation timing, error association, and disabled
   states all apply.
3. **Reproducibility is a stated non-goal at the token level.** Seed plus temperature plus model
   version gets you close; it is not a guarantee. Volunteering that you know sampling is
   non-deterministic and that model versions get deprecated is a credibility marker. Pin the model
   *version*, not the alias, in a saved preset.

**Client-side depth (spend your time here):** debounced autosave of the draft config to local
storage keyed by preset id · optimistic preset save with rollback · the run panel is the streaming
component from `§08` verbatim · **cancel on parameter change** — if the user moves temperature
mid-run, abort and mark the output stale rather than showing output that doesn't match the visible
config, which is the subtle UX bug in this product · a diff view between two versions.

**Server-side depth:** key management (never expose the raw key client-side; the browser calls your
backend, which holds the key) · per-key rate limits and quota display · run logs with token usage
for billing · abuse controls, since a Playground is an open proxy to a model if you let it be.

**Traps:** sharing a mutable preset · storing the API key in `localStorage` · re-rendering the
whole config tree per keystroke in the system-prompt textarea (this is where `§09 B` shows up —
the system prompt is a large textarea, and it needs to be uncontrolled-with-a-ref or debounced) ·
forgetting that a Playground is the most abusable surface OpenAI ships.

### C. DESIGN CANVAS — STREAMING EDITS INTO A DOCUMENT THE USER IS ALSO EDITING

**The hardest of the four, and the one that most directly matches the "text streaming + text
editor" report.** Worth one full rep on 9/11 even though it is less likely than A.

**The 60-second frame:** *"The distinguishing constraint is two writers on one buffer. The model is
producing edits while the user may be typing in the same document. That makes this a concurrent
editing problem, not a rendering problem — so the first thing I want to fix is the document model
and how an edit is represented, before I talk about any UI."*

**The core insight to lead with:** a streamed *replacement* of the document is unacceptable, because
it destroys the user's cursor, their selection, and their in-flight typing. So model edits must be
**ranged operations against a version**, not whole-document writes:

```ts
type Op =
  | { kind: 'insert'; at: number; text: string }
  | { kind: 'delete'; at: number; len: number }

interface EditRequest {
  baseVersion: number            // what the model saw
  ops: Op[]                      // streamed in, applied incrementally
  scope?: { start: number; end: number }  // "improve this paragraph"
}
```

**The four sub-problems, in the order to raise them:**

1. **Position transform.** The model produced ops against `baseVersion`. The user typed since. Each
   local edit must transform pending model ops (insert before a position shifts it right; delete
   before it shifts left; overlapping delete is the hard case). This is operational transform in
   miniature, and the honest framing is: *"for a single user plus a model, OT over insert/delete is
   tractable and I'd write it. For many concurrent humans I'd reach for a CRDT and I'd say why:
   convergence without a central transform authority."* `Figma Screen §04 C` is the command/inverse
   machinery this rests on.
2. **Granularity of application.** Applying every streamed character makes the document jitter and
   makes undo useless. Apply at a semantic boundary — per sentence, per op, or per debounce window
   — and **batch the whole model turn into one undo entry.** `Figma Screen §06 C` is the batching
   pattern verbatim.
3. **Conflict policy.** If the user edits inside the range the model is rewriting, someone loses.
   State a policy: *the human wins.* Abort the model's remaining ops on that range, keep what
   landed, and surface it ("stopped editing here because you started typing"). A policy stated is
   worth far more than a policy implemented.
4. **Presentation of pending model edits.** Show them as a decoration layer — a diff — that the
   user accepts or rejects, rather than mutating the buffer directly. This is the Cursor inline-diff
   pattern and it sidesteps most of problem 3. `Cursor Screen §05 B` covers it.

**The client architecture:** one document store (text + version + op log) · a renderer that never
owns state · a decoration layer for pending edits · undo/redo as inverse ops over the same log.
**The editor surface itself should be a `<textarea>` unless rich formatting is required** — see
`§09 G` for why that is a defensible, not a lazy, answer.

**Traps:** streaming into `innerHTML` · replacing `value` wholesale and losing the caret · one undo
entry per token · letting the model's ops apply to a stale version without transform · reaching for
a CRDT before establishing there are multiple human writers.

### D. DESIGN A CODEX-STYLE AGENT TASK RUN

**The 60-second frame:** *"Unlike chat, the unit here outlives the client. A task runs for minutes,
touches a sandbox, produces a diff, and the user should be able to close the laptop and come back.
So this is a durable-job system with a streaming view attached, and I'll design the job first."*

**The shape:** `POST /tasks` → job in a queue → a worker in an isolated sandbox (per-task container,
no network by default, repo mounted, resource-capped) → the worker emits structured events (tool
call, file read, patch, test run, log line) to a durable log → clients read the log.

**The five points that earn:**

1. **Persist-then-stream, not resume.** This is the case from `§05 E`'s third row: the job must
   complete whether or not anyone is watching. Say that explicitly — choosing the *more* expensive
   posture correctly is the signal.
2. **The event stream is structured, not text.** `{type: 'tool_call' | 'patch' | 'log' | 'status'}`.
   Which means the client must render **syntactically incomplete structured data on every frame** —
   a patch arriving hunk by hunk. Either buffer to the object boundary or use a streaming-tolerant
   parser. Naming this unprompted is a strong signal because it is the bug that ships.
3. **Sandbox isolation is the security answer.** Untrusted code execution: a fresh container per
   task, no ambient credentials, egress denied by default with an allowlist, CPU/mem/time caps,
   and the repo checked out from a token scoped to one repo.
4. **The output is a diff the human reviews**, not a push. Design the review surface: file tree,
   per-hunk accept/reject, and a comment. `UIE Components §10` is the tree; `Cursor Screen §05 B`
   is the diff.
5. **Fanout of long jobs.** Thousands of concurrent tasks, each minutes long, each holding a
   container. Queue depth, per-user concurrency caps, and preemption of free-tier tasks are the
   scale answers.

### E. IF YOU GET A PROMPT THAT ISN'T ONE OF THESE

The four above cover the reported Families 1 and 2. If you draw from Family 3 — Slack, a job
scheduler, webhook delivery, payments — you already have those pages. The mapping:

| Prompt | Read |
|---|---|
| Design Slack, with 100×/1000× follow-ups | `Designs → Discord` — it *is* this problem, one write becoming fifty thousand socket writes |
| Design a chat/messaging system with delivery guarantees | `Designs → WhatsApp` |
| A job scheduler / GPU scheduler under overload | `Designs → Cursor Tab §9`, plus `§04 D` here for the ladder |
| Anything with exactly-once / idempotency / contention | `Designs → Ticketmaster` |
| A read-heavy feed | `Designs → Twitter feed` |
| A chat product at consumer scale | `Designs → ChatGPT` |
| RAG, evals, retrieval quality | `System Design §11–§12`, plus `Designs → ChatGPT §15` |

**And the universal fallback**, which works on any prompt including one you have never seen:
requirements → two numbers → wireframe → entities → API → two flows → name the bottleneck →
scale ladder. `Designs → Interview mechanics` is that loop in full.

## 07 — Round 2 (Thu 9/17): the coding hour

### A. THE CLOCK

Assume a multi-part problem, because every report says the round is practical with heavy follow-up.
The clock below assumes the streaming-chat family; adapt the labels, keep the gates.

| Minute | Target | Gate |
|---|---|---|
| 0–4 | Clarify. Mock or real endpoint? Tests runnable? React or plain TS? Scope of "chat" | — |
| 4–8 | **Types and the state model first.** Status enum, message shape, the props | Types on screen by minute 8 |
| 8–22 | **The core**: submit → stream → render, with loading and error | **Something streams by minute 22** |
| 22–30 | **Stop, abort, and the generation guard.** Plus disabled-submit | Core is complete and demoed |
| 30–45 | **Extensions**, interviewer-led. Multi-turn, scroll, a11y, edit, mentions | Two extensions landed |
| 45–55 | **Tests.** Two written, three more named | Do not skip. This is a graded axis |
| 55–60 | What you'd do next, and the trade-offs you deferred | — |

**The one gate that matters is minute 22.** A working stream at 22 leaves 38 minutes of extension
room, and the extensions are where the differentiation happens. A working stream at 40 caps your
score no matter how elegant it was.

### B. THE FIRST FOUR MINUTES, CLOSE TO WORD FOR WORD

> "Before I type — four quick things.
>
> One: is there a real endpoint, or should I write a mock generator so we can see it working? I'd
> default to a mock, since the interesting part is the client.
>
> Two: can I run tests in this pad, or should I write them and talk through them?
>
> Three: scope — I'm hearing a single conversation, streamed responses, a stop button. Should I
> assume multi-turn from the start, or build one turn and extend?
>
> Four: I'm going to write the types and the status model first, before any JSX. It's about ninety
> seconds and it makes the rest of the hour faster. Sound good?
>
> One thing I'll flag up front: I'll be treating cancellation and stale responses as first-class
> rather than bolting them on, because that's where this class of UI actually breaks."

That last sentence is the highest-leverage line in the round. It sets the frame that you are
building a *correct* streaming UI rather than a demo, and it makes the abort/generation work later
look planned rather than reactive.

### C. BUILD ORDER, AND WHY THIS ORDER

1. **Types.** `StreamStatus`, `Message`, the component props. Ninety seconds.
2. **The mock stream.** Twelve lines (`§08 K`). Now you have something to develop against and the
   interviewer can see output.
3. **Render a static transcript** from a hardcoded array. The layout is now solved and never
   distracts again.
4. **Wire submit → stream → append.** The core.
5. **Status transitions and the disabled submit.** Turns a demo into a component.
6. **Abort + generation counter.** Stop.
7. **Extensions**, whichever the interviewer steers to.
8. **Tests.**

**Why types before JSX**: OpenAI grades solution design and code quality explicitly, and the
cheapest way to demonstrate both is a state model that makes impossible states unrepresentable,
visible on screen in the first eight minutes. It also means every later decision has a place to
live.

### D. NARRATION THAT SCORES

Three habits, each cheap:

- **Name the alternative you rejected, in one clause.** *"I'm taking a callback plus an
  `AbortSignal` rather than an async iterable — the iterable's prettier but the signal makes
  cancellation part of the contract instead of something you hope `for await` handles."*
- **Say the failure the code prevents, not the mechanism.** *"The generation counter is so that
  tokens already in flight when you hit Stop get dropped rather than trickling in after."*
- **Flag deliberate debt.** *"I'm inlining this for now; in real code it's a `useStreamingChat`
  hook so the transcript component stays presentational. Want me to extract it, or keep moving?"*
  This converts a shortcut from a gap into a judgment call.

### E. WHAT "PRODUCTION QUALITY" MEANS HERE, CONCRETELY

OpenAI's stated bar includes *high-quality code* and *test coverage* as separate axes from *does it
work*. Concretely, in a sixty-minute pad, that means:

| Axis | The cheap thing that satisfies it |
|---|---|
| Solution design | A status enum, a single reducer, no boolean soup |
| Code quality | Named handlers, no inline arrow soup in JSX, one component per concept, no `any` |
| Performance | One sentence on why arrival rate is decoupled from render rate, and the buffer that does it |
| Test coverage | Two written tests + three named. See `§10` |
| Communication | The alternative-you-rejected habit above |
| Collaboration | Ask twice: once at minute 4, once at minute 30 ("where do you want the remaining time?") |

### F. SELF-GRADE RUBRIC — RUN AFTER EVERY CODING REP

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | Clarified mock/tests/scope before typing | No | Partly | Yes |
| 2 | Types and status enum on screen by minute 8 | No | ~12 | ≤8 |
| 3 | Something streamed by minute 22 | No | ~30 | ≤22 |
| 4 | `TextDecoder` used with `{ stream: true }` | No | Used, no flag | Yes, and said why |
| 5 | Abort wired to unmount **and** to Stop | Neither | One | Both |
| 6 | Generation counter or request id drops stale tokens | No | Mentioned | Implemented |
| 7 | Abort distinguished from error in the UI | No | — | Yes |
| 8 | Render batching present, with the reason stated | No | Present | Present + reason |
| 9 | Two tests written | 0 | 1 | 2 |
| 10 | Named at least two trade-offs unprompted | 0 | 1 | 2+ |

## 08 — Text streaming, done properly

> This is the chapter that decides 9/17. `UIE Components §14` is its component-shaped sibling and
> should be reread alongside; this section is the same material organised around the *problem*
> rather than the component, plus the four extensions `§14` does not cover.

### A. THE FIVE FAILURE MODES, WHICH ARE WHAT IS ACTUALLY BEING TESTED

Every extension in this chapter exists to prevent one of these. Knowing the list means you can
volunteer the fix before the interviewer asks for it.

| # | Failure | Fix |
|---|---|---|
| 1 | A multi-byte character split across two chunks renders as `` | `TextDecoder` with `{ stream: true }` — `§08 C` |
| 2 | 500 chunks cause 500 React renders and the tab janks | Buffer + rAF or timer flush — `§08 E` |
| 3 | Stop is pressed; tokens keep arriving for another second | Abort **and** a generation counter — `§08 D` |
| 4 | Two submits race; the older response overwrites the newer | Request id compared on every delta — `§08 D` |
| 5 | The user scrolled up to read; the stream yanks them to the bottom | Intent flag + threshold — `§08 H` |

### B. THE STATE MODEL

**Never `isLoading`.** A boolean cannot express "the user stopped it" versus "it failed" versus
"it finished," and those three need three different UIs.

```ts
type StreamStatus = 'idle' | 'submitting' | 'streaming' | 'done' | 'stopped' | 'error'

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
}

interface ChatState {
  messages: Message[]
  status: StreamStatus
  error?: string
  /** Kept separately from the input so Retry re-sends what was sent, not what is typed now. */
  lastPrompt?: string
}
```

**Why `submitting` is separate from `streaming`:** between the request leaving and the first token
arriving there is a real interval — TTFT — during which the correct UI is a thinking indicator, not
an empty bubble. Distinguishing them is a one-line cost and it is the difference between a UI that
looks considered and one that looks broken on a slow first token.

**Why `stopped` is separate from `done`:** the transcript should be able to offer "continue" after
a stop and not after a natural finish.

**Why `lastPrompt` exists:** retry must re-send the value that was sent. If retry reads the input,
it sends whatever the user has since typed. This is a two-line fix and interviewers notice it.

**The reducer, which is the code-quality exhibit:**

```ts
type Action =
  | { type: 'submit'; prompt: string; userId: string; assistantId: string }
  | { type: 'firstToken' }
  | { type: 'delta'; text: string }
  | { type: 'done' }
  | { type: 'stop' }
  | { type: 'error'; message: string }

function reducer(s: ChatState, a: Action): ChatState {
  switch (a.type) {
    case 'submit':
      return {
        ...s,
        status: 'submitting',
        error: undefined,
        lastPrompt: a.prompt,
        messages: [
          ...s.messages,
          { id: a.userId, role: 'user', text: a.prompt },
          { id: a.assistantId, role: 'assistant', text: '' },
        ],
      }
    case 'firstToken':
      return s.status === 'submitting' ? { ...s, status: 'streaming' } : s
    case 'delta': {
      // Only the last message can be streaming — an invariant worth stating out loud.
      const messages = s.messages.slice()
      const last = messages[messages.length - 1]
      messages[messages.length - 1] = { ...last, text: last.text + a.text }
      return { ...s, messages }
    }
    case 'done':
      return { ...s, status: 'done' }
    case 'stop':
      return { ...s, status: 'stopped' }
    case 'error':
      return { ...s, status: 'error', error: a.message }
  }
}
```

**Say the invariant out loud:** *"only the last message can be streaming, and there is at most one
in-flight generation. Those two invariants are why this reducer stays small."*

### C. THE READER LOOP

```ts
async function readStream(
  res: Response,
  onText: (chunk: string) => void,
  signal: AbortSignal,
) {
  if (!res.body) throw new Error('no body')
  const reader = res.body.getReader()
  const decoder = new TextDecoder()          // <- the important object
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      onText(decoder.decode(value, { stream: true }))
    }
    onText(decoder.decode())                  // flush any trailing partial code point
  } finally {
    reader.releaseLock()
  }
}
```

**`{ stream: true }` is the tell.** Say why, unprompted:

> "`response.body` yields `Uint8Array`s at whatever boundary the network produced. A multi-byte
> character — an emoji, any CJK text — can land with its bytes split across two reads. Decoding
> each chunk independently turns that into a replacement character. `{ stream: true }` makes the
> decoder hold the partial sequence until the next chunk completes it, and the final bare
> `decode()` flushes the tail."

**Two more things to know about this loop:**

- **`reader.read()` does not reject on abort in every implementation** — depending on how the
  fetch was set up, the abort may surface as a rejected `fetch` promise, a rejected `read()`, or
  simply `done`. Wrap the whole thing and branch on `signal.aborted` rather than on the error type.
- **`reader.cancel()` versus aborting the request.** Cancelling the reader stops you consuming;
  aborting the request tells the network to stop. Do both — and remember from `§05 E` that neither
  one stops the server's GPU, which needs an explicit cancel call.

### D. CANCELLATION, AND THE GENERATION COUNTER

**Abort alone is not enough**, and this is the single most reliable place to earn a point.

```tsx
const abortRef = useRef<AbortController | null>(null)
const genRef = useRef(0)

async function send(prompt: string) {
  abortRef.current?.abort()               // supersede any in-flight generation
  const gen = ++genRef.current            // this request's identity
  const ctrl = new AbortController()
  abortRef.current = ctrl

  dispatch({ type: 'submit', prompt, userId: uid(), assistantId: uid() })
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
      signal: ctrl.signal,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    let first = true
    await readStream(res, (text) => {
      if (gen !== genRef.current) return        // a newer generation owns the UI now
      if (first) { first = false; dispatch({ type: 'firstToken' }) }
      push(text)                                 // buffered — see §08 E
    }, ctrl.signal)
    if (gen === genRef.current) dispatch({ type: 'done' })
  } catch (err) {
    if (gen !== genRef.current) return           // superseded: not our problem
    if (ctrl.signal.aborted) dispatch({ type: 'stop' })   // <- not an error
    else dispatch({ type: 'error', message: String(err) })
  }
}

function stop() {
  abortRef.current?.abort()
  genRef.current++            // late tokens are now dropped, not merely un-requested
}

useEffect(() => () => abortRef.current?.abort(), [])   // abort on unmount
```

**The three lines to narrate:**

1. `if (gen !== genRef.current) return` — *"tokens already decoded and queued in microtasks when
   the abort landed will still call this callback. Comparing the generation is what makes Stop feel
   instantaneous rather than trailing."*
2. `if (ctrl.signal.aborted) dispatch({type:'stop'})` — *"an abort produces the same rejected
   promise as a network failure. If I don't distinguish them I show 'something went wrong' to
   someone who pressed Stop."*
3. The unmount effect — *"navigate away mid-stream without this and the request keeps running while
   the callback calls `setState` on a dead component."*

**Also mention, one clause each:** the Stop/Send button swap should be keyed, or React reuses the
DOM node and a `type="button"` becomes `type="submit"` mid-click (`UIE Components §14 D` has the
full mechanism). And on the server, Stop is a *request*, not a disconnect (`§05 E`).

### E. BATCHING: ARRIVAL RATE VERSUS PAINT RATE

```tsx
const buf = useRef('')
const raf = useRef(0)

function push(text: string) {
  buf.current += text
  if (raf.current) return
  raf.current = requestAnimationFrame(() => {
    raf.current = 0
    const text = buf.current
    buf.current = ''
    dispatch({ type: 'delta', text })
  })
}
```

**Say what it saves, precisely**, because a good interviewer will push: it saves **renders**, not
paints — the browser already coalesces DOM mutation to one paint per vsync. The win is main-thread
time, and it matters when `render cost × arrival rate` is large: streamed markdown, a syntax-
highlighted diff, a long virtualized transcript. For appending to a bare text node it is close to
free, and **volunteering that distinction reads better than reaching for the buffer reflexively.**

**Two footguns, both worth naming:**
- `requestAnimationFrame` **does not fire in a background tab.** A user switching tabs mid-answer
  sees the stream freeze until they return. Pair it with a `visibilitychange` fallback, or use a
  ~50 ms `setTimeout` flush instead if background progress matters.
- **Flush the tail.** On `done`, on error, and on unmount, drain `buf.current` or the last partial
  batch is dropped. `cancelAnimationFrame` on unmount too.

**The alternative worth naming:** React 18's automatic batching already coalesces updates within a
single task, so multiple deltas arriving in one microtask checkpoint are one render for free. The
buffer is for deltas arriving across *separate* tasks, which is the normal case for network reads.

### F. THE SKELETON YOU TYPE FROM BLANK

Target: **six minutes, cold, no reference.** Drill it until it is muscle memory, because every
minute this takes is a minute stolen from the extensions where the score lives.

```tsx
type Status = 'idle' | 'submitting' | 'streaming' | 'done' | 'stopped' | 'error'
type Message = { id: string; role: 'user' | 'assistant'; text: string }

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<Status>('idle')
  const [input, setInput] = useState('')
  const abortRef = useRef<AbortController | null>(null)
  const genRef = useRef(0)
  const busy = status === 'submitting' || status === 'streaming'

  const append = (text: string) =>
    setMessages((m) => {
      const next = m.slice()
      next[next.length - 1] = { ...next[next.length - 1], text: next[next.length - 1].text + text }
      return next
    })

  async function send(prompt: string) {
    abortRef.current?.abort()
    const gen = ++genRef.current
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setMessages((m) => [
      ...m,
      { id: uid(), role: 'user', text: prompt },
      { id: uid(), role: 'assistant', text: '' },
    ])
    setStatus('submitting')
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ prompt }),
        signal: ctrl.signal,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const reader = res.body!.getReader()
      const dec = new TextDecoder()
      let first = true
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        if (gen !== genRef.current) return
        if (first) { first = false; setStatus('streaming') }
        append(dec.decode(value, { stream: true }))
      }
      if (gen === genRef.current) setStatus('done')
    } catch (err) {
      if (gen !== genRef.current) return
      setStatus(ctrl.signal.aborted ? 'stopped' : 'error')
    }
  }

  useEffect(() => () => abortRef.current?.abort(), [])

  return (
    <div>
      <ul>
        {messages.map((m) => (
          <li key={m.id} data-role={m.role} aria-busy={busy && m === messages[messages.length - 1]}>
            {m.text}
          </li>
        ))}
      </ul>
      <p role="status" aria-live="polite" className="sr-only">
        {status === 'streaming' ? 'Responding' : status === 'done' ? 'Response complete' : ''}
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (!input.trim() || busy) return
          send(input)
          setInput('')
        }}
      >
        <input value={input} onChange={(e) => setInput(e.target.value)} />
        {busy ? (
          <button key="stop" type="button" onClick={() => { abortRef.current?.abort(); genRef.current++ }}>
            Stop
          </button>
        ) : (
          <button key="send" type="submit">Send</button>
        )}
      </form>
    </div>
  )
}
```

**What that skeleton deliberately leaves out**, so you can offer them as next steps: the rAF buffer
(`§08 E`), SSE framing (`§08 D` below is raw text; add framing only if the problem says SSE), scroll
pinning, retry, and the extraction into a `useStreamingChat` hook. Naming what you left out and why
is worth more than silently having a longer file.

### G. MULTI-TURN: THE TRANSCRIPT MODEL

The extension that follows the core almost every time. Three decisions:

1. **The assistant message is created empty at submit time**, not on the first token. That gives
   the streaming text a stable identity, keeps React keys stable, and means the "thinking" state
   has somewhere to live.
2. **Client ids from `crypto.randomUUID()`**, reconciled with server ids on completion. Keep a
   `clientId → serverId` map so anything referencing the message (an edit, a retry) doesn't dangle.
   This is the optimistic-write pattern from `Cursor Screen §04 E`.
3. **At most one in-flight generation.** Enforce it in the state, not just by disabling the button
   — the button can be bypassed by Enter, by a race, or by a second tab.

**The keying trap:** using array index as a React key in the transcript breaks the moment you
support edit-and-truncate or optimistic reconciliation. Stable ids from creation.

### H. SCROLL PINNING

The extension everyone fumbles. The requirement: stick to the bottom as tokens arrive, **unless the
user scrolled up to read**, in which case leave them alone and offer a "jump to latest".

```tsx
const scroller = useRef<HTMLDivElement>(null)
const pinned = useRef(true)

function onScroll() {
  const el = scroller.current!
  // A threshold, not equality: fractional device pixels mean scrollTop rarely hits the exact bottom.
  pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40
}

useEffect(() => {
  if (pinned.current) scroller.current?.scrollTo({ top: scroller.current.scrollHeight })
})
```

**The four points to make:**

- **A threshold, not equality.** Zoom, fractional pixels, and sub-pixel layout mean
  `scrollTop + clientHeight === scrollHeight` is unreliable. ~40 px of slack.
- **Intent lives in a ref, not state.** Reading it during render or putting it in state causes a
  re-render per scroll event, which is exactly the jank you were avoiding.
- **Content can grow without a scroll event.** A code block finishing, an image loading, or a
  markdown reflow changes `scrollHeight` with no scroll fired. A `ResizeObserver` on the content
  element is the robust version.
- **`behavior: 'smooth'` fights a live stream.** Each new token retargets the animation and the
  scroll never settles. Use instant scrolling while streaming; smooth only for the explicit "jump
  to latest" button.

### I. STREAMING MARKDOWN, INCREMENTALLY

Real assistant output is markdown, and markdown arrives cut in half. The naive
`parse(fullTextSoFar)` on every delta is both slow and visually wrong.

**The three problems, in order of how much they matter:**

1. **Unclosed constructs flicker.** A fenced code block has no closing fence yet, so a standard
   parser emits it as a paragraph — then, on the closing fence, the whole thing snaps into a code
   block. Same for a lone `**` or a half-written link. **The fix is to close constructs
   speculatively**: if the text ends inside an open fence, append a virtual closing fence before
   parsing so it renders as code from the first line.

   **There are two answers here and the POV is picking one out loud.** Speculative closing is the
   workaround for handing an *off-the-shelf parser* (`marked`, `remark`) a document that isn't
   finished — it only accepts complete input, so you lie to it. The other answer is to own an
   **incremental tokenizer**, which knows it is inside a fence the moment the opening delimiter
   arrives and therefore never flickers at all — that is `cursor-11-streaming-markdown`, and it is
   a reported Cursor prompt in its own right. Say: *"I'd speculatively close, because I don't want
   to own a Markdown parser in a 60-minute round — but if we already had a streaming tokenizer the
   problem wouldn't exist, and at ChatGPT's volume that's the version I'd expect to ship."*
2. **Reparse cost.** Parsing the whole accumulated string per delta is O(n²) over the response. Two
   fixes, and it is worth naming both: **debounce the reparse to ~50–100 ms** (kills flicker and
   cost together, at an imperceptible latency price), and/or **parse block-by-block** — everything
   before the last blank line is stable and can be parsed once and memoised; only the trailing
   incomplete block is reparsed.
3. **Sanitisation is not optional.** Model output is untrusted input. Never
   `dangerouslySetInnerHTML` raw parser output; render to React elements, or sanitise. Say it in
   one clause — it is a cheap security point in an AI-product interview.

**Two smaller ones worth a sentence each:** partial links (`[text](htt`) should render as literal
text until closed, not as a broken anchor. And syntax highlighting a code block on every delta is
the most expensive thing on the page — highlight only when the block closes, or debounce it
separately at a longer interval than the text.

### J. THE SEAM: STREAMING INTO AN EDITABLE SURFACE

This is where `§08` and `§09` meet, and — per `§01 D` — the most likely place a problem gets hard.

**The rule: never write streamed text into the element the user has a caret in.** Setting `value`
on a focused `<textarea>` moves the caret to the end, drops the selection, and clears the native
undo stack. If the model must write into an editable surface, one of three postures:

| Posture | How | When |
|---|---|---|
| **Read-only until done** | Stream into a preview; enable editing on completion | Simplest. Always a valid answer, say so |
| **Ranged ops with caret preservation** | Apply an `insert`/`delete` at an index; save `selectionStart`/`End` before, transform them by the op, restore after | The model edits somewhere other than the caret |
| **Decoration layer** | The buffer is untouched; pending model text renders as an overlay the user accepts/rejects | Best UX, most work. The Cursor inline-diff pattern |

**The caret-preserving write, which is the code to have:**

```ts
function applyInsert(el: HTMLTextAreaElement, at: number, text: string) {
  const { selectionStart: s, selectionEnd: e } = el
  el.setRangeText(text, at, at, 'preserve')   // does not blow away native undo
  // Transform the user's selection by an insertion before it.
  const shift = (p: number) => (p >= at ? p + text.length : p)
  el.setSelectionRange(shift(s), shift(e))
}
```

`setRangeText` is the answer to "how do I insert without destroying the caret", and knowing it
exists — rather than reaching for `value = a + t + b` — is the whole point of `§09`.

### K. THE MOCK STREAM, AND TESTING

Twelve lines you should be able to type without thinking. It makes the round demonstrable and the
tests deterministic.

```ts
/** Deterministic fake: yields `text` in chunks, `delayMs` apart, cancellable. */
export function mockStream(text: string, chunk = 3, delayMs = 20) {
  return new ReadableStream<Uint8Array>({
    async start(controller) {
      const enc = new TextEncoder()
      for (let i = 0; i < text.length; i += chunk) {
        await new Promise((r) => setTimeout(r, delayMs))
        controller.enqueue(enc.encode(text.slice(i, i + chunk)))
      }
      controller.close()
    },
  })
}

export const mockFetch = (text: string) => async (_url: string, init?: RequestInit) =>
  new Response(mockStream(text), { status: 200 })
```

**Make one chunk boundary land mid-emoji on purpose.** `mockStream('héllo 👋 world', 3)` will split
the emoji's bytes across reads, which means your `TextDecoder` handling is *demonstrated* rather
than asserted. Doing this in front of the interviewer is a small piece of theatre that lands.

### L. THE EDGE CASES THEY WILL PROBE, RANKED

1. **Stop mid-stream.** Text so far is kept; status is `stopped`, not `error`; the button returns
   to Send; a second Stop is a no-op.
2. **Submit while streaming.** Either disabled, or it supersedes — pick one and enforce it in
   state. If it supersedes, the old generation's tokens must not land.
3. **Unmount mid-stream.** No warning, no leak.
4. **Empty or whitespace-only prompt.** Rejected before the request.
5. **A stream that ends with no tokens.** `done` with an empty assistant message — render an
   explicit empty state, not a blank bubble.
6. **HTTP error before the body.** `res.ok` checked; error surfaces with a retry that re-sends
   `lastPrompt`.
7. **Error *mid-*stream.** Partial text is kept and the error is shown *below* it. Discarding
   partial output on a mid-stream failure is the most common wrong answer.
8. **A multi-byte character split across chunks.** `§08 C`.
9. **Very long response.** Batching, and virtualization if the transcript is long.
10. **Duplicate submit from a double-click or Enter-held-down.** Guard on status, not on the button.

## 09 — Text-editor concepts, done properly

> The half of the Discord report that nobody prepares. It is also cheap insurance: three of the
> four sections below take one drill each, and they cover the composer, mentions, and
> edit-in-place — which between them account for most of the "make the text surface do something"
> extensions.

### A. THE FOUR SURFACES, AND WHAT EACH FORCES

| Surface | Probability on 9/17 | Forces you to know |
|---|---|---|
| **The composer** — auto-resize, Enter semantics, IME | **High.** "Editable text areas" is on every OpenAI frontend prep list | `selectionStart`, `scrollHeight`, `compositionstart`/`end`, key handling |
| **`@`/`/` autocomplete in the composer** | **Medium-high.** The natural "make it richer" extension | Trigger detection before the caret, `setRangeText`, anchored popup, combobox ARIA |
| **Edit a sent message and resubmit** | **Medium.** A ChatGPT feature, so a natural ask | Controlled/uncontrolled swap, pre-image restore, transcript truncation |
| **A document model with ops** (Canvas) | **Low-medium** as code; **medium** as a design question | Insert/delete ops, position transform, undo as inverse ops |

### B. THE COMPOSER

The whole component, with every decision that matters marked.

```tsx
export function Composer({ onSend, disabled }: { onSend: (t: string) => void; disabled: boolean }) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)
  const composing = useRef(false)          // (1) IME guard

  // (2) Auto-resize: measure, don't compute.
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'                       // collapse first, or it only ever grows
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [value])

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (composing.current) return                  // (1) never intercept during composition
    if (e.key === 'Enter' && !e.shiftKey) {        // (3) Enter sends, Shift+Enter newlines
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    const text = value.trim()
    if (!text || disabled) return                  // (4) guard on state, not on the button
    onSend(text)
    setValue('')
  }

  return (
    <textarea
      ref={ref}
      rows={1}
      value={value}
      disabled={disabled}
      aria-label="Message"
      onChange={(e) => setValue(e.target.value)}
      onKeyDown={onKeyDown}
      onCompositionStart={() => { composing.current = true }}
      onCompositionEnd={() => { composing.current = false }}
    />
  )
}
```

**(1) IME composition is the point that separates people who have shipped this.** On Japanese,
Korean, or Chinese input — and on some Android keyboards' predictive text — pressing Enter
*commits the candidate*, it does not mean "send". Intercepting it sends a half-typed word and looks
broken to a large fraction of users. Two mechanisms, know both:

- `compositionstart` / `compositionend` events with a ref flag, as above.
- `e.nativeEvent.isComposing` on the keydown, which is the modern one-liner. Chrome and Safari also
  dispatch `keyCode 229` during composition, which is the legacy check you may see in old code.

Say it out loud even if you only write one of them: *"Enter during IME composition means commit the
candidate, not send. I'm guarding on composition state so we don't send half a word."* This is a
high-signal sentence in a round at a company with global users.

**(2) Auto-resize by measurement.** Set `height: auto` first, then read `scrollHeight`. Skipping the
collapse means the box grows and never shrinks, because `scrollHeight` of an already-tall element
includes the height you gave it. `useLayoutEffect`, not `useEffect`, so the resize happens before
paint and the user never sees a one-frame jump. Cap the height and let it scroll past the cap.
`box-sizing` matters here; state which you assume.

**(3) Enter versus Shift+Enter is a product decision — say so.** Enter-to-send is right for chat,
wrong for a document. Also handle Cmd/Ctrl+Enter, which many users expect as "send" in the
newline-default mode. Mention `e.isComposing`, `e.repeat` (a held Enter should not send twice), and
that on mobile the on-screen keyboard's Enter is usually a newline regardless.

**(4) Guard on state, not on the button.** `disabled` on the button does not stop an Enter keydown,
a form submit, or a second tab. The check belongs in `submit()`.

**Extensions to volunteer if there's time:** draft persistence to `localStorage` keyed by
conversation (debounced), a character/token counter with a soft limit, paste handling that strips
formatting, and drag-drop file attach. Each is one sentence; naming them shows product sense.

**Performance footnote worth one clause:** for a *large* textarea — a system prompt in a Playground
— a fully controlled component re-renders an ancestor tree per keystroke. The escape hatches are an
uncontrolled input with a ref plus a debounced commit, or moving the input into its own leaf
component. `UIE Components §17 K` has the debounce mechanics.

### C. `@`-MENTION AND `/`-COMMAND AUTOCOMPLETE

**The realisation to lead with:** *"this is a combobox whose anchor is the caret rather than the
input, and whose value is a range rather than the whole field."* That sentence reframes an
intimidating problem into one you have already built — `UIE Components §06` is the component, and
its ARIA contract, keyboard contract, and active-descendant handling all transfer unchanged.

**The three parts that are genuinely new:**

**1. Trigger detection — a function of the text before the caret, nothing else.**

```ts
/** The active `@token` immediately before the caret, or null. */
function activeMention(value: string, caret: number) {
  const before = value.slice(0, caret)
  const m = /(^|\s)@([\w-]*)$/.exec(before)     // must follow start-of-input or whitespace
  if (!m) return null
  return { query: m[2], start: caret - m[2].length - 1, end: caret }
}
```

Three details to say aloud: the trigger must be **preceded by whitespace or start-of-input** or
every email address opens the menu; the token is bounded by the caret, so moving the caret away
closes the menu; and the returned `start`/`end` is a **range**, which is what makes insertion
non-destructive.

**2. Insertion rewrites the range, not the value.**

```ts
function insertMention(el: HTMLTextAreaElement, r: {start: number; end: number}, name: string) {
  el.setRangeText(`@${name} `, r.start, r.end, 'end')   // 'end' puts the caret after the insert
  el.dispatchEvent(new Event('input', { bubbles: true }))  // keep React's controlled value in sync
}
```

**`setRangeText` is the API to know.** Its fourth argument controls the resulting selection
(`'select' | 'start' | 'end' | 'preserve'`). Contrast it with `value = before + name + after`
out loud: the manual splice moves the caret to the end of the field, loses the selection, and — the
part people miss — **wipes the browser's native undo stack**, so Cmd+Z no longer works in the
composer. `setRangeText` preserves it. That single sentence is the best value-per-word in this
chapter.

**3. Positioning the popup at the caret.** In a `<textarea>` the caret has no exposed coordinates.
The standard technique, and knowing it exists is enough:

> "Textareas don't expose caret coordinates, so the trick is a mirror: an absolutely-positioned,
> visually-hidden `div` styled with the textarea's computed font, padding, border, and width, into
> which you copy the text up to the caret followed by a marker `<span>`. `getBoundingClientRect()`
> on that span gives you the caret's x/y. It's the `textarea-caret-position` technique. If I can
> get away with it in the interview I'd anchor the popup to the textarea's top or bottom edge
> instead, which is what most chat products actually do — and I'd say that's a deliberate
> simplification."

**Offering the simplification is the right answer under clock.** Naming the mirror technique
proves you know the hard version; anchoring to the element proves you know what's worth building.

**Keyboard contract, inherited from combobox:** ↑/↓ move the active option (and must **not** move
the caret — `preventDefault`), Enter selects (and must not send the message — order your key
handler so the menu wins), Escape closes the menu (and must not clear the input), Tab either
selects or closes, blur closes. `aria-activedescendant` on the textarea, `role="listbox"` on the
popup, and the textarea keeps focus throughout. Full contract in `UIE Components §06 C`.

### D. EDIT AND RESUBMIT A TRANSCRIPT MESSAGE

Small, high-signal, and it is a real ChatGPT feature so it is a natural ask.

**The four decisions:**

1. **The edit surface is a separate mode with its own local state**, seeded from the message.
   Cancel restores the pre-image; it does not re-read the message, because the message may have
   been reconciled with a server id in the meantime.
2. **Focus and selection on entry.** Focus the textarea and place the caret at the end — not
   select-all, which makes the first keystroke destroy the message. `el.setSelectionRange(len, len)`
   in a `useLayoutEffect`. Restore focus to the message's Edit button on cancel. This is the
   focus-restore pattern from `UIE Components §17 B`.
3. **Resubmit truncates the transcript below the edited turn**, because everything after it was a
   response to the old text. Say this out loud — it is the product decision the question is
   actually about. The alternative (branching, which is what ChatGPT does) is worth one sentence:
   *"the richer model is a tree of turns with a sibling selector; I'd keep the linear truncation
   unless you want branching."*
4. **Abort any in-flight generation first**, and reuse the same generation counter. Editing turn 3
   while turn 5 is streaming must not leave turn 5's tokens landing in a transcript that no longer
   contains turn 5.

**The trap:** an uncontrolled textarea seeded with `defaultValue` will not update if the message
changes underneath it, and switching a React input between controlled and uncontrolled warns and
misbehaves. Pick one — controlled with local state is the safe answer here — and key the editor by
message id so entering edit mode on a different message remounts it cleanly.

### E. THE DOCUMENT MODEL

If the problem escalates past a textarea into "the model edits a document," you need ops. **You
already have this material** — `Figma Screen §04` is the command/inverse pattern and `§06` is
undo/redo — so this section is only the delta.

**The minimum model:**

```ts
type Op =
  | { kind: 'insert'; at: number; text: string }
  | { kind: 'delete'; at: number; text: string }   // carry the deleted text: that IS the inverse

const invert = (op: Op): Op =>
  op.kind === 'insert'
    ? { kind: 'delete', at: op.at, text: op.text }
    : { kind: 'insert', at: op.at, text: op.text }
```

**The one new idea beyond the Figma material is position transform** — how a cursor, a selection,
or a pending op survives an edit made elsewhere in the document:

```ts
/** Where does position p end up after op is applied? */
function transform(p: number, op: Op): number {
  if (op.kind === 'insert') return p < op.at ? p : p + op.text.length
  // delete: before the range unaffected; inside collapses to the start; after shifts left
  if (p <= op.at) return p
  return p >= op.at + op.text.length ? p - op.text.length : op.at
}
```

**The three sentences that make this answer complete:**

- *"A selection is two positions, so transform both endpoints — and if they collapse to the same
  index the selection becomes a caret, which is the correct behaviour when the user's selection is
  deleted out from under them."*
- *"Tie-breaking at an equal index is a policy, not a fact: an insert exactly at the caret can go
  before or after it. Pick one, be consistent, and say which."*
- *"This is operational transform with one transform authority. With multiple concurrent human
  writers I'd move to a CRDT, because the reason CRDTs exist is convergence without a central
  authority — not because they're better at two writers."*

**Undo granularity, which is the ask that follows:** batch a whole model turn into one entry
(`Figma Screen §06 C`), and coalesce consecutive single-character user typing within a time window
(`§06 D`). One undo per token is the wrong answer, and so is one undo per session.

### F. STREAMING INTO THE DOCUMENT

Covered at the seam in `§08 J`. The compressed version, because it is worth being able to say in
twenty seconds:

> "Two writers on one buffer. I never write the model's output into a focused editable element,
> because setting `value` moves the caret and wipes native undo. Three postures: read-only until
> done, which is the simple correct answer; ranged ops with caret transform, which is `setRangeText`
> plus the transform function; or a decoration layer where pending edits render as an overlay the
> user accepts — which is the best UX and sidesteps the conflict entirely. If the user types inside
> the range the model is rewriting, the human wins and I abort the rest."

### G. `CONTENTEDITABLE`: WHEN, AND WHY THE ANSWER IS USUALLY "NOT YET"

If asked to build a rich-text surface, the framing that earns is a **defensible refusal followed by
the real design**, not an immediate `contentEditable` div.

> "`contenteditable` is genuinely hard to control: every browser has its own idea of what Enter
> produces, what Backspace merges, what a paste inserts, and it will happily generate markup you
> never asked for. The production answer is a **model-first editor** — my own document model is the
> source of truth, `contenteditable` is only a rendering and event surface, and I intercept
> `beforeinput` to turn user intent into ops against my model rather than letting the browser mutate
> the DOM. That's what Lexical, ProseMirror, Slate, and Quill all do, and it's why they're each
> tens of thousands of lines. In sixty minutes I'd use a `<textarea>` and be explicit that I'm
> trading formatting for correctness — unless formatting is a hard requirement, in which case I'd
> use a library and explain what I'd evaluate them on."

**The five things to be able to name if pushed:**

1. **`beforeinput`** is the interception point — it is cancellable and it tells you the *intent*
   (`insertText`, `deleteContentBackward`, `insertFromPaste`) before the DOM changes. `input` is too
   late.
2. **The Selection API** — `window.getSelection()`, `Range`, and `anchorNode`/`focusOffset` — maps
   DOM positions to model positions. That mapping, in both directions, is the hardest part of any
   contenteditable editor.
3. **IME composition cannot be cancelled**, so `beforeinput` interception has to let composition
   through and reconcile afterwards. This is the reason "just intercept everything" doesn't work.
4. **Paste**: you must handle `text/html`, `text/plain`, and files, and sanitise — pasted HTML is
   untrusted input.
5. **Undo**: once you intercept input, the browser's native undo stack is meaningless and you own
   undo entirely. Which is exactly the machinery in `§09 E`.

### H. THE API CHEAT SHEET

Have these in your fingers. Most of the round's editor extensions are two of them plus a guard.

| API | Use |
|---|---|
| `el.selectionStart` / `selectionEnd` / `selectionDirection` | Where the caret/selection is, in character offsets |
| `el.setSelectionRange(s, e, dir?)` | Move it |
| `el.setRangeText(text, s, e, mode?)` | **Replace a range without destroying native undo.** `mode`: `'select' \| 'start' \| 'end' \| 'preserve'` |
| `document.execCommand('insertText', false, t)` | Deprecated, but still the only way to insert into `contenteditable` *and* keep native undo in some browsers. Name it as a known wart |
| `el.scrollHeight` after `height:'auto'` | Auto-resize measurement |
| `compositionstart` / `compositionupdate` / `compositionend` | IME lifecycle |
| `e.nativeEvent.isComposing` | The one-line IME guard on a key event |
| `beforeinput` + `e.inputType` | Intent before mutation, in `contenteditable` |
| `window.getSelection()` → `Range` | DOM-level selection, for `contenteditable` and for mirrors |
| `new ResizeObserver(...)` | Content grew without a scroll event — pairs with `§08 H` |

### I. TRAPS, RANKED

1. **`value = before + insert + after`.** Caret jumps to the end, selection lost, native undo
   destroyed. Use `setRangeText`.
2. **Enter intercepted during IME composition.** Sends half a word for a large fraction of users.
3. **Auto-resize without collapsing to `auto` first.** The box grows monotonically and never shrinks.
4. **Guarding submit on the button's `disabled` rather than on state.** Enter bypasses it.
5. **`useEffect` instead of `useLayoutEffect`** for resize or caret placement — a visible one-frame
   flash.
6. **Arrow keys in a mention menu moving the caret** because `preventDefault` was forgotten.
7. **Escape in the mention menu clearing the whole input** because the key handler didn't stop.
8. **Index-based React keys in the transcript**, which breaks on edit-and-truncate.
9. **Select-all on entering edit mode**, so the first keystroke destroys the message.
10. **Reaching for `contenteditable` or a CRDT before establishing that you need either.**

## 10 — Tests, which OpenAI grades as its own axis

OpenAI's stated bar names **test coverage** separately from correctness and code quality. In a
sixty-minute pad most candidates write zero tests. Writing two, and naming three more, is one of the
cheapest differentiators available.

### A. ASK FIRST, AT MINUTE FOUR

*"Can I run tests in this pad, or would you rather I write them as a spec and talk through them?"*
The answer changes your plan and the question itself signals that you intended to test.

If the pad can't run them, **write them anyway as a commented block near the end** and read them
aloud. An unrunnable test that states the right invariant scores; a runnable test that asserts
`expect(true).toBe(true)` does not.

### B. THE FIVE TESTS FOR A STREAMING CHAT

Written against the deterministic `mockStream` from `§08 K`, which is why that helper is worth the
twelve lines.

| # | Test | The invariant it protects |
|---|---|---|
| 1 | Submitting renders the user message immediately and an empty assistant message | Optimistic echo; the assistant bubble exists before the first token |
| 2 | Text accumulates across chunks and the final text equals the full response | The reader loop and the decoder |
| 3 | Stop mid-stream keeps the partial text and sets status to `stopped`, not `error` | The single most important behavioural distinction in the component |
| 4 | Tokens arriving after Stop do not change the rendered text | The generation counter — the test most candidates never write |
| 5 | A rejected fetch surfaces an error and leaves any partial text visible | Error mid-stream does not discard output |

**Write 3 and 4.** They are the two that encode the hard parts, and #4 in particular is the test
that proves you understood why abort alone is insufficient.

```tsx
it('drops tokens that arrive after stop', async () => {
  render(<Chat fetchImpl={mockFetch('hello world, this is a long answer')} />)
  await userEvent.type(screen.getByLabelText('Message'), 'hi{Enter}')
  await screen.findByText(/hello/)                       // streaming has started
  await userEvent.click(screen.getByRole('button', { name: 'Stop' }))
  const frozen = screen.getByTestId('assistant').textContent
  await act(() => new Promise((r) => setTimeout(r, 200)))  // let the rest of the mock run
  expect(screen.getByTestId('assistant').textContent).toBe(frozen)
})
```

### C. THE IDIOMS THAT SAVE TIME

- **Query by role and accessible name**, not by test id, everywhere you can. It tests the a11y
  contract for free and reads better to the interviewer: `getByRole('button', {name: 'Stop'})`.
- **`findBy*` for anything after an await**; `getBy*` only for what is synchronously present.
- **`userEvent`, not `fireEvent`.** `userEvent.type` produces the real key sequence, which is what
  catches an Enter handler that ignores `isComposing`.
- **Fake timers plus a real microtask flush** is the classic trap with streams: advancing timers
  does not drain promises. `await act(async () => { vi.advanceTimersByTime(100) })`.
  `Cursor Screen §08 D` has the full treatment — reread it, it costs ten minutes in the room if you
  get it wrong.
- **Assert on rendered text, not on state.** State assertions test your implementation; text
  assertions test the contract.

### D. WHAT NOT TO TEST

Say this if you have time, because restraint reads as seniority: not the mock, not React, not CSS,
not that `useState` works. Test the invariants that would break if someone refactored the component
badly — which is exactly the five above.

## 11 — OpenAI, enough to be credible

### A. PRODUCT SURFACES TO HAVE TOUCHED BEFORE 9/16

Not trivia — the design round is likely to be one of their own products, and having used it is the
difference between designing from a description and designing from experience. An hour, total.

| Surface | What to notice, as an engineer |
|---|---|
| **ChatGPT** | Where the "thinking" state appears vs the first token; what Stop does to partial text; what happens if you refresh mid-answer; how editing a message truncates or branches the thread |
| **Canvas** | How model edits appear in a document you're also editing; whether your cursor survives; what undo does after a model edit |
| **The Playground** (platform.openai.com/playground) | Model controls as state; what a share link captures; the "view code" panel; how streaming previews |
| **Codex / agent tasks** | A long-running task with a streaming log and a diff you review; what happens if you close the tab |
| **The Responses / Chat Completions API with `stream: true`** | Actually run one from a terminal and watch the SSE frames. Twenty minutes, and it makes `§05 C` concrete rather than memorised |
| **Atlas / ChatGPT Apps** | Skim only. Know they exist and roughly what they are |

**Do the API one.** Watching real `data:` frames arrive, with a `[DONE]` terminator, is worth more
than any amount of reading about SSE — and it lets you say "when I've used the streaming API…"
instead of "I believe the format is…".

### B. THE ENGINEERING STORY, IN THREE PARAGRAPHS

Have this ready because it makes your design answers sound situated.

**The constraint is compute.** OpenAI's products are shaped by GPUs being scarce and expensive.
That is why tiering, rate limits, model routing, and caching are product-visible rather than
internal details, and it is why "cost per request" belongs in your non-functional requirements
alongside latency. An engineer who treats compute as free is designing for a different company.

**The interface is a stream.** Almost everything they ship is a token stream rendered
incrementally: chat, completions, agent logs, voice. That is why streaming, cancellation, and
resumability keep appearing in the interview — they are not interview trivia, they are the daily
work. The corollary is that partial, incomplete, syntactically-invalid state is the normal case in
their UIs, not an edge case.

**The products are converging on agents that act.** Codex, ChatGPT agent, Atlas, and Apps all move
from "model answers" to "model does, and the human reviews." Which puts the interesting frontend
problems in review surfaces — diffs, accept/reject, provenance, undo — and the interesting backend
problems in durable long-running jobs, sandboxing, and permissions. If you want one sentence about
where you'd want to work, that is the honest and well-informed one.

### C. QUESTIONS TO ASK, ONE PER ROUND

Pick from these; ask one, not three.

**After the architecture round:**
- "How much of the streaming stack is shared across ChatGPT, the API, and the agent products —
  is there one token-delivery layer, or has each surface grown its own?"
- "Where does the boundary sit between the product teams and the inference platform team? Who owns
  the latency budget?"

**After the coding round:**
- "How much of the frontend work is greenfield product surfaces versus deepening the ones that
  exist? Which is the team you're hiring for?"
- "What's the review culture like on client code where correctness is subtle — streaming,
  cancellation, that class of thing? Is there tooling, or is it convention?"

**Either round, if it fits:**
- "What's something that's true about building this product that surprised you?"

### D. THE MISSION QUESTION, WHICH IS ASKED IN TECHNICAL ROUNDS TOO

Reports are consistent that OpenAI weights motivation and safety-awareness heavily, and that it
comes up outside the dedicated behavioural round. Have ninety seconds ready. The shape that works:

1. **Something specific you've built or used that changed your view of the technology.** Concrete,
   first-person, ideally with a detail only someone who did it would know.
2. **Why this company rather than another lab** — and the honest answer for a product engineer is
   usually distribution: OpenAI ships to hundreds of millions of people, so interface decisions here
   set the norms for how everyone experiences this technology.
3. **A real answer to "where could this go wrong"**, which does not mean reciting existential risk.
   The credible product-engineer version is about the surfaces you'd build: an agent that acts on a
   user's behalf needs the user to be able to *see what it did and undo it*, and confident-sounding
   wrong output is a UI problem as much as a model problem. Say what you'd build differently
   because of that.

Avoid: "AGI is the most important technology ever." Everyone says it, and it is not evidence of
anything.

## 12 — The drills

### A. THE PROTOCOL

**Timer visible. No AI. No reference material. Talk out loud, recorded.** The recording is not
optional — the communication axis is graded and it is the only axis you cannot self-assess without
hearing yourself.

After every rep: score against `§07 F` (coding) or `§04 F` (architecture), and write **one
sentence** about the single thing that cost the most time. Rereading those sentences on 9/15 is
worth more than another drill.

### B. THE SEVEN CODING DRILLS

Live in `uie-practice` as new exercises. The first two are the load-bearing ones, and both are
**built** — the folders, briefs and specs are on disk, red by default. Drills 3–7 are still
prospective; build each on its `§02` date rather than up front, so what you learn in the Discord,
Cursor and Figma screens can shape them.

| # | Drill | Folder | Timebox | Ships when |
|---|---|---|---|---|
| 1 | **Streaming chat, core** — mock stream, status enum, stop, abort, generation guard | ✅ `openai-01-streaming-chat` | 45 min | Stream visible ≤20 min; all five `§08 L` cases 1–5 handled |
| 2 | **The composer** — auto-resize, Enter/Shift+Enter, IME guard, state-guarded submit | ✅ `openai-02-composer` | 30 min | Typed cold in 12 min; IME guard present without prompting |
| 3 | **Multi-turn + supersede** — transcript model, one in-flight generation, stale suppression | `openai-03-transcript` | 45 min | Submitting during a stream never interleaves output |
| 4 | **`@`-mention autocomplete** — trigger detection, `setRangeText`, anchored popup, combobox keys | `openai-04-mention-autocomplete` | 60 min | Arrows don't move the caret; Enter selects without sending |
| 5 | **Edit and resubmit** — edit mode, focus/caret restore, truncate below, abort in-flight | `openai-05-edit-resubmit` | 45 min | Cancel restores the pre-image; no orphaned generation |
| 6 | **Streaming markdown + scroll pinning** — speculative fence closing, debounced reparse, pin threshold | `openai-06-streaming-markdown` | 60 min | No flicker on code fences; scrolling up is respected |
| 7 | **Iterator → 2D → async** — the reported OpenAI fundamentals prompt | `openai-07-iterators` | 30 min | `Symbol.asyncIterator`, laziness, early-exit cleanup |

**Reuse before you build.** Drills 1 and 3 start from
`uie-practice/streaming-message-reference`; drill 4 starts from `combobox-reference`. Only drills
2, 4, 5, and 6 contain genuinely new code.

**Drill 6, revised 8/23.** Its old reuse pointer was `UIE Components §13`, which has no exercise on
disk — ignore it. The better starting point is `cursor-11-streaming-markdown`, built for the Cursor
screen: an incremental **tokenizer**, chunk boundaries and all. That is a different layer from this
drill, which is the **renderer** — and it changes what drill 6 is actually for. Problem #1 in
`§08 I` (fences flickering) is *dissolved* by owning a tokenizer rather than solved by speculative
closing, so drill 6's genuinely new content is the other three: reparse cost and block memoisation,
sanitisation, and **scroll pinning**, which nothing in either repo covers. Budget the hour
accordingly — 20 minutes on markdown, 40 on pinning.

**What drill 1 takes, and what it deliberately does not.** It reuses the reference's `StreamStatus`
enum, its two-layer `controllerRef` + `generationRef` guard, and its counter-intuitive a11y call
(status in the live region, `aria-busy` on the text). It replaces the *transport*: the reference
hands you an `onToken` callback and `cursor-01` hands you an `AsyncIterable<string>`, so both sit
**above the byte layer** and neither can exercise `§08 A` failure #1. Drill 1 owns
`fetch → res.ok → res.body.getReader() → TextDecoder(…, { stream: true })`, and its mock endpoint
can split a UTF-8 character across two chunks on demand. That is the whole reason it is not a
fourth copy of the same widget.

### C. THE FOUR DESIGN REPS

Sixty minutes each, whiteboard, out loud, recorded, self-graded against `§04 F`.

| # | Prompt | Date | The dive to force yourself into |
|---|---|---|---|
| 1 | Design a ChatGPT-style assistant (`§06 A`) | Tue 9/1 | The 570 k concurrent streams number, derived live |
| 2 | Design the OpenAI Playground (`§06 B`) | Sun 9/6 | Immutable preset versions and why a share link must snapshot |
| 3 | Design Canvas (`§06 C`) | Fri 9/11 | Position transform, and when a CRDT is and isn't warranted |
| 4 | Design a Codex agent task run (`§06 D`) | Tue 9/15 | Persist-then-stream, and sandbox isolation |

### D. THE TWO FULL MOCKS

**Sat 9/12 — coding.** Pick a Tier-1 prompt from `§03 B` blind (write them on cards; draw one).
Sixty minutes, CoderPad or an equivalent bare editor, no AI, recorded. Then thirty minutes
self-grading against `§07 F`, watching the recording at 1.5×. The recording is where you find out
that you narrated nothing for eleven minutes.

**Sun 9/13 — architecture.** Same, from `§03 C`, on Excalidraw. Grade against `§04 F`. The specific
thing to check: **did a box diagram exist by minute 15, and did you reach storage and scale?**

## 13 — Day-of runbook

### A. WED 9/16 — THE ARCHITECTURE ROUND

**The night before (Tue 9/15).** Reread only three things: `§04` of this guide, `§05 B` and `§05 E`
(transport and resumability — the two most likely dives), and the `§06 A` skeleton. Draw the
ChatGPT diagram once from blank on paper. Then stop. Sleep beats one more rep.

**The hour before.** Open Excalidraw and make the four regions from `§01 E` in a scratch file, so
your hands know the tool. Write the scale ladder from `§04 D` on paper next to you — six rows, and
it is legitimate to glance at your own notes. Have water. Close everything else.

**The first five minutes.** Restate. Requirements. Two numbers in the margin. `§04 B` is the script;
say it close to word for word — a rehearsed opening buys you calm for the middle.

**The middle.** Watch the two gates: **box diagram by minute 15**, **scale by minute 50**. If a deep
dive is running long, say *"I could keep going here — do you want more depth, or should I move to
scale?"* Handing the interviewer the steering wheel is collaboration, which is graded, and it
protects your clock.

**The last ten minutes.** Scale ladder, then one question from `§11 C`.

### B. WED 9/16, EVENING — THE TWENTY-MINUTE BRIDGE

**Do this. It is the highest-value twenty minutes of the whole month.**

Write down, immediately: every question the interviewer asked, every place they pushed, and every
place you felt thin. Then read it once and ask: **does anything here predict tomorrow's coding
problem?** It often does — interviewers on the same loop have talked, and the architecture round's
subject matter is a real signal about what the team works on. If today was Canvas, review `§09`
tonight. If today was streaming chat, review `§08 G`–`§08 I`, because the core will be assumed and
the extensions are where the round will go.

Then reread `§08 F` and type the skeleton once, from blank. Twenty minutes total. Then stop.

### C. THU 9/17 — THE CODING ROUND

**The hour before.** Type the `§08 F` skeleton once more and the `§08 K` mock once. Do not read
anything new. Have an empty CoderPad or sandbox open so the tool is not novel.

**The first four minutes.** `§07 B`, close to word for word. Ask the four questions. Say the
cancellation sentence.

**The build.** Types → mock → static render → wire → status → abort. Watch minute 22.

**Reuse yesterday's vocabulary, deliberately.** *"Yesterday we talked about the token log and
resumability — the client side of that is exactly this generation counter, so let me wire it now
rather than bolt it on."* It is true, it is relevant, and it makes two rounds read as one engineer
with a coherent model rather than two disconnected performances.

**The last fifteen minutes.** Tests, even if the extension is unfinished. Then: *"If I had another
hour: extract the streaming logic into a `useStreamingChat` hook, add the rAF buffer, and handle
[the specific thing you skipped]."* Naming your own gaps precisely is the strongest possible close.

### D. THE FIVE THINGS THAT MOST CHANGE THE OUTCOME

1. **A working stream by minute 22 on the 17th.** Everything else is downstream of this.
2. **A box diagram by minute 15 on the 16th**, and reaching scale by minute 50.
3. **Saying "an abort is not an error" and implementing it.** One line of code, disproportionate
   signal.
4. **Two tests written.** Most candidates write zero, at a company that grades test coverage.
5. **Reaching storage and the inference layer** on the 16th, honestly, with one stated edge.

### E. AFTERWARDS

Write the questions down within the hour, both days, while they are exact. Whatever happens with
this loop, that record is the most valuable artifact either round produces — for the next one, and
for this guide's next version.
