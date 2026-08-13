import { useCallback, useEffect, useRef, useState } from 'react'
import type { Heading } from './toc'

/** Give up on a smooth scroll after this long, so the lock can never stick. */
const JUMP_CEILING_MS = 1200
/** How long the page must be still before a jump counts as finished. */
const SETTLE_MS = 120

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
 * 2. PROGRAMMATIC SCROLL MUST NOT BE TRACKED. `scrollIntoView({behavior:
 *    'smooth'})` fires a scroll event every frame of its animation, so tracking
 *    it sweeps the highlight through every heading between origin and target —
 *    120 of them in this guide. Each step re-renders the sidebar and expands a
 *    different section, so entries jump around under the pointer until it lands.
 *    Debouncing only delays that sweep. Instead `jumpTo` sets the target
 *    immediately and suspends measurement until the page is still again.
 */
export function useActiveHeading(headings: Heading[], offset = 96) {
  const [active, setActive] = useState<string | null>(null)
  // While true, scroll events are ours and are ignored.
  const jumpingRef = useRef(false)
  // Tears down whatever jump is in flight. Held in a ref so a second click, or
  // an unmount, can cancel the first jump's listeners and timers.
  const endJumpRef = useRef<(() => void) | null>(null)

  // A jump can outlive the component — click a heading, hit back mid-animation —
  // and its listeners would leak.
  useEffect(() => () => endJumpRef.current?.(), [])

  useEffect(() => {
    if (headings.length === 0) return

    let frame = 0

    function measure() {
      frame = 0
      if (jumpingRef.current) return
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

  const jumpTo = useCallback((id: string) => {
    const el = document.getElementById(id)
    if (!el) return

    // A click during an earlier animation supersedes it. Without this, the first
    // jump's own backstop timer fires mid-flight and unlocks tracking while the
    // second is still moving — the sweep comes straight back.
    endJumpRef.current?.()

    // Land on the answer straight away rather than arriving there via every
    // section in between.
    setActive(id)
    jumpingRef.current = true

    let settle = 0
    let ceiling = 0

    // If the reader grabs the wheel mid-flight, they own the scroll again — hand
    // tracking straight back rather than making them wait out the animation.
    const TAKEOVER = ['wheel', 'touchstart', 'keydown'] as const

    const release = () => {
      window.clearTimeout(settle)
      window.clearTimeout(ceiling)
      window.removeEventListener('scroll', onScrollWhileJumping)
      for (const type of TAKEOVER) window.removeEventListener(type, release)
      jumpingRef.current = false
      if (endJumpRef.current === release) endJumpRef.current = null
    }

    function onScrollWhileJumping() {
      // Each scroll event pushes the settle timer out; when they stop arriving,
      // the animation has finished. Works without the `scrollend` event, which
      // still isn't everywhere.
      window.clearTimeout(settle)
      settle = window.setTimeout(release, SETTLE_MS)
    }

    window.addEventListener('scroll', onScrollWhileJumping, { passive: true })
    for (const type of TAKEOVER) window.addEventListener(type, release, { passive: true })
    // Backstop: if the target is already in place, no scroll event ever fires and
    // nothing above would release the lock.
    ceiling = window.setTimeout(release, JUMP_CEILING_MS)
    settle = window.setTimeout(release, SETTLE_MS * 3)
    endJumpRef.current = release

    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  return { activeId: active, jumpTo }
}
