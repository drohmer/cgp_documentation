"""Content check: code spans, references, resolution against the vocabulary."""

import pytest

from cgp_docmodel.content import Vocabulary, check_content, code_spans, references

PAGE = """# Title

Call `mesh_primitive_sphere(0.25f)` then `draw(sphere, environment)`.
The field `mesh_drawable::model` and the uniform `glUniform3f`.
A typo: `mesh_primitve_cube()` and a stale `old_function`.
Wrong owner: `mesh::look_at`. Typo in a member: `sphere.textur`.
Good member: `sphere.texture`, call `camera_control.camera().matrix_view()`.

```cpp
not_checked_inside_fences();
```
`x + y` is not a name.
"""


@pytest.fixture
def vocab():
    return Vocabulary(
        names={"mesh_primitive_sphere", "draw", "mesh_drawable", "mesh", "camera"},
        members={"mesh_drawable": {"model", "texture"}, "mesh": {"position"},
                 "camera_orbit": {"matrix_view", "look_at"}, "camera_controller_orbit": {"camera"}},
    )


def test_code_spans_skip_fences():
    spans = [s for _, s in code_spans(PAGE)]
    assert "mesh_primitive_sphere(0.25f)" in spans
    assert not any("not_checked" in s for s in spans)


@pytest.mark.parametrize("span, refs", [
    ("norm(v)", [("name", "norm")]),
    ("mesh_drawable::model", [("qualified", "mesh_drawable", "model")]),
    ("sphere.texture", [("member", "texture")]),
    ("camera().matrix_view()", [("name", "camera"), ("member", "matrix_view")]),
    ("x + y", []),
])
def test_references(span, refs):
    assert references(span) == refs


def test_check_content(tmp_path, vocab):
    (tmp_path / "guide").mkdir()
    (tmp_path / "guide" / "page.md").write_text(PAGE, encoding="utf-8")
    res = check_content(tmp_path, vocab, ignore=["glUniform*", "environment", "camera_control"])
    assert res["refs"]["mesh_primitive_sphere"] == ["guide/page.md"]
    assert "mesh_drawable::model" in res["refs"]
    unresolved = {name for _, _, name in res["unresolved"]}
    # typo, stale name, member of another struct, typo in a member
    assert unresolved == {"mesh_primitve_cube", "old_function", "mesh::look_at", "textur"}
    assert all(line > 0 for _, line, _ in res["unresolved"])


def test_local_names_of_a_page(tmp_path, vocab):
    # the names of the code of an example are ignored on its page only
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "a.md").write_text(
        "---\ntitle: A\nlocal_names: [update_field, blob_*]\n---\n`update_field()` `blob_a` `old_function`\n",
        encoding="utf-8")
    (tmp_path / "examples" / "b.md").write_text("---\ntitle: B\n---\n`update_field()`\n", encoding="utf-8")
    res = check_content(tmp_path, vocab, ignore=[])
    unresolved = {(page, name) for page, _, name in res["unresolved"]}
    assert unresolved == {("examples/a.md", "old_function"), ("examples/b.md", "update_field")}
