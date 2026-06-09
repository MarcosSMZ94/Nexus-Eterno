from pathlib import Path

from OpenGL.GL import *
from PIL import Image

def load_texture(path):
	texture = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, texture)

	glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_LOD_BIAS, -0.5)

	image_path = Path(path)
	if image_path.exists():
		image = Image.open(image_path).convert("RGBA")
		image = image.transpose(Image.FLIP_TOP_BOTTOM)
		image_data = image.tobytes()
		width = image.width
		height = image.height
	else:
		width = 1
		height = 1
		image_data = bytes([255, 255, 255, 255])

	glTexImage2D(
		GL_TEXTURE_2D,
		0,
		GL_RGBA8,
		width,
		height,
		0,
		GL_RGBA,
		GL_UNSIGNED_BYTE,
		image_data,
	)

	glGenerateMipmap(GL_TEXTURE_2D)
	glBindTexture(GL_TEXTURE_2D, 0)
	return texture
