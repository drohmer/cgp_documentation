---
title: Draw curves, segments and trajectories
section: How-to
group: Shapes and meshes
order: 6
description: Display a polyline, a set of independent segments or the trail of a moving object with curve_drawable.
---

# Draw curves, segments and trajectories

**Goal**: display a wavy parametric curve, the edges of a box, and the trail left by a
moving sphere.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: draw-curves-and-segments -->

## curve_drawable in short

A `curve_drawable` stores a list of 3D positions on the GPU and draws them as lines with a
single color, without lighting. It has its own `model` transform and `color`, like a
`mesh_drawable`. Its `display_type` chooses how the points are linked:

| `display_type` | Draws | OpenGL mode |
|---|---|---|
| `curve_drawable_display_type::Curve` (default) | one polyline through all the points | `GL_LINE_STRIP` |
| `curve_drawable_display_type::Segments` | one segment per pair of points (0-1, 2-3, ...) | `GL_LINES` |

## 1. Declare the drawables

```cpp
// scene.hpp - add in scene_structure
curve_drawable curve;
curve_drawable box;
```

## 2. Fill the positions and upload them (once)

```cpp
// scene.cpp - add at the end of initialize()
numarray<vec3> positions;
int const N = 150;
for (int k = 0; k < N; ++k) {
    float const u = k / (N - 1.0f);                  // u in [0,1]
    positions.push_back({ 0.0f, 4.0f * (u - 0.5f), 0.1f * std::cos(16 * Pi * u) });
}
curve.initialize_data_on_gpu(positions);
curve.color = { 0, 0.6f, 0 };
curve.model.translation = { 1.5f, 0, 0 };

// The 12 edges of a cube, given as pairs of extremities
numarray<vec3> edges = {
    {-1,-1,-1},{1,-1,-1},  {1,-1,-1},{1,1,-1},  {1,1,-1},{-1,1,-1},  {-1,1,-1},{-1,-1,-1},
    {-1,-1,1},{1,-1,1},    {1,-1,1},{1,1,1},    {1,1,1},{-1,1,1},    {-1,1,1},{-1,-1,1},
    {-1,-1,-1},{-1,-1,1},  {1,-1,-1},{1,-1,1},  {1,1,-1},{1,1,1},    {-1,1,-1},{-1,1,1} };
box.display_type = curve_drawable_display_type::Segments;   // set before the upload
box.initialize_data_on_gpu(edges);
```

## 3. Draw (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(curve, environment);
draw(box, environment);
```

## Common pitfalls

- **The box is drawn as a zigzag**: `display_type` was left to its default (Curve), which
  links every point to the next one. Use Segments for independent edges, vectors or grids.
- **The lines stay thin whatever I try**: the line width cannot be changed in the OpenGL
  core profile used by CGP (`glLineWidth` above 1 is ignored on most systems, macOS
  included). For thick lines, draw thin cylinders (`mesh_primitive_cylinder`) instead.
- **The curve is red**: `color` was not set, or it was set before
  `initialize_data_on_gpu`, which resets it to red (and `model` to the identity). Set
  both after the upload.
- **Changing the positions array has no effect**: the GPU keeps its own copy. Send the new values
  with `curve.vbo_position.update(positions);` (see below).

## Variations

- Animate the curve: keep the `numarray<vec3>` in the scene, modify it in
  `display_frame()`, then call `curve.vbo_position.update(positions);`. The number of points
  must not exceed the one given to `initialize_data_on_gpu`; to draw only the first 50
  points, call `draw(curve, environment, 50);`.
- Circle: `circle.initialize_data_on_gpu(curve_primitive_circle(0.5f, {0,0,0}, {0,0,1}, 40));`
  (radius, center, normal, number of samples). Scale it with `circle.model.scaling`.
- Trail of a moving object: declare `trajectory_drawable trail{100};` (keeps the 100 last
  positions), call `trail.add(sphere.model.translation);` at every frame, then
  `draw(trail, environment);`. Its color is `trail.visual.color`, to set after the first
  `add` (which uploads the buffer and resets the color to red), for instance right after
  each `add`.
- Curve whose number of points grows (strokes, recorded paths): see
  [Sketch curves with the mouse](sketch-with-the-mouse.md).

Source: EPITA Ani3D repository `epita_ani3d_lab_code-2027`, scenes
`scenes_ani3d/00_introduction` (parametric curve) and `scenes_ani3d/02_sphere_collision`
(edges of the cube), `scenes_ani3d/05_stable_fluids` (velocity vectors updated with
`vbo_position.update`) and `scenes_ani3d/06_sph` (`curve_primitive_circle`).

## See also

- How-to: [Animate a shape with time](animate-with-time.md), [Update a mesh at every frame](update-a-mesh-every-frame.md), [Display the wireframe of a mesh](display-the-wireframe.md) (segments built from the edges of a mesh)
- Understand: [From CPU to GPU](../understand/cpu-to-gpu.md)
- Reference: [`curve_drawable`](../reference/curve_drawable.md), [`numarray`](../reference/numarray.md), [`vec3`](../reference/vec3.md)
