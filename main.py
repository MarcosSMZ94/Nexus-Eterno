import glfw
import numpy as np
import ctypes

from OpenGL.GL import *
from PIL import Image

from shader import Shader


# =========================
# LOAD TEXTURE
# =========================

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
        image_data
    )

    glGenerateMipmap(GL_TEXTURE_2D)

    return texture


# =========================
# CONFIGURAÇÃO
# =========================

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

TITLE = "Nexus Eterno"


# =========================
# CALLBACK RESIZE
# =========================

def framebuffer_size_callback(window, width, height):

    global WINDOW_WIDTH
    global WINDOW_HEIGHT

    WINDOW_WIDTH = width
    WINDOW_HEIGHT = height

    glViewport(0, 0, width, height)


# =========================
# MATRIZ ORTOGRÁFICA
# =========================

def ortho(left, right, bottom, top):

    return np.array([

        [2 / (right - left), 0, 0, -(right + left) / (right - left)],

        [0, 2 / (top - bottom), 0, -(top + bottom) / (top - bottom)],

        [0, 0, -1, 0],

        [0, 0, 0, 1]

    ], dtype=np.float32)


# =========================
# MATRIZ MODEL
# =========================

def create_model_matrix(x, y, width, height, scale):

    scaled_width = width * scale
    scaled_height = height * scale

    return np.array([

        [scaled_width, 0, 0, x],

        [0, scaled_height, 0, y],

        [0, 0, 1, 0],

        [0, 0, 0, 1]

    ], dtype=np.float32)


# =========================
# CLASSE BATTLE SLOT
# =========================

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
            mouse_x >= self.x and
            mouse_x <= self.x + self.width and
            mouse_y >= self.y and
            mouse_y <= self.y + self.height
        )

    def occupy(self, card):

        self.card = card

    def draw_outline(self, VAO, model_loc):

        model = create_model_matrix(
            self.x,
            self.y,
            self.width,
            self.height,
            1.0
        )

        glUniformMatrix4fv(
            model_loc,
            1,
            GL_TRUE,
            model
        )

        glBindVertexArray(VAO)

        glDrawArrays(
            GL_LINE_LOOP,
            0,
            4
        )


# =========================
# BUSCA SLOT LIVRE
# =========================

def find_free_slot_under_mouse(mouse_x, mouse_y, battle_slots):

    for slot in battle_slots:

        if slot.contains(mouse_x, mouse_y) and slot.is_free():

            return slot

    return None


# =========================
# CLASSE CARD
# =========================

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
            mouse_x >= self.current_x and
            mouse_x <= self.current_x + scaled_width and
            mouse_y >= self.current_y and
            mouse_y <= self.current_y + scaled_height
        )

    def set_hover(self, hovered):

        self.hovered = hovered

        if self.dragging:
            return

        if self.state != "hand":
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

            self.current_x += (
                self.target_x - self.current_x
            ) * 0.18

            self.current_y += (
                self.target_y - self.current_y
            ) * 0.18

        self.current_scale += (
            self.target_scale - self.current_scale
        ) * 0.15

    def draw(self, VAO, model_loc):

        glBindTexture(
            GL_TEXTURE_2D,
            self.texture
        )

        model = create_model_matrix(
            self.current_x,
            self.current_y,
            self.width,
            self.height,
            self.current_scale
        )

        glUniformMatrix4fv(
            model_loc,
            1,
            GL_TRUE,
            model
        )

        glBindVertexArray(VAO)

        glDrawElements(
            GL_TRIANGLES,
            6,
            GL_UNSIGNED_INT,
            None
        )


# =========================
# MAIN
# =========================

def main():

    # =========================
    # GLFW
    # =========================

    if not glfw.init():
        raise Exception("Erro ao iniciar GLFW")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)

    glfw.window_hint(
        glfw.OPENGL_PROFILE,
        glfw.OPENGL_CORE_PROFILE
    )

    # =========================
    # JANELA
    # =========================

    window = glfw.create_window(
        WINDOW_WIDTH,
        WINDOW_HEIGHT,
        TITLE,
        None,
        None
    )

    if not window:
        glfw.terminate()
        raise Exception("Erro ao criar janela")

    glfw.make_context_current(window)

    glfw.maximize_window(window)

    glfw.set_framebuffer_size_callback(
        window,
        framebuffer_size_callback
    )

    glfw.swap_interval(1)

    # =========================
    # INFO OPENGL
    # =========================

    print("OpenGL:", glGetString(GL_VERSION).decode())
    print("GPU:", glGetString(GL_RENDERER).decode())

    # =========================
    # SHADER
    # =========================

    shader = Shader(
        "shaders/vertex.glsl",
        "shaders/fragment.glsl"
    )

    # =========================
    # VÉRTICES + UV
    # =========================

    vertices = np.array([

        # x     y     z      u     v

        0.0, 0.0, 0.0, 0.0, 1.0,
        1.0, 0.0, 0.0, 1.0, 1.0,
        1.0, 1.0, 0.0, 1.0, 0.0,
        0.0, 1.0, 0.0, 0.0, 0.0

    ], dtype=np.float32)

    indices = np.array([

        0, 1, 2,
        2, 3, 0

    ], dtype=np.uint32)

    # =========================
    # VAO
    # =========================

    VAO = glGenVertexArrays(1)
    glBindVertexArray(VAO)

    # =========================
    # VBO
    # =========================

    VBO = glGenBuffers(1)

    glBindBuffer(GL_ARRAY_BUFFER, VBO)

    glBufferData(
        GL_ARRAY_BUFFER,
        vertices.nbytes,
        vertices,
        GL_STATIC_DRAW
    )

    # =========================
    # EBO
    # =========================

    EBO = glGenBuffers(1)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)

    glBufferData(
        GL_ELEMENT_ARRAY_BUFFER,
        indices.nbytes,
        indices,
        GL_STATIC_DRAW
    )

    # =========================
    # ATRIBUTO POSIÇÃO
    # =========================

    glVertexAttribPointer(
        0,
        3,
        GL_FLOAT,
        GL_FALSE,
        5 * 4,
        ctypes.c_void_p(0)
    )

    glEnableVertexAttribArray(0)

    # =========================
    # ATRIBUTO UV
    # =========================

    glVertexAttribPointer(
        1,
        2,
        GL_FLOAT,
        GL_FALSE,
        5 * 4,
        ctypes.c_void_p(3 * 4)
    )

    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    # =========================
    # TEXTURAS
    # =========================

    card_texture1 = load_texture("assets/card1.png")
    card_texture2 = load_texture("assets/card2.png")
    card_texture3 = load_texture("assets/card3.png")

    # =========================
    # UNIFORMS
    # =========================

    shader.use()

    projection_loc = glGetUniformLocation(
        shader.id,
        "projection"
    )

    model_loc = glGetUniformLocation(
        shader.id,
        "model"
    )

    use_texture_loc = glGetUniformLocation(
        shader.id,
        "useTexture"
    )

    solid_color_loc = glGetUniformLocation(
        shader.id,
        "solidColor"
    )

    card_texture_loc = glGetUniformLocation(
        shader.id,
        "cardTexture"
    )

    glUniform1i(
        card_texture_loc,
        0
    )

    # =========================
    # CARTAS
    # =========================

    cards = [

        Card(100, 650, card_texture1),
        Card(380, 650, card_texture2),
        Card(660, 650, card_texture3)

    ]

    # =========================
    # SLOTS DE BATALHA
    # =========================

    battle_slots = [

        BattleSlot(430, 330),
        BattleSlot(660, 330),
        BattleSlot(890, 330),
        BattleSlot(1120, 330),
        BattleSlot(1350, 330)

    ]

    # =========================
    # ESTADO DO MOUSE
    # =========================

    selected_card = None
    mouse_was_pressed = False

    # =========================
    # FUNDO
    # =========================

    glClearColor(0.08, 0.08, 0.1, 1.0)

    # =========================
    # BLEND
    # =========================

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # =========================
    # LOOP
    # =========================

    while not glfw.window_should_close(window):

        glfw.poll_events()

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(window, True)

        # =========================
        # MOUSE
        # =========================

        mouse_x, mouse_y = glfw.get_cursor_pos(window)

        mouse_pressed = (
            glfw.get_mouse_button(
                window,
                glfw.MOUSE_BUTTON_LEFT
            ) == glfw.PRESS
        )

        # =========================
        # HOVER
        # =========================

        hovered_card = None

        if selected_card is None:

            for card in reversed(cards):

                if card.state != "hand":
                    continue

                if card.is_mouse_over(mouse_x, mouse_y):

                    hovered_card = card
                    break

        # =========================
        # COMEÇOU CLIQUE
        # =========================

        if mouse_pressed and not mouse_was_pressed:

            if hovered_card is not None:

                selected_card = hovered_card

                selected_card.start_drag(
                    mouse_x,
                    mouse_y
                )

                cards.remove(selected_card)
                cards.append(selected_card)

        # =========================
        # ARRASTANDO
        # =========================

        if mouse_pressed and selected_card is not None:

            selected_card.drag(
                mouse_x,
                mouse_y
            )

        # =========================
        # SOLTOU CLIQUE
        # =========================

        if not mouse_pressed and mouse_was_pressed:

            if selected_card is not None:

                target_slot = find_free_slot_under_mouse(
                    mouse_x,
                    mouse_y,
                    battle_slots
                )

                if target_slot is not None:

                    selected_card.stop_drag_to_slot(
                        target_slot
                    )

                else:

                    selected_card.stop_drag_return_to_hand()

                selected_card = None

        # =========================
        # UPDATE DAS CARTAS
        # =========================

        for card in cards:

            if selected_card is None:

                card.set_hover(
                    card == hovered_card
                )

            else:

                card.set_hover(False)

            card.update()

        mouse_was_pressed = mouse_pressed

        # =========================
        # RENDER
        # =========================

        glClear(GL_COLOR_BUFFER_BIT)

        shader.use()

        projection = ortho(
            0,
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            0
        )

        glUniformMatrix4fv(
            projection_loc,
            1,
            GL_TRUE,
            projection
        )

        # =========================
        # DRAW DOS SLOTS
        # =========================

        glUniform1i(
            use_texture_loc,
            0
        )

        glUniform4f(
            solid_color_loc,
            1.0, 1.0, 1.0, 1.0
        )

        glLineWidth(3.0)

        for slot in battle_slots:

            slot.draw_outline(
                VAO,
                model_loc
            )

        # =========================
        # DRAW DAS CARTAS
        # =========================

        glActiveTexture(GL_TEXTURE0)

        glUniform1i(
            use_texture_loc,
            1
        )

        for card in cards:

            card.draw(
                VAO,
                model_loc
            )

        glfw.swap_buffers(window)

    # =========================
    # LIMPEZA
    # =========================

    glDeleteVertexArrays(1, [VAO])

    glDeleteBuffers(1, [VBO])
    glDeleteBuffers(1, [EBO])

    glfw.terminate()


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    main()