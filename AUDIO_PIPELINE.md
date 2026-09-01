# Audio Pipeline — Operational Runbook

How to synthesize, publish, and subscribe to the narrated episodes. **For how to *write* an
episode, see `AUDIO_SCRIPT_AUTHORING.md`** — that's the style contract; this is the machinery.

The product is a private podcast feed of narrated episodes derived from `src/data/designs/`
and `src/data/guides/`, for prep away from a laptop.

---

## Setup

One secret, one file, gitignored:

```bash
echo 'ELEVENLABS_API_KEY=sk_...' > .env
```

Scripts read `process.env`, so load it before running anything:

```bash
set -a; . ./.env; set +a
```

Requires **Node 24+** (native `fetch`, and type-stripping so `.mjs` can import `src/learn/toc.ts`
directly). No ffmpeg — deliberately, see *One episode, one request*.

---

## Commands

```bash
npm run audio:voices                 # list voices on the account, with preview URLs
npm run audio:synth -- --dry-run     # lint + char counts + projected cost. SPENDS NOTHING
npm run audio:synth                  # synthesize every `ready` episode whose hash changed
npm run audio:synth -- --only <id>   # one episode, ignoring status
npm run audio:synth -- --force       # ignore the cache
npm run audio:synth -- --reindex     # recompute duration/bytes/hash from mp3s on disk, no API calls
npm run audio:feed                   # regenerate public/feed/<slug>/podcast.xml
npm run audio:feed -- --check        # fail if the committed feed is stale
npm run audio:publish                # gh release upload + verify every enclosure
npm run audio:publish -- --verify    # verification only
npm run audio:publish -- --dry-run
```

`scripts/audio/preview.mjs` renders one excerpt across a matrix of voices and speeds — use it
before changing voice, never guess from the label:

```bash
node scripts/audio/preview.mjs --text-file excerpt.txt --speed 0.9,1.0 \
  --voices <id1>,<id2> --names <id1>:Daniel,<id2>:George
```

---

## The loop

1. Write `src/data/audio/scripts/<id>.md` per `AUDIO_SCRIPT_AUTHORING.md`.
2. Add an entry to `episodes` in `src/data/audio/manifest.json` with `status: "draft"`.
3. `npm run audio:synth -- --dry-run` until it exits 0.
4. Flip to `status: "ready"` when you intend to spend on it.
5. `npm run audio:synth` → mp3s land in `out/audio/` (gitignored).
6. `npm run audio:publish` → uploads to the `audio-v1` GitHub Release, then verifies.
7. `npm run audio:feed` → regenerates the feed XML.
8. Commit `src/data/audio/**` and `public/feed/**`, push. Pages serves the feed.

**Never run synthesis from CI.** It spends money per push and would need the key in Actions.

---

## Subscribe

```
https://jsjaspreet2.github.io/morning-recall/feed/60c327e8c9a29b66d2dafcef/podcast.xml
```

Apple Podcasts: Library → ⋯ → *Add a Show by URL*. Overcast: search → *Add URL*.
Pocket Casts: paste into search.

**This is private by obscurity, not authentication** — the repo is public and release assets are
listed on it. The tags doing the real work are `<itunes:block>Yes</itunes:block>` (never list in
Apple's directory) and `<podcast:locked>yes</podcast:locked>` (refuse platform imports).

---

## Settings, and why

In `manifest.json` under `synthesis`:

| Setting | Value | Why |
|---|---|---|
| `voiceId` | `onwK4e9ZLuTAKqWW03F9` (Daniel) | British, steady broadcaster. Chosen by A/B against George, Brian, Bill, Matilda |
| `modelId` | `eleven_multilingual_v2` | **Not v3.** v3 caps at 5k chars, is alpha-variable across a long library, and *does not support break tags at all* |
| `outputFormat` | `mp3_44100_128` | Mono. Bitrate is free — billing is per character — and Releases hosting removed the size pressure that argued for 64 |
| `speed` | `0.9` | 0.7–1.2 is the valid range. Fixes global *pace*; only the script fixes *rhythm* |
| `stability` | `0.5` | Lower is more expressive but drifts over long passages |
| `apply_text_normalization` | `off` | Scripts are already in spoken form. Auto-normalization mangles numbers and URLs and makes output non-reproducible |
| `maxChars` | `8500` | Soft cap; linter fails above it |
| `requestCharCap` | `10000` | Hard multilingual-v2 per-request limit |

**Changing `voiceId`, `speed`, `modelId`, `outputFormat`, or `voiceSettings` invalidates every
cached episode** — they're all in the hash. Re-synthesizing the whole library is the cost, so
decide these at a pilot, not after fifty episodes.

---

## Gotchas discovered the hard way

**`output_format` is a query parameter, not a body field.** Passing it in the JSON body is
silently ignored and you get the 128 kbps default. This one hid a worse bug.

**Never assume the bitrate.** `probe()` in `synth.mjs` reads the real bitrate from the first MPEG
frame header, because an assumed bitrate put durations in the feed that were 2× wrong — which
would have broken every scrub bar. If audio and metadata ever disagree, run `--reindex`.

**`--reindex` asserts that mp3s on disk were made with the *current* manifest settings.** It
refreshes hashes as well as durations. Run it only when that's true, or it marks stale audio fresh.

**Break tags destabilize the model in bulk.** ElevenLabs' own warning: too many "can cause
instability — the AI might speed up, or introduce artifacts." The linter fails above twelve. Use
them only after a count announcement, between list items, and before the recap.

**`status` gates spending and publishing.** `draft` scripts are linted but never synthesized and
never uploaded — a public release asset is not easily taken back.

**The deixis linter is deliberately narrow.** "four orders of magnitude *above* the write path" is
a comparative and must not flag; "see the table above" must. There are unit tests for this in the
commit history — extend them if you touch the rule.

---

## Measured numbers (use these, don't re-estimate)

| Quantity | Value | How it was measured |
|---|---|---|
| **Credit rate** | **0.547 credits/char** | Two independent measurements, 48k and 30k chars, agreeing to three decimals. A Creator-tier discount — the $0.10/1k list rate is ~2× pessimistic |
| **Expansion ratio** | **1.49×** source prose words → narrated words | Three episodes; range 1.30–1.73. Tables-become-sentences and added recaps drive it |
| Chars per narrated word | 6.02 | Same sample |
| Speaking rate | ~131 wpm at speed 0.9 | 1,208 words in 9:15 |
| Typical episode | ~7,900 chars ≈ 9–10 min ≈ 9 MB | Across 16 episodes |

**Per episode: ~4,300 credits.** A full Creator cycle (129,796) is ~30 episodes.

---

## State as of 2026-08-20

**16 episodes published, 2h 39m.** Feed live and verified: all 16 enclosures serve HTTP 206 range
requests with byte lengths matching the feed, unique GUIDs, ascending past `pubDate`s.

| Page | Episodes | Status |
|---|---|---|
| `design-ticketmaster.md` | 6 | **complete** |
| `design-discord.md` | 5 | **complete** |
| `design-cursor.md` | 4 | **complete** |
| `design-figma.md` | 1 of 5 | only the §7–8 data-model dive |
| `design-airbnb.md` | 0 of 5 | not started |
| `design-uber.md`, `design-feed.md`, `design-messaging.md`, `design-chatgpt.md`, `00-interview-mechanics.md` | 0 of 21 | not started |

Full design-page corpus is **46 episodes / ~6.2 hours**. Remaining: ~30 episodes.

Three scripts are written but `draft` — `sysdesign-02-estimation`, `sysdesign-05-correctness`,
`tech-01-push`. The latter two have mp3s on disk from the pilot at **speed 1.0**, which is why they
are not published; re-synthesizing them at 0.9 costs ~7k credits.

### Next up

Finish Figma (4 episodes, ~31k chars, ~17k credits) — the 9/9 screen. Then Airbnb, then the
remaining pages. Episode cut rule and the per-page taxonomy are in `AUDIO_SCRIPT_AUTHORING.md`.

Check credits before a batch:

```bash
set -a; . ./.env; set +a
curl -s https://api.elevenlabs.io/v1/user/subscription -H "xi-api-key: $ELEVENLABS_API_KEY" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['character_limit']-d['character_count'], 'credits left')"
```
