from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType
from nexus.application.handlers.ability.trigger_handler import trigger_abilities_for_event

NEXUS_BONUS = 300  # +ATK/+DEF para criaturas do elemento dominante do Nexus (LIGHT/SHADOW)

def nexus_bonus(card, game_state):
    el = getattr(game_state, "nexus_element", None)
    if el and getattr(card, "element", None) == el:
        return NEXUS_BONUS
    return 0

def effective_atk(attacker, defender_element, game_state):
    return attacker.atk + nexus_bonus(attacker, game_state)

def _effective_hp(card):
    return card.hp + getattr(card, "def_temp", 0)

def handle_attack(event, game_state, queue):
    attacker = event.source
    target = event.target
    if attacker is None:
        return

    attacker.has_attacked = True
    attacker.attacks_this_turn = getattr(attacker, "attacks_this_turn", 0) + 1
    # Abominação evoluída (can_attack_twice): reseta o flag após o 1º ataque para permitir o 2º
    if getattr(attacker, "can_attack_twice", False) and attacker.attacks_this_turn < 2:
        attacker.has_attacked = False
    active = game_state.players[game_state.current_player]
    enemy = game_state.players[1 - game_state.current_player]

    # ataque direto ao herói inimigo
    if target is None:
        dmg = effective_atk(attacker, None, game_state)
        queue.push(Event(type=EventType.DAMAGE, target=enemy, value=dmg))
        _log(game_state, f"[ATTACK] {attacker.name} ataca diretamente ({dmg} de dano)")
        return

    # criatura imune: não recebe dano nem morre neste turno
    if getattr(target, "immune_turns", 0) > 0:
        target.immune_turns -= 1
        _log(game_state, f"[ATTACK] {target.name} é imune — ataque bloqueado")
        return

    atk_a = effective_atk(attacker, getattr(target, "element", None), game_state)
    atk_b = target.atk + nexus_bonus(target, game_state)

    # proteção: alvo não toma dano; atacante ainda recebe contra-ataque e proteção é consumida
    if getattr(target, "protected", False):
        target.protected = False
        _log(game_state, f"[ATTACK] {target.name} protegido — contra-ataque em {attacker.name}")
        attacker.hp -= atk_b
        eff_a = _effective_hp(attacker)
        if eff_a <= 0:
            excess = max(0, -eff_a)
            queue.push(Event(type=EventType.DEATH, source=enemy, target=attacker))
            if excess > 0:
                queue.push(Event(type=EventType.DAMAGE, target=active, value=excess))
        return

    target.hp -= atk_a
    attacker.hp -= atk_b

    # Damage Step: destruição quando HP efetivo (= DEF exibida = hp + def_temp) ≤ 0
    eff_t = _effective_hp(target)
    if eff_t <= 0:
        excess = max(0, -eff_t)
        queue.push(Event(type=EventType.DEATH, source=attacker, target=target))
        if excess > 0:
            queue.push(Event(type=EventType.DAMAGE, target=enemy, value=excess))
        # Abominação de Carne evoluída: gera Fragmento e +200 ATK ao destruir
        if getattr(attacker, "abominacao_evolved", False):
            attacker.atk = min(3000, attacker.atk + 200)
            from nexus.domain.abilities.implementations import spawn_fragment as _spawn_frag
            _spawn_frag(Event(type=EventType.DEATH, source=active, target=target, data={}),
                        game_state, queue)
        _log(game_state, f"[ATTACK] {attacker.name} destrói {target.name} (excesso {excess})")
    else:
        _log(game_state, f"[ATTACK] {attacker.name} causa {atk_a} a {target.name} (HP efetivo: {eff_t})")
        # alvo sobreviveu ao combate: dispara ON_COMBAT_HIT (ex: Sentinela da Luz +300 DEF)
        hit_evt = Event(type=EventType.ATTACK, source=attacker, target=target, data={})
        trigger_abilities_for_event(hit_evt, game_state, queue, "ON_COMBAT_HIT")

    eff_a = _effective_hp(attacker)
    if eff_a <= 0:
        excess = max(0, -eff_a)
        queue.push(Event(type=EventType.DEATH, source=enemy, target=attacker))
        if excess > 0:
            queue.push(Event(type=EventType.DAMAGE, target=active, value=excess))
        _log(game_state, f"[ATTACK] {attacker.name} é destruído pelo contra-ataque (excesso {excess})")

def _log(game_state, message):
    try:
        game_state.add_log(message)
    except Exception:
        import logging
        logging.info(message)
