import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { ThemeChoice } from './types'
import { apply, resolve, watchSystem } from './theme'
import { store } from './storage'

interface ThemeContextValue {
  choice: ThemeChoice
  setChoice: (c: ThemeChoice) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

// The provider sits at the root rather than inside the toggle so applying the
// theme is tied to the app's lifetime, not to one widget staying mounted.
export function ThemeProvider({ children }: { children: ReactNode }) {
  // The inline script in index.html has already put the right class on <html>
  // by now; starting from the same stored value means the first render agrees
  // with what's on screen instead of fighting it.
  const [choice, setChoiceState] = useState<ThemeChoice>(() => store.getTheme())

  useEffect(() => {
    apply(resolve(choice))

    // Follow the OS only while the user hasn't pinned a theme — an explicit
    // Light should stay light when the Mac flips to dark at sunset. Returning
    // the unsubscribe from the same effect means switching away from 'system'
    // tears the listener down immediately.
    if (choice !== 'system') return
    return watchSystem(() => apply(resolve('system')))
  }, [choice])

  const setChoice = useCallback((c: ThemeChoice) => {
    store.setTheme(c)
    setChoiceState(c)
  }, [])

  return <ThemeContext.Provider value={{ choice, setChoice }}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>')
  return ctx
}
