from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import tarfile
import tempfile
import threading
import time
import http.client
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.logs import registrar_log
from core.memoria import APP_DIR
from core.path_manager import offline_library_dir
from core.platform_utils import current_platform
from core.texto import normalizar_texto


CATALOG_ASSET_PATH = APP_DIR / "assets" / "offline_library" / "catalog.json"
LOCAL_LIBRARY_DIR = offline_library_dir()
CATALOG_DIR = LOCAL_LIBRARY_DIR / "catalog"
ZIM_DIR = LOCAL_LIBRARY_DIR / "zim"
TEMP_DIR = LOCAL_LIBRARY_DIR / "temp"
METADATA_DIR = LOCAL_LIBRARY_DIR / "metadata"
CACHE_DIR = LOCAL_LIBRARY_DIR / "cache"
INDEXES_DIR = LOCAL_LIBRARY_DIR / "indexes"
FAVORITES_DIR = LOCAL_LIBRARY_DIR / "favorites"
RUNTIME_DIR = LOCAL_LIBRARY_DIR / "runtime"
KIWIX_DIR = RUNTIME_DIR / "kiwix"
KIWIX_BIN_DIR = KIWIX_DIR / "bin"
STATE_PATH = METADATA_DIR / "library_state.json"
CATALOG_CACHE_PATH = CATALOG_DIR / "resolved_catalog.json"


def _runtime_download_url() -> str:
    custom = os.environ.get("TLAMATINI_KIWIX_RUNTIME_URL", "").strip()
    if custom:
        return custom
    info = current_platform()
    if info.os_name == "linux" and info.architecture == "x86_64":
        return "https://download.kiwix.org/release/kiwix-tools/kiwix-tools_linux-x86_64.tar.gz"
    return ""

_STATE_LOCK = threading.RLock()
_SERVER_LOCK = threading.RLock()
_SERVER_STATE: Dict[str, object] = {
    "content_id": "",
    "process": None,
    "port": 0,
    "url": "",
}

ProgressCallback = Callable[[Dict[str, object]], None]


DEFAULT_STATE = {
    "installed": {},
    "downloads": {},
    "favorites": [],
    "last_opened": "",
    "reader": {
        "content_id": "",
        "url": "",
        "port": 0,
        "status": "inactivo",
        "last_error": "",
    },
    "runtime": {
        "kiwix_serve": "",
        "downloaded_at": "",
        "source": "",
    },
}


def _default_state() -> Dict:
    return json.loads(json.dumps(DEFAULT_STATE))


def _ensure_dirs() -> None:
    for ruta in (
        LOCAL_LIBRARY_DIR,
        CATALOG_DIR,
        ZIM_DIR,
        TEMP_DIR,
        METADATA_DIR,
        CACHE_DIR,
        INDEXES_DIR,
        FAVORITES_DIR,
        RUNTIME_DIR,
        KIWIX_DIR,
        KIWIX_BIN_DIR,
    ):
        ruta.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(ruta: Path, payload: Dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(ruta.parent)) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, ruta)


def _load_json(ruta: Path, default):
    try:
        if not ruta.exists():
            return default
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return default


def _now_label() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def load_state() -> Dict:
    _ensure_dirs()
    with _STATE_LOCK:
        state = _load_json(STATE_PATH, _default_state())
        for clave, valor in DEFAULT_STATE.items():
            if clave not in state:
                state[clave] = json.loads(json.dumps(valor))
        return state


def save_state(state: Dict) -> Dict:
    _ensure_dirs()
    with _STATE_LOCK:
        _atomic_write_json(STATE_PATH, state)
    return state


def _reconcile_state(state: Dict, entries: List[Dict]) -> Dict:
    by_id = {entry.get("id"): entry for entry in entries if entry.get("id")}
    changed = False

    for content_id, download in list(state.get("downloads", {}).items()):
        entry = by_id.get(content_id)
        if not entry:
            continue
        temp_path = _temp_path(entry)
        final_path = _final_path(entry)
        status = str(download.get("status", "") or "")
        if status in {"descargando", "instalando"} and not temp_path.exists() and not final_path.exists():
            download["status"] = "error"
            download["error"] = "La descarga anterior fue interrumpida y no dejó archivo temporal."
            changed = True

    for content_id, installed in list(state.get("installed", {}).items()):
        path = Path(installed.get("path", ""))
        if not path.exists():
            installed["status"] = "error"
            installed["verified_complete"] = False
            changed = True

    if changed:
        save_state(state)
    return state


def _merge_entry_status(entry: Dict, state: Dict) -> Dict:
    item = dict(entry)
    content_id = item["id"]
    installed = state.get("installed", {}).get(content_id)
    download = state.get("downloads", {}).get(content_id, {})
    favorites = set(state.get("favorites", []))
    reader = state.get("reader", {})

    status = "no_descargado"
    if download.get("status"):
        status = str(download.get("status"))
    elif installed and Path(installed.get("path", "")).exists():
        status = str(installed.get("status", "descargado"))

    if reader.get("content_id") == content_id and reader.get("status") == "lector_activo":
        status = "lector_activo"
    elif reader.get("content_id") == content_id and reader.get("status") == "lector_iniciando":
        status = "lector_iniciando"

    item["status"] = status
    item["favorite"] = content_id in favorites
    item["installed_path"] = installed.get("path", "") if installed else ""
    item["download_progress"] = download.get("progress", 0.0)
    item["download_error"] = download.get("error", "")
    item["downloaded_bytes"] = download.get("downloaded_bytes", 0)
    item["verified_complete"] = bool(installed.get("verified_complete", False)) if installed else False
    item["remote_size_bytes"] = int(installed.get("remote_size_bytes", 0) or 0) if installed else 0
    return item


def load_catalog() -> List[Dict]:
    _ensure_dirs()
    payload = _load_json(CATALOG_ASSET_PATH, {"entries": []})
    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    state = _reconcile_state(load_state(), entries)
    merged = [_merge_entry_status(entry, state) for entry in entries if isinstance(entry, dict) and entry.get("id")]
    _atomic_write_json(CATALOG_CACHE_PATH, {"generated_at": _now_label(), "entries": merged})
    return merged


def get_catalog_entry(content_id: str) -> Optional[Dict]:
    for entry in load_catalog():
        if entry.get("id") == content_id:
            return entry
    return None


def _searchable_text(entry: Dict) -> str:
    return " ".join(
        [
            str(entry.get("id", "")),
            str(entry.get("name", "")),
            str(entry.get("language", "")),
            str(entry.get("category", "")),
            str(entry.get("content_type", "")),
            str(entry.get("description", "")),
            str(entry.get("source", "")),
            " ".join(str(tag) for tag in entry.get("tags", []) or []),
        ]
    )


def search_catalog(query: str = "") -> List[Dict]:
    entries = load_catalog()
    query_n = normalizar_texto(query or "")
    if not query_n:
        return entries
    return [entry for entry in entries if query_n in normalizar_texto(_searchable_text(entry))]


def list_installed(query: str = "") -> List[Dict]:
    state = load_state()
    catalog_by_id = {entry["id"]: entry for entry in load_catalog()}
    items = []
    for content_id, installed in state.get("installed", {}).items():
        if not Path(installed.get("path", "")).exists():
            continue
        entry = dict(catalog_by_id.get(content_id, {}))
        entry.update(installed)
        entry["id"] = content_id
        entry["status"] = "instalado"
        entry["favorite"] = content_id in set(state.get("favorites", []))
        items.append(entry)
    query_n = normalizar_texto(query or "")
    if not query_n:
        return sorted(items, key=lambda item: (not item.get("favorite", False), str(item.get("name", ""))))
    return [
        item
        for item in items
        if query_n in normalizar_texto(_searchable_text(item))
    ]


def set_favorite(content_id: str, favorito: bool) -> Dict:
    state = load_state()
    favoritos = set(state.get("favorites", []))
    if favorito:
        favoritos.add(content_id)
    else:
        favoritos.discard(content_id)
    state["favorites"] = sorted(favoritos)
    save_state(state)
    return {"ok": True, "favorite": favorito}


def _filename_from_entry(entry: Dict) -> str:
    filename = (entry.get("filename") or "").strip()
    if filename:
        return filename
    parsed = urllib.parse.urlparse(entry["download_url"])
    guessed = Path(parsed.path).name or f"{entry['id']}.zim"
    return guessed


def _final_path(entry: Dict) -> Path:
    return ZIM_DIR / _filename_from_entry(entry)


def _temp_path(entry: Dict) -> Path:
    return TEMP_DIR / f"{_filename_from_entry(entry)}.part"


def _update_download_state(content_id: str, **changes) -> None:
    state = load_state()
    current = dict(state.get("downloads", {}).get(content_id, {}))
    current.update(changes)
    state.setdefault("downloads", {})[content_id] = current
    save_state(state)


def _clear_download_state(content_id: str) -> None:
    state = load_state()
    state.setdefault("downloads", {}).pop(content_id, None)
    save_state(state)


def _mark_installed(entry: Dict, final_path: Path) -> Dict:
    state = load_state()
    state.setdefault("installed", {})[entry["id"]] = {
        "path": str(final_path),
        "installed_at": _now_label(),
        "size_bytes": final_path.stat().st_size if final_path.exists() else 0,
        "filename": final_path.name,
        "format": entry.get("format", "zim"),
        "name": entry.get("name", entry["id"]),
        "language": entry.get("language", ""),
        "category": entry.get("category", ""),
        "source": entry.get("source", ""),
        "version": entry.get("version", ""),
        "status": "descargado",
        "verified_complete": False,
        "remote_size_bytes": 0,
    }
    state.setdefault("downloads", {}).pop(entry["id"], None)
    save_state(state)
    registrar_log("sistema", f"Contenido instalado: {entry.get('name', entry['id'])}", "biblioteca_offline")
    return {"ok": True, "path": str(final_path)}


def delete_content(content_id: str) -> Dict:
    state = load_state()
    installed = state.get("installed", {}).get(content_id)
    if not installed:
        return {"ok": False, "message": "El contenido no está instalado."}

    path = Path(installed.get("path", ""))
    if path.exists():
        try:
            path.unlink()
        except Exception as exc:
            return {"ok": False, "message": f"No se pudo eliminar el archivo: {exc}"}

    state.setdefault("installed", {}).pop(content_id, None)
    if state.get("last_opened") == content_id:
        state["last_opened"] = ""
    save_state(state)

    with _SERVER_LOCK:
        if _SERVER_STATE.get("content_id") == content_id:
            stop_reader()

    registrar_log("admin", f"Contenido eliminado: {content_id}", "biblioteca_offline")
    return {"ok": True, "message": "Contenido eliminado correctamente."}


def _read_content_length(headers) -> int:
    try:
        return int(headers.get("Content-Length", "0") or "0")
    except Exception:
        return 0


def probe_remote_file(url: str) -> Dict:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "TLAMATINI/6 Biblioteca"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return {
            "ok": True,
            "status": response.status,
            "content_length": _read_content_length(response.headers),
            "content_type": response.headers.get("Content-Type", ""),
            "accept_ranges": response.headers.get("Accept-Ranges", ""),
        }


def verify_installed_content(content_id: str, remote_check: bool = True) -> Dict:
    state = load_state()
    installed = state.get("installed", {}).get(content_id)
    entry = get_catalog_entry(content_id)
    if not installed or not entry:
        return {"ok": False, "message": "El contenido no está registrado como instalado."}

    path = Path(installed.get("path", ""))
    if not path.exists():
        installed["status"] = "error"
        installed["verified_complete"] = False
        save_state(state)
        return {"ok": False, "message": "El archivo ZIM no existe en disco."}

    local_size = path.stat().st_size
    remote_size = int(installed.get("remote_size_bytes", 0) or 0)
    if remote_check or remote_size <= 0:
        try:
            probe = probe_remote_file(entry["download_url"])
            remote_size = int(probe.get("content_length", 0) or 0)
            installed["remote_size_bytes"] = remote_size
        except Exception as exc:
            if remote_size <= 0:
                installed["status"] = "error"
                installed["verified_complete"] = False
                save_state(state)
                return {"ok": False, "message": f"No se pudo verificar el tamaño remoto: {exc}"}

    if remote_size > 0 and local_size != remote_size:
        installed["status"] = "error"
        installed["verified_complete"] = False
        save_state(state)
        return {
            "ok": False,
            "message": f"Archivo incompleto o inconsistente. Local: {local_size} bytes, remoto: {remote_size} bytes.",
            "local_size": local_size,
            "remote_size": remote_size,
        }

    installed["verified_complete"] = True
    installed["status"] = "listo_para_abrir"
    save_state(state)
    return {"ok": True, "message": "Archivo verificado y listo para abrir.", "local_size": local_size, "remote_size": remote_size}


def download_content(content_id: str, progress_callback: Optional[ProgressCallback] = None, stop_event: Optional[threading.Event] = None) -> Dict:
    entry = get_catalog_entry(content_id)
    if not entry:
        return {"ok": False, "message": "No se encontró la entrada del catálogo."}

    final_path = _final_path(entry)
    temp_path = _temp_path(entry)
    expected_size = 0
    accept_ranges = ""

    try:
        remote_probe = probe_remote_file(entry["download_url"])
        expected_size = int(remote_probe.get("content_length", 0) or 0)
        accept_ranges = str(remote_probe.get("accept_ranges", "") or "")
    except Exception as exc:
        return {"ok": False, "message": f"No se pudo verificar la descarga remota: {exc}"}

    if final_path.exists() and final_path.stat().st_size > 0:
        state = load_state()
        state.setdefault("installed", {}).setdefault(entry["id"], {"path": str(final_path)})
        state["installed"][entry["id"]]["remote_size_bytes"] = expected_size
        save_state(state)
        verified = verify_installed_content(content_id, remote_check=False)
        if verified.get("ok"):
            return {"ok": True, "message": "El contenido ya estaba instalado y verificado.", "path": str(final_path)}
        try:
            final_path.unlink()
        except Exception:
            pass

    downloaded_bytes = temp_path.stat().st_size if temp_path.exists() else 0
    headers = {"User-Agent": "TLAMATINI/6 Biblioteca"}
    if downloaded_bytes > 0 and accept_ranges.lower() == "bytes":
        headers["Range"] = f"bytes={downloaded_bytes}-"
    elif downloaded_bytes > 0 and temp_path.exists():
        temp_path.unlink()
        downloaded_bytes = 0

    request = urllib.request.Request(entry["download_url"], headers=headers)
    _update_download_state(
        content_id,
        status="descargando",
        started_at=_now_label(),
        downloaded_bytes=downloaded_bytes,
        total_bytes=expected_size,
        progress=0.0,
        error="",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            partial_supported = response.getcode() == 206
            if downloaded_bytes and not partial_supported:
                downloaded_bytes = 0
                if temp_path.exists():
                    temp_path.unlink()
                _update_download_state(content_id, downloaded_bytes=0)

            total_bytes = _read_content_length(response.headers)
            if partial_supported:
                total_bytes += downloaded_bytes

            mode = "ab" if downloaded_bytes and partial_supported else "wb"
            with open(temp_path, mode) as destino:
                while True:
                    if stop_event and stop_event.is_set():
                        _update_download_state(content_id, status="cancelado")
                        return {"ok": False, "message": "Descarga cancelada."}
                    bloque = response.read(1024 * 256)
                    if not bloque:
                        break
                    destino.write(bloque)
                    downloaded_bytes += len(bloque)
                    progress = (downloaded_bytes / total_bytes) if total_bytes else 0.0
                    payload = {
                        "status": "descargando",
                        "downloaded_bytes": downloaded_bytes,
                        "total_bytes": total_bytes,
                        "progress": progress,
                    }
                    _update_download_state(content_id, **payload)
                    if progress_callback:
                        progress_callback(payload)

        _update_download_state(content_id, status="instalando", progress=1.0, downloaded_bytes=downloaded_bytes, total_bytes=total_bytes)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temp_path, final_path)
        _mark_installed(entry, final_path)
        state = load_state()
        state["installed"][entry["id"]]["remote_size_bytes"] = expected_size
        state["installed"][entry["id"]]["status"] = "descargado"
        save_state(state)
        verified = verify_installed_content(content_id, remote_check=False)
        if not verified.get("ok"):
            _update_download_state(content_id, status="error", error=verified.get("message", "Error de verificación"))
            return {"ok": False, "message": verified.get("message", "Error de verificación del archivo descargado.")}
        _clear_download_state(content_id)
        if progress_callback:
            progress_callback(
                {
                    "content_id": content_id,
                    "status": "listo_para_abrir",
                    "downloaded_bytes": final_path.stat().st_size,
                    "total_bytes": final_path.stat().st_size,
                    "progress": 1.0,
                }
            )
        return {"ok": True, "message": "Contenido descargado, verificado y listo para abrir.", "path": str(final_path)}
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, RuntimeError) as exc:
        _update_download_state(content_id, status="error", error=str(exc))
        registrar_log("error", f"Descarga fallida {content_id}: {exc}", "biblioteca_offline")
        return {"ok": False, "message": str(exc)}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _kiwix_binary_candidates() -> List[Path]:
    env = os.environ.get("TLAMATINI_KIWIX_SERVE", "").strip() or os.environ.get("TLAMATINI_KIWIX_BIN", "").strip()
    binary_name = "kiwix-serve.exe" if os.name == "nt" else "kiwix-serve"
    candidates = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(KIWIX_BIN_DIR / binary_name)
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        if path_dir:
            candidates.append(Path(path_dir) / binary_name)
    return candidates


def _detect_kiwix_binary() -> Optional[Path]:
    for candidate in _kiwix_binary_candidates():
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    which_path = shutil.which("kiwix-serve")
    if which_path:
        return Path(which_path).resolve()
    return None


def _extract_archive(archive_path: Path, dest_dir: Path) -> None:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(dest_dir)
        return
    with tarfile.open(archive_path, "r:*") as tf:
        tf.extractall(dest_dir)


def ensure_kiwix_runtime(progress_callback: Optional[ProgressCallback] = None) -> Dict:
    binary = _detect_kiwix_binary()
    if binary:
        try:
            probe = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=10)
            if probe.returncode != 0:
                raise RuntimeError(probe.stderr.strip() or "kiwix-serve no respondió correctamente.")
        except Exception as exc:
            return {"ok": False, "message": f"Se encontró kiwix-serve pero no es usable: {exc}"}
        state = load_state()
        state["runtime"]["kiwix_serve"] = str(binary)
        if not state["runtime"].get("source"):
            state["runtime"]["source"] = "system"
        save_state(state)
        return {"ok": True, "path": str(binary), "source": state["runtime"].get("source", "system")}

    runtime_url = _runtime_download_url()
    if not runtime_url:
        return {
            "ok": False,
            "message": "No hay runtime Kiwix preconfigurado para esta plataforma. Define TLAMATINI_KIWIX_SERVE o TLAMATINI_KIWIX_RUNTIME_URL.",
        }

    archive_path = TEMP_DIR / Path(runtime_url).name
    part_path = TEMP_DIR / f"{archive_path.name}.part"
    downloaded_bytes = part_path.stat().st_size if part_path.exists() else 0
    headers = {"User-Agent": "TLAMATINI/6 Biblioteca"}
    if downloaded_bytes > 0:
        headers["Range"] = f"bytes={downloaded_bytes}-"

    request = urllib.request.Request(runtime_url, headers=headers)
    try:
        if progress_callback:
            progress_callback({"status": "runtime_descargando", "progress": 0.0, "message": "Descargando runtime Kiwix"})
        with urllib.request.urlopen(request, timeout=90) as response:
            partial_supported = response.getcode() == 206
            if downloaded_bytes and not partial_supported:
                downloaded_bytes = 0
                if part_path.exists():
                    part_path.unlink()
            total_bytes = _read_content_length(response.headers)
            if partial_supported:
                total_bytes += downloaded_bytes
            mode = "ab" if downloaded_bytes and partial_supported else "wb"
            with open(part_path, mode) as destino:
                while True:
                    bloque = response.read(1024 * 256)
                    if not bloque:
                        break
                    destino.write(bloque)
                    downloaded_bytes += len(bloque)
                    if progress_callback:
                        progress_callback(
                            {
                                "status": "runtime_descargando",
                                "downloaded_bytes": downloaded_bytes,
                                "total_bytes": total_bytes,
                                "progress": (downloaded_bytes / total_bytes) if total_bytes else 0.0,
                                "message": "Descargando runtime Kiwix",
                            }
                        )
        os.replace(part_path, archive_path)

        extract_dir = KIWIX_DIR / "extract"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        _extract_archive(archive_path, extract_dir)

        found_binary = None
        binary_name = "kiwix-serve.exe" if os.name == "nt" else "kiwix-serve"
        for candidate in extract_dir.rglob(binary_name):
            if candidate.is_file():
                found_binary = candidate
                break
        if found_binary is None:
            raise RuntimeError(f"No se encontró {binary_name} dentro del paquete descargado.")

        final_binary = KIWIX_BIN_DIR / binary_name
        shutil.copy2(found_binary, final_binary)
        if os.name != "nt":
            final_binary.chmod(0o755)
        probe = subprocess.run([str(final_binary), "--version"], capture_output=True, text=True, timeout=10)
        if probe.returncode != 0:
            raise RuntimeError(probe.stderr.strip() or "El runtime descargado de kiwix-serve no inició correctamente.")

        state = load_state()
        state["runtime"] = {
            "kiwix_serve": str(final_binary),
            "downloaded_at": _now_label(),
            "source": runtime_url,
        }
        save_state(state)
        registrar_log("sistema", "Runtime Kiwix listo para biblioteca offline", "biblioteca_offline")
        return {"ok": True, "path": str(final_binary), "source": runtime_url}
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, RuntimeError, tarfile.TarError, zipfile.BadZipFile) as exc:
        registrar_log("error", f"No se pudo preparar runtime Kiwix: {exc}", "biblioteca_offline")
        return {"ok": False, "message": str(exc)}


def _wait_for_port(port: int, timeout: float = 12.0) -> bool:
    limit = time.time() + timeout
    while time.time() < limit:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False


def _validate_reader_endpoint(url: str, timeout: float = 12.0) -> Dict:
    parsed = urllib.parse.urlparse(url)
    end = time.time() + timeout
    last_error = ""
    while time.time() < end:
        try:
            conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=2)
            conn.request("GET", parsed.path or "/")
            response = conn.getresponse()
            body = response.read(512)
            conn.close()
            if response.status in {200, 302, 303}:
                return {"ok": True, "status": response.status, "body": body.decode("utf-8", errors="ignore")}
            last_error = f"HTTP {response.status}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.3)
    return {"ok": False, "message": last_error or "El lector no respondió con contenido válido."}


def stop_reader() -> Dict:
    with _SERVER_LOCK:
        process = _SERVER_STATE.get("process")
        if isinstance(process, subprocess.Popen) and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        _SERVER_STATE.update({"content_id": "", "process": None, "port": 0, "url": ""})

    state = load_state()
    state["reader"] = {"content_id": "", "url": "", "port": 0, "status": "inactivo", "last_error": ""}
    save_state(state)
    return {"ok": True}


def start_reader(content_id: str, progress_callback: Optional[ProgressCallback] = None) -> Dict:
    installed = load_state().get("installed", {}).get(content_id)
    if not installed or not Path(installed.get("path", "")).exists():
        return {"ok": False, "message": "El contenido no está instalado."}
    if not installed.get("verified_complete"):
        verified = verify_installed_content(content_id, remote_check=True)
        if not verified.get("ok"):
            return verified

    with _SERVER_LOCK:
        current_process = _SERVER_STATE.get("process")
        if (
            _SERVER_STATE.get("content_id") == content_id
            and isinstance(current_process, subprocess.Popen)
            and current_process.poll() is None
        ):
            existing_url = str(_SERVER_STATE.get("url", ""))
            reader_ok = _validate_reader_endpoint(existing_url, timeout=2.0)
            if reader_ok.get("ok"):
                return {
                    "ok": True,
                    "url": existing_url,
                    "port": int(_SERVER_STATE.get("port", 0)),
                    "reused": True,
                }

    runtime = ensure_kiwix_runtime(progress_callback=progress_callback)
    if not runtime.get("ok"):
        return runtime

    kiwix_serve = Path(runtime["path"])
    stop_reader()
    state = load_state()
    state["reader"] = {"content_id": content_id, "url": "", "port": 0, "status": "lector_iniciando", "last_error": ""}
    save_state(state)
    port = _find_free_port()
    cmd = [str(kiwix_serve), "-p", str(port), installed["path"]]
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(LOCAL_LIBRARY_DIR),
        )
    except Exception as exc:
        return {"ok": False, "message": f"No se pudo lanzar kiwix-serve: {exc}"}

    if not _wait_for_port(port):
        try:
            process.terminate()
        except Exception:
            pass
        state = load_state()
        state["reader"] = {"content_id": content_id, "url": "", "port": port, "status": "error", "last_error": "Kiwix no respondió en el puerto asignado."}
        save_state(state)
        return {"ok": False, "message": "Kiwix no respondió al iniciar el lector."}

    url = f"http://127.0.0.1:{port}/"
    validation = _validate_reader_endpoint(url)
    if not validation.get("ok"):
        try:
            process.terminate()
        except Exception:
            pass
        state = load_state()
        state["reader"] = {"content_id": content_id, "url": url, "port": port, "status": "error", "last_error": validation.get("message", "No fue posible acceder al contenido servido.")}
        save_state(state)
        return {"ok": False, "message": f"El lector inició pero el contenido no fue accesible: {validation.get('message', 'sin detalle')}"}

    with _SERVER_LOCK:
        _SERVER_STATE.update({"content_id": content_id, "process": process, "port": port, "url": url})

    state = load_state()
    state["last_opened"] = content_id
    state["reader"] = {"content_id": content_id, "url": url, "port": port, "status": "lector_activo", "last_error": ""}
    save_state(state)
    registrar_log("sistema", f"Lector Kiwix iniciado para {content_id}", "biblioteca_offline")
    return {"ok": True, "url": url, "port": port}


def open_content(content_id: str, progress_callback: Optional[ProgressCallback] = None) -> Dict:
    current = reader_state()
    if current.get("content_id") != content_id or current.get("status") != "lector_activo":
        return {"ok": False, "message": "El lector no está listo para este contenido. Primero usa 'Iniciar lector'."}
    url = str(current.get("url", ""))
    validation = _validate_reader_endpoint(url, timeout=3.0)
    if not validation.get("ok"):
        return {"ok": False, "message": f"El lector no está accesible: {validation.get('message', 'sin detalle')}"}
    try:
        webbrowser.open(url)
    except Exception:
        pass
    return {"ok": True, "url": url, "port": current.get("port", 0)}


def reader_state() -> Dict:
    state = load_state().get("reader", {})
    with _SERVER_LOCK:
        process = _SERVER_STATE.get("process")
        if isinstance(process, subprocess.Popen) and process.poll() is not None:
            stop_reader()
            return {"content_id": "", "url": "", "port": 0, "status": "inactivo", "last_error": ""}
    return state
