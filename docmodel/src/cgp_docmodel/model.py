"""Assemble the API model (build/api.json) from the Doxygen records and the editorial files.

The output is deterministic: the same sources and editorial files always give byte-identical
JSON (no timestamp, sorted lists). This makes the golden snapshots a reliable audit of any
change.

Provenance fields, so that every value can be traced:
  description_source  curated (descriptions.yaml) | source (C++ comment) | missing
  category_source     curated (annotations.yaml)  | heuristic
  category_rule       name of the heuristic rule (categories.RULES) when heuristic
  params_source       header (names/defaults read in the .hpp declaration) | doxygen
  excluded            functions left out of the model, with the reason
"""

import json
import subprocess

from . import categories, editorial, relations
from .content import Vocabulary
from .cpptypes import format_canonical
from .doxygen import DoxygenXML

SCHEMA_VERSION = "1.7"


def _git_info(path) -> dict:
    def git(*args):
        r = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain", "--", "."))}


def _ancestors(xml: DoxygenXML, target, depth=0) -> list:
    compound = xml.find_struct(target)
    if compound is None or depth > 8:
        return []
    out = []
    for b in xml.bases(compound):
        out.append(b)
        out += _ancestors(xml, b, depth + 1)
    return out


def _known_type(xml: DoxygenXML, target) -> bool:
    """A canonical type of types.yaml must exist: alias target, specialization or plain struct."""
    if format_canonical(target) in set(xml.aliases().as_dict().values()) | {
            format_canonical(xml.aliases().canonical(a)) for a in xml.aliases().aliases}:
        return True
    compound = xml.find_struct(target)
    if compound is None:
        return False
    return not target[1] or "<" in compound  # with arguments, a bare primary template is not enough


def build_model(paths, doxygen_version: str = "", doxygen_warnings=()) -> tuple:
    """Return (model, editorial, xml, errors). Does not write anything."""
    source = _git_info(paths.source)
    xml = DoxygenXML(paths.doxygen_xml, source_ref=source["commit"] or "main")
    aliases = xml.aliases()
    ed = editorial.load(paths)
    errors = list(ed.errors)
    targets = editorial.type_targets(ed)
    struct_bases = {t[0] for t in targets.values()}

    funcs, excluded, collisions = xml.free_functions()
    errors += collisions
    funcs.sort(key=lambda f: (f["module"], f["file"], f["line"], f["key"]))
    relations.group_variants(funcs)

    for f in funcs:
        curated = ed.descriptions.get(f["key"])
        f["description"] = curated or f["brief"] or None
        f["description_source"] = "curated" if curated else ("source" if f["brief"] else "missing")
        if f["key"] in ed.annotations:
            f["category"], f["category_source"], f["category_rule"] = ed.annotations[f["key"]], "curated", None
        else:
            f["category"], f["category_rule"] = categories.classify(f, aliases, struct_bases)
            f["category_source"] = "heuristic"

    types, matching = {}, {}
    for name, target in targets.items():
        t = ed.types[name]
        family_of = t.get("family_of")
        known = xml.find_struct(target) is not None if family_of else _known_type(xml, target)
        if not known:
            errors.append(f"types.yaml: '{name}' canonical '{t['canonical']}' is not a CGP type")
        for member in family_of or []:
            if member not in targets:
                errors.append(f"types.yaml: family '{name}' lists '{member}', which is not a documented type")
        struct = xml.struct(target)
        if struct:
            struct["methods"].sort(key=lambda m: (m["inherited_from"] or "", m["line"], m["key"]))
            struct["methods"] = relations.group_variants(struct["methods"])
            for fl in struct["fields"]:
                fl["id"] = f"field-{fl['name']}"
            for m in struct["fields"] + struct["methods"]:
                curated = ed.members.get(m["key"])
                m["description"] = curated or m["brief"] or None
                m["description_source"] = "curated" if curated else ("source" if m["brief"] else "missing")
        other_bases = {tg[0] for n, tg in targets.items() if ed.types[n].get("family_of") and n != name}
        ancestors = [] if family_of else _ancestors(xml, target)
        matching[name] = (target, bool(family_of), ancestors)
        rels = (relations.family_relations(target, funcs, aliases, other_bases) if family_of
                else relations.type_relations(target, funcs, aliases, ancestors))
        types[name] = {
            "name": name,
            "canonical": format_canonical(target),
            "group": t["group"],
            "short": t["short"],
            "family_of": list(family_of) if family_of else None,
            "figures": [dict(f) for f in t.get("figures") or []],
            "struct": struct,
            **rels,
            "guides": [],  # filled from the content pages by crossrefs.attach
            "tasks": [],  # filled from types.yaml `tasks` by crossrefs.attach_tasks
        }
    relations.mark_shared(types)

    # Functions on no type page: grouped by module (and name) into the pages of function_groups.yaml
    on_pages = {e["id"] for t in types.values() for rel in ("takes", "returns", "operators") for e in t[rel]}
    groups = {g: {"name": g, "title": d["title"], "short": d["short"], "under": d["under"], "functions": []}
              for g, d in ed.function_groups.items() if isinstance(d, dict) and "title" in d and "under" in d}
    for f in funcs:
        if f["primary"] and f["id"] not in on_pages:
            g = editorial.function_group_of(ed.function_groups, f["module"], f["name"])
            if g in groups:
                groups[g]["functions"].append({"id": f["id"]})
            else:
                errors.append(f"function_groups.yaml: {f['key']} (module {f['module']}) is on no type page "
                              f"and its module is in no group")
    for g in groups.values():
        g["functions"].sort(key=lambda e: next(f["key"] for f in funcs if f["id"] == e["id"]))

    # Home of each primary function: the page that documents it in full (relations.choose_home)
    order = {n: i for i, n in enumerate(types)}
    candidates = {}
    for name, t in types.items():
        for rel in ("takes", "returns", "operators"):
            for e in t[rel]:
                if not e["shared"]:
                    candidates.setdefault(e["id"], []).append((name, rel, e, order[name]))
    group_of_fn = {e["id"]: g["name"] for g in groups.values() for e in g["functions"]}

    def index_of(f, name):
        target, family, ancestors = matching[name]
        return relations.param_index(f, target, aliases, family, ancestors)

    for f in funcs:
        if not f["primary"]:
            f["home"] = None
        elif f["id"] in group_of_fn:
            f["home"] = {"type": None, "group": group_of_fn[f["id"]], "rel": "functions"}
        else:
            f["home"] = relations.choose_home(f, candidates.get(f["id"], []), index_of)

    model = {
        "schema_version": SCHEMA_VERSION,
        "library": "cgp-2027",
        "generator": {"doxygen": doxygen_version, "doxygen_warnings": len(doxygen_warnings), "source": source},
        "categories": list(categories.CATEGORIES),
        "aliases": aliases.as_dict(),
        "functions": funcs,
        "excluded": [{"key": k, "reason": r} for k, r in sorted(excluded)],
        "types": types,
        "function_groups": groups,
        "content_links": {},  # filled from the content pages by crossrefs.attach
    }
    return model, ed, xml, errors


def vocabulary(model: dict, xml: DoxygenXML) -> Vocabulary:
    """Every CGP name a page may legitimately cite, and the members of each struct
    (including inherited members)."""
    names = {f["name"] for f in model["functions"]} | set(model["types"]) | set(model["aliases"])
    names |= set(xml.struct_names())
    direct = xml.members_by_struct()
    members = {}
    for struct in direct:
        acc, todo, seen = set(direct[struct]), [struct], set()
        while todo:
            s = todo.pop()
            if s in seen:
                continue
            seen.add(s)
            compound = xml.find_struct((s, ()))
            if compound:
                for b in xml.bases(compound):
                    acc |= direct.get(b[0], set())
                    todo.append(b[0])
        members[struct] = acc
    for tname, t in model["types"].items():  # aliases (vec3, mat4) get the members of their struct
        if t["struct"]:
            members[tname] = {f["name"] for f in t["struct"]["fields"]} | {m["name"] for m in t["struct"]["methods"]}
    return Vocabulary(names=names, members=members, declared=direct)


def dump(model: dict) -> str:
    return json.dumps(model, indent=1, ensure_ascii=False) + "\n"
