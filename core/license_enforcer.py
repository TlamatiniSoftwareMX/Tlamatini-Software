from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict

from core.license_client import LicenseClient


BLOCKED_ON_EXPIRED = {
    "consulta",
    "ia",
    "gemma",
    "mapa",
    "biblioteca",
    "aprendizaje",
    "herramientas",
    "juegos",
}


class LicenseEnforcer:
    def __init__(self):
        self.client = LicenseClient()

    def current_status(self) -> Dict:
        return deepcopy(self.client.local_status())

    def current_state(self) -> str:
        return str(self.current_status().get("state", "missing")).strip().lower() or "missing"

    def is_license_valid(self) -> bool:
        return self.current_state() in {"valid", "grace"}

    def should_show_block_screen(self) -> bool:
        return self.current_state() == "invalid"

    def can_access_module(self, name: str) -> bool:
        module_name = str(name or "").strip().lower()
        state = self.current_state()
        if module_name in {"license", "licencia"}:
            return True
        if state in {"valid", "grace"}:
            return True
        if state == "expired":
            return module_name not in BLOCKED_ON_EXPIRED
        if state in {"invalid", "missing"}:
            return False
        return False

    def grace_message(self) -> str:
        status = self.current_status()
        days_remaining = None
        grace_until = str(status.get("grace_until", "")).strip()
        if grace_until:
            try:
                grace_dt = datetime.fromisoformat(grace_until.replace("Z", "+00:00"))
                delta = grace_dt - datetime.now(timezone.utc)
                if delta.total_seconds() > 0:
                    days_remaining = max(0, delta.days)
            except Exception:
                days_remaining = None
        remaining = f"{days_remaining} día(s)" if days_remaining is not None else "pocos días"
        return f"Tu licencia está vencida, tienes {remaining} restantes en modo gracia."

    def block_reason_for(self, name: str) -> str:
        state = self.current_state()
        status = self.current_status()
        module_name = str(name or "").strip()
        if state == "expired":
            return (
                f"{module_name or 'Este módulo'} está bloqueado porque la licencia local está vencida. "
                "Puedes sincronizar, renovar la suscripción o pegar una nueva licencia manual para recuperar acceso."
            )
        if state == "grace":
            return self.grace_message()
        if state == "invalid":
            return "La licencia local es inválida. Revisa el código recibido o vuelve a activar TLAMATINI con una licencia válida."
        if state == "missing":
            if status.get("trial_expired"):
                return "La prueba gratuita ya fue utilizada en esta instalación. Solicita tu licencia mensual o pega el código recibido."
            return "Comienza activando una prueba gratuita o solicitando tu licencia mensual."
        return str(status.get("message", "")).strip() or "Acceso restringido por licencia."
