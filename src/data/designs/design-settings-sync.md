# Design IDE Settings Sync — Layered Config with Team Precedence

## The question

> *"Design settings sync for an IDE like VS Code. A developer's editor settings should follow them to any machine they sign into — and their company should be able to require some of those settings for everyone. Which value wins for a given setting has to be a rule you can state, not a consequence of which update happened to arrive last."*

**The product.** An editor has hundreds of settings: theme, font size, tab width, keybindings, format-on-save, which linter runs, which extensions are enabled. Today each install has its own copy, so a new laptop starts blank. This feature makes them follow the person — sign in and the editor is already yours.

The twist is that there is a **second owner**. A team or an organization can also set values, and some of those the individual is not allowed to override — a company that requires format-on-save means it, and the UI has to show that value as locked rather than pretending the developer chose it. So for a single setting like `editor.formatOnSave`, a product default, one or more team values, and the developer's own value can all exist at once, and something has to decide which one wins. Meanwhile developers work on planes and in tunnels, and the editor has to start regardless of whether any of this is reachable.

**What a working system delivers**

- A laptop you signed into an hour ago already has your theme, your keybindings, and your font size.
- Your organization's required settings are applied, and when you click one the UI can tell you it's locked and which team set it.
- An admin changes a policy and it reaches everyone's running editor within seconds — and reaches the person whose laptop was shut all week when they next open the lid.
- Editing a setting on two of your own machines doesn't silently lose one of the edits.
- The editor opens, correctly configured, with the service completely down.

**Why this gets asked.** It is presented as a synchronization problem and it isn't one. Nobody is editing the same document: you own your layer, the admin owns theirs. What everyone reflexively calls a "conflict" here is really a precedence rule that nobody ever wrote down — and whether a candidate writes it down before designing any transport is the whole test.

---

**Archetype:** layered configuration resolved by a deterministic function, distributed to clients that are offline more often than they are online.
**Cousins that reuse ~70% of this page:** VS Code and JetBrains settings sync, Chrome enterprise policy, MDM configuration profiles, Slack and Notion workspace preferences, feature-flag delivery, AWS AppConfig, Kubernetes ConfigMaps. Also **any product where an administrator's value and an individual's value can both exist for the same key** and something has to decide.

**What's actually being graded:** whether you write down the **effective-settings function** — a total order over named layers, evaluated per key — *before* you design any transport, and then treat the entire sync protocol as cache invalidation of that function. Candidates who design the WebSocket first end up with arrival-order semantics, which is precisely the failure the problem statement calls out. The second signal is that you notice **push is a hint, not a delivery mechanism**: the notification carries a version and nothing else, so duplicate, late, reordered, and dropped notifications collapse into one no-op. The third, and the one most people miss, is that **team membership is an input to the function**, so a user's effective settings change when no settings document changed anywhere.

**Contrast to have ready:** *Figma is many writers on one document, where convergence is the whole problem and the algorithm is the answer. This is the inverse: **nobody writes the same document**. A user owns their layer and an admin owns the team's, so there is no write conflict to converge — what everyone calls a "conflict" here is an **unstated precedence rule**, and it is resolved by policy at read time, not by a merge algorithm at write time. The only real write conflict is a user against their own second laptop, and one conditional update handles it.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "There are three separable products inside settings sync — the resolution rules, the storage and versioning, and the delivery — and they fail in completely different ways. I'd scope to **the effective-settings function plus the sync protocol that keeps clients honest about it**, and leave identity, team administration, and secret storage out. Two things dominate. First, **nobody actually writes the same document here.** A user owns their layer, an admin owns the team's. So what gets called a conflict is really a precedence rule nobody wrote down, and I want that rule as a **total order over named layers, evaluated per key** — including the two cases that break naive answers: a team value that's mandatory, and two teams that disagree. Second, **push is only a hint.** Delivery is at-least-once, clients sleep for days, notifications arrive twice and out of order — so the notification carries a version and nothing else, and the client has exactly one rule: *ignore anything not newer, and on any gap, read the authoritative state.* That one rule turns duplicate, late, and lost delivery into the same no-op. I'll go deep on the resolution function, and on what happens to a client that edited a setting offline while a team policy landed on that same key."

**Why open this way:** it refuses the framing the prompt is fishing with — "synchronization" — and replaces it with a pure function plus a cache. It also pre-commits the two dives that carry the round, and it says "precedence is a product decision" out loud before the interviewer gets to ask "what if two teams disagree," which is the question they are definitely going to ask.

---

## 1 · Functional requirements

1. **A client reads its effective settings** — a deterministic merge of product defaults, every team it belongs to, and its own overrides — and can tell **which layer produced each key**, so the UI can show a value as locked, inherited, or personal.
2. **Users and team admins write their own layer**, one key or many at a time, against a version they name. A write whose base has moved is rejected with the current state, never silently merged.
3. **A client that has been offline converges.** Missed, duplicated, delayed, and reordered notifications are all harmless; local edits made while offline are either committed or surfaced as a conflict, and never silently discarded or silently reapplied.

**Out of scope (say them):** identity and SSO, team administration itself (invites, roles, provisioning), the editor's own consumption of the resolved values, secret and credential storage, large binary assets like themes and extension bundles (§15), billing.

**Below the line, likely follow-ups:** rollback and audit UI, per-repository settings that live in the repo rather than the service (§15), machine-scoped settings that deliberately don't sync, schema evolution across client versions (§11), and multi-region.

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Editor start → settings applied** | **p99 < 300 ms**, served **from the local store** | Past that, the window paints with defaults and then visibly re-themes. A flash of the wrong theme on every launch is the user-visible failure mode of this entire system |
| **Availability of the read path** | **The IDE opens and is fully usable with the service 100 % down** | The client resolves locally from its last-known-good inputs. A config service that can stop an editor from starting is worse than no config service — this requirement is what makes the client a resolver rather than a viewer |
| Admin write → connected member converged | p50 < 2 s, p95 < 10 s | An admin pushes a policy and watches someone's machine. Past ~10 s they push it a second time, and you get the duplicate delivery you'd better have designed for |
| **Convergence with the push channel entirely dead** | **≤ 60 s for any online client** | The poll floor. **This is the number that lets push be best-effort** — everything the socket does is reduce 60 s to 2 s, not make convergence possible |
| Write conflict (`412`) rate | **< 0.1 % of writes** | Higher means a layer has more than one real writer — a scripted admin tool, or two clients in a merge retry loop (§13) |
| Durability | An acknowledged revision **survives loss of any single node and is never rewritten** | It is a `COMMIT` against an append-only table. Unacknowledged client edits stay the client's problem and replay (§6 Flow C) |
| Audit retention | **Every revision, with author and commit time, for 400 days** | Thirteen months covers an annual audit cycle plus the lag in running it. For contrast, VS Code's own sync store keeps only the **latest 20 versions per resource** — a sync product, not an audited one |
| Consistency | **Read-your-writes for the author; bounded staleness (≤ 60 s) for everyone else** | Deliberately not linearizable across the fleet. See the sentence below |
| Scale | 5 M daily active clients, 100 k teams, largest team **50 k seats** | §3 |

**The sentence that earns the point:** *"The invariant isn't that every machine holds the same value at the same instant — it's that **any two clients given the same input versions compute the same effective document**. That makes this a caching problem with a pure function in the middle, which is exactly why at-least-once delivery isn't something I tolerate here, it's something I want."*

---

## 3 · Numbers that reframe the problem

**The poll floor, not the write rate, sets the read load**

- *Assumption:* 5 M daily active clients, ~8 hours active each.
- A naive "poll every 60 seconds" for everyone is 5 M × 8 h × 60 = **2.4 B requests/day ≈ 28 k/sec of 'nothing changed'.**
- Poll every **60 s only while the socket is down**, every **15 min while it's up**, and with ~5 % disconnected at any moment that collapses to **~3.3 k/sec average, ~10 k/sec at the morning peak.**
- **Say this out loud:** *"the WebSocket isn't here to make convergence fast — it's here to buy the right to poll rarely."* That is a nearly 10× infrastructure difference from one line of client policy, and it reframes the socket from a latency feature into a cost feature.

**Writes are so rare that the whole write path fits on one box**

- *Assumption:* a developer changes a setting about once a week. 5 M ÷ 7 ≈ **714 k writes/day ≈ 8/sec**, peaking maybe 25/sec. Team writes — 100 k teams, roughly monthly — add **0.04/sec** and are noise.
- Read:write on the sync path is therefore **~400:1**, and the absolute write number is small enough to state plainly: **one Postgres primary handles every write this system will ever take.**
- **This figure exists to license the complexity budget.** Nothing here is hard because of throughput, so every hard thing on this page has to be justified by correctness or by fanout — and if you find yourself sharding the write path, you have solved the wrong problem.

**Documents are kilobytes, which is what makes immutable revisions free**

- A real `settings.json` is a few hundred keys at most: **1–5 KB**. Call it 4 KB.
- 714 k revisions/day × 4 KB ≈ **2.9 GB/day, ~1 TB/year** — storing a **full snapshot of every revision** and never computing a delta at all.
- **This kills the instinct to build a clever delta-only log.** Deltas are a *transport* optimization for slow clients (§8), not a storage one. A terabyte a year is a line item, not an architecture.

**Team fanout is the only place the numbers get large**

- *Assumption:* p99 team is 5 k members; the largest enterprise tenant is **50 k seats**.
- One admin write invalidates **50 k effective documents** and, if those clients are connected, produces 50 k socket writes and then 50 k fetches **inside the same second** — against a system whose steady-state write rate is 8/sec.
- **The entire shape of §10 comes from this number:** the hint must be small and version-stamped so nothing is fetched twice, the fetch must be jittered, and the fetched object must be immutable so it is a cache hit for 49,999 of them.

**Membership churn is tiny, and the tiny number is the trap**

- *Assumption:* 2 % monthly member churn on 5 M users = **100 k membership events/month ≈ 0.04/sec.**
- Every one of them changes the *inputs* to the resolution function while changing **no settings document anywhere.**
- **The point of this figure is its smallness.** A number this small never shows up on a dashboard, so if membership isn't part of the version a client compares, a re-org silently leaves the old team's policy in force until something unrelated happens to bump a version. Volume: negligible. Blast radius: a compliance incident. §11.

---

## 4 · Core entities

- **Principal** — a `user` or a `team`. One entity type covering both, because for storage and versioning purposes they are identical: a settings owner.
- **Revision** — `(entity_type, entity_id, version, parent_version, patch, snapshot, author_id, schema_version, committed_at)`. **Immutable.** Never updated, never deleted inside the retention window.
- **Current pointer** — `(entity_type, entity_id) → version`. The only mutable row in the system.
- **Membership** — `(user_id, team_id, role, rank)`, plus a **`membership_version` monotonic per user**.
- **Key descriptor** — `key`, type, product default, which layers may write it, **whether it may be made mandatory**, and the schema version it appeared in.
- **Effective document** — *not stored.* Derived, and identified by an **aggregate version** built from every input that fed it (§11).

**The four that are load-bearing:**

**The revision is immutable and the pointer is the only mutable thing.** Every other mechanism on this page is a statement about versions: the conditional write compares one, the notification carries one, the cache is keyed on one, the ETag is one, and rollback *creates* one. Rollback in particular is a **forward write** — a new revision whose content equals an old one — so history is append-only in the literal sense and the audit trail can never be edited by the feature that exists to fix mistakes.

**`rank` on the membership row is what makes multi-team deterministic.** Precedence between two teams cannot be derived from any property of the teams — not size, not creation date, not join date, all of which are arbitrary and all of which change. It has to be an **explicit ordered list**, and it belongs on the user's membership because that's the only place the full set is known. Without it, resolution falls back to whichever document was fetched last, which means **the same user gets different settings on two laptops** — the exact bug the requirements name.

**The key descriptor carries mandatory-*capability*; the team's revision carries mandatory-*ness*.** Whether `telemetry.enabled` is the kind of key an admin may lock is a **product** decision that ships with the client. Whether it *is* locked, right now, for this team, is an **admin** decision that lives in a revision. Collapsing these lets an admin lock a keybinding, and now the product has a support queue it can't drain.

**A deletion is a value, not an absence.** `{"editor.fontSize": {"op": "unset"}}` is a tombstone; a key simply missing from a patch means *unchanged*. This is what makes "reset this back to my team's default" expressible at all — without it, a user who has ever set a key can never un-set it, because the only way to remove it is indistinguishable from never having touched it.

---

## 5 · API

```text
GET  /v1/manifest
     → 200 { session: "e3f…", entities: { "user:123": 88, "team:7": 12,
                                          "membership:123": 45, "keyschema": 31 } }
     ~200 bytes. This is the request that runs every 15 minutes and almost always
     tells the client that nothing has changed.

GET  /v1/entity/{type}/{id}                  If-None-Match: "<version>"
     → 200 { version, doc }  |  304 Not Modified
GET  /v1/entity/{type}/{id}?since=<version>
     → 200 { from, to, patches[] }  |  409 TooOld → fetch the snapshot instead

PUT  /v1/entity/{type}/{id}                  If-Match: "<expected_version>"
     body { patch: { "editor.tabSize": 2, "editor.fontSize": {"op":"unset"} },
            schema_version: 31 }
     → 200 { version }
     → 412 { current_version, doc }          ← the current state, not just a refusal
     → 422 { rejected: [{key, reason}] }     ← validation, or a key this layer may not write

POST /v1/entity/{type}/{id}/rollback  { to_version } → 201 { version }   // a new revision
GET  /v1/entity/{type}/{id}/history?limit=50                              // the audit trail

GET  /v1/effective
     → 200 { doc, sources: { "editor.tabSize": {layer:"team", id:7, version:12,
                                                mandatory:true}, … },
             aggregate_version, resolver_version }
     ETag: "<aggregate_version>"             ← so a revalidation is a 304 and zero bytes

WS   /v1/subscribe   ← { entity: "team:7", version: 13, delay_ms: 4200 }   // a hint
```

**Decisions to narrate, unprompted:**

- **`/effective` returns the sources alongside the values.** Without them the client cannot render "managed by your team," cannot explain to a user why their edit did nothing, and — the real reason — cannot tell which single input to re-fetch when one of them changes. The resolved document alone is a dead end.
- **Every write is conditional, and a rejected write returns the current document.** `If-Match` against the entity's version; a stale writer gets **412 plus the state it needed**, so it can merge in one round trip instead of two. This is exactly what the real VS Code sync store does — it returns 412 with *"There is new data for this resource. Make the request again with latest data."*
- **The subscription carries a version, never a value.** The moment a push carries data, it becomes a second source of truth with strictly weaker guarantees than the store, and every delivery anomaly turns into a correctness bug instead of a no-op (§10).
- **`session` in the manifest is the cheapest field on this page.** If the server's session differs from the client's cached one, everything the client holds is void — account reset, cloud data cleared, restore from backup. One string turns "the entire world moved underneath you" from an undetectable disaster into a comparison. VS Code's sync manifest carries this for the same reason.
- **A key absent from a patch means unchanged; deletion is an explicit op.** The alternative — absent means delete — makes every partial update a destructive full replace, which is how a laptop that slept through Tuesday erases Tuesday.
- **`resolver_version` is returned because the client resolves locally.** Two client builds can compute different effective documents from identical inputs, and this field is what lets an old client detect that and defer to the server's answer (§7).

---

## 6 · High-level design — flows

```text
        ┌──────────────── client (IDE) ─────────────────┐
        │  local store: source docs + their versions    │
        │               pending patch (base_version)    │
        │  resolve()  ──►  effective document           │ ← works with the server down
        └───┬──────────────────▲──────────────────▲─────┘
            │ GET /manifest    │ 304, usually     │ { entity, version }  = a hint
            │ PUT If-Match     │                  │
            ▼                  │                  │
     ┌───────────────────────┐ │           ┌──────┴───────┐
     │    settings API       │─┘           │  WS gateway  │──► registry (Redis)
     │  CAS on the pointer   │             └──────▲───────┘
     └───────────┬───────────┘                    │
                 │ ONE transaction                │
                 ▼                                │
     ┌──────────────────────────┐  outbox  ┌──────┴─────────┐
     │ Postgres                 │─────────►│    fanout      │
     │   revision  (immutable)  │  → Kafka │  team→members  │
     │   current   (pointer)    │          └────────────────┘
     │   membership · outbox    │
     └──────────────────────────┘
```

### Flow A — a user changes a setting on one of their two laptops

1. The IDE applies the change **locally and immediately** and records `(base_version = 88, patch)` in its durable local store. Nothing waits on the network (§2).
2. `PUT /v1/entity/user/123` with `If-Match: 88` and the patch — the changed keys only.
3. Server, in one transaction: `UPDATE current SET version = 89 WHERE entity = … AND version = 88`; insert revision 89; insert an **outbox** row. `COMMIT` (§8).
4. `200 {version: 89}`. The client clears its pending patch.
5. The outbox drains to Kafka, keyed by entity; fanout looks up the user's other sessions and sends `{entity:"user:123", version:89}`. The authoring laptop receives it too, sees 89 ≤ 89, and **does nothing**. This is why duplicates are free.
6. **The failure path.** The second laptop woke with its own pending patch and PUTs `If-Match: 88`. It gets **412 with the document at 89**. The keys are disjoint, so it merges and retries with `If-Match: 89` (§9). If it were the *same* key with a different value, it raises the conflict UI instead. Either way, note the trap: an auto-merge-and-retry loop with no backoff between two machines that both keep editing is a **livelock**, and the bound is "retry twice, then ask the human."

### Flow B — an admin pushes a policy to 50,000 members

1. Admin `PUT /v1/entity/team/7` with `If-Match`, marking `security.telemetry` mandatory. Authorization is re-checked **inside the transaction**, against the admin's role at commit time (§11).
2. Same single transaction as Flow A: revision, pointer, outbox row.
3. The fanout service expands `team:7` into its member list, pages through it, and publishes `{entity:"team:7", version:13}` to each connected member's gateway. **It does not compute 50 k effective documents** — the members do that themselves, locally.
4. Each client compares 13 against its cached `team:7` version, fetches a delta of a few hundred bytes, re-runs `resolve()`, and applies. §7 decides whether the user's own conflicting value survives; it does not.
5. Offline members receive nothing and are correct anyway — they pick it up on their next manifest fetch (Flow C).
6. **The failure path — the herd.** All 50 k connected clients want to fetch inside the same second (§3). Four things absorb it, and they're worth naming in order: the hint carries the version, so nothing is fetched twice; fanout stamps a **`delay_ms` jitter window scaled to team size** into the hint, spreading the fetch over ~30 s; the entity fetch is **version-addressed and immutable**, so it is a CDN hit for everyone after the first; and the API sheds with **429 + `Retry-After`**, which is safe *precisely because* every one of those clients already has a working document and is merely revalidating. **Under total fanout failure, nobody's editor breaks and the policy still lands inside the 60-second poll floor.**

### Flow C — a laptop that slept through the weekend, with a local edit

1. Wake. `GET /v1/manifest`. Compare `session` — unchanged, so the cache is still meaningful.
2. Compare each entity: `user:123` unchanged at 88; `team:7` moved 12 → 19; **`membership:123` moved 45 → 46** because the user was added to `team:9` on Friday.
3. Fetch `team:7?since=12` (a delta), a full snapshot for the newly-relevant `team:9`, and the new membership. Re-run `resolve()`. **The effective document changed even though the user's own document did not, and even though nobody edited a setting on their behalf** — that is §11's whole argument in one step.
4. Submit the pending patch with `If-Match: 88`. Nobody else writes this user's layer, so it commits at 89.
5. **The failure path, and it is the interesting one.** The offline edit was `editor.formatOnSave: false`, and `team:7` v19 made that key **mandatory**. The write to the user's own layer **succeeds** — it's their layer, they own it, and rejecting it would mean the server deciding what a user may store rather than what a user may see. Resolution then **discards it**, every time, until the policy is lifted. The client must say *"your value is overridden by your team"* and keep it stored. **The layer is writable; the effect is not** — and shipping either half without the other is a bug report either way: reject the write and the value is lost the day the policy lifts; apply the value and the policy didn't work.

### Flow D — every push is lost forever

1. The WebSocket tier is fully down. Clients notice the socket is gone and switch their poll interval from 15 minutes to 60 seconds (§3).
2. Each poll is `GET /v1/manifest`, ~200 bytes, and answers "nothing changed."
3. When something *has* changed, the client takes exactly the path it takes in Flow C — because **there is only one recovery path and it is also the normal path.**
4. **The failure path is that there isn't one.** Convergence degrades from ~2 s to ≤ 60 s and nothing else in the system changes behaviour. **Say this sentence out loud in the interview** — it is the proof that push is a hint, and it is worth more than any description of the WebSocket tier.

---

## 7 · Deep dive — the effective-settings function, and why "team overrides user" is not an answer

**The naive answer.** "Team settings override user settings; product defaults underneath; if the user is in several teams, whichever we applied last wins."

**What breaks.** Three separate ways, and they are all visible to users.

- **It is not a total order.** Two teams both set `editor.tabSize`. Which one applies now depends on document fetch order, which depends on network timing, which means **the same user gets different settings on two laptops** and neither is wrong. This is the failure the problem statement is pointing at when it says precedence must not be left to arrival order.
- **It makes every team value mandatory.** Once an admin sets a font size as a suggestion, no user can change their font size. In practice admins then stop using team settings at all, and the feature that was supposed to enforce a security policy is disabled because it also enforced a font.
- **"Override" has no answer for removal.** If a team sets a key and a user wants their *personal* value gone so the team's applies again, "override" gives them no way to express it, and the absence of a key is already overloaded (§4).

**What replaces it.** A **total order over named layers, evaluated independently per key**, with the team layer appearing **twice** at different priorities:

```text
effective(k) = the first defined value in this order:

  1. MANDATORY team policy   — highest-ranked team that marks k mandatory
  2. user override           — the user's own layer
  3. team DEFAULT            — teams in the user's explicit rank order
  4. product default         — from the key descriptor

  a tombstone at any layer means "I define nothing here" and falls through
```

**The whole trick is that layer 1 and layer 3 are the same documents at different priorities**, separated by one boolean in the team's revision. That is not an invention — it is what VS Code actually documents: an eleven-level precedence chain running default → user → remote → workspace → workspace-folder, then the language-specific versions of each, and finally *"Policy settings — set by the system administrator, these values always override other setting values."* The administrator's layer sits at the top **and** the bottom of that chain; only the mandatory half outranks the individual.

### Multi-team, and rejecting the ambiguity instead of resolving it

Rank lives on the membership row (§4). But the honest answer for a product that hasn't decided the ordering yet is not to invent one — it is to **reject the ambiguous write at admin time**: *"team-9 already sets `editor.tabSize` for 14 of these members; choose which team wins for those users before this saves."* An error at write time, seen by one admin who has context, is enormously cheaper than a coin flip at read time seen by 14 people who don't. **Making ambiguity a validation failure rather than a resolution rule is the single highest-leverage decision on this page.**

### Object-valued keys merge; arrays and primitives replace

A primitive or an array in a higher layer replaces the lower one entirely; an object-valued key is **merged key-by-key across layers**, with the higher layer winning per sub-key. Again, this is VS Code's real rule, and the reason to state which one you're doing is that arrays are genuinely ambiguous — `["a","b"]` might be a set to union or a list whose order is meaningful, and you cannot tell from the type. Replacing is the choice that never surprises anyone.

**What it costs.**

- **The function ships to clients, so it is versioned like an API.** Clients must resolve locally to satisfy the offline requirement in §2, which means two client builds can compute different effective documents from identical inputs. The mitigations are real work: the server computes and serves the same function at `/effective`, the response carries `resolver_version`, and a client older than the server's declared minimum defers to the server's answer instead of its own. **This is the price of the offline requirement, and it never goes away.**
- **Mandatory keys need an allowlist, an admin UI that explains itself, and an audit trail.** "My editor won't let me change this" is a support ticket that costs more than the feature unless the client can name the team and the admin who did it — which is why §5 returns `sources`, not just values.
- **Ranked teams are a product surface you now own.** Somebody defines the order when a user joins their second team, and a re-org changes it. There is no technical default; there is only a decision you have made or a decision you have deferred to timing.

---

## 8 · Deep dive — immutable revisions and conditional writes, instead of a mutable document

**The naive answer.** One row per entity: `settings JSONB`, `updated_at`, and `UPDATE … SET settings = ?`. It is one table, it is fast, and it is what most of these systems ship first.

**What breaks.**

- **A partial update becomes a read-modify-write**, so two machines saving different keys 50 ms apart silently lose one. And this is not a rare race — it is the *normal* case, because a user with two laptops has both of them syncing within seconds of each other every Monday morning.
- **There is no audit and no rollback**, which the requirements demand outright, and bolting on an audit table written by the same transaction gives you two sources of truth that will disagree the first time someone writes a migration.
- **The sync protocol has nothing to point at.** "Has anything changed?" degrades to "send me the whole document and let me diff it" — that is §3's 3.3 k/sec at 4 KB a request instead of a 200-byte manifest answering 304.
- **`updated_at` is not a concurrency token.** Clock skew between two API nodes makes timestamp comparison a coin flip at exactly the moment it matters, and two writes inside the same millisecond are indistinguishable.

**What replaces it.** An append-only `revision` table plus a `current` pointer, written in **one transaction**, with the expected version compared *inside* it:

```sql
BEGIN;

-- The entire concurrency control mechanism is this WHERE clause.
UPDATE settings_current
   SET version = version + 1
 WHERE entity_type = $1 AND entity_id = $2
   AND version = $3                       -- If-Match / expected_version
RETURNING version;                        -- zero rows updated  ⇒  HTTP 412

INSERT INTO settings_revision
       (entity_type, entity_id, version, parent_version,
        patch, snapshot, author_id, schema_version, committed_at)
VALUES ($1, $2, $4, $3, $5, $6, $7, $8, now());

INSERT INTO outbox (topic, key, payload)
VALUES ('settings.changed', $2, jsonb_build_object('entity', …, 'version', $4));

COMMIT;
```

Three properties fall out of those fifteen lines and are worth narrating individually: **the version is monotonic per entity and needs no coordination beyond the row you are already locking**; **the outbox row is in the same transaction as the revision**, so "committed but never announced" is not a state the system can reach (§10); and **zero rows updated is the entire conflict path** — no advisory lock, no `SELECT … FOR UPDATE`, no retry loop on the server.

Reads then get cheap in a way that shapes the whole protocol: `since_version` is answered from the `patch` column when the gap is short, and from the nearest `snapshot` when it isn't. **Snapshot every 20th revision**, so any replay is bounded at 20 patches regardless of how long a client slept.

**What it costs.**

- **Unbounded history, and a compaction policy you have to defend.** 2.9 GB/day (§3) is cheap, but it is not free forever: revisions are retained in full for the 400-day audit window and intermediate patches are compacted beyond a **30-day delta horizon**, past which `since=` simply answers with a snapshot. A client older than that horizon does a full reload — the same trade Figma makes on its op log, for the same reason.
- **Rollback is a forward write, and history therefore never shrinks.** That is the point, and it is also a compliance hazard: a secret pasted into a settings value is now retained for 400 days across every replica and backup. Redaction has to exist as a **separate, privileged, audited path that rewrites revision bodies**, and pretending the append-only story has no exception is worse than naming the exception.
- **The pointer row is a hot row per entity.** At 8 writes/sec globally it is nothing; a scripted admin tool doing 100 writes/sec against `team:7` serialises on one row and starts returning 412s to itself. The fix is **batching at the client** — one write with 40 keys, not 40 writes — and it is worth saying that sharding the row is the wrong instinct, because per-entity ordering is the property the entire sync protocol rests on.

---

## 9 · Deep dive — offline edits, and why both obvious merge policies are wrong

**The naive answer.** Either: the client sends its whole local document on reconnect and the server takes it. Or: the server three-way merges everything automatically so the user never sees a conflict.

**What breaks.**

- **Whole-document upload reverts every key the client hasn't heard about.** A laptop that slept from Friday to Monday uploads Friday's document and erases a teammate's Tuesday change — or, worse, a *policy* change. It is silent, it is not detectable from the write path, and it is the single most common real bug in this class of system.
- **Automatic merge of everything produces a document nobody wrote.** The user set `workbench.colorTheme: dark` offline; the remote says `light`. An automatic winner is arbitrary from the user's point of view, and the first time it happens the user stops trusting sync entirely — which in an IDE means they turn it off, which means the team policy stops arriving too.

**What replaces it.** **The client stores `(base_version, patch)` — never a document.** On reconnect it submits both, and the server applies a stated four-case policy:

| Case | Policy | Why |
|---|---|---|
| Base is current | Commit | The common case by a wide margin |
| Base is stale, **key sets disjoint** | Auto-merge, retry with the new version | The merge is over key *names*, not values — there is nothing to be wrong about |
| Base is stale, **same key, same value** | **Not a conflict.** Commit | Compare values before you raise a dialog. Two machines converging on the same value is the system working |
| Base is stale, **same key, different value** | Surface it — per key, not per document | The only case a human can actually adjudicate |

This is what VS Code does in production: a diff editor with **Accept Local / Accept Remote / merge manually**, and on first sync from a second machine a **Merge / Replace Local / Merge Manually** prompt rather than a guess. The fourth row is the one people forget in interviews and the one that removes most of the dialogs in practice.

**What it costs.**

- **A conflict UI is a feature with a maintenance cost, and it blocks.** A resource with an unresolved conflict is not syncing. So resolve **per key**, letting the rest of the document keep flowing — otherwise one argument about a theme stops a security policy from landing.
- **The client needs a crash-safe local store**, which means the local store has a schema, which means the local store has migrations. The client is now a small database, and pretending otherwise is how you lose a pending patch on an upgrade.
- **Past the delta horizon there is no common ancestor**, so a three-way merge is impossible and every key is potentially a conflict. The honest degradation is to fall back to the Merge / Replace prompt — which is exactly why VS Code asks that question on first sync, when there is no shared history at all.

---

## 10 · Deep dive — push as an invalidation hint, and why not push the values

**The naive answer.** The WebSocket delivers `{key, value}` and the client applies it. Or, slightly better, it delivers the new document.

**What breaks.**

- **At-least-once plus reordering means state moves backwards.** v13 arrives, then a retry of v12 arrives through a different gateway, and the client silently downgrades to a value the admin already replaced. Nothing detects this and nothing recovers from it until an unrelated write bumps the version.
- **The push channel becomes a second source of truth with weaker guarantees than the store**, so the two drift, and there is no mechanism by which the client could notice.
- **The 50 k-member fanout (§3) now carries the payload 50 k times** instead of ~200 bytes, and it carries it through the tier with the least backpressure in the system.
- **The offline client needs an entirely different code path**, so you have built the recovery path twice and only one of them runs often enough to be trustworthy.

**What replaces it.** The hint is `{entity, version}` and nothing else, and the client rule is one line:

> **Ignore any notification whose version is not greater than what I hold. On any gap, or any reconnect, read the authoritative state.**

Duplicate: no-op. Reordered: no-op. Lost: covered by the poll floor. **Three delivery failures collapse into one code path, and that code path is the same one a cold start uses** — so it is exercised millions of times a day rather than only during incidents.

The delivery chain is the boring half: outbox row in the write transaction (§8) → CDC or a `FOR UPDATE SKIP LOCKED` poller → **Kafka keyed by entity**, which buys per-entity ordering for free → fanout service, which expands team entities into member lists → **WebSocket gateway**, with a `user_id → gateway` registry in Redis under a heartbeat TTL.

**What it costs.**

- **Every hint costs a round trip.** You send a notification and then serve a fetch, where one message could have carried both. That is only acceptable because writes are 8/sec (§3) — at Figma's presence volume it would be indefensible, which is a useful contrast to have ready when someone asks why this isn't event-carried-state-transfer.
- **You are running a connection registry, a fanout service, and a gateway tier for a system whose write rate would fit in a spreadsheet.** Justify it by latency, not volume, and be honest that **a 60-second poll with no WebSocket at all is a legitimate v1** — and is what this design should ship first, because every other component works identically underneath it.
- **The herd in Flow B is created by this design, not solved by it.** Push is what turns a diffuse 60-second convergence into 50 k simultaneous fetches, and the jitter, the immutability, and the 429 path all exist to pay that bill.

---

## 11 · Deep dive — everything the function reads is an input, and the version has to say so

**The naive answer.** The aggregate version is a hash of the contributing settings documents' versions. Use it as the ETag, use it as the cache key, invalidate on it. It looks complete because every *settings document* is in it.

**What breaks.** Three ways, each of which is a real incident and none of which touches a settings document.

1. **Membership.** A user moves from `team:7` to `team:9`. No revision is written anywhere. The aggregate version doesn't move, the ETag matches, the client gets a 304, and it keeps enforcing the **old team's security policy** — for hours or until an unrelated write happens to bump something. This is §3's 0.04/sec figure, and its smallness is exactly why nobody notices.
2. **The key schema.** Changing a product default changes every effective document in the fleet while changing no revision at all. Shipping a *new* key does the same. Neither is visible to a version built only from documents.
3. **The resolver.** Same inputs, two client builds, two different answers (§7's cost). The client's own cache is now keyed on something that doesn't identify what produced it.

**What replaces it.** The aggregate version is a **tuple of every input**, hashed for the ETag but returned component-wise so a client can tell *what* moved:

```text
aggregate_version = H( user_doc_v,
                       [ (team_id, team_doc_v) … in rank order ],
                       membership_v,
                       key_schema_v,
                       resolver_v )
```

**Membership is a settings document in every respect except that it holds no settings**: it has a monotonic per-user version, it appears in the manifest as `membership:123`, it is fetched with `since=`, and a change to it emits the same `{entity, version}` hint through the same outbox. Once you see it that way, the "what happens when a user changes teams while offline" question answers itself — nothing special happens, because it was never a special case.

Authorization rides the same structure. `/effective` is evaluated against the caller's membership **at the caller's current membership version**, and a write to `team:7` re-checks admin role **inside the write transaction** (§8) rather than at request admission — otherwise a just-demoted admin's in-flight request commits after their demotion did.

### Schema evolution, which is the same problem wearing a different hat

- **Additive only.** A new key ships with a product default, so a client that has never heard of it resolves exactly as before.
- **Clients ignore unknown keys**; the server **validates against the key descriptor** and returns `422` for values a client of that `schema_version` could not have produced. Forward compatibility on the client, strictness on the server — neither alone is sufficient.
- **Removal is two releases:** stop reading the key, ship, then stop writing it. And because tombstones exist (§4), "this key was removed" stays distinguishable from "this key was never set" throughout — which is what makes the second release safe to run against clients still on the first.
- **A default change is a `key_schema_v` bump**, which invalidates every effective document in the fleet, which is a 5 M-client herd. Roll it with the same jitter machinery as Flow B, and treat it as a deploy rather than a config edit.

**What it costs.**

- **The tuple grows with team count.** A user in 30 teams carries a 33-component version and a fat ETag. Cap memberships as a product limit, or hash and accept losing the component-wise "what moved" detail for heavy users — a trade worth making explicitly rather than discovering.
- **Membership churn now invalidates settings caches**, coupling two systems that were independent. A bad membership-service deploy is now a settings thundering herd, and that dependency belongs on the diagram.
- **Every input has to be remembered**, and there is no compiler enforcing it. The concrete mitigation: `resolve()` takes an explicit `Inputs` struct and `aggregate_version` is **derived from that struct**, so adding a field to the function's inputs without adding it to the version is a build failure rather than a silent staleness bug. This is the sort of thing worth saying out loud — it converts a discipline problem into a type problem, which is the only durable fix.

---

## 12 · Data model, sharding, and storage decisions

**Partition key: `(entity_type, entity_id)`.** Revisions, the current pointer, and the history for one entity co-locate, so the conditional write in §8 is a single-shard transaction and needs no coordination. At 8 writes/sec this is one Postgres primary; if it ever isn't, `entity_id` is the Citus distribution column and nothing about the write path changes.

**Membership is partitioned twice, and that is deliberate.** Resolution asks "which teams is this user in?" (by `user_id`); fanout asks "who is in this team?" (by `team_id`). The two access patterns disagree, so there is an inverted table keyed by `team_id` maintained in the same transaction. **Name it as a second copy you are choosing to pay for**, not as an index that happens to exist.

**The hot shard is the largest team's document, and it is deliberately not a database problem.** 50 k clients read `team:7` after every admin write — but they read an **immutable version-addressed object**, so it is a CDN concern. The row itself is written a handful of times a day. **The hot shard is real, and the design's response is to move it off the database rather than to shard it.**

| Component | Access pattern | Durability | Choice | The one sentence you'd say |
|---|---|---|---|---|
| **Revisions, current pointer, outbox** | Append + one CAS per write, 8/sec; read by version | **The system of record** | **Postgres**, `JSONB` patch and snapshot columns, `UPDATE … WHERE version = $expected`, outbox in the same transaction | *"The compare-and-set is one `WHERE` clause and the outbox is in the same transaction — that's the entire consistency story."* |
| **Version-addressed entity reads** | Read-mostly, 50 k concurrent after a team write, immutable per version | Derived from Postgres | **Fastly / CloudFront** in front of `/v1/entity/{type}/{id}?v=`, `Cache-Control: public, max-age=31536000, immutable` | *"A version is never rewritten, so it's infinitely cacheable and there's no invalidation story to get wrong."* |
| **Effective-document cache** | Read 3 k/sec, computed per user | **None** — recomputable | **Redis**, key `(user_id, aggregate_version)`, 10-minute TTL | *"Keyed on the version tuple, so it can't go stale — a changed input produces a different key rather than a stale hit."* |
| **Membership** | Read by `user_id` on resolve; read by `team_id` on fanout | Durable, transactional | **Postgres**, same cluster, plus a `team_id`-keyed inverted table written in the same transaction | *"Two access patterns that disagree, so I keep two copies and write them together rather than pretending one index serves both."* |
| **Key descriptors / schema** | Read on every resolve; changes on release cadence | Durable, versioned | **A build artifact shipped with the client**, plus a served copy at `/v1/keyschema/{version}` | *"It changes when we deploy, not at runtime, so it's a versioned file — and the served copy exists only for clients that can't upgrade yet."* |
| **Change stream** | Append 8/sec, fan out; 7-day retention | Replayable, not authoritative | **Kafka**, topic `settings.changed`, **key = entity id** | *"Partitioning by entity gives me per-entity ordering for free, which is the only ordering the client rule needs."* |
| **Outbox drain** | Poll a small table, delete on publish | Derived | **Debezium CDC**, or a poller with `FOR UPDATE SKIP LOCKED` | *"At 8 writes/sec a poller is plenty — CDC is the thing I'd move to long before I'd shard anything."* |
| **Connection registry** | `user_id → gateway`, written on connect, read on every fanout | **Ephemeral** — rebuilt from heartbeats | **Redis** with a heartbeat TTL of 30 s | *"Ephemeral by construction, so a dead gateway ages out instead of needing a reaper."* |
| **WebSocket gateways** | Hold sockets; per-subscription last-sent version | **None** | Stateless service behind a sticky L4 LB | *"They hold a socket and an integer, so any gateway can serve any user and a restart costs a reconnect."* |
| **Audit log** | Written once, queried rarely, retained 400 days | Durable, immutable | **The revision table itself**, exported nightly to **S3 as Parquet** | *"I'm not building a second audit system — an immutable revision with an author and a commit time already is one."* |
| **Client local store** | Every read; survives restart and offline | Durable **on the device** | **SQLite** holding each source document with its version, the pending patch, and the last resolved output | *"The client is the replica that has to work with the server gone, so it stores the inputs — not just the answer."* |

### The signals that tell you this is broken

Volume dashboards are useless here — 8 writes/sec looks identical whether the system works or not. Four signals are worth naming, and they are all about **what the client experienced**:

- **Gap-recovery rate** — the fraction of client fetches triggered by a version gap rather than by a hint. This is the only honest measure of push delivery, because it measures the outcome rather than the tier. Healthy is near zero; a step change means the fanout path is dropping without erroring.
- **Resolver disagreement** — clients report their locally computed `aggregate_version` on the next request; the server recomputes and compares. **Any mismatch is a correctness bug in the one component that has no other test in production** (§7, §11).
- **Stale-membership window** — commit-to-recompute latency for the affected user. This is a security metric, not a performance one, and it is the alarm that would have caught incident #1 in §11.
- **412 rate per entity** — a spike on a single entity is two writers fighting: a scripted admin tool, or the merge livelock in §6 Flow A.

Plus the unglamorous ones: outbox depth (the leading indicator for everything above), compaction lag against the 30-day horizon, and a **monthly restore drill** that rebuilds the revision table into staging and diffs a sample of effective documents against production — *a backup you have not restored is a hypothesis.*

---

## 13 · Traps — the ranked list

**Design traps**

1. **Designing the sync protocol before the resolution function.** Precedence then falls out of arrival order, which is the one thing the requirements explicitly forbid (§7).
2. **"Team overrides user" as the whole rule.** It isn't a total order, it makes every team value mandatory, and it can't express removal (§7).
3. **Resolving multi-team ambiguity at read time instead of rejecting it at write time.** One admin with context beats fourteen users without it (§7).
4. **Pushing values instead of versions.** Turns every delivery anomaly into a correctness bug, and makes the offline path a second implementation (§10).
5. **Whole-document upload on reconnect.** The silent erasure of everything the client slept through — the most common real bug here (§9).
6. **An aggregate version that omits membership.** A re-org that leaves the old policy in force, with no signal (§11).
7. **Treating an absent key as a delete.** Makes every partial update destructive; makes "reset to default" inexpressible (§4, §5).
8. **No tombstone.** A user who has ever set a key can never un-set it back to the team's value (§4).
9. **Timestamps as the concurrency token.** Clock skew decides your writes, and same-millisecond writes are indistinguishable (§8).
10. **Authorizing at request admission rather than at commit.** The demoted admin's in-flight write lands (§11).
11. **Rollback that mutates history.** The feature for fixing mistakes must not be able to edit the record of them (§4).
12. **Assuming the client is online.** The editor must open with the service down, which is what forces local resolution and everything it costs (§2, §7).

**Performance traps**

13. **Fanning out per-user effective documents.** One admin write becomes 50 k server-side recomputations instead of 50 k 200-byte hints (§6 Flow B).
14. **No jitter on the invalidation fetch.** You built the thundering herd and then handed it a starting pistol (§6 Flow B).
15. **Recomputing `/effective` per request** instead of caching on the version tuple, for a document that changes weekly (§12).
16. **Serving `/effective` without an ETag.** 3 k/sec × 4 KB of unchanged documents, when a 304 costs nothing (§3, §5).
17. **A fixed 60-second poll for every client, connected or not.** 28 k/sec instead of 3.3 k/sec, for zero latency benefit (§3).
18. **Replaying a global change stream on reconnect** rather than per-entity `since_version`. The fleet-wide log is enormous; any one entity's delta is a handful of rows (§3).
19. **Unbounded auto-retry on 412.** Two machines auto-merging at each other forever (§6 Flow A).

---

## 14 · The five-minute skeleton (draw this cold)

1. **The resolution function first, in the middle of the board**, before any box: four layers, mandatory team policy on top, product default at the bottom, user override in between. Say "evaluated per key."
2. Two tables: **`revision` (immutable)** and **`current` (pointer)**. Write `WHERE version = $expected` next to the pointer — that is the concurrency control, and it is the whole of it.
3. **Client box** holding source documents with their versions, a pending patch, and `resolve()`. Draw the arrow marked **"works with the server down."**
4. `GET /manifest` → `{session, entity → version}`. Label it *"~200 bytes, usually answers 304."*
5. `PUT` with **`If-Match`**, and — this is the arrow people forget — the **`412` return carrying the current document**.
6. **Outbox inside the write transaction** → Kafka keyed by entity → fanout → WebSocket gateway → client.
7. Label the socket arrow **`{entity, version}` — a hint, not a value**, and write the client rule beside it: *ignore ≤, fetch on gap.*
8. **Membership box** feeding `resolve()`, with **its own version**, and an arrow into the aggregate version.
9. **`aggregate_version` = tuple of every input**, used as both the ETag and the Redis cache key. Draw it once, point two arrows at it.
10. In the corner, the two sentences: *"delivery is a hint; versions are the truth"* and *"the layer is writable, the effect is not."*

---

## 15 · Variants — what actually changes

**The governing axis: how much authority the pushed layer holds over the local one.** Everything else follows — whether a merge algorithm is needed at all, whether offline editing is even coherent, and what the word "conflict" means.

| Product | Layers | Authority of the pushed layer | The delta from this page |
|---|---|---|---|
| **Personal-only sync** (VS Code, JetBrains, with no team) | default < user | **None** — there is no pushed layer | §7 vanishes entirely and the page becomes §8 plus §9. Worth stating first, because it isolates exactly what the team layer costs: a precedence policy, a mandatory flag, an admin UI, and membership as an input |
| **This page** (Cursor / VS Code with team policy) | default < team default < user < team mandatory | **Per-key**, chosen by a flag in the team's own revision | As written. The team layer appears twice at different priorities, and that is the design |
| **Device policy** (Chrome enterprise, MDM profiles, Cursor's allowed-team-ID enforcement) | device policy above everything | **Absolute**, and delivered out of band — registry, plist, MDM channel, not your API | The client is no longer the authority; the OS is. Local edits to a managed key are **rejected at the client**, so §9 disappears and §7 collapses to two layers. §11 grows instead: device identity becomes an input, and it can change without the user doing anything |
| **Feature flags** (LaunchDarkly, Statsig) | one layer of targeting rules | Total — **there is no user layer** | Conflict is impossible by construction: exactly one writer, no merge, no offline edit. But §10 is unchanged — a streaming connection carrying "your config changed," a poll fallback, and a version. **The delivery half of this page survives when the resolution half is deleted**, which is the clearest evidence they're separable |
| **Repository settings** (`.editorconfig`, `.vscode/settings.json`) | a layer that lives in the repo | Scoped by **directory depth**, and versioned by git | The sync problem disappears — git is the transport, and the merge policy is the one the team already argues about. Resolution becomes hierarchical (nearest ancestor wins) rather than layered, which is a genuinely different function with the same shape |
| **Admission control** (Kubernetes + OPA, policy-as-validation) | one layer, but it **rejects rather than overrides** | Absolute, expressed as a veto | The alternative to §7's top layer, and worth having ready: instead of silently winning at read time, the mandatory layer **refuses the write**. Cheaper (no resolution at read time, no `sources` in the response) and worse UX (the user must fix it themselves, and offline they can't) |
| **Collaborative document** (Figma) | none — one shared document | n/a | The inverse. Many writers on one object, so conflict becomes convergence and the conditional update becomes last-writer-wins per property. See the Figma page — the useful comparison is that **this page has no merge algorithm because it has no shared writer** |
