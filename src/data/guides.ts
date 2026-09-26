import type { AccentName } from '../lib/types'

import discordFinalMd from './guides/discord-final.md?raw'
import finalLoopsMd from './guides/final-loops.md?raw'
import openaiCodingMd from './guides/openai-coding.md?raw'

import javascriptMd from './guides/javascript.md?raw'
import reactCssMd from './guides/react-css.md?raw'
import accessibilityMd from './guides/accessibility.md?raw'
import codingPatternsMd from './guides/coding-patterns.md?raw'
import systemDesignMd from './guides/system-design.md?raw'
import dataModelingMd from './guides/data-modeling.md?raw'
import animationMd from './guides/animation.md?raw'
import technologyMd from './guides/technology.md?raw'
import componentRoundMd from './guides/component-round.md?raw'
import uieComponentsMd from './guides/uie-components.md?raw'
import clientSideSystemDesignMd from './guides/client-side-system-design.md?raw'
import systemDesignCardMd from './guides/system-design-card.md?raw'
import figmaScreenMd from './guides/figma-screen.md?raw'
import discordScreenMd from './guides/discord-screen.md?raw'
import openaiScreenMd from './guides/openai-screen.md?raw'
import openaiTranscriptMd from './guides/openai-transcript.md?raw'

export interface Guide {
  id: string
  title: string
  subtitle: string
  accent: AccentName
  md: string
  /** Filename under public/pdfs. Omit for guides with no PDF yet — the download
   *  link is hidden rather than left pointing at a 404. */
  pdf?: string
  /** Company prep and current loop plans, grouped above general references.
   *  The field name is retained for existing registrations. */
  screen?: true
  /** Hidden from active prep, but still reachable by its original URL. */
  archived?: true
}

export const guides: Guide[] = [
  {
    id: 'discord-final',
    screen: true,
    title: 'Discord — Final Round, 48 Hours',
    subtitle: 'Five rounds on Mon 9/28: design, web app, principles, retro, DSA. Two days, hour by hour.',
    accent: 'indigo',
    md: discordFinalMd,
  },
  {
    id: 'final-loops',
    screen: true,
    title: 'Final Loops — OpenAI & Discord',
    subtitle: 'Start here: a seven-day plan, the highest-value rereads, project discussions, and what to defer.',
    accent: 'amber',
    md: finalLoopsMd,
  },
  {
    id: 'openai-coding',
    screen: true,
    title: 'OpenAI Coding — Top 20',
    subtitle: 'The supplied study sheet, integrated: twenty TypeScript examples, core-build priorities, corrections, and explicit contracts.',
    accent: 'emerald',
    md: openaiCodingMd,
  },
  {
    id: 'figma-screen',
    archived: true,
    screen: true,
    title: 'Figma Screen — Archived',
    subtitle:
      'One hour, one multi-part problem in CoderPad: the round script, the document model that every Figma question is made of, five worked problems, and undo/redo done properly.',
    accent: 'violet',
    md: figmaScreenMd,
  },
  // Retained at its original URL as technical reference for the final loop.
  {
    id: 'openai-screen',
    screen: true,
    title: 'OpenAI — Screen Reference',
    subtitle:
      'Historical September screen preparation: streaming, text-editor concepts, worked architectures, and testing. Start with Final Loops for the current plan.',
    accent: 'emerald',
    md: openaiScreenMd,
  },
  // The 9/17 coding hour, built part by part. Sits with its parent screen guide.
  {
    id: 'openai-transcript',
    screen: true,
    title: 'OpenAI Transcript Walkthrough',
    subtitle:
      'The five-part streaming-chat problem built the way the interviewer adds parts: the code at each step, what changes between steps, the two tests, and what to say.',
    accent: 'teal',
    md: openaiTranscriptMd,
  },
  // The retained screen reference. The final is Mon 9/28; the 48-hour plan is discord-final above.
  {
    id: 'discord-screen',
    screen: true,
    title: 'Discord — Final Round',
    subtitle:
      'Final-loop priorities plus the retained screen reference: the line server every coding part is made of, five worked problems, protocol design, correctness without a test runner, and Discord itself.',
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
  // The storage half of System Design, as a procedure: what to write down in the
  // five minutes a round spends on tables, and the rep that makes it automatic.
  {
    id: 'data-modeling',
    title: 'Data Modeling Under Pressure',
    subtitle:
      'From prompt to a written data model in five minutes: the six-step procedure, the notation, the four stores as modeling rules, the ten questions interviewers press on, ten worked models, and the drill.',
    accent: 'amber',
    md: dataModelingMd,
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
  // The read-it-at-T-30 sheet for the design round, built from a reviewed mock:
  // the process card, the minute-35 NFR audit, and a 0–2 rubric with its re-run
  // threshold. Everything on it exists in longer form in the three guides above
  // and on the Demand response and Smart-meter telemetry design pages.
  {
    id: 'system-design-card',
    title: 'The System Design Round — one page',
    subtitle:
      'Read at T-30: the rubric echo, the load-proportional budget, the state machine before the boxes, kill a box, the minute-35 NFR audit, a 0–2 rubric with its re-run threshold, and five same-archetype reps.',
    accent: 'amber',
    md: systemDesignCardMd,
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

/** Active company prep first, general references next, completed prep archived. */
export function guidesBySection(): { screens: Guide[]; general: Guide[]; archived: Guide[] } {
  return {
    screens: guides.filter((g) => g.screen && !g.archived),
    general: guides.filter((g) => !g.screen && !g.archived),
    archived: guides.filter((g) => g.archived),
  }
}

export function guideById(id: string | undefined): Guide | undefined {
  return guides.find((g) => g.id === id)
}

export function pdfUrl(guide: Guide): string | undefined {
  return guide.pdf ? `${import.meta.env.BASE_URL}pdfs/${guide.pdf}` : undefined
}

