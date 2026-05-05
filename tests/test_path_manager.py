import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import path_manager


class PathManagerTests(unittest.TestCase):
    def test_migrate_legacy_ai_skips_bundled_local_ai_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            bundled_root = project_root / "local_ai"
            target_root = tmp / "user-root"

            for name in ("config", "runtime", "models"):
                (bundled_root / name).mkdir(parents=True, exist_ok=True)
            (bundled_root / "models" / "gemma3.bin").write_text("ok", encoding="utf-8")

            paths = path_manager._build_paths(target_root)
            path_manager._ensure_core_dirs(paths)

            with mock.patch.object(path_manager, "PROJECT_ROOT", project_root):
                path_manager._migrate_legacy_ai(paths)

            migrated_model = paths.local_ai_models_dir / "gemma3.bin"
            self.assertFalse(migrated_model.exists())


if __name__ == "__main__":
    unittest.main()
