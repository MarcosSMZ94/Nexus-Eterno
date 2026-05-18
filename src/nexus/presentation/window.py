import ctypes
from pathlib import Path

import glfw
import glm
from OpenGL.GL import *

from nexus.presentation.gl.shader import Shader
from nexus.presentation.gl.texture import load_texture
from nexus.presentation.scene.entity import Card
from nexus.presentation.scene.scene import BattleSlot, find_free_slot_under_mouse
from nexus.presentation.scene.transform import ortho


WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
TITLE = "Nexus Eterno"


def framebuffer_size_callback(window, width, height):
    global WINDOW_WIDTH
    global WINDOW_HEIGHT

    WINDOW_WIDTH = width
    WINDOW_HEIGHT = height
    glViewport(0, 0, width, height)


def run_window():
    if not glfw.init():
        raise Exception("Erro ao iniciar GLFW")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 6)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, TITLE, None, None)
    if not window:
        glfw.terminate()
        raise Exception("Erro ao criar janela")

    glfw.make_context_current(window)
    glfw.maximize_window(window)
    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)
    glfw.swap_interval(1)

    print("OpenGL:", glGetString(GL_VERSION).decode())
    print("GPU:", glGetString(GL_RENDERER).decode())

    base_dir = Path(__file__).resolve().parent
    shader = Shader(
        str(base_dir / "gl" / "shaders" / "vertex.glsl"),
        str(base_dir / "gl" / "shaders" / "fragment.glsl"),
    )

    vertices = (ctypes.c_float * 20)(
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        1.0,
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
        1.0,
        0.0,
        1.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
    )

    indices = (ctypes.c_uint * 6)(0, 1, 2, 2, 3, 0)

    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertices), vertices, GL_STATIC_DRAW)

    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, ctypes.sizeof(indices), indices, GL_STATIC_DRAW)

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)

    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(3 * 4))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    card_texture1 = load_texture(str(base_dir / "assets" / "card1.png"))
    card_texture2 = load_texture(str(base_dir / "assets" / "card2.png"))
    card_texture3 = load_texture(str(base_dir / "assets" / "card3.png"))

    shader.use()
    projection_loc = glGetUniformLocation(shader.id, "projection")
    model_loc = glGetUniformLocation(shader.id, "model")
    use_texture_loc = glGetUniformLocation(shader.id, "useTexture")
    solid_color_loc = glGetUniformLocation(shader.id, "solidColor")
    card_texture_loc = glGetUniformLocation(shader.id, "cardTexture")

    glUniform1i(card_texture_loc, 0)

    cards = [
        Card(100, 650, card_texture1),
        Card(380, 650, card_texture2),
        Card(660, 650, card_texture3),
    ]

    battle_slots = [
        BattleSlot(430, 330),
        BattleSlot(660, 330),
        BattleSlot(890, 330),
        BattleSlot(1120, 330),
        BattleSlot(1350, 330),
    ]

    selected_card = None
    mouse_was_pressed = False

    glClearColor(0.08, 0.08, 0.1, 1.0)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    while not glfw.window_should_close(window):
        glfw.poll_events()

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(window, True)

        mouse_x, mouse_y = glfw.get_cursor_pos(window)
        mouse_pressed = glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS

        hovered_card = None
        if selected_card is None:
            for card in reversed(cards):
                if card.state != "hand":
                    continue
                if card.is_mouse_over(mouse_x, mouse_y):
                    hovered_card = card
                    break

        if mouse_pressed and not mouse_was_pressed and hovered_card is not None:
            selected_card = hovered_card
            selected_card.start_drag(mouse_x, mouse_y)
            cards.remove(selected_card)
            cards.append(selected_card)

        if mouse_pressed and selected_card is not None:
            selected_card.drag(mouse_x, mouse_y)

        if not mouse_pressed and mouse_was_pressed and selected_card is not None:
            target_slot = find_free_slot_under_mouse(mouse_x, mouse_y, battle_slots)
            if target_slot is not None:
                selected_card.stop_drag_to_slot(target_slot)
            else:
                selected_card.stop_drag_return_to_hand()
            selected_card = None

        for card in cards:
            if selected_card is None:
                card.set_hover(card == hovered_card)
            else:
                card.set_hover(False)
            card.update()

        mouse_was_pressed = mouse_pressed

        glClear(GL_COLOR_BUFFER_BIT)
        shader.use()

        projection = ortho(0, WINDOW_WIDTH, WINDOW_HEIGHT, 0)
        glUniformMatrix4fv(projection_loc, 1, GL_FALSE, glm.value_ptr(projection))

        glUniform1i(use_texture_loc, 0)
        glUniform4f(solid_color_loc, 1.0, 1.0, 1.0, 1.0)
        glLineWidth(3.0)

        for slot in battle_slots:
            slot.draw_outline(vao, model_loc)

        glActiveTexture(GL_TEXTURE0)
        glUniform1i(use_texture_loc, 1)

        for card in cards:
            card.draw(vao, model_loc)

        glfw.swap_buffers(window)

    glDeleteVertexArrays(1, [vao])
    glDeleteBuffers(1, [vbo])
    glDeleteBuffers(1, [ebo])
    glfw.terminate()
