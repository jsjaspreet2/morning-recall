import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

b=Board(712,"Billing high-level design, split down the middle. A header band: API request, inference gateway which admits synchronously and writes a usage event to a local outbox in the run's transaction, and the GPU pool. Left column, synchronous and approximate: admission service holding in-process leases, Redis holding budgets and reservations, and a spend-limit rejection whose overshoot is bounded. Right column, asynchronous and exact: Kafka usage.raw, rate-and-post workers that dedupe on run id, and ClickHouse. One arrow crosses the divide, carrying the materialised balance back to Redis. Both halves meet at an append-only ledger in Postgres, below which sit reconciliation, invoicing and the payment processor.")
b.banner("The vertical split is the consistency split. Left: sync, approximate, fails open. Right: async, exact, loses nothing.")
b.box(30,90,140,60,"API request")
b.box(200,90,420,60,"Inference Gateway",["admit sync ≤5 ms · usage → local outbox in the run's txn"])
b.box(650,90,310,60,"model / GPU pool",["the ChatGPT page"])
b.arrow((170,120),(200,120)); b.arrow((620,120),(650,120))
b.lane(30,186,"① SYNCHRONOUS — APPROXIMATE, FAILS OPEN")
b.lane(640,186,"② ASYNCHRONOUS — EXACT, LOSES NOTHING")
b.vdiv(505,196,275); b.vdiv(505,340,560)
b.arrow((400,150),(400,200))
b.box(30,200,420,56,"Admission Service",["in-process leases · worst-case reservation"])
b.arrow((240,256),(240,290),label="lease / refill",lx=255,ly=278,lcls='dg-lbl')
b.box(30,290,420,72,"Redis Cluster",["budget:{org} · resv:{run_id} with TTL","a cache with a lease protocol, never truth"])
b.arrow((240,362),(240,396))
b.box(30,396,420,56,"429 spend_limit_exceeded",["overshoot is bounded, not zero — the lease shrinks near the limit"],cls='dg-warn',tcls='dg-warn-t')
b.arrow((580,150),(580,200))
b.box(540,200,420,56,"Kafka usage.raw",["key = org_id · acks=all · 7-day retention"])
b.arrow((750,256),(750,290))
b.box(540,290,420,72,"Rate & post workers",["dedupe on run_id · price pinned by occurred_at","release the leftover reservation"])
b.arrow((750,362),(750,396))
b.box(540,396,420,56,"ClickHouse — rated usage",["~1 B rows/day · dashboards ≤60 s behind"])
b.arrow((540,326),(450,326)); b.ctext(495,282,"materialised balance",'dg-lbl')
b.arrow((750,452),(750,486),label="hourly aggregate per org",lx=765,ly=474,lcls='dg-lbl')
b.box(280,486,440,76,"Ledger — Postgres + Citus",["~55 entries/s · append-only · hash-chained","UNIQUE (source_type, source_id)","the only component both halves touch"],cls='dg-good')
b.line((500,562),(500,580)); b.line((175,580),(500,580))
b.arrow((175,580),(175,598)); b.arrow((500,580),(500,598))
b.box(30,598,290,64,"Reconciliation",["gateway log ↔ ledger ↔ settlement","an exception queue with an owner"])
b.box(360,598,280,64,"Invoicing",["period close, staggered by hash(org) % 28"])
b.box(680,598,280,64,"Payment processor",["explicit state machine · derived key"])
b.arrow((640,630),(680,630),label="charge",lx=660,ly=622,lcls='dg-lbl dg-c')
b.text(30,692,"No transition fires on a bare 200 OK. An invoice moves to PAID on a webhook or a reconciliation query, never on the HTTP response to the charge call.",'dg-note')
HLD_CAP = "Draw the vertical line before you draw a box. Left of it nothing may block a request and everything is allowed to be approximate; right of it nothing may lose a write. The ledger is the only component that belongs to both halves, and that is the whole argument."

s=Board(470,"Billing five-minute skeleton. Paired rows across the sync/async split: gateway and admission service, Redis and the outbox pump to Kafka, rate-and-post workers and ClickHouse, then the hourly ledger aggregation spanning both, and finally invoicing, the payment processor and daily reconciliation.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(30,68,460,64,"Inference gateway",["POST /admit — sync, ≤5 ms, fails open","usage event → local outbox, same txn"],badge=1)
s.box(510,68,450,64,"Admission service",["in-memory lease per org, refilled from Redis","reserve worst case, settle the actual later"],badge=2)
s.box(30,152,460,56,"Redis Cluster",["budget:{org} · resv:{run_id} TTL — never a source of truth"],badge=3)
s.box(510,152,450,56,"Outbox pump → Kafka usage.raw",["key org_id · acks=all · 7-day retention"],badge=4)
s.box(30,228,460,56,"Rate & post workers",["dedupe on run_id · price pinned by occurred_at"],badge=5)
s.box(510,228,450,56,"ClickHouse — rated usage",["ORDER BY (org_id, occurred_at) · ≤60 s behind"],badge=6)
s.box(30,304,930,64,"Hourly aggregation → the ledger",["Postgres + Citus sharded by org_id · append-only · hash-chained","UNIQUE (source_type, source_id) — re-running the window is a no-op"],cls='dg-good',badge=7)
s.box(30,388,290,56,"Invoicing at period close",["staggered by hash(org_id) % 28"],badge=8)
s.box(350,388,290,56,"Payment processor",["no transition fires on a 200"],badge=9)
s.box(670,388,290,56,"Daily 3-way reconciliation",["an exception queue with an owner"],badge=10)
SKEL_CAP = "The left column never blocks and the right column never loses. Badge 7 is where they join — say “money moves once an hour, the meter moves twelve thousand times a second” as you draw it."

a = Board(790, "Billing architecture, split by consistency. A request row: API request, inference gateway writing a usage event to a local outbox in the run's transaction, and the GPU pool. On the left, a synchronous tier that fails open: admission service holding in-process leases against a Redis cluster, and the spend-limit rejection. On the right, an asynchronous tier that loses nothing: Kafka usage.raw, rate-and-post workers, ClickHouse. Both meet at an append-only ledger in Postgres and Citus, feeding invoicing, the payment processor, reconciliation and an S3 audit store.")
a.banner("The vertical split is the consistency split: left of it nothing may block a request, right of it nothing may lose a write.")
a.box(20, 118, 140, 64, "API request")
a.box(190, 118, 200, 64, "Inference Gateway", ["outbox in the run's txn"])
a.box(420, 118, 180, 64, "model / GPU pool")
a.arrow((160, 150), (190, 150)); a.arrow((390, 150), (420, 150))
a.group(190, 220, 420, 200, "① SYNCHRONOUS — APPROXIMATE, FAILS OPEN")
a.box(206, 252, 180, 64, "Admission Service", ["in-process leases"])
a.cyl(410, 252, 184, 64, "Redis Cluster", ["budget:{org} · resv:{run}"])
a.arrow((386, 284), (410, 284))
a.box(206, 340, 388, 60, "429 spend_limit_exceeded", ["overshoot is bounded, not zero"],
      cls='dg-warn', tcls='dg-warn-t')
a.arrow((190, 150), (178, 150), (178, 284), (206, 284))
a.group(650, 220, 330, 290, "② ASYNCHRONOUS — EXACT, LOSES NOTHING")
a.queue(666, 252, 298, 56, "Kafka usage.raw", ["key org_id · acks=all"])
a.box(666, 332, 298, 64, "Rate & post workers", ["dedupe on run_id", "price by occurred_at"])
a.cyl(666, 420, 298, 56, "ClickHouse", ["ORDER BY (org_id, occurred_at)"])
a.arrow((815, 308), (815, 332)); a.arrow((815, 396), (815, 420))
a.arrow((340, 182), (340, 200), (815, 200), (815, 252))
a.ctext(577, 192, "outbox pump", 'dg-lbl')
a.arrow((666, 360), (630, 360), (630, 300), (594, 300))
a.text(672, 318, "materialised balance", 'dg-lbl')
a.cyl(190, 560, 420, 64, "Ledger — Postgres + Citus", ["append-only · hash-chained · by org_id"])
a.arrow((815, 476), (815, 530), (400, 530), (400, 560))
a.text(430, 522, "hourly aggregate per org", 'dg-lbl')
a.box(650, 560, 150, 64, "Invoicing")
a.box(830, 560, 150, 64, "PSP")
a.arrow((610, 592), (650, 592)); a.arrow((800, 592), (830, 592))
a.box(190, 660, 280, 64, "Reconciliation", ["gateway ↔ ledger ↔ settlement"])
a.cyl(500, 660, 220, 64, "S3 Object Lock", ["audit chain heads"])
a.arrow((330, 624), (330, 660)); a.arrow((560, 624), (560, 660))
a.text(20, 760, "Nothing on the request path writes to a database. The first durable, ordered, money-shaped write happens in a worker nobody is waiting on.", 'dg-note')

ARCH_CAP = ("Draw the two dashed boxes before anything inside them. Left of the split nothing may block a "
            "request and everything is allowed to be approximate; right of it nothing may lose a write. "
            "The ledger is the only component that belongs to both halves.")

PAGE = 'design-billing.md'
place(PAGE, 'architecture', a, ARCH_CAP, after_heading='## 6 ')
place(PAGE, 'flows', b, HLD_CAP)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
