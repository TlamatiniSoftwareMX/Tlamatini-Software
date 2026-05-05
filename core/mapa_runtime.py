import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from core.logs import registrar_log
from core.memoria import RUTA_BASE_DATOS


RUTA_CAPAS = RUTA_BASE_DATOS / "capas_tacticas"


def _geojson_vacio() -> Dict:
    return {
        "type": "FeatureCollection",
        "features": []
    }


def _carpeta_mapa(mapa_id: str) -> Path:
    carpeta = RUTA_CAPAS / mapa_id
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _ruta_capa(mapa_id: str, nombre: str) -> Path:
    carpeta = _carpeta_mapa(mapa_id)
    return carpeta / f"{nombre}.geojson"


def _cargar_geojson(ruta: Path) -> Dict:
    if not ruta.exists():
        return _geojson_vacio()

    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            data = json.load(archivo)
        if not isinstance(data, dict):
            return _geojson_vacio()
        if data.get("type") != "FeatureCollection":
            return _geojson_vacio()
        if not isinstance(data.get("features", []), list):
            data["features"] = []
        return data
    except Exception:
        return _geojson_vacio()


def _guardar_geojson(ruta: Path, data: Dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(data, archivo, indent=2, ensure_ascii=False)


def cargar_capas_mapa(mapa_id: str) -> Dict:
    return {
        "puntos": _cargar_geojson(_ruta_capa(mapa_id, "puntos")),
        "poligonos": _cargar_geojson(_ruta_capa(mapa_id, "poligonos")),
        "nodos": _cargar_geojson(_ruta_capa(mapa_id, "nodos"))
    }


def agregar_punto_tactico(
    mapa_id: str,
    nombre: str,
    categoria: str,
    descripcion: str,
    riesgo: str,
    lat: float,
    lon: float,
    color: str = "#EF4444"
) -> Dict:
    ruta = _ruta_capa(mapa_id, "puntos")
    data = _cargar_geojson(ruta)

    feature = {
        "type": "Feature",
        "properties": {
            "id": f"PTO-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "nombre": nombre.strip(),
            "categoria": categoria.strip(),
            "descripcion": descripcion.strip(),
            "riesgo": riesgo.strip().lower(),
            "color": color,
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "geometry": {
            "type": "Point",
            "coordinates": [float(lon), float(lat)]
        }
    }

    data["features"].append(feature)
    _guardar_geojson(ruta, data)
    registrar_log("sistema", f"Punto táctico agregado: {nombre}", "capas_tacticas")
    return feature


def agregar_poligono_tactico(
    mapa_id: str,
    nombre: str,
    descripcion: str,
    riesgo: str,
    coordenadas_lon_lat: List[List[float]],
    color: str = "#F97316"
) -> Dict:
    if len(coordenadas_lon_lat) < 3:
        raise ValueError("Un polígono necesita al menos 3 vértices.")

    ruta = _ruta_capa(mapa_id, "poligonos")
    data = _cargar_geojson(ruta)

    coords = [list(p) for p in coordenadas_lon_lat]
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    feature = {
        "type": "Feature",
        "properties": {
            "id": f"POL-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "nombre": nombre.strip(),
            "descripcion": descripcion.strip(),
            "riesgo": riesgo.strip().lower(),
            "color": color,
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords]
        }
    }

    data["features"].append(feature)
    _guardar_geojson(ruta, data)
    registrar_log("sistema", f"Polígono táctico agregado: {nombre}", "capas_tacticas")
    return feature


def resumen_capas(mapa_id: str) -> Dict:
    capas = cargar_capas_mapa(mapa_id)
    return {
        "puntos": len(capas["puntos"].get("features", [])),
        "poligonos": len(capas["poligonos"].get("features", [])),
        "nodos": len(capas["nodos"].get("features", []))
    }
