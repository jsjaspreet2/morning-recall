# Client-Side System Design

> The half of system design that lives in the browser: a client that carries as much complexity
> as the server, and a component whose *interface* and *tests* are scored above its
> implementation.

Companion to `System Design` (which is the server half) and `UIE Components` (which is the
component half). This is the seam between them, and it is the half most candidates leave thin —
the client treated as a view rather than as a replica with its own write path.

## 01 — The client as a distributed system

The `System Design` guide is the server half and it is good. This is the half it doesn't cover,
and it is the half a front-end or product-engineering round is most likely to probe.

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
above most candidates on the axis the round is actually grading.

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
| 5 | **WebRTC data channel** | Peer-to-peer, or latency below what a relay allows | Signaling, NAT traversal, TURN costs |

**The line to say for streamed LLM output specifically:** *"Model output is one-directional text,
so SSE. It's plain HTTP so it goes through corporate proxies, `EventSource` reconnects on its own,
and `Last-Event-ID` gives me resumption almost free. I'd move to a WebSocket if the client needed
to stream back continuously — live cursor presence would do it."*

Worth knowing so you don't get caught: `EventSource` cannot set headers, so auth is a cookie or a
query param — mention it, or use `fetch` with a `ReadableStream` and parse the event framing
yourself, which is what most production LLM clients actually do.

The ladder above is the decision. What each rung actually is at the socket level — the `101`
upgrade, ping/pong, `Last-Event-ID`, the missed-event window a long poll leaves — is
`Technology Choices` §22–25.

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

Be precise about what it saves, because an interviewer may push: it saves **renders**, not paints.
The browser already coalesces DOM mutations to one paint per vsync, so the visual output was
frame-synchronized before you touched anything. The win is main-thread time, and it only matters
when `render cost × cross-task arrival rate` is large — true for streamed markdown or a syntax-
highlighted diff, not for appending to a text node. Volunteering that distinction reads better than
reaching for the buffer reflexively.

Two footguns in the pattern above. `requestAnimationFrame` **does not fire in a background tab**, so
a buffered stream freezes mid-answer until the user returns — pair it with a `visibilitychange`
fallback or a timer if the tab can lose focus. And `cancelAnimationFrame` on unmount, or flush the
tail when the stream ends, or the last partial buffer is dropped on the floor.

**3. Cancellation.** Every stream needs a stop that is instant *in the UI* and eventually
propagates to the server. Abort the request, stop consuming, and — importantly — **keep the text
already received**. Users read a canceled response.

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

| Policy | Behavior | Fits |
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

This table is the pick; the mechanism behind each row — IndexedDB's transactions and its
auto-close, the single origin quota all three async stores share, and the fact that eviction is
all-or-nothing per origin rather than per record — is `Technology Choices` §17–21.

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

The wall-clock number and the felt number are different, and these rounds reward knowing which
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

**The inline-completion version, and worth rehearsing because it's a standing deep dive in any
AI-editor round:** for inline
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

The single highest-leverage habit in a client design round. Instead of "it should be fast," decompose:

> *"Target is 100 ms p50 for a suggestion to appear. That's ~10 ms of debounce I've already
> spent, ~20 ms RTT to the nearest edge, which leaves ~60 ms for inference and serialization.
> That budget is what forces a small model at the edge — a large model can't fit, so the large
> model has to be doing something the user isn't waiting on."*

Numbers worth having memorized well enough to say without pausing:

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

## 02 — A worked design: agent chat, streaming multi-file edits

> **Prompt.** *"Design the chat panel where a developer describes a task, an agent reads the
> codebase, and edits stream back across several files. The user watches them arrive and can
> accept or reject each one, keep typing while it runs, or stop it. It has to survive a reload."*

The client half here is genuinely harder than the server half, which is what makes it the worked
design worth carrying: almost every client concept in §01 shows up in it at once.

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
2. *Backpressure.* Coalesce deltas on `requestAnimationFrame` (§01 D). A five-file edit burst
   should be 60 renders/second, not 600.
3. *Partial diff rendering.* A streaming edit is a syntactically incomplete diff. Render arriving
   lines as a "pending" hunk; only compute the real hunk boundaries at `file_edit_end`. Cheap
   version under a clock: append-only rendering during the stream, re-render properly on close.
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
## 03 — Component API design

Interview rubrics name this axis explicitly — *"the props and interface your component
exposes"* — which is a tell that they expect it to be under-served. It is the cheapest twenty
points in the round because it costs three minutes and most candidates spend zero.

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

### B. THE DUAL API — SIX LINES, MEMORIZE THEM

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

### C. THE PATTERNS CATALOG

| Decision | Weak | Strong | The line to say |
|---|---|---|---|
| Value shape | `selectedIndex: number` | `value: string` (an id) | *"Index breaks when the list reorders or filters."* |
| Multiple booleans | `isOpen, isLoading, isError` | `status: 'idle' \| 'loading' \| 'error'` | *"Booleans let me represent states that can't exist."* |
| Customization | 6 flags | `renderItem` / `children` as a function | *"One escape hatch instead of anticipating every need."* |
| Related props | `label, labelId, labelClassName…` | Compound components: `Thing.Label` | *"Structure belongs in JSX, not in prop names."* |
| Callback payload | `onSelect(id)` | `onSelect(id, item)` | *"Saves every consumer the lookup I already did."* |
| Async source | `url: string` | `fetch: (q, signal) => Promise<T[]>` | *"Injectable, so it's testable, and it can be canceled."* |
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
## 04 — Test quality

Routinely a named grading axis, and the one with the least practice behind it. Twelve minutes of
tests is worth more than twelve minutes of the feature you didn't finish, because only one of
those is on the rubric twice (it's also evidence for "code correctness").

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
| `expect(wrapper.state.open).toBe(true)` | `expect(screen.getByRole('listbox')).toBeVisible()` | Implementation vs behavior. State can be renamed; behavior can't. |
| `fireEvent.click` | `await user.click` | `user-event` fires the real sequence — pointerdown, mousedown, focus, click. Half the bugs live between those. |
| One test asserting nine things | One behavior per test | A failure names itself. |
| `expect(fn).toHaveBeenCalled()` | `expect(fn).toHaveBeenCalledWith(…)` | Proves the payload, which is the API. |
| Snapshot of the whole tree | Explicit assertions | A snapshot passes forever and then fails for no reason anyone reads. |
| `await new Promise(r => setTimeout(r, 500))` | `await waitFor(() => …)` / `findBy*` | Deterministic, and doesn't cost half a second each. |

**The one-sentence version to say out loud in the pad:** *"I'm testing behavior through the roles
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

That last one is how you test a race in four lines, and it's worth having memorized: hand-resolving
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

- **Not CSS.** Styling is rarely graded; asserting a class name is worse than not testing.
- **Not third-party behavior.** You are not testing React.
- **Not every permutation.** One representative case per behavior.
- **Not internal function names.** Test through the public surface only.
- **Not the type system.** If the pad is TS, the compiler already did that.

### F. IF THE PAD CAN'T RUN TESTS

Write them anyway, and say so:

> *"I can't execute these here, but this is the suite I'd ship — and writing it now is partly how I
> check my own API, because a component that's awkward to test is usually a component with an
> awkward interface."*

That last clause is true and it is exactly the connection between this axis and §03.

### G. THE DRILL

Test quality is the axis with the least practice behind it, so `uie-practice` carries two
dedicated reps: `cursor-05-write-the-tests` (a finished `Toast`, ten behaviors, thirty minutes)
and `cursor-10-write-the-tests-ii` (a finished async hook). In both, the component is done and
**the suite is the entire deliverable**. Run them back to back, then diff against the reference
suites and count what you missed — the misses are the list to reread the night before.
