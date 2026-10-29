# Color palette of the figures

All SVG figures of content/assets/ (and reference/, primitives/) use the colors below.
Same concept = same color in every figure. The values live in
`tools/figures/palette.py` (dict `P`); the generators import it, and
`recolor.py` applies its text mapping to the hand-drawn SVGs.

Each concept has a light **fill** (background of a box), a **stroke** (border of the box), a
**line** color (arrows, curves, dots) and a darker **text** color (labels and titles written in
the color of the concept).

## Concepts

| concept | fill | stroke | line | text | used for |
|---|---|---|---|---|---|
| cpu | #e3eefb | #6b9bd8 | #4a86d0 | #2b66ad | CPU, main memory, C++ structs (mesh, image_structure, environment) |
| gpu | #fdebd6 | #e0912f | #e07b1a | #a85000 | GPU, video memory, OpenGL objects (mesh_drawable, texture, fbo, program) |
| vbo | #fff7ec | #e0912f | #e07b1a | #a85000 | GPU buffers: VBO, EBO, VAO, per-vertex and per-instance attributes |
| uniform | #eee5f8 | #9c6ade | #9c6ade | #7b48c4 | uniforms and the arrows that send them; purple is used for nothing else |
| code | #dff0dc | #5aa55a | #5aa55a | #2a7330 | code you write: shaders (programmable stages) and the scene functions |
| fixed | #ececec | #999999 | #999999 | #333333 | fixed-function stages of the GPU, library code you do not edit |
| local | #f4f9cf | #a8b04a | #a8b04a | #6f6400 | local space, model matrix M |
| world | #ececec | #999999 | #999999 | #333333 | world space (neutral) |
| camera | #dcf1f3 | #3a9aa5 | #2a8f99 | #1a6b73 | camera space, view matrix V, camera frame, eye, frustum, camera parameters |
| clip | #fbe4ec | #c9567f | #c9567f | #a3305e | clip space and NDC, projection matrix P and its parameters (field_of_view) |
| x / y / z | #fbe3e1 / #dff0dc / #e3eefb | - | #d0605a / #5aa55a / #4a86d0 | #b3261e / #2a7330 / #2b66ad | axes: x red, y green, z blue (also ux, uy, uz, right / up / back) |
| input | #fce4ee | - | #d6407a | #c2185b | user input: cursor position, mouse events |
| error | #fbe3e1 | - | #d9534f | #b3261e | warning, forbidden or missing path (the cross of buffer_update) |
| light | #fdf3dc | - | #e0a030 | #8a5a00 | light source and its frame (cast-shadows) |
| ink | - | - | - | #333333 | main text |
| muted | - | - | #888888 | #666666 | secondary text, guide and leader lines, arrows of a plain flow |

Time has no hue of its own: time axes and timelines are neutral (muted line, ink labels).

**Free accents.** A figure that shows none of the concepts above (a plot, a data layout, a
transform example) may use the cpu blue and the gpu orange as two plain series, with orange for
the highlighted element (timers_timeline, keyframe-interpolation, grid_2D, numarray, affine).
It must not use purple (uniform), teal (camera) or pink (clip) for anything else.
Colors that are content stay as they are: vertex colors (attribute_vs_uniform,
pipeline_summary), image texels (opengl_texture_wrap, image_structure), material colors
(curve_drawable red), the shapes of the scenes (yellow cube, red sphere).

## Contrast

Text colors are checked against white, against the figure card of the sites in dark mode
(#eef1f6, the SVGs stay on a light card) and against the lightest fill of their concept (WCAG
2 relative luminance, threshold 4.5:1 for text, 3:1 for lines and shapes).

| concept | text on #fff | on card #eef1f6 | on own fill | line on #fff |
|---|---|---|---|---|
| cpu | 5.8 | 5.1 | 5.0 | 3.7 |
| gpu | 5.5 | 4.9 | 4.7 | 3.0 |
| vbo | 5.5 | 4.9 | 5.2 | 3.0 |
| uniform | 5.9 | 5.2 | 4.8 | 3.8 |
| code | 5.8 | 5.2 | 4.9 | 3.0 |
| fixed / world | 12.6 | 11.2 | 10.7 | 2.8 (borders only) |
| local | 6.0 | 5.3 | 5.5 | 2.3 (borders only) |
| camera | 6.2 | 5.5 | 5.3 | 3.8 |
| clip | 6.7 | 5.9 | 5.5 | 4.1 |
| x | 6.5 | 5.8 | 5.3 | 3.8 |
| y | 5.8 | 5.2 | 4.9 | 3.0 |
| z | 5.8 | 5.1 | 5.0 | 3.7 |
| input | 5.9 | 5.2 | 4.9 | 4.3 |
| error | 6.5 | 5.8 | 5.3 | 4.0 |
| light | 5.9 | 5.2 | 5.4 | 2.3 (light rays, with dark labels) |
| muted | 5.7 | 5.1 | 4.7 (on #ececec 4.9) | 3.5 |

The mid tones used before 2026-10-29 as text (#4a86d0, #e07b1a, #5aa55a, #9c6ade, #888, ...)
were between 2.5:1 and 3.8:1: they are now line colors only.

## Tools

- `palette.py`: `P` (the table above), `TEXT_MAP` (old mid tone -> text tone of the same
  concept), `LINE_MAP` (near-duplicate line colors -> palette), `write_svg(path, lines)` used
  by the generators of figures/ (it applies `TEXT_MAP` to the text of the output).
- `recolor.py [--check] FILE.svg ...`: applies `TEXT_MAP` to `<text>`, `<tspan>` and the CSS
  rules that only style text, and `LINE_MAP` everywhere; idempotent. Run it on a new
  hand-drawn figure, then check the semantic colors by hand (a box that represents a concept
  takes the fill / stroke of the concept).
- `primitives/render_primitives.py`: axes in the text tone of x / y / z (dark enough over the
  light blue shapes), the points given as parameters in the gpu line / text tone.
