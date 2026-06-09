import glm

def ortho(left, right, bottom, top):
	return glm.ortho(left, right, bottom, top, -1.0, 1.0)

def create_model_matrix(x, y, width, height, scale):
	model = glm.mat4(1.0)
	model = glm.translate(model, glm.vec3(x, y, 0.0))
	model = glm.scale(model, glm.vec3(width * scale, height * scale, 1.0))
	return model
