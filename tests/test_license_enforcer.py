import unittest

from core.license_enforcer import LicenseEnforcer


class LicenseEnforcerTests(unittest.TestCase):
    def test_free_use_grants_access_without_license(self):
        enforcer = LicenseEnforcer()
        status = enforcer.current_status()

        self.assertTrue(status["is_valid"])
        self.assertEqual(status["state"], "valid")
        self.assertEqual(status["plan"], "libre")
        self.assertTrue(enforcer.is_license_valid())
        self.assertFalse(enforcer.should_show_block_screen())
        self.assertTrue(enforcer.can_access_module("consulta"))
        self.assertTrue(enforcer.can_access_module("mapa"))


if __name__ == "__main__":
    unittest.main()
