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

    def __repr__(self):
        return f"{self.name}(Lvl={self.level} ATK={self.atk} HP={self.hp})"


class AbilityDefinition:
    def __init__(self, trigger, ability_id, params=None):
        self.trigger = trigger
        self.ability_id = ability_id
        self.params = params or {}