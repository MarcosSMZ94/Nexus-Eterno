from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from nexus.domain.events.queue import EventQueue
from nexus.domain.events.event import Event
from nexus.domain.events.types import EventType

from nexus.domain.state.game_state import GameState
from nexus.domain.state.player_state import PlayerState

from nexus.application.event_resolver import EventResolver
from nexus.application.turn_manager import TurnManager
from nexus.application.command_handler import CommandHandler

from nexus.application.handlers.register_handlers import register_all

from nexus.domain.cards.loader import load_cards
from nexus.domain.cards.deck_loader import load_deck_by_id, load_decks


# -------------------------
# Setup inicial
# -------------------------
queue = EventQueue()
resolver = EventResolver(queue)

register_all(resolver)

turn_manager = TurnManager()
commands = CommandHandler(queue, turn_manager)

# jogadores
p1 = PlayerState("Player 1 - Mestre das Sombras")
p2 = PlayerState("Player 2 - Guardião da Luz")

game_state = GameState(p1, p2)

# -------------------------
# Carregar decks
# -------------------------
print("\n=== CARREGANDO DECKS ===\n")

all_cards = load_cards()
all_cards_dict = {card.id: card for card in all_cards}
decks_data = load_decks()

deck1 = load_deck_by_id("deck_shadow_master", decks_data, all_cards_dict)
deck2 = load_deck_by_id("deck_light_guardian", decks_data, all_cards_dict)

print(f"Deck 1: {deck1['name']} ({len(deck1['cards'])} cartas)")
print(f"Deck 2: {deck2['name']} ({len(deck2['cards'])} cartas)")

# Colocar cartas iniciais na mão
p1.hand.extend(deck1["cards"][:4])
p2.hand.extend(deck2["cards"][:4])

# Adicionar o Guerreiro Solar e a Abominação à mão para teste
for card in deck1["cards"]:
    if card.id == "guerreiro_solar":
        p1.hand.append(card)
        break

# Adicionar a Abominação à mão para teste
abominacao = deck1["cards"][10]  # A Abominação está na posição 10
p1.hand.append(abominacao)

# -------------------------
# INÍCIO DO JOGO
# -------------------------
print("\n=== INÍCIO DO TESTE ===\n")

# simular começo do turno
queue.push(Event(type=EventType.TURN_START))

# avançar até MAIN_1
for _ in range(4):
    commands.pass_phase(game_state)
    resolver.resolve(game_state)

# -------------------------
# INVOCAR CRIATURAS
# -------------------------
#print("\n--- Invocando criaturas ---\n")

# Player 1: invocar 2 Parasitas + Guerreiro Solar
parasita1 = None
parasita2 = None
guerreiro = None

for card in p1.hand:
    if card.id == "parasita_sombrio" and parasita1 is None:
        parasita1 = card
    elif card.id == "parasita_sombrio" and parasita2 is None:
        parasita2 = card
    elif card.id == "guerreiro_solar":
        guerreiro = card

if parasita1:
    commands.play_card(game_state, parasita1)
    resolver.resolve(game_state)

if parasita2:
    commands.play_card(game_state, parasita2)
    resolver.resolve(game_state)

if guerreiro:
    commands.play_card(game_state, guerreiro)
    resolver.resolve(game_state)

print("\nBoard após invocações iniciais:")
for c in p1.board.get_cards():
    print(f"- {c.name} (ATK: {c.atk}, HP: {c.hp})")

# -------------------------
# INVOCAR BOSS (COM SACRIFÍCIO)
# -------------------------
print("\n--- Invocando criatura de alto nível (Abominação) ---\n")

commands.play_card(game_state, abominacao)
resolver.resolve(game_state)

print("\nBoard final:")
for c in p1.board.get_cards():
    print(f"- {c.name} (ATK: {c.atk}, HP: {c.hp})")

print("\n=== FIM DO TESTE ===")