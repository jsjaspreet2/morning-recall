import { Suspense, lazy } from 'react'
import { NavLink, Route, Routes, useMatch } from 'react-router-dom'
import PracticePage from './practice/PracticePage'
import ThemeToggle from './ThemeToggle'

// Learn and Designs pull in the markdown renderer + syntax highlighter, which
// are heavy and unneeded for the morning drill. Code-split them so opening the
// app to Practice stays fast on a phone.
const LearnIndex = lazy(() => import('./learn/LearnIndex'))
const GuidePage = lazy(() => import('./learn/GuidePage'))
const DesignsIndex = lazy(() => import('./designs/DesignsIndex'))
const DesignPage = lazy(() => import('./designs/DesignPage'))

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

  return (
    <div
      className={[
        'min-h-full flex flex-col mx-auto w-full',
        wide ? 'max-w-2xl xl:max-w-[88rem]' : onIndex ? 'max-w-2xl lg:max-w-4xl' : 'max-w-2xl',
      ].join(' ')}
    >
      <header className="px-4 pt-3 pb-2 sticky top-0 z-20 bg-[var(--header-bg)] backdrop-blur border-b border-zinc-200 dark:border-zinc-900">
        <div className="flex items-center gap-2">
          <nav className="flex-1 sm:flex-none min-w-0 flex gap-1 p-1 rounded-xl bg-zinc-100 ring-1 ring-zinc-200 dark:bg-zinc-900/60 dark:ring-zinc-800">
            <TabLink to="/" label="Practice" />
            <TabLink to="/learn" label="Learn" />
            <TabLink to="/designs" label="Designs" />
          </nav>
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
