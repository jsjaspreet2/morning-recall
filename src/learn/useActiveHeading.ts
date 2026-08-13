import { useCallback, useEffect, useRef, useState } from 'react'
import type { Heading } from './toc'

/**
 * Safety net only. Nothing observable happens when this fires — measurement runs
 * on scroll, so unlocking with the page still is invisible until the reader
 * moves. It exists so the lock can never be stuck forever.
 */
const JUMP_CEILING_MS = 4000

/**
 * Events that mean the reader has taken the scroll back: trackpad and mouse
 * wheel, touch, keyboard paging, and pressing the scrollbar.
 */
const TAKEOVER = ['wheel', 'touchstart', 'keydown', 'pointerdown'] as const

/**
 * Which heading is currently being read, plus the jump that navigates to one.
 *
 * Two things make this less trivial than it looks.
 *
 * 1. WHAT COUNTS AS "CURRENT". Deliberately not an IntersectionObserver on
 *    heading visibility: in a guide this dense, long stretches have no heading on
 *    screen at all, and the highlight would blank out mid-section — exactly when
 *    you most want to know where you are. Instead, take the last heading whose
 *    top has passed the reading line. That always names a section, including
 *    while you sit in the middle of a 300-line code block.
 *
 * 2. A JUMP IS AN ANSWER, NOT A JOURNEY. `scrollIntoView({behavior:'smooth'})`
 *    fires a scroll event every frame of its animation. Tracking those sweeps the
 *    highlight through all ~120 headings between origin and target, expanding a
 *    different group each step, so entries shift under the pointer the whole way
 *    down. Debouncing only delays that.
 *
 *    So `jumpTo` pins the clicked heading and stops measuring — and critically,
 *    it does NOT unpin when the scrolling stops. Releasing on scroll-idle means
 *    the release itself re-measures the moment the animation lands, and if the
 *    target could not reach the reading line (anything near the end of the
 *    document, where the page runs out of room to scroll) the highlight snaps
 *    somewhere else. That snap is the jank.
 *
 *    The pin lifts only when the reader scrolls of their own accord, which is
 *    the only moment their position genuinely differs from what they clicked.
 */
export function useActiveHeading(headings: Heading[], offset = 96) {
  const [active, setActive] = useState<string | null>(null)
  // While true, scroll is ours and is not measured.
  const pinnedRef = useRef(false)
  // Tears down whatever jump is in flight. Held in a ref so a second click, or
  // an unmount, can cancel the first jump's listeners and timer.
  const unpinRef = useRef<(() => void) | null>(null)

  // A jump can outlive the component — click a heading, hit back mid-animation —
  // and its listeners would leak.
  useEffect(() => () => unpinRef.current?.(), [])

  useEffect(() => {
    if (headings.length === 0) return

    let frame = 0

    function measure() {
      frame = 0
      if (pinnedRef.current) return

      let current: string | null = null
      for (const h of headings) {
        const el = document.getElementById(h.id)
        if (!el) continue
        if (el.getBoundingClientRect().top - offset <= 0) current = h.id
        else break // headings are in document order, so the first one below the
        // line means every later one is too
      }

      // At the very bottom the page has run out of scroll, so the last few
      // headings never cross the reading line and the highlight sticks on
      // whichever one did. Relax the line to the middle of the viewport there —
      // enough to reach the trailing headings, strict enough that a heading
      // sitting low on screen is still ahead of you rather than behind.
      const atBottom = window.innerHeight + window.scrollY >= document.body.scrollHeight - 2
      if (atBottom) {
        const line = window.innerHeight / 2
        for (const h of headings) {
          const top = document.getElementById(h.id)?.getBoundingClientRect().top
          if (top !== undefined && top < line) current = h.id
        }
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

  const jumpTo = useCallback((id: string) => {
    const el = document.getElementById(id)
    if (!el) return

    // A second click supersedes the first jump, so the earlier one's timer can't
    // unpin while this one is still moving.
    unpinRef.current?.()

    // Land on the answer straight away rather than arriving there via every
    // section in between — and stay there.
    setActive(id)
    pinnedRef.current = true

    let ceiling = 0
    const unpin = () => {
      window.clearTimeout(ceiling)
      for (const type of TAKEOVER) window.removeEventListener(type, unpin)
      pinnedRef.current = false
      if (unpinRef.current === unpin) unpinRef.current = null
    }

    for (const type of TAKEOVER) window.addEventListener(type, unpin, { passive: true })
    ceiling = window.setTimeout(unpin, JUMP_CEILING_MS)
    unpinRef.current = unpin

    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  return { activeId: active, jumpTo }
}
