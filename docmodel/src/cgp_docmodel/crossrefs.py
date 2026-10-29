"""Links between the content pages (guides) and the reference, stored in api.json.

They reuse the resolution of the content check (content.check_content): every inline code
span of content/*.md and the names it resolves to. From it:

  types[T].guides  the guide pages citing T, one of its members, or a function whose home
                   page is T; ordered by section (get-started, understand, how-to,
                   examples), then `order:` of the front matter, then path.
  content_links    inline code span (exact text) -> its target in the reference, for the
                   renderers to turn the span into a link:
                   {kind: type | function | method | field, type, group, rel, id}

Names of `no_link` (editorial/content_check.yaml: `name`, `size`) are never linked. Only
references with exactly one target are used: `draw` (overloads documented on several
pages) or `sphere.model` (a member declared by several structs) get no target, and a span
holding several references (`camera().matrix_view()`) gets no link.
"""

import fnmatch
from pathlib import Path

from .content import front_matter, references
from .header import split_top_level

SECTIONS = ("get-started", "understand", "how-to", "examples")


def _short(compound: str) -> str:
    return compound.split("::")[-1].split("<")[0].strip()


class Targets:
    """Target in the reference of one resolved reference of the content check."""

    def __init__(self, model: dict, vocab, no_link=()):
        self.no_link = list(no_link)
        self.types = model["types"]
        self.vocab = vocab
        self.functions = {}  # name -> primaries with a home, in model order
        for f in model["functions"]:
            if f["primary"] and f.get("home"):
                self.functions.setdefault(f["name"], []).append(f)
        by_struct = {}
        for name, t in self.types.items():
            if t["struct"] and not t.get("family_of"):
                by_struct.setdefault(_short(t["struct"]["compound"]), []).append(name)
        self.by_struct = by_struct

    def owner_type(self, owner: str) -> str | None:
        """Documented type of an owner name: the type itself, or the only type of that struct."""
        if owner in self.types:
            return owner
        hits = self.by_struct.get(owner, [])
        return hits[0] if len(hits) == 1 else None

    def member(self, type_name: str, member: str) -> dict | None:
        """First field, else first method (overloads: the first one), named `member` on the
        page of `type_name` (own or inherited member)."""
        s = self.types[type_name]["struct"]
        if not s:
            return None
        for fl in s["fields"]:
            if fl["name"] == member:
                return {"kind": "field", "type": type_name, "group": None, "rel": None, "id": fl["id"]}
        for m in s["methods"]:
            if m["name"] == member:
                return {"kind": "method", "type": type_name, "group": None, "rel": None, "id": m["id"]}
        return None

    def function(self, name: str) -> dict | None:
        """Function name -> its home page if all its overloads share one (the first overload)."""
        fs = self.functions.get(name) or []
        if not fs or len({(f["home"]["type"], f["home"]["group"]) for f in fs}) != 1:
            return None
        return {"kind": "function", **fs[0]["home"], "id": fs[0]["id"]}

    def unique_member(self, name: str) -> dict | None:
        declaring = {s for s, names in self.vocab.declared.items() if name in names}
        if len(declaring) != 1:
            return None
        owner = self.owner_type(declaring.pop())
        return self.member(owner, name) if owner else None

    def of(self, ref, key) -> dict | None:
        if key is None:
            return None
        kind = ref[0]
        if kind == "qualified":
            owner = self.owner_type(ref[1].split("::")[-1])
            return self.member(owner, ref[2]) if owner else None
        name = ref[1]
        if any(fnmatch.fnmatchcase(name, pat) for pat in self.no_link):
            return None
        if kind == "name":
            if name in self.types:
                return {"kind": "type", "type": name, "group": None, "rel": None, "id": None}
            if name in self.functions:
                return self.function(name)
            if name in self.vocab.names:  # an alias or a struct without a page
                return None
        return self.unique_member(name)

    def in_type(self, span: str, type_name: str) -> dict | None:
        """Target of a code span of the `tasks` of a type: its first name, looked up first on the
        page of the type (`model.translation` -> field model, `draw(shape, environment)` -> the
        draw overload whose home is the type), then on the page of its family (`normalize` of
        vec3 -> vecN), then like a span of a guide page."""
        refs = references(split_top_level(span, ".")[0])
        if len(refs) != 1:
            return None
        kind, name = refs[0][0], refs[0][-1]
        if kind == "qualified":
            owner = self.owner_type(refs[0][1].split("::")[-1])
            return self.member(owner, name) if owner else None
        here = self.member(type_name, name)
        if here:
            return here
        pages = [type_name] + [n for n, t in self.types.items() if type_name in (t.get("family_of") or [])]
        homed = sorted((f for f in self.functions.get(name, []) if f["home"]["type"] in pages),
                       key=lambda f: pages.index(f["home"]["type"]))
        if homed:
            return {"kind": "function", **homed[0]["home"], "id": homed[0]["id"]}
        if name in self.types:
            return {"kind": "type", "type": name, "group": None, "rel": None, "id": None}
        return self.function(name) or self.unique_member(name)


def page_info(content_dir: Path, page: str) -> dict | None:
    """{path, title, section, order} of a guide page (a page of SECTIONS), else None."""
    section = page.split("/")[0]
    if section not in SECTIONS or "/" not in page:
        return None
    fm = front_matter((content_dir / page).read_text(encoding="utf-8"))
    order = fm.get("order")
    return {"path": page, "title": str(fm.get("title") or page), "section": section,
            "order": order if isinstance(order, int) else 1000}


def attach(model: dict, spans: list, vocab, content_dir: Path, no_link=()) -> None:
    """Fill types[T].guides and content_links from the spans of content.check_content.
    `no_link`: patterns of names never linked (editorial/content_check.yaml)."""
    targets = Targets(model, vocab, no_link)
    guides, links = {}, {}
    infos = {}
    for page, span, resolved in spans:
        found = [targets.of(ref, key) for ref, key in resolved]
        for t in found:
            if t and t["type"]:
                if page not in infos:
                    infos[page] = page_info(content_dir, page)
                if infos[page]:
                    guides.setdefault(t["type"], set()).add(page)
        if len(found) == 1 and found[0]:
            links[span] = found[0]
    for name, t in model["types"].items():
        pages = sorted((infos[p] for p in guides.get(name, ())),
                       key=lambda i: (SECTIONS.index(i["section"]), i["order"], i["path"]))
        t["guides"] = [{"path": i["path"], "title": i["title"], "section": i["section"]} for i in pages]
    model["content_links"] = dict(sorted(links.items()))


def attach_tasks(model: dict, ed_types: dict, vocab, content_dir: Path) -> list:
    """Fill types[T].tasks from types.yaml `tasks` (format checked by editorial.py). Returns
    the errors: a code span with no target in the reference, a guide that is not a guide page."""
    targets = Targets(model, vocab)
    errors = []
    for name, t in model["types"].items():
        tasks = []
        for task in ed_types.get(name, {}).get("tasks") or []:
            use = []
            for code in task["use"]:
                link = targets.in_type(code, name)
                if link is None:
                    errors.append(f"types.yaml: '{name}' task '{task['do']}': `{code}` links to nothing in the reference")
                use.append({"code": code, "link": link})
            guide = task.get("guide")
            info = page_info(content_dir, guide) if guide else None
            if guide and info is None:
                errors.append(f"types.yaml: '{name}' task '{task['do']}': '{guide}' is not a guide page")
            tasks.append({"do": task["do"], "use": use,
                          "guide": {k: info[k] for k in ("path", "title", "section")} if info else None})
        t["tasks"] = tasks
    return errors
