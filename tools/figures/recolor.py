"""Apply the palette (palette.py) to hand-drawn SVG figures.

    python3 tools/figures/recolor.py content/assets/foo.svg [...]   # rewrite in place
    python3 tools/figures/recolor.py --check content/assets/*.svg   # list, do not write

Two mechanical changes, nothing else:
  1. text colors: a fill of a <text>/<tspan> element, or of a CSS rule that only styles text,
     goes through TEXT_MAP (mid tone -> darker text tone of the same concept, >= 4.5:1);
  2. near-duplicate line colors go through LINE_MAP everywhere.
Semantic changes (a box that changes concept) are made by hand in the SVG.
A CSS class used both on text and on shapes is reported and left alone.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import TEXT_MAP, LINE_MAP  # noqa: E402

HEX = re.compile(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b')
TEXT_TAGS = {'text', 'tspan'}


def map_hex(s, table):
    return HEX.sub(lambda m: table.get(m.group(0).lower(), m.group(0)), s)


def map_fill_decl(decls, table):
    """Map the value of fill: in a CSS declaration list (not stroke, not stop-color)."""
    return re.sub(r'(?<![-\w])(fill\s*:\s*)(#[0-9a-fA-F]{3,6})\b',
                  lambda m: m.group(1) + table.get(m.group(2).lower(), m.group(2)), decls)


def recolor(src):
    warnings = []
    # class -> set of tags using it
    usage = {}
    for m in re.finditer(r'<(\w+)\b([^>]*)>', src):
        cm = re.search(r'\bclass="([^"]*)"', m.group(2))
        if cm:
            for c in cm.group(1).split():
                usage.setdefault(c, set()).add(m.group(1))

    def is_text_rule(selector):
        sels = [s.strip() for s in selector.split(',')]
        for s in sels:
            last = s.split()[-1] if s.split() else s
            if last in TEXT_TAGS:
                continue
            classes = re.findall(r'\.([\w-]+)', last)
            if not classes:
                return False
            tags = set().union(*(usage.get(c, set()) for c in classes))
            if not tags:
                continue                       # unused class: harmless either way
            if tags <= TEXT_TAGS:
                continue
            if tags & TEXT_TAGS:
                warnings.append(f'class {last} used on text and on {sorted(tags - TEXT_TAGS)}')
            return False
        return True

    def fix_style(m):
        css = m.group(2)
        css = re.sub(r'([^{}]+)\{([^{}]*)\}',
                     lambda r: r.group(1) + '{' + (map_fill_decl(r.group(2), TEXT_MAP)
                                                   if is_text_rule(r.group(1)) else r.group(2)) + '}',
                     css)
        return m.group(1) + css + m.group(3)

    out = re.sub(r'(<style[^>]*>)(.*?)(</style>)', fix_style, src, flags=re.S)

    def fix_elem(m):
        tag, attrs = m.group(1), m.group(2)
        if tag not in TEXT_TAGS:
            return m.group(0)
        attrs = re.sub(r'(\bfill=")([^"]*)(")', lambda a: a.group(1) + map_hex(a.group(2), TEXT_MAP) + a.group(3), attrs)
        attrs = re.sub(r'(\bstyle=")([^"]*)(")', lambda a: a.group(1) + map_fill_decl(a.group(2), TEXT_MAP) + a.group(3), attrs)
        return '<' + tag + attrs + '>'

    out = re.sub(r'<(\w+)\b([^>]*)>', fix_elem, out)
    out = map_hex(out, LINE_MAP)
    return out, warnings


if __name__ == '__main__':
    args = sys.argv[1:]
    check = '--check' in args
    for path in [a for a in args if a != '--check']:
        src = open(path).read()
        out, warnings = recolor(src)
        for w in warnings:
            print(f'{path}: warning: {w}')
        if out != src:
            print(f'{path}: {"would change" if check else "changed"}')
            if not check:
                open(path, 'w').write(out)
