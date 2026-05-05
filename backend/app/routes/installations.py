from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.installation import Installation
from app.models.user import User
from app.schemas.installation import InstallationRead, InstallationRegisterRequest
from app.services.security_service import get_current_user
from app.utils.time_utils import utcnow


router = APIRouter(prefix="/installations", tags=["installations"])


@router.post("/register", response_model=InstallationRead)
def register_installation(
    payload: InstallationRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    installation = db.scalar(select(Installation).where(Installation.installation_id == payload.installation_id))
    if installation is None:
        installation = Installation(
            user_id=current_user.id,
            installation_id=payload.installation_id,
            device_name=payload.device_name,
            os_name=payload.os_name,
            app_version=payload.app_version,
            last_seen_at=utcnow(),
        )
        db.add(installation)
    else:
        if installation.user_id is None:
            installation.user_id = current_user.id
        elif installation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La instalación ya está asociada a otro usuario.",
            )

        installation.device_name = payload.device_name
        installation.os_name = payload.os_name
        installation.app_version = payload.app_version
        installation.last_seen_at = utcnow()
    db.commit()
    db.refresh(installation)
    return installation


@router.get("", response_model=list[InstallationRead])
def list_installations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Installation)
        .where(Installation.user_id == current_user.id)
        .order_by(Installation.last_seen_at.desc(), Installation.id.desc())
    )
    return list(db.scalars(query).all())
