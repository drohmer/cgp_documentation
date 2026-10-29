---
title: Use a newer version of OpenGL (4.x)
section: How-to
group: Shaders and rendering
order: 26
local_names: [load_compute_shader, on_opengl_message, compute_program, surface, position, normal, vertex_count, Positions, Normals, gl_GlobalInvocationID]
description: Switch CGP from OpenGL 3.3 to 4.1, 4.3 or 4.6 with one compile definition, check the version obtained, then use OpenGL 4.3 - a compute shader that moves the vertices of a mesh_drawable on the GPU, and the debug messages of the driver.
---

# Use a newer version of OpenGL (4.x)

**Goal**: build CGP for OpenGL 4.3 (or 4.1, 4.6) instead of 3.3, then use two features of
OpenGL 4.3 in a scene: a **compute shader** that animates the vertices of a `mesh_drawable`
directly in its GPU buffers, and the **debug messages** of the driver, which explain an
OpenGL error in plain words.

> **Starting point**: the default project template (`src/scene.hpp`, `src/scene.cpp`, see
> [Your first scene](../get-started/first-scene.md)). It already declares the shapes `sphere`
> and `cylinder`, a `timer`, and the members `camera_control`, `environment` and `gui`: reuse
> them, do not declare them again. The first comment of each code block says in which file
> and where its lines go: *add* means insert them, *replace* means replace the whole function by the one shown.

This page runs only in the native program: the web version (Emscripten) always uses WebGL 2,
which has neither compute shaders nor debug messages. On macOS, OpenGL stops at 4.1: the
examples below need Windows or Linux.

## 1. Choose the version

CGP targets **OpenGL 3.3** (core profile) by default: it runs on every computer of the last
fifteen years, on macOS, and its shaders are converted automatically for the web. Another
version is chosen by one compile definition, in *CMakeLists.txt* (also used by Visual Studio
and the CMake presets):

```cmake
target_compile_definitions(${PROJECT_NAME} PRIVATE
    CGP_OPENGL_4_3                # instead of CGP_OPENGL_3_3
    ...
```

or in the *Makefile*:

```make
DEFINES     += CGP_OPENGL_4_3                  # instead of CGP_OPENGL_3_3
```

| Definition | Version | When to use it |
|---|---|---|
| `CGP_OPENGL_3_3` | 3.3 (default) | everywhere, and the code you also build for the web |
| `CGP_OPENGL_4_1` | 4.1 | the most recent version on macOS, which stops there (tessellation shaders, from 4.0) |
| `CGP_OPENGL_4_3` | 4.3 | compute shaders, shader storage buffers, debug messages of the driver |
| `CGP_OPENGL_4_6` | 4.6 | the latest version, on Windows and Linux |

The definition does two things:

- CGP loads the OpenGL functions of this version (the matching GLAD loader of
  *cgp/third_party/glad/*): the functions added after 3.3, such as `glDispatchCompute`, are
  declared and loaded only with a 4.x definition;
- the window asks the driver for a context of this version (core profile). If the driver
  cannot provide it, the program stops when it creates the window (see
  [Troubleshooting](../get-started/troubleshooting.md)).

Then **rebuild the whole project**: delete the *build/* folder (or run `make clean`), since
every file of CGP is compiled with this definition. At start-up, the program prints the
version of the context it obtained (lines `[VERSION]` and `[GLSL VERSION]`), for instance with
`CGP_OPENGL_4_3` on a recent NVIDIA card:

```text
[VERSION]     : 4.3.0 NVIDIA 595.71.05
```

The shaders keep their own version line: the default shaders, written
`#version 330 core`, still work in a 4.x context; write `#version 430 core` (or `460 core`)
at the top of a shader that uses a newer GLSL.

## 2. Check the version in the program

GLAD sets one flag per version that the context supports. A program that needs OpenGL 4.3 can
stop with a clear message rather than crash on the first missing function:

```cpp
// scene.cpp - add at the end of initialize()
if (!GLAD_GL_VERSION_4_3)
    error_cgp("This program needs OpenGL 4.3: use CGP_OPENGL_4_3 in CMakeLists.txt or the Makefile.");
```

`GLAD_GL_VERSION_4_3` exists only with the definitions `CGP_OPENGL_4_3` and `CGP_OPENGL_4_6`:
with `CGP_OPENGL_3_3`, this line does not compile, which is also a clear message.

## 3. A compute shader that moves the vertices on the GPU

A compute shader is a program run on the GPU outside the drawing pipeline: no vertex, no pixel,
just many invocations of a function that read and write buffers. Here it computes a wave on a
grid, writing the new positions and normals straight into the VBOs of a `mesh_drawable`. The
CPU never sees the vertices: compare with
[Update a mesh at every frame](update-a-mesh-every-frame.md), where the CPU computes them and
sends them with `vbo_position.update` at every frame.

### The shader

```glsl
// shaders/wave/wave.comp.glsl
#version 430 core

// One invocation per vertex, by groups of 64
layout(local_size_x = 64) in;

// The VBOs of the mesh_drawable, read as arrays of floats (3 per vertex): in a std430
// block, an array of vec3 would have a stride of 16 bytes, while a VBO of CGP is packed
// (12 bytes per vec3)
layout(std430, binding = 0) buffer Positions { float position[]; };
layout(std430, binding = 1) buffer Normals { float normal[]; };

uniform float time;        // seconds
uniform int vertex_count;  // number of vertices of the grid

void main()
{
    uint k = gl_GlobalInvocationID.x;
    if (k >= uint(vertex_count))
        return;                      // the last group may be incomplete

    // height of a circular wave around the z axis
    float x = position[3*k];
    float y = position[3*k+1];
    float d = sqrt(x*x + y*y);
    float w = 20.0*d - 3.0*time;
    position[3*k+2] = 0.05*cos(w);

    // normal of the surface z = h(d): (-dh/dx, -dh/dy, 1), normalized
    float dh = -0.05*20.0*sin(w);
    vec2 u = d > 1e-6 ? vec2(x, y)/d : vec2(0.0);
    vec3 n = normalize(vec3(-dh*u, 1.0));
    normal[3*k]   = n.x;
    normal[3*k+1] = n.y;
    normal[3*k+2] = n.z;
}
```

Two points specific to compute shaders:

- **The work is split into groups.** `local_size_x = 64` makes groups of 64 invocations; the
  C++ code launches enough groups to cover every vertex, so the last group may go past the
  end: the test on `vertex_count` stops it.
- **The memory layout of the buffers.** A `float position[]` reads the VBO exactly as CGP
  wrote it (x, y, z, x, y, z...). An array of `vec3` would not: in a `std430` block, each
  `vec3` takes 16 bytes.

### Compile it

`opengl_shader_structure::load` compiles a vertex and a fragment shader; a compute shader is a
program of its own, compiled with three OpenGL calls:

```cpp
// scene.cpp - add before initialize()
// Compile a compute shader file into a GPU program (OpenGL 4.3)
static GLuint load_compute_shader(std::string const& filename)
{
	std::string const source = read_text_file(filename);
	char const* text = source.c_str();
	GLuint const shader = glCreateShader(GL_COMPUTE_SHADER);
	glShaderSource(shader, 1, &text, nullptr);
	glCompileShader(shader);

	GLint ok = 0;
	glGetShaderiv(shader, GL_COMPILE_STATUS, &ok);
	if (!ok) {
		char log[2048];
		glGetShaderInfoLog(shader, 2048, nullptr, log);
		std::cout << "Error in the compute shader " << filename << ":\n" << log << std::endl;
	}

	GLuint const program = glCreateProgram();
	glAttachShader(program, shader);
	glLinkProgram(program);
	glDeleteShader(shader);   // the program keeps it
	return program;
}
```

### Create the grid and the program (once)

```cpp
// scene.hpp - add in scene_structure
mesh_drawable surface;       // a grid whose vertices are moved by the compute shader
GLuint compute_program = 0;  // the compute shader, as an OpenGL program
```

```cpp
// scene.cpp - add at the end of initialize()
surface.initialize_data_on_gpu(mesh_primitive_grid({-1,-1,0}, {1,-1,0}, {1,1,0}, {-1,1,0}, 200, 200));
surface.material.color = {0.3f, 0.6f, 0.9f};
compute_program = load_compute_shader(project::path + "shaders/wave/wave.comp.glsl");
```

### Run it, then draw (every frame)

```cpp
// scene.cpp - add in display_frame(), before timer.update()
// 1. the compute shader writes the positions and normals into the VBOs of the drawable
int const vertex_count = int(surface.vbo_position.size);
glUseProgram(compute_program);
glUniform1f(glGetUniformLocation(compute_program, "time"), timer.t);
glUniform1i(glGetUniformLocation(compute_program, "vertex_count"), vertex_count);
glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, surface.vbo_position.id);
glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, surface.vbo_normal.id);
glDispatchCompute((vertex_count + 63) / 64, 1, 1);   // enough groups of 64 for every vertex
glMemoryBarrier(GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT);  // the draw below waits for the writes
glUseProgram(0);

// 2. the drawable is drawn as usual: its VBOs already hold the new shape
draw(surface, environment);
```

- `glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, ...)` connects a buffer to the block
  declared with `binding = 0` in the shader. The VBO of CGP is an ordinary OpenGL buffer:
  `surface.vbo_position.id` is its id, and no copy is made.
- `glMemoryBarrier` matters: without it, the draw may read the VBOs while the compute shader
  is still writing them, and the surface flickers.
- The two VBOs are now owned by the GPU: the `mesh` on the CPU does not change, and
  `vbo_position.update` would overwrite the work of the shader.

## 4. Debug messages of the driver

With OpenGL 4.3, the driver can explain each error in a sentence, at the line that made it.
CGP already asks for a debug context when it creates the window; register a function that
prints the messages:

```cpp
// scene.cpp - add before initialize()
// Called by the driver for every message (OpenGL 4.3): errors, warnings, performance notes
static void APIENTRY on_opengl_message(GLenum, GLenum type, GLuint, GLenum severity, GLsizei,
                                       GLchar const* message, void const*)
{
	if (severity == GL_DEBUG_SEVERITY_NOTIFICATION)
		return;   // informative messages, frequent
	std::cout << (type == GL_DEBUG_TYPE_ERROR ? "[OpenGL error] " : "[OpenGL] ") << message << std::endl;
}
```

```cpp
// scene.cpp - add at the end of initialize()
glEnable(GL_DEBUG_OUTPUT);
glEnable(GL_DEBUG_OUTPUT_SYNCHRONOUS);   // the message comes during the faulty call (debugger)
glDebugMessageCallback(on_opengl_message, nullptr);
```

A call on a buffer id that was never created, for instance, prints:

```text
[OpenGL error] GL_INVALID_OPERATION error generated. Buffer name does not refer to an buffer object generated by OpenGL.
```

where the error check of CGP (`opengl_check`, see
[Troubleshooting](../get-started/troubleshooting.md)) only gives the name of the error
(`GL_INVALID_OPERATION`) and the line of CGP that detected it. With
`GL_DEBUG_OUTPUT_SYNCHRONOUS`, a breakpoint in `on_opengl_message` stops on the line of C++
that made the error.

## Common pitfalls

- **`glDispatchCompute` was not declared in this scope**: the project is still built with
  `CGP_OPENGL_3_3`, or not rebuilt from scratch after the change.
- **The window does not open, "Failed to create GLFW Window"**: the driver does not provide
  the version asked (macOS above 4.1, an old driver, a virtual machine). Choose a lower version.
- **The surface does not move, or moves by bands**: the binding numbers of the C++ code and of
  the shader differ, or the shader uses `vec3 position[]` (stride of 16 bytes).
- **The surface flickers**: the `glMemoryBarrier` is missing.

## Variations

- Particles: store positions and velocities in two buffers, integrate them in the compute
  shader at every frame, and draw them with instancing (see
  [Draw thousands of copies with instancing](draw-many-instances.md)).
- Tessellation (OpenGL 4.0, also on macOS with `CGP_OPENGL_4_1`): a tessellation shader
  subdivides the triangles on the GPU. Its program is built with OpenGL calls, as the compute
  shader above, with four stages; set the size of a patch with
  `glPatchParameteri(GL_PATCH_VERTICES, 3)` and draw with `draw(drawable, environment, 1, true,
  uniform_generic_structure(), GL_PATCHES)`, the last argument being the OpenGL primitive.

## See also

- How-to: [Update a mesh at every frame](update-a-mesh-every-frame.md) (vertices moved on the CPU), [Send a custom uniform to a shader](send-a-custom-uniform.md)
- Understand: [From CPU to GPU](../understand/cpu-to-gpu.md), [Shaders and uniforms](../understand/shaders-and-uniforms.md)
- Get started: [Install and compile](../get-started/install.md)
- Reference: [`opengl_vbo_structure`](../reference/opengl_vbo_structure.md), [`mesh_drawable`](../reference/mesh_drawable.md)
