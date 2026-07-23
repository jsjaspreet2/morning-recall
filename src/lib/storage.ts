// Thin, typed localStorage wrapper. Single user, single device (per the spec).
// All keys are namespaced so nothing collides with other apps on the origin.

import type { Session, SchedMap } from './types'

const NS = 'morning-recall:'
const K_SCHED = NS + 'sched'
const K_SESSION = NS + 'session' // the active/in-progress quiz run
const K_STREAK = NS + 'streak' // { lastCompletedISO, count }

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (raw == null) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function write(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // storage full / unavailable — practice still works for the session.
  }
}

export const store = {
  getSched(): SchedMap {
    return read<SchedMap>(K_SCHED, {})
  },
  setSched(m: SchedMap): void {
    write(K_SCHED, m)
  },

  getSession(): Session | null {
    return read<Session | null>(K_SESSION, null)
  },
  setSession(s: Session): void {
    write(K_SESSION, s)
  },
  clearSession(): void {
    localStorage.removeItem(K_SESSION)
  },

  getStreak(): { lastCompletedISO: string | null; count: number } {
    return read(K_STREAK, { lastCompletedISO: null, count: 0 })
  },
  setStreak(s: { lastCompletedISO: string | null; count: number }): void {
    write(K_STREAK, s)
  },

  // Escape hatch: wipe scheduling history and streak (does not touch guides).
  resetAll(): void {
    ;[K_SCHED, K_SESSION, K_STREAK].forEach((k) => localStorage.removeItem(k))
  },
}
