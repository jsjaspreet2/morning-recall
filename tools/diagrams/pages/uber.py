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
a.box(560,220,400,90,"COLD — Kafka → S3 / warehouse",["fire-and-forget, never in the matching path","traffic modelling · reconstruction · disputes"])
a.text(30,344,"No ping for 30 s → stale, and deprioritised in matching. 60 s → evicted entirely. Tunnels and dead apps must not appear as available supply.",'dg-note')
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
b.text(30,600,"Push is an optimisation, not the source of truth. If it is dropped, or the socket reconnects, the client calls GET /v1/rides/{id} and reconciles.",'dg-note')
FLOW_B_CAP = "The funnel narrows twice for a reason: cheap filters first, real road ETAs only on ten candidates. The conditional update at the bottom is the line that actually enforces one driver per ride — everything above it is an optimisation."


s=Board(460,"Uber five-minute skeleton. A banner naming the thousand-to-one ratio between the supply firehose and the ride lifecycle, then supply and demand, the matcher's cell ownership and the matching funnel, the offer TTL and the WebSocket push, and the region-sharded ride database with its payment saga.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(30,68,930,40,"Supply firehose 2.5 M writes/sec, disposable · ride lifecycle 30 k writes/sec, durable — a 1000× ratio",cls='dg-good',badge=1)
s.box(30,140,460,64,"Supply",["H3 index, sharded by parent cell, in memory","the cold path forks to Kafka"],badge=2)
s.box(510,140,450,64,"Demand",["quote → ride (idempotency key) → matcher"],badge=3)
s.box(30,224,460,64,"Matcher owns a cell range",["consistent hashing → single writer, no distributed lock"],badge=4)
s.box(510,224,450,64,"The funnel",["k-ring → filter → haversine top 10 → real ETA","batched min-cost assignment"],badge=5)
s.box(30,308,460,64,"Offer, 15 s TTL",["cascade on decline","the DB conditional update is the last line of defence"],badge=6)
s.box(510,308,450,64,"WebSocket push",["the client reconciles on reconnect"],badge=7)
s.box(30,392,930,50,"Region-sharded ride DB · payment pre-auth at start, async capture at end — the trip never blocks on payment",badge=8)
SKEL_CAP = "Badge 1 first, out loud: two systems, a thousand-to-one write ratio, and only one of them is allowed to lose data. Draw them as separate diagrams and the rest of the round follows."

PAGE = 'design-uber.md'
# §6 holds two fenced blocks; the later one is replaced first so the
# earlier one's fence indices are still valid for the call below it.
place(PAGE, 'demand', b, FLOW_B_CAP, section='## 6 ', nth=1)
place(PAGE, 'supply', a, FLOW_A_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
