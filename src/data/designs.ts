import type { AccentName } from '../lib/types'

/**
 * Design problem pages.
 *
 * Content is loaded by glob, so **dropping a `.md` file into `./designs/` is
 * enough to make it appear on the site**. The map below only supplies what a
 * file can't tell us — display order, accent, the short archetype label the
 * index groups by, and a one-line tension for the card.
 *
 * A file with no map entry still renders: it falls back to a title parsed from
 * its `#` heading and lands under "Unfiled". A forgotten registry line is a
 * cosmetic problem, never an invisible page.
 *
 * See DESIGN_PAGE_AUTHORING.md at the repo root for the page schema.
 */
const files = import.meta.glob('./designs/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

export interface Design {
  /** URL segment: `/designs/<slug>` */
  slug: string
  /** The page's own `#` heading — shown as the page title. */
  title: string
  /** Short label for the index card. */
  label: string
  /** Group heading on the index. Empty for pinned pages. */
  archetype: string
  /** One line under the card title: what makes this problem hard. */
  tension: string
  accent: AccentName
  md: string
  /** Pinned entries sit above the grouped problems and outside any archetype. */
  pinned?: boolean
}

interface Meta {
  label: string
  archetype: string
  tension: string
  accent: AccentName
  pinned?: boolean
}

/**
 * Keyed by slug. Order here is the order archetypes appear on the index, which
 * follows the archetype map in the authoring spec — the two inverse problems
 * (Uber and Ticketmaster) sit adjacent on purpose, because the contrast between
 * them teaches more than either page alone.
 */
const META: Record<string, Meta> = {
  'interview-mechanics': {
    label: 'Interview mechanics',
    archetype: '',
    tension: 'The clock, the opening, driving your own depth, and the traps that sink strong candidates. True regardless of problem.',
    accent: 'slate',
    pinned: true,
  },
  uber: {
    label: 'Uber',
    archetype: 'Geospatial marketplace',
    tension: 'Huge write throughput, near-zero contention.',
    accent: 'emerald',
  },
  ticketmaster: {
    label: 'Ticketmaster',
    archetype: 'High-contention inventory',
    tension: 'Trivial throughput, catastrophic contention. The inverse of Uber.',
    accent: 'rose',
  },
  messaging: {
    label: 'WhatsApp',
    archetype: 'Real-time messaging & delivery',
    tension: 'Ordering and delivery semantics against fanout cost.',
    accent: 'teal',
  },
  discord: {
    label: 'Discord',
    archetype: 'Real-time messaging & delivery',
    tension:
      'The same archetype as WhatsApp with the constraint inverted: the recipients are already connected, so one write becomes fifty thousand socket writes.',
    accent: 'indigo',
  },
  figma: {
    label: 'Figma',
    archetype: 'Real-time collaborative editing',
    tension: 'Convergence on one shared mutable document. The inverse of WhatsApp: delivery is easy, agreement is the problem.',
    accent: 'violet',
  },
  feed: {
    label: 'Twitter feed',
    archetype: 'Read-heavy content & fanout',
    tension: 'Fanout-on-write against fanout-on-read, over a skewed follower graph.',
    accent: 'indigo',
  },
  'llm-app': {
    label: 'LLM knowledge assistant',
    archetype: 'LLM application',
    tension: 'Non-determinism, latency, cost, and how you prove it works.',
    accent: 'violet',
  },
  cursor: {
    label: 'Cursor Tab',
    archetype: 'Low-latency inference in a loop',
    tension: 'The latency budget forbids the standard pipeline.',
    accent: 'amber',
  },
}

/** `./designs/design-ticketmaster.md` → `ticketmaster`; `00-interview-mechanics.md` → `interview-mechanics`. */
function slugFor(path: string): string {
  const base = path.split('/').pop()!.replace(/\.md$/, '')
  return base.replace(/^\d+-/, '').replace(/^design-/, '')
}

/** The `#` heading, minus markdown emphasis. */
function firstHeading(md: string): string {
  const m = /^#\s+(.*\S)\s*$/m.exec(md)
  return m ? m[1].replace(/[`*_]/g, '').trim() : ''
}

/** The `**Archetype:** …` line, used as the fallback tension for an unregistered file. */
function archetypeLine(md: string): string {
  const m = /^\*\*Archetype:\*\*\s*(.+)$/m.exec(md)
  return m ? m[1].trim() : ''
}

/**
 * Drop the leading `#` heading from the body — `DocLayout` renders it as the
 * page title, and showing it twice reads as a mistake. Stripped before both
 * `extractHeadings` and the renderer see it, so heading ids stay in sync.
 */
function stripLeadingH1(md: string): string {
  return md.replace(/^#\s+.*\S\s*\n+/, '')
}

export const designs: Design[] = Object.entries(files)
  .map(([path, md]) => {
    const slug = slugFor(path)
    const title = firstHeading(md) || slug
    const meta = META[slug]
    return {
      slug,
      title,
      // Fall back to the part of the heading before the em dash: "Design
      // Ticketmaster — High-Contention Inventory" → "Design Ticketmaster".
      label: meta?.label ?? title.split('—')[0].trim(),
      archetype: meta?.archetype ?? 'Unfiled',
      tension: meta?.tension ?? archetypeLine(md),
      accent: meta?.accent ?? 'slate',
      md: stripLeadingH1(md),
      pinned: meta?.pinned,
    }
  })
  .sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
    const ai = Object.keys(META).indexOf(a.slug)
    const bi = Object.keys(META).indexOf(b.slug)
    // Unregistered files (-1) sort last, then alphabetically among themselves.
    if (ai !== bi) return (ai < 0 ? Infinity : ai) - (bi < 0 ? Infinity : bi)
    return a.label.localeCompare(b.label)
  })

export function designBySlug(slug: string | undefined): Design | undefined {
  return designs.find((d) => d.slug === slug)
}

export interface ArchetypeGroup {
  archetype: string
  problems: Design[]
}

/** Pinned pages, then the problems grouped by archetype in registry order. */
export function designsByArchetype(): { pinned: Design[]; groups: ArchetypeGroup[] } {
  const pinned = designs.filter((d) => d.pinned)
  const groups: ArchetypeGroup[] = []
  for (const d of designs) {
    if (d.pinned) continue
    const existing = groups.find((g) => g.archetype === d.archetype)
    if (existing) existing.problems.push(d)
    else groups.push({ archetype: d.archetype, problems: [d] })
  }
  return { pinned, groups }
}
