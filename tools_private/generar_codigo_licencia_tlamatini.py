#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from license_generator_core import generate_license_code, infer_duration_days_from_plan


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{label}{suffix}: ").strip()
    return raw or default


def main() -> int:
    customer_name = _prompt("Nombre del cliente")
    customer_email = _prompt("Email del cliente")
    if not customer_email:
        print("El email es obligatorio.")
        return 1

    plan = _prompt("Plan", "mensual")
    duration_days = int(_prompt("Duracion en dias", str(infer_duration_days_from_plan(plan))))
    installation_id = _prompt("ID de instalacion (recomendado)")
    features = _prompt("Features separadas por coma", "offline_activation")

    generated = generate_license_code(
        email=customer_email,
        plan=plan,
        duration_days=duration_days,
        installation_id=installation_id or None,
        customer_name=customer_name or None,
        features=features,
    )
    payload = generated["payload"]

    print("\nCliente:", customer_name or customer_email)
    print("Plan:", plan)
    print("Vence:", payload["expires_at"])
    print("ID de instalacion:", installation_id or "(sin vincular)")
    print("\nCodigo de licencia:\n")
    print(generated["license_code"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
