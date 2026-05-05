from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.license_service import sign_license_payload
from app.models.app_release import AppRelease
from app.schemas.update import AppReleaseCreate, UpdateCheckResponse
from app.utils.time_utils import utcnow


SUPPORTED_PLATFORMS = {"linux", "windows", "macos"}
SUPPORTED_CHANNELS = {"stable", "beta", "dev"}
_VERSION_PARTS_RE = re.compile(r"[0-9]+|[a-zA-Z]+")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_platform(value: str) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {"darwin": "macos", "mac": "macos", "osx": "macos", "win32": "windows"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"platform debe ser uno de: {', '.join(sorted(SUPPORTED_PLATFORMS))}.",
        )
    return normalized


def normalize_channel(value: str | None) -> str:
    normalized = str(value or "stable").strip().lower()
    if normalized not in SUPPORTED_CHANNELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"channel debe ser uno de: {', '.join(sorted(SUPPORTED_CHANNELS))}.",
        )
    return normalized


def validate_download_url(value: str) -> str:
    normalized = str(value or "").strip()
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="download_url debe usar HTTPS y un host válido.",
        )
    if parsed.params or parsed.query or parsed.fragment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="download_url no puede incluir parámetros inseguros ni fragmentos.",
        )
    return normalized


def validate_sha256(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sha256 debe ser hex válido de 64 caracteres.")
    return normalized


def _version_key(value: str) -> tuple:
    cleaned = str(value or "").strip().lower().lstrip("v")
    if not cleaned:
        return ((0, 0),)
    parts = []
    for token in _VERSION_PARTS_RE.findall(cleaned):
        if token.isdigit():
            parts.append((1, int(token)))
        else:
            parts.append((0, token))
    return tuple(parts or [(0, cleaned)])


def compare_versions(left: str, right: str) -> int:
    left_key = list(_version_key(left))
    right_key = list(_version_key(right))
    total = max(len(left_key), len(right_key))
    for index in range(total):
        left_part = left_key[index] if index < len(left_key) else (1, 0)
        right_part = right_key[index] if index < len(right_key) else (1, 0)
        if left_part < right_part:
            return -1
        if left_part > right_part:
            return 1
    return 0


def build_release_signature_payload(
    *,
    version: str,
    platform: str,
    channel: str,
    download_url: str,
    sha256: str,
    is_mandatory: bool,
    min_supported_version: str | None,
) -> dict:
    return {
        "purpose": "update_release",
        "version": str(version or "").strip(),
        "platform": str(platform or "").strip().lower(),
        "channel": str(channel or "").strip().lower(),
        "download_url": str(download_url or "").strip(),
        "sha256": str(sha256 or "").strip().lower(),
        "is_mandatory": bool(is_mandatory),
        "min_supported_version": str(min_supported_version or "").strip() or "",
    }


def sign_release_payload(payload: dict) -> str:
    return sign_license_payload(payload)


def create_release(db: Session, payload: AppReleaseCreate) -> AppRelease:
    platform = normalize_platform(payload.platform)
    channel = normalize_channel(payload.channel)
    download_url = validate_download_url(payload.download_url)
    sha256 = validate_sha256(payload.sha256)
    signature_payload = build_release_signature_payload(
        version=payload.version,
        platform=platform,
        channel=channel,
        download_url=download_url,
        sha256=sha256,
        is_mandatory=payload.is_mandatory,
        min_supported_version=payload.min_supported_version,
    )
    release = AppRelease(
        version=payload.version.strip(),
        platform=platform,
        channel=channel,
        title=payload.title.strip(),
        release_notes=payload.release_notes.strip(),
        download_url=download_url,
        sha256=sha256,
        signature=(payload.signature or "").strip() or sign_release_payload(signature_payload),
        is_mandatory=payload.is_mandatory,
        min_supported_version=(payload.min_supported_version or "").strip() or None,
        published_at=payload.published_at or utcnow(),
        is_active=payload.is_active,
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


def list_releases_for_target(db: Session, *, platform: str, channel: str) -> list[AppRelease]:
    query = (
        select(AppRelease)
        .where(
            AppRelease.platform == platform,
            AppRelease.channel == channel,
            AppRelease.is_active.is_(True),
        )
        .order_by(AppRelease.published_at.desc(), AppRelease.id.desc())
    )
    return list(db.scalars(query).all())


def select_latest_release(db: Session, *, platform: str, channel: str) -> AppRelease | None:
    releases = list_releases_for_target(db, platform=platform, channel=channel)
    if not releases:
        return None
    return max(releases, key=lambda item: (_version_key(item.version), item.published_at, item.id))


def select_update_release(
    db: Session,
    *,
    current_version: str,
    platform: str,
    channel: str,
) -> AppRelease | None:
    latest = select_latest_release(db, platform=platform, channel=channel)
    if latest is None:
        return None
    if compare_versions(latest.version, current_version) <= 0:
        return None
    return latest


def build_update_check_response(
    db: Session,
    *,
    current_version: str,
    platform: str,
    channel: str,
) -> UpdateCheckResponse:
    normalized_platform = normalize_platform(platform)
    normalized_channel = normalize_channel(channel)
    release = select_update_release(
        db,
        current_version=current_version,
        platform=normalized_platform,
        channel=normalized_channel,
    )
    if release is None:
        return UpdateCheckResponse(
            update_available=False,
            latest_version=current_version,
            platform=normalized_platform,
            channel=normalized_channel,
        )

    is_mandatory = release.is_mandatory
    if release.min_supported_version and compare_versions(current_version, release.min_supported_version) < 0:
        is_mandatory = True

    return UpdateCheckResponse(
        update_available=True,
        latest_version=release.version,
        is_mandatory=is_mandatory,
        title=release.title,
        release_notes=release.release_notes,
        download_url=release.download_url,
        sha256=release.sha256,
        signature=release.signature,
        min_supported_version=release.min_supported_version,
        platform=release.platform,
        channel=release.channel,
        published_at=release.published_at,
    )
