import { Link } from 'react-router-dom'
import { guides } from '../data/guides'
import { accent } from '../lib/accents'

export default function LearnIndex() {
  return (
    <div className="px-4 py-6">
      <h1 className="text-2xl font-bold text-zinc-50">Learn</h1>
      <p className="mt-1 text-sm text-zinc-500">
        The answer key. Read these <em>after</em> you attempt the morning deck — not before.
      </p>

      <ul className="mt-6 flex flex-col gap-3">
        {guides.map((g) => {
          const ac = accent(g.accent)
          return (
            <li key={g.id}>
              <Link
                to={`/learn/${g.id}`}
                className="group flex items-stretch rounded-2xl bg-zinc-900/40 ring-1 ring-zinc-800 overflow-hidden hover:ring-zinc-700 transition-colors"
              >
                <div className={`w-1.5 shrink-0 ${ac.bar}`} aria-hidden />
                <div className="flex-1 p-4 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${ac.dot}`} />
                    <h2 className="text-base font-semibold text-zinc-100">{g.title}</h2>
                  </div>
                  <p className="mt-1 text-sm text-zinc-500">{g.subtitle}</p>
                </div>
                <div className="self-center pr-4 text-zinc-600 group-hover:text-zinc-400">→</div>
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
