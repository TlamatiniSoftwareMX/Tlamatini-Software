from datetime import datetime
from typing import Dict, Optional

from core.logs import registrar_log
from core.memoria import agregar_a_seccion, obtener_seccion
from core.texto import normalizar_texto


def aprender_conocimiento(
    titulo: str,
    contenido: str,
    dominio: str = "general",
    subdominio: str = "",
    fuente: str = "manual",
    etiquetas: Optional[list] = None
) -> Dict:
    item = {
        "id": f"CON-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "titulo": titulo.strip(),
        "contenido": contenido.strip(),
        "dominio": normalizar_texto(dominio),
        "subdominio": normalizar_texto(subdominio),
        "fuente": fuente.strip(),
        "etiquetas": etiquetas or [],
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    agregar_a_seccion("conocimiento", item)
    registrar_log("sistema", f"Conocimiento agregado: {item['titulo']}", "aprendizaje")
    return item


def listar_conocimiento(dominio: str = "") -> list:
    conocimientos = obtener_seccion("conocimiento", [])
    if not dominio:
        return conocimientos
    return [c for c in conocimientos if normalizar_texto(c.get("dominio", "")) == normalizar_texto(dominio)]
