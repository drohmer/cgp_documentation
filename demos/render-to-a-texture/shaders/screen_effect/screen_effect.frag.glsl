#version 330 core
in vec2 uv_frag;
uniform sampler2D image_texture;     // the texture of the quad = the first pass
layout(location=0) out vec4 FragColor;

void main()
{
    vec2 d = 1.0 / vec2(textureSize(image_texture, 0));     // size of one pixel
    vec4 laplacian = texture(image_texture, uv_frag + vec2(d.x, 0.0))
                   + texture(image_texture, uv_frag - vec2(d.x, 0.0))
                   + texture(image_texture, uv_frag + vec2(0.0, d.y))
                   + texture(image_texture, uv_frag - vec2(0.0, d.y))
                   - 4.0 * texture(image_texture, uv_frag);
    FragColor = abs(1.0 - laplacian);                        // dark edges on white
}
