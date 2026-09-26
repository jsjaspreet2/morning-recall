# Project instructions

A static reading site. Two sections, **Learn** (interview field guides) and **Designs**
(worked system design problems). `BUILD_SPEC.md` is the spec; `DESIGN_PAGE_AUTHORING.md`
and `AUDIO_SCRIPT_AUTHORING.md` are the authoring guides for their formats.

## Do not generate active-recall material

The site had a third section, **Practice** — a daily deck of 378 prompts from
`prompts.json`, with Leitner scheduling in `localStorage`. It was removed on 2026-08-30
because it went unused, and it is not coming back.

When asked to add a new system design problem, a new company screen guide, or any other
content here, **the deliverable is the page and only the page.** Do not also produce:

- recall prompts, study cards, flashcards, quiz decks, or a `prompts.json`
- a `§16 Active recall` section at the bottom of a design page (pages end at §15)
- a table of "cold prompts" or self-test questions at the end of a guide
- a scheduler, quiz mode, progress store, streak, or a third navigation tab

The seven design pages that still carried a §16 recall table lost it on 2026-08-30. Every
design page now ends at §15, and there is no page left to copy the pattern from.

Reviving recall is a deliberate decision, not a side effect of adding content. The deck is
in git history (`git log -- prompts.json`), and the deleted §16 tables are in
`git log -- src/data/designs/`, if that ever changes.

## Conventions

- **Guides**: markdown in `src/data/guides/`, registered in `src/data/guides.ts`. Company
  screens carry `screen: true` and sort above the general guides.
- **Root markdown mirrors**: the `*.md` files at the repo root mirror `src/data/guides/`
  and are hand-synced. Editing a guide means `cp`-ing it over its root twin **in the same
  commit** — several have drifted from being edited on only one side.
- **Designs**: markdown in `src/data/designs/`, registered in `src/data/designs.ts`.
- **Don't rename** the package, the `/morning-recall/` base path in `vite.config.ts`, or
  the `morning-recall:` localStorage namespace. The deployed GitHub Pages URL and the
  published podcast feed both depend on that path; the site's display name is
  "Interview Field Guides" and that is the only name that changed.
- Run `npx tsc --noEmit` and `npm run build` before calling a change done.
