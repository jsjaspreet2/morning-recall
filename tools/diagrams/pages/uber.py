import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# --- Flow A, the supply firehose (second fenced block replaced first, so the
#     first block's fence indices stay valid for the call below) ---
a=Board(366,"Uber supply firehose. Driver app pings every four seconds over a WebSocket to a regional location gateway, then the location service computes an H3 cell. The path forks: a hot in-memory geo index sharded by cell, where ninety percent of pings overwrite in place, and a cold Kafka path to S3 and the warehouse that is never in the matching path.")
a.banner("The hot path answers one question — who is near here, right now. Never route matching through Kafka.")
a.box(30,90,180,64,"Driver app",["ping / 4 s"])
a.box(250,90,240,64,"Location Gateway",["WebSocket, regional"])
a.box(530,90,220,64,"Location Service",["h3.latLngToCell(…, 8)"])
a.arrow((210,122),(250,122)); a.arrow((490,122),(530,122))
a.line((640,154),(640,186)); a.line((280,186),(830,186))
a.arrow((280,186),(280,220)); a.arrow((830,186),(830,220))
a.box(60,220,440,90,"HOT — in-memory geo index",["sharded by cell, Redis-backed for failover","same cell (~90%): overwrite in place, O(1)","different cell: move, and hand off on the ring"])
a.box(560,220,400,90,"COLD — Kafka → S3 / warehouse",["fire-and-forget, never in the matching path","traffic modeling · reconstruction · disputes"])
a.text(30,344,"No ping for 30 s → stale, and deprioritized in matching. 60 s → evicted entirely. Tunnels and dead apps must not appear as available supply.",'dg-note')
FLOW_A_CAP = "One source, two consumers, nothing in common. Kafka is a log, not an index — routing a matching query through it adds queue latency to the one thing that has to be fresh."

b=Board(620,"Uber demand path. Rider app to API gateway to ride service, which returns 201 without waiting for a match and writes to a region-sharded ride database with an outbox. The ride service enqueues to the matching service, which owns a cell range on the consistent-hash ring and is the only reader of the geo index. The matcher runs a funnel from k-ring to real road ETAs, offers with a fifteen-second TTL, and finally commits a conditional update that enforces exactly one driver.")
b.banner("The matcher is the only component that reads the supply index and writes the ride state machine — one owner, no lock.")
b.box(30,90,140,56,"Rider app")
b.box(210,90,150,56,"API Gateway")
b.box(400,90,200,56,"Ride Service",["201 without a match"])
b.box(640,90,320,56,"Ride DB",["sharded by region · outbox → Kafka"])
for x1,x2 in ((170,210),(360,400),(600,640)): b.arrow((x1,118),(x2,118))
b.arrow((500,146),(500,190))
b.box(330,190,340,76,"Matching Service",["owns a cell range on the ring","single writer — no distributed lock"])
b.arrow((670,228),(720,228),label="reads",lx=695,ly=220,lcls='dg-lbl dg-c')
b.box(720,190,240,76,"Geo index",["read-only from here"])
b.arrow((500,266),(500,310))
b.box(230,310,540,76,"The funnel",["k-ring → ~200 candidates → filter to AVAILABLE + class → ~50","haversine top 10 → real road ETAs → batch-solve in a 2–5 s window"])
b.arrow((500,386),(500,430))
b.box(230,430,540,64,"Offer, 15 s TTL",["decline or timeout → cascade to the next candidate","~60 s total, then fail visibly"])
b.arrow((500,494),(500,510))
b.box(30,510,930,60,"WHERE id=? AND status='MATCHING' AND version=? — zero rows means another matcher already assigned it",["this is where “exactly one driver” is actually enforced"],cls='dg-good')
b.text(30,600,"Push is an optimization, not the source of truth. If it is dropped, or the socket reconnects, the client calls GET /v1/rides/{id} and reconciles.",'dg-note')
FLOW_B_CAP = "The funnel narrows twice for a reason: cheap filters first, real road ETAs only on ten candidates. The conditional update at the bottom is the line that actually enforces one driver per ride — everything above it is an optimization."


s=Board(460,"Uber five-minute skeleton. A banner naming the thousand-to-one ratio between the supply firehose and the ride lifecycle, then supply and demand, the matcher's cell ownership and the matching funnel, the offer TTL and the WebSocket push, and the region-sharded ride database with its payment saga.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(30,68,930,40,"Supply firehose 2.5 M writes/sec, disposable · ride lifecycle 30 k writes/sec, durable — a 1000× ratio",cls='dg-good',badge=1)
s.box(30,140,460,64,"Supply",["H3 index, sharded by parent cell, in memory","the cold path forks to Kafka"],badge=2)
s.box(510,140,450,64,"Demand",["quote → ride (idempotency key) → matcher"],badge=3)
s.box(30,224,460,64,"Matcher owns a cell range",["consistent hashing → single writer, no distributed lock"],badge=4)
s.box(510,224,450,64,"The funnel",["k-ring → filter → haversine top 10 → real ETA","batched min-cost assignment"],badge=5)
s.box(30,308,460,64,"Offer, 15 s TTL",["cascade on decline","the DB conditional update is the last line of defense"],badge=6)
s.box(510,308,450,64,"WebSocket push",["the client reconciles on reconnect"],badge=7)
s.box(30,392,930,50,"Region-sharded ride DB · payment pre-auth at start, async capture at end — the trip never blocks on payment",badge=8)
SKEL_CAP = "Badge 1 first, out loud: two systems, a thousand-to-one write ratio, and only one of them is allowed to lose data. Draw them as separate diagrams and the rest of the round follows."

a2 = Board(660, "Uber architecture, two systems side by side. A supply tier: driver apps pinging a regional location gateway every four seconds, a location service computing an H3 cell, an in-memory geo index sharded by cell and backed by Redis, and a cold fork to Kafka and the warehouse. A demand tier: rider app, API gateway, ride service returning immediately, a matching service that owns a cell range on the consistent-hash ring and is the only reader of the geo index, and a region-sharded ride database. Kafka carries ride events to push notifications.")
a2.banner("Two systems with a 1000:1 write ratio: a disposable supply firehose and a durable ride lifecycle. Only one may lose data.")
a2.group(20, 86, 470, 200, "SUPPLY — 2.5 M WRITES/SEC, DISPOSABLE")
a2.box(36, 118, 180, 64, "Driver app", ["WSS · ping / 4 s", "lat, lng, heading, ts"])
a2.box(256, 118, 218, 64, "Location Gateway", ["WebSocket, regional", "202 ack, no payload"])
a2.arrow((216, 150), (256, 150))
a2.cyl(36, 206, 218, 64, "Geo index", ["in memory, by cell", "Redis-backed"])
a2.box(274, 206, 200, 64, "Location Service", ["h3.latLngToCell"])
a2.arrow((365, 182), (365, 206))
a2.arrow((274, 238), (254, 238))
a2.queue(540, 206, 200, 56, "Kafka", ["driver.locations"])
a2.cyl(780, 206, 200, 56, "S3 / warehouse")
a2.arrow((490, 234), (540, 234)); a2.arrow((740, 234), (780, 234))
a2.box(436, 300, 268, 56, "Pricing · Routing",
       ["POST /v1/fare-quotes", "signed quote, expiresAt"])
a2.group(20, 360, 700, 220, "DEMAND — 30 k WRITES/SEC, DURABLE")
a2.box(36, 392, 160, 64, "Rider app", ["HTTPS + WSS"])
a2.box(236, 392, 160, 64, "API Gateway")
a2.box(436, 392, 268, 64, "Ride Service",
       ["POST /v1/rides · Idempotency-Key", "201 without a match"])
a2.arrow((196, 424), (236, 424)); a2.arrow((396, 424), (436, 424))
a2.box(236, 480, 200, 64, "Matching Service", ["owns a cell range"])
a2.cyl(476, 480, 228, 64, "Ride DB", ["sharded by region · outbox"])
a2.arrow((570, 456), (570, 480)); a2.arrow((336, 456), (336, 480)); a2.arrow((436, 512), (476, 512))
a2.arrow((236, 512), (200, 512), (200, 290), (145, 290), (145, 270))
a2.text(206, 334, "reads supply", 'dg-lbl')
a2.arrow((570, 392), (570, 356))
a2.queue(760, 392, 220, 56, "Kafka", ["ride events"])
a2.box(760, 480, 220, 64, "Push / notifications",
       ["WS /v1/rides/{id}/events", "connection registry"])
a2.arrow((704, 420), (760, 420)); a2.arrow((870, 448), (870, 480))
a2.arrow((760, 512), (720, 512), (720, 610), (116, 610), (116, 456))
a2.text(20, 640, "The hot path answers one question — who is near here, right now. Never route a matching query through Kafka: it is a log, not an index.", 'dg-note')

ARCH_CAP = ("Two boards' worth of system drawn as two boxes, and the only arrow between them is the matcher "
            "reading the geo index. That single reader is what makes the matcher a single writer over its "
            "cell range, which is what removes the distributed lock.")

PAGE = 'design-uber.md'
# §6 holds two fenced blocks; the later one is replaced first so the
# earlier one's fence indices are still valid for the call below it.
place(PAGE, 'architecture', a2, ARCH_CAP, after_heading='## 6 ')
place(PAGE, 'demand', b, FLOW_B_CAP)
place(PAGE, 'supply', a, FLOW_A_CAP)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 4
WARN = a2.warn + a.warn + b.warn + s.warn
