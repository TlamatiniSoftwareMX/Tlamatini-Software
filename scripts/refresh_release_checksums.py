#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
FULL_DIST_DIR = DIST_DIR / "tlamatini_full"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version() -> str:
    return os.environ.get("TLAMATINI_APP_VERSION", "5.2.6")


def _platform_files(platform: str) -> list[Path]:
    version = _version()
    files_by_platform = {
        "linux": [
            DIST_DIR / "TLAMATINI-full-linux-x86_64.tar.gz",
            DIST_DIR / f"tlamatini-{version}-amd64.deb",
            FULL_DIST_DIR / "TLAMATINI",
            FULL_DIST_DIR / "install.sh",
            FULL_DIST_DIR / "tlamatini.png",
            FULL_DIST_DIR / "release_manifest.json",
        ],
        "windows": [
            DIST_DIR / "TLAMATINI-Windows-Instalador-Full.exe",
            DIST_DIR / "TLAMATINI-full-windows-x86_64.zip",
            FULL_DIST_DIR / "TLAMATINI.exe",
            FULL_DIST_DIR / "install.ps1",
            FULL_DIST_DIR / "install.cmd",
            FULL_DIST_DIR / "tlamatini.ico",
            FULL_DIST_DIR / "release_manifest.json",
        ],
        "macos": [
            DIST_DIR / "TLAMATINI-full-macos.zip",
            DIST_DIR / "TLAMATINI-full-macos.dmg",
            FULL_DIST_DIR / "TLAMATINI.app",
            FULL_DIST_DIR / "install.command",
            FULL_DIST_DIR / "tlamatini.icns",
            FULL_DIST_DIR / "release_manifest.json",
        ],
    }
    return files_by_platform[platform]


def refresh_release_checksums(platform: str) -> int:
    records = []
    lines = []
    for path in _platform_files(platform):
        if not path.exists() or not path.is_file():
            continue
        checksum = _sha256_file(path)
        rel = path.relative_to(PROJECT_ROOT)
        records.append({"path": str(rel), "sha256": checksum, "size": path.stat().st_size})
        lines.append(f"{checksum}  {rel}")

    checksums_txt = "\n".join(lines) + ("\n" if lines else "")
    checksums_json = json.dumps({"artifacts": records}, indent=2, ensure_ascii=False)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "SHA256SUMS.txt").write_text(checksums_txt, encoding="utf-8")
    (DIST_DIR / "SHA256SUMS.json").write_text(checksums_json, encoding="utf-8")
    (DIST_DIR / f"SHA256SUMS-{platform}.txt").write_text(checksums_txt, encoding="utf-8")
    (DIST_DIR / f"SHA256SUMS-{platform}.json").write_text(checksums_json, encoding="utf-8")

    metadata = {
        "app": "TLAMATINI",
        "edition": "full",
        "platform": platform,
        "version": _version(),
        "artifacts": records,
    }
    metadata_text = json.dumps(metadata, indent=2, ensure_ascii=False)
    (DIST_DIR / "release_metadata.json").write_text(metadata_text, encoding="utf-8")
    (DIST_DIR / f"release_metadata-{platform}.json").write_text(metadata_text, encoding="utf-8")
    if FULL_DIST_DIR.exists():
        (FULL_DIST_DIR / "release_metadata.json").write_text(metadata_text, encoding="utf-8")

    print(f"Checksums actualizados para {platform}:")
    for record in records:
        print(f"- {record['path']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Actualiza checksums y metadata de release por plataforma.")
    parser.add_argument("platform", choices=["linux", "windows", "macos"])
    args = parser.parse_args()
    return refresh_release_checksums(args.platform)


if __name__ == "__main__":
    raise SystemExit(main())
