# Design a Hosted Notebook Platform — Sandboxed Compute Sessions for Untrusted Code

## The question

> *"Design a hosted notebook platform — something like Colab. Users edit code in the browser and run it against a live kernel in an isolated environment. A workspace bundles their runtime and their files, and it can be created, suspended, resumed, and deleted. Five hundred thousand concurrently connected users, resume in under five seconds, files survive suspend and node loss, and every user is running code you did not write."*

**The product.** A data scientist opens a browser tab and gets a Python kernel with their files already there. They run a cell; the output — text, a plot, a table — appears under it while the code is still running. They install a package, it stays installed. They close the laptop for lunch; the platform quietly parks the session so it costs nothing while they are gone, and when they come back and press run, it is back in a few seconds with their files and, ideally, their variables. Meanwhile ten thousand other people are running whatever they like — including, occasionally, someone whose "notebook" is a crypto miner or an attempt to read the host's cloud credentials.

**What a working system delivers**

- A new workspace is interactive within single-digit seconds; a suspended one is back in under five.
- Output streams as it happens, survives the browser reconnecting mid-run, and a runaway `print` loop does not take the page down.
- A `pip install` survives suspend and resume without a full rebuild each time.
- Files never depend on the machine the code ran on; a host dying loses at most the variables in memory, never the notebook.
- One user's code cannot see, slow, or reach another user's session — or the platform's own credentials.
- An idle session costs the platform close to nothing, so five hundred thousand connected users do not mean five hundred thousand running VMs.

**Why this gets asked.** It is three problems that pull in different directions: running hostile code needs a hard boundary, interactivity needs that boundary to appear in seconds, and a workload that is 90 % idle needs the boundary to cost nothing while parked. Every substrate choice buys two of the three, and the round is watching which two you pick and whether you know what the third costs.

---

**Archetype:** sandboxed compute sessions — untrusted code needs a kernel boundary, interactivity needs a warm start, and the idle tail needs to cost nothing; every substrate choice buys two, and the design is what you do about the third.
**Cousins that reuse ~70% of this page:** Colab, Deepnote, Hex; Codex- and Devin-style agent sandboxes; cloud development environments (Codespaces, Replit, Gitpod); CI runners; serverless functions (Lambda and Cloud Run are this page with a millisecond lifecycle); online judges; browser-based data tools that run SQL or Python server-side. Also **any product that executes code it did not write, for many tenants, and has to be fast about it.**

**What's actually being graded:** whether you rank substrates by **which kernel the code shares** and pick a default with the GPU exception named; whether you draw the **session lifecycle as a state machine** and keep its transitions correct under retries and worker crashes; whether the **resume budget** is itemised — where the five seconds go, and what was pre-materialised so the common path is an attach rather than a rebuild; whether **egress** is treated as the most-attacked path with the cloud metadata endpoint named; and whether you separate **three durability classes** — files, runtime overlay, live memory — instead of promising to persist everything.

**Contrast to have ready:** *ChatGPT's hard problem is that a generation outlives the request that started it. This is the same shape one level down: a **session** outlives the tab, but a session has a kernel, a filesystem, and an adversary inside it. ChatGPT's resource is GPU-seconds you cannot autoscale; this page's resource is a host's RAM, and the whole economic argument is that a suspended session must hold none of it. The streaming half — output that survives a reconnect — is the ChatGPT page's §7–§8 verbatim, with a cell instead of a generation.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "This is sandboxed compute: every session runs code I have to assume is hostile, so the first decision is the isolation boundary, and everything about latency, density, and cost is optimised *subject to* that boundary rather than the other way round. I'll separate a stateless control plane — auth, scheduling, the lifecycle state machine, quotas — from a data plane of per-session sandboxes on a host fleet. Three things dominate. First, the **substrate**: plain containers share the host kernel, so one kernel CVE is every tenant; I'll rank by what kernel is shared and default to a microVM — Firecracker — because it snapshots and restores in about a second, which is the second thing. **The resume budget**: five seconds rules out a cold boot, so the common path is *attach to a restored snapshot*, with warm pools for creates and a cold-boot fallback that is slower but always available. Third, **the idle tail**: five hundred thousand connected users are mostly idle, and a suspended session has to cost zero host RAM — that is suspend-to-snapshot, and it is the number that makes the fleet affordable. I'll draw the session state machine before any service, go deep on the substrate and the resume path, and on isolation — especially egress, because that is where credentials get stolen. Real-time collaboration is out of scope unless you want it."

**Why open this way:** it puts the adversary first, which is the requirement the prompt calls non-negotiable; it names the substrate with its reason before the interviewer asks "why not containers"; it pre-commits the state machine (the plateau card's rule — draw it before the boxes) and the two dives (§7, §8) that carry the round; and it says the idle-tail number is the economic argument, so the suspend mechanism arrives as a consequence rather than a feature.

---

## 1 · Functional requirements

1. **A workspace lifecycle**: create, suspend, resume, delete — with **files always durable**, saved state durable across suspend/resume and node loss, and in-memory kernel state **best-effort** restored on resume.
2. **Execute untrusted code interactively** in an isolated sandbox per session, with `stdout`, `stderr`, and rich output (plots, tables, images) **streamed to the browser as it happens**, resumable after a disconnect, and with the execution continuing whether or not anyone is watching.
3. **Environment persistence**: packages a user installs survive suspend and resume without a full rebuild, and a workspace's files can be uploaded, downloaded, and edited from the browser.

**Out of scope (say them):** real-time multi-user collaboration on one notebook (the Figma page's problem — say so), the notebook file format and the editor itself, the package registry, billing for compute (the billing page), scheduled or batch job execution (§15), model training orchestration, enterprise SSO.

**Below the line, likely follow-ups:** GPU workspaces (§7, §15), free vs paid tiers with different idle timeouts and resume priority, secrets injection into a sandbox, custom images, multi-region placement, sharing a notebook read-only, abuse detection at scale (§9).

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Isolation** | **Untrusted by default; no shared host kernel between tenants.** A sandbox escape is bounded to one host, and one host runs one *tier* of tenant | The non-negotiable. It rules out plain containers as the default before any performance number is considered (§7) |
| **Resume latency** | **p95 < 5 s** for a recently suspended, common-image workspace; **p99 < 30 s** cold-boot fallback, always available | Five seconds is "I pressed run and it ran." The fallback exists because the fast path depends on a snapshot and a warm pool, and both can be missing |
| **Create latency** | **p95 < 8 s** for a fresh workspace from a curated image | A warm pool of pre-booted sandboxes turns create into "attach and mount"; the number is the pool's job |
| **Concurrency** | **500 k connected**; ~15 % executing at peak → **~75 k active sandboxes**; **~10× active suspended** → ~750 k parked | The ratio is the design. Active sizes the fleet; suspended must cost ~0 host RAM (§3) |
| **Durability** | Files and saved state: **11 nines, survive node, zone, and region loss**; runtime overlay: **rebuildable**, cached; in-memory kernel state: **best-effort snapshot**, lost on host death | Three classes, named. A design that promises to persist variables has promised something a host failure will break (§11) |
| **Output streaming** | First byte of output **< 200 ms** after a cell starts; **resumable** after a disconnect with no gaps or reorders; **output capped** per cell with a truncation marker | The interactive feel is the product; the cap is what keeps `while True: print()` from being a denial of service on the gateway (§10) |
| **Idle policy** | Auto-suspend after **30 min** idle (tier-configurable); suspended sessions **hold zero host CPU and RAM** | This is the number that makes 500 k users affordable. A suspended session is a file in object storage |
| **Noisy neighbour** | Per-sandbox CPU, memory, disk I/O, and egress bandwidth caps; **a fork bomb or a miner degrades only its own session** | cgroups on the host side of the boundary; the abuse response is automated (§9) |
| **Fault tolerance** | Survives: any host (active sessions on it die and resume from their last snapshot ≤ 5 min old; files are untouched), any cell's scheduler (sessions keep running; new transitions queue), object storage degraded (resumes fall back to cold boot). **Does not survive: the control-plane database down** — no lifecycle transitions; running sessions keep running and streaming until their idle timer, which cannot fire either, so they run until the database returns. Bounded, and the cost is compute, not data | Name the failure. Here it is "no new sessions and no suspends for the duration," and the blast radius is a cell, not the fleet (§11) |
| **Scale** | ~1,200 hosts per region for active sessions; **50 cells** of ~10 k users each | §3 |

**The sentence that earns the point:** *"The three things I'm allowed to lose are the variables in memory, the packages someone installed, and the warm pool — in that order of how much I'll fight for them. The one thing I'm never allowed to lose is a file, and the one thing I'm never allowed to share is a kernel. Everything on this page follows from those two lists."*

---

## 3 · Numbers that reframe the problem

**The active fleet is sized by RAM, and it is about twelve hundred hosts**

- *Assumption:* 500 k connected, **15 % executing** → **75 k active sandboxes** at peak. A session is **1–2 vCPU, 2–4 GB RAM**; call it 2 vCPU and 4 GB.
- 75 k × 4 GB = **300 TB of RAM**; 75 k × 2 vCPU = 150 k vCPU. On 256 GB / 128 vCPU hosts that is **~1,200 hosts by RAM, ~1,170 by CPU** — RAM binds, barely, and CPU can be overcommitted 3–4× on an interactive workload because most active sessions are waiting for a human between cells. **Say which dimension binds**; it decides the host shape.

**The idle tail is six times the fleet if it holds RAM, and a rounding error if it does not**

- ~750 k suspended sessions × 4 GB = **3 PB** of RAM if suspended means "still resident" → **~12,000 more hosts**, seven times the active fleet, for sessions doing nothing.
- Suspended as a **snapshot on disk**: memory compresses 3–5×, so ~1 GB per session → **~750 TB of object storage**, a few tens of thousands of dollars a month. **This single ratio is the reason suspend-to-snapshot exists**, and it is the number to say when the interviewer asks why not just keep them running.

**The resume budget, itemised, is why the common path is an attach**

- A cold boot: pull a multi-GB image (**10–60 s**), start a microVM (~150 ms), boot a guest kernel (~1 s), start the Python kernel and import the user's usual libraries (**2–10 s**), mount files. **Tens of seconds** — the 5 s target is not reachable from cold.
- A snapshot restore: fetch ~1 GB from local NVMe cache (**< 1 s**) or object storage (**2–4 s**), restore memory pages lazily (~200 ms to first instruction), reattach network and the file mount (~300 ms), reconnect the WebSocket (~100 ms). **1–2 s from cache, 3–5 s from object storage.** The budget is met only if the image was never pulled on the critical path and the snapshot is near. **Both are pre-materialisation, and both are the design.**

**Warm pool size is arrival rate times cold start**

- *Assumption:* **100 new sessions/s** at peak (creates plus resumes that missed their snapshot). Cold-boot time ~3 s from a pre-baked image on the host → **Little's law: ~300 sandboxes must be pre-booted** to absorb arrivals; hold **~1,000** per region for headroom. At 4 GB each that is 4 TB of RAM — **16 hosts, 1.3 % of the fleet**, buying single-digit-second creates for everyone.

**Egress is the most-attacked path, and it has one address on it**

- Every cloud host answers `169.254.169.254` with the instance's credentials. From inside a sandbox on that host, one `curl` — unless the boundary blocks it. **This is the first thing a hostile notebook tries**, and it is the number-one item in §9 because it is a single address that turns a tenant escape into a platform compromise.

**Blast radius: fifty cells, not one cluster**

- 500 k users in **50 cells of ~10 k** — each with its own scheduler, host pool, and control-plane shard. A bad scheduler deploy, a poisoned warm pool, or a runaway cell takes down **2 % of users**, and a cell can be drained and rebuilt in minutes. The number is arbitrary; the shape is not.

---

## 4 · Core entities

### Draw this first — the session state machine

```text
                     ┌──────────────────────────────────────────────────┐
                     ▼                                                  │
CREATING ──▶ READY ──▶ RUNNING ──▶ IDLE ──▶ SUSPENDING ──▶ SUSPENDED ──▶ RESUMING
   │          │  ▲        │          │          │              │              │
   │          └──┘        └──────────┘          │              ▼              │
   ▼         (cell runs)  (cell ends)           │          DELETING ──▶ DELETED (terminal)
 FAILED                                          ▼
 (create)                                    FAILED → RESUMING (retry) | cold boot
```

| Transition | Caused by | Component that owns it | Recorded where | Timer |
|---|---|---|---|---|
| `CREATING → READY` | A warm sandbox is claimed, files mounted, kernel attached | Scheduler (cell) + host agent | `sessions` row, CAS on `version` | 8 s create SLO |
| `READY ↔ RUNNING` | A cell starts / all cells end | Kernel manager on the host | `sessions.last_activity` | — |
| `READY → IDLE` | No activity for the tier's idle window | **Idle reaper** (cell) | `sessions` row | 30 min |
| `IDLE → SUSPENDING → SUSPENDED` | Reaper requests; host agent snapshots memory + overlay, uploads, frees the VM | Host agent, then the reaper on upload ack | `sessions` row + `snapshots` row | Snapshot ≤ 60 s or **terminate without memory** |
| `SUSPENDED → RESUMING → READY` | User action; scheduler picks a host, restores the snapshot, reattaches | Scheduler + host agent | `sessions` row (CAS) | 5 s SLO; fallback to cold boot at 15 s |
| `any → DELETING → DELETED` | User deletes; files tombstoned, snapshots and overlay garbage-collected | Control plane + a GC job | `sessions` row; `workspaces.deleted_at` | GC after 30 d |
| `CREATING / RESUMING → FAILED` | Host died, snapshot corrupt, pool empty and cold boot failed | Whoever held the lease, or the lease expiring | `sessions` row | Lease 30 s |

**The rule, and it is the whole method:** *every transition is a compare-and-set on the session row's `version`, owned by exactly one component holding a lease, and a duplicate event is a no-op because the CAS fails.* A resume request that arrives twice, a scheduler that crashes after picking a host but before recording it, a reaper and a user racing to suspend and resume the same session — all of these are the same case: the second writer loses the CAS, reads the current state, and does the right thing for *that* state. Without the machine, "correct under retries" is a wish.

### The entities

- **Workspace** — `(workspace_id, owner, tier, image_id, files_root, overlay_ref, deleted_at)`. The durable thing: files and the runtime overlay reference. Outlives every session.
- **Session** — `(session_id, workspace_id, state, version, host_id, sandbox_id, snapshot_ref, last_activity, lease_holder, lease_until)`. One live or parked instance of a workspace. **The row the state machine lives on.**
- **Snapshot** — `(snapshot_ref, session_id, memory_uri, overlay_uri, image_id, taken_at, size)`. A parked session's memory and disk delta, in object storage, with a copy in the host-local NVMe cache if it was taken recently.
- **Image** — a curated base (Python + the common scientific stack), **pre-baked onto every host** and pre-booted in the warm pool. Content-addressed.
- **Overlay** — the writable layer above the image: `pip install` lands here. Snapshotted separately from memory, **content-hashed, and shareable** between sessions of the same workspace.
- **Host** — `(host_id, cell, capacity, substrate: microvm | gpu-vm, healthy, sandboxes[])`.
- **Cell output log** — per session, an append-only sequence of `(seq, cell_id, stream, chunk | blob_ref)` — the thing the browser streams from and resumes against (§10).

**The three that are load-bearing:**

**The session row's `version` is the concurrency control for the whole lifecycle.** There is no lock service and no workflow engine: one row, one integer, and every actor does `UPDATE sessions SET state = $next, version = version + 1 WHERE session_id = $id AND version = $expected`. A host agent that finishes a snapshot after the reaper timed out and moved on loses the CAS and discards the snapshot. That is the entire correctness story for create, suspend, resume, and delete under crashes.

**The overlay is separate from memory, and it is the thing that makes `pip install` survive.** Memory is best-effort; the overlay is a disk delta above a content-addressed image, and it is snapshotted on every suspend as its own object. Resume mounts image + overlay and — if the memory snapshot is missing or stale — boots a fresh kernel on top: packages present, variables gone. **Two durability classes, two objects, and the user-visible promise is exactly what each can keep.**

**The warm pool holds sandboxes that have never seen a user, and that is a security property.** A pre-booted microVM is safe to hand to anyone *only* if nothing in it is per-tenant: no credentials, no files, and — the one people miss — **no entropy or host keys generated before the fork.** Restoring many sessions from one golden snapshot means every one of them has the same random seed and the same SSH host key until something reseeds them. Reseeding at attach time is a line in the host agent and the difference between a warm pool and a shared secret (§7, §9).

---

## 5 · API

```text
── control plane ─────────────────────────────────────────────────────────────
POST /v1/workspaces                { name, image_id, tier }                 → 201 { workspace_id }
DELETE /v1/workspaces/{id}                                                  → 202  (async GC)
POST /v1/workspaces/{id}/sessions  Idempotency-Key: <k>                     → 202 { session_id, state: CREATING | RESUMING }
     — one call for "open": creates if no session exists, resumes if one is SUSPENDED, no-op if READY
POST /v1/sessions/{id}/suspend                                              → 202 { state: SUSPENDING }
GET  /v1/sessions/{id}                                                      → 200 { state, version, host, resume_eta_ms }
     — poll or subscribe; the browser shows "resuming…" off this, not off the socket

── data plane, via the streaming gateway (WebSocket) ─────────────────────────
WS   /v1/sessions/{id}/attach?after=<seq>        ← resume from the last seq the client saw
  ▶ { type: "exec",   cell_id, code, exec_id }    exec_id is the client's idempotency key
  ▶ { type: "interrupt", exec_id }
  ◀ { seq, cell_id, exec_id, stream: stdout | stderr | display | status, chunk }
  ◀ { seq, cell_id, exec_id, stream: display, blob: { uri, mime, bytes } }     ← rich output sideloaded
  ◀ { seq, cell_id, exec_id, stream: status, state: running | done | error | truncated }

── files ─────────────────────────────────────────────────────────────────────
PUT  /v1/workspaces/{id}/files/{path}   (multipart, or a presigned upload URL for > 10 MB)
GET  /v1/workspaces/{id}/files/{path}
  — files are in the workspace, not the session; they exist whether or not a sandbox is running
```

**Decisions to narrate, unprompted:**

- **"Open" is one idempotent call that does create-or-resume.** The browser does not know whether a session exists, and should not have to; the control plane reads the session row and takes the right transition. The `Idempotency-Key` makes a double-click one session.
- **`attach?after=seq` is the whole resumability story.** Every output chunk carries a sequence number from the session's output log; a reconnecting client says the last one it saw and gets exactly the gap, in order. The same code path serves first attach (`after=0`) and reconnect — one path, not two.
- **`exec_id` is the client's, and it is idempotent.** A retried "run cell" after a dropped socket must not run the cell twice. The kernel manager dedupes on it.
- **Rich output is a reference, not a payload.** A 20 MB plot goes to object storage and the stream carries its URI; the text stream stays small and fast, and the blob is fetched with a presigned URL. Inlining it would head-of-line-block every `print` behind it.
- **Files live on the workspace, not the session.** Upload works while suspended; nothing about a file depends on a sandbox existing. This is the API-level statement of the durability class.
- **`resume_eta_ms` on the status.** The client renders a progress state from the control plane's estimate — warm-pool hit, snapshot in cache, snapshot in object storage, cold boot — so a 25 s fallback is a labelled wait, not a hang.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 660" role="img" aria-label="Sandboxed compute architecture, one cell. Control plane: an API, Postgres holding workspaces and sessions with a version column for compare-and-set, a scheduler and an idle reaper. Data plane: hosts running a host agent, Firecracker microVMs one per session behind cgroups, a warm pool of pre-booted sandboxes, an NVMe snapshot cache, and a per-host egress proxy that blocks the metadata endpoint. Storage: object storage for workspace files, snapshots and overlays, with a content-addressed layer cache. Streaming: a stateless WebSocket gateway tailing per-session output logs in Redis Streams. GPU hosts are a separate substrate with no suspend.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">A guest kernel per session, nothing shared; resume is an attach to a restored snapshot; an idle session holds zero host RAM.</text>
  <rect class="dg-group" x="20" y="86" width="300" height="260" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">CONTROL PLANE — DECIDES, RUNS NO CODE</text>
  <rect class="dg-box" x="36" y="118" width="268" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="170" y="142.5">API</text>
  <text class="dg-s dg-c" x="170" y="158.5">open = create-or-resume · idempotent</text>
  <path class="dg-box" d="M 36,197 L 36,247 A 134,7 0 0 0 304,247 L 304,197 A 134,7 0 0 0 36,197 Z"></path>
  <path class="dg-box" d="M 36,197 A 134,7 0 0 0 304,197" style="fill:none"></path>
  <text class="dg-t dg-c" x="170" y="214">Postgres, per cell</text>
  <text class="dg-s dg-c" x="170" y="230">workspaces · sessions (state, version, lease)</text>
  <text class="dg-s dg-c" x="170" y="246">UPDATE … WHERE version = $expected</text>
  <rect class="dg-box" x="36" y="270" width="128" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="100" y="296.5">Scheduler</text>
  <text class="dg-s dg-c" x="100" y="312.5">cache affinity</text>
  <rect class="dg-box" x="176" y="270" width="128" height="60" rx="8"></rect>
  <text class="dg-t dg-c" x="240" y="296.5">Idle reaper</text>
  <text class="dg-s dg-c" x="240" y="312.5">30 min → suspend</text>
  <path class="dg-line" d="M 170,174 L 170,182"></path>
  <path class="dg-head" d="M 165,182 L 175,182 L 170,190 Z"></path>
  <path class="dg-line" d="M 100,254 L 100,262"></path>
  <path class="dg-head" d="M 95,262 L 105,262 L 100,270 Z"></path>
  <path class="dg-line" d="M 240,254 L 240,262"></path>
  <path class="dg-head" d="M 235,262 L 245,262 L 240,270 Z"></path>
  <rect class="dg-group" x="350" y="86" width="630" height="260" rx="12"></rect>
  <text class="dg-group-t" x="366" y="108">DATA PLANE — HOSTS, ~1,200 PER REGION, 50 CELLS</text>
  <rect class="dg-box" x="366" y="118" width="290" height="110" rx="8"></rect>
  <text class="dg-t dg-c" x="511" y="153.5">Host agent</text>
  <text class="dg-s dg-c" x="511" y="169.5">runs microVMs · snapshots · file agent</text>
  <text class="dg-s dg-c" x="511" y="185.5">cgroups: cpu · mem · pids · egress</text>
  <text class="dg-s dg-c" x="511" y="201.5">holds the scoped token; the guest holds none</text>
  <path class="dg-line" d="M 304,300 L 336,300 L 336,173 L 358,173"></path>
  <path class="dg-head" d="M 358,178 L 358,168 L 366,173 Z"></path>
  <text class="dg-lbl dg-c" x="336" y="165">place</text>
  <rect class="dg-good" x="686" y="118" width="278" height="56" rx="8"></rect>
  <text class="dg-good-t dg-c" x="825" y="142.5">Firecracker microVM × N</text>
  <text class="dg-s dg-c" x="825" y="158.5">guest kernel · kernel manager · overlay</text>
  <path class="dg-line" d="M 656,146 L 678,146"></path>
  <path class="dg-head" d="M 678,151 L 678,141 L 686,146 Z"></path>
  <rect class="dg-good" x="686" y="190" width="114" height="38" rx="8"></rect>
  <text class="dg-good-t dg-c" x="743" y="213.5">Warm pool</text>
  <rect class="dg-box" x="826" y="190" width="138" height="38" rx="8"></rect>
  <text class="dg-t dg-c" x="895" y="213.5">GPU: full VM</text>
  <rect class="dg-warn" x="686" y="246" width="278" height="84" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="825" y="268.5">Egress proxy, per host</text>
  <text class="dg-s dg-c" x="825" y="284.5">blocks 169.254.169.254 + RFC 1918</text>
  <text class="dg-s dg-c" x="825" y="300.5">allowlist registries · logs every dest</text>
  <text class="dg-s dg-c" x="825" y="316.5">the abuse signal</text>
  <path class="dg-line" d="M 813,174 L 813,238"></path>
  <path class="dg-head" d="M 808,238 L 818,238 L 813,246 Z"></path>
  <path class="dg-box" d="M 366,253 L 366,323 A 145,7 0 0 0 656,323 L 656,253 A 145,7 0 0 0 366,253 Z"></path>
  <path class="dg-box" d="M 366,253 A 145,7 0 0 0 656,253" style="fill:none"></path>
  <text class="dg-t dg-c" x="511" y="280">NVMe snapshot cache</text>
  <text class="dg-s dg-c" x="511" y="296">last suspend, 24 h</text>
  <text class="dg-s dg-c" x="511" y="312">resume &lt; 1 s from here</text>
  <path class="dg-line" d="M 511,228 L 511,238"></path>
  <path class="dg-head" d="M 506,238 L 516,238 L 511,246 Z"></path>
  <rect class="dg-group" x="20" y="380" width="500" height="130" rx="12"></rect>
  <text class="dg-group-t" x="36" y="402">STORAGE — THE THREE CLASSES</text>
  <path class="dg-box" d="M 36,419 L 36,489 A 75,7 0 0 0 186,489 L 186,419 A 75,7 0 0 0 36,419 Z"></path>
  <path class="dg-box" d="M 36,419 A 75,7 0 0 0 186,419" style="fill:none"></path>
  <text class="dg-t dg-c" x="111" y="446">Files</text>
  <text class="dg-s dg-c" x="111" y="462">object storage · 11 nines</text>
  <text class="dg-s dg-c" x="111" y="478">never on a host</text>
  <path class="dg-box" d="M 206,419 L 206,489 A 75,7 0 0 0 356,489 L 356,419 A 75,7 0 0 0 206,419 Z"></path>
  <path class="dg-box" d="M 206,419 A 75,7 0 0 0 356,419" style="fill:none"></path>
  <text class="dg-t dg-c" x="281" y="446">Overlays</text>
  <text class="dg-s dg-c" x="281" y="462">disk delta · rebuildable</text>
  <text class="dg-s dg-c" x="281" y="478">pip install survives</text>
  <path class="dg-box" d="M 376,419 L 376,489 A 64,7 0 0 0 504,489 L 504,419 A 64,7 0 0 0 376,419 Z"></path>
  <path class="dg-box" d="M 376,419 A 64,7 0 0 0 504,419" style="fill:none"></path>
  <text class="dg-t dg-c" x="440" y="446">Snapshots</text>
  <text class="dg-s dg-c" x="440" y="462">memory · best-effort</text>
  <text class="dg-s dg-c" x="440" y="478">aged out at 30 d</text>
  <path class="dg-line" d="M 450,330 L 450,360 L 281,360 L 281,404"></path>
  <path class="dg-head" d="M 276,404 L 286,404 L 281,412 Z"></path>
  <path class="dg-line" d="M 560,330 L 560,365 L 440,365 L 440,404"></path>
  <path class="dg-head" d="M 435,404 L 445,404 L 440,412 Z"></path>
  <text class="dg-lbl" x="470" y="352">suspend: upload, free the VM</text>
  <rect class="dg-group" x="550" y="380" width="430" height="130" rx="12"></rect>
  <text class="dg-group-t" x="566" y="402">STREAMING</text>
  <path class="dg-box" d="M 566,419 L 566,489 A 100,7 0 0 0 766,489 L 766,419 A 100,7 0 0 0 566,419 Z"></path>
  <path class="dg-box" d="M 566,419 A 100,7 0 0 0 766,419" style="fill:none"></path>
  <text class="dg-t dg-c" x="666" y="446">Redis Streams</text>
  <text class="dg-s dg-c" x="666" y="462">one log per session · seq</text>
  <text class="dg-s dg-c" x="666" y="478">24 h · compacted on suspend</text>
  <rect class="dg-box" x="786" y="412" width="178" height="84" rx="8"></rect>
  <text class="dg-t dg-c" x="875" y="442.5">WS gateway</text>
  <text class="dg-s dg-c" x="875" y="458.5">stateless · tails by seq</text>
  <text class="dg-s dg-c" x="875" y="474.5">attach?after=seq</text>
  <path class="dg-line" d="M 766,454 L 778,454"></path>
  <path class="dg-head" d="M 778,459 L 778,449 L 786,454 Z"></path>
  <path class="dg-line" d="M 656,205 L 670,205 L 670,404"></path>
  <path class="dg-head" d="M 665,404 L 675,404 L 670,412 Z"></path>
  <text class="dg-lbl" x="676" y="372">output via vsock</text>
  <text class="dg-s" x="20" y="550">The session row says what should be; the host agent says what is; a reconciler fixes the difference. Nothing on a host is a source of truth.</text>
  <text class="dg-s" x="20" y="572">Suspended sessions: ~750 k × ~1 GB in object storage. Resident, they would be seven times the fleet.</text>
  <text class="dg-note" x="20" y="594">Reseed entropy and host keys at every attach — a golden snapshot restored without it is a shared secret.</text>
</svg>
</div>

<p class="diagram-cap">Draw the microVM box with its label — a guest kernel per session — before any latency number, then the egress proxy beside it with the one address it blocks. The three cylinders at the bottom are three promises; say which one is best-effort while you draw it.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 620" role="img" aria-label="Sandboxed compute high-level design in three lanes. Resume: compare-and-set the session row to resuming under a lease, pick a host by cache affinity, restore the snapshot lazily, reseed, attach network and files, and compare-and-set to ready; fallbacks at fifteen seconds to a cold boot with the overlay, then without it. Run a cell: the kernel manager writes sequence-numbered chunks to the session log; the gateway tails it; a disconnect changes nothing for execution; the client resumes from the last sequence; output is capped with a marker and blobs go by reference. Suspend and abuse: the idle reaper drives the machine, a snapshot that misses the budget keeps only the overlay, and a fork bomb is contained by cgroups, caught by egress logs, and suspended automatically.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Every transition is a compare-and-set under a lease; the resume budget is an attach, not a rebuild; the log outlives the socket.</text>
  <text class="dg-lane" x="30" y="76">RESUME — ~2 s FROM CACHE, ~5 s FROM OBJECT STORAGE, FALLBACKS ALWAYS AVAILABLE</text>
  <rect class="dg-box" x="30" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="114.5">SUSPENDED → RESUMING</text>
  <text class="dg-s dg-c" x="140" y="130.5">CAS on version · 30 s lease</text>
  <text class="dg-s dg-c" x="140" y="146.5">duplicate request → CAS fails</text>
  <rect class="dg-box" x="280" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="390" y="114.5">pick host by affinity</text>
  <text class="dg-s dg-c" x="390" y="130.5">the one holding the snapshot</text>
  <text class="dg-s dg-c" x="390" y="146.5">unless &gt; 85 % RAM</text>
  <path class="dg-line" d="M 250,126 L 272,126"></path>
  <path class="dg-head" d="M 272,131 L 272,121 L 280,126 Z"></path>
  <rect class="dg-good" x="530" y="90" width="220" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="640" y="114.5">restore · reseed · attach</text>
  <text class="dg-s dg-c" x="640" y="130.5">lazy pages 200 ms</text>
  <text class="dg-s dg-c" x="640" y="146.5">entropy · keys · NIC · mount</text>
  <path class="dg-line" d="M 500,126 L 522,126"></path>
  <path class="dg-head" d="M 522,131 L 522,121 L 530,126 Z"></path>
  <rect class="dg-good" x="780" y="90" width="200" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="880" y="114.5">→ READY</text>
  <text class="dg-s dg-c" x="880" y="130.5">restored_memory: true</text>
  <text class="dg-s dg-c" x="880" y="146.5">client attach?after=</text>
  <path class="dg-line" d="M 750,126 L 772,126"></path>
  <path class="dg-head" d="M 772,131 L 772,121 L 780,126 Z"></path>
  <rect class="dg-warn" x="530" y="176" width="450" height="44" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="755" y="202.5">15 s → cold boot with overlay (packages kept) → then without it</text>
  <path class="dg-line" d="M 640,162 L 640,168"></path>
  <path class="dg-head" d="M 635,168 L 645,168 L 640,176 Z"></path>
  <path class="dg-div" d="M 20,236 L 980,236"></path>
  <text class="dg-lane" x="30" y="270">RUN A CELL — THE LOG OUTLIVES THE SOCKET</text>
  <rect class="dg-box" x="30" y="284" width="220" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="308.5">exec {cell, exec_id}</text>
  <text class="dg-s dg-c" x="140" y="324.5">kernel manager dedupes</text>
  <text class="dg-s dg-c" x="140" y="340.5">on exec_id</text>
  <rect class="dg-good" x="280" y="284" width="220" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="390" y="308.5">output → session log</text>
  <text class="dg-s dg-c" x="390" y="324.5">seq · cell · stream · chunk</text>
  <text class="dg-s dg-c" x="390" y="340.5">Redis Streams via vsock</text>
  <path class="dg-line" d="M 250,320 L 272,320"></path>
  <path class="dg-head" d="M 272,325 L 272,315 L 280,320 Z"></path>
  <rect class="dg-box" x="530" y="284" width="220" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="640" y="308.5">gateway tails by seq</text>
  <text class="dg-s dg-c" x="640" y="324.5">stateless · any gateway</text>
  <text class="dg-s dg-c" x="640" y="340.5">any session</text>
  <path class="dg-line" d="M 500,320 L 522,320"></path>
  <path class="dg-head" d="M 522,325 L 522,315 L 530,320 Z"></path>
  <rect class="dg-warn" x="780" y="284" width="200" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="880" y="308.5">client drops</text>
  <text class="dg-s dg-c" x="880" y="324.5">execution continues</text>
  <text class="dg-s dg-c" x="880" y="340.5">reconnect: after=seq</text>
  <path class="dg-line" d="M 750,320 L 772,320"></path>
  <path class="dg-head" d="M 772,325 L 772,315 L 780,320 Z"></path>
  <rect class="dg-warn" x="280" y="372" width="220" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="390" y="396.5">cap → status: truncated</text>
  <text class="dg-s dg-c" x="390" y="412.5">process keeps running</text>
  <rect class="dg-box" x="530" y="372" width="220" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="640" y="396.5">blob → object storage</text>
  <text class="dg-s dg-c" x="640" y="412.5">display event carries the URI</text>
  <path class="dg-line" d="M 390,356 L 390,364"></path>
  <path class="dg-head" d="M 385,364 L 395,364 L 390,372 Z"></path>
  <path class="dg-line" d="M 640,356 L 640,364"></path>
  <path class="dg-head" d="M 635,364 L 645,364 L 640,372 Z"></path>
  <path class="dg-div" d="M 20,446 L 980,446"></path>
  <text class="dg-lane" x="30" y="480">SUSPEND AND ABUSE — THE REAPER DRIVES; CGROUPS CONTAIN; EGRESS LOGS CATCH</text>
  <rect class="dg-box" x="30" y="494" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="175" y="514.5">IDLE → SUSPENDING</text>
  <text class="dg-s dg-c" x="175" y="530.5">snapshot memory + overlay → upload</text>
  <text class="dg-s dg-c" x="175" y="546.5">CAS to SUSPENDED on ack · free RAM</text>
  <rect class="dg-warn" x="350" y="494" width="290" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="495" y="514.5">budget missed (60 s)?</text>
  <text class="dg-s dg-c" x="495" y="530.5">keep the overlay only</text>
  <text class="dg-s dg-c" x="495" y="546.5">has_memory: false</text>
  <path class="dg-line" d="M 320,526 L 342,526"></path>
  <path class="dg-head" d="M 342,531 L 342,521 L 350,526 Z"></path>
  <rect class="dg-warn" x="670" y="494" width="290" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="815" y="514.5">fork bomb / miner</text>
  <text class="dg-s dg-c" x="815" y="530.5">pid cap inside its own VM</text>
  <text class="dg-s dg-c" x="815" y="546.5">egress denied + logged → auto-suspend</text>
  <text class="dg-note" x="30" y="590">Three durability classes, said in one breath: files always · overlay kept and rebuildable · memory best-effort.</text>
</svg>
</div>

<p class="diagram-cap">The top lane's last box is what the five seconds buys, and the warning strip under it is what makes the SLO an SLO rather than an availability claim. The middle lane is the ChatGPT page's run lifecycle with a cell in place of a generation: the socket carries nothing the log does not already have.</p>

### Flow A — resume, on the fast path

1. The user opens a suspended workspace. `POST /workspaces/{id}/sessions`. The API reads the session row: `SUSPENDED`, `version 41`, `snapshot_ref` taken 40 minutes ago. CAS to `RESUMING`, `version 42`, lease to the cell's scheduler for 30 s.
2. The scheduler picks a host: **preferably the one whose NVMe cache holds this snapshot** (the host it was suspended on, if healthy and not full), else any host in the cell with capacity. It tells the host agent: restore `snapshot_ref` as a new microVM.
3. The host agent fetches the memory snapshot — **from local cache, < 1 s**; from object storage, 2–4 s — mounts image + overlay, restores the VM with lazy page loading so the guest is executing in ~200 ms, **reseeds entropy and regenerates host keys**, reattaches the virtual NIC behind the egress proxy, mounts the workspace files. ~1.5 s from cache.
4. The agent reports ready; the scheduler CASes the row to `READY`, `version 43`, and the API's status endpoint flips. The browser, polling status, opens `attach?after=<last seq>` and is live. **p50 ~2 s, p95 ~4 s** (→ ties to the resume-latency NFR).
5. The user runs a cell; the variables from before lunch are still there. That was the best-effort promise, kept.
6. **The failure path.** The memory snapshot is corrupt, or the host the cache was on died and object storage is slow. At **15 s** the agent abandons the restore and **cold-boots**: image + overlay mounted, fresh kernel, no memory. The row goes to `READY` with `restored_memory: false`; the client shows "your packages are here; variables were not restored." Packages survived because the overlay is its own object (§11). **The user lost the thing the NFR said they might, and nothing else.**

### Flow B — create, from the warm pool

1. `POST /workspaces` then open. No session exists; the API inserts a row in `CREATING` and leases it to the scheduler.
2. The scheduler **claims a pre-booted sandbox from the cell's warm pool** — a microVM already past kernel boot and Python import, sitting at an attach point, never assigned. Claim is a CAS on the pool entry.
3. The host agent attaches: reseeds entropy, injects the session's identity (a short-lived scoped token for the file mount, nothing else), mounts the empty workspace, connects the NIC. ~500 ms.
4. `READY`. The browser attaches. **p95 ~3 s**, most of it the control plane round trips.
5. A pool replenisher notices the pool is one short and boots a replacement in the background — the cold boot happens off the critical path, which is the whole point.
6. **The failure path.** The pool is empty — a viral course assignment sent 5,000 creates in a minute. Creates **fall back to cold boot** (~10–20 s from the pre-baked image), the status endpoint says so with an ETA, and the replenisher scales the pool target up from the arrival rate. **Paid tiers claim from the pool first** — a product decision worth stating — so free-tier creates absorb the wait. Nothing fails; the create SLO is missed, and the metric that missed it (`pool_depth`) was the leading indicator an hour earlier.

### Flow C — a cell runs, the browser drops, the code keeps going

1. The client sends `exec {cell_id, code, exec_id}`. The kernel manager inside the sandbox dedupes on `exec_id`, starts execution, and writes each output chunk to the **session's output log** with a monotonic `seq`. The streaming gateway tails the log to the socket.
2. The user's laptop sleeps mid-run. The socket closes. **Execution continues** — the kernel does not know or care about the socket; the log keeps filling. This is the ChatGPT page's "the run outlives the connection," with a cell in place of a generation.
3. The cell prints two million lines. At the **per-cell output cap** (say 10 MB of text) the kernel manager stops writing chunks, appends a single `status: truncated` event, and keeps the process running. The gateway never sees a flood; the log never grows unbounded.
4. The cell emits a 30 MB figure. The kernel manager **uploads it to object storage** and writes a `display` event carrying the URI. The text stream did not stall.
5. The laptop wakes; the client reconnects with `attach?after=8812`. The gateway replays `8813…` from the log — the truncation marker, the figure reference, the `done` — and the client renders exactly what it missed, in order.
6. **The failure path.** The streaming gateway shard holding the socket dies mid-run. The client reconnects — to any gateway, because **the gateway is stateless and the log is not in it**: it lives in the session's output store (Redis Streams per session, § 12), and any gateway can tail any session from any `seq`. The client's `after=` is the only state the resume needs, and it is on the client.

### Flow D — the idle reaper, and a fork bomb

1. Session 7 has had no activity for 30 minutes. The reaper CASes `READY → IDLE → SUSPENDING` and asks the host agent to snapshot.
2. The agent pauses the VM, writes the memory snapshot and the overlay delta to local NVMe, CASes to `SUSPENDED` **only after the upload to object storage is acknowledged**, and frees the VM's RAM. The local copy stays in the NVMe cache for a fast resume. Host RAM for this session: **zero**.
3. **The failure path — the snapshot takes too long.** A session with 30 GB of loaded data cannot snapshot in the 60 s budget. The agent gives up on memory, snapshots **only the overlay**, and CASes to `SUSPENDED` with `has_memory: false`. On resume it cold-boots with packages intact. **Files were never at risk; the overlay is safe; memory was best-effort and this is what best-effort means.**
4. **The abuse path — a fork bomb at 14:02.** The sandbox's cgroup caps it at 2 vCPU, 4 GB, and 1,000 pids. The bomb hits the pid limit inside its own VM; the host and every other sandbox on it are unaffected. The host agent's abuse signals — pid churn, CPU pegged with no output, egress to a mining pool blocked by the proxy and logged — fire an automated response: the session is `SUSPENDED` without a memory snapshot, the workspace is flagged, and a human sees it in a queue. **Isolation contained it; observability caught it; the response was automatic.** Say all three; "the sandbox stops it" is one third of the answer.

---

## 7 · Deep dive — the substrate: rank by the kernel you share, default to a microVM, and name the GPU exception

### What you'd reach for first

Docker containers. One per session, cgroups for limits, seccomp for syscalls, fast to start, dense on a host. It is what every tutorial and most internal tools use.

### What breaks

- **A container shares the host kernel.** Every syscall from hostile code is executed by the same kernel that runs every other tenant on the host. One kernel privilege-escalation CVE — there are several a year — and the escape is not to the host, it is to **every session on the host**, and from there to the host's cloud credentials. Seccomp and user namespaces reduce the attack surface; they do not change what is shared.
- **"Hardened containers" are the same kernel with a longer denylist.** Better, and still a bet that the next CVE is on the list.
- **Density arguments cut the other way once the kernel is the boundary**: a hundred sessions per host that all fall together is not density, it is blast radius.

### What replaces it

**Rank the options by what kernel the code shares, then pick on the three-way tension between isolation, cold start, and density.**

| Substrate | What is shared | Cold start | Density | Snapshot / resume | Verdict |
|---|---|---|---|---|---|
| **Container** (runc) | **The host kernel** | ~100 ms | Very high | Checkpoint via CRIU — fragile | Not for untrusted code. Right for the platform's own services |
| **Hardened container** (seccomp + userns + AppArmor) | The host kernel, less of it | ~100 ms | Very high | Same | The intermediate that is still one CVE from everyone |
| **Userspace kernel** (gVisor) | **A Go reimplementation of the kernel**; the host kernel sees a narrow surface | ~200 ms | High | Limited | Strong. Syscall-heavy workloads pay 2–10×; **no clean GPU story**; snapshot support is partial. The right choice where you cannot run a hypervisor |
| **MicroVM** (Firecracker, Cloud Hypervisor) | **Nothing** — a guest kernel per session, KVM underneath, a minimal device model | **~150 ms** to guest kernel, ~1 s to a Python kernel | High — a few thousand per host at 4 GB with memory overcommit | **Yes — and it is the point**: snapshot memory + device state, restore with lazy page loading in ~200 ms | **Default.** Hardware isolation, a boot fast enough for a warm pool, and a snapshot fast enough for the resume budget |
| **Full VM** (QEMU, cloud VM) | Nothing | 10–60 s | Low | Yes, slowly | Right when you need a full device model — **GPUs** |

- **The default is a Firecracker microVM per session**, on hosts with nested-virt or bare metal, with a minimal guest kernel and the base image **pre-baked onto every host's disk** so no image is ever pulled on the resume path. KVM is the isolation; the device model is small enough that its attack surface is a few hundred lines of virtio.
- **Lazy restore is what makes the snapshot a resume mechanism rather than a backup.** The VM resumes executing after ~200 ms with its memory backed by the snapshot file; pages fault in on first touch. A session whose user runs one small cell after lunch touches a few hundred MB of a 4 GB snapshot and never waits for the rest.
- **The GPU exception, named.** A microVM can pass through a GPU (VFIO), but it **cannot snapshot and restore GPU state**, the device's memory is not on the host's terms, and a passthrough device is a wider attack surface than virtio. So GPU sessions are **a different substrate**: full VMs on dedicated GPU hosts, **no suspend-to-snapshot** — an idle GPU session is terminated after a shorter timeout with its files and overlay persisted, and resume is a cold boot with a stated, longer SLO. The warm pool for GPUs is small (they are the expensive resource) and paid-tier only. **Say all of this before the interviewer asks "what about GPUs";** it is the follow-up on every version of this prompt.
- **The rejected alternative, with the sentence:** *"gVisor is what I'd use if I couldn't run a hypervisor — inside a managed Kubernetes cluster, say. It is strong isolation and it costs syscall performance, and it has no answer for the GPU case or for a sub-second resume. On bare metal with KVM, the microVM gives me the harder boundary and the snapshot, and I'd take the operational cost of running my own hypervisor layer for that."*

**Cost, volunteered:**

- **You are now operating a hypervisor layer.** Host kernels, KVM, a snapshot format, a device model — your team owns it, and a Firecracker CVE is your incident. This is the honest cost of the boundary.
- **Memory overcommit is a bet on the idle-heavy workload.** A host with 256 GB running 100 sessions at 4 GB is 1.6× overcommitted and safe only because sessions are waiting on humans; a workload that goes hot everywhere at once (that course assignment) is an OOM storm. The mitigation is the cell scheduler refusing placements past a measured working-set ratio, not a hope.
- **Golden snapshots share state that must be unique per session.** Random seeds, host SSH keys, session tokens, and the guest's `/etc/machine-id` are identical across every session restored from one image until reseeded. **Reseed at attach is a hard requirement**, and it is the item on this page most likely to be a real vulnerability if forgotten (§9).

**→ ties to the isolation and resume-latency NFRs.**

---

## 8 · Deep dive — the lifecycle state machine and the resume budget: what was done before the request arrived

### What you'd reach for first

Resume = `docker run` the user's image, mount their files, start the kernel. Track state with a `status` column updated by whoever gets there.

### What breaks

- **The cold boot is tens of seconds** (§3) and every one of its steps is on the critical path: image pull, VM boot, kernel start, library import, file fetch. Nothing about `docker run` can be made to fit in five seconds for a real scientific image.
- **A `status` column updated by "whoever gets there" is a race with three writers**: the user clicking resume twice, the idle reaper deciding to suspend, and a scheduler that crashed after placing but before recording. Two sandboxes for one session, or a session recorded `READY` on a host that died, are the everyday result.
- **No fallback** means the day the snapshot store is slow, resume is broken rather than slow.

### What replaces it

**The state machine in §4, driven by CAS on a version, with every expensive step moved off the critical path.**

- **Pre-materialise everything that does not depend on the user.** The base image is on every host's disk. A pool of microVMs is booted past kernel init and Python import, waiting. The user's overlay and memory snapshot were written at suspend time, and a copy stayed in the NVMe cache of the host that wrote it. **Resume is then: pick a host, restore, reseed, attach, mount — an attach, not a rebuild.**
- **The budget, written on the board:** control-plane round trips ~200 ms · snapshot fetch < 1 s from cache / 2–4 s from object storage · restore to first instruction ~200 ms · reseed + NIC + mount ~300 ms · client reattach ~100 ms. **~2 s from cache, ~4–5 s from object storage.** The two levers that decide which you get are **cache affinity in the scheduler** (prefer the host that has the snapshot) and **snapshot size** (compress; exclude page cache).
- **Leases and CAS make the machine correct under crashes.** A transition is owned by the component holding the session's lease; the lease has a 30 s expiry; the transition commits by CAS on `version`. The scheduler that crashes after placing a sandbox never commits `READY`; its lease expires; the next scheduler reads `RESUMING` with a stale lease, checks whether a sandbox exists for this session on any host (the host agent's inventory is authoritative for that), adopts it or tears it down, and continues. **Duplicate events are no-ops by construction, because the second CAS fails.**
- **Fallbacks, in order.** Snapshot in cache → snapshot in object storage → **cold boot with the overlay** (packages kept, memory lost) → **cold boot without the overlay** (the overlay object is corrupt; packages lost, files untouched). Each step has a timeout that triggers the next, each lands in `READY` with a flag saying which path was taken, and the client tells the user honestly. The SLO is for the first path; **the availability property is that the last path always works.**
- **The idle reaper is the other half.** Sessions do not suspend themselves; a per-cell reaper scans for `READY` sessions past their idle window and drives them through `SUSPENDING`. The suspend budget (60 s) is enforced by the same lease, and a session that cannot snapshot its memory in time is suspended without it — the overlay is enough to keep the promise that matters.

**Cost, volunteered:**

- **Every suspended session is a snapshot to store and eventually delete.** 750 k × ~1 GB, with a GC job that deletes snapshots for sessions idle beyond 30 days (the session becomes "cold": files only, resume is a cold boot). The GC is the least glamorous job on the page and the one that keeps the bill flat.
- **Cache affinity fights load balancing.** Preferring the host that has the snapshot concentrates returning users on the hosts they left; a host that is full forces a slower resume elsewhere. The scheduler needs both signals and a rule for the conflict — *"affinity unless the host is above 85 % RAM"* — and the rule is worth saying.
- **The state machine has eight states and a table of transitions, and it is the most-read document on the team.** That is a cost in the sense that it must be kept exact; it is also the reason the lifecycle survives a scheduler deploy.

**→ ties to the resume-latency, create-latency, and fault-tolerance NFRs.**

---

## 9 · Deep dive — isolation in layers: egress, the metadata endpoint, credentials, and what the guest may hold

### What you'd reach for first

The microVM is the boundary. Inside it the code can do what it likes; outside, it cannot get.

### What breaks

- **The boundary has a network interface**, and on the other side of it is the host's network — where the cloud metadata endpoint answers `169.254.169.254` with the instance's IAM credentials, the platform's internal services listen without authentication because "they're internal," and other tenants' file mounts are one hop away. **The kernel boundary does nothing about any of this.** Exfiltration and credential theft happen over the network, from inside a perfectly intact sandbox.
- **Credentials inside the guest are credentials the user owns.** A token in the sandbox's environment to let the kernel write the user's files is a token the user's code can read and use — from the sandbox or from anywhere, for as long as it is valid.
- **A shared host filesystem** — bind-mounting a host directory for speed — is a path from one tenant's code to another tenant's bytes, or to the host.
- **The golden snapshot** shares its randomness, its host keys, and its session identity with every sibling restored from it. Two sessions with the same TLS session keys, or the same seed for a random number generator that generates a token, is a cross-tenant leak that no kernel boundary prevents.

### What replaces it

**Four layers, each of which assumes the one inside it has failed.**

1. **Process and kernel:** the microVM (§7). Inside it, still: a non-root user, seccomp on the guest side, a pid limit, and cgroups on the host side for CPU, memory, disk I/O, and network bandwidth — the noisy-neighbour controls. A fork bomb hits the pid cap inside its own VM.
2. **Filesystem:** the guest sees a **virtio block device backed by image + overlay** and a **file mount for the workspace over a narrow protocol** (virtio-fs or a userspace FUSE bridge scoped to one workspace). No bind mounts. No host paths. The workspace mount is served by a per-host **file agent** that holds the credentials — not the guest.
3. **Network egress — the most-attacked path, so the most controlled:** the guest's NIC is on a per-session network namespace whose only route is an **egress proxy**. The proxy **blocks the metadata endpoint and every RFC 1918 range** by default, **allows package registries and user-configured hosts by allowlist**, rate-limits bandwidth per session, and **logs every destination** — which is the abuse signal that catches a mining pool. Inbound is nothing: the streaming gateway connects to the kernel manager over a host-local vsock, not TCP, so the sandbox is never on the public internet.
4. **Identity and credentials:** **the guest holds no long-lived credential.** The kernel manager inside it talks to the host agent over vsock; the host agent holds a **short-lived, workspace-scoped token** (minutes, one workspace, read-write to files, nothing else) and performs file operations on the guest's behalf. A user who dumps the sandbox's environment finds nothing worth having. Secrets the user *wants* in their session (an API key for their own code) are injected as files the user owns, scoped to that workspace, and revocable.

Plus the two that are about the platform's own hygiene: **reseed at attach** — new entropy, new host keys, new machine id, new session token, before the guest runs a single user instruction — and **audit** every lifecycle transition, every egress denial, and every file-agent call with the session id, because the security question after an incident is "what did session X touch," and the answer has to be a query.

**Cost, volunteered:**

- **The egress allowlist breaks things.** A user's code that calls an API not on the list fails, and the ticket says "the platform is broken." The product answer is a per-workspace allowlist the user can edit, with the metadata endpoint and private ranges unremovable — which is a UI and a policy, not just a proxy rule.
- **virtio-fs is slower than a local disk.** Large-file workloads (reading a 10 GB dataset) feel it. The mitigation is a local cache on the overlay with an explicit "copy to workspace" — a product surface that exists because the isolation boundary has a cost.
- **Token-per-file-operation through an agent is a hop** on every file write. Autosave of a notebook is small and frequent; it is fine. A training loop writing checkpoints every second is not, and it gets the local-disk path above.
- **Four layers is four things to test in a red-team exercise**, and the honest statement is that the platform runs one — quarterly, against its own sandboxes, with the metadata endpoint as the first target every time.

**→ ties to the isolation and noisy-neighbour NFRs.**

---

## 10 · Deep dive — output streaming: a sequence-numbered log, resumable from the client, capped, with blobs sideloaded

### What you'd reach for first

A WebSocket from the browser to the kernel. The kernel writes `stdout` to the socket. Reconnect opens a new socket.

### What breaks

- **A reconnect loses everything between the drop and the reopen.** The kernel wrote to a closed socket; the bytes are gone; the client has a hole in its output and no way to know where. Two reconnects and the order is scrambled.
- **The socket is the gateway's state.** A gateway shard dies and every session on it loses its stream — and its in-flight output — at once.
- **`while True: print()`** fills the socket's send buffer, then the gateway's memory, then the browser's DOM. A 50 MB plot inlined as base64 head-of-line-blocks every subsequent `print` for seconds.
- **"Should execution stop when the user disconnects?"** was never decided, so it stops sometimes — when the kernel blocks on a closed pipe — and continues other times.

### What replaces it

**Every output chunk goes to a per-session append-only log with a monotonic sequence number; the gateway is a stateless tail of that log; the client resumes from the last sequence it saw.**

- **The kernel manager writes, never the socket.** Inside the sandbox, the kernel's `stdout`, `stderr`, and display messages go to a kernel manager process that assigns `seq`, tags `cell_id` and `exec_id`, and appends to the session's output log — over vsock to the host agent, which writes to **Redis Streams, one stream per session** (`XADD` with the seq as the id; 24-hour retention; compacted to object storage on suspend).
- **The streaming gateway tails the stream** (`XREAD` from the client's `after`) and forwards. It holds no state but the cursor, so any gateway can serve any session, and a gateway death costs one reconnect. **`attach?after=seq` is first attach and reconnect with one code path.**
- **Delivery semantics, stated:** at-least-once from the log to the client, made exactly-once by the client discarding `seq ≤ last seen`. No gaps (the log is contiguous), no reordering (the log is ordered), and the only client state is one integer.
- **Backpressure and caps.** A per-cell output cap (10 MB of text, say) after which the kernel manager writes one `status: truncated` event and drops further text — **the process keeps running**; the user asked for the loop, not the log. Rich outputs above a threshold (256 KB) are **uploaded to object storage by the kernel manager and referenced by URI** in a `display` event; the text stream never carries a blob. The gateway applies per-socket send-buffer limits and drops the socket (not the log) if the client cannot keep up — the client reconnects with `after=` and catches up at its own pace.
- **Execution continues when the user disconnects.** Decided, and said: the cell runs to completion or to the idle timeout; the log captures it; the user sees it on reconnect. The alternative — stop on disconnect — makes every laptop sleep a lost computation, and it is the wrong default for a tool people run overnight.
- **`interrupt` reaches the kernel through the same manager**, and it is the one message that must not be queued behind output: it travels on a separate control channel over vsock, the ChatGPT page's "cancel must reach the GPU" in miniature.

**Cost, volunteered:**

- **A Redis Streams cluster holding 75 k active session logs** — small per session, 24 h retention, a few hundred GB across the fleet — is a stateful tier to run, and its loss loses in-flight output (not files, not execution). It is rebuilt empty; the client's `after=` will see a gap and the UI says "output from before the incident is unavailable." Bounded and honest.
- **Sequence numbers are per session, not global**, so two sessions of the same workspace (a user with two tabs) have two logs. The product decides whether a workspace may have two live sessions; the log does not.
- **Truncation is a product decision that looks technical.** 10 MB is generous for text and tiny for someone who printed a dataframe; the cap is tier-configurable and the marker tells the user it happened.

**→ ties to the output-streaming NFR.**

---

## 11 · Deep dive — three durability classes and the idle-tail economics

### What you'd reach for first

Persist the workspace: files, packages, and the kernel's memory, all of it, on every suspend. Or the opposite: persist files, and everything else is gone when you close the tab.

### What breaks

- **"Persist everything" promises the memory snapshot**, and a memory snapshot is best-effort by nature: a host dies between suspends, a 30 GB session cannot snapshot in the budget, a snapshot restored onto a different CPU generation faults. The promise breaks on the first host failure, and the user who lost a variable will not distinguish that from losing a file.
- **"Persist only files" rebuilds the environment on every resume.** `pip install` is gone every time; a 20-package scientific stack is minutes of install; the resume SLO is impossible and the user is retyping the same cell every morning.
- **Files on the sandbox's local disk** means resume must copy them to the new host, and host death loses whatever was not yet copied.

### What replaces it

**Three classes, three stores, three promises — and the idle tail costs what the third class costs, which is nothing.**

| Class | What it is | Store | Promise | Written when |
|---|---|---|---|---|
| **Workspace files** | Notebooks, data, user-created files | **Object storage** (S3-class, versioned), mounted into the guest via the file agent; autosaved by the editor every few seconds | **Durable — 11 nines, survives everything, versioned for 30 days** | Continuously, from the file agent |
| **Runtime overlay** | The writable layer above the base image: installed packages, caches, dotfiles | **Object storage**, as a content-addressed disk delta; a copy in the host's NVMe cache | **Rebuildable, kept**: survives suspend/resume and node loss as long as the object exists; can be discarded and rebuilt from the image if corrupt | At every suspend, and on a timer (every 10 min) while running |
| **Live memory** | Kernel process state: variables, loaded models, open handles | **Snapshot in object storage** + NVMe cache | **Best-effort**: restored when present and valid; **lost on host death between snapshots, and lost by design when it cannot be taken in budget** | At suspend only |

- **The overlay is the class people forget, and it is the one that makes `pip install` survive.** It is a disk delta, not memory; it snapshots in seconds; it restores by mounting. A cold boot with the overlay has every package and no variables — which is the exact promise the NFR made.
- **The idle tail costs the price of storage.** A suspended session is a ~1 GB memory object plus a ~500 MB overlay object in object storage and zero host resources. 750 k of them is ~1 PB — a storage bill, not a fleet. **The alternative — keeping them resident — is seven times the fleet (§3), and that is the sentence that justifies the whole suspend machinery.**
- **Aging.** After 30 days suspended the memory snapshot is deleted (resume becomes a cold boot with packages); after 90 days the overlay is deleted (resume rebuilds from the image); **files are never deleted by the platform.** Each tier down is cheaper and slower to resume, and the client says which it got.
- **Autoscaling is per cell, on two signals**: active sandbox count against host capacity (RAM-bound) and warm-pool depth against arrival rate. A cell scales hosts in and out on the first; the pool replenisher scales the pool on the second. Idle sessions do not appear in either — they are in object storage.
- **Files never live on the host.** Node death loses nothing in the first class, at most ten minutes of the second, and whatever was in memory since the last suspend in the third. Say the three numbers together.

**Cost, volunteered:**

- **The overlay grows.** A user who installs a different ML framework every week has a 10 GB overlay, and it is snapshotted every suspend. Cap it per tier; offer "reset environment" as a product action; and dedupe by content hash so the same package layer across a million sessions is stored once.
- **A memory snapshot is CPU-model-specific.** Restoring on a different CPU generation can fault. The cell's host pool has to be homogeneous per snapshot format, or the scheduler has to know — one more affinity constraint.
- **Object storage as the file backend has a consistency model** (read-after-write for new objects, eventual for overwrites on some providers). The file agent has to serialise writes per file and read its own writes through a local cache, or a user will save a notebook and reload an older one.

**→ ties to the durability, idle-policy, and scale NFRs.**

---

## 12 · Data model, sharding, and storage decisions

**Partition on `cell`, then `session_id`, and say why the cell is the unit.** Every stateful component — the control-plane database, the scheduler, the warm pool, the host fleet, the output-log cluster — is per cell, ~10 k users each. A session's row, log, and sandbox all live in one cell, so a lifecycle transition is a single-cell operation with no cross-cell coordination, and a cell's failure is 2 % of users. Workspaces are assigned to a cell at creation and migrate only by an explicit job.

**The hot shard is a viral moment inside one cell**, and the answer is the pool and the fallback: a burst of creates drains the pool, the cold-boot fallback absorbs it slower, and the replenisher and the host autoscaler catch up. No single row is hot; the scheduler's queue is, and it is per cell.

**Three things are sources of truth, and none of them is on a host.** The session row (state), workspace files (data), and the overlay object (environment). Everything on a host — a running VM, a warm sandbox, an NVMe cache entry — is rebuildable.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Workspaces, sessions, snapshots, hosts** | Lifecycle transitions as CAS; ~1 k writes/s per cell; read by scheduler and reaper | **System of record** | **Postgres** per cell, `UPDATE … WHERE version = $expected`, `lease_until` column, index on `(state, last_activity)` for the reaper | "A workflow engine would own the state machine for me; at a thousand transitions a second per cell, a row with a version *is* the workflow engine, and I can read it with `psql` at 3 a.m." |
| **Workspace files** | Autosave writes every few seconds per active session; reads on mount | **11 nines, versioned 30 d, cross-region replicated** | **Object storage** (S3-class), one prefix per workspace, served to the guest through the file agent | "Files on the host are files that die with the host. This is the one store that outlives everything, and the agent is what keeps its credentials out of the guest" |
| **Snapshots** (memory + overlay) | Write at suspend (~1 GB); read at resume; delete on aging | Durable until aged out; **best-effort in meaning** | **Object storage** + a **host-local NVMe cache** with affinity in the scheduler | "Two copies: the one that survives, and the one that makes resume two seconds instead of five" |
| **Base images** | Read at every boot; changes weekly | Content-addressed, immutable | **Pre-baked onto every host's disk** on host provisioning; registry only as the source | "An image pull on the resume path is thirty seconds I don't have. The image is on the disk before the host takes a session" |
| **Warm pool** | Claim by CAS; replenish in background | None — rebuilt from images | **Postgres rows per cell** (`pool_entries`) pointing at pre-booted sandboxes on hosts; target depth from arrival rate | "Little's law sizes it: arrivals × cold-boot time. It's one percent of the fleet buying single-digit-second creates" |
| **Output logs** | Append from 75 k sessions; tail by seq; 24 h | In-flight only; compacted to object storage on suspend | **Redis Streams**, one stream per session, sharded by `session_id` | "Kafka would do this with a partition per… no. A million tiny ordered logs with per-consumer cursors is what Streams is for, and losing it loses output in flight, not execution" |
| **Streaming gateways** | 500 k sockets; a cursor per socket | None | **Stateless** WebSocket tier, L4 balanced, tails Streams; talks to sandboxes over vsock via the host agent | "Any gateway serves any session from any `seq`. The client holds the only state the resume needs" |
| **Scheduler** | Placement decisions per transition; per cell | Rebuilt from Postgres + host inventory | **Stateless service** per cell, leader-elected, reading host capacity from agent heartbeats (Redis, 10 s TTL) | "It decides; it does not remember. If it dies, the next one reads the rows and the hosts and continues" |
| **Host agent** | Runs VMs; snapshots; serves files; enforces cgroups; reports inventory | Its inventory is authoritative for *what is running here* | **A daemon per host** with a local SQLite of sandbox state, reconciled against Postgres | "The row says what should be; the agent says what is; a reconciler fixes the difference. Both are needed and neither is trusted alone" |
| **Egress proxy** | Every outbound connection from every sandbox | Logs are durable (audit) | **Per-host proxy** (Envoy or Squid-class) with a per-session policy; logs → Kafka → ClickHouse | "It blocks the metadata endpoint and private ranges, allows the registry, and writes down everything else. The log is the abuse signal" |
| **Audit log** | Every transition, egress denial, file-agent call | **Immutable, 1 year** | **Kafka → ClickHouse**, with daily Parquet to S3 Object Lock | "‘What did session X touch’ has to be a query, not an investigation" |
| **Package layer cache** | Read on overlay rebuild; shared across tenants by content hash | Rebuildable | **Object storage**, content-addressed layers | "The same NumPy wheel across a million overlays is stored once" |
| **Inside the guest** | The kernel, the manager, the overlay mount | None — the VM is disposable | Ephemeral | "Nothing in the guest is worth backing up, and nothing in it is worth stealing. That's the design goal stated as a storage decision" |

### Data lifecycle — the append-only entities

| Entity | Growth | Hot | Warm | Cold | Restore |
|---|---|---|---|---|---|
| **Memory snapshots** | ~1 GB per suspend, ~750 k live | Until resumed; NVMe cache 24 h | Object storage until **30 days** idle | **Deleted**: resume becomes a cold boot with packages | n/a — best-effort by contract |
| **Overlays** | ~500 MB per workspace | Object storage while the workspace exists | — | Deleted at **90 days** idle; rebuilt from the image on resume | Packages reinstalled by the user; files untouched |
| **Workspace files** | User-driven; versioned | Object storage, forever | 30 days of versions | **Never deleted by the platform** while the workspace exists; 30 d tombstone after delete | Immediate, any version |
| **Output logs** | Per active session | 24 h in Streams | Compacted to the workspace's object prefix on suspend | With the workspace | Minutes |
| **Audit and egress logs** | ~50 GB/day | 90 d in ClickHouse | — | 1 year, Object Lock | Hours |

### The signals that tell you this is broken

- **Resume p95 by path taken** — cache hit / object storage / cold boot with overlay / cold boot without. The SLO is on the first; the mix is the leading indicator. A rising share of the third path is a snapshot store problem before it is a user complaint.
- **Warm-pool depth vs arrival rate** per cell — the create SLO's leading indicator, an hour ahead.
- **Host RAM working-set ratio** — overcommit is a bet; this is the bet being checked.
- **Suspend-without-memory rate** — sessions that missed the snapshot budget. A step change is a host or storage problem.
- **Egress denials per session** — the abuse signal, and the "your API is blocked" ticket source, in one graph.
- **CAS failure rate on session rows** — duplicate events being correctly rejected; a spike is a client or scheduler bug that the machine is absorbing, and it should be looked at before it stops absorbing.
- **Streams lag per gateway** and **socket drops for slow clients** — the streaming half's honesty.
- Plus the security ones: sessions restored without a reseed (should be zero, and alarmed), file-agent calls with an expired token, any connection attempt to `169.254.169.254`.

---

## 13 · Traps — the ranked list

**Design traps**

1. **Plain containers for untrusted code.** One kernel CVE is every tenant on the host. Rank by what kernel is shared and say it (§7).
2. **The metadata endpoint reachable from the guest.** A single address that turns a sandbox into the platform's cloud credentials. Blocked at the egress proxy, and named as the first thing the red team tries (§9).
3. **Credentials inside the guest.** Whatever the kernel can read, the user's code can exfiltrate. The host agent holds a short-lived scoped token; the guest holds nothing (§9).
4. **Golden snapshot restored without reseeding.** Shared entropy, shared host keys, shared session identity across every session from one image (§7, §9).
5. **A `status` column instead of a state machine with CAS.** Two sandboxes for one session; a `READY` row on a dead host (§4, §8).
6. **A cold boot on the resume path.** Image pull, VM boot, kernel start, library import — tens of seconds against a five-second budget. Pre-materialise or fail the SLO (§8).
7. **Idle sessions kept resident.** Seven times the fleet for sessions doing nothing. Suspend to snapshot, or explain the bill (§3, §11).
8. **Promising to persist memory.** A memory snapshot is best-effort by nature; the promise breaks on the first host failure. Three classes, three promises (§11).
9. **Files on the sandbox's local disk.** Resume copies them; host death loses them. Files live in object storage, always (§11).
10. **Output over the socket instead of a log.** A reconnect is a hole; a gateway death is every session's stream (§10).
11. **No output cap.** `while True: print()` is a denial of service on the gateway and the browser (§10).
12. **Blobs inlined on the text stream.** A 50 MB figure head-of-line-blocks every `print` behind it (§10).
13. **"Does execution stop on disconnect?" left undecided.** It then stops sometimes (§10).
14. **One global cluster.** A scheduler bug or a viral assignment is everyone; fifty cells is 2 % (§3, §12).
15. **GPUs on the default substrate.** A microVM cannot snapshot GPU state; GPU sessions are a different substrate with a different SLO and no suspend (§7).
16. **The overlay forgotten.** `pip install` gone on every resume, or memory promised as the way to keep it (§11).

**Performance traps**

17. **No cache affinity in the scheduler.** Every resume fetches a gigabyte from object storage: five seconds instead of two (§8).
18. **Eager snapshot restore.** Loading 4 GB before the first instruction, when lazy paging gets to first instruction in 200 ms (§7).
19. **Warm pool sized by guess.** Arrival rate × cold-boot time is the number, and a pool with no replenisher is a pool that is empty by noon (§3, §6 Flow B).
20. **Memory overcommit with no working-set check.** An OOM storm the first time every session in a cell goes hot (§7).
21. **The file agent on the path of a checkpoint loop.** A hop per write is fine for autosave and wrong for a training loop; the local-disk path exists for that (§9).

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

22. **Optimising latency and density first, then bolting isolation on.** The prompt says security is non-negotiable; the round is watching whether the substrate decision comes before the warm pool or after it. Say "the adversary first, then everything else subject to that" in the first minute, and every later trade-off is framed the way the interviewer wants to hear it.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 450" role="img" aria-label="Sandboxed compute five-minute skeleton. The session state machine across the top; then the control plane, the data plane with microVMs and the GPU exception, and the warm pool; then suspend-to-snapshot, the itemised resume budget, and the three durability classes; then the isolation layers and the output log; and a margin lane of the signals and the blast-radius sentence.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="44" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="94.5">CREATING → READY ↔ RUNNING → IDLE → SUSPENDING → SUSPENDED → RESUMING → READY · DELETED · every transition a CAS on version, under a lease</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="30" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="148.5">Control plane, per cell</text>
  <text class="dg-s dg-c" x="180" y="164.5">API · scheduler · reaper · Postgres sessions</text>
  <text class="dg-s dg-c" x="180" y="180.5">decides; runs no code</text>
  <circle class="dg-num" cx="30" cy="128" r="9"></circle>
  <text class="dg-num-t" x="30" y="131.4">2</text>
  <rect class="dg-box" x="350" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="148.5">Data plane</text>
  <text class="dg-s dg-c" x="500" y="164.5">Firecracker microVM per session · cgroups</text>
  <text class="dg-s dg-c" x="500" y="180.5">GPU = full VM, no suspend, its own SLO</text>
  <circle class="dg-num" cx="350" cy="128" r="9"></circle>
  <text class="dg-num-t" x="350" y="131.4">3</text>
  <rect class="dg-box" x="670" y="128" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="148.5">Warm pool</text>
  <text class="dg-s dg-c" x="815" y="164.5">arrivals × cold-boot time · ~1 % of fleet</text>
  <text class="dg-s dg-c" x="815" y="180.5">replenished off the critical path</text>
  <circle class="dg-num" cx="670" cy="128" r="9"></circle>
  <text class="dg-num-t" x="670" y="131.4">4</text>
  <rect class="dg-box" x="30" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="232.5">Suspend-to-snapshot</text>
  <text class="dg-s dg-c" x="180" y="248.5">idle = zero host RAM · resident tail = 7× fleet</text>
  <circle class="dg-num" cx="30" cy="208" r="9"></circle>
  <text class="dg-num-t" x="30" y="211.4">5</text>
  <rect class="dg-box" x="350" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="232.5">Resume budget</text>
  <text class="dg-s dg-c" x="500" y="248.5">affinity → cache &lt; 1 s → lazy 200 ms → attach ≈ 2 s</text>
  <circle class="dg-num" cx="350" cy="208" r="9"></circle>
  <text class="dg-num-t" x="350" y="211.4">6</text>
  <rect class="dg-box" x="670" y="208" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="232.5">Three durability classes</text>
  <text class="dg-s dg-c" x="815" y="248.5">files always · overlay kept · memory best-effort</text>
  <circle class="dg-num" cx="670" cy="208" r="9"></circle>
  <text class="dg-num-t" x="670" y="211.4">7</text>
  <rect class="dg-box" x="30" y="284" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="308.5">Isolation layers</text>
  <text class="dg-s dg-c" x="260" y="324.5">microVM · file agent · egress blocks 169.254.169.254 · no guest creds · reseed</text>
  <circle class="dg-num" cx="30" cy="284" r="9"></circle>
  <text class="dg-num-t" x="30" y="287.4">8</text>
  <rect class="dg-box" x="510" y="284" width="450" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="308.5">Output log</text>
  <text class="dg-s dg-c" x="735" y="324.5">per-session seq → stateless gateway → attach?after=seq · cap · blobs by ref</text>
  <circle class="dg-num" cx="510" cy="284" r="9"></circle>
  <text class="dg-num-t" x="510" y="287.4">9</text>
  <text class="dg-lane" x="30" y="370">IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="400.5">resume p95 by path</text>
  <text class="dg-s dg-c" x="140" y="416.5">cache · store · cold</text>
  <circle class="dg-num" cx="30" cy="382" r="9"></circle>
  <text class="dg-num-t" x="30" y="385.4">10</text>
  <rect class="dg-box" x="270" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="380" y="400.5">pool depth vs arrivals</text>
  <text class="dg-s dg-c" x="380" y="416.5">the create SLO, an hour early</text>
  <rect class="dg-box" x="510" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="400.5">egress denials · CAS fails</text>
  <text class="dg-s dg-c" x="620" y="416.5">abuse, and the machine absorbing</text>
  <rect class="dg-box" x="750" y="382" width="210" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="855" y="400.5">50 cells, 2 % blast radius</text>
  <text class="dg-s dg-c" x="855" y="416.5">not one cluster</text>
</svg>
</div>

<p class="diagram-cap">Badge 1 is the machine and it goes on the board before any service; badge 3's label — a guest kernel per session — is the answer to the first follow-up; badge 7 is three promises in one sentence, and the word best-effort in it is the one the interviewer is listening for.</p>

1. **The state machine, top centre, before any box:** `CREATING → READY ↔ RUNNING → IDLE → SUSPENDING → SUSPENDED → RESUMING → READY`, `DELETED` terminal, `FAILED` with retry. Write beside it: **"every transition is a CAS on `version`, under a lease."**
2. **Control plane** (stateless, per cell): API · scheduler · idle reaper · **Postgres** with workspaces and sessions. Label it **"decides; does not run code."**
3. **Data plane:** hosts with an **agent**, **Firecracker microVMs** one per session, **cgroups** on the host side. Label the box **"a guest kernel per session — nothing shared."** Beside it: **"GPU = full VM, no suspend, its own SLO."**
4. **Warm pool** of pre-booted sandboxes, sized **arrivals × cold-boot time**, replenished off the critical path.
5. **Suspend-to-snapshot:** memory + overlay → **object storage** + **NVMe cache**; idle session = **zero host RAM**. Write the ratio: **"resident idle tail = 7× the fleet."**
6. **The resume budget, itemised:** pick host (affinity) → restore from cache < 1 s → lazy pages 200 ms → reseed + NIC + mount 300 ms → attach. **~2 s; fallbacks: object store → cold boot with overlay → without.**
7. **Three durability classes:** files (object storage, always) · overlay (rebuildable, kept — `pip install` survives) · memory (best-effort). Say all three in one breath.
8. **Isolation layers:** microVM · virtio block + scoped file agent · **egress proxy blocking `169.254.169.254` and private ranges** · no credentials in the guest · **reseed at attach**.
9. **Output:** kernel manager → **per-session log with `seq`** (Redis Streams) → stateless gateway → `attach?after=seq`; cap + truncation marker; blobs by reference; **execution continues on disconnect**.
10. In the margin: resume p95 by path, pool depth, working-set ratio, egress denials, CAS failure rate — and **"50 cells, 2 % blast radius."**

---

## 15 · Variants — what actually changes

**The governing axis: how long a session lives, and whether its memory matters when it stops.** Every row has a sandbox, a boundary, a lifecycle, and a durability story. What moves along the axis is whether suspend-to-snapshot exists at all, how big the warm pool has to be relative to the fleet, and whether the thing driving the session is a human or a program.

| Product | Session lifetime | Does memory matter at stop? | The delta from this page |
|---|---|---|---|
| **Serverless functions** — Lambda, Cloud Run | **Milliseconds to minutes** | No — a function is stateless by contract | **The warm pool is the entire product.** No suspend, no overlay, no files: a snapshot of the *initialised* function (Lambda SnapStart is exactly "restore a microVM from a golden snapshot, reseeded") and a scheduler whose only job is keeping enough of them warm. §8 shrinks to the pool; §10 vanishes; §9's egress controls stay verbatim |
| **CI runners** — GitHub Actions, Buildkite | **Minutes**, batch | No — the artefacts are the output | Ephemeral by design: a fresh VM per job, destroyed after. No resume, no idle tail, no memory snapshot. What survives is **the layer cache** (§11's overlay, made explicit as build caches) and the artefact store. The state machine has three states. Isolation matters *more* — runners hold deploy credentials, so §9's "no credentials in the guest" becomes "short-lived, job-scoped, and audited" |
| **Online judge** — LeetCode-style execution | **Seconds**, strict limits | No | The cgroup caps *are* the product (time limit, memory limit, no network at all). A warm pool of tiny sandboxes; no files, no overlay, no streaming beyond one output blob. The smallest instance of this page |
| **Hosted notebooks** — this page | **Hours**, interactive, idle-heavy | **Best-effort yes** — variables are the user's work in progress | As written: suspend-to-snapshot, three durability classes, the resume budget, the reaper |
| **Agent sandbox** — Codex, Devin, Claude Code environments | **Minutes to hours**, driven by a **model**, not a human | Sometimes — a long task's working state | Same substrate, same lifecycle, and the ChatGPT page's run lifecycle wrapped around it. What changes: **the thing inside is not accountable** — egress policy is tighter (an allowlist per task, not per user), there is a **budget** (tokens, wall-clock, tool calls) that terminates the session, and the output stream is consumed by the orchestrator first and the user second. Snapshots become **checkpoints a task can be resumed or forked from**, which is a feature notebooks do not have |
| **Cloud development environments** — Codespaces, Gitpod | **Days**; a developer's machine | Partly — but the disk matters more | Disk persistence is primary: the overlay becomes a full persistent volume, snapshotted and restored as the thing the user cares about; memory restore is a nicety. Suspend is common (nightly), resume is slower and tolerated (30 s), and the warm pool is small. §9 grows: the sandbox holds *the developer's* credentials (git, cloud) by design, so the problem inverts to keeping the platform's credentials out of a machine the user rightfully controls |
| **GPU training sessions** | **Hours to days** | **No — the checkpoint file is the state** | The GPU substrate from §7, and the suspend mechanism is deleted: an idle GPU session is terminated, and the durable state is a checkpoint the training loop writes to object storage every N steps. The scheduler is the ChatGPT page's §9 (a pool you cannot autoscale) with fair-share across tenants; the warm pool is tiny because the resource is the expensive part, not the boot |

**The lesson:** the sandbox, the boundary, and the egress controls are the same in every row — build them once. **How long the session lives decides whether you build a warm pool, a snapshot mechanism, or a checkpoint format**, and whether a human or a program is on the other end decides how tight the leash is. Say the lifetime in the first minute, and the rest of the page is which of its mechanisms to keep.
