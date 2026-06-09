import ctypes
from pathlib import Path

import glfw
import glm
from OpenGL.GL import *

from nexus.presentation.gl.shader import Shader
from nexus.presentation.scene.scene import Slot
from nexus.presentation.scene.transform import ortho, create_model_matrix
from nexus.presentation.camera.camera import TurnCamera
from nexus.presentation.mapping.visual_mapper import make_hand_visuals, make_field_visuals
from nexus.presentation.ui.text_renderer import TextRenderer
from nexus.presentation.scene.scene3d import Scene3D
from nexus.application.handlers.core.summon_handler import required_sacrifices
from nexus.presentation.ui.constants import (   # noqa: F401 — re-exporta para uso externo
    DESIGN_W, DESIGN_H, TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    AUTO_PHASES, MAIN_PHASES, SPELLS_NEEDING_TARGET, SPELLS_NEEDING_ALLY_TARGET,
    PHASE_NAMES, HERO_NAMES, HERO_COOLDOWN_TURNS, DOUBLE_CLICK_SECONDS,
    WHITE, ELEMENT_TINT, ELEMENT_CLEAR, ELEMENT_NAMES, DEFAULT_CLEAR,
)
from nexus.domain.turn.phase import Phase


def framebuffer_size_callback(window, width, height):
    global WINDOW_WIDTH, WINDOW_HEIGHT
    WINDOW_WIDTH = max(1, width)
    WINDOW_HEIGHT = max(1, height)


def point_in_rect(px, py, rect):
    x, y, w, h = rect
    return x <= px <= x + w and y <= py <= y + h

def run_window(engine):
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
        0.0, 0.0, 0.0, 0.0, 1.0,
        1.0, 0.0, 0.0, 1.0, 1.0,
        1.0, 1.0, 0.0, 1.0, 0.0,
        0.0, 1.0, 0.0, 0.0, 0.0,
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

    texture_cache = {}
    text = TextRenderer()

    # carrega definições de heróis para tooltip e uso no frame loop
    import json as _json
    _heroes_path = base_dir.parent / "data" / "heroes.json"
    _heroes_map = {h["id"]: h for h in _json.load(open(_heroes_path, encoding="utf-8"))}

    shader.use()
    projection_loc = glGetUniformLocation(shader.id, "projection")
    view_loc = glGetUniformLocation(shader.id, "view")
    model_loc = glGetUniformLocation(shader.id, "model")
    use_texture_loc = glGetUniformLocation(shader.id, "useTexture")
    solid_color_loc = glGetUniformLocation(shader.id, "solidColor")
    card_texture_loc = glGetUniformLocation(shader.id, "cardTexture")
    tint_loc = glGetUniformLocation(shader.id, "tint")
    glUniform1i(card_texture_loc, 0)
    glUniform4f(tint_loc, *WHITE)

    # ============================================================
    # LOBBY — seleção de jogadores e decks antes do jogo
    # ============================================================
    def _lobby_loop():
        """Exibe tela de seleção antes do jogo; chama engine.setup_game() ao confirmar."""
        # ------ mini draw helpers (closure sobre vao/uniforms/text) ------
        def _fill(x, y, w, h, color):
            glUniform1i(use_texture_loc, 0)
            glUniform4f(solid_color_loc, *color)
            m = create_model_matrix(x, y, w, h, 1.0)
            glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(m))
            glBindVertexArray(vao)
            glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
            glUniform1i(use_texture_loc, 1)

        def _tex_rect(x, y, w, h, texture):
            glUniform1i(use_texture_loc, 1)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, texture)
            m = create_model_matrix(x, y, w, h, 1.0)
            glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(m))
            glBindVertexArray(vao)
            glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

        def _txt(value, x, y, size=24, color=(1.0, 1.0, 1.0, 1.0), anchor="topleft"):
            tex, tw, th = text.get(value, size, color)
            if anchor == "center":
                x -= tw / 2; y -= th / 2
            elif anchor == "topcenter":
                x -= tw / 2
            elif anchor in ("topright", "right"):
                x -= tw
            _tex_rect(x, y, tw, th, tex)

        def _btn(rect, label, enabled=True,
                 base=(0.16, 0.16, 0.22, 0.92), accent=(0.35, 0.45, 0.7, 1.0)):
            bx, by, bw, bh = rect
            if enabled:
                _fill(bx, by, bw, bh, base)
                _fill(bx, by, 6, bh, accent)
                tc = (1.0, 1.0, 1.0, 1.0)
            else:
                _fill(bx, by, bw, bh, (0.10, 0.10, 0.13, 0.75))
                tc = (0.45, 0.45, 0.50, 1.0)
            _txt(label, bx + bw / 2 + 3, by + bh / 2, 19, tc, anchor="center")

        # ------ estado do lobby ------
        lb_names  = ["Jogador 1", "Jogador 2"]
        lb_decks  = [None, None]
        lb_focus  = [0]        # lista para ser mutável em sub-closure
        lb_mouse  = [False]    # estado anterior do botão esquerdo

        def _char_cb(win, codepoint):
            f = lb_focus[0]
            if f is not None and len(lb_names[f]) < 18:
                lb_names[f] += chr(codepoint)

        glfw.set_char_callback(window, _char_cb)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # projeção ortográfica para 2D (coords de design)
        proj = ortho(0, DESIGN_W, DESIGN_H, 0)
        identity = glm.mat4(1.0)
        bksp_was = [False]

        # layout dos painéis (dois jogadores lado a lado)
        panel_w, panel_h = 480, 350
        gap = 120
        total_panels = panel_w * 2 + gap
        p_x = [(DESIGN_W - total_panels) / 2,
               (DESIGN_W - total_panels) / 2 + panel_w + gap]
        panel_y = (DESIGN_H - panel_h) / 2 - 30

        btn_w  = panel_w - 60
        btn_h  = 50
        btn_gap = 12

        deck_options = [("deck_sol", "Deck Sol"), ("deck_sombra", "Deck Sombra")]
        deck_accent  = {"deck_sol": (1.0, 0.78, 0.1, 1.0),
                        "deck_sombra": (0.65, 0.35, 1.0, 1.0)}

        while not glfw.window_should_close(window):
            glfw.poll_events()

            # backspace com debounce
            bksp = glfw.get_key(window, glfw.KEY_BACKSPACE) == glfw.PRESS
            if bksp and not bksp_was[0]:
                f = lb_focus[0]
                if f is not None and lb_names[f]:
                    lb_names[f] = lb_names[f][:-1]
            bksp_was[0] = bksp

            # mouse em coords de design
            mx, my = glfw.get_cursor_pos(window)
            fw, fh = glfw.get_framebuffer_size(window)
            _s = min(fw / DESIGN_W, fh / DESIGN_H)
            _ox = (fw - DESIGN_W * _s) / 2
            _oy = (fh - DESIGN_H * _s) / 2
            dmx = (mx - _ox) / _s
            dmy = (my - _oy) / _s
            btn_now = (glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS)
            clicked = btn_now and not lb_mouse[0]
            lb_mouse[0] = btn_now

            # clear e viewport letterbox
            glClearColor(*DEFAULT_CLEAR)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glViewport(int(_ox), int(_oy), int(DESIGN_W * _s), int(DESIGN_H * _s))
            glUniformMatrix4fv(projection_loc, 1, GL_FALSE, glm.value_ptr(proj))
            glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(identity))
            glUniform4f(tint_loc, 1.0, 1.0, 1.0, 1.0)

            # título
            _txt("NEXUS ETERNO  —  O CONFLITO DAS AUTORIDADES",
                 DESIGN_W / 2, 70, 36, (1.0, 0.85, 0.3, 1.0), anchor="topcenter")
            _txt("Selecione jogadores e decks para iniciar",
                 DESIGN_W / 2, 118, 22, (0.7, 0.7, 0.75, 1.0), anchor="topcenter")

            for pi, px in enumerate(p_x):
                # painel de fundo
                _fill(px, panel_y, panel_w, panel_h, (0.10, 0.10, 0.16, 0.88))
                _fill(px, panel_y, panel_w, 4,
                      (0.35, 0.45, 0.70, 1.0))  # barra superior

                # rótulo "JOGADOR N"
                _txt(f"JOGADOR {pi + 1}", px + panel_w / 2, panel_y + 16, 22,
                     (0.85, 0.85, 0.90, 1.0), anchor="topcenter")

                # campo de nome
                name_y = panel_y + 58
                name_rect = (px + 30, name_y, btn_w, 40)
                focused = (lb_focus[0] == pi)
                border_c = (0.55, 0.75, 1.0, 1.0) if focused else (0.3, 0.3, 0.4, 1.0)
                _fill(px + 28, name_y - 2, btn_w + 4, 44, border_c)
                _fill(px + 30, name_y, btn_w, 40, (0.07, 0.07, 0.10, 1.0))
                cursor_s = "|" if focused else ""
                _txt(lb_names[pi] + cursor_s, px + 42, name_y + 8, 21,
                     (1.0, 1.0, 1.0, 1.0))
                if clicked and point_in_rect(dmx, dmy, name_rect):
                    lb_focus[0] = pi

                # botões de deck
                for di, (deck_id, deck_label) in enumerate(deck_options):
                    dy = panel_y + 122 + di * (btn_h + btn_gap)
                    drect = (px + 30, dy, btn_w, btn_h)
                    selected = (lb_decks[pi] == deck_id)
                    acc = deck_accent[deck_id] if selected else (0.35, 0.45, 0.7, 1.0)
                    base_c = (0.12, 0.12, 0.18, 0.95) if selected else (0.16, 0.16, 0.22, 0.92)
                    _btn(drect, deck_label, True, base=base_c, accent=acc)
                    if selected:
                        _txt("✓", px + 30 + btn_w - 24, dy + btn_h / 2, 20,
                             (0.35, 1.0, 0.35, 1.0), anchor="center")
                    if clicked and point_in_rect(dmx, dmy, drect):
                        lb_decks[pi] = deck_id
                        lb_focus[0] = None   # desfoca campo de nome

            # botão Iniciar
            ready = (lb_decks[0] is not None and lb_decks[1] is not None)
            start_w2, start_h2 = 380, 58
            start_rect = (DESIGN_W / 2 - start_w2 / 2,
                          panel_y + panel_h + 36,
                          start_w2, start_h2)
            if ready:
                _btn(start_rect, "INICIAR PARTIDA", True,
                     base=(0.08, 0.22, 0.08, 0.95), accent=(0.3, 0.85, 0.3, 1.0))
            else:
                _btn(start_rect, "INICIAR PARTIDA", False)

            if clicked and ready and point_in_rect(dmx, dmy, start_rect):
                engine.setup_game(
                    player1_name=lb_names[0],
                    player2_name=lb_names[1],
                    deck1_id=lb_decks[0],
                    deck2_id=lb_decks[1],
                    initial_hand=4,
                )
                glfw.set_char_callback(window, lambda w, cp: None)
                break

            glfw.swap_buffers(window)

    if engine.game_state is None:
        _lobby_loop()

    gs = engine.game_state

    def _get_hero(player_index):
        pid = getattr(gs.players[player_index], "hero_id", None)
        return _heroes_map.get(pid)

    scene3d = Scene3D(base_dir)
    slot_centers = scene3d.get_slot_screen_positions(DESIGN_W, DESIGN_H)

    # ---------------- layout (coords de design) ----------------
    TOP_BAR = 120
    BOTTOM_MARGIN = 18
    RIGHT_COL = 320
    ROWS = 4
    ROW_GAP = 18

    card_height = (DESIGN_H - TOP_BAR - BOTTOM_MARGIN - (ROWS - 1) * ROW_GAP) / ROWS
    card_width = card_height * (2.0 / 3.0)
    hand_gap = 14
    battle_gap = 40
    hand_slots_count = 5
    board_center_x = (DESIGN_W - RIGHT_COL) / 2

    _hud_btn_w = 290
    _hud_btn_x = DESIGN_W - _hud_btn_w - 20

    def centered_positions(count, width, gap):
        if count <= 0:
            return []
        total = count * width + (count - 1) * gap
        start = board_center_x - total / 2
        return [start + i * (width + gap) for i in range(count)]

    def hand_positions(count):
        """Posições da mão limitadas à área central; sobrepõe as cartas quando há muitas
        (evita transbordar sobre o painel/botões do HUD)."""
        if count <= 0:
            return []
        if count == 1:
            return [board_center_x - card_width / 2]
        x_min = 396
        x_max = _hud_btn_x - 24
        avail = x_max - x_min
        step_full = card_width + hand_gap
        total_full = card_width + (count - 1) * step_full
        if total_full <= avail:
            start = board_center_x - total_full / 2
            return [start + i * step_full for i in range(count)]
        step = (avail - card_width) / (count - 1)
        return [x_min + i * step for i in range(count)]

    hand_x_positions = centered_positions(hand_slots_count, card_width, hand_gap)

    row_step      = card_height + ROW_GAP
    BOTTOM_HAND_Y = TOP_BAR + 3 * row_step   # jogador ativo (na câmera) fica aqui
    TOP_HAND_Y    = TOP_BAR

    active_player = 1  # inicial; reatribuído no frame loop

    def hand_y_for(owner):
        return BOTTOM_HAND_Y if owner == active_player else TOP_HAND_Y

    battle_x_p1 = [slot_centers[("monster", 1, i)][0] - card_width / 2 for i in range(3)]
    battle_x_p2 = [slot_centers[("monster", 2, i)][0] - card_width / 2 for i in range(3)]
    battle_y_p1 = slot_centers[("monster", 1, 1)][1] - card_height / 2
    battle_y_p2 = slot_centers[("monster", 2, 1)][1] - card_height / 2

    def battle_y_for(owner):
        return battle_y_p1 if owner == 1 else battle_y_p2

    def _slot_topleft(zone, owner, idx):
        cx, cy = slot_centers[(zone, owner, idx)]
        return cx - card_width / 2, cy - card_height / 2

    slots = []

    def _fill_slots():
        slots.clear()
        for x in hand_x_positions:
            slots.append(Slot(x, hand_y_for(2), card_width, card_height, owner=2, slot_type="hand", color=(0.4, 0.4, 0.4, 1.0)))
        for i in range(3):
            x, y = _slot_topleft("monster", 2, i)
            slots.append(Slot(x, y, card_width, card_height, owner=2, slot_type="battle", color=(0.55, 0.25, 0.95, 1.0)))
        for i in range(3):
            x, y = _slot_topleft("spell", 2, i)
            slots.append(Slot(x, y, card_width, card_height, owner=2, slot_type="spell", color=(0.1, 0.7, 0.3, 1.0)))
        for i in range(3):
            x, y = _slot_topleft("monster", 1, i)
            slots.append(Slot(x, y, card_width, card_height, owner=1, slot_type="battle", color=(1.0, 0.6, 0.15, 1.0)))
        for i in range(3):
            x, y = _slot_topleft("spell", 1, i)
            slots.append(Slot(x, y, card_width, card_height, owner=1, slot_type="spell", color=(0.1, 0.7, 0.3, 1.0)))
        for x in hand_x_positions:
            slots.append(Slot(x, hand_y_for(1), card_width, card_height, owner=1, slot_type="hand", color=(0.1, 0.85, 0.3, 1.0)))

    def rebuild_layout():
        nonlocal slot_centers, battle_x_p1, battle_x_p2, battle_y_p1, battle_y_p2
        slot_centers = scene3d.get_slot_screen_positions(DESIGN_W, DESIGN_H)
        battle_x_p1  = [slot_centers[("monster", 1, i)][0] - card_width / 2 for i in range(3)]
        battle_x_p2  = [slot_centers[("monster", 2, i)][0] - card_width / 2 for i in range(3)]
        battle_y_p1  = slot_centers[("monster", 1, 1)][1] - card_height / 2
        battle_y_p2  = slot_centers[("monster", 2, 1)][1] - card_height / 2
        _fill_slots()

    _fill_slots()

    # ---------------- cartas (espelham o game_state) ----------------
    cards = []

    def rebuild_hand(owner):
        nonlocal cards
        player = gs.players[owner - 1]
        cards = [c for c in cards if not (c.owner == owner and c.state == "hand")]
        positions = hand_positions(len(player.hand))
        cards.extend(
            make_hand_visuals(base_dir, positions, hand_y_for(owner), owner, player.hand,
                              texture_cache, card_width, card_height)
        )

    def rebuild_field(owner):
        nonlocal cards
        cards = [c for c in cards if not (c.owner == owner and c.state == "field")]
        board_cards = gs.players[owner - 1].board.get_cards()
        bx = battle_x_p1 if owner == 1 else battle_x_p2
        cards.extend(
            make_field_visuals(base_dir, bx, battle_y_for(owner), owner, board_cards,
                               texture_cache, card_width, card_height)
        )

    # definido aqui para que rebuild_all possa ler antes do frame loop
    spell_targeting = None
    detail_card = None  # inicializado antes de rebuild_all para que nonlocal funcione

    def rebuild_all():
        nonlocal detail_card
        if spell_targeting is not None:
            return  # não rebuildar durante targeting bifásico — spell card ficaria órfã
        rebuild_hand(1)
        rebuild_hand(2)
        rebuild_field(1)
        rebuild_field(2)
        # Atualiza detail_card para o novo visual card que encapsula a mesma domain card.
        # Se a carta foi destruída ou consumida, fecha o painel (detail_card = None).
        if detail_card is not None:
            _old_dom = getattr(detail_card, "domain_card", None)
            detail_card = next(
                (c for c in cards if getattr(c, "domain_card", None) is _old_dom),
                None,
            )

    def settle_to_manual_phase():
        guard = 0
        while gs.current_phase in AUTO_PHASES and guard < 32:
            engine.pass_phase()
            engine.resolver.resolve(gs)
            guard += 1

    def advance_phase():
        engine.pass_phase()
        engine.resolver.resolve(gs)
        settle_to_manual_phase()
        rebuild_all()

    engine.resolver.resolve(gs)
    settle_to_manual_phase()
    rebuild_all()

    def resolve_drop_slot(card, owner):
        cx = card.current_x + card.width / 2
        cy = card.current_y + card.height / 2
        battle_cy = battle_y_for(owner) + card_height / 2
        hand_cy = hand_y_for(owner) + card_height / 2
        if abs(cy - battle_cy) > abs(cy - hand_cy):
            return None
        best, best_d = None, None
        for s in slots:
            if s.slot_type != "battle" or s.owner != owner or not s.is_free():
                continue
            d = abs((s.x + s.width / 2) - cx)
            if best_d is None or d < best_d:
                best_d, best = d, s
        return best

    def field_card_under(wx, wy):
        for c in reversed(cards):
            if (c.state == "field"
                    and c.is_mouse_over(wx, wy)
                    and getattr(getattr(c, "domain_card", None), "board_position", None) is not None):
                return c
        return None

    def has_attacked(card):
        d = getattr(card, "domain_card", None)
        return bool(getattr(d, "has_attacked", False)) if d else False

    def _wrap_text(text, max_chars):
        """Quebra 'text' em linhas de no máximo max_chars caracteres, sem cortar palavras."""
        words = text.split()
        lines, cur = [], ""
        for word in words:
            if len(cur) + len(word) + (1 if cur else 0) <= max_chars:
                cur = f"{cur} {word}".strip()
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    # ============================================================
    # HELPERS DE DESENHO
    # ============================================================
    def set_view(matrix):
        glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(matrix))

    def set_tint(color):
        glUniform4f(tint_loc, *color)

    def fill_rect(x, y, w, h, color):
        glUniform1i(use_texture_loc, 0)
        glUniform4f(solid_color_loc, *color)
        model = create_model_matrix(x, y, w, h, 1.0)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
        glBindVertexArray(vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glUniform1i(use_texture_loc, 1)  # restaura: fill_rect nunca deixa shader em modo sólido

    def draw_texture_rect(x, y, w, h, texture):
        glUniform1i(use_texture_loc, 1)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, texture)
        model = create_model_matrix(x, y, w, h, 1.0)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
        glBindVertexArray(vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

    def draw_text(value, x, y, size=24, color=(1.0, 1.0, 1.0, 1.0), anchor="topleft"):
        tex, w, h = text.get(value, size, color)
        if anchor in ("topright", "right"):
            x -= w
        elif anchor == "center":
            x -= w / 2
            y -= h / 2
        elif anchor == "topcenter":
            x -= w / 2
        draw_texture_rect(x, y, w, h, tex)
        return w, h

    def draw_label_on_card(card, lx, ly, lw, lh, color=None, texture=None):
        scale = card.current_scale
        cw = card.width * scale
        ch = card.height * scale
        cx = card.current_x + cw / 2
        cy = card.current_y + ch / 2
        rot = 0.0 if card.owner == active_player else 180.0
        model = glm.mat4(1.0)
        model = glm.translate(model, glm.vec3(cx, cy, 0.0))
        model = glm.rotate(model, glm.radians(rot), glm.vec3(0.0, 0.0, 1.0))
        model = glm.translate(model, glm.vec3(-cw / 2 + lx, -ch / 2 + ly, 0.0))
        model = glm.scale(model, glm.vec3(lw, lh, 1.0))
        if texture is not None:
            glUniform1i(use_texture_loc, 1)
            glBindTexture(GL_TEXTURE_2D, texture)
        else:
            glUniform1i(use_texture_loc, 0)
            glUniform4f(solid_color_loc, *color)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model))
        glBindVertexArray(vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

    def card_overlay(card, color):
        draw_label_on_card(card, 0, 0, card.width * card.current_scale, card.height * card.current_scale, color=color)

    def _atk_color(d):
        """Verde se ATK buffed, vermelho se debuffed, dourado se normal."""
        base = getattr(d, "base_atk", d.atk)
        if d.atk > base:
            return (0.35, 1.0, 0.35, 1.0)
        elif d.atk < base:
            return (1.0, 0.35, 0.35, 1.0)
        return (1.0, 0.92, 0.45, 1.0)

    def _def_color(d):
        """Verde se def_temp positivo, vermelho se negativo, amarelo se zero (padrão)."""
        dt = getattr(d, "def_temp", 0)
        if dt > 0:
            return (0.35, 1.0, 0.35, 1.0)
        elif dt < 0:
            return (1.0, 0.35, 0.35, 1.0)
        return (1.0, 0.92, 0.45, 1.0)

    def draw_card_stats(card):
        d = getattr(card, "domain_card", None)
        if d is None or getattr(d, "card_type", "creature") != "creature":
            return
        scale = card.current_scale
        cw = card.width * scale
        ch = card.height * scale
        size = 20
        pad = 8
        _BG = (0.0, 0.0, 0.0, 0.62)
        defesa = d.hp + getattr(d, "def_temp", 0)
        atk_tex, aw, ah = text.get(str(d.atk), size, _atk_color(d))
        hp_tex, hw, hh = text.get(str(defesa), size, _def_color(d))
        lvl_tex, lw, lh = text.get(f"Nv{d.level}", 18, (1.0, 1.0, 1.0, 1.0))
        # barra de fundo na base da carta (ATK / HP)
        bar_h = max(ah, hh) + pad * 2
        draw_label_on_card(card, 0, ch - bar_h, cw, bar_h, color=_BG)
        # nível com fundo (canto superior esquerdo) — só para o jogador ativo
        if card.owner == active_player:
            draw_label_on_card(card, pad - 2, pad - 2, lw + 4, lh + 4, color=_BG)
            draw_label_on_card(card, pad, pad, lw, lh, texture=lvl_tex)
        # ATK (inferior esquerda) / DEF (inferior direita)
        draw_label_on_card(card, pad, ch - ah - pad, aw, ah, texture=atk_tex)
        draw_label_on_card(card, cw - hw - pad, ch - hh - pad, hw, hh, texture=hp_tex)

    def draw_field_card_stats(card, sx, sy, sw, sh):
        d = getattr(card, "domain_card", None)
        if d is None or getattr(d, "card_type", "creature") != "creature":
            return
        pad = 4
        size = 18
        # bônus do elemento dominante do Nexus (espelha combat_handler.nexus_bonus)
        nb = 300 if (gs.nexus_element and getattr(d, "element", None) == gs.nexus_element) else 0
        atk_val = d.atk + nb
        def_val = d.hp + getattr(d, "def_temp", 0) + nb
        atk_col = (0.45, 1.0, 1.0, 1.0) if nb else _atk_color(d)
        def_col = (0.45, 1.0, 1.0, 1.0) if nb else _def_color(d)
        atk_tex, aw, ah = text.get(str(atk_val), size, atk_col)
        hp_tex,  hw, hh = text.get(str(def_val), size, def_col)
        bar_h = max(ah, hh) + pad * 2
        bar_y = sy + sh - bar_h
        fill_rect(sx, bar_y, sw, bar_h, (0.0, 0.0, 0.0, 0.62))
        glUniform1i(use_texture_loc, 1)
        draw_texture_rect(sx + pad,           bar_y + pad, aw, ah, atk_tex)
        draw_texture_rect(sx + sw - hw - pad, bar_y + pad, hw, hh, hp_tex)
        if getattr(d, "evolved", False):
            draw_text("EV", sx + sw - 6, sy + 4, 18, (1.0, 0.85, 0.1, 1.0), anchor="topright")
        # indicador de debuff ativo: símbolo vermelho no canto superior esquerdo
        from nexus.domain.abilities.implementations import is_debuffed as _is_debuffed
        if _is_debuffed(d):
            draw_text("!", sx + 5, sy + 4, 18, (1.0, 0.25, 0.25, 1.0), anchor="topleft")

    def draw_button(rect, label, enabled=True, base=(0.16, 0.16, 0.22, 0.92), accent=(0.35, 0.45, 0.7, 1.0)):
        x, y, w, h = rect
        if enabled:
            fill_rect(x, y, w, h, base)
            fill_rect(x, y, 6, h, accent)
            txt_color = (1.0, 1.0, 1.0, 1.0)
        else:
            fill_rect(x, y, w, h, (0.1, 0.1, 0.12, 0.7))
            txt_color = (0.5, 0.5, 0.55, 1.0)
        draw_text(label, x + w / 2 + 3, y + h / 2, 19, txt_color, anchor="center")

    # ============================================================
    # ESTADO DE INTERAÇÃO
    # ============================================================
    selected_card = None
    attacker_card = None
    tribute_pending = None   # visual Card aguardando confirmação de tributo
    tribute_selected = []    # visual Cards marcadas como sacrifício
    tribute_needed = 0       # quantos sacrifícios ainda faltam selecionar
    spell_targeting    = None   # visual Card feitiço aguardando seleção de alvo
    spell_target_phase = None   # "ally" | "enemy" — fase atual do targeting bifásico
    spell_ally_sel     = None   # domain_card do aliado selecionado na fase 1 (sacrifício)
    evolution_card = None    # visual Card cujo painel de evolução está aberto
    show_log = False         # toggle do overlay de logs da partida
    mouse_was_pressed = False
    space_was_pressed = False
    esc_was_pressed = False
    last_click_domain = None
    last_click_time = -10.0
    hero_used_turn = {0: -10, 1: -10}

    camera = TurnCamera(DESIGN_W, DESIGN_H)
    last_player_index = gs.current_player
    identity = glm.mat4(1.0)

    glClearColor(0.05, 0.05, 0.08, 1.0)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    finalizar_rect = (_hud_btn_x, 320, _hud_btn_w, 60)
    hero_rect = (_hud_btn_x, 392, _hud_btn_w, 60)
    log_rect = (_hud_btn_x, 630, _hud_btn_w, 52)
    mull_rect = (_hud_btn_x, 492, _hud_btn_w, 56)
    pronto_rect = (_hud_btn_x, 556, _hud_btn_w, 56)

    last_time = glfw.get_time()
    rebuild_after = None  # timestamp para rebuild_all() atrasado após animação de morte

    while not glfw.window_should_close(window):
        glfw.poll_events()

        # delta time e animações
        now = glfw.get_time()
        dt = now - last_time
        last_time = now
        scene3d.update(dt)

        # rebuild atrasado — aguarda animação de morte antes de atualizar os visuais
        if rebuild_after is not None and now >= rebuild_after:
            rebuild_all()
            rebuild_after = None

        engine.resolver.resolve(gs)
        if engine.apply_passive_if_needed(gs):
            rebuild_all()

        fb_w, fb_h = glfw.get_framebuffer_size(window)
        fb_w = max(1, fb_w)
        fb_h = max(1, fb_h)
        scale = min(fb_w / DESIGN_W, fb_h / DESIGN_H)
        vw = DESIGN_W * scale
        vh = DESIGN_H * scale
        vx = (fb_w - vw) / 2
        vy = (fb_h - vh) / 2
        glViewport(int(vx), int(vy), int(vw), int(vh))

        active_index = gs.current_player
        active_player = active_index + 1
        enemy_player = 2 if active_player == 1 else 1
        active_state = gs.players[active_index]
        mulligan_open = getattr(active_state, "mulligan_active", False)
        phase = gs.current_phase
        hero_ready = (gs.turn_count - hero_used_turn[active_index]) >= HERO_COOLDOWN_TURNS

        # fim de jogo
        game_over = None
        if gs.players[0].hp <= 0:
            game_over = "JOGADOR 2 (Mestre das Sombras) venceu!"
        elif gs.players[1].hp <= 0:
            game_over = "JOGADOR 1 (Guardião da Luz) venceu!"

        if active_index != last_player_index:
            scene3d.set_active_player(active_player)
            rebuild_layout()
            last_player_index = active_index
            attacker_card = None
            rebuild_all()

        camera.update()

        # mouse -> coords de design
        raw_x, raw_y = glfw.get_cursor_pos(window)
        win_w, win_h = glfw.get_window_size(window)
        sx = fb_w / max(1, win_w)
        sy = fb_h / max(1, win_h)
        dmx = (raw_x * sx - vx) / scale
        dmy = (raw_y * sy - vy) / scale
        world_mouse_x, world_mouse_y = camera.screen_to_world(dmx, dmy)

        mouse_pressed = glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS
        press_edge = mouse_pressed and not mouse_was_pressed
        release_edge = (not mouse_pressed) and mouse_was_pressed

        # teclado
        esc_pressed = glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS
        if esc_pressed and not esc_was_pressed:
            if evolution_card is not None:
                evolution_card = None
            elif spell_targeting is not None:
                spell_targeting = None
                spell_target_phase = None
                spell_ally_sel = None
                rebuild_all()
            elif tribute_pending is not None:
                tribute_pending = None
                tribute_selected.clear()
                tribute_needed = 0
            elif detail_card is not None:
                detail_card = None
            else:
                glfw.set_window_should_close(window, True)
        esc_was_pressed = esc_pressed

        space_pressed = glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS
        if space_pressed and not space_was_pressed and detail_card is None and not game_over:
            attacker_card = None
            advance_phase()
        space_was_pressed = space_pressed

        consumed = False

        if game_over:
            consumed = True
        elif detail_card is not None:
            if press_edge:
                # verificar botão EVOLUIR antes de fechar o zoom
                _evo_btn_clicked = False
                d_chk = getattr(detail_card, "domain_card", None)
                evo_chk = getattr(d_chk, "evolution", None) if d_chk else None
                if (evo_chk is not None
                        and not getattr(d_chk, "evolved", False)
                        and detail_card.state == "field"
                        and detail_card.owner == active_player):
                    _cost_chk = evo_chk.get("cost", 2)
                    if (getattr(active_state, "hero_id", None) == "lord_of_shadows"
                            and getattr(d_chk, "element", "") == "SHADOW"):
                        _cost_chk = max(1, _cost_chk - 1)
                    if active_state.mana >= _cost_chk and phase in MAIN_PHASES:
                        # mesmas coordenadas usadas para desenhar o botão
                        _dh_chk = min(860, DESIGN_H - 120)
                        _dw_chk = _dh_chk * (card_width / card_height)
                        _dx_chk = 60  # _margin
                        _dy_chk = (DESIGN_H - _dh_chk) // 2
                        _ebx = _dx_chk + _dw_chk / 2 - 120
                        _eby = _dy_chk + _dh_chk + 8
                        if _ebx <= dmx <= _ebx + 240 and _eby <= dmy <= _eby + 52:
                            evolution_card = detail_card
                            detail_card = None
                            _evo_btn_clicked = True
                if not _evo_btn_clicked:
                    detail_card = None
            consumed = True

        # botões de HUD
        if not consumed and press_edge:
            if point_in_rect(dmx, dmy, finalizar_rect):
                start = gs.current_player
                attacker_card = None
                guard = 0
                while gs.current_player == start and guard < 64:
                    advance_phase()
                    guard += 1
                consumed = True
            elif point_in_rect(dmx, dmy, hero_rect):
                if hero_ready and phase in MAIN_PHASES:
                    ok = engine.use_hero_ability(gs)
                    if ok:
                        engine.resolver.resolve(gs)
                        hero_used_turn[active_index] = gs.turn_count
                        rebuild_all()
                consumed = True
            elif point_in_rect(dmx, dmy, log_rect):
                show_log = not show_log
                consumed = True
            elif mulligan_open and point_in_rect(dmx, dmy, mull_rect):
                if engine.mulligan(active_index):
                    engine.resolver.resolve(gs)
                    rebuild_hand(active_player)
                consumed = True
            elif mulligan_open and point_in_rect(dmx, dmy, pronto_rect):
                engine.confirm_hand(active_index)
                consumed = True

        # carta sob o mouse (para detalhe e hover)
        card_under = None
        if not consumed:
            for c in reversed(cards):
                if not c.is_mouse_over(world_mouse_x, world_mouse_y):
                    continue
                if c.state == "field" or (c.state == "hand" and c.owner == active_player):
                    card_under = c
                    break

        # duplo-clique abre o detalhe (mão ou campo) — compara pela carta de domínio,
        # que é estável mesmo quando os objetos visuais são recriados (rebuild_all)
        if not consumed and press_edge and card_under is not None:
            now = glfw.get_time()
            dom = getattr(card_under, "domain_card", None)
            if dom is not None and dom is last_click_domain and (now - last_click_time) < DOUBLE_CLICK_SECONDS:
                detail_card = card_under
                consumed = True
            last_click_domain = dom
            last_click_time = now

        # ------- MODO TARGETING DE FEITIÇO -------
        if spell_targeting is not None and press_edge and not consumed:
            _spell_dom = getattr(spell_targeting, "domain_card", None)
            _spell_id  = getattr(_spell_dom, "id", "")
            clicked_f  = field_card_under(world_mouse_x, world_mouse_y)

            if spell_target_phase == "ally":
                if clicked_f is not None and clicked_f.owner == active_player:
                    if _spell_id == "banquete_profano":
                        # fase 1: guardar aliado e mudar para fase inimigo
                        spell_ally_sel     = clicked_f.domain_card
                        spell_target_phase = "enemy"
                        # sem rebuild_all — spell ainda não foi jogada
                    else:
                        # ritual_degeneracao e similares: 1 fase só
                        engine.play_card(_spell_dom, sacrifice_ally=clicked_f.domain_card)
                        engine.resolver.resolve(gs)
                        spell_targeting = None; spell_target_phase = None; spell_ally_sel = None
                        rebuild_all()
                else:
                    # clique inválido → cancela
                    spell_targeting = None; spell_target_phase = None; spell_ally_sel = None
                    rebuild_all()
                consumed = True

            elif spell_target_phase == "enemy":
                if clicked_f is not None and clicked_f.owner != active_player:
                    engine.play_card(_spell_dom,
                                     sacrifice_ally=spell_ally_sel,
                                     target_card=clicked_f.domain_card)
                    engine.resolver.resolve(gs)
                    spell_targeting = None; spell_target_phase = None; spell_ally_sel = None
                    rebuild_all()
                else:
                    # clique inválido → cancela
                    spell_targeting = None; spell_target_phase = None; spell_ally_sel = None
                    rebuild_all()
                consumed = True

        # ------- MODO TRIBUTO: seleção de sacrifício -------
        if tribute_pending is not None and press_edge and not consumed:
            clicked = field_card_under(world_mouse_x, world_mouse_y)
            # Aberração Costurada evoluída: pode sacrificar inimigos com DEF efetiva < 1000
            _active_doms = gs.players[active_player - 1].board.get_cards()
            _aberracao_evo = any(getattr(c, "aberracao_evolved", False) for c in _active_doms)
            _can_sacrifice = False
            if clicked is not None:
                if clicked.owner == active_player:
                    _can_sacrifice = True
                elif _aberracao_evo and clicked.domain_card is not None:
                    _eff_def = clicked.domain_card.hp + getattr(clicked.domain_card, "def_temp", 0)
                    _can_sacrifice = (_eff_def < 1000)
            if _can_sacrifice and clicked not in tribute_selected:
                tribute_selected.append(clicked)
                if len(tribute_selected) >= tribute_needed:
                    sac_domains = [c.domain_card for c in tribute_selected]
                    engine.play_card(tribute_pending.domain_card, sacrifice_targets=sac_domains)
                    engine.resolver.resolve(gs)
                    _bp = getattr(tribute_pending.domain_card, "board_position", None)
                    if isinstance(_bp, int):
                        scene3d.play_anim(("monster", active_player, _bp), "summon", 0.45)
                    tribute_pending = None
                    tribute_selected.clear()
                    tribute_needed = 0
                    rebuild_all()
                consumed = True
            elif clicked is None:
                # clique em zona vazia → cancelar tributo
                tribute_pending = None
                tribute_selected.clear()
                tribute_needed = 0
                consumed = True

        # ------- FASE DE BATALHA: seleção de atacante/alvo -------
        if not consumed and phase == Phase.BATTLE and press_edge:
            target = field_card_under(world_mouse_x, world_mouse_y)
            enemy_creatures = gs.players[enemy_player - 1].board.get_cards()
            if attacker_card is None:
                if target is not None and target.owner == active_player and not has_attacked(target):
                    attacker_card = target
                consumed = True
            else:
                if target is not None and target.owner == enemy_player:
                    # Guardião Radiante evoluído: força todos os ataques a ir para o guardião
                    enemy_doms = gs.players[enemy_player - 1].board.get_cards()
                    guardian = next((c for c in enemy_doms if getattr(c, "guardian_evolved", False)), None)
                    if guardian is not None and target.domain_card is not guardian:
                        pass  # clique inválido: só o guardião pode ser alvo
                    else:
                        # guardar keys e refs ANTES de resolver (board_position some após morte)
                        atk_key = ("monster", active_player,
                                   getattr(attacker_card.domain_card, "board_position", 0))
                        def_key = ("monster", enemy_player,
                                   getattr(target.domain_card, "board_position", 0))
                        atk_dom = attacker_card.domain_card
                        def_dom = target.domain_card
                        scene3d.play_anim(atk_key, "attack", 0.35)
                        engine.attack(atk_dom, def_dom)
                        engine.resolver.resolve(gs)
                        attacker_card = None
                        # detectar mortes e animar
                        all_board = gs.players[0].board.get_cards() + gs.players[1].board.get_cards()
                        deaths = []
                        for key, dom in [(atk_key, atk_dom), (def_key, def_dom)]:
                            if dom not in all_board:
                                # delay = duração do ataque; morte começa depois que ataque termina
                                scene3d.play_anim(key, "death", 0.40, delay=0.35)
                                deaths.append(key)
                        if deaths:
                            rebuild_after = glfw.get_time() + 0.80  # 0.35 ataque + 0.40 morte + 0.05 buffer
                        else:
                            rebuild_all()
                elif target is not None and target.owner == active_player and not has_attacked(target):
                    attacker_card = target  # troca de atacante
                elif not enemy_creatures and abs(world_mouse_y - (battle_y_for(enemy_player) + card_height / 2)) < card_height * 1.6:
                    atk_key = ("monster", active_player,
                               getattr(attacker_card.domain_card, "board_position", 0))
                    scene3d.play_anim(atk_key, "attack", 0.35)
                    engine.attack(attacker_card.domain_card, None)  # ataque direto
                    engine.resolver.resolve(gs)
                    attacker_card = None
                    rebuild_after = glfw.get_time() + 0.40
                else:
                    attacker_card = None  # cancela seleção
                consumed = True

        # ------- FASES PRINCIPAIS: arrastar da mão para invocar -------
        can_drag = (phase in MAIN_PHASES) and detail_card is None and not consumed
        hovered_card = card_under if (can_drag and card_under is not None and card_under.state == "hand") else None
        if selected_card is not None:
            hovered_card = None

        if press_edge and can_drag and selected_card is None and hovered_card is not None:
            selected_card = hovered_card
            selected_card.start_drag(world_mouse_x, world_mouse_y)
            cards.remove(selected_card)
            cards.append(selected_card)

        if mouse_pressed and selected_card is not None:
            selected_card.drag(world_mouse_x, world_mouse_y)

        if release_edge and selected_card is not None:
            domain = getattr(selected_card, "domain_card", None)
            is_creature = domain is not None and getattr(domain, "card_type", "creature") == "creature"
            # detectar se o drop foi próximo da zona de batalha
            cy = selected_card.current_y + selected_card.height / 2
            battle_cy = battle_y_for(active_player) + card_height / 2
            hand_cy   = hand_y_for(active_player)  + card_height / 2
            near_battle = abs(cy - battle_cy) <= abs(cy - hand_cy)

            if is_creature and near_battle:
                needs_trib = required_sacrifices(domain)
                allied_field = [c for c in cards if c.state == "field" and c.owner == active_player]
                if needs_trib == 0:
                    # invocação normal: snap para slot livre mais próximo
                    target_slot = resolve_drop_slot(selected_card, active_player)
                    if target_slot is not None:
                        engine.play_card(domain)
                        engine.resolver.resolve(gs)
                        _bp = getattr(domain, "board_position", None)
                        if isinstance(_bp, int):
                            scene3d.play_anim(("monster", active_player, _bp), "summon", 0.45)
                        rebuild_all()
                elif len(allied_field) >= needs_trib:
                    # entrar em modo tributo: aguarda o jogador clicar nas cartas a sacrificar
                    tribute_pending = selected_card
                    tribute_selected.clear()
                    tribute_needed = needs_trib
                # else: cartas aliadas insuficientes → drop ignorado
            elif (not is_creature and domain is not None
                    and getattr(domain, "card_type", "") == "spell"
                    and near_battle and phase in MAIN_PHASES):
                spell_id = getattr(domain, "id", "")
                if spell_id in SPELLS_NEEDING_ALLY_TARGET:
                    spell_targeting    = selected_card
                    spell_target_phase = "ally"
                    spell_ally_sel     = None
                elif spell_id in SPELLS_NEEDING_TARGET:
                    spell_targeting    = selected_card
                    spell_target_phase = "enemy"
                    spell_ally_sel     = None
                else:
                    # feitiço sem alvo: joga imediatamente
                    engine.play_card(domain)
                    engine.resolver.resolve(gs)
                    rebuild_all()
            else:
                rebuild_all()
            selected_card = None

        for card in cards:
            card.set_hover(card == hovered_card if selected_card is None else False)
            card.update()

        mouse_was_pressed = mouse_pressed

        # ============================================================
        # RENDER
        # ============================================================
        # fundo acompanha o elemento dominante (mundo "queimando" no Fogo, etc.)
        glClearColor(*ELEMENT_CLEAR.get(gs.nexus_element, DEFAULT_CLEAR))
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # ---- cena 3D (fundo da arena + cartas de campo) ----
        glEnable(GL_DEPTH_TEST)
        scene3d.render(gs.nexus_element)

        # cartas de campo: quads 3D texturizados sobre o plano
        field_cards_3d = []
        for card in cards:
            if card.state == "field":
                tex_id = texture_cache.get(card.card_id)
                if tex_id:
                    slot_idx = getattr(card, "slot_idx",
                                       getattr(card.domain_card, "board_position", 0))
                    field_cards_3d.append((tex_id, ("monster", card.owner, slot_idx), card.owner == 2))
        scene3d.render_field_cards(field_cards_3d)

        # overlays de combate em 3D (amarelo=atacante, preto=já atacou, vermelho=sacrifício)
        combat_overlays = []
        if phase == Phase.BATTLE and not game_over:
            for card in cards:
                if card.state == "field" and card.owner == active_player and has_attacked(card):
                    slot_idx = getattr(card.domain_card, "board_position", 0)
                    combat_overlays.append((("monster", card.owner, slot_idx), (0.0, 0.0, 0.0, 0.45)))
            if attacker_card is not None and attacker_card.state == "field":
                slot_idx = getattr(attacker_card.domain_card, "board_position", 0)
                combat_overlays.append((("monster", attacker_card.owner, slot_idx), (1.0, 1.0, 0.2, 0.28)))
        # overlays de tributo: vermelho nas cartas selecionadas para sacrifício
        for c in tribute_selected:
            slot_idx = getattr(c, "slot_idx", getattr(c.domain_card, "board_position", 0))
            combat_overlays.append((("monster", c.owner, slot_idx), (1.0, 0.15, 0.15, 0.55)))
        # overlays de targeting de feitiço
        if spell_targeting is not None:
            if spell_target_phase == "ally":
                # verde nos aliados elegíveis para sacrifício
                for _tg in cards:
                    if _tg.state == "field" and _tg.owner == active_player:
                        _ti = getattr(_tg, "slot_idx", getattr(_tg.domain_card, "board_position", 0))
                        combat_overlays.append((("monster", _tg.owner, _ti), (0.1, 0.9, 0.2, 0.55)))
            elif spell_target_phase == "enemy":
                # laranja nos inimigos elegíveis como alvo
                for _tg in cards:
                    if _tg.state == "field" and _tg.owner != active_player:
                        _ti = getattr(_tg, "slot_idx", getattr(_tg.domain_card, "board_position", 0))
                        combat_overlays.append((("monster", _tg.owner, _ti), (1.0, 0.4, 0.1, 0.55)))
        scene3d.render_field_overlays(combat_overlays)

        glDisable(GL_DEPTH_TEST)

        shader.use()
        projection = ortho(0, DESIGN_W, DESIGN_H, 0)
        glUniformMatrix4fv(projection_loc, 1, GL_FALSE, glm.value_ptr(projection))
        field_card_bounds = scene3d.get_field_card_bounds(DESIGN_W, DESIGN_H)

        # ---- cartas da mão (sem tint do mundo para evitar outline colorido) ----
        set_view(camera.get_view_matrix())
        set_tint(WHITE)
        glActiveTexture(GL_TEXTURE0)
        # blend + textura: pixels transparentes compõem naturalmente sobre o fundo 3D escuro
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glUniform1i(use_texture_loc, 1)
        for card in cards:
            if card.state != "field" and card.owner == active_player:
                card.draw(vao, model_loc, rotated=False)

        # stats: apenas mão do jogador ativo (cartas de campo são 3D — sem overlay 2D)
        set_tint(WHITE)
        for card in cards:
            if card.state != "field" and card.owner == active_player:
                draw_card_stats(card)

        # stats de campo 3D com fundo semi-transparente
        set_tint(WHITE)
        for card in cards:
            if card.state == "field":
                slot_idx = getattr(card.domain_card, "board_position", None)
                if slot_idx is None:
                    continue  # carta removida do board — aguardando animação de morte
                key = ("monster", card.owner, slot_idx)
                if key in field_card_bounds:
                    sx, sy, sw, sh = field_card_bounds[key]
                    draw_field_card_stats(card, sx, sy, sw, sh)

        # destaques de combate — apenas cartas da mão (campo usa render_field_overlays em 3D)
        if phase == Phase.BATTLE and not game_over:
            if attacker_card is not None and attacker_card.state != "field":
                card_overlay(attacker_card, (1.0, 1.0, 0.2, 0.28))

        # ---- HUD ----
        set_view(identity)

        draw_text("JOGADOR 1 — Guardião da Luz", 24, 18, 22, (1.0, 0.85, 0.4, 1.0))
        draw_text(f"LP {gs.players[0].hp}", 24, 48, 30, (1.0, 1.0, 1.0, 1.0))
        draw_text("JOGADOR 2 — Mestre das Sombras", DESIGN_W - 24, 18, 22, (0.78, 0.58, 1.0, 1.0), anchor="topright")
        draw_text(f"LP {gs.players[1].hp}", DESIGN_W - 24, 48, 30, (1.0, 1.0, 1.0, 1.0), anchor="topright")

        draw_text(f"TURNO {gs.turn_count}", board_center_x, 16, 24, (0.95, 0.95, 1.0, 1.0), anchor="topcenter")
        if gs.nexus_element:
            _el_name = ELEMENT_NAMES.get(gs.nexus_element, gs.nexus_element)
            _el_col = (1.0, 0.92, 0.5, 1.0) if gs.nexus_element == "LIGHT" else (0.8, 0.6, 1.0, 1.0)
            draw_text(f"ELEMENTO DOMINANTE: {_el_name}", board_center_x, 48, 20, _el_col, anchor="topcenter")

        phase_label = PHASE_NAMES.get(phase, str(phase))
        fill_rect(16, DESIGN_H - 150, 360, 134, (0.04, 0.04, 0.07, 0.82))
        fill_rect(16, DESIGN_H - 150, 8, 134, (0.4, 0.6, 1.0, 1.0))
        draw_text(f"Vez do Jogador {active_player}", 34, DESIGN_H - 142, 20, (0.82, 0.82, 0.92, 1.0))
        draw_text(phase_label, 34, DESIGN_H - 114, 30, (1.0, 0.95, 0.6, 1.0))
        draw_text(f"Mana {active_state.mana}/8", 34, DESIGN_H - 72, 22, (0.7, 0.85, 1.0, 1.0))
        if tribute_pending is not None:
            faltam = tribute_needed - len(tribute_selected)
            draw_text(
                f"TRIBUTO: clique em {faltam} carta(s) aliada(s) para sacrificar  [ESC = cancelar]",
                board_center_x, DESIGN_H // 2 - 60, 26, (1.0, 0.9, 0.2, 1.0), anchor="topcenter",
            )
        if spell_targeting is not None:
            _st_dom  = getattr(spell_targeting, "domain_card", None)
            _st_name = getattr(_st_dom, "name", "Feitiço") if _st_dom else "Feitiço"
            if spell_target_phase == "ally":
                _hint = f"{_st_name} — escolha um aliado para sacrificar  [ESC = cancelar]"
                _col  = (0.2, 1.0, 0.4, 1.0)
            else:
                _hint = f"{_st_name} — escolha o alvo do dano  [ESC = cancelar]"
                _col  = (1.0, 0.5, 0.2, 1.0)
            draw_text(_hint, board_center_x, DESIGN_H // 2 - 60, 26, _col, anchor="topcenter")
        if phase == Phase.BATTLE:
            hint = "Clique no alvo inimigo" if attacker_card is not None else "Clique numa criatura para atacar"
            draw_text(hint, 34, DESIGN_H - 42, 18, (1.0, 0.6, 0.5, 1.0))
        else:
            draw_text("[ESPAÇO] avançar fase", 34, DESIGN_H - 42, 18, (0.6, 0.7, 0.85, 1.0))

        draw_button(finalizar_rect, "FINALIZAR TURNO", base=(0.18, 0.12, 0.12, 0.92), accent=(0.9, 0.4, 0.2, 1.0))
        hero_label = "HABILIDADE DO HERÓI" if hero_ready else "HABILIDADE (recarregando)"
        draw_button(hero_rect, hero_label, enabled=hero_ready, base=(0.12, 0.12, 0.2, 0.92), accent=(0.5, 0.4, 0.95, 1.0))
        log_label = "FECHAR LOGS" if show_log else "VER LOGS"
        draw_button(log_rect, log_label, base=(0.05, 0.12, 0.08, 0.92), accent=(0.3, 0.9, 0.5, 1.0))

        # ---- tooltip do herói (hover sobre o botão) ----
        _hero_def = _get_hero(active_index)
        if _hero_def and point_in_rect(dmx, dmy, hero_rect):
            _act = _hero_def["active"]
            _pas = _hero_def["passive"]
            _tip_lines = [
                _hero_def["name"],
                "",
                f"ATIVO — {_act['name']}  ({_act['mana_cost']} mana · CD {_act['cooldown_turns']} turnos)",
                _act["description"],
                "",
                f"PASSIVO — {_pas['name']}",
                _pas["description"],
            ]
            _tip_w, _tip_h = 430, 220
            _tip_x = hero_rect[0] - _tip_w - 12
            _tip_y = hero_rect[1]
            fill_rect(_tip_x, _tip_y, _tip_w, _tip_h, (0.05, 0.04, 0.12, 0.96))
            fill_rect(_tip_x, _tip_y, 4, _tip_h, (0.55, 0.45, 0.95, 1.0))
            _ty = _tip_y + 14
            for _li, _line in enumerate(_tip_lines):
                if not _line:
                    _ty += 8
                    continue
                if _li == 0:
                    _tc = (0.88, 0.78, 1.0, 1.0)
                    _ts = 20
                elif "ATIVO" in _line or "PASSIVO" in _line:
                    _tc = (0.70, 0.85, 1.0, 0.95)
                    _ts = 16
                else:
                    _tc = (0.80, 0.80, 0.90, 0.88)
                    _ts = 15
                draw_text(_line, _tip_x + 14, _ty, _ts, _tc)
                _ty += _ts + 5

        if mulligan_open:
            draw_button(mull_rect, "TROCAR MÃO", base=(0.22, 0.15, 0.05, 0.95), accent=(0.95, 0.6, 0.1, 1.0))
            draw_button(pronto_rect, "PRONTO", base=(0.08, 0.2, 0.1, 0.95), accent=(0.1, 0.85, 0.35, 1.0))

        # ---- overlay de logs da partida ----
        if show_log:
            # prefixos internos do engine — irrelevantes para o jogador
            _SKIP = ("[Resolver]", "[PHASE]", "[END PHASE]", "[TRIGGER]")
            _log_entries = [e for e in gs.get_logs() if not e.startswith(_SKIP)][-28:]
            _lw, _lh = 860, 560
            _lx = (DESIGN_W - _lw) / 2
            _ly = (DESIGN_H - _lh) / 2
            fill_rect(_lx, _ly, _lw, _lh, (0.04, 0.06, 0.04, 0.96))
            fill_rect(_lx, _ly, 6, _lh, (0.3, 0.9, 0.5, 1.0))
            draw_text("LOGS DA PARTIDA", _lx + _lw / 2, _ly + 14, 22,
                      (0.6, 1.0, 0.7, 1.0), anchor="topcenter")
            _ey = _ly + 50
            for _entry in _log_entries:
                draw_text(_entry, _lx + 18, _ey, 14, (0.80, 0.90, 0.80, 0.92))
                _ey += 17

        # ---- painel de evolução ----
        if evolution_card is not None and not game_over:
            dom = evolution_card.domain_card
            evo = dom.evolution
            cost = evo.get("cost", 2)
            # passivo Mutação: Mestre das Sombras evolui criaturas Sombra com -1 mana
            if (getattr(active_state, "hero_id", None) == "lord_of_shadows"
                    and getattr(dom, "element", "") == "SHADOW"):
                cost = max(1, cost - 1)
            can_evolve = (
                not dom.evolved
                and active_state.mana >= cost
                and phase in MAIN_PHASES
                and dom.board_position is not None
                and evolution_card.owner == active_player
            )

            fill_rect(0, 0, DESIGN_W, DESIGN_H, (0.0, 0.0, 0.0, 0.72))

            pw, ph = 700, 400
            px = (DESIGN_W - pw) / 2
            py = (DESIGN_H - ph) / 2
            fill_rect(px, py, pw, ph, (0.08, 0.08, 0.14, 0.97))

            draw_text(f"Evolução — {dom.name}", DESIGN_W / 2, py + 20, 26, (1.0, 0.9, 0.3, 1.0), anchor="topcenter")
            draw_text(f"ATK:  {dom.atk}  →  {dom.atk + 600}", DESIGN_W / 2, py + 70, 22, (1.0, 1.0, 1.0, 1.0), anchor="topcenter")
            draw_text(f"HP:   {dom.hp}  →  {dom.hp + 600}", DESIGN_W / 2, py + 100, 22, (0.6, 1.0, 0.6, 1.0), anchor="topcenter")
            draw_text("Nova habilidade:", DESIGN_W / 2, py + 145, 18, (0.8, 0.8, 1.0, 1.0), anchor="topcenter")
            draw_text(evo.get("desc", ""), DESIGN_W / 2, py + 170, 17, (0.9, 0.9, 0.9, 1.0), anchor="topcenter")

            mana_color = (0.5, 1.0, 0.5, 1.0) if can_evolve else (1.0, 0.4, 0.4, 1.0)
            draw_text(f"Custo: {cost} mana  (disponível: {active_state.mana})", DESIGN_W / 2, py + 240, 20, mana_color, anchor="topcenter")

            _evo__hud_btn_w, _evo_btn_h = 220, 50
            _evo__hud_btn_x = DESIGN_W / 2 - _evo__hud_btn_w / 2
            _evo_btn_y = py + ph - 80
            _evo_btn_color = (0.15, 0.55, 0.15, 0.95) if can_evolve else (0.25, 0.25, 0.25, 0.8)
            fill_rect(_evo__hud_btn_x, _evo_btn_y, _evo__hud_btn_w, _evo_btn_h, _evo_btn_color)
            draw_text("EVOLUIR", DESIGN_W / 2, _evo_btn_y + 12, 22, (1.0, 1.0, 1.0, 1.0), anchor="topcenter")

            if press_edge and not consumed and can_evolve and _evo__hud_btn_x <= dmx <= _evo__hud_btn_x + _evo__hud_btn_w and _evo_btn_y <= dmy <= _evo_btn_y + _evo_btn_h:
                engine.evolve_card(dom)
                engine.resolver.resolve(gs)
                evolution_card = None
                rebuild_all()
                consumed = True
            elif press_edge and not consumed and not (px <= dmx <= px + pw and py <= dmy <= py + ph):
                evolution_card = None
                consumed = True

        # ---- detalhe da carta ----
        if detail_card is not None:
            fill_rect(0, 0, DESIGN_W, DESIGN_H, (0.0, 0.0, 0.0, 0.85))
            # Layout: carta à esquerda (~35%), painel de info à direita (~60%)
            _margin   = 60
            _gap      = 50
            dh        = min(860, DESIGN_H - 120)
            dw        = dh * (card_width / card_height)
            dx        = _margin
            dy        = (DESIGN_H - dh) // 2

            draw_texture_rect(dx, dy, dw, dh, detail_card.texture)

            d = getattr(detail_card, "domain_card", None)

            # painel de informação — ocupa o espaço à direita da carta
            panel_x = dx + dw + _gap
            panel_y = dy
            panel_w = DESIGN_W - panel_x - _margin
            panel_h = dh
            panel_bottom = panel_y + panel_h

            fill_rect(panel_x - 12, panel_y, panel_w + 12, panel_h,
                      (0.05, 0.05, 0.10, 0.75))

            if d is not None:
                max_chars = max(24, int(panel_w / 11.5))
                lh = 27
                cy = panel_y + 16

                def _sep():
                    nonlocal cy
                    if cy + 8 < panel_bottom:
                        fill_rect(panel_x - 4, cy + 3, panel_w + 4, 2,
                                  (1.0, 1.0, 1.0, 0.18))
                        cy += 14

                def _row(txt, size=19, color=(0.9, 0.9, 0.9, 1.0)):
                    nonlocal cy
                    if cy + size < panel_bottom:
                        draw_text(txt, panel_x, cy, size, color)
                        cy += lh

                def _section(title, color):
                    nonlocal cy
                    _sep()
                    _row(title, 20, color)
                    _sep()

                def _wrapped(text, size=18, color=(0.88, 0.88, 0.88, 1.0)):
                    nonlocal cy
                    for line in _wrap_text(text, max_chars):
                        if cy + size >= panel_bottom:
                            break
                        draw_text(line, panel_x, cy, size, color)
                        cy += size + 8

                is_creature = getattr(d, "card_type", "creature") == "creature"
                _ddef = d.hp + getattr(d, "def_temp", 0)

                # ── Cabeçalho: nome ──────────────────────────────────────────
                _row(d.name, 28, (1.0, 0.95, 0.7, 1.0))

                # ── Tipo / Nível / Elemento ──────────────────────────────────
                if is_creature:
                    _row(f"Criatura  •  Nível {d.level}  •  {d.element}",
                         20, (0.75, 0.85, 1.0, 1.0))
                else:
                    _row(f"Feitiço  •  {d.element}  •  Custo: {d.cost_mana} mana",
                         20, (0.75, 0.85, 1.0, 1.0))

                _sep()

                # ── Estatísticas ─────────────────────────────────────────────
                if is_creature:
                    # ATK — mostra base se foi modificado
                    _base_atk = getattr(d, "base_atk", d.atk)
                    if d.atk != _base_atk:
                        _row(f"ATK:  {d.atk}  (base: {_base_atk})",
                             20, _atk_color(d))
                    else:
                        _row(f"ATK:  {d.atk}", 20, _atk_color(d))

                    # DEF (hp + def_temp) + HP bruto
                    _dtemp = getattr(d, "def_temp", 0)
                    if _dtemp != 0:
                        _sign = "+" if _dtemp > 0 else ""
                        _row(f"DEF:  {_ddef}  (HP: {d.hp}  buff: {_sign}{_dtemp})",
                             20, _def_color(d))
                    else:
                        _row(f"DEF:  {_ddef}  (HP: {d.hp})", 20, _def_color(d))

                # ── Descrição de efeitos ─────────────────────────────────────
                _desc_txt = getattr(d, "desc", "")
                if _desc_txt:
                    _section("Efeitos", (1.0, 0.9, 0.4, 1.0))
                    _wrapped(_desc_txt, 18, (0.95, 0.92, 0.82, 1.0))

                # ── Evolução ─────────────────────────────────────────────────
                _evo = getattr(d, "evolution", None)
                _evo_desc = _evo.get("desc", "") if _evo else ""
                if _evo_desc:
                    _evolved = getattr(d, "evolved", False)
                    _evo_cost = _evo.get("cost", 2)
                    _evo_title = ("Evolução  [JÁ EVOLUÍDA]"
                                  if _evolved
                                  else f"Evolução  ({_evo_cost} mana)")
                    _evo_color = ((0.4, 1.0, 0.7, 1.0)
                                  if _evolved
                                  else (0.45, 1.0, 0.75, 1.0))
                    _section(_evo_title, _evo_color)
                    _wrapped(_evo_desc, 18, (0.75, 0.95, 0.85, 1.0))

                # ── Status em jogo ───────────────────────────────────────────
                _status = []
                # ATK debuff (weaken_enemy — redução permanente abaixo da base)
                _base_atk_s = getattr(d, "base_atk", d.atk)
                if d.atk > _base_atk_s:
                    _status.append((f"ATK  +{d.atk - _base_atk_s}  (buff permanente)",
                                    (0.5, 1.0, 0.5, 1.0)))
                elif d.atk < _base_atk_s:
                    _status.append((f"ATK  -{_base_atk_s - d.atk}  (debuff permanente)",
                                    (1.0, 0.45, 0.45, 1.0)))
                # DEF buff/debuff (def_temp)
                _dtemp_s = getattr(d, "def_temp", 0)
                if _dtemp_s > 0:
                    _status.append((f"DEF  +{_dtemp_s}  (buff permanente)",
                                    (0.5, 1.0, 0.5, 1.0)))
                elif _dtemp_s < 0:
                    _status.append((f"DEF  {_dtemp_s}  (debuff)",
                                    (1.0, 0.45, 0.45, 1.0)))
                if getattr(d, "silenced", False):
                    _status.append(("Silenciada — sem ativação de efeitos",
                                    (0.9, 0.5, 0.9, 1.0)))
                if getattr(d, "protected", False):
                    _status.append(("Protegida — próximo ataque bloqueado",
                                    (0.4, 0.8, 1.0, 1.0)))
                _imm = getattr(d, "immune_turns", 0)
                if _imm > 0:
                    _status.append((f"Imune por {_imm} turno(s)",
                                    (0.4, 0.8, 1.0, 1.0)))
                _ctick = getattr(d, "corruption_ticks", 0)
                if _ctick > 0:
                    _status.append((f"Corrupção Progressiva: -{200} DEF/turno  ({_ctick} turnos restantes)",
                                    (0.8, 0.4, 1.0, 1.0)))
                if getattr(d, "can_attack_twice", False):
                    _status.append(("Pode atacar 2× por turno",
                                    (1.0, 0.85, 0.3, 1.0)))
                if getattr(d, "guardian_evolved", False):
                    _status.append(("Guardião: aliados não podem ser alvejados",
                                    (0.5, 0.9, 1.0, 1.0)))
                if getattr(d, "aberracao_evolved", False):
                    _status.append(("Pode sacrificar inimigos com DEF < 1000",
                                    (0.9, 0.6, 1.0, 1.0)))
                if getattr(d, "horror_evolved", False):
                    _status.append(("Debuffs causam dano direto (+100)",
                                    (0.8, 0.45, 0.8, 1.0)))
                if getattr(d, "has_attacked", False):
                    _status.append(("Já atacou neste turno",
                                    (0.6, 0.6, 0.6, 1.0)))
                if _status:
                    _section("Status em jogo", (1.0, 0.55, 0.55, 1.0))
                    for _stxt, _scol in _status:
                        _row(_stxt, 18, _scol)

            # dica de fechar
            draw_text("Clique ou ESC para fechar", panel_x + panel_w / 2,
                      panel_y + panel_h + 10, 17, (0.65, 0.65, 0.75, 1.0),
                      anchor="topcenter")
            # botão EVOLUIR — só para carta de campo evoluível do dono ativo
            d_evo = getattr(detail_card, "domain_card", None)
            evo = getattr(d_evo, "evolution", None) if d_evo else None
            if (evo is not None
                    and not getattr(d_evo, "evolved", False)
                    and detail_card.state == "field"
                    and detail_card.owner == active_player):
                cost = evo.get("cost", 2)
                # passivo Mutação: Mestre das Sombras evolui criaturas Sombra com -1 mana
                if (getattr(active_state, "hero_id", None) == "lord_of_shadows"
                        and getattr(d_evo, "element", "") == "SHADOW"):
                    cost = max(1, cost - 1)
                can_evo = active_state.mana >= cost and phase in MAIN_PHASES
                e_hud_btn_w, ebtn_h = 240, 52
                # centralizado abaixo da arte da carta
                e_hud_btn_x = dx + dw / 2 - e_hud_btn_w / 2
                ebtn_y = dy + dh + 8
                ebtn_color = (0.15, 0.55, 0.15, 0.95) if can_evo else (0.25, 0.25, 0.25, 0.85)
                fill_rect(e_hud_btn_x, ebtn_y, e_hud_btn_w, ebtn_h, ebtn_color)
                draw_text(f"EVOLUIR  ({cost} mana)",
                          e_hud_btn_x + e_hud_btn_w / 2, ebtn_y + 13, 22,
                          (1.0, 1.0, 1.0, 1.0), anchor="topcenter")

        # ---- fim de jogo ----
        if game_over:
            fill_rect(0, 0, DESIGN_W, DESIGN_H, (0.0, 0.0, 0.0, 0.82))
            draw_text("FIM DE JOGO", DESIGN_W / 2, DESIGN_H / 2 - 80, 60, (1.0, 0.9, 0.4, 1.0), anchor="center")
            draw_text(game_over, DESIGN_W / 2, DESIGN_H / 2 + 10, 34, (1.0, 1.0, 1.0, 1.0), anchor="center")
            draw_text("ESC para sair", DESIGN_W / 2, DESIGN_H / 2 + 70, 22, (0.7, 0.7, 0.8, 1.0), anchor="center")

        glfw.swap_buffers(window)

    glDeleteVertexArrays(1, [vao])
    glDeleteBuffers(1, [vbo])
    glDeleteBuffers(1, [ebo])
    scene3d.delete()
    glfw.terminate()
