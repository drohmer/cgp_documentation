---
title: Choose the right type
section: Understand
order: 9
description: Which CGP type to use for a need - transform an object (rotation_transform, frame, affine_rt, affine_rts, affine, mat4), store data (vec3, numarray, grid_2D, grid_3D, image_structure), display a shape (mesh_drawable, triangles_drawable, curve_drawable, hierarchy_mesh_drawable...), move the camera (camera models, controllers, projections) - with the usual case, the limits and an example.
---

# Choose the right type

CGP often offers several close types for the same idea: five ways to store a transform,
four containers, seven drawables, five camera controllers. Each page of the reference
describes one type; this page compares them, need by need. For each need, the first line of
the table is the usual choice of the course.

## Transform an object

| Need | Type | Limits |
|---|---|---|
| Place a shape in the scene | [`affine`](../reference/affine.md), the type of `mesh_drawable::model` | Not invertible (per-axis scaling) |
| Place an element of a hierarchy | [`affine_rts`](../reference/affine_rts.md), the type of `hierarchy_mesh_drawable_node::transform_local` | Uniform scaling only |
| Move a rigid object (no scaling) | [`affine_rt`](../reference/affine_rt.md) | No scaling |
| Rotate only | [`rotation_transform`](../reference/rotation_transform.md) | No translation |
| Describe a place: a camera, a joint, a local basis | [`frame`](../reference/frame.md) | Same data as `affine_rt`, read as axes |
| Send a transform to a shader, or a projection | [`mat4`](../reference/mat4.md) | Hard to read and to animate |

Rules of thumb:

- **Fill the fields, not a matrix.** `model.translation`, `model.rotation`,
  `model.scaling` and `model.scaling_xyz` are what you change in `display_frame()`; the
  `mat4` is built by `draw` when it sends the uniform. A `mat4` written by hand is rarely
  needed outside a shader.
- **Need the inverse?** `affine` has none, because of `scaling_xyz`. Keep the transforms
  you invert (a camera, a joint) in `affine_rts`, `affine_rt`, `frame` or
  `rotation_transform`, which all have `inverse`.
- **Animate a rotation** with `rotation_transform::lerp` rather than by interpolating
  angles: it follows the shortest path between the two orientations.

```cpp
// a shape turning on itself while it moves (affine: the model of a mesh_drawable)
shape.model.translation = {std::cos(t), std::sin(t), 0};
shape.model.rotation = rotation_transform::from_axis_angle({0,0,1}, t);
shape.model.scaling_xyz = {1, 1, 2};   // twice as tall along its own z axis
```

What each type stores, what `T * p` computes and the order of products:
[Rotations, frames and affine transforms](transformations.md).

## Store data

| Need | Type | Limits |
|---|---|---|
| A point, a direction, a color | [`vec3`](../reference/vec3.md) (also `vec2`, `vec4`) | Size fixed at compile time |
| A list of values whose size changes: positions, velocities, particles | [`numarray`](../reference/numarray.md) | 1D only |
| Values indexed by (i, j): a height field, the vertices of a grid surface | [`grid_2D`](../reference/grid_2D.md) | Fixed shape once resized |
| Values indexed by (i, j, k): a scalar field for marching cubes | [`grid_3D`](../reference/grid_3D.md) | Memory grows as N^3 |
| An image read from or written to a file | [`image_structure`](../reference/image_structure.md) | Bytes (unsigned char), not floats |

Rules of thumb:

- `vec3` is a `numarray_stack<float,3>`: no allocation, and the functions of
  [vecN](../reference/vecN.md) (`norm`, `dot`, `normalize`...) work on any size. Use it for
  one value, and `numarray<vec3>` for many: `mesh::position` is a `numarray<vec3>`.
- A `grid_2D` is a `numarray` plus a `dimension`: element (i, j) is at offset
  `i + dimension.x * j` of `data` (`index_to_offset`). Prefer it to a `numarray` with
  hand-written offsets, which is where indexing errors come from.
- To compute on an image, convert it: `image_structure` holds 8-bit channels, so a
  `grid_2D<vec3>` of floats is easier to process. Both can become a texture
  (`initialize_texture_2d_on_gpu` accepts either).

```cpp
// heights on a 100 x 100 grid, then the matching vertex positions
grid_2D<float> height;
height.resize(100, 100);
numarray<vec3> position;
for (int j = 0; j < 100; ++j)
    for (int i = 0; i < 100; ++i)
        position.push_back({i / 99.0f, j / 99.0f, height(i, j)});
```

## Display a shape

| Need | Type | Limits |
|---|---|---|
| A surface: a primitive, an OBJ file, a mesh built by hand | [`mesh_drawable`](../reference/mesh_drawable.md), from a [`mesh`](../reference/mesh.md) | Number of vertices and triangles fixed after `initialize_data_on_gpu` |
| Triangles listed three points at a time, with one normal per face | [`triangles_drawable`](../reference/triangles_drawable.md) | No shared vertices |
| A polyline or a set of segments | [`curve_drawable`](../reference/curve_drawable.md) | Fixed number of points |
| A curve that grows while the program runs (sketching) | [`curve_drawable_dynamic_extend`](../reference/curve_drawable_dynamic_extend.md) | Points are only added |
| The trail of a moving point | [`trajectory_drawable`](../reference/trajectory_drawable.md) | Keeps the last N positions |
| An articulated object: a character, a robot arm | [`hierarchy_mesh_drawable`](../reference/hierarchy_mesh_drawable.md) | Built from several `mesh_drawable` |
| A background around the camera | [`skybox_drawable`](../reference/skybox_drawable.md) | Cube map only |
| Many copies of one shape | `mesh_drawable` with per-instance buffers | Needs a custom shader |

Rules of thumb:

- **CPU, then GPU.** Build or modify a `mesh` (on the CPU), then copy it once with
  `initialize_data_on_gpu`. At each frame, change only `model` and `material`; to move the
  vertices themselves, update the buffers (`vbo_position.update`). See
  [From CPU to GPU](cpu-to-gpu.md).
- **`mesh_drawable` or `triangles_drawable`?** In a `mesh`, triangles can share a vertex,
  and `normal_update` averages the normals of the triangles around it: the surface looks
  smooth. `triangles_drawable` takes every triangle on its own and, without normals,
  computes one normal per face: the facets stay visible.
- **One object, many copies.** For a few copies, draw the same `mesh_drawable` several times
  with a different `model`. For thousands, use instancing:
  [Draw many instances](../how-to/draw-many-instances.md).

```cpp
// one drawable, drawn three times at three places
for (int k = 0; k < 3; ++k) {
    sphere.model.translation = {2.0f * k, 0, 0};
    draw(sphere, environment);
}
```

## Move the camera

The camera of the scene template is split into three parts: a **model** (where the camera
is), a **controller** (how the mouse and the keyboard move the model), and a **projection**
(how the 3D scene becomes an image).

| Need | Controller (model) | Limits |
|---|---|---|
| Look at an object from all sides, keep the horizon level | [`camera_controller_orbit_euler`](../reference/camera_controller_orbit_euler.md) ([`camera_orbit_euler`](../reference/camera_orbit_euler.md)), default of the template | Keeps an up axis |
| Turn freely around an object | [`camera_controller_orbit`](../reference/camera_controller_orbit.md) ([`camera_orbit`](../reference/camera_orbit.md)) | The horizon tilts |
| Walk in a scene | [`camera_controller_first_person_euler`](../reference/camera_controller_first_person_euler.md) ([`camera_first_person_euler`](../reference/camera_first_person_euler.md)) | Keeps an up axis |
| Look in any direction from a point | [`camera_controller_first_person`](../reference/camera_controller_first_person.md) ([`camera_first_person`](../reference/camera_first_person.md)) | The horizon tilts |
| Fly like a plane | [`camera_controller_fly_mode`](../reference/camera_controller_fly_mode.md) (`camera_first_person`) | Always moves forward |

| Need | Projection |
|---|---|
| Perspective view (the default) | [`camera_projection_perspective`](../reference/camera_projection_perspective.md) |
| Parallel view, no perspective: a 2D scene, a technical drawing | [`camera_projection_orthographic`](../reference/camera_projection_orthographic.md) |
| A projection matrix for a shader only (the light of a shadow map) | the functions `projection_perspective` and `projection_orthographic`, which return a `mat4` |

Rules of thumb:

- Changing the controller is a change of type of `camera_control` in `src/scene.hpp`, plus its
  initialization (`look_at`, rotation axis): see
  [Switching controller](interaction.md#switching-controller).
- The view matrix always comes from `camera_control.camera().matrix_view()`, and the
  projection matrix from `camera_projection.matrix()`: the shaders do not depend on the
  controller. See [Camera and matrices](camera-and-matrices.md).

## See also

- [Glossary](glossary.md): short definitions of the terms used on this page.
- [Create basic shapes](../how-to/create-basic-shapes.md): the primitives that return a
  `mesh`.
- [Hierarchies of shapes](hierarchies.md): local and global transforms of an articulated
  object.
