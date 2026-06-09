from nexus.presentation.gl.texture import load_texture
from nexus.presentation.scene.entity import Card

CARD_IMAGE_FILES = {
    "larva_carne_viva": ("sombra", "larvadacarne.png"),
    "sombra_rastejante": ("sombra", "sombrarastejante.png"),
    "parasita_abissal": ("sombra", "parasita.png"),
    "acolito_degeneracao": ("sombra", "acolito.png"),
    "aberracao_costurada": ("sombra", "aberracao.png"),
    "horror_pulsante": ("sombra", "horror.png"),
    "devora_almas_corrompido": ("sombra", "devoraalmas.png"),
    "massa_amorfa_mutante": ("sombra", "massa.png"),
    "abominacao_carne": ("sombra", "abominacao.png"),
    "quimera_5_cabecas": ("sombra", "quimera.png"),
    "avatar_degeneracao": ("sombra", "avatar.png"),
    "deus_carne_infinita": ("sombra", "deusdacarne.png"),
    "fragment":            ("sombra", "fragmentodecarne.png"),
    "ritual_degeneracao": ("sombra", "ritual.png"),
    "corrupcao_progressiva": ("sombra", "corrupcao.png"),
    "banquete_profano": ("sombra", "banquete.png"),
    "sentinela_da_luz": ("sol", "sentinela.png"),
    "discipulo_solar": ("sol", "discipulo.png"),
    "guardiao_radiante": ("sol", "guardiao.png"),
    "cavaleiro_da_aurora": ("sol", "cavaleiro.png"),
    "arcanjo_do_julgamento": ("sol", "arcanjo.png"),
    "avatar_solar": ("sol", "avatar.png"),
    "miniatura_sol_ardente": ("sol", "miniaturasol.png"),
    "encarnacao_sol_supremo": ("sol", "encarnacaodosol.png"),
    "julgamento_solar": ("sol", "julgamentosolar.png"),
    "explosao_radiante": ("sol", "explosaoradiante.png"),
    "luz_purificadora": ("sol", "luzpurificadora.png"),
    "barreira_divina": ("sol", "barreira.png"),
    "ordem_absoluta": ("sol", "ordemabsoluta.png"),
    "chama_equilibrio": ("sol", "chamadoequilibrio.png"),
    "renascimento_solar": ("sol", "renascimentosolar.png"),
}

def load_card_texture_for(base_dir, card_id, texture_cache):
    if card_id in texture_cache:
        return texture_cache[card_id]

    folder, filename = CARD_IMAGE_FILES.get(card_id, ("sol", "guardiao.png"))
    texture_path = base_dir.parent / "data" / "cartas" / folder / filename
    texture_cache[card_id] = load_texture(str(texture_path))
    return texture_cache[card_id]


def make_hand_visuals(base_dir, hand_x_positions, y, owner, domain_cards, texture_cache, card_w=160, card_h=240):
    """Cria as cartas visuais da mão de um jogador a partir das cartas de domínio.

    Cada carta visual recebe `card_id` e `domain_card` para que cliques/drags
    possam acionar o engine (`engine.play_card(card.domain_card)`).
    """
    ui_cards = []
    for index, domain_card in enumerate(domain_cards[: len(hand_x_positions)]):
        texture = load_card_texture_for(base_dir, domain_card.id, texture_cache)
        card = Card(hand_x_positions[index], y, texture, owner=owner, width=card_w, height=card_h)
        card.card_id = domain_card.id
        card.domain_card = domain_card
        card.state = "hand"
        ui_cards.append(card)
    return ui_cards


def make_field_visuals(base_dir, battle_x_positions, y, owner, domain_cards, texture_cache, card_w=160, card_h=240):
    """Cria as cartas visuais do campo, encaixadas no slot real (board_position) de cada carta."""
    ui_cards = []
    for index, domain_card in enumerate(domain_cards):
        slot_index = getattr(domain_card, "board_position", None)
        if not isinstance(slot_index, int) or slot_index < 0 or slot_index >= len(battle_x_positions):
            slot_index = index
        if slot_index >= len(battle_x_positions):
            continue
        texture = load_card_texture_for(base_dir, domain_card.id, texture_cache)
        x = battle_x_positions[slot_index]
        card = Card(x, y, texture, owner=owner, width=card_w, height=card_h)
        card.card_id = domain_card.id
        card.domain_card = domain_card
        card.state = "field"
        card.slot_idx = slot_index  # preservado mesmo após board_position = None
        card.current_x = x
        card.current_y = y
        card.target_x = x
        card.target_y = y
        ui_cards.append(card)
    return ui_cards
