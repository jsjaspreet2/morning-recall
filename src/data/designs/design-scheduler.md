# Design a Job Scheduler — Durable Work Queues Under Overload

## The question

> *"Design a job scheduler for a compute platform. Teams submit jobs — a CI pipeline, a nightly report, a video render, a training run — with a priority, resource needs, sometimes a dependency on other jobs, sometimes a schedule. The system runs each job on a fleet of workers, retries failures, and when there is more work than capacity, decides who waits."*

**The product.** An engineer pushes a commit and a pipeline of twenty steps has to run, in order, on machines the engineer never sees. A data team wants a report at 06:00 every day. A researcher submits a training run that needs eight GPUs for six hours. All of it lands in one system that owns a fleet of workers and answers, for every job, three questions: *has it run, is it running, and if not, why not.* Workers crash mid-job, the fleet is full at nine in the morning, and a job that runs twice can double-charge a customer or overwrite a result — so "run it" means run it exactly once in effect, and "who waits" is a rule, not luck.

**What a working system delivers**

- A submitted job starts within a second when there is capacity, and the submitter can see where it is in line when there is not.
- A worker dying mid-job costs a retry, never a lost job and never a job that runs twice.
- A pipeline step runs only after the steps it depends on succeeded, and a failed step stops what depends on it without stopping everything else.
- The 06:00 report runs at 06:00, once, including on the morning the scheduler itself was being restarted.
- A tenant that submits a hundred thousand jobs at once does not stop everyone else's ten.

**Why this gets asked.** It looks like a queue with workers, and everyone can draw that in a minute. What the round is watching is the second minute: what happens when a worker dies holding a job, what "exactly once" can actually mean, and what the scheduler does when it is full — because a queue with workers has no answer to any of those, and the answers are the design.

---

**Archetype:** durable work queues & scheduling — work that can run anywhere and fail anywhere must execute exactly once in effect, and under sustained overload someone has to decide who waits.
**Cousins that reuse ~70% of this page:** CI/CD pipelines, cron and scheduled-task services, GPU training and render job schedulers (the text-to-video prompt), data pipeline orchestrators (Airflow, Dagster), background job systems (Sidekiq, Celery, SQS + workers), batch inference. Also **any product where a unit of work outlives the request that created it and runs on a machine you have to assume will die.**

**What's actually being graded:** whether the **per-job state machine** is drawn before any box; whether the **lease with a heartbeat** is named as the correctness mechanism for a dead worker, with a fencing token so a zombie's late completion is rejected; whether you say plainly that **the scheduler can only offer at-least-once and the job body has to be idempotent** — and what that costs; and whether **overload has a policy** — priority, fair-share, preemption — with a stated bound on how long anyone waits, rather than "it queues."

**Contrast to have ready:** *ChatGPT's §9 schedules requests for a fixed GPU pool with a human waiting on the socket, so latency is the whole design and nothing is durable. Here nobody is waiting on a socket: a job is a row that survives everything, and the page trades latency for correctness everywhere it can. Demand response is the same state machine idea per target; the difference is that here the worker is yours, it dies, and the retry is the scheduler's job rather than a reconnect hook.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "This is a durable work queue with a scheduler on top. Three things dominate. First, **the job is a state machine and the lease is the mechanism**: a worker claims a job under a lease, heartbeats to keep it, and if the heartbeat stops the job goes back to ready — so a dead worker is a retry, and a slow worker that comes back is fenced by the attempt number. Second, **exactly-once is not something the scheduler can give you**: it delivers at-least-once, and the job body has to be idempotent — I'll say what that costs the people writing jobs. Third, **overload needs a policy**: at nine in the morning there is more work than workers, and the answer is priority within a tenant, weighted fair-share across tenants, and preemption for the expensive resources, with a bound on how long a high-priority job can wait. I'll draw the state machine first, go deep on the lease and on the overload policy, and cover dependencies and cron as the two things people bolt on badly. Out of scope: what runs inside the worker — the sandbox is its own page."

**Why open this way:** it names the two mechanisms the round is about — the lease and the overload policy — in the first minute, it makes the exactly-once admission before the interviewer can spring it, and it pre-commits the dives (§7, §9). The state machine first is the plateau card's rule, and on this prompt it also happens to be the data model.

---

## 1 · Functional requirements

1. **Submit a job** — a payload, a resource class, a priority, optionally a delay or a dependency on other jobs — and have it **run exactly once in effect** on a worker, retried on failure with backoff, with its state, attempts, and logs queryable by id.
2. **Decide who waits under overload**: jobs are dispatched by priority within a tenant and **weighted fair-share across tenants**, lower-priority work on scarce resources can be **preempted**, and no ready job waits longer than a stated bound at its priority.
3. **Scheduled jobs fire on time and once** — a cron expression produces one job per tick, within a stated tolerance, and never two, including across scheduler restarts and failovers.

**Out of scope (say them):** the worker runtime and sandbox (the Hosted notebooks page), artifact and log storage beyond a pointer, the CI product's UI and git integration, fleet autoscaling (named as a lever, not designed), billing for compute, long-running stateful workflows with human steps (§15 — a workflow engine).

**Below the line, likely follow-ups:** gang scheduling for multi-GPU jobs, job cancellation mid-run, rate limits per tenant, a dead-letter queue and its UI, multi-region, checkpoint-and-resume for preempted jobs.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Throughput** | **5 M jobs/day ≈ 60/s average; 2 k/s at the 09:00 CI peak**, sustained for ten minutes | Peaks are pipelines fanning out. The queue store is sized on the peak's claim rate, not the average (§3) |
| **Dispatch latency** | Ready → running **p99 < 1 s** when capacity exists | Fast enough that a CI step chain of twenty feels like one job. Slower than this and pipelines pay it twenty times |
| **Exactly-once effect** | **At-least-once execution; exactly-once effect** via an idempotent job body and a fencing token per attempt | The honest split. The scheduler guarantees a job is never lost and never runs concurrently under two valid leases; the job guarantees running twice is harmless (§8) |
| **Lease** | Heartbeat every **10 s**; a job with no heartbeat for **30 s** is re-leased | Three missed heartbeats separates a GC pause from a dead worker. Shorter and slow workers flap; longer and a dead worker's job waits a minute |
| **Fair-share bound** | At 100 % utilisation, a P0 job waits **< 60 s**; any tenant's P1 job waits **< 5 min**; no tenant is starved | The number the overload policy is judged on. "It queues" is not a bound (§9) |
| **Cron accuracy** | Fires within **±5 s** of the tick; **never twice** for one tick; a missed tick fires **once, late**, and is labelled | A leader failover at 06:00:00 must not produce zero reports or two (§11) |
| **Durability** | An acknowledged submission **survives loss of any scheduler node** and of the database primary with failover | A job is a row committed before the `201`. There is no in-memory queue anywhere on the accept path |
| **Fault tolerance** | Survives: any worker (its jobs re-lease within 30 s), the scheduler leader (a new one within 10 s, no dispatch lost), the heartbeat store (workers fall back to renewing leases in the database). **Does not survive: the job database primary down without failover** — no new dispatch, no new submissions; running jobs finish and workers buffer their completions until it returns; nothing already accepted is lost | Name the one that stops the world and say what keeps running. Here, running work finishes and the queue is frozen |
| **Scale** | 50 k workers · up to 200 k running jobs · 1 M ready jobs in the peak backlog · 100 k cron schedules | §3 |

**The sentence that earns the point:** *"The scheduler promises two things — never lost, never running under two leases at once — and refuses to promise the third: that it won't run twice. That third one belongs to the job, and the scheduler's job is to make it cheap: the attempt number is the fencing token, and the job's side effects key on it."*

---

## 3 · Numbers that reframe the problem

**The claim rate at the peak is what sizes the queue store**

- 2 k/s of dispatches for ten minutes means **2 k claims/s** against a table of ready jobs, each claim a `SELECT … FOR UPDATE SKIP LOCKED` on an indexed prefix. A single Postgres primary does **~10 k such claims/s** before the index becomes the bottleneck. **The queue fits in one database**, which is the number that keeps a message broker off the page (§12).
- The backlog during the peak is **~1 M ready rows** — fine for an index on `(class, priority, ready_at)`, and the reason the ordering has to be an index rather than a sort.

**Lease renewals are the real write load, and they are batched per worker**

- 200 k running jobs × one heartbeat / 10 s = **20 k renewals/s** if each is a row update. Batched as **one statement per worker per 10 s** that extends every lease that worker holds, it is **5 k statements/s** — the difference between a comfortable primary and a hot one. Heartbeat liveness itself goes to a Redis key with a TTL and never touches the database (§7).

**The idle-worker fan-in is the other hot spot**

- 50 k workers polling for work every second is **50 k queries/s of "anything for me?"** — five times the claim rate, for nothing. Workers **long-poll** (a claim that waits up to 10 s) or are **pushed** by a per-class dispatcher that already knows the backlog. Say which; both are fine; neither is "poll every second."

**A CI pipeline is twenty jobs and nineteen edges**

- 5 M jobs/day, mostly in pipelines of ~20, is **~250 k DAGs/day**. Each completion decrements its children's `deps_unmet` — **one small transaction per completion**, 60/s. Dependencies are counters, not a graph walk, and this number is why (§10).

**Cron is a hundred thousand rows evaluated once a minute**

- 100 k schedules, evaluated by **one leader** every minute, firing ~2 k/min. A single indexed scan on `next_tick ≤ now`, and the firing is an insert with a unique key. **Cron is small; the only hard thing about it is firing once across a failover** (§11).

**The GPU jobs are 1 % of the count and most of the preemption story**

- *Assumption:* 1 % of jobs need GPUs; they run for hours; the GPU fleet is fixed. A P0 GPU job arriving at a full fleet **waits hours unless something is preempted**, and preempting a six-hour training run without a checkpoint throws away six hours. **Preemption cost decides the policy** — this is the number that makes fair-share a checkpointing question (§9).

---

## 4 · Core entities

### Draw this first — the per-job state machine

```text
                  deps met · ready_at ≤ now            claim (lease)          heartbeat ok
SCHEDULED ──▶ PENDING ──────────▶ READY ────────────────▶ LEASED ──▶ RUNNING ──────▶ SUCCEEDED
   (cron)        ▲                 ▲                        │           │
                 │                 │  backoff elapsed       │ lease     │ non-zero exit
                 │                 └──── RETRY_WAIT ◀───────┴───────────┤   (attempt < max)
                 │                                                      │
                 │                                                      ├──▶ FAILED   (attempt = max, terminal)
                 │                                                      ├──▶ DEAD     (poison: crashed the worker N times)
   any non-terminal ──▶ CANCELLED                                       └──▶ PREEMPTED ──▶ READY  (checkpoint saved)
```

| Transition | Caused by | Component that owns it | Recorded where | Timer |
|---|---|---|---|---|
| `SCHEDULED → PENDING` | The cron tick arrives | **Cron leader** — one insert keyed `(schedule_id, tick)` | `jobs` | ±5 s |
| `PENDING → READY` | `deps_unmet = 0` and `ready_at ≤ now` | The completing parent's transaction, or the delay sweep | `jobs` | — |
| `READY → LEASED` | A worker claims: `SKIP LOCKED`, sets `lease_until`, `attempt + 1` | **Worker**, via the claim API | `jobs`, `attempts` | lease 30 s |
| `LEASED → RUNNING → SUCCEEDED / FAILED` | The worker reports, **with its attempt number as the fencing token** | Worker | `jobs`, `attempts` | heartbeat 10 s |
| `LEASED / RUNNING → RETRY_WAIT` | Lease expired (no heartbeat 30 s) or non-zero exit with attempts left | **Lease sweeper** (expiry) or the worker (exit) | `jobs`, `attempts` | backoff with jitter |
| `RETRY_WAIT → READY` | Backoff elapsed | Delay sweep | `jobs` | — |
| `RUNNING → PREEMPTED → READY` | A higher-priority job needs the resource; the worker checkpoints and stops | **Scheduler** (decision) + worker (checkpoint) | `jobs`, `attempts` | grace 60 s |
| `→ DEAD` | The job crashed its worker *N* times (poison) | Lease sweeper, on the attempt count | `jobs` — the dead-letter queue is a state, not a place | — |
| `→ CANCELLED` | A user cancels; a running one is signalled through the lease | API, then the worker on next heartbeat | `jobs` | — |

**The rule, and it is the whole method:** *every transition is a compare-and-set on the job row with the expected state and, for anything a worker does, the expected `attempt`.* A worker that lost its lease, ran on, and reports `SUCCEEDED` for attempt 3 when the row is at attempt 4 loses the CAS and its result is discarded. The dead-letter queue is `state = DEAD`, queried, not a second queue to keep consistent with the first.

### The entities

- **Job** — `(job_id, tenant, class, priority, payload_ref, idempotency_key, state, attempt, max_attempts, ready_at, deps_unmet, lease_until, worker_id, version, checkpoint_ref, submitted_at)`. The row the machine lives on.
- **Attempt** — `(job_id, n, worker_id, started_at, ended_at, outcome, exit_code, log_ref)`. Append-only; the answer to "why did it fail."
- **Edge** — `(parent_id, child_id)`. A DAG is jobs plus edges; `deps_unmet` on the child is the derived counter.
- **Schedule** — `(schedule_id, tenant, cron_expr, job_template, next_tick, last_fired_tick, missed_policy)`.
- **Worker** — `(worker_id, class, slots, capabilities)`; **liveness is a Redis key with a TTL**, not a column.
- **Tenant share** — `(tenant, weight, running_by_class)`; the fair-share input, maintained by the dispatcher.

**The three that are load-bearing:**

**The attempt number is the fencing token.** Every claim increments it; every report carries it; every write by a worker is conditional on it. That one integer is what turns "a worker might be a zombie" from a distributed-systems problem into a failed `UPDATE`.

**`deps_unmet` is a counter, not a graph.** A child becomes ready when its counter hits zero, decremented by each parent's completing transaction. The DAG is never walked at dispatch time; it was walked once at submission to set the counters and reject cycles.

**Liveness and the lease are two different things in two different stores.** Liveness — "is this worker alive" — is a heartbeat with a TTL in Redis, cheap and lossy. The lease — "who may run this job until when" — is a column in the job row, durable and authoritative. Losing Redis loses nothing but the fast path for detecting deaths; the lease expiry in the database is the backstop.

---

## 5 · API

```text
POST /v1/jobs                              Idempotency-Key: <client key>
     { class: "cpu-2x", priority: 1, payload_ref, max_attempts: 3,
       ready_at?, depends_on?: [job_id…], idempotency_key: "build:sha:abc" }
     → 201 { job_id, state: PENDING | READY }
POST /v1/jobs/batch                        a DAG: { jobs: [...], edges: [[i, j], …] }   → 201 { job_ids }   cycles → 422
GET  /v1/jobs/{id}                         → { state, attempt, position?: { class, ahead: 4 812 }, attempts: [...] }
POST /v1/jobs/{id}/cancel                  → 202
POST /v1/schedules                         { cron: "0 6 * * *", job_template, missed_policy: fire_once | skip }

── worker protocol ───────────────────────────────────────────────────────────
POST /v1/workers/{id}/claim               { class, free_slots, wait_s: 10 }        long-poll
     → 200 { jobs: [ { job_id, attempt, payload_ref, lease_until, checkpoint_ref? } ] }
POST /v1/workers/{id}/heartbeat           { running: [ {job_id, attempt, progress?} ] }     one call, every 10 s
     → 200 { lease_until, preempt: [job_id…], cancel: [job_id…] }             ← control channel rides the reply
POST /v1/jobs/{id}/complete               { attempt, outcome: succeeded | failed, exit_code, log_ref, checkpoint_ref? }
     → 200  |  409 stale_attempt                                                ← the zombie's result, refused
```

**Decisions to narrate, unprompted:**

- **`attempt` is on every worker call, and `409 stale_attempt` is the fencing token doing its job.** A worker that paused for forty seconds and came back finds its lease gone and its report refused. The scheduler never trusts a worker's belief about who holds a job.
- **One heartbeat per worker, not per job.** It carries every running job's id and attempt, renews all their leases in one statement, and **the reply is the control channel** — preempt and cancel instructions come back on it, so there is no inbound connection to a worker.
- **`idempotency_key` on the job is the submitter's, and it dedupes submissions; the `attempt` dedupes executions.** Two different problems, two keys, and saying which is which is most of §8.
- **`position` on `GET /jobs`** is what the submitter sees instead of a spinner: how many jobs of this class are ahead. It is a count on the index, cheap, and it is the honest face of the fair-share policy.
- **`missed_policy` on a schedule** is the cron decision people forget: a tick missed during an outage fires once late, or is skipped. Nightly reports want `fire_once`; a "every minute" health check wants `skip`.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 620" role="img" aria-label="Job scheduler architecture. Submitters call an API that writes job rows, edges and schedules into Postgres, partitioned by day with a claim index. Stateless scheduler nodes run dispatchers that serve worker claims with SKIP LOCKED, a lease sweeper on lease expiry, and one leader elected by a database lease that fires cron ticks as unique inserts. Fifty thousand workers long-poll for claims, heartbeat once per worker every ten seconds and receive preempt and cancel instructions on the reply, and report completions with their attempt number as a fencing token. Worker liveness is a Redis key with a TTL. Payloads, checkpoints and logs live in object storage; terminal jobs are archived to ClickHouse.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">The queue is a table and the lease is the mechanism: never lost, never under two leases; the job body makes twice harmless.</text>
  <rect class="dg-group" x="20" y="86" width="250" height="120" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">SUBMIT</text>
  <rect class="dg-box" x="36" y="118" width="218" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="145" y="142.5">API</text>
  <text class="dg-s dg-c" x="145" y="158.5">POST /jobs · /jobs/batch (DAG)</text>
  <text class="dg-s dg-c" x="145" y="174.5">Idempotency-Key · cycles → 422</text>
  <rect class="dg-group" x="300" y="86" width="380" height="200" rx="12"></rect>
  <text class="dg-group-t" x="316" y="108">SCHEDULER NODES — STATELESS, ANY NUMBER</text>
  <rect class="dg-box" x="316" y="118" width="170" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="401" y="134.5">Dispatcher</text>
  <text class="dg-s dg-c" x="401" y="150.5">claim: SKIP LOCKED</text>
  <text class="dg-s dg-c" x="401" y="166.5">rank: priority · share · age</text>
  <text class="dg-s dg-c" x="401" y="182.5">fair-share counts in memory</text>
  <rect class="dg-box" x="500" y="118" width="164" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="582" y="138.5">Lease sweeper</text>
  <text class="dg-s dg-c" x="582" y="154.5">lease_until &lt; now</text>
  <text class="dg-s dg-c" x="582" y="170.5">→ RETRY_WAIT · DEAD</text>
  <rect class="dg-good" x="500" y="196" width="164" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="582" y="216.5">Cron leader</text>
  <text class="dg-s dg-c" x="582" y="232.5">leader lease, 5 s</text>
  <text class="dg-s dg-c" x="582" y="248.5">UNIQUE (schedule, tick)</text>
  <path class="dg-box" d="M 710,125 L 710,263 A 135,7 0 0 0 980,263 L 980,125 A 135,7 0 0 0 710,125 Z"></path>
  <path class="dg-box" d="M 710,125 A 135,7 0 0 0 980,125" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="170">Postgres — jobs</text>
  <text class="dg-s dg-c" x="845" y="186">partitioned by day</text>
  <text class="dg-s dg-c" x="845" y="202">(class, state, priority, ready_at)</text>
  <text class="dg-s dg-c" x="845" y="218">attempt = the fencing column</text>
  <text class="dg-s dg-c" x="845" y="234">edges · attempts · schedules · leader</text>
  <path class="dg-line" d="M 216,118 L 216,78 L 845,78 L 845,110"></path>
  <path class="dg-head" d="M 840,110 L 850,110 L 845,118 Z"></path>
  <text class="dg-lbl dg-c" x="530" y="72">rows, committed before the 201</text>
  <path class="dg-line" d="M 664,150 L 702,150"></path>
  <path class="dg-head" d="M 702,155 L 702,145 L 710,150 Z"></path>
  <path class="dg-line" d="M 664,228 L 702,228"></path>
  <path class="dg-head" d="M 702,233 L 702,223 L 710,228 Z"></path>
  <rect class="dg-group" x="20" y="320" width="660" height="150" rx="12"></rect>
  <text class="dg-group-t" x="36" y="342">WORKERS ×50 k</text>
  <rect class="dg-box" x="36" y="356" width="300" height="100" rx="8"></rect>
  <text class="dg-t dg-c" x="186" y="386.5">Worker daemon</text>
  <text class="dg-s dg-c" x="186" y="402.5">long-poll claim · one heartbeat / 10 s for all jobs</text>
  <text class="dg-s dg-c" x="186" y="418.5">complete {attempt} → 409 if stale</text>
  <text class="dg-s dg-c" x="186" y="434.5">buffers completions while the API is down</text>
  <rect class="dg-warn" x="366" y="356" width="298" height="100" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="515" y="386.5">The job body</text>
  <text class="dg-s dg-c" x="515" y="402.5">at-least-once from us → idempotent by contract</text>
  <text class="dg-s dg-c" x="515" y="418.5">side effects keyed on job_id / attempt</text>
  <text class="dg-s dg-c" x="515" y="434.5">checkpoint hook if preemptible</text>
  <path class="dg-line" d="M 186,356 L 186,300 L 400,300 L 400,198"></path>
  <path class="dg-head" d="M 405,198 L 395,198 L 400,190 Z"></path>
  <text class="dg-lbl dg-c" x="300" y="294">claim · heartbeat · complete</text>
  <path class="dg-line" d="M 420,190 L 420,310 L 200,310 L 200,348"></path>
  <path class="dg-head" d="M 195,348 L 205,348 L 200,356 Z"></path>
  <text class="dg-lbl dg-c" x="310" y="342">jobs · preempt · cancel</text>
  <path class="dg-box" d="M 710,327 L 710,377 A 60,7 0 0 0 830,377 L 830,327 A 60,7 0 0 0 710,327 Z"></path>
  <path class="dg-box" d="M 710,327 A 60,7 0 0 0 830,327" style="fill:none"></path>
  <text class="dg-t dg-c" x="770" y="352">Redis</text>
  <text class="dg-s dg-c" x="770" y="368">liveness TTL 30 s</text>
  <path class="dg-line" d="M 336,444 L 350,444 L 350,464 L 700,464 L 700,352 L 702,352"></path>
  <path class="dg-head" d="M 702,357 L 702,347 L 710,352 Z"></path>
  <text class="dg-lbl dg-c" x="700" y="312">heartbeat</text>
  <path class="dg-box" d="M 860,327 L 860,377 A 60,7 0 0 0 980,377 L 980,327 A 60,7 0 0 0 860,327 Z"></path>
  <path class="dg-box" d="M 860,327 A 60,7 0 0 0 980,327" style="fill:none"></path>
  <text class="dg-t dg-c" x="920" y="352">Object storage</text>
  <text class="dg-s dg-c" x="920" y="368">payloads · logs</text>
  <path class="dg-box" d="M 710,413 L 710,463 A 135,7 0 0 0 980,463 L 980,413 A 135,7 0 0 0 710,413 Z"></path>
  <path class="dg-box" d="M 710,413 A 135,7 0 0 0 980,413" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="438">ClickHouse — archive</text>
  <text class="dg-s dg-c" x="845" y="454">terminal jobs + attempts · 2 y</text>
  <path class="dg-line" d="M 845,270 L 845,398"></path>
  <path class="dg-head" d="M 840,398 L 850,398 L 845,406 Z"></path>
  <text class="dg-lbl" x="855" y="300">terminal rows, hourly</text>
  <text class="dg-s" x="20" y="510">Liveness (Redis, cheap, lossy) and the lease (a column, durable) are two things: losing Redis loses nothing but the fast path for detecting deaths.</text>
  <text class="dg-s" x="20" y="532">Dead-letter is a state, not a queue. The leader is a leased job. The DAG is a counter decremented in the parent's commit.</text>
  <text class="dg-note" x="20" y="554">Exactly-once execution is not on offer. At-least-once plus an idempotent job body is, and the attempt number makes the second half one line.</text>
</svg>
</div>

<p class="diagram-cap">Draw the state machine first, then this. The two arrows between the workers and the dispatcher are the whole protocol — claim up, jobs down, and the heartbeat reply carrying preempt and cancel — and the warning box is the contract the scheduler cannot sign for the job.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 620" role="img" aria-label="Job scheduler flows in three lanes. Claim and lease: a worker claims with SKIP LOCKED, the row moves to leased with attempt incremented and a thirty-second lease; heartbeats renew it; a lost heartbeat moves the job to retry-wait and it is re-claimed as the next attempt, while the zombie's late completion is refused with a stale-attempt conflict. Overload: the claim ranks by priority, then fair-share deficit, then aging; a P0 arriving at a full GPU fleet preempts the cheapest checkpointed job within sixty seconds. Cron: the leader fires a tick as a unique insert; a failover fires it late but once; a partitioned old leader hits the unique constraint.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Claim under a lease, renew by heartbeat, fence by attempt; rank by priority then fair-share; fire cron as a unique row.</text>
  <text class="dg-lane" x="30" y="76">CLAIM AND LEASE — THE DEAD WORKER IS A RETRY, THE ZOMBIE IS A 409</text>
  <rect class="dg-box" x="30" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="135" y="114.5">READY → LEASED</text>
  <text class="dg-s dg-c" x="135" y="130.5">SKIP LOCKED · attempt + 1</text>
  <text class="dg-s dg-c" x="135" y="146.5">lease_until = now + 30 s</text>
  <rect class="dg-good" x="270" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="375" y="114.5">heartbeat every 10 s</text>
  <text class="dg-s dg-c" x="375" y="130.5">one per worker, all jobs</text>
  <text class="dg-s dg-c" x="375" y="146.5">reply: preempt · cancel</text>
  <path class="dg-line" d="M 240,126 L 262,126"></path>
  <path class="dg-head" d="M 262,131 L 262,121 L 270,126 Z"></path>
  <rect class="dg-warn" x="510" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="620" y="114.5">no heartbeat 30 s</text>
  <text class="dg-s dg-c" x="620" y="130.5">sweeper: → RETRY_WAIT</text>
  <text class="dg-s dg-c" x="620" y="146.5">re-claimed as attempt 2</text>
  <path class="dg-line" d="M 480,126 L 502,126"></path>
  <path class="dg-head" d="M 502,131 L 502,121 L 510,126 Z"></path>
  <rect class="dg-warn" x="760" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="870" y="114.5">zombie completes attempt 1</text>
  <text class="dg-s dg-c" x="870" y="130.5">409 stale_attempt</text>
  <text class="dg-s dg-c" x="870" y="146.5">result discarded, log kept</text>
  <path class="dg-line" d="M 730,126 L 752,126"></path>
  <path class="dg-head" d="M 752,131 L 752,121 L 760,126 Z"></path>
  <text class="dg-s" x="30" y="190">Attempt 1's side effects already happened. That is the job body's problem, and the contract makes it cheap: key them on job_id.</text>
  <path class="dg-div" d="M 20,206 L 980,206"></path>
  <text class="dg-lane" x="30" y="240">OVERLOAD — 09:00, A MILLION READY JOBS, THE FLEET FULL</text>
  <rect class="dg-box" x="30" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="175" y="278.5">rank at claim time</text>
  <text class="dg-s dg-c" x="175" y="294.5">priority → fair-share deficit (DRF)</text>
  <text class="dg-s dg-c" x="175" y="310.5">→ aging → ready_at</text>
  <rect class="dg-box" x="350" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="278.5">tenant X: 100 k jobs at P1</text>
  <text class="dg-s dg-c" x="495" y="294.5">gets its weighted share, no more</text>
  <text class="dg-s dg-c" x="495" y="310.5">GET /jobs shows position</text>
  <path class="dg-line" d="M 320,290 L 342,290"></path>
  <path class="dg-head" d="M 342,295 L 342,285 L 350,290 Z"></path>
  <rect class="dg-good" x="670" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="815" y="278.5">P0 GPU job, fleet full</text>
  <text class="dg-s dg-c" x="815" y="294.5">preempt cheapest checkpointed P2</text>
  <text class="dg-s dg-c" x="815" y="310.5">60 s grace → P0 runs &lt; 60 s</text>
  <path class="dg-line" d="M 640,290 L 662,290"></path>
  <path class="dg-head" d="M 662,295 L 662,285 L 670,290 Z"></path>
  <rect class="dg-warn" x="350" y="342" width="290" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="495" y="366.5">non-preemptible jobs</text>
  <text class="dg-s dg-c" x="495" y="382.5">never killed · wait longer to start</text>
  <path class="dg-line" d="M 815,326 L 815,370 L 648,370"></path>
  <path class="dg-head" d="M 648,365 L 648,375 L 640,370 Z"></path>
  <text class="dg-s" x="30" y="424">The bounds are the design output: P0 &lt; 60 s · P1 &lt; 5 min for any tenant · P3 eventually. “It queues” is not a bound.</text>
  <path class="dg-div" d="M 20,440 L 980,440"></path>
  <text class="dg-lane" x="30" y="474">CRON — ONCE, ACROSS A FAILOVER</text>
  <rect class="dg-box" x="30" y="488" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="175" y="516.5">leader scans next_tick ≤ now</text>
  <text class="dg-s dg-c" x="175" y="532.5">INSERT job UNIQUE (schedule, tick)</text>
  <rect class="dg-warn" x="350" y="488" width="290" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="495" y="508.5">leader dies 05:59:58</text>
  <text class="dg-s dg-c" x="495" y="524.5">standby takes the lease 06:00:04</text>
  <text class="dg-s dg-c" x="495" y="540.5">fires the 06:00 tick, 4 s late</text>
  <path class="dg-line" d="M 320,520 L 342,520"></path>
  <path class="dg-head" d="M 342,525 L 342,515 L 350,520 Z"></path>
  <rect class="dg-good" x="670" y="488" width="290" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="815" y="508.5">old leader wakes 06:00:05</text>
  <text class="dg-s dg-c" x="815" y="524.5">same insert → unique violation</text>
  <text class="dg-s dg-c" x="815" y="540.5">one report, not two</text>
  <path class="dg-line" d="M 640,520 L 662,520"></path>
  <path class="dg-head" d="M 662,525 L 662,515 L 670,520 Z"></path>
  <text class="dg-note" x="30" y="590">An hour-long outage: fire_once for the nightly report, late and labelled; skip for the every-minute check. Decided per schedule, before it happens.</text>
</svg>
</div>

<p class="diagram-cap">The top lane is the whole correctness argument in four boxes; the last one — a 409 — is where most designs have nothing. The middle lane turns “it queues” into three numbers, and the bottom lane's mechanism is a unique constraint, not the leader.</p>

### Flow A — a job runs, and its worker dies

1. `POST /jobs`. The API dedupes on the idempotency key, inserts the row in `READY` (no deps, no delay), commits, returns `201`. **The job exists before anyone is told about it.**
2. A worker with a free `cpu-2x` slot long-polls `claim`. The dispatcher runs one statement: select the next ready job for that class by `(priority, fair-share rank, ready_at)` **`FOR UPDATE SKIP LOCKED`**, set `state = LEASED, worker_id, attempt = 1, lease_until = now + 30 s`. Fifty other workers claiming at the same instant skip this row and take the next.
3. The worker starts the job, reports `RUNNING`, and heartbeats every 10 s; each heartbeat extends `lease_until` for every job it holds in one statement.
4. The job exits 0. `complete {attempt: 1, succeeded}` → CAS on `(job_id, attempt = 1, state ∈ {LEASED, RUNNING})` → `SUCCEEDED`. The completion transaction also decrements `deps_unmet` on any children (§10).
5. **The failure path.** The worker's host dies at step 3. Heartbeats stop; its Redis liveness key expires in 30 s; the **lease sweeper** — which also runs on a database index of `lease_until < now`, so it works with Redis gone — moves the job to `RETRY_WAIT` with `attempt = 1` recorded as `lost_lease`, then to `READY` after a jittered backoff. Another worker claims it as **attempt 2**. Meanwhile the first host comes back from what was actually a 45-second network partition, finishes attempt 1, and calls `complete {attempt: 1}`. **`409 stale_attempt`.** Its result is discarded; whatever side effects attempt 1 had are the job body's problem, and §8 is about making that problem cheap.

### Flow B — 09:00, and the fleet is full

1. Two thousand pipelines fan out in a minute: **~1 M ready jobs** against 50 k workers already running 200 k jobs.
2. The dispatcher's claim query ranks ready jobs by **priority first, then the tenant's fair-share deficit** — how far below its weighted share of running slots the tenant currently is — **then `ready_at`**. A tenant with weight 10 running 5 % of the fleet outranks one with weight 1 running 20 %, at equal priority.
3. Tenant X submitted 100 k jobs at P1. It gets its share and no more; its jobs behind the share wait, and `GET /jobs` shows them their position. Tenant Y's ten P1 jobs are ahead of X's 99,990th.
4. A P0 job arrives for the `gpu-8x` class and the GPU fleet is full of P2 training runs. The dispatcher picks the **cheapest preemption** — the P2 job with the most recent checkpoint — and returns `preempt: [job]` on that worker's next heartbeat. The worker checkpoints (60 s grace), stops, and the job goes to `PREEMPTED → READY` with its `checkpoint_ref`. The P0 job claims the slot. **P0 waited under 60 s at 100 % utilisation** (→ the fair-share-bound NFR).
5. **The failure path.** The P2 job had no checkpoint support. Preempting it throws away four hours. The policy says so: **jobs declare `preemptible: true` with a checkpoint hook, or they are scheduled at a lower priority ceiling and never preempted** — they simply wait longer to start. The trade is stated at submission, not discovered at 09:00.

### Flow C — a pipeline, and a step that fails

1. `POST /jobs/batch` with 20 jobs and 19 edges: lint → build → 16 parallel test shards → package → deploy. The API validates the DAG (no cycles: a topological sort at submission), inserts 20 rows with `deps_unmet` set per child, commits. Only `lint` is `READY`.
2. `lint` succeeds; its completion transaction decrements `build.deps_unmet` to 0 and flips `build` to `READY`. `build` succeeds; sixteen shards go `READY` at once and are claimed by sixteen workers.
3. Shard 11 exits non-zero: `RETRY_WAIT`, backoff 30 s → `READY` → attempt 2 on another worker → succeeds. `package.deps_unmet` reaches 0 only when all sixteen have succeeded.
4. **The failure path.** Shard 11 fails three times: `FAILED`, terminal. `package` and `deploy` stay `PENDING` forever — **a failed parent never makes a child ready** — and the pipeline's summary view (a query over the 20 rows) reports `failed at test-11`. Nothing downstream ran; the fifteen other shards' results are kept for the re-run, which is a **new batch that reuses their idempotency keys and short-circuits**: the job body for a shard keyed `test:sha:11` sees a prior success and returns it. The DAG did not need a transaction, a workflow engine, or a saga.

### Flow D — 06:00, during a leader failover

1. The cron leader holds a **leader lease** in the database (`leader_until`, renewed every 5 s). Every minute it scans `schedules WHERE next_tick ≤ now` and, per schedule, inserts a job with **`UNIQUE (schedule_id, tick)`** and advances `next_tick` in the same transaction.
2. At 05:59:58 the leader's host dies. Its lease expires at 06:00:03; a standby acquires it at 06:00:04 and runs the scan.
3. It finds the 06:00 tick unfired, inserts the job — **four seconds late, inside the ±5 s tolerance** — and advances `next_tick`.
4. **The failure path.** The old leader was not dead, only partitioned, and it wakes at 06:00:05 and tries to fire the same tick. Its insert hits the unique constraint: **one report, not two.** The unique key is the mechanism; the leader lease is only an optimisation that stops two leaders from *trying*. And if the outage had lasted an hour, the standby finds sixty missed ticks for the every-minute schedules and applies their `missed_policy` — `skip` — and one missed tick for the nightly report — `fire_once`, late, labelled.

---

## 7 · Deep dive — the lease is the correctness mechanism: claim, heartbeat, expiry, and the fencing token

### What you'd reach for first

A queue. Workers pop a job, run it, and ack when done. If a worker dies, the job is "in flight" and… a timeout puts it back.

### What breaks

- **"Pop" is a lost job or a double run, depending on when you delete.** Delete on pop and a dead worker loses the job. Delete on ack and a dead worker leaves it in flight forever — or a timeout re-queues it while the not-actually-dead worker finishes, and it runs twice with **both results accepted**.
- **A timeout with no heartbeat cannot tell slow from dead.** A six-hour training run and a crashed worker look identical to a 30-second timeout. Set it long and dead workers hold jobs for hours; set it short and long jobs are re-queued while they run.
- **A zombie's result is indistinguishable from a live one.** The worker that paused for a GC, lost its slot, and came back writes "succeeded" over a row another worker is now running. Nothing rejects it.

### What replaces it

- **A claim is a CAS on the job row**: `UPDATE jobs SET state = 'LEASED', worker_id = $w, attempt = attempt + 1, lease_until = now() + 30 s WHERE job_id IN (SELECT … WHERE class = $c AND state = 'READY' ORDER BY priority, share_rank, ready_at LIMIT $n FOR UPDATE SKIP LOCKED) RETURNING *`. Fifty concurrent claimers on the same index take fifty different rows; none blocks. This is the queue-in-a-database pattern, and at 2 k claims/s it is inside a single primary's envelope by 5×.
- **The lease is short and renewed, so it measures liveness, not duration.** 30 s, renewed every 10 s by one heartbeat per worker that extends every job it holds. A six-hour job holds a 30-second lease six hundred and twenty times. Dead means "missed three heartbeats," regardless of how long the job was meant to run.
- **Expiry is a sweeper on an index**: `WHERE state IN ('LEASED','RUNNING') AND lease_until < now()` → `RETRY_WAIT`, once a second, from any scheduler node. Redis liveness makes death detection faster (a TTL expiry event in ~30 s); the database sweeper is the backstop that works when Redis is gone.
- **The attempt number is the fencing token.** Every claim increments it; every worker call carries it; every state change a worker requests is `WHERE attempt = $reported`. The zombie's `complete {attempt: 1}` against a row at attempt 2 is a `409`, its log is kept under attempt 1 for the post-mortem, and its side effects are §8's problem — but its *result* never lands.
- **The rejected alternative, and the sentence:** *"SQS gives me this as a visibility timeout with a receipt handle, and I'd take it for a background-job system with no priority and no dependencies. Here I need priority ordering, fair-share ranking, and a DAG counter in the same transaction as the completion — that is a database, and `SKIP LOCKED` is what makes a database a queue."*

**Cost, volunteered:**

- **The job table is hot.** Every claim, heartbeat batch, and completion is a write on one table; at the peak that is ~10 k writes/s. Partition by day, keep the index narrow, and archive terminal rows out (§12). A queue table that is never vacuumed is the classic way this design dies in year one.
- **Heartbeats through the database are 5 k statements/s** even batched. Fine, and the reason liveness is *also* in Redis: the database sees renewals, Redis sees deaths, and the cheap one is the fast one.
- **A lost lease is a retry, and a retry is a second execution.** Thirty seconds of a dead worker's job is re-done, and if the job is not idempotent that is a bug the scheduler cannot fix. Which is the next dive.

**→ ties to the lease and fault-tolerance NFRs.**

---

## 8 · Deep dive — exactly-once is at-least-once plus an idempotent job body, and it costs the people who write jobs

### What you'd reach for first

"The scheduler guarantees exactly-once execution."

### What breaks

- **It cannot.** A worker that ran the job to completion and died before reporting looks identical to one that died before starting. The scheduler has to retry both, so the first one runs twice. **No lease, timeout, or transaction changes this** — it is the two-generals problem with a job instead of a message.
- **"Exactly-once" as a checkbox produces double charges.** A job that emails a customer, charges a card, or appends to a report is run again after a lost lease, and the scheduler kept its promise as far as it could tell.
- **A distributed transaction between the scheduler and the job's side effects** — commit the job's writes and the completion together — works only when both are in the same database, and drags every job's side effects into the scheduler's transaction scope.

### What replaces it

**Say the split, then make the idempotent half cheap.**

- **The scheduler promises at-least-once execution, never-lost, and never-concurrent-under-valid-leases.** The third is the fencing token (§7). The first two are the durable row and the sweeper.
- **The job body is required to be idempotent, and the scheduler hands it the tools:** the `job_id`, the `attempt`, and the submitter's `idempotency_key`. The contract, written in the job SDK's first paragraph: *your side effects must be keyed on `job_id` (or the idempotency key), so a second attempt finds the first's result and returns it.* Charge a card with `idempotency_key = job_id`; write a report to `reports/{job_id}`; send an email through a provider that dedupes on a message id you derive from the job.
- **For side effects in the same database as the scheduler**, the completion *can* be transactional: the job's writes and its `SUCCEEDED` transition commit together, and a lost lease after commit is a `409` on the report with no re-run — the transactional outbox, inverted. Offer it; do not require it.
- **Attempts are bounded, with backoff and jitter, and the end is `DEAD`, not infinity.** `max_attempts = 3` default; backoff `min(30 s × 2^n, 15 min)` plus jitter, so a thousand jobs failing on the same dependency do not retry in lockstep. A job that **crashed its worker** (OOM, segfault) rather than exiting non-zero is poison: after two such attempts it goes to `DEAD` without using its remaining budget, because a third worker is a third casualty. **The dead-letter queue is `state = DEAD` with a reason, queryable, re-drivable by an operator** — a state, not a second queue.
- **The rejected alternative, and the sentence:** *"I could offer exactly-once by running every job's side effects through the scheduler's database — an outbox the job writes to and we drain. It's the right answer when every job is 'write some rows,' and it's wrong here, where a job is a shell command that talks to twelve external systems. So the contract is idempotency, and the SDK makes it one line."*

**Cost, volunteered:**

- **Every job author has to think about it once.** The SDK and the docs carry the weight; the review checklist says "what happens if this runs twice." Jobs that cannot be made idempotent — a legacy script that appends — get `max_attempts = 1` and a human in the loop, and the scheduler says so in the job's state.
- **Re-doing thirty seconds of work on a lost lease** is the price of a short lease. At 2 % worker churn a day it is noise; during a bad deploy that kills workers it is the retry storm §11 has a circuit breaker for.
- **`DEAD` needs an owner.** A dead-letter state that nobody looks at is a silent loss with better logging.

**→ ties to the exactly-once-effect NFR.**

---

## 9 · Deep dive — priority, fair-share, and preemption: who waits at 09:00

### What you'd reach for first

FIFO. Or strict priority: highest priority first, ties by submission time.

### What breaks

- **FIFO starves the small and the urgent.** Tenant X's 100 k jobs arrive at 08:59; tenant Y's one P0 hotfix build waits behind all of them. The queue is fair to jobs and unfair to everyone.
- **Strict priority starves the low.** P2 jobs never run while any P1 exists, and at sustained overload some P1 always exists. And a tenant that learns this marks everything P0.
- **No preemption means a scarce resource is first-come-forever.** The GPU fleet fills with six-hour P2 runs at 08:00 and a P0 arrives at 08:05. Without preemption it waits six hours; with naive preemption it throws away six hours of someone else's work.

### What replaces it

**Priority within a tenant, weighted fair-share across tenants, aging so nothing starves, and preemption that is opt-in and checkpointed.**

- **The dispatch order is a rank, computed at claim time from three terms:** `priority` (0–3, set by the submitter, capped per tenant by policy so P0 means something); **fair-share deficit** — the tenant's weight divided by its current share of running slots in this class, so under-served tenants rank higher; and `ready_at` with **aging** — every ten minutes waiting promotes a job one priority level, so P3 eventually runs. The rank is an expression over indexed columns plus one in-memory number per tenant (its running count), maintained by the dispatcher.
- **Fair-share is weighted max-min by tenant, per resource class.** When jobs contend on two resources at once — GPUs and memory — it is **dominant-resource fairness**: a tenant's share is measured by whichever resource it uses the most of. Say the name and what it fixes: a tenant hoarding GPUs while using little CPU is over its share.
- **The bound is the design output.** P0 at 100 % utilisation: under 60 s, because a P0 preempts. P1 for any tenant: under 5 min, because fair-share guarantees the tenant's slice and aging promotes what waits. P3: eventually, and `GET /jobs` says how many are ahead. **"It queues" becomes three numbers.**
- **Preemption is opt-in, checkpointed, and cheapest-first.** A job declares `preemptible: true` and a checkpoint hook; the scheduler preempts the lowest-priority preemptible job with the **freshest checkpoint** (least work lost), signals it on the heartbeat reply, gives 60 s of grace, and re-queues it `READY` with `checkpoint_ref`. Non-preemptible jobs are never killed; they wait longer to *start* instead, and that is the trade the submitter chose.
- **Gang scheduling for multi-GPU jobs** is the one thing the claim query cannot do alone: an 8-GPU job needs eight slots on one host at once. The dispatcher **reserves** slots as they free up, holding them idle for up to the job's `gang_timeout`, then claims all eight in one transaction — or releases them and moves on. Idle-while-reserving is the cost; a job that can never assemble eight slots on a busy fleet is the failure it prevents.

**Cost, volunteered:**

- **Fair-share needs a running count per tenant per class**, maintained on every claim and completion — an in-memory map in the dispatcher, rebuilt from the database on restart. It is approximate for a second after a restart and that is fine.
- **Aging means priorities are not absolute**, and a tenant watching its P0 get overtaken by an aged P3 will ask why. Cap aging below P0, and document it.
- **Checkpointing is the job's work.** A framework that checkpoints every ten minutes loses ten minutes on preemption; one that does not is non-preemptible by construction. The scheduler offers the hook; the ML platform team writes it.

**→ ties to the fair-share-bound and dispatch-latency NFRs.**

---

## 10 · Deep dive — dependencies as counters, not a workflow engine

### What you'd reach for first

The pipeline is one job that runs its steps in order. Or: a workflow engine (Temporal, Step Functions) that owns the DAG and calls the scheduler for each step.

### What breaks

- **One job for the pipeline serialises sixteen test shards** and re-runs the whole thing when one fails. And it makes the pipeline's state live inside one worker, which dies.
- **A workflow engine per pipeline is a second scheduler** with its own state, retries, and failure modes, whose only job here is decrementing a counter. It earns its place when steps are long, stateful, and wait on humans or timers for days (§15) — not for `lint → build → test`.
- **Walking the graph at dispatch** — "is everything upstream of this done?" — is a query per candidate job per claim, against a million-row backlog. It is the scan the claim query exists to avoid.

### What replaces it

- **A DAG is jobs plus edges, and readiness is a counter.** At submission, validate (topological sort; a cycle is `422`), insert every job with `deps_unmet = number of parents`, and mark the roots `READY`. Nothing else is stored about the graph's shape beyond the edges.
- **A completion decrements its children in the same transaction** that marks the parent `SUCCEEDED`: `UPDATE jobs SET deps_unmet = deps_unmet − 1, state = CASE WHEN deps_unmet − 1 = 0 THEN 'READY' ELSE state END WHERE job_id IN (children)`. One transaction, tens of rows, 60/s. The child becomes claimable the instant its last parent commits, with no poller in between.
- **A failed parent never decrements.** Children stay `PENDING`; the pipeline view — a query over the batch's rows — reports where it stopped. There is no "cancel downstream" fanout to get wrong: downstream never became ready.
- **Re-runs reuse idempotency keys.** Submitting the batch again with the same per-step keys lets succeeded steps short-circuit in their job bodies (§8), so a pipeline re-run after one flaky shard re-executes one shard. The scheduler did not need a "resume" feature; the idempotency contract gave it one.
- **Fan-in and fan-out are the same counter.** Sixteen shards → `package` is `deps_unmet = 16`; `build` → sixteen shards is sixteen rows with `deps_unmet = 1`. Diamond shapes, conditional edges (`run_if: parent_failed`), and per-edge artifact passing are small additions to the edge row, and each is a product decision to name rather than build.

**Cost, volunteered:**

- **The graph is validated once and then trusted.** Editing a DAG after submission — adding a step to a running pipeline — is a new batch, not a mutation. That is a product constraint worth saying.
- **A completion transaction touches the children's rows**, which for a fan-out of a thousand is a thousand-row update on the hot table. Batch it, and cap fan-out per job at something like 10 k with the reason.
- **Long-lived, stateful, human-in-the-loop workflows do not fit this**, and the honest sentence is *"the day a step waits three days for an approval and needs its variables back, that is Temporal, and I'd run it on top of this scheduler rather than instead of it."*

**→ ties to the dispatch-latency NFR, via the no-poller readiness.**

---

## 11 · Deep dive — cron that fires once, a scheduler that survives itself, and what to watch

### What you'd reach for first

A cron loop in the scheduler process: every minute, for each schedule, if it is due, enqueue. Run one scheduler. Run two for HA.

### What breaks

- **One scheduler is the thing that stops the world.** Its host dies at 05:59 and the 06:00 report does not run; nobody notices until 09:00.
- **Two schedulers fire every tick twice.** Two reports, two invoices, two emails. HA made it worse.
- **A scheduler that was down for an hour** either fires sixty missed ticks of an every-minute job in a burst, or silently skips the one nightly job that mattered. Neither was decided.
- **A retry storm during a bad deploy** — workers crashing on start, every job's lease lost every 30 s — turns the queue table into 200 k re-leases a minute and the dead-letter state into a landfill.

### What replaces it

- **Firing is an insert with `UNIQUE (schedule_id, tick)`.** That constraint, not the leader, is what makes a tick fire once. Two schedulers racing produce one row and one constraint violation. The `tick` is the schedule's nominal time (06:00:00), not the wall clock at firing, so a late firing is still the 06:00 tick.
- **A leader lease so only one scheduler *tries*** — `leader_until` in the database, renewed every 5 s, acquired by CAS when expired. Standbys run the same code and win the lease within 10 s of the leader's death. The leader is itself a leased job, with the same mechanism as §7, which is a good sentence to say.
- **`missed_policy` per schedule.** On acquiring the lease, the new leader finds every schedule with `next_tick < now − tolerance` and applies the policy: `fire_once` inserts one job for the oldest missed tick and advances past the rest; `skip` advances `next_tick` to the next future tick. Both are one statement per schedule and both are logged as *missed*, so the 06:00 report that ran at 07:04 says so.
- **The scheduler's own availability, honestly:** dispatchers and sweepers are stateless and run on every node; the leader is only for cron and for the fair-share bookkeeping, and its loss costs seconds. The job database is the one dependency, and its loss **freezes the queue without losing it** — running jobs finish, workers buffer completions and retry them, and nothing accepted is gone (→ the fault-tolerance NFR).
- **A retry circuit breaker per class:** if lost leases in a class exceed a rate — say 5 % of running jobs a minute — new claims for that class pause for a minute and an alert fires. A bad worker image stops taking down the queue with it, and the jobs wait rather than burn their attempt budgets.
- **Observability, as the questions an operator asks:**
  - **Oldest ready age per class and priority** — the fair-share bound, measured. The single most important graph.
  - **Queue depth by class and priority** — the backlog shape, and the autoscaling input.
  - **Lost-lease rate** — worker deaths; a step change is a bad deploy.
  - **Retry rate and `DEAD` inflow** — the job-quality signal, by tenant.
  - **Dispatch latency p99** (ready → running) — the claim path's health.
  - **Cron lag** — nominal tick to actual fire, p99; and missed-tick count.
  - **Preemptions per hour and work lost** (minutes since the last checkpoint, summed) — the cost of the P0 guarantee.
  - **Leader age** and **heartbeat-store fallback active** — the scheduler's own health.

**Cost, volunteered:**

- **The leader is a single point of *coordination*, not of failure**, and that sentence needs to be true: every leader-only task must be safe to run twice (it is: unique ticks, idempotent bookkeeping) because the lease can be held by two nodes for a few seconds across a partition.
- **`fire_once` for a nightly job that depends on the previous night's** is still wrong if the previous night was skipped. Chains of scheduled jobs are DAGs across days, and the policy has to say whether a late run runs on stale input.
- **The circuit breaker pauses good jobs with bad ones** in the same class. The alternative — per-job-image breakers — is finer and more machinery; the class is the right granularity until it is not.

**→ ties to the cron-accuracy and fault-tolerance NFRs.**

---

## 12 · Data model, sharding, and storage decisions

**Partition on `class`, and say why it is not `tenant`.** Every claim is "the next job for a worker of class *c*," every fair-share count is per class, and every backlog graph is per class. Partitioning by tenant would spread one class's claims across every tenant's partition and make the claim query a scatter. The job table itself is **one Postgres primary partitioned by submission day** — the throughput fits (§3), and the day partition is what makes archiving a partition drop rather than a `DELETE` of five million rows.

**The hot row is not a row; it is the claim index.** Two thousand claims a second on `(class, state, priority, ready_at)` is contention on the index's leading pages, not on any job. `SKIP LOCKED` is what keeps fifty claimers from serialising on the same first row. If one class ever needed more than ~10 k claims/s, that class gets its own database; nothing else changes.

**Terminal rows leave the hot table.** A job in `SUCCEEDED`, `FAILED`, `DEAD`, or `CANCELLED` is archived to the analytics store within an hour and its row dropped with the day partition. The queue table holds the live set — a few million rows — not the history.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Jobs (live)** | Claims via `SKIP LOCKED` at 2 k/s peak; lease renewals 5 k stmt/s; completions with child decrements | **System of record** | **Postgres**, partitioned by day, index `(class, state, priority, ready_at)`, `attempt` as the fencing column | "Kafka can't do priority or per-job ack, and SQS can't do the DAG decrement in the completion's transaction. At two thousand claims a second a database is a queue, and `SKIP LOCKED` is the whole trick" |
| **Attempts** | Append per claim and per completion; read by job id | 90 days | **Postgres**, same cluster, then the archive | "Why did it fail is a query, not a log search" |
| **Edges** | Written at batch submit; read by the completion transaction | With the batch | **Postgres**, `(parent_id, child_id)`, index on parent | "The graph is validated once; after that it's a counter" |
| **Schedules** | 100 k rows; scanned once a minute by the leader; `UNIQUE (schedule_id, tick)` on the fired jobs | System of record | **Postgres** | "The unique constraint is the exactly-once cron; the leader lease just stops two nodes from trying" |
| **Worker liveness** | 50 k heartbeats / 10 s; expiry events | **Ephemeral** — the database lease is the backstop | **Redis**, key per worker, TTL 30 s, keyspace notifications for deaths | "Redis sees deaths fast and cheaply; if it's gone, the sweeper on `lease_until` catches them in the same 30 s. Losing it loses nothing" |
| **Fair-share counters** | Read on every claim; updated on claim and completion | Rebuildable from the live table | **In-memory on the dispatcher**, per class, rebuilt at startup | "Approximate for a second after a restart, and that's fine — it's a rank, not a ledger" |
| **Leader lease** | Renewed every 5 s; CAS to acquire | Durable | **A row in Postgres** | "The scheduler is a leased job, same mechanism as everything it schedules" |
| **Payloads and checkpoints** | Written by submitters and workers; read at claim | Durable, content-addressed | **Object storage**, referenced by the job row | "The row holds a pointer. A queue table full of payloads is a queue table that can't be indexed" |
| **Logs** | Streamed by workers; read by humans | 30 days | **Object storage**, `log_ref` on the attempt | "The scheduler never sees a log line" |
| **Archive** | Terminal jobs and attempts; queried for dashboards and per-tenant reports | 2 years | **ClickHouse**, `ORDER BY (tenant, submitted_at)` | "The live table holds the live set; history goes where `GROUP BY` is cheap" |
| **Worker** | Slots, running jobs, in-flight completions buffered on disk when the API is down | Local | A daemon with a small local queue of unreported completions | "A worker that finishes while the database is down keeps its result and reports it later, with its attempt number" |

### Data lifecycle — the append-only entities

| Entity | Growth | Hot | Warm | Cold | Restore |
|---|---|---|---|---|---|
| **Jobs** | 5 M/day | Live rows in the day partitions; terminal rows dropped within an hour | — | ClickHouse, 2 years | Minutes; `GET /jobs/{id}` falls through to the archive for old ids |
| **Attempts** | ~7 M/day | 90 days in Postgres | — | ClickHouse, 2 years | Same |
| **Logs** | Job-dependent | 30 days in object storage | — | Deleted; a product decision | n/a |
| **Schedules, edges** | Tiny | Live | — | With the archive | — |

### The signals that tell you this is broken

The list in §11, and one meta-signal: **the ratio of lost-lease retries to exit-code retries.** The first is the platform failing; the second is jobs failing. When the first rises, deploy less; when the second rises, talk to a tenant.

---

## 13 · Traps — the ranked list

**Design traps**

1. **A queue with pop and ack, and no lease.** Delete-on-pop loses jobs; delete-on-ack double-runs them; a timeout cannot tell slow from dead (§7).
2. **No fencing token.** The zombie worker's "succeeded" lands over another attempt's row (§7).
3. **Promising exactly-once.** The scheduler cannot; the job body must be idempotent, and the SDK makes that one line (§8).
4. **A dead-letter *queue*.** A second queue to keep consistent with the first. `DEAD` is a state, queried, with an owner (§8).
5. **FIFO, or strict priority, as the overload policy.** One starves the urgent, the other starves the patient; neither has a bound (§9).
6. **Preemption without checkpoints, or without opt-in.** Six hours of someone's training run, thrown away by policy (§9).
7. **Walking the DAG at dispatch.** A scan per candidate per claim; readiness is a counter decremented by the parent's commit (§10).
8. **A workflow engine for `lint → build → test`.** A second scheduler whose only job is a counter (§10).
9. **Two schedulers, no unique tick.** HA that fires every cron twice (§11).
10. **`missed_policy` undecided.** Sixty bursts, or one silent skip, discovered the morning after (§11).
11. **Heartbeats per job.** 20 k row updates a second where one statement per worker does (§3, §7).
12. **The lease timeout sized to the job's duration.** Dead workers hold hours-long jobs for hours (§7).
13. **Payloads in the queue table.** An index over rows that are kilobytes each (§12).

**Performance traps**

14. **Workers polling every second.** 50 k queries/s of nothing; long-poll or push (§3).
15. **A queue table that is never partitioned or vacuumed.** The year-one death of this design (§7, §12).
16. **Retries in lockstep.** A thousand jobs failing on one dependency and retrying at the same instant; backoff needs jitter (§8).
17. **No circuit breaker on lost leases.** A bad worker image burns every job's attempt budget in five minutes (§11).
18. **Fan-out of a hundred thousand children on one completion transaction** (§10).

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

19. **Drawing the queue and the workers and stopping.** The first minute's diagram is the same on every answer; the round is the dead worker, the double run, and the full fleet. Say the state machine before the queue, and the lease before the worker.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 450" role="img" aria-label="Job scheduler five-minute skeleton. The per-job state machine across the top; then the Postgres queue table, the claim and heartbeat, and the fencing token; then the exactly-once split, liveness versus lease, and the overload rank with its bounds; then preemption and gang scheduling, DAGs as counters, and cron; and a margin lane of the signals.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="44" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="94.5">PENDING → READY → LEASED → RUNNING → SUCCEEDED · RETRY_WAIT loops · FAILED · DEAD · CANCELLED · PREEMPTED → READY · CAS on state + attempt</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="30" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="148.5">Jobs — Postgres</text>
  <text class="dg-s dg-c" x="180" y="164.5">by day · index (class, state, priority, ready_at)</text>
  <text class="dg-s dg-c" x="180" y="180.5">the queue is a table; SKIP LOCKED makes it one</text>
  <circle class="dg-num" cx="30" cy="128" r="9"></circle>
  <text class="dg-num-t" x="30" y="131.4">2</text>
  <rect class="dg-box" x="350" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="148.5">Claim + heartbeat</text>
  <text class="dg-s dg-c" x="500" y="164.5">lease 30 s · attempt + 1 · one heartbeat per worker</text>
  <text class="dg-s dg-c" x="500" y="180.5">reply carries preempt · cancel</text>
  <circle class="dg-num" cx="350" cy="128" r="9"></circle>
  <text class="dg-num-t" x="350" y="131.4">3</text>
  <rect class="dg-box" x="670" y="128" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="148.5">Fencing token</text>
  <text class="dg-s dg-c" x="815" y="164.5">attempt on every worker call · stale → 409</text>
  <text class="dg-s dg-c" x="815" y="180.5">the zombie's result never lands</text>
  <circle class="dg-num" cx="670" cy="128" r="9"></circle>
  <text class="dg-num-t" x="670" y="131.4">4</text>
  <rect class="dg-box" x="30" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="232.5">The honest split</text>
  <text class="dg-s dg-c" x="180" y="248.5">at-least-once + idempotent body = exactly-once</text>
  <circle class="dg-num" cx="30" cy="208" r="9"></circle>
  <text class="dg-num-t" x="30" y="211.4">5</text>
  <rect class="dg-box" x="350" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="232.5">Liveness vs lease</text>
  <text class="dg-s dg-c" x="500" y="248.5">Redis TTL for deaths · lease_until index as backstop</text>
  <circle class="dg-num" cx="350" cy="208" r="9"></circle>
  <text class="dg-num-t" x="350" y="211.4">6</text>
  <rect class="dg-box" x="670" y="208" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="232.5">Overload rank + bounds</text>
  <text class="dg-s dg-c" x="815" y="248.5">priority → share → aging · P0 &lt; 60 s, P1 &lt; 5 min</text>
  <circle class="dg-num" cx="670" cy="208" r="9"></circle>
  <text class="dg-num-t" x="670" y="211.4">7</text>
  <rect class="dg-box" x="30" y="284" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="308.5">Preemption · gang</text>
  <text class="dg-s dg-c" x="180" y="324.5">opt-in · checkpointed · cheapest-first · gang</text>
  <circle class="dg-num" cx="30" cy="284" r="9"></circle>
  <text class="dg-num-t" x="30" y="287.4">8</text>
  <rect class="dg-box" x="350" y="284" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="308.5">DAGs as counters</text>
  <text class="dg-s dg-c" x="500" y="324.5">deps_unmet −1 in the parent's commit · failed: never</text>
  <circle class="dg-num" cx="350" cy="284" r="9"></circle>
  <text class="dg-num-t" x="350" y="287.4">9</text>
  <rect class="dg-box" x="670" y="284" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="308.5">Cron</text>
  <text class="dg-s dg-c" x="815" y="324.5">lease + UNIQUE (schedule, tick) + missed_policy</text>
  <circle class="dg-num" cx="670" cy="284" r="9"></circle>
  <text class="dg-num-t" x="670" y="287.4">10</text>
  <text class="dg-lane" x="30" y="370">IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="400.5">oldest ready age</text>
  <text class="dg-s dg-c" x="140" y="416.5">per class and priority</text>
  <rect class="dg-box" x="270" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="380" y="400.5">lost-lease rate</text>
  <text class="dg-s dg-c" x="380" y="416.5">platform failing vs jobs failing</text>
  <rect class="dg-box" x="510" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="400.5">DEAD inflow · cron lag</text>
  <text class="dg-s dg-c" x="620" y="416.5">with an owner</text>
  <rect class="dg-box" x="740" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="850" y="400.5">the scheduler is a leased job</text>
  <text class="dg-s dg-c" x="850" y="416.5">same mechanism</text>
</svg>
</div>

<p class="diagram-cap">Badge 1 before the queue, badge 4 before the worker. Badge 5 is the sentence the round is fishing for — say it before the interviewer asks what exactly-once means here — and badge 7's two numbers are what “it queues” has to become.</p>

1. **The state machine, top centre, before any box:** `PENDING → READY → LEASED → RUNNING → SUCCEEDED`, with `RETRY_WAIT` looping back, terminals `FAILED · DEAD · CANCELLED`, and `PREEMPTED → READY`. Write beside it: *"every transition is a CAS on state and attempt."*
2. **Jobs table — Postgres**, partitioned by day, index `(class, state, priority, ready_at)`. Label it **"the queue is a table; `SKIP LOCKED` makes it one."**
3. **The claim:** `FOR UPDATE SKIP LOCKED`, sets lease 30 s and `attempt + 1`. **The heartbeat:** one per worker per 10 s, renews every lease it holds, **carries preempt and cancel back.**
4. **The fencing token:** `attempt` on every worker call; a stale one is `409`. Label it **"the zombie's result never lands."**
5. **The honest split:** at-least-once execution + idempotent job body = exactly-once effect. Backoff with jitter; `DEAD` is a state.
6. **Worker liveness** in Redis with a TTL; **lease expiry** on a database index — the sweeper works with Redis gone.
7. **The overload policy as a rank:** priority → fair-share deficit (DRF) → aging → `ready_at`. Write the three bounds: **P0 < 60 s, P1 < 5 min, P3 eventually.**
8. **Preemption**: opt-in, checkpointed, cheapest-first, 60 s grace. **Gang scheduling** reserves slots with a timeout.
9. **DAGs as counters:** `deps_unmet`, decremented in the parent's completion transaction; a failed parent never decrements.
10. **Cron:** leader lease + **`UNIQUE (schedule_id, tick)`** + `missed_policy`. In the margin: oldest-ready age, lost-lease rate, `DEAD` inflow, cron lag — and *"the scheduler is itself a leased job."*

---

## 15 · Variants — what actually changes

**The governing axis: what an attempt costs when it is lost, which decides how much the scheduler invests in not losing it.** Every row has a durable job, a lease, a retry, and a policy for overload. What moves is whether preemption and checkpointing exist, whether dependencies matter, and whether the thing being scheduled is a job at all.

| Product | What a lost attempt costs | Dependencies? | The delta from this page |
|---|---|---|---|
| **Background jobs** — Sidekiq, Celery, SQS + workers | Seconds; retry and forget | Rarely | The smallest instance. No priority beyond a few named queues, no fair-share, no DAG: **Redis or SQS is the right store**, and §7's visibility timeout is the whole lease. This page's database queue is overkill here and the sentence says so |
| **CI/CD pipelines** — the OpenAI prompt | Minutes, and a developer waiting | **Always** — the DAG is the product | §10 is the centre of the page; ephemeral runners are the Hosted notebooks page's §15 row; artifacts pass between steps by reference; the overload policy is per-repo fair-share at 09:00. Cron is "nightly builds" |
| **Cron / scheduled tasks** — the service itself | One missed report | Across days | §11 is the whole page: the unique tick, the leader lease, `missed_policy`, and clock skew. Everything else is one worker pool |
| **This page — a general job scheduler** | Minutes to hours | Sometimes | As written |
| **GPU training and render jobs** — the text-to-video prompt | **Hours of GPU time** | Sometimes | §9 dominates: **preemption is a checkpoint question**, gang scheduling is required, DRF over GPUs and memory, and fair-share across research teams is a political document as much as a policy. Batching renders by model onto the same GPU is the ChatGPT page's §9 economics applied to a queue. The fleet is fixed, so the overload bound is honest only with preemption |
| **Data pipeline orchestration** — Airflow, Dagster | Hours, and downstream data is stale | **The DAG spans days** and is re-run by date | §10 with time as a dimension: every DAG run is keyed by its logical date; backfills are batches of past dates; sensors wait on external data and are jobs that poll. `missed_policy` becomes "catch up" by default |
| **Durable workflows** — Temporal, Step Functions | A workflow's state between steps | **Steps are stateful and wait on the world** for days | The row this page hands off to: when a step needs its variables back three days later, or waits on a human, the *workflow's* state has to be durable, not just the job's. Run it on top of this scheduler — it schedules its activities here — never instead of it |
| **Inference requests** — ChatGPT §9 | A user's request, and they are waiting | No | **Not a job.** Nothing is durable; the queue is in memory; the policy is admission control and batching under a latency budget. The degenerate row that proves this page's investment in durability is bought entirely by nobody waiting on a socket |

**The lesson:** the queue and the workers are the same picture in every row. **What a lost attempt costs** decides whether the store is Redis or a database, whether preemption needs checkpoints, and whether the DAG is a counter or a product — and a candidate who says that cost in the first minute has already chosen most of the page.
