rayTracingVertexShaderSource = r'''
#version 330 core
layout(location = 0) in vec3 aPos;

void main(){
    gl_Position = vec4(aPos, 1.0);
}
'''

rayTracingFragmentShaderSource = r'''
#version 330 core

out vec4 fragColor;

uniform vec3 backColor; 
uniform vec3 ambientColor;

uniform vec2 winSize;
uniform vec3 c_c;
uniform vec3 c_p;
uniform vec3 o_c;
uniform vec3 o_p;
uniform vec3 x_c;
uniform vec3 y_c;
uniform vec3 x_p;
uniform vec3 y_p;

uniform sampler2D sample;

void main(){
    vec3 l = gl_FragCoord.xyz / vec3(winSize.xy, 1.0);

    vec3 n_c = normalize(cross(y_c, x_c));
    vec3 n_p = normalize(cross(y_p, x_p));
    
    vec3 l3 = l.x * x_c + l.y * y_c + c_c;
    vec3 d = normalize(l3 - o_c);
    
    float b = 2.0 * dot(d, o_c);
    float c = dot(o_c, o_c) - 1.0;
    
    float delta = b * b - 4.0 * c;
    if(delta <= 1.0e-3){
        // no intersection
        discard;
    }
    
    float s1 = (-b - sqrt(delta)) / 2.0;
    float s2 = (-b + sqrt(delta)) / 2.0;
    vec3 v1 = o_c + s1 * d;
    vec3 v2 = o_c + s2 * d;
    
    if(v1.z >= 0.0 && v2.z >= 0.0){
        // both intersects with z>0 hemisphere
        discard;
    }
    if(v1.z < 0.0 && v2.z < 0.0){
        // sight blocked by the back of the screen
        fragColor = vec4(backColor, 1.0);
        return;
    }
    
    if(v2.z >= 0.0){
        // eye is inside the sphere, but looking at z>0 direction
        discard;
    }
    
    vec3 e = normalize(o_p - v2);
    vec3 p_p = x_p + c_p;
    float t = (dot(p_p, n_p) - dot(v2, n_p))/dot(e, n_p);
    vec3 w = v2 + t * e;
    
    mat3 projPlaneMat;
    projPlaneMat[0] = x_p;
    projPlaneMat[1] = y_p;
    projPlaneMat[2] = n_p;
    
    vec3 l_ = inverse(projPlaneMat) * (w - c_p);
    
    if(l_.x >= 0.0 && l_.x <= 1.0 && l_.y >= 0.0 && l_.y <= 1.0){
        fragColor = texture(sample, vec2(l_.x, 1.0-l_.y));
    }else{
        fragColor = vec4(ambientColor, 1.0);
    }
    
}

'''