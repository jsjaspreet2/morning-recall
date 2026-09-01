#!/usr/bin/env node
/**
 * Narration scripts -> ElevenLabs -> out/audio/*.mp3
 *
 * Synthesis is explicit and cached: an episode is only sent to the API when the
 * hash of (script body + every synthesis parameter) changes. Editing one script
 * re-spends credits on exactly that episode.
 *
 *   node scripts/audio/synth.mjs --dry-run     lint + char counts + cost, spends nothing
 *   node scripts/audio/synth.mjs               synthesize whatever changed
 *   node scripts/audio/synth.mjs --only <id>   one episode
 *   node scripts/audio/synth.mjs --force       ignore the cache
 */
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const OUT = join(ROOT, 'out', 'audio')
const CACHE = join(OUT, '.cache.json')
const SCRIPTS = join(ROOT, 'src', 'data', 'audio', 'scripts')

const argv = process.argv.slice(2)
const has = (f) => argv.includes(f)
const val = (f) => { const i = argv.indexOf(f); return i === -1 ? null : argv[i + 1] }
const DRY = has('--dry-run')
const FORCE = has('--force')
const ONLY = val('--only')

const manifest = JSON.parse(readFileSync(join(ROOT, 'src/data/audio/manifest.json'), 'utf8'))
const S = manifest.synthesis

/** Front matter + spoken body. The body is what gets hashed and sent. */
function parseScript(id) {
  const path = join(SCRIPTS, `${id}.md`)
  if (!existsSync(path)) return { id, missing: true, path }
  const raw = readFileSync(path, 'utf8')
  const m = /^---\n([\s\S]*?)\n---\n([\s\S]*)$/.exec(raw)
  if (!m) return { id, path, error: 'no front matter block' }
  const meta = Object.fromEntries(
    m[1].split('\n').filter(Boolean).map((l) => {
      const i = l.indexOf(':')
      return [l.slice(0, i).trim(), l.slice(i + 1).trim().replace(/^["']|["']$/g, '')]
    }),
  )
  // Collapse to exactly what the synthesizer receives: paragraphs separated by
  // blank lines. Anything else in the file is an authoring mistake.
  const body = m[2].split('\n').map((l) => l.trim()).join('\n').replace(/\n{3,}/g, '\n\n').trim()
  return { id, path, meta, body }
}

/**
 * The style contract from AUDIO_SCRIPT_AUTHORING.md, enforced. These are all
 * things that are silently wrong: they synthesize fine and sound broken.
 */
function lint(ep) {
  const problems = []
  // Break tags are synthesis directives, not spoken text — strip them before
  // linting so `<break time="0.8s" />` doesn't trip the unspoken-unit rule.
  const b = ep.body.replace(/<break\s+time="[\d.]+s"\s*\/>/g, ' ')
  const flag = (re, msg) => {
    const hits = [...b.matchAll(re)].map((h) => h[0])
    if (hits.length) problems.push(`${msg}: ${[...new Set(hits)].slice(0, 5).join(' · ')}`)
  }
  flag(/§\s*\d+[A-Z]?/g, 'section cross-reference')
  flag(/https?:\/\/\S+/g, 'URL')
  flag(/\b[\w./-]+\.(md|ts|tsx|json|mjs)\b/g, 'file path')
  flag(/`[^`]*`/g, 'inline code span')
  flag(/^#{1,6}\s/gm, 'markdown heading')
  flag(/^\s*[-*+]\s/gm, 'markdown bullet')
  flag(/\*\*[^*]+\*\*/g, 'bold markup')
  flag(/```/g, 'code fence')
  flag(/\[[^\]]+\]\([^)]+\)/g, 'markdown link')
  // Only deictic uses. A bare comparative ("four orders of magnitude above the
  // write path") is perfectly good spoken English and must not be flagged.
  flag(/\b(?:as shown|as above|see the|the diagram|the figure|earlier section|later section)\b/gi, 'visual deixis')
  flag(/\b(?:see|shown|listed|described|mentioned|noted|discussed|pictured)\s+(?:above|below)\b/gi, 'visual deixis')
  flag(/\bthe\s+(?:table|list|section|diagram|figure|chart|column|row)\s+(?:above|below)\b/gi, 'visual deixis')
  // No trailing \b here: it never matches after a symbol like `%`.
  flag(/\b\d[\d,.]*\s*(?:%|KB|MB|GB|TB|ms|s\b|kbps|QPS|RPS)/gi, 'unspoken unit')
  // Bare multi-digit numerals. Single digits inside words ("four-ten") are fine.
  flag(/(?<![\w.-])\d{2,}(?![\w.-])/g, 'bare numeral — write it in words')
  const breaks = (ep.body.match(/<break\s/g) ?? []).length
  if (breaks > 12) problems.push(`${breaks} break tags — over ~12 destabilizes multilingual v2 (it speeds up or adds artifacts)`)
  if (ep.body.length > S.maxChars) problems.push(`over soft cap: ${ep.body.length} > ${S.maxChars}`)
  if (ep.body.length > S.requestCharCap) problems.push(`OVER SINGLE-REQUEST CAP: ${ep.body.length} > ${S.requestCharCap}`)
  return problems
}

const hashOf = (body) =>
  createHash('sha256')
    .update(JSON.stringify([body, S.voiceId, S.modelId, S.outputFormat, S.seed, S.voiceSettings]))
    .digest('hex')
    .slice(0, 16)

/**
 * Read the real bitrate out of the first MPEG frame header rather than trusting
 * the requested format — the API silently ignores an unsupported output_format
 * and hands back its default, and an assumed bitrate then puts a wrong
 * itunes:duration in the feed. ElevenLabs mp3 is CBR, so bytes/bitrate is exact.
 */
const MPEG1_L3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
const MPEG2_L3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
function probe(buf) {
  let i = 0
  if (buf.slice(0, 3).toString() === 'ID3') {
    // ID3v2 size is four sync-safe bytes: seven significant bits each.
    i = 10 + ((buf[6] & 0x7f) << 21 | (buf[7] & 0x7f) << 14 | (buf[8] & 0x7f) << 7 | (buf[9] & 0x7f))
  }
  for (; i < buf.length - 4; i++) {
    if (buf[i] !== 0xff || (buf[i + 1] & 0xe0) !== 0xe0) continue
    const version = (buf[i + 1] >> 3) & 3   // 3 = MPEG-1, 2 = MPEG-2, 0 = MPEG-2.5
    const layer = (buf[i + 1] >> 1) & 3     // 1 = Layer III
    const kbps = (version === 3 ? MPEG1_L3 : MPEG2_L3)[(buf[i + 2] >> 4) & 0xf]
    if (layer !== 1 || !kbps) continue
    return { kbps, bytes: buf.length, duration: Math.round(((buf.length - i) * 8) / (kbps * 1000)) }
  }
  return null
}
const hhmmss = (s) =>
  [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map((n) => String(n).padStart(2, '0')).join(':')

/**
 * `/with-timestamps` is the same generation as plain text-to-speech — same voice,
 * same seed, same audio, billed the same per character — but it returns the
 * character-level alignment alongside the mp3. Alignment is only free at
 * synthesis time: recovering it afterwards means paying again for forced
 * alignment, so we always take it, even when no transcript is being built yet.
 *
 * There is deliberately no fallback to the plain endpoint. A silent fallback
 * would spend a full episode's credits and hand back audio with no timings,
 * which is the one failure worth failing loudly on.
 */
async function synthesize(ep) {
  const url = `https://api.elevenlabs.io/v1/text-to-speech/${S.voiceId}/with-timestamps?output_format=${encodeURIComponent(S.outputFormat)}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'xi-api-key': process.env.ELEVENLABS_API_KEY, 'content-type': 'application/json' },
    body: JSON.stringify({
      text: ep.body,
      model_id: S.modelId,
      // Scripts are already written in spoken form, so auto-normalization can
      // only do harm — and turning it off makes output reproducible.
      apply_text_normalization: 'off',
      seed: S.seed,
      voice_settings: S.voiceSettings,
    }),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${(await res.text()).slice(0, 300)}`)
  const json = await res.json()
  if (!json.audio_base64) throw new Error('response carried no audio_base64')
  return {
    buf: Buffer.from(json.audio_base64, 'base64'),
    // `alignment` indexes the text we sent, break tags and all; the VTT builder
    // maps back through it. `normalized_alignment` is kept because it is the
    // only record of what the model actually spoke.
    alignment: { text: ep.body, alignment: json.alignment, normalized: json.normalized_alignment },
  }
}

// ---------------------------------------------------------------------------

if (has('--reindex')) {
  const c = existsSync(CACHE) ? JSON.parse(readFileSync(CACHE, 'utf8')) : {}
  for (const [id, entry] of Object.entries(c)) {
    const f = join(OUT, `${id}.mp3`)
    if (!existsSync(f)) continue
    const p = probe(readFileSync(f))
    if (!p) continue
    // Also refresh the hash: reindex asserts that the audio on disk was made
    // with the settings currently in the manifest. Only run it when that is
    // true — otherwise it marks stale audio as fresh and you never notice.
    const ep = parseScript(id)
    const rehash = ep.body ? hashOf(ep.body) : entry.hash
    Object.assign(entry, { bytes: p.bytes, duration: p.duration, kbps: p.kbps, hash: rehash })
    console.log(`  ${id.padEnd(30)} ${hhmmss(p.duration)}  ${p.kbps}kbps${rehash !== entry.hash ? '' : ''}`)
  }
  writeFileSync(CACHE, JSON.stringify(c, null, 2))
  console.log('\n  cache reindexed from disk. No credits spent.\n')
  process.exit(0)
}

// Only `ready` episodes synthesize. Drafts stay authored-but-unspent, so a
// half-written script can sit in the repo without costing anything.
const episodes = manifest.episodes
  .filter((e) => (ONLY ? e.id === ONLY : e.status === 'ready'))
  .sort((a, b) => a.order - b.order)
  .map((e) => ({ ...e, ...parseScript(e.id) }))

mkdirSync(OUT, { recursive: true })
const cache = existsSync(CACHE) ? JSON.parse(readFileSync(CACHE, 'utf8')) : {}

let totalChars = 0, toSynth = [], blocked = 0
console.log()
for (const ep of episodes) {
  if (ep.missing) { console.log(`  ✗ ${ep.id}  — no script at ${ep.path.replace(ROOT + '/', '')}`); blocked++; continue }
  if (ep.error) { console.log(`  ✗ ${ep.id}  — ${ep.error}`); blocked++; continue }

  const problems = lint(ep)
  const hash = hashOf(ep.body)
  const cached = cache[ep.id]?.hash === hash && existsSync(join(OUT, `${ep.id}.mp3`))
  const words = ep.body.split(/\s+/).length
  const mins = (ep.body.length / 1000 / 60 * 60).toFixed(1)

  const mark = problems.length ? '!' : cached && !FORCE ? '=' : '+'
  console.log(`  ${mark} ${ep.id.padEnd(30)} ${String(ep.body.length).padStart(5)} chars  ${String(words).padStart(4)} words  ~${mins}m`)
  for (const p of problems) console.log(`      ${p}`)

  if (problems.some((p) => p.includes('OVER SINGLE-REQUEST CAP'))) { blocked++; continue }
  if (cached && !FORCE) continue
  totalChars += ep.body.length
  toSynth.push({ ...ep, hash })
}

const cost = (totalChars / 1000) * 0.10
console.log(`\n  ${episodes.length} episodes · ${toSynth.length} to synthesize · ${totalChars.toLocaleString()} chars · ~$${cost.toFixed(2)} at $0.10/1k`)
if (blocked) console.log(`  ${blocked} blocked`)

if (DRY) {
  const dirty = episodes.filter((e) => e.body && lint(e).length).length
  console.log(`\n  --dry-run: nothing sent.${dirty ? ` ${dirty} episode(s) failed lint.` : ''}\n`)
  process.exit(blocked || dirty ? 1 : 0)
}
if (!toSynth.length) { console.log('\n  Nothing changed. No credits spent.\n'); process.exit(0) }
if (!S.voiceId) { console.error('\n  No voiceId in manifest.json. Run: npm run audio:voices\n'); process.exit(1) }
if (!process.env.ELEVENLABS_API_KEY) { console.error('\n  ELEVENLABS_API_KEY is not set.\n'); process.exit(1) }

console.log()
for (const ep of toSynth) {
  process.stdout.write(`  → ${ep.id} … `)
  try {
    const { buf, alignment } = await synthesize(ep)
    const file = join(OUT, `${ep.id}.mp3`)
    writeFileSync(file, buf)
    // Written before the cache entry: a crash here must not leave an episode
    // marked synthesized with no timings on disk.
    writeFileSync(join(OUT, `${ep.id}.alignment.json`), JSON.stringify(alignment))
    const p = probe(buf) ?? { kbps: 0, bytes: statSync(file).size, duration: 0 }
    cache[ep.id] = { hash: ep.hash, bytes: p.bytes, duration: p.duration, kbps: p.kbps, title: ep.title, order: ep.order, chars: ep.body.length, aligned: true }
    writeFileSync(CACHE, JSON.stringify(cache, null, 2))
    console.log(`${(p.bytes / 1024 / 1024).toFixed(1)} MB  ${hhmmss(p.duration)}  ${p.kbps}kbps`)
  } catch (err) {
    console.log(`FAILED — ${err.message}`)
  }
}
console.log(`\n  Done. Spent ~$${cost.toFixed(2)}.\n`)
