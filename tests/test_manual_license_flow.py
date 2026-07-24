import base64
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.installation_identity import get_installation_id
from core.license_client import LicenseClient, LicenseClientError
from core.license_code_validator import normalize_license_code, validate_license_code
from core.local_license_store import load_local_license, load_offline_license_code, save_installation_identity, save_local_license
from core.user_profile import save_user_profile


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_license_code(
    private_key,
    *,
    installation_id: str,
    days: int = 30,
    email: str = "cliente@example.com",
    customer_name: str = "Cliente Demo",
) -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        "license_version": 1,
        "license_id": "lic-test-001",
        "customer_name": customer_name,
        "customer_email": email,
        "plan": "mensual",
        "issued_at": _iso(issued_at),
        "expires_at": _iso(issued_at + timedelta(days=days)),
        "features": ["offline_activation"],
        "installation_id": installation_id,
    }
    signing_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = private_key.sign(signing_bytes)
    package = {
        "algorithm": "Ed25519",
        "payload": payload,
        "signature": _b64url(signature),
    }
    return "TLAMATINI-LICENSE-v1." + _b64url(json.dumps(package, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


class ManualLicenseFlowTests(unittest.TestCase):
    def setUp(self):
        self._original_env = dict(os.environ)
        self._temp_dir = tempfile.TemporaryDirectory()
        tmp = Path(self._temp_dir.name)
        self.installation_file = tmp / "installation_identity.json"
        self.license_file = tmp / "license_state.json"
        self.code_file = tmp / "license_code.txt"
        os.environ["TLAMATINI_INSTALLATION_ID_FILE"] = str(self.installation_file)
        os.environ["TLAMATINI_LICENSE_FILE"] = str(self.license_file)
        os.environ["TLAMATINI_OFFLINE_LICENSE_CODE_FILE"] = str(self.code_file)

        self.private_key = Ed25519PrivateKey.generate()
        public_pem = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        os.environ["TLAMATINI_LICENSE_PUBLIC_KEY"] = public_pem.decode("utf-8")

    def tearDown(self):
        self._temp_dir.cleanup()
        os.environ.clear()
        os.environ.update(self._original_env)

    def test_installation_id_is_persistent(self):
        first = get_installation_id()
        second = get_installation_id()
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-fA-F-]{36}$")

    def test_manual_activation_valid_code(self):
        installation_id = get_installation_id()
        client = LicenseClient()
        code = _build_license_code(self.private_key, installation_id=installation_id)
        status = client.activate_manual_license(code)

        self.assertTrue(status["is_valid"])
        self.assertEqual(status["state"], "valid")
        self.assertEqual(status["plan"], "mensual")
        self.assertEqual(load_offline_license_code(), code)
        local_status = client.local_status()
        self.assertEqual(local_status["source"], "free_use")
        self.assertEqual(local_status["plan"], "libre")

    def test_manual_activation_accepts_wrapped_code(self):
        installation_id = get_installation_id()
        client = LicenseClient()
        code = _build_license_code(self.private_key, installation_id=installation_id)
        wrapped = "Solicitud aprobada:\n" + "\n ".join(code[index : index + 72] for index in range(0, len(code), 72))

        status = client.activate_manual_license(wrapped)

        self.assertTrue(status["is_valid"])
        self.assertEqual(status["license_code"], code)
        self.assertEqual(load_offline_license_code(), code)

    def test_normalize_license_code_removes_copy_formatting(self):
        code = "TLAMATINI-LICENSE-v1.abc_DEF-123"
        self.assertEqual(normalize_license_code("  " + code[:24] + "\n\t" + code[24:] + "  "), code)

    def test_manual_activation_rejects_expired_code(self):
        installation_id = get_installation_id()
        client = LicenseClient()
        code = _build_license_code(self.private_key, installation_id=installation_id, days=-1)

        with self.assertRaises(LicenseClientError) as ctx:
            client.activate_manual_license(code)
        self.assertIn("La licencia está vencida.", str(ctx.exception))

    def test_manual_activation_rejects_modified_code(self):
        installation_id = get_installation_id()
        client = LicenseClient()
        code = _build_license_code(self.private_key, installation_id=installation_id)
        broken = code[:-1] + ("A" if code[-1] != "A" else "B")

        with self.assertRaises(LicenseClientError) as ctx:
            client.activate_manual_license(broken)
        self.assertTrue(
            "Firma inválida" in str(ctx.exception)
            or "No se pudo leer el código de licencia." in str(ctx.exception)
            or "El código de licencia no tiene un formato válido." in str(ctx.exception)
        )

    def test_manual_activation_rejects_other_installation(self):
        save_installation_identity(
            {
                "installation_id": "11111111-1111-1111-1111-111111111111",
                "created_at": _iso(datetime.now(timezone.utc)),
                "updated_at": _iso(datetime.now(timezone.utc)),
            }
        )
        client = LicenseClient()
        code = _build_license_code(self.private_key, installation_id="22222222-2222-2222-2222-222222222222")

        with self.assertRaises(LicenseClientError) as ctx:
            client.activate_manual_license(code)
        self.assertIn("Esta licencia corresponde a otra instalación.", str(ctx.exception))

    def test_validator_allows_unbound_code(self):
        installation_id = get_installation_id()
        issued_at = datetime.now(timezone.utc)
        payload = {
            "license_version": 1,
            "license_id": "lic-unbound",
            "customer_email": "cliente@example.com",
            "plan": "mensual",
            "issued_at": _iso(issued_at),
            "expires_at": _iso(issued_at + timedelta(days=30)),
            "features": ["offline_activation"],
        }
        signing_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        signature = self.private_key.sign(signing_bytes)
        package = {"algorithm": "Ed25519", "payload": payload, "signature": _b64url(signature)}
        code = "TLAMATINI-LICENSE-v1." + _b64url(json.dumps(package, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))

        status = validate_license_code(code, installation_id=installation_id)
        self.assertTrue(status["is_valid"])
        self.assertFalse(status["is_bound_to_installation"])

    def test_local_trial_activation_valid(self):
        save_user_profile(full_name="Cliente Demo", email="cliente@example.com")
        client = LicenseClient()
        status = client.start_trial()

        self.assertTrue(status["is_valid"])
        self.assertEqual(status["plan"], "libre")
        self.assertEqual(status["source"], "free_use")
        self.assertEqual(status["customer_email"], "cliente@example.com")
        self.assertTrue(load_local_license()["trial_expires_at"])

    def test_expired_trial_does_not_grant_access(self):
        save_local_license(
            {
                "trial_started_at": "2026-04-01T00:00:00Z",
                "trial_expires_at": "2026-04-08T00:00:00Z",
                "trial_used_at": "2026-04-01T00:00:00Z",
                "trial_status": "active",
                "trial_name": "Cliente Demo",
                "trial_email": "cliente@example.com",
            }
        )
        client = LicenseClient()
        status = client.local_status()

        self.assertTrue(status["is_valid"])
        self.assertEqual(status["state"], "valid")
        self.assertFalse(status["trial_expired"])


if __name__ == "__main__":
    unittest.main()
