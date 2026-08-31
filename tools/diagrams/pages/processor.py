import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

a = Board(810, "Payment processor architecture, split horizontally by the settlement boundary. A top row: the merchant's server calling the API tier, the card vault, and — in its own right-hand column — the acquirer. Above the boundary, a synchronous tier holding the idempotency claim in DynamoDB, risk scoring, and authorization against the acquirer, which fails closed. At the centre, the double-entry ledger in Postgres and Citus, with a Redis balance cache beside it. Below the boundary, an outbox feeding Kafka, the acquirer's daily settlement file in S3 with Object Lock, and three consumers: webhook senders partitioned by endpoint, daily three-way reconciliation, and payouts.")
a.banner("The dashed line is the settlement boundary. Above it, permission. Below it, money that has actually moved.")
a.box(20, 100, 170, 60, "Merchant server", ["Idempotency-Key required"])
a.box(220, 100, 240, 60, "API tier", ["every money call claims a key first"])
a.box(500, 100, 190, 60, "Card vault", ["the only PAN in the system"])
a.box(790, 100, 190, 60, "Acquirer", ["a black box you call"])
a.arrow((190, 130), (220, 130))
a.arrow((460, 130), (500, 130))
a.arrow((340, 160), (340, 196))

a.group(20, 196, 740, 140, "SYNCHRONOUS — PERMISSION, NOT MONEY")
a.cyl(36, 228, 230, 64, "DynamoDB", ["(merchant_id, key) claim", "written BEFORE the money call"])
a.box(290, 228, 170, 64, "Risk", ["a terminal decline"])
a.box(484, 228, 260, 64, "Authorization", ["300–600 ms · FAILS CLOSED", "timeout → reversal advice"])
a.arrow((266, 260), (290, 260))
a.arrow((460, 260), (484, 260))
a.arrow((744, 260), (770, 260), (770, 180), (830, 180), (830, 160))
a.text(36, 322, "A unique violation on the claim is not an error — it is the answer: complete replays, in_flight returns 409, a hash mismatch always returns 409.", 'dg-s')
a.arrow((390, 336), (390, 396))

a.cyl(230, 396, 440, 76, "Ledger — Postgres + Citus", ["DR clearing / CR merchant:pending / CR fee_revenue", "double-entry, append-only, sharded by merchant_id"], cls='dg-good')
a.cyl(20, 396, 180, 76, "Redis", ["balance cache", "a SUM, never the payout"])
a.arrow((230, 434), (200, 434))
a.arrow((930, 160), (930, 528))
a.ctext(950, 350, "daily file", 'dg-lbl')

a.hdiv(500, 20, 980)
a.lane(20, 494, "THE SETTLEMENT BOUNDARY — AN AUTHORIZATION IS NOT MONEY")

a.queue(230, 528, 440, 56, "Kafka — outbox pump", ["keyed by object id · at-least-once"])
a.cyl(790, 528, 190, 56, "S3 Object Lock", ["the settlement file"])
a.arrow((560, 472), (560, 528))

a.group(20, 620, 960, 118, "ASYNCHRONOUS — MONEY ACTUALLY MOVING")
a.box(36, 652, 300, 64, "Webhook senders", ["partitioned by endpoint_id", "signed · 3-day backoff · circuit-broken"])
a.box(360, 652, 280, 64, "Reconciliation", ["ledger ↔ file ↔ bank, daily", "an exception queue with an owner"])
a.box(664, 652, 300, 64, "Payouts", ["available less reserve", "computed from the ledger, not the cache"])
a.arrow((450, 584), (450, 604), (186, 604), (186, 652))
a.arrow((930, 584), (930, 604), (500, 604), (500, 652))
a.text(20, 768, "Only a line in the settlement file moves a transfer from merchant:pending to merchant:available. There is no code path that sets SETTLED from an HTTP response.", 'dg-note')
a.text(20, 790, "Everything shards by merchant_id, which is why the payment row, the ledger transfer and the idempotency response commit in one local transaction — and why this page has no saga.", 'dg-s')

ARCH_CAP = ("Draw the dashed line first and label it: above it a card issuer is granting permission, below it "
            "banks are moving funds, and the two are days apart. The ledger spans both, and which account a "
            "transfer lands in — pending above, available below — is how it records which side of the line the "
            "money is on.")

b = Board(700, "The payment lifecycle as a sequence with its branches. Down the left: the API call, the idempotency claim, risk, authorization, and a single commit transaction. To the right of each, the ways it can end without money moving — a replayed response, a 409, a decline, a timeout that becomes a reversal advice rather than an approval. Below a divider, the money path: a transfer into pending, the settlement file moving it to available, and payout. A final band shows refunds, disputes and negative balances, each a new transfer rather than an edit.")
b.banner("Every branch above the divider ends without money moving. Below it, money moves — and only a file says so.")
b.box(30, 68, 330, 56, "POST /v1/payment_intents", ["Idempotency-Key required, or 400"], cls='dg-good', tcls='dg-good-t')
b.box(430, 68, 540, 56, "the key already exists — two answers, never one",
      ["complete  →  replay the stored response byte for byte",
       "in_flight  →  409 · a different request hash  →  409"])
b.arrow((360, 96), (430, 96))
b.box(30, 144, 330, 56, "claim the key", ["INSERT, and let the unique index decide"])
b.box(430, 144, 540, 56, "the claim carries a lease", ["without one, a crash wedges that key forever"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((195, 124), (195, 144))
b.arrow((360, 172), (430, 172))
b.box(30, 220, 330, 40, "risk")
b.arrow((195, 200), (195, 220))
b.box(30, 284, 330, 56, "authorize at the acquirer", ["nothing is booked to the ledger yet"])
b.box(430, 284, 540, 56, "the two failures, and they are not the same",
      ["decline  →  terminal, no transfer, no retry",
       "timeout  →  reversal advice, REQUIRES_ACTION, never approved"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((195, 260), (195, 284))
b.arrow((360, 312), (430, 312))
b.box(30, 360, 940, 56, "COMMIT — intent + authorization + LEDGER TRANSFER + idempotency response + outbox row",
      ["one local transaction, because everything shards by merchant_id"], cls='dg-good', tcls='dg-good-t')
b.arrow((195, 340), (195, 360))

b.hdiv(440, 20, 980)
b.lane(20, 434, "BELOW HERE, MONEY MOVES")
b.arrow((280, 416), (280, 464))
b.box(30, 464, 300, 56, "transfer → merchant:pending", ["visible, and not payable"])
b.box(360, 464, 300, 56, "the settlement file, T+1/T+2", ["pending → available"], cls='dg-good', tcls='dg-good-t')
b.box(690, 464, 280, 56, "payout, less reserve", ["computed from the ledger"])
b.arrow((330, 492), (360, 492))
b.arrow((660, 492), (690, 492))

b.lane(30, 548, "MONEY GOING BACK — EACH ONE A NEW TRANSFER, NEVER AN EDIT")
b.box(30, 562, 300, 56, "refund, weeks later", ["a reversing transfer"])
b.box(360, 562, 300, 56, "dispute opens", ["debit available immediately"], cls='dg-warn', tcls='dg-warn-t')
b.box(690, 562, 280, 56, "the balance goes negative", ["legal — the payout stalls"], cls='dg-warn', tcls='dg-warn-t')
b.text(30, 654, "Every transfer sums to zero, so the whole ledger sums to zero. That query, run continuously, is the cheapest bug detector in the system.", 'dg-s')
b.text(30, 676, "Nothing here is ever an UPDATE. A refund, a won dispute, a failed payout — each is new entries, and the originals stay exactly as they were.", 'dg-note')

HLD_CAP = ("The three boxes across the top are the whole of §7: a claim written before the side effect, and a "
           "unique violation treated as an answer rather than an error. The divider is §9 — an authorization "
           "is not money, a capture is not money, and only a line in a file moves anything to available.")

s = Board(600, "Payment processor five-minute skeleton. Rows for the mandatory idempotency key and the claim, the vault, authorization that fails closed, the single commit transaction spanning the full width, the double-entry ledger, the pending-to-available settlement step, the webhook senders and payouts, and reconciliation. A margin band below carries the balance-is-a-query line, the float figure and the dispute window.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 460, 56, "Idempotency-Key required on every money call", ["a missing key is a 400"], badge=1)
s.box(510, 68, 450, 56, "Claim first — INSERT (merchant_id, key, hash)", ["unique violation IS the answer · lease it"], badge=2)
s.box(30, 144, 460, 56, "Vault", ["the only PAN. This is why merchants get SAQ-A"], badge=3)
s.box(510, 144, 450, 56, "Authorize at the acquirer", ["FAILS CLOSED · timeout → reversal advice"], cls='dg-warn', tcls='dg-warn-t', badge=4)
s.box(30, 220, 930, 56, "COMMIT: intent + authorization + LEDGER TRANSFER + idempotency response + OUTBOX ROW", ["one local transaction — everything shards by merchant_id, so there is no saga"], cls='dg-good', badge=5)
s.box(30, 296, 930, 56, "The ledger — DR clearing / CR merchant:pending / CR fee_revenue, summing to zero", ["append-only · UNIQUE (source_type, source_id) · a balance is a query over this"], cls='dg-good', badge=6)
s.box(30, 372, 460, 56, "pending, NOT available", ["an authorization is not money"], badge=7)
s.box(510, 372, 450, 56, "Settlement file T+1/T+2 → available", ["and book estimated-vs-actual fee drift"], badge=8)
s.box(30, 448, 460, 56, "Webhooks partitioned by endpoint_id", ["signed · 3-day backoff · GET /v1/events backstop"], badge=9)
s.box(510, 448, 450, 56, "Payouts from available less reserve", ["reversing transfers · daily 3-way reconcile"], badge=10)
s.lane(30, 526, "IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 538, 300, 44, "A balance is a query", ["not a column. That is the answer"])
s.box(350, 538, 300, 44, "~$5.5B of float", ["why payouts have a lag"])
s.box(670, 538, 290, 44, "Disputes reach back 540 days", ["which is what reserves are for"])

SKEL_CAP = ("Badges 5 and 6 are the page. One local transaction, and a ledger that only ever grows — draw those "
            "two and the rest is consequence. Badge 7 is the one candidates skip: the money is visible and it "
            "is not payable, and saying why is the difference between a diagram and a design.")

PAGE = 'design-payment-processor.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
