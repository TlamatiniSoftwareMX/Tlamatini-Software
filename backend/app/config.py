from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    app_name: str = "TLAMATINI Backend"
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    api_base_url: str = Field(default="http://127.0.0.1:8000", alias="API_BASE_URL")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tlamatini_backend",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    license_private_key: str | None = Field(default=None, alias="LICENSE_PRIVATE_KEY")
    license_public_key: str | None = Field(default=None, alias="LICENSE_PUBLIC_KEY")
    license_signing_algorithm: str = Field(default="RS256", alias="LICENSE_SIGNING_ALGORITHM")
    license_signing_secret: str | None = Field(default=None, alias="LICENSE_SIGNING_SECRET")
    paddle_api_key: str = Field(default="placeholder", alias="PADDLE_API_KEY")
    paddle_webhook_secret: str = Field(default="placeholder", alias="PADDLE_WEBHOOK_SECRET")
    paddle_environment: str = Field(default="sandbox", alias="PADDLE_ENVIRONMENT")
    paddle_product_id: str = Field(default="placeholder-product", alias="PADDLE_PRODUCT_ID")
    paddle_price_id: str = Field(default="placeholder-price", alias="PADDLE_PRICE_ID")
    admin_api_key: str = Field(default="", alias="ADMIN_API_KEY")
    trial_days: int = Field(default=7, alias="TRIAL_DAYS")
    offline_grace_days: int = Field(default=30, alias="OFFLINE_GRACE_DAYS")
    auto_create_tables: bool = Field(default=True, alias="AUTO_CREATE_TABLES")
    force_https: bool = Field(default=False, alias="FORCE_HTTPS")
    allowed_hosts: str | None = Field(default=None, alias="ALLOWED_HOSTS")
    cors_allow_origins: str | None = Field(default=None, alias="CORS_ALLOW_ORIGINS")
    paddle_webhook_tolerance_seconds: int = Field(default=300, alias="PADDLE_WEBHOOK_TOLERANCE_SECONDS")

    @staticmethod
    def _is_placeholder(value: str | None) -> bool:
        normalized = str(value or "").strip().lower()
        return not normalized or normalized.startswith("placeholder") or normalized in {"replace-me", "changeme", "change-me"}

    @field_validator(
        "api_base_url",
        "database_url",
        "jwt_secret",
        "jwt_algorithm",
        "license_private_key",
        "license_public_key",
        "license_signing_algorithm",
        "license_signing_secret",
        "paddle_api_key",
        "paddle_webhook_secret",
        "paddle_environment",
        "paddle_product_id",
        "paddle_price_id",
        "admin_api_key",
        mode="before",
    )
    @classmethod
    def normalize_string_settings(cls, value: str | None):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("jwt_algorithm", "license_signing_algorithm", mode="after")
    @classmethod
    def normalize_algorithm(cls, value: str | None) -> str | None:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_production_security(self):
        if str(self.app_env or "").strip().lower() not in {"production", "prod"}:
            return self

        problems = []
        if not str(self.api_base_url or "").strip().lower().startswith("https://"):
            problems.append("API_BASE_URL debe usar HTTPS en producción")
        if not self.allowed_hosts_list():
            problems.append("ALLOWED_HOSTS debe configurarse en producción")
        if self.cors_allow_origins and "*" in self.cors_allow_origins_list():
            problems.append("CORS_ALLOW_ORIGINS no puede usar '*' en producción")
        if self.auto_create_tables:
            problems.append("AUTO_CREATE_TABLES debe estar desactivado en producción")
        if self._is_placeholder(self.jwt_secret):
            problems.append("JWT_SECRET no puede ser vacío ni placeholder")
        if self._is_placeholder(self.admin_api_key):
            problems.append("ADMIN_API_KEY no puede ser vacío ni placeholder")
        if self._is_placeholder(self.paddle_api_key):
            problems.append("PADDLE_API_KEY no puede ser vacío ni placeholder")
        if self._is_placeholder(self.paddle_webhook_secret):
            problems.append("PADDLE_WEBHOOK_SECRET no puede ser vacío ni placeholder")
        if self._is_placeholder(self.paddle_product_id):
            problems.append("PADDLE_PRODUCT_ID no puede ser vacío ni placeholder")
        if self._is_placeholder(self.paddle_price_id):
            problems.append("PADDLE_PRICE_ID no puede ser vacío ni placeholder")

        algorithm = str(self.license_signing_algorithm or "").upper()
        if algorithm.startswith("HS"):
            if self._is_placeholder(self.license_signing_secret):
                problems.append("LICENSE_SIGNING_SECRET es obligatorio para firma HS en producción")
        else:
            if self._is_placeholder(self.license_private_key) or self._is_placeholder(self.license_public_key):
                problems.append("LICENSE_PRIVATE_KEY y LICENSE_PUBLIC_KEY son obligatorias para firma asimétrica en producción")

        if problems:
            raise ValueError("Configuración insegura de producción: " + "; ".join(problems))
        return self

    @field_validator("paddle_webhook_tolerance_seconds", mode="after")
    @classmethod
    def validate_webhook_tolerance(cls, value: int) -> int:
        return max(30, min(int(value), 3600))

    def allowed_hosts_list(self) -> list[str]:
        raw = str(self.allowed_hosts or "").strip()
        return [item.strip() for item in raw.split(",") if item.strip()]

    def cors_allow_origins_list(self) -> list[str]:
        raw = str(self.cors_allow_origins or "").strip()
        return [item.strip() for item in raw.split(",") if item.strip()]

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
