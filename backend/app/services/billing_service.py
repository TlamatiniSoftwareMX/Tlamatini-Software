import hashlib
import hmac
import json
import logging
from datetime import datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.billing_webhook_event import BillingWebhookEvent
from app.models.installation import Installation
from app.models.license import License
from app.models.subscription import Subscription
from app.models.user import User
from app.services.license_service import sync_license_signature, upsert_paid_license
from app.utils.time_utils import utcnow


settings = get_settings()
logger = logging.getLogger(__name__)


def _paddle_base_url() -> str:
    return "https://sandbox-api.paddle.com" if settings.paddle_environment == "sandbox" else "https://api.paddle.com"


def ensure_paddle_configured() -> None:
    required = {
        "PADDLE_API_KEY": settings.paddle_api_key,
        "PADDLE_WEBHOOK_SECRET": settings.paddle_webhook_secret,
        "PADDLE_PRODUCT_ID": settings.paddle_product_id,
        "PADDLE_PRICE_ID": settings.paddle_price_id,
    }
    invalid = []
    for key, value in required.items():
        normalized = str(value or "").strip()
        if not normalized or normalized.startswith("placeholder"):
            invalid.append(key)
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Paddle no está configurado correctamente. Faltan o son placeholder: {', '.join(invalid)}.",
        )


def _parse_rfc3339(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _extract_custom_data(payload: dict) -> dict:
    return payload.get("custom_data") or {}


def verify_paddle_webhook_signature(*, raw_body: bytes, signature_header: str | None) -> None:
    ensure_paddle_configured()
    if not signature_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta Paddle-Signature.")

    pieces = {}
    for part in signature_header.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        pieces.setdefault(key.strip(), []).append(value.strip())

    timestamp = (pieces.get("ts") or [None])[0]
    signatures = pieces.get("h1") or []
    if not timestamp or not signatures:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma Paddle inválida.")
    try:
        timestamp_int = int(str(timestamp).strip())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Timestamp Paddle inválido.") from exc

    now_ts = int(utcnow().timestamp())
    if abs(now_ts - timestamp_int) > settings.paddle_webhook_tolerance_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma Paddle expirada o fuera de tolerancia.")

    signed_payload = timestamp.encode("utf-8") + b":" + raw_body
    expected = hmac.new(
        settings.paddle_webhook_secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma Paddle inválida.")


def get_webhook_event_by_event_id(db: Session, *, provider: str, event_id: str) -> BillingWebhookEvent | None:
    return db.scalar(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.provider == provider,
            BillingWebhookEvent.event_id == event_id,
        )
    )


def record_webhook_event_received(
    db: Session,
    *,
    provider: str,
    event_id: str,
    event_type: str,
    payload: str,
) -> BillingWebhookEvent:
    webhook_event = get_webhook_event_by_event_id(db, provider=provider, event_id=event_id)
    if webhook_event is None:
        webhook_event = BillingWebhookEvent(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            status="received",
            payload=payload,
        )
        db.add(webhook_event)
    else:
        webhook_event.event_type = event_type
        webhook_event.payload = payload
        webhook_event.status = "received"
        webhook_event.error_message = None
        webhook_event.processed_at = None

    db.commit()
    db.refresh(webhook_event)
    logger.info("Webhook recibido provider=%s event_id=%s event_type=%s", provider, event_id, event_type)
    return webhook_event


def mark_webhook_event_status(
    db: Session,
    webhook_event: BillingWebhookEvent,
    *,
    status_value: str,
    error_message: str | None = None,
) -> BillingWebhookEvent:
    webhook_event.status = status_value
    webhook_event.error_message = error_message
    webhook_event.processed_at = utcnow() if status_value in {"processed", "ignored", "failed"} else None
    db.commit()
    db.refresh(webhook_event)
    return webhook_event


def get_or_create_paddle_customer(user: User) -> str:
    existing_customer_id = db_lookup_provider_customer_id_for_user(user.id)
    if existing_customer_id is not None:
        return existing_customer_id

    payload = {
        "email": user.email,
        "custom_data": {
            "user_id": user.id,
            "source": "tlamatini_backend",
        },
        "locale": user.preferred_language,
    }
    response = paddle_api_request("POST", "/customers", json=payload)
    return response["data"]["id"]


def db_lookup_provider_customer_id_for_user(user_id: int) -> str | None:
    from app.database import SessionLocal

    with SessionLocal() as db:
        subscription = db.scalar(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.provider == "paddle",
                Subscription.provider_customer_id.is_not(None),
            )
        )
        return subscription.provider_customer_id if subscription is not None else None


def paddle_api_request(method: str, path: str, *, json: dict | None = None) -> dict:
    ensure_paddle_configured()
    headers = {
        "Authorization": f"Bearer {settings.paddle_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(base_url=_paddle_base_url(), timeout=20.0) as client:
        response = client.request(method, path, headers=headers, json=json)

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al comunicarse con Paddle: {response.text[:400]}",
        )
    return response.json()


def create_checkout_transaction(*, user: User, installation: Installation, country_code: str, postal_code: str | None) -> dict:
    customer_id = get_or_create_paddle_customer(user)
    address_response = paddle_api_request(
        "POST",
        f"/customers/{customer_id}/addresses",
        json={
            "country_code": country_code.upper(),
            "postal_code": postal_code,
            "description": f"TLAMATINI {installation.device_name}",
        },
    )
    address_id = address_response["data"]["id"]

    transaction_response = paddle_api_request(
        "POST",
        "/transactions",
        json={
            "items": [{"price_id": settings.paddle_price_id, "quantity": 1}],
            "customer_id": customer_id,
            "address_id": address_id,
            "collection_mode": "automatic",
            "custom_data": {
                "user_id": user.id,
                "installation_id": installation.installation_id,
                "installation_db_id": installation.id,
                "product_id": settings.paddle_product_id,
                "price_id": settings.paddle_price_id,
            },
        },
    )
    return transaction_response["data"]


def ensure_pending_subscription(
    db: Session,
    *,
    user_id: int,
    installation_id: int,
    provider_customer_id: str | None,
) -> Subscription:
    subscription = db.scalar(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.installation_id == installation_id,
            Subscription.provider == "paddle",
        )
    )
    if subscription is None:
        subscription = Subscription(
            user_id=user_id,
            installation_id=installation_id,
            provider="paddle",
            provider_customer_id=provider_customer_id,
            status="pending",
        )
        db.add(subscription)
    else:
        subscription.provider_customer_id = provider_customer_id or subscription.provider_customer_id
        subscription.status = "pending"

    db.commit()
    db.refresh(subscription)
    return subscription


def _resolve_user_and_installation(db: Session, entity_data: dict) -> tuple[User | None, Installation | None]:
    custom_data = _extract_custom_data(entity_data)
    user = None
    installation = None

    if custom_data.get("user_id") is not None:
        user = db.get(User, int(custom_data["user_id"]))
    provider_customer_id = entity_data.get("customer_id")
    if user is None and provider_customer_id:
        user = db.scalar(
            select(User)
            .join(Subscription, Subscription.user_id == User.id)
            .where(Subscription.provider_customer_id == provider_customer_id)
        )

    installation_identifier = custom_data.get("installation_id")
    if installation_identifier:
        installation = db.scalar(
            select(Installation).where(Installation.installation_id == installation_identifier)
        )
    elif custom_data.get("installation_db_id") is not None:
        installation = db.get(Installation, int(custom_data["installation_db_id"]))

    return user, installation


def upsert_subscription_from_paddle(db: Session, *, entity_data: dict) -> Subscription | None:
    user, installation = _resolve_user_and_installation(db, entity_data)
    if user is None:
        return None

    provider_subscription_id = entity_data.get("id") if str(entity_data.get("id", "")).startswith("sub_") else entity_data.get("subscription_id")
    provider_customer_id = entity_data.get("customer_id")
    subscription = None
    if provider_subscription_id:
        subscription = db.scalar(
            select(Subscription).where(Subscription.provider_subscription_id == provider_subscription_id)
        )

    if subscription is None:
        subscription = db.scalar(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.installation_id == (installation.id if installation else None),
                Subscription.provider == "paddle",
            )
        )

    if subscription is None:
        subscription = Subscription(
            user_id=user.id,
            installation_id=installation.id if installation else None,
            provider="paddle",
        )
        db.add(subscription)

    subscription.provider_customer_id = provider_customer_id or subscription.provider_customer_id
    subscription.provider_subscription_id = provider_subscription_id or subscription.provider_subscription_id
    subscription.status = entity_data.get("status") or subscription.status

    billing_period = entity_data.get("current_billing_period") or entity_data.get("billing_period") or {}
    subscription.current_period_start = _parse_rfc3339(billing_period.get("starts_at")) or subscription.current_period_start
    subscription.current_period_end = _parse_rfc3339(billing_period.get("ends_at")) or subscription.current_period_end
    db.commit()
    db.refresh(subscription)
    return subscription


def activate_license_from_subscription(db: Session, *, subscription: Subscription, entity_data: dict) -> License | None:
    if subscription.installation_id is None:
        return None

    installation = db.get(Installation, subscription.installation_id)
    if installation is None:
        return None

    billing_period = entity_data.get("current_billing_period") or entity_data.get("billing_period") or {}
    period_end = _parse_rfc3339(billing_period.get("ends_at"))
    period_start = _parse_rfc3339(billing_period.get("starts_at"))
    if period_end is None:
        return None

    return upsert_paid_license(
        db,
        user_id=subscription.user_id,
        installation=installation,
        plan="monthly",
        status="active",
        issued_at=period_start or utcnow(),
        expires_at=period_end,
    )


def mark_license_grace_or_expired(db: Session, *, subscription: Subscription) -> License | None:
    if subscription.installation_id is None:
        return None

    installation = db.get(Installation, subscription.installation_id)
    if installation is None:
        return None

    license_row = db.scalar(
        select(License).where(
            License.user_id == subscription.user_id,
            License.installation_id == installation.id,
        )
    )
    if license_row is None:
        return None

    if license_row.grace_until is not None and license_row.grace_until >= utcnow():
        license_row.status = "grace"
    else:
        license_row.status = "expired"

    sync_license_signature(db, license_row)
    return license_row


def process_paddle_webhook(db: Session, event: dict) -> str:
    event_type = (event.get("event_type") or "").replace("_", ".")
    entity_data = event.get("data") or {}

    if event_type in {"subscription.created", "subscription.updated", "subscription.activated"}:
        subscription = upsert_subscription_from_paddle(db, entity_data=entity_data)
        if subscription is not None and event_type == "subscription.activated":
            activate_license_from_subscription(db, subscription=subscription, entity_data=entity_data)
        return "processed"

    if event_type == "subscription.canceled":
        subscription = upsert_subscription_from_paddle(db, entity_data=entity_data)
        if subscription is not None:
            mark_license_grace_or_expired(db, subscription=subscription)
        return "processed"

    if event_type in {"transaction.paid", "transaction.completed"}:
        subscription = upsert_subscription_from_paddle(db, entity_data=entity_data)
        if subscription is not None:
            activate_license_from_subscription(db, subscription=subscription, entity_data=entity_data)
        return "processed"

    if event_type in {"transaction.payment.failed", "transaction.payment_failed", "transaction.past.due", "transaction.past_due"}:
        subscription = upsert_subscription_from_paddle(db, entity_data=entity_data)
        if subscription is not None:
            subscription.status = "past_due"
            db.commit()
            db.refresh(subscription)
            mark_license_grace_or_expired(db, subscription=subscription)
        return "processed"

    logger.info("Webhook ignorado event_type=%s", event_type)
    return "ignored"


def process_paddle_webhook_with_idempotency(db: Session, event: dict, *, raw_payload: str) -> dict:
    event_id = event.get("event_id")
    event_type = event.get("event_type") or "unknown"
    if not event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook Paddle sin event_id.")

    existing_event = get_webhook_event_by_event_id(db, provider="paddle", event_id=event_id)
    if existing_event is not None and existing_event.status == "processed":
        logger.info("Webhook duplicado ignorado provider=paddle event_id=%s", event_id)
        return {
            "event_id": event_id,
            "event_type": event_type,
            "status": "processed",
            "duplicated": True,
        }

    webhook_event = record_webhook_event_received(
        db,
        provider="paddle",
        event_id=event_id,
        event_type=event_type,
        payload=raw_payload,
    )

    try:
        processing_status = process_paddle_webhook(db, event)
        mark_webhook_event_status(db, webhook_event, status_value=processing_status)
        logger.info(
            "Webhook procesado provider=paddle event_id=%s event_type=%s status=%s",
            event_id,
            event_type,
            processing_status,
        )
        return {
            "event_id": event_id,
            "event_type": event_type,
            "status": processing_status,
            "duplicated": False,
        }
    except Exception as exc:
        mark_webhook_event_status(db, webhook_event, status_value="failed", error_message=str(exc))
        logger.exception("Webhook fallido provider=paddle event_id=%s event_type=%s", event_id, event_type)
        raise
