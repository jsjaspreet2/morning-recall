# Design Page Authoring Spec

The schema every problem page follows, the standing rules that make them good, and the steps to
publish one. **This is the file you hand to Claude Code when you want a new problem written.**

Pages live in `src/data/designs/` and are served at `/designs/<slug>`.

---

## Layout on disk

```
src/data/designs/
  00-interview-mechanics.md      published, pinned to the top of the index
  design-uber.md                 → /designs/uber
  design-ticketmaster.md         → /designs/ticketmaster
  …
```

Flat, one file per page. The slug is the filename minus any numeric prefix, the `design-` prefix,
and `.md`.

Three kinds of page, though only two exist so far:

- **`00-interview-mechanics.md`** — everything true regardless of problem. Written once. Problem
  pages link to it and never restate it.
- **`design-*.md`** — one page per problem, following the section schema below.
- **`primitives/*.md`** — one short card per reusable concept, linked from every problem that uses
  it. **None have been written yet.** The rule is that a concept graduates into a primitive the
  *second* time a problem page needs it; before that it lives inline. Adding the first one means
  adding a `primitives/` glob and a group to `DesignsIndex`.

**Primitives backlog** (things likely to graduate): idempotency keys · outbox pattern · optimistic
concurrency / conditional update · consistent hashing & ring membership · saga & compensation ·
space-filling curves and 2-D→1-D reduction · quorums and CAP in practice · CDC / change streams ·
WebSocket fanout & connection registries · rate limiting & admission control · `SKIP LOCKED` and
queue-in-a-database · bloom filters · write-ahead logs · read replicas & replica lag · cell-based
architecture

---

## The required opening

The site parses this, so it is not optional. Every problem page opens with exactly:

```markdown
# Design Ticketmaster — High-Contention Inventory

## The question

> *"Design Ticketmaster — specifically the onsale. A stadium tour goes on sale at 10am, ten
> million people are waiting, and there are sixty thousand seats."*

**The product.** …

**What a working system delivers**

- …

**Why this gets asked.** …

---

**Archetype:** non-fungible inventory reservation under thundering herd, with money attached.
**Cousins that reuse ~70% of this page:** airline seat selection, StubHub, hotel booking, …

**What's actually being graded:** …
```

- The `#` heading is the page title. It is **stripped from the body** before rendering, because the
  page chrome already displays it — so don't reference "the title above" in the prose.
- `**Archetype:**` is the fallback card subtitle if the file isn't registered yet.
- Everything after the header block is the section schema.

### Why "The question" is unnumbered

It sits above the header block because it is the only part of the page written for a reader who
does **not** already know the product — everything from `**Archetype:**` down assumes they do. It
stays unnumbered because the numbered sections are cross-referenced as `§7`, `§9` throughout every
page; renumbering to make room for it would invalidate all of them for no gain. §0 is still §0.

**Rules for writing it** (~150–250 words, ~350 for a page whose product needs explaining):

- **No architecture vocabulary in "The product."** Not "effective-settings function", not
  "fanout-on-write", not "CRDT". If a term makes its first appearance here, the section has failed.
- **The blockquote is the prompt as an interviewer would say it in one breath** — answerable and
  slightly under-specified, which is what a real prompt is. It is not a summary of the page. Where
  the page later says "the problem statement calls out X", the blockquote is what has to say X.
- **"What a working system delivers" is user-visible outcomes**, not components and not §1 in
  requirements-ese. "Your theme is already right on a laptop you signed into an hour ago", not
  "the client resolves settings locally".
- **"Why this gets asked" hands off; it does not compete.** One or two sentences naming the shape of
  the difficulty, ending exactly where `**What's actually being graded:**` picks up. Don't restate
  the graded line, the contrast line, or §0.

---

## Section schema

| § | Section | Standing rules |
|---|---|---|
| — | **The question** | The prompt as an interviewer says it, then what the product *is* in plain language, what a working one delivers in user terms, and one hand-off line on why it's a hard problem. Unnumbered, and it sits **above** the header block |
| — | **Header** | Archetype in one line. Cousins that reuse ~70% of the page. "What's actually being graded" — the specific misconception this problem exists to catch |
| 0 | **The 60-second frame** | A verbatim script. Names the archetype, the tension, the scope, and **pre-commits a deep dive** |
| 1 | **Functional requirements** | Exactly three. Plus explicit out-of-scope, plus "below the line" likely follow-ups |
| 2 | **Non-functional requirements** | Table. Every row is a *number* plus a *justification*. Adjectives score zero. End with the one sentence that earns the point |
| 3 | **Numbers that reframe the problem** | 4–6 figures max. Every number must change a decision — if it doesn't, cut it. Label assumptions as assumptions |
| 4 | **Core entities** | Nouns first. Fields only where a field carries a design decision. Then call out the 2–3 load-bearing ones explicitly |
| 5 | **API** | Code block. Then "decisions to narrate, unprompted" — the *why* behind each shape |
| 6 | **High-level design — flows** | Diagram **plus** a numbered walkthrough per core flow |
| 7–11 | **Deep dives** | 3–5. Each follows: naive approach → what breaks (with a mechanism or number) → what replaces it → **what the replacement costs** |
| 12 | **Data model / sharding** | Partition key + why. Name the hot-shard consequence and whether it's intentional. **Plus a storage decision table: one row per stateful component** — access pattern, durability requirement, choice, and the one sentence you'd say |
| 13 | **Traps** | Design traps and performance traps, ranked. Interview-performance traps live in the mechanics page — link, don't repeat |
| 14 | **Five-minute skeleton** | 8–10 numbered lines. This is the artifact that gets drawn cold |
| 15 | **Variants** | Table, organized around **one named governing axis**. Deltas only |

Use `## N · Title` for sections and `### Title` for subsections — those are the two levels the
sidebar TOC surfaces. **§15 is the last section.**

**§16 · Active recall is gone — don't write one.** Seven pages used to end with a table of
12–25 cold prompts and section pointers. Those tables were **deleted on 2026-08-30**: they were
the part of a page nobody read and the most expensive part to generate. Every design page now
ends at §15, and none of them is an example to copy. The site has no recall deck of any kind —
see `BUILD_SPEC.md` — so there is nowhere for a generated prompt to go and nothing to keep in
sync. Don't write recall prompts, tables of cold questions, or flashcards, here or anywhere else
in this repo. (`git log -- src/data/designs/` has the old tables if that judgment ever reverses.)

---

## Standing rules

**Write §6 last.** The flows should reference the dives (`§7`, `§9`) rather than duplicate them.
Written first, §6 becomes a second, shallower description of the same system. Written last, it
becomes the spine everything hangs off.

**Every flow ends in a failure path.** At least one abandonment, timeout, decline, partition, or
reconnect step. This is where interviewers probe and where a diagram has nowhere to put anything.
The best of these is often "nothing happens, and here's why that's correct."

**Every deep dive opens with why the obvious answer fails.** Not "here's what to use" — "here's
what you'd reach for, here's the specific mechanism by which it breaks, here's the replacement,
here's its cost." A dive missing the failure step is a technology list; one missing the cost reads
as memorized.

**Name the product, not the category.** "A KV store with last-write-wins" is a restatement of the
requirements, not a decision — the reader still has to pick. Every row of the storage table names
something you could actually deploy (Cassandra, Redis Cluster, Postgres+Citus, Kafka, Fastly), plus
the *configuration detail that makes it work* where one exists — `USING TIMESTAMP = seq`,
`FOR UPDATE SKIP LOCKED`, heartbeat TTL. Categories are what you say while deriving; products are
what you say at the end.

**Depth is allocated by variance, not by importance.** A decision earns a deep dive when
*reasonable engineers would disagree* — not when it's load-bearing. The connection registry is
load-bearing and boring: every requirement points at Redis, so it gets a table row and fifteen
seconds. Sequence assignment looks like a detail and is genuinely contested, so it gets prose.
**But nothing gets zero.** Every stateful component appears somewhere with a named choice and a
one-line derivation, because naming a product without the derivation is the specific failure mode
that reads as shallow. If a component only appears inside a diagram box, that's a gap.

**Numbers or nothing.** Any claim about scale carries a figure. Any figure that doesn't change a
decision gets cut.

**Separate levels, and separate choices from derivations.** §3 states per-entity, per-shard, and
global figures distinctly — collapsing them is the imprecision an interviewer probes first ("you
said 60k writes, but there are thousands of events"). And when a number follows from a *product
choice* rather than a constraint, label it: "two bits because we want to show held separately, not
because three states require it." Presenting a choice as a derivation is the most common way these
pages go subtly wrong, and it's worse than being vague — it teaches you to defend something you
can't actually justify.

**Bold the sentence, not the noun.** Emphasis goes on the reasoning worth saying out loud, not on
product names. If a bolded phrase would sound good spoken in an interview, it's bolded correctly.

**Show the loser, not just the winner.** Naming the right technology scores nothing on its own —
what's graded is watching you *choose*. Every storage-table row and every dive that lands on a
product carries the alternative you rejected and the sentence that rejected it, in the voice you'd
say it: *"Postgres models this perfectly and I'd use it at a tenth of this scale — but at petabytes
I'd be committing my team to hand-managed sharding forever, so DynamoDB, and I'm giving up joins I
don't have on this path."* A choice with no visible loser reads as recall.

**"Eventually" is not a target — every consistency claim carries a duration.** Milliseconds,
seconds, minutes, or hours, plus which reads are exempt. "Eventually consistent is fine here" is an
adjective wearing a technical hat; "≤1s replica lag for the sidebar, read-your-writes for the
author's own message" is a requirement. Same rule for freshness, lag, and staleness anywhere.

**Fault tolerance is a required §2 row, not a §13 afterthought.** Name the specific component whose
death the system survives, and — harder and better — the one whose death it *doesn't*, with the
policy for that case. A page where nothing is allowed to fail hasn't been designed under load.

**Every append-only entity needs a lifecycle row in §12.** What happens in year three. Hot / warm /
cold with the ages and the read latency of each, what the archive unit is, and the user-visible cost
of restoring one. Unbounded growth with no tiering is a real finding, and stating the trade beats
hoping nobody multiplies the daily volume by 365.

**Tie choices back to §2 by name.** A dive that ends with a decision should say which non-functional
requirement bought it — `**→ ties to the TTFT NFR**`. Do this two or three times a page, at the
decisions that would otherwise look like taste. It's the cheapest way to show the requirements
section wasn't a warm-up.

**Never restate the mechanics page.** No "remember to scope first" in a problem page.

**Variants need an axis.** "Similar problems" as an unstructured list is low value. Find the one
property that governs the family — fungible vs non-fungible inventory, read-heavy vs write-heavy,
contention vs throughput — and organize the table around it. Six problems collapse into one idea
plus deltas.

---

## Archetype map

The point of archetypes is that ~30 problems reduce to ~7 shapes. Tag every page, and use the exact
label from this table — the index groups by it.

| Archetype | Defining tension | Canonical page |
|---|---|---|
| **Geospatial marketplace** | Huge write throughput, near-zero contention | Uber |
| **High-contention inventory** | Trivial throughput, catastrophic contention | Ticketmaster |
| **Interval inventory & search** | Conflict is range overlap rather than row identity; contention ~1, so search dominates | Airbnb |
| **Real-time messaging & delivery** | Ordering and delivery semantics vs fanout cost | WhatsApp |
| **Real-time collaborative editing** | Convergence on a shared mutable document; the data model picks the algorithm | Figma |
| **Layered configuration & sync** | Precedence between layers is a product decision, not a merge algorithm; delivery is a hint and versions are the truth | IDE settings sync |
| **Read-heavy content & fanout** | Fanout-on-write vs fanout-on-read | Twitter feed |
| **LLM application** | A slow, expensive, capacity-bounded generation that outlives the request that started it | ChatGPT |
| **Low-latency inference in a loop** | Latency budget forbids the standard pipeline | Cursor Tab |
| **Usage metering & billing** | Lossy, high-volume telemetry must converge on an exact amount of money, settled through a third party you don't control | LLM API billing |
| **Multi-service order orchestration** | One user action must commit across services that share no transaction, and the last step is physical and cannot be undone | Amazon checkout |
| **Money movement & settlement** | Exactly-once movement of real funds through rails you don't own, where the books must balance and every retry is a potential double charge | Payment processor |
| **Write-heavy telemetry / analytics** | Ingest volume vs query flexibility | *(pending)* |
| **Coordination / uniqueness** | Global invariant across partitions | *(pending)* |

**When generating a new page, first ask which archetype it is and what the *inverse* problem in the
table teaches by contrast.** The Uber/Ticketmaster contrast — massive throughput with no contention
vs trivial throughput with total contention — turned out to be more instructive than either page
alone, which is why they sit adjacent on the index.

---

## Renderer constraints

The site renders these through `react-markdown` with `remark-gfm`, `rehype-raw`, `rehype-slug`, and
`rehype-highlight`. Four consequences:

1. **`rehype-raw` runs first, so any tag name in prose is live markup.** A bare `<nav>` in a
   sentence becomes an element and swallows the rest of the block. **Backtick every tag name.**
2. **Only `##` and `###` reach the TOC.** `####` renders but is invisible to navigation.
3. **Fence every code block** with a language. GFM tables render; so do `<details>`/`<summary>` if
   you want a collapsible.
4. Long tables and code blocks are fine — the content column is `min-w-0` and scrolls them
   horizontally rather than widening the page.

---

## Diagrams

Boards are **generated, not hand-written**. Specs live in `tools/diagrams/pages/`
and the finished SVG is written into the markdown, which stays what the site
renders. Full guide: `tools/diagrams/README.md`.

```bash
npm run diagrams              # rebuild every board (idempotent)
npm run diagrams cursor       # one page
npm run diagrams:verify       # render every page through the real pipeline
python3 tools/diagrams/render.py design-cursor.md 0 /tmp/boards   # look at one
```

A page carries up to three kinds of board:

1. **Architecture** — §6's first board, and the one an interviewer means by
   "high-level design": components you could point at in production. `group()`
   for tiers, `box()` for services, `cyl()` for anything that survives a
   restart, `queue()` for logs. Arrows carry the protocol, not a step number.
   `design-cursor.md` is the worked example.
2. **Flow** — a sequence, and only where the branches carry the argument, since
   an architecture board cannot show a branch. Cursor's hot path earns one
   because the should-fire filter and the cache hit are the economics.
3. **Skeleton** — §14, the system stripped to what belongs on a whiteboard at
   minute five, with a numbered badge per box keyed to the list below it, so the
   page doubles as a self-check after drawing it cold. Items with no box to hang
   on become tiles under a lane reading *"in the margin — said, not drawn."*
   That band is usually where candidates go quiet.

ASCII art is not an option for any of these: box-drawing arrows lose branches,
and §6 forks.

---

## Publishing a page

1. Write the file into `src/data/designs/` as `design-<slug>.md`.
2. Add an entry to `META` in `src/data/designs.ts`: `label`, `archetype` (exact label from the map
   above), `tension` (one line — the defining tension), and `accent`. Position in the object sets
   the index order.
   *If you skip this, the page still works* — it appears under "Unfiled" with a title and subtitle
   parsed from the file. It's a cosmetic gap, not a broken page.
3. Verify, then push. GitHub Pages deploys from `main`.

```bash
npm run build          # tsc + vite; must be clean
npm run dev            # /designs lists it; /designs/<slug> renders; TOC populated
```

---

## Self-check before publishing

Run this against the finished page. Each line maps to a standing rule above.

- [ ] "The question" present, above the header block, and free of architecture vocabulary
- [ ] Header block present and complete — archetype, cousins, what's being graded
- [ ] §0 is a script you could read aloud, and it pre-commits a deep dive
- [ ] Exactly three functional requirements, with explicit out-of-scope
- [ ] Every NFR row has a number and a justification; no adjectives
- [ ] Every consistency/freshness claim carries a duration, and §2 has a fault-tolerance row
- [ ] Every named product shows the alternative it beat, in one spoken sentence
- [ ] §12 has a data-lifecycle row for every append-only entity
- [ ] Two or three decisions tie back to a §2 requirement by name
- [ ] Every figure in §3 changes a decision; assumptions labelled as assumptions
- [ ] §6 was written last and references dives by number rather than restating them
- [ ] **Every flow ends in a failure path**
- [ ] **Every deep dive has all four beats**: naive → what breaks (mechanism or number) → replacement → cost
- [ ] Every stateful component appears in the storage table or a dive with a named product
- [ ] Products named, not categories — with the config detail where one exists
- [ ] §15 is organized around one named governing axis
- [ ] Nothing from the mechanics page is restated
- [ ] Tag names in prose are backticked; `npm run build` is clean

---

## Generation prompt

> Write `src/data/designs/design-<name>.md` following `DESIGN_PAGE_AUTHORING.md`. Tag the archetype
> using the exact label from the archetype map, and name the inverse problem for contrast. Write §6
> last, referencing the deep dives by section number. Every deep dive opens with why the obvious
> answer fails and closes with what the replacement costs. Every flow ends in a failure path. Do not
> restate anything from `00-interview-mechanics.md` — link to it. §15 must be organized around one
> named governing axis, and **the page ends there — no §16 active-recall section, and no recall
> prompts anywhere.** Then add the `META` entry in
> `src/data/designs.ts` and run the self-check
> list.
