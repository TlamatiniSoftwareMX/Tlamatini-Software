#!/usr/bin/env python3
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import sys


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from license_generator_core import (
    DEFAULT_FEATURES,
    PRIVATE_KEY_PATH,
    generate_license_code,
    generate_license_keys,
    infer_duration_days_from_plan,
    parse_license_request_text,
    private_key_exists,
)


PALETTE = {
    "bg": "#071423",
    "panel": "#10243d",
    "muted": "#9db8d0",
    "text": "#eef6ff",
    "accent": "#38bdf8",
    "ok": "#22c55e",
    "warn": "#f59e0b",
    "border": "#294866",
}


class GeneradorLicenciasGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TLAMATINI - Generador privado de licencias")
        self.configure(bg=PALETTE["bg"])
        self.minsize(980, 760)

        self.var_plan = tk.StringVar(value="mensual")
        self.var_duration_mode = tk.StringVar(value="30")
        self.var_duration_custom = tk.StringVar(value="")
        self.var_full_name = tk.StringVar(value="")
        self.var_email = tk.StringVar(value="")
        self.var_phone = tk.StringVar(value="")
        self.var_country = tk.StringVar(value="")
        self.var_installation_id = tk.StringVar(value="")
        self.var_os_name = tk.StringVar(value="")
        self.var_app_version = tk.StringVar(value="")
        self.var_requested_plan = tk.StringVar(value="")
        self.var_status = tk.StringVar(value="Pega la solicitud del usuario para detectar los datos.")
        self._parse_after_id = None

        self.request_text = None
        self.output_text = None

        self._ensure_keys_for_first_use()
        self._build_ui()
        self._sync_duration_from_plan()

    def _ensure_keys_for_first_use(self) -> None:
        if private_key_exists():
            return
        accepted = messagebox.askyesno(
            "TLAMATINI - Clave privada",
            "No se encontró la clave privada. ¿Quieres generar las claves ahora?",
            parent=self,
        )
        if not accepted:
            self.destroy()
            raise SystemExit(0)
        paths = generate_license_keys(overwrite=False)
        messagebox.showwarning(
            "TLAMATINI - Claves generadas",
            (
                "Guarda private_license_key.pem en un lugar seguro. No la compartas ni la incluyas en el instalador.\n\n"
                f"Privada: {paths['private_key_path']}\n"
                f"Pública para la app: {paths['app_public_key_path']}"
            ),
            parent=self,
        )

    def _build_ui(self) -> None:
        wrapper = tk.Frame(self, bg=PALETTE["bg"])
        wrapper.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(wrapper, text="Generador privado de licencias", font=("Arial", 22, "bold"), bg=PALETTE["bg"], fg=PALETTE["text"]).pack(anchor="w")
        tk.Label(wrapper, textvariable=self.var_status, font=("Arial", 10), bg=PALETTE["bg"], fg=PALETTE["muted"], justify="left", wraplength=920).pack(anchor="w", pady=(6, 12))

        request_card = tk.Frame(wrapper, bg=PALETTE["panel"], highlightthickness=1, highlightbackground=PALETTE["border"])
        request_card.pack(fill="both", expand=True, pady=(0, 12))
        tk.Label(request_card, text="Pega aquí la solicitud del usuario", font=("Arial", 13, "bold"), bg=PALETTE["panel"], fg=PALETTE["text"]).pack(anchor="w", padx=14, pady=(14, 8))
        self.request_text = tk.Text(request_card, height=12, font=("Courier New", 10), wrap="word", bg="white", fg="#0f172a", relief="flat")
        self.request_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.request_text.bind("<KeyRelease>", self._schedule_parse_request)

        form_card = tk.Frame(wrapper, bg=PALETTE["panel"], highlightthickness=1, highlightbackground=PALETTE["border"])
        form_card.pack(fill="x", pady=(0, 12))
        tk.Label(form_card, text="Datos detectados y configuración", font=("Arial", 13, "bold"), bg=PALETTE["panel"], fg=PALETTE["text"]).grid(row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(14, 10))

        self._label_entry(form_card, "Nombre", self.var_full_name, row=1, col=0)
        self._label_entry(form_card, "Email", self.var_email, row=1, col=1)
        self._label_entry(form_card, "Teléfono", self.var_phone, row=3, col=0)
        self._label_entry(form_card, "País", self.var_country, row=3, col=1)
        self._label_entry(form_card, "ID de instalación", self.var_installation_id, row=5, col=0)
        self._label_entry(form_card, "Sistema operativo", self.var_os_name, row=5, col=1)
        self._label_entry(form_card, "Versión TLAMATINI", self.var_app_version, row=7, col=0)

        tk.Label(form_card, text="Plan", font=("Arial", 10, "bold"), bg=PALETTE["panel"], fg=PALETTE["text"]).grid(row=7, column=1, sticky="w", padx=14)
        plan_combo = ttk.Combobox(form_card, textvariable=self.var_plan, values=["mensual", "trimestral", "anual"], state="readonly")
        plan_combo.grid(row=8, column=1, sticky="ew", padx=14, pady=(6, 10))
        plan_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_duration_from_plan())

        tk.Label(form_card, text="Duración", font=("Arial", 10, "bold"), bg=PALETTE["panel"], fg=PALETTE["text"]).grid(row=9, column=0, sticky="w", padx=14)
        duration_combo = ttk.Combobox(form_card, textvariable=self.var_duration_mode, values=["30", "90", "365", "personalizado"], state="readonly")
        duration_combo.grid(row=10, column=0, sticky="ew", padx=14, pady=(6, 10))
        duration_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_duration_entry_state())

        tk.Label(form_card, text="Días personalizados", font=("Arial", 10, "bold"), bg=PALETTE["panel"], fg=PALETTE["text"]).grid(row=9, column=1, sticky="w", padx=14)
        self.custom_duration_entry = tk.Entry(form_card, textvariable=self.var_duration_custom, font=("Arial", 11), bg="white", fg="#0f172a")
        self.custom_duration_entry.grid(row=10, column=1, sticky="ew", padx=14, pady=(6, 10))

        actions = tk.Frame(form_card, bg=PALETTE["panel"])
        actions.grid(row=10, column=3, sticky="e", padx=14, pady=(6, 10))
        tk.Button(actions, text="Generar licencia", command=self._generate_license, font=("Arial", 11, "bold"), bg=PALETTE["ok"], fg="white", relief="flat", padx=14, pady=8).pack(side="left")

        for column in range(4):
            form_card.grid_columnconfigure(column, weight=1)

        output_card = tk.Frame(wrapper, bg=PALETTE["panel"], highlightthickness=1, highlightbackground=PALETTE["border"])
        output_card.pack(fill="both", expand=True)
        tk.Label(output_card, text="Código de licencia generado", font=("Arial", 13, "bold"), bg=PALETTE["panel"], fg=PALETTE["text"]).pack(anchor="w", padx=14, pady=(14, 8))
        self.output_text = tk.Text(output_card, height=10, font=("Courier New", 10), wrap="word", bg="white", fg="#0f172a", relief="flat")
        self.output_text.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        output_actions = tk.Frame(output_card, bg=PALETTE["panel"])
        output_actions.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(output_actions, text="Copiar código", command=self._copy_output_code, font=("Arial", 11, "bold"), bg=PALETTE["accent"], fg="#00111d", relief="flat", padx=14, pady=8).pack(side="left")
        tk.Label(output_actions, text=f"Clave privada: {PRIVATE_KEY_PATH}", font=("Arial", 9), bg=PALETTE["panel"], fg=PALETTE["muted"]).pack(side="right")

        self._update_duration_entry_state()

    def _label_entry(self, parent, label: str, variable: tk.StringVar, *, row: int, col: int) -> None:
        tk.Label(parent, text=label, font=("Arial", 10, "bold"), bg=PALETTE["panel"], fg=PALETTE["text"]).grid(row=row, column=col, sticky="w", padx=14)
        tk.Entry(parent, textvariable=variable, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=row + 1, column=col, sticky="ew", padx=14, pady=(6, 10))

    def _schedule_parse_request(self, _event=None) -> None:
        if self._parse_after_id is not None:
            self.after_cancel(self._parse_after_id)
        self._parse_after_id = self.after(250, self._parse_request_text)

    def _parse_request_text(self) -> None:
        self._parse_after_id = None
        parsed = parse_license_request_text(self.request_text.get("1.0", "end"))
        if parsed["full_name"] and not self.var_full_name.get().strip():
            self.var_full_name.set(parsed["full_name"])
        if parsed["email"] and not self.var_email.get().strip():
            self.var_email.set(parsed["email"])
        if parsed["phone"] and not self.var_phone.get().strip():
            self.var_phone.set(parsed["phone"])
        if parsed["country"] and not self.var_country.get().strip():
            self.var_country.set(parsed["country"])
        if parsed["installation_id"]:
            self.var_installation_id.set(parsed["installation_id"])
        if parsed["os_name"]:
            self.var_os_name.set(parsed["os_name"])
        if parsed["app_version"]:
            self.var_app_version.set(parsed["app_version"])
        if parsed["requested_plan"]:
            requested_plan = parsed["requested_plan"].strip().lower()
            self.var_requested_plan.set(requested_plan)
            if requested_plan in {"mensual", "trimestral", "anual"}:
                self.var_plan.set(requested_plan)
                self._sync_duration_from_plan()

        if any(parsed.values()):
            installation = self.var_installation_id.get().strip() or "sin instalación detectada"
            self.var_status.set(f"Solicitud analizada. installation_id detectado: {installation}.")

    def _sync_duration_from_plan(self) -> None:
        self.var_duration_mode.set(str(infer_duration_days_from_plan(self.var_plan.get())))
        self.var_duration_custom.set("")
        self._update_duration_entry_state()

    def _update_duration_entry_state(self) -> None:
        is_custom = self.var_duration_mode.get() == "personalizado"
        self.custom_duration_entry.configure(state="normal" if is_custom else "disabled")
        if not is_custom:
            self.var_duration_custom.set("")

    def _resolved_duration_days(self) -> int:
        if self.var_duration_mode.get() == "personalizado":
            raw = self.var_duration_custom.get().strip()
            if not raw:
                raise ValueError("Escribe la duración personalizada en días.")
            return int(raw)
        return int(self.var_duration_mode.get())

    def _generate_license(self) -> None:
        self._parse_request_text()
        email = self.var_email.get().strip()
        if not email:
            raise_message = "No se encontró el email en la solicitud. Escríbelo manualmente antes de generar la licencia."
            self.var_status.set(raise_message)
            messagebox.showwarning("TLAMATINI", raise_message, parent=self)
            return

        installation_id = self.var_installation_id.get().strip()
        if not installation_id:
            confirmed = messagebox.askyesno(
                "TLAMATINI - Licencia sin vincular",
                "No se encontró installation_id. La licencia quedará no vinculada al equipo.\n\n¿Quieres continuar?",
                parent=self,
            )
            if not confirmed:
                return

        try:
            generated = generate_license_code(
                email=email,
                plan=self.var_plan.get().strip() or "mensual",
                duration_days=self._resolved_duration_days(),
                installation_id=installation_id or None,
                customer_name=self.var_full_name.get().strip() or None,
                customer_phone=self.var_phone.get().strip() or None,
                customer_country=self.var_country.get().strip() or None,
                features=list(DEFAULT_FEATURES),
            )
        except Exception as exc:
            self.var_status.set(str(exc))
            messagebox.showerror("TLAMATINI", str(exc), parent=self)
            return

        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", generated["license_code"])
        payload = generated["payload"]
        self.var_status.set(
            f"Licencia generada. Plan: {payload['plan']} | Vence: {payload['expires_at']} | "
            f"Instalación: {payload.get('installation_id', 'sin vincular')}"
        )

    def _copy_output_code(self) -> None:
        code = self.output_text.get("1.0", "end").strip()
        if not code:
            messagebox.showwarning("TLAMATINI", "No hay código generado para copiar.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(code)
        self.update_idletasks()
        self.var_status.set("El código de licencia se copió al portapapeles.")


def main() -> int:
    app = GeneradorLicenciasGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
