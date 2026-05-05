import os
import unittest
from unittest import mock

from core import local_license_store


class BackendHybridTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)

    def test_hybrid_mode_blocks_local_backend_by_default(self):
        with mock.patch("core.local_license_store.load_runtime_state", return_value={"backend_url": "http://127.0.0.1:8000", "backend_mode": "hybrid"}):
            self.assertEqual(local_license_store.get_backend_url(), "")
            cfg = local_license_store.describe_backend_configuration()
        self.assertEqual(cfg["mode"], "hybrid")
        self.assertTrue(cfg["is_local_url"])
        self.assertFalse(cfg["configured"])
        self.assertIn("modo desarrollo", cfg["blocked_reason"])

    def test_dev_local_mode_allows_local_backend(self):
        with mock.patch("core.local_license_store.load_runtime_state", return_value={"backend_url": "http://127.0.0.1:8000", "backend_mode": "dev-local"}):
            self.assertEqual(local_license_store.get_backend_url(), "http://127.0.0.1:8000")
            cfg = local_license_store.describe_backend_configuration()
        self.assertTrue(cfg["configured"])
        self.assertTrue(cfg["local_backend_allowed"])

    def test_hybrid_mode_accepts_remote_backend(self):
        with mock.patch("core.local_license_store.load_runtime_state", return_value={"backend_url": "https://api.tlamatini.example", "backend_mode": "hybrid"}):
            self.assertEqual(local_license_store.get_backend_url(), "https://api.tlamatini.example")
            cfg = local_license_store.describe_backend_configuration()
        self.assertTrue(cfg["configured"])
        self.assertFalse(cfg["is_local_url"])

    def test_uses_default_backend_when_user_has_not_saved_one(self):
        os.environ["TLAMATINI_DEFAULT_BACKEND_URL"] = "https://saas.tlamatini.example"
        with mock.patch("core.local_license_store.load_runtime_state", return_value={"backend_mode": "hybrid"}):
            self.assertEqual(local_license_store.get_backend_url(), "https://saas.tlamatini.example")
            cfg = local_license_store.describe_backend_configuration()
        self.assertTrue(cfg["configured"])
        self.assertEqual(cfg["source"], "default")
        self.assertEqual(cfg["default_url"], "https://saas.tlamatini.example")

    def test_save_backend_url_rejects_insecure_remote_http(self):
        with self.assertRaises(ValueError):
            local_license_store.save_backend_url("http://api.tlamatini.example")

    def test_save_backend_url_rejects_non_root_paths(self):
        with self.assertRaises(ValueError):
            local_license_store.save_backend_url("https://api.tlamatini.example/v1")


if __name__ == "__main__":
    unittest.main()
