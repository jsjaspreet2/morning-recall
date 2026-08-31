import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

a = Board(800, "Amazon checkout architecture, split horizontally by reversibility. A client tier with the cart and the checkout session. Above the dashed commit line, a synchronous tier: the order service calling inventory for a conditional reserve against available-to-promise in DynamoDB, and the payment service authorizing at a third-party processor. At the centre, the order store in Postgres and Citus holding orders, lines, payment references and an outbox row committed in one transaction. Below the line, an outbox pump feeding Kafka order events, consumed by fulfilment, which picks, packs and ships, and by the notification and capture workers that capture money per shipment.")
a.banner("The dashed line is the commit point. Above it everything is reversible; below it nothing is, and the last step is a warehouse.")
a.box(20, 100, 170, 60, "Client", ["cart · review · submit"])
a.box(230, 100, 230, 60, "Checkout Session", ["quote + expires_at, 15 min", "quoteId submitted, never a total"])
a.cyl(500, 100, 210, 60, "DynamoDB", ["carts · sessions · TTL"])
a.box(750, 100, 230, 60, "Idempotency store", ["key = checkout session id"])
a.arrow((190, 130), (230, 130))
a.arrow((460, 130), (500, 130))
a.arrow((345, 160), (345, 196))

a.group(20, 196, 960, 150, "REVERSIBLE — INSIDE THE REQUEST, UNDONE FOR FREE")
a.box(36, 228, 280, 64, "Inventory Service", ["conditional decrement per line", "sharded by sku"])
a.cyl(340, 228, 250, 64, "ATP — DynamoDB", ["on_hand - reserved >= qty"])
a.box(614, 228, 350, 64, "Payment Service", ["authorize the quote total", "voidable at zero cost"])
a.arrow((316, 260), (340, 260))
a.arrow((590, 260), (614, 260))
a.text(36, 316, "1. reserve — cheapest to undo, and the most likely ordinary failure.   2. authorize — reversible, and it must not be inside an inventory lock.", 'dg-s')

a.cyl(230, 396, 540, 72, "Order Store — Postgres + Citus", ["orders · lines · payment refs · first event · OUTBOX ROW", "one local transaction, sharded by customer_id"], cls='dg-good')
a.arrow((176, 292), (176, 432), (230, 432))
a.arrow((789, 292), (789, 432), (770, 432))
a.hdiv(500, 20, 980)
a.lane(30, 494, "THE COMMIT POINT — ABOVE IT, ABANDONABLE. BELOW IT, RETRIED FOREVER")

a.queue(230, 528, 540, 56, "Kafka  order.placed", ["outbox pump · keyed by order_id · at-least-once"])
a.arrow((640, 468), (640, 528))

a.group(20, 620, 960, 118, "IRREVERSIBLE — OUTSIDE THE REQUEST, PAID FOR IN RETURNS")
a.box(36, 652, 300, 64, "Fulfilment", ["plan · pick · pack · ship", "the pick is the point of no return"])
a.box(360, 652, 280, 64, "Capture worker", ["per shipment, derived key"])
a.box(664, 652, 300, 64, "Payment processor", ["its own page — the inverse"])
a.arrow((350, 584), (350, 620), (186, 620), (186, 652))
a.arrow((640, 684), (664, 684))
a.arrow((336, 684), (360, 684))
a.text(20, 778, "Reserve, authorize, commit, ship, capture — sorted by how expensive each is to undo. Nothing rolls a box back off a truck, so the box goes last.", 'dg-note')

ARCH_CAP = ("Draw the dashed line before anything else, and label it the commit point. Above it the steps are "
            "ordered by how cheap they are to undo; below it nothing is undoable and every failure is "
            "compensated with an apology rather than a rollback. The order store is the only component that "
            "belongs to both halves, and its outbox row is why the hand-off downstream is reliable.")

b = Board(660, "Place Order flow, as a sequence with its branches. The idempotency check comes first and short-circuits a double click. Then the quote is validated, with an expired quote branching to a 409 and a re-quote. Then inventory is reserved, with out-of-stock branching to a clean failure. Then payment is authorized, with a decline releasing the reservation. Then the order commits in one transaction. Below the commit, the outbox publishes to fulfilment, which picks and ships, and capture happens per shipment. A separate branch shows the cancel request racing the pick, winning or losing.")
b.banner("Every branch above the commit line ends with nothing having happened. Every branch below it ends with an apology.")
b.box(30, 68, 300, 40, "POST /orders  Idempotency-Key = sessionId", cls='dg-good', tcls='dg-good-t')
b.box(400, 68, 250, 40, "key seen → replay the stored response", cls='dg-good', tcls='dg-good-t')
b.arrow((330, 88), (400, 88))
b.ctext(365, 80, "hit", 'dg-lbl')
b.box(30, 132, 300, 40, "validate the quote")
b.arrow((180, 108), (180, 132))
b.box(400, 132, 250, 40, "409 + a fresh quote, re-confirm", cls='dg-warn', tcls='dg-warn-t')
b.arrow((330, 152), (400, 152))
b.ctext(365, 144, "expired", 'dg-lbl')
b.box(30, 196, 300, 40, "reserve inventory — conditional decrement")
b.arrow((180, 172), (180, 196))
b.box(400, 196, 250, 40, "409 out_of_stock — nothing to undo", cls='dg-warn', tcls='dg-warn-t')
b.arrow((330, 216), (400, 216))
b.box(30, 260, 300, 40, "authorize payment")
b.arrow((180, 236), (180, 260))
b.box(400, 260, 250, 40, "decline → release the reservation", cls='dg-warn', tcls='dg-warn-t')
b.arrow((330, 280), (400, 280))
b.box(30, 324, 620, 56, "COMMIT — order + lines + payment ref + event + outbox row", ["one local transaction, one database"], cls='dg-good', tcls='dg-good-t')
b.arrow((180, 300), (180, 324))
b.hdiv(400, 20, 980)
b.ctext(500, 396, "BELOW HERE, FAILURE IS COMPENSATED — NEVER ROLLED BACK", 'dg-lane dg-c')
b.box(30, 424, 300, 56, "outbox → Kafka → fulfilment", ["at-least-once, idempotent consumer"])
b.arrow((180, 380), (180, 424))
b.box(400, 424, 250, 56, "pick", ["THE POINT OF NO RETURN"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((330, 452), (400, 452))
b.box(700, 424, 270, 56, "ship → capture that shipment", ["void the remainder at the end"])
b.arrow((650, 452), (700, 452))
b.box(30, 512, 300, 56, "POST /cancel → CANCEL_REQUESTED", ["202, because it is a race"])
b.box(400, 512, 570, 56, "the race resolves, and either way is normal",
      ["won  →  void the auth, release the stock, order CANCELLED",
       "lost  →  a prepaid return label, which is a different product"])
b.arrow((330, 540), (400, 540))
b.text(30, 610, "The unfulfillable line — a picker finds the last one damaged — is compensated, not rolled back: a void or a refund, and an email before the customer notices.", 'dg-note')

HLD_CAP = ("The four boxes down the left are ordered by cost to undo, and every one of them can fail into the "
           "column on the right with nothing having happened. Below the divider that is no longer true — the "
           "pick has started and the compensation is an email, a refund, or a return label.")

s = Board(586, "Amazon checkout five-minute skeleton. Rows for the cart and the quote, the idempotent Place Order call, the reserve and authorize pair, the single commit transaction spanning the full width, the outbox to fulfilment, the pick as the point of no return, and capture per shipment. A margin lane below carries the two partition keys, the oversell target, and the order rate.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 460, 56, "Cart — DynamoDB by customer_id", ["a list of intents. NO PRICES"], badge=1)
s.box(510, 68, 450, 56, "Checkout session + quote", ["server-minted total, 15-min TTL"], badge=2)
s.box(30, 144, 930, 40, "POST /orders   Idempotency-Key = the checkout session id — derived, not random", badge=3)
s.box(30, 204, 460, 56, "Reserve inventory", ["UPDATE ... WHERE on_hand - reserved >= qty"], badge=4)
s.box(510, 204, 450, 56, "Authorize payment", ["reversible — a void costs nothing"], badge=5)
s.box(30, 280, 930, 56, "COMMIT: order + lines + payment ref + event + OUTBOX ROW — one local transaction", ["this is the atomic point of the whole design"], cls='dg-good', badge=6)
s.box(30, 356, 300, 56, "Outbox pump → Kafka", ["order.placed, keyed by order_id"], badge=7)
s.box(350, 356, 300, 56, "Fulfilment picks", ["POINT OF NO RETURN, ~30 min"], cls='dg-warn', tcls='dg-warn-t', badge=8)
s.box(670, 356, 290, 56, "Capture per shipment", ["re-auth anything past 7 days"], badge=9)
s.box(30, 432, 930, 40, "Compensations, not rollbacks — void or refund plus an email; a lost cancel race is a return label", cls='dg-good', tcls='dg-good-t', badge=10)
s.lane(30, 500, "IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 512, 300, 44, "Two partition keys", ["customer_id vs sku — WHY there's a saga"])
s.box(350, 512, 300, 44, "Oversell is a number", ["2 per 10,000 lines, with an owner"])
s.box(670, 512, 290, 44, "~150 orders/s", ["so this was never a scale problem"])

SKEL_CAP = ("Badge 6 is the one to draw first and the one to defend: a single local transaction that carries the "
            "outbox row with it. Everything above it is chosen for being cheap to undo, and everything below it "
            "is chosen for being retried until it lands.")

PAGE = 'design-checkout.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
