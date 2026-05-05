from datetime import datetime
from typing import Dict, List, Optional

from core.logs import registrar_log
from core.memoria import obtener_seccion, guardar_seccion


RIESGO_COLOR = {
    "bajo": "#22C55E",
    "medio": "#EAB308",
    "alto": "#F97316",
    "critico": "#DC2626"
}


def _estructura_mapa_base() -> Dict:
    return {
        "puntos_interes": [],
        "poligonos_riesgo": [],
        "configuracion": {
            "fondo_mapa": "",
            "ancho_canvas": 1000,
            "alto_canvas": 700
        }
    }


def _cargar_mapa() -> Dict:
    mapa = obtener_seccion("mapa", {})
    base = _estructura_mapa_base()

    if not isinstance(mapa, dict):
        return base

    for clave, valor in base.items():
        if clave not in mapa:
            mapa[clave] = valor

    if "configuracion" not in mapa or not isinstance(mapa["configuracion"], dict):
        mapa["configuracion"] = base["configuracion"]

    for clave, valor in base["configuracion"].items():
        if clave not in mapa["configuracion"]:
            mapa["configuracion"][clave] = valor

    return mapa


def _guardar_mapa(mapa: Dict) -> None:
    guardar_seccion("mapa", mapa)


def obtener_color_por_riesgo(nivel_riesgo: str) -> str:
    return RIESGO_COLOR.get((nivel_riesgo or "").strip().lower(), "#3B82F6")


def guardar_configuracion_mapa(
    fondo_mapa: str = "",
    ancho_canvas: Optional[int] = None,
    alto_canvas: Optional[int] = None
) -> Dict:
    mapa = _cargar_mapa()
    config = mapa.get("configuracion", {})

    if fondo_mapa is not None:
        config["fondo_mapa"] = fondo_mapa

    if ancho_canvas is not None:
        config["ancho_canvas"] = int(ancho_canvas)

    if alto_canvas is not None:
        config["alto_canvas"] = int(alto_canvas)

    mapa["configuracion"] = config
    _guardar_mapa(mapa)

    registrar_log("sistema", "Configuración de mapa actualizada", "mapa")
    return config


def obtener_configuracion_mapa() -> Dict:
    mapa = _cargar_mapa()
    return mapa.get("configuracion", {})


def agregar_punto_interes(
    nombre: str,
    tipo: str,
    descripcion: str,
    x: float,
    y: float,
    nivel_riesgo: str = "bajo",
    color: str = ""
) -> Dict:
    mapa = _cargar_mapa()

    nivel_riesgo = (nivel_riesgo or "bajo").strip().lower()
    color_final = color.strip() if color else obtener_color_por_riesgo(nivel_riesgo)

    punto = {
        "id": f"PTO-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "nombre": nombre.strip(),
        "tipo": tipo.strip(),
        "descripcion": descripcion.strip(),
        "nivel_riesgo": nivel_riesgo,
        "color": color_final,
        "x": float(x),
        "y": float(y),
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    mapa["puntos_interes"].append(punto)
    _guardar_mapa(mapa)

    registrar_log("sistema", f"Punto de interés agregado: {punto['nombre']}", "mapa")
    return punto


def agregar_poligono_riesgo(
    nombre: str,
    nivel_riesgo: str,
    descripcion: str,
    puntos: List[dict],
    tipo: str = "zona_riesgo",
    color: str = ""
) -> Dict:
    mapa = _cargar_mapa()

    nivel_riesgo = (nivel_riesgo or "medio").strip().lower()
    color_final = color.strip() if color else obtener_color_por_riesgo(nivel_riesgo)

    poligono = {
        "id": f"POL-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "nombre": nombre.strip(),
        "tipo": tipo.strip(),
        "nivel_riesgo": nivel_riesgo,
        "descripcion": descripcion.strip(),
        "color": color_final,
        "puntos": puntos,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    mapa["poligonos_riesgo"].append(poligono)
    _guardar_mapa(mapa)

    registrar_log("sistema", f"Polígono de riesgo agregado: {poligono['nombre']}", "mapa")
    return poligono


def obtener_mapa() -> dict:
    return _cargar_mapa()


def listar_elementos_mapa() -> List[Dict]:
    mapa = _cargar_mapa()
    elementos = []

    for punto in mapa.get("puntos_interes", []):
        elementos.append({
            "id": punto["id"],
            "tipo_elemento": "punto",
            "nombre": punto.get("nombre", ""),
            "categoria": punto.get("tipo", ""),
            "nivel_riesgo": punto.get("nivel_riesgo", ""),
            "descripcion": punto.get("descripcion", "")
        })

    for poligono in mapa.get("poligonos_riesgo", []):
        elementos.append({
            "id": poligono["id"],
            "tipo_elemento": "poligono",
            "nombre": poligono.get("nombre", ""),
            "categoria": poligono.get("tipo", ""),
            "nivel_riesgo": poligono.get("nivel_riesgo", ""),
            "descripcion": poligono.get("descripcion", "")
        })

    return elementos


def obtener_elemento_mapa(elemento_id: str) -> Optional[Dict]:
    mapa = _cargar_mapa()

    for punto in mapa.get("puntos_interes", []):
        if punto.get("id") == elemento_id:
            copia = dict(punto)
            copia["tipo_elemento"] = "punto"
            return copia

    for poligono in mapa.get("poligonos_riesgo", []):
        if poligono.get("id") == elemento_id:
            copia = dict(poligono)
            copia["tipo_elemento"] = "poligono"
            return copia

    return None


def eliminar_elemento_mapa(elemento_id: str) -> bool:
    mapa = _cargar_mapa()

    puntos = mapa.get("puntos_interes", [])
    poligonos = mapa.get("poligonos_riesgo", [])

    nuevos_puntos = [p for p in puntos if p.get("id") != elemento_id]
    if len(nuevos_puntos) != len(puntos):
        mapa["puntos_interes"] = nuevos_puntos
        _guardar_mapa(mapa)
        registrar_log("sistema", f"Elemento de mapa eliminado: {elemento_id}", "mapa")
        return True

    nuevos_poligonos = [p for p in poligonos if p.get("id") != elemento_id]
    if len(nuevos_poligonos) != len(poligonos):
        mapa["poligonos_riesgo"] = nuevos_poligonos
        _guardar_mapa(mapa)
        registrar_log("sistema", f"Elemento de mapa eliminado: {elemento_id}", "mapa")
        return True

    return False


def limpiar_mapa() -> None:
    _guardar_mapa(_estructura_mapa_base())
    registrar_log("sistema", "Mapa limpiado", "mapa")