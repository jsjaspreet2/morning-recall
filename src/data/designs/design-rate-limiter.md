# Design a Distributed Rate Limiter — Admission Control on the Hot Path

## The question

> *"Design a distributed rate limiter for a large API platform. Every request, at every gateway, in every region, gets an allow-or-reject decision against configurable limits: per user, per API key, per tenant, per IP, per endpoint, with different limits per subscription tier, some tolerance for bursts, and limits that can change without a redeploy. A million requests a second, a few milliseconds per check, and no cross-region round trip on the request path."*

**The product.** An API platform sells access in tiers: a free key gets sixty requests a minute, a pro key gets ten thousand, an enterprise contract gets whatever it negotiated. The limiter is the thing that says no. It sits in front of every request and, in the time it takes to look up a counter, decides whether this call is inside the customer's allowance. When it says no, the customer gets a `429` with a header telling them when to try again. When the platform is under attack or a customer's script goes wrong, the limiter is what keeps everyone else's traffic flowing.

**What a working system delivers**

- A customer inside their limit never sees a `429`, and one outside it sees one within a few milliseconds, with a `Retry-After` they can act on.
- A short burst — a page load that fires twenty calls at once — goes through; a sustained flood does not.
- An operator raises a tenant's limit and it takes effect in seconds, everywhere, without anyone redeploying anything.
- The limiter being slow or down never takes the API down with it. The worst case is that a few extra requests get through for a minute.
- The dashboard shows a customer how much of their allowance they have used, without that read costing the hot path anything.

**Why this gets asked.** It is a tiny function — read a counter, compare, increment — that has to run a million times a second, atomically, against limits that are supposed to be global, in a system where the one thing you may not do is ask another region. Every part of the design is a consequence of those four constraints colliding, and the interviewer wants to see which one you give up on, and whether you say so.

---

**Archetype:** admission control & global limits — a decision on every request's hot path against a limit that is global, when a cross-region hop is off the table, so the limit is approximate by design and the overshoot is the number you state.
**Cousins that reuse ~70% of this page:** API quotas and spend limits (the billing page's §8 is this page's lease mechanism applied to dollars), concurrency limits, login and OTP throttling, per-tenant fairness in a shared queue, the rate-limit control inside a GPU credit allocator, feature-flag percentage gates. Also **any product where a shared counter has to be checked on every request and cannot be a single row.**

**What's actually being graded:** whether the **capacity arithmetic** is done — rules per request times requests per second is the number that decides whether the check can touch a remote store at all; whether the **check-and-consume is one atomic step** and you can say what races if it isn't; whether the algorithm is **chosen from a comparison** rather than named; whether the **whale tenant** on one shard is noticed and relieved; and — the part that separates answers — whether you say out loud that **a global limit without a cross-region hop is approximate**, pick where on the spectrum you sit, and state the overshoot bound as a number.

**Contrast to have ready:** *Ticketmaster is the inverse. There, sixty thousand rows must each be sold exactly once, contention is the whole problem, and a single Postgres row lock is the right answer because the throughput is tiny. Here the throughput is a million a second, the counters are millions of independent keys with contention near zero, and **exactness is the thing you sell** — a limit of 1,000/min that admits 1,030 under partition is a working rate limiter, and one that blocks a paying customer for a hundred milliseconds of store latency is a broken one. Ticketmaster fails closed on a lock; this page fails open on a cache.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "This is admission control: a check on the hot path of every request against a limit, and the design is shaped by four constraints at once — a million checks a second, a few milliseconds each, limits that are nominally global, and no cross-region hop. Let me do the arithmetic first, because it decides everything: three or four rules apply to a typical request — user, key, endpoint — so that's **three to four million counter operations a second**, which means the check cannot scan anything, cannot call a service that calls a service, and cannot live on one node. So: a **token bucket per rule per subject**, updated by **one atomic script on one shard**, with the refill computed on read so there's no background job. Second, the **gateway holds a local lease** of tokens so most checks never leave the process — and that lease is what makes the limit approximate, by a bound I'll state. Third, **multi-region**: I'm going to enforce locally and reconcile globally out of band, accept a bounded overshoot, and handle the few tenants who genuinely need an exact global count as an exception with a home region. I'll go deep on the atomic check and the hot shard, and on the multi-region trade. Out of scope: volumetric DDoS, which is an edge problem upstream of this."

**Why open this way:** the arithmetic is the argument — said first, it forecloses "we'll call the rate-limit service" before it is drawn. Naming the local lease as *the source of approximation* in the first minute is the honest move the round is testing for, and it pre-commits the two dives (§8, §10) where reasonable engineers disagree. Ruling out DDoS scopes the page to admission rather than defence.

---

## 1 · Functional requirements

1. **Decide allow or reject for every request, in-line**, against every rule that applies to it — user, API key, tenant, IP, endpoint, and combinations — with **tier-aware limits** and a **burst allowance** above the steady rate, returning `429` with `Retry-After` and the standard `RateLimit-*` headers when rejecting.
2. **Rules change without a redeploy**: an operator creates, edits, or removes a limit and every gateway is enforcing the new version within seconds, with a way to **shadow** a rule before it enforces.
3. **Expose usage** — remaining allowance on every response, and a per-subject usage history for dashboards — **without the dashboard read touching the hot path's store.**

**Out of scope (say them):** volumetric DDoS defence (the CDN and edge scrubbers, upstream), authentication itself (the limiter consumes an already-resolved principal), billing-grade quotas that must be exact and settle to money (the billing page — §15 here says what changes), request routing and load balancing, WAF rules.

**Below the line, likely follow-ups:** per-request cost weights (an expensive inference call consuming ten tokens), multiple windows on one principal (100/s *and* 10,000/day), concurrency limits as opposed to rate limits (§15), a tenant that moves regions, an exact-global exception for one contract (§10), abuse signals beyond counting (§11).

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Check latency** | **p99 < 5 ms added to the request; p50 < 1 ms** | The check is on every request's critical path. A 5 ms p99 is what one round trip to a same-AZ Redis costs; anything that requires two hops or a cross-region call is disqualified by this row alone |
| **Throughput** | **1 M req/s globally → ~3.5 M counter ops/s**, with a 3× regional peak | Three to four rules per request (§3). The op count, not the request count, sizes the store |
| **Accuracy** | **Bounded, stated, and different per rule class.** Ordinary limits: overshoot ≤ **(gateways in region × lease size)** per window, ≈ 5 % at the default lease. Billing-grade quotas: exact, at the cost of a home-region hop | Exactness is impossible at this latency without a global lock, and a limiter that pretends otherwise will be wrong silently. Say the bound and which knob shrinks it (§9) |
| **Availability of the decision** | The API's availability must **not depend on the limiter's**: **fail open by default**, with a **local fallback bucket**; **fail closed** only for rule classes that opt in | A minute of over-admission costs a little capacity. A minute of rejecting every paying customer is an outage. The default is a product decision and the exceptions are named (§11) |
| **Config propagation** | Rule change visible at every gateway in **p99 < 10 s**; **shadow mode** available on every rule | Seconds is what an operator watching a dashboard will wait before assuming it did not work and doing it again |
| **Multi-region** | **No cross-region call on the request path.** Global counters converge within **≤ 2 s** of reconciliation lag | The cross-region RTT (60–150 ms) is 30× the latency budget. Convergence lag is what bounds the multi-region overshoot (§10) |
| **State bound** | Counter state per region **≤ 20 GB**, every key with a TTL | 10 M active subjects × ~4 rules × ~50 B is 2 GB of live buckets; the bound is what stops a key-per-IP rule from growing without limit |
| **Fault tolerance** | Survives: any gateway (leases are lost, tokens they held age out at lease expiry), any store shard (fail open on that shard's keys, local fallback bucket at a conservative fraction), the control plane for hours (gateways keep the last rule set). **Does not survive: the whole region's store down for longer than the fallback bucket is trusted** — after that the region is over-admitting by the fallback ratio and the on-call is paged; **the API stays up** | Name the failure the design accepts. This page's is "over-admit for a while," and it is chosen over the alternative on purpose |
| **Observability** | Every decision is **sampled** to an off-path log; per-rule `429` rate, store latency, lease overshoot, and config version are first-class metrics | The limiter is the component most likely to be blamed for an outage it did not cause. Its own evidence has to be cheap and always on |

**The sentence that earns the point:** *"A global limit checked in a few milliseconds without a cross-region hop is approximate — the only question is whether the approximation is bounded and stated or hidden. Mine is bounded by the lease size times the gateway count, it shrinks to zero as a subject approaches its limit, and for the handful of tenants whose limit is money I'll pay the hop and make it exact."*

---

## 3 · Numbers that reframe the problem

**Rules per request, times requests per second, is the number that sizes everything**

- *Assumption:* a typical request matches **3–4 rules** — the user, the API key, the endpoint, sometimes the tenant and the IP.
- 1 M req/s × 3.5 ≈ **3.5 M counter operations a second**, sustained; **~10 M/s** at a regional peak.
- A Redis node does **100–200 k ops/s** for a small Lua script. **20–40 shards per region**, and the check *must* be one operation per rule, on one shard, with no scan and no second hop. **This number also kills "call the rate-limit service":** a service in front of the store is a second hop on every one of ten million ops a second, for no decision the gateway could not make itself.

**A local lease turns 3.5 M store ops into 35 k**

- If a gateway leases **100 tokens** from a subject's bucket at a time and serves the next 99 checks from memory, store traffic drops **100×** — to a few tens of thousands of ops a second, which is *one* Redis node's worth.
- The price is the overshoot: **200 gateways × 100 leased tokens = 20,000 tokens** in flight that the store has already counted and the subjects may not have used — or that a dead gateway took with it. For a subject with a limit of 1,000/min that is absurd; for one at 1 M/min it is 2 %. **The lease size must scale with the limit and shrink to one as the subject approaches it** (§9). This number is the design.

**The whale tenant is one key on one shard**

- *Assumption:* the largest shared API key does **50 k req/s** — 5 % of the platform, on **one bucket, on one shard**.
- Without a lease, 50 k Lua calls a second on one key saturates the shard for everyone else hashed there. With the lease above it is **500 store ops/s** for that key. The lease is the hot-key answer, and it is worth noticing that it *is* the hottest-key question: *"does every check need to touch this key?"* No.

**Counter state is small, and unbounded without a TTL**

- 10 M active subjects × 4 rules × ~50 B (tokens, timestamp, key) ≈ **2 GB** live. Trivial.
- A per-IP rule on the public internet sees **billions of distinct keys a month**. Without `EXPIRE` at twice the window, the store fills with buckets for addresses that will never return. **TTL is a correctness property here, not hygiene.**

**The cross-region RTT is thirty times the budget**

- 60–150 ms between regions; 5 ms p99 for the whole check. **No design that consults another region per request survives §2.** So global limits are enforced from local state and reconciled out of band, and the reconciliation lag (≤ 2 s) bounds the multi-region overshoot: a subject can exceed a global limit by at most **(regions − 1) × its local share × 2 s of rate** before every region has tightened (§10).

**Rules fit in every gateway's memory**

- *Assumption:* 50 k rules, a few hundred bytes each ≈ **10–20 MB**. Every gateway holds the full set, indexed by scope, and resolves applicable rules in microseconds. A rule set of ten million (per-customer custom rules at scale) would not fit and would need a lookup tier; **ask the interviewer which it is**, because it decides whether rule resolution is in-process or a hop.

---

## 4 · Core entities

- **Rule** — `(rule_id, version, scope: user | key | tenant | ip | endpoint | composite, subject_pattern, tier, limit, window_s, burst, cost_fn, mode: enforce | shadow | off, fail_policy: open | closed, updated_by, updated_at)`. Versioned; every decision records which version it used.
- **Bucket** — the runtime state per `(rule_id, subject)`: `{tokens: float, ts: ms}`. Two numbers. Refill is computed from `ts` on read, so the bucket has no background job and no clock of its own.
- **Lease** — gateway-local: `(rule_id, subject) → {tokens_left, expires_at}`. Tokens the store has already subtracted, being spent from memory.
- **Decision** — `(ts, gateway, rule_id, rule_version, subject, cost, allowed, remaining, latency_us)`, **sampled** at 1 % (100 % for rejects) into an off-path stream.
- **Tier** — a named bundle of default rules; a principal's tier is resolved by auth and arrives on the request.
- **Usage rollup** — `(subject, rule_id, minute) → count`, derived from decisions, for dashboards.

**The three that are load-bearing:**

**The bucket is two numbers, and the refill is a function of elapsed time.** `tokens = min(burst, tokens + (now − ts) × rate)`. No cron, no per-key timer, no "reset at the top of the minute." That single expression is what makes the bucket express **both** a sustained rate and a burst allowance, is why the store needs no background work, and is why the fixed-window 2× boundary problem does not exist here (§7).

**The lease is subtraction that already happened.** When a gateway takes a lease of *n* tokens, the store has consumed them. From the store's point of view those requests occurred; from the world's point of view they may never. **Every statement about accuracy on this page is a statement about the size of outstanding leases**, and every knob that tightens accuracy is a knob that shrinks them.

**A rule is versioned and the decision records the version.** A `429` that a customer disputes at 14:03 is explainable only if the log says which rule, at which version, with which limit, made it — and a shadow-mode rollout is only safe if a rule can be in two modes at two versions for a few seconds without anyone being able to tell which one bit them.

---

## 5 · API

```text
── internal: gateway → store, one Lua script, one key ────────────────────────────
EVALSHA <bucket.lua> 1 rl:{rule_id}:{subject}  <rate> <burst> <cost> <now_ms> <lease_n>
   → { allowed: 0|1, remaining, retry_after_ms, leased }
   refill on read · consume `cost` (or lease `lease_n`) · EXPIRE 2×window · uses the arg `now_ms`
   only as a hint — the script reads TIME on the shard and ignores gateway clocks

── control plane ────────────────────────────────────────────────────────────────
PUT  /v1/rules/{rule_id}                       If-Match: <version>
     { scope, subject_pattern, tier, limit, window_s, burst, cost_fn, mode, fail_policy }
     → 200 { version }  |  412 { current }  |  422 { errors }     validated: burst ≥ limit/window …
POST /v1/rules/{rule_id}/mode  { mode: shadow | enforce | off }  → 200
GET  /v1/rules?scope=&tier=&version_since=                        the config stream's pull twin
GET  /v1/usage/{subject}?rule=&from=&to=&granularity=1m           dashboards, from the rollup — never the store

── client-facing contract, on every response ────────────────────────────────────
200/… RateLimit-Limit: 1000; w=60    RateLimit-Remaining: 412    RateLimit-Reset: 23
429   Retry-After: 23  +  the same headers  +  body { rule: "key:rps", scope: "api_key" }
      — which rule, so the customer can tell "you're over your per-second burst"
        from "you've used today's quota"
```

**Decisions to narrate, unprompted:**

- **One script, one key, one shard, per rule.** The read-modify-write has to be indivisible or two concurrent checks both read 1 remaining and both pass. Redis executes a Lua script atomically on one shard; that is the entire concurrency story, and it is why the key for a rule–subject pair is a single hash-tagged key and never two.
- **The script reads the shard's clock, not the gateway's.** Two hundred gateways have two hundred clocks; skew of a second refills a bucket by a second's worth of tokens for free. `TIME` inside the script makes every refill for a key computed against one clock.
- **`429` says which rule.** A customer with a per-second burst limit and a daily quota needs to know which one they hit; the fix is different. The `RateLimit-*` headers are the IETF draft names, and the point of using them is that client SDKs already parse them.
- **Usage is never read from the hot store.** The dashboard reads a rollup built from the decision stream; a customer refreshing their usage page a thousand times must not add a thousand reads to the shard their traffic is hashed to.
- **`If-Match` on rule writes.** Two operators editing a tenant's limit at once is a real event; the loser gets `412` with the current rule, not a silent overwrite. Same conditional-update pattern as the settings-sync page, for the same reason.

---

## 6 · High-level design — flows

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 640" role="img" aria-label="Distributed rate limiter architecture. A region: API gateways holding the rule set in memory, local token leases, a fallback bucket and a per-shard circuit breaker; a Redis Cluster of twenty to forty shards running one Lua script per check; a control plane of Postgres rules pushed through a compacted Kafka config stream, with shadow mode; a sampled decision log flowing to ClickHouse for usage rollups and dashboards. A second region mirrors it, exchanging per-tenant counts every second over a replicated stream and receiving share parameters from a reconciler. A home-region lane serves the exact-quota exception across regions.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Allows come from a lease, rejects are confirmed at the store, and the global limit is approximate by a stated bound.</text>
  <rect class="dg-group" x="20" y="86" width="460" height="250" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">REGION A — THE REQUEST PATH</text>
  <rect class="dg-box" x="36" y="118" width="200" height="96" rx="8"></rect>
  <text class="dg-t dg-c" x="136" y="146.5">API gateways ×200</text>
  <text class="dg-s dg-c" x="136" y="162.5">rule set in memory · ~50 k rules</text>
  <text class="dg-s dg-c" x="136" y="178.5">local leases · fallback bucket</text>
  <text class="dg-s dg-c" x="136" y="194.5">circuit breaker per shard</text>
  <path class="dg-box" d="M 276,125 L 276,207 A 94,7 0 0 0 464,207 L 464,125 A 94,7 0 0 0 276,125 Z"></path>
  <path class="dg-box" d="M 276,125 A 94,7 0 0 0 464,125" style="fill:none"></path>
  <text class="dg-t dg-c" x="370" y="150">Redis Cluster</text>
  <text class="dg-s dg-c" x="370" y="166">20–40 shards · one Lua script</text>
  <text class="dg-s dg-c" x="370" y="182">one key per rule–subject</text>
  <text class="dg-s dg-c" x="370" y="198">TIME from shard · TTL 2×window</text>
  <path class="dg-line" d="M 236,150 L 268,150"></path>
  <path class="dg-head" d="M 268,155 L 268,145 L 276,150 Z"></path>
  <text class="dg-lbl dg-c" x="256" y="142">lease</text>
  <path class="dg-line" d="M 276,190 L 244,190"></path>
  <path class="dg-head" d="M 244,185 L 244,195 L 236,190 Z"></path>
  <text class="dg-lbl dg-c" x="256" y="206">reject?</text>
  <rect class="dg-good" x="36" y="240" width="428" height="76" rx="8"></rect>
  <text class="dg-good-t dg-c" x="250" y="274.5">refill on read → consume cost → allow, or 429 + which rule</text>
  <text class="dg-s dg-c" x="250" y="290.5">3.5 M ops/s → ~35 k with leases · p99 &lt; 5 ms · no scan, no second hop</text>
  <path class="dg-line" d="M 136,214 L 136,232"></path>
  <path class="dg-head" d="M 131,232 L 141,232 L 136,240 Z"></path>
  <rect class="dg-group" x="510" y="86" width="470" height="250" rx="12"></rect>
  <text class="dg-group-t" x="526" y="108">CONTROL PLANE</text>
  <path class="dg-box" d="M 526,125 L 526,175 A 100,7 0 0 0 726,175 L 726,125 A 100,7 0 0 0 526,125 Z"></path>
  <path class="dg-box" d="M 526,125 A 100,7 0 0 0 726,125" style="fill:none"></path>
  <text class="dg-t dg-c" x="626" y="150">Postgres rules</text>
  <text class="dg-s dg-c" x="626" y="166">versioned · If-Match · audit</text>
  <rect class="dg-box" x="760" y="118" width="204" height="64" rx="8"></rect>
  <path class="dg-qbar" d="M 773,127 L 773,173"></path>
  <path class="dg-qbar" d="M 782,127 L 782,173"></path>
  <path class="dg-qbar" d="M 791,127 L 791,173"></path>
  <text class="dg-t dg-c" x="880" y="138.5">Kafka config</text>
  <text class="dg-s dg-c" x="880" y="154.5">compacted · {rule, version}</text>
  <text class="dg-s dg-c" x="880" y="170.5">cross-region</text>
  <path class="dg-line" d="M 726,150 L 752,150"></path>
  <path class="dg-head" d="M 752,155 L 752,145 L 760,150 Z"></path>
  <rect class="dg-warn" x="526" y="206" width="200" height="56" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="626" y="230.5">shadow → enforce</text>
  <text class="dg-s dg-c" x="626" y="246.5">would-be 429 rate first</text>
  <rect class="dg-box" x="760" y="206" width="204" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="862" y="230.5">Reconciler</text>
  <text class="dg-s dg-c" x="862" y="246.5">shares from observed traffic</text>
  <path class="dg-line" d="M 826,262 L 826,290 L 500,290 L 500,166 L 488,166"></path>
  <path class="dg-head" d="M 488,161 L 488,171 L 480,166 Z"></path>
  <text class="dg-lbl" x="560" y="284">rule + share push, p99 &lt; 10 s</text>
  <path class="dg-line" d="M 626,182 L 626,198"></path>
  <path class="dg-head" d="M 621,198 L 631,198 L 626,206 Z"></path>
  <rect class="dg-box" x="36" y="380" width="240" height="56" rx="8"></rect>
  <path class="dg-qbar" d="M 49,389 L 49,427"></path>
  <path class="dg-qbar" d="M 58,389 L 58,427"></path>
  <path class="dg-qbar" d="M 67,389 L 67,427"></path>
  <text class="dg-t dg-c" x="174" y="404.5">Kafka decisions</text>
  <text class="dg-s dg-c" x="174" y="420.5">1 % allows · 100 % rejects</text>
  <path class="dg-line" d="M 136,316 L 136,372"></path>
  <path class="dg-head" d="M 131,372 L 141,372 L 136,380 Z"></path>
  <path class="dg-box" d="M 316,387 L 316,429 A 120,7 0 0 0 556,429 L 556,387 A 120,7 0 0 0 316,387 Z"></path>
  <path class="dg-box" d="M 316,387 A 120,7 0 0 0 556,387" style="fill:none"></path>
  <text class="dg-t dg-c" x="436" y="400">ClickHouse</text>
  <text class="dg-s dg-c" x="436" y="416">usage rollups · overshoot</text>
  <text class="dg-s dg-c" x="436" y="432">why was I 429'd</text>
  <path class="dg-line" d="M 276,408 L 308,408"></path>
  <path class="dg-head" d="M 308,413 L 308,403 L 316,408 Z"></path>
  <rect class="dg-box" x="596" y="380" width="180" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="686" y="404.5">Dashboard</text>
  <text class="dg-s dg-c" x="686" y="420.5">never reads Redis</text>
  <path class="dg-line" d="M 556,408 L 588,408"></path>
  <path class="dg-head" d="M 588,413 L 588,403 L 596,408 Z"></path>
  <path class="dg-line" d="M 436,380 L 436,350 L 862,350 L 862,270"></path>
  <path class="dg-head" d="M 867,270 L 857,270 L 862,262 Z"></path>
  <text class="dg-lbl" x="560" y="344">per-tenant traffic → shares</text>
  <rect class="dg-group" x="20" y="466" width="960" height="110" rx="12"></rect>
  <text class="dg-group-t" x="36" y="488">REGION B — THE SAME, PLUS THE GOSSIP AND THE EXCEPTION</text>
  <rect class="dg-box" x="36" y="498" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="186" y="526.5">Gateways + Redis, region B</text>
  <text class="dg-s dg-c" x="186" y="542.5">enforces limit × share_B</text>
  <rect class="dg-box" x="370" y="498" width="280" height="64" rx="8"></rect>
  <path class="dg-qbar" d="M 383,507 L 383,553"></path>
  <path class="dg-qbar" d="M 392,507 L 392,553"></path>
  <path class="dg-qbar" d="M 401,507 L 401,553"></path>
  <text class="dg-t dg-c" x="528" y="518.5">Counts, every 1 s</text>
  <text class="dg-s dg-c" x="528" y="534.5">G-counter per (tenant, window)</text>
  <text class="dg-s dg-c" x="528" y="550.5">merge by max per region</text>
  <path class="dg-line" d="M 336,530 L 362,530"></path>
  <path class="dg-head" d="M 362,535 L 362,525 L 370,530 Z"></path>
  <path class="dg-line" d="M 370,546 L 344,546"></path>
  <path class="dg-head" d="M 344,541 L 344,551 L 336,546 Z"></path>
  <text class="dg-lbl" x="390" y="574">partition → shares still sum to the limit</text>
  <rect class="dg-warn" x="690" y="498" width="274" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="827" y="526.5">Home-region exception</text>
  <text class="dg-s dg-c" x="827" y="542.5">exact quotas · +80 ms · small lease</text>
  <path class="dg-line" d="M 827,498 L 827,456 L 472,456 L 472,200 L 472,200"></path>
  <path class="dg-head" d="M 472,195 L 472,205 L 464,200 Z"></path>
  <text class="dg-lbl" x="600" y="449">billing-grade tenants only, +80 ms</text>
  <text class="dg-s" x="20" y="608">Nothing in Redis is a source of truth: a lost shard is a refill's worth of generosity. The rules and the decision log are the durable data, and neither is on the hot path.</text>
  <text class="dg-note" x="20" y="630">Approximate by design, bounded by the lease, exact for the tenants who pay for it.</text>
</svg>
</div>

<p class="diagram-cap">Draw the arithmetic before the gateway box — three and a half million counter operations a second is what forbids the service-in-front-of-the-store and the global counter. Then draw the two arrows between gateway and store and label them differently: the lease is how allows stay fast, the confirm is how rejects stay exact.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 600" role="img" aria-label="Rate limiter check path in three lanes. Gateway: resolve rules from memory, check the local lease, spend from it on a hit, else run the Lua script on the store with a lease size that shrinks near the limit; a reject is confirmed at the store, never from the lease. Store failure: per-shard circuit breaker, fallback bucket at a conservative fraction for fail-open rules, 503 for fail-closed. Multi-region: local shares that sum to the limit, per-second count gossip that tightens, and a two-second over-rejection during a traffic shift.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Allows come from the lease, rejects are confirmed at the store, and a missing store is a smaller local bucket.</text>
  <text class="dg-lane" x="30" y="76">THE CHECK — ONE RULE, ONE KEY, ONE SHARD</text>
  <rect class="dg-box" x="30" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="135" y="114.5">Resolve rules</text>
  <text class="dg-s dg-c" x="135" y="130.5">3–4 per request</text>
  <text class="dg-s dg-c" x="135" y="146.5">from memory, microseconds</text>
  <rect class="dg-warn" x="270" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="375" y="114.5">lease has tokens?</text>
  <text class="dg-s dg-c" x="375" y="130.5">(rule, subject) in process</text>
  <text class="dg-s dg-c" x="375" y="146.5">expires in seconds</text>
  <path class="dg-line" d="M 240,126 L 262,126"></path>
  <path class="dg-head" d="M 262,131 L 262,121 L 270,126 Z"></path>
  <rect class="dg-good" x="510" y="90" width="210" height="72" rx="8"></rect>
  <text class="dg-good-t dg-c" x="615" y="114.5">spend locally</text>
  <text class="dg-s dg-c" x="615" y="130.5">no store call</text>
  <text class="dg-s dg-c" x="615" y="146.5">the common case</text>
  <path class="dg-line" d="M 480,126 L 502,126"></path>
  <path class="dg-head" d="M 502,131 L 502,121 L 510,126 Z"></path>
  <text class="dg-lbl dg-c" x="495" y="118">yes</text>
  <rect class="dg-box" x="750" y="90" width="230" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="865" y="114.5">Lua script on the shard</text>
  <text class="dg-s dg-c" x="865" y="130.5">refill on read · lease n</text>
  <text class="dg-s dg-c" x="865" y="146.5">n shrinks near the limit → 1</text>
  <path class="dg-line" d="M 375,162 L 375,176 L 865,176 L 865,170"></path>
  <path class="dg-head" d="M 870,170 L 860,170 L 865,162 Z"></path>
  <text class="dg-lbl dg-c" x="620" y="172">no — one round trip, ~1 ms</text>
  <path class="dg-div" d="M 20,196 L 980,196"></path>
  <text class="dg-lane" x="30" y="230">THE ANSWER — AND THE STORE'S ABSENCE</text>
  <rect class="dg-warn" x="30" y="244" width="290" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="175" y="272.5">would reject locally?</text>
  <text class="dg-s dg-c" x="175" y="288.5">confirm at the store first</text>
  <rect class="dg-warn" x="350" y="244" width="290" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="495" y="272.5">429 · Retry-After · which rule</text>
  <text class="dg-s dg-c" x="495" y="288.5">RateLimit-Limit / Remaining / Reset</text>
  <path class="dg-line" d="M 320,276 L 342,276"></path>
  <path class="dg-head" d="M 342,281 L 342,271 L 350,276 Z"></path>
  <text class="dg-lbl dg-c" x="335" y="268">yes</text>
  <rect class="dg-good" x="670" y="244" width="290" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="815" y="272.5">allow · headers · 1 % sampled</text>
  <text class="dg-s dg-c" x="815" y="288.5">100 % of rejects logged</text>
  <rect class="dg-warn" x="30" y="330" width="290" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="175" y="354.5">shard timeout at 5 ms</text>
  <text class="dg-s dg-c" x="175" y="370.5">circuit breaker per shard, 1 s</text>
  <text class="dg-s dg-c" x="175" y="386.5">no retry on the hot path</text>
  <rect class="dg-box" x="350" y="330" width="290" height="72" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="354.5">fail_policy: open</text>
  <text class="dg-s dg-c" x="495" y="370.5">local bucket at limit / gateways × 2</text>
  <text class="dg-s dg-c" x="495" y="386.5">region over-admits ≤ 2× on those keys</text>
  <path class="dg-line" d="M 320,366 L 342,366"></path>
  <path class="dg-head" d="M 342,371 L 342,361 L 350,366 Z"></path>
  <rect class="dg-warn" x="670" y="330" width="290" height="72" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="815" y="354.5">fail_policy: closed</text>
  <text class="dg-s dg-c" x="815" y="370.5">503, not 429 — money and safety rules</text>
  <text class="dg-s dg-c" x="815" y="386.5">named per rule, default open</text>
  <path class="dg-line" d="M 640,366 L 662,366"></path>
  <path class="dg-head" d="M 662,371 L 662,361 L 670,366 Z"></path>
  <path class="dg-div" d="M 20,424 L 980,424"></path>
  <text class="dg-lane" x="30" y="458">MULTI-REGION — LOCAL SHARES, THEN GOSSIP</text>
  <rect class="dg-good" x="30" y="472" width="290" height="64" rx="8"></rect>
  <text class="dg-good-t dg-c" x="175" y="500.5">each region: limit × share</text>
  <text class="dg-s dg-c" x="175" y="516.5">shares sum to the limit — the safety property</text>
  <rect class="dg-box" x="350" y="472" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="500.5">counts gossiped every 1 s</text>
  <text class="dg-s dg-c" x="495" y="516.5">over the global limit → tighten next second</text>
  <path class="dg-line" d="M 320,504 L 342,504"></path>
  <path class="dg-head" d="M 342,509 L 342,499 L 350,504 Z"></path>
  <rect class="dg-warn" x="670" y="472" width="290" height="64" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="815" y="500.5">traffic shifts</text>
  <text class="dg-s dg-c" x="815" y="516.5">≤ 2 s of over-rejection, then re-split</text>
  <path class="dg-line" d="M 640,504 L 662,504"></path>
  <path class="dg-head" d="M 662,509 L 662,499 L 670,504 Z"></path>
  <text class="dg-note" x="30" y="570">The multi-rule race — two rules allow, the third rejects — costs one token on two buckets. Bound it, say it, and do not refund it on the hot path.</text>
</svg>
</div>

<p class="diagram-cap">The middle lane is where the design earns its availability: a store timeout is a smaller local bucket, not an unlimited one, and the rules whose limit is money say so themselves. The bottom lane's first box is the multi-region safety property; the gossip is only the tightening.</p>

### Flow A — the check, in the common case

1. A request arrives at a gateway with its principal already resolved: `user_id`, `api_key`, `tenant`, `tier`, client IP, route.
2. The gateway resolves applicable rules from its in-memory rule set — a few map lookups keyed by scope — and gets, say, three: `key:rps`, `user:rpm`, `endpoint:rps`. Rules in `off` are skipped; rules in `shadow` are evaluated and logged, never enforced.
3. For each rule it checks its **local lease** for `(rule, subject)`. Two of three have tokens left: decrement in memory, done, microseconds.
4. The third lease is empty. The gateway runs the bucket script on the store with `lease_n` sized for this subject (§9): the script refills the bucket by elapsed time, subtracts the lease, and returns how many it granted. One round trip, ~1 ms.
5. All three allow. The response carries the tightest rule's `RateLimit-Remaining` and `Reset`. A 1 % sample of the decision goes to the off-path stream.
6. **The failure path.** Two of the three rules allow and the third rejects. The two leases already consumed a token each for a request that will not be served. **This is the multi-rule race, and the honest answer is that it is not worth fixing:** the cost is one token on two buckets, bounded, and refunding it means a second round trip on every reject. State it, bound it, move on. (An interviewer who pushes gets: evaluate rules tightest-first so the most likely rejector runs first, which makes the waste rarer.)

### Flow B — the whale tenant, and the lease that shrinks

1. A shared enterprise API key does 50 k req/s across all 200 gateways in the region — 250/s per gateway against a limit of 60 k/s.
2. Each gateway holds a lease of **1 % of the limit** — 600 tokens — and refreshes it when it runs low. 250 req/s per gateway is a refresh every ~2.4 s: **~80 store ops/s for the whole key**, on one shard, instead of 50 k.
3. The key approaches its limit: the bucket's `remaining` is under 5 % of the burst. The script returns smaller leases as remaining shrinks — 60, then 6, then 1 — so that the last few hundred tokens are contended one at a time at the store. **Accuracy at the limit is exact; accuracy in the middle is loose, and nobody cares about accuracy in the middle.**
4. **The failure path.** A gateway dies holding a 600-token lease. Those tokens are gone from the bucket and were never used. The bucket refills at its rate; the lease's `expires_at` (a few seconds) is the bound on how long the loss lasts, and the store does not need to know the gateway died — it just stops seeing refreshes. **A dead gateway under-admits, never over-admits.** Say which direction the error goes.

### Flow C — the store shard is unreachable

1. The script call to shard 17 times out at 5 ms. The gateway does **not** retry on the hot path.
2. It marks shard 17 unhealthy for 1 s (a circuit breaker per shard, not per store) and, for every rule–subject pair that hashes there, falls back to a **local bucket at a conservative fraction of the limit** — `limit / gateways × 2`, say — so that the region as a whole over-admits by at most 2× on those keys while the shard is down.
3. Rules with `fail_policy: closed` — the billing-grade class — reject instead, with `503` rather than `429`, because "you are over your limit" would be a lie.
4. A metric fires: `fallback_active{shard=17}`. The API stayed up; a few subjects on one shard got a generous minute.
5. **The failure path.** The whole regional store is down, not one shard. The fallback is now every key, and the region is over-admitting by the fallback ratio across the board. The on-call is paged at 60 s; the fallback keeps working indefinitely; **the design's stated failure (§2) has occurred and it is the one it chose.** The alternative — rejecting all traffic when the limiter is down — was rejected in the first minute for a reason, and this is where you point back at it.

### Flow D — a global limit, enforced locally

1. Tenant T has a global limit of 100 k req/s and sends traffic to three regions in a 50/30/20 split.
2. Each region enforces a **local share** of the limit: 50 k, 30 k, 20 k, from its own store, with no cross-region call. Shares are computed by a reconciler from the last minute's observed traffic and pushed as rule parameters — the same channel as any config change.
3. Every second, each region publishes its per-tenant counts to the other regions (a small replicated stream — §10). Each region adds the others' last-known counts to its own and, if the global sum is over the limit, **tightens its local rate** for the next second.
4. Traffic shifts: region C fails over into region A. A now sees 70 % of T's traffic against a 50 % share and starts rejecting at 50 k. Within the reconciliation lag (≤ 2 s) it sees C's count go to zero and the reconciler re-splits: A's share rises to 70 k. **Two seconds of over-rejection during a failover, for a tenant at their global limit.** State that; it is the cost of no cross-region hop.
5. **The failure path.** The inter-region stream partitions. Each region keeps enforcing its last share; the global sum is unknown; the overshoot is bounded by **the sum of shares, which still equals the limit** — a partitioned region cannot over-admit beyond its own share. Shares are the safety property; the gossip is the optimisation. **Say which is which.**

---

## 7 · Deep dive — the algorithm, chosen from a comparison: why the token bucket, and what the fixed window gets wrong

### What you'd reach for first

A counter per minute: `INCR rl:{key}:{minute}`, reject when it passes the limit, expire the key. Fixed windows. Simple, one command, and it is what half the tutorials show.

### What breaks

- **The boundary admits twice the limit.** A limit of 1,000/min, 1,000 requests at 12:00:59 and 1,000 more at 12:01:00: two thousand in one second, every counter happy. Any window edge is a place where the limit is 2×, and a client that knows this can time to it.
- **It cannot say "burst."** Burst *is* the boundary bug, undesigned. A product that wants "up to 100 at once, 1,000/min sustained" cannot express it with one fixed counter — it needs two, and the two disagree at edges.
- **Every reset is a thundering herd** at the top of the minute for every client that was waiting.

### What replaces it

**A token bucket with refill computed on read**, and the alternatives laid beside it so the choice is visible:

| Algorithm | Burst | Accuracy | Cost per check | Memory per subject | Verdict |
|---|---|---|---|---|---|
| **Fixed window** | Accidental, 2× at edges | Poor at boundaries | O(1), one `INCR` | One int | The tutorial answer; the edge bug is disqualifying for a product that sells limits |
| **Sliding log** | Exact | **Exact** | O(log n) insert + count | **O(limit)** — a ZSET of timestamps | Right when the limit is small and exactness matters (login attempts: 5 per hour). Wrong at 10 k/s: 10 k timestamps per subject, per window |
| **Sliding window counter** | Approximate | Good — weights the previous window by overlap | O(1), two ints | Two ints | The pragmatic middle; cannot express a burst allowance distinct from the rate |
| **Token bucket / GCRA** | **Designed**: `burst` is a parameter | Exact against its own model | O(1), a few float ops | **Two numbers** | **Chosen.** One structure expresses rate *and* burst; refill is arithmetic on elapsed time; cost weights are a multiplier on `consume` |
| **Leaky bucket** | Smooths, never bursts | Exact | O(1) | Two numbers | The same math seen from the queue side; right for shaping outbound traffic, wrong for admission where you want to *allow* a burst, not delay it |

- **The bucket:** `tokens = min(burst, tokens + (now − ts) × rate); if tokens ≥ cost: tokens −= cost, allow; else reject with retry_after = (cost − tokens) / rate`. Two numbers stored, refill derived, no background job.
- **Cost weights ride on `cost`.** An inference call consumes 10, a read consumes 1. Same bucket, same script, one argument.
- **Multiple windows are multiple buckets** — `key:rps` (burst 100, rate 1,000/s) and `key:rpd` (burst 0, rate 10 k/day) — evaluated as separate rules. The daily one is where the lease is large and accuracy loose; the per-second one is where it is small and tight.
- **The sliding log survives as the exception** for small exact limits — password attempts, OTP sends — where O(limit) memory is five timestamps and exactness is the product.

**Cost, volunteered:**

- **Floats and clocks.** The refill is arithmetic on a timestamp; the timestamp must come from one clock (the shard's `TIME`), and `tokens` is a float that must not drift negative. Ten lines of Lua, tested against the boundary cases, and it is the most important ten lines in the system.
- **A burst allowance is a product decision that looks like a technical one.** `burst = 100` means a customer at zero can fire a hundred at once; a customer who reads "1,000/min" and gets rejected at request 101 within a second will open a ticket. Document the two numbers together.
- **`retry_after` from a bucket is a prediction**, not a promise — another request from the same subject on another gateway may consume the refill first. The header is best-effort and the client is told so.

**→ ties to the check-latency and accuracy NFRs.**

---

## 8 · Deep dive — atomicity and the shard: one script, one key, and the whale that lands on it

### What you'd reach for first

`GET` the counter, compare in the gateway, `INCR` if allowed. Or a rate-limit *service* in front of the store that does the same thing with a nicer API.

### What breaks

- **Read-then-write is a race.** Two checks for the same subject on two gateways both `GET` 1 remaining, both decide to allow, both `INCR`. The limit is exceeded by exactly the concurrency, on every gateway, every window. At 3.5 M ops/s the "rare" race happens thousands of times a second.
- **A service in front of the store is a hop on every one of ten million ops a second**, adds a p99, and makes a decision the gateway had every input to make itself. It also becomes the single thing that, when slow, slows the entire API.
- **Hash-distributing counters is right until one key is 5 % of the platform.** A shared enterprise key at 50 k req/s is 50 k script executions a second on one shard; that shard also serves a few hundred thousand other subjects, and they all get the whale's p99.

### What replaces it

- **One Lua script per check, executed atomically on one shard.** Redis runs a script to completion with no interleaving on that shard: the read, the refill arithmetic, the compare, and the write are one indivisible step. **The key `rl:{rule_id}:{subject}` is the unit of atomicity**, and everything the script needs is in that one key — which is why a rule–subject pair is never split across keys. The alternative — `WATCH`/`MULTI` optimistic transactions — retries under contention, which is exactly when you cannot afford it.
- **Partition on the key's hash**, so a given bucket always resolves to the same shard: the atomicity property is "one node," and the hash is what makes it one node every time. A request that triggers three rules touches three keys on (probably) three shards, **in parallel** — three round trips that overlap into one p99, not three p99s in a row.
- **Relieve the whale with the lease, not with sharding.** The gateway-local lease (§9) turns 50 k ops/s on one key into ~80. It is the hottest-key question, answered by asking whether every check needs to touch the key at all. Where a subject is hot *and* needs tight accuracy — a lease of one — **split the bucket into *k* sub-buckets** (`rl:{rule}:{subject}:{0..k}`, each with `limit/k`) and have each gateway pin to one sub-bucket; the error is bounded by `k × burst/k = burst`, and the hot key becomes *k* warm keys on *k* shards.
- **Say what the store is:** Redis Cluster, 20–40 shards per region, replicas for failover only — **not** for reads, because a read from a replica is the race in a different costume. The alternative worth naming: a purpose-built limiter store (an in-memory service sharded the same way, with the script as native code) wins on cost at extreme scale and loses on operational familiarity; Redis is the default until the Redis bill is the problem.

**Cost, volunteered:**

- **Lua on the hot path means the script is the product's most critical code and is deployed to the store, not the gateway.** Version it (`EVALSHA` by hash), load it on every shard at boot, and treat a script change as a release.
- **Resharding a Redis Cluster moves slots and, briefly, keys.** During a slot migration a bucket can be read on the old shard and written on the new; the window is milliseconds and the effect is a refill's worth of generosity. Fine for limits, and one more reason quotas that bill do not live here.
- **The sub-bucket split trades exactness for spread** — `k` buckets can each be at their limit while the sum is under it. Only use it where the lease alone is not enough, and say the bound.

**→ ties to the throughput and check-latency NFRs.**

---

## 9 · Deep dive — the gateway fast path: leases, the overshoot bound, and what fail-open actually means

### What you'd reach for first

Every check goes to the store. It is a millisecond. Or: every gateway keeps its own counters and syncs "eventually."

### What breaks

- **Every check to the store is 3.5 M ops/s at the p99 of a network hop**, and the store is now the platform's availability floor: a slow shard is a slow API.
- **Independent gateway counters over-admit by the gateway count.** 200 gateways each enforcing 1,000/min is a limit of 200,000/min with no one noticing. "Sync eventually" does not bound it, and a design that cannot say its bound has not designed the fast path — it has hoped for one.
- **"Fail open" with no local state means unlimited.** If the store is unreachable and the gateway just allows, a runaway client during a store incident is unthrottled at the exact moment the platform is fragile.

### What replaces it

**A lease of tokens per gateway per subject, sized by distance from the limit, with expiry; and a local fallback bucket that makes fail-open bounded.**

- **The lease.** A gateway asks the store for *n* tokens at once (`lease_n`); the script subtracts them; the gateway spends them from memory. Store traffic drops by *n*×. The lease has an expiry (a few seconds); unused tokens on expiry are simply lost — the bucket refills on its own.
- **The overshoot bound, stated:** in-flight leased tokens ≤ **gateways × lease size**. With 200 gateways and a lease of 1 % of the limit, the region can be **≤ 2× over the limit** in the worst case where every gateway just leased and nobody used any — and in practice, since leases are spent as they are taken, the steady-state overshoot is the *unused* fraction, a few percent. **Which knob bounds it: the lease size.**
- **Leases shrink as the subject approaches the limit.** The script returns `min(requested, remaining × 0.1)` and never more than remaining; near the limit it returns one token at a time. So **the error is large where it does not matter and zero where it does** — a subject at 40 % of its limit is over-counted by a few percent; a subject at 99 % is exact.
- **A dead gateway under-admits.** Its leased tokens were subtracted and never spent; they come back through refill at the bucket's rate. Direction of error: conservative. Duration: the lease expiry. Say both.
- **Fail-open is a local bucket, not an absence of one.** When the store is unreachable the gateway enforces from a local bucket at `limit / gateways × 2` — every gateway assumes it is one of *N* and takes twice its fair share. The region over-admits by at most 2× per rule, a runaway client is still throttled, and the API is up. **Fail-closed rules** (`fail_policy: closed`) reject with `503` instead, and only rules whose limit is money or safety carry that policy.
- **Rejections are exact.** A reject never uses the lease — a request that would be rejected locally is confirmed against the store first (one extra round trip, on the path that is already returning an error). This is the asymmetry that makes "never block a paying customer for store latency" true: the fast path is only ever used to *allow*.

**Cost, volunteered:**

- **The gateway is now stateful in a small way.** Leases live in process memory and are lost on restart; the cost is the refill delay above, and the benefit is that no gateway needs to know about any other.
- **The bound is per region.** Multi-region multiplies it (§10), and a subject with a small limit (60/min) gets no lease at all — every check is a store hit, and that is correct: small limits are where exactness matters and where the volume is trivially small.
- **Two code paths — leased allow and store-confirmed reject — means two things to test**, and the property to test is *"the sum of tokens spent across all gateways never exceeds the bucket's issuance plus refill,"* which is a property-based test, not a unit test.

**→ ties to the accuracy and availability-of-the-decision NFRs.**

---

## 10 · Deep dive — multi-region: enforce locally, reconcile globally, and make the exact case an exception

### What you'd reach for first

One global Redis. Or: every region calls the subject's "home region" store. Either way, one authoritative counter everyone consults.

### What breaks

- **60–150 ms per check** against a 5 ms budget. Disqualified by §2 before any other property is considered.
- **The home region is a single point of failure for every tenant homed there**, and a region outage now takes down admission for customers who were never in that region.
- **A global store with local read replicas** is the read-then-write race with a WAN in the middle: replicas lag by hundreds of milliseconds, and every gateway reading a replica admits against stale counts — unbounded over-admission dressed up as consistency.

### What replaces it

**A spectrum, a chosen default, and a named exception.**

| Position | Mechanism | Latency | Availability | Accuracy | When |
|---|---|---|---|---|---|
| **Fully local** | Each region enforces the full limit independently | Best | Best | Over-admits by the region count | Acceptable only for limits that are per-region by definition (per-IP, per-endpoint capacity) |
| **Local shares + async reconciliation** — **chosen default** | Each region enforces a share of the global limit from local state; per-tenant counts are replicated across regions every ~1 s; shares are re-split from observed traffic | Local, ~1 ms | Regional — a partition degrades to "local shares," which is still safe | Overshoot ≤ **(regions − 1) × share drift × reconciliation lag**; ~2 s of a traffic shift | Every ordinary tenant limit |
| **Home-region authoritative** | One region owns the counter; others call it | +1 cross-region RTT | Home region's | Exact | **The exception**: billing-grade quotas, contractual hard caps — a handful of tenants who opt in and pay the latency |
| **Global consensus store** (Spanner-class) | Linearizable counter | +consensus RTT | Multi-region strong | Exact | Never for this hot path; the billing page's ledger is where exact global money lives, off the request path |

- **The default, mechanically.** The reconciler (a small stateless job per region) reads each tenant's per-region traffic from the decision stream, computes shares proportional to the last minute — `50/30/20` — and writes them as rule parameters through the ordinary config channel. Each region runs its bucket at `limit × share`. **The sum of shares equals the limit, so the shares alone are a safe bound** even with the gossip dead.
- **The gossip is the tightening.** A per-tenant count per region is published every second to a replicated stream (Kafka with MirrorMaker, or a purpose-built CRDT counter — a G-counter per `(tenant, window)` merges by max per region and is exactly this). Each region computes the global sum from its own count plus the others' last-known; if the sum is over the limit, it reduces its local rate for the next second by the overshoot. **Convergence in ≤ 2 s** is the NFR, and it is the lag that bounds the multi-region overshoot.
- **Traffic shift.** A region fails over; the receiving region briefly enforces its old share and over-rejects the tenant at the limit for the ~2 s until the reconciler re-splits. **That is the cost of the design, in the direction of rejecting rather than admitting**, and it is worth saying that the direction was chosen: under-admitting a tenant at their limit for two seconds during a regional failover is invisible; over-admitting by a region's worth is a bill.
- **The exception, mechanically.** A rule with `enforcement: home_region` skips the local bucket and calls the home region's store with a small per-tenant lease (tens of tokens) to amortise the RTT — the same lease mechanism, across a WAN, for tenants whose contract says "exactly 1 M calls a month and not one more." Latency: +80 ms for those tenants only. Availability: their home region's. Both stated in the contract.

**Cost, volunteered:**

- **Shares are a lagging estimate.** A tenant whose traffic pattern changes faster than the reconciler's window gets over-rejected in the growing region and under-used in the shrinking one. The window is a knob (one minute default) and the trade is responsiveness against flapping.
- **Two channels to operate:** the config push and the count gossip, each replicated across regions. Both can fall behind, and each has a metric — `share_age`, `gossip_lag` — that is the honest signal of how approximate the limiter currently is.
- **"Approximately global" is a phrase the contract must contain.** A tenant who buys "100 k req/s globally" and measures 103 k during a failover will ask. The answer — the bound, the lag, and the home-region option — has to be written down before the first such ticket.

**→ ties to the multi-region and accuracy NFRs.**

---

## 11 · Deep dive — dynamic configuration, failure policy, and what you measure off the hot path

### What you'd reach for first

Limits in a config file, deployed with the gateway. Or rules in a database the gateway queries per request.

### What breaks

- **A deploy per limit change** means an operator raising one tenant's limit is a release, and a release is the thing that goes wrong on a Friday.
- **A database read per request is a hop** (§3) — and a database outage is now an admission outage.
- **A bad rule ships to every gateway at once.** A typo that sets the free tier to 60/day instead of 60/min rejects a million customers within ten seconds of being saved, with no way to see it coming.
- **The control plane is down for thirty minutes** and nobody decided what the gateways do meanwhile.

### What replaces it

- **Rules in Postgres, versioned, pushed.** The control plane validates (`burst ≥ limit/window`, no overlapping composite scopes, tier references resolve), bumps the rule's version, and publishes `{rule_id, version}` to a config stream. Gateways consume it and fetch the rule — the hint-not-value pattern from the settings-sync page — and hold the full set in memory. **Propagation p99 < 10 s**; the metric is `config_version_age` per gateway.
- **Shadow mode is a first-class rule state.** A new or changed rule runs in `shadow` first: evaluated on every request, its would-be decision logged at 100 %, nothing enforced. The operator watches the would-be `429` rate for a few minutes, then flips to `enforce`. The typo above shows up as "this rule would reject 98 % of traffic" *before* it rejects anyone. **This is the cheapest safety control on the page and the one most designs skip.**
- **Fail policy is per rule, defaulting to open.** `fail_policy: open` → local fallback bucket (§9). `fail_policy: closed` → `503` on store failure, for rules whose limit is money or safety. The default is open because an admission system that can take the API down is worse than one that occasionally admits too much, and the exceptions are named in the rule, not in code.
- **Control plane down:** gateways keep the last rule set indefinitely and keep enforcing; `config_version_age` climbs; a new gateway booting with the control plane down loads the last snapshot from the config stream's compacted topic. **Worst case: a limit change is delayed by the outage. No decision changes.**
- **Observability, entirely off the hot path.** A 1 % sample of allows and 100 % of rejects go to a decision stream → ClickHouse. From it: `429` rate per rule and per tier; the top rejected subjects; **measured overshoot** (tokens admitted per window vs limit — the number that says how approximate the limiter actually is today); store p99 per shard; `fallback_active` per shard; lease refresh rate (a proxy for hot keys); `config_version_age`; `share_age` and `gossip_lag` for the multi-region path. The dashboard's usage numbers come from the same stream, rolled up per minute.
- **Abuse is a different product, and the boundary is worth stating.** IP-only limiting punishes everyone behind a corporate NAT or a mobile carrier's CGNAT and is trivially evaded by an IPv6 /64. The limiter's job is to enforce a principal's allowance; abuse detection (many keys from one payer, credential stuffing, scraping) consumes the same decision stream with slower, richer signals and *feeds rules back in* — a rule with `scope: ip` and a short TTL is how the abuse system's verdict is enforced, at the speed of config propagation rather than the speed of a request.

**Cost, volunteered:**

- **Shadow mode doubles the evaluation for shadowed rules** and logs at 100 %. Fine for a rule being rolled out; catastrophic if fifty rules are left in shadow forever. Alert on shadow rules older than a day.
- **The config stream is one more replicated thing**, and it needs compaction so a booting gateway can load the current set without replaying history.
- **Per-rule fail policy is a footgun** if the default is ever flipped. It is the one setting on the page that should require a second approver.

**→ ties to the config-propagation, availability, and observability NFRs.**

---

## 12 · Data model, sharding, and storage decisions

**Partition on `hash(rule_id, subject)`, and say why it is not `subject` alone.** A request's three rules touch three keys; hashing each independently spreads a hot subject's rules across shards, and each check is still one key on one shard — the atomicity unit. Hash-tagging *all* of a subject's rules to one shard (`{subject}`) would let a single pipelined call check them together, and would concentrate every whale's every rule on one node. **Independent hashing, parallel calls: the p99 is one round trip, and the whale's load spreads.**

**The hot shard is the whale's key, and the design's response is to stop touching it.** The lease (§9) reduces the hottest key's store traffic by two to three orders of magnitude; the sub-bucket split (§8) is the second lever. Neither involves moving the key.

**Nothing in the store is a source of truth.** Buckets are recomputable from the rules; a lost shard is a refill's worth of generosity; **the only durable data on the page is the rule set and the decision log, and neither is on the hot path.**

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Bucket state** | 3.5 M atomic script calls/s per region (35 k with leases), sub-ms | **None** — loss is a window of generosity; every key has a TTL | **Redis Cluster**, 20–40 shards per region, one Lua script, replicas for failover only | "Postgres serialises on a hot row at a thousand updates a second — three orders short. DynamoDB does atomic counters at ~10 ms — twice the budget on its own. This is the one design where Redis is the primary store, and it is allowed to be because a lost counter costs nothing" |
| **Gateway leases and fallback buckets** | Every check; in-process | None — lost on restart, bounded by expiry | **Process memory** on each gateway | "A dead gateway under-admits for a lease expiry. That direction is the one I want" |
| **Rule set** | Read on every request; written by operators; ~50 k rows | **System of record**, versioned, 7 years of history | **Postgres**, `UPDATE … WHERE version = $expected`, audit table of every change | "Config, not data. It lives in the boring store and is cached in every gateway" |
| **Config stream** | ~10 writes/hour; every gateway subscribed; compacted | Replayable; Postgres is the truth | **Kafka**, compacted topic keyed by `rule_id`, replicated across regions | "The push carries a version, not a value; a gateway that missed it fetches the rule. Redis Pub/Sub would drop the message for a gateway mid-reconnect" |
| **Decision log** | 1 % of allows + 100 % of rejects ≈ 50 k rows/s | 90 days | **Kafka → ClickHouse**, `ORDER BY (rule_id, subject, ts)` | "Every `429` is explainable — rule, version, subject, remaining. The dashboard reads this, never the buckets" |
| **Usage rollups** | Read by dashboards; per subject per minute | 30 d minutes, 2 y hours | **ClickHouse materialized view** over the decision log (rejects are logged at 100 %, so the reject count is exact; allows are scaled from the sample) | "A customer refreshing their usage page cannot add load to the shard their traffic is hashed to" |
| **Cross-region counts** | One write/s per region per active tenant; read by every region | Best-effort, ≤ 2 s | **Replicated Kafka topic** (or a G-counter CRDT service); regions merge by max-per-region | "The shares are the safety property; this stream is the tightening. A partition degrades to shares, which still sum to the limit" |
| **Shares** | Rewritten per tenant per minute by the reconciler | Derived from the decision log | **Rule parameters**, through the config stream | "A share is just a rule parameter — one channel to operate, not two" |
| **Home-region buckets** (exact-quota tenants) | Cross-region script calls with small leases | Same as bucket state, in one region | **The home region's Redis Cluster** | "Exactness for the tenants who pay for it, at +80 ms, and their availability is their home region's" |
| **The Lua script** | Loaded on every shard at boot; invoked by hash | Versioned in the repo | `EVALSHA` by content hash, loaded by the deploy | "Ten lines that are the whole concurrency story. Changing them is a release" |

### Data lifecycle — the append-only entities

| Entity | Growth | Hot | Warm | Cold | Restore |
|---|---|---|---|---|---|
| **Decision log** | ~50 k rows/s ≈ 300 GB/day compressed | 90 days in ClickHouse — the dispute window for a `429` | — | Parquet in S3 for 2 years, per day | Minutes; "why was I rate-limited on March 3" is answerable |
| **Usage rollups** | Tiny | 30 days at minute grain, 2 years at hour grain | — | — | Recomputable from the log while the log exists |
| **Rule history** | Tiny | Forever in Postgres | — | — | n/a — it is the audit trail |
| **Bucket state** | Bounded by TTL at 2× window | Live | — | — | **Not an archive**; a lost key is a refilled bucket |

### The signals that tell you this is broken

- **Measured overshoot per rule** — admitted per window ÷ limit, from the decision log. The honest number for "how approximate is the limiter today." Near 1.0 is healthy; rising is leases too large or gossip lagging.
- **Store p99 per shard**, and **`fallback_active` per shard** — a shard in fallback is a region over-admitting on its keys.
- **Lease refresh rate per subject** — the top of this list is the whale list, and a new entry is a new hot key before it is a problem.
- **`429` rate per rule and per tier**, with a step-change alert — a config typo shows here first, and shadow mode is what makes it show *before* it bites.
- **`config_version_age` per gateway** — a gateway that has not seen a config update is running stale rules.
- **`share_age` and `gossip_lag`** — the multi-region path's honesty metrics.
- **Shadow rules older than a day** — someone forgot to flip one, and it is logging at 100 %.

---

## 13 · Traps — the ranked list

**Design traps**

1. **Read-then-write.** `GET`, compare, `INCR`. The race happens thousands of times a second at this rate; the check has to be one atomic script on one key (§8).
2. **A rate-limit service in front of the store.** A second hop on ten million ops a second, and a new availability floor for the API (§8).
3. **Fixed windows.** 2× at every boundary, no way to express burst, a herd at every reset (§7).
4. **A global counter consulted per request.** Thirty times the latency budget. Enforce locally, reconcile globally, state the overshoot (§10).
5. **Independent per-gateway counters with no bound.** 200 gateways is a 200× limit. A fast path is a lease with a stated size, not a hope (§9).
6. **Fail-open meaning unlimited.** The local fallback bucket is what makes fail-open safe; without it a runaway client is unthrottled during the store incident (§9).
7. **Fail-closed by default.** The limiter takes the API down. Closed is for rules whose limit is money, and it is named per rule (§11).
8. **No shadow mode.** A typo in a tier's limit rejects a million customers before anyone can see the number (§11).
9. **Gateway clocks in the refill.** Two hundred clocks, a second of skew, a second of free tokens; the script reads the shard's `TIME` (§5, §7).
10. **No TTL on buckets.** A per-IP rule fills the store with keys for addresses that never return (§3).
11. **Reading buckets from replicas.** The race with a replication lag in the middle (§8).
12. **Dashboard reads against the hot store.** Every usage-page refresh lands on the whale's shard (§5, §12).
13. **A `429` that does not say which rule.** The customer cannot tell a burst limit from a daily quota and files the wrong ticket (§5).
14. **IP as the principal.** CGNAT and corporate NATs punish thousands for one; IPv6 evades it with a /64. IP is one scope among several, and abuse is a separate product (§11).

**Performance traps**

15. **The whale on one shard with no lease.** 50 k script calls a second on one key, and everyone hashed there inherits its p99 (§3, §8).
16. **Hash-tagging all of a subject's rules to one shard.** One pipelined call, and every whale's every rule on one node (§12).
17. **Leases with no shrink near the limit.** Exact where it does not matter, loose where it does — backwards (§9).
18. **Sliding log at a large limit.** O(limit) timestamps per subject per window (§7).
19. **Retrying the store on the hot path.** A slow shard becomes a slower API; the circuit breaker is per shard and the fallback is immediate (§6 Flow C).
20. **Logging every allow at 100 %.** A million rows a second for a dashboard. Sample allows; log every reject (§11).

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

21. **Claiming the global limit is exact.** The interviewer knows it is not, and the bound is a better answer than the claim. Say "approximate, bounded by *this*, exact for *these tenants* at *this* cost" in the first minute and the multi-region follow-up becomes a confirmation rather than a trap.

---

## 14 · The five-minute skeleton (draw this cold)

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 450" role="img" aria-label="Rate limiter five-minute skeleton. The arithmetic across the top; then the gateway with its leases, the Redis cluster with one script per key, and the bucket formula; then the lease bound, the control plane with shadow mode, and the decision log; then multi-region shares plus gossip and the 429 contract; and a margin lane of the signals and the sentence about approximation.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="44" rx="8"></rect>
  <text class="dg-good-t dg-c" x="495" y="94.5">1 M req/s × ~3.5 rules = 3.5 M counter ops/s · p99 5 ms — no scan, no second hop, not one node</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <rect class="dg-box" x="30" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="148.5">Gateway</text>
  <text class="dg-s dg-c" x="180" y="164.5">rules in memory · local leases · fallback bucket</text>
  <text class="dg-s dg-c" x="180" y="180.5">the fast path allows; rejects are confirmed</text>
  <circle class="dg-num" cx="30" cy="128" r="9"></circle>
  <text class="dg-num-t" x="30" y="131.4">2</text>
  <rect class="dg-box" x="350" y="128" width="300" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="148.5">Redis Cluster</text>
  <text class="dg-s dg-c" x="500" y="164.5">one Lua script, one key per rule–subject</text>
  <text class="dg-s dg-c" x="500" y="180.5">refill on read · TIME from the shard · TTL</text>
  <circle class="dg-num" cx="350" cy="128" r="9"></circle>
  <text class="dg-num-t" x="350" y="131.4">3</text>
  <rect class="dg-box" x="670" y="128" width="290" height="64" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="156.5">tokens = min(burst, t + Δt·rate)</text>
  <text class="dg-s dg-c" x="815" y="172.5">consume cost · fixed window admits 2×</text>
  <circle class="dg-num" cx="670" cy="128" r="9"></circle>
  <text class="dg-num-t" x="670" y="131.4">4</text>
  <rect class="dg-box" x="30" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="180" y="232.5">Lease bound</text>
  <text class="dg-s dg-c" x="180" y="248.5">≤ gateways × lease · shrinks to 1 near the limit</text>
  <circle class="dg-num" cx="30" cy="208" r="9"></circle>
  <text class="dg-num-t" x="30" y="211.4">5</text>
  <rect class="dg-box" x="350" y="208" width="300" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="500" y="232.5">Control plane</text>
  <text class="dg-s dg-c" x="500" y="248.5">Postgres rules → config stream · shadow → enforce</text>
  <circle class="dg-num" cx="350" cy="208" r="9"></circle>
  <text class="dg-num-t" x="350" y="211.4">6</text>
  <rect class="dg-box" x="670" y="208" width="290" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="815" y="232.5">Decision log</text>
  <text class="dg-s dg-c" x="815" y="248.5">1 % allows, 100 % rejects → ClickHouse → usage</text>
  <circle class="dg-num" cx="670" cy="208" r="9"></circle>
  <text class="dg-num-t" x="670" y="211.4">7</text>
  <rect class="dg-box" x="30" y="284" width="460" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="260" y="308.5">Multi-region</text>
  <text class="dg-s dg-c" x="260" y="324.5">local shares that sum to the limit + 1 s gossip · home-region exception at +80 ms</text>
  <circle class="dg-num" cx="30" cy="284" r="9"></circle>
  <text class="dg-num-t" x="30" y="287.4">8</text>
  <rect class="dg-box" x="510" y="284" width="450" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="735" y="308.5">The 429</text>
  <text class="dg-s dg-c" x="735" y="324.5">Retry-After · RateLimit-* · which rule</text>
  <circle class="dg-num" cx="510" cy="284" r="9"></circle>
  <text class="dg-num-t" x="510" y="287.4">9</text>
  <text class="dg-lane" x="30" y="370">IN THE MARGIN — SAID, NOT DRAWN</text>
  <rect class="dg-box" x="30" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="400.5">measured overshoot</text>
  <text class="dg-s dg-c" x="140" y="416.5">admitted ÷ limit, per rule</text>
  <circle class="dg-num" cx="30" cy="382" r="9"></circle>
  <text class="dg-num-t" x="30" y="385.4">10</text>
  <rect class="dg-box" x="270" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="380" y="400.5">store p99 · fallback_active</text>
  <text class="dg-s dg-c" x="380" y="416.5">per shard</text>
  <rect class="dg-box" x="510" y="382" width="220" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="620" y="400.5">top leased subjects</text>
  <text class="dg-s dg-c" x="620" y="416.5">the whale list</text>
  <rect class="dg-box" x="750" y="382" width="210" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="855" y="400.5">approximate by design</text>
  <text class="dg-s dg-c" x="855" y="416.5">bounded · exact for who pays</text>
</svg>
</div>

<p class="diagram-cap">Badge 1 is a line of arithmetic and it forbids two designs before they are drawn. Badge 5 is the sentence the multi-region follow-up is fishing for — say it unprompted. Badge 4 is the one formula on the board, and the loser beside it is the tutorial answer.</p>

1. **The arithmetic, top-left, before any box:** 1 M req/s × ~3.5 rules = **3.5 M counter ops/s**, p99 5 ms. Write beside it: *"no scan, no second hop, not one node."*
2. **Gateway:** rule set in memory (~50 k rules, 10–20 MB), **local leases**, local fallback bucket, per-shard circuit breaker. Label it **"the fast path allows; rejects are confirmed."**
3. **Redis Cluster**, 20–40 shards per region, **one Lua script, one key per rule–subject**, refill on read, `TIME` from the shard, TTL 2× window. Label it **"the atomicity unit is one key."**
4. **The bucket in one line:** `tokens = min(burst, tokens + Δt × rate)`, consume `cost`. Beside it the loser: *"fixed window admits 2× at the edge."*
5. **The lease, with its bound:** overshoot ≤ gateways × lease size; **shrinks to 1 near the limit**; a dead gateway under-admits for one expiry.
6. **Control plane:** Postgres rules, versioned, `If-Match` → **config stream** → every gateway; **shadow → enforce**; `fail_policy` per rule, default open.
7. **Decision log** (1 % allows, 100 % rejects) → Kafka → ClickHouse → usage rollups and the dashboard. Label it **"nothing reads the hot store but the check."**
8. **Multi-region:** local **shares** that sum to the limit (the safety property) + per-second **count gossip** that tightens (the optimisation); **home-region exception** for exact quotas at +80 ms.
9. **The `429`:** `Retry-After`, `RateLimit-*`, and **which rule**.
10. In the margin: measured overshoot, store p99 per shard, `fallback_active`, top leased subjects, `config_version_age`, `gossip_lag` — and the sentence: *"approximate by design, bounded by the lease, exact for the tenants who pay for it."*

---

## 15 · Variants — what actually changes

**The governing axis: how exact the limit has to be, which is the same as what a wrong decision costs.** Every row has a subject, a counter, an atomic check, and a policy for when the counter is unreachable. What moves along the axis is how much of this page's approximation machinery is allowed, and where the counter is permitted to live.

| Product | What a wrong decision costs | Exactness required | The delta from this page |
|---|---|---|---|
| **API rate limits** — this page | A few extra requests admitted, or a customer briefly over-rejected | **Bounded approximate** | As written: leases, fail-open with a local bucket, local shares with gossip |
| **Spend limits** — the billing page §8 | **Dollars** — but recoverable, because the usage event is still recorded | Bounded approximate, **with the bound stated in dollars** | The same lease design against a balance instead of a bucket; the lease is a *reservation* of the worst-case cost and is *settled* when the true cost is known. Fail-open on the check, never on the record; the overshoot bound is a number in the NFR table |
| **Billing-grade quota** — "1 M calls a month, contractually" | Revenue, or a breach | **Exact** | §10's home-region exception, for the few tenants who pay for it: a cross-region hop, small leases, and the tenant's availability tied to one region. Off this page's default path on purpose |
| **Concurrency limits** — "at most 10 in flight" | Overload of a downstream that cannot queue | Exact-ish, and **tokens are returned** | A semaphore, not a bucket: acquire on start, release on finish, with a **heartbeat lease** so a crashed caller's slot is reclaimed. The refill-on-read trick vanishes; lease expiry becomes the whole correctness story |
| **Login / OTP throttling** — 5 attempts an hour | Account takeover | **Exact, and fail-closed** | Tiny limits, tiny volume: the **sliding log** wins (five timestamps per subject), the store hit on every check is fine, and the fail policy inverts — a store outage rejects logins rather than admitting a brute-force |
| **Volumetric DDoS** — millions of packets a second from many sources | Availability of everything | Approximate is fine; **speed is everything** | Not this system. Per-IP and per-prefix counters at the CDN or in the kernel (XDP), no principal, no config stream, no dashboard. Named as out of scope in §1 because the moment it is in scope, the design is a different one |
| **GPU credit allocator** — budget + quota + rate limit + fair-share | Money, and capacity fairness | Budget exact (a ledger); quota and rate limit approximate (this page); fair-share is a scheduler property | Four controls that answer four questions, kept distinct: **this page is the rate-limit control only.** The budget is the billing page's ledger with reserve-then-settle; the fair-share is the ChatGPT page's §10 scheduler. The trap is building all four as one counter |

**The lesson:** every row has the same check; the cost of being wrong decides whether the counter may live in a cache, whether it may be leased, and which way it fails. Say what a wrong decision costs in the first minute, and the rest of the design is where you put the counter.
