#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    required_files = [
        backend_root / "Dockerfile",
        backend_root / "docker-compose.production.yml",
        backend_root / "deploy" / "Caddyfile",
        backend_root / ".env.production.example",
    ]
    missing = [path for path in required_files if not path.exists()]
    if missing:
        print("Doctor backend: faltan archivos")
        for item in missing:
            print(f"- {item}")
        return 1

    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    try:
        from app.config import Settings

        settings = Settings(_env_file=str(backend_root / ".env.production.example"))
    except Exception as exc:
        print(f"Doctor backend: configuración inválida: {exc}")
        return 1

    print("Doctor backend: OK")
    print(f"- env: {settings.app_env}")
    print(f"- api_base_url: {settings.api_base_url}")
    print(f"- allowed_hosts: {', '.join(settings.allowed_hosts_list())}")
    print(f"- signing_algorithm: {settings.license_signing_algorithm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
