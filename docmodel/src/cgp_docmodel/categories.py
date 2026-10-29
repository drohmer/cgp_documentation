"""Heuristic editorial category of a free function.

The rules are an ordered list: the first rule whose predicate holds gives the category,
and its name is stored in api.json ("category_rule") so that every classification can be
traced back to the rule that produced it. A curated value in editorial/annotations.yaml
always wins over these rules.

Covered by tests/unit/test_categories.py (one case per rule).
"""

import re

from .cpptypes import AliasTable

CATEGORIES = ("construct", "transform", "compute", "draw", "convert", "io", "access", "operator", "other")

SCALARS = {"float", "double", "int", "bool", "char", "short", "long", "long long", "size_t",
           "unsigned", "unsigned int", "unsigned char", "unsigned long", "unsigned short", "std::string"}


def _is_scalar(base: str, scalars: set) -> bool:
    return base in scalars or base.startswith("GL")  # GLuint, GLenum, GLint... are integers


def _ctx(f: dict, aliases: AliasTable, struct_bases: set) -> dict:
    tparams = set(f["tparams"])
    ret = aliases.canonical(f["ret"]) if f["ret"] not in ("", "void") else None
    params = [aliases.canonical(p["type"]) for p in f["params"]]
    return {"name": f["name"], "ret": ret, "params": params,
            "scalars": SCALARS | tparams, "struct_bases": struct_bases}


# (rule name, category, predicate(ctx)) - order matters
RULES = [
    ("name:operator", "operator", lambda c: c["name"].startswith("operator")),
    ("name:draw*", "draw", lambda c: c["name"].startswith("draw")),
    ("name:io", "io", lambda c: re.search(r"(^|_)(read|load|save|write|export|import)(_|$)", c["name"]) is not None),
    ("name:convert", "convert", lambda c: c["name"] in ("str", "type_str")
                                       or c["name"].startswith(("to_", "convert", "from_", "str_"))
                                       or c["name"].endswith("_to_string")),
    ("name:access", "access", lambda c: c["name"] in ("get", "ptr", "size", "size_in_memory", "at", "data", "element")
                                     or c["name"].startswith(("get_", "is_", "check_"))),
    ("name:factory", "construct", lambda c: c["name"].startswith(("mesh_primitive", "curve_primitive", "create_", "build_", "initialize"))),
    ("returns:void", "other", lambda c: c["ret"] is None),
    ("returns:scalar", "compute", lambda c: _is_scalar(c["ret"][0], c["scalars"])),
    ("returns:same-type-as-a-parameter", "transform", lambda c: c["ret"] in c["params"]),
    ("returns:documented-type-from-scalars", "construct",
     lambda c: c["ret"][0] in c["struct_bases"] and all(_is_scalar(p[0], c["scalars"]) or p[0] == "numarray_stack" for p in c["params"])),
    ("fallback", "compute", lambda c: True),
]


def classify(f: dict, aliases: AliasTable, struct_bases: set) -> tuple:
    """(category, rule name) for a free-function record."""
    c = _ctx(f, aliases, struct_bases)
    for rule, category, pred in RULES:
        if pred(c):
            return category, rule
    raise AssertionError("unreachable: the fallback rule always matches")
