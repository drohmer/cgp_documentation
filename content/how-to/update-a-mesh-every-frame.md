---
title: Update a mesh at every frame
section: How-to
group: Shapes and meshes
order: 5
description: Deform the vertices of a mesh on the CPU, recompute its normals, and re-send only the modified buffers to the GPU.
---

# Update a mesh at every frame

**Goal**: animate a terrain or a wave surface by moving its vertices, without rebuilding
the `mesh_drawable`.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: update-a-mesh-every-frame -->

## Why an explicit update is needed

`initialize_data_on_gpu` copies the arrays of the `mesh` into GPU buffers (VBO). After
that, the `mesh` and the `mesh_drawable` are independent: modifying `mesh.position` has
no visible effect until the new values are sent to the GPU. The `mesh_drawable` keeps one
buffer per field (`vbo_position`, `vbo_normal`, `vbo_color`, `vbo_uv`) that can be
overwritten with `update`, as long as the **number of vertices does not change**.

## 1. Keep the mesh next to the drawable

The time comes from the timer of the template: do not declare a second one.

```cpp
// scene.hpp - add in scene_structure
mesh surface_mesh;              // CPU copy, modified at each frame
mesh_drawable surface;          // GPU buffers
```

## 2. Create both (once)

```cpp
// scene.cpp - add at the end of initialize()
int const N = 100;
surface_mesh = mesh_primitive_grid({-1,-1,0}, {1,-1,0}, {1,1,0}, {-1,1,0}, N, N);
surface.initialize_data_on_gpu(surface_mesh);
surface.model.translation = {0, 0, -0.5f};   // under the sphere and the cylinder of the template
surface.material.color = {0.5f, 0.6f, 0.8f};
```

## 3. Modify, recompute normals, update the buffers (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
float const t = timer.t;

// CPU: move the vertices
for (vec3& p : surface_mesh.position)
    p.z = 0.1f * std::sin(6 * p.x + 3 * t) * std::cos(4 * p.y);

// CPU: the normals depend on the positions
surface_mesh.normal_update();

// GPU: overwrite the existing buffers (same size, no reallocation)
surface.vbo_position.update(surface_mesh.position);
surface.vbo_normal.update(surface_mesh.normal);

draw(surface, environment);
```

The template already calls `timer.update()` once, at the end of `display_frame()`.
Update only the buffers whose content changed: here the colors and uv are untouched, so
`vbo_color` and `vbo_uv` are left as they are.

## Common pitfalls

- **Nothing moves**: the `mesh` was modified but `vbo_position.update` was not called
  (or was called on another drawable).
- **The shape moves but the lighting stays frozen**: the normals were not recomputed
  (`normal_update()`) or `vbo_normal` was not updated.
- **Error "Cannot update VBO with more data than was allocated"**: `update` cannot
  enlarge a buffer. If the number of vertices or triangles changes, call `surface.clear()` then
  `initialize_data_on_gpu` again (costly: avoid doing it at every frame).
- **Low frame rate**: do not call `initialize_data_on_gpu` or `mesh_primitive_grid`
  inside `display_frame()`; reuse the same arrays and only rewrite their values.

## Variations

- Rigid motion only (move, rotate, scale the whole shape): no buffer update is needed,
  change `surface.model` instead (see [Move, rotate and scale a shape](transform-a-shape.md)).
- Recompute only when a parameter changes (GUI slider) instead of at every frame:
  see [Add GUI controls](add-gui-controls.md).
- Per-vertex colors that change: modify `surface_mesh.color`, then
  `surface.vbo_color.update(surface_mesh.color)`.
- Purely visual waves can be computed on the GPU in a custom vertex shader, with no CPU
  update at all (see [Send a custom uniform to a shader](send-a-custom-uniform.md)).

Source: course lab of CSC_43043 ([public version](https://github.com/drohmer/csc43043ep-lab-code), without the solutions): [`07_texture/c_perlin_noise`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/07_texture/c_perlin_noise) (terrain.cpp, function update_terrain).

## See also

- How-to: [Build a mesh by hand](build-a-mesh-by-hand.md), [Animate a shape with time](animate-with-time.md)
- Understand: [From CPU to GPU](../understand/cpu-to-gpu.md)
- Reference: [`mesh`](../reference/mesh.md), [`mesh_drawable`](../reference/mesh_drawable.md)
