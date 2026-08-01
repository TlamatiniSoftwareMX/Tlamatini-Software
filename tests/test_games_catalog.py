from interfaz.ventana_juegos import CARD_COLORS, LastCardWindow, _card_playable


def test_last_card_deck_has_expected_cards():
    game = LastCardWindow.__new__(LastCardWindow)
    deck = game._new_deck()

    assert len(deck) == 96
    assert set(color for color, _value in deck) == set(CARD_COLORS)
    assert all(deck.count((color, "+2")) == 2 for color in CARD_COLORS)
    assert all(deck.count((color, "Salta")) == 2 for color in CARD_COLORS)


def test_last_card_accepts_matching_color_or_symbol():
    top = ("Rojo", "7")

    assert _card_playable(("Rojo", "2"), top)
    assert _card_playable(("Azul", "7"), top)
    assert not _card_playable(("Verde", "4"), top)
