#!/usr/bin/env node
/**
 * manifest + synth cache -> public/feed/<slug>/podcast.xml
 *
 * Hand-rolled XML on purpose: this repo has no build tooling by choice, and a
 * feed generator dependency to emit one fixed document would be the wrong trade.
 *
 *   node scripts/audio/feed.mjs            write the feed
 *   node scripts/audio/feed.mjs --check    fail if the committed feed is stale
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const CHECK = process.argv.includes('--check')

const manifest = JSON.parse(readFileSync(join(ROOT, 'src/data/audio/manifest.json'), 'utf8'))
const cachePath = join(ROOT, 'out/audio/.cache.json')
const cache = existsSync(cachePath) ? JSON.parse(readFileSync(cachePath, 'utf8')) : {}

const { show } = manifest
const base = `https://github.com/${show.repo}/releases/download/${show.releaseTag}/`
const feedDir = join(ROOT, 'public', 'feed', show.feedSlug)
const feedUrl = `${show.link}feed/${show.feedSlug}/podcast.xml`

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]))
const cdata = (s) => `<![CDATA[${String(s).replace(/]]>/g, ']]]]><![CDATA[>')}]]>`

// Ascending pubDates in curriculum order, so a podcast client plays the course
// in study order rather than synthesis order. All in the past — several clients
// hide future-dated items.
const EPOCH = Date.UTC(2026, 0, 5, 9, 0, 0)
const rfc2822 = (ms) => new Date(ms).toUTCString().replace('GMT', '+0000')

// Publish only episodes that are both marked ready and actually synthesized —
// a draft with a stale cache entry must never reach a subscriber's feed.
const ready = manifest.episodes
  .filter((e) => e.status === 'ready' && cache[e.id])
  .sort((a, b) => a.order - b.order)

const items = ready.map((e, i) => {
  const c = cache[e.id]
  return `    <item>
      <title>${esc(e.title)}</title>
      <link>${esc(show.link)}</link>
      <guid isPermaLink="false">${esc(`${show.repo}/${e.id}`)}</guid>
      <pubDate>${rfc2822(EPOCH + i * 24 * 3600 * 1000)}</pubDate>
      <description>${cdata(e.summary ?? e.title)}</description>
      <enclosure url="${esc(base + e.id)}.mp3" length="${c.bytes}" type="audio/mpeg"/>
      <itunes:duration>${c.duration}</itunes:duration>
      <itunes:episode>${i + 1}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>`
}).join('\n')

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>${esc(show.title)}</title>
    <link>${esc(show.link)}</link>
    <description>${cdata(show.description)}</description>
    <language>${esc(show.language)}</language>
    <atom:link rel="self" type="application/rss+xml" href="${esc(feedUrl)}"/>
    <itunes:author>${esc(show.author)}</itunes:author>
    <itunes:image href="${esc(`${show.link}feed/${show.feedSlug}/${show.image}`)}"/>
    <itunes:category text="${esc(show.category)}"/>
    <itunes:explicit>${show.explicit}</itunes:explicit>
    <itunes:type>serial</itunes:type>
    <!-- These two, not the unguessable URL, are what actually keep this out of
         public directories: block Apple from listing it, and refuse imports. -->
    <itunes:block>Yes</itunes:block>
    <podcast:locked>yes</podcast:locked>
    <lastBuildDate>${rfc2822(EPOCH + Math.max(ready.length - 1, 0) * 24 * 3600 * 1000)}</lastBuildDate>
${items}
  </channel>
</rss>
`

const outPath = join(feedDir, 'podcast.xml')
if (CHECK) {
  const current = existsSync(outPath) ? readFileSync(outPath, 'utf8') : ''
  if (current !== xml) { console.error('  feed is stale — run: npm run audio:feed'); process.exit(1) }
  console.log(`  feed up to date (${ready.length} episodes)`)
  process.exit(0)
}

mkdirSync(feedDir, { recursive: true })
writeFileSync(outPath, xml)
const secs = ready.reduce((n, e) => n + cache[e.id].duration, 0)
console.log(`\n  ${outPath.replace(ROOT + '/', '')}`)
console.log(`  ${ready.length} episodes · ${Math.round(secs / 60)} min`)
console.log(`  ${feedUrl}\n`)
if (!ready.length) console.log('  (no synthesized episodes yet — run npm run audio:synth first)\n')
