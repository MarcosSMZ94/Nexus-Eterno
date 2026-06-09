import json
import os

from nexus.domain.cards.models import Card, AbilityDefinition
from nexus.domain.cards.parser import parse_effect

def load_cards(path: str = None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cards.json")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cards = []

    for card_data in data:
        abilities = [
            parse_effect(effect)
            for effect in card_data.get("effects", [])
        ]

        card = Card(
            id=card_data["id"],
            name=card_data["name"],
            level=card_data.get("level", 1),
            atk=card_data.get("atk", 0),
            hp=card_data.get("hp", 100),
            element=card_data.get("element", "NEUTRAL"),
            card_type=card_data.get("type", "creature"),
            abilities=abilities,
            cost_mana=card_data.get("cost_mana", 0)
        )

        card.evolution = card_data.get("evolution")  # None se ausente
        card.desc = card_data.get("desc", "")
        cards.append(card)

    return cards