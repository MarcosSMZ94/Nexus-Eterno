from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType
from nexus.domain.turn.phase import Phase

MAIN_PHASES = (Phase.MAIN_1, Phase.MAIN_2)

class CommandHandler:
    def __init__(self, queue, turn_manager):
        self.queue = queue
        self.turn_manager = turn_manager

    def pass_phase(self, game_state):
        self.turn_manager.next_phase(game_state, self.queue)

    def play_card(self, game_state, card, sacrifice_targets=None, target_card=None, sacrifice_ally=None):
        player = game_state.players[game_state.current_player]

        # só pode jogar nas fases principais
        if game_state.current_phase not in MAIN_PHASES:
            self._log(game_state, "[PLAY] Só é possível jogar cartas na Fase Principal")
            return

        # a carta precisa estar na mão do jogador atual
        if card not in player.hand:
            self._log(game_state, "[PLAY] Carta não está na sua mão")
            return

        # a primeira jogada da partida trava a janela de mulligan
        player.mulligan_active = False

        if getattr(card, "card_type", "creature") == "spell":
            cost = getattr(card, "cost_mana", 0)
            if player.mana < cost:
                self._log(game_state, f"[CAST] Mana insuficiente ({player.mana}/{cost})")
                return
            player.mana -= cost
            player.hand.remove(card)
            self.queue.push(Event(
                type=EventType.CAST,
                source=player,
                target=card,
                data={"card_id": getattr(card, "id", None),
                      "spell_target":    target_card,
                      "spell_sacrifice": sacrifice_ally},
            ))
            return

        self.queue.push(Event(
            type=EventType.SUMMON_REQUEST,
            target=card,
            data={"sacrifice_targets": sacrifice_targets},
        ))

    def evolve_card(self, game_state, card):
        """Evolui uma criatura no campo: custa mana, +600 ATK/HP, marca como evoluída."""
        if card.evolved:
            self._log(game_state, "[EVOLVE] Carta já foi evoluída")
            return
        if card.evolution is None:
            self._log(game_state, "[EVOLVE] Carta não pode evoluir")
            return
        if card.board_position is None:
            self._log(game_state, "[EVOLVE] Carta não está no campo")
            return
        player = game_state.players[game_state.current_player]
        cost = card.evolution.get("cost", 2)
        # passivo Mutação: Mestre das Sombras evolui criaturas Sombra com -1 mana (mínimo 1)
        if getattr(player, "hero_id", None) == "lord_of_shadows" and getattr(card, "element", "") == "SHADOW":
            cost = max(1, cost - 1)
        if player.mana < cost:
            self._log(game_state, f"[EVOLVE] Mana insuficiente ({player.mana}/{cost})")
            return
        player.mana -= cost
        card.atk += 600
        card.base_atk += 600
        card.hp += 600
        card.evolved = True
        self._log(game_state, f"[EVOLVE] {card.name} evoluiu!")
        # disparar habilidade de evolução específica da carta, se definida
        on_evolve = card.evolution.get("on_evolve") if card.evolution else None
        if on_evolve:
            from nexus.domain.events.event import Event
            from nexus.domain.events.types import EventType
            self.queue.push(Event(
                type=EventType.CAST,
                source=player,
                target=card,
                data={"ability_id": on_evolve},
            ))

    def _log(self, game_state, message):
        try:
            game_state.add_log(message)
        except Exception:
            import logging
            logging.info(message)
