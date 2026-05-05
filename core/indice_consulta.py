import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.memoria import RUTA_BASE_DATOS


RUTA_DB_CONSULTA = RUTA_BASE_DATOS / "consulta.db"


STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "y", "o", "en", "un", "una", "unos", "unas",
    "que", "qué", "como", "cómo", "cual", "cuál", "cuanto", "cuántos", "cuanta", "cuántas",
    "es", "son", "se", "al", "por", "para", "con", "sin", "lo", "le", "les", "su", "sus",
    "a", "u", "e", "sobre", "entre", "desde", "hasta"
}


PALABRAS_INTENCION = {
    "informacion": {
        "informacion", "información", "generalidades", "resumen", "acerca de", "sobre",
        "explicacion", "explicación", "descripcion general", "descripción general",
        "panorama general", "vision general", "visión general", "datos generales",
    },
    "definicion": {
        "que es", "qué es", "definicion", "definición", "define", "concepto",
        "descripcion", "descripción", "que significa", "qué significa", "identificar",
        "identificacion", "identificación",
    },
    "dosis": {
        "dosis", "dosificacion", "dosificación", "posologia", "posología",
        "cantidad", "cuanto usar", "cuánto usar", "cuanto aplicar", "cuánto aplicar",
        "proporcion", "proporción", "mezcla", "dilucion", "dilución", "medida",
        "medidas", "concentracion", "concentración", "frecuencia",
    },
    "contraindicaciones": {
        "contraindicaciones", "contraindicacion", "contraindicación", "cuando no usar",
        "cuando no aplicar", "cuándo no usar", "cuándo no aplicar", "restricciones",
        "prohibido", "no usar", "no aplicar",
    },
    "indicaciones": {
        "indicaciones", "indicacion", "indicación", "para que sirve", "para qué sirve",
        "uso", "usos", "utilidad", "aplicacion", "aplicación", "sirve para",
        "cuando usar", "cuándo usar",
    },
    "tratamiento": {
        "tratamiento", "manejo", "terapia", "procedimiento", "procedimientos",
        "pasos", "paso a paso", "como hacerlo", "cómo hacerlo", "como se hace",
        "cómo se hace", "como preparar", "cómo preparar", "preparacion", "preparación",
        "como reparar", "cómo reparar", "reparacion", "reparación", "como instalar",
        "cómo instalar", "instalacion", "instalación", "mantenimiento", "servicio",
        "ajuste", "calibracion", "calibración", "armado", "montaje", "construccion",
        "construcción", "siembra", "sembrar", "cultivo", "cultivar", "poda",
        "injerto", "riego", "fertilizacion", "fertilización", "control", "manejo integrado",
    },
    "clasificacion": {
        "clasificacion", "clasificación", "tipos", "clases", "variedades", "categorias",
        "categorías", "opciones", "modalidades", "versiones",
    },
    "presentacion": {
        "presentacion", "presentación", "presentaciones", "formato", "formatos",
        "medidas", "dimensiones", "tamano", "tamaño", "capacidad", "capacidades",
        "especificaciones", "especificación", "especificaciones tecnicas", "especificaciones técnicas",
    },
    "composicion": {
        "composicion", "composición", "formula", "fórmula", "materiales", "material",
        "ingredientes", "ingrediente", "componentes", "componente", "partes",
        "refacciones", "insumos", "herramientas", "herramienta", "equipo", "equipos",
    },
    "interacciones": {
        "interacciones", "interaccion", "interacción", "compatibilidad", "compatible",
        "incompatible", "mezclar con", "combinar con",
    },
    "precauciones": {
        "precauciones", "precaucion", "precaución", "seguridad", "riesgos",
        "peligros", "advertencias", "cuidados", "proteccion", "protección",
        "equipo de proteccion", "equipo de protección", "epp", "prevencion", "prevención",
    },
    "etiologia": {
        "etiologia", "etiología", "causas", "causa", "origen", "motivo", "por que pasa",
        "por qué pasa", "por que ocurre", "por qué ocurre",
    },
    "diagnostico": {
        "diagnostico", "diagnóstico", "como diagnosticar", "cómo diagnosticar",
        "falla", "falla comun", "falla común", "averia", "avería", "problema",
        "problemas", "revision", "revisión", "inspeccion", "inspección", "pruebas",
        "verificacion", "verificación", "detectar", "identificar falla", "solucion de fallas",
    },
}


def quitar_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    )


def normalizar_texto(texto: str) -> str:
    texto = texto or ""
    texto = texto.replace("\r", "\n")
    texto = texto.replace("\t", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip().lower()


def normalizar_sin_acentos(texto: str) -> str:
    return normalizar_texto(quitar_acentos(texto))


def limpiar_texto_extraido(texto: str) -> str:
    if not texto:
        return ""

    t = texto.replace("\r", "\n")

    # Reparar cortes por guion al salto de línea
    t = re.sub(r"([A-Za-zÁÉÍÓÚáéíóúÑñ])-\n([A-Za-zÁÉÍÓÚáéíóúÑñ])", r"\1\2", t)

    # Convertir saltos simples a espacio
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)

    # Mantener separación entre párrafos
    t = re.sub(r"\n{2,}", "\n\n", t)

    # Quitar símbolos basura comunes
    t = re.sub(r"[\[\]{}<>|¦]+", " ", t)

    # Reparar espacios
    t = re.sub(r"\s+", " ", t)

    # Reparar signos pegados
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"([,.;:!?])([A-Za-zÁÉÍÓÚáéíóúÑñ])", r"\1 \2", t)

    return t.strip()


def tokenizar(texto: str) -> List[str]:
    return re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\+\-]+", normalizar_texto(texto))


def tokens_significativos(texto: str) -> List[str]:
    return [t for t in tokenizar(texto) if t not in STOPWORDS and len(t) > 2]


def detectar_intencion(pregunta: str) -> str:
    p = normalizar_sin_acentos(pregunta)

    for nombre, patrones in PALABRAS_INTENCION.items():
        for patron in patrones:
            if normalizar_sin_acentos(patron) in p:
                return nombre

    return "general"


def asegurar_db() -> None:
    RUTA_DB_CONSULTA.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(RUTA_DB_CONSULTA) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS fragmentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                libro_id TEXT NOT NULL,
                libro_nombre TEXT NOT NULL,
                dominio TEXT NOT NULL,
                subdominio TEXT NOT NULL,
                pagina INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                titulo_seccion TEXT NOT NULL,
                texto TEXT NOT NULL,
                texto_normalizado TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fragmentos_fts
            USING fts5(
                texto_normalizado,
                content='fragmentos',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            )
        """)

        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS fragmentos_ai AFTER INSERT ON fragmentos BEGIN
                INSERT INTO fragmentos_fts(rowid, texto_normalizado)
                VALUES (new.id, new.texto_normalizado);
            END;

            CREATE TRIGGER IF NOT EXISTS fragmentos_ad AFTER DELETE ON fragmentos BEGIN
                INSERT INTO fragmentos_fts(fragmentos_fts, rowid, texto_normalizado)
                VALUES('delete', old.id, old.texto_normalizado);
            END;

            CREATE TRIGGER IF NOT EXISTS fragmentos_au AFTER UPDATE ON fragmentos BEGIN
                INSERT INTO fragmentos_fts(fragmentos_fts, rowid, texto_normalizado)
                VALUES('delete', old.id, old.texto_normalizado);
                INSERT INTO fragmentos_fts(rowid, texto_normalizado)
                VALUES (new.id, new.texto_normalizado);
            END;
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragmentos_libro_id ON fragmentos(libro_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragmentos_dominio ON fragmentos(dominio)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragmentos_subdominio ON fragmentos(subdominio)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragmentos_pagina ON fragmentos(pagina)")
        conn.commit()


def reiniciar_indice_consulta() -> None:
    if RUTA_DB_CONSULTA.exists():
        RUTA_DB_CONSULTA.unlink()
    asegurar_db()


def partir_en_frases(texto: str) -> List[str]:
    texto = limpiar_texto_extraido(texto)
    if not texto:
        return []
    frases = re.split(r'(?<=[\.\!\?\:;])\s+', texto)
    return [f.strip() for f in frases if f.strip()]


def es_titulo_probable(texto: str) -> bool:
    t = limpiar_texto_extraido(texto)
    if not t:
        return False

    t_sin = normalizar_sin_acentos(t)

    if len(t.split()) <= 10 and len(t) <= 120:
        if any(x in t_sin for grupo in PALABRAS_INTENCION.values() for x in map(normalizar_sin_acentos, grupo)):
            return True

    if t == t.upper() and len(t.split()) <= 12:
        return True

    return False


def fragmentar_texto(texto: str, max_chars: int = 1000) -> List[str]:
    texto = limpiar_texto_extraido(texto)
    if not texto:
        return []

    frases = partir_en_frases(texto)
    if not frases:
        return [texto[:max_chars]]

    bloques = []
    actual = ""

    for frase in frases:
        if len(actual) + len(frase) + 1 <= max_chars:
            actual = f"{actual} {frase}".strip()
        else:
            if actual:
                bloques.append(actual)
            actual = frase

    if actual:
        bloques.append(actual)

    return bloques


def detectar_titulo_desde_bloque(bloque: str) -> str:
    frases = partir_en_frases(bloque[:350])
    for frase in frases[:3]:
        if es_titulo_probable(frase):
            return frase[:140]
    return ""


def reindexar_libro(libro: Dict, paginas: List[Dict]) -> int:
    asegurar_db()

    libro_id = libro["id"]
    libro_nombre = libro["nombre"]
    dominio = normalizar_texto(libro.get("dominio", ""))
    subdominio = normalizar_texto(libro.get("subdominio", ""))

    total = 0

    with sqlite3.connect(RUTA_DB_CONSULTA) as conn:
        conn.execute("DELETE FROM fragmentos WHERE libro_id = ?", (libro_id,))

        for pagina in paginas:
            numero_pagina = int(pagina.get("pagina", 0))
            texto_pagina = pagina.get("texto", "") or ""
            secciones = pagina.get("secciones", {}) or {}

            # Indexar secciones primero, con prioridad semántica más fuerte
            for titulo_seccion, texto_seccion in secciones.items():
                texto_seccion = limpiar_texto_extraido(texto_seccion)
                if not texto_seccion:
                    continue

                for bloque in fragmentar_texto(texto_seccion):
                    conn.execute("""
                        INSERT INTO fragmentos (
                            libro_id, libro_nombre, dominio, subdominio,
                            pagina, tipo, titulo_seccion, texto, texto_normalizado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        libro_id,
                        libro_nombre,
                        dominio,
                        subdominio,
                        numero_pagina,
                        "seccion",
                        str(titulo_seccion).strip(),
                        bloque,
                        normalizar_sin_acentos(bloque),
                    ))
                    total += 1

            # Indexar página completa fragmentada
            texto_pagina = limpiar_texto_extraido(texto_pagina)
            if texto_pagina:
                for bloque in fragmentar_texto(texto_pagina):
                    titulo_detectado = detectar_titulo_desde_bloque(bloque)
                    conn.execute("""
                        INSERT INTO fragmentos (
                            libro_id, libro_nombre, dominio, subdominio,
                            pagina, tipo, titulo_seccion, texto, texto_normalizado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        libro_id,
                        libro_nombre,
                        dominio,
                        subdominio,
                        numero_pagina,
                        "pagina",
                        titulo_detectado,
                        bloque,
                        normalizar_sin_acentos(bloque),
                    ))
                    total += 1

        conn.commit()

    return total


def construir_queries(pregunta: str) -> List[str]:
    p = normalizar_sin_acentos(pregunta)
    if not p:
        return []

    queries = []

    if len(p.split()) >= 2:
        queries.append(f'"{p}"')

    toks = tokens_significativos(p)
    if toks:
        queries.append(" OR ".join(toks))

    return list(dict.fromkeys(queries))


def generar_snippet(texto: str, pregunta: str, ventana: int = 180) -> str:
    texto = limpiar_texto_extraido(texto)
    if not texto:
        return ""

    texto_n = normalizar_sin_acentos(texto)
    pregunta_n = normalizar_sin_acentos(pregunta)

    pos = texto_n.find(pregunta_n)

    if pos == -1:
        for tok in tokens_significativos(pregunta):
            tok_n = normalizar_sin_acentos(tok)
            pos = texto_n.find(tok_n)
            if pos != -1:
                break

    if pos == -1:
        frases = partir_en_frases(texto)
        return frases[0][:ventana] if frases else texto[:ventana]

    inicio = max(0, pos - ventana)
    fin = min(len(texto), pos + ventana)

    snippet = texto[inicio:fin].strip()

    if inicio > 0:
        snippet = "..." + snippet
    if fin < len(texto):
        snippet = snippet + "..."

    return snippet


def puntuar_resultado(pregunta: str, fila: sqlite3.Row) -> float:
    score = float(fila["bm25_score"])

    texto = fila["texto"] or ""
    titulo = fila["titulo_seccion"] or ""
    tipo = fila["tipo"] or ""

    texto_n = normalizar_sin_acentos(texto)
    titulo_n = normalizar_sin_acentos(titulo)
    pregunta_n = normalizar_sin_acentos(pregunta)
    tokens = tokens_significativos(pregunta)
    intencion = detectar_intencion(pregunta)

    # Mejor si es coincidencia exacta completa
    if pregunta_n and pregunta_n in texto_n:
        score -= 6.0

    if pregunta_n and pregunta_n in titulo_n:
        score -= 5.0

    # Mejor si es sección
    if tipo == "seccion":
        score -= 1.5

    # Coincidencias por tokens
    coinc = sum(1 for t in tokens if normalizar_sin_acentos(t) in texto_n)
    score -= coinc * 0.35

    # Premiar respuestas de definición
    if intencion == "definicion":
        if any(x in texto_n for x in [" es ", " consiste en ", " se define ", " se considera "]):
            score -= 3.5
        if any(x in titulo_n for x in ["definicion", "definición", "concepto"]):
            score -= 2.5

    # Premiar intención-sección
    if intencion == "dosis" and any(x in titulo_n for x in ["dosis", "dosificacion", "dosificación", "posologia", "posología"]):
        score -= 4.0

    if intencion == "contraindicaciones" and "contraindic" in titulo_n:
        score -= 4.0

    if intencion == "indicaciones" and "indicacion" in titulo_n:
        score -= 4.0

    if intencion == "tratamiento" and "tratamiento" in titulo_n:
        score -= 4.0

    if intencion == "clasificacion" and "clasificacion" in titulo_n:
        score -= 4.0

    if intencion == "presentacion" and "presentacion" in titulo_n:
        score -= 4.0

    if intencion == "composicion" and any(x in titulo_n for x in ["composicion", "formula"]):
        score -= 4.0

    # Castigar bloques excesivamente enumerativos si la intención es definición
    if intencion == "definicion":
        mayus = sum(1 for ch in texto if ch.isupper())
        if mayus > 45 and len(texto) < 900:
            score += 1.2

    return score


def buscar_fragmentos(
    pregunta: str,
    dominio: str = "",
    subdominio: str = "",
    limite: int = 8
) -> List[Dict]:
    asegurar_db()

    dominio = normalizar_texto(dominio)
    subdominio = normalizar_texto(subdominio)

    if dominio in ("", "todos"):
        dominio = ""

    if subdominio in ("", "general", "todos"):
        subdominio = ""

    resultados: List[Dict] = []
    queries = construir_queries(pregunta)

    if not queries:
        return []

    with sqlite3.connect(RUTA_DB_CONSULTA) as conn:
        conn.row_factory = sqlite3.Row

        for q in queries:
            sql = """
                SELECT
                    f.id,
                    f.libro_id,
                    f.libro_nombre,
                    f.dominio,
                    f.subdominio,
                    f.pagina,
                    f.tipo,
                    f.titulo_seccion,
                    f.texto,
                    f.texto_normalizado,
                    bm25(fragmentos_fts) AS bm25_score
                FROM fragmentos_fts
                JOIN fragmentos f ON f.id = fragmentos_fts.rowid
                WHERE fragmentos_fts MATCH ?
            """
            params: List = [q]

            if dominio:
                sql += " AND f.dominio = ?"
                params.append(dominio)

            if subdominio:
                sql += " AND f.subdominio = ?"
                params.append(subdominio)

            sql += " ORDER BY bm25_score LIMIT ?"
            params.append(max(30, limite * 6))

            filas = conn.execute(sql, params).fetchall()

            for fila in filas:
                item = dict(fila)
                item["score_final"] = puntuar_resultado(pregunta, fila)
                item["snippet"] = generar_snippet(item["texto"], pregunta)
                resultados.append(item)

    # Quitar duplicados y ordenar
    unicos = []
    vistos = set()

    for r in sorted(resultados, key=lambda x: x["score_final"]):
        clave = (
            r["libro_id"],
            r["pagina"],
            (r.get("titulo_seccion") or "").strip().lower(),
            (r.get("texto_normalizado") or "")[:220]
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(r)
        if len(unicos) >= limite:
            break

    return unicos
