from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

def handle_attack(event, game_state, queue):
    attacker = event.source
    target = event.target

    atk = attacker.atk

    if target:
        if atk > target.atk:
            queue.push(Event(type=EventType.DEATH, target=target))
    else:
        enemy = game_state.players[1 - game_state.current_player]

        queue.push(Event(
            type=EventType.DAMAGE,
            target=enemy,
            value=atk
        ))