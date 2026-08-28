import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

b=Board(872,"ChatGPT high-level design. Write path: client, API gateway, chat service, ScyllaDB, with a quota check at the door before enqueue. The chat service enqueues to a scheduler, priority queues by tier, and a fixed pool of inference workers. Each worker makes two independent writes that never meet: token-by-token XADD into Redis Streams for the lossy live view, which the streaming tier tails and forwards over SSE, and one finished message into Kafka keyed by chat id for durability, which a persister batch-writes to ScyllaDB. Read path: client to gateway to chat service to ScyllaDB.")
b.banner("Two independent writes out of the GPU — different systems, different reasons, and neither is a backup for the other.")
b.lane(30,76,"WRITE / GENERATE")
b.box(30,90,110,56,"Client")
b.box(170,90,140,56,"API Gateway")
b.box(340,90,180,56,"Chat Service",["CRUD + enqueue"])
b.box(550,90,200,56,"ScyllaDB",["chats, messages, runs"])
b.box(780,90,180,56,"Quota at the door",["rejection costs 0 GPU-seconds"],cls='dg-good',tcls='dg-good-t')
for x1,x2 in ((140,170),(310,340),(520,550)): b.arrow((x1,118),(x2,118))
b.arrow((430,146),(430,180),label="enqueue",lx=445,ly=168,lcls='dg-lbl')
b.box(340,180,180,52,"Scheduler",["tier weight + aging"])
b.arrow((430,232),(430,266))
b.box(300,266,260,52,"Priority queues",["free / plus / pro"])
b.arrow((430,318),(430,352))
b.box(280,352,300,64,"Inference workers",["fixed GPU pool · continuous batching"])
b.line((430,416),(430,450)); b.line((200,450),(720,450))
b.arrow((200,450),(200,486)); b.arrow((720,450),(720,486))
b.ctext(460,470,"two independent writes — neither is a backup for the other",'dg-lbl')
b.box(80,486,240,64,"Redis Streams",["key run:{runId} · XADD per token","lossy and TTL'd — costs the animation"])
b.arrow((200,550),(200,584))
b.box(60,584,310,64,"Streaming Tier",["~570 k SSE connections, no run state","XREAD from last-seen id → SSE"])
b.arrow((200,648),(200,676))
b.box(60,676,310,40,"Client — SSE, Last-Event-ID replays")
b.box(600,486,240,64,"Kafka",["topic messages, key = chatId","exactly one finished message"])
b.arrow((720,550),(720,584))
b.box(600,584,240,52,"Persister",["batches writes"])
b.arrow((720,636),(720,668))
b.box(600,668,240,40,"ScyllaDB")
b.ghost(395,560,180,110,"THEY NEVER MEET",["the streaming tier reads","Redis and only Redis","Kafka never feeds a stream"])
b.hdiv(740,20,980)
b.lane(30,766,"READ / HISTORY")
b.box(30,780,110,64,"Client")
b.box(170,780,150,64,"API Gateway")
b.box(350,780,180,64,"Chat Service")
b.box(560,780,260,64,"ScyllaDB",["LOCAL_ONE for the sidebar","your own chat: LOCAL_QUORUM"])
for x1,x2 in ((140,170),(320,350),(530,560)): b.arrow((x1,812),(x2,812))
HLD_CAP = "Draw the fork under the GPU first. Redis carries tokens for the live view and is allowed to lose them; Kafka carries one finished message and is not. Lose Redis and the animation breaks while the answer still gets stored — lose Kafka and the user watches a perfect answer you then fail to keep."

s=Board(606,"ChatGPT five-minute skeleton. A numbers banner, then the three tiers, the Run entity, the two-call submit and stream split, SSE, the Redis stream path, the two cheap writes on completion, cancellation, shedding, prefill versus decode, metering, context assembly and the storage layout.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.",y=10,h=34)
s.box(30,68,930,40,"57k generations/sec · 570 k concurrent streams · ~72 k GPUs · ~$3.5 M/day · 1.8 PB/yr",cls='dg-good',badge=13)
s.badge(22,132,1); s.lane(38,136,"THREE TIERS — ~50 MACHINES AGAINST ~9,000")
s.box(30,150,280,64,"API — CRUD",["stateless, scales on requests"])
s.box(350,150,280,64,"Streaming — sockets",["570 k connections, no run state"])
s.box(670,150,290,64,"Inference — GPUs",["fixed pool, scheduled not scaled"])
s.box(30,234,280,64,"Run",["queued → running → done / failed"],badge=2)
s.box(350,234,280,64,"Submit ≠ stream",["POST returns runId; GET streams"],badge=3)
s.box(670,234,290,64,"SSE, not WebSocket",["Last-Event-ID replay · cancel is a POST"],badge=4)
s.box(30,318,600,64,"Worker → Redis Stream run:{runId} → streaming tier",["SSE event id = Redis entry id, so reconnect is a replay from an offset"],badge=5)
s.box(650,318,310,64,"Two cheap writes, no DB call",["terminal entry + Kafka by chatId","a GPU never waits on storage"],badge=6)
s.box(30,402,300,50,"A closed socket is not a cancel",["cancel must reach the GPU"],cls='dg-warn',tcls='dg-warn-t',badge=7)
s.box(350,402,300,50,"Shed at the door",["never kill work in flight"],badge=8)
s.box(670,402,290,50,"Prefill compute-bound",["decode is bandwidth-bound"],badge=9)
s.box(30,472,460,50,"Meter tokens, not requests",["weighted queues with aging, not strict priority"],badge=10)
s.box(510,472,450,50,"Context: system → summary → last K",["stable prefix first, for the KV cache"],badge=11)
s.box(30,542,930,44,"ScyllaDB partitioned on chatId · a second table for the sidebar · hot/warm/cold at 30 and 180 days",badge=12)
SKEL_CAP = "Thirteen marks, and the top row carries the argument: ~50 machines against ~9,000 is why the tiers are separate deploys. Say the ratio before you draw the second box."

PAGE = 'design-chatgpt.md'
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ')
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 2
WARN = b.warn + s.warn
