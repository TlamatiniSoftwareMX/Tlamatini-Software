import json
import os
import re
import shutil
import threading
import time
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from core.logs import registrar_log
from core.memoria import APP_DIR, DATA_DIR, obtener_seccion, guardar_seccion

try:
    from pmtiles.reader import MmapSource, Reader
except Exception:
    MmapSource = None
    Reader = None

MAPS_ROOT = DATA_DIR / "local_maps"
PMTILES_DIR = MAPS_ROOT / "pmtiles"
PACKAGES_DIR = MAPS_ROOT / "packages"
INSTALLED_DIR = MAPS_ROOT / "installed"
CATALOG_DIR = MAPS_ROOT / "catalog"
TEMP_DIR = MAPS_ROOT / "temp"
METADATA_DIR = MAPS_ROOT / "metadata"
STYLES_DIR = MAPS_ROOT / "styles"
ASSETS_DIR = MAPS_ROOT / "assets"
OVERLAYS_DIR = MAPS_ROOT / "overlays"
CATALOG_CACHE_SECONDS = int(os.environ.get("TLAMATINI_MAPS_CATALOG_CACHE_SECONDS", "300") or 300)
REMOTE_READY_TIMEOUT = float(os.environ.get("TLAMATINI_MAPS_READY_TIMEOUT", "6") or 6)
REMOTE_READY_RANGE_BYTES = int(os.environ.get("TLAMATINI_MAPS_READY_RANGE_BYTES", "1") or 1)

BUILTIN_CATALOG = APP_DIR / "assets" / "offline_maps" / "catalog.json"
BUILTIN_STYLES_DIR = APP_DIR / "assets" / "offline_maps" / "styles"
def _utcnow() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _state_default() -> Dict:
    return {
        "version": 2,
        "mapa_activo_id": "",
        "mapas": [],
    }


def _safe_slug(value: str) -> str:
    raw = "".join(ch.lower() if ch.isalnum() else "-" for ch in (value or "").strip())
    compact = "-".join(part for part in raw.split("-") if part)
    return compact or f"mapa-{int(time.time())}"


def _format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(max(0, size))
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024.0
    return f"{size} B"


def _detect_xyz_zoom_range(folder: Path) -> Tuple[int, int, str]:
    zooms = []
    tile_format = "png"
    for child in folder.iterdir():
        if child.is_dir():
            try:
                zooms.append(int(child.name))
            except Exception:
                continue
    if not zooms:
        return 0, 5, tile_format
    min_zoom, max_zoom = min(zooms), max(zooms)
    for z_dir in folder.iterdir():
        if not z_dir.is_dir():
            continue
        for x_dir in z_dir.iterdir():
            if not x_dir.is_dir():
                continue
            for tile in x_dir.iterdir():
                if tile.is_file() and tile.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    tile_format = tile.suffix.lower().lstrip(".")
                    return min_zoom, max_zoom, tile_format
    return min_zoom, max_zoom, tile_format


def _load_json(path: Path, default):
    if not path.exists():
        return deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(default)


def _write_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _merge_map(base: Dict, overlay: Dict) -> Dict:
    result = dict(base)
    result.update({k: v for k, v in overlay.items() if v is not None})
    return result


@dataclass
class DownloadTask:
    map_id: str
    status: str = "idle"
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    error: str = ""
    temp_path: str = ""
    started_at: str = ""
    finished_at: str = ""
    thread: Optional[threading.Thread] = None
    cancel_event: Optional[threading.Event] = None

    def snapshot(self) -> Dict:
        return {
            "map_id": self.map_id,
            "status": self.status,
            "progress": self.progress,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "error": self.error,
            "temp_path": self.temp_path,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class OfflineMapsService:
    def __init__(self):
        self._tasks: Dict[str, DownloadTask] = {}
        self._lock = threading.RLock()
        self._catalog_cache: Dict = {}
        self._catalog_cache_at = 0.0
        self.ensure_structure()

    def ensure_structure(self) -> None:
        for path in [MAPS_ROOT, PMTILES_DIR, PACKAGES_DIR, INSTALLED_DIR, CATALOG_DIR, TEMP_DIR, METADATA_DIR, STYLES_DIR, ASSETS_DIR, OVERLAYS_DIR]:
            path.mkdir(parents=True, exist_ok=True)
        if BUILTIN_STYLES_DIR.exists():
            for style_file in BUILTIN_STYLES_DIR.glob("*.json"):
                target = STYLES_DIR / style_file.name
                if not target.exists():
                    shutil.copy2(style_file, target)
        state = self._load_state()
        self._save_state(state)

    def _load_state(self) -> Dict:
        repo = obtener_seccion("mapas_repo", {})
        if not isinstance(repo, dict):
            return _state_default()
        base = _state_default()
        if not isinstance(repo.get("mapas", []), list):
            repo["mapas"] = []
        for key, value in base.items():
            if key not in repo:
                repo[key] = value
        return repo

    def _save_state(self, state: Dict) -> None:
        guardar_seccion("mapas_repo", state)

    def _load_builtin_catalog(self) -> Dict:
        return _load_json(BUILTIN_CATALOG, {"maps": []})

    def _load_override_catalog(self) -> Dict:
        override_path = CATALOG_DIR / "catalog.json"
        data = _load_json(override_path, {"maps": []})
        if not isinstance(data.get("maps", []), list):
            data["maps"] = []
        return data

    def _load_remote_catalog(self) -> Dict:
        remote_catalog_url = os.environ.get("TLAMATINI_MAPS_CATALOG_URL", "").strip()
        if not remote_catalog_url:
            return {"maps": []}
        cache_path = CATALOG_DIR / "remote_catalog.json"
        try:
            response = requests.get(remote_catalog_url, timeout=15)
            if response.ok:
                data = response.json()
                if not isinstance(data.get("maps", []), list):
                    data["maps"] = []
                _write_json(cache_path, data)
                return data
        except Exception:
            pass
        return _load_json(cache_path, {"maps": []})

    def refresh_catalog(self, force: bool = False) -> Dict:
        now = time.time()
        if not force and self._catalog_cache and (now - self._catalog_cache_at) < CATALOG_CACHE_SECONDS:
            return deepcopy(self._catalog_cache)
        self.ensure_structure()
        builtin = self._load_builtin_catalog()
        override = self._load_override_catalog()
        remote = self._load_remote_catalog()
        merged = {}
        for item in builtin.get("maps", []):
            if isinstance(item, dict) and item.get("id"):
                merged[item["id"]] = dict(item)
        for item in remote.get("maps", []):
            if isinstance(item, dict) and item.get("id"):
                merged[item["id"]] = _merge_map(merged.get(item["id"], {}), item)
        for item in override.get("maps", []):
            if isinstance(item, dict) and item.get("id"):
                merged[item["id"]] = _merge_map(merged.get(item["id"], {}), item)
        catalog = {"updated_at": _utcnow(), "maps": list(merged.values())}
        self._catalog_cache = deepcopy(catalog)
        self._catalog_cache_at = now
        _write_json(CATALOG_DIR / "resolved_catalog.json", catalog)
        return catalog

    def _catalog_map(self, map_id: str) -> Optional[Dict]:
        catalog = self.refresh_catalog()
        for item in catalog.get("maps", []):
            if item.get("id") == map_id:
                return dict(item)
        return None

    def _installed_map(self, map_id: str) -> Optional[Dict]:
        state = self._load_state()
        for item in state.get("mapas", []):
            if item.get("id") == map_id:
                return dict(item)
        return None

    def list_installed_maps(self) -> List[Dict]:
        state = self._load_state()
        results = []
        active_id = state.get("mapa_activo_id", "")
        for item in state.get("mapas", []):
            entry = dict(item)
            entry["is_active"] = entry.get("id") == active_id
            entry["status"] = "installed"
            entry["human_size"] = _format_bytes(int(entry.get("size_bytes", 0) or 0))
            results.append(entry)
        return results

    def list_catalog_maps(self) -> List[Dict]:
        catalog = self.refresh_catalog()
        installed = {item["id"]: item for item in self.list_installed_maps() if item.get("id")}
        active_id = self.get_active_map_id()
        results = []
        for item in catalog.get("maps", []):
            merged = dict(item)
            merged["human_size"] = _format_bytes(int(item.get("size_bytes", 0) or 0))
            is_installed = item.get("id") in installed
            if item.get("id") in installed:
                merged["status"] = "installed"
                merged["is_active"] = item.get("id") == active_id
                merged["installed"] = installed[item["id"]]
            else:
                merged["status"] = "not_downloaded"
                merged["is_active"] = False
            task = self.get_download_status(item.get("id", ""))
            task_status = task.get("status")
            active_task_states = {"queued", "preparing", "waiting_remote", "downloading", "extracting"}
            terminal_task_states = {"error", "cancelled"}
            if task_status in active_task_states or (not is_installed and task_status in terminal_task_states):
                merged["status"] = task["status"]
                merged["download"] = task
            results.append(merged)
        return results

    def get_active_map_id(self) -> str:
        return str(self._load_state().get("mapa_activo_id", "") or "")

    def get_active_map(self) -> Optional[Dict]:
        active_id = self.get_active_map_id()
        if not active_id:
            return None
        return self._installed_map(active_id)

    def set_active_map(self, map_id: str) -> bool:
        state = self._load_state()
        if not any(item.get("id") == map_id for item in state.get("mapas", [])):
            return False
        state["mapa_activo_id"] = map_id
        self._save_state(state)
        registrar_log("sistema", f"Mapa offline activo: {map_id}", "mapas_offline")
        return True

    def delete_map(self, map_id: str) -> bool:
        state = self._load_state()
        installed = state.get("mapas", [])
        target = next((item for item in installed if item.get("id") == map_id), None)
        if not target:
            return False
        install_dir = Path(target.get("installed_path", ""))
        package_path = Path(target.get("package_path", ""))
        for path in [install_dir, package_path]:
            try:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
            except Exception:
                pass
        state["mapas"] = [item for item in installed if item.get("id") != map_id]
        if state.get("mapa_activo_id") == map_id:
            state["mapa_activo_id"] = state["mapas"][0]["id"] if state["mapas"] else ""
        self._save_state(state)
        registrar_log("sistema", f"Mapa offline eliminado: {map_id}", "mapas_offline")
        return True

    def import_xyz_folder(
        self,
        folder_path: str,
        name: str,
        region: str = "manual",
        description: str = "",
        center_lat: float = 19.4326,
        center_lon: float = -99.1332,
        min_zoom: Optional[int] = None,
        max_zoom: Optional[int] = None,
        default_zoom: Optional[int] = None,
    ) -> Dict:
        source = Path(folder_path).expanduser().resolve()
        if not source.exists() or not source.is_dir():
            raise ValueError("La carpeta de tiles XYZ no existe.")
        detected_min, detected_max, tile_format = _detect_xyz_zoom_range(source)
        min_zoom = detected_min if min_zoom is None else int(min_zoom)
        max_zoom = detected_max if max_zoom is None else int(max_zoom)
        if default_zoom is None:
            default_zoom = min(max(min_zoom + 1, min_zoom), max_zoom)
        map_id = _safe_slug(name)
        install_dir = INSTALLED_DIR / map_id
        if install_dir.exists():
            raise ValueError("Ya existe un mapa instalado con ese identificador.")
        shutil.copytree(source, install_dir / "tiles")
        metadata = {
            "id": map_id,
            "name": name.strip(),
            "region": region.strip() or "manual",
            "description": description.strip(),
            "version": _utcnow(),
            "format": "xyz_folder",
            "tile_format": tile_format,
            "center_lat": float(center_lat),
            "center_lon": float(center_lon),
            "min_zoom": int(min_zoom),
            "max_zoom": int(max_zoom),
            "default_zoom": int(default_zoom),
            "installed_path": str(install_dir),
            "tiles_path": str(install_dir / "tiles"),
            "package_path": "",
            "size_bytes": self._dir_size(install_dir),
            "installed_at": _utcnow(),
            "source_url": str(source),
            "source_type": "manual_xyz",
        }
        self._register_installed_map(metadata)
        return metadata

    def _register_installed_map(self, metadata: Dict) -> None:
        state = self._load_state()
        maps = [item for item in state.get("mapas", []) if item.get("id") != metadata.get("id")]
        maps.append(metadata)
        state["mapas"] = maps
        if not state.get("mapa_activo_id"):
            state["mapa_activo_id"] = metadata["id"]
        self._save_state(state)
        _write_json(METADATA_DIR / f"{metadata['id']}.json", metadata)
        registrar_log("sistema", f"Mapa offline instalado: {metadata['name']}", "mapas_offline")

    def _dir_size(self, folder: Path) -> int:
        total = 0
        if not folder.exists():
            return total
        for path in folder.rglob("*"):
            if path.is_file():
                try:
                    total += path.stat().st_size
                except Exception:
                    pass
        return total

    def get_download_status(self, map_id: str) -> Dict:
        with self._lock:
            task = self._tasks.get(map_id)
            return task.snapshot() if task else {"map_id": map_id, "status": "idle", "progress": 0.0, "downloaded_bytes": 0, "total_bytes": 0, "error": ""}

    def cancel_download(self, map_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(map_id)
            if not task or not task.cancel_event:
                return False
            task.cancel_event.set()
            task.status = "cancelled"
            return True

    def start_download(self, map_id: str) -> DownloadTask:
        entry = self._catalog_map(map_id)
        if not entry:
            raise ValueError("Mapa no encontrado en el catálogo.")
        if self._installed_map(map_id):
            raise ValueError("El mapa ya está instalado.")
        with self._lock:
            existing = self._tasks.get(map_id)
            if existing and existing.status in {"queued", "preparing", "waiting_remote", "downloading", "extracting"}:
                return existing
            task = DownloadTask(
                map_id=map_id,
                status="queued",
                progress=0.0,
                started_at=_utcnow(),
                cancel_event=threading.Event(),
            )
            worker = threading.Thread(target=self._download_worker, args=(entry, task), daemon=True)
            task.thread = worker
            self._tasks[map_id] = task
            worker.start()
            return task

    def _download_worker(self, entry: Dict, task: DownloadTask) -> None:
        map_id = entry["id"]
        temp_path = TEMP_DIR / f"{map_id}.part"
        final_package = PACKAGES_DIR / entry.get("destination_file", f"{map_id}.zip")
        task.temp_path = str(temp_path)
        try:
            if final_package.exists() and final_package.is_file() and final_package.stat().st_size > 0:
                task.status = "extracting"
                task.progress = 100.0
                task.total_bytes = final_package.stat().st_size
                task.downloaded_bytes = task.total_bytes
            else:
                source_url = self._prepare_download_url(entry, task)
                task.status = "downloading"
                self._download_to_temp(source_url, temp_path, task)
                if task.cancel_event and task.cancel_event.is_set():
                    raise RuntimeError("Descarga cancelada.")
                final_package.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(temp_path), str(final_package))
            task.status = "extracting"
            metadata = self._install_package(entry, final_package)
            self._register_installed_map(metadata)
            task.progress = 100.0
            task.downloaded_bytes = task.total_bytes or task.downloaded_bytes
            task.finished_at = _utcnow()
            task.status = "installed"
        except Exception as exc:
            task.error = str(exc)
            task.finished_at = _utcnow()
            if task.status != "cancelled":
                task.status = "error"
            registrar_log("error", f"Error descargando mapa {map_id}: {exc}", "mapas_offline")
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def _resolve_url(self, raw_url: str) -> str:
        value = (raw_url or "").strip()
        if value.startswith("asset://"):
            return str((APP_DIR / "assets" / value.replace("asset://", "", 1)).resolve())
        return value

    def _prepare_download_url(self, entry: Dict, task: DownloadTask) -> str:
        generator = entry.get("generator")
        if not isinstance(generator, dict):
            return self._resolve_url(entry.get("url", ""))
        kind = str(generator.get("kind", "")).strip().lower()
        if kind == "bbbike_extract":
            return self._prepare_bbbike_extract_url(entry, task, generator)
        raise ValueError(f"Generador de descarga no soportado: {kind}")

    def _prepare_bbbike_extract_url(self, entry: Dict, task: DownloadTask, generator: Dict) -> str:
        request_url = str(generator.get("request_url") or "https://extract.bbbike.org/").strip()
        params = {
            "format": str(generator.get("request_format") or "pmtiles-shortbread.zip").strip(),
            "city": str(generator.get("city") or entry.get("id") or "tlamatini-region").strip(),
            "email": str(generator.get("email") or "nobody").strip(),
            "as": str(generator.get("estimated_size_mb") or max(1, round(float(entry.get("size_bytes", 0) or 0) / (1024 * 1024)))).strip(),
            "pg": str(generator.get("polygon_ratio") or "1").strip(),
            "submit": "extract",
        }
        coords = generator.get("coords")
        encoded = []
        if isinstance(coords, list) and coords:
            for point in coords:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    encoded.append(f"{point[0]},{point[1]}")
        if encoded:
            params["coords"] = "|".join(encoded)
        else:
            bbox = generator.get("bbox") or {}
            bbox_params = {
                "sw_lng": str(bbox.get("sw_lng", "")).strip(),
                "sw_lat": str(bbox.get("sw_lat", "")).strip(),
                "ne_lng": str(bbox.get("ne_lng", "")).strip(),
                "ne_lat": str(bbox.get("ne_lat", "")).strip(),
            }
            if not all(bbox_params.values()):
                raise RuntimeError("El mapa no tiene un bbox ni un polígono válido para solicitar el extracto remoto.")
            params.update(bbox_params)

        task.status = "preparing"
        task.progress = 1.0
        response = requests.get(request_url, params=params, timeout=60)
        response.raise_for_status()
        html = response.text or ""
        download_url = self._extract_bbbike_download_url(html)
        if not download_url:
            raise RuntimeError("BBBike no devolvió un enlace de descarga utilizable para este extracto.")

        wait_seconds = int(generator.get("wait_timeout_seconds", 900) or 900)
        poll_interval = int(generator.get("poll_interval_seconds", 10) or 10)
        if int(generator.get("estimated_size_mb") or 0) <= 25:
            poll_interval = min(poll_interval, 4)
        deadline = time.time() + max(30, wait_seconds)
        task.status = "waiting_remote"
        task.progress = 3.0
        registrar_log(
            "sistema",
            f"Esperando extracto BBBike para {entry.get('id')}: intervalo={poll_interval}s timeout={wait_seconds}s",
            "mapas_offline",
        )

        while time.time() < deadline:
            if task.cancel_event and task.cancel_event.is_set():
                task.status = "cancelled"
                raise RuntimeError("Descarga cancelada.")
            try:
                if self._remote_download_ready(download_url):
                    return download_url
            except Exception:
                pass
            task.progress = min(15.0, round(task.progress + 0.5, 2))
            time.sleep(max(3, poll_interval))
        raise RuntimeError("El extracto remoto no quedó listo dentro del tiempo de espera.")

    def _extract_bbbike_download_url(self, html: str) -> str:
        text = html or ""
        patterns = [
            r"bbbike_extract_download_url:\s*(https?://[^\s<]+)",
            r'href="(https?://[^"]+\.zip[^"]*)"',
            r"href='(https?://[^']+\.zip[^']*)'",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _remote_download_ready(self, download_url: str) -> bool:
        try:
            head = requests.head(download_url, allow_redirects=True, timeout=REMOTE_READY_TIMEOUT)
        except requests.RequestException:
            head = None
        if head is not None and head.status_code in {200, 206}:
            return True
        if head is not None and head.status_code in {404, 410}:
            return False

        headers = {}
        if REMOTE_READY_RANGE_BYTES > 0:
            headers["Range"] = f"bytes=0-{max(0, REMOTE_READY_RANGE_BYTES - 1)}"
        try:
            with requests.get(download_url, stream=True, allow_redirects=True, timeout=REMOTE_READY_TIMEOUT, headers=headers) as probe:
                if probe.status_code not in {200, 206}:
                    return False
                for _chunk in probe.iter_content(chunk_size=max(1, REMOTE_READY_RANGE_BYTES)):
                    break
                return True
        except requests.RequestException:
            return False

    def _download_to_temp(self, source_url: str, temp_path: Path, task: DownloadTask) -> None:
        if source_url.startswith("http://") or source_url.startswith("https://"):
            self._download_http(source_url, temp_path, task)
            return
        if source_url.startswith("file://"):
            source = Path(urlparse(source_url).path)
        else:
            source = Path(source_url)
        self._copy_local_file(source, temp_path, task)

    def _copy_local_file(self, source: Path, temp_path: Path, task: DownloadTask) -> None:
        source = source.expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"No existe el paquete de mapa: {source}")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        total = source.stat().st_size
        task.total_bytes = total
        copied = temp_path.stat().st_size if temp_path.exists() else 0
        mode = "ab" if copied > 0 else "wb"
        with source.open("rb") as src, temp_path.open(mode) as dst:
            if copied > 0:
                src.seek(copied)
            while True:
                if task.cancel_event and task.cancel_event.is_set():
                    task.status = "cancelled"
                    raise RuntimeError("Descarga cancelada.")
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
                copied += len(chunk)
                task.downloaded_bytes = copied
                task.progress = round((copied / total) * 100, 2) if total else 0.0

    def _download_http(self, source_url: str, temp_path: Path, task: DownloadTask) -> None:
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        headers = {}
        downloaded = temp_path.stat().st_size if temp_path.exists() else 0
        if downloaded > 0:
            headers["Range"] = f"bytes={downloaded}-"
        with requests.get(source_url, stream=True, timeout=30, headers=headers) as response:
            if response.status_code not in {200, 206}:
                raise RuntimeError(f"Descarga falló con HTTP {response.status_code}")
            total = int(response.headers.get("Content-Length", "0") or 0)
            if response.status_code == 206 and downloaded > 0:
                total += downloaded
            task.total_bytes = total
            mode = "ab" if downloaded > 0 and response.status_code == 206 else "wb"
            if mode == "wb":
                downloaded = 0
            with temp_path.open(mode) as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if task.cancel_event and task.cancel_event.is_set():
                        task.status = "cancelled"
                        raise RuntimeError("Descarga cancelada.")
                    if not chunk:
                        continue
                    output.write(chunk)
                    downloaded += len(chunk)
                    task.downloaded_bytes = downloaded
                    task.progress = round((downloaded / total) * 100, 2) if total else 0.0

    def _install_package(self, entry: Dict, package_path: Path) -> Dict:
        format_id = str(entry.get("format", "xyz_zip") or "xyz_zip").strip().lower()
        if format_id in {"pmtiles_zip", "pmtiles"}:
            return self._install_pmtiles_package(entry, package_path, format_id)
        if format_id != "xyz_zip":
            raise ValueError(f"Formato aún no soportado por el instalador offline: {format_id}")
        install_dir = INSTALLED_DIR / entry["id"]
        if install_dir.exists():
            shutil.rmtree(install_dir)
        install_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(package_path) as zf:
            zf.extractall(install_dir)
        metadata_path = install_dir / "metadata.json"
        if not metadata_path.exists():
            raise ValueError("El paquete descargado no contiene metadata.json")
        metadata = _load_json(metadata_path, {})
        tiles_root = str(metadata.get("tiles_root", "tiles")).strip() or "tiles"
        tiles_path = install_dir / tiles_root
        if not tiles_path.exists():
            raise ValueError("El paquete descargado no contiene la carpeta de tiles esperada")
        installed = {
            "id": entry["id"],
            "name": metadata.get("name") or entry.get("name") or entry["id"],
            "region": metadata.get("region") or entry.get("region", ""),
            "description": metadata.get("description") or entry.get("description", ""),
            "version": metadata.get("version") or entry.get("version", ""),
            "format": format_id,
            "tile_format": metadata.get("tile_format", "png"),
            "center_lat": float(metadata.get("center_lat", entry.get("center_lat", 19.4326))),
            "center_lon": float(metadata.get("center_lon", entry.get("center_lon", -99.1332))),
            "min_zoom": int(metadata.get("min_zoom", entry.get("min_zoom", 0))),
            "max_zoom": int(metadata.get("max_zoom", entry.get("max_zoom", 5))),
            "default_zoom": int(metadata.get("default_zoom", entry.get("default_zoom", 2))),
            "installed_path": str(install_dir),
            "tiles_path": str(tiles_path),
            "package_path": str(package_path),
            "size_bytes": self._dir_size(install_dir),
            "installed_at": _utcnow(),
            "source_url": entry.get("url", ""),
            "source_type": "catalog_download",
            "catalog_id": entry["id"],
            "state": "installed",
        }
        return installed

    def _install_pmtiles_package(self, entry: Dict, package_path: Path, format_id: str) -> Dict:
        install_dir = INSTALLED_DIR / entry["id"]
        if install_dir.exists():
            shutil.rmtree(install_dir)
        install_dir.mkdir(parents=True, exist_ok=True)

        if format_id == "pmtiles_zip":
            with zipfile.ZipFile(package_path) as zf:
                zf.extractall(install_dir)
            pmtiles_path = self._find_pmtiles_file(install_dir)
        else:
            pmtiles_name = entry.get("destination_file") or package_path.name
            if not str(pmtiles_name).lower().endswith(".pmtiles"):
                pmtiles_name = f"{entry['id']}.pmtiles"
            pmtiles_path = install_dir / Path(str(pmtiles_name)).name
            shutil.copy2(package_path, pmtiles_path)

        if not pmtiles_path or not pmtiles_path.exists():
            raise ValueError("El paquete no contiene un archivo .pmtiles utilizable.")

        package_metadata = _load_json(install_dir / "metadata.json", {})
        pmtiles_info = self._safe_pmtiles_info(entry, package_metadata, pmtiles_path)

        installed = {
            "id": entry["id"],
            "name": package_metadata.get("name") or entry.get("name") or entry["id"],
            "region": package_metadata.get("region") or entry.get("region", ""),
            "description": package_metadata.get("description") or entry.get("description", ""),
            "version": package_metadata.get("version") or entry.get("version", ""),
            "format": "pmtiles",
            "tile_format": pmtiles_info.get("tile_format", ""),
            "tile_type": pmtiles_info.get("tile_type", ""),
            "schema": entry.get("schema", package_metadata.get("schema", "shortbread")),
            "center_lat": float(package_metadata.get("center_lat", entry.get("center_lat", pmtiles_info.get("center_lat", 19.4326)))),
            "center_lon": float(package_metadata.get("center_lon", entry.get("center_lon", pmtiles_info.get("center_lon", -99.1332)))),
            "min_zoom": int(package_metadata.get("min_zoom", entry.get("min_zoom", pmtiles_info.get("min_zoom", 0)))),
            "max_zoom": int(package_metadata.get("max_zoom", entry.get("max_zoom", pmtiles_info.get("max_zoom", 14)))),
            "default_zoom": int(package_metadata.get("default_zoom", entry.get("default_zoom", pmtiles_info.get("center_zoom", 10)))),
            "installed_path": str(install_dir),
            "tiles_path": "",
            "pmtiles_path": str(pmtiles_path),
            "package_path": str(package_path),
            "size_bytes": self._dir_size(install_dir),
            "installed_at": _utcnow(),
            "source_url": entry.get("url", ""),
            "source_type": "catalog_download",
            "catalog_id": entry["id"],
            "state": "installed",
            "viewer_mode": pmtiles_info.get("viewer_mode", "pmtiles_vector"),
            "bounds": pmtiles_info.get("bounds", []),
            "pmtiles_metadata": pmtiles_info.get("metadata", {}),
        }
        return installed

    def _safe_pmtiles_info(self, entry: Dict, package_metadata: Dict, pmtiles_path: Path) -> Dict:
        try:
            return self._read_pmtiles_info(pmtiles_path)
        except Exception as exc:
            registrar_log(
                "warning",
                f"No se pudieron leer metadatos PMTiles para {entry.get('id', pmtiles_path.name)}; se usarán valores de respaldo. Detalle: {exc}",
                "mapas_offline",
            )
            tile_type = str(package_metadata.get("tile_type") or entry.get("tile_type") or "").strip().upper()
            schema = str(entry.get("schema") or package_metadata.get("schema") or "").strip().lower()
            if not tile_type:
                tile_type = "MVT" if schema == "shortbread" else "UNKNOWN"
            viewer_mode = "pmtiles_vector" if tile_type == "MVT" else "pmtiles_raster"
            tile_format_map = {
                "PNG": "png",
                "JPEG": "jpg",
                "JPG": "jpg",
                "WEBP": "webp",
                "AVIF": "avif",
                "MVT": "pbf",
            }
            return {
                "tile_type": tile_type,
                "tile_format": tile_format_map.get(tile_type, str(package_metadata.get("tile_format") or entry.get("tile_format") or "").strip().lower()),
                "viewer_mode": viewer_mode,
                "metadata": package_metadata if isinstance(package_metadata, dict) else {},
                "min_zoom": int(package_metadata.get("min_zoom", entry.get("min_zoom", 0))),
                "max_zoom": int(package_metadata.get("max_zoom", entry.get("max_zoom", 14))),
                "center_zoom": int(package_metadata.get("default_zoom", entry.get("default_zoom", 10))),
                "center_lon": float(package_metadata.get("center_lon", entry.get("center_lon", -99.1332))),
                "center_lat": float(package_metadata.get("center_lat", entry.get("center_lat", 19.4326))),
                "bounds": package_metadata.get("bounds", entry.get("bounds", [])) or [],
            }

    def _find_pmtiles_file(self, folder: Path) -> Path:
        candidates = sorted(folder.rglob("*.pmtiles"))
        if not candidates:
            raise ValueError("No se encontró ningún archivo .pmtiles dentro del paquete.")
        return candidates[0]

    def _read_pmtiles_info(self, pmtiles_path: Path) -> Dict:
        if Reader is None or MmapSource is None:
            raise ValueError("La librería Python 'pmtiles' no está disponible en este entorno.")

        with pmtiles_path.open("rb") as fh:
            reader = Reader(MmapSource(fh))
            header = reader.header()
            try:
                metadata = reader.metadata()
            except Exception:
                metadata = {}

        tile_type = getattr(header.get("tile_type"), "name", str(header.get("tile_type")))
        viewer_mode = "pmtiles_vector" if tile_type == "MVT" else "pmtiles_raster"
        tile_format_map = {
            "PNG": "png",
            "JPEG": "jpg",
            "WEBP": "webp",
            "AVIF": "avif",
            "MVT": "pbf",
        }

        return {
            "tile_type": tile_type,
            "tile_format": tile_format_map.get(tile_type, tile_type.lower()),
            "viewer_mode": viewer_mode,
            "metadata": metadata,
            "min_zoom": int(header.get("min_zoom", 0)),
            "max_zoom": int(header.get("max_zoom", 14)),
            "center_zoom": int(header.get("center_zoom", 10)),
            "center_lon": float(header.get("center_lon_e7", 0) / 1e7),
            "center_lat": float(header.get("center_lat_e7", 0) / 1e7),
            "bounds": [
                float(header.get("min_lon_e7", 0) / 1e7),
                float(header.get("min_lat_e7", 0) / 1e7),
                float(header.get("max_lon_e7", 0) / 1e7),
                float(header.get("max_lat_e7", 0) / 1e7),
            ],
        }


_SERVICE: Optional[OfflineMapsService] = None


def get_offline_maps_service() -> OfflineMapsService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = OfflineMapsService()
    return _SERVICE
