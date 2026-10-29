---
title: Grass with per-instance positions
section: Examples
group: Instancing
order: 17
local_names: [tree, ground, grass, N_instances, instance_positions, quad, quad2, L]
description: 6000 tufts of grass drawn in a single draw call around a palm tree loaded from an OBJ file - two crossed textured quads, random positions computed once on the CPU and sent as a per-instance vertex buffer.
---

# Grass with per-instance positions

**What it shows**: a meadow of **6000 tufts of grass** around a palm tree, drawn with
**one draw call**. Each tuft is the same small mesh, two crossed quads textured with an image
of grass blades; its position is the only thing that changes from one copy to the next. The
positions are drawn at random once, at initialization, and stored on the GPU in an extra vertex
buffer that advances **once per instance** instead of once per vertex.

<!-- demo: instancing-positions -->

Concepts combined in this example:

- a mesh loaded from an OBJ file (`mesh_load_file_obj`), turned from y-up to z-up with its
  `model` rotation, and textured with a repeat wrapping;
- impostors: two crossed quads and a texture with transparent pixels, discarded in the
  fragment shader;
- instancing: a per-instance buffer (`initialize_supplementary_data_on_gpu`, location 4,
  divisor 1), a custom vertex shader that reads it, and `draw` with a number of instances.

Source: [`examples/08_instancing/01_instancing_position`](https://github.com/drohmer/epita_ani3d_lab_code-2027/tree/main/examples/08_instancing/01_instancing_position)
of the public repository *epita_ani3d_lab_code-2027*, run unchanged in the demo above. The
step-by-step recipe, with the pitfalls of instancing, is the how-to
[Draw thousands of copies with instancing](../how-to/draw-many-instances.md), derived from this
example; this page shows how the pieces fit in the complete scene.

| File | Role |
|---|---|
| `src/scene.hpp`, `src/scene.cpp` | the scene: tree, ground, grass and its per-instance buffer |
| `shaders/instancing/instancing.vert.glsl` | default vertex shader + the per-instance position |
| `shaders/instancing/instancing.frag.glsl` | default fragment shader + discard of the transparent pixels |
| `assets/palm_tree/` | the palm tree (OBJ, texture, license CC BY 3.0) |
| `assets/grass.png` | the image of grass blades, with transparency |

## 1. The scene around the grass

The camera is the orbit camera of the template, placed at $(0, -6, 1.5)$ and looking at the
origin, where the tree stands. The background color of the window is set to a light sky blue
(`environment.background_color`).

```cpp
// src/scene.cpp - initialize
tree.initialize_data_on_gpu(mesh_load_file_obj(project::path + "assets/palm_tree/palm_tree.obj"));
tree.model.rotation = rotation_transform::from_axis_angle({ 1,0,0 }, Pi / 2.0f);
tree.texture.load_and_initialize_texture_2d_on_gpu(project::path + "assets/palm_tree/palm_tree.jpg", GL_REPEAT, GL_REPEAT);

float const L = 20.0f; // size of the ground
ground.initialize_data_on_gpu(mesh_primitive_quadrangle({-L,-L,0.0f}, { L,-L,0.0f }, { L,L,0.0f }, { -L,L,0.0f }));
ground.material.color = { 0.4f, 0.6f, 0.3f };
```

The OBJ file is modeled with $y$ up; the rotation of $\pi/2$ around $x$ stands it up in the
z-up scene. The two `GL_REPEAT` arguments set the wrapping of the texture, for uv coordinates
outside $[0,1]$. The ground is a flat green square of $40 \times 40$ units, the same `L` that
bounds the positions of the grass.

## 2. One tuft, one buffer of 6000 positions

```cpp
// src/scene.cpp - initialize
mesh quad = mesh_primitive_quadrangle({ -0.5f,0.0f,0.0f }, { 0.5f,0.0f,0.0f }, { 0.5f,0.0f,1.0f }, { -0.5f,0.0f,1.0f });
mesh quad2 = quad; quad2.rotate({ 0,0,1 }, Pi / 2.0f); // second quad is orthogonal to the first one
quad.push_back(quad2);
grass.initialize_data_on_gpu(quad);
grass.material.phong = { 1,0,0,1 };
grass.texture.load_and_initialize_texture_2d_on_gpu(project::path + "assets/grass.png");
grass.shader.load(project::path + "shaders/instancing/instancing.vert.glsl", project::path + "shaders/instancing/instancing.frag.glsl");

N_instances = 6000;
numarray<vec3> instance_positions(N_instances);
for(int i=0; i< N_instances; ++i)
	instance_positions[i] = { rand_uniform(-L,L), rand_uniform(-L,L), 0.f };
grass.initialize_supplementary_data_on_gpu(instance_positions, /*location*/ 4, /*divisor: 1=per instance, 0=per vertex*/ 1);
```

- The tuft is 1 unit wide and 1 unit high, standing on $z = 0$. Two quads at right angles look
  like a volume from most directions, for 8 vertices: this is an *impostor*, a flat stand-in
  for a complex shape.
- `material.phong = {1,0,0,1}` keeps only the ambient term (ambient 1, no diffuse, no
  specular): the grass shows the colors of its image, without a dark side.
- The 6000 positions live on the CPU only during `initialize()`: once copied to the GPU, the
  `numarray` is freed. To move the tufts later, the array would have to be kept in the scene
  and re-sent (`update_supplementary_data_on_gpu`).

In the vertex shader, the only change compared to the default one is the new input and the
offset added to the vertex position, before the model matrix:

```glsl
// shaders/instancing/instancing.vert.glsl
layout (location = 4) in vec3 instance_position;  // instance position  (x,y,z)
// ...
vec4 position = model * vec4(vertex_position + instance_position, 1.0);
```

The diagram of the two buffers (per vertex, per instance) is in the how-to
[Draw thousands of copies with instancing](../how-to/draw-many-instances.md#why-instancing).

## 3. One draw call per frame

```cpp
// src/scene.cpp - display_frame
draw(tree, environment);
draw(ground, environment);

// Draw the instances of grass: the third parameter is the number of instances to display
draw(grass, environment, N_instances);
```

The third argument of `draw` is the number of instances: the GPU runs the vertex shader
$8 \times 6000$ times in one call, with `instance_position` taking the value of copy $i$ for
the 8 vertices of copy $i$. Compare with the loop of
[Walk on a plane with the keyboard](camera-2d-displacement.md#3-a-field-of-poles-drawn-in-a-loop),
which pays one draw call, and one upload of the uniforms, for each of its 399 poles. The
fragment shader discards the pixels whose alpha is below 0.5, so that the transparent parts of
the image leave no white rectangle (see
[Draw transparent objects](../how-to/draw-transparent-objects.md)).

The "Wireframe" checkbox calls `draw_wireframe(grass, environment, {0,0,1}, N_instances)`,
which draws nothing in the browser (see [Display the wireframe](../how-to/display-the-wireframe.md)).

## Going further

- Vary the size of the tufts: send a per-instance scale at location 5 and multiply
  `vertex_position` by it in the shader.
- Make the grass grow around the tree only: draw the positions in a disc, or reject those too
  close to the trunk.
- Compute everything in the shader instead, without any position buffer: the next example,
  [Procedural grass in the vertex shader](instancing-procedural.md).

## See also

- How-to: [Draw thousands of copies with instancing](../how-to/draw-many-instances.md), [Load a 3D model from an OBJ file](../how-to/load-an-obj-file.md), [Draw transparent objects](../how-to/draw-transparent-objects.md)
- Understand: [From CPU to GPU](../understand/cpu-to-gpu.md), [Shaders and uniforms](../understand/shaders-and-uniforms.md)
- Reference: [`mesh_drawable`](../reference/mesh_drawable.md), [`numarray`](../reference/numarray.md)
