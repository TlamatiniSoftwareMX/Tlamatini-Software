#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.installation_identity import get_app_version


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        return 127, f"No se encontró el ejecutable requerido: {exc.filename}"
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def _has_full_release_artifacts() -> bool:
    bundle = PROJECT_ROOT / "dist" / "tlamatini_full"
    return (bundle / "release_manifest.json").exists() or (PROJECT_ROOT / "dist" / "TLAMATINI-full-linux-x86_64.tar.gz").exists()


def _desktop_release_ok() -> tuple[bool, list[str]]:
    version = get_app_version()
    dist = PROJECT_ROOT / "dist"
    issues = []
    if not (dist / f"tlamatini-{version}-amd64.deb").exists():
        issues.append(f"Falta dist/tlamatini-{version}-amd64.deb")
    if not (dist / "SHA256SUMS-linux.txt").exists():
        issues.append("Falta dist/SHA256SUMS-linux.txt")
    if not (dist / "release_metadata-linux.json").exists():
        issues.append("Falta dist/release_metadata-linux.json")
    return not issues, issues


def main() -> int:
    checks = []
    if _has_full_release_artifacts():
        checks.append(("doctor_full_release", [sys.executable, "scripts/local_ai_tool.py", "doctor_full_release"], PROJECT_ROOT))
    else:
        print("[doctor_full_release]")
        print("Omitido: no hay release Full generado en dist/.")

    backend_python = PROJECT_ROOT / "backend" / ".venv" / "bin" / "python"
    if backend_python.exists():
        checks.append(("doctor_backend", [str(backend_python), "scripts/doctor_backend.py"], PROJECT_ROOT / "backend"))
    else:
        print("[doctor_backend]")
        print("Omitido: no existe backend/.venv/bin/python.")

    failures = []
    for name, cmd, cwd in checks:
        code, output = _run(cmd, cwd)
        print(f"[{name}]")
        if output:
            print(output)
        if code != 0:
            failures.append(name)
    if failures:
        print("Doctor TLAMATINI: fallos detectados")
        for item in failures:
            print(f"- {item}")
        return 1

    desktop_ok, desktop_issues = _desktop_release_ok()
    if not desktop_ok:
        print("Doctor TLAMATINI: problemas en paquete Desktop")
        for issue in desktop_issues:
            print(f"- {issue}")
        return 1
    print("Doctor TLAMATINI: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
