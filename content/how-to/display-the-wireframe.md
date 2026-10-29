---
title: Display the wireframe of a mesh
section: How-to
group: Appearance and textures
order: 9
description: Show the triangles of a mesh with draw_wireframe (desktop builds), and with a curve_drawable made of the mesh edges, which also works in the web (WebGL) build.
---

# Display the wireframe of a mesh

**Goal**: draw the edges of the triangles of a shape over its surface, to check its sampling
or show its structure, both in the desktop program and in the web build.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: display-the-wireframe -->

## Two ways, one of them desktop only

| | `draw_wireframe(drawable, environment)` | `curve_drawable` of the edges |
|---|---|---|
| Code | one line | about ten lines, once |
| Desktop (OpenGL 3.3) | yes | yes |
| Web build (Emscripten, WebGL 2) | **draws nothing** | yes |
| Follows changes of the mesh | yes (same buffers) | no: rebuild or update the curve |

`draw_wireframe` draws the drawable again with the OpenGL polygon mode `GL_LINE`, which WebGL
does not have: in a web build the function is compiled empty, without error or warning. The
demo of this page runs in WebGL, so it shows the second method.

## 1. Desktop: `draw_wireframe`

Create a coarse torus so that the triangles are easy to see:

```cpp
// scene.hpp - add in scene_structure
mesh_drawable torus;
```

```cpp
// scene.cpp - add at the end of initialize()
mesh torus_mesh = mesh_primitive_torus(0.6f, 0.2f, {0,0,0}, {0,0,1}, 30, 12);
torus.initialize_data_on_gpu(torus_mesh);
torus.model.translation = {0.0f, 0.0f, 1.0f};
```

Draw the surface, then its wireframe over it:

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(torus, environment);
draw_wireframe(torus, environment);                       // blue lines (default)
```

The signature, with its default values:

```cpp
void draw_wireframe(mesh_drawable const& drawable, environment_generic_structure const& environment = environment_generic_structure(),
                    vec3 const& color = {0,0,1}, int instance_count = 1, bool expected_uniforms = true,
                    uniform_generic_structure const& additional_uniforms = uniform_generic_structure());
```

- `color`: color of the lines, `{0,0,1}` (blue) by default. It replaces `material.color`
  for this call only; the per-vertex colors of the mesh still multiply it.
- The lines are drawn with the shader and the `model` transform of the drawable, without
  texture and without shading (ambient coefficient 1, no diffuse or specular term).
- *instance_count*, *expected_uniforms*, `additional_uniforms`: as for `draw`, for instanced
  drawables and custom shaders (see [Send a custom uniform to a shader](send-a-custom-uniform.md)).
- A small depth offset (`glPolygonOffset`) brings the lines in front of the surface, so
  they are not hidden by the triangles they belong to.

Only the wireframe, without the surface: call `draw_wireframe` without `draw`.

## 2. Any build, including WebGL: a `curve_drawable` of the edges

A `curve_drawable` in *Segments* mode draws one segment per pair of points. Put the three
edges of every triangle in it, once:

```cpp
// scene.hpp - add in scene_structure
curve_drawable torus_edges;
```

```cpp
// scene.cpp - add at the end of initialize()
// Two points per edge; each point is pushed slightly along its normal so that the lines
//  are not hidden by the surface (WebGL has no polygon offset for lines)
numarray<vec3> edges;
for (uint3 const& triangle : torus_mesh.connectivity) {
    for (int k = 0; k < 3; ++k) {
        int const a = triangle[k];
        int const b = triangle[(k + 1) % 3];
        edges.push_back(torus_mesh.position[a] + 0.003f * torus_mesh.normal[a]);
        edges.push_back(torus_mesh.position[b] + 0.003f * torus_mesh.normal[b]);
    }
}
torus_edges.initialize_data_on_gpu(edges);
torus_edges.display_type = curve_drawable_display_type::Segments;
torus_edges.color = {0.0f, 0.0f, 0.0f};   // after initialize_data_on_gpu, which sets it to red
```

*torus_mesh* is the mesh of step 1: this code goes after it, in the same `initialize()`.
Each edge shared by two triangles is pushed twice; this only costs memory.

Draw it with the same transform as the surface:

```cpp
// scene.cpp - add in display_frame(), before timer.update()
torus_edges.model = torus.model;
draw(torus_edges, environment);
```

## 3. Toggle the wireframe from the GUI

```cpp
// scene.hpp - add in gui_parameters
bool display_wireframe = true;
```

```cpp
// scene.cpp - add in display_gui()
ImGui::Checkbox("Wireframe", &gui.display_wireframe);
```

The whole `display_frame()` becomes (keep only one of the two methods in your own code):

```cpp
// scene.cpp - replace display_frame()
void scene_structure::display_frame()
{
    environment.camera_view = camera_control.camera().matrix_view();
    environment.light = camera_control.camera_model.position();

    if (gui.display_frame)
        draw(global_frame, environment);

    draw(sphere, environment);
    cylinder.model.rotation = rotation_transform::from_axis_angle({1,0,0}, timer.t);
    draw(cylinder, environment);

    draw(torus, environment);
    if (gui.display_wireframe) {
        draw_wireframe(torus, environment, {0,0,1});   // desktop only
        torus_edges.model = torus.model;
        draw(torus_edges, environment);                // desktop and web
    }

    timer.update();
}
```

## Common pitfalls

- **Nothing changes in the web build**: `draw_wireframe` is empty there; use the
  `curve_drawable` of section 2.
- **The lines flicker or are half hidden** (curve version): the segments lie exactly on the
  triangles and fight with them in the depth buffer. Push the points along the normals, as
  above (increase the 0.003 for a large shape).
- **The curve does not follow the shape**: copy `model` from the drawable at every frame,
  and rebuild or update the curve (`torus_edges.vbo_position.update(edges)`) when the mesh
  is modified.
- **The wireframe of `draw_wireframe` is black or tinted**: the per-vertex colors of the mesh
  multiply the line color.
- **Warnings about `material.*` uniforms with your own shader**: `draw_wireframe` sends the
  material uniforms of the default shader; pass `expected_uniforms = false` if your shader
  does not use them.

## Variations

- One code for both builds: test the build in C++ with `#ifdef __EMSCRIPTEN__` (defined by
  Emscripten) and draw the curve only there.
- Wireframe of a mesh updated at every frame: `draw_wireframe` reads the same buffers as `draw`,
  so it follows `vbo_position.update(...)` (see [Update a mesh at every frame](update-a-mesh-every-frame.md)).
- A hierarchy or a triangle soup: `draw_wireframe` also exists for `hierarchy_mesh_drawable`
  (every element, with its global transform) and `triangles_drawable`, with the same
  parameters and the same limitation in WebGL.
- Only some edges (the border of a grid, a quad mesh without its diagonals): push only these
  pairs of points into the curve.

## See also

- How-to: [Draw curves, segments and trajectories](draw-curves-and-segments.md), [Create basic shapes](create-basic-shapes.md), [Change the color of a shape](change-the-color.md)
- Install: [Build for the web](../get-started/install.md#build-for-the-web-emscripten)
- Reference: [`mesh_drawable`](../reference/mesh_drawable.md) (`draw_wireframe`), [`curve_drawable`](../reference/curve_drawable.md)
