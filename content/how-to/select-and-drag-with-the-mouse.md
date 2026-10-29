---
title: Select and drag objects with the mouse
section: How-to
group: Animation and interaction
order: 21
description: Pick a sphere with a mouse click (picking_spheres), drag it in the plane facing the camera (picking_plane_orthogonal_to_camera), and freeze the camera during the drag.
---

# Select and drag objects with the mouse

**Goal**: click on one of several spheres to select it, drag it with the mouse while the
camera stays still, and release it where you want.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `camera_projection`,
> `environment` and `gui`: reuse them, do not declare them again. The first comment of each
> code block says in which file and where its lines go: *add* means insert them, *replace*
> means replace the whole function by the one shown.

<!-- demo: select-and-drag-with-the-mouse -->

## From a click to a 3D object

A point of the screen is not a 3D point but a ray: all the points that project on this pixel.
*Picking* casts this ray from the camera position and intersects it with the scene. CGP
provides two helpers, both taking the cursor position in relative coordinates
(`inputs.mouse.position.current`, in [-1,1] x [-1,1]), the camera model and the projection:

| Function | Intersects the ray with | Returns |
|---|---|---|
| `picking_spheres(position, centers, radius, camera, projection)` | a set of spheres of the same radius | `picking_structure`: `active`, `index` of the closest sphere hit, `position`, `normal` |
| `picking_plane_orthogonal_to_camera(position, plane_position, camera, projection)` | the plane facing the camera and passing through a given point | `intersection_structure`: `valid`, `position` |

## 1. Store the positions and the selection

The spheres are drawn with one `mesh_drawable` placed at each position (as in
[Draw a mesh with a camera](draw-a-mesh.md)); the scene stores their centers and the index of
the dragged one.

```cpp
// scene.hpp - add in scene_structure
mesh_drawable ball;          // one shape, drawn at every position
numarray<vec3> positions;    // centers of the spheres
int picked = -1;             // index of the dragged sphere, -1 if none
```

```cpp
// scene.cpp - add at the end of initialize()
ball.initialize_data_on_gpu(mesh_primitive_sphere(0.15f));
positions = { {-0.5f, -0.75f, 0.8f}, {-0.15f, -0.25f, 1.0f}, {0.15f, 0.25f, 1.0f}, {0.5f, 0.75f, 0.8f} };
```

## 2. Select on click, release on button up

The radius given to `picking_spheres` is the radius of the drawn spheres. The camera is
frozen while a sphere is held: every function of the controller starts by testing
`is_active`.

```cpp
// scene.cpp - replace mouse_click_event()
void scene_structure::mouse_click_event()
{
    if (inputs.mouse.click.last_action == last_mouse_cursor_action::click_left) {
        picking_structure const picking = picking_spheres(inputs.mouse.position.current,
            positions, 0.15f, camera_control.camera_model, camera_projection);
        if (picking.active)
            picked = picking.index;
    }
    if (inputs.mouse.click.last_action == last_mouse_cursor_action::release_left)
        picked = -1;

    camera_control.is_active = (picked == -1);   // no camera motion while dragging
    camera_control.action_mouse_click();
}
```

## 3. Drag in the plane facing the camera

The plane of the drag passes through the sphere itself, so the sphere stays at the same
distance from the camera while it follows the cursor.

```cpp
// scene.cpp - replace mouse_move_event()
void scene_structure::mouse_move_event()
{
    if (picked != -1) {
        intersection_structure const I = picking_plane_orthogonal_to_camera(
            inputs.mouse.position.current, positions[picked],
            camera_control.camera_model, camera_projection);
        if (I.valid)
            positions[picked] = I.position;
    }
    if (!inputs.keyboard.shift)
        camera_control.action_mouse_move();     // does nothing while is_active is false
}
```

## 4. Draw the spheres (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
for (int k = 0; k < int(positions.size()); ++k) {
    ball.model.translation = positions[k];
    ball.material.color = (k == picked) ? vec3{1.0f, 0.5f, 0.0f} : vec3{0.3f, 0.5f, 0.9f};
    draw(ball, environment);
}
```

```cpp
// scene.cpp - add in display_gui()
ImGui::Text("Dragged sphere: %d", picked);
```

Compile and run: a click on a blue sphere turns it orange, and it follows the cursor until the
button is released; a click elsewhere still rotates the camera.

## Common pitfalls

- **Nothing is picked, or the wrong sphere.** Pass the `camera_projection` member of the
  scene, the one the application updates at every frame: its aspect ratio must match the
  window. Use the radius of the drawn spheres (after any `model.scaling`).
- **The camera turns while dragging.** `camera_control.is_active` must be false during the
  drag; it is set in `mouse_click_event`, before calling `action_mouse_click`.
- **The sphere jumps far away or behind the camera.** The drag plane must pass through the
  dragged object (`positions[picked]`), not through a fixed point.
- **A click on the GUI picks a sphere.** The application does not call the mouse callbacks
  when the cursor is over the GUI, but code that reads `inputs` elsewhere (in `idle_frame`)
  must test `inputs.mouse.on_gui`.

## Variations

- Pick the vertices of a mesh you deform (control points):
  `picking_mesh_vertex_as_sphere(position, mesh.position, mesh.normal, distance, camera, projection)`
  treats every vertex as a small sphere.
- Other shapes: the ray direction is given by `camera_ray_direction`, and
  `intersection_ray_plane` / `intersection_ray_sphere` intersect it with a plane or a sphere
  (see [Sketch curves with the mouse](sketch-with-the-mouse.md), Variations, for the ground plane).
- Select on Shift + click only, and keep plain clicks for the camera: test
  `inputs.keyboard.shift` before calling `picking_spheres` (the template convention, see
  [Mouse, keyboard and camera controllers](../understand/interaction.md)).

## See also

- Understand: [Mouse, keyboard and camera controllers](../understand/interaction.md)
  (`input_devices`, the callbacks, disabling the camera),
  [Camera and matrices](../understand/camera-and-matrices.md) (NDC, the projection)
- How-to: [Sketch curves with the mouse](sketch-with-the-mouse.md)
- Reference: [`picking_structure`](../reference/picking_structure.md),
  [`intersection_structure`](../reference/intersection_structure.md),
  [`input_devices`](../reference/input_devices.md)
