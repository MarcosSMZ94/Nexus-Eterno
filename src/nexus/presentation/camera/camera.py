import math

import glm

class TurnCamera:

	def __init__(self, screen_width, screen_height):
		self.screen_width = screen_width
		self.screen_height = screen_height
		self.current_angle = 0.0
		self.target_angle = 0.0

	def resize(self, screen_width, screen_height):
		self.screen_width = screen_width
		self.screen_height = screen_height

	def update(self):
		speed = 0.08
		self.current_angle += (self.target_angle - self.current_angle) * speed

	def get_view_matrix(self):
		center_x = self.screen_width / 2.0
		center_y = self.screen_height / 2.0

		view = glm.mat4(1.0)
		view = glm.translate(view, glm.vec3(center_x, center_y, 0.0))
		view = glm.rotate(view, self.current_angle, glm.vec3(0.0, 0.0, 1.0))
		view = glm.translate(view, glm.vec3(-center_x, -center_y, 0.0))
		return view

	def screen_to_world(self, mouse_x, mouse_y):
		view = self.get_view_matrix()
		inverse_view = glm.inverse(view)
		world_pos = inverse_view * glm.vec4(mouse_x, mouse_y, 0.0, 1.0)
		return world_pos.x, world_pos.y
