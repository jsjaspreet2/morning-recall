# Build spec — Morning Recall

Hand this file and `prompts.json` to Claude Code.

## What this is

A single-page static site for daily active recall before interviews. It shows one prompt
at a time with **no answer**. The user attempts the answer out loud or on paper, then marks
hit or miss. Misses come back sooner.

The whole point is retrieval practice. The site must never display an answer, a hint, or
an expandable "reveal" — that turns retrieval practice back into passive reading and
destroys the value. The `answerKey` field names which PDF cheatsheet to open offline;
show it as a small text label only, and only *after* the user has marked the card.

## Stack

- Vite + React + TypeScript, Tailwind. Static output, no backend, no auth.
- `prompts.json` imported directly at build time.
- All state in `localStorage`. Single user, single device is fine.
- Deploy target: any static host (Netlify / Vercel / GitHub Pages). Include the config
  for one of them and a one-line deploy command in the README.

## Core behavior

**Daily deck.** On first load each day, build a deck of `meta.dailyDeckSize` prompts (12).
Selection is weighted:

1. Any prompt marked *miss* in the last 2 days is included first.
2. Then prompts not seen in the longest time, biased by the `weight` field
   (weight 4 should appear roughly 4× as often as weight 1 over a month).
3. Cap any single track at 3 prompts per deck so the morning stays mixed.

**Card view.** One prompt, full screen, large type. Shows: track label, type label
(with the one-line instruction from `meta.types`), the prompt text, and a countdown
timer seeded from `timeboxSec`.

The timer is a pacing signal, not a fail state — when it hits zero, it turns amber and
keeps counting up. Don't auto-advance and don't play a sound.

**Marking.** Two buttons: **Got it** and **Blanked**. After marking, reveal the
`answerKey` line ("Answer key: JavaScript v2") and advance. That's the entire interaction —
no notes field, no rating scale. Adding more friction to the morning ritual is how it
stops getting done.

**Scheduling.** Lightweight Leitner, not full SM-2:
- Got it → next due in 2× the previous interval, starting at 2 days, capped at 21.
- Blanked → next due tomorrow, interval resets to 1.

**Done screen.** Show the day's hit/miss split, current streak, and the tracks with the
most misses in the last 14 days. Keep it to three numbers. No charts.

## Design

Read `/mnt/skills/public/frontend-design/SKILL.md` before styling.

- **Mobile-first and phone-primary.** This gets used standing in a kitchen. Big tap
  targets, one thumb, no horizontal scroll, works at 375px.
- Track accents come from `meta.tracks[].accent` — use them as a thin marker on the card,
  not as a full background.
- Follows the system appearance by default, with a Light / Dark / System selector in
  the header. Dark is the fallback when there's no preference to read — it's used early.
- The prompt text is the interface. Everything else recedes.

## Explicitly out of scope

Don't build: answer storage, editing prompts in-app, multi-user, sync, spaced-repetition
tuning UI, or analytics. If a feature would let the user tinker with the system instead of
doing reps, leave it out.

## Adding prompts later

Editing `prompts.json` and redeploying is the intended workflow. Keys are stable `id`
strings, so scheduling history survives edits as long as ids don't change.
