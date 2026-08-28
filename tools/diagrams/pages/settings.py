import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

b=Board(596,"Settings sync high-level design. The client holds source documents with their versions, a pending patch, and a resolve function evaluated per key over four layers, and works with the server down. Below: a settings API doing compare-and-set on a pointer, Postgres holding immutable revisions plus the pointer and an outbox in one transaction, a fanout service, and a WebSocket gateway whose push carries only an entity and a version — a hint, not a value.")
b.banner("Push is a hint, never a value. Kill the socket tier and convergence degrades from ~2 s to ≤60 s. Nothing else changes.")
b.lane(30,76,"CLIENT (IDE) — WORKS WITH THE SERVER DOWN")
b.box(30,90,560,92,"Local store",["source documents + their versions","pending patch (base_version)","resolve() → the effective document"])
b.box(620,90,340,92,"resolve() — evaluated per key",["1 · mandatory team policy","2 · user override","3 · team default","4 · product default"],cls='dg-good')
b.hdiv(200,20,980)
b.lane(30,238,"SERVER")
b.box(30,252,300,76,"Settings API",["CAS on the pointer","PUT If-Match · 412 + current doc"])
b.box(660,252,300,76,"WS gateway",["registry (Redis)","{entity, version} only"])
b.box(30,380,300,110,"Postgres",["revision (immutable)","current (pointer)","WHERE version = $expected","membership · outbox"])
b.box(660,380,300,110,"Fanout",["outbox → Kafka, keyed by entity","team → members, paged","does NOT compute 50 k documents"])
b.arrow((150,182),(150,252),label="PUT If-Match · GET /manifest",lx=165,ly=228,lcls='dg-lbl')
b.arrow((180,328),(180,380),label="ONE transaction",lx=195,ly=360,lcls='dg-lbl')
b.arrow((180,490),(180,512),(810,512),(810,490))
b.text(380,504,"outbox drains → Kafka",'dg-lbl')
b.arrow((810,380),(810,328))
b.arrow((810,252),(810,224),(430,224),(430,182))
b.text(450,218,"{entity, version} — a hint, not a value",'dg-lbl')
b.box(390,252,240,76,"412 + the current doc",["merge disjoint keys, retry","same key → conflict UI"],cls='dg-warn',tcls='dg-warn-t')
b.box(390,380,240,110,"Absorbing the herd",["the hint carries the version","delay_ms jitter by team size","version-addressed → CDN hit","429 + Retry-After is safe"])
b.text(30,552,"Retry twice, then ask the human. An auto-merge-and-retry loop with no backoff, between two machines that both keep editing, is a livelock.",'dg-s')
b.text(30,574,"Push tier fully down? Clients fall back from a 15-minute poll to 60 seconds. There is only one recovery path, and it is also the normal path.",'dg-note')
HLD_CAP = "The socket carries an entity and a version and nothing else. Draw that label on the arrow before you draw the gateway — it is what makes duplicate pushes free, lost pushes survivable, and the whole tier optional."

s=Board(490,"Settings sync five-minute skeleton. The resolution function centred at the top over four layers, flanked by the client and the membership entity. Then the two tables and their compare-and-set predicate, the aggregate version, the manifest and If-Match calls, the socket-as-hint rule, the outbox chain, and two closing sentences.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(280,68,440,96,"resolve() — evaluated per key",["1 · mandatory team policy","2 · user override","3 · team default","4 · product default"],cls='dg-good',badge=1)
s.box(30,68,230,96,"Client",["source docs + versions","pending patch","works with server down"],badge=3)
s.box(750,68,210,96,"Membership",["its own version","feeds resolve()"],badge=8)
s.box(30,190,460,64,"Two tables",["revision (immutable) · current (pointer)","WHERE version = $expected — that is the whole of it"],badge=2)
s.box(510,190,450,64,"aggregate_version",["a tuple of every input","the ETag and the Redis cache key"],badge=9)
s.box(30,274,290,64,"GET /manifest",["{session, entity → version}","~200 bytes, usually 304"],badge=4)
s.box(350,274,290,64,"PUT If-Match",["412 returns the current document"],badge=5)
s.box(670,274,290,64,"The socket is a hint",["ignore ≤, fetch on a gap"],badge=7)
s.box(30,358,930,50,"Outbox inside the write transaction → Kafka by entity → fanout → WS gateway → client",badge=6)
s.box(30,428,460,44,"delivery is a hint; versions are the truth",cls='dg-good',badge=10)
s.box(510,428,450,44,"the layer is writable, the effect is not",cls='dg-good')
SKEL_CAP = "Badge 1 goes on the board before any box, and it is four layers deep, evaluated per key. Everything else here exists to get the right inputs into that function and to tell clients when an input moved."

a = Board(550, "Settings sync architecture. A client holding a resolve function over four layers and a SQLite store of source documents, their versions and a pending patch. A write path: settings API doing compare-and-set on a pointer in Postgres, which holds immutable revisions, the current pointer, membership and an outbox in one transaction, plus a Redis cache of effective documents keyed by aggregate version. The outbox drains to Kafka keyed by entity, then a fanout service, then a WebSocket gateway backed by a Redis connection registry. Version-addressed entity reads are served from a CDN.")
a.banner("Push is a hint, never a value — kill the socket tier and convergence degrades from ~2 s to ≤60 s, and nothing else changes.")
a.group(20, 86, 220, 180, "CLIENT (IDE)")
a.box(36, 118, 188, 56, "resolve()", ["four layers, per key"])
a.cyl(36, 190, 188, 56, "SQLite", ["source docs + versions", "pending patch"])
a.group(300, 86, 400, 220, "WRITE PATH")
a.box(316, 118, 180, 90, "Settings API",
      ["GET /v1/manifest — ~200 B", "PUT If-Match · CAS", "412 + current doc"])
a.cyl(520, 118, 164, 90, "Postgres", ["revision (immutable)", "current (pointer)", "membership · outbox"])
a.arrow((496, 163), (520, 163))
a.cyl(440, 220, 244, 56, "Redis", ["effective doc, by aggregate_version"])
a.queue(740, 118, 240, 56, "Kafka", ["keyed by entity"])
a.arrow((684, 146), (740, 146))
a.box(740, 200, 240, 56, "Fanout", ["team → members, paged"])
a.arrow((860, 174), (860, 200))
a.box(740, 290, 240, 56, "WS gateway", ["WSS · {entity, version}"])
a.cyl(740, 370, 240, 56, "Registry — Redis", ["user → gateway, TTL"])
a.arrow((860, 256), (860, 290)); a.line((860, 346), (860, 370))
a.arrow((740, 318), (278, 318), (278, 240), (240, 240))
a.text(276, 338, "{entity, version} — a hint, not a value", 'dg-lbl')
a.cyl(420, 400, 240, 56, "CDN", ["GET /entity/{type}/{id}?v=", "immutable, max-age 1 y"])
a.arrow((240, 250), (262, 250), (262, 428), (420, 428))
a.arrow((360, 208), (360, 290), (500, 290), (500, 400))
a.text(370, 286, "origin", 'dg-lbl')
a.arrow((240, 134), (316, 134))
a.arrow((316, 160), (240, 160))
a.text(20, 520, "There is only one recovery path and it is also the normal path: compare the manifest, fetch what moved, re-run resolve(). The socket only makes it faster.", 'dg-note')

ARCH_CAP = ("The socket tier is the only part of this board you could delete and still have a correct "
            "system. Draw it last, and label its arrow with what it carries — an entity and a version, "
            "never a value.")

PAGE = 'design-settings-sync.md'
place(PAGE, 'architecture', a, ARCH_CAP, after_heading='## 6 ')
place(PAGE, 'flows', b, HLD_CAP)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
