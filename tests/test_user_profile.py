import os
import tempfile
import unittest
from pathlib import Path

from core.user_profile import is_profile_complete, load_user_profile, save_user_profile, validate_user_profile


class UserProfileTests(unittest.TestCase):
    def setUp(self):
        self._original_env = dict(os.environ)
        self._temp_dir = tempfile.TemporaryDirectory()
        self.profile_file = Path(self._temp_dir.name) / "user_profile.json"
        os.environ["TLAMATINI_USER_PROFILE_FILE"] = str(self.profile_file)

    def tearDown(self):
        self._temp_dir.cleanup()
        os.environ.clear()
        os.environ.update(self._original_env)

    def test_profile_is_empty_by_default(self):
        profile = load_user_profile()
        self.assertEqual(profile["full_name"], "")
        self.assertEqual(profile["email"], "")
        self.assertFalse(is_profile_complete(profile))

    def test_save_user_profile_persists_required_fields(self):
        saved = save_user_profile(
            full_name="Cliente Demo",
            email="cliente@example.com",
            phone="+52 555 123 4567",
            country="México",
        )
        loaded = load_user_profile()
        self.assertEqual(saved["full_name"], "Cliente Demo")
        self.assertEqual(loaded["email"], "cliente@example.com")
        self.assertEqual(loaded["phone"], "+52 555 123 4567")
        self.assertTrue(is_profile_complete(loaded))

    def test_invalid_email_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            validate_user_profile(full_name="Cliente Demo", email="correo-invalido")
        self.assertIn("correo electrónico válido", str(ctx.exception))

    def test_edit_profile_preserves_created_at_and_updates_timestamp(self):
        first = save_user_profile(full_name="Cliente Demo", email="cliente@example.com")
        second = save_user_profile(
            full_name="Cliente Editado",
            email="cliente@example.com",
            phone="+52 555 123 4567",
            country="México",
        )
        self.assertEqual(first["created_at"], second["created_at"])
        self.assertNotEqual(first["updated_at"], second["updated_at"])
        self.assertEqual(second["full_name"], "Cliente Editado")
        self.assertEqual(second["phone"], "+52 555 123 4567")


if __name__ == "__main__":
    unittest.main()
