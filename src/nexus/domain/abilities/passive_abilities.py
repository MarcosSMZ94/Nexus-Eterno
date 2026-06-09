from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType
from nexus.domain.abilities.helpers import _owner_player, _param, _log

def buff_on_death(event, game_state, queue):
    """GLOBAL DEATH: Acolito ganha +200 ATK por qualquer morte; +400 se foi sacrifício ALIADO.
    Distingue sacrifício aliado (source = dono do Acolito) de morte por combate (source = inimigo).
    """
    card = event.data.get("card") if event.data else None
    if card is None:
        return

    # guardrail: trigger_handler pode disparar GLOBAL duas vezes na mesma morte
    dead_key = id(event.target)
    if getattr(card, "_buff_on_death_last", None) == dead_key:
        return
    card._buff_on_death_last = dead_key

    # +400 apenas quando o source da morte é o próprio dono do Acolito (sacrifício aliado)
    acolito_player = _owner_player(game_state, card)
    is_own_sacrifice = (event.source is acolito_player)
    if is_own_sacrifice:
        amount = int(_param(event, "bonus_if_sacrifice", 400) or 400)
    else:
        amount = int(_param(event, "amount", 200) or 200)

    card.atk += amount
    _log(game_state, f"[ABILITY] {card.name} ganha +{amount} ATK permanente")

def buff_on_sacrifice(event, game_state, queue):
    """Aberração Costurada: aliados ganham +300 ATK ao ser sacrificada.
    Se este é o 2º+ sacrifício da partida: também ganham +300 DEF.
    """
    owner = _owner_player(game_state, event.source)
    atk = int(_param(event, "atk", 300) or 300)
    df = int(_param(event, "def", 300) or 300)
    # total de sacrifícios contado via lista sacrificed_cards (incluindo este)
    total_sacrifices = len(getattr(game_state, "sacrificed_cards", []))
    give_def = total_sacrifices >= 2
    for card in owner.board.get_cards():
        card.atk += atk
        if give_def:
            card.def_temp = getattr(card, "def_temp", 0) + df
        queue.push(Event(type=EventType.BUFF, target=card, source=event.source))
    _log(game_state, f"[ABILITY] Aberração sacrificada: aliados +{atk} ATK" +
         (f" +{df} DEF (sacrifício {total_sacrifices})" if give_def else f" (sacrifício {total_sacrifices})"))

def scales_with_deaths(event, game_state, queue):
    """GLOBAL DEATH: +100 ATK por morte na partida.
    Se 3+ criaturas morrerem no mesmo turno: +300 DEF permanente ao final desse turno.
    """
    card = event.data.get("card") if event.data else event.target
    if not card:
        return
    # guardrail: trigger_handler pode disparar GLOBAL duas vezes na mesma morte
    dead_key = id(event.target)
    if getattr(card, "_scales_last_death", None) == dead_key:
        return
    card._scales_last_death = dead_key
    card.atk += 100
    # rastreia mortes neste turno para o bônus de +300 DEF
    if not hasattr(game_state, "deaths_this_turn"):
        game_state.deaths_this_turn = 0
    game_state.deaths_this_turn += 1
    if game_state.deaths_this_turn >= 3 and not getattr(card, "_scales_def_bonus_given", False):
        card.def_temp = getattr(card, "def_temp", 0) + 300
        card._scales_def_bonus_given = True
        _log(game_state, f"[ABILITY] {card.name}: 3+ mortes no turno → +300 DEF permanente")
    _log(game_state, f"[ABILITY] {card.name} ganhou +100 ATK ({game_state.deaths_this_turn} morte(s) este turno)")

def revive_sacrificed(event, game_state, queue):
    """ONCE: retorna ao campo TODAS as criaturas Sombra sacrificadas como tokens 0 ATK/0 DEF.
    Tokens podem ser sacrificados imediatamente no mesmo turno.
    """
    owner = _owner_player(game_state, event.source)
    sacrificed_cards = getattr(game_state, "sacrificed_cards", [])
    # filtra apenas cartas Sombra (element == "SHADOW")
    sombra = [c for c in sacrificed_cards if getattr(c, "element", "") == "SHADOW"]
    for c in sombra:
        sacrificed_cards.remove(c)
        c.atk = 0
        c.hp = 0
        c.def_temp = 0
        owner.board.add_card(c)
    if sombra:
        _log(game_state, f"[ABILITY] {owner.name} reviveu {len(sombra)} criatura(s) Sombra como tokens 0/0")
    else:
        _log(game_state, f"[ABILITY] {owner.name}: nenhuma criatura Sombra no cemitério para reviver")

def temp_buff(event, game_state, queue):
    owner = _owner_player(game_state, event.source)
    atk = int(_param(event, "atk", 200) or 200)
    df  = int(_param(event, "def", 200) or 200)
    for card in owner.board.get_cards():
        card.atk += atk
        card.def_temp = getattr(card, "def_temp", 0) + df
        queue.push(Event(type=EventType.BUFF, target=card, source=event.source))
    _log(game_state, f"[ABILITY] temp_buff aplicado: +{atk}/+{df}")

def atk_per_ally(event, game_state, queue):
    """Passivo: +300 ATK para cada OUTRA criatura aliada em campo (exclui a própria carta).
    Recalcula o delta a cada chamada para não acumular erroneamente.
    """
    card = event.data.get("card") if event.data else event.target
    if card is None:
        return
    owner = _owner_player(game_state, card)
    per_ally = int(_param(event, "per_ally", 300) or 300)
    # conta apenas aliados diferentes desta carta
    other_allies = [c for c in owner.board.get_cards() if c is not card]
    bonus = per_ally * len(other_allies)
    prev = getattr(card, "_atk_per_ally_bonus", 0)
    delta = bonus - prev
    card.atk += delta
    card._atk_per_ally_bonus = bonus
    if delta > 0:
        queue.push(Event(type=EventType.BUFF, target=card, source=card))
    _log(game_state, f"[ABILITY] {card.name}: +{bonus} ATK por {len(other_allies)} aliado(s)")

def protect_allies(event, game_state, queue):
    owner = _owner_player(game_state, event.source)
    for c in owner.board.get_cards():
        c.protected = True
    _log(game_state, "[ABILITY] protect_allies aplicado")

def area_debuff_end_turn(event, game_state, queue):
    # Usa o dono da carta para calcular o inimigo corretamente.
    # Durante END_PHASE, trigger_handler itera cartas de AMBOS os jogadores se a carta do
    # jogador não-ativo disparar, game_state.current_player aponta para o adversário, não o dono.
    card = event.data.get("card") if event.data else None
    owner = _owner_player(game_state, card if card else event.source)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner),
                     game_state.current_player)
    enemy = game_state.players[1 - owner_idx]
    atk_pen = int(_param(event, "atk_penalty", -200) or -200)
    def_pen = int(_param(event, "def_penalty", -200) or -200)
    threshold_damage = int(_param(event, "threshold_damage", 200) or 200)
    affected = 0
    for c in enemy.board.get_cards():
        c.atk = max(0, c.atk + atk_pen)
        c.def_temp = getattr(c, "def_temp", 0) + def_pen
        affected += 1
    if affected >= 2:
        # dano ao herói inimigo (recompensa por debuffar 2+ criaturas)
        enemy.hp -= threshold_damage
    _log(game_state, f"[ABILITY] area_debuff_end_turn aplicado a {affected} criaturas")

def area_debuff(event, game_state, queue):
    return area_debuff_end_turn(event, game_state, queue)

def cycle_effects(event, game_state, queue):
    # trigger_handler seta event.data["card"] = a Quimera antes de chamar esta função
    card = event.data.get("card") if event.data else None
    if card is None:
        return

    # resolver o dono pela carta (não por event.source, que é None em TURN_START)
    owner = _owner_player(game_state, card)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner),
                     game_state.current_player)
    enemy = game_state.players[1 - owner_idx]

    mode = getattr(card, "cycle_mode", 0) % 3

    if mode == 0:
        enemy.hp -= 300
    elif mode == 1:
        for target in enemy.board.get_cards():
            target.atk = max(0, target.atk - 300)
            target.def_temp = getattr(target, "def_temp", 0) - 300
    else:
        owner.hp += 300

    card.cycle_mode = mode + 1
    _log(game_state, f"[ABILITY] cycle_effects modo {mode}: {owner.name} -> inimigo={enemy.name}")

def weaken_enemy(event, game_state, queue):
    """ON_ATTACK: reduz ATK do alvo permanentemente (somente ATK, não DEF)."""
    target = event.target
    if not target:
        return
    amount = int(_param(event, "amount", 300) or 300)
    target.atk = max(0, target.atk - amount)
    _log(game_state, f"[ABILITY] {target.name} perdeu -{amount} ATK permanente")
