import os
import platform
from datetime import datetime, timezone
from uuid import uuid4

from core.local_license_store import load_installation_identity, save_installation_identity
from core.memoria import obtener_seccion

DEFAULT_APP_VERSION = "5.2.4"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for part in str(value or "").strip().split("."):
        if not part.isdigit():
            break
        parts.append(int(part))
    return tuple(parts)


def get_app_version() -> str:
    env = os.environ.get("TLAMATINI_APP_VERSION", "").strip()
    if env:
        return env
    configuracion = obtener_seccion("configuracion", {})
    if isinstance(configuracion, dict):
        stored = str(configuracion.get("version", "")).strip()
        if stored and _version_tuple(stored) > _version_tuple(DEFAULT_APP_VERSION):
            return stored
    return DEFAULT_APP_VERSION


def get_or_create_installation_identity() -> dict:
    data = load_installation_identity()
    installation_id = str(data.get("installation_id", "")).strip()
    if not installation_id:
        now = _utcnow_iso()
        data = {
            "installation_id": str(uuid4()),
            "created_at": now,
            "updated_at": now,
        }
        save_installation_identity(data)
    return data


def get_installation_id() -> str:
    return str(get_or_create_installation_identity().get("installation_id", "")).strip()


def get_installation_payload() -> dict:
    identity = get_or_create_installation_identity()
    return {
        "installation_id": str(identity["installation_id"]).strip(),
        "device_name": platform.node().strip() or platform.machine().strip() or "Equipo TLAMATINI",
        "os_name": f"{platform.system()} {platform.release()}".strip(),
        "app_version": get_app_version(),
    }
