---
title: Animate a shape with time
section: How-to
group: Animation and interaction
order: 16
description: Use a timer_basic to make a shape rotate or move smoothly, at the same speed on every computer.
---

# Animate a shape with time

**Goal**: make a cylinder spin and a sphere bob up and down, driven by the elapsed time
in seconds (not by the number of frames).

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already contains the cylinder, the
> sphere and the timer used here, and already spins the cylinder: it is the smallest
> animated scene. This page explains its code and adds the bobbing sphere. Do not declare
> these members again.

<!-- demo: animate-with-time -->

## The timer

`timer_basic` measures real time. Its member `t` is the time in seconds since the first
call to `update()`, and it advances only when you call `update()` (once per frame).

| Member | Role |
|---|---|
| `t` | Current time in seconds (float) |
| `update()` | Advances `t` by the elapsed time and returns this increment dt |
| `scale` | Speed factor (`1` = real time, `0.5` = slow motion) |
| `stop()` / `start()` | Pause and resume |

## 1. The timer and the drawables (already declared)

```cpp
// scene.hpp - already in the template, in scene_structure
mesh_drawable sphere;
mesh_drawable cylinder;
timer_basic timer;
```

## 2. The shapes (already created)

```cpp
// scene.cpp - already in the template, in initialize()
sphere.initialize_data_on_gpu(mesh_primitive_sphere(0.25f));
sphere.model.translation = {-0.5f, 0.75f, 0.0f};
sphere.material.color = {1.0f, 0.0f, 0.0f};

cylinder.initialize_data_on_gpu(mesh_primitive_cylinder(0.1f, {0,0,-0.5f}, {0,0,0.5f}));
cylinder.model.translation = {0.5f, -0.75f, 0.0f};
cylinder.material.color = {0.0f, 1.0f, 0.0f};
```

## 3. Update the transforms and the timer (every frame)

Replace the whole `display_frame()` of the template by:

```cpp
// scene.cpp - replace display_frame()
void scene_structure::display_frame()
{
    environment.camera_view = camera_control.camera().matrix_view();
    environment.light = camera_control.camera_model.position();

    if (gui.display_frame)
        draw(global_frame, environment);

    float const t = timer.t;   // seconds since the first timer.update()

    // Rotation: the angle grows linearly with time (1 radian per second)
    cylinder.model.rotation = rotation_transform::from_axis_angle({1,0,0}, t);
    draw(cylinder, environment);

    // Oscillation: periodic motion with sin/cos (new lines)
    sphere.model.translation = {-0.5f, 0.75f, 0.2f * std::sin(2 * Pi * 0.5f * t)}; // 0.5 Hz
    draw(sphere, environment);

    timer.update();   // once per frame, at the end: advances timer.t for the next frame
}
```

`timer.update()` is called once, at the end of the function, as in the template. Do not add
a second call at the beginning: the time would then run twice as fast.

## Common pitfalls

- **The shape does not move**: `timer.update()` is never called, or it is called in
  `initialize()` only. Call it once per frame in `display_frame()`.
- **The animation runs too fast**: `timer.update()` is called twice per frame (for
  instance once added at the beginning of `display_frame()` while the template already
  calls it at the end). Keep a single call.
- **Speed depends on the computer**: do not write `angle += 0.01f` at each frame; the
  frame rate varies. Use `timer.t`, or multiply speeds by the increment dt returned by
  `timer.update()`.
- **Two timers drift apart**: each `timer_basic` counts from its own first `update()`
  and advances only with its own `update()` calls. Use a single timer for motions that must stay synchronized.

## Variations

- Pause the animation from the GUI: call `timer.stop()` / `timer.start()`, or set
  `timer.scale = 0` (see [Add GUI controls](add-gui-controls.md)).
- Physics-like integration: keep the increment returned by the single call of the
  frame, `float const dt = timer.update();`, then `position += dt * velocity;`.
- Trigger an action every N seconds: `timer_event_periodic`, a timer with an
  `event_period` and a boolean `event` that is true during the frame where a period ends
  (see [Spawn objects periodically](spawn-objects-periodically.md)).

Source: course labs of CSC_43043 ([public version](https://github.com/drohmer/csc43043ep-lab-code), without the solutions): [`00_test_installation`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/00_test_installation) (rotating cylinder) and
[`08_project`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/08_project) (bobbing cube), scene.cpp.

## See also

- How-to: [Move, rotate and scale a shape](transform-a-shape.md)
- Understand: [Scene structure](../understand/scene-structure.md)
- Reference: [`rotation_transform`](../reference/rotation_transform.md), [`mesh_drawable`](../reference/mesh_drawable.md)
