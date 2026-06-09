import logging

from nexus.domain.events.queue import EventQueue
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

class EventResolver:
    def __init__(self, queue: EventQueue):
        self.queue = queue
        self.handlers = {}

    def register_handler(self, event_type: EventType, handler):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def resolve(self, game_state):
        while not self.queue.is_empty():
            event = self.queue.pop()

            if game_state:
                try:
                    game_state.add_log(f"[Resolver] {event.type}")
                except Exception:
                    logging.info(f"[Resolver] {event.type}")
            else:
                logging.info(f"[Resolver] {event.type}")

            handlers = self.handlers.get(event.type, [])

            for handler in handlers:
                handler(event, game_state, self.queue)