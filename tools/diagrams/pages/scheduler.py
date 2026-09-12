import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# ---------------------------------------------------------------- architecture
a = Board(620, "Job scheduler architecture. Submitters call an API that writes job rows, edges and schedules into Postgres, partitioned by day with a claim index. Stateless scheduler nodes run dispatchers that serve worker claims with SKIP LOCKED, a lease sweeper on lease expiry, and one leader elected by a database lease that fires cron ticks as unique inserts. Fifty thousand workers long-poll for claims, heartbeat once per worker every ten seconds and receive preempt and cancel instructions on the reply, and report completions with their attempt number as a fencing token. Worker liveness is a Redis key with a TTL. Payloads, checkpoints and logs live in object storage; terminal jobs are archived to ClickHouse.")
a.banner("The queue is a table and the lease is the mechanism: never lost, never under two leases; the job body makes twice harmless.")

a.group(20, 86, 250, 120, "SUBMIT")
a.box(36, 118, 218, 72, "API", ["POST /jobs · /jobs/batch (DAG)", "Idempotency-Key · cycles → 422"])

a.group(300, 86, 380, 200, "SCHEDULER NODES — STATELESS, ANY NUMBER")
a.box(316, 118, 170, 72, "Dispatcher", ["claim: SKIP LOCKED", "rank: priority · share · age", "fair-share counts in memory"])
a.box(500, 118, 164, 64, "Lease sweeper", ["lease_until < now", "→ RETRY_WAIT · DEAD"])
a.box(500, 196, 164, 64, "Cron leader", ["leader lease, 5 s", "UNIQUE (schedule, tick)"], cls='dg-good', tcls='dg-good-t')

a.cyl(710, 118, 270, 152, "Postgres — jobs", ["partitioned by day", "(class, state, priority, ready_at)", "attempt = the fencing column", "edges · attempts · schedules · leader"])
a.arrow((216, 118), (216, 78), (845, 78), (845, 118))
a.ctext(530, 72, "rows, committed before the 201", 'dg-lbl')
a.arrow((664, 150), (710, 150)); a.arrow((664, 228), (710, 228))

a.group(20, 320, 660, 150, "WORKERS ×50 k")
a.box(36, 356, 300, 100, "Worker daemon",
      ["long-poll claim · one heartbeat / 10 s for all jobs", "complete {attempt} → 409 if stale",
       "buffers completions while the API is down"])
a.box(366, 356, 298, 100, "The job body",
      ["at-least-once from us → idempotent by contract", "side effects keyed on job_id / attempt",
       "checkpoint hook if preemptible"], cls='dg-warn', tcls='dg-warn-t')
a.arrow((186, 356), (186, 300), (400, 300), (400, 190))
a.ctext(300, 294, "claim · heartbeat · complete", 'dg-lbl')
a.arrow((420, 190), (420, 310), (200, 310), (200, 356))
a.ctext(310, 342, "jobs · preempt · cancel", 'dg-lbl')

a.cyl(710, 320, 120, 64, "Redis", ["liveness TTL 30 s"])
a.arrow((336, 444), (350, 444), (350, 464), (700, 464), (700, 352), (710, 352))
a.ctext(700, 312, "heartbeat", 'dg-lbl')
a.cyl(860, 320, 120, 64, "Object storage", ["payloads · logs"])
a.cyl(710, 406, 270, 64, "ClickHouse — archive", ["terminal jobs + attempts · 2 y"])
a.arrow((845, 270), (845, 406))
a.text(855, 300, "terminal rows, hourly", 'dg-lbl')

a.text(20, 510, "Liveness (Redis, cheap, lossy) and the lease (a column, durable) are two things: losing Redis loses nothing but the fast path for detecting deaths.", 'dg-s')
a.text(20, 532, "Dead-letter is a state, not a queue. The leader is a leased job. The DAG is a counter decremented in the parent's commit.", 'dg-s')
a.text(20, 554, "Exactly-once execution is not on offer. At-least-once plus an idempotent job body is, and the attempt number makes the second half one line.", 'dg-note')

ARCH_CAP = ("Draw the state machine first, then this. The two arrows between the workers and the dispatcher are "
            "the whole protocol — claim up, jobs down, and the heartbeat reply carrying preempt and cancel — and the "
            "warning box is the contract the scheduler cannot sign for the job.")

# ---------------------------------------------------------------- flows
b = Board(620, "Job scheduler flows in three lanes. Claim and lease: a worker claims with SKIP LOCKED, the row moves to leased with attempt incremented and a thirty-second lease; heartbeats renew it; a lost heartbeat moves the job to retry-wait and it is re-claimed as the next attempt, while the zombie's late completion is refused with a stale-attempt conflict. Overload: the claim ranks by priority, then fair-share deficit, then aging; a P0 arriving at a full GPU fleet preempts the cheapest checkpointed job within sixty seconds. Cron: the leader fires a tick as a unique insert; a failover fires it late but once; a partitioned old leader hits the unique constraint.")
b.banner("Claim under a lease, renew by heartbeat, fence by attempt; rank by priority then fair-share; fire cron as a unique row.")

b.lane(30, 76, "CLAIM AND LEASE — THE DEAD WORKER IS A RETRY, THE ZOMBIE IS A 409")
b.box(30, 90, 210, 72, "READY → LEASED", ["SKIP LOCKED · attempt + 1", "lease_until = now + 30 s"])
b.box(270, 90, 210, 72, "heartbeat every 10 s", ["one per worker, all jobs", "reply: preempt · cancel"], cls='dg-good', tcls='dg-good-t')
b.arrow((240, 126), (270, 126))
b.box(510, 90, 220, 72, "no heartbeat 30 s", ["sweeper: → RETRY_WAIT", "re-claimed as attempt 2"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((480, 126), (510, 126))
b.box(760, 90, 220, 72, "zombie completes attempt 1", ["409 stale_attempt", "result discarded, log kept"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((730, 126), (760, 126))
b.text(30, 190, "Attempt 1's side effects already happened. That is the job body's problem, and the contract makes it cheap: key them on job_id.", 'dg-s')
b.hdiv(206, 20, 980)

b.lane(30, 240, "OVERLOAD — 09:00, A MILLION READY JOBS, THE FLEET FULL")
b.box(30, 254, 290, 72, "rank at claim time", ["priority → fair-share deficit (DRF)", "→ aging → ready_at"])
b.box(350, 254, 290, 72, "tenant X: 100 k jobs at P1", ["gets its weighted share, no more", "GET /jobs shows position"])
b.arrow((320, 290), (350, 290))
b.box(670, 254, 290, 72, "P0 GPU job, fleet full", ["preempt cheapest checkpointed P2", "60 s grace → P0 runs < 60 s"], cls='dg-good', tcls='dg-good-t')
b.arrow((640, 290), (670, 290))
b.box(350, 342, 290, 56, "non-preemptible jobs", ["never killed · wait longer to start"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((815, 326), (815, 370), (640, 370))
b.text(30, 424, "The bounds are the design output: P0 < 60 s · P1 < 5 min for any tenant · P3 eventually. “It queues” is not a bound.", 'dg-s')
b.hdiv(440, 20, 980)

b.lane(30, 474, "CRON — ONCE, ACROSS A FAILOVER")
b.box(30, 488, 290, 64, "leader scans next_tick ≤ now", ["INSERT job UNIQUE (schedule, tick)"])
b.box(350, 488, 290, 64, "leader dies 05:59:58", ["standby takes the lease 06:00:04", "fires the 06:00 tick, 4 s late"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((320, 520), (350, 520))
b.box(670, 488, 290, 64, "old leader wakes 06:00:05", ["same insert → unique violation", "one report, not two"], cls='dg-good', tcls='dg-good-t')
b.arrow((640, 520), (670, 520))
b.text(30, 590, "An hour-long outage: fire_once for the nightly report, late and labelled; skip for the every-minute check. Decided per schedule, before it happens.", 'dg-note')

HLD_CAP = ("The top lane is the whole correctness argument in four boxes; the last one — a 409 — is where most "
           "designs have nothing. The middle lane turns “it queues” into three numbers, and the bottom lane's "
           "mechanism is a unique constraint, not the leader.")

# ---------------------------------------------------------------- skeleton
s = Board(450, "Job scheduler five-minute skeleton. The per-job state machine across the top; then the Postgres queue table, the claim and heartbeat, and the fencing token; then the exactly-once split, liveness versus lease, and the overload rank with its bounds; then preemption and gang scheduling, DAGs as counters, and cron; and a margin lane of the signals.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 930, 44, "PENDING → READY → LEASED → RUNNING → SUCCEEDED · RETRY_WAIT loops · FAILED · DEAD · CANCELLED · PREEMPTED → READY · CAS on state + attempt",
      cls='dg-good', tcls='dg-good-t', badge=1)
s.box(30, 128, 300, 64, "Jobs — Postgres", ["by day · index (class, state, priority, ready_at)", "the queue is a table; SKIP LOCKED makes it one"], badge=2)
s.box(350, 128, 300, 64, "Claim + heartbeat", ["lease 30 s · attempt + 1 · one heartbeat per worker", "reply carries preempt · cancel"], badge=3)
s.box(670, 128, 290, 64, "Fencing token", ["attempt on every worker call · stale → 409", "the zombie's result never lands"], badge=4)
s.box(30, 208, 300, 56, "The honest split", ["at-least-once + idempotent body = exactly-once"], badge=5)
s.box(350, 208, 300, 56, "Liveness vs lease", ["Redis TTL for deaths · lease_until index as backstop"], badge=6)
s.box(670, 208, 290, 56, "Overload rank + bounds", ["priority → share → aging · P0 < 60 s, P1 < 5 min"], badge=7)
s.box(30, 284, 300, 56, "Preemption · gang", ["opt-in · checkpointed · cheapest-first · gang"], badge=8)
s.box(350, 284, 300, 56, "DAGs as counters", ["deps_unmet −1 in the parent's commit · failed: never"], badge=9)
s.box(670, 284, 290, 56, "Cron", ["lease + UNIQUE (schedule, tick) + missed_policy"], badge=10)
s.lane(30, 370, "IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 382, 220, 44, "oldest ready age", ["per class and priority"])
s.box(270, 382, 220, 44, "lost-lease rate", ["platform failing vs jobs failing"])
s.box(510, 382, 220, 44, "DEAD inflow · cron lag", ["with an owner"])
s.box(740, 382, 220, 44, "the scheduler is a leased job", ["same mechanism"])

SKEL_CAP = ("Badge 1 before the queue, badge 4 before the worker. Badge 5 is the sentence the round is fishing "
            "for — say it before the interviewer asks what exactly-once means here — and badge 7's two numbers are "
            "what “it queues” has to become.")

PAGE = 'design-scheduler.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
