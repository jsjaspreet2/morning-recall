# Final Loops — OpenAI & Discord

Updated September 25, 2026. **Active targets: OpenAI and Discord. Figma prep is archived.** Dates and exact round breakdowns have not yet been supplied for these finals. The plan below is a seven-day allocation, not a claim about either company's interview schedule. Put the nearer loop's work first when dates are confirmed.

## 01 — Where the next hour goes

**Finish a working implementation, close a design, and explain your own decisions.** The library already covers more architectures than a final week can absorb. The September mock reviews recorded a narrower gap: too long on low-load paths, unfinished failure handling, and missed interviewer steering. That makes the [system design round card](#/learn/system-design-card) the first reread, ahead of another technology survey.

Use roughly **60 minutes coding + 45 minutes design + 25 minutes project/behavioral discussion + 20 minutes review** each day. This is a 150-minute default; a mock replaces its corresponding block. If only 90 minutes are available, use 40/30/20 and drop optional coverage. Keep the project block: the existing library is much stronger on implementation than on explaining Staff-level impact.

OpenAI's [official guide](https://openai.com/interview-guide/) describes team-dependent assessments and typically 4–6 hours of finals, while emphasizing testing, reasoning, communication, and collaboration. It does not publish a Top 20 question ranking. Tool permissions vary by interview. The recruiter packet takes precedence over the old screen guides and all candidate reports.

For both companies, confirm the round names and duration, coding language/environment, permitted tools, design scope, and whether a project presentation is expected. Until then, treat debugging, concurrency, and component work as useful coverage, not confirmed standalone rounds. Discord's line-server material is prior-screen preparation; it does not establish the final-loop format.

## 02 — OpenAI: integrate the Top 20 without spending the whole week on it

The [OpenAI Coding Top 20](#/learn/openai-coding) preserves all twenty numbered problems and TypeScript examples from the supplied sheet, with corrected examples and explicit contracts. The order below is a preparation judgment based on transferable skills, not reported question frequency.

**Core builds:** #1 LRU → #3 resumable iterator → #4 transactional DB → #5 versioned KV/TTL → #6 rate limiter → #7 path resolution → #8 spreadsheet → #10 scheduler. These cover mutable state, serialization, time, rollback, dependencies, and incremental extensions. In one hour, finish one base implementation with tests and one follow-up; do not attempt three complete systems.

**Supporting patterns:** #11 peeking and #12 nested iterators support #3; #13 simplify path supports #7; #14 topological sort supports #8; #15 merge-k and #17 top-k support heap fluency; #16 intervals, #18 sliding windows, #19 anagrams, and #20 weighted choice fill narrower gaps. Use the matching [Coding Patterns](#/learn/coding-patterns) chapter only when the implementation exposes a weakness.

**Defer until the core works:** #2 LFU and #9 bounded queue. LFU adds bookkeeping; the queue adds async coordination. Neither should displace an unfinished LRU or iterator. Elevate the queue if the confirmed loop includes concurrency. An async JavaScript queue is not evidence of shared-memory thread safety.

Retain the frontend differentiator. Revisit the [transcript walkthrough](#/learn/openai-transcript), [OpenAI screen reference](#/learn/openai-screen) §§05, 08–10, and [Client-Side System Design](#/learn/client-side-system-design) §§01–02. The important cases are split input chunks, duplicate/out-of-order events, stale work after cancellation, reconnect, and bounded rendering. A small-system coding sheet supplements this coverage; it does not replace it.

For design, start with [ChatGPT](#/designs/chatgpt) and [Distributed rate limiter](#/designs/rate-limiter). Then choose **one** of [Job scheduler](#/designs/scheduler), [Sandboxed notebooks](#/designs/sandbox), or [Cursor Tab](#/designs/cursor) according to team scope or the weakness in your latest mock. The old PracHub hearts ranking is a popularity snapshot, not an interview probability estimate.

## 03 — Discord: move beyond the passed screen

Discord's packet arrived 9/26: the final is Monday 9/28, five rounds in one day, and the round-by-round 48-hour plan is [Discord — Final Round, 48 Hours](#/learn/discord-final). This section stays as the longer-horizon track.

Start with [Discord Final Round](#/learn/discord-screen) §01 C/F/G, §03, and §04: byte framing, cleanup on every exit path, backpressure, protocol errors, and demonstrating correctness. Preserve the ability to extend a working server, but do not spend the entire week rebuilding the screen.

Pair that with [Design Discord](#/designs/discord) §§06–12 and the [Slack/messaging design](#/designs/messaging). Explain the boundary between durable message acceptance and best-effort live fanout; then reconnect, history recovery, a hot channel, slow consumers, presence expiry, and authorization. The shared question is what the client observes when a process dies between accepting a message and delivering it.

Use [Client-Side System Design](#/learn/client-side-system-design) §01 for optimistic state and reconciliation. If the packet names a UI round, add [Component Round](#/learn/component-round), [UIE Components](#/learn/uie-components), and the relevant accessibility contract. A prior server-side screen is not a reason to assume the final contains no client work.

For the project discussion, connect engineering choices to community experience: reliability during busy events, moderation/privacy boundaries, and the cost of keeping many clients current. Use a project you actually shipped; explain the decision and measured effect rather than borrowing Discord's scale as your own experience.

## 04 — Seven days, 2½ hours per day

Each day includes a 20-minute review of the actual failure or unfinished piece. The 25-minute story block rotates through the material in §05. Adjust the order for the nearer loop; do not add every optional branch on top.

1. **Baseline and caches.** Coding: #1 LRU, tests for eviction and overwrite, then TTL if time remains. Design: one 35-minute attempt on ChatGPT plus 10 minutes checking the round card. Story: flagship project's problem, constraints, and your decision. Use the result to choose the weakest core build next.
2. **State and restart.** Coding: #3 resumable iterator with empty sources, snapshot/restore, and exhaustion; use #11/#12 only as warm-ups if needed. Design: ChatGPT run lifecycle and reconnect from the persisted log. Story: a difficult design choice and the alternative you rejected.
3. **Transactions or time.** Coding: #4 nested transactions **or** #5 historical KV/TTL, whichever is weaker; the other becomes the Day 7 option. Design: rate limiter, covering hot keys and the cost of strict global limits. Story: an incident, mitigation, and the change that prevented recurrence.
4. **Discord end to end.** Coding: extend the line server with room membership/history or rate limiting (#6); include split frames, disconnect cleanup, and a slow client. Design: Discord fanout and recovery. Story: disagreement across teams, the decision, and what you did after it was made.
5. **Dependencies or paths.** Coding: #8 spreadsheet **or** #7 symlink resolution. Use #14/#13 as a short warm-up only if necessary. Design: scheduler or sandbox, with state transitions and failure recovery. Story: ambiguous ownership, how you narrowed scope, and how others could execute without you.
6. **Debugging and the client.** Coding: trace one deliberately broken earlier implementation, then implement a bounded extension such as #10 scheduling; if UI is confirmed, use the transcript walkthrough instead. Design: client reconciliation and cancellation, tied to a server contract. Story: a failure, the feedback you received, and a specific change in behavior.
7. **Two realistic sessions.** Coding: a 60-minute mock on the deferred Day 3 or Day 5 build with an added requirement. Design: a 45-minute mock for the nearer company. Story: 25 minutes of project explanation and company motivation. Review: 20 minutes repairing the single largest failure. Do not cram all remaining classics into this day.

If a design mock scores below the existing round-card threshold, repeat that architecture next time before adding a new one. A working baseline that survives a follow-up is a better use of the last hour than reading another full solution. The score is a personal diagnostic, not a hiring prediction.

## 05 — The missing final-loop coverage: project depth and collaboration

Prepare one flagship project as a two-minute overview and a ten-minute technical explanation. Use this sequence: user problem → constraints and scale → your scope → alternatives → decision → rollout → measurable result → what you would change. Separate team output from your own contribution. Use actual metrics; if you lack a measurement, say what evidence you do have.

The technical explanation should include one diagram, the critical data path, one rejected alternative, one failure mode, and how the rollout made it safe to learn. A Staff-level account also explains how you aligned stakeholders, divided ownership, mentored others, and reduced future coordination cost. Avoid describing influence only as attendance at meetings.

Have concrete examples of disagreement, a production incident, ambiguous scope, feedback that changed your behavior, and a project that did not work. These can overlap with the flagship project, but each needs a distinct decision and consequence. Keep the first answer short enough to leave room for follow-ups. In a live interview, pause and let the interviewer speak; the self-interviewer technique in solo mocks is only for solo rehearsal.

For OpenAI, explain the connection between the team's work and your own interests, plus a concrete product tradeoff involving reliability, privacy, safety, latency, or cost. For Discord, explain how a technical choice affected the experience of people using a community product. Read a recent team-relevant primary source before the interview and connect it to your experience; avoid memorized company slogans.

## 06 — Content pass: what to revisit, selectively consult, or defer

### Revisit first

- **[System Design Round](#/learn/system-design-card):** pacing, receiving hints, state transitions, failure closure, and the minute-35 audit. Highest shared priority given the recorded mock gaps.
- **[Data Modeling Under Pressure](#/learn/data-modeling):** §§02–05, then the model relevant to the chosen design. Write keys, access paths, uniqueness, retention, and hot partitions before naming a database.
- **[System Design](#/learn/system-design):** the timed loop, correctness/failure sections, and closing check. Use targeted sections after mocks instead of a cover-to-cover reread.
- **[Client-Side System Design](#/learn/client-side-system-design):** §§01–02 and §04. Transfers to both companies through reconnect, stale responses, optimistic state, and meaningful tests.
- **[JavaScript](#/learn/javascript):** §§03–04 and §08. Collections, async ordering, cancellation, and bounded concurrency directly support both coding tracks.
- **Company material:** OpenAI Top 20 and transcript for implementation; Discord §§01–04 for framing/lifecycle/protocol correctness. Old screen schedules are historical.

### Consult when a round or a failed attempt calls for it

- **[Coding Patterns](#/learn/coding-patterns):** maps, binary search, heaps, topology, and intervals. Broad DP/backtracking revision is secondary unless your confirmed round or baseline exposes that gap.
- **[React & CSS](#/learn/react-css):** §§02–06 for identity, effects, async races, and streaming; CSS layout when a UI build is confirmed.
- **[Component Round](#/learn/component-round) + [UIE Components](#/learn/uie-components):** the round clock, streaming-message component, async tests, prop contracts, and `useChat`. Skip a tour of all fourteen components.
- **[Accessibility](#/learn/accessibility):** focus, keyboard interaction, accessible naming, and live-region behavior for the surface being built.
- **[Technology Choices](#/learn/technology):** look up a specific decision from the current design, especially Postgres, Redis, Kafka, SSE, and WebSocket. A technology recital does not close a design.
- **[Animation & Motion](#/learn/animation):** reduced motion and keeping streaming updates responsive only when relevant. The full motion catalog is lower priority this week.

### Designs: narrow the library to a few useful contrasts

**First:** [Interview mechanics](#/designs/interview-mechanics), [Discord](#/designs/discord), [Slack](#/designs/messaging), [ChatGPT](#/designs/chatgpt), and [rate limiter](#/designs/rate-limiter). Read the complete flow once; focus later reading on the weakness observed in an actual attempt.

**Next, by need:** [scheduler](#/designs/scheduler), [sandbox](#/designs/sandbox), and [Cursor Tab](#/designs/cursor) for jobs, isolated execution, or inference latency. [Deployment](#/designs/deployment), [demand response](#/designs/demand-response), and [telemetry](#/designs/telemetry) are valuable specifically for correcting the recorded reconciliation, time-allocation, and ingestion gaps. Choose one, not all six.

**Defer unless team scope demands them:** [Uber](#/designs/uber), [Ticketmaster](#/designs/ticketmaster), [Airbnb](#/designs/airbnb), [feed](#/designs/feed), [settings sync](#/designs/settings-sync), [CI/CD](#/designs/cicd), [checkout](#/designs/checkout), [billing](#/designs/billing), and [payment processor](#/designs/payment-processor). These remain useful archetypes; they are a poor default use of a limited final week. Figma prep and its collaborative-editor design are archived and remain accessible as references.

## 07 — Guide maintenance priorities

**Addressed in this pass:** a current final-loop entry point; all twenty supplied coding examples integrated with priorities and correctness notes; Figma archived; historical OpenAI screen dates labeled; Discord linked to broader final-loop coverage; and the round card clarified so low throughput does not excuse ignoring critical correctness work.

**Next useful updates:** tailor this plan to the recruiter packets; add a real project walkthrough using your actual decisions and metrics; and turn the next mock's largest miss into a small amendment to the relevant section. Those would improve preparation more than another generic architecture page.

**Editorial debt to revisit:** older company guides make confident claims from candidate reports (including “every” question and ranked probabilities). Read those as practice coverage, not guarantees. Root guide mirrors and older downloadable PDFs also warrant a separate parity audit before treating a PDF as the current version. This pass syncs the guides it changes; it does not certify every historical PDF or every code block elsewhere in the library.
