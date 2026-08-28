import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

b=Board(662,"Ticketmaster high-level design, two paths that barely touch. Ten million users hit an edge that is both CDN and queue admission worker. Left path, browse at five million QPS: an availability service serving a ten-kilobyte bitmap from memory, rebuilt from the inventory change stream and edge-cached for one to five seconds, plus WebSocket deltas applied only when the version is exactly one ahead. Right path, buy at about two thousand a second: booking service requiring a session token, an inventory database with one shard per event and lazy expiry inside the conditional update, an outbox to Kafka, and the payment processor. Deltas flow from the inventory database back to the availability service.")
b.banner("Two paths that barely touch. 5 M QPS of browse never reaches the inventory DB; ~2 k/s is all the booking tier ever sees.")
b.box(30,90,150,64,"10 M users")
b.box(230,90,460,64,"EDGE — CDN + queue / admission worker",["the only thing between the herd and the booking tier"])
b.box(730,90,230,64,"Admission control",["scale by admitting, not by capacity"],cls='dg-good',tcls='dg-good-t')
b.arrow((180,122),(230,122))
b.lane(30,190,"BROWSE — 5 M QPS, STALE-TOLERANT")
b.lane(700,190,"BUY — ~2 k/s, STRICTLY SERIALIZABLE")
b.arrow((330,154),(330,200),label="~5 M QPS",lx=345,ly=182,lcls='dg-lbl')
b.arrow((590,154),(590,200),label="~2 k/s admitted",lx=605,ly=182,lcls='dg-lbl')
b.box(30,200,400,90,"Availability Service",["10 KB bitmap + version, served from memory","rebuilt from the inventory change stream","edge cache 1–5 s TTL — that TTL absorbs the QPS"])
b.arrow((230,290),(230,334))
b.box(30,334,400,76,"WebSocket deltas",["{version, changes: [[ordinal, status]]}","apply only if version == local + 1, else resync"])
b.box(530,200,430,76,"Booking Service",["session token required — this is what makes the queue real","seats acquired in sorted seat_id order"])
b.arrow((745,276),(745,320))
b.box(530,320,430,76,"Inventory DB",["one shard per event · a single writer","AVAILABLE / HELD / SOLD · lazy expiry in the predicate"])
b.arrow((745,396),(745,436))
b.box(530,436,430,60,"outbox → Kafka",["orders · notifications · analytics · async capture"])
b.arrow((745,496),(745,536))
b.box(530,536,430,50,"Payment Service (PSP)",["authorize under its own idempotency key"])
b.arrow((530,358),(480,358),(480,245),(430,245))
b.text(486,232,"deltas",'dg-lbl')
b.text(30,620,"The read path never touches the inventory DB. That is what lets 5 M QPS coexist with a single writer per event.",'dg-s')
b.text(30,642,"Abandonment: nothing happens. No job runs, no timer fires — the seat is reclaimed by whichever writer next evaluates the expiry predicate.",'dg-note')
HLD_CAP = "The two columns share one arrow, and it points the cheap way: inventory deltas out to the cache, never a read in. Scaling by admission rather than by capacity is the architectural move — everything right of the edge is built for 2 k/s and will never see more."

s=Board(490,"Ticketmaster five-minute skeleton. A banner separating browse from buy, then contention and sharding, the edge waiting room and the read path, the three inventory states and the two ways to acquire seats, multi-seat transactions and the purchase saga.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(30,68,930,40,"Browse: 5 M QPS, stale-OK. Buy: 60 k total writes, strictly serializable. Separate them completely.",cls='dg-good',badge=1)
s.box(30,140,460,56,"Contention 166:1",["the ratio is the problem, not the volume"],badge=2)
s.box(510,140,450,56,"Shard by event_id",["the hot shard is intentional · dedicate capacity"],badge=9)
s.box(30,216,460,76,"Edge waiting room",["Redis INCR → signed token → drain at measured capacity","session token required by the booking API"],badge=3)
s.box(510,216,450,76,"Read path",["10 KB bitmap + version, edge-cached 1–5 s","WebSocket deltas · resync on a version gap"],badge=4)
s.box(30,312,460,76,"Inventory — three states",["a hold is a row with hold_expires_at","lazy expiry inside the conditional update; the sweeper is cosmetic"],badge=5)
s.box(510,312,450,76,"Acquiring seats",["user-selected → optimistic conditional update","best-available → FOR UPDATE SKIP LOCKED"],badge=6)
s.box(30,408,460,56,"Multi-seat = one transaction",["seats acquired in sorted order, or you deadlock"],badge=7)
s.box(510,408,450,56,"Saga: hold → authorize → sell → capture",["reversible actions first"],badge=8)
SKEL_CAP = "Badge 2 is the sentence that reframes the round: 166 bidders per seat is a contention problem, and no amount of throughput planning touches it. Say it before you draw the waiting room."

a = Board(730, "Ticketmaster architecture. Ten million users hit an edge tier that is both CDN and waiting room: an admission worker issuing signed queue tokens against Redis counters, and a CDN serving the event page and availability blob on a one-to-five second TTL. A read tier holds the availability bitmap in memory and pushes WebSocket deltas. A buy tier, reached only with a session token, runs the booking service and order service against a Postgres inventory sharded one shard per event, plus the payment processor. A Kafka outbox carries deltas back to the read tier.")
a.banner("Scale by admission, not by capacity: everything past the edge is built for ~2 k/s and will never see more.")
a.box(20, 150, 150, 64, "10 M users")
a.group(200, 86, 460, 200, "EDGE — CDN + WAITING ROOM")
a.box(216, 118, 200, 64, "Admission worker",
      ["POST /queue → signed token", "GET /queue/{token} · poll or SSE"])
a.cyl(440, 118, 204, 64, "Redis", ["queue:seq · queue:admitted"])
a.arrow((416, 150), (440, 150))
a.cyl(216, 206, 428, 56, "CDN",
      ["GET /events/{id}/availability", "event page · blob, 1–5 s TTL"])
a.arrow((170, 182), (193, 182), (193, 150), (216, 150))
a.group(700, 86, 280, 200, "READ — 5 M QPS")
a.box(716, 118, 248, 64, "Availability Service", ["bitmap in memory"])
a.box(716, 206, 248, 56, "WS delta tier", ["WSS /availability/stream", "version + changes"])
a.arrow((840, 182), (840, 206))
a.arrow((644, 234), (676, 234), (676, 150), (716, 150))
a.group(200, 340, 460, 200, "BUY — ~2 k/s, STRICTLY SERIALIZABLE")
a.box(216, 372, 180, 64, "Booking Service", ["POST /v1/holds", "session token · Idem-Key"])
a.cyl(420, 372, 224, 64, "Inventory — Postgres", ["one shard per event"])
a.box(216, 460, 180, 64, "Order Service", ["POST /v1/orders"])
a.box(420, 460, 224, 64, "Payment (PSP)")
a.arrow((396, 404), (420, 404)); a.arrow((306, 436), (306, 460)); a.arrow((396, 492), (420, 492))
a.arrow((306, 286), (306, 340))
a.queue(200, 580, 444, 56, "Kafka", ["outbox → availability, tickets, analytics"])
a.arrow((644, 404), (672, 404), (672, 560), (560, 560), (560, 580))
a.arrow((644, 608), (690, 608), (690, 150), (716, 150))
a.text(600, 660, "deltas, ~1 s to the edge", 'dg-lbl')
a.text(20, 700, "The read path never touches the inventory DB, and the admission worker is the only thing standing between the herd and the booking tier.", 'dg-note')

ARCH_CAP = ("The board has two halves and one arrow between them, pointing the cheap way: inventory deltas "
            "out to the cache, never a read in. Draw the edge first — it is the component that makes every "
            "number downstream of it small.")

PAGE = 'design-ticketmaster.md'
place(PAGE, 'architecture', a, ARCH_CAP, after_heading='## 6 ')
place(PAGE, 'flows', b, HLD_CAP)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
