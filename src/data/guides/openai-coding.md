# OpenAI Coding — Top 20 Working Reference

Adapted from Jaspreet's September 22, 2026 study sheet; reviewed September 25.
Start with the [final-loop plan](#/learn/final-loops), which budgets this material alongside design and project discussions.
The original problem numbers are preserved so the plan and this reference agree.

## Evidence and priority

These are representative practice problems, not a verified question-frequency ranking or a prediction of your loop. Candidate-report links from the supplied sheet are background reading, not confirmation of an exact prompt, round, or tool. OpenAI's [official interview guide](https://openai.com/interview-guide/) describes team-dependent assessments and emphasizes code quality, performance, testing, communication, and collaboration. Your recruiter packet controls the format and tool policy.

**First pass:** #1 LRU, #3 resumable iterator, #4 transactions, #5 versioned KV/TTL, #6 limiter, #7 paths, #8 dependencies, and #10 scheduler. Each transfers to several small-system problems. Keep #2 LFU and #9 concurrency as extensions after a working core, unless your confirmed rounds elevate them. #11–#20 are targeted warm-ups for weak patterns, not ten extra mandatory sessions.

The examples below are small interview implementations with explicit contracts. The async examples use one JavaScript event loop; they do not demonstrate shared-memory thread safety. Individual video links are retained from the supplied sheet and have not been independently verified.

## Corrections and contracts

- Iterator restore validates state. The async iterator assumes sequential calls on immutable source files; concurrent reads/restores need serialization and stale-read protection.
- Transactions use nested undo scopes, but `commit()` commits **all** open scopes. Inner-only commit would require merging first-touch undo entries into the parent.
- Historical lookup and wall-clock TTL are separate APIs here. Combining them requires deciding expiry at query time versus current time, and whether an expired version hides older versions.
- Path resolution below uses physical semantics: expand symlinks before later `..`, resolve relative targets from the link's parent, and cap link traversals. It is not a complete shell or filesystem.
- A rejected spreadsheet formula leaves the old formula and dependencies intact. Caller mutation of the input list cannot change the stored formula.
- Limiter clocks must be monotonic. The sliding-log example uses `shift()`, so pruning is not O(1); use a deque/head index and cleanup for inactive clients in a long-lived server. Redis `INCR` plus expiry implements a fixed-window policy only when composed atomically; it is not a distributed token bucket.
- Unless validated in the snippet, inputs obey the stated interview contract: positive integer capacities, nonnegative finite time values and delays, positive token costs, and sequential calls. #17 assumes `1 ≤ k ≤ distinct values`; #18 counts UTF-16 code units; #19 assumes lowercase ASCII letters. Broader input domains require validation or a changed representation.
- The scheduler runs synchronous callbacks. Async completion, cancellation, fairness, and bounded work per tick are separate extensions.

## Tier 1 — OpenAI-style builds (1–10)

Each build starts small and grows. Focus on the state invariant and preserving earlier behavior as requirements change.

### 1. LRU Cache (LC 146)

**Problem.** `get(key)` and `put(key, value)` in expected O(1); evict the least-recently-used entry when over capacity.

**Breakdown.** You need O(1) lookup (hash map) and O(1) reordering (doubly linked list). Sentinel head/tail nodes remove every null check. On `get` or `put`, unlink the node and push it to the front; evict from the back.

**Core algorithm.** Hash map + doubly linked list. Shortcut in JS/TS: `Map` preserves insertion order, so delete-and-reinsert gives you LRU in 10 lines — say that first, then offer the linked-list version if the interviewer wants no built-in ordering.

**Useful extensions.** Thread-safe version (wrap operations in a lock; for operations spanning awaits on one JS event loop, an async mutex), TTL per entry, then a high-level chat about distributed caching.

```ts
class DNode<K, V> {
  prev: DNode<K, V> | null = null;
  next: DNode<K, V> | null = null;
  constructor(public key: K, public val: V) {}
}

class LRUCache<K, V> {
  private map = new Map<K, DNode<K, V>>();
  private head = new DNode<K, V>(null as K, null as V); // sentinel: MRU side
  private tail = new DNode<K, V>(null as K, null as V); // sentinel: LRU side

  constructor(private capacity: number) {
    if (capacity <= 0) throw new Error('capacity must be > 0');
    this.head.next = this.tail;
    this.tail.prev = this.head;
  }

  private unlink(n: DNode<K, V>): void {
    n.prev!.next = n.next;
    n.next!.prev = n.prev;
  }

  private pushFront(n: DNode<K, V>): void {
    n.next = this.head.next;
    n.prev = this.head;
    this.head.next!.prev = n;
    this.head.next = n;
  }

  get(key: K): V | undefined {
    const n = this.map.get(key);
    if (!n) return undefined;
    this.unlink(n);
    this.pushFront(n);
    return n.val;
  }

  put(key: K, val: V): void {
    const existing = this.map.get(key);
    if (existing) {
      existing.val = val;
      this.unlink(existing);
      this.pushFront(existing);
      return;
    }
    const n = new DNode(key, val);
    this.map.set(key, n);
    this.pushFront(n);
    if (this.map.size > this.capacity) {
      const lru = this.tail.prev!;
      this.unlink(lru);
      this.map.delete(lru.key);
    }
  }
}
```

**Video.** [NeetCode — LRU Cache](https://neetcode.io/solutions/lru-cache)

### 2. LFU Cache (LC 460) — the natural follow-up

**Problem.** Same API, but evict the least-frequently-used key; break ties by least-recently-used.

**Breakdown.** Track each key's frequency, and for each frequency keep the keys in recency order. Track `minFreq` so eviction is O(1). When a key is touched, move it from bucket `f` to bucket `f+1`; if bucket `f` empties and `f === minFreq`, bump `minFreq`. A new insert always sets `minFreq = 1`.

**Core algorithm.** Two hash maps + a map of frequency → insertion-ordered `Set` (JS `Set` keeps insertion order, so the first element is the LRU within that frequency).

```ts
class LFUCache {
  private vals = new Map<number, number>();
  private freqs = new Map<number, number>();
  private buckets = new Map<number, Set<number>>(); // freq -> keys, LRU first
  private minFreq = 0;

  constructor(private capacity: number) {}

  private touch(key: number): void {
    const f = this.freqs.get(key)!;
    const bucket = this.buckets.get(f)!;
    bucket.delete(key);
    if (bucket.size === 0) {
      this.buckets.delete(f);
      if (this.minFreq === f) this.minFreq = f + 1;
    }
    this.freqs.set(key, f + 1);
    if (!this.buckets.has(f + 1)) this.buckets.set(f + 1, new Set());
    this.buckets.get(f + 1)!.add(key);
  }

  get(key: number): number {
    if (!this.vals.has(key)) return -1;
    this.touch(key);
    return this.vals.get(key)!;
  }

  put(key: number, val: number): void {
    if (this.capacity === 0) return;
    if (this.vals.has(key)) {
      this.vals.set(key, val);
      this.touch(key);
      return;
    }
    if (this.vals.size === this.capacity) {
      const bucket = this.buckets.get(this.minFreq)!;
      const evict = bucket.values().next().value as number; // LRU in min bucket
      bucket.delete(evict);
      if (bucket.size === 0) this.buckets.delete(this.minFreq);
      this.vals.delete(evict);
      this.freqs.delete(evict);
    }
    this.vals.set(key, val);
    this.freqs.set(key, 1);
    if (!this.buckets.has(1)) this.buckets.set(1, new Set());
    this.buckets.get(1)!.add(key);
    this.minFreq = 1;
  }
}
```

**Video.** [NeetCode — LFU Cache](https://neetcode.io/solutions/lfu-cache)

### 3. Resumable iterator with getState / setState

**Problem.** Iterate a sequence (then a nested one) with `hasNext()` / `next()`, and expose `getState()` / `setState()` so the position can be serialized and restored. Extensions reported: list → multi-file JSON with empty files → async version → 2D/3D. For preparation, write a test before each extension ([Resumax breakdown](https://resumax.ai/interview-questions/openai)).

**Breakdown.** State is just the cursor: `(outer, inner)` for 2D. A key edge case is empty inner lists — normalize the cursor after every move so `hasNext()` is always truthful. `setState` must run the same normalization. Keep state a plain serializable object so it can be JSON-encoded.

**Core algorithm.** Cursor normalization (skip-empty loop) + explicit state object. Async version swaps `next(): T` for `next(): Promise<T>` and reads lazily.

```ts
type IterState = { outer: number; inner: number };

class ResumableIterator<T> {
  private outer = 0;
  private inner = 0;

  constructor(private readonly data: readonly (readonly T[])[]) {
    this.normalize();
  }

  // Advance past empty inner lists so the cursor always points at a real element or the end.
  private normalize(): void {
    while (this.outer < this.data.length && this.inner >= this.data[this.outer].length) {
      this.outer++;
      this.inner = 0;
    }
  }

  hasNext(): boolean {
    return this.outer < this.data.length;
  }

  next(): T {
    if (!this.hasNext()) throw new Error('Iterator exhausted');
    const v = this.data[this.outer][this.inner++];
    this.normalize();
    return v;
  }

  getState(): IterState {
    return { outer: this.outer, inner: this.inner };
  }

  setState(s: IterState): void {
    if (!Number.isInteger(s.outer) || !Number.isInteger(s.inner) ||
        s.outer < 0 || s.outer > this.data.length || s.inner < 0 ||
        (s.outer === this.data.length ? s.inner !== 0 : s.inner > this.data[s.outer].length)) {
      throw new Error('Invalid iterator state');
    }
    this.outer = s.outer;
    this.inner = s.inner;
    this.normalize();
  }
}

// Extension: async source (e.g. one file per outer index, read on demand)
class AsyncResumableIterator<T> {
  private file = 0;
  private offset = 0;
  private buf: T[] | null = null;

  constructor(private readonly fileCount: number, private readonly readFile: (i: number) => Promise<T[]>) {}

  private async load(): Promise<void> {
    while (this.file < this.fileCount) {
      if (this.buf === null) this.buf = await this.readFile(this.file);
      if (this.offset > this.buf.length) throw new Error('Invalid file offset');
      if (this.offset < this.buf.length) return;
      this.file++; this.offset = 0; this.buf = null; // empty or exhausted file
    }
  }

  async hasNext(): Promise<boolean> { await this.load(); return this.file < this.fileCount; }
  async next(): Promise<T> {
    if (!(await this.hasNext())) throw new Error('Iterator exhausted');
    return this.buf![this.offset++];
  }
  getState() { return { file: this.file, offset: this.offset }; }
  // Offsets inside a file are checked lazily when that file is loaded.
  setState(s: { file: number; offset: number }) {
    if (!Number.isInteger(s.file) || !Number.isInteger(s.offset) ||
        s.file < 0 || s.file > this.fileCount || s.offset < 0 ||
        (s.file === this.fileCount && s.offset !== 0)) throw new Error('Invalid state');
    this.file = s.file; this.offset = s.offset; this.buf = null;
  }
}
```

**Related walkthrough.** The supplied sheet has no dedicated video for this variant; the closest is [NeetCode — Flatten Nested List Iterator](https://www.youtube.com/watch?v=4ILiBgLokM8) (same cursor idea, see #12), plus the written breakdown linked above.

### 4. In-memory database with transactions

**Problem.** `set / get / unset / count(value)` in expected O(1), plus `begin / rollback / commit` with nested transactions ([Hello Interview breakdown](https://www.hellointerview.com/community/questions/memory-database-transactions/cm6uaoy1y00003b6la4jojd7s)).

**Breakdown.** Keep the committed store as one map plus a value-count map. Each open transaction is an undo log: the first time a key is written inside the transaction, record its prior value. `rollback` pops the top log and restores each touched key; `commit` discards all logs. Every write goes through one private `write()` so counts stay consistent. Only `rollback` closes the innermost scope; `commit` closes all scopes.

**Core algorithm.** Stack of undo logs (delta tracking). O(1) per op, O(k) rollback where k = keys touched in that transaction.

```ts
class InMemoryDB {
  private data = new Map<string, string>();
  private counts = new Map<string, number>();
  private undo: Map<string, string | undefined>[] = []; // one log per open tx

  private bump(value: string, delta: number): void {
    const next = (this.counts.get(value) ?? 0) + delta;
    if (next === 0) this.counts.delete(value); else this.counts.set(value, next);
  }

  // Single write path: keeps counts correct, never records undo.
  private write(key: string, value: string | undefined): void {
    const old = this.data.get(key);
    if (old !== undefined) this.bump(old, -1);
    if (value === undefined) this.data.delete(key);
    else { this.data.set(key, value); this.bump(value, 1); }
  }

  private record(key: string): void {
    const log = this.undo[this.undo.length - 1];
    if (log && !log.has(key)) log.set(key, this.data.get(key)); // first touch only
  }

  set(key: string, value: string): void { this.record(key); this.write(key, value); }
  get(key: string): string | null { return this.data.get(key) ?? null; }
  unset(key: string): void { this.record(key); this.write(key, undefined); }
  count(value: string): number { return this.counts.get(value) ?? 0; }

  begin(): void { this.undo.push(new Map()); }

  rollback(): boolean {
    const log = this.undo.pop();
    if (!log) return false; // NO TRANSACTION
    for (const [key, prior] of log) this.write(key, prior);
    return true;
  }

  commit(): boolean {
    if (this.undo.length === 0) return false;
    this.undo = []; // committed state is already in `data`
    return true;
  }
}
```

**Walkthrough.** Written: Hello Interview page above. Video-style: none canonical; practice by narrating the undo-log invariant out loud.

### 5. Time-based key-value store (LC 981) + TTL extension

**Problem.** `set(key, value, timestamp)` and `get(key, timestamp)` returning the value with the largest timestamp ≤ the query. Timestamps per key are strictly increasing. Useful follow-up: define expiry (TTL) semantics.

**Breakdown.** Because timestamps arrive in order, each key's history is already sorted — append in expected O(1), binary-search the floor in O(log n). For TTL, store `expiresAt` and expire lazily on read; inject a clock so tests are deterministic.

**Core algorithm.** Hash map of key → parallel sorted arrays; binary search for rightmost `ts ≤ query`.

```ts
class TimeMap {
  private store = new Map<string, { ts: number[]; vals: string[] }>();

  set(key: string, value: string, timestamp: number): void {
    if (!this.store.has(key)) this.store.set(key, { ts: [], vals: [] });
    const e = this.store.get(key)!;
    e.ts.push(timestamp);
    e.vals.push(value);
  }

  get(key: string, timestamp: number): string {
    const e = this.store.get(key);
    if (!e) return '';
    let lo = 0, hi = e.ts.length - 1, best = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (e.ts[mid] <= timestamp) { best = mid; lo = mid + 1; } else hi = mid - 1;
    }
    return best === -1 ? '' : e.vals[best];
  }
}

// Extension: key-value store with TTL, lazy expiry, injectable clock
class TTLStore<K, V> {
  private m = new Map<K, { v: V; expiresAt: number }>();
  constructor(private readonly now: () => number = Date.now) {}

  set(key: K, value: V, ttlMs: number): void {
    this.m.set(key, { v: value, expiresAt: this.now() + ttlMs });
  }

  get(key: K): V | undefined {
    const e = this.m.get(key);
    if (!e) return undefined;
    if (e.expiresAt <= this.now()) { this.m.delete(key); return undefined; }
    return e.v;
  }
}
```

**Video.** [NeetCode — Time Based Key-Value Store](https://www.youtube.com/watch?v=fu2cD_6E8Hw)

### 6. Rate limiter (token bucket + sliding window; LC 359 as warm-up)

**Problem.** Decide whether a request is allowed. A sliding log enforces at most N accepted requests in a rolling window. A token bucket instead specifies a burst capacity and sustained refill rate; these are different contracts. The supplied sheet includes rate limiting as a representative small-system build. LC 359 (Logger Rate Limiter) is the 5-minute warm-up: allow a message only if it wasn't printed in the last 10 seconds.

**Breakdown.** Two standard designs, know both and the trade-off: token bucket (smooth bursts, O(1) memory per client, refills lazily on each call) and sliding window log (exact, O(limit) memory per client). Inject the clock. Follow-ups: per-client vs global, distributed atomic enforcement (an atomic increment/expiry operation for a fixed window, or an atomic refill/debit operation for a token bucket), what happens at window boundaries.

**Core algorithm.** Lazy refill arithmetic (token bucket) or a timestamp queue pruned on each call (sliding log).

```ts
class TokenBucket {
  private tokens: number;
  private last: number;

  constructor(
    private readonly capacity: number,
    private readonly refillPerSec: number,
    private readonly now: () => number = Date.now,
  ) {
    this.tokens = capacity;
    this.last = now();
  }

  allow(cost = 1): boolean {
    const t = this.now();
    const elapsedSec = (t - this.last) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsedSec * this.refillPerSec);
    this.last = t;
    if (this.tokens < cost) return false;
    this.tokens -= cost;
    return true;
  }
}

class SlidingWindowLimiter {
  private log = new Map<string, number[]>(); // client -> timestamps in window

  constructor(
    private readonly limit: number,
    private readonly windowMs: number,
    private readonly now: () => number = Date.now,
  ) {}

  allow(client: string): boolean {
    const t = this.now();
    const q = this.log.get(client) ?? [];
    while (q.length && q[0] <= t - this.windowMs) q.shift(); // prune expired
    if (q.length >= this.limit) { this.log.set(client, q); return false; }
    q.push(t);
    this.log.set(client, q);
    return true;
  }
}

// LC 359 Logger Rate Limiter
class Logger {
  private lastPrinted = new Map<string, number>();
  shouldPrintMessage(timestamp: number, message: string): boolean {
    const last = this.lastPrinted.get(message);
    if (last !== undefined && timestamp < last + 10) return false;
    this.lastPrinted.set(message, timestamp);
    return true;
  }
}
```

**Walkthrough.** Written: [IGotAnOffer — OpenAI coding interview](https://igotanoffer.com/en/advice/openai-coding-interview) covers the rate-limiter category; for the algorithms themselves, Hello Interview's rate-limiter system design page is the standard reference.

### 7. Unix `cd` with symlink resolution (LC 71 as warm-up)

**Problem.** `cd(currentDir, target)` handling relative paths, `.` and `..`, absolute paths, `~`, and symlinks from a provided map; part 3 adds cycle detection ([Resumax breakdown](https://resumax.ai/interview-questions/openai)). LC 71 Simplify Path is the same stack walk without symlinks.

**Breakdown.** Process a queue of path components. Expand a symlink target into the remaining work before handling the suffix. An absolute target resets the stack; a relative target starts at the link's parent. This also resolves symlinks inside targets. A bounded traversal count rejects cycles and pathological chains without rejecting a legitimate repeated visit automatically.

**Core algorithm.** Component stack + work queue + symlink traversal budget. `cwd` and `home` are absolute physical paths; the map represents links, not filesystem existence or permissions.

```ts
type SymlinkMap = Record<string, string>;

function cd(cwd: string, target: string, symlinks: SymlinkMap = {}, home = '/home/user'): string {
  if (!cwd.startsWith('/') || !home.startsWith('/')) throw new Error('Absolute base required');
  const expanded = target === '~' || target.startsWith('~/') ? home + target.slice(1) : target;
  let pending = (expanded.startsWith('/') ? expanded : cwd + '/' + expanded).split('/');
  const stack: string[] = [];
  let links = 0;
  for (let i = 0; i < pending.length; i++) {
    const part = pending[i];
    if (!part || part === '.') continue;
    if (part === '..') { stack.pop(); continue; }
    stack.push(part);
    const path = '/' + stack.join('/');
    if (!Object.prototype.hasOwnProperty.call(symlinks, path)) continue;
    if (++links > 40) throw new Error('Too many symlink traversals');
    const dest = symlinks[path];
    if (!dest) throw new Error('Empty symlink target');
    stack.pop();
    if (dest.startsWith('/')) stack.length = 0;
    pending = dest.split('/').concat(pending.slice(i + 1));
    i = -1;
  }
  return '/' + stack.join('/');
}

// LC 71 is the same function with no symlinks/home handling:
function simplifyPath(path: string): string {
  const stack: string[] = [];
  for (const part of path.split('/')) {
    if (part === '' || part === '.') continue;
    if (part === '..') stack.pop();
    else stack.push(part);
  }
  return '/' + stack.join('/');
}
```

**Video.** [NeetCode — Simplify Path](https://neetcode.io/solutions/simplify-path) for the stack walk; symlink and cycle extensions in the Resumax write-up above.

### 8. Spreadsheet with formula evaluation (LC 631 Design Excel Sum Formula)

**Problem.** Cells hold either a number or `SUM` of other cells; setting a cell must recompute everything that depends on it. Reported at OpenAI as "build a spreadsheet with formula evaluation" ([IGotAnOffer](https://igotanoffer.com/en/advice/openai-coding-interview)). Circular references should be rejected.

**Breakdown.** Keep three maps: values, formulas, and reverse dependencies (`dependents[A]` = cells whose formula references A). On any change, collect the reachable dependents and recompute them in topological order so each cell is computed once, after all its inputs. Before accepting a formula, DFS from the cell through its references to reject cycles. Duplicates in a formula (`SUM(A1, A1)`) count twice — handle indegree per occurrence.

**Core algorithm.** Dependency graph + Kahn's topological sort for propagation; DFS for cycle detection.

```ts
class Spreadsheet {
  private values = new Map<string, number>();
  private formulas = new Map<string, string[]>(); // cell -> referenced cells (dups allowed)
  private dependents = new Map<string, Set<string>>(); // cell -> cells that reference it

  get(cell: string): number {
    return this.values.get(cell) ?? 0;
  }

  set(cell: string, value: number): void {
    this.detach(cell);
    this.values.set(cell, value);
    this.propagate(cell);
  }

  setSum(cell: string, refs: string[]): number {
    // Validate the proposed graph before mutating the current one.
    if (this.createsCycle(cell, refs)) throw new Error(`circular reference at ${cell}`);
    this.detach(cell);
    this.formulas.set(cell, [...refs]);
    for (const r of refs) {
      if (!this.dependents.has(r)) this.dependents.set(r, new Set());
      this.dependents.get(r)!.add(cell);
    }
    this.recompute(cell);
    this.propagate(cell);
    return this.get(cell);
  }

  private detach(cell: string): void {
    const refs = this.formulas.get(cell);
    if (!refs) return;
    for (const r of refs) this.dependents.get(r)?.delete(cell);
    this.formulas.delete(cell);
  }

  private recompute(cell: string): void {
    const refs = this.formulas.get(cell);
    if (refs) this.values.set(cell, refs.reduce((s, r) => s + this.get(r), 0));
  }

  // DFS from `cell` through formula references; a path back to `cell` is a cycle.
  private createsCycle(cell: string, proposed: string[]): boolean {
    const seen = new Set<string>();
    const dfs = (c: string): boolean => {
      for (const r of c === cell ? proposed : (this.formulas.get(c) ?? [])) {
        if (r === cell) return true;
        if (!seen.has(r)) { seen.add(r); if (dfs(r)) return true; }
      }
      return false;
    };
    return dfs(cell);
  }

  // Recompute every cell downstream of `start` in topological order (Kahn).
  private propagate(start: string): void {
    const sub = new Set<string>();
    const stack = [start];
    while (stack.length) {
      const c = stack.pop()!;
      for (const d of this.dependents.get(c) ?? []) if (!sub.has(d)) { sub.add(d); stack.push(d); }
    }
    const indeg = new Map<string, number>();
    for (const c of sub) indeg.set(c, (this.formulas.get(c) ?? []).filter(r => sub.has(r)).length);
    const queue = [...sub].filter(c => indeg.get(c) === 0);
    while (queue.length) {
      const c = queue.shift()!;
      this.recompute(c);
      for (const d of this.dependents.get(c) ?? []) {
        if (!sub.has(d)) continue;
        const occurrences = this.formulas.get(d)!.filter(r => r === c).length;
        indeg.set(d, indeg.get(d)! - occurrences);
        if (indeg.get(d) === 0) queue.push(d);
      }
    }
  }
}
```

**Video.** [LeetCode 631 walkthrough (BFS propagation)](https://www.youtube.com/watch?v=aYjdDqcwYYQ); written breakdown at [Hello Interview — Design Excel Sum Formula](https://www.hellointerview.com/community/questions/design-excel-sum-formula/983569a7-83df-4f3c-a687-ecc557b178d8).

### 9. Bounded blocking queue (LC 1188) — async producer–consumer

**Problem.** `enqueue` blocks when full, `dequeue` blocks when empty, safe under multiple producers and consumers. Treat concurrency as conditional preparation until your round breakdown is confirmed.

**Breakdown.** The classic answer is a mutex plus two condition variables (`notFull`, `notEmpty`), or item/slot semaphores plus mutual exclusion around shared queue operations. Within one JavaScript event loop, this version is async (workers and shared memory need a different synchronization model): waiters park a resolver in a queue and are woken one at a time. Keep the `while` re-check after waking — that is the condition-variable idiom and the thing interviewers probe.

**Core algorithm.** Producer–consumer with condition variables (here: promise-based wait queues).

```ts
class AsyncBoundedQueue<T> {
  private items: T[] = [];
  private waitingProducers: Array<() => void> = [];
  private waitingConsumers: Array<() => void> = [];

  constructor(private readonly capacity: number) {
    if (capacity <= 0) throw new Error('capacity must be > 0');
  }

  async enqueue(item: T): Promise<void> {
    while (this.items.length >= this.capacity) {
      await new Promise<void>(resolve => this.waitingProducers.push(resolve)); // wait notFull
    }
    this.items.push(item);
    this.waitingConsumers.shift()?.(); // signal notEmpty
  }

  async dequeue(): Promise<T> {
    while (this.items.length === 0) {
      await new Promise<void>(resolve => this.waitingConsumers.push(resolve)); // wait notEmpty
    }
    const item = this.items.shift()!;
    this.waitingProducers.shift()?.(); // signal notFull
    return item;
  }

  size(): number {
    return this.items.length;
  }
}
```

**Video.** [Design Bounded Blocking Queue — LeetCode 1188](https://www.youtube.com/watch?v=0B8CXDCtpCU); written: [AlgoMonster 1188](https://algo.monster/liteproblems/1188). Pair with a thread-safe counter and a producer/consumer pipeline for the same session.

### 10. Task scheduler (LC 621) + heap-based scheduler design

**Problem.** LC 621: tasks with a cooldown `n` between identical tasks; return the minimum intervals. The small-system extension below is a scheduler: `schedule(task, delayMs)` and a `tick()`/`run()` loop that executes due tasks in order.

**Breakdown.** LC 621 has a closed-form greedy: the most frequent task dictates the frame count, `(max - 1) * (n + 1) + (#tasks with max frequency)`, floored by `tasks.length`. For the design variant, a min-heap keyed on `runAt` gives O(log n) insert and O(log n) pop of the next due task. TS has no built-in heap, so write a small one — it's reused in #15.

**Core algorithm.** Greedy frequency math (621); binary min-heap for the scheduler.

```ts
function leastInterval(tasks: string[], n: number): number {
  if (tasks.length === 0) return 0;
  const counts = new Map<string, number>();
  for (const t of tasks) counts.set(t, (counts.get(t) ?? 0) + 1);
  const max = Math.max(...counts.values());
  const withMax = [...counts.values()].filter(c => c === max).length;
  return Math.max(tasks.length, (max - 1) * (n + 1) + withMax);
}

class MinHeap<T> {
  private a: T[] = [];
  constructor(private readonly less: (x: T, y: T) => boolean) {}
  get size(): number { return this.a.length; }
  peek(): T | undefined { return this.a[0]; }
  push(v: T): void {
    this.a.push(v);
    let i = this.a.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (!this.less(this.a[i], this.a[p])) break;
      [this.a[i], this.a[p]] = [this.a[p], this.a[i]];
      i = p;
    }
  }
  pop(): T | undefined {
    if (this.a.length === 0) return undefined;
    const top = this.a[0];
    const last = this.a.pop()!;
    if (this.a.length) {
      this.a[0] = last;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < this.a.length && this.less(this.a[l], this.a[m])) m = l;
        if (r < this.a.length && this.less(this.a[r], this.a[m])) m = r;
        if (m === i) break;
        [this.a[i], this.a[m]] = [this.a[m], this.a[i]];
        i = m;
      }
    }
    return top;
  }
}

type Job = { runAt: number; seq: number; fn: () => void };

class Scheduler {
  private heap = new MinHeap<Job>((x, y) => x.runAt !== y.runAt ? x.runAt < y.runAt : x.seq < y.seq);
  private seq = 0;
  constructor(private readonly now: () => number = Date.now) {}

  schedule(fn: () => void, delayMs: number): void {
    this.heap.push({ runAt: this.now() + delayMs, seq: this.seq++, fn });
  }

  // Run everything that is due; returns how many jobs ran. Call from a loop or timer.
  tick(): number {
    let ran = 0;
    while (this.heap.size && this.heap.peek()!.runAt <= this.now()) {
      this.heap.pop()!.fn();
      ran++;
    }
    return ran;
  }
}
```

**Video.** [NeetCode — Task Scheduler](https://neetcode.io/solutions/task-scheduler)

## Tier 2 — classic mediums (11–20)

Supplemental pattern coverage. The supplied sheet cites OpenAI candidate lists alongside the builds above ([Verve AI list](https://www.vervecopilot.com/hot-blogs/openai-leetcode-interview-questions), [CodingInterview.com](https://www.codinginterview.com/guide/openai-coding-interview-questions/)). Target 20 minutes each, brute force stated out loud before the optimal one. Honorable mentions not in the 20: Trie (208), Serialize/Deserialize Binary Tree (297), Trapping Rain Water (42), Product of Array Except Self (238).

### 11. Peeking Iterator (LC 284)

**Problem.** Wrap an iterator with `hasNext / next` and add `peek()` that returns the next element without advancing.

**Breakdown.** Cache one element ahead. `peek` returns the cache; `next` returns the cache and refills it. `hasNext` is "cache is non-empty".

**Core algorithm.** One-element lookahead buffer.

```ts
interface Iter<T> { hasNext(): boolean; next(): T }

class PeekingIterator<T> implements Iter<T> {
  private buffered = false;
  private value: T | undefined;

  constructor(private readonly it: Iter<T>) {}

  peek(): T {
    if (!this.buffered) { this.value = this.it.next(); this.buffered = true; }
    return this.value as T;
  }

  next(): T {
    const v = this.peek();
    this.buffered = false;
    this.value = undefined;
    return v;
  }

  hasNext(): boolean {
    return this.buffered || this.it.hasNext();
  }
}
```

**Video.** [Peeking Iterator — LeetCode 284](https://www.youtube.com/watch?v=O93h1s373Hs)

### 12. Flatten Nested List Iterator (LC 341)

**Problem.** Given a nested list of integers and lists, implement `hasNext / next` that yields integers in order.

**Breakdown.** Push the list onto a stack in reverse; on `hasNext`, while the top is a list, pop it and push its children in reverse. Lazy — never flatten everything up front (interviewers ask why not).

**Core algorithm.** Stack-based lazy DFS.

```ts
type Nested = number | Nested[];

class NestedIterator {
  private stack: Nested[] = [];

  constructor(list: Nested[]) {
    for (let i = list.length - 1; i >= 0; i--) this.stack.push(list[i]);
  }

  hasNext(): boolean {
    while (this.stack.length && Array.isArray(this.stack[this.stack.length - 1])) {
      const inner = this.stack.pop() as Nested[];
      for (let i = inner.length - 1; i >= 0; i--) this.stack.push(inner[i]);
    }
    return this.stack.length > 0;
  }

  next(): number {
    if (!this.hasNext()) throw new Error('exhausted');
    return this.stack.pop() as number;
  }
}
```

**Video.** [NeetCode — Flatten Nested List Iterator](https://www.youtube.com/watch?v=4ILiBgLokM8)

### 13. Simplify Path (LC 71)

Covered in #7 (the `simplifyPath` function). Stack walk over `/`-split parts; skip `''` and `.`, pop on `..`. **Video.** [NeetCode — Simplify Path](https://neetcode.io/solutions/simplify-path)

### 14. Course Schedule II (LC 210)

**Problem.** Given `numCourses` and prerequisite pairs `[a, b]` (take b before a), return a valid order or `[]` if impossible.

**Breakdown.** Build adjacency `b → a` and indegrees. Start with all indegree-0 nodes, pop, append to order, decrement neighbors. If the order is shorter than `numCourses`, there is a cycle. This is exactly the propagation step in #8.

**Core algorithm.** Kahn's topological sort (BFS).

```ts
function findOrder(numCourses: number, prerequisites: number[][]): number[] {
  const adj: number[][] = Array.from({ length: numCourses }, () => []);
  const indeg = new Array<number>(numCourses).fill(0);
  for (const [a, b] of prerequisites) { adj[b].push(a); indeg[a]++; }

  const queue: number[] = [];
  for (let i = 0; i < numCourses; i++) if (indeg[i] === 0) queue.push(i);

  const order: number[] = [];
  for (let qi = 0; qi < queue.length; qi++) { // index pointer avoids O(n) shift
    const c = queue[qi];
    order.push(c);
    for (const nxt of adj[c]) if (--indeg[nxt] === 0) queue.push(nxt);
  }
  return order.length === numCourses ? order : [];
}
```

**Video.** [NeetCode — Course Schedule II](https://neetcode.io/solutions/course-schedule-ii)

### 15. Merge k Sorted Lists (LC 23)

**Problem.** Merge k sorted linked lists into one sorted list.

**Breakdown.** Put each list head in a min-heap keyed on value; pop the smallest, append it, push its `next`. O(N log k). Reuse the `MinHeap` from #10. Alternative: pairwise divide-and-conquer merge, same complexity, no heap.

**Core algorithm.** k-way merge with a min-heap.

```ts
class ListNode {
  constructor(public val: number, public next: ListNode | null = null) {}
}

function mergeKLists(lists: (ListNode | null)[]): ListNode | null {
  const heap = new MinHeap<ListNode>((x, y) => x.val < y.val); // MinHeap from #10
  for (const head of lists) if (head) heap.push(head);

  const dummy = new ListNode(0);
  let tail = dummy;
  while (heap.size) {
    const node = heap.pop()!;
    tail.next = node;
    tail = node;
    if (node.next) heap.push(node.next);
  }
  return dummy.next;
}
```

**Video.** [NeetCode — Merge K Sorted Lists](https://neetcode.io/solutions/merge-k-sorted-lists)

### 16. Merge Intervals (LC 56)

**Problem.** Merge all overlapping intervals.

**Breakdown.** Sort by start. Walk once; if the current start ≤ last merged end, extend the end, else push a new interval. O(n log n).

**Core algorithm.** Sort + single linear sweep.

```ts
function merge(intervals: number[][]): number[][] {
  if (intervals.length === 0) return [];
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  const out: number[][] = [[...sorted[0]]];
  for (let i = 1; i < sorted.length; i++) {
    const [s, e] = sorted[i];
    const last = out[out.length - 1];
    if (s <= last[1]) last[1] = Math.max(last[1], e);
    else out.push([s, e]);
  }
  return out;
}
```

**Video.** [NeetCode — Merge Intervals](https://neetcode.io/solutions/merge-intervals)

### 17. Top K Frequent Elements (LC 347)

**Problem.** Return the k most frequent elements.

**Breakdown.** Count with a map. Then either a heap of size k (O(n log k)) or bucket sort by frequency (O(n)): index `buckets[freq]` holds the values with that frequency; walk from the highest bucket down. Be ready to explain why bucket sort beats the heap here.

**Core algorithm.** Hash map count + bucket sort.

```ts
function topKFrequent(nums: number[], k: number): number[] {
  const counts = new Map<number, number>();
  for (const n of nums) counts.set(n, (counts.get(n) ?? 0) + 1);

  const buckets: number[][] = Array.from({ length: nums.length + 1 }, () => []);
  for (const [val, c] of counts) buckets[c].push(val);

  const out: number[] = [];
  for (let f = buckets.length - 1; f >= 0 && out.length < k; f--) {
    for (const v of buckets[f]) { out.push(v); if (out.length === k) break; }
  }
  return out;
}
```

**Video.** [NeetCode — Top K Frequent Elements](https://neetcode.io/solutions/top-k-frequent-elements)

### 18. Longest Substring Without Repeating Characters (LC 3)

**Problem.** Length of the longest substring with all distinct characters.

**Breakdown.** Sliding window with a map of char → last index. When the current char was seen inside the window, jump `left` past its last index. One pass.

**Core algorithm.** Sliding window with last-seen index.

```ts
function lengthOfLongestSubstring(s: string): number {
  const lastSeen = new Map<string, number>();
  let left = 0, best = 0;
  for (let right = 0; right < s.length; right++) {
    const ch = s[right];
    const prev = lastSeen.get(ch);
    if (prev !== undefined && prev >= left) left = prev + 1;
    lastSeen.set(ch, right);
    best = Math.max(best, right - left + 1);
  }
  return best;
}
```

**Video.** [NeetCode — Longest Substring Without Repeating Characters](https://neetcode.io/solutions/longest-substring-without-repeating-characters)

### 19. Group Anagrams (LC 49)

**Problem.** Group strings that are anagrams of each other.

**Breakdown.** Every anagram shares a canonical key. Sorting each word costs O(k log k); a 26-count signature costs O(k) and is the answer interviewers want when they ask "can you avoid the sort?".

**Core algorithm.** Hash map keyed on a character-count signature.

```ts
function groupAnagrams(strs: string[]): string[][] {
  const groups = new Map<string, string[]>();
  for (const s of strs) {
    const counts = new Array<number>(26).fill(0);
    for (const ch of s) counts[ch.charCodeAt(0) - 97]++;
    const key = counts.join('#'); // separator avoids 1,11 vs 11,1 collisions
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(s);
  }
  return [...groups.values()];
}
```

**Video.** [NeetCode — Group Anagrams](https://neetcode.io/solutions/group-anagrams)

### 20. Random Pick with Weight (LC 528)

**Problem.** Given weights, `pickIndex()` returns index i with probability `w[i] / sum(w)`. Reported in OpenAI lists as "pick a key proportional to its weight"; follow-up asks what changes if weights update often (Fenwick tree).

**Breakdown.** Build a prefix-sum array. Draw a uniform target in `[0, total)`, then binary-search the first prefix greater than the target. O(n) build, O(log n) per pick.

**Core algorithm.** Prefix sums + upper-bound binary search.

```ts
class WeightedPicker {
  private prefix: number[] = [];
  private total = 0;

  constructor(w: number[], private readonly rand: () => number = Math.random) {
    if (!w.length || w.some(x => !Number.isFinite(x) || x < 0)) throw new Error('Invalid weights');
    for (const x of w) { this.total += x; this.prefix.push(this.total); }
    if (!Number.isFinite(this.total) || this.total <= 0) throw new Error('Invalid total');
  }

  pickIndex(): number {
    const draw = this.rand();
    if (!Number.isFinite(draw) || draw < 0 || draw >= 1) throw new Error('Invalid random draw');
    const target = draw * this.total; // [0, total)
    let lo = 0, hi = this.prefix.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (this.prefix[mid] > target) hi = mid; else lo = mid + 1;
    }
    return lo;
  }
}
```

**Video.** [NeetCode — Random Pick with Weight](https://neetcode.io/solutions/random-pick-with-weight)

## How to practice

- Rehearse in the confirmed interview environment. Include an unaided implementation session; the recruiter packet determines whether AI, autocomplete, and documentation are allowed.
- Run the code. Write 3–5 test cases before the first extension; then explain limitations and complexity.
- Say the simple version first, then optimize. A simple executable baseline gives you something to test before optimizing.
- Time-box each part. The problems are long; when the clock is tight, ask the interviewer which extension matters most and skip the rest ([Hello Interview L5 guide](https://www.hellointerview.com/guides/openai/l5)).
- Inject clocks and randomness (see #5, #6, #10, #20) so your tests are deterministic — interviewers notice.
- In a debugging session, take your earlier solutions, break one invariant each, and diagnose from symptoms before touching code. Debugging rounds reward hypothesis-first reading.

## Sources

- [IGotAnOffer — OpenAI coding interview (questions and prep)](https://igotanoffer.com/en/advice/openai-coding-interview)
- [IGotAnOffer — 30+ common OpenAI interview questions](https://igotanoffer.com/en/advice/openai-interview-questions)
- [Hello Interview — OpenAI L5 interview guide](https://www.hellointerview.com/guides/openai/l5)
- [Resumax — OpenAI interview questions (resumable iterator, Unix cd, LRU)](https://resumax.ai/interview-questions/openai)
- [Interview Coder — OpenAI SWE interview process 2026](https://www.interviewcoder.co/blog/openai-software-engineer-interview)
- [Verve AI — 30 OpenAI LeetCode interview questions](https://www.vervecopilot.com/hot-blogs/openai-leetcode-interview-questions)
- [CodingInterview.com — OpenAI coding interview questions](https://www.codinginterview.com/guide/openai-coding-interview-questions/)
- [Glassdoor — OpenAI interview experiences](https://www.glassdoor.com/Interview/OpenAI-Interview-Questions-E2210885.htm)
- [Design Gurus — Does OpenAI ask LeetCode questions?](https://www.designgurus.io/answers/detail/does-openai-ask-leetcode-questions-in-interviews)
- Video sources: NeetCode solution pages and YouTube channel; individual LeetCode 284, 631, 1188 walkthroughs linked inline.
