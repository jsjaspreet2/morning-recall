import { Link } from 'react-router-dom'
import type { Meta } from '../lib/types'
import { accent } from '../lib/accents'

interface Props {
  scopeLabel: string
  hits: number
  misses: number
  streak: number
  topMisses: { track: string; misses: number }[]
  meta: Meta
  onRetry: () => void
  onMenu: () => void
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col items-center rounded-2xl bg-zinc-900/40 ring-1 ring-zinc-800 py-6">
      <span className="text-4xl font-bold text-zinc-50 tabular-nums">{value}</span>
      <span className="mt-1 text-xs uppercase tracking-wide text-zinc-500">{label}</span>
    </div>
  )
}

export default function DoneScreen({
  scopeLabel,
  hits,
  misses,
  streak,
  topMisses,
  meta,
  onRetry,
  onMenu,
}: Props) {
  const total = hits + misses
  const weak = topMisses.slice(0, 3)

  return (
    <div className="flex-1 flex flex-col px-4 py-10">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-zinc-50">{scopeLabel} · done</h1>
        <p className="mt-1 text-sm text-zinc-500">
          {total === 0 ? 'No prompts in this set.' : 'Run it again, or pick another area.'}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3 mt-8">
        <Stat value={`${hits}/${total}`} label="Got it" />
        <Stat value={String(streak)} label={streak === 1 ? 'Day streak' : 'Day streak'} />
        <Stat value={String(misses)} label="Blanked" />
      </div>

      <div className="mt-8">
        <h2 className="text-xs uppercase tracking-wide text-zinc-500 mb-3">
          Weakest tracks · last 14 days
        </h2>
        {weak.length === 0 ? (
          <p className="text-sm text-zinc-500">
            No misses logged yet. Keep going and this will surface where to focus.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {weak.map(({ track, misses: m }) => {
              const t = meta.tracks[track]
              const ac = accent(t?.accent ?? 'slate')
              return (
                <li
                  key={track}
                  className="flex items-center justify-between rounded-xl bg-zinc-900/40 ring-1 ring-zinc-800 px-4 py-3"
                >
                  <span className="flex items-center gap-2.5 text-sm text-zinc-200">
                    <span className={`w-2 h-2 rounded-full ${ac.dot}`} />
                    {t?.label ?? track}
                  </span>
                  <span className="text-sm text-zinc-500 tabular-nums">
                    {m} {m === 1 ? 'miss' : 'misses'}
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="mt-auto pt-10 grid grid-cols-1 gap-3">
        <button
          onClick={onRetry}
          className="w-full py-4 rounded-xl text-base font-semibold bg-zinc-100 text-zinc-900 active:bg-white"
        >
          Practice again
        </button>
        <button
          onClick={onMenu}
          className="w-full py-3.5 rounded-xl text-sm font-semibold bg-zinc-900/50 ring-1 ring-zinc-800 text-zinc-200 active:bg-zinc-800"
        >
          Back to menu
        </button>
        <Link
          to="/learn"
          className="mt-1 text-center text-sm font-medium text-zinc-400 hover:text-zinc-200 underline underline-offset-4"
        >
          Study the guides →
        </Link>
      </div>
    </div>
  )
}
