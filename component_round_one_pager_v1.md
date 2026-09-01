# The component round — one page

Read this at T-30. Everything here exists in longer form elsewhere; this is the operational
version. Pointers to the deep sections are at the bottom.

---

## The clock

| Minute | Do |
|---|---|
| **0–3** | Clarify. Then state the contract out loud. **Do not type yet.** |
| **3–7** | Type the prop signature. Say why each prop exists as you write it. |
| **7–12** | Skeleton renders. Hardcoded data is fine. Something on screen. |
| **12–35** | Core behavior. The one thing they actually asked for. |
| **35–38** | Checkpoint out loud: what works, what's left, what you'd cut. |
| **38–50** | **Tests. Non-negotiable.** Whatever state the component is in. |
| **50–55** | Extensions, or the highest-value missing behavior. |
| **55–60** | Name what you skipped and what you'd do next. |

**If you are behind at 35, you are still writing tests at 38.** Test quality is a named axis; a
half-finished component with three real tests scores above a finished one with none.

---

## The first ninety seconds

**Ask, then commit.** Four questions, pick the ones that apply:

1. Controlled, uncontrolled, or both?
2. Where does the data come from — do I get a fetcher, or should I fake it?
3. Keyboard and screen-reader support in scope, or focus on the happy path?
4. Should I write tests as I go, or at the end?

**Then say the five decisions.** This is the highest-scoring ninety seconds available.

1. **Who owns the state?** Controlled / uncontrolled / both. Default to both — it's six lines.
2. **What is the identity?** Every item needs a stable `value`. Ids, keys and ARIA wiring derive
   from it. Never from display text, never from index.
3. **What moves focus?** Real focus (roving tabindex) · a virtual cursor (`aria-activedescendant`)
   · nothing. Decided by: *does something else stay usable while navigating?* If a text input must
   stay typable, it's a virtual cursor.
4. **What can arrive late, repeat, or outlive the component?** Two in flight → generation guard.
   Fires many times a second → debounce. Unmounted mid-flight → cleanup and abort.
5. **What changes without the user causing it?** That, and only that, is your live region.

---

## The prop signature — type this before any body

```tsx
type Props = {
  value?: string                                   // controlled
  defaultValue?: string                            // uncontrolled. never both meaningful
  onValueChange?: (next: string, item?: Item) => void   // not onChange — DOM collision
  items: Item[]                                    // data-driven beats compound: can't mis-nest
  fetchItems?: (query: string, signal: AbortSignal) => Promise<Item[]>  // inject, don't configure
  disabled?: boolean
}
```

**Say these while typing:**

- *"Controlled when the parent owns it, uncontrolled with a default when it doesn't, never both."*
- *"`items` rather than compound children, so the ARIA wiring stays my responsibility and it
  virtualizes later without an API change. I'd add `renderItem` if rows need to differ."*
- *"The fetcher is injected with the signal — the component owns rendering and lifecycle, the
  caller owns transport. That's what makes it testable with no network."*
- *"One `status` union, not three booleans — `isLoading` and `isError` can both be true and most
  of those combinations are illegal."*

**Escape hatch, one line:** `className` + `...rest` to the root, and forward the ref. One beats ten
props. Spread `rest` **before** your own `role`/`aria-*` so a caller can't clobber them.

---

## Async, streaming, cancellation

```tsx
useEffect(() => {
  const controller = new AbortController()

  async function run() {
    try {
      const res = await fetchStream(controller.signal)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      // TextDecoderStream does the {stream:true} bookkeeping AND the final flush,
      // so a split multi-byte character can't corrupt and a tail can't be dropped.
      const reader = res.body!.pipeThrough(new TextDecoderStream()).getReader()
      while (true) {
        const { done, value } = await reader.read()   // value is a string
        if (controller.signal.aborted) return
        if (done) break
        setText((t) => t + value)
      }
    } catch (err) {
      if (controller.signal.aborted) return
      setError(err instanceof Error ? err : new Error(String(err)))
    }
  }

  run()
  return () => controller.abort()      // covers retry, prop change AND unmount
}, [fetchStream])
```

**The four sentences:**

- *"`signal.aborted` after every await — React tears the old effect down before the new one, so a
  superseded run's controller is already aborted."*
- *"No `isMounted` flag. Since React 18 a state update after unmount is a no-op, and the cleanup
  plus the signal already do the job."*
- *"`TextDecoderStream` because it can't forget the streaming flag or the final flush. By hand it's
  `decode(value, { stream: true })` plus a bare `decode()` at the end."*
- *"A **debounce timer** fires outside any effect teardown, so that one needs a real generation
  counter — in a ref, because it's read and never rendered."*

**Where a generation counter goes:** a ref. **Where a restart trigger goes:** state — only state
re-runs an effect. Different jobs.

---

## State rules that get caught in review

- **New state from previous state → functional update.** `setItems(prev => [...prev, x])`. Always,
  including where a direct set would happen to work.
- **But a functional updater can't hand you a value back.** If you need the current value to build
  a request, read it from the closure *before* setting. Doing the read inside the write sends stale
  data and the UI looks perfect.
- **Never write a ref during render.** `ref.current = fn` at the top level is a side effect; put it
  in an effect with no dep array.
- **Derive, don't store.** `canSubmit`, `isEmpty`, `canUndo` are functions of other state.
- **No setState synchronously in an effect body.** If you can name the event that caused it, the
  change belongs in that event's handler.

---

## The three axes, and what earns on each

| Axis | What earns |
|---|---|
| **Correctness** | The keyboard contract, the async race, the empty/error/loading states |
| **API design** | Saying why each prop exists — and naming one you refused to add |
| **Test quality** | Behavior not implementation; the race; a11y queries over test-ids |

**Five tests that always earn**, in this order: renders the happy path · the keyboard contract ·
the async race (two in flight, only the last lands) · the error state · the empty state.

Use `getByRole`, `getByLabelText`, `findBy*` for async. `userEvent` over `fireEvent`.
**`vi.useFakeTimers()` deadlocks with `userEvent`** — use real timers with short durations, and if
you hit it live, say what's happening and switch rather than thrashing.

---

## Traps, ranked

1. **Silence.** Narrate the question you're weighing, not just the answer.
2. **`preventDefault()` at the top of a key handler.** `default: return` first, or you swallow Tab.
3. **`tabIndex={selected ? 0 : undefined}`** — no `tabindex` means not scriptably focusable, so
   arrows do nothing. It's `0` and `-1`.
4. **Index as identity.** Indexes shift when the list filters. Use the stable `value`.
5. **`<pre>` inside `<p>`.** A paragraph takes phrasing content only; browsers silently close it.
6. **Re-creating a stateful thing per chunk** — a parser, a decoder. One instance, fed forward.
7. **Forgetting `scrollIntoView({ block: 'nearest' })`** on the active item. `'start'` jumps.
8. **Building the whole thing before rendering anything.** Get pixels on screen by minute 12.

---

## Ask before you're asked

Say these unprompted near the end — each is a follow-up you pre-empt:

> *"I'd make it controlled-or-uncontrolled; right now it's uncontrolled."*
> *"Virtualization is the next thing this needs at a thousand rows — `items` means that's an
> internal change."*
> *"I'd add `renderItem` when rows need to differ, and keep the wrapper so the ARIA stays mine."*
> *"The thing I deliberately skipped is X, because Y — I'd do it next."*

---

## If you need more, in the components guide

| Need | Go to |
|---|---|
| Deriving a component you've never seen | **§02 B** — the six questions |
| Prop forks with the sentence for each | **§18** |
| The ninety-second API script | **§18 I** |
| `useChat` / hooks and return shapes | **§19** |
| Roving tabindex, focus trap, race guards | **§17 A, B, F** |
| Scroll-into-view, latest-ref, coalescing | **§17 P, Q, R** |
| The component you were actually asked for | **§03–16** |
