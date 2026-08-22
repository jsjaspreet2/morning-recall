import { useTheme } from './lib/useTheme'
import type { ThemeChoice } from './lib/types'

// Inline SVGs rather than emoji glyphs (☀ / ☾ render at wildly different
// weights across platforms) and rather than an icon package — three 16px marks
// don't justify a dependency in an app that has none.
const ICON = 'w-4 h-4 stroke-current'

function SunIcon() {
  return (
    <svg className={ICON} viewBox="0 0 24 24" fill="none" strokeWidth={1.6} aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path strokeLinecap="round" d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M18.7 5.3l-1.4 1.4M6.7 17.3l-1.4 1.4" />
    </svg>
  )
}

function SystemIcon() {
  return (
    <svg className={ICON} viewBox="0 0 24 24" fill="none" strokeWidth={1.6} aria-hidden="true">
      <rect x="2.75" y="4.75" width="18.5" height="12.5" rx="2" />
      <path strokeLinecap="round" d="M9 20.5h6" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg className={ICON} viewBox="0 0 24 24" fill="none" strokeWidth={1.6} aria-hidden="true">
      <path strokeLinejoin="round" d="M20 14.2A8.2 8.2 0 1 1 9.8 4a6.6 6.6 0 0 0 10.2 10.2Z" />
    </svg>
  )
}

const OPTIONS: { value: ThemeChoice; label: string; Icon: () => JSX.Element }[] = [
  { value: 'light', label: 'Light', Icon: SunIcon },
  { value: 'system', label: 'System', Icon: SystemIcon },
  { value: 'dark', label: 'Dark', Icon: MoonIcon },
]

export default function ThemeToggle() {
  const { choice, setChoice } = useTheme()

  // Native radios rather than hand-rolled role="radio" buttons: arrow-key
  // navigation, focus management and group semantics all come for free, and
  // getting roving tabindex wrong is easier than it looks. The inputs are
  // sr-only; the <span> next to each is what you actually see, styled off
  // `peer-checked` — which is why the input must stay its previous sibling.
  return (
    <fieldset className="shrink-0 ml-auto flex items-center gap-0.5 p-1 rounded-xl bg-zinc-100 ring-1 ring-zinc-200 dark:bg-zinc-900/60 dark:ring-zinc-800">
      <legend className="sr-only">Colour theme</legend>
      {OPTIONS.map(({ value, label, Icon }) => (
        <label key={value} title={label}>
          <input
            type="radio"
            name="theme"
            value={value}
            checked={choice === value}
            onChange={() => setChoice(value)}
            className="sr-only peer"
          />
          <span
            className="grid place-items-center w-8 h-9 rounded-lg cursor-pointer transition-colors
                       text-zinc-500 hover:text-zinc-900
                       peer-checked:bg-white peer-checked:text-zinc-900 peer-checked:shadow-sm
                       peer-focus-visible:ring-2 peer-focus-visible:ring-zinc-400
                       dark:text-zinc-400 dark:hover:text-zinc-200
                       dark:peer-checked:bg-zinc-800 dark:peer-checked:text-zinc-50 dark:peer-checked:shadow-none
                       dark:peer-focus-visible:ring-zinc-500"
          >
            <Icon />
            <span className="sr-only">{label}</span>
          </span>
        </label>
      ))}
    </fieldset>
  )
}
