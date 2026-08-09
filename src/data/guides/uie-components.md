# UIE Component Reference

> Companion to `react_css_frontend_interview_field_guide_v3`. That guide is for *recall* —
> terse bullets you scan before a mock. This one is for *understanding*: complete, working
> implementations with the reasoning spelled out line by line.

Fourteen components you will actually be asked to build, each with the API, the ARIA and
keyboard contract, the full implementation, the traps, and the test plan. Then the twelve
underlying techniques, derived from scratch.

Every implementation here is real, runnable, and test-covered. They live in the practice app
at `uie-practice/src/exercises/<name>-reference/`, and each ships a spec suite you can point
at your own from-scratch build.

## 01 — How to use this guide

### A. THE LOOP

Reading this front to back teaches you almost nothing. The loop that works:

1. Pick a component. Read only **§B (API)** and **§C (ARIA + keyboard contract)**. Close the guide.
2. Build it cold, from an empty file, on a clock. Say the prop signature out loud before you
   write the body — that narration is what's actually being graded.
3. Run the reference spec against your build:
   `npx vitest run src/exercises/<name>-reference`
4. Only once you're green, read **§E (implementation)** and diff it against yours.
5. Read **§F (traps)** last. If you hit one on your own, you'll never forget it.

Step 4 before step 2 is passive rereading, and passive rereading is not preparation.

### B. WHAT IS ACTUALLY GRADED

In roughly this order, and it is not the order most candidates optimize for:

| Rank | Axis | What it looks like |
|---|---|---|
| 1 | **API design** | You sketch props before the body. Controlled *and* uncontrolled. No boolean soup. |
| 2 | **Test quality** | You name what you'd assert. Behavior, not implementation. |
| 3 | **Correctness under stress** | Rapid clicks, stale responses, unmount mid-flight, empty data |
| 4 | **Accessibility** | Real semantics, keyboard parity, focus management |
| 5 | **Structure** | Boundaries that follow responsibility, not file size |
| 6 | **Styling** | Enough that state is visible. That's the bar. |

Almost everyone spends their time on 6 and 5. The separation is at 1 and 2.

### C. THE TEN-MINUTE VERSION

If you have one sitting before a screen, re-derive these four from memory on paper:

- The controlled/uncontrolled block (§17 C). Six lines. Works for every component here.
- Roving tabindex (§17 A). Which element holds `tabIndex=0`, and what moves it.
- The race guard (§17 F). Why `AbortController` alone is not enough.
- Focus restore (§17 B). What happens when the trigger has unmounted.

Those four cover most of the difference between a mid-level answer and a senior one.

## 02 — The component contract

Everything in §03–16 follows the same shape. Learn the shape once.

| Part | What it holds |
|---|---|
| **A. Asked as** | The real prompt phrasings that map to this component |
| **B. API** | The typed interface, and why each prop exists |
| **C. ARIA + keyboard contract** | Required roles and states; every key and what it does |
| **D. Decisions that matter** | Three to five calls, each with the sentence to say out loud |
| **E. Implementation** | Annotated chunks, then the complete file in a collapsed block |
| **F. Traps** | What breaks, and the symptom you'd see |
| **G. Spec** | The test list, mirroring the runnable suite |

§E always ends with **THE WHOLE THING** — the entire component assembled, collapsed by default.
The chunks teach; the full file shows how the pieces fit and is what you diff your own build
against. Each one is the real source of the matching exercise — annotations intact, exactly as
it sits in `uie-practice/src/exercises/<name>-reference/index.tsx`. Only the CSS import, the
exercise metadata, and the trailing demo harness are dropped, since none of them are part of
the component. The inline comments are the point: they mark the lines where the obvious choice
is the wrong one, and each is a sentence you can say out loud in the round.

### A. THE FIVE DECISIONS

Before writing any component, answer these out loud. It takes ninety seconds and it is the
single highest-scoring thing you can do in the round.

1. **Who owns the state?** Controlled, uncontrolled, or both. Default to both — it's six lines
   (§17 C) and it's the first follow-up question you'll get.
2. **What is the identity?** Every item needs a stable `value`. Ids, keys, and ARIA wiring all
   derive from it — never from display text, which changes.
3. **What moves focus?** Real DOM focus (roving tabindex), a virtual cursor
   (`aria-activedescendant`), or nothing. Picking wrong is not a detail; it's the difference
   between a working widget and a broken one.
4. **What can arrive late?** Any async source needs a stale-response answer before you write
   the fetch, not after.
5. **What's the empty/loading/error state?** Decide now, or you'll bolt it on at minute 38.

### B. API CONVENTIONS USED THROUGHOUT

| Prop | Meaning |
|---|---|
| `value` | Controlled state. Its presence is what makes the component controlled. |
| `defaultValue` | Uncontrolled initial state. Ignored when `value` is passed. |
| `onValueChange` | Fires on every change, in both modes. Not `onChange` — that name collides with DOM events. |
| `items` | Data-driven list: `{ value, label, ... }[]`. Simpler than compound components and impossible to mis-nest. |
| `orientation` | `'horizontal' \| 'vertical'`. Drives `aria-orientation` *and* which arrow keys apply. |

**Never accept both `value` and `defaultValue` as meaningful.** One or the other. The rule to
state: *"controlled when the parent owns it, uncontrolled with a default when it doesn't,
never both."*

### C. THE ARIA WIRING RULE

Two rules that would have caught most accessibility bugs you'll ever write:

1. **Every `aria-controls` / `aria-labelledby` gets a matching `id` in the same JSX block,
   written in the same keystroke.** A dangling reference is worse than no attribute — it's a
   promise the DOM doesn't keep.
2. **Ids derive from the stable `value`, never from the label or content.** Two components
   cross-reference each other only if both compute ids from the same key.

And always `useId()` for the base. Hardcoded id prefixes collide the moment two instances
share a page, which is exactly what happens in the demo the interviewer opens.

### D. STYLE OFF ARIA, NOT OFF A PARALLEL CLASS

```css
.tab[aria-selected='true']       { /* ... */ }
.trigger[aria-expanded='true']   { /* ... */ }
.option[aria-selected='true']    { /* ... */ }
```

The accessibility attribute and the visual state then cannot drift apart, and you write one
thing instead of two. Worth saying out loud — it reads as someone who has maintained a design
system rather than memorized a pattern.

### E. THE TEST PLAN TO NAME

Even if you write none of them, saying this list is worth more than most candidates' entire
implementation:

- Renders the initial state; the default selection is right
- Interaction changes the visible outcome (not the internal state)
- Keyboard parity: every mouse action has a key that does the same thing
- The tab-stop count is what you intended
- Every `aria-controls` resolves to a real element
- Two instances on one page don't collide
- Controlled mode reports changes and does not move on its own
- Async: pending → outcome; a stale response loses; unmount mid-flight doesn't warn

## 03 — Tabs

> Runnable: `uie-practice/src/exercises/tabs-reference/` · Spec: 11 tests

### A. ASKED AS

- "Build a tabs component"
- "Build a settings page with sections" — clarify: tabs or accordion (§04)?
- "Make the selected tab shareable by URL" — the controlled-mode follow-up, always

### B. API

```tsx
export interface TabItem {
  value: string
  label: ReactNode
  panel: ReactNode
}

export interface TabsProps {
  items: TabItem[]
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  orientation?: 'horizontal' | 'vertical'
}
```

| Prop | Why it exists |
|---|---|
| `value` / `onValueChange` | Deep-linking, a "next" button in panel 2, analytics. This is the first follow-up you will get. |
| `defaultValue` | Uncontrolled start. Falls back to the first item. |
| `orientation` | Drives `aria-orientation` **and** which arrow keys apply. Two lines, big signal. |

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Tablist | `role="tablist"`, `aria-orientation` |
| Tab | `role="tab"`, `aria-selected`, `aria-controls` → panel, `id`, roving `tabIndex` |
| Panel | `role="tabpanel"`, `aria-labelledby` → tab, `id`, `hidden` when inactive, `tabIndex={0}` when it holds nothing focusable |

| Key | Behavior |
|---|---|
| `Tab` | Enters the tablist once, lands on the selected tab |
| `←` `→` (horizontal) / `↑` `↓` (vertical) | Move selection **and** focus, wrapping |
| `Home` / `End` | First / last tab |

**The panel's `tabIndex={0}` is conditional.** APG: *"When the tabpanel does not contain any
focusable elements or the first element with content is not focusable, the tabpanel should set
`tabindex="0"` to include it in the page's tab sequence."* Text-only panel → needs it, so
keyboard users can reach and scroll the content. Panel with a link or button → don't, or you add
a redundant stop before the real content.

### D. DECISIONS THAT MATTER

1. **Roving tabindex.** The tablist is ONE tab stop. `tabIndex={selected ? 0 : -1}` — and the
   `-1` is load-bearing (§17 A), because it's what keeps unselected tabs programmatically
   focusable so the arrow handler can reach them.
2. **Automatic activation.** Arrows move focus *and* select. Correct when panels are cheap. If a
   panel fetched, switch to manual: arrows move focus only, Enter/Space commits. → *"Automatic is
   right here since the panels are local; I'd go manual if selecting triggered a request."*
3. **`event.key`, not `event.code`.** `code` is physical key position, so numpad arrows arrive as
   `Numpad4` and slip through. This is a real bug in a lot of published solutions.
4. **All panels stay mounted, `hidden` toggles.** Find-in-page works, panel state survives.

### E. IMPLEMENTATION

**1 — Ids, controlled state, refs.**

```tsx
const baseId = useId()
const tabId = (v: string) => `${baseId}-tab-${v}`
const panelId = (v: string) => `${baseId}-panel-${v}`

const [internalValue, setInternalValue] = useState(defaultValue ?? items[0]?.value)
const isControlled = valueProp !== undefined
const value = isControlled ? valueProp : internalValue

const tabRefs = useRef<(HTMLButtonElement | null)[]>([])
```

`items[0]?.value` rather than `items[0].value` so an empty list degrades instead of throwing.

**2 — Orientation drives both the ARIA and the keys.**

```tsx
const prevKey = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft'
const nextKey = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight'
```

One prop, one source of truth. This is what stops the screen reader announcing "vertical" while
the CSS renders a horizontal row.

**3 — The handler.**

```tsx
function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
  const current = items.findIndex((item) => item.value === value)
  let next: number

  switch (event.key) {
    case prevKey: next = (current - 1 + items.length) % items.length; break
    case nextKey: next = (current + 1) % items.length; break
    case 'Home':  next = 0; break
    case 'End':   next = items.length - 1; break
    default: return
  }

  event.preventDefault()
  selectByIndex(next)
}
```

- `switch` on **computed** case values (`prevKey`/`nextKey`) — legal in JS, and it keeps the
  orientation logic in one place.
- `+ items.length` before the modulo, because `-1 % 3` is `-1` in JavaScript, not `2`.
- `preventDefault()` or Home/End scroll the page out from under the tabs.

**4 — Selection and focus move together.**

```tsx
function selectByIndex(index: number) {
  const item = items[index]
  if (!item) return
  select(item.value)
  tabRefs.current[index]?.focus()
}
```

A ref array, not `document.getElementById`. It keeps focus inside React's tree, so it still works
under a portal or shadow root, and there's no unguarded `.focus()` on a possible `null`.

**5 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Tabs</summary>

```tsx
import { useId, useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'

/**
 * Everything here is reachable in a 40-minute pairing round. Three things are
 * doing the heavy lifting, and they are the three worth saying out loud:
 *
 *   1. Controlled OR uncontrolled. The first follow-up to any tabs question is
 *      "how does the parent change the tab?" — deep-link, a Next button, analytics.
 *   2. useId. Hardcoded ids collide the moment two <Tabs> share a page.
 *   3. Roving tabindex. The tablist is ONE tab stop; arrows move within it.
 */

export interface TabItem {
  value: string
  label: ReactNode
  panel: ReactNode
}

export interface TabsProps {
  items: TabItem[]
  /** Controlled selection. Pair with onValueChange. */
  value?: string
  /** Uncontrolled initial selection. Defaults to the first item. */
  defaultValue?: string
  onValueChange?: (value: string) => void
  orientation?: 'horizontal' | 'vertical'
}

export function Tabs({
  items,
  value: valueProp,
  defaultValue,
  onValueChange,
  orientation = 'horizontal',
}: TabsProps) {
  const baseId = useId()
  const tabId = (v: string) => `${baseId}-tab-${v}`
  const panelId = (v: string) => `${baseId}-panel-${v}`

  // Controlled when `value` is passed, uncontrolled otherwise — never a mix.
  // The internal state still exists in controlled mode; it just stops being read.
  const [internalValue, setInternalValue] = useState(defaultValue ?? items[0]?.value)
  const isControlled = valueProp !== undefined
  const value = isControlled ? valueProp : internalValue

  // A ref array, not document.getElementById: keeps focus inside React's tree,
  // so this still works under a portal or a shadow root.
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])

  function select(next: string) {
    if (!isControlled) setInternalValue(next)
    onValueChange?.(next)
  }

  function selectByIndex(index: number) {
    const item = items[index]
    if (!item) return
    select(item.value)
    // Automatic activation: arrows move focus AND select. Right call when panels
    // are cheap. If a panel fetched, switch to manual — arrows move focus only,
    // Enter/Space commits.
    tabRefs.current[index]?.focus()
  }

  const prevKey = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft'
  const nextKey = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight'

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const current = items.findIndex((item) => item.value === value)
    let next: number

    // event.key, not event.code. `code` is the physical key position, so the
    // numpad arrows arrive as Numpad4/Numpad7 and would slip straight through.
    switch (event.key) {
      case prevKey:
        next = (current - 1 + items.length) % items.length
        break
      case nextKey:
        next = (current + 1) % items.length
        break
      case 'Home':
        next = 0
        break
      case 'End':
        next = items.length - 1
        break
      default:
        return
    }

    // Without this, Home/End scroll the page out from under the tabs.
    event.preventDefault()
    selectByIndex(next)
  }

  return (
    <div className="tabs" data-orientation={orientation}>
      <div
        className="tabs-list"
        role="tablist"
        aria-orientation={orientation}
        onKeyDown={handleKeyDown}
      >
        {items.map((item, i) => {
          const selected = item.value === value
          return (
            <button
              key={item.value}
              // Block body: a ref callback must return void or a cleanup function,
              // and `ref={(el) => (arr[i] = el)}` returns the element.
              ref={(el) => {
                tabRefs.current[i] = el
              }}
              id={tabId(item.value)}
              type="button"
              role="tab"
              className="tabs-tab"
              aria-selected={selected}
              aria-controls={panelId(item.value)}
              tabIndex={selected ? 0 : -1}
              onClick={() => select(item.value)}
            >
              {item.label}
            </button>
          )
        })}
      </div>

      {items.map((item) => {
        const selected = item.value === value
        return (
          <div
            key={item.value}
            id={panelId(item.value)}
            role="tabpanel"
            className="tabs-panel"
            aria-labelledby={tabId(item.value)}
            // APG makes the panel focusable only when it holds nothing focusable.
            // Scoped to the visible panel — a hidden one isn't reachable anyway.
            tabIndex={selected ? 0 : undefined}
            hidden={!selected}
          >
            {item.panel}
          </div>
        )
      })}
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| No `role="tab"` on the buttons | A tablist owning no tabs; `aria-selected` becomes meaningless |
| `tabIndex={selected ? 0 : undefined}` | Unselected tabs unfocusable by script → arrow keys do nothing |
| `event.code` instead of `event.key` | Numpad arrows and numpad Home/End silently ignored |
| No `preventDefault` | Home/End scroll the page while switching tabs |
| `(index - 1) % length` | `-1 % 3 === -1`; backward wrap lands nowhere |
| Hardcoded id prefix instead of `useId` | Two `<Tabs>` on a page cross-wire their panels |
| `tabIndex={0}` on every panel | Invisible tab stops if `hidden` is ever defeated by CSS |
| Uncontrolled only | No answer to "deep-link to a tab" |

### G. SPEC

**Selection** — first item selected by default · honors `defaultValue` · clicking shows its panel
and hides the previous

**Keyboard** — the whole tablist is a single tab stop · arrows move selection and focus together,
wrapping at both ends · Home/End · vertical orientation swaps to ↑/↓ and sets `aria-orientation`,
with horizontal arrows inert

**Controlled** — reports changes and does not move on its own · the parent can drive it from
outside

**Wiring** — every `aria-controls` and `aria-labelledby` resolves · two instances don't share ids

## 04 — Accordion / Disclosure

> Runnable: `uie-practice/src/exercises/accordion-reference/` · Spec: 16 tests

### A. ASKED AS

- "Build an accordion / FAQ list"
- "Build a collapsible section" (a single disclosure — this component with one item)
- "Make only one section open at a time" (the follow-up, so build for it)
- "Build a settings panel with expandable groups"

**The trap in the prompt itself:** if you're asked for *tabs* and you build this, you've failed
regardless of code quality. Tabs show one panel and use roving tabindex. An accordion shows any
number and does not. Confirm which one they mean in the first thirty seconds.

### B. API

```tsx
export interface AccordionItem {
  value: string          // stable identity — all ids derive from this
  header: ReactNode
  panel: ReactNode
}

export interface AccordionProps {
  items: AccordionItem[]
  value?: string[]              // controlled open set
  defaultValue?: string[]       // uncontrolled initial open set
  onValueChange?: (value: string[]) => void
  allowMultiple?: boolean       // false = opening one closes the rest
  collapsible?: boolean         // single mode: may the open item be closed?
  headingLevel?: 2 | 3 | 4
}
```

| Prop | Type | Default | Why it exists |
|---|---|---|---|
| `value` | `string[]` | — | Controlled. Deep-linking to an open section, "expand all" buttons. |
| `defaultValue` | `string[]` | `[]` | Uncontrolled start state. |
| `onValueChange` | `(v: string[]) => void` | — | Fires in **both** modes. Always reports the whole next set, not a delta. |
| `allowMultiple` | `boolean` | `false` | The single most likely follow-up question. |
| `collapsible` | `boolean` | `true` | Single mode only. `false` = "one is always open". |
| `headingLevel` | `2 \| 3 \| 4` | `3` | Must nest correctly in the surrounding document outline. |

**Why `string[]` and not `string | null`.** Radix models these as two components with different
value types (`type="single"` vs `"multiple"`). That's the better library API and the wrong
interview API — the discriminated-union gymnastics cost you ten minutes and buy nothing. One
array, with `allowMultiple` controlling the *transition rule*, is the right call under a clock.
Say that tradeoff out loud; it's the kind of scoping judgment being measured.

**Why `string[]` and not `Set<string>`.** The instinct that `Set` is faster is correct and
irrelevant. `Set.has()` is O(1) against `Array.includes()`'s O(n), but n here is three. The
decision is about API surface, not lookup cost:

| | `string[]` | `Set<string>` |
|---|---|---|
| Serializable | Yes — URL params, `localStorage`, SSR payload | No, needs conversion at every boundary |
| Caller ergonomics | They already have an array | They must build a `Set` to call you |
| Immutable update | `[...value, v]` / `value.filter(...)` | `new Set(prev)` then mutate then return |
| Lookup | O(n) | O(1) |

The third row is the sharp one. The `Set` update is three statements and the copy is easy to
forget — skip `new Set(prev)` and you mutate state in place, React sees the same reference, and
nothing re-renders. That bug is invisible in review and common in practice.

**When `Set` genuinely wins:** internal state with hundreds or thousands of members and frequent
membership checks — selected rows in a 10k-row table (§11), expanded nodes in a large tree
(§10). There the O(n) scan runs once per rendered row and it does show up.

**The best of both, if you're asked to scale it:** keep `string[]` as the public API and derive
a lookup set internally.

```tsx
const openSet = useMemo(() => new Set(value), [value])
// ...then openSet.has(item.value) in the render loop
```

Serializable at the boundary, O(1) inside. → *"I'd keep the prop an array so it round-trips
through a URL, and memo a Set internally if the list ever got big."*

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Heading | `<h2>`–`<h4>` wrapping the trigger. The heading is **not** the control. |
| Trigger | `<button>`, `aria-expanded`, `aria-controls` → panel id, `id` |
| Panel | `id`, `hidden` when closed. No `tabIndex` — that's the Tabs pattern, not this one. Optionally `role="region"` + `aria-labelledby` → header id (see the region rule below). |

| Key | Behavior | Required? |
|---|---|---|
| `Tab` | Moves to the **next header** — every header is its own tab stop | Yes |
| `Enter` / `Space` | Toggles the focused section | Yes (native button) |
| `↓` / `↑` | Move focus between headers, wrapping | Optional |
| `Home` / `End` | First / last header | Optional |

**No roving tabindex.** This is the single most important line in this section. Accordion
headers are independent buttons; a keyboard user expects Tab to walk them. Applying the tabs
pattern here actively breaks the widget.

**No `tabIndex` on the panels either.** Tabs panels take `tabIndex={0}` when they hold nothing
focusable; the accordion pattern does not. Carrying it over adds a dead tab stop between every
header.

**No role on the panel — and that's why it needs no name.** This is the other half of the Tabs
contrast, and it's the one people get backwards. A tabs panel *must* carry `role="tabpanel"`:
`role="tab"` is only valid inside a `tablist`, and its `aria-controls` is contractually supposed
to resolve to a tabpanel. Strip it and the failure is audible — "tab 2 of 3", activate, and
focus lands on an anonymous div. Disclosure has no composite structure to complete, so there is
no required role on the revealed content; `aria-expanded` on the trigger already carries it.

`aria-labelledby` then drops out for a mechanical reason, not a stylistic one: **a name only
exposes on an element whose role supports naming.** A roleless `<div>` computes as `generic`,
and ARIA prohibits naming generic elements — so `aria-labelledby` on a bare panel is dead
markup no AT will read. You cannot add the name without first adding a role.

It isn't needed structurally either. Tabs renders its panels in a *second, separate* `.map()`,
as siblings after the tablist — a panel is nowhere near its tab in the DOM, so it needs the
explicit back-pointer. The accordion panel is nested inside its `.accordion-item`, directly
after its own heading: the association is already in document order, and `aria-expanded` +
`aria-controls` supply the programmatic link in the other direction.

**THE REGION RULE.** APG *does* allow `role="region"` with `aria-labelledby` pointing at the
header button — and explicitly warns against it once an accordion has more than roughly six
panels, because every region is a landmark and landmark navigation drowns. The reference omits
it, which is the right default. Naming the rule out loud is worth more than either choice:

> *"I'd put `role='region'` on the panels if there were a handful of sections, and drop it if the
> list could grow — landmark proliferation is worse than no landmark."*

The general form is worth carrying to every component: **a role you add for its own sake costs
nothing; a role you add out of symmetry with a different pattern costs the user.**

### D. DECISIONS THAT MATTER

1. **Single vs multiple is a transition rule, not two components.** One `string[]`, one
   `allowMultiple` flag. → *"I'm modelling the open set as an array either way; `allowMultiple`
   just decides whether opening replaces or appends."*
2. **`collapsible: false` must make the click a no-op, not a close.** The "one is always open"
   variant is a real product requirement (settings panels, wizards), and getting it wrong
   produces a panel that closes and leaves the user staring at nothing.
3. **The heading wrapper is not optional.** It's how screen-reader users jump section to
   section. → *"APG wants the trigger inside a heading so heading navigation works; the button
   stays the interactive element."*
4. **Arrows move focus only — never open.** Unlike Tabs, where arrows select. An accordion whose
   arrow keys expand sections fires side effects during navigation.

### E. IMPLEMENTATION

**1 — Ids and controlled state.** Identical to every other component in this guide; that
sameness is the point.

```tsx
const baseId = useId()
const headerId = (v: string) => `${baseId}-header-${v}`
const panelId  = (v: string) => `${baseId}-panel-${v}`

const [internalValue, setInternalValue] = useState<string[]>(defaultValue ?? [])
const isControlled = valueProp !== undefined
const value = isControlled ? valueProp : internalValue

const headerRefs = useRef<(HTMLButtonElement | null)[]>([])

function commit(next: string[]) {
  if (!isControlled) setInternalValue(next)
  onValueChange?.(next)
}
```

- `useId()` gives a per-instance prefix; both id helpers take **`item.value`**, never the header
  text, so the trigger and the panel can compute each other's ids (§02 C).
- `isControlled` keys off `!== undefined` so that a legitimate `value={[]}` — everything closed —
  is still controlled (§17 C).
- The resolved state is called **`value`**, not `open`, in every component in this guide. It's
  worth the slight awkwardness of `value.includes(item.value)`: the same three lines then appear
  verbatim in Tabs, Accordion, Combobox and Menu, so it becomes one memorized block instead of
  five near-misses.
- `headerRefs` exists only for arrow-key focus. There's no roving tabindex to maintain.

**2 — The toggle. This is where `allowMultiple` and `collapsible` live.**

```tsx
function toggle(itemValue: string) {
  const isOpen = value.includes(itemValue)

  if (allowMultiple) {
    commit(isOpen ? value.filter((v) => v !== itemValue) : [...value, itemValue])
    return
  }

  if (isOpen) commit(collapsible ? [] : value)
  else commit([itemValue])
}
```

- The parameter is `itemValue`, not `value` — otherwise it shadows the resolved state one scope
  up and the function silently reads the wrong thing.
- Multiple mode: remove or append. The rest of the set is untouched.
- Single mode, currently open: `collapsible` decides. `commit(value)` — passing the *same* array
  back — is deliberately a no-op that still fires `onValueChange`, so a controlled parent sees
  the attempted interaction.
- Single mode, currently closed: `[itemValue]` replaces the whole set. That one line is the
  entire "opening one closes the others" behavior.
- Every branch produces a **new array**. Mutating in place would leave controlled parents holding
  a reference that changed underneath them, and React would skip the re-render.

**3 — Keyboard. Note what it does *not* do.**

```tsx
function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
  const current = headerRefs.current.indexOf(document.activeElement as HTMLButtonElement)
  if (current === -1) return

  let next: number
  switch (event.key) {
    case 'ArrowDown': next = (current + 1) % items.length; break
    case 'ArrowUp':   next = (current - 1 + items.length) % items.length; break
    case 'Home':      next = 0; break
    case 'End':       next = items.length - 1; break
    default: return
  }
  event.preventDefault()
  headerRefs.current[next]?.focus()
}
```

- **`indexOf(document.activeElement)`** rather than threading an index through each button. It
  also gives the guard for free: if focus is on a link *inside* an open panel, `current` is `-1`
  and the handler bails, so panel content keeps its own arrow-key behavior.
- **`(current - 1 + items.length) % items.length`** — the `+ items.length` is what makes the
  backward wrap work. `-1 % 3` is `-1` in JavaScript, not `2`.
- **`event.preventDefault()`** or Home/End scroll the page out from under the widget.
- **`.focus()` and nothing else.** No `commit()` here. Arrows navigate; Enter and Space toggle.

**4 — The heading and trigger.**

```tsx
const Heading = `h${headingLevel}` as 'h2' | 'h3' | 'h4'

<Heading className="accordion-heading">
  <button
    ref={(el) => { headerRefs.current[i] = el }}
    id={headerId(item.value)}
    type="button"
    aria-expanded={isOpen}
    aria-controls={panelId(item.value)}
    onClick={() => toggle(item.value)}
  >
    <span className="accordion-marker" aria-hidden="true" />
    {item.header}
  </button>
</Heading>
```

- A capitalized variable holding a tag string is how you render a dynamic element type; lowercase
  would be treated as a literal DOM tag named `heading`.
- **`ref` uses a block body.** `ref={(el) => (refs.current[i] = el)}` returns the element, and
  React 19 treats a ref callback's return value as a cleanup function. TypeScript rejects it
  outright (§17 J).
- **`aria-expanded` on the button, never the heading.** The button is the control.
- **`type="button"`** — inside a form, the default `type="submit"` makes every header submit it.
- The marker triangle is `aria-hidden`; it carries no information that `aria-expanded` doesn't
  already convey, and announcing "▸" is noise. It's rotated by CSS keyed off
  `[aria-expanded='true']`, so the visual and the semantic state cannot drift (§02 D).

**5 — The panel. Notice how little there is.**

```tsx
<div id={panelId(item.value)} hidden={!isOpen}>
  {item.panel}
</div>
```

- **An `id`, and that's the only required attribute.** It exists so the trigger's `aria-controls`
  resolves. `aria-expanded` on the button already tells assistive tech the state.
- **`hidden` rather than `{isOpen && <div>}`.** The panel stays in the DOM, so browser
  find-in-page finds closed content and any component state inside survives a collapse. The
  cost: `[hidden]` is a low-specificity UA rule, so a stray `display` declaration in your CSS
  defeats it silently.
- **No `tabIndex={0}`.** Tabs panels take it (APG asks for it when the panel has no focusable
  content); the accordion pattern does not. Copying it across adds a dead tab stop between every
  header — and the spec has a test for exactly that.

**6 — THE WHOLE THING.** Every chunk above, assembled, including the `items.map()` the fragments
left out. Around 95 lines, and a realistic target for 25 minutes.

<details>
<summary>Complete implementation — Accordion</summary>

```tsx
import { useId, useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'

/**
 * The contrast with Tabs is the whole lesson, and it's the thing to say out loud:
 *
 *   Tabs      one panel visible · roving tabindex · arrow keys REQUIRED
 *   Accordion any number visible · every header is a tab stop · arrows OPTIONAL
 *
 * Reaching for roving tabindex here would be wrong. Accordion headers are
 * independent buttons; a keyboard user expects Tab to walk them.
 */

export interface AccordionItem {
  value: string
  header: ReactNode
  panel: ReactNode
}

export interface AccordionProps {
  items: AccordionItem[]
  /** Controlled open set. Pair with onValueChange. */
  value?: string[]
  /** Uncontrolled initial open set. Defaults to all closed. */
  defaultValue?: string[]
  onValueChange?: (value: string[]) => void
  /** false = radio behavior: opening one closes the rest. */
  allowMultiple?: boolean
  /** Single mode only: may the open item be closed again? */
  collapsible?: boolean
  /** Headings must nest correctly in the surrounding document outline. */
  headingLevel?: 2 | 3 | 4
}

export function Accordion({
  items,
  value: valueProp,
  defaultValue,
  onValueChange,
  allowMultiple = false,
  collapsible = true,
  headingLevel = 3,
}: AccordionProps) {
  const baseId = useId()
  const headerId = (v: string) => `${baseId}-header-${v}`
  const panelId = (v: string) => `${baseId}-panel-${v}`

  // Same controlled/uncontrolled shape as Tabs. Worth keeping identical across
  // every component you write — the reviewer sees one idea, not five.
  const [internalValue, setInternalValue] = useState<string[]>(defaultValue ?? [])
  const isControlled = valueProp !== undefined
  const value = isControlled ? valueProp : internalValue

  const headerRefs = useRef<(HTMLButtonElement | null)[]>([])

  function commit(next: string[]) {
    if (!isControlled) setInternalValue(next)
    onValueChange?.(next)
  }

  function toggle(itemValue: string) {
    const isOpen = value.includes(itemValue)
    if (allowMultiple) {
      commit(isOpen ? value.filter((v) => v !== itemValue) : [...value, itemValue])
      return
    }
    // Single mode. `collapsible: false` is the "one is always open" variant —
    // clicking the open header must then be a no-op, not a close.
    if (isOpen) commit(collapsible ? [] : value)
    else commit([itemValue])
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    // Which header has focus? Reading it off the refs means panel content that
    // happens to be focusable doesn't get hijacked by these arrow keys.
    // Which header has focus? Reading it off the refs also means focus sitting on
    // a link inside an open panel falls through (current === -1) and keeps its
    // own arrow-key behavior.
    const current = headerRefs.current.indexOf(document.activeElement as HTMLButtonElement)
    if (current === -1) return

    let next: number
    switch (event.key) {
      case 'ArrowDown':
        next = (current + 1) % items.length
        break
      case 'ArrowUp':
        next = (current - 1 + items.length) % items.length
        break
      case 'Home':
        next = 0
        break
      case 'End':
        next = items.length - 1
        break
      default:
        return
    }
    event.preventDefault()
    // Arrows move focus ONLY. Unlike Tabs, they must not open anything —
    // an accordion header's expanded state belongs to Enter/Space.
    headerRefs.current[next]?.focus()
  }

  const Heading = `h${headingLevel}` as 'h2' | 'h3' | 'h4'

  return (
    <div className="accordion" onKeyDown={handleKeyDown}>
      {items.map((item, i) => {
        const isOpen = value.includes(item.value)
        return (
          <div className="accordion-item" key={item.value}>
            {/* APG requires the trigger to be wrapped in a heading so screen
                reader users can jump section to section by heading. The button
                stays the interactive element — never put onClick on the h3. */}
            <Heading className="accordion-heading">
              <button
                ref={(el) => {
                  headerRefs.current[i] = el
                }}
                id={headerId(item.value)}
                type="button"
                className="accordion-trigger"
                aria-expanded={isOpen}
                aria-controls={panelId(item.value)}
                onClick={() => toggle(item.value)}
              >
                <span className="accordion-marker" aria-hidden="true" />
                {item.header}
              </button>
            </Heading>

            {/* No tabIndex here. Tabs panels take tabIndex={0} when they hold no
                focusable content; the accordion pattern does not, and copying it
                across adds a dead tab stop between every header. */}
            <div id={panelId(item.value)} className="accordion-panel" hidden={!isOpen}>
              {item.panel}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

</details>

Three things only visible once it's assembled:

- **The `key` is `item.value`, not `i`.** The index is used solely for `headerRefs`, where
  position genuinely is the identity. Keys must survive reordering; ref slots don't need to.
- **`onKeyDown` sits on the outer wrapper**, not on each button — one listener, and the handler
  works out which header has focus by looking it up. Attaching it per-button would mean
  threading the index into every handler.
- **`Heading` is computed once above the loop**, not per item. A capitalized binding holding a
  tag string is how you render a dynamic element type.

### F. TRAPS

| Trap | Symptom |
|---|---|
| Roving tabindex copied from Tabs | Tab skips past the whole accordion; only one header reachable |
| `aria-controls` with no matching `id` | Silent — nothing visibly breaks, and it fails every audit |
| `tabIndex={0}` on panels, copied from Tabs | A dead tab stop between every header |
| No heading wrapper | Screen-reader users can't jump between sections at all |
| Arrows also toggle | Navigating fires side effects; content shifts under the user |
| `collapsible={false}` implemented as "close then reopen" | A visible flash, and an empty panel if the reopen is async |
| Mutating the open array | Controlled parents see stale references; memoized children don't re-render |
| Index as `key` | Reordering or filtering items swaps panel content between headers |

### G. SPEC

The 16 assertions in `accordion-reference.test.tsx`, as a list to name out loud:

**Open state** — starts closed · honors `defaultValue` · single mode closes the previous ·
`allowMultiple` keeps both · a second click closes · `collapsible={false}` makes it a no-op

**Keyboard** — every header is its own tab stop *(this is the test that proves it isn't roving
tabindex)* · arrows move focus and wrap without opening anything · Home/End · Enter toggles

**Controlled** — reports the whole next set and does not move on its own · the parent can drive
it from outside

**Wiring** — every `aria-controls` resolves to a real panel · each trigger is wrapped in a
heading at the requested level · panels add no tab stops of their own · two instances don't
share ids

The two worth stealing for every component you build: **"every `aria-controls` resolves"** and
**"two instances don't collide."** Four lines each, and between them they catch the majority of
component-level accessibility bugs.

## 05 — Modal / Dialog

> Runnable: `uie-practice/src/exercises/modal-reference/` · Spec: 14 tests

### A. ASKED AS

- "Build a modal" / "a confirmation dialog" / "a settings drawer"
- "Implement a focus trap" — the sub-problem, asked directly

### B. API

```tsx
export interface ModalProps {
  open: boolean                              // controlled only
  onClose: () => void
  title: ReactNode                           // visible heading AND the accessible name
  children: ReactNode
  initialFocus?: RefObject<HTMLElement | null>
  returnFocus?: RefObject<HTMLElement | null>
  closeOnBackdrop?: boolean
}
```

**Controlled only, and say why.** Every other component here offers both modes. A dialog whose
open state the parent can't drive is useless — the parent is what decides a dialog should exist.
There is no sensible `defaultOpen`.

`title` is deliberately not optional and not an `aria-label`. Forcing a real heading means the
dialog always has both a visible title and an accessible name, from one prop.

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Dialog | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` → title, `tabIndex={-1}` |
| Title | real heading element with the referenced `id` |

`aria-modal="true"` tells AT to ignore everything outside. It is a **declaration, not
enforcement** — it does not stop a sighted mouse user reaching the page behind. Real inertness
needs the `inert` attribute on siblings. Naming that gap is worth more than pretending it isn't
there.

`tabIndex={-1}` on the dialog gives focus somewhere to land when the content holds nothing
focusable.

| Key | Behavior |
|---|---|
| `Esc` | Close. Innermost dialog only. |
| `Tab` / `Shift+Tab` | Cycle within, wrapping at the two edges only |

### D. DECISIONS THAT MATTER

Four of the five are focus. That ordering is the point.

1. **Portal to `<body>`.** `position: fixed` positions against the viewport *unless* an ancestor
   has `transform`, `filter`, `perspective`, `contain`, or `will-change` — any of which makes that
   ancestor the containing block. Plus `overflow: hidden` clips, and `z-index` can't escape a
   parent stacking context. Portalling sidesteps all three (§17 I).
2. **Mounting IS the state machine.** Render nothing when closed, and every effect runs exactly
   once per opening and cleans up exactly on close. No `if (!open) return` guard smeared through
   five effects.
3. **Restore focus, and handle the trigger being gone.** The `isConnected` check is not defensive
   decoration — `.focus()` on a detached node fails *silently*, so it's the only way to know
   restore failed and route focus somewhere deliberate.
4. **Trap only at the edges.** Intercept Tab when focus is on the first or last focusable element;
   let the browser handle everything between. Reimplementing full tab order breaks screen-reader
   navigation modes.
5. **Backdrop dismissal needs the pointerdown half.** Otherwise selecting text inside the dialog
   and releasing outside closes it and throws the work away.

### E. IMPLEMENTATION

**1 — Split on `open` so the effects are clean.**

```tsx
export function Modal({ open, ...rest }: ModalProps) {
  if (!open) return null
  return createPortal(<ModalContent {...rest} />, document.body)
}
```

The early return before any hook is legal because `Modal` itself uses none. All the state lives in
`ModalContent`, which only exists while open.

**2 — Focus in, focus back.**

```tsx
useEffect(() => {
  const previouslyFocused = document.activeElement as HTMLElement | null

  const target =
    initialFocus?.current ?? focusableWithin(dialogRef.current!)[0] ?? dialogRef.current
  target?.focus()

  return () => {
    if (previouslyFocused?.isConnected) previouslyFocused.focus()
    else returnFocus?.current?.focus()
  }
}, [initialFocus, returnFocus])
```

The three-step fallback — explicit target, then first focusable, then the dialog itself — means
focus always lands somewhere. For a destructive confirmation, pass `initialFocus` pointing at
Cancel; never open with the irreversible action pre-focused.

**3 — Finding focusables.** You are not expected to write this selector from memory (§17 B). The
interview answer is "native `<dialog>` with `showModal()`, or `focus-trap`". The one detail worth
remembering is the filter:

```tsx
(el) => !el.closest('[hidden]') && el.getAttribute('aria-hidden') !== 'true'
```

Not `el.offsetParent !== null`. That's the tempting one-liner, and `offsetParent` is also `null`
for every `position: fixed` element — a fixed toolbar inside the dialog would silently drop out of
the trap.

**4 — Edge-only Tab wrapping and Escape.**

```tsx
if (event.key === 'Escape') {
  event.stopPropagation()
  onClose()
  return
}
```

`stopPropagation` so a nested dialog closes only itself. Because focus is inside the dialog, this
keydown bubbles here first — no document-level listener, and therefore no ordering puzzle between
two open dialogs.

**5 — Scroll lock that survives nesting.**

```tsx
const previous = document.body.style.overflow
document.body.style.overflow = 'hidden'
return () => { document.body.style.overflow = previous }
```

Restore the *previous* value rather than clearing it, or closing an inner dialog unlocks the page
while the outer one is still open.

**6 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Modal</summary>

```tsx
import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { KeyboardEvent, MouseEvent, PointerEvent, ReactNode, RefObject } from 'react'

/**
 * Five things are load-bearing, and four of them are focus:
 *
 *   1. Portal out to <body>, so an ancestor's overflow/transform can't clip or
 *      re-parent the dialog's containing block.
 *   2. Move focus IN on open.
 *   3. Trap Tab inside while open.
 *   4. Put focus BACK on close — including when the trigger no longer exists.
 *   5. Escape closes, and the innermost dialog wins.
 *
 * Everything else (scroll lock, backdrop click) is polish you can name and skip
 * under time pressure. Focus is not.
 */

/** Everything the browser will hand focus to via Tab. */
const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function focusableWithin(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    // A node inside a `hidden` subtree still matches the selector but cannot take
    // focus, so it has to be filtered out or Tab appears to stick.
    //
    // The tempting one-liner here is `el.offsetParent !== null`. Don't: offsetParent
    // is also null for every position:fixed element, so a fixed toolbar inside the
    // dialog would silently drop out of the trap.
    (el) => !el.closest('[hidden]') && el.getAttribute('aria-hidden') !== 'true',
  )
}

export interface ModalProps {
  /** Controlled only. A dialog whose open state the parent can't drive is useless. */
  open: boolean
  onClose: () => void
  /** Names the dialog. Rendered as the visible heading and wired to aria-labelledby. */
  title: ReactNode
  children: ReactNode
  /** Where focus lands on open. Defaults to the first focusable node inside. */
  initialFocus?: RefObject<HTMLElement | null>
  /** Where focus goes on close when the trigger no longer exists. */
  returnFocus?: RefObject<HTMLElement | null>
  /** Clicking the backdrop closes. Turn off for destructive confirmations. */
  closeOnBackdrop?: boolean
}

export function Modal({ open, ...rest }: ModalProps) {
  // Mount/unmount IS the state machine. Rendering nothing when closed means every
  // effect below runs exactly once per opening and cleans up exactly on close —
  // no `if (!open) return` guard smeared through five different effects.
  if (!open) return null
  return createPortal(<ModalContent {...rest} />, document.body)
}

function ModalContent({
  onClose,
  title,
  children,
  initialFocus,
  returnFocus,
  closeOnBackdrop = true,
}: Omit<ModalProps, 'open'>) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const pointerDownTarget = useRef<EventTarget | null>(null)

  // Focus in on mount, focus back on unmount.
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null

    const target = initialFocus?.current ?? focusableWithin(dialogRef.current!)[0] ?? dialogRef.current
    target?.focus()

    return () => {
      // The trigger can disappear while the dialog is open — think a row's
      // "Delete" button whose row the dialog just deleted.
      //
      // .focus() on a detached node doesn't throw, it silently does nothing and
      // focus falls to <body>, stranding a keyboard user at the top of the page.
      // Because the failure is silent, the isConnected check isn't defensive
      // decoration: it is the only way to know restore failed and route focus
      // somewhere deliberate instead.
      if (previouslyFocused?.isConnected) previouslyFocused.focus()
      // Reading .current at cleanup time is the point here. The lint rule's usual
      // advice — copy the ref into a variable inside the effect — would capture
      // whatever existed when the dialog OPENED, and the fallback target is
      // precisely the thing that may have been added or replaced while it was open.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      else returnFocus?.current?.focus()
    }
  }, [initialFocus, returnFocus])

  // Scroll lock. Restore the previous value rather than clearing it, so nested
  // dialogs don't unlock the page when the inner one closes.
  useEffect(() => {
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [])

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      // stopPropagation so a nested dialog closes only itself. Because focus is
      // inside the dialog, this keydown bubbles here first — no document-level
      // listener, and therefore no ordering puzzle between two open dialogs.
      event.stopPropagation()
      onClose()
      return
    }

    if (event.key !== 'Tab') return

    const focusable = focusableWithin(dialogRef.current!)
    if (focusable.length === 0) {
      // Nothing to move to; keep focus on the dialog itself rather than letting
      // Tab escape to the page behind.
      event.preventDefault()
      return
    }

    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    // Wrap only at the two edges. Everywhere else, native Tab already does the
    // right thing — reimplementing it is how you break screen-reader modes.
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    pointerDownTarget.current = event.target
  }

  function handleClick(event: MouseEvent<HTMLDivElement>) {
    if (!closeOnBackdrop) return
    // Close only when the gesture STARTED and ENDED on the backdrop. Without the
    // pointerdown half, selecting text inside the dialog and releasing outside it
    // closes the dialog and throws away what the user typed.
    const startedOnBackdrop = pointerDownTarget.current === event.currentTarget
    const endedOnBackdrop = event.target === event.currentTarget
    if (startedOnBackdrop && endedOnBackdrop) onClose()
  }

  return (
    <div
      className="modal-backdrop"
      onPointerDown={handlePointerDown}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
    >
      <div
        ref={dialogRef}
        role="dialog"
        // aria-modal tells assistive tech to ignore everything outside this node.
        // It is a declaration, not enforcement: it does not stop a sighted mouse
        // user reaching the page behind. Real inertness needs `inert` on siblings.
        aria-modal="true"
        aria-labelledby={titleId}
        // The dialog container itself is focusable so there is somewhere to put
        // focus when the content has no focusable elements at all.
        tabIndex={-1}
        className="modal-dialog"
      >
        <h2 id={titleId} className="modal-title">
          {title}
        </h2>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| No portal | A transformed ancestor traps the "fixed" dialog inside a card |
| Focus never moves in | Keyboard users are still behind the dialog, tabbing through the page |
| Focus never restored | Focus falls to `<body>`; the user restarts from the top |
| Restore without `isConnected` | Silent failure whenever the trigger unmounted |
| Reimplementing full tab order | Breaks screen-reader browse mode |
| `offsetParent` used to filter focusables | Fixed-position elements silently drop out of the trap |
| Backdrop close on `click` alone | Select text inside, release outside → dialog closes, work lost |
| Scroll lock cleared instead of restored | Closing a nested dialog unlocks the page underneath |
| Escape on a document listener | Two open dialogs both close |

### G. SPEC

**Structure** — renders nothing while closed · is a named modal dialog whose name comes from a
real heading · portals out of the React container to `<body>`

**Focus** — moves to the first focusable on open · `initialFocus` overrides · Tab wraps last→first
· Shift+Tab wraps first→last · returns to the trigger on close · falls back to `returnFocus` when
the trigger unmounted

**Dismissal** — Escape closes · a click starting and ending on the backdrop closes · a drag
starting inside and ending on the backdrop does **not** · `closeOnBackdrop={false}` ignores it

**Scroll lock** — locks the body while open and restores the previous value

## 06 — Combobox / Typeahead

> Runnable: `uie-practice/src/exercises/combobox-reference/` · Spec: 16 tests

### A. ASKED AS

- "Build an autocomplete / typeahead / search-as-you-type"
- "Build a country picker with search"
- "Build a @-mention input" — same machinery, different trigger

### B. API

```tsx
export interface ComboboxOption { value: string; label: string }

export interface ComboboxProps {
  label: string
  fetchOptions: (query: string, signal: AbortSignal) => Promise<ComboboxOption[]>
  value?: ComboboxOption | null
  defaultValue?: ComboboxOption | null
  onValueChange?: (option: ComboboxOption | null) => void
  debounceMs?: number
  minChars?: number
  placeholder?: string
}
```

**Two deliberate API calls worth stating out loud:**

- **`fetchOptions` takes the `AbortSignal`.** Passing the signal *out* to the consumer is what
  makes cancellation their problem to honor and yours to trigger. A `fetchOptions(query)` that
  can't be cancelled forces you to guard purely on your own side.
- **The query is NOT part of the controlled API.** Only the *selection* is. The query is transient
  typing state; a parent that owned it would have to re-render on every keystroke just to hand
  back what was typed. Selection is what a form submits.

`fetchOptions` must be referentially stable — it's an effect dependency. `useCallback` it, or the
fetch re-runs on every parent render.

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Input | `role="combobox"` **on the input itself**, `aria-expanded`, `aria-controls`, `aria-autocomplete="list"`, `aria-activedescendant`, `aria-busy` |
| Listbox | `role="listbox"`, `id`, accessible name |
| Option | `role="option"`, `aria-selected`, `id` |

APG 1.2 puts `role="combobox"` on the input. The older 1.0 pattern wrapped it in a combobox div —
that markup is now wrong, and it's what most older blog posts show.

| Key | Behavior |
|---|---|
| `↓` / `↑` | Move the **virtual** cursor; open if closed. Wraps. |
| `Home` / `End` | First / last option (only when open) |
| `Enter` | Select highlighted. Only swallowed when it actually picks something. |
| `Esc` | First press closes the list; second clears the field |
| `Tab` | Move on **without** selecting |

### D. DECISIONS THAT MATTER

1. **Focus never leaves the input.** Arrow keys move `aria-activedescendant` — a virtual cursor —
   not real DOM focus. Moving real focus into the list would stop the user typing, which is the
   entire point of a typeahead. This is the opposite of Tabs, Menu and Tree. → *"It's a virtual
   cursor because focus has to stay in the input; a roving tabindex would break typing."*
2. **Two race guards, and they are not redundant.** `AbortController` stops the network; the
   generation counter is what makes stale responses lose (§17 F). Abort doesn't un-queue a `.then`
   that already resolved, and plenty of sources ignore the signal — a cache hit, a shared
   in-flight map, a mock in your own tests.
3. **Escape is two-stage.** Closing and clearing at once destroys typing the user can't get back.
4. **Select on `mousedown`, not `click`.** `click` lands after the input's `blur` has already
   closed the list, so the handler never fires. `preventDefault()` on mousedown keeps focus in the
   input.
5. **Typing after selecting clears the selection.** Otherwise a form submits the old value with
   new-looking text in the box.

### E. IMPLEMENTATION

**1 — Derive, don't reset.**

```tsx
const q = query.trim()
const enabled = q.length >= minChars
const options = enabled ? rawOptions : []
const status: Status = enabled ? rawStatus : 'idle'
```

The obvious version resets `options`/`status` from inside the effect when the query drops below
`minChars`. That's a synchronous `setState` in an effect body — a cascading render, and something
React's lint correctly rejects. **If a value can be computed during render, compute it during
render.**

**2 — Debounce and fetch in ONE effect.**

```tsx
useEffect(() => {
  if (!enabled) return

  const controller = new AbortController()
  const generation = ++generationRef.current

  const timer = setTimeout(() => {
    setStatus('loading')
    fetchOptions(q, controller.signal)
      .then((next) => {
        if (generation !== generationRef.current) return
        setOptions(next)
        setStatus('ready')
        setActiveIndex(next.length > 0 ? 0 : -1)
      })
      .catch(() => {
        if (controller.signal.aborted) return
        if (generation !== generationRef.current) return
        setStatus('error')
      })
  }, debounceMs)

  return () => {
    clearTimeout(timer)
    controller.abort()
  }
}, [q, enabled, debounceMs, fetchOptions])
```

- **One cleanup cancels both** the pending debounce and the in-flight request. Without the abort,
  a fast typist opens one socket per character.
- **`setStatus('loading')` is inside the timeout**, not beside it, so "loading" means a request is
  actually in flight rather than that a key was pressed. It also keeps the previous results on
  screen during the debounce window instead of flashing.
- **Pre-highlight index 0** so Enter is immediately useful — but never auto-select, which would
  fight the typing.

**3 — The virtual cursor.**

```tsx
aria-activedescendant={showList && activeIndex >= 0 ? optionId(activeIndex) : undefined}
```

The input keeps DOM focus the whole time; this attribute is what tells AT which option is current.
The highlighted option carries `aria-selected`, and the CSS styles off that attribute so the
visual and announced states can't disagree.

**4 — Announce the count.**

```tsx
<div className="visually-hidden" role="status" aria-live="polite">
  {showList ? message : ''}
</div>
```

Sighted users see the list appear. Screen reader users get nothing unless the count is spoken —
"3 results", "No results". The `.visually-hidden` class must use the clip technique;
`display: none` would remove it from the accessibility tree and it would never announce (§17 E).

**5 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Combobox</summary>

```tsx
import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

/**
 * Two ideas carry this component, and both are counter-intuitive:
 *
 * 1. FOCUS NEVER LEAVES THE INPUT. Arrow keys move a *virtual* cursor via
 *    aria-activedescendant, not real DOM focus. Moving real focus into the list
 *    would stop the user typing — which is the entire point of a typeahead.
 *    This is the opposite of the roving tabindex used by Tabs and Tree.
 *
 * 2. AN ABORTED REQUEST IS NOT A CANCELLED RESULT. AbortController stops the
 *    network; it does not un-queue a `.then` that already resolved. The
 *    generation counter is what actually makes stale responses lose.
 */

export interface ComboboxOption {
  value: string
  label: string
}

export interface ComboboxProps {
  /** Accessible name for the input. */
  label: string
  /** Must be stable — it's an effect dependency. useCallback it in the parent. */
  fetchOptions: (query: string, signal: AbortSignal) => Promise<ComboboxOption[]>
  /** Controlled selection. Pair with onValueChange. */
  value?: ComboboxOption | null
  defaultValue?: ComboboxOption | null
  onValueChange?: (option: ComboboxOption | null) => void
  debounceMs?: number
  /** Don't fire a request for a single stray keystroke. */
  minChars?: number
  placeholder?: string
}

type Status = 'idle' | 'loading' | 'ready' | 'error'

export function Combobox({
  label,
  fetchOptions,
  value: valueProp,
  defaultValue = null,
  onValueChange,
  debounceMs = 200,
  minChars = 1,
  placeholder,
}: ComboboxProps) {
  const baseId = useId()
  const inputId = `${baseId}-input`
  const listboxId = `${baseId}-listbox`
  const optionId = (index: number) => `${baseId}-option-${index}`

  const [internalValue, setInternalValue] = useState<ComboboxOption | null>(defaultValue)
  const isControlled = valueProp !== undefined
  const selected = isControlled ? valueProp : internalValue

  // The query is deliberately NOT part of the controlled API. It's transient
  // typing state; a parent that owned it would have to re-render on every
  // keystroke to give you back what you just typed.
  const [query, setQuery] = useState(selected?.label ?? '')
  const [rawOptions, setOptions] = useState<ComboboxOption[]>([])
  const [rawStatus, setStatus] = useState<Status>('idle')
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  const generationRef = useRef(0)
  const listRef = useRef<HTMLUListElement>(null)

  const q = query.trim()
  // Derived, not stored. Resetting options/status from inside the effect when the
  // query drops below minChars would be a synchronous setState in an effect body —
  // a cascading render, and something React's lint rule correctly rejects. If a
  // value can be computed during render, compute it during render.
  const enabled = q.length >= minChars
  const options = enabled ? rawOptions : []
  const status: Status = enabled ? rawStatus : 'idle'

  useEffect(() => {
    if (!enabled) return

    const controller = new AbortController()
    // Bump on every request; only the newest generation is allowed to write state.
    const generation = ++generationRef.current

    const timer = setTimeout(() => {
      // Inside the timeout, not beside it: "loading" should mean a request is
      // actually in flight, not that a key was pressed. It also keeps the last
      // results on screen during the debounce window instead of flashing.
      setStatus('loading')
      fetchOptions(q, controller.signal)
        .then((next) => {
          // The two guards are not redundant.
          //   signal.aborted  → the request we cancelled, if the source honors it
          //   generation      → everything else: a cache hit that resolved
          //                     synchronously, a source that ignores the signal,
          //                     or a promise that resolved microseconds before abort
          if (generation !== generationRef.current) return
          setOptions(next)
          setStatus('ready')
          // Pre-highlight the first result so Enter is immediately useful, but
          // do not auto-select it — that would fight the user's typing.
          setActiveIndex(next.length > 0 ? 0 : -1)
        })
        .catch(() => {
          if (controller.signal.aborted) return
          if (generation !== generationRef.current) return
          setStatus('error')
        })
    }, debounceMs)

    // Runs on every keystroke: cancels the pending debounce AND the in-flight
    // request. Without the abort, a fast typist opens one socket per character.
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [q, enabled, debounceMs, fetchOptions])

  // Keep the highlighted option visible without moving focus.
  useEffect(() => {
    if (activeIndex < 0) return
    const el = listRef.current?.children[activeIndex] as HTMLElement | undefined
    // jsdom has no layout, so scrollIntoView may not exist. Optional-call rather
    // than mocking it in every test.
    el?.scrollIntoView?.({ block: 'nearest' })
  }, [activeIndex])

  function commit(option: ComboboxOption | null) {
    if (!isControlled) setInternalValue(option)
    onValueChange?.(option)
  }

  function select(option: ComboboxOption) {
    commit(option)
    setQuery(option.label)
    setOpen(false)
    setActiveIndex(-1)
  }

  function move(delta: number) {
    if (options.length === 0) return
    setActiveIndex((i) => {
      // From "nothing highlighted", ArrowUp should land on the last option.
      if (i === -1) return delta > 0 ? 0 : options.length - 1
      return (i + delta + options.length) % options.length
    })
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault() // else the caret jumps to the end of the input
        if (!open) setOpen(true)
        else move(1)
        break
      case 'ArrowUp':
        event.preventDefault()
        if (!open) setOpen(true)
        else move(-1)
        break
      case 'Home':
        if (!open) return
        event.preventDefault()
        setActiveIndex(0)
        break
      case 'End':
        if (!open) return
        event.preventDefault()
        setActiveIndex(options.length - 1)
        break
      case 'Enter':
        if (!open || activeIndex < 0) return
        // Only swallow Enter when it actually picks something, so the form this
        // combobox sits in can still be submitted from the input.
        event.preventDefault()
        select(options[activeIndex])
        break
      case 'Escape':
        // First Escape closes the list, a second clears the field. Closing and
        // clearing at once destroys work the user can't get back.
        if (open) setOpen(false)
        else {
          setQuery('')
          commit(null)
        }
        break
      case 'Tab':
        // Tab must move on, never select. Leaving the list open would strand a
        // popup over content the user has already moved past.
        setOpen(false)
        break
      default:
        break
    }
  }

  const showList = open && status !== 'idle'
  const message =
    status === 'loading'
      ? 'Loading results'
      : status === 'error'
        ? 'Could not load results'
        : status === 'ready'
          ? options.length === 0
            ? 'No results'
            : `${options.length} result${options.length === 1 ? '' : 's'}`
          : ''

  return (
    <div className="combobox">
      <label className="combobox-label" htmlFor={inputId}>
        {label}
      </label>

      {/* APG 1.2 puts role="combobox" on the INPUT itself, not on a wrapper.
          The older 1.0 pattern wrapped it; that markup is now wrong. */}
      <input
        id={inputId}
        type="text"
        className="combobox-input"
        role="combobox"
        autoComplete="off"
        aria-expanded={showList}
        aria-controls={listboxId}
        aria-autocomplete="list"
        // The virtual cursor. Points at an option's id while real focus stays here.
        aria-activedescendant={showList && activeIndex >= 0 ? optionId(activeIndex) : undefined}
        aria-busy={status === 'loading'}
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setActiveIndex(-1)
          // Typing after choosing means the choice is stale. Say so immediately
          // rather than letting a submitted form carry the old selection.
          if (selected) commit(null)
        }}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (query.trim().length >= minChars) setOpen(true)
        }}
        onBlur={() => setOpen(false)}
      />

      {/* Announced, not shown. Sighted users can see the list appear; screen
          reader users get nothing unless the count is spoken. */}
      <div className="visually-hidden" role="status" aria-live="polite">
        {showList ? message : ''}
      </div>

      <ul
        ref={listRef}
        id={listboxId}
        role="listbox"
        aria-label={label}
        className="combobox-listbox"
        hidden={!showList}
      >
        {status === 'ready' &&
          options.map((option, i) => (
            <li
              key={option.value}
              id={optionId(i)}
              role="option"
              className="combobox-option"
              aria-selected={i === activeIndex}
              // onMouseDown, not onClick: onClick lands after the input's blur has
              // already closed the list, so the click never reaches this element.
              onMouseDown={(e) => {
                e.preventDefault() // keep focus in the input
                select(option)
              }}
              onMouseEnter={() => setActiveIndex(i)}
            >
              {option.label}
            </li>
          ))}
      </ul>

      {/* Outside the listbox on purpose: a listbox may only own `option` children,
          so a "Loading…" <li> in there is invalid ARIA. Visual only — the live
          region above is what actually gets announced. */}
      {showList && (status !== 'ready' || options.length === 0) && (
        <p className="combobox-message" aria-hidden="true">
          {message}
        </p>
      )}
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| Moving real focus into the list | The user can't keep typing — the component's whole purpose |
| `AbortController` with no generation counter | A stale response still overwrites newer results |
| Equal-latency mocks in the demo | The race is invisible and you ship it |
| Unmemoized `fetchOptions` | Refetches on every parent render |
| `onClick` on options | Blur closes the list first; the handler never fires |
| Resetting state from inside the effect | Cascading render; lint error |
| One-stage Escape | Closing the list also wipes what was typed |
| Tab selects the highlighted option | Users lose what they typed by navigating away |
| Selection kept after editing the text | The form submits a value that no longer matches the box |
| `display:none` on the live region | Never announces anything |

### G. SPEC

**Markup** — the input itself is the combobox with the APG 1.2 attribute set · `aria-controls`
resolves even while closed

**Querying** — typing opens and renders results · several fast keystrokes produce one request ·
`minChars` suppresses the request entirely · **a stale response cannot overwrite a newer one** ·
the in-flight request is aborted when the query changes · the result count is announced · so is
an empty result set

**Keyboard** — arrows move the virtual cursor while focus stays in the input · wrapping · Enter
selects and closes · Escape closes then clears · Tab leaves without selecting

**Selection** — pointer selection works despite blur · editing after selecting clears it ·
controlled mode

## 07 — Dropdown Menu

> Runnable: `uie-practice/src/exercises/menu-reference/` · Spec: 19 tests

### A. ASKED AS

- "Build a dropdown menu" / "a File menu" / "an actions menu on each row"
- "Build a select" — **stop and clarify.** A select is a listbox; this is not that.

### B. API

```tsx
export interface MenuItem {
  value: string
  label: ReactNode
  disabled?: boolean
}

export interface MenuProps {
  label: ReactNode
  items: MenuItem[]
  onSelect: (value: string) => void
  open?: boolean
  defaultOpen?: boolean
  onOpenChange?: (open: boolean) => void
}
```

**Notice what is missing: there is no `value` prop.** That absence is the entire distinction:

| | Listbox / select | Menu |
|---|---|---|
| The user is | choosing a value that persists | invoking a command that's then over |
| State | `aria-selected` on the chosen option | none — only open/closed |
| Callback | `onValueChange` | `onSelect` |
| Reopening shows | the current selection | nothing marked |

Getting this backwards — a menu with `aria-selected`, or a select with `role="menu"` — is the
single most common mistake on this component, and it's visible in five seconds of markup.

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Trigger | `aria-haspopup="menu"`, `aria-expanded`, `aria-controls` when open |
| Menu | `role="menu"`, `aria-labelledby` → trigger |
| Item | `role="menuitem"`, roving `tabIndex`, `aria-disabled` when unavailable |

| Key | On the trigger | In the menu |
|---|---|---|
| `Enter` / `Space` | Open, focus **first** item | Invoke focused item |
| `↓` | Open, focus first item | Next enabled item, wrapping |
| `↑` | Open, focus **last** item | Previous enabled item, wrapping |
| `Home` / `End` | — | First / last enabled item |
| `Esc` | — | Close, **return focus to trigger** |
| `Tab` | — | Close, let focus move on |
| a–z | — | Jump to item starting with the typed string |

**`↑` opens on the last item** because a menu that renders above its trigger puts the last item
nearest the pointer. It's a small thing that makes the widget feel native.

### D. DECISIONS THAT MATTER

1. **Real focus moves into the menu**, unlike Combobox (§06) where it stays in the input. There's
   no text entry to protect here. → *"Focus moves to the menuitem itself — there's no input to
   keep it in, so a virtual cursor would be needless indirection."*
2. **`aria-disabled`, never the `disabled` attribute.** A `disabled` element can't be focused, so
   a keyboard user never learns the option exists. `aria-disabled` keeps it reachable and
   announced while blocking activation.
3. **Escape returns focus; outside-click does not.** Escape means "I'm done here, put me back."
   Clicking elsewhere already says where the user is going — yanking focus back fights them.
4. **Typeahead accumulates within ~500ms.** Typing `s` then `a` searches `"sa"`, not `"a"`.

### E. IMPLEMENTATION

**1 — Derive the navigable set once.**

```tsx
const enabled = items.map((item, i) => (item.disabled ? -1 : i)).filter((i) => i !== -1)

function step(delta: number) {
  const position = enabled.indexOf(activeIndex)
  const next = (position + delta + enabled.length) % enabled.length
  setActiveIndex(enabled[next])
}
```

Navigating an index list of *enabled* items means skipping disabled entries falls out for free —
every movement, including wrap, Home and End, operates on `enabled` and can never land on a
disabled item. The alternative (a `while` loop that skips forward until it finds an enabled one)
has to handle the all-disabled case explicitly or it spins forever.

**2 — Focus follows state, in an effect.**

```tsx
useEffect(() => {
  if (!open || activeIndex < 0) return
  itemRefs.current[activeIndex]?.focus()
}, [open, activeIndex])
```

An effect rather than calling `.focus()` inside the key handler, because on open the item doesn't
exist yet — the menu renders in the same commit that sets `open`. Focusing from the handler would
target a node that isn't mounted.

**3 — Typeahead, with the timer in a ref.**

```tsx
function typeahead(char: string) {
  const state = typeaheadRef.current
  window.clearTimeout(state.timer)
  state.query += char.toLowerCase()
  state.timer = window.setTimeout(() => { state.query = '' }, 500)

  const match = enabled.find((i) => {
    const text = typeof items[i].label === 'string' ? (items[i].label as string) : items[i].value
    return text.toLowerCase().startsWith(state.query)
  })
  if (match !== undefined) setActiveIndex(match)
}
```

- A **ref, not state**: typing must not trigger a render per keystroke, and the buffer is never
  displayed.
- **No match leaves `activeIndex` alone.** Typing a wrong letter shouldn't fling focus to the top.
- `label` can be any `ReactNode`, so fall back to `value` when it isn't a string.

**4 — Outside click on `pointerdown`, not `click`.**

```tsx
useEffect(() => {
  if (!open) return
  function onPointerDown(event: PointerEvent) {
    const target = event.target as Node
    if (menuRef.current?.contains(target) || triggerRef.current?.contains(target)) return
    closeMenu(false)
  }
  document.addEventListener('pointerdown', onPointerDown)
  return () => document.removeEventListener('pointerdown', onPointerDown)
})
```

`click` fires only after `mouseup`, so a press that starts inside the menu and releases outside
would close it. Checking `contains` on both the menu *and* the trigger matters: without the
trigger check, clicking it while open would close via this listener and immediately reopen via
`onClick`.

**5 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Menu</summary>

```tsx
import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'

/**
 * A menu is not a listbox and not a combobox. The distinction decides the whole
 * implementation:
 *
 *   listbox  you are CHOOSING a value that persists    → aria-selected
 *   menu     you are INVOKING a command, then it's gone → no selection state
 *
 * So there is no `value` prop here. The only state is open/closed plus which item
 * has focus — and unlike Combobox, that is REAL DOM focus moved into the menu,
 * not a virtual cursor, because there is no text input to keep focus in.
 */

export interface MenuItem {
  value: string
  label: ReactNode
  disabled?: boolean
}

export interface MenuProps {
  /** Trigger text. Also the menu's accessible name. */
  label: ReactNode
  items: MenuItem[]
  onSelect: (value: string) => void
  /** Controlled open state. Pair with onOpenChange. */
  open?: boolean
  defaultOpen?: boolean
  onOpenChange?: (open: boolean) => void
}

export function Menu({
  label,
  items,
  onSelect,
  open: openProp,
  defaultOpen = false,
  onOpenChange,
}: MenuProps) {
  const baseId = useId()
  const triggerId = `${baseId}-trigger`
  const menuId = `${baseId}-menu`

  const [internalOpen, setInternalOpen] = useState(defaultOpen)
  const isControlled = openProp !== undefined
  const open = isControlled ? openProp : internalOpen

  const [activeIndex, setActiveIndex] = useState(-1)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([])
  // Buffer for type-to-jump. A ref because typing must not trigger renders.
  const typeaheadRef = useRef({ query: '', timer: 0 })

  // A disabled item is skipped by every movement, so navigation only ever visits
  // indices in this list.
  const enabled = items.map((item, i) => (item.disabled ? -1 : i)).filter((i) => i !== -1)

  function setOpen(next: boolean) {
    if (!isControlled) setInternalOpen(next)
    onOpenChange?.(next)
  }

  function openMenu(focus: 'first' | 'last') {
    setOpen(true)
    setActiveIndex(focus === 'first' ? enabled[0] : enabled[enabled.length - 1])
  }

  function closeMenu(returnFocus: boolean) {
    setOpen(false)
    setActiveIndex(-1)
    // Escape and selection return focus to the trigger; Tab and outside-click do
    // not, because the user has already chosen where to go next.
    if (returnFocus) triggerRef.current?.focus()
  }

  function choose(item: MenuItem) {
    if (item.disabled) return
    onSelect(item.value)
    closeMenu(true)
  }

  // Real DOM focus follows activeIndex. This is the difference from Combobox:
  // there is no input to protect, so moving focus is both allowed and expected.
  useEffect(() => {
    if (!open || activeIndex < 0) return
    itemRefs.current[activeIndex]?.focus()
  }, [open, activeIndex])

  // Outside click. pointerdown, not click: a click fires only after mouseup, so a
  // press-drag-release that starts inside and ends outside would close the menu.
  useEffect(() => {
    if (!open) return
    function onPointerDown(event: PointerEvent) {
      const target = event.target as Node
      if (menuRef.current?.contains(target) || triggerRef.current?.contains(target)) return
      closeMenu(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  })

  function step(delta: number) {
    const position = enabled.indexOf(activeIndex)
    const next = (position + delta + enabled.length) % enabled.length
    setActiveIndex(enabled[next])
  }

  function typeahead(char: string) {
    const state = typeaheadRef.current
    window.clearTimeout(state.timer)
    state.query += char.toLowerCase()
    // 500ms is the conventional window: "sa" jumps to Save, then the buffer
    // resets so a later "s" starts fresh rather than searching for "sas".
    state.timer = window.setTimeout(() => {
      state.query = ''
    }, 500)

    const match = enabled.find((i) => {
      const text = typeof items[i].label === 'string' ? (items[i].label as string) : items[i].value
      return text.toLowerCase().startsWith(state.query)
    })
    if (match !== undefined) setActiveIndex(match)
  }

  function onTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    switch (event.key) {
      case 'ArrowDown':
      case 'Enter':
      case ' ':
        event.preventDefault()
        openMenu('first')
        break
      case 'ArrowUp':
        // Opening upward lands on the last item — the one nearest the trigger
        // when the menu renders above it.
        event.preventDefault()
        openMenu('last')
        break
      default:
        break
    }
  }

  function onMenuKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        step(1)
        break
      case 'ArrowUp':
        event.preventDefault()
        step(-1)
        break
      case 'Home':
        event.preventDefault()
        setActiveIndex(enabled[0])
        break
      case 'End':
        event.preventDefault()
        setActiveIndex(enabled[enabled.length - 1])
        break
      case 'Escape':
        event.preventDefault()
        closeMenu(true)
        break
      case 'Tab':
        // Let Tab do its normal thing, but don't leave a menu hanging open over
        // content the user has moved past.
        closeMenu(false)
        break
      default:
        if (event.key.length === 1 && !event.metaKey && !event.ctrlKey && !event.altKey) {
          event.preventDefault()
          typeahead(event.key)
        }
    }
  }

  return (
    <div className="menu">
      <button
        ref={triggerRef}
        id={triggerId}
        type="button"
        className="menu-trigger"
        // haspopup="menu" is more specific than "true" and tells AT what's coming.
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => (open ? closeMenu(false) : openMenu('first'))}
        onKeyDown={onTriggerKeyDown}
      >
        {label}
        <span className="menu-caret" aria-hidden="true" />
      </button>

      {open && (
        <div
          ref={menuRef}
          id={menuId}
          role="menu"
          aria-labelledby={triggerId}
          className="menu-list"
          onKeyDown={onMenuKeyDown}
        >
          {items.map((item, i) => (
            <button
              key={item.value}
              ref={(el) => {
                itemRefs.current[i] = el
              }}
              type="button"
              role="menuitem"
              className="menu-item"
              // Roving tabindex: the menu is one tab stop, and -1 keeps the rest
              // programmatically focusable so the arrow handler can reach them.
              tabIndex={i === activeIndex ? 0 : -1}
              // aria-disabled, not `disabled`: a disabled element is unfocusable,
              // so a keyboard user would never learn the option exists.
              aria-disabled={item.disabled || undefined}
              onClick={() => choose(item)}
              onMouseEnter={() => !item.disabled && setActiveIndex(i)}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| `aria-selected` on menuitems | Screen reader announces a persistent choice that doesn't exist |
| `disabled` attribute on items | Keyboard users never discover the option is there |
| Outside-click on `click` not `pointerdown` | Press inside, release outside → menu closes unexpectedly |
| Outside-click handler ignores the trigger | Clicking the open trigger closes then instantly reopens |
| `.focus()` called in the key handler on open | Focuses a node that isn't mounted yet; nothing happens |
| Escape doesn't restore focus | Focus falls to `<body>`; the user restarts from the top of the page |
| Typeahead buffer never clears | After a few keys nothing ever matches again |

### G. SPEC

**Markup** — trigger advertises `aria-haspopup`/`aria-expanded` · open menu is named by its
trigger · no `aria-selected` anywhere

**Opening** — Enter opens on first · ↑ opens on last · roving tabindex means one tab stop

**Navigation** — arrows skip disabled and wrap · Home/End · typing jumps · consecutive letters
accumulate rather than restart · buffer resets after 500ms · disabled item is focusable and
announced but inert

**Selecting/closing** — click invokes and closes · Enter invokes · selecting returns focus ·
Escape closes and returns focus without selecting · outside click closes **without** returning
focus · Tab closes

**Controlled** — reports open changes and does not open on its own

## 08 — Tooltip

> Runnable: `uie-practice/src/exercises/tooltip-reference/` · Spec: 12 tests

### A. ASKED AS

- "Add a tooltip to this icon button"
- "Show help text on hover"
- "Build a popover" — **different component.** See the interactive-content rule below.

### B. API

```tsx
export interface TooltipProps {
  content: ReactNode
  children: ReactElement<Record<string, unknown>>
  delay?: number        // open delay, default 300
  closeDelay?: number   // grace period on leave, default 120
}
```

The API is small because the component should be. The interesting decisions are all behavioral.

**The rule that decides whether to build one at all: a tooltip may not contain interactive
content.** There is no way to reach a link inside a tooltip by keyboard — focus is on the
trigger, and moving it dismisses the tooltip. If you need a button in there, you need a popover,
which is a different component (dismissible, focusable, `role="dialog"` if modal).

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Trigger | `aria-describedby` → tooltip id, **only while open** |
| Bubble | `role="tooltip"`, `id` |

**`aria-describedby`, never `aria-labelledby`.** A tooltip *supplements* a control's name; it
does not supply one. With `labelledby`, a button reading "Save" is announced as its tooltip text
and the real label is lost. And an icon button whose only name is its tooltip announces as
"button" until it happens to open — it needs its own `aria-label` as well.

| Trigger | Behavior |
|---|---|
| Focus | Open **immediately** — no delay |
| Blur | Close immediately |
| `Esc` | Close, focus stays put |
| Pointer enter | Open after `delay` |
| Pointer leave | Close after `closeDelay` |

### D. DECISIONS THAT MATTER — WCAG 1.4.13

This is the whole component. Three requirements, and most implementations fail at least one:

1. **DISMISSIBLE.** Escape closes it without moving the pointer. Applies whether it was opened by
   hover or focus — a mouse user with a bubble covering the text they're reading needs the same
   escape hatch.
2. **HOVERABLE.** The pointer can move *onto* the tooltip without it vanishing. This is why
   `closeDelay` exists: it keeps the bubble alive while the pointer travels. A user at 400% zoom
   physically cannot read a tooltip they can't put the magnifier over.
3. **PERSISTENT.** No auto-hide timer. It stays until dismissed, blurred, or the pointer leaves.

Plus one that isn't in the spec but should be: **open instantly on focus, with a delay on hover.**
The hover delay stops every button flashing a bubble as the pointer sweeps a toolbar. A keyboard
user has already committed to the control, so the same delay is pure latency.

### E. IMPLEMENTATION

**1 — Two timers, because open and close are independently debounced.**

```tsx
const timers = useRef({ open: 0, close: 0 })

function show(immediate = false) {
  window.clearTimeout(timers.current.close)
  window.clearTimeout(timers.current.open)
  if (immediate || delay === 0) setOpen(true)
  else timers.current.open = window.setTimeout(() => setOpen(true), delay)
}

function hide(immediate = false) {
  window.clearTimeout(timers.current.open)
  window.clearTimeout(timers.current.close)
  if (immediate) setOpen(false)
  else timers.current.close = window.setTimeout(() => setOpen(false), closeDelay)
}
```

Each must cancel the other, or a fast in-out-in leaves a queued close that fires after you've
reopened. `immediate` distinguishes *decisions* (blur, Escape — act now) from *maybes* (a pointer
leaving might just be travelling toward the bubble).

**2 — Clone one string; put every handler on the wrapper.**

```tsx
const trigger = cloneElement(children, {
  'aria-describedby': open ? tooltipId : undefined,
})

return (
  <span
    className="tooltip-root"
    onPointerEnter={() => show()}
    onPointerLeave={() => hide()}
    onFocus={() => show(true)}
    onBlur={() => hide(true)}
    onKeyDown={onTriggerKeyDown}
  >
    {trigger}
    {open && <span id={tooltipId} role="tooltip">{content}</span>}
  </span>
)
```

Three reasons this beats cloning handlers onto the child:

- **You cannot clobber the consumer's handlers if you never touch them.** No compose helper, no
  "did I remember to call theirs first?" bug.
- **React's `onFocus`/`onBlur` map to `focusin`/`focusout`, which bubble** — unlike native
  `focus`/`blur`. So a wrapper handler sees focus land on the child.
- Pointer handlers *must* be here anyway. On the trigger, moving toward the bubble fires
  pointer-leave first and the tooltip closes before the pointer arrives — the hoverable failure.

**3 — CSS carries part of the contract.** The bubble sits flush against the trigger
(`top: 100%`, no margin). A transparent gap would break hoverable: the pointer leaves the trigger
before reaching the bubble, and the grace period would be doing all the work. Visual separation
comes from the shadow, not from empty space.

**4 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Tooltip</summary>

```tsx
import { cloneElement, useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent, ReactElement, ReactNode } from 'react'

/**
 * The most-underestimated component on this list, because the hard part isn't
 * positioning — it's WCAG 1.4.13 (Content on Hover or Focus), which has three
 * requirements almost every implementation fails:
 *
 *   DISMISSIBLE  Escape closes it without moving the pointer.
 *   HOVERABLE    You can move the pointer ONTO the tooltip without it vanishing.
 *   PERSISTENT   It stays until dismissed, blurred, or the pointer leaves.
 *                No auto-hide timer.
 *
 * And the rule that decides whether you should build one at all:
 *
 *   A TOOLTIP MAY NOT CONTAIN INTERACTIVE CONTENT.
 *
 * There is no way to reach a link inside a tooltip by keyboard — focus is on the
 * trigger, and moving it dismisses the tooltip. If you need a button in there you
 * need a popover, which is a different component with different semantics.
 */

export interface TooltipProps {
  /** Description only. Never interactive content — see above. */
  content: ReactNode
  /** A single focusable element. Receives aria-describedby; its own props are untouched. */
  children: ReactElement<Record<string, unknown>>
  /** Open delay in ms. Suppresses flicker when sweeping across a toolbar. */
  delay?: number
  /**
   * Grace period before closing on pointer-leave. This is what makes the tooltip
   * hoverable: it gives the pointer time to travel from the trigger to the bubble
   * without the tooltip disappearing under it mid-journey.
   */
  closeDelay?: number
}

export function Tooltip({ content, children, delay = 300, closeDelay = 120 }: TooltipProps) {
  const tooltipId = useId()
  const [open, setOpen] = useState(false)
  // Two timers, because opening and closing are independently debounced and each
  // must be able to cancel the other.
  const timers = useRef({ open: 0, close: 0 })

  useEffect(() => {
    const current = timers.current
    return () => {
      window.clearTimeout(current.open)
      window.clearTimeout(current.close)
    }
  }, [])

  function show(immediate = false) {
    window.clearTimeout(timers.current.close)
    window.clearTimeout(timers.current.open)
    // Focus opens instantly; hover waits. A keyboard user has already committed to
    // this control, so making them wait is pure latency.
    if (immediate || delay === 0) setOpen(true)
    else timers.current.open = window.setTimeout(() => setOpen(true), delay)
  }

  function hide(immediate = false) {
    window.clearTimeout(timers.current.open)
    window.clearTimeout(timers.current.close)
    // Blur and Escape are decisions — act now. A pointer leaving might just be
    // travelling toward the bubble, so that path gets the grace period.
    if (immediate) setOpen(false)
    else timers.current.close = window.setTimeout(() => setOpen(false), closeDelay)
  }

  function onTriggerKeyDown(event: KeyboardEvent) {
    // DISMISSIBLE. Fires whether the tooltip was opened by hover or by focus — a
    // mouse user with a bubble covering the text they're reading needs the same
    // escape hatch as a keyboard user.
    if (event.key === 'Escape' && open) {
      event.stopPropagation()
      hide(true)
    }
  }

  // The ONLY thing cloned onto the child is one string. Every handler lives on the
  // wrapper below, which matters for three reasons:
  //
  //   1. You cannot clobber the consumer's handlers if you never touch them. No
  //      compose helper, no "did I remember to call theirs first?" bug.
  //   2. React's onFocus/onBlur map to focusin/focusout, which BUBBLE — unlike the
  //      native focus/blur events. So a wrapper handler sees focus on the child.
  //   3. Passing ref-reading closures into cloneElement trips the compiler lint
  //      ("Cannot access refs during render"), because it can't prove cloneElement
  //      merely stores them.
  //
  // describedby, NOT labelledby. A tooltip supplements the control's name; it does
  // not replace it. With labelledby, a button reading "Save" would be announced as
  // its own tooltip text and the real label would be lost.
  const trigger = cloneElement(children, {
    'aria-describedby': open ? tooltipId : undefined,
  })

  return (
    // Pointer handlers live here rather than on the trigger. On the trigger,
    // moving toward the bubble fires pointer-leave first and the tooltip closes
    // before the pointer arrives. The wrapper contains both, and the closeDelay
    // covers the gap either way.
    <span
      className="tooltip-root"
      onPointerEnter={() => show()}
      onPointerLeave={() => hide()}
      onFocus={() => show(true)}
      onBlur={() => hide(true)}
      onKeyDown={onTriggerKeyDown}
    >
      {trigger}
      {open && (
        <span
          id={tooltipId}
          role="tooltip"
          className="tooltip-bubble"
          onPointerEnter={() => show(true)}
          onPointerLeave={() => hide()}
        >
          {content}
        </span>
      )}
    </span>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| Pointer handlers on the trigger | Tooltip closes as you move toward it — hoverable failure |
| `aria-labelledby` instead of `describedby` | The control's real name is replaced by its tooltip |
| Icon button named only by its tooltip | Announced as "button" whenever the tooltip is closed |
| Auto-hide after N seconds | Persistent failure; slow readers never finish |
| No Escape handler | Dismissible failure; a bubble can cover content with no way to clear it |
| Interactive content inside | Unreachable by keyboard — you needed a popover |
| Delay applied to focus too | Keyboard users wait for no reason |
| `aria-describedby` left on while closed | Points at a removed node |

### G. SPEC

**Naming** — describes the trigger without relabelling it · no dangling `aria-describedby` when
closed

**Keyboard parity** — focus opens instantly · blur closes · Escape dismisses while focus stays put

**Pointer** — hover opens only after the delay · leaving before the delay opens nothing at all ·
the bubble itself is hoverable · leaving without reaching it closes after the grace period ·
persistent with no auto-hide

**Composition** — the child keeps its own handlers · an icon button still has its own name

## 09 — Toast

> Runnable: `uie-practice/src/exercises/toast-reference/` · Spec: 10 tests

### A. ASKED AS

- "Build a toast / notification / snackbar system"
- "Show a confirmation after saving"
- "Design the API for a notification system" — a design question as often as a coding one

### B. API

This is the one component here whose API is a **hook plus a provider**, not props. That's the
interesting part, and it's what makes it a design question:

```tsx
export function ToastProvider({ children, max = 3, defaultDuration = 4000 }: ToastProviderProps)

export function useToast(): {
  toast: (message: ReactNode, options?: ToastOptions) => string
  dismiss: (id: string) => void
}

export interface ToastOptions {
  politeness?: 'polite' | 'assertive'
  duration?: number          // Infinity = manual dismissal only
}
```

**Why a context and not props:** a toast is fired from anywhere — a mutation handler, a route
guard, an error boundary — and it renders in one fixed place. Threading a callback down to every
call site is exactly the prop-drilling that context exists for.

**Why `toast()` returns the id:** so the caller can dismiss it themselves. "Uploading…" that a
completion handler replaces needs a handle.

**Why `max`:** an unbounded stack covers the page. Oldest gets dropped.

### C. ARIA CONTRACT

| Element | Required |
|---|---|
| Polite region | `aria-live="polite"`, **permanently mounted** |
| Assertive region | `aria-live="assertive"`, **permanently mounted** |
| Dismiss button | a name that identifies *which* toast |

**The rule that this whole component exists to teach:**

> **The live region must already be in the DOM before the message goes into it.**

Screen readers observe an *existing* `aria-live` container for mutations. Mount the container and
its text in the same commit and there is no mutation to observe — the toast is visible and
completely silent. So both regions are mounted for the life of the app and sit empty.

**Two regions, not one**, because a container has a single `aria-live` value. Putting an error in
the polite region means it waits behind whatever is currently being read.

| | `polite` | `assertive` |
|---|---|---|
| Timing | Waits for a pause in speech | Interrupts mid-word |
| Use for | Saved · Copied · 3 results | Errors that block · Session expiring |
| Cost of misuse | Missed | Users learn to tune you out |

### D. DECISIONS THAT MATTER

1. **Pause on hover AND focus.** The commonly-missed half is focus: a keyboard user tabbing to the
   dismiss button gets the toast yanked away mid-reach. React's `onFocus`/`onBlur` follow
   `focusin`/`focusout`, so a handler on the toast catches focus landing on the button inside.
2. **Resume, don't restart.** Bank the elapsed time. Restarting the full duration on every
   mouse-out means a toast the user keeps brushing past never leaves.
3. **`duration: Infinity` for anything requiring action.** An error the user must respond to
   should not evaporate.
4. **Never move focus to announce.** Focus movement is for navigation; live regions are for
   information. Stealing focus for "Saved" is hostile.

### E. IMPLEMENTATION

**1 — The provider owns the list; the context is memoized.**

```tsx
const dismiss = useCallback((id: string) => {
  setToasts((list) => list.filter((t) => t.id !== id))
}, [])

const toast = useCallback((message: ReactNode, options: ToastOptions = {}) => {
  const id = `toast-${idRef.current++}`
  setToasts((list) => [...list, { id, message,
    politeness: options.politeness ?? 'polite',
    duration: options.duration ?? defaultDuration }].slice(-max))
  return id
}, [defaultDuration, max])

const value = useMemo(() => ({ toast, dismiss }), [toast, dismiss])
```

The `useMemo` is not decoration. A fresh object literal every render re-renders **every consumer
of the context** on every toast — and consumers are, by design, scattered across the whole app.
`toast` and `dismiss` must themselves be `useCallback`ed or the memo is worthless (§17 D).

`.slice(-max)` caps the stack by keeping the newest. Functional updater throughout, so a burst of
five in one tick doesn't clobber itself.

**2 — Both regions, always mounted.**

```tsx
<div aria-live="polite" className="toast-stack">
  {polite.map((t) => <ToastItem key={t.id} toast={t} onDismiss={dismiss} />)}
</div>
<div aria-live="assertive" className="toast-stack">
  {assertive.map((t) => <ToastItem key={t.id} toast={t} onDismiss={dismiss} />)}
</div>
```

Rendered even when both arrays are empty. That's the whole point — see §C.

**3 — The pausable timer.**

```tsx
const [paused, setPaused] = useState(false)
const remainingRef = useRef(toast.duration)
const startedRef = useRef(0)

useEffect(() => {
  if (paused || toast.duration === Infinity) return

  startedRef.current = Date.now()
  const timer = setTimeout(() => onDismiss(toast.id), remainingRef.current)

  return () => {
    clearTimeout(timer)
    remainingRef.current -= Date.now() - startedRef.current
  }
}, [paused, toast.id, toast.duration, onDismiss])
```

The mechanism is worth reading twice: **the cleanup does the banking.** Toggling `paused` re-runs
the effect, and on the way out the cleanup subtracts however long the timer actually ran from
`remainingRef`. Resuming starts a fresh timeout for what's left. Refs, not state, because
adjusting the remaining time must not trigger a render.

`onDismiss` is in the dependency array, which is why it had to be `useCallback`ed in the provider
— otherwise every provider render restarts every toast's timer.

**4 — Name the dismiss button after its toast.**

```tsx
aria-label={`Dismiss: ${typeof toast.message === 'string' ? toast.message : 'notification'}`}
```

With three stacked toasts, three buttons all named "Close" are useless. `message` is a
`ReactNode`, so fall back when it isn't a string.

**5 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Toast</summary>

```tsx
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'

/**
 * The bug almost every toast implementation ships:
 *
 *   THE LIVE REGION MUST ALREADY BE IN THE DOM BEFORE THE MESSAGE GOES INTO IT.
 *
 * Screen readers watch an existing aria-live container for mutations. Mount the
 * container and its text in the same commit and there is no mutation to observe —
 * the toast is visible, and completely silent. So both regions below are mounted
 * for the life of the app and stay empty until there's something to say.
 *
 * The second thing people miss: pausing on hover but not on focus. A keyboard
 * user who tabs to the dismiss button gets the toast yanked away mid-reach.
 */

export type Politeness = 'polite' | 'assertive'

export interface Toast {
  id: string
  message: ReactNode
  politeness: Politeness
  /** ms, or Infinity to require manual dismissal. */
  duration: number
}

export interface ToastOptions {
  politeness?: Politeness
  duration?: number
}

interface ToastContextValue {
  toast: (message: ReactNode, options?: ToastOptions) => string
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  // Throwing beats returning undefined: the failure surfaces at the call site
  // during development instead of as "toast is not a function" at 2am.
  if (!ctx) throw new Error('useToast must be used inside a <ToastProvider>')
  return ctx
}

export interface ToastProviderProps {
  children: ReactNode
  /** Oldest toasts are dropped past this. Unbounded stacks cover the whole page. */
  max?: number
  defaultDuration?: number
}

export function ToastProvider({ children, max = 3, defaultDuration = 4000 }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const idRef = useRef(0)

  const dismiss = useCallback((id: string) => {
    setToasts((list) => list.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (message: ReactNode, options: ToastOptions = {}) => {
      const id = `toast-${idRef.current++}`
      const next: Toast = {
        id,
        message,
        politeness: options.politeness ?? 'polite',
        duration: options.duration ?? defaultDuration,
      }
      setToasts((list) => [...list, next].slice(-max))
      return id
    },
    [defaultDuration, max],
  )

  // Memoized so every consumer of the context doesn't re-render on each toast.
  // `toast` and `dismiss` are already stable, so this object is too.
  const value = useMemo(() => ({ toast, dismiss }), [toast, dismiss])

  const polite = toasts.filter((t) => t.politeness === 'polite')
  const assertive = toasts.filter((t) => t.politeness === 'assertive')

  return (
    <ToastContext.Provider value={value}>
      {children}

      <div className="toast-region">
        {/* Two containers, both permanently mounted. Splitting by politeness is
            not cosmetic: a single region can only have one aria-live value, and
            downgrading an error to polite means it waits behind whatever the
            screen reader is currently reading. */}
        <div aria-live="polite" className="toast-stack">
          {polite.map((t) => (
            <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
          ))}
        </div>
        <div aria-live="assertive" className="toast-stack">
          {assertive.map((t) => (
            <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
          ))}
        </div>
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const [paused, setPaused] = useState(false)
  // Time left, carried across pauses. A ref because changing it must not render.
  const remainingRef = useRef(toast.duration)
  const startedRef = useRef(0)

  useEffect(() => {
    if (paused || toast.duration === Infinity) return

    startedRef.current = Date.now()
    const timer = setTimeout(() => onDismiss(toast.id), remainingRef.current)

    return () => {
      clearTimeout(timer)
      // Bank the elapsed time so resuming continues rather than restarting.
      // Restarting the full duration on every mouse-out is the other common bug:
      // a toast the user keeps brushing past never leaves.
      remainingRef.current -= Date.now() - startedRef.current
    }
  }, [paused, toast.id, toast.duration, onDismiss])

  return (
    <div
      className="toast"
      data-politeness={toast.politeness}
      // Hover and focus both pause. onFocus/onBlur in React follow focusin/focusout,
      // so focus landing on the dismiss button inside counts too.
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <span className="toast-message">{toast.message}</span>
      <button
        type="button"
        className="toast-dismiss"
        // The visible × is decorative; the button needs a real name, and it has to
        // say WHICH toast it closes once several are stacked.
        aria-label={`Dismiss: ${typeof toast.message === 'string' ? toast.message : 'notification'}`}
        onClick={() => onDismiss(toast.id)}
      >
        <span aria-hidden="true">×</span>
      </button>
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| Live region mounted with its first toast | Visible but **completely silent** — the classic |
| One region for both politeness levels | Errors queue behind chatter, or confirmations interrupt |
| `display: none` used for visually-hidden | Removed from the a11y tree; never announces |
| Pause on hover but not focus | Toast vanishes as a keyboard user reaches for dismiss |
| Restarting the duration on resume | A toast brushed past repeatedly never leaves |
| Unmemoized context value | Every consumer in the app re-renders per toast |
| `onDismiss` not `useCallback`ed | Every provider render restarts every toast's timer |
| Uncapped stack | Notifications cover the page |
| Dismiss buttons all named "Close" | Unusable once more than one is stacked |
| Moving focus to the toast | Steals the user's place in the page |

### G. SPEC

**Live regions** — both regions exist and are empty before any toast · polite messages land in
the polite region · assertive in the assertive one

**Dismissal** — the dismiss button names the toast it closes · the stack is capped, dropping the
oldest

**Timing** — dismisses itself after the duration · `Infinity` waits for the user · hovering
pauses and resuming continues from where it stopped · keyboard focus pauses it too

**Context** — `useToast` outside a provider fails loudly

## 10 — Tree / File explorer

> Runnable: `uie-practice/src/exercises/tree-reference/` · Spec: 17 tests

### A. ASKED AS

- "Build a file explorer" / "a folder tree" / "a nested comment thread"
- "Build a nested checkbox list" — same navigation, plus tri-state checkboxes

### B. API

```tsx
export interface TreeNode {
  value: string
  label: string
  children?: TreeNode[]   // presence makes it a folder, even when empty
}

export interface TreeProps {
  nodes: TreeNode[]
  label: string
  value?: string | null
  defaultValue?: string | null
  onValueChange?: (value: string) => void
  defaultExpanded?: string[]
}
```

**`children: []` still means folder.** An empty directory is a directory — it expands, it shows
nothing, and `aria-expanded` applies. Deciding folder-ness by `children?.length` instead of
`Array.isArray(children)` is a real bug: empty folders silently become leaves.

**Selection is controlled/uncontrolled; expansion is not.** Expansion is view state the component
can own. Selection is what the parent cares about — it drives the editor pane next to the tree.
Making both controllable doubles the API for no benefit, and saying *why* you split them is worth
more than doing it.

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Container | `role="tree"`, `aria-label` |
| Row | `role="treeitem"`, `aria-level`, `aria-posinset`, `aria-setsize`, `aria-selected`, roving `tabIndex` |
| Folder row | plus `aria-expanded`. **Leaves must not have it.** |
| Children wrapper | `role="group"` |

`aria-level`/`posinset`/`setsize` exist because rows are *visually* indented but structurally
just divs. Without them a screen reader can't say "level 3, item 2 of 5".

| Key | Behavior |
|---|---|
| `↓` / `↑` | Next / previous **visible** row. Does not wrap. |
| `→` | Closed folder → open it. Open folder → move to first child. Leaf → nothing. |
| `←` | Open folder → close it. Otherwise → move to parent. |
| `Home` / `End` | First / last visible row |
| `Enter` / `Space` | Folder → toggle. Leaf → select. |

**No wrapping.** A tree is a hierarchy, not a carousel; running off the top should stop.

### D. DECISIONS THAT MATTER

1. **Render recursively, navigate linearly.** Flatten the visible rows into an array and every
   movement becomes `index ± 1`. Navigating the nested structure directly turns `↓` into a
   recursive descent with three special cases.
2. **← and → each do two jobs.** That's what makes it feel like an editor: → drills in, ← climbs
   out, and neither needs a separate key. `←` from a deep leaf reaches the parent without arrowing
   up past every sibling.
3. **Roving tabindex with a fallback.** Exactly one row is tabbable; if nothing is selected it's
   the first row, so the tree is always reachable.
4. **Enter on a folder toggles rather than selects.** Selecting a directory is rarely what the
   user meant.

### E. IMPLEMENTATION

**1 — The flatten. This is the component.**

```tsx
interface FlatRow {
  node: TreeNode
  level: number
  position: number      // 1-based, for aria-posinset
  setSize: number
  parentValue: string | null
  isFolder: boolean
}

function flatten(nodes, expanded, level = 1, parentValue = null, out: FlatRow[] = []) {
  nodes.forEach((node, i) => {
    const isFolder = Array.isArray(node.children)
    out.push({ node, level, position: i + 1, setSize: nodes.length, parentValue, isFolder })
    if (isFolder && expanded.includes(node.value)) {
      flatten(node.children!, expanded, level + 1, node.value, out)
    }
  })
  return out
}
```

- Recurses **only into expanded folders**, so the output is exactly what's on screen. `↓` is
  `rows[index + 1]` with no filtering.
- Carries `parentValue`, which is what makes `←`-to-parent a lookup instead of a search.
- Carries `level`/`position`/`setSize` so the ARIA attributes are already computed at render.
- Called on every render. It's O(visible rows) — for a file tree that's nothing. Memoize only if
  profiling says to.

**2 — The two-meaning arrows.**

```tsx
case 'ArrowRight':
  event.preventDefault()
  if (row.isFolder && !isExpanded) setExpandedFor(row.node.value, true)
  else if (row.isFolder && isExpanded) focusRow(rows[index + 1]?.node.value)
  break

case 'ArrowLeft':
  event.preventDefault()
  if (row.isFolder && isExpanded) setExpandedFor(row.node.value, false)
  else if (row.parentValue) focusRow(row.parentValue)
  break
```

Read them as mirror images: → is *open, then descend*; ← is *close, then ascend*. On a leaf, →
does nothing at all — no wrap, no jump to a sibling. `row.parentValue` being `null` at the root
is what stops ← escaping the tree.

**3 — Roving tabindex with a fallback.**

```tsx
const rows = flatten(nodes, expanded)
const activeValue = rows.some((r) => r.node.value === value) ? value : rows[0]?.node.value
```

The `some` check matters: the selected node can be inside a folder the user just collapsed. Then
it isn't in `rows`, nothing would be tabbable, and the tree would drop out of the tab order
entirely. Falling back to the first row keeps it reachable.

**4 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Tree</summary>

```tsx
import { useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

/**
 * The insight that makes a tree tractable:
 *
 *   RENDER RECURSIVELY, NAVIGATE LINEARLY.
 *
 * The DOM is nested, but the keyboard walks a flat list of *visible* rows. Try to
 * navigate the tree structure directly and ArrowDown becomes a recursive descent
 * with three special cases. Flatten first and it's `index + 1`.
 *
 * The other thing to notice: ← and → each do two different jobs depending on
 * where you are, which is what makes a tree feel like an editor rather than a list.
 */

export interface TreeNode {
  value: string
  label: string
  /** Presence of this array is what makes a node a folder, even when empty. */
  children?: TreeNode[]
}

interface FlatRow {
  node: TreeNode
  level: number
  /** 1-based position among siblings, for aria-posinset. */
  position: number
  setSize: number
  parentValue: string | null
  isFolder: boolean
}

/** Depth-first walk of everything currently visible. Collapsed subtrees are skipped. */
function flatten(
  nodes: TreeNode[],
  expanded: string[],
  level = 1,
  parentValue: string | null = null,
  out: FlatRow[] = [],
): FlatRow[] {
  nodes.forEach((node, i) => {
    const isFolder = Array.isArray(node.children)
    out.push({ node, level, position: i + 1, setSize: nodes.length, parentValue, isFolder })
    if (isFolder && expanded.includes(node.value)) {
      flatten(node.children!, expanded, level + 1, node.value, out)
    }
  })
  return out
}

export interface TreeProps {
  nodes: TreeNode[]
  label: string
  /** Controlled selection. Pair with onValueChange. */
  value?: string | null
  defaultValue?: string | null
  onValueChange?: (value: string) => void
  defaultExpanded?: string[]
}

export function Tree({
  nodes,
  label,
  value: valueProp,
  defaultValue = null,
  onValueChange,
  defaultExpanded = [],
}: TreeProps) {
  const baseId = useId()
  const rowId = (v: string) => `${baseId}-row-${v}`

  const [internalValue, setInternalValue] = useState<string | null>(defaultValue)
  const isControlled = valueProp !== undefined
  const value = isControlled ? valueProp : internalValue

  const [expanded, setExpanded] = useState<string[]>(defaultExpanded)
  const rowRefs = useRef(new Map<string, HTMLDivElement | null>())

  const rows = flatten(nodes, expanded)
  // Roving tabindex needs exactly one tabbable row. Falling back to the first row
  // means the tree is always reachable, even before anything is selected.
  const activeValue = rows.some((r) => r.node.value === value) ? value : rows[0]?.node.value

  function commit(next: string) {
    if (!isControlled) setInternalValue(next)
    onValueChange?.(next)
  }

  function focusRow(next: string | undefined) {
    if (!next) return
    commit(next)
    rowRefs.current.get(next)?.focus()
  }

  function setExpandedFor(nodeValue: string, open: boolean) {
    setExpanded((prev) =>
      open ? [...new Set([...prev, nodeValue])] : prev.filter((v) => v !== nodeValue),
    )
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = rows.findIndex((r) => r.node.value === activeValue)
    if (index === -1) return
    const row = rows[index]
    const isExpanded = expanded.includes(row.node.value)

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        focusRow(rows[index + 1]?.node.value)
        break

      case 'ArrowUp':
        event.preventDefault()
        focusRow(rows[index - 1]?.node.value)
        break

      case 'ArrowRight':
        event.preventDefault()
        // Two jobs: open a closed folder, or step INTO an already-open one.
        // On a leaf it does nothing at all — no wrapping, no jumping to a sibling.
        if (row.isFolder && !isExpanded) setExpandedFor(row.node.value, true)
        else if (row.isFolder && isExpanded) focusRow(rows[index + 1]?.node.value)
        break

      case 'ArrowLeft':
        event.preventDefault()
        // Mirror image: close an open folder, or step OUT to the parent. This is
        // what lets you climb out of a deep path without arrowing up past every
        // sibling on the way.
        if (row.isFolder && isExpanded) setExpandedFor(row.node.value, false)
        else if (row.parentValue) focusRow(row.parentValue)
        break

      case 'Home':
        event.preventDefault()
        focusRow(rows[0]?.node.value)
        break

      case 'End':
        event.preventDefault()
        focusRow(rows[rows.length - 1]?.node.value)
        break

      case 'Enter':
      case ' ':
        event.preventDefault()
        if (row.isFolder) setExpandedFor(row.node.value, !isExpanded)
        else commit(row.node.value)
        break

      default:
        break
    }
  }

  function renderNodes(list: TreeNode[], level: number) {
    return list.map((node, i) => {
      const isFolder = Array.isArray(node.children)
      const isExpanded = expanded.includes(node.value)
      const isActive = node.value === activeValue

      return (
        <div key={node.value} role="none">
          <div
            ref={(el) => {
              rowRefs.current.set(node.value, el)
            }}
            id={rowId(node.value)}
            role="treeitem"
            // aria-expanded only on folders. On a leaf it would announce a
            // collapse affordance that doesn't exist.
            aria-expanded={isFolder ? isExpanded : undefined}
            aria-selected={isActive}
            // The DOM is nested but the a11y tree needs the position spelled out,
            // because rows are visually indented rather than structurally obvious.
            aria-level={level}
            aria-posinset={i + 1}
            aria-setsize={list.length}
            tabIndex={isActive ? 0 : -1}
            className="tree-row"
            style={{ paddingLeft: 8 + (level - 1) * 16 }}
            onClick={() => {
              commit(node.value)
              if (isFolder) setExpandedFor(node.value, !isExpanded)
            }}
          >
            <span className="tree-twisty" aria-hidden="true">
              {isFolder ? (isExpanded ? '▾' : '▸') : ''}
            </span>
            <span className="tree-label">{node.label}</span>
          </div>

          {/* role="group" is what tells AT these rows are children of the row
              above rather than siblings of it. */}
          {isFolder && isExpanded && (
            <div role="group">{renderNodes(node.children!, level + 1)}</div>
          )}
        </div>
      )
    })
  }

  return (
    <div role="tree" aria-label={label} className="tree" onKeyDown={handleKeyDown}>
      {renderNodes(nodes, 1)}
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| Navigating the nested structure instead of a flat list | `↓` needs recursive descent; off-by-one bugs at every boundary |
| `children?.length` decides folder-ness | Empty directories become leaves and can't expand |
| `aria-expanded` on leaves | Announces a collapse affordance that doesn't exist |
| No `aria-level`/`posinset`/`setsize` | Indentation is purely visual; AT can't convey depth |
| Missing `role="group"` | Children announce as siblings of their parent |
| Arrows wrap at the ends | A hierarchy that loops is disorienting |
| No fallback for `activeValue` | Collapse the folder holding the selection → tree leaves the tab order |
| `←` doesn't climb | Escaping a deep path means arrowing up through every sibling |

### G. SPEC

**Structure** — collapsed subtrees aren't rendered · folders advertise expandability and leaves
don't · level/posinset/setsize are present · children live in a `group`

**Roving tabindex** — the whole tree is one tab stop · reachable before anything is selected

**Vertical** — ↓/↑ walk visible rows, skipping collapsed subtrees · no wrapping · Home/End

**Two-meaning arrows** — → opens then steps in · ← closes then climbs out · ← from a deep leaf
reaches the parent directly · → on a leaf does nothing · an empty folder is still a folder

**Selection** — Enter toggles a folder rather than selecting it · clicking a leaf reports it ·
controlled mode

## 11 — Data table

> Runnable: `uie-practice/src/exercises/data-table-reference/` · Spec: 15 tests

### A. ASKED AS

- "Build a sortable table" / "a users table with search and pagination"
- "Add row selection with a select-all"
- "Render 100,000 rows" — that's §13, not this

### B. API

```tsx
export interface Column<T> {
  key: string
  header: string
  sortable?: boolean
  sortValue?: (row: T) => string | number   // defaults to the raw cell value
  render?: (row: T) => ReactNode
}

export interface DataTableProps<T> {
  rows: T[]
  columns: Column<T>[]
  caption: string
  getRowId: (row: T) => string
  getCell: (row: T, key: string) => string | number
  pageSize?: number
  selectable?: boolean
}
```

**`getRowId` is not optional and not `id`.** Selection, keys and ARIA wiring all hang off it, and
hardcoding `row.id` makes the component useless for data shaped any other way.

**`sortValue` separate from `render`** because what you *display* and what you *sort by* diverge
constantly — a formatted date, a currency string, a status badge.

### C. SEMANTICS

| Element | Required |
|---|---|
| `<table>` | `<caption>` — the accessible name, and visible |
| Column header | `<th scope="col">`, `aria-sort` **only on the sorted column** |
| Row header | `<th scope="row">` — the first cell of each row |
| Pager status | `role="status"` announcing page and total |

**Use a real `<table>`.** A grid of divs loses row/column navigation entirely; screen-reader users
navigate tables with dedicated keys that only work on table markup. This is the single biggest
accessibility decision here and it costs nothing.

**`aria-sort` goes on the `<th>`, not the button inside it**, and only on the column currently
sorted. Putting `aria-sort="none"` on every column is noise.

**The first cell is a `<th scope="row">`.** That's what lets AT announce "Ada Lovelace,
Compilers" instead of just "Compilers" when moving across a row.

### D. DECISIONS THAT MATTER

1. **Filter → sort → paginate, in that order, all derived.** Any other order gives wrong answers:
   sort-then-filter wastes work, paginate-then-filter filters one page.
2. **Clamp the page; don't store a corrected one.** Filter down to two rows while on page 5 and a
   stored index leaves you rendering an empty table with working pagination. Users report it as
   "the search is broken."
3. **A `Set` for selection — the opposite call from §04's array.** Here it's *internal* state, one
   membership check per rendered row, and it can reach thousands of entries. That's exactly where
   O(1) earns its place. → *"Array for a public prop because it serializes; Set for internal
   selection because it's a hot lookup."*
4. **Three-state sort: ascending → descending → none.** Sorting shouldn't be a one-way door.
5. **Select-all means "all on this page."** Selecting 40,000 invisible rows from one checkbox is a
   support ticket waiting to happen. Say which you chose.

### E. IMPLEMENTATION

**1 — The derived pipeline.**

```tsx
const filtered = useMemo(() => {
  const q = query.trim().toLowerCase()
  if (!q) return rows
  return rows.filter((row) =>
    columns.some((col) => String(getCell(row, col.key)).toLowerCase().includes(q)),
  )
}, [rows, columns, query, getCell])

const sorted = useMemo(() => {
  if (!sort) return filtered
  const column = columns.find((c) => c.key === sort.key)
  if (!column) return filtered

  const value = (row: T) => column.sortValue?.(row) ?? getCell(row, column.key)
  return [...filtered].sort((a, b) => {
    const av = value(a), bv = value(b)
    const result = typeof av === 'number' && typeof bv === 'number'
      ? av - bv
      : String(av).localeCompare(String(bv))
    return sort.direction === 'ascending' ? result : -result
  })
}, [filtered, sort, columns, getCell])
```

- **`[...filtered]` before `.sort()`.** `Array.prototype.sort` mutates in place, and `filtered` is
  the `rows` *prop itself* when no query is active — so without the copy you'd be reordering your
  caller's array.
- **Numbers compared numerically.** `String(143) < String(88)` is true; a naive `localeCompare`
  everywhere is the classic sorted-numbers bug.
- Two memos rather than one, so typing in the filter doesn't redo the sort comparator setup and a
  sort change doesn't refilter.

**2 — Clamp, don't store.**

```tsx
const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize))
const safePage = Math.min(page, pageCount - 1)
const pageRows = sorted.slice(safePage * pageSize, safePage * pageSize + pageSize)
```

`page` is what the user asked for; `safePage` is what's possible. Deriving it means every path
that shrinks the result set — filtering, deleting a row, a new `rows` prop — is handled by one
line. Resetting the page inside the filter's `onChange` handles only the case you remembered.

**3 — Selection as a Set, copied on write.**

```tsx
function toggleRow(id: string) {
  setSelected((prev) => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  })
}
```

`new Set(prev)` is the part people forget. Mutating `prev` in place leaves React holding the same
reference, so nothing re-renders — a bug that's invisible in review.

**4 — Sort header markup.**

```tsx
<th scope="col" aria-sort={active ? sort!.direction : undefined}>
  {col.sortable ? (
    <button type="button" onClick={() => toggleSort(col.key)}>
      {col.header}
      <span aria-hidden="true">{active ? (sort!.direction === 'ascending' ? '▲' : '▼') : '↕'}</span>
    </button>
  ) : col.header}
</th>
```

The button is inside the `th` so the header is still a header; the arrow is `aria-hidden` because
`aria-sort` already conveys it.

**5 — THE WHOLE THING.**

<details>
<summary>Complete implementation — DataTable</summary>

```tsx
import { useId, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

/**
 * The bug this component exists to teach isn't accessibility, it's derived state:
 *
 *   FILTER, THEN SORT, THEN PAGINATE — and reset the page when the filter changes.
 *
 * Filter down to two results while sitting on page 5 and you render an empty
 * table with working pagination. Users report it as "the search is broken".
 *
 * The other half is `<table>` semantics. A grid of divs loses row/column
 * navigation entirely; screen reader users navigate tables with dedicated keys
 * that only work on real table markup.
 */

export interface Column<T> {
  key: string
  header: string
  sortable?: boolean
  /** Sort key. Defaults to the raw cell value. */
  sortValue?: (row: T) => string | number
  render?: (row: T) => ReactNode
}

export interface DataTableProps<T> {
  rows: T[]
  columns: Column<T>[]
  caption: string
  getRowId: (row: T) => string
  getCell: (row: T, key: string) => string | number
  pageSize?: number
  selectable?: boolean
}

type SortState = { key: string; direction: 'ascending' | 'descending' } | null

export function DataTable<T>({
  rows,
  columns,
  caption,
  getRowId,
  getCell,
  pageSize = 5,
  selectable = false,
}: DataTableProps<T>) {
  const baseId = useId()
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortState>(null)
  const [page, setPage] = useState(0)
  // A Set here, unlike the array in Accordion. Selection is INTERNAL state with
  // one membership check per rendered row, and it can reach thousands of entries
  // — exactly where O(1) lookup and O(1) toggling start to matter.
  const [selected, setSelected] = useState<Set<string>>(() => new Set())

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return rows
    return rows.filter((row) =>
      columns.some((col) => String(getCell(row, col.key)).toLowerCase().includes(q)),
    )
  }, [rows, columns, query, getCell])

  const sorted = useMemo(() => {
    if (!sort) return filtered
    const column = columns.find((c) => c.key === sort.key)
    if (!column) return filtered

    const value = (row: T) => column.sortValue?.(row) ?? getCell(row, column.key)
    // Copy before sorting: Array.prototype.sort mutates, and `filtered` may be
    // the `rows` prop itself when no query is active.
    return [...filtered].sort((a, b) => {
      const av = value(a)
      const bv = value(b)
      const result = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv))
      return sort.direction === 'ascending' ? result : -result
    })
  }, [filtered, sort, columns, getCell])

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize))
  // Clamp rather than store. If the filter shrinks the results while you're on
  // page 5, deriving the page keeps the table showing rows instead of nothing.
  const safePage = Math.min(page, pageCount - 1)
  const pageRows = sorted.slice(safePage * pageSize, safePage * pageSize + pageSize)

  function toggleSort(key: string) {
    setSort((prev) =>
      prev?.key === key
        ? prev.direction === 'ascending'
          ? { key, direction: 'descending' }
          : null // third click clears — sorting is not a one-way door
        : { key, direction: 'ascending' },
    )
  }

  function toggleRow(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      // The copy is the part people forget. Mutating `prev` in place leaves React
      // holding the same reference, so nothing re-renders.
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const allOnPageSelected = pageRows.length > 0 && pageRows.every((r) => selected.has(getRowId(r)))

  return (
    <div className="table-wrap">
      <div className="table-toolbar">
        <label className="table-search">
          <span className="visually-hidden">Filter rows</span>
          <input
            type="search"
            placeholder="Filter…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setPage(0) // belt as well as braces; the clamp above is the braces
            }}
          />
        </label>
        {selectable && (
          <span className="table-count">{selected.size} selected</span>
        )}
      </div>

      <table className="table">
        {/* A caption is the table's accessible name and is announced when a
            screen reader user enters it. Better than aria-label: it's visible. */}
        <caption className="table-caption">{caption}</caption>
        <thead>
          <tr>
            {selectable && (
              <th scope="col" className="table-select-col">
                <input
                  type="checkbox"
                  aria-label="Select all rows on this page"
                  checked={allOnPageSelected}
                  onChange={(e) => {
                    setSelected((prev) => {
                      const next = new Set(prev)
                      for (const row of pageRows) {
                        if (e.target.checked) next.add(getRowId(row))
                        else next.delete(getRowId(row))
                      }
                      return next
                    })
                  }}
                />
              </th>
            )}
            {columns.map((col) => {
              const active = sort?.key === col.key
              return (
                // aria-sort belongs on the TH, not on the button inside it, and
                // only on the column actually sorted.
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={active ? sort!.direction : undefined}
                >
                  {col.sortable ? (
                    <button
                      type="button"
                      className="table-sort"
                      onClick={() => toggleSort(col.key)}
                    >
                      {col.header}
                      <span aria-hidden="true" className="table-sort-icon">
                        {active ? (sort!.direction === 'ascending' ? '▲' : '▼') : '↕'}
                      </span>
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              )
            })}
          </tr>
        </thead>

        <tbody>
          {pageRows.map((row) => {
            const id = getRowId(row)
            return (
              <tr key={id} aria-selected={selectable ? selected.has(id) : undefined}>
                {selectable && (
                  <td>
                    <input
                      type="checkbox"
                      aria-labelledby={`${baseId}-row-${id}`}
                      checked={selected.has(id)}
                      onChange={() => toggleRow(id)}
                    />
                  </td>
                )}
                {columns.map((col, i) => {
                  const content = col.render ? col.render(row) : getCell(row, col.key)
                  // The first column is the row's header, which is what lets AT
                  // say "Ada Lovelace, Engineering" instead of just "Engineering".
                  return i === 0 ? (
                    <th key={col.key} scope="row" id={`${baseId}-row-${id}`}>
                      {content}
                    </th>
                  ) : (
                    <td key={col.key}>{content}</td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>

      {sorted.length === 0 && (
        <p className="table-empty">No rows match “{query}”.</p>
      )}

      <div className="table-pager">
        <button type="button" onClick={() => setPage(safePage - 1)} disabled={safePage === 0}>
          Previous
        </button>
        {/* Announced, because the rows changing underneath is otherwise silent. */}
        <span role="status" aria-live="polite">
          Page {safePage + 1} of {pageCount} · {sorted.length} rows
        </span>
        <button
          type="button"
          onClick={() => setPage(safePage + 1)}
          disabled={safePage >= pageCount - 1}
        >
          Next
        </button>
      </div>
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| Divs instead of `<table>` | Table navigation gone for screen-reader users |
| `.sort()` without copying | You reorder the caller's `rows` prop |
| `localeCompare` on numbers | 143 sorts before 88 |
| Storing a corrected page | Filter on page 5 → empty table, "search is broken" |
| Mutating the selection Set | React sees the same reference; nothing re-renders |
| Selection keyed by index | Sorting moves the selection to different rows |
| `aria-sort` on every column | Noise; the sorted column stops standing out |
| `aria-sort` on the button | Wrong element; AT reads it off the header cell |
| Row checkboxes all named "Select row" | Unusable with more than one row |
| No empty state | A blank table looks broken |

### G. SPEC

**Semantics** — a real table with a caption and column headers · the first cell of each row is a
row header

**Sorting** — cycles ascending → descending → none · only the sorted column carries `aria-sort` ·
numbers sort numerically · **does not mutate the rows prop**

**Filtering/pagination** — filters across every column · paginates · **filtering while on a later
page still shows rows** · announces page and total · shows an empty state

**Selection** — toggles and counts · checkboxes named by their row · select-all covers the current
page only · **selection survives sorting**

## 14 — Streaming message

> Runnable: `uie-practice/src/exercises/streaming-message-reference/` · Spec: 12 tests

### A. ASKED AS

- "Build a chat message that streams in"
- "Show the model's response as it arrives"
- "Add a stop button to this chat"

The single highest-probability component at an AI company. Practise this one cold.

### B. API

```tsx
export type StreamStatus = 'idle' | 'streaming' | 'done' | 'stopped' | 'error'

export interface StreamingMessageProps {
  stream: (
    prompt: string,
    onToken: (token: string) => void,
    signal: AbortSignal,
  ) => Promise<void>
  placeholder?: string
}
```

**Callback-plus-signal, not an async iterable.** An `AsyncIterable<string>` is arguably prettier,
but the callback form takes the `AbortSignal` explicitly — which makes cancellation a visible part
of the contract rather than something you hope `for await` handles. Name the alternative; picking
either is fine, having no answer is not.

**Five statuses, not `isLoading`.** `stopped` and `error` are genuinely different: one is the user
choosing, one is a failure. Collapse them and you show "Something went wrong" to someone who
pressed Stop.

### C. ACCESSIBILITY — the counter-intuitive one

> **Do not put `aria-live` on the streaming text.**

A live region announces every mutation. A token stream mutates thirty times a second, so a screen
reader reads the answer letter by letter, permanently behind, with no way to stop. Instead:

| Element | Attribute |
|---|---|
| The streamed text | `aria-busy={streaming}` — and nothing else |
| A visually-hidden status line | `role="status"` `aria-live="polite"`, one short sentence per transition |

"Responding" → "Response complete". Four words per stream instead of four hundred. The user then
reads the finished answer at their own pace.

### D. DECISIONS THAT MATTER

1. **Abort on unmount.** Navigate away mid-stream without it and the request keeps running while
   `onToken` calls `setState` on a dead component.
2. **Bump the generation on stop.** Abort alone leaves tokens already in flight to trickle in after
   the click. Incrementing the counter makes Stop feel instant because late tokens are *dropped*,
   not merely un-requested.
3. **An abort is not an error.** `signal.aborted` distinguishes "the user pressed Stop" from "the
   network died". Same rejected promise, completely different UI.
4. **Retry re-sends the stored prompt.** Keep the sent value separately from the input, or retry
   sends whatever the user has since typed.

### E. IMPLEMENTATION

**1 — One function drives send, retry, and supersede.**

```tsx
const run = useCallback(async (value: string) => {
  controllerRef.current?.abort()
  const controller = new AbortController()
  controllerRef.current = controller
  const generation = ++generationRef.current

  setSent(value)
  setText('')
  setStatus('streaming')

  try {
    await stream(value, (token) => {
      if (generation !== generationRef.current) return
      setText((prev) => prev + token)
    }, controller.signal)
    if (generation !== generationRef.current) return
    setStatus('done')
  } catch {
    if (generation !== generationRef.current) return
    setStatus(controller.signal.aborted ? 'stopped' : 'error')
  }
}, [stream])
```

- **The guard inside `onToken` is the important one.** That closure outlives the render that made
  it. Without the check, a retry's tokens interleave with the previous stream's and you get two
  answers spliced together — a bug that only appears when someone retries fast.
- **`setText((prev) => prev + token)`** — functional updater, because tokens arrive faster than
  renders commit.
- Aborting the previous controller at the top means send-while-streaming supersedes cleanly.

**2 — Stop bumps the generation before aborting.**

```tsx
function stop() {
  generationRef.current++
  controllerRef.current?.abort()
  setStatus('stopped')
}
```

Order matters. Bump first, so anything the abort shakes loose is already stale.

**3 — Unmount cleanup, one line.**

```tsx
useEffect(() => () => controllerRef.current?.abort(), [])
```

**4 — THE WHOLE THING.**

<details>
<summary>Complete implementation — StreamingMessage</summary>

```tsx
import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * The highest-probability component at any AI company, and the one where the
 * accessibility instinct is backwards:
 *
 *   DO NOT PUT aria-live ON THE STREAMING TEXT.
 *
 * A live region announces every mutation. A token stream mutates thirty times a
 * second, so a screen reader would read the answer letter by letter, forever
 * behind, with no way to stop it. Announce the STATUS ("Responding", "Response
 * complete") in a live region and mark the text `aria-busy` — then the user reads
 * the finished answer when they choose to.
 *
 * The other three are the async ones: stop must be instant, retry must not race,
 * and unmounting mid-stream must not warn.
 */

export type StreamStatus = 'idle' | 'streaming' | 'done' | 'stopped' | 'error'

export interface StreamingMessageProps {
  /**
   * Push tokens through `onToken`; resolve when the stream ends. Must honor the
   * signal — the component aborts it on stop, retry, and unmount.
   */
  stream: (prompt: string, onToken: (token: string) => void, signal: AbortSignal) => Promise<void>
  placeholder?: string
}

export function StreamingMessage({ stream, placeholder }: StreamingMessageProps) {
  const [prompt, setPrompt] = useState('')
  const [sent, setSent] = useState('')
  const [text, setText] = useState('')
  const [status, setStatus] = useState<StreamStatus>('idle')

  const controllerRef = useRef<AbortController | null>(null)
  // Same two-layer guard as the combobox: abort stops the source, the generation
  // counter stops anything that already slipped past it from writing state.
  const generationRef = useRef(0)

  const run = useCallback(
    async (value: string) => {
      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller
      const generation = ++generationRef.current

      setSent(value)
      setText('')
      setStatus('streaming')

      try {
        await stream(
          value,
          (token) => {
            // Tokens arrive from a closure that outlives the render that made it.
            // Without this check, a retry's tokens interleave with the previous
            // stream's and you get two answers spliced together.
            if (generation !== generationRef.current) return
            setText((prev) => prev + token)
          },
          controller.signal,
        )
        if (generation !== generationRef.current) return
        setStatus('done')
      } catch {
        if (generation !== generationRef.current) return
        // An abort is not an error. Stopping deliberately shouldn't show a
        // failure state, and unmounting shouldn't show anything at all.
        setStatus(controller.signal.aborted ? 'stopped' : 'error')
      }
    },
    [stream],
  )

  // Abort on unmount. Without this, navigating away mid-stream leaves the request
  // running and the onToken closure calling setState on a dead component.
  useEffect(() => () => controllerRef.current?.abort(), [])

  function stop() {
    // Bumping the generation is what makes stop feel instant: tokens already in
    // flight are dropped rather than trickling in after the button click.
    generationRef.current++
    controllerRef.current?.abort()
    setStatus('stopped')
  }

  const busy = status === 'streaming'

  return (
    <div className="stream">
      <form
        className="stream-form"
        onSubmit={(event) => {
          event.preventDefault()
          if (!prompt.trim()) return
          run(prompt.trim())
        }}
      >
        <label className="visually-hidden" htmlFor="stream-prompt">
          Message
        </label>
        <input
          id="stream-prompt"
          className="stream-input"
          value={prompt}
          placeholder={placeholder}
          onChange={(e) => setPrompt(e.target.value)}
        />
        {busy ? (
          <button type="button" className="stream-stop" onClick={stop}>
            Stop
          </button>
        ) : (
          <button type="submit" className="stream-send" disabled={!prompt.trim()}>
            Send
          </button>
        )}
      </form>

      {status !== 'idle' && (
        <div className="stream-output">
          {/* aria-busy, NOT aria-live. The status line below does the announcing. */}
          <p className="stream-text" aria-busy={busy}>
            {text}
            {busy && <span className="stream-caret" aria-hidden="true" />}
          </p>

          {status === 'stopped' && <p className="stream-meta">Stopped.</p>}
          {status === 'error' && (
            <p className="stream-meta stream-meta--error">Something went wrong.</p>
          )}
          {(status === 'error' || status === 'stopped') && (
            <button type="button" className="stream-retry" onClick={() => run(sent)}>
              Retry
            </button>
          )}
        </div>
      )}

      {/* One short sentence per transition — the entire accessible surface of a
          stream. Empty while idle so nothing is announced on mount. */}
      <div className="visually-hidden" role="status" aria-live="polite">
        {status === 'streaming'
          ? 'Responding'
          : status === 'done'
            ? 'Response complete'
            : status === 'stopped'
              ? 'Response stopped'
              : status === 'error'
                ? 'Response failed'
                : ''}
      </div>
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| `aria-live` on the streaming text | The answer is read letter by letter, unstoppably |
| No unmount abort | Request keeps running; setState on a dead component |
| Abort without a generation bump | Tokens trickle in after Stop; the button feels broken |
| Treating abort as an error | "Something went wrong" after the user pressed Stop |
| `setText(text + token)` | Dropped tokens — renders lag the stream |
| Retry reads the live input | Retries whatever the user typed since, not what failed |
| No stale guard in `onToken` | Two answers spliced together after a fast retry |
| Blinking caret with no reduced-motion guard | Persistent motion for users who asked for none |

### G. SPEC

**Streaming** — appends tokens as they arrive · swaps Send for Stop while streaming

**Accessibility** — the streaming text is **not** a live region · status transitions are announced
instead · `aria-busy` clears when it ends

**Stop** — aborts and reports stopped, not failed · **tokens still in flight are discarded** ·
partial text stays visible

**Errors/retry** — a real failure shows an error, not "stopped" · retry re-sends the same prompt
and clears the old text · a new send discards the previous stream rather than interleaving

**Unmount** — aborts in flight without warning

## 15 — Carousel

> Runnable: `uie-practice/src/exercises/carousel-reference/` · Spec: 14 tests

### A. ASKED AS

- "Build an image carousel" / "a slideshow" / "a featured-content rotator"
- "Build an image gallery with thumbnails" — same, with the dots as thumbnails

### B. API

```tsx
export interface CarouselSlide {
  value: string
  content: ReactNode
}

export interface CarouselProps {
  slides: CarouselSlide[]
  label: string
  autoPlay?: boolean     // ignored entirely under prefers-reduced-motion
  intervalMs?: number
}
```

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Container | `role="group"`, `aria-roledescription="carousel"`, `aria-label` |
| Viewport | `aria-live` — **`"off"` while rotating, `"polite"` once stopped** |
| Slide | `role="group"`, `aria-roledescription="slide"`, `aria-label="3 of 5"` |
| Play/pause | Name states the **action** (`"Pause…"` when playing), not the state |
| Dots | `aria-current` — they're navigation, not listbox options |

`aria-roledescription` renames the role for screen readers: "Featured, carousel" rather than
"Featured, group". It requires a real accessible name to attach to.

### D. DECISIONS THAT MATTER — this is a legal question, not a taste one

1. **WCAG 2.2.2 (Pause, Stop, Hide) is LEVEL A.** Motion that starts automatically, lasts more
   than five seconds, and sits alongside other content **must** have a pause control. A carousel
   that auto-advances with no pause button is a conformance failure. Say this out loud; most
   candidates treat autoplay as a product decision.
2. **`prefers-reduced-motion` means don't auto-advance at all.** Vestibular disorders are why the
   media query exists. Under it, there's no rotation and therefore no play control to render.
3. **Two different pause states, and conflating them is the bug.** Hover/focus *suspends*
   transiently and resumes on leave. The pause button and any manual navigation stop it
   *permanently*. If moving the mouse away restarts motion the user deliberately stopped, you've
   taken the control back off them.
4. **`aria-live` flips with the play state.** `"off"` while rotating — nobody wants a slide
   announced every four seconds. `"polite"` once the user drives, because now the change is a
   response to their own action.

### E. IMPLEMENTATION

**1 — Reduced motion, read at first render.**

```tsx
function prefersReducedMotion() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(prefersReducedMotion)   // lazy initializer

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  return reduced
}
```

- A **lazy initializer**, not `useState(false)` plus a `setState` in the effect. Seeding from the
  effect renders one frame of motion before correcting itself — visible to exactly the people the
  setting protects — and it's a cascading render the React lint rejects.
- **Subscribed, not read once.** A user can change the setting while the page is open.
- The `typeof` guards cover SSR and jsdom, neither of which has `matchMedia`.

**2 — Three booleans, one derived truth.**

```tsx
const [playing, setPlaying] = useState(autoPlay)     // the user's explicit choice
const [suspended, setSuspended] = useState(false)    // transient hover/focus
const rotating = playing && !suspended && !reducedMotion

useEffect(() => {
  if (!rotating || count <= 1) return
  const timer = window.setInterval(() => setIndex((i) => (i + 1) % count), intervalMs)
  return () => window.clearInterval(timer)
}, [rotating, count, intervalMs])
```

Keeping `playing` and `suspended` separate is what makes decision 3 work: leaving the carousel
clears `suspended` but can't revive a `playing` the user turned off. One combined boolean cannot
express that. `count <= 1` avoids an interval that re-renders forever to show the same slide.

**3 — Manual navigation stops rotation.**

```tsx
const go = (next: number) => {
  setIndex((next + count) % count)
  setPlaying(false)
}
```

Every arrow and every dot goes through `go`. Fighting the user for control of the viewport is the
single most-hated carousel behavior there is.

**4 — Icon buttons need real names.**

```tsx
<button type="button" onClick={() => go(index - 1)}>
  <span aria-hidden="true">‹</span>
  <span className="visually-hidden">Previous slide</span>
</button>
```

Leaving the bare `‹` in the accessible name yields "‹ Previous slide", which some screen readers
read as "left angle bracket". Hide the glyph, name the button.

**5 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Carousel</summary>

```tsx
import { useEffect, useId, useState } from 'react'
import type { ReactNode } from 'react'

/**
 * A carousel is where accessibility law shows up, not just guidance:
 *
 *   WCAG 2.2.2 (Pause, Stop, Hide) — LEVEL A. Any motion that starts
 *   automatically, lasts more than five seconds, and sits alongside other content
 *   MUST have a pause control. A carousel that auto-advances with no pause button
 *   is a straight conformance failure, not a nice-to-have.
 *
 * Three more that follow from it:
 *
 *   - prefers-reduced-motion means don't auto-advance at all. Vestibular
 *     disorders are the reason the media query exists.
 *   - Pause on hover AND on focus. A keyboard user tabbing to "next" needs the
 *     same reprieve a mouse user gets.
 *   - aria-live flips with the play state. While rotating it's "off" (nobody wants
 *     a slide announced every four seconds); once the user takes manual control it
 *     becomes "polite", because now the change is a response to their action.
 */

export interface CarouselSlide {
  value: string
  content: ReactNode
}

export interface CarouselProps {
  slides: CarouselSlide[]
  label: string
  /** Start auto-rotating. Ignored entirely under prefers-reduced-motion. */
  autoPlay?: boolean
  intervalMs?: number
}

const REDUCED_MOTION = '(prefers-reduced-motion: reduce)'

/** jsdom has no matchMedia, and neither does an SSR pass. */
function prefersReducedMotion() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia(REDUCED_MOTION).matches
}

/** Live subscription, because a user can change this setting while the page is open. */
function usePrefersReducedMotion() {
  // Lazy initializer rather than useState(false) plus a setState in the effect.
  // Seeding from the effect would render one frame of motion before correcting
  // itself — visible to exactly the people the setting exists to protect — and
  // it's a cascading render the compiler lint rightly rejects.
  const [reduced, setReduced] = useState(prefersReducedMotion)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const query = window.matchMedia(REDUCED_MOTION)
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  return reduced
}

export function Carousel({ slides, label, autoPlay = false, intervalMs = 4000 }: CarouselProps) {
  const baseId = useId()
  const slideId = (i: number) => `${baseId}-slide-${i}`

  const [index, setIndex] = useState(0)
  const reducedMotion = usePrefersReducedMotion()
  // The user's explicit play/pause choice, separate from the transient hover/focus
  // pause. Conflating them means moving the mouse away silently restarts motion
  // the user deliberately stopped.
  const [playing, setPlaying] = useState(autoPlay)
  const [suspended, setSuspended] = useState(false)

  const rotating = playing && !suspended && !reducedMotion
  const count = slides.length

  useEffect(() => {
    if (!rotating || count <= 1) return
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % count), intervalMs)
    return () => window.clearInterval(timer)
  }, [rotating, count, intervalMs])

  const go = (next: number) => {
    setIndex((next + count) % count)
    // Any manual navigation stops auto-rotation. Fighting the user for control of
    // the viewport is the single most-hated carousel behavior there is.
    setPlaying(false)
  }

  return (
    <div
      className="carousel"
      // roledescription renames the role for screen readers: "Featured, carousel"
      // instead of "Featured, group". Requires a real accessible name to attach to.
      role="group"
      aria-roledescription="carousel"
      aria-label={label}
      onPointerEnter={() => setSuspended(true)}
      onPointerLeave={() => setSuspended(false)}
      onFocus={() => setSuspended(true)}
      onBlur={() => setSuspended(false)}
    >
      <div className="carousel-controls">
        {/* WCAG 2.2.2. Rendered whenever rotation is possible at all — hiding it
            while paused would strand a user who paused and wants to resume. */}
        {!reducedMotion && count > 1 && (
          <button
            type="button"
            className="carousel-play"
            onClick={() => setPlaying((p) => !p)}
            // The name states the ACTION, not the state. "Pause" when it's playing.
            aria-label={playing ? 'Pause automatic slide rotation' : 'Start automatic slide rotation'}
          >
            {playing ? '❚❚' : '▶'}
          </button>
        )}

        {/* The glyph is aria-hidden and the real name is visually hidden. Leaving
            the bare "‹" in the accessible name yields "‹ Previous slide", which
            some screen readers read aloud as "left angle bracket". */}
        <button type="button" className="carousel-arrow" onClick={() => go(index - 1)}>
          <span aria-hidden="true">‹</span>
          <span className="visually-hidden">Previous slide</span>
        </button>
        <button type="button" className="carousel-arrow" onClick={() => go(index + 1)}>
          <span aria-hidden="true">›</span>
          <span className="visually-hidden">Next slide</span>
        </button>
      </div>

      {/* Off while rotating, polite once the user drives. Announcing every slide
          during autoplay makes the page unusable with a screen reader. */}
      <div className="carousel-viewport" aria-live={rotating ? 'off' : 'polite'}>
        {slides.map((slide, i) => (
          <div
            key={slide.value}
            id={slideId(i)}
            role="group"
            aria-roledescription="slide"
            // "3 of 5" is genuinely useful; "Slide" alone is not.
            aria-label={`${i + 1} of ${count}`}
            className="carousel-slide"
            hidden={i !== index}
          >
            {slide.content}
          </div>
        ))}
      </div>

      <div className="carousel-dots">
        {slides.map((slide, i) => (
          <button
            key={slide.value}
            type="button"
            className="carousel-dot"
            aria-label={`Go to slide ${i + 1} of ${count}`}
            // aria-current, not aria-selected: these are navigation controls, not
            // options in a listbox.
            aria-current={i === index ? 'true' : undefined}
            aria-controls={slideId(i)}
            onClick={() => go(i)}
          />
        ))}
      </div>
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| Autoplay with no pause control | WCAG 2.2.2 Level A failure |
| Ignoring `prefers-reduced-motion` | Motion sickness for the users the query exists to protect |
| One boolean for hover-suspend and user-pause | Moving the mouse away restarts motion the user stopped |
| `aria-live="polite"` while rotating | A slide announced every four seconds; page unusable with AT |
| Manual navigation doesn't stop rotation | The carousel advances a second after the user chose a slide |
| Bare glyph as the button's name | "left angle bracket" |
| Play button labelled with its state | "Playing" gives no clue what pressing it does |
| Dots with `aria-selected` | They're navigation controls, not listbox options |
| Dots at their visual 9px size | Below the 24×24 minimum target (WCAG 2.5.8) |

### G. SPEC

**Semantics** — announces as a carousel · slides say "n of N" · offscreen slides are outside the
accessibility tree · dots use `aria-current`

**Navigation** — next/previous move and wrap · a dot jumps directly

**WCAG 2.2.2** — a pause control exists whenever rotation is possible · it auto-advances while
playing · pausing stops it and the control offers to resume · hovering suspends and leaving
resumes · focus suspends too · manual navigation stops it permanently · the live region is `off`
while rotating and `polite` once stopped

## 16 — Form + validation

> Runnable: `uie-practice/src/exercises/form-reference/` · Spec: 13 tests

### A. ASKED AS

- "Build a signup form with validation"
- "Build a contact form" / "a checkout step"
- "Validate that the passwords match" — the cross-field case

### B. API

```tsx
export interface FormField {
  name: string
  label: string
  type?: 'text' | 'email' | 'password'
  validate?: (value: string, values: Record<string, string>) => string | null
}

export interface FormProps {
  fields: FormField[]
  onSubmit: (values: Record<string, string>) => Promise<void>
  submitLabel?: string
}
```

**`validate` receives all the values**, not just its own. That's what makes "passwords must match"
and "end date after start date" expressible without a second mechanism.

**`validate` returns `string | null`**, not a boolean. The message *is* the result — a boolean
forces a parallel lookup table of error text that drifts from the rules.

**`onSubmit` returns a promise and may reject.** Rejection is the server-error path; values are
kept either way.

### C. WIRING

| Element | Required |
|---|---|
| Input | real `<label htmlFor>`; `aria-invalid` and `aria-describedby` **only while erroring** |
| Error message | `id` matching the `aria-describedby` |
| Form outcome | `role="alert"` |

**`aria-invalid="false"` on every field is noise**, and an `aria-describedby` pointing at a
message that isn't rendered is a broken promise. Both appear only alongside a real error.

**A real `<label>`, not a placeholder.** A placeholder disappears the moment the user types, isn't
an accessible name, and fails contrast almost everywhere.

**Error text must not rely on colour** (WCAG 1.4.1). The message says what's wrong in words; the
red border is reinforcement, not the signal.

### D. DECISIONS THAT MATTER — timing is the whole component

1. **Validate on blur. Then, once a field has erred, validate that field on change.** Validating
   from the first keystroke tells someone their email is invalid while they're typing the "j" of
   "jane@…". Never validating on change means they must tab away to discover they fixed it. The
   two-phase rule is what everyone gets wrong, in one direction or the other.
2. **`event.preventDefault()` before any `await`.** Miss it and the browser does a full-page form
   post, which presents as "my handler never ran".
3. **Submit validates everything and moves focus to the first problem.** Without the focus move, a
   keyboard or screen-reader user gets a rejected submit and no idea where to look.
4. **Disable the submit while in flight.** A double-click that posts twice is a duplicate charge.
5. **Keep the values on server error.** Retyping a form you already filled in is the fastest way
   to lose a user.

### E. IMPLEMENTATION

**1 — Three pieces of state, and the third is the interesting one.**

```tsx
const [values, setValues] = useState<Record<string, string>>(...)
const [errors, setErrors] = useState<Record<string, string>>({})
const [erred, setErred] = useState<Record<string, boolean>>({})
```

`erred` means "this field has already been told off once", and it's what flips a field from
validate-on-blur to validate-on-change. It is *not* the same as `touched`: a field you visited and
left valid should stay quiet while you edit it again.

**2 — The two-phase rule, in four lines.**

```tsx
function handleChange(field: FormField, value: string) {
  const nextValues = { ...values, [field.name]: value }
  setValues(nextValues)
  if (erred[field.name]) setError(field.name, validateField(field, nextValues))
}

function handleBlur(field: FormField) {
  setError(field.name, validateField(field, values))
}
```

`handleChange` validates against `nextValues`, not `values` — state hasn't updated yet, and
validating the previous value is off-by-one-keystroke, which looks exactly like a flaky validator.

**3 — Submit.**

```tsx
event.preventDefault()
if (status === 'submitting') return

const nextErrors: Record<string, string> = {}
for (const field of fields) {
  const message = validateField(field, values)
  if (message) nextErrors[field.name] = message
}
setErrors(nextErrors)

const firstBad = fields.find((f) => nextErrors[f.name])
if (firstBad) {
  inputRefs.current.get(firstBad.name)?.focus()
  return
}
```

`fields.find` rather than `Object.keys(nextErrors)[0]` — object key order is not the visual order
of the form, and focus must land on the *first field on screen* that's wrong.

The `status === 'submitting'` guard backs up the disabled button, because `disabled` is a UI
affordance and a fast Enter-Enter can still get through.

**4 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Form</summary>

```tsx
import { useRef, useState } from 'react'
import type { FormEvent } from 'react'

/**
 * Validation TIMING is the whole component, and almost everyone gets it backwards.
 *
 *   Validate on change from the first keystroke and you tell someone their email
 *   is invalid while they're typing the "j" of "jane@…". It's hostile, and users
 *   learn to ignore the red.
 *
 *   The rule: validate a field on BLUR. After it has errored once, switch that
 *   field to validating on CHANGE, so the error clears the moment it's fixed
 *   rather than making them tab away to find out.
 *
 * Everything else follows: errors are wired with aria-describedby, submit
 * validates everything and moves focus to the first problem, and the submit
 * button is disabled while in flight so a double-click can't post twice.
 */

export interface FormField {
  name: string
  label: string
  type?: 'text' | 'email' | 'password'
  /** Return an error string, or null when valid. */
  validate?: (value: string, values: Record<string, string>) => string | null
}

export interface FormProps {
  fields: FormField[]
  /** Reject to surface a form-level error. Values are kept either way. */
  onSubmit: (values: Record<string, string>) => Promise<void>
  submitLabel?: string
}

type Status = 'idle' | 'submitting' | 'success' | 'error'

export function Form({ fields, onSubmit, submitLabel = 'Submit' }: FormProps) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((f) => [f.name, ''])),
  )
  const [errors, setErrors] = useState<Record<string, string>>({})
  // "This field has already been told off once", which is what flips it from
  // validate-on-blur to validate-on-change.
  const [erred, setErred] = useState<Record<string, boolean>>({})
  const [status, setStatus] = useState<Status>('idle')
  const [formError, setFormError] = useState<string | null>(null)

  const inputRefs = useRef(new Map<string, HTMLInputElement | null>())

  function validateField(field: FormField, nextValues: Record<string, string>) {
    return field.validate?.(nextValues[field.name] ?? '', nextValues) ?? null
  }

  function setError(name: string, message: string | null) {
    setErrors((prev) => {
      const next = { ...prev }
      if (message) next[name] = message
      else delete next[name]
      return next
    })
    if (message) setErred((prev) => ({ ...prev, [name]: true }))
  }

  function handleChange(field: FormField, value: string) {
    const nextValues = { ...values, [field.name]: value }
    setValues(nextValues)
    // Only re-validate a field that has already failed. Before that, typing is
    // just typing.
    if (erred[field.name]) setError(field.name, validateField(field, nextValues))
  }

  function handleBlur(field: FormField) {
    setError(field.name, validateField(field, values))
  }

  async function handleSubmit(event: FormEvent) {
    // Before any await. Miss it and the browser does a full-page form post,
    // which looks like "my handler never ran".
    event.preventDefault()
    if (status === 'submitting') return

    const nextErrors: Record<string, string> = {}
    for (const field of fields) {
      const message = validateField(field, values)
      if (message) nextErrors[field.name] = message
    }
    setErrors(nextErrors)
    setErred((prev) => ({
      ...prev,
      ...Object.fromEntries(Object.keys(nextErrors).map((k) => [k, true])),
    }))

    const firstBad = fields.find((f) => nextErrors[f.name])
    if (firstBad) {
      // Move focus to the problem. Without this a keyboard or screen-reader user
      // gets a rejected submit with no idea where the error is.
      inputRefs.current.get(firstBad.name)?.focus()
      return
    }

    setStatus('submitting')
    setFormError(null)
    try {
      await onSubmit(values)
      setStatus('success')
    } catch (error) {
      setStatus('error')
      setFormError(error instanceof Error ? error.message : 'Something went wrong')
    }
  }

  const submitting = status === 'submitting'

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      {fields.map((field) => {
        const error = errors[field.name]
        const errorId = `${field.name}-error`

        return (
          <div className="form-row" key={field.name}>
            {/* A real <label htmlFor>. Placeholder-as-label disappears the moment
                the user types, and is not an accessible name. */}
            <label className="form-label" htmlFor={field.name}>
              {field.label}
            </label>
            <input
              ref={(el) => {
                inputRefs.current.set(field.name, el)
              }}
              id={field.name}
              name={field.name}
              type={field.type ?? 'text'}
              className="form-input"
              value={values[field.name] ?? ''}
              // Only when there IS an error — aria-invalid="false" on every field
              // is noise, and a describedby pointing at nothing is a broken promise.
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? errorId : undefined}
              disabled={submitting}
              onChange={(e) => handleChange(field, e.target.value)}
              onBlur={() => handleBlur(field)}
            />
            {error && (
              <p id={errorId} className="form-error">
                {error}
              </p>
            )}
          </div>
        )
      })}

      <button type="submit" className="form-submit" disabled={submitting}>
        {submitting ? 'Submitting…' : submitLabel}
      </button>

      {/* Form-level outcome. role="alert" is assertive on purpose: the user just
          acted and is waiting on exactly this answer. */}
      <div role="alert" className="form-status">
        {status === 'success' && <span className="form-success">Saved.</span>}
        {status === 'error' && formError && <span className="form-error">{formError}</span>}
      </div>
    </form>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| Validate on change from the first keystroke | Errors while the user is still typing; they learn to ignore red |
| Only ever validate on blur | Fixing an error requires tabbing away to find out |
| Validating against `values` inside `onChange` | Off by one keystroke; looks like a flaky validator |
| No `preventDefault()` | Full-page form post; "my handler never ran" |
| No focus move on invalid submit | Keyboard users get a rejection with no location |
| Focus from `Object.keys(errors)[0]` | Lands on whichever key was inserted first, not the first field |
| Submit not disabled while in flight | Double-click posts twice |
| Values cleared on server error | The user retypes everything |
| Placeholder instead of `<label>` | No accessible name; the hint vanishes on first keystroke |
| `aria-invalid="false"` everywhere | Noise; and a dangling `describedby` when there's no message |
| Colour as the only error signal | WCAG 1.4.1 failure |

### G. SPEC

**Timing** — typing an invalid value says nothing yet · blurring validates · once a field has
erred it validates on every keystroke

**Wiring** — the error is linked to its input, and only while it exists · every input has a real
label

**Submit** — an invalid submit is blocked and focus moves to the first problem · focus goes to the
first *invalid* field, not simply the first field · a valid submit passes the values through ·
double-clicking cannot submit twice · fields are locked while in flight

**Outcomes** — success is announced · a server error is announced and the values are kept

**Cross-field** — a field can validate against the other values

## 17 — Techniques

The reusable primitives. Every component in §03–16 is an assembly of these.

### A. ROVING TABINDEX

**Problem.** A composite widget (tablist, toolbar, tree, radio group) contains many focusable
children. If each is a tab stop, a keyboard user must press Tab eleven times to get past your
toolbar. The widget should be **one** tab stop, with arrow keys navigating inside it.

**Derivation.** Exactly one child has `tabIndex={0}`; every other child has `tabIndex={-1}`.
Both halves are load-bearing:

- `0` on the active child → the widget appears once in the tab order.
- `-1` on the rest → they leave the tab order **but stay programmatically focusable**, which
  is what lets your arrow handler call `.focus()` on them.

Writing `tabIndex={selected ? 0 : undefined}` breaks it: an element with no `tabindex` cannot
be focused by script, so the arrow keys do nothing.

```tsx
const refs = useRef<(HTMLButtonElement | null)[]>([])

<button
  ref={(el) => { refs.current[i] = el }}   // block body! see §17 J
  tabIndex={isActive ? 0 : -1}
  onKeyDown={handleKeyDown}
/>

function move(next: number) {
  setActive(items[next].value)
  refs.current[next]?.focus()   // moving the 0 and moving focus must happen together
}
```

**Where it applies:** Tabs (§03), Menu (§07), Tree (§10), Carousel (§15), toolbars, radio groups.

**Where it does NOT:** Accordion (§04) — those headers are independent buttons and a keyboard
user expects Tab to walk them. And Combobox (§06), which uses a virtual cursor instead so the
user can keep typing.

**Say this:** *"The tablist is one tab stop. Arrows move both focus and the zero together."*

### B. FOCUS TRAP AND RESTORE

Four movements, in order. Miss any one and the widget is unusable by keyboard.

**1. Remember.** Capture `document.activeElement` before you move anything.

**2. Move in.** On open, focus the first focusable element inside — or an explicitly named one.
For a destructive confirmation, never the destructive button.

**3. Contain.** Intercept Tab only at the two edges. Let the browser handle everything in
between; reimplementing full tab order is how you break screen-reader navigation modes.

```tsx
if (event.key !== 'Tab') return
const items = focusableWithin(container)
const first = items[0]
const last = items[items.length - 1]

if (event.shiftKey && document.activeElement === first) {
  event.preventDefault(); last.focus()
} else if (!event.shiftKey && document.activeElement === last) {
  event.preventDefault(); first.focus()
}
```

**4. Restore — and handle the trigger being gone.**

```tsx
return () => {
  if (previouslyFocused?.isConnected) previouslyFocused.focus()
  else returnFocus?.current?.focus()
}
```

This is the part almost everyone misses. A dialog that deletes a row destroys the button that
opened it. `.focus()` on a detached node does not throw — it silently does nothing, and focus
falls to `<body>`, dumping a keyboard user at the top of the page. Because the failure is
silent, `isConnected` isn't defensive decoration: it's the only way to know restore failed and
route focus somewhere deliberate.

**Finding focusables — and what to actually do in an interview.**

You are not expected to reproduce a complete focusable-element selector from memory. Nobody
can, and an interviewer who wanted one would be testing recall, not engineering. There are
three honest answers, in descending order of what they'll like:

**1. Don't hand-roll it.** Say this first:

> *"In production I'd reach for native `<dialog>` with `showModal()` — the browser handles
> focus containment, the top layer, and Escape for free. Failing that, `focus-trap` or
> `tabbable`, because the full focusable-element set is a genuinely long tail."*

That answer is short, correct, and shows you know the problem is deeper than it looks.

**2. If they want the mechanics, write the short version and say what it misses:**

```tsx
const focusable = [...container.querySelectorAll<HTMLElement>(
  'a[href], button, input, select, textarea, [tabindex]',
)].filter((el) => !el.hasAttribute('disabled') && el.tabIndex !== -1)
```

Six words of selector and one filter. Then name the gaps out loud — `[hidden]` subtrees,
`contenteditable`, elements inside a closed `<details>`, `<audio controls>`. Naming a limitation
scores; pretending it isn't there does not.

**3. The exhaustive version** is in `uie-practice/src/exercises/modal-reference/`. Read it once
to know what the long tail *is*; don't try to memorize it.

**The one detail worth actually remembering**, because it's a bug rather than a list: filter
out anything inside a `[hidden]` subtree, and do **not** reach for `el.offsetParent !== null`
to do it. That's the tempting one-liner, and `offsetParent` is also `null` for every
`position: fixed` element — so a fixed toolbar inside your dialog silently drops out of the
trap. Use `!el.closest('[hidden]')` instead.

### C. CONTROLLED / UNCONTROLLED DUAL API

The single highest-leverage six lines in this document.

```tsx
function Widget({ value: valueProp, defaultValue, onValueChange }) {
  const [internal, setInternal] = useState(defaultValue ?? FALLBACK)
  const isControlled = valueProp !== undefined
  const value = isControlled ? valueProp : internal

  const commit = (next) => {
    if (!isControlled) setInternal(next)   // controlled: the parent is the only writer
    onValueChange?.(next)                  // both modes: always report
  }
}
```

**Why `!== undefined` and not truthiness.** `value={null}`, `value={0}`, and `value={''}` are
all legitimate controlled values. Only `undefined` means "not controlled."

**Why the internal state still exists in controlled mode.** It's simply never read. Trying to
avoid it requires a conditional hook, which is illegal.

**Why always call `onValueChange`.** An uncontrolled component that stays silent can't be
observed at all — no analytics, no dependent UI, no "unsaved changes" prompt.

**Never** mirror `valueProp` into state with an effect. That's a render-then-correct cycle
that flashes the wrong value, and it desynchronizes the moment the parent updates.

### D. COMPOUND COMPONENTS AND CONTEXT

Two shapes, and knowing when to pick which is the graded part.

**Data-driven** (used throughout this guide):
```tsx
<Tabs items={[{ value, label, panel }]} />
```
Wins on: less code, no context, impossible to mis-nest, trivially testable. Right answer under
a 40-minute clock.

**Compound**:
```tsx
<Tabs><TabList><Tab value="a">A</Tab></TabList><TabPanel value="a">…</TabPanel></Tabs>
```
Wins on: arbitrary markup between children, per-item props, consumer-controlled layout. This is
what Radix and Headless UI ship, because a library can't know your markup.

If you build compound, the context must be memoized or every child re-renders on every keystroke:

```tsx
const value = useMemo(() => ({ selected, select }), [selected, select])
```

And `select` must itself be stable (`useCallback`), or the memo is worthless. A context whose
value is a fresh object literal every render is a render storm with extra steps.

**Say this:** *"I'd go data-driven for the interview — it's less code and can't be mis-nested.
A library ships compound because it can't dictate your markup."*

### E. LIVE REGIONS

**The rule that matters: the region must already be in the DOM before the message goes into it.**

Screen readers observe an existing `aria-live` container for mutations. Mount the container and
its text in the same commit and there is no mutation to observe — your toast is visible and
completely silent. So live regions are mounted for the life of the app and sit empty.

```tsx
<div aria-live="polite" />       {/* always mounted, usually empty */}
<div aria-live="assertive" />
```

| | `polite` / `role="status"` | `assertive` / `role="alert"` |
|---|---|---|
| Timing | Waits for a pause in speech | Interrupts mid-word |
| Use for | Saved, 3 results, copied | Errors that block, session expiring |
| Cost of misuse | Missed | Users learn to tune you out |

Two regions, not one: a container has a single `aria-live` value, so putting an error in the
polite region means it waits behind whatever is being read.

`aria-atomic="false"` (the default) announces only what was added. `true` re-reads the entire
region on every change — right for a single status line, wrong for a stack.

**Don't** move focus to announce something. Focus movement is for navigation; live regions are
for information. Stealing focus for a "Saved" message is hostile.

### F. RACE GUARDS: ABORT + GENERATION

Two mechanisms, and they are **not** redundant.

```tsx
const generationRef = useRef(0)

useEffect(() => {
  const controller = new AbortController()
  const generation = ++generationRef.current

  const timer = setTimeout(() => {
    fetchOptions(query, controller.signal)
      .then((next) => {
        if (generation !== generationRef.current) return   // stale — drop it
        setOptions(next)
      })
      .catch(() => {
        if (controller.signal.aborted) return              // we cancelled it
        if (generation !== generationRef.current) return
        setStatus('error')
      })
  }, debounceMs)

  return () => { clearTimeout(timer); controller.abort() }
}, [query, debounceMs, fetchOptions])
```

**`AbortController`** stops the network. It saves bandwidth and server load, and it's what you
should reach for first.

**The generation counter** is what actually makes stale responses lose. Abort does not un-queue
a `.then` that already resolved; and plenty of sources ignore the signal entirely — a cache hit,
a shared in-flight map, a mock in your own tests. The counter is source-agnostic: only the
newest request is allowed to write state.

**How to demo the bug.** Make *shorter* queries slower. Type "re", keep typing, and the early
request lands last, overwriting good results with stale ones. With equal latencies the race
is invisible and you'll ship it.

**The cleanup runs on every keystroke**, cancelling both the pending debounce and the in-flight
request. Without it, a fast typist opens one socket per character.

### G. INTERSECTION OBSERVER SENTINELS

For infinite scroll, an empty sentinel element after the list beats scroll math.

```tsx
useEffect(() => {
  const el = sentinelRef.current
  if (!el || !hasMore) return

  const observer = new IntersectionObserver(
    ([entry]) => { if (entry.isIntersecting) loadMore() },
    { rootMargin: '200px' },   // start fetching before it's actually visible
  )
  observer.observe(el)
  return () => observer.disconnect()
}, [hasMore, loadMore])
```

**Why not a scroll listener.** Scroll fires at frame rate and forces you to read
`scrollHeight`/`scrollTop`, which triggers layout on every event. IntersectionObserver is
computed off the main thread and fires only on threshold crossings.

**`rootMargin`** is the whole UX difference: `'200px'` starts the fetch before the user reaches
the bottom, so content is there when they arrive.

**The trap:** `loadMore` must be stable, or the effect tears down and re-observes on every
render — which re-fires `isIntersecting` and requests the same page repeatedly. `useCallback`
it, and guard with an `isLoading` flag.

**Always provide a manual "Load more" button too.** Infinite scroll with no keyboard path is
a hard accessibility failure — there's no way to reach the footer.

### H. WINDOWING MATH

**What this is for.** One component (§13 Virtualized list) and one interview question:
*"how would you render a hundred thousand rows?"* Nothing else in this guide uses it.

**When you actually need it.** When the number of DOM nodes is itself the bottleneck — roughly
low thousands of rows and up. Below that, don't: windowing costs you find-in-page, Ctrl+F,
native scroll-anchoring, and screen-reader browse mode, and buys nothing.

**How it usually comes up.** Far more often as a thing to *name* than a thing to build:
*"past a few thousand rows I'd virtualize — render only the visible window plus a small
overscan, with a spacer preserving scroll height."* One sentence, and you move on. Being asked
to implement it from scratch in 40 minutes is uncommon; being asked how you'd scale a list is
near-universal.

Render only what's on screen. With fixed row heights it's four lines of arithmetic:

```tsx
const total = items.length
const first = Math.floor(scrollTop / rowHeight)
const visible = Math.ceil(viewportHeight / rowHeight)
const start = Math.max(0, first - overscan)
const end = Math.min(total, first + visible + overscan)
```

Three elements:
1. A **scroll container** with fixed height and `overflow-y: auto`.
2. A **spacer** of height `total * rowHeight`, so the scrollbar reflects the real list.
3. The **visible slice**, offset by `start * rowHeight` via `transform: translateY(...)`.

`overscan` (2–5 rows) renders slightly beyond the viewport so fast scrolling doesn't show blank
gaps.

**Variable heights** break all of this — you need measured offsets and a prefix-sum index.
Naming that limit is better than pretending it doesn't exist: *"This assumes fixed row height.
Variable heights need measurement plus a cumulative offset index, which is where I'd reach for
a library."*

**Accessibility cost, and you must name it:** windowing removes rows from the DOM, so find-in-page
and screen-reader browse mode can't see them. Set `aria-rowcount` on the grid and `aria-rowindex`
on each row so assistive tech knows the real size.

### I. PORTALS AND THE TOP LAYER

```tsx
return createPortal(<Dialog />, document.body)
```

**Why.** `position: fixed` positions against the viewport — *unless* an ancestor has a
`transform`, `filter`, `perspective`, `contain`, or `will-change`, any of which makes that
ancestor the containing block. A dialog inside a transformed card is then trapped inside the
card. `overflow: hidden` on an ancestor clips it, and `z-index` can't escape a parent stacking
context. Portalling to `<body>` sidesteps all three.

**What a portal does NOT change:** React events still bubble through the React tree, not the DOM
tree. A click inside a portalled dialog fires the `onClick` of its React parent. Usually
convenient; occasionally very surprising.

**Native `<dialog>`** with `showModal()` gets you the browser's top layer, a real backdrop, and
free Escape handling — no z-index fight at all. Worth naming as the production choice; the
manual version above is what you build when asked to show the mechanics.

### J. useId AND SSR-SAFE IDS

```tsx
const baseId = useId()
const tabId = (v: string) => `${baseId}-tab-${v}`
const panelId = (v: string) => `${baseId}-panel-${v}`
```

**Why not `Math.random()` or a module counter:** server and client generate different values,
hydration mismatches, React blows away the markup.

**Why not a hardcoded prefix:** two instances on one page collide, and every `aria-controls`
resolves to the wrong element — a bug that only appears in the demo the interviewer opens.

**Format note:** React 18 returned `:r0:`, which is not a valid CSS identifier, so
`querySelector('#' + id)` throws — `getElementById` was the only safe lookup. React 19 returns
`_r_0_`, which is selector-safe. Know the difference; don't rely on it.

**The mistake to avoid:** spending `useId` on `key`. `key` is a reconciliation hint that never
reaches the DOM, so the ids produce no accessibility benefit at all. `key={item.value}`;
`id={tabId(item.value)}`.

**Ref callbacks, since they always appear alongside:**

```tsx
ref={(el) => { refs.current[i] = el }}     // block body
ref={(el) => (refs.current[i] = el)}       // BROKEN in React 19
```

React 19 treats a ref callback's return value as a cleanup function. The expression body
returns the element, and TypeScript rejects it outright:

```
Type '(el: HTMLButtonElement | null) => HTMLButtonElement | null'
  is not assignable to type 'Ref<HTMLButtonElement>'.
```

### K. DEBOUNCE AND THROTTLE IN REACT

**Debounce** — wait for quiet. Search-as-you-type, autosave, resize-settle.
**Throttle** — at most once per interval. Scroll position, drag, progress.

In React, the cleanest debounce is an effect, not a utility:

```tsx
useEffect(() => {
  const timer = setTimeout(() => setDebounced(query), 300)
  return () => clearTimeout(timer)
}, [query])
```

The cleanup *is* the debounce: every new keystroke cancels the pending timer. No lodash, no ref
juggling, and it cleans up correctly on unmount for free.

**Debounce the value, not the callback.** Both approaches work; the value one has fewer ways to
go wrong. The callback version looks like this, and it is what most people reach for first:

```tsx
// Works — but only if every condition below holds.
const debouncedSearch = useMemo(() => debounce(onSearch, 300), [onSearch])
```

Two failure modes, and neither announces itself:

1. **`onSearch` must be referentially stable.** An inline arrow in the parent — `onSearch={(q) =>
   setQuery(q)}` — is a new function every render, so `useMemo` rebuilds, so you get a *fresh
   debounced function with its own empty timer* on every render. Nothing is ever debounced, and
   it looks fine in dev because you don't type fast enough to notice.
2. **Nothing cancels the pending call on unmount.** The timer fires after the component is
   gone, running a callback that closes over dead state.

The effect version has neither problem structurally: there's no function identity to preserve,
and `clearTimeout` in the cleanup handles both the next keystroke *and* unmount with the same
line. So:

```tsx
const [query, setQuery] = useState('')
const [debouncedQuery, setDebouncedQuery] = useState('')

useEffect(() => {
  const timer = setTimeout(() => setDebouncedQuery(query), 300)
  return () => clearTimeout(timer)
}, [query])

// then depend on debouncedQuery, not query
useEffect(() => { /* fetch */ }, [debouncedQuery])
```

Note that §17 F folds these two effects into one — the debounce timer and the fetch live
together, so a keystroke cancels both the pending timer and the in-flight request in a single
cleanup. That's the version to write when the debounced value's only consumer is the fetch.
Keep them separate when several things depend on the debounced value.

**Testing:** with `vi.useFakeTimers()`, note that `userEvent` v14 awaits its own internal
`setTimeout` between events — under fake timers that await never resolves and the test hangs at
the timeout. Use `fireEvent` for timer-based tests, and wrap advances in `act()`:

```tsx
await act(async () => { vi.advanceTimersByTime(1000) })
```

### L. REDUCERS AS EXPLICIT STATE MACHINES

Reach for `useReducer` when transitions carry invariants — not merely when there are several
fields.

The signal: you're writing `if (isLoading && !isError && data)`. Those booleans encode a state
machine badly, and they permit impossible combinations (`isLoading && isError`).

```tsx
type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; data: Item[] }
  | { status: 'error'; message: string }
```

A discriminated union makes impossible states unrepresentable, and TypeScript then forces you
to handle every branch at the point of use.

```tsx
function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH':   return { status: 'loading' }
    case 'RESOLVE': return { status: 'ready', data: action.data }
    case 'REJECT':  return { status: 'error', message: action.message }
    case 'RETRY':   return state.status === 'error' ? { status: 'loading' } : state
  }
}
```

That last case is the reason to bother: **the reducer is where you enforce which transitions are
legal.** "Retry only from error" lives in one readable place instead of being scattered across
handlers.

**Bonus for the round:** a reducer is a pure function, so it's testable without rendering
anything — `expect(reducer({status:'idle'}, {type:'RESOLVE'})).toEqual(...)`. Naming that is a
cheap point on the test-quality axis.
