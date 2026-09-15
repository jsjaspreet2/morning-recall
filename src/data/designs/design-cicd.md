# Design a CI/CD Pipeline — Event-Triggered DAG Execution

## The question

> *"Design the CI/CD system for a company with ten thousand engineers in one monorepo. Every push runs a pipeline of a couple of hundred steps — build, lint, unit tests, integration tests, packaging — and engineers expect a result in about ten minutes. Merging to main has to be gated on green. Steps run code written by anyone in the company, so runners can't trust each other. Around five thousand pushes a day, with a big spike at nine in the morning."*

**The product.** An engineer pushes a commit and, a few minutes later, sees a list of checks turn green or red next to it, with a log for each one they can open while it is still running. If they push again before the first run finishes, the old run stops and the new one takes its place. When they click merge, the change lands on main only if it is green *against what main looks like now*, not against what it looked like when they branched. Underneath, most of the work on any given push has been done before — the same library built from the same sources on someone else's push an hour ago — and a system that redoes it is slow for everyone and expensive for the company. At the end, a green run on main hands a build artifact to the deployment system, which is where this page stops.

**What a working system delivers**

- A push shows its first check result within a minute and its last within about ten, at nine in the morning as at midnight.
- A second push to the same branch cancels the first run's remaining work, and nobody waits behind it.
- A step that ran on identical inputs an hour ago does not run again; the result appears in seconds, labelled as a cache hit.
- A merge that would break main is rejected before it lands, even when twenty other merges are trying to land in the same minute.
- A malicious step in one pull request cannot read another team's secrets, poison the shared cache, or touch a runner it did not get.

**Why this gets asked.** It looks like the Job scheduler with a web hook in front, and a candidate who answers it that way runs out of things to say at minute fifteen. What makes it its own problem is that the work has edges, the run has an expiry, and the cheapest step is the one that never runs.

---

**Archetype:** event-triggered DAG execution — every push becomes a DAG of isolated steps on ephemeral workers; the run is superseded the moment a newer commit lands; correctness is the cache key, and the scarce thing is the worker pool at 09:00.
**Cousins that reuse ~70% of this page:** GitHub Actions and Buildkite (§15), Bazel remote execution, Airflow and Dagster (a DAG with a schedule instead of a push), data pipeline orchestration, ML training pipelines, any build-and-test farm.
**What's actually being graded:** whether the **DAG is scheduled as counters, not as a graph walk**; whether **supersession** is a first-class state that races in-flight leases; whether the **cache key is content, not the commit hash**, and cache writes are restricted to trusted runs; whether the **09:00 spike sizes a warm pool** rather than a queue; and whether a **merge queue** is named as the thing that makes "green on the PR" mean "green on main."

**Contrast to have ready:** *The Job scheduler places independent jobs that end, and its lease plus fencing token is reused here verbatim. Here the jobs have edges, a run has a supersession rule, and half the work should never execute because the cache already has the answer. The Deployment system starts exactly where this page ends, at the artifact digest a green main run produces.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "This is a DAG execution system triggered by pushes, and three things make it more than a job scheduler. First, **the unit is a run, not a job**: a push creates a run of about two hundred steps with dependencies, and a newer push to the same branch supersedes the whole run, so cancellation has to race the leases already out on runners. Second, **the cache is the product**: keyed by a hash of a step's inputs and toolchain, never by the commit, so an unchanged library built on someone else's push an hour ago is a hit — and only runs of main may write to it, because a pull request can contain anything. Third, **the load is bursty and the runners are untrusted**: five thousand pushes a day is a decoy, the 09:00 hour is ten times the average, and each step gets its own microVM from a warm pool that is sized for that hour and drained after it. On top sits a merge queue, because green on the branch is not green on main. I'll draw the step state machine first, go deep on scheduling and supersession, on the cache, and on the runner pool, and I'll cover the merge queue as the thing that decides the throughput of main. Out of scope: the build tool itself, the deploy half, and test selection."

**Why open this way:** it names the run as the unit before the interviewer asks what happens on a second push, puts the cache ahead of the scheduler so the cost story is on the table early, kills the pushes-per-day number, and pre-commits the dives (§7, §8, §9).

---

## 1 · Functional requirements

1. **Run the pipeline for a commit** — from a push event, resolve the pipeline definition at that commit into a DAG of steps, execute each step in an isolated runner once its dependencies have succeeded, and expose per-step status, streaming logs, and produced artifacts.
2. **Supersede a run when a newer commit lands on the same branch or pull request** — cancel every step of the old run that has not finished, including ones already executing, and never spend a runner on a result nobody will read.
3. **Gate merges to main on a green run against main's current head** — a merge queue that tests each change on top of the changes ahead of it, lands them in order, and ejects one that fails without blocking the rest.

**Out of scope (say them):** the build tool and its dependency graph (the pipeline definition arrives as a DAG; Bazel or a YAML file produced it), the deploy half (`/designs/deployment` begins at the digest), secrets management beyond "injected per step from a vault the runner cannot read directly", test selection and flake prediction, code review.

**Below the line, likely follow-ups:** manual approval steps, matrix builds, cross-repo triggers, scheduled and cron pipelines, self-hosted runner pools per team, cost attribution.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Time to first step running** | **< 60 s p95** from push, including at 09:00 | The engineer is watching. Sizes the warm pool (§9): a cold VM plus checkout is 90 s alone |
| **Pipeline p50** | **< 10 min** for a typical push; the critical path is ~8 min of steps, so **queue wait ≤ 60 s per step** | The number from the prompt. It buys parallelism (the DAG's width) and a warm pool; it does not buy faster tests |
| **Supersession latency** | A superseded run's steps stop consuming runners within **30 s** | One lease heartbeat interval (§7). Past it, the old run is burning capacity the new run needs |
| **Cache hit latency** | **< 2 s** to resolve a key and skip the step; **< 30 s** to fetch a 500 MB output | A hit that takes as long as the step is not a hit (§8) |
| **Step isolation** | One microVM per step, kernel boundary, no network to other runners, secrets injected per step with a **≤ 1 h** token | Runners execute code from any pull request. Isolation is a security requirement, not a scheduling one (§9) |
| **Step timeout** | **60 min** default, per-step override; lease heartbeat **10 s**, lease lost after **30 s** | The clock has an owner: the scheduler fails a step whose runner stops heartbeating, and re-queues it once |
| **Merge throughput** | **≥ 200 merges/hour** at peak with a 10-min pipeline, main stays green | Serial testing caps main at six merges an hour. Batching and speculation are required, not optional (§10) |
| **Log freshness** | Live tail **≤ 2 s** behind the step; full log readable **≤ 10 s** after completion | Engineers debug by watching (§11) |
| **Consistency** | Run and step state: **read-your-writes** from one Postgres primary. Cache index: **≤ 5 s** stale. Dashboards: **≤ 10 s** stale | Every freshness claim carries a duration |
| **Fault tolerance** | Survives: any runner (its step is re-queued once); any scheduler replica (leader lease, resumes from rows in **< 30 s**); the cache being unavailable (steps run uncached, slower, never wrong); the log store being unavailable (logs buffered on the runner for the step's lifetime). **Does not survive: the Postgres primary down without failover** — no new runs start, running steps finish and their completions queue on the runner until it returns | Name the frozen failure and what keeps working |
| **Scale** | 5 000 pushes/day · ~200 steps each · **1 M step executions/day nominal** · 10 × average at 09:00 | §3 |

**The sentence that earns the point:** *"Ten minutes is the critical path plus queue wait, and I can only buy down queue wait — so the pool is sized for nine in the morning, and the cache is what keeps the critical path from being every step."*

---

## 3 · Numbers that reframe the problem

**Five thousand pushes a day is a decoy; a million step executions is the load**

- 5 000 × 200 = **1 M scheduled steps a day**. *Assumption: 60 % are cache hits and 15 % are cancelled by supersession before they start.* That leaves **~250 k real executions a day**, at an assumed average of **3 min** each: 750 k runner-minutes, or **~520 runners busy on average**. Decision: the scheduler's write rate is trivial (§12); the cost and the burst are in the runner pool (§9).

**The 09:00 hour is ten times the average, and that is the pool**

- 10 × average is **~5 200 concurrent steps** for about an hour. With queue wait capped at 60 s, the pool at 09:00 is **~6 000 warm microVMs**, and at 03:00 it is a few hundred. A fixed pool sized for the peak idles at **~9 % utilisation**; a pool sized for the average makes 09:00 a forty-minute queue. Decision: a warm pool with a predictive scale-up thirty minutes ahead of the daily curve (§9).

**The cache is worth more than the scheduler**

- At 60 % hits, the cache removes **~600 k executions a day** — about **1 800 runner-hours**. Every point of hit rate is **~30 runner-hours a day**. *Assumption: 20 MB average output.* 250 k writes a day is **5 TB/day** into the cache; a 14-day retention is **~70 TB**. Decision: the cache is content-addressed object storage with a small index, and its hit rate is the metric the platform team is judged on (§8).

**Supersession is the second-biggest saving**

- *Assumption: a pull request averages six pushes, 20 minutes apart.* With a 10-minute pipeline most runs finish, but at 09:00 with a queue they do not, and **~15–25 % of scheduled steps belong to a run nobody will read**. Decision: cancellation is a run-level state that every lease check consults, not a best-effort kill (§7).

**Logs are the biggest byte stream and the least valuable byte**

- *Assumption: 2 MB per executed step.* 250 k × 2 MB = **500 GB/day**; 90 days is **45 TB**. Nobody queries across logs. Decision: object storage keyed by step id, a live tail through a short-lived stream, and no database anywhere near a log line (§11).

**Serial merges cap main at six an hour**

- *Assumption: 30 % of pushes end in a merge* — **1 500 merges a day**, peaking at **~200 an hour**. Testing each on top of the previous one serially, at 10 minutes each, is **6 an hour**. Decision: the merge queue batches and speculates, and the batch size is the throughput lever (§10).

---

## 4 · Core entities

### Draw this first — the step state machine

```text
                 in-degree 0      leased by a runner     runner reports
PENDING ──────▶ READY ──────▶ LEASED ──────▶ RUNNING ──────▶ SUCCEEDED
   │              │              │              │
   │              │              │              ├──▶ FAILED      (non-zero exit · 3 lease heartbeats missed → re-queued once, then FAILED)
   │              │              │              └──▶ TIMED_OUT   (step clock, owned by the scheduler)
   │              │              │
   └──────────────┴──────────────┴──▶ CANCELLED   (run superseded or aborted; a RUNNING step is killed on its next heartbeat reply)
                                                    
PENDING ──▶ CACHED   (cache key resolved to an existing output; counts as SUCCEEDED for dependants)
```

**Invariant:** a step transitions by **compare-and-set on `version`**, and a `RUNNING` step carries a `lease_token` that every completion must present. A completion with a stale token is dropped, which is how a runner that was cancelled but did not hear it cannot mark a superseded step green.

**Per run:** `CREATED → RUNNING → {SUCCEEDED, FAILED, SUPERSEDED, ABORTED}`. `SUPERSEDED` is set by the *next* run's creation, in the same transaction, and is the state every lease grant checks.

| Entity | Fields that carry a decision | Why |
|---|---|---|
| **run** | `repo`, `sha`, `ref`, `trigger`, `state`, `superseded_by`, `trusted` | `trusted` is true only for main and release branches; it gates cache writes and secret scope (§8). `superseded_by` is the cancel signal |
| **step** | `run_id`, `name`, `cache_key`, `state`, `version`, `attempt`, `lease_token`, `deps_remaining`, `pool` | `deps_remaining` is the in-degree counter (§7). `cache_key` is computed before scheduling, so a hit never touches a runner |
| **edge** | `(run_id, from_step, to_step)` | Read once at run creation to set counters; then only to find dependants on completion |
| **cache_entry** | `cache_key`, `output_digest`, `producer_run`, `size`, `last_hit` | `producer_run` is the audit trail for a bad entry; `last_hit` drives eviction |
| **artifact** | `digest`, `size`, `steps_referencing` | Content-addressed; the digest is what the deployment system receives |
| **runner** | `runner_id`, `pool`, `state`, `current_step`, `booted_at` | Ephemeral: a runner executes exactly one step and is destroyed (§9) |
| **merge_queue_entry** | `pr`, `position`, `batch_id`, `speculative_sha`, `state` | `speculative_sha` is the commit that was actually tested (§10) |

**The load-bearing three:** `step.deps_remaining` (the scheduler is a counter decrement), `step.cache_key` (the cost story), and `run.superseded_by` (the cancel story).

---

## 5 · API

```text
POST /v1/runs                              { repo, sha, ref, trigger: push | merge_queue | manual }   ← the web hook
     → 201 { run_id, superseded: [run_id…] }   supersedes any active run on the same ref, atomically
GET  /v1/runs/{id}                         → { state, steps: [{ name, state, cache_hit, duration, attempt }], critical_path_ms }
POST /v1/runs/{id}/cancel                  → 202
POST /v1/steps/{id}/retry                  → 201 { new step attempt }         only for FAILED / TIMED_OUT, flake budget enforced
POST /v1/merge-queue                       { pr }  → 201 { position }        ← merge is a queue entry, not a git push
GET  /v1/steps/{id}/logs?offset=           → chunked; live while RUNNING, from object storage after

── runner protocol ──────────────────────────────────────────────────────────────
POST /v1/runners/{id}/lease                → 200 { step_id, lease_token, inputs: [digest…], secrets_token, timeout }   or 204
POST /v1/steps/{id}/heartbeat              { lease_token, progress }   every 10 s
     → 200 { action: continue | cancel }                                ← the only downward channel to a runner
POST /v1/steps/{id}/complete               { lease_token, status, outputs: [{ path, digest }], cache_write: bool }
     → 200 · 409 if the token is stale
PUT  /v1/steps/{id}/logs                   { offset, bytes }            append-only, from the runner, ≤ 2 s batches
```

**Decisions to narrate, unprompted:**

- **`POST /runs` supersedes in the same transaction that creates.** The new run's insert and the old run's `state = SUPERSEDED` commit together, so there is never a moment when two runs on one ref are both active and both eligible for leases (§7).
- **The heartbeat reply is the cancel channel.** A runner learns it should stop the same way it learns anything: by asking every ten seconds. There is no inbound connection to a runner, which is also the isolation story (§9).
- **The lease carries input digests, not paths.** The runner fetches inputs from the artifact store by content hash. That is what makes a step reproducible and the cache key meaningful (§8).
- **`cache_write` is a request the server can refuse.** The runner says it produced a cacheable output; the server writes the index entry only if `run.trusted` (§8). The runner never holds cache-index credentials.
- **Merge is a queue entry.** The merge button calls `POST /merge-queue`, not git. The push to main is done by the queue after the speculative run is green (§10).

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 600" role="img" aria-label="CI/CD pipeline architecture. A push event from the git host creates a run in Postgres and supersedes the previous run on the same ref in the same transaction. A resolver turns the pipeline definition at that commit into about two hundred steps with dependency counters, and every step's cache key is looked up in a Redis index before anything is scheduled; hits are marked cached and never lease. A stateless, leader-leased scheduler grants leases to ready steps by skip-locked select, decrements dependants on completion, answers heartbeats with continue or cancel, and sweeps expired leases. About six thousand ephemeral microVM runners at nine in the morning poll for leases, fetch inputs by digest from S3, execute one step each, stream logs to a short-lived stream and then to S3, and are destroyed. Only trusted runs write the cache index. A merge queue is the only writer to main and tests speculative batches through the same scheduler. Events flow to Kafka and ClickHouse.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">A run is a DAG of counters with an expiry; the cache decides what never runs, and the pool is sized for nine o'clock.</text>
  <rect class="dg-group" x="20" y="86" width="230" height="110" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">TRIGGER</text>
  <rect class="dg-box" x="36" y="118" width="200" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="136" y="138.5">Git host web hook</text>
  <text class="dg-s dg-c" x="136" y="154.5">POST /runs { repo, sha, ref }</text>
  <text class="dg-s dg-c" x="136" y="170.5">supersedes the old run, same txn</text>
  <rect class="dg-group" x="270" y="86" width="410" height="206" rx="12"></rect>
  <text class="dg-group-t" x="286" y="108">SCHEDULER — STATELESS, LEADER-LEASED</text>
  <rect class="dg-box" x="286" y="118" width="180" height="80" rx="8"></rect>
  <text class="dg-t dg-c" x="376" y="138.5">Resolver → counters</text>
  <text class="dg-s dg-c" x="376" y="154.5">~200 steps · deps_remaining</text>
  <text class="dg-s dg-c" x="376" y="170.5">cache_key per step, up front</text>
  <text class="dg-s dg-c" x="376" y="186.5">hits → CACHED, never lease</text>
  <rect class="dg-box" x="486" y="118" width="178" height="80" rx="8"></rect>
  <text class="dg-t dg-c" x="575" y="138.5">Lease + complete</text>
  <text class="dg-s dg-c" x="575" y="154.5">SKIP LOCKED grant · token</text>
  <text class="dg-s dg-c" x="575" y="170.5">run superseded? → skip</text>
  <text class="dg-s dg-c" x="575" y="186.5">decrement dependants</text>
  <rect class="dg-good" x="286" y="214" width="378" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="475" y="238.5">Heartbeat reply · sweeper · fair share</text>
  <text class="dg-s dg-c" x="475" y="254.5">continue | cancel — the only downward channel</text>
  <text class="dg-s dg-c" x="475" y="270.5">3 missed beats → re-queue once · fair share when queued</text>
  <path class="dg-box" d="M 710,125 L 710,279 A 135,7 0 0 0 980,279 L 980,125 A 135,7 0 0 0 710,125 Z"></path>
  <path class="dg-box" d="M 710,125 A 135,7 0 0 0 980,125" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="178">Postgres — runs, steps, edges, queue</text>
  <text class="dg-s dg-c" x="845" y="194">steps (run_id, state) · deps_remaining</text>
  <text class="dg-s dg-c" x="845" y="210">lease_token · version · attempt</text>
  <text class="dg-s dg-c" x="845" y="226">merge_queue (repo, position)</text>
  <text class="dg-s dg-c" x="845" y="242">partitioned by month · leader lease row</text>
  <path class="dg-line" d="M 136,118 L 136,72 L 845,72 L 845,110"></path>
  <path class="dg-head" d="M 840,110 L 850,110 L 845,118 Z"></path>
  <text class="dg-lbl dg-c" x="490" y="66">run + SUPERSEDED, one transaction</text>
  <path class="dg-line" d="M 664,150 L 702,150"></path>
  <path class="dg-head" d="M 702,155 L 702,145 L 710,150 Z"></path>
  <path class="dg-line" d="M 664,250 L 702,250"></path>
  <path class="dg-head" d="M 702,255 L 702,245 L 710,250 Z"></path>
  <rect class="dg-group" x="20" y="320" width="330" height="150" rx="12"></rect>
  <text class="dg-group-t" x="36" y="342">CACHE — THE PRODUCT</text>
  <path class="dg-box" d="M 36,359 L 36,445 A 70,7 0 0 0 176,445 L 176,359 A 70,7 0 0 0 36,359 Z"></path>
  <path class="dg-box" d="M 36,359 A 70,7 0 0 0 176,359" style="fill:none"></path>
  <text class="dg-t dg-c" x="106" y="386">Redis index</text>
  <text class="dg-s dg-c" x="106" y="402">cache_key → digest</text>
  <text class="dg-s dg-c" x="106" y="418">LRU 14 d on last_hit</text>
  <text class="dg-s dg-c" x="106" y="434">rebuilt from S3</text>
  <path class="dg-box" d="M 196,359 L 196,445 A 75,7 0 0 0 346,445 L 346,359 A 75,7 0 0 0 196,359 Z"></path>
  <path class="dg-box" d="M 196,359 A 75,7 0 0 0 346,359" style="fill:none"></path>
  <text class="dg-t dg-c" x="271" y="386">S3 — outputs</text>
  <text class="dg-s dg-c" x="271" y="402">content-addressed</text>
  <text class="dg-s dg-c" x="271" y="418">refcounted · 30 d GC</text>
  <text class="dg-s dg-c" x="271" y="434">5 TB/day in</text>
  <path class="dg-line" d="M 196,402 L 184,402"></path>
  <path class="dg-head" d="M 184,397 L 184,407 L 176,402 Z"></path>
  <path class="dg-line" d="M 106,352 L 106,250 L 278,250"></path>
  <path class="dg-head" d="M 278,255 L 278,245 L 286,250 Z"></path>
  <text class="dg-lbl" x="112" y="244">resolve keys before scheduling</text>
  <rect class="dg-group" x="390" y="320" width="300" height="150" rx="12"></rect>
  <text class="dg-group-t" x="406" y="342">RUNNERS ×6 000 AT 09:00</text>
  <rect class="dg-box" x="406" y="352" width="270" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="541" y="368.5">microVM per step — destroyed after</text>
  <text class="dg-s dg-c" x="541" y="384.5">poll for lease · fetch inputs by digest</text>
  <text class="dg-s dg-c" x="541" y="400.5">scoped secrets token · egress allow-list</text>
  <rect class="dg-warn" x="406" y="420" width="270" height="40" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="541" y="436.5">Pool controller</text>
  <text class="dg-s dg-c" x="541" y="452.5">boots to yesterday's curve, 30 min ahead</text>
  <path class="dg-line" d="M 406,372 L 354,372"></path>
  <path class="dg-head" d="M 354,367 L 354,377 L 346,372 Z"></path>
  <text class="dg-lbl dg-c" x="376" y="364">write</text>
  <path class="dg-line" d="M 346,400 L 398,400"></path>
  <path class="dg-head" d="M 398,405 L 398,395 L 406,400 Z"></path>
  <text class="dg-lbl dg-c" x="376" y="414">read</text>
  <path class="dg-line" d="M 540,352 L 540,312 L 760,312 L 760,294"></path>
  <path class="dg-head" d="M 765,294 L 755,294 L 760,286 Z"></path>
  <text class="dg-lbl dg-c" x="650" y="307">lease · heartbeat / 10 s · complete</text>
  <path class="dg-box" d="M 710,327 L 710,373 A 135,7 0 0 0 980,373 L 980,327 A 135,7 0 0 0 710,327 Z"></path>
  <path class="dg-box" d="M 710,327 A 135,7 0 0 0 980,327" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="350">Logs — stream 10 min, then S3 90 d</text>
  <text class="dg-s dg-c" x="845" y="366">2 s batches · key logs/{run}/{step}/{attempt}</text>
  <path class="dg-line" d="M 676,380 L 692,380 L 692,350 L 702,350"></path>
  <path class="dg-head" d="M 702,355 L 702,345 L 710,350 Z"></path>
  <rect class="dg-box" x="710" y="392" width="270" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="845" y="410.5">Merge queue — only writer to main</text>
  <text class="dg-s dg-c" x="845" y="426.5">rows in Postgres · speculative batch 8–16</text>
  <text class="dg-s dg-c" x="845" y="442.5">bisect on red · a run with trigger: merge_queue</text>
  <path class="dg-box" d="M 710,471 L 710,507 A 135,7 0 0 0 980,507 L 980,471 A 135,7 0 0 0 710,471 Z"></path>
  <path class="dg-box" d="M 710,471 A 135,7 0 0 0 980,471" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="489">Kafka → ClickHouse</text>
  <text class="dg-s dg-c" x="845" y="505">transitions · flake rate per test · cost</text>
  <text class="dg-s" x="20" y="528">Cancellation is never a message: the run's state is read on every lease and every heartbeat reply, so a dead scheduler loses nothing.</text>
  <text class="dg-s" x="20" y="550">Hits never lease. The cache key is content plus toolchain, never the commit, and only trusted refs may write it.</text>
  <text class="dg-note" x="20" y="572">Five thousand pushes a day is a decoy; a million steps, ten times that at 09:00, and a runner per step is the load.</text>
</svg>
</div>

<p class="diagram-cap">Draw the step state machine first, then this. The resolver's second line — keys resolved before anything schedules — is the cost story, the heartbeat reply is the cancel story, and the merge queue's box is why green on the branch is not green on main. Nothing on the board keeps a graph in memory.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 580" role="img" aria-label="CI/CD flows in three lanes. Second push: a new run is created and the old one superseded in the same transaction; forty ready steps never lease, thirty running steps get cancel on their next heartbeat within ten seconds, and fifty completed outputs are cache hits for the new run; a runner that completes at the same instant is accepted because its token is still valid. The nine o'clock spike: the pool boots from eight hundred to six thousand thirty minutes ahead, queue wait stays under a minute, and when a toolchain release drops the cache hit rate to five percent fair share by team keeps one matrix build from owning the pool while wait rises to eight minutes with a banner. Merge queue: eight pull requests become one speculative commit, green lands all eight; red bisects into halves in parallel, ejects the culprit, and lands the seven innocents at a cost of about thirty minutes.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Supersede in one transaction and cancel on the heartbeat reply; size the pool for 09:00; batch the merge and bisect the red one.</text>
  <text class="dg-lane" x="30" y="76">SECOND PUSH — SUPERSESSION RACES THE LEASES</text>
  <rect class="dg-box" x="30" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="135" y="114.5">POST /runs, push 2</text>
  <text class="dg-s dg-c" x="135" y="130.5">run 2 inserted · run 1 SUPERSEDED</text>
  <text class="dg-s dg-c" x="135" y="146.5">one transaction</text>
  <rect class="dg-good" x="270" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="375" y="114.5">40 READY never lease</text>
  <text class="dg-s dg-c" x="375" y="130.5">lease grant reads run state</text>
  <text class="dg-s dg-c" x="375" y="146.5">swept to CANCELLED</text>
  <path class="dg-line" d="M 240,126 L 262,126"></path>
  <path class="dg-head" d="M 262,131 L 262,121 L 270,126 Z"></path>
  <rect class="dg-box" x="510" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="114.5">30 RUNNING → cancel ≤ 10 s</text>
  <text class="dg-s dg-c" x="620" y="130.5">on the heartbeat reply</text>
  <text class="dg-s dg-c" x="620" y="146.5">VM destroyed · 50 done = cache hits</text>
  <path class="dg-line" d="M 480,126 L 502,126"></path>
  <path class="dg-head" d="M 502,131 L 502,121 L 510,126 Z"></path>
  <rect class="dg-warn" x="760" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="870" y="114.5">one completes at that instant</text>
  <text class="dg-s dg-c" x="870" y="130.5">token still valid → accepted</text>
  <text class="dg-s dg-c" x="870" y="146.5">a correct output, cached</text>
  <path class="dg-line" d="M 730,126 L 752,126"></path>
  <path class="dg-head" d="M 752,131 L 752,121 L 760,126 Z"></path>
  <text class="dg-s" x="30" y="190">No kill list exists to lose. A scheduler that dies mid-cancel changed nothing, because supersession is a row every lease consults.</text>
  <path class="dg-div" d="M 20,206 L 980,206"></path>
  <text class="dg-lane" x="30" y="240">09:00 — THE POOL, AND THE DAY THE CACHE GOES COLD</text>
  <rect class="dg-box" x="30" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="175" y="278.5">08:30 · boot ahead of the curve</text>
  <text class="dg-s dg-c" x="175" y="294.5">800 → 6 000 microVMs in 30 min</text>
  <text class="dg-s dg-c" x="175" y="310.5">base image: last night's checkout</text>
  <rect class="dg-good" x="350" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="278.5">09:00–10:00 · 5 200 running</text>
  <text class="dg-s dg-c" x="495" y="294.5">queue wait p95 40 s · pool 90 % busy</text>
  <text class="dg-s dg-c" x="495" y="310.5">drains by disposal after 10:15</text>
  <path class="dg-line" d="M 320,290 L 342,290"></path>
  <path class="dg-head" d="M 342,295 L 342,285 L 350,290 Z"></path>
  <rect class="dg-warn" x="670" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="815" y="278.5">toolchain release: hits 60 % → 5 %</text>
  <text class="dg-s dg-c" x="815" y="294.5">demand 2.5 × pool · fair share by team</text>
  <text class="dg-s dg-c" x="815" y="310.5">wait p95 8 min, with a banner</text>
  <path class="dg-line" d="M 640,290 L 662,290"></path>
  <path class="dg-head" d="M 662,295 L 662,285 L 670,290 Z"></path>
  <text class="dg-s" x="30" y="350">A pool sized for the average is a forty-minute queue at nine. A pool sized for the peak idles at nine percent. Yesterday's curve, thirty minutes ahead, is the answer.</text>
  <path class="dg-div" d="M 20,366 L 980,366"></path>
  <text class="dg-lane" x="30" y="400">MERGE QUEUE — SPECULATE, THEN BISECT</text>
  <rect class="dg-box" x="30" y="414" width="220" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="434.5">8 PRs click merge</text>
  <text class="dg-s dg-c" x="140" y="450.5">one speculative commit:</text>
  <text class="dg-s dg-c" x="140" y="466.5">main + 1 … + 8</text>
  <rect class="dg-good" x="270" y="414" width="230" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="385" y="434.5">green in 10 min → all 8 land</text>
  <text class="dg-s dg-c" x="385" y="450.5">fast-forward main</text>
  <text class="dg-s dg-c" x="385" y="466.5">48/h at batch 8 · 300/h speculating</text>
  <path class="dg-line" d="M 250,446 L 262,446"></path>
  <path class="dg-head" d="M 262,451 L 262,441 L 270,446 Z"></path>
  <rect class="dg-box" x="520" y="414" width="220" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="630" y="434.5">red → bisect in parallel</text>
  <text class="dg-s dg-c" x="630" y="450.5">main + 1–4 · main + 5–8</text>
  <text class="dg-s dg-c" x="630" y="466.5">green half lands</text>
  <path class="dg-line" d="M 500,446 L 512,446"></path>
  <path class="dg-head" d="M 512,451 L 512,441 L 520,446 Z"></path>
  <rect class="dg-warn" x="760" y="414" width="220" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="870" y="434.5">culprit ejected, 7 land</text>
  <text class="dg-s dg-c" x="870" y="450.5">≈ 30 min cost to neighbours</text>
  <text class="dg-s dg-c" x="870" y="466.5">a flake here is a stall</text>
  <path class="dg-line" d="M 740,446 L 752,446"></path>
  <path class="dg-head" d="M 752,451 L 752,441 L 760,446 Z"></path>
  <text class="dg-note" x="30" y="520">The queue is the only writer to main. That is what turns 'main is green' from a norm into a property of the system.</text>
</svg>
</div>

<p class="diagram-cap">The top lane's fourth box is the one interviewers probe — a completion under a superseded run is accepted, and the only refused completion is a stale token. The middle lane is where the pushes-per-day number dies, and the bottom lane's arithmetic is the throughput of main.</p>

### Flow A — a push, start to green

1. The git host posts the push event. `POST /runs` inserts the run, marks any active run on the same ref `SUPERSEDED` in the same transaction (§7), and enqueues one job: *resolve the pipeline*.
2. A resolver runner checks out the pipeline definition at that commit and returns a DAG: ~200 steps and their edges. The scheduler inserts the steps with `deps_remaining` set from the edges, computes each step's `cache_key` from its declared inputs at that commit (§8), and marks every step whose key is already in the cache index `CACHED`. **Typically 120 of the 200 never run.**
3. Steps with `deps_remaining = 0` go `READY`. Warm runners polling `POST /runners/{id}/lease` receive them within a second, along with input digests and a scoped secrets token. Each runner fetches inputs by digest, executes, streams logs (§11), and calls `complete` with output digests.
4. On each completion the scheduler decrements `deps_remaining` on the dependants, marking any that hit zero `READY`. The run finishes when every step is terminal; a green run on a trusted ref writes its outputs to the cache index and hands the final artifact digest to deployment.
5. **The failure path.** A unit-test step exits non-zero at minute six. The step goes `FAILED`; its dependants stay `PENDING` and are marked `SKIPPED` when the run closes; steps already running on other branches of the DAG finish, because their results are still useful to the engineer reading the page. The run is `FAILED` in about eight minutes, and the engineer sees exactly which step, with its log.

### Flow B — a second push, and the lease that races it

1. Twenty minutes later, a new push on the same branch. `POST /runs` creates run 2 and sets run 1 `SUPERSEDED`. Run 1 has 40 steps `READY`, 30 `RUNNING`, 50 done.
2. The 40 `READY` steps never lease: **every lease grant reads the run's state** and skips superseded runs, so they are marked `CANCELLED` lazily by the sweeper. The 30 `RUNNING` steps get `action: cancel` on their next heartbeat reply, within 10 s, kill their process, and the microVM is destroyed.
3. Run 2's cache lookup finds the 50 done steps' outputs — the ones whose inputs did not change — as hits. **The old run's completed work is not wasted; it is cached.**
4. **The failure path.** One of the 30 runners finishes its step at the same moment the cancel is decided and calls `complete`. Its `lease_token` is still valid — cancellation has not revoked it — so the completion is accepted and the output is recorded. It is a valid result for that input; run 2 may hit it in the cache. The step's state is `SUCCEEDED` under a `SUPERSEDED` run, and that is correct. What is refused is a completion whose token was revoked by a lease timeout, which is the fencing case (§7).

### Flow C — the 09:00 spike

1. 08:30. The pool controller reads yesterday's curve and starts booting microVMs: from 800 to 6 000 over thirty minutes (§9).
2. 09:00–10:00. 50 000 pushes land in the hour. ~5 200 steps are running at any moment; queue wait p95 is 40 s. The pool is 90 % busy.
3. 10:15. Demand falls. Runners that finish a step are destroyed, not returned, so the pool drains to demand naturally; the controller stops booting replacements.
4. **The failure path.** A build-tool release makes every step miss the cache at once — the toolchain hash is part of the key (§8). Hit rate drops from 60 % to 5 %; demand is 2.5 × the pool. The scheduler applies **fair share by team** to the `READY` queue: no team's steps take more than their share of leases while the queue is non-empty, so one team's 400-step matrix does not starve everyone. Queue wait p95 is 8 minutes for an hour, and every engineer sees a banner that says so. Nothing is dropped.

### Flow D — the merge queue lands a batch

1. Eight pull requests click merge within a minute. Each becomes a `merge_queue_entry`. The queue builds a **speculative commit**: main + PR 1 + … + PR 8, and triggers a run on it with `trigger: merge_queue`.
2. The run is green in 10 minutes. The queue fast-forwards main to the speculative commit; all eight land. Throughput: 48 an hour at batch size 8, and the queue grows batches up to 16 when its length exceeds 30 (§10).
3. **The failure path.** The run is red. The queue does not know which of the eight broke it, so it **bisects**: two speculative runs, main + 1–4 and main + 5–8, in parallel. One is green and lands; the other splits again. The culprit is ejected with its log after at most three more rounds, and the seven innocents land. The cost of one bad PR in a batch of eight is about 30 minutes of queue delay for its neighbours, which is the number that sets the batch size.

### Flow E — a runner dies mid-step

1. A runner heartbeated at 09:14:00 and never again. At 09:14:30 the scheduler's sweeper sees the missed heartbeats, marks the step's lease expired, and re-queues it as attempt 2 with a **new `lease_token`**.
2. Attempt 2 leases to another runner and finishes at 09:19.
3. **The failure path.** The first runner was not dead; its network was. It comes back at 09:16 and calls `complete` with the old token. **409, stale token.** Its output is discarded even though it may have been correct, because two accepted completions for one step would let the second overwrite the first's outputs after dependants had already read them. *The Job scheduler's fencing token, unchanged.*

---

## 7 · Deep dive — the DAG is counters, and supersession is a state, not a kill

### What you'd reach for first

A scheduler that holds each run's DAG in memory, walks it on every completion to find newly unblocked steps, and on supersession iterates the run's steps and sends each runner a kill.

### What breaks

Two things, both at 09:00. **The in-memory graph is state that a scheduler restart loses:** with 5 000 active runs of 200 steps, rebuilding a million nodes from rows takes minutes, during which nothing schedules. And **the kill is edge-triggered:** a scheduler that dies after sending 12 of 30 kills leaves 18 runners burning capacity on a superseded run, and nothing ever tells them. At 09:00 those 18 are the difference between a 40 s and a 4 min queue wait for someone else.

### What replaces it

**Counters in rows.** Each step carries `deps_remaining`; run creation sets it from the edge list once. A completion does one `UPDATE steps SET deps_remaining = deps_remaining - 1 WHERE run_id = ? AND id IN (dependants)` and then `UPDATE … SET state = READY WHERE deps_remaining = 0 AND state = PENDING`. No graph in memory; a scheduler replica is stateless and resumes from rows in seconds. The dependants of a step are a single indexed read on `edges`.

**Supersession as a state that leases consult.** `POST /runs` sets `superseded_by` on the old run in the same transaction that inserts the new one. Every lease grant joins the step to its run and skips runs that are superseded; every heartbeat reply reads the run's state and returns `cancel` if it is. No kill message exists. A runner that missed the reply finds out on the next one, ten seconds later. A scheduler that dies mid-cancel has lost nothing, because there was never a list of kills to lose.

**The lease and the fencing token.** A `RUNNING` step carries a `lease_token` renewed on each heartbeat; three missed heartbeats expire it and re-queue the step once with a new token. Completions present the token; a stale one is a 409. This is the Job scheduler's mechanism and this page does not re-derive it.

**→ ties to the supersession-latency NFR:** 30 s is three heartbeats, and the heartbeat reply is the only channel, so it cannot be faster without a faster heartbeat.

### What it costs

- **Up to 10 s of wasted runner time per cancelled step,** and a step that ignores the cancel keeps its VM until the step timeout. The VM is destroyed at timeout regardless; the cost is bounded.
- **A completed step under a superseded run is accepted** (Flow B). It is a correct result for its inputs and it goes in the cache. Anyone who expects a cancelled run to have no green steps has to be told why it does.
- **Attempt 2 re-executes side effects.** A step that published a package on attempt 1 and then lost its lease publishes twice. Steps with external side effects declare `retries: 0`, and the platform's own outputs are content-addressed so a duplicate write is a no-op.

---

## 8 · Deep dive — the cache is the product, and the commit hash is the wrong key

### What you'd reach for first

Cache each step's output under `(step name, commit sha)`. It is what every hand-rolled CI does first.

### What breaks

**The hit rate is zero.** Every push is a new sha, so nothing ever matches, and the "cache" is a way to re-download your own outputs within one run. The second version people build, `(step name, hash of the step's source directory)`, hits within a team but misses whenever a dependency two directories away changes — and it is *wrong* when a dependency changes and the directory does not, which is worse than a miss: it serves a stale build as current.

### What replaces it

**A content-addressed key over the step's transitive inputs.** `cache_key = hash(sorted(input file digests) ‖ toolchain digest ‖ step command ‖ env allow-list)`. The inputs are what the pipeline definition declares — the build tool already knows them, which is why Bazel and its relatives get this for free and a YAML pipeline does not unless it says. The toolchain digest is in the key because a compiler upgrade must miss everything (Flow C's failure path). Outputs are stored by their own digest in object storage; the index maps `cache_key → output_digest`, and a hit means the runner fetches the output by digest and the step goes `CACHED` without leasing.

**Only trusted runs write.** A pull request can contain a step that produces a plausible-looking but hostile output. If that output were cached under the key the main branch would compute, main's next run serves it. So: **the index is written only when `run.trusted`**, which means main and release branches, and pull-request runs read the index but never write it. A PR's steps are still cached *within the PR's own runs* under a namespace keyed by the PR, so the second push benefits from the first.

**Eviction by last hit, not by age.** A 14-day LRU on `last_hit` keeps the outputs everyone builds against, and evicts a branch's leftovers in two weeks. At 5 TB/day of writes that is ~70 TB, and a hit rate that stays around 60 %.

**→ ties to the cache-hit-latency NFR:** the index is one Redis lookup and the fetch is a parallel range download from object storage; a 500 MB output at 200 MB/s is under 3 s.

### What it costs

- **The pipeline definition has to declare inputs honestly.** A step that reads a file it did not declare gets a stale hit when that file changes. This is the entire engineering cost of a good CI system and it never ends; the platform's job is to make undeclared reads fail (the runner mounts only declared inputs), which is a real and unpopular constraint.
- **Non-hermetic steps cannot be cached.** Anything that reads the clock, the network, or a random seed produces a different output from the same key. Those steps are marked `cache: false` and they are the ones that make the critical path.
- **Two-tier trust halves the hit rate for PRs on first push.** A PR's first run can hit main's entries for unchanged inputs and nothing else. That is the correct trade and it is stated as one.

---

## 9 · Deep dive — ephemeral untrusted runners, and the pool that is sized for nine o'clock

### What you'd reach for first

A fleet of long-lived build machines, each running steps in a container, reused between steps. It is fast, because the checkout and the toolchain are already there.

### What breaks

**Reuse is the vulnerability.** A step from one pull request can leave a modified binary in a shared toolchain directory, a background process holding a socket, or a cron entry, and the next step on that machine — from another team, with that team's secrets — runs into it. Containers share a kernel; a kernel exploit in one PR's test is a compromise of every runner it touches. And the fixed fleet is either idle at 3 am or queued at 9 am, with nothing in between.

### What replaces it

**One microVM per step, destroyed after.** Firecracker or a similar VMM: a ~1 s boot from a snapshot, a kernel boundary, no network route to other runners, egress only to the artifact store, the cache, the scheduler, and an allow-list. Secrets arrive as a token scoped to that step and that run's trust level, valid for the step's timeout. Nothing survives the step. **The Hosted notebooks page's §15 row is this runner**; the mechanism is not restated here.

**A warm pool ahead of the curve.** Booting is cheap but not free at 6 000 in thirty minutes, and checkout is not cheap. The pool controller boots VMs to a target derived from the same hour yesterday, thirty minutes ahead, and keeps a **base image with the monorepo already checked out at last night's main** — a push's checkout is then a fetch of one commit's delta. Runners poll for leases; a runner that has waited 10 minutes idle is destroyed, so the pool drains with demand.

**Fair share when the queue is non-empty.** Leases are granted round-robin across teams weighted by quota, only when there is a queue. At 3 am nobody queues and nobody notices; at 9 am with a cold cache (Flow C) it is what stops one matrix build from owning the pool.

**→ ties to the time-to-first-step NFR:** 60 s is only achievable with a booted VM holding a checkout. Cold, it is 90 s before the step starts.

### What it costs

- **A VM per step is ~10 % overhead on a 3-minute step** and ~50 % on a 10-second one. Tiny steps get batched into one step by the pipeline definition, or accept the overhead.
- **The warm pool idles.** Booting ahead of demand means paying for VMs that may not be used; at 09:00 the predictive error is ~10 %, and a wrong prediction is a queue, not an outage.
- **Nothing persists between steps on a runner,** so every step pays for its inputs. That is what the cache and the artifact store are for, and it is why they have to be fast.

---

## 10 · Deep dive — the merge queue, because green on the branch is not green on main

### What you'd reach for first

Require a green run on the pull request, then let the engineer push to main.

### What breaks

**The green run tested the PR against main as of when the branch was last rebased.** Two PRs that are each green against yesterday's main can each rename the same function and break main when both land. At 200 merges an hour it happens daily. The first fix people try, "rebase and re-run before merge", is correct and serialises main at six merges an hour with a 10-minute pipeline.

### What replaces it

**A queue that tests speculatively.** A merge is an entry with a position. The queue builds a speculative commit of main plus every entry ahead of this one plus this one, runs it, and lands entries in order as their speculative runs go green. **Batching:** with a queue of 30, the head 8 are tested as one commit; green lands all 8, and the batch size grows to 16 when the queue is long. **Speculation:** while batch 1 is testing, batch 2 is tested on top of the *assumption* that batch 1 is green, so a green streak lands 8 every 10 minutes with 3 batches in flight and 96 an hour becomes 300. **Bisection on red** (Flow D): split the batch, test halves in parallel, eject the culprit, land the innocents. A red batch costs its neighbours ~30 minutes.

**The queue is the only writer to main.** Direct pushes are rejected by the git host. That is what makes "main is green" a property of the system rather than a norm.

**→ ties to the merge-throughput NFR:** 200 an hour needs batches of at least 8 with speculation depth 3, and the math is on the board.

### What it costs

- **A merge takes at least one pipeline duration**, even when the queue is empty, because the speculative commit differs from anything already tested.
- **Speculation wastes work when a batch is red:** every batch tested on top of it is discarded and re-run. At a 5 % red rate that is ~15 % extra pipeline runs, which is why batches are not 64.
- **A flaky test is a queue stall.** One 2 % flake in a batch of 8 makes 15 % of batches red for no reason, and each costs 30 minutes. The merge queue is where flakes become expensive enough to be fixed, and the flake budget (§11) is enforced here first.

---

## 11 · Deep dive — logs, artifacts, and the flake budget

### What you'd reach for first

Runners write logs to a database table keyed by step, and a failed step is retried up to three times because tests are flaky.

### What breaks

500 GB a day of log lines is the hottest table in the company by a hundred times, indexed on something nobody queries. And three automatic retries turn a 2 % flake into a 0.0008 % failure, which sounds like a fix and is actually **a policy that spends 6 % more runner time forever and hides every flaky test from the people who could fix it**, until the merge queue (§10) turns those flakes into stalls.

### What replaces it

**Logs stream to object storage with a small index.** The runner appends 2-second batches to a per-step stream (a Redis stream or a Kafka topic partitioned by step) that the live-tail UI reads; on completion the runner uploads the full log to S3 at `logs/{run}/{step}/{attempt}` and the stream is deleted after 10 minutes. Postgres holds one row per step with the S3 key and the byte size. Search is per step, from the object. Retention: 90 days in standard storage, then deleted; a step's *result* is kept for a year, its log is not.

**Artifacts are content-addressed and reference-counted.** Every output is stored under its digest; the step row lists the digests. Deduplication is free, and the artifact a green main run hands to deployment is a digest that the deployment system pins (its Flow C). Unreferenced artifacts are garbage-collected after 30 days; those referenced by a cache entry live as long as the entry.

**Retry is a budget, not a reflex.** A step marked `flaky: true` by its owner is retried once, and the retry is recorded as a flake with its log. The platform publishes a per-test flake rate; a test above 1 % is quarantined — run but not counted — and its owner is paged by the dashboard, not by the queue. Steps not marked flaky are not retried automatically; the engineer clicks retry, and the click is counted.

### What it costs

- **Live tail has a 2-second lag and a 10-minute lifetime;** a step that ran an hour ago is read from S3, which takes a second to start. Nobody has ever noticed.
- **Quarantine hides real failures** in a test that was flaky *and* then broke. The quarantine has a 7-day limit, after which the test is either fixed or deleted, and that is a rule with owners.
- **The flake budget is politically expensive.** Someone gets a dashboard that says their test is the reason main is slow. That is the point, and the platform team has to be willing to publish it.

---

## 12 · Data model, sharding, and storage decisions

**One Postgres primary, partitioned by time.** Runs and steps are ~1 M rows a day; at 200 bytes a step that is 200 MB/day, and the working set is the active runs, a few thousand at 09:00. Every query is per run — `WHERE run_id = ?` — so the tables partition by `created_at` month for retention and index on `(run_id, state)`. The one cross-run query is the lease grant: `SELECT … FROM steps WHERE state = 'READY' AND pool = ? ORDER BY priority, created_at FOR UPDATE SKIP LOCKED LIMIT 1`, at ~50 a second peak, which one primary answers without noticing. **The hot row** is the run's `state`, read by every lease and heartbeat; it is one row per run, cached in Redis for 5 s, and its writes are two per run.

**What is not in Postgres, on purpose.** Log bytes, artifact bytes, cache outputs, the live-tail stream, runner liveness. The database holds the DAG and its transitions.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Runs, steps, edges** | Insert 200 rows per push; CAS per transition; `deps_remaining` decrement per completion; lease grant by `SKIP LOCKED` | **System of record**; 1 year | **Postgres**, partitioned by month, index `(run_id, state)` and `(state, pool, priority, created_at)` | "It's a few hundred writes a second and every query is per run. Kafka as the ready queue gives me ordering I don't want and takes away `SKIP LOCKED`, which is the scheduler" |
| **Run state cache** | Read on every lease and heartbeat; two writes per run | Ephemeral, 5 s TTL | **Redis** | "Five seconds stale on `SUPERSEDED` is inside the 30 s NFR" |
| **Cache index** | 1 M lookups/day; 250 k writes; eviction by `last_hit` | Rebuildable from object storage listing; 14 days | **Redis Cluster** `cache_key → output_digest`, with the entry also written as an S3 object for rebuild | "Postgres works at this rate too. Redis because the lookup is on the critical path of every step and a rebuild is a listing, not a restore" |
| **Cache outputs, artifacts** | Write once by digest; parallel range reads | Durable; refcounted; 14-day LRU for cache, 30-day GC for unreferenced artifacts | **S3** (or GCS), content-addressed | "Content-addressed means dedup is free and a duplicate write from a retry is a no-op" |
| **Logs, live** | Append 2 s batches; one reader | 10 minutes | **Redis stream** per step, or Kafka partitioned by step id at larger scale | "It exists so the engineer can watch. It is deleted when the object exists" |
| **Logs, complete** | Write once; read per step | 90 days | **S3**, key `logs/{run}/{step}/{attempt}`; Postgres holds the key | "Five hundred gigabytes a day of text nobody queries across. Elasticsearch here is the most expensive mistake on the page" |
| **Runner liveness** | Heartbeat every 10 s from ~6 000 runners; expiry is the event | Ephemeral | **Redis** `SET runner:{id} EX 30`; the step's lease expiry is the row's `lease_expires_at`, checked by the sweeper | "The runner is disposable. Losing its liveness record means a step re-queues, which is the same thing that happens if it dies" |
| **Runner pool** | Target size per pool per minute; boot and destroy | Derived from history | **The pool controller's own Postgres table** plus the cloud API | "Yesterday's curve, thirty minutes ahead, and a VM that idles ten minutes is destroyed" |
| **Merge queue** | Insert per merge click; batch assembly; reorder on eject | System of record | **Postgres**, same primary; `(repo, position)` | "A few thousand rows. It's a table with an `ORDER BY`" |
| **Events** | Append per transition; dashboards, cost attribution, flake rates | 2 years | **Kafka → ClickHouse** | "The flake rate per test is a `GROUP BY` over a year of attempts. That's not a Postgres query" |
| **Scheduler leader lease** | Renewed every 5 s; CAS to acquire | Durable | **A row in Postgres** | "Replicas are stateless; the sweeper and the pool controller run on the leader" |

### Data lifecycle — the append-only entities

| Entity | Growth | Hot | Warm | Cold | Restore |
|---|---|---|---|---|---|
| **Steps** | 1 M/day | 90 days in Postgres, partitioned by month | — | ClickHouse, 2 years | `GET /runs/{id}` falls through; seconds |
| **Logs** | 500 GB/day | S3 standard, 90 days | — | **Deleted** | None. The result survives; the log does not, and that is stated |
| **Cache outputs** | 5 TB/day | S3, LRU 14 days on `last_hit` | — | Evicted | A miss. Never a failure |
| **Artifacts** | ~1 TB/day after dedup | S3; refcounted | S3 IA after 30 days if referenced by a release | GC when unreferenced | Minutes; a release artifact is pinned by the deployment system |
| **Events** | ~5 M/day | ClickHouse, 2 years | — | Dropped | n/a |

### The signals that tell you this is broken

- **Queue wait p95 per pool** — the pool is under-sized or the prediction missed.
- **Cache hit rate, per step name** — a step whose hit rate fell is a step whose inputs are declared wrong, or a toolchain change.
- **Superseded-step runner-minutes** — capacity spent on runs nobody read; should be near zero past 30 s of supersession.
- **Merge queue depth and red-batch rate** — the second one is almost always a flake.
- **Stale-token 409 rate** — runners losing their network, or a sweeper that is too eager.

---

## 13 · Traps — the ranked list

**Design traps**

1. **"It's the job scheduler with a web hook."** Independent jobs have no edges, no supersession, and no cache. The scheduler page is the lease; this page is everything around it (§7, §8).
2. **Cache keyed by commit sha.** Zero hits. Keyed by source directory: wrong hits. Content-addressed over declared transitive inputs plus toolchain, or nothing (§8).
3. **Pull requests may write the shared cache.** One hostile PR poisons main's next build. Trusted refs write; everyone reads (§8).
4. **Cancel as a kill message.** Edge-triggered, lost when the sender dies. Supersession is a run state that every lease and heartbeat reply consults (§7).
5. **Long-lived shared runners.** Cross-PR contamination and a shared kernel. One microVM per step, destroyed after (§9).
6. **Merge gated on "the PR is green."** Green against stale main. A queue that tests speculatively and is the only writer to main (§10).
7. **A pool sized for the average.** 09:00 is a forty-minute queue. Warm pool ahead of the curve, drained by disposal (§9).
8. **Three automatic retries.** Hides flakes until the merge queue makes them stalls. Retry as a budget with a published rate (§11).
9. **The DAG in the scheduler's memory.** A restart at 09:00 rebuilds a million nodes. Counters in rows (§7).
10. **A whole-pipeline timeout as the only clock.** Per-step timeouts owned by the scheduler; the pipeline's duration is the critical path and has no separate cap.

**Performance traps**

11. **Logs in a database.** 500 GB a day of text nobody queries across (§11).
12. **Cache lookup after leasing.** The runner boots, then discovers the hit. Resolve keys at run creation; hits never lease (§8).
13. **A cold checkout per step.** 90 s of the 60 s budget. The base image carries last night's main (§9).
14. **Scanning the DAG for ready steps.** `deps_remaining = 0` is an index, not a walk (§7).
15. **Merge batches of one, or of sixty-four.** Six an hour, or a 30-minute bisect on every flake (§10).

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

16. **Designing the YAML.** Twenty minutes on how a pipeline is *described* and none on how it is *executed*. The definition arrives as a DAG; say so and move on.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 450" role="img" aria-label="CI/CD five-minute skeleton. The step and run state machines across the top; then the web hook that supersedes in one transaction, Postgres with counters and skip-locked leases, and the stateless scheduler; then the cache with its content key and trust rule, the microVM runners with the pool controller, and the merge queue; then logs and artifacts, the flake budget, and a margin lane of the decoy and the durations.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="44" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="86.5">Step: PENDING → READY → LEASED → RUNNING → SUCCEEDED · CACHED · FAILED · TIMED_OUT · CANCELLED — CAS on version, lease_token on complete</text>
  <text class="dg-s dg-c" x="495" y="102.5">Run: CREATED → RUNNING → SUCCEEDED | FAILED | SUPERSEDED — set by the next run's insert, same transaction</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="30" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="148.5">Web hook + resolver</text>
  <text class="dg-s dg-c" x="180" y="164.5">POST /runs supersedes, one txn</text>
  <text class="dg-s dg-c" x="180" y="180.5">definition at sha → ~200 steps + edges</text>
  <circle class="dg-num" cx="30" cy="128" r="9"></circle>
  <text class="dg-num-t" x="30" y="131.4">2</text>
  <rect class="dg-box" x="350" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="148.5">Postgres — runs, steps, edges, queue</text>
  <text class="dg-s dg-c" x="500" y="164.5">deps_remaining · (run_id, state)</text>
  <text class="dg-s dg-c" x="500" y="180.5">lease by SKIP LOCKED · by month · no logs</text>
  <circle class="dg-num" cx="350" cy="128" r="9"></circle>
  <text class="dg-num-t" x="350" y="131.4">3</text>
  <rect class="dg-box" x="670" y="128" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="148.5">Scheduler — stateless, leased</text>
  <text class="dg-s dg-c" x="815" y="164.5">complete → decrement → READY at 0</text>
  <text class="dg-s dg-c" x="815" y="180.5">heartbeat reply: continue | cancel</text>
  <circle class="dg-num" cx="670" cy="128" r="9"></circle>
  <text class="dg-num-t" x="670" y="131.4">4</text>
  <rect class="dg-box" x="30" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="232.5">Cache</text>
  <text class="dg-s dg-c" x="180" y="248.5">hash(inputs ‖ toolchain ‖ cmd) · trusted writes</text>
  <circle class="dg-num" cx="30" cy="208" r="9"></circle>
  <text class="dg-num-t" x="30" y="211.4">5</text>
  <rect class="dg-box" x="350" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="232.5">Runners — microVM per step, ~6 000</text>
  <text class="dg-s dg-c" x="500" y="248.5">destroyed after · pool booted 30 min ahead</text>
  <circle class="dg-num" cx="350" cy="208" r="9"></circle>
  <text class="dg-num-t" x="350" y="211.4">6</text>
  <rect class="dg-box" x="670" y="208" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="232.5">Merge queue — only writer to main</text>
  <text class="dg-s dg-c" x="815" y="248.5">speculative batch 8–16 · depth 3 · bisect</text>
  <circle class="dg-num" cx="670" cy="208" r="9"></circle>
  <text class="dg-num-t" x="670" y="211.4">7</text>
  <rect class="dg-box" x="30" y="284" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="308.5">Logs + artifacts</text>
  <text class="dg-s dg-c" x="180" y="324.5">stream 10 min → S3 90 d · digest → deploy</text>
  <circle class="dg-num" cx="30" cy="284" r="9"></circle>
  <text class="dg-num-t" x="30" y="287.4">8</text>
  <rect class="dg-box" x="350" y="284" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="308.5">Flake budget</text>
  <text class="dg-s dg-c" x="500" y="324.5">retry once if flaky: true · &gt; 1 % quarantined 7 d</text>
  <rect class="dg-box" x="670" y="284" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="308.5">Fair share</text>
  <text class="dg-s dg-c" x="815" y="324.5">by team, only while the queue is non-empty</text>
  <text class="dg-lane" x="30" y="370">9 · IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="400.5">5 000 pushes is a decoy</text>
  <text class="dg-s dg-c" x="140" y="416.5">1 M steps · 10 × at 09:00</text>
  <rect class="dg-box" x="270" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="380" y="400.5">cache hit rate is the metric</text>
  <text class="dg-s dg-c" x="380" y="416.5">60 % ≈ 1 800 runner-hours/day</text>
  <rect class="dg-box" x="510" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="400.5">step timeout 60 min</text>
  <text class="dg-s dg-c" x="620" y="416.5">lease 30 s · supersede ≤ 30 s</text>
  <rect class="dg-box" x="740" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="850" y="400.5">hits never lease</text>
  <text class="dg-s dg-c" x="850" y="416.5">keys resolved at run creation</text>
</svg>
</div>

<p class="diagram-cap">Badge 1 before any box, badge 5 before the runners — the cache is the cost story and it goes on the board before the pool does. Badge 7 is the box most candidates never draw, and the margin's first tile is the number to kill before the interviewer quotes it back.</p>

1. **The step state machine, top of the board.** `PENDING → READY → LEASED → RUNNING → SUCCEEDED`, with `CACHED` as a short-cut from `PENDING`, and `FAILED · TIMED_OUT · CANCELLED`. Beside it: *"CAS on `version`; a `lease_token` on every completion."* Per run: `CREATED → RUNNING → SUCCEEDED | FAILED | SUPERSEDED`.
2. **The web hook and the resolver.** `POST /runs` supersedes the old run **in the same transaction**. One resolver step turns the definition at that commit into ~200 steps and edges.
3. **Postgres: runs, steps, edges, merge queue.** `deps_remaining` per step; lease grant by `FOR UPDATE SKIP LOCKED`; index `(run_id, state)`. Partition by month. **No log bytes here.**
4. **The scheduler: stateless, leader-leased, level-triggered.** Completion → decrement dependants → `READY` at zero. Lease → check run not superseded → grant with token. Heartbeat reply → `continue | cancel`. Sweeper → expired leases re-queued once.
5. **The cache.** `cache_key = hash(input digests ‖ toolchain ‖ command)`. Resolved at run creation; a hit never leases. **Index in Redis, outputs in S3 by digest; trusted refs write, everyone reads.** LRU 14 days.
6. **Runners, ~6 000 at 09:00.** One microVM per step, destroyed after; base image with last night's checkout; poll for leases; scoped secrets token; egress allow-list. Pool controller boots ahead of yesterday's curve.
7. **The merge queue.** Only writer to main. Speculative commit of main + entries ahead; batch 8–16; speculation depth 3; bisect on red.
8. **Logs and artifacts.** Live tail via a per-step stream, 10 min; complete log to S3, 90 days; artifacts content-addressed and refcounted; the final digest goes to deployment.
9. **In the margin, said not drawn:** *5 000 pushes is a decoy, 1 M steps is the load · 09:00 is 10 × · cache hit rate is the metric · flake budget 1 %, quarantine 7 days · fair share only when the queue is non-empty · step timeout 60 min, lease 30 s.*

---

## 15 · Variants — what actually changes

**The governing axis: who owns the runner, and therefore how much of the page is yours.** Every row has a DAG, a trigger, a cache, and something that gates a merge. What moves is whether the platform owns the isolation and the pool (§9), or the customer does, and whether the DAG is known before the run starts.

| Product | Who owns the runner | DAG known up front? | The delta from this page |
|---|---|---|---|
| **GitHub Actions, hosted** | **The platform** | Yes, from YAML | This page as written, multi-tenant: `trusted` is per repository, the pool is shared across every customer and fair share is per account, and the cache has a per-repo quota because the platform pays for it. The merge queue is a product feature with the same bisect |
| **Buildkite, self-hosted agents** | **The customer** | Yes | §9 is not yours. The platform is §7, §8's index, §10, §11 and the UI; the customer's agents poll for leases over the internet, and isolation is their problem, stated in the contract. What you gain: no 09:00 pool to size. What you lose: the security row of §2 is a recommendation, not a guarantee |
| **Bazel remote execution** (Buildbarn, BuildBuddy) | The platform | **Yes, exactly** — the build tool computes it | §8 in its purest form: the action key is the input digests by construction, hit rates of 90 %+ are normal, and a step is an *action* of seconds, not minutes. §9's per-step VM overhead is unaffordable, so isolation is a sandbox per action on a long-lived worker, and the worker is trusted because the actions are hermetic. The merge queue is unchanged |
| **Airflow / Dagster** | The customer, usually | Yes | The trigger is a schedule, not a push, so **supersession does not exist and backfill replaces it**: a run for a past date, idempotent by `(dag, date)`. No merge queue, no untrusted code, no cache in this sense — the "cache" is the output table's partition existing. §7 survives verbatim; that is the whole overlap |
| **Zuul** (OpenStack's gating CI) | The platform | Yes | §10 is the product. Speculative testing across *many* repositories with cross-repo dependencies, so the speculative commit is a set of commits and a red batch bisects across repos. Everything else is this page |
| **A hosted notebook or a REPL** | The platform | **No** — the user decides the next step | The Hosted notebooks page. No DAG, no cache, no merge; §9's runner survives, with the idle tail as the problem instead of the 09:00 burst |

**The lesson:** the DAG and the lease are the same in every row, and they are never what distinguishes a good answer. **Who owns the runner** decides whether §9 is your hardest section or someone else's, and **whether the build tool computes the key** decides whether §8 is a solved problem or a permanent one.
