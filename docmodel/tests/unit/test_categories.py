"""Category heuristic: one case per rule of categories.RULES, plus rule coverage."""

import pytest

from cgp_docmodel.categories import CATEGORIES, RULES, classify
from cgp_docmodel.cpptypes import AliasTable


def fn(name, ret="void", params=(), tparams=()):
    return {"name": name, "ret": ret, "tparams": list(tparams),
            "params": [{"type": t, "name": "", "default": None} for t in params]}


@pytest.fixture
def aliases():
    t = AliasTable()
    t.add("vec3", "numarray_stack<float,3>")
    return t


STRUCTS = {"mesh", "numarray_stack", "quaternion"}

CASES = [
    # (function, expected category, expected rule)
    (fn("operator+", "vec3", ["vec3 const&", "vec3 const&"]), "operator", "name:operator"),
    (fn("draw", "void", ["mesh_drawable const&"]), "draw", "name:draw*"),
    (fn("mesh_load_file_obj", "mesh", ["std::string const&"]), "io", "name:io"),
    (fn("str", "std::string", ["vec3 const&"]), "convert", "name:convert"),
    (fn("get", "T const&", ["grid_2D<T> const&"], ["T"]), "access", "name:access"),
    (fn("mesh_primitive_sphere", "mesh", ["float", "vec3 const&"]), "construct", "name:factory"),
    (fn("fill_position", "void", ["mesh&"]), "other", "returns:void"),
    (fn("norm", "T", ["numarray_stack<T,N> const&"], ["T", "N"]), "compute", "returns:scalar"),
    (fn("normalize", "quaternion", ["quaternion const&"]), "transform", "returns:same-type-as-a-parameter"),
    (fn("tensor_product", "mesh", ["vec3 const&", "vec3 const&"]), "construct", "returns:documented-type-from-scalars"),
    (fn("intersection", "intersection_structure", ["mesh const&"]), "compute", "fallback"),
]


@pytest.mark.parametrize("f, category, rule", CASES, ids=[c[2] for c in CASES])
def test_rule(aliases, f, category, rule):
    assert classify(f, aliases, STRUCTS) == (category, rule)


def test_every_rule_has_a_case():
    """Adding a rule without a test case fails here."""
    assert {r[0] for r in RULES} == {c[2] for c in CASES}


def test_rules_produce_known_categories():
    assert {r[1] for r in RULES} <= set(CATEGORIES)


# Misclassifications found by the audit of 2026-10-28 (must not come back)
REGRESSIONS = [
    (fn("camera_ray_direction", "vec3", ["mat4 const&", "mat4 const&", "vec2 const&"]), "compute"),
    (fn("abs", "long", ["long"]), "compute"),
    (fn("element", "T const&", ["grid_2D<T> const&", "int"], ["T"]), "access"),
    (fn("str_lower", "std::string", ["std::string const&"]), "convert"),
    (fn("opengl_buffer_data_initialize_generic", "GLuint", ["GLuint"]), "compute"),
    (fn("thread_count", "int", []), "compute"),          # 'read' inside a word is not io
    (fn("upload_texture", "void", ["image_structure const&"]), "other"),
]


@pytest.mark.parametrize("f, category", REGRESSIONS, ids=[r[0]["name"] for r in REGRESSIONS])
def test_audit_regressions(aliases, f, category):
    aliases.add("vec2", "numarray_stack<float,2>")
    aliases.add("mat4", "matrix_stack<float,4,4>")
    assert classify(f, aliases, STRUCTS)[0] == category
