# Design LLM API Billing — Usage Metering & Billing

## The question

> *"Design billing for a token-based LLM API. Developers send requests, they're charged per token, and at the end of the month we have to take their money."*

**The product.** A developer signs up, gets an API key, and starts sending requests to a model. Every request consumes tokens — the text going in and the text coming out — and each model charges a different rate for each. There is no plan and no seat count: you pay for exactly what you used, and what you used is only knowable once the work is finished. Some customers spend eleven cents a month and some spend two million dollars, and both need a number they can trust, a breakdown of where it went, and a way to stop the meter before a runaway script empties their account.

**What a working system delivers**

- The dollar figure on your usage page within a minute of the request that produced it, split by model, project, and key.
- A spending limit that actually stops the spending — and a warning before you reach it rather than after.
- An invoice at the end of the month that adds up, that you can dispute line by line, and that matches your card statement to the cent.
- Never being charged twice for the same request, and never being charged for one that failed.
- Buying $500 of credits and having them usable seconds later, not tomorrow.

**Why this gets asked.** Money is the one number in a system that isn't allowed to be approximately right — and here it's derived from a firehose of events that arrive late, arrive twice, and occasionally don't arrive, then handed to a third party who moves funds you don't control. Each layer wants a different consistency model, and watching which one a candidate applies to all of them is the point of the exercise.

---

**Archetype:** usage metering & billing — lossy, high-volume telemetry that has to converge on an exact amount of money, settled through a third party.
**Cousins that reuse ~70% of this page:** AWS and GCP metered billing, Twilio, Snowflake credits, Cloudflare, Datadog host-hours, telecom rating & charging, ad-network budget pacing, any prepaid-credit consumable.

**What's actually being graded:** whether you notice this is **two systems, not one.** The meter is high-throughput, at-least-once, eventually consistent, and its correct answer is *log everything and dedupe later*. The money is low-throughput, strictly audited, and its correct answer is *never mutate a row and never trust a `200 OK`*. Candidates who build one pipeline from tokens to dollars either get the throughput right and lose the audit trail, or get the audit right and put a database transaction on the request path. **The seam between the two is an append-only ledger, and naming it as the seam is most of the answer.**

**The admission that scores highest, and that most candidates won't make:** *a hard spend limit cannot be enforced exactly.* The cost of a request is unknown until it finishes, thousands are in flight across hundreds of machines, and the balance is a single shared counter you cannot lock per request. So the answer isn't "we check the balance before every call" — it's **"here is the overshoot bound in dollars, here is the knob that shrinks it as you approach the limit, and here is why I'd rather overshoot by fifty dollars than put twenty milliseconds on every request."** That sentence is this page's version of Ticketmaster's *the seat map is a hint*: it's the moment you stop claiming a guarantee you can't deliver and start specifying the one you can.

**The one-line contrast to have ready if you've also prepped ChatGPT:** *both pages meter the same two integers — `inputTokens` and `outputTokens` on a run. On the ChatGPT page they're an input to the scheduler, and losing one costs you a metric. Here they're revenue, and losing one is money you can never invoice. Same field, and the cost of dropping it differs by three orders of magnitude — which is why that page can afford a fire-and-forget counter and this one needs an outbox.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "Three things live in this system and they want opposite properties. **Metering** is a firehose — order of ten thousand events a second, at-least-once at best, and every event I lose is revenue I can never invoice. **Enforcement** sits synchronously on the API request path with a single-digit-millisecond budget, in front of a call whose cost I don't yet know. **Settlement** moves real money through a payment processor where my only correctness tools are an idempotency key, a webhook that may arrive twice or out of order, and a reconciliation job. My plan is to split those three and join them with one append-only ledger: meter at-least-once and dedupe on the run id, enforce approximately with a stated overshoot bound, and settle exactly with a state machine plus daily reconciliation. I'd like to go deep on exactly-once metering and on why a hard spend limit is a bound rather than a guarantee. I'll treat tax calculation, dunning, and revenue recognition as named subsystems and leave them out."

**Why open this way:** it does three things in one breath. It reframes the problem away from "build a billing pipeline" toward *three subsystems with three different consistency requirements*, which is the actual insight. It pre-commits two deep dives, both of which are ground you've drilled. And the phrase "a bound rather than a guarantee" tells the interviewer within sixty seconds that you know the thing this problem exists to test — before you've drawn a single box.

---

## 1 · Functional requirements

1. **Meter every request exactly once** — capture input, cached-input, output, and reasoning tokens per model, attribute them to an organization, project, and API key, and turn them into money at the price that was in effect when the request ran.
2. **Enforce spend controls in near real time** — a prepaid credit balance, a hard limit that blocks, soft thresholds that notify, all settable per organization *or* per project, plus usage alerts at 50 / 75 / 90%.
3. **Settle** — close a billing period into an invoice, collect it through a payment processor, and reflect the outcome (paid, failed, refunded, credited) back into the customer's balance and the ledger.

Requirement 1 is a correctness invariant wearing a feature costume, and the same is true of the word *exactly*. State it as a requirement anyway: every later decision gets justified against it.

**Out of scope (say them):** tax and VAT calculation and remittance — that's a rules engine and a filing obligation, and it's a vendor (Stripe Tax, Avalara); dunning and collections sequences; revenue recognition and GAAP reporting, which reads the ledger but is a separate consumer; marketplace payouts to third parties; seat-based subscription proration (that's the §15 variant); fraud scoring at signup; and the inference path itself — the model, the GPU pool, and the streaming transport are the ChatGPT page.

**Below the line, likely follow-ups:** multi-currency and FX rate pinning, enterprise committed-spend contracts with tiered discounts, batch-API and cached-input discount pricing, free grants that expire, auto-recharge when credits run low, and per-key rate limits (a different mechanism from spend limits — see the ChatGPT page's §10, which keeps fairness and priority separate for the same reason).

**Why this section is worth two full minutes here and not on most pages:** billing is where a systems interview quietly becomes a product interview. Naming spend limits, alerts, credits, refunds, and currency as things you *considered and scoped* is the difference between designing a metering pipeline and designing a billing product. The three requirements above are deliberately the three that touch money; everything in the out-of-scope list is real product surface you're choosing not to build in fifty minutes, and saying so is the point.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Metering completeness** | **≤1 lost event per 10⁶**, any gap alarms, reconciled daily against the gateway's request log | At ~$10M/day of usage, a silent 0.1% loss is **$3.6M/year** nobody ever notices. 10⁻⁶ is ~$10/day — below the cost of the engineering to do better, which is how you know it's the right target |
| **Metering duplication** | **Exactly-once *effect*: zero double-charges**, enforced by a unique index rather than by delivery semantics | A lost event costs *us* money; a duplicated one costs the *customer* money and produces a refund, a support ticket, and a screenshot on social media. They are not symmetric, and every ambiguous case in this design resolves toward under-billing |
| Usage visibility | Dashboard **≤60s** behind the request; invoice-grade totals exact at close | Developers debug a runaway script by watching the number move. 60s is a product choice; 24h is a support queue |
| **Enforcement latency** | Adds **p99 ≤5ms** to the API request path, **zero network hops in the common case** | It sits in front of a call whose latency budget is already spent on TTFT (ChatGPT page, §2). Any design needing a round trip per request has already lost |
| **Enforcement accuracy** | Overshoot on a hard limit bounded by `(admission nodes × lease size) + in-flight reservations` — **≤$1,000 for the largest org at 10% of its limit, ≤$5 inside the last 1%** | Exactness is unachievable (§8). The *bound* is the requirement, and making it shrink as you approach the limit is the entire design |
| Availability — admission | 99.99%, and **fails open on the check, never on the record** | A minute of unmetered usage costs ~$7k and is recoverable, because the usage event is still written. A minute of refusing all paid API traffic costs the same money *and* takes down every customer's production |
| Availability — settlement | 99.9%; hours of slack tolerated | Invoicing is a batch job against a 30-day deadline. Nothing on this path is user-facing in real time |
| **Ledger durability** | Zero acknowledged writes lost, append-only, **7-year retention**, WORM archive | Tax authorities, financial audit, and card-network chargeback disputes all reach back years. This is the one component with no degraded mode |
| **Fault tolerance** | Survives loss of the rating workers (Kafka replays), Redis (fails open; usage still recorded), and the processor (invoices queue and retry). **Does not survive loss of the usage log** | Naming the one component that isn't allowed to fail is what forces the gateway outbox and `acks=all`. A design where everything survives everything hasn't been sized under failure |
| **Security & auditability** | **No card data in our systems** (PCI **SAQ-A**, not SAQ-D); ledger hash-chained; price changes and manual credits under **dual control** with an immutable audit log; **no human has write access to the production ledger** | Financial systems are compromised by insiders and by tampering far more often than by load. Access control and audit are functional requirements here, not hygiene — see §11 |

**The sentence that earns the point:** *"I'm not going to claim the hard limit is exact, because it can't be — the cost isn't known until the request finishes and there are thousands in flight. What I'll give you instead is the bound, in dollars, and the knob that shrinks it to a few dollars in the last one percent of the budget. That trade — a bounded overshoot in exchange for zero network hops on the request path — is the central decision on this page."*

---

## 3 · Numbers that reframe the problem

**Assume** ~1B API requests/day and ~$10M/day of gross usage across ~2M organizations with non-zero spend. Both are assumptions, stated as such; every figure below is derived from them and each one changes a decision.

**Per request**

- **Average run: ~500 input + ~1,000 output tokens.** On a cheap model at $0.15/1M in and $0.60/1M out, that's **$0.000675 — under a tenth of a cent.** *This is the number that picks your money type.* Integer cents rounds it to zero and you bill nothing; round *up* to a cent and you have overcharged by 15× on a billion requests a day. **Store money in integer nano-dollars and round exactly once, at the invoice line.**
- **Cost is unknown at admission time and bounded only by `max_output_tokens`.** A request authorized for 4,000 output tokens on an expensive model is an open-ended commitment of up to ~$0.06 that might turn out to be $0.002. Everything in §8 follows from this one asymmetry.

**Global — and the reframe**

- **1B requests/day = ~11.6k events/s average, ~50k/s at peak** (4× diurnal). At ~300 bytes per usage event that's **~300 GB/day raw, ~30 GB/day columnar, ~11 TB/year.** Set that against the ChatGPT page's 1.8 PB/year of conversation content: **the entire billing dataset is well under 1% of the product's storage.** Say this out loud early — *metering is not a big-data problem, it's a correctness problem* — because it's what licenses you to spend the whole hour on exactly-once and reconciliation instead of on ingest capacity.
- **The contrast that makes that true: meter per run, not per token.** A usage event per token would be ~1.5×10¹² events/day — **~17M events/s**, a genuinely different and much worse system. Incremental checkpoints during a long stream are fine and sometimes necessary (§7), but **the billable record is one row per run.**
- **Revenue at risk from metering loss:** $10M/day × 0.1% = **$10k/day, $3.6M/year, invisible.** That figure is the entire business case for the gateway outbox, `acks=all`, and the daily three-way reconciliation. Quote it when someone asks why you didn't just fire-and-forget an HTTP call.

**Per organization — the number that sizes the hot path**

- **Skew: the top ~1% of orgs generate ~80% of usage.** Assume the largest single org sustains ~5k req/s and peaks near **15k req/s.** That is 15,000 read-modify-writes per second **against one balance row.** A Postgres row under `SELECT … FOR UPDATE` serializes at roughly **500–2,000 updates/s** — one to two orders of magnitude short — and it's this number, not aggregate throughput, that kills the obvious design.
- **Enforcement lag, priced:** if you decrement *after* the run instead of before, then at 15k req/s with ~3s average runs you have **~45,000 requests already committed** past the moment the limit was crossed. At $0.02 each that's **~$900 of overshoot from a perfectly correct implementation.** This is why §8 reserves rather than records.

**Month-end**

- **2M invoices.** Closing them all at 00:00 UTC on the 1st is a thundering herd against the processor and your own ledger. **Stagger by `hash(org_id) % 28` — anniversary billing — and 2M/28 days ≈ 71k/day ≈ 0.8/s.** *That decision means the invoicing service needs no special capacity at all*, which is the cheapest scalability win on the page and it costs one modulo.

---

## 4 · Core entities

- **Organization** — id, currency, `billing_mode` (`prepaid_credits | postpaid_invoice`), tax id, processor customer id, payment-method token *(a token, never a card)*
- **Project / ApiKey** — the attribution granularity below the org. Spend limits and usage rollups hang off either
- **UsageEvent** — **`run_id`** *(the idempotency key)*, org, project, api_key, model, `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_tokens`, `status`, `reservation_id`, `occurred_at`, `ingested_at`
- **PriceVersion** — (model, token_kind) → nano-dollars per token, with `effective_from` / `effective_to`
- **LedgerEntry** — org, account, direction, `amount_nano`, `source_type`, **`source_id`**, `period`, `recorded_at`, `price_version`, `prev_hash`, `hash`. **One entry per org per hour, not per request** — see below
- **CreditGrant** — amount, source (purchase / promo / service credit), `expires_at`, consumption priority
- **Invoice** — org, period, lines, subtotal / tax / total, state
- **PaymentAttempt** — invoice, attempt number, idempotency key, processor intent id, state, failure code
- **SpendControl** — scope (org | project | key), `hard_limit`, soft thresholds, alert recipients

**Load-bearing details:**

- **`UsageEvent.run_id` is the idempotency key for the entire system**, and it is **generated by the inference gateway, not by billing** — it's the same id the ChatGPT page's `Run` entity carries. Billing isn't present at the moment the work happens, so it cannot be the thing that names it. Every downstream stage — ingest, dedupe, rating, ledger, invoice line — carries it unchanged. Without one id minted at the origin, "at-least-once delivery" is just a polite name for "sometimes double-charge."
- **`LedgerEntry` is append-only, and money is never a mutable column.** A refund is a new entry. A re-rating is a *correction* entry carrying only the delta. A discount is an entry at period close. There is no `UPDATE ledger SET amount = …` anywhere in this system, and the reason is not purity: **an append-only ledger is the only structure where "what did we think last Tuesday, and why?" is answerable**, which is what a chargeback, an audit, and a customer dispute all actually ask.
- **The ledger records money movements, not requests, and idempotency is enforced at two different levels.** Runs are deduped in the metering pipeline, on `run_id`, within a bounded window (§7). The **ledger** is four orders of magnitude smaller — one entry per org per hour rather than one per request — and its `UNIQUE (source_type, source_id)` with `source_id = hash(org, hour, rating_version)` makes re-running an aggregation window a no-op. **Conflating the two is how a billion rows a day ends up in a database that wanted fifty thousand**, and separating them is what keeps the money in something transactional and auditable while the meter lives in something columnar and cheap.
- **`PriceVersion` is effective-dated, and rating pins the version by `occurred_at`, never by `now()`.** Prices change. A re-run of rating over three-week-old events must produce byte-identical numbers to the first run, or every bug fix becomes a billing incident (§9).

---

## 5 · API

```
# Customer-facing — dashboard and management API, authenticated per org
GET  /v1/orgs/{org}/usage?start=&end=&group_by=model,project,api_key
                                       → { rows[], as_of }        (warehouse, ≤60s stale)
GET  /v1/orgs/{org}/balance            → { credits_nano, pending_nano, hard_limit_nano, as_of }
POST /v1/orgs/{org}/credits            Idempotency-Key: <uuid>
     { amount_nano, payment_method_id }
                                       → { payment_intent_id, client_secret, state }
PUT  /v1/orgs/{org}/spend-controls
     { scope, hard_limit_nano, soft_thresholds[], alert_emails[] }
GET  /v1/orgs/{org}/invoices/{id}      → { state, lines[], subtotal, tax, total }
POST /v1/orgs/{org}/invoices/{id}/pay  Idempotency-Key: <uuid>

# Internal — called by the inference gateway only, never reachable by a customer
POST /internal/v1/admit                → { allow, reservation_id, ttl_s }
     { org, project, api_key, model,     | { deny, reason: hard_limit | no_credits | suspended }
       prompt_tokens, max_output_tokens }

POST /internal/v1/usage                → 202 Accepted
     { run_id, org, project, api_key, model, status,
       input_tokens, cached_input_tokens, output_tokens, reasoning_tokens,
       reservation_id, occurred_at }

# Processor → us
POST /webhooks/psp                     signature-verified; 200 means "durably queued", not "applied"
```

**Decisions to narrate, unprompted:**

- **Two internal calls, not one, because they carry opposite guarantees.** `/admit` is synchronous, on the critical path, budgeted at 5ms, and **allowed to fail open**. `/usage` is asynchronous, returns 202, and is **never allowed to be lost** — the gateway writes it to a local outbox **in the same transaction that finalizes the run**, so "the model produced tokens" and "we wrote down that it did" commit together or not at all. Splitting them is what lets one be fast and the other be durable. **→ ties to the enforcement-latency and metering-completeness rows in §2.**
- **`/admit` returns a reservation, not a boolean.** A boolean would be a lie: the answer to *may I run this?* depends on what it costs, and nobody knows yet. So we reserve the worst case — `prompt_tokens × input_price + max_output_tokens × output_price` — and the usage event settles the truth and releases the difference. **This is Ticketmaster's hold with the nouns changed: take the cheap reversible action first, and let the expensive irreversible one come second.**
- **`run_id` is minted by the gateway, not by billing.** Billing isn't present at the moment the work happens, so it can't be the component that names it. Every stage downstream carries it unchanged.
- **Every money-mutating endpoint takes an `Idempotency-Key`.** We store `(key, request_hash, response)` for 24 hours and replay the stored response byte-for-byte on a retry — and return **`409`** if the same key arrives with a *different* body, because that's a client bug and silently accepting it is precisely how a double-charge is born.
- **`balance` and `usage` both return `as_of`.** The API states its own staleness rather than implying a freshness it doesn't have. It costs one field and removes an entire class of support ticket.
- **No endpoint anywhere in this system accepts a card number.** The browser posts the card straight to the processor's hosted field and we receive a token. **That single API-design decision is what keeps us in PCI scope SAQ-A — a short self-assessment — instead of SAQ-D, which is an annual on-site audit, a segmented cardholder-data network, and quarterly scans.** It belongs in the API section rather than a security appendix precisely because it is an API decision with a seven-figure compliance consequence.

---

## 6 · High-level design — flows

```
                        ┌───────────────────────┐
     API request ──────▶│   Inference Gateway   │──────▶ model / GPU pool
                        └──┬─────────────────┬──┘        (the ChatGPT page)
             ① admit       │                 │  ② usage event → gateway OUTBOX,
             sync, ≤5ms    │                 │     same txn as run completion
                           ▼                 ▼
                 ┌──────────────────┐   ┌──────────────────────────────┐
                 │  Admission Svc   │   │  Kafka  usage.raw            │
                 │  in-proc leases  │   │  key=org_id · acks=all       │
                 └────────┬─────────┘   └───────────────┬──────────────┘
                    lease │ refill                      │
                          ▼                             ▼
                 ┌──────────────────┐   ┌──────────────────────────────┐
                 │  Redis Cluster   │   │  Rate & Post workers          │
                 │  budget:{org}    │◀──│  dedupe on run_id             │
                 │  resv:{run_id}   │   │  price = f(model, occurred_at)│
                 └──────────────────┘   └───────────────┬──────────────┘
                          ▲                             │ rated events, deduped
       materialized       │                             ▼
       balance ───────────┘            ┌──────────────────────────────────┐
                                       │  ClickHouse — rated usage        │
                                       │  ~1B rows/day · dashboards       │
                                       └───────────────┬──────────────────┘
                                            hourly     │ aggregate per org
                                                       ▼
                                       ┌──────────────────────────────────┐
                                       │  Ledger — Postgres + Citus       │
                                       │  ~55 entries/s · append-only     │
                                       │  UNIQUE(source_type, source_id)  │
                                       └───┬──────────────────────────┬───┘
                                           │                          │ period close
                                           ▼                          ▼
                             ┌────────────────────┐   ┌─────────────────────┐
                             │ Reconciliation     │   │ Invoicing Service   │
                             │ gateway ↔ ledger   │   └──────────┬──────────┘
                             │        ↔ settlement│              │ charge
                             └─────────▲──────────┘   ┌──────────▼──────────┐
                                       │              │  Payment Processor  │
                                       └──────────────│  (Stripe)           │
                                          webhooks    └─────────────────────┘
```

**The two properties to point at before walking a request through it:**

1. **The vertical split is the consistency split.** Everything left of centre is synchronous, approximate, and allowed to fail open. Everything right of centre is asynchronous, exact, and not allowed to lose a write. The ledger is where they meet, and it is the only component both halves touch.
2. **Nothing on the request path writes to a database.** Admission reads a lease it already holds in process; the usage event goes to a local outbox. The first durable, ordered, money-shaped write happens in a worker nobody is waiting on.

### Flow A — one metered request

1. Request arrives at the gateway with an API key. The key resolves to `(org, project)` from a cache.
2. Gateway calls **`/admit`** with the model, prompt token count, and `max_output_tokens`.
3. Admission computes the **worst-case cost** and decrements it from the **lease it already holds in local memory** — no network hop in the common case. If the lease is exhausted it fetches another from Redis (§8). If the org is over its hard limit or out of credits, it returns `deny` and the gateway returns `429` with a machine-readable reason before a single GPU-second is spent.
4. The run executes. Streaming or not, **billing observes it exactly once, at the end** — not per token (§3).
5. On completion the gateway writes the run's terminal state **and** the usage event to its outbox **in one local transaction**, then acks the customer.
6. An outbox pump publishes to `usage.raw` on Kafka, keyed by `org_id`, `acks=all`.
7. A rate-and-post worker consumes it, **drops it if `run_id` is already in its keyed dedupe state** (§7), looks up the price version effective at `occurred_at`, computes the amount in nano-dollars, and writes the rated event to ClickHouse. The dashboard number moves within ~60s.
8. The same worker releases the leftover reservation back to the org's Redis budget — the difference between the worst case we held and what the run actually cost — and bumps the materialized balance.
9. **An hourly job aggregates each org's rated usage into one ledger entry**, keyed so that re-running the window is a no-op (§4, §9). **Money moves once an hour; the meter moves twelve thousand times a second, and the two are deliberately not the same write.**

**Failure path — the gateway process dies mid-stream:** the outbox row either committed with the run's terminal state or neither did. If it committed, the pump publishes it on restart and the customer is billed correctly for a run they may not have fully received. If neither committed, the run is **unbilled**, the reservation expires on its TTL, and the daily reconciliation (§11) surfaces it as a gateway request with no rated-usage row. **We bias to under-billing every single time** — the §2 asymmetry made concrete.

**Failure path — Redis is unavailable at step 3:** admission **fails open** and allows the request, while step 5 still records the usage. We lose enforcement for the duration and lose *no* revenue, which is the correct side to fail on. **→ ties to the admission-availability row in §2.**

### Flow B — an organization crosses its hard limit

1. Usage events keep landing; each rated event decrements the org's materialized balance in Redis — **the balance moves per event even though the ledger only moves per hour**, because enforcement can't wait for accounting.
2. Admission nodes discover it when their current lease is refused a refill — **not** at the instant of crossing. That gap is the overshoot, and it is bounded, not zero (§8).
3. As the org approaches the limit, the lease size shrinks — dollars at 10% remaining, cents in the last 1% — so the bound tightens exactly where it matters.
4. New requests get `429 spend_limit_exceeded` with the limit, the current spend, and a link to raise it.
5. Soft thresholds fire separately, off the ledger CDC stream rather than the request path, so an alerting outage can never block traffic.

**Failure path — requests already in flight when the limit is crossed:** they run to completion and are billed. **This is a decision, not an oversight, and you should say so:** killing an in-flight generation to save four cents produces a truncated response, a support ticket, and a customer who trusts the platform less. The overshoot is bounded by the reservations outstanding, and we quote that bound in the docs.

### Flow C — buying credits, and closing a period

1. `POST /credits` with an `Idempotency-Key` creates a **PaymentAttempt** row in `PENDING` and a processor payment intent whose idempotency key is derived from `(org, attempt_id)`.
2. The customer's browser confirms the intent directly with the processor. **No card data reaches us.**
3. The webhook arrives. We verify the signature, dedupe on the processor's event id, and only then write a `CreditGrant` plus its ledger entry and refresh the materialized balance.
4. At period close (staggered by `hash(org_id) % 28`, §3), invoicing sums the ledger for the period, applies tiered discounts at the *aggregate* level (§9), writes lines, and charges the stored payment token.
5. The invoice moves to `PAID` **only on a webhook or a reconciliation query** — never on the HTTP response to the charge call.

**Failure path — the charge call times out with an unknown outcome:** we do not retry blindly and we do not mark anything. We retry **with the same idempotency key**, which the processor answers with the original result if it exists. If it's still unknown, the invoice sits in `PROCESSING` and the daily settlement reconciliation resolves it (§10). **The state machine has no transition that fires on a bare `200 OK`, and that absence is deliberate.**

### Flow D — a refund or service credit

1. A support agent issues a credit. Under a per-agent daily cap it applies immediately; above it, **a second approver is required** (§11).
2. It is written as a **new ledger entry** of type `service_credit` with the agent, approver, and reason in the audit log. **Nothing is updated. The original usage entry stays exactly as it was.**
3. If the money has to leave — a refund of a real charge rather than a credit against future usage — the invoice's state machine handles it and reconciliation matches it to the processor's refund object.

**Failure path — the refund succeeds at the processor and our ledger write fails:** the customer has their money and our books say otherwise. Reconciliation catches it the next day as a settlement-without-ledger-entry and files it to the exception queue. **This case is why reconciliation is a component with a staffed queue rather than a cron job with a log line.**

---

## 7 · Deep dive — exactly-once metering over an at-least-once pipe

### What you'd reach for first

The gateway finishes a run and `POST`s the usage to a billing service. If the call fails, retry it. It's one HTTP call, it's obviously correct, and it's what almost everyone draws.

### What breaks, specifically

**Three things, and the third is the one that matters.**

1. **Coupling.** Billing's p99 is now on the inference path, and a billing deploy is an inference outage. At 12k req/s a 30-second billing blip is **360,000 dropped usage events** — call it **$4,000** of revenue that no reconciliation can recover, because there is no record anywhere that those requests happened.
2. **Retries duplicate.** The gateway can't distinguish "billing didn't receive it" from "billing received it and the response was lost." Retry on the second case and you have charged twice — the failure mode §2 says is strictly worse than losing it.
3. **The crash window.** The model produced tokens, the customer received them, and the gateway process died before the `POST`. That revenue is gone and nothing in the system knows. **This is the failure the whole design is built around**, and it's invisible in the naive version because there is no artifact left behind.

### What replaces it

**An outbox at the origin, a log in the middle, and a unique index at the end** — three mechanisms, each covering exactly one of the three failures.

- **Outbox.** The gateway writes the usage row into a local table **in the same transaction that finalizes the run.** The two facts — "tokens were produced" and "we recorded that they were" — become atomic. A separate pump reads the outbox and publishes. Crash anywhere and the row is either committed and will be published, or absent along with the run.
- **A log, not a queue.** Kafka, keyed by `org_id`, `acks=all`, `min.insync.replicas=2`, 7-day retention. Keying by org gives per-org ordering (so a reservation release never overtakes its own reservation) and gives every downstream consumer — rating, alerting, the warehouse, the fraud pipeline — the *same* events without the gateway knowing they exist. **Replay is the actual feature:** a rating bug means rewinding an offset, not reconstructing history from logs.
- **A bounded-window dedupe, and be honest that it's bounded.** The rating worker is a stateful consumer — Flink or Kafka Streams — keyed on `run_id`, with RocksDB-backed state and a **7-day TTL set equal to the Kafka retention**, so the dedupe window exactly covers the replay window. That equality is the point: **you can only be asked to reprocess what you can still read, so the window that matters is the one you can replay into.** The tempting alternative is a permanent unique index on every run, and you should name why it's rejected — a `UNIQUE (run_id)` constraint over **365 billion rows a year** is a database nobody wants to operate, to defend against a duplicate that cannot physically arrive after the log has aged out. Outside the window, the backstop is the daily reconciliation (§11), not a constraint. So the guarantee, stated precisely, is **exactly-once *effect* within the replay window, plus detection outside it** — which is the only kind of exactly-once anyone actually ships. Say it that way; a candidate who claims exactly-once *delivery* has told you they haven't built one.

**Late events get a stated policy, not a shrug.** An event whose `occurred_at` falls inside a closed period lands in the *next* period with its original timestamp preserved on the line. That's a product decision — the alternative, reopening a closed invoice, is worse for everyone including accounting — and it's the kind of rule you want to have already made when the interviewer asks.

**Cost, volunteered:**

- **The dedupe state is real infrastructure**: ~11.6k keys/s × 7 days is on the order of 7 billion keys, sharded across the consumer group and checkpointed. That's a stateful streaming deployment with its own failure modes — checkpoint restore time, state skew on the whale org — rather than a stateless worker you can restart casually.
- Keying by `org_id` makes the largest customer a **hot partition** — one org's events all land on one partition, and at 15k/s that's a real ceiling. Fix it for the top N orgs with a salted key `org_id:{0..15}` and accept that you've traded per-org total ordering for per-sub-key ordering; the reservation-release logic has to be commutative for that to be safe, and it is, because it's an addition.
- The customer sees usage seconds late rather than instantly. That's the **≤60s** row in §2, and it's cheap to defend.
- The outbox adds a write to the gateway's hot path — a local insert in a transaction it was already committing, so microseconds, but it's not free and the gateway team will ask.

---

## 8 · Deep dive — enforcing a spend limit you cannot enforce exactly

### What you'd reach for first

`BEGIN; SELECT balance FROM orgs WHERE id = ? FOR UPDATE; … COMMIT;` before every request. Exact, obvious, and correct in a single-threaded universe.

### What breaks

**The row, first.** A single Postgres row under `FOR UPDATE` serializes at roughly **500–2,000 updates/s** with commit latency in the way. The largest org peaks near **15k req/s** — an order of magnitude past it — and every one of those requests is now queued behind a lock while a GPU sits idle. You've added 5–20ms to a path with a 5ms budget and created a global choke point on your best customer.

**Then the deeper problem, which survives fixing the row.** Suppose you replace it with a Redis `DECRBY` — genuinely fine for throughput, and I'd ship it for an org doing a few hundred requests a second. **You still don't know what to decrement.** The cost of the run is unknown until it ends. So you have two options and both are wrong:

- **Decrement after the run.** Correct amounts, but enforcement is one request-duration late. At 15k req/s with ~3s runs, **~45,000 requests are already committed** when the limit is crossed — **~$900 of overshoot from a flawless implementation.**
- **Decrement an estimate before the run.** Now enforcement is timely but the balance is wrong until you correct it, and you've done two round trips per request instead of one.

### What replaces it: reserve-then-settle, on leased budget

**Two mechanisms, and keeping them separate is the point.**

**Reserve-then-settle** fixes the *unknown cost*. At admission we reserve the **worst case** — `prompt_tokens × input_price + max_output_tokens × output_price` — under `resv:{run_id}` with a TTL comfortably longer than the maximum run. When the usage event lands, the rating worker posts the true cost and releases the difference. The org's *available* budget is `balance − outstanding reservations`, so the system is always pessimistic: it will refuse a request it could have afforded before it will allow one it couldn't. **A stranded reservation from a crashed run self-heals at TTL** — no compensating transaction, no saga, just an expiry, which is the same trick Ticketmaster uses for an abandoned seat hold.

**Budget leases** fix the *hot row*. Each admission node fetches a slice of the org's budget — a lease — from Redis, then decrements it **in local memory with no network hop at all.** When the lease runs dry it fetches another. Redis sees one operation per lease instead of one per request, which turns 15k ops/s on a hot key into ~300, and the request path's p99 contribution drops to roughly zero. **→ ties to the enforcement-latency row in §2.**

**The trick that makes it defensible: the lease size is adaptive.** Fixed leases give a fixed overshoot, which is absurd for a customer at 0.1% of their budget and terrifying for one at 99.9%. So scale it to headroom:

| Remaining budget | Lease size | Worst-case overshoot at 200 admission nodes |
|---|---|---|
| > 10% | $5 | ~$1,000 + in-flight |
| 1–10% | $0.50 | ~$100 + in-flight |
| < 1% | $0.05 | ~$10 + in-flight |
| last $1 | no lease — per-request check against Redis | ~in-flight only |

**The bound is now proportional to how much room you have left**, which is exactly the shape a customer's intuition expects, and you pay the per-request round trip only in the last dollar where it's affordable because the traffic is about to stop anyway. **State the formula out loud — `overshoot ≤ (nodes × lease) + outstanding reservations` — because a number with a formula behind it is the thing being graded, not the number.**

**Cost, volunteered:**

- **The limit is not exact, and the docs have to say so.** "Hard limits are enforced within approximately $X" is a sentence someone in Legal will read. Getting to *exactly* zero requires a synchronous consensus round per request, and it would cost 20ms on every API call in the platform to save a customer $50 once a year.
- **A dead admission node strands its lease** until the TTL. That direction is safe — we temporarily under-serve rather than over-serve — but it means a rolling deploy of 200 nodes briefly locks up 200 leases, so the TTL has to be shorter than a deploy cycle and the lease has to be released on graceful shutdown.
- **Redis becomes a dependency of the send path.** Decide the direction now: **fail open on the check, never on the record.** A minute of unmetered usage is ~$7k and fully recoverable at invoice time because §7's pipeline still wrote everything down. A minute of refusing paid traffic costs the same money and also takes down every customer's production.
- **Two sources of truth for "how much has this org spent"** — the fast approximate one in Redis and the exact one in the ledger. They must reconcile, the ledger must win, and the invoice must never be generated from the cache. Say that explicitly; it is the mistake this design makes possible.

---

## 9 · Deep dive — rating: turning tokens into money you can reproduce

### What you'd reach for first

Multiply tokens by a price constant at ingest and store the dollar amount. `amount = tokens * PRICE[model]`.

### What breaks

- **Prices change**, and each model has four independently-priced token kinds — input, cached input, output, and reasoning. A price cut announced on the 12th applies to usage from the 12th, and your invoice covers the 1st through the 30th. `PRICE[model]` has no way to express that.
- **Discounts are non-local.** A committed-spend contract with a volume tier — "$0.12/1M above 500M tokens" — cannot be evaluated one event at a time, because the tier a request falls into depends on events that hadn't happened yet when it was rated.
- **And the one that actually hurts: you will find a bug.** A model mispriced for three weeks, a token kind double-counted, a currency wrong for a region. Now you must re-rate ~20 billion events **without double-charging anyone**, while some of those events are already on invoices customers have paid.

### What replaces it

**Rating as a pure function, and corrections instead of rewrites.**

- **`rate(event, price_version, contract) → amount_nano`, with no clock inside it.** The price version is selected by `occurred_at`, never by `now()`. Given the same three inputs the function returns the same nano-dollars in 2026 that it did in 2024. **That determinism is the property that makes replay safe**, and it's worth naming as a property rather than describing as a behaviour.
- **The ledger entry records its inputs** — `price_version` and `rating_version` alongside the amount. An entry that can't tell you how it was computed is an entry you can't defend in a dispute.
- **Re-rating emits correction entries carrying only the delta**, referencing the original `run_id`, with `source_id = run_id + rating_version`. It never touches the original row. If the correction is against a closed period it lands as a credit or a line on the next invoice — the same rule as late events in §7, which is not a coincidence: **both are the same policy, that a closed period never reopens.**
- **Tiered discounts are computed at period close over aggregates**, not per event, and are written as their own ledger entries. Per-event rating gives you list price; the close applies the contract.

**Cost, volunteered:**

- **Money now arrives in two phases**, so the number on the dashboard mid-month and the number on the invoice legitimately differ by the discount. You have to show both — "usage at list price / your contract discount / amount due" — or field the same support ticket every month forever. That's a UI consequence of a data-model decision, and volunteering it is the kind of thing that reads as having shipped one.
- **Every analyst query has to know about corrections.** `SUM(amount)` over a `run_id` is right only if you include correction rows and exclude nothing; the naive query silently reports pre-fix numbers. Ship a view, not a table, and say why.
- The ledger grows by the number of corrections, and a bad re-rating over a billion events is a billion rows. Rate-limit re-rating jobs and require them to declare their expected blast radius before running — a re-rate is a production change to money.

---

## 10 · Deep dive — the payment processor is a distributed system you don't control

### What you'd reach for first

`charge = psp.charge(customer, amount)`, check for a 200, set `invoice.state = PAID`. Three lines, and it is wrong in four separate ways.

### What breaks

- **The timeout with an unknown outcome.** The request times out. The money may have moved. Retrying may charge twice; not retrying may lose the payment. **There is no local information that resolves this**, and it is the single most common way real billing systems produce double charges.
- **Retries without a stable key.** A retry with a fresh idempotency key is not a retry — it's a second charge with extra steps.
- **Webhooks are not a stream.** They arrive twice, they arrive out of order (`payment_intent.succeeded` before `payment_intent.created` is routine), they arrive minutes late, and occasionally they don't arrive at all. Code that assumes sequence will process a `failed` after a `succeeded` and mark a paid invoice unpaid.
- **The processor has state you don't.** Disputes, chargebacks, partial refunds, and bank-initiated reversals all originate on their side, days or months later.

### What replaces it

**An explicit state machine, a derived idempotency key, an order-independent webhook handler, and a daily reconciliation.** Four mechanisms; each one closes one of the four holes above.

```
DRAFT ──▶ OPEN ──▶ PROCESSING ──┬──▶ PAID ──▶ REFUNDED
                    ▲           │
                    │           └──▶ FAILED ──▶ RETRYING ──▶ WRITTEN_OFF
                    └───────────────────────────┘
```

- **No transition fires on an HTTP response.** `PROCESSING` is entered when we *send* a charge; leaving it requires a webhook or a reconciliation query against the processor's API. The absence of a `200 OK → PAID` edge is the whole design, and pointing at the missing edge on the diagram is a good use of ten seconds.
- **The idempotency key is derived, not random: `sha256(invoice_id + attempt_number)`.** It survives our process restarting, so a retry after a crash is still recognisably the same attempt. A new attempt number is a deliberate act — a dunning retry days later — not an accident of a lost variable.
- **The webhook handler is order-independent and idempotent.** Verify the signature, dedupe on the processor's event id, then **apply by reading the state of the referenced object rather than by trusting the event's implied sequence**. A late `failed` for an intent the processor now reports as `succeeded` is a no-op. Return 200 as soon as the event is durably enqueued — the handler must be fast and must not do the work inline, because a slow handler triggers the processor's own retries and you're now racing yourself.
- **Daily reconciliation against the settlement report** (§11) resolves every case the webhooks didn't: money at the processor with no ledger entry, ledger entries with no settlement, amounts that differ.

**Dunning is out of scope (§1) but name the hook:** `FAILED → RETRYING` with a backoff schedule, and a hard rule that **retry policy is driven by the processor's decline code** — a `insufficient_funds` is worth retrying in three days, a `card_stolen` is never worth retrying and retrying it is how you get your merchant account reviewed.

**Cost, volunteered:**

- **There is a window where the customer's money has moved and our system says "pending."** Seconds usually, hours occasionally. The balance API has to expose `pending_nano` as its own field rather than folding it into the balance, because folding it in means either lying or double-counting.
- **Reconciliation needs a staffed exception queue.** Not a dashboard — a queue with an owner and an SLA. This is headcount, and saying so out loud is a more senior answer than pretending the mismatches will be rare enough not to matter.
- **You are now coupled to the processor's data model** for disputes and refunds. Migrating processors later means migrating stored payment tokens, which is a vendor-assisted project measured in quarters. Worth accepting for SAQ-A, but accept it knowingly.

---

## 11 · Deep dive — reconciliation, audit, and the security posture

### What you'd reach for first

Trust the pipeline. The code is tested, the queue is durable, the numbers add up.

### What breaks

**Three independent sources of truth exist, and they will diverge.** The gateway's request log knows what ran. The ledger knows what we charged for. The processor's settlement report knows what money actually moved. A dropped Kafka partition, a mispriced model, a duplicated webhook, or a re-rating job that ran twice will separate them, and **nothing in the happy path notices.** At 1B requests/day, a defect rate of one in 10⁵ is **10,000 wrong charges a day** — which is a mailbag, a refund program, and a headline, not an anomaly.

### What replaces it

**A three-way daily reconciliation, and a ledger built so that tampering is detectable.**

- **Three-way diff, every day, per org.** Gateway request count and token totals vs. rated-usage row count and token totals vs. ledger entries vs. processor settled amounts vs. invoice totals — four hops, each of which can drop something the next one can't detect on its own. Every variance over a threshold opens an exception with the org, the amount, and the direction. **The metric that matters is not "did it match" but "how much money is currently unexplained," graphed over time** — a number that should sit near zero and whose slope is the real health signal for the whole system.
- **Hash-chained, append-only ledger.** Each entry stores `prev_hash` within its partition and its own `hash`. A daily job verifies the chains and publishes the head hashes to WORM storage (S3 Object Lock). It doesn't prevent tampering; **it makes tampering detectable and dated**, which is what an auditor is actually asking for.
- **Dual control on everything that creates money from nothing.** Price changes, manual service credits above a per-agent daily cap, spend-limit overrides, and re-rating jobs each need a second approver, and each writes an immutable audit record with actor, approver, before, after, and reason.
- **No human has write access to the production ledger.** Corrections go through a reviewed, versioned job that emits correction entries (§9). Read access is per-org scoped and logged. The most likely attacker on a billing system is not an anonymous internet actor — it's someone with a legitimate login, and the controls that matter are the ones that constrain them.
- **Encryption and isolation as stated properties, not adjectives:** TLS everywhere, at-rest encryption with per-environment KMS keys, org id enforced as a predicate in the data-access layer rather than remembered in each query, and **no card data anywhere in scope** (§5).
- **Abuse and fraud are billing problems, not just security ones.** Free-grant farming across throwaway orgs, stolen cards buying credits that get resold, and prompt-injected agents burning a victim's budget all appear first as anomalies in this data. The pipeline that detects them is the same CDC stream that feeds the dashboards, which is a good reason to build it as a stream rather than a nightly query.

**Cost, volunteered:**

- **Hash chaining constrains the ledger.** Chains are per-partition (a global chain would serialize every write), archival has to preserve chain heads, and any retention policy that deletes rows breaks verification — so old entries are archived, never deleted.
- **Dual control turns a ten-second customer-service credit into an hours-long one.** Mitigate with a bounded auto-approve budget per agent per day, which is itself a risk decision someone has to own.
- **The exception queue never reaches zero.** Budget for it permanently. A reconciliation system with no findings isn't clean, it's broken, and the first thing to check when the variance graph flatlines at exactly zero is whether the job is still running.

---

## 12 · Data model, sharding, and storage decisions

**Partition on `org_id`, everywhere, and say why it isn't about throughput.** Every question this system answers is scoped to one organization — what did they use, what do they owe, what did they pay — so an org's invoice close is a **single-shard transaction** and their usage query is a single-shard scan. Hash-distributing by `run_id` would spread load beautifully and turn every invoice into a scatter-gather. **You are sharding for query locality, not for write volume**, and naming which of the two you're doing is the same call the Ticketmaster page makes about `event_id`.

**The hot shard is the whale, and it is intentional.** The largest org is ~15k req/s of usage events against a shard doing a few hundred for everyone else. For the **ledger** that's irrelevant — it sees one entry per org per hour. For the **Kafka topic** and the **dedupe state** it's real, and the fix is a salted key `org_id:{0..15}` for the top ~100 orgs, which costs you per-org total ordering and is safe only because reservation release is commutative addition. For the **budget counter** it's the whole of §8.

### Storage decisions — every stateful component

| Component | Access pattern | Durability | Choice | What you say |
|---|---|---|---|---|
| **Gateway outbox** | Insert + delete, same txn as the run | Must survive the process, not the host | **The gateway's existing local Postgres**, one table, pumped by a sidecar | "It only has to be as durable as the run record it commits with, because they're the same transaction. Writing to Kafka directly from the request path was the alternative, and it loses the atomicity that makes this whole design work" |
| **Usage log** | Append, replay by offset, many consumers | Zero acknowledged loss, 7-day replay | **Kafka**, key `org_id`, `acks=all`, `min.insync.replicas=2`, 7-day retention | "SQS would deliver these fine and cost less to run, but it has no replay and no second consumer. I need to rewind three days after a rating bug, and I need the fraud and alerting teams reading the same events without the gateway knowing they exist" |
| **Dedupe state** | Point lookup by `run_id`, 7-day TTL | Rebuildable from the log | **Flink keyed state on RocksDB**, TTL = Kafka retention | "The obvious alternative is a permanent unique index, and I'm rejecting it: 365B rows a year of constraint to catch a duplicate that can't arrive after the log ages out. Outside the window, reconciliation is the backstop" |
| **Rated usage** | Insert-only ~12k/s; `GROUP BY` org, model, day | High — it's the dispute evidence | **ClickHouse**, `ORDER BY (org_id, occurred_at)`, monthly partitions | "Postgres models this perfectly and dies on it: 1B rows/day of `GROUP BY` is what columnar storage exists for. Snowflake or BigQuery would also work and I'd pick one of them if I had no infra team — I'm choosing on the per-query bill at this volume, not the data model" |
| **Budgets & reservations** | Read-modify-write per lease, TTL keys | **None — rebuildable from the ledger plus rated usage since the last close** | **Redis Cluster**, `budget:{org}` and `resv:{run_id}`, **fails open on read** | "This is a cache with a lease protocol on top, not a source of truth. If it's gone I lose enforcement for a minute and lose no revenue, because §7's pipeline still records everything. Losing it must never be able to lose money" |
| **Ledger, invoices, payments** | ~55 writes/s; `SUM` per org per period; multi-row txn at close | **Absolute, append-only, 7 years** | **Postgres + Citus**, sharded by `org_id`, `UNIQUE (source_type, source_id)`, hash-chained | The three-way debate below |
| **Price book** | Read-mostly, tiny, effective-dated | Absolute — it's an input to money | **Postgres**, versioned rows, cached in-process with a 60s TTL and a version watermark | "It's a few thousand rows read a billion times, so it wants to be in every process's memory. The watermark exists so a price change can't half-apply across a fleet mid-second" |
| **Idempotency keys** | Point lookup, 24h TTL | Enough to survive a retry storm | **Redis** with a Postgres backstop for money-mutating calls | "A lost idempotency record on a `POST /credits` is a double charge, so this one specific cache gets a durable writeback. Everything else in Redis here doesn't" |
| **Audit log & ledger chain heads** | Append, read almost never, read seriously once | **Immutable** | **S3 with Object Lock (compliance mode)** | "The requirement isn't durability, it's that *I* can't alter it either. Object Lock is the only cheap thing that makes that true" |
| **Cold archive** | Restore on dispute or audit | 7 years | **S3 Glacier Deep Archive**, one object per org-month | "Nobody reads this until a lawyer does" |

### The ledger store — a genuine three-way debate

The volume is unremarkable — **~55 entries/s, ~1.7B rows/year** — which means throughput does *not* decide it, and saying so first saves five minutes.

| Option | Fit | The sentence |
|---|---|---|
| **DynamoDB** | Point reads by org are perfect; period close is not | "Invoicing is `SUM … GROUP BY` over a period, and DynamoDB's answer to that is a scan or a second denormalized aggregate I have to keep correct myself. I'd be reimplementing the one thing a relational engine is definitionally good at, on the exact data I'm least willing to get wrong" |
| **CockroachDB / Spanner** | Fits, and gives multi-region strong consistency | "This is the right answer the day the ledger has to be active-active across regions, and I'd migrate rather than shard around it. Today it costs 2–5× and adds consensus latency to every commit for a global property nobody has asked for" |
| **Postgres + Citus** | **Chosen.** Shard by `org_id`; close is single-shard | "Fifty-five writes a second of money wants the most boring, most auditable, most widely-understood transactional engine available, and Citus buys me sharding without buying me a new consistency model. Real `SUM`, real constraints, real foreign keys between invoice and line" |

**The sentence that carries it:** *"I'm choosing on what invoicing needs, not on what metering needs — those are separate stores precisely so this decision doesn't have to serve both. If you told me we're going active-active across three regions next year, I'd take Spanner today and pay for it, and that's the specific thing that would change my mind."*

### Data lifecycle — the append-only entities, because year three is a plan or it's a problem

| Entity | Growth | Hot | Warm | Cold | Restore |
|---|---|---|---|---|---|
| **Rated usage** | ~300 GB/day raw, ~30 GB/day compressed, **~11 TB/yr** | 90 days in ClickHouse — the dispute and dashboard window, p95 query <1s | 18 months on ClickHouse's S3-backed tier, seconds-to-minutes | 7 years in Glacier Deep Archive, one object per org-month | ~12h, and it's a **stated support SLA** on any dispute reaching back past 18 months |
| **Ledger entries** | ~1.7B rows/yr, small | 24 months live, indexed | — | Partitions detached, compressed, kept in S3 and queryable as foreign tables | Minutes. **Never deleted** — deleting a row breaks the hash chain, which is the point |
| **Usage log (Kafka)** | ~300 GB/day | 7 days | — | — | Not an archive. If you need day 8, you read the rated store |
| **Audit log** | Tiny | 7 years, Object Lock | — | — | Immediate |

**The 90-day number is a product decision, not a derivation** — it's the chargeback window plus a margin, and if Legal says 180 the storage tier moves and nothing else does. Say that; presenting a policy choice as a technical constraint is the specific way these sections go subtly wrong.

---

## 13 · Traps — the ranked list

**Design traps**

1. **Storing money in cents.** A cheap-model request costs ~$0.0002. Integer cents rounds it to zero and you bill nothing; rounding up bills 15× too much a billion times a day. **Nano-dollars, and round exactly once, at the invoice line.**
2. **Rating with `now()` instead of `occurred_at`.** Every re-run after a price change silently produces different money, and every bug fix becomes a billing incident.
3. **Marking an invoice paid on an HTTP 200.** The state machine must have no such transition. The unknown-outcome timeout is the most common source of real double charges in real systems.
4. **Mutable money.** `UPDATE ledger SET amount = …` destroys the only thing an audit, a dispute, and a chargeback all need: what you believed last Tuesday and why. Corrections are new rows.
5. **One pipeline from tokens to dollars.** The meter and the ledger want opposite consistency models and opposite write volumes. Building one system gets you a billion rows a day in Postgres or an unauditable spreadsheet, and sometimes both.
6. **No idempotency key minted at the origin.** Without a `run_id` generated where the work happens, "at-least-once" is just a formal way of saying "occasionally double-charge."
7. **Claiming a hard limit is exact.** It isn't, the interviewer knows it isn't, and the bound is a better answer than the claim.
8. **Metering requests instead of tokens.** A request is not a unit of cost — one request can cost 10,000× another. This is the same mistake the ChatGPT page's §10 makes about rate limits, for the same reason.
9. **Enforcing limits in the client SDK.** Trivially bypassed, and the bypass is profitable.
10. **Refunds and service credits that bypass the ledger.** A credit issued by an admin tool that writes directly to a balance is money created outside the audit trail.
11. **Forgetting that a cancelled or failed stream still cost money.** Tokens were generated. Decide the policy — we bill output tokens actually produced on a client-cancelled run, and bill nothing on a server-side 5xx — and put it in the docs before a customer discovers it.
12. **Reopening a closed period.** Late events and corrections land in the *next* period. One rule, applied to both, or accounting will never trust the system again.
13. **Treating tax as a formatting concern.** It's a jurisdiction, a rate, a rounding rule, and a filing obligation. Scoping it out is correct; discovering it at the end is not.
14. **A single global balance row.** The whale's row is 15k RMW/s and it will be the first thing that falls over.

**Performance traps**

15. **The hot Kafka partition** on the largest org — salt the key for the top N, and know that it costs you total ordering.
16. **An unbounded dedupe set.** Bound the window to the replay window and say why they're the same number.
17. **Per-event writes into the warehouse or the ledger.** Batch into the meter, aggregate into the money.
18. **A synchronous processor call anywhere near a request path.** It's a third party with a p99 you don't own.
19. **Closing all 2M invoices at 00:00 UTC on the 1st.** Stagger by `hash(org_id) % 28` and the invoicing tier needs no capacity plan at all.
20. **A slow webhook handler.** Doing the work inline makes the processor retry, and now you're racing yourself. Enqueue, return 200, process elsewhere.

**Interview-performance traps** → `00-interview-mechanics.md` §6. The one specific to this problem:

21. **Reaching for a distributed transaction between the meter and the money.** It's the instinct that correctness demands atomicity, and it's wrong here: the correct structure is at-least-once delivery plus an idempotent write plus reconciliation, and reaching for 2PC signals you've never had to operate the thing you're proposing.

---

## 14 · The five-minute skeleton (draw this cold)

1. **Inference gateway** → `POST /admit` (sync, ≤5ms, fails open) and a **usage event into a local outbox, in the same transaction as run completion.**
2. **Admission service** holds an **in-memory budget lease** per org; decrements locally; refills from Redis. Reserves the **worst case** at admission, settles the actual later.
3. **Redis Cluster** — `budget:{org}`, `resv:{run_id}` with TTL. A cache with a lease protocol, never a source of truth.
4. **Outbox pump → Kafka `usage.raw`**, keyed `org_id`, `acks=all`, 7-day retention.
5. **Rate & post workers** — stateful, dedupe on `run_id` (TTL = retention), price pinned by `occurred_at`, release the leftover reservation.
6. **ClickHouse** — rated usage, `ORDER BY (org_id, occurred_at)`. Dashboards, ≤60s behind.
7. **Hourly aggregation → the ledger.** Postgres + Citus sharded by `org_id`, append-only, hash-chained, `UNIQUE (source_type, source_id)`.
8. **Invoicing** at period close, staggered by `hash(org_id) % 28`; tiered discounts applied here, on aggregates.
9. **Payment processor** behind an explicit state machine. Derived idempotency key; **no transition fires on a 200**; order-independent webhook handler.
10. **Daily three-way reconciliation** — gateway request log ↔ ledger ↔ settlement report — with an exception queue that has an owner.

---

## 15 · Variants — what actually changes

**The axis that governs this family: when the cost of a unit becomes known relative to the moment you commit to it.** Everything else — the meter, the ledger, the processor, the reconciliation — is the same in all six rows. What changes is only how big that gap is, and every mechanism on this page exists to close it.

| Product | When cost is known | What changes |
|---|---|---|
| **Per-call API** — Twilio SMS, a paid webhook, most REST products | **Before**, and fixed | **§8 collapses to one `DECRBY`.** Reservations vanish, the overshoot bound is genuinely zero, and hard limits are exact. Everything else on this page survives unchanged — which is the cleanest proof that the LLM version's difficulty comes from *this one property* and nothing else |
| **Token-based LLM API** — this page | **After**, bounded only by `max_output_tokens` | Reserve-then-settle, adaptive leases, a stated overshoot bound |
| **Seat-based subscription** — ChatGPT Team, Slack, consumer Plus | At **period start**, changing on seat events | Metering becomes a `COUNT`, and **proration becomes the entire problem**: what a mid-cycle downgrade costs, whether a seat added on day 29 is billed. Same ledger, same processor, and §7–§9 shrink to nothing. Consumer ChatGPT Plus is the degenerate case — one line, one price, no meter |
| **Metered infrastructure** — EC2 hours, S3 GB-months | **Accrues continuously**, with no discrete event | The meter becomes a **sampler**, not an event stream, so a missed sample must be *interpolated* rather than replayed — and enforcement becomes "stop the resource," a control-plane action with its own latency and its own partial-failure story |
| **Prepaid consumable** — Twilio balance, cloud credits, this page's credit mode | After, and the **balance is the only enforcement point** | §10 mostly disappears — there's no invoice to collect, just top-ups. §8 gets *harder*, because there's no credit relationship to absorb the overshoot: every dollar of overshoot is a dollar you gave away |
| **Ad budget pacing** — Google Ads daily budgets | After, at enormous volume, and **the bound is contractual** | Structurally identical to this page's lease design, but overdelivery is *refunded* rather than billed — the bound is enforced by a compensating credit rather than by a block, which is what you do when refusing traffic is more expensive than the overshoot |

**The lesson:** every one of these has a meter, a ledger, a processor, and a reconciliation job, and if you've built one you can draw all six. The only question that reorganizes the design is **how long you have to wait to find out what you just agreed to pay for** — and when that answer is "no time at all," this stops being a systems problem.
