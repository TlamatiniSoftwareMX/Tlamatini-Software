from typing import Dict, Optional, Tuple

from core.local_llm import LocalLLMConfig, obtener_local_llm_provider
from core.texto import normalizar_texto


INTENCION_NONE = "NONE"
INTENCION_DEEPEN = "DEEPEN"
INTENCION_REQUEST_CITATION = "REQUEST_CITATION"
INTENCION_REQUEST_DOCUMENT_SOURCE = "REQUEST_DOCUMENT_SOURCE"
INTENCION_REQUEST_EXACT_PAGE = "REQUEST_EXACT_PAGE"


PATRONES_INTENCION = {
    INTENCION_REQUEST_EXACT_PAGE: {
        "dame la pagina",
        "dame la página",
        "que pagina",
        "qué página",
        "en que pagina",
        "en qué página",
        "pagina exacta",
        "página exacta",
        "pagina",
        "página",
    },
    INTENCION_REQUEST_CITATION: {
        "dame citas",
        "dame referencias",
        "cita textual",
        "citas textuales",
        "dame una cita",
        "cita",
        "referencia",
        "referencias",
    },
    INTENCION_REQUEST_DOCUMENT_SOURCE: {
        "segun los libros",
        "según los libros",
        "segun el libro",
        "según el libro",
        "segun los textos",
        "según los textos",
        "segun los documentos",
        "según los documentos",
        "buscalo en los libros",
        "búscalo en los libros",
        "buscalo en los documentos",
        "búscalo en los documentos",
        "que dice el autor",
        "qué dice el autor",
        "segun el autor",
        "según el autor",
    },
    INTENCION_DEEPEN: {
        "mas info",
        "más info",
        "mas informacion",
        "más información",
        "dame mas informacion",
        "dame más información",
        "profundiza",
        "quiero saber mas",
        "quiero saber más",
        "amplia",
        "amplía",
        "desarrolla",
        "explicalo mejor",
        "explícalo mejor",
        "explicame mejor",
        "explícame mejor",
    },
}


def _normalizar(texto: str) -> str:
    return normalizar_texto(texto or "")


PATRONES_NORMALIZADOS = {
    intencion: {_normalizar(patron) for patron in patrones}
    for intencion, patrones in PATRONES_INTENCION.items()
}


def _detectar_por_reglas(pregunta: str) -> Tuple[str, str]:
    consulta = _normalizar(pregunta)
    if not consulta:
        return INTENCION_NONE, "rules"

    for intencion in (
        INTENCION_REQUEST_EXACT_PAGE,
        INTENCION_REQUEST_CITATION,
        INTENCION_REQUEST_DOCUMENT_SOURCE,
        INTENCION_DEEPEN,
    ):
        for patron in PATRONES_NORMALIZADOS[intencion]:
            if patron and patron in consulta:
                return intencion, "rules"

    return INTENCION_NONE, "rules"


def _prompt_clasificacion_intencion(pregunta: str) -> str:
    return (
        "Clasifica la intención del mensaje del usuario.\n"
        "Responde con una sola etiqueta exacta, sin explicación.\n"
        "Etiquetas válidas: NONE, DEEPEN, REQUEST_CITATION, REQUEST_DOCUMENT_SOURCE, REQUEST_EXACT_PAGE.\n"
        "Usa DEEPEN cuando el usuario pide ampliar o profundizar.\n"
        "Usa REQUEST_CITATION cuando pide citas o referencias.\n"
        "Usa REQUEST_DOCUMENT_SOURCE cuando pide libros, textos, documentos o autor.\n"
        "Usa REQUEST_EXACT_PAGE cuando pide página exacta.\n"
        "Usa NONE si no aplica claramente.\n\n"
        f"Mensaje del usuario: {pregunta.strip()}"
    )


def _clasificar_con_llm(pregunta: str, config: Optional[LocalLLMConfig] = None) -> Tuple[str, str]:
    proveedor = obtener_local_llm_provider()
    disponible, _ = proveedor.is_available()
    if not disponible:
        return INTENCION_NONE, "fallback_unavailable"

    respuesta = proveedor.generate(
        prompt=_prompt_clasificacion_intencion(pregunta),
        system_prompt="Eres un clasificador de intención. Devuelve una sola etiqueta exacta.",
        config=config or LocalLLMConfig(route="classification", temperature=0.0, top_p=0.2, max_tokens=12),
    )
    etiqueta = (respuesta or "").strip().splitlines()[0].strip().upper()
    if etiqueta in {
        INTENCION_NONE,
        INTENCION_DEEPEN,
        INTENCION_REQUEST_CITATION,
        INTENCION_REQUEST_DOCUMENT_SOURCE,
        INTENCION_REQUEST_EXACT_PAGE,
    }:
        return etiqueta, "llm"
    return INTENCION_NONE, "fallback_invalid"


def detectar_intencion_seguimiento(
    pregunta: str,
    usar_fallback_llm: bool = True,
    config: Optional[LocalLLMConfig] = None,
) -> Dict[str, str]:
    intencion, origen = _detectar_por_reglas(pregunta)
    if intencion != INTENCION_NONE or not usar_fallback_llm:
        return {"intent": intencion, "source": origen}

    intencion_llm, origen_llm = _clasificar_con_llm(pregunta, config=config)
    return {"intent": intencion_llm, "source": origen_llm}
