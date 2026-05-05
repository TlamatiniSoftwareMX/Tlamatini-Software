import re
from typing import Dict, Optional, Tuple

from core.catalogo_dominios import inferir_dominio_desde_texto
from core.local_llm import LocalLLMConfig, obtener_local_llm_provider
from core.texto import normalizar_texto


TEMA_GENERAL = "general"
TEMAS_SOPORTADOS = {
    "medicina",
    "filosofia",
    "derecho",
    "historia",
    "psicologia",
    "literatura",
    "ingenieria",
    "general",
}

TEMAS_BIBLIOTECAS = {
    "medicina": "biblioteca_medica",
    "filosofia": "biblioteca_filosofia",
    "derecho": "biblioteca_derecho",
    "historia": "biblioteca_historia",
    "psicologia": "biblioteca_psicologia",
    "literatura": "biblioteca_literatura",
    "ingenieria": "biblioteca_ingenieria",
    "general": "biblioteca_general",
}

DOMINIO_A_TEMA = {
    "medica": "medicina",
    "herbolaria": "medicina",
    "veterinaria": "medicina",
    "animales": "medicina",
    "proteccion_civil": "ingenieria",
    "autosuficiencia": "ingenieria",
    "siembra": "ingenieria",
    "campismo": "ingenieria",
    "preparacionismo": "ingenieria",
    "instalacion_mantenimiento_reparacion": "ingenieria",
    "vehiculos": "ingenieria",
    "construccion": "ingenieria",
    "agua_saneamiento": "ingenieria",
}

ALIAS_TEMA = {
    "medica": "medicina",
    "medicina": "medicina",
    "medico": "medicina",
    "medicos": "medicina",
    "médica": "medicina",
    "médico": "medicina",
    "filosofia": "filosofia",
    "filosofico": "filosofia",
    "filosófico": "filosofia",
    "derecho": "derecho",
    "juridico": "derecho",
    "jurídico": "derecho",
    "legal": "derecho",
    "historia": "historia",
    "historico": "historia",
    "histórico": "historia",
    "psicologia": "psicologia",
    "psicologico": "psicologia",
    "psicológico": "psicologia",
    "literatura": "literatura",
    "literario": "literatura",
    "ingenieria": "ingenieria",
    "ingenieril": "ingenieria",
    "tecnico": "ingenieria",
    "técnico": "ingenieria",
    "instalacion": "ingenieria",
    "instalación": "ingenieria",
    "mantenimiento": "ingenieria",
    "reparacion": "ingenieria",
    "reparación": "ingenieria",
    "instalacion_mantenimiento_reparacion": "ingenieria",
    "general": "general",
}

PATRONES_TEMA = {
    "medicina": {
        "enfermedad", "sintoma", "síntoma", "tratamiento", "diagnostico", "diagnóstico",
        "diabetes", "hipertension", "hipertensión", "cancer", "cáncer", "clinica", "clínica",
        "anatomia", "anatomía", "farmacologia", "farmacología", "medicina", "medicamento",
        "fisiologia", "fisiología", "insulina", "paciente",
    },
    "filosofia": {
        "etica", "ética", "ontologia", "ontología", "epistemologia", "epistemología",
        "metafisica", "metafísica", "platon", "platón", "aristoteles", "aristóteles",
        "kant", "nihilismo", "filosofia", "filosofía", "ser", "moral",
    },
    "derecho": {
        "ley", "codigo", "código", "amparo", "jurisprudencia", "sentencia", "tribunal",
        "constitucional", "derecho", "legal", "juridico", "jurídico", "norma", "delito",
        "contrato", "constitucion", "constitución",
    },
    "historia": {
        "historia", "historico", "histórico", "epoca", "época", "siglo", "revolucion",
        "revolución", "imperio", "guerra", "civilizacion", "civilización", "antiguedad",
        "antigüedad", "cronologia", "cronología",
    },
    "psicologia": {
        "psicologia", "psicología", "conducta", "emocion", "emoción", "trastorno",
        "depresion", "depresión", "ansiedad", "trauma", "cognitivo", "mente",
        "comportamiento", "terapia cognitiva", "psiquico", "psíquico",
    },
    "literatura": {
        "literatura", "poesia", "poesía", "novela", "cuento", "autor", "narrador",
        "personaje", "metafora", "metáfora", "poema", "ensayo", "obra", "verso",
        "estilo literario",
    },
    "ingenieria": {
        "ingenieria", "ingeniería", "circuito", "voltaje", "corriente", "motor",
        "mecanica", "mecánica", "electricidad", "electronica", "electrónica", "panel solar",
        "fotovoltaico", "resistencia", "instalacion", "instalación", "mantenimiento",
        "reparacion", "reparación", "algoritmo", "estructura", "sistema tecnico", "sistema técnico",
    },
}


def _normalizar(texto: str) -> str:
    base = normalizar_texto(texto or "")
    base = re.sub(r"[^a-z0-9\s]", " ", base)
    return re.sub(r"\s+", " ", base).strip()


PATRONES_TEMA_NORMALIZADOS = {
    tema: {_normalizar(p) for p in patrones}
    for tema, patrones in PATRONES_TEMA.items()
}


def normalizar_tema(tema: str) -> str:
    return ALIAS_TEMA.get(_normalizar(tema), TEMA_GENERAL)


def biblioteca_por_tema(tema: str) -> str:
    return TEMAS_BIBLIOTECAS.get(normalizar_tema(tema), TEMAS_BIBLIOTECAS[TEMA_GENERAL])


def tema_por_dominio(dominio: str) -> str:
    dominio_raw = str(dominio or "").strip().lower()
    dominio_norm = _normalizar(dominio)
    return normalizar_tema(
        DOMINIO_A_TEMA.get(dominio_raw)
        or DOMINIO_A_TEMA.get(dominio_norm)
        or DOMINIO_A_TEMA.get(dominio_norm.replace(" ", "_"))
        or TEMA_GENERAL
    )


def _contar_coincidencias(texto: str, patron: str) -> int:
    consulta = f" {_normalizar(texto)} "
    termino = f" {_normalizar(patron)} "
    if not termino.strip():
        return 0
    return consulta.count(termino)


def _clasificar_por_reglas(pregunta: str, dominio_explicito: str = "") -> Tuple[str, float]:
    tema_explicito = normalizar_tema(dominio_explicito)
    if tema_explicito != TEMA_GENERAL and dominio_explicito.strip():
        return tema_explicito, 0.98

    consulta = _normalizar(pregunta)
    if not consulta:
        return TEMA_GENERAL, 0.0

    mejor_tema = TEMA_GENERAL
    mejor_puntaje = 0
    for tema, patrones in PATRONES_TEMA_NORMALIZADOS.items():
        puntaje = sum(_contar_coincidencias(consulta, patron) for patron in patrones)
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_tema = tema

    if mejor_puntaje <= 0:
        return TEMA_GENERAL, 0.0
    if mejor_puntaje >= 3:
        return mejor_tema, 0.95
    if mejor_puntaje == 2:
        return mejor_tema, 0.8
    return mejor_tema, 0.65


def _prompt_clasificacion_tema(pregunta: str, dominio_explicito: str = "") -> str:
    contexto_dominio = _normalizar(dominio_explicito)
    return (
        "Clasifica el tema principal de la consulta del usuario.\n"
        "Responde con una sola etiqueta exacta.\n"
        "Etiquetas válidas: medicina, filosofia, derecho, historia, psicologia, literatura, ingenieria, general.\n"
        "Usa general si no hay evidencia suficiente.\n"
        "No expliques nada.\n\n"
        f"Dominio explícito del sistema: {contexto_dominio or 'ninguno'}\n"
        f"Consulta: {pregunta.strip()}"
    )


def _clasificar_con_llm(pregunta: str, dominio_explicito: str = "", config: Optional[LocalLLMConfig] = None) -> Tuple[str, float]:
    proveedor = obtener_local_llm_provider()
    disponible, _ = proveedor.is_available()
    if not disponible:
        return TEMA_GENERAL, 0.0

    respuesta = proveedor.generate(
        prompt=_prompt_clasificacion_tema(pregunta, dominio_explicito=dominio_explicito),
        system_prompt="Eres un clasificador temático. Devuelve una sola etiqueta exacta.",
        config=config or LocalLLMConfig(route="classification", temperature=0.0, top_p=0.2, max_tokens=12),
    )
    etiqueta = _normalizar((respuesta or "").splitlines()[0] if respuesta else "")
    if etiqueta in TEMAS_SOPORTADOS:
        return etiqueta, 0.6
    return TEMA_GENERAL, 0.0


def clasificar_tema_consulta(
    pregunta: str,
    dominio_explicito: str = "",
    usar_fallback_llm: bool = True,
    config: Optional[LocalLLMConfig] = None,
) -> Dict[str, object]:
    dominio_inferido = inferir_dominio_desde_texto(pregunta, include_possible=True)
    dominio_probable = str(dominio_inferido.get("domain", "") or "")
    dominio_operativo = str(dominio_inferido.get("operational_domain", "") or "")

    tema, confianza = _clasificar_por_reglas(pregunta, dominio_explicito=dominio_explicito)
    source = "rules"
    tema_dominio = tema_por_dominio(dominio_operativo or dominio_probable)
    if tema == TEMA_GENERAL and tema_dominio != TEMA_GENERAL:
        tema = tema_dominio
        confianza = max(confianza, 0.72)
        source = "domain_catalog"
    if tema == TEMA_GENERAL and usar_fallback_llm:
        tema_llm, confianza_llm = _clasificar_con_llm(
            pregunta,
            dominio_explicito=dominio_explicito,
            config=config,
        )
        if tema_llm != TEMA_GENERAL:
            tema = tema_llm
            confianza = confianza_llm
            source = "llm"

    tema = normalizar_tema(tema)
    return {
        "theme": tema,
        "confidence": round(float(confianza), 2),
        "library": biblioteca_por_tema(tema),
        "source": source,
        "domain": dominio_probable,
        "operational_domain": dominio_operativo,
        "domain_score": round(float(dominio_inferido.get("score", 0.0) or 0.0), 2),
        "matched_terms": list(dominio_inferido.get("matched_terms", []) or []),
    }
