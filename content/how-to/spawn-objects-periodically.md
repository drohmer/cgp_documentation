---
title: Spawn objects periodically
section: How-to
group: Animation and interaction
order: 18
description: Use timer_event_periodic to create particles at a regular rate, move them with time, remove the old ones, and draw them all with a single drawable.
---

# Spawn objects periodically

**Goal**: emit a new bubble every 0.2 s, make each bubble rise, and remove it after 3 s.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: spawn-objects-periodically -->

## The periodic timer

`timer_event_periodic` is a `timer_basic` (it has `t`, `update()`, `scale`) with two more
members:

| Member | Role |
|---|---|
| `event_period` | Time in seconds between two events (constructor argument, default `1`) |
| `event` | true during the single frame where a period has elapsed, false otherwise |

## 1. Declare the particles, the timer and one drawable

```cpp
// scene.hpp - add before scene_structure
struct particle_bubble {
    vec3 p0;    // initial position
    float t0;   // creation time
};
```

The template already has a `timer_basic timer;`. Change its type instead of declaring a
second timer: a `timer_event_periodic` is also a `timer_basic`, so the rotation of the
cylinder keeps working.

```cpp
// scene.hpp - replace the line `timer_basic timer;`
timer_event_periodic timer;
```

```cpp
// scene.hpp - add in scene_structure
std::vector<particle_bubble> bubbles;
mesh_drawable bubble;            // shared by all the bubbles
```

## 2. Initialize (once)

```cpp
// scene.cpp - add at the end of initialize()
bubble.initialize_data_on_gpu(mesh_primitive_sphere(1.0f));
bubble.material.color = {0.5f, 0.8f, 1.0f};
timer.event_period = 0.2f;       // one new bubble every 0.2 s
```

## 3. Spawn, remove, draw (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
float const t = timer.t;

// Spawn: event is true once per period (set by the timer.update() of the previous frame)
if (timer.event) {
    float const theta = rand_uniform(0.0f, 2 * Pi);
    bubbles.push_back({ 0.5f * vec3{std::cos(theta), std::sin(theta), 0}, t });
}

// Remove the bubbles older than 3 s
auto is_old = [t](particle_bubble const& b) { return t - b.t0 > 3.0f; };
bubbles.erase(std::remove_if(bubbles.begin(), bubbles.end(), is_old), bubbles.end());

// Draw every bubble with the same drawable: change its model, then draw
for (particle_bubble const& b : bubbles) {
    float const age = t - b.t0;
    bubble.model.translation = b.p0 + vec3{0.1f * std::cos(5 * age), 0, 0.5f * age};
    bubble.model.scaling = 0.05f;
    draw(bubble, environment);
}
```

The template already calls `timer.update()` once, at the end of `display_frame()`.
The position is evaluated from the age of the particle (`t - t0`), so its motion does not
depend on the frame rate.

## Common pitfalls

- **No bubble appears**: `timer.update()` is not called, so `event` stays false.
- **Twice as many bubbles as expected**: `timer.update()` is called twice per frame (the
  template already calls it at the end of `display_frame()`). Keep a single call.
- **One mesh_drawable per particle**: do not create a `mesh_drawable` (and call
  `initialize_data_on_gpu`) for each new particle: it allocates GPU memory at every spawn.
  Reuse one drawable and change its `model` before each `draw`.
- **The number of particles grows forever**: remove the old ones; otherwise the frame
  rate drops after a while.
- **Erasing inside a range-for loop**: erasing an element invalidates the loop; use the
  remove_if / erase idiom above (include the header algorithm). The template compiles in
  C++17, so the C++20 shortcut std::erase_if is not available.
- **Events missed when the period is shorter than a frame**: at most one event is
  produced per `update()`. With `event_period` below the frame duration (about 0.016 s
  at 60 fps), spawn several particles per event instead.

## Variations

- Several emitters with different rates: one `timer_event_periodic` per emitter.
- Random size or color per particle: store them in the particle and set
  `bubble.model.scaling` / `bubble.material.color` before each `draw`.
- Smoke or sparks as camera-facing textured quads, fading with age: see
  [Draw transparent objects](draw-transparent-objects.md).
- Pause the emission: `timer.stop()` / `timer.start()`.

Source: course lab of CSC_43043 ([public version](https://github.com/drohmer/csc43043ep-lab-code), without the solutions): [`07_texture/d_animation`](https://github.com/drohmer/csc43043ep-lab-code/tree/main/07_texture/d_animation) (scene.cpp and particles/particles.cpp: bubble
and smoke particles of the cauldron).

## See also

- How-to: [Animate a shape with time](animate-with-time.md), [Move, rotate and scale a shape](transform-a-shape.md)
- Understand: [Scene structure](../understand/scene-structure.md)
- Reference: [`mesh_drawable`](../reference/mesh_drawable.md), [`vec3`](../reference/vec3.md)
