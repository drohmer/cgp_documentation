#version 330 core

// Fragment shader of the demo "uniforms": diffuse lighting with a uniform color.

in struct fragment_data {
    vec3 position;
    vec3 normal;
} fragment;

layout(location=0) out vec4 FragColor;

uniform vec3 light;       // environment.light
uniform vec3 wave_color;  // environment.uniform_generic.uniform_vec3["wave_color"]

void main()
{
    vec3 N = normalize(fragment.normal);
    vec3 L = normalize(light - fragment.position);
    float diffuse = abs(dot(N, L));                 // lit from both sides
    FragColor = vec4((0.25 + 0.75 * diffuse) * wave_color, 1.0);
}
