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
        self.hero_id = None       # id do herói associado ao deck (ex: "solar_champion")
        self.passive_used = False  
        self.first_turn_done = False
        self.mulligan_active = False
        self.summons_this_turn = 0
        self.order_lock_turns = 0  # Ordem Absoluta: bloqueia ataques Nv5+ e efeitos de evoluídos