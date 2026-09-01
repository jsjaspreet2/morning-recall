import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

b=Board(605,"Discord high-level design. A write path over HTTP: client to API service, which evaluates permissions once, mints a Snowflake id and writes to ScyllaDB before publishing. The guild process owns one guild, resolves online members and groups them by gateway node, sending one message per node rather than one per session. Three gateway nodes fan out to roughly fifteen million WebSocket clients. A Redis session registry with heartbeat TTL drives routing and presence.")
b.banner("Ingest is trivial; fanout is not. Tens of thousands of writes a second become ~15 M sockets and millions of deliveries.")
b.lane(30,76,"WRITE PATH — OVER HTTP, NOT OVER THE SOCKET")
b.box(30,90,110,72,"Client",["POST + nonce"])
b.box(180,90,190,72,"API service",["permissions once, here","Snowflake id"])
b.box(420,90,240,72,"Message store",["ScyllaDB","(channel_id, bucket)"])
b.arrow((140,126),(180,126)); b.arrow((370,126),(420,126))
b.box(690,90,270,72,"Order is not negotiable",["store write, then publish —","the inverse is unrecoverable"],cls='dg-warn',tcls='dg-warn-t')
b.arrow((275,162),(275,196),(430,196),(430,220),label="publish(channel_id)",lx=300,ly=190,lcls='dg-lbl')
b.box(280,220,380,92,"Guild / channel process (BEAM)",
      ["one owner per guild → per-channel total order","resolves ONLINE members, groups by gateway node",
       "one message per node, not per session — the 100× win"],cls='dg-good')
b.line((450,312),(450,344)); b.line((190,344),(630,344))
for cx in (190,410,630): b.arrow((cx,344),(cx,380))
for x in (100,320,540): b.box(x,380,180,72,"Gateway node",["local sockets","stamps a per-session seq"])
for cx in (190,410,630): b.arrow((cx,452),(cx,500))
for x in (100,320,540): b.box(x,500,180,36,"clients — WebSocket")
b.box(760,380,200,92,"Session registry",["Redis, heartbeat TTL","who is where, for routing","and for presence, by expiry"])
b.arrow((860,380),(860,266),(660,266))
b.text(680,258,"presence = TTL expiry, coalesced",'dg-lbl')
b.text(30,560,"A message can exist that nobody was told about; the client re-reads it on RESUME, because the store is the source of truth and the push is an optimization over it.",'dg-s')
b.text(30,582,"Degrade in this order: presence → read state → history depth. Never live message delivery.",'dg-note')
HLD_CAP = "The 100× win is one arrow, and it is the reason this page exists: the guild process groups recipients by <em>gateway node</em> before sending. Everything above that box is unremarkable; everything below it is the interview."

s=Board(512,"Discord five-minute skeleton. Write row: client, API service, ScyllaDB. Fanout row: guild process, one message per gateway node, gateway nodes stamping a sequence number, clients holding one WebSocket each. A Redis session registry. Margin notes for RESUME, presence, read state and the degradation order.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.badge(22,68,2); s.lane(38,72,"WRITE — HTTP, NOT THE SOCKET")
s.box(30,86,100,56,"Client")
s.box(158,86,200,56,"API service",["permissions once · Snowflake"],badge=3)
s.box(398,86,220,56,"ScyllaDB",["(channel_id, bucket)"])
s.arrow((130,114),(158,114)); s.arrow((358,114),(398,114))
s.box(650,86,310,56,"Store, then publish",["never the inverse — it is unrecoverable"],cls='dg-warn',tcls='dg-warn-t')
s.lane(30,190,"FANOUT")
s.box(30,204,250,76,"Guild process",["one owner per guild","per-channel total order for free"],badge=4)
s.badge(360,206,5); s.ctext(360,232,"one message per node")
s.arrow((280,242),(440,242))
s.box(440,204,210,76,"Gateway nodes",["stamp a monotonic seq"],badge=6)
s.arrow((650,242),(690,242))
s.box(690,204,270,76,"clients",["one WebSocket each","~15 M concurrent"],badge=1)
s.line((545,300),(545,280))
s.box(440,300,210,44,"Session registry",["Redis, heartbeat TTL"])
s.lane(30,380,"IN THE MARGIN — SAID, NOT DRAWN")
s.box(30,394,300,50,"RESUME from seq",["replay buffer · backoff + jitter"],badge=8)
s.box(350,394,290,50,"Presence",["TTL-derived · coalesced · lazy"],badge=7)
s.box(660,394,300,50,"Read state",["write-behind · coalescing cache"],badge=9)
s.box(30,462,930,40,"Degrade in this order: presence → read state → history depth. Never live message delivery.",cls='dg-warn',badge=10)
SKEL_CAP = "The bottom row is the one candidates skip. Presence, read state and the degradation order are not decoration — presence is the highest-volume event type in the system, and scoping it out is what makes the connection look stateless when it is not."

a = Board(512, "Discord architecture. Clients holding one WebSocket each. A write tier over HTTP: API service, ScyllaDB for messages partitioned by channel and bucket, Postgres for guild metadata and roles, and ScyllaDB for read state. A guild process tier, one owner per guild, resolving online members and grouping them by gateway node. A gateway fleet of roughly ten thousand nodes holding fifteen million sockets, with a Redis session registry on a heartbeat TTL. Attachments go to S3 and a CDN, never through the gateway.")
a.banner("Ingest is trivial; fanout is not. One API tier, one process per guild, and ~10 k gateway nodes holding 15 M sockets.")
a.box(20, 240, 150, 64, "Clients", ["WSS to receive", "HTTPS to send"])
a.cyl(20, 340, 150, 64, "S3 + CDN", ["attachments"])
a.line((95, 304), (95, 340))

a.group(200, 86, 420, 180, "WRITE — OVER HTTP")
a.box(216, 118, 180, 64, "API service",
      ["POST /channels/{id}/messages", "permissions once · Snowflake"])
a.cyl(420, 118, 180, 64, "ScyllaDB", ["(channel_id, bucket)"])
a.arrow((396, 150), (420, 150))
a.cyl(216, 200, 180, 50, "Postgres", ["guilds · roles"])
a.cyl(420, 200, 180, 50, "Read state", ["Scylla, write-behind"])

a.group(680, 86, 300, 150, "GUILD PROCESSES")
a.box(696, 118, 270, 90, "Guild / channel process",
      ["one owner per guild", "resolves ONLINE members", "groups them by gateway node"])
a.arrow((306, 182), (306, 196), (628, 196), (628, 150), (696, 150))
a.ctext(650, 214, "publish", 'dg-lbl')

a.group(200, 300, 780, 130, "GATEWAY FLEET — ~10 k NODES, 15 M SOCKETS")
for x in (216, 406, 596):
    a.box(x, 340, 180, 64, "Gateway node",
          ["WSS · IDENTIFY / RESUME", "heartbeat ~40 s · stamps seq"])
a.cyl(800, 340, 166, 64, "Session registry", ["Redis, heartbeat TTL"])
a.line((830, 236), (830, 283)); a.line((306, 283), (830, 283))
for cx in (306, 496, 686):
    a.arrow((cx, 283), (cx, 340))
a.line((800, 372), (776, 372))
a.arrow((170, 258), (186, 258), (186, 150), (216, 150))
a.arrow((216, 372), (194, 372), (194, 290), (170, 290))
a.text(20, 470, "Attachment bytes never pass through the gateway — the message row carries a pointer to S3.", 'dg-s')
a.text(20, 492, "There is no broker in the delivery path: it would add a durable hop to something explicitly not durable.", 'dg-note')

ARCH_CAP = ("One process per guild is the whole architecture. It is the only component that knows which "
            "members are online, so it is the only place the recipient list can be grouped by gateway "
            "node — and that grouping is the 100× win.")

PAGE = 'design-discord.md'
place(PAGE, 'architecture', a, ARCH_CAP, after_heading='## 6 ')
place(PAGE, 'flows', b, HLD_CAP)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
