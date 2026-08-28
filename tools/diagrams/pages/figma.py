import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

b=Board(578,"Figma high-level design. Client column: input, local apply to the scene graph painting inside sixteen milliseconds with no network, a WebGL renderer, and a pending queue keyed by object and property holding unacknowledged values. Server column: one file process per open file acting as the ordering authority with last-writer-wins per property, an op log in Kafka as the system of record, and a snapshot job to S3 and the CDN. A bottom lane shows cold open: snapshot from CDN, decode off the main thread, paint the viewport first, then apply the op tail.")
b.banner("Convergence, not linearizability. The document model chose the algorithm — and the local loop never waits for the network.")
b.lane(30,76,"CLIENT — 16 MS, NO NETWORK ON THIS PATH")
b.lane(560,76,"SERVER — ONE PROCESS PER OPEN FILE")
b.vdiv(515,90,145); b.vdiv(515,255,420)
b.box(40,100,180,40,"Input")
b.box(40,158,180,56,"Local apply",["scene graph, painted now"])
b.box(40,232,180,52,"Renderer (WebGL)",["16 ms budget"])
b.arrow((130,140),(130,158)); b.arrow((130,214),(130,232))
b.box(250,150,200,100,"Pending queue",["keyed (objectId, key)","unacknowledged values","1000 frames replay as 1"])
b.arrow((220,186),(250,186))
b.box(560,100,400,120,"File process",
      ["the ordering authority — one per open file","in-memory document · version counter",
       "last-writer-wins per property","socket set for this file"])
b.arrow((450,170),(560,170)); b.ctext(505,162,"set · clientSeq",'dg-lbl')
b.arrow((560,200),(450,200)); b.ctext(505,222,"ack · set · bye",'dg-lbl')
b.box(560,270,400,56,"Op log — Kafka, partitioned by fileId",["the system of record"])
b.box(560,356,400,52,"Snapshot job → S3 → CDN")
b.arrow((760,220),(760,270)); b.arrow((760,326),(760,356))
b.box(250,270,200,76,"Discard rule",["a remote set for a property","you hold an unacked value for","is dropped, every frame"],cls='dg-warn',tcls='dg-warn-t')
b.arrow((350,250),(350,270))
b.hdiv(430,20,980)
b.lane(30,456,"COLD OPEN — hello(sinceVersion)")
b.box(30,470,220,52,"snapshot from CDN",["immutable blob + its version"])
b.box(290,470,220,52,"decode off main thread")
b.box(550,470,200,52,"paint viewport first")
b.box(790,470,170,52,"apply op tail",["then live"])
for x1,x2 in ((250,290),(510,550),(750,790)): b.arrow((x1,496),(x2,496))
b.text(30,552,"Tail too old? The server does not reconstruct — it sends a fresh snapshot and the client discards everything except its pending queue.",'dg-note')
HLD_CAP = "The interesting line is the one that isn't there: nothing on the local loop touches the network. Draw the client as a closed cycle first, then hang the socket off the pending queue — that ordering is the whole argument for why this is not OT."

s=Board(500,"Figma five-minute skeleton. The document model as a map of object to property to value. Client loop: input, local apply, renderer, pending queue. One WebSocket to one file process, the ordering authority, with a registry, an op log and a snapshot path to the CDN. Presence drawn as a separate lossy arrow, and two decisions written in the corner.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(30,68,930,40,"Map<ObjectID, Map<Property, Value>> — the property is the unit of conflict",cls='dg-good',badge=1)
s.lane(30,140,"CLIENT")
s.lane(560,140,"SERVER")
s.vdiv(515,150,230); s.vdiv(515,262,330)
s.box(30,154,150,50,"Input",badge=2)
s.box(30,222,150,50,"Local apply",["16 ms"])
s.box(30,290,150,50,"Renderer (WebGL)")
s.arrow((105,204),(105,222)); s.arrow((105,272),(105,290))
s.box(220,204,240,86,"Pending queue",["keyed (objectId, key)","unacked values only"],badge=3)
s.arrow((180,247),(220,247))
s.box(560,154,400,86,"File process",["the ordering authority","LWW per property"],badge=4)
s.arrow((460,247),(560,247)); s.ctext(510,239,"one WebSocket",'dg-lbl')
s.box(560,270,400,44,"Op log — Kafka by fileId",badge=6)
s.box(560,338,400,44,"Snapshot → S3 → CDN",badge=7)
s.arrow((760,240),(760,270)); s.arrow((760,314),(760,338))
s.arrow((560,360),(500,360),(500,404),(180,404))
s.box(30,382,150,44,"cold open")
s.box(220,338,240,44,"Presence",["lossy · unordered · never stored"],badge=8)
s.box(30,446,290,40,"Registry: fileId → server",badge=5)
s.box(340,446,290,40,"fractional index · LWW per property",badge=9)
s.box(650,446,310,40,"convergence, not linearizability",cls='dg-good',badge=10)
SKEL_CAP = "Item 1 is a box because it is the answer: get the document model on the board before anything else, and the algorithm argument in §7 writes itself. The two boxes at the bottom are the sentences you close on."

PAGE = 'design-figma.md'
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ')
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 2
WARN = b.warn + s.warn
