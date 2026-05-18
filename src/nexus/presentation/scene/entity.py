from OpenGL.GL import *
import glm

from nexus.presentation.scene.transform import create_model_matrix

class Card:
	def __init__(self, x, y, texture):
		self.x = x
		self.y = y
		self.home_x = x
		self.home_y = y
		self.current_x = x
		self.current_y = y
		self.target_x = x
		self.target_y = y
		self.width = 220
		self.height = 320
		self.texture = texture
		self.hovered = False
		self.dragging = False
		self.current_scale = 1.0
		self.target_scale = 1.0
		self.drag_offset_x = 0
		self.drag_offset_y = 0
		self.state = "hand"
		self.slot = None

	def is_mouse_over(self, mouse_x, mouse_y):
		scaled_width = self.width * self.current_scale
		scaled_height = self.height * self.current_scale
		return (
			mouse_x >= self.current_x
			and mouse_x <= self.current_x + scaled_width
			and mouse_y >= self.current_y
			and mouse_y <= self.current_y + scaled_height
		)

	def set_hover(self, hovered):
		self.hovered = hovered

		if self.dragging or self.state != "hand":
			return

		if hovered:
			self.target_x = self.home_x
			self.target_y = self.home_y - 40
			self.target_scale = 1.08
		else:
			self.target_x = self.home_x
			self.target_y = self.home_y
			self.target_scale = 1.0

	def start_drag(self, mouse_x, mouse_y):
		self.dragging = True
		self.drag_offset_x = mouse_x - self.current_x
		self.drag_offset_y = mouse_y - self.current_y
		self.target_scale = 1.12

	def drag(self, mouse_x, mouse_y):
		if self.dragging:
			self.current_x = mouse_x - self.drag_offset_x
			self.current_y = mouse_y - self.drag_offset_y
			self.target_x = self.current_x
			self.target_y = self.current_y

	def stop_drag_return_to_hand(self):
		self.dragging = False
		self.state = "hand"
		self.slot = None
		self.target_x = self.home_x
		self.target_y = self.home_y
		self.target_scale = 1.0

	def stop_drag_to_slot(self, slot):
		self.dragging = False
		self.state = "field"
		self.slot = slot
		slot.occupy(self)
		self.target_scale = 0.85
		self.target_x = slot.x + (slot.width - self.width * self.target_scale) / 2
		self.target_y = slot.y + (slot.height - self.height * self.target_scale) / 2

	def update(self):
		if not self.dragging:
			self.current_x += (self.target_x - self.current_x) * 0.18
			self.current_y += (self.target_y - self.current_y) * 0.18
		self.current_scale += (self.target_scale - self.current_scale) * 0.15

	def draw(self, vao, model_loc):
		glBindTexture(GL_TEXTURE_2D, self.texture)
		model = create_model_matrix(
			self.current_x,
			self.current_y,
			self.width,
			self.height,
			self.current_scale,
		)
		glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
		glBindVertexArray(vao)
		glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
