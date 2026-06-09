import logging

from nexus.domain.events.event import Event   # noqa: F401
from nexus.domain.events.types import EventType  # noqa: F401

def _owner_player(game_state, source=None):
    if source in getattr(game_state, "players", []):
        return source

    for player in getattr(game_state, "players", []):
        if source in player.board.get_cards() or source in player.hand or source in player.deck:
            return player

    return game_state.players[game_state.current_player]

def _param(event, key, default=None):
    if event and event.data and key in event.data:
        return event.data[key]
    return default

def _log(game_state, message):
    try:
        game_state.add_log(message)
    except Exception:
        logging.info(message)

def is_debuffed(card):
    return (
        getattr(card, "def_temp", 0) < 0
        or card.atk < getattr(card, "base_atk", card.atk)
        or getattr(card, "silenced", False)
        or getattr(card, "corruption_ticks", 0) > 0
    )
