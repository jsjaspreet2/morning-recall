import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSlug from 'rehype-slug'
import rehypeHighlight from 'rehype-highlight'

// Renders a guide's markdown. remark-gfm gives tables/strikethrough,
// rehype-raw parses inline HTML so <details>/<summary> collapsibles work,
// rehype-slug adds heading ids (for the TOC), rehype-highlight colors code.
// Tables get wrapped so they can scroll horizontally on narrow phones.
//
// rehype-raw must run FIRST: it turns raw HTML into real element nodes, and every
// plugin after it needs a parsed tree to walk. Ordered after rehype-slug, a
// heading written as HTML would never receive an id and would vanish from the TOC.
//
// The tradeoff it buys: angle brackets in prose are now live markup. A bare `<nav>`
// in running text becomes an element and silently swallows the rest of the block,
// so tag names in prose must be backticked. All guides were audited when this was
// enabled; re-run that check if you paste in new prose.
export default function Markdown({ md }: { md: string }) {
  return (
    <div className="prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[
          rehypeRaw,
          rehypeSlug,
          [rehypeHighlight, { detect: true, ignoreMissing: true }],
        ]}
        components={{
          table: ({ children, ...props }) => (
            <div className="table-wrap">
              <table {...props}>{children}</table>
            </div>
          ),
        }}
      >
        {md}
      </ReactMarkdown>
    </div>
  )
}
