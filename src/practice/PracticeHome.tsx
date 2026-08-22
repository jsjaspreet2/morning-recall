import { useMemo, useState } from 'react'
import { meta, prompts } from '../data/prompts'
import { accent } from '../lib/accents'
import type { QuizScope } from '../lib/types'

interface Props {
  onStart: (scope: QuizScope) => void
  streak: number
}

export default function PracticeHome({ onStart, streak }: Props) {
  const [selected, setSelected] = useState<string[]>([])

  // Prompt counts per track, in the order tracks are declared in meta.
  const trackList = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const p of prompts) counts[p.track] = (counts[p.track] ?? 0) + 1
    return Object.entries(meta.tracks)
      .filter(([key]) => counts[key] > 0)
      .map(([key, t]) => ({ key, label: t.label, accent: t.accent, count: counts[key] }))
  }, [])

  const total = prompts.length
  const selectedCount = selected.reduce(
    (n, k) => n + (trackList.find((t) => t.key === k)?.count ?? 0),
    0,
  )

  function toggle(key: string) {
    setSelected((s) => (s.includes(key) ? s.filter((k) => k !== key) : [...s, key]))
  }

  function startSelected() {
    if (selected.length === 0) return
    const label =
      selected.length === 1
        ? (trackList.find((t) => t.key === selected[0])?.label ?? 'Focused')
        : `${selected.length} areas`
    onStart({ mode: 'tracks', tracks: selected, label })
  }

  return (
    <div className="px-4 py-6 pb-28">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">{meta.title}</h1>
        {streak > 0 && (
          <span className="text-sm text-amber-700 dark:text-amber-300 tabular-nums">🔥 {streak}-day streak</span>
        )}
      </div>
      <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-500">{meta.subtitle}</p>

      {/* primary modes */}
      <div className="mt-6 grid grid-cols-1 gap-3">
        <button
          onClick={() => onStart({ mode: 'daily', label: 'Daily mix' })}
          className="group flex items-center justify-between rounded-2xl bg-white ring-1 ring-zinc-200 hover:ring-zinc-300 dark:bg-zinc-900/50 dark:ring-zinc-800 dark:hover:ring-zinc-700 shadow-sm dark:shadow-none px-5 py-4 text-left"
        >
          <span>
            <span className="block text-base font-semibold text-zinc-800 dark:text-zinc-100">Daily mix</span>
            <span className="block text-sm text-zinc-600 dark:text-zinc-500">
              {Math.min(meta.dailyDeckSize, total)} prompts, weighted to what you miss
            </span>
          </span>
          <span className="text-xl text-zinc-500">→</span>
        </button>

        <button
          onClick={() => onStart({ mode: 'all', label: 'Everything' })}
          className="group flex items-center justify-between rounded-2xl bg-white ring-1 ring-zinc-200 hover:ring-zinc-300 dark:bg-zinc-900/50 dark:ring-zinc-800 dark:hover:ring-zinc-700 shadow-sm dark:shadow-none px-5 py-4 text-left"
        >
          <span>
            <span className="block text-base font-semibold text-zinc-800 dark:text-zinc-100">Everything</span>
            <span className="block text-sm text-zinc-600 dark:text-zinc-500">
              All {total} prompts, shuffled — a full run-through
            </span>
          </span>
          <span className="text-xl text-zinc-500">→</span>
        </button>
      </div>

      {/* targeted areas */}
      <h2 className="mt-8 text-xs uppercase tracking-wide text-zinc-600 dark:text-zinc-500">Focus on an area</h2>
      <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-500">Tap one or more, then start.</p>
      <div className="mt-3 grid grid-cols-2 gap-2.5">
        {trackList.map((t) => {
          const ac = accent(t.accent)
          const on = selected.includes(t.key)
          return (
            <button
              key={t.key}
              onClick={() => toggle(t.key)}
              aria-pressed={on}
              className={[
                'flex items-center justify-between gap-2 rounded-xl px-3.5 py-3 text-left ring-1 transition-colors',
                on
                  ? 'bg-white ring-zinc-900 shadow-sm dark:bg-zinc-800 dark:ring-zinc-600 dark:shadow-none'
                  : 'bg-white ring-zinc-200 hover:ring-zinc-300 shadow-sm dark:bg-zinc-900/40 dark:ring-zinc-800 dark:hover:ring-zinc-700 dark:shadow-none',
              ].join(' ')}
            >
              <span className="flex items-center gap-2 min-w-0">
                <span className={`w-2 h-2 rounded-full shrink-0 ${ac.dot}`} />
                <span className="text-sm font-medium text-zinc-800 dark:text-zinc-100 truncate">{t.label}</span>
              </span>
              <span className="text-xs text-zinc-600 dark:text-zinc-500 tabular-nums shrink-0">{t.count}</span>
            </button>
          )
        })}
      </div>

      {/* sticky start bar for the selection */}
      {selected.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-30 px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-3 start-bar-fade">
          <div className="max-w-2xl mx-auto flex items-center gap-3">
            <button
              onClick={() => setSelected([])}
              className="text-sm text-zinc-600 dark:text-zinc-400 px-3 py-3.5"
            >
              Clear
            </button>
            <button
              onClick={startSelected}
              className="flex-1 py-3.5 rounded-xl text-base font-semibold bg-emerald-600 text-white active:bg-emerald-700 dark:bg-emerald-500/90 dark:text-emerald-950 dark:active:bg-emerald-400"
            >
              Start · {selectedCount} {selectedCount === 1 ? 'prompt' : 'prompts'} →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
