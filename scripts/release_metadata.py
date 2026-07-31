#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"


def _detect_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def build_release_metadata() -> dict:
    checksums_path = DIST_DIR / "SHA256SUMS.json"
    checksums = {}
    if checksums_path.exists():
        try:
            checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
        except Exception:
            checksums = {}

    metadata = {
        "app": "TLAMATINI",
        "edition": "full",
        "platform": _detect_platform(),
        "version": os.environ.get("TLAMATINI_APP_VERSION", "5.2.6"),
        "artifacts": checksums.get("artifacts", []),
    }
    return metadata


def main() -> int:
    output = DIST_DIR / "release_metadata.json"
    output.write_text(json.dumps(build_release_metadata(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Metadata generada en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
