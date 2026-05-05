import base64
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.license_code_validator import load_and_validate_offline_license_code
from core.local_license_store import get_public_key_material, load_local_license
from core.logs import registrar_log

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
except Exception:
    InvalidSignature = None
    hashes = None
    padding = None
    load_pem_public_key = None


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _parse_datetime(value: str | None) -> datetime | None:
    texto = str(value or "").strip()
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except Exception:
        return None


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _days_until(value: datetime | None) -> int | None:
    normalized = _ensure_utc(value)
    if normalized is None:
        return None
    delta = normalized - datetime.now(timezone.utc)
    return max(0, delta.days if delta.total_seconds() > 0 else 0)


def _verify_hs256(signing_input: bytes, signature: bytes, secret: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return hmac.compare_digest(expected, signature)


def _verify_rs256(signing_input: bytes, signature: bytes, public_key: str) -> bool:
    if load_pem_public_key is not None and padding is not None and hashes is not None and InvalidSignature is not None:
        try:
            key = load_pem_public_key(public_key.encode("utf-8"))
            key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
            return True
        except InvalidSignature:
            return False
        except Exception:
            pass

    openssl_bin = shutil_which("openssl")
    if not openssl_bin:
        return False
    with tempfile.TemporaryDirectory(prefix="tlamatini-license-") as temp_dir:
        temp_path = Path(temp_dir)
        data_file = temp_path / "payload.bin"
        signature_file = temp_path / "signature.bin"
        key_file = temp_path / "public.pem"
        data_file.write_bytes(signing_input)
        signature_file.write_bytes(signature)
        key_file.write_text(public_key, encoding="utf-8")
        result = subprocess.run(
            [
                openssl_bin,
                "dgst",
                "-sha256",
                "-verify",
                str(key_file),
                "-signature",
                str(signature_file),
                str(data_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0


def shutil_which(name: str) -> str:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def decode_signed_payload(signed_payload: str) -> Dict[str, Any]:
    token = str(signed_payload or "").strip()
    if not token:
        raise ValueError("No hay licencia firmada disponible.")
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("El formato de la licencia firmada es inválido.")
    header = json.loads(_base64url_decode(parts[0]).decode("utf-8"))
    payload = json.loads(_base64url_decode(parts[1]).decode("utf-8"))
    return {"header": header, "payload": payload, "signature": parts[2], "signing_input": f"{parts[0]}.{parts[1]}".encode("ascii")}


def verify_signed_payload(signed_payload: str) -> Dict[str, Any]:
    decoded = decode_signed_payload(signed_payload)
    alg = str(decoded["header"].get("alg", "")).upper()
    signature = _base64url_decode(str(decoded["signature"]))
    key_material = get_public_key_material()
    if not key_material:
        raise ValueError("No hay clave local configurada para validar la licencia (PEM o secreto HS256).")

    if alg == "HS256":
        is_valid = _verify_hs256(decoded["signing_input"], signature, key_material)
    elif alg == "RS256":
        is_valid = _verify_rs256(decoded["signing_input"], signature, key_material)
    else:
        raise ValueError(f"Algoritmo de licencia no soportado: {alg}")

    if not is_valid:
        raise ValueError("La firma local de la licencia es inválida.")
    return decoded["payload"]


def validate_local_license(license_record: Dict[str, Any] | None = None) -> Dict[str, Any]:
    record = license_record if isinstance(license_record, dict) else load_local_license()
    signed_payload = str(record.get("signed_payload", "")).strip()
    online_status = {
        "state": "missing",
        "is_valid": False,
        "message": "No hay licencia local guardada.",
        "payload": None,
        "plan": "",
        "status": "",
        "expires_at": "",
        "grace_until": "",
        "days_remaining": None,
        "last_sync_at": str(record.get("last_sync_at", "")).strip(),
        "source": str(record.get("source", "")).strip() or "backend",
        "customer_email": "",
        "customer_name": "",
        "license_id": str(record.get("license_id", "")).strip(),
    }

    if signed_payload:
        try:
            payload = verify_signed_payload(signed_payload)
            now = datetime.now(timezone.utc)
            expires_at = _ensure_utc(_parse_datetime(payload.get("expires_at")))
            grace_until = _ensure_utc(_parse_datetime(payload.get("grace_until")))
            state = "valid"
            message = "Licencia válida."
            if expires_at is not None and now > expires_at:
                if grace_until is not None and now <= grace_until:
                    state = "grace"
                    message = "Licencia vencida, pero dentro del periodo de gracia."
                else:
                    state = "expired"
                    message = "La licencia local ya expiró."
            online_status = {
                "state": state,
                "is_valid": state in {"valid", "grace"},
                "message": message,
                "payload": payload,
                "plan": str(payload.get("plan", "")).strip(),
                "status": str(payload.get("status", "")).strip(),
                "expires_at": payload.get("expires_at"),
                "grace_until": payload.get("grace_until"),
                "days_remaining": _days_until(expires_at),
                "last_sync_at": str(record.get("last_sync_at", "")).strip(),
                "source": str(record.get("source", "")).strip() or "backend",
                "customer_email": str(payload.get("customer_email", payload.get("email", ""))).strip(),
                "customer_name": str(payload.get("customer_name", payload.get("name", ""))).strip(),
                "license_id": str(payload.get("license_id", record.get("license_id", ""))).strip(),
            }
        except Exception as exc:
            registrar_log("warning", f"Licencia local inválida: {exc}", "licencias")
            online_status = {
                "state": "invalid",
                "is_valid": False,
                "message": str(exc),
                "payload": None,
                "plan": str(record.get("plan", "")).strip(),
                "status": str(record.get("status", "")).strip(),
                "expires_at": str(record.get("expires_at", "")).strip(),
                "grace_until": str(record.get("grace_until", "")).strip(),
                "days_remaining": None,
                "last_sync_at": str(record.get("last_sync_at", "")).strip(),
                "source": str(record.get("source", "")).strip() or "backend",
                "customer_email": "",
                "customer_name": "",
                "license_id": str(record.get("license_id", "")).strip(),
            }

    try:
        offline_status = load_and_validate_offline_license_code()
    except Exception as exc:
        registrar_log("warning", f"Código offline inválido: {exc}", "licencias")
        offline_status = {
            "state": "invalid",
            "is_valid": False,
            "message": str(exc),
            "payload": None,
            "plan": "",
            "status": "",
            "expires_at": "",
            "grace_until": "",
            "days_remaining": None,
            "last_sync_at": str(record.get("last_sync_at", "")).strip(),
            "source": "offline_code",
            "customer_email": "",
            "customer_name": "",
            "license_id": "",
        }

    trial_expires_at = _ensure_utc(_parse_datetime(str(record.get("trial_expires_at", "")).strip()))
    trial_used_at = str(record.get("trial_used_at", "")).strip()
    trial_status = {
        "state": "missing",
        "is_valid": False,
        "message": "",
        "payload": None,
        "plan": "",
        "status": "",
        "expires_at": "",
        "grace_until": "",
        "days_remaining": None,
        "last_sync_at": str(record.get("last_sync_at", "")).strip(),
        "source": "local_trial",
        "customer_email": str(record.get("trial_email", "")).strip(),
        "customer_name": str(record.get("trial_name", "")).strip(),
        "license_id": "",
    }
    if trial_expires_at is not None:
        now = datetime.now(timezone.utc)
        if now <= trial_expires_at:
            trial_status.update(
                {
                    "state": "valid",
                    "is_valid": True,
                    "message": "Prueba activa.",
                    "plan": "trial",
                    "status": "trial_active",
                    "expires_at": str(record.get("trial_expires_at", "")).strip(),
                    "days_remaining": _days_until(trial_expires_at),
                }
            )
        else:
            trial_status.update(
                {
                    "state": "expired",
                    "is_valid": False,
                    "message": "La prueba gratuita ya fue utilizada en esta instalación.",
                    "plan": "trial",
                    "status": "trial_expired",
                    "expires_at": str(record.get("trial_expires_at", "")).strip(),
                    "days_remaining": 0,
                }
            )
    elif trial_used_at:
        trial_status.update(
            {
                "state": "expired",
                "is_valid": False,
                "message": "La prueba gratuita ya fue utilizada en esta instalación.",
                "plan": "trial",
                "status": "trial_expired",
                "days_remaining": 0,
            }
        )

    candidates = [online_status]
    if offline_status.get("state") != "missing" or record.get("offline_license_code"):
        candidates.append(offline_status)
    elif online_status.get("state") == "missing":
        candidates.append(offline_status)
    if trial_status.get("state") != "missing":
        candidates.append(trial_status)

    priority = {"valid": 5, "grace": 4, "expired": 3, "invalid": 2, "missing": 1}
    source_priority = {"backend": 3, "offline_code": 2, "local_trial": 1}
    best = max(
        candidates,
        key=lambda item: (
            priority.get(str(item.get("state", "missing")).strip().lower(), 0),
            source_priority.get(str(item.get("source", "")).strip(), 0),
        ),
    )
    best = dict(best)
    if str(best.get("source", "")).strip() == "local_trial" and str(best.get("state", "")).strip() == "expired":
        best["state"] = "missing"
        best["plan"] = ""
        best["status"] = "trial_expired"
    best["online_status"] = online_status
    best["offline_status"] = offline_status
    best["trial_status"] = trial_status
    best["trial_available"] = trial_status.get("state") == "missing"
    best["trial_active"] = trial_status.get("state") == "valid"
    best["trial_expired"] = trial_status.get("state") == "expired"
    best["trial_used"] = trial_status.get("state") in {"valid", "expired"}
    if best.get("state") == "missing" and best["trial_expired"]:
        best["message"] = str(trial_status.get("message", "")).strip() or best.get("message", "")
    best["offline_ready"] = bool(
        online_status.get("state") in {"valid", "grace"}
        or offline_status.get("state") == "valid"
        or trial_status.get("state") == "valid"
    )
    return best
