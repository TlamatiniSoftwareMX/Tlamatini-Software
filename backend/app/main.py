from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.database import create_db_and_tables
from app.routes.auth import router as auth_router
from app.routes.billing import router as billing_router
from app.routes.health import router as health_router
from app.routes.installations import router as installations_router
from app.routes.licenses import router as licenses_router
from app.routes.updates import router as updates_router


settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

allowed_hosts = settings.allowed_hosts_list()
if allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

cors_origins = settings.cors_allow_origins_list()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-Api-Key"],
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(ValueError)
async def handle_value_error(_request: Request, exc: ValueError):
    message = str(exc)
    if message.startswith("Configuración insegura de producción:"):
        return JSONResponse(status_code=503, content={"detail": message})
    return JSONResponse(status_code=500, content={"detail": "Error interno de configuración o validación."})

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(installations_router)
app.include_router(licenses_router)
app.include_router(updates_router)


@app.get("/", tags=["root"])
def root():
    return {
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": settings.app_version,
        "status": "ok",
    }
