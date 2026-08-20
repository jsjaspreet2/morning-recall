#!/usr/bin/env node
/**
 * Upload synthesized mp3s to a GitHub Release and verify the enclosure URLs.
 *
 * Releases, not `public/audio/`, because ~200 MB of incompressible blobs in git
 * history is permanent and re-synthesis adds a fresh copy every time. Release
 * assets live outside history, cap at 2 GB each, and serve range requests.
 *
 *   node scripts/audio/publish.mjs              upload changed episodes
 *   node scripts/audio/publish.mjs --verify     check every enclosure URL
 *   node scripts/audio/publish.mjs --dry-run
 */
import { readFileSync, existsSync, readdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFileSync } from 'node:child_process'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const argv = process.argv.slice(2)
const DRY = argv.includes('--dry-run')
const VERIFY_ONLY = argv.includes('--verify')

const manifest = JSON.parse(readFileSync(join(ROOT, 'src/data/audio/manifest.json'), 'utf8'))
const { show } = manifest
const cachePath = join(ROOT, 'out/audio/.cache.json')
const cache = existsSync(cachePath) ? JSON.parse(readFileSync(cachePath, 'utf8')) : {}
const sh = (cmd, args) => execFileSync(cmd, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()

// Only ready + synthesized episodes get uploaded. Drafts and superseded audio
// stay local; a release asset on a public repo is not easily taken back.
const publishable = new Set(
  manifest.episodes.filter((e) => e.status === 'ready' && cache[e.id]).map((e) => `${e.id}.mp3`),
)
const files = existsSync(join(ROOT, 'out/audio'))
  ? readdirSync(join(ROOT, 'out/audio')).filter((f) => publishable.has(f))
  : []

if (!VERIFY_ONLY) {
  if (!files.length) { console.error('\n  No mp3s in out/audio. Run: npm run audio:synth\n'); process.exit(1) }
  // `gh release view` exits non-zero when the tag doesn't exist yet.
  let exists = true
  try { sh('gh', ['release', 'view', show.releaseTag, '--repo', show.repo]) } catch { exists = false }

  console.log(`\n  ${files.length} file(s) → ${show.repo} @ ${show.releaseTag}${exists ? '' : ' (new release)'}`)
  if (DRY) { console.log('  --dry-run: nothing uploaded.\n'); process.exit(0) }

  if (!exists) {
    sh('gh', ['release', 'create', show.releaseTag, '--repo', show.repo,
              '--title', 'Narration audio', '--notes', 'Audio assets for the private narration feed.'])
  }
  sh('gh', ['release', 'upload', show.releaseTag, '--repo', show.repo, '--clobber',
            ...files.map((f) => join(ROOT, 'out/audio', f))])
  console.log('  uploaded.\n')
}

// Verification: the two things that actually break podcast playback are a wrong
// enclosure length (clients truncate or mis-seek) and a host that won't serve
// ranges (every scrub re-downloads the file).
const base = `https://github.com/${show.repo}/releases/download/${show.releaseTag}/`
let bad = 0
console.log()
for (const ep of manifest.episodes.filter((e) => e.status === 'ready' && cache[e.id])) {
  const url = `${base}${ep.id}.mp3`
  try {
    const res = await fetch(url, { headers: { Range: 'bytes=100000-100100' } })
    const len = Number(res.headers.get('content-range')?.split('/')[1] ?? res.headers.get('content-length'))
    const ok = res.status === 206 && len === cache[ep.id].bytes
    if (!ok) bad++
    console.log(`  ${ok ? '✓' : '✗'} ${ep.id.padEnd(30)} ${res.status} ${len === cache[ep.id].bytes ? 'length ok' : `LENGTH ${len} vs ${cache[ep.id].bytes}`}`)
  } catch (err) { bad++; console.log(`  ✗ ${ep.id} — ${err.message}`) }
}
console.log(bad ? `\n  ${bad} enclosure(s) failed.\n` : '\n  All enclosures serve ranges with matching lengths.\n')
process.exit(bad ? 1 : 0)
