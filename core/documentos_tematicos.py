from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.biblioteca import guardar_cache_libro, listar_libros, registrar_libro
from core.extractor_documental import (
    Image,
    extraer_paginas_pdf,
    extraer_paginas_texto_simple,
    normalizar_texto as normalizar_texto_extraido,
    pytesseract,
)
from core.indice_consulta import buscar_fragmentos, fragmentar_texto, reindexar_libro
from core.logs import registrar_log
from core.tema_consulta import TEMA_GENERAL, biblioteca_por_tema, normalizar_tema
from core.texto import normalizar_texto


BIBLIOTECAS_DOMINIOS = {
    "biblioteca_medica": ["medica", "medicina", "herbolaria", "veterinaria"],
    "biblioteca_filosofia": ["filosofia"],
    "biblioteca_derecho": ["derecho"],
    "biblioteca_historia": ["historia"],
    "biblioteca_psicologia": ["psicologia"],
    "biblioteca_literatura": ["literatura"],
    "biblioteca_ingenieria": [
        "ingenieria", "instalacion_mantenimiento_reparacion", "instalacion",
        "proteccion_civil", "autosuficiencia", "siembra", "preparacionismo",
        "campismo", "vehiculos", "construccion", "agua_saneamiento",
    ],
    "biblioteca_general": [""],
}

EXTENSIONES_IMAGEN = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
EXTENSIONES_DOCUMENTO = {".pdf", ".txt", ".md"}


def _normalizar(valor: str) -> str:
    return normalizar_texto(valor or "")


def _normalizar_biblioteca(nombre: str) -> str:
    nombre_n = _normalizar(nombre)
    if nombre_n in BIBLIOTECAS_DOMINIOS:
        return nombre_n
    if nombre_n.startswith("biblioteca_"):
        return nombre_n
    return biblioteca_por_tema(nombre_n or TEMA_GENERAL)


def _dominios_para_biblioteca(biblioteca: str) -> List[str]:
    biblioteca_n = _normalizar_biblioteca(biblioteca)
    return BIBLIOTECAS_DOMINIOS.get(biblioteca_n, [""])


def _deduplicar_resultados(resultados: List[Dict], limite: int) -> List[Dict]:
    unicos = []
    vistos = set()
    for resultado in sorted(resultados, key=lambda item: item.get("score_final", 999999)):
        clave = (
            resultado.get("libro_id"),
            resultado.get("pagina"),
            (resultado.get("titulo_seccion") or "").strip().lower(),
            (resultado.get("texto_normalizado") or "")[:220],
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(resultado)
        if len(unicos) >= limite:
            break
    return unicos


class OCRService:
    def is_available(self) -> Tuple[bool, str]:
        if Image is None or pytesseract is None:
            return False, "PIL o pytesseract no están disponibles."
        return True, "OCR disponible."

    def extract_image_text(self, ruta_archivo: str) -> str:
        disponible, _ = self.is_available()
        if not disponible:
            return ""
        try:
            imagen = Image.open(ruta_archivo).convert("RGB")
            texto = pytesseract.image_to_string(imagen, lang="spa+eng")
            return normalizar_texto_extraido(texto)
        except Exception as exc:
            registrar_log("error", f"OCR de imagen falló en {ruta_archivo}: {exc}", "documentos_tematicos")
            return ""


class TextExtractionService:
    def __init__(self, ocr_service: Optional[OCRService] = None):
        self.ocr_service = ocr_service or OCRService()

    def extract_pages(self, ruta_archivo: str) -> Tuple[List[Dict], int, bool]:
        ruta = Path(ruta_archivo).expanduser().resolve()
        ext = ruta.suffix.lower()

        if ext == ".pdf":
            paginas, total = extraer_paginas_pdf(str(ruta))
            return paginas, total, any(p.get("secciones") == {} and p.get("texto") for p in paginas)

        if ext in {".txt", ".md"}:
            paginas, total = extraer_paginas_texto_simple(str(ruta))
            return paginas, total, False

        if ext in EXTENSIONES_IMAGEN:
            texto = self.ocr_service.extract_image_text(str(ruta))
            if not texto:
                return [], 0, True
            return [{
                "pagina": 1,
                "texto": texto,
                "secciones": {},
                "temas": [],
            }], 1, True

        return [], 0, False


class ChunkingService:
    def chunk_text(self, texto: str, max_chars: int = 1000) -> List[str]:
        return fragmentar_texto(texto, max_chars=max_chars)


class DocumentIngestionService:
    def __init__(self, extraction_service: Optional[TextExtractionService] = None):
        self.extraction_service = extraction_service or TextExtractionService()

    def ingest_document(
        self,
        ruta_archivo: str,
        biblioteca: str = "biblioteca_general",
        subdominio: str = "general",
        categoria_id: str = "",
        categoria_nombre: str = "",
    ) -> Dict:
        ruta = Path(ruta_archivo).expanduser().resolve()
        if not ruta.exists():
            return {"ok": False, "mensaje": "No se encontró el archivo indicado."}

        ext = ruta.suffix.lower()
        if ext not in EXTENSIONES_DOCUMENTO.union(EXTENSIONES_IMAGEN):
            return {"ok": False, "mensaje": "Formato no soportado para ingestión temática."}

        tema = normalizar_tema(_normalizar_biblioteca(biblioteca).replace("biblioteca_", ""))
        dominio = _dominios_para_biblioteca(biblioteca)[0] or "general"
        paginas, total_paginas, fue_ocr = self.extraction_service.extract_pages(str(ruta))
        if not paginas:
            return {"ok": False, "mensaje": "No se pudo extraer texto útil del documento."}

        libro = registrar_libro(
            ruta_archivo=str(ruta),
            dominio=dominio,
            subdominio=_normalizar(subdominio or "general") or "general",
            tipo_archivo=ext.replace(".", ""),
            paginas=total_paginas,
            caracteres_extraidos=sum(len((p.get("texto") or "")) for p in paginas),
            temas_detectados=[tema],
            paginas_indexadas=[p.get("pagina", 0) for p in paginas],
            categoria_id=categoria_id,
            categoria_nombre=categoria_nombre,
        )
        guardar_cache_libro(libro["hash_archivo"], {
            "libro_id": libro["id"],
            "libro_nombre": libro["nombre"],
            "dominio": libro["dominio"],
            "subdominio": libro["subdominio"],
            "ruta": libro["ruta"],
            "paginas": paginas,
            "fue_ocr": fue_ocr,
        })
        total_fragmentos = reindexar_libro(libro, paginas)
        return {
            "ok": True,
            "mensaje": f"Documento cargado en {biblioteca}: {libro['nombre']}",
            "libro": libro,
            "fragmentos": total_fragmentos,
            "fue_ocr": fue_ocr,
        }


class EmbeddingService:
    def is_available(self) -> Tuple[bool, str]:
        return False, "No hay embeddings locales integrados; se usa búsqueda FTS5/BM25."


class VectorStoreService:
    def describe(self) -> Dict[str, str]:
        return {
            "backend": "sqlite_fts5",
            "mode": "sparse_retrieval",
            "note": "Tlamatini reutiliza índice FTS5 local en lugar de vector store denso en esta fase.",
        }


class RetrieverService:
    def list_documents(self, biblioteca: str) -> List[Dict]:
        documentos = []
        for dominio in _dominios_para_biblioteca(biblioteca):
            documentos.extend(listar_libros(dominio=dominio))
        if not documentos and _normalizar_biblioteca(biblioteca) == "biblioteca_general":
            documentos = listar_libros()
        return documentos

    def search(
        self,
        pregunta: str,
        biblioteca: str,
        subdominio: str = "",
        limite: int = 8,
    ) -> Dict:
        biblioteca_n = _normalizar_biblioteca(biblioteca)
        documentos = self.list_documents(biblioteca_n)
        if not documentos:
            return {
                "ok": True,
                "library": biblioteca_n,
                "theme": normalizar_tema(biblioteca_n.replace("biblioteca_", "")),
                "document_count": 0,
                "results": [],
                "message": "La biblioteca temática está vacía.",
            }

        resultados = []
        for dominio in _dominios_para_biblioteca(biblioteca_n):
            resultados.extend(
                buscar_fragmentos(
                    pregunta=pregunta,
                    dominio=dominio,
                    subdominio=subdominio,
                    limite=max(limite * 3, 12),
                )
            )

        if not resultados and biblioteca_n == "biblioteca_general":
            resultados = buscar_fragmentos(pregunta=pregunta, dominio="", subdominio=subdominio, limite=max(limite * 3, 12))

        resultados = _deduplicar_resultados(resultados, limite=limite)
        return {
            "ok": True,
            "library": biblioteca_n,
            "theme": normalizar_tema(biblioteca_n.replace("biblioteca_", "")),
            "document_count": len(documentos),
            "results": resultados,
            "message": "Búsqueda temática completada." if resultados else "No hubo coincidencias en la biblioteca temática.",
        }


def buscar_en_biblioteca_tematica(
    pregunta: str,
    biblioteca: str,
    subdominio: str = "",
    limite: int = 8,
) -> Dict:
    return RetrieverService().search(
        pregunta=pregunta,
        biblioteca=biblioteca,
        subdominio=subdominio,
        limite=limite,
    )
