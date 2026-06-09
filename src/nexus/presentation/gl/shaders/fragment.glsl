#version 460 core

out vec4 FragColor;

in vec2 TexCoord;

uniform sampler2D cardTexture;

uniform bool useTexture;
uniform vec4 solidColor;

uniform vec4 tint = vec4(1.0);

void main()
{
    if (useTexture)
    {
        FragColor = texture(cardTexture, TexCoord) * tint;
    }
    else
    {
        FragColor = solidColor * tint;
    }
}