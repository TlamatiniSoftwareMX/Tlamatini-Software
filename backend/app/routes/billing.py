import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.billing_webhook_event import BillingWebhookEvent
from app.models.installation import Installation
from app.models.user import User
from app.schemas.billing import (
    BillingCheckoutRequest,
    BillingCheckoutResponse,
    BillingWebhookEventRead,
    BillingWebhookResponse,
)
from app.services.billing_service import (
    create_checkout_transaction,
    ensure_pending_subscription,
    process_paddle_webhook_with_idempotency,
    verify_paddle_webhook_signature,
)
from app.services.security_service import get_current_user, require_admin_api_key


router = APIRouter(prefix="/billing", tags=["billing"])
MAX_WEBHOOK_BODY_BYTES = 512 * 1024


@router.post("/create-checkout", response_model=BillingCheckoutResponse)
def create_checkout(
    payload: BillingCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    installation = db.scalar(
        select(Installation).where(
            Installation.installation_id == payload.installation_id,
            Installation.user_id == current_user.id,
        )
    )
    if installation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instalación no encontrada para el usuario.")

    transaction = create_checkout_transaction(
        user=current_user,
        installation=installation,
        country_code=payload.country_code,
        postal_code=payload.postal_code,
    )
    ensure_pending_subscription(
        db,
        user_id=current_user.id,
        installation_id=installation.id,
        provider_customer_id=transaction.get("customer_id"),
    )
    checkout = transaction.get("checkout") or {}
    checkout_url = checkout.get("url")
    if not checkout_url:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Paddle no devolvió checkout.url.")

    return BillingCheckoutResponse(
        checkout_url=checkout_url,
        transaction_id=transaction["id"],
        provider_customer_id=transaction.get("customer_id"),
        provider_subscription_id=transaction.get("subscription_id"),
        status=transaction.get("status", "draft"),
    )


@router.post("/webhook", response_model=BillingWebhookResponse)
async def paddle_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    if len(raw_body) > MAX_WEBHOOK_BODY_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload de webhook demasiado grande.")
    signature_header = request.headers.get("Paddle-Signature")
    verify_paddle_webhook_signature(raw_body=raw_body, signature_header=signature_header)
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON inválido.") from exc
    result = process_paddle_webhook_with_idempotency(db, event, raw_payload=raw_body.decode("utf-8"))
    return BillingWebhookResponse(
        accepted=True,
        event_type=result["event_type"],
        event_id=result["event_id"],
        status=result["status"],
        duplicated=result["duplicated"],
    )


@router.get("/webhook-events", response_model=list[BillingWebhookEventRead])
def list_webhook_events(
    limit: int = 50,
    _admin: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit debe estar entre 1 y 200.")

    query = (
        select(BillingWebhookEvent)
        .where(BillingWebhookEvent.provider == "paddle")
        .order_by(BillingWebhookEvent.received_at.desc(), BillingWebhookEvent.id.desc())
        .limit(limit)
    )
    return list(db.scalars(query).all())
