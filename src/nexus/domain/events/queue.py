from collections import deque
from typing import Optional

from .event import Event

class EventQueue:
    def __init__(self):
        self._queue = deque()

    def push(self, event: Event):
        self._queue.append(event)

    def pop(self) -> Optional[Event]:
        if self._queue:
            return self._queue.popleft()
        return None

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def clear(self):
        self._queue.clear()