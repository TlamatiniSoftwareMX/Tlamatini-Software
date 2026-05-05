import unicodedata


def normalizar_texto(texto: str) -> str:
    base = " ".join(str(texto or "").strip().lower().split())
    return "".join(c for c in unicodedata.normalize("NFD", base) if unicodedata.category(c) != "Mn")
