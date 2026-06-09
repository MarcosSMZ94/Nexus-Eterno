def handle_mana_phase(event, game_state, queue):
    player = game_state.players[game_state.current_player]

    player.mana = min(player.mana + 1, 8)

    try:
        game_state.add_log(f"[MANA] {player.name} agora tem {player.mana}")
    except Exception:
        import logging
        logging.info(f"[MANA] {player.name} agora tem {player.mana}")