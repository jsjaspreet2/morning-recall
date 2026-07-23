# CSS Animation & Motion — Interview Cheatsheet

> Source: `Animation-Motion-Cheatsheet-v1.pdf`  
> Format: semantic Markdown extraction optimized for agent retrieval and parsing.

For GFE / frontend-coding loops (OpenAI · Shopify · Airbnb · Figma). Motion is a polish layer, not the point — ship correct logic + states + a11y first, then add this as a named step. Everything below with ★ is write-from-memory.

## FLUENT ★ (no lookup)

`transition`, `transform` (translate/scale/rotate) + why, `@keyframes`+`animation`, `opacity`, easing basics, `prefers-reduced-motion`, the height-auto & exit-anim traps.

## RECOGNIZE (have a plan)

Exit/unmount timing, `@starting-style`+`allow-`

`discrete`, FLIP for reorder, `will-change` hygiene, Web Animations API, `scroll-behavior`.

## SKIP (these loops)

3D/perspective, spring-physics internals, Framer/ GSAP internals, canvas/SVG/Lottie animation, staggered choreography, motion-path.

## The pixel pipeline — the *why* ★

This is the mechanism answer that separates you. Say it out loud when you pick a property.

Every frame runs some subset of: Style → Layout → Paint → Composite. The property you animate decides how much of the pipeline re-runs at 60fps (every ~16ms).

Stage Triggered by (examples) Cost

Layout (reflow)

width height top left margin padding worst

Paint color background box-shadow border-

radius

bad

Composite `transform opacity filter` cheap (GPU)

Rule: animate `transform` and `opacity`. They run on the compositor thread — off the main thread, so they stay smooth even while JS is busy. Anything else, justify it.

## transition — the workhorse ★

```css
/* property | duration | easing | delay */
transition: transform .3s ease-out;
transition: opacity .2s, transform .3s ease .1s; /* multiple */
```

Fires when a property changes value (hover, class toggle, state). Needs two interpolatable endpoints.

Avoid `transition: all` — animates props you didn't mean to (layout jank + surprise transitions). List properties explicitly.

Not animatable the naive way: `height: auto`, `display`, and discrete props. See traps below for the fixes.

## transform functions ★

`translateX/Y() translate()` move (no layout)

`scaleX/Y() scale()` resize — your progress-bar tool

`rotate()` spin

`skewX/Y()` rarely needed

transform-origin sets the anchor (default `center`). A fill bar using `scaleX` must set `transform-origin: left` or it grows from the middle.

Order matters: `translate() rotate()` ≠ `rotate() translate()`.

Modern: individual `translate`/`rotate`/`scale` props animate independently without clobbering each other.

## @keyframes + animation ★

Use when there's no state change to trigger a transition — looping or multistep: spinners, skeletons, indeterminate bars, blinking carets.

```css
@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
/* name dur easing delay count direction fill */
animation: spin 1s linear infinite;
}
```

- iteration-count: infinite · direction: alternate (ping-pong)

- `fill-mode: forwards` holds the last frame; `both` also applies frame 0 during delay

- animation-play-state: paused to freeze

- Steps: `0% / 50% / 100%` or `from / to`

### Easing / timing functions

`ease` default; gentle both ends

`linear` spinners, mechanical loops

`ease-out` enters (fast→slow, feels snappy)

`ease-in` exits (slow→fast, gets out of the way)

`cubic-bezier(...)` custom curves; overshoot with y>1

`steps(n)` sprite sheets, typewriter, blink

One-liner to say: "ease-out on the way in, ease-in on the way out." It signals taste for almost no words.

## The traps — the differentiators ★

### 1 · height: auto can't transition (accordion)

Modern clean fix — animate a grid track:

```css
.panel { display: grid; grid-template-rows: 0fr;
         transition: grid-template-rows .3s ease; }
.panel.open { grid-template-rows: 1fr; }
.panel > .inner { overflow: hidden; } /* required */
```

Fallbacks: `max-height` hack (pick a value ≥ real height; easing feels off) · or JSmeasure `scrollHeight` and set an explicit px height.

### 2 · Exit animations (unmount timing)

The classic React miss: you set state → element unmounts instantly → the exit transition never plays because the node is already gone.

Keep it mounted until the transition ends, then remove:

```html
// on close: play out, unmount on transitionend
<div className={closing ? "toast out" : "toast"}
  onTransitionEnd={() => closing && onDone()} />
```

Real projects reach for `AnimatePresence` (Framer) or react-transition-group — namedrop, but know the manual pattern.

### 3 · display / discrete (modern answer)

```css
dialog { opacity: 1;
  transition: opacity .3s, display .3s allow-discrete; }
@starting-style { dialog[open] { opacity: 0; } }
```

Pre-2024 fallback: toggle `visibility` + `opacity` instead of `display`.

## Performance & hygiene

- `will-change: transform` promotes to its own layer — use sparingly and remove after; each layer costs memory.

- Old GPU nudge: `transform: translateZ(0)` / `translate3d(0,0,0)`.

- Don't animate `box-shadow` (paint-heavy) — animate `opacity` of a pseudoelement holding the shadow.

- JS-driven motion → `requestAnimationFrame`, never `setInterval`.

- Debounce animations to transform/opacity before blaming the framework.

## prefers-reduced-motion ★

Ship this unprompted — it's the highest-signal, lowest-effort a11y move in a motion component.

```css
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Narrate it: "vestibular users get essential motion killed; the component still works." Definition-of-done item.

## Component recipes — progress bar ★

### Determinate — two options

```css
/* A. width — simplest, but triggers layout */
.fill { width: var(--p); transition: width .3s ease; }
/* B. scaleX — composite-only, the perf answer */
.fill { transform-origin: left;
        transform: scaleX(var(--p)); /* 0..1 */
        transition: transform .3s ease-out; }
```

scaleX caveat: it distorts children (text/icons stretch). Use it for a bare fill; use

`width` if the bar has content. Mention this tradeoff — it's the whole point of the question.

A11y: role="progressbar" + aria-valuenow/min/max.

### Indeterminate

```css
@keyframes slide { to { transform: translateX(400%);} }
.blip { animation: slide 1.2s ease-in-out infinite; }
```

## Recipes — carousel ★

```css
.track { display: flex;
  transform: translateX(calc(var(--i) * -100%));
  transition: transform .4s ease; }
```

Infinite loop gotcha: clone first/last slides. When you jump from a clone back to the real slide, disable the transition for that one frame or you see it rewind:

```javascript
track.style.transition = "none";
track.style.transform = realOffset;
track.offsetHeight; // force reflow to commit
track.style.transition = ""; // re-enable
```

CSS-only alt for simple cases: `scroll-snap-type: x mandatory` +

scroll-snap-align: start.

## Recipes — modal / drawer / toast

```css
.modal { opacity: 0; transform: translateY(8px);
  transition: opacity .2s, transform .2s ease-out; }
.modal.open { opacity: 1; transform: translateY(0); }
.backdrop { opacity: 0; transition: opacity .2s; }
```

- Enter is trivial; the exit is the interview — defer unmount (trap #2).

- Drawer = swap `translateY` for `translateX(-100%)→0`.

- Pair with focus-trap + `role="dialog"` + `aria-modal`.

## Recipes — spinner · skeleton · tabs

### Spinner

```css
@keyframes spin { to { transform: rotate(360deg);} }
.spinner { animation: spin .8s linear infinite; }
```

### Skeleton shimmer

```css
.skel { background: linear-gradient(90deg,
    #eee 25%, #f5f5f5 50%, #eee 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite; }
@keyframes shimmer { to { background-position-x: -200%; } }
```

### Tab indicator

Measure active tab's `offsetLeft`/`offsetWidth`, then slide one bar:

```css
.ink { transform: translateX(var(--x));
  width: var(--w); transition: transform .25s, width .25s; }
```

## OpenAI streaming chat — motion bits ★

Your double-starred build. Motion here is minimal and mostly about not janking under high-frequency updates.

### Blinking caret

```css
@keyframes blink { 50% { opacity: 0; } }
.caret { animation: blink 1s step-end infinite; }
```

### Typing dots (staggered)

```css
.dot { animation: bob 1.2s ease-in-out infinite; }
.dot:nth-child(2){ animation-delay:.15s; }
.dot:nth-child(3){ animation-delay:.30s; }
@keyframes bob { 40%{ transform: translateY(-4px);} }
```

Don't animate per token. Fading in each streamed chunk thrashes layout. Animate at the message level (one fade-in on mount) or not at all; let text just appear.

### Auto-scroll

- Stick to bottom with `scrollTo({top, behavior:"smooth"})` on each chunk...

- ...but only if the user is already near the bottom. If they scrolled up to read, stop auto-scrolling (check `scrollHeight - scrollTop -`

clientHeight).

## Animatable? — quick reference

Want to animate… Do this instead

position (top/left) `transform: translate`

size (width/height) `transform: scale` (mind distortion)

height: auto grid `0fr→1fr` / max-height / JS

display none↔block `@starting-style`+`allow-discrete`, or visibility+opacity

show/hide `opacity` (+ visibility)

box-shadow opacity of a shadow pseudo-element

gradient / color animate `opacity` of a layered element

## How to talk about it in the loop

- Name it as a step: "I'll get behavior + states right, then add the slide transition and reduced-motion."

- When you pick `transform`, say why (compositor, no reflow). That one sentence is the signal.

- Call the trap before you hit it: "height auto won't transition, so I'll use the grid trick."

- Close with reduced-motion — reads as production maturity, not interview theater.
