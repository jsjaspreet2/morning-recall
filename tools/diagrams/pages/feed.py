import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

b=Board(596,"Feed high-level design. Write path: post to the tweet service, Snowflake id, tweet store, acknowledge immediately. An outbox feeds Kafka and fanout workers with tiered queues, which read the social graph and either push into a Redis timeline cache below the follower threshold, or do nothing at all above it. Read path: timeline service merges a sorted-set range with the recent tweets of followed celebrities, then hydrates bodies, authors and counts.")
b.banner("6k writes/sec, ×200 amplification. Neither pure strategy works — push below the threshold, pull above it, merge at read.")
b.lane(30,76,"WRITE — ENDS AT THE TWEET STORE")
b.box(30,90,130,56,"POST /tweets")
b.box(190,90,180,56,"Tweet Service",["Snowflake id"])
b.box(400,90,200,56,"Tweet Store",["source of truth"])
b.arrow((160,118),(190,118)); b.arrow((370,118),(400,118))
b.box(640,90,320,56,"Ack here",["durable now; everything after is delivery"],cls='dg-good',tcls='dg-good-t')
b.arrow((500,146),(500,180))
b.box(400,180,200,44,"outbox → Kafka")
b.arrow((500,224),(500,258))
b.box(340,258,300,76,"Fanout workers",["tiered queues by follower count","active users only · idempotent ZADD"])
b.box(30,258,250,76,"Social graph",["who follows X","stored both directions"])
b.arrow((340,296),(280,296))
b.box(700,254,260,56,"Timeline cache",["Redis zset, capped ~400"])
b.ghost(700,326,260,60,"ABOVE ~100k → NOTHING",["the path is the absence of work"])
b.arrow((640,280),(700,280)); b.arrow((640,312),(670,312),(670,356),(700,356))
b.hdiv(410,20,980)

b.lane(30,436,"READ — THE MERGE IS THE HYBRID")
b.box(30,450,140,64,"GET /timeline")
b.box(190,450,170,64,"Timeline Service",["merge · dedupe · cap"])
b.arrow((170,482),(190,482))
b.box(400,428,250,44,"ZREVRANGE timeline:{user}")
b.box(400,486,250,44,"celebrity recent tweets")
b.arrow((360,482),(380,482),(380,450),(400,450))
b.arrow((360,482),(380,482),(380,508),(400,508))
b.box(700,450,260,64,"Hydrate",["tweet · author · counts","this is the real read cost"])
b.arrow((650,450),(675,450),(675,468),(700,468))
b.arrow((650,508),(675,508),(675,496),(700,496))
b.text(30,558,"Filter deletes, blocks and mutes at read time. Scrubbing timelines is what makes a delete expensive.",'dg-s')
b.text(30,578,"Losing fanout writes degrades a timeline; it never loses a tweet. That is what makes the cache safe to lose.",'dg-note')
HLD_CAP = "Two arrows leave the fanout worker and one of them goes nowhere. Draw the celebrity branch as an empty box on purpose — the elegant part of this design is work that does not happen."

s=Board(520,"Feed five-minute skeleton. An amplification banner, a write row from tweet service through Kafka and fanout workers into the Redis timeline cache, the social graph and the hybrid threshold, the free celebrity pull, then a read row: timeline lookup, merge, hydrate, cursor.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(30,68,930,40,"6k writes/sec · ×200 amplification, ×100 M worst case — the write is trivial, the amplification is the problem",cls='dg-good',badge=1)
s.lane(30,140,"WRITE")
s.box(30,154,170,64,"Tweet Service")
s.box(230,154,200,64,"Kafka",["tiered queues"],badge=5)
s.box(460,154,230,64,"Fanout workers",["active users · idempotent ZADD"])
s.box(720,154,240,64,"Timeline cache",["Redis zset, capped ~400","it is a cache"],badge=6)
for x1,x2 in ((200,230),(430,460),(690,720)): s.arrow((x1,186),(x2,186))
s.box(30,248,230,56,"Social graph",["both directions · bucketed"],badge=8)
s.box(290,248,400,56,"Hybrid",["push below ~100k · pull above · merge at read"],badge=3)
s.box(720,248,240,56,"Celebrity pull is free",["one list, millions of readers"],cls='dg-good',badge=4)
s.lane(30,346,"READ")
s.box(30,360,230,64,"Timeline lookup",["~1 ms"])
s.box(290,360,200,64,"Merge · dedupe · cap")
s.box(520,360,250,64,"Hydrate",["tweet · author · counts","the real read cost"],badge=9)
s.box(790,360,170,64,"Cursor",["Snowflake, never offset"],badge=10)
for x1,x2 in ((260,290),(490,520),(770,790)): s.arrow((x1,392),(x2,392))
s.box(30,458,460,40,"Deletes filtered at read time, never scrubbed",badge=7)
s.box(510,458,450,40,"Fanout-on-write by default — the inverse of messaging",badge=2)
SKEL_CAP = "Badge 3 is the whole answer and it is one box: neither pure strategy survives contact with a 100 M-follower account. Get the threshold on the board and the two deep dives write themselves."

PAGE = 'design-feed.md'
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ')
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 2
WARN = b.warn + s.warn
