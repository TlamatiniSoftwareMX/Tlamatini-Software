from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UpdateCheckResponse(BaseModel):
    update_available: bool
    latest_version: str | None = None
    is_mandatory: bool = False
    title: str | None = None
    release_notes: str | None = None
    download_url: str | None = None
    sha256: str | None = None
    signature: str | None = None
    min_supported_version: str | None = None
    platform: str | None = None
    channel: str | None = None
    published_at: datetime | None = None


class AppReleaseCreate(BaseModel):
    version: str = Field(min_length=1, max_length=64)
    platform: str = Field(min_length=3, max_length=32)
    channel: str = Field(default="stable", min_length=3, max_length=32)
    title: str = Field(min_length=1, max_length=255)
    release_notes: str = Field(default="")
    download_url: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    signature: str | None = None
    is_mandatory: bool = False
    min_supported_version: str | None = Field(default=None, max_length=64)
    published_at: datetime | None = None
    is_active: bool = True


class AppReleaseRead(BaseModel):
    id: int
    version: str
    platform: str
    channel: str
    title: str
    release_notes: str
    download_url: str
    sha256: str
    signature: str | None
    is_mandatory: bool
    min_supported_version: str | None
    published_at: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
