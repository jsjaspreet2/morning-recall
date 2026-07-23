import GithubSlugger from 'github-slugger'

export interface Heading {
  depth: 2 | 3
  text: string
  id: string
}

// Pull ## / ### headings from the markdown, skipping fenced code blocks, and
// assign ids with the same slugger rehype-slug uses so TOC links line up with
// the rendered heading ids.
export function extractHeadings(md: string): Heading[] {
  const slugger = new GithubSlugger()
  const out: Heading[] = []
  let inFence = false

  for (const line of md.split('\n')) {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence
      continue
    }
    if (inFence) continue

    // Match every heading level so the slugger consumes ids in the same order
    // rehype-slug does (it slugs h1–h6), keeping our TOC ids in sync.
    const m = /^(#{1,6})\s+(.*\S)\s*$/.exec(line)
    if (!m) continue
    const depth = m[1].length
    // strip inline markdown emphasis/backticks for the label
    const text = m[2].replace(/[`*_]/g, '').trim()
    const id = slugger.slug(text)
    if (depth === 2 || depth === 3) out.push({ depth, text, id })
  }
  return out
}
