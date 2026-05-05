from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InstallationRegisterRequest(BaseModel):
    installation_id: str = Field(min_length=3, max_length=128)
    device_name: str = Field(min_length=1, max_length=255)
    os_name: str = Field(min_length=1, max_length=120)
    app_version: str = Field(min_length=1, max_length=64)


class InstallationRead(BaseModel):
    id: int
    user_id: int | None
    installation_id: str
    device_name: str
    os_name: str
    app_version: str
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
