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

### E. YOUR OWN MACHINE: THE FIRST NINETY SECONDS

Unlike a CoderPad round, the environment is yours and the setup cost is refundable in advance. Do
this once now and once more on D-1 so it is stale-proof:

```bash
mkdir -p ~/interviews/discord && cd ~/interviews/discord
npm init -y && npm i -D typescript tsx @types/node
npx tsc --init
printf 'console.log("ok")\n' > server.ts
npx tsx server.ts        # must print ok. If this errors on the 26th you have lost five minutes
```

Then arrange the screen **before** the call, because rearranging terminals while someone watches
reads as unpreparedness:

| Pane | Holds | Why |
|---|---|---|
| Left, large | The editor on `server.ts` | The thing being graded |
| Right, top | `npx tsx server.ts` | Restarted constantly. Keep it on its own pane so the scrollback stays readable |
| Right, middle | `nc localhost 8080` — client A | |
| Right, bottom | `nc localhost 8080` — client B | **Two clients from minute one.** A one-client demo cannot show broadcast, which is the whole feature |

**The ninety seconds themselves,** once the problem is stated: confirm the run command still works,
confirm the port, and say what you are about to do. *"I'm going to get an empty server listening
and connect to it with `nc` before I write any logic, so we both know the plumbing works."* That
costs ninety seconds and it buys the rest of the hour — every subsequent bug is a logic bug, which
is a bug you can reason about, rather than an environment bug, which is a bug that eats ten
minutes and your composure.

**Have `nc` in your fingers.** `nc localhost 8080` connects. `Ctrl-C` kills the client hard,
`Ctrl-D` sends EOF, and they produce different events on the server — `§07 E` has the table, and
knowing the difference out loud is a cheap signal.

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

type LineSink = (line: string) => void

/**
 * Chunks in, lines out. The only function in the program that knows about `\n`.
 * Nothing above this layer should ever see a partial line, and nothing below it
 * should ever see a command.
 */
function makeLineReader(onLine: LineSink, onOverflow: () => void, maxLen = 4096) {
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
`net` so the import is unambiguous. Run with `npx tsx server.ts` rather than a build step, so
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
the entire Node process. So a client that hits `Ctrl-C` at the wrong moment produces an ECONNRESET
that kills your server, in front of the interviewer, while another client is connected. It looks
like a crash caused by nothing. It is the highest-frequency way this exercise goes visibly wrong,
and it is one line.

**Put cleanup on `'close'`, not `'end'`,** because `'close'` is the only event that fires on every
path — clean FIN, reset, error, and your own `destroy()`. Cleanup on `'end'` means a client killed
with `Ctrl-C` leaves a stale entry in the registry, and the symptom is a ghost: `/who` lists someone
who left, and broadcasting to them throws later, somewhere else entirely.

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
