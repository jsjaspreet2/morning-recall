// Shapes shared across the app. The guide and design registries carry their own
// types next to their data (see data/guides.ts, data/designs.ts); what lives
// here is what more than one of them needs.

export type AccentName =
  | 'emerald'
  | 'indigo'
  | 'rose'
  | 'teal'
  | 'violet'
  | 'amber'
  | 'slate'

// What the user picked in the header's theme selector. 'system' defers to the
// OS and keeps following it; 'light'/'dark' pin it. Persisted in localStorage.
export type ThemeChoice = 'light' | 'dark' | 'system'

// What 'system' collapses to once the OS preference is read.
export type ResolvedTheme = 'light' | 'dark'
