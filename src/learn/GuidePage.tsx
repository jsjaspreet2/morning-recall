import { useEffect, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { guideById, pdfUrl } from '../data/guides'
import { accent } from '../lib/accents'
import { extractHeadings } from './toc'
import Markdown from './Markdown'

export default function GuidePage() {
  const { guideId } = useParams()
  const guide = guideById(guideId)
  const headings = useMemo(() => (guide ? extractHeadings(guide.md) : []), [guide])

  // Start each guide at the top when navigating in.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [guideId])

  if (!guide) {
    return (
      <div className="px-4 py-10 text-center">
        <p className="text-zinc-400">That guide doesn’t exist.</p>
        <Link to="/learn" className="mt-3 inline-block text-sm text-zinc-300 underline">
          ← Back to Learn
        </Link>
      </div>
    )
  }

  const ac = accent(guide.accent)

  function jump(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="px-4 py-5">
      <Link
        to="/learn"
        className="text-sm text-zinc-500 hover:text-zinc-300 inline-flex items-center gap-1"
      >
        ← Learn
      </Link>

      <div className="mt-3 flex items-start gap-3">
        <div className={`w-1 self-stretch rounded-full ${ac.bar}`} aria-hidden />
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-zinc-50">{guide.title}</h1>
          <p className="mt-1 text-sm text-zinc-500">{guide.subtitle}</p>
        </div>
      </div>

      <a
        href={pdfUrl(guide)}
        target="_blank"
        rel="noreferrer"
        className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-zinc-300 rounded-lg ring-1 ring-zinc-800 bg-zinc-900/60 px-3 py-1.5 hover:ring-zinc-700"
      >
        ↓ Original PDF
      </a>

      {headings.length > 0 && (
        <details className="mt-5 rounded-xl bg-zinc-900/40 ring-1 ring-zinc-800 overflow-hidden">
          <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-zinc-300">
            Contents · {headings.length} sections
          </summary>
          <nav className="px-2 pb-2">
            <ul className="flex flex-col">
              {headings.map((h, i) => (
                <li key={`${h.id}-${i}`}>
                  <button
                    onClick={() => jump(h.id)}
                    className={[
                      'w-full text-left px-2 py-1.5 rounded-md text-sm hover:bg-zinc-800/60',
                      h.depth === 3 ? 'pl-6 text-zinc-500' : 'text-zinc-300',
                    ].join(' ')}
                  >
                    {h.text}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </details>
      )}

      <article className="mt-6">
        <Markdown md={guide.md} />
      </article>

      <div className="mt-10 pt-6 border-t border-zinc-900 text-center">
        <Link to="/learn" className="text-sm text-zinc-400 hover:text-zinc-200 underline underline-offset-4">
          ← Back to all guides
        </Link>
      </div>
    </div>
  )
}
