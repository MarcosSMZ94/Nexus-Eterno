from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType


def consume_ally_double_atk(event, game_state, queue):
    card = event.target
    player = event.source
    board_cards = player.board.get_cards()
    if board_cards:
        ally = board_cards[0]
        player.board.remove_card(ally)
        card.atk *= 2
        print(f"[ABILITY] {card.name} +ATK x2")


def spawn_token(event, game_state, queue):
    card = event.target
    player = event.source
    from nexus.domain.cards.models import Card
    token = Card("token_shadow", "Token Sombrio", 1, 100, 100, "SHADOW", "creature", [])
    if player.board.add_card(token):
        print(f"[ABILITY] Token spawnado")


def gain_atk(event, game_state, queue):
    card = event.target
    card.atk += 200
    print(f"[ABILITY] {card.name} +200 ATK")


def apply_debuff_def(event, game_state, queue):
    target = event.target
    if not target:
        return
    target.def_temp = getattr(target, 'def_temp', 0) - 200
    print(f"[ABILITY] {target.name} -DEF")


def buff_light_creatures(event, game_state, queue):
    player = game_state.players[game_state.current_player]
    for card in player.board.get_cards():
        if card.element == "LIGHT":
            card.atk += 500
            card.def_temp = getattr(card, 'def_temp', 0) + 500
            print(f"[ABILITY] {card.name} +ATK/DEF")


def debuff_enemy_creatures(event, game_state, queue):
    enemy_idx = 1 - game_state.current_player
    enemy = game_state.players[enemy_idx]
    for card in enemy.board.get_cards():
        card.atk = max(0, card.atk - 400)
        card.def_temp = getattr(card, 'def_temp', 0) - 400
        print(f"[ABILITY] {card.name} -ATK/DEF")


def destroy_target(event, game_state, queue):
    target = event.target
    if not target:
        return
    enemy_idx = 1 - game_state.current_player
    enemy = game_state.players[enemy_idx]
    if enemy.board.remove_card(target):
        print(f"[ABILITY] {target.name} destruído")
        queue.push(Event(
            type=EventType.DEATH,
            target=target
        ))


def heal_player(event, game_state, queue):
    player = event.source
    player.hp += 200
    print(f"[ABILITY] {player.name} +200 HP")


def deal_damage_all(event, game_state, queue):
    enemy_idx = 1 - game_state.current_player
    enemy = game_state.players[enemy_idx]
    for card in enemy.board.get_cards():
        card.hp -= 300
        if card.hp <= 0:
            enemy.board.remove_card(card)
            queue.push(Event(type=EventType.DEATH, target=card))
    print(f"[ABILITY] Dano em área")