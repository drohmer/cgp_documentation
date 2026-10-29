---
title: Load a 3D model from an OBJ file
section: How-to
group: Loading files
order: 14
description: Read a Wavefront .obj file into a mesh, send it to the GPU, then scale and place it in the scene.
---

# Load a 3D model from an OBJ file

**Goal**: display a model made in a modeling software (here a camel), at the right size
and position.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: load-an-obj-file -->

## 1. Put the file in the project

The template has no model and no `assets/` folder: create the folder `assets/` at the root
of the project, next to `shaders/`, and copy an OBJ file into it, for instance
`assets/camel.obj` (download [camel.obj](../assets/download/camel.obj), 240 KB, the camel of
the course lab given in the source below, or any `.obj` file). Paths are built from `project::path`, the root folder of the project
(the one that contains `shaders/`), found automatically at startup: the program then
works whatever the folder it is launched from.

## 2. Declare the drawable

```cpp
// scene.hpp - add in scene_structure
mesh_drawable camel;
```

## 3. Load, upload and place it (once)

```cpp
// scene.cpp - add at the end of initialize()
mesh camel_mesh = mesh_load_file_obj(project::path + "assets/camel.obj");
camel.initialize_data_on_gpu(camel_mesh);

camel.model.scaling = 0.5f;                // the file units are arbitrary: adjust the size
camel.model.translation = {-1, 1, 0.5f};
```

`mesh_load_file_obj` reads the vertex positions, normals and uv coordinates of the file
and returns an ordinary `mesh`: everything that works on a primitive shape works on it
(color, texture, transforms, wireframe).

## 4. Draw (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(camel, environment);
```

## Common pitfalls

- **The program stops with an error on the file name**: the path is wrong. Print `project::path` and check that
  the file is in `assets/` under it. Do not use an absolute path from your own computer.
- **Nothing is visible**: the model may be huge or tiny, or far from the origin. Inspect
  it with `get_bounding_box_position`, or normalize it on the CPU:
  `camel_mesh.centered().normalize_size_to_position();` before `initialize_data_on_gpu`.
- **The model lies on its side**: many files use y as the up axis while the CGP scenes
  use z. Rotate it: `camel.model.rotation = rotation_transform::from_axis_angle({1,0,0}, Pi/2);`.
- **Slow startup**: large OBJ files are parsed as text. Load them once in `initialize()`,
  never in `display_frame()`.

## Variations

- Textured model: load the image that comes with the file,
  `camel.texture.load_and_initialize_texture_2d_on_gpu(project::path + "assets/camel.png");`
  (see [Apply a texture image](apply-a-texture.md)).
- Shortcut in one line:
  `camel.initialize_data_on_gpu(mesh_load_file_obj(project::path + "assets/camel.obj"));`.
- Wireframe overlay to inspect the triangles: `draw_wireframe(camel, environment);`.

Source: course labs of CSC_43043 ([public version](https://github.com/drohmer/csc43043ep-lab-code), without the solutions): [`05_shaders/a_shader_manipulation`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/05_shaders/a_shader_manipulation) (assets/camel.obj) and
[`07_texture/d_animation`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/07_texture/d_animation) (scene.cpp, cauldron and spoon).

## See also

- How-to: [Move, rotate and scale a shape](transform-a-shape.md), [Draw a mesh with a camera](draw-a-mesh.md)
- Understand: [Scene structure](../understand/scene-structure.md)
- Reference: [`mesh`](../reference/mesh.md), [`mesh_drawable`](../reference/mesh_drawable.md)
