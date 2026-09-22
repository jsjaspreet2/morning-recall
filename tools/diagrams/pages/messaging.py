import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board
from splice import place

a = Board(610, "Slack-like messaging architecture. Clients send through WebSocket gateways to the Message Service. A conversation-sharded Postgres group commits message, retry result, counter and outbox before acknowledgement. After commit, the Message Service can deliver small conversations directly to recipient gateways. Independently, an outbox relay publishes to Kafka, then a channel fanout service pushes to subscribed gateways. Both paths use the same message identity. Search is an asynchronous consumer. A separate History and Sync API reads channel history and heads from Postgres and memberships from a durable directory. Live pushes are repaired by bounded sync.")
a.banner("One durable acceptance transaction; live delivery can repeat or fail because bounded sync repairs it.")
a.lane(20, 86, "ACCEPT — ACK AFTER THE REPLICATED COMMIT")
a.box(20, 110, 140, 74, "Clients", ["retry ID", "local outbox"])
a.box(210, 110, 180, 74, "Gateways", ["WebSocket sessions", "bounded send queues"])
a.box(450, 110, 200, 74, "Message Service", ["auth + shard routing", "idempotent send"])
a.cyl(730, 100, 240, 104, "Postgres shard group", ["message + dedupe", "counter + outbox", "cross-AZ replication"])
a.arrow((160, 147), (210, 147))
a.arrow((390, 147), (450, 147))
a.arrow((650, 147), (730, 147))
a.ctext(690, 137, "transaction", 'dg-lbl')
a.arrow((480, 184), (480, 220), (370, 220), (370, 184))
a.ctext(610, 218, "DM fast path · only after commit", 'dg-lbl')
a.lane(390, 254, "DELIVER — DURABLE BACKGROUND PATH")
a.box(730, 290, 240, 70, "Outbox relay", ["publish committed events", "retry with stable event ID"])
a.queue(450, 290, 200, 70, "Kafka", ["at-least-once events", "bounded replay retention"])
a.box(210, 290, 180, 70, "Channel fanout", ["channel / device routes", "leased subscriptions"])
a.arrow((850, 204), (850, 290))
a.ctext(920, 237, "committed outbox", 'dg-lbl')
a.arrow((730, 325), (650, 325))
a.arrow((450, 325), (390, 325))
a.arrow((300, 290), (300, 184))
a.ctext(235, 238, "message bodies", 'dg-lbl')
a.box(450, 400, 200, 54, "Search consumer", ["Elasticsearch · optional"])
a.arrow((550, 360), (550, 400))
a.lane(20, 463, "RECOVER — HTTPS")
a.cyl(20, 485, 190, 70, "Membership directory", ["Postgres projection", "paginated per user"])
a.box(280, 485, 280, 70, "History / Sync API", ["authorize · heads · range pages", "active channel check ≤30s"])
a.arrow((280, 520), (210, 520))
a.arrow((560, 520), (990, 520), (990, 150), (970, 150))
a.ctext(803, 500, "authoritative heads + history", 'dg-lbl')
a.arrow((90, 184), (90, 385), (245, 385), (245, 468), (420, 468), (420, 485))
a.ctext(142, 375, "HTTPS sync", 'dg-lbl')
a.text(20, 590, "A lost final push needs a periodic head check. Dense sequence numbers alone cannot reveal it.", 'dg-note')

s = Board(644, "Slack five-minute skeleton with ten numbered points. Scope and sizing, client and acceptance transaction, durability and channel fanout, recovery and unread state, retention and storage alternatives. Numbers match the accompanying interview outline.")
s.banner("Slack: shared retained history + transactional acceptance + recoverable live delivery.")
items = [
    ("Scope", ["channels / DMs · 90-day history", "unread state, no public read receipts"]),
    ("Size the whole workload", ["assume 1 B messages/day → 60 k peak/s", "writes + reads + storage + failure capacity"]),
    ("Client", ["persist retry ID before sending", "optimistic echo → canonical ack"]),
    ("Conversation-local transaction", ["permission + dedupe + counter", "message + outbox"]),
    ("Durability before acknowledgement", ["cross-AZ replicated commit", "no safe primary → pending send"]),
    ("Live delivery", ["DM: direct gateway attempt after commit", "always outbox → Kafka → fanout"]),
    ("Bounded recovery", ["membership / heads → range pages", "periodic active-channel reconciliation"]),
    ("Client and unread state", ["identity dedupe + covered ranges", "user read cursor = MAX; retry final update"]),
    ("Lifecycle", ["explicit history expiry; preserve counter", "dedupe retention; asynchronous search"]),
    ("Storage tradeoff", ["Postgres for local transaction simplicity", "sparse + another store if measured need"]),
]
for index, (title, lines) in enumerate(items):
    x = 30 if index % 2 == 0 else 515
    y = 88 + (index // 2) * 106
    s.box(x, y, 455, 76, title, lines, badge=index + 1)
s.text(30, 625, "Sparse IDs change completeness detection, not the need for idempotency or reliable recovery.", 'dg-note')

PAGE = 'design-messaging.md'
place(PAGE, 'architecture', a,
      "The Postgres cylinder is a sharded fleet, not one machine. Its local transaction establishes acceptance. Small sends may go directly to recipient gateways after commit; the outbox path always runs and can deliver duplicates with the same identity. Sync reads durable history when a push is missed.",
      after_heading='## 6 ')
place(PAGE, 'skeleton', s,
      "Keep acceptance, delivery, and recovery separate on the board. The transaction is the correctness shortcut; the bounded recovery path is still required.",
      after_heading='## 14 ')
BOARDS = 2
WARN = a.warn + s.warn
