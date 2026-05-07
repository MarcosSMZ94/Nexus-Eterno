import random
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

ELEMENTS = ["FIRE", "WATER", "EARTH", "AIR"]

def handle_nexus_phase(event, game_state, queue):
    element = random.choice(ELEMENTS)

    game_state.nexus_element = element

    print(f"[NEXUS] {element}")

    queue.push(Event(
        type=EventType.NEXUS_CHANGED,
        data={"element": element}
    ))