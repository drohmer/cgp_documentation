#version 330 core

// Vertex shader of the demo "uniforms": a plane wave computed on the GPU.
// The attributes (location 0..3) differ for every vertex; the uniforms are the same
// for every vertex of the draw call.

layout (location = 0) in vec3 vertex_position;
layout (location = 1) in vec3 vertex_normal;
layout (location = 2) in vec3 vertex_color;
layout (location = 3) in vec2 vertex_uv;

out struct fragment_data {
    vec3 position;
    vec3 normal;
} fragment;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

uniform float time;       // environment.uniform_generic.uniform_float["time"]
uniform float amplitude;  // environment.uniform_generic.uniform_float["amplitude"]

void main()
{
    float k = 8.0;                                  // wave number
    vec3 p = vertex_position;
    p.z += amplitude * sin(k * p.x - 3.0 * time);   // displacement along z
    float dzdx = amplitude * k * cos(k * p.x - 3.0 * time);
    vec3 n = normalize(vec3(-dzdx, 0.0, 1.0));      // normal of the displaced surface

    vec4 position = model * vec4(p, 1.0);
    fragment.position = position.xyz;
    fragment.normal = mat3(model) * n;
    gl_Position = projection * view * position;
}
