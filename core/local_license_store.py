import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from core.logs import registrar_log
from core.memoria import cargar_memoria, guardar_memoria
from core.path_manager import get_paths


_APP_PATHS = get_paths()
DEFAULT_LICENSE_FILE = _APP_PATHS.license_file
DEFAULT_OFFLINE_LICENSE_CODE_FILE = _APP_PATHS.offline_license_code_file
DEFAULT_INSTALLATION_ID_FILE = _APP_PATHS.installation_id_file
DEFAULT_BUNDLED_PUBLIC_KEY_FILE = _APP_PATHS.bundled_public_key_file
DEFAULT_UPDATE_DOWNLOAD_DIR = _APP_PATHS.local_updates_dir
STATE_SECTION = "licenciamiento"
DEFAULT_BACKEND_MODE = "hybrid"
VALID_BACKEND_MODES = {"hybrid", "remote-only", "dev-local"}
LOCAL_BACKEND_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _normalize_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _set_secure_permissions(path: Path, *, is_dir: bool) -> None:
    if os.name == "nt":
        return
    try:
        os.chmod(path, 0o700 if is_dir else 0o600)
    except Exception:
        pass


def normalize_backend_url(url: str) -> str:
    normalized = str(url or "").strip().rstrip("/")
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("La URL del backend debe iniciar con http:// o https:// y contener un host válido.")
    if parsed.params or parsed.query or parsed.fragment:
        raise ValueError("La URL del backend no puede incluir parámetros, query ni fragmentos.")
    if parsed.path not in {"", "/"}:
        raise ValueError("La URL del backend debe apuntar a la raíz del servicio, sin rutas adicionales.")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError("La URL del backend no incluye un host válido.")
    if parsed.scheme != "https" and hostname not in LOCAL_BACKEND_HOSTS:
        raise ValueError("El backend remoto debe usar HTTPS.")
    return normalized


def _license_file_path() -> Path:
    env = os.environ.get("TLAMATINI_LICENSE_FILE", "").strip()
    return _normalize_path(env) if env else DEFAULT_LICENSE_FILE.resolve()


def _installation_file_path() -> Path:
    env = os.environ.get("TLAMATINI_INSTALLATION_ID_FILE", "").strip()
    return _normalize_path(env) if env else DEFAULT_INSTALLATION_ID_FILE.resolve()


def _offline_license_code_file_path() -> Path:
    env = os.environ.get("TLAMATINI_OFFLINE_LICENSE_CODE_FILE", "").strip()
    return _normalize_path(env) if env else DEFAULT_OFFLINE_LICENSE_CODE_FILE.resolve()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _set_secure_permissions(path.parent, is_dir=True)


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    _ensure_parent(path)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)
    _set_secure_permissions(path, is_dir=False)


def _read_json_file(path: Path, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else (default or {})
    except FileNotFoundError:
        return deepcopy(default or {})
    except Exception as exc:
        registrar_log("warning", f"No se pudo leer {path.name}: {exc}", "licencias")
        return deepcopy(default or {})


def _read_text_file(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default
    except Exception as exc:
        registrar_log("warning", f"No se pudo leer {path.name}: {exc}", "licencias")
        return default


def _atomic_write_text(path: Path, value: str) -> None:
    _ensure_parent(path)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)
    _set_secure_permissions(path, is_dir=False)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_runtime_state() -> Dict[str, Any]:
    memoria = cargar_memoria()
    configuracion = memoria.get("configuracion", {})
    if not isinstance(configuracion, dict):
        return {}
    datos = configuracion.get(STATE_SECTION, {})
    return deepcopy(datos) if isinstance(datos, dict) else {}


def _normalize_backend_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    if mode in VALID_BACKEND_MODES:
        return mode
    return DEFAULT_BACKEND_MODE


def save_runtime_state(values: Dict[str, Any]) -> Dict[str, Any]:
    memoria = cargar_memoria()
    configuracion = memoria.get("configuracion", {})
    if not isinstance(configuracion, dict):
        configuracion = {}
        memoria["configuracion"] = configuracion
    actual = configuracion.get(STATE_SECTION, {})
    if not isinstance(actual, dict):
        actual = {}
    actual.update(values or {})
    configuracion[STATE_SECTION] = actual
    guardar_memoria(memoria)
    return deepcopy(actual)


def load_update_state() -> Dict[str, Any]:
    state = load_runtime_state()
    updates = state.get("updates", {})
    return deepcopy(updates) if isinstance(updates, dict) else {}


def save_update_state(values: Dict[str, Any]) -> Dict[str, Any]:
    state = load_runtime_state()
    updates = state.get("updates", {})
    if not isinstance(updates, dict):
        updates = {}
    updates.update(values or {})
    return deepcopy(save_runtime_state({"updates": updates}).get("updates", {}))


def get_backend_url() -> str:
    raw = get_saved_backend_url() or get_default_backend_url()
    if not raw:
        return ""
    if is_local_backend_url(raw) and not local_backend_allowed():
        return ""
    return raw


def get_saved_backend_url() -> str:
    env = os.environ.get("TLAMATINI_BACKEND_URL", "").strip()
    if env:
        try:
            return normalize_backend_url(env)
        except ValueError:
            return ""
    saved = str(load_runtime_state().get("backend_url", "")).strip()
    if not saved:
        return ""
    try:
        return normalize_backend_url(saved)
    except ValueError:
        return ""


def get_default_backend_url() -> str:
    env = os.environ.get("TLAMATINI_DEFAULT_BACKEND_URL", "").strip()
    if env:
        try:
            return normalize_backend_url(env)
        except ValueError:
            return ""
    saved = str(load_runtime_state().get("default_backend_url", "")).strip()
    if not saved:
        return ""
    try:
        return normalize_backend_url(saved)
    except ValueError:
        return ""


def save_backend_url(url: str) -> str:
    normalized = normalize_backend_url(url) if str(url or "").strip() else ""
    save_runtime_state({"backend_url": normalized})
    return normalized


def get_backend_mode() -> str:
    env = os.environ.get("TLAMATINI_BACKEND_MODE", "").strip()
    if env:
        return _normalize_backend_mode(env)
    return _normalize_backend_mode(load_runtime_state().get("backend_mode", DEFAULT_BACKEND_MODE))


def save_backend_mode(mode: str) -> str:
    normalized = _normalize_backend_mode(mode)
    save_runtime_state({"backend_mode": normalized})
    return normalized


def is_local_backend_url(url: str) -> bool:
    try:
        parsed = urlparse(str(url or "").strip())
    except Exception:
        return False
    return (parsed.hostname or "").strip().lower() in LOCAL_BACKEND_HOSTS


def local_backend_allowed(mode: str | None = None) -> bool:
    env = os.environ.get("TLAMATINI_ALLOW_LOCAL_BACKEND", "").strip().lower()
    if env in {"1", "true", "yes"}:
        return True
    return _normalize_backend_mode(mode or get_backend_mode()) == "dev-local"


def describe_backend_configuration() -> Dict[str, Any]:
    raw_url = get_saved_backend_url()
    default_url = get_default_backend_url()
    mode = get_backend_mode()
    candidate_url = raw_url or default_url
    is_local = is_local_backend_url(candidate_url)
    local_allowed = local_backend_allowed(mode)
    effective_url = get_backend_url()
    source = "saved" if raw_url else ("default" if default_url else "")
    return {
        "mode": mode,
        "raw_url": raw_url,
        "default_url": default_url,
        "source": source,
        "effective_url": effective_url,
        "configured": bool(effective_url),
        "has_saved_url": bool(raw_url),
        "has_default_url": bool(default_url),
        "is_local_url": is_local,
        "local_backend_allowed": local_allowed,
        "blocked_reason": (
            "El backend local solo se usa en modo desarrollo."
            if candidate_url and is_local and not local_allowed
            else ""
        ),
    }


def load_auth_session() -> Dict[str, Any]:
    state = load_runtime_state()
    return {
        "access_token": str(state.get("access_token", "")).strip(),
        "user": deepcopy(state.get("user", {})) if isinstance(state.get("user", {}), dict) else {},
        "saved_at": str(state.get("auth_saved_at", "")).strip(),
    }


def save_auth_session(*, access_token: str, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = {
        "access_token": str(access_token or "").strip(),
        "user": deepcopy(user or {}),
        "auth_saved_at": _utcnow_iso(),
    }
    save_runtime_state(payload)
    return load_auth_session()


def clear_auth_session() -> None:
    save_runtime_state({"access_token": "", "user": {}, "auth_saved_at": ""})


def load_installation_identity() -> Dict[str, Any]:
    path = _installation_file_path()
    return _read_json_file(
        path,
        default={
            "installation_id": "",
            "created_at": "",
            "updated_at": "",
        },
    )


def save_installation_identity(data: Dict[str, Any]) -> Dict[str, Any]:
    path = _installation_file_path()
    payload = deepcopy(data or {})
    payload.setdefault("updated_at", _utcnow_iso())
    _atomic_write_json(path, payload)
    return deepcopy(payload)


def load_offline_license_code() -> str:
    path = _offline_license_code_file_path()
    return _read_text_file(path, default="").strip()


def save_offline_license_code(code: str) -> str:
    path = _offline_license_code_file_path()
    normalized = str(code or "").strip()
    _atomic_write_text(path, normalized + ("\n" if normalized else ""))
    return normalized


def load_local_license() -> Dict[str, Any]:
    path = _license_file_path()
    return _read_json_file(
        path,
        default={
            "signed_payload": "",
            "plan": "",
            "status": "",
            "license_id": "",
            "expires_at": "",
            "grace_until": "",
            "last_sync_at": "",
            "source": "",
            "offline_license_code": "",
            "offline_license_status": "",
            "offline_expires_at": "",
            "offline_license_id": "",
            "trial_started_at": "",
            "trial_expires_at": "",
            "trial_used_at": "",
            "trial_status": "",
            "trial_name": "",
            "trial_email": "",
            "trial_phone": "",
            "trial_country": "",
        },
    )


def save_local_license(data: Dict[str, Any]) -> Dict[str, Any]:
    path = _license_file_path()
    payload = deepcopy(data or {})
    payload["last_saved_at"] = _utcnow_iso()
    _atomic_write_json(path, payload)
    return deepcopy(payload)


def update_local_license_from_backend(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = load_local_license()
    current.update(
        {
            "signed_payload": str(payload.get("signed_payload", current.get("signed_payload", ""))).strip(),
            "plan": str(payload.get("plan", current.get("plan", ""))).strip(),
            "status": str(payload.get("status", current.get("status", ""))).strip(),
            "license_id": str(payload.get("license_id", current.get("license_id", ""))).strip(),
            "expires_at": str(payload.get("expires_at", current.get("expires_at", ""))).strip(),
            "grace_until": str(payload.get("grace_until", current.get("grace_until", ""))).strip(),
            "issued_at": str(payload.get("issued_at", current.get("issued_at", ""))).strip(),
            "days_remaining": payload.get("days_remaining"),
            "is_valid": payload.get("is_valid"),
            "source": "backend",
            "last_sync_at": _utcnow_iso(),
        }
    )
    return save_local_license(current)


def activate_local_trial(*, profile: Dict[str, Any], duration_days: int = 7) -> Dict[str, Any]:
    normalized_profile = deepcopy(profile or {})
    email = str(normalized_profile.get("email", "")).strip().lower()
    full_name = str(normalized_profile.get("full_name", "")).strip()
    if not email or not full_name:
        raise ValueError("Primero guarda tu nombre y un correo electrónico válido.")

    current = load_local_license()
    now = datetime.now(timezone.utc)
    expires_at_raw = str(current.get("trial_expires_at", "")).strip()
    used_at = str(current.get("trial_used_at", "")).strip()
    if expires_at_raw:
        try:
            expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
        except Exception:
            expires_at = None
        if expires_at is not None and expires_at > now:
            return save_local_license(current)
    if used_at:
        raise ValueError("La prueba gratuita ya fue utilizada en esta instalación.")

    started_at = now.isoformat().replace("+00:00", "Z")
    trial_expires_at = (now + timedelta(days=max(1, int(duration_days)))).isoformat().replace("+00:00", "Z")
    current.update(
        {
            "trial_started_at": started_at,
            "trial_expires_at": trial_expires_at,
            "trial_used_at": started_at,
            "trial_status": "active",
            "trial_name": full_name,
            "trial_email": email,
            "trial_phone": str(normalized_profile.get("phone", "")).strip(),
            "trial_country": str(normalized_profile.get("country", "")).strip(),
        }
    )
    return save_local_license(current)


def get_public_key_material() -> str:
    for env_name in ("TLAMATINI_LICENSE_PUBLIC_KEY", "TLAMATINI_LICENSE_SIGNING_SECRET"):
        env = os.environ.get(env_name, "").strip()
        if env:
            candidate = Path(env).expanduser()
            if candidate.exists():
                try:
                    return candidate.read_text(encoding="utf-8").strip()
                except Exception:
                    pass
            return env.replace("\\n", "\n").strip()

    state = load_runtime_state()
    for key in ("license_public_key", "license_signing_secret"):
        value = str(state.get(key, "")).replace("\\n", "\n").strip()
        if value:
            return value
    bundled_key = _read_text_file(DEFAULT_BUNDLED_PUBLIC_KEY_FILE, default="").strip()
    if bundled_key:
        return bundled_key
    return ""


def save_public_key_material(value: str) -> str:
    normalized = str(value or "").replace("\\n", "\n").strip()
    save_runtime_state({"license_public_key": normalized})
    return normalized
