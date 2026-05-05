import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_release_bundle import verify_release_bundle


class ReleaseBundleTests(unittest.TestCase):
    def test_verify_linux_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "tlamatini_full"
            bundle.mkdir()
            (bundle / "TLAMATINI").write_bytes(b"x" * (101 * 1024 * 1024))
            (bundle / "install.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (bundle / "release_manifest.json").write_text(
                json.dumps(
                    {
                        "app": "TLAMATINI",
                        "edition": "full",
                        "platform": "linux",
                        "ai_backend": "local",
                        "primary_model": "gemma3:4b",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(verify_release_bundle(bundle), 0)

    def test_verify_windows_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "tlamatini_full"
            bundle.mkdir()
            (bundle / "TLAMATINI.exe").write_bytes(b"x" * (101 * 1024 * 1024))
            (bundle / "install.ps1").write_text("Write-Host 'install'\n", encoding="utf-8")
            (bundle / "install.cmd").write_text("@echo off\n", encoding="utf-8")
            (bundle / "release_manifest.json").write_text(
                json.dumps(
                    {
                        "app": "TLAMATINI",
                        "edition": "full",
                        "platform": "windows",
                        "ai_backend": "local",
                        "primary_model": "gemma3:4b",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(verify_release_bundle(bundle), 0)

    def test_windows_bundle_missing_installer_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "tlamatini_full"
            bundle.mkdir()
            (bundle / "TLAMATINI.exe").write_bytes(b"x" * (101 * 1024 * 1024))
            (bundle / "install.ps1").write_text("Write-Host 'install'\n", encoding="utf-8")
            (bundle / "release_manifest.json").write_text(
                json.dumps(
                    {
                        "app": "TLAMATINI",
                        "edition": "full",
                        "platform": "windows",
                        "ai_backend": "local",
                        "primary_model": "gemma3:4b",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(verify_release_bundle(bundle), 1)

    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle = Path(temp_dir) / "tlamatini_full"
            bundle.mkdir()
            (bundle / "TLAMATINI").write_bytes(b"x" * (101 * 1024 * 1024))
            self.assertEqual(verify_release_bundle(bundle), 1)


if __name__ == "__main__":
    unittest.main()
