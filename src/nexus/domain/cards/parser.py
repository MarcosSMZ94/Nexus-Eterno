import re

from nexus.domain.events.types import EventType
from nexus.domain.cards.models import AbilityDefinition

TRIGGER_ALIASES = {
    "END_TURN": EventType.END_PHASE,
    "ON_ATTACK": EventType.ATTACK,
    "ON_DESTROY": EventType.DEATH,
    "USED_IN_EFFECT": EventType.SACRIFICE,
    "ONCE": EventType.SUMMON,
}

PARAM_KEYS = {
    "spawn_fragment": ["count"],
    "draw_cards": ["count"],
    "extra_debuff": ["amount"],
    "buff_on_death": ["amount", "bonus_if_sacrifice"],
    "buff_on_sacrifice": ["atk", "def"],
    "area_debuff_end_turn": ["atk_penalty", "def_penalty", "threshold_damage"],
    "area_debuff": ["atk_penalty", "def_penalty", "threshold_damage"],
    "heal_and_draw": ["heal"],
    "temp_buff": ["atk", "def"],
    "buff_atk_def": ["atk", "def"],
    "permanent_def": ["amount"],
    "weaken_enemy": ["amount"],
    "atk_per_ally": ["per_ally"],
    "apply_debuff_def": ["amount", "duration"],
    "buff_received_atk": ["amount"],
}

def parse_effect(effect_str: str) -> AbilityDefinition:
    """
    Exemplo:
    "DEATH:spawn_fragment(1)"
    "GLOBAL:buff_on_death(200,400)"
    """

    trigger_part, ability_part = effect_str.split(":")
    trigger_part = trigger_part.strip()

    # Trigger: nomes desconhecidos são preservados como string para o dispatcher decidir
    if trigger_part in TRIGGER_ALIASES:
        trigger = TRIGGER_ALIASES[trigger_part]
    else:
        try:
            trigger = EventType[trigger_part]
        except Exception:
            # preserva gatilhos customizados para o dispatcher decidir quando executar
            trigger = trigger_part

    # Ability + params
    if "(" in ability_part:
        ability_id, params_str = ability_part.split("(")
        params_str = params_str.replace(")", "")

        params = parse_params(params_str, ability_id)
    else:
        ability_id = ability_part
        params = {}

    return AbilityDefinition(trigger, ability_id, params)

def parse_params(params_str: str, ability_id: str = ""):
    numbers = [int(value) for value in re.findall(r"-?\d+", params_str)]
    if not numbers:
        return {}

    keys = PARAM_KEYS.get(ability_id, [])
    params = {"values": numbers}

    for index, key in enumerate(keys):
        if index < len(numbers):
            params[key] = numbers[index]

    if len(numbers) == 1:
        params["value"] = numbers[0]

    return params