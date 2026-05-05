#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 1


def _host_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _expected_bundle_entry(platform: str) -> str:
    if platform == "windows":
        return "TLAMATINI.exe"
    if platform == "macos":
        return "TLAMATINI.app"
    return "TLAMATINI"


def verify_release_bundle(bundle_dir: Path) -> int:
    if not bundle_dir.exists():
        return _fail(f"No existe el bundle: {bundle_dir}")

    manifest_path = bundle_dir / "release_manifest.json"
    if not manifest_path.exists():
        return _fail("Falta release_manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fail(f"No se pudo leer release_manifest.json: {exc}")

    entry_name = _expected_bundle_entry(str(manifest.get("platform") or _host_platform()).lower())
    entry_path = bundle_dir / entry_name
    if not entry_path.exists():
        return _fail(f"Falta el ejecutable o bundle esperado: {entry_name}")

    expected_platform = str(manifest.get("platform") or "").lower()
    if expected_platform and expected_platform not in {"linux", "windows", "macos"}:
        return _fail(f"Plataforma inválida en manifest: {expected_platform}")

    if str(manifest.get("edition") or "").lower() != "full":
        return _fail("El manifest no declara edition=full")
    if str(manifest.get("ai_backend") or "").lower() != "local":
        return _fail("El manifest no declara ai_backend=local")
    if str(manifest.get("primary_model") or "").lower() != "gemma3:4b":
        return _fail("El manifest no declara primary_model=gemma3:4b")

    installer_names = {
        "linux": ["install.sh"],
        "windows": ["install.ps1", "install.cmd"],
        "macos": ["install.command"],
    }
    required_installers = installer_names.get(expected_platform or _host_platform(), [])
    for installer in required_installers:
        if not (bundle_dir / installer).exists():
            return _fail(f"Falta instalador esperado: {installer}")

    size = entry_path.stat().st_size
    if size < 100 * 1024 * 1024:
        return _fail("El bundle parece demasiado pequeño para una edición Full con IA embebida")

    print("Bundle OK")
    print(f"- ruta: {bundle_dir}")
    print(f"- plataforma: {expected_platform or _host_platform()}")
    print(f"- ejecutable: {entry_name}")
    print(f"- tamaño: {size}")
    return 0


def main() -> int:
    raw = sys.argv[1] if len(sys.argv) > 1 else os.path.join("dist", "tlamatini_full")
    return verify_release_bundle(Path(raw).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
