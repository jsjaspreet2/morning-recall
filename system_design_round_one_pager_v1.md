# The system design round — one page

Read this at T-30. Everything here exists in longer form elsewhere; this is the operational
version, built from one reviewed mock that scored 6 out of 20 with every component named
correctly. The gap was not knowledge. It was **allocation and closure** — where the minutes went,
and whether anything was finished. Pointers to the deep sections are at the bottom.

---

## The card

| When | Do | Say |
|---|---|---|
| **0–2** | **Rubric echo.** If the prompt lists topics, write them on the canvas as a checklist before anything else. Tick each as it is covered. Revisit at 25 and at 40. | *"The prompt names eleven things. I'm listing them so I can tick them."* |
| **After back-of-envelope** | **Load-proportional budget.** Annotate every box with its QPS or storage. Allocate deep-dive minutes in proportion. **Anything under ~1 MB/day or ~10 QPS gets at most three minutes, total.** | *"This table is three megabytes over ten years. It gets one box and three minutes."* |
| **Before any service** (workflow prompts) | **State machine first.** Draw the per-entity states and transitions. Then every service you draw must own a transition. One that owns none is deleted. | *"Here's where each target can be. Every box I draw has to move something on this."* |
| **After the diagram** | **Kill a box.** Pick one component and ask which requirement breaks without it. If nothing breaks, delete it and say why out loud. Repeat once. | *"If I remove the outbox — the device dedupes on the id, so nothing breaks. It's gone."* |
| **35** | **NFR audit.** Re-read every NFR against the boxes as drawn. Name one contradiction aloud and resolve it. | *"I wrote 100 ms creation-to-fanout and drew ten million devices. That can't both be true."* |
| **After each of:** requirements · entities/API · high-level design · each deep dive | **Forced pause.** Stop for ten seconds. Ask *"what would you push on here?"* Then answer it **as the interviewer would**, not as yourself. | *"If I were grading this, I'd ask what happens to the state when a gateway dies. So —"* |
| **Throughout** | **Waffle count ≤ 2.** Count every "actually, no" and "let me back up." When uncertain, **state the decision and the condition under which you would reverse it**, then move on. | *"I'm choosing Postgres. If the write rate crosses ten thousand a second, I'd revisit. Moving on."* |

Seven rows. They are cheap, and in the reviewed mock five of them would each have moved the
score by two points.

---

## The budget rule

The reviewed mock computed that campaigns were **≈ 3 MB over ten years**, and then spent about
**twelve minutes** building a job queue → workers → outbox → CDC → message queue → delivery
service for that path. The **10-million-device fanout** and the **1-million-readings-a-second
ingest** — the two paths that carry every hard number in the prompt — got **about five minutes
combined**. Vocabulary was fine throughout. The allocation was inverted.

**The rule:** after the back-of-envelope, write a number on every box — QPS, rows, bytes per day.
Then look at where the minutes are about to go. Anything under roughly a megabyte a day or ten
requests a second is a table with an index; it gets a box, a store, one sentence, and no deep
dive. The deep dives go to the two highest-load paths, and the interviewer should hear you say
which two those are before you start either.

A reflex worth naming: **complexity feels like competence**, and a small table is where it is
safest to build a lot. That is exactly why the number has to be on the box before the boxes
multiply.

---

## State machine first

For any prompt where "each target advances through states" — commands to a fleet, orders,
payments, rollouts, jobs — draw this before a single service:

```text
pending → delivered → acked | rejected → executed → measured
          terminals the sweeper produces: timed_out · unreachable · executed_silently · cancelled
```

Then a four-column table beside it: **transition · caused by · component that owns it · recorded
where.** Every box on the high-level design has to appear in the third column. In the reviewed
mock, the queue, the outbox, the CDC pipeline, and the delivery service would have owned nothing,
and drawing the machine first would have kept all four off the board.

The machine is also what "reconcile late or missing reports" means: the non-terminal states, each
with one rule for closing it and one moment when that happens. Without the machine, reconciliation
is a box with a name. With it, reconciliation is three queries at the deadline. The worked version
is the **Demand response** design page, §4 and §10.

---

## Kill a box

The self-check is not "what is X" — it is **"which box can you delete, and why."** Recognition
does not move a score; allocation does. Three deletions from the reviewed mock, as the procedure
should have run:

**The outbox.** *Which requirement breaks if it goes?* Exactly-once delivery. *Who provides that?*
The device — it persists the last campaign id it applied and ignores anything at or below it. So a
fanout worker that dies halfway can simply republish everything, and the outbox, the CDC tail, and
the delivery-tracking table protected a guarantee the receiver was already providing. Deleted.
The general rule: **decide where idempotency lives before adding any component whose only job is
exactly-once-ish delivery.** It usually lets you delete a box.

**The registry lookup.** A Redis map of device → gateway, read ten million times to send one
campaign. *Does this key need to exist?* The campaign is a predicate; each gateway holds the
attributes of the fifty thousand devices connected to it and can evaluate the predicate locally.
Two hundred messages, not ten million lookups. The registry survives — for unicast, where there is
no predicate — and the broadcast path never reads it. The hottest-key question, asked once, deleted
the hottest key.

**The stream processor, placed, retracted, placed again.** Three retractions on one box, and it
was never asked what the box was for. The question would have settled it in ten seconds: the
1-million-readings-a-second path needs event-time windows with a watermark, so the processor stays
— on the telemetry side, with its lateness number said aloud — and it does not belong on the
command side at all. State the decision and the reversal condition; do not re-litigate it.

---

## Minute 35 — the NFR audit

The line, close to verbatim:

> *"Let me re-read the NFRs against what I drew. I wrote p99 100 ms creation-to-fanout, and I
> drew a ten-million-device fanout — that can't both be true. The honest version is three numbers
> with three enforcers: first connected device within a second, a stage across the connected fleet
> within thirty seconds, and a per-device timeout one minute after delivery — held by the gateway
> that delivered, because a timeout nobody enforces is decoration."*

Then the two checklists that went to zero minutes in the reviewed mock. They are recited, not
derived — when "safety" or "observability" is in the prompt, the interviewer is signalling they
will ask.

**Safety, for anything that actuates the physical world or moves money:**

- Max delta per action, computed at creation, with a number.
- Staged rollout — 1 % → 10 % → 100 % — with a hold after each and **abort thresholds checked
  before the next stage**, not after 100 %.
- Cancel as a **new command with a higher id** on the same path, no approval gate, faster than the
  thing it stops. Never a flag on the row.
- Dry run: the count and the expected effect, publishing nothing.
- Rate limit on creation, per operator.
- Two-person approval above a threshold; the second approver must differ from the first.
- Oscillation guard: no opposite-sign command to an overlapping target set inside the settle
  window. Cancel is exempt.

**Observability, as ratios and tails, not throughput:**

- The funnel per action — targeted / delivered / acked / rejected / executed / timed out — as
  ratios between adjacent steps, because each drop is a different failure.
- Delivery lag p50 and p99. The p99 is the reconnect tail.
- Gateway connection counts, per gateway. A drop is also a coverage warning.
- Sweeper backlog — actions past their deadline and not yet closed. Should be zero.

---

## The rubric

Score each 0–2 after a rep. **0** is absent or wrong; **1** is present but unused — mentioned,
not acted on; **2** is present and it changed the design or the allocation.

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | Rubric coverage | Under half the listed topics touched | Half to four-fifths | Four-fifths or more, and the checklist was visible on the canvas |
| 2 | Time ∝ load | Most minutes on the lightest path | Mixed | Deep dives on the two highest-load paths, named as such |
| 3 | Back-of-envelope | Absent or wrong | Present, one error | Correct, and a number on it drove a decision |
| 4 | Per-entity state machine | Absent | Implied by the prose | Drawn first; every service maps to a transition |
| 5 | Idempotency placement | Not addressed | Mentioned | Chosen deliberately, and used to remove a component |
| 6 | Hottest-key question | Never asked | Asked, not acted on | Asked, and the design changed |
| 7 | NFR consistency | A contradiction went unnoticed | Noticed late, not resolved | Audited at ~35, one contradiction named and resolved |
| 8 | Storage choices | Unnamed, or mismatched to the access pattern | Named | Named, with the rule for each and the alternative rejected |
| 9 | Safety / observability | Absent | One of the two mentioned | Both, with concrete mechanisms and numbers |
| 10 | Delivery | More than four retractions, no pauses | Two to four retractions | Two or fewer, and the pause points were hit |

### How to score

Twenty points. **Below 14, run the same archetype again** — not a new prompt. The misses are
specific to the shape, and a new prompt hides them behind new vocabulary. At 14–17, move on and
note which criteria scored 1; the ones that recur across reps are the sections to reread. At 18
or above on a prompt you have not seen, the shape is automatic and the remaining work is the
spoken, thirty-minute version.

Two patterns worth naming, because they are how the reviewed mock lost its points while feeling
fine: **criteria 1, 2, 4, 7, and 9 all at zero** with criterion 3 and the vocabulary strong — the
knowledge was there and none of the scaffolding was; and **criterion 6 at zero on a board with a
10-million-read key on it** — the trigger question exists and was not fired.

---

## Five reps, same archetype

The point is the *shape* becoming automatic, not novelty. Five consecutive thirty-minute sessions
on the command-workflow archetype, each run through the card top to bottom and scored against the
rubric:

1. OTA firmware rollout to a device fleet.
2. Feature-flag rollout to a client fleet.
3. Bulk notification send to millions of users.
4. Configuration push to devices or agents.
5. Payment retry orchestration against a processor.

Each is a §15 row on the Demand response page, which says what changes; the rep is finding that
out on the canvas before reading it. Then the other half of the reviewed prompt: the write-heavy
telemetry archetype, using the Smart-meter telemetry page's §15 rows (fleet GPS, industrial
sensors, app analytics, metrics pipelines) the same way.

---

## If you need more

| Need | Go to |
|---|---|
| The state machine, drawn and with its transition table | **Demand response** design page, §4 |
| Where idempotency lives, and the four boxes it deletes | **Demand response** §7 |
| Broadcast vs unicast, and Pub/Sub vs a registry | **Demand response** §8 |
| The safety checklist, each item with its number | **Demand response** §11 |
| The traps ranked, including "twelve minutes on a three-megabyte table" | **Demand response** §13 |
| The lateness number and what it costs in state | **Smart-meter telemetry** design page, §8 |
| A time-series store named with retention and downsampling | **Smart-meter telemetry** §10 |
| The 45-minute shape of the round | **System Design** guide, §02 |
| The closing check and the prompt → pressure table | **System Design** §14 |
| The storage rubric — ten questions, 0–2 each | **Data Modeling Under Pressure**, §05 |
| Interview-performance traps that are true for every prompt | **Interview mechanics** design page, §6 |
