from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType


def handle_summon(event, game_state, queue):
    player = game_state.players[game_state.current_player]
    card = event.target

    # 🔹 validar carta na mão
    if card not in player.hand:
        print("[SUMMON] Carta não está na mão")
        return

    # 🔹 validar espaço no board
    if player.board.get_free_slot_index() is None:
        print("[SUMMON] Board cheio")
        return

    # 🔹 verificar sacrifício
    cost = required_sacrifices(card)
    board_cards = player.board.get_cards()

    if len(board_cards) < cost:
        print("[SUMMON] Sacrifícios insuficientes")
        return

    # 🔥 SACRIFÍCIO AUTOMÁTICO (MVP)
    sacrificed = board_cards[:cost]

    for c in sacrificed:
        player.board.remove_card(c)

        queue.push(Event(
            type=EventType.SACRIFICE,
            source=player,
            target=c
        ))

        queue.push(Event(
            type=EventType.DEATH,
            source=player,
            target=c
        ))

    # 🔹 invocar
    player.hand.remove(card)
    player.board.add_card(card)

    print(f"[SUMMON] {player.name} invocou {card.name}")

    queue.push(Event(
        type=EventType.SUMMON,
        source=player,
        target=card
    ))
    
def required_sacrifices(card):
    if card.level <= 4:
        return 0
    elif card.level <= 6:
        return 1
    else:
        return 2