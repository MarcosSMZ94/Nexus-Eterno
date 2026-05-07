from nexus.domain.turn.phase import Phase
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

def handle_phase_changed(event, game_state, queue):
    phase = event.data["phase"]

    if phase == Phase.DRAW:
        queue.push(Event(type=EventType.DRAW_PHASE))

    elif phase == Phase.NEXUS:
        queue.push(Event(type=EventType.NEXUS_PHASE))

    elif phase == Phase.MANA:
        queue.push(Event(type=EventType.MANA_PHASE))

    elif phase == Phase.END:
        queue.push(Event(type=EventType.END_PHASE))