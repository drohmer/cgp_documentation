---
title: Load an OBJ model made of several textured parts
section: How-to
group: Loading files
order: 15
description: Load an OBJ file with its .mtl materials and textures as a list of drawables, one per material.
---

# Load an OBJ model made of several textured parts

**Goal**: display a large model (here the Sponza building) whose parts use different
texture images, described in a `.mtl` material file next to the `.obj`.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: load-an-obj-with-materials -->

## When to use it

`mesh_load_file_obj` (see [Load a 3D model from an OBJ file](load-an-obj-file.md)) returns
one `mesh`, and you assign one texture by hand. `mesh_load_file_obj_advanced` reads the
material file as well: it splits the model into one part per material, loads the texture
image of each material, and returns a list of `mesh_obj_advanced_loader::shape_element_node`
(a `mesh_element` and its `texture_element`).

## 1. Put the files in the project

Create the folder `assets/` at the root of the project, next to `shaders/`, and copy the
whole folder of the model into it, keeping its layout. Download
[sponza.zip](../assets/download/sponza.zip) (1 MB, the version of the web demo: lighter
textures, image names fixed for case-sensitive file systems; Sponza by Marko Dabrovic, see
copyright.txt) and unzip it in `assets/`:

```text
assets/sponza/sponza.obj
assets/sponza/sponza.mtl
assets/sponza/*.JPG            (texture images, at the paths written in sponza.mtl)
```

## 2. Declare a list of drawables

```cpp
// scene.hpp - add in scene_structure
std::vector<mesh_drawable> sponza;
```

## 3. Load and convert (once)

```cpp
// scene.cpp - add at the end of initialize()
std::vector<mesh_obj_advanced_loader::shape_element_node> parts =
    mesh_load_file_obj_advanced(project::path + "assets/sponza/", "sponza.obj");
sponza = mesh_obj_advanced_loader::convert_to_mesh_drawable(parts);

for (mesh_drawable& part : sponza) {          // this file is y-up and 35 units wide
    part.model.rotation = rotation_transform::from_axis_angle({1,0,0}, Pi / 2);
    part.model.scaling = 0.1f;
}
```

The model is a building: the camera of the template sees it from outside. To start inside,
place the camera in the gallery:

```cpp
// scene.cpp - replace the camera_control.look_at call in initialize()
camera_control.look_at({1.5f, -0.35f, 0.25f} /*eye*/, {-0.6f, 0.1f, 0.55f} /*target*/, {0,0,1} /*up*/);
```

The first argument is the folder (ending with `/`), the second the file name: the texture
paths of the `.mtl` file are read relative to this folder. `convert_to_mesh_drawable`
calls `initialize_data_on_gpu` on each part and assigns its texture.

## 4. Draw all the parts (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
for (mesh_drawable const& part : sponza)
    draw(part, environment);
```

## Common pitfalls

- **The program stops on "cannot parse"**: the path is wrong. Check that the folder ends
  with `/` and that the file name does not repeat the folder.
- **Textures are missing or the program stops on an image file**: the `.mtl` file refers
  to images with paths relative to its folder (or with absolute paths from the computer of
  the author). Open the `.mtl` file in a text editor and fix the map_Kd lines. The case
  matters on Linux (and in a WebGL build): the Sponza file asks for "SP_LUK.JPG" or
  "00_SKAP.JPG" while the images are named "sp_luk.JPG" and "00_skap.JPG", which only works
  on the case-insensitive file systems of macOS and Windows.
- **The parts are white**: only the diffuse texture (map_Kd) is used; the plain colors
  of the materials (Kd) are ignored. Set `part.material.color` yourself if needed.
- **A transform applies to one part only**: each part is an independent drawable. Apply the
  same `model` to all of them in a loop.
- **Slow start**: a large model with many textures takes seconds to parse and upload.
  Load it once, in `initialize()`.

## Variations

- Edit the geometry before the upload: the meshes are in `parts[k].mesh_element`, for
  instance `parts[k].mesh_element.scale(0.1f);`, before calling
  `convert_to_mesh_drawable`.
- Inspect the model: print `parts.size()` (number of parts), draw the triangles with
  `draw_wireframe(part, environment);`.
- A single OBJ without materials: prefer `mesh_load_file_obj`, simpler and with a single
  drawable.

Source: EPITA Ani3D repository `epita_ani3d_lab_code-2027`, example `09_mesh_loading`
(scene.cpp; the models are provided as zip files in its assets folder).

## See also

- How-to: [Load a 3D model from an OBJ file](load-an-obj-file.md), [Apply a texture image](apply-a-texture.md), [Move, rotate and scale a shape](transform-a-shape.md)
- Understand: [From CPU to GPU](../understand/cpu-to-gpu.md)
- Reference: [`mesh`](../reference/mesh.md), [`mesh_drawable`](../reference/mesh_drawable.md), [`opengl_texture_image_structure`](../reference/opengl_texture_image_structure.md)
