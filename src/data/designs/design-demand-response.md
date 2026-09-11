# Design Grid Demand Response — Commands to 10M Intermittently Connected Devices

## The question

> *"Design the control system for a utility's demand response program. An operator needs to send a command — 'shed two kilowatts for the next thirty minutes' — to a large group of devices in people's homes: thermostats, water heaters, EV chargers. Ten million of them, connected intermittently. Cover targeting, dispatch, per-device state, retries, idempotency, telemetry ingestion, aggregation, late events, reconciliation, safety, and observability."*

**The product.** On a hot afternoon the grid is short of power. Instead of firing up a gas plant, the utility asks a million homes to let their thermostats drift up two degrees for half an hour — customers who opted in, in exchange for a credit on their bill. An operator picks the homes (a region, a device type, a program tier), writes the instruction, and presses go. The devices are in basements and behind flaky Wi-Fi, so some of them will not hear the instruction for a while, and some never will. Thirty minutes later the utility has to tell the grid operator how many megawatts actually came off, and the customer whose water heater did not respond has to not be charged for it.

**What a working system delivers**

- The operator presses go and, within seconds, sees the count of devices that received the instruction climbing — and the count that acknowledged it, and the count that rejected it.
- A thermostat that was offline at the moment of dispatch and comes back ten minutes later still gets the instruction, if there is still time for it to matter. If there is not, it does not.
- A device never runs an instruction twice, and never runs an old instruction after a newer one that cancelled it — including after a reboot.
- At the end, a funnel that adds up: targeted, delivered, acknowledged, executed, confirmed by the meter, timed out, unreachable. And the megawatts, measured, not modelled.
- An operator cannot accidentally shed a gigawatt, cannot send the same fleet the opposite instruction two minutes later, and can stop everything with one action that is faster than the thing it stops.

**Why this gets asked.** It is a workflow problem wearing a fanout costume. The fanout to ten million devices turns out to be cheap once you ask who evaluates the targeting rule; what is expensive is knowing, for every one of ten million pairs of campaign and device, which of eight states it is in — and closing the ones that never reported. Candidates spend the round on the cheap part.

---

**Archetype:** coordination / command workflow — one operator action fans out to millions of intermittently connected targets, each of which has to be driven through a state machine to a terminal state and reconciled when it does not report.
**Cousins that reuse ~70% of this page:** OTA firmware rollout, feature-flag rollout to a client fleet, bulk notification send, configuration push to devices or agents, payment retry orchestration, fleet job dispatch (robots, drones, POS terminals, CI runners). Also **any product where the question at the end is "which of the targets did it, and what happened to the rest."**

**What's actually being graded:** whether you draw the **per-target state machine before any service**, and then justify every box on the diagram by a transition it causes or records; whether you decide **where idempotency lives** and notice what that decision lets you delete; whether you distinguish **broadcast from unicast** and refuse to look up ten million devices in a registry to send one message; whether **safety** is mechanisms with numbers rather than an adjective; and — the one that decides staff versus senior — whether the minutes of the round go to the ten-million-device paths rather than to the three-megabyte table.

**Contrast to have ready:** *IDE settings sync pushes a hint — a version number — and the truth lives in a store the client will eventually read; nobody has to know which laptops applied it. This is the inverse: **the push is an actuation with a deadline**, the target has to say what it did, and the product is the funnel of who did it. Settings sync deletes the delivery guarantee and keeps the store; this page keeps the delivery guarantee and deletes almost every store the reflex reaches for. The telemetry that confirms the effect is the Smart-meter telemetry page; this page consumes its before-and-after delta and owns nothing about ingest.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "This is a command workflow: an operator creates a campaign — a targeting predicate, an instruction, a start time, a deadline — and ten million devices each have to move through a state machine and end up somewhere terminal, whether they reported or not. The prompt lists eleven topics, so I'm going to write them on the board as a checklist and tick them. Three things dominate. First, **the state machine comes before the boxes**: pending, delivered, acked or rejected, executed, measured, and the terminals for devices that never answered — every service I draw has to own a transition on it or I delete the service. Second, **idempotency lives on the device**: it persists the last campaign id it applied and ignores anything at or below it, which means delivery is at-least-once and the effect is exactly-once, and it means I do not need an outbox, a CDC pipeline, or a delivery-tracking table on the send side. Third, **broadcast versus unicast**: a campaign is a predicate, so I publish it once and let each of two hundred gateways evaluate it against the fifty thousand devices it holds — two hundred messages, not ten million registry lookups. The registry exists for the unicast case only. The campaign table itself is three megabytes over ten years and gets three minutes of this interview, not twelve. I'll scope out the telemetry pipeline — that's its own design and I'll draw it as one box that gives me a before-and-after delta with a coverage figure. I'll go deep on the state machine and its reconciliation, and on fanout without a registry."

**Why open this way:** it names the archetype as a workflow rather than a fanout, it puts the state machine first out loud so the interviewer watches you draw it, it pre-commits the two dives (§10, §8) and the one deletion (§7) that carry the round, and it states the time allocation — three minutes on the small table — before the reflex to build a job queue for it can take hold. The eleven-topic checklist on the board is not decoration: five of them are the ones that go to zero minutes when it is not there.

---

## 1 · Functional requirements

1. **An operator creates an immutable campaign** — a predicate over device attributes, an instruction with a start time and duration, a deadline, and a staged rollout — and **every matching device that is connected before the deadline receives it exactly once in effect**, including devices that were offline at creation and connect later.
2. **The system knows the state of every `(campaign, device)` pair** and, at the deadline, **reconciles the ones that never reported** into terminal states — including inferring from the meter that a silent device actually complied — so the funnel is exact when the regulator reads it.
3. **An operator can cancel, and the system enforces safety**: a cap on the load a campaign may move, staged rollout with abort thresholds, a second approver above a threshold, and a guard against sending a fleet the opposite instruction inside its settle window.

**Out of scope (say them):** the telemetry ingest pipeline and the measurement query (the Smart-meter telemetry page — this page calls its `/delta`), load forecasting and choosing *which* homes to target, device firmware beyond the three rules it must follow, customer enrolment and settlement credits, multi-utility tenancy, the operator UI.

**Below the line, likely follow-ups:** recurring and scheduled campaigns, a manual command to one device (unicast — §8), campaign templates and per-program defaults, a device that is in two overlapping campaigns, audit export for the regulator, multi-region control planes.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Creation → first connected device** | **p50 < 500 ms, p99 < 2 s** | One Postgres commit, one Kafka hop, one gateway push. **This is the only place a sub-second number is honest** — see the sentence below the table |
| **Stage fanout to connected devices** | **≤ 30 s** for all 200 gateways to finish pushing a stage | Each gateway evaluates one predicate against 50 k cached attribute sets and pushes to the matches. The bound is local CPU, not a network round trip per device |
| **Full campaign, three stages** | **~15 min**: 1 % → 10 % → 100 %, with a **5-minute hold** after each | The hold is the abort window — long enough for acks and a measured delta to come back and be compared to the threshold. **Safety sets this number, not throughput**, and saying so is the point |
| **Offline devices** | Receive the instruction **on reconnect, until `deadline`; nothing after** | A device that reconnects after the deadline must not shed load for a campaign that is over. **The deadline is the TTL** on every pending instruction, and it is the same number on the device and in the system |
| **Per-device ack timeout** | **60 s after delivery**, enforced by the gateway that delivered | A device that received and did not answer in a minute is not going to. An NFR with no component enforcing it is decoration — the enforcer is named in §9 |
| **Delivery vs effect** | **At-least-once delivery; exactly-once effect**, via a `last_seen_campaign_id` persisted on the device | Duplicates are free by construction, which is what makes every retry on this page a plain resend (§7) |
| **Ordering** | A device **never applies an older campaign after a newer one**; a cancel is a campaign with a higher id | Campaign ids are monotonic; the device keeps the highest it applied. Persisted, or a reboot reintroduces the bug (§7) |
| **Funnel** | **≤ 30 s stale during the campaign; exact within 10 min of the deadline** | The operator watches it live and reacts in minutes; the regulator reads it after close and needs it to add up. Two consumers, two consistency levels, one table (§10) |
| **Cancel** | Reaches every connected device **≤ 10 s**; the cancel path is **99.99 %** available and **has no approval gate** | The kill switch must be faster and more available than the thing it stops. It uses the same fanout path with a higher id — nothing special, which is why it is fast |
| **Safety** | Max delta per campaign (**e.g. 400 MW, a product number**); staged 1/10/100 % with abort on **reject rate > 2 %** or **measured delta < 50 % of expected** at any stage; **two-person approval above 100 MW**; **oscillation guard: no opposite-sign command to an overlapping target set within 15 min** | §11. Each is a mechanism with a number; the numbers are product decisions and should be said as such |
| **Fault tolerance** | Survives: **any gateway** (its 60 s timers are lost; the deadline sweeper closes the gap), **any stage worker** (its lease expires, another takes the stage; the duplicate stage message is a no-op at every gateway), **ClickHouse lagging** (Kafka buffers seven days). **Does not survive: loss of the control-plane Postgres primary without failover** — no new campaigns and no stage advances; stages already published keep running at the gateways; devices keep the instruction they have until its deadline, which bounds the blast radius | Name what dies. The bounded case — "in-flight stages finish, nothing new starts, and the deadline is the ceiling" — is a better answer than pretending Postgres is immortal |
| **Scale** | 10 M devices · 200 gateways · ~10 campaigns/day · **1 M telemetry readings/s** (the telemetry page) | §3 |

**The sentence that earns the point:** *"The NFR I refuse to write is 'p99 100 ms creation-to-fanout.' Ten million deliveries in a hundred milliseconds is a contradiction, not a target, and a design that drew it would be lying to itself. The honest version is three numbers with three enforcers: first connected device within a second, a stage across the connected fleet within thirty seconds, and a per-device timeout one minute after delivery — held by the gateway, because a timeout nobody enforces is decoration."*

---

## 3 · Numbers that reframe the problem

**200 gateways, and the fanout is 200 messages — not 10 million lookups**

- 10 M devices at **50 k connections per gateway** = **200 gateways**. Do the division on the board; the reviewed mock said 40, and every number downstream inherits the error.
- A campaign is a predicate. If each gateway evaluates it against the attributes of the 50 k devices it holds (cached at connect), **dispatch is one message to 200 consumers**. The alternative — look up each targeted device's gateway in a registry — is **10 M reads of a Redis key for one campaign**. That registry is the hottest key on the board, and the question to ask before drawing it is *"does this key need to exist?"* For broadcast, it does not (§8).

**The campaign table is 3 MB over ten years, and it gets three minutes**

- ~10 campaigns/day × 365 × 10 years ≈ **36 k rows** at ~100 B — **~3.6 MB**. One Postgres table, one lease column, one index on `deadline`.
- **Say the budget aloud:** *"this table is three megabytes; it gets one box and three minutes."* The reviewed mock spent twelve minutes building a job queue, workers, an outbox, CDC, and a delivery service for this path. **Time on the board should be proportional to load**, and this is the number that proves the campaign path has none.

**Per-pair events are 30–50 GB a day, and that is the only volume on the send side**

- Each of 10 M targets emits **3–5 events** per campaign (delivered, acked, executed, measured; or a terminal) → **30–50 M events per campaign, 300–500 M/day** at ~100 B → **30–50 GB/day**. Append-only, partitioned by campaign, queried by campaign. This is a columnar table (§12), and it is where the design's storage budget actually goes.
- For contrast, the outbox the reflex builds: 10 M rows *per campaign* in Postgres, 100 M/day, each written, leased, and deleted. **Partition by campaign and drop, or — better — do not build it** (§7).

**The ack storm is 300 k events a second, and one counter key cannot take it**

- The 100 % stage reaches ~9 M connected devices inside 30 s; each emits `delivered` and, within seconds, `acked` → **~18 M events in about a minute ≈ 300 k events/s peak**.
- Partitioned by `device_id` across 200 partitions that is 1.5 k/s per partition — trivial. Batched into a columnar store — trivial. **Incremented on a single Redis key `funnel:{campaign}:acked` — 300 k `INCR`/s on one shard, which is the hot-key failure in its purest form.** The funnel is a count over the event table, not a counter (§10, §12).

**Ten percent are offline, and five percent never come back — that is normal, not an incident**

- *Assumption:* ~10 % of devices are disconnected at any moment (basements, Wi-Fi, power). Of 10 M targets, **~1 M receive the instruction via reconnect** inside the deadline, and **~500 k never do**.
- Half a million `unreachable` per campaign is the expected shape of the funnel, and the reconciliation that produces it is a **set difference over 10 M ids** — targeted minus reported — which is seconds in a columnar store and a nightmare as 10 M point reads. This number decides §12's store.

**The telemetry is a million readings a second, and it is one box here**

- 10 M meters × 1 / 10 s = **1 M/s**. It is the highest-load path in the prompt by three orders of magnitude, and it is **its own design** — the Smart-meter telemetry page — with its own partition math, its own lateness policy, and its own store. On this board it is one box labelled *"gives me `/delta` with coverage,"* and the minutes it deserves are spent on that page, not squeezed into this one.

---

## 4 · Core entities

### Draw this first — the per-target state machine

```text
                          ┌──▶ rejected
pending ──▶ delivered ────┼──▶ acked ──▶ executed ──▶ measured
   │                      └──▶ timed_out ─ ─ ─ ▶ executed_silently   (inferred from the meter, after the deadline)
   └──▶ unreachable                     └──▶ acked_late   (recorded as an event; the state stays terminal)

   any non-terminal ──▶ cancelled       (a CANCEL campaign with a higher id)

   terminal: measured · rejected · timed_out · unreachable · executed_silently · cancelled
```

| Transition | Caused by | Component that owns it | Recorded where | Timer |
|---|---|---|---|---|
| **(creation) → pending** | Operator creates the campaign; the target set is snapshotted | Campaign API + one bulk insert | `campaign_targets` (ClickHouse) | starts the `deadline` clock |
| **pending → delivered** | A gateway pushes `CMD` to a connected, matching device — on stage publish, or on `HELLO` | Gateway | `device_events` | starts a **60 s ack timer on that gateway** |
| **delivered → acked / rejected** | The device answers `ACK {accepted}` or `ACK {rejected, reason}` | Device, via its gateway | `device_events` | stops the timer |
| **delivered → timed_out** | 60 s pass with no ack | **Gateway timer** | `device_events` | — |
| **acked → executed** | The device reports it applied the setpoint at `start_at` | Device | `device_events` | — |
| **executed → measured** | The meter's before/after delta for this device matches the expected effect | **Measurement job**, reading the telemetry page's `/delta` | `device_events` | runs at `start_at + 5 min` |
| **pending → unreachable** | The deadline passes and no `delivered` event exists for the pair | **Deadline sweeper** — a set difference, once per campaign | `device_events` | at `deadline` |
| **timed_out → executed_silently** | No ack, but the meter's delta says the device complied | **Inference job** (same run as the sweeper) | `device_events` | after `deadline` |
| **timed_out → (acked_late)** | An ack arrives after the timer fired | Gateway | `device_events` as a new event; state is not rewritten | — |
| **any non-terminal → cancelled** | A `CANCEL` campaign with a higher id reaches the device (or the deadline sweeper applies it to the unreached) | The same fanout path | `device_events` | — |

**The rule, and it is the whole method:** *every box drawn in §6 must appear in the "Component" column above, or it is deleted.* The reviewed mock's job queue, outbox, CDC pipeline, and delivery service own no row in this table. They are gone. The per-pair state itself is not stored anywhere — it is **`argMax(event, event_ts)` over the event log**, derived, and a Redis hash holding it would own no row either.

### The entities

- **Campaign** — `(campaign_id, predicate, command, start_at, duration_s, deadline, stages[], hold_s, max_delta_mw, approval, cancels?, created_by, created_at)`. **Immutable. `campaign_id` is a monotonic integer** issued by Postgres. A cancel is a new row whose `cancels` points at the old one.
- **Stage** — `(campaign_id, pct, seed, state, leased_until, published_at)`. The unit of work the stage worker leases with `FOR UPDATE SKIP LOCKED`.
- **Approval** — `(campaign_id, approver, at)`. Two rows required above the threshold; the second approver may not equal the first.
- **CampaignTarget** — `(campaign_id, device_id)`. The predicate evaluated once against the device dimension at creation and written in bulk — **the denominator of the funnel and the left side of the reconciliation set difference.**
- **DeviceEvent** — `(campaign_id, device_id, event, event_ts, gateway_id, detail)`. Append-only. **The only per-pair state in the system.**
- **Device** — the dimension: `device_id, region, type, program_tier, fw, attrs…` in Postgres, shared with the telemetry page, cached on each gateway per connection at `HELLO`.
- **On the device** — `last_seen_campaign_id`, the current setpoint and its `restore_at`. **In flash.**

**The four that are load-bearing:**

**`campaign_id` is both the idempotency key and the ordering token.** The device persists the highest id it has applied and ignores anything at or below it. That one rule makes a duplicate delivery a no-op, makes an old instruction arriving after a newer one a no-op, and makes a cancel — which is a *newer* campaign — win. Three problems, one integer, and the integer already exists.

**A cancel is a new campaign, not a mutation.** Campaigns are immutable, so "cancelled" cannot be a flag on the row — a flag races the delivery that is happening at that instant, and a device that has the old instruction in hand has no way to learn about the flag. A `CANCEL` with a higher id travels the same path as the original, reaches the same devices by the same predicate, and wins on the device by the ordering rule. **The kill switch is the normal path with a bigger number**, which is what makes it fast and what makes it trustworthy.

**State is derived from the event log.** Every transition is an appended event; "what state is device X in" is the latest event for the pair. There is no table to keep consistent with the log, no dual write, and no "which one is right" when they disagree — because there is only one. The cost is that the funnel is a query, and §10 pays it.

**The device persists `last_seen_campaign_id`.** In RAM, a reboot resets it to zero and the device re-applies whatever campaign it next hears about — including the one it already executed. The rule is only a rule if it survives a power cut, and a power cut is exactly the kind of event that happens during a demand response campaign.

---

## 5 · API

```text
POST /v1/campaigns                                        Idempotency-Key: <operator's key>
     { predicate: { region: "west", type: "thermostat", tier: "gold" },
       command:   { kind: "shed", kw: 2 },
       start_at, duration_s: 1800, deadline,              deadline ≤ start_at + duration_s
       stages: [1, 10, 100], hold_s: 300,
       max_delta_mw: 400, dry_run: false }
     → 201 { campaign_id: 9871, targeted: 1_042_311, expected_delta_mw: 380,
             approval: "required" }                       ← monotonic id; above 100 MW needs a second approver
     → 409 oscillation_guard { conflicts_with: 9868, settle_until }
     → 422 max_delta_exceeded

POST /v1/campaigns/{id}/approve                           → 200 | 409 same_principal
POST /v1/campaigns/{id}/cancel                            → 201 { campaign_id: 9872, cancels: 9871 }   a NEW campaign
POST /v1/campaigns/{id}/abort                             → 200   stop advancing stages; what is delivered stays delivered
GET  /v1/campaigns/{id}/funnel
     → 200 { targeted, delivered, acked, rejected, executed, measured,
             timed_out, unreachable, executed_silently, cancelled,
             freshness_s: 12, exact: false }               ← exact: true only after the deadline sweep
GET  /v1/campaigns/{id}/targets?state=timed_out&cursor=   paged from the event log

POST /v1/devices/{id}/commands                            unicast — the registry and the pending list exist for this (§8)

── device protocol, over MQTT or WebSocket through a gateway ────────────────────────────
HELLO  { device_id, attrs: { region, type, tier, fw }, last_seen_campaign_id }
       ← the gateway answers with every active campaign whose predicate matches,
         whose id > last_seen_campaign_id, and whose deadline > now
CMD    { campaign_id, command, start_at, duration_s, deadline }        at-least-once
ACK    { campaign_id, result: accepted | rejected, reason? }            idempotent on (campaign_id, device_id)
REPORT { campaign_id, executed_at, setpoint_applied }                   sent at start_at
```

**Decisions to narrate, unprompted:**

- **`cancel` returns a new `campaign_id`.** It is a campaign with a higher id whose instruction is "restore," and it goes out on the same path. The alternative — `PATCH state=cancelled` — is a flag that races every delivery in flight and that an already-delivered device can never see.
- **`HELLO` carries the device's attributes and its `last_seen_campaign_id`.** The first is what lets the gateway evaluate a predicate locally instead of asking a registry (§8). The second is what makes store-and-forward *computable*: the gateway does not need a per-device queue of pending instructions, because the device just told it exactly which campaigns it has not applied (§9).
- **`ACK` is idempotent on the pair.** A device that acks twice — because its first ack was lost and it re-sent on reconnect — produces two events and one state. Every consumer of the log treats the pair as the key.
- **The funnel carries `exact: false` until the sweep.** During the campaign the counts are approximate distinct counts, ≤ 30 s stale, and the field says so; after the sweep they are exact. Two consumers, two guarantees, and the response tells the caller which one it got.
- **`dry_run` returns `targeted` and `expected_delta_mw` and publishes nothing.** It is the cheapest safety control on the page — the operator sees "1.04 M devices, 380 MW" before anything moves — and it costs one query against the device dimension.
- **`abort` is not `cancel`.** Abort stops the stage worker from advancing; devices already told keep the instruction. Cancel reverses it. An operator who sees a 3 % reject rate at the 10 % stage wants abort; one who sees the grid frequency swing wants cancel. Both exist, and the difference is said aloud.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 640" role="img" aria-label="Demand response architecture. Control plane: a campaign API with the safety checks, Postgres holding campaigns, stages and approvals, and a stage worker that leases a stage and publishes it once. Fanout: a tiny Kafka commands topic consumed by two hundred gateways that evaluate the predicate locally against cached device attributes and hold a sixty-second ack timer per delivery. Device edge: devices that persist the last campaign id in flash and apply only higher ids, and the meter whose readings go to the telemetry page. Receive side: device events keyed by device into Kafka, then ClickHouse partitioned by campaign, with the funnel as a materialized view; a deadline sweeper that runs once per campaign and reads the meter delta for silent devices.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Idempotency lives on the device, so there is no outbox; the predicate is evaluated at the edge, so there is no registry lookup.</text>
  <rect class="dg-group" x="20" y="86" width="300" height="250" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">CONTROL PLANE — 3 MB, THREE MINUTES</text>
  <rect class="dg-box" x="36" y="118" width="268" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="134.5">Campaign API</text>
  <text class="dg-s dg-c" x="170" y="150.5">dry run · max delta · oscillation guard</text>
  <text class="dg-s dg-c" x="170" y="166.5">two-person approval above 100 MW</text>
  <path class="dg-box" d="M 36,197 L 36,239 A 134,7 0 0 0 304,239 L 304,197 A 134,7 0 0 0 36,197 Z"></path>
  <path class="dg-box" d="M 36,197 A 134,7 0 0 0 304,197" style="fill:none"></path>
  <text class="dg-t dg-c" x="170" y="210">Postgres</text>
  <text class="dg-s dg-c" x="170" y="226">campaigns · stages · approvals</text>
  <text class="dg-s dg-c" x="170" y="242">monotonic id · deadline index</text>
  <rect class="dg-box" x="36" y="262" width="268" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="278.5">Stage worker</text>
  <text class="dg-s dg-c" x="170" y="294.5">FOR UPDATE SKIP LOCKED · 1 → 10 → 100 %</text>
  <text class="dg-s dg-c" x="170" y="310.5">hold 5 min · abort on thresholds</text>
  <path class="dg-line" d="M 170,174 L 170,182"></path>
  <path class="dg-head" d="M 165,182 L 175,182 L 170,190 Z"></path>
  <path class="dg-line" d="M 170,246 L 170,254"></path>
  <path class="dg-head" d="M 165,254 L 175,254 L 170,262 Z"></path>
  <rect class="dg-group" x="350" y="86" width="280" height="250" rx="12"></rect>
  <text class="dg-group-t" x="366" y="108">FANOUT</text>
  <rect class="dg-box" x="366" y="118" width="248" height="56" rx="8"></rect>
  <path class="dg-qbar" d="M 379,127 L 379,165"></path>
  <path class="dg-qbar" d="M 388,127 L 388,165"></path>
  <path class="dg-qbar" d="M 397,127 L 397,165"></path>
  <text class="dg-t dg-c" x="508" y="142.5">Kafka commands</text>
  <text class="dg-s dg-c" x="508" y="158.5">1 message per stage · 200 consumers</text>
  <path class="dg-line" d="M 304,290 L 336,290 L 336,146 L 358,146"></path>
  <path class="dg-head" d="M 358,151 L 358,141 L 366,146 Z"></path>
  <text class="dg-lbl dg-c" x="336" y="138">1 msg</text>
  <rect class="dg-box" x="366" y="198" width="248" height="110" rx="8"></rect>
  <text class="dg-t dg-c" x="490" y="225.5">Gateways ×200</text>
  <text class="dg-s dg-c" x="490" y="241.5">50 k sockets · attrs cached at HELLO</text>
  <text class="dg-s dg-c" x="490" y="257.5">evaluate predicate + stage hash locally</text>
  <text class="dg-s dg-c" x="490" y="273.5">60 s ack timer per delivery</text>
  <text class="dg-s dg-c" x="490" y="289.5">active campaign list, from Postgres</text>
  <path class="dg-line" d="M 490,174 L 490,190"></path>
  <path class="dg-head" d="M 485,190 L 495,190 L 490,198 Z"></path>
  <rect class="dg-group" x="660" y="86" width="320" height="250" rx="12"></rect>
  <text class="dg-group-t" x="676" y="108">DEVICE EDGE</text>
  <rect class="dg-box" x="676" y="118" width="288" height="96" rx="8"></rect>
  <text class="dg-t dg-c" x="820" y="146.5">Device</text>
  <text class="dg-s dg-c" x="820" y="162.5">flash: last_seen_campaign_id · setpoint</text>
  <text class="dg-s dg-c" x="820" y="178.5">applies only id &gt; last_seen · respects deadline</text>
  <text class="dg-s dg-c" x="820" y="194.5">HELLO {attrs, last_seen} on reconnect</text>
  <path class="dg-line" d="M 614,240 L 640,240 L 640,150 L 668,150"></path>
  <path class="dg-head" d="M 668,155 L 668,145 L 676,150 Z"></path>
  <text class="dg-lbl" x="646" y="205">CMD</text>
  <path class="dg-line" d="M 676,190 L 650,190 L 650,280 L 622,280"></path>
  <path class="dg-head" d="M 622,275 L 622,285 L 614,280 Z"></path>
  <text class="dg-lbl dg-c" x="632" y="298">ACK</text>
  <path class="dg-box" d="M 676,247 L 676,289 A 144,7 0 0 0 964,289 L 964,247 A 144,7 0 0 0 676,247 Z"></path>
  <path class="dg-box" d="M 676,247 A 144,7 0 0 0 964,247" style="fill:none"></path>
  <text class="dg-t dg-c" x="820" y="260">Meter</text>
  <text class="dg-s dg-c" x="820" y="276">1 M readings/s → the telemetry page</text>
  <text class="dg-s dg-c" x="820" y="292">/delta with coverage</text>
  <rect class="dg-box" x="350" y="380" width="280" height="56" rx="8"></rect>
  <path class="dg-qbar" d="M 363,389 L 363,427"></path>
  <path class="dg-qbar" d="M 372,389 L 372,427"></path>
  <path class="dg-qbar" d="M 381,389 L 381,427"></path>
  <text class="dg-t dg-c" x="508" y="404.5">Kafka device_events</text>
  <text class="dg-s dg-c" x="508" y="420.5">key device_id · 200 partitions · RF 3</text>
  <path class="dg-line" d="M 490,308 L 490,372"></path>
  <path class="dg-head" d="M 485,372 L 495,372 L 490,380 Z"></path>
  <text class="dg-lbl" x="500" y="350">delivered · acked · rejected · timed_out · executed</text>
  <path class="dg-box" d="M 350,477 L 350,553 A 140,7 0 0 0 630,553 L 630,477 A 140,7 0 0 0 350,477 Z"></path>
  <path class="dg-box" d="M 350,477 A 140,7 0 0 0 630,477" style="fill:none"></path>
  <text class="dg-t dg-c" x="490" y="499">ClickHouse</text>
  <text class="dg-s dg-c" x="490" y="515">device_events · PARTITION BY campaign</text>
  <text class="dg-s dg-c" x="490" y="531">campaign_targets · bulk insert</text>
  <text class="dg-s dg-c" x="490" y="547">funnel = materialized view, uniq()</text>
  <path class="dg-line" d="M 490,436 L 490,462"></path>
  <path class="dg-head" d="M 485,462 L 495,462 L 490,470 Z"></path>
  <rect class="dg-box" x="660" y="470" width="300" height="90" rx="8"></rect>
  <text class="dg-t dg-c" x="810" y="495.5">Deadline sweeper + inference</text>
  <text class="dg-s dg-c" x="810" y="511.5">targets − reported → unreachable</text>
  <text class="dg-s dg-c" x="810" y="527.5">delivered, no successor → timed_out</text>
  <text class="dg-s dg-c" x="810" y="543.5">timed_out + meter delta → executed_silently</text>
  <path class="dg-line" d="M 630,515 L 652,515"></path>
  <path class="dg-head" d="M 652,520 L 652,510 L 660,515 Z"></path>
  <text class="dg-lbl dg-c" x="645" y="462">once, at deadline</text>
  <path class="dg-line" d="M 820,296 L 820,462"></path>
  <path class="dg-head" d="M 815,462 L 825,462 L 820,470 Z"></path>
  <text class="dg-lbl" x="828" y="400">/delta per silent device</text>
  <rect class="dg-box" x="36" y="470" width="280" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="176" y="494.5">GET /campaigns/{id}/funnel</text>
  <text class="dg-s dg-c" x="176" y="510.5">≤ 30 s stale during · exact after the sweep</text>
  <path class="dg-line" d="M 350,498 L 324,498"></path>
  <path class="dg-head" d="M 324,493 L 324,503 L 316,498 Z"></path>
  <text class="dg-s" x="20" y="600">The per-pair state is not stored: it is the latest event in the log. A Redis hash per campaign would be a ten-million-field key on one shard.</text>
  <text class="dg-note" x="20" y="622">Time on the board is proportional to load: the control plane is three megabytes and gets three minutes; the fanout, the events, and the meter get the rest.</text>
</svg>
</div>

<p class="diagram-cap">Draw the state machine before any of this, then draw the control plane small. The two arrows to label are the one leaving the stage worker — one message — and the one leaving the gateways — ten million pushes with no lookup in between. The registry and the outbox are the boxes this board is missing on purpose, and saying why they are missing is worth more than drawing either.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 620" role="img" aria-label="Demand response high-level design in three lanes. Create: a campaign request passes the safety guards, gets a monotonic id, snapshots its targets in one bulk insert, and a stage worker leases and publishes stage one. Deliver: each gateway evaluates the predicate and the stage hash against its cached attributes; a connected device is pushed the command with a sixty-second timer and moves to delivered, then acked and executed on its replies, or timed out when the timer fires; an offline device is evaluated the same way on its later HELLO, only if the deadline has not passed. Close: once at the deadline, targets minus reported become unreachable, delivered with no successor becomes timed out, timed out with a matching meter delta becomes executed silently, and the funnel becomes exact. A cancel is a new campaign with a higher id on the same path.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Every box owns a transition or it is deleted: the device decides idempotency, the gateway delivery, the sweeper closure.</text>
  <text class="dg-lane" x="30" y="76">CREATE — SAFETY BEFORE FANOUT</text>
  <rect class="dg-box" x="30" y="90" width="220" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="110.5">POST /campaigns</text>
  <text class="dg-s dg-c" x="140" y="126.5">predicate · command · deadline</text>
  <text class="dg-s dg-c" x="140" y="142.5">stages 1/10/100 · hold 5 min</text>
  <rect class="dg-warn" x="280" y="90" width="240" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="400" y="118.5">max delta · oscillation · approval</text>
  <text class="dg-s dg-c" x="400" y="134.5">422 · 409 · wait for a 2nd approver</text>
  <path class="dg-line" d="M 250,122 L 272,122"></path>
  <path class="dg-head" d="M 272,127 L 272,117 L 280,122 Z"></path>
  <rect class="dg-good" x="550" y="90" width="200" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="650" y="110.5">campaign_id = 9871</text>
  <text class="dg-s dg-c" x="650" y="126.5">monotonic · immutable</text>
  <text class="dg-s dg-c" x="650" y="142.5">targets → one bulk insert</text>
  <path class="dg-line" d="M 520,122 L 542,122"></path>
  <path class="dg-head" d="M 542,127 L 542,117 L 550,122 Z"></path>
  <rect class="dg-box" x="780" y="90" width="200" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="880" y="118.5">stage worker leases stage 1</text>
  <text class="dg-s dg-c" x="880" y="134.5">SKIP LOCKED · publish once</text>
  <path class="dg-line" d="M 750,122 L 772,122"></path>
  <path class="dg-head" d="M 772,127 L 772,117 L 780,122 Z"></path>
  <path class="dg-div" d="M 20,176 L 980,176"></path>
  <text class="dg-lane" x="30" y="210">DELIVER — THE GATEWAY DECIDES, PER CONNECTION</text>
  <rect class="dg-box" x="30" y="224" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="252.5">gateway: predicate ∧ hash &lt; pct</text>
  <text class="dg-s dg-c" x="180" y="268.5">against 50 k cached attribute sets</text>
  <rect class="dg-box" x="360" y="224" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="510" y="252.5">connected → push CMD, 60 s timer</text>
  <text class="dg-s dg-c" x="510" y="268.5">→ delivered</text>
  <path class="dg-line" d="M 330,256 L 352,256"></path>
  <path class="dg-head" d="M 352,261 L 352,251 L 360,256 Z"></path>
  <rect class="dg-good" x="690" y="224" width="270" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="825" y="252.5">ACK → acked · REPORT → executed</text>
  <text class="dg-s dg-c" x="825" y="268.5">idempotent on (campaign, device)</text>
  <path class="dg-line" d="M 660,256 L 682,256"></path>
  <path class="dg-head" d="M 682,261 L 682,251 L 690,256 Z"></path>
  <rect class="dg-warn" x="690" y="306" width="270" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="825" y="330.5">timer fires → timed_out</text>
  <text class="dg-s dg-c" x="825" y="346.5">a lost timer closes at the deadline</text>
  <path class="dg-line" d="M 640,288 L 640,334 L 682,334"></path>
  <path class="dg-head" d="M 682,339 L 682,329 L 690,334 Z"></path>
  <rect class="dg-box" x="360" y="306" width="300" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="510" y="330.5">offline → nothing stored</text>
  <text class="dg-s dg-c" x="510" y="346.5">HELLO {attrs, last_seen} later → same evaluation</text>
  <text class="dg-s dg-c" x="510" y="362.5">only if deadline &gt; now</text>
  <path class="dg-line" d="M 180,288 L 180,342 L 352,342"></path>
  <path class="dg-head" d="M 352,347 L 352,337 L 360,342 Z"></path>
  <text class="dg-lbl dg-c" x="270" y="336">not connected</text>
  <text class="dg-s" x="30" y="396">Device rule: apply only campaign_id &gt; last_seen (persisted in flash), never past deadline, ascending order if several arrive at once.</text>
  <path class="dg-div" d="M 20,412 L 980,412"></path>
  <text class="dg-lane" x="30" y="446">CLOSE — ONCE, AT THE DEADLINE</text>
  <rect class="dg-box" x="30" y="460" width="220" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="488.5">targets − reported</text>
  <text class="dg-s dg-c" x="140" y="504.5">→ unreachable</text>
  <rect class="dg-box" x="280" y="460" width="220" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="390" y="488.5">delivered, no successor</text>
  <text class="dg-s dg-c" x="390" y="504.5">→ timed_out</text>
  <rect class="dg-box" x="530" y="460" width="230" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="645" y="488.5">timed_out + meter ≥ 70 %</text>
  <text class="dg-s dg-c" x="645" y="504.5">→ executed_silently</text>
  <rect class="dg-good" x="790" y="460" width="170" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="875" y="488.5">funnel exact: true</text>
  <text class="dg-s dg-c" x="875" y="504.5">snapshot → campaign row</text>
  <path class="dg-line" d="M 250,492 L 272,492"></path>
  <path class="dg-head" d="M 272,497 L 272,487 L 280,492 Z"></path>
  <path class="dg-line" d="M 500,492 L 522,492"></path>
  <path class="dg-head" d="M 522,497 L 522,487 L 530,492 Z"></path>
  <path class="dg-line" d="M 760,492 L 782,492"></path>
  <path class="dg-head" d="M 782,497 L 782,487 L 790,492 Z"></path>
  <rect class="dg-warn" x="30" y="546" width="930" height="44" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="495" y="572.5">CANCEL = a new campaign with a higher id, same path, no approval gate, ≤ 10 s — the device applies it because newer wins</text>
  <text class="dg-note" x="30" y="610">A late ACK after the sweep is recorded as acked_late; the terminal state and the filed funnel do not change.</text>
</svg>
</div>

<p class="diagram-cap">Read the middle lane left to right and notice what is absent: no lookup, no queue per device, no retry loop. The offline branch is the reconnect hook, and it is a computation over one integer the device brought with it. The bottom lane is what “reconcile late or missing reports” means — three queries, once, and then the number is exact.</p>

### Flow A — an operator presses go

1. `POST /v1/campaigns`. The API evaluates the predicate against the device dimension for a count and an expected delta, checks `max_delta_mw`, checks the oscillation guard against recent campaigns on overlapping predicates (§11), and inserts the campaign and its three stage rows in one Postgres transaction. `campaign_id = 9871`.
2. In the same transaction's wake, one **bulk insert** of the 1.04 M matching device ids into `campaign_targets` in ClickHouse — a single columnar write, seconds. Not 1.04 M queue rows.
3. Above the approval threshold the campaign waits for a second approver; otherwise the first stage row is `ready` at `start_at − lead`.
4. The **stage worker** leases the stage row (`FOR UPDATE SKIP LOCKED`), publishes **one message** to Kafka `commands`: `{campaign_id: 9871, pct: 1, seed, predicate, command, start_at, duration_s, deadline}`, marks the row `published`.
5. **Every one of the 200 gateways** consumes the message, evaluates the predicate against its cached attributes for its ~50 k connected devices, applies the stage bucket `hash(device_id, seed) % 100 < 1`, pushes `CMD` to the ~500 matches, **starts a 60 s timer per delivery**, and emits `delivered` events to `device_events`, keyed by `device_id`.
6. Devices answer `ACK`; the gateway stops the timer and emits `acked`. At `start_at` they `REPORT`; the gateway emits `executed`.
7. After the 5-minute hold the stage worker reads the funnel and the measured delta for the stage (§11): reject rate under 2 %, delta over 50 % of expected → it leases stage 2. Same message, `pct: 10`. Then 100.
8. **The failure path.** The stage worker dies between publishing and marking the row. Its lease expires; another worker leases the row and **publishes the stage again**. Every gateway keeps a small set of `(campaign_id, pct)` it has processed and treats the duplicate as a no-op; if a gateway had also restarted and lost that set, it re-pushes `CMD` to devices that **dedupe on `campaign_id`** and ignore it. Two layers of idempotency, neither of them a database, and the duplicate costs a few hundred kilobytes of socket traffic. **This is the flow the outbox was going to protect, and it is protected without one.**

### Flow B — a device that was in the basement

1. A thermostat lost Wi-Fi at 13:50. The campaign was created at 14:00 with `start_at 14:15`, `deadline 14:30`. Its gateway evaluated the predicate over connected devices at 14:00; this device was not among them.
2. At 14:12 it reconnects — to a different gateway — and sends `HELLO {attrs, last_seen_campaign_id: 9865}`.
3. The gateway holds the **active campaign list** — every campaign with `deadline > now`, a few dozen rows, loaded from Postgres at boot and kept current by the `commands` topic. It evaluates each predicate against the device's attributes, keeps the ones with `id > 9865` whose stage bucket includes this device, and pushes `CMD` for 9871. Timer starts; `delivered` is emitted. **Nothing was stored per device to make this happen.**
4. The device acks, applies the setpoint at 14:15, reports. Its path through the funnel is identical to Flow A's, three minutes behind.
5. A neighbour reconnects at 14:35. Same `HELLO`, same evaluation, but 9871's deadline has passed: **it is not sent**, and at the sweep (Flow C) this pair is `unreachable`. The instruction that would have arrived at 14:35 was for a window that ended at 14:30; delivering it would have shed load the grid no longer needed.
6. **The failure path.** The gateway dies at 14:13, after pushing `CMD` and before the ack. Its timer dies with it. The device's ack goes to the gateway it reconnects to, which emits `acked` — the pair is fine. If the device had *not* acked, no `timed_out` event is ever emitted for it; **the deadline sweeper** finds `delivered` with no successor after 14:30 and closes it as `timed_out` then. The state machine's terminal is reached late rather than never, and that is the whole cost of keeping the timer local.

### Flow C — the deadline, and what "reconcile late or missing reports" means

1. At `deadline + 60 s` a **sweeper job** — one per campaign, scheduled off the campaign row's `deadline` index — runs a single query: `campaign_targets` for 9871 **minus** device ids with any event for 9871. ~500 k ids. It appends `unreachable` for each.
2. Second query: pairs whose latest event is `delivered` (timer lost to a gateway crash) → `timed_out`.
3. Third: pairs whose latest event is `timed_out`. For those, the job asks the telemetry page, per device, for the before/after delta over the command window. Where the meter dropped by the expected amount within tolerance — say 70 % of the commanded shed — it appends **`executed_silently`**. The device did the thing and never said so; the meter is the witness.
4. The funnel query now returns `exact: true`. The campaign row gets a snapshot of the final counts and the measured megawatts written back to Postgres, and that snapshot is what the regulator's report reads.
5. **The failure path.** An ack for 9871 arrives at 14:41 from a device the sweep closed as `timed_out` at 14:31. The gateway appends **`acked_late`** — a new event. The state does not change; the funnel does not move; the event is there for the customer-credit dispute that will ask "did my water heater respond?" **Terminal states are terminal; late facts are still recorded.** A design that rewrote `timed_out` to `acked` would have a funnel that changes after the report was filed.

### Flow D — cancel, mid-campaign

1. At 14:20 the grid operator says stop. `POST /v1/campaigns/9871/cancel` inserts campaign **9872** with `cancels: 9871`, the same predicate, `command: restore`, `stages: [100]`, `hold_s: 0`, and **no approval gate**.
2. The stage worker publishes it — one message — and 200 gateways push `CMD 9872` to every connected device matching the predicate, ~10 s end to end. Devices with `last_seen 9871` apply 9872 (it is higher), restore their setpoint, ack.
3. The sweeper for 9871 runs at its deadline as usual, but pairs whose latest event is `cancelled` — appended by the gateways as 9872 was acked — are excluded from `unreachable` and `timed_out`. The funnel for 9871 shows how far it got before it was stopped.
4. **The oscillation guard is not involved** — a cancel restores baseline and is always allowed. What the guard blocks is the operator creating a *new* shed campaign on the same region at 14:25 because the frequency dipped again: `409 oscillation_guard, settle_until 14:35`.
5. **The failure path.** A device offline since 13:50 reconnects at 14:22 and receives **both** 9871 and 9872 in the same `HELLO` response. It applies them **in ascending id order** — shed, then restore — and ends in the right state, because the ordering rule is per-id and not per-arrival. Had the gateway sent only the highest, the result would be the same; it sends both so that the event log records that the device was told to shed and told to stop. Either way, **the cancel wins because it is newer, and newer is a number the device already keeps.**

---

## 7 · Deep dive — where idempotency lives, and the outbox you don't need

### What you'd reach for first

Campaign created → job queue → workers expand the target set → write 10 M rows to an outbox table in the same transaction → CDC tails the outbox into Kafka → a delivery service consumes Kafka, looks up each device's gateway, and pushes. Exactly-once delivery, textbook.

This is the path the reviewed mock spent twelve minutes on.

### What breaks

- **100 M outbox rows a day**, each inserted, leased, published, and deleted, in Postgres, for a system whose only real table is three megabytes. The outbox is bigger than everything it protects by five orders of magnitude.
- **The dual-write problem it solves does not exist here.** The outbox pattern exists so that "write the campaign" and "publish the fanout" cannot half-succeed. But a fanout worker that dies halfway can simply **start over and republish every `(campaign, device)`** — as long as the *consumer* dedupes. The question is not "how do I make publishing atomic," it is **"who dedupes?"** — and the answer decides whether the outbox exists.
- **It moved the hard problem to the wrong place.** Exactly-once *delivery* to a device over a flaky socket is impossible — the ack can always be lost. Exactly-once *effect* is easy if the device keeps one integer. Building delivery-side machinery for a guarantee the receiver has to provide anyway is paying twice.

### What replaces it

**Idempotency lives on the device, and the send side is allowed to be sloppy.**

- **The device persists `last_seen_campaign_id` in flash** and applies a `CMD` only if `campaign_id > last_seen`. A duplicate is a no-op. An old instruction after a newer one is a no-op. A cancel — a higher id — wins. One comparison, one integer, one flash write.
- **Every gateway also dedupes stage messages** on `(campaign_id, pct)`, an in-memory set of a few hundred entries, so a republished stage is a no-op at the gateway and does not even reach the socket. This is a courtesy, not a correctness mechanism — remove it and the device still dedupes.
- **The stage worker is therefore free to be at-least-once**: lease the stage row, publish, mark. Die anywhere in between and the next worker republishes. There is no outbox, no CDC, no delivery-tracking table, and no delivery service — the gateways *are* the delivery service, and the tracking is the event log they write.
- **The rule, stated generally:** *decide where idempotency lives before adding any component whose only job is exactly-once-ish delivery. It usually lets you delete a box.* On this page it deletes four.

**Cost, volunteered:**

- **A firmware requirement.** The device must persist the id, and must persist it *before* acking. A device that acks and then loses power before the flash write will re-execute on the next delivery. Bound: one extra execution of an instruction the device already agreed to, inside the same campaign window — and the oscillation guard means the worst case is "shed for thirty minutes" happening once, not a flapping setpoint.
- **Duplicate socket traffic.** A republished stage sends ~50 k `CMD`s per gateway that the devices will discard. Kilobytes per device, once, on the rare path.
- **The event log will contain duplicate `delivered` events** for a pair, and every consumer keys on the pair. Distinct counts, not row counts, everywhere in §10 — and the honest note that the live funnel is approximate because of it.

**→ ties to the delivery-vs-effect and ordering NFRs.**

---

## 8 · Deep dive — broadcast vs unicast: fanout without the registry lookup

### What you'd reach for first

A registry: `device_id → gateway_id` in Redis, heartbeat TTL. To send a campaign, expand the target set to 10 M device ids, look each one up, and route the message to its gateway.

### What breaks

- **10 M Redis reads per campaign** — for a campaign that is *one predicate*. The registry is the hottest key on the board by a factor of ten million over anything else, and the question the reviewed mock never asked is the one to ask before drawing it: **"does this key need to exist?"**
- **The registry is stale by construction.** A device reconnects to a different gateway between the lookup and the push, and the push goes to a socket that no longer holds it. Now the delivery service needs a retry loop, and the retry loop needs the very reconnect hook (§9) that makes the lookup unnecessary in the first place.
- **The gateways already know the answer.** Each one holds the attributes of the 50 k devices connected to it — they arrived in `HELLO`. Asking a central store "which of my devices match?" is asking someone else a question you can answer locally.

### What replaces it

**Broadcast the predicate; evaluate it at the edge. The registry exists for unicast only.**

- **Publish the campaign once** to Kafka `commands` — a tiny topic, one message per stage, ~10 messages a day. **Every gateway is its own consumer** (200 consumer groups on a topic that fits in memory; or, equivalently, every gateway reads from the latest offset and loads the active campaign list from Postgres at boot — the topic is a notification, Postgres is the truth).
- **Each gateway evaluates the predicate against its own connected set** — 50 k attribute records in memory, a predicate is a few comparisons, tens of milliseconds — and pushes to the matches. **200 messages in, 10 M pushes out, zero lookups.** The same evaluation runs on every `HELLO` for the reconnect case (§9).
- **Staged rollout is a hash, not a list.** `hash(device_id, seed) % 100 < pct` at each gateway gives a consistent 1 %, then 10 %, then 100 % — the 1 % is a subset of the 10 % — with no central list of who is in which stage.
- **Unicast — "reboot device 4471" from support — is the case the registry is for.** `device_id → gateway_id` in Redis with a 30 s heartbeat TTL, plus a **per-device pending list** (`Redis LPUSH`, `EXPIRE` at the command's deadline) drained on `HELLO`, because a single-device command has no predicate for the gateway to evaluate. Both exist; **the broadcast path never reads either**, and a design that draws them should say which path they serve.
- **Redis Pub/Sub versus Redis as a registry — say which is which, because the mock conflated them.** *Pub/Sub* is a fire-and-forget fanout transport: publish a campaign notification, every subscribed gateway gets it, and any gateway that was reconnecting at that instant **never does** — no persistence, no replay. It is a plausible alternative to the `commands` topic and a worse one, for exactly that reason. *A registry* is a TTL'd key-value map used for unicast routing. Two products in one binary, one for transport and one for lookup, and neither is what makes broadcast work.

**Cost, volunteered:**

- **Attribute freshness.** A device's `tier` changes in the dimension at 14:05; the gateway's cache says `silver` until the device reconnects. Bound it: gateways refresh cached attributes from the dimension every 15 minutes, or the dimension publishes changes to a topic the gateways consume. Say the staleness — *"a predicate is evaluated against attributes at most fifteen minutes old"* — and it is a requirement rather than a bug.
- **A gateway restart re-caches 50 k attribute sets** as devices reconnect, over the reconnect jitter window. Fine; that is why `HELLO` carries them.
- **The targeted count in the funnel comes from the dimension, not from the gateways.** The denominator is evaluated centrally at creation; the numerator is evaluated at the edge. If they disagree by a few hundred devices because of attribute staleness, the funnel shows it as `unreachable`, which is honest and slightly pessimistic.

**→ ties to the stage-fanout and creation-to-first-device NFRs.**

---

## 9 · Deep dive — retries are a reconnect hook: store-and-forward, the deadline as TTL, and who holds the timer

### What you'd reach for first

A retry loop: push `CMD`, wait for the ack, on timeout push again with backoff, up to *n* times, then mark failed. And a central "timeout service" that scans for devices in `delivered` older than 60 s.

### What breaks

- **A device that is offline is not going to answer the second push either.** "Intermittently connected" means the retry that matters is the one that happens *when the device comes back*, which could be an hour later, from a different gateway. A backoff loop against a dead socket is retrying the wrong thing.
- **The central scan is a 10 M-row query every minute** — `WHERE state = 'delivered' AND delivered_at < now() − 60 s` — against a table that is also taking 300 k writes a second. Indexed on `(state, delivered_at)` it is still a scan of every in-flight pair, sixty times per campaign.
- **The stated NFR — "60 s ack timeout" — has no owner.** The reviewed mock wrote it in §2 and nothing on the diagram enforced it. A timeout that no component fires is decoration.

### What replaces it

**Three mechanisms, each with one job.**

- **Store-and-forward is the `HELLO` evaluation, not a store.** On reconnect the device says `last_seen_campaign_id`; the gateway evaluates every active campaign with a higher id and an unexpired deadline against the device's attributes, and pushes the ones that match. The "pending instructions for this device" were never written anywhere — they are computed from a list of a few dozen campaigns and one integer the device brought with it. **Retries are a reconnect hook**, and the hook needs no per-device state on the server.
- **The deadline is the TTL, and it is the same number everywhere.** The gateway will not push a campaign past its deadline; the device will not apply one (it has `deadline` in the `CMD`); the sweeper closes the pair at the deadline. There is no separate retry budget, retry count, or expiry to keep consistent with the deadline — there is only the deadline.
- **The 60 s ack timer lives on the gateway that delivered.** It pushed the `CMD`; it holds the socket; it has a timer wheel with one entry per in-flight delivery — ~50 k at the peak of a stage, in memory. When it fires, the gateway emits `timed_out`. No scan, no central service, and the NFR has an owner. When the gateway dies, its timers die, and **the deadline sweeper** (§10) is the backstop: `delivered` with no successor at the deadline → `timed_out`, late rather than never.
- **The sweeper is one query per campaign, scheduled off the campaign row.** Postgres has an index on `deadline`; a scheduler picks up campaigns whose deadline has passed and runs the set-difference and the inference (§10) once. Not sixty scans per campaign — one, at the moment there is something to close.

**Cost, volunteered:**

- **A timer lost to a gateway crash is closed at the deadline, not at 60 s.** For a 15-minute campaign a small fraction of pairs reach `timed_out` up to 14 minutes late. The funnel is slightly optimistic during that window and exact after the sweep, which is the guarantee §2 already made.
- **A device that missed two campaigns receives both on reconnect** and must apply them in id order. That is a firmware rule, and it is the third one (after "persist the id" and "respect the deadline"). Three rules; write them on the board.
- **The active campaign list is state on every gateway** — a few dozen rows, loaded at boot, updated by the `commands` topic. A gateway that boots with Postgres unavailable serves connections but delivers nothing until the list loads. Say it; it is the same dependency §2's fault-tolerance row already named.

**→ ties to the offline-devices and per-device-ack-timeout NFRs.**

---

## 10 · Deep dive — reconciliation is a state machine plus a sweeper, and the meter closes the loop

### What you'd reach for first

"We'll have a reconciliation job." And a per-pair state table — Postgres, or a Redis hash per campaign with 10 M fields — updated on every event, so the funnel is a `GROUP BY state`.

### What breaks

- **A reconciliation job with no definition of what it reconciles.** *Late* means what? *Missing* means what? Without the state machine there is no list of non-terminal states to close and no rule for closing each, so the job is a name on a box.
- **The per-pair state table is a second source of truth.** It is updated from the events; the events are the truth; when they disagree — a lost update, a crashed writer — which is right? Now there is a reconciliation job *for the reconciliation table*.
- **The Redis hash is the hottest key on the page.** 10 M fields on one key live on one shard; 300 k `HSET`/s at the ack peak is the ceiling of a single Redis node, on the one campaign everybody is watching. **A Postgres table partitioned by campaign** takes the writes with batched upserts but is now a 100 M-row/day table that exists to answer a query the event log already answers.
- **`GROUP BY state` on 10 M rows for a live dashboard**, polled by every operator every few seconds.

### What replaces it

**The state machine defines what is open; a sweeper closes it at the deadline; the meter is the witness for the silent; and the funnel is a count over the log.**

- **Two definitions.** *Missing* = a pair with no `delivered` at the deadline → `unreachable`. *Late* = a pair whose latest event is `delivered` or `timed_out` at the deadline → `timed_out`, then tested for `executed_silently`. The sweeper is the list of non-terminal states with one rule each (§4), executed once.
- **The set difference is a columnar query.** `campaign_targets` minus `device_events` for one campaign is 10 M against 10 M in ClickHouse: seconds. As 10 M point reads against a per-device store it is a batch job with a progress bar.
- **Telemetry-based inference.** For each `timed_out` pair the sweeper reads the meter's before/after delta from the Smart-meter telemetry page (its §9 supplies the reading and a coverage flag; **this page owns the threshold**: a drop ≥ 70 % of the commanded shed, sustained over the window, counts). Devices that complied but whose ack was lost are `executed_silently`. This is what "reconcile late or missing reports" *means* in the prompt: a sweeper plus a side channel, and the side channel is the meter.
- **The per-pair state is `argMax(event, event_ts)` over the log, and it is not stored.** There is one source of truth and it is append-only. "Which state is device X in" is a point query on `(campaign_id, device_id)` in a table sorted by exactly that.
- **The funnel is a materialized view over the event stream:** per campaign, per event type, `uniq(device_id)` — an HLL sketch, ±1 %, updated as batches land, ≤ 30 s behind. That is the live funnel, and the API says `exact: false`. After the sweep, one exact query (`uniqExact`, or `argMax` per pair then `count`) writes the final numbers to the campaign row, and the API says `exact: true`. **Two consumers, two guarantees, one table.** No counter key, no hash, no second store.

**Cost, volunteered:**

- **Inference is probabilistic**, and the threshold is a product decision that will be argued about. A house whose air conditioner was already off shows no drop and is classified as silent-non-compliant when it was compliant by accident. Say the threshold, say the false-negative direction (it undercounts compliance, so credits err against the customer), and say that `executed_silently` is reported separately from `executed` so the regulator can weight it.
- **Late acks after the sweep do not change the funnel.** `acked_late` is recorded and the report stands. Someone will ask why the dispute tool shows an ack and the funnel shows a timeout; the answer is the timestamp, and it is a good answer.
- **The live funnel is approximate.** ±1 % on a million is ten thousand devices, and an operator comparing stage-1 acks to stage-1 targets needs to know that. The `exact` flag is the honest signal; a UI that hides it will produce a support ticket.
- **The sweep is a burst:** ~500 k `unreachable` appends and up to a few hundred thousand telemetry point reads per campaign, once. Sized as a batch, not as a stream.

**→ ties to the funnel and fault-tolerance NFRs.**

---

## 11 · Deep dive — safety: the section most likely to be probed

### What you'd reach for first

"Operators are trained." A `cancelled` boolean on the campaign row. A confirmation dialog.

### What breaks

- **A boolean cancel races every delivery in flight** and is invisible to a device that already has the instruction (§4). It is the one safety control everyone draws and it does not work.
- **No cap means one typo sheds a gigawatt.** `kw: 2` on 10 M devices is 20 GW; a region's entire load. The system let it through because nothing in it knew what a large number was.
- **An abort threshold after 100 % is a post-mortem, not a control.** If the first time the system checks the reject rate is when every device has been told, the check is decoration.
- **A second campaign two minutes after the first, with the opposite sign**, because the frequency swung back — and now a million water heaters turn on at once. Oscillation is the failure mode grid operators fear most, and a system with no memory of what it just did cannot prevent it.

### What replaces it

**Seven mechanisms, each with a number, recited as a checklist. When "safety" is in the prompt, the interviewer will ask; have the list.**

1. **Max delta per campaign** — `expected_delta_mw ≤ max_delta_mw` (a product number; say 400 MW) computed at creation from the target count and per-device shed; `422` otherwise. The cap is a property of the program, not of the operator.
2. **Staged rollout with abort thresholds** — 1 % → 10 % → 100 %, a 5-minute hold after each; the stage worker advances only if the **reject rate < 2 %** and the **measured delta ≥ 50 % of expected** for the stage (read from the telemetry page's `/delta` for the stage's cohort). Below either: `abort`, automatically, and page a human. The 1 % stage is the canary and the 5 minutes is the time it takes the meter to show a delta.
3. **`CANCEL` as a new campaign with a higher id** — the same path, ≤ 10 s to connected devices, no approval gate, restores baseline. Not a flag.
4. **Dry run** — `dry_run: true` returns `targeted` and `expected_delta_mw` and publishes nothing. Required before any campaign above the approval threshold; cheap enough to require for all.
5. **Rate limit on campaign creation** — per operator and per program, say 10 per hour, so a scripted mistake cannot fan out faster than a human can notice.
6. **Two-person approval above a threshold** — 100 MW; the second approver must differ from the creator; the check runs inside the approval transaction, not at request admission. **Cancel is exempt** — a kill switch behind an approval is not a kill switch.
7. **Oscillation guard** — no campaign whose command has the opposite sign of a campaign on an overlapping target set within its **settle window** (15 minutes after `start_at + duration_s`). Evaluated at creation from the campaign table; `409 oscillation_guard` with the conflicting id and `settle_until`. A cancel restores baseline and is exempt.

Plus the two that are not controls but make the controls checkable: **every campaign, approval, abort, and cancel is an immutable row with actor and time**, and **the funnel snapshot is written to the campaign at close** — so the regulator's question "what did you send, who approved it, and what happened" is a `SELECT`.

**Cost, volunteered:**

- **Staging stretches the campaign.** Fifteen minutes to full fanout instead of thirty seconds. **Restate the NFR per stage** and say safety bought it: a demand response event is planned an hour ahead, and fifteen minutes is inside the plan. A campaign that genuinely needs 100 % in thirty seconds is a different product — emergency load shed — with a different approval model.
- **Abort thresholds need a measured delta, which needs the meter, which needs five minutes.** The hold time is the measurement latency; you cannot make it shorter than the telemetry page's rollup freshness plus the window.
- **The oscillation guard blocks legitimate corrections.** An operator who genuinely needs to reverse inside the window uses `cancel` (allowed) and then waits, or escalates to an override with a second approver — which is a ninth mechanism and worth naming as the escape hatch.
- **Approval turns a ten-second action into a two-person one.** Below the threshold it is not required; the threshold is where the product decides speed stops mattering more than a second pair of eyes.

**→ ties to the safety and cancel NFRs.**

---

## 12 · Data model, sharding, and storage decisions

**Two partition keys, one per side, and say why they differ.** The **send side** is keyed by `campaign_id`: the campaign row, its stages, its target snapshot, and its funnel are all read and written per campaign, and the stage worker's lease is a single row. The **receive side** — `device_events`, and the telemetry page's readings — is keyed by `device_id`: 300 k events a second from 10 M sources spread across 200 partitions, with per-device ordering so a device's `delivered` lands before its `acked`. Keying events by campaign would put an entire campaign's ack storm on one partition; keying campaigns by device makes no sense at all. **The two sides want different keys, and the boundary between them is the gateway.**

**The hot key is the in-flight campaign, and the design's response is to make it a partition in a columnar store rather than a key in a key-value one.** All 30–50 M events for campaign 9871 share a `campaign_id`; in ClickHouse that is a partition that gets scanned once at the sweep and summarised by a materialized view, which is what columnar stores are for. In Redis it would be one key on one shard, taking 300 k writes a second — the hottest-key question, answered by not building it.

**The campaign table is three megabytes and is treated as such.** One Postgres primary, no sharding, no read replicas for this table, one index on `deadline` for the scheduler and one on `(predicate_hash, start_at)` for the oscillation guard. If a question about scaling this table arrives, the answer is the number.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Campaigns, stages, approvals** | ~10 inserts/day; one lease per stage; read by id and by `deadline` | **System of record**, 7 years | **Postgres**, `FOR UPDATE SKIP LOCKED` on the stage row, monotonic `campaign_id` from a sequence | "It's three megabytes. A workflow engine — Temporal — is the right call at a hundred campaigns a minute; at ten a day a table and a lease *is* the scheduler, and I'm not adding a runtime to hold ten rows" |
| **Campaign target snapshot** | One bulk write of 10 M ids per campaign; read once at the sweep | Until 90 days after the deadline | **ClickHouse** `campaign_targets`, `ORDER BY (campaign_id, device_id)` | "Ten million rows in one insert, seconds. The same rows as ten million Postgres inserts would be the outbox I said I wasn't building" |
| **Device events** | 300 k/s peak append; point read by pair; set difference and `argMax` per campaign | Zero acknowledged loss; 90 days hot | **Kafka** `device_events` (key `device_id`, 200 partitions, RF 3, 7 d) → **ClickHouse** `ReplacingMergeTree`, `ORDER BY (campaign_id, device_id, event_ts)`, `PARTITION BY campaign_id` | "Cassandra ingests this fine — partition per campaign, cluster by device — and then the sweep is a set difference over ten million rows, which is a columnar query, not a partition read. The reads decide it, and every read here is per campaign across devices" |
| **Per-pair state** | "What state is device X in for campaign Y" | Derived | **Not stored.** `argMax(event, event_ts)` on the events table, a point query on the sort key | "A Redis hash per campaign is a ten-million-field key on one shard taking the ack storm. A state table is a second source of truth. The log is the state; I'd rather pay a point query than a reconciliation between two copies" |
| **Funnel** | Read every few seconds by operators during; exactly once after | Derived; final snapshot durable | **ClickHouse materialized view** — per `(campaign_id, event)`, `uniqState(device_id)`, ≤ 30 s behind; exact query at the sweep, **snapshot written to the campaign row in Postgres** | "A Redis counter per state would be three hundred thousand increments a second on one key. The view already exists because the log does, and thirty seconds is the requirement" |
| **Command notifications** | ~30 messages/day, 200 consumers | Replayable; Postgres is the truth | **Kafka** `commands`, 1 partition, 7 d — every gateway consumes from latest and loads the active list from Postgres at boot | "Redis Pub/Sub would carry this and drop it for any gateway mid-reconnect. The topic is a notification; the list of active campaigns lives in Postgres" |
| **Active campaign list** | Read on every `HELLO` and every stage message | Rebuilt from Postgres at boot | **In-process on each gateway**, a few dozen rows | "This is what makes store-and-forward a computation rather than a store" |
| **Ack timers** | ~50 k in flight per gateway at a stage peak | **None** — lost with the gateway; the sweeper is the backstop | **In-memory timer wheel** on the gateway | "The NFR needs an owner. The gateway that delivered is the owner, and losing a gateway means those pairs close at the deadline instead of at sixty seconds" |
| **Gateways** | 50 k sockets each; attribute cache per connection | None | **Stateless** service, 200 instances, L4 balancer, MQTT or WebSocket | "They hold a socket, fifty thousand attribute records, a few dozen campaigns, and a timer wheel. Any gateway serves any device" |
| **Device registry** (unicast only) | Written on connect; read per unicast command | **Ephemeral**, rebuilt from heartbeats | **Redis** KV `device_id → gateway_id`, 30 s heartbeat TTL | "Exists for the support engineer who needs to reach one device. The broadcast path never reads it — and it is a key-value map, not Pub/Sub" |
| **Per-device pending** (unicast only) | `LPUSH` on send, drained on `HELLO` | Until the command's deadline | **Redis** list per device, `EXPIRE` = deadline | "Same rule as the registry: the unicast path needs it, the broadcast path computes it from `last_seen_campaign_id`" |
| **Device dimension** | Read at creation (predicate count) and by gateways on refresh | Durable | **Postgres**, shared with the telemetry page; CDC to the gateways every 15 min | "Attributes at most fifteen minutes stale at the edge — that's the requirement, not a bug" |
| **On the device** | Read on every `CMD`; written before every `ACK` | **Flash** | `last_seen_campaign_id`, current setpoint, `restore_at` | "Persisted before the ack, or a reboot re-executes. This is a firmware rule and I'd own the spec" |
| **Telemetry readings** | 1 M/s | — | **The Smart-meter telemetry page.** This page reads `/delta` per cohort and per device | "One box, one API, its own design" |

### Data lifecycle — the append-only entities

| Entity | Growth | Hot | Warm | Cold | Restore |
|---|---|---|---|---|---|
| **Device events** | 30–50 GB/day | 90 days in ClickHouse — the regulatory reporting and customer-credit dispute window | — | **7 years** as Parquet in S3, one object per campaign; a regulated utility's retention | Minutes per campaign; a dispute older than 90 days is a stated support SLA, not a surprise |
| **Campaign targets** | ~1 GB/day | Until `deadline + 90 d`, then the partition is dropped | — | Recoverable from the campaign's predicate and the dimension's history if ever needed | n/a — the funnel snapshot on the campaign row is the durable summary |
| **Campaigns, approvals** | Tiny | 7 years, live | — | — | Never needed |
| **Kafka topics** | 30–50 GB/day | 7 days | — | — | Not an archive; day 8 is in ClickHouse or nowhere |

**The 90-day number is a product and regulatory decision, not a derivation.** If the regulator's window is 180 days, the TTL moves and nothing else does — say that, rather than presenting it as a storage constraint.

### The signals that tell you this is broken

Throughput is not the signal — 300 k events a second looks the same whether the devices are shedding load or ignoring you. The honest signals are **ratios per campaign and per stage**, and they are also the abort inputs:

- **The funnel as ratios:** `delivered / targeted`, `acked / delivered`, `executed / acked`, `measured / executed`. Each step that drops is a different failure: the first is connectivity, the second is firmware, the third is devices that agreed and did not do it, the fourth is the meter disagreeing with the device.
- **Delivery lag** — creation to `delivered`, p50 and p99, per stage. The p99 is the reconnect tail, and its shape is the connectivity story.
- **Gateway connection counts** — 200 lines that should sum to ~9 M. A drop on one is a gateway outage; a drop on all is a network event, and it is also a **coverage warning for every campaign in flight**.
- **`timed_out` rate by firmware version.** The single most useful breakdown: a firmware that acks and never reports shows up here first.
- **Sweeper backlog** — campaigns past `deadline + 60 s` with `exact: false`. Should be zero; anything else is a sweep that is failing, and the regulator's report is late.
- **Measured vs expected delta per stage** — the abort input, graphed. If it is flat at 100 % the meter is not being read.
- **Cancel latency** — creation of a `CANCEL` to `acked` p99. Tested monthly with a dry campaign, because the day you need it is not the day to find out.

---

## 13 · Traps — the ranked list

**Design traps**

1. **An outbox and CDC when idempotency lives on the device.** Four boxes and a hundred million rows a day protecting a guarantee the device already provides with one integer (§7).
2. **A registry lookup per device for a broadcast command.** Ten million reads of the hottest key on the board, for one predicate the gateways can evaluate themselves — and the question "does this key need to exist?" never asked (§8).
3. **An NFR that contradicts the drawing.** "p99 100 ms creation-to-fanout" beside a ten-million-device fanout. Audit the NFRs against the boxes at minute 35 and rewrite it as three numbers with three enforcers (§2).
4. **`last_seen_campaign_id` in RAM.** A reboot re-executes the campaign the device just finished. The rule is only a rule if it survives a power cut (§4, §7).
5. **Cancel as a mutation of the campaign.** It races every delivery in flight and is invisible to a device that already has the instruction. A cancel is a newer campaign (§4, §11).
6. **Redis Pub/Sub conflated with a Redis registry.** One is a fire-and-forget transport that drops for a reconnecting subscriber; the other is a TTL'd map for unicast routing. Neither is what makes broadcast work (§8).
7. **Retries as a resend loop against a socket.** The device that did not answer is offline; the retry that matters is the reconnect hook, and it needs no per-device store (§9).
8. **A 60 s timeout with no owner.** Stated in the requirements, enforced nowhere. The gateway that delivered holds the timer; the sweeper is the backstop (§9).
9. **Per-pair state in a mutable table** — Postgres, Cassandra, or a Redis hash. A second source of truth next to the log, and in Redis the hottest key on the page (§10, §12).
10. **A per-device pending queue for broadcast commands.** Ten million lists to keep consistent with the campaign table, for a question `HELLO` answers with one integer (§9).
11. **No oscillation guard.** The opposite command two minutes later, because nothing remembered the first one (§11).
12. **Staged rollout without abort thresholds** — or with thresholds that are checked after 100 % (§11).
13. **Reconciliation as a box with no definition.** "Late" and "missing" each need a state, a rule, and a moment (§10).
14. **Replay order ignored for a device that missed two campaigns.** Highest-wins is right; ascending order is also right and records more. Arrival order is wrong (§6 Flow D).
15. **`timed_out` rewritten to `acked` when a late ack arrives.** The funnel changes after the report was filed. Terminal states are terminal; late facts are new events (§6 Flow C).

**Performance traps**

16. **`device_events` keyed by campaign.** One partition takes the whole ack storm (§12).
17. **A single counter key per funnel state.** Three hundred thousand increments a second on one Redis shard (§3, §10).
18. **The sweeper as a per-minute scan of every in-flight pair** instead of one set difference at the deadline (§9, §10).
19. **Row-at-a-time inserts into the event store** during the ack storm. Batch by partition; the Kafka sink already does (§12).
20. **A 10 M-row target list written as 10 M rows to Postgres.** It is one columnar insert (§12).

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

21. **Twelve minutes on a three-megabyte table.** The campaign path has no load; the fanout and the telemetry have all of it. Say the budget — *"three minutes"* — before drawing the first box, and spend the rest where the numbers are (§3).

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 450" role="img" aria-label="Demand response five-minute skeleton. The per-target state machine across the top; then Postgres campaigns, the single publish to two hundred gateways, and the gateway with its timer; then the device with its persisted id, the HELLO reconnect hook, and the event log in ClickHouse; then the deadline sweeper and the safety strip; and a margin lane with the funnel ratios, delivery lag, connection counts, and the honest NFR.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="44" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="94.5">pending → delivered → acked | rejected → executed → measured    ·    terminals: timed_out · unreachable · executed_silently · cancelled</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="30" y="132" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="156.5">Campaigns — Postgres</text>
  <text class="dg-s dg-c" x="180" y="172.5">immutable · monotonic id · 3 MB — three minutes</text>
  <circle class="dg-num" cx="30" cy="132" r="9"></circle>
  <text class="dg-num-t" x="30" y="135.4">2</text>
  <rect class="dg-box" x="350" y="132" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="156.5">Kafka commands → 200 gateways</text>
  <text class="dg-s dg-c" x="500" y="172.5">200 messages, not 10 M lookups</text>
  <circle class="dg-num" cx="350" cy="132" r="9"></circle>
  <text class="dg-num-t" x="350" y="135.4">3</text>
  <rect class="dg-box" x="670" y="132" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="156.5">Gateway</text>
  <text class="dg-s dg-c" x="815" y="172.5">50 k sockets · attrs at HELLO · 60 s timer</text>
  <circle class="dg-num" cx="670" cy="132" r="9"></circle>
  <text class="dg-num-t" x="670" y="135.4">4</text>
  <rect class="dg-box" x="30" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="232.5">Device</text>
  <text class="dg-s dg-c" x="180" y="248.5">flash last_seen_campaign_id → no outbox</text>
  <circle class="dg-num" cx="30" cy="208" r="9"></circle>
  <text class="dg-num-t" x="30" y="211.4">5</text>
  <rect class="dg-box" x="350" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="232.5">HELLO {attrs, last_seen}</text>
  <text class="dg-s dg-c" x="500" y="248.5">retries are a reconnect hook · deadline = TTL</text>
  <circle class="dg-num" cx="350" cy="208" r="9"></circle>
  <text class="dg-num-t" x="350" y="211.4">6</text>
  <rect class="dg-box" x="670" y="208" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="232.5">device_events → ClickHouse</text>
  <text class="dg-s dg-c" x="815" y="248.5">keyed device, partitioned campaign · funnel = MV</text>
  <circle class="dg-num" cx="670" cy="208" r="9"></circle>
  <text class="dg-num-t" x="670" y="211.4">7</text>
  <rect class="dg-box" x="30" y="284" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="308.5">Deadline sweeper, once</text>
  <text class="dg-s dg-c" x="260" y="324.5">targets − reported → unreachable · timed_out → meter → executed_silently</text>
  <circle class="dg-num" cx="30" cy="284" r="9"></circle>
  <text class="dg-num-t" x="30" y="287.4">8</text>
  <rect class="dg-good" x="510" y="284" width="450" height="56" rx="8"></rect>
  <text class="dg-good-t dg-c" x="735" y="308.5">Safety strip</text>
  <text class="dg-s dg-c" x="735" y="324.5">max Δ · staged+abort · cancel=new id · dry run · rate limit · 2-person · settle</text>
  <circle class="dg-num" cx="510" cy="284" r="9"></circle>
  <text class="dg-num-t" x="510" y="287.4">9</text>
  <text class="dg-lane" x="30" y="370">IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="400.5">funnel as ratios</text>
  <text class="dg-s dg-c" x="140" y="416.5">delivered/targeted · acked/delivered …</text>
  <circle class="dg-num" cx="30" cy="382" r="9"></circle>
  <text class="dg-num-t" x="30" y="385.4">10</text>
  <rect class="dg-box" x="270" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="380" y="400.5">delivery lag p99</text>
  <text class="dg-s dg-c" x="380" y="416.5">the reconnect tail</text>
  <rect class="dg-box" x="510" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="400.5">gateway connection counts</text>
  <text class="dg-s dg-c" x="620" y="416.5">a drop is a coverage warning</text>
  <rect class="dg-box" x="750" y="382" width="210" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="855" y="400.5">the honest NFR</text>
  <text class="dg-s dg-c" x="855" y="416.5">&lt; 1 s · ≤ 30 s · 60 s</text>
</svg>
</div>

<p class="diagram-cap">Badge 1 goes on the board before any box, and every box after it has to point at a transition on it. Badge 2 gets three minutes. Badge 9 is the strip that went to zero in the reviewed mock — seven items, recited, each with a number.</p>

1. **The state machine, top centre, before any box:** `pending → delivered → acked | rejected → executed → measured`, terminals `timed_out · unreachable · executed_silently · cancelled`. Write beside it: *"every box must own a transition."*
2. **Campaigns — Postgres.** Immutable, monotonic id, three stages with a lease, `deadline` indexed. Label it **"3 MB — three minutes, not twelve."**
3. **Publish once → Kafka `commands` → 200 gateways evaluate the predicate locally.** Label the arrow **"200 messages, not 10 M lookups."**
4. **Gateway:** 50 k sockets, attribute cache from `HELLO`, the active campaign list, **a 60 s timer per delivery**. It owns `delivered` and `timed_out`.
5. **Device:** persists `last_seen_campaign_id` in flash, applies only higher ids, respects `deadline`. Label it **"idempotency lives here — so no outbox."**
6. **`HELLO {attrs, last_seen}` → the gateway computes what the device missed.** Label it **"retries are a reconnect hook; the deadline is the TTL."**
7. **`device_events` → Kafka keyed by device → ClickHouse partitioned by campaign.** The only per-pair state, and it is a log. The funnel is a materialized view over it.
8. **Deadline sweeper:** targets minus reported → `unreachable`; delivered with no successor → `timed_out`; then **an arrow from the telemetry box** → `executed_silently`. One run per campaign.
9. **The safety strip**, seven items in a row: max delta · staged with abort thresholds · cancel as a higher id · dry run · creation rate limit · two-person approval · oscillation guard.
10. **In the margin:** the funnel as ratios, delivery lag p99, gateway connection counts, sweeper backlog — and the honest NFR: *"first device < 1 s, a stage ≤ 30 s, per-device timeout 60 s after delivery."*

---

## 15 · Variants — what actually changes

**The governing axis: how much closure each target owes — delivered, acknowledged, executed, or executed-and-verified by a side channel — and whether the effect is reversible.** Every row has an operator action, a fanout, a per-target state machine, and a reconciliation at a deadline. What changes is how many states the machine has, whether cancel means anything, and how much of §9–§11 survives.

| Product | Closure owed per target | Reversible? | The delta from this page |
|---|---|---|---|
| **Bulk notification send** (push, email, SMS to millions) | **Delivered.** Nobody executes anything | Not applicable | The state machine collapses to `pending → delivered` or `failed`, and `unreachable` is the whole reconciliation. §9's timer and §10's inference vanish; §8 survives entirely (broadcast by segment, evaluated at the edge or by a fanout worker); the deadline is still the TTL — a "flash sale ends at noon" push at 12:05 is the same bug as a shed command after the window. Safety shrinks to a rate limit and a send cap |
| **Feature-flag rollout** (LaunchDarkly, Statsig) | **Applied**, but the target *pulls* | Yes — flip it back | The IDE settings sync page. The push becomes a hint and the truth becomes a version; per-target state collapses to "which config version does this client have," reported on heartbeat. **§7's ordering rule survives verbatim** — a client must never apply an older config after a newer one — and staged rollout by `hash(id) % 100` is the same mechanism. No deadline, because there is nothing time-bound to actuate |
| **Configuration push** to devices or agents | **Acknowledged and applied**, not measured | Yes — push the previous config, as a newer version | This page minus §10's inference: there is no meter, so `executed_silently` does not exist and `timed_out` is terminal. Store-and-forward via `HELLO`, the deadline (usually "until superseded"), the gateway timer, and the sweeper all stay. Safety keeps staging and the kill switch, drops the oscillation guard |
| **OTA firmware rollout** | **Executed and self-verified** — the device reboots into the new image and reports | **Partially** — a rollback is another rollout, and a bricked device is unreachable forever | Add a `verifying` state between `executed` and a new terminal `healthy`, with the device's post-reboot heartbeat as the transition, and add `bricked` as the terminal nobody wants. **§11 dominates the page**: the 1 % canary stage holds for hours, the abort threshold is "any device that fails to come back," and two-person approval is universal. The bandwidth is on the device-side download, which becomes its own §7 (chunked, resumable, content-addressed) |
| **Payment retry orchestration** (dunning) | **Executed by a third party**, and the answer arrives by webhook | **No** — a successful charge is money moved | The "device" is a PSP behind an API you do not control (the payment-processor page); `HELLO` becomes a webhook; store-and-forward becomes a retry ladder driven by decline codes; and **§7's question is identical** — the idempotency key is derived from `(invoice, attempt)` and lives at the PSP, which is what makes retries safe. Safety becomes "never retry a `card_stolen`," and the oscillation guard becomes "no charge and refund inside the same settlement window" |
| **Grid demand response** — this page | **Executed and measured** through a side channel | Yes — a restore is a newer command | As written. The meter is what makes `executed_silently` possible and what makes the abort threshold a measurement instead of an assumption. The oscillation guard exists because the effect is physical and the physics has a settle time |

**The lesson:** the fanout is the same in every row and it is never the hard part. **What the state machine looks like is decided by how much each target owes you at the end** — and drawing that machine first is what tells you which of the boxes on this page each cousin gets to keep.
