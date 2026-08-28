# Design Figma — Multiplayer Design Editor

## The question

> *"Design Figma. A design tool that runs in the browser, where several people can edit the same file at the same time and watch each other's cursors move."*

**The product.** A design file is a canvas of shapes, frames, text, and reusable components — an object graph you drag around, not a document you type into. Several designers open the same file, move things, resize things, and change colours, and each of them sees everyone else's changes land live, along with a labelled cursor for each person. It runs in a browser tab and has to stay smooth with thousands of objects on screen, on a laptop, over a wifi connection that occasionally stalls.

**What a working system delivers**

- Two people dragging two different rectangles both land immediately, on both screens.
- Two people dragging the *same* rectangle end up looking at the same result — one file, not two divergent versions.
- The canvas keeps its frame rate while all of that is arriving.
- A network stall doesn't freeze your editing; you keep working and it reconciles when you're back.

**Why this gets asked.** Delivery is the easy half here — everyone is online, looking at one document. *Agreement* is the problem, and how hard agreement turns out to be is decided by a modelling choice made in the first two minutes of the round.

---

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

<div class="diagram" data-board="architecture">
<svg viewBox="0 0 1000 530" role="img" aria-label="Figma architecture. A client holding a scene graph, a WebGL renderer and a pending queue. A Redis registry mapping file id to the server that owns it, on a heartbeat TTL. A file-process tier, one process per open file, holding the in-memory document and acting as the ordering authority. Below it a Kafka op log partitioned by file id, a snapshot job writing immutable blobs to S3 behind a CDN, and Postgres for files, teams and permissions.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">One process owns one file. Everything keys on fileId — the registry, the op log, the snapshot keyspace, the routing decision.</text>
  <rect class="dg-group" x="20" y="86" width="210" height="180" rx="12"></rect>
  <text class="dg-group-t" x="36" y="108">CLIENT</text>
  <rect class="dg-box" x="36" y="118" width="178" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="125" y="150.5">Scene graph + renderer</text>
  <rect class="dg-box" x="36" y="190" width="178" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="125" y="214.5">Pending queue</text>
  <text class="dg-s dg-c" x="125" y="230.5">keyed (objectId, key)</text>
  <path class="dg-box" d="M 280,157 L 280,199 A 100,7 0 0 0 480,199 L 480,157 A 100,7 0 0 0 280,157 Z"></path>
  <path class="dg-box" d="M 280,157 A 100,7 0 0 0 480,157" style="fill:none"></path>
  <text class="dg-t dg-c" x="380" y="178">Registry — Redis</text>
  <text class="dg-s dg-c" x="380" y="194">fileId → server, TTL</text>
  <path class="dg-line" d="M 230,178 L 272,178"></path>
  <path class="dg-head" d="M 272,183 L 272,173 L 280,178 Z"></path>
  <text class="dg-lbl dg-c" x="255" y="198">lookup</text>
  <rect class="dg-group" x="540" y="86" width="440" height="140" rx="12"></rect>
  <text class="dg-group-t" x="556" y="108">FILE PROCESSES — ONE PER OPEN FILE</text>
  <rect class="dg-box" x="556" y="118" width="410" height="90" rx="8"></rect>
  <text class="dg-t dg-c" x="761" y="143.5">File process</text>
  <text class="dg-s dg-c" x="761" y="159.5">the ordering authority · in-memory document</text>
  <text class="dg-s dg-c" x="761" y="175.5">version counter · last-writer-wins per property</text>
  <text class="dg-s dg-c" x="761" y="191.5">the socket set for this file</text>
  <path class="dg-line" d="M 230,120 L 520,120 L 520,150 L 548,150"></path>
  <path class="dg-head" d="M 548,155 L 548,145 L 556,150 Z"></path>
  <text class="dg-lbl" x="300" y="112">one WebSocket, straight to the owner</text>
  <rect class="dg-box" x="556" y="270" width="410" height="56" rx="8"></rect>
  <path class="dg-qbar" d="M 569,279 L 569,317"></path>
  <path class="dg-qbar" d="M 578,279 L 578,317"></path>
  <path class="dg-qbar" d="M 587,279 L 587,317"></path>
  <text class="dg-t dg-c" x="779" y="294.5">Op log — Kafka</text>
  <text class="dg-s dg-c" x="779" y="310.5">partitioned by fileId · the system of record</text>
  <path class="dg-line" d="M 761,226 L 761,262"></path>
  <path class="dg-head" d="M 756,262 L 766,262 L 761,270 Z"></path>
  <rect class="dg-box" x="556" y="360" width="190" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="651" y="392.5">Snapshot job</text>
  <path class="dg-box" d="M 776,367 L 776,409 A 95,7 0 0 0 966,409 L 966,367 A 95,7 0 0 0 776,367 Z"></path>
  <path class="dg-box" d="M 776,367 A 95,7 0 0 0 966,367" style="fill:none"></path>
  <text class="dg-t dg-c" x="871" y="388">S3 + CDN</text>
  <text class="dg-s dg-c" x="871" y="404">file/{id}/{version}</text>
  <path class="dg-line" d="M 746,388 L 768,388"></path>
  <path class="dg-head" d="M 768,393 L 768,383 L 776,388 Z"></path>
  <path class="dg-line" d="M 651,326 L 651,352"></path>
  <path class="dg-head" d="M 646,352 L 656,352 L 651,360 Z"></path>
  <path class="dg-box" d="M 280,367 L 280,409 A 100,7 0 0 0 480,409 L 480,367 A 100,7 0 0 0 280,367 Z"></path>
  <path class="dg-box" d="M 280,367 A 100,7 0 0 0 480,367" style="fill:none"></path>
  <text class="dg-t dg-c" x="380" y="388">Postgres</text>
  <text class="dg-s dg-c" x="380" y="404">files · teams · permissions</text>
  <path class="dg-line" d="M 556,180 L 530,180 L 530,388 L 488,388"></path>
  <path class="dg-head" d="M 488,383 L 488,393 L 480,388 Z"></path>
  <path class="dg-line" d="M 871,416 L 871,450 L 500,450 L 500,240 L 238,240"></path>
  <path class="dg-head" d="M 238,235 L 238,245 L 230,240 Z"></path>
  <text class="dg-lbl" x="560" y="442">snapshot on cold open</text>
  <text class="dg-note" x="20" y="500">Presence is the highest-volume thing in the system and the only thing worth losing, so it never touches disk — in memory in the owning process, TTL-evicted.</text>
</svg>
</div>

<p class="diagram-cap">There is no coordination layer on this board, and that is the design: one process owns one file, so ordering is free and the op log only has to make it durable. Draw the registry as a lookup rather than a proxy — the socket goes straight to the owner.</p>

<div class="diagram" data-board="flows">
<svg viewBox="0 0 1000 578" role="img" aria-label="Figma high-level design. Client column: input, local apply to the scene graph painting inside sixteen milliseconds with no network, a WebGL renderer, and a pending queue keyed by object and property holding unacknowledged values. Server column: one file process per open file acting as the ordering authority with last-writer-wins per property, an op log in Kafka as the system of record, and a snapshot job to S3 and the CDN. A bottom lane shows cold open: snapshot from CDN, decode off the main thread, paint the viewport first, then apply the op tail.">
  <rect class="dg-banner" x="10" y="10" width="980" height="38" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="33.5">Convergence, not linearizability. The document model chose the algorithm — and the local loop never waits for the network.</text>
  <text class="dg-lane" x="30" y="76">CLIENT — 16 MS, NO NETWORK ON THIS PATH</text>
  <text class="dg-lane" x="560" y="76">SERVER — ONE PROCESS PER OPEN FILE</text>
  <path class="dg-div" d="M 515,90 L 515,145"></path>
  <path class="dg-div" d="M 515,255 L 515,420"></path>
  <rect class="dg-box" x="40" y="100" width="180" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="124.5">Input</text>
  <rect class="dg-box" x="40" y="158" width="180" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="182.5">Local apply</text>
  <text class="dg-s dg-c" x="130" y="198.5">scene graph, painted now</text>
  <rect class="dg-box" x="40" y="232" width="180" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="130" y="254.5">Renderer (WebGL)</text>
  <text class="dg-s dg-c" x="130" y="270.5">16 ms budget</text>
  <path class="dg-line" d="M 130,140 L 130,150"></path>
  <path class="dg-head" d="M 125,150 L 135,150 L 130,158 Z"></path>
  <path class="dg-line" d="M 130,214 L 130,224"></path>
  <path class="dg-head" d="M 125,224 L 135,224 L 130,232 Z"></path>
  <rect class="dg-box" x="250" y="150" width="200" height="100" rx="8"></rect>
  <text class="dg-t dg-c" x="350" y="180.5">Pending queue</text>
  <text class="dg-s dg-c" x="350" y="196.5">keyed (objectId, key)</text>
  <text class="dg-s dg-c" x="350" y="212.5">unacknowledged values</text>
  <text class="dg-s dg-c" x="350" y="228.5">1000 frames replay as 1</text>
  <path class="dg-line" d="M 220,186 L 242,186"></path>
  <path class="dg-head" d="M 242,191 L 242,181 L 250,186 Z"></path>
  <rect class="dg-box" x="560" y="100" width="400" height="120" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="132.5">File process</text>
  <text class="dg-s dg-c" x="760" y="148.5">the ordering authority — one per open file</text>
  <text class="dg-s dg-c" x="760" y="164.5">in-memory document · version counter</text>
  <text class="dg-s dg-c" x="760" y="180.5">last-writer-wins per property</text>
  <text class="dg-s dg-c" x="760" y="196.5">socket set for this file</text>
  <path class="dg-line" d="M 450,170 L 552,170"></path>
  <path class="dg-head" d="M 552,175 L 552,165 L 560,170 Z"></path>
  <text class="dg-lbl dg-c" x="505" y="162">set · clientSeq</text>
  <path class="dg-line" d="M 560,200 L 458,200"></path>
  <path class="dg-head" d="M 458,195 L 458,205 L 450,200 Z"></path>
  <text class="dg-lbl dg-c" x="505" y="222">ack · set · bye</text>
  <rect class="dg-box" x="560" y="270" width="400" height="56" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="294.5">Op log — Kafka, partitioned by fileId</text>
  <text class="dg-s dg-c" x="760" y="310.5">the system of record</text>
  <rect class="dg-box" x="560" y="356" width="400" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="386.5">Snapshot job → S3 → CDN</text>
  <path class="dg-line" d="M 760,220 L 760,262"></path>
  <path class="dg-head" d="M 755,262 L 765,262 L 760,270 Z"></path>
  <path class="dg-line" d="M 760,326 L 760,348"></path>
  <path class="dg-head" d="M 755,348 L 765,348 L 760,356 Z"></path>
  <rect class="dg-warn" x="250" y="270" width="200" height="76" rx="8"></rect>
  <text class="dg-warn-t dg-c" x="350" y="288.5">Discard rule</text>
  <text class="dg-s dg-c" x="350" y="304.5">a remote set for a property</text>
  <text class="dg-s dg-c" x="350" y="320.5">you hold an unacked value for</text>
  <text class="dg-s dg-c" x="350" y="336.5">is dropped, every frame</text>
  <path class="dg-line" d="M 350,250 L 350,262"></path>
  <path class="dg-head" d="M 345,262 L 355,262 L 350,270 Z"></path>
  <path class="dg-div" d="M 20,430 L 980,430"></path>
  <text class="dg-lane" x="30" y="456">COLD OPEN — hello(sinceVersion)</text>
  <rect class="dg-box" x="30" y="470" width="220" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="140" y="492.5">snapshot from CDN</text>
  <text class="dg-s dg-c" x="140" y="508.5">immutable blob + its version</text>
  <rect class="dg-box" x="290" y="470" width="220" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="400" y="500.5">decode off main thread</text>
  <rect class="dg-box" x="550" y="470" width="200" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="650" y="500.5">paint viewport first</text>
  <rect class="dg-box" x="790" y="470" width="170" height="52" rx="8"></rect>
  <text class="dg-t dg-c" x="875" y="492.5">apply op tail</text>
  <text class="dg-s dg-c" x="875" y="508.5">then live</text>
  <path class="dg-line" d="M 250,496 L 282,496"></path>
  <path class="dg-head" d="M 282,501 L 282,491 L 290,496 Z"></path>
  <path class="dg-line" d="M 510,496 L 542,496"></path>
  <path class="dg-head" d="M 542,501 L 542,491 L 550,496 Z"></path>
  <path class="dg-line" d="M 750,496 L 782,496"></path>
  <path class="dg-head" d="M 782,501 L 782,491 L 790,496 Z"></path>
  <text class="dg-note" x="30" y="552">Tail too old? The server does not reconstruct — it sends a fresh snapshot and the client discards everything except its pending queue.</text>
</svg>
</div>

<p class="diagram-cap">The interesting line is the one that isn't there: nothing on the local loop touches the network. Draw the client as a closed cycle first, then hang the socket off the pending queue — that ordering is the whole argument for why this is not OT.</p>

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

<div class="diagram" data-board="skeleton">
<svg viewBox="0 0 1000 500" role="img" aria-label="Figma five-minute skeleton. The document model as a map of object to property to value. Client loop: input, local apply, renderer, pending queue. One WebSocket to one file process, the ordering authority, with a registry, an op log and a snapshot path to the CDN. Presence drawn as a separate lossy arrow, and two decisions written in the corner.">
  <rect class="dg-banner" x="10" y="10" width="980" height="34" rx="9"></rect>
  <text class="dg-banner-t dg-c" x="500" y="31.5">Minute five: everything below must be on the board. Badge numbers match the list.</text>
  <rect class="dg-good" x="30" y="68" width="930" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="495" y="92.5">Map&lt;ObjectID, Map&lt;Property, Value&gt;&gt; — the property is the unit of conflict</text>
  <circle class="dg-num" cx="30" cy="68" r="9"></circle>
  <text class="dg-num-t" x="30" y="71.4">1</text>
  <text class="dg-lane" x="30" y="140">CLIENT</text>
  <text class="dg-lane" x="560" y="140">SERVER</text>
  <path class="dg-div" d="M 515,150 L 515,230"></path>
  <path class="dg-div" d="M 515,262 L 515,330"></path>
  <rect class="dg-box" x="30" y="154" width="150" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="105" y="183.5">Input</text>
  <circle class="dg-num" cx="30" cy="154" r="9"></circle>
  <text class="dg-num-t" x="30" y="157.4">2</text>
  <rect class="dg-box" x="30" y="222" width="150" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="105" y="243.5">Local apply</text>
  <text class="dg-s dg-c" x="105" y="259.5">16 ms</text>
  <rect class="dg-box" x="30" y="290" width="150" height="50" rx="8"></rect>
  <text class="dg-t dg-c" x="105" y="319.5">Renderer (WebGL)</text>
  <path class="dg-line" d="M 105,204 L 105,214"></path>
  <path class="dg-head" d="M 100,214 L 110,214 L 105,222 Z"></path>
  <path class="dg-line" d="M 105,272 L 105,282"></path>
  <path class="dg-head" d="M 100,282 L 110,282 L 105,290 Z"></path>
  <rect class="dg-box" x="220" y="204" width="240" height="86" rx="8"></rect>
  <text class="dg-t dg-c" x="340" y="235.5">Pending queue</text>
  <text class="dg-s dg-c" x="340" y="251.5">keyed (objectId, key)</text>
  <text class="dg-s dg-c" x="340" y="267.5">unacked values only</text>
  <circle class="dg-num" cx="220" cy="204" r="9"></circle>
  <text class="dg-num-t" x="220" y="207.4">3</text>
  <path class="dg-line" d="M 180,247 L 212,247"></path>
  <path class="dg-head" d="M 212,252 L 212,242 L 220,247 Z"></path>
  <rect class="dg-box" x="560" y="154" width="400" height="86" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="185.5">File process</text>
  <text class="dg-s dg-c" x="760" y="201.5">the ordering authority</text>
  <text class="dg-s dg-c" x="760" y="217.5">LWW per property</text>
  <circle class="dg-num" cx="560" cy="154" r="9"></circle>
  <text class="dg-num-t" x="560" y="157.4">4</text>
  <path class="dg-line" d="M 460,247 L 552,247"></path>
  <path class="dg-head" d="M 552,252 L 552,242 L 560,247 Z"></path>
  <text class="dg-lbl dg-c" x="510" y="239">one WebSocket</text>
  <rect class="dg-box" x="560" y="270" width="400" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="296.5">Op log — Kafka by fileId</text>
  <circle class="dg-num" cx="560" cy="270" r="9"></circle>
  <text class="dg-num-t" x="560" y="273.4">6</text>
  <rect class="dg-box" x="560" y="338" width="400" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="760" y="364.5">Snapshot → S3 → CDN</text>
  <circle class="dg-num" cx="560" cy="338" r="9"></circle>
  <text class="dg-num-t" x="560" y="341.4">7</text>
  <path class="dg-line" d="M 760,240 L 760,262"></path>
  <path class="dg-head" d="M 755,262 L 765,262 L 760,270 Z"></path>
  <path class="dg-line" d="M 760,314 L 760,330"></path>
  <path class="dg-head" d="M 755,330 L 765,330 L 760,338 Z"></path>
  <path class="dg-line" d="M 560,360 L 500,360 L 500,404 L 188,404"></path>
  <path class="dg-head" d="M 188,399 L 188,409 L 180,404 Z"></path>
  <rect class="dg-box" x="30" y="382" width="150" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="105" y="408.5">cold open</text>
  <rect class="dg-box" x="220" y="338" width="240" height="44" rx="8"></rect>
  <text class="dg-t dg-c" x="340" y="356.5">Presence</text>
  <text class="dg-s dg-c" x="340" y="372.5">lossy · unordered · never stored</text>
  <circle class="dg-num" cx="220" cy="338" r="9"></circle>
  <text class="dg-num-t" x="220" y="341.4">8</text>
  <rect class="dg-box" x="30" y="446" width="290" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="175" y="470.5">Registry: fileId → server</text>
  <circle class="dg-num" cx="30" cy="446" r="9"></circle>
  <text class="dg-num-t" x="30" y="449.4">5</text>
  <rect class="dg-box" x="340" y="446" width="290" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="485" y="470.5">fractional index · LWW per property</text>
  <circle class="dg-num" cx="340" cy="446" r="9"></circle>
  <text class="dg-num-t" x="340" y="449.4">9</text>
  <rect class="dg-good" x="650" y="446" width="310" height="40" rx="8"></rect>
  <text class="dg-t dg-c" x="805" y="470.5">convergence, not linearizability</text>
  <circle class="dg-num" cx="650" cy="446" r="9"></circle>
  <text class="dg-num-t" x="650" y="449.4">10</text>
</svg>
</div>

<p class="diagram-cap">Item 1 is a box because it is the answer: get the document model on the board before anything else, and the algorithm argument in §7 writes itself. The two boxes at the bottom are the sentences you close on.</p>

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
