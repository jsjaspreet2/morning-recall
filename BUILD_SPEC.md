# Build spec — Interview Field Guides

## What this is

A single-page static site with exactly two sections, and no plans for a third:

- **Learn** — the interview field guides, rendered as web-friendly pages with a table of
  contents and code highlighting. Company screens are grouped above the standing general
  guides, because a screen goes stale after its date and a general guide doesn't.
- **Designs** — worked system design problems, one page each, plus a mechanics page read
  once before the rest. Some are also narrated as a private podcast feed.

That is the whole surface. It is a reading site.

## Explicitly out of scope — read this before adding anything

**No active recall, in any form.** The site used to carry a third section, "Practice": a
daily deck of prompts from `prompts.json`, Leitner scheduling in `localStorage`, hit/miss
marking, streaks. It was removed on 2026-08-30 because it went essentially unused, and it is
not coming back.

So when the work is *"add a new system design problem"* or *"add a guide for the <company>
screen"*, the deliverable is **the page, and only the page**:

- Don't write recall prompts, study cards, flashcards, or tables of cold questions — not as
  a `prompts.json`, not as a `§16 Active recall` section at the bottom of a design page
  (see `DESIGN_PAGE_AUTHORING.md`), not as a separate file. The seven pages that still had a
  §16 table lost it on 2026-08-30; design pages end at §15.
- Don't add a scheduler, a quiz mode, a progress store, or a streak.
- Don't reintroduce a third tab.

The recall deck and its 378 prompts are recoverable from git history if that judgment ever
reverses (`git log -- prompts.json`), but reviving it is a deliberate decision, not a
side effect of adding a guide.

Also out of scope, as before: editing content in-app, multi-user, sync, analytics.

## Stack

- Vite + React + TypeScript, Tailwind. Static output, no backend, no auth.
- Guides are markdown under `src/data/guides/`, registered in `src/data/guides.ts`.
  Design pages are markdown under `src/data/designs/`, registered in `src/data/designs.ts`.
  Adding a page is: write the markdown, add the registry entry, commit.
- The only `localStorage` key is the theme choice. It is namespaced `morning-recall:` after
  the repo and deploy path, which stay as they are — renaming the namespace would silently
  drop every existing visitor's theme.
- Deploy target: GitHub Pages via `.github/workflows/deploy.yml`, base path
  `/morning-recall/`. The published podcast feed URL depends on that path; don't change it.

## Design

- **Mobile-first.** Big tap targets, one thumb, no horizontal scroll, works at 375px.
- Guide and design pages take the full desktop width — they're long-form reading with wide
  code blocks and tables. The two indexes get a two-up card grid.
- Accents come from each registry entry's `accent` and are used as a thin marker, never as
  a full background.
- Follows the system appearance by default, with a Light / Dark / System selector in the
  header. `index.html` paints the stored theme before the first frame; `src/lib/theme.ts`
  duplicates that logic on purpose and the two carry notes pointing at each other.

## Root markdown files

The `*.md` files at the repo root mirror `src/data/guides/` and are hand-synced. When you
edit a guide, `cp` the new version over its root twin in the same commit.
