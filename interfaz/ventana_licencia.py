import threading
import tkinter as tk
from tkinter import messagebox

from core.installation_identity import get_installation_payload
from core.license_client import BackendNotConfiguredError, BackendUnavailableError, LicenseClient, LicenseClientError
from core.license_request import build_manual_license_request
from core.local_license_store import (
    describe_backend_configuration,
    get_backend_mode,
    get_backend_url,
    get_default_backend_url,
    load_offline_license_code,
    get_saved_backend_url,
    get_public_key_material,
    save_backend_mode,
    save_backend_url,
    save_public_key_material,
)
from core.user_profile import is_profile_complete, load_user_profile, save_user_profile
from core.window_geometry import aplicar_geometria_relativa


PALETA = {
    "bg": "#071423",
    "panel": "#10243d",
    "panel_alt": "#132c49",
    "panel_soft": "#0d1d30",
    "border": "#294866",
    "text": "#eef6ff",
    "text_dim": "#9db8d0",
    "accent": "#38bdf8",
    "accent_dark": "#0ea5e9",
    "ok": "#22c55e",
    "ok_dark": "#15803d",
    "warn": "#f59e0b",
    "warn_dark": "#b45309",
    "danger": "#ef4444",
    "danger_dark": "#b91c1c",
    "soft": "#16314f",
    "muted": "#1d3552",
    "white": "#ffffff",
}

class VentanaLicencia(tk.Toplevel):
    def __init__(self, master, initial_view: str = "auto"):
        super().__init__(master)
        self.client = LicenseClient()
        self.title("TLAMATINI")
        self.configure(bg=PALETA["bg"])
        self.minsize(920, 760)
        aplicar_geometria_relativa(self, master, rel_w=0.72, rel_h=0.88, min_w=940, min_h=780)

        session_user = self.client.session_data().get("user", {})
        profile = load_user_profile()
        self.var_backend_url = tk.StringVar(value=get_saved_backend_url() or get_default_backend_url())
        self.var_backend_mode = tk.StringVar(value=get_backend_mode())
        self.var_backend_public_key = tk.StringVar(value=get_public_key_material())
        self.var_email = tk.StringVar(value=str(session_user.get("email", "")).strip())
        self.var_password = tk.StringVar()
        self.var_language = tk.StringVar(value="es")
        self.var_country = tk.StringVar(value="MX")
        self.var_postal = tk.StringVar()
        self.var_profile_name = tk.StringVar(value=str(profile.get("full_name", "")).strip())
        self.var_profile_email = tk.StringVar(value=str(profile.get("email", "")).strip() or str(session_user.get("email", "")).strip())
        self.var_profile_phone = tk.StringVar(value=str(profile.get("phone", "")).strip())
        self.var_profile_country = tk.StringVar(value=str(profile.get("country", "")).strip())
        self.var_auth_mode = tk.StringVar(value="register")
        self.var_banner = tk.StringVar(value="")
        self.var_manual_status = tk.StringVar(value="")
        self._initial_view = str(initial_view or "auto").strip().lower()

        self._advanced_visible = False
        self._banner_tone = "info"
        self._content_frame = None
        self._steps_frame = None
        self._banner_frame = None
        self._banner_label = None
        self._advanced_toggle_button = None
        self._current_context = {}
        self._manual_license_text = None
        self._manual_details_visible = False
        self._manual_entry_visible = False
        self._force_profile_view = self._initial_view == "profile"
        self._screen_override = {
            "manual": "paste_code",
            "paste_code": "paste_code",
            "request_license": "request_license",
            "profile": "profile_form",
        }.get(self._initial_view, "")

        self._build_shell()
        self._refresh_local_view()

    def _build_shell(self) -> None:
        wrapper = tk.Frame(self, bg=PALETA["bg"])
        wrapper.pack(fill="both", expand=True, padx=18, pady=18)

        header = tk.Frame(wrapper, bg=PALETA["bg"])
        header.pack(fill="x", pady=(0, 8))
        tk.Label(
            header,
            text="TLAMATINI",
            font=("Arial", 24, "bold"),
            bg=PALETA["bg"],
            fg=PALETA["text"],
        ).pack(anchor="w")
        self._banner_frame = tk.Frame(wrapper, bg=PALETA["soft"], highlightthickness=1, highlightbackground=PALETA["border"])
        self._banner_label = tk.Label(
            self._banner_frame,
            textvariable=self.var_banner,
            font=("Arial", 10, "bold"),
            bg=PALETA["soft"],
            fg=PALETA["text"],
            anchor="w",
            justify="left",
            wraplength=820,
            padx=14,
            pady=10,
        )
        self._banner_label.pack(fill="x")

        self._content_frame = tk.Frame(wrapper, bg=PALETA["bg"])
        self._content_frame.pack(fill="both", expand=True)

    def _clear_frame(self, frame: tk.Widget) -> None:
        for child in frame.winfo_children():
            child.destroy()

    def _set_banner(self, message: str, tone: str = "info") -> None:
        self.var_banner.set(str(message or "").strip())
        self._banner_tone = tone
        self._update_banner_style()

    def _update_banner_style(self) -> None:
        tone_map = {
            "info": (PALETA["soft"], PALETA["border"], PALETA["text"]),
            "success": ("#10351d", PALETA["ok_dark"], "#dcfce7"),
            "warning": ("#3a2908", PALETA["warn_dark"], "#fef3c7"),
            "danger": ("#3a1113", PALETA["danger_dark"], "#fee2e2"),
        }
        bg, border, fg = tone_map.get(self._banner_tone, tone_map["info"])
        self._banner_frame.configure(bg=bg, highlightbackground=border)
        self._banner_label.configure(bg=bg, fg=fg)

    def _build_context(self) -> dict:
        identity = get_installation_payload()
        local_status = self.client.local_status()
        session = self.client.session_data()
        user_profile = load_user_profile()
        backend_cfg = describe_backend_configuration()
        backend = backend_cfg.get("effective_url", "")
        has_backend = bool(backend_cfg.get("configured"))
        has_session = bool(str(session.get("access_token", "")).strip())
        has_key = bool(get_public_key_material().strip())
        local_state = str(local_status.get("state", "missing")).strip().lower() or "missing"
        plan = str(local_status.get("plan", "")).strip()
        status = str(local_status.get("status", "")).strip()
        has_valid_license = local_state in {"valid", "grace"}
        has_saved_license = bool(plan or status or local_status.get("expires_at") or local_status.get("grace_until"))
        missing_dev_key = backend_cfg.get("is_local_url") and backend_cfg.get("local_backend_allowed") and not has_key
        profile_ready = is_profile_complete(user_profile)

        if has_valid_license:
            current_step = 4
        elif not profile_ready:
            current_step = 1
        elif not has_backend:
            current_step = 2
        elif not has_session:
            current_step = 3
        else:
            current_step = 3

        return {
            "identity": identity,
            "local_status": local_status,
            "session": session,
            "user_profile": user_profile,
            "profile_ready": profile_ready,
            "backend": backend,
            "backend_cfg": backend_cfg,
            "has_backend": has_backend,
            "has_session": has_session,
            "has_key": has_key,
            "local_state": local_state,
            "plan": plan,
            "status": status,
            "has_valid_license": has_valid_license,
            "has_saved_license": has_saved_license,
            "missing_dev_key": missing_dev_key,
            "current_step": current_step,
        }

    def _refresh_local_view(self) -> None:
        self._current_context = self._build_context()
        self._sync_default_banner()
        self._render_content()

    def _sync_default_banner(self) -> None:
        self._set_banner("", "info")

    def _render_content(self) -> None:
        self._clear_frame(self._content_frame)
        ctx = self._current_context
        state = self._resolve_screen_state(ctx)
        if state == "profile_form":
            self._render_profile_setup_section(self._content_frame, ctx)
        elif state == "choose_path":
            self._render_choose_path_section(self._content_frame, ctx)
        elif state == "trial_expired":
            self._render_trial_expired_section(self._content_frame, ctx)
        elif state == "request_license":
            self._render_request_license_section(self._content_frame, ctx)
        elif state == "paste_code":
            self._render_paste_code_section(self._content_frame, ctx)
        elif state == "trial_active":
            self._render_trial_active_section(self._content_frame, ctx)
        else:
            self._render_license_active_section(self._content_frame, ctx)

    def _resolve_screen_state(self, ctx: dict) -> str:
        return "license_active"

    def _sync_profile_vars(self, profile=None) -> None:
        data = profile or load_user_profile()
        if data.get("full_name") and not self.var_profile_name.get().strip():
            self.var_profile_name.set(str(data.get("full_name", "")).strip())
        if data.get("email") and not self.var_profile_email.get().strip():
            self.var_profile_email.set(str(data.get("email", "")).strip())
        if data.get("phone") and not self.var_profile_phone.get().strip():
            self.var_profile_phone.set(str(data.get("phone", "")).strip())
        if data.get("country") and not self.var_profile_country.get().strip():
            self.var_profile_country.set(str(data.get("country", "")).strip())

    def _profile_name_for_display(self, ctx: dict) -> str:
        return str(ctx["local_status"].get("customer_name", "")).strip() or str(ctx["user_profile"].get("full_name", "")).strip()

    def _save_profile(self) -> None:
        try:
            profile = save_user_profile(
                full_name=self.var_profile_name.get(),
                email=self.var_profile_email.get(),
                phone=self.var_profile_phone.get(),
                country=self.var_profile_country.get(),
            )
        except ValueError as exc:
            self._set_banner(str(exc), "warning")
            return
        self.var_profile_name.set(profile["full_name"])
        self.var_profile_email.set(profile["email"])
        self.var_profile_phone.set(profile["phone"])
        self.var_profile_country.set(profile["country"])
        self._force_profile_view = False
        self._screen_override = ""
        self._refresh_local_view()
        self._set_banner("Tus datos se guardaron correctamente. Ahora elige cómo quieres activar TLAMATINI.", "success")

    def _render_profile_setup_section(self, parent, ctx: dict) -> None:
        self._sync_profile_vars(ctx.get("user_profile"))
        card = self._make_card(
            parent,
            "Bienvenido a TLAMATINI",
            "Para comenzar, guarda tus datos y elige cómo quieres activar TLAMATINI.",
            tone="soft",
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        fields = tk.Frame(body, bg=card.cget("bg"))
        fields.pack(fill="x")
        entries = [
            ("Nombre completo", self.var_profile_name, 0, 0),
            ("Correo electrónico", self.var_profile_email, 0, 1),
            ("Teléfono opcional", self.var_profile_phone, 2, 0),
            ("País opcional", self.var_profile_country, 2, 1),
        ]
        for label, variable, row, col in entries:
            tk.Label(fields, text=label, font=("Arial", 10, "bold"), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=row, column=col, sticky="w", padx=(0, 12), pady=(0, 4))
            tk.Entry(fields, textvariable=variable, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=row + 1, column=col, sticky="ew", padx=(0, 12), pady=(0, 10))
        fields.grid_columnconfigure(0, weight=1)
        fields.grid_columnconfigure(1, weight=1)

        self._create_button(body, "Guardar y continuar", self._save_profile, role="primary").pack(anchor="w", pady=(4, 0))

    def _render_access_options_section(self, parent, ctx: dict) -> None:
        card = self._make_card(
            parent,
            "Información de licencia",
            "Solicita tu activación manual, inicia la prueba o pega un código recibido.",
            tone="soft",
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        tk.Label(
            body,
            text=f"Hola, {self._profile_name_for_display(ctx) or ctx['user_profile'].get('full_name')}. Puedes solicitar una licencia mensual, iniciar prueba o pegar un código recibido.",
            font=("Arial", 10),
            bg=card.cget("bg"),
            fg=PALETA["text_dim"],
            justify="left",
            wraplength=820,
        ).pack(anchor="w", pady=(0, 12))

        actions = tk.Frame(body, bg=card.cget("bg"))
        actions.pack(fill="x")
        self._create_button(actions, "Solicitar licencia mensual", self._copy_license_request, role="secondary").pack(side="left", padx=(0, 8))
        self._create_button(actions, "Activar prueba de 7 días", self._start_trial, role="primary").pack(side="left", padx=(0, 8))
        self._create_button(actions, "Ya tengo un código", self._show_manual_activation, role="soft").pack(side="left", padx=(0, 8))
        self._create_button(actions, "Editar datos", self._edit_profile, role="soft").pack(side="left")

    def _render_license_summary_section(self, parent, ctx: dict) -> None:
        local_status = ctx["local_status"]
        tone = "soft"
        if str(local_status.get("state", "")).strip().lower() == "invalid":
            tone = "danger"
        elif str(local_status.get("state", "")).strip().lower() == "expired":
            tone = "warning"
        elif local_status.get("is_valid"):
            tone = "success"

        card = self._make_card(
            parent,
            "Resumen de licencia",
            "Estado actual de esta instalación.",
            tone=tone,
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        facts = [
            ("Estado de licencia", self._manual_license_state_label(ctx)),
            ("Nombre", self._profile_name_for_display(ctx) or "No disponible"),
            ("Plan", str(local_status.get("plan", "")).strip() or "Sin plan"),
            ("Vencimiento", str(local_status.get("expires_at", "")).strip() or "No disponible"),
            ("Días restantes", str(local_status.get("days_remaining")) if local_status.get("days_remaining") is not None else "Sin licencia"),
            ("Email", self._manual_license_email(ctx)),
            ("ID de instalación", ctx["identity"]["installation_id"]),
        ]
        for label, value in facts:
            row = tk.Frame(body, bg=card.cget("bg"))
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=("Arial", 10, "bold"), bg=card.cget("bg"), fg=PALETA["text"], width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text_dim"], anchor="w", justify="left").pack(side="left", fill="x", expand=True)

    def _make_card(self, parent, title: str, subtitle: str, *, tone: str = "default") -> tk.Frame:
        tone_map = {
            "default": (PALETA["panel"], PALETA["border"]),
            "soft": (PALETA["panel_alt"], PALETA["border"]),
            "success": ("#0f2d1a", PALETA["ok_dark"]),
            "warning": ("#35270a", PALETA["warn_dark"]),
            "danger": ("#351416", PALETA["danger_dark"]),
        }
        bg, border = tone_map.get(tone, tone_map["default"])
        card = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=border)
        card.pack(fill="x", pady=(0, 12))

        tk.Label(card, text=title, font=("Arial", 15, "bold"), bg=bg, fg=PALETA["text"]).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(
            card,
            text=subtitle,
            font=("Arial", 10),
            bg=bg,
            fg=PALETA["text_dim"],
            justify="left",
            wraplength=820,
        ).pack(anchor="w", padx=16, pady=(0, 12))
        return card

    def _create_button(self, parent, text: str, command, *, role: str = "primary", width: int | None = None) -> tk.Button:
        styles = {
            "primary": (PALETA["ok"], PALETA["white"]),
            "secondary": (PALETA["accent"], "#00111d"),
            "soft": (PALETA["soft"], PALETA["text"]),
            "warning": (PALETA["warn"], "#1f1400"),
            "danger": (PALETA["danger"], PALETA["white"]),
        }
        bg, fg = styles.get(role, styles["primary"])
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Arial", 11, "bold"),
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            relief="flat",
            padx=14,
            pady=10,
            width=width,
        )

    def _render_choose_path_section(self, parent, ctx: dict) -> None:
        card = self._make_card(parent, "Elige cómo comenzar", "Elige cómo quieres activar TLAMATINI.", tone="soft")
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        trial_card = tk.Frame(body, bg=PALETA["panel_soft"], highlightthickness=1, highlightbackground=PALETA["border"])
        trial_card.pack(fill="x", pady=(0, 10))
        tk.Label(trial_card, text="Activar prueba gratuita de 7 días", font=("Arial", 12, "bold"), bg=PALETA["panel_soft"], fg=PALETA["text"]).pack(anchor="w", padx=12, pady=(12, 4))
        tk.Label(trial_card, text="Usa TLAMATINI durante 7 días sin solicitar una licencia mensual.", font=("Arial", 10), bg=PALETA["panel_soft"], fg=PALETA["text_dim"], justify="left", wraplength=800).pack(anchor="w", padx=12, pady=(0, 10))
        if not ctx["local_status"].get("trial_expired"):
            self._create_button(trial_card, "Activar prueba de 7 días", self._start_trial, role="primary").pack(anchor="w", padx=12, pady=(0, 12))

        monthly_card = tk.Frame(body, bg=PALETA["panel_soft"], highlightthickness=1, highlightbackground=PALETA["border"])
        monthly_card.pack(fill="x")
        tk.Label(monthly_card, text="Solicitar licencia mensual", font=("Arial", 12, "bold"), bg=PALETA["panel_soft"], fg=PALETA["text"]).pack(anchor="w", padx=12, pady=(12, 4))
        tk.Label(monthly_card, text="Copia tu solicitud de licencia y envíala al administrador después del pago. Recibirás un código de activación.", font=("Arial", 10), bg=PALETA["panel_soft"], fg=PALETA["text_dim"], justify="left", wraplength=800).pack(anchor="w", padx=12, pady=(0, 10))
        self._create_button(monthly_card, "Solicitar licencia mensual", self._show_request_license, role="secondary").pack(anchor="w", padx=12, pady=(0, 12))

        secondary = tk.Frame(body, bg=card.cget("bg"))
        secondary.pack(fill="x", pady=(12, 0))
        self._create_button(secondary, "Pegar código recibido", self._show_manual_activation, role="soft").pack(side="left", padx=(0, 8))
        self._create_button(secondary, "Editar datos", self._edit_profile, role="soft").pack(side="left")

    def _render_trial_expired_section(self, parent, ctx: dict) -> None:
        card = self._make_card(
            parent,
            "Tu prueba gratuita ha vencido",
            "Para seguir usando TLAMATINI, solicita una licencia mensual o pega un código recibido.",
            tone="warning",
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))
        actions = tk.Frame(body, bg=card.cget("bg"))
        actions.pack(fill="x")
        self._create_button(actions, "Solicitar licencia mensual", self._show_request_license, role="secondary").pack(side="left", padx=(0, 8))
        self._create_button(actions, "Pegar código recibido", self._show_manual_activation, role="soft").pack(side="left", padx=(0, 8))
        self._create_button(actions, "Editar mis datos", self._edit_profile, role="soft").pack(side="left")

    def _render_request_license_section(self, parent, ctx: dict) -> None:
        card = self._make_card(
            parent,
            "Solicitar licencia mensual",
            "Copia esta solicitud y envíala al administrador después de realizar el pago. Recibirás un código de activación.",
            tone="soft",
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        summary = [
            ("Nombre", self._profile_name_for_display(ctx) or "No disponible"),
            ("Email", self._manual_license_email(ctx)),
            ("ID de instalación", ctx["identity"]["installation_id"]),
            ("Plan solicitado", "mensual"),
        ]
        for label, value in summary:
            row = tk.Frame(body, bg=card.cget("bg"))
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=("Arial", 10, "bold"), bg=card.cget("bg"), fg=PALETA["text"], width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text_dim"], anchor="w", justify="left").pack(side="left", fill="x", expand=True)

        self._create_button(body, "Copiar solicitud de licencia", self._copy_license_request, role="secondary").pack(anchor="w", pady=(12, 12))
        self._render_code_box(body, include_back=True)

    def _render_paste_code_section(self, parent, ctx: dict) -> None:
        card = self._make_card(
            parent,
            "Pegar código de licencia",
            "Pega aquí el código que recibiste para activar TLAMATINI.",
            tone="soft",
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))
        self._render_code_box(body, include_back=True)

    def _render_code_box(self, parent, *, include_back: bool) -> None:
        tk.Label(parent, text="Pega aquí tu código de licencia…", font=("Arial", 10), bg=parent.cget("bg"), fg=PALETA["text_dim"]).pack(anchor="w", pady=(0, 6))
        self._manual_license_text = tk.Text(parent, height=8, font=("Courier New", 10), bg="white", fg="#0f172a", wrap="word", relief="flat")
        self._manual_license_text.pack(fill="x")
        saved_code = load_offline_license_code()
        if saved_code and not self._manual_license_text.get("1.0", "end").strip():
            self._manual_license_text.insert("1.0", saved_code)
        if self.var_manual_status.get().strip():
            status_fg = PALETA["ok"] if self.var_manual_status.get().strip().startswith("Solicitud copiada") else PALETA["warn"]
            tk.Label(parent, text=self.var_manual_status.get().strip(), font=("Arial", 10, "bold"), bg=parent.cget("bg"), fg=status_fg, justify="left", wraplength=820).pack(anchor="w", pady=(10, 0))
        actions = tk.Frame(parent, bg=parent.cget("bg"))
        actions.pack(fill="x", pady=(12, 0))
        self._create_button(actions, "Activar licencia", self._activate_manual_license, role="primary").pack(side="left", padx=(0, 8))
        if include_back:
            self._create_button(actions, "Volver", self._back_to_choose_path, role="soft").pack(side="left")

    def _render_trial_active_section(self, parent, ctx: dict) -> None:
        card = self._make_card(parent, "Prueba activa", "Tu prueba local de 7 días ya está activa en esta instalación.", tone="success")
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))
        for label, value in (
            ("Estado", "Prueba activa"),
            ("Plan", "trial"),
            ("Vence", str(ctx["local_status"].get("expires_at", "")).strip() or "No disponible"),
            ("Días restantes", str(ctx["local_status"].get("days_remaining")) if ctx["local_status"].get("days_remaining") is not None else "No disponible"),
            ("Email", self._manual_license_email(ctx)),
        ):
            row = tk.Frame(body, bg=card.cget("bg"))
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=("Arial", 10, "bold"), bg=card.cget("bg"), fg=PALETA["text"], width=18, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text_dim"], anchor="w", justify="left").pack(side="left", fill="x", expand=True)
        actions = tk.Frame(body, bg=card.cget("bg"))
        actions.pack(fill="x", pady=(12, 0))
        self._create_button(actions, "Solicitar licencia mensual", self._show_request_license, role="secondary").pack(side="left", padx=(0, 8))
        self._create_button(actions, "Pegar código recibido", self._show_manual_activation, role="soft").pack(side="left")

    def _render_license_active_section(self, parent, ctx: dict) -> None:
        card = self._make_card(parent, "TLAMATINI", "", tone="default")
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))
        actions = tk.Frame(body, bg=card.cget("bg"))
        actions.pack(fill="x")
        self._create_button(actions, "Continuar a TLAMATINI", self.destroy, role="primary").pack(side="left", padx=(0, 8))

    def _render_connection_step(self, parent, ctx: dict) -> None:
        has_backend = ctx["has_backend"]
        title = "Paso 1. Conexión"
        subtitle = "TLAMATINI usa un servicio de licencias para crear tu cuenta y activar tu acceso."
        tone = "soft" if has_backend else "default"
        card = self._make_card(parent, title, subtitle, tone=tone)
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        if ctx["has_valid_license"] and not has_backend:
            tk.Label(
                body,
                text="Esta instalación ya está activada localmente",
                font=("Arial", 13, "bold"),
                bg=card.cget("bg"),
                fg=PALETA["ok"],
            ).pack(anchor="w")
            tk.Label(
                body,
                text="No necesitas volver a configurar el servidor para seguir usando TLAMATINI en este equipo.",
                font=("Arial", 10),
                bg=card.cget("bg"),
                fg=PALETA["text_dim"],
            ).pack(anchor="w", pady=(6, 0))
        elif has_backend:
            source = ctx["backend_cfg"].get("source")
            status_text = "El servicio de TLAMATINI ya está listo."
            if source == "default":
                status_text = "El servicio de TLAMATINI ya viene configurado."
            tk.Label(
                body,
                text=status_text,
                font=("Arial", 13, "bold"),
                bg=card.cget("bg"),
                fg=PALETA["ok"],
            ).pack(anchor="w")
            tk.Label(
                body,
                text="Puedes continuar con tu cuenta.",
                font=("Arial", 10),
                bg=card.cget("bg"),
                fg=PALETA["text_dim"],
            ).pack(anchor="w", pady=(6, 0))
        else:
            tk.Label(
                body,
                text="Falta la configuración del servicio",
                font=("Arial", 13, "bold"),
                bg=card.cget("bg"),
                fg=PALETA["warn"],
            ).pack(anchor="w")
            tk.Label(
                body,
                text="Esto solo debe usarse en soporte o instalación avanzada.",
                font=("Arial", 10),
                bg=card.cget("bg"),
                fg=PALETA["text_dim"],
            ).pack(anchor="w", pady=(6, 0))

    def _render_auth_switch(self, parent, selected_mode: str) -> None:
        switch = tk.Frame(parent, bg=parent.cget("bg"))
        switch.pack(fill="x", pady=(0, 12))

        register_role = "primary" if selected_mode == "register" else "soft"
        login_role = "primary" if selected_mode == "login" else "soft"

        self._create_button(switch, "Crear cuenta nueva", lambda: self._set_auth_mode("register"), role=register_role).pack(side="left", padx=(0, 8))
        self._create_button(switch, "Ya tengo cuenta", lambda: self._set_auth_mode("login"), role=login_role).pack(side="left")

    def _render_account_step(self, parent, ctx: dict) -> None:
        card = self._make_card(
            parent,
            "Paso 2. Cuenta",
            "Captura tus datos para crear tu cuenta o entrar con una existente.",
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        if ctx["has_session"]:
            email = str(ctx["session"].get("user", {}).get("email", "")).strip() or "Sesión activa"
            tk.Label(body, text=f"Sesión iniciada: {email}", font=("Arial", 13, "bold"), bg=card.cget("bg"), fg=PALETA["ok"]).pack(anchor="w")
            tk.Label(
                body,
                text="Continúa con la activación.",
                font=("Arial", 10),
                bg=card.cget("bg"),
                fg=PALETA["text_dim"],
            ).pack(anchor="w", pady=(6, 12))
            self._create_button(body, "Cerrar sesión", self._logout, role="soft").pack(anchor="w")
            return

        selected_mode = self.var_auth_mode.get().strip() or "register"
        self._render_auth_switch(body, selected_mode)

        form = tk.Frame(body, bg=card.cget("bg"))
        form.pack(fill="x")

        tk.Label(form, text="Correo electrónico", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=0, column=0, sticky="w")
        tk.Entry(form, textvariable=self.var_email, font=("Arial", 12), bg="white", fg="#0f172a").grid(row=1, column=0, sticky="ew", pady=(6, 10))

        tk.Label(form, text="Contraseña", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=2, column=0, sticky="w")
        tk.Entry(form, textvariable=self.var_password, show="*", font=("Arial", 12), bg="white", fg="#0f172a").grid(row=3, column=0, sticky="ew", pady=(6, 10))

        if selected_mode == "register":
            tk.Label(form, text="Idioma", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=4, column=0, sticky="w")
            tk.Entry(form, textvariable=self.var_language, font=("Arial", 12), bg="white", fg="#0f172a").grid(row=5, column=0, sticky="ew", pady=(6, 12))
            self._create_button(form, "Crear cuenta y continuar", self._register_and_login, role="primary").grid(row=6, column=0, sticky="w")
        else:
            self._create_button(form, "Iniciar sesión", self._login, role="secondary").grid(row=4, column=0, sticky="w", pady=(2, 0))

        form.grid_columnconfigure(0, weight=1)

    def _render_activation_step(self, parent, ctx: dict) -> None:
        tone = "default"
        if ctx["local_state"] == "expired":
            tone = "warning"
        elif ctx["local_state"] == "invalid":
            tone = "danger"

        card = self._make_card(
            parent,
            "Paso 3. Activación",
            "Elige la opción con la que quieres empezar.",
            tone=tone,
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        title, description = self._activation_copy(ctx)
        tk.Label(body, text=title, font=("Arial", 13, "bold"), bg=card.cget("bg"), fg=PALETA["text"]).pack(anchor="w")
        tk.Label(
            body,
            text=description,
            font=("Arial", 10),
            bg=card.cget("bg"),
            fg=PALETA["text_dim"],
            justify="left",
            wraplength=820,
        ).pack(anchor="w", pady=(6, 10))

        self._render_status_facts(body, ctx, include_installation=False)

        actions = tk.Frame(body, bg=card.cget("bg"))
        actions.pack(fill="x", pady=(12, 0))

        primary, secondary = self._activation_actions(ctx)
        self._create_button(actions, primary["text"], primary["command"], role=primary["role"]).pack(side="left", padx=(0, 10))
        if secondary:
            self._create_button(actions, secondary["text"], secondary["command"], role=secondary["role"]).pack(side="left")

        if ctx["has_session"]:
            extra = tk.Frame(body, bg=card.cget("bg"))
            extra.pack(fill="x", pady=(12, 0))
            self._create_button(extra, "Cerrar sesión", self._logout, role="soft").pack(anchor="w")

    def _activation_copy(self, ctx: dict) -> tuple[str, str]:
        state = ctx["local_state"]
        plan = ctx["plan"] or "sin plan"

        if state == "expired":
            return (
                "La licencia local venció",
                "Sincroniza la licencia para recuperar el estado más reciente o renueva la suscripción si ya terminó tu periodo actual.",
            )
        if state == "invalid":
            if ctx["missing_dev_key"]:
                return (
                    "La licencia no pudo validarse en este equipo",
                    "Si estás trabajando en modo local de desarrollo, abre las opciones avanzadas y pega la clave de validación correspondiente.",
                )
            return (
                "La licencia guardada necesita revisión",
                "Puedes intentar sincronizar de nuevo la licencia. Si el problema persiste, revisa la configuración avanzada.",
            )
        if plan == "trial":
            return (
                "La prueba ya está guardada",
                "Puedes seguir con tu prueba o activar la mensualidad cuando quieras.",
            )
        if plan:
            return (
                f"Licencia detectada: {plan}",
                "Puedes sincronizar el estado o renovar la mensualidad.",
            )
        return (
            "Todavía no has activado TLAMATINI",
            "Inicia tu prueba gratis de 7 días o activa tu mensualidad.",
        )

    def _activation_actions(self, ctx: dict) -> tuple[dict, dict | None]:
        state = ctx["local_state"]
        plan = ctx["plan"]

        if state == "expired":
            return (
                {"text": "Sincronizar licencia", "command": self._sync_license, "role": "secondary"},
                {"text": "Solicitar renovación", "command": self._open_checkout, "role": "primary"},
            )
        if state == "invalid":
            if ctx["missing_dev_key"]:
                return (
                    {"text": "Mostrar opciones avanzadas", "command": self._toggle_advanced, "role": "warning"},
                    {"text": "Sincronizar licencia", "command": self._sync_license, "role": "secondary"},
                )
            return (
                {"text": "Sincronizar licencia", "command": self._sync_license, "role": "secondary"},
                {"text": "Solicitar licencia mensual", "command": self._open_checkout, "role": "primary"},
            )
        if plan == "trial":
            return (
                {"text": "Sincronizar licencia", "command": self._sync_license, "role": "secondary"},
                {"text": "Solicitar licencia mensual", "command": self._open_checkout, "role": "primary"},
            )
        if plan:
            return (
                {"text": "Sincronizar licencia", "command": self._sync_license, "role": "secondary"},
                {"text": "Solicitar renovación", "command": self._open_checkout, "role": "primary"},
            )
        return (
            {"text": "Activar prueba de 7 días", "command": self._start_trial, "role": "primary"},
            {"text": "Solicitar licencia mensual", "command": self._open_checkout, "role": "secondary"},
        )

    def _render_status_facts(self, parent, ctx: dict, *, include_installation: bool) -> None:
        facts = tk.Frame(parent, bg=parent.cget("bg"))
        facts.pack(fill="x", pady=(4, 0))
        local_status = ctx["local_status"]

        lines = [
            f"Estado: {self._friendly_state(ctx['local_state'])}",
            f"Plan: {ctx['plan'] or '--'}",
            f"Vence: {local_status.get('expires_at') or '--'}",
            f"Días restantes: {local_status.get('days_remaining') if local_status.get('days_remaining') is not None else '--'}",
        ]
        if local_status.get("grace_until"):
            lines.append(f"Gracia hasta: {local_status.get('grace_until')}")
        if local_status.get("last_sync_at"):
            lines.append(f"Última sincronización: {local_status.get('last_sync_at')}")
        if include_installation:
            identity = ctx["identity"]
            lines.append(f"Instalación: {identity['installation_id']}")

        for line in lines:
            tk.Label(
                facts,
                text=line,
                font=("Arial", 10),
                bg=parent.cget("bg"),
                fg=PALETA["text"],
                anchor="w",
            ).pack(fill="x", pady=1)

    def _render_done_step(self, parent, ctx: dict) -> None:
        plan = ctx["plan"] or "activo"
        state = ctx["local_state"]
        subtitle = "Tu licencia ya es válida en este equipo. Puedes cerrar esta ventana y seguir trabajando."
        if state == "grace":
            subtitle = "Tu licencia sigue funcionando en modo gracia. Conviene sincronizarla para recuperar el estado normal."

        card = self._make_card(parent, "Paso 4. TLAMATINI activado correctamente", subtitle, tone="success")
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        tk.Label(
            body,
            text=f"Plan actual: {plan}",
            font=("Arial", 14, "bold"),
            bg=card.cget("bg"),
            fg="#dcfce7",
        ).pack(anchor="w", pady=(0, 8))

        self._render_status_facts(body, ctx, include_installation=False)

        actions = tk.Frame(body, bg=card.cget("bg"))
        actions.pack(fill="x", pady=(14, 0))
        self._create_button(actions, "Continuar a TLAMATINI", self.destroy, role="primary").pack(side="left", padx=(0, 10))

        secondary = None
        if state == "grace" and ctx["has_session"]:
            secondary = {"text": "Sincronizar licencia", "command": self._sync_license, "role": "secondary"}
        elif plan == "trial" and ctx["has_session"]:
            secondary = {"text": "Solicitar licencia mensual", "command": self._open_checkout, "role": "secondary"}
        elif ctx["has_session"]:
            secondary = {"text": "Solicitar renovación", "command": self._open_checkout, "role": "secondary"}

        if secondary:
            self._create_button(actions, secondary["text"], secondary["command"], role=secondary["role"]).pack(side="left")

    def _render_manual_activation_section(self, parent, ctx: dict, *, renew_mode: bool = False) -> None:
        state = str(ctx["local_status"].get("state", "missing")).strip().lower()
        tone = "soft"
        if state == "invalid":
            tone = "danger"
        elif state == "expired":
            tone = "warning"
        elif ctx["local_status"].get("source") == "offline_code" and ctx["local_status"].get("is_valid"):
            tone = "success"

        card = self._make_card(
            parent,
            "Activación manual por código" if not renew_mode else "Renovar licencia por código",
            "Activa tu licencia pegando el código que recibiste después del pago.",
            tone=tone,
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        step1 = tk.Frame(body, bg=card.cget("bg"))
        step1.pack(fill="x", pady=(0, 12))
        tk.Label(step1, text="1. Copia tu solicitud de licencia", font=("Arial", 11, "bold"), bg=card.cget("bg"), fg=PALETA["text"]).pack(anchor="w")
        tk.Label(
            step1,
            text="Envíanos esta solicitud después de realizar el pago para generar tu código de activación.",
            font=("Arial", 10),
            bg=card.cget("bg"),
            fg=PALETA["text_dim"],
            justify="left",
            wraplength=820,
        ).pack(anchor="w", pady=(4, 8))
        self._create_button(step1, "Copiar solicitud de licencia", self._copy_license_request, role="secondary").pack(anchor="w")

        step2 = tk.Frame(body, bg=card.cget("bg"))
        step2.pack(fill="x", pady=(0, 12))
        tk.Label(step2, text="2. Pega tu código de licencia", font=("Arial", 11, "bold"), bg=card.cget("bg"), fg=PALETA["text"]).pack(anchor="w")
        tk.Label(step2, text="Pega aquí tu código de licencia…", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text_dim"]).pack(anchor="w", pady=(4, 6))
        self._manual_license_text = tk.Text(body, height=8, font=("Courier New", 10), bg="white", fg="#0f172a", wrap="word", relief="flat")
        self._manual_license_text.pack(fill="x")
        saved_code = load_offline_license_code()
        if saved_code and not self._manual_license_text.get("1.0", "end").strip():
            self._manual_license_text.insert("1.0", saved_code)

        step3 = tk.Frame(body, bg=card.cget("bg"))
        step3.pack(fill="x", pady=(12, 0))
        tk.Label(step3, text="3. Activar", font=("Arial", 11, "bold"), bg=card.cget("bg"), fg=PALETA["text"]).pack(anchor="w", pady=(0, 6))
        self._create_button(step3, "Activar licencia", self._activate_manual_license, role="primary").pack(anchor="w")

        status_message = self.var_manual_status.get().strip()
        if not status_message:
            local_message = str(ctx["local_status"].get("message", "")).strip()
            if str(ctx["local_status"].get("source", "")).strip() == "offline_code":
                status_message = local_message or "La activación manual está lista en este equipo."
            elif local_message and state in {"invalid", "expired"}:
                status_message = local_message
        if status_message:
            tk.Label(
                body,
                text=status_message,
                font=("Arial", 10, "bold"),
                bg=card.cget("bg"),
                fg=PALETA["ok"] if ctx["local_status"].get("source") == "offline_code" and ctx["local_status"].get("is_valid") else PALETA["warn"],
                justify="left",
                wraplength=820,
            ).pack(anchor="w", pady=(10, 0))

        actions = tk.Frame(body, bg=card.cget("bg"))
        actions.pack(fill="x", pady=(12, 0))
        self._create_button(actions, "Limpiar", self._clear_manual_license_input, role="soft").pack(side="left")
        if not renew_mode:
            self._create_button(actions, "Editar datos", self._edit_profile, role="soft").pack(side="left", padx=(8, 0))
        self._create_button(
            actions,
            "Ver detalles técnicos" if not self._manual_details_visible else "Ocultar detalles técnicos",
            self._toggle_manual_details,
            role="soft",
        ).pack(side="left", padx=(8, 0))

        if self._manual_details_visible:
            self._render_manual_details(body, ctx)

    def _render_advanced_section(self, parent, ctx: dict) -> None:
        shell = tk.Frame(parent, bg=PALETA["bg"])
        shell.pack(fill="x", pady=(4, 0))

        toggle_text = "Ocultar opciones avanzadas" if self._advanced_visible else "Mostrar opciones avanzadas"
        self._advanced_toggle_button = self._create_button(shell, toggle_text, self._toggle_advanced, role="soft")
        self._advanced_toggle_button.pack(anchor="w")

        if not self._advanced_visible:
            return

        card = self._make_card(
            parent,
            "Opciones avanzadas",
            "Configuración técnica para soporte, pruebas y diagnóstico.",
            tone="soft",
        )
        body = tk.Frame(card, bg=card.cget("bg"))
        body.pack(fill="x", padx=16, pady=(0, 14))

        tk.Label(body, text="URL backend", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=0, column=0, sticky="w")
        tk.Entry(body, textvariable=self.var_backend_url, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 10))
        tk.Label(body, text="Modo backend", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=2, column=0, sticky="w")
        tk.OptionMenu(body, self.var_backend_mode, "hybrid", "remote-only", "dev-local").grid(row=3, column=0, sticky="w", pady=(6, 10))

        tk.Label(body, text="Clave local de validación", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=4, column=0, sticky="w")
        tk.Entry(body, textvariable=self.var_backend_public_key, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=5, column=0, columnspan=2, sticky="ew", pady=(6, 10))

        if ctx["missing_dev_key"]:
            tk.Label(
                body,
                text="Para pruebas locales con HS256, pega aquí LICENSE_SIGNING_SECRET del backend/.env.",
                font=("Arial", 10, "bold"),
                bg=card.cget("bg"),
                fg=PALETA["warn"],
                justify="left",
                wraplength=760,
            ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 10))

        info = tk.Frame(body, bg=card.cget("bg"))
        info.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self._advanced_info_lines(info, ctx)

        actions = tk.Frame(body, bg=card.cget("bg"))
        actions.grid(row=8, column=0, columnspan=2, sticky="w")
        self._create_button(actions, "Guardar servidor", self._save_backend_settings, role="secondary").pack(side="left", padx=(0, 8))
        self._create_button(actions, "Refrescar estado local", self._refresh_local_view, role="soft").pack(side="left", padx=(0, 8))
        if ctx["has_backend"] and ctx["has_session"]:
            self._create_button(actions, "Sincronizar licencia", self._sync_license, role="secondary").pack(side="left", padx=(0, 8))
        if ctx["has_session"]:
            self._create_button(actions, "Cerrar sesión", self._logout, role="soft").pack(side="left")

        if ctx["has_session"]:
            billing = tk.Frame(body, bg=card.cget("bg"))
            billing.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(12, 0))
            tk.Label(billing, text="País", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=0, column=0, sticky="w")
            tk.Entry(billing, textvariable=self.var_country, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(6, 8))
            tk.Label(billing, text="Código postal", font=("Arial", 10), bg=card.cget("bg"), fg=PALETA["text"]).grid(row=0, column=1, sticky="w")
            tk.Entry(billing, textvariable=self.var_postal, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=1, column=1, sticky="ew", pady=(6, 8))
            self._create_button(billing, "Abrir checkout", self._open_checkout, role="primary").grid(row=1, column=2, padx=(8, 0), sticky="ew")
            billing.grid_columnconfigure(0, weight=1)
            billing.grid_columnconfigure(1, weight=1)

        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

    def _advanced_info_lines(self, parent, ctx: dict) -> None:
        session_email = str(ctx["session"].get("user", {}).get("email", "")).strip() or "--"
        identity = ctx["identity"]
        local_status = ctx["local_status"]
        lines = [
            f"Modo backend: {ctx['backend_cfg'].get('mode', '--')}",
            f"Backend guardado: {ctx['backend_cfg'].get('raw_url') or '--'}",
            f"Backend predeterminado: {ctx['backend_cfg'].get('default_url') or '--'}",
            f"Backend efectivo: {ctx['backend'] or '--'}",
            f"Permite backend local: {'sí' if ctx['backend_cfg'].get('local_backend_allowed') else 'no'}",
            f"Sesión: {session_email}",
            f"Estado local: {ctx['local_state']}",
            f"Plan local: {ctx['plan'] or '--'}",
            f"Última sincronización: {local_status.get('last_sync_at') or '--'}",
            f"installation_id: {identity['installation_id']}",
            f"Equipo: {identity['device_name']} | {identity['os_name']} | app {identity['app_version']}",
        ]
        for line in lines:
            tk.Label(
                parent,
                text=line,
                font=("Arial", 10),
                bg=parent.cget("bg"),
                fg=PALETA["text"],
                anchor="w",
                justify="left",
                wraplength=780,
            ).pack(fill="x", pady=1)

    def _friendly_state(self, state: str) -> str:
        labels = {
            "valid": "válida",
            "grace": "en gracia",
            "expired": "vencida",
            "invalid": "inválida",
            "missing": "sin licencia",
        }
        return labels.get(state, state or "--")

    def _set_auth_mode(self, mode: str) -> None:
        self.var_auth_mode.set(mode)
        self._render_content()

    def _toggle_advanced(self) -> None:
        self._advanced_visible = not self._advanced_visible
        self._render_content()

    def _toggle_manual_details(self) -> None:
        self._manual_details_visible = not self._manual_details_visible
        self._render_content()

    def _show_manual_activation(self) -> None:
        self._screen_override = "paste_code"
        self._render_content()

    def _show_request_license(self) -> None:
        self._screen_override = "request_license"
        self._render_content()

    def _back_to_choose_path(self) -> None:
        self._screen_override = ""
        self.var_manual_status.set("")
        self._render_content()

    def _edit_profile(self) -> None:
        self._force_profile_view = True
        self._screen_override = "profile_form"
        self._sync_profile_vars()
        self._render_content()

    def _copy_to_clipboard(self, text: str, success_message: str) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(str(text))
            self.update_idletasks()
            self._set_banner(success_message, "success")
        except Exception as exc:
            self._set_banner(f"No se pudo copiar al portapapeles: {exc}", "danger")

    def _manual_license_state_label(self, ctx: dict) -> str:
        local_status = ctx["local_status"]
        state = str(local_status.get("state", "missing")).strip().lower()
        source = str(local_status.get("source", "")).strip().lower()
        if state in {"valid", "grace"}:
            if source == "local_trial" or str(local_status.get("plan", "")).strip().lower() == "trial":
                return "Prueba activa"
            return "Modo offline permitido" if source == "offline_code" else "Activa"
        if state == "expired":
            return "Vencida"
        if state == "invalid":
            return "Licencia inválida"
        if local_status.get("trial_expired"):
            return "Prueba utilizada"
        return "Sin licencia"

    def _manual_license_email(self, ctx: dict) -> str:
        local_status = ctx["local_status"]
        email = str(local_status.get("customer_email", "")).strip()
        if email:
            return email
        profile_email = str(ctx["user_profile"].get("email", "")).strip()
        if profile_email:
            return profile_email
        session_email = str(ctx["session"].get("user", {}).get("email", "")).strip()
        return session_email or "Pendiente"

    def _build_license_request_text(self, ctx: dict) -> str:
        return build_manual_license_request(
            profile=ctx["user_profile"],
            identity=ctx["identity"],
            current_state=self._manual_license_state_label(ctx),
            requested_plan=ctx["local_status"].get("plan") or "mensual",
        )

    def _copy_license_request(self) -> None:
        ctx = self._current_context or self._build_context()
        try:
            request_text = self._build_license_request_text(ctx)
        except ValueError as exc:
            self._set_banner(str(exc), "warning")
            self._force_profile_view = True
            self._screen_override = "profile_form"
            self._render_content()
            return
        self.var_manual_status.set("Solicitud copiada. Envíala al administrador. Cuando recibas tu código, pégalo abajo.")
        self._screen_override = "request_license"
        self._copy_to_clipboard(request_text, "La solicitud de licencia se copió al portapapeles.")

    def _copy_installation_id(self) -> None:
        installation_id = str((self._current_context or self._build_context())["identity"]["installation_id"]).strip()
        self._copy_to_clipboard(installation_id, "El ID de instalación se copió al portapapeles.")

    def _render_manual_details(self, parent, ctx: dict) -> None:
        local_status = ctx["local_status"]
        identity = ctx["identity"]
        details = tk.Frame(parent, bg=PALETA["panel_soft"], highlightthickness=1, highlightbackground=PALETA["border"])
        details.pack(fill="x", pady=(12, 0))
        for label, value in (
            ("Nombre", self._profile_name_for_display(ctx) or "No disponible"),
            ("Email", self._manual_license_email(ctx)),
            ("Estado", self._manual_license_state_label(ctx)),
            ("Plan", str(local_status.get("plan", "")).strip() or "Sin plan"),
            ("Vence", str(local_status.get("expires_at", "")).strip() or "No disponible"),
            ("Días restantes", local_status.get("days_remaining") if local_status.get("days_remaining") is not None else "No disponible"),
            ("ID de instalación", identity["installation_id"]),
        ):
            row = tk.Frame(details, bg=PALETA["panel_soft"])
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{label}:", font=("Arial", 10, "bold"), bg=PALETA["panel_soft"], fg=PALETA["text"], width=16, anchor="w").pack(side="left")
            tk.Label(row, text=str(value), font=("Arial", 10), bg=PALETA["panel_soft"], fg=PALETA["text_dim"], anchor="w", justify="left").pack(side="left", fill="x", expand=True)
        actions = tk.Frame(details, bg=PALETA["panel_soft"])
        actions.pack(fill="x", padx=12, pady=(10, 12))
        self._create_button(actions, "Copiar solo ID", self._copy_installation_id, role="soft").pack(side="left")

    def _manual_license_code(self) -> str:
        if self._manual_license_text is None:
            return ""
        return self._manual_license_text.get("1.0", "end").strip()

    def _clear_manual_license_input(self) -> None:
        if self._manual_license_text is not None:
            self._manual_license_text.delete("1.0", "end")
        self.var_manual_status.set("")
        self._set_banner("Campo de licencia manual limpiado.", "info")

    def _persist_backend_settings(self) -> None:
        save_backend_mode(self.var_backend_mode.get())
        save_backend_url(self.var_backend_url.get())
        save_public_key_material(self.var_backend_public_key.get())

    def _save_backend_settings(self) -> None:
        try:
            self._persist_backend_settings()
        except ValueError as exc:
            self._set_banner(str(exc), "danger")
            return
        self._refresh_local_view()
        self._set_banner("Configuración guardada.", "success")

    def _run_task(self, action, success_message: str | None = None, checkout_notice: bool = False) -> None:
        def worker():
            try:
                action()
            except BackendNotConfiguredError as exc:
                self.after(0, self._refresh_local_view)
                self.after(0, lambda: self.var_manual_status.set(str(exc)))
                self.after(0, lambda: self._set_banner(str(exc), "warning"))
                return
            except BackendUnavailableError as exc:
                self.after(0, self._refresh_local_view)
                self.after(0, lambda: self.var_manual_status.set(str(exc)))
                self.after(0, lambda: self._set_banner(str(exc), "warning"))
                return
            except LicenseClientError as exc:
                self.after(0, self._refresh_local_view)
                self.after(0, lambda: self.var_manual_status.set(str(exc)))
                self.after(0, lambda: self._set_banner(str(exc), "danger"))
                return
            except Exception as exc:
                self.after(0, self._refresh_local_view)
                self.after(0, lambda: self.var_manual_status.set(f"Error inesperado: {exc}"))
                self.after(0, lambda: self._set_banner(f"Error inesperado: {exc}", "danger"))
                return

            def on_success():
                self._refresh_local_view()
                self.var_manual_status.set(success_message or "")
                if success_message:
                    self._set_banner(success_message, "success")
                if checkout_notice:
                    messagebox.showinfo(
                        "Suscripción",
                        "Se abrió el pago.\n\nCuando termines, vuelve a TLAMATINI y pulsa Sincronizar licencia.",
                        parent=self,
                    )

            self.after(0, on_success)

        threading.Thread(target=worker, daemon=True).start()

    def _login(self) -> None:
        self._persist_backend_settings()
        email = self.var_email.get().strip()
        password = self.var_password.get()
        if not email or not password:
            self._set_banner("Escribe tu correo y contraseña para iniciar sesión.", "warning")
            return
        self._run_task(lambda: self.client.login(email=email, password=password), success_message="Sesión iniciada. Ahora activa tu acceso.")

    def _register_and_login(self) -> None:
        self._persist_backend_settings()
        email = self.var_email.get().strip()
        password = self.var_password.get()
        language = self.var_language.get().strip() or "es"
        if not email or not password:
            self._set_banner("Escribe correo y contraseña para crear la cuenta.", "warning")
            return
        self._run_task(
            lambda: self.client.register_and_login(email=email, password=password, preferred_language=language),
            success_message="Cuenta creada. Ahora activa tu acceso.",
        )

    def _logout(self) -> None:
        self.client.logout()
        self._refresh_local_view()
        self._set_banner("Sesión cerrada localmente.", "info")

    def _start_trial(self) -> None:
        ctx = self._current_context or self._build_context()
        if not ctx.get("profile_ready"):
            self._set_banner("Primero guarda tus datos para activar la prueba.", "warning")
            self._render_content()
            return
        self._run_task(self.client.start_trial, success_message="Prueba activada. Ya puedes continuar con TLAMATINI.")

    def _sync_license(self) -> None:
        self._persist_backend_settings()
        self._run_task(self.client.sync_license, success_message="Licencia sincronizada correctamente.")

    def _open_checkout(self) -> None:
        self._persist_backend_settings()
        country = self.var_country.get().strip() or "MX"
        postal = self.var_postal.get().strip()
        self._run_task(
            lambda: self.client.open_checkout(country_code=country, postal_code=postal),
            success_message="Checkout preparado.",
            checkout_notice=True,
        )

    def _activate_manual_license(self) -> None:
        code = self._manual_license_code()
        if not code:
            self.var_manual_status.set("Pega aquí tu código de licencia para activarlo.")
            self._set_banner("Pega aquí tu código de licencia para activarlo.", "warning")
            self._render_content()
            return
        self.var_manual_status.set("")
        self._run_task(
            lambda: self.client.activate_manual_license(code),
            success_message="Licencia manual activada correctamente.",
        )
