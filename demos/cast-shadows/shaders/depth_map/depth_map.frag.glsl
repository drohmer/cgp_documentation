#version 330 core
layout(location = 0) out float fragment_depth;
void main() { fragment_depth = gl_FragCoord.z; }
