#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUNDLE_DIR = DIST_DIR / "tlamatini_full"


def _safe_stat(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    return {
        "exists": True,
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size": path.stat().st_size if path.is_file() else None,
    }


def build_report() -> dict:
    report = {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": sys.version,
        },
        "project_root": str(PROJECT_ROOT),
        "dist": {
            "exists": DIST_DIR.exists(),
            "bundle": _safe_stat(BUNDLE_DIR),
            "bundle_entry": _safe_stat(BUNDLE_DIR / "TLAMATINI"),
            "checksums_txt": _safe_stat(DIST_DIR / "SHA256SUMS.txt"),
            "checksums_json": _safe_stat(DIST_DIR / "SHA256SUMS.json"),
            "checksums_sig": _safe_stat(DIST_DIR / "SHA256SUMS.sig.json"),
            "release_metadata": _safe_stat(DIST_DIR / "release_metadata.json"),
        },
        "environment": {
            "TLAMATINI_HOME": os.environ.get("TLAMATINI_HOME", ""),
            "TLAMATINI_DATA_DIR": os.environ.get("TLAMATINI_DATA_DIR", ""),
            "TLAMATINI_BACKEND_URL": os.environ.get("TLAMATINI_BACKEND_URL", ""),
            "TLAMATINI_AI_BACKEND": os.environ.get("TLAMATINI_AI_BACKEND", ""),
        },
    }
    metadata_path = DIST_DIR / "release_metadata.json"
    if metadata_path.exists():
        try:
            report["release_metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            report["release_metadata_error"] = str(exc)
    return report


def main() -> int:
    output = PROJECT_ROOT / "release_diagnostics.json"
    output.write_text(json.dumps(build_report(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Diagnóstico generado en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
