"""Reading declarations in headers (names and default values lost by Doxygen)."""

import pytest

from cgp_docmodel.cpptypes import normalize
from cgp_docmodel.header import HeaderReader, declaration_params, split_top_level


def test_split_top_level():
    assert split_top_level("std::map<int,float> a, vec3 const& b = {0,0,1}, std::string s = \"a,b\"") == \
        ["std::map<int,float> a", "vec3 const& b = {0,0,1}", 'std::string s = "a,b"']


DRAW = """\tvoid draw(mesh_drawable const& drawable,
\t\tenvironment_generic_structure const& environment = environment_generic_structure(), // comment, with comma
\t\tint instance_count = 1, bool expected_uniforms = true,
\t\tGLenum draw_mode = GL_TRIANGLES);
"""


def test_multiline_declaration_with_defaults():
    assert declaration_params(DRAW, "draw") == [
        ("drawable", None),
        ("environment", "environment_generic_structure()"),
        ("instance_count", "1"),
        ("expected_uniforms", "true"),
        ("draw_mode", "GL_TRIANGLES"),
    ]


@pytest.mark.parametrize("text, expected", [
    ("vec3 cross(vec3 const&, vec3 const&);", [("", None), ("", None)]),        # unnamed
    ("void f(unsigned int, float radius = 1.0f);", [("", None), ("radius", "1.0f")]),
    ("int f();", []),
    ("int f(void);", []),
    ("mesh g(numarray<vec3> const& p = {});", [("p", "{}")]),
])
def test_declaration_variants(text, expected):
    assert declaration_params(text, text.split("(")[0].split()[-1]) == expected


def test_name_must_not_be_part_of_another_name():
    assert declaration_params("void my_draw(int a); void draw(float b);", "draw") == [("b", None)]


def test_find_declaration_picks_the_right_overload(tmp_path):
    h = tmp_path / "string.hpp"
    h.write_text("// header\nstd::string str(std::string const& s);\n\nstd::string str(char const* s);\n",
                 encoding="utf-8")
    r = HeaderReader()
    assert r.find_declaration(str(h), "str", ["char const*"], normalize) == 4
    assert r.find_declaration(str(h), "str", ["std::string const&"], normalize) == 2
    assert r.find_declaration(str(h), "str", ["int"], normalize) is None


def test_params_ignores_cpp_files(tmp_path):
    cpp = tmp_path / "a.cpp"
    cpp.write_text("void f(int a = 1) {}\n", encoding="utf-8")
    assert HeaderReader().params(str(cpp), 1, "f") is None
