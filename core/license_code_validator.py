from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any, Dict

from core.installation_identity import get_installation_id
from core.local_license_store import get_public_key_material, load_offline_license_code

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
except Exception:
    InvalidSignature = Exception
    Ed25519PublicKey = None
    load_pem_public_key = None


LICENSE_CODE_PREFIX = "TLAMATINI-LICENSE-v1."
REQUIRED_PAYLOAD_FIELDS = (
    "license_version",
    "license_id",
    "customer_email",
    "plan",
    "issued_at",
    "expires_at",
    "features",
)


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _parse_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _days_remaining(expires_at: datetime | None) -> int | None:
    target = _ensure_utc(expires_at)
    if target is None:
        return None
    delta = target - datetime.now(timezone.utc)
    if delta.total_seconds() <= 0:
        return 0
    return max(0, delta.days)


def _payload_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def decode_license_code(license_code: str) -> Dict[str, Any]:
    token = str(license_code or "").strip()
    if not token.startswith(LICENSE_CODE_PREFIX):
        raise ValueError("El código de licencia no tiene un formato válido.")

    encoded_body = token[len(LICENSE_CODE_PREFIX) :].strip()
    if not encoded_body:
        raise ValueError("El código de licencia no tiene un formato válido.")

    try:
        package = json.loads(_base64url_decode(encoded_body).decode("utf-8"))
    except Exception as exc:
        raise ValueError("No se pudo leer el código de licencia.") from exc

    if not isinstance(package, dict):
        raise ValueError("La licencia está incompleta.")

    algorithm = str(package.get("algorithm", "")).strip()
    payload = package.get("payload")
    signature = str(package.get("signature", "")).strip()
    if algorithm != "Ed25519":
        raise ValueError("La licencia está incompleta.")
    if not isinstance(payload, dict) or not signature:
        raise ValueError("La licencia está incompleta.")
    if any(not str(payload.get(field, "")).strip() for field in REQUIRED_PAYLOAD_FIELDS if field != "features"):
        raise ValueError("La licencia está incompleta.")
    if "features" not in payload:
        raise ValueError("La licencia está incompleta.")

    return {
        "algorithm": algorithm,
        "payload": payload,
        "signature": signature,
        "encoded_body": encoded_body,
    }


def verify_license_code_signature(license_code: str) -> Dict[str, Any]:
    decoded = decode_license_code(license_code)
    public_key_pem = get_public_key_material()
    if not public_key_pem.strip():
        raise ValueError("La licencia está incompleta.")
    if load_pem_public_key is None or Ed25519PublicKey is None:
        raise ValueError("La licencia está incompleta.")

    try:
        key = load_pem_public_key(public_key_pem.encode("utf-8"))
        signature = _base64url_decode(decoded["signature"])
        payload_bytes = _payload_bytes(decoded["payload"])
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("La licencia está incompleta.")
        key.verify(signature, payload_bytes)
    except InvalidSignature as exc:
        raise ValueError("Firma inválida. La licencia fue modificada o no fue generada por TLAMATINI.") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("No se pudo leer el código de licencia.") from exc

    return decoded


def validate_license_code(license_code: str, *, installation_id: str | None = None) -> Dict[str, Any]:
    token = str(license_code or "").strip()
    if not token:
        return {
            "state": "missing",
            "is_valid": False,
            "message": "Sin licencia",
            "payload": None,
            "plan": "",
            "customer_email": "",
            "expires_at": "",
            "days_remaining": None,
            "installation_id": "",
            "is_bound_to_installation": False,
            "source": "offline_code",
            "license_code": "",
            "license_id": "",
        }

    decoded = verify_license_code_signature(token)
    payload = decoded["payload"]
    expires_at = _ensure_utc(_parse_datetime(payload.get("expires_at")))
    if expires_at is None:
        raise ValueError("La licencia está incompleta.")
    if datetime.now(timezone.utc) > expires_at:
        raise ValueError("La licencia está vencida.")

    current_installation_id = str(installation_id or get_installation_id()).strip()
    bound_installation_id = str(payload.get("installation_id", "")).strip()
    if bound_installation_id and bound_installation_id != current_installation_id:
        raise ValueError("Esta licencia corresponde a otra instalación.")

    return {
        "state": "valid",
        "is_valid": True,
        "message": "Licencia válida.",
        "payload": payload,
        "plan": str(payload.get("plan", "")).strip(),
        "customer_name": str(payload.get("customer_name", "")).strip(),
        "customer_email": str(payload.get("customer_email", "")).strip(),
        "expires_at": str(payload.get("expires_at", "")).strip(),
        "days_remaining": _days_remaining(expires_at),
        "installation_id": bound_installation_id,
        "is_bound_to_installation": bool(bound_installation_id),
        "source": "offline_code",
        "license_code": token,
        "license_id": str(payload.get("license_id", "")).strip(),
    }


def load_and_validate_offline_license_code(*, installation_id: str | None = None) -> Dict[str, Any]:
    return validate_license_code(load_offline_license_code(), installation_id=installation_id)
