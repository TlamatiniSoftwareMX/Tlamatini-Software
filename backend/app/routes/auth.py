from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import AuthTokenResponse, UserCreate, UserLogin, UserProfile, UserRead
from app.services.security_service import (
    clear_failed_login_attempts,
    create_access_token,
    ensure_login_allowed,
    get_current_user,
    hash_password,
    register_failed_login_attempt,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def auth_status():
    return {
        "status": "ready",
        "message": "Registro, login con JWT y perfil autenticado disponibles.",
    }


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese email.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        preferred_language=payload.preferred_language,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=AuthTokenResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    ensure_login_allowed(normalized_email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not verify_password(payload.password, user.password_hash):
        register_failed_login_attempt(normalized_email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El usuario está inactivo.")

    clear_failed_login_attempts(normalized_email)
    access_token = create_access_token(user_id=user.id)
    return AuthTokenResponse(access_token=access_token, user=UserProfile.model_validate(user))


@router.get("/me", response_model=UserProfile)
def get_authenticated_profile(current_user: User = Depends(get_current_user)):
    return current_user
