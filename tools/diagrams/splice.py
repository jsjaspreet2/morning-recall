"""Write a rendered board into a design page — idempotently.

The markdown is the source of truth for the site, so the finished SVG lives in
the .md file and this module is what puts it there. Every board carries a stable
`data-board` id, which is what makes a re-run a no-op: on the second and every
later build the board is found by that id and replaced in place, byte for byte
if nothing about its spec changed.

`section` and `after_heading` therefore only matter the first time a board is
introduced — they say where to put something that isn't in the page yet.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESIGNS = ROOT / 'src' / 'data' / 'designs'


def _block(bid, svg, caption):
    return (f'<div class="diagram" data-board="{bid}">\n{svg}\n</div>\n\n'
            f'<p class="diagram-cap">{caption}</p>')


def _found(bid):
    return re.compile(
        r'<div class="diagram" data-board="' + re.escape(bid) + r'">\n'
        r'[\s\S]*?\n</div>\n\n<p class="diagram-cap">[\s\S]*?</p>')


def place(page, bid, board, caption, *, section=None, nth=0, after_heading=None):
    """Put `board` into `page` under the id `bid`.

    section:       e.g. '## 6 ' — replace the nth fenced block inside that section,
                   which is how a board first displaces the ASCII art it supersedes.
    after_heading: e.g. '## 14 ' — insert directly beneath that heading.
    """
    path = DESIGNS / page
    text = path.read_text()
    block = _block(bid, board.svg(), caption)

    hit = _found(bid).search(text)
    if hit:
        path.write_text(text[:hit.start()] + block + text[hit.end():])
        return 'replaced'

    lines = text.split('\n')
    heads = [i for i, l in enumerate(lines) if l.startswith('## ')]

    if section is not None:
        start = next(i for i in heads if lines[i].startswith(section))
        end = next((i for i in heads if i > start), len(lines))
        fences = [i for i in range(start, end) if lines[i].startswith('```')]
        if len(fences) < 2 * nth + 2:
            raise SystemExit(
                f'{page}: no fenced block #{nth} left in "{section.strip()}" and no board '
                f'tagged data-board="{bid}". Nothing to replace — did the id change?')
        a, b = fences[2 * nth], fences[2 * nth + 1]
        out = lines[:a] + block.split('\n') + lines[b + 1:]
    elif after_heading is not None:
        start = next(i for i in heads if lines[i].startswith(after_heading))
        j = start + 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        out = lines[:start + 1] + [''] + block.split('\n') + lines[j - 1:]
    else:
        raise SystemExit(f'{page}: board "{bid}" is not in the page yet — '
                         'pass section= or after_heading= to say where it goes.')

    path.write_text('\n'.join(out))
    return 'inserted'
