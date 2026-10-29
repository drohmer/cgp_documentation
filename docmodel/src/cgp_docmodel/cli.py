"""Command line: cgp-docmodel build | check | report | snapshot.

Exit codes (stable, for scripts and agents):
  0  success
  1  check failed (errors, or warnings with --strict, or snapshot differs)
  2  environment problem (doxygen missing, sources or build outputs not found,
     invalid editorial files)
"""

import argparse
import difflib
import json
import sys
import time

from . import checks, content, crossrefs, editorial, model as model_mod, report
from .doxygen import DoxygenError, DoxygenXML, run_doxygen
from .paths import default_paths


def log(msg):
    print(f"[cgp-docmodel] {msg}", flush=True)


def cmd_build(paths, args) -> int:
    t0 = time.time()
    try:
        version, warnings = run_doxygen(paths)
    except DoxygenError as e:
        log(f"ERROR {e}")
        return 2
    log(f"doxygen {version}: XML in {paths.doxygen_xml} ({time.time() - t0:.1f}s), "
        f"{len(warnings)} warnings (see {paths.build / 'doxygen.log'})")
    model, ed, xml, errors = model_mod.build_model(paths, version, warnings)
    if errors:
        for e in errors:
            log(f"ERROR {e}")
        return 2
    vocab = model_mod.vocabulary(model, xml)
    res = content.check_content(paths.content, vocab, ed.content_ignore)
    crossrefs.attach(model, res["spans"], vocab, paths.content, ed.content_no_link)
    errors = crossrefs.attach_tasks(model, ed.types, vocab, paths.content)
    if errors:
        for e in errors:
            log(f"ERROR {e}")
        return 2
    paths.api_json.write_text(model_mod.dump(model), encoding="utf-8")
    paths.content_index.write_text(json.dumps(res["refs"], indent=1) + "\n", encoding="utf-8")
    prim = sum(f["primary"] for f in model["functions"])
    log(f"{len(model['functions'])} functions ({prim} primaries), {len(model['excluded'])} excluded, "
        f"{len(model['types'])} types -> {paths.api_json}")
    log(f"content index ({len(res['refs'])} cited names) -> {paths.content_index}; "
        f"{len(model['content_links'])} inline code spans linked to the reference, "
        f"{sum(len(t['guides']) > 0 for t in model['types'].values())} types with guides")
    log(f"done in {time.time() - t0:.1f}s")
    return 0


def _load_built(paths):
    if not paths.api_json.exists() or not (paths.doxygen_xml / "index.xml").exists():
        log(f"ERROR build outputs missing in {paths.build}: run `cgp-docmodel build` first")
        return None, None
    model = json.loads(paths.api_json.read_text(encoding="utf-8"))
    source = model.get("generator", {}).get("source", {}).get("commit") or "main"
    return model, DoxygenXML(paths.doxygen_xml, source_ref=source)


def cmd_check(paths, args) -> int:
    model, xml = _load_built(paths)
    if model is None:
        return 2
    ed = editorial.load(paths)
    if ed.errors:
        for e in ed.errors:
            print(f"ERROR   {e}")
        return 2
    errors = checks.schema_errors(model, paths.schema)
    errors += checks.invariant_errors(model)
    member_keys = {m["key"] for t in model["types"].values() for m in
                   ((t["struct"] or {}).get("fields", []) + (t["struct"] or {}).get("methods", []))}
    errors += editorial.stale_keys(ed, {f["key"] for f in model["functions"]}, member_keys)
    vocab = model_mod.vocabulary(model, xml)
    res = content.check_content(paths.content, vocab, ed.content_ignore)
    warnings = [f"content/{p}:{line}: `{name}` does not resolve to a CGP name "
                f"(fix the page, or add it to content_check.yaml if it is not CGP)"
                for p, line, name in res["unresolved"]]
    warnings += [f"content_check.yaml: '{n}' is a CGP name, no need to ignore it"
                 for n in ed.content_ignore if n in vocab.names]
    drafts = sum(v.rstrip().endswith("[draft]") for v in ed.descriptions.values())
    missing = sum(f["description_source"] == "missing" for f in model["functions"] if f["primary"])
    members_missing = len({m["key"] for t in model["types"].values() for m in
                           ((t["struct"] or {}).get("fields", []) + (t["struct"] or {}).get("methods", []))
                           if m["description_source"] == "missing"})
    for e in errors:
        print(f"ERROR   {e}")
    for w in warnings:
        print(f"WARNING {w}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s); "
          f"info: {missing} functions without description, {members_missing} members without description, "
          f"{drafts} draft descriptions to review")
    return 1 if errors or (args.strict and warnings) else 0


def cmd_report(paths, args) -> int:
    model, xml = _load_built(paths)
    if model is None:
        return 2
    ed = editorial.load(paths)
    res = content.check_content(paths.content, model_mod.vocabulary(model, xml), ed.content_ignore)
    warnings_log = paths.build / "doxygen.log"
    dox = [l for l in warnings_log.read_text(encoding="utf-8").splitlines() if ": warning:" in l] \
        if warnings_log.exists() else []
    paths.reports.mkdir(parents=True, exist_ok=True)
    out = paths.reports / "coverage.md"
    out.write_text(report.coverage_markdown(model, res["unresolved"], dox), encoding="utf-8")
    log(f"report -> {out}")
    return 0


def cmd_snapshot(paths, args) -> int:
    model, _ = _load_built(paths)
    if model is None:
        return 2
    status = 0
    for golden, current in report.snapshots(model, paths.golden_dir).items():
        if args.update:
            golden.parent.mkdir(parents=True, exist_ok=True)
            golden.write_text(current, encoding="utf-8")
            log(f"snapshot updated -> {golden}")
            continue
        previous = golden.read_text(encoding="utf-8") if golden.exists() else ""
        diff = list(difflib.unified_diff(previous.splitlines(), current.splitlines(),
                                         f"golden/{golden.name}", "current", lineterm="", n=0))
        if diff:
            print("\n".join(diff))
            log(f"{golden.name}: {sum(l[:1] in '+-' for l in diff[2:])} lines differ")
            status = 1
        else:
            log(f"{golden.name}: unchanged")
    if status:
        log("review the diff, then `cgp-docmodel snapshot --update` (see AGENTS.md rule 3)")
    return status


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cgp-docmodel", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="run Doxygen and write build/api.json and build/content_index.json")
    c = sub.add_parser("check", help="validate schema, invariants, editorial files and content references")
    c.add_argument("--strict", action="store_true", help="fail on warnings too")
    sub.add_parser("report", help="write build/reports/coverage.md")
    s = sub.add_parser("snapshot", help="compare the model with the golden snapshots")
    s.add_argument("--update", action="store_true", help="accept the current model as the new golden")
    args = ap.parse_args(argv)
    paths = default_paths()
    return {"build": cmd_build, "check": cmd_check, "report": cmd_report, "snapshot": cmd_snapshot}[args.cmd](paths, args)


if __name__ == "__main__":
    sys.exit(main())
