from enum import Enum, auto

class EventType(Enum):
    # Turno
    TURN_START = auto()
    TURN_END = auto()
    PHASE_CHANGED = auto()

    # Fases
    DRAW_PHASE = auto()
    NEXUS_PHASE = auto()
    MANA_PHASE = auto()
    END_PHASE = auto()

    # Nexus
    NEXUS_CHANGED = auto()

    # Combate
    ATTACK = auto()
    DAMAGE = auto()

    # Cartas
    SUMMON = auto()
    SUMMON_REQUEST = auto()
    DEATH = auto()
    SACRIFICE = auto()
    CAST = auto()

    # Sistema
    DRAW = auto()

    # Abilities
    TRIGGER_ABILITY = auto()
    
    
