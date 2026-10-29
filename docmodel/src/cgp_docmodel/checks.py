"""Checks run by `cgp-docmodel check`. Each check returns a list of messages (empty = pass).

Errors make the command fail; warnings are reported only (or fail with --strict).
"""

import json

import jsonschema


def schema_errors(model: dict, schema_path) -> list:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    return [f"schema: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(model), key=lambda e: list(map(str, e.absolute_path)))][:50]


def invariant_errors(model: dict) -> list:
    """Structural invariants that must always hold, whatever the CGP sources."""
    errs = []
    ids = [f["id"] for f in model["functions"]]
    if len(ids) != len(set(ids)):
        errs.append("functions: duplicate ids")
    keys = [(f["namespace"], f["key"]) for f in model["functions"]]
    if len(keys) != len(set(keys)):
        errs.append("functions: duplicate (namespace, key): declaration/definition not merged")
    by_id = {f["id"]: f for f in model["functions"]}
    for name, t in model["types"].items():
        for rel in ("takes", "returns", "operators"):
            for e in t[rel]:
                f = by_id.get(e["id"])
                if f is None:
                    errs.append(f"types.{name}.{rel}: unknown id {e['id']}")
                elif not f["primary"]:
                    errs.append(f"types.{name}.{rel}: {f['key']} is a variant, not a primary")
            for e in t[rel]:
                if e["shared"] and not (model["types"].get(e["shared"]) or {}).get("family_of"):
                    errs.append(f"types.{name}.{rel}: shared with unknown family {e['shared']}")
                elif e["shared"] and name not in model["types"][e["shared"]]["family_of"] and not e["via"]:
                    errs.append(f"types.{name}.{rel}: shared with {e['shared']} but not one of its members")
        if not (t["takes"] or t["returns"] or t["operators"] or t["struct"]):
            errs.append(f"types.{name}: no struct and no function (wrong canonical type in types.yaml?)")
    for f in model["functions"]:
        h = f["home"]
        if f["primary"] and h is None:
            errs.append(f"{f['key']}: primary function without home page")
        elif h and h["type"] is not None:
            listed = [e for e in model["types"].get(h["type"], {}).get(h["rel"], []) if e["id"] == f["id"]]
            if not listed or listed[0]["shared"]:
                errs.append(f"{f['key']}: home {h['type']}.{h['rel']} does not list it in full")
        elif h and f["id"] not in {e["id"] for e in model["function_groups"].get(h["group"], {}).get("functions", [])}:
            errs.append(f"{f['key']}: home group {h['group']} does not list it")
    for span, tg in model["content_links"].items():
        if tg["kind"] == "function":
            if by_id.get(tg["id"], {}).get("home") != {k: tg[k] for k in ("type", "group", "rel")}:
                errs.append(f"content_links `{span}`: target is not the home of {tg['id']}")
        elif tg["type"] not in model["types"]:
            errs.append(f"content_links `{span}`: unknown type {tg['type']}")
        elif tg["kind"] in ("method", "field"):
            s = model["types"][tg["type"]]["struct"] or {}
            ids = {m.get("id") for m in s.get("fields", []) + s.get("methods", [])}
            if tg["id"] not in ids:
                errs.append(f"content_links `{span}`: no member {tg['id']} on {tg['type']}")
    for name, t in model["types"].items():
        paths = [g["path"] for g in t["guides"]]
        if len(paths) != len(set(paths)):
            errs.append(f"types.{name}.guides: duplicate pages")
    for f in model["functions"]:
        if f["category"] not in model["categories"]:
            errs.append(f"{f['key']}: unknown category {f['category']}")
        if not f["primary"] and f.get("variant_of") not in by_id:
            errs.append(f"{f['key']}: variant of an unknown function")
    return errs
