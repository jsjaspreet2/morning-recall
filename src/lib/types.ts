// Shapes that mirror prompts.json plus the local scheduling state.

export type AccentName =
  | 'emerald'
  | 'indigo'
  | 'rose'
  | 'teal'
  | 'violet'
  | 'amber'
  | 'slate'

export type PromptType = 'fact' | 'procedure' | 'spoken'

export interface TrackMeta {
  label: string
  accent: AccentName
}

export interface Meta {
  title: string
  subtitle: string
  version: number
  rule: string
  dailyDeckSize: number
  tracks: Record<string, TrackMeta>
  types: Record<PromptType, string>
}

export interface Prompt {
  id: string
  track: string
  type: PromptType
  timeboxSec: number
  weight: number
  prompt: string
  // A short 1-2 sentence answer, shown after marking so a blank is recoverable.
  answer?: string
  answerKey: string
}

export interface PromptsFile {
  meta: Meta
  prompts: Prompt[]
}

export type Result = 'hit' | 'miss'

// Per-prompt scheduling state, persisted in localStorage.
export interface SchedItem {
  intervalDays: number
  dueISO: string // date (YYYY-MM-DD) this prompt is next due
  lastResult?: Result
  lastSeenISO?: string // date last shown
  history: { dateISO: string; result: Result }[]
}

export type SchedMap = Record<string, SchedItem>

// A card as presented in a deck, tracking this session's result.
export interface DeckCard {
  promptId: string
  result?: Result
}

// What the user chose to practice.
export type QuizMode = 'daily' | 'all' | 'tracks'

export interface QuizScope {
  mode: QuizMode
  tracks?: string[] // for mode 'tracks'
  label: string // human label, e.g. "Daily mix" or "React"
}

// A live practice run, persisted so a reload resumes where you left off.
export interface Session {
  scope: QuizScope
  cards: DeckCard[]
  pos: number
  startedISO: string
}

// What the user picked in the header's theme selector. 'system' defers to the
// OS and keeps following it; 'light'/'dark' pin it. Persisted in localStorage.
export type ThemeChoice = 'light' | 'dark' | 'system'

// What 'system' collapses to once the OS preference is read.
export type ResolvedTheme = 'light' | 'dark'
