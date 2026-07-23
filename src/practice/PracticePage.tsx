import { useEffect, useRef, useState } from 'react'
import { meta, prompts, promptById } from '../data/prompts'
import { store } from '../lib/storage'
import { applyResult, buildScopeDeck, missesByTrack } from '../lib/scheduler'
import { addDays, todayISO } from '../lib/dates'
import type { DeckCard, QuizScope, Result, SchedMap, Session } from '../lib/types'
import Card from './Card'
import DoneScreen from './DoneScreen'
import PracticeHome from './PracticeHome'

function firstUnmarked(cards: DeckCard[]): number {
  const i = cards.findIndex((c) => !c.result)
  return i === -1 ? cards.length : i
}

// Drop cards whose prompt no longer exists (prompts.json was edited), so a
// stale saved session never dead-ends on a removed prompt.
function sanitize(s: Session | null): Session | null {
  if (!s) return null
  const cards = s.cards.filter((c) => promptById(c.promptId))
  if (cards.length === 0) return null
  // Resume at the first still-unanswered card (auto-skips any removed prompts).
  return { ...s, cards, pos: firstUnmarked(cards) }
}

export default function PracticePage() {
  const today = todayISO()
  const [sched, setSched] = useState<SchedMap>(() => store.getSched())
  const [session, setSession] = useState<Session | null>(() => sanitize(store.getSession()))
  const streakRecorded = useRef(false)

  function persist(s: Session | null) {
    if (s) store.setSession(s)
    else store.clearSession()
    setSession(s)
  }

  function startQuiz(scope: QuizScope) {
    const cards = buildScopeDeck(prompts, store.getSched(), scope, meta.dailyDeckSize, today)
    streakRecorded.current = false
    persist({ scope, cards, pos: 0, startedISO: today })
  }

  function handleMark(result: Result) {
    if (!session) return
    const card = session.cards[session.pos]
    const prompt = promptById(card.promptId)
    if (!prompt) return
    const nextSched = applyResult(sched, prompt, result, today)
    setSched(nextSched)
    store.setSched(nextSched)
    const cards = session.cards.map((c, i) => (i === session.pos ? { ...c, result } : c))
    persist({ ...session, cards })
  }

  function handleNext() {
    if (!session) return
    persist({ ...session, pos: session.pos + 1 })
  }

  const done = !!session && session.pos >= session.cards.length

  // Record the streak once per day, when a run is completed.
  useEffect(() => {
    if (!done || streakRecorded.current) return
    streakRecorded.current = true
    const s = store.getStreak()
    if (s.lastCompletedISO === today) return
    const yesterday = addDays(today, -1)
    const count = s.lastCompletedISO === yesterday ? s.count + 1 : 1
    store.setStreak({ lastCompletedISO: today, count })
  }, [done, today])

  if (!session) {
    return <PracticeHome onStart={startQuiz} streak={store.getStreak().count} />
  }

  if (done) {
    const hits = session.cards.filter((c) => c.result === 'hit').length
    const misses = session.cards.filter((c) => c.result === 'miss').length
    return (
      <DoneScreen
        scopeLabel={session.scope.label}
        hits={hits}
        misses={misses}
        streak={store.getStreak().count}
        topMisses={missesByTrack(prompts, sched, 14, today)}
        meta={meta}
        onRetry={() => startQuiz(session.scope)}
        onMenu={() => persist(null)}
      />
    )
  }

  const card = session.cards[session.pos]
  const prompt = promptById(card.promptId)
  // sanitize() guarantees every card resolves; this guard is just for types.
  if (!prompt) return null

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center justify-between px-4 pt-3">
        <span className="text-xs font-medium text-zinc-500 truncate">{session.scope.label}</span>
        <button
          onClick={() => persist(null)}
          className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1 -mr-2"
        >
          End
        </button>
      </div>
      <Card
        key={prompt.id}
        prompt={prompt}
        meta={meta}
        index={session.pos}
        total={session.cards.length}
        onMark={handleMark}
        onNext={handleNext}
      />
    </div>
  )
}
