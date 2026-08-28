# Design-page diagrams

Every board on a `/designs` page is inline SVG generated from a spec in
`pages/`. The markdown holds the finished SVG — that is what the site renders,
and it stays the source of truth — but nothing here is hand-edited: change the
spec, rebuild, and the board is replaced in place.

```bash
npm run diagrams            # rebuild every board
npm run diagrams cursor     # rebuild one page's boards
npm run diagrams:verify     # render every page through the real site pipeline
python3 tools/diagrams/render.py design-cursor.md 0 /tmp/boards   # look at one
```

`build.py` is idempotent. Each board carries a stable `data-board` id, so a
rebuild finds it and replaces it byte-for-byte when nothing changed — which
makes `git diff` after a build an honest answer to *did my edit do what I meant?*

## The two kinds of board

**An architecture board** is the one to draw first, and the one an interviewer
means by "high-level design": components you could point at in production. Use
`group()` for tiers and trust boundaries, `box()` for services, `cyl()` for
anything that survives a restart, `queue()` for logs and queues. Arrows carry
the protocol or the payload, not the step number. `design-cursor.md`'s
`architecture` board is the worked example.

**A flow board** is a sequence, and it earns its place only where the branches
carry the argument — an architecture board cannot show a branch. Cursor's
`hot-path` board exists because the should-fire filter and the cache hit are
where the economics live.

**A skeleton board** (§14) is the system stripped to what belongs on a
whiteboard at minute five, with a numbered `badge=` on each box keyed to the
numbered list below it, so the page doubles as a self-check after drawing it
cold. Items with no box to hang on — a ratio, a rule, a sentence you have to
say — become tiles under a lane reading *"in the margin — said, not drawn."*

## Writing a spec

```python
from dgl import Board
from splice import place

b = Board(560, "One sentence per tier, for a screen reader.")
b.banner("The governing number, or the sentence the whole page argues for.")
b.group(20, 86, 210, 300, "CLIENT")
b.box(35, 118, 180, 56, "Service", ["what it actually does"])
b.cyl(35, 190, 180, 54, "Postgres", ["sharded by org_id"])
b.arrow((230, 150), (354, 150)); b.ctext(292, 142, "one request", 'dg-lbl')

place('design-x.md', 'architecture', b, "Caption: what to say while drawing it.",
      after_heading='## 6 ')
BOARDS, WARN = 1, b.warn
```

`place()` takes `section='## 6 '` to replace the *n*th fenced block in a section
(how a board first displaces the ASCII art it supersedes), or
`after_heading='## 14 '` to insert under a heading. Both only matter the first
time — after that the `data-board` id is what finds it. A module must expose
`BOARDS` and `WARN` for `build.py` to report on.

## Rules that are not negotiable

1. **No colours, weights or anchors as attributes.** Everything is a `dg-*`
   class defined once in `src/index.css`, so one copy of the markup reads in
   both themes. Adding a class means adding it to `render.py`'s token block too.
2. **Arrowheads are explicit triangles, never `<marker>` defs.** Markers survive
   the parse5 → hast → React round-trip only if every camelCased attribute maps
   cleanly, and a silently headless arrow is the exact failure a diagram exists
   to prevent.
3. **No blank lines inside the `<div class="diagram">` block.** A blank line
   closes the HTML block and the rest of the SVG renders as literal text.
4. **Look at the board before you ship it.** `build.py`'s width guard catches
   text that overflows its box; it cannot catch an arrow routed through a box,
   two labels colliding, or a diagram that is simply wrong. Every layout bug
   found so far was found by rendering a PNG and looking at it.

`viewBox` is 1000 units wide and the wrapper scrolls below 680px rather than
shrinking a board to a picture of a board.
