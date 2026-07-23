// Deck selection + lightweight Leitner scheduling. Pure functions so the logic
// is testable and the UI stays dumb.

import { addDays, daysBetween, todayISO } from './dates'
import type { DeckCard, Prompt, QuizScope, Result, SchedItem, SchedMap } from './types'

const MAX_INTERVAL = 21
const TRACK_CAP = 3
const RECENT_MISS_DAYS = 2
// How strongly never-seen prompts are favored. Held constant across all
// never-seen prompts so their relative odds reduce to the `weight` ratio —
// i.e. a weight-4 prompt shows ~4x as often as a weight-1 prompt (per spec).
const NEVER_SEEN_RECENCY = 14
const HISTORY_KEEP_DAYS = 30

function defaultItem(today: string): SchedItem {
  return { intervalDays: 0, dueISO: today, history: [] }
}

// ---- Leitner update ------------------------------------------------------

export function applyResult(
  sched: SchedMap,
  prompt: Prompt,
  result: Result,
  today = todayISO(),
): SchedMap {
  const prev = sched[prompt.id] ?? defaultItem(today)

  // Got it → 2x previous interval, starting at 2, capped at 21.
  // Blanked → back to 1 (due tomorrow).
  const intervalDays =
    result === 'hit' ? Math.min(Math.max(prev.intervalDays * 2, 2), MAX_INTERVAL) : 1

  const history = [...prev.history, { dateISO: today, result }].filter(
    (h) => daysBetween(h.dateISO, today) <= HISTORY_KEEP_DAYS,
  )

  const next: SchedItem = {
    intervalDays,
    dueISO: addDays(today, intervalDays),
    lastResult: result,
    lastSeenISO: today,
    history,
  }

  return { ...sched, [prompt.id]: next }
}

// ---- Deck construction ---------------------------------------------------

function seenDaysAgo(item: SchedItem | undefined, today: string): number | null {
  if (!item?.lastSeenISO) return null
  return daysBetween(item.lastSeenISO, today)
}

function isRecentMiss(item: SchedItem | undefined, today: string): boolean {
  if (!item || item.lastResult !== 'miss') return false
  const ago = seenDaysAgo(item, today)
  return ago != null && ago <= RECENT_MISS_DAYS
}

// Selection weight used for the recency-and-weight biased sampling.
function selectionWeight(prompt: Prompt, item: SchedItem | undefined, today: string): number {
  const ago = seenDaysAgo(item, today)
  if (ago === 0) return 0 // already seen today — don't repeat
  const recency = ago == null ? NEVER_SEEN_RECENCY : ago
  return prompt.weight * recency
}

// Draw one index from `weights` proportional to weight. Returns -1 if all zero.
function weightedPick(weights: number[], rand: () => number): number {
  const total = weights.reduce((s, w) => s + w, 0)
  if (total <= 0) return -1
  let r = rand() * total
  for (let i = 0; i < weights.length; i++) {
    r -= weights[i]
    if (r < 0) return i
  }
  return weights.findIndex((w) => w > 0)
}

/**
 * Build the day's deck.
 * 1. Recent misses first.
 * 2. Then recency+weight biased sampling of the rest.
 * 3. No more than TRACK_CAP prompts from any single track.
 */
export function buildDeck(
  prompts: Prompt[],
  sched: SchedMap,
  size: number,
  today = todayISO(),
  rand: () => number = Math.random,
): DeckCard[] {
  const chosen: Prompt[] = []
  const perTrack: Record<string, number> = {}

  const canTake = (p: Prompt) => (perTrack[p.track] ?? 0) < TRACK_CAP
  const take = (p: Prompt) => {
    chosen.push(p)
    perTrack[p.track] = (perTrack[p.track] ?? 0) + 1
  }

  // Tier 1 — recent misses, oldest-seen first.
  const misses = prompts
    .filter((p) => isRecentMiss(sched[p.id], today))
    .sort((a, b) => (seenDaysAgo(sched[b.id], today) ?? 0) - (seenDaysAgo(sched[a.id], today) ?? 0))
  for (const p of misses) {
    if (chosen.length >= size) break
    if (canTake(p)) take(p)
  }

  // Tier 2 — weighted sampling without replacement from what's left.
  const chosenIds = new Set(chosen.map((p) => p.id))
  const pool = prompts.filter((p) => !chosenIds.has(p.id))
  while (chosen.length < size) {
    const eligible = pool.filter((p) => canTake(p))
    if (eligible.length === 0) break
    const weights = eligible.map((p) => selectionWeight(p, sched[p.id], today))
    let idx = weightedPick(weights, rand)
    // If every remaining eligible prompt has weight 0 (e.g. all seen today),
    // fall back to filling by longest-unseen so the deck still reaches size.
    if (idx === -1) {
      eligible.sort(
        (a, b) =>
          (seenDaysAgo(sched[b.id], today) ?? NEVER_SEEN_RECENCY) -
          (seenDaysAgo(sched[a.id], today) ?? NEVER_SEEN_RECENCY),
      )
      idx = 0
    }
    const picked = eligible[idx]
    take(picked)
    pool.splice(pool.indexOf(picked), 1)
  }

  return chosen.map((p) => ({ promptId: p.id }))
}

// Fisher-Yates shuffle (returns a new array).
function shuffle<T>(arr: T[], rand: () => number): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

/**
 * Build a deck for the chosen scope:
 * - 'daily'  → the weighted, track-capped deck of `size` (spaced repetition).
 * - 'all'    → every prompt, shuffled (a full run-through).
 * - 'tracks' → every prompt in the chosen tracks, shuffled.
 */
export function buildScopeDeck(
  prompts: Prompt[],
  sched: SchedMap,
  scope: QuizScope,
  size: number,
  today = todayISO(),
  rand: () => number = Math.random,
): DeckCard[] {
  if (scope.mode === 'daily') {
    return buildDeck(prompts, sched, size, today, rand)
  }
  const pool =
    scope.mode === 'tracks' && scope.tracks
      ? prompts.filter((p) => scope.tracks!.includes(p.track))
      : prompts
  return shuffle(pool, rand).map((p) => ({ promptId: p.id }))
}

// ---- Done-screen stats ---------------------------------------------------

export function missesByTrack(
  prompts: Prompt[],
  sched: SchedMap,
  windowDays = 14,
  today = todayISO(),
): { track: string; misses: number }[] {
  const byId = new Map(prompts.map((p) => [p.id, p]))
  const tally: Record<string, number> = {}
  for (const [id, item] of Object.entries(sched)) {
    const track = byId.get(id)?.track
    if (!track) continue
    for (const h of item.history) {
      if (h.result === 'miss' && daysBetween(h.dateISO, today) <= windowDays) {
        tally[track] = (tally[track] ?? 0) + 1
      }
    }
  }
  return Object.entries(tally)
    .map(([track, misses]) => ({ track, misses }))
    .sort((a, b) => b.misses - a.misses)
}
