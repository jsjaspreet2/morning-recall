import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# ---------------------------------------------------------------- architecture
a = Board(640, "Demand response architecture. Control plane: a campaign API with the safety checks, Postgres holding campaigns, stages and approvals, and a stage worker that leases a stage and publishes it once. Fanout: a tiny Kafka commands topic consumed by two hundred gateways that evaluate the predicate locally against cached device attributes and hold a sixty-second ack timer per delivery. Device edge: devices that persist the last campaign id in flash and apply only higher ids, and the meter whose readings go to the telemetry page. Receive side: device events keyed by device into Kafka, then ClickHouse partitioned by campaign, with the funnel as a materialized view; a deadline sweeper that runs once per campaign and reads the meter delta for silent devices.")
a.banner("Idempotency lives on the device, so there is no outbox; the predicate is evaluated at the edge, so there is no registry lookup.")

a.group(20, 86, 300, 250, "CONTROL PLANE — 3 MB, THREE MINUTES")
a.box(36, 118, 268, 56, "Campaign API", ["dry run · max delta · oscillation guard", "two-person approval above 100 MW"])
a.cyl(36, 190, 268, 56, "Postgres", ["campaigns · stages · approvals", "monotonic id · deadline index"])
a.box(36, 262, 268, 56, "Stage worker", ["FOR UPDATE SKIP LOCKED · 1 → 10 → 100 %", "hold 5 min · abort on thresholds"])
a.arrow((170, 174), (170, 190)); a.arrow((170, 246), (170, 262))

a.group(350, 86, 280, 250, "FANOUT")
a.queue(366, 118, 248, 56, "Kafka commands", ["1 message per stage · 200 consumers"])
a.arrow((304, 290), (336, 290), (336, 146), (366, 146))
a.ctext(336, 138, "1 msg", 'dg-lbl')
a.box(366, 198, 248, 110, "Gateways ×200",
      ["50 k sockets · attrs cached at HELLO", "evaluate predicate + stage hash locally",
       "60 s ack timer per delivery", "active campaign list, from Postgres"])
a.arrow((490, 174), (490, 198))

a.group(660, 86, 320, 250, "DEVICE EDGE")
a.box(676, 118, 288, 96, "Device",
      ["flash: last_seen_campaign_id · setpoint", "applies only id > last_seen · respects deadline",
       "HELLO {attrs, last_seen} on reconnect"])
a.arrow((614, 240), (640, 240), (640, 150), (676, 150))
a.text(646, 205, "CMD", 'dg-lbl')
a.arrow((676, 190), (650, 190), (650, 280), (614, 280))
a.ctext(632, 298, "ACK", 'dg-lbl')
a.cyl(676, 240, 288, 56, "Meter", ["1 M readings/s → the telemetry page", "/delta with coverage"])

a.queue(350, 380, 280, 56, "Kafka device_events", ["key device_id · 200 partitions · RF 3"])
a.arrow((490, 308), (490, 380))
a.text(500, 350, "delivered · acked · rejected · timed_out · executed", 'dg-lbl')
a.cyl(350, 470, 280, 90, "ClickHouse",
      ["device_events · PARTITION BY campaign", "campaign_targets · bulk insert", "funnel = materialized view, uniq()"])
a.arrow((490, 436), (490, 470))
a.box(660, 470, 300, 90, "Deadline sweeper + inference",
      ["targets − reported → unreachable", "delivered, no successor → timed_out", "timed_out + meter delta → executed_silently"])
a.arrow((630, 515), (660, 515))
a.ctext(645, 462, "once, at deadline", 'dg-lbl')
a.arrow((820, 296), (820, 470))
a.text(828, 400, "/delta per silent device", 'dg-lbl')
a.box(36, 470, 280, 56, "GET /campaigns/{id}/funnel", ["≤ 30 s stale during · exact after the sweep"])
a.arrow((350, 498), (316, 498))

a.text(20, 600, "The per-pair state is not stored: it is the latest event in the log. A Redis hash per campaign would be a ten-million-field key on one shard.", 'dg-s')
a.text(20, 622, "Time on the board is proportional to load: the control plane is three megabytes and gets three minutes; the fanout, the events, and the meter get the rest.", 'dg-note')

ARCH_CAP = ("Draw the state machine before any of this, then draw the control plane small. The two arrows to label "
            "are the one leaving the stage worker — one message — and the one leaving the gateways — ten million "
            "pushes with no lookup in between. The registry and the outbox are the boxes this board is missing on "
            "purpose, and saying why they are missing is worth more than drawing either.")

# ---------------------------------------------------------------- flows
b = Board(620, "Demand response high-level design in three lanes. Create: a campaign request passes the safety guards, gets a monotonic id, snapshots its targets in one bulk insert, and a stage worker leases and publishes stage one. Deliver: each gateway evaluates the predicate and the stage hash against its cached attributes; a connected device is pushed the command with a sixty-second timer and moves to delivered, then acked and executed on its replies, or timed out when the timer fires; an offline device is evaluated the same way on its later HELLO, only if the deadline has not passed. Close: once at the deadline, targets minus reported become unreachable, delivered with no successor becomes timed out, timed out with a matching meter delta becomes executed silently, and the funnel becomes exact. A cancel is a new campaign with a higher id on the same path.")
b.banner("Every box owns a transition or it is deleted: the device decides idempotency, the gateway delivery, the sweeper closure.")

b.lane(30, 76, "CREATE — SAFETY BEFORE FANOUT")
b.box(30, 90, 220, 64, "POST /campaigns", ["predicate · command · deadline", "stages 1/10/100 · hold 5 min"])
b.box(280, 90, 240, 64, "max delta · oscillation · approval", ["422 · 409 · wait for a 2nd approver"],
      cls='dg-warn', tcls='dg-warn-t')
b.arrow((250, 122), (280, 122))
b.box(550, 90, 200, 64, "campaign_id = 9871", ["monotonic · immutable", "targets → one bulk insert"],
      cls='dg-good', tcls='dg-good-t')
b.arrow((520, 122), (550, 122))
b.box(780, 90, 200, 64, "stage worker leases stage 1", ["SKIP LOCKED · publish once"])
b.arrow((750, 122), (780, 122))
b.hdiv(176, 20, 980)

b.lane(30, 210, "DELIVER — THE GATEWAY DECIDES, PER CONNECTION")
b.box(30, 224, 300, 64, "gateway: predicate ∧ hash < pct", ["against 50 k cached attribute sets"])
b.box(360, 224, 300, 64, "connected → push CMD, 60 s timer", ["→ delivered"])
b.arrow((330, 256), (360, 256))
b.box(690, 224, 270, 64, "ACK → acked · REPORT → executed", ["idempotent on (campaign, device)"],
      cls='dg-good', tcls='dg-good-t')
b.arrow((660, 256), (690, 256))
b.box(690, 306, 270, 56, "timer fires → timed_out", ["a lost timer closes at the deadline"],
      cls='dg-warn', tcls='dg-warn-t')
b.arrow((640, 288), (640, 334), (690, 334))
b.box(360, 306, 300, 72, "offline → nothing stored", ["HELLO {attrs, last_seen} later → same evaluation", "only if deadline > now"])
b.arrow((180, 288), (180, 342), (360, 342))
b.ctext(270, 336, "not connected", 'dg-lbl')
b.text(30, 396, "Device rule: apply only campaign_id > last_seen (persisted in flash), never past deadline, ascending order if several arrive at once.", 'dg-s')
b.hdiv(412, 20, 980)

b.lane(30, 446, "CLOSE — ONCE, AT THE DEADLINE")
b.box(30, 460, 220, 64, "targets − reported", ["→ unreachable"])
b.box(280, 460, 220, 64, "delivered, no successor", ["→ timed_out"])
b.box(530, 460, 230, 64, "timed_out + meter ≥ 70 %", ["→ executed_silently"])
b.box(790, 460, 170, 64, "funnel exact: true", ["snapshot → campaign row"],
      cls='dg-good', tcls='dg-good-t')
b.arrow((250, 492), (280, 492)); b.arrow((500, 492), (530, 492)); b.arrow((760, 492), (790, 492))
b.box(30, 546, 930, 44, "CANCEL = a new campaign with a higher id, same path, no approval gate, ≤ 10 s — the device applies it because newer wins",
      cls='dg-warn', tcls='dg-warn-t')
b.text(30, 610, "A late ACK after the sweep is recorded as acked_late; the terminal state and the filed funnel do not change.", 'dg-note')

HLD_CAP = ("Read the middle lane left to right and notice what is absent: no lookup, no queue per device, no "
           "retry loop. The offline branch is the reconnect hook, and it is a computation over one integer the "
           "device brought with it. The bottom lane is what “reconcile late or missing reports” means — three "
           "queries, once, and then the number is exact.")

# ---------------------------------------------------------------- skeleton
s = Board(450, "Demand response five-minute skeleton. The per-target state machine across the top; then Postgres campaigns, the single publish to two hundred gateways, and the gateway with its timer; then the device with its persisted id, the HELLO reconnect hook, and the event log in ClickHouse; then the deadline sweeper and the safety strip; and a margin lane with the funnel ratios, delivery lag, connection counts, and the honest NFR.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 930, 44, "pending → delivered → acked | rejected → executed → measured    ·    terminals: timed_out · unreachable · executed_silently · cancelled",
      cls='dg-good', tcls='dg-good-t', badge=1)
s.box(30, 132, 300, 56, "Campaigns — Postgres", ["immutable · monotonic id · 3 MB — three minutes"], badge=2)
s.box(350, 132, 300, 56, "Kafka commands → 200 gateways", ["200 messages, not 10 M lookups"], badge=3)
s.box(670, 132, 290, 56, "Gateway", ["50 k sockets · attrs at HELLO · 60 s timer"], badge=4)
s.box(30, 208, 300, 56, "Device", ["flash last_seen_campaign_id → no outbox"], badge=5)
s.box(350, 208, 300, 56, "HELLO {attrs, last_seen}", ["retries are a reconnect hook · deadline = TTL"], badge=6)
s.box(670, 208, 290, 56, "device_events → ClickHouse", ["keyed device, partitioned campaign · funnel = MV"], badge=7)
s.box(30, 284, 460, 56, "Deadline sweeper, once", ["targets − reported → unreachable · timed_out → meter → executed_silently"], badge=8)
s.box(510, 284, 450, 56, "Safety strip", ["max Δ · staged+abort · cancel=new id · dry run · rate limit · 2-person · settle"],
      cls='dg-good', tcls='dg-good-t', badge=9)
s.lane(30, 370, "IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 382, 220, 44, "funnel as ratios", ["delivered/targeted · acked/delivered …"], badge=10)
s.box(270, 382, 220, 44, "delivery lag p99", ["the reconnect tail"])
s.box(510, 382, 220, 44, "gateway connection counts", ["a drop is a coverage warning"])
s.box(750, 382, 210, 44, "the honest NFR", ["< 1 s · ≤ 30 s · 60 s"])

SKEL_CAP = ("Badge 1 goes on the board before any box, and every box after it has to point at a transition on "
            "it. Badge 2 gets three minutes. Badge 9 is the strip that went to zero in the reviewed mock — "
            "seven items, recited, each with a number.")

PAGE = 'design-demand-response.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
