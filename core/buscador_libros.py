from core.buscador_documental import (
    buscar_en_biblioteca,
    detectar_tipo_pregunta,
    normalizar_texto
)
from core.buscador_documental import buscar_en_biblioteca as buscar_documental

import re


def extraer_numeros(texto: str):
    return re.findall(r"\b\d+(?:[\.,]\d+)?\b", texto)