from nexus.domain.turn.phase import Phase

class GameState:
    def __init__(self, player1, player2):
        self.players = [player1, player2]
        self.current_player = 0

        self.current_phase = Phase.DRAW
        self.turn_count = 1

        self.nexus_element = None
        self.log = []

    def add_log(self, message: str):
        self.log.append(message)

    def get_logs(self):
        return list(self.log)

    def clear_logs(self):
        self.log.clear()