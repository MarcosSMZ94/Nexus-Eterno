from OpenGL.GL import *
import glm

from nexus.presentation.scene.transform import create_model_matrix

class BattleSlot:
	def __init__(self, x, y, width=190, height=270):
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.card = None

	def is_free(self):
		return self.card is None

	def contains(self, mouse_x, mouse_y):
		return (
			mouse_x >= self.x
			and mouse_x <= self.x + self.width
			and mouse_y >= self.y
			and mouse_y <= self.y + self.height
		)

	def occupy(self, card):
		self.card = card

	def draw_outline(self, vao, model_loc):
		model = create_model_matrix(self.x, self.y, self.width, self.height, 1.0)
		glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
		glBindVertexArray(vao)
		glDrawArrays(GL_LINE_LOOP, 0, 4)

class Slot(BattleSlot):
	def __init__(self, x, y, width=190, height=270, owner=None, slot_type="battle", color=(1.0, 1.0, 1.0, 1.0)):
		super().__init__(x, y, width, height)
		self.owner = owner
		self.slot_type = slot_type
		self.color = color
		self.state = "free"
		self.hovered = False

	def draw_outline(self, vao, model_loc, solid_color_loc=None):
		super().draw_outline(vao, model_loc)
