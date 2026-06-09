from nexus.domain.events.types import EventType
from nexus.domain.abilities.registry import get_ability_registry

GLOBAL_TRIGGER_MAP = {
    "buff_on_death": {EventType.DEATH},
    "scales_with_deaths": {EventType.DEATH},
    "atk_per_ally": {EventType.SUMMON},
    "protect_allies": {EventType.SUMMON},
    "permanent_def": {EventType.SUMMON},
    "cycle_effects": {EventType.TURN_START},
}

def execute_ability(ability_id, event, game_state, queue):
    try:
        get_ability_registry().execute(ability_id, event, game_state, queue)
    except Exception as e:
        try:
            game_state.add_log(f"[ERROR] {ability_id}: {e}")
        except Exception:
            import logging
            logging.exception(f"[ERROR] {ability_id}: {e}")

def _event_type_name(event):
    return getattr(getattr(event, "type", None), "name", None)

def _iter_candidate_cards(event, game_state):
    cards = []

    for source in (getattr(event, "source", None), getattr(event, "target", None)):
        if source is not None and hasattr(source, "abilities"):
            cards.append(source)

    if event.type in {EventType.TURN_START, EventType.END_PHASE} and game_state:
        for player in game_state.players:
            cards.extend(player.board.get_cards())

    seen = set()
    for card in cards:
        marker = id(card)
        if marker in seen:
            continue
        seen.add(marker)
        yield card

def _iter_board_cards(game_state):
    if not game_state:
        return

    seen = set()
    for player in game_state.players:
        for card in player.board.get_cards():
            marker = id(card)
            if marker in seen:
                continue
            seen.add(marker)
            yield card

def _matches_trigger(ability_def, event):
    trigger = ability_def.trigger
    if trigger == event.type:
        return True

    if isinstance(trigger, str):
        event_name = _event_type_name(event)
        if trigger == event_name:
            return True

        if "/" in trigger:
            return event_name in {part.strip() for part in trigger.split("/")}

        if trigger == "GLOBAL":
            return event.type in GLOBAL_TRIGGER_MAP.get(ability_def.ability_id, set())

        if trigger == "ONCE":
            return event.type == EventType.SUMMON

    return False

def _order_locked(card, game_state):
    if not getattr(card, "evolved", False):
        return False
    for player in getattr(game_state, "players", []):
        if card in player.board.get_cards():
            return getattr(player, "order_lock_turns", 0) > 0
    return False


def trigger_matching_abilities(event, game_state, queue):
    for card in _iter_candidate_cards(event, game_state):
        if not card.abilities:
            continue

        for ability_def in card.abilities:
            if _matches_trigger(ability_def, event):
                # Ordem Absoluta: bloqueia efeitos de criaturas já evoluídas
                if _order_locked(card, game_state):
                    try:
                        game_state.add_log(f"[ORDEM] {card.name} (evoluída) teve efeito bloqueado pela Ordem Absoluta")
                    except Exception:
                        pass
                    continue
                if event.data is None:
                    event.data = {}
                event.data["card"] = card
                # injetar params da ability para que _param() leia valores corretos
                for k, v in ability_def.params.items():
                    if k not in event.data:
                        event.data[k] = v
                try:
                    game_state.add_log(f"[TRIGGER] {card.name} ativa {ability_def.ability_id}")
                except Exception:
                    import logging
                    logging.info(f"[TRIGGER] {card.name} ativa {ability_def.ability_id}")
                execute_ability(ability_def.ability_id, event, game_state, queue)

    if event.type in {EventType.SUMMON, EventType.DEATH, EventType.SACRIFICE, EventType.CAST, EventType.ATTACK}:
        for card in _iter_board_cards(game_state):
            if not card.abilities:
                continue

            for ability_def in card.abilities:
                if ability_def.trigger != "GLOBAL":
                    continue
                if not _matches_trigger(ability_def, event):
                    continue

                # Ordem Absoluta: bloqueia efeitos de criaturas já evoluídas
                if _order_locked(card, game_state):
                    try:
                        game_state.add_log(f"[ORDEM] {card.name} (evoluída) teve efeito bloqueado pela Ordem Absoluta")
                    except Exception:
                        pass
                    continue

                if event.data is None:
                    event.data = {}
                event.data["card"] = card
                # injetar params da ability para que _param() leia valores corretos
                for k, v in ability_def.params.items():
                    if k not in event.data:
                        event.data[k] = v
                try:
                    game_state.add_log(f"[TRIGGER] {card.name} ativa {ability_def.ability_id}")
                except Exception:
                    import logging
                    logging.info(f"[TRIGGER] {card.name} ativa {ability_def.ability_id}")
                execute_ability(ability_def.ability_id, event, game_state, queue)

def trigger_abilities_for_event(event, game_state, queue, trigger_type):
    for card in _iter_candidate_cards(event, game_state):
        if not card.abilities:
            continue

        for ability_def in card.abilities:
            if ability_def.trigger == trigger_type:
                try:
                    game_state.add_log(f"[TRIGGER] {card.name} ativa {ability_def.ability_id}")
                except Exception:
                    import logging
                    logging.info(f"[TRIGGER] {card.name} ativa {ability_def.ability_id}")
                execute_ability(ability_def.ability_id, event, game_state, queue)

def handle_summon_triggers(event, game_state, queue):
    trigger_matching_abilities(event, game_state, queue)

def handle_death_triggers(event, game_state, queue):
    trigger_matching_abilities(event, game_state, queue)

def handle_sacrifice_triggers(event, game_state, queue):
    trigger_matching_abilities(event, game_state, queue)

def handle_attack_triggers(event, game_state, queue):
    trigger_matching_abilities(event, game_state, queue)

def handle_end_phase_triggers(event, game_state, queue):
    trigger_matching_abilities(event, game_state, queue)

def handle_turn_start_triggers(event, game_state, queue):
    # Corrupção Progressiva: aplica -200 DEF por turno durante corruption_ticks turnos restantes
    for player in game_state.players:
        for card in player.board.get_cards():
            ticks = getattr(card, "corruption_ticks", 0)
            if ticks > 0:
                card.def_temp = getattr(card, "def_temp", 0) - 200
                card.corruption_ticks = ticks - 1
                try:
                    game_state.add_log(f"[CORRUPTION] {card.name} -200 DEF (restam {card.corruption_ticks} turnos)")
                except Exception:
                    pass
    trigger_matching_abilities(event, game_state, queue)

def handle_buff_triggers(event, game_state, queue):
    trigger_matching_abilities(event, game_state, queue)

def handle_cast_triggers(event, game_state, queue):
    # Habilidade ativa de herói: ability_id direto no data (source = PlayerState, sem card)
    if event.data and event.data.get("ability_id"):
        execute_ability(event.data["ability_id"], event, game_state, queue)
    trigger_matching_abilities(event, game_state, queue)
