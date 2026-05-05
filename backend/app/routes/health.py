from fastapi import APIRouter

from app.config import get_settings


router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
def health():
    return {"status": "ok", "environment": settings.app_env}


@router.get("/version")
def version():
    return {"version": settings.app_version, "service": settings.app_name}
