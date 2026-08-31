import type { AccentName } from '../lib/types'

import javascriptMd from './guides/javascript.md?raw'
import reactCssMd from './guides/react-css.md?raw'
import accessibilityMd from './guides/accessibility.md?raw'
import codingPatternsMd from './guides/coding-patterns.md?raw'
import systemDesignMd from './guides/system-design.md?raw'
import animationMd from './guides/animation.md?raw'
import technologyMd from './guides/technology.md?raw'
import componentRoundMd from './guides/component-round.md?raw'
import uieComponentsMd from './guides/uie-components.md?raw'
import clientSideSystemDesignMd from './guides/client-side-system-design.md?raw'
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
  // The 8/26 screen passed; this is what's left of that guide, kept for the final
  // round. Last among the screens only because the final round has no date yet —
  // pin it back to the top when one lands.
  {
    id: 'discord-screen',
    screen: true,
    title: 'Discord — Final Round',
    subtitle:
      'The screen is passed and the final round has no date yet. What survived: the line server every coding part is made of, five worked problems, protocol design, correctness without a test runner, and Discord itself.',
    accent: 'indigo',
    md: discordScreenMd,
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
  // The client half of System Design, salvaged from the retired Cursor screen guide:
  // the chapters that were never Cursor-specific.
  {
    id: 'client-side-system-design',
    title: 'Client-Side System Design',
    subtitle:
      'The client as a replica, not a view: the seven-layer checklist, the transport ladder, streaming and backpressure, offline and reconciliation — plus component API design and test quality.',
    accent: 'amber',
    md: clientSideSystemDesignMd,
  },
  {
    id: 'animation',
    title: 'Animation & Motion',
    subtitle: 'Performant web animation: transitions, transforms, and reduced-motion.',
    accent: 'violet',
    md: animationMd,
    pdf: 'Animation-Motion-Cheatsheet-v1.pdf',
  },
  // Pinned first: the read-it-at-T-30 sheet. Everything on it exists in longer
  // form elsewhere; this is the operational version.
  {
    id: 'component-round',
    title: 'The Component Round — one page',
    subtitle:
      'The clock, the first ninety seconds, the prop signature, the async block, and the traps ranked. Read this last.',
    accent: 'indigo',
    md: componentRoundMd,
  },
  {
    id: 'uie-components',
    title: 'UIE Components',
    subtitle:
      'Fourteen components you will be asked to build — API, ARIA contract, full implementation, and the test plan — plus the eighteen techniques underneath them and the prop-design forks that decide the API.',
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

