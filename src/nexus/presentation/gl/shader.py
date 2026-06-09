from OpenGL.GL import *

class Shader:
	def __init__(self, vertex_path, fragment_path):
		with open(vertex_path, "r", encoding="utf-8") as file:
			vertex_src = file.read()

		with open(fragment_path, "r", encoding="utf-8") as file:
			fragment_src = file.read()

		vertex_shader = glCreateShader(GL_VERTEX_SHADER)
		glShaderSource(vertex_shader, vertex_src)
		glCompileShader(vertex_shader)
		self.check_compile_errors(vertex_shader, "VERTEX")

		fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
		glShaderSource(fragment_shader, fragment_src)
		glCompileShader(fragment_shader)
		self.check_compile_errors(fragment_shader, "FRAGMENT")

		self.id = glCreateProgram()
		glAttachShader(self.id, vertex_shader)
		glAttachShader(self.id, fragment_shader)
		glLinkProgram(self.id)
		self.check_compile_errors(self.id, "PROGRAM")

		glDeleteShader(vertex_shader)
		glDeleteShader(fragment_shader)

	def use(self):
		glUseProgram(self.id)

	def check_compile_errors(self, shader, shader_type):
		if shader_type != "PROGRAM":
			success = glGetShaderiv(shader, GL_COMPILE_STATUS)
			if not success:
				info_log = glGetShaderInfoLog(shader).decode()
				print(f"ERRO SHADER ({shader_type})")
				print(info_log)
		else:
			success = glGetProgramiv(shader, GL_LINK_STATUS)
			if not success:
				info_log = glGetProgramInfoLog(shader).decode()
				print(f"ERRO LINK ({shader_type})")
				print(info_log)
