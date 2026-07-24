from __future__ import annotations

import webbrowser
from typing import Any, Dict
from urllib.parse import urlparse

import requests

from core.installation_identity import get_installation_payload
from core.license_code_validator import normalize_license_code, validate_license_code
from core.local_license_store import (
    activate_local_trial,
    clear_auth_session,
    describe_backend_configuration,
    get_backend_url,
    load_auth_session,
    load_local_license,
    save_local_license,
    save_offline_license_code,
    save_auth_session,
    save_backend_url,
    update_local_license_from_backend,
)
from core.logs import registrar_log
from core.user_profile import load_user_profile


class LicenseClientError(RuntimeError):
    pass


class BackendNotConfiguredError(LicenseClientError):
    pass


class BackendUnavailableError(LicenseClientError):
    pass


class LicenseClient:
    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout

    def backend_url(self) -> str:
        url = get_backend_url()
        if not url:
            cfg = describe_backend_configuration()
            if cfg.get("blocked_reason"):
                raise BackendNotConfiguredError(str(cfg["blocked_reason"]))
            raise BackendNotConfiguredError("No hay backend SaaS configurado.")
        return url

    def save_backend_url(self, url: str) -> str:
        return save_backend_url(url)

    def session_data(self) -> Dict[str, Any]:
        return load_auth_session()

    def access_token(self) -> str:
        return str(self.session_data().get("access_token", "")).strip()

    def is_authenticated(self) -> bool:
        return bool(self.access_token())

    def backend_profile(self) -> Dict[str, Any]:
        return describe_backend_configuration()

    def logout(self) -> None:
        clear_auth_session()
        registrar_log("dashboard", "Sesión SaaS cerrada localmente.", "licencias")

    def _headers(self, *, auth: bool = False) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if auth:
            token = self.access_token()
            if not token:
                raise LicenseClientError("No hay sesión iniciada.")
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(self, method: str, path: str, *, auth: bool = False, json_payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.backend_url()}{path}"
        try:
            response = requests.request(
                method,
                url,
                headers=self._headers(auth=auth),
                json=json_payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            host = (urlparse(url).hostname or "").strip().lower()
            if host in {"127.0.0.1", "localhost", "::1"}:
                raise BackendUnavailableError("El backend local de licencias no está disponible.") from exc
            raise BackendUnavailableError("No se pudo contactar el backend remoto. TLAMATINI seguirá en modo offline local.") from exc

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail") or response.text
            except Exception:
                detail = response.text
            raise LicenseClientError(str(detail).strip() or f"Error HTTP {response.status_code}")

        try:
            return response.json()
        except Exception as exc:
            raise LicenseClientError("El backend devolvió una respuesta inválida.") from exc

    def register_user(self, *, email: str, password: str, preferred_language: str = "es") -> Dict[str, Any]:
        payload = self._request(
            "POST",
            "/auth/register",
            json_payload={
                "email": email.strip(),
                "password": password,
                "preferred_language": preferred_language.strip() or "es",
            },
        )
        registrar_log("dashboard", f"Usuario SaaS registrado: {email.strip().lower()}", "licencias")
        return payload

    def login(self, *, email: str, password: str) -> Dict[str, Any]:
        payload = self._request(
            "POST",
            "/auth/login",
            json_payload={"email": email.strip(), "password": password},
        )
        save_auth_session(access_token=payload.get("access_token", ""), user=payload.get("user", {}))
        registrar_log("dashboard", f"Inicio de sesión SaaS: {email.strip().lower()}", "licencias")
        return payload

    def register_and_login(self, *, email: str, password: str, preferred_language: str = "es") -> Dict[str, Any]:
        self.register_user(email=email, password=password, preferred_language=preferred_language)
        return self.login(email=email, password=password)

    def current_user(self) -> Dict[str, Any]:
        return self._request("GET", "/auth/me", auth=True)

    def ensure_installation_registered(self) -> Dict[str, Any]:
        payload = get_installation_payload()
        result = self._request("POST", "/installations/register", auth=True, json_payload=payload)
        registrar_log("dashboard", f"Instalación registrada/sincronizada: {payload['installation_id']}", "licencias")
        return result

    def start_trial(self) -> Dict[str, Any]:
        profile = load_user_profile()
        try:
            activate_local_trial(profile=profile, duration_days=7)
        except ValueError as exc:
            raise LicenseClientError(str(exc)) from exc
        registrar_log("dashboard", f"Prueba local activada: {profile.get('email', 'sin-email')}", "licencias")
        return self.local_status()

    def license_status(self) -> Dict[str, Any]:
        installation = get_installation_payload()
        payload = self._request(
            "GET",
            f"/licenses/status?installation_id={installation['installation_id']}",
            auth=True,
        )
        if payload.get("signed_payload"):
            update_local_license_from_backend(payload)
        return payload

    def sync_license(self) -> Dict[str, Any]:
        self.ensure_installation_registered()
        payload = self.license_status()
        registrar_log("dashboard", "Licencia sincronizada con backend SaaS.", "licencias")
        return payload

    def create_checkout(self, *, country_code: str = "MX", postal_code: str = "") -> Dict[str, Any]:
        installation = self.ensure_installation_registered()
        payload = self._request(
            "POST",
            "/billing/create-checkout",
            auth=True,
            json_payload={
                "installation_id": installation["installation_id"],
                "country_code": (country_code or "MX").strip().upper(),
                "postal_code": postal_code.strip() or None,
            },
        )
        registrar_log("dashboard", f"Checkout Paddle creado: {installation['installation_id']}", "licencias")
        return payload

    def open_checkout(self, *, country_code: str = "MX", postal_code: str = "") -> Dict[str, Any]:
        payload = self.create_checkout(country_code=country_code, postal_code=postal_code)
        checkout_url = str(payload.get("checkout_url", "")).strip()
        if checkout_url:
            webbrowser.open(checkout_url)
        return payload

    def activate_manual_license(self, license_code: str) -> Dict[str, Any]:
        normalized = normalize_license_code(license_code)
        try:
            status = validate_license_code(normalized, installation_id=get_installation_payload()["installation_id"])
        except Exception as exc:
            raise LicenseClientError(str(exc).strip() or "No se pudo activar la licencia manual.") from exc
        normalized = str(status.get("license_code", normalized)).strip()
        save_offline_license_code(normalized)

        payload = status.get("payload") or {}
        current = load_local_license()
        current.update(
            {
                "offline_license_code": normalized,
                "offline_license_status": str(status.get("state", "")).strip(),
                "offline_expires_at": str(status.get("expires_at", "")).strip(),
                "offline_license_id": str(payload.get("license_id", status.get("license_id", ""))).strip(),
            }
        )
        save_local_license(current)
        registrar_log("dashboard", f"Licencia manual activada: {current.get('offline_license_id') or 'sin-id'}", "licencias")
        return status

    def local_status(self) -> Dict[str, Any]:
        cfg = self.backend_profile()
        session = self.session_data()
        profile = load_user_profile()
        customer_email = (
            str(profile.get("email", "")).strip()
            or str(session.get("user", {}).get("email", "")).strip()
        )
        customer_name = (
            str(profile.get("full_name", "")).strip()
            or str(session.get("user", {}).get("name", "")).strip()
        )
        return {
            "is_valid": True,
            "state": "valid",
            "source": "free_use",
            "status": "active",
            "message": "Disponible",
            "plan": "libre",
            "expires_at": "",
            "grace_until": "",
            "days_remaining": None,
            "trial_expired": False,
            "offline_ready": True,
            "backend_mode": "disabled",
            "backend_url": cfg.get("effective_url", ""),
            "backend_saved_url": cfg.get("raw_url", ""),
            "backend_configured": False,
            "backend_blocked_reason": "",
            "customer_email": customer_email,
            "customer_name": customer_name,
            "session_email": str(session.get("user", {}).get("email", "")).strip(),
        }
