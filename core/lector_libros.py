from pathlib import Path
from typing import Callable, Dict, Optional

from core.biblioteca import EXTENSIONES_VALIDAS, registrar_libro, guardar_cache_libro
from core.catalogo_dominios import inferir_dominio_desde_texto
from core.clasificador_temas import detectar_subdominio_sugerido
from core.extractor_documental import PdfReader, extraer_paginas_pdf, extraer_paginas_texto_simple, fitz, pytesseract
from core.indice_consulta import reindexar_libro
from core.logs import registrar_log


def cargar_libro_a_conocimiento(
    ruta_archivo: str,
    dominio: str = "medica",
    subdominio: str = "general",
    pagina_inicio: Optional[int] = None,
    pagina_fin: Optional[int] = None,
    categoria_id: str = "",
    categoria_nombre: str = "",
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict:
    ruta = Path(ruta_archivo)

    def reportar(etapa: str):
        if progress_callback is None:
            return
        try:
            progress_callback(etapa)
        except Exception:
            pass

    if not ruta.exists():
        return {"ok": False, "mensaje": "No se encontró el archivo indicado."}

    if ruta.suffix.lower() not in EXTENSIONES_VALIDAS:
        return {"ok": False, "mensaje": "Formato no soportado. Solo .pdf, .txt y .md"}

    reportar("Extrayendo texto")
    if ruta.suffix.lower() == ".pdf":
        paginas, paginas_leidas = extraer_paginas_pdf(
            ruta_archivo=ruta_archivo,
            pagina_inicio=pagina_inicio,
            pagina_fin=pagina_fin
        )
    else:
        paginas, paginas_leidas = extraer_paginas_texto_simple(ruta_archivo)

    if not paginas:
        detalle = []
        if ruta.suffix.lower() == ".pdf":
            detalle.append(f"PyMuPDF={'OK' if fitz is not None else 'NO'}")
            detalle.append(f"pypdf={'OK' if PdfReader is not None else 'NO'}")
            detalle.append(f"pytesseract={'OK' if pytesseract is not None else 'NO'}")
        return {
            "ok": False,
            "mensaje": (
                "No se pudo extraer texto útil del archivo."
                + (f" Diagnóstico: {', '.join(detalle)}." if detalle else "")
                + " Si es un PDF escaneado, revisa OCR/Tesseract."
            )
        }

    caracteres_extraidos = sum(len((p.get("texto") or "")) for p in paginas)
    muestra_texto = " ".join(((p.get("texto", "") or "")[:1200]) for p in paginas[:6])
    inferencia_dominio = inferir_dominio_desde_texto(f"{ruta.name} {muestra_texto}", include_possible=True)
    dominio_final = (dominio or "").strip().lower() or "general"
    if dominio_final in {"", "general"}:
        dominio_inferido = str(inferencia_dominio.get("operational_domain", "") or "")
        if dominio_inferido:
            dominio_final = dominio_inferido

    reportar("Analizando temas")
    todos_los_temas = []
    for p in paginas:
        for tema in p.get("temas", []):
            if tema not in todos_los_temas:
                todos_los_temas.append(tema)

    subdominio_final = (subdominio or "general").strip().lower()
    if subdominio_final in ("", "general"):
        sugerido = detectar_subdominio_sugerido(
            dominio_final,
            " ".join(((p.get("texto", "") or "")[:1500]) for p in paginas[:8])
        )
        if sugerido:
            subdominio_final = sugerido

    reportar("Registrando libro")
    libro = registrar_libro(
        ruta_archivo=str(ruta),
        dominio=dominio_final,
        subdominio=subdominio_final or "general",
        tipo_archivo=ruta.suffix.lower().replace(".", ""),
        paginas=paginas_leidas,
        caracteres_extraidos=caracteres_extraidos,
        temas_detectados=todos_los_temas,
        paginas_indexadas=[p.get("pagina", 0) for p in paginas],
        categoria_id=categoria_id,
        categoria_nombre=categoria_nombre,
    )

    reportar("Guardando caché")
    payload = {
        "libro_id": libro["id"],
        "libro_nombre": libro["nombre"],
        "dominio": libro["dominio"],
        "subdominio": libro["subdominio"],
        "ruta": libro["ruta"],
        "paginas": paginas
    }

    guardar_cache_libro(libro["hash_archivo"], payload)
    reportar("Indexando contenido")
    total_fragmentos = reindexar_libro(libro, paginas)

    registrar_log(
        "sistema",
        f"Libro cargado e indexado: {libro['nombre']} ({paginas_leidas} páginas, {total_fragmentos} fragmentos)",
        "lector_libros"
    )

    return {
        "ok": True,
        "mensaje": f"Libro cargado correctamente: {libro['nombre']} ({total_fragmentos} fragmentos indexados)",
        "libro": libro,
        "fragmentos": total_fragmentos
    }
