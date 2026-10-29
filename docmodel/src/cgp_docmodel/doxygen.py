"""Doxygen stage: run Doxygen on the CGP sources and read its XML into plain records.

Doxygen is only used as a C++ parser. Its XML is read here and nowhere else: the rest of
the package works on the records returned by this module.

What enters the model (and what does not, with the reason recorded in `excluded`):
  - free functions of the namespaces cgp and cgp::loader DECLARED IN A HEADER
    (helpers local to a .cpp file and static variables are excluded);
  - parameter names and default values are read in the header declaration
    (header.py), because Doxygen reports those of the .cpp definition.
A key collision (two functions with the same key) is an error, never a silent drop.
"""

import hashlib
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from .cpptypes import AliasTable, format_canonical, normalize, split_template, strip_qualifiers
from .header import HeaderReader
from .paths import Paths

GITHUB = "https://github.com/drohmer/cgp-2027/blob/{ref}/cgp/"
NAMESPACES = ("cgp", "cgp::loader")  # namespaces whose free functions are public API
HEADER_SUFFIXES = (".hpp", ".h")


class DoxygenError(RuntimeError):
    pass


def run_doxygen(paths: Paths) -> tuple:
    """Generate the XML into build/doxygen/xml. Returns (version, warnings)."""
    exe = shutil.which("doxygen")
    if exe is None:
        raise DoxygenError("doxygen not found in PATH (brew install doxygen)")
    if not paths.source.is_dir():
        raise DoxygenError(f"CGP sources not found: {paths.source} (set CGP_SOURCE_DIR)")
    out = paths.build / "doxygen"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    doxyfile = paths.build / "Doxyfile"
    template = paths.doxyfile_template.read_text(encoding="utf-8")
    doxyfile.write_text(template.replace("@INPUT@", str(paths.source)).replace("@OUTPUT@", str(out)),
                        encoding="utf-8")
    proc = subprocess.run([exe, str(doxyfile)], capture_output=True, text=True)
    log = proc.stdout + proc.stderr
    (paths.build / "doxygen.log").write_text(log, encoding="utf-8")
    if proc.returncode != 0:
        raise DoxygenError(f"doxygen failed (see {paths.build / 'doxygen.log'})")
    warnings = [l for l in log.splitlines() if ": warning:" in l]
    version = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.strip()
    return version, warnings


# ---------------------------------------------------------------- XML helpers

def _text(node) -> str:
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip() if node is not None else ""


def _tparam_name(p) -> str:
    return p.findtext("declname") or _text(p.find("type")).split()[-1]  # 'typename T' -> 'T'


def _relpath(path: str) -> str:
    """Path relative to the cgp/ source folder: '.../cgp-2027/cgp/05_vec/vec3/vec3.hpp' -> '05_vec/vec3/vec3.hpp'."""
    m = re.search(r"/cgp/(\d\d_.*)$", path)
    return m.group(1) if m else Path(path).name


def stable_id(namespace: str, key: str) -> str:
    """Identifier that depends only on the signature, so it survives Doxygen upgrades."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", key.split("(", 1)[0]).strip("-").lower()
    return f"fn-{slug}-{hashlib.sha1(f'{namespace}::{key}'.encode()).hexdigest()[:8]}"


def make_key(name: str, tparams, param_types, is_const: bool, owner: str | None = None) -> str:
    """'norm<T,N>(numarray_stack<T,N> const&)': name, template parameters, parameter types."""
    prefix = f"{owner}::" if owner else ""
    tpl = f"<{','.join(tparams)}>" if tparams else ""
    return f"{prefix}{name}{tpl}(" + ",".join(param_types) + ")" + (" const" if is_const else "")


class DoxygenXML:
    """Read access to the Doxygen XML output."""

    def __init__(self, xml_dir: Path, source_ref: str = "main"):
        self.dir = xml_dir
        self.github = GITHUB.format(ref=source_ref or "main")
        self.headers = HeaderReader()
        index = ET.parse(xml_dir / "index.xml").getroot()
        self.compounds = {}  # 'cgp::mesh' -> (kind, refid)
        for c in index.findall("compound"):
            self.compounds[c.findtext("name")] = (c.get("kind"), c.get("refid"))
        self.by_refid = {refid: name for name, (_, refid) in self.compounds.items()}
        self._aliases = None

    def _compounddef(self, qualified_name: str):
        return self._compounddef_ref(self.compounds[qualified_name][1])

    def _compounddef_ref(self, refid: str):
        return ET.parse(self.dir / f"{refid}.xml").getroot().find("compounddef")

    def source_url(self, rel: str, line: int) -> str:
        return f"{self.github}{rel}#L{line}"

    # ------------------------------------------------------------ aliases

    def aliases(self) -> AliasTable:
        if self._aliases is None:
            table = AliasTable()
            for m in self._compounddef("cgp").iter("memberdef"):
                if m.get("kind") == "typedef":
                    tpl = m.find("templateparamlist")
                    params = [_tparam_name(p) for p in tpl.findall("param")] if tpl is not None else []
                    table.add(m.findtext("name"), _text(m.find("type")), params)
            self._aliases = table
        return self._aliases

    # ------------------------------------------------------------ functions

    def parse_function(self, m, namespace: str, owner: str | None = None) -> dict:
        """One <memberdef kind="function"> as a record (free function or method)."""
        tpl = m.find("templateparamlist")
        tparams = tuple(_tparam_name(p) for p in tpl.findall("param")) if tpl is not None else ()
        template = ""
        if tpl is not None:
            parts = [_text(p.find("type")) + (" " + p.findtext("declname") if p.findtext("declname") else "")
                     for p in tpl.findall("param")]
            template = "template <" + ", ".join(parts) + ">"
        params = [{"type": normalize(_text(p.find("type"))),
                   "name": p.findtext("declname") or "",
                   "default": _text(p.find("defval")) or None}
                  for p in m.findall("param")]
        loc = m.find("location")
        decl_file = loc.get("declfile") or loc.get("file")
        line = int(loc.get("declline") or loc.get("line") or 0)
        name = m.findtext("name")

        params_source = "doxygen"
        from_header = self.headers.params(decl_file, line, name)
        if from_header is not None and len(from_header) == len(params):
            for p, (hname, hdefault) in zip(params, from_header):
                if hname:
                    p["name"] = hname
                p["default"] = hdefault
            params_source = "header"

        ret = normalize(_text(m.find("type")))
        for q in ("inline ", "static ", "constexpr ", "virtual ", "explicit "):
            ret = ret.replace(q, "")
        is_const = m.get("const") == "yes"
        prefix = f"{owner}::" if owner else ""
        args = ", ".join(p["type"] + (" " + p["name"] if p["name"] else "") + (" = " + p["default"] if p["default"] else "")
                         for p in params)
        signature = f"{ret} {prefix}{name}({args}){' const' if is_const else ''}".strip()
        if owner and m.get("static") == "yes":
            signature = "static " + signature
        key = make_key(name, tparams, [p["type"] for p in params], is_const, owner)
        rel = _relpath(decl_file)
        return {
            "id": stable_id(namespace, key),
            "key": key,
            "name": name,
            "namespace": namespace,
            "owner": owner,
            "static": m.get("static") == "yes",
            "const": is_const,
            "template": template,
            "tparams": list(tparams),
            "ret": ret,
            "params": params,
            "params_source": params_source,
            "signature": signature,
            "module": rel.split("/", 1)[0],
            "file": rel,
            "line": line,
            "source_url": self.source_url(rel, line),
            "brief": _text(m.find("briefdescription")),
            "detail": _text(m.find("detaileddescription")),
            "_declfile": decl_file,
        }

    def _relocate_to_header(self, m, ns, declfile: str, f: dict) -> dict:
        """Doxygen sometimes attaches a function to its .cpp definition although the header
        of the same name declares it (str_lower in string.hpp). Look for that declaration;
        if found, re-read the record from it, otherwise mark it as .cpp-only."""
        header = str(Path(declfile).with_suffix(".hpp"))
        line = self.headers.find_declaration(header, f["name"], [p["type"] for p in f["params"]], normalize)
        if line is None:
            f["_declfile_cpp"] = True
            return f
        loc = m.find("location")
        loc.set("declfile", header)
        loc.set("declline", str(line))
        g = self.parse_function(m, ns)
        g.pop("_declfile")
        return g

    def free_functions(self) -> tuple:
        """(functions, excluded, errors). `excluded` lists (key, reason); `errors` key collisions."""
        funcs, excluded, errors, seen = [], [], [], {}
        for ns in NAMESPACES:
            if ns not in self.compounds:
                continue
            for m in self._compounddef(ns).iter("memberdef"):
                if m.get("kind") != "function":
                    continue
                f = self.parse_function(m, ns)
                declfile = f.pop("_declfile")
                if not declfile.endswith(HEADER_SUFFIXES):
                    f = self._relocate_to_header(m, ns, declfile, f)
                if f.pop("_declfile_cpp", False):
                    excluded.append((f"{f['key']} [{f['file']}:{f['line']}]", "declared in a .cpp file (not public API)"))
                    continue
                if f["id"] in seen:
                    errors.append(f"key collision: '{f['key']}' at {f['file']}:{f['line']} and {seen[f['id']]}")
                    continue
                seen[f["id"]] = f"{f['file']}:{f['line']}"
                funcs.append(f)
        return funcs, excluded, errors

    # ------------------------------------------------------------ structs

    def struct_names(self) -> list:
        """Unqualified names of every struct/class of the cgp namespace (for content checks)."""
        return sorted({n.split("::")[-1].split("<")[0].strip() for n, (kind, _) in self.compounds.items()
                       if kind in ("struct", "class") and n.startswith("cgp::")})

    def find_struct(self, target) -> str | None:
        """Compound name documenting a canonical type: exact specialization first
        (matrix_stack<float,4,4>), then partial specialization (numarray_stack<T,3> for
        <float,3>), then the primary template / plain struct."""
        base, args = target
        best, best_score = None, -1
        for name, (kind, _) in self.compounds.items():
            if kind not in ("struct", "class") or not name.startswith("cgp::"):
                continue
            cbase, cargs = split_template(normalize(name))
            if cbase != base:
                continue
            if not cargs:
                score = 0
            elif len(cargs) == len(args) and all(c == a or (len(c) == 1 and c.isupper()) for c, a in zip(cargs, args)):
                score = 1 + sum(c == a for c, a in zip(cargs, args))
            else:
                continue
            if score > best_score:
                best, best_score = name, score
        return best

    def bases(self, compound: str) -> list:
        """Canonical types of the public base classes: quaternion -> [numarray_stack<float,4>]."""
        out = []
        for b in self._compounddef(compound).findall("basecompoundref"):
            if b.get("prot") != "public":
                continue
            text = normalize(_text(b))  # 'numarray_stack<T,4><float>' or 'camera_generic_base'
            m = re.match(r"^(.*?<[^<>]*>)<([^<>]*)>$", text)
            if m:  # partial specialization instantiated: substitute its template parameters
                pbase, pargs = split_template(m.group(1))
                given = [a.strip() for a in m.group(2).split(",")]
                params = [a for a in pargs if len(a) == 1 and a.isupper()]
                subst = dict(zip(params, given))
                out.append((pbase, tuple(subst.get(a, a) for a in pargs)))
            else:
                out.append(self.aliases().canonical(text))
        return out

    def struct(self, target, follow_bases: bool = True) -> dict | None:
        """Fields and public methods of the struct documenting `target` (with inherited members)."""
        compound = self.find_struct(target)
        if compound is None:
            return None
        cd = self._compounddef(compound)
        own_prefix = cd.get("id") + "_1"
        short = compound.split("::", 1)[1].replace(" ", "")
        fields, methods = [], []
        for m in cd.iter("memberdef"):
            if m.get("prot") != "public":
                continue
            if not m.get("id", "").startswith(own_prefix):
                # Doxygen copies members of the primary template into its specializations
                # (numarray_stack<T,3> gets 'std::array<T,N> data', which it does not declare):
                # keep only members whose id belongs to this compound.
                continue
            if m.get("kind") == "variable":
                fields.append({
                    "key": f"{short}::{m.findtext('name')}",
                    "name": m.findtext("name"),
                    "type": normalize(_text(m.find("type"))),
                    "static": m.get("static") == "yes",
                    "brief": _text(m.find("briefdescription")),
                    "initializer": _text(m.find("initializer")),
                    "inherited_from": None,
                })
            elif m.get("kind") == "function" and not (m.findtext("name") or "").startswith("~"):
                f = self.parse_function(m, "cgp", owner=target[0])
                f.pop("_declfile")
                f["ctor"] = f["name"] == target[0]
                f["inherited_from"] = None
                methods.append(f)
        bases = self.bases(compound)
        if follow_bases:
            for b in bases:
                bs = self.struct(b)
                if not bs:
                    continue
                origin = format_canonical(b)
                own = {x["name"] for x in fields}
                fields += [dict(x, inherited_from=x["inherited_from"] or origin) for x in bs["fields"] if x["name"] not in own]
                own_m = {x["name"] for x in methods}
                methods += [dict(x, inherited_from=x["inherited_from"] or origin) for x in bs["methods"]
                            if x["name"] not in own_m and not x.get("ctor")]
        loc = cd.find("location")
        rel = _relpath(loc.get("file"))
        line = int(loc.get("line") or 0)
        return {
            "compound": short,
            "bases": [format_canonical(b) for b in bases],
            "brief": _text(cd.find("briefdescription")),
            "detail": _text(cd.find("detaileddescription")),
            "fields": fields,
            "methods": methods,
            "module": rel.split("/", 1)[0],
            "file": rel,
            "line": line,
            "source_url": self.source_url(rel, line),
        }

    def members_by_struct(self) -> dict:
        """struct name -> names of its public members (fields and methods)."""
        out = {}
        for n, (kind, refid) in self.compounds.items():
            if kind in ("struct", "class") and n.startswith("cgp::"):
                short = n.split("::")[-1].split("<")[0].strip()
                cd = self._compounddef_ref(refid)
                names = out.setdefault(short, set())
                for m in cd.iter("memberdef"):
                    if m.get("prot") == "public" and m.get("kind") in ("variable", "function"):
                        names.add(m.findtext("name"))
        return out
