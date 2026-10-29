---
title: CGP documentation
description: CGP (Computer Graphics Programming) is a lightweight C++ library for learning and prototyping 3D graphics with OpenGL.
---

# CGP - Computer Graphics Programming

CGP is a lightweight C++ library to learn and prototype interactive 3D graphics with OpenGL:
write a few lines of C++, see your shapes move on screen, and understand what the GPU does with
them. It is developed alongside the course *CSC_43043 - Introduction to Computer Graphics*
(Ecole polytechnique) and is free to use (MIT license).

**[Get started](get-started/install.md)** - **[See the examples](#examples)** -
**[Browse the reference](reference/index.md)** - **[CGP on GitHub](https://github.com/drohmer/cgp-2027)**

<!-- demo: environment-map -->

Drag with the mouse to turn around the shape: a torus reflects a sky box, with a few lines of
shader code ([the example](examples/environment-map.md) explains how).

## The spirit of CGP

- **Close to OpenGL, without the boilerplate.** CGP takes care of the window, the buffers and
  the shader programs, but keeps the steps of the graphics pipeline visible: a `mesh` on the CPU
  is copied explicitly to a `mesh_drawable` on the GPU, uniforms have names you can find in the
  shaders, and plain OpenGL calls still work next to CGP.
- **Readable code you can step into.** The library is plain C++ source compiled with your
  project, mostly free functions on simple structs (`norm(v)`, `draw(shape, environment)`), and
  the default shaders are short GLSL files you can read and copy.
- **One scene structure for every program.** Each project starts from the same template:
  `initialize()` once, `display_frame()` at every frame, `display_gui()` for the sliders. The
  course labs and the examples of this documentation all follow it.
- **Native and web.** The same program compiles for Linux, macOS and Windows, and for the
  browser (WebGL with Emscripten): every interactive demo of this documentation is a CGP
  program. ImGui, the image and OBJ loaders come with the library; only GLFW is installed
  separately on Linux and macOS ([Install and compile](get-started/install.md)).

## What it gives you

- **Math**: vectors and matrices (`vec3`, `mat4`), rotations, frames and affine transforms
  ([Rotations, frames and affine transforms](understand/transformations.md)).
- **Data**: dynamic arrays and 2D / 3D grids (`numarray`, `grid_2D`, `grid_3D`), images,
  random numbers and Perlin noise.
- **Shapes**: meshes with primitives (sphere, cube, cylinder, grid, torus...), OBJ loading with
  materials, implicit surfaces with marching cubes, curves and trajectories.
- **Rendering**: drawables for meshes, curves and triangle soups, Phong materials, textures and
  cube maps, your own shaders and uniforms, instancing, frame buffers for multi-pass effects
  and shadow maps.
- **Scene and interaction**: articulated hierarchies, orbit, first-person and fly cameras,
  perspective and orthographic projections, mouse and keyboard, picking, timers, and an ImGui
  window for the GUI.

## Examples

Complete programs, each explained step by step with its live demo. Click on an image to open
the example.

<!-- gallery: examples -->

## Code on GitHub

| Repository | What you find there |
|---|---|
| [drohmer/cgp-2027](https://github.com/drohmer/cgp-2027) | The CGP library and the project template: clone it to start (see [Install and compile](get-started/install.md)). |
| [drohmer/epita_ani3d_lab_code-2027](https://github.com/drohmer/epita_ani3d_lab_code-2027/tree/main/examples) | The examples of this documentation (folder `examples/`), each a complete project. |
| [drohmer/csc43043ep-lab-code](https://github.com/drohmer/csc43043ep-lab-code) | The labs of the course CSC_43043 (public version, without the solutions). |

## Where to start

The sections below follow the order of the menu.

- **Get started** - [install and compile](get-started/install.md), then
  [tour your first scene](get-started/first-scene.md). Something goes wrong?
  [Troubleshooting and error messages](get-started/troubleshooting.md).
- **Understand** - how a 3D scene is built and rendered: the structure of a program, from C++
  data to the GPU, shaders and uniform variables, camera models and their matrices, rotations
  and affine transforms, hierarchies of shapes, time and animation, mouse and keyboard.
  Start with [Scene structure](understand/scene-structure.md). An unknown word? See the
  [Glossary](understand/glossary.md).
- **How-to** - short recipes for common tasks, grouped by topic: shapes and meshes,
  appearance and textures, loading files, animation and interaction, shaders and rendering.
  Start with [Draw a mesh with a camera](how-to/draw-a-mesh.md), or see [all the recipes](how-to.md).
- **Reference** - every type with its fields, its methods and the functions that apply to it,
  and, next to the types of each theme, the [pages of functions](reference/index.md) that take none of them
  (random numbers, marching cubes, OBJ files, strings and files...).
  CGP is mostly made of free functions (`norm(v)`, `draw(drawable, environment)`), so each type
  page lists what you can *do* with it: for instance [`vec3`](reference/vec3.md).

## Common tasks

| I want to... | Recipe |
|---|---|
| draw a sphere, a cube, a cylinder... | [Create basic shapes](how-to/create-basic-shapes.md) |
| move, rotate or scale a shape | [Move, rotate and scale a shape](how-to/transform-a-shape.md) |
| change the color of a shape, make it transparent | [Change the color of a shape](how-to/change-the-color.md) |
| put an image on a shape | [Apply a texture image](how-to/apply-a-texture.md) |
| load a 3D model | [Load a 3D model from an OBJ file](how-to/load-an-obj-file.md) |
| animate a shape | [Animate a shape with time](how-to/animate-with-time.md) |
| add a slider or a checkbox | [Add GUI controls](how-to/add-gui-controls.md) |
| click on an object and move it | [Select and drag objects with the mouse](how-to/select-and-drag-with-the-mouse.md) |
| write my own shader | [Send a custom uniform to a shader](how-to/send-a-custom-uniform.md) |
| understand an error message | [Troubleshooting and error messages](get-started/troubleshooting.md) |

Something else? Use the search box at the top of the page: it covers the guides and every
function of the reference.

## A first look

```cpp
mesh_drawable sphere;
sphere.initialize_data_on_gpu(mesh_primitive_sphere(0.25f)); // once
draw(sphere, environment);                                   // every frame
```
