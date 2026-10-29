"""Read a function declaration directly in a header file.

Why: when a function is declared in a .hpp and defined in a .cpp, Doxygen reports the
parameters of the *definition*, which has no default values and sometimes other parameter
names (draw(mesh_drawable const&, environment...) loses its 6 defaults). The declaration in
the header is what users read, so names and defaults are taken from there.

Pure text functions; covered by tests/unit/test_header.py.
"""

import re
from pathlib import Path

_OPEN = "<({["
_CLOSE = ">)}]"


def split_top_level(s: str, sep: str = ",") -> list:
    """Split on `sep` outside brackets and quotes: 'a<b,c> x, int y = f(1,2)' -> 2 parts."""
    parts, depth, cur, quote = [], 0, "", None
    for ch in s:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


_TYPE_WORDS = {"const", "int", "float", "double", "bool", "char", "unsigned", "signed", "long", "short", "size_t", "auto", "void"}


def _param_name(decl: str) -> str:
    """'vec3 const& center' -> 'center'; 'vec3 const&' or 'unsigned int' (unnamed) -> ''."""
    m = re.search(r"([A-Za-z_]\w*)\s*(\[[^\]]*\])?$", decl)
    if not m:
        return ""
    before = decl[: m.start()].rstrip()
    if not before or before.endswith("::") or m.group(1) in _TYPE_WORDS:
        return ""
    return m.group(1)


def declaration_params(text: str, name: str, with_types: bool = False):
    """Parameters [(name, default)] of the first declaration of `name` in `text`, or None.
    With `with_types`: [(name, default, type)].

    `text` starts at the declaration line. Only the parenthesized list right after the
    function name is read.
    """
    text = _strip_comments(text)
    m = re.search(r"(?<![\w:])" + re.escape(name) + r"\s*\(", text)
    if not m:
        return None
    i, depth, buf = m.end(), 1, ""
    while i < len(text) and depth:
        ch = text[i]
        depth += (ch == "(") - (ch == ")")
        if depth:
            buf += ch
        i += 1
    if depth:
        return None
    out = []
    for p in split_top_level(buf):
        if p in ("", "void"):
            continue
        eq = split_top_level(p, "=")
        decl, default = eq[0], ("=".join(eq[1:]).strip() if len(eq) > 1 else None)
        out.append((_param_name(decl), default, _param_type(decl)))
    return [(n, d) for n, d, _ in out] if not with_types else out


def _param_type(decl: str) -> str:
    """'vec3 const& center' -> 'vec3 const&' (the declaration without its name)."""
    name = _param_name(decl)
    return decl[: decl.rfind(name)].strip() if name else decl.strip()


class HeaderReader:
    """Cached access to the lines of the source files."""

    def __init__(self):
        self._cache = {}

    def params(self, path: str, line: int, name: str):
        if not path.endswith((".hpp", ".h")) or line <= 0:
            return None
        if path not in self._cache:
            try:
                self._cache[path] = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                return None
        lines = self._cache[path]
        chunk = "\n".join(lines[line - 1: line + 40])
        return declaration_params(chunk, name.split("::")[-1])

    def find_declaration(self, path: str, name: str, param_types: list, normalize):
        """Line of the declaration of `name` in header `path` whose parameter types equal
        `param_types` (after `normalize`), or None. Used when Doxygen attaches a function
        to its .cpp definition although the header declares it."""
        if not Path(path).exists():
            return None
        if path not in self._cache:
            self._cache[path] = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        lines = self._cache[path]
        pat = re.compile(r"(?<![\w:.])" + re.escape(name) + r"\s*\(")
        for i, l in enumerate(lines, 1):
            if l.lstrip().startswith("//") or not pat.search(l):
                continue
            ps = declaration_params("\n".join(lines[i - 1: i + 40]), name, with_types=True)
            if ps is not None and [normalize(t) for _, _, t in ps] == list(param_types):
                return i
        return None
