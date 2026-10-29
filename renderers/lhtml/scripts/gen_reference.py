"""Generate the Reference pages of the CGP documentation from api.json.

One Markdown page per type (src/reference/<type>/index.md.j2) and an index
(src/reference/index.md.j2). The body of each page is raw HTML (a single
Markdown HTML block, written without blank lines so that Markdown leaves it
alone); only the title is a Markdown heading, so that lhtml-site gives the
page its title.

Usage: gen_reference.py API_JSON OUT_SRC_DIR   (prints the deck entries)
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

import lhtml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins'))
from cgp_content import figure_size_style  # noqa: E402  (max width of a figure, review C1)

ASSETS = Path(__file__).resolve().parents[3] / 'content' / 'assets'

CATEGORIES = [('construct', 'Construct'), ('transform', 'Transform'), ('compute', 'Compute'),
              ('draw', 'Draw'), ('convert', 'Convert'), ('io', 'I/O'), ('access', 'Access'),
              ('other', 'Other')]

def esc(text):
    """HTML-escaped text that neither Jinja nor the Markdown math scanner reads."""
    text = html.escape(str(text or ''), quote=True)
    return text.replace('{', '&#123;').replace('}', '&#125;').replace('\\', '&#92;').replace('`', '&#96;')


def jinja_safe(fragment):
    """An HTML fragment (already escaped) with the braces made inert for Jinja."""
    return fragment.replace('{', '&#123;').replace('}', '&#125;').replace('\\', '&#92;')


def tidy_sig(sig):
    return re.sub(r'>const', '> const', sig or '')


def format_signature(f, explode=True):
    """The signature on several lines when it is long: one parameter per line (not for the
    overloads of a group, kept on one wrapped line each to stay compact)."""
    sig = tidy_sig(f['signature'])
    if explode and len(sig) > 96 and f.get('params') and len(f['params']) > 1:
        head = sig[:sig.index('(') + 1]
        params = []
        for p in f['params']:
            s = f"{p['type']} {p['name']}".strip()
            if p.get('default') is not None:
                s += f" = {p['default']}"
            params.append('    ' + tidy_sig(s))
        tail = sig[sig.rindex(')'):]
        sig = head + '\n' + ',\n'.join(params) + '\n' + tail
    if f.get('template'):
        sig = f['template'].strip() + '\n' + sig
    return sig


def signatures(f, explode=True):
    """The signature, then the signatures of the variants (the non-const overload of a const
    method or function, `variants` of api.json), one per line."""
    sig = format_signature(f, explode)
    for v in f.get('variants') or []:
        sig += '\n' + short_sig(v['signature'], f.get('owner'))
    return sig


def short_sig(sig, owner=None):
    """A signature without the owner prefix (`T::f(...)` -> `f(...)`)."""
    sig = tidy_sig(sig)
    return sig.replace(f'{owner}::', '') if owner else sig


def highlight(code):
    out = lhtml.highlight(code + '\n', 'cpp')
    out = out.replace('<div class="code"><pre><span></span>', '').replace('\n</pre></div>', '').strip('\n')
    return jinja_safe(out)


def old_anchor(f, suffix=''):
    """Anchor used before schema 1.5 (hash of the key, suffix per section: -r returns,
    -o operators). Kept as an empty alias so that old links still land on the entry."""
    h = hashlib.sha1(f['key'].encode('utf-8')).hexdigest()[:6]
    name = re.sub(r'[^A-Za-z0-9_]+', '', f['name'].replace('operator', 'op')) or 'fn'
    return f'fn-{name}-{h}{suffix}'


SUFFIX = {'takes': '', 'returns': '-r', 'operators': '-o', 'functions': ''}


def home_url(f, site, rel='../'):
    """Page and anchor where a function is documented in full (`home` of api.json); the
    anchor is the model id of the function, the same on both renderers."""
    h = f.get('home')
    if not h:
        return None
    if h.get('type'):
        return f'{rel}{h["type"]}/index.html#{f["id"]}'
    return f'{rel}functions/{h["group"]}/index.html#{f["id"]}'


def home_label(f, site):
    h = f.get('home') or {}
    if h.get('type'):
        return 'on', h['type']
    if h.get('group'):
        return 'in', (site.function_groups.get(h['group']) or {}).get('title', h['group'])
    return '', ''




UTILITIES = 'Utilities'   # group of the pages of functions of no theme (function_groups.yaml, under)


class Site:
    """What a page needs to know about the other types (schema 1.2)."""

    def __init__(self, api):
        self.F = {f['id']: f for f in api['functions']}
        self.types = api['types']
        self.function_groups = api.get('function_groups') or {}
        # canonical name -> documented type (numarray_stack<float,4> -> vec4)
        self.by_canonical = {}
        for n, t in self.types.items():
            self.by_canonical.setdefault(t.get('canonical'), n)
        # groups of the menu and the index: the order of the model, families first
        groups = {}
        for n, t in self.types.items():
            groups.setdefault(t.get('group') or 'Other types', []).append(n)
        self.groups = [(g, sorted(ns, key=lambda n: not self.types[n].get('family_of'))) for g, ns in groups.items()]
        self.order = [n for _, ns in self.groups for n in ns]
        # pages of functions (function_groups.yaml) by group of the menu (`under`): after the
        # types of the same theme; the group Utilities, of no type, comes last
        self.functions_under = {}
        for name, g in self.function_groups.items():
            self.functions_under.setdefault(g.get('under') or UTILITIES, []).append(name)
        self.menu = [(g, ns, self.functions_under.get(g, [])) for g, ns in self.groups]
        if UTILITIES in self.functions_under:
            self.menu.append((UTILITIES, [], self.functions_under[UTILITIES]))

    def group_of(self, name):
        return next(g for g, ns in self.groups if name in ns)

    def documented(self, canonical):
        """The documented type of a canonical name, or None."""
        return self.by_canonical.get(canonical)

    def type_ref(self, canonical, rel='../'):
        """`canonical (doc)` with a link to the documented type when there is one."""
        doc = self.documented(canonical)
        if doc:
            return (f'<code>{esc(canonical)}</code> (<a href="{rel}{doc}/index.html"><code>{esc(doc)}</code></a>)'
                    if doc != canonical else f'<a href="{rel}{doc}/index.html"><code>{esc(doc)}</code></a>')
        return f'<code>{esc(canonical)}</code>'

    def via_label(self, canonical):
        return self.documented(canonical) or canonical


def family_noun(name, t):
    canonical = t.get('canonical') or ''
    if canonical.startswith('numarray_stack'):
        return 'all vectors'
    if canonical.startswith('matrix_stack'):
        return 'all matrices'
    return ', '.join(t.get('family_of') or [name])


def desc_html(desc):
    if not desc:
        return '<p class="fn-desc fn-missing" data-pagefind-ignore>No description yet.</p>'
    return f'<p class="fn-desc">{esc(desc)}</p>'


def src_html(f):
    return (f'<a class="fn-src" data-pagefind-ignore href="{esc(f["source_url"])}" title="{esc(f["file"])}:{f["line"]}">source</a>'
            if f.get('source_url') else '')


def entry_html(items, site, suffix='', family=False):
    """One entry for the overloads of one name on this page: [(f, e), ...]. The heading is
    anchored by the model id of the first overload, each other signature by its own id;
    the description is written once when the overloads share it, else under each one."""
    f0, e0 = items[0]
    a = f0['id']
    descs = [f.get('description') if f.get('description_source') != 'missing' else None for f, _ in items]
    shared = len(set(descs)) == 1
    many = len(items) > 1
    own, common = (descs, None) if shared else split_descriptions(descs)
    badges = ''
    if any(e.get('generic') for _, e in items) and not family:
        badges += ('<span class="badge badge-generic" data-pagefind-ignore title="Generic: comes from the template '
                   'numarray_stack&lt;T,N&gt; (or another generic container), and applies to this type">generic</span>')
    if e0.get('via'):
        badges += (f'<span class="badge badge-via" data-pagefind-ignore title="Applies through the base class '
                   f'{esc(e0["via"])}">via {esc(site.via_label(e0["via"]))}</span>')
    if many:
        badges += f'<span class="badge badge-n" data-pagefind-ignore>{len(items)} overloads</span>'
    olds = ''.join(f'<span class="old-anchor" id="{old_anchor(f, suffix)}"></span>' for f, _ in items)
    ovs = []
    for k, (f, _) in enumerate(items):
        oid = f' id="{esc(f["id"])}"' if k > 0 else ''
        src = src_html(f) if many else ''
        ovs.append(f'<div class="fn-ov"{oid}><div class="fn-ov-sig"><pre class="fn-sig code"><code>{highlight(signatures(f, not many))}</code></pre>{src}</div>'
                   + ('' if shared else desc_html(own[k])) + '</div>')
    return (f'<div class="fn-entry{" fn-entry-overloads" if many else ""}" data-name="{esc(f0["name"])}" '
            f'data-category="{esc(f0.get("category"))}">{olds}'
            f'<div class="fn-head"><h4 class="fn-name" id="{a}" data-pagefind-weight="10"><a href="#{a}">{esc(f0["name"])}</a></h4>'
            f'{badges}<span class="fn-spacer"></span>{"" if many else src_html(f0)}</div>'
            + ''.join(ovs) + (desc_html(descs[0]) if shared else '')
            + (f'<p class="fn-desc fn-desc-common">{esc(common)}</p>' if common else '') + '</div>')


def overloads(items):
    """[(f, e)] sorted -> [[(f, e) of one name], ...] in the same order."""
    groups = {}
    for f, e in items:
        groups.setdefault(f['name'], []).append((f, e))
    return list(groups.values())


def sort_key(x):
    """By name, then the overloads in source order (the order chosen by the author)."""
    f = x[0]
    return (f['name'].startswith('operator'), f['name'], f.get('file') or '', f.get('line') or 0, f['signature'])


def split_descriptions(descs):
    """Descriptions of overloads: when they all end with the same clause ("; warns if the
    uniform is not found..."), the clause is written once. Returns (per overload, common or None)."""
    if len(descs) < 2 or not all(descs):
        return descs, None
    tail = descs[0]
    for d in descs:
        while not d.endswith(tail):
            tail = tail[1:]
    m = re.search(r'[;.] ', tail)
    common = tail[m.start() + 2:].strip() if m else ''
    if len(common) < 12:
        return descs, None
    own = [d[:len(d) - len(tail) + m.start()].strip() + '.' for d in descs]
    return own, common[0].upper() + common[1:]


def compact_html(items, site, suffix=''):
    """Functions of this section documented in full on another page (their home): one line
    each (name linked to the home anchor, description, home page). Not indexed by the search."""
    if not items:
        return ''
    lines = {}
    for f, e in items:
        lines.setdefault((f['name'], home_label(f, site)), []).append(f)
    out = []
    for (nm, (prep, where)), fs in lines.items():
        href = home_url(fs[0], site)
        descs = {f.get('description') or '' for f in fs}
        desc = descs.pop() if len(descs) == 1 else f'{len(fs)} overloads'
        name = f'<a href="{href}"><code>{esc(nm)}</code></a>' if href else f'<code>{esc(nm)}</code>'
        n = f'<span class="fn-compact-n">x{len(fs)}</span>' if len(fs) > 1 else '<span></span>'
        home = f'<span class="fn-compact-home">{prep} <code>{esc(where)}</code></span>' if where else ''
        olds = ''.join(f'<span class="old-anchor" id="{old_anchor(f, suffix)}"></span>' for f in fs)
        search = ' '.join([nm, where, desc] + [f['signature'] for f in fs])
        out.append(f'<li class="fn-compact" data-name="{esc(nm)}" data-search="{esc(search.lower())}">{olds}{name}{n}'
                   f'<span class="fn-compact-desc">{esc(desc)}</span>{home}</li>')
    return ('<div class="fn-compact-block" data-pagefind-ignore><p class="fn-compact-title">Documented on another page</p>'
            f'<ul class="fn-compact-list">{"".join(out)}</ul></div>')


def split(entries, site, is_home, used):
    """(full, compact) lists of (f, e): full on the home section of the function, compact elsewhere."""
    full, compact = [], []
    for e in entries:
        f = site.F[e['id']]
        if (is_home(f) or not f.get('home')) and f['id'] not in used:
            used.add(f['id'])
            full.append((f, e))
        else:
            compact.append((f, e))
    return sorted(full, key=sort_key), sorted(compact, key=sort_key)


def grouped(full, compact, site, suffix, section_id, family=False):
    """Entries grouped by category, in the order of CATEGORIES: the overload groups in full,
    then the compact lines of the functions documented elsewhere."""
    def cat_of(f):
        cat = f.get('category') or 'other'
        return cat if cat in dict(CATEGORIES) else 'other'
    parts = []
    for cat, label in CATEGORIES:
        fl = [x for x in full if cat_of(x[0]) == cat]
        cl = [x for x in compact if cat_of(x[0]) == cat]
        if not fl and not cl:
            continue
        n = len(fl) + len(cl)
        parts.append(f'<section class="fn-group" data-category="{cat}">'
                     f'<h3 id="{section_id}-{cat}" data-toc="{label} ({n})">{label} <span class="count">{n}</span></h3>'
                     + ''.join(entry_html(g, site, suffix, family) for g in overloads(fl))
                     + compact_html(cl, site, suffix) + '</section>')
    return ''.join(parts)


def flat(full, compact, site, suffix, family=False):
    return '<section class="fn-group" data-category="operator">' + \
        ''.join(entry_html(g, site, suffix, family) for g in overloads(full)) + compact_html(compact, site, suffix) + '</section>'


def shared_blocks(name, t, site):
    """One compact block per family: the functions written once on the family page.

    Not indexed by the search (data-pagefind-ignore): these functions are found
    on the family page. Returns (html, number of .fn-shared items)."""
    fams = {}
    for rel in ('takes', 'returns', 'operators'):
        for e in t.get(rel) or []:
            if e.get('shared'):
                fams.setdefault(e['shared'], {}).setdefault(e['id'], e)
    out, n_items = [], 0
    for fam, ids in fams.items():
        ft = site.types.get(fam, {})
        by_name = {}
        for fid in ids:
            by_name.setdefault(site.F[fid]['name'], []).append(fid)
        names = sorted(by_name, key=lambda s: (s.startswith('operator'), s))
        items = []
        for nm in names:
            fids = sorted(by_name[nm], key=lambda i: site.F[i]['signature'])
            href = home_url(site.F[fids[0]], site) or f'../{fam}/index.html'
            more = f'<span class="fn-shared-n" title="{len(fids)} overloads">x{len(fids)}</span>' if len(fids) > 1 else ''
            items.append(f'<li><a class="fn-shared" data-name="{esc(nm)}" href="{href}"><code>{esc(nm)}</code>{more}</a></li>')
        n_items += len(items)
        label = f'Shared with {family_noun(fam, ft)}'
        out.append(f'<div class="fn-shared-block" id="shared-{fam}" data-family="{esc(fam)}" '
                   f'data-toc="{esc(label)} ({len(ids)})" data-pagefind-ignore>'
                   f'<p class="fn-shared-title"><strong>{esc(label)}:</strong> {len(ids)} functions on '
                   f'<a href="../{fam}/index.html"><code>{esc(fam)}</code></a>, written once for every size.</p>'
                   f'<ul class="fn-shared-list">{"".join(items)}</ul></div>')
    return ''.join(out), n_items


def method_sig_html(sig, name, weighted):
    """Escaped signature with the method name in bold; on the first signature the name is
    weighted for the search, like the name of a free function (exact method name -> type page)."""
    at = sig.find(name + '(')
    if at < 0:
        return esc(sig)
    attr = ' data-pagefind-weight="10"' if weighted else ''
    return f'{esc(sig[:at])}<strong class="m-name"{attr}>{esc(name)}</strong>{esc(sig[at + len(name):])}'


def member_tables(fields, methods, ids=True):
    """Tables of fields and methods. Each row is anchored by the id of the model (field-x,
    method id: the same anchors on both renderers) and matched by the filter (.member-row)."""
    out = []
    if fields:
        h = f'<h3 id="fields" data-toc="Fields ({len(fields)})">Fields</h3>' if ids else '<h4>Fields</h4>'
        out.append(f'<div class="member-block">{h}<table class="member-table"><tbody>')
        for fl in fields:
            init = f' = {esc(fl["initializer"].lstrip("= "))}' if fl.get('initializer') else ''
            out.append(f'<tr class="member-row" id="{esc(fl["id"])}" data-name="{esc(fl["name"])}">'
                       f'<td class="m-sig"><a class="m-anchor" href="#{esc(fl["id"])}"><code><span class="m-type">{esc(fl["type"])}</span> '
                       f'<strong>{esc(fl["name"])}</strong>{init}</code></a></td>'
                       f'<td class="m-brief">{esc(fl.get("description"))}</td></tr>')
        out.append('</tbody></table></div>')
    if methods:
        h = f'<h3 id="methods" data-toc="Methods ({len(methods)})">Methods</h3>' if ids else '<h4>Methods</h4>'
        out.append(f'<div class="member-block">{h}<table class="member-table member-methods">')
        for group in method_groups(methods):
            out.append(method_group_html(group))
        out.append('</table></div>')
    return out


def method_groups(methods):
    """[[m, ...] of one name], in the order of the first declaration of each name (overloads in
    source order), as the overload groups of the free functions."""
    groups = {}
    for m in methods:
        groups.setdefault(m['name'], []).append(m)
    return list(groups.values())


def method_group_html(ms):
    """The overloads of one method name: one <tbody class="member-row"> (one entry for the
    filter, anchored by the id of the first overload). Shared description: one row, the
    signatures stacked. Different descriptions: one <tr> per overload (anchored by its own id)
    so that each description stays next to its signature; a common trailing clause is
    written once in a last row."""
    m0, many = ms[0], len(ms) > 1
    name = m0['name']

    def sig_block(m, weighted):
        sigs = [short_sig(m['signature'], m.get('owner'))] + \
            [short_sig(v['signature'], m.get('owner')) for v in m.get('variants') or []]
        code = '<br>'.join(f'<code>{method_sig_html(x, name, weighted and k == 0)}</code>' for k, x in enumerate(sigs))
        return f'<a class="m-anchor" href="#{esc(m["id"])}">{code}</a>'

    def src(m):
        return f' <a class="m-src" data-pagefind-ignore href="{esc(m["source_url"])}">src</a>' if m.get('source_url') else ''

    descs = [m.get('description') for m in ms]
    shared = len(set(descs)) == 1
    badge = f'<span class="badge badge-n m-n" data-pagefind-ignore>{len(ms)} overloads</span>' if many else ''
    head = (f'<tbody class="member-row{" member-overloads" if many else ""}" id="{esc(m0["id"])}" '
            f'data-name="{esc(name)}">')
    if shared:
        sigs = ''.join(('<div class="m-ov">' if k == 0 else f'<div class="m-ov" id="{esc(m["id"])}">')
                       + sig_block(m, k == 0) + '</div>' for k, m in enumerate(ms))
        return (head + f'<tr><td class="m-sig">{sigs}</td><td class="m-brief">{esc(descs[0])}{badge}'
                f'{src(m0)}</td></tr></tbody>')
    own, common = split_descriptions(descs)
    rows = []
    for k, m in enumerate(ms):
        oid = '' if k == 0 else f' id="{esc(m["id"])}"'
        rows.append(f'<tr class="m-ov"{oid}><td class="m-sig">{sig_block(m, k == 0)}</td>'
                    f'<td class="m-brief">{esc(own[k])}{badge if k == 0 else ""}{src(m)}</td></tr>')
    if common:
        rows.append(f'<tr class="m-common"><td class="m-sig"></td><td class="m-brief">{esc(common)}</td></tr>')
    return head + ''.join(rows) + '</tbody>'


def struct_html(name, t, site):
    s = t.get('struct') or {}
    fields, methods = s.get('fields') or [], s.get('methods') or []
    if not fields and not methods:
        return ''
    what = 'primary template' if t.get('family_of') else 'struct'
    out = ['<h2 id="members">Fields and methods</h2>',
           f'<p class="muted">Members of the {what} <code>{esc(s.get("compound") or t["canonical"])}</code>. '
           'Most of what you do with a CGP type goes through the free functions listed below.</p>',
           '<div class="members">']
    out += member_tables([f for f in fields if not f.get('inherited_from')],
                         [m for m in methods if not m.get('inherited_from')])
    bases = list(dict.fromkeys([m['inherited_from'] for m in fields + methods if m.get('inherited_from')]))
    for b in bases:
        bf = [f for f in fields if f.get('inherited_from') == b]
        bm = [m for m in methods if m.get('inherited_from') == b]
        out.append(f'<details class="inherited"><summary>Inherited from <code>{esc(site.via_label(b))}</code> '
                   f'({len(bf) + len(bm)} members)</summary>')
        out += member_tables(bf, bm, ids=False)
        out.append('</details>')
    out.append('</div>')
    return ''.join(out)


SECTION_LABELS = {'get-started': 'Get started', 'understand': 'Understand', 'how-to': 'How-to',
                  'examples': 'Examples'}


def guide_url(path, rel='../../'):
    """content page a/b.md -> the generated page, relative to a reference page."""
    return rel + path[:-3] + '/index.html'


def guides_html(t):
    """The guide pages citing the type (api.json `guides`), one line per section. Not
    indexed by the search: guide titles would make the type page outrank the guides."""
    guides = t.get('guides') or []
    if not guides:
        return ''
    lines = []
    for sec, label in SECTION_LABELS.items():
        items = [g for g in guides if g['section'] == sec]
        if items:
            links = ''.join(f'<li><a href="{guide_url(g["path"])}">{esc(g["title"])}</a></li>' for g in items)
            lines.append(f'<div class="guides-line"><span class="guides-sec">{label}</span><ul>{links}</ul></div>')
    return (f'<nav class="type-guides" id="guides" aria-label="Guides" data-pagefind-ignore>'
            f'<p class="guides-title">Used in these guides ({len(guides)})</p>{"".join(lines)}</nav>')


def link_url(link):
    """Target of api.json (content_links, tasks) -> URL relative to a reference page."""
    page = f'../{link["type"]}/index.html' if link['type'] else f'../functions/{link["group"]}/index.html'
    return page + '#' + link['id'] if link.get('id') else page


def tasks_html(t):
    """Common operations on the type (api.json `tasks`, from types.yaml), one line per task.
    Not indexed by the search, like the guides: the names belong to their own entries."""
    tasks = t.get('tasks') or []
    if not tasks:
        return ''
    lines = []
    for task in tasks:
        links = ''.join(f'<li><a href="{link_url(u["link"])}"><code>{esc(u["code"])}</code></a></li>' for u in task['use'])
        guide = task.get('guide')
        see = (f'<span class="task-guide"> (guide: <a href="{guide_url(guide["path"])}">{esc(guide["title"])}</a>)</span>'
               if guide else '')
        lines.append(f'<div class="guides-line"><span class="guides-sec">{esc(task["do"])}</span><span><ul>{links}</ul>{see}</span></div>')
    return (f'<nav class="type-guides type-tasks" id="tasks" aria-label="Common tasks" data-pagefind-ignore>'
            f'<p class="guides-title">Common tasks</p>{"".join(lines)}</nav>')


def figures_html(t):
    # diagrams of the type (types.yaml, src relative to content/assets, copied to assets/);
    # not indexed: a caption citing "norm" would outrank the function itself in the search
    # the image opens full size on click (lightbox of site.js, or the SVG itself without JS)
    return ''.join(f'<figure class="figure" data-pagefind-ignore><a class="figure-zoom" href="../../assets/{esc(f["src"])}" '
                   f'aria-label="Open the figure full size"><img loading="lazy"{figure_size_style(ASSETS / f["src"])} src="../../assets/{esc(f["src"])}" '
                   f'alt="{esc(f["caption"])}"></a><figcaption>{esc(f["caption"])}'
                   f'<span class="figure-hint"> Tap to enlarge.</span></figcaption></figure>'
                   for f in t.get('figures') or [])


def type_page(name, t, site):
    s = t.get('struct') or {}
    family = bool(t.get('family_of'))
    takes, returns, ops = t.get('takes') or [], t.get('returns') or [], t.get('operators') or []
    own = lambda es: [e for e in es if not e.get('shared')]  # noqa: E731
    src = s.get('source_url')
    head = ['<div class="type-header">',
            f'<p class="type-lead">{esc(t.get("short"))}</p>']
    lines = []
    if family:
        links = ', '.join(f'<a href="../{m}/index.html"><code>{esc(m)}</code></a>' if m in site.types
                          else f'<code>{esc(m)}</code>' for m in t['family_of'])
        lines.append(f'<p class="type-line"><span class="type-line-label">Applies to:</span> {links}</p>')
    if s.get('bases'):
        lines.append('<p class="type-line"><span class="type-line-label">Derives from:</span> '
                     + ', '.join(site.type_ref(b) for b in s['bases']) + '</p>')
    head += lines
    head.append('<div class="type-meta">')
    if family:
        head.append(f'<span class="type-canonical">template <code>{esc(t["canonical"])}</code></span>')
    elif t.get('canonical') and t['canonical'] != name:
        head.append(f'<span class="type-canonical">alias of <code>{esc(t["canonical"])}</code></span>')
    if s.get('module'):
        head.append(f'<span class="chip">module {esc(s["module"])}</span>')
    if src:
        head.append(f'<a class="chip chip-link" href="{esc(src)}">source: {esc(s.get("file", "").split("/")[-1])}</a>')
    head.append('</div><div class="type-stats">'
                f'<a href="#takes"><strong>{len(takes)}</strong> functions take it</a>'
                f'<a href="#returns"><strong>{len(returns)}</strong> return it</a>'
                f'<a href="#operators"><strong>{len(ops)}</strong> operators</a></div></div>')
    body = [''.join(head), tasks_html(t), guides_html(t), figures_html(t)]
    shared_html, n_shared = shared_blocks(name, t, site)
    n_members = len(s.get('fields') or []) + len(s.get('methods') or [])
    total = len(own(takes)) + len(own(returns)) + len(own(ops)) + n_shared + n_members
    if total:
        # before the members, so that it is on screen on arrival; matches fields and methods too
        body.append('<div class="fn-filter-bar" data-pagefind-ignore>'
                    f'<input id="fn-filter" type="search" placeholder="Filter the members and functions of {esc(name)} '
                    '(name, signature, description)" autocomplete="off" spellcheck="false">'
                    '<span id="fn-filter-count" class="fn-filter-count"></span></div>')
    body.append(struct_html(name, t, site))
    body.append(shared_html)
    def none(es):
        return '<p class="muted">' + ('None besides the shared functions above.' if any(e.get('shared') for e in es)
                                      else 'None.') + '</p>'
    none_t, none_r, none_o = none(takes), none(returns), none(ops)
    used = set()

    def sec(rel, es):
        return split(own(es), site, lambda f: (f.get('home') or {}).get('type') == name
                     and f['home'].get('rel') == rel, used)
    takes, returns, ops = sec('takes', takes), sec('returns', returns), sec('operators', ops)
    word = f'any {esc(name)}' if family else f'a {esc(name)}'
    body.append(f'<h2 id="takes">Functions taking {word}</h2>')
    body.append(grouped(*takes, site, '', 'takes', family) if any(takes) else none_t)
    body.append(f'<h2 id="returns">Functions returning {word}</h2>')
    body.append(grouped(*returns, site, '-r', 'returns', family) if any(returns) else none_r)
    body.append('<h2 id="operators">Operators</h2>')
    if any(ops):
        n_ops = len(ops[0]) + len(ops[1])
        body.append(f'<details class="fn-operators"><summary>Show the {n_ops} operators '
                    '(<code>+</code>, <code>-</code>, <code>*</code>, <code>==</code>, ...)</summary>'
                    + flat(*ops, site, '-o', family) + '</details>')
    else:
        body.append(none_o)
    html_body = '<div class="ref-page">' + ''.join(body) + '</div>'
    assert '\n\n' not in html_body
    check_ids(name, html_body)
    desc = (t.get('short') or '').replace('"', "'")
    return (f'---\ntitle: "{name}"\nsection: Reference\ngroup: "{site.group_of(name)}"\ndescription: "{desc}"\n'
            f'pagetype: reference\n---\n\n# {name}\n\n{html_body}\n')


def check_ids(page, body):
    """Every id of a generated page is unique (anchors are model ids, shared by both sites)."""
    ids = re.findall(r'\sid="([^"]+)"', body)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    assert not dup, f'{page}: duplicate ids {dup[:5]}'


def group_page(g, site):
    """Page of a group of functions that appear on no type page (function_groups.yaml)."""
    entries = g['functions']
    body = (f'<div class="ref-page"><div class="type-header"><p class="type-lead">{esc(g["short"])}</p></div>'
            '<div class="fn-filter-bar" data-pagefind-ignore>'
            f'<input id="fn-filter" type="search" placeholder="Filter these functions (name, signature, description)" '
            'autocomplete="off" spellcheck="false"><span id="fn-filter-count" class="fn-filter-count"></span></div>'
            + grouped(*split(entries, site, lambda f: True, set()), site, '', 'fn') + '</div>')
    assert '\n\n' not in body
    check_ids(g['name'], body)
    desc = g['short'].replace('"', "'")
    return (f'---\ntitle: "{g["title"]}"\nsection: Reference\ngroup: "{g.get("under") or UTILITIES}"\ndescription: "{desc}"\n'
            f'pagetype: reference\n---\n\n# {g["title"]}\n\n{body}\n')


def function_count(t):
    """Number of distinct functions that take the type, return it, or are its operators (a
    function in several lists counts once). Same definition as the Starlight reference index
    (renderers/starlight/src/lib/api.mjs, functionCount)."""
    return len({e['id'] for k in ('takes', 'returns', 'operators') for e in (t.get(k) or [])})


def function_card(name, g):
    return (f'<a class="type-card type-card-functions" href="functions/{name}/index.html">'
            f'<span class="type-card-name">{esc(g["title"])}</span>'
            f'<span class="type-card-desc">{esc(g["short"])}</span>'
            f'<span class="type-card-count">{len(g["functions"])} functions</span></a>')


def index_page(site):
    rows = ['<div class="ref-index">']
    for g, names, groups in site.menu:
        gid = re.sub(r'[^a-z0-9]+', '-', g.lower()).strip('-')
        rows.append(f'<h2 id="{gid}">{esc(g)}</h2>')
        if not names:
            rows.append('<p class="muted">Functions that take or return none of the types of the reference.</p>')
        rows.append('<div class="type-cards">')
        for n in names:
            t = site.types[n]
            nf = function_count(t)
            fam = t.get('family_of')
            extra = (f'<span class="type-card-family">applies to {esc(", ".join(fam))}</span>' if fam else '')
            rows.append(f'<a class="type-card{" type-card-fam" if fam else ""}" href="{n}/index.html">'
                        f'<span class="type-card-name">{esc(n)}</span>'
                        f'<span class="type-card-desc">{esc(t.get("short"))}</span>{extra}'
                        f'<span class="type-card-count">{nf} functions</span></a>')
        rows += [function_card(name, site.function_groups[name]) for name in groups]
        rows.append('</div>')
    rows.append('</div>')
    body = ''.join(rows)
    assert '\n\n' not in body
    return ('---\ntitle: "Reference"\nsection: Reference\ngroup: ""\n'
            'description: "Every CGP type with the free functions that take it, return it, and its operators."\n'
            'pagetype: reference-index\n---\n\n# Reference\n\n'
            'CGP is mostly made of free functions (`norm(v)`, `draw(drawable, environment)`) rather than methods: '
            'each type page lists what you can *do* with the type, grouped by intent. '
            'The functions written once for every size of vector or matrix are on the pages '
            '`vecN` and `matN`.\n\n' + body + '\n')


# Workaround (lhtml 3.0.1, lhtml/source.py _matches): when a Markdown page has no
# fenced block after the current position, the code pattern is searched again
# from each zone (HTML tag) to the end of the text: quadratic, 70 s for these
# pages. A fence at the very end, inside an HTML comment (not rendered), makes
# the search find it once.
SCAN_SENTINEL = '\n<!-- scan sentinel (see gen_reference.py)\n~~~\n~~~\n-->\n'


def main(api_path, out_src):
    api = json.loads(Path(api_path).read_text(encoding='utf-8'))
    site = Site(api)
    ref = Path(out_src) / 'reference'
    ref.mkdir(parents=True, exist_ok=True)
    (ref / 'index.md.j2').write_text(index_page(site) + SCAN_SENTINEL, encoding='utf-8')
    for n in site.order:
        d = ref / n
        d.mkdir(exist_ok=True)
        (d / 'index.md.j2').write_text(type_page(n, site.types[n], site) + SCAN_SENTINEL, encoding='utf-8')
    for name, g in site.function_groups.items():
        d = ref / 'functions' / name
        d.mkdir(parents=True, exist_ok=True)
        (d / 'index.md.j2').write_text(group_page(g, site) + SCAN_SENTINEL, encoding='utf-8')
    # order of the menu and of previous / next: in each group, its types, then its pages of functions
    return ['reference/index.html'] + [p for _, names, groups in site.menu
                                       for p in [f'reference/{n}' for n in names] + [f'reference/functions/{g}' for g in groups]]


if __name__ == '__main__':
    print('\n'.join(main(sys.argv[1], sys.argv[2])))
