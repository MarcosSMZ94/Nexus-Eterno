"""Constantes de layout, fases e visual do jogo — importadas por window.py e outros módulos."""
from nexus.domain.turn.phase import Phase

# resolução virtual de design: layout em coords fixas, projetado via viewport letterbox
DESIGN_W = 1920
DESIGN_H = 1080
TITLE = "Nexus Eterno"

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

AUTO_PHASES  = {Phase.DRAW, Phase.NEXUS, Phase.MANA, Phase.END}
MAIN_PHASES  = {Phase.MAIN_1, Phase.MAIN_2}

SPELLS_NEEDING_TARGET      = {"corrupcao_progressiva", "miniatura_sol_ardente"}
SPELLS_NEEDING_ALLY_TARGET = {"ritual_degeneracao", "banquete_profano"}

PHASE_NAMES = {
    Phase.DRAW:   "Compra",
    Phase.NEXUS:  "Nexus",
    Phase.MANA:   "Mana",
    Phase.MAIN_1: "Fase Principal 1",
    Phase.BATTLE: "Fase de Batalha",
    Phase.MAIN_2: "Fase Principal 2",
    Phase.END:    "Fase Final",
}

HERO_NAMES          = ["Guardião da Luz", "Mestre das Sombras"]
HERO_COOLDOWN_TURNS = 3
DOUBLE_CLICK_SECONDS = 0.35

WHITE = (1.0, 1.0, 1.0, 1.0)

# iluminação ambiente do mundo conforme o elemento dominante do Nexus (LIGHT/SHADOW)
ELEMENT_TINT = {
    "LIGHT":  (1.0, 0.92, 0.62, 1.0),   # Luz dourada
    "SHADOW": (0.72, 0.55, 1.0,  1.0),  # Sombra arroxeada
}
ELEMENT_CLEAR = {
    "LIGHT":  (0.12, 0.10, 0.04, 1.0),
    "SHADOW": (0.07, 0.03, 0.12, 1.0),
}
ELEMENT_NAMES = {"LIGHT": "LUZ", "SHADOW": "SOMBRA"}
DEFAULT_CLEAR = (0.05, 0.05, 0.08, 1.0)
