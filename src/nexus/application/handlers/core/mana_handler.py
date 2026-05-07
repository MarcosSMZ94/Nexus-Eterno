def handle_mana_phase(event, game_state, queue):
    player = game_state.players[game_state.current_player]

    player.mana = min(player.mana + 1, 8)

    print(f"[MANA] {player.name} agora tem {player.mana}")