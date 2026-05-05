from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LicenseTrialRequest(BaseModel):
    installation_id: str = Field(min_length=3, max_length=128)


class LicenseVerifyRequest(BaseModel):
    signed_payload: str


class LicenseRevokeRequest(BaseModel):
    installation_id: str = Field(min_length=3, max_length=128)


class LicenseVerifyResponse(BaseModel):
    is_valid: bool
    payload: dict | None = None
    detail: str


class LicenseStatusResponse(BaseModel):
    status: str
    plan: str
    license_id: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    grace_until: datetime | None = None
    signed_payload: str | None = None
    days_remaining: int | None = None
    is_valid: bool
    offline_grace_days: int
    trial_days: int


class LicenseRead(BaseModel):
    id: int
    user_id: int | None
    installation_id: int | None
    license_id: str
    plan: str
    status: str
    issued_at: datetime
    expires_at: datetime | None
    grace_until: datetime | None
    signed_payload: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
