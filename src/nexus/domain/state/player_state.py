from nexus.domain.state.board_state import BoardState

class PlayerState:
    def __init__(self, name):
        self.name = name
        self.hp = 4000
        self.mana = 0

        self.deck = []
        self.hand = []

        self.board = BoardState()

        self.hero_cooldowns = {}