from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from core.installation_identity import get_app_version
from core.license_validator import verify_signed_payload
from core.local_license_store import load_update_state, save_update_state
from core.logs import registrar_log
from core.update_client import (
    UpdateBackendNotConfiguredError,
    UpdateBackendUnavailableError,
    UpdateClient,
    UpdateClientError,
    compute_sha256,
    current_version,
    detect_platform,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expected_update_signature_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "purpose": "update_release",
        "version": str(payload.get("latest_version", "")).strip(),
        "platform": str(payload.get("platform", "")).strip().lower(),
        "channel": str(payload.get("channel", "")).strip().lower(),
        "download_url": str(payload.get("download_url", "")).strip(),
        "sha256": str(payload.get("sha256", "")).strip().lower(),
        "is_mandatory": bool(payload.get("is_mandatory", False)),
        "min_supported_version": str(payload.get("min_supported_version", "")).strip(),
    }


def _verify_update_signature(payload: Dict[str, Any]) -> None:
    if not payload.get("update_available"):
        return
    signature = str(payload.get("signature", "")).strip()
    if not signature:
        raise UpdateClientError("La metadata de actualización no incluye firma.")
    signed = verify_signed_payload(signature)
    expected = _expected_update_signature_payload(payload)
    normalized = {
        "purpose": str(signed.get("purpose", "")).strip(),
        "version": str(signed.get("version", "")).strip(),
        "platform": str(signed.get("platform", "")).strip().lower(),
        "channel": str(signed.get("channel", "")).strip().lower(),
        "download_url": str(signed.get("download_url", "")).strip(),
        "sha256": str(signed.get("sha256", "")).strip().lower(),
        "is_mandatory": bool(signed.get("is_mandatory", False)),
        "min_supported_version": str(signed.get("min_supported_version", "")).strip(),
    }
    if normalized != expected:
        raise UpdateClientError("La firma de la actualización no coincide con la metadata recibida.")


class UpdateChecker:
    def __init__(self, client: UpdateClient | None = None):
        self.client = client or UpdateClient()

    def local_state(self) -> Dict[str, Any]:
        state = load_update_state()
        return {
            "channel": str(state.get("channel", "stable")).strip() or "stable",
            "last_checked_at": str(state.get("last_checked_at", "")).strip(),
            "last_error": str(state.get("last_error", "")).strip(),
            "current_version": str(state.get("current_version", "")).strip() or current_version(),
            "platform": str(state.get("platform", "")).strip() or detect_platform(),
            "update_available": bool(state.get("update_available", False)),
            "latest_version": str(state.get("latest_version", "")).strip(),
            "is_mandatory": bool(state.get("is_mandatory", False)),
            "title": str(state.get("title", "")).strip(),
            "release_notes": str(state.get("release_notes", "")).strip(),
            "download_url": str(state.get("download_url", "")).strip(),
            "sha256": str(state.get("sha256", "")).strip(),
            "signature": str(state.get("signature", "")).strip(),
            "min_supported_version": str(state.get("min_supported_version", "")).strip(),
            "downloaded_path": str(state.get("downloaded_path", "")).strip(),
            "downloaded_sha256": str(state.get("downloaded_sha256", "")).strip(),
            "downloaded_at": str(state.get("downloaded_at", "")).strip(),
        }

    def save_state(self, values: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(values or {})
        payload.setdefault("current_version", get_app_version())
        payload.setdefault("platform", detect_platform())
        return save_update_state(payload)

    def check_now(self, *, channel: str = "stable") -> Dict[str, Any]:
        payload = self.client.check_for_updates(
            version=get_app_version(),
            platform_name=detect_platform(),
            channel=channel,
        )
        result = {
            "channel": channel,
            "last_checked_at": _utcnow_iso(),
            "last_error": "",
            "current_version": get_app_version(),
            "platform": detect_platform(),
            "update_available": bool(payload.get("update_available", False)),
            "latest_version": str(payload.get("latest_version", "")).strip(),
            "is_mandatory": bool(payload.get("is_mandatory", False)),
            "title": str(payload.get("title", "")).strip(),
            "release_notes": str(payload.get("release_notes", "")).strip(),
            "download_url": str(payload.get("download_url", "")).strip(),
            "sha256": str(payload.get("sha256", "")).strip(),
            "signature": str(payload.get("signature", "")).strip(),
            "min_supported_version": str(payload.get("min_supported_version", "")).strip(),
        }
        _verify_update_signature(result)
        self.save_state(result)
        return self.local_state()

    def download_latest(self) -> Dict[str, Any]:
        state = self.local_state()
        if not state.get("update_available"):
            raise UpdateClientError("No hay una actualización pendiente para descargar.")
        _verify_update_signature(state)
        result = self.client.download_update(state)
        self.save_state(
            {
                "downloaded_path": result["path"],
                "downloaded_sha256": result["sha256"],
                "downloaded_at": _utcnow_iso(),
                "last_error": "",
            }
        )
        return result

    def open_latest_download_url(self) -> str:
        state = self.local_state()
        _verify_update_signature(state)
        url = self.client.open_download_url(state.get("download_url", ""))
        self.save_state({"last_error": ""})
        return url

    def verify_download(self, path: str) -> bool:
        state = self.local_state()
        expected = str(state.get("sha256", "")).strip().lower()
        if not expected:
            raise UpdateClientError("No hay sha256 esperado para validar la descarga.")
        actual = compute_sha256(path)
        is_valid = actual == expected
        if is_valid:
            self.save_state({"downloaded_path": path, "downloaded_sha256": actual, "downloaded_at": _utcnow_iso()})
        return is_valid

    def check_in_background(self, *, channel: str = "stable", on_complete: Callable[[Dict[str, Any]], None] | None = None) -> None:
        def worker():
            try:
                state = self.check_now(channel=channel)
            except (UpdateBackendNotConfiguredError, UpdateBackendUnavailableError, UpdateClientError) as exc:
                registrar_log("warning", f"No se pudo revisar actualizaciones: {exc}", "updates")
                state = self.save_state(
                    {
                        "channel": channel,
                        "last_checked_at": _utcnow_iso(),
                        "last_error": str(exc),
                        "current_version": get_app_version(),
                        "platform": detect_platform(),
                    }
                )
            except Exception as exc:
                registrar_log("warning", f"Fallo inesperado al revisar actualizaciones: {exc}", "updates")
                state = self.save_state(
                    {
                        "channel": channel,
                        "last_checked_at": _utcnow_iso(),
                        "last_error": str(exc),
                        "current_version": get_app_version(),
                        "platform": detect_platform(),
                    }
                )
            if on_complete:
                on_complete(state)

        threading.Thread(target=worker, daemon=True).start()

    def status_summary(self) -> Dict[str, str | bool]:
        state = self.local_state()
        if state.get("update_available"):
            latest = state.get("latest_version") or "nueva versión"
            label = f"Actualización disponible · {latest}"
            if state.get("is_mandatory"):
                label = f"Actualización obligatoria · {latest}"
            return {"text": label, "available": True, "mandatory": bool(state.get("is_mandatory", False))}
        if state.get("last_error"):
            lowered = str(state.get("last_error", "")).lower()
            if "backend local de actualizaciones no está disponible" in lowered:
                return {"text": "Backend de actualizaciones inactivo", "available": False, "mandatory": False}
            if "no hay backend configurado" in lowered or "solo se usa en modo desarrollo" in lowered:
                return {"text": "Actualizaciones en espera de backend SaaS", "available": False, "mandatory": False}
            if "modo offline local" in lowered:
                return {"text": "Actualizaciones no disponibles sin internet", "available": False, "mandatory": False}
            return {"text": "Actualizaciones no disponibles", "available": False, "mandatory": False}
        return {"text": "Actualizaciones al día", "available": False, "mandatory": False}
