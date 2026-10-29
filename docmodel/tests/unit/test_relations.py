"""Const-variant grouping and type relations on synthetic records."""

from cgp_docmodel.cpptypes import AliasTable
from cgp_docmodel.relations import family_relations, group_variants, mark_shared, type_relations


def rec(id_, name, key, params=(), ret="void", const=False, tparams=(), ns="cgp"):
    return {"id": id_, "name": name, "key": key, "namespace": ns, "const": const, "ret": ret,
            "tparams": list(tparams), "signature": key,
            "params": [{"type": t, "name": "", "default": None} for t in params]}


def test_const_pair_is_merged():
    a = rec("a", "operator[]", "numarray_stack::operator[](int) const", ["int"], "T const&", const=True)
    b = rec("b", "operator[]", "numarray_stack::operator[](int)", ["int"], "T&")
    prim = group_variants([b, a])
    assert prim == [a]
    assert a["primary"] and a["variants"] == [{"id": "b", "signature": b["signature"]}]
    assert b["primary"] is False and b["variant_of"] == "a"


def test_const_ref_parameter_pair_is_merged():
    a = rec("a", "get", "get(grid const&)", ["grid const&"])
    b = rec("b", "get", "get(grid&)", ["grid&"])
    assert group_variants([a, b]) == [a]


def test_real_overloads_are_kept():
    a = rec("a", "draw", "draw(mesh_drawable const&)", ["mesh_drawable const&"])
    b = rec("b", "draw", "draw(curve_drawable const&)", ["curve_drawable const&"])
    assert len(group_variants([a, b])) == 2


def test_type_relations():
    t = AliasTable()
    t.add("vec3", "numarray_stack<float,3>")
    vec3 = ("numarray_stack", ("float", "3"))
    funcs = [
        rec("norm", "norm", "norm(numarray_stack<T,N> const&)", ["numarray_stack<T,N> const&"], "T", tparams=["T", "N"]),
        rec("cross", "cross", "cross(vec3 const&,vec3 const&)", ["vec3 const&", "vec3 const&"], "vec3"),
        rec("orth", "orth", "orth(float)", ["float"], "vec3"),
        rec("plus", "operator+", "operator+(vec3 const&,vec3 const&)", ["vec3 const&", "vec3 const&"], "vec3"),
        rec("other", "f", "f(mesh const&)", ["mesh const&"], "mesh"),
    ]
    group_variants(funcs)
    r = type_relations(vec3, funcs, t)
    assert r["takes"] == [{"id": "norm", "generic": True, "via": None},
                          {"id": "cross", "generic": False, "via": None}]
    assert r["returns"] == [{"id": "orth", "generic": False, "via": None}]
    assert r["operators"] == [{"id": "plus", "generic": False, "via": None}]


def test_functions_of_a_base_class_apply_via_the_base():
    t = AliasTable()
    vec4 = ("numarray_stack", ("float", "4"))
    funcs = [
        rec("norm", "norm", "norm<T,N>(numarray_stack<T,N> const&)", ["numarray_stack<T,N> const&"], "T", tparams=["T", "N"]),
        rec("make", "make", "make(float)", ["float"], "numarray_stack<float,4>"),
        rec("conj", "conjugate", "conjugate(quaternion const&)", ["quaternion const&"], "quaternion"),
    ]
    group_variants(funcs)
    r = type_relations(("quaternion", ()), funcs, t, ancestors=[vec4])
    assert {"id": "norm", "generic": True, "via": "numarray_stack<float,4>"} in r["takes"]
    assert {"id": "conj", "generic": False, "via": None} in r["takes"]
    assert r["returns"] == []  # a function returning a vec4 does not return a quaternion


def test_family_and_shared_entries():
    t = AliasTable()
    t.add("vec3", "numarray_stack<float,3>")
    funcs = [
        rec("norm", "norm", "norm<T,N>(numarray_stack<T,N> const&)", ["numarray_stack<T,N> const&"], "T", tparams=["T", "N"]),
        rec("n3", "f3", "f3<T>(numarray_stack<T,3> const&)", ["numarray_stack<T,3> const&"], "T", tparams=["T"]),  # size 3 only
        rec("cross", "cross", "cross(vec3 const&,vec3 const&)", ["vec3 const&", "vec3 const&"], "vec3"),
        rec("mv", "operator*", "operator*<T,N1,N2>(matrix_stack<T,N1,N2> const&,numarray_stack<T,N2> const&)",
            ["matrix_stack<T,N1,N2> const&", "numarray_stack<T,N2> const&"], "numarray_stack<T,N1>", tparams=["T", "N1", "N2"]),
    ]
    group_variants(funcs)
    vecN = ("numarray_stack", ("T", "N"))
    matN = ("matrix_stack", ("T", "N1", "N2"))
    fam = family_relations(vecN, funcs, t)
    assert [e["id"] for e in fam["takes"]] == ["norm"]           # not f3 (size 3 only), not cross
    assert [e["id"] for e in fam["operators"]] == ["mv"]
    types = {
        "vecN": {"canonical": "numarray_stack<T,N>", "family_of": ["vec3"], **fam},
        "matN": {"canonical": "matrix_stack<T,N1,N2>", "family_of": ["mat3"], **family_relations(matN, funcs, t)},
        "vec3": {"canonical": "numarray_stack<float,3>", "family_of": None,
                 **type_relations(("numarray_stack", ("float", "3")), funcs, t)},
    }
    mark_shared(types)
    shared = {e["id"]: e["shared"] for rel in ("takes", "operators") for e in types["vec3"][rel]}
    assert shared == {"norm": "vecN", "n3": None, "cross": None, "mv": "vecN"}
