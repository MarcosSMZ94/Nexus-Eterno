class BoardState:
    MAX_SLOTS = 3

    def __init__(self):
        self.slots = [None] * self.MAX_SLOTS

    def get_free_slot_index(self):
        for i, card in enumerate(self.slots):
            if card is None:
                return i
        return None

    def add_card(self, card):
        idx = self.get_free_slot_index()
        if idx is None:
            return False

        self.slots[idx] = card
        card.board_position = idx
        return True

    def remove_card(self, card):
        idx = card.board_position
        if idx is not None and self.slots[idx] == card:
            self.slots[idx] = None
            card.board_position = None
            return True
        return False

    def get_cards(self):
        return [c for c in self.slots if c is not None]

    def count(self):
        return len(self.get_cards())