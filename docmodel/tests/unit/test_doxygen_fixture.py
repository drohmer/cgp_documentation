"""DoxygenXML on a tiny synthetic XML: collisions and .cpp-only functions are never silent."""

from cgp_docmodel.doxygen import DoxygenXML

INDEX = """<?xml version='1.0'?><doxygenindex>
<compound refid="namespacecgp" kind="namespace"><name>cgp</name></compound>
</doxygenindex>"""


def memberdef(name, ptype, declfile, line):
    return f"""<memberdef kind="function" id="x{line}" prot="public" static="no" const="no">
  <type>float</type><name>{name}</name>
  <param><type>{ptype}</type><declname>v</declname></param>
  <briefdescription></briefdescription><detaileddescription></detaileddescription>
  <location file="{declfile}" line="{line}" declfile="{declfile}" declline="{line}"/>
</memberdef>"""


def write_xml(tmp_path, members):
    (tmp_path / "index.xml").write_text(INDEX, encoding="utf-8")
    body = "\n".join(members)
    (tmp_path / "namespacecgp.xml").write_text(
        f"<doxygen><compounddef id='namespacecgp' kind='namespace'><compoundname>cgp</compoundname>"
        f"<sectiondef>{body}</sectiondef></compounddef></doxygen>", encoding="utf-8")
    return DoxygenXML(tmp_path)


def test_collision_is_an_error(tmp_path):
    h = "/src/cgp-2027/cgp/05_vec/vec3/vec3.hpp"
    xml = write_xml(tmp_path, [memberdef("norm", "vec3 const &amp;", h, 10), memberdef("norm", "vec3 const&amp;", h, 20)])
    funcs, excluded, errors = xml.free_functions()
    assert len(funcs) == 1
    assert len(errors) == 1 and "key collision" in errors[0] and "norm(vec3 const&)" in errors[0]


def test_cpp_only_function_is_excluded_with_a_reason(tmp_path):
    cpp = "/src/cgp-2027/cgp/13_opengl/shaders/shaders.cpp"  # no shaders.hpp next to it
    xml = write_xml(tmp_path, [memberdef("compile_shader", "int", cpp, 5)])
    funcs, excluded, errors = xml.free_functions()
    assert funcs == [] and errors == []
    assert excluded == [("compile_shader(int) [13_opengl/shaders/shaders.cpp:5]", "declared in a .cpp file (not public API)")]
