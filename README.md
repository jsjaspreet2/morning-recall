# Morning Recall

A single-page static site for daily active-recall practice before interviews, plus a
browsable library of the interview field guides.

Two sections:

- **Practice** — one prompt at a time. Attempt it from memory (out loud or on paper), then
  mark **Got it** or **Blanked**. Only *after* you mark does a short 1–2 sentence answer
  appear, along with a link to the full guide — so a blank is always recoverable. Misses come
  back sooner (lightweight Leitner scheduling). Choose how to practice from the home screen:
  - **Daily mix** — 12 prompts weighted toward what you've missed and haven't seen recently,
    capped at 3 per track.
  - **Everything** — all prompts, shuffled, for a full run-through.
  - **Focus on an area** — pick one or more tracks (JavaScript, React, CSS, Accessibility,
    Coding Patterns, Animation, System Design, LLM, Distributed Systems, Behavioral) and quiz
    just those. Finish a run and you can **Practice again** or jump back to the menu.

  All progress lives in `localStorage`.
- **Learn** — the six field guides rendered as web-friendly, searchable pages with a table
  of contents and code highlighting. Read them for the full detail behind any short answer.
  Each guide also links to its original PDF.

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
   git commit -m "Morning Recall"
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

## Adding or editing prompts

Edit **`prompts.json`** at the repo root (the app imports it directly), commit, and push.
Prompt `id`s are stable, so your scheduling history survives edits as long as ids don't
change. No answers ever live in this file — the guides are the answer key. Keep every
`answerKey` pointing at something real (a guide, a book chapter, your own notes); the app is
built to only carry prompts you can actually check yourself against when you blank.

## Project layout

```
src/
  lib/         types, localStorage, date helpers, Leitner scheduler, accent tokens
  data/        guide markdown files + registries (prompts.json lives at the repo root)
  practice/    PracticePage, Card, Timer, DoneScreen
  learn/       LearnIndex, GuidePage, Markdown renderer, TOC extraction
public/pdfs/   original guide PDFs (linked from each Learn page)
```
