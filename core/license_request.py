from __future__ import annotations

from typing import Any, Mapping

from core.user_profile import is_profile_complete


def requested_plan_label(raw_plan: str | None) -> str:
    plan = str(raw_plan or "").strip().lower()
    if plan in {"mensual", "trimestral", "anual"}:
        return plan
    return "mensual"


def build_manual_license_request(
    *,
    profile: Mapping[str, Any],
    identity: Mapping[str, Any],
    current_state: str,
    requested_plan: str | None = None,
) -> str:
    if not is_profile_complete(dict(profile or {})):
        raise ValueError("Primero guarda tu nombre y un correo electrónico válido.")

    name = str(profile.get("full_name", "") or "").strip() or "Pendiente"
    email = str(profile.get("email", "") or "").strip() or "Pendiente"
    phone = str(profile.get("phone", "") or "").strip() or "no proporcionado"
    country = str(profile.get("country", "") or "").strip() or "no proporcionado"

    return "\n".join(
        [
            "TLAMATINI - Solicitud de licencia",
            "",
            f"Nombre: {name}",
            f"Email: {email}",
            f"Teléfono: {phone}",
            f"País: {country}",
            f"ID de instalación: {str(identity.get('installation_id', '') or '').strip()}",
            f"Sistema operativo: {str(identity.get('os_name', '') or '').strip()}",
            f"Versión de TLAMATINI: {str(identity.get('app_version', '') or '').strip()}",
            f"Estado actual: {str(current_state or '').strip() or 'Sin licencia'}",
            f"Plan solicitado: {requested_plan_label(requested_plan)}",
        ]
    )
