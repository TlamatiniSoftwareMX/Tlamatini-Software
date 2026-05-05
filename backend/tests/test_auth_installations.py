import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException

from app.database import Base, SessionLocal, engine
from app.models import app_release, billing_webhook_event, installation, license, subscription, user  # noqa: F401
from app.models.billing_webhook_event import BillingWebhookEvent
from app.routes.auth import get_authenticated_profile, login_user, register_user
from app.routes.billing import create_checkout, list_webhook_events
from app.routes.installations import list_installations, register_installation
from app.routes.licenses import create_trial, license_status, verify_license
from app.routes.updates import check_updates, create_update_release, require_admin_api_key
from app.schemas.billing import BillingCheckoutRequest
from app.schemas.installation import InstallationRegisterRequest
from app.schemas.license import LicenseTrialRequest, LicenseVerifyRequest
from app.schemas.update import AppReleaseCreate
from app.schemas.user import UserCreate, UserLogin
from app.services.billing_service import (
    process_paddle_webhook_with_idempotency,
    verify_paddle_webhook_signature,
)
from app.services.security_service import ensure_login_allowed, register_failed_login_attempt


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def build_paddle_signature(raw_body: bytes) -> str:
    ts = str(int(time.time()))
    digest = hmac.new(
        b"test-paddle-webhook-secret",
        ts.encode("utf-8") + b":" + raw_body,
        hashlib.sha256,
    ).hexdigest()
    return f"ts={ts};h1={digest}"


def build_transaction_completed_event(*, installation_id: str, installation_db_id: int, event_id: str) -> dict:
    return {
        "event_id": event_id,
        "event_type": "transaction.completed",
        "occurred_at": "2026-04-24T12:00:00Z",
        "notification_id": f"ntf_{event_id}",
        "data": {
            "id": f"txn_{event_id}",
            "customer_id": "ctm_001",
            "subscription_id": "sub_001",
            "status": "completed",
            "custom_data": {
                "user_id": 1,
                "installation_id": installation_id,
                "installation_db_id": installation_db_id,
                "price_id": "pri_test",
                "product_id": "pro_test",
            },
            "billing_period": {
                "starts_at": "2026-04-24T12:00:00Z",
                "ends_at": "2026-05-24T12:00:00Z",
            },
        },
    }


def create_user_and_installation(db, *, email: str, installation_id: str):
    user_read = register_user(
        UserCreate(email=email, password="ClaveSegura123", preferred_language="es"),
        db=db,
    )
    login_payload = login_user(
        UserLogin(email=email, password="ClaveSegura123"),
        db=db,
    )
    current_user = db.get(user.User, user_read.id)
    installation_read = register_installation(
        InstallationRegisterRequest(
            installation_id=installation_id,
            device_name="Equipo TLAMATINI",
            os_name="Linux",
            app_version="0.1.0",
        ),
        db=db,
        current_user=current_user,
    )
    return current_user, login_payload, installation_read


def create_release(db, *, version: str, platform: str = "linux", channel: str = "stable", mandatory: bool = False):
    return create_update_release(
        AppReleaseCreate(
            version=version,
            platform=platform,
            channel=channel,
            title=f"TLAMATINI {version}",
            release_notes=f"Cambios de {version}",
            download_url=f"https://downloads.example.com/tlamatini-{platform}-{version}.zip",
            sha256="a" * 64,
            signature=None,
            is_mandatory=mandatory,
            min_supported_version="5.0.0",
        ),
        _admin=None,
        db=db,
    )


def test_auth_and_installations_flow():
    reset_database()
    db = SessionLocal()
    try:
        registered_user = register_user(
            UserCreate(email="persona@example.com", password="ClaveSegura123", preferred_language="es"),
            db=db,
        )
        assert registered_user.email == "persona@example.com"

        login_payload = login_user(
            UserLogin(email="persona@example.com", password="ClaveSegura123"),
            db=db,
        )
        assert login_payload.token_type == "bearer"
        assert login_payload.user.id == registered_user.id

        current_user = db.get(user.User, registered_user.id)
        profile = get_authenticated_profile(current_user=current_user)
        assert profile.email == "persona@example.com"

        installation_payload = register_installation(
            InstallationRegisterRequest(
                installation_id="inst-local-001",
                device_name="Laptop Operativa",
                os_name="Linux",
                app_version="0.1.0",
            ),
            db=db,
            current_user=current_user,
        )
        assert installation_payload.user_id == registered_user.id
        assert installation_payload.installation_id == "inst-local-001"

        installation_update = register_installation(
            InstallationRegisterRequest(
                installation_id="inst-local-001",
                device_name="Laptop Operativa",
                os_name="Linux",
                app_version="0.1.1",
            ),
            db=db,
            current_user=current_user,
        )
        assert installation_update.app_version == "0.1.1"

        installations_payload = list_installations(db=db, current_user=current_user)
        assert len(installations_payload) == 1
        assert installations_payload[0].installation_id == "inst-local-001"
    finally:
        db.close()


def test_duplicate_register_and_invalid_login():
    reset_database()
    db = SessionLocal()
    try:
        register_user(
            UserCreate(email="duplicado@example.com", password="ClaveSegura123", preferred_language="es"),
            db=db,
        )
        with pytest.raises(HTTPException) as duplicate_exc:
            register_user(
                UserCreate(email="duplicado@example.com", password="ClaveSegura123", preferred_language="es"),
                db=db,
            )
        assert duplicate_exc.value.status_code == 409

        with pytest.raises(HTTPException) as invalid_exc:
            login_user(
                UserLogin(email="duplicado@example.com", password="otra-clave-incorrecta"),
                db=db,
            )
        assert invalid_exc.value.status_code == 401
    finally:
        db.close()


def test_login_lockout_after_repeated_failures():
    reset_database()
    db = SessionLocal()
    try:
        register_user(
            UserCreate(email="lock@example.com", password="ClaveSegura123", preferred_language="es"),
            db=db,
        )
        for _ in range(5):
            with pytest.raises(HTTPException):
                login_user(UserLogin(email="lock@example.com", password="incorrecta"), db=db)
        with pytest.raises(HTTPException) as locked_exc:
            ensure_login_allowed("lock@example.com")
        assert locked_exc.value.status_code == 429
    finally:
        db.close()


def test_trial_license_flow_and_verify():
    reset_database()
    db = SessionLocal()
    try:
        current_user, _login, installation_payload = create_user_and_installation(
            db,
            email="licencias@example.com",
            installation_id="inst-lic-001",
        )

        first_trial = create_trial(
            LicenseTrialRequest(installation_id="inst-lic-001"),
            db=db,
            current_user=current_user,
        )
        assert first_trial["status"] == "trial"
        assert first_trial["plan"] == "trial"
        assert first_trial["is_valid"] is True
        assert first_trial["license_id"].startswith("lic_")
        assert first_trial["signed_payload"]

        second_trial = create_trial(
            LicenseTrialRequest(installation_id="inst-lic-001"),
            db=db,
            current_user=current_user,
        )
        assert second_trial["license_id"] == first_trial["license_id"]
        assert second_trial["signed_payload"] == first_trial["signed_payload"]

        current_status = license_status(
            installation_id="inst-lic-001",
            db=db,
            current_user=current_user,
        )
        assert current_status["license_id"] == first_trial["license_id"]
        assert current_status["is_valid"] is True

        verify_valid = verify_license(LicenseVerifyRequest(signed_payload=first_trial["signed_payload"]))
        assert verify_valid.is_valid is True
        assert verify_valid.payload["license_id"] == first_trial["license_id"]
        assert verify_valid.payload["installation_id"] == "inst-lic-001"

        verify_invalid = verify_license(LicenseVerifyRequest(signed_payload=f"{first_trial['signed_payload']}corrupto"))
        assert verify_invalid.is_valid is False

        assert installation_payload.installation_id == "inst-lic-001"
    finally:
        db.close()


def test_create_checkout_returns_paddle_url(monkeypatch):
    reset_database()
    db = SessionLocal()
    try:
        current_user, _login, _installation = create_user_and_installation(
            db,
            email="billing@example.com",
            installation_id="inst-billing-001",
        )

        def fake_create_checkout_transaction(*, user, installation, country_code, postal_code):
            assert user.email == "billing@example.com"
            assert installation.installation_id == "inst-billing-001"
            assert country_code == "MX"
            assert postal_code == "91000"
            return {
                "id": "txn_test_001",
                "status": "ready",
                "customer_id": "ctm_test_001",
                "subscription_id": None,
                "checkout": {"url": "https://sandbox-checkout.test/txn_test_001"},
            }

        monkeypatch.setattr("app.routes.billing.create_checkout_transaction", fake_create_checkout_transaction)
        payload = create_checkout(
            BillingCheckoutRequest(
                installation_id="inst-billing-001",
                country_code="MX",
                postal_code="91000",
            ),
            db=db,
            current_user=current_user,
        )
        assert payload.checkout_url == "https://sandbox-checkout.test/txn_test_001"
        assert payload.transaction_id == "txn_test_001"
        assert payload.provider_customer_id == "ctm_test_001"
    finally:
        db.close()


def test_paddle_webhook_activates_monthly_license():
    reset_database()
    db = SessionLocal()
    try:
        current_user, _login, installation_payload = create_user_and_installation(
            db,
            email="paddle@example.com",
            installation_id="inst-paddle-001",
        )
        create_trial(
            LicenseTrialRequest(installation_id="inst-paddle-001"),
            db=db,
            current_user=current_user,
        )

        event = build_transaction_completed_event(
            installation_id="inst-paddle-001",
            installation_db_id=installation_payload.id,
            event_id="evt_001",
        )
        raw_body = json.dumps(event).encode("utf-8")
        verify_paddle_webhook_signature(raw_body=raw_body, signature_header=build_paddle_signature(raw_body))
        result = process_paddle_webhook_with_idempotency(db, event, raw_payload=raw_body.decode("utf-8"))
        assert result["status"] == "processed"
        assert result["duplicated"] is False

        status_payload = license_status(
            installation_id="inst-paddle-001",
            db=db,
            current_user=current_user,
        )
        assert status_payload["status"] == "active"
        assert status_payload["plan"] == "monthly"
        assert status_payload["is_valid"] is True
        assert status_payload["signed_payload"]

        events = list(db.query(BillingWebhookEvent).all())
        assert len(events) == 1
        assert events[0].event_id == "evt_001"
        assert events[0].status == "processed"
    finally:
        db.close()


def test_paddle_webhook_invalid_signature_is_rejected():
    reset_database()
    with pytest.raises(HTTPException) as exc:
        verify_paddle_webhook_signature(
            raw_body=json.dumps({"event_id": "evt_bad"}).encode("utf-8"),
            signature_header="ts=1;h1=invalida",
        )
    assert exc.value.status_code == 401


def test_paddle_webhook_expired_timestamp_is_rejected():
    reset_database()
    raw_body = json.dumps({"event_id": "evt_old"}).encode("utf-8")
    ts = str(int(time.time()) - 3600)
    digest = hmac.new(
        b"test-paddle-webhook-secret",
        ts.encode("utf-8") + b":" + raw_body,
        hashlib.sha256,
    ).hexdigest()
    with pytest.raises(HTTPException) as exc:
        verify_paddle_webhook_signature(
            raw_body=raw_body,
            signature_header=f"ts={ts};h1={digest}",
        )
    assert exc.value.status_code == 401


def test_paddle_webhook_duplicate_is_not_reprocessed():
    reset_database()
    db = SessionLocal()
    try:
        _current_user, _login, installation_payload = create_user_and_installation(
            db,
            email="dup@example.com",
            installation_id="inst-dup-001",
        )
        event = build_transaction_completed_event(
            installation_id="inst-dup-001",
            installation_db_id=installation_payload.id,
            event_id="evt_dup_001",
        )
        raw_body = json.dumps(event).encode("utf-8")
        first = process_paddle_webhook_with_idempotency(db, event, raw_payload=raw_body.decode("utf-8"))
        duplicate = process_paddle_webhook_with_idempotency(db, event, raw_payload=raw_body.decode("utf-8"))
        assert first["duplicated"] is False
        assert duplicate["duplicated"] is True
        events = list(db.query(BillingWebhookEvent).all())
        assert len(events) == 1
        assert events[0].status == "processed"
    finally:
        db.close()


def test_paddle_webhook_unknown_event_is_ignored():
    reset_database()
    db = SessionLocal()
    try:
        create_user_and_installation(
            db,
            email="unknown@example.com",
            installation_id="inst-unknown-001",
        )
        event = {
            "event_id": "evt_unknown_001",
            "event_type": "adjustment.created",
            "occurred_at": "2026-04-24T12:00:00Z",
            "notification_id": "ntf_unknown_001",
            "data": {},
        }
        raw_body = json.dumps(event).encode("utf-8")
        result = process_paddle_webhook_with_idempotency(db, event, raw_payload=raw_body.decode("utf-8"))
        assert result["status"] == "ignored"
        events = list(db.query(BillingWebhookEvent).all())
        assert len(events) == 1
        assert events[0].status == "ignored"
    finally:
        db.close()


def test_webhook_events_require_admin_key_and_return_records():
    reset_database()
    db = SessionLocal()
    try:
        _current_user, _login, installation_payload = create_user_and_installation(
            db,
            email="admin-events@example.com",
            installation_id="inst-admin-events-001",
        )
        event = build_transaction_completed_event(
            installation_id="inst-admin-events-001",
            installation_db_id=installation_payload.id,
            event_id="evt_admin_001",
        )
        raw_body = json.dumps(event).encode("utf-8")
        process_paddle_webhook_with_idempotency(db, event, raw_payload=raw_body.decode("utf-8"))

        with pytest.raises(HTTPException) as exc:
            require_admin_api_key("incorrecta")
        assert exc.value.status_code == 401

        require_admin_api_key("test-admin-api-key")
        events = list_webhook_events(limit=10, _admin=None, db=db)
        assert len(events) == 1
        assert events[0].event_id == "evt_admin_001"
    finally:
        db.close()


def test_updates_check_without_available_release():
    reset_database()
    db = SessionLocal()
    try:
        create_release(db, version="5.1.0", platform="linux", channel="stable")
        payload = check_updates(current_version="5.1.0", platform="linux", channel="stable", db=db)
        assert payload.update_available is False
        assert payload.latest_version == "5.1.0"
    finally:
        db.close()


def test_updates_check_with_newer_release_and_mandatory_flag():
    reset_database()
    db = SessionLocal()
    try:
        release = create_release(db, version="5.2.0", platform="linux", channel="stable", mandatory=True)
        payload = check_updates(current_version="5.1.0", platform="linux", channel="stable", db=db)
        assert payload.update_available is True
        assert payload.latest_version == "5.2.0"
        assert payload.is_mandatory is True
        assert payload.download_url.endswith("tlamatini-linux-5.2.0.zip")
        assert payload.signature == release.signature
    finally:
        db.close()


def test_updates_check_filters_by_platform():
    reset_database()
    db = SessionLocal()
    try:
        create_release(db, version="5.3.0", platform="windows", channel="stable")
        payload = check_updates(current_version="5.1.0", platform="linux", channel="stable", db=db)
        assert payload.update_available is False
    finally:
        db.close()


def test_updates_release_requires_admin_api_key():
    with pytest.raises(HTTPException) as exc:
        require_admin_api_key(None)
    assert exc.value.status_code == 401


def test_updates_check_marks_release_mandatory_if_current_below_min_supported():
    reset_database()
    db = SessionLocal()
    try:
        create_update_release(
            AppReleaseCreate(
                version="5.4.0",
                platform="linux",
                channel="stable",
                title="TLAMATINI 5.4.0",
                release_notes="Compatibilidad endurecida",
                download_url="https://downloads.example.com/tlamatini-linux-5.4.0.zip",
                sha256="c" * 64,
                min_supported_version="5.3.0",
                is_mandatory=False,
            ),
            _admin=None,
            db=db,
        )
        payload = check_updates(current_version="5.1.0", platform="linux", channel="stable", db=db)
        assert payload.update_available is True
        assert payload.is_mandatory is True
    finally:
        db.close()
