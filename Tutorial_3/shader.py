frameVertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec3 aPos;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 fragPos;
out vec3 bNormal;

void main()
{
    vec3 aNormal = vec3(0.0, 0.0, 1.0); // using a fixed normal
    fragPos = vec3(model * vec4(aPos, 1.0));
    bNormal = mat3(transpose(inverse(model))) * aNormal;
    gl_Position = projection * view * model * vec4(aPos, 1.0);
}
'''

frameFragmentShaderSource = r'''
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

textureVertexShaderSource = r'''
#version 330 core
layout (location = 0) in vec3 aVec;
layout (location = 1) in vec2 aTexPos;
out vec2 bTexPos;

uniform mat4 projection;
uniform mat4 model;
uniform mat4 view;

void main(){
    gl_Position = projection * view * model * vec4(aVec, 1.0);
    bTexPos = aTexPos;
}  
'''

textureFragmentShaderSource = r'''
#version 330 core
in vec2 bTexPos;
out vec4 color;

uniform sampler2D textureSample;
uniform vec2 textureSize;

void main(){
    vec4 sampled = texture(textureSample, bTexPos);
    color = sampled;
}  
'''


textureBicubicFragmentShaderSource = r'''

#version 330 core
in vec2 bTexPos;
out vec4 color;

uniform sampler2D textureSample;
uniform vec2 textureSize;

// source: https://www.codeproject.com/Articles/236394/Bi-Cubic-and-Bi-Linear-Interpolation-with-GLSL
float Triangular( float f )
{
	f = f / 2.0;
	if( f < 0.0 )
	{
		return ( f + 1.0 );
	}
	else
	{
		return ( 1.0 - f );
	}
	return 0.0;
}

vec4 BiCubic( sampler2D textureSampler, vec2 TexCoord )
{
    float fWidth = textureSize[0];
    float fHeight = textureSize[1];
    float texelSizeX = 1.0 / fWidth; //size of one texel 
    float texelSizeY = 1.0 / fHeight; //size of one texel 
    vec4 nSum = vec4( 0.0, 0.0, 0.0, 0.0 );
    vec4 nDenom = vec4( 0.0, 0.0, 0.0, 0.0 );
    float a = fract( TexCoord.x * fWidth ); // get the decimal part
    float b = fract( TexCoord.y * fHeight ); // get the decimal part
    for( int m = -1; m <=2; m++ )
    {
        for( int n =-1; n<= 2; n++)
        {
			vec4 vecData = texture2D(textureSampler, 
                               TexCoord + vec2(texelSizeX * float( m ), 
					texelSizeY * float( n )));
			float f  = Triangular( float( m ) - a );
			vec4 vecCooef1 = vec4( f,f,f,f );
			float f1 = Triangular ( -( float( n ) - b ) );
			vec4 vecCoeef2 = vec4( f1, f1, f1, f1 );
            nSum = nSum + ( vecData * vecCoeef2 * vecCooef1  );
            nDenom = nDenom + (( vecCoeef2 * vecCooef1 ));
        }
    }
    return nSum / nDenom;
}


void main(){
    vec4 sampled = BiCubic(textureSample, bTexPos);
    color = sampled;
}  
'''
