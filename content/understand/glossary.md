---
title: Glossary
section: Understand
order: 10
description: Short definitions of the graphics and CGP terms used in this documentation - shader, uniform, attribute, VBO, VAO, EBO, texture, uv, texel, mipmap, depth buffer, clip space, NDC, affine transform, quaternion, frame, drawable, environment - with a link to the page that explains each one.
---

# Glossary

One or two sentences per term, and the page that explains it in full. The terms are grouped
by topic; use the search or the "On this page" menu to find one.

## The GPU and its programs

### Shader

A small program written in GLSL that runs on the GPU, in parallel, for every vertex or every
pixel of a draw call. CGP draws each shape with a pair of shaders, a vertex shader and a
fragment shader, held by an `opengl_shader_structure`.
More: [Shaders and uniforms](shaders-and-uniforms.md).

### Vertex shader

The shader that runs once per vertex: it reads the attributes of the vertex and computes its
position on the screen (`gl_Position`), usually as projection x view x model x position.
More: [Shaders and uniforms](shaders-and-uniforms.md#1-the-default-vertex-shader).

### Fragment shader

The shader that runs once per *fragment*, a pixel covered by a triangle: it computes the color
of this pixel (lighting, texture, transparency).
More: [Shaders and uniforms](shaders-and-uniforms.md#2-the-default-fragment-shader).

### Rasterization

The fixed step of the GPU between the two shaders: it assembles the triangles, finds the
pixels each one covers, and interpolates the outputs of the vertex shader (normal, color, uv)
at each of these pixels.
More: [Shaders and uniforms](shaders-and-uniforms.md).

### Attribute

A per-vertex input of the vertex shader (GLSL qualifier **in**): position, normal, color, uv. Each
vertex has its own value, read from a VBO.
More: [From CPU to GPU](cpu-to-gpu.md).

### Uniform

A shader variable (GLSL qualifier **uniform**) whose value is set from C++ and is the same for
every vertex and every pixel of a draw call: the model, view and projection matrices, the
light position, the material color. `draw` sends them before each draw call.
More: [Shaders and uniforms](shaders-and-uniforms.md#3-three-levels-of-uniforms).

### Phong shading

The lighting model of the default CGP shader: an ambient term, a diffuse term (brighter where
the surface faces the light) and a specular highlight, weighted by the coefficients of
`material.phong`.
More: [Shaders and uniforms](shaders-and-uniforms.md#2-the-default-fragment-shader),
[Change the color of a shape](../how-to/change-the-color.md).

## Buffers on the GPU

### VBO

*Vertex Buffer Object*: an array stored in the GPU memory, one per attribute (positions,
normals...). `initialize_data_on_gpu` creates them by copying the arrays of a `mesh`.
More: [From CPU to GPU](cpu-to-gpu.md#2-mesh_drawable-buffers-on-the-gpu).

### EBO

*Element Buffer Object*: the GPU array of the triangle indices (three vertex indices per
triangle), copied from `mesh::connectivity`.
More: [From CPU to GPU](cpu-to-gpu.md#2-mesh_drawable-buffers-on-the-gpu).

### VAO

*Vertex Array Object*: the GPU object that records which VBO feeds which input of the vertex
shader (position at location 0, normal at 1, color at 2, uv at 3). Drawing a shape binds its
VAO.
More: [From CPU to GPU](cpu-to-gpu.md#3-initialize_data_on_gpu-the-copy).

### Depth buffer

An image, of the size of the window, that stores for every pixel the depth of the closest
surface drawn so far. With the *depth test* (enabled by the application at every frame), a
fragment farther than this value is discarded, so that near objects hide far ones whatever
the drawing order.
More: [Scene structure](scene-structure.md#4-one-frame-step-by-step),
[Draw transparent objects](../how-to/draw-transparent-objects.md).

### Framebuffer

The set of images a draw call writes into: by default the window (color and depth buffers);
an `opengl_fbo_structure` (FBO) is an off-screen framebuffer whose color or depth is a texture.
More: [Render the scene to a texture](../how-to/render-to-a-texture.md),
[Cast shadows](../how-to/cast-shadows.md).

### Swap buffers

The window has two color images: the GPU draws the next frame in the hidden one, and swapping
the buffers shows it at once, at the end of every frame, so the reader never sees a half-drawn
image.
More: [Scene structure](scene-structure.md#4-one-frame-step-by-step).

## Images and textures

### Texture

An image stored in the GPU memory and read by a shader, for instance to color a surface. In CGP
it is an `opengl_texture_image_structure`, set in the `texture` field of a drawable.
More: [Apply a texture image](../how-to/apply-a-texture.md),
[From CPU to GPU](cpu-to-gpu.md#5-textures-from-an-image-on-the-cpu-to-a-texture-on-the-gpu).

### UV coordinates

Two numbers (u, v), stored per vertex in `mesh::uv`, that give the point of the texture image
attached to this vertex: (0,0) and (1,1) are two opposite corners of the image. Between the
vertices they are interpolated.
More: [Apply a texture image](../how-to/apply-a-texture.md).

### Texel

A pixel of a texture image. One pixel of the screen may cover a fraction of a texel (close
view, the texture is magnified) or many texels (far view).
More: [Apply a texture image](../how-to/apply-a-texture.md).

### Mipmap

A series of smaller copies of a texture (half size, quarter size...), computed once when the
texture is sent to the GPU; a far surface reads the small copy, which avoids flickering
patterns. CGP builds them by default (`is_mipmap = true` when a texture is loaded).
More: [From CPU to GPU](cpu-to-gpu.md#5-textures-from-an-image-on-the-cpu-to-a-texture-on-the-gpu).

## Coordinates and transforms

### Homogeneous coordinates

A 3D point (x,y,z) written with a fourth coordinate, (x,y,z,1), and a direction written
(x,y,z,0), so that translations and perspective are 4x4 matrix products.
More: [Camera and matrices](camera-and-matrices.md).

### Model, view and projection matrices

The three 4x4 matrices applied to every vertex: the *model* matrix places the shape in the
world, the *view* matrix expresses the world in the camera frame, the *projection* matrix
applies the perspective.
More: [Camera and matrices](camera-and-matrices.md).

### Clip space

The 4D homogeneous coordinates (x,y,z,w) written by the vertex shader in `gl_Position`, after
the projection matrix. The GPU clips the triangles against the visible volume in this space.
More: [Camera and matrices](camera-and-matrices.md).

### NDC

*Normalized Device Coordinates*: the clip-space point divided by its w, (x/w, y/w, z/w). The
visible points are in the cube [-1,1]^3; x and y are then mapped to the pixels of the window.
The mouse position of CGP uses the same [-1,1] range.
More: [Camera and matrices](camera-and-matrices.md#3-projection-matrix-from-3d-to-the-screen).

### Affine transform

A transform made of a linear part (rotation, scaling) and a translation: `p -> R p + t`.
CGP has three of them, from the most to the least constrained: `affine_rt` (rotation and
translation), `affine_rts` (with a uniform scaling) and `affine` (with a scaling per axis).
More: [Rotations, frames and affine transforms](transformations.md).

### Frame

An origin and three orthonormal axes, for instance the position and orientation of a camera
or of a part of a character. In CGP, `frame` stores it as a rotation and a translation.
More: [Rotations, frames and affine transforms](transformations.md#2-frames).

### Quaternion

Four numbers (x, y, z, w) of unit norm that encode a 3D rotation; they are cheap to compose
and to interpolate. `rotation_transform` stores a `quaternion`.
More: [Rotations, frames and affine transforms](transformations.md#quaternions).

### Euler angles

A rotation written as successive angles around fixed axes (yaw and pitch for a camera). The
*euler* camera controllers of CGP use them, which keeps the horizon horizontal.
More: [Mouse, keyboard and camera controllers](interaction.md#3-camera-controllers).

## CGP and the scene

### Mesh

A shape stored on the CPU, in a `mesh`: arrays of per-vertex data (position, normal, color,
uv) and the list of triangles (`connectivity`). You can read and modify it in C++.
More: [From CPU to GPU](cpu-to-gpu.md#1-mesh-data-on-the-cpu).

### Drawable

A shape ready to be drawn by the GPU, such as a `mesh_drawable`: the ids of its GPU buffers,
its shader, its texture, and the uniforms set in C++ (`model`, `material`). It is created once
from a mesh with `initialize_data_on_gpu` and drawn at every frame with
`draw(drawable, environment)`.
More: [From CPU to GPU](cpu-to-gpu.md), [Draw a mesh with a camera](../how-to/draw-a-mesh.md).

### Environment

The data shared by all the shapes of a frame, passed to every `draw` call: the view and
projection matrices of the camera, the light position, and your own extra uniforms. In the
template it is the member `environment` of the scene, an `environment_structure`.
More: [Scene structure](scene-structure.md#3-the-environment).

### Camera controller

The object that turns mouse drags and keys into camera motion (orbit, first person, fly
mode). The scene copies its view matrix into the environment at every frame.
More: [Mouse, keyboard and camera controllers](interaction.md#3-camera-controllers).

### ImGui

*Dear ImGui*, the library of the GUI window (sliders, checkboxes, buttons) of every CGP
program. Its widgets are created at every frame in `display_gui()`.
More: [Add GUI controls](../how-to/add-gui-controls.md).
