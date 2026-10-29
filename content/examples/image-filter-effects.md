---
title: "Image effects: colors, contours, deformations"
section: Examples
group: Multi-pass rendering
order: 10
local_names: [multipass_structure, multipass_rendering, set_shader_pass_2, start_pass_1, scene_elements, scene_elements_structure, deform_terrain, display, update, terrain, water, tree, cube1, cube2, camel, shader_names, shader_path, uv_frag, FragColor, filter_color, rgb_noise, gold_noise, deformation, floor]
description: Eight post-processing shaders on a small island scene, switched at run time from the GUI - posterization, vignette, film noise, contours, wave and ripple deformations, some animated by a time uniform.
---

# Image effects: colors, contours, deformations

**What it shows**: a small island (sand, sea, a palm tree, a camel and two wooden crates)
rendered through one of eight screen effects, chosen with the GUI buttons. Each effect is a
fragment shader applied to the image of the scene: it can change the colors of a pixel,
combine its neighbors, or read the image at a displaced position. The demo starts with
"contours", which outlines the shapes in red.

<!-- demo: image-filter-effects -->

Concepts combined in this example:

- the two passes of [An image filter on the whole scene](image-filter.md), with the same
  `multipass_structure`;
- a shader of pass 2 that is replaced at run time (`set_shader_pass_2` after a button
  click);
- a `time` uniform sent through `environment.uniform_generic` to the animated effects;
- per-pixel operations (color quantization, a weight that depends on the position on
  screen, noise) and uv deformations.

Source: [`examples/06_multipass/02_image_filter_basic_effects`](https://github.com/drohmer/epita_ani3d_lab_code-2027/tree/main/examples/06_multipass/02_image_filter_basic_effects)
of the public repository *epita_ani3d_lab_code-2027*, run unchanged in the demo above (the
palm tree file and the wood image are reduced in size).

| File | Role |
|---|---|
| `src/scene.hpp`, `src/scene.cpp` | the two passes, the `time` uniform, the buttons that load an effect |
| `src/scene_elements/scene_elements.*` | the island: terrain, water, palm tree, crates, camel |
| `src/multipass_structure/multipass_structure.*` | identical to the [previous example](image-filter.md#1-the-helper-struct) |
| `shaders/screen_effect_<name>/` | one folder per effect; the eight vertex shaders are identical |
| `assets/` | `assets/camel.obj`, `assets/sand.jpg`, `assets/sea.png`, `assets/wood.jpg`, `assets/palm_tree/` (palm tree by E. Puybaret / eTeks and Scopia, CC BY 3.0) |

## 1. The scene

`scene_elements_structure` groups the shapes so that `display_frame` stays short; its
`display` draws them, with their wireframes if the checkbox is set. The terrain is a grid of
100 x 100 vertices raised into a Gaussian bump with a little Perlin noise:

```cpp
// src/scene_elements/scene_elements.cpp - deform_terrain
float d2 = p.x * p.x + p.y * p.y;
float z = exp(-d2 / 4) - 1;
z = z + 0.05f * noise_perlin({ p.x,p.y });
```

The water is a larger flat grid below it (z = -0.8), so the sea shows where the terrain goes
under. The palm tree file is modeled with y up and is turned by $\pi/2$ around x. `cube2`
is a copy of `cube1` (same GPU buffers and texture) that floats on the water: `update`
moves and tilts it with sines and cosines of the time. Every shape but the camel loads a texture image with
`load_and_initialize_texture_2d_on_gpu`.

Unlike the previous example, the global frame is drawn **inside** pass 1: it is filtered
with the rest of the scene. Pass 1 also clears the FBO with the sky color
`environment.background_color`.

## 2. Switching the effect at run time

```cpp
// src/scene.cpp - display_gui
std::vector<std::string> shader_names = {"default", "contours", "convolution", "color1", "color2", "color3", "deformation", "deformation2" };
for (int k = 0; k < shader_names.size(); ++k) {
	bool click_shader = ImGui::Button(shader_names[k].c_str());

	// If click on a shader, load it and set is to the multipass_rendering structure
	if (click_shader) {
		std::string shader_path = project::path + "shaders/screen_effect_" + shader_names[k] + "/screen_effect_" + shader_names[k];
		opengl_shader_structure shader;
		shader.load(shader_path + ".vert.glsl", shader_path + ".frag.glsl");
		multipass_rendering.set_shader_pass_2(shader);
	}
}
```

The folder and file names follow one pattern, so a new effect only needs a new folder and a
new name in the list. The shader is compiled at the click: a syntax error in an effect only
shows when its button is pressed. Each click compiles a new GPU program and the previous one
is not freed, which is harmless for a few clicks.

## 3. A time uniform for the animated effects

```cpp
// src/scene.cpp - initialize, then display_frame
environment.default_expected_uniform = false;
...
timer.update();
environment.uniform_generic.uniform_float["time"] = timer.t;
```

Every `draw` of the scene sends `time`, but only two effects (color3 and deformation2) use
it, and none of the shapes do: `default_expected_uniform = false` turns off the warnings
for the uniforms of the environment that a shader does not use (see
[Shaders and uniforms](../understand/shaders-and-uniforms.md#3-three-levels-of-uniforms)).

## 4. The eight effects

All of them read the image of pass 1 through `image_texture` at the coordinates `uv_frag`
of the pixel, in $[0,1]^2$.

| Button | What the fragment shader does |
|---|---|
| default | copies the color: the scene as without the filter |
| convolution | the Laplacian of the previous example, dark edges on white |
| contours | the same Laplacian $c$, used to mix the image with red: `base*(1.0-c)+c*vec4(1.0,0.0,0.0,0.0)` |
| color1 | posterization: `floor(color * 5.0) / 5.0` keeps 5 levels per channel |
| color2 | vignette: the color fades to black away from the center of the screen |
| color3 | the colors fade to gray away from the center, plus a colored noise that changes with `time` |
| deformation | reads at `uv_frag + offset`, offset along x varying as a cosine of y: vertical waves |
| deformation2 | radial ripples: the offset points away from the center, oscillates with the distance and moves with `time` |

**Weight from the position on screen** (color2, color3). `filter_color` maps the uv
coordinates to $p \in [-1,1]^2$, centered on the screen, and computes the weight
$w = \exp(-(\|p\|/\sigma)^2)$, equal to 1 at the center and decreasing outward. color2 mixes
`w * color + (1.0 - w) * black` ($\sigma = 0.8$); color3 mixes the color with its gray
level $0.33\,(r+g+b)$ instead ($\sigma = 0.5$), then adds $0.2$ times an RGB noise computed
by `gold_noise` from the pixel coordinates and the time.

**Deformation** (deformation, deformation2). These shaders do not change the color they
read, but where they read it:

```glsl
// shaders/screen_effect_deformation/screen_effect_deformation.frag.glsl
vec2 offset = vec2(0.01 * cos(5.0 * 3.14 * uv_frag.y), 0.0);
vec4 color = texture(image_texture, uv_frag+offset);
```

Each row of pixels is shifted horizontally by up to 1% of the width, by an amount that
varies with the height: the straight vertical edges become waves. In deformation2, the
offset is 0.1 times the result of the function `deformation`, $\alpha\,u$, where $u$ is the unit vector from the
center of the screen to the pixel and
$\alpha = (d/\sigma)^2 \cos(2\pi(d/\lambda - f\,t))$ depends on the distance $d$ to the
center: zero at the center, and circular waves that travel with the time.

## Going further

- Combine two effects in one shader, for instance the vignette of color2 on the posterized
  colors of color1 - or keep them separate and chain them with a second FBO:
  [A chain of two image filters](image-filters-chain.md).
- Add a slider for the number of levels of color1, sent as a uniform like `time`.
- Write a pixelation effect: round `uv_frag` to a coarse grid before reading the texture.

## See also

- Examples: [An image filter on the whole scene](image-filter.md), [A chain of two image filters](image-filters-chain.md)
- How-to: [Render the scene to a texture and filter it](../how-to/render-to-a-texture.md), [Send a custom uniform to a shader](../how-to/send-a-custom-uniform.md), [Apply a texture image](../how-to/apply-a-texture.md)
- Understand: [Shaders and uniforms](../understand/shaders-and-uniforms.md)
- Reference: [`opengl_fbo_structure`](../reference/opengl_fbo_structure.md), [`opengl_shader_structure`](../reference/opengl_shader_structure.md), [`uniform_generic_structure`](../reference/uniform_generic_structure.md)
