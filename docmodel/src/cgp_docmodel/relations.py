"""Relations between documented types and functions, and grouping of overload variants.

Variants: two overloads that differ only by const-ness (operator[] const / operator[],
get(T const&) / get(T&)) say the same thing to a reader. The const one is kept as the
"primary" entry and the other is attached to it in "variants"; lists shown to readers
only contain primaries.
"""

import re

from .cpptypes import AliasTable, format_canonical


def variant_group(f: dict) -> str:
    """Key shared by overloads that differ only by const qualifiers."""
    key = re.sub(r"\bconst\b", "", f["key"])
    return f"{f['namespace']}|{re.sub(r'\s+', '', key)}"


def group_variants(funcs: list) -> list:
    """Mark primaries and attach variants. Returns the list of primary records."""
    groups = {}
    for f in funcs:
        groups.setdefault(variant_group(f), []).append(f)
    primaries = []
    for members in groups.values():
        # most const-qualified version first, then the key itself: deterministic choice
        members.sort(key=lambda f: (-f["key"].count("const"), f["key"]))
        head, rest = members[0], members[1:]
        head["primary"] = True
        head["variants"] = [{"id": v["id"], "signature": v["signature"]} for v in rest]
        for v in rest:
            v["primary"] = False
            v["variants"] = []
            v["variant_of"] = head["id"]
        primaries.append(head)
    return primaries


def _relate(f, target, aliases):
    """('operators' | 'takes' | 'returns', generic) or None for one function and one type."""
    tp = f["tparams"]
    hits = [m for m in (aliases.match(p["type"], target, tp) for p in f["params"]) if m]
    rm = aliases.match(f["ret"], target, tp) if f["ret"] else None
    if f["name"].startswith("operator") and (hits or rm):
        return "operators", "exact" not in hits + [rm]
    if hits:
        return "takes", "exact" not in hits
    if rm:
        return "returns", rm == "generic"
    return None


def type_relations(target, funcs: list, aliases: AliasTable, ancestors=()) -> dict:
    """takes / returns / operators lists for one documented type (primaries only).

    `ancestors` are the canonical base classes of the type (quaternion -> numarray_stack<float,4>):
    a function on a base applies to the type too and is listed with "via" = that base.
    Functions that return a base are not listed (a vec4 is not a quaternion).
    """
    out = {"takes": [], "returns": [], "operators": []}
    for f in funcs:
        if not f.get("primary", True):
            continue
        r = _relate(f, target, aliases)
        via = None
        if r is None:
            for anc in ancestors:
                r = _relate(f, anc, aliases)
                if r and r[0] != "returns":
                    via = format_canonical(anc)
                    break
                r = None
        if r:
            out[r[0]].append({"id": f["id"], "generic": r[1], "via": via})
    return out


def family_relations(target, funcs: list, aliases: AliasTable, other_family_bases=()) -> dict:
    """takes / returns / operators of a family (vecN = numarray_stack<T,N>): the functions
    written once for every size, i.e. generic over all the template arguments.

    A function that only returns a member of the family while taking a member of another
    family (get<idx>(matrix_stack) returns a row vector) belongs to that other family only."""
    base, args = target
    out = {"takes": [], "returns": [], "operators": []}
    for f in funcs:
        if not f.get("primary", True):
            continue
        tp = f["tparams"]
        hit = any(aliases.match_family(p["type"], base, len(args), tp) for p in f["params"])
        ret = bool(f["ret"]) and aliases.match_family(f["ret"], base, len(args), tp) \
            and not any(aliases.canonical(p["type"])[0] in other_family_bases for p in f["params"])
        rel = ("operators" if f["name"].startswith("operator") and (hit or ret)
               else "takes" if hit else "returns" if ret else None)
        if rel:
            out[rel].append({"id": f["id"], "generic": True, "via": None, "shared": None})
    return out


def mark_shared(types: dict) -> None:
    """On member types, flag the generic entries already listed on a family page.

    An entry is shared with a family only if the type is a member of that family (vec3 in
    vecN), or reaches a member through a base class (quaternion via numarray_stack<float,4>,
    i.e. vec4). A matrix-vector product is generic for both families: on the vec3 page it
    stays listed in full, since vec3 is not a member of matN.
    """
    families = {name: {e["id"] for rel in ("takes", "returns", "operators") for e in t[rel]}
                for name, t in types.items() if t.get("family_of")}
    canonical_to_type = {t["canonical"]: name for name, t in types.items()}
    for name, t in types.items():
        for rel in ("takes", "returns", "operators"):
            for e in t[rel]:
                e.setdefault("shared", None)
                if t.get("family_of") or not e["generic"]:
                    continue
                member = canonical_to_type.get(e["via"]) if e["via"] else name
                for fam in sorted(families):
                    if member in types[fam]["family_of"] and e["id"] in families[fam]:
                        e["shared"] = fam
                        break


def param_index(f, target, aliases: AliasTable, family=False, ancestors=()) -> int:
    """Position of the first parameter of `f` of the type `target` (a family when `family`,
    or one of its base classes `ancestors`); len(params) if none."""
    tp = f["tparams"]
    for i, p in enumerate(f["params"]):
        if family:
            if aliases.match_family(p["type"], target[0], len(target[1]), tp):
                return i
        elif aliases.match(p["type"], target, tp) or any(aliases.match(p["type"], a, tp) for a in ancestors):
            return i
    return len(f["params"])


def choose_home(f, candidates: list, index_of) -> dict | None:
    """The page where a primary function is documented in full and linked to (guides, links
    of the content pages): one of the `candidates` [(type, rel, entry)] listing it in full
    (entry not shared).

    construct functions (factories) live on the type they return (mesh_primitive_sphere ->
    mesh); the others on the type of their first parameter of a documented type
    (draw(mesh_drawable, environment) -> mesh_drawable). Ties: exact before generic, direct
    before via a base class, then the order of types.yaml. `index_of(f, type)` gives the
    parameter position (param_index)."""
    if not candidates:
        return None
    n = len(f["params"])

    def rank(c):
        name, rel, e, order = c
        factory = 0 if (f["category"] == "construct" and rel == "returns") else 1
        pos = n if rel == "returns" else index_of(f, name)
        return (factory, pos, e["generic"], e["via"] is not None, order)

    name, rel, _, _ = min(candidates, key=rank)
    return {"type": name, "group": None, "rel": rel}
