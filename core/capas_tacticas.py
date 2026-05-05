import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.logs import registrar_log
from core.memoria import DATA_DIR, RUTA_BASE_DATOS, obtener_seccion


LEGACY_RUTA_CAPAS = RUTA_BASE_DATOS / "capas_tacticas"
RUTA_CAPAS = DATA_DIR / "local_maps" / "overlays"

LAYER_DEFS = {
    "puntos": {"label": "Puntos guardados", "geometry": ["Point"]},
    "rutas": {"label": "Rutas", "geometry": ["LineString", "MultiLineString"]},
    "poligonos": {"label": "Zonas de riesgo", "geometry": ["Polygon", "MultiPolygon"]},
    "refugios": {"label": "Refugios", "geometry": ["Point"]},
    "recursos": {"label": "Recursos", "geometry": ["Point"]},
    "nodos": {"label": "Nodos", "geometry": ["Point"]},
    "sensores": {"label": "Sensores", "geometry": ["Point"]},
    "comunicaciones": {"label": "Comunicaciones", "geometry": ["Point"]},
    "observacion": {"label": "Observación", "geometry": ["Point"]},
    "control": {"label": "Control y checkpoints", "geometry": ["Point"]},
    "rutas_evacuacion": {"label": "Rutas de evacuación", "geometry": ["LineString", "MultiLineString"]},
    "rutas_logisticas": {"label": "Rutas logísticas", "geometry": ["LineString", "MultiLineString"]},
    "rutas_patrullaje": {"label": "Rutas de patrullaje", "geometry": ["LineString", "MultiLineString"]},
    "zonas_seguras": {"label": "Zonas seguras", "geometry": ["Polygon", "MultiPolygon"]},
    "perimetros": {"label": "Perímetros", "geometry": ["Polygon", "MultiPolygon"]},
    "amenazas": {"label": "Amenazas", "geometry": ["Polygon", "MultiPolygon"]},
    "imported": {"label": "GeoJSON importado", "geometry": ["Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]},
}

GEOMETRY_KIND_MAP = {
    "point": ["Point"],
    "route": ["LineString", "MultiLineString"],
    "polygon": ["Polygon", "MultiPolygon"],
}


def obtener_layer_defs() -> Dict:
    capas = dict(LAYER_DEFS)
    prefs = obtener_seccion("mapas_viewer", {})
    custom_layers = prefs.get("custom_layers", []) if isinstance(prefs, dict) else []
    if not isinstance(custom_layers, list):
        custom_layers = []
    for item in custom_layers:
        if not isinstance(item, dict):
            continue
        layer_id = str(item.get("id", "")).strip().lower()
        label = str(item.get("label", "")).strip()
        geometry = item.get("geometry", [])
        if not layer_id or not label or not isinstance(geometry, list):
            continue
        geometry_clean = [str(value).strip() for value in geometry if str(value).strip()]
        if not geometry_clean:
            continue
        capas[layer_id] = {
            "label": label,
            "geometry": geometry_clean,
            "color": str(item.get("color", "")).strip(),
        }
    return capas


def _geojson_vacio() -> Dict:
    return {"type": "FeatureCollection", "features": []}


def _asegurar_raices() -> None:
    RUTA_CAPAS.mkdir(parents=True, exist_ok=True)
    LEGACY_RUTA_CAPAS.mkdir(parents=True, exist_ok=True)


def _migrar_legado_si_hace_falta(mapa_id: str, destino: Path) -> None:
    legacy_dir = LEGACY_RUTA_CAPAS / mapa_id
    if destino.exists() or not legacy_dir.exists():
        return
    shutil.copytree(legacy_dir, destino)


def _carpeta_mapa(mapa_id: str) -> Path:
    _asegurar_raices()
    carpeta = RUTA_CAPAS / mapa_id
    _migrar_legado_si_hace_falta(mapa_id, carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _ruta_capa(mapa_id: str, nombre: str) -> Path:
    carpeta = _carpeta_mapa(mapa_id)
    return carpeta / f"{nombre}.geojson"


def _cargar_geojson(ruta: Path) -> Dict:
    if not ruta.exists():
        return _geojson_vacio()
    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            return _geojson_vacio()
        if not isinstance(data.get("features", []), list):
            data["features"] = []
        return data
    except Exception:
        return _geojson_vacio()


def _guardar_geojson(ruta: Path, data: Dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _feature_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _norm_coord_list(coordenadas_lon_lat: List[List[float]]) -> List[List[float]]:
    return [[float(lon), float(lat)] for lon, lat in coordenadas_lon_lat]


def _layer_key(nombre: str) -> str:
    key = str(nombre or "").strip().lower()
    if key not in obtener_layer_defs():
        raise ValueError(f"Capa no soportada: {nombre}")
    return key


def cargar_capas_mapa(mapa_id: str) -> Dict:
    capas = {}
    for layer_id in obtener_layer_defs():
        capas[layer_id] = _cargar_geojson(_ruta_capa(mapa_id, layer_id))
    return capas


def guardar_feature(mapa_id: str, layer_id: str, feature: Dict) -> Dict:
    layer_id = _layer_key(layer_id)
    ruta = _ruta_capa(mapa_id, layer_id)
    data = _cargar_geojson(ruta)
    data["features"].append(feature)
    _guardar_geojson(ruta, data)
    registrar_log("sistema", f"Feature agregada a {layer_id}: {feature.get('properties', {}).get('nombre', feature.get('properties', {}).get('id', ''))}", "capas_tacticas")
    return feature


def agregar_punto_tactico(
    mapa_id: str,
    nombre: str,
    categoria: str,
    descripcion: str,
    riesgo: str,
    lat: float,
    lon: float,
    color: str = "#EF4444",
    layer_id: str = "puntos",
    notas: str = "",
    estado: str = "activo",
    emoji: str = "",
    icon_label: str = "",
) -> Dict:
    feature = {
        "type": "Feature",
        "properties": {
            "id": _feature_id("PTO"),
            "nombre": nombre.strip(),
            "tipo": layer_id,
            "categoria": categoria.strip() or layer_id,
            "descripcion": descripcion.strip(),
            "riesgo": riesgo.strip().lower(),
            "color": color,
            "estado": estado,
            "notas": notas.strip(),
            "emoji": emoji.strip(),
            "icon_label": icon_label.strip(),
            "fuente_datos": "manual",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "geometry": {
            "type": "Point",
            "coordinates": [float(lon), float(lat)],
        },
    }
    return guardar_feature(mapa_id, layer_id, feature)


def agregar_poligono_tactico(
    mapa_id: str,
    nombre: str,
    descripcion: str,
    riesgo: str,
    coordenadas_lon_lat: List[List[float]],
    color: str = "#F97316",
    layer_id: str = "poligonos",
    categoria: str = "zona_riesgo",
) -> Dict:
    if len(coordenadas_lon_lat) < 3:
        raise ValueError("Un polígono necesita al menos 3 vértices.")
    coords = _norm_coord_list(coordenadas_lon_lat)
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    feature = {
        "type": "Feature",
        "properties": {
            "id": _feature_id("POL"),
            "nombre": nombre.strip(),
            "tipo": layer_id,
            "categoria": categoria,
            "descripcion": descripcion.strip(),
            "riesgo": riesgo.strip().lower(),
            "color": color,
            "fuente_datos": "manual",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords],
        },
    }
    return guardar_feature(mapa_id, layer_id, feature)


def agregar_ruta_tactica(
    mapa_id: str,
    nombre: str,
    descripcion: str,
    categoria: str,
    coordenadas_lon_lat: List[List[float]],
    color: str = "#22c55e",
    layer_id: str = "rutas",
) -> Dict:
    if len(coordenadas_lon_lat) < 2:
        raise ValueError("Una ruta necesita al menos 2 coordenadas.")
    feature = {
        "type": "Feature",
        "properties": {
            "id": _feature_id("RUT"),
            "nombre": nombre.strip(),
            "tipo": layer_id,
            "categoria": categoria.strip() or "ruta",
            "descripcion": descripcion.strip(),
            "color": color,
            "fuente_datos": "manual",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "geometry": {
            "type": "LineString",
            "coordinates": _norm_coord_list(coordenadas_lon_lat),
        },
    }
    return guardar_feature(mapa_id, layer_id, feature)


def importar_geojson_capa(mapa_id: str, ruta_archivo: str, layer_id: str = "imported", fusionar: bool = True) -> Dict:
    path = Path(ruta_archivo).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError("El archivo GeoJSON no existe.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"No se pudo leer el GeoJSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise ValueError("El archivo debe ser un FeatureCollection GeoJSON.")
    if not isinstance(payload.get("features", []), list):
        raise ValueError("El GeoJSON no contiene una lista válida de features.")

    target_path = _ruta_capa(mapa_id, layer_id)
    current = _cargar_geojson(target_path) if fusionar else _geojson_vacio()
    imported_count = 0
    for feature in payload.get("features", []):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            continue
        props = feature.setdefault("properties", {})
        props.setdefault("id", _feature_id("IMP"))
        props.setdefault("tipo", layer_id)
        props.setdefault("categoria", "importado")
        props.setdefault("fuente_datos", str(path))
        props.setdefault("fecha_registro", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        current["features"].append(feature)
        imported_count += 1
    _guardar_geojson(target_path, current)
    registrar_log("sistema", f"GeoJSON importado a {layer_id}: {path.name} ({imported_count} features)", "capas_tacticas")
    return {"layer_id": layer_id, "features": imported_count, "path": str(path)}


def metadata_capas_mapa(mapa_id: str) -> List[Dict]:
    capas = cargar_capas_mapa(mapa_id)
    layer_defs = obtener_layer_defs()
    results = []
    for layer_id, info in layer_defs.items():
        features = capas.get(layer_id, {}).get("features", [])
        geometry_types = sorted({str((feat.get("geometry") or {}).get("type", "")) for feat in features if feat.get("geometry")})
        results.append(
            {
                "id": layer_id,
                "label": info["label"],
                "color": info.get("color", ""),
                "feature_count": len(features),
                "geometry_types": geometry_types,
            }
        )
    return results


def resumen_capas(mapa_id: str) -> Dict:
    capas = cargar_capas_mapa(mapa_id)
    return {layer_id: len(capas[layer_id].get("features", [])) for layer_id in obtener_layer_defs()}


def obtener_feature(mapa_id: str, feature_id: str) -> Optional[Dict]:
    for layer in cargar_capas_mapa(mapa_id).values():
        for feature in layer.get("features", []):
            if feature.get("properties", {}).get("id") == feature_id:
                return feature
    return None


def actualizar_feature(mapa_id: str, feature_id: str, layer_id: str, feature_actualizada: Dict) -> Dict:
    layer_id = _layer_key(layer_id)
    ruta = _ruta_capa(mapa_id, layer_id)
    data = _cargar_geojson(ruta)
    updated = False
    for idx, feature in enumerate(data.get("features", [])):
        if feature.get("properties", {}).get("id") == feature_id:
            data["features"][idx] = feature_actualizada
            updated = True
            break
    if not updated:
        raise ValueError("No se encontró el elemento a actualizar.")
    _guardar_geojson(ruta, data)
    registrar_log("sistema", f"Feature actualizada en {layer_id}: {feature_id}", "capas_tacticas")
    return feature_actualizada


def eliminar_feature(mapa_id: str, feature_id: str, layer_id: Optional[str] = None) -> bool:
    layer_ids = [layer_id] if layer_id else list(obtener_layer_defs().keys())
    for raw_layer_id in layer_ids:
        current_layer = _layer_key(raw_layer_id)
        ruta = _ruta_capa(mapa_id, current_layer)
        data = _cargar_geojson(ruta)
        features = data.get("features", [])
        filtered = [feature for feature in features if feature.get("properties", {}).get("id") != feature_id]
        if len(filtered) != len(features):
            data["features"] = filtered
            _guardar_geojson(ruta, data)
            registrar_log("sistema", f"Feature eliminada de {current_layer}: {feature_id}", "capas_tacticas")
            return True
    return False
