"""lhtml-site plugin: the shared Markdown content of the CGP documentation.

The content (ROOT/content/*.md) is written for a generic docs tool: math in
$...$ / $$...$$, links between .md files, images relative to the .md file,
and a `<!-- demo: NAME -->` marker. This plugin adapts it to lhtml-site:

pre_process (the Markdown source, before Jinja):
  - $...$ -> \\(...\\) and $$...$$ -> \\[...\\] outside code (lhtml-site keeps
    \\( \\) and \\[ \\] away from Markdown, and KaTeX renders them);
  - <!-- demo: NAME --> -> a click-to-load poster of assets/NAME-demo/;
  - <!-- gallery: SECTION --> -> the posters of the demos of a section, linking to its pages;
  - <!-- code-image: PATH | caption --> + a code block -> the code next to the image;
post_process (the page HTML):
  - links to .md files -> the generated pages (x/y.md -> x/y/index.html);
  - images relative to the .md file -> relative to the generated page;
  - an image alone in its paragraph -> <figure> with the alt text as caption;
  - tables wrapped in a scrolling container (narrow screens);
  - inline code naming a CGP type, function or member -> link to its reference page
    (`content_links` of api.json, computed by cgp-docmodel: no name resolution here).

A page of the content `a/b.md` is generated in the directory `a/b/`
(`index.md` at the root): the mapping is a convention, inverted here.
"""
import html as html_mod
import json
import posixpath
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / 'content' / 'assets'
API = ROOT / 'build' / 'api.json'

# Inline code outside code blocks, links and headings; an h1/h2 starts a new section.
CODE_TOKEN = re.compile(r'<pre\b.*?</pre>|<a\b.*?</a>|<h([1-6])\b.*?</h\1>|<code>([^<]*)</code>', re.S)
_api = {}


def _links():
    """content_links of api.json and the functions by id (read once)."""
    if not _api:
        api = json.loads(API.read_text(encoding='utf-8'))
        _api['links'] = api.get('content_links') or {}
        _api['F'] = {f['id']: f for f in api['functions']}
    return _api


def _target_url(t, F):
    """Site path (from the root) of a content_links target: type page or group page + anchor."""
    page = f'reference/{t["type"]}/index.html' if t['type'] else f'reference/functions/{t["group"]}/index.html'
    # functions, methods and fields: anchored by their model id (the same on both sites)
    return page + '#' + t['id'] if t.get('id') else page


def link_code(body, page_dir):
    """Wrap inline code spans of content_links in a link to the reference. Only the first
    span of a given target per section (h2) is linked: a guide citing `mesh_drawable` five
    times in a section gets one link, close to where the reader is."""
    api = _links()
    seen = set()

    def sub(m):
        if m.group(1):
            if m.group(1) in '12':
                seen.clear()
            return m.group(0)
        if m.group(2) is None:
            return m.group(0)
        span = html_mod.unescape(m.group(2)).strip()
        t = api['links'].get(span)
        if not t:
            return m.group(0)
        url = _target_url(t, api['F'])
        if url in seen:
            return m.group(0)
        seen.add(url)
        return f'<a class="code-ref" href="{_relative(url, page_dir)}">{m.group(0)}</a>'

    return CODE_TOKEN.sub(sub, body)

FENCE = re.compile(r'(?ms)^[ \t]{0,3}(`{3,}|~{3,})[^\n]*\n.*?^[ \t]{0,3}\1[ \t]*$')
INLINE_CODE = re.compile(r'(`+)[^`].*?\1', re.S)
DISPLAY_MATH = re.compile(r'\$\$(.+?)\$\$', re.S)
INLINE_MATH = re.compile(r'(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\$)')
DEMO = re.compile(r'<!--\s*demo:\s*([\w-]+)\s*-->')
GALLERY = re.compile(r'<!--\s*gallery:\s*([\w-]+)\s*-->')
# <!-- code-image: PATH | caption --> followed by a fenced code block: the code and the image side by side
CODE_IMAGE = re.compile(r'<!--\s*code-image:\s*([^|>]+?)\s*(?:\|\s*(.*?))?\s*-->\s*\n(\s*(`{3,}|~{3,})[^\n]*\n.*?\n\s*\4[ \t]*)(?=\n|$)', re.S)


def _content_path(page_dir):
    """The .md file of the content a page directory comes from."""
    d = page_dir.strip('/')
    return (d + '.md') if d else 'index.md'


def _site_target(content_target):
    """The generated page of a .md file of the content."""
    stem = content_target[:-3]
    if stem == 'index':
        return 'index.html'
    if stem.endswith('/index'):
        return stem + '.html'
    return stem + '/index.html'


def _convert_math(text):
    """$ and $$ to \\( and \\[, outside fenced and inline code."""
    out, pos = [], 0
    for m in FENCE.finditer(text):
        out.append(_math_in_text(text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_math_in_text(text[pos:]))
    return ''.join(out)


def has_math(text):
    """Whether a page writes $ or $$ math outside code. lhtml-site detects the formulas of
    a page (page.math, rendered at build) from its source before this plugin converts the
    dollars: build.py says `math: true` in the front matter of these pages."""
    return _convert_math(text) != text


def _math_in_text(text):
    out, pos = [], 0
    for m in INLINE_CODE.finditer(text):
        out.append(_math(text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_math(text[pos:]))
    return ''.join(out)


def _math(text):
    text = DISPLAY_MATH.sub(lambda m: '\\[' + m.group(1) + '\\]', text)
    return INLINE_MATH.sub(lambda m: '\\(' + m.group(1) + '\\)', text)


def _demo_html(name, root):
    src = f'{root}assets/{name}-demo/index.html'
    folder = ASSETS / f'{name}-demo'
    size = sum(f.stat().st_size for f in folder.glob('project.*')) / 1e6
    shot = (folder / 'poster.png').exists()
    # with a poster.png (captured by demos/build.py): the image of the scene, 16:10;
    # without: a generic square poster
    poster = (f'<img class="demo-shot" src="{root}assets/{name}-demo/poster.png" alt="" loading="lazy">'
              if shot else '<span class="demo-grid" aria-hidden="true"></span>')
    # one HTML block, no blank line: Markdown keeps it as it is
    return (f'<figure class="demo{" has-shot" if shot else ""}" data-src="{src}" data-pagefind-ignore>'
            f'<button class="demo-poster" type="button" aria-label="Load the interactive {name} demo">'
            f'{poster}'
            f'<span class="demo-play" aria-hidden="true"></span>'
            f'<span class="demo-title">Interactive demo: {name}</span>'
            f'<span class="demo-hint">CGP program compiled to WebGL. Click to load (about {size:.1f} MB).</span>'
            f'</button>'
            f'<figcaption>Interactive CGP demo ({name}). <a href="{src}" target="_blank" rel="noopener">'
            f'Open in a new tab</a>.</figcaption></figure>\n\n')


def gallery_pages(section):
    """[(slug, title, group)] of the pages of a content section that have a demo poster
    (assets/<slug>-demo/poster.png), in the order of the menu (front matter `order`). Same list
    as renderers/starlight/src/plugins/cgp-markdown.mjs (galleryPages)."""
    pages = []
    for md in sorted((ROOT / 'content' / section).glob('*.md')):
        fm = re.match(r'---\n(.*?)\n---', md.read_text(encoding='utf-8'), re.S)
        meta = dict(re.findall(r'^(\w+):\s*(.*?)\s*$', fm.group(1), re.M)) if fm else {}
        if (ASSETS / f'{md.stem}-demo' / 'poster.png').exists():
            order = int(meta['order']) if meta.get('order', '').isdigit() else 1000
            pages.append((order, md.stem, meta.get('title', md.stem).strip('"\''), meta.get('group', '').strip('"\'')))
    return [p[1:] for p in sorted(pages)]


def _gallery_html(section, root):
    """<!-- gallery: SECTION --> -> a grid of the posters of the demos of the section, each
    linking to its page. One HTML block, no blank line."""
    cards = ''.join(
        f'<a class="cgp-gallery__card" href="{root}{section}/{slug}/index.html">'
        f'<img src="{root}assets/{slug}-demo/poster.png" alt="" loading="lazy">'
        f'<span class="cgp-gallery__title">{html_mod.escape(title)}</span>'
        f'<span class="cgp-gallery__group">{html_mod.escape(group)}</span></a>'
        for slug, title, group in gallery_pages(section))
    return f'<div class="cgp-gallery" data-pagefind-ignore>{cards}</div>\n\n'


def _code_image_html(m, root):
    """The code block of the marker <!-- code-image: PATH | caption --> next to the image
    content/assets/PATH. The fence stays Markdown (highlighted as any other block): it is
    between two HTML blocks, separated by blank lines."""
    src, caption, fence = m.group(1), m.group(2) or '', m.group(3)
    cap = f'<figcaption>{html_mod.escape(caption)}</figcaption>' if caption else ''
    return (f'<div class="cgp-codeimg"><div class="cgp-codeimg__code">\n\n{fence}\n\n'
            f'</div><figure class="cgp-codeimg__image" data-pagefind-ignore>'
            f'<img src="{root}assets/{src}" alt="{html_mod.escape(caption)}" loading="lazy">{cap}</figure></div>')


def pre_process(text, context):
    page = context.page or {}
    if not page.get('template', '').endswith('.md.j2') or page.get('pagetype', '').startswith('reference'):
        return text
    if re.search(r'{[{%#]', GALLERY.sub('', DEMO.sub('', text))):
        context.warning('the content holds a Jinja marker ({{, {% or {#): it will be read by Jinja')
    root = '../' * page.get('dir', '').count('/')
    text = _convert_math(text)
    text = CODE_IMAGE.sub(lambda m: _code_image_html(m, root), text)
    text = GALLERY.sub(lambda m: _gallery_html(m.group(1), root), text)
    return DEMO.sub(lambda m: _demo_html(m.group(1), root), text)


def slugify(text):
    """GitHub-style heading id, as Starlight (github-slugger) makes them: lower case, characters
    other than letters, digits, '_', '-' and spaces removed, spaces -> '-'. Both sites then have
    the same anchors, so that a link `page.md#section` of the content works on both."""
    text = html_mod.unescape(re.sub(r'<[^>]+>', '', text)).strip().lower()
    return re.sub(r'[^\w\- ]', '', text).replace(' ', '-')


def heading_ids(body):
    """Replace the ids lhtml-site gives to the headings (`run_the_program_from_l2`) by
    GitHub-style slugs, unique in the page (-1, -2... as github-slugger)."""
    used = {}

    def sub(m):
        level, attrs, inner = m.group(1), m.group(2), m.group(3)
        base = slugify(inner) or 'section'
        n = used.get(base, 0)
        used[base] = n + 1
        slug = base if n == 0 else f'{base}-{n}'
        attrs = re.sub(r'\sid="[^"]*"', '', attrs)
        return f'<h{level} id="{slug}"{attrs}>{inner}</h{level}>'

    return re.sub(r'<h([1-6])((?:\s[^>]*)?)>(.*?)</h\1>', sub, body, flags=re.S)


def svg_width(path):
    """Intrinsic width of an SVG file (width attribute, else viewBox width), None if unknown.
    The figures are shown at most at this width (times --figure-scale in cgp.css), so that
    their text has the same size whatever the width of the file (review C1)."""
    try:
        head = Path(path).read_text(encoding='utf-8', errors='replace')[:4000]
    except OSError:
        return None
    m = re.search(r'<svg\b[^>]*>', head)
    if not m:
        return None
    w = re.search(r'\swidth="([\d.]+)(?:px)?"', m.group(0))
    if w:
        return float(w.group(1))
    vb = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)', m.group(0))
    return float(vb.group(1)) if vb else None


def figure_size_style(path):
    """style="--fig-w:...px" for an <img> of a figure, '' when the width is unknown."""
    w = svg_width(path) if str(path).endswith('.svg') else None
    return f' style="--fig-w:{w:g}px"' if w else ''


def figure_html(img_tag, href, caption):
    """A figure whose image opens full size on click (lightbox of site.js; without JS, the link
    opens the image itself): text of the figures is too small on a phone."""
    hint = '<span class="figure-hint" data-pagefind-ignore> Tap to enlarge.</span>'
    cap = f'<figcaption>{caption}{hint}</figcaption>' if caption else ''
    return (f'<figure class="figure"><a class="figure-zoom" href="{href}" '
            f'aria-label="Open the figure full size">{img_tag}</a>{cap}</figure>')


def _relative(target, page_dir):
    return posixpath.relpath(target, page_dir.strip('/') or '.')


def post_process(html, context):
    page = context.page or {}
    if not page.get('template', '').endswith('.md.j2'):
        return html
    page_dir = page.get('dir', '')
    content_dir = posixpath.dirname(_content_path(page_dir))

    def link(m):
        attr, url, anchor = m.group(1), m.group(2), m.group(3) or ''
        if re.match(r'^[a-z]+:|^/|^#', url):
            return m.group(0)
        target = posixpath.normpath(posixpath.join(content_dir, url))
        return f'{attr}="{_relative(_site_target(target), page_dir)}{anchor}"'

    html = re.sub(r'(href)="([^"#]+\.md)(#[^"]*)?"', link, html)

    def file_link(m):
        # relative link to another file of the content (download of an image, ...)
        url = m.group(2)
        if re.match(r'^[a-z]+:|^/|^#', url) or url.endswith('/') or url.endswith('.html'):
            return m.group(0)
        target = posixpath.normpath(posixpath.join(content_dir, url))
        return f'{m.group(1)}="{_relative(target, page_dir)}"'

    # the reference pages (generated) already write paths relative to the page itself
    reference = page.get('pagetype', '').startswith('reference')
    main_at = html.find('<main')
    if not reference:
        html = html[:main_at] + re.sub(r'(href)="((?:\.\./)*assets/[^"#]+)"', file_link, html[main_at:])

    def image(m):
        url = m.group(2)
        if re.match(r'^[a-z]+:|^/|^data:', url):
            return m.group(0)
        target = posixpath.normpath(posixpath.join(content_dir, url))
        return f'{m.group(1)}="{_relative(target, page_dir)}"'

    main = html.find('<main')
    head, body = html[:main], html[main:]
    if not reference:
        body = re.sub(r'(<img[^>]*?\ssrc)="([^"]+)"', image, body)

    def figure(m):
        img = m.group(1)
        alt = re.search(r'alt="([^"]*)"', img)
        src = re.search(r'\ssrc="([^"]+)"', img).group(1)
        size = figure_size_style(ROOT / 'content' / posixpath.normpath(posixpath.join(page_dir.strip('/'), src)))
        img = img.replace('<img ', f'<img loading="lazy" decoding="async"{size} ', 1)
        return figure_html(img, src, alt.group(1) if alt else '')

    body = re.sub(r'<p>\s*(<img[^>]*>)\s*</p>', figure, body)
    if not page.get('pagetype', '').startswith('reference'):
        body = heading_ids(body)      # reference pages set their own ids (function anchors)
    body = re.sub(r'<table>(.*?)</table>', r'<div class="table-wrap"><table>\1</table></div>', body, flags=re.S)
    if not page.get('pagetype', '').startswith('reference'):
        body = link_code(body, page_dir)
    return head + body
