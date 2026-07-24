from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict


class LicenseEnforcer:
    def __init__(self):
        pass

    def current_status(self) -> Dict:
        return deepcopy(
            {
                "is_valid": True,
                "state": "valid",
                "source": "free_use",
                "plan": "libre",
                "message": "Uso libre",
                "offline_ready": True,
                "backend_mode": "disabled",
                "backend_configured": False,
            }
        )

    def current_state(self) -> str:
        return str(self.current_status().get("state", "missing")).strip().lower() or "missing"

    def is_license_valid(self) -> bool:
        return self.current_state() in {"valid", "grace"}

    def should_show_block_screen(self) -> bool:
        return False

    def can_access_module(self, name: str) -> bool:
        return True

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
        return "TLAMATINI está configurado para uso libre."
