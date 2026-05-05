import re
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from core.indice_consulta import buscar_fragmentos, detectar_intencion
from core.intencion_consulta import (
    INTENCION_DEEPEN,
    INTENCION_NONE,
    INTENCION_REQUEST_CITATION,
    INTENCION_REQUEST_DOCUMENT_SOURCE,
    INTENCION_REQUEST_EXACT_PAGE,
    detectar_intencion_seguimiento,
)
from core.consulta_avanzada import responder_consulta_documental_tematica
from core.local_llm import LocalLLMConfig, obtener_local_llm_provider
from core.logs import registrar_log
from core.memoria import guardar_seccion, obtener_seccion
from core.tema_consulta import (
    TEMA_GENERAL,
    biblioteca_por_tema,
    clasificar_tema_consulta,
    normalizar_tema,
)
from core.texto import normalizar_texto


SECCIONES_CORTAS = {
    "dosis",
    "contraindicaciones",
    "indicaciones",
    "tratamiento",
    "presentacion",
    "presentaciones",
    "composicion",
    "interacciones",
    "precauciones",
    "clasificacion",
    "diagnostico",
    "etiologia",
}

def _normalizar(texto: str) -> str:
    return normalizar_texto(texto)


def _extraer_entidad_simple(texto: str) -> str:
    t = _normalizar(texto)
    if not t:
        return ""

    if t in SECCIONES_CORTAS:
        return ""

    palabras = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+", t)
    if not palabras:
        return ""

    if len(palabras) <= 5:
        return " ".join(palabras)

    return ""


def _expandir_por_contexto(pregunta: str) -> str:
    p = _normalizar(pregunta)
    conv = obtener_seccion("conversacion", {})
    ultima_entidad = _normalizar(conv.get("ultima_entidad", ""))

    if p in SECCIONES_CORTAS and ultima_entidad:
        return f"{p} de {ultima_entidad}"

    return pregunta


def _normalizar_session_id(session_id: Optional[str]) -> str:
    session_limpia = (session_id or "").strip()
    return session_limpia or "consulta-principal"


def _normalizar_subtema(subdominio: str) -> str:
    subtema = _normalizar(subdominio or "")
    if not subtema or subtema in {"todos", "general"}:
        return ""
    return subtema

def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _obtener_contexto_sesion(session_id: Optional[str] = None) -> Dict:
    conv = obtener_seccion("conversacion", {})
    sesiones = conv.get("sesiones", {})
    return sesiones.get(_normalizar_session_id(session_id), {})


def obtener_contexto_conversacion(session_id: Optional[str] = None) -> Dict:
    return dict(_obtener_contexto_sesion(session_id))


def limpiar_contexto_conversacion(session_id: Optional[str] = None) -> None:
    conv = obtener_seccion("conversacion", {})
    sesiones = dict(conv.get("sesiones", {}) or {})
    session_key = _normalizar_session_id(session_id)
    sesiones.pop(session_key, None)
    conv["sesiones"] = sesiones

    if conv.get("session_id_actual") == session_key:
        conv["session_id_actual"] = ""
        conv["tema_actual"] = ""
        conv["ultimo_dominio"] = ""
        conv["ultima_pregunta"] = ""
        conv["ultima_respuesta"] = ""
        conv["ultimo_tema_detectado"] = ""
        conv["ultimo_tema_confianza"] = 0.0
        conv["ultimo_tema_source"] = ""
        conv["ultimo_subtema_detectado"] = ""
        conv["ultima_biblioteca_objetivo"] = ""
        conv["ultimo_modo_respuesta"] = ""
        conv["ultima_intencion_seguimiento"] = ""
        conv["ultima_entidad"] = ""
        conv["ultimo_timestamp"] = ""

    historial = conv.get("historial", [])
    if isinstance(historial, list):
        conv["historial"] = [
            item for item in historial
            if not isinstance(item, dict) or item.get("session_id") != session_key
        ]

    guardar_seccion("conversacion", conv)


def _actualizar_contexto(
    pregunta_original: str,
    pregunta_usada: str,
    dominio: str,
    subdominio: str,
    resultados: List[Dict],
    session_id: Optional[str] = None,
    respuesta: str = "",
    modo_respuesta: str = "",
    intencion_seguimiento: str = INTENCION_NONE,
    clasificacion_tema: Optional[Dict] = None,
) -> None:
    conv = obtener_seccion("conversacion", {})
    historial = conv.get("historial", [])
    sesiones = conv.get("sesiones", {})
    session_key = _normalizar_session_id(session_id)
    sesion = sesiones.get(session_key, {})

    entidad = _extraer_entidad_simple(pregunta_original)

    if not entidad and resultados:
        titulo = (resultados[0].get("titulo_seccion") or "").strip()
        if titulo:
            entidad = _extraer_entidad_simple(titulo)

    if not entidad and resultados:
        texto = (resultados[0].get("texto") or "").strip()[:120]
        entidad = _extraer_entidad_simple(texto)

    historial.append({
        "pregunta": pregunta_original,
        "pregunta_usada": pregunta_usada,
        "dominio": dominio,
        "subdominio": subdominio,
        "session_id": session_key,
        "timestamp": _timestamp_utc(),
    })

    info_tema = clasificacion_tema or clasificar_tema_consulta(
        pregunta_original,
        dominio_explicito=dominio,
        usar_fallback_llm=False,
    )
    tema = normalizar_tema(str(info_tema.get("theme", TEMA_GENERAL)))
    subtema = _normalizar_subtema(subdominio)
    biblioteca_objetivo = str(info_tema.get("library") or biblioteca_por_tema(tema))
    tema_confianza = float(info_tema.get("confidence", 0.0) or 0.0)
    tema_source = str(info_tema.get("source", "rules") or "rules")

    sesion.update({
        "sessionId": session_key,
        "ultima_pregunta": pregunta_original,
        "pregunta_expandida": pregunta_usada,
        "ultima_respuesta": respuesta,
        "tema_detectado": tema,
        "tema_confianza": tema_confianza,
        "tema_source": tema_source,
        "subtema_detectado": subtema,
        "biblioteca_objetivo": biblioteca_objetivo,
        "ultimo_modo_respuesta": modo_respuesta,
        "ultima_intencion_seguimiento": intencion_seguimiento,
        "timestamp": _timestamp_utc(),
    })

    conv["tema_actual"] = pregunta_original
    conv["ultimo_dominio"] = dominio
    conv["ultimo_subdominio"] = subdominio
    conv["ultima_entidad"] = entidad or conv.get("ultima_entidad", "")
    conv["session_id_actual"] = session_key
    conv["ultima_pregunta"] = pregunta_original
    conv["ultima_respuesta"] = respuesta
    conv["ultimo_tema_detectado"] = tema
    conv["ultimo_tema_confianza"] = tema_confianza
    conv["ultimo_tema_source"] = tema_source
    conv["ultimo_subtema_detectado"] = subtema
    conv["ultima_biblioteca_objetivo"] = biblioteca_objetivo
    conv["ultimo_modo_respuesta"] = modo_respuesta
    conv["ultima_intencion_seguimiento"] = intencion_seguimiento
    conv["ultimo_timestamp"] = sesion["timestamp"]
    conv["historial"] = historial[-25:]
    sesiones[session_key] = sesion
    conv["sesiones"] = sesiones

    guardar_seccion("conversacion", conv)


def _actualizar_contexto_directo(
    pregunta_original: str,
    respuesta: str,
    session_id: Optional[str] = None,
) -> None:
    conv = obtener_seccion("conversacion", {})
    historial = conv.get("historial", [])
    sesiones = conv.get("sesiones", {})
    session_key = _normalizar_session_id(session_id)
    sesion = sesiones.get(session_key, {})

    historial.append({
        "pregunta": pregunta_original,
        "pregunta_usada": pregunta_original,
        "dominio": "",
        "subdominio": "",
        "session_id": session_key,
        "timestamp": _timestamp_utc(),
    })

    sesion.update({
        "sessionId": session_key,
        "ultima_pregunta": pregunta_original,
        "pregunta_expandida": pregunta_original,
        "ultima_respuesta": respuesta,
        "tema_detectado": TEMA_GENERAL,
        "tema_confianza": 0.0,
        "tema_source": "direct_local",
        "subtema_detectado": "",
        "biblioteca_objetivo": "",
        "ultimo_modo_respuesta": "local_direct",
        "ultima_intencion_seguimiento": INTENCION_NONE,
        "timestamp": _timestamp_utc(),
    })

    conv["tema_actual"] = pregunta_original
    conv["ultimo_dominio"] = ""
    conv["ultimo_subdominio"] = ""
    conv["ultima_entidad"] = _extraer_entidad_simple(pregunta_original)
    conv["session_id_actual"] = session_key
    conv["ultima_pregunta"] = pregunta_original
    conv["ultima_respuesta"] = respuesta
    conv["ultimo_tema_detectado"] = TEMA_GENERAL
    conv["ultimo_tema_confianza"] = 0.0
    conv["ultimo_tema_source"] = "direct_local"
    conv["ultimo_subtema_detectado"] = ""
    conv["ultima_biblioteca_objetivo"] = ""
    conv["ultimo_modo_respuesta"] = "local_direct"
    conv["ultima_intencion_seguimiento"] = INTENCION_NONE
    conv["ultimo_timestamp"] = sesion["timestamp"]
    conv["historial"] = historial[-25:]
    sesiones[session_key] = sesion
    conv["sesiones"] = sesiones
    guardar_seccion("conversacion", conv)


def proveedor_local_disponible():
    proveedor = obtener_local_llm_provider()
    return proveedor.is_available()


def _perfil_respuesta_por_pregunta(pregunta: str) -> str:
    p = _normalizar(pregunta or "")
    if not p:
        return "Responde con la longitud estrictamente necesaria."

    patrones_breves = (
        "que es",
        "qué es",
        "define",
        "definicion",
        "definición",
        "significa",
    )
    patrones_pasos = (
        "como ",
        "cómo ",
        "como medir",
        "cómo medir",
        "como hacer",
        "cómo hacer",
        "paso a paso",
        "que hago",
        "qué hago",
        "como se usa",
        "cómo se usa",
    )

    if p.startswith(patrones_breves):
        return (
            "Si la pregunta es de definición o identificación simple, responde en 1 párrafo corto o 2 frases contundentes. "
            "Ve al punto y evita expandirte."
        )
    if any(token in p for token in patrones_pasos):
        return (
            "Si la pregunta pide procedimiento, medición, uso o pasos, responde con instrucciones ordenadas y completas. "
            "Da los pasos suficientes para hacerlo bien, sin recortar detalles necesarios."
        )
    return (
        "Ajusta la longitud a la complejidad real de la pregunta: breve para dudas simples, más amplia para procedimientos, "
        "comparaciones o explicaciones prácticas."
    )


def _prompt_respuesta_rapida(pregunta: str) -> str:
    return (
        "Responde en español de forma directa, útil y clara.\n"
        "Mantén un tono técnico pero entendible.\n"
        "No menciones libros, documentos, fuentes ni bibliografía.\n"
        "No inventes citas ni referencias.\n"
        "Empieza respondiendo el punto principal sin preámbulos.\n"
        f"{_perfil_respuesta_por_pregunta(pregunta)}\n"
        "Si hace falta, añade consejos prácticos o una advertencia breve.\n"
        "Evita rodeos o texto de relleno.\n\n"
        f"Pregunta del usuario: {pregunta.strip()}"
    )


def _prompt_respuesta_con_contexto(pregunta: str, contexto: Dict) -> str:
    ultima_pregunta = (contexto.get("ultima_pregunta") or "").strip()
    ultima_respuesta = (contexto.get("ultima_respuesta") or "").strip()
    tema = (contexto.get("tema_detectado") or "general").strip()
    return (
        "Responde en español con una ampliación clara, útil y suficiente.\n"
        "Usa solo el contexto conversacional dado y conocimiento general del modelo.\n"
        "No digas que consultaste libros, documentos o fuentes.\n"
        "No inventes citas ni referencias.\n"
        "Amplía la explicación con más detalle práctico sin volverla extensa innecesariamente.\n"
        "Si falta contexto, dilo de forma breve.\n\n"
        f"Tema detectado: {tema}\n"
        f"Pregunta anterior: {ultima_pregunta}\n"
        f"Respuesta anterior: {ultima_respuesta}\n"
        f"Seguimiento del usuario: {pregunta.strip()}"
    )


def _mensaje_sin_contexto_para_intencion(intencion: str) -> str:
    if intencion == INTENCION_DEEPEN:
        return (
            "[Respuesta rápida de IA local]\n\n"
            "No hay una consulta anterior en esta sesión para ampliar. "
            "Haz primero una pregunta concreta."
        )
    if intencion in {
        INTENCION_REQUEST_CITATION,
        INTENCION_REQUEST_DOCUMENT_SOURCE,
        INTENCION_REQUEST_EXACT_PAGE,
    }:
        return (
            "[Respuesta rápida de IA local]\n\n"
            "Detecté que pides fuentes o ampliación documental, pero no hay una consulta anterior "
            "en esta sesión para usar como contexto. Haz primero una pregunta concreta."
        )
    return ""


def _mensaje_intencion_documental_pendiente(intencion: str) -> str:
    if intencion == INTENCION_REQUEST_EXACT_PAGE:
        return (
            "[Respuesta rápida de IA local]\n\n"
            "Detecté que pides la página exacta. Esa parte se resolverá con búsqueda documental "
            "en la siguiente fase; por ahora aún no está conectada a libros desde este flujo."
        )
    if intencion in {INTENCION_REQUEST_CITATION, INTENCION_REQUEST_DOCUMENT_SOURCE}:
        return (
            "[Respuesta rápida de IA local]\n\n"
            "Detecté que pides citas, referencias o fuentes documentales. "
            "La detección ya está activa, pero la recuperación de libros se conectará en la siguiente fase."
        )
    return ""


def _pregunta_tiene_contenido_tematico(pregunta: str) -> bool:
    tokens = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+", pregunta or "")
    return len(tokens) >= 4


def _es_solicitud_documental_directa(intencion: str, pregunta: str, contexto: Dict) -> bool:
    if intencion not in {
        INTENCION_REQUEST_CITATION,
        INTENCION_REQUEST_DOCUMENT_SOURCE,
        INTENCION_REQUEST_EXACT_PAGE,
    }:
        return False
    if contexto.get("ultima_pregunta"):
        return True
    return _pregunta_tiene_contenido_tematico(pregunta)


def _resolver_intencion_en_sesion_vacia(
    pregunta: str,
    intencion: str,
    deteccion: Dict,
    contexto: Dict,
) -> str:
    if contexto.get("ultima_pregunta"):
        return intencion
    if deteccion.get("source") != "llm":
        return intencion
    if intencion in {
        INTENCION_REQUEST_CITATION,
        INTENCION_REQUEST_DOCUMENT_SOURCE,
        INTENCION_REQUEST_EXACT_PAGE,
    }:
        return intencion if _pregunta_tiene_contenido_tematico(pregunta) else INTENCION_NONE
    if intencion == INTENCION_DEEPEN and _pregunta_tiene_contenido_tematico(pregunta):
        return INTENCION_NONE
    return intencion


def _modo_respuesta_desde_etiqueta(respuesta: str) -> str:
    if respuesta.startswith("[Respuesta híbrida: IA local + documentos]"):
        return "hybrid"
    if respuesta.startswith("[Respuesta ampliada basada en documentos]"):
        return "documental"
    return "local"


def _heredar_tema_desde_contexto(clasificacion_tema: Dict, contexto: Dict) -> Dict:
    tema_actual = str(clasificacion_tema.get("theme", TEMA_GENERAL) or TEMA_GENERAL)
    tema_contexto = normalizar_tema(str(contexto.get("tema_detectado", TEMA_GENERAL)))
    if tema_contexto == TEMA_GENERAL:
        return clasificacion_tema

    source_actual = str(clasificacion_tema.get("source", "rules") or "rules")
    confianza_actual = float(clasificacion_tema.get("confidence", 0.0) or 0.0)
    if tema_actual != TEMA_GENERAL and source_actual == "rules" and confianza_actual >= 0.9:
        return clasificacion_tema

    return {
        "theme": tema_contexto,
        "confidence": float(contexto.get("tema_confianza", 0.85) or 0.85),
        "library": str(contexto.get("biblioteca_objetivo") or biblioteca_por_tema(tema_contexto)),
        "source": "session_context",
    }


def responder_consulta_local_rapida(
    pregunta: str,
    dominio: Optional[str] = None,
    subdominio: Optional[str] = None,
    config: Optional[LocalLLMConfig] = None,
    session_id: Optional[str] = None,
) -> str:
    pregunta_original = (pregunta or "").strip()
    if not pregunta_original:
        return "Debes escribir una consulta."

    session_key = _normalizar_session_id(session_id)
    respuesta = transmitir_consulta_local_rapida(
        pregunta=pregunta_original,
        config=config,
        session_id=session_key,
    )
    return respuesta


def transmitir_consulta_local_rapida(
    pregunta: str,
    on_chunk: Optional[Callable[[str], None]] = None,
    config: Optional[LocalLLMConfig] = None,
    session_id: Optional[str] = None,
) -> str:
    pregunta_original = (pregunta or "").strip()
    if not pregunta_original:
        return "Debes escribir una consulta."

    session_key = _normalizar_session_id(session_id)
    proveedor = obtener_local_llm_provider()
    config_efectiva = config or LocalLLMConfig(max_tokens=512, timeout=120, context_window=1024)
    partes: List[str] = []
    for chunk in proveedor.generate_stream(
        prompt=_prompt_respuesta_rapida(pregunta_original),
        system_prompt="Eres TLAMATINI. Responde de forma directa y útil a la pregunta del usuario.",
        config=config_efectiva,
    ):
        if not chunk:
            continue
        partes.append(chunk)
        if on_chunk is not None:
            on_chunk(chunk)
    respuesta = "".join(partes).strip()
    if not respuesta:
        raise RuntimeError("La IA local no devolvió contenido.")

    _actualizar_contexto_directo(
        pregunta_original=pregunta_original,
        respuesta=respuesta,
        session_id=session_key,
    )

    registrar_log(
        "consulta",
        (
            f"Consulta directa IA local: {pregunta_original} | "
            f"backend=direct_local | session_id={session_key}"
        ),
        "consulta",
    )
    return respuesta


def responder_consulta_inteligente(
    pregunta: str,
    dominio: Optional[str] = None,
    subdominio: Optional[str] = None,
    config: Optional[LocalLLMConfig] = None,
    session_id: Optional[str] = None,
) -> str:
    pregunta_original = (pregunta or "").strip()
    if not pregunta_original:
        return "Debes escribir una consulta."

    dominio = _normalizar(dominio or "")
    subdominio = _normalizar(subdominio or "")
    session_key = _normalizar_session_id(session_id)
    contexto = _obtener_contexto_sesion(session_key)
    deteccion = detectar_intencion_seguimiento(pregunta_original)
    intencion = _resolver_intencion_en_sesion_vacia(
        pregunta_original,
        deteccion["intent"],
        deteccion,
        contexto,
    )
    if intencion == INTENCION_NONE:
        return responder_consulta_local_rapida(
            pregunta=pregunta_original,
            dominio=dominio,
            subdominio=subdominio,
            config=config,
            session_id=session_key,
        )

    clasificacion_tema = clasificar_tema_consulta(
        pregunta_original,
        dominio_explicito=dominio or str(contexto.get("tema_detectado", "")),
        usar_fallback_llm=False,
        config=config,
    )

    if intencion == INTENCION_DEEPEN and not contexto.get("ultima_pregunta"):
        return _mensaje_sin_contexto_para_intencion(intencion)

    if _es_solicitud_documental_directa(intencion, pregunta_original, contexto):
        pregunta_documental = pregunta_original
        if contexto.get("ultima_pregunta") and not _pregunta_tiene_contenido_tematico(pregunta_original):
            pregunta_documental = str(contexto.get("ultima_pregunta"))

        if contexto.get("ultima_pregunta"):
            clasificacion_tema = _heredar_tema_desde_contexto(clasificacion_tema, contexto)

        modo_documental = "documental"
        if intencion == INTENCION_DEEPEN:
            modo_documental = "auto"
        elif intencion in {INTENCION_REQUEST_CITATION, INTENCION_REQUEST_DOCUMENT_SOURCE}:
            modo_documental = "documental"
        elif intencion == INTENCION_REQUEST_EXACT_PAGE:
            modo_documental = "documental"

        respuesta = responder_consulta_documental_tematica(
            pregunta=pregunta_documental,
            dominio=dominio or str(clasificacion_tema.get("theme", "")),
            subdominio=subdominio or str(contexto.get("subtema_detectado", "")),
            modo=modo_documental,
        )
        modo_respuesta = _modo_respuesta_desde_etiqueta(respuesta)
        _actualizar_contexto(
            pregunta_original=pregunta_original,
            pregunta_usada=pregunta_documental,
            dominio=dominio or str(clasificacion_tema.get("theme", "")),
            subdominio=subdominio or str(contexto.get("subtema_detectado", "")),
            resultados=[],
            session_id=session_key,
            respuesta=respuesta,
            modo_respuesta=modo_respuesta,
            intencion_seguimiento=intencion,
            clasificacion_tema=clasificacion_tema,
        )
        registrar_log(
            "consulta",
            (
                f"Consulta inteligente documental: {pregunta_original} | "
                f"intent={intencion} | source={deteccion['source']} | "
                f"theme={clasificacion_tema['theme']} | library={clasificacion_tema['library']} | "
                f"mode={modo_respuesta} | session_id={session_key}"
            ),
            "consulta",
        )
        return respuesta

    if intencion == INTENCION_DEEPEN:
        clasificacion_tema = _heredar_tema_desde_contexto(clasificacion_tema, contexto)
        pregunta_documental = str(contexto.get("ultima_pregunta", pregunta_original))
        respuesta = responder_consulta_documental_tematica(
            pregunta=pregunta_documental,
            dominio=dominio or str(clasificacion_tema.get("theme", "")),
            subdominio=subdominio or str(contexto.get("subtema_detectado", "")),
            modo="auto",
        )
        modo_respuesta = _modo_respuesta_desde_etiqueta(respuesta)
        _actualizar_contexto(
            pregunta_original=pregunta_original,
            pregunta_usada=pregunta_documental,
            dominio=dominio or str(clasificacion_tema.get("theme", "")),
            subdominio=subdominio or str(contexto.get("subtema_detectado", "")),
            resultados=[],
            session_id=session_key,
            respuesta=respuesta,
            modo_respuesta=modo_respuesta,
            intencion_seguimiento=intencion,
            clasificacion_tema=clasificacion_tema,
        )
        registrar_log(
            "consulta",
            (
                f"Consulta inteligente profundizacion: {pregunta_original} | "
                f"theme={clasificacion_tema['theme']} | library={clasificacion_tema['library']} | "
                f"mode={modo_respuesta} | session_id={session_key}"
            ),
            "consulta",
        )
        return respuesta

    return responder_consulta_local_rapida(
        pregunta=pregunta_original,
        dominio=dominio,
        subdominio=subdominio,
        config=config,
        session_id=session_key,
    )


def _formatear_resultados(
    pregunta_original: str,
    pregunta_usada: str,
    dominio: str,
    subdominio: str,
    resultados: List[Dict]
) -> str:
    if not resultados:
        return (
            f"Consulta: {pregunta_original}\n"
            f"Búsqueda usada: {pregunta_usada}\n"
            f"Dominio aplicado: {dominio or 'sin filtro'}\n"
            f"Subdominio aplicado: {subdominio or 'sin filtro'}\n\n"
            "No encontré coincidencias suficientes en los libros cargados."
        )

    principal = resultados[0]
    lineas = [
        f"Consulta: {pregunta_original}",
        f"Búsqueda usada: {pregunta_usada}",
        f"Dominio aplicado: {dominio or 'sin filtro'}",
        f"Subdominio aplicado: {subdominio or 'sin filtro'}",
        "",
        f"Libro principal: {principal['libro_nombre']}",
        f"Página principal: {principal['pagina']}",
    ]

    if principal.get("titulo_seccion"):
        lineas.append(f"Sección: {principal['titulo_seccion']}")

    lineas.extend([
        "",
        "Fragmento principal:",
        principal.get("snippet") or principal.get("texto") or "",
        "",
        "Coincidencias relacionadas:"
    ])

    for r in resultados[1:5]:
        ref = f"- {r['libro_nombre']} / pág. {r['pagina']}"
        if r.get("titulo_seccion"):
            ref += f" / sección {r['titulo_seccion']}"
        lineas.append(ref)

    lineas.extend([
        "",
        "Fuentes:"
    ])

    fuentes = []
    for r in resultados[:5]:
        f = f"{r['libro_nombre']} / pág. {r['pagina']}"
        if f not in fuentes:
            fuentes.append(f)

    for f in fuentes:
        lineas.append(f"- {f}")

    return "\n".join(lineas)


def responder_consulta(
    pregunta: str,
    dominio: Optional[str] = None,
    subdominio: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    pregunta_original = (pregunta or "").strip()
    if not pregunta_original:
        return "Debes escribir una consulta."

    dominio = _normalizar(dominio or "")
    subdominio = _normalizar(subdominio or "")
    clasificacion_tema = clasificar_tema_consulta(
        pregunta_original,
        dominio_explicito=dominio,
        usar_fallback_llm=True,
    )

    if dominio in ("", "todos"):
        dominio = ""

    if subdominio in ("", "general", "todos"):
        subdominio = ""

    pregunta_usada = _expandir_por_contexto(pregunta_original)

    resultados = buscar_fragmentos(
        pregunta=pregunta_usada,
        dominio=dominio,
        subdominio=subdominio,
        limite=8
    )

    respuesta_final = _formatear_resultados(
        pregunta_original=pregunta_original,
        pregunta_usada=pregunta_usada,
        dominio=dominio,
        subdominio=subdominio,
        resultados=resultados
    )

    _actualizar_contexto(
        pregunta_original=pregunta_original,
        pregunta_usada=pregunta_usada,
        dominio=dominio,
        subdominio=subdominio,
        resultados=resultados,
        session_id=session_id,
        respuesta=respuesta_final,
        modo_respuesta="documental",
        intencion_seguimiento=INTENCION_NONE,
        clasificacion_tema=clasificacion_tema,
    )

    registrar_log(
        "consulta",
        f"Consulta realizada: {pregunta_original} | intencion={detectar_intencion(pregunta_original)}",
        "consulta"
    )

    return respuesta_final
