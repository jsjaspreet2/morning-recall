"""Rebuild every board in every design page.

Idempotent: run it twice and the second run changes nothing, because each board
is found by its data-board id and replaced in place. `git diff` after a build is
therefore an honest answer to "did my edit do what I meant?".

    python3 tools/diagrams/build.py            # all pages
    python3 tools/diagrams/build.py cursor     # just these

Exits non-zero if any label is estimated to overflow its box or run off the
edge of the board, so a bad edit fails loudly instead of shipping clipped text.
"""
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

wanted = set(sys.argv[1:])
pages = sorted(HERE.joinpath('pages').glob('*.py'))
if wanted:
    pages = [p for p in pages if p.stem in wanted]
    missing = wanted - {p.stem for p in pages}
    if missing:
        raise SystemExit(f'no such page spec: {", ".join(sorted(missing))}')

problems = 0
counts = []
for path in pages:
    spec = importlib.util.spec_from_file_location(f'board_{path.stem}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    warn = getattr(module, 'WARN', [])
    boards = getattr(module, 'BOARDS', 0)
    problems += len(warn)
    print(f'{path.stem:16} {boards} board(s)  {"OK" if not warn else str(len(warn)) + " OVERFLOW"}')
    for line in warn:
        print(line)
    counts.append((path.stem, module))

# Element counts per board. A spec that builds several boards is one typo away
# from appending to the wrong one — `a.` where `a2.` was meant — which is silent
# and puts arrows on a diagram that never asked for them. Printing the counts
# makes that show up in a diff instead of in a screenshot three days later.
print()
for stem, module in counts:
    for name in dir(module):
        b = getattr(module, name)
        if hasattr(b, 'el') and hasattr(b, 'warn'):
            print(f'  {stem:16} {name:4} {len(b.el):3} elements')

print(f'\n{len(pages)} page(s) rebuilt.')
if problems:
    print(f'{problems} label(s) overflow. Shorten the text or widen the box.')
    sys.exit(1)
