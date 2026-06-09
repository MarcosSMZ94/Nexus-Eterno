"""Habilidades de evolução (Nv6), feitiços avançados e habilidades ativas de herói."""
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType
from nexus.domain.abilities.helpers import _owner_player, _param, _log, is_debuffed
from nexus.domain.abilities.spell_abilities import spawn_fragment


def julgamento_solar(event, game_state, queue):
    owner = _owner_player(game_state, event.source)
    enemy = game_state.players[1 - game_state.current_player]
    for c in owner.board.get_cards():
        c.atk += 300
        c.def_temp = getattr(c, "def_temp", 0) + 300
    for c in enemy.board.get_cards():
        c.atk = max(0, c.atk - 300)
        c.def_temp = getattr(c, "def_temp", 0) - 300
    _log(game_state, "[ABILITY] julgamento_solar aplicado")


def barreira_divina(event, game_state, queue):
    """Aliados ficam protegidos e imunes à destruição neste turno."""
    owner = _owner_player(game_state, event.source)
    for c in owner.board.get_cards():
        c.protected = True
        c.immune_turns = getattr(c, "immune_turns", 0) + 1
    _log(game_state, "[ABILITY] barreira_divina: aliados imunes neste turno")


def ordem_absoluta(event, game_state, queue):
    """Oponente não pode atacar com criaturas Nv>=5 nem ativar efeitos de criaturas evoluídas.
    Dura até o fim do próximo turno inimigo (order_lock_turns = 2).
    """
    owner = _owner_player(game_state, event.source)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner),
                     game_state.current_player)
    enemy = game_state.players[1 - owner_idx]
    enemy.order_lock_turns = 2
    _log(game_state, "[ABILITY] ordem_absoluta: oponente bloqueado por 2 turnos")


def chama_equilibrio(event, game_state, queue):
    """Se inimigo tiver mais criaturas: destrói a de maior ATK.
    Se igual número: 300 dano ao herói inimigo.
    Se inimigo tiver menos: sem efeito.
    """
    owner = _owner_player(game_state, event.source)
    enemy = game_state.players[1 - game_state.current_player]
    ally_count = len(owner.board.get_cards())
    enemy_cards = enemy.board.get_cards()
    if len(enemy_cards) > ally_count:
        strongest = max(enemy_cards, key=lambda c: c.atk)
        enemy.board.remove_card(strongest)
        queue.push(Event(type=EventType.DEATH, source=owner, target=strongest))
        _log(game_state, f"[ABILITY] chama_equilibrio destrói {strongest.name}")
    elif len(enemy_cards) == ally_count:
        queue.push(Event(type=EventType.DAMAGE, target=enemy, value=300))
        _log(game_state, "[ABILITY] chama_equilibrio: campo igual → 300 dano direto")
    else:
        _log(game_state, "[ABILITY] chama_equilibrio: inimigo tem menos criaturas, sem efeito")


def renascimento_solar(event, game_state, queue):
    """Revive 1 criatura de luz morta com +500 ATK e imunidade neste turno."""
    owner = _owner_player(game_state, event.source)
    sacrificed = getattr(game_state, "sacrificed_cards", [])
    revived = next((c for c in reversed(sacrificed) if getattr(c, "element", "") == "LIGHT"), None)
    if revived is None:
        _log(game_state, "[ABILITY] renascimento_solar: nenhuma criatura de luz para reviver")
        return
    sacrificed.remove(revived)
    revived.atk += 500
    revived.immune_turns = getattr(revived, "immune_turns", 0) + 1
    owner.board.add_card(revived)
    _log(game_state, f"[ABILITY] renascimento_solar revive {revived.name} com +500 ATK")


def discipulo_solar_aura(event, game_state, queue):
    """Discípulo Solar evoluído: aliados ganham +200 ATK, debuffs removidos e cura 100 LP por aliado curado."""
    owner = _owner_player(game_state, event.source)
    healed = 0
    for c in owner.board.get_cards():
        c.atk += 200
        c.base_atk += 200  # permanente: atualiza base para que colorização seja correta
        if getattr(c, "def_temp", 0) < 0:
            c.def_temp = 0
            healed += 1
    if healed:
        owner.hp += healed * 100
    _log(game_state, f"[EVOLVE] Discípulo Solar aura: aliados +200 ATK, {healed} debuffs removidos, +{healed * 100} LP")


# ---------------------------------------------------------------------------
# Habilidades ativas de herói
# ---------------------------------------------------------------------------

def hero_ordem_divina(event, game_state, queue):
    """Guardião da Luz: todos os aliados ficam protegidos e imunes neste turno."""
    owner = _owner_player(game_state, event.source)
    count = 0
    for c in owner.board.get_cards():
        c.protected = True
        c.immune_turns = getattr(c, "immune_turns", 0) + 1
        count += 1
    _log(game_state, f"[HERÓI] Ordem Divina: {count} aliado(s) protegido(s) e imune(s) neste turno")


def hero_degeneracao(event, game_state, queue):
    """Mestre das Sombras: aplica -300 DEF a todas as criaturas inimigas."""
    enemy = game_state.players[1 - game_state.current_player]
    count = 0
    for c in enemy.board.get_cards():
        c.def_temp = getattr(c, "def_temp", 0) - 300
        count += 1
    _log(game_state, f"[HERÓI] Degeneração: {count} criatura(s) inimigas com -300 DEF")


# ---------------------------------------------------------------------------
# Habilidades de evolução (on_evolve)
# ---------------------------------------------------------------------------

def parasita_evo(event, game_state, queue):
    """Parasita Abissal evoluído: +200 ATK por inimigo debuffado atual; destrói inimigos com DEF efetiva ≤ 0."""
    card = event.target
    if card is None:
        return
    owner = _owner_player(game_state, event.source)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner), game_state.current_player)
    enemy = game_state.players[1 - owner_idx]

    debuffed = [c for c in enemy.board.get_cards() if is_debuffed(c)]
    card.atk += len(debuffed) * 200
    _log(game_state, f"[EVOLVE] {card.name}: +{len(debuffed) * 200} ATK ({len(debuffed)} inimigos debuffados)")

    # destrói inimigos cuja DEF efetiva (hp + def_temp) já é ≤ 0
    to_destroy = [c for c in enemy.board.get_cards() if c.hp + getattr(c, "def_temp", 0) <= 0]
    for tgt in to_destroy:
        if enemy.board.remove_card(tgt):
            queue.push(Event(type=EventType.DEATH, source=owner, target=tgt))
            spawn_fragment(Event(type=EventType.DEATH, source=owner, target=tgt, data={}),
                           game_state, queue)
    if to_destroy:
        _log(game_state, f"[EVOLVE] {card.name}: destruiu {len(to_destroy)} inimigo(s) com DEF ≤ 0")


def aberracao_evo(event, game_state, queue):
    """Aberração Costurada evoluída: compra 1 carta; habilita sacrifício de inimigos com DEF < 1000."""
    card = event.target
    if card is None:
        return
    card.aberracao_evolved = True  # flag usada pela UI para permitir sacrificar inimigos com DEF < 1000
    owner = _owner_player(game_state, event.source)
    if owner.deck:
        owner.hand.append(owner.deck.pop(0))
        _log(game_state, f"[EVOLVE] {card.name}: comprou 1 carta (pode sacrificar inimigos DEF < 1000)")
    else:
        _log(game_state, f"[EVOLVE] {card.name}: deck vazio (pode sacrificar inimigos DEF < 1000)")


def horror_evo(event, game_state, queue):
    """Horror Pulsante evoluído: causa 100 dano a cada inimigo com debuff; marca para efeito contínuo."""
    card = event.target
    if card is None:
        return
    card.horror_evolved = True
    owner = _owner_player(game_state, event.source)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner), game_state.current_player)
    enemy = game_state.players[1 - owner_idx]

    debuffed = [c for c in enemy.board.get_cards() if is_debuffed(c)]
    for tgt in debuffed:
        queue.push(Event(type=EventType.DAMAGE, target=tgt, value=100))
    _log(game_state, f"[EVOLVE] {card.name}: 100 dano em {len(debuffed)} inimigo(s) com debuff")


def abominacao_evo(event, game_state, queue):
    """Abominação de Carne evoluída: pode atacar 2x por turno; ao destruir: +200 ATK e gera Fragmento."""
    card = event.target
    if card is None:
        return
    card.can_attack_twice = True
    card.abominacao_evolved = True
    _log(game_state, f"[EVOLVE] {card.name}: pode atacar 2x por turno")


def guardiao_evo(event, game_state, queue):
    """Guardião Radiante evoluído: protege todos os aliados; +300 DEF; aliados não podem ser alvo."""
    card = event.target
    if card is None:
        return
    card.guardian_evolved = True  # flag para lógica de redirecionamento de ataques
    card.def_temp = getattr(card, "def_temp", 0) + 300
    owner = _owner_player(game_state, event.source)
    for c in owner.board.get_cards():
        if c is not card:
            c.protected = True
    _log(game_state, f"[EVOLVE] {card.name}: aliados protegidos, +300 DEF")


def cavaleiro_evo(event, game_state, queue):
    """Cavaleiro da Aurora evoluído: destrói todos os inimigos com debuff; +300 ATK por destruído."""
    card = event.target
    if card is None:
        return
    owner = _owner_player(game_state, event.source)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner), game_state.current_player)
    enemy = game_state.players[1 - owner_idx]

    destroyed = 0
    for tgt in [c for c in enemy.board.get_cards() if is_debuffed(c)]:
        if enemy.board.remove_card(tgt):
            queue.push(Event(type=EventType.DEATH, source=owner, target=tgt))
            card.atk += 300
            destroyed += 1
    _log(game_state, f"[EVOLVE] {card.name}: destruiu {destroyed} inimigo(s) com debuff (+{destroyed * 300} ATK)")


def arcanjo_evo(event, game_state, queue):
    """Arcanjo do Julgamento evoluído: silencia inimigos, remove buffs (reseta para ATK base) e -200 ATK."""
    card = event.target
    if card is None:
        return
    owner = _owner_player(game_state, event.source)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner), game_state.current_player)
    enemy = game_state.players[1 - owner_idx]

    for c in enemy.board.get_cards():
        c.silenced = True
        c.atk = max(0, getattr(c, "base_atk", c.atk))  # remove buffs: volta para ATK base
        c.atk = max(0, c.atk - 200)
    _log(game_state, f"[EVOLVE] {card.name}: inimigos silenciados, buffs removidos, -200 ATK")


def avatar_solar_evo(event, game_state, queue):
    """Avatar Solar evoluído: causa 200 dano ao herói inimigo e a cada criatura inimiga."""
    card = event.target
    if card is None:
        return
    owner = _owner_player(game_state, event.source)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner), game_state.current_player)
    enemy = game_state.players[1 - owner_idx]

    queue.push(Event(type=EventType.DAMAGE, target=enemy, value=200))
    for c in enemy.board.get_cards():
        queue.push(Event(type=EventType.DAMAGE, target=c, value=200))
    _log(game_state, f"[EVOLVE] {card.name}: 200 dano global ao inimigo")
