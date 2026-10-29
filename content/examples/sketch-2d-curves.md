---
title: A 2D sketching program
section: Examples
group: Cameras and interaction
order: 16
local_names: [unproject, sketch_drawable, sketch_mode, k_sketch, N_stroke, p_screen, p_proj, camera_view_inverse]
description: Strokes drawn with the mouse, unprojected with the inverse projection and view matrices at a fixed depth - with a perspective or an orthographic camera, and a button to cancel the last stroke.
---

# A 2D sketching program

**What it shows**: a blank window in which you draw strokes with the left mouse button, as on
paper. Each stroke is a curve that grows while the mouse moves; "Cancel last stroke" removes
the last one, and unchecking "Sketch Mode" gives the mouse back to the camera (and shows
the axes). The cursor position is turned into a 3D point by inverting the projection and
view matrices: the example is written for a 2D drawing, where the camera does not move.

<!-- demo: sketch-2d-curves -->

Concepts combined in this example:

- a `numarray` of `curve_drawable_dynamic_extend`, one per stroke, each growing with
  `push_back`;
- the 2D-to-3D conversion done by hand with `matrix_inverse()` of the projection and
  `matrix_frame()` of the camera, at a fixed depth of the normalized device coordinates;
- two overloads of the same function, one per type of projection, chosen by the compiler
  from the type of `camera_projection`;
- a mode switch between sketching and camera control.

Source: [`examples/04_sketch/02_2d_curve`](https://github.com/drohmer/epita_ani3d_lab_code-2027/tree/main/examples/04_sketch/02_2d_curve)
of the public repository *epita_ani3d_lab_code-2027*, run unchanged in the demo above (files
`src/scene.hpp` and `src/scene.cpp`). The how-to
[Sketch curves with the mouse](../how-to/sketch-with-the-mouse.md) builds the same program
step by step, with one change: it intersects the mouse ray with a plane through the origin,
so that the strokes stay in the scene when the camera turns. This page explains what the
example does instead.

## 1. Unprojecting the cursor

`inputs.mouse.position.current` is in $[-1,1]^2$, the $x, y$ of the normalized device
coordinates (NDC). The example picks a depth, $z = 0.5$ in NDC, and goes back through the
two matrices of the camera:

```cpp
// src/scene.cpp - unproject (perspective version)
vec4 const p_proj = camera_view_inverse * P.matrix_inverse() *  vec4(p_screen, 0.5f, 1.0f);
return p_proj.xyz()/p_proj.w;
```

`P.matrix_inverse()` goes from NDC to camera space, and `camera_view_inverse`, the
argument `camera_control.camera_model.matrix_frame()`, from camera space to world space
(it is the inverse of `matrix_view()`). With a perspective projection, the result has a
$w \neq 1$: the division by $w$ gives the actual point.

**At which distance?** The depth in NDC is not proportional to the distance. With the
default `depth_min` = 0.01 and `depth_max` = 1000 of `camera_projection_perspective`, the
depth 0.5 corresponds to a distance $d$ such that

$$
z_{ndc} = \frac{f+n}{f-n} - \frac{2fn}{(f-n)\,d} = 0.5 \quad\Rightarrow\quad d \approx \frac{2n}{1 - 0.5} = 0.04
$$

So every stroke lies on a plane 0.04 units in front of the camera: a tiny drawing very close
to the eye, which looks like a full-size drawing only from this viewpoint. Uncheck "Sketch
Mode" and turn the camera: the strokes stay near the place where the eye was and leave the
view, while the axes at the center of rotation remain. This is fine for 2D drawing, and it
is why the how-to intersects a plane of the scene instead.

## 2. The orthographic variant

The scene declares two lines, one commented out, to choose the camera:

```cpp
// src/scene.hpp - scene_structure
camera_projection_perspective camera_projection; // uncomment this line for projective perspective
//camera_projection_orthographic camera_projection; // uncomment this line for orthographic projection
```

and `initialize()` has the matching commented line that sets the orthographic box
(`-1.1, 1.1` horizontally, scaled by the aspect ratio, and vertically; depth from -10 to 10).
The file defines `unproject` twice, for `camera_projection_orthographic` and for
`camera_projection_perspective`; the call is the same in both cases, and the compiler picks the
overload from the declared type. The orthographic version skips the division ($w$ stays 1)
and its depth is linear: with the depth range $[-10, 10]$, $z_{ndc} = 0.5$ falls 5 units in
front of the camera, that is 2 units behind the center of rotation (the camera starts at
`{0,0,3}`, looking at the origin). A stroke then has the size it has on screen and lies in
the scene, where it remains when the camera turns.

## 3. Strokes as growing curves

```cpp
// src/scene.cpp - mouse_click_event
if (gui.sketch_mode && inputs.mouse.click.last_action == last_mouse_cursor_action::click_left)
{
	// Create new stroke (curve_dynamic_drawable)
	int k_sketch = sketch_drawable.size();
	sketch_drawable.push_back(curve_drawable_dynamic_extend());
	sketch_drawable[k_sketch].initialize_data_on_gpu();
```

followed by a first `push_back` of the clicked point. Then each `mouse_move_event` with the
left button down appends the new point to the last stroke. `initialize_data_on_gpu()`
reserves room for 100 points; `push_back` doubles the GPU buffer when it is full, and `draw`
displays only the `N_valid_points` points written so far. The strokes keep the color that
`initialize_data_on_gpu` gives to a curve (red).

"Cancel last stroke" frees the GPU buffer of the last curve (`clear()`) before removing it
from the array, so that removing strokes does not leak GPU memory.

## Going further

- Switch to the orthographic camera (the two commented lines), draw, then turn the camera.
- Give each stroke its own color (`color` of the curve), chosen with an `ImGui::ColorEdit3`.
- Smooth or resample a stroke when the mouse is released, before sending its points again
  (see [Draw curves, segments and trajectories](../how-to/draw-curves-and-segments.md)).

## See also

- How-to: [Sketch curves with the mouse](../how-to/sketch-with-the-mouse.md), [Select and drag objects with the mouse](../how-to/select-and-drag-with-the-mouse.md)
- Understand: [Camera and matrices](../understand/camera-and-matrices.md)
- Reference: [`curve_drawable_dynamic_extend`](../reference/curve_drawable_dynamic_extend.md), [`camera_projection_perspective`](../reference/camera_projection_perspective.md)
