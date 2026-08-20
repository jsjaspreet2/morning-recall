#!/usr/bin/env node
/**
 * Render one short excerpt across a matrix of voices and speeds, so voice and
 * pacing get decided by listening rather than by reading voice labels.
 *
 *   node scripts/audio/preview.mjs --text-file x.txt --voices a,b,c --speed 0.9
 *
 * Output lands in out/audio/preview/. Keep the excerpt short — this is the one
 * place it's worth spending credits repeatedly.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const argv = process.argv.slice(2)
const val = (f, d) => { const i = argv.indexOf(f); return i === -1 ? d : argv[i + 1] }

const manifest = JSON.parse(readFileSync(join(ROOT, 'src/data/audio/manifest.json'), 'utf8'))
const S = manifest.synthesis
const text = readFileSync(val('--text-file'), 'utf8').trim()
const speeds = val('--speed', '1.0').split(',').map(Number)
const voices = val('--voices', S.voiceId).split(',')
const names = Object.fromEntries((val('--names', '') || '').split(',').filter(Boolean).map((p) => p.split(':')))

const OUT = join(ROOT, 'out', 'audio', 'preview')
mkdirSync(OUT, { recursive: true })

const total = text.length * voices.length * speeds.length
console.log(`\n  ${text.length} chars × ${voices.length} voices × ${speeds.length} speed(s) = ${total.toLocaleString()} chars · ~$${(total / 1000 * 0.10).toFixed(2)}\n`)

for (const voice of voices) {
  for (const speed of speeds) {
    const label = `${names[voice] ?? voice}-speed${speed}`
    process.stdout.write(`  → ${label} … `)
    const res = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${voice}?output_format=${S.outputFormat}`,
      { method: 'POST',
        headers: { 'xi-api-key': process.env.ELEVENLABS_API_KEY, 'content-type': 'application/json' },
        body: JSON.stringify({
          text, model_id: S.modelId, apply_text_normalization: 'off', seed: S.seed,
          voice_settings: { ...S.voiceSettings, speed },
        }) })
    if (!res.ok) { console.log(`FAILED ${res.status} — ${(await res.text()).slice(0, 160)}`); continue }
    const buf = Buffer.from(await res.arrayBuffer())
    writeFileSync(join(OUT, `${label}.mp3`), buf)
    console.log(`${(buf.length / 1024).toFixed(0)} KB`)
  }
}
console.log(`\n  out/audio/preview/\n`)
