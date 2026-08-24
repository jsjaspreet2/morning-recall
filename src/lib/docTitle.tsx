import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { AccentName } from './types'

/**
 * Lets the long-form pages put their title into the app header once their own
 * <h1> has scrolled away, so it's always clear which guide or design you're in.
 *
 * Why a context rather than App reading the route param and looking the title up
 * itself: designs.ts is properly code-split — a ~384KB lazy chunk reached only
 * through the lazy DesignsIndex/DesignPage — and importing it into App would
 * pull all of it into the main bundle. DocLayout already sits inside that chunk
 * and serves both routes, so it publishes upward instead.
 *
 * (guides.ts is a different story: it is already in the main bundle, because
 * practice/Card.tsx imports guideForAnswerKey for its post-mark cross-link and
 * Practice is not lazy. That's pre-existing, and worth untangling separately if
 * the initial payload ever matters.)
 */
export interface DocTitle {
  title: string
  accent: AccentName
  /** Where the header's back control goes — /learn or /designs. */
  backTo: string
}

interface DocTitleValue {
  doc: DocTitle | null
  /** True once the page's own <h1> has passed up behind the header. */
  compact: boolean
  setDoc: (d: DocTitle | null) => void
  setCompact: (v: boolean) => void
}

const DocTitleContext = createContext<DocTitleValue | null>(null)

export function DocTitleProvider({ children }: { children: ReactNode }) {
  const [doc, setDoc] = useState<DocTitle | null>(null)
  const [compact, setCompact] = useState(false)
  // setDoc/setCompact are stable, so this only changes when the values do.
  const value = useMemo(() => ({ doc, compact, setDoc, setCompact }), [doc, compact])
  return <DocTitleContext.Provider value={value}>{children}</DocTitleContext.Provider>
}

export function useDocTitle(): DocTitleValue {
  const ctx = useContext(DocTitleContext)
  if (!ctx) throw new Error('useDocTitle must be used inside <DocTitleProvider>')
  return ctx
}
