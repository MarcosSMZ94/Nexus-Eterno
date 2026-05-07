from enum import Enum, auto

class Phase(Enum):
    DRAW = auto()
    NEXUS = auto()
    MANA = auto()
    MAIN_1 = auto()
    BATTLE = auto()
    MAIN_2 = auto()
    END = auto()