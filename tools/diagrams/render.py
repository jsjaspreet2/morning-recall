"""Rasterise one board so a human (or a model with eyes) can actually look at it.

The board in the page has no colours of its own — src/index.css supplies them —
so this inlines the light-theme token values and hands the result to Quick Look.
Every layout bug found so far was found here and not by any automated check.

    python3 tools/diagrams/render.py design-cursor.md 0 /tmp/out
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splice import DESIGNS  # noqa: E402

STYLE = """<style>
text{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif}
.dg-box{fill:#fff;stroke:#c4c4cc;stroke-width:1.25}
.dg-banner{fill:#eef2ff;stroke:#c7d2fe;stroke-width:1.25}
.dg-good{fill:#ecfdf5;stroke:#6ee7b7;stroke-width:1.25}
.dg-warn{fill:#fff7ed;stroke:#fdba74;stroke-width:1.25}
.dg-ghost{fill:none;stroke:#c4c4cc;stroke-width:1.25;stroke-dasharray:5 5}
.dg-line{fill:none;stroke:#9a9aa4;stroke-width:1.5}
.dg-head{fill:#9a9aa4;stroke:none}
.dg-div{fill:none;stroke:#c4c4cc;stroke-width:1;stroke-dasharray:4 5}
.dg-t{fill:#27272a;font-size:12.5px;font-weight:600}
.dg-s{fill:#71717a;font-size:10.5px}
.dg-lbl{fill:#71717a;font-size:10.5px;font-style:italic}
.dg-lane{fill:#71717a;font-size:10.5px;font-weight:700;letter-spacing:.09em}
.dg-banner-t{fill:#3730a3;font-size:13px;font-weight:650}
.dg-good-t{fill:#065f46;font-size:11px;font-weight:600}
.dg-warn-t{fill:#9a3412;font-size:11px;font-weight:600}
.dg-note{fill:#9a3412;font-size:11px}
.dg-qbar{fill:none;stroke:#c4c4cc;stroke-width:1.25}
.dg-group{fill:none;stroke:#c4c4cc;stroke-width:1.25;stroke-dasharray:6 5}
.dg-group-t{fill:#71717a;font-size:10.5px;font-weight:700;letter-spacing:.09em}
.dg-num{fill:#c7d2fe;stroke:none}
.dg-num-t{fill:#3730a3;font-size:9.5px;font-weight:700;text-anchor:middle}
.dg-c{text-anchor:middle}
</style>"""


def render(page, index, out_dir):
    svgs = re.findall(r'<svg viewBox[\s\S]*?</svg>', (DESIGNS / page).read_text())
    svg = svgs[index].replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    cut = svg.index('>') + 1
    svg = svg[:cut] + '<rect width="100%" height="100%" fill="#f6f8fa"/>' + STYLE + svg[cut:]
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, '_board.svg')
    with open(tmp, 'w') as fh:
        fh.write(svg)
    subprocess.run(['qlmanage', '-t', '-s', '1500', '-o', out_dir, tmp], capture_output=True)
    return os.path.join(out_dir, '_board.svg.png')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit('usage: render.py <design-page.md> <board index> [out dir]')
    print(render(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else '.'))
