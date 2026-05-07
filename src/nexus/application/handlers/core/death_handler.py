from nexus.domain.events.types import EventType
from nexus.domain.events.event import Event


def handle_death(event, game_state, queue):
    target = event.target

    print(f"{target} morreu")

    # exemplo: remover do board
    game_state.board.remove(target)

    # dispara habilidade
    queue.push(Event(
        type=EventType.TRIGGER_ABILITY,
        source=target
    ))