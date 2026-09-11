import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# ---------------------------------------------------------------- architecture
a = Board(640, "Distributed rate limiter architecture. A region: API gateways holding the rule set in memory, local token leases, a fallback bucket and a per-shard circuit breaker; a Redis Cluster of twenty to forty shards running one Lua script per check; a control plane of Postgres rules pushed through a compacted Kafka config stream, with shadow mode; a sampled decision log flowing to ClickHouse for usage rollups and dashboards. A second region mirrors it, exchanging per-tenant counts every second over a replicated stream and receiving share parameters from a reconciler. A home-region lane serves the exact-quota exception across regions.")
a.banner("Allows come from a lease, rejects are confirmed at the store, and the global limit is approximate by a stated bound.")

a.group(20, 86, 460, 250, "REGION A — THE REQUEST PATH")
a.box(36, 118, 200, 96, "API gateways ×200",
      ["rule set in memory · ~50 k rules", "local leases · fallback bucket", "circuit breaker per shard"])
a.cyl(276, 118, 188, 96, "Redis Cluster", ["20–40 shards · one Lua script", "one key per rule–subject", "TIME from shard · TTL 2×window"])
a.arrow((236, 150), (276, 150)); a.ctext(256, 142, "lease", 'dg-lbl')
a.arrow((276, 190), (236, 190)); a.ctext(256, 206, "reject?", 'dg-lbl')
a.box(36, 240, 428, 76, "refill on read → consume cost → allow, or 429 + which rule",
      ["3.5 M ops/s → ~35 k with leases · p99 < 5 ms · no scan, no second hop"],
      cls='dg-good', tcls='dg-good-t')
a.arrow((136, 214), (136, 240))

a.group(510, 86, 470, 250, "CONTROL PLANE")
a.cyl(526, 118, 200, 64, "Postgres rules", ["versioned · If-Match · audit"])
a.queue(760, 118, 204, 64, "Kafka config", ["compacted · {rule, version}", "cross-region"])
a.arrow((726, 150), (760, 150))
a.box(526, 206, 200, 56, "shadow → enforce", ["would-be 429 rate first"], cls='dg-warn', tcls='dg-warn-t')
a.box(760, 206, 204, 56, "Reconciler", ["shares from observed traffic"])
a.arrow((826, 262), (826, 290), (500, 290), (500, 166), (480, 166))
a.text(560, 284, "rule + share push, p99 < 10 s", 'dg-lbl')
a.arrow((626, 182), (626, 206))

a.queue(36, 380, 240, 56, "Kafka decisions", ["1 % allows · 100 % rejects"])
a.arrow((136, 316), (136, 380))
a.cyl(316, 380, 240, 56, "ClickHouse", ["usage rollups · overshoot", "why was I 429'd"])
a.arrow((276, 408), (316, 408))
a.box(596, 380, 180, 56, "Dashboard", ["never reads Redis"])
a.arrow((556, 408), (596, 408))
a.arrow((436, 380), (436, 350), (862, 350), (862, 262))
a.text(560, 344, "per-tenant traffic → shares", 'dg-lbl')

a.group(20, 466, 960, 110, "REGION B — THE SAME, PLUS THE GOSSIP AND THE EXCEPTION")
a.box(36, 498, 300, 64, "Gateways + Redis, region B", ["enforces limit × share_B"])
a.queue(370, 498, 280, 64, "Counts, every 1 s", ["G-counter per (tenant, window)", "merge by max per region"])
a.arrow((336, 530), (370, 530)); a.arrow((370, 546), (336, 546))
a.text(390, 574, "partition → shares still sum to the limit", 'dg-lbl')
a.box(690, 498, 274, 64, "Home-region exception", ["exact quotas · +80 ms · small lease"],
      cls='dg-warn', tcls='dg-warn-t')
a.arrow((827, 498), (827, 456), (472, 456), (472, 200), (464, 200))
a.text(600, 449, "billing-grade tenants only, +80 ms", 'dg-lbl')

a.text(20, 608, "Nothing in Redis is a source of truth: a lost shard is a refill's worth of generosity. The rules and the decision log are the durable data, and neither is on the hot path.", 'dg-s')
a.text(20, 630, "Approximate by design, bounded by the lease, exact for the tenants who pay for it.", 'dg-note')

ARCH_CAP = ("Draw the arithmetic before the gateway box — three and a half million counter operations a second "
            "is what forbids the service-in-front-of-the-store and the global counter. Then draw the two arrows "
            "between gateway and store and label them differently: the lease is how allows stay fast, the "
            "confirm is how rejects stay exact.")

# ---------------------------------------------------------------- flows
b = Board(600, "Rate limiter check path in three lanes. Gateway: resolve rules from memory, check the local lease, spend from it on a hit, else run the Lua script on the store with a lease size that shrinks near the limit; a reject is confirmed at the store, never from the lease. Store failure: per-shard circuit breaker, fallback bucket at a conservative fraction for fail-open rules, 503 for fail-closed. Multi-region: local shares that sum to the limit, per-second count gossip that tightens, and a two-second over-rejection during a traffic shift.")
b.banner("Allows come from the lease, rejects are confirmed at the store, and a missing store is a smaller local bucket.")

b.lane(30, 76, "THE CHECK — ONE RULE, ONE KEY, ONE SHARD")
b.box(30, 90, 210, 72, "Resolve rules", ["3–4 per request", "from memory, microseconds"])
b.box(270, 90, 210, 72, "lease has tokens?", ["(rule, subject) in process", "expires in seconds"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((240, 126), (270, 126))
b.box(510, 90, 210, 72, "spend locally", ["no store call", "the common case"], cls='dg-good', tcls='dg-good-t')
b.arrow((480, 126), (510, 126)); b.ctext(495, 118, "yes", 'dg-lbl')
b.box(750, 90, 230, 72, "Lua script on the shard", ["refill on read · lease n", "n shrinks near the limit → 1"])
b.arrow((375, 162), (375, 176), (865, 176), (865, 162)); b.ctext(620, 172, "no — one round trip, ~1 ms", 'dg-lbl')
b.hdiv(196, 20, 980)

b.lane(30, 230, "THE ANSWER — AND THE STORE'S ABSENCE")
b.box(30, 244, 290, 64, "would reject locally?", ["confirm at the store first"], cls='dg-warn', tcls='dg-warn-t')
b.box(350, 244, 290, 64, "429 · Retry-After · which rule", ["RateLimit-Limit / Remaining / Reset"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((320, 276), (350, 276)); b.ctext(335, 268, "yes", 'dg-lbl')
b.box(670, 244, 290, 64, "allow · headers · 1 % sampled", ["100 % of rejects logged"], cls='dg-good', tcls='dg-good-t')
b.box(30, 330, 290, 72, "shard timeout at 5 ms", ["circuit breaker per shard, 1 s", "no retry on the hot path"], cls='dg-warn', tcls='dg-warn-t')
b.box(350, 330, 290, 72, "fail_policy: open", ["local bucket at limit / gateways × 2", "region over-admits ≤ 2× on those keys"])
b.arrow((320, 366), (350, 366))
b.box(670, 330, 290, 72, "fail_policy: closed", ["503, not 429 — money and safety rules", "named per rule, default open"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((640, 366), (670, 366))
b.hdiv(424, 20, 980)

b.lane(30, 458, "MULTI-REGION — LOCAL SHARES, THEN GOSSIP")
b.box(30, 472, 290, 64, "each region: limit × share", ["shares sum to the limit — the safety property"], cls='dg-good', tcls='dg-good-t')
b.box(350, 472, 290, 64, "counts gossiped every 1 s", ["over the global limit → tighten next second"])
b.arrow((320, 504), (350, 504))
b.box(670, 472, 290, 64, "traffic shifts", ["≤ 2 s of over-rejection, then re-split"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((640, 504), (670, 504))
b.text(30, 570, "The multi-rule race — two rules allow, the third rejects — costs one token on two buckets. Bound it, say it, and do not refund it on the hot path.", 'dg-note')

HLD_CAP = ("The middle lane is where the design earns its availability: a store timeout is a smaller local bucket, "
           "not an unlimited one, and the rules whose limit is money say so themselves. The bottom lane's first "
           "box is the multi-region safety property; the gossip is only the tightening.")

# ---------------------------------------------------------------- skeleton
s = Board(450, "Rate limiter five-minute skeleton. The arithmetic across the top; then the gateway with its leases, the Redis cluster with one script per key, and the bucket formula; then the lease bound, the control plane with shadow mode, and the decision log; then multi-region shares plus gossip and the 429 contract; and a margin lane of the signals and the sentence about approximation.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 930, 44, "1 M req/s × ~3.5 rules = 3.5 M counter ops/s · p99 5 ms — no scan, no second hop, not one node",
      cls='dg-good', tcls='dg-good-t', badge=1)
s.box(30, 128, 300, 64, "Gateway", ["rules in memory · local leases · fallback bucket", "the fast path allows; rejects are confirmed"], badge=2)
s.box(350, 128, 300, 64, "Redis Cluster", ["one Lua script, one key per rule–subject", "refill on read · TIME from the shard · TTL"], badge=3)
s.box(670, 128, 290, 64, "tokens = min(burst, t + Δt·rate)", ["consume cost · fixed window admits 2×"], badge=4)
s.box(30, 208, 300, 56, "Lease bound", ["≤ gateways × lease · shrinks to 1 near the limit"], badge=5)
s.box(350, 208, 300, 56, "Control plane", ["Postgres rules → config stream · shadow → enforce"], badge=6)
s.box(670, 208, 290, 56, "Decision log", ["1 % allows, 100 % rejects → ClickHouse → usage"], badge=7)
s.box(30, 284, 460, 56, "Multi-region", ["local shares that sum to the limit + 1 s gossip · home-region exception at +80 ms"], badge=8)
s.box(510, 284, 450, 56, "The 429", ["Retry-After · RateLimit-* · which rule"], badge=9)
s.lane(30, 370, "IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 382, 220, 44, "measured overshoot", ["admitted ÷ limit, per rule"], badge=10)
s.box(270, 382, 220, 44, "store p99 · fallback_active", ["per shard"])
s.box(510, 382, 220, 44, "top leased subjects", ["the whale list"])
s.box(750, 382, 210, 44, "approximate by design", ["bounded · exact for who pays"])

SKEL_CAP = ("Badge 1 is a line of arithmetic and it forbids two designs before they are drawn. Badge 5 is the "
            "sentence the multi-region follow-up is fishing for — say it unprompted. Badge 4 is the one formula "
            "on the board, and the loser beside it is the tutorial answer.")

PAGE = 'design-rate-limiter.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
