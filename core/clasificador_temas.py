import re
import unicodedata
from typing import Dict, List

from core.catalogo_dominios import catalogo_subdominios_existentes


TEMAS_POR_DOMINIO: Dict[str, Dict[str, List[str]]] = catalogo_subdominios_existentes()


def quitar_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def normalizar_texto(texto: str) -> str:
    texto = quitar_acentos(texto.lower())
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def contar_ocurrencias_palabra_o_frase(texto: str, termino: str) -> int:
    """
    Cuenta coincidencias de palabra o frase de forma más estricta para evitar ruido.
    """
    texto_n = f" {normalizar_texto(texto)} "
    termino_n = f" {normalizar_texto(termino)} "

    if not termino_n.strip():
        return 0

    return texto_n.count(termino_n)


def detectar_temas_en_texto(texto: str, umbral_minimo: int = 2) -> List[str]:
    texto_n = normalizar_texto(texto)
    temas_detectados = []

    for _, subdominios in TEMAS_POR_DOMINIO.items():
        for subdominio, palabras in subdominios.items():
            puntaje = 0

            for palabra in palabras:
                ocurrencias = contar_ocurrencias_palabra_o_frase(texto_n, palabra)
                if ocurrencias > 0:
                    puntaje += ocurrencias

            if puntaje >= umbral_minimo:
                temas_detectados.append(subdominio)

    return temas_detectados


def detectar_subdominio_sugerido(dominio: str, texto: str) -> str:
    texto_n = normalizar_texto(texto)
    subdominios = TEMAS_POR_DOMINIO.get(dominio.lower(), {})

    mejor_subdominio = ""
    mejor_puntaje = 0

    for subdominio, palabras in subdominios.items():
        puntaje = 0

        for palabra in palabras:
            ocurrencias = contar_ocurrencias_palabra_o_frase(texto_n, palabra)
            puntaje += ocurrencias

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_subdominio = subdominio

    return mejor_subdominio if mejor_puntaje > 0 else ""
