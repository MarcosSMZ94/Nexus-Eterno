
from nexus.domain.events.types import EventType

from .core.phase_handler import handle_phase_changed
from .core.draw_handler import handle_draw_phase
from .core.nexus_handler import handle_nexus_phase
from .core.mana_handler import handle_mana_phase
from .core.end_handler import handle_end_phase
from .core.combat_handler import handle_attack
from .core.summon_handler import handle_summon
from .ability.trigger_handler import handle_summon_triggers, handle_death_triggers

def register_all(resolver):
    resolver.register_handler(EventType.PHASE_CHANGED, handle_phase_changed)
    resolver.register_handler(EventType.DRAW_PHASE, handle_draw_phase)
    resolver.register_handler(EventType.NEXUS_PHASE, handle_nexus_phase)
    resolver.register_handler(EventType.MANA_PHASE, handle_mana_phase)
    resolver.register_handler(EventType.END_PHASE, handle_end_phase)
    resolver.register_handler(EventType.ATTACK, handle_attack)
    resolver.register_handler(EventType.SUMMON_REQUEST, handle_summon)
    resolver.register_handler(EventType.SUMMON, handle_summon_triggers)
    resolver.register_handler(EventType.DEATH, handle_death_triggers)