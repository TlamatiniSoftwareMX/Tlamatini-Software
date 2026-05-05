#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from license_generator_core import generate_license_keys


def main() -> int:
    paths = generate_license_keys(overwrite=False)

    print("Claves Ed25519 generadas.")
    print(f"Privada: {paths['private_key_path']}")
    print(f"Publica privada/local: {paths['public_key_path']}")
    print(f"Publica para TLAMATINI: {paths['app_public_key_path']}")
    print("No distribuyas private_license_key.pem ni la carpeta tools_private/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
