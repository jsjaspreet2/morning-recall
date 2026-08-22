import { Link, useParams } from 'react-router-dom'
import { guideById, pdfUrl } from '../data/guides'
import DocLayout from './DocLayout'

export default function GuidePage() {
  const { guideId } = useParams()
  const guide = guideById(guideId)

  if (!guide) {
    return (
      <div className="px-4 py-10 text-center">
        <p className="text-zinc-600 dark:text-zinc-400">That guide doesn’t exist.</p>
        <Link to="/learn" className="mt-3 inline-block text-sm text-zinc-700 dark:text-zinc-300 underline">
          ← Back to Learn
        </Link>
      </div>
    )
  }

  const pdf = pdfUrl(guide)

  return (
    <DocLayout
      backTo="/learn"
      backLabel="Learn"
      footerLabel="all guides"
      title={guide.title}
      subtitle={guide.subtitle}
      accent={guide.accent}
      md={guide.md}
      resetKey={guideId}
      actions={
        pdf && (
          <a
            href={pdf}
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-zinc-700 rounded-lg ring-1 ring-zinc-200 bg-zinc-100 hover:ring-zinc-300 dark:text-zinc-300 dark:ring-zinc-800 dark:bg-zinc-900/60 dark:hover:ring-zinc-700 px-3 py-1.5"
          >
            ↓ Original PDF
          </a>
        )
      }
    />
  )
}
