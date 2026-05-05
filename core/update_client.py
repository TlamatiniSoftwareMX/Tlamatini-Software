from __future__ import annotations

import hashlib
import platform as platform_lib
import re
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

import requests

from core.installation_identity import get_app_version
from core.local_license_store import DEFAULT_UPDATE_DOWNLOAD_DIR, describe_backend_configuration, get_backend_url, normalize_backend_url
from core.logs import registrar_log


class UpdateClientError(RuntimeError):
    pass


class UpdateBackendNotConfiguredError(UpdateClientError):
    pass


class UpdateBackendUnavailableError(UpdateClientError):
    pass


def detect_platform() -> str:
    system_name = platform_lib.system().strip().lower()
    if system_name == "darwin":
        return "macos"
    if system_name.startswith("win"):
        return "windows"
    return "linux"


def current_version() -> str:
    return get_app_version()


def compute_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if chunk:
                digest.update(chunk)
    return digest.hexdigest()


def _safe_filename(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip())
    return normalized.strip(".-") or "tlamatini-update.bin"


def _allow_download_url(download_url: str, backend_url: str) -> None:
    parsed = urlparse(download_url)
    backend = urlparse(backend_url)
    if parsed.scheme == "https":
        return
    if parsed.scheme != "http":
        raise UpdateClientError("La URL de descarga usa un esquema no soportado.")
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.hostname in local_hosts and backend.hostname in local_hosts:
        return
    raise UpdateClientError("No se permiten descargas HTTP inseguras fuera de entorno local.")


def _is_local_backend_url(url: str) -> bool:
    host = (urlparse(str(url or "")).hostname or "").strip().lower()
    return host in {"localhost", "127.0.0.1", "::1"}


class UpdateClient:
    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout

    def backend_url(self) -> str:
        url = get_backend_url()
        if not url:
            cfg = describe_backend_configuration()
            if cfg.get("blocked_reason"):
                raise UpdateBackendNotConfiguredError(str(cfg["blocked_reason"]))
            raise UpdateBackendNotConfiguredError("No hay backend configurado para revisar actualizaciones.")
        return normalize_backend_url(url).rstrip("/")

    def _request(self, method: str, path: str, *, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.backend_url()}{path}"
        try:
            response = requests.request(method, url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            if _is_local_backend_url(url):
                raise UpdateBackendUnavailableError(
                    "El backend local de actualizaciones no está disponible en 127.0.0.1:8000."
                ) from exc
            raise UpdateClientError(f"No se pudo revisar actualizaciones: {exc}") from exc

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail") or response.text
            except Exception:
                detail = response.text
            raise UpdateClientError(str(detail).strip() or f"Error HTTP {response.status_code}")

        try:
            return response.json()
        except Exception as exc:
            raise UpdateClientError("El backend devolvió metadata de actualización inválida.") from exc

    def check_for_updates(self, *, version: str | None = None, platform_name: str | None = None, channel: str = "stable") -> Dict[str, Any]:
        payload = self._request(
            "GET",
            "/updates/check",
            params={
                "current_version": (version or current_version()).strip() or "local",
                "platform": (platform_name or detect_platform()).strip(),
                "channel": (channel or "stable").strip(),
            },
        )
        registrar_log("dashboard", "Consulta de actualizaciones completada.", "updates")
        return payload

    def open_download_url(self, download_url: str) -> str:
        url = str(download_url or "").strip()
        if not url:
            raise UpdateClientError("La release no incluye download_url.")
        _allow_download_url(url, self.backend_url())
        webbrowser.open(url)
        registrar_log("dashboard", f"URL de descarga abierta: {url}", "updates")
        return url

    def download_update(self, update_payload: Dict[str, Any], *, destination_dir: str | Path | None = None) -> Dict[str, Any]:
        download_url = str(update_payload.get("download_url", "")).strip()
        expected_sha256 = str(update_payload.get("sha256", "")).strip().lower()
        version = str(update_payload.get("latest_version", "")).strip() or "unknown"
        platform_name = str(update_payload.get("platform", "")).strip() or detect_platform()
        if not download_url:
            raise UpdateClientError("La release no incluye download_url.")
        if len(expected_sha256) != 64:
            raise UpdateClientError("La release no incluye un sha256 válido.")

        backend_url = self.backend_url()
        _allow_download_url(download_url, backend_url)

        target_dir = Path(destination_dir or DEFAULT_UPDATE_DOWNLOAD_DIR).expanduser().resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(urlparse(download_url).path).suffix or ".bin"
        filename = _safe_filename(f"tlamatini-{platform_name}-{version}{suffix}")
        target_path = target_dir / filename

        try:
            response = requests.get(download_url, stream=True, timeout=max(self.timeout, 60.0))
            response.raise_for_status()
        except requests.RequestException as exc:
            raise UpdateClientError(f"No se pudo descargar el paquete: {exc}") from exc

        with tempfile.NamedTemporaryFile(
            "wb",
            dir=str(target_dir),
            prefix=f"{filename}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
            handle.flush()

        actual_sha256 = compute_sha256(temp_path)
        if actual_sha256 != expected_sha256:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise UpdateClientError(
                f"El sha256 no coincide. esperado={expected_sha256} obtenido={actual_sha256}"
            )

        temp_path.replace(target_path)
        registrar_log("dashboard", f"Paquete de actualización descargado y validado: {target_path}", "updates")
        return {
            "path": str(target_path),
            "sha256": actual_sha256,
            "version": version,
            "platform": platform_name,
        }
