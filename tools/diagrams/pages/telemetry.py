import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# ---------------------------------------------------------------- architecture
a = Board(630, "Smart-meter telemetry architecture. Device edge: ten million meters with a flash buffer, and two hundred stateless MQTT gateways that batch into Kafka and sample backlog under pressure. Bus: a readings topic keyed by device id with two hundred partitions. Stream: Flink with event-time windows, a watermark, allowed lateness and dedupe, fed by a broadcast cohort dimension from Postgres, checkpointing to S3. A late-readings topic with its own backfill consumer. Store: ClickHouse raw, a per-meter hourly materialized view and cohort rollups, behind a query API that reports coverage on every delta.")
a.banner("Loss is a metric, not revenue: no outbox anywhere, and every dropped reading is counted.")

a.group(20, 86, 230, 220, "DEVICE EDGE")
a.box(36, 118, 198, 64, "10 M meters", ["1 reading / 10 s · ~100 B", "flash buffer · live first"])
a.box(36, 200, 198, 96, "MQTT gateways ×200",
      ["50 k sockets each · stateless", "batch: linger 200 ms · zstd", "sample backlog, count it"])
a.arrow((135, 182), (135, 200))

a.group(270, 86, 240, 220, "BUS")
a.queue(286, 118, 208, 72, "Kafka readings", ["device_id · 200 partitions", "RF 3 · acks=all · 7 days"])
a.arrow((234, 248), (258, 248), (258, 154), (286, 154))
a.ctext(258, 140, "1 M/s", 'dg-lbl')
a.text(296, 230, "PUBACK to the meter only", 'dg-s')
a.text(296, 246, "after acks=all — the meter", 'dg-s')
a.text(296, 262, "deletes its buffer on ack", 'dg-s')

a.group(540, 86, 440, 220, "STREAM")
a.box(556, 118, 200, 96, "Flink — event time",
      ["1-min windows · watermark −20 s", "allowed lateness 30 s", "dedupe (device_id, seq)"])
a.arrow((494, 154), (556, 154))
a.ctext(525, 146, "200 tasks", 'dg-lbl')
a.box(776, 118, 188, 64, "Broadcast cohorts", ["feeder · region · campaigns", "300 MB / task"])
a.arrow((776, 150), (756, 150))
a.cyl(776, 206, 188, 44, "Postgres device dim")
a.arrow((870, 206), (870, 182))
a.text(880, 200, "CDC, hourly", 'dg-lbl')
a.cyl(776, 262, 188, 40, "S3 checkpoints")
a.arrow((700, 214), (700, 282), (776, 282))
a.text(706, 276, "every 60 s", 'dg-lbl')

# late path: Flink -> readings.late (row 2) -> backfill consumer -> raw
a.arrow((556, 190), (530, 190), (530, 330), (136, 330), (136, 392))
a.text(300, 324, "beyond lateness → side output, counted", 'dg-lbl')
a.queue(36, 392, 200, 60, "Kafka readings.late", ["side output · 24 h"])
a.box(266, 392, 170, 60, "Backfill consumer", ["hourly · backfilled=1"])
a.arrow((236, 422), (266, 422))
a.arrow((436, 422), (480, 422))
a.ctext(458, 440, "is_late", 'dg-lbl')

a.group(464, 360, 516, 120, "STORE — ClickHouse")
a.cyl(480, 392, 150, 72, "raw", ["ORDER BY (device_id, ts)", "TTL 30 d"])
a.cyl(652, 392, 146, 72, "per-meter hourly", ["materialized view", "2 y"])
a.cyl(818, 392, 150, 72, "cohort rollups", ["upsert by window key", "10 y"])
a.arrow((630, 428), (652, 428))
a.line((656, 214), (656, 340)); a.line((560, 340), (893, 340))
a.arrow((560, 340), (560, 392)); a.arrow((893, 340), (893, 392))
a.ctext(610, 334, "batched inserts", 'dg-lbl')

a.box(652, 500, 316, 60, "Query API — /rollups · /delta with coverage", ["→ the operator map · the Demand response page"])
a.arrow((893, 464), (893, 500))

a.text(20, 586, "The live path never waits for the late path: readings.late has its own consumer group, an hour behind, and its rollups are marked backfilled.", 'dg-s')
a.text(20, 608, "An outbox on a meter is the billing page's answer to a question this page does not have — a lost reading is a counted metric, not revenue.", 'dg-note')

ARCH_CAP = ("Draw the source line with its arithmetic before any box — ten million meters, one reading every ten "
            "seconds, a million a second, lossy. Every box after it is cheaper than the billing page's because of "
            "that last word, and the late-readings topic is the one box people forget: it is what keeps a basement "
            "meter's hour of backlog out of the live watermark.")

# ---------------------------------------------------------------- flows
b = Board(600, "Smart-meter telemetry high-level design in three lanes. Gateway: a reading arrives; if the producer buffer is over seventy percent, live readings are always forwarded and backlog is sampled one in k with a shed counter. Stream processor: the watermark is max event time minus twenty seconds; a reading within thirty seconds of allowed lateness enters an event-time window that fires when the watermark passes and upserts by window key; a later reading goes to the late topic, is counted, and is recomputed hourly by the backfill consumer. Query: a delta request reads two rollup rows and returns the delta with coverage and the late-excluded count.")
b.banner("Event time decides the window; the watermark decides when it fires; the lateness number decides what it costs.")

b.lane(30, 76, "GATEWAY — WHERE BACKPRESSURE ACTS")
b.box(30, 90, 200, 72, "Reading arrives", ["MQTT QoS 1 · batched", "event_ts, seq from the meter"])
b.box(260, 90, 220, 72, "producer buffer > 70 %?", ["one open batch per partition", "linger 200 ms · 64 KB"],
      cls='dg-warn', tcls='dg-warn-t')
b.arrow((230, 126), (260, 126))
b.box(510, 90, 220, 72, "live → always forwarded", ["event_ts ≈ now", "the map recovers first"],
      cls='dg-good', tcls='dg-good-t')
b.box(760, 90, 220, 72, "backlog → sample 1-in-k", ["shed_readings++", "never disconnect the meter"],
      cls='dg-warn', tcls='dg-warn-t')
b.arrow((480, 126), (510, 126)); b.ctext(495, 118, "no", 'dg-lbl')
b.arrow((370, 162), (370, 176), (870, 176), (870, 162)); b.ctext(620, 172, "yes, and event_ts is old", 'dg-lbl')
b.hdiv(196, 20, 980)

b.lane(30, 230, "STREAM PROCESSOR — WHERE TIME IS DECIDED")
b.box(30, 244, 300, 64, "watermark = max(event_ts) − 20 s", ["per partition · idle after 60 s"])
b.box(360, 244, 280, 64, "event_ts ≥ watermark − 30 s ?", ["allowed lateness: a chosen number"],
      cls='dg-warn', tcls='dg-warn-t')
b.arrow((330, 276), (360, 276))
b.box(670, 244, 290, 64, "event-time window, per cohort", ["feeder · region · campaign"],
      cls='dg-good', tcls='dg-good-t')
b.arrow((640, 276), (670, 276)); b.ctext(655, 268, "yes", 'dg-lbl')
b.box(670, 330, 290, 90, "fires when watermark > window_end",
      ["stays open 30 s more, re-fires on a late row", "upsert by (cohort, 1m, window_start)", "a re-fired window overwrites itself"],
      cls='dg-good', tcls='dg-good-t')
b.arrow((815, 308), (815, 330))
b.box(360, 330, 280, 72, "late → readings.late", ["late_excluded++ · late_by_s", "never touches an open window"],
      cls='dg-warn', tcls='dg-warn-t')
b.arrow((500, 308), (500, 330)); b.ctext(520, 322, "no", 'dg-lbl')
b.box(30, 330, 300, 72, "backfill consumer, hourly", ["raw rows with is_late=1", "touched rollups → backfilled=1"])
b.arrow((360, 366), (330, 366))
b.hdiv(440, 20, 980)

b.lane(30, 474, "QUERY — WHERE COVERAGE IS REPORTED")
b.box(30, 488, 300, 64, "/delta?cohort=campaign:987&t=T", ["window=5m"])
b.box(360, 488, 280, 64, "two rollup reads", ["[T−5m, T) and [T, T+5m)", "no raw scan"])
b.arrow((330, 520), (360, 520))
b.box(670, 488, 290, 64, "delta_kw · coverage 0.962", ["late_excluded: 4 811", "distinct meters / cohort size"],
      cls='dg-good', tcls='dg-good-t')
b.arrow((640, 520), (670, 520))
b.text(30, 580, "A restart restores state and offsets from one checkpoint, so replayed windows re-fire with the same keys — the watermark makes a replay produce the live run's answer.", 'dg-note')

HLD_CAP = ("The lane in the middle is the whole argument. Say the watermark formula, then say the lateness number, "
           "then say what falls outside it goes to its own topic — and only then draw the store. A candidate who "
           "draws Kafka → Flink → ClickHouse and never says thirty seconds has drawn a category, not a design.")

# ---------------------------------------------------------------- skeleton
s = Board(450, "Smart-meter telemetry five-minute skeleton. The source line with its arithmetic across the top; then gateways, the readings topic and the event-time processor; then the late path, ClickHouse and the cohort dimension; then the query API and the retention sentence; and a margin lane of the signals and the sentence about the outbox.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 930, 44, "10 M meters × 1 / 10 s = 1 M/s · ~100 B each · lossy OK — write “loss is a metric” before any box",
      cls='dg-good', tcls='dg-good-t', badge=1)
s.box(30, 128, 300, 64, "MQTT gateways", ["200 × 50 k · linger 200 ms · PUBACK after acks=all", "sample backlog, count it"], badge=2)
s.box(350, 128, 300, 64, "Kafka readings", ["key device_id · 200 partitions · RF 3 · 7 d", "per-meter order; the count is fixed"], badge=3)
s.box(670, 128, 290, 64, "Flink — event time", ["watermark −20 s · lateness 30 s", "dedupe (device_id, seq) · ckpt 60 s"], badge=4)
s.box(30, 208, 300, 56, "readings.late → backfill", ["an hour behind · rows marked backfilled"], badge=5)
s.box(350, 208, 300, 56, "ClickHouse", ["raw 30 d · cohort rollups · per-meter hourly MV"], badge=6)
s.box(670, 208, 290, 56, "Cohort dimension", ["feeder · region · campaign snapshot → broadcast"], badge=7)
s.box(30, 284, 300, 56, "Query API", ["/rollups · /delta with coverage + late_excluded"], badge=8)
s.box(350, 284, 610, 56, "Retention, in one sentence", ["raw 30 d · per-meter hourly 2 y · cohort minutes 10 y"],
      cls='dg-good', tcls='dg-good-t', badge=9)
s.lane(30, 370, "IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 382, 220, 44, "watermark lag", ["now − watermark, per partition"], badge=10)
s.box(270, 382, 220, 44, "late_excluded · shed", ["the loss budget, spent visibly"])
s.box(510, 382, 220, 44, "coverage on every delta", ["a number without it is a guess"])
s.box(750, 382, 210, 44, "no outbox here", ["that's the billing page"])

SKEL_CAP = ("Badge 1 is a line of arithmetic, not a box, and it goes on the board first. Badge 9 is a sentence — "
            "three numbers — and it is the one the reviewed mock left unsaid. Everything between them is the "
            "same three boxes every telemetry design has; the badges are what make this one a design.")

PAGE = 'design-telemetry.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
