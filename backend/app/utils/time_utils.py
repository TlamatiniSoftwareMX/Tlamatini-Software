from datetime import UTC, datetime, timedelta


def utcnow() -> datetime:
    return datetime.now(UTC)


def add_days(value: datetime | None, days: int) -> datetime | None:
    if value is None:
        return None
    return value + timedelta(days=days)
