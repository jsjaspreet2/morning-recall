# Cursor Screen — Fri 8/28, 10:00–12:00 PDT

> Two back-to-back hours: **Systems Design** then **Technical Coding**. Web search allowed,
> **no AI tools**. This guide is the twelve-day plan, the two round scripts, and the one chapter
> of material the other guides don't have.

Companion to `System Design` (which is the server half) and `UIE Components` (which is the
component half). Neither covers what this screen actually grades, which is the seam between them:
a client that carries as much complexity as the server, and a component whose *interface* and
*tests* are scored above its implementation.

## 01 — The two hours, and what is actually graded

### A. THE FORMAT

| | 10:00–11:00 | 11:00–12:00 |
|---|---|---|
| **Round** | Systems Design | Technical Coding |
| **With** | An engineer, collaborative | Pairing with an engineer |
| **Tool** | Excalidraw or equivalent, your choice | CoderPad, link dropped in chat |
| **Deliverable** | A design you talked through | A React component |
| **Named criteria** | requirements gathered diligently, follow-up questions, thought process shared, **clear technology decisions, POV, systems depth** | **code correctness · component API design · test quality** |
| **Explicitly de-emphasised** | — | **styling, component structure** |

Two phrases in the invitation are doing real work.

**"Both the client and server have real complexity."** This is not a backend system design round
with a UI mentioned politely at the end, and it is not a pure frontend round either. It is a
warning that if you spend fifty minutes on sharding and five on the client, you have answered half
the question. §04 exists because that is the half you have the least written material for.

**"POV."** Not "considers tradeoffs." A point of view is a decision plus the reason plus what you
would need to see to change your mind. *"I'd use SSE here — it's one-directional, it survives
proxies, and it reconnects for free with `Last-Event-ID`. I'd switch to a WebSocket the moment we
need the client to stream back, like cursor presence."* That is a POV. *"We could use SSE or
WebSockets, both have tradeoffs"* is the anti-signal, and it is the most common failure mode in
the round.

### B. THE GRADING LINE, READ LITERALLY

> *"We will evaluate code correctness, component API design (the props and interface your
> component exposes), and test quality more than styling or component structure."*

They defined "component API design" inline, which means it is the axis they expect candidates to
under-serve. Three consequences worth internalising:

1. **The prop signature is a deliverable, not a preamble.** Type it into the pad, as a comment or
   a `type`, before the body. Say it out loud. If you change it mid-build, say why you changed it —
   a revised API with a stated reason scores better than an API that was right by luck.
2. **Tests are a deliverable, not a bonus.** A component with four sharp tests and one missing
   feature beats a complete component with zero tests. Budget for it: see §06 C.
3. **Do not spend time on CSS.** They told you. Enough that state is visible, nothing more. If you
   catch yourself centring something, stop.

### C. WHAT IS KNOWN ABOUT THE BAR, BY CONFIDENCE

Most search results for "Cursor interview" are machine-generated and contradict each other —
several claim there is no system design round at all, which the invitation disproves. Only these
are load-bearing.

| Confidence | Claim | Source |
|---|---|---|
| **High** | No AI in the first technical screens. Cofounder/CEO Michael Truell: *"We actually still interview people without allowing them to use AI, other than autocomplete, for first technical screens."* Later rounds flip and expect AI fluency — that is the onsite, not this. | First-party quote, widely reported |
| **High** | CoderPad's React interview environment runs **Vite**, is **multi-file**, and has a **Run Main / Run Tests** toggle. Jest + Testing Library work but need Babel wiring the interviewer sets up in the template. | CoderPad docs |
| **High** | Stack is TypeScript / React. ~300 people, no PMs, engineers own the product surface end to end. | Company statements |
| **Medium** | *"The questions are very practical, not complicated, but you are given very little time to complete them, so practice typing fast, don't index on quality."* | Single candidate report |
| **Medium** | A reported phone screen: *implement a flexible rate limiter for various API endpoints using per-user rules and interfaces.* Note the shape — **the interface is the deliverable**. Same axis the invitation names second. | Single candidate report |
| **Low** | Every "leaked question list" blog. Ignore them. | SEO content farms |

**Reasoned inference, flagged as such:** the design prompt is probably a surface Cursor itself has
to build — inline completion, streaming agent edits, repo indexing, remote agents — because those
are exactly the systems where the client is not a thin view. §05 works four of them plus one
deliberately non-Cursor problem. The point is to rehearse the *method*, not to have four answers
memorised; if you get handed "design a collaborative spreadsheet," the fifth one is why you'll be
fine.

### D. THE NO-AI RULE, AND HOW TO TRAIN FOR IT

Every rep you have done so far has happened in an editor with a model attached. That is a
different motor skill. Two specific things degrade without you noticing:

- **Import lines and hook signatures.** You have not typed `import { useState, useEffect, useRef,
  useMemo } from 'react'` from blank in months. Autocomplete has been finishing
  `useEffect(() => {`, `}, [deps])` for you, including the closing bracket and the array.
- **Recovering from a typo you can't see.** When the pad shows a red squiggle and no quick fix,
  the loop is read the message → form a hypothesis → check. That loop is slow if unpractised.

The rule for the next twelve days: **every timed rep runs with AI off.** Not "I won't accept
suggestions" — off. Disable Copilot/Cursor Tab in the editor you practise in, or use the
timer-gated harness in `uie-practice`, which hides the reference until the clock expires.

Web search *is* allowed in the round. Practise using it the way you will there: MDN for a DOM API
signature, the React docs for a hook's exact argument order. Not Stack Overflow for a solution.

### E. CODERPAD: THE FIRST NINETY SECONDS

The pad is a multi-file Vite React sandbox with a live preview. What varies is whether a test
runner is wired up, and you need to know before you plan your time.

**Ask, in the first minute, verbatim:**

> *"Before I start — can this pad run tests, and if so what's the runner? I want to know whether
> to write tests I can execute or tests you'll read."*

That question is itself a signal: it says you intend to write tests. Then:

| Answer | What you do |
|---|---|
| Yes, Jest/RTL wired | Write tests that run. Run them. A green suite on screen is the strongest evidence available. |
| No runner | Write the suite anyway, in a `__tests__` comment block or a second file. Say *"I can't execute these here, but this is the suite I'd ship."* Written-but-unrun still scores on the named axis. |
| "Up to you" | Spend ninety seconds trying to wire it; if it fights you, fall back to written. Do not burn ten minutes on config. |

Other pad mechanics worth knowing cold, so you don't discover them live:

- The interviewer sees your cursor and every keystroke, and the pad records **paste events with
  playback**. Type your code. A large paste is visible and reads badly in a no-AI round, even when
  the content is entirely your own.
- Long silent stretches read as being stuck. Narrate.
- Preview auto-reloads on save. Get something rendering in the first five minutes so there is a
  feedback loop.
- Multi-file means you *can* split — but the invitation says structure is not graded, so split only
  when it genuinely helps you (e.g. a hook you want to test in isolation).
- Assume **JavaScript unless told otherwise**, and ask. If the pad is TS, use it; if it's JS, do
  not fight it — express the API in a JSDoc block or a comment. The API is graded, the type syntax
  is not.

### F. RESOURCES, RANKED — AND WHAT TO ASK THE RECRUITER

Twelve days is short enough that resource choice matters. In order:

1. **The drills in `uie-practice`, and §04–08 here.** Built for the named axes. Nothing else is.
2. **GreatFrontend**, which you own outright. Its Front End System Design Playbook and the RADIO
   framework are calibrated for exactly the 10:00 round; its component practice for the 11:00 one.
   §03 A's clock is RADIO with the phases timed and the client side expanded — use whichever
   spine you find easier to hold, but hold one.
3. **Your `Accessibility` and `Technology Choices` guides.** The first is load-bearing rather than
   optional here, because for an interactive component the ARIA contract *is* part of the
   interface being graded. The second directly serves "clear technology decisions, POV."
4. **Four posts from cursor.com/blog** — two evenings, and only these four. The blog is mostly
   product and company announcements; the engineering posts are the minority and they are the ones
   the design round rhymes with.

   | Post | Read it for | Maps to |
   |---|---|---|
   | `/blog/tab-rl` — Improving Tab with online RL | The single most usable idea on the blog: *when to suggest* is part of the learned policy, not a heuristic | §05 A |
   | `/blog/tab-update` — the Fusion Tab model | Real production numbers to anchor a latency budget against | §05 A, §04 J |
   | `/blog/instant-apply` — Editing at 1000 tokens/second | Their best pure systems post; the plan-with-the-big-model, apply-with-the-fast-one split | §05 B |
   | `/blog/how-cursor-router-works` | A documented production model cascade, with real cost deltas | §05 A, §12 C |

   Read `tab-rl` and `tab-update` together — they're one story. If you have a third evening,
   `/blog/cloud-agent-environment` and `/blog/builds` cover §05 D, though the first is more about
   their internal developer experience than isolation internals. **Skip** the model cards,
   acquisitions, the AIUC-1 certification, and Mixture-of-Kittens — the last is genuinely good work
   with zero leverage in a product-engineering loop.

5. **Cursor itself, daily, between now and the 28th.** Candidate reports are consistent that
   interviewers detect inauthentic product usage within minutes. You use Claude Code — make that an
   honest comparison rather than a gap. Keep a running list: **three things you'd fix, one feature
   you'd build.** Both are likely to be asked, and a specific answer is disproportionately strong.

   **Read `/blog/joining-spacex` before you write that answer.** Cursor was acquired by SpaceX on
   14 August 2026, completing a partnership that began in April; the stated rationale is access to
   the largest GPU fleet in the world, and therefore more capable models at lower cost per request.
   Two consequences for you. Your "why Cursor" needs a version that survives it — answering as
   though this is still an independent startup will land badly two weeks after the announcement.
   And cost-per-request, already their obsession, is now the acquisition thesis, which raises the
   value of every cost-and-latency argument in §04 J and §12 C.
6. **Hello Interview** for server-side depth only. Don't lead with its templates — a pure
   distributed-systems opening reads as pattern-matching against a prompt that explicitly asked for
   both halves.

**Questions worth emailing the recruiter now**, because the answers change how you prepare and
none of them are awkward to ask:

- Does the CoderPad pad come with a test runner already configured, and which one?
- JavaScript or TypeScript for the component round?
- Is the design round product-shaped ("design feature X") or infrastructure-shaped?
- What's the next stage if these two go well, and is there a behavioural round?
- Given the SpaceX acquisition closed on the 14th, is the loop for this role unchanged? A
  two-week-old acquisition moves interview processes often enough that asking is routine.

### G. THE FIVE-MINUTE VERSION

If you read nothing else on the morning of the 28th:

- **Round 1:** eight minutes of requirements before a single box. State a latency budget out loud.
  Split the whiteboard into *client* and *server* and make sure both halves are full.
- **Round 2:** prop signature first, out loud. Get something rendering in five minutes. Reserve
  the last twelve minutes for tests, non-negotiably. Name what you skipped.
- **Both:** decisions, not menus. Every choice gets a reason and a switching condition.

## 02 — The twelve-day schedule

Twelve days, ~2.5–3.5 h each. Every day is one design rep, one coding rep, and the recall deck.
The reps are what move the number; reading this guide is not a rep.

| Day | Design (≈75 min) | Coding (≈75 min) | Read |
|---|---|---|---|
| **Sun 8/16 · D-12** | **Baseline. Do not read first.** Tab completion, 45 min out loud into Excalidraw | Cold 50-min build, AI off: `cursor-02-typeahead` | Nothing. Grade both, then read §01 |
| Mon 8/17 · D-11 | Tab again, now with the framework — §05 A | `cursor-01-streaming-message` 45 min + 5 tests | §03, §04 A–E |
| Tue 8/18 · D-10 | Agent chat, streaming multi-file edits — §05 B | `cursor-06-command-palette` (unseen) 50 min | §04 F–J |
| Wed 8/19 · D-9 | Codebase index — §05 C | **Test day:** `cursor-05` then `cursor-10`, 30 min each | §08 |
| Thu 8/20 · D-8 | Background agents — §05 D | `cursor-07-undo-redo`, then finish `combobox-practice-8-13` cold | §07 |
| **Fri 8/21 · D-7** | **Full mock #1 — 10:00–12:00, real clock, both hours back to back, no breaks** | | §10 the night before |
| Sat 8/22 · D-6 | Re-rep whatever the mock scored lowest. Only that. | | Re-read the relevant section |
| Sun 8/23 · D-5 | Collaborative review comments — §05 E (non-Cursor on purpose) | `cursor-08-chip-multiselect` + `cursor-04-file-tree` | §06 |
| Mon 8/24 · D-4 | Three requirements-gathering openings, 10 min each, no design | **Speed:** three 25-min mini-builds, AI off | §01 G |
| **Tue 8/25 · D-3** | **Full mock #2 — different problems, same clock** | | — |
| Wed 8/26 · D-2 | Weak-spot surgery | `cursor-09-inline-diff-review` | Whatever mock #2 exposed |
| Thu 8/27 · D-1 | **Taper.** One light rep, nothing new. Set up Excalidraw, a clean browser profile, and your notes. | | §03, §06, §10 only |
| **Fri 8/28 · D-0** | Runbook — §10 | | |

**Rules for the twelve days.**

1. **Grade every rep the same day you do it**, against the rubric in the relevant section. An
   ungraded rep teaches you your existing habits.
2. **Design reps are spoken.** Out loud, to an empty room, into a diagram. Silent designing is a
   different skill and not the one being tested. Record yourself once — the gap between what you
   thought you said and what you said is the single most useful thing you'll learn this week.
3. **Never read the model answer before the timer.** §05's answers are inside collapsibles for
   exactly this reason.
4. **If a day slips, drop the coding rep, not the design rep.** You have twenty-eight components
   built and one client-architecture chapter read.

## 03 — Round 1: the sixty-minute shape

### A. THE CLOCK

Sixty minutes, collaborative, and the interviewer will interrupt. That is fine — the shape below
is a spine to return to, not a script to complete.

| Minutes | Phase | What "done" looks like |
|---|---|---|
| 0–8 | **Requirements** | Users, the one core flow, scale numbers, and *the constraint that makes this hard*, all written on the board |
| 8–12 | **Contract** | The API surface and data model, written before any boxes. Two or three endpoints/events, with shapes. |
| 12–24 | **Client architecture** | State ownership, transport, cache, optimistic path, rendering strategy |
| 24–36 | **Server architecture** | Services, storage, the hot path, the async path |
| 36–52 | **Deep dive** | The hard thing, chosen by you or them, taken to real depth |
| 52–58 | **Failure and scale** | What breaks first, what degrades gracefully, what you'd measure |
| 58–60 | **Close** | Biggest risk, what you'd build first, what you left out |

**The two most common ways to lose this round:** starting to draw at minute two, and never getting
to a deep dive because you narrated breadth for forty minutes. The 36-minute mark is the one to
watch. If you are not deep in something specific by then, cut and go deep.

### B. THE OPENING, WORD FOR WORD

Rehearse this until it's automatic, because minute zero is when nerves cost the most.

> *"Let me make sure I'm building the right thing before I draw anything. I've got four
> categories of question — users and the core flow, scale, the quality bar, and constraints.
> I'll spend about eight minutes here and then start on the contract."*

Then work the four categories. Aim for **six to eight questions**, not twenty.

**1. Users and the core flow.** *Who uses this and what is the single most common action?* Then
restate it: *"So the flow I'm optimising is: developer types a character → we decide whether to
suggest → suggestion appears inline → they accept or keep typing. Everything else is secondary.
Is that right?"* Getting this restated and confirmed is worth more than any other minute in the
hour.

**2. Scale, as numbers you say out loud.** Never *"how many users?"* — offer a number and let them
correct it. *"I'll assume a million daily actives, each with an editor open for four hours, and a
keystroke rate that peaks around five per second. That's the number that sizes everything else —
does it sound right?"* Offering a number is a POV; asking for one is not.

**3. The quality bar.** This is where latency budgets live and where most candidates say nothing.
*"What does 'fast enough' mean here? For an inline suggestion I'd say the ghost text has to land
under 100 ms at p50 or people stop trusting it, and anything over 300 ms is worse than nothing
because it arrives after they've typed past it."*

**4. Constraints.** Offline? Multi-device? Enterprise/self-hosted? Privacy — does source code
leave the machine? Cost per request? *Cursor cares about cost per request*, and naming it unasked
is a strong signal.

Close the phase explicitly: *"I'll assume X, Y, Z and flag them as assumptions. Anything I've
missed that would change the architecture?"*

### C. REQUIREMENTS THAT CHANGE THE ARCHITECTURE

Most clarifying questions are decoration. These six change the drawing, which is why they are the
ones to ask:

| Question | If yes, the design gains |
|---|---|
| Does it work offline / on a flaky connection? | Local persistence, an outbox, conflict resolution |
| Can two clients touch the same object at once? | Presence, and either CRDT/OT or a locking model |
| Is any of this streamed rather than request/response? | SSE or WS, backpressure, resumability, partial-render UI |
| Is there a hard latency bar? | Speculative execution, caching, edge placement, smaller models |
| Does data leave the user's machine? | Local-first indexing, encryption, a self-hosted path |
| Does cost per request matter? | Batching, cascading model sizes, aggressive caching, debouncing |

Ask the two or three that plausibly apply. Naming one that *doesn't* apply and saying so —
*"there's no multi-user editing here so I'm not going near CRDTs"* — also scores, because it shows
you considered and rejected rather than never knew.

### D. HOW TO USE THE BOARD

Draw **two columns from the start**, labelled *Client* and *Server*, with the network boundary as
a vertical line between them. This single habit does more for this specific interview than any
other, because it makes an unbalanced answer visible to you in real time. If the left column has
three boxes and the right has eleven at minute thirty, you can see it and fix it.

Inside the client column, the boxes are not components. They are: **input/event layer · local
state and cache · sync engine · transport · render strategy**. See §04 B.

Other board rules:

- **Number your boxes in the order data flows**, then walk the numbers out loud. A diagram you
  narrate as a path beats a diagram you narrate as an inventory.
- **Write the decisions in a corner as you make them**, one line each: *"SSE, not WS — one
  direction, free reconnect."* At minute fifty-eight you read that list back and you have a
  summary you didn't have to compose under pressure.
- **Do not colour anything.** Do not align anything. You are on a clock and it is not graded.

### E. THE PHRASES THAT CARRY THE ROUND

- Deciding: *"I'm going to use X. The reason is Y. I'd switch to Z if W changed."*
- Deferring: *"I'm noting that and coming back — it matters, but the hot path matters more first."*
- Not knowing: *"I don't know the exact semantics there. What I'd do is check the docs and, if it
  doesn't work the way I expect, fall back to ___."* Never bluff — a wrong confident claim about a
  technology is the fastest way to lose "clear technology decisions."
- Being corrected: *"That's a better read than mine — that means I should change ___."* Then
  actually change the drawing. Collaboration is a named criterion.
- Closing: *"Biggest risk is ___. First thing I'd build is ___. The thing I'd want a week to
  prototype before committing is ___."*

### F. SELF-GRADE RUBRIC — RUN THIS AFTER EVERY DESIGN REP

Score honestly out of 100. Below 75 means re-rep the same problem.

| | Points | Criterion |
|---|---:|---|
| 1 | 15 | Did not draw for the first eight minutes. Restated the core flow and got it confirmed. |
| 2 | 10 | Offered scale numbers rather than asking for them. Stated a **latency budget**. |
| 3 | 15 | **The client column is as full as the server column.** State ownership, transport, cache, and render strategy all named. |
| 4 | 15 | Every technology choice came with a reason *and* a switching condition. Zero "both have tradeoffs." |
| 5 | 15 | Went genuinely deep on one thing — to the level of a data structure, a protocol detail, or a concrete algorithm. |
| 6 | 10 | Named failure modes and what degrades first. |
| 7 | 10 | Narrated continuously; no silent stretch over ~20 seconds. |
| 8 | 10 | Closed with risk / first build / open question, unprompted. |

**Automatic flags:** drew before asking · said "it depends" without then deciding · left the client
side thin · never named a number · ran out of time mid-breadth with no deep dive · bluffed a
technology detail.

## 04 — Client-side system design

The `System Design` guide is the server half and it is good. This is the half it doesn't cover,
and it is the half the invitation went out of its way to name.

### A. WHY THE CLIENT IS A DISTRIBUTED SYSTEM

A modern editor client is not a view. It holds replicated state that can disagree with the server,
it makes concurrent requests that can land out of order, it caches, it retries, it works while
disconnected, and it reconciles. Every hard problem in distributed systems shows up on the client,
just with different names:

| Server concept | Same problem, on the client |
|---|---|
| Replication lag | Local state is ahead of (or behind) the server after an optimistic write |
| Consistency model | Does the UI show what you did, or what the server has confirmed? |
| Idempotency | Retrying a request after a flaky connection, without double-creating |
| Ordering | Two in-flight responses landing in the wrong order — the combobox race |
| Backpressure | A token stream arriving faster than 60 fps can paint |
| Partition tolerance | Offline mode: keep working, reconcile later |
| Write-ahead log | An outbox in IndexedDB that survives a reload |
| Cache invalidation | Exactly as hard as the joke says, plus tab-to-tab coordination |

**The sentence to say in the room**, once, early: *"I want to treat the client as a replica rather
than a view — it has its own copy of the state, its own write path, and its own reconciliation
story. That's where most of the complexity in this product lives."* That framing alone puts you
above most candidates on the axis the invitation names.

### B. THE SEVEN-LAYER CLIENT CHECKLIST

Left column of the whiteboard, top to bottom. Walk it and you cannot leave the client thin.

| # | Layer | The question it answers | Typical answers |
|---|---|---|---|
| 1 | **Input & events** | What triggers work, and how often? | keystroke, scroll, focus, visibility, interval; debounce/throttle/coalesce |
| 2 | **Local state & ownership** | Who owns each piece, and is it server state or UI state? | component state · a store · a query cache · URL · `localStorage` |
| 3 | **Sync engine** | How local and remote converge | optimistic apply + rollback · versioning · last-write-wins · CRDT |
| 4 | **Transport** | How bytes move, in each direction | fetch · SSE · WebSocket · WebRTC · service worker |
| 5 | **Persistence** | What survives a reload, and what must not | IndexedDB · `localStorage` · Cache API · in-memory only |
| 6 | **Render strategy** | How you paint a lot without dropping frames | virtualization · incremental/chunked · memo boundaries · worker offload |
| 7 | **Resilience** | What happens when each of 1–6 fails | retry/backoff · degrade · queue · surface the state |

The layer people forget is **2**. Say the distinction out loud: *"Server state and UI state are
different animals — server state needs caching, invalidation, and a staleness policy; UI state
needs none of that and shouldn't live in the same place."*

### C. THE TRANSPORT LADDER

Climb only as far as the requirement forces. The default of reaching for WebSockets is a common
over-engineering tell; so is polling something that has a real push channel available.

| Rung | Mechanism | Reach for it when | Cost you're accepting |
|---|---|---|---|
| 0 | **Request/response** (`fetch`) | The client can ask when it needs to know | Nothing. Start here. |
| 1 | **Polling** | Updates are rare, latency tolerance is seconds, simplicity wins | Wasted requests; latency = interval/2 |
| 2 | **Long polling** | Push semantics without new infrastructure | A held connection per client anyway |
| 3 | **SSE** (`EventSource`) | **Server → client only**, text, and you want reconnect for free | One direction; ~6 connections/domain on HTTP/1.1 (fine on HTTP/2) |
| 4 | **WebSocket** | Genuinely **bidirectional and continuous** — presence, cursors, collaborative edits | You now own reconnect, heartbeat, resubscribe, message ordering, and auth refresh |
| 5 | **WebRTC data channel** | Peer-to-peer, or latency below what a relay allows | Signalling, NAT traversal, TURN costs |

**The line to say for streamed LLM output specifically:** *"Model output is one-directional text,
so SSE. It's plain HTTP so it goes through corporate proxies, `EventSource` reconnects on its own,
and `Last-Event-ID` gives me resumption almost free. I'd move to a WebSocket if the client needed
to stream back continuously — live cursor presence would do it."*

Worth knowing so you don't get caught: `EventSource` cannot set headers, so auth is a cookie or a
query param — mention it, or use `fetch` with a `ReadableStream` and parse the event framing
yourself, which is what most production LLM clients actually do.

### D. STREAMING, BACKPRESSURE, AND RESUMABILITY

Streaming is where a client design gets interesting and where the deep dive usually lands.

**1. Framing.** Tokens arrive as chunks that respect no boundary you care about — a chunk can
split a word, a UTF-8 code point, or a JSON object. Buffer and split on your delimiter; never
assume one chunk equals one event.

**2. Backpressure.** A fast stream can deliver hundreds of chunks a second. Calling `setState` per
chunk is a render per chunk, and React will happily try. The fix is to decouple arrival rate from
paint rate:

```tsx
// Accumulate in a ref; paint on the frame boundary. Arrival rate and paint
// rate are now independent, which is the whole point.
const buffer = useRef('')
const frame = useRef(0)
const [text, setText] = useState('')

function onChunk(chunk) {
  buffer.current += chunk
  if (frame.current) return                    // a paint is already scheduled
  frame.current = requestAnimationFrame(() => {
    frame.current = 0
    setText(buffer.current)
  })
}
```

Say why: *"Arrival is network-paced, paint is display-paced. Coalescing on `requestAnimationFrame`
means a 500-token-per-second stream still costs 60 renders a second, not 500."*

**3. Cancellation.** Every stream needs a stop that is instant *in the UI* and eventually
propagates to the server. Abort the request, stop consuming, and — importantly — **keep the text
already received**. Users read a cancelled response.

**4. Resumability.** Connection drops mid-response. Three postures, and picking one deliberately
is the signal:

| Posture | Mechanism | When |
|---|---|---|
| Restart | Re-issue the request | Cheap, short responses |
| Resume | Server keeps the generation keyed by id; client sends `Last-Event-ID` / an offset | Long or expensive generations |
| Persist-then-stream | Server writes tokens to durable storage as it generates; the client reads a durable log | The response must survive the client closing entirely — background agents |

**5. The partial-render problem.** If the stream carries structured output (a diff, a tool call,
JSON), the UI must handle *syntactically incomplete* data on every frame. Either render text until
the object closes, or use a streaming-tolerant parser. Naming this unprompted is a strong signal
because it is the bug that ships.

### E. CLIENT CACHE, OPTIMISTIC WRITES, RECONCILIATION

**The cache decision, stated as three questions:** what is the key, when is it stale, and who
invalidates it. If you can answer those three for the main entity in the design, you have said
everything a cache answer needs.

**Staleness policies**, in the order you should consider them:

| Policy | Behaviour | Fits |
|---|---|---|
| Cache-first | Serve cache, never refetch until told | Immutable things: file blobs by hash |
| Stale-while-revalidate | Paint cache instantly, refetch in the background, repaint | Almost everything a UI shows |
| Network-first | Try the network, fall back to cache | Correctness-critical reads |
| No cache | Always fresh | Anything you'd be embarrassed to show stale |

**The optimistic write path**, which is the piece to draw as an explicit loop:

1. Apply locally, immediately, with a client-generated id (`crypto.randomUUID()`).
2. Enqueue the mutation in an outbox with that id as an **idempotency key**.
3. Send. On success, reconcile — replace the optimistic record with the server's, keeping the
   client id → server id mapping so anything referencing it doesn't dangle.
4. On failure, either retry with backoff (transient) or roll back and surface it (permanent).
   **Decide which errors are which, out loud.** A 409 is not a 503.
5. Keep the queue **ordered per entity**, or you get lost-update bugs when two mutations to the
   same object race.

**Rollback is the part people skip.** The line: *"Optimistic UI is a lie you tell the user, so I
need a plan for when the lie is caught. For a create I remove the row and show a retry; for an
edit I need the pre-image, so the outbox entry carries both the mutation and the previous value."*

**Concurrency control between clients:** version numbers or ETags with a compare-and-set on the
server. `If-Match: <etag>` → 412 on conflict → the client decides: rebase, prompt, or last-write-wins.
Say which and why.

### F. OFFLINE, PERSISTENCE, AND CONFLICT

Only if the requirements phase said offline matters. If it doesn't, say *"I'm not building for
offline because ___"* and move on — that also scores.

| Store | Capacity | Sync/async | Use for |
|---|---|---|---|
| In-memory | RAM | sync | Everything transient |
| `localStorage` | ~5 MB | **sync — blocks the main thread** | Tiny prefs, flags. Not data. |
| **IndexedDB** | Large, quota-based | async | The real answer: documents, outbox, cached queries |
| Cache API | Large | async | HTTP responses, via a service worker |
| OPFS | Large, fast | async (+ sync in a worker) | Genuinely file-like workloads; SQLite-in-WASM |

**Conflict resolution ladder**, cheapest first — pick the lowest rung that satisfies the
requirement, and say why the next rung up is unnecessary:

1. **Last-write-wins** on a timestamp. Cheap, lossy. Fine for preferences.
2. **Per-field merge.** Two users editing different fields both win. Fine for forms and metadata.
3. **Operational transform.** Central server transforms concurrent ops. What Google Docs uses;
   correct, and hard to implement.
4. **CRDT.** Convergence without a central authority; works peer-to-peer and offline. Costs
   metadata that grows with edit history, which is the tradeoff to name.

For code editing specifically the honest answer is usually *not* CRDT: **file-level ownership plus
a diff-and-prompt on conflict** is what most tools ship, because developers already have git for
merges. Saying that is a POV.

### G. PERCEIVED PERFORMANCE

The wall-clock number and the felt number are different, and this round rewards knowing which
levers move which.

| Lever | What it does | Where it fits |
|---|---|---|
| **Optimistic UI** | Removes the round trip from the felt path entirely | Any user-initiated write |
| **Speculative/prefetch** | Starts the work before it's certainly needed | Hover intent, likely-next file, next page |
| **Streaming** | First token instead of last token | Anything an LLM generates |
| **Skeletons over spinners** | Removes layout shift, communicates shape | Any list or panel |
| **Debounce with a leading edge** | The first keystroke feels instant; the burst is one request | Search-as-you-type |
| **Stale-while-revalidate** | Zero perceived latency on repeat views | Navigation |
| **Local-first read path** | The network is off the critical path | Editors, indexes, file trees |

**The Cursor-shaped version, and worth rehearsing because it's the likely deep dive:** for inline
completion the felt budget is roughly *"under 100 ms or it isn't ambient."* You cannot get a model
round trip inside that reliably, so the design is not "make the model fast" — it's a stack of
tricks: **debounce so you don't ask on every character; predict and prefetch on a pause; cache by
prefix so a continued keystroke hits a warm result; run a small model at the edge for the common
case and escalate to a large one only when the small one is unconfident; and cancel aggressively
so a superseded request never paints.** Each of those is a client decision, which is precisely why
this problem is a good interview.

### H. RENDERING AT SCALE

| Symptom | Cause | Fix |
|---|---|---|
| 50k rows janks | Painting DOM you can't see | Virtualization: render the window plus overscan |
| Rows are uneven heights | Fixed-height math doesn't apply | Measure and cache heights; estimate then correct |
| Typing lags in a big tree | Re-rendering the whole tree per keystroke | Split state so the input owns its own; memo boundaries at the list item |
| Parsing/diffing blocks input | Long task on the main thread | Web Worker, or chunk with `scheduler.yield`/`requestIdleCallback` |
| Everything re-renders on stream | New object identity every chunk | Coalesce (§D), memoize, key stably |
| Scroll jumps when data loads above | Content inserted above the viewport | Scroll anchoring: pin to an item id, restore offset after paint |

Virtualization numbers to have ready: DOM nodes get expensive in the low thousands; a virtualized
window is typically *visible + 5–10 overscan*; and the moment heights vary you need a measurement
cache, which is the actual complexity.

### I. THE CLIENT FAILURE-MODE PASS

Ninety seconds at minute ~52. Walk the seven layers and name what breaks. Interviewers rarely ask
for this and always notice it.

- **Network drops mid-stream** → resume vs restart, and what the UI shows meanwhile
- **Response lands out of order** → generation counter, not just `AbortController`
- **Server returns 500 on an optimistic write** → rollback path, and is the error retryable
- **Two tabs open** → who owns the socket, how state syncs (`BroadcastChannel`, or a leader
  election with a lock)
- **Auth token expires mid-session** → silent refresh, and what happens to the open stream
- **Clock skew** → don't resolve conflicts on client timestamps you don't trust
- **Quota exceeded in IndexedDB** → eviction policy, and degrade to memory-only
- **The user closes the tab mid-operation** → does the work survive server-side, or is it lost

### J. STATING A LATENCY BUDGET

The single highest-leverage habit for this round. Instead of "it should be fast," decompose:

> *"Target is 100 ms p50 for a suggestion to appear. That's ~10 ms of debounce I've already
> spent, ~20 ms RTT to the nearest edge, which leaves ~60 ms for inference and serialization.
> That budget is what forces a small model at the edge — a large model can't fit, so the large
> model has to be doing something the user isn't waiting on."*

Numbers worth having memorised well enough to say without pausing:

| Thing | Order of magnitude |
|---|---|
| One frame at 60 fps | 16 ms |
| Feels instantaneous | < 100 ms |
| Keeps a train of thought | < 1 s |
| Attention lost | > 10 s |
| Same-region RTT | 1–10 ms |
| Cross-country RTT | ~50–70 ms |
| Transatlantic RTT | ~100–150 ms |
| TLS handshake | 1–2 extra RTTs |
| Memory read | ~100 ns |
| SSD read | ~100 µs |
| LLM time-to-first-token | 100 ms – 1 s |
| LLM per-token, streamed | 10–50 ms |
| Embedding one chunk | 1–10 ms batched |
| Vector search, millions of vectors | 5–50 ms |

The move is not to recite these. It is to **spend them**: name the budget, subtract the fixed
costs, and let what's left dictate the architecture. That is what "systems depth" looks like in a
one-hour round.

## 05 — Five designs, worked

**How to use this section.** Read only the prompt. Close the guide. Set a 45-minute timer, open
Excalidraw, and design it out loud following §03 A. Grade yourself with §03 F. *Then* open the
collapsible.

Reading the answer first converts a rep into a reading, and you already know how to read.

The model answers are not scripts to memorise — they are what a strong 45 minutes looks like, so
you can see where yours was thin. Four are Cursor-shaped because that is the likely flavour; the
fifth deliberately isn't, so you can prove to yourself the method transfers.

### A. TAB — INLINE COMPLETION AT SUB-100 MS

> **Prompt.** *"Design the system behind Cursor's Tab. As a developer types, we predict the edit
> they're about to make and show it inline as ghost text. Tab accepts it. It should feel
> instantaneous, it runs for millions of developers, and inference is expensive."*

This is the one to do first. It has a hard latency constraint, a genuinely complex client, and a
cost story — all three of the things the invitation says they grade.

<details>
<summary>Model answer — Tab</summary>

**Requirements (8 min).** Core flow: keystroke → decide whether to predict → request → ghost text
→ accept or invalidate. Assume 1M DAU, 4 h/day of editor open, keystrokes bursting to ~5/s.
Quality bar: **p50 under 100 ms for the suggestion to appear, p99 under 300 ms; over 300 ms is
worse than nothing** because the user has typed past it. Acceptance rate is the product metric and
also the cost lever. Constraint to raise unprompted: source code leaves the machine, so there must
be a privacy posture and an enterprise story.

**The budget, stated before any boxes.** ~100 ms is the *felt* bar — under it a suggestion is
ambient, over ~300 ms it arrives after the user has typed past it. Subtract the fixed costs: ~20 ms
RTT to a nearby edge, ~10 ms of client debounce, ~10 ms serialize/deserialize and paint → **~60 ms
left for inference**. No frontier model fits in 60 ms.

That subtraction is the whole architecture, and the real numbers make the point more sharply than
the derivation does. Cursor publishes p50 **server** latency of 260 ms for its Tab model — down
from 475 ms — against a felt target of ~100 ms. In other words the gap is real and permanent, and
it is closed on the client, not by making the model faster. Prefix caching, speculation on a pause,
and aggressive cancellation are therefore load-bearing structure rather than optimizations. Saying
*"their published p50 is 260 ms, so the client has to be hiding roughly 160 ms"* is a much stronger
opening than any budget you derive from first principles.

**Client (the half that matters here).**

1. *Trigger policy — and this is where the interesting answer lives.* The obvious version is
   heuristics: debounce ~10–30 ms, suppress inside a word, during fast continuous typing, and
   immediately after a rejection at the same position. The better version, and what Cursor actually
   ships, is to make **"should I suggest at all" part of the model's learned policy** rather than a
   rule. Their reward is +0.75 for an accepted suggestion, −0.25 for one shown and rejected, and 0
   for staying silent — so a reward-maximizing policy suggests only when it estimates at least a
   25% chance of acceptance. That reframing is worth saying out loud: **a bad suggestion is not
   free, it is actively negative**, and once you price it that way the trigger stops being a
   debounce and becomes a decision the model makes. It bought them 21% fewer suggestions at a 28%
   higher accept rate.
2. *Context assembly.* This is the interesting client problem. The prompt is not "the file" — it's
   a budgeted window: the ~100 lines around the cursor, plus recently edited regions, plus the
   current diff, plus a few symbols resolved from the local index. Assemble it in a **worker** so
   a big file doesn't block typing, and cap it by token budget with a fixed priority order.
3. *Prefix cache.* Key suggestions by (file id, cursor context hash). If the user types exactly
   the characters the model predicted, the next suggestion is a **continuation of a cached one** —
   no round trip at all. This is the single biggest perceived-latency win and the thing most
   candidates miss.
4. *Speculative execution.* On a typing pause, fire for the most likely next positions. Cheap
   relative to a miss.
5. *Cancellation.* Every superseded request is aborted, and there is a **generation counter** as
   well, because abort alone does not stop an already-resolved response from painting. Say this
   explicitly — it's the same guard as the combobox race and it shows the pattern generalises.
6. *Render.* Ghost text is a decoration, not a document mutation. It must not enter undo history,
   must not fire change events, and must be invalidated the instant the buffer changes underneath.
7. *Two tabs / multiple windows.* One connection per window is fine here since requests are
   stateless; if we later stream, elect a leader with the Web Locks API.

**Server.**

- *Edge tier* terminates connections close to the user — this is where the 20 ms RTT assumption
  comes from, and it is a real architectural choice, not a detail.
- *Router* classifies: cache hit → return; trivial completion (closing a bracket, finishing an
  obvious identifier) → a tiny model or pure heuristics; otherwise → the small speculative model.
- *Model tier* is a **cascade**. A small distilled model handles the common case inside budget.
  Escalate to a larger model only when the small model's confidence is low *and* the user has
  paused long enough that a slower answer is still useful. Cost per request is the reason this is
  a cascade rather than one model.
- *Continuous batching* on the inference servers: requests join an in-flight batch rather than
  waiting for a batch window. This is what makes p50 and throughput compatible.
- *KV-cache reuse* keyed by prefix, with session affinity so a returning request lands on the node
  that already has the prefix warm. Affinity is a load-balancing decision with a real failure mode
  — name it: hot nodes, and a fallback to any node on miss.
- *Async path* logs (context, suggestion, accepted?) to a stream for training data and metrics.
  Off the hot path entirely.

**Failure and degradation.** Inference tier saturated → shed load by dropping to heuristics-only,
because a slightly worse suggestion is much better than a late one. Edge unreachable → fall back
to direct-to-region with a raised debounce so the user isn't spamming a slow path. Model returns
garbage → client-side validity check (does it parse? does it duplicate what's already there?)
before painting.

**Cost.** Cost per accepted suggestion is the metric, not cost per request. Levers, in order:
trigger policy (fewest requests), cache hit rate, model size cascade, batching efficiency, and
token budget on the context window.

**Privacy.** Never persist code by default; enterprise mode gets a dedicated tenant, no training
on customer code, and optionally a self-hosted inference tier. Say this before being asked.

**Close.** Biggest risk is the acceptance-rate/latency tradeoff — a bigger model suggests better
and lands later, and the only way to settle it is an online experiment measuring accepted
characters per session, not offline eval. First thing I'd build is the client trigger policy and
the prefix cache, because they are the cheapest large wins and they're independent of the model.

</details>

### B. AGENT CHAT — STREAMING MULTI-FILE EDITS

> **Prompt.** *"Design the chat panel where a developer describes a task, an agent reads the
> codebase, and edits stream back across several files. The user watches them arrive and can
> accept or reject each one, keep typing while it runs, or stop it. It has to survive a reload."*

The client half here is genuinely harder than the server half, which is what makes it a strong
prompt for this round.

<details>
<summary>Model answer — Agent chat</summary>

**Requirements.** Core flow: message → agent plans → tool calls (read, search, edit) → edits
stream into the UI as diffs → user accepts/rejects per hunk → conversation continues. Assume runs
last 10 s to 5 min and touch 1–20 files. Must survive reload mid-run. Must be interruptible
within ~100 ms of felt time. The user may edit the same files while the agent is running — I'd ask
whether we allow that, and design for "yes" because that's the honest product answer.

**The decision that shapes everything: where does run state live?**

The naive design streams straight into React state, and it fails the reload requirement instantly.
So: **the run is a server-side durable object, and the client is a subscriber to its event log.**
The client is not the source of truth for anything except unsent input and accept/reject decisions
it hasn't committed yet.

That gives resumption almost free: on reload, the client asks for the run's events from offset N.

**Transport.** SSE for the run stream — one direction, text, reconnects natively, and
`Last-Event-ID` is exactly the offset mechanism the design already needs. User actions (stop,
accept, reject, follow-up message) are ordinary `POST`s. I'd only take a WebSocket if we added
presence or collaborative viewing of a run.

**Event model.** The stream is not tokens — it's typed events, each with a monotonic id:

- `message_delta` — assistant prose, token by token
- `tool_call_start` / `tool_call_end` — with a stable id
- `file_edit_begin { path, editId }` · `file_edit_delta { editId, chunk }` · `file_edit_end { editId, hash }`
- `run_status` — planning / running / awaiting-input / done / error

Typed events rather than a text blob is the choice to defend: the UI needs to render a diff
progressively and attach accept/reject state to a specific edit, and you can't do that against
undifferentiated text.

**Client architecture.**

1. *Event reducer.* Events fold into a normalized store keyed by `editId` and `messageId`.
   Idempotent by event id, so a reconnect that replays overlapping events is harmless. This is the
   piece I'd write on the board as actual code.
2. *Backpressure.* Coalesce deltas on `requestAnimationFrame` (§04 D). A five-file edit burst
   should be 60 renders/second, not 600.
3. *Partial diff rendering.* A streaming edit is a syntactically incomplete diff. Render arriving
   lines as a "pending" hunk; only compute the real hunk boundaries at `file_edit_end`. Cheap
   version for the round: append-only rendering during the stream, re-render properly on close.
4. *Apply model.* Edits land in a **staged layer**, not the real buffer. The editor shows
   staged-vs-current as a decoration. Accept commits to the buffer and to undo history; reject
   drops the staged hunk. Nothing the agent does is un-undoable.
5. *Conflict with the human.* If the user edits a file with staged hunks, the staged hunk's anchor
   is invalidated. Options: re-anchor by context match, or mark it stale and ask. I'd re-anchor
   with a fuzzy context match and fall back to stale — and I'd say why: silent re-anchoring that
   guesses wrong corrupts code, which is unforgivable in this product.
6. *Stop.* Optimistically flip the UI to "stopping" immediately, `POST /stop`, abort the SSE
   consumer. **Keep everything already received.** The felt latency of stop is a client concern
   entirely.
7. *Reload.* Persist `{ runId, lastEventId }` in `localStorage`; on mount, resubscribe from the
   offset. Staged-but-undecided hunks live in IndexedDB so they survive too.

**Server.**

- *Run orchestrator* — a durable workflow per run (a state machine with checkpoints, not a
  long-lived process holding memory). It appends every event to a per-run **append-only log** in
  durable storage before fanning it out. Write-then-publish, so a subscriber joining late and a
  subscriber reconnecting both read the same log.
- *Stream gateway* — holds the SSE connections, replays from offset, tails the log. Stateless and
  horizontally scalable, which matters because connections are long-lived.
- *Tool execution* — sandboxed workspace with the repo checked out; file reads/searches hit a
  local index; edits are produced as diffs against a known base hash so the client can detect drift.
- *Model calls* stream into the orchestrator, which translates model output into the typed event
  vocabulary. The translation layer is where malformed model output gets contained.

**Failure modes.** Gateway dies → client reconnects with `Last-Event-ID`, no loss, because the log
is the truth. Orchestrator dies → workflow resumes from its last checkpoint; already-emitted events
are not re-emitted because they're in the log. Model produces an edit against a stale base →
detected by base hash, surfaced as a conflict rather than applied. Run abandoned (tab closed) →
it either completes and persists or is reaped by a TTL; I'd let it complete, because a user who
closed a laptop wants the result when they reopen.

**Close.** Biggest risk is the human-edits-during-run conflict path — it's the one that can corrupt
work, so it deserves the most care and the most conservative default. First thing I'd build is the
event log plus the reducer, because every other feature is a consumer of those two.

</details>

### C. CODEBASE INDEX — SEMANTIC SEARCH OVER A REPO

> **Prompt.** *"Design codebase indexing: when a developer opens a repo, we make its contents
> searchable by meaning so the agent can retrieve relevant context. Repos range from a hundred
> files to a million. It has to stay fresh as they type, and enterprise customers won't let source
> code leave their network."*

The one with a genuine data-pipeline shape *and* a hard privacy constraint. It also has an obvious
wrong answer — "embed the whole repo on every open" — which makes the incremental story the test.

<details>
<summary>Model answer — Codebase index</summary>

**Requirements.** Core flow: open repo → index → agent issues a semantic query → top-k chunks come
back with file/line spans. Sizes: p50 maybe 5k files, tail into millions. Freshness: an edit
should be searchable in seconds, not minutes. **Privacy is a hard requirement, not a nice-to-have**
— and it forks the architecture, so I'd settle it in the requirements phase.

**Chunking — the decision with the most leverage on quality.** Not fixed-size windows. Chunk on
**syntactic boundaries**: function, class, or top-level block, via tree-sitter, with a
parent-context header (file path, enclosing class, imports) prepended to each chunk so an embedding
of a method body knows what it belongs to. Overlap slightly at boundaries. Oversized functions get
split with the signature repeated. The reason to say: an embedding of half a function is an
embedding of nothing.

**Incremental indexing, which is the real problem.**

1. Watch the filesystem (debounced, batched — a `git checkout` changes thousands of files at once
   and must not trigger thousands of jobs).
2. Hash each file (content hash). Unchanged hash → skip entirely.
3. For changed files, re-chunk and hash each **chunk**. Only chunks whose hash changed get
   re-embedded. In practice an edit to one function re-embeds one chunk.
4. Delete vectors for chunks that disappeared; upsert the new ones. Keyed by
   `(repoId, filePath, chunkHash)`.
5. Content-addressed embeddings are cacheable **across users**: the same file at the same commit
   in a popular open-source dependency embeds once globally. Big cost win, and worth naming
   because it's non-obvious. It also has a privacy caveat — only safe for content already public,
   so the cache is keyed by a hash and only populated from public sources.

**Cold start.** A million-file repo cannot block. Index in priority order — files open in the
editor, then recently changed by git, then imports of those, then breadth-first over the rest — and
make the index **queryable while incomplete**, reporting coverage. Show progress. Merkle-tree the
directory structure so a re-open only walks subtrees whose hash changed.

**Storage and retrieval.** Vector index with an ANN structure (HNSW or IVF-PQ); exact search is
fine up to ~10⁴ vectors and stops being fine well before a million. Metadata filters (path glob,
language, git-tracked) applied as pre-filters, which is a real constraint on which ANN index you
can use. **Hybrid retrieval**: dense vectors plus lexical BM25, fused with reciprocal rank fusion —
because developers search for exact identifiers constantly and dense retrieval is bad at rare
tokens. Then a small cross-encoder rerank over the top ~50. Saying "hybrid, because exact symbol
names are the failure case of pure embeddings" is the depth signal here.

**The privacy fork — this is where a POV is required.**

*Cloud-indexed (default).* Chunks are embedded server-side; store **vectors plus file paths and
line ranges, not source text**. Retrieval returns spans, and the *client* reads the actual bytes
off local disk before they go into the prompt. That means a breach of the vector store leaks
structure and embeddings, not source. Vectors are not perfectly non-invertible — say so honestly —
so this is a mitigation, not a proof.

*Local-only (enterprise).* Embedding model runs on the developer's machine or on a customer-hosted
node; the index lives in local storage (SQLite + a vector extension). Costs quality (smaller
embedding model) and CPU, buys a hard guarantee. Same retrieval interface, so the agent code
doesn't change — that interface stability is the thing that makes the fork affordable.

**Client's role.** File watching, hashing, chunk boundaries via a local parser, and the read-back
of spans. A worker thread — parsing a large repo on the main thread would freeze the editor. The
client also owns a small hot cache of recently retrieved chunks.

**Failure and scale.** Embedding service down → fall back to lexical-only search and say so in the
UI; degraded retrieval beats none. Index drift (vectors point at lines that moved) → detect via
file hash mismatch at read time and re-index that file synchronously before answering. Quota →
evict by least-recently-queried repo.

**Close.** Biggest risk is retrieval quality, which is invisible until agents give bad answers, so
I'd build an eval set of (query → expected file) pairs from real sessions before optimising
anything. First build: the chunker and the incremental pipeline, since re-embedding cost dominates
the bill.

</details>

### D. BACKGROUND AGENTS — A FLEET OF REMOTE WORKERS

> **Prompt.** *"Design background agents: a developer kicks off a long-running task that executes
> remotely in its own environment, possibly for an hour, across many concurrent runs. They close
> their laptop, come back, and want to review what happened and turn it into a PR."*

The most server-weighted of the five. Do it to prove you can still balance the columns when the
client is genuinely the smaller half — the trap is letting the client column go empty.

<details>
<summary>Model answer — Background agents</summary>

**Requirements.** Core flow: describe task → environment provisions → agent works → progress
observable → result is a branch/PR to review. Assume runs of 1–60 min, thousands concurrent,
bursty. Must survive the client disconnecting entirely. Must not be able to exfiltrate secrets or
escape into other tenants — I'd raise isolation unprompted, because "we run untrusted model-authored
code" is the defining property of this system.

**Control plane / data plane split**, drawn first.

*Control plane:* run registry, scheduling, quotas, auth, and the event log. Small, transactional,
Postgres-backed.

*Data plane:* the sandboxes. Ephemeral, isolated, disposable, and the expensive part.

**Isolation — the decision to have a POV on.** Containers alone are not sufficient for
model-authored code; shared-kernel escapes are a real class. I'd argue for **microVMs**
(Firecracker-class) per run: a real kernel boundary, ~125 ms boot, and a memory footprint that
still allows density. Network egress default-deny with an allowlist (package registries, the git
remote), because otherwise the sandbox is an exfiltration channel. Secrets injected as short-lived
scoped tokens, never long-lived credentials, and never the user's own git credentials — the agent
pushes to a namespaced branch via a scoped bot identity.

Present the microVM choice as **your** position, not as what Cursor does. What they have published
is that cloud agents run on Linux VMs built from a Cursor-defined Dockerfile, with egress
restrictions, scoped and proxied git remote access, secret scanning in commits, and secret
redaction in tool results — the security posture above is confirmed; the specific isolation
primitive is not. Asserting the wrong internal detail to someone who works on it is a much worse
outcome than defending a clearly-labelled opinion.

**Scheduling.** Runs go to a queue partitioned by tenant so one customer's burst can't starve
another (fair queuing, not FIFO). Warm pool of pre-booted VMs to hide boot latency; autoscale on
queue depth with a scale-up bias, since a queued developer is an idle developer. Hard timeouts and
a cost ceiling per run — an agent in a loop is a billing incident.

**Snapshotting.** Provisioning a repo + dependencies is the slow part, not the VM. Cache a
filesystem snapshot per (repo, lockfile hash) and boot from it, so a warm start is seconds and a
cold start is minutes. This is the single biggest latency lever, so it's worth a box of its own.

**Durability.** Same shape as §05 B: an append-only per-run event log in the control plane. The
sandbox streams events to it; every consumer reads from it. The run's output is a git branch pushed
to the remote — which is the real durability story, since git is already the artifact store the
user trusts.

**Client.** Smaller here, but not empty, and I'd make sure the column has content:

- A run list, which is a **subscription to many runs at once** — one SSE connection multiplexing
  status for all active runs, rather than N connections.
- Detail view resumes an individual run's event log from an offset (identical mechanism to §05 B —
  worth pointing out the reuse).
- Local persistence of which runs the user has already reviewed, so returning after a day doesn't
  present everything as new.
- Notifications: the user is *by design* not looking. Web push or email on completion, with the
  service worker handling the push while the tab is closed.
- Review UI is diff-per-file over the branch — the same component as §05 B's accept/reject,
  operating on a completed diff instead of a streaming one.

**Failure modes.** Sandbox crashes → run marked failed with logs retained; retry is a user
decision, not automatic, because agent work is not idempotent. Control plane loses the sandbox
(network partition) → heartbeat timeout reaps it; the VM self-destructs on lost heartbeat so we
never leak compute. Agent produces a broken branch → that's a normal outcome, surfaced as a diff
to reject, not an error. Runaway cost → per-run token and wall-clock ceilings, enforced in the
sandbox and in the control plane.

**Close.** Biggest risk is isolation — one escape is a company-ending event, so I'd spend the
security budget there and accept worse density. First build: the event log plus the sandbox
lifecycle, since correctness of the run record is what everything else displays.

</details>

### E. COLLABORATIVE REVIEW COMMENTS — THE NON-CURSOR ONE

> **Prompt.** *"Design threaded comments anchored to lines of a diff, like GitHub's review UI.
> Multiple reviewers are in the same PR at the same time. Comments must stay anchored when the
> author pushes new commits, and reviewers should see each other's comments appear live."*

Do this one **last**, and only after the other four. Its purpose is to prove the method isn't four
memorised answers: no streaming LLM, no inference budget, and it still fills both columns.

<details>
<summary>Model answer — Review comments</summary>

**Requirements.** Core flow: reviewer selects a line range in a diff → writes a comment → it
appears for everyone on that PR. Threads, replies, resolve. Assume tens of concurrent reviewers on
a hot PR, thousands of comments on the largest. Anchoring must survive force-pushes. Latency bar
is soft — sub-second for your own comment to appear is enough — which immediately tells me
optimistic UI is sufficient and I don't need anything exotic.

**The hard part, named early: anchoring.** A comment is not attached to "line 42." Line 42 moves.
Store the anchor as `{ commitSha, filePath, side (old/new), lineNumber, contextHash }` where
`contextHash` hashes a few lines around the target. On a new commit, re-anchor by:

1. Exact match — the same lines exist unchanged at a new offset → move the comment.
2. Context match — the surrounding lines match with small drift → move it, mark "moved."
3. No match → mark the comment **outdated**, keep it on the old commit, and show it collapsed.

Never guess silently. Attaching a review comment to the wrong line is worse than admitting it
moved, and saying that out loud is the POV.

**Client.**

1. *State ownership.* The diff is server state, cached and rarely changing (immutable per commit —
   cache-first, keyed by sha). Comments are server state that changes constantly —
   stale-while-revalidate plus a live channel. Draft text is UI state and must **never** be lost,
   so it goes to `localStorage` on every keystroke, debounced.
2. *Optimistic post.* Client-generated uuid as the idempotency key, render immediately as pending,
   reconcile on ack, roll back with the text preserved into the composer on permanent failure. The
   nightmare outcome is a reviewer losing a long comment; the design exists to prevent it.
3. *Live updates.* SSE per PR, not WebSocket — updates are server→client only. Events are
   `comment_created`, `comment_updated`, `thread_resolved`, each with an id so the reducer is
   idempotent and my own optimistic comment doesn't double-render when it echoes back.
4. *Presence* (who else is viewing) is the one bidirectional need. I'd either take it on a
   WebSocket, or — cheaper and honestly good enough — a heartbeat `POST` every 20 s and let it ride
   the same SSE channel back down. Naming that I'd rather not add a socket for presence alone is
   itself a decision.
5. *Rendering scale.* A 5,000-line diff virtualizes, which fights with comments inserted inline at
   arbitrary positions. Solution: treat the diff as a flat list of rows where a comment thread *is*
   a row, with measured (not fixed) heights and a measurement cache. Scroll anchoring on the row id
   so a thread expanding above the viewport doesn't move the reader's position.
6. *Multi-tab* → `BroadcastChannel` so a comment posted in one tab appears in the other without a
   second connection.

**Server.**

- Comments table keyed by `(prId, threadId)`, with the anchor fields denormalized for query. The
  access pattern is "all comments for a PR, grouped by thread, ordered by created_at" — that's the
  index.
- Re-anchoring runs asynchronously on push: a job diffs old→new, recomputes anchors, writes
  results, emits events. Off the request path because it's O(comments) and a push shouldn't block.
- Fanout is small (tens of reviewers), so a simple pub/sub keyed by PR id is sufficient — no need
  for a fanout-on-write index. Saying "the fanout is small so I'm not building a fanout system" is
  a correct piece of scoping.
- Notifications (mentions, replies) go through a queue, deduped per user per PR per window.

**Failure modes.** SSE drops → reconnect with `Last-Event-ID`, replay missed comment events from a
per-PR log; a comment appearing 10 s late is acceptable, a comment never appearing is not.
Re-anchor job fails → comments stay on their old commit marked outdated, which is the safe
degradation. Two reviewers resolve the same thread → last-write-wins is genuinely fine, and I'd say
why: the outcome is identical either way.

**Close.** Biggest risk is anchoring quality, because a mis-anchored comment destroys trust in the
whole review surface; I'd invest in an offline eval over historical PRs before shipping the fuzzy
matcher. First build: comment CRUD with optimistic UI and exact-match anchoring only — outdated is
an acceptable v1, wrong is not.

</details>

### F. IF YOU GET A PROMPT THAT ISN'T ONE OF THESE

Which is likely. The method, compressed:

1. **Find the constraint that makes it hard.** Latency? Concurrency? Scale? Privacy? Offline?
   Cost? Say it out loud: *"the thing that makes this interesting is ___."* Everything downstream
   is justified by that sentence.
2. **Budget it.** Turn the constraint into a number and subtract the fixed costs (§04 J).
3. **Draw two columns and fill both.** Left column = the seven layers (§04 B).
4. **Pick the lowest rung that works** on every ladder — transport (§04 C), conflict resolution
   (§04 F), caching (§04 E) — and say why the next rung up is unnecessary.
5. **Go deep on one thing** by minute 36, to the level of a data structure or a protocol detail.
6. **Walk the failure pass** (§04 I) and close with risk / first build / open question.

## 06 — Round 2: the coding hour

### A. THE CLOCK

Assume ~50 working minutes of the 60 once intros and the pad link are done. The single most
important structural decision is that **the last twelve minutes belong to tests and they are not
negotiable.** Everything else compresses.

| Minutes | Phase | Output |
|---|---|---|
| 0–2 | **Setup & scope** | Ask about the test runner (§01 E). Restate the problem in one sentence and get it confirmed. |
| 2–7 | **The API, out loud** | The prop signature typed into the pad, before any body. Ask the two questions in §07 A. |
| 7–12 | **Skeleton renders** | Static markup with hardcoded data, on screen, working. |
| 12–35 | **Core behaviour** | The thing they actually asked for, built in the order in §C. |
| 35–38 | **Checkpoint** | Say where you are, name what's left, name what you'll cut. |
| 38–50 | **Tests** | Four to six, in the order in §08 A. Run them if the pad can. |
| 50–55 | **Extensions or polish** | Only if genuinely done. Otherwise more tests. |
| 55–60 | **Name what you skipped** | The closing move in §E. |

**The checkpoint at 35 is the discipline that saves the round.** Say out loud: *"I've got twenty
minutes left. Core interaction works, keyboard doesn't yet. I'm going to write tests now and come
back to keyboard if there's time, because I'd rather hand you a tested partial component than an
untested complete one."* That sentence is itself evidence of the judgement they're grading.

### B. THE FIRST FIVE MINUTES, WORD FOR WORD

> *"Before I write the body, let me sketch the interface — I find that's where most of the design
> decisions actually are."*

Then type it, and narrate as you type. Two questions to ask while you do:

1. **"Should this be controlled, uncontrolled, or both?"** — the highest-value API question that
   exists, and asking it demonstrates you know there's a difference. If they say "your call," say
   *"I'll do both, defaulting to uncontrolled — it's about six lines and it's the difference
   between a component that composes and one that doesn't."*
2. **"Is this a leaf component or a container?"** — i.e. does it own its data fetching, or does the
   parent hand it data? Prefer taking data as a prop; it's more testable, and testability is graded.

Then state the shape:

```tsx
// The interface first — this is what I'd want a teammate to read.
type ThingProps = {
  items: Item[]                                  // data in, so the component stays testable
  value?: string                                 // controlled…
  defaultValue?: string                          // …or uncontrolled. Presence of `value` decides.
  onChange?: (value: string, item: Item) => void // fires in BOTH modes
  disabled?: boolean
  renderItem?: (item: Item) => React.ReactNode   // escape hatch, not a config explosion
}
```

If the pad is JavaScript, write exactly that as a comment block. The API is graded; the type syntax
is not.

### C. BUILD ORDER

Same order every time, so it's automatic under pressure:

1. **Static render with hardcoded data.** Something on screen inside five minutes. This gives you a
   feedback loop and gives the interviewer something to react to.
2. **The core interaction, happy path only.** No edge cases, no keyboard, no ARIA.
3. **State correctness.** Derive everything derivable. Say *"I'm computing this rather than storing
   it — stored derived state is state that can disagree with itself."*
4. **Async and races**, if there's a network call: debounce, abort, generation guard. This is where
   most candidates are actually differentiated, so don't rush past it silently.
5. **Keyboard and semantics.** `role`, `aria-*`, arrow keys. Say the APG pattern name if you know
   it.
6. **Tests.** At 38, whatever state you're in.
7. **Edge cases and empty/error states**, if time remains.

**Never** start with CSS. **Never** start with folder structure. They told you neither is graded.

### D. NARRATION THAT SCORES

The interviewer is scoring your reasoning, and they can only score what they hear.

| Situation | Say |
|---|---|
| Choosing state shape | *"I'm storing the id, not the object — one source of truth, and it survives the list refetching."* |
| Reaching for a ref | *"This is a mutable value that shouldn't trigger a render, so it's a ref not state."* |
| Adding a guard | *"Two requests can be in flight; abort stops the fetch but not an already-resolved promise, so I need a generation counter too."* |
| Deferring | *"I'm hardcoding this for now and I'll come back — flagging it so it doesn't look like I think it's finished."* |
| Stuck | *"I'm going to check the exact signature — one second."* Then actually search. Silence is worse. |
| Fixing your own bug | *"That's off by one because I'm comparing after the increment."* Debugging out loud is a positive signal, not an admission. |

**On typing speed:** the one credible candidate report about Cursor says the questions are
practical but time-starved. That means fluency in the boring parts — imports, hook signatures,
`map` with a key, an event handler — is worth real points, and it is exactly what atrophies with
AI autocomplete on. That's what D-4's three-mini-build day is for.

### E. WHEN TIME RUNS OUT

Never let the clock end mid-keystroke. At minute 55, stop and deliver a summary:

> *"Where I got to: the core selection works, it's controlled and uncontrolled, and there are five
> tests covering the main paths. What I'd do next, in order: keyboard navigation — arrows, Enter,
> Escape, roughly fifteen lines; then a live region announcing the result count, about four lines,
> because otherwise screen reader users get nothing when the list changes; then the empty and error
> states. The thing I'd want to revisit is the debounce interval — 200 ms is a guess and I'd
> measure it."*

Naming a cut precisely demonstrates the same knowledge as building it, at a fraction of the cost.
Silently omitting it demonstrates nothing.

### F. SELF-GRADE RUBRIC — RUN THIS AFTER EVERY CODING REP

| | Points | Criterion |
|---|---:|---|
| 1 | 20 | **API written and spoken before the body.** Controlled/uncontrolled addressed. No boolean soup, no config-object sprawl. |
| 2 | 25 | **Correctness:** the happy path works, and the obvious stress case (rapid input, empty data, unmount mid-flight) doesn't break it. |
| 3 | 25 | **Tests exist, test behaviour, and would fail if the component broke.** At least four. |
| 4 | 10 | Something rendered within five minutes; ran the code repeatedly rather than at the end. |
| 5 | 10 | Narrated continuously; every non-obvious choice got a reason. |
| 6 | 10 | Closed by naming the cuts, specifically and in priority order. |

**Automatic flags:** wrote CSS before behaviour · stored derived state · no tests · tests that
assert implementation details · went silent for minutes · ran out of time with no summary ·
used a library the pad doesn't have without checking.

## 07 — Component API design

They defined this axis inline in the invitation — *"the props and interface your component
exposes"* — which means they expect it to be under-served. It is the cheapest twenty points in the
round because it costs three minutes and most candidates spend zero.

### A. THE SIX QUESTIONS, IN ORDER

Run these on any component prompt. They take ninety seconds and they produce the whole interface.

**1. What data does it need, and who owns it?**
Take data as a prop rather than fetching inside, unless asked otherwise. `items: Item[]` beats
`fetchUrl: string` — it's testable, reusable, and it makes the loading state the parent's problem,
which is where it belongs. If it must fetch, take the *fetcher* as a prop:
`fetchOptions: (q: string, signal: AbortSignal) => Promise<Item[]>`. Now it's still testable.

**2. What state does it own, and could the parent need it?**
Anything a parent could plausibly want to read or set gets the dual API (§B). Transient state —
hover, focus, the text mid-typing — stays internal, and saying *"I'm keeping the query internal
because a parent that wanted it would be a different component"* is a real answer.

**3. What are the events, and what do they carry?**
`onChange(value)` is thin. `onChange(value, item)` saves every consumer a lookup. `onSelect(item,
{ via: 'keyboard' | 'mouse' })` is better still if the distinction matters. Pass what the consumer
would otherwise have to reconstruct — and no more.

**4. Where are the escape hatches?**
One `renderItem` prop beats six boolean flags. The test: if a consumer wants something you didn't
anticipate, can they get it without forking? Render props, `children` as a function, or a
compound-component API. Say *"I'd rather give one escape hatch than accumulate flags."*

**5. What are the defaults, and is the zero-config case sensible?**
`<Combobox items={items} />` should work. Every prop past the first two should have a default.
Name them out loud — defaults *are* API design.

**6. What can't this component do, by design?**
Stating a non-goal is a senior move: *"This doesn't do multi-select. If we needed it I'd change
`value` to `value: string[]` and keep everything else — the shape survives."*

### B. THE DUAL API — SIX LINES, MEMORISE THEM

The highest-frequency API question in frontend interviews, and it fits in a breath.

```tsx
function Thing({ value: valueProp, defaultValue, onChange }) {
  const [uncontrolled, setUncontrolled] = useState(defaultValue)
  const isControlled = valueProp !== undefined      // presence of the prop, NOT of defaultValue
  const value = isControlled ? valueProp : uncontrolled

  const commit = (next) => {
    if (!isControlled) setUncontrolled(next)        // controlled parent owns the state
    onChange?.(next)                                // fires in BOTH modes, always
  }
}
```

Three things that are wrong in most people's version, and all three are worth saying out loud:

- **The test is `valueProp !== undefined`.** Keying off `defaultValue === undefined` inverts it and
  silently kills controlled mode when both props are passed.
- **`onChange` fires in both modes.** An uncontrolled component that doesn't notify its parent is
  a component you can't build anything on.
- **The mode must not flip mid-life.** React warns about this for inputs for a reason; if asked,
  say you'd capture `isControlled` on first render.

### C. THE PATTERNS CATALOGUE

| Decision | Weak | Strong | The line to say |
|---|---|---|---|
| Value shape | `selectedIndex: number` | `value: string` (an id) | *"Index breaks when the list reorders or filters."* |
| Multiple booleans | `isOpen, isLoading, isError` | `status: 'idle' \| 'loading' \| 'error'` | *"Booleans let me represent states that can't exist."* |
| Customisation | 6 flags | `renderItem` / `children` as a function | *"One escape hatch instead of anticipating every need."* |
| Related props | `label, labelId, labelClassName…` | Compound components: `Thing.Label` | *"Structure belongs in JSX, not in prop names."* |
| Callback payload | `onSelect(id)` | `onSelect(id, item)` | *"Saves every consumer the lookup I already did."* |
| Async source | `url: string` | `fetch: (q, signal) => Promise<T[]>` | *"Injectable, so it's testable, and it can be cancelled."* |
| Ids | Hardcoded | `useId()` | *"Two on one page must not collide, and it's SSR-safe."* |
| Imperative needs | A `ref` to internals | `useImperativeHandle` with a named surface | *"I expose `focus()`, not the node."* |
| Styling | `style` objects as props | `className` passthrough + data attributes | *"State goes in `data-state`, so CSS reads the real state."* |
| Keys | `key={index}` | `key={item.id}` | *"Index keys reuse the wrong DOM when the list changes."* |
| Children | `items` + a config array | `children` where it's genuinely composition | *"If it looks like markup, it should be markup."* |
| Nothing to show | Render `null` silently | An explicit empty state, or document it | *"Empty and loading are different, and users can tell."* |

### D. THE THREE-MINUTE API DRILL

Run this daily, on components you have never built. Write only the interface — no implementation —
then check it against the six questions. It's the cheapest rep in this guide.

Queue for the twelve days: a date-range picker · a file uploader with progress · a rating widget ·
a toolbar with overflow · a pagination control · a split button · a resizable panel group · a
mention autocomplete inside a textarea · a keyboard-shortcut registry · a virtualized table with
sticky columns · a toast queue · an inline editable cell.

For each, three minutes, out loud, then ask: *which of the six questions did I skip?*

## 08 — Test quality

One of three named axes, and the one with the least practice behind it. Twelve minutes of tests is
worth more than twelve minutes of the feature you didn't finish, because only one of those is on
the rubric twice (it's also evidence for "code correctness").

### A. THE FIVE TESTS THAT ALWAYS EARN

Write them in this order. If you only get three, these are the three.

**1. It renders what it's given.** The cheapest test and it catches the most breakage.

```tsx
test('renders each item', () => {
  render(<Thing items={ITEMS} />)
  expect(screen.getAllByRole('option')).toHaveLength(3)
})
```

**2. The core interaction produces the right callback.** This is the test that proves the component
does its job.

```tsx
test('selecting an item reports it to the parent', async () => {
  const onSelect = vi.fn()
  const user = userEvent.setup()
  render(<Thing items={ITEMS} onSelect={onSelect} />)

  await user.click(screen.getByRole('option', { name: 'redux' }))

  expect(onSelect).toHaveBeenCalledWith('redux', ITEMS[1])   // assert the payload, not just the call
})
```

`toHaveBeenCalledWith` rather than `toHaveBeenCalled` — asserting the payload is where the API
design you just defended gets verified.

**3. Controlled and uncontrolled both work.** Two short tests, and almost nobody writes them.

```tsx
test('uncontrolled: manages its own value and still notifies', async () => { … })
test('controlled: renders the prop, and does not move on its own', async () => {
  const onChange = vi.fn()
  render(<Thing items={ITEMS} value="react" onChange={onChange} />)
  await userEvent.click(screen.getByRole('option', { name: 'redux' }))
  expect(onChange).toHaveBeenCalledWith('redux')
  expect(screen.getByRole('option', { name: 'react' })).toHaveAttribute('aria-selected', 'true')
})
```

That second one — *the controlled component does not change without the parent* — is the test that
proves you understand what controlled means.

**4. The stress case.** Whatever this component's version of "the hard part" is:

- async → a stale response cannot overwrite a newer one
- a list → empty renders an empty state, not nothing
- a timer → it does not fire after unmount
- a form → invalid input doesn't submit

**5. Keyboard, if there is one.** One test, covering the main path.

```tsx
test('arrows move the highlight and Enter selects', async () => {
  const user = userEvent.setup()
  render(<Thing items={ITEMS} onSelect={onSelect} />)
  await user.click(screen.getByRole('combobox'))
  await user.keyboard('{ArrowDown}{ArrowDown}{Enter}')
  expect(onSelect).toHaveBeenCalledWith('redux', ITEMS[1])
})
```

### B. WHAT MAKES A TEST "QUALITY" RATHER THAN PRESENT

| Bad | Good | Why |
|---|---|---|
| `getByTestId('option-1')` | `getByRole('option', { name: 'redux' })` | Queries the way a user (and a screen reader) finds it. Roles are also free a11y evidence. |
| `expect(wrapper.state.open).toBe(true)` | `expect(screen.getByRole('listbox')).toBeVisible()` | Implementation vs behaviour. State can be renamed; behaviour can't. |
| `fireEvent.click` | `await user.click` | `user-event` fires the real sequence — pointerdown, mousedown, focus, click. Half the bugs live between those. |
| One test asserting nine things | One behaviour per test | A failure names itself. |
| `expect(fn).toHaveBeenCalled()` | `expect(fn).toHaveBeenCalledWith(…)` | Proves the payload, which is the API. |
| Snapshot of the whole tree | Explicit assertions | A snapshot passes forever and then fails for no reason anyone reads. |
| `await new Promise(r => setTimeout(r, 500))` | `await waitFor(() => …)` / `findBy*` | Deterministic, and doesn't cost half a second each. |

**The one-sentence version to say out loud in the pad:** *"I'm testing behaviour through the roles
a user would use, so these tests survive a refactor and double as accessibility checks."*

### C. THE IDIOMS TO HAVE IN YOUR FINGERS

No-AI means these have to be typed from memory. Drill them until they're automatic.

```tsx
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

const user = userEvent.setup()

// Queries: getBy → must exist now · queryBy → may not exist (the ONLY one for absence)
//          findBy → will exist soon (async, returns a promise — always await)
screen.getByRole('button', { name: /save/i })
expect(screen.queryByRole('alert')).not.toBeInTheDocument()
await screen.findByRole('option', { name: 'redux' })

// Scope a query to a subtree
within(screen.getByRole('listbox')).getAllByRole('option')

// Waiting for a consequence rather than a timer
await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1))

// Common jest-dom matchers
expect(el).toBeVisible()
expect(el).toHaveAttribute('aria-expanded', 'true')
expect(el).toHaveFocus()
expect(el).toHaveValue('re')
expect(el).toBeDisabled()

// Keyboard
await user.keyboard('{ArrowDown}{Enter}{Escape}')
await user.tab()

// A controllable async source — the single most useful test helper there is
const pending = []
const fetchOptions = vi.fn(() => new Promise((resolve) => pending.push(resolve)))
// …then resolve them in whatever order the test needs, including backwards
```

That last one is how you test a race in four lines, and it's worth having memorised: hand-resolving
promises out of order is the only way to prove a generation guard works.

### D. TIMERS AND ASYNC — THE TRAP THAT COSTS TEN MINUTES

`user-event` v14 only knows how to advance **Jest's** fake timers. Combining `vi.useFakeTimers()`
with `await user.type(...)` deadlocks until the test times out. Discovering that live in a pad,
with an interviewer watching, is a bad ten minutes.

**The reliable pattern:** real timers, tiny durations, `waitFor` for the consequence.

```tsx
render(<Toast message="Saved" duration={30} onDismiss={onDismiss} />)
await waitFor(() => expect(onDismiss).toHaveBeenCalledWith('timeout'))
```

If you genuinely need fake timers (asserting something does *not* happen for a long interval),
configure the advance function:

```tsx
vi.useFakeTimers()
const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
```

Say the reason out loud when you do it — *"I'm using a 30 ms duration with real timers because
fake timers and user-event don't compose cleanly"* — because a shortcut with a stated reason reads
as expertise and a shortcut without one reads as luck.

### E. WHAT NOT TO TEST

Time is the constraint, so spend it where the signal is:

- **Not CSS.** They said styling isn't graded; asserting a class name is worse than not testing.
- **Not third-party behaviour.** You are not testing React.
- **Not every permutation.** One representative case per behaviour.
- **Not internal function names.** Test through the public surface only.
- **Not the type system.** If the pad is TS, the compiler already did that.

### F. IF THE PAD CAN'T RUN TESTS

Write them anyway, and say so:

> *"I can't execute these here, but this is the suite I'd ship — and writing it now is partly how I
> check my own API, because a component that's awkward to test is usually a component with an
> awkward interface."*

That last clause is true and it is exactly the connection between the two graded axes.

### G. THE DRILL

Test quality is the axis with the least practice behind it, so it gets two dedicated reps:
`cursor-05-write-the-tests` (a finished `Toast`, ten behaviours, thirty minutes) and
`cursor-10-write-the-tests-ii` (a finished async hook). In both, the component is done and **the
suite is the entire deliverable**. Run them on D-9 back to back, then diff against the reference
suites and count what you missed — the misses are the list to reread the night before.

## 09 — The drills, and how to run them

All of these live in `uie-practice`. Run them with `npm run dev` and the route matching the slug;
the spec suite is `npx vitest run src/exercises/<slug>`.

### A. THE PROTOCOL

Non-negotiable, or the reps measure the wrong thing:

1. **AI off.** Not "I won't accept suggestions." Disabled. The drill harness enforces the other
   half by hiding the reference until the timer expires.
2. **Timer visible, started before you read the prompt.**
3. **Narrate out loud, alone, the whole time.** This is the part that feels stupid and matters
   most — the round grades reasoning you have to externalise, and doing it under time pressure is
   a separate skill from having the thought.
4. **Stop when the timer stops.** Then write the §06 E closing summary out loud, as though the
   interviewer were there.
5. **Grade with §06 F before looking at anything.**
6. **Only then** open the reference and diff.

For the smaller kit pieces — a CSS primitive, a utility function, a component skeleton — the mode is
different: don't re-solve them, **retype them cold on a stopwatch**. Type from memory, diff, note
only what you got wrong, redo tomorrow. Two clean reps in a row and it's kitted; stop drilling it.

**Rep targets:** CSS primitive ≤ 60s · utility function ≤ 90s · component skeleton ≤ 5 min.

The point of the timed retype is that layout and boilerplate stop consuming working memory. That is
the specific capacity AI autocomplete has been renting from you, and it's the capacity the round
needs for reasoning out loud.

### B. THE ELEVEN

| Slug | Min | What it drills | Why it's on the list |
|---|---:|---|---|
| `cursor-01-streaming-message` | 45 | Chunked arrival, coalesced paint, stop/cancel, cleanup | The client-side streaming pattern from §04 D, in code |
| `cursor-02-typeahead` | 50 | Debounce, abort, generation guard, keyboard | The single most likely component prompt shape |
| `cursor-03-diff-view` | 40 | Rendering a computed structure, keys, memo boundaries | Cursor-shaped, and pure render logic |
| `cursor-04-file-tree` | 45 | Recursion, expand/collapse, roving tabindex | Tests whether your keyboard model generalises |
| `cursor-05-write-the-tests` | 30 | **Test quality**, against a finished `Toast` | The graded axis, isolated |
| `cursor-06-command-palette` | 50 | ⌘K: filter, keyboard, portal, recents, focus restore | **Unseen.** Forces derivation, not recall |
| `cursor-07-undo-redo` | 45 | A `useHistory` hook — past/present/future, coalescing | **Pure API design**, and trivially testable |
| `cursor-08-chip-multiselect` | 50 | Two focus models in one widget; Backspace-removes-last | The §02 B worked example, now runnable |
| `cursor-09-inline-diff-review` | 45 | Accept/reject hunks, staged vs committed, keyboard | Closest thing to real Cursor surface |
| `cursor-10-write-the-tests-ii` | 30 | **Test quality** against an async hook — races, cleanup | Second rep on the thinnest axis |
| `combobox-practice-8-13` | 45 | The full combobox, cold, from the given API | Already in progress; finish it AI-off |

### C. THE THREE-MINI-BUILD DAY (D-4)

Pure fluency, not design. Three components, twenty-five minutes each, AI off, no reference:

1. **Star rating** — hover vs selected state, keyboard, `onChange`
2. **Progress bar** — determinate/indeterminate, `role="progressbar"` and its three attributes
3. **Toast queue** — add, auto-dismiss, dismiss early, max visible

You have built all three before. That is the point: this day measures **typing and recall speed on
things you already know**, which is the specific thing AI autocomplete has been doing for you.
Target is finishing each inside the box with tests. If you can't, the gap is fluency and it's fixable
with exactly this drill.

### D. THE TWO FULL MOCKS (D-7, D-3)

Run them at **10:00–12:00**, on the real clock, back to back, no break between the hours. The
fatigue transition from a design hour straight into a coding hour is real and worth having felt
once before the 28th.

**Mock #1 (Fri 8/21).** Design: pick a §05 problem you have *not* yet done. Coding: `cursor-09`, or
any drill you haven't touched. Grade both with §03 F and §06 F. Whatever scores lowest is
Saturday's entire agenda.

**Mock #2 (Tue 8/25).** Design: something not in this guide at all — *"design a real-time
dashboard for agent runs across an org"*, *"design a collaborative spreadsheet"*, *"design an
in-editor debugger UI"*. Coding: an unseen prompt. This mock is testing the method, not the
material.

If you can get a person for either one, do it — an interviewer who interrupts changes the round in
ways a timer can't simulate. Failing that, record yourself and watch the first ten minutes back.
That is where the openings live, and openings are the part you can most reliably fix.

## 10 — Day-of runbook

### A. THE NIGHT BEFORE (Thu 8/27)

- **Excalidraw open in a tab, with a blank board already split into two labelled columns**,
  *Client* and *Server*, and a vertical line between them. Save it as a scratch file you duplicate.
  Starting from that template costs nothing and guarantees the balanced-columns habit under nerves.
- **A clean browser profile or window.** Close everything with a notification. The interviewer sees
  your screen.
- **Test the hardware.** Mic, camera, screen share, and specifically *screen sharing the Excalidraw
  tab* — a failed share at 10:01 costs you the opening.
- **Disable AI in whatever editor is open.** Even if you'll be in CoderPad, a visible autocomplete
  in a shared screen is a bad look and you don't want the muscle memory.
- **Re-read only §03 B (the opening), §06 A–B (the coding clock), and §07 A (the six questions).**
  Nothing new. Reading new material the night before does not help and costs sleep.
- Sleep. The round rewards fluency and fluency is the first thing sleep debt takes.

### B. THE MORNING

- Eat. It is a two-hour block with no break.
- Twenty minutes before: one warm-up rep, low stakes — type a `useState` + `useEffect` +
  `AbortController` skeleton from blank, out loud. Not to learn anything; to get the fingers and
  the voice already moving so minute one isn't cold.
- Have on a second screen or on paper: the §03 A clock, the §03 F rubric headings, the §04 B
  seven-layer list, the §04 J latency anchors, and the §06 A clock. Nothing else. If you need to
  look something up mid-round, looking it up is allowed and normal — say *"one second, checking"*.
- Water within reach.

### C. 10:00 — SYSTEMS DESIGN

| | |
|---|---|
| **0:00** | *"Let me make sure I'm building the right thing before I draw anything."* Then the four categories — §03 B. |
| **0:08** | Restate the core flow and get it confirmed. Write assumptions in a corner. |
| **0:08** | **Say a latency budget or a scale number, unprompted.** This is the single highest-leverage sentence in the hour. |
| **0:12** | Contract before boxes: two or three endpoints/events with shapes. |
| **0:12** | Both columns. Left column walks the seven layers (§04 B). |
| **0:36** | **Hard stop on breadth.** Pick the hardest thing and go deep. If they haven't steered you, choose it yourself and say why. |
| **0:52** | Failure pass — §04 I. Ninety seconds, out loud. |
| **0:58** | Close: biggest risk · what I'd build first · what I'd want to prototype. |

Every decision gets the three-part form: **choice · reason · switching condition.** If you catch
yourself saying "it depends," finish the sentence with "…so I'm choosing X, because in this case
___."

### D. 11:00 — CODING

| | |
|---|---|
| **0:00** | *"Can this pad run tests, and if so what's the runner?"* Then restate the problem in one sentence. |
| **0:02** | **The prop signature, typed and spoken, before the body.** Ask controlled-vs-uncontrolled. |
| **0:07** | Static render on screen with hardcoded data. Feedback loop established. |
| **0:12** | Core behaviour. Happy path first, then correctness, then async guards, then keyboard. |
| **0:35** | **Checkpoint out loud:** where I am, what's left, what I'm cutting, and why tests come next. |
| **0:38** | **Tests. Non-negotiable.** §08 A, in order. Run them if you can. |
| **0:50** | Extensions only if genuinely done. Otherwise, more tests. |
| **0:55** | Closing summary — §06 E. Name the cuts in priority order. |

### E. THE FIVE THINGS THAT MOST CHANGE THE OUTCOME

If everything else falls out of your head under pressure, these five are the ones that carry:

1. **Don't draw, and don't type, for the first several minutes.** Both rounds are won in the
   requirements phase and lost by starting early.
2. **Say a number.** A latency budget, a request rate, a data size. One number, spoken unprompted,
   changes how the whole hour reads.
3. **Fill both columns.** The invitation told you the client has real complexity. Most candidates
   still draw a server diagram with a box labelled "React app."
4. **Ship the prop signature before the body**, out loud.
5. **Stop at 38 minutes and write tests**, whatever state the component is in.

### F. AFTERWARDS

Within an hour, while it's fresh, write down: the two prompts verbatim, every question they asked,
every place you hesitated, and everything you'd say differently. That document is worth more than
this guide for the next loop, and memory for interview specifics decays within a day.

Good luck. The preparation is real — twenty-eight components built, a client-architecture chapter
that most candidates have never seen written down, and two full mocks on the real clock. Walk in
and do the thing you have practised: ask first, decide out loud, and leave time for tests.
