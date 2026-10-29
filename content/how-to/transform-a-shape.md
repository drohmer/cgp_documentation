---
title: Move, rotate and scale a shape
section: How-to
group: Shapes and meshes
order: 3
description: Place a drawable in the world with model.translation, model.rotation and model.scaling, without touching its vertices.
---

# Move, rotate and scale a shape

**Goal**: place the same cube at a given position, tilted and resized, by changing only
its `model` transform.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: transform-a-shape -->

## The `model` transform of a drawable

Every `mesh_drawable` has a `model` member of type `affine`. It is sent to the shader as
the `model` matrix at each `draw` call and applied to every vertex on the GPU:

```text
p_world = translation + rotation * (scaling * scaling_xyz * p_local)
```

| Member | Type | Default |
|---|---|---|
| `model.translation` | `vec3` | `{0,0,0}` |
| `model.rotation` | `rotation_transform` | identity |
| `model.scaling` | float (uniform scaling) | `1` |
| `model.scaling_xyz` | `vec3` (scaling per axis) | `{1,1,1}` |

![T * p scales, rotates and then translates: affine_rt gives R p + t, affine_rts gives R s p + t, and affine (the type of model) gives R s S p + t, where S = diag(scaling_xyz) stretches the local axes of the shape before the rotation.](../assets/reference/affine.svg)

The `mesh` on the CPU is never modified: changing `model` is free and can be done at
every frame.

## 1. Declare the drawable

```cpp
// scene.hpp - add in scene_structure
mesh_drawable cube;
```

## 2. Create it and set its transform (once)

```cpp
// scene.cpp - add at the end of initialize()
cube.initialize_data_on_gpu(mesh_primitive_cube({0,0,0}, 1.0f));

cube.model.translation = {1.0f, 0.5f, 0.0f};                              // position
cube.model.rotation = rotation_transform::from_axis_angle({0,0,1}, Pi/4); // 45 deg around z
cube.model.scaling = 0.5f;                                                // half size
```

`rotation_transform::from_axis_angle(axis, angle)` builds a rotation from an axis
(normalized internally) and an angle in **radians**. The constant Pi is defined by CGP.

## 3. Draw (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(cube, environment);
```

## Common pitfalls

- **The rotation is not around the center of the shape**: the rotation is applied around
  the origin of the *local* frame of the mesh, before the translation. Build the mesh
  centered at `{0,0,0}` (most `mesh_primitive_*` functions take a center argument) and
  move it with `model.translation`.
- **Angle in degrees**: `from_axis_angle` expects radians; write `30 * Pi / 180`.
- **`scaling_xyz` stretches the shape along its own axes**: it is applied *before* the
  rotation, so a cube scaled with `{2,1,1}` stays a box when it turns.

## Variations

- Combine rotations: `rotation_transform` values can be multiplied,
  `R = R2 * R1` applies R1 first.
- Rotate one vector into another: `rotation_transform::from_vector_transform({0,0,1}, normalize(direction))`
  (both vectors must have a unit norm: the function stops on an assertion otherwise).
- Draw the same drawable at several places: change `model.translation` between two
  `draw` calls (no need for several drawables).
- Bake a transform into the vertices instead (CPU, done once): `mesh::translate`,
  `mesh::scale`, `mesh::rotate`, then `initialize_data_on_gpu`.

Source: course labs of CSC_43043 ([public version](https://github.com/drohmer/csc43043ep-lab-code), without the solutions): [`00_test_installation`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/00_test_installation) and [`08_project`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/08_project) (scene.cpp).

## See also

- How-to: [Draw a mesh with a camera](draw-a-mesh.md), [Animate a shape with time](animate-with-time.md), [Create basic shapes](create-basic-shapes.md)
- Understand: [Camera and matrices](../understand/camera-and-matrices.md)
- Reference: [`rotation_transform`](../reference/rotation_transform.md), [`affine`](../reference/affine.md), [`mesh_drawable`](../reference/mesh_drawable.md)
