---
title: Explore a scene with a first-person camera
section: How-to
group: Animation and interaction
order: 19
description: Replace the default orbit camera by a walking or flying first-person camera controlled with the keyboard and the mouse.
---

# Explore a scene with a first-person camera

**Goal**: walk on a large ground with the arrow keys (or WASD/ZQSD) and look around with
the mouse, as in a game, instead of rotating around the origin.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: explore-with-a-first-person-camera -->

## Choose a camera controller

The camera of the default scene is driven by a *controller*: an object that reads the
mouse and keyboard and updates a camera model. Changing the behavior of the camera only
means changing the type of `camera_control`:

| Controller | Behavior |
|---|---|
| `camera_controller_orbit_euler` | default: rotates around a target point, keeps the up axis |
| `camera_controller_2d_displacement` | walks on a plane: arrows/WASD move, left drag looks around |
| `camera_controller_fly_mode` | plane-like flight: always moves forward, arrows pitch and roll |
| `camera_controller_first_person` | free rotation around the camera position, no fixed up axis |

All controllers share the same functions (`initialize`, `action_mouse_move`,
`action_keyboard`, `idle_frame`, `camera()`), so the rest of the scene does not change.

## 1. Change the type (scene.hpp)

In `scene_structure`, change the type of the existing `camera_control` member (do not add a
second one), and add a ground to walk on:

```cpp
// scene.hpp - replace the line `camera_controller_orbit_euler camera_control;`
camera_controller_2d_displacement camera_control;
```

```cpp
// scene.hpp - add in scene_structure
mesh_drawable ground;
```

## 2. Set the up axis and the initial view (once)

At the beginning of `initialize()`, the template already calls
`camera_control.initialize(inputs, window)` and `set_rotation_axis_z()` (z is the up
direction: the camera walks in the xy plane). Replace its `look_at` call by:

```cpp
// scene.cpp - replace the camera_control.look_at call in initialize()
camera_control.look_at({ 0.0f, -5.0f, 1.0f } /*eye*/, { 0,0,1.0f } /*target*/);
```

Then create the ground, under the shapes of the template:

```cpp
// scene.cpp - add at the end of initialize()
ground.initialize_data_on_gpu(mesh_primitive_quadrangle({-20,-20,-0.5f}, {20,-20,-0.5f}, {20,20,-0.5f}, {-20,20,-0.5f}));
ground.material.color = {0.6f, 0.85f, 0.5f};
```

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(ground, environment);
```

The eye is at z = 1, that is 1.5 above the ground: the displacements keep this height
constant. The function display_info of the template prints the controls of the current
controller (`camera_control.doc_usage()`) in the terminal.

## 3. Forward the events (every frame)

The template already calls the controller in each callback. Only remove the `shift` test
in `mouse_move_event`: with this controller, Shift is the "run" key.

```cpp
// scene.cpp - replace mouse_move_event()
void scene_structure::mouse_move_event()
{
    camera_control.action_mouse_move();    // left drag: look around, right drag: move forward
}
```

The other two callbacks stay as they are:

```cpp
// scene.cpp - already in the template
camera_control.action_keyboard();      // in keyboard_event(): Shift+C captures the mouse cursor, Esc releases it
camera_control.idle_frame();           // in idle_frame(): arrows / WASD move, at every frame
```

`display_frame()` does not change: `camera_control.camera().matrix_view()` returns the view
matrix of any controller.

## Common pitfalls

- **The keys do nothing**: `idle_frame()` does not call `camera_control.idle_frame()`. The
  displacement is applied there, at every frame, as long as a key is pressed (not in
  `keyboard_event`, which is only called when a key changes state).
- **The camera walks on a wall or the horizon is tilted**: the up axis does not match the
  scene. Call `set_rotation_axis_z()` for a z-up scene (the CGP default), `set_rotation_axis_y()`
  for a y-up scene (many OBJ files), and call it *before* `look_at`.
- **The mouse cursor disappears and the camera turns by itself**: Shift+C captured the
  cursor (infinite mouse tracking for game-like control). Press Esc or Shift+C to release it.
- **Compile error on `camera_control.look_at` with two arguments**: the fly and free
  controllers (`camera_controller_fly_mode`, `camera_controller_first_person`) also need the
  up vector, `look_at(eye, target, up)`; the walking one accepts and ignores it.

## Variations

- Fly over a terrain: declare `camera_controller_fly_mode camera_control;` and initialize it
  with `camera_control.look_at({0,-5,2}, {0,0,0}, {0,0,1});`. Tune its speed with
  `camera_control.speed` (keys R/F or +/- change it at run time, up to `speed_max`).
- Follow the ground of a terrain: after `camera_control.idle_frame()`, set the height of
  the camera, `camera_control.camera_model.position_camera.z = terrain_height(x, y) + 1.7f;`
  where terrain_height is your own function.
- Render the same frame from a second, fixed camera: declare a second controller, and before
  drawing the shapes it should see, set `environment.camera_view` to
  `camera2_control.camera().matrix_view()` (both cameras draw into the same image).

Source: EPITA Ani3D repository `epita_ani3d_lab_code-2027`, examples
`07_camera/01_camera_fly_mode`, `07_camera/02_camera_2d_displacement` and
`07_camera/03_multiple_cameras` (scene.hpp and scene.cpp).

## See also

- How-to: [Draw a mesh with a camera](draw-a-mesh.md), [Load a 3D model from an OBJ file](load-an-obj-file.md)
- Understand: [Camera and matrices](../understand/camera-and-matrices.md), [Scene structure](../understand/scene-structure.md),
  [Mouse, keyboard and camera controllers](../understand/interaction.md) (the
  [controls of every controller](../understand/interaction.md#controls-as-coded))
- Reference: [`camera_projection_perspective`](../reference/camera_projection_perspective.md)
