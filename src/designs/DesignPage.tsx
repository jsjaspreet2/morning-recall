import { Link, useParams } from 'react-router-dom'
import { designBySlug } from '../data/designs'
import DocLayout from '../learn/DocLayout'

export default function DesignPage() {
  const { slug } = useParams()
  const design = designBySlug(slug)

  if (!design) {
    return (
      <div className="px-4 py-10 text-center">
        <p className="text-zinc-400">That design doesn’t exist.</p>
        <Link to="/designs" className="mt-3 inline-block text-sm text-zinc-300 underline">
          ← Back to Designs
        </Link>
      </div>
    )
  }

  return (
    <DocLayout
      backTo="/designs"
      backLabel="Designs"
      footerLabel="all designs"
      // The page's own `#` heading already carries the qualifier
      // ("Design Ticketmaster — High-Contention Inventory"), so the title is
      // the heading and the subtitle is the tension rather than a repeat.
      title={design.title}
      subtitle={design.pinned ? undefined : design.tension}
      accent={design.accent}
      md={design.md}
      resetKey={slug}
      eyebrow={
        design.archetype && !design.pinned ? (
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-zinc-500">
            {design.archetype}
          </p>
        ) : undefined
      }
    />
  )
}
