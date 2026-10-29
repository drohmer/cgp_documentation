"""Human-readable outputs for audit: golden snapshots and coverage report.

Golden snapshots (docmodel/tests/golden/*.txt) are plain-text projections of the model,
one fact per line, sorted. The tests compare them with the current model, so any change
of the extraction logic or of the C++ sources shows up as a readable diff that a reviewer
(human or agent) approves with `cgp-docmodel snapshot --update`:

  functions.txt  every function: key, category (and rule), params source, signature, location
  relations.txt  type -> function relations (takes / returns / operators, generic, via base),
                 and the home page of each function (home | page | rel | key)
  structs.txt    struct of each documented type: compound, bases, fields, methods
  excluded.txt   functions left out of the model, with the reason
"""

from collections import Counter, defaultdict


def functions_snapshot(model: dict) -> str:
    lines = []
    for f in model["functions"]:
        role = "primary" if f["primary"] else f"variant-of {f['variant_of']}"
        rule = f["category_rule"] or "curated"
        lines.append(f"{f['key']} | {f['category']} ({rule}) | {role} | params:{f['params_source']} "
                     f"| {f['signature']} | {f['file']}:{f['line']}")
    return "\n".join(sorted(lines)) + "\n"


def relations_snapshot(model: dict) -> str:
    by_id = {f["id"]: f for f in model["functions"]}
    lines = []
    for name, t in model["types"].items():
        for rel in ("takes", "returns", "operators"):
            for e in t[rel]:
                f = by_id[e["id"]]
                flag = "generic" if e["generic"] else "exact"
                via = f" | via {e['via']}" if e.get("via") else ""
                shared = f" | shared {e['shared']}" if e.get("shared") else ""
                lines.append(f"{name} | {rel} | {f['category']} | {flag} | {f['key']}{via}{shared}")
    for name, g in model.get("function_groups", {}).items():
        for e in g["functions"]:
            f = by_id[e["id"]]
            lines.append(f"group:{name} | functions | {f['category']} | {f['key']}")
    for f in model["functions"]:
        h = f.get("home")
        if h:  # page that documents the function in full (links of the guides point there)
            page = h["type"] if h["type"] else f"group:{h['group']}"
            lines.append(f"home | {page} | {h['rel']} | {f['key']}")
    return "\n".join(sorted(lines)) + "\n"


def structs_snapshot(model: dict) -> str:
    lines = []
    for name, t in model["types"].items():
        s = t["struct"]
        if not s:
            lines.append(f"{name} | no struct")
            continue
        lines.append(f"{name} | compound {s['compound']} | bases {', '.join(s['bases']) or '-'}")
        for fl in s["fields"]:
            lines.append(f"{name} | field | {fl['type']} {fl['name']}"
                         + (f" | from {fl['inherited_from']}" if fl["inherited_from"] else ""))
        for m in s["methods"]:
            lines.append(f"{name} | method | {m['key']}"
                         + (f" (+{len(m['variants'])} variant)" if m["variants"] else "")
                         + (f" | from {m['inherited_from']}" if m["inherited_from"] else ""))
    return "\n".join(sorted(lines)) + "\n"


def excluded_snapshot(model: dict) -> str:
    return "\n".join(sorted(f"{e['key']} | {e['reason']}" for e in model["excluded"])) + "\n"


def snapshots(model: dict, golden_dir) -> dict:
    """golden file path -> current text."""
    return {
        golden_dir / "functions.txt": functions_snapshot(model),
        golden_dir / "relations.txt": relations_snapshot(model),
        golden_dir / "structs.txt": structs_snapshot(model),
        golden_dir / "excluded.txt": excluded_snapshot(model),
    }


def coverage_markdown(model: dict, unresolved: list, doxygen_warnings=()) -> str:
    funcs = [f for f in model["functions"] if f["primary"]]
    src = Counter(f["description_source"] for f in funcs)
    cat = Counter(f["category"] for f in funcs)
    rule = Counter(f["category_rule"] or "curated" for f in funcs)
    psrc = Counter(f["params_source"] for f in funcs)
    per_module = defaultdict(Counter)
    for f in funcs:
        per_module[f["module"]][f["description_source"]] += 1
    gen = model["generator"]

    out = ["# cgp-docmodel coverage report", "",
           f"Source commit: `{gen['source']['commit']}`" + (" (uncommitted changes)" if gen["source"]["dirty"] else ""),
           f"Doxygen: {gen['doxygen']}, {gen['doxygen_warnings']} warnings", "",
           f"Functions (primaries, const variants merged): **{len(funcs)}** "
           f"({len(model['functions']) - len(funcs)} variants, {len(model['excluded'])} excluded)", "",
           f"Parameters read from the header declaration: {psrc['header']}, from Doxygen only: {psrc['doxygen']}", "",
           "| Description source | Count |", "|---|---|"]
    out += [f"| {k} | {src.get(k, 0)} |" for k in ("curated", "source", "missing")]
    out += ["", "## Descriptions per module", "", "| Module | curated | source | missing |", "|---|---|---|---|"]
    out += [f"| {m} | {c['curated']} | {c['source']} | {c['missing']} |" for m, c in sorted(per_module.items())]
    out += ["", "## Categories", "", "| Category | Count |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in sorted(cat.items(), key=lambda kv: (-kv[1], kv[0]))]
    out += ["", "## Category rules used", "", "| Rule | Count |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in sorted(rule.items(), key=lambda kv: (-kv[1], kv[0]))]
    out += ["", "## Types", "", "| Type | struct | takes | returns | operators | methods |", "|---|---|---|---|---|---|"]
    for name, t in model["types"].items():
        s = t["struct"]
        out.append(f"| {name} | {s['compound'] if s else '-'} | {len(t['takes'])} | {len(t['returns'])} "
                   f"| {len(t['operators'])} | {len(s['methods']) if s else 0} |")
    out += ["", "## Unresolved names in content/", ""]
    out += [f"- `{name}` in {page}:{line}" for page, line, name in unresolved] or ["None."]
    out += ["", "## Doxygen warnings", ""]
    out += [f"- {w}" for w in doxygen_warnings] or ["None."]
    return "\n".join(out) + "\n"
