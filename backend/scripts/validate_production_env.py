#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    env_file = backend_root / ".env.production"
    using_template = False
    if not env_file.exists():
        env_file = backend_root / ".env.production.example"
        using_template = True
    try:
        from app.config import Settings

        settings = Settings(_env_file=str(env_file))
    except Exception as exc:
        print(f"ERROR: configuración de producción inválida: {exc}")
        return 1

    if using_template:
        print("AVISO: se validó la plantilla .env.production.example, no un entorno real.")
    print("Configuración de producción OK")
    print(f"- env: {settings.app_env}")
    print(f"- api_base_url: {settings.api_base_url}")
    print(f"- allowed_hosts: {', '.join(settings.allowed_hosts_list())}")
    print(f"- cors_allow_origins: {', '.join(settings.cors_allow_origins_list())}")
    print(f"- signing_algorithm: {settings.license_signing_algorithm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
