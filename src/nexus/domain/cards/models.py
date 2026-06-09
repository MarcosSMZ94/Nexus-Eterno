class Card:
    def __init__(self, id, name, level, atk, hp, element, card_type, abilities, cost_mana=0):
        self.id = id
        self.name = name
        self.level = level
        self.atk = atk
        self.hp = hp
        self.element = element
        self.card_type = card_type  # "creature" ou "spell"
        self.abilities = abilities  # lista de AbilityDefinition
        self.cost_mana = cost_mana
        self.board_position = None
        self.base_atk = atk  
        self.def_temp = 0
        self.has_attacked = False
        self.cycle_mode = 0
        self.immune_turns = 0
        self.silenced = False
        self.protected = False
        self._atk_per_ally_bonus = 0
        self._permanent_def_done = False
        self._buff_on_death_last = None
        self._scales_last_death = None
        self.evolution = None    # dict {"cost": int, "desc": str} ou None se não pode evoluir
        self.evolved = False     # True após evoluir (limite: 1 vez por criatura)
        self.desc = ""           # descrição dos efeitos da carta para o painel de detalhes
        self.corruption_ticks = 0      # turnos restantes de Corrupção Progressiva (-200 DEF/turno)
        self.can_attack_twice = False  # Abominação evoluída: ataca 2x por turno
        self.attacks_this_turn = 0     # contador de ataques no turno atual (reset no início do turno)

    def __repr__(self):
        return f"{self.name}(Lvl={self.level} ATK={self.atk} HP={self.hp})"

class AbilityDefinition:
    def __init__(self, trigger, ability_id, params=None):
        self.trigger = trigger
        self.ability_id = ability_id
        self.params = params or {}