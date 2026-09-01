import { useEffect, useMemo, useRef } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { AccentName } from '../lib/types'
import { accent } from '../lib/accents'
import { extractHeadings, groupHeadings } from './toc'
import { useActiveHeading } from './useActiveHeading'
import { useDocTitle } from '../lib/docTitle'
import GuideToc from './GuideToc'
import Markdown from './Markdown'

/** Height of the sticky app header, in px — the nav pill plus its padding. */
const HEADER_HEIGHT = 68

/**
 * The long-form reading layout, shared by guides (`/learn/:guideId`) and design
 * problem pages (`/designs/:slug`).
 *
 * Everything here was tuned once and is easy to regress: the sticky sidebar TOC
 * with its scroll-idle behavior, the separate collapsible TOC for narrow
 * screens, and `min-w-0` on the content column — without which a wide `<pre>`
 * or table pushes the grid past `1fr` and the whole page scrolls sideways.
 * Two copies of that would drift, so there is one.
 */
export default function DocLayout({
  backTo,
  backLabel,
  footerLabel,
  title,
  subtitle,
  accent: accentName,
  eyebrow,
  actions,
  md,
  /** Changing this scrolls back to the top — pass the route param. */
  resetKey,
}: {
  backTo: string
  backLabel: string
  /** Footer link text, which reads better in full: "Back to all guides". */
  footerLabel: string
  title: string
  subtitle?: string
  accent: AccentName
  /** Small label above the title, e.g. the archetype. */
  eyebrow?: ReactNode
  /** Rendered under the header — the guide PDF button, for instance. */
  actions?: ReactNode
  md: string
  resetKey?: string
}) {
  const headings = useMemo(() => extractHeadings(md), [md])
  const sections = useMemo(() => groupHeadings(headings), [headings])
  // jumpTo, not a bare scrollIntoView: it also pins the active section for the
  // duration of the animation. See useActiveHeading.
  const { activeId, jumpTo } = useActiveHeading(headings)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [resetKey])

  // Hand the title to the app header, which shows it once the <h1> below has
  // scrolled away. Cleared on unmount so it never lingers over another route.
  const titleRef = useRef<HTMLHeadingElement>(null)
  const { setDoc, setCompact } = useDocTitle()

  useEffect(() => {
    setDoc({ title, accent: accentName, backTo })
    return () => {
      setDoc(null)
      setCompact(false)
    }
  }, [title, accentName, backTo, setDoc, setCompact])

  useEffect(() => {
    const el = titleRef.current
    if (!el) return
    // Shrink the viewport by the header's height so the swap happens exactly as
    // the <h1> slides under the chrome, rather than when it leaves the screen.
    const io = new IntersectionObserver(([entry]) => setCompact(!entry.isIntersecting), {
      rootMargin: `-${HEADER_HEIGHT}px 0px 0px 0px`,
    })
    io.observe(el)
    return () => io.disconnect()
  }, [setCompact, resetKey])

  const ac = accent(accentName)

  return (
    <div className="px-4 py-5">
      <Link
        to={backTo}
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-500 dark:hover:text-zinc-300 inline-flex items-center gap-1"
      >
        ← {backLabel}
      </Link>

      <div className="mt-3 flex items-start gap-3">
        <div className={`w-1 self-stretch rounded-full ${ac.bar}`} aria-hidden />
        <div className="min-w-0">
          {eyebrow}
          <h1 ref={titleRef} className="text-2xl lg:text-3xl font-bold text-zinc-900 dark:text-zinc-50">
            {title}
          </h1>
          {subtitle && <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-500">{subtitle}</p>}
        </div>
      </div>

      {actions}

      {/* Two columns from xl up; a single stacked column below it, which is what
          phones and tablets get. The sidebar is display:none there rather than
          reflowed, so nothing about the narrow layout changes. */}
      <div className="mt-6 xl:grid xl:grid-cols-[16rem_minmax(0,1fr)] xl:gap-10 xl:items-start">
        <aside className="hidden xl:block sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto pb-6 toc-scroll">
          <GuideToc sections={sections} activeId={activeId} onJump={jumpTo} />
        </aside>

        {/* min-w-0 is load-bearing: without it a wide <pre> or table forces the
            grid column past 1fr and the whole page scrolls sideways. */}
        <div className="min-w-0">
          {/* The collapsible TOC stays for narrow screens, where the sidebar is hidden. */}
          {headings.length > 0 && (
            <details className="xl:hidden mb-6 rounded-xl bg-white ring-1 ring-zinc-200 dark:bg-zinc-900/40 dark:ring-zinc-800 shadow-sm dark:shadow-none overflow-hidden">
              <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Contents · {headings.length} sections
              </summary>
              <nav className="px-2 pb-2">
                <ul className="flex flex-col">
                  {headings.map((h, i) => (
                    <li key={`${h.id}-${i}`}>
                      <button
                        onClick={() => jumpTo(h.id)}
                        className={[
                          'w-full text-left px-2 py-1.5 rounded-md text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800/60',
                          h.depth === 3
                            ? 'pl-6 text-zinc-600 dark:text-zinc-500'
                            : 'text-zinc-700 dark:text-zinc-300',
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

          <article>
            <Markdown md={md} />
          </article>
        </div>
      </div>

      <div className="mt-10 pt-6 border-t border-zinc-200 dark:border-zinc-900 text-center">
        <Link
          to={backTo}
          className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200 underline underline-offset-4"
        >
          ← Back to {footerLabel}
        </Link>
      </div>
    </div>
  )
}
