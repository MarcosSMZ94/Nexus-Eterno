from nexus.domain.events.types import EventType
from nexus.domain.events.event import Event

def handle_death(event, game_state, queue):
    target = event.target
    if target is None:
        return

    for player in game_state.players:
        if target in player.board.get_cards():
            player.board.remove_card(target)
            try:
                game_state.add_log(f"[DEATH] {getattr(target, 'name', target)} foi destruída")
            except Exception:
                import logging
                logging.info(f"[DEATH] {getattr(target, 'name', target)} foi destruída")
            return
