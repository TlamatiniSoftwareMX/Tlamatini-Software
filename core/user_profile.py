from __future__ import annotations

import json
import os
import re
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.path_manager import get_paths


_APP_PATHS = get_paths()
DEFAULT_USER_PROFILE_FILE = _APP_PATHS.user_profile_file
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _profile_file_path() -> Path:
    env = os.environ.get("TLAMATINI_USER_PROFILE_FILE", "").strip()
    return _normalize_path(env) if env else DEFAULT_USER_PROFILE_FILE.resolve()


def _set_secure_permissions(path: Path, *, is_dir: bool) -> None:
    if os.name == "nt":
        return
    try:
        os.chmod(path, 0o700 if is_dir else 0o600)
    except Exception:
        pass


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _set_secure_permissions(path.parent, is_dir=True)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_profile() -> Dict[str, str]:
    return {
        "full_name": "",
        "email": "",
        "phone": "",
        "country": "",
        "created_at": "",
        "updated_at": "",
    }


def load_user_profile() -> Dict[str, str]:
    path = _profile_file_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return _default_profile()
    except Exception:
        return _default_profile()
    profile = _default_profile()
    if isinstance(data, dict):
        for key in profile:
            profile[key] = str(data.get(key, "") or "").strip()
    return profile


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(str(email or "").strip()))


def is_profile_complete(profile: Dict[str, Any] | None = None) -> bool:
    data = profile if isinstance(profile, dict) else load_user_profile()
    return bool(str(data.get("full_name", "")).strip() and is_valid_email(str(data.get("email", "")).strip()))


def validate_user_profile(
    *,
    full_name: str,
    email: str,
    phone: str = "",
    country: str = "",
) -> Dict[str, str]:
    normalized = {
        "full_name": str(full_name or "").strip(),
        "email": str(email or "").strip().lower(),
        "phone": str(phone or "").strip(),
        "country": str(country or "").strip(),
    }
    if not normalized["full_name"]:
        raise ValueError("Ingresa tu nombre completo.")
    if not normalized["email"] or not is_valid_email(normalized["email"]):
        raise ValueError("Ingresa un correo electrónico válido.")
    return normalized


def save_user_profile(
    *,
    full_name: str,
    email: str,
    phone: str = "",
    country: str = "",
) -> Dict[str, str]:
    current = load_user_profile()
    normalized = validate_user_profile(full_name=full_name, email=email, phone=phone, country=country)
    payload = deepcopy(current)
    payload.update(normalized)
    now = _utcnow_iso()
    payload["created_at"] = payload.get("created_at") or now
    payload["updated_at"] = now

    path = _profile_file_path()
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
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)
    _set_secure_permissions(path, is_dir=False)
    return payload
