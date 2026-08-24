# Design Figma — Multiplayer Design Editor

**Archetype:** concurrent mutation of one shared document, where the choice of data model *is* the choice of concurrency algorithm.
**Cousins that reuse ~70% of this page:** Miro, Canva, Framer, Lucidchart, a collaborative spreadsheet, a multiplayer level editor. Also **any product where several people mutate one identified object graph** rather than appending to a stream.

**What's actually being graded:** whether you notice that **the document model determines the algorithm**, and design the model first. Modelling the file as `Map<ObjectID, Map<Property, Value>>` is what lets last-writer-wins per property be sufficient; modelling it as a sequence is what forces you into OT or a sequence CRDT. Candidates who open with "OT versus CRDT" have answered the Google Docs question. The second signal is that **the client is a renderer with a frame budget, not a view** — a design where the client is a thin layer over the server has answered half the problem, and it is the half this product is famous for.

**Contrast to have ready:** *WhatsApp is append-only: messages are immutable, delivery and ordering are the whole problem, and fanout cost dominates. Figma is the inverse — **delivery is easy and convergence is the problem**. Every client mutates the same objects, nothing is immutable, and the correctness invariant is not "everyone saw the same order" but "everyone ends in the same state." That is a strictly weaker requirement, and exploiting it is the design.*

---

## 0 · The 60-second frame (say this before you draw anything)

> "Figma is several products sharing one document — canvas editing, presence and cursors, comments, components and shared libraries, prototyping, plugins. I'd like to scope to **multiplayer canvas editing plus presence**, because that's where the interesting constraint lives. Two things dominate. First, **the shape of the document decides the concurrency algorithm**: if I model a file as a map of identified objects each holding a property bag, then two people editing different properties of the same object never conflict, and I can resolve the rare real conflict with last-writer-wins per property instead of building operational transforms. Second, **the client is a renderer, not a view** — a real file is hundreds of thousands of objects and the browser's own layout engine cannot paint that at sixty frames a second, so the client owns a scene graph and a GPU pipeline, and the sync engine has to feed it without ever blocking a frame. I'll go deep on the concurrency model and on sibling ordering, which looks like a detail and is the part that actually breaks."

**Why open this way:** it names the product rather than the category, it pre-commits the two dives that carry the round, and it forecloses the interviewer's most likely steer — a generic "so, CRDTs?" — by having already said something more specific than the answer they were fishing for.

---

## 1 · Functional requirements

1. **Several users edit the objects in one file at the same time, and all of them converge** to the same document.
2. **Each user sees the others' cursors and selections** as they move.
3. **A user who drops offline and reconnects rejoins the file** without losing acknowledged work and without a manual merge.

**Out of scope (say them):** comments, prototyping, plugins, components and shared libraries, permissions and org administration, export and rendering to image, version history.

**Below the line, likely follow-ups:** multiplayer undo (§13), branching and merging, offline for hours rather than seconds, the plugin sandbox, and text — which is genuinely a different problem and the one place a sequence algorithm is unavoidable (§15).

---

## 2 · Non-functional requirements

| Property | Target | Why this number |
|---|---|---|
| **Local edit → local paint** | **< 16 ms, always** | One frame at 60 Hz. **The network is never on this path.** This is the requirement that forces optimistic local application and a client-owned renderer |
| Local edit → remote paint | p50 < 100 ms, p95 < 250 ms | Past ~250 ms collaborators start taking turns instead of working simultaneously — the product stops being multiplayer in the way that matters |
| **Convergence** | **Guaranteed, with no user-visible merge step** | The correctness invariant. Note it is *convergence*, not linearizability — see the sentence below |
| Durability | An **acknowledged** edit survives loss of any single server | Unacknowledged edits stay the client's problem and are replayed on reconnect (§6 Flow A) |
| Presence freshness | Cursor position no older than ~100 ms; **lossy is fine** | A dropped cursor frame is invisible; a dropped property edit is data loss. Different guarantees, therefore §7's split |
| File open | **First meaningful paint < 3 s** on a large file | Beyond that the product feels like a desktop app launching, which is the thing it exists not to be |
| Availability | Editing **degrades to local-only**; the canvas never freezes | A frozen canvas is worse than a stale one. §11 |
| Concurrency per file | 1–10 simultaneous editors typical, tail into the hundreds of viewers | Small. **The server is not throughput-bound** — see §3 |

**The sentence that earns the point:** *"The invariant here is convergence, not linearizability. I don't need every client to observe the same order of events — I need them all to end in the same state. That's a much weaker requirement than a transactional system, and the entire design is an exercise in spending that slack."*

---

## 3 · Numbers that reframe the problem

**The document is small by database standards and enormous by browser standards**

- *Assumption:* a complex production file is **10⁵–10⁶ objects**, each carrying on the order of **30–100 properties**. Take 200k objects × 50 properties ≈ **10 million property values** in one file.
- At ~200 bytes per object of live state that is **~40 MB resident** for a single open file.
- **This is the number that kills "send the document as JSON on open"** — 40 MB over a 20 Mbit connection is roughly **16 seconds** before the client has parsed anything. §10 exists because of this figure.

**The edit rate is trivially small, and that is the surprise**

- A user dragging one object emits a property update **per frame**: ~60 updates/second.
- Five people dragging simultaneously in the same file is **~300 document updates/second** — for the *whole file*.
- **Say this comparison out loud:** a server that would be considered idle at 300 writes/second is nonetheless the bottleneck here, because the constraint is not write throughput. It is **connections, memory, and ordering authority per file**. That reframing is what moves you off a generic stateless-services answer and onto §11.

**Presence traffic dwarfs document traffic, which is why they are different channels**

- 10 users, each broadcasting cursor position at 60 Hz, fanned out to the other 9: **~5,400 messages/second** for one file's presence.
- The same file's document edits in the same second: a few hundred at most, and usually zero.
- **Presence is the volume. Document edits are the correctness.** One is lossy, unordered, and never persisted; the other is durable and ordered. Designing them as one channel with one guarantee means paying persistence costs on cursor movement — trap #3 in §13.

**Server memory is the real capacity limit**

- 40 MB resident per open file × **10,000 concurrently open files ≈ 400 GB**.
- *This is a product choice, not a derivation:* holding the document in memory in a single owning process is what makes ordering free (§11). The 400 GB is what that choice costs, and it is why files are evicted the moment the last client disconnects.

---

## 4 · Core entities

- **File** — id, team id, current version (a monotonic sequence number the server assigns)
- **Object** — `ObjectID`, type (`FRAME`, `RECTANGLE`, `TEXT`, …), and a map of properties
- **Property** — `(ObjectID, key)` → value, plus the version at which the server last accepted it
- **Change** — `(ObjectID, key, value)` plus the originating client id and that client's own sequence number
- **Session** — a connected client: user, socket, cursor, selection, and the last version it has acknowledged

**The three that are load-bearing:**

**The `Property` is the unit of conflict — not the `Object`, not the file.** Two people restyling the same rectangle, one changing the fill and one the corner radius, never conflict at all. This is the single decision the whole page rests on, and it is a consequence of the data model rather than of any clever algorithm.

**Parent and sibling position are stored as one atomic property, not two.** If "which frame am I in" and "where among my siblings" are separate properties, a concurrent move can land one and not the other, and the object appears in a frame at a position that means nothing. §8.

**`ObjectID` is generated by the client, not the server.** Creating a rectangle cannot cost a network round trip — the 16 ms budget in §2 forbids it — so ids are client-minted and globally unique (client id plus a local counter is sufficient and cheaper than a UUID).

---

## 5 · API

One WebSocket per client per open file. Both document changes and presence ride it; only one of them is durable.

```ts
// ---- client → server ----
{ t: 'hello',   fileId: string, sinceVersion: number | null }
{ t: 'set',     objectId: string, key: string, value: Value, clientSeq: number }
{ t: 'create',  objectId: string, props: Record<string, Value>, clientSeq: number }
{ t: 'cursor',  x: number, y: number, selection: string[] }        // not persisted, not acked

// ---- server → client ----
{ t: 'snapshot', url: string, version: number }                   // an S3/CDN blob, not inline
{ t: 'ack',      clientSeq: number, version: number }
{ t: 'set',      objectId: string, key: string, value: Value, version: number, by: string }
{ t: 'presence', clientId: string, x: number, y: number, selection: string[] }
{ t: 'bye',      clientId: string }
```

**Decisions to narrate, unprompted:**

- **Granularity is the property.** Sending whole objects would make two people styling one rectangle conflict for no reason; sending whole documents is absurd at 40 MB. The message is the smallest unit that can independently conflict, which is exactly the unit §4 identified.
- **`clientSeq` exists so the client can match an ack to its own pending edit** and know which of its optimistic values are now confirmed. It is not an ordering mechanism — the server's `version` is.
- **`hello` carries `sinceVersion`, not the document.** Reconnect is "catch me up from here," and only falls back to a fresh snapshot when the server can no longer serve that far back (§6 Flow B).
- **`cursor` has no ack and no version.** It is deliberately the only unreliable message in the protocol, and saying so pre-empts the "how do you scale presence" question with a better answer than sharding.
- **`create` is a client-minted id plus properties**, so a new object paints in the same frame the user drew it.

---

## 6 · High-level design — flows

```text
   ┌────────── client ──────────┐                    ┌──────── server ────────┐
   │  input → scene graph       │                    │  file process (§11)    │
   │        ↓            ↑      │   WebSocket        │   in-memory document   │
   │  local apply    renderer   │ ◄────────────────► │   version counter      │
   │        ↓         (WebGL)   │   set / ack / set  │   socket set for file  │
   │  pending queue             │                    └───────────┬────────────┘
   └────────────────────────────┘                                │
                    ▲                                            ▼
              snapshot (CDN)  ◄───────── periodic ──────── op log (durable)
```

### Flow A — a local edit, and the conflict it might hit

1. User drags a rectangle. The client applies `x = 240` to its **local** scene graph and paints it **this frame**. No network on this path (§2).
2. The change goes into a **pending queue** keyed by `(objectId, key)` and is sent as `set` with the next `clientSeq`.
3. The file's owning process receives it, assigns the next `version`, writes it to the in-memory document, and appends it to the durable op log (§12).
4. It broadcasts the change to every other socket it owns and returns `ack` to the sender.
5. Remote clients apply it to their scene graphs and paint on their next frame.
6. **The conflict case.** While the drag is in flight, another user sets `x = 700` on the same rectangle and the server orders theirs after. The dragging client receives `set x = 700` for a property it has an *unacknowledged* local value for, and **discards it**. Otherwise the shape being dragged would jump out from under the cursor and snap back — visibly broken, every frame.
7. **The failure path.** The socket dies mid-drag. The client keeps painting its optimistic value and keeps the pending queue. On reconnect it replays the queue; because entries are keyed by `(objectId, key)` and carry only the final value, a thousand dragged frames replay as **one** message. If the server has since accepted someone else's value and orders the replay first, the *other* user's value wins and this user's rectangle jumps. **That is correct and worth saying out loud:** last-writer-wins means someone loses, the design's job is to make sure it is never ambiguous *who*, not to prevent it (§7).

### Flow B — opening a file

1. Client connects and sends `hello` with `sinceVersion: null`.
2. Server responds with `snapshot`: a URL to an **immutable blob in object storage, served from the CDN**, plus the version that blob represents.
3. Client fetches and decodes the snapshot off the main thread, building the scene graph progressively and painting what is in the viewport first (§9, §10).
4. Server streams the op tail — every change since the snapshot version — which the client applies on top.
5. The file is live. Total: first paint well before the tail finishes.
6. **The failure path.** A reconnecting client sends `sinceVersion: 41200` and the server's retained tail no longer reaches back that far (compaction ran, or the process failed over and restarted from a snapshot). The server does not try to reconstruct: it responds with a fresh `snapshot` and the client discards local state **except its pending queue**, which it replays. **Degrading to a full reload is the correct answer here** — the alternative is an unbounded op log kept alive for one absent client.

### Flow C — presence

1. Client sends `cursor` on pointer move, coalesced to at most one per frame.
2. The owning process fans it out to the file's other sockets and stores nothing.
3. Remote clients interpolate between received positions so a 60 Hz stream renders smoothly at any frame rate.
4. **The failure path.** A client vanishes without a clean close. Its socket's read times out, the process removes the session and broadcasts `bye`; any client that missed the `bye` expires the cursor on a local TTL anyway. **Nothing is retried and nothing is persisted** — a lost cursor frame is invisible, which is exactly why presence gets a different guarantee from `set` (§3).

---

## 7 · Deep dive — why not OT, and why not a real CRDT

**The naive answer.** "Collaborative editing means Operational Transformation — Google Docs does it, so transform each incoming operation against the concurrent ones the client has already applied."

**What breaks.** OT requires a transformation function for **every ordered pair of operation types**. With a rich object model — set property, create, delete, reparent, reorder, group — that is quadratic in the number of operation types, and the functions are individually subtle. Figma's own writeup is blunt about it: OTs were *"unnecessarily complex for our problem space"* and *"very complicated and hard to implement correctly."* The deeper point is that **OT is machinery for editing a sequence**, where an insert at position 4 changes what position 7 means. Setting `fill` on object `abc` does not change what any other property means. **You would be paying for a problem you designed away in §4.**

**What replaces it.** **Last-writer-wins per property, with a single server process as the ordering authority.** The server keeps the latest value any client has sent for a given property on a given object; the order of arrival at that process *is* the order, so there is nothing to transform. Figma describes their system as CRDT-*inspired* while stating plainly that *"Figma isn't using true CRDTs"* — because the server is central, they drop the vector clocks, tombstone sets, and merge functions a decentralised CRDT needs to converge without a coordinator.

**What it costs.**

- **Last write wins means someone silently loses.** Two users setting `fill` concurrently: one value survives and the other disappears with no conflict UI and no merge. That is acceptable for `fill` and *unacceptable* for a paragraph of text, which is precisely why text is the one place this model does not stretch (§15).
- **You have given up decentralisation.** No peer-to-peer, no true offline-for-a-week merge, no federating between servers — every edit to a file must reach one process. §11 is the bill for this, and it is the reason the file process is a single point of failure.
- **Ordering is per file, not global.** Two files are wholly independent, which is fine, but any feature spanning files (a shared component library) cannot be made atomic with an edit. Worth naming before they ask.

---

## 8 · Deep dive — sibling ordering, which looks like a detail

Draw the interviewer's attention here yourself. It is where a design that seemed finished falls over, and getting it right is a strong signal because most candidates never reach it.

**The naive answer.** "Each object stores its index among its siblings — the parent holds an array of child ids, or each child holds an integer position."

**What breaks — two distinct failures, and both are load-bearing.**

1. **Concurrent inserts collide.** Two users each drop a layer at index 3. With the parent's child array modelled as one property, LWW means one user's entire insert vanishes — the array they didn't write is the array that survives. With per-child integer positions, both children claim index 3 and the order is undefined.
2. **A single drag becomes an O(n) write.** Moving one layer from the bottom of a 200-object frame to the top renumbers every sibling. That is 200 property writes broadcast to every client for one user gesture, and every one of them is an independent LWW race.

**What replaces it.** **Fractional indexing.** An object's position among its siblings is a fraction strictly between 0 and 1. To insert between two objects, average their indices; to insert at the start or end, average with 0 or 1. There is always room, because there is always a rational number between two rationals. A drag writes **exactly one property** — the moved object's — and touches nothing else.

Two implementation details worth stating because they are where it actually goes wrong:

- **Not a 64-bit float.** Repeated insertion at the same point halves the gap each time and exhausts double precision in about fifty operations. Figma stores the index as an **arbitrary-precision fraction encoded as a string**, averaged by string manipulation, and compacts it by dropping the leading `0.` and using the full printable ASCII range — **base 95 rather than base 10**.
- **Parent and position are one atomic property.** If they are two, a concurrent move can land the new parent and lose the new position, and the object appears in the right frame at a meaningless place. Storing them together makes a move a single indivisible LWW write.

**What it costs.**

- **Index strings grow.** Every insertion between the same two neighbours adds roughly a character. Sustained editing in one spot produces long keys, so you need a **renormalisation pass** that rewrites a parent's children back to short evenly-spaced indices — and because that is a multi-property write that must not interleave with concurrent edits, the server has to perform it, not a client.
- **Interleaving is arbitrary.** Two users inserting at the same position get a deterministic, convergent order — but not necessarily the one either intended. Figma's own justification for accepting this is that a layers panel is not prose: nobody is harmed if two simultaneously-added rectangles land in the other order. Say that trade explicitly; it is the same trade §7 made, one level down.
- **Cycles are now possible.** Since parenting is just a property, two users can concurrently reparent A into B and B into A, producing a cycle that detaches a whole subtree from the document. **The server rejects parent updates that would create one** — the same check a candidate writes by walking parent pointers, enforced at the ordering authority because that is the only place with a consistent view.

---

## 9 · Deep dive — the client is a renderer, not a view

**The naive answer.** "It's a web app, so the canvas is DOM or SVG nodes and a framework diffs them when state changes."

**What breaks.** §3 put a real file at 10⁵–10⁶ objects. A browser's style, layout, and paint pipeline is roughly linear in node count per frame, and the practical ceiling for a smooth 60 Hz is **low thousands of nodes**, not hundreds of thousands — you are over budget by two orders of magnitude before anything animates. Worse, the failure is not gradual: one style recalculation that exceeds **16 ms** drops a frame during a drag, which is the single most-used interaction in the product.

**What replaces it.** The client owns a **scene graph and its own rendering pipeline**: geometry is submitted to the GPU through **WebGL**, with the hot path compiled to **WebAssembly** rather than run as JavaScript, so a frame's work is bounded by what is *visible* rather than by what exists. The essential techniques are viewport **culling** (touch only objects intersecting the visible rectangle) and **tiling** (cache rendered regions so panning re-composites rather than re-rasterises). The DOM keeps the chrome — panels, menus, inputs — and nothing else.

**What it costs.** This is the expensive answer and you should price it honestly:

- **You reimplement everything the browser gave you free**: text shaping and line breaking, IME composition for non-Latin input, hit testing, selection, focus, scrolling, and accessibility. Each of these is a project.
- **A large WebAssembly binary must be downloaded and instantiated before the first pixel**, which lands directly on §2's 3-second open budget and pulls against §10.
- **Debugging leaves the browser's tooling behind.** DevTools can show you a dropped frame; it cannot show you which node in your scene graph caused it, so you build your own instrumentation.
- **Memory is now yours to bound.** Tile caches and GPU textures grow with document size and zoom level, and evicting them badly produces visible re-rasterisation during a pan.

---

## 10 · Deep dive — opening a large file without a sixteen-second stall

**The naive answer.** "On open, the server serialises the current document and sends it down the socket."

**What breaks.** §3's figure: ~40 MB, which is **~16 s** on a 20 Mbit connection before the client parses a byte — and the parse itself blocks the main thread, so the tab is frozen for the tail of it. It is also the worst possible load pattern for the server: the file's owning process must serialise its whole in-memory document on demand, on the same thread that is ordering live edits, every time anyone opens the file.

**What replaces it.** Split the document into **an immutable snapshot plus a tail of operations.**

- A background job periodically writes the file's state at version *V* as an **immutable blob to S3**, keyed `file/{id}/{V}`, and serves it through a **CDN (Fastly or CloudFront)**. Immutable plus content-addressed means it is infinitely cacheable and never invalidated.
- On open, the server sends a **URL and a version**, not bytes. The client fetches from the CDN — usually a nearby edge — decodes **off the main thread in a worker**, and the owning process does no serialisation work at all.
- The server then streams only the operations **since** *V*. Reconnects reuse the same mechanism with a version the client already has, so the common case transfers almost nothing.
- The client builds the scene graph progressively and **paints the viewport first**, so first meaningful paint happens long before the document is fully resident.

**What it costs.**

- **Two sources of truth to keep consistent.** A snapshot and an op log can disagree if the snapshotter reads a torn state, so it must snapshot at a version boundary, not at a wall-clock instant.
- **Tail length is unbounded if snapshotting lags.** A heavily-edited file whose snapshot job is behind makes every open replay a huge tail — so snapshot cadence is driven by **ops since last snapshot**, not by time.
- **Compaction has to retire old snapshots and old log segments**, and every retirement is a version below which reconnects can no longer be served incrementally and must take a full reload (§6 Flow B's failure path).
- **A stale CDN edge serving a superseded snapshot is harmless only because blobs are immutable** — the moment you make a snapshot URL mutable, this whole dive becomes a cache-invalidation problem instead.

---

## 11 · Deep dive — server topology: one process per open file

**The naive answer.** "Stateless application servers behind a load balancer, with document state in Redis and fanout over a pub/sub channel." It is the reflexive answer and it is wrong here in an instructive way.

**What breaks.**

- **Ordering.** LWW needs *somebody* to decide which write is last. With N stateless servers, every property write becomes a read-modify-write against shared state and needs a lock or a compare-and-set **per property**, on a path where §2 allows 100 ms end to end.
- **Latency.** Client → app server → pub/sub broker → app server → client adds two network hops to every message, including the 5,400 presence messages per second per file from §3. You spend the remote-paint budget on hops that exist only because the state is somewhere else.
- **Cost shape.** Redis would be holding 40 MB per open file (§3) and serving property-level reads and writes for it — you have paid for a distributed store and are using it as one process's heap.

**What replaces it.** **A single authoritative process per open file.** A registry in **Redis** maps `fileId → server`, with a heartbeat TTL, and a router directs every connection for a file to its owner (consistent hashing gives a stable default; the registry handles the exceptions). That process holds the document in memory, orders operations **by arrival**, appends them to the durable log, and fans out to the sockets **it already owns** — no broker, no lock, no coordination. Ordering becomes free because there is exactly one place where order can be defined.

**What it costs.** This is the trade to state plainly rather than let them find:

- **It is a single point of failure per file.** Recovery is: detect via the heartbeat, elect a new owner, rehydrate from the last snapshot plus the op log, and let clients reconnect with `hello`. Unacknowledged client edits replay. **The file is unavailable for the length of that rehydration** — seconds — and the honest answer is that this is acceptable because it is per file and rare, not because it doesn't happen.
- **There is no horizontal escape hatch for one file.** A file with a thousand simultaneous viewers cannot be split across processes without reintroducing the ordering problem. The mitigation is asymmetric: viewers can be served by **read-only relay processes** that subscribe to the owner's output and never write, which scales fanout without touching ordering.
- **Memory becomes the capacity planning unit** (§3's 400 GB), and eviction policy — drop the document when the last client disconnects — becomes load-bearing rather than housekeeping.

---

## 12 · Data model, sharding, and storage decisions

**Partition key: `fileId`.** Everything — the op log, the snapshot keyspace, the session registry, the routing decision — keys on it. A file is the unit of ordering (§7), so it is the only partition boundary that doesn't reintroduce coordination.

**The hot shard is a single enormously collaborative file, and it is intentional.** No partition scheme fixes it, because splitting one file across owners is precisely what §11 refused. The mitigation is read-only relay processes for viewers; the residual risk is a file with hundreds of simultaneous *editors*, which is rare enough to accept and worth naming as accepted rather than solved.

| Component | Access pattern | Durability | Choice | The one sentence you'd say |
|---|---|---|---|---|
| **Live document** | Random property read/write, 100s/s, one writer | **None on its own** | **In-process memory** in the file's owning server | *"The document lives in the heap of the one process that owns the file — that's what makes ordering free, and the op log is what makes it durable."* |
| **Op log** | Append-only, ordered per file; read on recovery and reconnect | **The system of record** | **Kafka**, partitioned by `fileId` — a partition gives per-file order for free. At lower volume, a Postgres append-only table with a per-file sequence is simpler and sufficient | *"Ordering per file is exactly a Kafka partition's guarantee, so I get the ordering I need without a global log."* |
| **Snapshots** | Written by a background job, read once per cold open, immutable | Durable, replaceable | **S3** with keys `file/{id}/{version}`, fronted by **Fastly** or **CloudFront** | *"Immutable and content-addressed, so it's infinitely cacheable and there's no invalidation story to get wrong."* |
| **File metadata, teams, permissions** | Relational, read-heavy, low volume | Durable, transactional | **Postgres** with read replicas | *"It's relational and small — this is the one part of the system that's an ordinary CRUD app, and pretending otherwise would be the mistake."* |
| **Session / ownership registry** | `fileId → server`, written on open, read on every connect | **Ephemeral** — rebuilt from heartbeats | **Redis** with a heartbeat TTL per owner | *"TTL'd registry, so a dead owner ages out on its own rather than needing a reaper."* |
| **Presence** | Write 60 Hz per user, fan out, never read back | **None, by design** | **Not stored** — in-memory in the owning process, TTL-evicted | *"Presence is the highest-volume thing in the system and the only thing I'm willing to lose, so it never touches disk."* |
| **Asset blobs** (images, fonts) | Write once, read many, large | Durable | **S3** + CDN, referenced from properties by content hash | *"Properties hold a hash, not bytes — so an image drop is one small property write plus an independent upload."* |

---

## 13 · Traps — the ranked list

**Design traps**

1. **Opening with "OT versus CRDT" and never designing the document model.** The model is the answer; the algorithm falls out of it (§7). This is the single most common way to answer the wrong question well.
2. **A thin client.** If the client is a view over server state, you have not built this product. The renderer is half the system and it is the half with the hard budget (§9).
3. **One channel, one guarantee.** Persisting cursor movements, or acking them, costs you the volume in §3 for no benefit.
4. **Z-order as array indices.** Two bugs at once — vanished concurrent inserts, and O(n) writes per drag (§8).
5. **Server-assigned object ids.** A round trip inside a 16 ms budget (§4).
6. **Waiting for the server before painting.** Every edit is optimistic; the network is never on the local paint path (§2).
7. **No reconnect story.** Unacknowledged edits must be replayable and idempotent, and the pending queue must be keyed so a thousand drag frames replay as one message (§6 Flow A).
8. **Pretending LWW never loses data.** It does, silently. The design's job is to make the loser unambiguous, not to prevent loss (§7).
9. **Multiplayer undo answered as a stack.** Undo must revert **your own** last change, not the document's — a shared stack means undoing a colleague's work. Naming it as a genuinely hard sub-problem scores; hand-waving it as "just a stack" is a visible tell.

**Performance traps**

10. **Sending the document on open** (§10).
11. **Broadcasting every dragged frame to every viewer unthrottled** — coalesce to one message per property per frame, server-side as well as client-side.
12. **Rebuilding the scene graph on incoming changes** instead of mutating the affected nodes; the whole point of object identity is that an update touches one node.
13. **Snapshotting on a timer rather than on operation count** — the file that needs snapshots most is the one a timer serves worst (§10).

---

## 14 · The five-minute skeleton (draw this cold)

1. **Document model, first and biggest:** `Map<ObjectID, Map<Property, Value>>`. Say that the property is the unit of conflict.
2. **Client:** input → local apply → scene graph → WebGL renderer. Mark the **16 ms** budget on the local loop.
3. **Pending queue** on the client, keyed `(objectId, key)`, holding unacknowledged values.
4. **One WebSocket** to **one file process**. Label it *the ordering authority*.
5. **Registry** (Redis, `fileId → server`, heartbeat TTL) between the client and that process.
6. **Op log** (Kafka, partitioned by `fileId`) hanging off the file process — the system of record.
7. **Snapshot job** → S3 → CDN, and an arrow from the CDN back to the client for cold open.
8. **Presence** as a separate arrow through the same socket, drawn dashed, labelled *lossy, unordered, never stored*.
9. Write **fractional index** next to the object box, and **LWW per property** next to the file process.
10. In the corner, the two decisions: *"convergence, not linearizability"* and *"the model chose the algorithm."*

---

## 15 · Variants — what actually changes

**The governing axis: what the shared data structure is.** Everything else follows from it, including which algorithm you are forced into and what "conflict" even means.

| Product | Shared structure | Concurrency algorithm | The delta from this page |
|---|---|---|---|
| **Figma, Miro, Canva** | Map of identified objects → property bags | **LWW per property**, central ordering | This page as written |
| **Google Docs, a code editor** | A **sequence** of characters | **OT or a sequence CRDT** (RGA, Logoot) — unavoidable, because an insert changes what every later position means | §7 flips entirely. Interleaving now matters enormously: two people typing in one paragraph must not shuffle characters, which is exactly the harm §8 was willing to accept |
| **Notion** | A **tree of blocks**, each containing a sequence of text | **Both.** LWW per block property, a sequence algorithm inside text, fractional indexing between blocks | The most instructive hybrid: it shows the choice is per-field, not per-product |
| **A collaborative spreadsheet** | Map of cells **plus a formula dependency graph** | LWW per cell, plus **recompute of the dependency closure** | Adds a derived-state problem this page doesn't have: convergence of inputs no longer implies convergence of outputs unless recomputation is deterministic |
| **A multiplayer level or CAD editor** | Map of objects, but with **geometric constraints between them** | LWW per property, plus **constraint solving** | Property-level LWW can produce a document that converges and is *invalid* — two users each satisfying one constraint. Introduces validation as a first-class server concern |
| **A single-player editor with sync** | Same map, but **one writer at a time** | No algorithm at all — last device to save wins | Collapses §7, §8, and §11 into a version number. Useful to state, because it isolates what multiplayer actually costs |
| **Layered configuration** (IDE settings) | **No shared structure at all** — several separately-owned documents merged at read time | A precedence function, not a merge algorithm | The inverse of this page, and **its own page — see IDE settings sync**. Nobody writes the same document, so there is no convergence problem; what's called a conflict is an unwritten precedence rule |

---

## 16 · Active recall — answer these cold, no scrolling

1. Why is convergence a weaker requirement than linearizability, and what specifically does the design buy with the slack? → §2
2. What is the unit of conflict, and what would break if it were the object instead? → §4
3. Why must `ObjectID` be minted by the client? → §4
4. Give the two reasons OT is the wrong tool here — one about the algorithm, one about the data model. → §7
5. In what sense is this "not a true CRDT," and what does the server's centrality let you delete? → §7
6. Two users concurrently set `fill` on one rectangle. Precisely what happens, and what is lost? → §7
7. Name the two independent failures of storing sibling order as array indices. → §8
8. Why is a 64-bit float an inadequate fractional index, and what is used instead? → §8
9. Why are parent and sibling position stored as a single property? → §8
10. Where do ordering cycles come from once parenting is just a property, and who rejects them? → §8
11. Roughly how many DOM nodes can be painted at 60 Hz, and how far is a real file from that? → §9
12. Name three things the browser gives you free that a custom renderer has to rebuild. → §9
13. Why does open return a URL rather than bytes, and why must the snapshot be immutable? → §10
14. Why is snapshot cadence driven by operation count rather than elapsed time? → §10
15. Give the three specific reasons stateless servers plus Redis is the wrong topology. → §11
16. A file's owning process dies mid-edit. Walk the recovery, and say what the user sees. → §11
17. Presence and document edits ride the same socket. Name every guarantee that differs between them. → §3, §5
18. Why is multiplayer undo not a stack? → §13
