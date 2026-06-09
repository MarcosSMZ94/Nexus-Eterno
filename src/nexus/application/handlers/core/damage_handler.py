from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

def handle_damage(event, game_state, queue):
    target = event.target
    if target is None:
        return

    damage = event.value or 0
    target.hp -= damage

    is_creature = hasattr(target, "abilities")
    if is_creature and target.hp <= 0:
        queue.push(Event(
            type=EventType.DEATH,
            source=game_state.players[game_state.current_player],
            target=target,
        ))
