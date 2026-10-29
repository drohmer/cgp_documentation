"""Hand-curated inputs (editorial/*.yaml): loading and validation.

These files are the only place where humans (or agents) steer the model without touching
code. Every problem found here is returned as a message; nothing is silently ignored.
"""

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .categories import CATEGORIES
from .cpptypes import split_template


@dataclass
class Editorial:
    types: dict = field(default_factory=dict)          # name -> {canonical, group, short, figures, tasks}
    descriptions: dict = field(default_factory=dict)   # function key -> one-line description
    members: dict = field(default_factory=dict)        # member key (type::field, method key) -> description
    function_groups: dict = field(default_factory=dict)  # group -> {title, short, under, modules, names}
    annotations: dict = field(default_factory=dict)    # function key -> category
    content_ignore: list = field(default_factory=list)  # names ignored by the content check
    content_no_link: list = field(default_factory=list)  # names never linked to the reference
    errors: list = field(default_factory=list)          # format errors found while loading


def _load(path: Path, errors: list):
    """A YAML mapping; a missing file, invalid YAML or a non-mapping is an error."""
    if not path.exists():
        errors.append(f"{path.name}: file missing ({path})")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        errors.append(f"{path.name}: invalid YAML ({e})")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{path.name}: expected a mapping (key: value), got {type(data).__name__}")
        return {}
    return data


TASK_KEYS = {"do", "use", "guide"}


def _task_errors(name: str, task, content: Path) -> list:
    """Format of one entry of `tasks` (types.yaml): {do: one word, use: [code...], guide: page}.
    The code spans are resolved later, against the model (crossrefs.attach_tasks)."""
    if not (isinstance(task, dict) and set(task) <= TASK_KEYS and isinstance(task.get("do"), str)
            and isinstance(task.get("use"), list) and task["use"]
            and all(isinstance(u, str) and u.strip() for u in task["use"])):
        return [f"types.yaml: '{name}' tasks must be a list of {{do, use: [code...], guide}}"]
    errors = []
    if not (task["do"].isalpha() and task["do"].isascii() and len(task["do"]) <= 10):
        errors.append(f"types.yaml: '{name}' task '{task['do']}': `do` must be one ASCII word of at most 10 letters")
    if not all(u.isascii() for u in task["use"]):
        errors.append(f"types.yaml: '{name}' task '{task['do']}': non-ASCII characters in `use`")
    guide = task.get("guide")
    if guide is not None and not (isinstance(guide, str) and (content / guide).is_file()):
        errors.append(f"types.yaml: '{name}' task '{task['do']}': guide '{guide}' not found in content/")
    return errors


UTILITIES = "Utilities"   # last group of the Reference, for the pages of functions of no theme


def _function_group_errors(ed: Editorial) -> list:
    """`under` names a group of types.yaml (or Utilities); a module has at most one page that
    takes its functions by default (no `names`)."""
    groups = {t["group"] for t in ed.types.values() if isinstance(t, dict) and t.get("group")}
    errors, default_of = [], {}
    for name, g in ed.function_groups.items():
        if not isinstance(g, dict) or not isinstance(g.get("modules"), list):
            continue
        if isinstance(g.get("under"), str) and g["under"] not in groups | {UTILITIES}:
            errors.append(f"function_groups.yaml: '{name}' under '{g['under']}' is no group of types.yaml "
                          f"(nor {UTILITIES})")
        if "names" not in g:
            for m in g["modules"]:
                if m in default_of:
                    errors.append(f"function_groups.yaml: module {m} is taken by default by '{default_of[m]}' "
                                  f"and '{name}': give `names` to one of them")
                default_of[m] = name
    return errors


def function_group_of(function_groups: dict, module: str, name: str):
    """The page of function_groups.yaml of a function on no type page: among the pages of its
    module, the first whose `names` match its name, else the page of the module without `names`."""
    default = None
    for g, d in function_groups.items():
        if not isinstance(d, dict) or module not in (d.get("modules") or []):
            continue
        if "names" not in d:
            default = default or g
        elif any(fnmatch.fnmatchcase(name, pat) for pat in d["names"]):
            return g
    return default


def load(paths) -> Editorial:
    ed = Editorial()
    ed.types = _load(paths.types, ed.errors)
    ed.descriptions = _load(paths.descriptions, ed.errors)
    ed.annotations = _load(paths.annotations, ed.errors)
    ed.members = _load(paths.members, ed.errors)
    ed.function_groups = _load(paths.function_groups, ed.errors)
    for name, g in ed.function_groups.items():
        if not (isinstance(g, dict) and isinstance(g.get("title"), str) and isinstance(g.get("short"), str)
                and isinstance(g.get("under"), str) and isinstance(g.get("modules"), list) and g["modules"]):
            ed.errors.append(f"function_groups.yaml: '{name}' needs title, short, under and a non-empty list of modules")
        elif "names" in g and not (isinstance(g["names"], list) and g["names"]
                                   and all(isinstance(n, str) for n in g["names"])):
            ed.errors.append(f"function_groups.yaml: '{name}' names must be a non-empty list of name patterns")
    content_check = _load(paths.content_check, ed.errors) or {}
    ed.content_ignore = list(content_check.get("ignore") or [])
    ed.content_no_link = list(content_check.get("no_link") or [])

    for name, t in ed.types.items():
        for k in ("canonical", "group", "short"):
            if not isinstance(t, dict) or not t.get(k):
                ed.errors.append(f"types.yaml: '{name}' lacks '{k}'")
        if isinstance(t, dict) and "family_of" in t and not (
                isinstance(t["family_of"], list) and t["family_of"] and all(isinstance(m, str) for m in t["family_of"])):
            ed.errors.append(f"types.yaml: '{name}' family_of must be a non-empty list of type names")
        for fig in (t.get("figures") or []) if isinstance(t, dict) else []:
            if not (isinstance(fig, dict) and isinstance(fig.get("src"), str) and isinstance(fig.get("caption"), str)
                    and fig["caption"].strip() and set(fig) == {"src", "caption"}):
                ed.errors.append(f"types.yaml: '{name}' figures must be a list of {{src, caption}}")
            elif not (paths.content / "assets" / fig["src"]).is_file():
                ed.errors.append(f"types.yaml: '{name}' figure '{fig['src']}' not found in content/assets")
            elif not fig["caption"].isascii():
                ed.errors.append(f"types.yaml: '{name}' non-ASCII characters in the caption of '{fig['src']}'")
        for task in (t.get("tasks") or []) if isinstance(t, dict) else []:
            ed.errors += _task_errors(name, task, paths.content)
    ed.errors += _function_group_errors(ed)
    for k, v in ed.descriptions.items():
        if not isinstance(v, str) or not v.strip():
            ed.errors.append(f"descriptions.yaml: empty description for '{k}'")
        elif not v.isascii():
            ed.errors.append(f"descriptions.yaml: non-ASCII characters in the description of '{k}'")
    for k, v in ed.members.items():
        if not isinstance(v, str) or not v.strip():
            ed.errors.append(f"members.yaml: empty description for '{k}'")
        elif not v.isascii():
            ed.errors.append(f"members.yaml: non-ASCII characters in the description of '{k}'")
    for k, v in ed.annotations.items():
        if v not in CATEGORIES:
            ed.errors.append(f"annotations.yaml: '{k}' has unknown category '{v}' (allowed: {', '.join(CATEGORIES)})")
    return ed


def type_targets(ed: Editorial) -> dict:
    """name -> canonical (base, args) for every documented type."""
    return {name: split_template(t["canonical"]) for name, t in ed.types.items() if isinstance(t, dict) and t.get("canonical")}


def stale_keys(ed: Editorial, function_keys: set, member_keys: set = frozenset()) -> list:
    """Editorial entries whose function or member key no longer exists in the code."""
    out = [f"members.yaml: '{k}' matches no member of a documented type (renamed or removed?)"
           for k in ed.members if k not in member_keys]
    for fname, table in (("descriptions.yaml", ed.descriptions), ("annotations.yaml", ed.annotations)):
        out += [f"{fname}: '{k}' matches no function (renamed or removed?)" for k in table if k not in function_keys]
    return out
