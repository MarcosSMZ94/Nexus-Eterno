from nexus.domain.abilities import implementations


# Dicionário simples de todas as abilities
ABILITIES = {
    "consume_ally_double_atk": implementations.consume_ally_double_atk,
    "spawn_token": implementations.spawn_token,
    "gain_atk": implementations.gain_atk,
    "apply_debuff_def": implementations.apply_debuff_def,
    "buff_light_creatures": implementations.buff_light_creatures,
    "debuff_enemy_creatures": implementations.debuff_enemy_creatures,
    "destroy_target": implementations.destroy_target,
    "heal_player": implementations.heal_player,
    "deal_damage_all": implementations.deal_damage_all,
}


def get_ability_registry():
    """Retorna um objeto compatível com o código antigo"""
    class Registry:
        def execute(self, ability_id, event, game_state, queue):
            if ability_id not in ABILITIES:
                raise ValueError(f"Ability não encontrada: {ability_id}")
            ABILITIES[ability_id](event, game_state, queue)
    
    return Registry()