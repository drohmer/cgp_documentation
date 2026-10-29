---
title: Send a custom uniform to a shader
section: How-to
group: Shaders and rendering
order: 22
description: Load your own GLSL shader, assign it to a drawable, and send it extra parameters (time, coefficients, colors) through environment.uniform_generic.
---

# Send a custom uniform to a shader

**Goal**: make a flat grid wave in the vertex shader, driven by a time value and an
amplitude slider sent from the C++ code.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: send-a-custom-uniform -->

## Where your uniforms come from

`draw` already sends the uniforms of the drawable (`model`, `material`) and of the
environment (`view`, `projection`, `light`); the full list and their order are in
[Shaders and uniforms](../understand/shaders-and-uniforms.md#3-three-levels-of-uniforms).
Your own values go in `environment.uniform_generic`, a `uniform_generic_structure` with one
map per GLSL type (`uniform_float`, `uniform_vec3`...): each entry `name -> value` is sent to
the shader of every drawable at each `draw` call, where it is declared as
`uniform <type> name;`.

## 1. Write the shader

Copy `shaders/mesh/mesh.vert.glsl` to `shaders/mesh_custom/mesh_custom.vert.glsl`, declare
the new uniforms and use them:

```glsl
// shaders/mesh_custom/mesh_custom.vert.glsl (only the changed lines)
uniform float time;       // seconds, sent from C++
uniform float amplitude;  // set by a GUI slider

void main()
{
    vec3 p = vertex_position;
    p.z += amplitude * sin(6.0 * p.x + 3.0 * time);
    vec4 position = model * vec4(p, 1.0);
    // ... rest of the default shader unchanged
}
```

## 2. Load it and assign it to a drawable (once)

The time comes from the timer of the template: do not declare a second one.

```cpp
// scene.hpp - add in scene_structure
mesh_drawable water;
float amplitude = 0.1f;
```

```cpp
// scene.cpp - add at the end of initialize()
water.initialize_data_on_gpu(mesh_primitive_grid({-1,-1,0}, {1,-1,0}, {1,1,0}, {-1,1,0}, 100, 100));
water.model.translation = {0, 0, -0.5f};   // under the sphere and the cylinder of the template
water.material.color = {0.5f, 0.6f, 0.8f};

opengl_shader_structure shader_custom;
shader_custom.load(
    project::path + "shaders/mesh_custom/mesh_custom.vert.glsl",
    project::path + "shaders/mesh/mesh.frag.glsl");      // keep the default fragment shader
water.shader = shader_custom;
```

`load` compiles and links the two files; the program stops with the GLSL compiler
message if the shader has an error. Assigning the shader to a drawable only copies its
GPU id: several drawables can share it.

## 3. Set the values (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
environment.uniform_generic.uniform_float["time"] = timer.t;
environment.uniform_generic.uniform_float["amplitude"] = amplitude;

draw(water, environment);
```

The template already calls `timer.update()` once, at the end of `display_frame()`.

```cpp
// scene.cpp - add in display_gui()
ImGui::SliderFloat("Amplitude", &amplitude, 0.0f, 0.3f);
```

A `vec3` is sent the same way: `environment.uniform_generic.uniform_vec3["light_color"] = {1,1,1};`
matches `uniform vec3 light_color;` in GLSL.

## Common pitfalls

- **Warning "Try to send uniform variable [time] to a shader that doesn't use it"**: the
  `uniform_generic` values are sent to *every* drawn shape, including those using the
  default shader, which does not declare time. It also happens when the uniform is
  declared but unused: the GLSL compiler removes it. The warning is harmless; silence it
  with `cgp_warning::max_warning = 0;` in `initialize()`.
- **The value never changes**: the name in the map and in GLSL differ (case included), or
  the map does not match the GLSL type (a `uniform int` is filled from `uniform_int`, a
  `uniform float` from `uniform_float`).
- **The shape keeps the default look**: the shader was assigned to another drawable, or
  the file you edited is not the one loaded (compare with the path given to `load`).
- **Normals and lighting do not follow the waves**: the vertex shader moved the
  positions but not the normals. Compute the normal in the shader from the derivative of
  the displacement if the lighting matters.

## Variations

- Load the shader directly into the drawable, for a shader used by one shape only:
  `water.shader.load(vertex_path, fragment_path);` (the other shapes keep the default
  shader, see [Shaders and uniforms](../understand/shaders-and-uniforms.md)).
- Uniform for a single drawable only: pass a `uniform_generic_structure` as the
  `additional_uniforms` argument of `draw`.
- Custom fragment shader as well (Phong coefficients, fog...): copy
  `shaders/mesh/mesh.frag.glsl` the same way and declare `uniform float coeff_ambient;`
  etc.
- Release a shader explicitly: `shader_custom.clear()` (new in cgp-2027), only once no
  drawable uses it any more (the drawables hold copies of the same GPU id).

Source: course labs of CSC_43043 ([public version](https://github.com/drohmer/csc43043ep-lab-code), without the solutions): [`05_shaders/b_shading_effect`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/05_shaders/b_shading_effect) (scene.cpp and mesh_custom.frag.glsl: Phong
coefficients and light_color from the GUI) and [`07_texture/d_animation`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/07_texture/d_animation) (liquid surface
animated in the vertex shader).

## See also

- How-to: [Add GUI controls](add-gui-controls.md), [Update a mesh at every frame](update-a-mesh-every-frame.md)
- Understand: [Shaders and uniforms](../understand/shaders-and-uniforms.md)
- Reference: [`opengl_shader_structure`](../reference/opengl_shader_structure.md), [`environment_generic_structure`](../reference/environment_generic_structure.md), [`mesh_drawable`](../reference/mesh_drawable.md)
