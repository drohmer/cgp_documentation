#!/usr/bin/env python
"""Build prototype A of the CGP documentation (lhtml-site + Pagefind).

    ../.venv/bin/python build.py            # -> dist/

1. assemble _build/theme: the bundled docs theme + theme/ (the CGP overlay: cgp.css and
   cgp.js, loaded through the `docs` settings of configure.yaml);
2. assemble _build/src: ../content/*.md as pages (a/b.md -> a/b/index.md.j2),
   pages/, the content assets, and the reference pages generated from
   ../../build/api.json (scripts/gen_reference.py); write the deck;
3. lhtml-site -i configure.yaml;
4. Pagefind over dist/.
"""
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # renderers/lhtml -> documentation root
CONTENT = ROOT / 'content'
API = ROOT / 'build' / 'api.json'
BUILD = HERE / '_build'
BIN = Path(sys.executable).parent

sys.path.insert(0, str(HERE / 'scripts'))
sys.path.insert(0, str(HERE / 'plugins'))
import gen_reference  # noqa: E402
from cgp_content import has_math  # noqa: E402


def step(name, t0=[time.perf_counter()]):
    t = time.perf_counter()
    print(f'[{t - t0[0]:6.2f}s] {name}', flush=True)


def assemble_theme():
    import lhtml_site
    bundled = Path(lhtml_site.__file__).parent / 'themes' / 'docs'
    if not bundled.is_dir():
        sys.exit(f'lhtml-site has no docs theme ({bundled}): it needs a version with it')
    theme = BUILD / 'theme'
    shutil.copytree(bundled, theme)
    shutil.copytree(HERE / 'theme', theme, dirs_exist_ok=True)


def page_order(md):
    """The `order:` field of the front matter of a content page (1000 if absent)."""
    m = re.search(r'^order:\s*(\d+)\s*$', front_matter(md), re.M)
    return int(m.group(1)) if m else 1000


def front_matter(md):
    text = md.read_text(encoding='utf-8')
    return text.split('---', 2)[1] if text.startswith('---') else ''


def page_group(md):
    """The `group:` field of the front matter (sub-heading of the menu inside a section), or None."""
    m = re.search(r'^group:\s*(.+?)\s*$', front_matter(md), re.M)
    return m.group(1).strip('"\'') if m else None


def inherited_groups(section):
    """{page: group} for the pages of a section that has groups: a page without `group:` takes
    the group of the page before it (in `order`), with a warning, so that the menu groups stay
    contiguous. Same rule as renderers/starlight/src/lib/content-groups.mjs."""
    mds = sorted(CONTENT.glob(f'{section}/*.md'), key=lambda md: (page_order(md), md.stem))
    if not any(page_group(md) for md in mds):
        return {}
    out, last = {}, None
    for md in mds:
        g = page_group(md)
        if g is None:
            print(f'WARNING {md.relative_to(ROOT)}: no `group:` in the front matter, '
                  f'placed in the group of the previous page ({last!r})', flush=True)
            g = last
        out[md] = last = g
    return out


def sort_key(rel, groups):
    md = CONTENT / f'{rel}.md'
    g = groups.get(md)
    rank = min(page_order(m) for m, h in groups.items() if h == g) if g else 0
    return (rank, page_order(md), rel)


SECTION_INDEX = re.compile(r'<!--\s*section-index:\s*([\w-]+)\s*-->')


def section_index(section, groups):
    """Markdown list of the pages of a section, by group (same groups and order as the menu),
    each with its title and description, read from the front matter: the marker
    `<!-- section-index: how-to -->` of a content page is replaced by it, so the index cannot
    drift from the pages. Same output as renderers/starlight/src/plugins/cgp-markdown.mjs."""
    import yaml
    mds = sorted(CONTENT.glob(f'{section}/*.md'),
                 key=lambda md: sort_key(md.relative_to(CONTENT).as_posix()[:-3], groups))
    out, last = [], object()
    for md in mds:
        fm = yaml.safe_load(front_matter(md)) or {}
        g = groups.get(md)
        if g != last:
            if g:
                out.append(f'\n## {g}\n')
            last = g
        desc = str(fm.get('description') or '').strip()
        out.append(f'- [{fm.get("title") or md.stem}]({section}/{md.name})' + (f': {desc}' if desc else ''))
    return '\n'.join(out) + '\n'


def assemble_sources():
    src = BUILD / 'src'
    src.mkdir(parents=True)
    pages = []
    groups = {}
    for section in ('get-started', 'understand', 'how-to', 'examples'):
        groups.update(inherited_groups(section))
    for md in sorted(CONTENT.rglob('*.md')):
        rel = md.relative_to(CONTENT).as_posix()[:-3]          # understand/camera-and-matrices
        target = src / ('index.md.j2' if rel == 'index' else f'{rel}/index.md.j2')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(md, target)
        if groups.get(md) and not page_group(md):      # inherited group, written in the copy
            text = target.read_text(encoding='utf-8')
            target.write_text(text.replace('---\n', f'---\ngroup: {groups[md]}\n', 1), encoding='utf-8')
        text = target.read_text(encoding='utf-8')
        if has_math(text) and not re.search(r'^math:', text.split('---', 2)[1], re.M):
            text = text.replace('---\n', '---\nmath: true\n', 1)   # $x$ only: unseen by lhtml-site
            target.write_text(text, encoding='utf-8')
        if SECTION_INDEX.search(text):      # index of a section (content/how-to.md), from the front matter
            target.write_text(SECTION_INDEX.sub(lambda m: section_index(m.group(1), groups), text), encoding='utf-8')
        pages.append(rel)
    shutil.copytree(CONTENT / 'assets', src / 'assets')
    if (HERE / 'pages').exists():  # pages written only for this renderer
        shutil.copytree(HERE / 'pages', src, dirs_exist_ok=True)
    reference = gen_reference.main(API, src)
    # order of the site (menu and previous / next): home, then the sections; inside a section,
    # by group (groups ranked by the smallest `order` of their pages), then by `order`, then
    # by file name: the pages of a group are always contiguous
    order = ['index.html']
    for section in ('get-started', 'understand', 'how-to', 'examples'):
        order += [p for p in pages if p == section]      # index of the section (content/how-to.md) first
        order += sorted((p for p in pages if p.startswith(section + '/')), key=lambda p: sort_key(p, groups))
    order += reference
    (BUILD / 'deck.yaml').write_text('slides:\n' + ''.join(f'  - {p}\n' for p in order), encoding='utf-8')
    return len(order)


def main():
    t0 = time.perf_counter()
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir()
    assemble_theme()
    n = assemble_sources()
    step(f'sources assembled ({n} pages)')
    # CGP_BASE_URL (make deploy): the path of the site on its server, for the links of the 404
    # page; a copy of configure.yaml next to it (its paths are relative to its folder)
    config = HERE / 'configure.yaml'
    base_url = os.environ.get('CGP_BASE_URL')
    if base_url:
        text = re.sub(r"^base_url:.*$", f"base_url: '{base_url}'", config.read_text(encoding='utf-8'), flags=re.M)
        config = HERE / '.configure-deploy.yaml'
        config.write_text(text, encoding='utf-8')
    try:
        subprocess.run([str(BIN / 'lhtml-site'), '-i', str(config)], check=True, cwd=HERE)
    finally:
        if base_url:
            config.unlink()
    step(f'lhtml-site build done (base_url {base_url or "of configure.yaml"})')
    # the copy of the sources in the site is not part of the site
    for leftover in (HERE / 'dist').rglob('*.md.j2'):
        leftover.unlink()
    subprocess.run([sys.executable, '-m', 'pagefind', '--site', str(HERE / 'dist'), '--quiet'], check=True)
    step('pagefind index done')
    print(f'Built dist/ in {time.perf_counter() - t0:.2f}s')


if __name__ == '__main__':
    main()
