import { Link } from 'react-router-dom'
import { designsByArchetype } from '../data/designs'
import type { Design } from '../data/designs'
import { accent } from '../lib/accents'

/** The archetype is already the group heading, so a card only carries a chip
 *  when it sits outside a group — i.e. the pinned mechanics page. */
function Card({ design, chip }: { design: Design; chip?: string }) {
  const ac = accent(design.accent)
  return (
    <Link
      to={`/designs/${design.slug}`}
      className="group flex items-stretch rounded-2xl bg-zinc-900/40 ring-1 ring-zinc-800 overflow-hidden hover:ring-zinc-700 transition-colors"
    >
      <div className={`w-1.5 shrink-0 ${ac.bar}`} aria-hidden />
      <div className="flex-1 p-4 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`w-2 h-2 rounded-full ${ac.dot}`} />
          <h3 className="text-base font-semibold text-zinc-100">{design.label}</h3>
          {chip && (
            <span className={`text-[11px] px-2 py-0.5 rounded-full ring-1 ${ac.chip}`}>{chip}</span>
          )}
        </div>
        <p className="mt-1 text-sm text-zinc-500">{design.tension}</p>
      </div>
      <div className="self-center pr-4 text-zinc-600 group-hover:text-zinc-400">→</div>
    </Link>
  )
}

export default function DesignsIndex() {
  const { pinned, groups } = designsByArchetype()

  return (
    <div className="px-4 py-6">
      <h1 className="text-2xl font-bold text-zinc-50">Designs</h1>
      <p className="mt-1 text-sm text-zinc-500">
        One page per problem, each taken end to end. Roughly thirty interview problems reduce to
        these few shapes — so learn the shape, not the answer.
      </p>

      {pinned.length > 0 && (
        <ul className="mt-6 flex flex-col gap-3">
          {pinned.map((d) => (
            <li key={d.slug}>
              <Card design={d} chip="start here" />
            </li>
          ))}
        </ul>
      )}

      {groups.map((group) => (
        <section key={group.archetype} className="mt-8">
          <h2 className="text-[11px] font-bold uppercase tracking-[0.08em] text-zinc-500">
            {group.archetype}
          </h2>
          <ul className="mt-3 flex flex-col gap-3">
            {group.problems.map((d) => (
              <li key={d.slug}>
                <Card design={d} />
              </li>
            ))}
          </ul>
        </section>
      ))}

      <p className="mt-10 pt-6 border-t border-zinc-900 text-xs text-zinc-600">
        Read the mechanics page once. Then per problem: read it through, draw the five-minute
        skeleton cold the next day, answer the recall prompts out loud the day after.
      </p>
    </div>
  )
}
