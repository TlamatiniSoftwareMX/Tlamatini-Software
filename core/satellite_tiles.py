from __future__ import annotations

import math
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import requests

from core.memoria import DATA_DIR


# WARNING:
# La descarga offline de tiles debe usarse solo con proveedores que permitan
# almacenamiento local o caché offline según sus términos de uso.
SATELLITE_TILE_URL = (
    os.environ.get("TLAMATINI_SATELLITE_TILE_URL", "").strip()
    or "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
SATELLITE_TILE_TIMEOUT = int(os.environ.get("TLAMATINI_SATELLITE_TIMEOUT", "20") or 20)
SATELLITE_TILE_EXTENSION = os.environ.get("TLAMATINI_SATELLITE_TILE_EXTENSION", "jpg").strip().lower() or "jpg"
SATELLITE_PROVIDER_ID = os.environ.get("TLAMATINI_SATELLITE_PROVIDER_ID", "").strip().lower() or (
    (urlparse(SATELLITE_TILE_URL).hostname or "default").replace(".", "-")
)
SATELLITE_DOWNLOAD_LIMIT = int(os.environ.get("TLAMATINI_SATELLITE_MAX_TILES", "2000") or 2000)
SATELLITE_ESTIMATED_TILE_BYTES = int(os.environ.get("TLAMATINI_SATELLITE_ESTIMATED_TILE_BYTES", "220000") or 220000)
SATELLITE_ROOT = DATA_DIR / "local_maps" / "satellite_tiles"
SATELLITE_PROVIDER_ROOT = SATELLITE_ROOT / SATELLITE_PROVIDER_ID


def satellite_provider_configured() -> bool:
    return bool(SATELLITE_TILE_URL and "{z}" in SATELLITE_TILE_URL and "{x}" in SATELLITE_TILE_URL and "{y}" in SATELLITE_TILE_URL)


def is_internet_available(hostname: Optional[str] = None, port: int = 443, timeout: float = 1.5) -> bool:
    target = hostname or (urlparse(SATELLITE_TILE_URL).hostname or "")
    if not target:
        return False
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return True
    except OSError:
        return False


def _clamp_lat(lat: float) -> float:
    return max(min(float(lat), 85.05112878), -85.05112878)


def _clamp_lon(lon: float) -> float:
    value = float(lon)
    while value < -180.0:
        value += 360.0
    while value > 180.0:
        value -= 360.0
    return value


def latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    lat = _clamp_lat(lat)
    lon = _clamp_lon(lon)
    z = int(zoom)
    scale = 2**z
    x = int((lon + 180.0) / 360.0 * scale)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * scale)
    x = max(0, min(scale - 1, x))
    y = max(0, min(scale - 1, y))
    return x, y


def tile_bounds_for_view(bounds: Dict, zoom: int) -> tuple[int, int, int, int]:
    west = _clamp_lon(bounds.get("west", -180.0))
    south = _clamp_lat(bounds.get("south", -85.0))
    east = _clamp_lon(bounds.get("east", 180.0))
    north = _clamp_lat(bounds.get("north", 85.0))
    if east < west:
        east = west
    if north < south:
        north = south
    min_x, max_y = latlon_to_tile(south, west, zoom)
    max_x, min_y = latlon_to_tile(north, east, zoom)
    if max_x < min_x:
        min_x, max_x = max_x, min_x
    if max_y < min_y:
        min_y, max_y = max_y, min_y
    return min_x, max_x, min_y, max_y


def estimate_tile_count(bounds: Dict, min_zoom: int, max_zoom: int) -> Dict:
    details = []
    total = 0
    for zoom in range(int(min_zoom), int(max_zoom) + 1):
        min_x, max_x, min_y, max_y = tile_bounds_for_view(bounds, zoom)
        count = max(0, (max_x - min_x + 1)) * max(0, (max_y - min_y + 1))
        details.append({"zoom": zoom, "count": count})
        total += count
    return {
        "min_zoom": int(min_zoom),
        "max_zoom": int(max_zoom),
        "total_tiles": total,
        "estimated_bytes": total * SATELLITE_ESTIMATED_TILE_BYTES,
        "by_zoom": details,
        "limit": SATELLITE_DOWNLOAD_LIMIT,
    }


def get_satellite_tile_path(z: int, x: int, y: int) -> Path:
    return SATELLITE_PROVIDER_ROOT / str(int(z)) / str(int(x)) / f"{int(y)}.{SATELLITE_TILE_EXTENSION}"


def _ensure_tile_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_satellite_tile_url(z: int, x: int, y: int) -> str:
    return SATELLITE_TILE_URL.format(z=int(z), x=int(x), y=int(y))


def has_offline_satellite_tiles(bounds: Dict, zoom: int) -> Dict:
    min_x, max_x, min_y, max_y = tile_bounds_for_view(bounds, zoom)
    total = 0
    available = 0
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            total += 1
            if get_satellite_tile_path(zoom, x, y).exists():
                available += 1
    return {
        "zoom": int(zoom),
        "available": available,
        "total": total,
        "complete": total > 0 and available == total,
        "partial": available > 0 and available < total,
    }


@dataclass
class SatelliteDownloadTask:
    status: str = "idle"
    current: int = 0
    total: int = 0
    percent: float = 0.0
    error: str = ""
    message: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    thread: Optional[threading.Thread] = None
    cancel_event: Optional[threading.Event] = None

    def snapshot(self) -> Dict:
        return {
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "percent": self.percent,
            "error": self.error,
            "message": self.message,
            "downloaded": self.downloaded,
            "skipped": self.skipped,
            "failed": self.failed,
        }


class SatelliteTileService:
    def __init__(self):
        self._lock = threading.RLock()
        self._task = SatelliteDownloadTask()
        SATELLITE_PROVIDER_ROOT.mkdir(parents=True, exist_ok=True)

    def task_status(self) -> Dict:
        with self._lock:
            return self._task.snapshot()

    def estimate(self, bounds: Dict, min_zoom: int, max_zoom: int) -> Dict:
        return estimate_tile_count(bounds, min_zoom, max_zoom)

    def start_download(self, bounds: Dict, min_zoom: int, max_zoom: int) -> Dict:
        if not satellite_provider_configured():
            raise ValueError("No hay proveedor satelital configurado.")
        estimate = self.estimate(bounds, min_zoom, max_zoom)
        if estimate["total_tiles"] > SATELLITE_DOWNLOAD_LIMIT:
            raise ValueError("La zona seleccionada es demasiado grande. Acerca el mapa o reduce el rango de zoom.")
        with self._lock:
            if self._task.status in {"queued", "downloading"}:
                return self._task.snapshot()
            task = SatelliteDownloadTask(
                status="queued",
                total=estimate["total_tiles"],
                message="Preparando descarga satelital...",
                started_at=time.time(),
                cancel_event=threading.Event(),
            )
            worker = threading.Thread(target=self._download_worker, args=(task, bounds, min_zoom, max_zoom), daemon=True)
            task.thread = worker
            self._task = task
            worker.start()
            return task.snapshot()

    def cancel_download(self) -> bool:
        with self._lock:
            if self._task.cancel_event and self._task.status in {"queued", "downloading"}:
                self._task.cancel_event.set()
                self._task.status = "cancelled"
                self._task.message = "Descarga cancelada."
                return True
            return False

    def _download_worker(self, task: SatelliteDownloadTask, bounds: Dict, min_zoom: int, max_zoom: int) -> None:
        task.status = "downloading"
        task.message = "Descargando satélite offline..."
        try:
            with requests.Session() as session:
                session.headers.update({"User-Agent": "TLAMATINI-Satellite/1.0"})
                for zoom in range(int(min_zoom), int(max_zoom) + 1):
                    min_x, max_x, min_y, max_y = tile_bounds_for_view(bounds, zoom)
                    for x in range(min_x, max_x + 1):
                        for y in range(min_y, max_y + 1):
                            if task.cancel_event and task.cancel_event.is_set():
                                task.status = "cancelled"
                                task.message = "Descarga cancelada."
                                return
                            path = get_satellite_tile_path(zoom, x, y)
                            if path.exists():
                                task.skipped += 1
                                task.current += 1
                                task.percent = round((task.current / max(1, task.total)) * 100, 2)
                                continue
                            try:
                                response = session.get(build_satellite_tile_url(zoom, x, y), timeout=SATELLITE_TILE_TIMEOUT)
                                response.raise_for_status()
                                _ensure_tile_parent(path)
                                path.write_bytes(response.content)
                                task.downloaded += 1
                            except Exception:
                                task.failed += 1
                            task.current += 1
                            task.percent = round((task.current / max(1, task.total)) * 100, 2)
                            task.message = f"Descargando satélite offline: {task.current} / {task.total} tiles"
            task.status = "completed" if task.failed == 0 else "partial"
            task.message = "Satélite offline descargado correctamente." if task.failed == 0 else "Algunos tiles no pudieron descargarse. La vista offline puede estar incompleta."
        except Exception as exc:
            task.status = "error"
            task.error = str(exc)
            task.message = str(exc)
        finally:
            task.finished_at = time.time()

    def get_tile_bytes(self, z: int, x: int, y: int) -> tuple[Optional[bytes], str, str]:
        path = get_satellite_tile_path(z, x, y)
        if path.exists():
            return path.read_bytes(), _content_type_for_ext(path.suffix.lower()), "offline"
        if not satellite_provider_configured():
            return None, "", "unconfigured"
        if not is_internet_available():
            return None, "", "offline_unavailable"
        try:
            response = requests.get(build_satellite_tile_url(z, x, y), timeout=SATELLITE_TILE_TIMEOUT)
            response.raise_for_status()
            content = response.content
            _ensure_tile_parent(path)
            path.write_bytes(content)
            content_type = response.headers.get("Content-Type", "").strip() or _content_type_for_ext(path.suffix.lower())
            return content, content_type, "online"
        except Exception:
            return None, "", "error"


def _content_type_for_ext(ext: str) -> str:
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def satellite_availability(bounds: Optional[Dict] = None, zoom: Optional[int] = None) -> Dict:
    configured = satellite_provider_configured()
    online = configured and is_internet_available()
    payload = {
        "configured": configured,
        "online": online,
        "provider_id": SATELLITE_PROVIDER_ID,
        "download_limit": SATELLITE_DOWNLOAD_LIMIT,
    }
    if bounds is not None and zoom is not None:
        coverage = has_offline_satellite_tiles(bounds, int(zoom))
        payload["coverage"] = coverage
        if coverage["complete"]:
            payload["mode"] = "offline"
            payload["message"] = "Vista satelital offline disponible para esta zona."
        elif online:
            payload["mode"] = "online"
            payload["message"] = "Satélite online."
        elif coverage["partial"]:
            payload["mode"] = "partial"
            payload["message"] = "Vista satelital offline parcialmente disponible para esta zona."
        else:
            payload["mode"] = "unavailable"
            payload["message"] = "La vista satelital requiere internet o un paquete satelital descargado para esta zona."
    return payload


_SERVICE: Optional[SatelliteTileService] = None


def get_satellite_tile_service() -> SatelliteTileService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = SatelliteTileService()
    return _SERVICE
