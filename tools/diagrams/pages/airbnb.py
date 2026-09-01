import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# ---------------- §6 -----------------------------------------------------
b=Board(600,"Airbnb high-level design. A search lane carrying 99.9% of traffic: client to search service to Elasticsearch with a geo bounding box and availability bitmap, then hydration. A booking lane: client to booking API to a Temporal workflow whose four steps end at a reservations database with an exclusion constraint. An outbox feeds Kafka, which updates the search index seconds later. A third lane polls external iCal calendars, the real source of double bookings.")
b.banner("1000:1 read:write — 100k searches/sec against 23 bookings/sec. Search is the hard problem; correctness is one line of DDL.")

b.lane(30,76,"SEARCH — 99.9% OF TRAFFIC")
b.box(30,90,110,64,"Client")
b.box(180,90,160,64,"Search Service",["one ES query"])
b.box(380,90,250,64,"Elasticsearch",["geo bbox + attrs + availability bitmap","ranked; cursor on (score, listing_id)"])
b.box(670,90,290,64,"Hydrate",["per-night price with host overrides","fees, photos, review aggregates"])
for x1,x2 in ((140,180),(340,380),(630,670)): b.arrow((x1,122),(x2,122))
b.ctext(505,180,"no post-filtering — pagination stays correct")
b.ctext(815,180,"prices computed at hydration, not indexed")
b.hdiv(206,20,980)

b.lane(30,232,"BOOKING — RARE, TRANSACTIONAL")
b.box(30,246,110,52,"Client")
b.box(180,246,160,52,"Booking API",["idempotency key"])
b.box(380,246,290,110,"Temporal workflow",
      ["1 · insert PENDING — constraint arbitrates","2 · authorize payment, before any wait",
       "3 · confirm → outbox event","4 · durable timer → capture at check-in"])
b.box(710,246,250,110,"Reservations DB",["EXCLUDE USING gist","(listing_id =, stay_range &&)","half-open ranges '[)'"],cls='dg-good')
b.arrow((140,272),(180,272)); b.arrow((340,272),(380,272)); b.arrow((670,301),(710,301))
b.box(380,380,290,56,"outbox → Kafka",["search index · notifications","push blocked dates to external calendars"])
b.arrow((525,356),(525,380))
b.arrow((380,408),(358,408),(358,140),(380,140))
b.text(180,200,"index updates (~seconds)",'dg-lbl')
b.hdiv(460,20,980)

b.lane(30,486,"HOST / EXTERNAL — WHERE DOUBLE BOOKINGS ACTUALLY COME FROM")
b.box(30,500,150,52,"iCal poller",["every few minutes"])
b.box(220,500,170,52,"Calendar Sync",["detect, don't prevent"])
b.box(430,500,180,52,"Block ranges")
b.arrow((180,526),(220,526)); b.arrow((390,526),(430,526))
b.arrow((610,526),(835,526),(835,364))
b.text(660,516,"conflicts arrive after the fact",'dg-note')
b.text(30,580,"A stale search result is fine. Three layers, each fresher than the last: search bitmap → listing calendar → constraint. Only the last is truth.",'dg-note')

HLD_CAP = "Two paths that touch in exactly one place — an outbox, read seconds later. Draw that gap deliberately: the search lane never reads the reservations database, and saying so is worth more than any box on the board."

# ---------------- §14 ----------------------------------------------------
s=Board(470,"Airbnb five-minute skeleton. Search lane: client, search service, Elasticsearch, hydrate. Booking lane: client, booking API, Temporal workflow, reservations database with an exclusion constraint. Three notes on durable execution, active expiry and derived availability. An external calendar lane, and the three availability layers ordered by freshness.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.badge(22,68,1); s.lane(38,72,"SEARCH — 100k/SEC")
s.box(30,86,100,56,"Client")
s.box(168,86,140,56,"Search Service")
s.box(346,86,250,56,"Elasticsearch",["geo bbox + availability bitmap"],badge=5)
s.box(634,86,200,56,"Hydrate",["prices computed here"],badge=6)
for x1,x2 in ((130,168),(308,346),(596,634)): s.arrow((x1,114),(x2,114))

s.badge(22,190,2); s.lane(38,194,"BOOKING — 23/SEC, CONTENTION ≈ 1")
s.box(30,208,100,64,"Client")
s.box(168,208,140,64,"Booking API",["idempotency key"])
s.box(346,208,250,64,"Temporal workflow",["constraint → auth → approve","confirm → timer → capture"],badge=7)
s.box(634,208,200,64,"Reservations DB",["EXCLUDE USING gist","half-open '[)'"],cls='dg-good',badge=3)
for x1,x2 in ((130,168),(308,346),(596,634)): s.arrow((x1,240),(x2,240))

for i,(n,t) in enumerate([(8,"Temporal is durable execution, not mutual exclusion — the constraint does the arbitrating."),
                          (9,"Expiry is active here, a workflow timer. A constraint cannot evaluate now()."),
                          (4,"Availability is derived from reservations + rules, and materialized only into the index.")]):
    y=302+24*i; s.badge(30,y-4,n); s.text(48,y,t)

s.vdiv(440,376,452)
s.badge(22,384,11); s.lane(38,388,"EXTERNAL")
s.box(30,400,140,44,"iCal poller")
s.box(210,400,160,44,"Calendar Sync",["detect, don't prevent"])
s.arrow((170,422),(210,422))
s.badge(462,384,10); s.lane(478,388,"AVAILABILITY — LEAST TO MOST FRESH")
s.box(470,400,150,44,"search bitmap")
s.box(650,400,150,44,"listing calendar")
s.box(830,400,140,44,"constraint",cls='dg-good')
s.arrow((620,422),(650,422)); s.arrow((800,422),(830,422))

SKEL_CAP = "Draw it cold, then check the badges. The three text lines are the ones with no box to hang on — they get said, not drawn, and they are where most candidates go quiet."

a = Board(750, "Airbnb architecture. Clients on the left. A search tier: search service and pricing service reading a geo-sharded Elasticsearch cluster carrying the availability bitmap, plus a Redis price cache. A booking tier: booking API, Temporal workers, a Postgres reservations store with an exclusion constraint sharded by listing id, the payment processor, and a co-sharded listings store. On the right, a Kafka outbox feeding consumers that update the search index. At the bottom, an external tier polling iCal calendars.")
a.banner("The search tier never touches the reservations database — it reads an index built from the change stream.")
a.box(20, 200, 150, 64, "Clients", ["web · iOS · Android"])

a.group(200, 86, 520, 166, "SEARCH — 100k QPS, STALE-TOLERANT")
a.box(216, 118, 160, 56, "Search Service", ["GET /v1/search", "viewport bbox + dates"])
a.cyl(400, 118, 300, 56, "Elasticsearch", ["geo-sharded · availability bitmap"])
a.box(216, 194, 160, 50, "Pricing Service", ["per-night + fees"])
a.cyl(400, 194, 300, 50, "Price cache — Redis", ["(listing, date range, guests)"])
a.arrow((376, 146), (400, 146)); a.arrow((376, 219), (400, 219))

a.group(200, 320, 520, 230, "BOOKING — 23/SEC, STRICTLY CORRECT")
a.box(216, 352, 160, 56, "Booking API", ["POST /v1/bookings", "Idempotency-Key"])
a.box(216, 428, 160, 72, "Temporal workers", ["durable execution", "signals + 24 h timers"])
a.cyl(400, 352, 300, 56, "Reservations — Postgres", ["EXCLUDE USING gist, by listing_id"])
a.box(400, 440, 140, 60, "Payments (PSP)")
a.cyl(560, 440, 140, 60, "Listings", ["Postgres"])
a.arrow((296, 408), (296, 428))
a.arrow((376, 464), (400, 464))
a.arrow((376, 440), (390, 440), (390, 380), (400, 380))
a.line((630, 408), (630, 440))

a.queue(770, 352, 200, 56, "Kafka", ["outbox"])
a.box(770, 440, 200, 72, "Consumers", ["search index update", "notify · calendar push"])
a.arrow((870, 408), (870, 440))
a.arrow((700, 380), (770, 380))
a.arrow((970, 440), (985, 440), (985, 146), (720, 146))
a.text(760, 138, "index updates (~seconds)", 'dg-lbl')

a.arrow((170, 216), (186, 216), (186, 146), (216, 146))
a.arrow((170, 248), (194, 248), (194, 380), (216, 380))

a.group(200, 590, 780, 110, "EXTERNAL — WHERE DOUBLE BOOKINGS ACTUALLY COME FROM")
a.box(216, 622, 180, 56, "iCal poller", ["HTTP GET .ics", "every few minutes"])
a.box(430, 622, 200, 56, "Calendar Sync", ["detect, don't prevent"])
a.arrow((396, 650), (430, 650))
a.arrow((630, 650), (700, 650), (700, 550))
a.text(20, 730, "The search tier reads an index, never the reservations database. That gap is what lets 100k QPS coexist with one Postgres constraint doing all the arbitration.", 'dg-note')

ARCH_CAP = ("Two tiers that share no store. The only thing crossing between them is a Kafka outbox read "
            "seconds later — draw that gap deliberately, because it is what makes a 1000:1 read ratio "
            "survivable without weakening the one constraint that guarantees correctness.")

PAGE = 'design-airbnb.md'
place(PAGE, 'architecture', a, ARCH_CAP, after_heading='## 6 ')
place(PAGE, 'flows', b, HLD_CAP)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
