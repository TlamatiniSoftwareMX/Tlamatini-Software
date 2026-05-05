from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools_private"
PRIVATE_KEY_PATH = TOOLS_DIR / "private_license_key.pem"
PUBLIC_KEY_PATH = TOOLS_DIR / "public_license_key.pem"
APP_PUBLIC_KEY_PATH = PROJECT_ROOT / "public_license_key.pem"
LICENSE_PREFIX = "TLAMATINI-LICENSE-v1."
DEFAULT_FEATURES = ["offline_activation"]
PLAN_DEFAULT_DAYS = {
    "mensual": 30,
    "trimestral": 90,
    "anual": 365,
}


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _isoformat_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def private_key_exists() -> bool:
    return PRIVATE_KEY_PATH.exists() and PRIVATE_KEY_PATH.is_file()


def generate_license_keys(*, overwrite: bool = False) -> Dict[str, Path]:
    if private_key_exists() and not overwrite:
        return {
            "private_key_path": PRIVATE_KEY_PATH,
            "public_key_path": PUBLIC_KEY_PATH,
            "app_public_key_path": APP_PUBLIC_KEY_PATH,
            "created": False,
        }

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    _write_bytes(PRIVATE_KEY_PATH, private_pem)
    _write_bytes(PUBLIC_KEY_PATH, public_pem)
    _write_bytes(APP_PUBLIC_KEY_PATH, public_pem)
    return {
        "private_key_path": PRIVATE_KEY_PATH,
        "public_key_path": PUBLIC_KEY_PATH,
        "app_public_key_path": APP_PUBLIC_KEY_PATH,
        "created": True,
    }


def ensure_private_key_available() -> Path:
    if not private_key_exists():
        raise FileNotFoundError(
            f"No existe la clave privada en {PRIVATE_KEY_PATH}. Ejecuta primero generar_claves_tlamatini.py"
        )
    return PRIVATE_KEY_PATH


def load_private_key():
    return serialization.load_pem_private_key(ensure_private_key_available().read_bytes(), password=None)


def normalize_features(features: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if features is None:
        return list(DEFAULT_FEATURES)
    if isinstance(features, str):
        values = [item.strip() for item in features.split(",") if item.strip()]
        return values or list(DEFAULT_FEATURES)
    values = [str(item).strip() for item in features if str(item).strip()]
    return values or list(DEFAULT_FEATURES)


def generate_license_code(
    email: str,
    plan: str,
    duration_days: int,
    installation_id: str | None = None,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    customer_country: str | None = None,
    features: list[str] | tuple[str, ...] | str | None = None,
) -> Dict[str, Any]:
    customer_email = str(email or "").strip()
    if not customer_email:
        raise ValueError("El email es obligatorio.")

    normalized_plan = str(plan or "").strip() or "mensual"
    normalized_duration = int(duration_days)
    if normalized_duration <= 0:
        raise ValueError("La duración debe ser mayor a 0 días.")

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(days=normalized_duration)
    payload = {
        "license_version": 1,
        "license_id": str(uuid4()),
        "customer_email": customer_email,
        "plan": normalized_plan,
        "issued_at": _isoformat_utc(issued_at),
        "expires_at": _isoformat_utc(expires_at),
        "features": normalize_features(features),
    }

    normalized_customer_name = str(customer_name or "").strip()
    if normalized_customer_name:
        payload["customer_name"] = normalized_customer_name
    normalized_customer_phone = str(customer_phone or "").strip()
    if normalized_customer_phone:
        payload["customer_phone"] = normalized_customer_phone
    normalized_customer_country = str(customer_country or "").strip()
    if normalized_customer_country:
        payload["customer_country"] = normalized_customer_country

    normalized_installation_id = str(installation_id or "").strip()
    if normalized_installation_id:
        payload["installation_id"] = normalized_installation_id

    signing_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = load_private_key().sign(signing_bytes)
    package = {
        "algorithm": "Ed25519",
        "payload": payload,
        "signature": _base64url_encode(signature),
    }
    encoded_package = _base64url_encode(
        json.dumps(package, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    return {
        "license_code": f"{LICENSE_PREFIX}{encoded_package}",
        "payload": payload,
        "package": package,
    }


def infer_duration_days_from_plan(plan: str) -> int:
    return PLAN_DEFAULT_DAYS.get(str(plan or "").strip().lower(), 30)


def parse_license_request_text(text: str) -> Dict[str, str]:
    raw = str(text or "").strip()
    result = {
        "full_name": "",
        "email": "",
        "phone": "",
        "country": "",
        "installation_id": "",
        "os_name": "",
        "app_version": "",
        "current_status": "",
        "requested_plan": "",
    }
    if not raw:
        return result

    patterns = {
        "full_name": r"(?im)^Nombre:\s*(.+?)\s*$",
        "email": r"(?im)^Email:\s*(.+?)\s*$",
        "phone": r"(?im)^Tel[eé]fono:\s*(.+?)\s*$",
        "country": r"(?im)^Pa[ií]s:\s*(.+?)\s*$",
        "installation_id": r"(?im)^ID de instalaci[oó]n:\s*(.+?)\s*$",
        "os_name": r"(?im)^Sistema operativo:\s*(.+?)\s*$",
        "app_version": r"(?im)^Versi[oó]n de TLAMATINI:\s*(.+?)\s*$",
        "current_status": r"(?im)^Estado actual:\s*(.+?)\s*$",
        "requested_plan": r"(?im)^Plan solicitado:\s*(.+?)\s*$",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, raw)
        if match:
            result[key] = match.group(1).strip()

    pending_markers = {"", "pendiente", "no registrado", "<email o pendiente>"}
    if result["email"].strip().lower() in pending_markers:
        result["email"] = ""
    for field in ("phone", "country", "full_name"):
        if result[field].strip().lower() in {"", "pendiente", "no proporcionado"}:
            result[field] = ""
    return result
