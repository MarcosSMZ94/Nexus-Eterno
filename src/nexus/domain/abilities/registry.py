from nexus.domain.abilities import implementations

ABILITIES = {}

def get_ability_registry():
    class Registry:
        def execute(self, ability_id, event, game_state, queue):
            if ability_id not in ABILITIES:
                if hasattr(implementations, ability_id):
                    ABILITIES[ability_id] = getattr(implementations, ability_id)
                else:
                    raise ValueError(f"Ability não encontrada: {ability_id}")
            ABILITIES[ability_id](event, game_state, queue)
    
    return Registry()