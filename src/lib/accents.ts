// Full, literal Tailwind class strings per accent so nothing is purged and no
// class name is built by string concatenation — that includes the `dark:`
// halves, which have to sit inside the same literal for the scanner to see them.
// Accents are used only as thin markers (a bar, a dot, a chip) — never a full
// background — per the spec.
//
// The two themes need different weights: the -400/-300 shades that read well on
// near-black wash out on white, so light mode drops two stops to -600/-700. The
// /10 chip fill is faint enough to work on either surface unchanged.

import type { AccentName } from './types'

interface AccentClasses {
  bar: string // vertical marker bar on a card
  dot: string // small filled dot
  text: string // colored label text
  chip: string // small pill (bg + text + ring)
}

const MAP: Record<AccentName, AccentClasses> = {
  emerald: {
    bar: 'bg-emerald-600 dark:bg-emerald-400',
    dot: 'bg-emerald-600 dark:bg-emerald-400',
    text: 'text-emerald-700 dark:text-emerald-300',
    chip: 'bg-emerald-500/10 text-emerald-700 ring-emerald-600/30 dark:text-emerald-300 dark:ring-emerald-500/30',
  },
  indigo: {
    bar: 'bg-indigo-600 dark:bg-indigo-400',
    dot: 'bg-indigo-600 dark:bg-indigo-400',
    text: 'text-indigo-700 dark:text-indigo-300',
    chip: 'bg-indigo-500/10 text-indigo-700 ring-indigo-600/30 dark:text-indigo-300 dark:ring-indigo-500/30',
  },
  rose: {
    bar: 'bg-rose-600 dark:bg-rose-400',
    dot: 'bg-rose-600 dark:bg-rose-400',
    text: 'text-rose-700 dark:text-rose-300',
    chip: 'bg-rose-500/10 text-rose-700 ring-rose-600/30 dark:text-rose-300 dark:ring-rose-500/30',
  },
  teal: {
    bar: 'bg-teal-600 dark:bg-teal-400',
    dot: 'bg-teal-600 dark:bg-teal-400',
    text: 'text-teal-700 dark:text-teal-300',
    chip: 'bg-teal-500/10 text-teal-700 ring-teal-600/30 dark:text-teal-300 dark:ring-teal-500/30',
  },
  violet: {
    bar: 'bg-violet-600 dark:bg-violet-400',
    dot: 'bg-violet-600 dark:bg-violet-400',
    text: 'text-violet-700 dark:text-violet-300',
    chip: 'bg-violet-500/10 text-violet-700 ring-violet-600/30 dark:text-violet-300 dark:ring-violet-500/30',
  },
  amber: {
    bar: 'bg-amber-600 dark:bg-amber-400',
    dot: 'bg-amber-600 dark:bg-amber-400',
    text: 'text-amber-700 dark:text-amber-300',
    chip: 'bg-amber-500/10 text-amber-800 ring-amber-600/30 dark:text-amber-300 dark:ring-amber-500/30',
  },
  slate: {
    bar: 'bg-slate-600 dark:bg-slate-400',
    dot: 'bg-slate-600 dark:bg-slate-400',
    text: 'text-slate-700 dark:text-slate-300',
    chip: 'bg-slate-500/10 text-slate-700 ring-slate-600/30 dark:text-slate-300 dark:ring-slate-500/30',
  },
}

export function accent(name: AccentName): AccentClasses {
  return MAP[name] ?? MAP.slate
}
