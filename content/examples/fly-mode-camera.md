---
title: Fly over a terrain
section: Examples
group: Cameras and interaction
order: 13
local_names: [terrain, display_info]
description: A plane-like camera that always moves forward over a textured terrain loaded from an OBJ file - camera_controller_fly_mode, its keys, its speed, and a light that follows the camera.
---

# Fly over a terrain

**What it shows**: a camera that behaves like a plane. It **always moves forward**, and the
keyboard and the mouse only steer it: pitch the nose up or down, roll around the direction of
flight, speed up or slow down. The scene is a mountain terrain loaded from an OBJ file with its
texture, lit from the position of the camera.

<!-- demo: fly-mode-camera -->

> **Controls.** Click in the demo first, so that it receives the keys. The camera starts
> slowly (0.05 units per second): hold **R** to speed up.
>
> | Input | Effect |
> |---|---|
> | Up / Down arrows, W / S (Z / S on AZERTY) | Up: the nose goes down; Down: the nose goes up |
> | Left / Right arrows, A / D (Q / D on AZERTY) | roll |
> | R or keypad +, F or keypad - | speed up, slow down |
> | Left drag | vertical motion: pitch, horizontal motion: roll |
> | Shift + C, Esc | capture the cursor (the camera follows the mouse without a click), release it |
>
> There is no collision: the camera flies through the terrain. The "Wireframe" checkbox draws
> nothing in the browser (see [Display the wireframe](../how-to/display-the-wireframe.md)).

Concepts combined in this example:

- the camera controller `camera_controller_fly_mode`, in place of the orbit camera of the
  template;
- a mesh loaded with `mesh_load_file_obj` and textured with
  `load_and_initialize_texture_2d_on_gpu`, placed with its `model` transform;
- a light that moves with the camera (`environment.light`).

Source: [`examples/07_camera/01_camera_fly_mode`](https://github.com/drohmer/epita_ani3d_lab_code-2027/tree/main/examples/07_camera/01_camera_fly_mode)
of the public repository *epita_ani3d_lab_code-2027*, run unchanged in the demo above. How to
change the camera of your own scene is the subject of
[Explore a scene with a first-person camera](../how-to/explore-with-a-first-person-camera.md);
this page looks at the complete flying program.

| File | Role |
|---|---|
| `src/scene.hpp`, `src/scene.cpp` | the scene: the controller, the terrain, the callbacks |
| `assets/terrain.obj`, `assets/terrain.jpg` | the terrain mesh (positions, uv, normals) and its texture |

## 1. A controller of another type

The only change of the camera is the type of the member `camera_control`:

```cpp
// src/scene.hpp - scene_structure
// Special camera mode adapted to a fly mode
camera_controller_fly_mode camera_control;
```

`initialize()` gives it access to the inputs and to the window, and that is all: there is no
`look_at` and no rotation axis.

```cpp
// src/scene.cpp - initialize
camera_control.initialize(inputs, window); // Give access to the inputs and window global state to the camera controler
display_info();
```

The camera therefore starts at the origin, with the identity orientation of its camera model
(`camera_first_person`): it looks toward $-z$, with $y$ up. The terrain is modeled with $y$ as
its vertical axis, so the flight starts level, inside the valley. `display_info` prints the
controls (`camera_control.doc_usage()`) in the terminal (the browser console for the demo).

## 2. The terrain

```cpp
// src/scene.cpp - initialize
terrain.initialize_data_on_gpu(mesh_load_file_obj(project::path+"assets/terrain.obj"));
terrain.texture.load_and_initialize_texture_2d_on_gpu(project::path + "assets/terrain.jpg");
terrain.model.scaling = 3.0;
terrain.model.translation = { 0.0f, -0.2f, 0.0f };
```

The OBJ file is about 4.8 units wide; scaled by 3, the terrain spans about 14.5 units, and its
heights go from about -0.5 to 2 after the translation: the camera, at height 0, flies between
the mountains. The file already contains the uv coordinates of the texture and the normals,
which `mesh_load_file_obj` reads (see [Load a 3D model from an OBJ file](../how-to/load-an-obj-file.md)).

## 3. What the controller does at every frame

The template forwards the events to the controller; this example keeps the template callbacks
(`mouse_move_event` still ignores the motion while Shift is held). Everything happens in the
`idle_frame` of the controller, called at every frame before `display_frame`. Here is its code
in CGP:

```cpp
// cgp/19_camera_controller/camera_controller_fly_mode/camera_controller_fly_mode.cpp - idle_frame
float const magnitude = inputs->time_interval;

if (inputs->keyboard.up || inputs->keyboard.is_pressed(GLFW_KEY_W))
    camera_model.manipulator_rotate_roll_pitch_yaw(0, pitch * magnitude, 0);
// ... down / S, left / A, right / D: the same with -pitch, roll, -roll

float const speed_factor = std::pow(speed_increase, 60.0f * magnitude);
if (inputs->keyboard.is_pressed(GLFW_KEY_KP_ADD) || inputs->keyboard.is_pressed(GLFW_KEY_R))
    speed = std::min(speed * speed_factor, speed_max);
// ... keypad - / F: divide, down to speed_min

camera_model.manipulator_translate_front(speed * magnitude);
```

- **Always forward.** The last line runs at every frame, whatever the keys: the camera moves
  by `speed` times the duration of the frame along its front direction, so `speed` is in units
  per second (0.05 by default, between `speed_min` = 0.0001 and `speed_max` = 0.5).
- **Frame-rate independent.** Rotations and speed changes are also multiplied by the frame
  duration. `speed_increase` (1.02) is the factor per frame at 60 frames per second; raising
  it to the power $60\,\Delta t$ gives the same acceleration per second at any frame rate.
- **Rotations in the frame of the camera.** `manipulator_rotate_roll_pitch_yaw` composes the
  rotation on the right of the current orientation: the pitch turns around the current *right*
  axis of the camera, the roll around its current *front* axis, as for a plane. There is no
  fixed up axis (the camera model stores a free rotation, not Euler angles): after a roll, the
  horizon stays tilted until you roll back.
- The mouse does the same with the motion of the cursor (left button held, or always once the
  cursor is captured with Shift + C): `manipulator_rotate_roll_pitch_yaw(-dp.x, dp.y, 0)`.

The table of all the controllers and their keys is in
[Mouse, keyboard and camera controllers](../understand/interaction.md#controls-as-coded).

## 4. A light attached to the camera

```cpp
// src/scene.cpp - display_frame
environment.camera_view = camera_control.camera_model.matrix_view();
environment.light = camera_control.camera_model.position();
```

The view matrix is read from the controller at every frame, as in the template. The light is
placed at the eye: the slopes that face the camera are the brightest, like the headlight of
a vehicle, wherever you fly.

## Going further

- Start from a chosen position and direction: in `initialize()`, after
  `camera_control.initialize(inputs, window)`, call `camera_control.look_at(eye, target, {0,1,0})`
  (this controller needs the up vector).
- Start faster: set `camera_control.speed` in `initialize()`; raise `speed_max` for a faster
  plane.
- Keep the plane above the ground: after `camera_control.idle_frame()`, clamp
  `camera_control.camera_model.position_camera.y` to a minimal height.
- Compare with a walking camera: [Walk on a plane with the keyboard](camera-2d-displacement.md).

## See also

- How-to: [Explore a scene with a first-person camera](../how-to/explore-with-a-first-person-camera.md), [Load a 3D model from an OBJ file](../how-to/load-an-obj-file.md)
- Understand: [Mouse, keyboard and camera controllers](../understand/interaction.md), [Camera and matrices](../understand/camera-and-matrices.md), [Time and animation](../understand/time-and-animation.md)
- Reference: [`camera_controller_fly_mode`](../reference/camera_controller_fly_mode.md), [`camera_first_person`](../reference/camera_first_person.md)
