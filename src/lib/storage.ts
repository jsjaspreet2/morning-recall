// Thin, typed localStorage wrapper. Single user, single device.
// All keys are namespaced so nothing collides with other apps on the origin.
//
// The namespace is still `morning-recall:` — it is the deployed origin's path
// and renaming it would silently drop every existing visitor's theme choice.

import type { ThemeChoice } from './types'

const NS = 'morning-recall:'
const K_THEME = NS + 'theme' // 'light' | 'dark' | 'system'

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
    // storage full / unavailable — the app still works for the session.
  }
}

export const store = {
  // 'system' is the default: a first-time visitor gets whatever their OS is set
  // to. Read by the inline script in index.html too, which parses the same JSON.
  getTheme(): ThemeChoice {
    return read<ThemeChoice>(K_THEME, 'system')
  },
  setTheme(t: ThemeChoice): void {
    write(K_THEME, t)
  },
}
