"""Type strings: normalization, templates, alias resolution, matching."""

import pytest

from cgp_docmodel.cpptypes import AliasTable, normalize, split_template, strip_qualifiers


@pytest.mark.parametrize("raw, expected", [
    ("numarray_stack< T, N > const &", "numarray_stack<T,N> const&"),
    ("cgp::mesh const  &", "mesh const&"),
    ("float *", "float*"),
    ("std::map< std::string, int >", "std::map<std::string,int>"),
    ("const std::string &", "std::string const&"),     # east const: one spelling per type
    ("const char *", "char const*"),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("vec3", ("vec3", ())),
    ("numarray_stack<T,N>", ("numarray_stack", ("T", "N"))),
    ("numarray<numarray_stack<float,3>>", ("numarray", ("numarray_stack<float,3>",))),
    ("matrix_stack<float,4,4>", ("matrix_stack", ("float", "4", "4"))),
])
def test_split_template(raw, expected):
    assert split_template(raw) == expected


def test_strip_qualifiers():
    assert strip_qualifiers("numarray_stack<T,N> const&") == "numarray_stack<T,N>"
    assert strip_qualifiers("static inline float") == "float"


@pytest.fixture
def aliases():
    t = AliasTable()
    # as in cgp-2027: vec3 = numarray_stack3<float>, numarray_stack3<T> = numarray_stack<T,3>
    t.add("numarray_stack3", "numarray_stack< T, 3 >", ["T"])
    t.add("vec3", "numarray_stack3< float >")
    t.add("mat4", "matrix_stack< float, 4, 4 >")
    return t


VEC3 = ("numarray_stack", ("float", "3"))


def test_alias_chain_resolution(aliases):
    assert aliases.canonical("vec3 const&") == VEC3
    assert aliases.canonical("numarray_stack3<float>") == VEC3
    assert aliases.canonical("mat4") == ("matrix_stack", ("float", "4", "4"))
    assert aliases.canonical("mesh const&") == ("mesh", ())


@pytest.mark.parametrize("type_str, tparams, expected", [
    ("vec3 const&", (), "exact"),                     # cross(vec3, vec3)
    ("numarray_stack<T,N> const&", ("T", "N"), "generic"),  # norm(numarray_stack<T,N>)
    ("numarray_stack3<T> const&", ("T",), "generic"),  # size-3 specialisation, any scalar
    ("numarray_stack<float,2> const&", (), None),      # vec2 is not vec3
    ("numarray_stack<T,2> const&", ("T",), None),      # generic but wrong size
    ("numarray<vec3> const&", (), None),               # container of vec3 is not vec3
    ("mesh const&", (), None),
])
def test_match_vec3(aliases, type_str, tparams, expected):
    assert aliases.match(type_str, VEC3, tparams) == expected


def test_match_plain_struct(aliases):
    assert aliases.match("mesh&", ("mesh", ()), ()) == "exact"
    assert aliases.match("mesh_drawable const&", ("mesh", ()), ()) is None


def test_match_type_documented_without_arguments(aliases):
    # numarray is documented as "numarray": numarray<T> is generic, numarray<vec3> exact
    assert aliases.match("numarray<T> const&", ("numarray", ()), ("T",)) == "generic"
    assert aliases.match("numarray<vec3> const&", ("numarray", ()), ()) == "exact"


def test_match_family(aliases):
    assert aliases.match_family("numarray_stack<T,N> const&", "numarray_stack", 2, ("T", "N"))
    assert not aliases.match_family("numarray_stack<T,3> const&", "numarray_stack", 2, ("T",))
    assert not aliases.match_family("vec3 const&", "numarray_stack", 2, ())
