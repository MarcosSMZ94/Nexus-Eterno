from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType


class CommandHandler:
    def __init__(self, queue, turn_manager):
        self.queue = queue
        self.turn_manager = turn_manager

    def pass_phase(self, game_state):
        self.turn_manager.next_phase(game_state, self.queue)
        
    def play_card(self, game_state, card):
        self.queue.push(Event(
            type=EventType.SUMMON_REQUEST,
            target=card
        ))