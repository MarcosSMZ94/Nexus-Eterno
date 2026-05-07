from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType


def handle_card_triggers(event, game_state, queue, ability_registry):
    for card in game_state.board:
        for ability in card.abilities:
            if ability.trigger == event.type:
                print(f"[TRIGGER] {card.name} ativa {ability.ability_id}")

                # cria evento de ability
                queue.push(
                    Event(
                        type=EventType.TRIGGER_ABILITY,
                        source=card,
                        data={
                            "ability_id": ability.ability_id,
                            "params": ability.params
                        }
                    )
                )