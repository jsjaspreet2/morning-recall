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

export interface TocSection {
  /** The `##` itself. */
  heading: Heading
  /** Its `###` children, in document order. */
  children: Heading[]
}

/**
 * Group the flat heading list into `##` sections with their `###` children.
 *
 * The UIE guide has 132 headings, and a flat sidebar list of that is a scrollbar
 * with words in it. Nesting lets the sidebar show ~15 sections and expand only
 * the one being read.
 *
 * A `###` appearing before any `##` is dropped rather than orphaned — every guide
 * opens with a `##`, so this only guards malformed input.
 */
export function groupHeadings(headings: Heading[]): TocSection[] {
  const out: TocSection[] = []
  for (const h of headings) {
    if (h.depth === 2) out.push({ heading: h, children: [] })
    else out[out.length - 1]?.children.push(h)
  }
  return out
}
