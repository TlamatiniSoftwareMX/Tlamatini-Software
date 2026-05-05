import io
import os
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from statistics import median
from typing import Dict, List, Tuple, Optional

from core.clasificador_temas import detectar_temas_en_texto
from core.logs import registrar_log

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None


TESSERACT_RUTA_WINDOWS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

ENCABEZADOS_OBJETIVO = [
    "patologia",
    "patología",
    "definicion",
    "definición",
    "concepto",
    "descripcion",
    "descripción",
    "patogenia",
    "etiologia",
    "etiología",
    "causas",
    "factores de riesgo",
    "cuadro clinico",
    "cuadro clínico",
    "manifestaciones clinicas",
    "manifestaciones clínicas",
    "manifestaciones extraintestinales",
    "manifestaciones extrapulmonares",
    "manifestaciones neurologicas",
    "manifestaciones neurológicas",
    "signos y sintomas",
    "signos y síntomas",
    "sintomas",
    "síntomas",
    "diagnostico",
    "diagnóstico",
    "diagnostico diferencial",
    "diagnóstico diferencial",
    "evaluacion",
    "evaluación",
    "anamnesis",
    "exploracion fisica",
    "exploración física",
    "pruebas diagnosticas",
    "pruebas diagnósticas",
    "pruebas de laboratorio",
    "estudios de laboratorio",
    "estudios complementarios",
    "gabinete",
    "imagen",
    "imagenes",
    "imágenes",
    "radiografia",
    "radiografía",
    "tomografia",
    "tomografía",
    "ultrasonido",
    "ecografia",
    "ecografía",
    "endoscopia",
    "endoscopía",
    "colonoscopia",
    "colonoscopía",
    "sigmoidoscopia",
    "sigmoidoscopía",
    "biopsia",
    "gabinete",
    "tratamiento",
    "tratamiento medico",
    "tratamiento médico",
    "tratamiento farmacologico",
    "tratamiento farmacológico",
    "tratamiento quirurgico",
    "tratamiento quirúrgico",
    "tratamiento de apoyo",
    "manejo inicial",
    "manejo agudo",
    "manejo cronico",
    "manejo crónico",
    "manejo",
    "de apoyo",
    "quirurgico",
    "quirúrgico",
    "complicaciones",
    "pronostico",
    "pronóstico",
    "prevencion",
    "prevención",
    "epidemiologia",
    "epidemiología",
    "fisiopatologia",
    "fisiopatología",
    "factores de riesgo",
    "diagnostico diferencial",
    "diagnóstico diferencial",
    "contraindicaciones",
    "indicaciones",
    "indicaciones terapeuticas",
    "indicaciones terapéuticas",
    "dosis",
    "dosificacion",
    "dosificación",
    "posologia",
    "posología",
    "reacciones adversas",
    "interacciones",
    "interacciones medicamentosas y de otro genero",
    "interacciones medicamentosas y de otro género",
    "precauciones",
    "precauciones generales",
    "precauciones en relacion con efectos de carcinogenesis mutagenesis teratogenesis y sobre la fertilidad",
    "precauciones en relación con efectos de carcinogénesis mutagénesis teratogénesis y sobre la fertilidad",
    "presentacion",
    "presentaciones",
    "almacenamiento",
    "restricciones de uso",
    "restricciones de uso durante el embarazo y la lactancia",
    "embarazo",
    "lactancia",
    "advertencias",
    "administracion",
    "modo de uso",
    "dosis y via de administracion",
    "dosis y vía de administración",
    "farmacocinetica",
    "farmacocinética",
    "farmacodinamia",
    "farmacocinetica y farmacodinamia",
    "farmacocinética y farmacodinamia",
    "composicion",
    "composición",
    "formula",
    "fórmula",
    "uso pediatrico",
    "uso pediátrico",
    "uso geriatrico",
    "uso geriátrico",
    "sobredosis",
    "manifestaciones y manejo de la sobredosificacion o ingesta accidental",
    "manifestaciones y manejo de la sobredosificación o ingesta accidental",
    "leyendas de proteccion",
    "leyendas de protección",
    "leyenda de proteccion",
    "leyenda de protección",
    "hecho en mexico",
    "hecho en méxico",
    "reg no",
    "reg. no",
    "registro",
    "presentacion comercial"
]


def quitar_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def normalizar_texto(texto: str) -> str:
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def normalizar_clave(texto: str) -> str:
    texto = quitar_acentos(texto.lower().strip())
    texto = re.sub(r"[^a-z0-9\s:]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def configurar_tesseract_si_existe() -> None:
    if pytesseract is None:
        return
    if os.path.exists(TESSERACT_RUTA_WINDOWS):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_RUTA_WINDOWS


def texto_pobre(texto: str) -> bool:
    t = normalizar_texto(texto)
    if len(t) < 120:
        return True
    letras = sum(c.isalpha() for c in t)
    if letras < 60:
        return True
    return False


def limpiar_linea(linea: str) -> str:
    return re.sub(r"\s+", " ", linea).strip()


def obtener_headers_normalizados() -> List[str]:
    return [normalizar_clave(x) for x in ENCABEZADOS_OBJETIVO]


def parece_encabezado_textual(linea: str) -> bool:
    original = linea.strip()
    l = normalizar_clave(original)
    if not l:
        return False

    headers = obtener_headers_normalizados()

    if l.rstrip(":") in headers:
        return True

    if l.endswith(":") and l.rstrip(":") in headers:
        return True

    if (
        len(original) <= 140
        and len(original.split()) <= 18
        and original == original.upper()
        and l.rstrip(":") in headers
    ):
        return True

    return False


def extraer_encabezado_inline(linea: str) -> Tuple[Optional[str], str]:
    """
    Detecta líneas del tipo:
    'INDICACIONES TERAPÉUTICAS: texto...'
    y devuelve (encabezado, resto).
    """
    original = limpiar_linea(linea)
    if not original:
        return None, ""

    headers = sorted(obtener_headers_normalizados(), key=len, reverse=True)
    original_norm = normalizar_clave(original)

    for header in headers:
        header_con_dos_puntos = f"{header}:"

        if original_norm == header:
            return header, ""

        if original_norm.startswith(header_con_dos_puntos):
            resto_original = original[len(original.split(":")[0]) + 1:].strip()
            return header, resto_original

        # Caso robusto: encabezado seguido de ":" aunque haya diferencias de OCR
        patron = re.compile(rf"^{re.escape(header)}\s*:\s*(.*)$", flags=re.IGNORECASE)
        m = patron.match(original_norm)
        if m:
            # Reconstrucción más fiel usando el original
            partes = original.split(":", 1)
            resto_original = partes[1].strip() if len(partes) > 1 else ""
            return header, resto_original

    return None, ""


def unir_spans_a_texto(line_dict: Dict) -> Tuple[str, float]:
    spans = line_dict.get("spans", [])
    textos = []
    tamanos = []

    for sp in spans:
        t = sp.get("text", "")
        if t and t.strip():
            textos.append(t.strip())
            try:
                tamanos.append(float(sp.get("size", 0.0)))
            except Exception:
                pass

    texto = " ".join(textos)
    texto = limpiar_linea(texto)
    size_promedio = sum(tamanos) / len(tamanos) if tamanos else 0.0
    return texto, size_promedio


def extraer_bloques_pagina_fitz(page) -> List[Dict]:
    data = page.get_text("dict")
    bloques = []

    for block in data.get("blocks", []):
        if block.get("type", 0) != 0:
            continue

        bbox = block.get("bbox", [0, 0, 0, 0])
        x0, y0, x1, y1 = [float(v) for v in bbox]

        lineas_texto = []
        tamanos = []

        for line in block.get("lines", []):
            texto_linea, size_linea = unir_spans_a_texto(line)
            if texto_linea:
                lineas_texto.append(texto_linea)
                if size_linea > 0:
                    tamanos.append(size_linea)

        texto_bloque = "\n".join(lineas_texto).strip()
        if not texto_bloque:
            continue

        bloques.append({
            "texto": texto_bloque.strip(),
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "size": (sum(tamanos) / len(tamanos)) if tamanos else 0.0,
        })

    return bloques


def detectar_dos_columnas_bloques(bloques: List[Dict], ancho_pagina: float) -> bool:
    if len(bloques) < 4:
        return False

    mitad = ancho_pagina / 2
    izquierda = 0
    derecha = 0

    for b in bloques:
        centro = (b["x0"] + b["x1"]) / 2
        if centro < mitad:
            izquierda += 1
        else:
            derecha += 1

    return izquierda >= 2 and derecha >= 2


def ordenar_bloques_por_lectura(bloques: List[Dict], ancho_pagina: float) -> List[Dict]:
    if not bloques:
        return []

    if detectar_dos_columnas_bloques(bloques, ancho_pagina):
        mitad = ancho_pagina / 2
        izquierda = [b for b in bloques if ((b["x0"] + b["x1"]) / 2) < mitad]
        derecha = [b for b in bloques if ((b["x0"] + b["x1"]) / 2) >= mitad]

        izquierda.sort(key=lambda b: (b["y0"], b["x0"]))
        derecha.sort(key=lambda b: (b["y0"], b["x0"]))
        return izquierda + derecha

    return sorted(bloques, key=lambda b: (b["y0"], b["x0"]))


def dividir_bloque_en_lineas(bloque: Dict) -> List[Dict]:
    texto = bloque["texto"]
    partes = [limpiar_linea(x) for x in texto.split("\n")]
    partes = [x for x in partes if x]

    if not partes:
        return []

    total = len(partes)
    alto = max(1.0, bloque["y1"] - bloque["y0"])
    salto = alto / max(total, 1)

    salida = []
    for i, linea in enumerate(partes):
        salida.append({
            "texto": linea,
            "x0": bloque["x0"],
            "x1": bloque["x1"],
            "top": bloque["y0"] + (i * salto),
            "bottom": bloque["y0"] + ((i + 1) * salto),
            "size": bloque["size"],
            "bloque_id": id(bloque),
        })
    return salida


def detectar_encabezados_posicionales(lineas: List[Dict]) -> List[int]:
    if not lineas:
        return []

    tamanos = [l["size"] for l in lineas if l["size"] > 0]
    size_base = median(tamanos) if tamanos else 0.0

    indices = []

    for i, linea in enumerate(lineas):
        texto = linea["texto"]

        encabezado_inline, resto = extraer_encabezado_inline(texto)
        if encabezado_inline:
            indices.append(i)
            continue

        if parece_encabezado_textual(texto):
            indices.append(i)
            continue

        if (
            size_base > 0
            and linea["size"] >= (size_base * 1.15)
            and len(texto.split()) <= 18
            and parece_encabezado_textual(texto)
        ):
            indices.append(i)

    return sorted(set(indices))


def linea_parece_lista(linea: str) -> bool:
    l = linea.strip()

    patrones = [
        r"^\d+[\.\)]\s+",
        r"^[a-zA-Z][\.\)]\s+",
        r"^[-•*]\s+",
        r"^(frasco|bolsa|ampolleta|tabletas|capsulas|cápsulas|jarabe|solucion|solución|suspension|suspensión|caja)\b",
    ]

    for patron in patrones:
        if re.match(patron, l, flags=re.IGNORECASE):
            return True

    return False


def construir_bloque_con_formato(partes: List[str], nombre_seccion: str = "") -> str:
    if not partes:
        return ""

    partes_limpias = [limpiar_linea(x) for x in partes if limpiar_linea(x)]
    if not partes_limpias:
        return ""

    nombre_seccion_n = normalizar_clave(nombre_seccion)

    if nombre_seccion_n in {"presentacion", "presentaciones", "formula", "fórmula", "composicion", "composición"}:
        return "\n".join(partes_limpias)

    lista_detectada = sum(1 for p in partes_limpias if linea_parece_lista(p))

    if lista_detectada >= 2:
        return "\n".join(partes_limpias)

    return normalizar_texto(" ".join(partes_limpias))


def construir_secciones_desde_lineas(lineas: List[Dict]) -> Dict[str, str]:
    if not lineas:
        return {}

    secciones: Dict[str, List[str]] = {}
    actual = "texto_general"
    secciones[actual] = []

    for linea in lineas:
        texto = limpiar_linea(linea["texto"])
        if not texto:
            continue

        encabezado_inline, resto = extraer_encabezado_inline(texto)

        if encabezado_inline:
            clave = encabezado_inline.rstrip(":").strip()
            secciones.setdefault(clave, [])
            actual = clave

            if resto:
                secciones[actual].append(resto)
            continue

        if parece_encabezado_textual(texto):
            clave = normalizar_clave(texto).rstrip(":")
            if not clave:
                clave = "texto_general"
            secciones.setdefault(clave, [])
            actual = clave
            continue

        secciones.setdefault(actual, []).append(texto)

    resultado = {}
    for clave, partes in secciones.items():
        bloque = construir_bloque_con_formato(partes, clave)
        if bloque:
            resultado[clave] = bloque

    return resultado


def ocr_pagina_pdf(doc_fitz, numero_pagina: int) -> str:
    if fitz is None or Image is None or pytesseract is None:
        return ""

    configurar_tesseract_si_existe()

    try:
        pagina = doc_fitz.load_page(numero_pagina)
        pix = pagina.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        imagen_bytes = pix.tobytes("png")
        imagen = Image.open(io.BytesIO(imagen_bytes))
        texto = pytesseract.image_to_string(imagen, lang="spa+eng")
        return normalizar_texto(texto)
    except Exception as e:
        registrar_log("error", f"OCR falló en página {numero_pagina + 1}: {e}", "extractor_documental")
        return ""


def ocr_pagina_pdf_con_pdftoppm(ruta_archivo: str, numero_pagina: int) -> str:
    if Image is None or pytesseract is None:
        return ""

    configurar_tesseract_si_existe()

    try:
        with tempfile.TemporaryDirectory(prefix="tlamatini_pdf_") as tmpdir:
            salida_base = str(Path(tmpdir) / "pagina")
            cmd = [
                "pdftoppm",
                "-f", str(numero_pagina + 1),
                "-l", str(numero_pagina + 1),
                "-png",
                ruta_archivo,
                salida_base,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                registrar_log("error", f"pdftoppm falló en página {numero_pagina + 1}: {res.stderr.strip()}", "extractor_documental")
                return ""

            imagenes = sorted(Path(tmpdir).glob("pagina-*.png"))
            if not imagenes:
                return ""

            imagen = Image.open(imagenes[0]).convert("RGB")
            texto = pytesseract.image_to_string(imagen, lang="spa+eng")
            return normalizar_texto(texto)
    except Exception as e:
        registrar_log("error", f"OCR con pdftoppm falló en página {numero_pagina + 1}: {e}", "extractor_documental")
        return ""


def extraer_paginas_pdf_pypdf(
    ruta_archivo: str,
    pagina_inicio: Optional[int] = None,
    pagina_fin: Optional[int] = None
) -> Tuple[List[Dict], int]:
    paginas: List[Dict] = []

    if PdfReader is None:
        registrar_log("error", "pypdf no está instalado.", "extractor_documental")
        return [], 0

    try:
        reader = PdfReader(ruta_archivo)
    except Exception as e:
        registrar_log("error", f"No se pudo abrir PDF con pypdf {ruta_archivo}: {e}", "extractor_documental")
        return [], 0

    try:
        total = len(reader.pages)
        inicio = 1 if pagina_inicio is None else max(1, pagina_inicio)
        fin = total if pagina_fin is None else min(total, pagina_fin)

        for i in range(inicio - 1, fin):
            texto_plano = ""
            try:
                texto_plano = normalizar_texto(reader.pages[i].extract_text() or "")
            except Exception as e:
                registrar_log("error", f"pypdf falló al extraer texto de página {i + 1}: {e}", "extractor_documental")

            if texto_pobre(texto_plano):
                texto_ocr = ocr_pagina_pdf_con_pdftoppm(ruta_archivo, i)
                if len(texto_ocr) > len(texto_plano):
                    texto_plano = texto_ocr

            texto_plano = normalizar_texto(texto_plano)
            if not texto_plano:
                continue

            temas = detectar_temas_en_texto(texto_plano)
            paginas.append({
                "pagina": i + 1,
                "texto": texto_plano,
                "secciones": {},
                "temas": temas,
            })

        return paginas, len(paginas)
    except Exception as e:
        registrar_log("error", f"Error al extraer PDF con pypdf {ruta_archivo}: {e}", "extractor_documental")
        return [], 0


def extraer_paginas_pdf(
    ruta_archivo: str,
    pagina_inicio: Optional[int] = None,
    pagina_fin: Optional[int] = None
) -> Tuple[List[Dict], int]:
    paginas: List[Dict] = []

    if fitz is None:
        registrar_log("error", "PyMuPDF no está instalado. Se usará fallback PDF.", "extractor_documental")
        return extraer_paginas_pdf_pypdf(ruta_archivo, pagina_inicio=pagina_inicio, pagina_fin=pagina_fin)

    configurar_tesseract_si_existe()

    try:
        doc = fitz.open(ruta_archivo)
    except Exception as e:
        registrar_log("error", f"No se pudo abrir PDF {ruta_archivo}: {e}", "extractor_documental")
        return [], 0

    try:
        total = len(doc)
        inicio = 1 if pagina_inicio is None else max(1, pagina_inicio)
        fin = total if pagina_fin is None else min(total, pagina_fin)

        for i in range(inicio - 1, fin):
            page = doc.load_page(i)
            ancho = float(page.rect.width)

            bloques = extraer_bloques_pagina_fitz(page)
            bloques = ordenar_bloques_por_lectura(bloques, ancho)

            lineas = []
            for bloque in bloques:
                lineas.extend(dividir_bloque_en_lineas(bloque))

            texto_plano = normalizar_texto("\n".join(l["texto"] for l in lineas))

            if texto_pobre(texto_plano):
                texto_ocr = ocr_pagina_pdf(doc, i)
                if len(texto_ocr) > len(texto_plano):
                    texto_plano = texto_ocr
                    lineas = [
                        {
                            "texto": l.strip(),
                            "x0": 0.0,
                            "x1": ancho,
                            "top": float(idx * 10),
                            "bottom": float(idx * 10 + 8),
                            "size": 0.0,
                            "bloque_id": idx,
                        }
                        for idx, l in enumerate(texto_ocr.split("\n")) if l.strip()
                    ]

            texto_plano = normalizar_texto(texto_plano)
            if not texto_plano:
                continue

            secciones = construir_secciones_desde_lineas(lineas)
            temas = detectar_temas_en_texto(texto_plano)

            paginas.append({
                "pagina": i + 1,
                "texto": texto_plano,
                "secciones": secciones,
                "temas": temas,
            })

        return paginas, len(paginas)

    except Exception as e:
        registrar_log("error", f"Error al extraer PDF {ruta_archivo}: {e}", "extractor_documental")
        return [], 0
    finally:
        try:
            doc.close()
        except Exception:
            pass


def extraer_paginas_texto_simple(ruta_archivo: str) -> Tuple[List[Dict], int]:
    try:
        with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as archivo:
            texto = archivo.read()

        texto = normalizar_texto(texto)
        lineas = [limpiar_linea(x) for x in texto.split("\n") if limpiar_linea(x)]

        lineas_reg = [
            {
                "texto": l,
                "x0": 0.0,
                "x1": 1000.0,
                "top": float(i * 10),
                "bottom": float(i * 10 + 8),
                "size": 0.0,
                "bloque_id": i,
            }
            for i, l in enumerate(lineas)
        ]

        secciones = construir_secciones_desde_lineas(lineas_reg)
        temas = detectar_temas_en_texto(texto)

        return [{
            "pagina": 1,
            "texto": texto,
            "secciones": secciones,
            "temas": temas,
        }], 1

    except Exception as e:
        registrar_log("error", f"Error al leer archivo de texto {ruta_archivo}: {e}", "extractor_documental")
        return [], 0
