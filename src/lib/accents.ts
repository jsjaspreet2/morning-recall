// Full, literal Tailwind class strings per accent so nothing is purged and no
// class name is built by string concatenation. Accents are used only as thin
// markers (a bar, a dot, a chip) — never a full background — per the spec.

import type { AccentName } from './types'

interface AccentClasses {
  bar: string // vertical marker bar on a card
  dot: string // small filled dot
  text: string // colored label text
  chip: string // small pill (bg + text + ring)
}

const MAP: Record<AccentName, AccentClasses> = {
  emerald: {
    bar: 'bg-emerald-400',
    dot: 'bg-emerald-400',
    text: 'text-emerald-300',
    chip: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  },
  indigo: {
    bar: 'bg-indigo-400',
    dot: 'bg-indigo-400',
    text: 'text-indigo-300',
    chip: 'bg-indigo-500/10 text-indigo-300 ring-indigo-500/30',
  },
  rose: {
    bar: 'bg-rose-400',
    dot: 'bg-rose-400',
    text: 'text-rose-300',
    chip: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
  },
  teal: {
    bar: 'bg-teal-400',
    dot: 'bg-teal-400',
    text: 'text-teal-300',
    chip: 'bg-teal-500/10 text-teal-300 ring-teal-500/30',
  },
  violet: {
    bar: 'bg-violet-400',
    dot: 'bg-violet-400',
    text: 'text-violet-300',
    chip: 'bg-violet-500/10 text-violet-300 ring-violet-500/30',
  },
  amber: {
    bar: 'bg-amber-400',
    dot: 'bg-amber-400',
    text: 'text-amber-300',
    chip: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
  },
  slate: {
    bar: 'bg-slate-400',
    dot: 'bg-slate-400',
    text: 'text-slate-300',
    chip: 'bg-slate-500/10 text-slate-300 ring-slate-500/30',
  },
}

export function accent(name: AccentName): AccentClasses {
  return MAP[name] ?? MAP.slate
}
