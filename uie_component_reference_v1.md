# UIE Component Reference

> Companion to `react_css_frontend_interview_field_guide_v3`. That guide is for *recall* —
> terse bullets you scan before a mock. This one is for *understanding*: complete, working
> implementations with the reasoning spelled out line by line.

Fourteen components you will actually be asked to build, each with the API, the ARIA and
keyboard contract, the full implementation, the traps, and the test plan. Then the fifteen
underlying techniques, derived from scratch, plus two that are not about the DOM at all
(§17 N–O) because the component round has started handing out modules.

Every implementation here is real, runnable, and test-covered. They live in the practice app
at `uie-practice/src/exercises/<name>-reference/`, and each ships a spec suite you can point
at your own from-scratch build. Two exceptions: the command palette (§12) has no
`-reference` exercise — its three runnables are the §H cut, the native `<dialog>` variant, and the
drill it came from — and the virtualized list (§13) has no exercise on disk at all yet.

## 01 — How to use this guide

### A. THE LOOP

Reading this front to back teaches you almost nothing. The loop that works:

1. Pick a component. **Derive its API and ARIA contract yourself**, using the six tests in
   §02 B, before opening anything. Write them down.
2. Read **§B (API)** and **§C (ARIA + keyboard contract)** and mark where you differed. Those
   marks are the whole lesson — they are the gaps in your method, not in your memory.
3. Build it cold, from an empty file, on a clock. Say the prop signature out loud before you
   write the body — that narration is what's actually being graded.
4. Run the reference spec against your build:
   `npx vitest run src/exercises/<name>-reference`
5. Only once you're green, read **§E (implementation)** and diff it against yours.
6. Read **§F (traps)** last. If you hit one on your own, you'll never forget it.

Step 5 before step 3 is passive rereading, and passive rereading is not preparation.

Step 1 is the one people skip, and skipping it is what turns this guide into a memorisation
exercise. A component you can only build after reading its section is a component you have
memorised. The interview will not be one of these twelve.

### B. TWO SIZES OF EVERY COMPONENT

Every §E implementation is a **reference**: what the component should be when nobody is holding a
stopwatch. Several are larger than anything you would type in a timed round, and that is
deliberate — you cannot decide what to leave out of something you have never seen whole.

**§H (INTERVIEW SCOPE)** is the other half. For each component it gives the line budget, what is
genuinely core, and what to drop — with the sentence to say when you drop it. Five components have
a complete pared implementation there, because their references are the ones that genuinely
overrun a round:

| Component | Reference | Interview cut | Runnable |
|---|---:|---:|---|
| Combobox | 208 | **117** | `combobox-interview` |
| Command palette | 201 | **132** | `command-palette-interview` |
| Data table | 193 | **111** | `data-table-interview` |
| Menu | 178 | **125** | `menu-interview` |
| Tree | 154 | **131** | `tree-interview` |

Every other component is already between 62 and 113 lines, which is a round's worth of typing. For
those, §H lists what to cut without a separate implementation.

Line counts are the component only — no demo, comments, imports, or `meta` export. The files on
disk look larger because they carry the teaching apparatus this guide is built from.

**Naming a cut scores better than making it silently.** *"I've left the live region out — screen
reader users need the result count spoken, it's about four lines and I'd add it next"* demonstrates
the same knowledge as writing it, and costs eight seconds instead of four minutes. That is the
skill §H is trying to build.

### C. WHAT IS ACTUALLY GRADED

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

### D. THE TEN-MINUTE VERSION

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
| **H. Interview scope** | The line budget, what's core, and what to cut with the sentence for each |

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

### B. HOW TO DECIDE — the tests behind those five

§A tells you which questions to ask. This tells you how to answer them for a component you have
never seen, which is the only version of the skill that survives contact with a real round.

If you find yourself reaching for what a component in this guide did, you are recalling rather
than deriving, and it will fail the moment the prompt is a chip multi-select instead of a
combobox. Each test below is a question about the widget in front of you. None of them require
knowing what any other widget did.

**1. Does interacting leave state behind?**

| Answer | It is | Which gives you |
|---|---|---|
| One item is now "the chosen one" | a selection widget | `aria-selected`, and a `value` |
| It fires and is gone | a command widget | `menuitem`, no selection state, no `value` |
| It shows or hides adjacent content | a disclosure | `aria-expanded` + `aria-controls` |

This is what separates a menu from a listbox, and an accordion from tabs. You never have to
remember that menus don't take `aria-selected` — there is nothing for a selection to persist as.

**2. Is there exactly one "current" item?**

This decides the focus model, which is the highest-consequence choice in the component.

| Answer | Focus model |
|---|---|
| Something else must stay usable while navigating (a text input being typed into) | Focus stays put, a virtual cursor moves — `aria-activedescendant` |
| Exactly one item is current | Roving tabindex; the container is one tab stop |
| There is no such thing as "the current one" | Every item is its own tab stop |

An accordion lands in the third row because several panels can be open at once, so no header is
"the current" one. Tabs lands in the second because exactly one tab is selected. Apply the test
per region, not per component: a widget can have a virtual cursor in one part and roving tabindex
in another.

**3. For each piece of state, can I compute it instead?**

Ask before every `useState`. If a value is a function of other state, deriving it at render is
not a style preference — storing it means storing something that can disagree with its own
inputs, which is the bug.

Then two follow-ups: *would a parent ever need to read or set this?* → dual API (§17 C).
*Is it transient typing state?* → keep it internal, whatever else you expose.

**4. What can arrive late, repeat, or outlive the component?**

For anything async or timed, in this order:

- Two in flight at once → generation counter (§17 F)
- Fired many times a second → debounce (§17 K)
- Unmounted mid-flight → cleanup, and abort

**5. The keyboard falls out of question 2.**

There is no key table to memorize. Given the focus model:

| Focus model | Keys |
|---|---|
| Roving tabindex | Arrows move focus, Home/End, one tab stop, `preventDefault` on everything you handle |
| Virtual cursor | Arrows move the cursor, focus never moves, Enter commits, Escape dismisses |
| All tab stops | Tab does the work; arrow keys are optional |

**6. What changes without the user causing it?**

That is your live region, and only that. Anything the user just did, they already know about.

**Worked example — a multi-select with removable chips.**

Nothing in this guide implements one. The six questions still produce it.

1. **State behind?** Yes, and more than one at a time — a selection widget. Options take
   `aria-selected`; the listbox takes `aria-multiselectable="true"`.
2. **One current item?** Two regions, two answers. The text input must stay usable while you
   arrow the suggestions, so the list gets a **virtual cursor**. The chips are a separate
   navigable set with one current chip, so they get **roving tabindex** — one Tab stop for the
   whole chip row, arrows between them.
3. **Derivable state?** `query` (transient, internal). `selected` (a parent will want it → dual
   API). Derived, not stored: the visible options are `results` minus anything already chosen,
   and list visibility is a function of focus, query length, and status.
4. **Late or repeated?** Identical to any typeahead: debounce the query, generation-guard the
   response, abort on change, swallow the `AbortError`.
5. **Keyboard?** Falls out of 2. In the input: arrows move the cursor, Enter adds a chip,
   Escape dismisses. On the chips: arrows move focus, Delete/Backspace removes and focus moves
   to the neighbour. Plus one the tests don't give you, which you get by asking what the natural
   undo is — **Backspace in an empty input removes the last chip.**
6. **Announce?** The result count, and each chip added or removed — the chip row changes as a
   consequence of a keystroke somewhere else, so it will not be read otherwise.

That is the whole design, derived, before writing a line. Note that question 5 produced a
behaviour no amount of recall would have: nothing else in this guide has a Backspace rule.

**How to practise this.**

Reps on the components in this guide measure your memory of them. To measure the method, build
things that are **not** here: a rating widget, a segmented control, a chip multi-select, a split
button, a pagination bar, a toolbar, a date picker.

For each, write the API and the ARIA contract from the six questions **before** any code, then
check yourself against APG. Being wrong is the point — it is information you cannot get from a
component whose answer you already know.

### C. API CONVENTIONS USED THROUGHOUT

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

### D. THE ARIA WIRING RULE

Two rules that would have caught most accessibility bugs you'll ever write:

1. **Every `aria-controls` / `aria-labelledby` gets a matching `id` in the same JSX block,
   written in the same keystroke.** A dangling reference is worse than no attribute — it's a
   promise the DOM doesn't keep.
2. **Ids derive from the stable `value`, never from the label or content.** Two components
   cross-reference each other only if both compute ids from the same key.

And always `useId()` for the base. Hardcoded id prefixes collide the moment two instances
share a page, which is exactly what happens in the demo the interviewer opens.

### E. STYLE OFF ARIA, NOT OFF A PARALLEL CLASS

```css
.tab[aria-selected='true']       { /* ... */ }
.trigger[aria-expanded='true']   { /* ... */ }
.option[aria-selected='true']    { /* ... */ }
```

The accessibility attribute and the visual state then cannot drift apart, and you write one
thing instead of two. Worth saying out loud — it reads as someone who has maintained a design
system rather than memorized a pattern.

### F. THE TEST PLAN TO NAME

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
4. **All panels stay mounted, `hidden` toggles.** State inside an inactive panel survives being
   switched away from — scroll position, uncontrolled inputs, a playing video — instead of
   unmounting. It does *not* buy find-in-page: `hidden` computes to `display: none`, which search
   skips. `hidden="until-found"` is the attribute that makes closed content findable, and it
   reveals the panel on a match; Chromium-only for now, so treat it as an enhancement.

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

### H. INTERVIEW SCOPE

**Reference: 109 lines of code — already a round's worth of typing.** Nothing to cut; the
collapsible at the end of this section is the target, unchanged.

**Core, and none of it is optional:**

- `role="tab"` / `role="tablist"` / `role="tabpanel"`, `aria-selected`, `aria-controls`, `aria-labelledby`
- Roving tabindex: the whole list is one tab stop
- Arrow keys with wrapping, plus `preventDefault`
- Automatic activation — arrows move selection, not just focus
- `hidden` on unselected panels rather than conditional rendering

**Cut only if the clock beats you:**

| Drop | Say |
|---|---|
| `orientation` prop | "Vertical tabs swap to Up/Down and set `aria-orientation`." |
| Controlled/uncontrolled dual API | "`value`/`defaultValue`/`onValueChange` for a library component. The URL-sync follow-up needs it." |
| Home / End | "APG lists them; two lines each." |

Expect the controlled-mode follow-up — "make the selected tab shareable by URL" — so know the
four-line dual-API shape cold even if you don't write it up front.

<details>
<summary>The interview target — Tabs (identical to the reference above)</summary>

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
- **`hidden` rather than `{isOpen && <div>}`.** The panel stays in the DOM, so component state
  inside it survives a collapse — scroll position, uncontrolled input values, a playing video —
  instead of being torn down and remounted. Two costs worth knowing: `[hidden]` is a
  low-specificity UA rule, so a stray `display` declaration in your CSS defeats it silently; and
  `hidden` computes to `display: none`, which browser find-in-page skips. If you want closed
  panels to be findable, that is `hidden="until-found"` — it reveals the panel and fires
  `beforematch` when a search hits inside it. Baseline in Chromium since 102, still landing
  elsewhere, so treat it as an enhancement rather than the default.
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

### H. INTERVIEW SCOPE

**Reference: 98 lines of code** — the smallest of the widget patterns. Nothing to cut; the
collapsible at the end of this section is the target, unchanged.

**Core:**

- `aria-expanded` on the header button — *not* `aria-selected`, which isn't valid on `button`
- `aria-controls` pointing at a panel that exists
- Every header its own tab stop — **no** roving tabindex, the opposite of Tabs
- A heading element wrapping each button
- `hidden` panels

**Cut freely:**

| Drop | Say |
|---|---|
| Arrow-key navigation between headers | "APG makes it optional for accordions, unlike tabs where it's required." |
| `allowMultiple` / `collapsible` | "One flag each; the four-branch toggle covers every combination." |
| Controlled API | "Same dual-API shape as tabs." |

The arrow keys being *optional* here is worth saying out loud — it shows you know the patterns
differ rather than applying one keyboard model to everything.

<details>
<summary>The interview target — Accordion (identical to the reference above)</summary>

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
| Escape on a document listener | Two open dialogs both close — unless a layer stack picks the innermost (§17 M) |

### G. SPEC

**Structure** — renders nothing while closed · is a named modal dialog whose name comes from a
real heading · portals out of the React container to `<body>`

**Focus** — moves to the first focusable on open · `initialFocus` overrides · Tab wraps last→first
· Shift+Tab wraps first→last · returns to the trigger on close · falls back to `returnFocus` when
the trigger unmounted

**Dismissal** — Escape closes · a click starting and ending on the backdrop closes · a drag
starting inside and ending on the backdrop does **not** · `closeOnBackdrop={false}` ignores it

**Scroll lock** — locks the body while open and restores the previous value

### H. INTERVIEW SCOPE

**Reference: 107 lines of code**, and the trap is where the time goes, not the markup.

**Core:**

- `role="dialog"`, `aria-modal="true"`, an accessible name from the title
- Portal to `document.body`
- Focus into the dialog on open, back to the trigger on close
- Escape closes; backdrop click closes but a click *inside* does not
- Focus trap wrapping Tab and Shift+Tab at the edges

**Cut, and say so:**

| Drop | Say |
|---|---|
| The exhaustive `FOCUSABLE` selector | "Four or five entries covers it. The tail — `details > summary`, `contenteditable`, media with controls — is why production uses `focus-trap` or Radix." |
| `isConnected` / `returnFocus` fallback | "If the trigger unmounted while the dialog was open, `.focus()` is a silent no-op and the user lands on `<body>`." |
| The pointerdown-and-click backdrop check | "Otherwise selecting text inside and releasing outside closes the dialog." |
| `inert` on the background | "`inert` is the modern answer and cheaper than a trap — it just doesn't wrap." |

If you're out of time, ship **focus restore** over the trap. It's four lines, and an untrapped
dialog is a smaller failure than one that strands the user on `<body>` after every close.

<details>
<summary>The interview target — Modal (identical to the reference above)</summary>

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

## 06 — Combobox / Typeahead

> Runnable: `uie-practice/src/exercises/combobox-reference/` · Spec: 16 tests  
> Interview cut (§H): `uie-practice/src/exercises/combobox-interview/` · Spec: 9 tests

### A. ASKED AS

- "Build an autocomplete / typeahead / search-as-you-type"
- "Build a country picker with search"
- "Build a @-mention input" — same machinery, different trigger
- "Build a ⌘K command palette" — this machinery inside a dialog (§12)

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

### H. INTERVIEW SCOPE

**Reference: 208 lines of code — the largest in the set, and too big for a timed round.**
The cut below is 117 and keeps everything that gets graded.

**Core:**

- Debounce, so a burst of keystrokes is one request
- **Both** race guards — the generation counter is what makes stale responses lose; `AbortController`
  saves the socket but cannot un-queue a resolved `.then`
- `aria-activedescendant` with real focus never leaving the input
- APG 1.2 markup: `role="combobox"` on the input itself, not a wrapper
- Arrows with wrapping, Enter to select, Escape to dismiss
- `onMouseDown` not `onClick` on options — blur closes the list before a click would land

**Cut, and say so:**

| Drop | Say |
|---|---|
| `aria-live` result count | "Sighted users see the list appear; screen reader users need the count spoken. Four lines — the one I'd add back first." |
| Controlled/uncontrolled API | "For a library component." |
| `minChars` | "One-line guard against firing on a stray keystroke." |
| Home / End | "APG lists them; lowest value of the keys." |
| `scrollIntoView` on the active option | "Needed once the list can overflow." |
| Distinct error state | "Right now a failure looks like an empty result set." |

<details>
<summary>The interview cut — Combobox</summary>

```tsx
import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

/**
 * THE INTERVIEW CUT of combobox-reference: 208 lines of code down to 117.
 *
 * Everything load-bearing is still here — debounce, both race guards,
 * aria-activedescendant, the listbox markup, arrow/enter/escape. What went is
 * listed at the bottom of this file, with the sentence to say for each. Naming
 * what you cut is worth more than silently shipping less.
 */

export interface Option {
  value: string
  label: string
}

interface ComboboxProps {
  label: string
  fetchOptions: (query: string, signal: AbortSignal) => Promise<Option[]>
  onSelect?: (option: Option) => void
}

export function Combobox({ label, fetchOptions, onSelect }: ComboboxProps) {
  const baseId = useId()
  const optionId = (i: number) => `${baseId}-option-${i}`

  const [query, setQuery] = useState('')
  const [rawOptions, setOptions] = useState<Option[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const generationRef = useRef(0)

  // Derived, not reset from inside the effect. Clearing state synchronously in an
  // effect body is a cascading render, and React's lint rule rejects it.
  const q = query.trim()
  const options = q ? rawOptions : []

  useEffect(() => {
    if (!q) return

    const controller = new AbortController()
    // Only the newest request may write state. AbortController stops the
    // network but cannot un-queue a `.then` that already resolved — this is
    // what actually makes stale responses lose.
    const generation = ++generationRef.current

    const timer = setTimeout(() => {
      setLoading(true)
      fetchOptions(q, controller.signal)
        .then((next) => {
          if (generation !== generationRef.current) return
          setOptions(next)
          setActiveIndex(next.length > 0 ? 0 : -1)
          setLoading(false)
        })
        .catch(() => {
          if (generation !== generationRef.current) return
          setLoading(false)
        })
    }, 200)

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [q, fetchOptions])

  function select(option: Option) {
    setQuery(option.label)
    setOpen(false)
    onSelect?.(option)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open || options.length === 0) return
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        setActiveIndex((i) => (i + 1) % options.length)
        break
      case 'ArrowUp':
        event.preventDefault()
        setActiveIndex((i) => (i - 1 + options.length) % options.length)
        break
      case 'Enter':
        if (activeIndex < 0) return
        event.preventDefault()
        select(options[activeIndex])
        break
      case 'Escape':
        setOpen(false)
        break
      default:
        break
    }
  }

  const showList = open && (loading || options.length > 0)

  return (
    <div className="cbi">
      <label className="cbi-label" htmlFor={`${baseId}-input`}>
        {label}
      </label>
      <input
        id={`${baseId}-input`}
        className="cbi-input"
        type="text"
        role="combobox"
        autoComplete="off"
        aria-expanded={showList}
        aria-controls={`${baseId}-listbox`}
        aria-autocomplete="list"
        // The virtual cursor: real focus stays in the input so typing keeps working.
        aria-activedescendant={showList && activeIndex >= 0 ? optionId(activeIndex) : undefined}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setActiveIndex(-1)
        }}
        onKeyDown={handleKeyDown}
        onBlur={() => setOpen(false)}
      />

      <ul id={`${baseId}-listbox`} role="listbox" aria-label={label} hidden={!showList} className="cbi-list">
        {options.map((option, i) => (
          <li
            key={option.value}
            id={optionId(i)}
            role="option"
            aria-selected={i === activeIndex}
            className="cbi-option"
            // mousedown, not click: blur closes the list before click would fire.
            onMouseDown={(e) => {
              e.preventDefault()
              select(option)
            }}
            onMouseEnter={() => setActiveIndex(i)}
          >
            {option.label}
          </li>
        ))}
      </ul>
      {showList && loading && <p className="cbi-msg">Loading…</p>}
    </div>
  )
}

/* ------------------------------------------------------------------ cut ----
 * Dropped from the reference, and what to say if asked:
 *
 * - Controlled/uncontrolled dual API   "I'd add value/defaultValue/onValueChange
 *                                       if this were a library component."
 * - minChars                           "One-line guard; I'd add it to avoid
 *                                       firing on a single stray keystroke."
 * - Home / End                         "APG lists them; lower value than the
 *                                       arrows and I'd add them last."
 * - scrollIntoView on the active option "Needed once the list can overflow."
 * - aria-live result-count announcement "Sighted users see the list appear;
 *                                       screen reader users need the count
 *                                       spoken. Real gap, and it's four lines."
 * - Distinct error state               "Right now a failure looks like no
 *                                       results. I'd split those."
 * - Tab closing the list               "Tab should leave without selecting."
 *
 * Of those, the live region is the one I'd actually spend time on if the
 * interviewer signals accessibility matters.
 * -------------------------------------------------------------------------- */

/* ----------------------------------------------------------------- demo ---- */

const PACKAGES = ['react', 'react-dom', 'redux', 'vite', 'vitest', 'typescript', 'eslint']

export default function ComboboxInterview() {
  const [picked, setPicked] = useState<Option | null>(null)

  return (
    <div className="cbi-demo">
      <p className="cbi-note">
        The same widget as <code>combobox-reference</code>, scoped to what fits in a timed round —
        117 lines of code instead of 208. Everything that would actually be graded is still here.
      </p>
      <Combobox
        label="Search packages"
        fetchOptions={async (query) => {
          await new Promise((r) => setTimeout(r, 180))
          return PACKAGES.filter((p) => p.includes(query.toLowerCase())).map((p) => ({
            value: p,
            label: p,
          }))
        }}
        onSelect={setPicked}
      />
      <p className="cbi-picked">
        Selected: <code>{picked ? picked.label : 'nothing'}</code>
      </p>
    </div>
  )
}
```

</details>

## 07 — Dropdown Menu

> Runnable: `uie-practice/src/exercises/menu-reference/` · Spec: 19 tests  
> Interview cut (§H): `uie-practice/src/exercises/menu-interview/` · Spec: 12 tests

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

### H. INTERVIEW SCOPE

**Reference: 178 lines of code.** The cut below is 125.

**Core:**

- `aria-haspopup="menu"` and `aria-expanded` on the trigger
- `role="menu"` / `role="menuitem"`, and **no** `aria-selected` — a menu invokes a command, it
  doesn't hold a value. That distinction is the thing being tested.
- Real DOM focus moved into the menu (the opposite of Combobox, which has an input to protect)
- Enter / Space / ArrowDown open onto the first item; ArrowUp opens onto the last
- Escape and selection return focus to the trigger; Tab and outside-click do not
- Outside click on `pointerdown`, not `click`

**Cut, and say so:**

| Drop | Say |
|---|---|
| Disabled items | "`aria-disabled`, not the `disabled` attribute — a disabled button is unfocusable, so it vanishes instead of being announced. Then movement skips those indices." |
| Type-to-jump | "APG asks for it: printable characters accumulate in a 500ms buffer." |
| Controlled open state | "For a library component." |
| Submenus, `menuitemcheckbox` / `menuitemradio` | "Those *do* carry state, unlike a plain menuitem — different pattern." |
| Positioning and collision detection | "floating-ui in production, not hand-rolled." |

Disabled items are the most common follow-up. Know the `aria-disabled` reasoning even if you
don't write it.

<details>
<summary>The interview cut — Menu</summary>

```tsx
import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'

/**
 * THE INTERVIEW CUT of menu-reference: 178 lines of code down to 125.
 *
 * The idea that decides everything: A MENU IS NOT A LISTBOX. You are invoking a
 * command, not choosing a value that persists — so there is no `value` prop and
 * no aria-selected. The only state is open/closed plus which item has focus.
 *
 * And unlike Combobox, that is REAL DOM focus moved into the menu, because there
 * is no text input to protect. Combobox needs a virtual cursor; a menu does not.
 *
 * What went, and the sentence to say, is at the bottom of the file.
 */

export interface MenuItem {
  value: string
  label: ReactNode
}

interface MenuProps {
  label: ReactNode
  items: MenuItem[]
  onSelect: (value: string) => void
}

export function Menu({ label, items, onSelect }: MenuProps) {
  const baseId = useId()
  const menuId = `${baseId}-menu`

  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([])

  function openMenu(focus: 'first' | 'last') {
    setOpen(true)
    setActiveIndex(focus === 'first' ? 0 : items.length - 1)
  }

  function closeMenu(returnFocus: boolean) {
    setOpen(false)
    setActiveIndex(-1)
    // Escape and selection return focus to the trigger; Tab and outside-click do
    // not, because the user has already chosen where to go next.
    if (returnFocus) triggerRef.current?.focus()
  }

  // Real DOM focus follows activeIndex.
  useEffect(() => {
    if (!open || activeIndex < 0) return
    itemRefs.current[activeIndex]?.focus()
  }, [open, activeIndex])

  // Outside click. pointerdown, not click: click fires only on mouseup, so a
  // press-drag-release starting inside the menu would close it.
  useEffect(() => {
    if (!open) return
    function onPointerDown(event: PointerEvent) {
      const target = event.target as Node
      if (menuRef.current?.contains(target) || triggerRef.current?.contains(target)) return
      setOpen(false)
      setActiveIndex(-1)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [open])

  function onTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    switch (event.key) {
      case 'ArrowDown':
      case 'Enter':
      case ' ':
        event.preventDefault()
        openMenu('first')
        break
      case 'ArrowUp':
        // Opening upward lands on the last item — nearest the trigger.
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
        setActiveIndex((i) => (i + 1) % items.length)
        break
      case 'ArrowUp':
        event.preventDefault()
        setActiveIndex((i) => (i - 1 + items.length) % items.length)
        break
      case 'Home':
        event.preventDefault()
        setActiveIndex(0)
        break
      case 'End':
        event.preventDefault()
        setActiveIndex(items.length - 1)
        break
      case 'Escape':
        event.preventDefault()
        closeMenu(true)
        break
      case 'Tab':
        // Let Tab move on, but don't strand an open menu over content behind it.
        closeMenu(false)
        break
      default:
        break
    }
  }

  return (
    <div className="mi">
      <button
        ref={triggerRef}
        type="button"
        className="mi-trigger"
        // "menu" is more specific than "true" — it tells AT what is coming.
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => (open ? closeMenu(false) : openMenu('first'))}
        onKeyDown={onTriggerKeyDown}
      >
        {label}
      </button>

      {open && (
        <div ref={menuRef} id={menuId} role="menu" className="mi-menu" onKeyDown={onMenuKeyDown}>
          {items.map((item, i) => (
            <button
              key={item.value}
              ref={(el) => {
                itemRefs.current[i] = el
              }}
              type="button"
              role="menuitem"
              className="mi-item"
              // Every item is tabIndex -1; focus is moved programmatically, so the
              // menu is a single stop in the page's tab order.
              tabIndex={-1}
              onClick={() => {
                onSelect(item.value)
                closeMenu(true)
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ cut ----
 * Dropped from the reference, and what to say if asked:
 *
 * - Disabled items          "aria-disabled rather than the disabled attribute —
 *                            a disabled button is unfocusable, so it vanishes
 *                            from the menu instead of being announced. Then
 *                            every movement skips those indices."
 * - Type-to-jump            "APG asks for it: printable characters accumulate in
 *                            a 500ms buffer and jump to the first match."
 * - Controlled open state   "open / defaultOpen / onOpenChange if this were a
 *                            library component."
 * - Submenus, checkbox and  "menuitemcheckbox and menuitemradio DO carry state,
 *   radio items              unlike a plain menuitem — different pattern."
 * - Positioning / collision "In production this is floating-ui, not hand-rolled."
 *
 * Disabled-item handling is the one I'd add first — it's the most commonly asked
 * follow-up, and the aria-disabled reasoning is what gets credit.
 * -------------------------------------------------------------------------- */

/* ----------------------------------------------------------------- demo ---- */

const ITEMS: MenuItem[] = [
  { value: 'new', label: 'New file' },
  { value: 'open', label: 'Open…' },
  { value: 'save', label: 'Save' },
  { value: 'export', label: 'Export as PDF' },
]

export default function MenuInterview() {
  const [last, setLast] = useState<string | null>(null)

  return (
    <div className="mi-demo">
      <p className="mi-note">
        Enter, Space or ↓ opens on the first item; ↑ opens on the last. Escape closes and returns
        focus to the trigger. 125 lines of code against the reference’s 178.
      </p>
      <Menu label="File ▾" items={ITEMS} onSelect={setLast} />
      <p className="mi-picked">
        Last command: <code>{last ?? 'none'}</code>
      </p>
    </div>
  )
}
```

</details>

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

### H. INTERVIEW SCOPE

**Reference: 62 lines of code** — the smallest component in the set, and there is genuinely
nothing to cut. The collapsible at the end of this section is the target, unchanged.

**Core:**

- `role="tooltip"` and `aria-describedby` on the trigger, only while open
- Opens on hover **and** on focus; a hover-only tooltip is invisible to keyboard users
- Escape dismisses without moving the pointer
- Handlers on a wrapper, not the trigger, so moving the pointer onto the bubble doesn't close it

Those last three are **WCAG 1.4.13** (Content on Hover or Focus): dismissible, hoverable,
persistent. Naming the criterion is worth more than any amount of extra code here.

The one thing to say out loud: **a tooltip is not a popover.** Tooltips hold a short text
description and nothing interactive. The moment there's a link or a button inside, it's a popover
or a dialog and the whole keyboard contract changes.

<details>
<summary>The interview target — Tooltip (identical to the reference above)</summary>

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

### H. INTERVIEW SCOPE

**Reference: 101 lines of code**, unchanged as the target — the collapsible is at the end of this
section. What makes this one different is that you're
designing an **imperative API**, not a rendered component — `toast('Saved')` from anywhere.

**Core:**

- Context + a `useToast()` hook; the provider owns the queue
- Two live regions that are **permanently mounted** — a region inserted at the same moment as its
  content announces nothing. This is the single most common toast bug.
- `role="status"` (polite) for normal messages, `role="alert"` (assertive) for errors
- Auto-dismiss on a timer, paused on hover and focus

**Cut, and say so:**

| Drop | Say |
|---|---|
| Banking the remaining time across pauses | "Otherwise hovering restarts the full duration each time." |
| Max-visible queueing | "Past three or four, older ones should queue rather than stack." |
| Swipe / drag to dismiss | "Pointer-events work, out of scope here." |
| Exit animations | "Needs the element to outlive its removal from state." |

If asked why the regions are always mounted: screen readers only announce *changes* to a live
region that was already being observed. Mount it and fill it in the same commit and there's
nothing to observe.

<details>
<summary>The interview target — Toast (identical to the reference above)</summary>

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

## 10 — Tree / File explorer

> Runnable: `uie-practice/src/exercises/tree-reference/` · Spec: 17 tests  
> Interview cut (§H): `uie-practice/src/exercises/tree-interview/` · Spec: 10 tests

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

### H. INTERVIEW SCOPE

**Reference: 154 lines of code.** The cut below is 131 — the smallest saving of the four, because
`flatten` genuinely is the answer and there's no honest way to shrink it.

**Core:**

- **Render recursively, navigate linearly.** `flatten` produces the visible rows in order, so
  ArrowDown from a folder's last child reaches the folder's next sibling instead of dead-ending.
- Roving tabindex — exactly one row tabbable, with a fallback so the tree is reachable before
  anything is selected
- Left/right arrows meaning two things each: open/close a folder, or step into/out of one
- `aria-expanded` on folders only; on a leaf it announces a state that can never change
- `role="group"` wrapping children so the nesting is real to assistive tech

**Cut, and say so:**

| Drop | Say |
|---|---|
| `aria-posinset` / `aria-setsize` | "Screen readers announce '2 of 5' from these, and `flatten` already computes them. Cheapest thing on this list." |
| Controlled selection, `defaultExpanded` | "For a library component; `defaultExpanded` is useful for deep-linking." |
| Type-to-jump | "APG asks for it." |
| Multi-select, drag, rename | "Different feature, not the tree pattern." |
| Virtualisation | "Past a few thousand visible rows — and `flatten` already gives you the flat list to window over." |

Write `flatten` first and narrate it. It's the part that separates a working tree from a broken one.

<details>
<summary>The interview cut — Tree</summary>

```tsx
import { useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

/**
 * THE INTERVIEW CUT of tree-reference: 154 lines of code down to 131 — the
 * smallest saving of the four, because `flatten` really is the answer and there
 * is no honest way to shrink it.
 *
 * RENDER RECURSIVELY, NAVIGATE LINEARLY. The markup nests, but the keyboard sees
 * one flat list of visible rows — so ArrowDown from the last child of a folder
 * lands on the folder's next sibling, not on nothing. `flatten` is the whole
 * trick, and it is the part worth being able to write cold.
 *
 * The other half is that left/right arrows mean TWO things depending on where you
 * are: open/close a folder, or step into/out of one.
 *
 * What went, and the sentence to say, is at the bottom of the file.
 */

export interface TreeNode {
  value: string
  label: string
  /** Presence of this array makes a node a folder, even when empty. */
  children?: TreeNode[]
}

interface FlatRow {
  node: TreeNode
  level: number
  parentValue: string | null
  isFolder: boolean
}

/** Depth-first walk of everything currently visible; collapsed subtrees are skipped. */
function flatten(
  nodes: TreeNode[],
  expanded: string[],
  level = 1,
  parentValue: string | null = null,
  out: FlatRow[] = [],
): FlatRow[] {
  for (const node of nodes) {
    const isFolder = Array.isArray(node.children)
    out.push({ node, level, parentValue, isFolder })
    if (isFolder && expanded.includes(node.value)) {
      flatten(node.children!, expanded, level + 1, node.value, out)
    }
  }
  return out
}

interface TreeProps {
  nodes: TreeNode[]
  label: string
  onSelect?: (value: string) => void
}

export function Tree({ nodes, label, onSelect }: TreeProps) {
  const baseId = useId()
  const [selected, setSelected] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string[]>([])
  const rowRefs = useRef(new Map<string, HTMLDivElement | null>())

  const rows = flatten(nodes, expanded)
  // Roving tabindex needs exactly one tabbable row. Falling back to the first
  // keeps the tree reachable before anything is selected.
  const activeValue = rows.some((r) => r.node.value === selected) ? selected : rows[0]?.node.value

  function focusRow(next: string | undefined) {
    if (!next) return
    setSelected(next)
    onSelect?.(next)
    rowRefs.current.get(next)?.focus()
  }

  function setExpandedFor(value: string, open: boolean) {
    setExpanded((prev) => (open ? [...new Set([...prev, value])] : prev.filter((v) => v !== value)))
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
        // Open a closed folder, or step INTO an open one. Nothing on a leaf.
        if (row.isFolder && !isExpanded) setExpandedFor(row.node.value, true)
        else if (row.isFolder && isExpanded) focusRow(rows[index + 1]?.node.value)
        break
      case 'ArrowLeft':
        event.preventDefault()
        // Mirror image: close an open folder, or step OUT to the parent. This is
        // what lets you climb out of a deep path without arrowing past siblings.
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
        else focusRow(row.node.value)
        break
      default:
        break
    }
  }

  function renderNodes(list: TreeNode[], level: number) {
    return list.map((node) => {
      const isFolder = Array.isArray(node.children)
      const isExpanded = expanded.includes(node.value)
      const isActive = node.value === activeValue

      return (
        <div key={node.value} role="none">
          <div
            ref={(el) => {
              rowRefs.current.set(node.value, el)
            }}
            role="treeitem"
            // aria-expanded only on folders — on a leaf it announces a collapsed
            // state that can never open.
            aria-expanded={isFolder ? isExpanded : undefined}
            aria-selected={node.value === selected}
            aria-level={level}
            tabIndex={isActive ? 0 : -1}
            className="ti-row"
            style={{ paddingLeft: `${(level - 1) * 16 + 6}px` }}
            onClick={() => {
              if (isFolder) setExpandedFor(node.value, !isExpanded)
              focusRow(node.value)
            }}
          >
            <span aria-hidden="true" className="ti-caret">
              {isFolder ? (isExpanded ? '▾' : '▸') : '·'}
            </span>
            {node.label}
          </div>
          {isFolder && isExpanded && (
            // The group wrapper is what makes the nesting real to assistive tech.
            <div role="group">{renderNodes(node.children!, level + 1)}</div>
          )}
        </div>
      )
    })
  }

  return (
    <div id={`${baseId}-tree`} role="tree" aria-label={label} className="ti" onKeyDown={handleKeyDown}>
      {renderNodes(nodes, 1)}
    </div>
  )
}

/* ------------------------------------------------------------------ cut ----
 * Dropped from the reference, and what to say if asked:
 *
 * - aria-posinset / aria-setsize  "Screen readers announce '2 of 5' from these.
 *                                  flatten already computes them — I'd thread
 *                                  them through if accessibility is being graded."
 * - Controlled selection API      "value / defaultValue / onValueChange for a
 *                                  library component."
 * - defaultExpanded               "Trivial to add; useful for deep-linking."
 * - Type-to-jump                  "APG asks for it — printable characters jump to
 *                                  the next matching node."
 * - Multi-select, drag, rename    "Different feature, not the tree pattern."
 * - Virtualisation                "Only past a few thousand visible rows, and
 *                                  flatten already gives you the flat list it
 *                                  would window over."
 *
 * aria-posinset/setsize is the cheapest of these and the one I'd add first.
 * -------------------------------------------------------------------------- */

/* ----------------------------------------------------------------- demo ---- */

const FILES: TreeNode[] = [
  {
    value: 'src',
    label: 'src',
    children: [
      {
        value: 'components',
        label: 'components',
        children: [
          { value: 'button.tsx', label: 'Button.tsx' },
          { value: 'modal.tsx', label: 'Modal.tsx' },
        ],
      },
      { value: 'app.tsx', label: 'App.tsx' },
      { value: 'main.tsx', label: 'main.tsx' },
    ],
  },
  { value: 'readme', label: 'README.md' },
  { value: 'empty', label: 'assets' , children: [] },
]

export default function TreeInterview() {
  const [picked, setPicked] = useState<string | null>(null)

  return (
    <div className="ti-demo">
      <p className="ti-note">
        ↓ ↑ walk every visible row regardless of depth. → opens a folder then steps into it; ←
        closes it then climbs to the parent. 131 lines of code against the reference’s 154.
      </p>
      <Tree nodes={FILES} label="Project files" onSelect={setPicked} />
      <p className="ti-picked">
        Selected: <code>{picked ?? 'nothing'}</code>
      </p>
    </div>
  )
}
```

</details>

## 11 — Data table

> Runnable: `uie-practice/src/exercises/data-table-reference/` · Spec: 15 tests  
> Interview cut (§H): `uie-practice/src/exercises/data-table-interview/` · Spec: 10 tests

### A. ASKED AS

- "Build a sortable table" / "a users table with search and pagination"
- "Add row selection with a select-all"
- "Render 100,000 rows" — that's §13 (Virtualized list), not this

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

### H. INTERVIEW SCOPE

**Reference: 193 lines of code.** The cut below is 111.

**Core, and it's one idea:**

**Filter, then sort, then paginate — and derive the page rather than storing it.** Filter down to
two results while sitting on page 5 and a stored page index renders an empty table with working
pagination. Users report that as "the search is broken."

Everything else is table markup, and the markup matters more than it looks:

- A real `<table>`, not a grid of divs — screen reader users navigate tables with dedicated keys
  that only work on real table markup
- `<caption>` as the accessible name; visible, unlike `aria-label`
- `<th scope="row">` on the first cell so AT says "Ada, Compilers" rather than just "Compilers"
- `aria-sort` on the `th`, only on the sorted column
- Copy before sorting — `Array.prototype.sort` mutates, and the filtered array may be the `rows`
  prop itself
- Sort cycling ascending → descending → none; sorting shouldn't be a one-way door

**Cut, and say so:**

| Drop | Say |
|---|---|
| Row selection | "Keyed by row id, not index, so sorting doesn't move it. A `Set` for O(1) membership per rendered row." |
| Custom `sortValue` / `render` props | "So a column can sort on a date while displaying a formatted string." |
| Column resize / reorder | "Out of scope unless asked." |
| Virtualisation | "Past a few thousand rows — and it breaks native table semantics, so it's a real trade-off, not a free win." |

<details>
<summary>The interview cut — DataTable</summary>

```tsx
import { useMemo, useState } from 'react'

/**
 * THE INTERVIEW CUT of data-table-reference: 193 lines of code down to 111.
 *
 * The whole component is one idea — FILTER, THEN SORT, THEN PAGINATE, and derive
 * the page rather than storing it. Filter to two results while sitting on page 5
 * and a stored page index renders an empty table; users report that as "the
 * search is broken". Everything else is table markup.
 *
 * What went, and the sentence to say, is at the bottom of the file.
 */

export interface Column {
  key: string
  header: string
  sortable?: boolean
}

interface DataTableProps<T> {
  rows: T[]
  columns: Column[]
  caption: string
  getRowId: (row: T) => string
  getCell: (row: T, key: string) => string | number
  pageSize?: number
}

type SortState = { key: string; direction: 'ascending' | 'descending' } | null

export function DataTable<T>({
  rows,
  columns,
  caption,
  getRowId,
  getCell,
  pageSize = 5,
}: DataTableProps<T>) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortState>(null)
  const [page, setPage] = useState(0)

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = q
      ? rows.filter((row) => columns.some((c) => String(getCell(row, c.key)).toLowerCase().includes(q)))
      : rows
    if (!sort) return filtered
    // Copy first: sort mutates, and `filtered` may be the rows prop itself.
    return [...filtered].sort((a, b) => {
      const av = getCell(a, sort.key)
      const bv = getCell(b, sort.key)
      const result =
        typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv))
      return sort.direction === 'ascending' ? result : -result
    })
  }, [rows, columns, query, sort, getCell])

  const pageCount = Math.max(1, Math.ceil(visible.length / pageSize))
  // Clamp rather than store — this is the bug the component exists to avoid.
  const safePage = Math.min(page, pageCount - 1)
  const pageRows = visible.slice(safePage * pageSize, safePage * pageSize + pageSize)

  function toggleSort(key: string) {
    setSort((prev) =>
      prev?.key === key
        ? prev.direction === 'ascending'
          ? { key, direction: 'descending' }
          : null // third click clears — sorting is not a one-way door
        : { key, direction: 'ascending' },
    )
  }

  return (
    <div>
      <label className="dti-search">
        <span className="visually-hidden">Filter rows</span>
        <input type="search" placeholder="Filter…" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>

      <table className="dti-table">
        {/* The table's accessible name, and visible — better than aria-label. */}
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((col) => {
              const active = sort?.key === col.key
              // aria-sort goes on the th, and only on the sorted column.
              return (
                <th key={col.key} scope="col" aria-sort={active ? sort.direction : undefined}>
                  {col.sortable ? (
                    <button type="button" onClick={() => toggleSort(col.key)}>
                      {col.header}
                      <span aria-hidden="true"> {active ? (sort.direction === 'ascending' ? '▲' : '▼') : '↕'}</span>
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
          {pageRows.map((row) => (
            <tr key={getRowId(row)}>
              {columns.map((col, i) =>
                // The first cell is the row's header, so AT says "Ada, Compilers".
                i === 0 ? (
                  <th key={col.key} scope="row">
                    {getCell(row, col.key)}
                  </th>
                ) : (
                  <td key={col.key}>{getCell(row, col.key)}</td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {visible.length === 0 && <p className="dti-empty">No rows match “{query}”.</p>}

      <div className="dti-pager">
        <button type="button" onClick={() => setPage(safePage - 1)} disabled={safePage === 0}>
          Previous
        </button>
        {/* Announced — the rows changing underneath is otherwise silent. */}
        <span role="status">
          Page {safePage + 1} of {pageCount} · {visible.length} rows
        </span>
        <button type="button" onClick={() => setPage(safePage + 1)} disabled={safePage >= pageCount - 1}>
          Next
        </button>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ cut ----
 * Dropped from the reference, and what to say if asked:
 *
 * - Row selection (Set + select-all)  "Selection is keyed by row id, not index,
 *                                      so sorting doesn't move it. A Set for
 *                                      O(1) membership per rendered row."
 * - Custom sortValue / render props   "I'd add them so a column can sort on a
 *                                      date while displaying a formatted string."
 * - Column resize / reorder           "Out of scope unless asked."
 * - Virtualisation                    "Only past a few thousand rows — and it
 *                                      breaks native table semantics, so it's a
 *                                      real trade-off, not a free win."
 *
 * The reference keeps all of these; this is the version that fits the clock.
 * -------------------------------------------------------------------------- */

/* ----------------------------------------------------------------- demo ---- */

interface Person {
  id: string
  name: string
  team: string
  commits: number
}

const PEOPLE: Person[] = [
  { id: '1', name: 'Ada Lovelace', team: 'Compilers', commits: 412 },
  { id: '2', name: 'Grace Hopper', team: 'Compilers', commits: 388 },
  { id: '3', name: 'Alan Turing', team: 'Runtime', commits: 274 },
  { id: '4', name: 'Barbara Liskov', team: 'Languages', commits: 501 },
  { id: '5', name: 'Katherine Johnson', team: 'Runtime', commits: 143 },
  { id: '6', name: 'Margaret Hamilton', team: 'Flight', commits: 655 },
]

const COLUMNS: Column[] = [
  { key: 'name', header: 'Name', sortable: true },
  { key: 'team', header: 'Team', sortable: true },
  { key: 'commits', header: 'Commits', sortable: true },
]

export default function DataTableInterview() {
  return (
    <div className="dti-demo">
      <p className="dti-note">
        Filter to something narrow while on page 2 — the page clamps to one that has rows instead of
        rendering blank. 111 lines of code against the reference’s 193.
      </p>
      <DataTable
        rows={PEOPLE}
        columns={COLUMNS}
        caption="Engineers by team"
        getRowId={(r) => r.id}
        getCell={(r, key) => r[key as keyof Person]}
        pageSize={3}
      />
    </div>
  )
}
```

</details>

## 12 — Command palette

> Interview cut (§H): `uie-practice/src/exercises/command-palette-interview/` · Spec: 20 tests  
> Native variant (§I): `uie-practice/src/exercises/command-palette-dialog/` · Spec: 15 tests  
> Derive-it-cold drill: `uie-practice/src/exercises/cursor-06-command-palette/` · Spec: 15 tests  
> The §E reference is guide-only — there is no `command-palette-reference` on disk. The three
> runnables above are the cut, the same component on native `<dialog>`, and the blank-page drill
> this section came out of.

### A. ASKED AS

- "Build a ⌘K command palette"
- "Build quick-open / go-to-file"
- "Build the Slack switcher" / "the Linear command menu"
- After the streaming message (§14), the likeliest component at an editor company

This is the most *composed* thing in the guide: a dialog (§05) containing a combobox (§06) over a
command list (§07). None of the three arrives whole, and the interesting decisions are all at the
seams. If you can only afford one derivation rep, make it this one.

### B. API

```tsx
export interface Command {
  id: string
  label: string
  /** Section heading in the list. Purely presentational. */
  group?: string
  /** Aliases, so "Toggle Theme" is findable by typing "dark". */
  keywords?: string[]
  run: () => void
}

export interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  commands: Command[]
  /** Most recent first. */
  recentIds?: string[]
  placeholder?: string
  emptyMessage?: string
}
```

**Four calls worth stating out loud:**

- **`open` is a prop, and the ⌘K listener is not this component's.** A palette that owns its own
  global shortcut cannot be opened from a menu item or a button, and two on a page fight over the
  key. The listener belongs to the app. Same reasoning as the Modal (§05) being controlled-only:
  the parent is what decides a dialog should exist.
- **Each command carries its own `run`.** The alternative — `onSelect(id)` plus a switch in the
  parent — grows a switch statement inside every caller. Behaviour travels with the thing it
  belongs to.
- **`keywords` is a product decision, not a feature.** It is one `.some()`, and it is the
  difference between a palette people use and one they abandon. Name it as such.
- **`recentIds` is passed in rather than tracked.** Recency has to survive this component
  unmounting, so it belongs to whatever owns the session.

**And one non-prop, which is the more interesting half.** The query is not in the API at all — not
`value`, not `defaultValue`, not a `key` for the caller to bump. Opening resets it, and that is the
component's business. A palette that reopens onto last time's half-typed query is a bug, and no
caller should have to know that. This is the Combobox call (§06) taken one step further: there the
query merely isn't controlled; here it isn't persisted either.

### C. ARIA + KEYBOARD CONTRACT

| Element | Required |
|---|---|
| Dialog | `role="dialog"`, `aria-modal="true"`, accessible name |
| Input | `role="combobox"`, `aria-expanded="true"`, `aria-controls` → listbox, `aria-autocomplete="list"`, `aria-activedescendant` |
| Listbox | `role="listbox"`, `id`, accessible name — **rendered even when empty** |
| Group | `role="group"` with `aria-label`; the visible heading is `aria-hidden` |
| Option | `role="option"`, `aria-selected`, `id` derived from the **flat** index |

`aria-expanded` is permanently `true`. The list is part of the surface rather than a popup over
it — there is no closed state to describe, because closing the list means closing the palette.

**Why this is a listbox and not a menu.** The two derivation tests give conflicting answers, and
watching them resolve is the whole lesson. Question 1 (§02 B): interactions here fire and leave
nothing behind, which says command widget — `menuitem`, no selection state, no `value`. Question 2:
the input must stay typeable while the cursor moves, which forces `aria-activedescendant`. Those
collide, because a combobox may only point `aria-activedescendant` into the popup it controls, and
a combobox popup is a `listbox`, `grid`, `tree`, or `dialog` — never a `menu`.

The focus model wins, because it is the one the user can feel. The command-ness does not disappear;
it moves from markup into behaviour: `aria-selected` marks **the cursor**, not a selection, nothing
is selected once the palette closes, and there is no `value` anywhere in the API. That sentence is
the single highest-value thing you can say while building this component.

| Key | Behavior |
|---|---|
| `↓` / `↑` | Move the virtual cursor over the flat result list. Wraps. |
| `Home` / `End` | First / last result |
| `Enter` | Run the cursor's command, then close. No-op on an empty list. |
| `Esc` | Close. One stage, unlike the Combobox's two. |
| `Tab` | Trapped. With one focusable node in the dialog, the trap is `preventDefault`. |
| Typing | Refilters, and returns the cursor to the top |

Escape being one-stage is worth a sentence, because §06 makes the opposite call. There, closing the
list must not also wipe the query — the query is the user's work and the field survives. Here the
whole surface goes away and the query goes with it either way, so a two-stage Escape would only
mean pressing it twice.

### D. DECISIONS THAT MATTER

1. **Mounting is the state machine.** Closed renders nothing, so every opening is a fresh mount.
   The query starts empty for free — no reset effect — and focus-in / focus-out become one effect
   with a cleanup instead of four `if (open)` guards. → *"I render nothing when it's closed, so
   opening is a mount. That's what resets the query, and it's why there's only one focus effect."*
2. **An empty query is the recents view, not "no filter".** Two orderings of one derived list, and
   nothing stored. Getting this wrong shows up as a recent command appearing twice, which is what
   the dedupe `Set` is for. → *"Empty isn't unfiltered — it's the recents ordering."*
3. **The cursor indexes the flat result list; groups are a rendering concern.** The moment the
   index means "third row of the second group", every key handler has to understand grouping, and
   Home/End and wrapping all acquire an off-by-one at every boundary. Render groups by walking the
   flat list and carrying each row's flat index with it.
4. **Close before you run.** `onClose()` first, then `command.run()`. A command that opens another
   dialog must not have that dialog closed by this one unmounting afterwards.
5. **`onMouseDown`, not `onClick`.** `blur` fires before `click`, and blur closes the palette, so an
   `onClick` on an option never runs. `preventDefault()` on mousedown keeps the caret in the input.
   Identical to §06, and it is the bug most people ship.

### E. IMPLEMENTATION

**1 — Two orderings, one derived list.**

```tsx
const results = useMemo<Row[]>(() => {
  const q = query.trim().toLowerCase()
  if (!q) {
    const recents = recentIds
      .map((id) => commands.find((c) => c.id === id))
      .filter((c): c is Command => c !== undefined)
    const promoted = new Set(recents.map((c) => c.id))
    return [
      ...recents.map((command) => ({ command, section: 'Recently used' })),
      ...commands.filter((c) => !promoted.has(c.id)).map((command) => ({ command, section: command.group })),
    ]
  }
  return commands
    .filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        (c.keywords ?? []).some((k) => k.toLowerCase().includes(q)),
    )
    .map((command) => ({ command, section: command.group }))
}, [commands, query, recentIds])
```

`recentIds` maps through `find` rather than the reverse, because the *order of `recentIds`* is the
recency order — filtering `commands` would give you back the catalogue's order with the recents
still scattered through it. The `promoted` set is what stops each recent command rendering twice.

**2 — Clamp the cursor; don't store the clamp.**

```tsx
const activeIndex = results.length === 0 ? -1 : Math.min(cursor, results.length - 1)
```

`commands` is a prop, so the list can shrink under a cursor that is already parked past the new
end. Left alone, `aria-activedescendant` then names an id that is no longer in the DOM — and a
dangling IDREF fails silently, so nothing tells you. One derived line, and §02 B question 3 is
exactly the instinct that produces it.

**3 — Groups, without renumbering anything.**

```tsx
const sections = useMemo(() => {
  const out: { label?: string; rows: Array<{ row: Row; index: number }> }[] = []
  results.forEach((row, index) => {
    const last = out[out.length - 1]
    if (last && last.label === row.section) last.rows.push({ row, index })
    else out.push({ label: row.section, rows: [{ row, index }] })
  })
  return out
}, [results])
```

Adjacent runs, not a `groupBy`. The caller's ordering is the ordering — recents deliberately break
their commands out of their usual sections, and a `groupBy` would silently put them back. Each row
carries the **flat** index it had in `results`, which is what keeps decision 3 true.

**4 — Focus in, focus back, and the reset you don't write.**

```tsx
useEffect(() => {
  const previouslyFocused = document.activeElement as HTMLElement | null
  inputRef.current?.focus()
  return () => {
    if (previouslyFocused?.isConnected) previouslyFocused.focus()
  }
}, [])
```

Empty deps, because this component only exists while open. The `isConnected` check is not
decoration: `.focus()` on a detached node does nothing and throws nothing, so focus falls to
`<body>` and a keyboard user restarts from the top of the page (§17 B). And note what isn't here —
no "reset the query on open" effect, because there is no open-to-closed transition to react to.

**5 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Command palette</summary>

```tsx
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { KeyboardEvent, MouseEvent, PointerEvent } from 'react'

/**
 * Three ideas carry this component:
 *
 * 1. IT IS A COMBOBOX IN A DIALOG, NOT A MENU. Commands fire and leave nothing
 *    selected, which says `menuitem` — but the input has to stay typeable while
 *    the cursor moves, which forces aria-activedescendant, and a combobox may
 *    only point that at an `option` inside the listbox it controls. Behaviour
 *    decides the popup role; "it's a list of commands" does not.
 *
 * 2. MOUNTING IS THE STATE MACHINE. Closed renders nothing, so every opening is
 *    a fresh mount: the query starts empty for free, and focus-in / focus-out
 *    are one effect with a cleanup instead of four `if (open)` guards.
 *
 * 3. THE CURSOR INDEXES THE FLAT RESULT LIST. Groups are a rendering
 *    concern. The moment the index means "third item in the second group", every
 *    key handler has to know about grouping, and it will get it wrong.
 */

export interface Command {
  id: string
  label: string
  /** Section heading in the list. Purely presentational — it never affects indexing. */
  group?: string
  /** Aliases, so "Toggle Theme" is findable by typing "dark". */
  keywords?: string[]
  run: () => void
}

export interface CommandPaletteProps {
  /** Controlled only. The ⌘K listener belongs to the app, not to this component. */
  open: boolean
  onClose: () => void
  /** Must be referentially stable — filtering memoizes on it. */
  commands: Command[]
  /** Most recent first. Owned by the caller, because recency outlives this unmount. */
  recentIds?: string[]
  placeholder?: string
  emptyMessage?: string
}

/**
 * Hoisted so the default is one stable array. `recentIds = []` in the parameter
 * list allocates a fresh array on every render, which invalidates the useMemo
 * below on every render — the filter still works, and the memo does nothing.
 */
const NO_RECENTS: string[] = []

/** One result row: the command, plus the section it renders under. */
interface Row {
  command: Command
  section?: string
}

export function CommandPalette({ open, ...rest }: CommandPaletteProps) {
  // Mount/unmount IS the state machine (see 2 above). It is also why there is no
  // "reset the query on open" effect anywhere in this file.
  if (!open) return null
  // Portal for the same three reasons as the Modal: a transformed ancestor becomes
  // the containing block for position:fixed, overflow clips, and z-index cannot
  // escape a parent stacking context.
  return createPortal(<Palette {...rest} />, document.body)
}

function Palette({
  onClose,
  commands,
  recentIds = NO_RECENTS,
  placeholder = 'Type a command…',
  emptyMessage = 'No matching commands',
}: Omit<CommandPaletteProps, 'open'>) {
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)

  const baseId = useId()
  const listboxId = `${baseId}-listbox`
  const optionId = (index: number) => `${baseId}-option-${index}`

  const inputRef = useRef<HTMLInputElement>(null)
  const pointerDownTarget = useRef<EventTarget | null>(null)

  // An empty query is not "no filter" — it is the recents view. Two different
  // orderings of one derived list, and nothing is stored.
  const results = useMemo<Row[]>(() => {
    const q = query.trim().toLowerCase()
    if (!q) {
      const recents = recentIds
        .map((id) => commands.find((c) => c.id === id))
        .filter((c): c is Command => c !== undefined)
      const promoted = new Set(recents.map((c) => c.id))
      return [
        ...recents.map((command) => ({ command, section: 'Recently used' })),
        // Filtering out the promoted ones is what stops a recent command appearing twice.
        ...commands.filter((c) => !promoted.has(c.id)).map((command) => ({ command, section: command.group })),
      ]
    }
    return commands
      .filter(
        (c) =>
          c.label.toLowerCase().includes(q) ||
          (c.keywords ?? []).some((k) => k.toLowerCase().includes(q)),
      )
      .map((command) => ({ command, section: command.group }))
  }, [commands, query, recentIds])

  // Derived, not stored. `commands` can shrink under a cursor that is already
  // parked past the new end — and then aria-activedescendant names an id that no
  // longer exists, which is a silent failure, not a visible one.
  const activeIndex = results.length === 0 ? -1 : Math.min(cursor, results.length - 1)

  // Adjacent runs, not a groupBy: the caller's ordering is the ordering, and
  // recents deliberately break their commands out of their usual sections.
  const sections = useMemo(() => {
    const out: { label?: string; rows: Array<{ row: Row; index: number }> }[] = []
    results.forEach((row, index) => {
      const last = out[out.length - 1]
      if (last && last.label === row.section) last.rows.push({ row, index })
      else out.push({ label: row.section, rows: [{ row, index }] })
    })
    return out
  }, [results])

  // Focus in on mount, back out on unmount. `.focus()` on a detached node fails
  // silently, so isConnected is the only way to know restore did not happen.
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null
    inputRef.current?.focus()
    return () => {
      if (previouslyFocused?.isConnected) previouslyFocused.focus()
    }
  }, [])

  // Keep the cursor visible without moving focus. getElementById, not
  // querySelector: React 18's useId emits ids like `:r3:`, and a colon is not a
  // valid CSS identifier, so `#${id}` throws. React 19 emits `_R_3_`, which
  // happens to be safe — an id you did not choose is not one to build selectors on.
  useEffect(() => {
    if (activeIndex < 0) return
    // The template is inlined rather than calling optionId, so the dependency is
    // baseId — which is stable — instead of a function rebuilt every render.
    document.getElementById(`${baseId}-option-${activeIndex}`)?.scrollIntoView?.({ block: 'nearest' })
  }, [activeIndex, baseId])

  function run(row?: Row) {
    if (!row) return
    // Close BEFORE running. A command that opens another dialog must not have that
    // dialog closed by this one unmounting after it.
    onClose()
    row.command.run()
  }

  function move(delta: number) {
    if (results.length === 0) return
    setCursor((i) => (Math.min(i, results.length - 1) + delta + results.length) % results.length)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault() // else the caret jumps to the end of the input
        move(1)
        break
      case 'ArrowUp':
        event.preventDefault()
        move(-1)
        break
      case 'Home':
        event.preventDefault()
        setCursor(0)
        break
      case 'End':
        event.preventDefault()
        setCursor(Math.max(0, results.length - 1))
        break
      case 'Enter':
        event.preventDefault()
        // No-op on an empty result set, rather than closing. Enter on "no matches"
        // dismissing the palette reads as "it did something".
        run(results[activeIndex])
        break
      case 'Escape':
        // One stage, unlike the Combobox's two. There the query is the user's work
        // and closing the list must not destroy it; here the whole surface goes
        // away and the query goes with it either way.
        event.preventDefault()
        onClose()
        break
      case 'Tab':
        // The trap, collapsed. The input is the only focusable node in this dialog,
        // so "wrap at the edges" and "swallow Tab" are the same behaviour. Add a
        // footer button and this has to become the real edge trap (§17 B).
        event.preventDefault()
        break
      default:
        break
    }
  }

  const message =
    results.length === 0
      ? emptyMessage
      : `${results.length} command${results.length === 1 ? '' : 's'}`

  return (
    <div
      className="cp-backdrop"
      onPointerDown={(event: PointerEvent<HTMLDivElement>) => {
        pointerDownTarget.current = event.target
      }}
      onClick={(event: MouseEvent<HTMLDivElement>) => {
        // Both halves of the gesture must land on the backdrop. Without the
        // pointerdown half, selecting text in the input and releasing outside closes.
        if (pointerDownTarget.current === event.currentTarget && event.target === event.currentTarget) {
          onClose()
        }
      }}
    >
      <div role="dialog" aria-modal="true" aria-label="Command palette" className="cp-panel">
        <input
          ref={inputRef}
          className="cp-input"
          type="text"
          role="combobox"
          autoComplete="off"
          // Always expanded: the list is part of the surface, not a popup on it.
          aria-expanded
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? optionId(activeIndex) : undefined}
          aria-label="Search commands"
          placeholder={placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setCursor(0) // a new filter invalidates the old position
          }}
          onKeyDown={handleKeyDown}
        />

        {/* Announced, not shown. The list appearing is visible; the count is not. */}
        <div className="visually-hidden" role="status" aria-live="polite">
          {message}
        </div>

        {/* Rendered even when empty, so aria-controls always resolves. A dangling
            IDREF fails silently, which is exactly why it survives review. */}
        <div id={listboxId} role="listbox" aria-label="Commands" className="cp-list">
          {sections.map((section, i) => (
            // listbox → group → option is the only legal nesting here; a bare
            // heading element as a listbox child is not.
            <div
              key={section.label ?? `section-${i}`}
              role="group"
              aria-label={section.label ?? 'Other commands'}
              className="cp-group"
            >
              {section.label && (
                // aria-hidden because the group already carries this as its name;
                // without it every option is announced with the heading prefixed.
                <div className="cp-group-label" aria-hidden="true">
                  {section.label}
                </div>
              )}
              {section.rows.map(({ row, index }) => (
                <div
                  key={row.command.id}
                  id={optionId(index)}
                  role="option"
                  // Marks the CURSOR, not a selection. Nothing stays selected after
                  // this closes — that is what makes it a command widget.
                  aria-selected={index === activeIndex}
                  className="cp-option"
                  // onMouseDown, not onClick: blur closes the palette before a
                  // click would ever land on this element.
                  onMouseDown={(e) => {
                    e.preventDefault() // keep focus, and the caret, in the input
                    run(row)
                  }}
                  onMouseEnter={() => setCursor(index)}
                >
                  {row.command.label}
                </div>
              ))}
            </div>
          ))}
        </div>

        {results.length === 0 && (
          // Visual only — the live region above is what actually gets announced.
          <p className="cp-empty" aria-hidden="true">
            {emptyMessage}
          </p>
        )}
      </div>
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| ⌘K listener inside the component | Nothing else can open it, and two on a page fight over the key |
| Storing the filtered list in state | It disagrees with the query the moment `commands` changes |
| Storing the cursor without clamping | `aria-activedescendant` names a removed id — silently |
| Indexing options per group | Arrows skip or repeat a row at every group boundary |
| `onClick` on options | Blur closes the palette first; the handler never fires |
| Unmounting the listbox when empty | `aria-controls` dangles, and nothing reports it |
| `run()` before `onClose()` | A command that opens another surface is closed by this one unmounting |
| `recentIds = []` as a default parameter | New array identity every render; the memo never hits |
| Recents left in the rest of the list | The same command renders twice |
| `querySelector('#' + id)` from `useId` | React 18 emits `:r3:` — a colon is not a valid CSS identifier, so it throws |
| `aria-live` on the option list | Every keystroke re-announces every row |
| `onKeyDown` on the panel `<div>` | Dies the moment focus leaves the input — the panel can't hold focus, so `<body>` gets the keydown (§17 M) |
| `type="search"` on the input | WebKit and Chromium add a mouse-only clear button and clear the field on Escape — UA behaviour you then have to suppress. `type="text"` has none of it |
| Reset done by keying the component from the parent | Works, and pushes a bug the caller shouldn't know about onto every caller |

### G. SPEC

**Markup** — closed renders nothing · a labelled modal dialog · the input is the combobox, and
`aria-controls` resolves to the listbox before anything is typed

**Filtering** — an empty query lists everything · recents first, without duplicating them · the
label matches case-insensitively · a keyword matches when the label does not

**Cursor** — arrows move it and wrap at both ends · exactly one option is `aria-selected` · focus
never leaves the input · typing returns the cursor to the top

**Running** — Enter runs the cursor's command and closes · a click runs it despite blur · Escape
closes and runs nothing · with no matches there is a message and Enter is a no-op

**Lifecycle** — focus restores to the trigger on close · reopening starts from an empty query

### H. INTERVIEW SCOPE

**Reference: 201 lines of code — second only to the Combobox, and too big for a timed round.**
The cut below is 132 and keeps everything that gets graded.

Worth diffing against `cursor-06-command-palette/solution.jsx`, which solves the same prompt at 120
lines and makes three different calls: one component with an `[open]` effect and an explicit reset
rather than a split and a portal; Home/End kept; a group tag per row kept; no Tab trap. Neither is
the right answer — the point of reading both is that a cut is a set of choices, not a fixed
subset.

Fifty minutes sounds generous for a palette, and it is not. The reference is three components'
worth of contract, and there is a real risk of spending the hour on group headings and the backdrop
while the cursor still doesn't wrap.

**Core:**

- The dialog: `role="dialog"`, `aria-modal="true"`, an accessible name
- The combobox markup with `aria-activedescendant`, and focus that never leaves the input
- The listbox rendered even when the result set is empty, so `aria-controls` resolves
- Recents-when-empty and keyword matching — one expression each, and both are graded as product judgement
- Arrows with wrapping, Enter runs and closes, Escape closes
- `onMouseDown` not `onClick` on options
- Focus in on mount, back out on unmount, with the `isConnected` check

**Cut, and say so:**

| Drop | Say |
|---|---|
| Group headings and `role="group"` | "The cursor already indexes the flat list, so grouping is a render-time regroup that doesn't touch the keyboard. It's the first thing I'd add back visually." |
| `aria-live` result count | "Sighted users watch the list shrink; screen reader users need the count spoken. Four lines — the one I'd add back first." |
| `scrollIntoView` on the cursor | "Needed the moment the list overflows." |
| Home / End | "APG lists them; lowest value of the keys here." |
| The pointerdown half of backdrop dismissal | "Right now a drag that starts inside and ends on the backdrop closes it and throws the query away." |
| Fuzzy subsequence matching | "Substring over label plus keywords is the 80% case. Fuzzy is a scoring function, not a structural change." |
| `placeholder` / `emptyMessage` props | "Hardcoded here; they'd be props in a library component." |

Do **not** cut the mousedown ordering to save two characters, and do not cut focus restore. Those
are the two the interviewer will test by hand.

<details>
<summary>The interview cut — Command palette</summary>

```tsx
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { KeyboardEvent } from 'react'

/**
 * THE INTERVIEW CUT: 201 lines of code down to 132.
 *
 * Everything load-bearing is still here — the dialog, the combobox markup with a
 * virtual cursor, recents-when-empty, keyword matching, arrows/Enter/Escape,
 * mousedown-not-click, and focus in and back out. What went is listed at the
 * bottom, with the sentence to say for each.
 */

export interface Command {
  id: string
  label: string
  keywords?: string[]
  run: () => void
}

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  commands: Command[]
  recentIds?: string[]
}

const NO_RECENTS: string[] = []

export function CommandPalette({ open, ...rest }: CommandPaletteProps) {
  // Mounting is the state machine: a fresh mount per opening is what makes the
  // query start empty without a reset effect anywhere.
  if (!open) return null
  return createPortal(<Palette {...rest} />, document.body)
}

function Palette({
  onClose,
  commands,
  recentIds = NO_RECENTS,
}: Omit<CommandPaletteProps, 'open'>) {
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)

  const baseId = useId()
  const listboxId = `${baseId}-listbox`
  const optionId = (i: number) => `${baseId}-option-${i}`
  const inputRef = useRef<HTMLInputElement>(null)

  // An empty query is the recents view, not "no filter". Two orderings of one
  // derived list; nothing stored.
  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) {
      const recents = recentIds
        .map((id) => commands.find((c) => c.id === id))
        .filter((c): c is Command => c !== undefined)
      const promoted = new Set(recents.map((c) => c.id))
      return [...recents, ...commands.filter((c) => !promoted.has(c.id))]
    }
    return commands.filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        (c.keywords ?? []).some((k) => k.toLowerCase().includes(q)),
    )
  }, [commands, query, recentIds])

  // Derived: `commands` can shrink under a parked cursor, and then
  // aria-activedescendant names an id that is no longer in the DOM.
  const activeIndex = results.length === 0 ? -1 : Math.min(cursor, results.length - 1)

  // Focus in on mount, back out on unmount. `.focus()` on a detached node fails
  // silently, so isConnected is the only way to know restore did not happen.
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null
    inputRef.current?.focus()
    return () => {
      if (previouslyFocused?.isConnected) previouslyFocused.focus()
    }
  }, [])

  function run(command?: Command) {
    if (!command) return
    onClose() // close first: a command that opens another surface must survive this
    command.run()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    const move = (delta: number) =>
      setCursor((i) => (Math.min(i, results.length - 1) + delta + results.length) % results.length)

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault() // else the caret jumps to the end of the input
        if (results.length > 0) move(1)
        break
      case 'ArrowUp':
        event.preventDefault()
        if (results.length > 0) move(-1)
        break
      case 'Enter':
        event.preventDefault()
        run(results[activeIndex]) // undefined on an empty list, so this is a no-op
        break
      case 'Escape':
        event.preventDefault()
        onClose()
        break
      case 'Tab':
        // The input is the only focusable node in here, so the trap collapses to
        // swallowing Tab. A footer button would need the real edge trap.
        event.preventDefault()
        break
      default:
        break
    }
  }

  return (
    <div className="cp-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label="Command palette" className="cp-panel">
        <input
          ref={inputRef}
          className="cp-input"
          type="text"
          role="combobox"
          autoComplete="off"
          aria-expanded
          aria-controls={listboxId}
          aria-autocomplete="list"
          // The virtual cursor: real focus never leaves the input.
          aria-activedescendant={activeIndex >= 0 ? optionId(activeIndex) : undefined}
          aria-label="Search commands"
          placeholder="Type a command…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setCursor(0) // a new filter invalidates the old position
          }}
          onKeyDown={handleKeyDown}
        />

        {/* Rendered even when empty so aria-controls always resolves. */}
        <ul id={listboxId} role="listbox" aria-label="Commands" className="cp-list">
          {results.map((command, index) => (
            <li
              key={command.id}
              id={optionId(index)}
              role="option"
              // Marks the cursor, not a selection — nothing stays selected.
              aria-selected={index === activeIndex}
              className="cp-option"
              // mousedown, not click: blur closes the palette first.
              onMouseDown={(e) => {
                e.preventDefault()
                run(command)
              }}
              onMouseEnter={() => setCursor(index)}
            >
              {command.label}
            </li>
          ))}
        </ul>

        {results.length === 0 && (
          <p role="status" className="cp-empty">
            No matching commands
          </p>
        )}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ cut ----
 * Dropped from the reference, and what to say if asked:
 *
 * - Group headings / role="group"    "The cursor indexes the flat list already,
 *                                     so grouping is a render-time regroup that
 *                                     doesn't touch the keyboard."
 * - aria-live result count           "Sighted users watch the list shrink; screen
 *                                     reader users need the count spoken. Four
 *                                     lines, and the first thing I'd add back."
 * - scrollIntoView on the cursor     "Needed the moment the list overflows."
 * - Home / End                       "APG lists them; lowest value of the keys."
 * - The pointerdown half of backdrop "A drag that starts inside and ends on the
 *   dismissal                         backdrop currently closes it."
 * - Fuzzy subsequence matching       "Substring over label plus keywords is the
 *                                     80% case; fuzzy is a scoring function, not
 *                                     a structural change."
 * - placeholder / emptyMessage props "Hardcoded; they'd be props in a library."
 *
 * Of those, the live region is the one I'd actually spend time on if the
 * interviewer signals accessibility matters.
 * -------------------------------------------------------------------------- */
```

</details>

### I. THE NATIVE `<dialog>` VARIANT

> Runnable: `uie-practice/src/exercises/command-palette-dialog/` · Spec: 15 tests

Everything above builds the dialog by hand, because that is what the round is testing. This is the
same component on `showModal()`, so you can diff them — and so the sentence *"in production I'd use
native `<dialog>`"* is backed by something you've actually written.

**What they share:** the role. `<dialog>` has an implicit `role="dialog"`, so to assistive tech the
two are identical. That is the *only* thing `role="dialog"` was buying. Everything below comes from
the `showModal()` call, not from the element.

| | `<div role="dialog">` | `<dialog>` + `showModal()` |
|---|---|---|
| Top layer | No — portal to `<body>` to escape ancestor `transform` / `overflow` / `z-index` | **Yes.** Renders above the document from wherever it sits |
| Backdrop | An element you render | `::backdrop`, also in the top layer |
| Outside content inert | **No.** `aria-modal="true"` is a declaration to AT; pointer and Tab ignore it | **Yes, enforced.** Unclickable, unfocusable, out of the a11y tree |
| Focus trap | Yours to write (§17 B) | Free — a consequence of the inertness |
| Focus in / restore | Your effect, plus the `isConnected` check | `showModal()` in, `close()` back |
| Escape | Your keydown case | Fires `cancel`, then closes |

Note the third row especially. §05 C says `aria-modal` is a declaration rather than enforcement,
and this is the row where that stops being a footnote: a hand-rolled modal leaks to mouse users
and to Tab unless you also put `inert` on every sibling yourself. `showModal()` is the only way to
get real inertness without doing that.

**But the API is imperative, and three things follow.** They are the whole substance of the diff:

**1 — `<dialog open>` is not a modal.** The attribute gives you a *non-modal* dialog: no top layer,
no inertness, no backdrop, no Escape. Same trap with `.show()` versus `.showModal()`. So the
element renders closed and gets opened from an effect:

```tsx
useEffect(() => {
  const el = dialogRef.current
  el?.showModal()
  return () => el?.close()
}, [])
```

The cleanup is not tidiness. **`close()` is what restores focus**, and React runs effect cleanups
before removing the host node — so that one line is the difference between focus returning to the
trigger and falling to `<body>`. Note also what survived: mount/unmount is still the state machine,
so the query reset is still free, and there is still no reset effect.

**2 — Escape closes the DOM node behind React's back.** The browser fires `cancel` and then closes,
which leaves your state saying open while the page shows nothing — and a second Escape does
nothing at all, because the node is already closed. The fix is to refuse the browser's close and
let React drive it:

```tsx
onCancel={(event) => {
  event.preventDefault()
  onClose()
}}
```

One source of truth, and the unmount cleanup above does the actual closing.

**3 — There is no backdrop element to put a handler on.** `::backdrop` is a pseudo-element. A click
that lands on it is reported with *the dialog itself* as the target, so:

```tsx
onClick={(event) => {
  if (event.target === dialogRef.current) onClose()
}}
```

This is only reliable if the dialog has no padding or border of its own and the panel is a real
child covering it — otherwise a click on the dialog's own padding reads as a backdrop click. The
stylesheet does that work, which is a rare case of CSS being load-bearing for behaviour.

**What you also drop:** `role="dialog"` and `aria-modal` are both redundant on a modal `<dialog>`
and should not be re-added. You still supply `aria-label` yourself. And `onMouseDown` instead of
`onClick` on the options stays exactly as it was — blur still fires before click, and none of the
browser's focus handling touches that.

**The cost, and it is a real one: `<dialog>` is not testable in jsdom.** jsdom 30 ships
`HTMLDialogElement` with exactly one member on it — `open`. No `showModal`, no `close`, no `cancel`
event, no top layer. The runnable spec for this variant carries a ~25-line shim, and the shim can
only fake the bookkeeping:

> **Everything `<dialog>` gave you for free is the part you cannot assert on.** Inertness, the
> focus trap and the top layer are browser behaviours. They do not exist in jsdom, and no shim
> invents them.

So in a round where **test quality is a graded axis** — which is exactly the Cursor round — the
hand-rolled version has an argument the native one doesn't: you can test the focus management,
because you wrote it. That tension is worth saying out loud; it lands better than advocating for
either one.

**Which to reach for.**

| | |
|---|---|
| **Hand-rolled** | The interview, when focus management is the thing being examined. Anywhere the behaviour must be assertable in jsdom. |
| **`<dialog>`** | Production. Anywhere real inertness matters, which is every modal that isn't a toy. |

And note the line counts: 155 for the native variant against 201 for the reference, with the native
one also carrying Home/End and the live region. **The win is not brevity — it's correctness.** You
delete the portal, the focus effect, the Tab trap and the Escape case, and you get inertness that
the hand-rolled version cannot have at all. Say that rather than "it's shorter", which is the
version that doesn't survive a follow-up.

<details>
<summary>Complete implementation — Command palette on `<dialog>`</summary>

```tsx
import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent, MouseEvent } from 'react'

/**
 * THE NATIVE VARIANT of the command palette. Same API, same behaviour, same
 * markup below the dialog — and four whole concerns deleted, because the
 * browser owns them once you call showModal():
 *
 *   TOP LAYER      No portal. The dialog renders above the document regardless
 *                  of any ancestor's transform, overflow, or z-index.
 *   INERTNESS      Everything outside is genuinely unreachable — by pointer, by
 *                  Tab, and to assistive tech. `aria-modal` only *claimed* that.
 *   FOCUS TRAP     Free, as a consequence of inertness. No focusable-node
 *                  selector, no edge-wrapping Tab handler.
 *   FOCUS RESTORE  close() puts focus back where it was.
 *
 * What you pay for it is that the API is imperative, and three things follow
 * from that. They are marked (1) (2) (3) below, and they are the whole reason
 * this file is worth reading next to the hand-rolled one.
 */

export interface Command {
  id: string
  label: string
  group?: string
  keywords?: string[]
  run: () => void
}

export interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  commands: Command[]
  recentIds?: string[]
  placeholder?: string
  emptyMessage?: string
}

const NO_RECENTS: string[] = []

export function CommandPalette({ open, ...rest }: CommandPaletteProps) {
  // Still mount/unmount as the state machine, exactly like the hand-rolled
  // version — the query reset stays free. Note what ISN'T here: createPortal.
  // showModal() promotes the element into the top layer from wherever it sits,
  // so there is nothing left for a portal to solve.
  if (!open) return null
  return <Palette {...rest} />
}

function Palette({
  onClose,
  commands,
  recentIds = NO_RECENTS,
  placeholder = 'Type a command…',
  emptyMessage = 'No matching commands',
}: Omit<CommandPaletteProps, 'open'>) {
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)

  const dialogRef = useRef<HTMLDialogElement>(null)
  const baseId = useId()
  const listboxId = `${baseId}-listbox`
  const optionId = (index: number) => `${baseId}-option-${index}`

  // (1) The declarative-to-imperative bridge. A <dialog> rendered with the
  // `open` attribute is a NON-MODAL dialog: no top layer, no inertness, no
  // backdrop, no Escape. Only the showModal() call gets you any of it, so the
  // element is rendered closed and opened from an effect.
  //
  // The cleanup is not tidiness. close() is what restores focus, and React runs
  // effect cleanups before it removes the host node — so calling it here is the
  // difference between focus going back to the trigger and falling to <body>.
  useEffect(() => {
    const el = dialogRef.current
    el?.showModal()
    return () => el?.close()
  }, [])

  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) {
      const recents = recentIds
        .map((id) => commands.find((c) => c.id === id))
        .filter((c): c is Command => c !== undefined)
      const promoted = new Set(recents.map((c) => c.id))
      return [...recents, ...commands.filter((c) => !promoted.has(c.id))]
    }
    return commands.filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        (c.keywords ?? []).some((k) => k.toLowerCase().includes(q)),
    )
  }, [commands, query, recentIds])

  const activeIndex = results.length === 0 ? -1 : Math.min(cursor, results.length - 1)

  const run = useCallback(
    (command?: Command) => {
      if (!command) return
      onClose()
      command.run()
    },
    [onClose],
  )

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    const move = (delta: number) =>
      setCursor((i) => (Math.min(i, results.length - 1) + delta + results.length) % results.length)

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        if (results.length > 0) move(1)
        break
      case 'ArrowUp':
        event.preventDefault()
        if (results.length > 0) move(-1)
        break
      case 'Home':
        event.preventDefault()
        setCursor(0)
        break
      case 'End':
        event.preventDefault()
        setCursor(Math.max(0, results.length - 1))
        break
      case 'Enter':
        event.preventDefault()
        run(results[activeIndex])
        break
      // No Escape case, and no Tab case. The browser fires `cancel` for the
      // first and traps the second. See (2).
      default:
        break
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="cpd-dialog"
      aria-label="Command palette"
      // (2) Escape is the browser's, so it closes the DOM node without telling
      // React — and then state says open while the page shows nothing.
      // preventDefault stops that close and lets React drive it instead, which
      // keeps one source of truth. Drop this line and the palette "sticks" after
      // the first Escape.
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      // (3) There is no backdrop element to hang a handler on — ::backdrop is a
      // pseudo-element. A click that lands on the backdrop is reported with the
      // dialog itself as the target, which only works because the dialog has no
      // padding of its own and the panel below is a real child.
      onClick={(event: MouseEvent<HTMLDialogElement>) => {
        if (event.target === dialogRef.current) onClose()
      }}
    >
      <div className="cpd-panel">
        <input
          className="cpd-input"
          type="text"
          role="combobox"
          autoComplete="off"
          aria-expanded
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? optionId(activeIndex) : undefined}
          aria-label="Search commands"
          placeholder={placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setCursor(0)
          }}
          onKeyDown={handleKeyDown}
        />

        <div className="visually-hidden" role="status" aria-live="polite">
          {results.length === 0
            ? emptyMessage
            : `${results.length} command${results.length === 1 ? '' : 's'}`}
        </div>

        <ul id={listboxId} role="listbox" aria-label="Commands" className="cpd-list">
          {results.map((command, index) => (
            <li
              key={command.id}
              id={optionId(index)}
              role="option"
              aria-selected={index === activeIndex}
              className="cpd-option"
              // Unchanged from the hand-rolled version: blur still fires before
              // click, and the browser's focus handling does nothing about that.
              onMouseDown={(e) => {
                e.preventDefault()
                run(command)
              }}
              onMouseEnter={() => setCursor(index)}
            >
              <span>{command.label}</span>
              {command.group && <span className="cpd-group">{command.group}</span>}
            </li>
          ))}
        </ul>

        {results.length === 0 && (
          <p className="cpd-empty" aria-hidden="true">
            {emptyMessage}
          </p>
        )}
      </div>
    </dialog>
  )
}
```

</details>

## 13 — Virtualized list

> Runnable: none yet — the only section without an exercise on disk. The §E implementation is
> self-contained and typechecked; build against §G and point your own spec at it.

### A. ASKED AS

- "How would you render a hundred thousand rows?"
- "This list janks at five thousand items — fix it"
- "Build a log viewer" / "a message list that scrolls back a million lines"
- As the scale follow-up to §11 Data table, far more often than as its own prompt

**Read that list again: three of the four are questions, not builds.** This is the component you
are most likely to be asked to *describe* and least likely to be asked to write. §17 H gives the
sentence; this section is so that the sentence is backed by something.

### B. API

```tsx
export interface VirtualListProps<T> {
  items: T[]
  rowHeight: number
  height: number
  label: string
  renderRow: (item: T, index: number) => ReactNode
  getRowKey: (item: T, index: number) => string
  overscan?: number
  onVisibleRangeChange?: (start: number, end: number) => void
}
```

**Four calls worth stating out loud:**

- **`rowHeight` is required, fixed, and the whole component rests on it.** Every number here is
  `index × rowHeight`. Say the constraint when you write the prop rather than when you're caught:
  *"this assumes a fixed row height; variable heights need measured offsets and a prefix-sum
  index, which is where I'd reach for a library."*
- **`height` is a number, not "fill the parent".** The math needs the viewport height during
  render, and getting it from the DOM means a layout read plus a `ResizeObserver` plus a first
  paint with nothing in it. Taking it as a prop is the honest version; name the ResizeObserver as
  what you'd add for a responsive container.
- **`getRowKey`, not the array index.** This is not the usual React-key advice — see §F. In a
  windowed list an index key is actively wrong, because rows are recycled.
- **`onVisibleRangeChange` is the prefetch hook**, and it is the only thing separating this from a
  toy. It's what a real list uses to fetch the pages it's about to scroll into. Like `fetchOptions`
  in §06 it must be referentially stable — it's an effect dependency.

Deliberately absent: a `scrollToIndex` imperative handle. It's the first thing a production list
adds, it needs `useImperativeHandle` plus a ref to the viewport, and naming it is cheaper than
building it.

### C. SEMANTICS

Windowing is the one technique in this guide that **removes information from the page**, so its
accessibility story is not a wiring checklist — it's a set of things that genuinely stop working,
and the grade is in whether you say so.

| Element | Required |
|---|---|
| Viewport | `role="list"`, accessible name, **`tabIndex={0}`** |
| Spacer and window wrappers | `role="presentation"` |
| Row | `role="listitem"`, `aria-setsize` = the **real** count, `aria-posinset` = the **absolute** index |

**`aria-setsize` / `aria-posinset` is the whole point.** Assistive tech counts what is in the DOM,
so it will announce "row 3 of 20" about a hundred thousand rows — confidently, and wrongly. These
two attributes are ARIA's mechanism for exactly this: *the DOM holds a window onto a larger set.*

§17 H names the grid form of the same idea — `aria-rowcount` on the container and `aria-rowindex`
per row. Both are correct; pick by what the thing is. A flat list gets set-size and position-in-set;
a windowed **table** (§11 at scale) gets row-count and row-index.

**`tabIndex={0}` on the viewport is not optional.** Firefox makes scrollable containers focusable
on its own; Chrome does not. Without it there is no way for a keyboard user to scroll the list at
all — and it's a scroll container, so once it can take focus the browser gives you Arrow keys,
PageUp/PageDown, Home and End for free. That is the entire keyboard contract, which is why there
is no key table in this section.

**`role="presentation"` on the two wrappers.** `role="list"` requires its `listitem`s to be owned
by it, and an intervening element with an implicit generic role breaks that ownership. The spacer
and the translated window are pure geometry, so say so.

**What windowing costs, in the order an interviewer cares:** Ctrl+F finds nothing outside the
window; screen-reader browse mode can only walk what's rendered; the browser's scroll anchoring
and `:target` navigation stop working; and printing produces one screen of rows. None of these
have fixes — they are the price. Naming them is what separates *"I'd virtualize"* from *"I'd
virtualize, and here's what it costs."*

### D. DECISIONS THAT MATTER

1. **The first decision is not to.** DOM nodes get expensive in the low thousands; below that,
   windowing takes away find-in-page and buys nothing. And before reaching for it, `content-visibility:
   auto` with `contain-intrinsic-size` skips rendering off-screen subtrees with no JavaScript at
   all — and unlike windowing, the nodes are still there, so Ctrl+F still works. → *"First I'd check
   whether it's the node count or a re-render problem, then try `content-visibility`, and only
   window if the node count is genuinely the bottleneck."*
2. **The scroll position is not state; the first visible index is.** Storing `scrollTop` re-renders
   at scroll frequency to produce identical output — it reintroduces the exact cost windowing was
   meant to remove. Store the row index, and only write it when it changes. That one `if` is the
   optimization.
3. **Spacer plus transform, not layout.** A full-height spacer makes the scrollbar honest; an
   absolutely-positioned, translated window puts the rows in place without touching layout. A
   `margin-top` or a `top` value would reflow on every row boundary.
4. **Focus dies when a row scrolls out, and this component does not fix it.** Window a list of
   buttons, Tab into row 4, scroll — the focused node unmounts, focus falls to `<body>`, and the
   keyboard user is back at the top of the page. Real fixes are keeping the focused row rendered
   outside the window, or restoring focus by key on the way back. → *"Interactive rows plus
   windowing is a focus problem, not a rendering one. I'd pin the focused row into the render
   window."* Saying this unprompted is the single strongest thing available in this section.
5. **Keys come from the data.** Covered in §F because it's a trap, but it is decided here.

### E. IMPLEMENTATION

**1 — The window is four lines of arithmetic, and none of it is stored.**

```tsx
const visibleCount = Math.ceil(height / rowHeight) + 1
const maxStart = Math.max(0, items.length - visibleCount)
const start = Math.min(firstVisible, maxStart)
const from = Math.max(0, start - overscan)
const to = Math.min(items.length, start + visibleCount + overscan)
```

The `+ 1` is for the row the viewport is showing half of; without it, `overscan={0}` leaves a blank
strip at the bottom edge. The `maxStart` clamp is there because `items` is a prop and can shrink
under a scroll position already past the new end — the browser clamps `scrollTop` itself and fires
a scroll event, but the render in between would slice past the array. Same instinct as the cursor
clamp in §12 E: if it can be computed, compute it.

**2 — The guard is the optimization.**

```tsx
function handleScroll(event: UIEvent<HTMLDivElement>) {
  const next = Math.floor(event.currentTarget.scrollTop / rowHeight)
  if (next !== firstVisible) setFirstVisible(next)
}
```

Scroll fires at frame rate. The rendered window only changes when you cross a row boundary, so
that's the only time to write state. Drop the `if` and you re-render sixty times a second to
produce byte-identical output — and you will have written a virtualized list that is slower than
the naive one it replaced.

Note also what's *not* here: no `scrollHeight` or `getBoundingClientRect` read. Both force layout,
and a forced layout inside a scroll handler is the classic way to make scrolling jank.

**3 — Spacer, then a translated window.**

```tsx
<div role="presentation" style={{ position: 'relative', height: items.length * rowHeight }}>
  <div
    role="presentation"
    style={{ position: 'absolute', top: 0, left: 0, right: 0,
             transform: `translateY(${from * rowHeight}px)` }}
  >
    {/* rows */}
  </div>
</div>
```

The spacer's height is the *whole* list, which is what makes the scrollbar the right size and the
scroll distance real. The window is out of flow and translated into place, so moving it composites
instead of reflowing.

One thing worth checking rather than assuming: a transform can extend an element's scrollable
overflow area. It doesn't here, because the translated block's bottom edge is `to * rowHeight`, and
`to` is clamped to `items.length` — so it is never below the spacer's own bottom.

**4 — THE WHOLE THING.**

<details>
<summary>Complete implementation — Virtualized list</summary>

```tsx
import { useEffect, useState } from 'react'
import type { ReactNode, UIEvent } from 'react'

/**
 * Three things carry this component, and the first is the one that gets graded:
 *
 * 1. KNOW WHEN NOT TO REACH FOR IT. Windowing costs find-in-page, Ctrl+F,
 *    scroll anchoring, and screen-reader browse mode. Below a few thousand rows
 *    it buys nothing and takes all of that away.
 *
 * 2. THE WINDOW IS DERIVED, THE SCROLL POSITION IS NOT STATE. What lives in
 *    state is one integer — the first visible index — and it is only written
 *    when it actually changes. Storing scrollTop re-renders at scroll frequency,
 *    which is the exact cost windowing was supposed to remove.
 *
 * 3. THE DOM NO LONGER HOLDS THE LIST. Assistive tech is counting what it can
 *    see, so it will say "3 of 12" about a hundred thousand rows unless you tell
 *    it otherwise. That is what aria-setsize and aria-posinset are for.
 */

export interface VirtualListProps<T> {
  items: T[]
  /** Fixed, and required. Variable heights need measurement — see the note in §D. */
  rowHeight: number
  /** Viewport height. A number, not "fill the parent" — see §B. */
  height: number
  /** Accessible name for the list. */
  label: string
  renderRow: (item: T, index: number) => ReactNode
  /** Never the array index — see §F. */
  getRowKey: (item: T, index: number) => string
  /** Rows rendered beyond each edge, so a fast scroll doesn't show blank. */
  overscan?: number
  /** Fires when the window moves. The hook a real list prefetches from. */
  onVisibleRangeChange?: (start: number, end: number) => void
}

export function VirtualList<T>({
  items,
  rowHeight,
  height,
  label,
  renderRow,
  getRowKey,
  overscan = 3,
  onVisibleRangeChange,
}: VirtualListProps<T>) {
  // The only state in the component: the first visible row's index. Not scrollTop —
  // that would re-render on every scroll event rather than every row boundary.
  const [firstVisible, setFirstVisible] = useState(0)

  // +1 because a viewport scrolled to a fraction of a row shows part of one more.
  // Without it, overscan={0} leaves a blank strip at the bottom edge.
  const visibleCount = Math.ceil(height / rowHeight) + 1

  // Derived, not corrected in an effect. `items` is a prop and can shrink under a
  // scroll position that is already past the new end — the browser clamps scrollTop
  // itself and fires a scroll event, but the render in between would slice past the
  // array and render nothing. Same instinct as the cursor clamp in §12 E.
  const maxStart = Math.max(0, items.length - visibleCount)
  const start = Math.min(firstVisible, maxStart)

  const from = Math.max(0, start - overscan)
  const to = Math.min(items.length, start + visibleCount + overscan)

  function handleScroll(event: UIEvent<HTMLDivElement>) {
    const next = Math.floor(event.currentTarget.scrollTop / rowHeight)
    // The guard IS the optimization. Scroll fires at frame rate; the rendered window
    // only changes when you cross a row boundary, so that is the only time to write
    // state. Drop this line and you re-render 60 times a second to produce identical
    // output.
    if (next !== firstVisible) setFirstVisible(next)
  }

  useEffect(() => {
    onVisibleRangeChange?.(from, to)
  }, [from, to, onVisibleRangeChange])

  return (
    <div
      className="vlist-viewport"
      style={{ height, overflowY: 'auto' }}
      onScroll={handleScroll}
      // A scrollable div is NOT keyboard-scrollable in Chrome unless it can take
      // focus. Firefox does it for you; Chrome does not, and the result is a list
      // a keyboard user cannot move at all. One attribute, and it is a real bug.
      tabIndex={0}
      role="list"
      aria-label={label}
    >
      {/* The spacer. Its height is the WHOLE list, which is what makes the scrollbar
          the right size and the scroll distance real. */}
      <div
        role="presentation"
        className="vlist-spacer"
        style={{ position: 'relative', height: items.length * rowHeight }}
      >
        {/* Out of flow and translated into place. Absolute + transform rather than a
            margin or a `top` value: both of those are layout, and this runs on every
            row boundary. The translated block's bottom edge is `to * rowHeight`,
            which is <= the spacer height by construction, so it never extends the
            scrollable area.

            role="presentation" on both wrappers is not decoration. role="list"
            requires its listitems to be owned by it, and an intervening element with
            an implicit generic role breaks that ownership. */}
        <div
          role="presentation"
          className="vlist-window"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            transform: `translateY(${from * rowHeight}px)`,
          }}
        >
          {items.slice(from, to).map((item, i) => {
            const index = from + i
            return (
              <div
                // Never the array index. Rows are recycled as you scroll, so an index
                // key makes React reuse row 0's DOM node for whatever is now at the
                // top — carrying its focus, its scroll position, and any uncontrolled
                // input state to a different item.
                key={getRowKey(item, index)}
                role="listitem"
                className="vlist-row"
                // The DOM holds a window; these two say how big the real set is and
                // where this row sits in it. Without them AT announces "1 of 20" for
                // a hundred thousand rows, which is worse than saying nothing.
                aria-setsize={items.length}
                aria-posinset={index + 1}
                style={{ height: rowHeight }}
              >
                {renderRow(item, index)}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

</details>

### F. TRAPS

| Trap | Symptom |
|---|---|
| `key={index}` | Rows are recycled, so row 0's DOM node is reused for a different item — its focus, its caret, and any uncontrolled input state go with it |
| `scrollTop` in state | A re-render per scroll event; slower than the unvirtualized list |
| No spacer | The scrollbar reflects one screen; you can't scroll to the end |
| Offsetting with `margin-top` or `top` | Reflow on every row boundary instead of a composited transform |
| Reading `scrollHeight` in the scroll handler | Forced layout per event — the jank you were removing |
| Viewport without `tabIndex={0}` | Chrome gives keyboard users no way to scroll it |
| Generic `div`s between list and listitems | The list/listitem ownership breaks; AT stops reporting it as a list |
| `aria-setsize` from the rendered slice | "Row 3 of 20" for a hundred thousand rows — confident and wrong |
| `overscan={0}` | A blank strip at the leading edge on fast scroll |
| Fixed `rowHeight` against variable content | Rows overlap or leave gaps, and the gaps grow with scroll distance |
| Interactive rows | Focus falls to `<body>` the moment the focused row scrolls out (§D 4) |
| Windowing a list of 300 rows | You paid the whole accessibility cost for nothing measurable |

### G. SPEC

**Windowing** — renders the window plus overscan, never all of `items` · scrolling swaps which
items are rendered · the spacer's height is `items.length × rowHeight` · the rendered block's
offset matches the first rendered index · `overscan` renders beyond both edges

**Edges** — an empty list renders nothing and does not throw · a list shorter than the viewport
renders every row · shrinking `items` under a scrolled window clamps instead of rendering blank ·
scrolling to the very end shows the last row flush with the bottom

**Semantics** — `aria-setsize` is the full count, not the rendered count · `aria-posinset` is the
absolute index · the viewport is focusable · rows keep their identity across a scroll (assert on a
row's DOM node, not its text)

**Cheap and worth writing:** render 10,000 items and assert the DOM node count is under 50. That
single test is the whole component's reason to exist, and it reads as someone who tests outcomes
rather than internals.

### H. INTERVIEW SCOPE

**Reference: 78 lines of code — second only to the Tooltip's 62, and comfortably a round's worth
of typing.** There is no separate cut, and that is not because it's easy.

This section's §H is different from every other one, because the highest-scoring answer here is
usually not to build it at all:

> *"Past a few thousand rows I'd virtualize — render only the visible window plus a small overscan,
> with a spacer preserving the scroll height. It costs find-in-page and screen-reader browse mode,
> so I'd check first whether the bottleneck is really the node count. In production I'd use
> TanStack Virtual rather than hand-rolling it."*

That is thirty seconds, it demonstrates everything §D 1 is about, and it is very often the whole
expected answer. Reaching for the keyboard when that sentence was what was wanted is a way to lose
ten minutes and look like you can't judge scope.

**Build it when:** you're asked to explicitly, the prompt *is* the log viewer, or you've named the
sentence above and the interviewer says "go on".

**Then the core is:**

- The five lines of arithmetic, including the clamp
- The `if (next !== firstVisible)` guard — mention that this is the optimization
- Spacer at full height, window absolutely positioned and translated
- `getRowKey` from the data
- `aria-setsize` / `aria-posinset`, and `tabIndex={0}` on the viewport

**Cut, and say so:**

| Drop | Say |
|---|---|
| `overscan` | "Render one extra row past each edge, or you get a blank strip on a fast scroll. One line, and I'd hardcode it to 3." |
| `onVisibleRangeChange` | "This is where a real list hangs prefetching for the pages it's about to reach." |
| `role="presentation"` on the wrappers | "Needed, or the list/listitem ownership breaks. Two attributes." |
| Generic `<T>` | "Concrete row type here; I'd make it generic in a library." |
| A `scrollToIndex` handle | "useImperativeHandle plus a viewport ref — first thing a production list adds." |

**Do not cut** the clamp or the scroll guard. Without the guard the component is slower than doing
nothing, which is the one outcome worse than not attempting it.

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
5. **Key the Stop/Send swap.** Both branches render a `<button>` in the same slot, so React reuses
   the DOM node and rewrites `type="button"` into `type="submit"` in place. Click is a discrete
   event, so that re-render flushes *during* the click, and activation behavior — evaluated after
   dispatch — reads the new type and submits the form. Stop aborts and instantly re-sends.
   Distinct `key`s force a fresh node. `type="button"` alone does not save you, and jsdom does not
   reproduce it, so the test suite stays green while the page is broken.

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
        {/* The keys are load-bearing. Without them React sees <button> in the same
            slot both times and REUSES the DOM node, rewriting type="button" into
            type="submit" while the browser is still mid-click. Activation behavior
            runs after dispatch, so the browser reads the new type and submits the
            form — Stop aborts and instantly re-sends. */}
        {busy ? (
          <button key="stop" type="button" className="stream-stop" onClick={stop}>
            Stop
          </button>
        ) : (
          <button key="send" type="submit" className="stream-send" disabled={!prompt.trim()}>
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
| Unkeyed Stop/Send swap in a form | Stop aborts, then the form submits and it re-sends immediately |
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

### H. INTERVIEW SCOPE

**Reference: 107 lines of code**, unchanged as the target — the collapsible is at the end of this
section.

**Core:**

- An `AbortController` **and** a generation counter — same two guards as Combobox, same reason
- `stop()` bumps the generation *before* aborting, so a token already in flight can't land
- Abort on unmount
- Retry and supersede both routed through one `run()`, so there's a single place where a stream
  can start

**The counter-intuitive one, and the reason this gets asked:** `aria-live` on a streaming message
is **wrong**. A polite region re-announces on every mutation, so a token-by-token stream produces
a stutter of partial words. Announce once when the message completes instead.

Saying that unprompted is worth more than the rest of the component put together — it's the
difference between having used a screen reader and having read about ARIA.

**Cut, and say so:**

| Drop | Say |
|---|---|
| Token batching / rAF coalescing | "One setState per token is fine up to a point; past that you batch into animation frames." |
| Markdown rendering mid-stream | "Needs an incremental parser — partial fences break naive renderers." |
| Scroll-anchoring at the bottom | "Stick to the bottom unless the user has scrolled up." |

<details>
<summary>The interview target — StreamingMessage (identical to the reference above)</summary>

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
        {/* The keys are load-bearing. Without them React sees <button> in the same
            slot both times and REUSES the DOM node, rewriting type="button" into
            type="submit" while the browser is still mid-click. Activation behavior
            runs after dispatch, so the browser reads the new type and submits the
            form — Stop aborts and instantly re-sends. */}
        {busy ? (
          <button key="stop" type="button" className="stream-stop" onClick={stop}>
            Stop
          </button>
        ) : (
          <button key="send" type="submit" className="stream-send" disabled={!prompt.trim()}>
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

### H. INTERVIEW SCOPE

**Reference: 106 lines of code**, unchanged as the target — the collapsible is at the end of this
section.

**Core, and it's mostly WCAG rather than code:**

- **WCAG 2.2.2 (Pause, Stop, Hide)** — anything auto-advancing for more than five seconds needs a
  pause control. The single most-missed requirement, and the most likely to be probed.
- Pause on hover *and* on focus, composed so neither clobbers an explicit user pause
- `prefers-reduced-motion` disables auto-rotation entirely — seeded with a lazy `useState`
  initializer, or you render one frame of motion before the effect catches up
- `aria-live` off while auto-rotating, polite once the user drives it. Announcing every
  auto-advance is noise that looks like thoroughness.
- Slide labelling — "3 of 7", each slide named

**Cut, and say so:**

| Drop | Say |
|---|---|
| The slide transition itself | "A translated track with a transition — and it'd be behind a reduced-motion guard, which is why I left it as a cut." |
| Infinite looping | "Clone the first and last slides, then jump back with the transition disabled on `transitionend`." |
| Touch / swipe | "Pointer events plus a velocity threshold." |
| Lazy-loading slide images | "`loading="lazy"` past the first slide." |

A carousel that slides beautifully but can't be paused scores below a hard-cut one with a pause
button. Get the state machine right first, then say what you'd animate.

<details>
<summary>The interview target — Carousel (identical to the reference above)</summary>

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

### H. INTERVIEW SCOPE

**Reference: 113 lines of code**, unchanged as the target — the collapsible is at the end of this
section.

**Core:**

- **Two-phase validation**: validate on blur, then on every keystroke *once a field has erred*.
  Validating while someone first types their email is hostile; not clearing the error until they
  tab away again is worse.
- A real `<label>` per input — placeholder-as-label fails as soon as there's text in the field
- `aria-invalid` and `aria-describedby` pointing at the error, and only while it exists
- `preventDefault()` before the await
- Focus the first invalid field on a rejected submit — otherwise a keyboard user gets a rejection
  and no idea where to look
- Disable the submit while in flight, so a double-click can't submit twice
- Keep the values on a server error

**Cut, and say so:**

| Drop | Say |
|---|---|
| Cross-field validation | "The validator takes all values, so confirm-password compares against them." |
| A schema library | "Zod or Valibot in production — this is the same shape, hand-rolled." |
| Async / server-side field validation | "Debounced, with the same race guards as the combobox." |
| Dirty tracking, unsaved-changes prompt | "Compare against the initial values." |

If the prompt says "contact form", the two-phase validation timing *is* the question. Everything
else is scaffolding.

<details>
<summary>The interview target — Form (identical to the reference above)</summary>

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

## 17 — Techniques

The reusable primitives. Every component in §03–16 is an assembly of these.

§N and §O are the exception: they are not DOM techniques at all. They are here because the
component rounds at AI companies have started handing out **modules** — a streaming tokenizer, a
content hash — graded on the same three axes, and both of those questions are won or lost on a
primitive that no amount of React practice teaches.

**§P–R are the ones people forget rather than the ones people cannot do:** scrolling the active
item into view, keeping a callback current without re-subscribing, and coalescing updates that
arrive faster than the screen refreshes.

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

**The handler.** This is the reusable half — the same twelve lines serve a tablist, a toolbar, a
radio group and a carousel, and they are what the four components in this guide differ *around*
rather than differ *in*.

```tsx
// Derive the key names from orientation, and feed aria-orientation from the same
// variable — then the announced orientation cannot disagree with the actual keys.
const nextKey = orientation === 'horizontal' ? 'ArrowRight' : 'ArrowDown'
const prevKey = orientation === 'horizontal' ? 'ArrowLeft' : 'ArrowUp'

function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
  const current = items.findIndex((item) => item.value === active)
  let next: number

  switch (event.key) {
    case nextKey: next = (current + 1) % items.length; break
    case prevKey: next = (current - 1 + items.length) % items.length; break
    case 'Home':  next = 0; break
    case 'End':   next = items.length - 1; break
    default: return                     // everything else must reach the browser
  }

  event.preventDefault()
  move(next)                            // moves the 0 and calls .focus() together
}
```

**`default: return` before any `preventDefault()`.** This is the line that decides whether the
widget is usable. Calling `preventDefault()` once at the top of the handler — which is what
happens when you write the arrow cases first and tidy up later — swallows Tab, first-letter
typeahead, and every browser and screen-reader shortcut that reaches this element. The handler
must be transparent to every key it does not implement.

**`preventDefault()` on the keys you did handle, though.** Arrows scroll the page, and Home/End
jump to the top and bottom of the document. Without it the widget works *and* the page moves
underneath it.

**`+ items.length` before the modulo,** because `-1 % 3` is `-1` in JavaScript, not `2`. The
version without it silently fails only at the first item, which is exactly the case nobody
demos.

**`event.key`, not `event.code`.** `code` is the physical key position, so the numpad arrows
arrive as `Numpad4` / `Numpad8` and fall through to `default`.

**Compute `current` from your own state, not from `document.activeElement`.** The state is what
renders `tabIndex={0}`, so reading anything else lets the two drift — and `activeElement` may be
a child of the item rather than the item itself.

**The four axes it varies on.** Everything above is fixed; this is the part you re-derive per
widget, and it is worth having the table in your head because interviewers probe exactly here:

| Axis | Tabs (§03), toolbar, radio group | Menu (§07) | Tree (§10) |
|---|---|---|---|
| Wrap at the ends? | Yes | Yes | **No** — clamp with `Math.min`/`Math.max` |
| What do Left/Right do? | The navigation axis itself | Close / open a submenu | Collapse / expand, then step out / in |
| Does selection follow focus? | Yes | No — Enter commits | No — Enter activates |
| Extra keys | — | First-letter typeahead (§07 E), Escape | Enter/Space toggles a folder, selects a leaf |

**"Selection follows focus" is a spec question, not a taste one.** For tabs and radio groups APG
says arrowing should select as it moves — that's *automatic activation*, and it's what makes a
radio group behave the way users expect. The exception is when showing the new panel is expensive
(a fetch, a heavy render): then switch to *manual activation*, where arrows move focus only and
Enter or Space selects. Name which one you picked and why — *"automatic activation, since these
panels are already rendered; I'd switch to manual if selecting one triggered a fetch."*

**Packaging.** This generalizes cleanly into a `useRovingTabIndex({ count, orientation, wrap })`
returning `{ activeIndex, getItemProps, onKeyDown }`. Worth *naming* in a round — it shows you see
the pattern rather than the instance — but not worth building unless you're asked for a library,
because the per-widget axes above end up as options anyway and the indirection stops paying.

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

**What this is for.** One component (§13 Virtualized list, which assembles all of this) and one
interview question: *"how would you render a hundred thousand rows?"* Nothing else in this guide
uses it.

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

### M. KEY HANDLERS: WHERE TO ATTACH THEM

**The rule.** Attach a key handler to whatever *owns* the behaviour, and there are exactly three
scopes:

| Scope | Attach to | Example |
|---|---|---|
| The widget's own keys | the focused element itself | Arrows and Enter on a combobox input (§06, §12) |
| The layer's keys | `document` | Escape to dismiss a modal or palette |
| The app's keys | `window` | ⌘K to open the palette |

Getting this wrong doesn't usually produce a bug you can see. It produces keys that work until they
don't.

**The pitfall: a handler on a non-focusable container only fires while a descendant has focus.**

```tsx
<div className="panel" onKeyDown={handleKeyDown}>   {/* ← the bug */}
  <input />                                          {/* the only focusable node */}
</div>
```

Keydown is delivered to `document.activeElement` and bubbles from there. A `<div>` can't hold
focus, so this handler is alive exactly as long as the input is focused. Click any dead space
inside the panel — the gap between rows, a `<span>`, the panel itself — and focus falls to
`<body>`, which is **not** a descendant of the panel. Every key silently stops working. No error,
no warning; the shortcuts just cease to exist.

This is not a theoretical failure. Headless UI moved its Dialog's Escape handler from a global
listener onto the Dialog element to fix nested dialogs, shipped it, and reverted:

> *"escape would not close if you click on a non-focusable element like a span in the Dialog … this
> PR reverts to the 'global' window event listener so that we can still catch all of the escape
> keydown events."*

Radix reaches the same place from the other direction: `useEscapeKeydown` attaches to the
document, and `DismissableLayer` is a separate concern from the widget inside it. `cmdk` handles
list navigation on its own root but explicitly does **not** own escape-to-close — you wrap it in a
dialog primitive for that.

**Two ways out, and the choice is a real trade — §05 and §12 make it differently on purpose:**

1. **Guarantee focus can't leave, and keep the handler on the container.** `tabIndex={-1}` makes
   the container focusable *by click and script* while keeping it out of the Tab order, so a click
   on dead space focuses the container — still inside the handler's subtree. Pair it with
   `onMouseDown` + `preventDefault()` on the rows so clicking one doesn't drop the caret either.
   **Nesting then works for free:** the innermost dialog's handler runs first and
   `stopPropagation()` keeps the outer one out of it. This is §05's Modal, and it is only safe
   because that component also has a real focus trap.
2. **Move dismissal to the document.** Focus-independent, and correct even when the surface has no
   reliable focus story. The cost is that **every open layer hears the same Escape** — §05 F lists
   exactly this as a trap — so past one dialog you need a layer stack to decide which acts. That's
   what Radix built `DismissableLayer` for.

**The rule that reconciles them:** a container handler is correct *if and only if* you guarantee
focus stays inside it. §05 does, with `tabIndex={-1}` plus a trap. A palette built without either
does not, which is why §12's Escape belongs on the document until it grows a trap of its own.

Native `<dialog>` sidesteps the whole question: the browser fires `cancel` **at the element**, so
nothing depends on the propagation path (§12 I).

**`window` vs `document`.** Keydown bubbles `target → … → document → window`, so a `window`
listener sees everything a `document` listener does. Three things separate them:

- **A synthetic event dispatched *directly* on `window` never passes through `document`.** Its
  propagation path is just `window`. This bites in tests: `fireEvent.keyDown(window, …)` will not
  reach a `document` listener. Dispatch on `document.body` if you want the test to be agnostic.
- **Use `ownerDocument`, not the global `document`,** when the element may be portalled into
  another window. Radix changed `DismissableLayer` for exactly this.
- **Capture phase wins over `stopPropagation`.** Radix listens with `{ capture: true }` so a
  dismissal still fires even when something inside swallowed the event on the way up. It also
  means every open layer hears the same Escape, which is why they keep a layer stack so only the
  innermost acts — and it has caused real compatibility complaints. At one dialog you don't care;
  know the failure mode exists before you add a second.

**Modifier keys, and the cross-platform shape.**

```tsx
useEffect(() => {
  function onKeyDown(e: globalThis.KeyboardEvent) {
    if (e.key.toLowerCase() !== 'k') return
    if (!e.metaKey && !e.ctrlKey) return       // ⌘ on macOS, Ctrl everywhere else
    e.preventDefault()                          // Chrome's Ctrl-K focuses the omnibox
    onTrigger()
  }
  window.addEventListener('keydown', onKeyDown)
  return () => window.removeEventListener('keydown', onKeyDown)
}, [onTrigger])
```

Five things in nine lines, and each is a question you can be asked:

| | |
|---|---|
| `metaKey \|\| ctrlKey` | Accept both rather than sniffing the platform. `metaKey` is ⌘ on macOS and the Windows key elsewhere; `ctrlKey` is Ctrl everywhere. Checking both is one condition instead of a `navigator` branch that goes stale. |
| `.toLowerCase()` | `e.key` is the **character produced**, so Shift changes it — ⇧⌘K arrives as `'K'`. Without this, the shortcut silently misses whenever Shift is held. |
| `preventDefault()` | Browsers already own a lot of combos. Skip it and the palette opens *and* focus jumps to the address bar. |
| The cleanup | Without it every unmount leaves a listener holding a stale closure, and they accumulate. |
| `globalThis.KeyboardEvent` | If the file also does `import type { KeyboardEvent } from 'react'`, that shadows the DOM type for the whole module — and React's synthetic event is a different type. Reach past the shadow, or alias the React import. |

**`e.key` or `e.code`?** `key` is the character produced — layout- and modifier-dependent, and what
you want for shortcuts and for text. `code` is the physical key position, unaffected by layout,
which is what you want for WASD-style controls and what you must *not* use for a combobox, since
the numpad arrows arrive as `Numpad4` / `Numpad8` (§17 A).

**One more, for any key handler on a text input: don't act while an IME is composing.** Typing
Japanese, Chinese or Korean routes Enter to the candidate picker, not to you. Handle it anyway and
you run a command when the user was only confirming a character:

```tsx
if (event.nativeEvent.isComposing) return
```

Nothing in this guide's specs covers it and jsdom won't reproduce it. Naming it unprompted while
building a combobox is worth more than most of the code around it.

### N. INCREMENTAL PARSING ACROSS A CHUNK BOUNDARY

**Problem.** Data arrives in chunks you do not control — SSE frames, a `ReadableStream`, a
WebSocket, a paste handler fed a megabyte at a time — and the thing you are looking for is longer
than one character. A delimiter will eventually be split across the boundary, and the naive
`chunk.split('```')` is wrong on exactly that chunk, intermittently, in production only.

**The rule: a chunk that ends mid-delimiter has decided nothing.** Hold the ambiguous tail, emit
everything before it, and let the next chunk resolve it. The tail is the *carry buffer*, and the
whole technique is keeping it bounded.

```ts
// The state machine's entire state. Four scalars — which is also why it
// serialises, which is the answer to "make it resumable after a restart".
type State = 'text' | 'inline' | 'info' | 'fence'
let state: State = 'text'
let ticks = 0     // backticks seen but not yet interpretable — NEVER stored as text
let buf = ''      // content of the token being accumulated

function feed(chunk: string): Token[] {
  out = []
  for (const ch of chunk) consume(ch)
  flush()         // emit what is now certain; keep `ticks` pending
  return out
}
```

Three properties to state out loud, because they are what separates this from a `split()`:

1. **The pending state is bounded by the DELIMITER, not by the DOCUMENT.** Two characters, forever,
   no matter how big the stream. *"How do you prevent unbounded buffering?"* is the follow-up in
   every version of this question, and this sentence is the answer.
2. **Hold the run as a count, not as a string.** A count cannot be accidentally emitted, and it is
   what makes the resolution rules readable: reach three and it is a fence, stop short and it is
   literal.
3. **There must be a `finish()`.** End-of-stream is a real event with real decisions in it —
   an unterminated fence closes (it runs to end of document), an unterminated span downgrades to
   text (an unmatched delimiter is just a character). Pick, then say why.

**Emit granularity is an API decision, so make it deliberately.** Short constructs — an inline code
span — can be emitted whole. Long ones cannot: a fenced block may be an entire file, so it emits
`open` / N × `chunk` / `close` and the renderer can paint a half-arrived code block. Buffering the
fence until it closes is the easy version and it reintroduces the unbounded buffer you just
eliminated.

**Where it shows up.** Streaming Markdown in a chat panel (§14, and drill
`cursor-11-streaming-markdown`); SSE frame reassembly, where the delimiter is `\n\n`; any
`TextDecoder` over a byte stream, where a multi-byte UTF-8 character splits across chunks and
`decoder.decode(chunk, { stream: true })` is the built-in that already does exactly this for you —
naming that built-in is a cheap point.

**This is a different layer from speculative rendering.** The tokenizer decides *what the bytes
mean*; the renderer decides *what to paint before the construct is complete* — closing an open
fence speculatively so a code block does not flicker into existence. Both are needed and they are
not substitutes.

**Testing it is the differentiator, and it is one loop.** Do not hand-pick three split points —
assert the invariant directly: *chunking must not be observable*.

```ts
const doc = 'a `b` c\n```\nx`y\n``` z'
const whole = run([doc])
for (let i = 0; i <= doc.length; i++) {
  expect(run([doc.slice(0, i), doc.slice(i)]), `split after ${i}`).toEqual(whole)
}
```

### O. UNAMBIGUOUS ENCODING: DOMAIN SEPARATION AND LENGTH PREFIXES

**Problem.** You are turning structured data into one string or one byte stream — a cache key, a
`key` prop, an ETag, a content hash, a localStorage name, a dedupe set. Concatenation loses the
boundaries, and two different inputs collide.

```ts
const key = `${userId}:${query}`          // user "1", query "2:3"  ==  user "1:2", query "3"
const key = names.sort().join('')         // {"a","bc"}             ==  {"ab","c"}
```

Both are real bugs, both are invisible until the day two users see each other's cached results.
There are exactly two rules.

**1. Domain separation — the type goes inside the value.** An empty file and an empty directory are
different things; if the tag is not in the hash, they are the same 32 bytes. Prefix each kind with
its own tag: `file\0…`, `dir\0…`, `link\0…`.

**2. Length prefixes — every variable-length field carries its own length.** Then the boundaries
are recoverable from the encoding, which is the property you actually need. Fixed-length fields
(a hex digest, a UUID) do not need one; anything a user can name does.

```ts
// A directory record: nothing here can be reparsed two ways.
hash(
  'dir\0', u32(children.length),
  ...children                                    // sorted by raw NAME BYTES,
    .sort(byUtf8Bytes)                           // not by JS `<`, which is UTF-16 order
    .flatMap(c => [u32(c.name.length), c.name, KIND[c.kind], u32(c.hash.length), c.hash]),
)
```

**The two-sentence version for an interview:** *"I'll domain-separate so a file and a directory
can't collide, and length-prefix every variable-length field so the concatenation is unambiguous —
otherwise `{'a','bc'}` and `{'ab','c'}` hash identically."* That is the entire answer to *"why is
concatenating raw child hashes insufficient?"*, which is asked every time.

**The third rule, for tree hashes specifically: the child's name belongs to the PARENT's record,
never to the child's own hash.** Fold the name in and a subtree can never be recognised in a new
position — no rename detection, no dedup, no content-addressed reuse. It is the difference between
a hash that identifies *content* and one that identifies *a path*.

**And cache the result on a version, not a timestamp.** `(snapshot id, path)` is sound;
`(path, mtime)` is not, because timestamps are coarse and are preserved by copies and checkouts.

**Where it shows up in a frontend round.** React `key` built by concatenating fields; a
`useMemo`/SWR/React Query cache key built from an object (this is why those libraries hash a
structured key rather than a template string); `localStorage` namespacing; deduping a request
in-flight map. Drill `cursor-12-merkle-hash` is the version Cursor actually asks.

---

### P. SCROLL THE ACTIVE ITEM INTO VIEW

**Problem.** A combobox, palette or menu with a virtual cursor: arrowing past the visible window
moves `aria-activedescendant`, the screen reader announces the right option, and the sighted user
sees nothing move. Every list widget in §03–16 needs this and it is the most commonly forgotten
line in the whole guide.

**Derivation.** The active item is the one that must be visible, so scrolling is a function of the
active index — which makes it an effect, not something you do inside the key handler. Do it in the
handler and you scroll before React has moved the highlight.

```tsx
useEffect(() => {
  if (active < 0) return
  refs.current[active]?.scrollIntoView({ block: 'nearest' })
}, [active])
```

**`block: 'nearest'` is the whole technique.** The default is `'start'`, which yanks the item to
the top of the scroller on every keypress — the list jumps even when the item was already in view.
`'nearest'` scrolls the minimum distance, so an item already visible does not move at all. That is
the difference between arrow keys that feel native and arrow keys that feel broken.

**Do not compute `scrollTop` by hand.** `offsetTop - container.scrollTop + clientHeight` math is
four lines that break the moment there is a sticky header, a border, or a non-`position: relative`
ancestor. `scrollIntoView` is one line and the browser owns the edge cases.

**Add `behavior: 'smooth'` only for a jump the user did not make** — a "scroll to selected" on
open. On arrow keys it makes the list lag behind the cursor, and it fights `prefers-reduced-motion`.

---

### Q. THE LATEST-REF PATTERN, AND WHEN NOT TO USE IT

**Problem.** An effect that subscribes to something long-lived — a stream, a socket, an interval —
needs to call a callback the parent passed. Put the callback in the dependency array and every
parent render with an inline arrow tears the subscription down and rebuilds it. Leave it out and
you call a stale closure forever.

**Derivation.** Split the two things the dependency array conflates: *what should re-subscribe*
versus *what value should be current when I call it*. Only the first belongs in deps.

```tsx
const onTokenRef = useRef(onToken)
useEffect(() => {
  onTokenRef.current = onToken     // after every commit
})

useEffect(() => {
  const socket = connect(url)
  socket.onmessage = (e) => onTokenRef.current(e.data)   // always the latest
  return () => socket.close()
}, [url])                          // re-subscribes on url only, which is correct
```

**Assign in an effect, never during render.** `ref.current = onToken` at the top level of the
component body is a side effect during render, which react.dev explicitly forbids: React may
render a component and throw the result away, and under `<StrictMode>` it renders twice. The
no-dependency-array effect above runs after every commit, which is exactly the guarantee you want.

**Declaration order matters** when two effects are involved: the effect that *writes* the ref must
be declared above the effect that *reads* it, because React runs them top to bottom.

**When not to reach for it.** If the callback identity changing *should* restart the work, the
dependency array was right and the ref is a bug that hides a real dependency. The honest test:
*"if the parent passes a different function, do I want a different subscription?"* If yes, put it
in deps and tell the caller to memoise. The ref is for callbacks that are notifications, not
configuration.

**The React 19 note worth one sentence.** `useEffectEvent` is designed for exactly this and removes
the ref entirely, but it is still experimental — say you know it exists and that you would not ship
on it yet.

---

### R. COALESCING HIGH-FREQUENCY UPDATES

**Problem.** A stream delivering tokens at 100/sec, a pointermove, a resize observer. One
`setState` per event is one render per event, and the renders queue behind each other until the
input lags.

**Derivation.** The screen only updates 60 times a second, so anything faster than that is work
whose result is never seen. Accumulate in a ref, schedule one paint, and let the frame decide.

```tsx
const buffer = useRef('')
const frame = useRef<number | null>(null)

function push(chunk: string) {
  buffer.current += chunk
  frame.current ??= requestAnimationFrame(() => {
    frame.current = null
    setText(buffer.current)          // one render per frame, not per token
  })
}

useEffect(() => () => {
  if (frame.current !== null) cancelAnimationFrame(frame.current)
}, [])
```

**Why a ref for the buffer.** It is written many times between paints and rendering it early is
precisely what you are avoiding — this is the textbook "mutable value that is not state."

**Why `??=` rather than a boolean flag.** One variable holds both "is a frame scheduled" and "which
frame to cancel", so the two can never disagree.

**Say the tradeoff, and say it is premature.** React 18 already batches updates inside its own
event handlers and, since 18, inside promises and timeouts too — so a plain `setText` per token is
usually fine and this is an optimisation you reach for **after** you measure, not before. What
scores is naming it as a known lever and saying you would not add it yet: *"tokens arrive faster
than the display refreshes, so if this profiled badly I would accumulate in a ref and flush once
per animation frame."* Reaching for it unprompted reads as premature optimisation, which is its
own negative signal.

---

## 18 — Prop design, decided

**Component API design** is one of the three named grading axes, and it is the one people prepare
for least — it has no keyboard table to memorise and no ARIA spec to check yourself against. This
section is the missing checklist: eight forks, each with the test that decides it and the sentence
to say.

Use it in the first five minutes, out loud, before the body of the component exists. §02 A gives
you the five decisions about *state*; this gives you the decisions about *surface*.

---

### A. DATA, CHILDREN, OR A RENDER PROP

The first fork, and the one that shapes everything after it.

| Shape | Choose it when | What it costs |
|---|---|---|
| `items={[{ value, label }]}` | The list is homogeneous and the component owns the markup | Customising one row means adding a prop |
| `renderItem={(item, state) => ReactNode}` | Rows vary, but the component still owns behaviour and layout | One more prop; the caller can break your ARIA if you let them render the wrapper |
| Compound — `<Menu><Menu.Item/></Menu>` | Consumers must interleave, reorder, or nest arbitrary children | Mis-nestable, needs context, hard to virtualise, much more code |

**Default to `items`, and say why.** It is impossible to mis-nest, it virtualises without changing
the API, and the component can guarantee its own ARIA wiring because it renders every node. The
compound version hands that guarantee to the caller.

**The upgrade path is the answer to "what if I need a custom row?"** — add `renderItem`, keep the
wrapper. You render the `<li role="option" aria-selected>`; they render what is inside it. That
keeps the accessibility contract yours while the content becomes theirs.

> *"I'd take `items` because it makes the ARIA wiring my responsibility rather than the caller's,
> and it virtualises later without an API change. If rows need to vary I'd add `renderItem` and
> still own the option wrapper. I'd only go compound if consumers need to interleave arbitrary
> children — that's a real requirement, and it costs a context and the ability to mis-nest."*

---

### B. ONE CALLBACK OR SEVERAL

**The rule: one callback per piece of state you own. Extra callbacks only for events that are not
state changes.**

```tsx
onValueChange(next)                 // the state moved — always this one
onOpenChange(open)                  // a second piece of state → a second callback

onDismiss(reason: 'timeout' | 'user' | 'action')   // not state; the REASON is the payload
```

The anti-pattern is a component that fires `onChange`, `onSelect` and `onCommit` for the same
interaction. The caller cannot tell which to use, and any two of them will drift.

**A `reason` argument is worth more than a second callback.** `onDismiss('timeout')` versus
`onDismiss('user')` lets the parent log an auto-dismiss differently without you exposing two
functions that must both fire in the right order. Toast is the standard example, and the same trick
applies to a modal that can close by Escape, backdrop, or a button.

---

### C. BOOLEANS OR A VARIANT

Four booleans is sixteen states, of which maybe four are legal.

```tsx
// Illegal states are representable — isPrimary + isDanger, isSm + isLg
<Button isPrimary isSecondary isDanger isSm isLg />

// Illegal states are unrepresentable
<Button variant="primary" size="sm" />
```

**Keep a boolean when the thing is genuinely independent and binary** — `disabled`, `required`,
`loading`. Reach for a union the moment two booleans are mutually exclusive.

**And use a discriminated union when props travel in sets**, so the type system enforces what a
comment otherwise would:

```tsx
type Props =
  | { mode: 'single'; value: string; onValueChange: (v: string) => void }
  | { mode: 'multi'; value: string[]; onValueChange: (v: string[]) => void }
```

Now `mode="single"` with an array value does not compile. Saying *"I'd make the illegal states
unrepresentable rather than validate them at runtime"* is a strong sentence in any round.

---

### D. CONFIGURE, OR INJECT

The question is whether the component should know **how** or only **what**.

| | Configure — pass data | Inject — pass a function |
|---|---|---|
| Looks like | `url="/api/search"` | `fetchResults={(q, signal) => Promise<Item[]>}` |
| Component knows | the transport | nothing about transport |
| Testable without a network | no | yes |
| Works for SSE, socket, cache, mock | no | yes |

**Inject anything that is policy, transport, or I/O.** The component owns rendering and lifecycle;
the caller owns where bytes come from. That one sentence is the highest-value API line in a
streaming or async round, and it is why every drill in this repo takes a `fetchX` prop rather than
a `url`.

**Pass the `AbortSignal` in**, because cancellation is the component's job to *trigger* and the
caller's job to *honour*. A `fetchResults` that ignores the signal is the caller's bug, and your
generation guard still saves you.

**Configure when it genuinely is just a value** — `debounceMs`, `minChars`, `placeholder`. If you
find yourself adding `headers`, `method` and `transformResponse`, you have rebuilt `fetch` badly
and should have injected.

---

### E. CALLBACK SIGNATURES

**Pass the meaning, not the event.**

```tsx
onValueChange(e)                       // caller digs through e.target.value
onValueChange(next: string)            // caller gets what they asked for
onValueChange(next: string, item: Item) // and the row, when hydrating costs them a lookup
```

**Never pass an index.** Indexes shift when the list is filtered, sorted, or paginated, and the
bug appears a week later in someone else's code. Pass the stable `value`, which §02 A already made
you define.

**Order: the new value first, context second.** `onValueChange(next, meta)` reads correctly and
lets callers write `onValueChange={setValue}` with no wrapper — a small thing that gets noticed.

---

### F. NAMES THAT DO NOT COLLIDE

| Use | Not | Because |
|---|---|---|
| `onValueChange` | `onChange` | Collides with the DOM event if the root is an `<input>`; ambiguous on every other element |
| `open` / `defaultOpen` | `isOpen` | Pairs with `value` / `defaultValue`, and matches the platform's own `<details open>` |
| `items` | `data`, `options`, `list` | `data` says nothing; `options` is right only for a listbox |
| `renderItem` | `itemRenderer`, `children` as function | `render*` reads as a slot; a function child is a puzzle to the next reader |

**The controlled/uncontrolled pair is a naming convention, not just an API one.** `x` plus
`defaultX` plus `onXChange` is the shape React itself uses, so a reader who has never seen your
component already knows which prop makes it controlled.

---

### G. ESCAPE HATCHES — one beats ten props

You cannot anticipate every consumer, and every prop you add to try is a prop you maintain forever.

```tsx
function Toast({ className, style, ...rest }: Props & ComponentPropsWithoutRef<'div'>) {
  return <div role="status" className={className} style={style} {...rest} />
}
```

Three things earn their place:

1. **`className` and `style` passthrough**, so styling needs no new prop.
2. **`...rest` onto the root**, so `data-*`, `aria-describedby` and event handlers all work.
3. **A forwarded `ref`**, so callers can focus or measure the node. React 19 lets `ref` be an
   ordinary prop; below that it is `forwardRef`. Say which you are on.

**Spread `rest` *before* your own critical attributes**, so a caller cannot accidentally clobber
`role` or `aria-*`. Order in JSX is last-wins, and that ordering is a deliberate choice worth
narrating.

---

### H. WHAT DOES NOT BELONG IN PROPS

- **Anything derivable.** `isEmpty` when you already have `items`; `count` when you have the array.
  A prop that can disagree with another prop is a bug with a scheduled delivery date.
- **State the component should own.** Transient typing state, hover, focus-within. Expose it only
  if a parent has a real reason to read or set it (§02 A, question 3).
- **A second source of truth.** Never accept `value` *and* `defaultValue` as both meaningful. One
  or the other: *"controlled when the parent owns it, uncontrolled with a default when it doesn't,
  never both."*
- **Config objects that are rebuilt every render.** `options={{ debounce: 300 }}` is a new object
  each time, which defeats memoisation and re-runs effects. Take flat scalar props, or document
  that the object must be memoised — flat props are kinder.

---

### I. THE NINETY-SECOND API SCRIPT

Say this before writing a body. It is the cheapest points in the round.

1. **Name the shape.** *"It takes `items`, it's controlled-or-uncontrolled on `value`, and it
   reports through `onValueChange`."*
2. **Name the one injected thing, if any.** *"`fetchResults` is injected with the signal, so the
   component owns rendering and the caller owns transport."*
3. **Name what you deliberately left out.** *"No `renderItem` yet — I'd add it the moment rows need
   to differ, and the wrapper would stay mine so the ARIA contract doesn't leak."*
4. **Name the escape hatch.** *"`className` and `...rest` go to the root, and I forward the ref."*
5. **Then type the signature**, and only then the body.

The candidates who score on this axis are not the ones with more props. They are the ones who can
say why each prop exists and which one they refused to add.
---

## Company signals

What each company emphasises at staff level, based on reported patterns. Use it to order practice,
not to predict the prompt.

| Company | What they test | Signature flavor |
|---|---|---|
| **Anthropic** | Streaming chat, async cancellation, refactor under changing requirements | `useStreamingChat` plus mid-stream abort; they change the spec partway through on purpose |
| **Cursor** | Editor-adjacent surfaces: diffs, trees, palettes, inline review — and **non-component modules** on the same rubric: a streaming Markdown tokenizer, a Merkle hash over a repo | Real product surface, and test quality graded as its own axis |
| **Ramp** | Bug-fix inside an existing React+TS codebase, data table with pagination, a DOM puzzle round | Navigating someone else's component; `runConcurrently` for batch fetches |
| **Airbnb** | Booking-flow components — date picker, tabs, star rating — and deep JS fundamentals | `curry`, `LRUCache`, `deepEqual` all appear; heavy keyboard a11y emphasis |
| **Meta** | Recursive UI (file explorer, comment tree), `EventEmitter`, `Promise.all` from scratch | DOM renderer from a JSON descriptor; `role="tree"` / `role="group"` hierarchy |
| **OpenAI** | Team-dependent; take-home or CoderPad on real product problems | Autocomplete with proper cancellation; chat UI patterns |
| **Google** | Performance-heavy: virtualization, throttle, `memoize`; utility re-implementation | May ask for `Promise.all` / `Promise.race` from scratch |

**The staff-level delta is the same everywhere.** Not "does it work" — correct roles and keyboard
contract, stale-closure safety, cancellation of async work, component API design, and an
articulated tradeoff on every decision you make.
