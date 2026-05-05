import shutil
import socket
import subprocess
import threading
import tkinter as tk
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from time import monotonic
from tkinter import messagebox, ttk

from core.alert_actions import (
    acciones_para_alerta,
    activar_modo_emergencia,
    crear_recordatorio_desde_alerta,
    obtener_estado_modo_emergencia,
    registrar_accion_alerta,
)
from core.alert_ai_advisor import gemma_disponible, pedir_recomendacion_ia, recomendaciones_por_reglas
from core.alert_manager import limpiar_panel_alertas, listar_alertas_panel, resolver_alerta_panel, sincronizar_alertas_dashboard
from core.aprendizaje_offline import load_state as load_learning_state
from core.biblioteca_offline import load_state as load_library_state
from core.dashboard_config import cargar_config, obtener_modulos_ordenados, reordenar_modulos
from core.inventario import listar_alertas_inventario, listar_inventario
from core.license_client import BackendNotConfiguredError, BackendUnavailableError, LicenseClient, LicenseClientError
from core.license_enforcer import LicenseEnforcer
from core.logs import leer_logs, registrar_log
from core.mapas_repo import obtener_mapa_activo
from core.memoria import ESTRUCTURA_BASE, obtener_seccion
from core.modulos import limpiar_modulos, obtener_modulo, registrar_modulo
from core.perfiles import listar_personas
from core.planes import listar_planes
from core.resiliencia import estimar_agua_disponible_litros, estimar_reserva_agua, estimar_reserva_comida
from core.update_checker import UpdateChecker
from core.window_geometry import aplicar_geometria_relativa
from core.path_manager import PROJECT_ROOT, get_paths
from core.installation_identity import get_installation_payload
from core.license_request import build_manual_license_request
from core.user_profile import is_profile_complete, load_user_profile, save_user_profile
from interfaz.ventana_aprendizaje import VentanaAprendizaje
from interfaz.ventana_biblioteca import VentanaBiblioteca
from interfaz.ventana_configuracion import VentanaConfiguracion
from interfaz.ventana_consulta import VentanaConsulta
from interfaz.ventana_herramientas import (
    SONIDO_ALERTA_DEFAULT,
    SONIDOS_ALERTA,
    VentanaBlocNotas,
    VentanaComunicaciones,
    VentanaEnergia,
    cargar_alarmas,
    cargar_recordatorios,
    cargar_sonido_dashboard,
    etiqueta_repeticion,
    etiqueta_sonido_alerta,
    formatear_hora_ampm,
    formatear_hora_ampm_segundos,
    guardar_alarmas,
    guardar_recordatorios,
    guardar_sonido_dashboard,
    normalizar_sonido_alerta,
    obtener_ruta_sonido_alerta,
)
from interfaz.ventana_herramientas import VentanaHerramientas
from interfaz.ventana_inventario import VentanaCategoriaInventario, VentanaInventario
from interfaz.ventana_juegos import VentanaJuegos
from interfaz.ventana_licencia import VentanaLicencia
from interfaz.ventana_actualizaciones import VentanaActualizaciones
from interfaz.ventana_mapa_tactico import VentanaMapa as VentanaMapaTactico
from interfaz.ventana_perfiles import VentanaPerfiles
from interfaz.ventana_planes import VentanaPlanes


WORLD_MONITOR_URL_DEFAULT = "https://www.worldmonitor.app/?lat=20.0000&lon=0.0000&zoom=1.00&view=global&timeRange=7d&layers=conflicts%2Cbases%2Chotspots%2Cnuclear%2Csanctions%2Cweather%2Ceconomic%2Cwaterways%2Coutages%2Cmilitary%2Cnatural%2CiranAttacks"

def _configurar_cierre_toplevel(ventana):
    def _cerrar():
        try:
            if ventana.winfo_exists():
                ventana.destroy()
        except Exception as exc:
            registrar_log("warning", f"No se pudo cerrar la ventana {getattr(ventana, 'title', lambda: 'sin-titulo')()}: {exc}", "dashboard")

    try:
        ventana.protocol("WM_DELETE_WINDOW", _cerrar)
    except Exception as exc:
        registrar_log("warning", f"No se pudo asociar WM_DELETE_WINDOW: {exc}", "dashboard")
    return ventana


def _mostrar_encima(ventana, parent):
    try:
        ventana.lift()
        ventana.focus_force()
    except Exception as exc:
        registrar_log("warning", f"No se pudo enfocar/llevar al frente una ventana: {exc}", "dashboard")


def abrir_consulta(master_root, focus_parent=None):
    ventana = VentanaConsulta(master_root)
    _mostrar_encima(ventana, focus_parent or master_root)


def abrir_mapa(master_root, focus_parent=None):
    ventana = VentanaMapaTactico(master_root)
    _mostrar_encima(ventana, focus_parent or master_root)


def abrir_inventario(master_root, focus_parent=None):
    ventana = _configurar_cierre_toplevel(tk.Toplevel(master_root))
    _mostrar_encima(ventana, focus_parent or master_root)
    VentanaInventario(ventana)


def abrir_inventario_categoria(master_root, categoria_nombre, focus_parent=None):
    ventana = VentanaCategoriaInventario(master_root, categoria_nombre)
    _mostrar_encima(ventana.top, focus_parent or master_root)


def abrir_herramienta_energia(master_root, focus_parent=None):
    ventana = VentanaEnergia(master_root, focus_parent or master_root)
    _mostrar_encima(ventana.top, focus_parent or master_root)


def abrir_planes(master_root, focus_parent=None):
    ventana = _configurar_cierre_toplevel(tk.Toplevel(master_root))
    _mostrar_encima(ventana, focus_parent or master_root)
    VentanaPlanes(ventana)


def abrir_biblioteca(master_root, focus_parent=None):
    ventana = _configurar_cierre_toplevel(tk.Toplevel(master_root))
    _mostrar_encima(ventana, focus_parent or master_root)
    VentanaBiblioteca(ventana)


def abrir_aprendizaje(master_root, focus_parent=None):
    ventana = _configurar_cierre_toplevel(tk.Toplevel(master_root))
    _mostrar_encima(ventana, focus_parent or master_root)
    VentanaAprendizaje(ventana)


def abrir_codigos(master_root, focus_parent=None):
    from interfaz.ventana_codigos import VentanaCodigos

    ventana = VentanaCodigos(master_root)
    _mostrar_encima(ventana.root, focus_parent or master_root)


def abrir_perfiles(master_root, focus_parent=None):
    ventana = _configurar_cierre_toplevel(tk.Toplevel(master_root))
    _mostrar_encima(ventana, focus_parent or master_root)
    VentanaPerfiles(ventana)


def abrir_herramientas(master_root, focus_parent=None):
    ventana = VentanaHerramientas(master_root, focus_parent or master_root)
    _mostrar_encima(ventana, focus_parent or master_root)


def abrir_juegos(master_root, focus_parent=None):
    ventana = VentanaJuegos(master_root, focus_parent or master_root)
    _mostrar_encima(ventana, focus_parent or master_root)


def abrir_licencia(master_root, focus_parent=None, *, initial_view="auto"):
    ventana = VentanaLicencia(master_root, initial_view=initial_view)
    _mostrar_encima(ventana, focus_parent or master_root)


def abrir_actualizaciones(master_root, focus_parent=None):
    ventana = VentanaActualizaciones(master_root)
    _mostrar_encima(ventana, focus_parent or master_root)


def abrir_world_monitor(master_root, cfg=None, focus_parent=None):
    url = (cfg or {}).get("external_urls", {}).get("world_monitor") or WORLD_MONITOR_URL_DEFAULT
    try:
        registrar_log("dashboard", f"Abrir World Monitor: {url}", "world_monitor")
        webbrowser.open(url)
    except Exception as exc:
        registrar_log("error", f"Error al abrir World Monitor: {exc}", "world_monitor")
        messagebox.showerror(
            "World Monitor",
            f"No se pudo abrir la página de World Monitor.\n\nURL: {url}\n\nDetalle: {exc}",
            parent=focus_parent or master_root,
        )


def abrir_modulo_generico(master_root, titulo, focus_parent=None):
    ventana = _configurar_cierre_toplevel(tk.Toplevel(master_root))
    _mostrar_encima(ventana, focus_parent or master_root)
    ventana.title(titulo)
    aplicar_geometria_relativa(ventana, focus_parent or master_root, rel_w=0.58, rel_h=0.56, min_w=700, min_h=450)
    ventana.configure(bg="#111827")

    tk.Label(ventana, text=titulo, font=("Arial", 18, "bold"), bg="#111827", fg="white").pack(pady=20)
    tk.Label(
        ventana,
        text="Este módulo fue creado desde configuración.\nMás adelante podrá tener lógica propia.",
        font=("Arial", 12),
        bg="#111827",
        fg="#D1D5DB",
        justify="center",
    ).pack(pady=10)


def registrar_todos(master_root, cfg, focus_parent=None):
    limpiar_modulos()

    visuales = cfg.get("custom_modulos", {})
    color_default = cfg.get("tema", {}).get("modulo", "#1E293B")

    def datos(mid, titulo_def, icono_def):
        d = visuales.get(mid, {})
        return {
            "titulo": d.get("titulo") or titulo_def,
            "icono": d.get("icono") or icono_def,
            "color": d.get("color") or color_default,
        }

    d = datos("consulta", "Consulta", "🧠")
    registrar_modulo("consulta", d["titulo"], d["icono"], lambda: abrir_consulta(master_root, focus_parent), d["color"])

    d = datos("mapa", "Mapa", "🗺")
    registrar_modulo("mapa", d["titulo"], d["icono"], lambda: abrir_mapa(master_root, focus_parent), d["color"])

    d = datos("inventario", "Inventario", "📦")
    registrar_modulo("inventario", d["titulo"], d["icono"], lambda: abrir_inventario(master_root, focus_parent), d["color"])

    d = datos("planes_emergencia", "Planes de emergencia", "📋")
    registrar_modulo("planes_emergencia", d["titulo"], d["icono"], lambda: abrir_planes(master_root, focus_parent), d["color"])

    d = datos("biblioteca", "Biblioteca", "📚")
    registrar_modulo("biblioteca", d["titulo"], d["icono"], lambda: abrir_biblioteca(master_root, focus_parent), d["color"])

    d = datos("aprendizaje", "Aprendizaje", "🎓")
    registrar_modulo("aprendizaje", d["titulo"], d["icono"], lambda: abrir_aprendizaje(master_root, focus_parent), d["color"])

    d = datos("codigos", "Codigos", "🏷")
    registrar_modulo("codigos", d["titulo"], d["icono"], lambda: abrir_codigos(master_root, focus_parent), d["color"])

    d = datos("perfiles", "Perfiles", "👤")
    registrar_modulo("perfiles", d["titulo"], d["icono"], lambda: abrir_perfiles(master_root, focus_parent), d["color"])

    d = datos("herramientas", "Herramientas", "🛠")
    registrar_modulo("herramientas", d["titulo"], d["icono"], lambda: abrir_herramientas(master_root, focus_parent), d["color"])

    d = datos("juegos", "Juegos", "🎮")
    registrar_modulo("juegos", d["titulo"], d["icono"], lambda: abrir_juegos(master_root, focus_parent), d["color"])

    d = datos("world_monitor", "World Monitor", "🌍")
    registrar_modulo("world_monitor", d["titulo"], d["icono"], lambda: abrir_world_monitor(master_root, cfg, focus_parent), d["color"])

    for mod_cfg in cfg.get("modulos", []):
        mid = mod_cfg["id"]
        if mid in {
            "consulta",
            "mapa",
            "inventario",
            "planes_emergencia",
            "biblioteca",
            "aprendizaje",
            "codigos",
            "perfiles",
            "herramientas",
            "juegos",
            "world_monitor",
        }:
            continue
        d = datos(mid, mid, "🧩")
        registrar_modulo(
            mid,
            d["titulo"],
            d["icono"],
            lambda titulo=d["titulo"]: abrir_modulo_generico(master_root, titulo, focus_parent),
            d["color"],
            tipo="custom",
        )


class DashboardTLAMATINI:
    def __init__(self, root, app_root=None):
        self.root = root
        self.app_root = app_root or root
        self.logo_image = None
        self.window_icon = None
        self.root.title("TLAMATINI")
        self.root.protocol("WM_DELETE_WINDOW", self._cerrar_dashboard)
        aplicar_geometria_relativa(self.root, None, rel_w=0.95, rel_h=0.92, min_w=1420, min_h=900)
        self._aplicar_icono_ventana()

        self.config = cargar_config()
        self.reloj_job = None
        self.recordatorios_job = None
        self.sonido_dashboard_id = cargar_sonido_dashboard()
        self.alert_filter = "todas"
        self._is_rebuilding = False
        self._refresh_pending = False
        self._last_dashboard_refresh = 0.0
        self._wrap_jobs = []
        self._wrap_refresh_job = None
        self._focus_refresh_job = None
        self._audio_preview_process = None
        self._audio_preview_lock = threading.Lock()
        self._gemma_available = False
        self._gemma_status = "No verificado"
        self._license_details_visible = False
        self._module_drag = {"active": False, "source": "", "target": "", "moved": False}
        self._module_card_refs = {}
        profile = load_user_profile()
        self.var_profile_name = tk.StringVar(value=str(profile.get("full_name", "")).strip())
        self.var_profile_email = tk.StringVar(value=str(profile.get("email", "")).strip())
        self.var_profile_phone = tk.StringVar(value=str(profile.get("phone", "")).strip())
        self.var_profile_country = tk.StringVar(value=str(profile.get("country", "")).strip())
        self.status_left = None
        self.status_right = None
        self.license_client = LicenseClient()
        self.license_enforcer = LicenseEnforcer()
        self.update_checker = UpdateChecker()
        self.ui = {
            "bg": "#06101c",
            "bg_alt": "#081827",
            "sidebar": "#040b14",
            "sidebar_active": "#0d1f33",
            "surface": "#0b1629",
            "surface_alt": "#0f1d33",
            "surface_soft": "#14243d",
            "border": "#18334f",
            "border_soft": "#21425f",
            "text": "#edf6ff",
            "text_dim": "#8ba6bf",
            "accent": "#35d8ff",
            "success": "#22c55e",
            "warning": "#f59e0b",
            "danger": "#ef4444",
            "info": "#3b82f6",
            "muted": "#1b2d46",
            "footer": "#040c16",
        }
        registrar_todos(self.app_root, self.config, self.root)
        self._module_meta = self._build_module_meta()
        self._gemma_available, self._gemma_status = gemma_disponible()
        self.content_inner = None
        self.primary_view = None
        self.alerts_row = None
        self.cards_row = None
        self.modules_row = None
        self.grid_panels = None
        self.license_info_row = None
        self.label_fecha = None
        self.label_hora = None
        try:
            self.crear_ui()
        except Exception as exc:
            registrar_log("error", f"Fallo al construir dashboard: {exc}", "dashboard")
            self._crear_fallback_error_ui(exc)
        self.root.bind("<FocusIn>", self._al_recuperar_foco)
        self.root.after(1800, self._check_updates_soft_startup)

    def _aplicar_icono_ventana(self):
        icon_path = PROJECT_ROOT / "assets" / "app_icon.png"
        if not icon_path.exists():
            return
        try:
            self.window_icon = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self.window_icon)
        except Exception as exc:
            registrar_log("warning", f"No se pudo aplicar icono TLAMATINI: {exc}", "dashboard")

    def _build_module_meta(self):
        meta = {}
        for mod_cfg in obtener_modulos_ordenados(self.config):
            mod = obtener_modulo(mod_cfg["id"])
            if not mod:
                continue
            meta[mod_cfg["id"]] = mod
        return meta

    def crear_ui(self):
        self.root.configure(bg=self.ui["bg"])
        wrapper = tk.Frame(self.root, bg=self.ui["bg"])
        wrapper.pack(fill="both", expand=True)
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)

        main_shell = tk.Frame(wrapper, bg=self.ui["bg"])
        main_shell.grid(row=0, column=0, sticky="nsew")
        main_shell.grid_columnconfigure(0, weight=1)
        main_shell.grid_rowconfigure(1, weight=1)
        main_shell.grid_rowconfigure(2, weight=0)

        self.main = tk.Frame(main_shell, bg=self.ui["bg"])
        self.main.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        self._crear_contenido_principal()
        self._crear_barra_inferior(main_shell)
        self.actualizar_hora()
        self._programar_revision_recordatorios()

    def _crear_contenido_principal(self):
        canvas = tk.Canvas(self.main, bg=self.ui["bg"], highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(self.main, orient="vertical", command=canvas.yview)
        self.content_inner = tk.Frame(canvas, bg=self.ui["bg"])

        self.content_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        content_window = canvas.create_window((0, 0), window=self.content_inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(content_window, width=e.width))
        self._bind_mousewheel(self.content_inner, canvas)
        self.primary_view = tk.Frame(self.content_inner, bg=self.ui["bg"])
        self.primary_view.pack(fill="both", expand=True)
        self._reconstruir_dashboard()

    def _build_dashboard_layout(self):
        self.alerts_row = None
        self.cards_row = None
        self.modules_row = None
        self.grid_panels = None
        self.license_info_row = None

        header = tk.Frame(self.primary_view, bg=self.ui["bg"])
        header.pack(fill="x", padx=22, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        header.grid_columnconfigure(2, weight=0)

        title_wrap = tk.Frame(header, bg=self.ui["bg"])
        title_wrap.grid(row=0, column=0, sticky="w")
        top_line = tk.Frame(title_wrap, bg=self.ui["bg"])
        top_line.pack(anchor="w")
        logo = self._crear_logo_header(top_line)
        if logo is not None:
            logo.pack(side="left", padx=(0, 14))
        title_stack = tk.Frame(top_line, bg=self.ui["bg"])
        title_stack.pack(side="left")
        tk.Label(title_stack, text="TLAMATINI", font=("Arial", 25, "bold"), bg=self.ui["bg"], fg=self.ui["text"]).pack(anchor="w")
        tk.Label(title_stack, text="Centro de Control", font=("Arial", 11, "bold"), bg=self.ui["bg"], fg=self.ui["accent"]).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(header, bg=self.ui["bg"])
        right.grid(row=0, column=2, sticky="e")
        self.label_fecha = tk.Label(right, text="Fecha", font=("Arial", 10, "bold"), bg=self.ui["bg"], fg=self.ui["text"])
        self.label_fecha.grid(row=0, column=0, sticky="e")
        self.label_hora = tk.Label(right, text="Hora", font=("Arial", 14, "bold"), bg=self.ui["bg"], fg=self.ui["accent"])
        self.label_hora.grid(row=1, column=0, sticky="e", pady=(4, 0))
        tools = tk.Frame(right, bg=self.ui["bg"])
        tools.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))
        cfg_btn = self._icon_button(tools, "⚙", lambda: None)
        cfg_btn.pack(side="left", padx=4)
        self._bind_double_click_action(cfg_btn, lambda: VentanaConfiguracion(self.root, on_change=self._recargar_dashboard))

        self.alerts_row = tk.Frame(self.primary_view, bg=self.ui["bg"])
        self.alerts_row.pack(fill="x", padx=22, pady=(0, 10))

        self.cards_row = tk.Frame(self.primary_view, bg=self.ui["bg"])
        self.cards_row.pack(fill="x", padx=22, pady=(0, 8))

        modules_header = tk.Frame(self.primary_view, bg=self.ui["bg"])
        modules_header.pack(fill="x", padx=22, pady=(0, 6))
        tk.Label(modules_header, text="Módulos", font=("Arial", 15, "bold"), bg=self.ui["bg"], fg=self.ui["text"]).pack(anchor="w")

        self.modules_row = tk.Frame(self.primary_view, bg=self.ui["bg"])
        self.modules_row.pack(fill="x", padx=22, pady=(0, 12))

        self.grid_panels = tk.Frame(self.primary_view, bg=self.ui["bg"])
        self.grid_panels.pack(fill="x", padx=22, pady=(0, 12))
        for col in range(3):
            self.grid_panels.grid_columnconfigure(col, weight=1, uniform="dash")

        self.license_info_row = tk.Frame(self.primary_view, bg=self.ui["bg"])
        self.license_info_row.pack(fill="x", padx=22, pady=(0, 18))

    def _crear_logo_header(self, parent):
        logo_path = PROJECT_ROOT / "assets" / "logo_tlamatini.png"
        if not logo_path.exists():
            return None
        try:
            from PIL import Image, ImageTk

            image = Image.open(logo_path).convert("RGBA").resize((62, 62), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(image)
            return tk.Label(parent, image=self.logo_image, bg=self.ui["bg"], bd=0)
        except Exception as exc:
            registrar_log("warning", f"No se pudo cargar logo TLAMATINI: {exc}", "dashboard")
            return None

    def _clear_primary_view(self):
        if self.primary_view is None:
            return
        for widget in self.primary_view.winfo_children():
            widget.destroy()
        self.alerts_row = None
        self.cards_row = None
        self.modules_row = None
        self.grid_panels = None
        self.license_info_row = None

    def _crear_barra_inferior(self, parent):
        self.status_bar = tk.Frame(parent, bg=self.ui["footer"], height=42, highlightthickness=1, highlightbackground=self.ui["border"])
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_bar.grid_propagate(False)

        self.status_left = tk.Frame(self.status_bar, bg=self.ui["footer"])
        self.status_left.pack(side="left", fill="x", expand=True, padx=18)
        self.status_right = tk.Frame(self.status_bar, bg=self.ui["footer"])
        self.status_right.pack(side="right", padx=18)
        self._render_status_bar()

    def _render_status_bar(self):
        self._render_status_bar_with_status(self._collect_dashboard_data())

    def _render_status_bar_with_status(self, status):
        if self.status_left is None or self.status_right is None:
            return
        try:
            if not self.status_left.winfo_exists() or not self.status_right.winfo_exists():
                return
        except Exception:
            return
        for widget in self.status_left.winfo_children():
            widget.destroy()
        for widget in self.status_right.winfo_children():
            widget.destroy()

        if not self._can_access_with_status(status):
            tk.Label(
                self.status_left,
                text=self._current_version_label(),
                font=("Arial", 9),
                bg=self.ui["footer"],
                fg=self.ui["text_dim"],
            ).pack(side="left", padx=(0, 12), pady=6)
            return

        license_status = self._license_status_summary()
        update_status = self.update_checker.status_summary()
        tk.Label(
            self.status_left,
            text=license_status["text"],
            font=("Arial", 9, "bold"),
            bg=self.ui["footer"],
            fg=license_status["color"],
        ).pack(side="left", padx=(0, 12), pady=6)
        tk.Label(
            self.status_left,
            text=self._current_version_label(),
            font=("Arial", 9),
            bg=self.ui["footer"],
            fg=self.ui["text_dim"],
        ).pack(side="left", padx=(0, 12), pady=6)
        tk.Label(
            self.status_left,
            text=str(update_status.get("text", "Actualizaciones al día")),
            font=("Arial", 9, "bold"),
            bg=self.ui["footer"],
            fg=self.ui["warning"] if update_status.get("mandatory") else (self.ui["info"] if update_status.get("available") else self.ui["text_dim"]),
        ).pack(side="left", padx=(0, 12), pady=6)
        tk.Button(
            self.status_left,
            text="Licencia",
            font=("Arial", 10, "bold"),
            bg=self.ui["surface_alt"],
            fg=self.ui["text"],
            activebackground=self.ui["surface_soft"],
            activeforeground=self.ui["text"],
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            command=lambda: abrir_licencia(self.app_root, self.root),
        ).pack(side="left", pady=6)
        tk.Button(
            self.status_left,
            text="Actualizaciones",
            font=("Arial", 10, "bold"),
            bg=self.ui["surface_alt"],
            fg=self.ui["text"],
            activebackground=self.ui["surface_soft"],
            activeforeground=self.ui["text"],
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            command=lambda: abrir_actualizaciones(self.app_root, self.root),
        ).pack(side="left", pady=6)

        tk.Button(
            self.status_right,
            text="Sincronizar datos",
            font=("Arial", 10, "bold"),
            bg=self.ui["accent"],
            fg="#00111d",
            activebackground="#77e8ff",
            activeforeground="#00111d",
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            command=self._sincronizar_datos,
        ).pack(pady=6)

    def _can_access_with_status(self, status):
        license_status = self._safe_dict(status.get("license_status", {}))
        state = str(license_status.get("state", "")).strip().lower()
        return state in {"valid", "grace"}

    def _can_access_app(self):
        return self._can_access_with_status({"license_status": self.license_enforcer.current_status()})

    def _access_gate_state(self, status):
        license_status = self._safe_dict(status.get("license_status", {}))
        profile_ready = is_profile_complete(self._user_profile())
        if not profile_ready:
            return "profile_form"
        if license_status.get("trial_expired"):
            return "trial_expired"
        state = str(license_status.get("state", "")).strip().lower()
        if state in {"valid", "grace"}:
            plan = str(license_status.get("plan", "")).strip().lower()
            return "trial_active" if plan == "trial" else "license_active"
        return "choose_path"

    def _license_status_summary(self):
        try:
            estado = self.license_client.local_status()
        except Exception as exc:
            return {"text": f"Licencia local no disponible: {exc}", "color": self.ui["warning"]}

        state = str(estado.get("state", "missing")).strip().lower()
        backend_configured = bool(estado.get("backend_configured", False))
        backend_blocked = str(estado.get("backend_blocked_reason", "")).strip()
        plan = str(estado.get("plan", "")).strip().lower()
        if state in {"valid", "grace"} and plan == "trial":
            return {
                "text": f"Prueba activa · vence {estado.get('expires_at') or '--'}",
                "color": self.ui["success"],
            }
        if estado.get("trial_expired"):
            return {
                "text": "Prueba gratuita ya utilizada · solicita licencia mensual o pega tu código",
                "color": self.ui["warning"],
            }
        text_map = {
            "valid": f"Licencia válida · {estado.get('plan') or 'plan'} · vence {estado.get('expires_at') or '--'}",
            "grace": f"Licencia en gracia · hasta {estado.get('grace_until') or '--'}",
            "expired": "Licencia vencida · acceso SaaS restringido",
            "invalid": "Licencia inválida · revisa clave pública o sincronización",
            "missing": "Sin licencia local · puedes iniciar prueba o solicitar activación manual",
        }
        color_map = {
            "valid": self.ui["success"],
            "grace": self.ui["warning"],
            "expired": self.ui["danger"],
            "invalid": self.ui["danger"],
            "missing": self.ui["text_dim"],
        }
        if state in {"valid", "grace"} and not backend_configured:
            return {
                "text": f"Licencia local activa · modo offline listo · {estado.get('plan') or 'plan'}",
                "color": self.ui["success"] if state == "valid" else self.ui["warning"],
            }
        if backend_blocked:
            return {"text": backend_blocked, "color": self.ui["warning"]}
        return {"text": text_map.get(state, "Estado de licencia desconocido"), "color": color_map.get(state, self.ui["text_dim"])}

    def _bind_double_click_action(self, widget, action):
        widget.bind("<Double-Button-1>", lambda _event: action())

    def _abrir_modulo_dashboard(self, module_id):
        if not self._permitir_acceso_modulo(module_id):
            return
        mod = self._module_meta.get(module_id)
        if mod and callable(mod.get("funcion")):
            mod["funcion"]()

    def _permitir_acceso_modulo(self, module_id, titulo: str | None = None):
        nombre = titulo or str(module_id or "").replace("_", " ").title()
        if self.license_enforcer.can_access_module(module_id):
            return True
        self._mostrar_bloqueo_licencia(nombre, self.license_enforcer.block_reason_for(nombre))
        return False

    def _mostrar_bloqueo_licencia(self, titulo_modulo, motivo):
        ventana = tk.Toplevel(self.root)
        ventana.title("Acceso bloqueado por licencia")
        aplicar_geometria_relativa(ventana, self.root, rel_w=0.34, rel_h=0.30, min_w=460, min_h=260)
        ventana.configure(bg=self.ui["surface"])

        tk.Label(
            ventana,
            text="Licencia requerida",
            font=("Arial", 18, "bold"),
            bg=self.ui["surface"],
            fg=self.ui["danger"],
        ).pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(
            ventana,
            text=f"Módulo: {titulo_modulo}",
            font=("Arial", 11, "bold"),
            bg=self.ui["surface"],
            fg=self.ui["text"],
        ).pack(anchor="w", padx=16)
        tk.Label(
            ventana,
            text=motivo,
            font=("Arial", 10),
            bg=self.ui["surface"],
            fg=self.ui["text_dim"],
            justify="left",
            wraplength=420,
        ).pack(anchor="w", padx=16, pady=(8, 12))

        acciones = tk.Frame(ventana, bg=self.ui["surface"])
        acciones.pack(fill="x", padx=16, pady=(0, 16))

        def _sync():
            try:
                if self.license_client.is_authenticated():
                    self.license_client.sync_license()
                    self._reconstruir_dashboard()
                    messagebox.showinfo("Licencia", "Licencia sincronizada.", parent=ventana)
                else:
                    abrir_licencia(self.app_root, self.root)
            except (BackendNotConfiguredError, BackendUnavailableError) as exc:
                messagebox.showwarning("Licencia", str(exc), parent=ventana)
            except Exception as exc:
                messagebox.showerror("Licencia", f"No se pudo sincronizar: {exc}", parent=ventana)

        def _pay():
            try:
                if self.license_client.is_authenticated():
                    self.license_client.open_checkout()
                else:
                    abrir_licencia(self.app_root, self.root)
            except Exception as exc:
                messagebox.showerror("Licencia", f"No se pudo abrir el checkout: {exc}", parent=ventana)

        tk.Button(
            acciones,
            text="Sincronizar",
            font=("Arial", 10, "bold"),
            bg=self.ui["accent"],
            fg="#00111d",
            relief="flat",
            command=_sync,
        ).pack(side="left")
        tk.Button(
            acciones,
            text="Solicitar licencia mensual",
            font=("Arial", 10, "bold"),
            bg=self.ui["info"],
            fg="white",
            relief="flat",
            command=_pay,
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            acciones,
            text="Ver licencia",
            font=("Arial", 10),
            bg=self.ui["surface_alt"],
            fg=self.ui["text"],
            relief="flat",
            command=lambda: abrir_licencia(self.app_root, self.root),
        ).pack(side="left", padx=(8, 0))

    def _reset_module_drag_visuals(self):
        for card in self._module_card_refs.values():
            try:
                if card.winfo_exists():
                    card.configure(highlightbackground=self.ui["border"], highlightthickness=1)
            except Exception:
                pass

    def _start_module_drag(self, module_id):
        self._module_drag = {"active": True, "source": module_id, "target": module_id, "moved": False}
        self._reset_module_drag_visuals()
        card = self._module_card_refs.get(module_id)
        if card is not None:
            try:
                card.configure(highlightbackground=self.ui["accent"], highlightthickness=2)
            except Exception:
                pass

    def _track_module_drag(self, event):
        if not self._module_drag.get("active"):
            return
        self._module_drag["moved"] = True
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        while widget is not None and not hasattr(widget, "module_id"):
            try:
                widget = widget.master
            except Exception:
                widget = None
        target = getattr(widget, "module_id", "") if widget is not None else ""
        if not target:
            return
        self._module_drag["target"] = target
        self._reset_module_drag_visuals()
        for module_id in {self._module_drag.get("source", ""), target}:
            card = self._module_card_refs.get(module_id)
            if card is None:
                continue
            try:
                color = self.ui["accent"] if module_id == target else "#77e8ff"
                card.configure(highlightbackground=color, highlightthickness=2)
            except Exception:
                pass

    def _finish_module_drag(self, module_id):
        if not self._module_drag.get("active"):
            return
        source = self._module_drag.get("source", "")
        target = self._module_drag.get("target") or module_id
        moved = bool(self._module_drag.get("moved"))
        self._module_drag = {"active": False, "source": "", "target": "", "moved": False}
        self._reset_module_drag_visuals()
        if not moved or not source or not target or source == target:
            return
        self.config = reordenar_modulos(self.config, source, target)
        self._module_meta = self._build_module_meta()
        registrar_log("dashboard", f"Módulo reordenado: {source} -> {target}", "dashboard")
        self._reconstruir_dashboard()

    def _render_module_cards(self):
        for widget in self.modules_row.winfo_children():
            widget.destroy()
        self._module_card_refs = {}

        module_order = [mod["id"] for mod in obtener_modulos_ordenados(self.config)]
        if obtener_estado_modo_emergencia().get("activo"):
            prioridad = [
                "inventario",
                "mapa",
                "planes_emergencia",
                "perfiles",
                "herramientas",
                "biblioteca",
                "aprendizaje",
                "consulta",
            ]
            prioridades = {mid: idx for idx, mid in enumerate(prioridad)}
            module_order = sorted(module_order, key=lambda mid: (prioridades.get(mid, 999), module_order.index(mid)))
        columnas = 4
        for col in range(columnas):
            self.modules_row.grid_columnconfigure(col, weight=1, uniform="module_cards")

        for idx, module_id in enumerate(module_order):
            data = self._module_meta.get(module_id, {})
            titulo = data.get("titulo") or module_id.replace("_", " ").title()
            icono = data.get("icono", "🧩")
            color = data.get("color") or self.ui["surface_soft"]
            row = idx // columnas
            col = idx % columnas

            card = tk.Frame(
                self.modules_row,
                bg=self.ui["surface"],
                height=154,
                highlightthickness=1,
                highlightbackground=self.ui["border"],
                cursor="hand2",
            )
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(0, weight=1)
            card.module_id = module_id
            self._module_card_refs[module_id] = card

            inner = tk.Frame(card, bg=self.ui["surface"])
            inner.grid(row=0, column=0, sticky="nsew")
            inner.grid_columnconfigure(0, weight=1)
            inner.module_id = module_id

            icon_wrap = tk.Frame(inner, bg=self.ui["surface"])
            icon_wrap.pack(anchor="center", pady=(16, 8))
            icon_wrap.module_id = module_id

            icon_badge = tk.Frame(
                icon_wrap,
                bg=color,
                width=58,
                height=58,
                highlightthickness=1,
                highlightbackground="#dbeafe",
            )
            icon_badge.pack()
            icon_badge.pack_propagate(False)
            icon_badge.module_id = module_id

            icon_label = tk.Label(
                icon_badge,
                text=icono,
                font=("Arial", 26),
                bg=color,
                fg="#f8fbff",
            )
            icon_label.pack(expand=True)
            icon_label.module_id = module_id

            title_label = tk.Label(
                inner,
                text=titulo,
                font=("Arial", 11, "bold"),
                bg=self.ui["surface"],
                fg=self.ui["text"],
                justify="center",
                wraplength=170,
            )
            title_label.pack(fill="x", padx=12)
            title_label.module_id = module_id
            self._bind_wrap_to_parent(title_label, card, pad=30, min_width=110)

            for widget in (card, inner, icon_wrap, icon_badge, icon_label, title_label):
                self._bind_double_click_action(widget, lambda mid=module_id: self._abrir_modulo_dashboard(mid))
                widget.bind("<ButtonPress-1>", lambda _event, mid=module_id: self._start_module_drag(mid))
                widget.bind("<B1-Motion>", self._track_module_drag)
                widget.bind("<ButtonRelease-1>", lambda _event, mid=module_id: self._finish_module_drag(mid))

    def _alert_level(self, alerta):
        nivel = str(alerta.get("nivel", alerta.get("prioridad", ""))).lower()
        prioridad = str(alerta.get("prioridad", "")).lower()
        if nivel in {"critico", "critica", "crítico", "alta"} or prioridad in {"alta", "critica", "crítica"}:
            return {"label": "CRÍTICO", "color": self.ui["danger"], "bg": "#3a1318", "icon": "⛔"}
        if nivel in {"advertencia", "media", "warning"} or prioridad in {"media", "warning"}:
            return {"label": "ADVERTENCIA", "color": self.ui["warning"], "bg": "#3b2608", "icon": "⚠"}
        return {"label": "INFO", "color": self.ui["info"], "bg": "#102744", "icon": "ℹ"}

    def _set_alert_filter(self, filtro):
        self.alert_filter = filtro
        self._reconstruir_dashboard()

    def _limpiar_panel_alertas_dashboard(self):
        total = limpiar_panel_alertas()
        if total:
            self._reconstruir_dashboard()

    def _respuesta_alerta(self, alerta):
        reglas = recomendaciones_por_reglas(alerta)
        acciones = acciones_para_alerta(alerta, gemma_ok=self._gemma_available)
        return {
            "summary": str(reglas.get("summary", "")).strip(),
            "suggestions": list(reglas.get("suggestions", []) or []),
            "steps": list(reglas.get("steps", []) or []),
            "actions": acciones,
        }

    def _color_accion_alerta(self, action_id):
        if action_id in {"activar_modo_emergencia"}:
            return ("#7f1d1d", "#fee2e2")
        if action_id in {"pedir_ia"}:
            return (self.ui["accent"], "#00111d")
        if action_id in {"crear_recordatorio", "crear_registro"}:
            return ("#0f766e", "white")
        return (self.ui["muted"], self.ui["text"])

    def _abrir_logs_alerta(self, alerta):
        ventana = tk.Toplevel(self.root)
        ventana.title("Logs de alerta")
        aplicar_geometria_relativa(ventana, self.root, rel_w=0.52, rel_h=0.52, min_w=680, min_h=460)
        ventana.configure(bg=self.ui["surface"])
        tk.Label(ventana, text=str(alerta.get("titulo", "Logs de alerta")), font=("Arial", 15, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=16, pady=(16, 8))
        caja = tk.Text(ventana, bg=self.ui["bg_alt"], fg=self.ui["text"], insertbackground=self.ui["text"], relief="flat", wrap="word")
        caja.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        origen = normalizar_texto(alerta.get("origen", ""))
        referencia = str(alerta.get("referencia", "")).strip().lower()
        lineas = []
        for log in reversed(self._safe_list(leer_logs())[-120:]):
            modulo = normalizar_texto(log.get("modulo", ""))
            mensaje = str(log.get("mensaje", "")).strip()
            if origen and modulo != origen and origen not in mensaje.lower():
                continue
            if referencia and referencia not in mensaje.lower():
                continue
            lineas.append(f"[{log.get('fecha', '--')} {log.get('hora', '--:--:--')}] [{str(log.get('tipo', '')).upper()}] [{str(log.get('modulo', '')).upper()}] {mensaje}")
        if not lineas:
            lineas = ["No hay logs específicos que coincidan con esta alerta."]
        caja.insert("1.0", "\n".join(lineas[:80]))
        caja.configure(state="disabled")

    def _mostrar_respuesta_ia(self, alerta):
        ventana = tk.Toplevel(self.root)
        ventana.title("Recomendación IA")
        aplicar_geometria_relativa(ventana, self.root, rel_w=0.52, rel_h=0.56, min_w=700, min_h=520)
        ventana.configure(bg=self.ui["surface"])
        tk.Label(ventana, text=f"IA local · {alerta.get('titulo', 'Alerta')}", font=("Arial", 15, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=16, pady=(16, 8))
        estado = tk.Label(ventana, text="Consultando Gemma local...", font=("Arial", 10), bg=self.ui["surface"], fg=self.ui["text_dim"])
        estado.pack(anchor="w", padx=16, pady=(0, 8))
        caja = tk.Text(ventana, bg=self.ui["bg_alt"], fg=self.ui["text"], insertbackground=self.ui["text"], relief="flat", wrap="word")
        caja.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        def _worker():
            respuesta = pedir_recomendacion_ia(alerta)

            def _render():
                if not ventana.winfo_exists():
                    return
                caja.configure(state="normal")
                caja.delete("1.0", "end")
                if respuesta.get("ok"):
                    estado.config(text=f"Fuente: {respuesta.get('source', 'gemma')}", fg=self.ui["success"])
                    caja.insert("1.0", str(respuesta.get("texto", "")).strip())
                    registrar_accion_alerta(alerta, "pedir_ia", "Respuesta IA generada")
                else:
                    estado.config(text=f"Gemma no disponible: {respuesta.get('detalle', self._gemma_status)}", fg=self.ui["warning"])
                    reglas = self._respuesta_alerta(alerta)
                    texto = [reglas["summary"], "", "Sugerencias por reglas locales:"]
                    texto.extend(f"- {linea}" for linea in reglas["suggestions"])
                    texto.append("")
                    texto.append("Pasos sugeridos:")
                    texto.extend(f"- {linea}" for linea in reglas["steps"])
                    caja.insert("1.0", "\n".join(texto).strip())
                caja.configure(state="disabled")

            self.root.after(0, _render)

        threading.Thread(target=_worker, daemon=True).start()

    def _ejecutar_accion_alerta(self, alerta, action_id):
        titulo = str(alerta.get("titulo", "Alerta")).strip() or "Alerta"
        if action_id == "pedir_ia":
            if not self._permitir_acceso_modulo("ia", "IA local"):
                return
            self._mostrar_respuesta_ia(alerta)
            return
        accion = next((a for a in self._respuesta_alerta(alerta)["actions"] if a.get("id") == action_id), None)
        mensaje_confirm = str((accion or {}).get("confirm", "")).strip()
        if mensaje_confirm and not messagebox.askyesno("Confirmar acción", mensaje_confirm, parent=self.root):
            return

        if action_id == "inventario_agua":
            abrir_inventario_categoria(self.app_root, "Alimentos", self.root)
        elif action_id == "inventario_comida":
            abrir_inventario_categoria(self.app_root, "Alimentos", self.root)
        elif action_id == "inventario_medico":
            abrir_inventario_categoria(self.app_root, "Insumos medicos", self.root)
        elif action_id == "inventario_energia":
            abrir_inventario_categoria(self.app_root, "Energia", self.root)
        elif action_id == "abrir_inventario":
            abrir_inventario(self.app_root, self.root)
        elif action_id == "abrir_mapa":
            if not self._permitir_acceso_modulo("mapa", "Mapa"):
                return
            abrir_mapa(self.app_root, self.root)
        elif action_id == "abrir_planes":
            abrir_planes(self.app_root, self.root)
        elif action_id == "abrir_biblioteca":
            if not self._permitir_acceso_modulo("biblioteca", "Biblioteca"):
                return
            abrir_biblioteca(self.app_root, self.root)
        elif action_id == "abrir_aprendizaje":
            if not self._permitir_acceso_modulo("aprendizaje", "Aprendizaje"):
                return
            abrir_aprendizaje(self.app_root, self.root)
        elif action_id == "abrir_perfiles":
            abrir_perfiles(self.app_root, self.root)
        elif action_id == "herramienta_energia":
            abrir_herramienta_energia(self.app_root, self.root)
        elif action_id == "crear_recordatorio":
            crear_recordatorio_desde_alerta(titulo, str(alerta.get("descripcion", "")).strip())
        elif action_id == "crear_registro":
            registrar_accion_alerta(alerta, "registro_manual", str(alerta.get("descripcion", "")).strip())
        elif action_id == "reintentar_dashboard":
            self._reconstruir_dashboard()
        elif action_id == "ver_logs":
            self._abrir_logs_alerta(alerta)
        elif action_id == "activar_modo_emergencia":
            activar_modo_emergencia(str(alerta.get("origen", "alertas")), str(alerta.get("descripcion", "")).strip())
            self._reconstruir_dashboard()
        else:
            registrar_accion_alerta(alerta, action_id)
            return

        registrar_accion_alerta(alerta, action_id)
        self._reconstruir_dashboard()

    def _render_alert_row(self, parent, alerta, compact=False):
        respuesta = self._respuesta_alerta(alerta)
        severidad = self._alert_level(alerta)
        row = tk.Frame(parent, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=severidad["color"])
        row.pack(fill="x", pady=4)
        top = tk.Frame(row, bg=self.ui["surface_alt"])
        top.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(top, text=severidad["icon"], font=("Arial", 13), bg=self.ui["surface_alt"], fg=severidad["color"]).pack(side="left")
        tk.Label(top, text=str(alerta.get("titulo", "Alerta")), font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(side="left", padx=(8, 0))
        tk.Label(top, text=severidad["label"], font=("Arial", 8, "bold"), bg=severidad["bg"], fg=severidad["color"], padx=8, pady=3).pack(side="right")
        descripcion = tk.Label(
            row,
            text=str(alerta.get("descripcion", alerta.get("mensaje", ""))).strip(),
            font=("Arial", 9),
            bg=self.ui["surface_alt"],
            fg=self.ui["text_dim"],
            justify="left",
            wraplength=920 if compact else 520,
        )
        descripcion.pack(anchor="w", padx=12)
        self._bind_wrap_to_parent(descripcion, row, pad=26, min_width=260 if compact else 180)
        if respuesta["suggestions"]:
            sugerencias = tk.Frame(row, bg=self.ui["surface_alt"])
            sugerencias.pack(fill="x", padx=12, pady=(6, 0))
            limite = 2 if compact else 3
            for linea in respuesta["suggestions"][:limite]:
                texto = tk.Label(sugerencias, text=f"• {linea}", font=("Arial", 8 if compact else 9), bg=self.ui["surface_alt"], fg="#bfe4ff", justify="left", wraplength=900 if compact else 500)
                texto.pack(anchor="w", pady=(0, 2))
                self._bind_wrap_to_parent(texto, row, pad=28, min_width=220 if compact else 180)
        if not compact and respuesta["steps"]:
            pasos = tk.Frame(row, bg=self.ui["surface_alt"])
            pasos.pack(fill="x", padx=12, pady=(4, 0))
            tk.Label(pasos, text="Pasos sugeridos", font=("Arial", 8, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", pady=(0, 2))
            for linea in respuesta["steps"][:3]:
                texto = tk.Label(pasos, text=f"- {linea}", font=("Arial", 8), bg=self.ui["surface_alt"], fg=self.ui["text_dim"], justify="left", wraplength=500)
                texto.pack(anchor="w", pady=(0, 2))
                self._bind_wrap_to_parent(texto, row, pad=28, min_width=180)
        if respuesta["actions"]:
            acciones = tk.Frame(row, bg=self.ui["surface_alt"])
            acciones.pack(fill="x", padx=12, pady=(6, 2))
            visibles = respuesta["actions"][:3] if compact else respuesta["actions"]
            for accion in visibles:
                bg, fg = self._color_accion_alerta(accion.get("id", ""))
                boton = tk.Button(
                    acciones,
                    text=str(accion.get("label", "")),
                    font=("Arial", 8, "bold"),
                    bg=bg,
                    fg=fg,
                    relief="flat",
                    bd=0,
                    padx=10,
                    pady=4,
                    command=lambda: None,
                )
                boton.pack(side="left", padx=(0, 6), pady=(0, 2))
                self._bind_double_click_action(boton, lambda aid=accion.get("id", ""), a=alerta: self._ejecutar_accion_alerta(a, aid))
        bottom = tk.Frame(row, bg=self.ui["surface_alt"])
        bottom.pack(fill="x", padx=12, pady=(6, 8))
        origen = str(alerta.get("origen", "sistema")).replace("_", " ").title()
        sello = f"{origen} · {alerta.get('fecha', '--')} {formatear_hora_ampm_segundos(alerta.get('hora', '--:--:--'))}"
        tk.Label(bottom, text=sello, font=("Arial", 8), bg=self.ui["surface_alt"], fg=self.ui["text_dim"]).pack(side="left")
        if not compact:
            boton = tk.Button(
                bottom,
                text="Resolver",
                font=("Arial", 8, "bold"),
                bg=self.ui["muted"],
                fg=self.ui["text"],
                activebackground=self.ui["surface_soft"],
                activeforeground=self.ui["text"],
                relief="flat",
                bd=0,
                padx=10,
                pady=4,
                command=lambda: None,
            )
            boton.pack(side="right")
            self._bind_double_click_action(boton, lambda aid=alerta.get("id", ""): self._resolver_alerta_y_refrescar(aid))

    def _resolver_alerta_y_refrescar(self, alerta_id):
        if alerta_id:
            resolver_alerta_panel(alerta_id)
            self._reconstruir_dashboard()

    def _render_alerts_panel(self, status):
        panel = tk.Frame(self.alerts_row, bg="#071a2c", highlightthickness=1, highlightbackground="#1f4f75")
        panel.pack(fill="x")

        header = tk.Frame(panel, bg="#071a2c")
        header.pack(fill="x", padx=16, pady=(14, 10))
        header.grid_columnconfigure(0, weight=1)
        left = tk.Frame(header, bg="#071a2c")
        left.grid(row=0, column=0, sticky="w")
        right = tk.Frame(header, bg="#071a2c")
        right.grid(row=0, column=1, sticky="e")
        tk.Label(left, text="Panel de Alertas", font=("Arial", 14, "bold"), bg="#071a2c", fg="#d8f3ff").pack(anchor="w")
        estado_ai = "Gemma local disponible" if status.get("gemma_available") else "Gemma no disponible"
        color_ai = self.ui["success"] if status.get("gemma_available") else self.ui["warning"]
        tk.Label(left, text=estado_ai, font=("Arial", 8, "bold"), bg="#071a2c", fg=color_ai).pack(anchor="w", pady=(4, 0))
        if status.get("emergency_state", {}).get("activo"):
            tk.Label(left, text="Modo emergencia activo", font=("Arial", 8, "bold"), bg="#071a2c", fg="#fecaca").pack(anchor="w", pady=(2, 0))

        filtros = tk.Frame(left, bg="#071a2c")
        filtros.pack(anchor="w", pady=(6, 0))
        for clave, etiqueta in [("todas", "Todas"), ("critico", "Críticas"), ("advertencia", "Advertencias"), ("info", "Info")]:
            activo = self.alert_filter == clave
            boton = tk.Button(
                filtros,
                text=etiqueta,
                font=("Arial", 8, "bold"),
                bg="#10304a" if activo else "#0b2238",
                fg="#d8f3ff",
                activebackground="#16415f",
                activeforeground="#d8f3ff",
                relief="flat",
                bd=0,
                padx=10,
                pady=5,
                command=lambda filtro=clave: self._set_alert_filter(filtro),
            )
            boton.pack(side="left", padx=(0, 6))

        acciones = tk.Frame(right, bg="#071a2c")
        acciones.pack(anchor="e")
        ver_todas = tk.Button(acciones, text="Ver todas las alertas", font=("Arial", 9, "bold"), bg="#10304a", fg="#d8f3ff", relief="flat", bd=0, padx=12, pady=6, command=lambda: None)
        ver_todas.pack(side="left", padx=(0, 6))
        self._bind_double_click_action(ver_todas, self._abrir_panel_alertas_completo)
        limpiar = tk.Button(acciones, text="Limpiar panel", font=("Arial", 9, "bold"), bg="#3b2608", fg="#fde68a", relief="flat", bd=0, padx=12, pady=6, command=self._limpiar_panel_alertas_dashboard)
        limpiar.pack(side="left", padx=(0, 6))
        sonidos = tk.Button(acciones, text="Sonidos alarma", font=("Arial", 9, "bold"), bg="#10304a", fg="#d8f3ff", relief="flat", bd=0, padx=12, pady=6, command=lambda: None)
        sonidos.pack(side="left")
        self._bind_double_click_action(sonidos, self._abrir_ventana_sonidos)

        body = self._build_scroll_list(panel)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        body.configure(height=210)

        alertas_panel = listar_alertas_panel(self.alert_filter)
        if not alertas_panel:
            self._empty_state(body.inner, "Sin alertas activas", "No hay condiciones reales activas para mostrar.")
            return

        for alerta in alertas_panel[:12]:
            self._render_alert_row(body.inner, alerta, compact=True)

    def _abrir_panel_alertas_completo(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Panel de alertas")
        aplicar_geometria_relativa(ventana, self.root, rel_w=0.60, rel_h=0.70, min_w=760, min_h=560)
        ventana.configure(bg=self.ui["surface"])

        header = tk.Frame(ventana, bg=self.ui["surface"])
        header.pack(fill="x", padx=16, pady=(16, 10))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="Panel de alertas", font=("Arial", 17, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).grid(row=0, column=0, sticky="w")
        acciones = tk.Frame(header, bg=self.ui["surface"])
        acciones.grid(row=0, column=1, sticky="e")
        limpiar = tk.Button(acciones, text="Limpiar panel", font=("Arial", 9, "bold"), bg=self.ui["warning"], fg="#1a1200", relief="flat", bd=0, padx=12, pady=6, command=lambda: self._limpiar_panel_alertas_desde_ventana(ventana))
        limpiar.pack(side="left", padx=(0, 8))
        sonidos = tk.Button(acciones, text="Sonidos alarma", font=("Arial", 9, "bold"), bg=self.ui["accent"], fg="#00111d", relief="flat", bd=0, padx=12, pady=6, command=lambda: None)
        sonidos.pack(side="left")
        self._bind_double_click_action(sonidos, self._abrir_ventana_sonidos)

        filtros = tk.Frame(ventana, bg=self.ui["surface"])
        filtros.pack(fill="x", padx=16, pady=(0, 10))
        filtro_actual = tk.StringVar(value=self.alert_filter)

        def _refrescar_lista(_event=None):
            for widget in body.inner.winfo_children():
                widget.destroy()
            alertas = listar_alertas_panel(filtro_actual.get(), incluir_resueltas=True)
            if not alertas:
                self._empty_state(body.inner, "Sin alertas registradas", "No hay alertas activas ni recientes en el panel.")
                return
            for alerta in alertas[:50]:
                self._render_alert_row(body.inner, alerta, compact=False)

        for clave, etiqueta in [("todas", "Todas"), ("critico", "Críticas"), ("advertencia", "Advertencias"), ("info", "Info")]:
            tk.Radiobutton(
                filtros,
                text=etiqueta,
                variable=filtro_actual,
                value=clave,
                command=_refrescar_lista,
                bg=self.ui["surface"],
                fg=self.ui["text"],
                selectcolor=self.ui["surface_alt"],
                activebackground=self.ui["surface"],
                activeforeground=self.ui["text"],
                highlightthickness=0,
            ).pack(side="left", padx=(0, 10))

        body = self._build_scroll_list(ventana)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        _refrescar_lista()

    def _limpiar_panel_alertas_desde_ventana(self, ventana):
        total = limpiar_panel_alertas()
        if total and ventana.winfo_exists():
            ventana.destroy()
        self._reconstruir_dashboard()

    def _reconstruir_dashboard(self):
        if self._is_rebuilding or not self.root.winfo_exists():
            return
        self._is_rebuilding = True
        try:
            status = self._collect_dashboard_data()
            self._wrap_jobs = []
            self._clear_primary_view()
            if not self._can_access_with_status(status):
                self._render_access_gate(status)
                self._render_status_bar_with_status(status)
                self._last_dashboard_refresh = monotonic()
                return
            self._build_dashboard_layout()
            if self.license_enforcer.should_show_block_screen():
                self._render_license_block_screen(status)
            self._render_license_banner(status)
            self._render_alerts_panel(status)
            self._render_module_cards()
            self._render_status_cards(status)
            self._render_consumption_panel(status)
            self._render_actions_panel(status)
            self._render_plans_panel(status)
            self._render_license_info_panel(status)
            self._render_status_bar_with_status(status)
            self._last_dashboard_refresh = monotonic()
        except Exception as exc:
            if self.root.winfo_exists():
                registrar_log("error", f"Fallo al refrescar dashboard: {exc}", "dashboard")
                self._mostrar_error_en_panel(exc)
        finally:
            self._is_rebuilding = False

    def _render_access_gate(self, status):
        gate = tk.Frame(self.primary_view, bg=self.ui["bg"])
        gate.pack(fill="both", expand=True, padx=26, pady=26)
        gate.grid_columnconfigure(0, weight=1)

        shell = tk.Frame(gate, bg=self.ui["surface"], highlightthickness=1, highlightbackground=self.ui["border"])
        shell.pack(fill="both", expand=True)

        state = self._access_gate_state(status)
        if state == "profile_form":
            self._render_gate_profile_form(shell)
        elif state == "trial_expired":
            self._render_gate_trial_expired(shell, status)
        else:
            self._render_gate_choose_path(shell, status)

    def _render_gate_profile_form(self, parent):
        profile = self._user_profile()
        self._sync_profile_vars(profile)
        body = tk.Frame(parent, bg=self.ui["surface"])
        body.pack(fill="both", expand=True, padx=24, pady=24)
        tk.Label(body, text="Bienvenido a TLAMATINI", font=("Arial", 24, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", pady=(0, 8))
        tk.Label(body, text="Configura tus datos para comenzar.", font=("Arial", 12, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w")
        tk.Label(body, text="Puedes activar una prueba gratuita de 7 días o solicitar una licencia mensual.", font=("Arial", 10), bg=self.ui["surface"], fg=self.ui["text_dim"], justify="left", wraplength=760).pack(anchor="w", pady=(8, 16))
        form = tk.Frame(body, bg=self.ui["surface"])
        form.pack(fill="x", pady=(0, 8))
        labels = [
            ("Nombre completo", self.var_profile_name, 0, 0),
            ("Correo electrónico", self.var_profile_email, 0, 1),
            ("Teléfono opcional", self.var_profile_phone, 2, 0),
            ("País opcional", self.var_profile_country, 2, 1),
        ]
        for text, variable, row, col in labels:
            tk.Label(form, text=text, font=("Arial", 10, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).grid(row=row, column=col, sticky="w", padx=(0, 14), pady=(0, 4))
            tk.Entry(form, textvariable=variable, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=row + 1, column=col, sticky="ew", padx=(0, 14), pady=(0, 10))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        tk.Button(body, text="Guardar y continuar", font=("Arial", 11, "bold"), bg=self.ui["accent"], fg="#00111d", relief="flat", padx=18, pady=10, command=self._save_dashboard_profile).pack(anchor="w", pady=(6, 8))
        tk.Label(body, text="Estos datos se usarán para generar tu solicitud de licencia.", font=("Arial", 9), bg=self.ui["surface"], fg=self.ui["text_dim"]).pack(anchor="w")

    def _render_gate_choose_path(self, parent, status):
        profile = self._user_profile()
        body = tk.Frame(parent, bg=self.ui["surface"])
        body.pack(fill="both", expand=True, padx=24, pady=24)
        tk.Label(body, text="Activa TLAMATINI", font=("Arial", 24, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", pady=(0, 8))
        tk.Label(body, text="Elige cómo quieres comenzar.", font=("Arial", 12, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", pady=(0, 18))

        trial_card = tk.Frame(body, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
        trial_card.pack(fill="x", pady=(0, 12))
        tk.Label(trial_card, text="Prueba gratuita de 7 días", font=("Arial", 13, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", padx=14, pady=(14, 4))
        tk.Label(trial_card, text="Usa TLAMATINI durante 7 días en este equipo. No necesitas conexión con servidor.", font=("Arial", 10), bg=self.ui["surface_alt"], fg=self.ui["text_dim"], justify="left", wraplength=760).pack(anchor="w", padx=14, pady=(0, 10))
        tk.Button(trial_card, text="Activar prueba de 7 días", font=("Arial", 11, "bold"), bg=self.ui["success"], fg="#04110a", relief="flat", padx=18, pady=10, command=self._start_trial_from_dashboard).pack(anchor="w", padx=14, pady=(0, 14))

        monthly_card = tk.Frame(body, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
        monthly_card.pack(fill="x")
        tk.Label(monthly_card, text="Licencia mensual", font=("Arial", 13, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", padx=14, pady=(14, 4))
        tk.Label(monthly_card, text="Solicita tu licencia mensual al administrador. Recibirás un código de activación.", font=("Arial", 10), bg=self.ui["surface_alt"], fg=self.ui["text_dim"], justify="left", wraplength=760).pack(anchor="w", padx=14, pady=(0, 10))
        tk.Button(monthly_card, text="Solicitar licencia mensual", font=("Arial", 11, "bold"), bg=self.ui["accent"], fg="#00111d", relief="flat", padx=18, pady=10, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="request_license")).pack(anchor="w", padx=14, pady=(0, 14))

        secondary = tk.Frame(body, bg=self.ui["surface"])
        secondary.pack(fill="x", pady=(16, 0))
        tk.Button(secondary, text="Pegar código recibido", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", padx=12, pady=8, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="paste_code")).pack(side="left", padx=(0, 8))
        tk.Button(secondary, text="Editar mis datos", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", padx=12, pady=8, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="profile")).pack(side="left")
        tk.Label(body, text=f"{profile.get('full_name', '').strip()} · {profile.get('email', '').strip()}", font=("Arial", 9), bg=self.ui["surface"], fg=self.ui["text_dim"]).pack(anchor="w", pady=(12, 0))

    def _render_gate_trial_expired(self, parent, status):
        body = tk.Frame(parent, bg=self.ui["surface"])
        body.pack(fill="both", expand=True, padx=24, pady=24)
        tk.Label(body, text="Tu prueba gratuita ha vencido", font=("Arial", 24, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", pady=(0, 8))
        tk.Label(body, text="Para seguir usando TLAMATINI, solicita una licencia mensual o pega un código recibido.", font=("Arial", 11), bg=self.ui["surface"], fg=self.ui["text_dim"], justify="left", wraplength=760).pack(anchor="w", pady=(0, 18))
        actions = tk.Frame(body, bg=self.ui["surface"])
        actions.pack(fill="x")
        tk.Button(actions, text="Solicitar licencia mensual", font=("Arial", 11, "bold"), bg=self.ui["accent"], fg="#00111d", relief="flat", padx=18, pady=10, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="request_license")).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Pegar código recibido", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", padx=12, pady=8, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="paste_code")).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Editar mis datos", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", padx=12, pady=8, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="profile")).pack(side="left")

    def _refrescar_estado_sin_reconstruir(self):
        if not self.root.winfo_exists():
            return
        if self.status_left is None or self.status_right is None:
            return
        status = self._collect_dashboard_data()
        self._render_status_bar_with_status(status)
        self._last_dashboard_refresh = monotonic()

    def _collect_dashboard_data(self):
        license_status = self.license_enforcer.current_status()
        active_alerts = self._safe_list(sincronizar_alertas_dashboard())
        inventory_alerts = self._safe_list(listar_alertas_inventario())
        inventory_items = self._safe_list(listar_inventario())
        logs = list(reversed(self._safe_list(leer_logs())[-12:]))
        learning_state = self._safe_dict(load_learning_state())
        library_state = self._safe_dict(load_library_state())
        planes = self._safe_list(listar_planes())
        personas = self._safe_list(listar_personas() or obtener_seccion("personas", []))
        mapa_activo = self._safe_dict(obtener_mapa_activo() or {})

        learning_installed_map = self._safe_dict(learning_state.get("installed", {}))
        learning_progress_map = self._safe_dict(learning_state.get("progress", {}))
        learning_installed = list(learning_installed_map.values())
        lessons_total = sum(int(item.get("lesson_count", 0) or 0) for item in learning_installed)
        lessons_done = sum(
            len(self._safe_dict(learning_progress_map.get(item.get("id", ""), {})).get("completed_lessons", []) or [])
            for item in learning_installed
        )
        learning_progress = round((lessons_done / lessons_total) * 100.0, 1) if lessons_total else 0.0

        library_installed = list(self._safe_dict(library_state.get("installed", {})).values())
        active_reader = self._safe_dict(library_state.get("reader", {}))
        agua_litros = estimar_agua_disponible_litros(inventory_items)
        food_status = estimar_reserva_comida(inventory_items, personas)
        water_status = estimar_reserva_agua(inventory_items, personas)
        inventory_status = self._inventory_status(inventory_items, inventory_alerts)
        health_status = self._health_status(active_alerts, inventory_alerts, personas)
        health_alerts = health_status["alerts"]
        climate_value = self._climate_fallback()
        location_text = mapa_activo.get("name") or "Sin mapa activo"
        active_users = max(1, len(personas)) if personas else 1
        connectivity_status = self._connectivity_status(active_reader, logs)
        emergency_state = obtener_estado_modo_emergencia()

        status = {
            "alerts": active_alerts,
            "inventory_alerts": inventory_alerts,
            "inventory_items": inventory_items,
            "logs": logs,
            "learning_installed": learning_installed,
            "learning_progress": learning_progress,
            "library_installed": library_installed,
            "library_reader": active_reader,
            "planes": planes,
            "profiles": personas,
            "mapa_activo": mapa_activo,
            "location_text": location_text,
            "active_users": active_users,
            "backup_text": self._last_backup_label(),
            "connectivity": connectivity_status["summary"],
            "connectivity_status": connectivity_status,
            "gemma_available": self._gemma_available,
            "gemma_status": self._gemma_status,
            "emergency_state": emergency_state,
            "food_status": food_status,
            "water_status": water_status,
            "agua_litros": agua_litros,
            "health_alerts": health_alerts,
            "health_status": health_status,
            "climate": climate_value,
            "inventory_critical": inventory_status["critical_count"],
            "inventory_status": inventory_status,
            "operational_state": self._operational_state(active_alerts, emergency_state),
            "bitacora": logs[:8],
            "license_status": license_status,
        }
        status["system_suggestions"] = self._build_system_suggestions(status)
        return status

    def _render_license_banner(self, status):
        license_status = self._safe_dict(status.get("license_status", {}))
        state = str(license_status.get("state", "")).strip().lower()
        if state not in {"grace", "expired"}:
            return

        bg = "#3b2608" if state == "grace" else "#2a0c11"
        border = self.ui["warning"] if state == "grace" else self.ui["danger"]
        fg = "#fde68a" if state == "grace" else "#fecaca"
        titulo = "Modo gracia activo" if state == "grace" else "Licencia vencida"
        mensaje = self.license_enforcer.grace_message() if state == "grace" else self.license_enforcer.block_reason_for("este módulo")

        panel = tk.Frame(self.alerts_row, bg=bg, highlightthickness=1, highlightbackground=border)
        panel.pack(fill="x", pady=(0, 10))
        tk.Label(panel, text=titulo, font=("Arial", 12, "bold"), bg=bg, fg=fg).pack(anchor="w", padx=16, pady=(12, 4))
        tk.Label(panel, text=mensaje, font=("Arial", 10), bg=bg, fg=fg, justify="left", wraplength=980).pack(anchor="w", padx=16, pady=(0, 10))

    def _license_dashboard_state_label(self, license_status):
        state = str(license_status.get("state", "missing")).strip().lower()
        source = str(license_status.get("source", "")).strip().lower()
        if state in {"valid", "grace"}:
            if source == "local_trial" or str(license_status.get("plan", "")).strip().lower() == "trial":
                return "Prueba activa"
            if source == "offline_code":
                return "Modo offline permitido"
            return "Activa"
        if state == "expired":
            return "Vencida"
        if state == "invalid":
            return "Licencia inválida"
        if license_status.get("trial_expired"):
            return "Prueba utilizada"
        return "Sin licencia"

    def _license_dashboard_email(self, license_status):
        email = str(license_status.get("customer_email", "")).strip()
        if email:
            return email
        if license_status.get("session_email"):
            return str(license_status.get("session_email", "")).strip()
        if license_status.get("backend_configured"):
            return "Pendiente"
        return "No registrado"

    def _license_dashboard_days_remaining(self, license_status):
        state = str(license_status.get("state", "missing")).strip().lower()
        if license_status.get("trial_expired"):
            return "0"
        if state == "expired":
            return "Vencida"
        if state == "missing":
            return "Sin licencia"
        days = license_status.get("days_remaining")
        return str(days) if days is not None else "No disponible"

    def _current_version_label(self):
        version = self.update_checker.local_state().get("current_version") or "local"
        return f"Versión {version}"

    def _user_profile(self):
        return load_user_profile()

    def _sync_profile_vars(self, profile=None):
        data = profile or self._user_profile()
        if data.get("full_name") and not self.var_profile_name.get().strip():
            self.var_profile_name.set(str(data.get("full_name", "")).strip())
        if data.get("email") and not self.var_profile_email.get().strip():
            self.var_profile_email.set(str(data.get("email", "")).strip())
        if data.get("phone") and not self.var_profile_phone.get().strip():
            self.var_profile_phone.set(str(data.get("phone", "")).strip())
        if data.get("country") and not self.var_profile_country.get().strip():
            self.var_profile_country.set(str(data.get("country", "")).strip())

    def _license_dashboard_name(self, license_status):
        name = str(license_status.get("customer_name", "")).strip()
        if name:
            return name
        profile = self._user_profile()
        return str(profile.get("full_name", "")).strip()

    def _license_request_text(self, status):
        license_status = self._safe_dict(status.get("license_status", {}))
        return build_manual_license_request(
            profile=self._user_profile(),
            identity=get_installation_payload(),
            current_state=self._license_dashboard_state_label(license_status),
            requested_plan=license_status.get("plan") or "mensual",
        )

    def _copy_to_clipboard(self, text, *, title, success_message):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(str(text))
            self.root.update_idletasks()
            messagebox.showinfo(title, success_message, parent=self.root)
        except Exception as exc:
            messagebox.showerror(title, f"No se pudo copiar al portapapeles.\n\nDetalle: {exc}", parent=self.root)

    def _copy_license_request_info(self, status):
        try:
            request_text = self._license_request_text(status)
        except ValueError as exc:
            messagebox.showwarning("Licencia", str(exc), parent=self.root)
            abrir_licencia(self.app_root, self.root, initial_view="profile")
            return
        self._copy_to_clipboard(request_text, title="Licencia", success_message="La solicitud de licencia se copió al portapapeles.")

    def _copy_installation_id(self):
        installation_id = get_installation_payload()["installation_id"]
        self._copy_to_clipboard(
            installation_id,
            title="Licencia",
            success_message="El ID de instalación se copió al portapapeles.",
        )

    def _toggle_license_details(self):
        self._license_details_visible = not self._license_details_visible
        self._reconstruir_dashboard()

    def _save_dashboard_profile(self):
        try:
            profile = save_user_profile(
                full_name=self.var_profile_name.get(),
                email=self.var_profile_email.get(),
                phone=self.var_profile_phone.get(),
                country=self.var_profile_country.get(),
            )
        except ValueError as exc:
            messagebox.showwarning("Perfil", str(exc), parent=self.root)
            return
        self.var_profile_name.set(profile["full_name"])
        self.var_profile_email.set(profile["email"])
        self.var_profile_phone.set(profile["phone"])
        self.var_profile_country.set(profile["country"])
        messagebox.showinfo("Perfil", "Tus datos se guardaron correctamente. Ahora elige cómo quieres activar TLAMATINI.", parent=self.root)
        self._reconstruir_dashboard()

    def _start_trial_from_dashboard(self):
        try:
            self.license_client.start_trial()
        except (BackendNotConfiguredError, BackendUnavailableError, LicenseClientError) as exc:
            messagebox.showwarning("Licencia", str(exc), parent=self.root)
            return
        except Exception as exc:
            messagebox.showerror("Licencia", f"No se pudo activar la prueba: {exc}", parent=self.root)
            return
        messagebox.showinfo("Licencia", "La prueba de 7 días quedó activada.", parent=self.root)
        self._reconstruir_dashboard()

    def _license_panel_mode(self, license_status, profile_ready):
        if not profile_ready:
            return "profile_form"
        state = str(license_status.get("state", "")).strip().lower()
        plan = str(license_status.get("plan", "")).strip().lower()
        if state in {"valid", "grace"} and plan == "trial":
            return "trial_active"
        if state in {"valid", "grace"}:
            return "license_active"
        return "choose_path"

    def _render_license_info_panel(self, status):
        license_status = self._safe_dict(status.get("license_status", {}))
        profile = self._user_profile()
        self._sync_profile_vars(profile)
        identity = get_installation_payload()
        profile_ready = is_profile_complete(profile)
        panel_mode = self._license_panel_mode(license_status, profile_ready)
        panel = tk.Frame(self.license_info_row, bg=self.ui["surface"], highlightthickness=1, highlightbackground=self.ui["border"])
        panel.pack(fill="x")

        if panel_mode == "profile_form":
            tk.Label(panel, text="Bienvenido a TLAMATINI", font=("Arial", 14, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=16, pady=(14, 4))
            tk.Label(panel, text="Para comenzar, guarda tus datos y elige cómo quieres activar TLAMATINI.", font=("Arial", 10), bg=self.ui["surface"], fg=self.ui["text_dim"], justify="left", wraplength=980).pack(anchor="w", padx=16, pady=(0, 12))
            form = tk.Frame(panel, bg=self.ui["surface"])
            form.pack(fill="x", padx=16, pady=(0, 8))
            labels = [
                ("Nombre completo", self.var_profile_name, 0, 0),
                ("Correo electrónico", self.var_profile_email, 0, 1),
                ("Teléfono opcional", self.var_profile_phone, 2, 0),
                ("País opcional", self.var_profile_country, 2, 1),
            ]
            for text, variable, row, col in labels:
                tk.Label(form, text=text, font=("Arial", 10, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).grid(row=row, column=col, sticky="w", padx=(0, 12), pady=(0, 4))
                tk.Entry(form, textvariable=variable, font=("Arial", 11), bg="white", fg="#0f172a").grid(row=row + 1, column=col, sticky="ew", padx=(0, 12), pady=(0, 10))
            form.grid_columnconfigure(0, weight=1)
            form.grid_columnconfigure(1, weight=1)
            actions = tk.Frame(panel, bg=self.ui["surface"])
            actions.pack(fill="x", padx=16, pady=(4, 16))
            tk.Button(actions, text="Guardar y continuar", font=("Arial", 11, "bold"), bg=self.ui["accent"], fg="#00111d", relief="flat", padx=18, pady=10, command=self._save_dashboard_profile).pack(side="left")
            return

        if panel_mode == "choose_path":
            tk.Label(panel, text="Elige cómo comenzar", font=("Arial", 14, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=16, pady=(14, 4))
            subtitle = "Comienza activando una prueba gratuita o solicitando tu licencia mensual."
            if license_status.get("trial_expired"):
                subtitle = "La prueba gratuita ya fue utilizada en esta instalación."
            tk.Label(panel, text=subtitle, font=("Arial", 10), bg=self.ui["surface"], fg=self.ui["text_dim"], justify="left", wraplength=980).pack(anchor="w", padx=16, pady=(0, 12))

            options = tk.Frame(panel, bg=self.ui["surface"])
            options.pack(fill="x", padx=16, pady=(0, 8))
            trial_card = tk.Frame(options, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
            trial_card.pack(fill="x", pady=(0, 10))
            tk.Label(trial_card, text="Activar prueba gratuita de 7 días", font=("Arial", 12, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", padx=12, pady=(12, 4))
            tk.Label(trial_card, text="Usa TLAMATINI durante 7 días sin solicitar una licencia mensual.", font=("Arial", 10), bg=self.ui["surface_alt"], fg=self.ui["text_dim"], justify="left", wraplength=940).pack(anchor="w", padx=12, pady=(0, 10))
            if not license_status.get("trial_expired"):
                tk.Button(trial_card, text="Activar prueba de 7 días", font=("Arial", 11, "bold"), bg=self.ui["success"], fg="#04110a", relief="flat", padx=18, pady=10, command=self._start_trial_from_dashboard).pack(anchor="w", padx=12, pady=(0, 12))

            monthly_card = tk.Frame(options, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
            monthly_card.pack(fill="x")
            tk.Label(monthly_card, text="Solicitar licencia mensual", font=("Arial", 12, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", padx=12, pady=(12, 4))
            tk.Label(monthly_card, text="Copia tu solicitud de licencia y envíala al administrador después del pago. Recibirás un código de activación.", font=("Arial", 10), bg=self.ui["surface_alt"], fg=self.ui["text_dim"], justify="left", wraplength=940).pack(anchor="w", padx=12, pady=(0, 10))
            tk.Button(monthly_card, text="Solicitar licencia mensual", font=("Arial", 11, "bold"), bg=self.ui["accent"], fg="#00111d", relief="flat", padx=18, pady=10, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="request_license")).pack(anchor="w", padx=12, pady=(0, 12))

            actions = tk.Frame(panel, bg=self.ui["surface"])
            actions.pack(fill="x", padx=16, pady=(4, 16))
            tk.Button(actions, text="Pegar código recibido", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", padx=12, pady=8, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="paste_code")).pack(side="left", padx=(0, 8))
            tk.Button(actions, text="Editar datos", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", padx=12, pady=8, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="profile")).pack(side="left")
            return

        summary = tk.Frame(panel, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
        summary.pack(fill="x", padx=16, pady=(14, 12))
        facts = [
            ("Estado", self._license_dashboard_state_label(license_status)),
            ("Nombre", self._license_dashboard_name(license_status) or "No disponible"),
            ("Email", self._license_dashboard_email(license_status)),
            ("Plan", str(license_status.get("plan", "")).strip() or "Sin plan"),
            ("Vence", str(license_status.get("expires_at", "")).strip() or "No disponible"),
            ("Días restantes", self._license_dashboard_days_remaining(license_status)),
            ("ID de instalación", identity["installation_id"]),
        ]
        if panel_mode == "trial_active":
            facts = [item for item in facts if item[0] != "Nombre"]
        for label, value in facts:
            row = tk.Frame(summary, bg=self.ui["surface_alt"])
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{label}:", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], width=16, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Arial", 10), bg=self.ui["surface_alt"], fg=self.ui["text_dim"] if label != "Estado" else self.ui["text"], anchor="w", justify="left").pack(side="left", fill="x", expand=True)

        tk.Label(panel, text="Prueba activa" if panel_mode == "trial_active" else "Licencia activa", font=("Arial", 14, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=16, pady=(0, 4))
        actions = tk.Frame(panel, bg=self.ui["surface"])
        actions.pack(fill="x", padx=16, pady=(0, 16))
        if panel_mode == "trial_active":
            tk.Button(actions, text="Solicitar licencia mensual", font=("Arial", 11, "bold"), bg=self.ui["accent"], fg="#00111d", relief="flat", padx=18, pady=10, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="request_license")).pack(side="left", padx=(0, 8))
            tk.Button(actions, text="Pegar código recibido", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", padx=12, pady=8, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="paste_code")).pack(side="left")
            return

        tk.Button(actions, text="Renovar licencia", font=("Arial", 11, "bold"), bg=self.ui["accent"], fg="#00111d", relief="flat", padx=18, pady=10, command=lambda: abrir_licencia(self.app_root, self.root, initial_view="request_license")).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Ver detalles" if not self._license_details_visible else "Ocultar detalles", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", padx=12, pady=8, command=self._toggle_license_details).pack(side="left")

        if self._license_details_visible:
            details = tk.Frame(panel, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
            details.pack(fill="x", padx=16, pady=(0, 16))
            facts = [
                ("Estado", self._license_dashboard_state_label(license_status)),
                ("Nombre", self._license_dashboard_name(license_status) or "No disponible"),
                ("Plan", str(license_status.get("plan", "")).strip() or "Sin plan"),
                ("Vence", str(license_status.get("expires_at", "")).strip() or "No disponible"),
                ("Días restantes", self._license_dashboard_days_remaining(license_status)),
                ("Email", self._license_dashboard_email(license_status)),
                ("ID de instalación", identity["installation_id"]),
            ]
            for label, value in facts:
                row = tk.Frame(details, bg=self.ui["surface_alt"])
                row.pack(fill="x", padx=12, pady=2)
                tk.Label(row, text=f"{label}:", font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], width=16, anchor="w").pack(side="left")
                tk.Label(row, text=value, font=("Arial", 10), bg=self.ui["surface_alt"], fg=self.ui["text_dim"] if label != "Estado" else self.ui["text"], anchor="w", justify="left").pack(side="left", fill="x", expand=True)
            detail_actions = tk.Frame(details, bg=self.ui["surface_alt"])
            detail_actions.pack(fill="x", padx=12, pady=(10, 12))
            tk.Button(
                detail_actions,
                text="Copiar solo ID de instalación",
                font=("Arial", 10, "bold"),
                bg=self.ui["surface"],
                fg=self.ui["text"],
                activebackground=self.ui["surface_soft"],
                activeforeground=self.ui["text"],
                relief="flat",
                padx=12,
                pady=8,
                command=self._copy_installation_id,
            ).pack(side="left")

    def _render_license_block_screen(self, status):
        license_status = self._safe_dict(status.get("license_status", {}))
        panel = tk.Frame(self.cards_row, bg="#2a0c11", highlightthickness=1, highlightbackground="#7f1d1d")
        panel.pack(fill="x")
        tk.Label(
            panel,
            text="Acceso restringido por licencia",
            font=("Arial", 18, "bold"),
            bg="#2a0c11",
            fg="#fecaca",
        ).pack(anchor="w", padx=18, pady=(18, 8))
        tk.Label(
            panel,
            text=self.license_enforcer.block_reason_for("TLAMATINI"),
            font=("Arial", 11),
            bg="#2a0c11",
            fg="#fecaca",
            justify="left",
            wraplength=960,
        ).pack(anchor="w", padx=18, pady=(0, 8))
        tk.Label(
            panel,
            text=f"Estado local: {license_status.get('state', 'missing')} | Plan: {license_status.get('plan') or '--'} | Última sincronización: {license_status.get('last_sync_at') or '--'}",
            font=("Arial", 10),
            bg="#2a0c11",
            fg="#fca5a5",
            justify="left",
            wraplength=960,
        ).pack(anchor="w", padx=18, pady=(0, 12))

        acciones = tk.Frame(panel, bg="#2a0c11")
        acciones.pack(anchor="w", padx=18, pady=(0, 18))
        tk.Button(
            acciones,
            text="Abrir activación",
            font=("Arial", 10, "bold"),
            bg=self.ui["surface_alt"],
            fg=self.ui["text"],
            relief="flat",
            command=lambda: abrir_licencia(self.app_root, self.root),
        ).pack(side="left")

    def _render_status_cards(self, status):
        for widget in self.cards_row.winfo_children():
            widget.destroy()

        cards = [
            {
                "title": "Estado operativo",
                "value": status["operational_state"]["label"],
                "subtitle": status["operational_state"]["subtitle"],
                "icon": "🛡",
                "color": status["operational_state"]["color"],
                "details": [],
            },
            {
                "title": "Comida",
                "value": status["food_status"]["value"],
                "subtitle": status["food_status"]["subtitle"],
                "icon": "🍽",
                "color": "#fbbf24",
                "details": [],
            },
            {
                "title": "Agua",
                "value": status["water_status"]["value"],
                "subtitle": status["water_status"]["subtitle"],
                "icon": "💧",
                "color": "#38bdf8",
                "details": [],
            },
            {
                "title": "Inventario crítico",
                "value": status["inventory_status"]["value"],
                "subtitle": status["inventory_status"]["subtitle"],
                "icon": "📦",
                "color": "#f97316",
                "details": [],
            },
            {
                "title": "Conectividad",
                "value": status["connectivity_status"]["value"],
                "subtitle": status["connectivity_status"]["subtitle"],
                "icon": "📶",
                "color": status["connectivity_status"]["color"],
                "details": status["connectivity_status"]["details"][:2],
            },
        ]

        for index, card in enumerate(cards):
            self.cards_row.grid_columnconfigure(index, weight=1, uniform="cards")
            frame = tk.Frame(self.cards_row, bg=self.ui["surface"], highlightthickness=1, highlightbackground=self.ui["border"])
            frame.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 8, 0), pady=0)
            icon, title, value = card["icon"], card["title"], card["value"]
            tk.Label(frame, text=icon, font=("Arial", 14), bg=self.ui["surface"], fg=card["color"]).pack(anchor="w", padx=10, pady=(8, 0))
            tk.Label(frame, text=title, font=("Arial", 10, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=10, pady=(6, 0))
            tk.Label(frame, text=value, font=("Arial", 10, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=10, pady=(4, 0))
            subtitle = tk.Label(
                frame,
                text=card.get("subtitle", ""),
                font=("Arial", 7),
                bg=self.ui["surface"],
                fg=self.ui["text_dim"],
                justify="left",
                wraplength=155,
            )
            subtitle.pack(anchor="w", padx=10, pady=(5, 0))
            self._bind_wrap_to_parent(subtitle, frame, pad=28, min_width=110)
            for detail in card.get("details", [])[:2]:
                detalle = tk.Label(frame, text=detail, font=("Arial", 7), bg=self.ui["surface"], fg=self.ui["text_dim"], wraplength=155, justify="left")
                detalle.pack(anchor="w", padx=10, pady=(2, 0))
                self._bind_wrap_to_parent(detalle, frame, pad=28, min_width=110)
            tk.Frame(frame, bg=self.ui["surface"], height=6).pack(fill="x", padx=10, pady=(0, 8))

    def _build_panel(self, parent, title, subtitle=""):
        frame = tk.Frame(parent, bg=self.ui["surface"], highlightthickness=1, highlightbackground=self.ui["border"])
        header = tk.Frame(frame, bg=self.ui["surface"])
        header.pack(fill="x", padx=16, pady=(14, 10))
        header.grid_columnconfigure(0, weight=1)
        left = tk.Frame(header, bg=self.ui["surface"])
        left.grid(row=0, column=0, sticky="w")
        right = tk.Frame(header, bg=self.ui["surface"])
        right.grid(row=0, column=1, sticky="e")
        tk.Label(left, text=title, font=("Arial", 13, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w")
        body = tk.Frame(frame, bg=self.ui["surface"])
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        frame.body = body
        frame.header_right = right
        return frame

    def _render_actions_panel(self, status):
        panel = self._build_panel(self.grid_panels, "Acciones rápidas")
        panel.grid(row=0, column=1, sticky="nsew", padx=8, pady=0)
        grid = tk.Frame(panel.body, bg=self.ui["surface"])
        grid.pack(fill="both", expand=True)
        acciones = [
            ("📝", "Registrar evento", self._abrir_registro_rapido_bitacora, self.ui["accent"]),
            ("🗺", "Ver mapa", lambda: self._permitir_acceso_modulo("mapa", "Mapa") and abrir_mapa(self.app_root, self.root), self.ui["info"]),
            ("📦", "Revisar inventario", lambda: abrir_inventario(self.app_root, self.root), "#f97316"),
            ("📋", "Activar protocolo", self._abrir_selector_protocolos, "#fbbf24"),
            ("✅", "Iniciar checklist", self._abrir_checklist_rapida, self.ui["success"]),
            ("📡", "Comunicar", self._abrir_centro_comunicaciones, "#0891B2"),
        ]
        for idx, (icono, titulo, accion, color) in enumerate(acciones):
            fila = idx // 2
            columna = idx % 2
            grid.grid_columnconfigure(columna, weight=1, uniform="acciones")
            grid.grid_rowconfigure(fila, weight=1, uniform="acciones_r")
            card = tk.Frame(
                grid,
                bg=self.ui["surface_alt"],
                highlightthickness=1,
                highlightbackground=color,
                cursor="hand2",
            )
            card.grid(row=fila, column=columna, sticky="nsew", padx=6, pady=6)
            icon_label = tk.Label(card, text=icono, font=("Arial", 20), bg=self.ui["surface_alt"], fg=color)
            icon_label.pack(anchor="w", padx=12, pady=(12, 6))
            text_label = tk.Label(card, text=titulo, font=("Arial", 10, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], anchor="w", justify="left", wraplength=180)
            text_label.pack(anchor="w", padx=12, pady=(0, 12))
            self._bind_wrap_to_parent(text_label, card, pad=26, min_width=110)
            for widget in (card, icon_label, text_label):
                self._bind_double_click_action(widget, lambda fn=accion: fn())

    def _render_plans_panel(self, status):
        panel = self._build_panel(self.grid_panels, "Planes y protocolos")
        panel.grid(row=0, column=2, sticky="nsew", padx=(8, 0), pady=0)
        planes = status["planes"]
        if not planes:
            self._empty_state(panel.body, "Aún no tienes planes registrados.", "Crea un plan en el módulo de Planes para verlo y activarlo aquí.")
            return
        for plan in planes[:4]:
            row = tk.Frame(panel.body, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
            row.pack(fill="x", pady=5)
            nombre = self._titulo_plan(plan)
            escenario = str(plan.get("datos_generales", {}).get("escenario_principal", "")).strip() or "Sin escenario principal"
            nombre_label = tk.Label(row, text=nombre, font=("Arial", 11, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], wraplength=280, justify="left")
            nombre_label.pack(anchor="w", padx=12, pady=(10, 2))
            self._bind_wrap_to_parent(nombre_label, row, pad=26, min_width=140)
            escenario_label = tk.Label(row, text=escenario, font=("Arial", 9), bg=self.ui["surface_alt"], fg=self.ui["text_dim"], wraplength=280, justify="left")
            escenario_label.pack(anchor="w", padx=12)
            self._bind_wrap_to_parent(escenario_label, row, pad=26, min_width=140)
            acciones = tk.Frame(row, bg=self.ui["surface_alt"])
            acciones.pack(fill="x", padx=12, pady=(8, 10))
            boton_abrir = tk.Button(acciones, text="Abrir", font=("Arial", 9, "bold"), bg=self.ui["muted"], fg=self.ui["text"], relief="flat", command=lambda: None)
            boton_abrir.pack(side="left")
            self._bind_double_click_action(boton_abrir, lambda: abrir_planes(self.app_root, self.root))
            boton_ejecutar = tk.Button(acciones, text="Ejecutar", font=("Arial", 9, "bold"), bg=self.ui["warning"], fg="#1a1200", relief="flat", command=lambda: None)
            boton_ejecutar.pack(side="left", padx=(8, 0))
            self._bind_double_click_action(boton_ejecutar, lambda p=plan: self._activar_plan(p))
        if len(planes) > 4:
            boton_todos = tk.Button(panel.body, text="Ver todos los planes", font=("Arial", 9, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"], relief="flat", command=lambda: None)
            boton_todos.pack(anchor="w", pady=(10, 0))
            self._bind_double_click_action(boton_todos, lambda: abrir_planes(self.app_root, self.root))

    def _render_consumption_panel(self, status):
        panel = self._build_panel(self.grid_panels, "Consumo / análisis")
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        water = status["water_status"]
        food = status["food_status"]
        tiene_datos = (
            water.get("litros_disponibles", 0) > 0
            or food.get("total_kcal", 0) > 0
            or food.get("total_raciones", 0) > 0
        )
        if not tiene_datos:
            self._empty_state(panel.body, "Sin datos de consumo suficientes.", "Registra perfiles y recursos de agua/comida para ver análisis útil.")
            return

        agua_box = tk.Frame(panel.body, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
        agua_box.pack(fill="x", pady=(0, 8))
        tk.Label(agua_box, text="Agua", font=("Arial", 11, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", padx=12, pady=(10, 4))
        for linea in [
            f"Disponibles: {water.get('value', 'Sin datos')}",
            f"Grupo: {water.get('personas_consideradas', 0)} persona(s)",
            (
                f"Autonomía: {water['dias_autonomia']:.1f} días"
                if water.get("dias_autonomia") is not None
                else "Autonomía: Sin datos"
            ),
        ]:
            tk.Label(agua_box, text=linea, font=("Arial", 9), bg=self.ui["surface_alt"], fg=self.ui["text_dim"]).pack(anchor="w", padx=12, pady=(0, 3))

        comida_box = tk.Frame(panel.body, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
        comida_box.pack(fill="x", pady=(8, 0))
        tk.Label(comida_box, text="Comida", font=("Arial", 11, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", padx=12, pady=(10, 4))
        lineas_comida = [
            f"Reserva: {food.get('value', 'Sin datos')}",
            f"Grupo: {food.get('personas_consideradas', 0)} persona(s)",
        ]
        if food.get("dias_autonomia") is not None:
            lineas_comida.append(f"Autonomía estimada: {food['dias_autonomia']:.1f} días")
        else:
            lineas_comida.append("Autonomía estimada: Sin datos")
        if food.get("metodo") == "kcal" and food.get("dias_autonomia_raciones") is not None:
            lineas_comida.append(f"Referencia secundaria: {food['dias_autonomia_raciones']:.1f} días por raciones")
        for linea in lineas_comida:
            tk.Label(comida_box, text=linea, font=("Arial", 9), bg=self.ui["surface_alt"], fg=self.ui["text_dim"]).pack(anchor="w", padx=12, pady=(0, 3))

    def _build_scroll_list(self, parent):
        host = tk.Frame(parent, bg=self.ui["surface"])
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(0, weight=1)
        canvas = tk.Canvas(host, bg=self.ui["surface"], highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.ui["surface"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(inner_window, width=e.width))
        self._bind_mousewheel(host, inner, canvas)
        host.inner = inner
        return host

    def _bind_wrap_to_parent(self, label, parent, pad=28, min_width=120):
        def _actualizar(_event=None):
            try:
                if not self.root.winfo_exists() or not label.winfo_exists() or not parent.winfo_exists():
                    return
                width = max(min_width, parent.winfo_width() - pad)
                if getattr(label, "_last_wraplength", None) == width:
                    return
                label._last_wraplength = width
                label.configure(wraplength=width)
            except Exception:
                pass

        parent.bind("<Configure>", _actualizar, add="+")
        self._wrap_jobs.append(_actualizar)
        self.root.after(20, _actualizar)

    def _refresh_wraps(self):
        self._wrap_refresh_job = None
        for callback in list(self._wrap_jobs):
            try:
                callback()
            except Exception:
                pass

    def _schedule_wrap_refresh(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if self._wrap_refresh_job:
            return
        self._wrap_refresh_job = self.root.after(90, self._refresh_wraps)

    def _empty_state(self, parent, title, subtitle):
        box = tk.Frame(parent, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
        box.pack(fill="both", expand=True, pady=5)
        tk.Label(box, text=title, font=("Arial", 12, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", padx=14, pady=(14, 4))
        tk.Label(box, text=subtitle, font=("Arial", 9), bg=self.ui["surface_alt"], fg=self.ui["text_dim"]).pack(anchor="w", padx=14, pady=(0, 14))

    def _icon_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            font=("Arial", 13),
            bg=self.ui["surface"],
            fg=self.ui["text"],
            activebackground=self.ui["surface_soft"],
            activeforeground=self.ui["text"],
            relief="flat",
            bd=0,
            padx=10,
            pady=7,
            command=command,
        )

    def _progress_bar(self, parent, percent, color):
        shell = tk.Frame(parent, bg=self.ui["muted"], height=8)
        shell.pack_propagate(False)
        if percent is None:
            return shell
        width = int(2.2 * max(0, min(100, percent)))
        fill = tk.Frame(shell, bg=color, width=width)
        fill.pack(side="left", fill="y")
        return shell

    def _bind_mousewheel(self, *widgets):
        if len(widgets) < 2:
            return
        canvas = widgets[-1]

        def _pointer_inside_canvas():
            try:
                pointer_x = self.root.winfo_pointerx()
                pointer_y = self.root.winfo_pointery()
                left = canvas.winfo_rootx()
                top = canvas.winfo_rooty()
                right = left + canvas.winfo_width()
                bottom = top + canvas.winfo_height()
                return left <= pointer_x <= right and top <= pointer_y <= bottom
            except Exception:
                return False

        def _on_wheel(event):
            if not _pointer_inside_canvas():
                return
            delta = 0
            if getattr(event, "delta", 0):
                delta = -1 if event.delta > 0 else 1
            elif getattr(event, "num", None) == 4:
                delta = -1
            elif getattr(event, "num", None) == 5:
                delta = 1
            if delta:
                canvas.yview_scroll(delta, "units")

        for target in widgets:
            target.bind("<MouseWheel>", _on_wheel, add="+")
            target.bind("<Button-4>", _on_wheel, add="+")
            target.bind("<Button-5>", _on_wheel, add="+")
        self.root.bind_all("<MouseWheel>", _on_wheel, add="+")
        self.root.bind_all("<Button-4>", _on_wheel, add="+")
        self.root.bind_all("<Button-5>", _on_wheel, add="+")

    def actualizar_hora(self):
        if not self.root.winfo_exists():
            return
        if self.label_fecha is None or self.label_hora is None:
            self.reloj_job = self.root.after(1000, self.actualizar_hora)
            return
        ahora = datetime.now()
        self.label_fecha.config(text=ahora.strftime("%d/%m/%Y"))
        self.label_hora.config(text=ahora.strftime("%I:%M:%S %p").lower())
        self.reloj_job = self.root.after(1000, self.actualizar_hora)

    def _render_bitacora_items(self, parent, eventos):
        if not eventos:
            self._empty_state(parent, "Sin eventos recientes.", "La bitácora mostrará actividad del sistema.")
            return

        for evento in eventos:
            tipo = str(evento.get("tipo", "sistema")).strip().lower() or "sistema"
            tipo_label = {"bitacora": "ACCIÓN", "dashboard": "ACCIÓN", "error": "ERROR", "audio": "SISTEMA"}.get(tipo, tipo.upper())
            row = tk.Frame(parent, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
            row.pack(fill="x", pady=5)
            top = tk.Frame(row, bg=self.ui["surface_alt"])
            top.pack(fill="x", padx=12, pady=(10, 4))
            tk.Label(
                top,
                text=f"{evento.get('fecha', '--')} {formatear_hora_ampm_segundos(evento.get('hora', '--:--:--'))}",
                font=("Arial", 9, "bold"),
                bg=self.ui["surface_alt"],
                fg=self.ui["accent"],
            ).pack(side="left")
            tk.Label(
                top,
                text=tipo_label,
                font=("Arial", 8, "bold"),
                bg="#113454" if tipo_label != "ERROR" else "#3a1318",
                fg="#9ad9ff" if tipo_label != "ERROR" else "#fecaca",
                padx=8,
                pady=3,
            ).pack(side="left", padx=(8, 0))
            tk.Label(
                top,
                text=str(evento.get("modulo", "sistema")).upper(),
                font=("Arial", 9, "bold"),
                bg=self.ui["surface_alt"],
                fg=self.ui["text_dim"],
            ).pack(side="right")
            mensaje = tk.Label(
                row,
                text=self._truncate(evento.get("mensaje", ""), 220),
                font=("Arial", 10),
                bg=self.ui["surface_alt"],
                fg=self.ui["text"],
                wraplength=620,
                justify="left",
            )
            mensaje.pack(anchor="w", padx=12, pady=(0, 10))
            self._bind_wrap_to_parent(mensaje, row, pad=26, min_width=220)

    def _abrir_ventana_bitacora(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Bitácora")
        aplicar_geometria_relativa(ventana, self.root, rel_w=0.52, rel_h=0.62, min_w=640, min_h=520)
        ventana.configure(bg=self.ui["surface"])

        tk.Label(ventana, text="Bitácora", font=("Arial", 16, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=16, pady=(16, 8))
        host = tk.Frame(ventana, bg=self.ui["surface"])
        host.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        body = self._build_scroll_list(host)
        body.pack(fill="both", expand=True)

        logs = list(reversed(self._safe_list(leer_logs())[-24:]))
        self._render_bitacora_items(body.inner, logs)

    def _abrir_registro_rapido_bitacora(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Registro rápido en bitácora")
        aplicar_geometria_relativa(ventana, self.root, rel_w=0.34, rel_h=0.28, min_w=420, min_h=240)
        ventana.configure(bg=self.ui["surface"])

        tk.Label(
            ventana,
            text="Registro rápido en bitácora",
            font=("Arial", 16, "bold"),
            bg=self.ui["surface"],
            fg=self.ui["text"],
        ).pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(
            ventana,
            text="Escribe un evento breve. Se guardará en la bitácora real del sistema.",
            font=("Arial", 10),
            bg=self.ui["surface"],
            fg=self.ui["text_dim"],
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 10))

        entrada = tk.Text(ventana, height=5, font=("Arial", 11), bg=self.ui["bg_alt"], fg=self.ui["text"], insertbackground=self.ui["text"], relief="flat")
        entrada.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        acciones = tk.Frame(ventana, bg=self.ui["surface"])
        acciones.pack(fill="x", padx=16, pady=(0, 16))

        def _guardar():
            mensaje = entrada.get("1.0", "end").strip()
            if not mensaje:
                messagebox.showwarning("Bitácora", "Escribe un evento antes de guardarlo.", parent=ventana)
                return
            self._registrar_evento_rapido(mensaje)
            ventana.destroy()

        tk.Button(
            acciones,
            text="Guardar evento",
            font=("Arial", 10, "bold"),
            bg=self.ui["accent"],
            fg="#00111d",
            activebackground="#77e8ff",
            activeforeground="#00111d",
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            command=_guardar,
        ).pack(side="left")
        tk.Button(
            acciones,
            text="Cancelar",
            font=("Arial", 10),
            bg=self.ui["surface_alt"],
            fg=self.ui["text"],
            activebackground=self.ui["surface_soft"],
            activeforeground=self.ui["text"],
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            command=ventana.destroy,
        ).pack(side="left", padx=(8, 0))
        entrada.focus_set()

    def _abrir_ventana_sonidos(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Sonidos de alarma")
        aplicar_geometria_relativa(ventana, self.root, rel_w=0.40, rel_h=0.54, min_w=520, min_h=460)
        ventana.configure(bg=self.ui["surface"])

        tk.Label(ventana, text="Sonidos de alarma", font=("Arial", 16, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(
            ventana,
            text="Escoge el sonido principal del dashboard. 'Probar alarma' usará este sonido.",
            font=("Arial", 10),
            bg=self.ui["surface"],
            fg=self.ui["text_dim"],
        ).pack(anchor="w", padx=16, pady=(0, 10))

        contenedor = tk.Frame(ventana, bg=self.ui["surface"])
        contenedor.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        sonido_actual = normalizar_sonido_alerta(self.sonido_dashboard_id)
        seleccion = tk.StringVar(value=sonido_actual)

        for sonido_id, datos in SONIDOS_ALERTA.items():
            fila = tk.Frame(contenedor, bg=self.ui["bg_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
            fila.pack(fill="x", pady=4)
            tk.Radiobutton(
                fila,
                variable=seleccion,
                value=sonido_id,
                bg=self.ui["bg_alt"],
                activebackground=self.ui["bg_alt"],
                selectcolor=self.ui["surface"],
                highlightthickness=0,
            ).pack(side="left", padx=(10, 4))
            tk.Button(
                fila,
                text=datos["label"],
                font=("Arial", 11, "bold"),
                bg=self.ui["bg_alt"],
                fg=self.ui["text"],
                activebackground=self.ui["bg_alt"],
                activeforeground=self.ui["text"],
                relief="flat",
                bd=0,
                cursor="hand2",
                anchor="w",
                command=lambda sid=sonido_id: self._emitir_alerta_sonora(sid, incluir_timbre=False, detener_anterior=True),
            ).pack(side="left", padx=12, pady=10)
            tk.Button(
                fila,
                text="Escoger",
                font=("Arial", 10, "bold"),
                bg=self.ui["accent"],
                fg="#00111D",
                activebackground="#77e8ff",
                activeforeground="#00111D",
                relief="flat",
                command=lambda sid=sonido_id: self._seleccionar_sonido_dashboard(sid, seleccion),
            ).pack(side="right", padx=12, pady=8)

    def _seleccionar_sonido_dashboard(self, sonido_id, variable_ui=None):
        sonido_id = normalizar_sonido_alerta(sonido_id)
        self.sonido_dashboard_id = sonido_id
        guardar_sonido_dashboard(sonido_id)
        if variable_ui is not None:
            variable_ui.set(sonido_id)

    def _programar_revision_recordatorios(self):
        if not self.root.winfo_exists():
            return
        self._revisar_recordatorios_vencidos()
        self.recordatorios_job = self.root.after(1000, self._programar_revision_recordatorios)

    def _revisar_recordatorios_vencidos(self):
        ahora = datetime.now()
        hoy = ahora.strftime("%Y-%m-%d")
        marca_minuto = ahora.strftime("%Y-%m-%d %H:%M")
        recordatorios = cargar_recordatorios()
        alarmas = cargar_alarmas()
        cambios = False

        for item in recordatorios:
            fecha_recordatorio = item.get("fecha", "")
            repeticion = item.get("repeticion", "una_vez")
            if repeticion == "una_vez":
                if fecha_recordatorio != hoy:
                    continue
            else:
                if not fecha_recordatorio or fecha_recordatorio > hoy:
                    continue
            hora = item.get("hora", "")
            try:
                programado = datetime.strptime(f"{hoy} {hora}", "%Y-%m-%d %H:%M")
            except (KeyError, ValueError):
                continue
            if ahora < programado or item.get("disparado_en") == marca_minuto:
                continue
            if repeticion == "una_vez" and item.get("alerta_emitida"):
                continue
            if repeticion == "diaria" and item.get("ultimo_disparo_fecha") == hoy:
                continue

            hora_ampm = formatear_hora_ampm(hora)
            hora_actual_ampm = ahora.strftime("%I:%M %p").lower()
            mensaje = f"Recordatorio {hora_ampm} [{etiqueta_repeticion(item)}] activado a las {hora_actual_ampm}: {item.get('titulo', 'Sin título')}"
            if item.get("nota"):
                mensaje += f" | {item['nota']}"
            registrar_log("recordatorio", mensaje, "herramientas")
            item["disparado_en"] = marca_minuto
            item["ultimo_disparo_fecha"] = hoy
            if repeticion == "una_vez":
                item["alerta_emitida"] = True
            cambios = True
            self._emitir_alerta_sonora(item.get("sonido", SONIDO_ALERTA_DEFAULT), incluir_timbre=False)

        for item in alarmas:
            if not item.get("activa", True):
                continue
            repeticion = item.get("repeticion", "una_vez")
            if repeticion == "una_vez":
                if item.get("fecha", "") != hoy or item.get("alerta_emitida"):
                    continue
            else:
                if ahora.weekday() not in item.get("dias_semana", []):
                    continue
                if item.get("ultimo_disparo_fecha") == hoy:
                    continue
            hora = item.get("hora", "")
            try:
                programado = datetime.strptime(f"{hoy} {hora}", "%Y-%m-%d %H:%M")
            except (KeyError, ValueError):
                continue
            if ahora < programado or item.get("disparado_en") == marca_minuto:
                continue

            hora_ampm = formatear_hora_ampm(hora)
            hora_actual_ampm = ahora.strftime("%I:%M %p").lower()
            mensaje = f"Alarma {hora_ampm} [{etiqueta_repeticion(item)}] activada a las {hora_actual_ampm}: {item.get('titulo', 'Alarma')}"
            if item.get("nota"):
                mensaje += f" | {item['nota']}"
            registrar_log("alarma", mensaje, "herramientas")
            item["disparado_en"] = marca_minuto
            item["ultimo_disparo_fecha"] = hoy
            if repeticion == "una_vez":
                item["alerta_emitida"] = True
            cambios = True
            self._emitir_alerta_sonora(item.get("sonido", SONIDO_ALERTA_DEFAULT), incluir_timbre=True)

        if cambios:
            guardar_recordatorios(recordatorios)
            guardar_alarmas(alarmas)
            self._reconstruir_dashboard()

    def _emitir_alerta_sonora(self, sonido_id=None, incluir_timbre=False, detener_anterior=False):
        threading.Thread(
            target=self._reproducir_alerta_sonora,
            args=(sonido_id, detener_anterior),
            daemon=True,
        ).start()
        if incluir_timbre:
            try:
                self.root.bell()
                self.root.after(180, self.root.bell)
                self.root.after(360, self.root.bell)
            except Exception:
                pass
            try:
                if self.app_root is not None:
                    self.app_root.bell()
            except Exception:
                pass

    def _detener_audio_preview(self):
        with self._audio_preview_lock:
            proceso = self._audio_preview_process
            self._audio_preview_process = None
        if proceso is None:
            return
        try:
            if proceso.poll() is None:
                proceso.terminate()
                try:
                    proceso.wait(timeout=0.4)
                except Exception:
                    proceso.kill()
        except Exception:
            pass

    def _reproducir_alerta_sonora(self, sonido_id=None, detener_anterior=False):
        sonido_id = normalizar_sonido_alerta(sonido_id or self.sonido_dashboard_id or SONIDO_ALERTA_DEFAULT)
        ruta_sonido = obtener_ruta_sonido_alerta(sonido_id)
        if not ruta_sonido.exists():
            registrar_log("audio", f"No existe el archivo de alerta: {ruta_sonido}", "dashboard")
            return

        if detener_anterior:
            self._detener_audio_preview()

        rutas_audio = []
        pw_play = shutil.which("pw-play")
        if pw_play:
            rutas_audio.append([pw_play, str(ruta_sonido)])
        if ruta_sonido.suffix.lower() == ".wav":
            aplay = shutil.which("aplay")
            if aplay:
                rutas_audio.append([aplay, "-q", str(ruta_sonido)])

        for comando in rutas_audio:
            ejecutable = comando[0]
            if not Path(ejecutable).exists():
                continue
            try:
                proceso = subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if detener_anterior:
                    with self._audio_preview_lock:
                        self._audio_preview_process = proceso
                registrar_log("audio", f"Alerta sonora lanzada con {Path(ejecutable).name}", "dashboard")
                return
            except Exception as exc:
                registrar_log("audio", f"Excepción con {Path(ejecutable).name}: {exc}", "dashboard")

        try:
            canberra = shutil.which("canberra-gtk-play")
            if canberra:
                proceso = subprocess.Popen([canberra, "-i", "bell"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if detener_anterior:
                    with self._audio_preview_lock:
                        self._audio_preview_process = proceso
                registrar_log("audio", "Alerta sonora lanzada con canberra-gtk-play", "dashboard")
        except Exception:
            registrar_log("audio", "No se pudo reproducir canberra-gtk-play", "dashboard")

    def _registrar_evento_rapido(self, mensaje):
        mensaje = str(mensaje or "").strip()
        if not mensaje:
            return
        registrar_log("bitacora", mensaje, "dashboard")
        self._reconstruir_dashboard()

    def _sincronizar_datos(self):
        registrar_log("dashboard", "Sincronización local solicitada desde barra inferior.", "dashboard")
        try:
            if self.license_client.is_authenticated():
                self.license_client.sync_license()
                registrar_log("dashboard", "Licencia SaaS sincronizada desde barra inferior.", "licencias")
        except Exception as exc:
            registrar_log("warning", f"No se pudo sincronizar licencia SaaS: {exc}", "licencias")
        try:
            self.update_checker.check_in_background(on_complete=lambda _state: self.root.after(0, self._refrescar_estado_sin_reconstruir))
        except Exception as exc:
            registrar_log("warning", f"No se pudo revisar updates en sincronización: {exc}", "updates")
        self._reconstruir_dashboard()

    def _check_updates_soft_startup(self):
        try:
            self.update_checker.check_in_background(on_complete=lambda _state: self.root.after(0, self._refrescar_estado_sin_reconstruir))
        except Exception as exc:
            registrar_log("warning", f"No se pudo iniciar revisión suave de updates: {exc}", "updates")

    def _inventory_status(self, items, inventory_alerts):
        total_items = len(items)
        critical_item_ids = {str(alerta.get("item_id", "")).strip() for alerta in inventory_alerts if str(alerta.get("item_id", "")).strip()}
        critical_count = len(critical_item_ids)
        if total_items <= 0:
            return {"value": "Sin datos", "subtitle": "Inventario vacío", "percent": None, "critical_count": 0}
        if critical_count <= 0:
            return {"value": "0", "subtitle": "Sin elementos críticos", "percent": None, "critical_count": 0}
        return {
            "value": str(critical_count),
            "subtitle": f"{critical_count} elemento(s) críticos de {total_items} registrados",
            "percent": None,
            "critical_count": critical_count,
        }

    def _health_status(self, alerts, inventory_alerts, personas):
        profiles = [persona for persona in personas if isinstance(persona, dict)]
        alerts_count = self._count_health_alerts(alerts, inventory_alerts)
        if not profiles:
            return {"value": str(alerts_count), "subtitle": "Sin perfiles para evaluar cobertura", "percent": None, "alerts": alerts_count}
        percent = max(0, 100 - int((alerts_count / max(1, len(profiles))) * 100))
        return {
            "value": str(alerts_count),
            "subtitle": f"{len(profiles)} perfil(es) monitoreados",
            "percent": percent,
            "alerts": alerts_count,
        }

    def _to_float(self, value):
        try:
            return float(str(value).strip().replace(",", "."))
        except Exception:
            return None

    def _format_percent(self, percent):
        if percent is None:
            return "--"
        return f"{max(0, min(100, int(round(percent))))}%"

    def _count_health_alerts(self, alerts, inventory_alerts):
        words = ("med", "salud", "hemorrag", "emergen", "botiqu", "farmac", "caduc")
        total = 0
        for alerta in alerts:
            text = " ".join(str(alerta.get(key, "")).lower() for key in ("tipo", "mensaje", "origen"))
            if any(word in text for word in words):
                total += 1
        for alerta in inventory_alerts:
            text = " ".join(str(alerta.get(key, "")).lower() for key in ("categoria", "mensaje"))
            if any(word in text for word in words):
                total += 1
        return total

    def _climate_fallback(self):
        return {"value": "Sin sensor", "subtitle": "No hay datos climáticos reales", "percent": None}

    def _operational_state(self, alerts, emergency_state=None):
        if isinstance(emergency_state, dict) and emergency_state.get("activo"):
            return {
                "label": "EMERGENCIA",
                "subtitle": str(emergency_state.get("resumen", "Modo emergencia activo")).strip() or "Modo emergencia activo",
                "percent": 0,
                "color": self.ui["danger"],
            }
        critical = sum(1 for alerta in alerts if self._alert_level(alerta)["label"] == "CRÍTICO")
        warning = sum(1 for alerta in alerts if self._alert_level(alerta)["label"] == "ADVERTENCIA")
        if critical:
            total = max(1, len(alerts))
            percent = max(0, 100 - int(((critical * 2) + warning) / (total * 2) * 100))
            return {"label": "INESTABLE", "subtitle": f"{critical} alerta(s) críticas", "percent": percent, "color": self.ui["danger"]}
        if warning:
            total = max(1, len(alerts))
            percent = max(0, 100 - int((warning / total) * 100))
            return {"label": "VIGILANCIA", "subtitle": f"{warning} alerta(s) en seguimiento", "percent": percent, "color": self.ui["warning"]}
        return {"label": "ESTABLE", "subtitle": "Sin incidencias críticas", "percent": 100, "color": self.ui["success"]}

    def _last_backup_label(self):
        paths = get_paths()
        candidates = []
        for path in [
            paths.memory_json,
            paths.offline_learning_dir / "metadata" / "learning_state.json",
            paths.offline_library_dir / "metadata" / "library_state.json",
        ]:
            if path.exists():
                candidates.append(path.stat().st_mtime)
        if not candidates:
            return "Sin registro"
        return datetime.fromtimestamp(max(candidates)).strftime("%d/%m %H:%M")

    def _last_sync_info(self, logs):
        for item in logs:
            mensaje = str(item.get("mensaje", "")).lower()
            if "sincron" not in mensaje and "sync" not in mensaje:
                continue
            fecha = item.get("fecha", "")
            hora = item.get("hora", "")
            try:
                stamp = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M:%S")
            except Exception:
                stamp = None
            label = f"{fecha} {hora}".strip() or "Sin registro"
            return {"label": label, "datetime": stamp}
        return {"label": "Sin registro", "datetime": None}

    def _local_network_status(self):
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip and not ip.startswith("127."):
                return True, ip
        except Exception:
            pass
        return False, "No detectada"

    def _internet_status(self):
        try:
            with socket.create_connection(("1.1.1.1", 53), timeout=0.35):
                return True, "Disponible"
        except OSError:
            return False, "No disponible"
        except Exception:
            return None, "No verificado"

    def _connectivity_status(self, reader_state, logs):
        internet_ok, internet_label = self._internet_status()
        lan_ok, lan_detail = self._local_network_status()
        backend_ok = reader_state.get("status") == "lector_activo"
        sync_info = self._last_sync_info(logs)
        sync_state = "No disponible aún"
        if sync_info["datetime"] is not None:
            age_hours = (datetime.now() - sync_info["datetime"]).total_seconds() / 3600.0
            sync_state = "Reciente" if age_hours <= 24 else "Pendiente"
        elif internet_ok:
            sync_state = "Pendiente"
        if internet_ok is True and lan_ok:
            color = self.ui["success"]
        elif internet_ok is False and not lan_ok:
            color = self.ui["danger"]
        else:
            color = self.ui["warning"]

        value = "Internet disponible" if internet_ok is True else ("Sin internet" if internet_ok is False else "Estado no verificado")
        details = [
            f"Red local: {'Activa' if lan_ok else 'No activa'}",
            f"Sincronización: {sync_state}",
            f"Backend local: {'Alcanzable' if backend_ok else 'No alcanzable'}",
        ]
        subtitle = f"LAN {lan_detail} · última sync {sync_info['label']}"
        summary = f"{value} · LAN {'activa' if lan_ok else 'no activa'} · Sync {sync_state.lower()}"
        return {
            "value": value,
            "subtitle": subtitle,
            "percent": None,
            "color": color,
            "summary": summary,
            "details": details,
            "internet_available": internet_ok,
            "lan_active": lan_ok,
            "sync_state": sync_state,
            "last_sync": sync_info["label"],
            "backend_available": backend_ok,
        }

    def _titulo_plan(self, plan):
        return str(plan.get("datos_generales", {}).get("nombre_del_plan", "")).strip() or "Plan sin nombre"

    def _abrir_checklist_rapida(self):
        registrar_log("dashboard", "Checklist rápida abierta desde acciones.", "dashboard")
        VentanaBlocNotas(self.root, self.root)

    def _abrir_centro_comunicaciones(self):
        registrar_log("dashboard", "Centro de comunicaciones abierto desde acciones.", "dashboard")
        VentanaComunicaciones(self.root, self.root)

    def _activar_plan(self, plan):
        nombre = self._titulo_plan(plan)
        mensaje = f"Protocolo activado desde Centro de Control: {nombre}"
        registrar_log("bitacora", mensaje, "planes")
        self._reconstruir_dashboard()

    def _abrir_selector_protocolos(self):
        planes = self._safe_list(listar_planes())
        if not planes:
            messagebox.showinfo("Protocolos", "Aún no tienes planes registrados.", parent=self.root)
            return
        ventana = tk.Toplevel(self.root)
        ventana.title("Protocolos disponibles")
        aplicar_geometria_relativa(ventana, self.root, rel_w=0.42, rel_h=0.48, min_w=520, min_h=420)
        ventana.configure(bg=self.ui["surface"])
        tk.Label(ventana, text="Protocolos disponibles", font=("Arial", 16, "bold"), bg=self.ui["surface"], fg=self.ui["text"]).pack(anchor="w", padx=16, pady=(16, 8))
        host = self._build_scroll_list(ventana)
        host.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        for plan in planes:
            row = tk.Frame(host.inner, bg=self.ui["surface_alt"], highlightthickness=1, highlightbackground=self.ui["border"])
            row.pack(fill="x", pady=5)
            tk.Label(row, text=self._titulo_plan(plan), font=("Arial", 11, "bold"), bg=self.ui["surface_alt"], fg=self.ui["text"]).pack(anchor="w", padx=12, pady=(10, 4))
            escenario = str(plan.get("datos_generales", {}).get("escenario_principal", "")).strip()
            if escenario:
                tk.Label(row, text=escenario, font=("Arial", 9), bg=self.ui["surface_alt"], fg=self.ui["text_dim"], wraplength=360, justify="left").pack(anchor="w", padx=12)
            acciones = tk.Frame(row, bg=self.ui["surface_alt"])
            acciones.pack(fill="x", padx=12, pady=(8, 10))
            boton_abrir = tk.Button(acciones, text="Abrir", font=("Arial", 9, "bold"), bg=self.ui["muted"], fg=self.ui["text"], relief="flat", command=lambda: None)
            boton_abrir.pack(side="left")
            self._bind_double_click_action(boton_abrir, lambda: abrir_planes(self.app_root, self.root))
            boton_ejecutar = tk.Button(acciones, text="Ejecutar", font=("Arial", 9, "bold"), bg=self.ui["warning"], fg="#1a1200", relief="flat", command=lambda: None)
            boton_ejecutar.pack(side="left", padx=(8, 0))
            self._bind_double_click_action(boton_ejecutar, lambda p=plan: self._activar_plan_desde_dialogo(p, ventana))

    def _activar_plan_desde_dialogo(self, plan, ventana):
        self._activar_plan(plan)
        try:
            ventana.destroy()
        except Exception:
            pass

    def _connectivity_label(self, reader_state):
        if reader_state.get("status") == "lector_activo":
            return "Local + lector offline"
        try:
            socket.gethostbyname("localhost")
            return "Local operativa"
        except Exception:
            return "Limitada"

    def _build_system_suggestions(self, status):
        suggestions = []
        if status["inventory_critical"] > 0:
            suggestions.append({
                "icon": "📦",
                "title": "Revisar inventario crítico",
                "reason": f"Hay {status['inventory_critical']} elemento(s) en estado crítico o bajo.",
                "module": "Inventario",
            })
        water_days = status["water_status"].get("dias_autonomia")
        if water_days is None and status["agua_litros"] <= 0:
            suggestions.append({
                "icon": "💧",
                "title": "Registrar o reabastecer agua",
                "reason": "No hay reservas hídricas suficientes para calcular autonomía real.",
                "module": "Inventario / Perfiles",
            })
        elif water_days is not None and water_days < 7:
            suggestions.append({
                "icon": "💧",
                "title": "Reabastecer agua",
                "reason": status["water_status"].get("subtitle", "La cobertura de agua es baja."),
                "module": "Inventario",
            })

        caducidades = [
            alerta for alerta in status["inventory_alerts"]
            if any(word in " ".join(str(alerta.get(k, "")).lower() for k in ("categoria", "mensaje")) for word in ("med", "caduc", "farmac"))
        ]
        if caducidades:
            suggestions.append({
                "icon": "💊",
                "title": "Revisar medicamentos por vencer",
                "reason": f"Se detectaron {len(caducidades)} alerta(s) vinculadas con salud o caducidad.",
                "module": "Inventario",
            })

        if status["learning_installed"] and status["learning_progress"] < 100:
            suggestions.append({
                "icon": "🎓",
                "title": "Continuar aprendizaje pendiente",
                "reason": f"El progreso offline actual está en {status['learning_progress']:.1f}%.",
                "module": "Aprendizaje",
            })
        if not status["planes"]:
            suggestions.append({
                "icon": "📋",
                "title": "Revisar planes de emergencia",
                "reason": "No hay planes registrados o activos en el sistema.",
                "module": "Planes",
            })
        if status["connectivity_status"]["internet_available"] is True and status["connectivity_status"]["sync_state"] != "Reciente":
            suggestions.append({
                "icon": "🔄",
                "title": "Sincronizar datos",
                "reason": "Hay conectividad disponible y no se detecta una sincronización reciente.",
                "module": "Barra inferior",
            })
        if status["mapa_activo"].get("name"):
            suggestions.append({
                "icon": "🗺",
                "title": "Revisar rutas y mapa activo",
                "reason": f"El mapa operativo actual es {status['location_text']}. Conviene validar rutas y zonas seguras.",
                "module": "Mapa",
            })
        else:
            suggestions.append({
                "icon": "🗺",
                "title": "Abrir mapa operativo",
                "reason": "No hay un mapa activo seleccionado en este momento.",
                "module": "Mapa",
            })

        return suggestions

    def _truncate(self, text, max_len):
        text = str(text or "").strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1].rstrip() + "…"

    def _safe_list(self, value):
        return value if isinstance(value, list) else []

    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def _crear_fallback_error_ui(self, exc):
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass
        self.root.configure(bg="#0b1020")
        wrap = tk.Frame(self.root, bg="#0b1020")
        wrap.pack(fill="both", expand=True, padx=24, pady=24)
        box = tk.Frame(wrap, bg="#151b2f", highlightthickness=1, highlightbackground="#7f1d1d")
        box.pack(fill="both", expand=True)
        tk.Label(box, text="Dashboard no pudo cargarse", font=("Arial", 22, "bold"), bg="#151b2f", fg="#fee2e2").pack(anchor="w", padx=18, pady=(18, 8))
        tk.Label(
            box,
            text="Se activó un modo de recuperación para evitar que la aplicación se cierre. Puedes abrir módulos básicos mientras se corrige el error.",
            font=("Arial", 11),
            bg="#151b2f",
            fg="#cbd5e1",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=18)
        tk.Label(box, text=f"Error: {exc}", font=("Arial", 11, "bold"), bg="#151b2f", fg="#fca5a5", wraplength=760, justify="left").pack(anchor="w", padx=18, pady=(12, 8))
        detail = tk.Text(box, bg="#0b1020", fg="#dbeafe", relief="flat", height=14, wrap="word")
        detail.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        detail.insert("1.0", traceback.format_exc())
        detail.configure(state="disabled")
        actions = tk.Frame(box, bg="#151b2f")
        actions.pack(fill="x", padx=18, pady=(0, 18))
        tk.Button(actions, text="Reintentar", font=("Arial", 10, "bold"), bg="#38bdf8", fg="#00111d", relief="flat", command=self._recargar_dashboard).pack(side="left", padx=(0, 10))
        tk.Button(
            actions,
            text="Consulta",
            font=("Arial", 10, "bold"),
            bg="#1f2937",
            fg="white",
            relief="flat",
            command=lambda: self._permitir_acceso_modulo("consulta", "Consulta") and abrir_consulta(self.app_root, self.root),
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            actions,
            text="Mapa",
            font=("Arial", 10, "bold"),
            bg="#1f2937",
            fg="white",
            relief="flat",
            command=lambda: self._permitir_acceso_modulo("mapa", "Mapa") and abrir_mapa(self.app_root, self.root),
        ).pack(side="left")

    def _mostrar_error_en_panel(self, exc):
        if not hasattr(self, "grid_panels"):
            self._crear_fallback_error_ui(exc)
            return
        for container in (getattr(self, "cards_row", None), getattr(self, "grid_panels", None), getattr(self, "modules_row", None)):
            if container is None:
                continue
            for widget in container.winfo_children():
                try:
                    widget.destroy()
                except Exception:
                    pass
        panel = tk.Frame(self.grid_panels, bg="#2a0c11", highlightthickness=1, highlightbackground="#7f1d1d")
        panel.grid(row=0, column=0, columnspan=3, sticky="nsew")
        tk.Label(panel, text="Error al refrescar el dashboard", font=("Arial", 18, "bold"), bg="#2a0c11", fg="#fee2e2").pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(panel, text=str(exc), font=("Arial", 11), bg="#2a0c11", fg="#fecaca", wraplength=1080, justify="left").pack(anchor="w", padx=16)
        tk.Button(panel, text="Reintentar", font=("Arial", 10, "bold"), bg="#38bdf8", fg="#00111d", relief="flat", command=self._reconstruir_dashboard).pack(anchor="w", padx=16, pady=(14, 16))

    def _recargar_dashboard(self):
        if self._focus_refresh_job:
            try:
                self.root.after_cancel(self._focus_refresh_job)
            except Exception:
                pass
            self._focus_refresh_job = None
        if self.reloj_job:
            try:
                self.root.after_cancel(self.reloj_job)
            except Exception:
                pass
            self.reloj_job = None
        if self.recordatorios_job:
            try:
                self.root.after_cancel(self.recordatorios_job)
            except Exception:
                pass
            self.recordatorios_job = None

        self.config = cargar_config()
        registrar_todos(self.app_root, self.config, self.root)
        self._module_meta = self._build_module_meta()
        self._wrap_jobs = []
        self.status_left = None
        self.status_right = None
        for widget in self.root.winfo_children():
            widget.destroy()
        self.crear_ui()

    def _cerrar_dashboard(self):
        self._detener_audio_preview()
        if self._focus_refresh_job:
            try:
                self.root.after_cancel(self._focus_refresh_job)
            except Exception:
                pass
            self._focus_refresh_job = None
        if self._wrap_refresh_job:
            try:
                self.root.after_cancel(self._wrap_refresh_job)
            except Exception:
                pass
            self._wrap_refresh_job = None
        if self.reloj_job:
            try:
                self.root.after_cancel(self.reloj_job)
            except Exception:
                pass
            self.reloj_job = None
        if self.recordatorios_job:
            try:
                self.root.after_cancel(self.recordatorios_job)
            except Exception:
                pass
            self.recordatorios_job = None
        try:
            self.root.destroy()
        except Exception:
            pass
        if self.app_root is not self.root:
            try:
                self.app_root.quit()
            except Exception:
                pass
            try:
                self.app_root.destroy()
            except Exception:
                pass

    def _al_recuperar_foco(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if not self.root.winfo_exists():
            return
        if self._refresh_pending:
            return
        self._refresh_pending = True

        def _run_refresh():
            self._focus_refresh_job = None
            self._refresh_pending = False
            if not self.root.winfo_exists():
                return
            try:
                elapsed = monotonic() - self._last_dashboard_refresh
                if elapsed >= 12.0:
                    self._reconstruir_dashboard()
                else:
                    self._refrescar_estado_sin_reconstruir()
            except Exception:
                self._reconstruir_dashboard()

        self._focus_refresh_job = self.root.after(80, _run_refresh)
