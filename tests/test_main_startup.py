import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
import os
from core.installation_identity import get_app_version


class MainStartupTests(unittest.TestCase):
    def test_bundled_local_ai_available_reads_from_project_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            runtime = project_root / "local_ai" / "runtime" / "bin" / "llama-server"
            config = project_root / "local_ai" / "config" / "models.json"
            model = project_root / "local_ai" / "models" / "gemma3" / "model.gguf"

            runtime.parent.mkdir(parents=True, exist_ok=True)
            config.parent.mkdir(parents=True, exist_ok=True)
            model.parent.mkdir(parents=True, exist_ok=True)

            runtime.write_text("bin", encoding="utf-8")
            config.write_text("{}", encoding="utf-8")
            model.write_text("ok", encoding="utf-8")

            with mock.patch.object(main, "PROJECT_ROOT", project_root):
                self.assertTrue(main._bundled_local_ai_available())

    def test_cleanup_ai_keeps_runtime_alive_by_default(self):
        original_env = dict(os.environ)
        try:
            os.environ.pop("TLAMATINI_AI_STOP_ON_EXIT", None)
            service = mock.Mock()
            cleanup = main._registrar_cleanup_ai(service, ["gemma3"])
            cleanup()
            service.stop_model_process.assert_not_called()
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_get_app_version_ignores_legacy_51_value(self):
        with mock.patch("core.installation_identity.obtener_seccion", return_value={"version": "5.1"}):
            self.assertEqual(get_app_version(), "5.2.4")

    def test_get_app_version_ignores_older_saved_value(self):
        with mock.patch("core.installation_identity.obtener_seccion", return_value={"version": "5.2.2"}):
            self.assertEqual(get_app_version(), "5.2.4")

    def test_get_app_version_allows_newer_saved_value(self):
        with mock.patch("core.installation_identity.obtener_seccion", return_value={"version": "5.2.5"}):
            self.assertEqual(get_app_version(), "5.2.5")


if __name__ == "__main__":
    unittest.main()
