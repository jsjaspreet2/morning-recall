// Render every design page through the *real* site pipeline and assert the boards
// survive it. rehype-raw parses the SVG with parse5, hast normalizes the attribute
// names, and react-markdown turns that into elements — a board can be perfectly
// valid SVG and still lose its viewBox or its arrowheads somewhere in there.
//
//     node tools/diagrams/verify.mjs
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSlug from 'rehype-slug'
import rehypeHighlight from 'rehype-highlight'
import { readFileSync, readdirSync } from 'node:fs'

const dir = 'src/data/designs'
let boards = 0
const bad = []

for (const file of readdirSync(dir).filter(f => f.endsWith('.md')).sort()) {
  const md = readFileSync(`${dir}/${file}`, 'utf8')
  const html = renderToStaticMarkup(React.createElement(ReactMarkdown, {
    remarkPlugins: [remarkGfm],
    rehypePlugins: [rehypeRaw, rehypeSlug, [rehypeHighlight, { detect: true, ignoreMissing: true }]],
    children: md,
  }))

  const svgs = html.match(/<svg[\s\S]*?<\/svg>/g) ?? []
  const wraps = (html.match(/<div class="diagram" data-board="/g) ?? []).length
  const caps = (html.match(/class="diagram-cap"/g) ?? []).length
  const heads = (html.match(/class="dg-head"/g) ?? []).length
  const ids = [...md.matchAll(/data-board="([^"]+)"/g)].map(m => m[1])

  const faults = []
  if (svgs.length !== wraps) faults.push(`${svgs.length} svg vs ${wraps} wrapper`)
  if (wraps !== caps) faults.push(`${wraps} wrapper vs ${caps} caption`)
  if (svgs.some(s => !/viewBox="/.test(s))) faults.push('a board lost its viewBox')
  if (/&lt;(svg|rect|path|circle)/.test(html)) faults.push('markup escaped to text')
  if (svgs.length && !heads) faults.push('no arrowheads rendered')
  if (new Set(ids).size !== ids.length) faults.push('duplicate data-board id')
  if (faults.length) bad.push(`${file}: ${faults.join('; ')}`)

  boards += svgs.length
  console.log(`${file.padEnd(26)} boards=${svgs.length} heads=${String(heads).padStart(3)}` +
    ` ${faults.length ? 'FAIL — ' + faults.join('; ') : 'ok'}`)
}

console.log(`\n${boards} boards checked.`)
if (bad.length) {
  console.error('\n' + bad.join('\n'))
  process.exit(1)
}
