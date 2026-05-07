from nexus.domain.turn.phase import Phase

class GameState:
    def __init__(self, player1, player2):
        self.players = [player1, player2]
        self.current_player = 0

        self.current_phase = Phase.DRAW
        self.turn_count = 1

        self.nexus_element = None