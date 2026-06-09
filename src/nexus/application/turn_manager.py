from nexus.domain.turn.phase import Phase
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

PHASE_ORDER = [
    Phase.DRAW,
    Phase.NEXUS,
    Phase.MANA,
    Phase.MAIN_1,
    Phase.BATTLE,
    Phase.MAIN_2,
    Phase.END
]

class TurnManager:
    def next_phase(self, game_state, queue):
        current_index = PHASE_ORDER.index(game_state.current_phase)

        if current_index + 1 < len(PHASE_ORDER):
            next_phase = PHASE_ORDER[current_index + 1]
        else:
            # troca turno
            prev_idx = game_state.current_player
            try:
                prev_player = game_state.players[prev_idx]
                if not getattr(prev_player, 'first_turn_done', False):
                    prev_player.first_turn_done = True
                    prev_player.mulligan_active = False
            except Exception:
                pass

            game_state.current_player = 1 - game_state.current_player
            game_state.turn_count += 1
            next_phase = Phase.DRAW

            try:
                new_player = game_state.players[game_state.current_player]
                new_player.mulligan_active = not getattr(new_player, 'first_turn_done', False)
                new_player.summons_this_turn = 0
                # libera os ataques das criaturas do jogador que está começando o turno
                for c in new_player.board.get_cards():
                    c.has_attacked = False
                    c.attacks_this_turn = 0
                # decrementa order_lock_turns do jogador que está COMEÇANDO seu turno
                if getattr(new_player, "order_lock_turns", 0) > 0:
                    new_player.order_lock_turns -= 1
                # zera mortes do turno anterior para scales_with_deaths
                game_state.deaths_this_turn = 0
            except Exception:
                pass

            queue.push(Event(type=EventType.TURN_START))

        game_state.current_phase = next_phase
        # log phase change
        try:
            game_state.add_log(f"[PHASE] {next_phase}")
        except Exception:
            import logging
            logging.info(f"[PHASE] {next_phase}")

        queue.push(Event(
            type=EventType.PHASE_CHANGED,
            data={"phase": next_phase}
        ))