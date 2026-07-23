import { useEffect, useRef, useState } from 'react'

function fmt(totalSec: number): string {
  const s = Math.abs(totalSec)
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${String(r).padStart(2, '0')}`
}

/**
 * A pacing signal, not a fail state. Counts down from `seconds`; at zero it
 * turns amber and keeps counting up. Never auto-advances, never plays a sound.
 * Remount (via a `key` on the prompt id) to restart for a new card.
 */
export default function Timer({ seconds }: { seconds: number }) {
  const [elapsed, setElapsed] = useState(0)
  const start = useRef<number | null>(null)

  useEffect(() => {
    let raf = 0
    const tick = (t: number) => {
      if (start.current == null) start.current = t
      setElapsed(Math.floor((t - start.current) / 1000))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  const remaining = seconds - elapsed
  const overtime = remaining < 0
  const label = overtime ? `+${fmt(remaining)}` : fmt(remaining)

  return (
    <div
      className={[
        'inline-flex items-center gap-2 tabular-nums font-mono text-sm px-3 py-1 rounded-full ring-1 transition-colors',
        overtime
          ? 'text-amber-300 ring-amber-500/40 bg-amber-500/10'
          : 'text-zinc-400 ring-zinc-800 bg-zinc-900/60',
      ].join(' ')}
      role="timer"
      aria-live="off"
    >
      <span
        className={[
          'inline-block w-1.5 h-1.5 rounded-full',
          overtime ? 'bg-amber-400' : 'bg-zinc-600',
        ].join(' ')}
      />
      {label}
    </div>
  )
}
