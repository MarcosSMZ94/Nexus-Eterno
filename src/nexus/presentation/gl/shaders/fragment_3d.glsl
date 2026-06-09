#version 460 core

in vec3 FragPos;
in vec3 Normal;
in vec2 TexCoord;

out vec4 FragColor;

uniform sampler2D diffuseTexture;
uniform bool      useTexture;
uniform vec4      solidColor;

uniform vec3  lightDir;    
uniform vec3  lightColor;
uniform float ambientStr;
uniform vec3  viewPos;

uniform vec4 tint = vec4(1.0);

void main()
{
    vec4 base = useTexture ? texture(diffuseTexture, TexCoord) : solidColor;

    vec3 norm    = normalize(Normal);
    float diff   = max(dot(norm, normalize(lightDir)), 0.0);

    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 halfDir = normalize(normalize(lightDir) + viewDir);
    float spec   = pow(max(dot(norm, halfDir), 0.0), 32.0);

    vec3 lighting = (ambientStr + diff + 0.3 * spec) * lightColor;
    FragColor = vec4(lighting, 1.0) * base * tint;
}
