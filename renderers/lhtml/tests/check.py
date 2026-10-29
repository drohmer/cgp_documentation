"""Self-check of the built site (dist/): screenshots, filter, search, links.

    ../.venv/bin/python tests/check.py [--no-shots]
"""
import functools
import http.server
import re
import socket
import sys
import threading
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent.parent
DIST = HERE / 'dist'
SHOTS = HERE / 'shots'
PAGES = {'home': 'index.html', 'camera': 'understand/camera-and-matrices/index.html',
         'howto': 'how-to/draw-a-mesh/index.html', 'vec3': 'reference/vec3/index.html',
         'vecN': 'reference/vecN/index.html', 'quaternion': 'reference/quaternion/index.html',
         'mat4': 'reference/mat4/index.html', 'index': 'reference/index.html'}


def serve():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(DIST))
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{port}/'


def check_links():
    bad = []
    for page in DIST.rglob('*.html'):
        if {'pagefind', 'assets', 'theme'} & set(page.relative_to(DIST).parts):
            continue
        text = page.read_text(encoding='utf-8')
        for url in re.findall(r'(?:href|src)="([^"#?]+)', text):
            if re.match(r'^[a-z]+:|^//', url):
                continue
            target = (page.parent / unquote(url)).resolve()
            if not target.exists():
                bad.append(f'{page.relative_to(DIST)} -> {url}')
    return bad


def main(shots=True):
    base = serve()
    errors = []
    bad = check_links()
    print(f'links: {len(bad)} broken', *bad[:20], sep='\n  ')
    SHOTS.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if shots:
            for scheme in ('light', 'dark'):
                ctx = browser.new_context(viewport={'width': 1440, 'height': 1000}, color_scheme=scheme)
                page = ctx.new_page()
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: m.type == 'error' and errors.append('console: ' + m.text))
                for name, path in PAGES.items():
                    page.goto(base + path)
                    page.wait_for_timeout(500)
                    page.screenshot(path=str(SHOTS / f'{name}-desktop-{scheme}.png'), full_page=True)
                    page.screenshot(path=str(SHOTS / f'view-{name}-desktop-{scheme}.png'))
                    if name == 'vec3':
                        page.goto(base + path + '#takes')
                        page.wait_for_timeout(300)
                        page.screenshot(path=str(SHOTS / f'view-vec3-takes-{scheme}.png'))
                ctx.close()
            ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                                      is_mobile=True, has_touch=True, color_scheme='light')
            page = ctx.new_page()
            for name, path in PAGES.items():
                page.goto(base + path)
                page.wait_for_timeout(500)
                page.screenshot(path=str(SHOTS / f'{name}-mobile.png'), full_page=True)
                page.screenshot(path=str(SHOTS / f'view-{name}-mobile.png'))
                width = page.evaluate('document.documentElement.scrollWidth')
                if width > 390:
                    errors.append(f'{name}: horizontal overflow at 390px ({width}px)')
            page.click('.nav-toggle')
            page.wait_for_timeout(300)
            page.screenshot(path=str(SHOTS / 'vec3-mobile-menu.png'))
            ctx.close()

        ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = ctx.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: m.type == 'error' and errors.append('console: ' + m.text))
        page.goto(base + PAGES['vec3'])
        total = page.locator('.fn-entry').count()
        page.fill('#fn-filter', 'cross')
        visible = page.locator('.fn-entry:visible').count()
        if page.locator('.fn-shared:visible').count():
            errors.append('filter "cross": shared names still visible')
        groups = page.locator('.fn-group:visible').count()
        names = page.eval_on_selector_all('.fn-entry:visible', 'els => els.map(e => e.dataset.name)')
        print(f'filter "cross": {visible}/{total} entries visible, {groups} groups visible: {names}')
        if not (0 < visible < total) or 'cross' not in names:
            errors.append('filter does not work')
        page.fill('#fn-filter', 'norm')
        shared = page.eval_on_selector_all('.fn-shared:visible', 'els => els.map(e => e.dataset.name)')
        full = page.eval_on_selector_all('.fn-entry:visible', 'els => els.map(e => e.dataset.name)')
        print(f'filter "norm": shared visible {shared}, entries visible {full}')
        if 'norm' not in shared:
            errors.append('filter "norm" does not show the shared norm')
        page.fill('#fn-filter', 'operator+')
        ops = page.locator('.fn-entry:visible').count()
        print(f'filter "operator+": {ops} entries visible (operators opened)')
        page.screenshot(path=str(SHOTS / 'vec3-filter.png'))
        page.fill('#fn-filter', '')

        for q in ('norm', 'dot', 'transpose', 'cross', 'uniform', 'perspective', 'mesh_primitive_sphere'):
            page.goto(base + PAGES['home'])
            page.fill('#search', q)
            try:
                page.wait_for_selector('.search-results .sr', timeout=5000)
            except Exception:
                errors.append(f'search "{q}": no result')
                continue
            res = page.eval_on_selector_all('.sr-item', 'els => els.map(e => e.getAttribute("href"))')
            pages = list(dict.fromkeys(r.split('#')[0] for r in res))
            print(f'search "{q}": {len(res)} links, pages: {pages}')
            if q in ('norm', 'dot') and '/reference/vecN/' not in pages[0]:
                errors.append(f'search "{q}": vecN is not first')
            if q == 'transpose' and '/reference/matN/' not in pages[0]:
                errors.append(f'search "{q}": matN is not first')
            want = {'norm': '/reference/vecN/', 'cross': '/reference/vec3/', 'uniform': '/understand/camera-and-matrices/',
                    'perspective': '/understand/camera-and-matrices/'}.get(q)
            if want and want not in pages:
                errors.append(f'search "{q}": {want} not in the results')
            if q == 'norm':
                page.screenshot(path=str(SHOTS / 'search-norm.png'))
        # follow a deep link of the search into the operators
        page.goto(base + PAGES['vec3'])
        anchor = page.eval_on_selector('details.fn-operators h4[id]', 'e => e.id')
        page.goto(base + PAGES['vec3'] + '#' + anchor)
        page.wait_for_timeout(300)
        opened = page.eval_on_selector('details.fn-operators', 'e => e.open')
        print(f'deep link into the operators opens them: {opened}')
        if not opened:
            errors.append('deep link into operators does not open them')
        # demo: lazy
        page.goto(base + PAGES['camera'])
        frames = page.locator('iframe').count()
        page.click('.demo-poster')
        page.wait_for_timeout(2500)
        print(f'demo: {frames} iframe before click, {page.locator("iframe.demo-frame").count()} after')
        page.locator('figure.demo').screenshot(path=str(SHOTS / 'demo-loaded.png'))
        browser.close()
    print('errors:', errors or 'none')
    return 1 if errors or bad else 0


if __name__ == '__main__':
    sys.exit(main('--no-shots' not in sys.argv))
