from nexus.domain.events.types import EventType
from nexus.domain.cards.models import AbilityDefinition


def parse_effect(effect_str: str) -> AbilityDefinition:
    """
    Exemplo:
    "ON_DEATH:spawn_token"
    "ON_DEBUFF:gain_atk(200)"
    """

    trigger_part, ability_part = effect_str.split(":")

    # Trigger
    trigger = EventType[trigger_part]

    # Ability + params
    if "(" in ability_part:
        ability_id, params_str = ability_part.split("(")
        params_str = params_str.replace(")", "")

        params = parse_params(params_str)
    else:
        ability_id = ability_part
        params = {}

    return AbilityDefinition(trigger, ability_id, params)


def parse_params(params_str: str):
    # Exemplo simples: "200"
    if params_str.isdigit():
        return {"value": int(params_str)}

    return {}