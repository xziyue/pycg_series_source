vertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 fragPos;
out vec3 bNormal;

void main()
{
    fragPos = vec3(model * vec4(aPos, 1.0));
    bNormal = mat3(transpose(inverse(model))) * aNormal;
    gl_Position = projection * view * model * vec4(aPos, 1.0);
}
'''

fragmentShaderSource = r'''
#version 330 core
in vec3 fragPos;
in vec3 bNormal;
out vec4 fragColor;

uniform vec3 objectColor;
uniform vec3 lightColor;
uniform vec3 viewPos;
uniform vec3 lightPos;
uniform float ambientCoef;
uniform float specularCoef;
uniform int specularP;

void main()
{   
    vec3 cNormal = normalize(bNormal);
    vec3 ambient = ambientCoef * lightColor;

    vec3 lightDir = normalize(lightPos - fragPos);
    float diffMul = max(0.0, dot(cNormal, lightDir));
    vec3 diffuse = diffMul * lightColor;

    vec3 viewDir = normalize(viewPos - fragPos);
    vec3 reflectDir = normalize(reflect(-lightDir, cNormal));
    float specMul = pow(max(0.0, dot(viewDir, reflectDir)), specularP);
    vec3 specular = specMul * specularCoef * lightColor;

    vec3 result = (ambient + diffuse + specular) * objectColor;
    fragColor = vec4(result, 1.0);
}
'''


lineVertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec3 aPos;

void main()
{
    gl_Position = vec4(aPos, 1.0);
}

'''

lineGeometryShaderSource = r'''
#version 330 core
layout (lines) in;
layout (triangle_strip, max_vertices=4) out;

out vec3 fragPos;
out vec3 gNormal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform vec3 viewPos;
uniform float lineWidth;

void main(){
    vec3 p1 = gl_in[0].gl_Position.xyz;
    vec3 p2 = gl_in[1].gl_Position.xyz;
    vec3 pDiff = p1 - p2;
    float hlw = lineWidth / 2.0;
    
    vec3 viewDir = viewPos - p2;
    vec3 radDir = normalize(cross(pDiff, viewDir));
    
    vec3 rNormal = mat3(transpose(inverse(model))) * normalize(cross(radDir, pDiff));
    vec3 r1 = p1 - radDir * hlw;
    vec3 r2 = p1 + radDir * hlw;
    vec3 r3 = p2 - radDir * hlw;
    vec3 r4 = p2 + radDir * hlw;
    
    
    gl_Position = projection * view * model * vec4(r1, 1.0);
    gNormal = rNormal;
    fragPos = vec3(model * vec4(r1, 1.0));
    EmitVertex();
    
    gl_Position = projection * view * model * vec4(r2, 1.0);
    gNormal = rNormal;
    fragPos = vec3(model * vec4(r2, 1.0));
    EmitVertex();
    
    gl_Position = projection * view * model * vec4(r3, 1.0);
    gNormal = rNormal;
    fragPos = vec3(model * vec4(r3, 1.0));
    EmitVertex();
    
    gl_Position = projection * view * model * vec4(r4, 1.0);
    gNormal = rNormal;
    fragPos = vec3(model * vec4(r4, 1.0));
    EmitVertex();
    
    EndPrimitive();
}

'''


lineFragmentShaderSource = r'''
#version 330 core
in vec3 fragPos;
in vec3 gNormal;
out vec4 fragColor;

uniform vec3 lineColor;

void main(){

    fragColor = vec4(lineColor, 1.0);
}
'''