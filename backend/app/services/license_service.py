from datetime import UTC, datetime
from uuid import uuid4

import jwt
from jwt import InvalidTokenError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.installation import Installation
from app.models.license import License
from app.models.user import User
from app.utils.time_utils import add_days, utcnow


settings = get_settings()


def _normalize_pem(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("\\n", "\n").strip()


def _get_license_signing_keys() -> tuple[str, str]:
    algorithm = settings.license_signing_algorithm.upper()
    if algorithm.startswith("HS"):
        if not settings.license_signing_secret:
            raise ValueError("LICENSE_SIGNING_SECRET es obligatorio cuando se usa firma simétrica.")
        return settings.license_signing_secret, settings.license_signing_secret

    private_key = _normalize_pem(settings.license_private_key)
    public_key = _normalize_pem(settings.license_public_key)
    if not private_key or private_key == "replace-me" or not public_key or public_key == "replace-me":
        raise ValueError("LICENSE_PRIVATE_KEY y LICENSE_PUBLIC_KEY son obligatorias para firma asimétrica.")
    return private_key, public_key


def _serialize_datetime(value: datetime | None) -> str | None:
    normalized = _ensure_utc_datetime(value)
    return normalized.isoformat() if normalized is not None else None


def _ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def build_license_payload(license_row: License) -> dict:
    return {
        "license_id": license_row.license_id,
        "user_id": license_row.user_id,
        "installation_id": license_row.installation.installation_id if license_row.installation is not None else None,
        "plan": license_row.plan,
        "status": license_row.status,
        "issued_at": _serialize_datetime(license_row.issued_at),
        "expires_at": _serialize_datetime(license_row.expires_at),
        "grace_until": _serialize_datetime(license_row.grace_until),
        "features": get_plan_features(license_row.plan),
    }


def sign_license_payload(payload: dict) -> str:
    private_key, _ = _get_license_signing_keys()
    return jwt.encode(payload, private_key, algorithm=settings.license_signing_algorithm)


def verify_license_payload(signed_payload: str) -> dict:
    _, public_key = _get_license_signing_keys()
    return jwt.decode(signed_payload, public_key, algorithms=[settings.license_signing_algorithm])


def get_plan_features(plan: str) -> list[str]:
    if plan == "trial":
        return ["core_access", "offline_validation_ready"]
    if plan == "monthly":
        return ["core_access", "updates", "offline_validation_ready"]
    if plan == "lifetime_dev":
        return ["core_access", "updates", "offline_validation_ready", "internal_dev"]
    return ["core_access"]


def get_current_license(db: Session, *, user_id: int, installation_db_id: int) -> License | None:
    query = (
        select(License)
        .where(License.user_id == user_id, License.installation_id == installation_db_id)
        .order_by(desc(License.created_at), desc(License.id))
    )
    return db.scalar(query)


def compute_license_status(license_row: License | None, *, allow_offline_grace: bool = False) -> dict:
    if license_row is None:
        return {
            "status": "unknown",
            "plan": "none",
            "license_id": None,
            "issued_at": None,
            "expires_at": None,
            "grace_until": None,
            "signed_payload": None,
            "days_remaining": None,
            "is_valid": False,
            "offline_grace_days": settings.offline_grace_days,
            "trial_days": settings.trial_days,
        }

    now = utcnow()
    issued_at = _ensure_utc_datetime(license_row.issued_at)
    expires_at = _ensure_utc_datetime(license_row.expires_at)
    grace_until = _ensure_utc_datetime(license_row.grace_until)
    status = license_row.status
    is_valid = status in {"trial", "active", "grace"}

    if status == "revoked":
        is_valid = False
    elif expires_at is not None and now > expires_at:
        is_valid = False
        status = "expired"
        if allow_offline_grace and grace_until is not None and now <= grace_until:
            status = "grace"
            is_valid = True
    elif status == "grace" and grace_until is not None and now > grace_until:
        status = "expired"
        is_valid = False

    days_remaining = None
    if expires_at is not None:
        delta = expires_at - now
        days_remaining = max(0, delta.days if delta.total_seconds() > 0 else 0)

    return {
        "status": status,
        "plan": license_row.plan,
        "license_id": license_row.license_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "grace_until": grace_until,
        "signed_payload": license_row.signed_payload,
        "days_remaining": days_remaining,
        "is_valid": is_valid,
        "offline_grace_days": settings.offline_grace_days,
        "trial_days": settings.trial_days,
    }


def create_trial_license(db: Session, user: User, installation: Installation) -> License:
    existing_license = get_current_license(db, user_id=user.id, installation_db_id=installation.id)
    if existing_license is not None:
        return existing_license

    issued_at = utcnow()
    expires_at = add_days(issued_at, settings.trial_days)
    grace_until = add_days(expires_at, settings.offline_grace_days)
    license_row = License(
        user_id=user.id,
        installation_id=installation.id,
        license_id=f"lic_{uuid4().hex}",
        plan="trial",
        status="trial",
        issued_at=issued_at,
        expires_at=expires_at,
        grace_until=grace_until,
    )
    db.add(license_row)
    db.flush()
    db.refresh(license_row, attribute_names=["installation"])

    signed_payload = sign_license_payload(build_license_payload(license_row))
    license_row.signed_payload = signed_payload
    db.commit()
    db.refresh(license_row)
    return license_row


def revoke_license(db: Session, license_row: License) -> License:
    license_row.status = "revoked"
    payload = build_license_payload(license_row)
    license_row.signed_payload = sign_license_payload(payload)
    db.commit()
    db.refresh(license_row)
    return license_row


def sync_license_signature(db: Session, license_row: License) -> License:
    db.refresh(license_row, attribute_names=["installation"])
    license_row.signed_payload = sign_license_payload(build_license_payload(license_row))
    db.commit()
    db.refresh(license_row)
    return license_row


def upsert_paid_license(
    db: Session,
    *,
    user_id: int,
    installation: Installation,
    plan: str,
    status: str,
    issued_at: datetime,
    expires_at: datetime,
) -> License:
    license_row = get_current_license(db, user_id=user_id, installation_db_id=installation.id)
    grace_until = add_days(expires_at, settings.offline_grace_days)

    if license_row is None:
        license_row = License(
            user_id=user_id,
            installation_id=installation.id,
            license_id=f"lic_{uuid4().hex}",
            plan=plan,
            status=status,
            issued_at=issued_at,
            expires_at=expires_at,
            grace_until=grace_until,
        )
        db.add(license_row)
        db.flush()
        db.refresh(license_row, attribute_names=["installation"])
    else:
        license_row.plan = plan
        license_row.status = status
        license_row.issued_at = issued_at
        license_row.expires_at = expires_at
        license_row.grace_until = grace_until

    return sync_license_signature(db, license_row)
