from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType


def handle_damage(event, game_state, queue):
    target = event.target
    damage = event.value

    target.hp -= damage

    if target.hp <= 0:
        queue.push(Event(
            type=EventType.DEATH,
            target=target
        ))