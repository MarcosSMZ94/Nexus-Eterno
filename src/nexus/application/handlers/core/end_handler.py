def handle_end_phase(event, game_state, queue):
    player = game_state.players[game_state.current_player]

    for key in player.hero_cooldowns:
        if player.hero_cooldowns[key] > 0:
            player.hero_cooldowns[key] -= 1

    try:
        game_state.add_log("[END PHASE]")
    except Exception:
        import logging
        logging.info("[END PHASE]")