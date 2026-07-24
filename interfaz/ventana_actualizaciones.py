import threading
import tkinter as tk
from tkinter import messagebox

from core.local_license_store import (
    describe_backend_configuration,
    get_backend_mode,
    get_saved_backend_url,
    save_backend_mode,
    save_backend_url,
)
from core.update_checker import UpdateChecker
from core.update_client import (
    UpdateBackendNotConfiguredError,
    UpdateBackendUnavailableError,
    UpdateClientError,
    current_version,
    detect_platform,
)
from core.window_geometry import aplicar_geometria_relativa


PALETA = {
    "bg": "#071423",
    "panel": "#10243d",
    "panel_alt": "#132c49",
    "border": "#294866",
    "text": "#eef6ff",
    "text_dim": "#9db8d0",
    "accent": "#35d8ff",
    "ok": "#22c55e",
    "warn": "#f59e0b",
    "danger": "#ef4444",
    "soft": "#16314f",
    "info": "#2563eb",
}


class VentanaActualizaciones(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.checker = UpdateChecker()
        self.title("TLAMATINI - Actualizaciones")
        self.configure(bg=PALETA["bg"])
        self.minsize(860, 720)
        aplicar_geometria_relativa(self, master, rel_w=0.70, rel_h=0.82, min_w=880, min_h=740)

        self.var_backend_url = tk.StringVar(value=get_saved_backend_url())
        self.var_backend_mode = tk.StringVar(value=get_backend_mode())
        self.var_current_version = tk.StringVar(value=current_version())
        self.var_platform = tk.StringVar(value=detect_platform())
        self.var_channel = tk.StringVar(value="stable")
        self.var_status = tk.StringVar(value="Sin revisión reciente.")
        self.var_latest = tk.StringVar(value="Nueva versión: --")
        self.var_mandatory = tk.StringVar(value="Tipo: --")
        self.var_checked = tk.StringVar(value="Última revisión: --")
        self.var_download = tk.StringVar(value="Descarga: --")
        self.var_hash = tk.StringVar(value="SHA256: --")
        self.notes_text = None

        self._build_ui()
        self._refresh_view()

    def _build_ui(self):
        wrapper = tk.Frame(self, bg=PALETA["bg"])
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)

        header = tk.Frame(wrapper, bg=PALETA["bg"])
        header.pack(fill="x", pady=(0, 12))
        tk.Label(header, text="Actualizaciones", font=("Arial", 22, "bold"), bg=PALETA["bg"], fg=PALETA["text"]).pack(anchor="w")
        tk.Label(
            header,
            text="Consulta releases del backend, revisa cambios y descarga paquetes sin ejecución automática.",
            font=("Arial", 10),
            bg=PALETA["bg"],
            fg=PALETA["text_dim"],
        ).pack(anchor="w", pady=(6, 0))

        top = tk.Frame(wrapper, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["border"])
        top.pack(fill="x", pady=(0, 10))
        tk.Label(top, text="Backend de updates", font=("Arial", 13, "bold"), bg=PALETA["panel"], fg=PALETA["text"]).grid(row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(12, 4))
        tk.Label(top, text="URL backend", font=("Arial", 10), bg=PALETA["panel"], fg=PALETA["text_dim"]).grid(row=1, column=0, sticky="w", padx=14)
        tk.Entry(top, textvariable=self.var_backend_url, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=2, column=0, columnspan=3, sticky="ew", padx=(14, 8), pady=(2, 10))
        tk.Button(top, text="Guardar", font=("Arial", 10, "bold"), bg=PALETA["accent"], fg="#00111d", relief="flat", command=self._save_backend).grid(row=2, column=3, sticky="ew", padx=(0, 14), pady=(2, 10))
        tk.Label(top, text="Modo", font=("Arial", 10), bg=PALETA["panel"], fg=PALETA["text_dim"]).grid(row=3, column=0, sticky="w", padx=14)
        tk.OptionMenu(top, self.var_backend_mode, "hybrid", "remote-only", "dev-local").grid(row=3, column=1, sticky="w", padx=(8, 8), pady=(0, 10))

        tk.Label(top, text=f"Versión actual: {self.var_current_version.get()}", font=("Arial", 10), bg=PALETA["panel"], fg=PALETA["text"]).grid(row=4, column=0, sticky="w", padx=14, pady=(0, 10))
        tk.Label(top, text=f"Plataforma: {self.var_platform.get()}", font=("Arial", 10), bg=PALETA["panel"], fg=PALETA["text"]).grid(row=4, column=1, sticky="w", padx=8, pady=(0, 10))
        tk.Label(top, text="Canal", font=("Arial", 10), bg=PALETA["panel"], fg=PALETA["text_dim"]).grid(row=4, column=2, sticky="e", padx=8, pady=(0, 10))
        tk.Entry(top, textvariable=self.var_channel, font=("Arial", 10), bg="white", fg="#0f172a").grid(row=4, column=3, sticky="ew", padx=(0, 14), pady=(0, 10))
        for col in range(4):
            top.grid_columnconfigure(col, weight=1)

        summary = tk.Frame(wrapper, bg=PALETA["panel_alt"], highlightthickness=1, highlightbackground=PALETA["border"])
        summary.pack(fill="x", pady=(0, 10))
        tk.Label(summary, textvariable=self.var_status, font=("Arial", 12, "bold"), bg=PALETA["panel_alt"], fg=PALETA["accent"]).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 4))
        tk.Label(summary, textvariable=self.var_latest, font=("Arial", 10), bg=PALETA["panel_alt"], fg=PALETA["text"]).grid(row=1, column=0, sticky="w", padx=14, pady=2)
        tk.Label(summary, textvariable=self.var_mandatory, font=("Arial", 10), bg=PALETA["panel_alt"], fg=PALETA["text"]).grid(row=2, column=0, sticky="w", padx=14, pady=2)
        tk.Label(summary, textvariable=self.var_checked, font=("Arial", 10), bg=PALETA["panel_alt"], fg=PALETA["text"]).grid(row=3, column=0, sticky="w", padx=14, pady=2)
        tk.Label(summary, textvariable=self.var_download, font=("Arial", 10), bg=PALETA["panel_alt"], fg=PALETA["text"]).grid(row=4, column=0, sticky="w", padx=14, pady=2)
        tk.Label(summary, textvariable=self.var_hash, font=("Arial", 10), bg=PALETA["panel_alt"], fg=PALETA["text"]).grid(row=5, column=0, sticky="w", padx=14, pady=(2, 12))

        notes_panel = tk.Frame(wrapper, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["border"])
        notes_panel.pack(fill="both", expand=True, pady=(0, 10))
        tk.Label(notes_panel, text="Notas de versión", font=("Arial", 13, "bold"), bg=PALETA["panel"], fg=PALETA["text"]).pack(anchor="w", padx=14, pady=(12, 6))
        self.notes_text = tk.Text(notes_panel, height=18, bg="#091725", fg=PALETA["text"], insertbackground=PALETA["text"], relief="flat", wrap="word")
        self.notes_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.notes_text.configure(state="disabled")

        actions = tk.Frame(wrapper, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["border"])
        actions.pack(fill="x")
        tk.Button(actions, text="Buscar actualizaciones", font=("Arial", 10, "bold"), bg=PALETA["accent"], fg="#00111d", relief="flat", command=self._check_updates).grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=14)
        tk.Button(actions, text="Abrir URL de descarga", font=("Arial", 10, "bold"), bg=PALETA["info"], fg="white", relief="flat", command=self._open_download_url).grid(row=0, column=1, sticky="ew", padx=8, pady=14)
        tk.Button(actions, text="Descargar actualización", font=("Arial", 10, "bold"), bg=PALETA["ok"], fg="white", relief="flat", command=self._download_update).grid(row=0, column=2, sticky="ew", padx=8, pady=14)
        tk.Button(actions, text="Refrescar vista", font=("Arial", 10, "bold"), bg=PALETA["soft"], fg=PALETA["text"], relief="flat", command=self._refresh_view).grid(row=0, column=3, sticky="ew", padx=(8, 14), pady=14)
        for col in range(4):
            actions.grid_columnconfigure(col, weight=1)

    def _save_backend(self):
        try:
            save_backend_mode(self.var_backend_mode.get())
            save_backend_url(self.var_backend_url.get())
        except ValueError as exc:
            messagebox.showerror("Actualizaciones", str(exc), parent=self)
            return
        self._refresh_view()
        messagebox.showinfo("Actualizaciones", "Backend de updates guardado.", parent=self)

    def _run_task(self, action, success_message: str | None = None):
        def worker():
            succeeded = False
            try:
                action()
                succeeded = True
            except UpdateBackendNotConfiguredError as exc:
                self.after(0, lambda: messagebox.showwarning("Actualizaciones", str(exc), parent=self))
            except UpdateBackendUnavailableError as exc:
                self.after(0, lambda: messagebox.showwarning("Actualizaciones", str(exc), parent=self))
            except UpdateClientError as exc:
                self.after(0, lambda: messagebox.showerror("Actualizaciones", str(exc), parent=self))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Actualizaciones", f"Error inesperado: {exc}", parent=self))
            finally:
                self.after(0, self._refresh_view)
                if succeeded and success_message:
                    self.after(0, lambda: messagebox.showinfo("Actualizaciones", success_message, parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _check_updates(self):
        try:
            save_backend_mode(self.var_backend_mode.get())
            save_backend_url(self.var_backend_url.get())
        except ValueError as exc:
            messagebox.showerror("Actualizaciones", str(exc), parent=self)
            return
        channel = self.var_channel.get().strip() or "stable"
        self._run_task(lambda: self.checker.check_now(channel=channel), success_message="Revisión de actualizaciones completada.")

    def _open_download_url(self):
        try:
            save_backend_mode(self.var_backend_mode.get())
            save_backend_url(self.var_backend_url.get())
        except ValueError as exc:
            messagebox.showerror("Actualizaciones", str(exc), parent=self)
            return
        self._run_task(self.checker.open_latest_download_url, success_message="URL de descarga abierta en el navegador.")

    def _download_update(self):
        try:
            save_backend_mode(self.var_backend_mode.get())
            save_backend_url(self.var_backend_url.get())
        except ValueError as exc:
            messagebox.showerror("Actualizaciones", str(exc), parent=self)
            return
        self._run_task(self.checker.download_latest, success_message="Paquete descargado y validado por sha256.")

    def _refresh_view(self):
        state = self.checker.local_state()
        backend_cfg = describe_backend_configuration()
        self.var_backend_mode.set(backend_cfg.get("mode", "hybrid"))
        self.var_current_version.set(state.get("current_version") or current_version())
        self.var_platform.set(state.get("platform") or detect_platform())
        self.var_channel.set(state.get("channel") or "stable")
        self.var_checked.set(f"Última revisión: {state.get('last_checked_at') or '--'}")
        self.var_download.set(f"Descarga local: {state.get('downloaded_path') or '--'}")
        self.var_hash.set(f"SHA256: {state.get('sha256') or '--'}")

        if state.get("update_available"):
            latest = state.get("latest_version") or "--"
            self.var_status.set("Hay una actualización disponible.")
            self.var_latest.set(f"Nueva versión: {latest}")
            self.var_mandatory.set("Tipo: obligatoria" if state.get("is_mandatory") else "Tipo: opcional")
        elif state.get("last_error"):
            lowered = str(state.get("last_error", "")).lower()
            if "backend local de actualizaciones no está disponible" in lowered:
                self.var_status.set("No se pudo revisar actualizaciones.")
            elif "no hay backend configurado" in lowered or "solo se usa en modo desarrollo" in lowered:
                self.var_status.set("No hay una fuente de actualizaciones configurada.")
            else:
                self.var_status.set("No se pudo revisar actualizaciones.")
            self.var_latest.set("Nueva versión: --")
            detail = state.get("last_error")
            if backend_cfg.get("effective_url"):
                detail = f"{detail} | backend={backend_cfg.get('effective_url')}"
            self.var_mandatory.set(f"Detalle: {detail}")
        else:
            self.var_status.set("Tu versión está al día o aún no hay releases publicadas.")
            self.var_latest.set(f"Nueva versión: {state.get('latest_version') or '--'}")
            self.var_mandatory.set("Tipo: --")

        if self.notes_text is not None:
            self.notes_text.configure(state="normal")
            self.notes_text.delete("1.0", "end")
            notes = state.get("release_notes") or "Sin notas de versión disponibles."
            if state.get("title"):
                notes = f"{state['title']}\n\n{notes}"
            if state.get("min_supported_version"):
                notes += f"\n\nVersión mínima soportada: {state['min_supported_version']}"
            if state.get("signature"):
                notes += "\n\nLa release incluye campo de firma para validación futura."
            self.notes_text.insert("1.0", notes)
            self.notes_text.configure(state="disabled")
