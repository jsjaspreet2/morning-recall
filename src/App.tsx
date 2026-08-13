import { Suspense, lazy } from 'react'
import { NavLink, Route, Routes, useMatch } from 'react-router-dom'
import PracticePage from './practice/PracticePage'

// The Learn section pulls in the markdown renderer + syntax highlighter, which
// are heavy and unneeded for the morning drill. Code-split them so opening the
// app to Practice stays fast on a phone.
const LearnIndex = lazy(() => import('./learn/LearnIndex'))
const GuidePage = lazy(() => import('./learn/GuidePage'))

function TabLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        [
          'flex-1 text-center py-2.5 rounded-lg text-sm font-medium transition-colors',
          isActive ? 'bg-zinc-800 text-zinc-50' : 'text-zinc-400 hover:text-zinc-200',
        ].join(' ')
      }
    >
      {label}
    </NavLink>
  )
}

export default function App() {
  // Practice is a phone-first morning drill and stays in a single narrow column
  // at every size. A guide is long-form reading with wide code blocks, so it gets
  // the desktop width — and only there, so nothing else in the app reflows.
  const onGuide = useMatch('/learn/:guideId') !== null

  return (
    <div
      className={[
        'min-h-full flex flex-col mx-auto w-full',
        onGuide ? 'max-w-2xl xl:max-w-[88rem]' : 'max-w-2xl',
      ].join(' ')}
    >
      <header className="px-4 pt-3 pb-2 sticky top-0 z-20 bg-[#0a0a0b]/90 backdrop-blur border-b border-zinc-900">
        <nav className="flex gap-1 p-1 rounded-xl bg-zinc-900/60 ring-1 ring-zinc-800">
          <TabLink to="/" label="Practice" />
          <TabLink to="/learn" label="Learn" />
        </nav>
      </header>

      <main className="flex-1 flex flex-col">
        <Suspense
          fallback={<div className="flex-1 grid place-items-center text-zinc-600 text-sm">Loading…</div>}
        >
          <Routes>
            <Route path="/" element={<PracticePage />} />
            <Route path="/learn" element={<LearnIndex />} />
            <Route path="/learn/:guideId" element={<GuidePage />} />
            <Route path="*" element={<PracticePage />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
