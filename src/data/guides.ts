import type { AccentName } from '../lib/types'

import javascriptMd from './guides/javascript.md?raw'
import reactCssMd from './guides/react-css.md?raw'
import accessibilityMd from './guides/accessibility.md?raw'
import codingPatternsMd from './guides/coding-patterns.md?raw'
import systemDesignMd from './guides/system-design.md?raw'
import animationMd from './guides/animation.md?raw'
import technologyMd from './guides/technology.md?raw'
import uieComponentsMd from './guides/uie-components.md?raw'
import cursorScreenMd from './guides/cursor-screen.md?raw'

export interface Guide {
  id: string
  title: string
  subtitle: string
  accent: AccentName
  md: string
  /** Filename under public/pdfs. Omit for guides with no PDF yet — the download
   *  link is hidden rather than left pointing at a 404. */
  pdf?: string
}

export const guides: Guide[] = [
  // Pinned to the top through 8/28. Drop it back down the list afterwards.
  {
    id: 'cursor-screen',
    title: 'Cursor Screen — 8/28',
    subtitle:
      'Twelve-day plan for the two-hour screen: what each round grades, client-side system design, five worked designs, and the coding-hour script.',
    accent: 'rose',
    md: cursorScreenMd,
  },
  {
    id: 'javascript',
    title: 'JavaScript',
    subtitle: 'Language mechanics, browser runtime, async control, and implementation prompts.',
    accent: 'emerald',
    md: javascriptMd,
    pdf: 'javascript_interview_field_guide_v2.pdf',
  },
  {
    id: 'react-css',
    title: 'React & CSS',
    subtitle: 'React rendering and hooks, plus CSS layout, specificity, and stacking.',
    accent: 'indigo',
    md: reactCssMd,
    pdf: 'react_css_frontend_interview_field_guide_v3.pdf',
  },
  {
    id: 'accessibility',
    title: 'Accessibility',
    subtitle: 'Mnemonic-first a11y: roles, accessible names, focus, and live regions.',
    accent: 'rose',
    md: accessibilityMd,
    pdf: 'Accessibility_Cheatsheet_v2_dark.pdf',
  },
  {
    id: 'coding-patterns',
    title: 'Coding Patterns',
    subtitle: 'Pattern recognition and reusable templates for timed coding rounds.',
    accent: 'teal',
    md: codingPatternsMd,
    pdf: 'coding_patterns_interview_field_guide_v2.pdf',
  },
  {
    id: 'system-design',
    title: 'System Design',
    subtitle:
      'A decision reference, not a course: the 45-minute loop, capacity math, correctness, failure, and AI-native systems.',
    accent: 'amber',
    md: systemDesignMd,
    // No PDF: the markdown has diverged from the shipped PDF. Regenerate before
    // re-adding the link rather than serving the older text.
  },
  {
    id: 'animation',
    title: 'Animation & Motion',
    subtitle: 'Performant web animation: transitions, transforms, and reduced-motion.',
    accent: 'violet',
    md: animationMd,
    pdf: 'Animation-Motion-Cheatsheet-v1.pdf',
  },
  {
    id: 'uie-components',
    title: 'UIE Components',
    subtitle:
      'Fourteen components you will be asked to build — API, ARIA contract, full implementation, and the test plan.',
    accent: 'indigo',
    md: uieComponentsMd,
  },
  {
    id: 'technology',
    title: 'Technology Choices',
    subtitle: 'Which technology and why — 14 stores, mechanism, CAP, when to reach for it, and when it flips.',
    accent: 'teal',
    md: technologyMd,
    // No PDF: the shipped PDF still carries the per-fact change markers the
    // markdown has folded away. Regenerate before re-adding the link.
  },
]

export function guideById(id: string | undefined): Guide | undefined {
  return guides.find((g) => g.id === id)
}

export function pdfUrl(guide: Guide): string | undefined {
  return guide.pdf ? `${import.meta.env.BASE_URL}pdfs/${guide.pdf}` : undefined
}

/**
 * Map a prompt's `answerKey` label to a guide, when one exists. Used only for
 * the post-mark "Open guide" cross-link in Practice. answerKeys such as
 * "None yet…", "Your STAR drafts", or "DDIA Ch 5" have no in-app guide.
 */
export function guideForAnswerKey(answerKey: string): Guide | undefined {
  const key = answerKey.toLowerCase()
  if (key.startsWith('cursor screen')) return guideById('cursor-screen')
  if (key.startsWith('javascript')) return guideById('javascript')
  if (key.startsWith('react')) return guideById('react-css')
  if (key.startsWith('accessibility')) return guideById('accessibility')
  if (key.startsWith('coding patterns')) return guideById('coding-patterns')
  if (key.startsWith('system design')) return guideById('system-design')
  if (key.startsWith('animation')) return guideById('animation')
  if (key.startsWith('technology')) return guideById('technology')
  return undefined
}
