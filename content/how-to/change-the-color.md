---
title: Change the color of a shape
section: How-to
group: Appearance and textures
order: 8
description: Change the color of a shape with material.color, give each vertex its own color, tint a texture, make a shape transparent, and change the color while the program runs or from the GUI.
---

# Change the color of a shape

**Goal**: change the color of a shape, as a whole or vertex by vertex, and change it while
the program runs with a color picker.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

<!-- demo: change-the-color -->

## Where the color of a pixel comes from

The default shader (`shaders/mesh/mesh.frag.glsl`) multiplies three colors, then applies
the Phong lighting:

```text
color_object = vertex color  x  material.color  x  texture color        (per channel, RGB in [0,1])
pixel        = (ambient + diffuse * cos) * color_object  +  specular * highlight (white)
alpha        = material.alpha  x  texture alpha
```

| Source | Set with | Default |
|---|---|---|
| One color for the whole shape | `material.color` of the `mesh_drawable` | white `{1,1,1}` |
| One color per vertex | `color` of the `mesh`, before the upload | white (filled by the primitives) |
| A texture image | `texture` of the `mesh_drawable` | a 1x1 white image |

Since the defaults are white, setting one of them is enough: the two others leave it
unchanged. Colors are `vec3` with components between 0 and 1 (not 0 to 255).

## 1. One color for the whole shape: `material.color`

The template already does it for its two shapes:

```cpp
// scene.cpp - already in the template, in initialize()
sphere.material.color = {1.0f, 0.0f, 0.0f};
cylinder.material.color = {0.0f, 1.0f, 0.0f};
```

For a new shape, set the color **after** `initialize_data_on_gpu`: this function resets the
material (and the `model` transform) to their default values.

```cpp
// scene.hpp - add in scene_structure
mesh_drawable ball;
```

```cpp
// scene.cpp - add at the end of initialize()
ball.initialize_data_on_gpu(mesh_primitive_sphere(0.25f));
ball.model.translation = {0.5f, 0.75f, 0.0f};
ball.material.color = {0.2f, 0.4f, 1.0f};   // blue: R, G, B in [0,1]
```

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(ball, environment);
```

`material.color` is sent to the shader (uniform `material.color`) at every `draw` call: it
costs nothing to change it, even at every frame (see section 3).

## 2. One color per vertex: `mesh.color`

To vary the color over the surface, fill the per-vertex array `color` of the `mesh`
**before** the upload. Here, a gradient from blue at the bottom to red at the top:

```cpp
// scene.hpp - add in scene_structure
mesh_drawable colored_ball;
```

```cpp
// scene.cpp - add at the end of initialize()
mesh colored_ball_mesh = mesh_primitive_sphere(0.25f);
for (size_t k = 0; k < colored_ball_mesh.position.size(); ++k) {
    float const t = (colored_ball_mesh.position[k].z + 0.25f) / 0.5f;   // 0 at the bottom, 1 at the top
    colored_ball_mesh.color[k] = {t, 0.2f, 1.0f - t};
}
colored_ball.initialize_data_on_gpu(colored_ball_mesh);
colored_ball.model.translation = {-0.5f, -0.75f, 0.0f};
```

```cpp
// scene.cpp - add in display_frame(), before timer.update()
draw(colored_ball, environment);
```

The `mesh_primitive_*` functions fill `color` with white, so it already has one entry per
vertex. For a mesh built by hand, give `color` the size of `position` (or call
`fill_empty_field()` first, see [Build a mesh by hand](build-a-mesh-by-hand.md)). The colors
are interpolated between the vertices of each triangle.

The material color still multiplies the vertex colors: keep `material.color` white to see
them as they are. A non-white material color filters them: with `{1,1,0}` (yellow), the blue
part of the gradient becomes black.

To change the vertex colors after the upload, modify the `mesh` and send the new array to the
GPU: `colored_ball.vbo_color.update(colored_ball_mesh.color)` (keep the mesh as a member of
the scene for this; see [Update a mesh at every frame](update-a-mesh-every-frame.md)).

## 3. Change the color while the program runs, or from the GUI

Since `material.color` is read at each `draw`, assign it in `display_frame()`. With a color
picker in the GUI:

```cpp
// scene.hpp - add in gui_parameters
vec3 ball_color = {0.2f, 0.4f, 1.0f};
```

```cpp
// scene.cpp - add in display_gui()
ImGui::ColorEdit3("Ball color", &gui.ball_color[0]);   // edits 3 consecutive floats
```

The whole `display_frame()` becomes:

```cpp
// scene.cpp - replace display_frame()
void scene_structure::display_frame()
{
    environment.camera_view = camera_control.camera().matrix_view();
    environment.light = camera_control.camera_model.position();

    if (gui.display_frame)
        draw(global_frame, environment);

    draw(sphere, environment);
    cylinder.model.rotation = rotation_transform::from_axis_angle({1,0,0}, timer.t);
    draw(cylinder, environment);

    ball.material.color = gui.ball_color;   // the color chosen in the GUI
    draw(ball, environment);

    // the color can also depend on time: here the green channel oscillates
    colored_ball.material.color = {1.0f, 0.5f + 0.5f * std::cos(2 * timer.t), 1.0f};
    draw(colored_ball, environment);

    timer.update();
}
```

Changing `material.color` never requires a new `initialize_data_on_gpu`.

## 4. Tint a texture

With a texture (see [Apply a texture image](apply-a-texture.md)), the color of the image is
multiplied by `material.color` as well: leave it white to see the image as it is, or set it
to tint the image (`{1.0f, 0.8f, 0.6f}` warms it up). To drop the texture and get back to a
plain color, set `material.texture_settings.active = false`.

## 5. Transparency: `material.alpha`

`material.alpha` (1 by default) is the opacity of the shape: `ball.material.alpha = 0.5f;`
makes it half transparent. It is only visible when blending is enabled
(`glEnable(GL_BLEND)`), and transparent shapes must be drawn after the opaque ones: see
[Draw transparent objects](draw-transparent-objects.md).

## 6. Shading: brighter, matte, or flat color

The lighting coefficients are in `material.phong` (type `phong_parameters`):

| Field | Default | Effect |
|---|---|---|
| `phong.ambient` | 0.3 | color even where the light does not reach |
| `phong.diffuse` | 0.6 | color on the side facing the light |
| `phong.specular` | 0.3 | white highlight (0: matte surface) |
| `phong.specular_exponent` | 64 | size of the highlight (larger: smaller and sharper) |

With the defaults, a surface facing the light shows 90% of its color (0.3 + 0.6) plus the
highlight. To display the exact color, without shading (a flat color, as in a diagram), use
only the ambient term: `ball.material.phong = {1, 0, 0, 1};`.

## Common pitfalls

- **The color is ignored, the shape stays white**: the color was set before
  `initialize_data_on_gpu`, which resets the material. Set it after.
- **The shape is black**: one factor of the product is zero: `material.color` of `{0,0,0}`,
  vertex colors left at zero (a `color` array resized without being filled), or a vertex
  color and a material color with no common channel (pure red times pure blue). See also
  [Troubleshooting](../get-started/troubleshooting.md#a-shape-is-black-or-very-dark).
- **The color is saturated, not the one chosen**: the components were given between 0 and
  255 (`{255, 128, 0}`); divide them by 255.
- **Colors look darker than the value set**: the shading multiplies them by at most 0.9 on
  the lit side and 0.3 on the dark side; use the ambient-only material above for exact colors.
- **Per-vertex colors do not change after editing `mesh.color`**: the GPU has its own copy;
  call `vbo_color.update(...)`.
- **With your own shader, the colors have no effect**: the shader must read the vertex color
  (location 2) and the uniform `material.color`, as *mesh.frag.glsl* does.

## Variations

- Background of the window: `environment.background_color = {0.1f, 0.1f, 0.15f};` in
  `initialize()` (white by default).
- Curves and segments: a `curve_drawable` has its own `color` member (red by default), see
  [Draw curves, segments and trajectories](draw-curves-and-segments.md).
- Color of the lines of `draw_wireframe`: its third argument, see
  [Display the wireframe of a mesh](display-the-wireframe.md).
- One color per copy with instancing: a per-instance color attribute, see
  [Draw thousands of copies with instancing](draw-many-instances.md).

## See also

- How-to: [Add GUI controls](add-gui-controls.md), [Create basic shapes](create-basic-shapes.md)
- Understand: [Shaders and uniforms](../understand/shaders-and-uniforms.md) (the material uniforms of the default shader)
- Reference: [`material_mesh_drawable_phong`](../reference/material_mesh_drawable_phong.md), [`phong_parameters`](../reference/phong_parameters.md), [`mesh`](../reference/mesh.md)
