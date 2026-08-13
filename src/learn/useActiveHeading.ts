import { useEffect, useState } from 'react'
import type { Heading } from './toc'

/**
 * Which heading is currently being read, for highlighting in the sidebar.
 *
 * Deliberately NOT an IntersectionObserver on "is the heading visible": in a
 * guide this dense, long stretches have no heading on screen at all, and the
 * highlight would blank out mid-section — exactly when you most want to know
 * where you are.
 *
 * Instead: on scroll, pick the last heading whose top has passed the reading
 * line. That always names a section, including while you sit in the middle of a
 * 300-line code block.
 *
 * `deps` re-runs the measurement after the document changes (a new guide, or
 * headings that only exist once markdown has rendered).
 */
export function useActiveHeading(headings: Heading[], offset = 96): string | null {
  const [active, setActive] = useState<string | null>(null)

  useEffect(() => {
    if (headings.length === 0) return

    let frame = 0

    function measure() {
      frame = 0
      let current: string | null = null
      for (const h of headings) {
        const el = document.getElementById(h.id)
        if (!el) continue
        if (el.getBoundingClientRect().top - offset <= 0) current = h.id
        else break // headings are in document order, so the first one below the
        // line means every later one is too
      }
      // Before the first heading scrolls past, highlight it anyway rather than
      // showing nothing at the very top of the page.
      setActive(current ?? headings[0]?.id ?? null)
    }

    function onScroll() {
      // Coalesce to one measurement per frame; this runs on every scroll event.
      if (frame === 0) frame = requestAnimationFrame(measure)
    }

    measure()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll, { passive: true })
    return () => {
      if (frame) cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [headings, offset])

  return active
}
