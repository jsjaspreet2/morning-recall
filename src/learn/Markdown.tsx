import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSlug from 'rehype-slug'
import rehypeHighlight from 'rehype-highlight'

// Renders a guide's markdown. remark-gfm gives tables/strikethrough,
// rehype-slug adds heading ids (for the TOC), rehype-highlight colors code.
// Tables get wrapped so they can scroll horizontally on narrow phones.
export default function Markdown({ md }: { md: string }) {
  return (
    <div className="prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSlug, [rehypeHighlight, { detect: true, ignoreMissing: true }]]}
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
