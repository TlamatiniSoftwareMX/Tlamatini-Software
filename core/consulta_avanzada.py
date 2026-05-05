import re
from pathlib import Path
from typing import Dict, List, Tuple

from core.biblioteca import cargar_cache_libro, listar_libros, registrar_libro
from core.catalogo_dominios import catalogo_patrones_inferencia
from core.clasificador_temas import detectar_subdominio_sugerido
from core.documentos_tematicos import buscar_en_biblioteca_tematica
from core.indice_consulta import (
    buscar_fragmentos,
    detectar_intencion,
    normalizar_sin_acentos,
    normalizar_texto,
    reindexar_libro,
    tokens_significativos,
)
from core.lector_libros import cargar_libro_a_conocimiento
from core.local_llm import LocalLLMConfig, obtener_local_llm_provider
from core.logs import registrar_log
from core.tema_consulta import clasificar_tema_consulta


try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from haystack import Document as HaystackDocument
    from haystack.document_stores.in_memory import InMemoryDocumentStore
    from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
except Exception:
    HaystackDocument = None
    InMemoryDocumentStore = None
    InMemoryBM25Retriever = None

EXTENSIONES_COMPATIBLES = {".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
LIMITE_RESULTADOS = 12
LIMITE_CITAS = 8
UMBRAL_EVIDENCIA_FUERTE = 3
UMBRAL_COBERTURA_MINIMA = 2


INTENCIONES_SENSIBLES = {
    "dosis",
    "contraindicaciones",
    "indicaciones",
    "tratamiento",
}


PALABRAS_SINTOMAS = {
    "dolor", "fiebre", "nausea", "náusea", "vomito", "vómito", "diarrea", "cefalea",
    "tos", "disnea", "mareo", "melena", "hematemesis", "ardor", "pirosis",
    "fatiga", "debilidad", "palidez", "sangrado", "convulsion", "convulsión",
}


SECCIONES_OBJETIVO = {
    "definicion": ["definicion", "definición", "concepto", "descripcion", "descripción", "patologia", "patología", "que es", "qué es"],
    "sintomas": ["signos", "sintomas", "síntomas", "manifestaciones", "manifestaciones clinicas", "manifestaciones clínicas", "cuadro clinico", "cuadro clínico"],
    "tratamiento": ["tratamiento", "tratamiento medico", "tratamiento médico", "tratamiento farmacologico", "tratamiento farmacológico", "tratamiento quirurgico", "tratamiento quirúrgico", "manejo", "terapia", "procedimiento", "conducta", "de apoyo", "pasos", "paso a paso", "preparacion", "preparación", "instalacion", "instalación", "reparacion", "reparación", "mantenimiento", "ajuste", "calibracion", "calibración", "armado", "montaje", "siembra", "cultivo", "riego", "poda", "control"],
    "pruebas": ["pruebas", "pruebas diagnosticas", "pruebas diagnósticas", "pruebas de laboratorio", "laboratorio", "gabinete", "estudios complementarios", "imagen", "imagenes", "imágenes", "radiografia", "radiografía", "tomografia", "tomografía", "ecografia", "ecografía", "ultrasonido", "endoscopia", "endoscopía", "colonoscopia", "colonoscopía", "sigmoidoscopia", "sigmoidoscopía", "biopsia"],
    "indicaciones": ["indicaciones", "indicacion", "indicación", "para que sirve", "para qué sirve", "uso"],
    "dosis": ["dosis", "dosificacion", "dosificación", "posologia", "posología", "via de administracion", "vía de administración"],
    "riesgos": ["contraindicaciones", "precauciones", "advertencias", "reacciones adversas", "interacciones", "riesgos", "seguridad", "peligros", "epp", "proteccion", "protección", "cuidados"],
    "asociacion": ["diagnostico", "diagnóstico", "diagnostico diferencial", "diagnóstico diferencial", "evaluacion", "evaluación", "anamnesis", "etiologia", "etiología", "causas", "clasificacion", "clasificación", "falla", "averia", "avería", "problema", "inspeccion", "inspección", "revision", "revisión", "verificacion", "verificación"],
    "complicaciones": ["complicaciones", "complicacion", "complicación", "pronostico", "pronóstico", "evolucion", "evolución", "manifestaciones extraintestinales"],
    "administracion": ["via de administracion", "vía de administración", "administracion", "administración", "frecuencia", "cada"],
    "contraindicaciones": ["contraindicaciones", "contraindicacion", "contraindicación", "restricciones", "no administrar"],
    "efectos_adversos": ["reacciones adversas", "efectos adversos", "evento adverso", "toxicidad", "sobredosis"],
    "alarma": ["urgencia", "alarma", "complicaciones", "sangrado", "choque", "grave", "severo"],
    "composicion": ["composicion", "composición", "componentes", "componente", "materiales", "material", "ingredientes", "ingrediente", "partes", "refacciones", "insumos", "mezcla"],
    "presentacion": ["presentacion", "presentación", "formato", "medidas", "dimensiones", "tamano", "tamaño", "capacidad", "especificaciones"],
}


DOMINIOS_EQUIVALENTES = {
    "general": "general",
    "medica": "medica",
    "medicina": "medica",
    "medico": "medica",
    "médica": "medica",
    "médico": "medica",
    "proteccion_civil": "proteccion_civil",
    "protección_civil": "proteccion_civil",
    "proteccion civil": "proteccion_civil",
    "protección civil": "proteccion_civil",
    "autosuficiencia": "autosuficiencia",
    "instalacion": "instalacion_mantenimiento_reparacion",
    "instalación": "instalacion_mantenimiento_reparacion",
    "instalacion_mantenimiento_reparacion": "instalacion_mantenimiento_reparacion",
    "instalación_mantenimiento_reparación": "instalacion_mantenimiento_reparacion",
    "mantenimiento": "instalacion_mantenimiento_reparacion",
    "reparacion": "instalacion_mantenimiento_reparacion",
    "reparación": "instalacion_mantenimiento_reparacion",
    "animales": "animales",
}


PATRONES_DOMINIO = catalogo_patrones_inferencia(include_possible=True)


def runtime_local_esta_disponible() -> Tuple[bool, str]:
    return obtener_local_llm_provider().is_available()


def ollama_esta_disponible() -> Tuple[bool, str]:
    # Compatibilidad histórica para llamadas antiguas de la UI.
    return runtime_local_esta_disponible()


def _normalizar_dominio(dominio: str) -> str:
    dominio_n = normalizar_sin_acentos(dominio or "")
    return DOMINIOS_EQUIVALENTES.get(dominio_n, dominio_n or "general")


def _inferir_dominios_desde_pregunta(pregunta: str) -> List[str]:
    pregunta_n = normalizar_sin_acentos(pregunta)
    detectados = []

    for dominio, patrones in PATRONES_DOMINIO.items():
        if any(normalizar_sin_acentos(patron) in pregunta_n for patron in patrones):
            detectados.append(dominio)

    intencion = detectar_intencion(pregunta)
    if intencion in INTENCIONES_SENSIBLES and "medica" not in detectados:
        detectados.insert(0, "medica")

    return detectados


def _extraer_tema_principal(pregunta: str) -> str:
    pregunta_n = normalizar_texto(pregunta)
    recortes = [
        "dame informacion sobre ", "dame información sobre ", "informacion sobre ", "información sobre ",
        "mas informacion sobre ", "más información sobre ", "quiero informacion sobre ", "quiero información sobre ",
        "materiales para ", "materiales de ", "materiales ", "herramientas para ", "herramientas de ", "herramientas ",
        "seguridad para ", "seguridad de ", "seguridad ", "precauciones para ", "precauciones de ", "precauciones ",
        "diagnostico de ", "diagnóstico de ", "diagnostico para ", "diagnóstico para ",
        "mantenimiento de ", "mantenimiento para ", "mantenimiento ", "reparacion de ", "reparación de ", "reparacion ", "reparación ",
        "instalacion de ", "instalación de ", "dosis de ", "dosis para ",
        "dosis ", "mezcla de ", "mezcla para ", "mezcla ",
        "tratamiento ", "diagnostico ", "diagnóstico ", "signos y sintomas ", "signos y síntomas ",
        "sintomas ", "síntomas ", "complicaciones ", "definicion ", "definición ", "informacion ", "información ",
        "cual es el tratamiento para ", "cuál es el tratamiento para ",
        "cual es el tratamiento de ", "cuál es el tratamiento de ",
        "tratamiento para ", "tratamiento de ",
        "cual es el manejo de ", "cuál es el manejo de ",
        "manejo de ", "manejo para ",
        "que es ", "qué es ", "signos y sintomas de ", "signos y síntomas de ", "sintomas de ", "síntomas de ",
        "tratamiento de ", "manejo de ", "dosis de ", "para que sirve ", "para qué sirve ", "riesgos de ",
        "que enfermedad causa ", "que trastorno causa ", "que enfermedad se asocia con ", "que trastorno se asocia con ",
    ]
    for recorte in recortes:
        if pregunta_n.startswith(recorte):
            pregunta_n = pregunta_n[len(recorte):].strip(" ?.")
            break

    for prefijo in ("la ", "el ", "los ", "las ", "un ", "una "):
        if pregunta_n.startswith(prefijo):
            pregunta_n = pregunta_n[len(prefijo):].strip()
            break

    return pregunta_n.strip(" ?.")


def _consulta_desde_palabras_clave(pregunta: str) -> Dict[str, str | List[str]]:
    tema = _extraer_tema_principal(pregunta)
    grupos = _grupos_objetivo_desde_pregunta(pregunta)
    intencion = detectar_intencion(pregunta)
    if grupos == ["tratamiento"]:
        consulta = f"tratamiento {tema}".strip()
    elif grupos == ["dosis", "administracion"]:
        consulta = f"dosis {tema}".strip()
    elif grupos == ["contraindicaciones", "riesgos"]:
        consulta = f"contraindicaciones {tema}".strip()
    elif grupos == ["indicaciones", "definicion"]:
        consulta = f"indicaciones {tema}".strip()
    elif grupos == ["sintomas"]:
        consulta = f"sintomas {tema}".strip()
    elif grupos == ["complicaciones", "alarma"]:
        consulta = f"seguridad {tema}".strip() if intencion == "precauciones" else f"complicaciones {tema}".strip()
    elif grupos == ["asociacion", "pruebas"]:
        consulta = f"diagnostico {tema}".strip()
    elif grupos == ["composicion", "presentacion"]:
        consulta = f"materiales {tema}".strip()
    else:
        consulta = tema or pregunta.strip()
    return {
        "tema": tema,
        "grupos": grupos,
        "consulta_busqueda": consulta,
    }


def _grupos_objetivo_desde_pregunta(pregunta: str) -> List[str]:
    pregunta_n = normalizar_sin_acentos(pregunta)
    intencion = detectar_intencion(pregunta)

    if intencion == "informacion" or any(x in pregunta_n for x in ["informacion", "información", "generalidades", "resumen", "sobre "]):
        return []
    if intencion in {"composicion", "presentacion"} or any(x in pregunta_n for x in ["materiales", "material", "ingredientes", "ingrediente", "componentes", "componente", "partes", "refacciones", "insumos", "herramientas", "herramienta", "equipo", "equipos", "dimensiones", "medidas", "capacidad", "formato", "especificaciones"]):
        return ["composicion", "presentacion"]
    if intencion == "tratamiento" or any(x in pregunta_n for x in ["tratamiento", "manejo", "terapia", "conducta", "procedimiento", "pasos", "paso a paso", "preparacion", "preparación", "instalacion", "instalación", "reparacion", "reparación", "mantenimiento", "armado", "montaje", "siembra", "cultivo", "riego", "poda"]):
        return ["tratamiento"]
    if intencion == "dosis" or "dosis" in pregunta_n:
        return ["dosis", "administracion"]
    if intencion == "contraindicaciones" or "contraindic" in pregunta_n:
        return ["contraindicaciones", "riesgos"]
    if intencion == "indicaciones" or any(x in pregunta_n for x in ["para que sirve", "para qué sirve", "indicaciones", "uso"]):
        return ["indicaciones", "definicion"]
    if any(x in pregunta_n for x in ["signos y sintomas", "signos y síntomas", "sintomas", "síntomas"]):
        return ["sintomas"]
    if intencion == "precauciones" or any(x in pregunta_n for x in ["complicaciones", "signos de alarma", "alarma", "seguridad", "peligros", "advertencias", "epp", "proteccion", "protección", "cuidados"]):
        return ["complicaciones", "alarma"]
    if intencion in {"diagnostico", "etiologia"} or any(x in pregunta_n for x in ["diagnostico", "diagnóstico", "etiologia", "etiología", "causa", "falla", "averia", "avería", "problema", "inspeccion", "inspección", "revision", "revisión", "verificacion", "verificación", "pruebas"]):
        return ["asociacion", "pruebas"]
    return []


def _tokens_nucleo_tema(tema: str) -> List[str]:
    excluir = {
        "tratamiento", "manejo", "terapia", "conducta", "dosis", "indicaciones", "uso",
        "contraindicaciones", "contraindicacion", "riesgos", "efectos", "adversos",
        "diagnostico", "diagnóstico", "sintomas", "síntomas", "signos", "complicaciones",
        "alarma", "materiales", "material", "ingredientes", "ingrediente", "componentes",
        "componente", "herramientas", "herramienta", "equipo", "equipos", "instalacion",
        "instalación", "reparacion", "reparación", "mantenimiento", "pasos", "paso",
        "cual", "cuál", "que", "qué", "para", "de", "del",
    }
    tokens = []
    for token in tokens_significativos(tema or ""):
        token_n = normalizar_sin_acentos(token)
        if token_n and token_n not in excluir and token_n not in tokens:
            tokens.append(token_n)
    return tokens


def _cobertura_nucleo_tema(tema: str, texto: str, titulo: str = "") -> float:
    tokens = _tokens_nucleo_tema(tema)
    if not tokens:
        return 0.0
    texto_n = normalizar_sin_acentos(texto or "")
    titulo_n = normalizar_sin_acentos(titulo or "")
    coincidencias = sum(1 for token in tokens if token in texto_n or token in titulo_n)
    return coincidencias / max(1, len(tokens))


def _ocr_imagen(ruta: Path) -> str:
    if Image is None or pytesseract is None:
        return ""

    try:
        imagen = Image.open(ruta).convert("RGB")
        texto = pytesseract.image_to_string(imagen, lang="spa+eng")
        return " ".join((texto or "").strip().split())
    except Exception:
        return ""


def _indexar_imagen(ruta: Path, dominio: str, subdominio: str) -> Dict:
    texto = _ocr_imagen(ruta)
    if not texto:
        return {"ok": False, "mensaje": "No se pudo extraer texto útil de la imagen."}

    subdominio_final = (subdominio or "general").strip().lower()
    if subdominio_final in ("", "general"):
        sugerido = detectar_subdominio_sugerido(dominio, texto[:3000])
        if sugerido:
            subdominio_final = sugerido

    libro = registrar_libro(
        ruta_archivo=str(ruta),
        dominio=dominio,
        subdominio=subdominio_final or "general",
        tipo_archivo=ruta.suffix.lower().replace(".", ""),
        paginas=1,
        caracteres_extraidos=len(texto),
        temas_detectados=[],
        paginas_indexadas=[1],
    )

    paginas = [{"pagina": 1, "texto": texto, "secciones": {}, "temas": []}]
    total_fragmentos = reindexar_libro(libro, paginas)

    registrar_log(
        "sistema",
        f"Imagen cargada e indexada: {libro['nombre']} (1 página lógica, {total_fragmentos} fragmentos)",
        "lector_libros",
    )

    return {
        "ok": True,
        "mensaje": f"Imagen cargada correctamente: {libro['nombre']} ({total_fragmentos} fragmentos indexados)",
        "libro": libro,
        "fragmentos": total_fragmentos,
    }


def indexar_documento(ruta_archivo: str, dominio: str = "general", subdominio: str = "general") -> Dict:
    ruta = Path(ruta_archivo).expanduser().resolve()

    if not ruta.exists():
        return {"ok": False, "mensaje": "No se encontró el archivo indicado."}

    ext = ruta.suffix.lower()
    if ext not in EXTENSIONES_COMPATIBLES:
        return {"ok": False, "mensaje": "Formato no soportado. Usa PDF, TXT, MD o imágenes."}

    dominio = _normalizar_dominio(dominio)
    subdominio = normalizar_texto(subdominio or "general") or "general"

    if ext in {".pdf", ".txt", ".md"}:
        return cargar_libro_a_conocimiento(str(ruta), dominio=dominio, subdominio=subdominio)

    return _indexar_imagen(ruta, dominio=dominio, subdominio=subdominio)


def _parrafos_de_texto(texto: str) -> List[str]:
    texto = (texto or "").replace("\r", "\n")
    bloques = [b.strip() for b in texto.split("\n\n") if b.strip()]
    if bloques:
        return bloques

    frases = re.split(r"(?<=[\.\!\?\:;])\s+", texto.strip())
    return [f.strip() for f in frases if f.strip()]


def _score_cita(pregunta: str, texto: str, titulo: str = "") -> float:
    pregunta_n = normalizar_sin_acentos(pregunta)
    texto_n = normalizar_sin_acentos(texto)
    titulo_n = normalizar_sin_acentos(titulo)
    tokens = tokens_significativos(pregunta)

    score = 0.0
    if pregunta_n and pregunta_n in texto_n:
        score += 20.0
    if pregunta_n and pregunta_n in titulo_n:
        score += 9.0

    coinc = sum(1 for t in tokens if normalizar_sin_acentos(t) in texto_n)
    score += coinc * 3.5

    if detectar_intencion(pregunta) == "definicion":
        if any(x in texto_n for x in [" es ", " se define ", " consiste en ", " se considera "]):
            score += 4.0

    return score


def _bonus_por_dominio(cita: Dict, dominios_prioritarios: List[str]) -> float:
    dominio_cita = _normalizar_dominio(cita.get("dominio", ""))
    if dominio_cita and dominio_cita in dominios_prioritarios:
        return 3.0
    return 0.0


def _score_por_seccion(cita: Dict, grupos: List[str]) -> float:
    titulo = normalizar_sin_acentos(cita.get("titulo_seccion", ""))
    texto = normalizar_sin_acentos(cita.get("texto", ""))
    score = 0.0
    for grupo in grupos:
        for patron in SECCIONES_OBJETIVO.get(grupo, []):
            patron_n = normalizar_sin_acentos(patron)
            if patron_n and patron_n in titulo:
                score += 6.0
            elif patron_n and patron_n in texto[:240]:
                score += 2.0
    return score


def _tokens_relevantes_pregunta(pregunta: str) -> List[str]:
    tokens = []
    for token in tokens_significativos(pregunta):
        token_n = normalizar_sin_acentos(token)
        if token_n and token_n not in tokens:
            tokens.append(token_n)
    return tokens


def _tokens_tema(tema: str) -> List[str]:
    return [normalizar_sin_acentos(t) for t in tokens_significativos(tema or "")]


def _cobertura_tema_en_texto(tema: str, texto: str, titulo: str = "") -> float:
    tema_n = normalizar_sin_acentos(tema or "")
    texto_n = normalizar_sin_acentos(texto or "")
    titulo_n = normalizar_sin_acentos(titulo or "")
    tokens = _tokens_tema(tema)
    if not tokens:
        return 0.0

    if tema_n and (tema_n in texto_n or tema_n in titulo_n):
        return 1.0

    coincidencias = sum(1 for token in tokens if token in texto_n or token in titulo_n)
    return coincidencias / max(1, len(tokens))


def _extraer_citas_de_resultados(pregunta: str, resultados: List[Dict], limite: int = LIMITE_CITAS) -> List[Dict]:
    dominios_prioritarios = _inferir_dominios_desde_pregunta(pregunta)
    citas = []
    tema = _extraer_tema_principal(pregunta)
    grupos_objetivo = _grupos_objetivo_desde_pregunta(pregunta)

    for resultado in resultados:
        titulo = resultado.get("titulo_seccion", "")
        parrafos = _parrafos_de_texto(resultado.get("texto", ""))
        for idx, parrafo in enumerate(parrafos, start=1):
            score = _score_cita(pregunta, parrafo, titulo)
            score += _score_por_seccion(
                {
                    "titulo_seccion": titulo,
                    "texto": parrafo,
                },
                ["definicion", "sintomas", "tratamiento", "asociacion", "complicaciones", "dosis", "indicaciones", "riesgos", "administracion", "contraindicaciones", "efectos_adversos", "alarma"],
            )
            cobertura_tema = _cobertura_tema_en_texto(tema, parrafo, titulo)
            cobertura_nucleo = _cobertura_nucleo_tema(tema, parrafo, titulo)
            if tema and normalizar_sin_acentos(tema) in normalizar_sin_acentos(parrafo):
                score += 3.0
            elif cobertura_tema > 0:
                score += cobertura_tema * 2.5
            if cobertura_nucleo > 0:
                score += cobertura_nucleo * 8.0
            if len(_tokens_tema(tema)) >= 2 and cobertura_tema < 0.5 and titulo:
                score -= 4.0
            if _tokens_nucleo_tema(tema) and cobertura_nucleo == 0:
                score -= 8.0
            elif _tokens_nucleo_tema(tema) and cobertura_nucleo < 0.5:
                score -= 3.0

            if grupos_objetivo:
                score += _score_por_seccion(
                    {
                        "titulo_seccion": titulo,
                        "texto": parrafo,
                    },
                    grupos_objetivo,
                ) * 1.8
                if _score_por_seccion({"titulo_seccion": titulo, "texto": parrafo}, grupos_objetivo) <= 0:
                    score -= 2.5
                if _tokens_nucleo_tema(tema) and cobertura_nucleo == 0:
                    score -= 28.0
                elif _tokens_nucleo_tema(tema) and cobertura_nucleo > 0:
                    score += 6.0
            parrafo_n = normalizar_sin_acentos(parrafo)
            if parrafo_n.startswith(("contenido", "indice", "índice")):
                score -= 14.0
            if "..." in parrafo[:120]:
                score -= 4.0

            # Si el resultado proviene de una sección relevante, no lo descartes aunque el texto
            # no repita exactamente el nombre del tema en cada párrafo.
            if score <= 0 and not titulo:
                continue
            citas.append(
                {
                    "libro_nombre": resultado["libro_nombre"],
                    "libro_id": resultado["libro_id"],
                    "pagina": resultado["pagina"],
                    "parrafo": idx,
                    "titulo_seccion": titulo,
                    "texto": parrafo.strip(),
                    "dominio": resultado.get("dominio", ""),
                    "subdominio": resultado.get("subdominio", ""),
                    "score": score + _bonus_por_dominio(resultado, dominios_prioritarios),
                }
            )

    citas.sort(key=lambda x: x["score"], reverse=True)

    unicas = []
    vistos = set()
    for cita in citas:
        clave = (cita["libro_nombre"], cita["pagina"], cita["parrafo"], cita["texto"][:160])
        if clave in vistos:
            continue
        vistos.add(clave)
        unicas.append(cita)
        if len(unicas) >= limite:
            break

    return unicas


def _evidencia_es_fuerte(pregunta: str, resultados: List[Dict], citas: List[Dict]) -> bool:
    if not resultados or not citas:
        return False

    mejor = citas[0]
    tokens = _tokens_relevantes_pregunta(pregunta)
    texto_n = normalizar_sin_acentos(mejor["texto"])
    cobertura = sum(1 for t in tokens if normalizar_sin_acentos(t) in texto_n)

    return mejor["score"] >= UMBRAL_EVIDENCIA_FUERTE and cobertura >= max(1, min(3, len(tokens)))


def _cobertura_tokens_en_cita(tokens: List[str], cita: Dict) -> int:
    texto_n = normalizar_sin_acentos(cita.get("texto", ""))
    titulo_n = normalizar_sin_acentos(cita.get("titulo_seccion", ""))
    return sum(1 for token in tokens if token in texto_n or token in titulo_n)


def _hay_validacion_cruzada(pregunta: str, citas: List[Dict]) -> bool:
    if len(citas) < 2:
        return False

    tokens = _tokens_relevantes_pregunta(pregunta)
    if not tokens:
        return False

    libros = {cita.get("libro_id", cita.get("libro_nombre", "")) for cita in citas[:4]}
    paginas = {(cita.get("libro_id", ""), cita.get("pagina", 0)) for cita in citas[:4]}
    coberturas = [_cobertura_tokens_en_cita(tokens, cita) for cita in citas[:4]]

    suficientes = sum(1 for cobertura in coberturas if cobertura >= min(len(tokens), UMBRAL_COBERTURA_MINIMA))
    return suficientes >= 2 and (len(libros) >= 2 or len(paginas) >= 2)


def _es_pregunta_sensible(pregunta: str) -> bool:
    intencion = detectar_intencion(pregunta)
    if intencion in INTENCIONES_SENSIBLES:
        return True

    pregunta_n = normalizar_sin_acentos(pregunta)
    terminos = [
        "dosis", "via de administracion", "via", "contraindic", "tratamiento",
        "manejo", "precauc", "interaccion", "embarazo", "lactancia",
        "reparacion electrica", "alto voltaje", "combustible", "soldadura",
    ]
    return any(termino in pregunta_n for termino in terminos)


def _detectar_conflicto_entre_citas(citas: List[Dict]) -> bool:
    if len(citas) < 2:
        return False

    textos = [normalizar_sin_acentos(cita.get("texto", "")) for cita in citas[:3]]

    patrones_conflicto = [
        ("contraindicado", "indicado"),
        ("no se recomienda", "se recomienda"),
        ("debe evitarse", "puede utilizarse"),
        ("no administrar", "administrar"),
    ]

    for a, b in patrones_conflicto:
        hay_a = any(a in texto for texto in textos)
        hay_b = any(b in texto for texto in textos)
        if hay_a and hay_b:
            return True

    cantidades = set()
    for texto in textos:
        for numero, unidad in re.findall(r"(\d+(?:[\.,]\d+)?)\s*(mg|g|mcg|ml|gotas|tabletas|capsulas|cápsulas|ampolletas?)", texto):
            cantidades.add(f"{numero}-{unidad}")
    if len(cantidades) >= 2:
        return True

    return False


def _buscar_resultados_priorizados(pregunta: str, dominio: str = "", subdominio: str = "") -> List[Dict]:
    dominio = _normalizar_dominio(dominio)
    subdominio = normalizar_texto(subdominio)
    dominios_objetivo = []

    if dominio and dominio not in ("", "general", "todos"):
        dominios_objetivo.append(dominio)
    dominios_objetivo.extend([d for d in _inferir_dominios_desde_pregunta(pregunta) if d not in dominios_objetivo])

    resultados = []
    vistos = set()

    for dominio_objetivo in dominios_objetivo:
        for item in buscar_fragmentos(
            pregunta=pregunta,
            dominio=dominio_objetivo,
            subdominio=subdominio,
            limite=max(LIMITE_RESULTADOS, 6),
        ):
            clave = (
                item.get("libro_id"),
                item.get("pagina"),
                (item.get("titulo_seccion") or "").strip().lower(),
                (item.get("texto_normalizado") or "")[:220],
            )
            if clave in vistos:
                continue
            vistos.add(clave)
            item["score_final"] = item.get("score_final", 0) - 0.45
            resultados.append(item)

    for item in buscar_fragmentos(pregunta=pregunta, dominio="", subdominio=subdominio, limite=max(LIMITE_RESULTADOS, 10)):
        clave = (
            item.get("libro_id"),
            item.get("pagina"),
            (item.get("titulo_seccion") or "").strip().lower(),
            (item.get("texto_normalizado") or "")[:220],
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        resultados.append(item)

    resultados.sort(key=lambda x: x.get("score_final", 999999))
    return resultados[: max(LIMITE_RESULTADOS * 2, 12)]


def _haystack_disponible() -> bool:
    return HaystackDocument is not None and InMemoryDocumentStore is not None and InMemoryBM25Retriever is not None


def _documentos_haystack_desde_biblioteca(dominio: str = "", subdominio: str = "") -> List:
    if not _haystack_disponible():
        return []

    documentos = []
    for libro in listar_libros(dominio=dominio, subdominio=subdominio):
        payload = cargar_cache_libro(libro.get("cache_json", ""))
        for pagina in payload.get("paginas", []) or []:
            texto_pagina = (pagina.get("texto") or "").strip()
            if texto_pagina:
                documentos.append(
                    HaystackDocument(
                        content=texto_pagina,
                        meta={
                            "libro_id": libro.get("id", ""),
                            "libro_nombre": libro.get("nombre", ""),
                            "dominio": libro.get("dominio", ""),
                            "subdominio": libro.get("subdominio", ""),
                            "pagina": pagina.get("pagina", 0),
                            "titulo_seccion": "",
                            "tipo": "pagina",
                        },
                    )
                )

            for titulo_seccion, texto_seccion in (pagina.get("secciones") or {}).items():
                if not (texto_seccion or "").strip():
                    continue
                documentos.append(
                    HaystackDocument(
                        content=texto_seccion,
                        meta={
                            "libro_id": libro.get("id", ""),
                            "libro_nombre": libro.get("nombre", ""),
                            "dominio": libro.get("dominio", ""),
                            "subdominio": libro.get("subdominio", ""),
                            "pagina": pagina.get("pagina", 0),
                            "titulo_seccion": titulo_seccion,
                            "tipo": "seccion",
                        },
                    )
                )
    return documentos


def _buscar_con_haystack(pregunta: str, dominio: str = "", subdominio: str = "", limite: int = 12) -> List[Dict]:
    if not _haystack_disponible():
        return []

    documentos = _documentos_haystack_desde_biblioteca(dominio=dominio, subdominio=subdominio)
    if not documentos:
        return []

    try:
        store = InMemoryDocumentStore(bm25_algorithm="BM25L")
        store.write_documents(documentos)
        retriever = InMemoryBM25Retriever(document_store=store, top_k=max(limite, 18), scale_score=True)
        salida = retriever.run(query=pregunta)
    except Exception as e:
        registrar_log("error", f"Haystack falló al recuperar documentos: {e}", "consulta")
        return []

    resultados = []
    vistos = set()
    for doc in salida.get("documents", []):
        contenido = (getattr(doc, "content", "") or "").strip()
        meta = getattr(doc, "meta", {}) or {}
        clave = (
            meta.get("libro_id", ""),
            meta.get("pagina", 0),
            meta.get("titulo_seccion", ""),
            contenido[:220],
        )
        if not contenido or clave in vistos:
            continue
        vistos.add(clave)
        resultados.append(
            {
                "libro_id": meta.get("libro_id", ""),
                "libro_nombre": meta.get("libro_nombre", ""),
                "dominio": meta.get("dominio", ""),
                "subdominio": meta.get("subdominio", ""),
                "pagina": meta.get("pagina", 0),
                "tipo": meta.get("tipo", ""),
                "titulo_seccion": meta.get("titulo_seccion", ""),
                "texto": contenido,
                "texto_normalizado": normalizar_texto(contenido),
                "score_final": -(getattr(doc, "score", 0.0) or 0.0),
                "snippet": _limitar_texto(contenido, 360),
            }
        )

    resultados.sort(key=lambda x: x.get("score_final", 999999))
    return resultados[:limite]


def _paginas_vecinas_del_cache(libro_id: str, pagina_base: int, radio: int = 2) -> List[Dict]:
    libro = next((l for l in listar_libros() if l.get("id") == libro_id), None)
    if not libro:
        return []

    payload = cargar_cache_libro(libro.get("cache_json", ""))
    salida = []
    for pagina in payload.get("paginas", []) or []:
        numero = int(pagina.get("pagina", 0) or 0)
        if numero <= 0 or numero == pagina_base or abs(numero - pagina_base) > radio:
            continue
        texto = (pagina.get("texto") or "").strip()
        if not texto:
            continue
        salida.append(
            {
                "libro_id": libro.get("id", ""),
                "libro_nombre": libro.get("nombre", ""),
                "dominio": libro.get("dominio", ""),
                "subdominio": libro.get("subdominio", ""),
                "pagina": numero,
                "tipo": "pagina_vecina",
                "titulo_seccion": "",
                "texto": texto,
                "texto_normalizado": normalizar_texto(texto),
                "score_final": 999998 + abs(numero - pagina_base),
                "snippet": _limitar_texto(texto, 360),
            }
        )
    return salida


def _expandir_resultados_por_continuidad(pregunta: str, resultados: List[Dict]) -> List[Dict]:
    if not resultados:
        return resultados

    tema = normalizar_sin_acentos(_extraer_tema_principal(pregunta))
    if not tema:
        return resultados

    expandidos = list(resultados)
    vistos = {
        (
            r.get("libro_id", ""),
            r.get("pagina", 0),
            (r.get("titulo_seccion") or "").strip().lower(),
            (r.get("texto_normalizado") or "")[:220],
        )
        for r in resultados
    }

    candidatos_base = []
    for resultado in resultados[:4]:
        texto_n = normalizar_sin_acentos(resultado.get("texto", ""))
        titulo_n = normalizar_sin_acentos(resultado.get("titulo_seccion", ""))
        if tema in texto_n or tema in titulo_n:
            candidatos_base.append(resultado)

    for base in candidatos_base:
        for vecino in _paginas_vecinas_del_cache(base.get("libro_id", ""), int(base.get("pagina", 0)), radio=2):
            texto_n = normalizar_sin_acentos(vecino.get("texto", ""))
            if not any(p in texto_n for p in ["tratamiento", "diagnostico", "diagnóstico", "complicaciones", "manifestaciones", tema]):
                continue
            clave = (
                vecino.get("libro_id", ""),
                vecino.get("pagina", 0),
                (vecino.get("titulo_seccion") or "").strip().lower(),
                (vecino.get("texto_normalizado") or "")[:220],
            )
            if clave in vistos:
                continue
            vistos.add(clave)
            expandidos.append(vecino)

    expandidos.sort(key=lambda x: x.get("score_final", 999999))
    return expandidos


def _limitar_texto(texto: str, max_chars: int = 420) -> str:
    texto = " ".join((texto or "").split())
    if len(texto) <= max_chars:
        return texto
    return texto[: max_chars - 3].rstrip() + "..."


def _frases_relevantes(texto: str, tema: str = "", patrones: List[str] = None, max_frases: int = 1) -> str:
    frases = [f.strip() for f in re.split(r"(?<=[\.\!\?\:;])\s+", normalizar_texto(texto)) if f.strip()]
    if not frases:
        return _limitar_texto(texto, 220)

    tema_tokens = [normalizar_sin_acentos(t) for t in tokens_significativos(tema or "")][:5]
    patrones_n = [normalizar_sin_acentos(p) for p in (patrones or [])]

    puntuadas = []
    for frase in frases:
        frase_n = normalizar_sin_acentos(frase)
        score = 0.0
        score += sum(2.5 for token in tema_tokens if token and token in frase_n)
        score += sum(2.0 for patron in patrones_n if patron and patron in frase_n)
        if any(c.isdigit() for c in frase) and any(x in frase_n for x in ["mg", "ml", "horas", "dias", "días", "cada", "via", "vía"]):
            score += 2.0
        if len(frase) < 30:
            score -= 0.5
        puntuadas.append((score, frase))

    puntuadas.sort(key=lambda x: x[0], reverse=True)
    mejores = [frase for score, frase in puntuadas[:max_frases] if score > 0]
    if not mejores:
        mejores = frases[:max_frases]
    return " ".join(_limitar_texto(frase, 140) for frase in mejores)


def _resumen_puntual(texto: str, tema: str = "", patrones: List[str] = None) -> str:
    return _frases_relevantes(texto, tema=tema, patrones=patrones or [], max_frases=1)


def _detectar_modo_respuesta(pregunta: str, citas: List[Dict]) -> str:
    pregunta_n = normalizar_sin_acentos(pregunta)
    grupos_objetivo = _grupos_objetivo_desde_pregunta(pregunta)
    titulos = " ".join(normalizar_sin_acentos(c.get("titulo_seccion", "")) for c in citas[:6])

    if grupos_objetivo:
        if grupos_objetivo in (["dosis", "administracion"], ["contraindicaciones", "riesgos"], ["indicaciones", "definicion"]):
            return "medicamento"
        if grupos_objetivo == ["sintomas"]:
            return "sintomas"
        return "enfermedad"

    if any(x in pregunta_n for x in ["informacion", "información", "resumen", "generalidades", "que es", "qué es"]):
        return "enfermedad"

    if any(x in pregunta_n for x in ["dosis", "para que sirve", "para qué sirve", "contraindic", "riesgos", "efectos adversos"]):
        return "medicamento"

    tokens = set(_tokens_relevantes_pregunta(pregunta))
    if len(tokens & {normalizar_sin_acentos(x) for x in PALABRAS_SINTOMAS}) >= 2:
        return "sintomas"

    if any(x in titulos for x in ["dosis", "indicaciones", "contraindicaciones", "reacciones adversas"]):
        return "medicamento"

    if any(x in titulos for x in ["signos", "sintomas", "tratamiento", "cuadro clinico", "cuadro clínico"]):
        return "enfermedad"

    if len(_tokens_relevantes_pregunta(pregunta)) <= 3 and citas:
        if any(x in titulos for x in ["indicaciones", "dosis", "contraindicaciones"]):
            return "medicamento"
        return "enfermedad"

    return "general"


def _seleccionar_cita_para_grupo(citas: List[Dict], grupos: List[str], tema: str = "") -> Dict:
    mejor = None
    mejor_score = -1.0
    tema_n = normalizar_sin_acentos(tema)
    for cita in citas:
        score = cita.get("score", 0.0) + _score_por_seccion(cita, grupos)
        texto_n = normalizar_sin_acentos(cita.get("texto", ""))
        titulo_n = normalizar_sin_acentos(cita.get("titulo_seccion", ""))
        cobertura_tema = _cobertura_tema_en_texto(tema, cita.get("texto", ""), cita.get("titulo_seccion", ""))
        cobertura_nucleo = _cobertura_nucleo_tema(tema, cita.get("texto", ""), cita.get("titulo_seccion", ""))
        if tema_n and tema_n in texto_n:
            score += 4.0
        elif cobertura_tema > 0:
            score += cobertura_tema * 3.0
        if cobertura_nucleo > 0:
            score += cobertura_nucleo * 10.0

        # Si el tema tiene varias palabras, evita mezclar secciones de otro padecimiento
        # que solo coincidan por una palabra genérica.
        if len(_tokens_tema(tema)) >= 2 and cobertura_tema < 0.5:
            score -= 6.0
        if len(_tokens_tema(tema)) >= 2 and any(p in titulo_n for p in ["tratamiento", "diagnostico", "diagnóstico", "manifestaciones", "complicaciones"]) and cobertura_tema == 0:
            score -= 8.0
        if _tokens_nucleo_tema(tema) and cobertura_nucleo == 0:
            score -= 18.0
        elif _tokens_nucleo_tema(tema) and cobertura_nucleo < 0.5:
            score -= 7.0
        if _tokens_nucleo_tema(tema) and any(p in titulo_n for p in ["tratamiento", "diagnostico", "diagnóstico", "manifestaciones", "complicaciones", "farmacologico", "farmacológico"]) and cobertura_nucleo == 0:
            score -= 14.0
        if score > mejor_score:
            mejor_score = score
            mejor = cita
    return mejor or {}


def _linea_seccion(titulo: str, cita: Dict, tema: str, patrones: List[str]) -> str:
    if not cita:
        return ""
    contenido = _resumen_puntual(cita.get("texto", ""), tema, patrones)
    if not contenido:
        return ""
    return f"{titulo}: {contenido}"


def _armar_respuesta_enfermedad(pregunta: str, citas: List[Dict]) -> Tuple[str, str]:
    tema = _extraer_tema_principal(pregunta)
    grupos_objetivo = _grupos_objetivo_desde_pregunta(pregunta)
    intencion = detectar_intencion(pregunta)
    cita_def = _seleccionar_cita_para_grupo(citas, ["definicion"], tema)
    cita_sint = _seleccionar_cita_para_grupo(citas, ["sintomas"], tema)
    cita_pruebas = _seleccionar_cita_para_grupo(citas, ["pruebas", "asociacion"], tema)
    cita_trat = _seleccionar_cita_para_grupo(citas, ["tratamiento"], tema)
    cita_diag = _seleccionar_cita_para_grupo(citas, ["asociacion"], tema)
    cita_comp = _seleccionar_cita_para_grupo(citas, ["complicaciones", "alarma"], tema)

    if grupos_objetivo == ["tratamiento"]:
        if cita_trat:
            contenido = _frases_relevantes(
                cita_trat.get("texto", ""),
                tema=tema,
                patrones=["tratamiento", "manejo", "terapia", "colecistectomia", "colecistectomía", "sintomaticos", "sintomáticos"],
                max_frases=2,
            )
            linea = f"Tratamiento o manejo: {contenido}" if contenido else ""
        else:
            linea = ""
        if not linea:
            linea = _respuesta_directa_desde_citas(citas[:2])
        observ = []
        if cita_trat:
            observ.append("La respuesta se enfocó solo en tratamiento, como pediste.")
        else:
            observ.append("No recuperé una sección de tratamiento lo bastante clara y devolví el mejor fragmento disponible.")
        return linea, " ".join(observ)

    if grupos_objetivo == ["sintomas"]:
        linea = _linea_seccion("Signos y síntomas", cita_sint, tema, ["signos", "sintomas", "manifestaciones", "dolor"])
        if not linea:
            linea = _respuesta_directa_desde_citas(citas[:2])
        return linea, "La respuesta se enfocó solo en signos y síntomas, como pediste."

    if grupos_objetivo == ["complicaciones", "alarma"]:
        linea = _linea_seccion("Complicaciones o alarma", cita_comp, tema, ["complicaciones", "grave", "sangrado", "alarma"])
        if not linea:
            linea = _respuesta_directa_desde_citas(citas[:2])
        return linea, "La respuesta se enfocó solo en complicaciones o signos de alarma, como pediste."

    if grupos_objetivo == ["asociacion", "pruebas"]:
        lineas = []
        for linea in [
            _linea_seccion("Pruebas o estudios", cita_pruebas, tema, ["pruebas", "laboratorio", "gabinete", "endoscopia", "biopsia"]),
            _linea_seccion("Diagnóstico o asociación", cita_diag, tema, ["diagnostico", "etiologia", "causa", "asociado"]),
        ]:
            if linea:
                lineas.append(linea)
        if not lineas:
            lineas.append(_respuesta_directa_desde_citas(citas[:2]))
        return "\n".join(lineas), "La respuesta se enfocó en diagnóstico y estudios, como pediste."

    if grupos_objetivo == ["composicion", "presentacion"]:
        cita_comp = _seleccionar_cita_para_grupo(citas, ["composicion"], tema)
        cita_pres = _seleccionar_cita_para_grupo(citas, ["presentacion"], tema)
        lineas = []
        if cita_comp:
            lineas.append(_linea_seccion("Materiales, componentes o ingredientes", cita_comp, tema, ["materiales", "componentes", "ingredientes", "partes", "herramientas"]))
        if cita_pres:
            lineas.append(_linea_seccion("Presentación, medidas o especificaciones", cita_pres, tema, ["presentacion", "formato", "medidas", "dimensiones", "capacidad", "especificaciones"]))
        if not lineas:
            lineas.append(_respuesta_directa_desde_citas(citas[:2]))
        return "\n".join(lineas), "La respuesta se enfocó en materiales, componentes o especificaciones, como pediste."

    if not grupos_objetivo and intencion in {"informacion", "definicion", "general"}:
        citas_tema = _citas_centradas_en_tema(tema, citas, limite=3)
        bloques = []
        if cita_def and _cobertura_nucleo_tema(tema, cita_def.get("texto", ""), cita_def.get("titulo_seccion", "")) > 0:
            bloques.append(_linea_seccion("Resumen general", cita_def, tema, ["definicion", "es", "consiste", "calculos", "cálculos", "biliares"]))
        if not bloques and citas_tema:
            bloques.append(f"Resumen general: {_frases_relevantes(citas_tema[0].get('texto', ''), tema=tema, patrones=['definicion', 'es', 'calculos', 'cálculos', 'biliares'], max_frases=2)}")
        if cita_sint and _cobertura_nucleo_tema(tema, cita_sint.get("texto", ""), cita_sint.get("titulo_seccion", "")) > 0:
            bloques.append(_linea_seccion("Manifestaciones", cita_sint, tema, ["signos", "sintomas", "manifestaciones", "dolor"]))
        elif len(citas_tema) > 1:
            bloques.append(f"Datos clave: {_frases_relevantes(citas_tema[1].get('texto', ''), tema=tema, patrones=['dolor', 'epigastrio', 'biliar', 'complicaciones'], max_frases=2)}")
        if cita_trat and _cobertura_nucleo_tema(tema, cita_trat.get("texto", ""), cita_trat.get("titulo_seccion", "")) > 0:
            bloques.append(_linea_seccion("Tratamiento o manejo", cita_trat, tema, ["tratamiento", "manejo", "terapia"]))
        bloques = [b for b in bloques if b and not b.endswith(": ")]
        if not bloques:
            bloques.append(_respuesta_directa_desde_citas(citas_tema))
        return "\n".join(bloques), "La respuesta se enfocó en información general del padecimiento."

    bloques = []
    for linea in [
        _linea_seccion("Definición", cita_def, tema, ["definicion", "es", "consiste"]),
        _linea_seccion("Signos y síntomas", cita_sint, tema, ["signos", "sintomas", "manifestaciones", "dolor"]),
        _linea_seccion("Diagnóstico o asociación", cita_diag, tema, ["diagnostico", "etiologia", "causa", "asociado"]),
        _linea_seccion("Pruebas o estudios", cita_pruebas, tema, ["pruebas", "laboratorio", "gabinete", "endoscopia", "biopsia"]),
        _linea_seccion("Tratamiento o manejo", cita_trat, tema, ["tratamiento", "manejo", "terapia", "erradicacion", "erradicación"]),
        _linea_seccion("Complicaciones o alarma", cita_comp, tema, ["complicaciones", "grave", "sangrado", "alarma"]),
    ]:
        if linea:
            bloques.append(linea)

    if not bloques:
        bloques.append(_respuesta_directa_desde_citas(citas[:2]))

    faltantes = []
    if not cita_def:
        faltantes.append("definición")
    if not cita_sint:
        faltantes.append("signos y síntomas")
    if not cita_trat:
        faltantes.append("tratamiento")

    observ = []
    if faltantes:
        observ.append(f"No recuperé con suficiente claridad estas secciones: {', '.join(faltantes)}.")
    else:
        observ.append("Se recuperaron secciones clínicas útiles.")
    observ.append("Si quieres más precisión, pregunta por diagnóstico, complicaciones, tratamiento o signos de alarma.")
    return "\n".join(bloques), " ".join(observ)


def _armar_respuesta_medicamento(pregunta: str, citas: List[Dict]) -> Tuple[str, str]:
    tema = _extraer_tema_principal(pregunta)
    cita_ind = _seleccionar_cita_para_grupo(citas, ["indicaciones", "definicion"], tema)
    cita_dosis = _seleccionar_cita_para_grupo(citas, ["dosis"], tema)
    cita_admin = _seleccionar_cita_para_grupo(citas, ["administracion"], tema)
    cita_contra = _seleccionar_cita_para_grupo(citas, ["contraindicaciones", "riesgos"], tema)
    cita_adversos = _seleccionar_cita_para_grupo(citas, ["efectos_adversos", "riesgos"], tema)

    bloques = []
    for linea in [
        _linea_seccion("Indicaciones o uso", cita_ind, tema, ["indicaciones", "uso", "sirve"]),
        _linea_seccion("Dosis", cita_dosis, tema, ["dosis", "mg", "ml", "cada", "horas"]),
        _linea_seccion("Vía o administración", cita_admin, tema, ["via", "vía", "administracion", "frecuencia", "cada"]),
        _linea_seccion("Contraindicaciones o precauciones", cita_contra, tema, ["contraindicaciones", "precauciones", "interacciones"]),
        _linea_seccion("Efectos adversos o riesgos", cita_adversos, tema, ["reacciones", "efectos adversos", "toxicidad", "sobredosis"]),
    ]:
        if linea:
            bloques.append(linea)

    if not bloques:
        bloques.append(_respuesta_directa_desde_citas(citas[:2]))

    observ = [
        "No extrapoles dosis si falta presentación, concentración, edad o condición clínica."
    ]
    if not cita_dosis:
        observ.append("No apareció una sección de dosis suficientemente clara en la evidencia recuperada.")
    if not cita_contra or not cita_adversos:
        observ.append("Conviene revisar contraindicaciones, interacciones y reacciones adversas en el material fuente.")
    return "\n".join(bloques), " ".join(observ)


def _armar_respuesta_sintomas(pregunta: str, citas: List[Dict]) -> Tuple[str, str]:
    cita_asoc = _seleccionar_cita_para_grupo(citas, ["asociacion", "sintomas", "definicion"])
    cita_manejo = _seleccionar_cita_para_grupo(citas, ["tratamiento", "riesgos"])
    cita_alarma = _seleccionar_cita_para_grupo(citas, ["alarma", "complicaciones"])

    if cita_asoc:
        lineas = [
            f"Asociación más probable: {_resumen_puntual(cita_asoc.get('texto', ''), pregunta, ['diagnostico', 'asociado', 'causa', 'signos', 'sintomas'])}"
        ]
        if cita_manejo:
            lineas.append(f"Dato complementario: {_resumen_puntual(cita_manejo.get('texto', ''), pregunta, ['tratamiento', 'precauciones', 'riesgo'])}")
        if cita_alarma:
            lineas.append(f"Signos de alarma: {_resumen_puntual(cita_alarma.get('texto', ''), pregunta, ['alarma', 'grave', 'sangrado', 'choque'])}")
        respuesta = "\n".join(lineas)
    else:
        respuesta = _respuesta_directa_desde_citas(citas[:2])

    observ = ["La asociación por síntomas no equivale a diagnóstico definitivo; debe confirmarse con contexto y criterios adicionales."]
    return respuesta, " ".join(observ)


def _armar_respuesta_especializada(pregunta: str, citas: List[Dict]) -> Tuple[str, str, str]:
    modo = _detectar_modo_respuesta(pregunta, citas)
    if modo == "enfermedad":
        r1, r2 = _armar_respuesta_enfermedad(pregunta, citas)
    elif modo == "medicamento":
        r1, r2 = _armar_respuesta_medicamento(pregunta, citas)
    elif modo == "sintomas":
        r1, r2 = _armar_respuesta_sintomas(pregunta, citas)
    else:
        r1, r2 = _respuesta_directa_desde_citas(citas), ""
    return modo, r1, r2


def _construir_prompt_preciso(pregunta: str, citas: List[Dict]) -> str:
    contexto = []
    for i, cita in enumerate(citas, start=1):
        contexto.append(
            f"[CITA {i}] Libro: {cita['libro_nombre']} | Página: {cita['pagina']} | Párrafo: {cita['parrafo']}\n"
            f"{cita['texto']}"
        )

    return (
        "Eres TLAMATINI, asistente offline basado en biblioteca documental del usuario.\n"
        "Reglas estrictas:\n"
        "1. Usa solo las citas proporcionadas.\n"
        "2. No inventes nada.\n"
        "3. Si las citas no alcanzan, dilo.\n"
        "4. Responde en español.\n"
        "5. Formato exacto:\n"
        "Respuesta 1:\n"
        "Respuesta 2:\n"
        "Referencias:\n\n"
        f"Pregunta:\n{pregunta}\n\n"
        f"Citas:\n{chr(10).join(contexto)}"
    )


def _consultar_runtime_local_con_citas(pregunta: str, citas: List[Dict]) -> str:
    disponible, _ = runtime_local_esta_disponible()
    if not disponible or not citas:
        return ""
    try:
        proveedor = obtener_local_llm_provider()
        respuesta = proveedor.generate(
            prompt=_construir_prompt_preciso(pregunta, citas),
            system_prompt="Eres TLAMATINI. Responde solo con citas documentales recuperadas.",
            config=LocalLLMConfig(
                route="documents",
                temperature=0.0,
                top_p=0.1,
                max_tokens=640,
            ),
        )
        texto = str(respuesta).strip()
        if not texto:
            return ""
        return texto
    except Exception:
        return ""


def _respuesta_parece_truncada(texto: str) -> bool:
    texto = (texto or "").strip()
    if not texto:
        return False
    texto_l = texto.lower()
    if texto_l.endswith(("respuesta 1:", "respuesta 2:", "referencias:", "fuentes:", "observaciones:")):
        return True
    if texto.endswith((":", ",", ";", "(", "[", "{", "-", " y", " o")):
        return True
    if texto.count("(") != texto.count(")"):
        return True
    if texto.count("[") != texto.count("]"):
        return True
    return False


def _recortar_a_ultimo_cierre(texto: str) -> str:
    texto = " ".join((texto or "").split()).strip()
    if not texto:
        return ""
    cierres = [texto.rfind(sep) for sep in (".", "!", "?", "…")]
    ultimo = max(cierres)
    if ultimo >= 40:
        return texto[: ultimo + 1].strip()
    return texto


def _sanear_respuesta_modelo(texto: str, max_chars: int = 900) -> str:
    texto = (texto or "").replace("\r", "\n").strip()
    if not texto:
        return ""

    lineas = [linea.rstrip() for linea in texto.splitlines()]
    texto = "\n".join(linea for linea in lineas if linea.strip())
    texto = texto.strip()
    if not texto:
        return ""

    if len(texto) > max_chars:
        texto = _recortar_a_ultimo_cierre(texto[:max_chars])

    if _respuesta_parece_truncada(texto):
        texto = _recortar_a_ultimo_cierre(texto)

    if _respuesta_parece_truncada(texto):
        return ""

    return texto.strip()


def _filtrar_citas_para_presentacion(pregunta: str, citas: List[Dict], limite: int = 6) -> List[Dict]:
    tema = _extraer_tema_principal(pregunta)
    grupos_objetivo = _grupos_objetivo_desde_pregunta(pregunta)
    filtradas = []
    for cita in citas:
        score = float(cita.get("score", 0.0) or 0.0)
        cobertura_nucleo = _cobertura_nucleo_tema(tema, cita.get("texto", ""), cita.get("titulo_seccion", ""))
        score_seccion = _score_por_seccion(cita, grupos_objetivo) if grupos_objetivo else 0.0
        if grupos_objetivo and score_seccion <= 0:
            continue
        if grupos_objetivo and cobertura_nucleo == 0:
            continue
        if score < 0:
            continue
        filtradas.append(cita)
    limite_final = 1 if grupos_objetivo and len(grupos_objetivo) == 1 else (4 if grupos_objetivo else limite)
    return filtradas[:limite_final] or citas[:limite]


def _citas_centradas_en_tema(tema: str, citas: List[Dict], limite: int = 3) -> List[Dict]:
    centradas = []
    for cita in citas:
        cobertura_nucleo = _cobertura_nucleo_tema(tema, cita.get("texto", ""), cita.get("titulo_seccion", ""))
        if cobertura_nucleo <= 0:
            continue
        centradas.append(cita)
    return centradas[:limite] or citas[:limite]


def _respuesta_directa_desde_citas(citas: List[Dict]) -> str:
    if not citas:
        return "No encontré evidencia documental suficiente para responder con precisión."

    partes = [_limitar_texto(cita["texto"]) for cita in citas[:2]]
    return " ".join([p for p in partes if p]).strip()


def _respuesta_observaciones(
    pregunta: str,
    resultados: List[Dict],
    citas: List[Dict],
    evidencia_fuerte: bool,
    validacion_cruzada: bool,
    conflicto: bool,
) -> str:
    if not resultados or not citas:
        return "Conviene cargar más material o reformular la pregunta con más contexto específico."

    observaciones = []
    if not evidencia_fuerte:
        observaciones.append("La evidencia es parcial.")
    if conflicto:
        observaciones.append("Hay conflicto entre citas.")
    if _es_pregunta_sensible(pregunta) and not validacion_cruzada:
        observaciones.append("Falta validación cruzada suficiente.")
    elif validacion_cruzada:
        observaciones.append("Hay validación cruzada entre referencias.")

    if len(citas) == 1:
        observaciones.append("Solo se recuperó una cita fuerte.")

    intencion = detectar_intencion(pregunta)
    if intencion in {"dosis", "contraindicaciones", "indicaciones", "tratamiento"}:
        observaciones.append("Verifica presentación, concentración, vía y contexto clínico.")

    if not observaciones:
        observaciones.append("La respuesta está apoyada en las citas más relevantes recuperadas.")

    return " ".join(observaciones)


def responder_consulta_avanzada(pregunta: str, dominio: str = "", subdominio: str = "") -> str:
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return "Respuesta 1:\nDebes escribir una pregunta.\n\nRespuesta 2:\nFormula una consulta concreta.\n\nReferencias:\n- Sin referencias."

    dominio = _normalizar_dominio(dominio)
    subdominio = normalizar_texto(subdominio)
    resultados = _buscar_con_haystack(pregunta=pregunta, dominio=dominio, subdominio=subdominio, limite=max(LIMITE_RESULTADOS * 2, 12))
    if not resultados:
        resultados = _buscar_resultados_priorizados(pregunta=pregunta, dominio=dominio, subdominio=subdominio)
    resultados = _expandir_resultados_por_continuidad(pregunta, resultados)
    citas = _extraer_citas_de_resultados(pregunta, resultados)
    evidencia_fuerte = _evidencia_es_fuerte(pregunta, resultados, citas)
    validacion_cruzada = _hay_validacion_cruzada(pregunta, citas)
    conflicto = _detectar_conflicto_entre_citas(citas)
    pregunta_sensible = _es_pregunta_sensible(pregunta)
    modo_respuesta, respuesta_estructurada_1, respuesta_estructurada_2 = _armar_respuesta_especializada(pregunta, citas)

    registrar_log(
        "consulta",
        f"Consulta documental avanzada: {pregunta} | intencion={detectar_intencion(pregunta)} | modo={modo_respuesta} | resultados={len(resultados)} | citas={len(citas)} | validacion_cruzada={validacion_cruzada}",
        "consulta",
    )

    if not resultados or not citas:
        return (
            "Respuesta 1:\n"
            "No encontré evidencia documental suficiente en la biblioteca cargada para responder con precisión.\n\n"
            "Respuesta 2:\n"
            "Carga más libros o reformula la consulta con términos más específicos.\n\n"
            "Referencias:\n"
            "- Sin coincidencias documentales suficientes."
        )

    if conflicto:
        respuesta_1 = "No puedo darte una respuesta única con seguridad porque las citas recuperadas muestran señales de conflicto o ambigüedad."
    elif pregunta_sensible and not validacion_cruzada:
        if respuesta_estructurada_1:
            respuesta_1 = "La evidencia no alcanza seguridad alta, pero esto es lo mejor sustentado que recuperé:\n" + respuesta_estructurada_1
        else:
            respuesta_1 = "No puedo responder con seguridad alta porque la pregunta es sensible y no encontré suficiente validación cruzada entre fuentes."
    elif not evidencia_fuerte:
        if respuesta_estructurada_1:
            respuesta_1 = "La evidencia es parcial, pero esto es lo más sustentado que recuperé:\n" + respuesta_estructurada_1
        else:
            respuesta_1 = "No puedo responder con seguridad plena usando solo la evidencia recuperada."
    else:
        respuesta_1 = respuesta_estructurada_1 or _respuesta_directa_desde_citas(citas)

    respuesta_2 = _respuesta_observaciones(
        pregunta,
        resultados,
        citas,
        evidencia_fuerte,
        validacion_cruzada,
        conflicto,
    )
    if respuesta_estructurada_2:
        respuesta_2 = f"{respuesta_estructurada_2} {respuesta_2}".strip()
    respuesta_modelo = ""
    if evidencia_fuerte and (validacion_cruzada or not pregunta_sensible) and not conflicto and modo_respuesta == "general":
        respuesta_modelo = _sanear_respuesta_modelo(
            _consultar_runtime_local_con_citas(pregunta, citas),
            max_chars=1200,
        )

    if respuesta_modelo and "Respuesta 1:" in respuesta_modelo and "Respuesta 2:" in respuesta_modelo and "Referencias:" in respuesta_modelo:
        return respuesta_modelo

    referencias = []
    for cita in citas:
        ref = f"- {cita['libro_nombre']} | página {cita['pagina']} | párrafo {cita['parrafo']}"
        if cita.get("titulo_seccion"):
            ref += f" | sección {cita['titulo_seccion']}"
        referencias.append(ref)

    if respuesta_modelo:
        respuesta_2 = f"{respuesta_2}\n\nSíntesis IA local:\n{respuesta_modelo}"

    return (
        f"Respuesta 1:\n{respuesta_1}\n\n"
        f"Respuesta 2:\n{respuesta_2}\n\n"
        "Referencias:\n"
        + "\n".join(referencias)
    )


def listar_documentos_indexados() -> List[Dict]:
    return listar_libros()


def _formatear_referencias_documentales(citas: List[Dict], limite: int = 6) -> List[str]:
    referencias = []
    vistos = set()
    for cita in citas[:limite]:
        referencia = f"- {cita['libro_nombre']} | página {cita['pagina']}"
        if cita.get("parrafo"):
            referencia += f" | párrafo {cita['parrafo']}"
        if cita.get("titulo_seccion"):
            referencia += f" | sección {cita['titulo_seccion']}"
        if referencia in vistos:
            continue
        vistos.add(referencia)
        referencias.append(referencia)
    return referencias


def _prompt_respuesta_documental(pregunta: str, citas: List[Dict]) -> str:
    contexto = []
    for idx, cita in enumerate(citas[:6], start=1):
        contexto.append(
            f"[Fragmento {idx}] Libro: {cita.get('libro_nombre', '')} | "
            f"Página: {cita.get('pagina', 0)} | "
            f"Sección: {cita.get('titulo_seccion', '') or 'sin sección'}\n"
            f"{cita.get('texto', '').strip()}"
        )
    return (
        "Responde en español usando solo los fragmentos documentales proporcionados.\n"
        "No inventes hechos, citas, páginas, nombres ni relaciones causales.\n"
        "Si los fragmentos no bastan, dilo claramente.\n"
        "No afirmes haber usado otras fuentes.\n"
        "No repitas la pregunta.\n"
        "No uses introducciones, relleno ni conclusiones largas.\n"
        "Formato obligatorio:\n"
        "Respuesta breve:\n"
        "- Una respuesta directa de 2 a 4 oraciones cortas.\n"
        "Límites:\n"
        "- Una sola línea indicando incertidumbre, conflicto o alcance si aplica.\n"
        "Termina con una oración completa.\n\n"
        f"Pregunta: {pregunta.strip()}\n\n"
        f"Fragmentos:\n{chr(10).join(contexto)}"
    )


def _generar_sintesis_documental_local(pregunta: str, citas: List[Dict]) -> str:
    proveedor = obtener_local_llm_provider()
    disponible, _ = proveedor.is_available()
    if not disponible or not citas:
        return ""
    try:
        respuesta = proveedor.generate(
            prompt=_prompt_respuesta_documental(pregunta, citas),
            system_prompt="Eres TLAMATINI. Sintetiza solo con evidencia documental recuperada.",
            config=LocalLLMConfig(route="documents", temperature=0.0, top_p=0.1, max_tokens=640),
        ).strip()
        return _sanear_respuesta_modelo(respuesta, max_chars=1000)
    except Exception:
        return ""


def _formatear_respuesta_documental(
    etiqueta: str,
    pregunta: str,
    clasificacion: Dict,
    resultados: List[Dict],
    citas: List[Dict],
    respuesta_base: str,
    respuesta_modelo: str = "",
) -> str:
    if not resultados or not citas:
        return (
            f"[{etiqueta}]\n\n"
            f"No encontré evidencia documental suficiente en {clasificacion.get('library', 'la biblioteca seleccionada')}.\n\n"
            "Fuentes:\n"
            "- Sin coincidencias documentales suficientes."
        )

    referencias = _formatear_referencias_documentales(_filtrar_citas_para_presentacion(pregunta, citas))
    if etiqueta == "Respuesta híbrida: IA local + documentos":
        sintesis = respuesta_modelo.strip() or "No hubo síntesis adicional suficientemente sustentada."
        return (
            f"[{etiqueta}]\n\n"
            "Síntesis general:\n"
            f"{sintesis}\n\n"
            "Sustento documental:\n"
            f"{respuesta_base.strip()}\n\n"
            "Fuentes:\n"
            + "\n".join(referencias)
        )

    cuerpo = respuesta_modelo.strip() or respuesta_base.strip()
    return (
        f"[{etiqueta}]\n\n"
        f"{cuerpo}\n\n"
        "Fuentes:\n"
        + "\n".join(referencias)
    )


def buscar_resultados_documentales_por_tema(
    pregunta: str,
    dominio: str = "",
    subdominio: str = "",
    limite: int = 8,
) -> Dict:
    consulta = _consulta_desde_palabras_clave(pregunta)
    pregunta_busqueda = str(consulta.get("consulta_busqueda") or pregunta)
    clasificacion = clasificar_tema_consulta(
        pregunta_busqueda,
        dominio_explicito=dominio,
        usar_fallback_llm=True,
    )
    salida = buscar_en_biblioteca_tematica(
        pregunta=pregunta_busqueda,
        biblioteca=clasificacion["library"],
        subdominio=subdominio,
        limite=limite,
    )
    salida["classification"] = clasificacion
    salida["search_query"] = pregunta_busqueda
    salida["search_topic"] = str(consulta.get("tema") or "")
    salida["search_groups"] = list(consulta.get("grupos") or [])
    return salida


def responder_consulta_documental_tematica(
    pregunta: str,
    dominio: str = "",
    subdominio: str = "",
    modo: str = "documental",
) -> str:
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return "[Respuesta ampliada basada en documentos]\n\nDebes escribir una pregunta."

    salida_tematica = buscar_resultados_documentales_por_tema(
        pregunta=pregunta,
        dominio=dominio,
        subdominio=subdominio,
        limite=10,
    )
    clasificacion = salida_tematica.get("classification", {})
    resultados = salida_tematica.get("results", [])
    citas = _extraer_citas_de_resultados(pregunta, resultados, limite=6)
    modo_respuesta, respuesta_estructurada_1, respuesta_estructurada_2 = _armar_respuesta_especializada(pregunta, citas)

    if respuesta_estructurada_2:
        respuesta_base = f"{respuesta_estructurada_1}\n\nObservaciones:\n{respuesta_estructurada_2}".strip()
    else:
        respuesta_base = (respuesta_estructurada_1 or _respuesta_directa_desde_citas(citas)).strip()

    if not resultados or not citas:
        registrar_log(
            "consulta",
            (
                f"Consulta documental temática sin evidencia: {pregunta} | "
                f"theme={clasificacion.get('theme', 'general')} | library={clasificacion.get('library', 'biblioteca_general')}"
            ),
            "consulta",
        )
        return _formatear_respuesta_documental(
            etiqueta="Respuesta ampliada basada en documentos",
            pregunta=pregunta,
            clasificacion=clasificacion,
            resultados=resultados,
            citas=citas,
            respuesta_base=respuesta_base,
        )

    modo_final = normalizar_texto(modo)
    if modo_final not in {"documental", "hibrido", "híbrido", "hybrid", "auto"}:
        modo_final = "documental"

    usar_hibrida = modo_final in {"hibrido", "híbrido", "hybrid"}
    if modo_final == "auto":
        usar_hibrida = modo_respuesta == "general" and len(citas) >= 2

    respuesta_modelo = _generar_sintesis_documental_local(pregunta, citas) if usar_hibrida else ""
    etiqueta = "Respuesta híbrida: IA local + documentos" if usar_hibrida else "Respuesta ampliada basada en documentos"

    registrar_log(
        "consulta",
        (
            f"Consulta documental temática: {pregunta} | modo={modo_final} | etiqueta={etiqueta} | "
            f"theme={clasificacion.get('theme', 'general')} | library={clasificacion.get('library', 'biblioteca_general')} | "
            f"resultados={len(resultados)} | citas={len(citas)}"
        ),
        "consulta",
    )

    return _formatear_respuesta_documental(
        etiqueta=etiqueta,
        pregunta=pregunta,
        clasificacion=clasificacion,
        resultados=resultados,
        citas=citas,
        respuesta_base=respuesta_base,
        respuesta_modelo=respuesta_modelo,
    )


def probar_busqueda_consulta(pregunta: str, dominio: str = "", subdominio: str = "") -> str:
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return "Escribe una pregunta para probar la búsqueda."

    dominio = _normalizar_dominio(dominio)
    subdominio = normalizar_texto(subdominio)
    consulta = _consulta_desde_palabras_clave(pregunta)
    pregunta_busqueda = str(consulta.get("consulta_busqueda") or pregunta)
    salida_tematica = buscar_resultados_documentales_por_tema(
        pregunta=pregunta,
        dominio=dominio,
        subdominio=subdominio,
        limite=8,
    )
    clasificacion = salida_tematica.get("classification", {})
    dominios_inferidos = _inferir_dominios_desde_pregunta(pregunta_busqueda)
    resultados = _buscar_con_haystack(pregunta=pregunta_busqueda, dominio=dominio, subdominio=subdominio, limite=max(LIMITE_RESULTADOS * 2, 12))
    backend = "haystack"
    if not resultados:
        resultados = _buscar_resultados_priorizados(pregunta=pregunta_busqueda, dominio=dominio, subdominio=subdominio)
        backend = "sqlite"
    resultados = _expandir_resultados_por_continuidad(pregunta_busqueda, resultados)
    citas = _extraer_citas_de_resultados(pregunta, resultados, limite=6)

    lineas = [
        "MODO DE PRUEBAS DE BÚSQUEDA",
        f"Pregunta: {pregunta}",
        f"Tema extraído: {consulta.get('tema', '') or 'sin extraer'}",
        f"Consulta normalizada: {pregunta_busqueda}",
        f"Grupos objetivo: {', '.join(consulta.get('grupos', [])) or 'general'}",
        f"Backend activo: {backend}",
        f"Dominio manual: {dominio or 'sin filtro'}",
        f"Subdominio manual: {subdominio or 'sin filtro'}",
        f"Tema detectado: {clasificacion.get('theme', 'general')}",
        f"Biblioteca temática: {clasificacion.get('library', 'biblioteca_general')}",
        f"Confianza temática: {clasificacion.get('confidence', 0.0)}",
        f"Dominios inferidos: {', '.join(dominios_inferidos) if dominios_inferidos else 'ninguno'}",
        f"Documentos en biblioteca temática: {salida_tematica.get('document_count', 0)}",
        f"Resultados en biblioteca temática: {len(salida_tematica.get('results', []))}",
        f"Resultados recuperados: {len(resultados)}",
        f"Citas útiles: {len(citas)}",
        "",
        "CITAS PRIORIZADAS:",
    ]

    if not citas:
        lineas.append("- No se recuperaron citas útiles para esta pregunta.")
        return "\n".join(lineas)

    for idx, cita in enumerate(citas, start=1):
        lineas.extend(
            [
                f"{idx}. {cita.get('titulo_seccion') or 'Fragmento relevante'}",
                f"   {_limitar_texto(cita.get('texto', ''), 520)}",
            ]
        )

    if resultados:
        lineas.extend(["", "FRAGMENTOS RECUPERADOS:"])
        for idx, resultado in enumerate(resultados[:8], start=1):
            lineas.extend(
                [
                    f"{idx}. {resultado.get('titulo_seccion') or 'Fragmento recuperado'}",
                    f"   {_limitar_texto(resultado.get('snippet') or resultado.get('texto', ''), 360)}",
                ]
            )

    if salida_tematica.get("results"):
        lineas.extend(["", "FRAGMENTOS TEMÁTICOS:"])
        for idx, resultado in enumerate(salida_tematica.get("results", [])[:8], start=1):
            lineas.extend(
                [
                    f"{idx}. {resultado.get('libro_nombre', 'Documento')} / pág. {resultado.get('pagina', 0)}",
                    f"   {_limitar_texto(resultado.get('snippet') or resultado.get('texto', ''), 360)}",
                ]
            )

    return "\n".join(lineas)
