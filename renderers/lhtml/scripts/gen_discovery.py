"""Files that help search engines and AI tools find and read the site, written into dist/ after
the lhtml-site build:

- favicon (static/ copied to the root of the site) and, in the <head> of every page, the icon
  links, the canonical URL and the Open Graph tags (preview of a shared link);
- sitemap.xml: every page, with the date of its last change;
- llms.txt (https://llmstxt.org): what CGP is and the list of the pages with their description;
- llms-full.txt: the whole documentation as plain Markdown, the reference included (from
  build/api.json), to be read in one file.

The URLs are absolute, on the public site (SITE_URL, env CGP_SITE_URL), whatever the base_url of
the build: a local build points to the same canonical pages as the deployed one.
"""
import html
import json
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

SITE_URL = os.environ.get('CGP_SITE_URL', 'https://graphicscomputing.fr/cgp/')
SITE_NAME = 'CGP documentation'
OG_IMAGE = 'assets/environment-map-demo/poster.png'
SECTIONS = [('get-started', 'Get started'), ('understand', 'Understand'), ('how-to', 'How-to'),
            ('examples', 'Examples'), ('reference', 'Reference')]
SUMMARY = ('CGP (Computer Graphics Programming) is a lightweight C++ library to learn and prototype '
           'interactive 3D graphics with OpenGL: meshes, shaders, cameras, textures, animation and a '
           'GUI, with direct access to the OpenGL calls. Programs also compile to WebGL (Emscripten).')
ABOUT = """\
- Source code: https://github.com/drohmer/cgp-2027 (MIT license)
- Sources of this documentation: https://github.com/drohmer/cgp_documentation
- Public code using CGP: https://github.com/drohmer/epita_ani3d_lab_code-2027 (examples) and
  https://github.com/drohmer/csc43043ep-lab-code (course labs, without the solutions)
- The types of CGP: vec2/vec3/vec4 are numarray_stack<float,N>, mat2/mat3/mat4 are
  matrix_stack<float,N,N>; a mesh (CPU data) is sent to the GPU as a mesh_drawable, drawn with
  draw(drawable, environment) in a scene_structure."""


def page_url(rel):
    """rel = folder of the page in dist/ ('' for the home page) -> its public URL."""
    return SITE_URL + (rel + '/' if rel else '')


def site_pages(dist, order):
    """[(rel, title, description)] in the order of the site (deck order: home, sections, reference)."""
    out = []
    for item in order:
        rel = re.sub(r'/?index\.html$', '', item)       # 'index.html', 'reference/index.html'
        f = dist / rel / 'index.html'
        if not f.exists():
            continue
        text = f.read_text(encoding='utf-8')
        title = re.search(r'<title>(.*?)</title>', text, re.S).group(1)
        title = html.unescape(re.sub(r'\s+-\s+CGP docs$', '', title.strip()))
        m = re.search(r'<meta name="description" content="(.*?)">', text)
        out.append((rel, title, html.unescape(m.group(1)) if m else ''))
    return out


def last_change(paths, root):
    """Date (YYYY-MM-DD) of the last commit touching these paths, else today."""
    try:
        out = subprocess.run(['git', '-C', str(root), 'log', '-1', '--format=%cs', '--', *map(str, paths)],
                             capture_output=True, text=True, check=True).stdout.strip()
        return out or date.today().isoformat()
    except (OSError, subprocess.CalledProcessError):
        return date.today().isoformat()


def source_of(rel, content):
    """The content page of a site page, or None (generated reference page)."""
    md = content / ('index.md' if rel == '' else f'{rel}.md')
    return md if md.exists() else None


def write_sitemap(dist, pages, content, root):
    reference_date = last_change([root / 'editorial', root / 'docmodel'], root)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel, _, _ in pages:
        md = source_of(rel, content)
        when = last_change([md], root) if md else reference_date
        lines.append(f'  <url><loc>{escape(page_url(rel))}</loc><lastmod>{when}</lastmod></url>')
    lines.append('</urlset>')
    (dist / 'sitemap.xml').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def head_tags(rel, title, description, base_url):
    """Tags added at the end of the <head> of a page; rel None = the 404 page (served at any
    path: icons from base_url, no canonical URL)."""
    root = base_url if rel is None else '../' * (rel.count('/') + 1 if rel else 0)
    tags = [f'<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">',
            f'<link rel="icon" href="{root}favicon-32.png" sizes="32x32" type="image/png">',
            f'<link rel="apple-touch-icon" href="{root}apple-touch-icon.png">']
    if rel is not None:
        url = html.escape(page_url(rel))
        tags += [f'<link rel="canonical" href="{url}">',
                 '<meta property="og:type" content="website">',
                 f'<meta property="og:site_name" content="{SITE_NAME}">',
                 f'<meta property="og:title" content="{html.escape(title)}">',
                 f'<meta property="og:url" content="{url}">',
                 f'<meta property="og:image" content="{SITE_URL}{OG_IMAGE}">',
                 '<meta name="twitter:card" content="summary_large_image">']
        if description:
            tags.append(f'<meta property="og:description" content="{html.escape(description)}">')
    return '\n'.join(tags) + '\n'


def add_head_tags(dist, pages, base_url):
    for rel, title, description in pages:
        f = dist / rel / 'index.html'
        text = f.read_text(encoding='utf-8')
        f.write_text(text.replace('</head>', head_tags(rel, title, description, base_url) + '</head>', 1),
                     encoding='utf-8')
    f = dist / '404.html'
    if f.exists():
        text = f.read_text(encoding='utf-8')
        f.write_text(text.replace('</head>', head_tags(None, '', '', base_url) + '</head>', 1), encoding='utf-8')


def write_llms(dist, pages):
    out = [f'# {SITE_NAME}', '', f'> {SUMMARY}', '', ABOUT, '',
           f'Home page: [{SITE_NAME}]({page_url("")})',
           f'The whole documentation in one Markdown file: {SITE_URL}llms-full.txt', '']
    by_section = {}
    for rel, title, description in pages:
        if rel:
            by_section.setdefault(rel.split('/')[0], []).append((rel, title, description))
    for key, name in SECTIONS:
        out += [f'## {name}', '']
        for rel, title, description in by_section.get(key, []):
            out.append(f'- [{title}]({page_url(rel)})' + (f': {description}' if description else ''))
        out.append('')
    (dist / 'llms.txt').write_text('\n'.join(out), encoding='utf-8')


# ------------------------------------------------------------------ llms-full.txt

MD_LINK = re.compile(r'\]\(([^)\s:#]+)\.md(#[^)\s]*)?\)')
CODE_IMAGE = re.compile(r'<!--\s*code-image:\s*[^|]*\|\s*(.*?)\s*-->')
DEMO = re.compile(r'<!--\s*demo:\s*([\w-]+)\s*-->')
COMMENT = re.compile(r'<!--.*?-->', re.S)


def markdown_page(md, content):
    """Text of a content page for llms-full.txt: no front matter, the links to other pages and
    the images as absolute URLs, the markers of the site replaced by a short note."""
    text = md.read_text(encoding='utf-8')
    if text.startswith('---'):
        text = text.split('---', 2)[2]
    here = md.parent.relative_to(content)

    def link(m):
        target = os.path.normpath(here / m.group(1)).replace(os.sep, '/')
        target = '' if target in ('index', '.') else re.sub(r'/?index$', '', target)
        return f']({page_url(target)}{m.group(2) or ""})'
    text = MD_LINK.sub(link, text)
    text = re.sub(r'\]\((?:\.\./)*assets/', f']({SITE_URL}assets/', text)
    text = CODE_IMAGE.sub(lambda m: f'(Image on the page: {m.group(1)})', text)
    text = DEMO.sub('(Interactive WebGL demo on the page.)', text)
    return COMMENT.sub('', text).strip()


def reference_markdown(api):
    """The reference as Markdown: each type with its fields and functions, then the pages of
    functions by theme. A function shared by a family (vecN for vec3) is listed on the family."""
    fns = {f['id']: f for f in api['functions']}

    def fn_line(fid):
        f = fns.get(fid)
        if not f:
            return None
        desc = (f.get('description') or f.get('brief') or '').strip()
        return f'- `{f["signature"]}`' + (f' - {desc}' if desc else '')

    out = ['# Reference', '',
           'Every type of CGP with the functions that apply to it, generated from the C++ sources.', '']
    if api.get('aliases'):
        alias = api['aliases']
        out.append('Aliases: ' + ', '.join(f'{k} = {v}' for k, v in alias.items()) + '.'
                   if isinstance(alias, dict) else 'Aliases: ' + ', '.join(map(str, alias)) + '.')
        out.append('')
    for name, t in api['types'].items():
        out += [f'## {name}', '', f'URL: {page_url("reference/" + name)}', '']
        if t.get('canonical') and t['canonical'] != name:
            out.append(f'C++ type: `{t["canonical"]}`.')
        if t.get('family_of'):
            out.append('Shared by: ' + ', '.join(t['family_of']) + '.')
        if t.get('short'):
            out.append(t['short'])
        out.append('')
        fields = (t.get('struct') or {}).get('fields') or []
        if fields:
            out += ['Fields:', '']
            for fd in fields:
                desc = (fd.get('description') or fd.get('brief') or '').strip()
                out.append(f'- `{fd["type"]} {fd["name"]}`' + (f' - {desc}' if desc else ''))
            out.append('')
        for key, label in (('takes', 'Functions taking it'), ('returns', 'Functions returning it'),
                           ('operators', 'Operators')):
            lines = [fn_line(e['id']) for e in t.get(key) or [] if not e.get('shared')]
            lines = list(dict.fromkeys(x for x in lines if x))
            if lines:
                out += [f'{label}:', '', *lines, '']
    for gid, g in api.get('function_groups', {}).items():
        out += [f'## {g["title"]}', '', f'URL: {page_url("reference/functions/" + gid)}', '']
        if g.get('short'):
            out += [g['short'], '']
        lines = list(dict.fromkeys(x for x in (fn_line(e['id']) for e in g.get('functions') or []) if x))
        out += [*lines, '']
    return '\n'.join(out)


def write_llms_full(dist, pages, content, api_path):
    out = [f'# {SITE_NAME}', '', f'> {SUMMARY}', '', ABOUT, '']
    for rel, title, description in pages:
        md = source_of(rel, content)
        if not md:
            continue
        out += ['', '-' * 72, f'Page: {title}', f'URL: {page_url(rel)}', '-' * 72, '',
                markdown_page(md, content), '']
    out += ['', '-' * 72, '', reference_markdown(json.loads(api_path.read_text(encoding='utf-8')))]
    (dist / 'llms-full.txt').write_text('\n'.join(out) + '\n', encoding='utf-8')


def main(dist, order, content, api_path, static, base_url):
    """Called by build.py after the lhtml-site build. Returns the number of pages listed."""
    root = content.parent
    for f in static.iterdir():
        shutil.copy2(f, dist / f.name)
    pages = site_pages(dist, order)
    add_head_tags(dist, pages, base_url)
    write_sitemap(dist, pages, content, root)
    write_llms(dist, pages)
    write_llms_full(dist, pages, content, api_path)
    return len(pages)
