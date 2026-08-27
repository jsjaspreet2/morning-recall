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
import figmaScreenMd from './guides/figma-screen.md?raw'
import discordScreenMd from './guides/discord-screen.md?raw'
import openaiScreenMd from './guides/openai-screen.md?raw'

export interface Guide {
  id: string
  title: string
  subtitle: string
  accent: AccentName
  md: string
  /** Filename under public/pdfs. Omit for guides with no PDF yet — the download
   *  link is hidden rather than left pointing at a 404. */
  pdf?: string
  /** Company-specific screen prep: a self-contained track for one interview on
   *  one date — round script, worked problems, the lot. Grouped separately from
   *  the general guides on the Learn index, since the two are read for very
   *  different reasons. */
  screen?: true
}

export const guides: Guide[] = [
  // Pinned to the top through 8/28 — the nearest date. Drop it back down afterwards.
  {
    id: 'cursor-screen',
    screen: true,
    title: 'Cursor Screen — 8/28',
    subtitle:
      'The last thirty-six hours, hour by hour: what each round grades, where a product engineer’s depth belongs, client-side system design, five worked designs, and the coding-hour script.',
    accent: 'rose',
    md: cursorScreenMd,
  },
  // Screen was 8/26. Drop it down the list once the Cursor and Figma screens have passed.
  {
    id: 'discord-screen',
    screen: true,
    title: 'Discord Skill Challenge — 8/26',
    subtitle:
      'Seventy-five minutes on your own machine, a TCP server driven over nc: the round script, the line server every part is made of, five worked problems, and framing done properly.',
    accent: 'indigo',
    md: discordScreenMd,
  },
  // Pinned to the top through 9/9. Drop it back down the list afterwards.
  {
    id: 'figma-screen',
    screen: true,
    title: 'Figma Screen — 9/9',
    subtitle:
      'One hour, one multi-part problem in CoderPad: the round script, the document model that every Figma question is made of, five worked problems, and undo/redo done properly.',
    accent: 'violet',
    md: figmaScreenMd,
  },
  // Pinned through 9/17 — the last of the four screens. Drop it down afterwards.
  {
    id: 'openai-screen',
    screen: true,
    title: 'OpenAI Screen — 9/16 & 9/17',
    subtitle:
      'Two hours across two days, architecture then coding: the researched question bank, the streaming spine end to end, four worked architectures, and the two chapters that decide the coding hour — text streaming and text-editor concepts.',
    accent: 'emerald',
    md: openaiScreenMd,
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
      'Fourteen components you will be asked to build — API, ARIA contract, full implementation, and the test plan — plus the fifteen techniques underneath them.',
    accent: 'indigo',
    md: uieComponentsMd,
  },
  {
    id: 'technology',
    title: 'Technology Choices',
    subtitle:
      'Which technology and why — 26 technologies across server and browser: mechanism, CAP, when to reach for it, and when it flips.',
    accent: 'teal',
    md: technologyMd,
    // No PDF: the shipped PDF still carries the per-fact change markers the
    // markdown has folded away. Regenerate before re-adding the link.
  },
]

/**
 * Split the index into its two halves. Company screens keep their hand-set
 * order (nearest date first — see the comments on each entry); the general
 * guides follow in declaration order.
 */
export function guidesBySection(): { screens: Guide[]; general: Guide[] } {
  return {
    screens: guides.filter((g) => g.screen),
    general: guides.filter((g) => !g.screen),
  }
}

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
  if (key.startsWith('openai screen')) return guideById('openai-screen')
  if (key.startsWith('discord screen')) return guideById('discord-screen')
  if (key.startsWith('figma screen')) return guideById('figma-screen')
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
