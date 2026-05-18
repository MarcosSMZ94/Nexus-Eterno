#version 460 core

out vec4 FragColor;

in vec2 TexCoord;

uniform sampler2D cardTexture;

uniform bool useTexture;
uniform vec4 solidColor;

void main()
{
    if (useTexture)
    {
        FragColor = texture(cardTexture, TexCoord);
    }
    else
    {
        FragColor = solidColor;
    }
}