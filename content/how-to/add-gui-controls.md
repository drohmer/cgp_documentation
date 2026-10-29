---
title: Add GUI controls
section: How-to
group: Animation and interaction
order: 17
description: Add checkboxes, sliders and color pickers with ImGui in display_gui, and recompute a shape only when a parameter changes.
---

# Add GUI controls

**Goal**: toggle the display of a shape, tune its color and size with sliders, and
regenerate a terrain when one of its parameters is modified.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function or struct by the one shown.

<!-- demo: add-gui-controls -->

## Where the GUI lives

CGP uses the immediate-mode library [Dear ImGui](https://github.com/ocornut/imgui). The
scene template already opens a GUI window and calls `display_gui()`
inside it at every frame. A widget is a single function call that both **draws** the
widget and **writes** the new value into the variable whose address you pass. It returns
true during the frame where the user modified the value.

## 1. Store the parameters

The template provides a `gui_parameters` structure for this purpose, and a member `gui` of
this type in `scene_structure`. Add the new parameters to it:

```cpp
// scene.hpp - replace gui_parameters
struct gui_parameters {
    bool display_frame = false;
    bool display_sphere = true;
    float radius = 0.25f;
    vec3 color = {1, 0, 0};
};
```

```cpp
// scene.hpp - already in the template, in scene_structure
gui_parameters gui;
```

## 2. Add the widgets

```cpp
// scene.cpp - replace display_gui()
void scene_structure::display_gui()
{
    ImGui::Checkbox("Frame", &gui.display_frame);
    ImGui::Checkbox("Sphere", &gui.display_sphere);
    ImGui::SliderFloat("Radius", &gui.radius, 0.05f, 1.0f);   // label, address, min, max
    ImGui::ColorEdit3("Color", &gui.color[0]);                 // 3 consecutive floats
}
```

## 3. Use the values (every frame)

In `display_frame()`, the line `draw(sphere, environment);` of the template becomes four
lines. The whole function:

```cpp
// scene.cpp - replace display_frame()
void scene_structure::display_frame()
{
    environment.camera_view = camera_control.camera().matrix_view();
    environment.light = camera_control.camera_model.position();

    if (gui.display_frame)
        draw(global_frame, environment);

    sphere.model.scaling = gui.radius / 0.25f;   // the sphere is created with radius 0.25
    sphere.material.color = gui.color;
    if (gui.display_sphere)
        draw(sphere, environment);

    cylinder.model.rotation = rotation_transform::from_axis_angle({1,0,0}, timer.t);
    draw(cylinder, environment);

    timer.update();
}
```

Parameters that only change uniforms (transform, color, material) can be read directly
at each frame: they cost nothing.

## Recompute geometry only when a slider moves

When a parameter requires rebuilding a mesh, use the return value of the widgets so that
the costly work runs only on change. Here a terrain whose height comes from a Perlin
noise is recomputed when one of its three sliders moves.

```cpp
// scene.hpp - add in gui_parameters
int octave = 5;
float persistency = 0.3f;
float height = 0.5f;
```

```cpp
// scene.hpp - add in scene_structure
mesh terrain_mesh;         // CPU copy, modified when a slider moves
mesh_drawable terrain;
void update_terrain();     // recompute the heights and send them to the GPU
```

```cpp
// scene.cpp - add at the end of the file
void scene_structure::update_terrain()
{
    int const N = 100;   // terrain_mesh created with mesh_primitive_grid(..., N, N)
    for (int ku = 0; ku < N; ++ku) {
        for (int kv = 0; kv < N; ++kv) {
            vec2 const uv = {ku / (N - 1.0f), kv / (N - 1.0f)};
            terrain_mesh.position[kv + N*ku].z = gui.height * noise_perlin(uv, gui.octave, gui.persistency);
        }
    }
    terrain_mesh.normal_update();
    terrain.vbo_position.update(terrain_mesh.position);
    terrain.vbo_normal.update(terrain_mesh.normal);
}
```

```cpp
// scene.cpp - add at the end of initialize()
terrain_mesh = mesh_primitive_grid({-2,-2,0}, {2,-2,0}, {2,2,0}, {-2,2,0}, 100, 100);
terrain.initialize_data_on_gpu(terrain_mesh);
terrain.model.translation = {0, 0, -1};   // below the shapes of the template
terrain.material.color = {0.6f, 0.85f, 0.5f};
update_terrain();
```

```cpp
// scene.cpp - add in display_gui()
bool update = false;
update |= ImGui::SliderInt("Octave", &gui.octave, 1, 8);
update |= ImGui::SliderFloat("Persistency", &gui.persistency, 0.1f, 0.6f);
update |= ImGui::SliderFloat("Height", &gui.height, 0.1f, 1.5f);
if (update)
    update_terrain();
```

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(terrain, environment);
```

Use `|=` and not `||`: with `||`, the widgets after the first modified one would not be
drawn during that frame.

## Common pitfalls

- **Two widgets interfere**: ImGui identifies a widget by its label. Two widgets with the
  same label share their state; make the labels unique, or add a hidden suffix:
  `"Radius##sphere"` and `"Radius##cube"`.
- **The slider does not move the shape**: the value is written into the gui member, but
  `display_frame()` does not read it (or reads a copy made in `initialize()`).
- **Angles**: `ImGui::SliderAngle` displays degrees but stores radians, which is what
  `rotation_transform::from_axis_angle` expects.
- **Mouse events over the GUI**: the template does not call `mouse_move_event()` and
  `mouse_click_event()` while the mouse is over the GUI window, so dragging a slider does
  not move the camera. The flag `inputs.mouse.on_gui` tells your own code the same thing.

## Variations

- Integer choice: `ImGui::SliderInt`, `ImGui::InputInt`; list of options: `ImGui::Combo`.
- Buttons: `if (ImGui::Button("Reset")) { ... }`.
- Pause an animation, acting only on the frame where the box is clicked (calling
  `start()` at every frame would reset the elapsed time to zero each time):
  `if (ImGui::Checkbox("Pause", &gui.pause)) { if (gui.pause) timer.stop(); else timer.start(); }`.
- Bind a slider directly to a scene value: `ImGui::SliderFloat("x", &camel.model.translation.x, -2, 2);`.

Source: course labs of CSC_43043 ([public version](https://github.com/drohmer/csc43043ep-lab-code), without the solutions): [`07_texture/c_perlin_noise`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/07_texture/c_perlin_noise) (scene.cpp, display_gui with the
`update |=` pattern) and [`05_shaders/b_shading_effect`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/05_shaders/b_shading_effect) (sliders and color pickers).

## See also

- How-to: [Update a mesh at every frame](update-a-mesh-every-frame.md), [Send a custom uniform to a shader](send-a-custom-uniform.md), [Change the color of a shape](change-the-color.md)
- Understand: [Scene structure](../understand/scene-structure.md)
- Reference: [`mesh_drawable`](../reference/mesh_drawable.md), [`mesh`](../reference/mesh.md)
