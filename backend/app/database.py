from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


engine_kwargs = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def _sqlite_column_exists(columns: set[str], name: str) -> bool:
    return name in columns


def _add_column_if_missing(table: str, columns: set[str], column_name: str, ddl: str) -> bool:
    if _sqlite_column_exists(columns, column_name):
        return False
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {ddl}"))
    columns.add(column_name)
    return True


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_db_and_tables() -> None:
    if not settings.auto_create_tables:
        return
    from app.models import app_release, billing_webhook_event, installation, license, subscription, user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    run_startup_migrations()


def run_startup_migrations() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "installations" in table_names:
        installation_columns = {column["name"] for column in inspector.get_columns("installations")}
        if "updated_at" not in installation_columns:
            column_type = "TIMESTAMP"
            if engine.dialect.name == "postgresql":
                column_type = "TIMESTAMP WITH TIME ZONE"

            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"ALTER TABLE installations ADD COLUMN updated_at {column_type} "
                        "DEFAULT CURRENT_TIMESTAMP NOT NULL"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE installations "
                        "SET updated_at = COALESCE(updated_at, created_at, last_seen_at, CURRENT_TIMESTAMP)"
                    )
                )

    if "licenses" not in table_names:
        license_columns = set()
    else:
        license_columns = {column["name"] for column in inspector.get_columns("licenses")}
        if "license_id" not in license_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE licenses ADD COLUMN license_id VARCHAR(255)"))
                if "license_key" in license_columns:
                    connection.execute(text("UPDATE licenses SET license_id = license_key WHERE license_id IS NULL"))
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_licenses_license_id ON licenses (license_id)"))
                license_columns.add("license_id")
        if _add_column_if_missing("licenses", license_columns, "grace_until", "TIMESTAMP"):
            with engine.begin() as connection:
                connection.execute(text("UPDATE licenses SET grace_until = expires_at WHERE grace_until IS NULL"))
        _add_column_if_missing("licenses", license_columns, "signed_payload", "TEXT")
        if _add_column_if_missing("licenses", license_columns, "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE licenses "
                        "SET updated_at = COALESCE(updated_at, created_at, issued_at, expires_at, CURRENT_TIMESTAMP)"
                    )
                )

    if "subscriptions" not in table_names:
        return

    subscription_columns = {column["name"] for column in inspector.get_columns("subscriptions")}
    if "installation_id" not in subscription_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE subscriptions ADD COLUMN installation_id INTEGER"))

    if "billing_webhook_events" not in table_names:
        return

    webhook_columns = {column["name"] for column in inspector.get_columns("billing_webhook_events")}
    if "processed_at" not in webhook_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE billing_webhook_events ADD COLUMN processed_at TIMESTAMP"))
