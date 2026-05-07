from dataclasses import dataclass
from typing import Any, Optional

from .types import EventType


@dataclass
class Event:
    type: EventType

    # Quem causou o evento
    source: Optional[Any] = None

    # Quem recebe
    target: Optional[Any] = None

    # Dados extras (dano, quantidade, etc)
    value: Optional[int] = None

    # Dados genéricos adicionais
    data: Optional[dict] = None