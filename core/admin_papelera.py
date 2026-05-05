from datetime import datetime
from typing import Dict, List, Optional

from core.logs import registrar_log_admin
from core.memoria import agregar_a_seccion, buscar_en_seccion, eliminar_elemento, obtener_seccion, guardar_seccion


def enviar_a_papelera(tipo_objeto: str, origen: str, contenido: Dict) -> Dict:
    item = {
        "id": f"PAP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "tipo_objeto": tipo_objeto,
        "origen": origen,
        "contenido": contenido,
        "fecha_eliminacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    agregar_a_seccion("papelera", item)
    registrar_log_admin("enviar_a_papelera", f"{tipo_objeto} desde {origen}", "papelera")
    return item


def listar_papelera(tipo_objeto: str = "") -> List[Dict]:
    papelera = obtener_seccion("papelera", [])
    if not tipo_objeto:
        return papelera
    return [item for item in papelera if item.get("tipo_objeto") == tipo_objeto]


def restaurar_desde_papelera(papelera_id: str) -> Dict:
    item = buscar_en_seccion("papelera", "id", papelera_id)
    if not item:
        return {"ok": False, "mensaje": "No se encontró el elemento en papelera."}

    origen = item.get("origen", "")
    contenido = item.get("contenido", {})

    seccion = obtener_seccion(origen, [])
    if not isinstance(seccion, list):
        return {"ok": False, "mensaje": "La sección destino no es válida."}

    seccion.append(contenido)
    guardar_seccion(origen, seccion)

    eliminado = eliminar_elemento("papelera", "id", papelera_id)
    if eliminado is not None:
        registrar_log_admin("restaurar_papelera", f"{item.get('tipo_objeto', '')} a {origen}", "papelera")
        return {"ok": True, "mensaje": "Elemento restaurado correctamente."}

    return {"ok": False, "mensaje": "No se pudo completar la restauración."}


def vaciar_papelera() -> Dict:
    guardar_seccion("papelera", [])
    registrar_log_admin("vaciar_papelera", "Se vació la papelera interna", "papelera")
    return {"ok": True, "mensaje": "Papelera vaciada correctamente."}