from OpenGL.GL import *
from PIL import Image

def load_texture(path):
	texture = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, texture)

	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

	image = Image.open(path)
	image = image.transpose(Image.FLIP_TOP_BOTTOM)
	image_data = image.convert("RGBA").tobytes()

	glTexImage2D(
		GL_TEXTURE_2D,
		0,
		GL_RGBA,
		image.width,
		image.height,
		0,
		GL_RGBA,
		GL_UNSIGNED_BYTE,
		image_data,
	)

	glGenerateMipmap(GL_TEXTURE_2D)
	return texture
