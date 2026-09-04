/* Shared presentation helpers for the drill visualizations.
   Deliberately tiny and dependency-free: every page's ALGORITHM is written out
   verbatim in that page, so the page cannot drift from what the tests grade.
   Only the drawing lives here. */
(function (global) {
  const SVGNS = 'http://www.w3.org/2000/svg'

  const $ = (id) => document.getElementById(id)

  function h(tag, attrs, kids) {
    const n = document.createElement(tag)
    apply(n, attrs, kids)
    return n
  }

  function s(tag, attrs, kids) {
    const n = document.createElementNS(SVGNS, tag)
    apply(n, attrs, kids)
    return n
  }

  function apply(n, attrs, kids) {
    for (const k in attrs || {}) {
      const v = attrs[k]
      if (v === null || v === undefined || v === false) continue
      if (k === 'text') n.textContent = String(v)
      else if (k === 'html') n.innerHTML = v
      else if (k === 'class') n.setAttribute('class', v)
      else if (k.startsWith('on') && typeof v === 'function') n.addEventListener(k.slice(2), v)
      else n.setAttribute(k, String(v))
    }
    for (const kid of [].concat(kids || [])) {
      if (kid === null || kid === undefined || kid === false) continue
      n.appendChild(typeof kid === 'string' ? document.createTextNode(kid) : kid)
    }
  }

  /** An SVG that scales to its container but keeps its drawing coordinates. */
  function svgRoot(w, hgt, cls) {
    return s('svg', { viewBox: `0 0 ${w} ${hgt}`, class: cls || '', 'aria-hidden': 'true' })
  }

  function mount(target, node) {
    const el = typeof target === 'string' ? $(target) : target
    if (!el) return
    el.textContent = ''
    if (node) el.appendChild(node)
  }

  /** headers: string[] | {t, cls}[]. rows: (string | {t, cls, html})[][] */
  function table(headers, rows) {
    const cell = (tag, c) => {
      const spec = typeof c === 'string' ? { t: c } : c || {}
      return h(tag, { class: spec.cls || '', html: spec.html, text: spec.html ? undefined : spec.t })
    }
    const thead = h('thead', null, h('tr', null, (headers || []).map((c) => cell('th', c))))
    const tbody = h('tbody', null, (rows || []).map((r) => h('tr', { class: r.cls || '' }, (r.cells || r).map((c) => cell('td', c)))))
    return h('table', null, headers ? [thead, tbody] : [tbody])
  }

  /**
   * Wires Reset / Step / Play buttons plus a counter to a step index.
   * ids: { reset, step, back, play, counter }. render(i) is called on every change.
   */
  function stepper(ids, getCount, render, opts) {
    const o = opts || {}
    let i = 0
    let timer = null
    const btn = (k) => (ids[k] ? $(ids[k]) : null)

    function draw() {
      const n = getCount()
      if (i > n) i = n
      render(i)
      const stepBtn = btn('step')
      const backBtn = btn('back')
      if (stepBtn) stepBtn.disabled = i >= n
      if (backBtn) backBtn.disabled = i <= 0
      const c = btn('counter')
      if (c) c.textContent = `step ${i} of ${n}`
      if (timer && i >= n) stop()
    }

    function go(next) {
      const n = getCount()
      i = Math.max(0, Math.min(next, n))
      draw()
    }

    function stop() {
      if (timer) clearInterval(timer)
      timer = null
      const p = btn('play')
      if (p) p.textContent = 'Play'
    }

    function play() {
      if (timer) return stop()
      if (i >= getCount()) i = 0
      timer = setInterval(() => go(i + 1), o.interval || 900)
      const p = btn('play')
      if (p) p.textContent = 'Pause'
      draw()
    }

    if (btn('step')) btn('step').addEventListener('click', () => { stop(); go(i + 1) })
    if (btn('back')) btn('back').addEventListener('click', () => { stop(); go(i - 1) })
    if (btn('reset')) btn('reset').addEventListener('click', () => { stop(); go(0) })
    if (btn('play')) btn('play').addEventListener('click', play)

    return { draw, go, stop, reset: () => { stop(); go(0) }, get index() { return i } }
  }

  /** Highlights <span class="ln" data-l="..."> lines inside a <pre>. */
  function highlight(preId, keys) {
    const pre = $(preId)
    if (!pre) return
    const want = new Set([].concat(keys || []))
    for (const ln of pre.querySelectorAll('.ln')) {
      ln.classList.toggle('on', want.has(ln.dataset.l))
    }
  }

  const fmt = (v) =>
    v === undefined ? 'undefined' : typeof v === 'string' ? JSON.stringify(v) : String(v)

  global.V = { $, h, s, svgRoot, mount, table, stepper, highlight, fmt, SVGNS }
})(window)
