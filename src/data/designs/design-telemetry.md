# Design Smart-Meter Telemetry — Write-Heavy Ingest at a Million Readings a Second

## The question

> *"Design the telemetry pipeline for ten million smart meters. Each one reports its power draw every ten seconds over a connection that comes and goes. Operators want live load per feeder and per region within about thirty seconds, planners want years of history, and after we send a fleet-wide command we need to know how much load actually dropped — across exactly the meters we sent it to."*

**The product.** A utility has a meter on every home it serves. Each meter measures how much power is flowing right now and sends that number, with a timestamp, every ten seconds. The connection is a cellular or mesh radio that drops in basements, in storms, and whenever a tower is busy, so a meter that has been quiet for an hour comes back and sends the whole hour at once. Operators watch a map of the grid coloured by load. Planners look back over years to decide where to build. And when the grid is short of power, the operator asks a million homes to trim their air conditioning for half an hour — and then has to tell the regulator how many megawatts actually came off.

**What a working system delivers**

- A feeder's live load on the operator's map within thirty seconds of it changing.
- A meter that was offline overnight and reports its backlog at 7 a.m. does not make the 7 a.m. graph spike, and does not silently rewrite last night's totals either.
- Minutes after a command goes out to a million homes, a number: *expected 400 MW off, measured 370 MW, from 96 % of the meters we targeted.*
- Ten years of history at a resolution that fits on disk, and last month at full resolution.
- Losing a few readings out of a million a second is fine. Not knowing how many you lost is not.

**Why this gets asked.** It sounds like "put it on Kafka, aggregate it, store it in a time-series database," and every candidate says those words. What separates answers is the arithmetic between the words — how many partitions, how big a batch, how much state a window holds — and one number almost nobody volunteers: how late a reading may be and still count.

---

**Archetype:** write-heavy telemetry / analytics — N sources × f Hz of small, lossy, event-timed readings that have to become windowed aggregates within seconds and stay queryable for years.
**Cousins that reuse ~70% of this page:** fleet GPS and vehicle telematics, industrial IoT sensors, app analytics events, metrics pipelines (Prometheus remote-write, Datadog agents), ad impression counting, CDN log analytics. Also **any product where the question is "what happened to a cohort in a window," never "what happened to row X."**

**What's actually being graded:** whether the **partition and batching arithmetic** is said with numbers rather than gestured at; whether you separate **event time from arrival time** and then *pick* an allowed-lateness number and say what it costs in state; whether the time-series store is **named, with a retention and a downsampling policy**, rather than left as "a TSDB"; and whether loss is treated as a **counted policy** — a pipeline that is allowed to drop readings and required to say how many.

**Contrast to have ready:** *LLM API billing is the same firehose — small events, at-least-once, arriving late and twice — with the opposite requirement: every one of them is money, so that page buys an outbox, a dedupe window, and a ledger. Here a dropped reading is a metric. **The design gets cheaper everywhere that fact is applied, and no cheaper anywhere it is forgotten** — an outbox on a meter is the tell that the candidate has not asked what a lost reading costs.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "This is a write-heavy telemetry pipeline: ten million sources at one reading every ten seconds is **a million writes a second**, each about a hundred bytes, and the readings are **allowed to be lossy** — nobody is billed off a single sample. Three things dominate. First, the ingest arithmetic: a million a second is roughly two hundred Kafka partitions and it only works if the gateways **batch**, so I'll say the partition count and the batch size out loud. Second, **event time is not arrival time** — a meter that was in a basement for an hour sends the hour in one burst, and if I window on arrival the 7 a.m. graph lies. So I'll window on event time with a watermark, and I'll **pick an allowed-lateness number** and say what it costs in state, because 'it's a trade-off' is not a design. Third, the store: a million inserts a second is not a Postgres problem and 'all devices in a five-minute window' is not a Cassandra read, so it's a columnar time-series store with **retention and downsampling stated**. I'll scope to ingest, live rollups, and the before/after measurement of a command's effect, and I'll leave the command dispatch itself out — that's its own system. I'll go deep on the windowing and lateness decision, and on the storage tiering."

**Why open this way:** it converts "put it on Kafka" into three numbers before the interviewer can ask for them, it refuses the vague version of lateness in the first minute, and it pre-commits the two dives (§8, §10) where reasonable engineers actually disagree. It also names the one thing the prompt is really about — measuring a command's effect (§9) — so the pipeline is built toward a query rather than toward a dashboard.

---

## 1 · Functional requirements

1. **Ingest readings from 10 M meters at one every 10 s**, over connections that drop and reconnect, accepting a backlog burst from a meter that was offline — without the burst being mistaken for current load.
2. **Serve per-cohort aggregates** (feeder, region, and any command's target set) at one-minute granularity **within 30 s of event time**, and answer *"what was this cohort's load in the five minutes before and after T"* with a **coverage figure** — the fraction of the cohort that actually reported.
3. **Keep the data**: full resolution for a bounded recent window, downsampled series for years, with a stated read latency for each tier.

**Out of scope (say them):** dispatching the command itself and the per-device command state machine (the Demand response page), meter provisioning and identity, load forecasting, billing off these readings (a separate, exact pipeline — the billing page), the operator UI.

**Below the line, likely follow-ups:** per-device anomaly and outage detection (a gap in `seq` is an outage signal), meter clock drift and firmware, multi-region ingest, ad-hoc analytics over years of raw data (§15), tamper detection.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Sustained ingest** | **1 M readings/s**, with a **3× burst** for ten minutes | 10 M × 1/10 s is the steady state. The burst is a regional outage ending: a million meters reconnect inside a few minutes and each has an hour of backlog (§3). Sizing for 1 M/s and no burst is sizing for the day nothing goes wrong |
| **Acceptable loss** | **≤ 0.1 % of readings, and every dropped reading is counted** | A feeder's load is a sum over thousands of meters, so a missing sample moves the answer by a rounding error. For contrast, the billing page's target is 10⁻⁶ with reconciliation — that gap is the whole difference between the two pages. **The counter is the requirement; the 0.1 % is a budget** |
| **Rollup freshness** | A one-minute window is **queryable ≤ 30 s after it closes in event time** | Operators react to load in minutes; 30 s is invisible on the map. Achieved as watermark lag 20 s + emit; **this is the number that bounds allowed lateness** (§8) |
| **Allowed lateness** | **30 s** past the watermark. Later readings are **stored, counted, and excluded from the live rollup** | The trade is state (§3) against completeness. 30 s covers cellular jitter and a gateway restart; it does not cover a basement, and it isn't meant to — backfill is its own path (§11) |
| **Cohort query latency** | p99 **< 1 s** for a feeder or region; p99 **< 5 s** for a command's target set of up to 10 M meters | The operator map polls the first; the second is a report someone waits for once per command |
| **Retention** | Raw **30 days**; per-meter hourly **2 years**; per-cohort minute rollups **10 years** | Thirty days covers a billing dispute's evidence window and every "what happened Tuesday" question at full resolution. Beyond that, nobody asks about a single meter at ten-second resolution, and the storage math (§3) says nobody should |
| **Durability of an accepted reading** | Once the gateway has acknowledged the batch: **replicated three ways, replayable for 7 days** | The meter deletes its buffer on ack. Kafka RF 3 with acks=all is what makes the ack honest. Before the ack, the meter's own buffer is the durability |
| **Fault tolerance** | Survives: any gateway (meters reconnect elsewhere), any broker (RF 3), a stream-processor restart (checkpoint ≤ 60 s old, replayed). **Does not survive: the analytics store being down longer than Kafka retention** — after 7 days the readings are gone, and the policy is a page to on-call at 24 h and sampling at 5 days | Naming the one that kills you is worth more than the list it survives. Seven days of buffer is generous and finite |
| **Backpressure** | Under overload, gateways **sample** (keep every *k*-th reading per meter) rather than disconnect, and the shed count is a metric | Disconnecting a meter costs a reconnect storm later; a sampled feeder is still a correct feeder within the loss budget |
| **Scale** | 10 M meters, 200 gateways, ~8.6 TB/day raw | §3 |

**The sentence that earns the point:** *"The pipeline is allowed to lose readings and is not allowed to lie about how many it lost. Every mechanism on this page is cheaper than the billing page's because of the first half of that sentence, and every counter on it exists because of the second."*

---

## 3 · Numbers that reframe the problem

**A million a second is ~200 partitions, and only if the gateways batch**

- *Assumption:* ~100 B per reading (device id, two timestamps, a sequence number, two floats).
- **1 M/s × 100 B = 100 MB/s** in, ×3 for replication = **300 MB/s of broker disk** — about 15–20 brokers, which is a cluster, not a problem.
- A Kafka partition comfortably takes **5–10 k msg/s**, so **100–200 partitions**. Pick **200**, keyed by `device_id`.
- The trap is requests, not bytes: **each gateway (§3, next) produces 5 k msg/s spread across 200 partitions**, so without batching that is a million tiny produce requests a second across the cluster. With `linger.ms = 200` and 64 KB batches it is ~4 k requests/s per broker. **Batching is what makes the partition count true**, and it costs ~200 ms of latency nobody will notice against a 30 s freshness target.

**200 gateways, 5 k messages a second each**

- 10 M meters at **50 k connections per gateway** = **200 gateways**. Not 40 — the arithmetic is worth doing on the board because the number sets the batching math above and the fanout math on the Demand response page.
- Each gateway sees 5 k readings/s: trivial for the socket layer, which is why gateways are stateless and the interesting work is downstream.

**Raw is 8.6 TB a day, which is why retention is a decision and not a default**

- 100 MB/s × 86,400 s = **8.6 TB/day uncompressed**; columnar compression on timestamps and slowly-varying floats gets ~10×, so **~1 TB/day on disk, ~30 TB for the 30-day hot window**.
- Ten years of raw would be **3 PB** compressed. Nobody queries a single meter at ten-second resolution from 2019. **This number is what licenses downsampling** (§10): per-meter hourly is 10 M × 24 = 240 M rows/day (~5 GB/day), and per-cohort minute rollups are ~14 M rows/day — a rounding error.

**Window state is 10 M keys, and lateness multiplies it**

- One-minute windows keyed by meter: 10 M keys × ~50 B of partial aggregate (count, sum, min, max) = **~500 MB per open window**.
- With allowed lateness of **30 s**, about 1.5 windows are open at once → **~1 GB of state**. At **10 minutes** of lateness, eleven windows → **~5.5 GB**, checkpointed every minute. **This is the number that picks the lateness figure** — it is linear, and saying "it's a trade-off" without it is the answer this page exists to replace.
- Cohort windows (feeders, regions, campaigns) are a few hundred thousand keys and don't register.

**A regional outage ending is 360 M late readings**

- *Assumption:* a tower outage takes **1 M meters** offline for **1 hour**. When it ends, each has 360 buffered readings: **360 M readings arrive over a few minutes, every one of them an hour late**.
- That is a **3× ingest burst** (§2) *and* it is entirely outside any sane lateness window. So the design needs a backfill path that is not the live path (§11), and the meters need to send **backlog after live** so the map recovers first.

**The command-effect query is two reads, not a scan — if membership is applied at rollup time**

- A command targets up to **10 M meters**. Answering "before vs after" by scanning raw is 10 M meters × 30 readings × 2 windows = **600 M rows per question**.
- If the stream processor tags each reading with the **active campaigns its meter belongs to** (a broadcast set of ~10 M ids, ~80 MB, changes ten times a day), the campaign becomes a cohort and the answer is **two rollup rows plus a distinct-meter count**. §9 is built on this number.

---

## 4 · Core entities

- **Reading** — `(device_id, event_ts, ingest_ts, seq, kw, volts)`. Immutable. `event_ts` is the meter's clock; `ingest_ts` is the gateway's. **Both are stored, always** — lateness is their difference, and it is the most-graphed number on the page.
- **Device** — the dimension: `device_id, feeder_id, region_id, install_ts, firmware`, plus the attributes a command predicate reads. Changes rarely; joined at rollup time, not stored per reading.
- **Cohort** — a named set of meters: a feeder, a region, or **a campaign's target set** (a snapshot, written once when the campaign is created). The rollup key.
- **Rollup** — `(cohort_id, granularity, window_start) → (count, sum_kw, min_kw, max_kw, distinct_devices)`. Derived, recomputable, upserted by key.
- **Watermark** — per Kafka partition, `max(event_ts) − 20 s`. Not stored; it is the processor's clock.
- **Late reading** — a Reading whose `event_ts` fell behind the watermark by more than the allowed lateness. Same row, one flag, a different path.

**The three that are load-bearing:**

**`seq` is per meter, monotonic, and persisted on the meter.** It is what makes at-least-once delivery harmless (dedupe on `(device_id, seq)` inside the replay window) and what turns a *gap* into an outage signal. Without it, a duplicated batch after a gateway restart double-counts a feeder for a minute and nobody can prove it.

**Cohort membership is an input to the rollup, not a column on the reading.** A meter's feeder can change; a campaign's target set is defined the moment the campaign is created. Tagging at rollup time from a broadcast dimension means a membership change re-rolls forward from now, and a campaign's cohort exists the instant it is created. Tagging at ingest bakes the dimension into 8.6 TB a day of immutable rows.

**The rollup is upserted by `(cohort_id, granularity, window_start)`, and that key is the whole exactly-once story.** Replaying a checkpoint re-emits the same windows with the same keys, and an upsert of an identical value is a no-op. No transaction, no dedupe table on the write side, no outbox — **idempotency lives in the key of the derived row**, and that is the entire mechanism.

---

## 5 · API

```text
MQTT  PUBLISH meters/{device_id}                       QoS 1, batched by the meter
      { readings: [ {event_ts, seq, kw, volts}, … ] }   ← live first, then backlog
      → PUBACK once the gateway's Kafka batch is acknowledged (acks=all)

Kafka readings          key = device_id, 200 partitions, RF 3, 7-day retention
      value { device_id, event_ts, ingest_ts, seq, kw, volts }
Kafka readings.late     same shape + { late_by_s }     ← the side output (§8)

GET  /v1/rollups?cohort=feeder:1234&granularity=1m&from=…&to=…
     → 200 { rows: [ {window_start, count, sum_kw, avg_kw, distinct_devices} ], freshness_s }

GET  /v1/delta?cohort=campaign:987&t=…&window=5m
     → 200 { before_kw, after_kw, delta_kw,
             coverage: { targeted: 1_000_000, reported_both_windows: 962_114, ratio: 0.962 },
             late_excluded: 4_811 }

GET  /v1/device/{id}/readings?from=…&to=…                p99 < 200 ms inside 30 days; slower after
```

**Decisions to narrate, unprompted:**

- **The meter batches, and it sends live before backlog.** One PUBLISH per ten seconds is fine; a meter returning from an hour offline sends its *current* reading first, then drains the buffer oldest-first. The map recovers in one message; the history fills in behind it. This is a firmware decision the pipeline depends on, and it is worth saying that you'd own that spec.
- **QoS 1 and PUBACK only after Kafka acknowledges.** The meter deletes its buffer on ack, so the ack has to mean "replicated," not "received." At-least-once falls out — a lost PUBACK means a resend — and `(device_id, seq)` makes the duplicate a no-op.
- **`coverage` is on every delta response.** A delta from 60 % of the cohort is a different fact from one at 96 %, and the number that says which is not optional. **This is the field the Demand response page reads to decide which silent meters actually executed.**
- **`late_excluded` is on it too.** The live rollup omitted these; the backfilled one (§11) will include them; the caller can tell the two apart.
- **Two topics, not a flag.** Late readings go to their own topic so the backfill consumer can be slow, batchy, and restartable without touching the live path's lag.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 630" role="img" aria-label="Smart-meter telemetry architecture. Device edge: ten million meters with a flash buffer, and two hundred stateless MQTT gateways that batch into Kafka and sample backlog under pressure. Bus: a readings topic keyed by device id with two hundred partitions. Stream: Flink with event-time windows, a watermark, allowed lateness and dedupe, fed by a broadcast cohort dimension from Postgres, checkpointing to S3. A late-readings topic with its own backfill consumer. Store: ClickHouse raw, a per-meter hourly materialized view and cohort rollups, behind a query API that reports coverage on every delta.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Loss is a metric, not revenue: no outbox anywhere, and every dropped reading is counted.</text>
  <rect class="dg-group" x="20" y="86" width="230" height="220" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">DEVICE EDGE</text>
  <rect class="dg-box" x="36" y="118" width="198" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="135" y="138.5">10 M meters</text>
  <text class="dg-s dg-c" x="135" y="154.5">1 reading / 10 s · ~100 B</text>
  <text class="dg-s dg-c" x="135" y="170.5">flash buffer · live first</text>
  <rect class="dg-box" x="36" y="200" width="198" height="96" rx="8"></rect>
  <text class="dg-t dg-c" x="135" y="228.5">MQTT gateways ×200</text>
  <text class="dg-s dg-c" x="135" y="244.5">50 k sockets each · stateless</text>
  <text class="dg-s dg-c" x="135" y="260.5">batch: linger 200 ms · zstd</text>
  <text class="dg-s dg-c" x="135" y="276.5">sample backlog, count it</text>
  <path class="dg-line" d="M 135,182 L 135,192"></path>
  <path class="dg-head" d="M 130,192 L 140,192 L 135,200 Z"></path>
  <rect class="dg-group" x="270" y="86" width="240" height="220" rx="12"></rect>
  <text class="dg-group-t" x="286" y="108">BUS</text>
  <rect class="dg-box" x="286" y="118" width="208" height="72" rx="8"></rect>
  <path class="dg-qbar" d="M 299,127 L 299,181"></path>
  <path class="dg-qbar" d="M 308,127 L 308,181"></path>
  <path class="dg-qbar" d="M 317,127 L 317,181"></path>
  <text class="dg-t dg-c" x="408" y="142.5">Kafka readings</text>
  <text class="dg-s dg-c" x="408" y="158.5">device_id · 200 partitions</text>
  <text class="dg-s dg-c" x="408" y="174.5">RF 3 · acks=all · 7 days</text>
  <path class="dg-line" d="M 234,248 L 258,248 L 258,154 L 278,154"></path>
  <path class="dg-head" d="M 278,159 L 278,149 L 286,154 Z"></path>
  <text class="dg-lbl dg-c" x="258" y="140">1 M/s</text>
  <text class="dg-s" x="296" y="230">PUBACK to the meter only</text>
  <text class="dg-s" x="296" y="246">after acks=all — the meter</text>
  <text class="dg-s" x="296" y="262">deletes its buffer on ack</text>
  <rect class="dg-group" x="540" y="86" width="440" height="220" rx="12"></rect>
  <text class="dg-group-t" x="556" y="108">STREAM</text>
  <rect class="dg-box" x="556" y="118" width="200" height="96" rx="8"></rect>
  <text class="dg-t dg-c" x="656" y="146.5">Flink — event time</text>
  <text class="dg-s dg-c" x="656" y="162.5">1-min windows · watermark −20 s</text>
  <text class="dg-s dg-c" x="656" y="178.5">allowed lateness 30 s</text>
  <text class="dg-s dg-c" x="656" y="194.5">dedupe (device_id, seq)</text>
  <path class="dg-line" d="M 494,154 L 548,154"></path>
  <path class="dg-head" d="M 548,159 L 548,149 L 556,154 Z"></path>
  <text class="dg-lbl dg-c" x="525" y="146">200 tasks</text>
  <rect class="dg-box" x="776" y="118" width="188" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="870" y="138.5">Broadcast cohorts</text>
  <text class="dg-s dg-c" x="870" y="154.5">feeder · region · campaigns</text>
  <text class="dg-s dg-c" x="870" y="170.5">300 MB / task</text>
  <path class="dg-line" d="M 776,150 L 764,150"></path>
  <path class="dg-head" d="M 764,145 L 764,155 L 756,150 Z"></path>
  <path class="dg-box" d="M 776,213 L 776,243 A 94,7 0 0 0 964,243 L 964,213 A 94,7 0 0 0 776,213 Z"></path>
  <path class="dg-box" d="M 776,213 A 94,7 0 0 0 964,213" style="fill:none"></path>
  <text class="dg-t dg-c" x="870" y="236">Postgres device dim</text>
  <path class="dg-line" d="M 870,206 L 870,190"></path>
  <path class="dg-head" d="M 875,190 L 865,190 L 870,182 Z"></path>
  <text class="dg-lbl" x="880" y="200">CDC, hourly</text>
  <path class="dg-box" d="M 776,269 L 776,295 A 94,7 0 0 0 964,295 L 964,269 A 94,7 0 0 0 776,269 Z"></path>
  <path class="dg-box" d="M 776,269 A 94,7 0 0 0 964,269" style="fill:none"></path>
  <text class="dg-t dg-c" x="870" y="290">S3 checkpoints</text>
  <path class="dg-line" d="M 700,214 L 700,282 L 768,282"></path>
  <path class="dg-head" d="M 768,287 L 768,277 L 776,282 Z"></path>
  <text class="dg-lbl" x="706" y="276">every 60 s</text>
  <path class="dg-line" d="M 556,190 L 530,190 L 530,330 L 136,330 L 136,384"></path>
  <path class="dg-head" d="M 131,384 L 141,384 L 136,392 Z"></path>
  <text class="dg-lbl" x="300" y="324">beyond lateness → side output, counted</text>
  <rect class="dg-box" x="36" y="392" width="200" height="60" rx="8"></rect>
  <path class="dg-qbar" d="M 49,401 L 49,443"></path>
  <path class="dg-qbar" d="M 58,401 L 58,443"></path>
  <path class="dg-qbar" d="M 67,401 L 67,443"></path>
  <text class="dg-t dg-c" x="154" y="418.5">Kafka readings.late</text>
  <text class="dg-s dg-c" x="154" y="434.5">side output · 24 h</text>
  <rect class="dg-box" x="266" y="392" width="170" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="351" y="418.5">Backfill consumer</text>
  <text class="dg-s dg-c" x="351" y="434.5">hourly · backfilled=1</text>
  <path class="dg-line" d="M 236,422 L 258,422"></path>
  <path class="dg-head" d="M 258,427 L 258,417 L 266,422 Z"></path>
  <path class="dg-line" d="M 436,422 L 472,422"></path>
  <path class="dg-head" d="M 472,427 L 472,417 L 480,422 Z"></path>
  <text class="dg-lbl dg-c" x="458" y="440">is_late</text>
  <rect class="dg-group" x="464" y="360" width="516" height="120" rx="12"></rect>
  <text class="dg-group-t" x="480" y="382">STORE — ClickHouse</text>
  <path class="dg-box" d="M 480,399 L 480,457 A 75,7 0 0 0 630,457 L 630,399 A 75,7 0 0 0 480,399 Z"></path>
  <path class="dg-box" d="M 480,399 A 75,7 0 0 0 630,399" style="fill:none"></path>
  <text class="dg-t dg-c" x="555" y="420">raw</text>
  <text class="dg-s dg-c" x="555" y="436">ORDER BY (device_id, ts)</text>
  <text class="dg-s dg-c" x="555" y="452">TTL 30 d</text>
  <path class="dg-box" d="M 652,399 L 652,457 A 73,7 0 0 0 798,457 L 798,399 A 73,7 0 0 0 652,399 Z"></path>
  <path class="dg-box" d="M 652,399 A 73,7 0 0 0 798,399" style="fill:none"></path>
  <text class="dg-t dg-c" x="725" y="420">per-meter hourly</text>
  <text class="dg-s dg-c" x="725" y="436">materialized view</text>
  <text class="dg-s dg-c" x="725" y="452">2 y</text>
  <path class="dg-box" d="M 818,399 L 818,457 A 75,7 0 0 0 968,457 L 968,399 A 75,7 0 0 0 818,399 Z"></path>
  <path class="dg-box" d="M 818,399 A 75,7 0 0 0 968,399" style="fill:none"></path>
  <text class="dg-t dg-c" x="893" y="420">cohort rollups</text>
  <text class="dg-s dg-c" x="893" y="436">upsert by window key</text>
  <text class="dg-s dg-c" x="893" y="452">10 y</text>
  <path class="dg-line" d="M 630,428 L 644,428"></path>
  <path class="dg-head" d="M 644,433 L 644,423 L 652,428 Z"></path>
  <path class="dg-line" d="M 656,214 L 656,340"></path>
  <path class="dg-line" d="M 560,340 L 893,340"></path>
  <path class="dg-line" d="M 560,340 L 560,384"></path>
  <path class="dg-head" d="M 555,384 L 565,384 L 560,392 Z"></path>
  <path class="dg-line" d="M 893,340 L 893,384"></path>
  <path class="dg-head" d="M 888,384 L 898,384 L 893,392 Z"></path>
  <text class="dg-lbl dg-c" x="610" y="334">batched inserts</text>
  <rect class="dg-box" x="652" y="500" width="316" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="810" y="526.5">Query API — /rollups · /delta with coverage</text>
  <text class="dg-s dg-c" x="810" y="542.5">→ the operator map · the Demand response page</text>
  <path class="dg-line" d="M 893,464 L 893,492"></path>
  <path class="dg-head" d="M 888,492 L 898,492 L 893,500 Z"></path>
  <text class="dg-s" x="20" y="586">The live path never waits for the late path: readings.late has its own consumer group, an hour behind, and its rollups are marked backfilled.</text>
  <text class="dg-note" x="20" y="608">An outbox on a meter is the billing page's answer to a question this page does not have — a lost reading is a counted metric, not revenue.</text>
</svg>
</div>

<p class="diagram-cap">Draw the source line with its arithmetic before any box — ten million meters, one reading every ten seconds, a million a second, lossy. Every box after it is cheaper than the billing page's because of that last word, and the late-readings topic is the one box people forget: it is what keeps a basement meter's hour of backlog out of the live watermark.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 600" role="img" aria-label="Smart-meter telemetry high-level design in three lanes. Gateway: a reading arrives; if the producer buffer is over seventy percent, live readings are always forwarded and backlog is sampled one in k with a shed counter. Stream processor: the watermark is max event time minus twenty seconds; a reading within thirty seconds of allowed lateness enters an event-time window that fires when the watermark passes and upserts by window key; a later reading goes to the late topic, is counted, and is recomputed hourly by the backfill consumer. Query: a delta request reads two rollup rows and returns the delta with coverage and the late-excluded count.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Event time decides the window; the watermark decides when it fires; the lateness number decides what it costs.</text>
  <text class="dg-lane" x="30" y="76">GATEWAY — WHERE BACKPRESSURE ACTS</text>
  <rect class="dg-box" x="30" y="90" width="200" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="114.5">Reading arrives</text>
  <text class="dg-s dg-c" x="130" y="130.5">MQTT QoS 1 · batched</text>
  <text class="dg-s dg-c" x="130" y="146.5">event_ts, seq from the meter</text>
  <rect class="dg-warn" x="260" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="370" y="114.5">producer buffer &gt; 70 %?</text>
  <text class="dg-s dg-c" x="370" y="130.5">one open batch per partition</text>
  <text class="dg-s dg-c" x="370" y="146.5">linger 200 ms · 64 KB</text>
  <path class="dg-line" d="M 230,126 L 252,126"></path>
  <path class="dg-head" d="M 252,131 L 252,121 L 260,126 Z"></path>
  <rect class="dg-good" x="510" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="620" y="114.5">live → always forwarded</text>
  <text class="dg-s dg-c" x="620" y="130.5">event_ts ≈ now</text>
  <text class="dg-s dg-c" x="620" y="146.5">the map recovers first</text>
  <rect class="dg-warn" x="760" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="870" y="114.5">backlog → sample 1-in-k</text>
  <text class="dg-s dg-c" x="870" y="130.5">shed_readings++</text>
  <text class="dg-s dg-c" x="870" y="146.5">never disconnect the meter</text>
  <path class="dg-line" d="M 480,126 L 502,126"></path>
  <path class="dg-head" d="M 502,131 L 502,121 L 510,126 Z"></path>
  <text class="dg-lbl dg-c" x="495" y="118">no</text>
  <path class="dg-line" d="M 370,162 L 370,176 L 870,176 L 870,170"></path>
  <path class="dg-head" d="M 875,170 L 865,170 L 870,162 Z"></path>
  <text class="dg-lbl dg-c" x="620" y="172">yes, and event_ts is old</text>
  <path class="dg-div" d="M 20,196 L 980,196"></path>
  <text class="dg-lane" x="30" y="230">STREAM PROCESSOR — WHERE TIME IS DECIDED</text>
  <rect class="dg-box" x="30" y="244" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="272.5">watermark = max(event_ts) − 20 s</text>
  <text class="dg-s dg-c" x="180" y="288.5">per partition · idle after 60 s</text>
  <rect class="dg-warn" x="360" y="244" width="280" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="500" y="272.5">event_ts ≥ watermark − 30 s ?</text>
  <text class="dg-s dg-c" x="500" y="288.5">allowed lateness: a chosen number</text>
  <path class="dg-line" d="M 330,276 L 352,276"></path>
  <path class="dg-head" d="M 352,281 L 352,271 L 360,276 Z"></path>
  <rect class="dg-good" x="670" y="244" width="290" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="815" y="272.5">event-time window, per cohort</text>
  <text class="dg-s dg-c" x="815" y="288.5">feeder · region · campaign</text>
  <path class="dg-line" d="M 640,276 L 662,276"></path>
  <path class="dg-head" d="M 662,281 L 662,271 L 670,276 Z"></path>
  <text class="dg-lbl dg-c" x="655" y="268">yes</text>
  <rect class="dg-good" x="670" y="330" width="290" height="90" rx="8"></rect>
  <text class="dg-good-t dg-c" x="815" y="355.5">fires when watermark &gt; window_end</text>
  <text class="dg-s dg-c" x="815" y="371.5">stays open 30 s more, re-fires on a late row</text>
  <text class="dg-s dg-c" x="815" y="387.5">upsert by (cohort, 1m, window_start)</text>
  <text class="dg-s dg-c" x="815" y="403.5">a re-fired window overwrites itself</text>
  <path class="dg-line" d="M 815,308 L 815,322"></path>
  <path class="dg-head" d="M 810,322 L 820,322 L 815,330 Z"></path>
  <rect class="dg-warn" x="360" y="330" width="280" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="500" y="354.5">late → readings.late</text>
  <text class="dg-s dg-c" x="500" y="370.5">late_excluded++ · late_by_s</text>
  <text class="dg-s dg-c" x="500" y="386.5">never touches an open window</text>
  <path class="dg-line" d="M 500,308 L 500,322"></path>
  <path class="dg-head" d="M 495,322 L 505,322 L 500,330 Z"></path>
  <text class="dg-lbl dg-c" x="520" y="322">no</text>
  <rect class="dg-box" x="30" y="330" width="300" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="354.5">backfill consumer, hourly</text>
  <text class="dg-s dg-c" x="180" y="370.5">raw rows with is_late=1</text>
  <text class="dg-s dg-c" x="180" y="386.5">touched rollups → backfilled=1</text>
  <path class="dg-line" d="M 360,366 L 338,366"></path>
  <path class="dg-head" d="M 338,361 L 338,371 L 330,366 Z"></path>
  <path class="dg-div" d="M 20,440 L 980,440"></path>
  <text class="dg-lane" x="30" y="474">QUERY — WHERE COVERAGE IS REPORTED</text>
  <rect class="dg-box" x="30" y="488" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="516.5">/delta?cohort=campaign:987&amp;t=T</text>
  <text class="dg-s dg-c" x="180" y="532.5">window=5m</text>
  <rect class="dg-box" x="360" y="488" width="280" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="508.5">two rollup reads</text>
  <text class="dg-s dg-c" x="500" y="524.5">[T−5m, T) and [T, T+5m)</text>
  <text class="dg-s dg-c" x="500" y="540.5">no raw scan</text>
  <path class="dg-line" d="M 330,520 L 352,520"></path>
  <path class="dg-head" d="M 352,525 L 352,515 L 360,520 Z"></path>
  <rect class="dg-good" x="670" y="488" width="290" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="815" y="508.5">delta_kw · coverage 0.962</text>
  <text class="dg-s dg-c" x="815" y="524.5">late_excluded: 4 811</text>
  <text class="dg-s dg-c" x="815" y="540.5">distinct meters / cohort size</text>
  <path class="dg-line" d="M 640,520 L 662,520"></path>
  <path class="dg-head" d="M 662,525 L 662,515 L 670,520 Z"></path>
  <text class="dg-note" x="30" y="580">A restart restores state and offsets from one checkpoint, so replayed windows re-fire with the same keys — the watermark makes a replay produce the live run's answer.</text>
</svg>
</div>

<p class="diagram-cap">The lane in the middle is the whole argument. Say the watermark formula, then say the lateness number, then say what falls outside it goes to its own topic — and only then draw the store. A candidate who draws Kafka → Flink → ClickHouse and never says thirty seconds has drawn a category, not a design.</p>

### Flow A — steady state: a reading becomes a feeder's load

1. The meter publishes a batch of one to `meters/{device_id}` over MQTT. The gateway appends it to its Kafka producer buffer, partition `hash(device_id) % 200`.
2. `linger.ms` expires; the gateway sends a 64 KB batch to the broker, waits for `acks=all`, then sends PUBACK. The meter drops the reading from its buffer.
3. The stream processor consumes the partition, dedupes on `(device_id, seq)` against a 7-day TTL keyed state, and advances the partition's watermark to `max(event_ts) − 20 s`.
4. It looks up the meter's cohorts — feeder, region, and any active campaign — from the broadcast dimension (§9), and adds the reading to each cohort's open one-minute window.
5. When the watermark passes `window_end + 30 s`, the window fires: one upsert per cohort into the rollup table, keyed `(cohort_id, 1m, window_start)`.
6. The operator map polls `/v1/rollups` for its feeders; the row is there **≤ 30 s after the minute closed in event time** (→ the rollup-freshness NFR).
7. **The failure path.** The gateway dies between step 1 and step 2. The meter never gets a PUBACK, resends the batch to whichever gateway it reconnects to, and the processor's dedupe on `(device_id, seq)` discards the copy if the first one had in fact been sent. **A gateway holds nothing that matters for longer than one linger interval**, which is why there are 200 of them and none of them is special.

### Flow B — a tower comes back: a million meters, an hour of backlog each

1. Each meter reconnects (jittered by its firmware over ~2 minutes — say that you'd insist on it) and sends its **live reading first**. The map is correct for that feeder within one window.
2. Then it drains its buffer, oldest first: 360 readings, each with an `event_ts` an hour old.
3. The processor sees `event_ts` an hour behind the watermark. Every one is **late beyond allowed lateness**: it goes to `readings.late` with `late_by_s ≈ 3600`, is counted on the `late_excluded` metric, and **does not touch any open window**.
4. The backfill consumer (§11) reads `readings.late` at its own pace, writes the rows into raw storage with `is_late = true`, and recomputes the affected cohort-minutes in hourly batches, marking them `backfilled`.
5. The 7 a.m. graph never spiked, and by 8 a.m. the 6 a.m. graph is correct and labelled as revised.
6. **The failure path.** 360 M readings in a few minutes is 3× ingest. Gateways watch their producer buffer depth; past a threshold they **sample backlog batches** (keep every 4th reading) and increment `shed_readings`. Live readings are never sampled — the gateway can tell them apart by `event_ts`. The loss lands in the budget (§2), it is counted, and the map is never wrong, only sparser for the hour that was already lost.

### Flow C — measuring a command's effect

1. The Demand response page creates a campaign targeting 1 M meters and, as part of creation, writes the target set as a **cohort snapshot** — one bulk insert of a million ids, and a small message to the processor's broadcast stream saying "campaign 987 is active over this cohort."
2. From that point every reading from a targeted meter is also added to `campaign:987`'s windows. Nothing about the live path changed; one more cohort key per reading.
3. The command fires at *T*. Operators call `/v1/delta?cohort=campaign:987&t=T&window=5m`.
4. The API reads the rollup rows for `[T−5m, T)` and `[T, T+5m)`, averages `sum_kw` per minute, subtracts, and reports **coverage**: `distinct_devices` seen in both windows over the cohort size.
5. `delta_kw = −372 MW, coverage 0.962` — the number the regulator asked for, minutes after *T*, and the number the Demand response page uses to mark silent-but-compliant meters as executed (its §10).
6. **The failure path.** Coverage comes back at 0.61 because a region was mid-outage. The delta is *reported with that coverage*, not hidden, and the honest sentence is "the measurement is inconclusive for that region until backfill lands." An API that returned `delta_kw` alone would have reported a confident wrong number.

### Flow D — the stream processor restarts mid-window

1. The processor checkpoints every 60 s: keyed window state and dedupe state to object storage, Kafka offsets alongside them.
2. A task manager dies. The job restores from the last checkpoint — offsets and state together, so the two agree by construction — and replays up to 60 s of the partition.
3. Replayed readings re-enter their windows; the dedupe state came from the same checkpoint, so nothing is double-counted. Windows that had already fired fire again with identical values; the **upsert by window key** makes that a no-op.
4. Live rollups are **≤ 60 s later than usual** for one minute (→ the rollup-freshness NFR is missed by one window, and the freshness field on the API says so).
5. **The failure path.** The job is down for four hours. Kafka has held everything; the processor comes back and works through four hours of backlog at full throughput in about twenty minutes, watermarks sweeping forward as it goes. Nothing is lost and nothing is late in the *event-time* sense — the windows are computed exactly as they would have been. **Say this:** *"the watermark is what makes a replay produce the same answer as the live run."*

---

## 7 · Deep dive — the ingest path: partition count and batching math, or why "put it on Kafka" is not an answer

### What you'd reach for first

Each gateway calls `producer.send()` per reading on a topic with the default partition count. "Kafka handles a million a second."

### What breaks

- **The default partition count is single digits.** Twelve partitions at 5–10 k msg/s each is 100 k msg/s — a tenth of the load — and the consumer parallelism is capped at twelve tasks for a job that needs ~200.
- **Per-reading sends are a request storm, not a byte problem.** A million sends a second, each its own request, across ~20 brokers is 50 k requests/s per broker. Brokers fall over on request rate long before they fall over on 100 MB/s.
- **Changing the partition count later reshuffles every key.** A meter's readings move partitions, and for the seconds around the change its `seq` ordering is split across two consumers. It is a planned event with a runbook, not a config change.

### What replaces it

- **200 partitions, keyed by `device_id`, from day one.** Per-meter ordering lands in one partition, which is what lets the processor detect a gap in `seq` without a shuffle. 5 k msg/s per partition at steady state, 15 k in the burst — inside the envelope with room.
- **Batching in the gateway producer:** `linger.ms = 200`, `batch.size = 64 KB`, `compression = zstd`, `acks = all`, `enable.idempotence = true`. Each gateway holds one open batch per partition; at 5 k msg/s per gateway that is a few messages per partition per flush — thin, which is exactly why `linger` is 200 and not 5. The cost is 200 ms of latency against a 30 s target.
- **The rejected alternative, and the sentence:** *"I could partition by `gateway_id` instead — then every gateway writes one fat batch to one partition and the request rate collapses by 200×. I'm not, because a meter that reconnects to another gateway changes partition and I lose per-meter ordering, and I'd have to pay a full keyBy shuffle in the processor to get it back. If produce-request rate ever becomes the broker bottleneck, that is the switch I'd make, and I'd pay the shuffle."*
- **~20 brokers**, sized on **replicated bytes** (300 MB/s) and **request rate** (≈4 k/s per broker with the batching above), not on message count.

**Cost, volunteered:**

- **200 ms of batching latency** on every reading, and a gateway restart loses one open batch per partition — a few hundred readings, which the meters resend on missing PUBACK.
- **Idempotent producers cost a sequence number per partition per producer** and pin you to one producer instance per gateway. Fine; there is one.
- **Partition count is fixed** for practical purposes. 200 is sized for 3× growth in meters before it has to change.

**→ ties to the sustained-ingest and burst NFRs.**

---

## 8 · Deep dive — event time, watermarks, and the lateness number you have to pick

### What you'd reach for first

Window by the clock on the wall: every reading that arrives between 07:00:00 and 07:01:00 goes into the 07:00 window.

### What breaks

- **The basement.** A meter offline for an hour sends 360 readings at 07:00. Arrival-time windowing puts an hour of load into one minute: the feeder appears to spike 60×, the alert fires, and the 06:00 windows — the ones the readings belong to — stay wrong forever.
- **The delta is wrong for exactly the meters that matter.** The Demand response page's measurement window is five minutes either side of *T*. Any meter with a hiccup during it reports its *T*−2 reading at *T*+3, and arrival-time windowing moves load from before the command to after it — the error has the same sign as the effect being measured.
- **Replay is not reproducible.** Restore from a checkpoint and re-process, and every reading lands in a different arrival window than it did the first time. Flow D's "same answer as the live run" is impossible.

### What replaces it

**Event-time windows, a per-partition watermark, a chosen allowed lateness, and a side output.**

- **Windows are keyed by `event_ts`.** A reading with `event_ts = 06:14:30` goes into the 06:14 window no matter when it arrives.
- **The watermark is `max(event_ts seen on this partition) − 20 s`.** It is the processor's claim that "no reading earlier than this is still coming." Twenty seconds covers cellular jitter and one gateway linger; it is measured off `ingest_ts − event_ts` p99 in steady state (about 6 s) with headroom.
- **Allowed lateness is 30 s.** A window fires when the watermark passes its end, and stays open — its state retained — for 30 more seconds. A reading landing in that grace period re-fires the window with an updated value (the upsert by key makes that cheap). After 30 s the window's state is dropped.
- **Beyond that, the reading is late.** It goes to the `readings.late` side output, is counted, and never touches an open window (§11).
- **Say the trade, then pick the number.** *"Every second of allowed lateness is a second of window state I keep for ten million keys — about 17 MB a second, so 30 s is half a gigabyte and 10 minutes is five and a half. Thirty seconds covers everything except a genuinely offline meter, and offline meters are hours late, not minutes — so no number I could pick would catch them in the live path, and that's why backfill is a separate path rather than a bigger number here."*
- **Idle partitions hold the watermark hostage**, and this is the mechanic to mention: the job's watermark is the *minimum* across partitions, so one partition with no traffic stops every window from firing. **Mark a partition idle after 60 s of silence** and exclude it from the minimum.
- **Bound the meter's clock.** A reading with `event_ts > ingest_ts + 5 min` is from a meter with a broken clock, not from the future. Quarantine it: store raw with a flag, count it, exclude it from windows. Ten million cheap clocks and some of them are wrong.

**Cost, volunteered:**

- **~1 GB of keyed window state**, checkpointed every minute — a few hundred MB of incremental checkpoint a minute to object storage, and a restore time of tens of seconds.
- **A window can fire more than once.** Consumers of the rollup table must treat rows as upserts, never as append-only facts — which is why the API carries `freshness_s` and the backfill path marks rows `backfilled`.
- **Late is a policy, and a number in the policy will be wrong for someone.** A meter that is reliably 45 s late — a bad cell — is permanently excluded from live rollups and permanently correct in backfill. That is the right behaviour and it needs to be written down before the first operator asks why their feeder undercounts.

**→ ties to the rollup-freshness and allowed-lateness NFRs.**

---

## 9 · Deep dive — aggregation consumers and the before/after delta: measuring a command's effect

### What you'd reach for first

When the operator asks, run the query: scan raw for every targeted meter, five minutes before and after *T*, average, subtract.

### What breaks

- **600 M rows per question** (§3). ClickHouse scans a billion simple rows a second on a good node, so the first answer takes a few seconds, the tenth concurrent one takes a minute, and the raw table is also taking 1 M inserts/s at the time.
- **The cohort is defined by something ingest doesn't know.** The target set is decided by a predicate on the Demand response page, at campaign creation. Joining 10 M ids against 600 M rows at query time is a semi-join the sort key was not built for.
- **No coverage.** A scan returns a number. It does not return "from what fraction of the cohort," and the number without the fraction is how a 60 %-coverage delta gets reported as a fact.

### What replaces it

**Cohorts are applied in the stream processor, from a broadcast dimension, and the delta is two rollup reads.**

- **Static cohorts** — feeder, region — come from the device dimension, loaded into every processor task as a **broadcast state** (10 M rows × ~30 B = 300 MB, refreshed hourly from the dimension table via CDC).
- **Campaign cohorts** arrive on a control stream: `{campaign_id, cohort_snapshot_ref, active_from, active_until}`. The processor loads the snapshot (a million ids, ~8 MB) into the same broadcast state. From then until `active_until`, every reading from a member is also aggregated under `campaign:987`.
- **One reading, N cohort keys.** Each reading updates its feeder window, its region window, and 0–2 campaign windows. The per-cohort rollup is `(count, sum_kw, min, max, distinct_devices)` — the distinct count is an HLL sketch, because 10 M exact ids per window per cohort is the state budget again.
- **The delta query** reads 10 rollup rows (five minutes before, five after), averages `sum_kw`, subtracts, and reports `coverage = distinct_devices / cohort_size` for each window, plus `late_excluded` from the counter. Sub-second, with the raw table untouched.
- **The `executed_silently` handoff.** The Demand response page has meters that never acked but might have complied. It asks this page, per meter, for `kw` in the minute before and after *T* — a **point read on the per-meter hourly rollup for old data, or raw within 30 days** — and applies its own threshold. This page provides the reading and the coverage; the other page owns the inference and the threshold, and saying which page owns which is the boundary that keeps both honest.
- **The rejected alternative, and the sentence:** *"I could store the cohort ids on each reading at ingest — then any query is a filter. I'm not, because it bakes a changeable dimension into 8.6 TB a day of immutable rows, and a campaign created at 07:00 wouldn't be on any reading before 07:00. Applying membership at rollup time means a cohort exists the instant it's declared and costs one key per reading, not a schema."*

**Cost, volunteered:**

- **Broadcast state is per task.** 300 MB × 200 tasks = 60 GB of memory across the job, for a dimension that changes hourly. Acceptable; it is the price of no shuffle.
- **A membership change re-rolls forward, not backward.** A meter moved to a new feeder at 09:00 is in the new feeder's windows from 09:00; the old windows are not rewritten. That is correct — it is what happened — and it needs a sentence in the operator docs.
- **HLL distinct counts are ±1 %** at the precision that fits. Coverage of 0.962 is really 0.952–0.972, and the API should say so.
- **The ad-hoc case is still slow.** "Meters whose kw exceeded 5 kW at any point last week" is a raw scan, minutes, and it goes to the analytics replica (§15), not the live cluster.

**→ ties to the cohort-query-latency NFR.**

---

## 10 · Deep dive — storage: why not Postgres, why not Cassandra for the reads, and the retention you have to say

### What you'd reach for first

A Postgres table `readings(device_id, event_ts, kw, …)` with a B-tree on `(device_id, event_ts)`. Or, having heard that's wrong, Cassandra with `device_id` as the partition key.

### What breaks

- **Postgres at 1 M inserts/s** is a B-tree taking a million leaf updates a second with WAL and vacuum behind it — a single primary manages perhaps 50 k/s of small inserts on good hardware, so this is twenty shards before the first query runs, and the 30-day table is 2.6 B rows per shard. TimescaleDB pushes the ceiling up meaningfully (hypertable chunks, compression) and is **the right answer at a tenth of this scale**; at this one it is a sharding project.
- **Cassandra ingests this beautifully and cannot answer the questions.** The partition is a meter; the query is "all meters on this feeder in this five minutes." That is a cross-partition scan of 10 M partitions, which Cassandra does not do and will not be made to do. Cassandra fits a per-source event log read by source. This workload's reads are by *cohort and window*, and the rows the query wants are spread over every node.
- **Neither one has downsampling as a primitive.** Ten years of raw in either store is 3 PB, and "we'll write a job" is a job nobody writes until the disk is full.

### What replaces it

**A columnar time-series store — ClickHouse — with a sort key for the queries, TTL-driven tiering, and materialized views for the downsampled series.**

- **Raw table:** `MergeTree`, `PARTITION BY toDate(event_ts)`, `ORDER BY (device_id, event_ts)`. Per-meter reads inside 30 days are a range on the sort key; the daily partition is what makes `TTL 30 DAY` a directory delete rather than a 1 B-row `DELETE`.
- **Inserts come from the processor in batches of ~10 k rows per second per task** — ClickHouse wants few, large inserts, and the stream processor is already batching. Never one row at a time.
- **Late rows are handled by `ReplacingMergeTree` keyed on `(device_id, seq)`**: a resent reading collapses on merge, and a late one is simply an insert with `is_late = 1`. No point updates — ClickHouse has none worth using — and none are needed.
- **Per-cohort minute rollups** are a table the processor upserts into (`ReplacingMergeTree` on the window key, §4). **Per-meter hourly** is a `MATERIALIZED VIEW` off raw — `AggregatingMergeTree` with `sumState`/`countState` — so it is computed on insert and never as a batch job. 240 M rows/day, `TTL 2 YEAR`.
- **Tiering:** raw hot on NVMe for 30 days, then dropped — the hourly and cohort series are the retained history. Cohort-minute rows for 10 years are ~50 GB total. Say the three numbers together: *"raw thirty days, per-meter hourly two years, cohort minutes ten years."* That sentence is the retention policy, and it is the one the mock left unsaid.
- **The rejected alternatives, and the sentences:** *"Timescale wins at a tenth of this scale and I'd take it for the SQL and the operational simplicity — but here it's a sharding project on top of a database. Druid or Pinot win if the requirement were sub-second ad-hoc slicing on a live stream with high concurrency; the operator map is a few hundred fixed queries and ClickHouse's materialized views serve those at a fraction of the ops burden. Cassandra ingests this fine and can't answer a single cross-meter question."*

**Cost, volunteered:**

- **ClickHouse is eventually consistent across replicas** (replicated tables ship parts asynchronously, typically sub-second). A rollup read immediately after a write may miss it on another replica; the API's `freshness_s` absorbs this and the operator map polls anyway.
- **Merges are background work that competes with inserts.** Too many small parts and the cluster stalls with "too many parts" — the fix is the batching above and monitoring `parts_to_merge`. This is the one operational failure mode to name.
- **No updates means corrections are new rows.** A mis-calibrated meter's readings are not fixed in place; a correction factor is applied at rollup and the raw stays what the meter said. Same principle as the billing page's ledger, for a different reason: not audit, but because the store cannot do otherwise cheaply.
- **A cluster of ~30 nodes and a team that knows it.** Snowflake or BigQuery would take the batches and the SQL and remove the ops burden at a per-query bill that is fine for planning queries and ruinous for the operator map at one poll a second — which is why the live store and the analytics store (§15) may reasonably be two products.

**→ ties to the retention and cohort-query-latency NFRs.**

---

## 11 · Deep dive — failure modes: processor restart, the late burst after a partition, and backpressure

### What you'd reach for first

Restart the job and let it catch up. If it's overloaded, add consumers.

### What breaks

- **Restart without a checkpoint loses or doubles every open window.** State in memory is gone; offsets committed independently of state either skip the readings in flight (loss) or replay them into windows that already fired (double count). Neither is inside the 0.1 % budget when a restart hits a busy minute.
- **A regional outage ending is 360 M late readings in a few minutes** (§3). Through the live path they are all beyond lateness, so they all go to the side output — and if the side-output consumer is the same job, its backlog stalls the watermark for live traffic too.
- **Adding consumers doesn't help a producer-side bottleneck.** The burst arrives at 200 gateways; if their producer buffers fill, more Flink tasks change nothing. Backpressure has to act where the bytes enter.

### What replaces it

- **Checkpoints every 60 s, state and offsets atomically**, to object storage, with incremental RocksDB checkpoints so each one is the delta. Restore = last checkpoint + replay ≤ 60 s of partitions. The dedupe state and the window state restore together, and upserts by window key make re-fired windows harmless (Flow D). This is the mechanism behind the fault-tolerance row in §2, and it is worth saying that **the checkpoint interval is the RPO** — 60 s of recomputation, zero loss.
- **Kafka is the buffer.** Seven days of retention means a four-hour outage of the processor or the store is a replay, not an incident. The only unrecoverable case is exceeding it, which is why §2 names it.
- **The late path is its own consumer group on `readings.late`**, batch-oriented, restartable, and allowed to be an hour behind. It writes raw rows with `is_late = 1` and, hourly, recomputes the affected `(cohort, minute)` rollups from raw for the touched windows and upserts them with `backfilled = 1`. The live job never waits for it.
- **Backpressure at the gateway, as sampling with a counter.** Each gateway watches its producer buffer (`buffer.memory` occupancy); past 70 % it samples *backlog* batches at 1-in-*k* (k rising with occupancy) and increments `shed_readings{gateway, reason=backlog}`. Live readings are exempt. The meter is never disconnected — a disconnect is a reconnect storm ten minutes later.
- **Meters jitter their reconnect** over a window proportional to the outage length, and send live before backlog. Firmware you'd specify, because the pipeline's burst number depends on it.

**Cost, volunteered:**

- **Sampling is loss**, and the design chooses it over queueing because the readings being sampled are already an hour stale. The count makes it visible; the budget makes it acceptable.
- **Backfilled rollups arrive up to an hour after the outage ends**, labelled. The operator UI has to render "revised" — a product cost of the two-path design.
- **Two consumer groups on one firehose are twice the Kafka read bandwidth.** 100 MB/s becomes 200 MB/s of egress in the burst. Sized for, and cheap next to the alternative of one job that stalls its own watermark.

**→ ties to the burst, acceptable-loss, and fault-tolerance NFRs.**

---

## 12 · Data model, sharding, and storage decisions

**Partition on `device_id` on the ingest side, and say why the sort key is the same.** Per-meter ordering in Kafka is what makes gap detection and dedupe local to one task; `ORDER BY (device_id, event_ts)` in the raw table is what makes a meter's 30-day history a range read. **The Demand response page partitions its send side by campaign and its receive side by device** — the receive side is this page, and it is by device for the same reason.

**The hot key is a cohort, not a meter, and the design absorbs it in the processor.** A region cohort receives 2 M readings a minute into one window key. Flink handles that as one hot key per task — it is a single accumulator being incremented, not a lookup — and the rollup table receives one row per minute for it. **The hot key never reaches a database**, which is the property to name.

**Cohort membership lives in broadcast state, not in the raw rows**, and the raw rows carry no dimension columns at all — 8.6 TB a day is the reason (§9).

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **MQTT gateways** | 50 k sockets each, batch buffer of ≤ 200 ms | None — a lost batch is resent by the meter on missing PUBACK | **Stateless service**, 200 of them behind an L4 balancer; EMQX or a Netty-based service | "They hold a socket and an open Kafka batch. Any gateway serves any meter, and a restart costs one linger interval of resends" |
| **Readings log** | 1 M/s append, 200 partitions, two consumer groups | Zero acknowledged loss, 7-day replay | **Kafka**, key `device_id`, `acks=all`, `min.insync.replicas=2`, `zstd` | "Kinesis would take the writes and cap me at 1 MB/s per shard — a thousand shards — and Pub/Sub has no per-key ordering I can lean on. I need replay and a second consumer group, and I need per-meter order" |
| **Late readings** | Bursty append, slow batch consumer | Same as above | **Kafka**, topic `readings.late`, 24-hour retention | "Its own topic so the backfill consumer can be an hour behind without stalling the live watermark" |
| **Window and dedupe state** | 10 M keys read-modify-write per reading | Rebuildable from Kafka; checkpointed every 60 s | **Flink keyed state on RocksDB**, incremental checkpoints to **S3** | "Kafka Streams would do this too and I'd pick it if the team were already on it; Flink's event-time and watermark model is the one I want to be explaining in a postmortem" |
| **Cohort dimension** | Read by every task per reading | Durable, changes hourly | **Broadcast state**, loaded from a **Postgres** device table via CDC | "Three hundred megabytes per task in exchange for no shuffle on a million a second" |
| **Raw readings** | 1 M/s batched insert; per-meter range reads; rare cohort scans | 30 days, RF 2 | **ClickHouse** `ReplacingMergeTree(seq)`, `ORDER BY (device_id, event_ts)`, `PARTITION BY toDate(event_ts)`, `TTL 30 DAY` | "Postgres dies at the insert rate and Cassandra can't answer a cross-meter question. Timescale is the right call at a tenth of this" |
| **Cohort minute rollups** | Upsert by window key; read by the map at ~1 k/s | 10 years — the history | **ClickHouse** `ReplacingMergeTree`, `ORDER BY (cohort_id, granularity, window_start)` | "Upsert by key is the exactly-once story. A re-fired window overwrites itself" |
| **Per-meter hourly** | Computed on insert; point reads for old data | 2 years | **ClickHouse `MATERIALIZED VIEW`**, `AggregatingMergeTree`, `TTL 2 YEAR` | "Downsampling is a view, not a job — it can't be forgotten" |
| **Campaign cohort snapshots** | One bulk write per campaign; read once into broadcast state | Until the campaign closes + 30 days | **S3 object** per campaign (a million ids, ~8 MB), referenced from the control stream | "It's a list written once and read once. It doesn't want a database" |
| **Counters** — `late_excluded`, `shed_readings`, `future_clock`, watermark lag | Increment per event; read by dashboards | Best-effort | **Prometheus** metrics off the processor and gateways | "The counters are half of the loss requirement. They're not optional and they're not in the data path" |
| **Meter local buffer** | Append, drain on ack | Durable on the device, hours of readings | **Flash ring buffer** on the meter, oldest-first drain, live-first on reconnect | "The meter is the durability before the ack. Firmware I'd want to own the spec of" |

### Data lifecycle — the append-only entities

| Entity | Growth | Hot | Warm | Cold | Restore |
|---|---|---|---|---|---|
| **Raw readings** | 8.6 TB/day raw, **~1 TB/day compressed** | 30 days on NVMe, p99 < 200 ms per-meter | — | **Dropped.** The hourly and cohort series are the history | n/a — the choice to keep no raw beyond 30 days is a product decision (dispute window), and if Legal says 90, the TTL changes and nothing else does |
| **Per-meter hourly** | 240 M rows/day, ~5 GB/day | 2 years, ~3.6 TB | — | Dropped at 2 years; a Parquet export to S3 monthly if planning wants it | Minutes, from the export |
| **Cohort minute rollups** | ~14 M rows/day, tiny | 10 years, ~50 GB total | — | — | Never needed |
| **Readings log (Kafka)** | ~8.6 TB/day | 7 days | — | — | Not an archive. Day 8 is in ClickHouse or nowhere |
| **Late readings (Kafka)** | Bursty, hours-scale | 24 hours | — | — | Consumed into raw within the hour |

### The signals that tell you this is broken

Throughput graphs look identical whether the pipeline is right or wrong — a million a second is a million a second. The honest signals are about **time and loss**:

- **Watermark lag per partition** — `now − watermark`. Steady state ~25 s. Rising on one partition is a slow task or an idle-partition bug; rising on all is the processor falling behind, and it is the leading indicator for every rollup being late.
- **`late_excluded` rate** — readings past allowed lateness. A background trickle is normal; a step is an outage ending (fine) or a watermark misconfiguration (not fine), and the two look different by `late_by_s`.
- **`shed_readings` by gateway** — the loss budget being spent. Should be zero outside a burst.
- **Rollup freshness** — event-time window end to row visible, p99. The user-facing NFR, measured directly.
- **`future_clock` count** — meters whose clocks are wrong. Slowly rising means a firmware batch is bad.
- **Coverage on every delta response**, graphed. A coverage drop with no outage is a cohort snapshot that went wrong.
- Plus ClickHouse `parts_to_merge` and insert latency, consumer lag per group, and checkpoint duration — the unglamorous three that page someone.

---

## 13 · Traps — the ranked list

**Design traps**

1. **Windowing by arrival time.** The basement meter spikes the 7 a.m. graph and rewrites nothing it should. Every downstream number is wrong in the direction of the effect being measured (§8).
2. **"Lateness is a trade-off" with no number.** It is a number times ten million keys. Pick it, say the state it costs, say what falls outside it (§8).
3. **The time-series store unnamed, or named without retention and downsampling.** "A TSDB" is a category; ClickHouse with thirty days raw, two years hourly, ten years cohort minutes is a design (§10).
4. **Postgres at a million inserts a second.** Twenty shards before the first query. Timescale is the honest answer at a tenth of the scale (§10).
5. **Cassandra for the cross-meter read.** Perfect partition for ingest, and the query wants every partition (§10).
6. **`producer.send()` per reading on default partitions.** A request storm at a tenth of the needed parallelism (§7).
7. **Keying Kafka by region or by campaign.** One partition takes a region's 2 M readings a minute; the rest idle. Key by the finest unit — the meter — and aggregate downstream (§7, §12).
8. **A delta with no coverage.** A confident number from 60 % of the cohort, reported as a fact (§9).
9. **Backfill through the live path.** An hour of backlog stalls the watermark for everyone; the late readings need their own consumer (§11).
10. **An outbox on a meter** — exactly-once machinery for a lossy pipeline. The billing page needs it because a lost event is money; here it costs a database write per reading to protect a rounding error (contrast, header).
11. **Trusting the meter's clock.** Ten million cheap clocks; some are in the future. Bound it and count it (§8).
12. **Dropping late readings silently.** The 0.1 % budget is fine; the uncounted 0.1 % is the incident (§2).
13. **Cohort ids baked into the raw rows.** A campaign created at 07:00 is on no reading before 07:00, and a feeder change rewrites terabytes (§9).

**Performance traps**

14. **Answering cohort questions from raw.** 600 M rows per question, against a table taking a million inserts a second (§9).
15. **Unbounded allowed lateness.** Unbounded state; the checkpoint grows until the restore takes longer than the interval (§8).
16. **Checkpoints every ten minutes** because every minute "seemed expensive." Ten minutes of replay on every restart, at 1 M/s (§11).
17. **Adding stream-processor tasks for a gateway-side bottleneck.** The bytes are stuck in the producer buffers; consumers can't help (§11).
18. **Row-at-a-time inserts into ClickHouse.** "Too many parts," then merges fall behind, then inserts stall (§10).
19. **An exact distinct count per cohort per window.** Ten million ids per window per cohort is the state budget again; it is an HLL (§9).
20. **One partition idle stalling every window.** The minimum-watermark rule, forgotten (§8).

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

21. **Spending the round on the ingest boxes and none on the query.** Gateways, Kafka, and a processor are the same three boxes on every telemetry page; the difference between candidates is whether the store can answer "before and after, for these meters, with coverage." Draw toward the query.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 450" role="img" aria-label="Smart-meter telemetry five-minute skeleton. The source line with its arithmetic across the top; then gateways, the readings topic and the event-time processor; then the late path, ClickHouse and the cohort dimension; then the query API and the retention sentence; and a margin lane of the signals and the sentence about the outbox.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="44" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="94.5">10 M meters × 1 / 10 s = 1 M/s · ~100 B each · lossy OK — write “loss is a metric” before any box</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="30" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="148.5">MQTT gateways</text>
  <text class="dg-s dg-c" x="180" y="164.5">200 × 50 k · linger 200 ms · PUBACK after acks=all</text>
  <text class="dg-s dg-c" x="180" y="180.5">sample backlog, count it</text>
  <circle class="dg-num" cx="30" cy="128" r="9"></circle>
  <text class="dg-num-t" x="30" y="131.4">2</text>
  <rect class="dg-box" x="350" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="148.5">Kafka readings</text>
  <text class="dg-s dg-c" x="500" y="164.5">key device_id · 200 partitions · RF 3 · 7 d</text>
  <text class="dg-s dg-c" x="500" y="180.5">per-meter order; the count is fixed</text>
  <circle class="dg-num" cx="350" cy="128" r="9"></circle>
  <text class="dg-num-t" x="350" y="131.4">3</text>
  <rect class="dg-box" x="670" y="128" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="148.5">Flink — event time</text>
  <text class="dg-s dg-c" x="815" y="164.5">watermark −20 s · lateness 30 s</text>
  <text class="dg-s dg-c" x="815" y="180.5">dedupe (device_id, seq) · ckpt 60 s</text>
  <circle class="dg-num" cx="670" cy="128" r="9"></circle>
  <text class="dg-num-t" x="670" y="131.4">4</text>
  <rect class="dg-box" x="30" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="232.5">readings.late → backfill</text>
  <text class="dg-s dg-c" x="180" y="248.5">an hour behind · rows marked backfilled</text>
  <circle class="dg-num" cx="30" cy="208" r="9"></circle>
  <text class="dg-num-t" x="30" y="211.4">5</text>
  <rect class="dg-box" x="350" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="232.5">ClickHouse</text>
  <text class="dg-s dg-c" x="500" y="248.5">raw 30 d · cohort rollups · per-meter hourly MV</text>
  <circle class="dg-num" cx="350" cy="208" r="9"></circle>
  <text class="dg-num-t" x="350" y="211.4">6</text>
  <rect class="dg-box" x="670" y="208" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="232.5">Cohort dimension</text>
  <text class="dg-s dg-c" x="815" y="248.5">feeder · region · campaign snapshot → broadcast</text>
  <circle class="dg-num" cx="670" cy="208" r="9"></circle>
  <text class="dg-num-t" x="670" y="211.4">7</text>
  <rect class="dg-box" x="30" y="284" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="308.5">Query API</text>
  <text class="dg-s dg-c" x="180" y="324.5">/rollups · /delta with coverage + late_excluded</text>
  <circle class="dg-num" cx="30" cy="284" r="9"></circle>
  <text class="dg-num-t" x="30" y="287.4">8</text>
  <rect class="dg-good" x="350" y="284" width="610" height="56" rx="8"></rect>
  <text class="dg-good-t dg-c" x="655" y="308.5">Retention, in one sentence</text>
  <text class="dg-s dg-c" x="655" y="324.5">raw 30 d · per-meter hourly 2 y · cohort minutes 10 y</text>
  <circle class="dg-num" cx="350" cy="284" r="9"></circle>
  <text class="dg-num-t" x="350" y="287.4">9</text>
  <text class="dg-lane" x="30" y="370">IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="400.5">watermark lag</text>
  <text class="dg-s dg-c" x="140" y="416.5">now − watermark, per partition</text>
  <circle class="dg-num" cx="30" cy="382" r="9"></circle>
  <text class="dg-num-t" x="30" y="385.4">10</text>
  <rect class="dg-box" x="270" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="380" y="400.5">late_excluded · shed</text>
  <text class="dg-s dg-c" x="380" y="416.5">the loss budget, spent visibly</text>
  <rect class="dg-box" x="510" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="400.5">coverage on every delta</text>
  <text class="dg-s dg-c" x="620" y="416.5">a number without it is a guess</text>
  <rect class="dg-box" x="750" y="382" width="210" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="855" y="400.5">no outbox here</text>
  <text class="dg-s dg-c" x="855" y="416.5">that's the billing page</text>
</svg>
</div>

<p class="diagram-cap">Badge 1 is a line of arithmetic, not a box, and it goes on the board first. Badge 9 is a sentence — three numbers — and it is the one the reviewed mock left unsaid. Everything between them is the same three boxes every telemetry design has; the badges are what make this one a design.</p>

1. **The source line, with the arithmetic on it:** 10 M meters × 1 / 10 s = **1 M/s, ~100 B each, lossy OK.** Write "loss is a metric" in the margin before any box.
2. **MQTT gateways** — 200 × 50 k sockets, stateless, **batch to Kafka with `linger 200 ms`**, PUBACK after `acks=all`, **sample backlog under pressure and count it**.
3. **Kafka `readings`** — key `device_id`, **200 partitions**, RF 3, 7 days. Say "per-meter order, and the partition count is fixed."
4. **Stream processor (Flink)** — **event-time** one-minute windows, watermark `max(event_ts) − 20 s`, **allowed lateness 30 s**, dedupe on `(device_id, seq)`, cohorts from broadcast state. Checkpoint every 60 s.
5. **`readings.late` side output** → the backfill consumer, an hour behind, upserting rows marked `backfilled`.
6. **ClickHouse** — raw `ORDER BY (device_id, event_ts)` for 30 days; cohort-minute rollups upserted by window key; per-meter hourly as a materialized view.
7. **Cohort dimension** — feeder, region, campaign snapshot — as broadcast state, from Postgres by CDC.
8. **Query API** — `/rollups` for the map; `/delta` with **coverage** and `late_excluded` on every answer.
9. **Retention, said as one sentence:** raw 30 d, per-meter hourly 2 y, cohort minutes 10 y.
10. In the margin: watermark lag, `late_excluded`, `shed_readings`, coverage — and *"an outbox on a meter is the billing page's answer to a question this page doesn't have."*

---

## 15 · Variants — what actually changes

**The governing axis: what a lost or late event costs — from a rounding error in an aggregate to a dollar that is gone.** Everything else on the page — gateways, a partitioned log, event-time windows, a columnar store with tiers — is the same in every row. What moves is how much exactly-once machinery the cost of a loss buys, and, secondarily, whether the query is per-source or across sources.

| Product | What a lost or late event costs | Query shape | The delta from this page |
|---|---|---|---|
| **Smart-meter telemetry** — this page | A rounding error in a feeder's load; a coverage figure on a delta | Cross-source, by cohort and window | As written. Loss counted, not prevented; membership at rollup time; retention in three numbers |
| **Fleet GPS / telematics** | A gap in one vehicle's track; a stale "where is it now" | **Per-source dominates**: latest position per vehicle, one vehicle's track | §9's cohort rollups shrink to a per-region count; **a latest-position KV (Redis, `vehicle_id → (lat, lon, ts)`) joins the design**, updated per reading. Per-source *ordering* matters more than lateness — a late point must not move the marker backwards, so the KV write is conditional on `ts` |
| **Industrial IoT sensors** | A missed threshold crossing — a real cost, so loss budget tightens to ~0 for alert-bearing channels | Per-source, high frequency (100 Hz–kHz), thousands of sources not millions | Fewer keys, more readings per key: window state is small, per-partition throughput is the constraint. **Threshold alerting joins the stream as stateful rules** (§8's job gains a second output), and a dual path appears — alert channels at-least-once with dedupe, everything else lossy |
| **App analytics events** | A miscounted funnel step; a missing purchase event is *money-adjacent* and gets a dedupe window | Cross-source, by cohort and session | Events, not samples: **no `seq` per source**, so dedupe is by event id; **sessionization** replaces fixed windows (a session window with a 30-minute gap); lateness is *hours* — offline mobile clients — so the live/backfill split (§11) becomes the main path and allowed lateness is measured in days of state on a much smaller key space |
| **Metrics pipelines** — Prometheus, Datadog | A gap in a graph | Per-series, by time; cardinality is the enemy | Pull replaces push for the in-cluster case; **cardinality control replaces partition math** as the sizing problem (a label with 10 M values *is* this page); downsampling is the entire product, and it happens at ingest by resolution tier rather than as a view |
| **Usage metering & billing** — the billing page | **Money.** A lost event is revenue; a duplicated one is a refund | Per-org sum, exact | The inverse row. The same firehose buys an **outbox at the origin, a dedupe window the length of the replay window, a ledger with unique constraints, and a three-way reconciliation** — every box this page deliberately does not have, each justified by the first column |

**The lesson:** the boxes are the same in every row; the *cost of a loss* decides which of them are allowed to be lossy, and that decision is made once, out loud, before the first box is drawn. Say what a dropped event costs in the first minute, and the rest of the page is arithmetic.
