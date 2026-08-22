// Theme resolution and application. The one place that knows how a stored
// choice becomes actual pixels.
//
// NOTE: index.html carries an inline copy of resolve()/apply() so the first
// paint is already correct — nothing here is importable that early. If the
// resolution rules or the theme-color values change, change them there too.

import type { ThemeChoice, ResolvedTheme } from './types'

// Kept in sync with the <meta name="theme-color"> default in index.html and the
// --page-bg token in index.css. This is the browser chrome colour on mobile.
const THEME_COLOR: Record<ResolvedTheme, string> = {
  dark: '#0a0a0b',
  light: '#fbfbfc',
}

const DARK_QUERY = '(prefers-color-scheme: dark)'

export function prefersDark(): boolean {
  return window.matchMedia(DARK_QUERY).matches
}

/** A choice plus the current OS preference becomes one of two real themes. */
export function resolve(choice: ThemeChoice): ResolvedTheme {
  if (choice === 'light' || choice === 'dark') return choice
  return prefersDark() ? 'dark' : 'light'
}

/** Drive the `dark` class that every `dark:` utility keys off, plus the bits
 *  Tailwind can't reach: form-control rendering and the mobile browser chrome. */
export function apply(theme: ResolvedTheme): void {
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
  root.style.colorScheme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLOR[theme])
}

/** Subscribe to OS appearance changes. Only worth calling while the choice is
 *  'system' — an explicit light/dark pick should ignore the OS entirely. */
export function watchSystem(onChange: () => void): () => void {
  const mq = window.matchMedia(DARK_QUERY)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}
