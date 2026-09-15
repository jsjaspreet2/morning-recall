import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# ---------------------------------------------------------------- architecture
a = Board(600, "CI/CD pipeline architecture. A push event from the git host creates a run in Postgres and supersedes the previous run on the same ref in the same transaction. A resolver turns the pipeline definition at that commit into about two hundred steps with dependency counters, and every step's cache key is looked up in a Redis index before anything is scheduled; hits are marked cached and never lease. A stateless, leader-leased scheduler grants leases to ready steps by skip-locked select, decrements dependants on completion, answers heartbeats with continue or cancel, and sweeps expired leases. About six thousand ephemeral microVM runners at nine in the morning poll for leases, fetch inputs by digest from S3, execute one step each, stream logs to a short-lived stream and then to S3, and are destroyed. Only trusted runs write the cache index. A merge queue is the only writer to main and tests speculative batches through the same scheduler. Events flow to Kafka and ClickHouse.")
a.banner("A run is a DAG of counters with an expiry; the cache decides what never runs, and the pool is sized for nine o'clock.")

a.group(20, 86, 230, 110, "TRIGGER")
a.box(36, 118, 200, 64, "Git host web hook", ["POST /runs { repo, sha, ref }", "supersedes the old run, same txn"])

a.group(270, 86, 410, 206, "SCHEDULER — STATELESS, LEADER-LEASED")
a.box(286, 118, 180, 80, "Resolver → counters", ["~200 steps · deps_remaining", "cache_key per step, up front", "hits → CACHED, never lease"])
a.box(486, 118, 178, 80, "Lease + complete", ["SKIP LOCKED grant · token", "run superseded? → skip", "decrement dependants"])
a.box(286, 214, 378, 72, "Heartbeat reply · sweeper · fair share",
      ["continue | cancel — the only downward channel", "3 missed beats → re-queue once · fair share when queued"],
      cls='dg-good', tcls='dg-good-t')

a.cyl(710, 118, 270, 168, "Postgres — runs, steps, edges, queue",
      ["steps (run_id, state) · deps_remaining", "lease_token · version · attempt",
       "merge_queue (repo, position)", "partitioned by month · leader lease row"])
a.arrow((136, 118), (136, 72), (845, 72), (845, 118))
a.ctext(490, 66, "run + SUPERSEDED, one transaction", 'dg-lbl')
a.arrow((664, 150), (710, 150)); a.arrow((664, 250), (710, 250))

a.group(20, 320, 330, 150, "CACHE — THE PRODUCT")
a.cyl(36, 352, 140, 100, "Redis index", ["cache_key → digest", "LRU 14 d on last_hit", "rebuilt from S3"])
a.cyl(196, 352, 150, 100, "S3 — outputs", ["content-addressed", "refcounted · 30 d GC", "5 TB/day in"])
a.arrow((196, 402), (176, 402))
a.arrow((106, 352), (106, 250), (286, 250))
a.text(112, 244, "resolve keys before scheduling", 'dg-lbl')

a.group(390, 320, 300, 150, "RUNNERS ×6 000 AT 09:00")
a.box(406, 352, 270, 56, "microVM per step — destroyed after",
      ["poll for lease · fetch inputs by digest", "scoped secrets token · egress allow-list"])
a.box(406, 420, 270, 40, "Pool controller", ["boots to yesterday's curve, 30 min ahead"], cls='dg-warn', tcls='dg-warn-t')
a.arrow((406, 372), (346, 372)); a.ctext(376, 364, "write", 'dg-lbl')
a.arrow((346, 400), (406, 400)); a.ctext(376, 414, "read", 'dg-lbl')
a.arrow((540, 352), (540, 312), (760, 312), (760, 286))
a.ctext(650, 307, "lease · heartbeat / 10 s · complete", 'dg-lbl')

a.cyl(710, 320, 270, 60, "Logs — stream 10 min, then S3 90 d", ["2 s batches · key logs/{run}/{step}/{attempt}"])
a.arrow((676, 380), (692, 380), (692, 350), (710, 350))
a.box(710, 392, 270, 60, "Merge queue — only writer to main", ["rows in Postgres · speculative batch 8–16", "bisect on red · a run with trigger: merge_queue"])
a.cyl(710, 464, 270, 50, "Kafka → ClickHouse", ["transitions · flake rate per test · cost"])

a.text(20, 528, "Cancellation is never a message: the run's state is read on every lease and every heartbeat reply, so a dead scheduler loses nothing.", 'dg-s')
a.text(20, 550, "Hits never lease. The cache key is content plus toolchain, never the commit, and only trusted refs may write it.", 'dg-s')
a.text(20, 572, "Five thousand pushes a day is a decoy; a million steps, ten times that at 09:00, and a runner per step is the load.", 'dg-note')

ARCH_CAP = ("Draw the step state machine first, then this. The resolver's second line — keys resolved before anything "
            "schedules — is the cost story, the heartbeat reply is the cancel story, and the merge queue's box is "
            "why green on the branch is not green on main. Nothing on the board keeps a graph in memory.")

# ---------------------------------------------------------------- flows
b = Board(580, "CI/CD flows in three lanes. Second push: a new run is created and the old one superseded in the same transaction; forty ready steps never lease, thirty running steps get cancel on their next heartbeat within ten seconds, and fifty completed outputs are cache hits for the new run; a runner that completes at the same instant is accepted because its token is still valid. The nine o'clock spike: the pool boots from eight hundred to six thousand thirty minutes ahead, queue wait stays under a minute, and when a toolchain release drops the cache hit rate to five percent fair share by team keeps one matrix build from owning the pool while wait rises to eight minutes with a banner. Merge queue: eight pull requests become one speculative commit, green lands all eight; red bisects into halves in parallel, ejects the culprit, and lands the seven innocents at a cost of about thirty minutes.")
b.banner("Supersede in one transaction and cancel on the heartbeat reply; size the pool for 09:00; batch the merge and bisect the red one.")

b.lane(30, 76, "SECOND PUSH — SUPERSESSION RACES THE LEASES")
b.box(30, 90, 210, 72, "POST /runs, push 2", ["run 2 inserted · run 1 SUPERSEDED", "one transaction"])
b.box(270, 90, 210, 72, "40 READY never lease", ["lease grant reads run state", "swept to CANCELLED"], cls='dg-good', tcls='dg-good-t')
b.arrow((240, 126), (270, 126))
b.box(510, 90, 220, 72, "30 RUNNING → cancel ≤ 10 s", ["on the heartbeat reply", "VM destroyed · 50 done = cache hits"])
b.arrow((480, 126), (510, 126))
b.box(760, 90, 220, 72, "one completes at that instant", ["token still valid → accepted", "a correct output, cached"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((730, 126), (760, 126))
b.text(30, 190, "No kill list exists to lose. A scheduler that dies mid-cancel changed nothing, because supersession is a row every lease consults.", 'dg-s')
b.hdiv(206, 20, 980)

b.lane(30, 240, "09:00 — THE POOL, AND THE DAY THE CACHE GOES COLD")
b.box(30, 254, 290, 72, "08:30 · boot ahead of the curve", ["800 → 6 000 microVMs in 30 min", "base image: last night's checkout"])
b.box(350, 254, 290, 72, "09:00–10:00 · 5 200 running", ["queue wait p95 40 s · pool 90 % busy", "drains by disposal after 10:15"], cls='dg-good', tcls='dg-good-t')
b.arrow((320, 290), (350, 290))
b.box(670, 254, 290, 72, "toolchain release: hits 60 % → 5 %", ["demand 2.5 × pool · fair share by team", "wait p95 8 min, with a banner"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((640, 290), (670, 290))
b.text(30, 350, "A pool sized for the average is a forty-minute queue at nine. A pool sized for the peak idles at nine percent. Yesterday's curve, thirty minutes ahead, is the answer.", 'dg-s')
b.hdiv(366, 20, 980)

b.lane(30, 400, "MERGE QUEUE — SPECULATE, THEN BISECT")
b.box(30, 414, 220, 64, "8 PRs click merge", ["one speculative commit:", "main + 1 … + 8"])
b.box(270, 414, 230, 64, "green in 10 min → all 8 land", ["fast-forward main", "48/h at batch 8 · 300/h speculating"], cls='dg-good', tcls='dg-good-t')
b.arrow((250, 446), (270, 446))
b.box(520, 414, 220, 64, "red → bisect in parallel", ["main + 1–4 · main + 5–8", "green half lands"])
b.arrow((500, 446), (520, 446))
b.box(760, 414, 220, 64, "culprit ejected, 7 land", ["≈ 30 min cost to neighbours", "a flake here is a stall"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((740, 446), (760, 446))
b.text(30, 520, "The queue is the only writer to main. That is what turns 'main is green' from a norm into a property of the system.", 'dg-note')

HLD_CAP = ("The top lane's fourth box is the one interviewers probe — a completion under a superseded run is accepted, "
           "and the only refused completion is a stale token. The middle lane is where the pushes-per-day number "
           "dies, and the bottom lane's arithmetic is the throughput of main.")

# ---------------------------------------------------------------- skeleton
s = Board(450, "CI/CD five-minute skeleton. The step and run state machines across the top; then the web hook that supersedes in one transaction, Postgres with counters and skip-locked leases, and the stateless scheduler; then the cache with its content key and trust rule, the microVM runners with the pool controller, and the merge queue; then logs and artifacts, the flake budget, and a margin lane of the decoy and the durations.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 930, 44, "Step: PENDING → READY → LEASED → RUNNING → SUCCEEDED · CACHED · FAILED · TIMED_OUT · CANCELLED — CAS on version, lease_token on complete",
      ["Run: CREATED → RUNNING → SUCCEEDED | FAILED | SUPERSEDED — set by the next run's insert, same transaction"],
      cls='dg-good', tcls='dg-good-t', badge=1)
s.box(30, 128, 300, 64, "Web hook + resolver", ["POST /runs supersedes, one txn", "definition at sha → ~200 steps + edges"], badge=2)
s.box(350, 128, 300, 64, "Postgres — runs, steps, edges, queue", ["deps_remaining · (run_id, state)", "lease by SKIP LOCKED · by month · no logs"], badge=3)
s.box(670, 128, 290, 64, "Scheduler — stateless, leased", ["complete → decrement → READY at 0", "heartbeat reply: continue | cancel"], badge=4)
s.box(30, 208, 300, 56, "Cache", ["hash(inputs ‖ toolchain ‖ cmd) · trusted writes"], badge=5)
s.box(350, 208, 300, 56, "Runners — microVM per step, ~6 000", ["destroyed after · pool booted 30 min ahead"], badge=6)
s.box(670, 208, 290, 56, "Merge queue — only writer to main", ["speculative batch 8–16 · depth 3 · bisect"], badge=7)
s.box(30, 284, 300, 56, "Logs + artifacts", ["stream 10 min → S3 90 d · digest → deploy"], badge=8)
s.box(350, 284, 300, 56, "Flake budget", ["retry once if flaky: true · > 1 % quarantined 7 d"])
s.box(670, 284, 290, 56, "Fair share", ["by team, only while the queue is non-empty"])
s.lane(30, 370, "9 · IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 382, 220, 44, "5 000 pushes is a decoy", ["1 M steps · 10 × at 09:00"])
s.box(270, 382, 220, 44, "cache hit rate is the metric", ["60 % ≈ 1 800 runner-hours/day"])
s.box(510, 382, 220, 44, "step timeout 60 min", ["lease 30 s · supersede ≤ 30 s"])
s.box(740, 382, 220, 44, "hits never lease", ["keys resolved at run creation"])

SKEL_CAP = ("Badge 1 before any box, badge 5 before the runners — the cache is the cost story and it goes on the "
            "board before the pool does. Badge 7 is the box most candidates never draw, and the margin's first "
            "tile is the number to kill before the interviewer quotes it back.")

PAGE = 'design-cicd.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
