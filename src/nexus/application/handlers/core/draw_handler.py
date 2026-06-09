def handle_draw_phase(event, game_state, queue):
    player = game_state.players[game_state.current_player]

    if player.deck:
        card = player.deck.pop()
        player.hand.append(card)

        try:
            game_state.add_log(f"[DRAW] {player.name} comprou {card.name}")
        except Exception:
            import logging
            logging.info(f"[DRAW] {player.name} comprou {card.name}")