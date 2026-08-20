#!/usr/bin/env node
/**
 * List the voices available on the account, so a voiceId can be pasted into
 * src/data/audio/manifest.json. Narration wants a calm, low-variance voice —
 * high stability, minimal style. Preview each before committing to 7 hours of it.
 */
const key = process.env.ELEVENLABS_API_KEY
if (!key) { console.error('ELEVENLABS_API_KEY is not set.'); process.exit(1) }

const res = await fetch('https://api.elevenlabs.io/v2/voices?page_size=100', { headers: { 'xi-api-key': key } })
if (!res.ok) { console.error(`${res.status} ${res.statusText} — ${(await res.text()).slice(0, 300)}`); process.exit(1) }
const { voices } = await res.json()

console.log()
for (const v of voices) {
  const l = v.labels ?? {}
  const tags = [l.accent, l.age, l.gender, l.use_case].filter(Boolean).join(', ')
  console.log(`  ${v.voice_id}  ${(v.name ?? '').padEnd(18)} ${tags}`)
  if (v.preview_url) console.log(`  ${' '.repeat(22)}${v.preview_url}`)
}
console.log(`\n  ${voices.length} voices. Paste one into synthesis.voiceId in src/data/audio/manifest.json.\n`)
