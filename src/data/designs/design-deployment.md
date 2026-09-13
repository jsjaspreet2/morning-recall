# Design a Deployment System — Fleet Reconciliation and Staged Rollout

## The question

> *"Design a deployment system. It has to deploy many different kinds of services safely, and make sure that once a service is deployed it keeps running until it is redeployed. Assume the artifact is already built and tested and sitting in storage — we only care about the deployment part. Every service at the company ships through this: about fifteen deployments a day, two thousand services, a hundred and fifty thousand machines, and the largest service runs on seventy thousand of them."*

**The product.** An engineer merges a change and wants the new version running on every machine that serves it, without taking the site down and without finding out from customers that it was broken. A different engineer owns a batch model that gets no traffic at all and just needs to be running when the nightly job calls it. Neither of them knows a single machine by name, and neither wants to. Underneath, machines die every day — a rack loses power at three in the morning, a disk fills, a kernel panics — and the service that was on them has to be somewhere else within minutes, with nobody paged. And when a deployment *is* broken, the system has to notice before most of the fleet has it, stop, and put the old version back.

**What a working system delivers**

- An engineer says *"run this artifact, seventy thousand copies, four cores and sixteen gigabytes each"* and the system finds the machines, rolls the change out a slice at a time, and stops itself if the slice looks worse than the version it is replacing.
- A machine that dies at 03:00 costs nothing but a log line: the copies it was running are back on other machines before anyone notices.
- A bad build reaches a few hundred machines, never seventy thousand, and the previous version is back on those few hundred within minutes.
- For any service, at any moment, the answer to *"what is running where, and at which version"* is one query.
- A service with no traffic still gets a meaningful "is it healthy" answer.

**Why this gets asked.** Everyone has used one and almost nobody has built one, so it cannot be answered from memory — and the two halves of the prompt pull apart the candidates who read it carefully from those who did not. "Deploy safely" is the half everyone hears. "Keep running until redeployed" is the half that is the actual system: it means a loop that never stops watching, and once you have that loop, a deployment is just one more thing it notices.

---

**Archetype:** fleet reconciliation & staged rollout — desired state is a spec and observed state is 150 k heartbeats; the system makes them equal forever, and a rollout is one more gap walked through stages with a health gate at each.
**Cousins that reuse ~70% of this page:** Kubernetes Deployments and ReplicaSets, Nomad, Borg and Tupperware, ECS services, Argo Rollouts and Spinnaker, configuration and feature-flag rollout (§15). Also **any product where a fleet has a declared state and something has to keep it there** — agent fleets, edge caches, database replicas under an operator.
**What's actually being graded:** whether the **reconciliation loop** — desired minus observed — is drawn before any endpoint; whether a deployment request is stated as **replicas plus resources** and placement as a **claim against a capacity inventory**, never "deploy to the tier"; whether the load is named as **150 k hosts heartbeating** rather than fifteen requests a day; whether staged rollout has **health gates with numbers** and a rollback that is itself a deployment; and whether **per-host and per-stage timeouts exist and a whole-rollout timeout does not**.

**Contrast to have ready:** *Demand response is one operator action fanned out to millions of targets with a deadline, reconciled once when the window closes. Here the command has no deadline and never closes: desired state is enforced indefinitely, and a host that dies at 03:00 and a release at 15:00 are the same gap, closed by the same loop. The Job scheduler places work that ends; this page places work that must never end — and "the controller is stateless and rebuilds from the database" is the mechanism they share.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "This is a fleet reconciliation system with a rollout controller on top. The requirement 'keep running until redeployed' is the actual product: every service has a **desired state** — an artifact digest, a replica count, a resource request — and a hundred and fifty thousand hosts report an **observed state** through an agent; a controller loop makes observed match desired, forever. A host dying at three in the morning and a new release at three in the afternoon are the same event to that loop — a gap. Three things dominate. First, **the loop, not the API**: fifteen deployments a day is a decoy; the load is 150 k hosts heartbeating, and the work per deployment is proportional to host count — the biggest service is 70 k hosts. Second, **placement is a claim against a capacity inventory**: a deployment says 'seventy thousand replicas of four cores and sixteen gig,' the scheduler picks hosts with room and reserves them one stage at a time with a per-host conditional update — never all 70 k up front. A 'tier' is what service discovery reads *out of* the result; it is never the target, because a brand-new service has an empty one. Third, **staged rollout with health gates**: canary, one percent, ten, fifty, a hundred, a bake at each; health is agent liveness plus the service's own readiness probe plus error rate and latency against the previous version where there is traffic — and readiness plus crash-loop rate alone for the ML services that get none. A failed gate is an automatic rollback, and a rollback is a new deployment of the previous digest through the same machinery. Per-host and per-stage timeouts exist; a whole-rollout timeout does not, because 70 k customer-facing hosts cannot roll in an hour. I'll draw the two state machines first — per deployment and per instance — go deep on the loop and on placement, and cover the 150 k-host health plane as the thing that actually needs sharding. Out of scope: build and test, secrets, and service discovery beyond the one table this system writes."

**Why open this way:** it reinterprets "keep running until redeployed" as reconciliation in the first sentence, kills the fifteen-a-day number in the second, replaces "tier" with "replicas plus resources" before the interviewer has to hint at it, states the timeout policy before it can be probed, and pre-commits the dives (§7, §8, §10). It spends zero seconds on REST — on an infra prompt, the flow is the contract, and the entities fall out of it (§5).

---

## 1 · Functional requirements

1. **Deploy a new artifact for a service** — given a service spec (artifact digest, `replicas`, `resources {cpu, mem, gpu}`, a health definition, a rollout policy), place instances on hosts with free capacity and **roll them out in stages with a health gate between stages**, aborting and rolling back automatically when a gate fails.
2. **Keep every service at its desired state until redeployed** — when a host dies, an instance crashes, or an instance goes unhealthy, **replace it on another host with free capacity within a stated time**, with no operator action.
3. **Answer, for any service, what is running where and at which version** — per-instance state, the deployment's stage and gate history, and the host inventory that placement reads.

**Out of scope (say them):** building and testing artifacts (they arrive as a digest), secrets and configuration injection, service discovery and load balancing (this page *writes* the table they read), autoscaling (a lever that edits `replicas`, nothing more), multi-cluster and multi-region, cost accounting, approval workflows.

**Below the line, likely follow-ups:** blue/green and traffic-shifting rollouts, stateful services with persistent volumes, host drain for maintenance, priority and preemption *across* services (the Job scheduler's §9), per-team quota, GPU topology-aware placement, upgrading the agent itself (§15).

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Heartbeat** | Agent → health plane every **10 s**, **one message per host** carrying every instance on it; a host with no heartbeat for **30 s** is `LOST` | Three missed beats separates a GC pause or a network blip from a death. Per host, not per instance: 15 k messages/s instead of 750 k (§3) |
| **Replacement latency** (FR 2) | Host death → replacement instance `HEALTHY` in **< 5 min p95** (30 s to detect, seconds to place, ≤ 2 min to pull, ≤ 2 min to start and pass readiness) | Bounds how long a dead rack leaves a service under-replicated; the pull budget is what sizes §11 |
| **Per-host deploy timeout** | **10 min** from `ALLOCATED` to `HEALTHY` (pull ≤ 2 min, start ≤ 3 min, readiness ≤ 5 min), **enforced by the controller**, not the agent | The number the round asks for. Past it the instance is `FAILED`, re-placed elsewhere, and counted against the stage's gate. A timeout with no owner is decoration |
| **Per-stage timeout** | A stage must reach its target healthy count within **max(30 min, 2 × expected)**; otherwise the stage fails and the deployment rolls back | Catches the image that hangs on start on every host and never trips a per-host failure loudly enough |
| **Whole-rollout timeout** | **None.** The 70 k rollout takes about six hours by policy (§3); some rollouts are paused for days | Stated on purpose. A 5-host service and a 70 k service have no shared number, and a cap that fits both fits neither |
| **Bake and gate** | Canary **30 min** · 1 % **30 min** · 10 % **60 min** · 50 % **120 min**. Gate, checked **before** advancing: readiness ≥ **99 %** of the stage, crash-loop rate **0**, error rate ≤ baseline **+ 0.5 pp**, p99 latency ≤ **1.2 ×** baseline where traffic exists | Product numbers, labelled as such (§9). The gate is checked before the next stage, not after 100 % |
| **Rollback** | Canary or 1 % stage: **< 5 min**. 10 % stage: **< 20 min** (7 k instances, 700 in parallel, ~2 min each). Stages not yet touched cost **zero** | Rollback replaces only what moved (§9) |
| **Placement latency** | A 10-host service's stage placed in **< 5 s** while a 70 k rollout is in flight | The concurrency probe: a per-host conditional claim, never a table lock or a reserve-everything scan (§8) |
| **Blast radius** | Never fewer than `replicas − max_unavailable` (**5 %**) healthy instances of a service, by construction; surge ≤ **10 %** | The rolling-replacement constraint; the controller cannot drain what would breach it (§8) |
| **Controller failover** | Leader lease **5 s**; a new leader resumes every active deployment from the database in **< 30 s**; no in-flight step lost | The controller is stateless; the database is the state (§7) |
| **Consistency** | Desired state: **read-your-writes** (one Postgres primary). Observed state: **≤ 10 s stale** (one heartbeat). Discovery table: **≤ 15 s stale** | Every freshness claim carries a duration. Nobody reads observed state expecting it to be *now* |
| **Fault tolerance** | Survives: any host or agent; any health-ingest shard (a **2 × interval grace** after a shard restart so nothing goes `LOST` in bulk); the controller leader; Redis (death detection is **blind** until it returns, and nothing is *incorrectly* replaced). **Does not survive: the Postgres primary down without failover** — no new deployments and no replacements; **every running instance keeps running**, because the agent enforces its last desired state locally. The failure is frozen, not cascading | Name the one that stops the world and say what keeps running. Here, the fleet keeps serving and the control plane waits |
| **Scale** | 2 000 services · 150 k hosts · ~**750 k instances** (*assumption: five per host*) · largest service 70 k · 15 deployments/day | §3 |

**The sentence that earns the point:** *"The only timeout I refuse to write is the one on the whole rollout. Every other duration on this page has an owner: the agent owns the pull and the start, the controller owns the per-host and per-stage clocks, and the health plane owns the thirty seconds that decide a host is dead."*

---

## 3 · Numbers that reframe the problem

**Fifteen a day is a request rate, and the request rate is a decoy**

- Fifteen deployments a day at an average of ~375 instances is **~5.6 k instance transitions a day** — nothing. But one 70 k deployment is 70 k instances × ~6 state transitions each = **~420 k state writes**, and the health plane sees 150 k hosts × 8 640 beats a day = **1.3 billion heartbeats a day**. **The work scales with hosts, not with requests.** Decision: the API tier is one box with no number on it; the sharding argument lives in the health plane (§10). *The mock this page comes from said "fifteen a day, so Postgres and we're done" and never recovered.*

**The heartbeat ladder — three designs, one order of magnitude apart each**

- Per instance, every second: **750 k/s**. Per host, every second: **150 k/s** — the figure the interviewer will quote. Per host, every ten seconds, one message carrying every instance's state: **15 k/s**. That last number is still **thirty times** what one Postgres primary should take as row updates — so heartbeats land in a **TTL store sharded by `host_id`** (16 shards ≈ 1 k/s each) and **only transitions** reach Postgres: hundreds a second during a rollout, single digits otherwise. Decision: §10's split between liveness and state.

**The capacity inventory is small; its index is the whole story**

- 150 k host rows × ~300 B = **45 MB**. 750 k allocation rows × ~200 B = **150 MB**. Postgres holds both without a thought. The 1 % stage of the big service needs **700 hosts with 4 cores and 16 GB free**: that is an index range scan on `(pool, az, cpu_free, mem_free)`, not a scan of 150 k rows per claim. Decision: §8's inventory is a table with the right index, and the per-host claim is a conditional `UPDATE`.

**The 70 k rollout, in arithmetic**

- Stages **10 → 700 → 7 000 → 35 000 → 70 000**. Within a stage, batches bounded by `max_unavailable = 5 %` (at most 3 500 down at once) and `max_surge = 10 %` (7 000 spare host-slots, or in-place replacement when there are none). At ~2 minutes per host and 700–3 500 in parallel, the 50 % stage is **~20 minutes of rolling plus a two-hour bake**. **The whole rollout is about six hours, and bake is five of them.** Decision: no whole-rollout timeout (§2), and a rollback that touches only the moved stages is a twenty-minute event, not a six-hour one (§9).

**Artifact distribution is a bandwidth problem before it is anything else**

- *Assumption: a 500 MB image.* 70 k pulls = **35 TB**. From one registry at 10 Gbps that is **~8 hours serialised** — longer than the rollout. A per-rack cache (40 hosts per rack → **1 750 first pulls, 875 GB**) or peer-to-peer distribution brings the 7 000-host stage to minutes. Decision: §11 — pull, content-addressed, through a cache the registry never sees.

**The reconciler is always working, and a rollout is a burst on top of it**

- *Assumption: 0.1 % of hosts die per day.* That is **150 hosts ≈ 750 instances replaced a day with no rollout running at all.** The loop is not a thing that runs during deployments; it is the thing that runs, and a deployment is a bigger gap than usual (§7).

---

## 4 · Core entities

### Draw this first — the two state machines

**Per deployment (the release):**

```text
                       stage n placed & healthy         bake elapsed, gate passed
PENDING ──▶ ROLLING(n) ─────────────────────▶ BAKING(n) ────────────────────────▶ ROLLING(n+1) … ──▶ SUCCEEDED
              │  ▲                              │  ▲
              │  │ operator resume              │  │
              ├──┴──▶ PAUSED ◀──────────────────┘  │
              │                                     │
              ├──▶ ABORTED  (gate failed · stage timed out · operator)  ──▶ spawns a rollback deployment of prev_digest
              │
   any active ──▶ SUPERSEDED  (a newer deployment for the same service started)
```

**Invariant:** at most one active deployment per service — `UNIQUE (service_id) WHERE state IN (PENDING, ROLLING, BAKING, PAUSED)`.

**Per instance (the allocation):**

```text
                pull done        started          readiness passed
ALLOCATED ──▶ PULLING ──▶ STARTING ──▶ HEALTHY ──▶ DRAINING ──▶ STOPPED
                 │            │           │  ▲            (replaced by a rollout, or replicas reduced)
                 │            │           ▼  │  readiness passes again
                 │            │        UNHEALTHY ──▶ FAILED   (3 consecutive readiness failures, or crash-loop)
                 └────────────┴──▶ FAILED   (exit · per-host timeout 10 min)
   any non-terminal ──▶ LOST   (host heartbeat gone 30 s)
```

`FAILED` and `LOST` are terminal **for the row**. The reconciler never revives an allocation; it creates a new one (§7). That is what makes a rollout and a host death the same code path.

| Transition | Caused by | Component that owns it | Recorded where | Timer |
|---|---|---|---|---|
| `→ ALLOCATED` | The reconciler computes `desired − (healthy + in-progress)` for a service at its current stage and claims host capacity with a **conditional update** | **Reconciler** (§7, §8) | `allocations` insert + `hosts.cpu_free` decrement, **one transaction** | per-host clock starts: 10 min |
| `ALLOCATED → PULLING → STARTING → HEALTHY` | The agent reports each step on its next heartbeat, **with the `alloc_id` and the state it expects the row to be in** | **Agent** (§11) | `allocations` (transition only); Redis (current) | pull ≤ 2 min · start ≤ 3 min · ready ≤ 5 min |
| `HEALTHY ↔ UNHEALTHY` | Readiness probe result, run locally, carried on the heartbeat | Agent | `allocations` | 3 consecutive failures → `FAILED` |
| `→ FAILED` | Non-zero exit, crash-loop, readiness never passing, or the per-host clock expiring | Agent (exit) or **Controller** (clock) | `allocations` | — |
| `→ LOST` | No host heartbeat for 30 s | **Health-plane sweeper** (§10) | `allocations` for every instance on the host; `hosts.state = dead`; the host's capacity freed | 30 s |
| `HEALTHY → DRAINING → STOPPED` | A rollout replaces it, or `replicas` was reduced; the reply to the agent's heartbeat says `drain` | Reconciler decides; agent executes | `allocations` | drain grace 60 s |
| `PENDING → ROLLING(n)`, `ROLLING → BAKING`, `BAKING → ROLLING(n+1)`, `→ ABORTED` | Stage placed and healthy; bake elapsed and gate evaluated; gate failed or stage clock expired | **Rollout controller** (§9) | `deployments`, `stages` | stage clock, bake duration |
| `→ SUPERSEDED` | A newer `POST /deployments` for the service | API | `deployments` | — |

**The rule, and it is the whole method:** *every transition is a compare-and-set on the row's `version`, and every agent report carries the `alloc_id` and the state it expects.* A report for an allocation the sweeper already marked `LOST` and the reconciler already replaced loses the CAS, and the reply tells the agent to stop that instance. The Job scheduler's fencing token, reused: here the token is the allocation id itself, because a replaced instance gets a *new* id.

### The entities

- **Service** — `(service_id, owner, replicas, resources {cpu, mem, gpu}, health {readiness_path, probe_interval, gate: traffic | no_traffic, synthetic_check?}, rollout {stages [], bake_s [], max_unavailable, max_surge}, anti_affinity {rack | az}, current_deployment_id)`. **The desired state.** This row is the deployment request; a host list never appears on it.
- **Deployment** — `(deployment_id, service_id, artifact_digest, prev_digest, state, current_stage, reason, created_by, created_at)`. Immutable except `state` and `current_stage`. A rollback is a row like any other, with the digests swapped.
- **Stage** — `(deployment_id, n, pct, target_count, state, started_at, baked_until, gate_result {readiness, crashloops, err_delta, p99_ratio})`. The gate result is written once and kept — it is the audit trail of *why* a rollout stopped.
- **Allocation** — `(alloc_id, service_id, deployment_id, host_id, artifact_digest, resources, state, version, last_transition_at)`. **The observed state**, one row per instance ever placed. The unit of both rollout and self-healing.
- **Host** — `(host_id, pool, az, rack, cpu_total, cpu_free, mem_free, gpu_free, labels, state, version)`. **The capacity inventory.** `last_heartbeat_at` is *not* a column — it lives in Redis (§10).
- **HealthReport** — `(host_id, ts, capacity, instances [{alloc_id, state, ready, version}])`. **Ephemeral. Never a table.** It is the heartbeat's payload, and its only interesting property is whether the latest one is recent.
- **Discovery table** — `service_id → [host:port]` for allocations in `HEALTHY`. **Derived, not authored.** This is what the rest of the company calls "the tier" — and it is an *output* of this system. A brand-new service has an empty one, which is why it can never be the target.

**The three that are load-bearing:**

**`Service.replicas` and `Service.resources` are the deployment request.** Not a host list, not a tier, not a group name. The user says how many and how big; the system says where. The moment the request is a list of machines, a new service has nothing to list and a host at capacity has nowhere to put version two.

**`Allocation` is the unit of both rollout and self-healing.** A rollout drains old allocations and creates new ones a stage at a time; a host death loses allocations and the reconciler creates new ones. Same row, same transitions, same code path — which is why "keep running until redeployed" costs no extra machinery once the loop exists.

**`Host.cpu_free` under a conditional update is the whole concurrency story.** Two deployments that want the same host both issue `UPDATE hosts SET cpu_free = cpu_free − 4 WHERE host_id = h AND cpu_free ≥ 4 AND version = v`; one wins the row, the other moves to the next candidate. No global lock, no single-threaded scheduler, no reserve-everything scan (§8).

---

## 5 · API

```text
PUT  /v1/services/{id}                    { replicas, resources, health, rollout, anti_affinity }
     → 200                                desired state; idempotent; the same call an autoscaler makes
POST /v1/services/{id}/deployments        Idempotency-Key: <client key>    { artifact_digest }
     → 201 { deployment_id }              409 if one is active — or { supersede: true } to replace it
POST /v1/deployments/{id}/pause | resume | abort
     → 202                                abort → { rollback_deployment_id }   ← rollback is a deployment
GET  /v1/deployments/{id}                 → { state, current_stage, stages: [{ n, pct, state, gate_result }], counts_by_instance_state }
GET  /v1/services/{id}/instances          → [ { alloc_id, host, digest, state } ]        ← this is "the tier"

── agent protocol ──────────────────────────────────────────────────────────────
POST /v1/hosts/{id}/heartbeat             every 10 s   { capacity, instances: [ { alloc_id, state, ready, version } ] }
     → 200 { desired: [ { alloc_id, digest, resources, action: run | drain } ] }   ← the only downward channel
```

**Decisions to narrate, unprompted:**

- **On an infra prompt the REST surface is three verbs, and I will not spend a minute on it.** What earns points is the data flow from a spec change to seventy thousand agents; the entities fall out of that flow and get written next to the database box, not designed up front. *The mock this page comes from spent nine minutes here and never reached the health plane.*
- **The heartbeat reply is the only downward channel.** No push, no queue, no inbound connection to a host. The agent asks *"what should I be running?"* every ten seconds and is told. A controller that restarts says nothing new and loses nothing, because desired state is a row, not a message (§7).
- **`abort` returns a new deployment id.** Rollback is not a special path; it is a deployment of `prev_digest` with a one-stage policy (§9). Anyone who can read a deployment can read a rollback.
- **`PUT /services` is idempotent and is the same call the autoscaler makes.** Autoscaling is out of scope and this is the entire reason it can be: it edits one number and the loop does the rest.
- **The heartbeat carries `version` per instance** so a stale agent — one that paused, or came back from a partition — cannot overwrite a transition the controller already made. The reply tells it to `drain` anything the database no longer wants.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 620" role="img" aria-label="Deployment system architecture. Engineers call an API with three verbs that writes desired state into Postgres: services, deployments, stages, allocations and the host inventory. A stateless, leader-leased control plane runs a reconciler tick that computes the gap between desired and observed state and claims host capacity with a per-host conditional update, one stage at a time; a rollout controller that walks stages with a bake and a gate checked before advancing; and a sweeper that turns Redis TTL expiries into LOST transitions under a disruption budget. A hundred and fifty thousand host agents heartbeat once per host every ten seconds to a heartbeat API sharded by host id, which stores liveness in Redis Cluster with a thirty-second TTL and returns the host's desired allocations on the reply. Agents pull artifacts by digest through a rack cache, run the readiness probe locally, and keep their state in SQLite. Healthy allocations are materialised into a discovery table every fifteen seconds; the metrics platform answers the gate query by deployment id.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Desired state is a row and observed state is a heartbeat; the loop closes the gap forever, and a rollout is one more gap.</text>
  <rect class="dg-group" x="20" y="86" width="230" height="110" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">SUBMIT</text>
  <rect class="dg-box" x="36" y="118" width="200" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="136" y="138.5">API — three verbs</text>
  <text class="dg-s dg-c" x="136" y="154.5">PUT /services · POST /deployments</text>
  <text class="dg-s dg-c" x="136" y="170.5">abort → a rollback deployment id</text>
  <rect class="dg-group" x="270" y="86" width="410" height="206" rx="12"></rect>
  <text class="dg-group-t" x="286" y="108">CONTROL PLANE — STATELESS, LEADER-LEASED</text>
  <rect class="dg-box" x="286" y="118" width="180" height="80" rx="8"></rect>
  <text class="dg-t dg-c" x="376" y="138.5">Reconciler tick, 5 s</text>
  <text class="dg-s dg-c" x="376" y="154.5">gap = desired − observed</text>
  <text class="dg-s dg-c" x="376" y="170.5">per-host CAS claim, per stage</text>
  <text class="dg-s dg-c" x="376" y="186.5">drain oldest digest first</text>
  <rect class="dg-box" x="486" y="118" width="178" height="80" rx="8"></rect>
  <text class="dg-t dg-c" x="575" y="138.5">Rollout controller</text>
  <text class="dg-s dg-c" x="575" y="154.5">stage → bake → gate</text>
  <text class="dg-s dg-c" x="575" y="170.5">gate checked before advancing</text>
  <text class="dg-s dg-c" x="575" y="186.5">abort = a new deployment</text>
  <rect class="dg-good" x="286" y="214" width="378" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="475" y="238.5">Sweeper — TTL expiry → LOST</text>
  <text class="dg-s dg-c" x="475" y="254.5">capacity freed · grace 2 × interval after a restart</text>
  <text class="dg-s dg-c" x="475" y="270.5">disruption budget: ≤ 1 % of a service per minute</text>
  <path class="dg-box" d="M 710,125 L 710,279 A 135,7 0 0 0 980,279 L 980,125 A 135,7 0 0 0 710,125 Z"></path>
  <path class="dg-box" d="M 710,125 A 135,7 0 0 0 980,125" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="178">Postgres — desired + transitions</text>
  <text class="dg-s dg-c" x="845" y="194">services · deployments · stages</text>
  <text class="dg-s dg-c" x="845" y="210">allocations (service_id, digest, state)</text>
  <text class="dg-s dg-c" x="845" y="226">hosts (pool, az, cpu_free, mem_free)</text>
  <text class="dg-s dg-c" x="845" y="242">transitions only · leader lease row</text>
  <path class="dg-line" d="M 136,118 L 136,72 L 845,72 L 845,110"></path>
  <path class="dg-head" d="M 840,110 L 850,110 L 845,118 Z"></path>
  <text class="dg-lbl dg-c" x="490" y="66">rows, committed before the 201</text>
  <path class="dg-line" d="M 664,150 L 702,150"></path>
  <path class="dg-head" d="M 702,155 L 702,145 L 710,150 Z"></path>
  <path class="dg-line" d="M 664,250 L 702,250"></path>
  <path class="dg-head" d="M 702,255 L 702,245 L 710,250 Z"></path>
  <rect class="dg-group" x="20" y="320" width="330" height="150" rx="12"></rect>
  <text class="dg-group-t" x="36" y="342">HEALTH PLANE</text>
  <path class="dg-box" d="M 36,359 L 36,445 A 70,7 0 0 0 176,445 L 176,359 A 70,7 0 0 0 36,359 Z"></path>
  <path class="dg-box" d="M 36,359 A 70,7 0 0 0 176,359" style="fill:none"></path>
  <text class="dg-t dg-c" x="106" y="386">Redis Cluster</text>
  <text class="dg-s dg-c" x="106" y="402">host:{id} TTL 30 s</text>
  <text class="dg-s dg-c" x="106" y="418">instance hash per host</text>
  <text class="dg-s dg-c" x="106" y="434">sharded by host_id</text>
  <rect class="dg-box" x="196" y="352" width="150" height="100" rx="8"></rect>
  <text class="dg-t dg-c" x="271" y="382.5">Heartbeat API ×16</text>
  <text class="dg-s dg-c" x="271" y="398.5">by hash(host_id) → Redis</text>
  <text class="dg-s dg-c" x="271" y="414.5">15 k beats/s</text>
  <text class="dg-s dg-c" x="271" y="430.5">reply = desired rows</text>
  <path class="dg-line" d="M 196,402 L 184,402"></path>
  <path class="dg-head" d="M 184,397 L 184,407 L 176,402 Z"></path>
  <path class="dg-line" d="M 106,352 L 106,250 L 278,250"></path>
  <path class="dg-head" d="M 278,255 L 278,245 L 286,250 Z"></path>
  <text class="dg-lbl" x="112" y="244">expiry → LOST transitions</text>
  <path class="dg-line" d="M 300,352 L 300,312 L 760,312 L 760,294"></path>
  <path class="dg-head" d="M 765,294 L 755,294 L 760,286 Z"></path>
  <text class="dg-lbl dg-c" x="560" y="307">reads desired · writes transitions only</text>
  <rect class="dg-group" x="390" y="320" width="300" height="150" rx="12"></rect>
  <text class="dg-group-t" x="406" y="342">HOSTS ×150 k</text>
  <rect class="dg-box" x="406" y="352" width="270" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="541" y="368.5">Agent — one heartbeat / 10 s</text>
  <text class="dg-s dg-c" x="541" y="384.5">reply = desired · pull digest · probe locally</text>
  <text class="dg-s dg-c" x="541" y="400.5">SQLite state · runs with no control plane</text>
  <rect class="dg-warn" x="406" y="420" width="270" height="40" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="541" y="436.5">The service</text>
  <text class="dg-s dg-c" x="541" y="452.5">/ready: model loaded, deps reachable</text>
  <path class="dg-line" d="M 406,372 L 354,372"></path>
  <path class="dg-head" d="M 354,367 L 354,377 L 346,372 Z"></path>
  <text class="dg-lbl dg-c" x="376" y="364">heartbeat</text>
  <path class="dg-line" d="M 346,400 L 398,400"></path>
  <path class="dg-head" d="M 398,405 L 398,395 L 406,400 Z"></path>
  <text class="dg-lbl dg-c" x="376" y="414">desired</text>
  <path class="dg-box" d="M 710,327 L 710,373 A 135,7 0 0 0 980,373 L 980,327 A 135,7 0 0 0 710,327 Z"></path>
  <path class="dg-box" d="M 710,327 A 135,7 0 0 0 980,327" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="350">Discovery table — the tier, an output</text>
  <text class="dg-s dg-c" x="845" y="366">HEALTHY allocations → host:port · 15 s</text>
  <path class="dg-line" d="M 930,286 L 930,312"></path>
  <path class="dg-head" d="M 925,312 L 935,312 L 930,320 Z"></path>
  <path class="dg-box" d="M 710,399 L 710,445 A 135,7 0 0 0 980,445 L 980,399 A 135,7 0 0 0 710,399 Z"></path>
  <path class="dg-box" d="M 710,399 A 135,7 0 0 0 980,399" style="fill:none"></path>
  <text class="dg-t dg-c" x="845" y="422">Object storage + rack cache / P2P</text>
  <text class="dg-s dg-c" x="845" y="438">content-addressed · last two digests pinned</text>
  <path class="dg-line" d="M 676,380 L 692,380 L 692,422 L 702,422"></path>
  <path class="dg-head" d="M 702,427 L 702,417 L 710,422 Z"></path>
  <text class="dg-lbl" x="712" y="466">pull by digest — push scales with the pusher</text>
  <rect class="dg-box" x="710" y="474" width="270" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="845" y="487.5">Metrics platform</text>
  <text class="dg-s dg-c" x="845" y="503.5">error rate · p99 by deployment_id</text>
  <text class="dg-s dg-c" x="845" y="519.5">queried at the gate, not stored here</text>
  <text class="dg-s" x="20" y="546">Heartbeats never touch Postgres: liveness is a TTL, and only transitions are rows. Losing Redis is blindness, never a wrong replacement.</text>
  <text class="dg-s" x="20" y="568">No queue and no outbox: the row is the message, and the agent asks for it every ten seconds. A restarted controller says nothing new.</text>
  <text class="dg-note" x="20" y="590">A host death at 03:00 and a release at 15:00 are the same gap. The tier is what falls out; it is never what you deploy to.</text>
</svg>
</div>

<p class="diagram-cap">Draw the two state machines first, then this. The heartbeat and its reply are the whole protocol — one message up per host, desired rows down — and the sweeper's budget line is the number that stops the loop from eating the fleet on a bad day. Nothing on the board queues anything.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 580" role="img" aria-label="Deployment flows in three lanes. Release: the canary stage claims ten hosts by conditional update, bakes thirty minutes, and the gate is checked before advancing through one, ten, fifty and a hundred percent — about six hours, five of them bake; forty hosts that never become healthy are failed by the per-host clock, re-placed, and the stage still passes at ninety-nine point four percent readiness. Host death with no rollout: a heartbeat stops, thirty seconds later the host is dead and its allocations lost with capacity freed, the reconciler sees a gap of one per service and places replacements that are healthy in about three minutes; when the host returns at forty-five seconds the reply lists nothing it should run and it drains everything. Gate failure: error rate up one point eight points aborts the deployment, a new deployment of the previous digest with a single stage rolls back only the seven thousand seven hundred and ten instances that moved in about twenty minutes, and the trap is a previous image the registry garbage-collected.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Claim a stage by CAS, bake, gate before advancing; a dead host is a gap; a failed gate is a deployment of the previous digest.</text>
  <text class="dg-lane" x="30" y="76">RELEASE — STAGE, BAKE, GATE BEFORE ADVANCING</text>
  <rect class="dg-box" x="30" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="135" y="114.5">PENDING → ROLLING(0)</text>
  <text class="dg-s dg-c" x="135" y="130.5">canary: 10 hosts</text>
  <text class="dg-s dg-c" x="135" y="146.5">claim by CAS, this stage only</text>
  <rect class="dg-good" x="270" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="375" y="114.5">BAKING(0), 30 min</text>
  <text class="dg-s dg-c" x="375" y="130.5">gate checked before advancing</text>
  <text class="dg-s dg-c" x="375" y="146.5">ready · crash · Δerr · p99</text>
  <path class="dg-line" d="M 240,126 L 262,126"></path>
  <path class="dg-head" d="M 262,131 L 262,121 L 270,126 Z"></path>
  <rect class="dg-box" x="510" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="114.5">1 % → 10 % → 50 % → 100 %</text>
  <text class="dg-s dg-c" x="620" y="130.5">each: claim → healthy → bake → gate</text>
  <text class="dg-s dg-c" x="620" y="146.5">≈ 6 h, five of them bake</text>
  <path class="dg-line" d="M 480,126 L 502,126"></path>
  <path class="dg-head" d="M 502,131 L 502,121 L 510,126 Z"></path>
  <rect class="dg-warn" x="760" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="870" y="114.5">40 hosts never HEALTHY</text>
  <text class="dg-s dg-c" x="870" y="130.5">per-host 10 min → FAILED, re-placed</text>
  <text class="dg-s dg-c" x="870" y="146.5">99.4 % ≥ 99 % → the stage passes</text>
  <path class="dg-line" d="M 730,126 L 752,126"></path>
  <path class="dg-head" d="M 752,131 L 752,121 L 760,126 Z"></path>
  <text class="dg-s" x="30" y="190">Never 70 k hosts up front: the 1 % stage claims its 700 thirty minutes after the canary, and a 10-host service places in under five seconds meanwhile.</text>
  <path class="dg-div" d="M 20,206 L 980,206"></path>
  <text class="dg-lane" x="30" y="240">HOST DEATH — NO ROLLOUT RUNNING</text>
  <rect class="dg-box" x="30" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="175" y="278.5">heartbeat stops, 03:00</text>
  <text class="dg-s dg-c" x="175" y="294.5">30 s → host dead · 5 allocations LOST</text>
  <text class="dg-s dg-c" x="175" y="310.5">capacity freed in the same transaction</text>
  <rect class="dg-good" x="350" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="278.5">gap = 1, in each of 5 services</text>
  <text class="dg-s dg-c" x="495" y="294.5">reconciler claims other hosts by CAS</text>
  <text class="dg-s dg-c" x="495" y="310.5">warm-cache pull → HEALTHY ≈ 3 min</text>
  <path class="dg-line" d="M 320,290 L 342,290"></path>
  <path class="dg-head" d="M 342,295 L 342,285 L 350,290 Z"></path>
  <rect class="dg-warn" x="670" y="254" width="290" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="815" y="278.5">the host returns at 03:00:45</text>
  <text class="dg-s dg-c" x="815" y="294.5">reply lists nothing it should run → drains all</text>
  <text class="dg-s dg-c" x="815" y="310.5">a minute of 30 where 25 were wanted</text>
  <path class="dg-line" d="M 640,290 L 662,290"></path>
  <path class="dg-head" d="M 662,295 L 662,285 L 670,290 Z"></path>
  <text class="dg-s" x="30" y="350">Over-replacement for a minute is the price of a 30-second threshold. The other price — minutes under-replicated on a real death — is worse, and the budget caps the blip case.</text>
  <path class="dg-div" d="M 20,366 L 980,366"></path>
  <text class="dg-lane" x="30" y="400">GATE FAILS — ROLLBACK IS A DEPLOYMENT</text>
  <rect class="dg-box" x="30" y="414" width="220" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="434.5">10 % bake: err +1.8 pp</text>
  <text class="dg-s dg-c" x="140" y="450.5">threshold 0.5 → ABORTED</text>
  <text class="dg-s dg-c" x="140" y="466.5">gate_result written, kept</text>
  <rect class="dg-good" x="270" y="414" width="230" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="385" y="434.5">new deployment: prev_digest</text>
  <text class="dg-s dg-c" x="385" y="450.5">stages [100] · bake 0</text>
  <text class="dg-s dg-c" x="385" y="466.5">still batched · still probed</text>
  <path class="dg-line" d="M 250,446 L 262,446"></path>
  <path class="dg-head" d="M 262,451 L 262,441 L 270,446 Z"></path>
  <rect class="dg-box" x="520" y="414" width="220" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="630" y="434.5">7 710 roll back ≈ 20 min</text>
  <text class="dg-s dg-c" x="630" y="450.5">62 290 on v1 untouched</text>
  <text class="dg-s dg-c" x="630" y="466.5">only what moved moves back</text>
  <path class="dg-line" d="M 500,446 L 512,446"></path>
  <path class="dg-head" d="M 512,451 L 512,441 L 520,446 Z"></path>
  <rect class="dg-warn" x="760" y="414" width="220" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="870" y="434.5">v1 image GC'd from the registry</text>
  <text class="dg-s dg-c" x="870" y="450.5">stalls in PULLING, clocks fail it</text>
  <text class="dg-s dg-c" x="870" y="466.5">pin the last two digests</text>
  <path class="dg-line" d="M 740,446 L 752,446"></path>
  <path class="dg-head" d="M 752,451 L 752,441 L 760,446 Z"></path>
  <text class="dg-note" x="30" y="520">Rollback is not a code path that runs only during incidents. It is a row with the digests swapped, through the same machinery that just proved itself.</text>
</svg>
</div>

<p class="diagram-cap">The top lane's third box is where the clock goes — six hours, five of them waiting — and its fourth is why a per-host timeout has an owner. The middle lane is the requirement the mock did not hear, and the bottom lane's mechanism is a row, not a runbook.</p>

### Flow A — a 70 k-host release, stage by stage

1. `POST /services/web/deployments { digest: v2 }` → a `deployments` row in `PENDING`, `prev_digest = v1`. The controller leader picks it up on its next tick and moves it to `ROLLING(0)`.
2. **Stage 0, the canary: 10 hosts.** The reconciler computes the gap — desired(v2) at this stage is 10, observed is 0 — selects candidates from the inventory index with rack spread, and **claims each host with a conditional update** (§8). Ten `allocations` rows in `ALLOCATED`, one transaction each with the capacity decrement.
3. The ten agents see the new desired entries on their next heartbeat reply, **pull v2 by digest through the rack cache** (§11), start it, run the readiness probe, and report `HEALTHY`. Old v1 allocations on those slots — if the pool is in-place rather than surge — go `DRAINING → STOPPED` after the 60 s grace; the discovery table drops them and adds the new ones within 15 s.
4. Stage 0 reaches 10/10 healthy → `BAKING(0)` for 30 minutes. The controller evaluates the gate **before** advancing (§9): readiness, crash-loops, error rate and p99 against the v1 cohort. Pass → `ROLLING(1)`: 700 hosts, in batches bounded by `max_unavailable`. Then 7 000, 35 000, 70 000 — **about six hours, five of them bake.**
5. **The failure path.** In the 10 % stage, 40 hosts never reach `HEALTHY` inside the per-host 10 minutes — a slow disk, a wedged pull. The controller marks them `FAILED`, the reconciler places 40 replacements elsewhere, and the 40 failures count against the gate: 99.4 % readiness still clears 99 %, and the stage advances. The gate result records the 40. If it had been 400, the stage fails and Flow C runs.

### Flow B — a host dies, and no rollout is running

1. 03:00. A rack loses power. Five hosts stop heartbeating.
2. 03:00:30. The health-plane sweeper (§10) sees five keys expire, marks each host `dead`, marks every allocation on them `LOST` — twenty-five rows — and **frees their capacity in the inventory**.
3. On its next tick the reconciler sees a gap of one for each of the affected services, claims capacity on healthy hosts, and inserts new allocations. Agents pull (warm cache — these digests are already on every rack), start, pass readiness. **`HEALTHY` in about three minutes.** Nobody was paged; the discovery table never listed the dead hosts for more than 45 seconds.
4. **The failure path.** The rack was not dead — a switch rebooted. At 03:00:45 the five hosts come back, still running all twenty-five instances, and heartbeat as if nothing happened. The reply lists **zero desired entries** for those allocation ids — the database has them as `LOST` — so the agent **drains all twenty-five**. For about a minute the fleet ran thirty instances where it wanted twenty-five. **That over-replacement is the cost of a 30-second threshold, and it is the right cost:** the alternative is a threshold long enough that a real death leaves the service under-replicated for minutes.

### Flow C — a gate fails, and the rollback is a deployment

1. Stage 2 (10 %, 7 000 hosts) has been baking for 40 minutes. The gate evaluates: error rate is **1.8 pp above the v1 cohort**. Threshold is 0.5. The deployment goes `ABORTED`, `reason = gate:error_rate`, and the gate result is written to the stage row.
2. The controller **creates a new deployment** — `artifact = v1`, `prev = v2`, `rollout = { stages: [100], bake: [0] }` — and links it as `rollback_deployment_id`. It is a normal deployment with a one-stage policy: still batched by `max_unavailable`, still per-host health-checked, so a rollback cannot itself take the service down.
3. The reconciler drains the **7 710 v2 allocations** (stages 0–2) and places v1 in their slots; 700 in parallel at ~2 minutes each is **about 20 minutes**. The **62 290 hosts still on v1 are untouched** — they were never a gap.
4. **The failure path.** The v1 image has been garbage-collected from the registry — it was six weeks old. The rollback stalls with every allocation in `PULLING`, and the per-host clock starts failing them. The policy that prevents this is stated up front: **the registry pins the last two digests of every service**, and a rollback to anything older is a deliberate `POST` of an old digest, not an automatic one.

### Flow D — a brand-new service, and the tier that does not exist yet

1. `PUT /services/ranker { replicas: 200, resources: { cpu: 8, mem: 64, gpu: 8 } }`, then `POST /deployments { digest: r1 }`. There is **no tier to target and no cohort to compare against.**
2. The reconciler places 200 allocations exactly as it would for a replacement — the inventory query does not know or care whether the service is new. The discovery table is empty until the first allocation is `HEALTHY`, at which point it has one entry. **The tier is created by the deployment.** This is the flow that makes "deploy to the tier" impossible as a design: it would have been asked to deploy to nothing.
3. With no previous cohort, the gate uses **readiness and crash-loop rate only** — the `no_traffic` gate — and the canary stage is one instance, because a canary with nothing to compare to is a smoke test, and a smoke test needs one.
4. **The failure path.** The GPU pool has room for 140 of the 200. Placement returns partial. The deployment sits in `ROLLING(0)` at **140/200, visibly**, and the reconciler keeps trying on every tick as capacity frees. **It does not fail and it does not time out** — "pending, visibly, until capacity exists" is the correct behaviour for a capacity shortfall, and the operator's `GET /deployments` says exactly that. A timeout here would turn a capacity problem into a mystery.

### Flow E — the controller leader dies mid-rollout

1. The leader is halfway through issuing stage 3's batch — 1 700 of 3 500 allocations inserted — when it is killed.
2. Its lease expires in 5 s; a standby takes it and scans `deployments WHERE state IN active`. For each, it recomputes the gap: desired at the current stage minus observed. The 1 700 already placed are observed; the gap is 1 800. It issues them. **The half-finished batch was never a thing that needed resuming, because commands were never stored — desired state was.**
3. **The failure path.** The old leader was not dead, only paused, and wakes after 12 s to issue its next claim. Its claim carries its lease token; the `deployments` row's token has moved on; the conditional update fails. It reads the lease row, sees it is no longer leader, and stops. **The scheduler page's fencing token, one level up.**

---

## 7 · Deep dive — the reconciliation loop is the product, and it is why there is no queue

### What you'd reach for first

A **deploy job**: for each target host, push the artifact, start it, mark done; when every host is done, the deployment is done. And separately, a **monitor** — a cron that checks whether services are running and restarts what is not.

### What breaks

- **"Done" is a lie the moment a host dies.** The deploy job finished at 15:00; at 03:00 five hosts are gone and the job has no opinion, because it ended. Now the monitor has to know what the deploy job knew — which artifact, how many, what resources — and you have two systems holding the same truth.
- **Commands are edge-triggered, and edges get lost.** "Start v2 on host 41" is a message. If the deployer crashes after sending 1 700 of 3 500, someone has to know which 1 700 — so now there is a queue, an outbox to write it atomically, and a replay on restart. *The mock this page comes from drew exactly that, for fifteen events a day, and was asked "do we need a queue?"*
- **The deployer and the healer fight.** The healer restarts v1 on a host the deployer is draining; the deployer places v2 on a host the healer just filled. Two writers, one fleet.

### What replaces it

**A level-triggered controller.** Every tick — say every 5 s — for every service:

```text
desired(service, stage) = replicas × stage.pct for the new digest, replicas × (1 − stage.pct) for the old
observed(service)       = count of allocations by (digest, state) — one indexed query
gap                     = desired − (HEALTHY + in-progress)
gap > 0 → place that many (§8)        gap < 0 → drain the oldest-digest allocations first, bounded by max_unavailable
```

- **A rollout is the controller raising `desired(v2)` and lowering `desired(v1)` one stage at a time.** Nothing else. Host death is the same computation with no stage change: observed dropped, gap opened, place.
- **The controller is stateless and leader-leased.** Its entire state is the `services`, `deployments`, `stages`, and `allocations` tables. A new leader recomputes every gap from scratch in one scan and continues (Flow E). There is nothing to replay because nothing was ever in flight — desired state is a row, and the next tick reads it.
- **Agents pull desired state on the heartbeat reply.** The controller never sends a command; it writes a row, and the agent asks every ten seconds what its rows say (§11). **The row is the message.** No queue, no outbox, no dual write — the thing the mock spent four minutes on does not exist, because the receiver polls the source of truth.
- **The tick over 2 000 services is cheap** — 2 000 `count … GROUP BY digest, state` queries on an index, or one query grouped by service — because the reconciler *counts* allocations, it never *scans* them.

**→ ties to the controller-failover NFR and to the fault-tolerance row:** the controller can be gone for a minute and nothing is lost; the database can be gone for an hour and every instance keeps running on its last desired state.

**What the replacement costs:**

- **The loop needs damping.** A health-plane blip that marks 10 k hosts `LOST` for 40 seconds would make the loop place 50 k replacements it does not need. §10's disruption budget — no more than 1 % of a service replaced per minute for `LOST` reasons — is a cost of level-triggering, not a nicety.
- **"Why did this instance move?" is no longer in a log of commands.** The loop does not narrate; it converges. A `deployment_events` table — allocation created, reason `gap:host_lost:h41` — has to be written *by* the loop, or operators debug a fleet that changes for no visible reason (§12).
- **The tick interval is a latency floor.** A gap opened at second 0 is seen at second 5 at worst. Fine here; a system that needed sub-second reaction would need a watch (Kubernetes' etcd watch is exactly this trade), and the sentence to say is that a 5-second tick is chosen because the heartbeat is 10 s and nothing downstream is faster.

---

## 8 · Deep dive — placement is a claim against a capacity inventory, reserved one stage at a time

### What you'd reach for first

**"Deploy to the web tier."** The service has a group of machines it runs on; a deployment goes to that group. Or, the concurrency-safe version: when a 70 k deployment arrives, **reserve all 70 k hosts up front** under a table lock, so nothing else can take them, then roll.

### What breaks

- **A new service has no tier.** Flow D. There is nothing to deploy to. The target has to be *derived* from the request, not named by it.
- **A host running v1 at capacity has no room for v2.** If the target is "the machines currently running this service," a rolling replacement has to stop v1 before starting v2 on the same host — which is fine as one option, but it cannot be the *only* option, and it is not what "deploy to the tier" means.
- **A tier is a service-networking concept, and it is downstream of this system.** Discovery reads the set of healthy allocations and calls the result a tier. Using it as the input reverses the flow of control — *the interviewer will say exactly this.*
- **Reserve-all-up-front serialises every deployment behind the biggest.** A 10-host service arrives while the 70 k scan-and-reserve holds the lock; it waits. And the 70 k reservation locks up capacity for six hours of bake that will not be *used* for six hours. **→ this is the placement-latency NFR, and this design fails it.**
- **A host list is not a resource request.** Two services placed by list onto the same host can both believe they have the RAM.

### What replaces it

**The request is `replicas × {cpu, mem, gpu}`; the inventory is a table; the claim is a conditional update; the reservation is per stage.**

1. **Candidate selection is an index range scan.** `SELECT host_id FROM hosts WHERE pool = ? AND state = 'alive' AND cpu_free ≥ 4 AND mem_free ≥ 16 ORDER BY az, rack, cpu_free DESC LIMIT 700`. The index `(pool, az, cpu_free, mem_free)` makes this milliseconds against 150 k rows. Spread is a policy on the candidate list — round-robin over racks, at most `k` per rack, at most `replicas / azs` per AZ — not a scan.
2. **The claim is one conditional update per host:** `UPDATE hosts SET cpu_free = cpu_free − 4, mem_free = mem_free − 16, version = version + 1 WHERE host_id = h AND cpu_free ≥ 4 AND mem_free ≥ 16 AND version = v`. **A lost CAS moves to the next candidate.** Two deployments wanting the same host never both get it, and neither waited for the other — the concurrency probe, answered by the row.
3. **Reserve per stage, and within a stage per batch.** The canary claims 10 hosts. The 1 % stage claims 700 — thirty minutes later, when it starts. **Never 70 k.** Capacity that a rollout will not use for five hours is capacity someone else can use now, and the 10-host deployment placed in under 5 s because there was no lock to wait for.
4. **Surge versus in-place is a per-service choice, and the spec says which.** With `max_surge = 10 %` and room in the pool, v2 is placed on *other* hosts and v1 drained after — zero capacity dip. With no room, the batch is `max_unavailable = 5 %`: drain 5 % of v1, place v2 on the freed capacity, wait for healthy, next batch. **The controller never drains below `replicas − max_unavailable` healthy** — the blast-radius NFR is a check in the drain step, not a hope.

**The loser, named:** the Borg/Omega answer is a **per-pool single-writer scheduler with the inventory in memory** — one process owns placement for a pool, optimistic concurrency between pools. It is the right design at ten thousand placements a second. At fifteen deployments a day and a peak of ~1 k claims/s during the 50 % stage, **Postgres with a conditional update on an indexed row is enough**, and the memory-resident scheduler is a rewrite this page names as the revisit condition: *"if claim latency on the inventory index crosses 50 ms at p99, placement moves in-process per pool."*

**→ ties to the placement-latency and blast-radius NFRs.**

**What the replacement costs:**

- **Bin-packing is greedy, not optimal.** First-fit by free capacity fragments a pool over months: a thousand hosts each with 3 cores free and no host with 4. A **rebalance job** — drain and re-place the worst-fragmented allocations inside the disruption budget — is named here and not designed; it is a week of work and a follow-up question.
- **GPU topology** — eight GPUs on one NVLink domain versus eight across two — is a placement constraint the `resources` field cannot express. Below the line, and say so: the request gains a `topology` hint and the candidate query gains a predicate.
- **The index has to be maintained under 15 k capacity updates a minute during a big stage.** It is fine — this is what B-trees do — but it is the one hot index in the system, and it is the reason `hosts` is its own table rather than a column on something bigger.

---

## 9 · Deep dive — staged rollout, health gates, and a rollback that is a deployment

### What you'd reach for first

Roll to everything, watch a dashboard. Health is *"the process is up."* And to be safe, **a timeout on the whole rollout** — twelve hours, say — after which it is declared failed.

### What breaks

- **Rolling to everything is a 100 % blast radius.** A bad build is on 70 k hosts before the dashboard has a data point.
- **"The process is up" misses the build that starts and returns 500.** Liveness is not readiness, and readiness is not correctness.
- **Traffic metrics are meaningless for a service that gets no traffic.** The ML ranker that the nightly job calls has an error rate of exactly zero all day because nothing calls it. A gate on error rate passes a broken build. *The interviewer named this case.*
- **A whole-rollout timeout either fails healthy rollouts or means nothing.** Twelve hours fails the 70 k service on a slow day and is meaningless for the 5-host service. Whatever the number, it is wrong for most services, and a timeout that fires on a healthy rollout is a page at 04:00 for nothing. **The durations that matter are per host and per stage, and they have owners (§2).**

### What replaces it

**Stages with bake, a three-layer health definition declared per service, a gate checked before advancing, and a rollback that reuses everything.**

- **Stages:** 10 → 1 % → 10 % → 50 % → 100 % with bakes of 30 / 30 / 60 / 120 minutes. The canary is ten hosts, not one, because one host's metrics are noise. The 50 % stage exists because **a load-dependent bug passes at 10 %** — a connection pool that is fine at a tenth of the traffic and exhausted at half.
- **Health is three layers, and the service declares which apply:**
  1. **Agent liveness** — the host is heartbeating. Free.
  2. **The service's readiness probe** — `GET /ready` answered by the service itself: model loaded, dependencies reachable, warm-up done. Run locally by the agent, reported on the heartbeat. This is the layer that catches "up but broken."
  3. **Comparative metrics against the previous version's cohort** — error rate and p99 for the v2 instances versus the v1 instances *during the same window*, not against yesterday. Requires the metrics platform to tag by `deployment_id`. **Only where traffic exists.**
  - **For `gate: no_traffic` services,** layer 3 is replaced by **crash-loop rate** (a process that exits and restarts is unhealthy even if it answers `/ready` between restarts) and an optional **declared synthetic request** — the service ships a canned input and the agent sends it. The ranker's owner declares this; the system does not guess.
- **The gate is evaluated before the next stage starts, never after 100 %.** Readiness ≥ 99 %, crash-loops 0, error ≤ baseline + 0.5 pp, p99 ≤ 1.2 ×. The result is written to the stage row whether it passes or fails — the audit trail of every rollout is the gate results.
- **Per-stage timeout:** `max(30 min, 2 × expected)`. A stage whose hosts never converge fails the stage, and the deployment aborts. **This is the timeout the mock reached for and put in the wrong place.**
- **Abort creates a rollback deployment** (Flow C): `artifact = prev_digest`, `stages: [100]`, `bake: [0]`, still batched by `max_unavailable`, still per-host health-checked. **Only the instances that moved roll back**; a rollback from the 10 % stage is 7 710 instances and twenty minutes, not 70 k and six hours. Rollback is not a code path — it is a row.

**→ ties to the bake-and-gate NFR and the rollback NFR.**

**What the replacement costs:**

- **Bake dominates the clock.** Six hours for 70 k hosts, five of them waiting. That is the price of a gate with enough data to mean something, and it is why the whole-rollout timeout is refused rather than set.
- **The metrics platform has to know about deployments.** Every metric from an instance is tagged `deployment_id`; the gate is a query the metrics platform answers. If it cannot, layer 3 does not exist and the gate is readiness plus crash-loops for everyone — say so, because it is a real deployment system's most common gap.
- **A canary can pass and 50 % can fail.** Load-dependent bugs, cache-warming effects, a downstream that is fine with 10 % of the traffic on a new code path. The 50 % stage costs two hours and exists for exactly this; a team that skips it to ship faster is the trap in §13.
- **Rollback needs the previous artifact to exist.** The registry pins the last two digests per service (Flow C); GC that ignores this turns an abort into a stall.

---

## 10 · Deep dive — the 150 k-host health plane, and the disruption budget that keeps it from eating the fleet

### What you'd reach for first

Every agent does `UPDATE hosts SET last_seen = now() WHERE host_id = ?` every second. A cron finds hosts with `last_seen < now() − 30 s` and marks them dead.

### What breaks

- **150 k row updates a second on one Postgres primary** — or 15 k/s batched to every ten seconds, which is still the hottest table in the system by two orders of magnitude and would be the thing that pages at 03:00. §3's ladder: this is the number that drives sharding, and it is not fifteen a day.
- **A restart of the ingest tier makes every host look dead at once.** Thirty seconds of no writes → 150 k hosts `LOST` → the reconciler (§7) tries to place **750 k replacements** on a fleet that is, in fact, fine. This is the outage a deployment system causes *itself*, and it has happened at every company that has one.
- **Dead and partitioned look identical from here.** A host that cannot reach the ingest tier for 35 seconds is marked dead while still serving traffic.

### What replaces it

- **One heartbeat per host per 10 s carrying every instance's state** — `{ capacity, instances: [{ alloc_id, state, ready, version }] }`. 15 k/s total.
- **An ingest tier sharded by `hash(host_id)`, writing to Redis Cluster:** `SET host:{id} <ts> EX 30` plus a hash per host of instance states. Sixteen shards, ~1 k/s each, trivially. **The heartbeat never touches Postgres.**
- **A sweeper per shard** watches for key expiry (keyspace notifications, with a periodic scan as the backstop) and turns each expiry into **transitions** in Postgres — `hosts.state = dead`, every allocation on it `LOST`, capacity freed. **Only transitions reach the database:** hundreds a second during a rollout, single digits at 03:00.
- **Dead versus partitioned is a guess by design**, and the design handles the wrong guess on the agent side: a host that comes back is told, on its next heartbeat reply, to drain what the database no longer wants (Flow B). Thirty seconds is chosen because the cost of guessing "dead" wrongly is a minute of over-replacement, and the cost of guessing "alive" wrongly is minutes of under-replication.
- **Thundering-herd protection, three layers:**
  1. **Jittered heartbeat phase** per host, so 150 k agents do not beat in the same 100 ms.
  2. **A grace period of 2 × the interval after an ingest shard restarts** — the shard does not sweep until it has had time to hear from everyone.
  3. **A disruption budget in the reconciler:** no more than **1 % of a service's instances replaced per minute for `LOST` reasons.** A control-plane blip that marks 10 k hosts `LOST` produces at most a trickle of replacements before the hosts come back and the sweeper reverses itself. This is the single most important number in the health plane, and it is the one nobody draws.

**The loser, named:** **Kafka for heartbeats.** A durable, ordered log for data whose only interesting property is *"is the latest one recent?"* — nobody will ever replay a heartbeat. Redis with a TTL is the primitive that matches the question. Kafka is the right answer for the **transition events** (§12), where someone *will* ask "what happened to host 41 last Tuesday."

**→ ties to the heartbeat NFR and the replacement-latency NFR.** The 30-second threshold plus a 5-second tick plus a warm pull is the < 5 min p95.

**What the replacement costs:**

- **Losing Redis blinds death detection until it returns.** Nothing incorrect happens — no host is marked dead, no instance is replaced — but a host that dies during the outage is not replaced until Redis is back. The fault-tolerance row says this out loud.
- **The agent must run its last desired state without a control plane for hours.** It keeps a local copy (§11) and keeps enforcing it; a heartbeat that gets no reply changes nothing. This is what makes "Postgres down" a frozen failure instead of a fleet-wide one.
- **Two sources of truth for instance state, deliberately.** Redis has the *current* state of every instance, ten seconds stale; Postgres has the *transitions*. A dashboard reads Redis; the reconciler counts Postgres. Saying which reads which is the sentence that shows the split was chosen.

---

## 11 · Deep dive — artifact distribution and the host agent: pull by digest, and an agent that survives without you

### What you'd reach for first

The controller opens a connection to each host, pushes the image, and runs the start command. A "deploy" is a remote procedure call.

### What breaks

- **Push means the controller holds 70 k connections and has to know who is up.** It becomes a stateful thing that tracks every host — the opposite of §7.
- **35 TB from one registry is eight hours** (§3) — longer than the rollout it is supposed to serve. Seven thousand hosts pulling the same 500 MB at once is a denial-of-service attack on your own registry.
- **A push command that is lost on a controller restart is lost.** Back to the outbox.

### What replaces it

- **Pull, content-addressed by digest.** The desired entry says `digest: sha256:…`; the agent fetches it from object storage **through a per-rack cache** (40 hosts per rack means 1 750 pulls from the registry, not 70 k) or a peer-to-peer distributor — name one: **Dragonfly, Kraken, or Spegel**, all of which exist for exactly this. The canary stage's ten pulls warm the caches the 1 % stage will hit.
- **The command is idempotent and repeated until observed matches:** *"allocation A: run digest D with resources R."* It rides every heartbeat reply. An agent that already has A running does nothing; one that lost it restarts it; one that was told to `drain` stops it. Repetition is free because the command is a *state*, not an *action*.
- **The agent keeps a local state file** — SQLite on the host — of its desired and observed allocations. It survives its own restart. It **enforces desired state with no control plane at all**: a heartbeat with no reply, or a Postgres outage, changes nothing about what runs on the host. This is the fault-tolerance row's "every instance keeps running," made concrete.
- **The agent's local machine** mirrors §4: `PULLING → STARTING → HEALTHY`, with the readiness probe run locally on the service's declared path and interval, and the result carried on the next heartbeat. The agent never decides an instance has *failed a stage* — it reports; the controller decides.
- **The per-host timeout is the controller's clock, not the agent's.** An agent cannot be trusted to time itself out — it may be the thing that is wedged. The controller compares `allocated_at` to now on every tick.

**The loser, named:** **`rsync`/SSH push from a deploy box** is what every startup's first deployer is, and it works to a few hundred hosts. The sentence: *"push scales with the pusher; pull scales with the fleet."*

**→ ties to the per-host-timeout NFR and the replacement-latency NFR** — a warm rack cache is what makes a 2-minute pull budget honest.

**What the replacement costs:**

- **The canary always pays the cold pull.** Ten hosts fetching a digest no cache has seen. Fine, and it is why the canary bake starts *after* healthy, not after placement.
- **Disk on every host holds N recent digests,** and a GC policy — keep the current, the previous, and anything pulled in the last 24 hours — is a real thing someone has to write.
- **The agent is the one component whose own upgrade needs a rollout,** and it cannot be rolled out by itself in the ordinary way: a new agent that fails to start leaves the host with no agent. §15's last row.

---

## 12 · Data model, sharding, and storage decisions

**One Postgres primary, and say why that is not a cop-out.** The system of record is ~200 MB — 150 k hosts, 750 k allocations, 2 000 services, a few thousand deployments — and its write rate peaks at **~1 k transitions/s** during the 50 % stage of the biggest service. The two indexes that matter are `allocations (service_id, digest, state)` — the reconciler's count — and `hosts (pool, az, cpu_free, mem_free)` — placement's candidate scan. **The hot row** is the `deployments` row of the 70 k service, written by one leader; a single-writer row is not contention. If the allocations table ever needed splitting, it partitions by `service_id`, because every query on it is per service. It does not need to.

**What is not in Postgres, on purpose.** Heartbeats (§10), current instance state (Redis), rollout metrics (the metrics platform), artifacts (object storage). The database holds desired state and transitions. Everything with a "latest value" shape lives somewhere that expires.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Services, deployments, stages** | 2 000 + a few thousand rows; CAS on `deployments.state`; one active per service by unique index | **System of record** | **Postgres** | "It's two thousand rows and a compare-and-set. etcd is what Kubernetes uses because it needs *watch*; I get watch from the loop's tick and I'd rather have a `JOIN`" |
| **Allocations** | `count … GROUP BY digest, state` per service per tick; insert on place; CAS on every transition | System of record; 90 days of history | **Postgres**, index `(service_id, digest, state)`; partition by `service_id` only if the 70 k service ever dominates | "Cassandra takes the writes but can't give me `count WHERE state` per service every five seconds without a counter I'd have to keep correct myself" |
| **Host inventory** | Index range scan for candidates; conditional update per claim; capacity freed on `LOST` | System of record | **Postgres**, index `(pool, az, cpu_free, mem_free)`, `version` column | "The Borg answer is an in-memory single writer per pool. I don't need ten thousand placements a second; I need a thousand claims a second, and a B-tree does that" |
| **Host liveness** | 15 k writes/s; expiry is the event | **Ephemeral** — rebuilt by the next heartbeat | **Redis Cluster**, `SET host:{id} EX 30`, sharded by `host_id` | "Postgres at fifteen thousand updates a second is the trap. A TTL *is* the death detector" |
| **Instance current state** | Written per heartbeat; read by dashboards and the reply builder | Ephemeral | **Redis**, hash per host | "Ten seconds stale and that's the contract" |
| **Rollout metrics** | Error rate and p99 by `deployment_id`, queried at the gate | Whatever the platform keeps | **The metrics platform** (Prometheus, M3) — queried, not stored here | "The gate is a query. If the platform can't tag by deployment, the gate is readiness plus crash-loops, and I say that up front" |
| **Artifacts** | 1 750 rack-cache pulls per digest; content-addressed | Durable; last two digests per service pinned | **Object storage** + per-rack cache or P2P (Dragonfly / Kraken / Spegel) | "Push scales with the pusher; pull scales with the fleet" |
| **Discovery table** | Read by every client's service mesh; rebuilt every 15 s from `HEALTHY` allocations | Derived | **A Postgres view materialised into Redis or ZooKeeper** every 15 s | "This is the tier. It's an output. The next system reads it; this one never does" |
| **Agent local state** | Desired + observed allocations on this host; read on every enforcement loop | Local; survives agent restart | **SQLite** on the host | "The host keeps running through a control-plane outage because the truth it needs is on its own disk" |
| **Deployment events** | Append per transition with a reason; read by humans | 90 days hot, 2 years cold | **Postgres**, then **ClickHouse** | "The loop converges; it doesn't narrate. This table is the narration" |
| **Leader lease** | Renewed every 5 s; CAS to acquire; token on every write | Durable | **A row in Postgres** | "Same mechanism as the scheduler page — the controller is a leased job" |

### Data lifecycle — the append-only entities

| Entity | Growth | Hot | Warm | Cold | Restore |
|---|---|---|---|---|---|
| **Allocations** | ~750/day steady; up to 420 k in one big rollout | Live rows; terminal (`STOPPED`, `FAILED`, `LOST`) rows kept 90 days | — | ClickHouse, 2 years | Minutes; `GET /instances` falls through for old ids |
| **Deployment events** | ~1 M/day worst case | 90 days in Postgres | — | ClickHouse, 2 years | Same |
| **Stage gate results** | 5 per deployment | Forever in Postgres — tiny, and it is the audit trail | — | — | — |
| **Heartbeats** | 1.3 B/day | **Never stored.** 30-second TTL | — | — | n/a — the next one arrives in ten seconds |

### The signals that tell you this is broken

- **Gap per service** — desired minus healthy, summed. Should be zero outside a rollout. A persistent positive gap is a capacity problem; a persistent negative one is a reconciler bug.
- **`LOST` rate versus `FAILED` rate** — the first is the platform (hosts, network, the health plane); the second is the image. When `LOST` spikes with no hardware event, look at the ingest tier, not the fleet.
- **Time in `PULLING`, p99** — the rack cache is cold or the registry is the bottleneck.
- **Gate-fail rate per stage** — a service that fails at 50 % more often than at 1 % has a load-dependent bug class.
- **Disruption-budget saturation** — the reconciler wanted to replace more than 1 %/min and was held back. Every saturation is either an incident or a blip that would have become one.

---

## 13 · Traps — the ranked list

**Design traps** — the first six are, in order, the mock this page was written from.

1. **"Deploy to the tier."** A tier is an output of deployment — the set of healthy instances that discovery reads. A new service has none; a full v1 tier has no room for v2; and the request has to be *replicas plus resources* for the scheduler to have anything to compute (§8, Flow D).
2. **"Fifteen a day, so Postgres and we're done."** The request rate is a decoy. The load is 150 k hosts heartbeating, and work per deployment is proportional to hosts. The sharding argument is in the health plane, and it is there whether or not you look (§3, §10).
3. **Reserve all 70 k hosts up front, or a single-threaded scheduler.** Serialises every deployment behind the biggest and locks up capacity for hours of bake. Per-host conditional claim, reserved per stage (§8).
4. **An outbox and a queue for fifteen events a day.** Desired state in a row plus an agent that pulls it *is* the delivery mechanism. There is nothing to queue (§7).
5. **A timeout on the whole rollout.** No number fits both a 5-host and a 70 k-host service. Per-host and per-stage clocks, each with an owner (§2, §9).
6. **"Keep running until redeployed" read as "don't break things during a rollout."** It means *replace instances when hosts die* — the loop is the product, and the rollout is a special case of it (§7).
7. **Health is "the process is up," or health is traffic metrics for a service that gets no traffic.** Three layers, declared per service; `no_traffic` gets crash-loops and a synthetic request (§9).
8. **Edge-triggered deploy commands.** "Start v2 on host 41" is lost when the sender dies. Level-triggered gaps are recomputed from rows (§7, Flow E).
9. **Rollback as a special code path.** It is a deployment of the previous digest with a one-stage policy; anything else is untested code that runs only during incidents (§9, Flow C).
10. **No disruption budget.** An ingest-tier blip marks 10 k hosts `LOST` and the loop dutifully places 50 k replacements. 1 % per service per minute (§10).
11. **The gate checked after advancing.** The bake exists to produce a decision *before* the next stage has the build (§9).
12. **Push-based distribution from one registry.** 35 TB through one door is eight hours; pull through a rack cache is minutes (§11).

**Performance traps**

13. **Heartbeats as Postgres row updates.** The hottest table by a hundred times (§10).
14. **Heartbeats per instance, per second.** 750 k/s where 15 k/s does the job (§3).
15. **Placement by table scan.** The candidate query is an index range; the claim is one row (§8).
16. **A reconciler that scans allocations instead of counting them.** 750 k rows read every five seconds; `count … GROUP BY` on the index instead (§7).
17. **The rollback digest garbage-collected.** Pin the last two per service, or the abort stalls in `PULLING` (Flow C).

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

18. **You wrote the REST API anyway.** Forty minutes on requirements, entities, and endpoints; the health plane never drawn. On an infra prompt: data flow first, entities beside the database box, three verbs — and the two state machines before any of it (§4, §5).

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 450" role="img" aria-label="Deployment system five-minute skeleton. Both state machines across the top; then the three-verb API, Postgres with its two indexes, and the stateless leased controller; then the health plane, the agent, and the gate numbers; then rollback as a deployment and the discovery table as an output; and a margin lane of the durations and the decoy.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="44" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="86.5">Deployment: PENDING → ROLLING(n) → BAKING(n) → … → SUCCEEDED · PAUSED · ABORTED → rollback deployment · SUPERSEDED</text>
  <text class="dg-s dg-c" x="495" y="102.5">Instance: ALLOCATED → PULLING → STARTING → HEALTHY → DRAINING → STOPPED · FAILED · LOST — every transition a CAS on version</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="30" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="148.5">API — three verbs</text>
  <text class="dg-s dg-c" x="180" y="164.5">PUT /services · POST /deployments · abort</text>
  <text class="dg-s dg-c" x="180" y="180.5">replicas + resources, never a host list</text>
  <circle class="dg-num" cx="30" cy="128" r="9"></circle>
  <text class="dg-num-t" x="30" y="131.4">2</text>
  <rect class="dg-box" x="350" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="148.5">Postgres — desired + transitions</text>
  <text class="dg-s dg-c" x="500" y="164.5">allocations (service_id, digest, state)</text>
  <text class="dg-s dg-c" x="500" y="180.5">hosts (pool, az, cpu_free, mem_free) · no beats</text>
  <circle class="dg-num" cx="350" cy="128" r="9"></circle>
  <text class="dg-num-t" x="350" y="131.4">3</text>
  <rect class="dg-box" x="670" y="128" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="148.5">Controller — stateless, leased</text>
  <text class="dg-s dg-c" x="815" y="164.5">tick 5 s: gap = desired − observed</text>
  <text class="dg-s dg-c" x="815" y="180.5">per-host CAS per stage · gate before advance</text>
  <circle class="dg-num" cx="670" cy="128" r="9"></circle>
  <text class="dg-num-t" x="670" y="131.4">4</text>
  <rect class="dg-box" x="30" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="232.5">Health plane</text>
  <text class="dg-s dg-c" x="180" y="248.5">Redis TTL 30 s → sweeper → LOST · budget 1 %/min</text>
  <circle class="dg-num" cx="30" cy="208" r="9"></circle>
  <text class="dg-num-t" x="30" y="211.4">5</text>
  <rect class="dg-box" x="350" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="232.5">Agent ×150 k</text>
  <text class="dg-s dg-c" x="500" y="248.5">beat / 10 s · reply = desired · SQLite · pull</text>
  <circle class="dg-num" cx="350" cy="208" r="9"></circle>
  <text class="dg-num-t" x="350" y="211.4">6</text>
  <rect class="dg-box" x="670" y="208" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="232.5">The gate, before advancing</text>
  <text class="dg-s dg-c" x="815" y="248.5">ready ≥ 99 % · crash 0 · err +0.5 pp · p99 1.2 ×</text>
  <circle class="dg-num" cx="670" cy="208" r="9"></circle>
  <text class="dg-num-t" x="670" y="211.4">7</text>
  <rect class="dg-box" x="30" y="284" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="308.5">Rollback = a deployment</text>
  <text class="dg-s dg-c" x="180" y="324.5">prev_digest · stages [100] · no bake · batched</text>
  <circle class="dg-num" cx="30" cy="284" r="9"></circle>
  <text class="dg-num-t" x="30" y="287.4">8</text>
  <rect class="dg-box" x="350" y="284" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="308.5">Discovery table — an output</text>
  <text class="dg-s dg-c" x="500" y="324.5">HEALTHY allocations → host:port · 15 s</text>
  <circle class="dg-num" cx="350" cy="284" r="9"></circle>
  <text class="dg-num-t" x="350" y="287.4">9</text>
  <rect class="dg-box" x="670" y="284" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="308.5">no_traffic gate</text>
  <text class="dg-s dg-c" x="815" y="324.5">readiness + crash-loops + a synthetic request</text>
  <text class="dg-lane" x="30" y="370">10 · IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="400.5">no whole-rollout timeout</text>
  <text class="dg-s dg-c" x="140" y="416.5">every duration has an owner</text>
  <rect class="dg-box" x="270" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="380" y="400.5">per-host 10 min</text>
  <text class="dg-s dg-c" x="380" y="416.5">per-stage max(30 min, 2 × expected)</text>
  <rect class="dg-box" x="510" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="400.5">surge 10 % · unavailable 5 %</text>
  <text class="dg-s dg-c" x="620" y="416.5">pin the last two digests</text>
  <rect class="dg-box" x="740" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="850" y="400.5">15 a day is a decoy</text>
  <text class="dg-s dg-c" x="850" y="416.5">150 k hosts is the load</text>
</svg>
</div>

<p class="diagram-cap">Badge 1 before any box, badge 4 before the API is finished. Badge 2's second line is the sentence the mock lost ten minutes to — say it before the interviewer has to — and the margin's first tile is the timeout you refuse to write, with the two you write instead.</p>

1. **Both state machines, top of the board, before any box.** Per deployment: `PENDING → ROLLING(n) → BAKING(n) → … → SUCCEEDED`, with `PAUSED`, `ABORTED → rollback deployment`, `SUPERSEDED`. Per instance: `ALLOCATED → PULLING → STARTING → HEALTHY → DRAINING → STOPPED`, terminals `FAILED · LOST`. Write beside them: *"every transition is a CAS on `version`; a replaced instance gets a new id."*
2. **The API: three verbs.** `PUT /services` (desired), `POST /deployments` (a digest), `abort` (returns a rollback deployment). Label it **"replicas + resources, never a host list."**
3. **Postgres — desired state and transitions.** `services · deployments · stages · allocations · hosts`. The two indexes: `allocations (service_id, digest, state)` and `hosts (pool, az, cpu_free, mem_free)`. **Heartbeats never land here.**
4. **The controller: stateless, leader-leased, level-triggered.** Every 5 s per service: `gap = desired(stage) − observed`; place or drain. Stage → bake → **gate before advancing** → next stage. **Per-host claim by conditional update, reserved per stage.** Write: *"a host death and a release are the same gap."*
5. **The health plane.** Agent → ingest sharded by `host_id` → **Redis TTL 30 s** → sweeper → `LOST` transitions in Postgres. **Only transitions.** Grace 2 × interval after a shard restart; **disruption budget 1 %/service/min.**
6. **The agent, ×150 k.** One heartbeat per host per 10 s carrying every instance; **the reply is the only downward channel.** Pull by digest through the rack cache; readiness probe run locally; **SQLite state, keeps running with no control plane.**
7. **The gate, as three numbers and a rule.** Liveness + readiness ≥ 99 % + crash-loops 0 + error ≤ baseline + 0.5 pp and p99 ≤ 1.2 × where there is traffic. **`no_traffic` services: readiness + crash-loops + a declared synthetic request.**
8. **Rollback = a deployment of `prev_digest`,** `stages: [100]`, no bake, still batched and health-checked. Only moved instances roll back.
9. **The discovery table** — `HEALTHY` allocations → `host:port` — materialised every 15 s. Label it **"the tier: an output."**
10. **In the margin, said not drawn:** *no whole-rollout timeout · per-host 10 min, per-stage max(30 min, 2 ×) · surge 10 % / unavailable 5 % · pin the last two digests · fifteen a day is a decoy — 150 k hosts is the load.*

---

## 15 · Variants — what actually changes

**The governing axis: how long desired state is enforced after the rollout ends, and whether a target can be replaced.** Every row has a spec, a fleet, stages with a gate, and something that rolls back. What moves is whether anything keeps watching after 100 % — which is the requirement the mock missed — and whether a target that dies can be re-created somewhere else.

| Product | Enforced after rollout? | Target replaceable? | The delta from this page |
|---|---|---|---|
| **Kubernetes Deployment controller** | **Forever** | Yes | This page as written. A Pod is an allocation; a ReplicaSet is the per-digest desired count (two of them during a rollout, exactly §7's `desired(v1)` and `desired(v2)`); the kubelet is the agent; the scheduler is §8 with a plugin pipeline for spread; readiness and liveness probes are §9's layers 1–2; **etcd's watch replaces the tick** — and PodDisruptionBudgets are §10's damping with a name. Say this row in one breath and the interviewer knows you know what you built |
| **Feature-flag rollout** (LaunchDarkly, Statsig) | Forever, but the target **pulls a value** | n/a — nothing to place | The IDE settings sync page. No placement, no capacity, no artifact: the "rollout" is `hash(user) % 100 < pct`, the gate is layer 3 only (metrics by cohort), and rollback is flipping the flag — instant, because nothing was moved. §7 and §10 do not exist; a client that missed the flag pulls it on next fetch |
| **OTA firmware rollout** | Until the next rollout | **No** — a bricked device is `LOST` forever | The Demand response page's §15 row. Placement vanishes (a device is its own host); §11 dominates — chunked, resumable, content-addressed pull over a bad link; the canary bake is **days**, and the gate's decisive metric is "came back after reboot." §9's rollback is another rollout, and the ones that bricked cannot take it |
| **Serverless deploy** (Lambda aliases, Cloud Run revisions) | Forever, **by the platform** | Yes, invisibly | No host inventory you can see; `replicas` becomes a concurrency limit; §8 collapses to **alias weights** — the stage is "10 % of invocations to the new revision" — and §9 survives entirely, because the gate is the same three layers over the same cohort comparison. The platform owns §7, §10, and §11 and you say which one you are trusting it with |
| **Database schema migration rollout** | **One-shot** | **No, and irreversible** | The Checkout and Payment processor pages' shape, not this one. Stages are *expand → migrate → contract*, the gate is query error rate and replication lag, and "rollback" is a **forward** migration, because the data already moved. No reconciler — there is nothing to keep converged after it is done. Say this row to show you know when the archetype does not apply |
| **Configuration push** to agents or devices | Forever, as a version | Yes | This page minus §8 and §11: no capacity, no artifact. The agent pulls a config version on the heartbeat reply, the tier is "which version does each host have," and **§7 and §10 survive verbatim** — including the disruption budget, because a config that crashes the agent on 10 k hosts at once is the same incident |
| **Upgrading the agent itself** | Forever | Yes — but the target is the thing doing the replacing | The row this page cannot fully handle and must name: a new agent that fails to start leaves a host with no agent to report it. The answer is a **supervisor** below the agent — systemd, or a second minimal agent — that rolls the agent back on a failed readiness, and a canary stage measured in hosts that came *back*, like OTA |

**The lesson:** the stages look the same in every row, and they are never the hard part. **Whether anything keeps watching after 100 %** is what decides whether §7 and §10 exist — and it is the half of the prompt that says *"keep running until redeployed,"* which is the half that is easy not to hear.
