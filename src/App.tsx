import { Suspense, lazy, useEffect } from 'react'
import { Link, NavLink, Route, Routes, useMatch } from 'react-router-dom'
import type { AccentName } from './lib/types'
import PracticePage from './practice/PracticePage'
import ThemeToggle from './ThemeToggle'
import { useDocTitle } from './lib/docTitle'
import { accent } from './lib/accents'

// Learn and Designs pull in the markdown renderer + syntax highlighter, which
// are heavy and unneeded for the morning drill. Code-split them so opening the
// app to Practice stays fast on a phone.
const LearnIndex = lazy(() => import('./learn/LearnIndex'))
const GuidePage = lazy(() => import('./learn/GuidePage'))
const DesignsIndex = lazy(() => import('./designs/DesignsIndex'))
const DesignPage = lazy(() => import('./designs/DesignPage'))

const SITE = 'Morning Recall'

/**
 * The browser tab title.
 *
 * Guide and design pages already publish their title upward through
 * `DocTitleProvider` for the compact header, so this reuses that rather than
 * re-deriving it from the route param — which would mean importing designs.ts
 * into the main bundle and undoing its code-splitting (see docTitle.tsx).
 *
 * Titles are trimmed at the em dash — "Design Airbnb — Interval Inventory &
 * Search-Dominant Booking" becomes "Design Airbnb" — because a tab shows about
 * twenty characters and the half after the dash is never one of them. It's the
 * same trim designs.ts uses for a card label. All three tabs label themselves,
 * Practice included — they're peers, not a landing page and its subpages, and
 * with several tabs open the consistency is what makes them findable.
 */
function useBrowserTitle(section: string | null) {
  useEffect(() => {
    document.title = section ? `${section} · ${SITE}` : SITE
  }, [section])
}

function TabLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        [
          'flex-1 sm:flex-none sm:px-6 text-center py-2.5 rounded-lg text-sm font-medium transition-colors',
          isActive
            ? 'bg-white text-zinc-900 shadow-sm dark:bg-zinc-800 dark:text-zinc-50 dark:shadow-none'
            : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200',
        ].join(' ')
      }
    >
      {label}
    </NavLink>
  )
}

/**
 * What the header shows once a guide's own <h1> has scrolled away: a back
 * control, the accent dot, and the title. It replaces the tabs rather than
 * stacking below them — a second row would change the header's height, and the
 * sidebar's `sticky top-20` and the headings' `scroll-margin-top` are both
 * measured against the current one.
 */
function DocTitleBar({ title, accentName, backTo }: { title: string; accentName: AccentName; backTo: string }) {
  return (
    <div className="doc-title-in flex-1 min-w-0 flex items-center gap-2 h-12">
      <Link
        to={backTo}
        aria-label="Back"
        className="shrink-0 grid place-items-center w-8 h-8 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-800/60 transition-colors"
      >
        ←
      </Link>
      <span className={`w-2 h-2 rounded-full shrink-0 ${accent(accentName).dot}`} aria-hidden />
      <span className="truncate text-sm font-semibold text-zinc-800 dark:text-zinc-100">{title}</span>
    </div>
  )
}

export default function App() {
  // Three width tiers. Practice stays a single narrow column at every size —
  // the prompt is the interface, and widening it would work against that. The
  // Learn and Designs indexes get enough room for a two-up card grid. A guide
  // or design page is long-form reading with wide code blocks and tables, so it
  // takes the full desktop width.
  const onGuide = useMatch('/learn/:guideId') !== null
  const onDesign = useMatch('/designs/:slug') !== null
  const onLearnIndex = useMatch('/learn') !== null
  const onDesignsIndex = useMatch('/designs') !== null
  const wide = onGuide || onDesign
  const onIndex = onLearnIndex || onDesignsIndex

  // A doc page publishes its title here; `compact` flips once its <h1> is gone.
  const { doc, compact } = useDocTitle()
  const showDocTitle = doc !== null && compact

  // A doc page's own title wins once it has mounted; until then (its chunk is
  // lazy) the tab shows the bare site name rather than a stale section.
  useBrowserTitle(
    doc?.title.split('—')[0].trim() ??
      (onLearnIndex ? 'Learn' : onDesignsIndex ? 'Designs' : onGuide || onDesign ? null : 'Practice'),
  )

  return (
    <div
      className={[
        'min-h-full flex flex-col mx-auto w-full',
        wide ? 'max-w-2xl xl:max-w-[88rem]' : onIndex ? 'max-w-2xl lg:max-w-4xl' : 'max-w-2xl',
      ].join(' ')}
    >
      <header className="px-4 pt-3 pb-2 sticky top-0 z-20 bg-[var(--header-bg)] backdrop-blur border-b border-zinc-200 dark:border-zinc-900">
        <div className="flex items-center gap-2">
          {showDocTitle ? (
            <DocTitleBar title={doc.title} accentName={doc.accent} backTo={doc.backTo} />
          ) : (
            <nav className="flex-1 sm:flex-none min-w-0 flex gap-1 p-1 rounded-xl bg-zinc-100 ring-1 ring-zinc-200 dark:bg-zinc-900/60 dark:ring-zinc-800">
              <TabLink to="/" label="Practice" />
              <TabLink to="/learn" label="Learn" />
              <TabLink to="/designs" label="Designs" />
            </nav>
          )}
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 flex flex-col">
        <Suspense
          fallback={<div className="flex-1 grid place-items-center text-zinc-500 dark:text-zinc-600 text-sm">Loading…</div>}
        >
          <Routes>
            <Route path="/" element={<PracticePage />} />
            <Route path="/learn" element={<LearnIndex />} />
            <Route path="/learn/:guideId" element={<GuidePage />} />
            <Route path="/designs" element={<DesignsIndex />} />
            <Route path="/designs/:slug" element={<DesignPage />} />
            <Route path="*" element={<PracticePage />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
