import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dgl import Board          # noqa: E402
from splice import place       # noqa: E402

PAGE = 'design-cursor.md'

# --------------------------------------------------------------------------
# §6 · the architecture — components, not steps. This is the board you draw
# first: services you could point at in production, stores that survive a
# restart, and the three paths that leave the editor.
# --------------------------------------------------------------------------
a = Board(776, "Cursor Tab architecture. A client tier holding the editor, a context assembler running on a worker thread, a local completion cache, ghost-text decorations and a file watcher. An edge tier with a regional edge doing cached auth and rate limiting, and an auth cache. An inference tier with a regional router, a GPU worker fleet running a small FIM model with continuous batching, a prefix KV cache in GPU memory, and a shared result cache in Redis holding hashed contexts and no user code. Below, an asynchronous indexing tier: index API, AST chunker, embedding service, a Merkle store and a vector index. Below that, a telemetry tier: event collector, a Kafka queue, and a warehouse.")
a.banner("Three paths leave the editor: one synchronous, budgeted at 200 ms; two asynchronous and off the hot path.")

a.group(20, 86, 210, 332, "CLIENT — THE EDITOR")
a.box(35, 118, 180, 40, "Editor / extension host", ["HTTPS, abortable"])
a.box(35, 170, 180, 56, "Context assembler", ["worker thread, ~10 ms"])
a.cyl(35, 238, 180, 54, "Completion cache", ["LRU · hash(context)"])
a.box(35, 304, 180, 40, "Ghost-text decorations")
a.box(35, 356, 180, 50, "File watcher", ["Merkle tree · .cursorignore"])
a.arrow((125, 158), (125, 170))
a.line((125, 226), (125, 238))
a.line((125, 292), (125, 304))

a.group(340, 86, 160, 178, "EDGE")
a.box(354, 118, 132, 72, "Regional edge",
      ["POST /completion", "auth + rate limit", "request coalescing"])
a.cyl(354, 202, 132, 50, "Auth cache", ["at the edge"])

a.group(610, 86, 370, 262, "INFERENCE")
a.box(625, 118, 150, 64, "Router", ["by region"])
a.cyl(795, 118, 170, 64, "Prefix KV cache", ["in HBM"])
a.box(625, 194, 340, 72, "Inference workers — GPU",
      ["small FIM model · continuous batching", "speculative decoding · single-shot"])
a.cyl(625, 278, 340, 58, "Shared result cache", ["Redis · hashed contexts, no user code"])
a.arrow((700, 182), (700, 194))
a.line((880, 194), (880, 182))
a.line((795, 266), (795, 278))

a.arrow((230, 140), (354, 140)); a.ctext(292, 132, "completion request", 'dg-lbl')
a.arrow((354, 166), (230, 166)); a.ctext(292, 190, "ghost text", 'dg-lbl')
a.arrow((486, 140), (625, 140)); a.ctext(555, 132, "routed by region", 'dg-lbl')
a.arrow((625, 166), (486, 166)); a.ctext(555, 190, "tokens", 'dg-lbl')

a.group(250, 430, 730, 180, "INDEXING — ASYNCHRONOUS, OFF THE HOT PATH")
a.box(268, 462, 170, 56, "Index API", ["POST /index", "Merkle diff"])
a.box(468, 462, 180, 56, "AST chunker", ["chunk on syntax bounds"])
a.box(678, 462, 180, 56, "Embedding service")
a.cyl(268, 540, 170, 56, "Merkle store", ["per repo, server-side"])
a.cyl(678, 540, 180, 56, "Vector index", ["keyed by content hash"])
a.arrow((438, 490), (468, 490)); a.arrow((648, 490), (678, 490))
a.arrow((353, 518), (353, 540)); a.arrow((768, 518), (768, 540))
a.arrow((215, 381), (240, 381), (240, 490), (268, 490))

a.group(250, 630, 730, 110, "TELEMETRY — WHAT THE NEXT MODEL IS TRAINED ON")
a.box(268, 662, 150, 56, "Event collector", ["POST /events", "batched"])
a.queue(448, 662, 160, 56, "Kafka", ["shown · accepted"])
a.cyl(638, 662, 150, 56, "Warehouse", ["retained chars"])
a.box(818, 662, 148, 56, "Offline eval", ["→ next model"])
a.arrow((418, 690), (448, 690)); a.arrow((608, 690), (638, 690)); a.arrow((788, 690), (818, 690))
a.arrow((966, 690), (988, 690), (988, 230), (965, 230))
a.arrow((125, 418), (125, 690), (268, 690))
a.text(20, 762, "Neither lower tier is allowed to make the top row slower. Tab reads the editor's own signals and its own local cache — never the vector index.", 'dg-note')

ARCH_CAP = ("The board to draw first, and the one an interviewer is looking for: components you could "
            "point at in production. Three arrows leave the client and only the top one has a latency "
            "budget — drawing the other two <em>below</em> it, in their own boxes, is how you say "
            "“off the hot path” without saying it.")

# --------------------------------------------------------------------------
# §6 · the hot path — the same system as a sequence, because the branches are
# where the economics live and an architecture board cannot show a branch.
# --------------------------------------------------------------------------
b = Board(838, "Tab completion hot path. Client column: keystroke, should-fire filter which suppresses twenty to forty percent, debounce, local context assembly in about ten milliseconds, a cache check whose hit renders ghost text at zero milliseconds, then a cancellable request. Server column: regional edge, then a small FIM model. A dashed box lists what the budget makes illegal: no retrieval service, no reranker, no large model. The response returns to the client, which renders ghost text only if the cursor has not moved.")
b.banner("200 ms, keystroke to ghost text. Every box below is downstream of that one number.")
b.lane(55, 78, "CLIENT — THE EDITOR, WHERE MOST OF THE WORK HAPPENS")
b.lane(550, 78, "SERVER")
b.vdiv(505, 90, 812)
b.ghost(550, 110, 420, 92, "NOT IN THIS PATH",
        ["no retrieval service · no reranker (100 ms on its own)",
         "no large model (≈350 ms just to prefill)",
         "the budget makes these illegal, not merely expensive"])
b.box(55, 100, 230, 34, "Keystroke")
b.arrow((170, 134), (170, 158))
b.box(55, 158, 230, 66, "Should-fire filter",
      ["in a comment? mid-identifier?", "just dismissed at this position?"])
b.arrow((285, 191), (310, 191))
b.box(310, 171, 175, 40, "suppress · never fires", ["20–40% of keystrokes"],
      cls='dg-warn', tcls='dg-warn-t')
b.arrow((170, 224), (170, 248))
b.box(55, 248, 230, 34, "Debounce ~30 ms")
b.arrow((170, 282), (170, 306))
b.box(55, 306, 230, 72, "Assemble context locally",
      ["prefix + suffix (FIM), recent edits", "open tabs, LSP symbols in scope"])
b.text(300, 336, "~10 ms · no network", 'dg-lbl')
b.text(300, 352, "2–4k token budget", 'dg-lbl')
b.arrow((170, 378), (170, 402))
b.box(55, 402, 230, 50, "Cache check", ["key = hash(assembled context)"])
b.arrow((285, 427), (310, 427))
b.box(310, 409, 175, 36, "HIT → ghost text at ~0 ms", cls='dg-good', tcls='dg-good-t')
b.arrow((170, 452), (170, 476))
b.box(55, 476, 230, 50, "Send request", ["requestId · abort any in-flight"])
b.ctext(415, 493, "one request, cancellable", 'dg-lbl')
b.arrow((285, 501), (550, 501))
b.box(550, 476, 420, 66, "Regional edge",
      ["auth + rate limit, cached at the edge", "coalesce duplicate in-flight requests"])
b.arrow((760, 542), (760, 566))
b.box(550, 566, 420, 80, "Inference — small FIM model",
      ["continuous batching · prefix KV cache · speculative decoding",
       "single-shot at ~30 tokens: no partial-render flicker"])
b.arrow((760, 646), (760, 676), (170, 676), (170, 700))
b.text(190, 668, "later than ~300 ms → drop it, never render stale", 'dg-note')
b.box(55, 700, 230, 50, "Render ghost text", ["only if the cursor hasn’t moved"])
b.arrow((170, 750), (170, 774))
b.box(55, 774, 230, 34, "Tab = accept · else dismiss")
b.arrow((285, 791), (550, 791))
b.box(550, 772, 420, 38, "Events, batched — acceptance + retained characters")
b.text(55, 830, "Server unavailable → fail silent. No toast, no per-keystroke retry: the editor must feel exactly like a normal editor.", 'dg-note')

HOT_CAP = ("The same system as a sequence, because the two branches are the economics and no "
           "architecture board can show a branch: the filter that suppresses a third of all "
           "keystrokes, and the cache that answers in zero.")

# --------------------------------------------------------------------------
# §6 · indexing, drawn apart on purpose
# --------------------------------------------------------------------------
c = Board(242, "Indexing pipeline, asynchronous and separate from the Tab hot path. Client side: a file watcher respecting .cursorignore feeds a Merkle tree of file hashes. Server side: a root-hash diff returns only the missing subtrees, an AST chunker splits on syntax boundaries, and chunks are embedded into a vector index keyed by content hash.")
c.banner("Indexing — a separate, asynchronous lifecycle. Tab never waits on it.", y=10, h=34)
c.lane(20, 68, "CLIENT"); c.lane(420, 68, "SERVER")
c.vdiv(400, 78, 158)
c.box(20, 88, 160, 56, "File watcher", ["respects .cursorignore"])
c.arrow((180, 116), (205, 116))
c.box(205, 88, 160, 56, "Merkle tree", ["of file hashes"])
c.arrow((365, 116), (420, 116))
c.box(420, 88, 170, 56, "Root-hash diff", ["→ missing subtrees only"])
c.arrow((590, 116), (620, 116))
c.box(620, 88, 160, 56, "AST chunker", ["chunk on syntax bounds"])
c.arrow((780, 116), (810, 116))
c.box(810, 88, 170, 56, "Embed → vector index", ["keyed by content hash"])
c.text(20, 182, "▸  A one-line change in a 100k-file monorepo uploads one chunk — that is the entire point of the Merkle diff.")
c.text(20, 204, "▸  Vectors are keyed by content hash, not file path, so identical code across branches and forks dedupes for free.")
c.text(20, 226, "▸  Local edits update a local index immediately; the server index catches up. Tab’s context never comes from here.")

IDX_CAP = ("Drawn beside the hot path, not inside it. If your board makes indexing look like a step in "
           "the completion flow you have designed the wrong system — say “separate lifecycle” out loud "
           "as you draw the gap between them.")

# --------------------------------------------------------------------------
# §14 · the skeleton
# --------------------------------------------------------------------------
s = Board(516, "Cursor Tab five-minute skeleton. A banner scoping to the 200 millisecond budget, then the QPS and waste figures, why the budget makes a RAG pipeline illegal, client-side context assembly, the should-fire filter, the three caches, the small FIM model and its serving stack, cancellation, indexing as a separate lifecycle, the privacy ladder, and the metrics that matter.")
s.banner("Minute five: everything below must be on the board. Badge numbers match the list.", y=10, h=34)
s.box(30, 68, 930, 40, "Four products, four budgets — scope to Tab at ~200 ms and let that constraint drive everything", cls='dg-good', badge=1)
s.box(30, 140, 460, 56, "~40 k QPS average, 100 k peak", ["80%+ of inference is wasted — the economic center"], badge=2)
s.box(510, 140, 450, 56, "The budget kills the RAG pipeline", ["rerank 100 ms alone · large-model prefill 350 ms"], cls='dg-warn', tcls='dg-warn-t', badge=3)
s.box(30, 216, 600, 64, "Context assembled client-side in ~10 ms", ["prefix/suffix (FIM) → recent edits → open tabs → LSP symbols → imports", "embeddings are the last resort, not the first"], badge=4)
s.box(650, 216, 310, 64, "Should-fire filter, before debounce", ["suppressing 20–40% beats any", "inference optimization"], badge=5)
s.box(30, 300, 460, 64, "Three caches", ["client (context hash) · server KV (prefix)", "shared results, containing no user code"], badge=6)
s.box(510, 300, 450, 64, "Small FIM model, trained on edits", ["continuous batching · prefix KV cache", "speculative decoding · regional routing"], badge=7)
s.box(30, 384, 300, 50, "Cancellation frees the slot", ["it is the common path"], badge=8)
s.box(350, 384, 300, 50, "Indexing is separate", ["Merkle diff · Tab never waits"], badge=9)
s.box(670, 384, 290, 50, "Privacy ladder", ["Tab is unaffected by privacy mode"], badge=10)
s.box(30, 454, 930, 44, "Metrics: acceptance rate · retained characters (acceptance is gameable) · the latency-vs-acceptance curve", badge=11)

SKEL_CAP = ("Eleven marks, and badge 3 is the one that wins the round: price the RAG pipeline out loud "
            "rather than asserting it away. At 200 ms a reranker is illegal, not merely expensive.")

place(PAGE, 'architecture', a, ARCH_CAP, after_heading='## 6 ')
place(PAGE, 'hot-path', b, HOT_CAP)
place(PAGE, 'indexing', c, IDX_CAP)
place(PAGE, 'skeleton', s, SKEL_CAP)

BOARDS = 4
WARN = a.warn + b.warn + c.warn + s.warn
