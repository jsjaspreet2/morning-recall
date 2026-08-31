# Interview Field Guides

A single-page static site: a browsable library of the interview field guides, plus worked
system design problems.

Two sections, and only two:

- **Learn** — the field guides rendered as web-friendly, searchable pages with a table of
  contents and code highlighting. Company screens are grouped above the standing general
  guides. Most guides also link to their original PDF.
- **Designs** — worked system design problems, one page each: requirements, flows, deep
  dives, data model, a five-minute skeleton to draw cold, and variants. Read
  `00-interview-mechanics` once before the rest.

> **Note.** There used to be a third section, **Practice** — a daily active-recall deck of
> 378 prompts with Leitner scheduling. It was removed on 2026-08-30 because it went
> essentially unused. New guides and design pages ship as pages only; don't generate recall
> prompts or study cards to go with them. See `BUILD_SPEC.md`.

## Listen

The design pages are also narrated as a private podcast feed — for prep while driving or at the
gym. Sixteen episodes, ~2h 40m, covering Ticketmaster, Discord, and Cursor Tab end to end.

Subscribe by URL in Apple Podcasts, Overcast, or Pocket Casts:

```
https://jsjaspreet2.github.io/morning-recall/feed/60c327e8c9a29b66d2dafcef/podcast.xml
```

Narration scripts are committed under `src/data/audio/scripts/`; audio lives on a GitHub Release
rather than in git. See **`AUDIO_PIPELINE.md`** to synthesize and publish, and
**`AUDIO_SCRIPT_AUTHORING.md`** for how an episode is written.

## Run locally

```bash
npm install
npm run dev          # http://localhost:5173
```

Build a production bundle:

```bash
npm run build        # outputs to dist/
npm run preview      # serve the built bundle locally
```

## Deploy to GitHub Pages (free)

The repo ships a GitHub Actions workflow (`.github/workflows/deploy.yml`) that builds and
publishes on every push to `main`.

1. **Set the base path.** In `vite.config.ts`, `BASE` must match your repo name. It's set to
   `'/morning-recall/'`. If your repo is named differently, change it to `'/<repo-name>/'`.

2. **Create the repo and push:**

   ```bash
   git init
   git add -A
   git commit -m "Interview field guides"
   git branch -M main
   git remote add origin https://github.com/<you>/morning-recall.git
   git push -u origin main
   ```

3. **Turn on Pages:** in the repo, go to **Settings → Pages → Build and deployment → Source**
   and choose **GitHub Actions**. The workflow runs automatically; watch it under the
   **Actions** tab.

4. Your site goes live at **`https://<you>.github.io/morning-recall/`**.

**Redeploy** is just `git push` — the Action rebuilds and republishes.

> Deploying to Netlify or Vercel instead? Set `BASE = '/'` in `vite.config.ts`, run
> `npm run build`, and deploy the `dist/` folder (`npx netlify-cli deploy --prod --dir=dist`
> or `npx vercel --prod`).

## Adding or editing a guide

Write or edit the markdown under **`src/data/guides/`**, add or update its entry in
**`src/data/guides.ts`** (id, title, subtitle, accent, and `screen: true` for a company
screen), then `cp` the file over its hand-synced twin at the repo root. Commit and push.

Design pages work the same way — **`src/data/designs/design-<name>.md`** plus a `META` entry
in **`src/data/designs.ts`**. Follow **`DESIGN_PAGE_AUTHORING.md`**; pages end at §15.

## Project layout

```
src/
  lib/         shared types, theme + localStorage, accent tokens
  data/        guide and design markdown + their registries
  learn/       LearnIndex, GuidePage, Markdown renderer, TOC extraction
  designs/     DesignsIndex, DesignPage
public/pdfs/   original guide PDFs (linked from each Learn page)
```
