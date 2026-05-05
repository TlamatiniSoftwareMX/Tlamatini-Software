import unittest

from core.license_request import build_manual_license_request


class LicenseRequestTests(unittest.TestCase):
    def test_build_manual_license_request_includes_profile_and_installation(self):
        request_text = build_manual_license_request(
            profile={
                "full_name": "Cliente Demo",
                "email": "cliente@example.com",
                "phone": "+52 555 123 4567",
                "country": "México",
            },
            identity={
                "installation_id": "12345678-1234-1234-1234-1234567890ab",
                "os_name": "Linux",
                "app_version": "5.2",
            },
            current_state="Sin licencia",
            requested_plan="mensual",
        )
        self.assertIn("Nombre: Cliente Demo", request_text)
        self.assertIn("Email: cliente@example.com", request_text)
        self.assertIn("ID de instalación: 12345678-1234-1234-1234-1234567890ab", request_text)
        self.assertIn("Plan solicitado: mensual", request_text)

    def test_build_manual_license_request_requires_complete_profile(self):
        with self.assertRaises(ValueError) as ctx:
            build_manual_license_request(
                profile={"full_name": "Cliente Demo", "email": ""},
                identity={"installation_id": "abc", "os_name": "Linux", "app_version": "5.2"},
                current_state="Sin licencia",
                requested_plan="mensual",
            )
        self.assertIn("correo electrónico válido", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
