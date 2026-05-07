import json
import os

from nexus.domain.cards.loader import load_cards


def load_decks(path: str = None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "decks.json")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    decks = {}

    for deck_data in data:
        decks[deck_data["id"]] = {
            "name": deck_data.get("name", ""),
            "hero": deck_data.get("hero", ""),
            "card_ids": deck_data.get("cards", [])
        }

    return decks


def build_deck_from_ids(card_ids: list, all_cards: dict):
    deck = []
    for card_id in card_ids:
        if card_id in all_cards:
            card = all_cards[card_id]
            deck.append(card)
        else:
            print(f"Aviso: Carta {card_id} não encontrada")
    return deck


def load_deck_by_id(deck_id: str, decks_data: dict = None, cards_data: dict = None):
    if decks_data is None:
        decks_data = load_decks()
    
    if cards_data is None:
        cards = load_cards()
        cards_data = {card.id: card for card in cards}
    
    if deck_id not in decks_data:
        raise ValueError(f"Deck '{deck_id}' não encontrado")
    
    deck_info = decks_data[deck_id]
    deck_cards = build_deck_from_ids(deck_info["card_ids"], cards_data)
    
    return {
        "id": deck_id,
        "name": deck_info["name"],
        "hero": deck_info["hero"],
        "cards": deck_cards
    }
