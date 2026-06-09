from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from nexus.application.engine import Engine

engine = Engine()
engine.setup_game(initial_hand=5)

p = engine.game_state.players[engine.game_state.current_player]
print('Before hand:')
for c in p.hand:
    print('-', c.name)

ok = engine.mulligan()
print('Mulligan performed:', ok)
print('After hand:')
for c in p.hand:
    print('-', c.name)

print('Deck size:', len(p.deck))
