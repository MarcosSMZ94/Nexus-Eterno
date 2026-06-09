import math
from pathlib import Path
import glm
from OpenGL.GL import *

from nexus.presentation.gl.mesh import load_obj, Mesh
from nexus.presentation.gl.texture import load_texture
from nexus.presentation.gl.shader import Shader



_ELEMENT_TINT = {
    "FIRE":  (1.0, 0.78, 0.65, 1.0),
    "WATER": (0.65, 0.83, 1.0,  1.0),
    "EARTH": (0.75, 1.0,  0.72, 1.0),
    "AIR":   (0.88, 0.94, 1.0,  1.0),
}

# 12 slots no plano (y=0.01): 3 monstros + 3 magias por jogador
# separação de 4 unidades entre linhas — acomoda carta W=2.5, H=3.75 sem sobreposição
_SLOT_WORLD = {
    ("spell",   1, 0): (-3.5, 0.01,  6.5),   # spell: mais perto de P1
    ("spell",   1, 1): ( 0.0, 0.01,  6.5),
    ("spell",   1, 2): ( 3.5, 0.01,  6.5),
    ("monster", 1, 0): (-3.5, 0.01,  2.5),   # monster: entre spell e centro
    ("monster", 1, 1): ( 0.0, 0.01,  2.5),
    ("monster", 1, 2): ( 3.5, 0.01,  2.5),
    ("monster", 2, 0): (-3.5, 0.01, -2.5),
    ("monster", 2, 1): ( 0.0, 0.01, -2.5),
    ("monster", 2, 2): ( 3.5, 0.01, -2.5),
    ("spell",   2, 0): (-3.5, 0.01, -6.5),   # spell: mais perto de P2
    ("spell",   2, 1): ( 0.0, 0.01, -6.5),
    ("spell",   2, 2): ( 3.5, 0.01, -6.5),
}

_SLOT_COLORS = {
    "monster": (0.05, 0.40, 0.12, 0.45),   # verde
    "spell":   (0.10, 0.20, 0.55, 0.45),   # azul
}

# câmera fixa: ~35° de elevação, campo claramente visível como mesa em perspectiva
_EYE = glm.vec3(0.0, 11.5, 17.0)
_AT  = glm.vec3(0.0, 0.0,  0.0)
_UP  = glm.vec3(0.0, 1.0,  0.0)


class Scene3D:
    """Renderiza o fundo 3D da arena antes do pass 2D das cartas."""

    def __init__(self, base_dir: Path):
        shaders_dir = base_dir / "gl" / "shaders"
        self._shader = Shader(
            str(shaders_dir / "vertex_3d.glsl"),
            str(shaders_dir / "fragment_3d.glsl"),
        )

        models_dir = base_dir / "assets" / "3dmodels"
        self._meshes   = {}
        self._textures = {}

        for name in ("plano", "ilhas", "sun", "shadow"):
            p = models_dir / f"{name}.obj"
            if p.exists():
                try:
                    self._meshes[name] = load_obj(p)
                except Exception as exc:
                    print(f"[3D] falha ao carregar {name}.obj: {exc}")

        for name, tex_file in (("sun", "suntex.png"), ("shadow", "shadowtex.png"),
                               ("plano", "plantex.png")):
            tex_path = models_dir / tex_file
            if tex_path.exists():
                self._textures[name] = load_texture(str(tex_path))

        self._proj = glm.perspective(glm.radians(58.0), 16.0 / 9.0, 0.1, 100.0)
        self._view = glm.lookAt(_EYE, _AT, _UP)

        # uniforms de iluminação (constantes — só precisam ser enviados uma vez)
        s = self._shader
        s.use()
        sid = s.id
        glUniform1i(glGetUniformLocation(sid, "diffuseTexture"), 0)
        ld = glm.normalize(glm.vec3(1.0, 2.5, 1.5))
        glUniform3f(glGetUniformLocation(sid, "lightDir"),   ld.x,    ld.y,    ld.z)
        glUniform3f(glGetUniformLocation(sid, "lightColor"), 1.0,     0.95,    0.88)
        glUniform1f(glGetUniformLocation(sid, "ambientStr"), 0.35)
        glUniform3f(glGetUniformLocation(sid, "viewPos"),    0.0,     11.5,    17.0)

        # quad plano para marcadores de slot (xz, proporção próxima à carta)
        _sw, _sd = 3.5, 3.0
        _sv = [
            -_sw/2, 0.0, -_sd/2,  0.0, 1.0, 0.0,  0.0, 1.0,
             _sw/2, 0.0, -_sd/2,  0.0, 1.0, 0.0,  1.0, 1.0,
             _sw/2, 0.0,  _sd/2,  0.0, 1.0, 0.0,  1.0, 0.0,
            -_sw/2, 0.0,  _sd/2,  0.0, 1.0, 0.0,  0.0, 0.0,
        ]
        self._slot_quad = Mesh(_sv, [0, 1, 2, 0, 2, 3])

        # quad de carta deitada (xz, razão 2:3) — UV (0,0) = topo da carta
        _cw, _ch = 2.5, 3.75
        _cv = [
            -_cw/2, 0.0, -_ch/2,  0.0, 1.0, 0.0,  0.0, 1.0,   # far-left  → topo da carta
             _cw/2, 0.0, -_ch/2,  0.0, 1.0, 0.0,  1.0, 1.0,   # far-right → topo
             _cw/2, 0.0,  _ch/2,  0.0, 1.0, 0.0,  1.0, 0.0,   # near-right → base
            -_cw/2, 0.0,  _ch/2,  0.0, 1.0, 0.0,  0.0, 0.0,   # near-left  → base
        ]
        self._card_quad = Mesh(_cv, [0, 2, 1,  0, 3, 2])

        # animações ativas: slot_key → {"type": str, "t": float, "dur": float}
        self._anims = {}

    # ------------------------------------------------------------------
    def play_anim(self, slot_key, anim_type, duration=0.5, delay=0.0):
        """Inicia animação para uma carta de campo.

        Se delay > 0 e já existe animação ativa para o slot, enfileira como _next
        (não sobrescreve — a animação atual termina antes de começar a próxima).
        Isso permite sequenciar ataque→morte no mesmo frame sem perder o ataque.
        """
        if delay > 0 and slot_key in self._anims:
            self._anims[slot_key]["_next"] = {"type": anim_type, "dur": duration}
        else:
            self._anims[slot_key] = {"type": anim_type, "t": 0.0, "dur": duration, "delay": delay}

    def update(self, dt):
        """Avança todas as animações. Retorna conjunto de slot_keys concluídos."""
        done = set()
        for key, anim in list(self._anims.items()):
            if anim.get("delay", 0) > 0:
                anim["delay"] = max(0.0, anim["delay"] - dt)
            else:
                anim["t"] = min(1.0, anim["t"] + dt / anim["dur"])
                if anim["t"] >= 1.0:
                    if "_next" in anim:
                        nxt = anim["_next"]
                        self._anims[key] = {"type": nxt["type"], "t": 0.0, "dur": nxt["dur"]}
                    else:
                        done.add(key)
        for key in done:
            del self._anims[key]
        return done

    # ------------------------------------------------------------------
    def render_field_cards(self, cards_info):
        """Renderiza cartas de campo como quads 3D texturizados sobre o plano.

        cards_info: lista de (texture_id, slot_key, flip)
        flip=True para P2 (carta rotacionada 180° em Y).
        """
        if not cards_info:
            return
        s = self._shader
        s.use()
        sid = s.id
        glUniformMatrix4fv(glGetUniformLocation(sid, "projection"), 1, GL_FALSE, glm.value_ptr(self._proj))
        glUniformMatrix4fv(glGetUniformLocation(sid, "view"),       1, GL_FALSE, glm.value_ptr(self._view))
        glUniform4f(glGetUniformLocation(sid, "tint"), 1.0, 1.0, 1.0, 1.0)
        glUniform1i(glGetUniformLocation(sid, "useTexture"), 1)
        glActiveTexture(GL_TEXTURE0)

        # blend necessário para fade-out na animação de morte
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        for tex_id, slot_key, flip in cards_info:
            if slot_key not in _SLOT_WORLD:
                continue
            wx, wy, wz = _SLOT_WORLD[slot_key]
            m = glm.translate(glm.mat4(1.0), glm.vec3(wx, wy + 0.02, wz))
            if flip:
                m = glm.rotate(m, glm.radians(180.0), glm.vec3(0.0, 1.0, 0.0))

            # animação do slot (só aplica quando delay já passou)
            anim_tint = (1.0, 1.0, 1.0, 1.0)
            anim = self._anims.get(slot_key)
            if anim and anim.get("delay", 0) <= 0:
                t = anim["t"]
                atype = anim["type"]
                if atype == "summon":
                    # ease-out-back: começa em 0 com leve overshoot até 1
                    c1 = 1.70158
                    raw = 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2
                    sc = max(0.001, raw)
                    m = glm.scale(m, glm.vec3(sc, 1.0, sc))
                    # flash branco na chegada
                    b = 1.0 + max(0.0, 0.5 - t) * 0.6
                    anim_tint = (min(b, 2.0), min(b, 2.0), min(b, 2.0), 1.0)
                elif atype == "attack":
                    # surge: sobe em Y e avança em Z em direção ao inimigo
                    progress = math.sin(t * math.pi)  # 0 → pico → 0
                    owner = slot_key[1]
                    dz = progress * 2.5 * (-1 if owner == 1 else 1)
                    dy = progress * 1.2
                    m = glm.translate(m, glm.vec3(0.0, dy, dz))
                    # flash amarelo no pico
                    anim_tint = (1.0, 1.0, 1.0 - progress * 0.5, 1.0)
                elif atype == "death":
                    # encolhe e fica vermelho antes de sumir
                    sc = max(0.001, 1.0 - t)
                    m = glm.scale(m, glm.vec3(sc, 1.0, sc))
                    anim_tint = (1.0, 1.0 - t, 1.0 - t, max(0.1, 1.0 - t))

            glUniform4f(glGetUniformLocation(sid, "tint"), *anim_tint)
            glUniformMatrix4fv(glGetUniformLocation(sid, "model"), 1, GL_FALSE, glm.value_ptr(m))
            glBindTexture(GL_TEXTURE_2D, tex_id)
            self._card_quad.draw()

        # restaurar estado após o loop
        glDisable(GL_BLEND)
        glUniform4f(glGetUniformLocation(sid, "tint"), 1.0, 1.0, 1.0, 1.0)

    # ------------------------------------------------------------------
    def render_field_overlays(self, overlays_info):
        """Overlay semitransparente sobre cartas de campo (combate: amarelo=atacante, preto=atacou)."""
        if not overlays_info:
            return
        s = self._shader
        s.use()
        sid = s.id
        glUniformMatrix4fv(glGetUniformLocation(sid, "projection"), 1, GL_FALSE, glm.value_ptr(self._proj))
        glUniformMatrix4fv(glGetUniformLocation(sid, "view"),       1, GL_FALSE, glm.value_ptr(self._view))
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glUniform1i(glGetUniformLocation(sid, "useTexture"), 0)
        glUniform4f(glGetUniformLocation(sid, "tint"), 1.0, 1.0, 1.0, 1.0)
        for slot_key, color in overlays_info:
            if slot_key not in _SLOT_WORLD:
                continue
            wx, wy, wz = _SLOT_WORLD[slot_key]
            m = glm.translate(glm.mat4(1.0), glm.vec3(wx, wy + 0.04, wz))
            glUniformMatrix4fv(glGetUniformLocation(sid, "model"), 1, GL_FALSE, glm.value_ptr(m))
            glUniform4f(glGetUniformLocation(sid, "solidColor"), *color)
            self._card_quad.draw()
        glDisable(GL_BLEND)

    # ------------------------------------------------------------------
    def set_active_player(self, player: int):
        """Atualiza câmera para a perspectiva do jogador ativo (1 ou 2)."""
        eye = glm.vec3(0.0, 11.5, 17.0) if player == 1 else glm.vec3(0.0, 11.5, -17.0)
        self._view = glm.lookAt(eye, _AT, _UP)
        self._shader.use()
        glUniform3f(glGetUniformLocation(self._shader.id, "viewPos"), eye.x, eye.y, eye.z)

    # ------------------------------------------------------------------
    def get_slot_screen_positions(self, design_w, design_h):
        """Projeta os 12 centros de slot do mundo 3D para coordenadas de design 2D.

        Retorna dict (zone, owner, idx) → (cx, cy) em coordenadas de design.
        """
        result = {}
        for key, (wx, wy, wz) in _SLOT_WORLD.items():
            clip = self._proj * self._view * glm.vec4(wx, wy, wz, 1.0)
            sx = (clip.x / clip.w + 1.0) * 0.5 * design_w
            sy = (1.0 - clip.y / clip.w) * 0.5 * design_h
            result[key] = (sx, sy)
        return result

    # ------------------------------------------------------------------
    def get_field_card_bounds(self, design_w, design_h):
        """Projeta os 4 cantos de cada card quad para coordenadas de design.

        Retorna dict (zone, owner, idx) → (sx, sy, sw, sh):
          sx/sy = canto superior-esquerdo em design pixels
          sw/sh = largura/altura projetada em design pixels
        """
        _cw, _ch = 2.5, 3.75
        result = {}
        for key, (wx, wy, wz) in _SLOT_WORLD.items():
            corners = [
                (wx - _cw/2, wy, wz - _ch/2),
                (wx + _cw/2, wy, wz - _ch/2),
                (wx + _cw/2, wy, wz + _ch/2),
                (wx - _cw/2, wy, wz + _ch/2),
            ]
            xs, ys = [], []
            for (cx, cy, cz) in corners:
                clip = self._proj * self._view * glm.vec4(cx, cy, cz, 1.0)
                xs.append((clip.x / clip.w + 1.0) * 0.5 * design_w)
                ys.append((1.0 - clip.y / clip.w) * 0.5 * design_h)
            sx, sy = min(xs), min(ys)
            result[key] = (sx, sy, max(xs) - sx, max(ys) - sy)
        return result

    # ------------------------------------------------------------------
    def render(self, nexus_element=None):
        s = self._shader
        s.use()
        sid = s.id

        tint = _ELEMENT_TINT.get(nexus_element, (1.0, 1.0, 1.0, 1.0))
        glUniform4f(glGetUniformLocation(sid, "tint"), *tint)
        glUniformMatrix4fv(glGetUniformLocation(sid, "projection"), 1, GL_FALSE, glm.value_ptr(self._proj))
        glUniformMatrix4fv(glGetUniformLocation(sid, "view"),       1, GL_FALSE, glm.value_ptr(self._view))

        # plano da arena
        if "plano" in self._textures:
            self._draw_tex("plano", glm.mat4(1.0))
        else:
            self._draw("plano", glm.mat4(1.0), color=(0.14, 0.19, 0.24, 1.0))

        # ilhas decorativas nos 4 cantos da arena
        _island_color = (0.30, 0.25, 0.20, 1.0)
        for _ix, _iz in ((-8.0, 8.0), (8.0, 8.0), (-8.0, -8.0), (8.0, -8.0)):
            _mi = glm.translate(glm.mat4(1.0), glm.vec3(_ix, 0.0, _iz))
            self._draw("ilhas", _mi, color=_island_color)

        # mascotes
        glUniform4f(glGetUniformLocation(sid, "tint"), 1.0, 1.0, 1.0, 1.0)
        m_sun    = glm.scale(glm.translate(glm.mat4(1.0), glm.vec3(-7.0, 0.0,  2.5)), glm.vec3(0.3,  0.3,  0.3 ))
        m_shadow = glm.scale(glm.translate(glm.mat4(1.0), glm.vec3( 7.0, 2.0, -2.5)), glm.vec3(0.65, 0.65, 0.65))
        self._draw_tex("sun",    m_sun)
        self._draw_tex("shadow", m_shadow)

    # ------------------------------------------------------------------
    def _draw(self, name, model, *, color):
        if name not in self._meshes:
            return
        sid = self._shader.id
        glUniformMatrix4fv(glGetUniformLocation(sid, "model"), 1, GL_FALSE, glm.value_ptr(model))
        glUniform1i(glGetUniformLocation(sid, "useTexture"), 0)
        glUniform4f(glGetUniformLocation(sid, "solidColor"), *color)
        self._meshes[name].draw()

    def _draw_tex(self, name, model):
        if name not in self._meshes or name not in self._textures:
            return
        sid = self._shader.id
        glUniformMatrix4fv(glGetUniformLocation(sid, "model"), 1, GL_FALSE, glm.value_ptr(model))
        glUniform1i(glGetUniformLocation(sid, "useTexture"), 1)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self._textures[name])
        self._meshes[name].draw()

    def delete(self):
        for m in self._meshes.values():
            m.delete()
        self._slot_quad.delete()
        self._card_quad.delete()
        for t in self._textures.values():
            glDeleteTextures(1, [t])
