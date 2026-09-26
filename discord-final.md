# Discord — Final Round, 48 Hours

> **Packet received Saturday 2026-09-26. Final is Monday 2026-09-28, five interviews in one day.**
> This page is the plan for the two days between. It supersedes the "dates not yet recorded" notes
> in [Discord — Final Round](#/learn/discord-screen) §00 and [Final Loops](#/learn/final-loops)
> §03, both of which were written before the packet existed. Where an older page assumed a format,
> the recruiter's words below win.

The library already carries the design archetype, the server-side coding reference, and the data
structure reference this loop needs. What it did not have until now is anything for the
**web-app build**, the **Principles** round, or the **Project Retro**. Those three get the most
words here; the other two get a schedule and a pointer.

## 00 — The packet, read against the library

The recruiter's text, round by round, then where the material is and what this page adds. Each
"signal" line is quoted because it is the rubric the interviewer is holding.

| Round | Recruiter's words | Existing page | This page adds |
|---|---|---|---|
| **Systems Design** | "a standard technical architecture question … a large, scalable system, and the tradeoffs … should be something that could be built … online whiteboarding tool (Excalidraw)" | [System design round card](#/learn/system-design-card), [Design Discord](#/designs/discord), [Slack](#/designs/messaging), [Interview mechanics](#/designs/interview-mechanics) | Excalidraw drawing order, two scored reps (§02) |
| **Coding 1 — web app** | "build a web application … scaffold a simple project and come … with it already open in your IDE and running … whatever UI framework … LLMs are not allowed … disable LLM autocompletion" | [Component round](#/learn/component-round), [UIE Components](#/learn/uie-components), [Client-side system design](#/learn/client-side-system-design), katas in `uie-practice` | The scaffold spec, the LLM-off checklist, likely shapes, a 60-minute procedure and rubric (§03) |
| **Principles** | "decision making, problem solving, or conflict resolution … aligned with our Principles … strive to innovate and challenge norms … hit the ground running not only in their skillsets but within our culture" | none | The seven principles with their own key phrases, a six-slot story scaffold (§05) |
| **Project Retro** | "one or more projects … retrospective fashion … a recent project that you played the role of leader … define ownership · measure success and relate it to the business · break down and structure · collaborate with stakeholders · assess risk · learn from experiences · overcome adversity or conflict, both technologically and relationally" | [Final Loops](#/learn/final-loops) §05 | A fill-in scaffold keyed to those seven bullets, a rehearsal procedure and rubric (§06) |
| **Coding 2 — DSA** | "identifying a data structure and creating a coded solution using the data structure … in your own IDE … how you code, how clean the code is, how to debug and how you collaborate" | [OpenAI Coding — Top 20](#/learn/openai-coding), [Coding patterns](#/learn/coding-patterns) | A candidate map with Discord-shaped framings, a 45-minute procedure and rubric (§04) |

Two things the packet says that older pages did not know:

- **Coding 1 is a browser build, not a TCP server.** The August screen was a line server over
  sockets; `discord-screen` §§01–05 are that screen. They passed. Do not reread them this weekend.
- **Coding 2 is explicitly data-structure-first.** `discord-screen` §00 says Discord "does not ask
  you to build red-black trees", which is still true — but the DSA round is real, and the signal
  named is *identifying* the structure, then code quality, debugging, and collaboration.

## 01 — Two days and a morning, hour by hour

About five working hours each day, with a hard stop. Every block below is either a **rep** (timed,
scored, a rubric on this page or the card) or a **fill** (writing on paper about your own work).
There is no reading block longer than twenty minutes, because reading is what this library has too
much of already.

### A. SATURDAY 9/26

| Block | Minutes | What | Score against |
|---|---|---|---|
| 1 | 45 + 20 | **Design rep 1.** Prompt: *design Discord* — guild fanout, sessions, reconnect. Draw in Excalidraw, timed, card open on a second monitor. Then 20 minutes: score, and reread only the §§ of [Design Discord](#/designs/discord) that the lowest-scoring criteria point at. | [Card rubric](#/learn/system-design-card) |
| 2 | 15 | **Scaffold rep.** Blank directory → Vite React TS running in the browser with the three-pane stub and the fake API from §03 A. Timed. Then `git commit` it so Monday's reset is one command. | §03 A checklist |
| 3 | 60 + 15 | **Web-app build 1.** Shape 1 from §03 C (channel list + message list + composer, optimistic send with failure). Then score. | §03 E |
| 4 | 60 | **Retro fill.** §06 B on paper, one project, all seven bullets. Nothing rehearsed yet, just written. | — |
| 5 | 45 | **Principles fill.** §05 B, six slots, each a few lines. Where a slot has no story, write "none" and move on — that is information. | — |

### B. SUNDAY 9/27

| Block | Minutes | What | Score against |
|---|---|---|---|
| 1 | 45 + 15 | **DSA rep.** One prompt from §04 B, cold, IDE only, run with a `main()` block. | §04 E |
| 2 | 75 | **Web-app build 2.** A different shape from §03 C, and at minute 45 add one requirement from §03 D's extension list without a rewrite. | §03 E |
| 3 | 45 + 15 | **Design rep 2.** If Saturday scored below 14: *design Discord* again, same prompt. Otherwise: *design Slack* — the same archetype with the read side pushed harder — using [Slack](#/designs/messaging) §§7–11 for the post-mortem. | Card rubric |
| 4 | 30 | **Retro rehearsal.** §06 D aloud, timed: two-minute overview, then the ten-minute technical pass. Score. | §06 E |
| 5 | 30 | **Principles aloud.** Each of the six stories once, ninety seconds, out loud, then stop. Note which ran long. | §05 C |
| 6 | 15 | **Excalidraw rep.** §02 A: three boxes, an arrow, a label, a state machine, in under three minutes, twice. | — |

### C. MONDAY 9/28, T-60

The §07 checklist. Nothing new is learned on Monday morning.

### D. WHAT NOT TO DO THIS WEEKEND

- **No new design pages.** Both September mocks scored about 6/20 with every component named
  correctly. The gap is allocation and closure, and a new page is more vocabulary.
- **No rebuilding the line server.** The screen passed. The final's coding rounds are a browser
  app and a data structure.
- **No component tour.** `uie-components` has fourteen components; the round needs one layout and
  three interactions. Run the five katas in §03 F cold if you want reps, not the chapter.
- **No reading a full design page end to end.** Read the §§ that a rubric row sent you to.

## 02 — Systems design on a whiteboard tool

The card carries the process; this section is only what changes when the canvas is Excalidraw
instead of a shared doc.

### A. EXCALIDRAW IN TEN MINUTES

Open [excalidraw.com](https://excalidraw.com). No account. Five tools cover the whole round:

| Key | Tool | Use it for |
|---|---|---|
| `R` | Rectangle | Every service, store, and client |
| `A` | Arrow | Every flow. Click source, click target; arrows stay attached when you drag a box |
| `T` | Text | Labels on arrows, the NFR list, the checklist |
| `L` | Line | The dashed boundary around a trust or process boundary |
| `1`–`5` | Selection / hand | Get out of a tool. `Esc` also works |

Three habits that keep the board legible under time pressure:

- **`Alt`-drag duplicates.** Draw one box with the style you want, then duplicate it for every
  other service. `Ctrl/Cmd-D` also duplicates in place.
- **Group before moving.** `Ctrl/Cmd-G` on a box and its label, so a drag moves both.
- **One colour for hot paths.** Pick the hot-path arrows and set their stroke red with the style
  panel. The interviewer sees at a glance where you think the load is, which is rubric row 2.

The rep, Sunday block 6: from a blank canvas, draw three boxes, one arrow between each, a label on
each arrow, and a four-state state machine in a corner. Under three minutes, twice. That is the
whole mechanical skill; the rest is the card.

### B. DRAW ORDER THAT MATCHES THE CARD

The card's rule is *state machine first, then the data flow, then boxes*. On a canvas that becomes
a literal placement:

1. **Top-left, minute 3:** the NFR list as a text block. It stays visible for the minute-35 audit.
2. **Top-right, minute 6:** the per-entity state machine. For Discord: a message's states
   (accepted → dispatched → acked) and a session's (connected → resuming → gone).
3. **Centre, minutes 8–18:** the data flow as boxes and arrows, entities derived from the arrows.
   The API is a text list beside the flow, not a box, and on an infra-shaped prompt it can wait.
4. **Bottom, minute 20 onward:** the deep-dive boxes get drawn *around* the hot arrow, not in a
   fresh area. Redrawing costs minutes.

**The API box last** is a lesson from the 9/13 mock, where forty minutes went to requirements and
entities before a single flow was drawn. On a canvas the temptation is worse, because a neat
entity table looks like progress.

### C. THE LIKELY ARCHETYPE, AND TWO NEIGHBOURS

The packet says "a standard technical architecture question". At Discord the standard question is
the company's own product, and the library's page for it is [Design Discord](#/designs/discord):
one write becomes fifty thousand socket writes, sessions survive transport loss, presence is
replaceable state. Read §6 (flows), §7 (recovery), §8 (large-guild fanout) and §13 (traps) after
Saturday's rep, not before.

Two neighbours the phrasing "large, scalable system" also admits, each with a page:

- **[Distributed rate limiter](#/designs/rate-limiter)** — small surface, entirely about hot keys
  and the cost of strict global limits. Twenty minutes with §§6–9 on Sunday if design rep 2 goes
  well.
- **[Feed](#/designs/feed)** — fanout on write versus read, the same tension as a hot guild. Skip
  unless the recruiter's "large, scalable" turns out to mean a consumer read path.

The rule from the card still holds: **the prompt you get is the prompt you run**, and the first
ten minutes are for finding which archetype it is, not for assuming.

### D. THE TWO REPS

Saturday: *design Discord*. Sunday: the same again if Saturday scored below 14, otherwise *design
Slack*. Score both on the [card rubric](#/learn/system-design-card) exactly as written — it is
twenty points, and 14 is the re-run line. Do not invent a Discord-specific rubric; the mocks
established that the misses are in the process rows, not the domain.

## 03 — Coding Exercise 1: the web app

> "This interview tests your programming ability by asking you to build a web application. Before
> the interview, scaffold a simple project and come to the interview with it already open in your
> IDE and running in your browser."

The scaffold is homework, and it is the one part of the round you control completely. Everything
below is React + Vite + TypeScript, which is what every kata in `uie-practice` already uses.

### A. THE SCAFFOLD SPEC

Fifteen minutes on Saturday, from a blank directory, timed. What "done" is:

```bash
cd ~/interviews && npm create vite@latest discord-final -- --template react-ts
cd discord-final && npm install && npm run dev
```

Then, before the first commit:

- **`src/App.tsx`** is a three-pane layout stub — a sidebar, a main column, a composer strip —
  with fake data rendering in each pane. CSS grid, three lines, in `App.css`. No component
  library.
- **`src/api.ts`** is an in-memory fake with latency and a failure switch. The key behind
  §03 F has one. Every async interaction in the round goes through it, so the "what if the send
  fails" follow-up is a one-line flip, not a rewrite.
- **`src/types.ts`** holds `Channel`, `Message`, `User`. Three interfaces, ten lines.
- **`README.md`** has the one-line reset: `git checkout -- . && git clean -fd`.
- **`git init && git add -A && git commit -m scaffold`.** Monday starts from this commit.

What *not* to pre-build: state management, routing, a test runner, a design system. The round
scores what you build in front of them; a scaffold that already does the work reads as evasion,
and a scaffold with a stack to explain wastes the first five minutes.

Have open on Monday: the dev server in a browser tab, the IDE on `App.tsx`, and a terminal. Nothing
else. The transcript walkthrough and the katas are closed.

### B. THE LLM-OFF CHECKLIST

The packet says it twice. Verify, do not assume:

- **VS Code:** `"github.copilot.enable": { "*": false }` in settings, *and* disable the Copilot and
  Copilot Chat extensions for the workspace. `"editor.inlineSuggest.enabled": false` catches any
  other ghost-text extension.
- **Cursor:** switch to plain VS Code for the day. Cursor Tab can be turned off, but explaining
  that to an interviewer is a worse use of a minute than not needing to.
- **Any AI extension** (Codeium, Tabnine, Supermaven, Continue): disabled for the workspace, not
  just the setting.
- **The test:** type `// fetch the messages for` and wait two seconds. If anything grey appears,
  it is not off.

Do this Saturday, in the scaffold commit's workspace, so Monday's IDE is already the verified one.

### C. PROBABLE SHAPES

Discord does not publish this round, and there is no candidate report in this library for it. What
follows is inference from the company's product and the packet's phrasing, not a claim about the
prompt. Five shapes cover the plausible range; every one of them is built from the same six
mechanics.

| Shape | The build | The follow-up that reveals the mechanics |
|---|---|---|
| 1. **Channels and messages** | Channel list, message list for the selected channel, composer | Optimistic send, then the send fails |
| 2. **Unread state** | Messages arrive on a timer into channels you are not viewing; show counts | Mark-read on view, and the count must not flicker when you switch back |
| 3. **Members and presence** | User list with online/idle/offline; presence updates on a timer | Sort by status then name, and stable rows while updating |
| 4. **Search or filter** | A search box over messages or members, results as you type | Debounce, and a stale response must not overwrite a newer one |
| 5. **Threads or replies** | A message can open a thread pane; replies post into it | Reply count on the parent updates; closing the pane preserves the draft |

The six mechanics every shape shares, and where the library covers each:

1. **Lists with stable keys** and no index keys — [React & CSS](#/learn/react-css) §02.
2. **A controlled composer** with Enter to send, Shift-Enter for a newline, focus returned after
   send — `kata-01`, `kata-02`, `kata-04`.
3. **Derived state computed, not stored** — unread counts, filtered lists, sorted members are
   `useMemo` over source state, never a second `useState` — `kata-07`.
4. **A reducer for the message list** — append, replace-by-temp-id on ack, mark-failed — `kata-08`.
5. **Scroll to bottom on new message, but not while the reader has scrolled up** — `kata-09`.
6. **Async with a stale-response guard** — an `AbortController` or a request counter, so a slower
   earlier response cannot land after a newer one — `kata-13`, `kata-14`.

Nothing here is Discord-specific. That is the point: the shapes differ in nouns, the mechanics do
not, and the six are what the katas drill.

### D. THE SIXTY-MINUTE PROCEDURE

The round is probably longer than sixty minutes; the procedure is sixty so that the follow-ups
have room.

| Minutes | Do | Say |
|---|---|---|
| 0–5 | Restate the build. Draw the component tree in a comment at the top of `App.tsx`: three or four components, the state each owns. | "I'll keep state at the top and pass down; if a piece only one component needs, it moves there." |
| 5–15 | Static layout with fake data. Every pane renders something. | "Layout first so we can see it; behaviour next." |
| 15–35 | The interactions: select a channel, type, send. Reducer in, keys stable. | Narrate each state decision in one sentence. |
| 35–50 | Async through `api.ts`: loading state, the optimistic path, then flip the failure switch and handle it. | "Here's what the user sees if this fails." Show it failing. |
| 50–60 | Polish what is visible: focus after send, empty state, one keyboard path. Then say what you would do next. | Name two trade-offs you took and the alternative for each. |

**Extension list for Sunday's build 2**, add one at minute 45 without a rewrite: a typing
indicator on a timer; an edit-in-place on your own messages; a "jump to unread" divider; a member
filter box. The rubric row that matters is whether the first forty-five minutes' structure
survived it.

### E. SELF-GRADE RUBRIC

Score 0–2 per row after each build. **0** absent or wrong; **1** present but you would not want the
interviewer to look closely; **2** present and you narrated it.

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | Works end to end | A pane is dead | Works with a console error | Works, console clean |
| 2 | Keys | Index keys | Stable keys, one list re-mounts anyway | Stable ids everywhere, temp ids replaced on ack |
| 3 | Derived state | Derived values stored in `useState` | Mixed | All derived values computed from source state |
| 4 | Stale responses | A late response can overwrite | Guarded in one place | Guarded, and demonstrated by slowing the fake |
| 5 | Loading and failure | Neither shown | One shown | Both shown, failure recoverable (retry or revert) |
| 6 | Keyboard | Mouse only | Enter sends | Enter sends, Shift-Enter newline, focus returns |
| 7 | Narration | Silent typing | Decisions explained when asked | Each state decision said before it was typed |
| 8 | Extension | Rewrote to add the feature | Added with some churn | Added inside the existing structure |
| 9 | Dead code | Unused state, commented blocks | Some | None; the file reads top to bottom |
| 10 | Time | Ran out before async | Async in, no polish | Finished with a next-step list |

**Below 14, Sunday's build 2 is the same shape again**, not a new one — the misses are in the
mechanics, and a new shape hides them under new nouns. At 14 or above, pick a different shape.

### F. THE KATAS, COLD

Five in `~/projects/uie-practice`, each a stub that fails until you write it:

```bash
cd ~/projects/uie-practice
npx vitest run src/exercises/katas/kata-08-message-reducer      # append, ack, fail
npx vitest run src/exercises/katas/kata-09-scroll-to-bottom     # pinned unless scrolled up
npx vitest run src/exercises/katas/kata-14-latest-wins          # stale-response guard
npx vitest run src/exercises/katas/kata-18-chat-layout          # the three-pane grid
npx vitest run src/exercises/openai/openai-02-composer          # Enter / Shift-Enter / focus
DRILL_SOLUTIONS=1 npx vitest run src/exercises/katas/kata-08-message-reducer   # the reference
```

They are optional on this schedule. Run one only where a rubric row scored 0.

<details>
<summary><strong>Worked key — the fake API and the message reducer, as reference code</strong></summary>

`src/api.ts`. Latency and failure are switches so the follow-up is a flip:

```ts
import type { Channel, Message } from './types'

export const config = { latencyMs: 300, failSends: false }

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

const channels: Channel[] = [
  { id: 'c1', name: 'general' },
  { id: 'c2', name: 'random' },
  { id: 'c3', name: 'engineering' },
]

const messages = new Map<string, Message[]>([
  ['c1', [{ id: 'm1', channelId: 'c1', author: 'sam', body: 'hello', sentAt: 1 }]],
  ['c2', []],
  ['c3', []],
])

let nextId = 100

export async function listChannels(): Promise<Channel[]> {
  await wait(config.latencyMs)
  return channels
}

export async function listMessages(channelId: string, signal?: AbortSignal): Promise<Message[]> {
  await wait(config.latencyMs)
  if (signal?.aborted) throw new DOMException('aborted', 'AbortError')
  return [...(messages.get(channelId) ?? [])]
}

export async function sendMessage(channelId: string, body: string): Promise<Message> {
  await wait(config.latencyMs)
  if (config.failSends) throw new Error('send failed')
  const m: Message = { id: `m${nextId++}`, channelId, author: 'me', body, sentAt: Date.now() }
  messages.get(channelId)!.push(m)
  return m
}
```

`src/messages.ts`. One reducer, three actions, and the temp id is the whole idea:

```ts
import type { Message } from './types'

export type Pending = Message & { status: 'sending' | 'failed' }
export type Row = Message | Pending

export type Action =
  | { type: 'loaded'; rows: Message[] }
  | { type: 'sending'; tempId: string; message: Message }
  | { type: 'sent'; tempId: string; message: Message }
  | { type: 'failed'; tempId: string }
  | { type: 'received'; message: Message }

export function reduce(rows: Row[], a: Action): Row[] {
  switch (a.type) {
    case 'loaded':
      return a.rows
    case 'sending':
      return [...rows, { ...a.message, id: a.tempId, status: 'sending' }]
    case 'sent':
      return rows.map((r) => (r.id === a.tempId ? a.message : r))
    case 'failed':
      return rows.map((r) => (r.id === a.tempId ? { ...r, status: 'failed' } as Pending : r))
    case 'received':
      return rows.some((r) => r.id === a.message.id) ? rows : [...rows, a.message]
  }
}
```

The send path in the component is then four lines: dispatch `sending` with a `crypto.randomUUID()`
temp id, `await sendMessage`, dispatch `sent` or `failed`. The `received` case's duplicate check is
what makes a retry safe, and it is the line to point at when the interviewer asks what happens if
the ack is lost.

</details>

## 04 — Coding Exercise 2: identify the data structure

> "You will work on identifying a data structure and creating a coded solution using the data
> structure … The signal we are looking for is to see how you code, how clean the code is, how to
> debug and how you collaborate with others."

Four signals, in the recruiter's order, and the first one is the choice of structure. So the
choice is made **out loud, with the alternative named**, before a line is typed. Then the code is
graded on cleanliness, then on how you find the bug they will ask you to find, then on whether the
hour felt like pairing.

### A. THE ROUND, DECODED

"Identifying a data structure" means the prompt describes an operation set — insert, look up,
evict, rank, expire — and the answer is which structure makes each operation cheap. The
interviewer wants to hear the candidates and the reason the others lost. A candidate who types
`Map` in the first minute and is right has still skipped the signal.

There is no algorithms chapter in the Discord screen guide because the screen had none. The
[OpenAI Coding — Top 20](#/learn/openai-coding) page has the worked implementations for every
structure below, in TypeScript, with contracts and corrections. Use it as the answer key after a
rep, not as reading before.

### B. THE CANDIDATE MAP

Discord-shaped framings, the structure, the alternative, and where the worked code is.

| Prompt shape | Structure | The alternative and why it loses | Worked |
|---|---|---|---|
| Per-user message rate limit, N per window | Sliding-window log or token bucket, `Map<userId, state>` | Fixed window: a burst straddles the boundary at 2N | [#6](#/learn/openai-coding) |
| Last N messages per channel, O(1) append and read | Ring buffer with a head index | Array `shift()` is O(n); a linked list is heavier than the ring | — (write it: ten lines) |
| `@mention` autocomplete over a member list | Sorted array + binary search on prefix, or a trie | The trie is right at millions; at thousands the sorted scan is simpler and you finish | [Coding patterns](#/learn/coding-patterns) binary search |
| Top-K most active channels | Min-heap of size K, or a count map + partial sort | Full sort is O(n log n) and the interviewer will ask | [#17](#/learn/openai-coding) |
| Guild metadata cache with eviction | LRU: `Map` with insertion order, delete-and-reinsert on touch | A doubly linked list + map is the textbook; JS `Map` keeps order, so say why that is enough | [#1](#/learn/openai-coding) |
| Merge overlapping voice-session intervals | Sort by start, sweep | Interval tree is overkill for a batch | [#16](#/learn/openai-coding) |
| Order tasks with dependencies (permissions, role inheritance) | Topological sort, Kahn's with in-degrees | DFS colouring works; Kahn's makes the cycle error explicit | [#14](#/learn/openai-coding) |
| Unread count per channel per user | `Map<channelId, lastReadId>` plus the channel's latest id | Storing a count is derived state that drifts | — (the design page, [Discord](#/designs/discord) §10, is the argument) |
| Message history with edits, "as of" a time | Time-versioned KV: `Map<key, [(t, v)]>` with binary search on `t` | Copy-on-edit is O(history) per read | [#5](#/learn/openai-coding) |

Nine rows. The first, fourth, fifth and last are the ones the Top 20 page treats as OpenAI's
"builds", which is where the overlap between the two loops pays off.

### C. THE FORTY-FIVE-MINUTE PROCEDURE

| Minutes | Do | Say |
|---|---|---|
| 0–5 | Restate. Write two concrete examples as comments, including one edge (empty, duplicate, at the limit). | "Let me check I have the operations right: …" |
| 5–10 | Name two candidate structures. Choose. Write the complexity of each operation under the chosen one. | "The alternative is X; it loses because Y." |
| 10–30 | Code it. Small functions, named for the operation. No premature generality. | One sentence per function before typing it. |
| 30–40 | Run it. A `main()` at the bottom that exercises the two examples and prints. `node file.ts` runs TypeScript directly on Node 23.6 and later. | "Running the edge case first, because it's where I'd expect to be wrong." |
| 40–45 | Complexity summary, and the follow-up they hint at (bigger N, concurrency, persistence). | Name what would change, not everything that could. |

### D. DEBUGGING AS A PERFORMANCE

The packet grades "how to debug", which means they will break it or ask a case that breaks it.
The procedure is the same as at work, said out loud:

1. **Read the failing case aloud** — the input, the expected, the actual.
2. **State a hypothesis before touching code.** "I think the window isn't sliding; the timestamps
   are compared with the wrong bound."
3. **One `console.log`** at the point the hypothesis names. Not three.
4. **Fix, re-run both examples,** and say which invariant the fix restores.

A candidate who fixes it silently in ten seconds scores lower on this row than one who takes ninety
and narrates. That is not a trick; it is the stated rubric.

### E. SELF-GRADE RUBRIC

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | Restated with examples | Started coding from the prompt | Restated, no examples | Two examples, one an edge, written down |
| 2 | Candidates named | One structure, no alternative | Alternative named | Alternative named with the operation that makes it lose |
| 3 | Complexity stated | Not stated | Stated for the main op | Stated per operation, correct |
| 4 | Code shape | One function | Split, some names vague | Small functions named for operations |
| 5 | Runs | Did not run | Ran once | Ran both examples, output checked aloud |
| 6 | Edge handled | Crashes | Handled silently | Handled and pointed out |
| 7 | Debug narration | Fixed silently | Explained after | Hypothesis before the log, one log |
| 8 | Follow-up | Not reached | Reached, vague | Reached, one concrete change named |
| 9 | Collaboration | Monologue or silence | Answered questions | Asked one clarifying question, took one hint on the first nudge |
| 10 | Time | Not running at 45 | Running, no follow-up | Done with five minutes spare |

Below 14, the same prompt again on Sunday evening in place of the Excalidraw rep. Row 9's "took
the hint on the first nudge" is the 9/13 mock's lesson moved to the coding room.

## 05 — Principles interview

> "Centered around decision making, problem solving, or conflict resolution, how they act on
> those thoughts, and how those thoughts align with Discord's Principles. Signal looking for:
> folks who are aligned with our Principles, who are willing to strive to innovate and challenge
> norms, and who can hit the ground running not only in their skillsets but within our culture."

Two signals beyond alignment: **challenge norms** and **hit the ground running**. Every story
should end on a decision you made, not a decision you attended.

### A. THE SEVEN PRINCIPLES, IN THEIR OWN WORDS

From [the post](https://discord.com/blog/the-seven-principles-of-working-at-discord), read
2026-09-26. The key phrase is the post's; use it once, in your words around it, not as a quote.

| # | Principle | What the post means by it | Key phrase |
|---|---|---|---|
| 1 | **Cultivate Belonging** | Start from trust; seek to understand before judging; find common ground with people unlike you | "assume good intent" |
| 2 | **Deliver for Customers** | Understand the people you serve deeply enough to invent for them; requirements come from users, not competitors | "from first principles" |
| 3 | **Surprise & Delight** | Care about small details in how people experience your work, external and internal | "the million little details" |
| 4 | **Debate, Decide, Commit** | Involve the stakeholders, use data, argue, decide, then commit fully whether or not you agreed | "transparency is our goal, not consensus" |
| 5 | **Progress Over Perfection** | Ship value now and iterate; incremental beats complete-later | "an 80/20 approach" |
| 6 | **Embrace the Brutal Facts** | Take calculated risks, read the data honestly, and stop what is not working | "don't be afraid to cut your losses" |
| 7 | **Strive for Excellence** | Do work you are proud of, keep learning, and raise the people around you | "reach their maximum potential" |

The two that map to the packet's extra signals: **challenge norms** is 4 and 6 together (argue with
data, kill the thing that is not working); **hit the ground running** is 5 (ship the 80% early).

### B. THE STORY SCAFFOLD — SIX SLOTS

Fill on Saturday, on paper, from your own work. Each slot is a frame with prompts; the frame is
deliberately short because the first answer should be ninety seconds and the follow-ups pull the
rest. **Where you have no story for a slot, write "none".** Two "none"s is fine. Do not invent.

Each slot, five lines:

- **Context** — one sentence: the team, the system, the moment.
- **The decision** — what was decided, and that *you* decided it or drove it.
- **What you did** — the two or three actions, in order.
- **Result** — a number if one exists; if not, the evidence you do have.
- **What you would change** — one sentence, honest.

| Slot | Principle | The prompt to fill it |
|---|---|---|
| 1 | Debate, Decide, Commit | A disagreement across teams or with a senior person. You argued, lost or won, and then what you did *after* the decision. |
| 2 | Embrace the Brutal Facts | A project or initiative you stopped, or an incident where the data said the plan was wrong. What told you, and how fast you acted. |
| 3 | Progress Over Perfection | A scope you cut to ship earlier. What was left out, what the early version taught, and whether the cut part ever shipped. |
| 4 | Strive for Excellence | Someone you raised: a mentee, a team whose bar you moved. What changed in their work, not in your feelings about it. |
| 5 | Deliver for Customers | A decision that came from understanding users directly rather than from a spec or a competitor. How you knew. |
| 6 | Cultivate Belonging | Trust that broke between people or teams, and what you did to repair it. Assuming good intent as an action, not a stance. |

Surprise & Delight has no slot because it rarely gets its own question; it shows up inside slot 3
or 5 as the detail you cared about that nobody asked for. If you have one, note it in the margin.

The packet's third theme, **problem solving**, is covered by the Retro; if the Principles
interviewer asks for it, use the Retro project's hardest technical turn as a ninety-second version.

### C. ANSWER SHAPE

- **Ninety seconds, then stop.** Context in one breath, the decision, two actions, the result.
  Then silence. The follow-ups are where the depth goes, and an interviewer who has to interrupt
  a five-minute answer has already scored it.
- **"I" for your decisions, "we" for the team's output.** Both, and clearly separated. A Staff
  answer names what the team did and what only you did.
- **End on the decision or the change**, not on a moral. "So now I do X" beats "so I learned the
  importance of communication".
- **Take the follow-up as asked.** If they ask what you would do differently, say the thing, not
  a defence of what you did.

Sunday block 5 is each story once, aloud, timed. The ones that run past two minutes have a
context paragraph that needs cutting, not a result that needs adding.

### D. WHY DISCORD

Answered from the engineering, not from affinity: [Discord — Final Round](#/learn/discord-screen)
§07 D has the answer and §07 B has the three paragraphs of primary-source material behind it.
Read those two subsections once on Sunday evening. Do not restate them here or memorise them; the
point is to have one specific, checkable thing to say.

## 06 — Project Retro

> "The interview will be held in a retrospective fashion, where we want to cover several
> different topics on a recent project that you played the role of leader."

The word is *retrospective*, and it changes the shape. A project walkthrough is chronological; a
retro is **what we set out to do → what actually happened → what we would change**, and the
interviewer steers through the packet's seven bullets inside that. Prepare the retro shape, and
let the seven bullets be pulled from it.

### A. THE FORMAT

Open with two minutes, unprompted, in the retro shape:

1. **What we set out to do** — the user problem, the constraint, the success measure as it was
   defined at the start.
2. **What happened** — the shape of the work, the one thing that went wrong, the result against
   the measure.
3. **What we would change** — one process change, one technical change.

Then stop. The interviewer has seven bullets to cover and will pick the order. Your job after the
opening is to have every bullet's answer ready and short.

Pick **one** project. The packet says "one or more" but seven bullets in an hour on one project is
already dense. Choose the one where you can say "I decided" most often, not the largest.

### B. THE FILL-IN SCAFFOLD

Saturday block 4, on paper, every bullet. The prompts under each are what the interviewer's
follow-ups will be.

**1. Ownership.** *Define ownership of a project.*
- What were you the owner of, in one sentence, and what were you explicitly *not* the owner of?
- Who else had a stake, and how was the boundary between you agreed — written, spoken, assumed?
- When did the boundary get tested, and what did you do?

**2. Success, and its link to the business.** *Measure success of a project and how you relate
that success to the business.*
- The metric as defined at the start. The number it was, and the number it became.
- The business thing that metric stands in for — revenue, retention, cost, risk — and how sure
  you were of the link.
- If there was no clean metric: what evidence did you use, and what would you instrument now?

**3. Breakdown and structure.** *Break down and structure a large, complex project.*
- The first cut: what were the three to five pieces, and what was the ordering rule?
- What could ship on its own, and what did shipping it early teach you?
- Which piece turned out to be wrongly sized, and how did you find out?

**4. Stakeholders.** *Collaborate with stakeholders.*
- Who needed to be aligned, and who merely needed to be informed?
- The stakeholder who disagreed, what they wanted, and what you did with it.
- The mechanism you used to keep them current — a doc, a cadence, a demo — and whether it held.

**5. Risk.** *Assess risk.*
- The risk you named up front that materialised. What you had prepared for it.
- The risk you named that did not materialise, and whether preparing for it was still right.
- The risk you did not see. This is the honest one; have it.

**6. Learning.** *Learn from experiences.*
- One thing you do differently on every project since. Concretely.
- One thing you believed at the start that the project disproved.

**7. Adversity and conflict, technical and relational.** *Overcome adversity or conflict, both
technologically and relationally.*
- The technical wall: what broke, what the options were, what you chose, why.
- The relational one: who, over what, and what you did in the room and after. Ending, not
  blame.

### C. ONE DIAGRAM

The systems interview is not the only place a whiteboard tool helps. Have one Excalidraw file
ready: the project's critical data path, five to eight boxes, with the **rejected alternative
drawn in grey beside it**. When the interviewer asks about breakdown or the technical wall, share
it. A candidate who can draw their own system in thirty seconds is making a claim about ownership
that words cannot.

Draw it on Saturday after the fill, ten minutes. Export as PNG as well, in case screen-sharing a
canvas is awkward.

### D. TWO-PASS REHEARSAL

Sunday block 4, aloud, timed, in this order:

1. **The two-minute opening** (§06 A). Stop at two minutes even if unfinished; that is the
   information.
2. **The ten-minute technical pass.** Assume the interviewer said "walk me through the hardest
   technical part": the diagram, the data path, the one rejected alternative, the one failure
   mode, and how the rollout made it safe to learn. Stop at ten.
3. **Seven follow-ups, cold.** Read each of §06 B's bullet titles aloud and answer in under a
   minute.

Then score.

### E. SELF-GRADE RUBRIC

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | Ownership stated | Hedged ("we sort of") | Stated | Stated with the boundary and who was on the other side of it |
| 2 | Metric has a number | No metric | Metric named | Before and after numbers, or the evidence used in their place |
| 3 | Business link | Not made | Asserted | Explained: what the metric stands in for and how sure you were |
| 4 | Rejected alternative | None | Named | Named with the reason it lost and what it would have cost |
| 5 | Risk that materialised | None | Named | Named with what was prepared and whether it worked |
| 6 | Risk that did not | Not considered | Named | Named with whether preparing was still right |
| 7 | Stakeholder disagreement | None | Described | Described with what you did and how it ended |
| 8 | "I" versus "we" | Blurred | Mostly separated | Clearly separated throughout |
| 9 | A lesson that changed behaviour | A moral | A lesson | A concrete change you have made since, with an example |
| 10 | Time | Opening over four minutes | Opening under three | Opening under two, technical pass under ten |

Below 14, rehearse again Sunday evening in place of the Principles block, and the first fix is
almost always the opening: too much context, too late to the decision.

## 07 — Monday: T-60 and the Outro

### A. THE CHECKLIST

Sixty minutes before the first interview:

- **Scaffold:** `cd ~/interviews/discord-final && git status` clean at the scaffold commit,
  `npm run dev` running, browser tab open on it, IDE open on `App.tsx`.
- **LLM off:** the §03 B test, once more, in the IDE you will use. Type a comment, wait, nothing
  grey.
- **Excalidraw:** one tab with a blank canvas, one with the retro diagram. Hand tool selected.
- **The card:** [System design round card](#/learn/system-design-card) read once, top to bottom,
  five minutes. It is the only reading on Monday.
- **The paper:** the six Principles slots and the seven Retro bullets, on the desk, out of camera.
- **The round order,** if the recruiter sent it. If not, ask the first interviewer.
- Water. A closed door. Notifications off on every device.

### B. QUESTIONS FOR THE INTERVIEWERS

[Discord — Final Round](#/learn/discord-screen) §07 C has four that still hold — the real version
of the exercise, the Elixir/Rust line, on-call for a service where every client holds a
connection, the first three months. Two more for the web-app and Principles rounds:

- *"The packet asks us to work without LLM tooling. How does the frontend team actually ship
  day to day — where has that changed the work, and where hasn't it?"*
- *"Progress over perfection is easy to say. What's a recent release where you shipped the 80%
  and what did the 20% turn out to be?"*

Ask about the work. Do not ask how you did.

### C. THE OUTRO

"Just a quick recap of your interviews with me." It is not scored, but it is remembered. Have one
sentence per round on what you would do differently, and nothing else — not what went well, not
a re-argument of a design point. Five sentences. Then thank them and ask about timeline.
