import re
from typing import Dict, List

from core.memoria import obtener_seccion
from core.texto import normalizar_texto as _normalizar_base


STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "y", "o", "en", "un", "una", "unos", "unas",
    "que", "qué", "como", "cómo", "cual", "cuál", "cuantos", "cuántos", "tiene", "tienen",
    "es", "son", "se", "al", "por", "para", "con", "sin", "lo", "le", "les", "su", "sus",
    "humano", "humana", "cuerpo"
}


def normalizar_texto(texto: str) -> str:
    return _normalizar_base(texto)


def tokens_significativos(texto: str) -> List[str]:
    tokens = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", normalizar_texto(texto))
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def es_pregunta_factual(texto: str) -> bool:
    t = normalizar_texto(texto)
    patrones = [
        "cuántos", "cuantos", "qué es", "que es", "cuál es", "cual es",
        "cuáles son", "cuales son", "cómo se llama", "como se llama",
        "qué hace", "que hace", "función", "funcion"
    ]
    return any(p in t for p in patrones)


def es_frase_ruidosa(frase: str) -> bool:
    f = frase.strip()

    if len(f) < 15:
        return True

    # Penalizar frases con demasiadas mayúsculas o texto editorial
    mayus = sum(ch.isupper() for ch in f if ch.isalpha())
    letras = sum(ch.isalpha() for ch in f)
    if letras > 0 and (mayus / letras) > 0.65 and len(f) < 120:
        return True

    patrones_ruido = [
        r"page \d+",
        r"página \d+",
        r"pagina \d+",
        r"cap[ií]tulo \d+",
        r"objetivos",
        r"introducción",
        r"introduccion"
    ]

    f_n = normalizar_texto(f)
    if any(re.search(p, f_n) for p in patrones_ruido):
        return True

    return False


def puntuar_frase(pregunta: str, frase: str) -> int:
    pregunta_n = normalizar_texto(pregunta)
    frase_n = normalizar_texto(frase)
    tokens = tokens_significativos(pregunta)
    puntaje = 0

    if es_frase_ruidosa(frase):
        return -20

    for token in tokens:
        if token in frase_n:
            puntaje += 12

    if pregunta_n in frase_n:
        puntaje += 40

    if es_pregunta_factual(pregunta_n):
        if any(ch.isdigit() for ch in frase):
            puntaje += 20
        if any(x in frase_n for x in ["es ", "son ", "tiene ", "tienen ", "se define", "se considera", "consiste en", "se encarga de"]):
            puntaje += 12

    # Si pregunta por huesos y la frase menciona huesos y un número, premiar fuerte
    if "huesos" in pregunta_n and "huesos" in frase_n and any(ch.isdigit() for ch in frase):
        puntaje += 30

    # Si pregunta por homeostasis y la frase la define, premiar fuerte
    if "homeostasis" in pregunta_n and "homeostasis" in frase_n and any(x in frase_n for x in ["es ", "se define", "consiste en"]):
        puntaje += 28

    # Si pregunta "qué hace" o función, premiar descripciones funcionales
    if any(x in pregunta_n for x in ["qué hace", "que hace", "función", "funcion"]):
        if any(x in frase_n for x in ["función", "funcion", "se encarga", "permite", "regula", "realiza"]):
            puntaje += 22

    return puntaje


def detectar_subdominios_probables(pregunta: str) -> List[str]:
    p = normalizar_texto(pregunta)
    resultado = []

    patrones = {
        "urgencias": ["shock", "choque", "emergencia", "urgencia", "herida", "sangrado", "trauma"],
        "farmacologia": ["dosis", "medicamento", "farmaco", "fármaco", "insulina", "via", "vía", "frecuencia"],
        "anatomia": ["hueso", "huesos", "arteria", "vena", "nervio", "músculo", "musculo", "órgano", "organo", "cráneo", "craneo"],
        "fisiologia": ["función", "funcion", "homeostasis", "metabolismo", "respiración", "respiracion", "circulación", "circulacion"],
        "procedimientos": ["limpiar", "lavar", "curación", "curacion", "lavado", "manejo", "procedimiento"],
    }

    for subdominio, palabras in patrones.items():
        if any(palabra in p for palabra in palabras):
            resultado.append(subdominio)

    return resultado


def seleccionar_frase_exacta(pregunta: str, bloque: Dict) -> str:
    frases = bloque.get("frases", [])
    if not frases:
        frases = [bloque.get("texto", "")]

    frases_puntuadas = []
    for frase in frases:
        puntaje = puntuar_frase(pregunta, frase)
        frases_puntuadas.append((puntaje, frase))

    frases_puntuadas.sort(key=lambda x: x[0], reverse=True)
    mejor_puntaje, mejor_frase = frases_puntuadas[0]

    if mejor_puntaje <= 0:
        return bloque.get("texto", "")[:300].strip()

    return mejor_frase.strip()


def puntuar_bloque(pregunta: str, bloque: Dict, dominio: str = "", contexto: Dict = None) -> int:
    contexto = contexto or {}
    pregunta_n = normalizar_texto(pregunta)
    texto = normalizar_texto(bloque.get("texto", ""))
    tokens = tokens_significativos(pregunta)
    puntaje = 0

    for token in tokens:
        if token in texto:
            puntaje += 7

    if dominio and bloque.get("dominio", "") == dominio.lower():
        puntaje += 10

    subdominios_probables = detectar_subdominios_probables(pregunta)
    if bloque.get("subdominio", "") in subdominios_probables:
        puntaje += 16

    etiquetas = bloque.get("etiquetas_detectadas", [])
    for sub in subdominios_probables:
        if sub in etiquetas:
            puntaje += 12

    frase_exacta = seleccionar_frase_exacta(pregunta, bloque)
    puntaje += max(puntuar_frase(pregunta, frase_exacta), 0)

    if contexto.get("natural"):
        if any(x in texto for x in ["alimentación", "alimentacion", "ejercicio", "fibra", "infusión", "infusion", "vinagre"]):
            puntaje += 10

    if contexto.get("farmacologico"):
        if any(x in texto for x in ["dosis", "frecuencia", "medicamento", "insulina", "antibiótico", "antibiotico"]):
            puntaje += 10

    return puntaje


def buscar_en_indices(pregunta: str, dominio: str = "", contexto: Dict = None, limite: int = 6) -> List[Dict]:
    indices = obtener_seccion("indices_conocimiento", [])
    resultados = []

    for bloque in indices:
        puntaje = puntuar_bloque(pregunta, bloque, dominio, contexto)
        if puntaje > 0:
            resultados.append({
                "puntaje": puntaje,
                "bloque": bloque,
                "frase_exacta": seleccionar_frase_exacta(pregunta, bloque)
            })

    resultados.sort(key=lambda x: x["puntaje"], reverse=True)
    return resultados[:limite]
