from nexus.domain.abilities.registry import AbilityRegistry
from nexus.domain.abilities.implementations import (
    spawn_token,
    gain_atk
)


def setup_abilities() -> AbilityRegistry:
    registry = AbilityRegistry()

    registry.register("spawn_token", spawn_token)
    registry.register("gain_atk", gain_atk)

    return registry