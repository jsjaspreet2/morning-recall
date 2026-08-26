# Discord Skill Challenge — Wed 8/26, 12:00–1:15 PT

> Seventy-five minutes, **your machine**, your language. You build a small server-side application
> that a `nc` client connects to, and the interviewer adds requirements in parts as each one works.
> Browser research allowed, questions to the interviewer encouraged, **no AI tools.** This guide is
> the seven-day plan, the round script, and the one chapter that decides the hour: the line server.

Companion to `Coding Patterns` (the general shape library) and `Cursor Screen` (the other company
hour, two days later, graded on entirely different axes). Neither covers what this round actually
is: **a networked line protocol dressed as a chat app, extended in parts, where the score is how
far you get and whether part 1 survived contact with part 2.**

**Three things this guide deliberately does not contain.** There is no algorithms chapter — Discord
says in print that trivia has no place in their interviews and that they do not ask you to build
red-black trees, and every credible report of this round is a running server, not a puzzle. There
is no React or component chapter — this is server-side, and `UIE Components` already holds that
material. And there is no full distributed-systems treatment of Discord itself; the "now scale it"
follow-up gets three minutes in the room, so it gets `§09` here, and `Design Discord` under Designs
holds the rest.

## 01 — The seventy-five minutes, and what is actually graded

### A. THE FORMAT

| | Wed 8/26, 12:00–1:15 PM PT |
|---|---|
| **Round** | The "Skill Challenge" — a coding exercise, and the only technical round on the invitation |
| **With** | One Discord engineer, positioned explicitly as someone you may ask questions of |
| **Tool** | **Your machine, your editor, your terminal**, shared over screen share. Not CoderPad |
| **Client** | `nc` on macOS — already installed. PuTTY in "Raw" mode is the Windows equivalent |
| **Language** | Yours: *"use a language that you feel comfortable with"* — **TypeScript on Node** for you, see `§08` |
| **Deliverable** | **A server-side application that runs**, extended in parts as you finish them |
| **Stated design** | Practical problem-solving · **elements you may be unfamiliar with** · you may need to read documentation · browser allowed · ask the interviewer |
| **Rules** | No AI tools, no Copilot, no AI browser extensions, no second device, no real-time coaching. Non-AI accessibility tools remain permitted |
| **Also** | **Seventy-five minutes, not sixty.** That extra quarter-hour is a whole additional part |

### B. THE INVITATION, READ LITERALLY

Five sentences carry information. Take each at face value — this invitation is unusually candid,
and every ambiguity in it resolves the same way.

**1. "You'll be expected to build a small server-side application."**

Not "solve a problem." Not "implement a function." **An application**, which means it starts, it
listens, it holds state across events, and it keeps running after the first thing goes wrong. The
unit of assessment is a process you can point a client at, not a function that returns a value.
This is the sentence that rules out preparing with algorithm practice.

**2. "Please have your development environment set up, and use a language that you feel comfortable
with."**

Your machine, your editor, your keybindings, your terminal. That is an advantage worth several
minutes and it only cashes out if you have actually rehearsed on the exact setup — see `§01 E`,
which is about the ninety seconds before you write the first line.

Note also what it licenses: **setting up your environment in advance is requested, not tolerated.**
A folder that already has a `package.json`, a verified run command, and three terminals arranged is
what "set up" means. **What it does not license is pre-written solution code.** The line is clean
and worth holding: stage the *environment*, never the *program*. Pre-typing a chat server and
pasting it is the one move that turns a strong round into a withdrawn offer, and `§08 B` gets you
the same speed honestly, by making the skeleton something your hands know.

**3. "This exercise will be a practical, problem-solving question with elements that you may be
unfamiliar with, so you may need to look into documentation to learn about new concepts."**

This is a warning, and it is specific. The unfamiliar element is **sockets** — the invitation says
so two paragraphs later by telling you which client to install. Discord is signalling that a
working knowledge of a TCP listener is not assumed and that reading the docs mid-round is expected
behaviour rather than a confession.

Two consequences. First, **reading documentation in front of the interviewer is a graded positive,
not a cost.** Discord's own rubric lists *"How effectively did you use your environment and
resources?"* as an axis. Narrate it: *"I want to check whether `write` returns a boolean here,
because if it does I get backpressure for free."* Second, and this is the leverage this whole guide
exists to capture: **the unfamiliar element stops being unfamiliar if you spend seven days on it.**
The candidate who has to learn `net` in the room and the candidate who has typed it forty times are
being scored on the same rubric.

**4. "You'll be allowed to use your browser to research and ask questions of the interviewer."**

Two permissions in one sentence, and the second is worth more. An interviewer you may ask is an
interviewer who holds the requirements — and in a multi-part problem, the requirements *are* the
score. `§03 B` is the opening that gets them talking early.

**5. "If you're using Mac, you will use `nc` which should already be installed."**

The single most informative line in the email, and the reason this guide can be specific. `nc` is a
raw TCP client with no framing, no handshake, and no protocol. Telling you to install it means the
thing you build **listens on a TCP port and speaks newline-delimited text**. There is no HTTP here,
no framework, no WebSocket upgrade. It also tells you how you will demonstrate the program: by
typing into a terminal, live, while someone watches.

### C. WHAT IS KNOWN ABOUT THE BAR, BY CONFIDENCE

Search results for "Discord interview" are heavily polluted — most hits are generated listicles
describing a HackerRank algorithm screen, which is a different round for a different org, and a
large fraction of the rest are about building Discord *bots*. Only these are load-bearing.

| Confidence | Claim | Source |
|---|---|---|
| **High** | The format in `§01 A`: 75 minutes, your machine, your language, `nc` as the client, browser allowed, interviewer answers questions, no AI. | The invitation — first-party |
| **High** | **The rubric is published.** Discord grades: *functionality* (*"Does the code compile & run properly, and does it fulfill the question's requirements?"*) · *understanding* (*"know if something is constant time, linear time, or worse"*) · *trade-offs* (*"Are you aware of any tradeoffs you made in writing it?"*) · *resource use* (*"How effectively did you use your environment and resources?"*) · **refactoring** (*"How did you approach refactoring your solution to consider the new requirements?"*) · *code quality* (*"Is the code well abstracted such that it could be tested?"*). | Discord's own "How to prepare for your Discord interview" post — first-party |
| **High** | *"We don't ask you to build self-balancing red-black trees… Trivia has no place in our interviews."* Problems are *"based upon real work we've done."* | Same post — first-party |
| **High** | The exercise is a **TCP chat server** driven over telnet or netcat: multiple clients connect, messages go between them, and the code has to actually run. Reported consistently through 2025 and 2026. | Glassdoor's verbatim question entry, plus four independent aggregators |
| **High** | **Multi-part, revealed incrementally.** Part 2 is not described until part 1 works. One report puts a passing solution at roughly 130 lines in 75 minutes. | Candidate reports, several naming "Part 1" and "Part 2" explicitly |
| **Medium** | **Part 1 is one global room:** the client sends a name on its first line, subsequent lines are messages, the server broadcasts to *other* clients, **a client must not receive its own message echoed back**, and a disconnect must not take the server or another client down. | Two independent write-ups of the same question agree line for line |
| **Medium** | **Part 2 is rooms and slash commands:** `/join <room>` creating on demand, `/who` answering only the asker, `/quit` closing cleanly, broadcast scoped to the room, and empty rooms cleaned up. | Same two sources |
| **Medium** | Third parts, when reached: **message history replayed on join** (a "last 10" is named), reconnect, **rate limiting** (a specific "30 messages per minute, drop the excess"), private messages. | Aggregated reports; the 30/min figure appears verbatim in one |
| **Medium** | Follow-ups are discussed, not coded: scaling past one process via a pub/sub backbone, handling a slow client without blocking the broadcast, graceful shutdown, line-length caps. | Reported evaluation notes |
| **Low** | Specific implementations reported: Python `asyncio` (twice), Go, Java. The language really is yours; nobody reports a preference being expressed. | Single reports each |
| **Ignore** | Every "35+ Discord interview questions" listicle, and anything describing a timed CoderPad or HackerRank algorithm assessment. Those describe a different pipeline and will send you to prepare sliding-window problems for a round that has none. | SEO content farms |

**The shape to internalise.** Every credible variant is the same program wearing different clothes:

> accept a connection → **frame a byte stream into lines** → parse a line into a command → mutate
> **one registry** of connected clients → write lines back to **some subset** of sockets.

Parts 2 and 3 only ever change *which subset* and *what a line means*. They never change the first
two steps. **That is the entire reason `§04` is the long chapter** — and it is also why the
refactoring axis on Discord's rubric is winnable in advance rather than in the room. You cannot
know what part 2 will be. You can absolutely build part 1 so that any of the reported part 2s is an
addition rather than a rewrite.

**Reasoned inference, flagged as such:** the exact prompt wording is not knowable, and treating the
"name on first line, then messages" protocol as certain is a mistake. Treat it as the most likely
single shape, and treat `§04` as the thing that holds regardless of which shape lands.

### D. THE NO-AI RULE, AND HOW TO TRAIN FOR IT

The invitation is unusually explicit — no tool, extension, application, real-time coaching service,
or secondary device. Take it completely straight and turn Copilot off at the settings level, not
the keybinding level, the night before. An accidental ghost-text completion appearing on a shared
screen is a conversation nobody wants to have mid-round.

The thing worth internalising is **what the rule actually removes**, because it is not knowledge.
You keep the browser, the Node docs, `man nc`, and an interviewer who will answer questions. What
you lose is the thing that finishes your line for you. Two skills atrophy first under Copilot and
both are load-bearing here:

- **Typing an API from blank.** `net.createServer((socket) => {})` and the four event names are
  three seconds with completion and forty seconds without, if you have not typed them recently.
  Forty seconds is fine once. It is not fine eleven times.
- **Writing the boring middle.** The buffer-and-split loop, the `try`/`finally` cleanup, the map
  deletion on `'close'`. These are exactly what autocomplete has been writing for you.

Every rep in `§11` is run with AI off. That is not a purity thing — an AI-assisted rep measures a
skill you will not have on the 26th, so it produces a number you cannot use.

### E. FROM AN EMPTY DIRECTORY TO A SERVER YOU CAN TALK TO

The `discord-drills` repo hands you a configured project — a `package.json`, a test runner, `tsx`
already installed. **The interview hands you an empty directory.** That gap is the one part of the
round with no partial credit: it either works in ninety seconds or it eats five minutes while
somebody watches you read an error message. So rehearse the part that looks too trivial to rehearse.

**The fact that removes the setup entirely: Node runs TypeScript directly.** Since Node 23.6 a `.ts`
file needs no flag, no `tsconfig.json`, no `tsx`, no `package.json` and no `npm install`. On 24.19.0
it is on by default and completely silent — nothing on stderr, no experimental warning. The whole of
"getting started" is two commands and one file, and **none of it touches the network.**

**Step 1 · the directory.**

```bash
mkdir -p ~/interviews/discord && cd ~/interviews/discord
```

**Empty means empty, and this is the one place it bites.** Node decides whether a file is ESM or
CommonJS from the nearest `package.json`, and only falls back to reading your syntax when there
isn't one. `npm init -y` writes `"type": "commonjs"` explicitly, which switches that fallback
**off** — so a directory you "just ran npm init in" rejects the `import` on line 1 with
`Cannot use import statement outside a module`, on a file that is otherwise perfect. Do not run
`npm init` in this directory. If something already did, `§01 E`'s troubleshooting table below has
the two one-line fixes.

**Step 2 · `server.ts`, typed from blank.** This is not throwaway scaffolding. It is the opening of
the skeleton in `§06 F`, and every part of the round is built by adding to it.

```ts
import net from 'node:net'

const PORT = 8080

const server = net.createServer((socket) => {
  console.log('connected')
  socket.setEncoding('utf8')                      // chunks arrive as strings, not Buffers
  socket.on('data', (chunk: string) => {
    console.log('recv:', JSON.stringify(chunk))   // stringify so you SEE the \n
    socket.write(`echo: ${chunk}`)
  })
  socket.on('close', () => console.log('disconnected'))
  socket.on('error', () => {})                    // an unlistened 'error' kills the process
})

server.listen(PORT, () => console.log(`listening on ${PORT}`))
```

**Step 3 · run it, and connect twice.** No build, no watcher, no npm script. Two clients from the
first minute, because one client cannot demonstrate a broadcast.

```bash
node server.ts          # pane 1
nc localhost 8080       # panes 2 and 3
```

**The checkpoint, before a single line of logic.** Forty seconds, and it converts every later bug
into a logic bug:

| Where | You do | You must see |
|---|---|---|
| Server | `node server.ts` | `listening on 8080` |
| Client A | connect | The server prints `connected` |
| Client A | type `hello`, Return | Client: `echo: hello` · server: `recv: "hello\n"` |
| Client A | `Ctrl-C` | The server prints `disconnected` **and keeps running** |

**`recv: "hello\n"` is the line that earns its keep.** The quotes and the escape make the whole of
`§04 C` visible: what arrived is a *chunk that happens to contain a newline*, not a line. Drive the
same server from `telnet` and it prints `recv: "hi\r\n"` instead — the carriage return of `§04 C`,
seen rather than remembered. Keep that `console.log` until framing works, then delete it.

**What `node server.ts` does and does not do.** It strips types. It does not check them:

| | |
|---|---|
| Works | `interface` · annotations · generics · `as` · `satisfies` · `import type` · ESM `import` |
| Fails to parse | `enum` · `namespace` · parameter properties — `constructor(private x: number)` |
| Not attempted | **Type checking.** `const n: number = 'oops'` runs, and prints `oops` |

None of the three failures matter here — nothing in `§05`, `§06 F` or the drills uses an `enum` or a
parameter property. **Say it out loud when you start**, because it is eight seconds of free
credibility: *"I'm running the TypeScript directly, so the annotations are documentation rather than
checks — a mistake will show up as a runtime error, not a compile error."*

**Editor types are worth having, and getting them is three commands.** Without them, VS Code has no
definitions for `node:net`: the import gets a red squiggle and you get no completion on
`net.createServer`, `socket.on`, or the event names — which is exactly the API you will be leaning
on.

```bash
mkdir -p ~/interviews/discord && cd ~/interviews/discord
npm i -D @types/node
npm pkg set type=module
echo '{"compilerOptions":{"types":["node"]}}' > tsconfig.json
```

**Three commands, three different jobs, which is what makes them possible to retype from memory:**

| Command | Buys you |
|---|---|
| `npm i -D @types/node` | The definitions exist on disk |
| `npm pkg set type=module` | Node runs the file **without a warning** |
| the one-line `tsconfig.json` | The **editor** actually uses the definitions |

**The third one is not optional, and it is the one that will surprise you.** VS Code ships its own
TypeScript — 6.0.3 at the time of writing — and on 6 the `@types/node` in your `node_modules` is
**not** picked up implicitly. Without `"types": ["node"]` you get a red squiggle reading
`Cannot find name 'node:net'. Do you need to install type definitions for node?` on a file that runs
perfectly, which is a maddening thing to debug because the suggested fix is the thing you already
did. Nothing else in a `tsconfig.json` matters here — not `module`, not `moduleResolution`, not
`target`. One line is the whole file. **If you add it while the editor is open, run
`TypeScript: Restart TS Server` from the command palette**, or the language service will keep
serving the old answer.

**What you still do not need:** `npm init` — `npm i` writes the `package.json` itself. And the
`typescript` package — VS Code uses its bundled copy for the editor, so installing it would buy you
only the command-line `tsc`, which `node server.ts` never calls.

**The second command is the forgiving one.** Without it everything still works — Node detects the
module syntax and runs the file — it just prints a `MODULE_TYPELESS_PACKAGE_JSON` warning about the
reparse each time. Blank on it under pressure and you lose tidiness, not the round.

**Arrive with it already built.** The invitation says *"please have your development environment set
up"* — that is an instruction, not a loophole, and the thing to avoid is doing this on the 26th, not
doing it at all. But **leave `server.ts` out of it.** `§01 B` draws the line and it is worth
restating here: **stage the environment, never the program.** A `package.json` waiting for you is
preparation. A `makeLineReader` waiting for you is not — and that is also why the setup is worth
being able to retype from memory rather than keeping in a script. A script you run is a script you
cannot adapt when the directory turns out to be somewhere else.

**On the no-AI rule, since this is the obvious place to wonder.** TypeScript completion is static
analysis over `.d.ts` files — deterministic, offline, the same category of tool as a compiler error
or a linter. It is not what `§01 D` is about. What has to be off is anything generating suggestions
from a model: **Copilot, Cursor's completions, and — the one people forget — VS Code IntelliCode**,
which re-ranks the completion list with an ML model and ships preinstalled in some setups. Turn all
of them off at the settings level, then spend ten seconds on it in the opening: *"Copilot and
IntelliCode are off. I do have the Node type definitions installed so I get autocomplete on the
standard library — say the word if you'd rather I drop those too."* The invitation explicitly invites
that question, asking costs nothing, and it removes the only ambiguity in the room.

**Two fallbacks, in order, and between them the setup is unloseable.** First: **rename it
`server.mts`.** An explicit `.mts` is ESM TypeScript no matter what any `package.json` says, so it
walks past the whole module-type question and costs you nothing — you keep the types. If even that
fails for a reason you cannot diagnose in thirty seconds, rename to `server.mjs`, delete the one
annotation — `chunk: string` — and run `node server.mjs`: plain JavaScript, same file, ten seconds,
and nothing in this guide depends on the types. **The worst case is not *"I can't run"*, it is
*"I lost my annotations"*.**

**When it goes wrong,** which is nearly always one of four things:

| Symptom | Cause | Fix |
|---|---|---|
| `EADDRINUSE` | A previous run still holds the port | `lsof -ti:8080 \| xargs kill` — put it in your shell history before the call |
| `Connection refused` in `nc` | The server is not running, or is on another port | Check the server pane actually says `listening on 8080` |
| `Cannot use import statement outside a module` | A `package.json` above the file says `"type": "commonjs"`, which disables syntax detection | `npm pkg set type=module`, or delete the `package.json`, or rename the file to `server.mts` |
| Red squiggle: `Cannot find name 'node:net'` — but the file runs fine | The editor's TypeScript (VS Code bundles 6.x) does not pick up `@types/node` implicitly | `echo '{"compilerOptions":{"types":["node"]}}' > tsconfig.json`, then `TypeScript: Restart TS Server` |
| `Unknown file extension ".ts"` | Node older than 23.6 | `node -v` first. On 22.x: `node --experimental-strip-types server.ts` |
| `nc` connects but nothing echoes | Nothing has been sent yet — `nc` sends on Return | Press Return. Then check you are typing into the pane you think you are |

Then arrange the screen **before** the call, because rearranging terminals while someone watches
reads as unpreparedness:

| Pane | Holds | Why |
|---|---|---|
| Editor | `server.ts` | The thing being graded |
| Server | `node server.ts` | Restarted constantly. Keep it on its own pane so the scrollback stays readable |
| Client A | `nc localhost 8080` | |
| Client B | `nc localhost 8080` | **Two clients from minute one.** A one-client demo cannot show broadcast, which is the whole feature |

**The shape to arrange them in.** With the editor in a separate application, the three terminals
want to be server across the top, clients side by side underneath — not three stacked rows. The
server gets full width and half the height, which is where the scrollback is needed, and putting the
clients side by side means a broadcast is visibly a message crossing from left to right, which is
the single clearest way to demonstrate that the feature works:

```text
┌─────────────────────────────┐
│  node server.ts             │
├──────────────┬──────────────┤
│ nc … client A│ nc … client B│
└──────────────┴──────────────┘
```

**In Ghostty, that is two keystrokes** from a fresh window — `Cmd+Shift+D` to split down, which
moves focus into the new bottom pane, then `Cmd+D` to split that pane right. If you keep the editor
in Ghostty too, press `Cmd+D` first to claim the left half and build the three terminals in the
right one. Skip `tmux`: it is a prefix key you do not have in your fingers and a status bar on a
shared screen, to replace two keystrokes.

**The four Ghostty keys worth having before the day** — the defaults, so there is nothing to
configure:

| Key | Does | Why it matters here |
|---|---|---|
| `Cmd+Option+←↑→↓` | Move between panes | **The one to drill.** Reaching for the mouse to change pane is slow and reads as fumbling |
| `Cmd+Shift+Enter` | Zoom the focused pane to fill the window | For when the server pane fills with a stack trace: zoom, read, zoom back |
| `Cmd+Ctrl+=` | Equalise the splits | After panes drift while you resize |
| `Cmd+Ctrl+←↑→↓` | Resize by ten columns or rows | Give the server pane more height once the `recv:` lines pile up |

**`node --watch server.ts` restarts on every save** and rebinds the port cleanly, with no
`EADDRINUSE`. Use it while drilling, where it is free iteration speed. **Do not use it in the
round:** a restart drops every connected client, and you want that to happen when you decide it
does, not because you saved the file in the middle of explaining something. In the round, restart by
hand — up-arrow, Return.

**The ninety seconds themselves,** once the problem is stated: confirm the run command still works,
confirm the port, and say what you are about to do. *"I'm going to get an empty server listening
and connect to it with `nc` before I write any logic, so we both know the plumbing works."* That
costs ninety seconds and it buys the rest of the hour — every subsequent bug is a logic bug, which
is a bug you can reason about, rather than an environment bug, which is a bug that eats ten
minutes and your composure.

**Have `nc` in your fingers.** `nc localhost 8080` connects. `Ctrl-C` kills the client hard,
`Ctrl-D` sends EOF, and they produce different events on the server — `§07 E` has the table, and
knowing the difference out loud is a cheap signal.

**Rehearse the whole sequence cold** — `mkdir` to `echo: hello`, no reference open — twice: once
today and once on D-1. It is item 5 in `§08 B`, and it is the only failure mode in this round you
can eliminate completely in advance.

### F. RESOURCES, RANKED

Seven days. This list is short on purpose, and the order is the order.

1. **This guide's `§04`, then `§05 A` and `§05 B`.** Everything else is elaboration on those.
2. **The drills in `discord-drills`** — `§11`. Seven of them, red by default. Reps beat reading by
   a wide margin for this round, because the failure mode is not knowing things, it is not having
   typed them.
3. **The Node `net` documentation, once, properly.** `nodejs.org/api/net.html`. Read `createServer`,
   the `Socket` events, `write`'s return value, and `setEncoding`. Twenty minutes. You are allowed
   to reread it in the room, but reading it cold in the room costs five minutes you would rather
   spend on part 3.
4. **Discord's "How to prepare for your Discord interview" post**, once. It is the source of the
   rubric in `§01 C` and it is short. Read it for the six axes and for the sentence about red-black
   trees, which tells you what not to prepare.
5. **`§10`, for credibility** — enough of Discord's engineering story to answer *"why Discord"* and
   to ask a good question at the end. One evening, and only after the drills are running green.

**Skip** every interview-prep aggregator beyond the confidence table in `§01 C`, all bot-development
tutorials, and any "build a chat app" tutorial that reaches for Socket.IO or Express — they solve a
different problem, over HTTP, and the framing work that this round is actually about is exactly what
they hide from you.

**Worth emailing your recruiter now**, because the answers change how you prepare and none are
awkward:

- Will I be sharing my full screen, or a single window? *(Determines whether the docs tab is visible
  and whether you should say so up front.)*
- Is there anything you'd like me to have installed beyond `nc` and a language toolchain?
- Is the exercise done in a scratch folder of my own, or will something be sent to me at the start?
- Roughly how much of the 75 minutes is the exercise, versus intro and my questions?

### G. THE FIVE-MINUTE VERSION

If you read nothing else on the morning of the 26th:

- **Get an empty server listening and a `nc` client attached before writing any logic.** Ninety
  seconds, and every bug after it is a logic bug.
- **Write the framing helper first, once, and never touch it again.** `'data'` gives you chunks,
  not lines. `§04 C`. This is the bug that quietly breaks part 2 for people who got part 1 working.
- **One registry, one `broadcast`, one `cleanup`.** Every mutation of connected-client state goes
  through a named function. That single decision is what makes part 2 an addition instead of a
  rewrite, and refactoring-to-new-requirements is a *named* axis on their rubric.
- **Do not echo a message back to its sender.** It is the one explicit requirement in every report
  of part 1, and it is the first thing that gets demonstrated.
- **Handle the disconnect before you handle the happy path's polish.** A server that dies when one
  client hits `Ctrl-C` fails the functionality axis outright.
- **Say the trade-off out loud when you make it, not when asked.** *"I'm keeping a `Map` from name
  to socket rather than an array, because broadcast to a room has to be linear in the room, not in
  the server"* is a full answer. *"We could use an array or a map"* is a stall wearing an answer's
  clothes.
- **When they add a part, say what it touches before you type.** *"That's a change to dispatch and
  to the registry index; framing and lifecycle don't move."* Ten seconds, and it is the refactoring
  axis being graded in plain sight.

## 02 — The seven-day schedule, interleaved with Cursor

Seven days, and they are not empty days — the Cursor screen is Friday the 28th, forty-eight hours
after this one. The schedule below protects Cursor by keeping its reps alive at low volume rather
than pausing them, because a cold restart on the 27th is worse than four light days.

| Day | Date | Discord | Cursor |
|---|---|---|---|
| **D-7** | Wed 8/19 | **Baseline.** Drill 1 cold, 30 min, no reading first. Then `§01`, `§03`, `§04`. | — |
| **D-6** | Thu 8/20 | `§05 A` and `§05 B`. Drill 2. | Keep one design rep |
| **D-5** | Fri 8/21 | `§04 C` again, then drill 3 — framing only. `§06`. | One coding rep |
| **D-4** | Sat 8/22 | `§05 C`, `§05 D`. Drills 4 and 5. | One design rep |
| **D-3** | Sun 8/23 | `§07`, `§08`. Drill 6, the off-theme one. | Rest |
| **D-2** | Mon 8/24 | **Full mock: drill 7, sealed, 75 minutes, at 12:00 noon.** Then `§10`. | — |
| **D-1** | Tue 8/25 | **Taper.** `§01 G`, `§06 F`, `§12 A`. Retype the skeleton from blank twice. No new material. | — |
| **D-0** | Wed 8/26 | **12:00–1:15. Runbook is `§12`.** | Resumes the 27th |

**Do not read `§05` on D-7.** The baseline rep is only worth running once, and its value is the
honest number it gives you — which parts you reached, where the clock went, and what you had to
look up. That number is what tells you whether D-6 through D-4 should be weighted toward framing or
toward protocol design.

**Rules for the seven days.**

- AI off for every rep, at the settings level. An AI-assisted rep measures a skill you will not have.
- **The timer starts before you read the prompt.** Reading is part of the round.
- Narrate out loud even when alone. The narration is graded and it is a motor skill, not a decision.
- Run the parts in order on **one clock**, exactly as the real thing does — never restart the timer
  for part 2.
- **Self-grade with `§03 G` before you read the model answer.** Reading first replaces your memory
  of what you did with a memory of what you should have done, which is how a rep teaches nothing.
- Anything you had to look up goes on a list. On D-1 you retype those from blank until you do not.

## 03 — The seventy-five-minute shape

### A. THE CLOCK

Seventy-five minutes is not a long hour, it is a short ninety. The extra fifteen over a standard
screen is roughly one additional part, which is why the discipline in `§03 D` matters more here
than it would at sixty.

| Minute | Phase | What "done" looks like |
|---|---|---|
| 0 | Intros, and the prompt is stated | You have it in writing somewhere, in your own words |
| 3 | **Understand.** Restate it, run one exchange by hand, ask two or three questions | You have said the message flow out loud: *"A types a line, B sees it, A does not"* |
| 6 | **Plumbing.** Empty server listening, `nc` attached, one echoed line | Both terminals are live and you have proven the loop end to end |
| 10 | **Framing and the registry**, typed before any feature | `§04 C` helper and a `Map`. Nothing chat-specific yet |
| 16 | **Part 1**, to correct-and-demonstrated | Two clients, a message crosses, the sender sees nothing, a disconnect is clean |
| 34 | **Part 2**, as stated by them | Rooms or whatever they add, without part 1 being rewritten |
| 54 | **Part 3, or hardening** — their call, and ask | Either a third part, or the edge cases in `§06 E` closed deliberately |
| 66 | **Close.** Demonstrate, summarise, name the cuts | `§03 F`, unprompted |
| 71 | Your questions | `§10 C` |

**The hard rule:** if part 1 is still not demonstrable at **minute 34**, stop adding to it and get
what exists into a state you can show. A demonstrated part 1 plus a described part 2 outscores two
half-built parts every time, because *functionality* is the first axis on their rubric and
"compiles and runs" is a binary.

**The counter-rule, so you do not overshoot:** do not spend minutes 16–34 polishing part 1. Correct
and demonstrated is the target, not elegant. Elegance is graded through the *seam* — see `§03 D` —
and the seam is a structural decision made at minute 10, not a cleanup done at minute 30.

### B. THE OPENING, CLOSE TO WORD FOR WORD

The invitation says you may ask questions of the interviewer. In a problem whose later parts are
hidden, that permission is worth more than the browser. Use it in the first three minutes.

> *"Let me play it back. A client connects over TCP — I'll use `nc` — and sends some lines. Other
> connected clients should see those lines. So if I have A and B connected and A types 'hello', B
> sees 'hello' attributed to A, and A doesn't see it echoed. Is that right?"*
>
> *"Three things I want to check before I write anything. First, is there a handshake — does the
> first line a client sends mean something different from the rest, like a name? Second, when
> someone disconnects, does anyone need to be told? And third, is this one room, or should I be
> thinking about more than one from the start?"*
>
> *"Last one, and it's about how you'd like me to work: I'm assuming you'd rather I get a small
> thing running end to end and then grow it, over designing the whole thing up front. Tell me if
> you'd rather see it the other way."*

**Four things happened there and all four are graded.**

1. **You ran an example by hand** — A types, B sees, A does not. That is the no-self-echo
   requirement discovered by you rather than corrected into you, and it is the single most-reported
   part 1 detail.
2. **The third question asks what part 2 is** without asking what part 2 is. If the answer is
   *"one room for now"*, the word **for now** has just told you rooms are coming and you have
   fifteen free minutes of foresight. If they decline to say, you have lost nothing.
3. **The second question is the failure path**, asked before the happy path is written. Interviewers
   notice which candidates think about disconnects at minute 3 versus at minute 40, because on this
   problem disconnects are not an edge case, they are half the feature.
4. **The last question hands them a lever.** Some interviewers want to see design first. Asking
   costs eight seconds and removes the only strategic risk in the round.

**Then say the plan in one sentence before typing**, because it makes the next ten silent minutes
legible: *"Plan is: empty server plus `nc` first so the plumbing is proven, then line framing and a
client registry, then the actual broadcast. Should be talking to you by about minute fifteen."*

### C. WHAT "ELEMENTS YOU MAY BE UNFAMILIAR WITH" MEANS

It means sockets, and it is worth being precise about what part of sockets, because the unfamiliar
bit is narrower than "networking" and much more specific than most candidates expect.

| What people assume is hard | What is actually hard |
|---|---|
| Opening a listening socket | Six lines. `net.createServer(handler).listen(port)`. Not the problem |
| Concurrency and threads | **There are none.** Node gives you one thread and an event loop; the concurrency question answers itself, and saying so is a signal — see `§04 B` |
| The protocol | Trivial once framed. Split on the first space, switch on the verb |
| — | **Turning a byte stream into lines.** `'data'` fires with arbitrary chunks. One line may arrive in two chunks; two lines may arrive in one. `§04 C` |
| — | **The lifecycle.** `'end'`, `'close'`, `'error'`, and a half-open socket are four different things, and *every* one of them must reach the same cleanup. `§04 F` |
| — | **Backpressure.** `socket.write()` returns `false` when the kernel buffer is full, and ignoring that is how one slow client becomes unbounded memory. `§04 G` |

**The line to say when you hit the unfamiliar part**, because Discord grades resource use
explicitly: *"I want to check the exact semantics of `write`'s return value before I rely on it —
give me twenty seconds."* Then check it. Guessing at an API in front of someone who knows it is
strictly worse than looking it up in front of them.

### D. PART-BOUNDARY DISCIPLINE — THE ONE TECHNIQUE

Discord names refactoring on the rubric: *"How did you approach refactoring your solution to
consider the new requirements?"* That sentence is doing something specific. It says the new
requirement is coming, that your response to it is scored **separately from the code you had**, and
therefore that **part 1 is graded twice** — once on whether it works, and once on what it cost you
when part 2 arrived.

So the highest-leverage work in the round happens at minute 10, before any feature exists, and it
is three decisions:

**1. One registry, and one place that mutates it.** Not a `Set` of sockets scattered across three
handlers. A `Map` from a client id to a record, plus `add`, `remove`, and `broadcast` functions
that are the only code that touches it. Every reported part 2 — rooms, private messages, rate
limits, history — is a change to *what those three functions do*, and none of them is a change to
the handler that calls them.

**2. Framing lives below the protocol and never moves.** The chunk-to-line helper knows nothing
about chat. It is written once in part 1 and is untouched for the rest of the hour. If part 2 makes
you edit your framing code, the layering was wrong.

**3. Dispatch is a table, not an `if` chain.** Even in part 1, when there is exactly one command
and it is "say this to everyone", route it through a `handleLine(client, line)` that switches. Part
2 is then *adding rows*, which takes ninety seconds and reads as design, rather than *restructuring
a conditional*, which takes eight minutes and reads as rescue.

**Then, when part 2 lands, spend ten seconds on this before typing:**

> *"Okay — rooms. That's two changes. The registry gains a room index so broadcast stays linear in
> the room rather than the server, and dispatch gains three commands. Framing and lifecycle don't
> move. Let me do the index first."*

That sentence is the refactoring axis being graded, out loud, before the work rather than after it.
It costs ten seconds and it is the single highest-value thing you will say in the hour.

**The failure mode to recognise in yourself:** you finish part 1, they say "now add rooms", and
your first instinct is to open the connection handler. If that happens, stop. The connection
handler is the one file that should not change. Open the registry.

### E. WHEN YOU STALL, AND WHEN THEY NUDGE

| Situation | Say |
|---|---|
| A bug you cannot see, 60+ seconds in | *"Let me print what I'm actually receiving rather than what I think I am."* Then log the raw chunk with `JSON.stringify` so `\r` and `\n` become visible. This finds framing bugs in one step |
| You do not know an API | *"I'm going to check the `net` docs for thirty seconds rather than guess."* Then actually take thirty seconds, not four minutes |
| They ask "what happens if…" | It is a hint, not a quiz. **Answer it, then fix it.** *"Right now, nothing — the socket stays in the map. Let me wire that up."* |
| They ask about complexity | Answer in the shape of the data, not the code: *"Broadcast is linear in the room's membership, and the room lookup is constant, so it's O(members) not O(clients)."* `§04 G` |
| You are stuck on part 2 with 10 minutes left | *"I'd rather leave part 1 demonstrably working than half-land this. Let me revert the last change and tell you how I'd finish it."* Reverting to green, deliberately and out loud, scores |
| Silence has run 20+ seconds | Narrate the next line before you type it. Any sentence beats silence, and *"I'm about to do the boring bit"* is a fine sentence |

**What a nudge sounds like, so you catch it:** *"Interesting — what happens if two people pick the
same name?"* is not curiosity. It is the interviewer handing you an edge case they intend to see
handled. Treat every hypothetical as a requirement stated politely.

### F. THE CLOSE

At minute 66, stop coding **whether or not you are mid-thought**, and drive the close yourself. It
is the last thing they see and it is disproportionately what gets written down.

**Demonstrate first, then summarise.** Restart the server, connect both clients, and run the
scenario end to end — join, message, the other client sees it, the sender does not, one client
disconnects, the other is told, the server survives. Thirty seconds, and it is the *functionality*
axis proven rather than asserted.

Then:

> *"Where I got to: part 1 works end to end and I've just run it — two clients, broadcast, no
> self-echo, and a disconnect that cleans up and notifies. Part 2's rooms are in, with `/join` and
> `/who`, and the room index means broadcast is linear in the room rather than the server.*
>
> *What I'd do next, in order. First, a line-length cap — right now a client that never sends a
> newline grows my buffer without bound, which is the one thing in here I'd call a real bug rather
> than a missing feature. Second, backpressure: I'm ignoring `write`'s return value, so one slow
> reader can grow memory, and I'd give each client a small queue with a drop policy. Third, `/who`
> is linear in the room and I'd only care about that above a few thousand members.*
>
> *The trade-off I'd flag: I kept everything in memory with no persistence, because nothing in the
> requirements survived a restart. If reconnect-with-history mattered, that's the decision I'd
> revisit first."*

**The three moves in there.** You named a genuine bug before they found it, which converts a
finding into a judgement call. You ranked the remaining work, which shows you know what matters.
And you named the assumption you made rather than the feature you skipped — those are graded very
differently.

### G. SELF-GRADE RUBRIC — RUN THIS AFTER EVERY REP

Score honestly out of 100, before reading any model answer. Below 75, re-rep the same drill.

| | Points | Criterion |
|---|---:|---|
| 1 | 10 | **Plumbing proven before logic** — empty server and a live `nc` client inside the first six minutes. |
| 2 | 10 | Restated the problem and **ran one exchange by hand**, out loud, before typing. Asked at least two questions. |
| 3 | 15 | **Framing written once, correctly**, below the protocol, and never edited again. |
| 4 | 20 | **Part 1 correct and demonstrated** — two clients, no self-echo, and a disconnect that neither crashes the server nor leaves a stale entry. |
| 5 | 20 | **The seam held**: part 2 was an addition. One registry, one broadcast, dispatch by table. Part 1's handler was not reopened. |
| 6 | 10 | Every non-obvious choice got a spoken reason at the moment it was made. No menus, no undecided "it depends". |
| 7 | 10 | Narrated continuously; no silence beyond ~20 seconds. Looked something up out loud rather than guessing. |
| 8 | 5 | Closed by **demonstrating**, then naming cuts and assumptions in priority order, unprompted. |

**Automatic flags:** wrote logic before a client was connected · concatenated `'data'` chunks
without splitting on `\n` · echoed to the sender · the server died on `Ctrl-C` from a client ·
mutated the client map in more than one place · rewrote part 1 to fit part 2 · silent stretches ·
ran out of time with no demonstration · guessed at an API instead of reading it.

## 04 — The line server: the one chapter that matters

Every reported version of this question — one room, many rooms, private messages, history, rate
limits, and the off-theme key–value store in `§05 E` — is the same five-step program with a
different step 3. This chapter is those five steps. If you internalise one chapter before the 26th,
it is this one, and if you only have an hour, it is `§04 C` and `§04 F`.

### A. WHY EVERY DISCORD SCREEN QUESTION IS THIS QUESTION

Write the program out as data flow and the invariance is obvious:

> **accept** → **frame** bytes into lines → **parse** a line into a command → **mutate** one
> registry → **write** lines to some subset of sockets

Now overlay the reported variants. Part 2 rooms change the *subset* and add rows to *parse*.
Private messages change the *subset*. History changes the *registry* and adds a write on join. Rate
limiting adds a check between parse and mutate. A key–value store replaces *parse* entirely and
guts the subset down to one socket. **Nothing in any variant touches accept or frame.**

That is the whole strategic claim of this guide: two of the five steps are fixed, they are the two
you are least likely to have written recently, and they are the two that fail silently. So you type
them first, from muscle memory, and spend the remaining time on the three steps that actually vary.

### B. THE FOUR LAYERS

| Layer | What it is | Changes between parts? |
|---|---|---|
| **Socket** | `net.createServer`, one `Socket` per client, and the four events in `§04 F` | **No** |
| **Framing** | Bytes → lines. A per-socket buffer, split on `\n`, strip a trailing `\r` | **No** |
| **Protocol** | Line → command. One `handleLine`, one dispatch table | Yes |
| **State** | The registry: who is connected, what they are called, where they are | Yes |

**The concurrency question answers itself, and saying so is a signal.** In Node there is one thread
and one event loop, so two `'data'` handlers never interleave mid-function and **there is no lock to
take**. Say it explicitly when the interviewer probes concurrency, and say what it costs:

> *"There's no mutex here because Node is single-threaded — a handler runs to completion before the
> next event is dispatched, so the registry can't be observed half-updated. What I do have to be
> careful about is anything that awaits in the middle of a mutation, because that's a yield point
> and the world can change across it. The other cost is that one CPU-heavy handler stalls every
> connection, which is the trade I'm accepting for not having locks."*

That paragraph is worth more than a working part 3. It answers *understanding* and *trade-offs*,
two named rubric axes, in one breath — and it is the honest answer, not a dodge. If you were in Go,
the same question would have the opposite shape: a goroutine per connection, real concurrent access,
and either a mutex around the registry or a single hub goroutine that owns it.

### C. LINE FRAMING, AND THE BUG THAT COSTS THE ROUND

**TCP is a byte stream. It has no idea what a message is.** The `'data'` event fires whenever bytes
arrive, in whatever sizes the network and the kernel decided on. Three consequences, each of which
produces a different and confusing symptom:

| What happens | Why | Symptom if you ignore it |
|---|---|---|
| One line arrives in **two chunks** | The segment boundary fell mid-line | Half a message is broadcast, then the other half as a second message. Looks like "sometimes it splits words" |
| **Two lines arrive in one chunk** | The client sent fast, or Nagle coalesced them | Two messages appear as one line with a `\n` inside it. Looks fine in `nc` and breaks every parse |
| A chunk arrives with **no newline at all, ever** | The client is `nc` with no Return pressed, or is hostile | Your buffer grows without bound. This is the memory bug in `§03 F` |

**The demonstration that makes this land**, and which is worth running once during prep: paste a
200-character line into `nc` and log the raw chunks with `JSON.stringify(chunk)`. You will see the
split. Nothing about this is theoretical.

**The helper. Write it once, in part 1, and never open it again.**

```ts
import net from 'node:net'

/**
 * Chunks in, lines out. The only function in the program that knows about `\n`.
 * Nothing above this layer should ever see a partial line, and nothing below it
 * should ever see a command.
 */
function makeLineReader(onLine: (line: string) => void, onOverflow: () => void, maxLen = 4096) {
  let buf = ''
  return (chunk: string) => {
    buf += chunk
    let nl = buf.indexOf('\n')
    while (nl !== -1) {                          // while, not if: a chunk may hold many lines
      const line = buf.slice(0, nl).replace(/\r$/, '')   // PuTTY raw sends \r\n; nc sends \n
      buf = buf.slice(nl + 1)
      onLine(line)
      nl = buf.indexOf('\n')
    }
    if (buf.length > maxLen) {                   // a client that never sends \n is not a client
      buf = ''
      onOverflow()
    }
  }
}
```

Wire it with `setEncoding`, which is the second half of the trick:

```ts
socket.setEncoding('utf8')                       // chunks arrive as strings, not Buffers
socket.on('data', makeLineReader(
  (line) => handleLine(client, line),
  () => { client.send('error line too long'); socket.destroy() },
))
```

**`setEncoding('utf8')` is not cosmetic and is worth one sentence out loud.** Without it you get
`Buffer`s, and calling `.toString()` on each one independently corrupts any multi-byte character
that straddles a chunk boundary — an emoji arrives as two replacement characters and you spend six
minutes on a bug that has nothing to do with your logic. `setEncoding` runs a `StringDecoder`
underneath, which holds the partial bytes back until the character is complete. **This is the
highest ratio of signal to keystrokes in the entire round:** *"I'm setting the encoding so the
decoder handles multi-byte characters split across chunks — otherwise an emoji at a segment
boundary comes through mangled."*

**The five things being graded in that helper.**

1. `while`, not `if`. The single most common version of this bug is handling exactly one line per
   chunk, which works perfectly until someone types fast.
2. The buffer is **per socket**, closed over inside `makeLineReader`. A module-level buffer shared
   between clients interleaves their messages and is very hard to see.
3. The `\r` strip, which is the difference between working with `nc` and working with PuTTY in raw
   mode — and the invitation names PuTTY, so some interviewer somewhere is using it.
4. **The overflow cap.** Unbounded buffer growth from a well-formed TCP connection is the one real
   security-shaped bug in this program, and naming it unprompted at close is worth real credit.
5. Nothing above this line knows about `\n`, and nothing in it knows about chat.

### D. THE REGISTRY IS THE ONLY SHARED STATE

One map, one set of functions that touch it, and every feature in every reported part 2 is a change
to those functions rather than to the connection handler.

```ts
interface Client {
  id: number
  name: string | null                    // null until the first line names them
  room: string | null                    // null until /join. Part 1 can leave this unused
  socket: net.Socket
  send(line: string): void               // the only way anything writes to a socket
}

const clients = new Map<number, Client>()          // every connection, named or not
const rooms = new Map<string, Set<Client>>()       // the index that keeps broadcast cheap
```

**Why a room index rather than filtering `clients` on every message.** Filtering is O(connected)
per message; the index is O(members). With one room they are identical, which is exactly why the
decision has to be made in part 1 on principle rather than in part 2 under pressure. State it when
you type it: *"I'm indexing by room even though there's only one room right now, because broadcast
should be linear in the room and not in the server — and it means rooms are a data-structure change,
not a control-flow change."*

**The three functions, and nothing else, mutate these maps.**

```ts
function join(c: Client, room: string) {
  leave(c)                                        // exactly one room at a time — an invariant
  c.room = room
  let members = rooms.get(room)
  if (!members) rooms.set(room, (members = new Set()))
  members.add(c)
  broadcast(room, `* ${c.name} joined ${room}`, c)
}

function leave(c: Client) {
  if (!c.room) return
  const members = rooms.get(c.room)
  members?.delete(c)
  if (members && members.size === 0) rooms.delete(c.room)   // empty rooms don't linger
  broadcast(c.room, `* ${c.name} left ${c.room}`, c)
  c.room = null
}

function broadcast(room: string, line: string, except?: Client) {
  for (const m of rooms.get(room) ?? []) {
    if (m !== except) m.send(line)                // `except` is the no-self-echo requirement
  }
}
```

**Four invariants live in there, and they are the graded content.** A client is in at most one room,
enforced by `join` calling `leave` rather than by callers remembering to. An empty room is deleted,
so a long-running server does not accumulate them. `broadcast` takes an `except` rather than making
every caller filter — which is how you make the no-self-echo rule structurally true instead of
remembered. And `send` is the only path to a socket, which is what makes rate limiting and
backpressure a one-file change in part 3 rather than a search-and-replace.

**Names are a `Map` decision too.** If part 2 asks for private messages or reconnect, you need
name → client, and scanning `clients` for a matching name is the kind of thing that works and reads
as unconsidered. A second `Map<string, Client>` costs two lines; the invariant it forces — names are
unique, and a second connection with a taken name is rejected — is the edge case in `§06 E` that
gets probed most often.

### E. THE NODE KIT

Everything you need, in one place, so that none of it costs thinking time on the 26th.

```ts
import net from 'node:net'

const server = net.createServer((socket) => {
  // one call per connection; `socket` is a duplex stream
})

server.listen(8080, () => console.log('listening on 8080'))
```

| Thing | What it does | The detail that matters |
|---|---|---|
| `net.createServer(fn)` | `fn` runs once per accepted connection | No `await`, no callback for readiness — connection setup is already done |
| `socket.setEncoding('utf8')` | Chunks arrive as strings | Handles multi-byte characters split across chunks. See `§04 C` |
| `socket.write(str)` | Queues bytes | **Returns `false`** when the kernel buffer is full. `§04 G` |
| `socket.end(str?)` | Sends optional data, then FIN | The graceful close. Use for `/quit` |
| `socket.destroy()` | Tears the socket down now | The ungraceful close. Use for protocol violations |
| `socket.remoteAddress` / `remotePort` | Identifies the peer | A free unique id before a client has named itself |
| `socket.setNoDelay(true)` | Disables Nagle | Worth one sentence: without it, small writes can be coalesced and delayed ~40 ms |
| `server.listen(0)` | Binds an ephemeral port | How the drill specs avoid port collisions — `§11` |

**Three ergonomics that save real keystrokes under time pressure.** Use `node:net` rather than
`net` so the import is unambiguous. Run with `node server.ts` rather than a build step, so
restarting is one keystroke of history. And give `Client` a `send` method at construction — closing
over the socket once means the rest of the program never types `socket.write` again, which is what
makes `§04 G` a two-line change.

### F. THE LIFECYCLE: EVERY EXIT PATH CLEANS UP

This is where servers die in front of interviewers, and it is entirely avoidable.

| Event | Fires when | What you must do |
|---|---|---|
| `'end'` | The peer sent FIN — `Ctrl-D` in `nc`, or a clean client shutdown | Nothing, usually. `'close'` is coming |
| `'error'` | ECONNRESET, EPIPE, anything at all | **You must have a listener.** See below |
| `'close'` | The socket is fully done, on every path | **All cleanup goes here, and only here** |
| `'timeout'` | Only if you called `setTimeout` | Nothing by default — it does not close the socket for you |

**The single most important line in the program:**

```ts
socket.on('error', (err) => { /* log and let 'close' clean up */ })
```

**An `'error'` event with no listener is thrown**, and a thrown error on an EventEmitter takes down
the entire Node process. **The trigger is not the client leaving — it is your next write to a client
that has already gone.** A clean `Ctrl-C` sends FIN and you get `'end'` then `'close'` with no error
at all; but a peer that dies with bytes still unread, or that resets, turns the very next
`socket.write()` into an ECONNRESET or EPIPE. A broadcast server is always writing to everyone,
which makes this routine rather than exotic: one client leaves mid-broadcast and the process dies in
front of the interviewer, looking like a crash caused by nothing. It is the highest-frequency way
this exercise goes visibly wrong, and it is one line.

**If you try to reproduce it, you need two clients.** A lone idle `nc` drains its socket the instant
anything arrives, so you can `Ctrl-C` it all day and never see an error — there is nothing in flight
to fail on. Connect two, keep one talking, and kill the other.

**Put cleanup on `'close'`, not `'end'`,** because `'close'` is the only event that fires on every
path — clean FIN, reset, error, and your own `destroy()`. Cleanup on `'end'` means a client that
vanishes *without* a clean FIN — a reset, a dropped link, a `destroy()` with unread data — leaves a
stale entry in the registry, and the symptom is a ghost: `/who` lists someone who left, and
broadcasting to them throws later, somewhere else entirely.

```ts
socket.on('close', () => {
  leave(client)                                   // removes from the room, notifies, GCs the room
  clients.delete(client.id)
  if (client.name) byName.delete(client.name)
})
```

**Say the invariant out loud when you write it:** *"Every way this socket can die routes through
`'close'`, and `'close'` is the only place I remove from the registry. That way there's one cleanup
path rather than four."* That is *code quality — well abstracted such that it could be tested*,
which is a named axis, expressed as a sentence.

**Half-open connections, if they ask.** By default Node closes the writable side when it receives
FIN, so a peer that shuts down its write side ends the connection. `allowHalfOpen: true` changes
that and is occasionally the right answer for request/response protocols where a client sends
everything then reads. For a chat server it is not — mention it only if asked, and mention it as a
thing you deliberately did not want.

### G. BACKPRESSURE, AND THE COMPLEXITY FOLLOW-UP

**`socket.write()` returns a boolean and almost nobody checks it.** `false` means the internal
buffer is above the high-water mark — the peer is not reading fast enough. Node keeps accepting your
writes and keeps buffering them, in your process's memory, indefinitely. One slow reader in a busy
room is therefore an unbounded memory leak with no error and no log line.

The question *"what happens if one client is really slow?"* is reported as a standard follow-up, so
have the answer ready even if you never write it:

> *"Right now, nothing good — I'm ignoring `write`'s return value, so a slow reader's backlog grows
> in my heap without bound. The fix is per-client: give each one a bounded queue, stop writing when
> `write` returns `false`, resume on `'drain'`, and when the queue hits its cap, pick a policy —
> for chat I'd drop the oldest messages rather than disconnect, because a laggy client that misses
> some history is better than a laggy client that gets kicked. The cost is that delivery is no
> longer guaranteed, which for a chat room is the right trade and for a payments feed would not be."*

The two-line version, if you have time to actually write it:

```ts
send(line: string) {
  if (this.socket.writableLength > HIGH_WATER) return   // drop rather than buffer without bound
  this.socket.write(line + '\n')
}
```

**The complexity follow-up that always comes.** Discord's rubric says *"know if something is
constant time, linear time, or worse."* Answer in the shape of the data structure, and volunteer
the number that matters:

| Operation | Cost | The line to say |
|---|---|---|
| Accept a connection | O(1) | *"Map insert."* |
| Frame a chunk | O(chunk) amortised | *"Linear in bytes received, which is unavoidable."* |
| Look up a room or a name | O(1) | *"That's why both are maps."* |
| **Broadcast** | **O(members)** | ***"Linear in the room, not in the server — that's what the room index buys."*** |
| `/who` | O(members) | *"Same set, and I'd paginate above a few thousand."* |
| Disconnect cleanup | O(1) | *"Set delete plus two map deletes — no scan."* |

**The trap inside the framing helper, and the honest answer if pushed.** `buf.slice(nl + 1)` copies
the remainder on every line, so a chunk carrying *k* lines is O(k · remaining) rather than
O(chunk). For interactive chat, where a chunk is one short line, that is free and the simplicity is
worth it. Say exactly that: *"This is quadratic in the number of lines per chunk. For a human typing
into `nc` a chunk holds one line, so it doesn't matter — if this were a firehose I'd track an offset
instead of re-slicing."* **Naming a real inefficiency and then defending it with the access pattern
is a much stronger signal than not having one,** and it is precisely the *trade-offs* axis.

## 05 — Five problems, worked

Four of these are the reported shapes, in the order they are reported to arrive. The fifth is
deliberately **not** a chat server, for the reason `§05 E` gives.

Read a problem only after you have run its drill and self-graded with `§03 G`. Reading first
replaces your memory of what you did with a memory of what you should have done, and a rep that
teaches nothing is worse than no rep, because it costs the same time and leaves you confident.

### A. BROADCAST CHAT

**This is the one to be able to write in your sleep.** Every source that names a Discord part 1
names this, and everything in `§05 B` through `§05 D` is built on top of it.

> **The prompt, roughly.** Build a chat server. Clients connect over TCP — use `nc` — and the first
> line a client sends is its name. Every line after that is a message, which every other connected
> client should see. A client should not see its own messages echoed back.

**Your first three questions.** Is the first line special, or is naming a command? What should
happen when someone disconnects — does anyone need to be told? And is this one room, or should I be
thinking about more than one? The third is the one that matters; the answer *"one room for now"*
contains the word **for now**, and that word is worth fifteen minutes of foresight.

**The shape to commit to before writing bodies**, typed into the file so the interviewer can see the
plan:

```ts
interface Client {
  socket: net.Socket
  name: string | null              // null until the first line names them
  send(line: string): void         // the only path to a socket, anywhere
}

const clients = new Set<Client>()
const byName = new Map<string, Client>()

function broadcast(line: string, except?: Client): void
function handleLine(c: Client, line: string): void
```

**Say this while you type it:** *"Three things before any logic. `send` on the client so nothing
else ever touches `socket.write` — that's what makes rate limiting a one-line change later.
`broadcast` takes an `except`, so 'don't echo to the sender' is structural rather than something I
have to remember at each call site. And a `byName` map, because the moment there are private
messages or reconnects, scanning for a name is the thing that reads as unconsidered."*

<details>
<summary><strong>Model answer — the whole thing, ~70 lines</strong></summary>

**The load-bearing idea:** the connection handler contains no chat logic at all. It wires four
things — encoding, framing, the error listener, the close listener — and hands every line to
`handleLine`. Parts 2 and 3 never reopen it.

```ts
import net from 'node:net'

// ---- framing: written once, never touched again (§04 C) --------------------
function makeLineReader(onLine: (line: string) => void, onOverflow: () => void, maxLen = 4096) {
  let buf = ''
  return (chunk: string) => {
    buf += chunk
    let nl = buf.indexOf('\n')
    while (nl !== -1) {                                 // while, not if
      const line = buf.slice(0, nl).replace(/\r$/, '')  // PuTTY raw sends \r\n
      buf = buf.slice(nl + 1)
      onLine(line)
      nl = buf.indexOf('\n')
    }
    if (buf.length > maxLen) { buf = ''; onOverflow() } // never-sends-\n is not a client
  }
}

interface Client { socket: net.Socket; name: string | null; send(l: string): void }

export function createServer(): net.Server {
  const clients = new Set<Client>()
  const byName = new Map<string, Client>()

  // ---- the registry: the only code that reads or mutates membership -------
  function broadcast(line: string, except?: Client) {
    for (const c of clients) {
      if (c !== except && c.name !== null) c.send(line)  // unnamed clients aren't in yet
    }
  }

  // ---- dispatch: a switch even with one case, so part 2 is new rows -------
  function handleLine(c: Client, raw: string) {
    const text = raw.trim()
    if (text === '') return

    if (c.name === null) {                              // the handshake
      if (byName.has(text)) return c.send('error name taken')
      c.name = text
      byName.set(text, c)
      c.send(`you are ${text}`)
      return broadcast(`* ${text} joined`, c)
    }

    if (text === '/quit') { c.send('bye'); return void c.socket.end() }

    broadcast(`${c.name}: ${text}`, c)                  // `except` IS the requirement
  }

  return net.createServer((socket) => {
    socket.setEncoding('utf8')                          // decoder handles split multi-byte
    const client: Client = {
      socket,
      name: null,
      send: (l) => { if (!socket.destroyed) socket.write(l + '\n') },
    }
    clients.add(client)
    client.send('welcome! what is your name?')

    socket.on('data', makeLineReader(
      (l) => handleLine(client, l),
      () => { client.send('error line too long'); socket.destroy() },
    ))

    socket.on('error', () => {})                        // WITHOUT THIS, A WRITE TO A DEAD PEER KILLS IT
    socket.on('close', () => {                          // the only cleanup path (§04 F)
      clients.delete(client)
      if (client.name !== null) {
        byName.delete(client.name)
        broadcast(`* ${client.name} left`, client)
      }
    })
  })
}
```

**The five things in there an interviewer is looking for.**

1. **The framing loop is a `while`.** Everything else in the file is ordinary; this is the line that
   separates people who have written a socket server from people who have written an HTTP handler.
2. **`socket.on('error', …)` exists.** Without it, the next broadcast to a client that has already
   left takes the whole process down, live, on the shared screen.
3. **Cleanup is on `'close'` and nowhere else.** On `'end'` instead, a hard reset leaves a ghost in
   the registry and `/who` lists someone who left.
4. **`broadcast` takes an `except`.** The no-self-echo requirement is enforced by the signature
   rather than by remembering to filter at three call sites.
5. **`handleLine` is a switch with one interesting case.** It looks like over-engineering until part
   2 arrives, at which point it is ninety seconds instead of eight minutes.

</details>

**The follow-ups they will add, in the order they usually come:**

| Follow-up | The answer, in one line |
|---|---|
| "What if two people pick the same name?" | Already handled — `byName` makes it a lookup, and the client stays unnamed and can retry |
| "What if someone disconnects mid-message?" | The partial line is in the per-socket buffer and dies with it. Nothing to clean up, which is the point of the buffer being per socket |
| "Is there a race between two clients sending at once?" | No — one thread, one event loop, handlers run to completion. `§04 B`, and name the cost |
| "How does this scale?" | `§09`. Pub/sub backbone, sticky sessions, and the connection registry moves out of process |
| "What's the complexity of a broadcast?" | O(connected). With rooms it becomes O(members), which is why the index exists |

**What a weak answer looks like**, so you can hear yourself doing it: `socket.on('data', d => broadcast(d.toString()))` with no framing · no `'error'` listener, so the first `Ctrl-C` ends the round · echoing to the sender and then filtering it out at the call site instead of in `broadcast` · cleanup duplicated in `'end'` and `'close'` · every mutation of `clients` written inline in the connection handler, so part 2 means reopening it.

> **Runnable:** `discord-drills/src/drills/discord-01-broadcast-chat` · Spec: 13 tests, parts 2–3 gated

### B. ROOMS AND SLASH COMMANDS

The reported part 2, and the part where the grade is decided — not by whether you can write rooms,
but by whether part 1 let you.

> **The prompt, roughly.** Now let people have separate conversations. A client should be able to
> join a room, which is created on demand, and only see messages from the room it is in. Add
> whatever commands you need.

**Say this before you type anything.** Ten seconds, and it is the refactoring axis being graded in
plain sight:

> *"Rooms are two changes. The registry gains a room index, so a broadcast stays linear in the room
> rather than the server. And dispatch gains three commands. Framing and the lifecycle don't move —
> the only thing I have to be careful about is that leaving on disconnect now has to go through the
> same path as leaving by command, so I'll write `leave` once and call it from both."*

**The design decision worth defending**, because it is the one an interviewer will push on:

```ts
const rooms = new Map<string, Set<Client>>()   // an index, not a filter
```

*"I could filter `clients` by `c.room` on every message, which is O(connected) per message. Indexing
makes it O(members). With one room those are the same number, so this is a decision I'm making on
principle rather than on measurement — but the reason it's the right principle is that it also makes
`/who` a set read rather than a scan, and it makes empty-room cleanup a size check."*

<details>
<summary><strong>Model answer — join, leave, and the dispatch table</strong></summary>

**The load-bearing idea:** `join` calls `leave`. "A client is in at most one room" then becomes an
invariant enforced in one place, rather than a rule every caller has to remember.

```ts
function broadcast(room: string, line: string, except?: Client) {
  for (const m of rooms.get(room) ?? []) if (m !== except) m.send(line)
}

function leave(c: Client) {
  if (c.room === null) return
  const members = rooms.get(c.room)
  members?.delete(c)
  broadcast(c.room, `* ${c.name} left ${c.room}`, c)
  if (members && members.size === 0) rooms.delete(c.room)   // empty rooms don't linger
  c.room = null
}

function join(c: Client, room: string) {
  leave(c)                                        // the invariant lives here, not in callers
  let members = rooms.get(room)
  if (!members) rooms.set(room, (members = new Set()))
  members.add(c)
  c.room = room
  c.send(`you joined ${room}`)
  broadcast(room, `* ${c.name} joined ${room}`, c)
}
```

Dispatch becomes a table. Note that the *shape* of `handleLine` did not change — only its rows:

```ts
const sp = line.indexOf(' ')
const verb = sp === -1 ? line : line.slice(0, sp)
const rest = sp === -1 ? '' : line.slice(sp + 1).trim()

switch (verb) {
  case '/join':  return rest ? join(c, rest) : c.send('error usage: /join <room>')
  case '/rooms': { const n = [...rooms.keys()].sort()
                   return c.send(n.length ? `rooms: ${n.join(', ')}` : 'rooms: (none)') }
  case '/who':   { if (c.room === null) return c.send('error you are not in a room')
                   const w = [...(rooms.get(c.room) ?? [])].map((m) => m.name!).sort()
                   return c.send(`who: ${w.join(', ')}`) }        // asker only
  case '/msg':   { const gap = rest.indexOf(' ')
                   if (gap === -1) return c.send('error usage: /msg <name> <text>')
                   const target = byName.get(rest.slice(0, gap))
                   if (!target) return c.send('error no such user')
                   return target.send(`[${c.name}] ${rest.slice(gap + 1)}`) }
  case '/quit':  c.send('bye'); return void c.socket.end()
  default:       return c.send('error unknown command')
}
```

And the one line in the connection handler that *does* change — `'close'` now calls `leave`, so a
disconnect and a `/join` elsewhere are the same code path:

```ts
socket.on('close', () => {
  leave(client)                                 // announces, and GCs the room
  if (client.name !== null) byName.delete(client.name)
})
```

**The four things being graded here.**

1. **`join` calls `leave`.** Two people will write this; one of them will set `c.room = room`
   directly and leave a stale entry in the old room's set, and it will not show up until someone
   disconnects.
2. **The empty-room delete.** Small, and it is the difference between a server that runs for an hour
   and one that runs for a month. Say the word "unbounded" out loud when you write it.
3. **`/who` answers only the asker.** Broadcasting the answer is the sort of thing that works and is
   still wrong, and it is a one-word difference in the code.
4. **The `default` case exists.** `/dance` producing silence is indistinguishable from a broken
   server; producing `error unknown command` is a protocol.

</details>

**The follow-ups, in the order they usually come:**

| Follow-up | The answer, in one line |
|---|---|
| "Can someone be in two rooms?" | Not today, and `join` calling `leave` is where that is enforced. Supporting it means `c.room` becomes a `Set` and `leave` takes an argument — a contained change, which is the point |
| "What if they message before joining?" | An explicit `error you are not in a room`. Silence is the failure mode here, not a crash |
| "How would you list the biggest rooms?" | `rooms` is already a map to sets, so it is a sort over sizes — O(rooms log rooms), and I would cache it if it were on a hot path |
| "What if a room name has spaces?" | Right now it works, because I take the rest of the line. If names needed to be tokens I would validate on join rather than at each use |

**What a weak answer looks like:** filtering `clients` on every message and calling it fine because
there is only one room · setting `c.room` in two places · a disconnect that removes from `clients`
but not from the room's set · `/who` broadcast to everybody · rooms that are never deleted, with no
acknowledgement that this is a leak · and, most commonly, **reopening the connection handler** to
thread the room through, which is the specific thing part 1 was supposed to prevent.

> **Runnable:** `discord-drills/src/drills/discord-02-rooms-and-commands` · Spec: 15 tests

### C. HISTORY, REPLAY, AND RECONNECT

The most commonly reported part 3. The ring buffer is not the interesting part.

> **The prompt, roughly.** When someone joins a room, show them what they missed — the last ten
> messages. And if a client reconnects with the same name, put them back where they were.

**The observation that makes this a design question rather than a data-structure question:** you now
have **two things with different lifetimes**. Membership dies with the last socket in the room.
History must outlive it, or "what you missed" is empty exactly when it matters. So they are two
maps, and saying that out loud is most of the answer.

<details>
<summary><strong>Model answer — two maps, one leak, named</strong></summary>

```ts
const members = new Map<string, Set<Client>>()   // dies when the last socket goes
const history = new Map<string, string[]>()      // outlives it. Deliberately unbounded
const lastRoom = new Map<string, string>()       // name → where they were, for reconnect

function record(room: string, line: string) {
  const ring = history.get(room) ?? []
  ring.push(line)
  if (ring.length > 10) ring.shift()             // fixed window, oldest out
  history.set(room, ring)
}
```

Replay happens inside `join`, to the joiner only, before the room is told anyone arrived:

```ts
c.send(`you joined ${room}`)
const ring = history.get(room)
if (ring && ring.length > 0) {
  c.send(`* replaying ${ring.length}`)
  for (const line of ring) c.send(line)          // joiner only — not a broadcast
}
broadcast(room, `* ${c.name} joined ${room}`, c)
```

And `leave` deletes from `members` but never from `history`:

```ts
if (set && set.size === 0) members.delete(c.room)   // membership only; history stays
```

**The three things being graded, and the third is the real one.**

1. **Replay goes to the joiner, not the room.** A `broadcast` here re-sends everyone the last ten
   messages every time anybody joins, which is both wrong and very visible.
2. **The ring is capped on write**, not trimmed on read. Trimming on read means the array grows
   forever and you have merely hidden it.
3. **You said the word "unbounded" before they did.** `history` grows one entry per room name ever
   used and nothing removes it. *"That map is a leak — it grows with the number of distinct rooms
   ever created, not with live rooms. I'm accepting it because rooms are user-named and the
   cardinality is low, and the fix is an LRU keyed on last activity."* **Naming your own leak
   converts a finding into a judgement call**, and it is the single highest-value sentence in this
   problem.

</details>

**The follow-ups:** *"Ten messages or ten minutes?"* — a count is O(1) to enforce and a window needs
timestamps and a scan; I would ask which one users actually complain about · *"What if history has
to survive a restart?"* — then it stops being a `Map` and becomes the one thing in this program that
needs storage, and I would reach for an append-only log per room before a database · *"Should
private messages be in history?"* — no, and the fact that `record` is only called from the room
broadcast path is what makes that true by construction.

**What a weak answer looks like:** one map holding both membership and history, so history dies with
the room · replay broadcast to everyone · `slice(-10)` on read while the array grows without bound ·
reconnect implemented by leaving the old `Client` object in the registry, so a name is never free ·
and never mentioning that `history` leaks.

> **Runnable:** `discord-drills/src/drills/discord-04-history-and-reconnect` · Spec: 9 tests

### D. RATE LIMITING AND SLOW CLIENTS

The other reported part 3, and the one place where a named rubric axis — *"is the code well
abstracted such that it could be tested?"* — has a concrete, thirty-second answer.

> **The prompt, roughly.** Stop one person flooding the room. Cap it at thirty messages per minute
> per client, and drop anything over the cap.

**Take the clock as a parameter, and say why.** This is the highest ratio of signal to keystrokes in
the whole hour after `setEncoding`:

```ts
export function createServer(opts: { now?: () => number; limit?: number; windowMs?: number } = {}) {
  const now = opts.now ?? Date.now
```

*"I'm injecting the clock. A limiter that reads `Date.now()` internally can only be tested by
sleeping, which means in practice it doesn't get tested. This way the whole window is exercisable in
milliseconds."*

<details>
<summary><strong>Model answer — sliding, not fixed</strong></summary>

**The load-bearing idea:** evict expired stamps *before* checking the count. That one ordering is
the difference between a sliding window and a fixed one, and a fixed window lets a client send
double the limit across a boundary.

```ts
function allow(c: Client): boolean {
  const t = now()                                                        // read the clock once
  const cutoff = t - windowMs
  while (c.stamps.length > 0 && c.stamps[0] <= cutoff) c.stamps.shift()   // evict first
  if (c.stamps.length >= limit) return false
  c.stamps.push(t)
  return true
}
```

**Read the clock once per decision.** With an injected clock the two reads return the same value, so
this changes nothing you can observe — but it means the eviction, the limit check and the stamp you
store all agree on what *now* is, and *"it can't move between those lines, I take it once"* is a
complete answer to the obvious follow-up. Note also that `cutoff` is an **instant, not a duration**:
an epoch millisecond minus a window length is still an epoch millisecond, which is why every
comparison in here is timestamp against timestamp.

Called from exactly one place, because `handleLine` is a table:

```ts
if (line.startsWith('/')) { /* commands are never limited — see below */ }
if (!allow(c)) { c.dropped++; return c.send('error rate limited') }
c.sent++
broadcast(`${c.name}: ${line}`, c)
```

**The four things being graded.**

1. **Sliding, and you can say why.** *"A fixed window resets on a boundary, so a client can send the
   whole budget at 0:59 and the whole budget again at 1:01. Keeping the stamps costs O(limit) memory
   per client and removes that."*
2. **Per client, not per server.** One flooder must not throttle everyone else, and the state lives
   on the `Client` for that reason.
3. **Commands are exempt.** A throttled user must still be able to ask why and to leave. This is a
   product judgement, stated as one, not an oversight.
4. **The sender is told.** Silent dropping is indistinguishable from a broken server from the
   client's side; `error rate limited` is a protocol.

**The memory note to volunteer:** the stamps array is bounded by `limit`, so this is O(limit) per
client and not O(messages). For a very large limit I would switch to a counter plus a coarse bucket
ring, trading exactness for constant space.

</details>

**And the follow-up that is really about `§04 G`:** *"What if a client is slow to read?"* — that is
a different problem with the same shape, and the answer is in `§04 G`. Both are admission control;
one bounds what a client may send you and the other bounds what you will buffer for them.

**What a weak answer looks like:** a fixed window described as a sliding one · `Date.now()` read
inside the limiter, so the tests sleep · one counter shared across all clients · dropping in silence
· rate limiting `/quit`, so a throttled user cannot leave.

> **Runnable:** `discord-drills/src/drills/discord-05-rate-limit` · Spec: 8 tests

### E. A KEY–VALUE STORE OVER TCP

Deliberately **not** a chat server. If the method only works on the problem you rehearsed, it is not
a method — it is a memorised answer, and a multi-part interview is designed to find out which one
you have. There is a real chance the prompt on the 26th is not chat at all.

> **The prompt, roughly.** Build a little key–value server. Clients connect with `nc` and type
> commands, one per line. Keys can expire.

**The point of this section, in one sentence.** Layers 1 and 2 of `§04 B` — the listener and the
framing — are *character for character identical* to `§05 A`. The connection handler is identical.
The lifecycle is identical. Only `handleLine` and the state change. **That is what having a method
means**, and noticing it out loud in the room is worth saying: *"This is the same server shape as
before, with a different command table."*

<details>
<summary><strong>Model answer — the protocol layer only, because the rest is unchanged</strong></summary>

```ts
interface Entry { value: string; expiresAt: number | null }
const store = new Map<string, Entry>()

/** Lazy expiry: the only place a deadline is consulted. */
function read(key: string): string | null {
  const e = store.get(key)
  if (e === undefined) return null
  if (e.expiresAt !== null && e.expiresAt <= now()) { store.delete(key); return null }
  return e.value
}

switch (verb) {
  case 'SET': {                                  // value is the REST of the line, spaces and all
    const gap = rest.indexOf(' ')
    if (gap === -1) return send('ERR wrong number of arguments')
    store.set(rest.slice(0, gap), { value: rest.slice(gap + 1), expiresAt: null })
    return send('OK')
  }
  case 'GET':    { const v = read(rest); return send(v === null ? 'NIL' : `VALUE ${v}`) }
  case 'DEL':    { const had = read(rest) !== null; store.delete(rest)
                   return send(`DELETED ${had ? 1 : 0}`) }
  case 'EXPIRE': { const ms = Number(rest.slice(rest.indexOf(' ') + 1))
                   if (!Number.isInteger(ms)) return send('ERR value is not an integer')
                   if (read(rest.slice(0, rest.indexOf(' '))) === null) return send('NIL')
                   store.get(rest.slice(0, rest.indexOf(' ')))!.expiresAt = now() + ms
                   return send('OK') }
  case 'KEYS':   { const live = [...store.keys()].filter((k) => read(k) !== null).sort()
                   return send(live.length ? `KEYS ${live.join(',')}` : 'KEYS (empty)') }
  default:       return send('ERR unknown command')
}
```

**The three things being graded, none of which are about maps.**

1. **Lazy expiry, named as a choice.** *"I'm checking the deadline on access rather than sweeping.
   That's O(1) per read and it means a key nobody touches occupies memory forever — I'd add a
   low-frequency background sweep when dead keys start outnumbering live ones."*
2. **An error taxonomy.** Wrong arity, bad integer, and unknown verb are three different replies. A
   single `ERR` for all of them is the thing that reads as unfinished.
3. **`SET` takes the rest of the line.** Splitting on whitespace and taking `parts[1]` silently
   truncates any value with a space in it, and the bug will not show up in your own testing because
   you will type single words.

</details>

**The trade to narrate, because it *is* the answer:** *"Everything below the protocol is the same
program as the chat server — same listener, same framing, same lifecycle, same cleanup path. That's
not a coincidence; it's what the layering was for."* **That paragraph is the graded content**; the
switch statement is the setup for it.

**What a weak answer looks like:** splitting the whole line on spaces, so values cannot contain one ·
one generic error string · a `setInterval` sweeper that is never cleared, so the process will not
exit · reaching for a second data structure to track expiry when a field on the entry does it.

> **Runnable:** `discord-drills/src/drills/discord-06-kv-over-tcp` · Spec: 12 tests

### F. IF YOU GET A PROMPT THAT ISN'T ONE OF THESE

Six steps, in order, and they are the same six regardless of what the prompt turns out to be.

1. **Restate it and run one exchange by hand, out loud.** *"So A sends X, and then B should see Y."*
   If you cannot say that sentence, you do not have the problem yet, and the next forty minutes will
   be spent building the wrong thing quickly.
2. **Ask what the first line means.** Every line-protocol problem has a handshake or does not, and
   which one it is changes the state machine.
3. **Ask what happens on disconnect.** It is half the feature in every variant, and asking at minute
   3 rather than minute 40 is itself a signal.
4. **Type the plumbing anyway.** Listener, `setEncoding`, framing helper, `'error'` listener,
   `'close'` cleanup. These are the same in every problem in this family, they take four minutes,
   and you can write them before you fully understand the requirements.
5. **Name the state, then the commands.** One registry, one function per mutation, dispatch as a
   table. Say what the subset is: *"a message goes to — who, exactly?"* The answer to that question
   is the whole design.
6. **Say what part 2 would touch,** unprompted, when part 1 goes green. *"If the next thing is X,
   that's a change to the registry and the table; framing and lifecycle don't move."* If you are
   wrong about what part 2 is, you have lost nothing and demonstrated the axis anyway.

## 06 — Commands and protocol design, done properly

The protocol layer is the only part of the program that changes between parts, which makes it the
part worth having opinions about. It is also where a working answer and a good answer diverge most
visibly, because a bad protocol still passes every demonstration you would think to run.

### A. THE PARSE FUNCTION IS ONE CHOKE POINT

Three lines, written once, and every command in every part goes through them:

```ts
const sp = line.indexOf(' ')
const verb = sp === -1 ? line : line.slice(0, sp)
const rest = sp === -1 ? '' : line.slice(sp + 1)
```

**Why `indexOf` and not `line.split(' ')`.** Splitting throws away the structure you need: a value,
a message, or a room name may contain spaces, and `parts[1]` silently truncates it. The bug does not
surface in your own testing because you will type single words, and it surfaces immediately when the
interviewer types *"hello there"*. `rest` is the whole remainder, and any command that wants two
arguments splits `rest` once more, deliberately.

**Trim the line, not the rest.** `line.trim()` removes the stray whitespace a terminal contributes.
Trimming `rest` as well destroys trailing spaces inside a message, which nobody notices and which
is still wrong. `/join` trims its own argument; `/msg` does not trim its text.

### B. THE COMMAND TABLE

```ts
switch (verb) {
  case '/join': …
  case '/who':  …
  case '/quit': …
  default:      return c.send('error unknown command')
}
```

**Write the `switch` in part 1, when there is nothing to switch on.** It looks like
over-engineering and it is the difference between part 2 costing ninety seconds and costing eight
minutes. If asked, defend it exactly that way — *"I know there's one case. The reason it's a table
is that I expect to add rows, and a table absorbs rows without being restructured."*

**Two rules about which lines are commands.**

- **A leading `/` decides**, not a lookup. `/dance` is an *unknown command*, not a message that
  happens to start with a slash. Treating unmatched slash-lines as chat means a typo gets broadcast
  to the room, which is a real product bug in a real product.
- **Commands are not rate limited and are not room-scoped.** A throttled user must still be able to
  ask why and to leave; a user with no room must still be able to `/join`. Both follow from the
  command check sitting *above* those gates in `handleLine`, which is a two-line ordering decision
  worth making deliberately.

### C. ERRORS THE CLIENT CAN READ

`nc` has no client. The only feedback a human gets is the line you send back, so every rejected
input needs one — **silence is the worst possible response and it is the default one.**

| Situation | Reply | Why this one |
|---|---|---|
| Unknown verb | `error unknown command` | Distinguishes "I rejected this" from "I crashed" |
| Missing argument | `error usage: /join <room>` | Tells them the fix, which costs three words |
| Wrong kind of argument | `error value is not an integer` | A separate class from missing — the caller can act on it |
| Not allowed yet | `error you are not in a room` | State errors are not syntax errors |
| Refused by policy | `error rate limited` | The client can back off. A silent drop cannot be distinguished from a broken server |
| Name collision | `error name taken` | And the connection stays usable, so they can retry |

**One prefix, consistently.** Every error starts with the same token so a client could filter on it.
Say that out loud when you pick it: *"I'm prefixing errors so this is machine-readable as well as
human-readable — if there were a real client it would branch on that first word."*

**And never `throw` out of a handler.** An exception inside a `'data'` listener is an uncaught
exception, and an uncaught exception ends the process. Every failure in the protocol layer is a
`return c.send(...)`, never a throw.

### D. THE THREE CONNECTION STATES

Almost every variant of this problem has the same tiny state machine, and drawing it in a comment
before you write the handler is thirty seconds well spent:

| State | Entered by | What a line means | What is refused |
|---|---|---|---|
| **connected** | `net` accepts | nothing yet — the greeting has been sent | everything except naming |
| **named** | the first non-empty line | commands | messages, if the variant has rooms |
| **in a room** | `/join` | messages and commands | — |

**The transitions are the graded part, not the states.** Three specific things go wrong:

- **An empty first line names the client `""`.** `if (text === '') return` before the naming branch
  fixes it, and it is the most common single bug in this problem.
- **A refused name leaves the client in limbo.** After `error name taken`, `c.name` must still be
  `null` so the next line is another attempt. Setting it and then rolling back is how this breaks.
- **The greeting implies a state.** If you send `welcome! what is your name?` you have promised the
  next line is a name. If the variant has no handshake, do not send a prompt that says it does.

### E. THE EDGE CASES THEY WILL PROBE, RANKED

Ranked by how often reports mention them, and each is one or two lines to handle.

1. **A client disconnects hard.** `Ctrl-C`, not `Ctrl-D`. Needs the `'error'` listener and cleanup
   on `'close'`. **If only one thing on this list is handled, make it this one** — everything else
   is a missing feature, and this one is a crash.
2. **Two clients pick the same name.** A `Map` makes it a lookup; the client must stay usable.
3. **An empty line, at every stage.** Before naming, after naming, and as a message.
4. **A message before joining a room.** An explicit error, not silence.
5. **A very long line, or a line that never ends.** The cap in `§04 C`. Name it even if you skip it.
6. **A client that connects and says nothing.** It occupies a slot and a buffer forever. This is the
   sealed drill's territory, and mentioning idle timeouts unprompted is a strong close.
7. **A name with a space, or a leading `/`.** Decide out loud whether you validate or accept. Either
   is defensible; not having noticed is not.
8. **The last member leaving a room.** GC the room, or say why you are not.

### F. THE SKELETON YOU TYPE FROM BLANK

This is the artifact. Retype it from nothing twice on D-1 and once on the morning of the 26th. It is
about forty lines, it takes under four minutes with practice, and it is correct for every variant in
`§05` — including the one that is not a chat server.

```ts
import net from 'node:net'

function makeLineReader(onLine: (line: string) => void, onOverflow: () => void, maxLen = 4096) {
  let buf = ''
  return (chunk: string) => {
    buf += chunk
    let nl = buf.indexOf('\n')
    while (nl !== -1) {
      const line = buf.slice(0, nl).replace(/\r$/, '')
      buf = buf.slice(nl + 1)
      onLine(line)
      nl = buf.indexOf('\n')
    }
    if (buf.length > maxLen) { buf = ''; onOverflow() }
  }
}

interface Client { socket: net.Socket; name: string | null; send(l: string): void }

export function createServer(): net.Server {
  const clients = new Set<Client>()
  const byName = new Map<string, Client>()

  function broadcast(line: string, except?: Client) {
    for (const c of clients) if (c !== except && c.name !== null) c.send(line)
  }

  function handleLine(c: Client, raw: string) {
    const line = raw.trim()
    if (line === '') return
    if (c.name === null) { /* handshake */ return }
    const sp = line.indexOf(' ')
    const verb = sp === -1 ? line : line.slice(0, sp)
    const rest = sp === -1 ? '' : line.slice(sp + 1)
    switch (verb) {
      case '/quit': c.send('bye'); return void c.socket.end()
      default:      if (verb.startsWith('/')) return c.send('error unknown command')
    }
    broadcast(`${c.name}: ${line}`, c)
  }

  return net.createServer((socket) => {
    socket.setEncoding('utf8')
    const client: Client = {
      socket, name: null,
      send: (l) => { if (!socket.destroyed) socket.write(l + '\n') },
    }
    clients.add(client)
    socket.on('data', makeLineReader(
      (l) => handleLine(client, l),
      () => { client.send('error line too long'); socket.destroy() },
    ))
    socket.on('error', () => {})
    socket.on('close', () => {
      clients.delete(client)
      if (client.name !== null) byName.delete(client.name)
    })
  })
}
```

**What is deliberately missing:** the greeting, the handshake body, and the feature. Those are the
three things that depend on the prompt. Everything above is the same every time — which is exactly
the claim `§04 A` makes, expressed as a file you can produce from memory.

## 07 — Correctness with two terminals and no test runner

There is no `npm test` in this round. Nothing stops you writing one — and if you have twenty spare
minutes, a test file is a strong signal against the *"well abstracted such that it could be tested"*
axis — but you will not have twenty spare minutes, and a half-written test suite is worse than a
demonstrated program. So the primary tool is two terminals, used deliberately.

### A. ASK FIRST

Before minute 6: *"Would you rather I write a test or two as I go, or drive it by hand with `nc` and
keep the time in features?"* Some interviewers have a strong preference and all of them will tell
you. If they have no preference, **drive it by hand and write one test at the end if there is time**
— because the demonstration is what proves functionality, which is the first axis, and a test proves
it only to you.

### B. THE THREE-TERMINAL RITUAL

Run this after every feature, not at the end. It takes fifteen seconds once the panes are arranged
and it catches the whole class of bugs that only appear with two clients.

1. Restart the server. **Every time** — a stale process is the source of the most confusing bug in
   this exercise, because your new code is not the code that is running.
2. `nc localhost 8080` in both client panes.
3. Name them, watching that each sees what it should and nothing it should not.
4. Send from A. Confirm B received it **and that A did not**.
5. `Ctrl-C` in A. Confirm B is told, and confirm the server is still running.
6. Reconnect A. Confirm the name is free again.

**Step 4's second half is the one people skip**, and no-self-echo is the single explicitly stated
requirement in the reported part 1. Watching your own message not appear is the demonstration.

### C. THE SCRIPTED CLIENT YOU TYPE IN SIXTY SECONDS

When clicking between panes gets slow — and it will, around the time rate limits or history appear —
this pays for itself immediately:

```ts
// client.ts — usage: node client.ts 8080 alice hello "how are you"
import net from 'node:net'

const [, , port, name, ...lines] = process.argv
const s = net.createConnection({ port: Number(port) }, () => {
  s.write(name + '\n')
  lines.forEach((l, i) => setTimeout(() => s.write(l + '\n'), 100 * (i + 1)))
})
s.setEncoding('utf8')
s.on('data', (d) => process.stdout.write(d.split('\n').filter(Boolean).map((l) => `[${name}] ${l}\n`).join('')))
s.on('error', (e) => console.error(`[${name}] ${e.message}`))
```

**Two things it buys beyond speed.** It sends thirty messages in three seconds, which is how you
demonstrate a rate limiter without waiting a minute. And it prefixes every received line with the
client's name, so one pane shows you the whole conversation from every side at once — which makes an
ordering bug visible instead of inferable.

**Say why you are writing it:** *"I'm going to spend a minute on a scripted client, because I'm
about to need to send faster than I can type and I'd rather see the ordering than reason about it."*
Building a tool to test your own work is *resource use*, which is a named axis.

### D. THE WORKED-EXAMPLE TABLE

Before writing the handler, put this in a comment. It is thirty seconds, it is the thing you check
against at minute 30, and it doubles as the script for the closing demonstration.

```ts
// A connects, names alice        → A: "you are alice"
// B connects, names bob          → B: "you are bob"      A: "* bob joined"
// A sends "hi"                   → B: "alice: hi"        A: (nothing)
// B sends "/who"                 → B: "who: alice, bob"  A: (nothing)
// A hits Ctrl-C                  → B: "* alice left"     server: still running
// C connects, names alice        → C: "you are alice"    (the name was freed)
```

**Test invariants, not examples, when you get to it.** *"No client ever receives its own message"*
is checkable at every step of the table; *"B receives `alice: hi`"* is checkable once. When an
interviewer adds a part, the invariant survives and the example does not.

### E. NC AND TELNET GOTCHAS

Every one of these has cost somebody ten minutes.

| Symptom | Cause | Fix |
|---|---|---|
| `nc: Address already in use` on start | The previous server is still running | `lsof -ti:8080 \| xargs kill` — have this in your history before the call |
| The client connects and immediately exits | You typed `nc -l 8080` — that *listens* | `nc localhost 8080` connects |
| Everything you type appears twice | Your server is echoing, and the terminal already echoes locally | Do not echo. The requirement says not to |
| Nothing arrives until you press Return | The terminal is line-buffered, which is correct | Nothing to fix. This is why the protocol is line-based |
| The server logs a line with a trailing `\r` | The client is PuTTY in raw mode, or a Windows tool | The `.replace(/\r$/, '')` in `§04 C` |
| Garbage bytes on the very first line, only with `telnet` | Telnet sends option negotiation — `0xFF` command sequences — before any data | Ignore lines containing `\xff`, or ask the interviewer to use `nc`. Worth knowing exists; not worth implementing |
| The server dies when a client quits | No `'error'` listener on the socket | `§04 F`. One line |
| A message from a fast client arrives glued to the next | You are not framing | `§04 C` |
| `Ctrl-C` and `Ctrl-D` behave differently | They are different: `Ctrl-C` kills `nc` (reset), `Ctrl-D` sends EOF (FIN) | Handle both. `'close'` covers both, which is why cleanup lives there |

**Knowing the last row out loud is a cheap, specific signal:** *"`Ctrl-D` sends a FIN so I get
`'end'` then `'close'`; `Ctrl-C` kills the client so I get a reset — `'error'` then `'close'`. That's
why the cleanup is on `'close'` and the `'error'` handler does nothing but exist."*

## 08 — Typing fluency with AI off

### A. WHAT DEGRADES, AND WHY IT MATTERS HERE

This round is unusually sensitive to typing fluency, for a reason worth being precise about: the
program has **a large fixed cost and a small variable cost**. Roughly forty lines are the same
regardless of the prompt, and the interesting work is the twenty lines on top. If the fixed forty
take you eighteen minutes, you have spent a quarter of the round on the part that carries no signal
at all — and you will reach one part instead of two, which is the difference the score is made of.

With completion on, the fixed forty are nearly free and you have not noticed how long they take
unaided. **Time yourself once, today.** `§06 F` from blank, no AI, no reference. If it is over six
minutes, that number is the highest-leverage thing in your whole seven days.

### B. THE RETYPE KIT

Five things, from blank, no reference, until they are boring. Ten minutes a day is enough.

| # | What | Target |
|---|---|---|
| 1 | The framing helper from `§04 C` | 60 seconds, correct on the first run |
| 2 | The skeleton from `§06 F`, whole | Under 4 minutes |
| 3 | The `Client` interface and the three registry functions from `§04 D` | 90 seconds |
| 4 | The scripted client from `§07 C` | 60 seconds |
| 5 | `mkdir`, the two setup commands, `server.ts` from blank, `node server.ts`, two `nc` clients | 90 seconds, from an empty directory |

**Number 5 is not padding.** The environment is yours on the 26th, which means an environment
failure is yours too, and it happens in the first five minutes when it is most expensive.

### C. NODE ERGONOMICS THAT SAVE KEYSTROKES

| Instead of | Type | Saves |
|---|---|---|
| A build step, or `tsx` | `node server.ts` — Node 23.6+ runs `.ts` directly | No install, no config, and restart is one up-arrow and Return |
| `const x = new Map(); x.set(...)` guards | `let s = m.get(k); if (!s) m.set(k, (s = new Set()))` | The get-or-create in one statement |
| `Array.from(set).map(...)` | `[...set].map(...)` | Consistently shorter, and reads better in a `.sort()` chain |
| `if (a) { b(); return }` | `if (a) return b()` | Every dispatch row becomes one line, which is what makes the table readable |
| Optional chaining you have to remember | `for (const m of rooms.get(r) ?? [])` | An unknown room iterates zero times instead of throwing |
| `socket.write(x + '\n')` everywhere | `send` on the `Client` | The one change that makes `§04 G` two lines |

**And two TypeScript notes for a round where the compiler is not the point.** Use `!` freely on
things you have just checked (`m.name!` inside a filter on `name !== null`) rather than restructuring
to please the checker — say *"I'd tighten that type if this were real"* and move on. And do not
reach for generics. Nothing here needs them, and reaching for them under time pressure is how you
end up debugging a type instead of a program.

### D. WHAT TO HAVE OPEN, AND WHAT TO LOOK UP

The browser is allowed. Use it, visibly, and use it for the right things.

**Have open before the call:** `nodejs.org/api/net.html`, and nothing else. One tab. A wall of tabs
on a shared screen reads as a wall of tabs.

**Worth looking up in the room, out loud:** the exact return semantics of `socket.write` · which
events a `Socket` emits and in what order · anything about `StringDecoder` if multi-byte comes up.
All three are *"I want to check this rather than guess"*, which is a named axis.

**Not worth looking up, because you should have it:** how to create a server · how to read from a
socket · how to split a string. Looking these up mid-round is not penalised, but it is thirty seconds
each and there are a lot of them, and it is exactly what `§08 B` exists to remove.

## 09 — "Now scale it past one process"

### A. THE QUESTION AS ASKED

It arrives near the end, it is discussed rather than coded, and it is reported often enough to
prepare for. It usually sounds like *"suppose this needed to handle a million people — what
changes?"*

**The trap is treating it as a system design round.** It is three minutes, it comes after you have
been in the weeds for an hour, and a fifteen-minute architecture answer reads as not knowing what
was asked. Give the compressed answer, name the one thing that actually breaks first, and offer to
go deeper.

### B. THE THREE-MINUTE ANSWER

> *"The thing that breaks first isn't throughput, it's that the registry is in this process's
> memory. Two clients in the same room on two different servers can't see each other, so the
> registry has to come out.*
>
> *So: a pub/sub backbone between the nodes — Redis pub/sub or NATS — where a node publishes a
> room's messages to a channel and subscribes to the channels for the rooms its own clients are in.
> Fanout inside a node stays the loop I already wrote; fanout across nodes becomes one publish.
> Presence — who is online and where — moves to a shared store with a heartbeat TTL, so a node
> dying expires its clients instead of leaving them online forever.*
>
> *Connections are long-lived, so load balancing is by connection, not by request — you place a
> client once and it stays. That means a deploy drops every connection on a node at once, so I'd
> want reconnect with backoff and jitter on the client, and drain rather than kill on the server.*
>
> *What breaks next, and it's the interesting one: a very large room. Fanout is linear in members
> however you slice it, so one message to a hundred thousand people is a hundred thousand writes
> somewhere. That's where you stop treating rooms uniformly and give the big ones dedicated
> fanout."*

**Four beats in there, and they are the graded ones:** you named what breaks *first* rather than
listing components · you kept the in-process loop and added a layer rather than replacing the design
· you noticed that long-lived connections change deploys, which is the thing that separates people
who have run a socket service from people who have read about one · and you named the second-order
failure, the hot room, unprompted.

### C. WHERE IT POINTS

`Design Discord` under Designs is the full treatment — gateway and connection registry, guild fanout
and the session-per-process model, and message storage. Read it if the loop continues; do not
rehearse it for the 26th, because three minutes is what this question gets and the rest of the hour
is worth more.

## 10 — Discord, enough to be credible

Half an evening, on D-2, after the mock. Not before — this is the lowest-leverage chapter in the
guide and it is the one that feels most like productive work, which is a bad combination.

### A. PRODUCT SURFACES TO TOUCH BEFORE THE 26TH

If you do not use Discord daily, spend twenty minutes in it. Make a server. Make a channel, then a
thread off a message. Set a status. Join a voice channel and notice how fast it connects and that it
does not have a "call" concept — presence is ambient rather than an event. Look at how a message
edit propagates, and at read state: what unread means when you have been away for a day.

**Why this and not the marketing site:** every one of those is a data-modelling decision you could
be asked to reason about, and each has an obvious naive design that Discord did not choose.

### B. THE ENGINEERING STORY, IN THREE PARAGRAPHS

All of this is from their public engineering writing, and it is unusually good writing — they
publish mechanism and numbers rather than diagrams.

**Elixir on the BEAM, for the real-time half.** A guild — a server, in product language — is its own
lightweight process, so one busy or crashing community cannot take down the millions of others. That
is the same isolation argument as one connection handler per socket, at a different scale, and it is
worth being able to say out loud because it is the direct large-scale version of the thing you built
in the exercise.

**Rust where the BEAM ran out.** When CPU-bound work hit a ceiling, they extended Elixir with Rust
through NIFs rather than rewriting — a sorted-set implementation for the hot path, keeping Elixir
for concurrency and Rust for the parts where garbage collection pauses showed up in the tail. The
same reasoning drove a Go service to Rust: the problem was not throughput, it was GC pause latency
at p99.

**Cassandra, then ScyllaDB, and a coalescing layer in front.** Messages went MongoDB → Cassandra →
ScyllaDB, with Java GC pauses at trillions-of-messages scale being the reason for the last move; the
cluster went from 177 Cassandra nodes to 72 ScyllaDB ones. **The detail worth remembering** is the
Rust data-services layer in front: when a hot partition is requested by a huge number of clients at
once, it recognises them as the same request, issues **one** query, and fans the single result back
out to every waiter. That is exactly the shape of the thing you wrote in `§05 A` — many waiters, one
source, one fanout loop — which makes it the natural thing to mention if scaling comes up.

### C. QUESTIONS TO ASK THE INTERVIEWER

Two or three, at minute 71. Ask about the work, not the perks.

- *"This exercise is clearly built out of something real. What's the version of it you actually run
  into?"* — the invitation says the problems come from real work, so this lands, and the answer is
  usually genuinely interesting.
- *"Where's the line between Elixir and Rust now? Is it still 'Rust where GC pauses show up', or has
  it moved?"* — specific, shows you read primary sources, and is a real open question.
- *"What does on-call look like for a service where every client holds a connection open? Deploys
  seem like the hard part."* — this comes straight out of `§09 B` and shows the round's thinking
  continued past the round.
- *"What would I be working on in the first three months?"* — always worth asking, always answered.

**Do not ask** anything answerable from the careers page, and do not ask how you did.

### D. WHY DISCORD, ANSWERED FROM THE ENGINEERING

Answer it with the thing you can actually defend rather than an affinity claim: **it is one of a
small number of consumer products where the hard problem is real-time state at scale, and they
publish enough about it to know that before joining.** Then name a specific: the coalescing layer,
or the Go-to-Rust move being about tail latency rather than throughput. Specificity is the whole
answer here — *"I love the product"* is what everyone says, and it is not checkable.

*Flagged as medium confidence:* the exact wording of Discord's stated company values moves around.
If you want to reference them, read the current careers page the night before rather than quoting
anything from memory.

## 11 — The drills, and how to run them

Seven drills, in `discord-drills`, one directory each. Red by default — every stub fails, and that
is the artifact. `npm run solutions` runs the references and must be fully green.

### A. THE PROTOCOL

Non-negotiable, because a rep run loosely measures nothing and still costs the time.

1. **AI off at the settings level.** Not the keybinding level.
2. **Start the timer before you open the file.** Reading the prompt is part of the round.
3. **Narrate out loud, alone.** It is a motor skill, and it is graded on the 26th.
4. **Parts in order, on one clock.** Never restart the timer between parts.
5. **Un-gate the next part only when the previous is green, without stopping the clock.** That
   transition *is* the drill — it is the refactoring axis, and it is the only way to find out
   whether your part 1 was shaped right.
6. **Stop when the timer stops**, mid-line if that is where you are.
7. **Self-grade with `§03 G` before reading anything.** Then read the matching `§05` section.

### B. THE SEVEN

| Slug | Min | What it drills | Why it is on the list |
|---|---:|---|---|
| `discord-01-broadcast-chat` | 30 | accept, name-on-first-line, broadcast to others, no self-echo, clean disconnect | The reported part 1, near verbatim. `§05 A` |
| `discord-02-rooms-and-commands` | 35 | `/join` `/rooms` `/who` `/msg` `/quit`, room-scoped fanout, empty-room GC | The reported part 2. Graded on whether part 1 had to be reopened. `§05 B` |
| `discord-03-framing-torture` | 20 | split lines, coalesced lines, `\r\n`, a no-newline flood, a split emoji | Pure `§04 C`, no chat logic. The spec writes bytes directly |
| `discord-04-history-and-reconnect` | 30 | a ten-message ring, replay on join, rejoin by name | The most common part 3. Two lifetimes, one leak you name. `§05 C` |
| `discord-05-rate-limit` | 30 | a sliding window on an injected clock, per-client budgets, `/stats` | The other common part 3, and the cheapest code-quality signal. `§05 D` |
| `discord-06-kv-over-tcp` | 30 | `SET`/`GET`/`DEL`/`EXPIRE`/`KEYS`, lazy TTL, an error taxonomy | Off-theme on purpose. `§05 E` |
| `discord-07-sealed` | 75 | — | **Do not open before D-2.** This is the mock |

**How to run one:**

```bash
cd ~/projects/discord-drills
npm run test:watch                                   # while you work
npx vitest run src/drills/discord-01-broadcast-chat  # one drill
npm run solutions                                    # the references, after you have graded
```

And by hand, which is closer to the real thing and worth doing at least once per drill:

```bash
npx tsx -e "import('./src/drills/discord-01-broadcast-chat/server.ts').then(m => m.createServer().listen(8080))"
nc localhost 8080     # in two more panes
```

### C. THE FULL MOCK (D-2, MON 8/24)

`discord-07-sealed`, at **12:00 noon**, in the real slot, for the real 75 minutes. Its prompt is one
you have not seen and will not have practised, which is the entire point — drills 1 through 6 build
the reflexes and cannot measure whether the reflexes transfer.

Run it exactly as the round: environment set up beforehand, three panes arranged, timer started
before the file is opened, narrated out loud from the first second, no AI, no reference, stop when
the clock does. Then the closing summary out loud, then `§03 G`, and only then the solution.

**If you score below 75, do not re-run drill 7.** Re-run whichever earlier drill the lost points
point at — sub-75 on the mock is almost always the framing helper or the part boundary, and both
have a dedicated drill.

## 12 — Day-of runbook

### A. THE NIGHT BEFORE (TUE 8/25)

- **Turn Copilot off at the settings level.** Verify by opening a file and typing a function header.
- Verify the environment from scratch, exactly as `§01 E`: new directory, `server.ts` typed from
  blank, `node server.ts`, `nc` in two panes, `echo: hello` comes back. Ninety seconds, and it is
  the only failure mode you can fully eliminate in advance.
- `nc localhost 8080` against a throwaway server, both panes. Confirm `Ctrl-C` and `Ctrl-D` behave
  as `§07 E` says.
- Retype `§06 F` from blank, twice. Time the second one.
- Put `lsof -ti:8080 | xargs kill` in your shell history.
- Arrange the panes as `§01 E`, and leave them arranged.
- Read `§01 G` and `§03 A`. Nothing else. **No new material.**
- Sleep. This is a midday interview, which is the easy one to be rested for.

### B. THE HOUR BEFORE

- Retype the framing helper once, from blank. One minute. It is a warm-up, not a study session.
- Open exactly one browser tab: `nodejs.org/api/net.html`.
- Close everything else — Slack, mail, anything that can produce a notification on a shared screen.
- Reread `§03 B` — the opening — and say the first two sentences out loud once.
- Join five minutes early.

### C. THE FIRST FIVE MINUTES

- Restate the problem and **run one exchange by hand, out loud**. Do not type.
- Ask the three questions in `§03 B`. The third one — *"one room, or should I be thinking about more
  than one?"* — is the one worth waiting for the answer to.
- Say the plan in one sentence, including when you will next be talking to them.
- **Then get an empty server listening and `nc` attached before any logic.**

### D. THE MIDDLE

- Framing helper and registry before any feature. Four minutes, from memory.
- Narrate every non-obvious choice **at the moment you make it**, not when asked.
- Demonstrate after each feature, with two clients, including the thing that should *not* happen.
- **When they add a part, say what it touches before you type.** Ten seconds. `§03 D`.
- If you are stuck for more than sixty seconds, print the raw bytes with `JSON.stringify`.
- If something needs looking up, say so and look it up. It scores.

### E. THE LAST TEN MINUTES

- **At minute 66, stop coding**, wherever you are.
- Restart the server and run the demonstration end to end — join, message, no self-echo, disconnect,
  survive.
- Give the close in `§03 F`: where you got to, what you would do next in priority order, the real
  bug you know about, and the assumption you made.
- Ask two of the questions from `§10 C`.

### F. AFTERWARDS

Write down, within ten minutes and before you forget: the prompt as stated, what each part was and
when it arrived, every follow-up question, and the two places you lost time. That page is worth more
than anything else you could do that afternoon — and Cursor is on Friday, so the next thing after
writing it is to close this guide and open `Cursor Screen`.

Good luck. The preparation is real: seven drills with seventy-nine tests behind them, a framing
helper you can type in sixty seconds, and a mock on the real clock in the real slot. Walk in and do
the thing you have practised — get it listening, ask before you build, decide out loud, and leave
time to show it working.
