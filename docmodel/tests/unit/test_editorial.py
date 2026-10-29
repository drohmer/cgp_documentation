"""Editorial files: format errors and stale keys are reported, never ignored."""

from cgp_docmodel import editorial
from cgp_docmodel.paths import Paths


def make_root(tmp_path, types="", descriptions="", annotations="", content_check="", members=""):
    ed = tmp_path / "editorial"
    ed.mkdir()
    (ed / "types.yaml").write_text(types, encoding="utf-8")
    (ed / "descriptions.yaml").write_text(descriptions, encoding="utf-8")
    (ed / "annotations.yaml").write_text(annotations, encoding="utf-8")
    (ed / "content_check.yaml").write_text(content_check, encoding="utf-8")
    (ed / "members.yaml").write_text(members, encoding="utf-8")
    (ed / "function_groups.yaml").write_text("", encoding="utf-8")
    return Paths(tmp_path)


def test_valid_files(tmp_path):
    p = make_root(tmp_path,
                  types="vec3: {canonical: 'numarray_stack<float,3>', group: Vectors, short: 3D vector.}\n",
                  descriptions="'norm(numarray_stack<T,N> const&)': Euclidean length.\n",
                  annotations="'cross(vec3 const&,vec3 const&)': compute\n",
                  content_check="ignore: [gl_Position]\n")
    ed = editorial.load(p)
    assert ed.errors == []
    assert editorial.type_targets(ed) == {"vec3": ("numarray_stack", ("float", "3"))}
    assert ed.content_ignore == ["gl_Position"]


def test_errors_are_reported(tmp_path):
    p = make_root(tmp_path,
                  types="vec3: {canonical: 'numarray_stack<float,3>'}\n",
                  descriptions="'norm(x)': ''\n",
                  annotations="'cross(vec3 const&,vec3 const&)': computation\n")
    errors = "\n".join(editorial.load(p).errors)
    assert "'vec3' lacks 'group'" in errors
    assert "empty description for 'norm(x)'" in errors
    assert "unknown category 'computation'" in errors


def test_invalid_yaml(tmp_path):
    p = make_root(tmp_path, descriptions="key: [unclosed\n")
    assert any("invalid YAML" in e for e in editorial.load(p).errors)


def test_stale_keys(tmp_path):
    p = make_root(tmp_path, descriptions="'gone(int)': Removed function.\n'kept(int)': Still here.\n")
    stale = editorial.stale_keys(editorial.load(p), {"kept(int)"})
    assert stale == ["descriptions.yaml: 'gone(int)' matches no function (renamed or removed?)"]


def test_missing_file_is_an_error(tmp_path):
    p = make_root(tmp_path)
    (tmp_path / "editorial" / "annotations.yaml").unlink()
    assert any("annotations.yaml: file missing" in e for e in editorial.load(p).errors)


def test_non_mapping_is_an_error(tmp_path):
    p = make_root(tmp_path, descriptions="- a list\n- not a mapping\n")
    assert any("expected a mapping" in e for e in editorial.load(p).errors)


def test_non_ascii_description_is_an_error(tmp_path):
    p = make_root(tmp_path, descriptions="'norm(x)': Norme euclidienne → réel.\n")
    assert any("non-ASCII" in e for e in editorial.load(p).errors)


def test_figures(tmp_path):
    p = make_root(tmp_path, types=(
        "mesh: {canonical: mesh, group: G, short: S., figures: [{src: reference/mesh.svg, caption: Arrays.}]}\n"
        "image: {canonical: image, group: G, short: S., figures: [{src: missing.svg, caption: X.}]}\n"
        "grid: {canonical: grid, group: G, short: S., figures: [{src: reference/mesh.svg}]}\n"))
    (tmp_path / "content" / "assets" / "reference").mkdir(parents=True)
    (tmp_path / "content" / "assets" / "reference" / "mesh.svg").write_text("<svg/>")
    errors = "\n".join(editorial.load(p).errors)
    assert "'mesh'" not in errors
    assert "'image' figure 'missing.svg' not found" in errors
    assert "'grid' figures must be a list of {src, caption}" in errors


def test_members(tmp_path):
    p = make_root(tmp_path, members="'timer_basic::t': Elapsed time in seconds.\n'timer_basic::gone()': Removed.\n"
                                     "'timer_basic::scale': ''\n")
    ed = editorial.load(p)
    assert "members.yaml: empty description for 'timer_basic::scale'" in ed.errors
    stale = editorial.stale_keys(ed, set(), {"timer_basic::t", "timer_basic::scale"})
    assert stale == ["members.yaml: 'timer_basic::gone()' matches no member of a documented type (renamed or removed?)"]


def test_tasks_format(tmp_path):
    head = "mesh: {canonical: mesh, group: Meshes, short: Mesh., tasks: "
    cases = [("[{do: Draw, use: ['draw(m, env)'], guide: how-to/draw.md}]", None),
             ("[{do: Draw}]", "tasks must be a list of"),
             ("[{do: Draw, use: []}]", "tasks must be a list of"),
             ("[{do: Draw, use: [x], see: y}]", "tasks must be a list of"),
             ("[{do: Draw it, use: [x]}]", "one ASCII word"),
             ("[{do: Draw, use: [x], guide: how-to/none.md}]", "guide 'how-to/none.md' not found")]
    for i, (tasks, message) in enumerate(cases):
        root = tmp_path / str(i)
        (root / "content" / "how-to").mkdir(parents=True)
        (root / "content" / "how-to" / "draw.md").write_text("---\ntitle: Draw\n---\n", encoding="utf-8")
        errors = editorial.load(make_root(root, types=head + tasks + "}\n")).errors
        if message is None:
            assert errors == [], tasks
        else:
            assert any(message in e for e in errors), tasks


GROUPS = {
    "math": {"title": "M", "short": "m", "under": "Vectors", "modules": ["01_base"], "names": ["abs", "is_*"]},
    "strings": {"title": "S", "short": "s", "under": "Utilities", "modules": ["01_base", "02_numarray"], "names": ["str"]},
    "base": {"title": "B", "short": "b", "under": "Utilities", "modules": ["01_base"]},
}


def test_function_group_by_name_then_module():
    # a page with `names` takes the functions of these names; the page without `names` the rest
    assert editorial.function_group_of(GROUPS, "01_base", "abs") == "math"
    assert editorial.function_group_of(GROUPS, "01_base", "is_equal") == "math"
    assert editorial.function_group_of(GROUPS, "01_base", "str") == "strings"
    assert editorial.function_group_of(GROUPS, "01_base", "ptr") == "base"
    assert editorial.function_group_of(GROUPS, "02_numarray", "str") == "strings"
    assert editorial.function_group_of(GROUPS, "02_numarray", "ptr") is None   # no default page: build error
    assert editorial.function_group_of(GROUPS, "99_other", "abs") is None


def test_function_group_errors():
    ed = editorial.Editorial(types={"vec3": {"group": "Vectors"}}, function_groups=dict(GROUPS))
    assert editorial._function_group_errors(ed) == []
    ed.function_groups["bad"] = {"title": "X", "short": "x", "under": "Nowhere", "modules": ["01_base"]}
    errors = "\n".join(editorial._function_group_errors(ed))
    assert "'bad' under 'Nowhere' is no group of types.yaml" in errors
    assert "module 01_base is taken by default by 'base' and 'bad'" in errors
