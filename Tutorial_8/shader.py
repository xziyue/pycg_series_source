waveVertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec2 loc;

void main()
{
    gl_Position = vec4(loc.x, loc.y, 0.0, 1.0);
}
'''

waveFragmentShaderSource = r'''
#version 330 core
uniform vec3 waveColor;
out vec4 fragColor;

void main()
{   
    fragColor = vec4(waveColor.xyz, 1.0);
}
'''