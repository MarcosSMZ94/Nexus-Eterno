import glm

def ortho(left, right, bottom, top):
	return glm.ortho(float(left), float(right), float(bottom), float(top), -1.0, 1.0)

def create_model_matrix(x, y, width, height, scale):
	model = glm.mat4(1.0)
	model = glm.translate(model, glm.vec3(float(x), float(y), 0.0))
	model = glm.scale(model, glm.vec3(float(width * scale), float(height * scale), 1.0))
	return model
