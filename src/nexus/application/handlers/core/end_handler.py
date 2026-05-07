def handle_end_phase(event, game_state, queue):
    player = game_state.players[game_state.current_player]

    for key in player.hero_cooldowns:
        if player.hero_cooldowns[key] > 0:
            player.hero_cooldowns[key] -= 1

    print("[END PHASE]")