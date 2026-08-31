import { Link } from 'react-router-dom'
import { guidesBySection } from '../data/guides'
import type { Guide } from '../data/guides'
import { accent } from '../lib/accents'

function GuideCard({ guide }: { guide: Guide }) {
  const ac = accent(guide.accent)
  return (
    <Link
      to={`/learn/${guide.id}`}
      className="group flex h-full items-stretch rounded-2xl bg-white ring-1 ring-zinc-200 hover:ring-zinc-300 dark:bg-zinc-900/40 dark:ring-zinc-800 dark:hover:ring-zinc-700 shadow-sm dark:shadow-none overflow-hidden transition-all motion-safe:hover:-translate-y-0.5 hover:shadow-md dark:hover:shadow-none"
    >
      <div className={`w-1.5 shrink-0 ${ac.bar}`} aria-hidden />
      <div className="flex-1 p-4 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full shrink-0 ${ac.dot}`} />
          <h3 className="text-base font-semibold text-zinc-800 dark:text-zinc-100">{guide.title}</h3>
        </div>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-500">{guide.subtitle}</p>
      </div>
      <div className="self-center pr-4 text-zinc-400 group-hover:text-zinc-700 dark:text-zinc-600 dark:group-hover:text-zinc-400">
        →
      </div>
    </Link>
  )
}

function Section({ label, guides }: { label: string; guides: Guide[] }) {
  if (guides.length === 0) return null
  return (
    <section className="mt-8 first:mt-6">
      <h2 className="text-[11px] font-bold uppercase tracking-[0.08em] text-zinc-600 dark:text-zinc-500">
        {label}
      </h2>
      <ul className="mt-3 grid gap-3 sm:grid-cols-2">
        {guides.map((g) => (
          <li key={g.id}>
            <GuideCard guide={g} />
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function LearnIndex() {
  // Two halves, company screens first: a screen is prep for one interview on one
  // date and goes stale after it, while the general guides are the standing
  // reference. Mixing them made the list read as one undifferentiated pile.
  const { screens, general } = guidesBySection()

  return (
    <div className="px-4 py-6">
      <h1 className="text-2xl lg:text-3xl font-bold text-zinc-900 dark:text-zinc-50">Learn</h1>
      <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-500">
        The standing reference: every round, worked end to end.
      </p>

      <Section label="Company screens" guides={screens} />
      <Section label="General guides" guides={general} />
    </div>
  )
}
