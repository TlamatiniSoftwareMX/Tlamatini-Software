import os
from pathlib import Path


TEST_DB_PATH = Path(__file__).resolve().parent / "test_backend.sqlite3"

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_VERSION", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-suite")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("LICENSE_SIGNING_ALGORITHM", "HS256")
os.environ.setdefault("LICENSE_SIGNING_SECRET", "test-license-signing-secret")
os.environ.setdefault("LICENSE_PRIVATE_KEY", "replace-me")
os.environ.setdefault("LICENSE_PUBLIC_KEY", "replace-me")
os.environ.setdefault("PADDLE_API_KEY", "pdl_sdbx_test_key")
os.environ.setdefault("PADDLE_WEBHOOK_SECRET", "test-paddle-webhook-secret")
os.environ.setdefault("PADDLE_ENVIRONMENT", "sandbox")
os.environ.setdefault("PADDLE_PRODUCT_ID", "pro_test")
os.environ.setdefault("PADDLE_PRICE_ID", "pri_test")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-api-key")
os.environ.setdefault("TRIAL_DAYS", "7")
os.environ.setdefault("OFFLINE_GRACE_DAYS", "30")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")
