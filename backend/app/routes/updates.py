from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.update import AppReleaseCreate, AppReleaseRead, UpdateCheckResponse
from app.services.security_service import require_admin_api_key
from app.services.update_service import build_update_check_response, create_release

router = APIRouter(prefix="/updates", tags=["updates"])


@router.get("/check", response_model=UpdateCheckResponse)
def check_updates(
    current_version: str = Query(..., min_length=1, max_length=64),
    platform: str = Query(..., min_length=3, max_length=32),
    channel: str = Query(default="stable", min_length=3, max_length=32),
    db: Session = Depends(get_db),
):
    return build_update_check_response(
        db,
        current_version=current_version,
        platform=platform,
        channel=channel,
    )


@router.post("/releases", response_model=AppReleaseRead, status_code=status.HTTP_201_CREATED)
def create_update_release(
    payload: AppReleaseCreate,
    _admin: None = Depends(require_admin_api_key),
    db: Session = Depends(get_db),
):
    return create_release(db, payload)
