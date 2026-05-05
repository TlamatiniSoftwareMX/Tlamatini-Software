import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools_private import license_generator_core as lgc
from core.license_code_validator import validate_license_code


class LicenseGeneratorCoreTests(unittest.TestCase):
    def test_parse_license_request_text(self):
        parsed = lgc.parse_license_request_text(
            "\n".join(
                [
                    "TLAMATINI - Solicitud de licencia",
                    "",
                    "Nombre: Cliente Demo",
                    "Email: cliente@example.com",
                    "Teléfono: +52 555 123 4567",
                    "País: México",
                    "ID de instalación: 12345678-1234-1234-1234-1234567890ab",
                    "Sistema operativo: Linux",
                    "Versión de TLAMATINI: 0.1.0",
                    "Estado actual: Sin licencia",
                    "Plan solicitado: mensual",
                ]
            )
        )
        self.assertEqual(parsed["full_name"], "Cliente Demo")
        self.assertEqual(parsed["email"], "cliente@example.com")
        self.assertEqual(parsed["phone"], "+52 555 123 4567")
        self.assertEqual(parsed["country"], "México")
        self.assertEqual(parsed["installation_id"], "12345678-1234-1234-1234-1234567890ab")
        self.assertEqual(parsed["os_name"], "Linux")
        self.assertEqual(parsed["app_version"], "0.1.0")
        self.assertEqual(parsed["requested_plan"], "mensual")

    def test_generate_keys_and_license_code(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            private_path = tmp / "private_license_key.pem"
            public_path = tmp / "public_license_key.pem"
            app_public_path = tmp / "app_public_key.pem"

            with mock.patch.object(lgc, "PRIVATE_KEY_PATH", private_path), \
                 mock.patch.object(lgc, "PUBLIC_KEY_PATH", public_path), \
                 mock.patch.object(lgc, "APP_PUBLIC_KEY_PATH", app_public_path):
                result = lgc.generate_license_keys(overwrite=False)
                self.assertTrue(result["created"])
                self.assertTrue(private_path.exists())
                self.assertTrue(public_path.exists())
                self.assertTrue(app_public_path.exists())

                with mock.patch.dict("os.environ", {"TLAMATINI_LICENSE_PUBLIC_KEY": str(app_public_path)}):
                    generated = lgc.generate_license_code(
                        email="cliente@example.com",
                        plan="mensual",
                        duration_days=30,
                        installation_id="12345678-1234-1234-1234-1234567890ab",
                        customer_name="Cliente Demo",
                        customer_phone="+52 555 123 4567",
                        customer_country="México",
                    )
                    status = validate_license_code(
                        generated["license_code"],
                        installation_id="12345678-1234-1234-1234-1234567890ab",
                    )
                    self.assertTrue(status["is_valid"])
                    self.assertEqual(status["plan"], "mensual")
                    self.assertEqual(status["customer_name"], "Cliente Demo")
                    self.assertEqual(generated["payload"]["customer_phone"], "+52 555 123 4567")
                    self.assertEqual(generated["payload"]["customer_country"], "México")

    def test_infer_duration_days_from_plan(self):
        self.assertEqual(lgc.infer_duration_days_from_plan("mensual"), 30)
        self.assertEqual(lgc.infer_duration_days_from_plan("trimestral"), 90)
        self.assertEqual(lgc.infer_duration_days_from_plan("anual"), 365)
        self.assertEqual(lgc.infer_duration_days_from_plan("otro"), 30)


if __name__ == "__main__":
    unittest.main()
