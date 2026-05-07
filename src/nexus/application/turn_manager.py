from nexus.domain.turn.phase import Phase
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

PHASE_ORDER = [
    Phase.DRAW,
    Phase.NEXUS,
    Phase.MANA,
    Phase.MAIN_1,
    Phase.BATTLE,
    Phase.MAIN_2,
    Phase.END
]

class TurnManager:
    def next_phase(self, game_state, queue):
        current_index = PHASE_ORDER.index(game_state.current_phase)

        if current_index + 1 < len(PHASE_ORDER):
            next_phase = PHASE_ORDER[current_index + 1]
        else:
            # troca turno
            game_state.current_player = 1 - game_state.current_player
            game_state.turn_count += 1
            next_phase = Phase.DRAW

            queue.push(Event(type=EventType.TURN_START))

        game_state.current_phase = next_phase

        print(f"[PHASE] {next_phase}")

        queue.push(Event(
            type=EventType.PHASE_CHANGED,
            data={"phase": next_phase}
        ))