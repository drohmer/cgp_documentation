#version 330 core
layout (location = 0) in vec3 vertex_position;
uniform mat4 model;
uniform mat4 view_light;
uniform mat4 projection_light;

void main()
{
    gl_Position = projection_light * view_light * model * vec4(vertex_position, 1.0);
}
