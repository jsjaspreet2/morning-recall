import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Meta, Prompt, Result } from '../lib/types'
import { accent } from '../lib/accents'
import { guideForAnswerKey } from '../data/guides'
import Timer from './Timer'

interface Props {
  prompt: Prompt
  meta: Meta
  index: number
  total: number
  onMark: (result: Result) => void
  onNext: () => void
}

export default function Card({ prompt, meta, index, total, onMark, onNext }: Props) {
  const [marked, setMarked] = useState<Result | null>(null)
  const track = meta.tracks[prompt.track]
  const ac = accent(track?.accent ?? 'slate')
  const typeInstruction = meta.types[prompt.type]
  const guide = marked ? guideForAnswerKey(prompt.answerKey) : undefined

  function mark(result: Result) {
    setMarked(result)
    onMark(result)
  }

  return (
    <section className="flex-1 flex flex-col px-4 pb-6 pt-4">
      {/* progress */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1 rounded-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
          <div
            className={`h-full ${ac.bar} transition-all`}
            style={{ width: `${((index + (marked ? 1 : 0)) / total) * 100}%` }}
          />
        </div>
        <span className="text-xs text-zinc-600 dark:text-zinc-500 tabular-nums">
          {index + 1} / {total}
        </span>
      </div>

      {/* card body — accent is a thin left marker, not a fill */}
      <div className="flex-1 flex flex-col mt-4 rounded-2xl bg-white ring-1 ring-zinc-200 dark:bg-zinc-900/40 dark:ring-zinc-800 shadow-sm dark:shadow-none overflow-hidden">
        <div className="flex-1 flex">
          <div className={`w-1.5 shrink-0 ${ac.bar}`} aria-hidden />
          <div className="flex-1 flex flex-col p-5 sm:p-6 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-col gap-1 min-w-0">
                <span
                  className={`self-start text-xs font-semibold px-2 py-0.5 rounded-full ring-1 ${ac.chip}`}
                >
                  {track?.label ?? prompt.track}
                </span>
                <span className="text-xs text-zinc-600 dark:text-zinc-500 capitalize">{prompt.type}</span>
              </div>
              <Timer key={prompt.id} seconds={prompt.timeboxSec} />
            </div>

            {/* the prompt text is the interface */}
            <p className="mt-6 text-[1.35rem] leading-snug sm:text-2xl font-medium text-zinc-900 dark:text-zinc-50 text-balance">
              {prompt.prompt}
            </p>

            <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-500">{typeInstruction}</p>

            {/* answer — only after marking */}
            <div className="mt-auto pt-6">
              {marked && (
                <div className="rounded-xl bg-zinc-50 ring-1 ring-zinc-200 dark:bg-zinc-950/60 dark:ring-zinc-800 px-4 py-3.5">
                  {prompt.answer && (
                    <p className="text-[0.98rem] leading-relaxed text-zinc-800 dark:text-zinc-100 whitespace-pre-line">
                      {prompt.answer}
                    </p>
                  )}
                  <div
                    className={[
                      'flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-600 dark:text-zinc-500',
                      prompt.answer ? 'mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800/80' : '',
                    ].join(' ')}
                  >
                    <span>
                      <span className="text-zinc-500 dark:text-zinc-600">Source:</span> {prompt.answerKey}
                    </span>
                    {guide && (
                      <Link
                        to={`/learn/${guide.id}`}
                        className={`font-medium ${ac.text} hover:underline`}
                      >
                        Open guide →
                      </Link>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* actions */}
      <div className="mt-4">
        {!marked ? (
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => mark('miss')}
              className="py-4 rounded-xl text-base font-semibold bg-zinc-100 text-zinc-800 active:bg-zinc-200 ring-1 ring-zinc-300 dark:bg-zinc-800 dark:text-zinc-200 dark:active:bg-zinc-700 dark:ring-zinc-700"
            >
              Blanked
            </button>
            <button
              onClick={() => mark('hit')}
              className="py-4 rounded-xl text-base font-semibold bg-emerald-600 text-white active:bg-emerald-700 ring-1 ring-emerald-600/40 dark:bg-emerald-500/90 dark:text-emerald-950 dark:active:bg-emerald-400 dark:ring-emerald-400/50"
            >
              Got it
            </button>
          </div>
        ) : (
          <button
            onClick={onNext}
            className="w-full py-4 rounded-xl text-base font-semibold bg-zinc-900 text-zinc-50 active:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:active:bg-white"
          >
            {index + 1 < total ? 'Next →' : 'Finish'}
          </button>
        )}
      </div>
    </section>
  )
}
