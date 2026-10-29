"""C++ type strings: normalization, alias resolution and matching against a target type.

Pure functions, no I/O: everything here is covered by tests/unit/test_cpptypes.py.

Vocabulary
  normalized type  'numarray_stack< T, N > const &' -> 'numarray_stack<T,N> const&'
  canonical type   (base, args) after alias resolution: 'vec3 const&' -> ('numarray_stack', ('float', '3'))
  match            how a parameter type relates to a target canonical type:
                   'exact', 'generic' (a template applying to the target) or None
"""

import re
from dataclasses import dataclass, field

Canonical = tuple  # (base: str, args: tuple[str, ...])

_QUALIFIERS = re.compile(r"\b(const|volatile|constexpr|inline|static|typename)\b")


def normalize(type_str: str) -> str:
    """Canonical spelling of a type string, used for keys and display."""
    s = re.sub(r"\s+", " ", type_str or "").strip()
    s = re.sub(r"\s*([<,])\s*", r"\1", s)
    s = re.sub(r"\s*>", ">", s)  # keep the space after '>' ('numarray_stack<T,N> const&')
    s = re.sub(r"\s*([&*])", r"\1", s)
    s = s.replace("cgp::", "")
    # east const: 'const std::string&' -> 'std::string const&' (one spelling per type)
    return re.sub(r"^const ([^&*]+?)([&*]*)$", r"\1 const\2", s)


def split_template(s: str) -> Canonical:
    """'numarray_stack<T,N>' -> ('numarray_stack', ('T', 'N')); nested templates are kept whole."""
    if "<" not in s:
        return s.strip(), ()
    base, rest = s.split("<", 1)
    rest = rest[: rest.rfind(">")]
    args, depth, cur = [], 0, ""
    for ch in rest:
        depth += (ch == "<") - (ch == ">")
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    args.append(cur.strip())
    return base.strip(), tuple(args)


def strip_qualifiers(type_str: str) -> str:
    """'numarray_stack<T,N> const&' -> 'numarray_stack<T,N>'."""
    t = _QUALIFIERS.sub(" ", normalize(type_str)).replace("&", " ").replace("*", " ")
    return re.sub(r"\s+", " ", t).strip()


def format_canonical(c: Canonical) -> str:
    base, args = c
    return base + ("<" + ",".join(args) + ">" if args else "")


@dataclass
class AliasTable:
    """Typedefs of the cgp namespace: alias -> (target canonical, template parameter names)."""

    aliases: dict = field(default_factory=dict)  # name -> (Canonical, tuple[str, ...])

    def add(self, name: str, target: str, params=()):
        self.aliases[name] = (split_template(strip_qualifiers(target)), tuple(params))

    def canonical(self, type_str: str, _depth: int = 0) -> Canonical:
        """Resolve aliases recursively: 'vec3 const&' -> ('numarray_stack', ('float', '3'))."""
        base, args = split_template(strip_qualifiers(type_str))
        if base in self.aliases and _depth < 16:
            (abase, aargs), params = self.aliases[base]
            subst = dict(zip(params, args))
            resolved = (abase, tuple(subst.get(a, a) for a in aargs))
            return self.canonical(format_canonical(resolved), _depth + 1)
        return base, args

    def match(self, type_str: str, target: Canonical, template_params=()):
        """'exact', 'generic' or None: does a type (parameter or return) designate the target?"""
        base, args = self.canonical(type_str)
        tbase, targs = target
        if base != tbase or (targs and len(args) != len(targs)):
            return None
        if not targs:  # type documented without arguments (numarray, grid_2D)
            return "generic" if any(a in template_params for a in args) else "exact"
        generic = False
        for a, ta in zip(args, targs):
            if a == ta:
                continue
            if a in template_params:
                generic = True
                continue
            return None
        return "generic" if generic else "exact"

    def match_family(self, type_str: str, base: str, nargs: int, template_params=()) -> bool:
        """True when a type is the template `base` with ALL its arguments left as template
        parameters of the function: numarray_stack<T,N> (any scalar, any size) is in the vecN
        family, numarray_stack<T,3> or numarray_stack<float,N> is not."""
        b, args = self.canonical(type_str)
        return b == base and len(args) == nargs and all(a in template_params for a in args)

    def as_dict(self) -> dict:
        return {k: format_canonical(v[0]) for k, v in sorted(self.aliases.items())}
