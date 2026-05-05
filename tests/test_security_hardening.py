import os
import unittest
from unittest import mock

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from core.license_validator import verify_signed_payload

try:
    from pydantic import ValidationError
    from backend.app.config import Settings
    from fastapi import HTTPException
    from backend.app.services.update_service import validate_download_url, validate_sha256
except Exception:
    ValidationError = None
    Settings = None
    HTTPException = None
    validate_download_url = None
    validate_sha256 = None


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)

    def test_rs256_local_validation_works_without_openssl_lookup(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        token = jwt.encode({"license_id": "lic_test_rs256"}, private_pem, algorithm="RS256")

        with (
            mock.patch("core.license_validator.get_public_key_material", return_value=public_pem),
            mock.patch("core.license_validator.shutil_which", return_value=""),
        ):
            payload = verify_signed_payload(token)

        self.assertEqual(payload["license_id"], "lic_test_rs256")

    def test_production_settings_reject_insecure_defaults(self):
        if ValidationError is None or Settings is None:
            self.skipTest("Dependencias del backend no disponibles en este entorno.")
        with self.assertRaises(ValidationError):
            Settings(
                APP_ENV="production",
                API_BASE_URL="http://127.0.0.1:8000",
                DATABASE_URL="sqlite:////tmp/test.sqlite3",
                JWT_SECRET="placeholder-secret",
                ADMIN_API_KEY="",
                LICENSE_SIGNING_ALGORITHM="RS256",
                LICENSE_PRIVATE_KEY="replace-me",
                LICENSE_PUBLIC_KEY="replace-me",
                PADDLE_API_KEY="placeholder",
                PADDLE_WEBHOOK_SECRET="placeholder",
                PADDLE_PRODUCT_ID="placeholder-product",
                PADDLE_PRICE_ID="placeholder-price",
                AUTO_CREATE_TABLES=True,
            )

    def test_update_release_rejects_insecure_download_url(self):
        if HTTPException is None or validate_download_url is None:
            self.skipTest("Dependencias del backend no disponibles en este entorno.")
        with self.assertRaises(HTTPException):
            validate_download_url("http://downloads.example.com/tlamatini.zip")

    def test_update_release_rejects_invalid_sha256(self):
        if HTTPException is None or validate_sha256 is None:
            self.skipTest("Dependencias del backend no disponibles en este entorno.")
        with self.assertRaises(HTTPException):
            validate_sha256("abc123")


if __name__ == "__main__":
    unittest.main()
