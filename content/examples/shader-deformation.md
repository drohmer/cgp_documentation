---
title: A surface deformed by its vertex shader
section: Examples
group: Shaders and textures
order: 5
local_names: [surface, mesh_grid, deformer, deformer_normal, p0, p_deformed, n_deformed, omega, dpdx, dpdy]
description: A flat grid animated as circular waves entirely on the GPU - the vertex shader moves each vertex with a time uniform and computes the exact normal of the deformed surface from its partial derivatives.
---

# A surface deformed by its vertex shader

**What it shows**: a flat square grid of 200 x 200 vertices, uploaded once, becomes a surface
of circular waves moving out from the center. The C++ code never touches the vertices again:
at every frame it only sends the current time to a custom **vertex shader**, which computes
the deformed position of each vertex and the exact normal of the deformed surface.

<!-- demo: shader-deformation -->

Concepts combined in this example:

- a custom shader loaded on one drawable (`surface.shader.load`);
- a user uniform `time`, sent with `environment.uniform_generic.uniform_float` and updated
  from a `timer_basic`;
- a deformation $z = f(x, y, t)$ applied in the vertex shader, on the GPU, to the 40 000
  vertices at each frame;
- normals computed analytically from the partial derivatives of the deformation;
- a two-sided material (`material.texture_settings.two_sided`), so that the surface is lit
  from below as well.

Source: [`examples/03_shaders/01_deformation`](https://github.com/drohmer/epita_ani3d_lab_code-2027/tree/main/examples/03_shaders/01_deformation)
of the public repository *epita_ani3d_lab_code-2027*, run unchanged in the demo above. The
mechanism of the uniforms (who sends what, the warning for unused uniforms) is explained
in [Shaders and uniforms](../understand/shaders-and-uniforms.md#user-uniforms-uniform_generic),
whose demo also moves a grid with a wave; this example adds the normals.

| File | Role |
|---|---|
| `src/scene.hpp`, `src/scene.cpp` | the scene: creates the grid, sends the time |
| `shaders/mesh_deformation/mesh_deformation.vert.glsl` | the deformation of the positions and of the normals |
| `shaders/mesh_deformation/mesh_deformation.frag.glsl` | identical to the default fragment shader |

## 1. A flat grid and a time uniform

```cpp
// src/scene.cpp - initialize
mesh mesh_grid = mesh_primitive_grid({ -1,-1,0 }, { 1,-1,0 }, { 1,1,0 }, { -1,1,0 }, 200, 200);

surface.initialize_data_on_gpu(mesh_grid);
surface.material.color = { 0.8f, 0.95f, 1.0f };
surface.material.texture_settings.two_sided=true;

// Set the shader with animated deformation
surface.shader.load(project::path + "shaders/mesh_deformation/mesh_deformation.vert.glsl", project::path + "shaders/mesh_deformation/mesh_deformation.frag.glsl");
```

```cpp
// src/scene.cpp - display_frame
timer.update();

// Send current time as a uniform value to the shader
environment.uniform_generic.uniform_float["time"] = timer.t;

// Standard draw call
draw(surface, environment);
```

The VBOs of `surface` keep the flat grid ($z = 0$) for the whole run. A dense grid is
needed even though the data is flat: the shader can only move the existing vertices, so the
waves are as smooth as the grid is fine. The camera turns around the z axis
(`set_rotation_axis_z`), the vertical axis of the surface.

## 2. Moving the vertices

The vertex shader replaces the height of each vertex by a cosine of its distance $d$ to the
z axis, shifted with time:

$$
p(x, y, t) = \big(x,\; y,\; 0.05 \cos(\omega)\big), \qquad \omega = 20\,d - 3\,t, \qquad d = \sqrt{x^2+y^2}
$$

```glsl
// shaders/mesh_deformation/mesh_deformation.vert.glsl - deformer
vec3 deformer(vec3 p0)
{
	float d = sqrt(p0.x*p0.x+p0.y*p0.y);
	float omega = 20.0*d - 3.0*time;

	vec3 p = vec3(p0.x, p0.y, 0.05*cos(omega) );

	return p;
}
```

The waves have a wavelength of $2\pi/20 \approx 0.31$ and move outward at $3/20 = 0.15$
units per second. (The comment above this function in the shader writes the formula without
the factor 20; the code is what runs.) The result then goes through the usual `model`,
`view` and `projection` matrices, as in the default shader.

## 3. The normal of the deformed surface

The normals stored in the VBO are those of the flat grid, $(0,0,1)$: with them, the waves
would be lit as a flat plane. The shader computes the true normal from the two tangent
vectors of the surface, the partial derivatives of $p$:

$$
\frac{\partial p}{\partial x} = \Big(1,\; 0,\; -0.05 \cdot 20\,\frac{x}{d}\,\sin\omega\Big), \qquad
\frac{\partial p}{\partial y} = \Big(0,\; 1,\; -0.05 \cdot 20\,\frac{y}{d}\,\sin\omega\Big), \qquad
n = \frac{\partial p/\partial x \times \partial p/\partial y}{\|\partial p/\partial x \times \partial p/\partial y\|}
$$

```glsl
// shaders/mesh_deformation/mesh_deformation.vert.glsl - deformer_normal
vec3 dpdx = vec3(1.0, 0.0, -20.0*p0.x/d*0.05*sin(omega) );
vec3 dpdy = vec3(0.0, 1.0, -20.0*p0.y/d*0.05*sin(omega) );
vec3 n = normalize(cross(dpdx,dpdy));
```

then transforms it by the inverse transpose of `model`, like the default shader. The
fragment shader is unchanged: it shades with whatever normal it receives. The formula
divides by $d$, undefined on the z axis; the grid has an even number of vertices per side
(200), so no vertex lies exactly at the center.

This is the general method for any height field $z = h(x, y)$: the normal is proportional to
$(-\partial h/\partial x,\, -\partial h/\partial y,\, 1)$. When the derivatives are hard to
write, a finite difference of `deformer` at two nearby points gives the tangents instead.

## 4. What does not follow the deformation

Since only the GPU knows the deformed positions:

- picking, collisions or any C++ computation on `mesh_grid` see the flat grid;
- every shape that must deform needs this shader. The "Wireframe" checkbox calls
  `draw_wireframe`, which draws `surface` again with its own shader, so the native wireframe
  follows the waves (in the browser, `draw_wireframe` draws nothing, see
  [Display the wireframe](../how-to/display-the-wireframe.md));
- the uniform `time` is also sent to the default shader of the global frame, which does not
  declare it: the console shows the "doesn't use it" warning a few times (see
  [Shaders and uniforms](../understand/shaders-and-uniforms.md#user-uniforms-uniform_generic)).

## Going further

- Add amplitude and frequency sliders: two more `uniform_float` entries and two `uniform float`
  declarations in the vertex shader.
- Replace the circular waves by a sum of two waves with different centers, and update
  `deformer_normal` accordingly (the derivatives add up).
- Color the surface by height: pass $z$ to the fragment shader in the `color` field of the
  fragment struct.
- Do the same deformation on the CPU with `vbo_position.update` (see
  [Update a mesh every frame](../how-to/update-a-mesh-every-frame.md)) and compare the frame
  rate.

## See also

- Understand: [Shaders and uniforms](../understand/shaders-and-uniforms.md)
- How-to: [Send a custom uniform to a shader](../how-to/send-a-custom-uniform.md), [Animate with time](../how-to/animate-with-time.md), [Update a mesh every frame](../how-to/update-a-mesh-every-frame.md)
- Reference: [`mesh_drawable`](../reference/mesh_drawable.md), [`timer_basic`](../reference/timer_basic.md)
