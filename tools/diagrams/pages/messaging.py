import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

b=Board(662,"Messaging high-level design. Send path: client with a client message id and optimistic echo, connection gateways, message service, and a message store sharded by conversation that assigns a sequence number and appends durably in one atomic step. Deliver path: the message service resolves members to devices, looks each up in a Redis connection registry, groups them by gateway and pushes one batched RPC per gateway; devices with no registry entry get a push notification carrying no body. Reconnect path: backoff with jitter, a sync token, then per-conversation catch-up.")
b.banner("The store is boring; the gateway tier is enormous. 120 writes/sec per shard against ~10,000 nodes holding a billion sockets.")
b.lane(30,76,"SEND")
b.box(30,90,160,72,"Client",["clientMessageId","optimistic local echo"])
b.box(230,90,240,72,"Connection Gateways",["~10 k nodes, WebSocket"])
b.box(510,90,210,72,"Message Service")
b.box(760,90,200,72,"Message Store",["sharded by conversation"])
for x1,x2 in ((190,230),(470,510),(720,760)): b.arrow((x1,126),(x2,126))
b.box(30,190,450,70,"Durability before delivery",["ack once stored — delivery may fail and retry","because sync is authoritative"],cls='dg-good',tcls='dg-good-t')
b.box(510,190,450,70,"Dedupe, in one atomic step",["seq = last_seq + 1, unique (conv_id, client_msg_id)","constraint violation → return the original"])
b.arrow((860,162),(860,190))
b.hdiv(286,20,980)

b.lane(30,312,"DELIVER — A LOOKUP, NOT A BROADCAST")
b.box(30,326,200,76,"Message Service",["members → devices"])
b.box(270,326,240,76,"Connection Registry",["Redis, device → gateway","heartbeat TTL"])
b.box(550,326,200,76,"Group by gateway",["one batched RPC per gateway"])
b.box(790,326,170,76,"Gateways",["push to local sockets"])
for x1,x2 in ((230,270),(510,550),(750,790)): b.arrow((x1,364),(x2,364))
b.arrow((390,402),(390,436))
b.box(270,436,240,52,"No entry = offline",["APNs / FCM hint, no body"],cls='dg-warn',tcls='dg-warn-t')
b.box(550,436,410,52,"seq > local_max + 1 → pull the missing range",["empty pull? retry, then advance past it — or the client wedges"])
b.hdiv(512,20,980)

b.lane(30,538,"RECONNECT")
b.box(30,552,230,56,"Backoff with jitter",["10 M in lockstep is a herd"])
b.box(290,552,290,56,"GET /sync with a sync token",["a per-device watermark"])
b.box(610,552,350,56,"Diff, then after_seq per conversation",["usually zero — one round trip"])
b.arrow((260,580),(290,580)); b.arrow((580,580),(610,580))
b.text(30,640,"Sync token older than retention? Reset to head and backfill. A bounded gap in history beats a sync that never completes.",'dg-note')
HLD_CAP = "Delivery is a lookup. Nothing subscribes to a conversation — the service resolves members to devices to gateways and sends one batched RPC per gateway, which is the same grouping trick as Discord arrived at from the opposite direction."

s=Board(510,"Messaging five-minute skeleton. A banner naming fanout and guarantees as the problem. Send row: client with a client message id, gateway, message service, and the conversation shard assigning a sequence. Rows for exactly-once impossibility, durability before delivery, the connection registry, fanout-on-read, offline push, per-device cursors and sharding by conversation.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(30,68,930,40,"Not a throughput problem, not a contention problem — fanout and guarantees",cls='dg-good',badge=1)
s.lane(30,140,"SEND")
s.box(30,154,170,64,"Client",["clientMessageId"],badge=3)
s.box(240,154,190,64,"Gateway")
s.box(470,154,200,64,"Message Service")
s.box(700,154,260,64,"Conversation shard",["seq = last_seq + 1","unique (conv, client_msg)"],badge=4)
for x1,x2 in ((200,240),(430,470),(670,700)): s.arrow((x1,186),(x2,186))
s.box(30,248,460,50,"Exactly-once is impossible",["at-least-once + idempotent dedupe at both ends"],badge=2)
s.box(510,248,450,50,"Durability before delivery",["delivery is best-effort because sync is authoritative"],badge=5)
s.lane(30,340,"DELIVER")
s.box(30,354,290,64,"Connection registry",["device → gateway, ~10 k nodes","batch per gateway, not pub/sub"],badge=6)
s.box(350,354,290,64,"Fanout-on-read for content",["write only for notifications"],badge=7)
s.box(670,354,290,64,"Offline → APNs / FCM hint",["no body · two-phase bounded sync"],badge=8)
s.box(30,440,460,46,"Read state = per-device cursor",["debounced, lossy — monotonic state is safe to drop"],badge=9)
s.box(510,440,450,46,"Shard by conversation_id",["single-writer ordering · name the retention fork"],badge=10)
SKEL_CAP = "Badge 4 is the one integer doing four jobs — order, gaps, cursors, dedupe. Say the density fork out loud while you draw it: sortable is free, dense is what forces the counter and the log into one transaction."

a = Board(590, "Messaging architecture. Roughly a billion devices holding one socket each into a fleet of about ten thousand connection gateways. A Redis connection registry maps device to gateway. A message service resolves members to devices and writes to a message log sharded by conversation id, with cursors co-partitioned alongside. A Kafka outbox feeds receipts, search indexing and analytics, and a push tier for offline devices. A separate sync service backed by a Redis conversation list.")
a.banner("The store is boring and the gateway tier is enormous: 120 writes/sec per shard against ~10 k nodes holding a billion sockets.")
a.box(20, 240, 150, 64, "Devices", ["~1 B, one socket each"])
a.group(200, 86, 560, 130, "CONNECTION GATEWAYS — ~10 k NODES")
for x in (216, 396, 576):
    a.box(x, 118, 168, 64, "Gateway", ["holds sockets"])
a.cyl(790, 118, 180, 64, "Connection registry", ["Redis, device → gateway"])
a.group(200, 260, 560, 180, "MESSAGE SERVICE + STORE")
a.cyl(216, 292, 280, 64, "Message log", ["sharded by conversation_id", "seq = last_seq + 1"])
a.box(520, 292, 224, 64, "Message Service", ["members → devices"])
a.arrow((520, 324), (496, 324))
a.cyl(216, 376, 280, 50, "Cursors", ["co-partitioned with the log"])
a.arrow((600, 216), (600, 292)); a.ctext(600, 250, "send", 'dg-lbl')
a.arrow((680, 292), (680, 216)); a.ctext(680, 250, "deliver", 'dg-lbl')
a.arrow((744, 310), (776, 310), (776, 150), (790, 150))
a.queue(790, 292, 180, 56, "Kafka", ["outbox"])
a.box(790, 376, 180, 64, "Consumers", ["receipts · search · analytics"])
a.box(790, 470, 180, 56, "APNs / FCM", ["wake-up hint, no body"])
a.arrow((744, 340), (762, 340), (762, 320), (790, 320))
a.arrow((880, 348), (880, 376)); a.arrow((880, 440), (880, 470))
a.box(216, 470, 180, 56, "Sync service", ["per-device watermark"])
a.cyl(430, 470, 270, 56, "Conversation list", ["Redis zset, convs:{user}"])
a.arrow((396, 498), (430, 498))
a.arrow((170, 258), (182, 258), (182, 150), (216, 150))
a.arrow((170, 290), (194, 290), (194, 498), (216, 498))
a.text(20, 560, "Delivery is a lookup, not a broadcast — nothing subscribes to a conversation. And nothing is retried at the delivery layer, because sync is authoritative.", 'dg-note')

ARCH_CAP = ("Count the boxes: the store is one cylinder and the gateway tier is a fleet. If you spend the "
            "round sharding the database you have designed the cheap half — the interesting number is the "
            "connection count, two orders of magnitude above the write rate.")

PAGE = 'design-messaging.md'
place(PAGE, 'architecture', a, ARCH_CAP, after_heading='## 6 ')
place(PAGE, 'flows', b, HLD_CAP)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
