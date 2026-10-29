"""Check the hand-written Markdown pages (content/) against the API model.

Every inline code span that looks like a name is resolved (fenced code blocks are not
scanned):
  `norm`, `mesh_primitive_sphere(0.25f)`  -> a function, type, alias or struct name
  `mesh_drawable::model`                  -> `model` must be a member of mesh_drawable
                                             (or of one of its base classes)
  `sphere.texture`, `camera.matrix_view()`-> `texture` / `matrix_view` must be a member of
                                             some CGP struct (the object type is unknown)
Results:
  resolved     recorded in build/content_index.json (name -> pages citing it)
  ignored      matches editorial/content_check.yaml (OpenGL, GLSL, scene template...), or
               the front matter `local_names:` of the page (names of the code of an example)
  unresolved   anything else, reported with page and line
"""

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .header import split_top_level

_SPAN = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_SEGMENT = re.compile(rf"^(?P<name>{_NAME}(?:::{_NAME})*)(?P<call>\s*\(.*\))?$")


@dataclass
class Vocabulary:
    names: set = field(default_factory=set)        # functions, types, aliases, structs
    members: dict = field(default_factory=dict)    # struct -> member names (with inherited ones)
    declared: dict = field(default_factory=dict)   # struct -> member names declared in it (no inherited)

    @property
    def all_members(self) -> set:
        return set().union(*self.members.values()) if self.members else set()


def code_spans(markdown: str):
    """(line number, span text) of inline code spans, outside fenced code blocks."""
    in_fence = False
    for i, line in enumerate(markdown.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence:
            for m in _SPAN.finditer(line):
                yield i, m.group(1).strip()


def references(span: str) -> list:
    """Names to resolve in a span: [('name', x) | ('qualified', T, m) | ('member', m)].

    'norm(v)' -> [('name','norm')]; 'mesh_drawable::model' -> [('qualified','mesh_drawable','model')];
    'sphere.texture' -> [('member','texture')] ('sphere' is a variable of an example);
    'camera().matrix_view()' -> [('name','camera'), ('member','matrix_view')]; 'x + y' -> [].
    """
    segments = split_top_level(span, ".")
    parsed = []
    for seg in segments:
        m = _SEGMENT.match(seg)
        if not m:
            return []
        parsed.append((m.group("name"), m.group("call") is not None))
    (head, head_call), members = parsed[0], parsed[1:]
    refs = []
    parts = head.split("::")
    if len(parts) > 1:
        refs.append(("qualified", "::".join(parts[:-1]), parts[-1]))
    elif head_call or not members:
        refs.append(("name", head))
    refs += [("member", name) for name, _ in members]
    return refs


def _ignored(name: str, ignore: list) -> bool:
    return any(fnmatch.fnmatchcase(name, pat) for pat in ignore)


def resolve(ref, vocab: Vocabulary) -> str | None:
    """The name under which a reference is indexed, or None if it does not resolve."""
    kind = ref[0]
    if kind == "name":
        return ref[1] if ref[1] in vocab.names or ref[1] in vocab.all_members else None
    if kind == "qualified":
        owner, member = ref[1].split("::")[-1], ref[2]
        if member in vocab.members.get(owner, set()):
            return f"{owner}::{member}"
        return None
    if kind == "member":
        return ref[1] if ref[1] in vocab.all_members else None
    raise ValueError(kind)


def check_content(content_dir: Path, vocab: Vocabulary, ignore: list) -> dict:
    """Scan content/**/*.md. Returns
      'refs'       {name: [page...]}            resolved names (build/content_index.json)
      'unresolved' [(page, line, text)]
      'spans'      [(page, span, [(ref, key)])] every span with its resolved references
                   (key None: ignored or unresolved); used by crossrefs.py for the links
                   between the guides and the reference."""
    refs, unresolved, spans = {}, [], []
    for md in sorted(content_dir.rglob("*.md")):
        page = md.relative_to(content_dir).as_posix()
        text = md.read_text(encoding="utf-8")
        # names of the code of an example (its own functions and variables), listed in the
        # front matter `local_names:` of its page: ignored on this page only
        local = [str(n) for n in (front_matter(text).get("local_names") or [])]
        page_ignore = ignore + local
        for line, span in code_spans(text):
            resolved = []
            for ref in references(span):
                shown = ref[1] if ref[0] != "qualified" else f"{ref[1]}::{ref[2]}"
                if _ignored(shown, page_ignore) or (ref[0] == "name" and _ignored(ref[1], page_ignore)):
                    resolved.append((ref, None))
                    continue
                key = resolve(ref, vocab)
                resolved.append((ref, key))
                if key is None:
                    unresolved.append((page, line, shown))
                elif page not in refs.setdefault(key, []):
                    refs[key].append(page)
            if resolved:
                spans.append((page, span, resolved))
    return {"refs": dict(sorted(refs.items())), "unresolved": unresolved, "spans": spans}


def front_matter(markdown: str) -> dict:
    """The YAML front matter of a page ({} if none)."""
    if not markdown.startswith("---"):
        return {}
    parts = markdown.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1]) or {}
    return data if isinstance(data, dict) else {}
