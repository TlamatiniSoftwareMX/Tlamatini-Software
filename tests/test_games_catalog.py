from interfaz.ventana_juegos import (
    CARD_COLORS,
    LastCardWindow,
    _card_playable,
    decode_morse,
    encode_morse,
)


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


def test_morse_encodes_words_numbers_and_accents():
    assert encode_morse("SOS") == "... --- ..."
    assert encode_morse("señal 2") == "... . -. .- .-.. / ..---"


def test_morse_decodes_words_and_unknown_symbols():
    assert decode_morse(".- --. ..- .-") == "AGUA"
    assert decode_morse("... --- ... / .----") == "SOS 1"
    assert decode_morse("......") == "?"
