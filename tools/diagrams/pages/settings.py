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

PAGE = 'design-settings-sync.md'
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ')
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 2
WARN = b.warn + s.warn
