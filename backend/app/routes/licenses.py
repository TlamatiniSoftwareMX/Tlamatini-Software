import logging

from jwt import InvalidTokenError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.installation import Installation
from app.models.user import User
from app.schemas.license import (
    LicenseRead,
    LicenseRevokeRequest,
    LicenseStatusResponse,
    LicenseTrialRequest,
    LicenseVerifyRequest,
    LicenseVerifyResponse,
)
from app.services.license_service import (
    compute_license_status,
    create_trial_license,
    get_current_license,
    revoke_license,
    verify_license_payload,
)
from app.services.security_service import get_current_user


router = APIRouter(prefix="/licenses", tags=["licenses"])
logger = logging.getLogger(__name__)


@router.post("/trial", response_model=LicenseStatusResponse)
def create_trial(
    payload: LicenseTrialRequest,
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

    try:
        license_row = create_trial_license(db, current_user, installation)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while creating trial license")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de base de datos al crear la licencia trial.",
        ) from exc
    return compute_license_status(license_row)


@router.get("/status", response_model=LicenseStatusResponse)
def license_status(
    installation_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    installation = db.scalar(
        select(Installation).where(
            Installation.installation_id == installation_id,
            Installation.user_id == current_user.id,
        )
    )
    if installation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instalación no encontrada para el usuario.")

    try:
        license_row = get_current_license(db, user_id=current_user.id, installation_db_id=installation.id)
    except SQLAlchemyError as exc:
        logger.exception("Database error while fetching license status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de base de datos al consultar la licencia.",
        ) from exc
    return compute_license_status(license_row)


@router.post("/verify", response_model=LicenseVerifyResponse)
def verify_license(payload: LicenseVerifyRequest):
    try:
        decoded_payload = verify_license_payload(payload.signed_payload)
    except InvalidTokenError:
        return LicenseVerifyResponse(is_valid=False, payload=None, detail="Firma inválida.")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return LicenseVerifyResponse(is_valid=True, payload=decoded_payload, detail="Firma válida.")


@router.post("/revoke", response_model=LicenseRead)
def revoke_license_endpoint(
    payload: LicenseRevokeRequest,
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

    license_row = get_current_license(db, user_id=current_user.id, installation_db_id=installation.id)
    if license_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe licencia para esa instalación.")

    try:
        return revoke_license(db, license_row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while revoking license")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de base de datos al revocar la licencia.",
        ) from exc
