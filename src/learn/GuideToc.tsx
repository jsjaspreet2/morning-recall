import { useEffect, useRef } from 'react'
import type { Heading, TocSection } from './toc'

interface GuideTocProps {
  sections: TocSection[]
  activeId: string | null
  onJump: (id: string) => void
}

/**
 * Desktop sidebar contents. Only the section being read expands its `###`
 * children — with 132 headings in the UIE guide, showing them all at once is
 * worse than showing none.
 */
export default function GuideToc({ sections, activeId, onJump }: GuideTocProps) {
  const navRef = useRef<HTMLElement>(null)

  // Keep the highlighted entry inside the sidebar's own scroll box.
  //
  // Deliberately not scrollIntoView: that walks every scrollable ancestor, so it
  // can scroll the PAGE as well as the sidebar — and during a smooth jump that
  // means the sidebar fighting the animation it is supposed to be following.
  // Setting scrollTop on the container touches nothing else.
  useEffect(() => {
    if (!activeId) return
    const box = navRef.current?.parentElement
    const el = navRef.current?.querySelector<HTMLElement>(`[data-toc-id="${CSS.escape(activeId)}"]`)
    if (!box || !el) return

    const top = el.offsetTop - box.offsetTop
    const bottom = top + el.offsetHeight
    if (top < box.scrollTop) box.scrollTop = top
    else if (bottom > box.scrollTop + box.clientHeight) box.scrollTop = bottom - box.clientHeight
  }, [activeId])

  function entryClass(h: Heading, isActive: boolean) {
    const base =
      'block w-full text-left rounded-md transition-colors border-l-2 leading-snug ' +
      (h.depth === 3 ? 'pl-4 pr-2 py-1 text-[12.5px] ' : 'px-2 py-1.5 text-[13px] font-medium ')
    if (isActive) return base + 'border-zinc-500 bg-zinc-800/70 text-zinc-100'
    return base + 'border-transparent text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/40'
  }

  return (
    <nav ref={navRef} aria-label="On this page" className="flex flex-col gap-0.5">
      <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-zinc-600">
        On this page
      </p>

      {sections.map((section) => {
        const sectionIds = [section.heading.id, ...section.children.map((c) => c.id)]
        const isCurrent = activeId !== null && sectionIds.includes(activeId)

        return (
          <div key={section.heading.id}>
            <button
              data-toc-id={section.heading.id}
              onClick={() => onJump(section.heading.id)}
              aria-current={activeId === section.heading.id ? 'location' : undefined}
              className={entryClass(section.heading, activeId === section.heading.id)}
            >
              {section.heading.text}
            </button>

            {isCurrent && section.children.length > 0 && (
              <div className="mt-0.5 mb-1 flex flex-col gap-0.5">
                {section.children.map((child) => (
                  <button
                    key={child.id}
                    data-toc-id={child.id}
                    onClick={() => onJump(child.id)}
                    aria-current={activeId === child.id ? 'location' : undefined}
                    className={entryClass(child, activeId === child.id)}
                  >
                    {child.text}
                  </button>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </nav>
  )
}
