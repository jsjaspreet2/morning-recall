# OpenAI Transcript Walkthrough — Thu 9/17

> Sixty minutes in CoderPad. One problem, extended by follow-ups: a chat box that streams a reply,
> then a conversation, then what happens when you submit mid-stream, then scroll pinning, then what
> a screen reader hears, then two tests. This guide builds it in that order, showing the code as it
> stands after each part and exactly what changes between parts.

Companion to `OpenAI Screen` (`§07` is the clock and the first four minutes, `§08` is the theory
behind every block here, `§10` is the testing axis). This guide is the reconstruction of the round
as one continuous build, so that on the day each follow-up lands on code you have already typed
twice.

**How sure is the five-part script.** Public reports (GreatFrontEnd, Exponent, HelloInterview,
interviewing.io) agree on the family: a practical UI problem, a streaming chat interface with
loading, error and cancel states named as the representative example, follow-ups that extend
scope, and an explicit grade for tests. None publishes the follow-ups word for word. The five below
are the ones that fall out of the product itself, in the order an interviewer naturally adds them.
If the real follow-ups differ, the mechanisms are the same; only the labels move.

## 00 — Before you type

### A. THE CLOCK

| Minute | Target | Gate |
|---|---|---|
| 0–4 | Clarify. Real endpoint or mock? Plain text stream or SSE? Can the pad run tests? React or plain TS? | — |
| 4–8 | **Types and the skeleton first.** Status enum, message shape, the JSX with every label and test id | Types on screen by minute 8 |
| 8–22 | **Part 1**: submit → stream → render, Stop, error, retry | **Something streams by minute 22** |
| 22–32 | **Part 2 and 3**: multi-turn, then supersede | Old bubble freezes, late tokens land nowhere |
| 32–48 | **Part 4 and 5**: scroll pinning, announcements | Jump to latest works; status region reads Responding |
| 48–56 | **Tests.** Two written, three named | Do not skip. Graded on its own |
| 56–60 | What you left out, and why | — |

### B. THE FOUR QUESTIONS

Ask these before the first keystroke. Each one changes the code.

1. **What does the endpoint return?** The drill and this guide assume `text/event-stream`: the
   byte loop plus a frame buffer split on the blank line (`§08` here, `OpenAI Screen §05 C`). A
   plain text stream is the same loop without the buffer. JSON lines is the buffer split on `\n`.
2. **Real endpoint or mock?** Default to a mock you write in two minutes, because the interesting
   part is the client. Say that.
3. **Can the pad run tests?** Ask at minute four so you know the answer at minute fifty.
4. **React or plain TS?** Everything here is React with TypeScript. The mechanisms transfer.

### C. THE SKELETON-FIRST RULE

The loop is the part you know. The points you lose are exact strings and attributes: the input's
label, the test id on a bubble, the empty-state text, the default value of a prop. So the first
thing on screen after the types is the JSX with all of those in place and no behaviour behind it.
Then the state. Then the loop.

```tsx
type Status = 'idle' | 'submitting' | 'streaming' | 'done' | 'stopped' | 'error'
type Message = { id: string; role: 'user' | 'assistant'; text: string }

type ChatProps = {
  fetchChat: typeof fetch // injected so tests can drive it; called exactly like fetch
}
```

The transport has `fetch`'s own signature, so the call is the production call: `POST` the prompt
as JSON, pass `{ signal }` in the init, read `text/event-stream` off `res.body`.

Say the enum out loud: six states, and `stopped` is not `error` because the user asked for it.
Two booleans give four states of which two are nonsense; six names cannot disagree.

## 01 — Part 1: "Build a chat box that streams the reply. Handle loading, error and cancel."

This is the component at minute 22. Everything later is a change to this file.

```tsx
import { useEffect, useRef, useState } from 'react'

const uid = () => crypto.randomUUID()

/**
 * One SSE frame → its `data` payload, or null for a comment / keep-alive.
 * `data:` lines join with `\n`; one space after the colon is stripped; lines
 * starting with `:` are comments; `event:`, `id:` and `retry:` are ignored here.
 */
function dataOf(frame: string): string | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).replace(/^ /, ''))
  return data.length ? data.join('\n') : null
}

export function Chat({ fetchChat }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<Status>('idle')
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)

  const abortRef = useRef<AbortController | null>(null)
  const genRef = useRef(0)
  const lastPromptRef = useRef('')

  const busy = status === 'submitting' || status === 'streaming'

  // Append to the last message. Only that object changes identity.
  const append = (text: string) =>
    setMessages((ms) => {
      const next = ms.slice()
      const last = next[next.length - 1]
      next[next.length - 1] = { ...last, text: last.text + text }
      return next
    })

  async function send(prompt: string) {
    abortRef.current?.abort()
    const gen = ++genRef.current
    const ctrl = new AbortController()
    abortRef.current = ctrl
    lastPromptRef.current = prompt

    setError(null)
    setMessages((ms) => [
      ...ms,
      { id: uid(), role: 'user', text: prompt },
      { id: uid(), role: 'assistant', text: '' },
    ])
    setStatus('submitting')

    try {
      const res = await fetchChat('/api/chat', {
        method: 'POST',
        headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
        body: JSON.stringify({ prompt }),
        signal: ctrl.signal,
      })
      if (gen !== genRef.current) return
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      // Two boundaries. TextDecoderStream handles a character cut across chunks;
      // `buf` handles a frame cut across chunks: parse only up to the blank line.
      let first = true
      let buf = ''
      stream: for await (const chunk of res.body.pipeThrough(new TextDecoderStream())) {
        if (gen !== genRef.current) return // superseded: leaving the loop cancels the stream
        buf += chunk
        let end: number
        while ((end = buf.search(/\r?\n\r?\n/)) !== -1) {
          const data = dataOf(buf.slice(0, end))
          buf = buf.slice(end).replace(/^\r?\n\r?\n/, '')
          if (data === null) continue // comment or keep-alive
          if (data === '[DONE]') break stream
          if (first) {
            first = false
            setStatus('streaming')
          }
          append((JSON.parse(data) as { delta: string }).delta)
        }
      }
      if (gen === genRef.current) setStatus('done')
    } catch (err) {
      if (gen !== genRef.current) return
      if (ctrl.signal.aborted) {
        setStatus('stopped') // not a failure; the text so far is kept
      } else {
        setError(err instanceof Error ? err.message : String(err))
        setStatus('error')
      }
    }
  }

  const stop = () => {
    if (!busy) return // a second Stop is a no-op
    abortRef.current?.abort()
    genRef.current++ // late tokens are dropped, not merely un-requested
    setStatus('stopped')
  }

  const retry = () => {
    setMessages((ms) => ms.slice(0, -2))
    void send(lastPromptRef.current)
  }

  useEffect(() => () => abortRef.current?.abort(), [])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text) return
    setInput('')
    void send(text)
  }

  return (
    <div className="chat">
      <ul className="transcript">
        {messages.map((m, i) => {
          const streaming = busy && i === messages.length - 1
          return (
            <li
              key={m.id}
              data-testid={m.role === 'assistant' ? 'assistant-message' : 'user-message'}
              aria-busy={streaming || undefined}
              className={`bubble ${m.role}`}
            >
              {m.role === 'assistant' && m.text === '' && status === 'done' ? (
                <em>No response.</em>
              ) : (
                m.text
              )}
            </li>
          )
        })}
      </ul>

      <p role="status" aria-live="polite" data-testid="status" className="sr-only">
        {status === 'streaming' ? 'Responding' : status === 'done' ? 'Response complete' : status === 'stopped' ? 'Stopped' : ''}
      </p>

      {error && (
        <p role="alert" data-testid="error" className="error">
          {error} <button type="button" onClick={retry}>Retry</button>
        </p>
      )}

      <form onSubmit={submit} className="composer">
        <input aria-label="Message" value={input} onChange={(e) => setInput(e.target.value)} />
        {busy ? (
          <button key="stop" type="button" onClick={stop}>Stop</button>
        ) : (
          <button key="send" type="submit">Send</button>
        )}
      </form>
    </div>
  )
}
```

### A. WHAT CARRIES IT

Five things, in the order an interviewer notices them. Say each one as you type it.

1. **The status enum.** Never `isLoading`. `submitting` is the gap before the first byte, where
   ChatGPT shows a pulsing dot; `streaming` is after. If you collapse them, say you would split
   them the moment the UI wants a thinking indicator.
2. **`res.ok` before the body.** An HTTP error arrives before any bytes. A loop that skips the check
   hangs instead of failing. The call itself is a plain fetch: prompt in the JSON body, the
   controller's signal as `{ signal }` in the init.
3. **`pipeThrough(new TextDecoderStream())`, then a frame buffer.** The body is bytes at whatever
   boundary the network produced. A multi-byte character can straddle two chunks; the decoder
   stream holds the partial sequence and flushes on close. An SSE frame can straddle two chunks
   too; the string buffer parses only up to the last blank line and keeps the tail. Comment lines
   (`: keep-alive`) are skipped, `data: [DONE]` ends the loop, everything else is `JSON.parse`d
   for its delta.
4. **Abort plus a generation counter.** Abort tells the network to stop, but a chunk already in
   flight still arrives. The counter is what refuses it. Stop bumps the counter; a new send bumps it
   too, which is how a superseded request's tokens land nowhere.
5. **`aria-live` on the status region, `aria-busy` on the bubble.** A live region on the streaming
   text re-announces every token. Not `role="log"` on the transcript either: it carries an implicit
   `aria-live="polite"`.

### B. THE EDGE CASES THE TESTS CHECK

| Case | Where it is handled |
|---|---|
| Stop keeps the text so far, status `stopped`, button returns to Send | `stop` and the catch branch on `ctrl.signal.aborted` |
| A second Stop is a no-op | `if (!busy) return` |
| Whitespace-only prompt never calls `fetchChat` | `submit` trims and returns |
| `fetchChat` is called like fetch: `POST`, JSON body with the prompt, `{ signal }` | the call in `send` |
| A frame split across two chunks parses once whole; a comment line is skipped | `buf` and `dataOf` |
| A stream that ends with no tokens renders an explicit empty state | the `No response.` branch |
| HTTP error before the body: Retry re-sends the last prompt | `res.ok`, `lastPromptRef`, `retry` |
| Error mid-stream keeps the partial text, error renders below | the catch's else branch sets `error` and leaves `messages` alone |
| Unmount mid-stream: no warning, no leak | the cleanup effect aborts |

## 02 — Part 2: "Now make it a conversation."

Part 1 already appends both turns at submit, so the transcript is already an array. What changes is
that "the last message" stops being a safe address. The moment there is more than one assistant
turn, every write goes by id.

**Before**, appending by position:

```tsx
const append = (text: string) =>
  setMessages((ms) => {
    const next = ms.slice()
    const last = next[next.length - 1]
    next[next.length - 1] = { ...last, text: last.text + text }
    return next
  })
```

**After**, a general patch by id, and the reply id captured at submit:

```tsx
const patch = (id: string, fn: (m: Message) => Message) =>
  setMessages((ms) => ms.map((m) => (m.id === id ? fn(m) : m)))

async function send(prompt: string) {
  // ...
  const replyId = uid()
  setMessages((ms) => [
    ...ms,
    { id: uid(), role: 'user', text: prompt },
    { id: replyId, role: 'assistant', text: '' },
  ])
  const append = (chunk: string) => patch(replyId, (m) => ({ ...m, text: m.text + chunk }))
  // ... the loop calls append(chunk) as before
}
```

Two things to say:

- **Both turns are appended together at submit**, so the stream has somewhere to write from the
  first byte and the assistant bubble exists, `aria-busy`, before the first token.
- **Keys are the message id from creation.** An array index as key means inserting or truncating
  above a bubble re-keys every bubble below it, and React remounts them. The test checks that
  earlier bubbles keep their DOM nodes across a second turn.

`map` copies only the one message that changed. The rest keep their identity, so memoised bubbles
skip re-rendering. Never `msg.text += chunk` followed by `{ ...state }`: the outer object is new,
the message is not, and nothing re-renders.

## 03 — Part 3: "What if I submit again while a reply is still streaming?"

Now the transcript has two answers to give: how the old reply ended, and what the new one is doing.
A single component status can only hold the second. So the outcome moves onto the message, and the
generation counter becomes a request id that lives on the data.

**The types gain two optional fields:**

```tsx
type MessageState = 'streaming' | 'done' | 'stopped' | 'error'
type Message = {
  id: string
  role: 'user' | 'assistant'
  text: string
  requestId?: string  // the request that owns this bubble
  state?: MessageState // how this bubble ended, kept after newer turns start
}
```

**`genRef` becomes `currentRef`, holding the request id that may still write:**

```tsx
const currentRef = useRef<string | null>(null)

/** Freeze whatever is still streaming, so its bubble stays honest after a supersede. */
const freezeStreaming = (as: MessageState) =>
  setMessages((ms) => ms.map((m) => (m.state === 'streaming' ? { ...m, state: as } : m)))

async function send(prompt: string) {
  abortRef.current?.abort()
  freezeStreaming('stopped')

  const requestId = uid()
  const replyId = uid()
  const ctrl = new AbortController()
  abortRef.current = ctrl
  currentRef.current = requestId
  lastPromptRef.current = prompt

  setError(null)
  setMessages((ms) => [
    ...ms,
    { id: uid(), role: 'user', text: prompt },
    { id: replyId, role: 'assistant', text: '', requestId, state: 'streaming' },
  ])
  setStatus('submitting')

  // A delta applies only if this request is still current AND the bubble is still
  // streaming. Stop clears the first, a supersede sets the second, and a chunk
  // already in flight arrives after both.
  const isCurrent = () => currentRef.current === requestId
  const append = (chunk: string) => {
    if (!isCurrent()) return
    patch(replyId, (m) => (m.state === 'streaming' ? { ...m, text: m.text + chunk } : m))
  }

  try {
    const res = await fetchChat('/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
      body: JSON.stringify({ prompt }),
      signal: ctrl.signal,
    })
    if (!isCurrent()) return
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

    let first = true
    let buf = ''
    stream: for await (const chunk of res.body.pipeThrough(new TextDecoderStream())) {
      if (!isCurrent()) return
      buf += chunk
      let end: number
      while ((end = buf.search(/\r?\n\r?\n/)) !== -1) {
        const data = dataOf(buf.slice(0, end))
        buf = buf.slice(end).replace(/^\r?\n\r?\n/, '')
        if (data === null) continue
        if (data === '[DONE]') break stream
        if (first) {
          first = false
          setStatus('streaming')
        }
        append((JSON.parse(data) as { delta: string }).delta)
      }
    }
    if (!isCurrent()) return
    patch(replyId, (m) => ({ ...m, state: 'done' }))
    setStatus('done')
  } catch (err) {
    if (!isCurrent()) return
    if (ctrl.signal.aborted) {
      patch(replyId, (m) => ({ ...m, state: 'stopped' }))
      setStatus('stopped')
    } else {
      patch(replyId, (m) => ({ ...m, state: 'error' }))
      setError(err instanceof Error ? err.message : String(err))
      setStatus('error')
    }
  }
}

const stop = () => {
  if (!busy) return
  abortRef.current?.abort()
  currentRef.current = null // late tokens are dropped, not merely un-requested
  freezeStreaming('stopped')
  setStatus('stopped')
}
```

**The bubble reads its own state now**, not the component's:

```tsx
<li
  key={m.id}
  data-testid={m.role === 'assistant' ? 'assistant-message' : 'user-message'}
  data-state={m.state}
  aria-busy={m.state === 'streaming' || undefined}
  className={`bubble ${m.role}`}
>
  {m.role === 'assistant' && m.text === '' && m.state === 'done' ? <em>No response.</em> : m.text}
  {m.role === 'assistant' && m.state === 'stopped' && <span className="tag"> · stopped</span>}
</li>
```

And `submit` drops any `busy` guard, because a submit mid-stream is the supersede. Say the product
note: "ChatGPT disables Send while streaming. That is a product choice. The mechanism is needed
either way, because Stop-then-Send and a double click both produce the same race."

### A. WHY TWO OWNERS FOR "HOW DID IT END"

- **Component `status`** answers "is a request in flight now, and how did the latest one end." It
  drives the Send versus Stop button and the live region.
- **`Message.state`** answers "how did this bubble end." It drives the stopped tag, the error
  placement, and `aria-busy` on the one bubble still streaming. Once there are two replies these
  diverge: after Stop then Send, status is `streaming` and the old bubble is `stopped`.

The guard is two checks because they fail at different times. Stop sets `currentRef` to null, so
the old request is no longer current. A supersede freezes the old bubble to `stopped`, so even a
delta that passes the first check finds a non-streaming bubble and does nothing. The same two
checks carry edit-and-resubmit unchanged.

## 04 — Part 4: "Keep the view pinned to the bottom as it streams, unless I've scrolled up."

Three pieces: measure intent on scroll, auto-scroll after each render only if pinned, and a Jump
button when not.

```tsx
const scrollerRef = useRef<HTMLUListElement>(null)
const pinnedRef = useRef(true)               // intent: is the reader following the stream
const [unpinned, setUnpinned] = useState(false) // only for rendering the Jump button

const onScroll = () => {
  const el = scrollerRef.current
  if (!el) return
  // A threshold, never equality: fractional pixels mean scrollTop rarely hits the exact bottom.
  const pinned = el.scrollHeight - el.scrollTop - el.clientHeight < pinThresholdPx
  pinnedRef.current = pinned
  setUnpinned(!pinned) // same value → React bails out; this flips only when pinned-ness changes
}

useLayoutEffect(() => {
  if (!pinnedRef.current) return
  const el = scrollerRef.current
  if (el) el.scrollTop = el.scrollHeight // instant. Smooth retargets on every token and never settles
}, [messages])

const jumpToLatest = () => {
  const el = scrollerRef.current
  if (!el) return
  pinnedRef.current = true
  setUnpinned(false)
  // Smooth is fine here: one explicit gesture, not one per token. jsdom has no scrollTo.
  if (typeof el.scrollTo === 'function') el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  else el.scrollTop = el.scrollHeight
}
```

```tsx
<ul ref={scrollerRef} onScroll={onScroll} data-testid="transcript" className="transcript" style={{ maxHeight: maxHeightPx }}>
  {/* ... */}
</ul>
{unpinned && (
  <button type="button" onClick={jumpToLatest} className="jump">Jump to latest</button>
)}
```

### A. THE SUBTRACTION, VARIABLE BY VARIABLE

`scrollHeight` is the full content height including what is hidden. `clientHeight` is the height
of the visible box. `scrollTop` is how far the content has scrolled past the top edge, from 0 up to
`scrollHeight − clientHeight`. So `scrollHeight − scrollTop − clientHeight` is the number of pixels
still hidden below the window. Under the threshold means "at the bottom".

### B. WHAT TO SAY

- **Intent lives in a ref, measured in `onScroll`, before the append.** Measure inside the effect
  and the list has already grown; you are always one message from the bottom.
- **Layout effect, not effect,** so the scroll lands before paint and the user never sees a frame
  with the new token below the fold.
- **Instant while streaming, smooth only for the button.** `behavior: 'smooth'` animates toward a
  target that moves every 30ms and never arrives.
- **The height is a prop only so tests can force overflow.** jsdom has no layout, so the spec
  installs `scrollHeight` and `clientHeight` getters and asserts on `scrollTop`. In production the
  height is CSS.

## 05 — Part 5: "A screen-reader user is listening. What do they hear?"

One sentence per transition, never the text. Progress at a cadence, not per token.

```tsx
const [announcement, setAnnouncement] = useState('')
const words = (text: string) => text.split(/\s+/).filter(Boolean).length

// inside send, replacing the bare setStatus calls:
let acc = ''
let lastAnnouncedAt = 0
setAnnouncement('')
// ...
for await (const chunk of res.body.pipeThrough(new TextDecoderStream())) {
  if (!isCurrent()) return
  acc += chunk
  append(chunk)
  if (first) {
    first = false
    setStatus('streaming')
    setAnnouncement('Responding')
    lastAnnouncedAt = Date.now()
  } else if (Date.now() - lastAnnouncedAt >= announceEveryMs) {
    setAnnouncement(`Responding, ${words(acc)} words so far`)
    lastAnnouncedAt = Date.now()
  }
}
// ... on done:     setAnnouncement('Response complete')
// ... on stopped:  setAnnouncement('Stopped')
// ... on error:    setAnnouncement('Something went wrong')
```

```tsx
<p role="status" aria-live="polite" data-testid="status" className="sr-only">
  {announcement}
</p>
```

Three rules, and the test checks all three:

- The status region is the only `aria-live` on the page.
- The streaming bubble is `aria-busy` and has no `aria-live`.
- The transcript is a plain `ul`, not `role="log"`, which carries an implicit `aria-live="polite"`
  and would re-announce every mutation.

The progress cadence is a product detail. "Responding" then "Response complete" is the part that
matters; say the cadence, build it if there is time.

## 06 — Minute 50: "Write two tests."

Both use the hand-driven transport from the drill's mock, where nothing moves until you push. That
keeps the tests synchronous and free of fake timers. In the room, if the pad cannot run tests, write
them anyway as the spec and say so.

```tsx
async function type(text: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Message'), text)
  await user.click(screen.getByRole('button', { name: 'Send' }))
  return user
}

it('Stop mid-stream keeps the partial text and sets status to stopped, not error', async () => {
  const t = controllableFetch()
  render(<Chat fetchChat={t.fetchChat} />)
  const user = await type('hello')

  await act(async () => {
    t.push('partial answer')
  })
  await user.click(screen.getByRole('button', { name: 'Stop' }))

  expect(screen.getByTestId('assistant-message')).toHaveTextContent('partial answer')
  await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent(/stopped/i))
  expect(screen.queryByTestId('error')).toBeNull()
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument())
})

it('tokens arriving after Stop do not change the rendered text', async () => {
  const t = controllableFetch()
  render(<Chat fetchChat={t.fetchChat} />)
  const user = await type('hello')

  await act(async () => {
    t.push('partial')
  })
  await user.click(screen.getByRole('button', { name: 'Stop' }))
  await act(async () => {
    t.push(' late')
  })

  const bubble = screen.getByTestId('assistant-message')
  expect(bubble).toHaveTextContent('partial')
  expect(bubble).not.toHaveTextContent('late')
})
```

Three to name without writing: a whitespace-only prompt never calls the transport; a superseding
submit freezes the old bubble and its late token lands nowhere; earlier bubbles keep their DOM
nodes across a second turn (`toBe` on the element before and after).

## 07 — The finished component

What the file looks like at minute 56, all five parts in. This is the reference; the point of the
guide is that you arrived here one change at a time.

```tsx
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

export type Status = 'idle' | 'submitting' | 'streaming' | 'done' | 'stopped' | 'error'
export type MessageState = 'streaming' | 'done' | 'stopped' | 'error'
export type Message = {
  id: string
  role: 'user' | 'assistant'
  text: string
  requestId?: string
  state?: MessageState
}
export type ChatProps = {
  fetchChat: typeof fetch
  pinThresholdPx?: number
  announceEveryMs?: number
  maxHeightPx?: number
}

const uid = () => crypto.randomUUID()
const words = (text: string) => text.split(/\s+/).filter(Boolean).length

function dataOf(frame: string): string | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).replace(/^ /, ''))
  return data.length ? data.join('\n') : null
}

export function Chat({ fetchChat, pinThresholdPx = 40, announceEveryMs = 5000, maxHeightPx = 320 }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<Status>('idle')
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const [unpinned, setUnpinned] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const currentRef = useRef<string | null>(null)
  const lastPromptRef = useRef('')
  const scrollerRef = useRef<HTMLUListElement>(null)
  const pinnedRef = useRef(true)

  const busy = status === 'submitting' || status === 'streaming'

  const patch = useCallback((id: string, fn: (m: Message) => Message) => {
    setMessages((ms) => ms.map((m) => (m.id === id ? fn(m) : m)))
  }, [])

  const freezeStreaming = useCallback((as: MessageState) => {
    setMessages((ms) => ms.map((m) => (m.state === 'streaming' ? { ...m, state: as } : m)))
  }, [])

  const send = useCallback(
    async (prompt: string) => {
      abortRef.current?.abort()
      freezeStreaming('stopped')

      const requestId = uid()
      const replyId = uid()
      const ctrl = new AbortController()
      abortRef.current = ctrl
      currentRef.current = requestId
      lastPromptRef.current = prompt

      setError(null)
      setMessages((ms) => [
        ...ms,
        { id: uid(), role: 'user', text: prompt },
        { id: replyId, role: 'assistant', text: '', requestId, state: 'streaming' },
      ])
      setStatus('submitting')
      setAnnouncement('')

      const isCurrent = () => currentRef.current === requestId
      const append = (chunk: string) => {
        if (!isCurrent()) return
        patch(replyId, (m) => (m.state === 'streaming' ? { ...m, text: m.text + chunk } : m))
      }

      let acc = ''
      let lastAnnouncedAt = 0

      try {
        const res = await fetchChat('/api/chat', {
          method: 'POST',
          headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
          body: JSON.stringify({ prompt }),
          signal: ctrl.signal,
        })
        if (!isCurrent()) return
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

        let first = true
        let buf = ''
        const onDelta = (delta: string) => {
          acc += delta
          append(delta)
          if (first) {
            first = false
            setStatus('streaming')
            setAnnouncement('Responding')
            lastAnnouncedAt = Date.now()
          } else if (Date.now() - lastAnnouncedAt >= announceEveryMs) {
            setAnnouncement(`Responding, ${words(acc)} words so far`)
            lastAnnouncedAt = Date.now()
          }
        }

        stream: for await (const chunk of res.body.pipeThrough(new TextDecoderStream())) {
          if (!isCurrent()) return
          buf += chunk
          let end: number
          while ((end = buf.search(/\r?\n\r?\n/)) !== -1) {
            const data = dataOf(buf.slice(0, end))
            buf = buf.slice(end).replace(/^\r?\n\r?\n/, '')
            if (data === null) continue
            if (data === '[DONE]') break stream
            onDelta((JSON.parse(data) as { delta: string }).delta)
          }
        }

        if (!isCurrent()) return
        patch(replyId, (m) => ({ ...m, state: 'done' }))
        setStatus('done')
        setAnnouncement('Response complete')
      } catch (err) {
        if (!isCurrent()) return
        if (ctrl.signal.aborted) {
          patch(replyId, (m) => ({ ...m, state: 'stopped' }))
          setStatus('stopped')
          setAnnouncement('Stopped')
        } else {
          patch(replyId, (m) => ({ ...m, state: 'error' }))
          setError(err instanceof Error ? err.message : String(err))
          setStatus('error')
          setAnnouncement('Something went wrong')
        }
      }
    },
    [announceEveryMs, fetchChat, freezeStreaming, patch],
  )

  const stop = useCallback(() => {
    if (!busy) return
    abortRef.current?.abort()
    currentRef.current = null
    freezeStreaming('stopped')
    setStatus('stopped')
    setAnnouncement('Stopped')
  }, [busy, freezeStreaming])

  const retry = useCallback(() => {
    if (lastPromptRef.current) {
      setMessages((ms) => ms.slice(0, -2))
      void send(lastPromptRef.current)
    }
  }, [send])

  useEffect(() => () => abortRef.current?.abort(), [])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text) return
    setInput('')
    void send(text)
  }

  const onScroll = () => {
    const el = scrollerRef.current
    if (!el) return
    const pinned = el.scrollHeight - el.scrollTop - el.clientHeight < pinThresholdPx
    pinnedRef.current = pinned
    setUnpinned(!pinned)
  }

  useLayoutEffect(() => {
    if (!pinnedRef.current) return
    const el = scrollerRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  const jumpToLatest = () => {
    const el = scrollerRef.current
    if (!el) return
    pinnedRef.current = true
    setUnpinned(false)
    if (typeof el.scrollTo === 'function') el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    else el.scrollTop = el.scrollHeight
  }

  return (
    <div className="chat">
      <ul ref={scrollerRef} data-testid="transcript" onScroll={onScroll} className="transcript" style={{ maxHeight: maxHeightPx }}>
        {messages.map((m) => (
          <li
            key={m.id}
            data-role={m.role}
            data-state={m.state}
            data-testid={m.role === 'assistant' ? 'assistant-message' : 'user-message'}
            aria-busy={m.state === 'streaming' || undefined}
            className={`bubble ${m.role}`}
          >
            {m.role === 'assistant' && m.text === '' && m.state === 'done' ? <em>No response.</em> : m.text}
            {m.role === 'assistant' && m.state === 'stopped' && <span className="tag"> · stopped</span>}
          </li>
        ))}
      </ul>

      {unpinned && (
        <button type="button" onClick={jumpToLatest} className="jump">Jump to latest</button>
      )}

      <p role="status" aria-live="polite" data-testid="status" className="sr-only">
        {announcement}
      </p>

      {error && (
        <p role="alert" data-testid="error" className="error">
          {error} <button type="button" onClick={retry}>Retry</button>
        </p>
      )}

      <form onSubmit={submit} className="composer">
        <input aria-label="Message" value={input} onChange={(e) => setInput(e.target.value)} />
        {busy ? (
          <button key="stop" type="button" onClick={stop}>Stop</button>
        ) : (
          <button key="send" type="submit">Send</button>
        )}
      </form>
    </div>
  )
}
```

## 08 — Facts about the loop worth saying

- **`for await` over the body.** `response.body` is a `ReadableStream`, and a `ReadableStream` is
  an async iterable. Piping through `TextDecoderStream` makes the chunks strings. Support is Chrome
  124, Firefox 110, Safari 27. Older Safari needs `getReader()` and a `while (true)` over
  `reader.read()`; say it, do not write it.
- **Leaving the loop early cancels the stream.** `return`, `break` or a throw inside the body calls
  the iterator's `return()`, which cancels the reader. That is why the guard can simply `return`.
- **Abort arrives as a rejection.** A real fetch rejects the pending iteration with an `AbortError`
  when aborted mid-body, or rejects the `fetch` call itself if the abort lands before the headers.
  Both reach the catch. Decide `stopped` versus `error` from `ctrl.signal.aborted`, not from the
  error's name. The signal is the one source of truth for "did the user stop this".
- **Abort is still not enough on its own.** A chunk already in flight arrives after the abort. The
  request id check is what drops it. Say "abort un-requests, the id check refuses the answer".
- **SSE is the second boundary.** The loop feeds a string buffer; only text up to the last blank
  line is parsed and the unfinished tail waits for the next chunk. Comment lines starting with a
  colon are skipped, `data: [DONE]` breaks out of the loop (which cancels the body), everything
  else is `JSON.parse`d for its delta. Two boundary problems, two fixes: the decoder stream for
  characters, the buffer for frames. Named and skipped: `event:`, `id:`, `retry:` and resuming
  with `Last-Event-ID`.
- **Batching is the thing you name and skip.** Five hundred chunks are five hundred renders. A
  `requestAnimationFrame` buffer that flushes once per frame fixes it in ten lines. Say it at
  minute 56.

## 09 — What to leave out, and say that you did

Naming what you left out and why scores better than silently writing more.

- The `requestAnimationFrame` buffer so chunks are not renders.
- A `ResizeObserver` on the transcript for content that grows without a token: an image loading, a
  code block reflowing. The robust version of Part 4.
- Virtualization for thousands of messages.
- Markdown rendering with a fence-aware block split.
- Edit-and-resubmit: abort first, truncate below the edited turn, resubmit with a new request id.
  The two-check guard carries it unchanged.
- Extracting `useChat`: the state, `send`, `stop` and `retry` move into a hook and the component
  keeps the JSX. Name it as the refactor.
