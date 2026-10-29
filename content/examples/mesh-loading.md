---
title: A building loaded with its materials
section: Examples
group: Shapes and surfaces
order: 4
local_names: [struct_shape, shapes, display_info, tree, ground, grass, number_of_instances, scaling_grass]
description: The Sponza model loaded with mesh_load_file_obj_advanced as one drawable per run of material, with the textures of its .mtl file - what the loader does with the faces, the textures and the normals.
---

# A building loaded with its materials

**What it shows**: the Sponza atrium, an OBJ model of 40 000 faces (66 000 triangles once its
quads are split) that uses 20 materials, 19 of them with a texture image. `mesh_load_file_obj_advanced` reads the model
and its `.mtl` file, and returns it split into parts, one per material; the scene converts
them into a list of `mesh_drawable` and draws them in a loop. The camera starts inside the
building.

<!-- demo: mesh-loading -->

Concepts combined in this example:

- `mesh_load_file_obj_advanced(directory, filename)`, which also loads the texture images
  named in the material file;
- `mesh_obj_advanced_loader::convert_to_mesh_drawable`, which sends every part to the GPU;
- a `std::vector<mesh_drawable>` drawn with one `draw` per part;
- an OBJ file without normals: the normals are computed at loading, one per triangle.

Source: [`examples/09_mesh_loading`](https://github.com/drohmer/epita_ani3d_lab_code-2027/tree/main/examples/09_mesh_loading)
of the public repository *epita_ani3d_lab_code-2027*, run unchanged in the demo above. For
the steps in your own project (where to put the files, how to fix a `.mtl` file, how to
scale and rotate the parts), see
[Load an OBJ model made of several textured parts](../how-to/load-an-obj-with-materials.md);
for a single model without materials,
[Load a 3D model from an OBJ file](../how-to/load-an-obj-file.md).

| File | Role |
|---|---|
| `src/scene.hpp`, `src/scene.cpp` | the scene: loads the model, draws its parts |
| `assets/sponza.zip` | the Sponza model (OBJ, MTL, JPG images): unzip it in `assets/` |
| `assets/f1.zip` | a second model (a Formula 1 car, an OBJ of 25 MB once unzipped), loaded by a commented-out line |

The models are shipped as zip files: unzip them in `assets/` before running the example
natively (the comment in `initialize()` says so). The demo above uses a lighter copy of
Sponza (rounded coordinates, smaller images, see `demos/mesh-loading/origin.txt`) and leaves
out the car. The scene also declares a `timer`, `tree`, `ground` and `grass` drawables and two
GUI fields (`number_of_instances`, `scaling_grass`) that no code uses: leftovers of a larger
scene.

## 1. Load and convert

```cpp
// src/scene.cpp - initialize
// Unzip the files in assets/ before runing the code
//auto struct_shape = mesh_load_file_obj_advanced(project::path + "assets/f1/", "F1GenV3Backup.obj");
auto struct_shape = mesh_load_file_obj_advanced(project::path + "assets/sponza/", "sponza.obj");
shapes = mesh_obj_advanced_loader::convert_to_mesh_drawable(struct_shape);
```

To display the car instead, swap the two comments. The model is used as it is in the file:
no scaling, no rotation. Sponza measures about 35 x 17 x 16 units and its vertical axis is
y, while the camera of the scene (`camera_controller_orbit`, placed by `look_at` with the up
vector `{0,0,1}`) treats z as vertical: the building appears lying on its side, and the
camera, at `{4,4,1.5}`, starts within its walls. Zoom out (right button drag) to see it
whole. The how-to rotates and scales the parts to get an upright building of a few units.

## 2. What the loader builds

`mesh_load_file_obj_advanced` parses the file with the tinyobjloader library, then:

1. **loads each texture once**: for every material of the `.mtl` file with a diffuse image
   ("map_Kd"), the image `directory + name` is loaded on the GPU in `GL_REPEAT` mode;
   a material without image gets the default white texture;
2. **cuts the faces into parts**: it walks through the faces of each shape returned by the
   parser (the "g" groups of the file, for Sponza) and starts a new part every time the material changes. Each part is a
   `mesh_obj_advanced_loader::shape_element_node`: a `mesh` and the texture of its material.
   Several parts with the same material share the same texture, since a texture copy only
   copies its OpenGL id;
3. **does not share vertices**: the faces are triangulated by the parser, and every triangle gets three new vertices, with the position,
   the uv and, if the file has some, the normal of its corners.

`convert_to_mesh_drawable` then calls `fill_empty_field` and `initialize_data_on_gpu` on
each mesh, and assigns its texture. Sponza has no "vn" line: `fill_empty_field` computes the
normals from the triangles, and since no vertex is shared, each triangle gets its own
normal. The building is therefore lit with flat facets, which suits its mostly flat walls.

Only the diffuse image of each material is used: the colors ("Kd"), the bump maps and the
other images of the `.mtl` file are ignored.

## 3. Draw all the parts

```cpp
// src/scene.cpp - display_frame
for (int k = 0; k < shapes.size(); ++k)
	draw(shapes[k], environment);

if (gui.display_wireframe) {
	for (int k = 0; k < shapes.size(); ++k)
		draw_wireframe(shapes[k], environment);
}
```

One draw call per part. The "Wireframe" checkbox draws the triangles in blue over the
model natively; in the browser `draw_wireframe` draws nothing (see
[Display the wireframe](../how-to/display-the-wireframe.md)).

## Going further

- Print `shapes.size()` to see how many parts the material changes produce.
- Rotate and scale all the parts in the same loop (`model.rotation`, `model.scaling`), as in
  the how-to, to stand the building upright.
- Give each part a random `material.color` to see where the parts are cut.
- Load your own model: export it from Blender as OBJ with its materials, keep the images
  next to the `.mtl` file, and check the image names in the "map_Kd" lines.

## See also

- How-to: [Load an OBJ model made of several textured parts](../how-to/load-an-obj-with-materials.md), [Load a 3D model from an OBJ file](../how-to/load-an-obj-file.md), [Move, rotate and scale a shape](../how-to/transform-a-shape.md)
- Understand: [From CPU to GPU](../understand/cpu-to-gpu.md)
- Reference: [`mesh`](../reference/mesh.md), [`mesh_drawable`](../reference/mesh_drawable.md), [`opengl_texture_image_structure`](../reference/opengl_texture_image_structure.md)
