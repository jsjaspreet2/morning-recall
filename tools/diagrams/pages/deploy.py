import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# ---------------------------------------------------------------- architecture
a = Board(620, "Deployment system architecture. Engineers call an API with three verbs that writes desired state into Postgres: services, deployments, stages, allocations and the host inventory. A stateless, leader-leased control plane runs a reconciler tick that computes the gap between desired and observed state and claims host capacity with a per-host conditional update, one stage at a time; a rollout controller that walks stages with a bake and a gate checked before advancing; and a sweeper that turns Redis TTL expiries into LOST transitions under a disruption budget. A hundred and fifty thousand host agents heartbeat once per host every ten seconds to a heartbeat API sharded by host id, which stores liveness in Redis Cluster with a thirty-second TTL and returns the host's desired allocations on the reply. Agents pull artifacts by digest through a rack cache, run the readiness probe locally, and keep their state in SQLite. Healthy allocations are materialised into a discovery table every fifteen seconds; the metrics platform answers the gate query by deployment id.")
a.banner("Desired state is a row and observed state is a heartbeat; the loop closes the gap forever, and a rollout is one more gap.")

a.group(20, 86, 230, 110, "SUBMIT")
a.box(36, 118, 200, 64, "API — three verbs", ["PUT /services · POST /deployments", "abort → a rollback deployment id"])

a.group(270, 86, 410, 206, "CONTROL PLANE — STATELESS, LEADER-LEASED")
a.box(286, 118, 180, 80, "Reconciler tick, 5 s", ["gap = desired − observed", "per-host CAS claim, per stage", "drain oldest digest first"])
a.box(486, 118, 178, 80, "Rollout controller", ["stage → bake → gate", "gate checked before advancing", "abort = a new deployment"])
a.box(286, 214, 378, 72, "Sweeper — TTL expiry → LOST",
      ["capacity freed · grace 2 × interval after a restart", "disruption budget: ≤ 1 % of a service per minute"],
      cls='dg-good', tcls='dg-good-t')

a.cyl(710, 118, 270, 168, "Postgres — desired + transitions",
      ["services · deployments · stages", "allocations (service_id, digest, state)",
       "hosts (pool, az, cpu_free, mem_free)", "transitions only · leader lease row"])
a.arrow((136, 118), (136, 72), (845, 72), (845, 118))
a.ctext(490, 66, "rows, committed before the 201", 'dg-lbl')
a.arrow((664, 150), (710, 150)); a.arrow((664, 250), (710, 250))

a.group(20, 320, 330, 150, "HEALTH PLANE")
a.cyl(36, 352, 140, 100, "Redis Cluster", ["host:{id} TTL 30 s", "instance hash per host", "sharded by host_id"])
a.box(196, 352, 150, 100, "Heartbeat API ×16", ["by hash(host_id) → Redis", "15 k beats/s", "reply = desired rows"])
a.arrow((196, 402), (176, 402))
a.arrow((106, 352), (106, 250), (286, 250))
a.text(112, 244, "expiry → LOST transitions", 'dg-lbl')
a.arrow((300, 352), (300, 312), (760, 312), (760, 286))
a.ctext(560, 307, "reads desired · writes transitions only", 'dg-lbl')

a.group(390, 320, 300, 150, "HOSTS ×150 k")
a.box(406, 352, 270, 56, "Agent — one heartbeat / 10 s",
      ["reply = desired · pull digest · probe locally", "SQLite state · runs with no control plane"])
a.box(406, 420, 270, 40, "The service", ["/ready: model loaded, deps reachable"], cls='dg-warn', tcls='dg-warn-t')
a.arrow((406, 372), (346, 372)); a.ctext(376, 364, "heartbeat", 'dg-lbl')
a.arrow((346, 400), (406, 400)); a.ctext(376, 414, "desired", 'dg-lbl')

a.cyl(710, 320, 270, 60, "Discovery table — the tier, an output", ["HEALTHY allocations → host:port · 15 s"])
a.arrow((930, 286), (930, 320))
a.cyl(710, 392, 270, 60, "Object storage + rack cache / P2P", ["content-addressed · last two digests pinned"])
a.arrow((676, 380), (692, 380), (692, 422), (710, 422))
a.text(712, 466, "pull by digest — push scales with the pusher", 'dg-lbl')
a.box(710, 474, 270, 50, "Metrics platform", ["error rate · p99 by deployment_id", "queried at the gate, not stored here"])

a.text(20, 546, "Heartbeats never touch Postgres: liveness is a TTL, and only transitions are rows. Losing Redis is blindness, never a wrong replacement.", 'dg-s')
a.text(20, 568, "No queue and no outbox: the row is the message, and the agent asks for it every ten seconds. A restarted controller says nothing new.", 'dg-s')
a.text(20, 590, "A host death at 03:00 and a release at 15:00 are the same gap. The tier is what falls out; it is never what you deploy to.", 'dg-note')

ARCH_CAP = ("Draw the two state machines first, then this. The heartbeat and its reply are the whole protocol — one message "
            "up per host, desired rows down — and the sweeper's budget line is the number that stops the loop from eating "
            "the fleet on a bad day. Nothing on the board queues anything.")

# ---------------------------------------------------------------- flows
b = Board(580, "Deployment flows in three lanes. Release: the canary stage claims ten hosts by conditional update, bakes thirty minutes, and the gate is checked before advancing through one, ten, fifty and a hundred percent — about six hours, five of them bake; forty hosts that never become healthy are failed by the per-host clock, re-placed, and the stage still passes at ninety-nine point four percent readiness. Host death with no rollout: a heartbeat stops, thirty seconds later the host is dead and its allocations lost with capacity freed, the reconciler sees a gap of one per service and places replacements that are healthy in about three minutes; when the host returns at forty-five seconds the reply lists nothing it should run and it drains everything. Gate failure: error rate up one point eight points aborts the deployment, a new deployment of the previous digest with a single stage rolls back only the seven thousand seven hundred and ten instances that moved in about twenty minutes, and the trap is a previous image the registry garbage-collected.")
b.banner("Claim a stage by CAS, bake, gate before advancing; a dead host is a gap; a failed gate is a deployment of the previous digest.")

b.lane(30, 76, "RELEASE — STAGE, BAKE, GATE BEFORE ADVANCING")
b.box(30, 90, 210, 72, "PENDING → ROLLING(0)", ["canary: 10 hosts", "claim by CAS, this stage only"])
b.box(270, 90, 210, 72, "BAKING(0), 30 min", ["gate checked before advancing", "ready · crash · Δerr · p99"], cls='dg-good', tcls='dg-good-t')
b.arrow((240, 126), (270, 126))
b.box(510, 90, 220, 72, "1 % → 10 % → 50 % → 100 %", ["each: claim → healthy → bake → gate", "≈ 6 h, five of them bake"])
b.arrow((480, 126), (510, 126))
b.box(760, 90, 220, 72, "40 hosts never HEALTHY", ["per-host 10 min → FAILED, re-placed", "99.4 % ≥ 99 % → the stage passes"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((730, 126), (760, 126))
b.text(30, 190, "Never 70 k hosts up front: the 1 % stage claims its 700 thirty minutes after the canary, and a 10-host service places in under five seconds meanwhile.", 'dg-s')
b.hdiv(206, 20, 980)

b.lane(30, 240, "HOST DEATH — NO ROLLOUT RUNNING")
b.box(30, 254, 290, 72, "heartbeat stops, 03:00", ["30 s → host dead · 5 allocations LOST", "capacity freed in the same transaction"])
b.box(350, 254, 290, 72, "gap = 1, in each of 5 services", ["reconciler claims other hosts by CAS", "warm-cache pull → HEALTHY ≈ 3 min"], cls='dg-good', tcls='dg-good-t')
b.arrow((320, 290), (350, 290))
b.box(670, 254, 290, 72, "the host returns at 03:00:45", ["reply lists nothing it should run → drains all", "a minute of 30 where 25 were wanted"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((640, 290), (670, 290))
b.text(30, 350, "Over-replacement for a minute is the price of a 30-second threshold. The other price — minutes under-replicated on a real death — is worse, and the budget caps the blip case.", 'dg-s')
b.hdiv(366, 20, 980)

b.lane(30, 400, "GATE FAILS — ROLLBACK IS A DEPLOYMENT")
b.box(30, 414, 220, 64, "10 % bake: err +1.8 pp", ["threshold 0.5 → ABORTED", "gate_result written, kept"])
b.box(270, 414, 230, 64, "new deployment: prev_digest", ["stages [100] · bake 0", "still batched · still probed"], cls='dg-good', tcls='dg-good-t')
b.arrow((250, 446), (270, 446))
b.box(520, 414, 220, 64, "7 710 roll back ≈ 20 min", ["62 290 on v1 untouched", "only what moved moves back"])
b.arrow((500, 446), (520, 446))
b.box(760, 414, 220, 64, "v1 image GC'd from the registry", ["stalls in PULLING, clocks fail it", "pin the last two digests"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((740, 446), (760, 446))
b.text(30, 520, "Rollback is not a code path that runs only during incidents. It is a row with the digests swapped, through the same machinery that just proved itself.", 'dg-note')

HLD_CAP = ("The top lane's third box is where the clock goes — six hours, five of them waiting — and its fourth is why "
           "a per-host timeout has an owner. The middle lane is the requirement the mock did not hear, and the bottom "
           "lane's mechanism is a row, not a runbook.")

# ---------------------------------------------------------------- skeleton
s = Board(450, "Deployment system five-minute skeleton. Both state machines across the top; then the three-verb API, Postgres with its two indexes, and the stateless leased controller; then the health plane, the agent, and the gate numbers; then rollback as a deployment and the discovery table as an output; and a margin lane of the durations and the decoy.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 930, 44, "Deployment: PENDING → ROLLING(n) → BAKING(n) → … → SUCCEEDED · PAUSED · ABORTED → rollback deployment · SUPERSEDED",
      ["Instance: ALLOCATED → PULLING → STARTING → HEALTHY → DRAINING → STOPPED · FAILED · LOST — every transition a CAS on version"],
      cls='dg-good', tcls='dg-good-t', badge=1)
s.box(30, 128, 300, 64, "API — three verbs", ["PUT /services · POST /deployments · abort", "replicas + resources, never a host list"], badge=2)
s.box(350, 128, 300, 64, "Postgres — desired + transitions", ["allocations (service_id, digest, state)", "hosts (pool, az, cpu_free, mem_free) · no beats"], badge=3)
s.box(670, 128, 290, 64, "Controller — stateless, leased", ["tick 5 s: gap = desired − observed", "per-host CAS per stage · gate before advance"], badge=4)
s.box(30, 208, 300, 56, "Health plane", ["Redis TTL 30 s → sweeper → LOST · budget 1 %/min"], badge=5)
s.box(350, 208, 300, 56, "Agent ×150 k", ["beat / 10 s · reply = desired · SQLite · pull"], badge=6)
s.box(670, 208, 290, 56, "The gate, before advancing", ["ready ≥ 99 % · crash 0 · err +0.5 pp · p99 1.2 ×"], badge=7)
s.box(30, 284, 300, 56, "Rollback = a deployment", ["prev_digest · stages [100] · no bake · batched"], badge=8)
s.box(350, 284, 300, 56, "Discovery table — an output", ["HEALTHY allocations → host:port · 15 s"], badge=9)
s.box(670, 284, 290, 56, "no_traffic gate", ["readiness + crash-loops + a synthetic request"])
s.lane(30, 370, "10 · IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 382, 220, 44, "no whole-rollout timeout", ["every duration has an owner"])
s.box(270, 382, 220, 44, "per-host 10 min", ["per-stage max(30 min, 2 × expected)"])
s.box(510, 382, 220, 44, "surge 10 % · unavailable 5 %", ["pin the last two digests"])
s.box(740, 382, 220, 44, "15 a day is a decoy", ["150 k hosts is the load"])

SKEL_CAP = ("Badge 1 before any box, badge 4 before the API is finished. Badge 2's second line is the sentence the "
            "mock lost ten minutes to — say it before the interviewer has to — and the margin's first tile is the "
            "timeout you refuse to write, with the two you write instead.")

PAGE = 'design-deployment.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
