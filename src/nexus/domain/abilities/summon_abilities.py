"""Habilidades de invocação: triggers ONCE/SUMMON e efeitos de entrada."""
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType
from nexus.domain.abilities.helpers import _owner_player, _param, _log

def consume_ally_double_atk(event, game_state, queue):
    """SUMMON: consome 1 aliado do campo e ganha o ATK dele (máximo 3000).
    Os 2 tributos de nível já foram gastos pelo sistema de invocação;
    esta habilidade consome mais 1 aliado como custo adicional.
    """
    card = event.target
    player = _owner_player(game_state, event.source)
    allies = [c for c in player.board.get_cards() if c is not card]
    if allies:
        ally = allies[0]
        gained = ally.atk
        player.board.remove_card(ally)
        card.atk = min(3000, card.atk + gained)
        card.base_atk = card.atk
        _log(game_state, f"[ABILITY] {card.name} consumiu {ally.name} (+{gained} ATK → {card.atk})")
    else:
        _log(game_state, f"[ABILITY] {card.name}: sem aliado para consumir, ATK mantido em {card.atk}")

def buff_atk_def(event, game_state, queue):
    """SUMMON: a carta ganha +ATK e +DEF permanentes (buff na própria carta que invocou)."""
    source_card = (event.data.get("card") if event.data else None) or event.target
    if not source_card:
        return
    atk = int(_param(event, "atk", 200) or 200)
    df  = int(_param(event, "def", 200) or 200)
    source_card.atk += atk
    source_card.def_temp = getattr(source_card, "def_temp", 0) + df
    _log(game_state, f"[ABILITY] {source_card.name} ganhou +{atk}/+{df} permanentes")
    # Notifica o sistema de buff para habilidades reativas (ex: Sentinela da Luz)
    queue.push(Event(type=EventType.BUFF, target=source_card, source=source_card))

def buff_received_atk(event, game_state, queue):
    """Sentinela da Luz: ao receber um buff, ganha +100 ATK permanente."""
    card = event.target
    if card is None:
        return
    amount = int(_param(event, "amount", 100) or 100)
    card.atk += amount
    _log(game_state, f"[ABILITY] {card.name} reage ao buff: +{amount} ATK")

def immune_on_entry(event, game_state, queue):
    card = event.target
    if not card:
        return
    card.immune_turns = getattr(card, "immune_turns", 0) + 1
    _log(game_state, f"[ABILITY] {card.name} ficou imune neste turno")

def silence_on_entry(event, game_state, queue):
    enemy = game_state.players[1 - game_state.current_player]
    for c in enemy.board.get_cards():
        c.silenced = True
    _log(game_state, "[ABILITY] silence_on_entry aplicado aos inimigos")

def permanent_def(event, game_state, queue):
    card = event.data.get("card") if event.data else event.target
    if not card:
        return
    # +DEF permanente: aplica apenas uma vez por criatura (não acumula a cada invocação)
    if getattr(card, "_permanent_def_done", False):
        return
    amount = int(_param(event, "amount", 300) or 300)
    card.def_temp = getattr(card, "def_temp", 0) + amount
    card._permanent_def_done = True
    _log(game_state, f"[ABILITY] {card.name} ganhou +{amount} DEF permanente")
    queue.push(Event(type=EventType.BUFF, target=card, source=card))

def aberracao_invocacao_atk(event, game_state, queue):
    """SUMMON via sacrifício: +300 ATK por criatura sacrificada. Com 2+ sacrifícios: +300 DEF permanente."""
    card = (event.data.get("card") if event.data else None) or event.target
    if not card:
        return
    sacrifices_used = int(_param(event, "sacrifices_used", 0) or 0)
    if sacrifices_used <= 0:
        # fallback: conta pelo histórico global se o handler não informou
        sacrifices_used = len(getattr(game_state, "sacrificed_cards", []))
    if sacrifices_used <= 0:
        _log(game_state, f"[ABILITY] {card.name}: nenhum sacrifício detectado, sem bônus")
        return
    card.atk += 300 * sacrifices_used
    if sacrifices_used >= 2:
        card.def_temp = getattr(card, "def_temp", 0) + 300
        _log(game_state, f"[ABILITY] {card.name}: +{300 * sacrifices_used} ATK e +300 DEF ({sacrifices_used} sacrifício(s))")
    else:
        _log(game_state, f"[ABILITY] {card.name}: +{300 * sacrifices_used} ATK ({sacrifices_used} sacrifício)")

def miniatura_solar_entry(event, game_state, queue):
    """SUMMON: destrói automaticamente a criatura inimiga com maior ATK.
    Se a destruída for Nv6+: causa 300 dano ao herói inimigo.
    Fragmentos gerados pela morte são redirecionados para o campo do jogador dono.
    """
    card = (event.data.get("card") if event.data else None) or event.target
    owner = _owner_player(game_state, card)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner),
                     game_state.current_player)
    enemy = game_state.players[1 - owner_idx]
    enemy_cards = enemy.board.get_cards()
    if not enemy_cards:
        _log(game_state, f"[ABILITY] {card.name}: nenhuma criatura inimiga para destruir")
        return
    target = max(enemy_cards, key=lambda c: c.atk)
    target_level = getattr(target, "level", 0)
    enemy.board.remove_card(target)
    _log(game_state, f"[ABILITY] {card.name} destrói {target.name} (maior ATK: {target.atk})")
    queue.push(Event(type=EventType.DEATH, source=owner, target=target,
                     data={"redirect_spawn_to": owner}))
    if target_level >= 6:
        queue.push(Event(type=EventType.DAMAGE, target=enemy, value=300))
        _log(game_state, f"[ABILITY] {card.name}: alvo Nv{target_level} → 300 dano ao herói inimigo")
