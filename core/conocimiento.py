import re
from typing import Dict, List

from core.texto import normalizar_texto as _normalizar_base


SINONIMOS = {
    "glucosa": ["azúcar", "azucar", "glucemia", "hiperglucemia"],
    "farmacológico": ["farmacologico", "medicamentos", "fármacos", "farmacos", "insulina", "dosis", "horario"],
    "natural": ["sin medicamentos", "alimentación", "alimentacion", "plantas", "infusiones", "ejercicio", "vinagre", "fibra"],
    "herida": ["lesión", "lesion", "trauma", "corte"],
    "dolor torácico": ["dolor toracico", "opresión en pecho", "opresion en pecho", "diaforesis", "náusea", "nausea"],
    "síntomas": ["sintomas", "síntoma", "sintoma", "signos", "semiología", "semiologia"],
    "protección civil": ["proteccion civil", "rescate", "riesgos", "emergencia"],
    "instalación": ["instalacion", "mantenimiento", "reparación", "reparacion", "equipo", "herramienta"],
    "huesos": ["hueso", "esqueleto", "sistema óseo", "sistema oseo"],
    "corazón": ["corazon", "miocardio", "cardíaco", "cardiaco"],
    "homeostasis": ["equilibrio interno", "medio interno", "regulación interna", "regulacion interna"]
}


STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "y", "o", "en", "un", "una", "unos", "unas",
    "que", "qué", "como", "cómo", "cual", "cuál", "cuantos", "cuántos", "tiene", "tienen",
    "es", "son", "se", "al", "por", "para", "con", "sin", "humano", "humana"
}


def normalizar_texto(texto: str) -> str:
    return _normalizar_base(texto)


def partir_en_frases(texto: str) -> List[str]:
    frases = re.split(r'(?<=[\.\!\?\:])\s+', texto.strip())
    return [f.strip() for f in frases if f.strip()]


def expandir_terminos(texto: str) -> List[str]:
    texto = normalizar_texto(texto)
    terminos = set(texto.split())

    for base, sinonimos in SINONIMOS.items():
        if base in texto or any(s in texto for s in sinonimos):
            terminos.add(base)
            terminos.update(sinonimos)

    return list(terminos)


def terminos_significativos(texto: str) -> List[str]:
    tokens = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", normalizar_texto(texto))
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def detectar_nivel_coincidencia(puntaje: int) -> str:
    if puntaje >= 40:
        return "alta"
    if puntaje >= 22:
        return "media"
    return "baja"


def es_pregunta_factual(texto: str) -> bool:
    t = normalizar_texto(texto)
    patrones = [
        "cuántos", "cuantos", "qué es", "que es", "cuál es", "cual es",
        "cuáles son", "cuales son", "cómo se llama", "como se llama"
    ]
    return any(p in t for p in patrones)


def puntuar_frase(pregunta: str, frase: str) -> int:
    pregunta_n = normalizar_texto(pregunta)
    frase_n = normalizar_texto(frase)
    tokens = terminos_significativos(pregunta)
    puntaje = 0

    for token in tokens:
        if token in frase_n:
            puntaje += 8

    if es_pregunta_factual(pregunta_n):
        if any(ch.isdigit() for ch in frase):
            puntaje += 12
        if any(x in frase_n for x in ["es ", "son ", "tiene ", "consta de", "está formado", "esta formado"]):
            puntaje += 8

    if pregunta_n in frase_n:
        puntaje += 25

    return puntaje


def extraer_mejor_frase(pregunta: str, contenido: str) -> str:
    frases = partir_en_frases(contenido)
    if not frases:
        return contenido[:300].strip()

    frases_puntuadas = []
    for frase in frases:
        puntaje = puntuar_frase(pregunta, frase)
        frases_puntuadas.append((puntaje, frase))

    frases_puntuadas.sort(key=lambda x: x[0], reverse=True)
    mejor_puntaje, mejor_frase = frases_puntuadas[0]

    if mejor_puntaje <= 0:
        return frases[0]

    return mejor_frase


def puntuar_fragmento(pregunta: str, item: Dict, dominio: str = "", contexto: Dict = None) -> int:
    pregunta_normalizada = normalizar_texto(pregunta)
    terminos = expandir_terminos(pregunta_normalizada)
    contexto = contexto or {}

    titulo = normalizar_texto(item.get("titulo", ""))
    contenido = normalizar_texto(item.get("contenido", ""))
    item_dominio = normalizar_texto(item.get("dominio", ""))
    subdominio = normalizar_texto(item.get("subdominio", ""))

    puntaje = 0

    for termino in terminos:
        if termino in titulo:
            puntaje += 8
        if termino in contenido:
            puntaje += 5

    if dominio and item_dominio == dominio.lower():
        puntaje += 8

    if contexto.get("natural"):
        if any(t in subdominio for t in ["manejo_no_farmacologico", "apoyo_complementario"]):
            puntaje += 12
        if any(t in contenido for t in ["alimentación", "alimentacion", "ejercicio", "fibra", "vinagre", "infusiones", "tés", "tes"]):
            puntaje += 10

    if contexto.get("farmacologico"):
        if "farmacologia" in subdominio:
            puntaje += 12
        if any(t in contenido for t in ["dosis", "vía", "via", "frecuencia", "tratamiento", "insulina", "antidiabéticos", "antidiabeticos"]):
            puntaje += 10

    if contexto.get("sintomas"):
        if any(t in contenido for t in ["síntoma", "sintoma", "signo", "diagnóstico", "diagnostico", "semiología", "semiologia"]):
            puntaje += 10

    mejor_frase = extraer_mejor_frase(pregunta, item.get("contenido", ""))
    puntaje += puntuar_frase(pregunta, mejor_frase)

    if es_pregunta_factual(pregunta_normalizada) and len(contenido) > 2500:
        puntaje -= 5

    return puntaje


def buscar_conocimiento(pregunta: str, dominio: str = "", contexto: Dict = None, limite: int = 5) -> List[Dict]:
    from core.memoria import obtener_seccion

    conocimiento = obtener_seccion("conocimiento", [])
    resultados = []

    for item in conocimiento:
        puntaje = puntuar_fragmento(pregunta, item, dominio, contexto)
        if puntaje > 0:
            mejor_frase = extraer_mejor_frase(pregunta, item.get("contenido", ""))
            resultados.append({
                "puntaje": puntaje,
                "nivel_coincidencia": detectar_nivel_coincidencia(puntaje),
                "mejor_frase": mejor_frase,
                "item": item
            })

    resultados.sort(key=lambda x: x["puntaje"], reverse=True)
    return resultados[:limite]
