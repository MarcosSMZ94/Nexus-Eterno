import json
import os
import time
import random
import copy
from threading import Thread

from nexus.domain.events.queue import EventQueue
from nexus.application.event_resolver import EventResolver
from nexus.application.handlers.register_handlers import register_all
from nexus.application.turn_manager import TurnManager
from nexus.application.command_handler import CommandHandler
from nexus.domain.state.player_state import PlayerState
from nexus.domain.state.game_state import GameState
from nexus.domain.cards.deck_loader import load_deck_by_id
from nexus.domain.cards.loader import load_cards
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType
import logging


def _load_heroes():
    """Carrega heroes.json e retorna dict id→hero_def."""
    path = os.path.join(os.path.dirname(__file__), "..", "data", "heroes.json")
    with open(path, "r", encoding="utf-8") as f:
        return {h["id"]: h for h in json.load(f)}


class Engine:
    def __init__(self):
        self.queue = EventQueue()
        self.resolver = EventResolver(self.queue)

        register_all(self.resolver)
        self.turn_manager = TurnManager()
        self.command_handler = CommandHandler(self.queue, self.turn_manager)
        
        self.game_state = None

        self._running = False
        self._thread = None

    def setup_game(self, player1_name: str = "Player 1", player2_name: str = "Player 2", deck1_id: str = None, deck2_id: str = None, initial_hand: int = 4):
        p1 = PlayerState(player1_name)
        p2 = PlayerState(player2_name)

        all_cards = {c.id: c for c in load_cards()}

        if deck1_id:
            deck1_data = load_deck_by_id(deck1_id, None, all_cards)
            deck1_cards = deck1_data["cards"]
            p1.hero_id = deck1_data.get("hero") or None
        else:
            deck1_cards = list(all_cards.values())[:30]

        if deck2_id:
            deck2_data = load_deck_by_id(deck2_id, None, all_cards)
            deck2_cards = deck2_data["cards"]
            p2.hero_id = deck2_data.get("hero") or None
        else:
            deck2_cards = list(all_cards.values())[:30]

        random.seed(None)
        
        p1.deck = [copy.deepcopy(c) for c in deck1_cards]
        p2.deck = [copy.deepcopy(c) for c in deck2_cards]
        random.shuffle(p1.deck)
        random.shuffle(p2.deck)

        # Draw inicial
        for _ in range(initial_hand):
            if p1.deck:
                p1.hand.append(p1.deck.pop(0))
            if p2.deck:
                p2.hand.append(p2.deck.pop(0))

        self.game_state = GameState(p1, p2)

        # libera mulligan ilimitado para o jogador que inicia (até a 1ª jogada)
        starting = self.game_state.players[self.game_state.current_player]
        starting.mulligan_active = True

        # Push evento inicial para configurar o estado corretamente
        self.queue.push(self._make_phase_event(self.game_state.current_phase))

    def _make_phase_event(self, phase):
        return Event(type=EventType.PHASE_CHANGED, data={"phase": phase})

    def start(self, in_thread: bool = True):
        if self.game_state is None:
            raise RuntimeError("Game not initialized. Call setup_game() first.")

        if self._running:
            return

        self._running = True

        if in_thread:
            self._thread = Thread(target=self.run, daemon=True)
            self._thread.start()
        else:
            self.run()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def run(self):
        # main loop
        try:
            while self._running:
                # resolve eventos na fila até esvaziar, processando gatilhos e atualizando o estado do jogo
                self.resolver.resolve(self.game_state)

                # Pausa breve para evitar loop muito apertado quando a fila esvazia
                time.sleep(0.05)
        except Exception as e:
            if self.game_state:
                try:
                    self.game_state.add_log(f"[Engine] Exception in run loop: {e}")
                except Exception:
                    logging.exception(f"[Engine] Exception in run loop: {e}")
            else:
                logging.exception(f"[Engine] Exception in run loop: {e}")
        finally:
            self._running = False

    # ------------------------------------------------------------------
    def use_hero_ability(self, game_state):
        player = game_state.players[game_state.current_player]
        heroes = _load_heroes()
        hero = heroes.get(getattr(player, "hero_id", None))
        if not hero:
            return False

        cost = hero["active"]["mana_cost"]
        if player.mana < cost:
            try:
                game_state.add_log(f"[HERÓI] Mana insuficiente ({player.mana}/{cost})")
            except Exception:
                pass
            return False

        player.mana -= cost
        ability_id = hero["active"]["ability_id"]
        game_state.add_log(f"[HERÓI] {player.name} ativou {hero['active']['name']}")
        self.queue.push(Event(
            type=EventType.CAST,
            source=player,
            target=None,
            data={"ability_id": ability_id, "hero": True},
        ))
        return True

    def apply_passive_if_needed(self, game_state):
        #Verifica e aplica passivos de uso único.
        triggered = False
        for player in game_state.players:
            hero_id = getattr(player, "hero_id", None)
            # Luz Inextinguível (solar_champion): retorna de 0 LP com 500 LP e limpa o campo
            if (hero_id == "solar_champion"
                    and player.hp <= 0
                    and not getattr(player, "passive_used", False)):
                player.passive_used = True
                player.hp = 500
                # remove todas as criaturas de ambos os lados
                for p in game_state.players:
                    for card in p.board.get_cards()[:]:
                        p.board.remove_card(card)
                try:
                    game_state.add_log(
                        f"[PASSIVO] Luz Inextinguível! {player.name} retorna com 500 LP!"
                    )
                except Exception:
                    pass
                triggered = True
        return triggered

    # ------------------------------------------------------------------
    def evolve_card(self, card):
        self.command_handler.evolve_card(self.game_state, card)

    def play_card(self, card, sacrifice_targets=None, target_card=None, sacrifice_ally=None):
        self.command_handler.play_card(self.game_state, card,
                                       sacrifice_targets=sacrifice_targets,
                                       target_card=target_card,
                                       sacrifice_ally=sacrifice_ally)

    def attack(self, attacker, target=None):
        player = self.game_state.players[self.game_state.current_player]
        if getattr(player, "order_lock_turns", 0) > 0 and getattr(attacker, "level", 0) >= 5:
            try:
                self.game_state.add_log(
                    f"[ORDEM] {attacker.name} (Nv{attacker.level}) não pode atacar — Ordem Absoluta ativa"
                )
            except Exception:
                pass
            return

        self.queue.push(Event(type=EventType.ATTACK, source=attacker, target=target))

    def mulligan(self, player_index: int = None):
        if player_index is None:
            player_index = self.game_state.current_player

        player = self.game_state.players[player_index]
        if getattr(player, 'first_turn_done', False):
            return False

        # mulligan trava após a 1ª jogada (ou após "Pronto")
        if not getattr(player, 'mulligan_active', False):
            return False

        hand_size = len(player.hand)
        player.deck.extend(player.hand)
        player.hand.clear()
        random.shuffle(player.deck)
        for _ in range(hand_size):
            if player.deck:
                player.hand.append(player.deck.pop(0))

        try:
            self.game_state.add_log(f"[MULLIGAN] {player.name} realizou mulligan (mão trocada)")
        except Exception:
            import logging
            logging.info(f"[MULLIGAN] {player.name} realizou mulligan (mão trocada)")

        player.mulligan_active = True
        return True

    def confirm_hand(self, player_index: int = None):
        if player_index is None:
            player_index = self.game_state.current_player

        player = self.game_state.players[player_index]
        player.mulligan_active = False

        try:
            self.game_state.add_log(f"[MULLIGAN] {player.name} confirmou a mão")
        except Exception:
            import logging
            logging.info(f"[MULLIGAN] {player.name} confirmou a mão")

        return True

    def pass_phase(self):
        self.command_handler.pass_phase(self.game_state)

def make_demo_engine():
    e = Engine()
    e.setup_game(deck1_id="deck_sol", deck2_id="deck_sombra", initial_hand=4)
    return e
