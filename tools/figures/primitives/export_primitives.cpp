// Export the meshes of the mesh_primitive_* functions of CGP to JSON (no OpenGL needed),
// read by render_primitives.py to draw the figures of content/how-to/create-basic-shapes.md.
// Each entry is built by the actual CGP function: the figures show the real triangles.
// Build and run: see run.sh in this folder.
#include "cgp/cgp.hpp"
#include <fstream>
#include <iostream>

using namespace cgp;

static void write_mesh(std::ostream& out, std::string const& name, std::string const& call, mesh const& m, bool last)
{
    out << "  \"" << name << "\": {\"call\": \"" << call << "\", \"position\": [";
    for (size_t k = 0; k < m.position.size(); ++k)
        out << (k ? "," : "") << "[" << m.position[k].x << "," << m.position[k].y << "," << m.position[k].z << "]";
    out << "], \"normal\": [";
    for (size_t k = 0; k < m.normal.size(); ++k)
        out << (k ? "," : "") << "[" << m.normal[k].x << "," << m.normal[k].y << "," << m.normal[k].z << "]";
    out << "], \"color\": [";
    for (size_t k = 0; k < m.color.size(); ++k)
        out << (k ? "," : "") << "[" << m.color[k].x << "," << m.color[k].y << "," << m.color[k].z << "]";
    out << "], \"connectivity\": [";
    for (size_t k = 0; k < m.connectivity.size(); ++k)
        out << (k ? "," : "") << "[" << m.connectivity[k][0] << "," << m.connectivity[k][1] << "," << m.connectivity[k][2] << "]";
    out << "]}" << (last ? "\n" : ",\n");
}

int main(int argc, char** argv)
{
    std::string const path = argc > 1 ? argv[1] : "primitives.json";
    std::ofstream out(path);
    out << "{\n";
    // Default arguments everywhere, except the ellipsoid (its default scale {1,1,1} is a sphere)
    //  and the cylinder drawn a second time closed.
    write_mesh(out, "sphere", "mesh_primitive_sphere()", mesh_primitive_sphere(), false);
    write_mesh(out, "ellipsoid", "mesh_primitive_ellipsoid({1.0f, 0.6f, 0.4f})", mesh_primitive_ellipsoid({1.0f, 0.6f, 0.4f}), false);
    write_mesh(out, "cube", "mesh_primitive_cube()", mesh_primitive_cube(), false);
    write_mesh(out, "cubic_grid", "mesh_primitive_cubic_grid()", mesh_primitive_cubic_grid(), false);
    write_mesh(out, "cylinder", "mesh_primitive_cylinder()", mesh_primitive_cylinder(), false);
    write_mesh(out, "cylinder_closed", "mesh_primitive_cylinder(0.2f, {0,0,0}, {0,0,1}, 10, 20, true)", mesh_primitive_cylinder(0.2f, {0,0,0}, {0,0,1}, 10, 20, true), false);
    write_mesh(out, "cone", "mesh_primitive_cone()", mesh_primitive_cone(), false);
    write_mesh(out, "torus", "mesh_primitive_torus()", mesh_primitive_torus(), false);
    write_mesh(out, "disc", "mesh_primitive_disc()", mesh_primitive_disc(), false);
    write_mesh(out, "grid", "mesh_primitive_grid()", mesh_primitive_grid(), false);
    write_mesh(out, "quadrangle", "mesh_primitive_quadrangle()", mesh_primitive_quadrangle(), false);
    write_mesh(out, "triangle", "mesh_primitive_triangle()", mesh_primitive_triangle(), false);
    write_mesh(out, "tetrahedron", "mesh_primitive_tetrahedron()", mesh_primitive_tetrahedron(), false);
    write_mesh(out, "arrow", "mesh_primitive_arrow()", mesh_primitive_arrow(), false);
    write_mesh(out, "frame", "mesh_primitive_frame()", mesh_primitive_frame(), true);
    out << "}\n";
    std::cout << "wrote " << path << std::endl;
    return 0;
}
