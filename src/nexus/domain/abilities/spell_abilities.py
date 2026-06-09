"""Habilidades de feitiços e efeitos CAST."""
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType
from nexus.domain.abilities.helpers import _owner_player, _param, _log, is_debuffed

def apply_debuff_def(event, game_state, queue):
    # identificar o dono da carta que ativou o efeito
    card = (event.data.get("card") if event.data else None) or event.target
    owner = _owner_player(game_state, card)
    owner_idx = next((i for i, p in enumerate(game_state.players) if p is owner),
                     game_state.current_player)
    enemy = game_state.players[1 - owner_idx]
    enemy_cards = enemy.board.get_cards()
    if not enemy_cards:
        return

    target = enemy_cards[0]  # primeira criatura inimiga (sem seleção de alvo)
    amount = int(_param(event, "amount", _param(event, "value", 200)) or 200)
    target.def_temp = getattr(target, "def_temp", 0) - amount

    # dispara extra_debuff de aliados com ON_ENEMY_DEBUFF (ex: Parasita Abissal evoluído)
    for c in owner.board.get_cards():
        for ability in getattr(c, "abilities", []):
            if ability.ability_id == "extra_debuff":
                extra_event = Event(type=EventType.CAST, source=owner, target=target,
                                    data={"amount": -100})
                extra_debuff(extra_event, game_state, queue)

    _log(game_state, f"[ABILITY] apply_debuff_def: {target.name} -{amount} DEF")

def extra_debuff(event, game_state, queue):
    target = event.target
    amount = int(_param(event, "amount", -100) or -100)
    if not target:
        return
    target.def_temp = getattr(target, "def_temp", 0) + amount
    _log(game_state, f"[ABILITY] {target.name} recebeu debuff extra {amount}")

def draw_cards(event, game_state, queue):
    count = int(_param(event, "count", _param(event, "value", 1)) or 1)
    player = _owner_player(game_state, event.source)
    for _ in range(count):
        if player.deck:
            player.hand.append(player.deck.pop(0))
    _log(game_state, f"[ABILITY] {player.name} comprou {count} carta(s)")

def destroy_target(event, game_state, queue):
    """Destrói criatura inimiga. Se alvo for Nv6+: causa 300 dano ao herói inimigo.
    Fragmentos gerados pela morte do alvo são redirecionados para o campo de quem jogou a carta."""
    target = (event.data.get("spell_target") if event.data else None) or event.target
    if not target:
        return
    enemy_idx = 1 - game_state.current_player
    enemy = game_state.players[enemy_idx]
    caster = _owner_player(game_state, event.source)
    target_level = getattr(target, "level", 0)
    if enemy.board.remove_card(target):
        _log(game_state, f"[ABILITY] {target.name} destruído")
        # redirect_spawn_to: fragmentos gerados pela morte do alvo vão para o campo do caster
        queue.push(Event(type=EventType.DEATH, source=caster, target=target,
                         data={"redirect_spawn_to": caster}))
        if target_level >= 6:
            queue.push(Event(type=EventType.DAMAGE, target=enemy, value=300))
            _log(game_state, f"[ABILITY] Miniatura: alvo Nv{target_level} → 300 dano ao herói inimigo")

def spawn_fragment(event, game_state, queue):
    from nexus.domain.cards.models import Card
    # event.data["card"] = carta dona da habilidade (ex: Larva da Carne Viva)
    # Para DEATH: carta ainda está no board → _owner_player a encontra e retorna o dono correto
    # Para SACRIFICE: carta já fora do board → _owner_player cai no fallback current_player (correto)
    # NÃO usar event.source: em DEATH por combate, source = inimigo que matou
    # redirect_spawn_to: Miniatura de Sol Ardente redireciona fragmentos para o campo do caster
    redirect_to = (event.data.get("redirect_spawn_to") if event.data else None)
    if redirect_to is not None:
        owner = redirect_to
    else:
        ref = (event.data.get("card") if event.data else None) or event.target
        owner = _owner_player(game_state, ref)
    count = int(_param(event, "count", _param(event, "value", 1)) or 1)

    spawned = 0
    for _ in range(max(1, count)):
        frag = Card("fragment", "Fragmento", 0, 50, 100, "NEUTRAL", "creature", [])
        if owner.board.add_card(frag):
            spawned += 1

    if spawned:
        _log(game_state, f"[ABILITY] {owner.name} gerou {spawned} Fragmento(s)")

def heal_and_draw(event, game_state, queue):
    """ON_DESTROY (=DEATH): cura 300 LP ao destruir inimigo; saca 1 carta SOMENTE se o alvo tinha debuff."""
    card = event.data.get("card") if event.data else None
    # só ativa quando esta carta é o atacante que destruiu (source), não quando ela morre (target)
    if card is None or card is not event.source:
        return
    owner = _owner_player(game_state, card)
    amount = int(_param(event, "heal", _param(event, "amount", 300)) or 300)
    owner.hp += amount
    # compra carta apenas se o inimigo destruído tinha qualquer debuff ativo
    had_debuff = is_debuffed(event.target) if event.target else False
    if had_debuff and owner.deck:
        drawn = owner.deck.pop(0)
        owner.hand.append(drawn)
        _log(game_state, f"[ABILITY] {card.name}: +{amount} LP + sacou (alvo tinha debuff)")
    else:
        _log(game_state, f"[ABILITY] {card.name}: +{amount} LP" + (" (sem debuff, sem saque)" if not had_debuff else " (deck vazio)"))

def ritual_degeneracao(event, game_state, queue):
    player = _owner_player(game_state, event.source)
    board = player.board.get_cards()
    if not board:
        return
    sac = (event.data.get("spell_sacrifice") if event.data else None) or board[0]
    is_larva_or_frag = getattr(sac, "id", "") in ("larva_carne_viva", "fragment")
    player.board.remove_card(sac)
    if not hasattr(game_state, "sacrificed_cards"):
        game_state.sacrificed_cards = []
    game_state.sacrificed_cards.append(sac)
    queue.push(Event(type=EventType.SACRIFICE, source=player, target=sac, data={"sacrificed": sac}))
    queue.push(Event(type=EventType.DEATH, source=player, target=sac))
    for _ in range(2):
        if player.deck:
            player.hand.append(player.deck.pop(0))
    # +500 ATK para a primeira criatura que sobrou no campo
    remaining = player.board.get_cards()
    if remaining:
        remaining[0].atk += 500
        _log(game_state, f"[ABILITY] {remaining[0].name} ganhou +500 ATK")
    # bônus: Larva ou Fragmento sacrificado → gera mais 1 Fragmento
    if is_larva_or_frag:
        spawn_fragment(event, game_state, queue)
    _log(game_state, f"[ABILITY] ritual_degeneracao: sacrificado {sac.name}, +2 cartas")

def corrupcao_progressiva(event, game_state, queue):
    """Aplica -200 DEF imediatamente e configura 2 ticks adicionais (-200/turno por mais 2 turnos).
    Total: -600 DEF ao longo de 3 turnos.
    """
    target = (event.data.get("spell_target") if event.data else None) or event.target
    if not target:
        return
    # 1ª aplicação imediata
    target.def_temp = getattr(target, "def_temp", 0) - 200
    # configura 2 ticks restantes (processados no início dos próximos 2 turnos)
    target.corruption_ticks = getattr(target, "corruption_ticks", 0) + 2
    _log(game_state, f"[ABILITY] corrupcao_progressiva: {target.name} -200 DEF agora + 2 turnos")

def banquete_profano(event, game_state, queue):
    """Sacrifica 1 aliado: causa ATK dele ao alvo inimigo.
    Se alvo morrer (HP efetivo ≤ 0): gera 1 Fragmento + ativa efeitos de sacrifício no alvo.
    """
    player = _owner_player(game_state, event.source)
    board_cards = player.board.get_cards()
    if not board_cards:
        return
    victim = (event.data.get("spell_sacrifice") if event.data else None) or board_cards[0]
    if victim is None:
        return
    atk = victim.atk
    player.board.remove_card(victim)
    if not hasattr(game_state, "sacrificed_cards"):
        game_state.sacrificed_cards = []
    game_state.sacrificed_cards.append(victim)
    queue.push(Event(type=EventType.SACRIFICE, source=player, target=victim, data={"sacrificed": victim}))
    queue.push(Event(type=EventType.DEATH, source=player, target=victim))

    tgt = (event.data.get("spell_target") if event.data else None) or event.target
    if tgt:
        tgt.hp -= atk
        # morte quando HP efetivo (hp + def_temp) ≤ 0 — Yu-Gi-Oh Damage Step
        eff = tgt.hp + getattr(tgt, "def_temp", 0)
        if eff <= 0:
            enemy = game_state.players[1 - game_state.current_player]
            enemy.board.remove_card(tgt)
            queue.push(Event(type=EventType.DEATH, source=player, target=tgt))
            # Se alvo morreu: ativa efeitos de sacrifício + gera Fragmento
            queue.push(Event(type=EventType.SACRIFICE, source=player, target=tgt, data={"sacrificed": tgt}))
            frag_event = Event(type=EventType.DEATH, source=player, target=tgt, data={})
            spawn_fragment(frag_event, game_state, queue)
    _log(game_state, f"[ABILITY] banquete_profano: {victim.name} sacrificado, {atk} dano ao alvo")

def explosao_radiante(event, game_state, queue):
    """Destrói criatura inimiga com ATK ≥ 1500. Se a criatura tinha debuff: +300 dano ao herói inimigo."""
    enemy = game_state.players[1 - game_state.current_player]
    target = event.data.get("spell_target") if event.data else None
    if target is None:
        candidates = [c for c in enemy.board.get_cards() if c.atk >= 1500]
        if not candidates:
            _log(game_state, "[ABILITY] explosao_radiante: nenhum alvo com ATK ≥ 1500")
            return
        target = max(candidates, key=lambda c: c.atk)
    had_debuff = is_debuffed(target)
    if enemy.board.remove_card(target):
        queue.push(Event(type=EventType.DEATH, source=_owner_player(game_state, event.source), target=target))
        if had_debuff:
            queue.push(Event(type=EventType.DAMAGE, target=enemy, value=300))
            _log(game_state, f"[ABILITY] explosao_radiante: {target.name} tinha debuff → 300 dano ao herói inimigo")
        else:
            _log(game_state, f"[ABILITY] explosao_radiante destruiu {target.name}")

def luz_purificadora(event, game_state, queue):
    """Remove TODOS os debuffs ativos das criaturas aliadas: DEF, ATK, silêncio e corrupção.
    Cura 100 LP por criatura purificada (ao menos um debuff removido).
    """
    owner = _owner_player(game_state, event.source)
    removed = 0
    for c in owner.board.get_cards():
        cleared = False
        # DEF debuff: def_temp negativo
        if getattr(c, "def_temp", 0) < 0:
            c.def_temp = 0
            cleared = True
        # ATK debuff: atk abaixo da base (ex: weaken_enemy)
        base = getattr(c, "base_atk", None)
        if base is not None and c.atk < base:
            c.atk = base
            cleared = True
        # Silêncio
        if getattr(c, "silenced", False):
            c.silenced = False
            cleared = True
        # Corrupção Progressiva
        if getattr(c, "corruption_ticks", 0) > 0:
            c.corruption_ticks = 0
            cleared = True
        c.hp += 100
        if cleared:
            removed += 1
    if removed:
        owner.hp += removed * 100
    _log(game_state, f"[ABILITY] luz_purificadora: {removed} criatura(s) purificada(s)")
