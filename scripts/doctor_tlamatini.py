#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def main() -> int:
    checks = [
        ("doctor_full_release", [sys.executable, "scripts/local_ai_tool.py", "doctor_full_release"], PROJECT_ROOT),
        ("doctor_backend", [str(PROJECT_ROOT / "backend" / ".venv" / "bin" / "python"), "scripts/doctor_backend.py"], PROJECT_ROOT / "backend"),
    ]
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
    if not (PROJECT_ROOT / "dist" / "SHA256SUMS.txt").exists():
        print("Doctor TLAMATINI: falta dist/SHA256SUMS.txt")
        return 1
    if not (PROJECT_ROOT / "dist" / "release_metadata.json").exists():
        print("Doctor TLAMATINI: falta dist/release_metadata.json")
        return 1
    print("Doctor TLAMATINI: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
