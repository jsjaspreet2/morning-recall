# OpenAI PIL — Offline Onsite Field Guide

Prepared September 30, 2026 for a Staff role. **Start here for the current onsite.** The recruiter says the coding interview will primarily emphasize UI. That changes the preparation order: complete a usable interface quickly, explain its state and failure behavior, then carry those same decisions through the full stack. The older September screen schedules and the generic Top 20 list are references, not the current plan.

This page combines the supplied six-page **PIL Onsite Interview Prep Doc – FS**, the supplied travel setup handoff, authenticated 1point3acres reading, and original learning material. It does not reproduce a purchased problem bank. Recommendations and example designs below are preparation judgments, not predictions of your interview.

## 01 — What is actually confirmed

The recruiter packet is the strongest source for the loop. Its coding section lists general coding and refactoring; your recruiter's more specific UI guidance sets the emphasis. It also explicitly grades interpretation of a mockup. The permitted framework, exact editor setup, AI-tool policy, and interview date remain unconfirmed. Practice in React/TypeScript locally, but verify the actual environment before the interview.

| Module | Packet duration | Preparation consequence |
|---|---|---|
| Technical deep dive | 45 minutes | Slides required; at most 12 recommended. Explain one project deeply, including your decisions, impact and lessons. |
| Coding | 60 minutes | Working behavior, correctness, readable code, prioritization, mockup interpretation and testing. Include some code-reading/refactoring preparation. |
| System design / architecture | 60 minutes | End-to-end frontend and backend, even for a frontend-leaning candidate. Expect mockup-to-product reasoning and follow-ups in your strongest area. |
| Decomposition | 45 minutes | Customer role-play: 10 minutes scoping, 20 whiteboarding, 10 presenting back. The listed activities total 40 minutes; leave the remaining five as buffer. |
| Hiring manager | 45 minutes | Specific examples of judgment, contribution, growth, values and long-term fit. |

Source: supplied recruiter PDF, pp. 1–5. A candidate report's 60-minute deep-dive description does not override this packet's 45 minutes. The travel handoff's generic 14-algorithm shopping list is background; it is not a requirement to build a new deck or displace UI preparation.

A useful allocation for ten preparation hours is **4½ UI, 3 full-stack design, 1 decomposition, 1 project/HM, and ½ algorithms**. Change the allocation after an actual weak session or recruiter clarification. This is a planning estimate, not an official rubric.

## 02 — What the authenticated reports add

Read through the company catalog and eight relevant detailed entries using the signed-in browser. The live catalog showed 53 curated entries and a separate paginated coding collection. This was a targeted review, not a claim to have inspected every underlying thread or every coding entry. Frequency labels describe that site's reports across roles; they do not estimate a PIL candidate's probability.

| Reviewed entry | Reported scope | How to use it here |
|---|---|---|
| [Real-Time AI Product Feature](https://www.1point3acres.com/interview/problems/company/openai/real-time-ai-product-feature) | Streaming UX plus admission, cost, recovery and 10× growth; single-report label. | Closest full-stack rehearsal. Tie every backend decision to a user-visible state. |
| [GPT-3 Playground](https://www.1point3acres.com/interview/problems/company/openai/gpt-3-playground) | Mockup-based greenfield architecture with parameters, streamed completion and saved presets; single-report label. | Practice organizing an unfamiliar product from its mockup. |
| [AI Chatbot System](https://www.1point3acres.com/interview/problems/company/openai/design-ai-chatbot-system) | Authenticated chat, browser-held conversation, no server chat persistence, refresh clears history; low label. | Respect the no-persistence constraint. Do not add a conversation database by reflex. |
| [Chat Bot System Refactoring](https://www.1point3acres.com/interview/problems/company/openai/chat-bot-system-refactoring) | Separate legacy command handlers and state; preserve output; event-based extension; medium label. | Practice behavior-preserving change before introducing abstractions. |
| [OpenSheet](https://www.1point3acres.com/interview/problems/company/openai/opensheet-spreadsheet) | Formula dependencies, cycle handling and cached reads; single-report label. | Secondary coverage connecting a UI to a dependency graph. |
| [Sora / Video Generation](https://www.1point3acres.com/interview/problems/company/openai/design-sora-video-generation) | Asynchronous jobs, scarce workers, cancellation and recovery; very-high label. | Review the job lifecycle; model internals are not the center of this report. |
| [Cloud IDE](https://www.1point3acres.com/interview/problems/company/openai/design-cloud-ide) | Browser files, terminal, workspace lifecycle and isolation; high label. | Compare short request/response work with long-running sessions. |
| [Technical Deep Dive](https://www.1point3acres.com/interview/problems/company/openai/technical-deep-dive) | Defensible decisions, technical depth, impact and cross-team alignment. | Use the packet's duration and slide guidance; reports reinforce depth over breadth. |

The public [infection-spread preview](https://www.1point3acres.com/interview/problems/company/openai/infection-spread-cellular-automata) describes multi-source grid propagation and later stateful simulation. Keep BFS level boundaries and simultaneous updates warm. Its generic coding frequency is not evidence to prioritize it above the recruiter's UI guidance.

**Important distinctions:** a system-design listing is not proof that the same task appears as UI coding. The local Playground build is an original learning example inspired by transferable product mechanics. The old [OpenAI Coding Top 20](#/learn/openai-coding) explicitly identifies itself as representative coverage, not a verified ranking. The root `openai-sysdesign-top5.md` is a separate PracHub-derived artifact; its ranking was not revalidated here.

## 03 — Use what already exists

The reading site remains two sections: Learn and Designs. The coding environment lives in the sibling `uie-practice` repository. No new quiz, scheduler or recall deck is part of this setup.

| Need | Existing material | Read for |
|---|---|---|
| Fast UI implementation | [Component round](#/learn/component-round), [React & CSS](#/learn/react-css) | Scope, layout, state ownership, effects and the working baseline. |
| Production-like UI behavior | [UIE Components](#/learn/uie-components), [Accessibility](#/learn/accessibility) | Keyboard and focus behavior; concrete component contracts. |
| Streaming chat | [Transcript walkthrough](#/learn/openai-transcript), [OpenAI screen reference](#/learn/openai-screen) §§5, 8–10 | Incremental construction, cancellation, decoding, transcript state and tests. |
| Architecture | [System design round](#/learn/system-design-card), [Data modeling](#/learn/data-modeling), [Client-side design](#/learn/client-side-system-design) | A complete request path, authoritative state, reconnect, ordering and failures. |
| Backend mechanics | [System Design](#/learn/system-design), [Technology Choices](#/learn/technology) | Consult a specific mechanism after identifying a concrete bottleneck. |
| Small algorithm maintenance | [Coding Top 20](#/learn/openai-coding) #3, #5, #8, #14 | Iterator state, temporal lookup, formula graphs and topological ordering. |

In `uie-practice/src/exercises/openai/`, the existing 01–06 folders cover streaming, composer behavior, transcript, mentions, edit/resubmit and markdown; 07 covers iterators. They already include local mocks and reference implementations. Preserve your dated attempts. The parent repo currently has unrelated incomplete exercises that break its full TypeScript build; `pil-offline` has its own dependency lockfile, build and tests.

The prior Discord retrospective materials under `interview-prep/discord-technical-retrospective/` may supply raw material for your deep dive. They have not been rewritten or validated for this loop. Do not assume the prior deck satisfies the recruiter packet just because slides exist.

## 04 — Learning: turn a mockup into a prototype

The fastest route to a good prototype is a narrow, complete interaction. Before coding, identify the primary action, the resulting screen change and the state that must survive each interaction. A mockup shows appearance; your first job is to infer and confirm behavior.

For a prompt Playground, the minimal vertical slice is: edit prompt → submit → see response → submit again. Parameters and presets are useful only after that flow works. A well-styled empty shell is not a working product.

**First five minutes:** restate the user and the main action. Confirm the framework, input/output contract, mock data, persistence and whether streaming is required. Explain the cut: “I will finish sending and displaying a response, then add cancellation and failure recovery, then refine layout.” State what you will do if time runs short.

**Minutes 5–15:** build semantic markup, a labeled composer, an output region and the primary button. Use CSS grid for the major panels and flex for a toolbar. Set a readable content width and sensible overflow before decoration. At a narrow width, collapse the sidebar above or below the content. Do not let a long token force horizontal page scrolling.

**Minutes 15–30:** connect a deterministic local API. Represent empty, loading, success and failure explicitly. Submit via a form. Prevent blank input. Use stable IDs for list entries. A native button and textarea already provide much of the keyboard behavior you need.

**Minutes 30–45:** add the important interruption path: Stop, a new request superseding an old request, or retry. Preserve the user's input on a failed submission where appropriate. A disabled control should have a visible reason. Make status changes accessible without announcing every streamed token.

**Minutes 45–55:** test the user-visible contract, then correct spacing, alignment, scrolling and focus. Explain why the tests would have caught a real bug. Avoid using all remaining time on snapshots or internal component structure.

**Final five minutes:** demonstrate the main flow and one failure path. State the remaining product limitation precisely: “Presets are session-only in this prototype; production requires an authenticated save API.” Give the next implementation step and its justification.

### State is the part to design first

Separate three kinds of data:

- **Draft state:** what the user is currently editing. It can change while a previous response arrives.
- **Domain state:** messages, saved presets, document versions, jobs. Give these stable identity and clear ownership.
- **Request state:** which operation is active, its cancellation handle and its status. A request is not a message; a retry can create another attempt for the same user intent.

For example, each response turn can have `{id, prompt, text, status}`. Keep a request generation in a ref. On every new submission, advance the generation before aborting the old request. Any callback must verify it still belongs to the current generation before writing state. Aborting asks the transport to stop; checking identity protects the UI if a late callback still arrives.

Avoid independent booleans such as `loading`, `done` and `failed` that can all become true. Use a status union and define allowed transitions. Derive “can stop” from `status === 'streaming'`. The offline reference implements this contract and tests a deliberately uncooperative transport.

### Rendering, accessibility and scope

Keep streamed text as text until a safe renderer is genuinely needed. In the offline reference, React escapes output and no raw HTML is inserted. A production markdown renderer needs an explicit sanitization and link policy. Keep the streaming buffer separate from expensive parsing; flush at a controlled cadence if token frequency makes rendering costly.

Auto-scroll only while the user is following the newest output. If they scroll upward, preserve that intent and offer a way to jump back. Virtualization is a response to a measured or stated transcript-size constraint; it is not the first feature to implement.

Enter-to-send must allow Shift+Enter for a newline and must not submit during IME composition. Use a short polite status announcement such as “Response complete.” A screen reader should not have to listen to every intermediate token to discover that Stop exists.

## 05 — Learning: read, debug and refactor UI code

Treat a refactoring exercise as preservation of observable behavior. First run the supplied example and capture output order, text and state changes. A surprising legacy behavior may be intentional. Identify it before changing it; get agreement on a bug fix separately from a structural refactor.

For a command-driven chat UI, separate parsing from domain actions and rendering. A parser converts raw text into a small command union. A handler receives explicit state and dependencies and returns changes or effects. A view renders those results. You can then test parsing without mounting the UI and test the UI without a real network.

Start with the smallest useful seam: inject the clock or transport, move global state into an instance, or extract one handler. A central event bus is justified when independent consumers really need the same event; it adds ordering, lifecycle and debugging questions. Keep registration order and unsubscribe behavior explicit. Avoid recursively feeding a bot's own output back into itself unless the product requires that behavior.

**JavaScript-specific caution:** string length counts UTF-16 code units, not user-perceived characters. Do not mechanically translate a Python emoji-counting exercise into `.length`. Use an explicit token parser for the declared command format; for general grapheme limits, use a grapheme-aware approach.

When a test contradicts the described behavior, reduce it to a small input and explain the discrepancy. Do not silently change the contract to make the test green. The goal is a defensible implementation with understood limitations.

## 06 — Learning: full-stack design from the same UI

Draw a single real request before adding infrastructure. For a persistent Playground, begin with these responsibilities:

```text
Browser: draft + selected parameters + current response
    → authenticated application API: validate + authorize + admit request
    → model adapter: provider credentials + timeout + cancellation
    → streamed events back to browser

Preset save/load API → relational store scoped to the owner/tenant
Request identity and telemetry cross every hop
```

A browser never needs the provider secret. An application session identifies the user; server-side authorization checks access to presets or jobs on every operation. Session/auth state and chat-history persistence are separate design decisions.

Model the smallest durable entities. `Preset(id, tenant_id, owner_id, name, prompt, parameters, version)` supports a saved experiment. Updating a preset with an expected version prevents one edit from silently overwriting another. Do not put token-sized response updates into the preset row.

For a persistent execution, use `Run(id, tenant_id, request_key, status, model, parameters, created_at)` and an attempt or event model if recovery requires it. Make request-key uniqueness tenant-scoped. A retry with the same key and different parameters should be rejected or explicitly defined, not silently reused.

For the reported **ephemeral chatbot variant**, remove durable conversation/run content from the baseline. Keep the transcript in React memory if refresh must clear it. `localStorage`, IndexedDB and `sessionStorage` all survive a refresh and therefore violate that behavior unless explicitly cleared. Authentication can still use a normal application session. Operational metadata needs a deliberate retention policy; do not accidentally log the entire conversation.

### Streaming transport and framing

HTTP response streaming is sufficient for a one-way completion. A POST with `fetch` allows a request body and explicit authorization headers. Native `EventSource` is GET-oriented and has different header/reconnection constraints. “SSE” describes framing over HTTP; it is not synonymous with choosing the browser `EventSource` API. WebSocket is reasonable when there is genuinely bidirectional, frequent communication such as a terminal.

TCP/HTTP chunks are not message boundaries. Decode UTF-8 incrementally, buffer incomplete frames, and only parse complete messages. If reconnect is supported, include an event sequence and define the replay window. A cursor is only useful if the server retains a replay source. Without replay, show the partial result and offer a clearly labeled new attempt; do not blindly append a regenerated answer as though it were the remainder of the old one.

Define cancellation at both ends. The UI stops accepting updates immediately, but disconnecting the client does not prove that model work stopped. Propagate cancellation to the execution owner and account for already-consumed compute. Completion racing with cancellation needs a stated winning transition.

### Capacity and failure, with concrete consequences

Use Little's Law for a starting estimate: at **40 accepted requests/second** and **15 seconds mean stream lifetime**, expect about **600 active streams**, before headroom. These are illustrative assumptions, not OpenAI traffic figures. At ten times the arrival rate, you need roughly 6,000 stream slots if service time holds; if it rises under overload, concurrency rises further.

Separate the number of connected clients from available model capacity. A queue can protect workers but cannot make unlimited demand disappear. Bound waiting time, apply per-tenant limits, return understandable admission feedback, and distinguish “waiting” from “generating.” A streaming gateway can be healthy while the model queue is unusably slow.

Trace failures through both state and UX:

| Failure | System decision | Visible behavior |
|---|---|---|
| Request accepted, acknowledgement lost | Deduplicate by client request key where durable runs are in scope. | Recover the existing run instead of double-starting expensive work. |
| Stream disconnects | Replay from retained cursor, or declare interruption if replay is unsupported. | Preserve partial text and explain what Retry means. |
| Model request times out | End the attempt; propagate cancellation; classify retryability. | Error state with a usable recovery action. |
| Tenant exceeds budget | Reject or queue within a bounded policy. | Clear limit/queue feedback; never an infinite spinner. |
| Preset edit races | Conditional write with version check. | Resolve conflict without silently losing another edit. |

Measure time to first useful output, inter-chunk stalls, completion success, queue wait, cancellation lag and cost per successful run. Correlate client and server request IDs. These measures explain customer experience better than “we use monitoring.”

## 07 — Two contrasting design walkthroughs

### Long-running generation: durable intent, replaceable attempt

Use a job API that acknowledges only after durable acceptance. The UI receives a stable job ID, can leave and return, and can display queued/running/cancelling/terminal states. Separate that job from each worker attempt; retries should not create a second customer-visible request.

A transactional claim establishes the current attempt and its lease. When a lease expires, a replacement can be assigned, but the old worker may still be alive. A fencing identity lets the result store reject stale completion. The lease by itself does not stop the old process.

Write a result artifact first, then conditionally attach it to the still-current attempt. Clean up abandoned artifacts later. Durable cancel intent plus best-effort worker notification handles lost replies; only confirmed stopping or reconciliation makes the capacity reusable. If the model cannot checkpoint meaningful execution state, be honest that recovery repeats work.

For fairness, “equal numbers of starts” and “equal GPU-seconds” are different objectives. A long non-preemptive job can dominate service despite round-robin dispatch. Define the resource and customer guarantee before choosing a queue policy. Keep the UI truthful about approximate progress and uncertain wait estimates.

This is an original teaching design for the reported problem family, not a prescribed 1point3acres solution.

### Cloud workspace: interactive execution and isolation

Separate a durable workspace (identity, access, source files) from a disposable runtime (processes, memory, installed packages according to the persistence contract). A browser terminal needs input as well as output, so a WebSocket session has a clear purpose here.

Authenticate the connection, authorize its workspace and bound terminal output buffers. After reconnection, replay from an acknowledged sequence if a bounded log exists. A noisy process must not force unlimited browser memory growth. Slow clients can lose old output with an explicit gap marker or be disconnected under a stated policy.

For arbitrary untrusted code, “one Kubernetes pod per user” is not a complete isolation argument. Discuss the trust boundary, restricted privileges, network access, resource caps, secrets and a sandbox or microVM appropriate to the threat model. Start with direct output routing if it meets the reliability requirement; a durable broker is a trade-off, not a mandatory box.

The original source's sizing and specific technology choices are examples. In your interview, use the stated load, runtime lifetime and persistence requirements to choose the system.

## 08 — Decomposition and Staff communication

The decomposition round is not another opportunity to recite a generic chat architecture. Begin with the customer's outcome: who does what today, where it fails, how success is measured, and which constraints are real. Identify a narrow first version and the assumptions that could invalidate it.

For an original example, imagine a support team wanting help drafting replies from internal documents. First establish whether the system suggests or automatically sends replies. That choice changes the failure cost, approval flow, permissions and release plan. Understand document access and the existing workflow before proposing retrieval infrastructure.

A sensible initial design can use authorized retrieval, a cited draft, human approval and a feedback record. Split delivery into an evaluation using representative cases, an internal pilot, then a monitored rollout. Name a fallback when retrieval finds nothing or confidence is poor. Do not invent a numerical quality target on the customer's behalf; propose how to measure it and agree on a threshold.

Present back in customer language: “This reduces drafting time while keeping your agent in control. The first release covers one document source. We will measure accepted drafts and incorrect citations before expanding.” Then explain the main cost, failure and dependency. This is how technical choices become a coherent delivery decision.

For the technical deep dive, use one project with enough depth to defend. A useful ten-slide structure is context, success criteria, your ownership, baseline architecture, decision one, decision two, failure/recovery, delivery and alignment, measured outcome, and lessons. Keep the prepared narrative around 12–15 minutes so the 45-minute round has room for conversation. These are preparation suggestions; the packet requires slides and recommends at most 12.

Staff-level substance comes from decisions under constraints: alternatives rejected, disagreements resolved, boundaries between teams, migration sequencing, evidence behind the result, and what you personally changed. If a metric was not measured, say so. Describe how AI could improve the workflow only where the use case and evaluation are defensible.

## 09 — Courses: use your purchase selectively

Your [Senior Level Frontend Interview Prep](https://master.dev/courses/interviewing-frontend-v2/) course is a good fit. Its public syllabus is 11 hours 28 minutes and includes JS/TS, component work, a ChatGPT-like interface and a spreadsheet. Prioritize the component and ChatGPT portions; use debounce/throttle and tree selection where they expose an actual weakness. Defer the full Promise reimplementation and advanced type puzzles until your working UI is reliable. Pair each relevant lesson with a local implementation; completion percentage is not the objective.

Master.dev's [official features FAQ](https://master.dev/features/) confirms course downloads in **Android and iOS apps**. It does not establish an offline laptop player or transferable video files. Download selected lessons to your phone/tablet while online, then test playback after restarting that app in airplane mode. Browser tabs and course bookmarks are not offline copies. This setup includes original learning notes and local code, not downloaded course videos.

The signed-in course's Resources links also expose its [official code repository](https://github.com/EvgeniiRay/preparing-for-ui-interview-v2) and slide PDF. A separate local `pil-frontend-course` repo now holds that code at commit `ba7e664e73a121aecfc8ae112f4e39975d31537b`, with a local Bun runtime. Its `OFFLINE-SETUP.md` has commands. The private transfer bundle includes the slides. The course's gallery uses local SVG fixtures in this copy, and its server binds to localhost. Other student solutions remain as the course shipped them.

Two useful complements:

- [Front-End System Design, Evgenii Ray](https://master.dev/courses/frontend-system-design/), 4 hours 37 minutes: state/network design, virtualization and a design walkthrough. Use it for client depth, then add the backend ownership and failure reasoning required by your packet. Check whether your purchase includes this course before spending more.
- [GreatFrontEnd System Design Playbook](https://www.greatfrontend.com/front-end-system-design-playbook/introduction): a structured frontend design reference. Useful for API shape, application state, performance and accessibility. Offline access was not established here; use online before departure or an offered personal export, not as a dependency of the local kit.

Do not buy another broad interview subscription merely to collect more material. Your existing guide library and UI exercises already cover the core mechanisms. The current gap is executing a complete product slice and explaining it end-to-end.

## 10 — The local setup and transfer contract

The separate `uie-practice/pil-offline` package contains:

- `src/Prototype.tsx`: an intentionally minimal workspace for your implementation.
- `src/Reference.tsx`: a working, original Playground-style UI with session presets, local streaming, Stop, superseding requests, partial-error recovery and keyboard input.
- `src/stream.ts`: a deterministic fixture with slow, failed and empty responses; no model/API connection.
- `src/Reference.test.tsx`: reference tests for stale callbacks, cancellation, partial failure, retry and empty output.
- A local Excalidraw editor with bundled fonts, `.excalidraw` import/export and browser draft recovery. Export files for transfer; browser storage does not move with a folder.

From that package, use `npm run dev`, `npm test` and `npm run build`. Dependencies must be installed before departure. The reference's preset persistence is deliberately session-only, unlike the persistent production Playground design; the UI labels this limit. Its chunk fixture delivers strings, so the existing screen guide's byte-decoding/SSE material remains important for real HTTP streams.

The transfer builder lives at `scripts/offline/build-kit.mjs` in this reading repo. Run `npm run offline:pack` after both apps build. It creates an ignored, timestamped `out/pil-travel-…/pil-travel-kit/` folder and a `.tar.gz` archive with built reading pages, the lab/whiteboard, selected source trees and lockfiles, a dependency-free local server, and integrity hashes. `--include-deps` additionally includes the lab and course dependencies, plus the local Bun runtime, for a compatible machine. These installed dependencies are excluded from integrity hashing; source and built assets are hashed.

On the destination laptop, install **Node 24** and your editor/browser while online. Extract the archive, open a terminal in `pil-travel-kit`, then run:

```bash
node verify.mjs
node serve.mjs
```

Open `http://127.0.0.1:4178/`. Reading, the built reference and the whiteboard require Node but no npm install. The site keeps its `/morning-recall/` base path. Stop the server with Ctrl+C. For editable coding, in a second terminal:

```bash
cd source/uie-practice/pil-offline
npm ci                 # Do this ONLINE on the destination laptop before travel.
npm test
npm run dev
```

The official course can run separately from the bundle root with `node run-course.mjs`, at `http://localhost:3000/`. On a different OS/architecture, first reinstall the course tools with `npm --prefix source/pil-frontend-course/offline-tools ci`, then use that local Bun executable to install the course's frozen lockfile, as described in its setup file. Course reference examples work independently of unfinished student solutions; the full course test suite is not an all-green setup check.

The editor runs at `http://127.0.0.1:5178/`. Keep the bundle server running for the Learning guide link; the lab itself works independently. Source changes update the development app, not the prebuilt copy. Rebuild and repack to refresh the transferable snapshot.

Copied `node_modules` may work on the same OS/architecture, but native build tooling is platform-specific. An Apple Silicon Mac, Intel Mac and Windows laptop are not interchangeable. The robust migration is `npm ci` on the destination while online, then preserve those installed dependencies. No Node installer, editor or course videos are included. Never rely on a Git clone to carry uncommitted attempts or browser-saved drawings; the kit copies current source and drawings need explicit exports.

### Before the trip

On the actual travel laptop, restart the browser and local servers without internet. Open the new guide and two existing guide links. Run the reference through success, failure, empty response and Stop. Edit `Prototype.tsx`, confirm hot reload and run tests. Draw labeled boxes and arrows, export `.excalidraw`, reopen it, and confirm the drawing survives. Save the exported file into your travel folder and copy it to your backup location.

A passing build on this computer does not certify that different laptop. The final destination-machine rehearsal is still required. Do not turn off Wi-Fi during an active call; perform that check when convenient. The packer accepts `--reference=/absolute/path` for explicitly chosen private attachments in its `references/` folder; they are not added to the public reading-site assets.

## 11 — A flexible six-session reading and building sequence

1. **Setup and prototype:** verify the local tools, read §4, build a complete send/response UI, then inspect the reference.
2. **Interruptions:** read the transcript walkthrough and §5; handle Stop, stale callbacks, failure recovery and a small behavior-preserving refactor.
3. **Full-stack product:** read §6 and the data-modeling guide; use the local whiteboard for one complete Playground flow and its ephemeral-chat contrast.
4. **Long-running work:** read §7; draw the job/attempt lifecycle and walk through worker loss, cancellation and delayed completion.
5. **Customer and project depth:** use §8 to explain a scoped customer proposal and tighten the opening of your project story. Review existing slides against the packet.
6. **Rehearsal and transfer:** complete a 60-minute UI session and a separate 60-minute design discussion; package the current files and perform the destination-machine offline check.

For a short hotel session, finish one small correction: fix a cancellation bug, improve a cramped layout, or clarify a durability boundary in a diagram. Preserve progress in source files and exported drawings. No scheduler or new recall collection is needed.
