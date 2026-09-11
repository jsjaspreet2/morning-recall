import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

# ---------------------------------------------------------------- architecture
a = Board(660, "Sandboxed compute architecture, one cell. Control plane: an API, Postgres holding workspaces and sessions with a version column for compare-and-set, a scheduler and an idle reaper. Data plane: hosts running a host agent, Firecracker microVMs one per session behind cgroups, a warm pool of pre-booted sandboxes, an NVMe snapshot cache, and a per-host egress proxy that blocks the metadata endpoint. Storage: object storage for workspace files, snapshots and overlays, with a content-addressed layer cache. Streaming: a stateless WebSocket gateway tailing per-session output logs in Redis Streams. GPU hosts are a separate substrate with no suspend.")
a.banner("A guest kernel per session, nothing shared; resume is an attach to a restored snapshot; an idle session holds zero host RAM.")

a.group(20, 86, 300, 260, "CONTROL PLANE — DECIDES, RUNS NO CODE")
a.box(36, 118, 268, 56, "API", ["open = create-or-resume · idempotent"])
a.cyl(36, 190, 268, 64, "Postgres, per cell", ["workspaces · sessions (state, version, lease)", "UPDATE … WHERE version = $expected"])
a.box(36, 270, 128, 60, "Scheduler", ["cache affinity"])
a.box(176, 270, 128, 60, "Idle reaper", ["30 min → suspend"])
a.arrow((170, 174), (170, 190)); a.arrow((100, 254), (100, 270)); a.arrow((240, 254), (240, 270))

a.group(350, 86, 630, 260, "DATA PLANE — HOSTS, ~1,200 PER REGION, 50 CELLS")
a.box(366, 118, 290, 110, "Host agent",
      ["runs microVMs · snapshots · file agent", "cgroups: cpu · mem · pids · egress", "holds the scoped token; the guest holds none"])
a.arrow((304, 300), (336, 300), (336, 173), (366, 173))
a.ctext(336, 165, "place", 'dg-lbl')
a.box(686, 118, 278, 56, "Firecracker microVM × N", ["guest kernel · kernel manager · overlay"], cls='dg-good', tcls='dg-good-t')
a.arrow((656, 146), (686, 146))
a.box(686, 190, 114, 38, "Warm pool", cls='dg-good', tcls='dg-good-t')
a.box(826, 190, 138, 38, "GPU: full VM")
a.box(686, 246, 278, 84, "Egress proxy, per host",
      ["blocks 169.254.169.254 + RFC 1918", "allowlist registries · logs every dest", "the abuse signal"],
      cls='dg-warn', tcls='dg-warn-t')
a.arrow((813, 174), (813, 246))
a.cyl(366, 246, 290, 84, "NVMe snapshot cache", ["last suspend, 24 h", "resume < 1 s from here"])
a.arrow((511, 228), (511, 246))

a.group(20, 380, 500, 130, "STORAGE — THE THREE CLASSES")
a.cyl(36, 412, 150, 84, "Files", ["object storage · 11 nines", "never on a host"])
a.cyl(206, 412, 150, 84, "Overlays", ["disk delta · rebuildable", "pip install survives"])
a.cyl(376, 412, 128, 84, "Snapshots", ["memory · best-effort", "aged out at 30 d"])
a.arrow((450, 330), (450, 360), (281, 360), (281, 412))
a.arrow((560, 330), (560, 365), (440, 365), (440, 412))
a.text(470, 352, "suspend: upload, free the VM", 'dg-lbl')

a.group(550, 380, 430, 130, "STREAMING")
a.cyl(566, 412, 200, 84, "Redis Streams", ["one log per session · seq", "24 h · compacted on suspend"])
a.box(786, 412, 178, 84, "WS gateway", ["stateless · tails by seq", "attach?after=seq"])
a.arrow((766, 454), (786, 454))
a.arrow((656, 205), (670, 205), (670, 412))
a.text(676, 372, "output via vsock", 'dg-lbl')

a.text(20, 550, "The session row says what should be; the host agent says what is; a reconciler fixes the difference. Nothing on a host is a source of truth.", 'dg-s')
a.text(20, 572, "Suspended sessions: ~750 k × ~1 GB in object storage. Resident, they would be seven times the fleet.", 'dg-s')
a.text(20, 594, "Reseed entropy and host keys at every attach — a golden snapshot restored without it is a shared secret.", 'dg-note')

ARCH_CAP = ("Draw the microVM box with its label — a guest kernel per session — before any latency number, then the "
            "egress proxy beside it with the one address it blocks. The three cylinders at the bottom are three "
            "promises; say which one is best-effort while you draw it.")

# ---------------------------------------------------------------- flows
b = Board(620, "Sandboxed compute high-level design in three lanes. Resume: compare-and-set the session row to resuming under a lease, pick a host by cache affinity, restore the snapshot lazily, reseed, attach network and files, and compare-and-set to ready; fallbacks at fifteen seconds to a cold boot with the overlay, then without it. Run a cell: the kernel manager writes sequence-numbered chunks to the session log; the gateway tails it; a disconnect changes nothing for execution; the client resumes from the last sequence; output is capped with a marker and blobs go by reference. Suspend and abuse: the idle reaper drives the machine, a snapshot that misses the budget keeps only the overlay, and a fork bomb is contained by cgroups, caught by egress logs, and suspended automatically.")
b.banner("Every transition is a compare-and-set under a lease; the resume budget is an attach, not a rebuild; the log outlives the socket.")

b.lane(30, 76, "RESUME — ~2 s FROM CACHE, ~5 s FROM OBJECT STORAGE, FALLBACKS ALWAYS AVAILABLE")
b.box(30, 90, 220, 72, "SUSPENDED → RESUMING", ["CAS on version · 30 s lease", "duplicate request → CAS fails"])
b.box(280, 90, 220, 72, "pick host by affinity", ["the one holding the snapshot", "unless > 85 % RAM"])
b.arrow((250, 126), (280, 126))
b.box(530, 90, 220, 72, "restore · reseed · attach", ["lazy pages 200 ms", "entropy · keys · NIC · mount"], cls='dg-good', tcls='dg-good-t')
b.arrow((500, 126), (530, 126))
b.box(780, 90, 200, 72, "→ READY", ["restored_memory: true", "client attach?after="], cls='dg-good', tcls='dg-good-t')
b.arrow((750, 126), (780, 126))
b.box(530, 176, 450, 44, "15 s → cold boot with overlay (packages kept) → then without it",
      cls='dg-warn', tcls='dg-warn-t')
b.arrow((640, 162), (640, 176))
b.hdiv(236, 20, 980)

b.lane(30, 270, "RUN A CELL — THE LOG OUTLIVES THE SOCKET")
b.box(30, 284, 220, 72, "exec {cell, exec_id}", ["kernel manager dedupes", "on exec_id"])
b.box(280, 284, 220, 72, "output → session log", ["seq · cell · stream · chunk", "Redis Streams via vsock"], cls='dg-good', tcls='dg-good-t')
b.arrow((250, 320), (280, 320))
b.box(530, 284, 220, 72, "gateway tails by seq", ["stateless · any gateway", "any session"])
b.arrow((500, 320), (530, 320))
b.box(780, 284, 200, 72, "client drops", ["execution continues", "reconnect: after=seq"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((750, 320), (780, 320))
b.box(280, 372, 220, 56, "cap → status: truncated", ["process keeps running"], cls='dg-warn', tcls='dg-warn-t')
b.box(530, 372, 220, 56, "blob → object storage", ["display event carries the URI"])
b.arrow((390, 356), (390, 372)); b.arrow((640, 356), (640, 372))
b.hdiv(446, 20, 980)

b.lane(30, 480, "SUSPEND AND ABUSE — THE REAPER DRIVES; CGROUPS CONTAIN; EGRESS LOGS CATCH")
b.box(30, 494, 290, 64, "IDLE → SUSPENDING", ["snapshot memory + overlay → upload", "CAS to SUSPENDED on ack · free RAM"])
b.box(350, 494, 290, 64, "budget missed (60 s)?", ["keep the overlay only", "has_memory: false"], cls='dg-warn', tcls='dg-warn-t')
b.arrow((320, 526), (350, 526))
b.box(670, 494, 290, 64, "fork bomb / miner", ["pid cap inside its own VM", "egress denied + logged → auto-suspend"], cls='dg-warn', tcls='dg-warn-t')
b.text(30, 590, "Three durability classes, said in one breath: files always · overlay kept and rebuildable · memory best-effort.", 'dg-note')

HLD_CAP = ("The top lane's last box is what the five seconds buys, and the warning strip under it is what makes "
           "the SLO an SLO rather than an availability claim. The middle lane is the ChatGPT page's run lifecycle "
           "with a cell in place of a generation: the socket carries nothing the log does not already have.")

# ---------------------------------------------------------------- skeleton
s = Board(450, "Sandboxed compute five-minute skeleton. The session state machine across the top; then the control plane, the data plane with microVMs and the GPU exception, and the warm pool; then suspend-to-snapshot, the itemised resume budget, and the three durability classes; then the isolation layers and the output log; and a margin lane of the signals and the blast-radius sentence.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 930, 44, "CREATING → READY ↔ RUNNING → IDLE → SUSPENDING → SUSPENDED → RESUMING → READY · DELETED · every transition a CAS on version, under a lease",
      cls='dg-good', tcls='dg-good-t', badge=1)
s.box(30, 128, 300, 64, "Control plane, per cell", ["API · scheduler · reaper · Postgres sessions", "decides; runs no code"], badge=2)
s.box(350, 128, 300, 64, "Data plane", ["Firecracker microVM per session · cgroups", "GPU = full VM, no suspend, its own SLO"], badge=3)
s.box(670, 128, 290, 64, "Warm pool", ["arrivals × cold-boot time · ~1 % of fleet", "replenished off the critical path"], badge=4)
s.box(30, 208, 300, 56, "Suspend-to-snapshot", ["idle = zero host RAM · resident tail = 7× fleet"], badge=5)
s.box(350, 208, 300, 56, "Resume budget", ["affinity → cache < 1 s → lazy 200 ms → attach ≈ 2 s"], badge=6)
s.box(670, 208, 290, 56, "Three durability classes", ["files always · overlay kept · memory best-effort"], badge=7)
s.box(30, 284, 460, 56, "Isolation layers", ["microVM · file agent · egress blocks 169.254.169.254 · no guest creds · reseed"], badge=8)
s.box(510, 284, 450, 56, "Output log", ["per-session seq → stateless gateway → attach?after=seq · cap · blobs by ref"], badge=9)
s.lane(30, 370, "IN THE MARGIN — SAID, NOT DRAWN")
s.box(30, 382, 220, 44, "resume p95 by path", ["cache · store · cold"], badge=10)
s.box(270, 382, 220, 44, "pool depth vs arrivals", ["the create SLO, an hour early"])
s.box(510, 382, 220, 44, "egress denials · CAS fails", ["abuse, and the machine absorbing"])
s.box(750, 382, 210, 44, "50 cells, 2 % blast radius", ["not one cluster"])

SKEL_CAP = ("Badge 1 is the machine and it goes on the board before any service; badge 3's label — a guest kernel "
            "per session — is the answer to the first follow-up; badge 7 is three promises in one sentence, and the "
            "word best-effort in it is the one the interviewer is listening for.")

PAGE = 'design-sandbox.md'
place(PAGE, 'architecture', a, ARCH_CAP, section='## 6 ', nth=0)
place(PAGE, 'flows', b, HLD_CAP, section='## 6 ', nth=0)
place(PAGE, 'skeleton', s, SKEL_CAP, after_heading='## 14 ')

BOARDS = 3
WARN = a.warn + b.warn + s.warn
