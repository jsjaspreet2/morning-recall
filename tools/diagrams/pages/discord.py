import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board
from splice import place

a = Board(570, "Discord-inspired live path. HTTP API accepts an authenticated idempotent message into ScyllaDB through data services, then directly calls the BEAM guild service over gRPC. Guild owners route to relays that filter authorized interested sessions and batch by node. Session processes have bounded in-memory mailboxes, replay and socket queues. A Redis directory only locates surviving sessions. Postgres owns role metadata. This live path does not depict an atomic durable dispatch guarantee.")
a.banner("Durable history first; direct gRPC into BEAM for live fanout. Mailboxes are in memory.")
a.lane(20, 86, "ACCEPT — HTTP REQUEST / RESULT")
a.box(20, 110, 240, 78, "API + data services", ["auth + sender permission", "nonce → canonical message"])
a.cyl(330, 110, 270, 78, "ScyllaDB", ["send attempts + history", "channel / bucket placement"])
a.arrow((260, 149), (330, 149))
a.ctext(294, 138, "persist", 'dg-lbl')
a.cyl(710, 110, 270, 78, "Postgres metadata", ["guilds · channels · roles", "versioned authorization"])
a.lane(310, 254, "LIVE — ACTOR FANOUT")
a.box(20, 310, 240, 84, "Guild owner (BEAM)", ["shared guild state", "routing, not history ordering"])
a.box(365, 310, 270, 84, "Relays for large guilds", ["recipient permission checks", "interested sessions · batch by node"])
a.box(740, 310, 240, 84, "Session processes", ["bounded mailbox + replay", "per-session event sequence"])
a.arrow((140, 188), (140, 310))
a.ctext(225, 227, "gRPC after storage", 'dg-lbl')
a.arrow((260, 352), (365, 352))
a.arrow((635, 352), (740, 352))
a.cyl(20, 450, 240, 66, "Redis session directory", ["host + generation + lease", "does not preserve replay"])
a.box(365, 450, 270, 66, "Presence aggregation", ["all devices · timeout + disconnect", "coalesced / visible members only"])
a.box(740, 450, 240, 66, "Clients over WebSocket", ["message-identity dedupe", "settle into history order"])
a.arrow((860, 394), (860, 450))
a.arrow((710, 150), (670, 150), (670, 280), (580, 280), (580, 310))
a.ctext(582, 222, "role / channel versions", 'dg-lbl')
a.arrow((140, 394), (140, 450))
a.ctext(208, 426, "session lookup", 'dg-lbl')
a.arrow((500, 450), (500, 394))
a.text(20, 551, "If storage succeeds but dispatch fails, RESUME cannot invent the missing event. See the recovery paths below.", 'dg-note')

b = Board(590, "Recovery decision diagram. A disconnected client tries resume. A surviving session stream with retained coverage replays events. A lost or expired stream requires a fresh session and paginated state and history. Independently, a database message never dispatched has no session event to replay; history refresh repairs the current view, while stronger completeness requires durable dispatch and change cursors.")
b.banner("Session replay and history reconciliation cover different failures.")
b.box(30, 95, 250, 76, "Connection lost", ["reconnect with jitter", "session ID + last processed seq"])
b.box(375, 95, 260, 76, "Can the stream resume?", ["session state survives", "buffer still covers the gap"])
b.arrow((280, 133), (375, 133))
b.box(715, 95, 250, 76, "Replay session events", ["then continue live", "duplicates remain possible"], cls='dg-good')
b.arrow((635, 133), (715, 133))
b.ctext(675, 123, "yes", 'dg-lbl')
b.box(375, 240, 260, 76, "New session + state", ["invalid / expired / lost session", "bounded membership subscriptions"])
b.arrow((505, 171), (505, 240))
b.ctext(550, 209, "no", 'dg-lbl')
b.box(715, 240, 250, 76, "History API", ["active channel first", "page older messages on demand"])
b.arrow((635, 278), (715, 278))
b.hdiv(355, 20, 980)
b.lane(30, 390, "SEPARATE FAILURE — STORED, BUT NEVER DISPATCHED")
b.box(30, 415, 280, 82, "No session event exists", ["a successful RESUME can omit it", "refresh recent history to repair view"], cls='dg-warn')
b.box(380, 415, 585, 82, "Stronger requirement: durable dispatch + recovery cursor", ["acceptance-coupled record / change stream → retrying relay → guild", "direct gRPC may remain the fast path; define retention and dedupe"])
b.arrow((310, 456), (380, 456))
b.text(30, 548, "Sparse message IDs sort history. Session seq orders a session stream. Neither alone proves complete offline delivery.", 'dg-note')

s = Board(570, "Discord interview skeleton. Acceptance and direct gRPC lead to guild routing, authorized selective relays, and bounded session delivery. Margin notes cover load, reconnect, presence, hot reads, and the distinction between durable history and best-effort live dispatch.")
s.banner("Draw shared history and live actors; explain the failure boundary between them.")
s.box(30, 90, 260, 76, "HTTP acceptance", ["permission + stable nonce", "durable canonical history"], badge=2)
s.box(370, 90, 250, 76, "Direct post-store gRPC", ["bounded deadline / retries", "not a durable handoff"], badge=3)
s.box(700, 90, 270, 76, "Guild owner", ["shared community state", "not database commit order"], badge=4)
s.arrow((290, 128), (370, 128))
s.arrow((620, 128), (700, 128))
s.box(700, 240, 270, 76, "Relays", ["interested + authorized", "group recipients by node"], badge=5)
s.box(370, 240, 250, 76, "Session → WebSocket", ["bounded replay and socket queues", "event seq + identity dedupe"], badge=6)
s.box(30, 240, 260, 76, "Reconnect", ["resume surviving stream", "otherwise page state / history"], badge=7)
s.arrow((835, 166), (835, 240))
s.arrow((700, 278), (620, 278))
s.arrow((370, 278), (290, 278))
s.lane(30, 368, "IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 390, 290, 64, "Workload assumptions", ["15 M sessions / 150 k peak sends", "size storage, hot reads, fanout"], badge=1)
s.box(355, 390, 290, 64, "Presence", ["aggregate devices; 20 s / 60 s", "coalesce / selective subscriptions"], badge=8)
s.box(680, 390, 290, 64, "Hot reads / read state", ["coalesce identical history queries", "monotonic per-user read position"], badge=9)
s.box(30, 495, 940, 48, "Durable history, best-effort live push. Stronger delivery needs a durable dispatch and recovery mechanism.", cls='dg-warn', badge=10)

PAGE = 'design-discord.md'
place(PAGE, 'architecture', a,
      "Published live-path shape, with proposed storage and recovery choices. BEAM implements the guild/relay/session tier; it does not replace a transactional outbox. Recipient authorization is separate from permission to send.",
      after_heading='## 6 ')
place(PAGE, 'flows', b,
      "A lost socket can resume only if its event stream survives. A message that never reached that stream needs independent history or durable-dispatch recovery; replay cannot repair an event that does not exist.",
      after_heading='## 7 ')
place(PAGE, 'skeleton', s,
      "The large-fanout companion to Slack: spend the hour on selective recipients, relay work, bounded queues, and honest reconnect guarantees.",
      after_heading='## 14 ')
BOARDS = 3
WARN = a.warn + b.warn + s.warn
