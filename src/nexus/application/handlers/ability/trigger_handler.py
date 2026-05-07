from nexus.domain.events.types import EventType
from nexus.domain.abilities.registry import get_ability_registry


def execute_ability(ability_id, event, game_state, queue):
    """Executa uma ability com tratamento de erro simples"""
    try:
        get_ability_registry().execute(ability_id, event, game_state, queue)
    except Exception as e:
        print(f"[ERROR] {ability_id}: {e}")


def trigger_abilities_for_event(event, game_state, queue, trigger_type):
    """Dispara abilities de uma carta para um tipo de evento"""
    card = event.target
    if not card.abilities:
        return
    
    for ability_def in card.abilities:
        if ability_def.trigger == trigger_type:
            print(f"[TRIGGER] {card.name} ativa {ability_def.ability_id}")
            execute_ability(ability_def.ability_id, event, game_state, queue)


def handle_summon_triggers(event, game_state, queue):
    """Abilities ao invocar"""
    trigger_abilities_for_event(event, game_state, queue, EventType.SUMMON)


def handle_death_triggers(event, game_state, queue):
    """Abilities ao morrer"""
    trigger_abilities_for_event(event, game_state, queue, EventType.DEATH)
