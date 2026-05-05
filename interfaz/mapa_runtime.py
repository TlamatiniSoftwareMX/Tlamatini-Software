import json
import mimetypes
import socket
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import unquote, urlparse

from core.capas_tacticas import LAYER_DEFS, cargar_capas_mapa, metadata_capas_mapa, obtener_layer_defs
from core.capas_tacticas import agregar_poligono_tactico, agregar_punto_tactico, agregar_ruta_tactica, actualizar_feature, eliminar_feature, obtener_feature, guardar_feature
from core.mapas_offline import get_offline_maps_service
from core.memoria import APP_DIR, guardar_seccion, obtener_seccion
from core.satellite_tiles import SATELLITE_TILE_URL, get_satellite_tile_service, satellite_availability, satellite_provider_configured


MAP_UI_DIR = APP_DIR / "map_ui"
RUNTIME_DIR = MAP_UI_DIR / "runtime"
VIEWER_STYLES = [
    {"id": "standard", "label": "Estándar"},
    {"id": "dark", "label": "Oscuro"},
    {"id": "tactical", "label": "Táctico"},
    {"id": "paper", "label": "Papel"},
    {"id": "desert", "label": "Desierto"},
    {"id": "nightwatch", "label": "Nightwatch"},
    {"id": "high_contrast", "label": "Alto contraste"},
]
BASE_LAYER_DEFAULTS = {
    "land": True,
    "water": True,
    "roads": True,
    "rails": True,
    "air": True,
    "buildings": True,
    "parks": True,
    "terrain": True,
    "landuse": True,
    "boundaries": True,
    "labels": True,
    "place_labels": True,
    "water_labels": True,
    "boundary_labels": True,
}
EXTRA_OVERLAY_DEFAULTS = {
    "curvas_nivel": False,
    "areas_verdes": False,
    "areas_urbanas": False,
}
LAYER_OPTION_LABELS_DEFAULTS = {
    layer_id: meta.get("label", layer_id.title()) for layer_id, meta in LAYER_DEFS.items()
}
CATEGORY_OPTIONS_DEFAULTS = {
    "point": [
        {"value": "refugio", "label": "Refugio"},
        {"value": "recurso", "label": "Recurso"},
        {"value": "zona_riesgo", "label": "Zona de riesgo"},
        {"value": "nodo", "label": "Nodo"},
        {"value": "sensor", "label": "Sensor"},
        {"value": "punto_interes", "label": "Punto de interés"},
        {"value": "comunicaciones", "label": "Comunicaciones"},
        {"value": "observacion", "label": "Observación"},
        {"value": "checkpoint", "label": "Checkpoint"},
    ],
    "route": [
        {"value": "ruta", "label": "Ruta"},
        {"value": "evacuacion", "label": "Evacuación"},
        {"value": "abastecimiento", "label": "Abastecimiento"},
        {"value": "patrullaje", "label": "Patrullaje"},
        {"value": "escape", "label": "Escape"},
        {"value": "enlace", "label": "Enlace"},
    ],
    "polygon": [
        {"value": "zona_riesgo", "label": "Zona de riesgo"},
        {"value": "perimetro", "label": "Perímetro"},
        {"value": "operacion", "label": "Operación"},
        {"value": "zona_segura", "label": "Zona segura"},
        {"value": "amenaza", "label": "Amenaza"},
        {"value": "resguardo", "label": "Resguardo"},
    ],
}


class _ViewerState:
    server = None
    thread = None
    port = None
    active_map_id = ""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _viewer_url() -> str:
    _start_server_if_needed()
    return f"http://127.0.0.1:{_ViewerState.port}/"


def _utcnow() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _prefs_default() -> Dict:
    return {
        "style_id": "standard",
        "map_base": "mapa",
        "base_layers": dict(BASE_LAYER_DEFAULTS),
        "overlay_layers": {**{layer_id: True for layer_id in obtener_layer_defs()}, **dict(EXTRA_OVERLAY_DEFAULTS)},
        "category_options": dict(CATEGORY_OPTIONS_DEFAULTS),
        "category_hidden": {"point": [], "route": [], "polygon": []},
        "custom_layers": [],
        "layer_option_labels": dict(LAYER_OPTION_LABELS_DEFAULTS),
        "layer_hidden": {"point": [], "route": [], "polygon": []},
        "last_center": {"lat": 19.4326, "lon": -99.1332},
        "last_zoom": 11.0,
        "measurement_enabled": False,
        "telemetry_visible": False,
    }


def get_map_viewer_url() -> str:
    return _viewer_url()


def open_map_viewer() -> str:
    url = _viewer_url()
    webbrowser.open(url)
    return url


def load_viewer_preferences() -> Dict:
    prefs = obtener_seccion("mapas_viewer", {})
    if not isinstance(prefs, dict):
        prefs = {}
    base = _prefs_default()
    result = dict(base)
    result.update({k: v for k, v in prefs.items() if v is not None})
    result["base_layers"] = {**base["base_layers"], **dict(result.get("base_layers", {}))}
    result["overlay_layers"] = {**base["overlay_layers"], **dict(result.get("overlay_layers", {}))}
    result["category_options"] = {
        **base["category_options"],
        **dict(result.get("category_options", {})),
    }
    result["category_hidden"] = {
        **base["category_hidden"],
        **dict(result.get("category_hidden", {})),
    }
    result["layer_option_labels"] = {
        **base["layer_option_labels"],
        **dict(result.get("layer_option_labels", {})),
    }
    result["layer_hidden"] = {
        **base["layer_hidden"],
        **dict(result.get("layer_hidden", {})),
    }
    if not isinstance(result.get("custom_layers", []), list):
        result["custom_layers"] = []
    for layer_id in obtener_layer_defs().keys():
        result["overlay_layers"].setdefault(layer_id, True)
    for layer_id, enabled in EXTRA_OVERLAY_DEFAULTS.items():
        result["overlay_layers"].setdefault(layer_id, enabled)
    return result


def save_viewer_preferences(prefs: Dict) -> Dict:
    current = load_viewer_preferences()
    for key, value in (prefs or {}).items():
        if key in {"style_id", "map_base", "last_center", "last_zoom", "measurement_enabled", "telemetry_visible"}:
            current[key] = value
        elif key == "base_layers":
            current["base_layers"].update(dict(value or {}))
        elif key == "overlay_layers":
            current["overlay_layers"].update(dict(value or {}))
        elif key == "category_options":
            current["category_options"].update(dict(value or {}))
        elif key == "category_hidden":
            current["category_hidden"].update(dict(value or {}))
        elif key == "custom_layers":
            current["custom_layers"] = list(value or [])
        elif key == "layer_option_labels":
            current["layer_option_labels"].update(dict(value or {}))
        elif key == "layer_hidden":
            current["layer_hidden"].update(dict(value or {}))
    guardar_seccion("mapas_viewer", current)
    return current


def update_map_runtime(mapa: Optional[dict]) -> str:
    _start_server_if_needed()
    _write_runtime(mapa)
    return _viewer_url()


def _start_server_if_needed() -> None:
    if _ViewerState.server is not None:
        return
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), TacticalMapHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _ViewerState.server = server
    _ViewerState.thread = thread
    _ViewerState.port = port


def _write_runtime(mapa: Optional[dict]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    _ViewerState.active_map_id = str((mapa or {}).get("id", "") or "")
    capas = cargar_capas_mapa(_ViewerState.active_map_id) if _ViewerState.active_map_id else _empty_layers()
    prefs = load_viewer_preferences()
    layer_meta = metadata_capas_mapa(_ViewerState.active_map_id) if _ViewerState.active_map_id else []
    layer_labels = dict(prefs.get("layer_option_labels", {}))
    for item in layer_meta:
        item["label"] = layer_labels.get(item["id"], item.get("label", item["id"]))
    config = {
        "updated_at": _utcnow(),
        "viewer_url": _viewer_url(),
        "mapa": _runtime_map_payload(mapa),
        "styles": VIEWER_STYLES,
        "preferences": prefs,
        "capas": _runtime_layers_payload(capas, layer_labels),
        "layer_meta": layer_meta,
        "satellite": {
            "configured": satellite_provider_configured(),
            "provider_url": SATELLITE_TILE_URL,
        },
    }
    (RUNTIME_DIR / "runtime_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    for layer_id, fc in capas.items():
        (RUNTIME_DIR / f"{layer_id}.geojson").write_text(json.dumps(fc, indent=2, ensure_ascii=False), encoding="utf-8")
    (RUNTIME_DIR / "preferences.json").write_text(json.dumps(config["preferences"], indent=2, ensure_ascii=False), encoding="utf-8")


def _runtime_layers_payload(capas: Dict, layer_labels: Optional[Dict] = None) -> Dict:
    payload = {}
    defs = obtener_layer_defs()
    labels = layer_labels or {}
    for layer_id, fc in capas.items():
        payload[layer_id] = {
            "id": layer_id,
            "label": labels.get(layer_id, defs.get(layer_id, {}).get("label", layer_id.title())),
            "url": f"/runtime/{layer_id}.geojson",
            "feature_count": len(fc.get("features", [])),
        }
    return payload


def _runtime_map_payload(mapa: Optional[dict]) -> Optional[dict]:
    if not mapa:
        return None
    viewer_mode = str(mapa.get("viewer_mode") or ("pmtiles_vector" if mapa.get("format") == "pmtiles" else "xyz")).strip()
    map_id = str(mapa.get("id", "")).strip()
    return {
        "id": map_id,
        "name": mapa.get("name", "Mapa offline"),
        "description": mapa.get("description", ""),
        "format": mapa.get("format", ""),
        "viewer_mode": viewer_mode,
        "schema": mapa.get("schema", ""),
        "centerLat": float(mapa.get("center_lat", 19.4326)),
        "centerLon": float(mapa.get("center_lon", -99.1332)),
        "minZoom": int(mapa.get("min_zoom", 0)),
        "maxZoom": int(mapa.get("max_zoom", 14)),
        "zoomInicial": int(mapa.get("default_zoom", mapa.get("min_zoom", 0))),
        "bounds": mapa.get("bounds", []),
        "pmtilesUrl": f"{_viewer_url()}maps/{map_id}/archive.pmtiles" if mapa.get("pmtiles_path") else "",
        "hasPmtiles": bool(mapa.get("pmtiles_path")),
        "hasRasterTiles": bool(mapa.get("tiles_path")),
        "pmtilesMetadata": mapa.get("pmtiles_metadata", {}),
    }


def _empty_layers() -> Dict:
    return {layer_id: {"type": "FeatureCollection", "features": []} for layer_id in obtener_layer_defs()}


def _get_map(map_id: str) -> Optional[dict]:
    for item in get_offline_maps_service().list_installed_maps():
        if item.get("id") == map_id:
            return item
    return None


class TacticalMapHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_HEAD(self):
        self._dispatch(head_only=True)

    def do_GET(self):
        self._dispatch(head_only=False)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/runtime/feature":
            self._handle_feature_post()
            return
        if path == "/runtime/satellite/estimate":
            self._handle_satellite_estimate()
            return
        if path == "/runtime/satellite/download":
            self._handle_satellite_download()
            return
        if path == "/runtime/satellite/cancel":
            self._handle_satellite_cancel()
            return
        if path == "/runtime/satellite/status":
            self._handle_satellite_status()
            return
        if path == "/runtime/feature/update":
            self._handle_feature_update()
            return
        if path == "/runtime/feature/delete":
            self._handle_feature_delete()
            return
        if path != "/runtime/preferences":
            self.send_error(404, "Ruta POST no soportada")
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            prefs = save_viewer_preferences(payload if isinstance(payload, dict) else {})
            _write_runtime(_get_map(_ViewerState.active_map_id) if _ViewerState.active_map_id else None)
            body = json.dumps({"ok": True, "preferences": prefs}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _handle_feature_post(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Payload inválido.")
            mapa = _get_map(_ViewerState.active_map_id) if _ViewerState.active_map_id else None
            if not mapa:
                raise ValueError("No hay mapa activo.")
            kind = str(payload.get("kind", "")).strip().lower()
            created = self._create_feature_from_payload(mapa["id"], kind, payload)
            _write_runtime(_get_map(_ViewerState.active_map_id))
            body = json.dumps({"ok": True, "feature": created}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _json_payload(self) -> Dict:
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Payload inválido.")
        return payload

    def _send_json(self, status_code: int, payload: Dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_satellite_estimate(self):
        try:
            payload = self._json_payload()
            bounds = dict(payload.get("bounds") or {})
            min_zoom = int(payload.get("min_zoom"))
            max_zoom = int(payload.get("max_zoom"))
            estimate = get_satellite_tile_service().estimate(bounds, min_zoom, max_zoom)
            self._send_json(200, {"ok": True, "estimate": estimate, "availability": satellite_availability(bounds, min_zoom)})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _handle_satellite_download(self):
        try:
            payload = self._json_payload()
            bounds = dict(payload.get("bounds") or {})
            min_zoom = int(payload.get("min_zoom"))
            max_zoom = int(payload.get("max_zoom"))
            task = get_satellite_tile_service().start_download(bounds, min_zoom, max_zoom)
            self._send_json(200, {"ok": True, "task": task})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _handle_satellite_cancel(self):
        cancelled = get_satellite_tile_service().cancel_download()
        self._send_json(200, {"ok": True, "cancelled": cancelled, "task": get_satellite_tile_service().task_status()})

    def _handle_satellite_status(self):
        try:
            payload = self._json_payload()
            bounds = payload.get("bounds")
            zoom = payload.get("zoom")
            availability = satellite_availability(bounds, int(zoom)) if bounds is not None and zoom is not None else satellite_availability()
            self._send_json(200, {"ok": True, "availability": availability, "task": get_satellite_tile_service().task_status()})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _handle_feature_update(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Payload inválido.")
            mapa = _get_map(_ViewerState.active_map_id) if _ViewerState.active_map_id else None
            if not mapa:
                raise ValueError("No hay mapa activo.")
            feature = self._update_feature_from_payload(mapa["id"], payload)
            _write_runtime(_get_map(_ViewerState.active_map_id))
            body = json.dumps({"ok": True, "feature": feature}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _handle_feature_delete(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Payload inválido.")
            mapa = _get_map(_ViewerState.active_map_id) if _ViewerState.active_map_id else None
            if not mapa:
                raise ValueError("No hay mapa activo.")
            feature_id = str(payload.get("feature_id", "")).strip()
            layer_id = str(payload.get("layer_id", "")).strip() or None
            if not feature_id:
                raise ValueError("Falta feature_id.")
            deleted = eliminar_feature(mapa["id"], feature_id, layer_id)
            if not deleted:
                raise ValueError("No se encontró el elemento a eliminar.")
            _write_runtime(_get_map(_ViewerState.active_map_id))
            body = json.dumps({"ok": True, "deleted": True}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _create_feature_from_payload(self, mapa_id: str, kind: str, payload: Dict):
        if kind == "point":
            coords = payload.get("coordinates") or {}
            return agregar_punto_tactico(
                mapa_id=mapa_id,
                nombre=str(payload.get("nombre", "")).strip(),
                categoria=str(payload.get("categoria", "punto_interes")).strip(),
                descripcion=str(payload.get("descripcion", "")).strip(),
                riesgo=str(payload.get("riesgo", "medio")).strip(),
                lat=float(coords.get("lat")),
                lon=float(coords.get("lon")),
                layer_id=str(payload.get("layer_id", "puntos")).strip() or "puntos",
                emoji=str(payload.get("emoji", "")).strip(),
                icon_label=str(payload.get("icon_label", "")).strip(),
            )
        if kind == "route":
            return agregar_ruta_tactica(
                mapa_id=mapa_id,
                nombre=str(payload.get("nombre", "")).strip(),
                descripcion=str(payload.get("descripcion", "")).strip(),
                categoria=str(payload.get("categoria", "ruta")).strip(),
                coordenadas_lon_lat=list(payload.get("coordinates") or []),
                layer_id=str(payload.get("layer_id", "rutas")).strip() or "rutas",
            )
        if kind == "polygon":
            return agregar_poligono_tactico(
                mapa_id=mapa_id,
                nombre=str(payload.get("nombre", "")).strip(),
                descripcion=str(payload.get("descripcion", "")).strip(),
                riesgo=str(payload.get("riesgo", "alto")).strip(),
                coordenadas_lon_lat=list(payload.get("coordinates") or []),
                layer_id=str(payload.get("layer_id", "poligonos")).strip() or "poligonos",
                categoria=str(payload.get("categoria", "zona_riesgo")).strip() or "zona_riesgo",
            )
        raise ValueError("Tipo de operación no soportado.")

    def _update_feature_from_payload(self, mapa_id: str, payload: Dict):
        feature_id = str(payload.get("feature_id", "")).strip()
        layer_id = str(payload.get("layer_id", "")).strip()
        if not feature_id or not layer_id:
            raise ValueError("Faltan datos del elemento.")
        current = obtener_feature(mapa_id, feature_id)
        if not current:
            raise ValueError("No se encontró el elemento a editar.")
        current_layer_id = str((current.get("properties", {}) or {}).get("tipo", "")).strip() or layer_id

        kind = str(payload.get("kind", "")).strip().lower()
        props = dict(current.get("properties", {}) or {})
        geometry = dict(current.get("geometry", {}) or {})
        props["nombre"] = str(payload.get("nombre", props.get("nombre", ""))).strip()
        props["categoria"] = str(payload.get("categoria", props.get("categoria", ""))).strip()
        props["descripcion"] = str(payload.get("descripcion", props.get("descripcion", ""))).strip()
        props["riesgo"] = str(payload.get("riesgo", props.get("riesgo", ""))).strip().lower()
        props["tipo"] = layer_id
        props["estado"] = str(payload.get("estado", props.get("estado", "activo"))).strip()
        props["notas"] = str(payload.get("notas", props.get("notas", ""))).strip()
        props["emoji"] = str(payload.get("emoji", props.get("emoji", ""))).strip()
        props["icon_label"] = str(payload.get("icon_label", props.get("icon_label", ""))).strip()
        props["fecha_actualizacion"] = _utcnow()

        if kind == "point":
            coords = payload.get("coordinates") or {}
            geometry = {
                "type": "Point",
                "coordinates": [float(coords.get("lon")), float(coords.get("lat"))],
            }
        elif kind == "route":
            geometry = {
                "type": "LineString",
                "coordinates": [[float(lon), float(lat)] for lon, lat in list(payload.get("coordinates") or [])],
            }
        elif kind == "polygon":
            coords = [[float(lon), float(lat)] for lon, lat in list(payload.get("coordinates") or [])]
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            geometry = {
                "type": "Polygon",
                "coordinates": [coords],
            }
        else:
            raise ValueError("Tipo de edición no soportado.")

        updated = {
            "type": "Feature",
            "properties": props,
            "geometry": geometry,
        }
        if current_layer_id != layer_id:
            eliminar_feature(mapa_id, feature_id, current_layer_id)
            return guardar_feature(mapa_id, layer_id, updated)
        return actualizar_feature(mapa_id, feature_id, layer_id, updated)

    def _dispatch(self, head_only: bool):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/":
            path = "/index.html"

        if path.startswith("/runtime/satellite_tile/"):
            self._serve_satellite_tile(path, head_only=head_only)
            return

        if path.startswith("/runtime/"):
            self._serve_file(RUNTIME_DIR / path.replace("/runtime/", "", 1), head_only=head_only)
            return

        if path.startswith("/maps/") and path.endswith("/archive.pmtiles"):
            map_id = path.strip("/").split("/")[1]
            mapa = _get_map(map_id)
            pmtiles_path = Path(str((mapa or {}).get("pmtiles_path", "")))
            if not mapa or not pmtiles_path.exists():
                self.send_error(404, "Mapa PMTiles no disponible")
                return
            self._serve_file(pmtiles_path, head_only=head_only, allow_range=True)
            return

        target = MAP_UI_DIR / path.lstrip("/")
        self._serve_file(target, head_only=head_only)

    def _serve_file(self, path: Path, head_only: bool = False, allow_range: bool = False) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404, "Archivo no encontrado")
            return

        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "application/octet-stream"
        file_size = path.stat().st_size
        range_header = self.headers.get("Range", "") if allow_range else ""
        start = 0
        end = file_size - 1
        status_code = 200

        if range_header.startswith("bytes="):
            try:
                raw_start, raw_end = range_header.replace("bytes=", "", 1).split("-", 1)
                if raw_start.strip():
                    start = int(raw_start)
                if raw_end.strip():
                    end = min(int(raw_end), file_size - 1)
                if start > end or start >= file_size:
                    self.send_error(416, "Rango inválido")
                    return
                status_code = 206
            except Exception:
                self.send_error(416, "Rango inválido")
                return

        length = end - start + 1
        self.send_response(status_code)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        if allow_range:
            self.send_header("Accept-Ranges", "bytes")
        if status_code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()

        if head_only:
            return

        with path.open("rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _serve_satellite_tile(self, path: str, head_only: bool = False) -> None:
        try:
            parts = path.replace("/runtime/satellite_tile/", "", 1).split("/")
            if len(parts) != 3:
                self.send_error(404, "Tile satelital inválido")
                return
            z = int(parts[0])
            x = int(parts[1])
            y_part = parts[2].split(".", 1)[0]
            y = int(y_part)
            content, content_type, _mode = get_satellite_tile_service().get_tile_bytes(z, x, y)
            if content is None:
                self.send_error(404, "Tile satelital no disponible")
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type or "image/jpeg")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head_only:
                self.wfile.write(content)
        except Exception:
            self.send_error(404, "Tile satelital no disponible")
