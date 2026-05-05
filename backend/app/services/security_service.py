import hmac
import os
import threading
from datetime import timedelta

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.utils.time_utils import utcnow


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()
_LOGIN_ATTEMPT_LOCK = threading.RLock()
_FAILED_LOGIN_ATTEMPTS: dict[str, dict[str, float | int]] = {}
MAX_FAILED_LOGIN_ATTEMPTS = max(3, int(os.environ.get("MAX_FAILED_LOGIN_ATTEMPTS", "5") or "5"))
LOGIN_LOCKOUT_SECONDS = max(30, int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "300") or "300"))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(*, user_id: int) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def ensure_login_allowed(identifier: str) -> None:
    normalized = str(identifier or "").strip().lower()
    if not normalized:
        return
    with _LOGIN_ATTEMPT_LOCK:
        state = _FAILED_LOGIN_ATTEMPTS.get(normalized) or {}
        locked_until = float(state.get("locked_until", 0.0) or 0.0)
        if locked_until > utcnow().timestamp():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos. Espera unos minutos antes de volver a intentar.",
            )


def register_failed_login_attempt(identifier: str) -> None:
    normalized = str(identifier or "").strip().lower()
    if not normalized:
        return
    now_ts = utcnow().timestamp()
    with _LOGIN_ATTEMPT_LOCK:
        state = _FAILED_LOGIN_ATTEMPTS.get(normalized) or {"count": 0, "locked_until": 0.0}
        locked_until = float(state.get("locked_until", 0.0) or 0.0)
        if locked_until <= now_ts:
            state["locked_until"] = 0.0
        state["count"] = int(state.get("count", 0) or 0) + 1
        if state["count"] >= MAX_FAILED_LOGIN_ATTEMPTS:
            state["count"] = 0
            state["locked_until"] = now_ts + LOGIN_LOCKOUT_SECONDS
        _FAILED_LOGIN_ATTEMPTS[normalized] = state


def clear_failed_login_attempts(identifier: str) -> None:
    normalized = str(identifier or "").strip().lower()
    if not normalized:
        return
    with _LOGIN_ATTEMPT_LOCK:
        _FAILED_LOGIN_ATTEMPTS.pop(normalized, None)


def require_admin_api_key(x_admin_api_key: str | None = Header(default=None)) -> None:
    expected = settings.admin_api_key.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY no está configurada.",
        )
    candidate = str(x_admin_api_key or "").strip()
    if not hmac.compare_digest(candidate, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ADMIN_API_KEY inválida.")
