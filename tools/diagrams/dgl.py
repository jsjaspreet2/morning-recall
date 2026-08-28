"""Authoring aid for the design-page whiteboard SVGs.

Boards are laid out on a 1000-unit viewBox. Nothing here emits colour or weight:
every element carries a dg-* class and src/index.css supplies the theme, which is
why one copy of the markup reads in light and dark. Arrowheads are explicit
triangles because <marker> defs do not reliably survive parse5 -> hast -> React.
"""
W = 1000

# Font sizes must match src/index.css. The width guard is only as honest as this
# table: check a dg-good-t title at dg-t's 12.5px and it reports overflow that
# will not happen.
FONT = {
    'dg-t': 12.5, 'dg-banner-t': 13.0, 'dg-good-t': 11.0, 'dg-warn-t': 11.0,
    'dg-s': 10.5, 'dg-lbl': 10.5, 'dg-lane': 10.5, 'dg-note': 11.0,
}
BOLD = {'dg-t', 'dg-banner-t', 'dg-good-t', 'dg-warn-t', 'dg-lane'}

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# Rough advance widths for the site's system sans, used only to catch a label
# that will overflow its box. Cheaper than rendering twenty boards to find out.
def width(text, fs=10.5, bold=False):
    return len(text) * fs * (0.55 if bold else 0.515)

class Board:
    def __init__(self, height, label):
        self.h = height
        self.label = label
        self.el = []
        self.warn = []

    def _(self, s):
        self.el.append('  ' + s)

    # ---- containers ------------------------------------------------------
    def banner(self, text, y=10, h=38):
        self._(f'<rect class="dg-banner" x="10" y="{y}" width="980" height="{h}" rx="9"></rect>')
        self._(f'<text class="dg-banner-t dg-c" x="500" y="{y + h/2 + 4.5:g}">{esc(text)}</text>')
        self._chk(text, 940, 13, True)

    def box(self, x, y, w, h, title, subs=(), cls='dg-box', tcls='dg-t', scls='dg-s', badge=None):
        self._(f'<rect class="{cls}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8"></rect>')
        self._label(x, y, w, h, title, subs, tcls, scls)
        if badge is not None:
            self.badge(x, y, badge)

    def _label(self, x, y, w, h, title, subs=(), tcls='dg-t', scls='dg-s'):
        cx = x + w / 2
        block = 13 + 16 * len(subs)
        # The width guard cannot see text spilling out of the *bottom* of a box,
        # which is what happens the moment a sub-line is added to a box that was
        # already full. Centred content fits exactly while block <= h - 2.
        if block > h - 2:
            self.warn.append(f'    TOO TALL {block} > {h - 2}: {title!r} with {len(subs)} sub-lines')
        top = y + (h - block) / 2 + 11
        if title:
            self._(f'<text class="{tcls} dg-c" x="{cx:g}" y="{top:g}">{esc(title)}</text>')
            self._chk(title, w, FONT.get(tcls, 12.5), tcls in BOLD)
        for i, s in enumerate(subs):
            self._(f'<text class="{scls} dg-c" x="{cx:g}" y="{top + 16 + 16*i:g}">{esc(s)}</text>')
            self._chk(s, w, FONT.get(scls, 10.5), scls in BOLD)

    # ---- architecture shapes ---------------------------------------------
    # A flow board draws steps. An architecture board draws *things you can
    # point at in production* — a service, a store, a queue — and the shape
    # carries the kind, so the reader knows what a box is before reading it.
    def cyl(self, x, y, w, h, title, subs=(), cls='dg-box', r=7):
        """A datastore. Anything with a cylinder is something that survives a restart."""
        top, bot = y + r, y + h - r
        self._(f'<path class="{cls}" d="M {x:g},{top:g} L {x:g},{bot:g} '
               f'A {w/2:g},{r} 0 0 0 {x+w:g},{bot:g} L {x+w:g},{top:g} '
               f'A {w/2:g},{r} 0 0 0 {x:g},{top:g} Z"></path>')
        self._(f'<path class="{cls}" d="M {x:g},{top:g} '
               f'A {w/2:g},{r} 0 0 0 {x+w:g},{top:g}" style="fill:none"></path>')
        self._label(x, y + r, w, h - r, title, subs)

    def queue(self, x, y, w, h, title, subs=(), cls='dg-box'):
        """A queue or log. The bars are the point: things wait here, in order."""
        self._(f'<rect class="{cls}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8"></rect>')
        for i in range(3):
            bx = x + 13 + 9 * i
            self._(f'<path class="dg-qbar" d="M {bx:g},{y+9:g} L {bx:g},{y+h-9:g}"></path>')
        self._label(x + 36, y, w - 36, h, title, subs)

    def group(self, x, y, w, h, label):
        """A tier or a trust boundary. Draw these first; they are the argument."""
        self._(f'<rect class="dg-group" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="12"></rect>')
        self._(f'<text class="dg-group-t" x="{x+16:g}" y="{y+22:g}">{esc(label)}</text>')

    def badge(self, cx, cy, n, r=9):
        self._(f'<circle class="dg-num" cx="{cx:g}" cy="{cy:g}" r="{r}"></circle>')
        self._(f'<text class="dg-num-t" x="{cx:g}" y="{cy + 3.4:g}">{n}</text>')

    # ---- connectors ------------------------------------------------------
    def arrow(self, *pts, label=None, lx=None, ly=None, lcls='dg-lbl dg-c'):
        pts = list(pts)
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** 0.5 or 1
        ux, uy = dx / L, dy / L
        bx, by = x2 - 8 * ux, y2 - 8 * uy
        px, py = -uy, ux
        self._(f'<path class="dg-line" d="M ' +
               ' L '.join(f'{x:g},{y:g}' for x, y in pts[:-1] + [(bx, by)]) + '"></path>')
        self._(f'<path class="dg-head" d="M {bx + 5*px:g},{by + 5*py:g} '
               f'L {bx - 5*px:g},{by - 5*py:g} L {x2:g},{y2:g} Z"></path>')
        if label:
            self._(f'<text class="{lcls}" x="{lx:g}" y="{ly:g}">{esc(label)}</text>')

    def line(self, *pts, cls='dg-line'):
        self._(f'<path class="{cls}" d="M ' + ' L '.join(f'{x:g},{y:g}' for x, y in pts) + '"></path>')

    def vdiv(self, x, y1, y2):
        self._(f'<path class="dg-div" d="M {x:g},{y1:g} L {x:g},{y2:g}"></path>')

    def hdiv(self, y, x1, x2):
        self._(f'<path class="dg-div" d="M {x1:g},{y:g} L {x2:g},{y:g}"></path>')

    # ---- text ------------------------------------------------------------
    def lane(self, x, y, text):
        self._(f'<text class="dg-lane" x="{x:g}" y="{y:g}">{esc(text)}</text>')

    def text(self, x, y, s, cls='dg-s'):
        self._(f'<text class="{cls}" x="{x:g}" y="{y:g}">{esc(s)}</text>')
        # left-anchored: it has the rest of the board to run into, and nothing
        # stops it running off the edge, so check against what is actually left
        self._chk(s, (W - 10 - x) + 14, FONT.get(cls.split()[0], 11))

    def ctext(self, cx, y, s, cls='dg-s'):
        self._(f'<text class="{cls} dg-c" x="{cx:g}" y="{y:g}">{esc(s)}</text>')
        self._chk(s, 2 * min(cx - 10, W - 10 - cx) + 14, FONT.get(cls.split()[0], 10.5))

    def ghost(self, x, y, w, h, heading, lines):
        self._(f'<rect class="dg-ghost" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8"></rect>')
        cx = x + w / 2
        self.ctext(cx, y + 24, heading, 'dg-lane')
        for i, s in enumerate(lines):
            self.ctext(cx, y + 45 + 17 * i, s)
            self._chk(s, w, 10.5)

    # ---- output ----------------------------------------------------------
    def _chk(self, s, w, fs, bold=False):
        est = width(s, fs, bold)
        if est > w - 14:
            self.warn.append(f'    OVERFLOW {est:.0f} > {w-14:.0f}: {s!r}')

    def svg(self):
        return (f'<svg viewBox="0 0 1000 {self.h}" role="img" aria-label="{esc(self.label)}">\n'
                + '\n'.join(self.el) + '\n</svg>')

    def block(self, caption):
        return ('<div class="diagram">\n' + self.svg() + '\n</div>\n\n'
                f'<p class="diagram-cap">{caption}</p>')
