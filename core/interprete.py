from typing import Dict, List

from core.indice_consulta import buscar_documentos


def buscar_en_biblioteca(
    pregunta: str,
    dominio: str = "",
    subdominio: str = "",
    limite: int = 8,
    modo_profundo: bool = False
) -> List[Dict]:
    resultados = buscar_documentos(
        consulta=pregunta,
        dominio=dominio,
        subdominio=subdominio,
        limite=limite if not modo_profundo else max(limite, 12)
    )

    if not resultados and subdominio:
        resultados = buscar_documentos(
            consulta=pregunta,
            dominio=dominio,
            subdominio="",
            limite=limite if not modo_profundo else max(limite, 12)
        )

    salida = []
    for i, r in enumerate(resultados, start=1):
        puntaje = max(1, 100 - ((i - 1) * 7))
        seccion = r.get("seccion", "") or ""

        salida.append({
            "puntaje": puntaje,
            "libro_id": r.get("libro_id", ""),
            "libro_nombre": r.get("libro_nombre", ""),
            "dominio": r.get("dominio", ""),
            "subdominio": r.get("subdominio", ""),
            "pagina": r.get("pagina", 0),
            "respuesta_exacta": (r.get("fragmento", "") or "").strip(),
            "frases_apoyo": [],
            "ruta": "",
            "tipo_resultado": "seccion" if seccion and not seccion.startswith("pagina_") else "frase",
            "seccion_detectada": seccion,
            "consenso_ocurrencias": 1
        })

    return salida