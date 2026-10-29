#!/usr/bin/env python3
"""
End-to-end comparison tests of the documentation prototypes, with Playwright.

For each prototype described in tests/protos.json:
  - serve its output directory on a local port;
  - screenshots of the main pages (desktop light, desktop dark, mobile 390px) -> tests/out/<proto>/;
  - search queries (the audit questions) typed in the search UI: check expected page in results;
  - vec3 filter: typing "norm" leaves only matching entries; rotation_transform filter
    matches the methods ("from_axis");
  - inline code links of the guides (.code-ref): every target page and anchor exists;
  - every function is anchored by its model id on its home page (same link on both sites);
  - internal links of the main pages: no 404;
  - links with a #fragment in the content pages (glossary entries, sections): the target page
    has this id; content pages link to the glossary; heading ids identical on both sites;
  - figures are at most FIGURE_MAX_SCALE times their intrinsic width (text size), centered;
  - figures (content and reference pages): the image is wrapped in a link to an existing file
    (opens full size on a phone); a click opens the lightbox;
  - How-to sidebar: the groups (front matter `group:`) and their pages, in the order of the
    content, and previous / next consistent with it; the mobile menu shows the current page;
  - methods of one name are one entry (hierarchy_mesh_drawable::add: 3 signatures, 3 anchors);
  - the How-to index lists every how-to page, by group, as the sidebar; how-to pages have a
    breadcrumb How-to > group > page above the title, ignored by the search;
  - no console error.

Usage:  .venv/bin/python tests/test_protos.py [proto ...]
"""

import functools
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import time
import urllib.parse

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CONFIG = json.load(open(os.path.join(HERE, "protos.json"), encoding="utf-8"))

# (query, substring expected in the URL (lowercase), maximal rank among distinct pages)
SEARCH_CASES = [
    ("norm", "reference/vecn", 1),        # generic functions are indexed on the family page only
    ("dot", "reference/vecn", 2),
    ("transpose", "reference/matn", 2),
    ("cross", "reference/vec3", 1),
    ("uniform", "understand/shaders-and-uniforms", 3),   # the guide, after the reference of uniform_generic_structure
    ("shadow", "how-to/cast-shadows", 2),          # after the example examples/shadow-mapping
    ("skybox", "how-to/add-a-skybox", 2),
    ("perspective", "camera-and-matrices", 5),
    ("mesh_drawable", "reference/mesh_drawable", 1),
    ("draw a mesh", "draw-a-mesh", 3),
    ("rand_uniform", "reference/functions/random-noise", 1),   # function on no type page
    ("timer_interval", "reference/timer_interval", 1),
    # exact method names (expert review): the page of the type that declares the method
    ("update_wrap", "reference/opengl_texture_image_structure", 3),
    ("update_supplementary_data_on_gpu", "reference/mesh_drawable", 3),
    ("load_and_initialize_texture_2d_on_gpu", "reference/opengl_texture_image_structure", 3),
    ("from_vector_transform", "reference/rotation_transform", 3),
    ("update_local_to_global_coordinates", "reference/hierarchy_mesh_drawable", 3),
    # free functions in full on their home page only (structure review F9, expert review 5):
    # the camera / vec3 pages that only take them no longer outrank the guide or the home page
    ("picking", "how-to/select-and-drag-with-the-mouse", 3),   # the recipe moved out of interaction.md
    ("wireframe", "how-to/display-the-wireframe", 1),   # was: uniform_generic_structure 1st
    ("mesh_primitive_cylinder", "reference/mesh", 1),
    ("color of a shape", "how-to/change-the-color", 1),
    ("Error cannot access the following file path", "get-started/troubleshooting", 1),
    ("segmentation fault", "get-started/troubleshooting", 1),
    ("bounding box", "reference/bounding_box", 1),
]


# Function names: the first sub-result of the top page must be the exact function
# (norm before normalize), not a longer name sharing the prefix.
EXACT_FIRST = {"norm", "dot", "transpose", "cross"}

# Pages are loaded up to the "load" event (scripts run, stylesheets and eager images loaded):
# "networkidle" waits 500 ms more on every page. A screenshot also waits for the fonts and the
# images (ready() below).
LOAD = "load"


def ready(page):
    """Wait for the fonts and every image of the page (lazy ones included) before a screenshot."""
    page.evaluate("""async () => {
        await document.fonts.ready;
        document.querySelectorAll('img').forEach(e => { e.loading = 'eager'; });
        await Promise.all([...document.images].map(e => e.complete ? 0 : new Promise(r => { e.onload = e.onerror = r; })));
    }""")


def search_links(page, cfg, query):
    """Type the query in the search box of the open page and return the result links in visual
    order (a renderer may reorder them with CSS), once the list has stopped changing (Pagefind
    loads the fragments of the results one after the other). The box is emptied first, so that
    the results of the previous query are gone."""
    page.fill(cfg["search_input"], "")
    page.wait_for_function("(sel) => !document.querySelector(sel)", arg=cfg["search_result_link"], timeout=5000)
    page.fill(cfg["search_input"], query)
    try:
        page.wait_for_selector(cfg["search_result_link"], timeout=5000)
    except Exception:
        return []
    links, stable, t0 = None, 0, time.time()
    while stable < 2 and time.time() - t0 < 5:     # unchanged twice in a row, 150 ms apart
        page.wait_for_timeout(150)
        now = page.eval_on_selector_all(cfg["search_result_link"], "els => els.map(e => [e.href, e.getBoundingClientRect().top]).sort((a, b) => a[1] - b[1]).map(x => x[0])")
        stable = stable + 1 if now == links else 0
        links = now
    return links


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    handler = functools.partial(Quiet, directory=directory)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def check_code_links(dist, broken):
    """Every <a class="code-ref"> of the content pages points to an existing page and anchor.
    Static check of the built files. Returns the number of links."""
    import re
    ids_of, n = {}, 0
    for dirpath, _, files in os.walk(dist):
        rel = os.path.relpath(dirpath, dist).replace(os.sep, "/")
        if rel.startswith(("reference", "pagefind", "_astro", "assets", "demos")):
            continue
        for fname in files:
            if not fname.endswith(".html"):
                continue
            text = open(os.path.join(dirpath, fname), encoding="utf-8").read()
            for tag in re.findall(r'<a [^>]*class="code-ref"[^>]*>', text):
                n += 1
                href = re.search(r'href="([^"]+)"', tag).group(1).replace("&amp;", "&")
                url, _, frag = href.partition("#")
                target = os.path.join(dist, url.lstrip("/")) if url.startswith("/") else \
                    os.path.normpath(os.path.join(dirpath, url))
                if os.path.isdir(target):
                    target = os.path.join(target, "index.html")
                if target not in ids_of:
                    ids_of[target] = (set(re.findall(r'\sid="([^"]+)"', open(target, encoding="utf-8").read()))
                                      if os.path.exists(target) else None)
                if ids_of[target] is None or (frag and frag not in ids_of[target]):
                    broken.append(f"{rel}/{fname}: code link {href}")
    if n == 0:
        broken.append("no inline code link (.code-ref) in the content pages")
    return n


def check_code_images(broken):
    """Each code block of the home page shown next to its image (<!-- code-image: ... -->) is the
    code that drew the image: every line of it (comments and blank lines aside) is in a region
    `// snippet: ... // end` of demos/first-look/scene.cpp, the demo the images are captured from
    (tools/figures/first_look_captures.py). Returns the number of blocks."""
    import re
    page = open(os.path.join(ROOT, "content", "index.md"), encoding="utf-8").read()
    demo = open(os.path.join(ROOT, "demos", "first-look", "scene.cpp"), encoding="utf-8").read()
    demo_lines = {l.strip() for region in re.findall(r"// snippet:[^\n]*\n(.*?)// end", demo, re.S)
                  for l in region.splitlines()}
    blocks = re.findall(r"<!--\s*code-image:[^>]*-->\s*\n```\w*\n(.*?)\n```", page, re.S)
    for block in blocks:
        for line in block.splitlines():
            code = line.strip()
            if code and not code.startswith("//") and code not in demo_lines:
                broken.append(f"index.md: code-image line not in demos/first-look/scene.cpp: {code}")
    if not blocks:
        broken.append("index.md: no code-image block")
    return len(blocks)


def check_math(dist, broken):
    """The formulas of the content pages (written $x$ or $$x$$) are rendered: one KaTeX element
    per formula of the source, and no TeX delimiter left in the text. Static check of the built
    files. Returns the number of formulas."""
    import re
    content = os.path.join(ROOT, "content")
    code = re.compile(r"```.*?```|`[^`\n]*`", re.S)
    formula = re.compile(r"\$\$.+?\$\$|(?<![\\$])\$(?!\s)[^$\n]+?(?<!\s)\$(?!\$)", re.S)
    total = 0
    for dirpath, _, files in os.walk(content):
        for fname in files:
            if not fname.endswith(".md") or "assets" in dirpath:
                continue
            md = os.path.join(dirpath, fname)
            n = len(formula.findall(code.sub("", open(md, encoding="utf-8").read())))
            if not n:
                continue
            total += n
            rel = os.path.relpath(md, content)[:-3]
            page = os.path.join(dist, "index.html" if rel == "index" else os.path.join(rel, "index.html"))
            html = open(page, encoding="utf-8").read()
            text = re.sub(r"<(pre|code|script|style)\b.*?</\1>", "", html, flags=re.S)
            rendered = len(re.findall(r'class="katex"', html))
            if rendered < n or "\\(" in text or "\\[" in text:
                broken.append(f"{rel}: {n} formulas in the source, {rendered} rendered by KaTeX")
    return total


def check_home_anchors(dist, broken):
    """Every function of api.json is anchored by its model id on its home page (type page or
    group page): /reference/<home>/#<id> is the same link on both sites. Returns the count."""
    import re
    api = json.load(open(os.path.join(ROOT, "build", "api.json"), encoding="utf-8"))
    ids_of, n = {}, 0
    for f in api["functions"]:
        h = f.get("home")
        if not h:
            continue
        if h["type"]:
            d = os.path.join(dist, "reference", h["type"])
            if not os.path.isdir(d):
                d = os.path.join(dist, "reference", h["type"].lower())
        else:
            d = os.path.join(dist, "reference", "functions", h["group"])
        page = os.path.join(d, "index.html")
        if page not in ids_of:
            ids_of[page] = (set(re.findall(r'\sid="([^"]+)"', open(page, encoding="utf-8").read()))
                            if os.path.exists(page) else set())
        n += 1
        if f["id"] not in ids_of[page]:
            broken.append(f"{os.path.relpath(page, dist)}: no anchor #{f['id']} ({f['key']})")
    return n


CONTENT_SKIP = ("reference", "pagefind", "_astro", "assets", "demos", "theme", "sitemap")


def _content_pages(dist):
    """(relative dir, path) of the HTML pages made from content/*.md (not the reference)."""
    for dirpath, _, files in os.walk(dist):
        rel = os.path.relpath(dirpath, dist).replace(os.sep, "/")
        if rel.startswith(CONTENT_SKIP):
            continue
        for fname in files:
            if fname.endswith(".html") and fname != "404.html":
                yield rel, os.path.join(dirpath, fname)


def _resolve(dist, dirpath, url):
    target = os.path.join(dist, url.lstrip("/")) if url.startswith("/") else os.path.normpath(os.path.join(dirpath, url))
    if os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return target


def _main_html(text):
    """The <main> element of a page (links of the header, menu and footer excluded)."""
    import re
    m = re.search(r"<main\b.*?</main>", text, re.S)
    return m.group(0) if m else text


def check_fragment_links(dist, broken):
    """Every link with a #fragment in the <main> of a content page (glossary entries, sections of
    another page, same-page anchors) points to an existing page with this id. Returns
    (number of links, number of links to the glossary)."""
    import re
    ids_of, n, n_glossary = {}, 0, 0
    for rel, path in _content_pages(dist):
        text = open(path, encoding="utf-8").read()
        for href in re.findall(r'<a [^>]*?href="([^"]*#[^"]+)"', _main_html(text)):
            href = href.replace("&amp;", "&")
            url, _, frag = href.partition("#")
            if re.match(r"^[a-z]+:", url):
                continue
            target = _resolve(dist, os.path.dirname(path), url) if url else path
            if not target.startswith(os.path.abspath(dist)) and not os.path.abspath(target).startswith(os.path.abspath(dist)):
                continue
            if target not in ids_of:
                ids_of[target] = (set(re.findall(r'\sid="([^"]+)"', open(target, encoding="utf-8").read()))
                                  if os.path.exists(target) else None)
            n += 1
            n_glossary += "glossary" in url
            if ids_of[target] is None or urllib.parse.unquote(frag) not in ids_of[target]:
                broken.append(f"{rel}: link {href} (no such page or id)")
    if n_glossary < 20:
        broken.append(f"only {n_glossary} links to glossary entries in the content pages (expected >= 20)")
    return n, n_glossary


def heading_ids(dist):
    """{content page: [ids of its h2/h3 headings]} of a built site."""
    import re
    out = {}
    for rel, path in _content_pages(dist):
        main = _main_html(open(path, encoding="utf-8").read())
        out[rel.strip("./")] = re.findall(r'<h[23][^>]*\sid="([^"]+)"', main)
    return out


def check_figure_links(dist, broken):
    """Every figure of a page (content figures and reference figures) wraps its image in a link
    a.figure-zoom to an existing file of the site. Returns the number of figures."""
    import re
    n = 0
    for dirpath, _, files in os.walk(dist):
        rel = os.path.relpath(dirpath, dist).replace(os.sep, "/")
        if rel.startswith(("pagefind", "_astro", "assets", "demos", "theme")):
            continue
        for fname in files:
            if not fname.endswith(".html"):
                continue
            text = open(os.path.join(dirpath, fname), encoding="utf-8").read()
            for fig in re.findall(r'<figure class="(?:figure|cgp-figure)"[^>]*>.*?</figure>', text, re.S):
                n += 1
                m = re.search(r'<a class="figure-zoom" href="([^"]+)"[^>]*>\s*<img ', fig)
                if not m:
                    broken.append(f"{rel}/{fname}: figure without a full-size link")
                    continue
                target = _resolve(dist, dirpath, urllib.parse.unquote(m.group(1)))
                if not os.path.isfile(target):
                    broken.append(f"{rel}/{fname}: figure link {m.group(1)} -> missing file")
    if n == 0:
        broken.append("no figure found")
    return n


# A figure is shown at most at its intrinsic width (SVG width / viewBox) times this factor:
# the 700 px drawings have 13-15 px text, so their text never exceeds about 16 px on screen,
# whatever the width of the file (illustration review C1: 470 px files stretched to 736 px had
# 21-29 px text). Same factor as --figure-scale / --cgp-figure-scale in the site CSS (1), plus
# a margin.
FIGURE_MAX_SCALE = 1.05
FIGURE_SIZE_JS = """els => els.map(img => {
    const cs = getComputedStyle(img), r = img.getBoundingClientRect(), f = img.closest('figure').getBoundingClientRect();
    const pad = ['paddingLeft', 'paddingRight', 'borderLeftWidth', 'borderRightWidth'].reduce((a, k) => a + parseFloat(cs[k]), 0);
    return {src: img.getAttribute('src'), natural: img.naturalWidth, shown: r.width - pad,
            gap: Math.abs((r.left - f.left) - (f.right - r.right)), figw: cs.getPropertyValue('--fig-w').trim()};
})"""


def check_figure_size(page, base, cfg, res):
    """Every figure of the given pages (desktop, 1400 px) is at most FIGURE_MAX_SCALE times its
    intrinsic width, carries --fig-w (set by the build) and is centered. Returns 'N figures ok'."""
    n, before = 0, len(res["broken_links"])
    paths = list(cfg["figure_pages"]) + [cfg["pages"]["vecN"], cfg["pages"]["rotation"]]
    for path in paths:
        page.goto(base + path, wait_until=LOAD)
        page.eval_on_selector_all("figure img", "els => els.forEach(e => { e.loading = 'eager'; })")
        page.wait_for_function("[...document.querySelectorAll('figure img')].every(e => e.complete)", timeout=5000)
        figs = page.eval_on_selector_all("figure a.figure-zoom img", FIGURE_SIZE_JS)
        if not figs:
            res["broken_links"].append(f"{path}: no figure (figure size check)")
        for f in figs:
            n += 1
            name = f"{path}: figure {f['src'].rsplit('/', 1)[-1]}"
            if not f["figw"]:
                res["broken_links"].append(f"{name}: no --fig-w (intrinsic width not set by the build)")
            if f["natural"] and f["shown"] > f["natural"] * FIGURE_MAX_SCALE + 1:
                res["broken_links"].append(f"{name}: shown {f['shown']:.0f} px wide for an intrinsic width of "
                                           f"{f['natural']} px (text enlarged {f['shown'] / f['natural']:.2f} x)")
            if f["gap"] > 2:
                res["broken_links"].append(f"{name}: not centered ({f['gap']:.0f} px)")
    bad = len(res["broken_links"]) - before
    return f"{n} figures ok" if not bad else f"{n} figures, {bad} problem(s) (see broken links)"


def expected_howto_groups():
    """[(group, [slug...])] of content/how-to from the front matter: same rules as the renderers
    (a page without `group:` takes the group of the previous page; groups ranked by their
    smallest `order`, pages by `order` then name)."""
    import re
    pages = []
    for f in sorted(os.listdir(os.path.join(ROOT, "content", "how-to"))):
        if not f.endswith(".md"):
            continue
        fm = open(os.path.join(ROOT, "content", "how-to", f), encoding="utf-8").read().split("---", 2)[1]
        order = re.search(r"^order:\s*(\d+)", fm, re.M)
        group = re.search(r"^group:\s*(.+?)\s*$", fm, re.M)
        pages.append([int(order.group(1)) if order else 1000, f[:-3], group.group(1) if group else None])
    pages.sort()
    last = None
    for p in pages:
        p[2] = p[2] or last
        last = p[2]
    rank = {}
    for o, _, g in pages:
        rank[g] = min(rank.get(g, o), o)
    pages.sort(key=lambda p: (rank[p[2]], p[0], p[1]))
    groups = []
    for _, slug, g in pages:
        if not groups or groups[-1][0] != g:
            groups.append((g, []))
        groups[-1][1].append(slug)
    return groups


def _howto_slug(href):
    import re
    m = re.search(r"how-to/([\w-]+)", href or "")
    return m.group(1) if m else href


def check_howto_sidebar(page, base, cfg, res):
    """The How-to groups of the sidebar and their pages match the content, previous / next
    follows the same order across the groups. Appends to res["broken_links"]; returns a summary."""
    expected = expected_howto_groups()
    url = base + cfg["pages"]["howto"]
    page.goto(url, wait_until=LOAD)
    # groups of the How-to section only (the Examples section has groups too)
    shown = [(g, [_howto_slug(h) for h in hrefs]) for g, hrefs in page.evaluate(cfg["howto_groups_js"])
             if all("/how-to/" in h for h in hrefs)]
    if shown != [(g, s) for g, s in expected]:
        res["broken_links"].append(f"How-to sidebar groups differ from the content: shown {shown}, expected {expected}")
    # previous / next at the border of two groups: first page of the 2nd group
    first, prev_slug, next_slug = expected[1][1][0], expected[0][1][-1], (expected[1][1] + expected[2][1])[1]
    page.goto(base + cfg["pages"]["howto"].replace("draw-a-mesh", first), wait_until=LOAD)
    prev, nxt = [_howto_slug(h) for h in page.evaluate(cfg["pager_js"])]
    if (prev, nxt) != (prev_slug, next_slug):
        res["broken_links"].append(f"previous / next of how-to/{first}: {prev}, {nxt}; expected {prev_slug}, {next_slug}")
    return f"{len(shown)} groups, {sum(len(s) for _, s in shown)} pages"


def check_method_groups(page, base, cfg, res):
    """Methods of the same name are one entry: hierarchy_mesh_drawable::add (3 overloads) is a
    single .member-row / .fn-entry holding the 3 signatures, each anchored by its model id."""
    api = json.load(open(os.path.join(ROOT, "build", "api.json"), encoding="utf-8"))
    ids = [m["id"] for m in api["types"]["hierarchy_mesh_drawable"]["struct"]["methods"] if m["name"] == "add"]
    page.goto(base + cfg["pages"]["hierarchy"], wait_until=LOAD)
    got = page.evaluate("""(ids) => {
        const entries = [...document.querySelectorAll('.member-row, .fn-entry')].filter(e => e.dataset.name === 'add');
        const e = entries[0];
        return {n: entries.length,
                ids: e ? ids.filter(i => e.id === i || !!e.querySelector('[id="' + i + '"]')) : [],
                sigs: e ? (e.textContent.match(/add\\(/g) || []).length : 0};
    }""", ids)
    ok = len(ids) == 3 and got["n"] == 1 and len(got["ids"]) == 3 and got["sigs"] == 3
    if not ok:
        res["broken_links"].append(f"hierarchy_mesh_drawable::add is not one entry with 3 anchored signatures: {got}")
    return f"add: {got['n']} entry, {got['sigs']} signatures, {len(got['ids'])}/3 anchors"


def check_howto_index(page, base, cfg, res):
    """The How-to index page lists every how-to page, under the same groups and in the same
    order as the sidebar (both come from the front matter)."""
    expected = expected_howto_groups()
    page.goto(base + cfg["pages"]["howto_index"], wait_until=LOAD)
    shown = page.evaluate("""() => [...document.querySelectorAll('main h2')].filter(h => h.id && !h.id.startsWith('starlight__')).map(h => {
        let n = (h.closest('.sl-heading-wrapper') || h).nextElementSibling;
        while (n && n.tagName !== 'UL' && !/^H[12]$/.test(n.tagName) && !n.classList.contains('sl-heading-wrapper')) n = n.nextElementSibling;
        return [h.textContent.replace(/#\s*$/, '').trim(), n && n.tagName === 'UL' ? [...n.querySelectorAll(':scope > li > p > a, :scope > li > a')].map(a => a.href) : []];
    })""")
    shown = [(g, [_howto_slug(h) for h in hrefs]) for g, hrefs in shown]
    if shown != [(g, s) for g, s in expected]:
        res["broken_links"].append(f"How-to index differs from the content: shown {shown}, expected {expected}")
    # every link of the list leads to an existing page
    for _, slugs in shown:
        for s in slugs:
            r = page.request.get(base + cfg["pages"]["howto"].replace("draw-a-mesh", s))
            if r.status >= 400:
                res["broken_links"].append(f"How-to index -> {s} ({r.status})")
    return f"{len(shown)} groups, {sum(len(s) for _, s in shown)} pages"


def check_not_found(page, base, cfg, res):
    """dist/404.html, served as a host does for an unknown URL at any depth: its styles,
    scripts and links load (they start at the root of the server), and it links to the site
    (menu or content)."""
    body = open(os.path.join(ROOT, cfg["dist"], "404.html"), encoding="utf-8").read()
    url = base + "/old/doc/vec3.html"
    failed = []
    page.on("response", lambda r: r.status >= 400 and r.url != url and failed.append(f"{r.status} {r.url}"))
    page.route(url, lambda route: route.fulfill(status=404, content_type="text/html", body=body))
    page.goto(url, wait_until=LOAD)
    page.wait_for_timeout(300)
    links = page.evaluate("[...document.querySelectorAll('a')].map(a => a.href)")
    page.unroute(url)
    if failed:
        res["broken_links"].append(f"404 page at a deep URL: failed requests {failed[:3]}")
    if not any(h.rstrip("/").endswith(("/index.html", "/how-to", "/reference")) or h == base + "/" for h in links):
        res["broken_links"].append(f"404 page at a deep URL: no link to the site ({links[:5]})")
    return f"{len(links)} links"


def check_discovery(page, base, cfg, res):
    """lhtml: sitemap.xml lists every page of the site, each page has a canonical URL and its
    favicon loads, llms.txt links every page of the sitemap and llms-full.txt holds the guides
    and the reference (renderers/lhtml/scripts/gen_discovery.py)."""
    dist = os.path.join(ROOT, cfg["dist"])
    site = "https://graphicscomputing.fr/cgp/"
    locs = re.findall(r"<loc>(.*?)</loc>", open(os.path.join(dist, "sitemap.xml"), encoding="utf-8").read())
    pages = set()
    for d, _, files in os.walk(dist):
        rel = os.path.relpath(d, dist).replace(os.sep, "/")
        if "index.html" in files and rel.split("/")[0] not in ("assets", "pagefind", "theme"):
            pages.add(site + ("" if rel == "." else rel + "/"))
    for p in sorted(pages - set(locs))[:5]:
        res["broken_links"].append(f"sitemap.xml: page missing {p}")
    llms = open(os.path.join(dist, "llms.txt"), encoding="utf-8").read()
    for p in sorted(u for u in locs if f"({u})" not in llms)[:5]:
        res["broken_links"].append(f"llms.txt: page missing {p}")
    full = open(os.path.join(dist, "llms-full.txt"), encoding="utf-8").read()
    for needle in ("Page: Add a skybox", "## vec3", "`T norm(numarray_stack<T,N> const& v)`"):
        if needle not in full:
            res["broken_links"].append(f"llms-full.txt: no {needle!r}")
    page.goto(base + cfg["pages"]["howto"], wait_until=LOAD)
    canonical = page.evaluate("document.querySelector('link[rel=canonical]')?.href")
    if canonical != site + cfg["pages"]["howto"].lstrip("/").replace("index.html", ""):
        res["broken_links"].append(f"{cfg['pages']['howto']}: canonical {canonical}")
    icon = page.evaluate("document.querySelector('link[rel=icon]')?.href")
    if not icon or page.request.get(icon).status != 200:
        res["broken_links"].append(f"{cfg['pages']['howto']}: favicon {icon} not found")
    return f"{len(locs)} pages in sitemap.xml"


def check_breadcrumb(page, base, cfg, res):
    """A how-to page shows Section > Group > Page above its title, outside the search index; the
    section links to the How-to index, the group to its heading there."""
    page.goto(base + cfg["pages"]["howto"], wait_until=LOAD)
    got = page.evaluate("""() => { const n = document.querySelector('nav.breadcrumb');
        if (!n) return null;
        const h1 = document.querySelector('main h1');
        return {items: [...n.querySelectorAll('li')].map(l => l.textContent.trim()),
                links: [...n.querySelectorAll('a')].map(a => a.getAttribute('href')),
                ignored: !!n.closest('[data-pagefind-ignore]'),
                above: !!h1 && !!(n.compareDocumentPosition(h1) & Node.DOCUMENT_POSITION_FOLLOWING)}; }""")
    group = next(g for g, slugs in expected_howto_groups() if "draw-a-mesh" in slugs)
    ok = (got is not None and got["items"][:2] == ["How-to", group] and len(got["items"]) == 3
          and got["ignored"] and got["above"] and len(got["links"]) == 2
          and all("how-to/" in h for h in got["links"]) and got["links"][1].endswith("#" + group.lower().replace(" ", "-")))
    if ok:
        r = page.request.get(urllib.parse.urljoin(page.url, got["links"][0].split("#")[0]))
        ok = r.status < 400
    if not ok:
        res["broken_links"].append(f"breadcrumb of how-to/draw-a-mesh: {got}")
    return " > ".join(got["items"]) if got else None


def check_mobile_menu(browser, base, cfg, res):
    """390 px: open the menu on a page far down the menu; the current entry is visible."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(base + cfg["pages"]["howto"].replace("draw-a-mesh", "render-to-a-texture"), wait_until=LOAD)
    page.click(cfg["menu_button"])
    page.wait_for_timeout(500)
    box = page.locator(cfg["menu_active"]).first.bounding_box()
    ok = box is not None and box["y"] >= 0 and box["y"] + box["height"] <= 844
    if not ok:
        res["broken_links"].append(f"mobile menu: the current page is not visible when the menu opens ({box})")
    # figure: a tap opens the lightbox with the image
    page.goto(base + cfg["pages"]["camera"], wait_until=LOAD)
    page.locator("a.figure-zoom").first.click()
    page.wait_for_timeout(500)
    shown = page.evaluate("() => { const b = document.querySelector('.lightbox'); const i = b && b.querySelector('img');"
                          " return !!(b && !b.hidden && i && i.complete && i.naturalWidth > 0 && i.getBoundingClientRect().width >= 600); }")
    if not shown:
        res["broken_links"].append("figure: a tap does not open the lightbox with the full-size image")
    ctx.close()
    return ok and shown


def run_proto(name, cfg, browser, report):
    out = os.path.join(HERE, "out", name)
    os.makedirs(out, exist_ok=True)
    httpd, base = serve(os.path.join(ROOT, cfg["dist"]))
    res = {"errors": [], "search": {}, "filter": None, "broken_links": [], "console": []}
    report[name] = res
    timing = res["timing"] = {}     # seconds spent in each phase, printed at the end
    clock = [time.time()]
    def lap(phase):
        now = time.time()
        timing[phase] = round(timing.get(phase, 0) + now - clock[0], 1)
        clock[0] = now
    try:
        # --- screenshots
        modes = {"light": dict(viewport={"width": 1400, "height": 900}, color_scheme="light"),
                 "dark": dict(viewport={"width": 1400, "height": 900}, color_scheme="dark"),
                 "mobile": dict(viewport={"width": 390, "height": 844}, color_scheme="light",
                                device_scale_factor=2, is_mobile=True, has_touch=True)}
        for mode, opts in modes.items():
            ctx = browser.new_context(**opts)
            page = ctx.new_page()
            page.on("console", lambda m: m.type == "error" and res["console"].append(f"{page.url}: {m.text}"))
            for pname, path in cfg["pages"].items():
                t0 = time.time()
                page.goto(base + path, wait_until=LOAD)
                if mode == "dark" and cfg.get("dark_toggle_js"):
                    page.evaluate(cfg["dark_toggle_js"])
                    page.wait_for_timeout(300)
                ready(page)
                page.screenshot(path=os.path.join(out, f"{pname}-{mode}.png"),
                                full_page=(pname != "vec3"))
                res.setdefault("load_ms", {})[f"{pname}-{mode}"] = int((time.time() - t0) * 1000)
            ctx.close()
        lap("screenshots (pages x light/dark/mobile)")

        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        # --- vec3 filter: own functions (.fn-entry) and functions shared with vecN (.fn-shared)
        page.goto(base + cfg["pages"]["vec3"], wait_until=LOAD)
        items = page.locator(".fn-entry, .fn-shared")
        total = items.count()
        shared_ignored = page.eval_on_selector_all(
            ".fn-shared", "els => els.length > 0 && els.every(e => e.closest('[data-pagefind-ignore]'))")
        checks_ = {}
        for query, cls in (("norm", "fn-shared"), ("cross", "fn-entry")):
            page.fill(cfg["filter_input"], query)
            page.wait_for_timeout(300)
            vis = [(e.get_attribute("data-name"), e.get_attribute("class")) for e in items.all() if e.is_visible()]
            checks_[query] = 0 < len(vis) < total and any(n == query and cls in (c or "") for n, c in vis)
        # --- rotation_transform filter: the methods are matched too (review: "0 / 21")
        page.goto(base + cfg["pages"]["rotation"], wait_until=LOAD)
        page.fill(cfg["filter_input"], "from_axis")
        page.wait_for_timeout(300)
        vis = [e.get_attribute("data-name") for e in page.locator(".member-row, .fn-entry, .fn-shared").all()
               if e.is_visible()]
        checks_["rotation_transform from_axis"] = "from_axis_angle" in vis
        ok = all(checks_.values()) and shared_ignored
        res["filter"] = {"total": total, "checks": checks_, "shared_block_ignored_by_search": shared_ignored, "ok": ok}
        lap("filter")

        # --- search: every query in the same page (the search box stays open)
        page.goto(base + cfg["pages"]["home"], wait_until=LOAD)
        if cfg.get("search_open"):
            page.click(cfg["search_open"])
        for query, expect, max_rank in SEARCH_CASES:
            links = search_links(page, cfg, query)
            # rank by distinct pages (sub-results / anchors of the same page count once)
            pages = []
            for h in links:
                p = urllib.parse.unquote(urllib.parse.urlparse(h).path).replace("index.html", "").lower()
                if p not in pages:
                    pages.append(p)
            top = pages[:5]
            rank = next((i + 1 for i, p in enumerate(pages) if expect in p), None)
            ok = rank is not None and rank <= max_rank
            first_sub = None
            if query in EXACT_FIRST and pages:
                frags = [urllib.parse.urlparse(h).fragment for h in links
                         if urllib.parse.unquote(urllib.parse.urlparse(h).path).replace("index.html", "").lower() == pages[0]
                         and urllib.parse.urlparse(h).fragment]
                first_sub = frags[0] if frags else None
                ok = ok and bool(first_sub) and first_sub.startswith(f"fn-{query}-")
            res["search"][query] = {"ok": ok, "rank": rank, "max_rank": max_rank, "first_sub": first_sub, "top": top}
            if not ok:      # screenshot of the failing searches only
                page.screenshot(path=os.path.join(out, f"search-{query.replace(' ', '_')}.png"))
        lap(f"search ({len(SEARCH_CASES)} queries)")

        # --- internal links of the main pages
        seen = set()
        for path in cfg["pages"].values():
            page.goto(base + path, wait_until=LOAD)
            hrefs = page.eval_on_selector_all("main a[href], article a[href], .content a[href]", "els => els.map(e => e.href)")
            for h in hrefs:
                u = urllib.parse.urlparse(h)
                if not h.startswith(base) or u.path in seen:
                    continue
                seen.add(u.path)
                r = page.request.get(base + u.path)
                if r.status >= 400:
                    res["broken_links"].append(f"{path} -> {u.path} ({r.status})")
        lap("internal links of the main pages")

        # --- inline code links of the guides (content_links of api.json): target page and anchor exist
        res["code_links"] = check_code_links(os.path.join(ROOT, cfg["dist"]), res["broken_links"])
        res["math"] = check_math(os.path.join(ROOT, cfg["dist"]), res["broken_links"])
        res["code_images"] = check_code_images(res["broken_links"])
        lap("code_links")
        res["home_anchors"] = check_home_anchors(os.path.join(ROOT, cfg["dist"]), res["broken_links"])
        lap("home_anchors")
        res["fragment_links"] = check_fragment_links(os.path.join(ROOT, cfg["dist"]), res["broken_links"])
        lap("fragment_links")
        res["figure_links"] = check_figure_links(os.path.join(ROOT, cfg["dist"]), res["broken_links"])
        lap("figure_links")
        res["figure_size"] = check_figure_size(page, base, cfg, res)
        lap("figure_size")
        res["howto_sidebar"] = check_howto_sidebar(page, base, cfg, res)
        lap("howto_sidebar")
        res["mobile_menu_and_lightbox"] = check_mobile_menu(browser, base, cfg, res)
        lap("mobile_menu_and_lightbox")
        res["method_groups"] = check_method_groups(page, base, cfg, res)
        lap("method_groups")
        res["howto_index"] = check_howto_index(page, base, cfg, res)
        lap("howto_index")
        res["breadcrumb"] = check_breadcrumb(page, base, cfg, res)
        res["not_found"] = check_not_found(page, base, cfg, res)
        if name == "lhtml":
            res["discovery"] = check_discovery(page, base, cfg, res)
        lap("breadcrumb")

        # --- figures of the types (types.yaml): shown on the reference page and loaded
        api = json.load(open(os.path.join(ROOT, "build", "api.json"), encoding="utf-8"))
        for tname, t in api["types"].items():
            if not t["figures"]:
                continue
            slug = tname if os.path.isdir(os.path.join(ROOT, cfg["dist"], "reference", tname)) else tname.lower()
            page.goto(f"{base}/reference/{slug}/", wait_until=LOAD)
            page.eval_on_selector_all("figure img", "els => els.forEach(e => { e.loading = 'eager'; })")
            page.wait_for_function("[...document.querySelectorAll('figure img')].every(e => e.complete)", timeout=5000)
            shown = page.eval_on_selector_all(
                "figure img", "els => els.filter(e => e.complete && e.naturalWidth > 0).map(e => e.getAttribute('src'))")
            for f in t["figures"]:
                if not any(s.endswith(f["src"]) for s in shown):
                    res["broken_links"].append(f"reference/{tname}: figure {f['src']} missing or not loaded")
        lap("figures of the reference types")
        ctx.close()
    except Exception as e:  # keep going with the other prototype
        res["errors"].append(repr(e))
    finally:
        httpd.shutdown()


def run_one(name):
    """Test one site in its own browser (one process per site, run in parallel)."""
    print(f"== {name}", flush=True)
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        run_proto(name, CONFIG[name], browser, report)
        browser.close()
    print(f"== {name} done in {sum(report[name].get('timing', {}).values()):.0f} s", flush=True)
    return report[name]


def main():
    from concurrent.futures import ProcessPoolExecutor
    names = sys.argv[1:] or list(CONFIG)
    with ProcessPoolExecutor(max_workers=len(names)) as pool:
        report = dict(zip(names, pool.map(run_one, names)))
    with open(os.path.join(HERE, "out", "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)

    failed = 0
    for n, r in report.items():
        print(f"\n### {n}")
        t = r.get("timing", {})
        if t:
            print(f"  time: {sum(t.values()):.0f} s = " + ", ".join(f"{k} {v:.0f}" for k, v in sorted(t.items(), key=lambda x: -x[1]) if v >= 1))
        for q, s in r["search"].items():
            print(f"  search {q!r:16} {'ok ' if s['ok'] else 'KO '} rank={s['rank']}/{s['max_rank']}{(' first=' + str(s['first_sub'])) if s.get('first_sub') else ''} {s['top'][:3]}")
            failed += not s["ok"]
        f = r["filter"]
        if f:
            print(f"  filter: {f['checks']}, shared block ignored by search: {f['shared_block_ignored_by_search']} -> {'ok' if f['ok'] else 'KO'}")
            failed += not f["ok"]
        print(f"  code links of the guides: {r.get('code_links')}")
        print(f"  functions anchored by their id on their home page: {r.get('home_anchors')}")
        print(f"  #fragment links of the content pages (all, to the glossary): {r.get('fragment_links')}")
        print(f"  figures with a full-size link: {r.get('figure_links')}")
        print(f"  figure width <= {FIGURE_MAX_SCALE} x intrinsic width, centered: {r.get('figure_size')}")
        print(f"  How-to sidebar: {r.get('howto_sidebar')}; mobile menu and lightbox: {r.get('mobile_menu_and_lightbox')}")
        print(f"  methods grouped by name: {r.get('method_groups')}; How-to index: {r.get('howto_index')}; breadcrumb: {r.get('breadcrumb')}")
        print(f"  broken links: {r['broken_links'] or 'none'}")
        print(f"  console errors: {r['console'][:5] or 'none'}")
        print(f"  errors: {r['errors'] or 'none'}")
        failed += len(r["broken_links"]) + len(r["errors"])
    # heading ids of the content pages: the same on both sites (a link page.md#section of the
    # content must work on both)
    if len(names) > 1:
        ids = {n: heading_ids(os.path.join(ROOT, CONFIG[n]["dist"])) for n in names}
        a, b = names[0], names[1]
        diff = [f"{p}: {sorted(set(ids[a][p]) ^ set(ids[b].get(p, [])))[:4]}"
                for p in sorted(ids[a]) if p in ids[b] and set(ids[a][p]) != set(ids[b][p])]
        print(f"\n### heading ids of the content pages, {a} vs {b}: "
              f"{len(ids[a])} pages compared, {'identical' if not diff else 'DIFFERENT: ' + '; '.join(diff[:5])}")
        failed += len(diff)
    print(f"\n{failed} problem(s); screenshots in {os.path.join(HERE, 'out')}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
