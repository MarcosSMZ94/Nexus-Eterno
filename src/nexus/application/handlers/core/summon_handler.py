from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

def handle_summon(event, game_state, queue):
    player = game_state.players[game_state.current_player]
    card = event.target

    if card not in player.hand:
        try:
            game_state.add_log("[SUMMON] Carta não está na mão")
        except Exception:
            import logging
            logging.info("[SUMMON] Carta não está na mão")
        return

    if getattr(player, "summons_this_turn", 0) >= 1:
        try:
            game_state.add_log("[SUMMON] Já invocou neste turno (limite: 1)")
        except Exception:
            import logging
            logging.info("[SUMMON] Já invocou neste turno (limite: 1)")
        return

    cost = required_sacrifices(card)
    board_cards = player.board.get_cards()

    if player.board.get_free_slot_index() is None and cost == 0:
        try:
            game_state.add_log("[SUMMON] Board cheio")
        except Exception:
            import logging
            logging.info("[SUMMON] Board cheio")
        return

    explicit_targets = (event.data or {}).get("sacrifice_targets")
    if explicit_targets is not None:
        if len(explicit_targets) < cost:
            try:
                game_state.add_log("[SUMMON] Sacrifícios insuficientes")
            except Exception:
                import logging
                logging.info("[SUMMON] Sacrifícios insuficientes")
            return
        sacrificed = explicit_targets[:cost]
    else:
        if len(board_cards) < cost:
            try:
                game_state.add_log("[SUMMON] Sacrifícios insuficientes")
            except Exception:
                import logging
                logging.info("[SUMMON] Sacrifícios insuficientes")
            return
        sacrificed = board_cards[:cost]

    sacrificed_cards = getattr(game_state, "sacrificed_cards", None)
    if sacrificed_cards is None:
        game_state.sacrificed_cards = []
        sacrificed_cards = game_state.sacrificed_cards

    for c in sacrificed:
        # Tenta remover do próprio campo; se não encontrar, remove do campo inimigo
        # (Aberração Costurada evoluída permite sacrificar inimigos com DEF < 1000)
        if not player.board.remove_card(c):
            for other in game_state.players:
                if other is not player:
                    other.board.remove_card(c)
        sacrificed_cards.append(c)

        queue.push(Event(
            type=EventType.SACRIFICE,
            source=player,
            target=c,
            data={"sacrificed": c}
        ))

        queue.push(Event(
            type=EventType.DEATH,
            source=player,
            target=c
        ))

    # invocar
    player.hand.remove(card)
    player.board.add_card(card)
    card.has_attacked = True  # summoning sickness: não pode atacar no turno de invocação
    player.summons_this_turn = getattr(player, "summons_this_turn", 0) + 1

    try:
        game_state.add_log(f"[SUMMON] {player.name} invocou {card.name}")
    except Exception:
        import logging
        logging.info(f"[SUMMON] {player.name} invocou {card.name}")

    queue.push(Event(
        type=EventType.SUMMON,
        source=player,
        target=card,
        data={"sacrifices_used": len(sacrificed)}
    ))
    
def required_sacrifices(card):
    if card.level <= 4:
        return 0
    elif card.level <= 6:
        return 1
    else:
        return 2