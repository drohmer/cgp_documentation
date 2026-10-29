"""The real model built from cgp-2027: contract, invariants, known facts, determinism.

"Known facts" encode what a reader expects from the documentation of CGP. If one fails
after a change of the C++ sources, the fact may need updating; if it fails after a
change of cgp_docmodel, the change is probably a regression. Several facts come from the
independent audit of 2026-10-28 (bugs that the first test suite did not catch).
"""

import json

import pytest

from cgp_docmodel import checks, cli, editorial
from cgp_docmodel.paths import default_paths
from cgp_docmodel.report import snapshots

pytestmark = pytest.mark.integration


def names(model, fns, type_name, rel):
    return {fns[e["id"]]["name"] for e in model["types"][type_name][rel]}


def fn(model, name, contains=""):
    found = [f for f in model["functions"] if f["name"] == name and contains in f["key"]]
    assert found, f"no function {name} with '{contains}' in its key"
    return found[0]


# ---------------------------------------------------------------- contract

def test_schema(built, model):
    paths, _ = built
    assert checks.schema_errors(model, paths.schema) == []


def test_invariants(model):
    assert checks.invariant_errors(model) == []


def test_check_command_passes(built):
    assert cli.main(["check"]) == 0


def test_editorial_keys_all_resolve(model):
    ed = editorial.load(default_paths())
    assert ed.errors == []
    members = {m["key"] for t in model["types"].values() if t["struct"]
               for m in t["struct"]["fields"] + t["struct"]["methods"]}
    assert editorial.stale_keys(ed, {f["key"] for f in model["functions"]}, members) == []


# ---------------------------------------------------------------- relations

@pytest.mark.parametrize("name", ["norm", "dot", "cross", "normalize"])
def test_vec3_takes(model, fns, name):
    assert name in names(model, fns, "vec3", "takes")


def test_cross_is_vec3_only(model, fns):
    assert "cross" not in names(model, fns, "vec2", "takes")
    assert "cross" not in names(model, fns, "vec4", "takes")


def test_generic_flags(model, fns):
    takes = model["types"]["vec3"]["takes"]
    norm = [e for e in takes if fns[e["id"]]["name"] == "norm"]
    cross = [e for e in takes if fns[e["id"]]["name"] == "cross"]
    assert norm and all(e["generic"] for e in norm)
    assert cross and not any(e["generic"] for e in cross)
    sums = [e for e in model["types"]["numarray"]["takes"] if fns[e["id"]]["name"] == "sum"]
    assert sums and all(e["generic"] for e in sums), "numarray<T> functions are generic"


def test_inherited_relations(model, fns):
    q = model["types"]["quaternion"]
    via = {fns[e["id"]]["name"]: e["via"] for e in q["takes"]}
    assert via.get("norm") == "numarray_stack<float,4>", "quaternion derives from vec4"
    assert via.get("conjugate") is None
    cam = {fns[e["id"]]["name"]: e["via"] for e in model["types"]["camera_orbit"]["takes"]}
    assert cam.get("picking_spheres") == "camera_generic_base"


def test_mesh_factories(model, fns):
    assert {"mesh_primitive_sphere", "mesh_primitive_cube", "mesh_primitive_cylinder"} <= names(model, fns, "mesh", "returns")
    assert fn(model, "mesh_primitive_sphere")["category"] == "construct"


def test_families(model, fns):
    vecN = model["types"]["vecN"]
    assert vecN["family_of"] == ["vec2", "vec3", "vec4"]
    assert {"norm", "dot", "normalize"} <= names(model, fns, "vecN", "takes")
    assert "cross" not in names(model, fns, "vecN", "takes")
    v3 = {fns[e["id"]]["name"]: e["shared"] for e in model["types"]["vec3"]["takes"]}
    assert v3["norm"] == "vecN" and v3["cross"] is None
    q = {fns[e["id"]]["name"]: e["shared"] for e in model["types"]["quaternion"]["takes"]}
    assert q["norm"] == "vecN", "through its base vec4"
    assert q["conjugate"] is None
    assert {"transpose", "trace"} <= names(model, fns, "matN", "takes")
    assert "get" not in names(model, fns, "vecN", "returns"), "matrix row/column extraction belongs to matN"


# ---------------------------------------------------------------- structs

def test_specializations_are_used(model):
    vec3 = model["types"]["vec3"]["struct"]
    assert vec3["compound"] == "numarray_stack<T,3>"
    assert {f["name"] for f in vec3["fields"]} == {"x", "y", "z"}, "no 'data' copied from the primary template"
    mat4 = {m["name"] for m in model["types"]["mat4"]["struct"]["methods"]}
    mat2 = {m["name"] for m in model["types"]["mat2"]["struct"]["methods"]}
    assert {"build_translation", "get_block_linear"} <= mat4
    assert "build_translation" not in mat2


def test_inherited_members(model):
    q = model["types"]["quaternion"]["struct"]
    assert q["bases"] == ["numarray_stack<float,4>"]
    fields = {f["name"]: f["inherited_from"] for f in q["fields"]}
    assert fields.get("x") == "numarray_stack<float,4>"


def test_const_method_pairs_merged(model):
    methods = model["types"]["vec3"]["struct"]["methods"]
    ops = [m for m in methods if m["name"] == "operator[]"]
    assert len(ops) == 1 and ops[0]["key"].endswith("const") and len(ops[0]["variants"]) == 1


# ---------------------------------------------------------------- parameters and scope

def test_defaults_read_from_header(model):
    draw = fn(model, "draw", "(mesh_drawable const&")
    assert draw["params_source"] == "header"
    defaults = {p["name"]: p["default"] for p in draw["params"]}
    assert defaults["instance_count"] == "1" and defaults["expected_uniforms"] == "true"
    assert [p["name"] for p in fn(model, "normal_per_vertex")["params"]][2] == "normals_to_fill"
    assert all(p["default"] for p in fn(model, "opengl_uniform", "float")["params"][-1:])


def test_template_overloads_kept(model):
    gets = {f["key"] for f in model["functions"] if f["name"] == "get" and "matrix_stack" in f["key"]}
    assert "get<idx1,T,N1,N2>(matrix_stack<T,N1,N2> const&)" in gets
    assert "get<idx1,idx2,T,N1,N2>(matrix_stack<T,N1,N2> const&)" in gets


def test_only_header_declared_functions(model):
    assert all(f["file"].endswith((".hpp", ".h")) for f in model["functions"])
    names_ = {f["name"] for f in model["functions"]}
    assert not {"generator", "distribution", "distribution_normal"} & names_, "static variables of rand.cpp"
    assert {"compile_shader", "glfw_create_window"} <= {e["key"].split("(")[0] for e in model["excluded"]}
    lower = fn(model, "str_lower")
    assert lower["file"] == "01_base/string/string.hpp", "declared in the header although defined in the .cpp"


def test_categories_of_core_functions(model):
    cat = {f["key"]: f["category"] for f in model["functions"]}
    assert cat[fn(model, "norm", "numarray_stack")["key"]] == "compute"
    assert cat[fn(model, "normalize", "numarray_stack")["key"]] == "transform"
    assert fn(model, "camera_ray_direction")["category"] == "compute"
    assert fn(model, "str_lower")["category"] == "convert"


def test_provenance(model):
    commit = model["generator"]["source"]["commit"]
    for f in model["functions"]:
        assert (f["category_source"] == "heuristic") == (f["category_rule"] is not None)
        if commit:
            assert f"/blob/{commit}/cgp/" in f["source_url"], "links pinned to the extracted commit"


# ---------------------------------------------------------------- audit

def test_deterministic(built, tmp_path, monkeypatch):
    """Two builds of the same inputs are byte-identical."""
    paths, _ = built
    first = paths.api_json.read_bytes()
    monkeypatch.setenv("CGP_BUILD_DIR", str(tmp_path))
    assert cli.main(["build"]) == 0
    assert (tmp_path / "api.json").read_bytes() == first


@pytest.mark.parametrize("golden", ["functions.txt", "relations.txt", "structs.txt", "excluded.txt"])
def test_golden_snapshot(built, model, golden):
    """The model equals the reviewed snapshots. On purpose changes: `cgp-docmodel snapshot --update`."""
    paths, _ = built
    current = {p.name: text for p, text in snapshots(model, paths.golden_dir).items()}
    path = paths.golden_dir / golden
    assert path.exists(), "no golden snapshot: run `cgp-docmodel snapshot --update` and review it"
    assert current[golden] == path.read_text(encoding="utf-8"), f"run `cgp-docmodel snapshot` to see the diff"


def test_content_pages_resolve(built):
    paths, _ = built
    index = json.loads(paths.content_index.read_text(encoding="utf-8"))
    assert "how-to/draw-a-mesh.md" in index["initialize_data_on_gpu"]
    assert "understand/camera-and-matrices.md" in index["opengl_uniform"]
    assert "mesh_drawable::model" in index


def test_check_exit_code_when_build_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CGP_BUILD_DIR", str(tmp_path / "nothing"))
    assert cli.main(["check"]) == 2


def test_every_public_function_has_a_page(model):
    """A function on no type page goes to a page of function_groups.yaml (rand_uniform...)."""
    on_types = {e["id"] for t in model["types"].values() for rel in ("takes", "returns", "operators") for e in t[rel]}
    in_groups = {e["id"] for g in model["function_groups"].values() for e in g["functions"]}
    primaries = {f["id"] for f in model["functions"] if f["primary"]}
    assert primaries <= on_types | in_groups
    assert not (on_types & in_groups)
    assert fn(model, "rand_uniform")["id"] in {e["id"] for e in model["function_groups"]["random-noise"]["functions"]}


def test_module_without_group_is_an_error(built, monkeypatch, tmp_path):
    """Removing a module from function_groups.yaml makes the build fail (no silent loss)."""
    from cgp_docmodel import model as model_mod
    paths = built[0]
    real = editorial.load
    def load_without_random(p):
        ed = real(p)
        ed.function_groups = {k: v for k, v in ed.function_groups.items() if k != "random-noise"}
        return ed
    monkeypatch.setattr(editorial, "load", load_without_random)
    errors = model_mod.build_model(paths)[3]
    assert any("rand_uniform" in e and "in no group" in e for e in errors)


# ---------------------------------------------------------------- guides and links (schema 1.5)

def test_home_pages(model):
    """Factories live on the type they return, the other functions on their first parameter."""
    assert fn(model, "mesh_primitive_sphere")["home"] == {"type": "mesh", "group": None, "rel": "returns"}
    assert fn(model, "draw", "(mesh_drawable const&")["home"]["type"] == "mesh_drawable"
    assert fn(model, "norm", "numarray_stack")["home"]["type"] == "vecN"
    assert fn(model, "rand_uniform")["home"] == {"type": None, "group": "random-noise", "rel": "functions"}
    assert all((f["home"] is None) != f["primary"] for f in model["functions"])


def test_guides_of_types(model):
    paths = [g["path"] for g in model["types"]["mesh_drawable"]["guides"]]
    assert {"how-to/draw-a-mesh.md", "understand/cpu-to-gpu.md"} <= set(paths)
    sections = [crossref_sections.index(g["section"]) for g in model["types"]["mesh_drawable"]["guides"]]
    assert sections == sorted(sections)
    assert "understand/hierarchies.md" in [g["path"] for g in model["types"]["hierarchy_mesh_drawable"]["guides"]]


def test_content_links(model):
    links = model["content_links"]
    assert links["mesh_drawable"]["kind"] == "type"
    assert links["mesh_primitive_sphere"]["type"] == "mesh"
    assert links["mesh_drawable::model"] == {"kind": "field", "type": "mesh_drawable", "group": None,
                                             "rel": None, "id": "field-model"}
    assert links["rotation_transform::from_axis_angle"]["kind"] == "method"
    assert "draw" not in links  # overloads documented on several type pages
    assert "name" not in links  # editorial/content_check.yaml no_link


crossref_sections = ["get-started", "understand", "how-to", "examples"]


# ---------------------------------------------------------------- tasks of the types (schema 1.6)

def test_tasks_of_types(model):
    tasks = {k["do"]: k for k in model["types"]["mesh_drawable"]["tasks"]}
    draw = tasks["Draw"]["use"][0]
    assert draw["link"]["type"] == "mesh_drawable" and draw["link"]["kind"] == "function"
    assert tasks["Create"]["guide"]["path"] == "how-to/draw-a-mesh.md"
    assert model["types"]["vec3"]["tasks"][0]["use"][0]["link"]["type"] == "vecN"  # norm
    assert model["types"]["grid_3D"]["tasks"] == []


# ---------------------------------------------------------------- function pages by theme (schema 1.7)

def test_function_groups_by_theme(model):
    groups = model["function_groups"]
    types_groups = {t["group"] for t in model["types"].values()}
    assert all(g["under"] in types_groups | {"Utilities"} for g in groups.values())
    assert fn(model, "clamp")["home"]["group"] == "scalar-math"
    assert fn(model, "str_lower")["home"]["group"] == "strings"
    assert fn(model, "call_error")["home"]["group"] == "errors-memory"
    assert groups["marching-cubes"]["under"] == "Meshes and drawables"
    assert "opengl_ebo_structure" in model["types"] and "opengl_gpu_buffer" in model["types"]
