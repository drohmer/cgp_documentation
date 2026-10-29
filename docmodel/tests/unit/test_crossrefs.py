"""Links between the guides and the reference: home page of a function, guides of a type,
targets of the inline code spans (crossrefs.py, relations.choose_home)."""

import pytest

from cgp_docmodel import crossrefs, relations
from cgp_docmodel.content import Vocabulary, check_content


def _f(fid, name, category="compute", params=1, home=None):
    return {"id": fid, "key": f"{name}({fid})", "name": name, "category": category, "primary": True,
            "params": [{"type": "x", "name": "", "default": None}] * params, "home": home}


def _entry(fid, generic=False, via=None):
    return {"id": fid, "generic": generic, "via": via, "shared": None}


# ---------------------------------------------------------------- home page of a function

def test_home_of_a_factory_is_its_return_type():
    f = _f("a", "mesh_primitive_sphere", category="construct", params=2)
    cands = [("vec3", "takes", _entry("a"), 0), ("mesh", "returns", _entry("a"), 5)]
    assert relations.choose_home(f, cands, lambda f, t: 1)["type"] == "mesh"


def test_home_of_other_functions_is_the_first_parameter():
    # draw(mesh_drawable, environment): both are taken, mesh_drawable is the first parameter
    f = _f("d", "draw", category="draw", params=2)
    pos = {"environment": 1, "mesh_drawable": 0}
    cands = [("environment", "takes", _entry("d"), 0), ("mesh_drawable", "takes", _entry("d"), 9)]
    assert relations.choose_home(f, cands, lambda f, t: pos[t]) == {
        "type": "mesh_drawable", "group": None, "rel": "takes"}


def test_home_returns_last_for_a_non_factory():
    f = _f("r", "camera_ray", category="compute", params=1)
    cands = [("vec3", "returns", _entry("r"), 0), ("camera", "takes", _entry("r"), 9)]
    assert relations.choose_home(f, cands, lambda f, t: 0)["type"] == "camera"


def test_home_ties_exact_then_direct_then_order():
    f = _f("n", "norm", params=1)
    cands = [("vecN", "takes", _entry("n", generic=True), 0), ("vec3", "takes", _entry("n"), 3),
             ("quaternion", "takes", _entry("n", via="vec4"), 1)]
    assert relations.choose_home(f, cands, lambda f, t: 0)["type"] == "vec3"
    assert relations.choose_home(f, [], lambda f, t: 0) is None


# ---------------------------------------------------------------- guides and links

def _model():
    def struct(compound, fields=(), methods=()):
        return {"compound": compound,
                "fields": [{"id": f"field-{n}", "name": n} for n in fields],
                "methods": [{"id": f"fn-{n}-{i:08x}", "name": n} for i, n in enumerate(methods)]}
    types = {
        "mesh": {"struct": struct("cgp::mesh", fields=["position", "name"]), "family_of": None},
        "mesh_drawable": {"struct": struct("cgp::mesh_drawable", fields=["model"],
                                           methods=["initialize_data_on_gpu", "clear"]), "family_of": None},
        "curve_drawable": {"struct": struct("cgp::curve_drawable", fields=["model"], methods=["clear"]),
                           "family_of": None},
    }
    home = lambda t: {"type": t, "group": None, "rel": "takes"}  # noqa: E731
    functions = [_f("p", "mesh_primitive_sphere", home={"type": "mesh", "group": None, "rel": "returns"}),
                 _f("d1", "draw", home=home("mesh_drawable")), _f("d2", "draw", home=home("curve_drawable"))]
    return {"types": types, "functions": functions}


def _vocab():
    declared = {"mesh": {"position", "name"}, "mesh_drawable": {"model", "initialize_data_on_gpu", "clear"},
                "curve_drawable": {"model", "clear"}}
    return Vocabulary(names={"mesh", "mesh_drawable", "curve_drawable", "mesh_primitive_sphere", "draw"},
                      members=declared, declared=declared)


PAGES = {
    "how-to/draw.md": "---\ntitle: Draw\norder: 2\n---\n"
                      "Call `mesh_primitive_sphere(0.5f)`, then `draw(sphere, environment)` and "
                      "`sphere.initialize_data_on_gpu(m)`. The `model` and `name`.\n",
    "how-to/first.md": "---\ntitle: First\norder: 1\n---\nA `mesh_drawable::model` and `mesh_drawable`.\n",
    "understand/gpu.md": "---\ntitle: GPU\n---\n`mesh` and `camera().clear()`.\n",
    "index.md": "---\ntitle: Home\n---\n`mesh_drawable`\n",
}


@pytest.fixture
def linked(tmp_path):
    for page, text in PAGES.items():
        (tmp_path / page).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / page).write_text(text, encoding="utf-8")
    model, vocab = _model(), _vocab()
    res = check_content(tmp_path, vocab, ignore=["environment"])
    crossrefs.attach(model, res["spans"], vocab, tmp_path, no_link=["name"])
    return model


def test_guides_of_a_type_ordered_by_section_then_order(linked):
    # understand before how-to; inside how-to, order 1 before order 2; index.md is not a guide
    assert [g["path"] for g in linked["types"]["mesh_drawable"]["guides"]] == ["how-to/first.md", "how-to/draw.md"]
    assert [g["path"] for g in linked["types"]["mesh"]["guides"]] == ["understand/gpu.md", "how-to/draw.md"]
    assert linked["types"]["mesh"]["guides"][0] == {"path": "understand/gpu.md", "title": "GPU",
                                                    "section": "understand"}


def test_links_only_for_unambiguous_spans(linked):
    links = linked["content_links"]
    assert links["mesh_drawable"]["kind"] == "type"
    assert links["mesh_primitive_sphere(0.5f)"] == {"kind": "function", "type": "mesh", "group": None,
                                                    "rel": "returns", "id": "p"}
    assert links["mesh_drawable::model"] == {"kind": "field", "type": "mesh_drawable", "group": None,
                                             "rel": None, "id": "field-model"}
    # member declared by one struct only: linked
    assert links["sphere.initialize_data_on_gpu(m)"]["id"].startswith("fn-initialize_data_on_gpu-")
    # draw: overloads on two pages; model: declared by two structs; name: no_link;
    # camera().clear(): two references in one span
    for span in ("draw(sphere, environment)", "model", "name", "camera().clear()"):
        assert span not in links, span


def test_no_link_names_do_not_make_guides(linked):
    # `name` is a field of mesh, but listed in no_link: draw.md is in mesh's guides only
    # through mesh_primitive_sphere, whose home is mesh
    model = _model()
    vocab = _vocab()
    spans = [("how-to/x.md", "name", [(("name", "name"), "name")])]
    crossrefs.attach(model, spans, vocab, None, no_link=["name"])
    assert model["types"]["mesh"]["guides"] == []


# ---------------------------------------------------------------- tasks of a type (types.yaml)

def test_task_spans_resolve_on_the_page_of_the_type(tmp_path):
    (tmp_path / "how-to").mkdir()
    (tmp_path / "how-to" / "draw.md").write_text("---\ntitle: Draw\n---\n", encoding="utf-8")
    model = _model()
    model["types"]["vecN"] = {"struct": None, "family_of": ["mesh_drawable"]}
    model["functions"].append(_f("n", "norm", home={"type": "vecN", "group": None, "rel": "takes"}))
    ed_types = {"mesh_drawable": {"tasks": [
        {"do": "Draw", "use": ["draw(drawable, environment)", "model.translation", "mesh_primitive_sphere(0.5f)",
                               "norm(v)", "mesh"], "guide": "how-to/draw.md"},
        {"do": "Free", "use": ["clear()", "nothing_here()"]}]}}
    errors = crossrefs.attach_tasks(model, ed_types, _vocab(), tmp_path)
    tasks = model["types"]["mesh_drawable"]["tasks"]
    links = {u["code"]: u["link"] for u in tasks[0]["use"]}
    # draw: two overloads, the one whose home is mesh_drawable; model: the field of this type,
    # not the model of curve_drawable; norm: homed on the family page vecN
    assert links["draw(drawable, environment)"]["id"] == "d1"
    assert links["model.translation"] == {"kind": "field", "type": "mesh_drawable", "group": None,
                                          "rel": None, "id": "field-model"}
    assert links["mesh_primitive_sphere(0.5f)"]["type"] == "mesh"
    assert links["norm(v)"]["type"] == "vecN"
    assert links["mesh"]["kind"] == "type"
    assert tasks[0]["guide"] == {"path": "how-to/draw.md", "title": "Draw", "section": "how-to"}
    assert tasks[1]["use"][0]["link"]["id"].startswith("fn-clear-")
    assert errors == ["types.yaml: 'mesh_drawable' task 'Free': `nothing_here()` links to nothing in the reference"]
    assert model["types"]["mesh"]["tasks"] == []
