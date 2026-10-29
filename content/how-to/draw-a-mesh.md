---
title: Draw a mesh with a camera
section: How-to
group: Shapes and meshes
order: 1
description: The minimal code to create a shape, send it to the GPU and draw it with the scene camera.
---

# Draw a mesh with a camera

**Goal**: display a new sphere in the scene and look at it with the orbit camera.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: draw-a-mesh -->

## The two-step pattern: `mesh` then `mesh_drawable`

CGP separates the data on the CPU from the data on the GPU:

| Type | Lives in | Role |
|---|---|---|
| `mesh` | CPU memory | Geometry you can create and modify: `position`, `normal`, `color`, `uv`, `connectivity` |
| `mesh_drawable` | GPU memory | Buffers (VBO), shader, texture, `model` transform, material: what `draw()` needs |

You build or edit a `mesh`, then upload it **once** into a `mesh_drawable`, and draw the
drawable **at every frame**.

## 1. Declare the drawable in the scene

The template already has a red sphere: give the new shape another name.

```cpp
// scene.hpp - add in scene_structure
mesh_drawable ball;
```

## 2. Create the mesh and upload it (once)

```cpp
// scene.cpp - add at the end of initialize()
mesh ball_mesh = mesh_primitive_sphere(0.25f);   // CPU: positions, normals, uv, triangles
ball.initialize_data_on_gpu(ball_mesh);          // GPU: VBOs + default shader + white texture

ball.model.translation = {1.0f, 1.0f, 0.0f};     // where the shape is in the world
ball.material.color = {0.2f, 0.4f, 1.0f};        // blue
```

`initialize_data_on_gpu` copies every per-vertex array into a GPU buffer
(`glBufferData`) and keeps their handles in the drawable. Call it only once: it allocates GPU
memory.

## 3. Set the camera (once)

The template already does it, at the beginning of `initialize()`:

```cpp
// scene.cpp - already in the template, in initialize()
camera_control.initialize(inputs, window);
camera_control.set_rotation_axis_z();
camera_control.look_at({3.0f, -2.0f, 1.5f} /*eye*/, {0,0,0} /*target*/, {0,0,1});
```

The camera turns around the z axis set by `set_rotation_axis_z()`. The third argument of
`look_at` is ignored by the template controller (`camera_controller_orbit_euler`): only the
other controllers use it as the up direction.

## 4. Draw (every frame)

Add one line to `display_frame()`. The whole function becomes:

```cpp
// scene.cpp - replace display_frame()
void scene_structure::display_frame()
{
    environment.camera_view = camera_control.camera().matrix_view();   // camera -> view matrix
    environment.light = camera_control.camera_model.position();        // light at the camera

    if (gui.display_frame)
        draw(global_frame, environment);

    draw(sphere, environment);
    cylinder.model.rotation = rotation_transform::from_axis_angle({1,0,0}, timer.t);
    draw(cylinder, environment);

    draw(ball, environment);   // new line

    timer.update();
}
```

Keep the two `environment` lines: without the light line, the light stays at its default
position `{1,1,1}` instead of following the camera.

`draw` binds the buffers and the shader, sends the uniforms (`model` from the drawable;
`view`, `projection` and `light` from the environment), then calls `glDrawElements`.

```text
mesh  --initialize_data_on_gpu()-->  mesh_drawable  --draw(drawable, environment)-->  pixels
(CPU)        once, glBufferData          (GPU)          every frame, uniforms + glDraw
```

## Common pitfalls

- **Nothing is displayed**: check that `initialize_data_on_gpu` was called before `draw`,
  and that the shape is in front of the camera (`look_at` target). More causes in
  [Troubleshooting](../get-started/troubleshooting.md#nothing-is-displayed).
- **Modifying the `mesh` has no effect**: the GPU keeps its own copy. Either rebuild the
  drawable, or update the buffers with `vbo_position.update(mesh.position)`.
- **Low frame rate**: do not call `mesh_primitive_*` or `initialize_data_on_gpu` inside
  `display_frame()`.

## Variations

- Other shapes: `mesh_primitive_cube`, `mesh_primitive_cylinder`, `mesh_primitive_cone`,
  `mesh_primitive_torus`, `mesh_primitive_grid`... (pictures and parameters of all of them in
  [Create basic shapes](create-basic-shapes.md)).
- Color: `material.color`, per-vertex colors, color picker: see
  [Change the color of a shape](change-the-color.md).
- Wireframe: `draw_wireframe(ball, environment)` (native builds only: it draws nothing in
  WebGL, which has no polygon mode; see [Display the wireframe of a mesh](display-the-wireframe.md)
  for a version that also works there).
- Texture: pass an `opengl_texture_image_structure` to `initialize_data_on_gpu`, or set
  `ball.texture`.

## See also

- How-to: [Create basic shapes](create-basic-shapes.md), [Change the color of a shape](change-the-color.md), [Move, rotate and scale a shape](transform-a-shape.md)
- Get started: [Troubleshooting and error messages](../get-started/troubleshooting.md) (nothing displayed, black shape)
- Understand: [Camera and matrices](../understand/camera-and-matrices.md)
- Reference: [`mesh`](../reference/mesh.md), [`mesh_drawable`](../reference/mesh_drawable.md), [`vec3`](../reference/vec3.md)
