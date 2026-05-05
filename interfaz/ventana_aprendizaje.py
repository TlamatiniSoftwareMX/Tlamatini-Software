import threading
import tkinter as tk
from queue import Empty, Queue
from tkinter import messagebox, ttk

from core.aprendizaje_offline import (
    DownloadCancelledError,
    continue_course,
    delete_course,
    download_course,
    list_installed,
    load_catalog,
    load_state,
    set_favorite,
)
from core.logs import registrar_log
from core.texto import normalizar_texto
from core.window_geometry import aplicar_geometria_relativa, crear_contenedor_scrollable
from interfaz.visor_curso import VentanaCurso


STATUS_LABELS = {
    "no_descargado": "Disponible",
    "en_cola": "En cola",
    "descargando": "Descargando",
    "instalando": "Instalando",
    "verificando": "Verificando",
    "listo": "Listo para estudiar",
    "instalado": "Instalado",
    "cancelado": "Cancelado",
    "error": "Error",
}

PALETA = {
    "bg": "#07131f",
    "bg_alt": "#0c1f31",
    "panel": "#11263d",
    "panel_soft": "#18334f",
    "panel_soft_alt": "#214266",
    "card": "#f8fbff",
    "card_alt": "#edf4fb",
    "border": "#2b4d70",
    "border_soft": "#d7e3ee",
    "text": "#edf6ff",
    "text_dim": "#a5bfd9",
    "card_text": "#132235",
    "card_dim": "#4d6278",
    "accent": "#1d4ed8",
    "accent_alt": "#0f766e",
    "gold": "#d4a017",
    "ok": "#169c72",
    "warn": "#c97911",
    "danger": "#b91c1c",
    "purple": "#6d28d9",
}


def _label_status(status: str) -> str:
    return STATUS_LABELS.get(status or "", status or "-")


def _safe_float(value) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _fmt_percent(value) -> str:
    return f"{_safe_float(value):.1f}%"


def _lesson_count(item: dict) -> int:
    total = int(item.get("total_lessons", 0) or item.get("lesson_count", 0) or 0)
    if total:
        return total
    count = 0
    for module in item.get("modules", []) or []:
        count += len(module.get("lessons", []) or [])
    return count


def _course_eta(item: dict) -> str:
    lessons = max(1, _lesson_count(item))
    minutes = lessons * 12
    if minutes < 60:
        return f"{minutes} min aprox."
    hours = minutes // 60
    rem = minutes % 60
    if rem:
        return f"{hours} h {rem} min aprox."
    return f"{hours} h aprox."


def _course_state_hint(item: dict) -> str:
    progress = _safe_float(item.get("progress_percent", 0.0))
    status = str(item.get("status", "") or "")
    if progress >= 100.0:
        return "Curso terminado"
    if progress > 0.0:
        return "En progreso"
    if status in {"listo", "instalado"}:
        return "Listo para empezar"
    if status in {"descargando", "instalando", "en_cola"}:
        return "Preparando contenido"
    return "Disponible para descargar"


def _motivation_line(progress: float) -> str:
    if progress >= 100.0:
        return "Curso completado. Puedes repasarlo o avanzar al siguiente."
    if progress >= 70.0:
        return "Ya casi terminas. Mantén el ritmo y cierra el curso."
    if progress >= 35.0:
        return "Vas a mitad de camino. Continúa desde tu última lección."
    if progress > 0.0:
        return "Ya comenzaste. Retomar ahora te será más fácil."
    return "Elige un curso y avanza por módulos con una ruta clara."


class VentanaAprendizaje:
    def __init__(self, root):
        self.root = root
        self.root.title("TLAMATINI - Aprendizaje")
        self.root.protocol("WM_DELETE_WINDOW", self._close_window)
        self.root.configure(bg=PALETA["bg"])
        self.root.minsize(1500, 920)
        aplicar_geometria_relativa(self.root, self.root.master, rel_w=0.96, rel_h=0.94, min_w=1500, min_h=920)

        self.queue = Queue()
        self.current_worker = None
        self.worker_cancel_event = None
        self.poll_after_id = None
        self.geometry_refresh_job = None
        self.is_closing = False
        self.course_viewer = None

        self.catalog_items = []
        self.installed_items = []
        self.selected_course_id = ""
        self.active_download_course_id = ""

        self.var_catalog_search = tk.StringVar()
        self.var_library_search = tk.StringVar()
        self.var_filter_category = tk.StringVar(value="Todas")
        self.var_filter_language = tk.StringVar(value="Todos")
        self.var_filter_level = tk.StringVar(value="Todos")
        self.var_filter_state = tk.StringVar(value="Todos")
        self.var_status = tk.StringVar(value="Aprendizaje listo para explorar.")
        self.var_download_meta = tk.StringVar(value="Sin descargas activas.")
        self.var_download_activity = tk.StringVar(value="Selecciona un curso para empezar a estudiar offline.")
        self.var_progress = tk.DoubleVar(value=0.0)
        self.var_overview_title = tk.StringVar(value="Tu espacio de aprendizaje offline")
        self.var_overview_body = tk.StringVar(value="Explora contenidos, descarga lo necesario y retoma exactamente donde te quedaste.")
        self.var_continue_summary = tk.StringVar(value="Todavía no hay una sesión reciente.")
        self.var_recommendation = tk.StringVar(value="Descarga un curso para ver recomendaciones personalizadas.")

        self.catalog_cards = {}
        self.library_cards = {}
        self.catalog_search_combo = None
        self.category_combo = None
        self.language_combo = None
        self.level_combo = None
        self.state_combo = None
        self.catalog_cards_container = None
        self.library_cards_container = None
        self.course_summary_text = None
        self.course_summary_progress = None
        self.hero_progress = None
        self.hero_continue_btn = None
        self.hero_recent_btn = None
        self.btn_primary_download = None
        self.btn_primary_continue = None
        self.btn_primary_open = None
        self.btn_primary_favorite = None
        self.btn_primary_delete = None
        self.stats_container = None
        self.categories_container = None
        self.recommendations_container = None

        self._build_ui()
        self.root.bind("<FocusIn>", self._al_recuperar_foco)
        self.root.bind("<Configure>", self._programar_reajuste_geometria)
        self._refresh_all()
        self._poll_queue()

    def _log(self, message: str):
        registrar_log("ui", message, "aprendizaje")

    def _root_alive(self) -> bool:
        try:
            return not self.is_closing and bool(self.root.winfo_exists())
        except Exception:
            return False

    def _show_warning(self, title: str, message: str):
        self._log(f"Advertencia UI: {title}: {message}")
        if self._root_alive():
            messagebox.showwarning(title, message, parent=self.root)

    def _show_error(self, title: str, message: str):
        self._log(f"Error UI: {title}: {message}")
        if self._root_alive():
            messagebox.showerror(title, message, parent=self.root)

    def _build_ui(self):
        shell = tk.Frame(self.root, bg=PALETA["bg"])
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg=PALETA["bg"])
        header.pack(fill="x", padx=24, pady=(18, 10))
        tk.Label(header, text="Aprendizaje", bg=PALETA["bg"], fg=PALETA["text"], font=("Arial", 31, "bold")).pack(anchor="w")
        tk.Label(
            header,
            text="Una portada educativa clara para explorar, estudiar, retomar y ver tu avance sin sentir que usas una herramienta técnica.",
            bg=PALETA["bg"],
            fg=PALETA["text_dim"],
            font=("Arial", 12),
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        self._build_main(shell)
        self._build_overview(shell)
        self._build_controls(shell)
        self._build_footer(shell)

    def _build_overview(self, parent):
        wrap = tk.Frame(parent, bg=PALETA["bg"])
        wrap.pack(fill="x", padx=24, pady=(0, 8))
        wrap.grid_columnconfigure(0, weight=2)
        wrap.grid_columnconfigure(1, weight=1)

        hero = tk.Frame(wrap, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["border"])
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        hero.grid_columnconfigure(0, weight=1)
        left = tk.Frame(hero, bg=PALETA["panel"])
        left.grid(row=0, column=0, sticky="nsew", padx=18, pady=16)
        tk.Label(left, textvariable=self.var_overview_title, bg=PALETA["panel"], fg=PALETA["text"], font=("Arial", 19, "bold"), anchor="w", justify="left").pack(fill="x")
        tk.Label(left, textvariable=self.var_overview_body, bg=PALETA["panel"], fg=PALETA["text_dim"], font=("Arial", 10), anchor="w", justify="left", wraplength=700).pack(fill="x", pady=(6, 10))
        self.hero_progress = ttk.Progressbar(left, variable=self.var_progress, maximum=100)
        self.hero_progress.pack(fill="x")
        tk.Label(left, textvariable=self.var_status, bg=PALETA["panel"], fg="#bfdbfe", anchor="w").pack(fill="x", pady=(6, 0))
        tk.Label(left, textvariable=self.var_download_meta, bg=PALETA["panel"], fg=PALETA["text"], anchor="w").pack(fill="x", pady=(2, 0))
        tk.Label(left, textvariable=self.var_download_activity, bg=PALETA["panel"], fg="#86efac", anchor="w", justify="left", wraplength=720).pack(fill="x", pady=(2, 8))

        actions = tk.Frame(left, bg=PALETA["panel"])
        actions.pack(fill="x", pady=(4, 0))
        self.hero_continue_btn = self._action_button(actions, "Continuar donde me quedé", self._continue_recent_course, PALETA["accent_alt"])
        self.hero_continue_btn.pack(side="left")
        self.hero_recent_btn = self._action_button(actions, "Abrir curso actual", self._open_recent_course, PALETA["accent"])
        self.hero_recent_btn.pack(side="left", padx=(8, 0))
        self._action_button(actions, "Explorar catálogo", self._reset_to_catalog, PALETA["panel_soft_alt"]).pack(side="left", padx=(8, 0))

        aside = tk.Frame(wrap, bg=PALETA["panel_soft"], highlightthickness=1, highlightbackground=PALETA["border"])
        aside.grid(row=0, column=1, sticky="nsew")
        tk.Label(aside, text="Continuidad de estudio", bg=PALETA["panel_soft"], fg=PALETA["text"], font=("Arial", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(aside, textvariable=self.var_continue_summary, bg=PALETA["panel_soft"], fg=PALETA["text_dim"], justify="left", wraplength=360).pack(anchor="w", padx=16)
        tk.Label(aside, text="Sugerencia actual", bg=PALETA["panel_soft"], fg="#bfdbfe", font=("Arial", 10, "bold")).pack(anchor="w", padx=16, pady=(10, 4))
        tk.Label(aside, textvariable=self.var_recommendation, bg=PALETA["panel_soft"], fg=PALETA["text"], justify="left", wraplength=360).pack(anchor="w", padx=16)

        stats_shell = tk.Frame(aside, bg=PALETA["panel_soft"])
        stats_shell.pack(fill="x", padx=12, pady=(12, 12))
        self.stats_container = stats_shell

    def _build_controls(self, parent):
        rail = tk.Frame(parent, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["border"])
        rail.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(rail, text="Áreas educativas y filtros", bg=PALETA["panel"], fg=PALETA["text"], font=("Arial", 13, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        tk.Label(
            rail,
            text="Usa categorías visibles y filtros simples para llegar rápido al catálogo y a tus cursos descargados.",
            bg=PALETA["panel"],
            fg=PALETA["text_dim"],
            justify="left",
        ).pack(anchor="w", padx=16)
        container = tk.Frame(rail, bg=PALETA["panel"])
        container.pack(fill="x", padx=12, pady=(8, 10))
        self.categories_container = container
        self._build_filters(rail)

    def _build_filters(self, parent):
        bar = tk.Frame(parent, bg=PALETA["panel"])
        bar.pack(fill="x", padx=8, pady=(0, 10))

        fields = [
            ("Categoría", "category_combo", self.var_filter_category, ["Todas"], 18),
            ("Idioma", "language_combo", self.var_filter_language, ["Todos"], 12),
            ("Nivel", "level_combo", self.var_filter_level, ["Todos"], 12),
            ("Estado", "state_combo", self.var_filter_state, ["Todos", "Solo descargados", "Solo disponibles", "En progreso", "Favoritos"], 16),
        ]
        for idx, (label, attr, variable, values, width) in enumerate(fields):
            tk.Label(bar, text=label, bg=PALETA["panel"], fg=PALETA["text"]).grid(row=0, column=idx * 2, sticky="w", padx=(14 if idx == 0 else 8, 6), pady=8)
            combo = ttk.Combobox(bar, textvariable=variable, state="readonly", width=width, values=values)
            combo.grid(row=0, column=(idx * 2) + 1, sticky="w", padx=(0, 8), pady=8)
            combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())
            setattr(self, attr, combo)

        tip = tk.Label(
            bar,
            text="Filtra por tema, idioma, nivel o situación de estudio para encontrar rápido qué seguir aprendiendo.",
            bg=PALETA["panel"],
            fg=PALETA["text_dim"],
            justify="left",
            wraplength=420,
        )
        tip.grid(row=0, column=8, sticky="e", padx=14, pady=8)
        bar.grid_columnconfigure(8, weight=1)

    def _build_main(self, parent):
        main = tk.PanedWindow(parent, orient="horizontal", sashrelief="flat", bd=0, bg=PALETA["bg"])
        main.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        main.configure(height=700)
        self.main_paned = main

        col_a = tk.Frame(main, bg=PALETA["bg"])
        col_b = tk.Frame(main, bg=PALETA["bg"])
        col_c = tk.Frame(main, bg=PALETA["bg"])
        uniform_minsize = 430
        main.add(col_a, minsize=uniform_minsize)
        main.add(col_b, minsize=uniform_minsize)
        main.add(col_c, minsize=uniform_minsize)

        self._build_catalog_column(col_a)
        self._build_library_column(col_b)
        self._build_context_column(col_c)
        self.root.after_idle(self._balance_main_sections)

    def _balance_main_sections(self):
        try:
            if not getattr(self, "main_paned", None) or not self.main_paned.winfo_exists():
                return
            self.main_paned.update_idletasks()
            width = self.main_paned.winfo_width()
            if width <= 0:
                return
            third = max(1, width // 3)
            self.main_paned.sash_place(0, third, 0)
            self.main_paned.sash_place(1, third * 2, 0)
        except Exception as exc:
            self._log(f"Advertencia UI: no se pudo equilibrar el panel principal de aprendizaje: {exc}")

    def _build_catalog_column(self, parent):
        card = self._section_card(parent, "A. Explorar cursos", "Catálogo didáctico con tarjetas amplias, estado visible y acceso directo para descargar.")
        card.pack(fill="both", expand=True)
        header = tk.Frame(card.body, bg=PALETA["panel"])
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="Tema", bg=PALETA["panel"], fg=PALETA["text"]).pack(side="left")
        combo = ttk.Combobox(header, textvariable=self.var_catalog_search, state="normal", values=["Todos los temas"], font=("Arial", 11))
        combo.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=4)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_catalog())
        combo.bind("<KeyRelease>", lambda _event: self._refresh_catalog())
        self.catalog_search_combo = combo

        outer, _canvas, interior = crear_contenedor_scrollable(card.body, bg=PALETA["panel"], canvas_bg=PALETA["panel"])
        outer.pack(fill="both", expand=True)
        self.catalog_cards_container = interior

    def _build_library_column(self, parent):
        card = self._section_card(parent, "B. Mi espacio de estudio", "Tus cursos descargados con continuidad, progreso, últimas lecciones y accesos para retomar.")
        card.pack(fill="both", expand=True)
        header = tk.Frame(card.body, bg=PALETA["panel"])
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="Buscar", bg=PALETA["panel"], fg=PALETA["text"]).pack(side="left")
        entry = tk.Entry(header, textvariable=self.var_library_search, bg="#071423", fg="white", insertbackground="white", relief="flat", font=("Arial", 11))
        entry.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=6)
        entry.bind("<KeyRelease>", lambda _event: self._refresh_library())

        outer, _canvas, interior = crear_contenedor_scrollable(card.body, bg=PALETA["panel"], canvas_bg=PALETA["panel"])
        outer.pack(fill="both", expand=True)
        self.library_cards_container = interior

    def _build_context_column(self, parent):
        top = self._section_card(parent, "C. Curso seleccionado", "Ficha educativa del curso, con resumen de avance, continuidad y próximas acciones.")
        top.pack(fill="both", expand=True)

        hero = tk.Frame(top.body, bg=PALETA["panel_soft"], highlightthickness=1, highlightbackground=PALETA["border"])
        hero.pack(fill="x", pady=(0, 12))
        self.course_selected_title = tk.Label(hero, text="Selecciona un curso", bg=PALETA["panel_soft"], fg=PALETA["text"], font=("Arial", 20, "bold"), justify="left", anchor="w", wraplength=470)
        self.course_selected_title.pack(fill="x", padx=16, pady=(16, 6))
        self.course_selected_meta = tk.Label(hero, text="Explora el catálogo o elige uno de tus cursos para ver su ficha completa.", bg=PALETA["panel_soft"], fg=PALETA["text_dim"], justify="left", anchor="w", wraplength=470)
        self.course_selected_meta.pack(fill="x", padx=16)
        self.course_summary_progress = ttk.Progressbar(hero, maximum=100)
        self.course_summary_progress.pack(fill="x", padx=16, pady=(12, 8))
        self.course_progress_label = tk.Label(hero, text="Progreso del curso: 0.0%", bg=PALETA["panel_soft"], fg="#86efac", font=("Arial", 11, "bold"), anchor="w")
        self.course_progress_label.pack(fill="x", padx=16, pady=(0, 14))

        actions = tk.Frame(top.body, bg=PALETA["panel"])
        actions.pack(fill="x", pady=(0, 12))
        self.btn_primary_download = self._action_button(actions, "Descargar", self._download_selected, PALETA["accent"])
        self.btn_primary_download.pack(fill="x", pady=(0, 8))
        self.btn_primary_continue = self._action_button(actions, "Continuar donde te quedaste", self._continue_selected_course, PALETA["accent_alt"])
        self.btn_primary_continue.pack(fill="x", pady=(0, 8))
        self.btn_primary_open = self._action_button(actions, "Ver curso", self._open_selected_course, PALETA["ok"])
        self.btn_primary_open.pack(fill="x", pady=(0, 8))
        self.btn_primary_favorite = self._action_button(actions, "Marcar favorito", self._toggle_favorite_selected, PALETA["purple"])
        self.btn_primary_favorite.pack(fill="x", pady=(0, 8))
        self.btn_primary_delete = self._action_button(actions, "Eliminar curso", self._delete_selected_course, PALETA["danger"])
        self.btn_primary_delete.pack(fill="x")

        summary_card = tk.Frame(top.body, bg=PALETA["panel_soft"], highlightthickness=1, highlightbackground=PALETA["border"])
        summary_card.pack(fill="both", expand=True, pady=(0, 12))
        tk.Label(summary_card, text="Vista educativa del curso", bg=PALETA["panel_soft"], fg=PALETA["text"], font=("Arial", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        self.course_summary_text = tk.Text(
            summary_card,
            bg="#071423",
            fg="#e5eef8",
            wrap="word",
            relief="flat",
            height=14,
            padx=16,
            pady=16,
            font=("Arial", 11),
            spacing1=4,
            spacing2=3,
            spacing3=8,
        )
        self.course_summary_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.course_summary_text.configure(state="disabled")

        rec_card = tk.Frame(top.body, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["border"])
        rec_card.pack(fill="x")
        tk.Label(rec_card, text="Sugeridos para seguir", bg=PALETA["panel"], fg=PALETA["text"], font=("Arial", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(rec_card, text="Cursos recientes, favoritos o en progreso para que no pierdas continuidad.", bg=PALETA["panel"], fg=PALETA["text_dim"], justify="left", wraplength=460).pack(anchor="w", padx=16)
        inner = tk.Frame(rec_card, bg=PALETA["panel"])
        inner.pack(fill="x", padx=12, pady=(10, 14))
        self.recommendations_container = inner

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["border"])
        footer.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(footer, text="Guía rápida del módulo", bg=PALETA["panel"], fg=PALETA["text"], font=("Arial", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(
            footer,
            text="1. Explora por tema o nivel. 2. Descarga el curso. 3. Estudia en ventana completa. 4. Marca lecciones completas. 5. Retoma desde Continuar donde te quedaste.",
            bg=PALETA["panel"],
            fg=PALETA["text_dim"],
            justify="left",
            wraplength=1380,
        ).pack(anchor="w", padx=16, pady=(0, 12))

    def _section_card(self, parent, title, subtitle):
        outer = tk.Frame(parent, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["border"])
        tk.Label(outer, text=title, bg=PALETA["panel"], fg=PALETA["text"], font=("Arial", 16, "bold"), anchor="w").pack(fill="x", padx=16, pady=(16, 4))
        tk.Label(outer, text=subtitle, bg=PALETA["panel"], fg=PALETA["text_dim"], justify="left", anchor="w", wraplength=500).pack(fill="x", padx=16, pady=(0, 12))
        body = tk.Frame(outer, bg=PALETA["panel"])
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        outer.body = body
        return outer

    def _action_button(self, parent, text, command, color):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            font=("Arial", 11, "bold"),
            cursor="hand2",
        )

    def _close_window(self):
        if self.is_closing:
            return
        self.is_closing = True
        if self.geometry_refresh_job:
            try:
                self.root.after_cancel(self.geometry_refresh_job)
            except Exception as exc:
                self._log(f"Advertencia UI: no se pudo cancelar el reajuste de geometría: {exc}")
            self.geometry_refresh_job = None
        if self.course_viewer and self.course_viewer.winfo_exists():
            try:
                self.course_viewer.destroy()
            except Exception as exc:
                self._log(f"Advertencia UI: no se pudo cerrar el visor de curso al salir: {exc}")
        if self.worker_cancel_event and self.current_worker and self.current_worker.is_alive():
            self.worker_cancel_event.set()
        if self.poll_after_id:
            try:
                self.root.after_cancel(self.poll_after_id)
            except Exception as exc:
                self._log(f"Advertencia UI: no se pudo cancelar el polling de descargas: {exc}")
            self.poll_after_id = None
        try:
            self.root.destroy()
        except Exception as exc:
            self._log(f"Advertencia UI: no se pudo destruir la ventana de aprendizaje: {exc}")

    def _al_recuperar_foco(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        self._reajustar_a_pantalla()

    def _programar_reajuste_geometria(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if self.geometry_refresh_job:
            try:
                self.root.after_cancel(self.geometry_refresh_job)
            except Exception as exc:
                self._log(f"Advertencia UI: no se pudo reprogramar el reajuste de geometría: {exc}")
        self.geometry_refresh_job = self.root.after(120, self._reajustar_a_pantalla)

    def _reajustar_a_pantalla(self):
        self.geometry_refresh_job = None
        if not self._root_alive():
            return
        try:
            aplicar_geometria_relativa(self.root, self.root.master, rel_w=0.96, rel_h=0.94, min_w=1500, min_h=920)
        except Exception as exc:
            self._log(f"Advertencia UI: no se pudo reajustar la ventana de aprendizaje: {exc}")

    def _poll_queue(self):
        if not self._root_alive():
            self.poll_after_id = None
            return
        try:
            while True:
                payload = self.queue.get_nowait()
                self._handle_queue_message(payload)
        except Empty:
            pass
        self.poll_after_id = self.root.after(180, self._poll_queue)

    def _handle_queue_message(self, payload):
        event = payload.get("event")
        if event == "download_progress":
            self.active_download_course_id = str(payload.get("course_id", "") or self.active_download_course_id)
            self.var_progress.set(float(payload.get("progress", 0.0) or 0.0))
            self.var_status.set(str(payload.get("message", "Descargando curso.")))
            self.var_download_meta.set(self._compose_download_meta(payload))
            self.var_download_activity.set(str(payload.get("activity", "Preparando lecciones del curso.")))
            self._apply_download_payload(payload)
            self._refresh_catalog()
            self._refresh_context_panel()
            self._refresh_overview()
        elif event == "download_done":
            self.current_worker = None
            self.worker_cancel_event = None
            self.var_progress.set(100.0)
            self.var_status.set(str(payload.get("message", "Curso listo para estudiar.")))
            self.var_download_meta.set("Descarga completada y verificada.")
            self.var_download_activity.set("El curso ya está listo. Puedes abrirlo o continuar desde tu último avance.")
            course_id = str(payload.get("course_id", "") or "")
            if course_id:
                self.selected_course_id = course_id
            self._refresh_all()
        elif event == "download_error":
            self.current_worker = None
            self.worker_cancel_event = None
            self.var_status.set(str(payload.get("message", "Error en la descarga.")))
            self.var_download_meta.set(self._compose_download_meta(payload))
            self.var_download_activity.set(str(payload.get("error", "La descarga se interrumpió.")))
            self._refresh_all()
            if payload.get("error") != "cancelado_por_usuario":
                self._show_error("Descarga de curso", str(payload.get("message", "Error en la descarga.")))
        self._update_action_states()

    def _compose_download_meta(self, payload):
        progress = float(payload.get("progress", 0.0) or 0.0)
        downloaded_lessons = int(payload.get("downloaded_lessons", 0) or 0)
        total_lessons = int(payload.get("total_lessons", 0) or 0)
        downloaded_bytes = int(payload.get("downloaded_bytes", 0) or 0)
        total_bytes = int(payload.get("total_bytes", 0) or 0)
        parts = [f"{progress:.1f}%"]
        if total_lessons:
            parts.append(f"{downloaded_lessons}/{total_lessons} lecciones")
        if downloaded_bytes or total_bytes:
            size_text = f"{downloaded_bytes} / {total_bytes} bytes" if total_bytes else f"{downloaded_bytes} bytes"
            parts.append(size_text)
        phase = str(payload.get("phase", "") or "")
        if phase:
            parts.append(f"fase: {phase}")
        return " · ".join(parts)

    def _matches_filters(self, item):
        category = self.var_filter_category.get()
        language = self.var_filter_language.get()
        level = self.var_filter_level.get()
        state_filter = self.var_filter_state.get()
        if category not in {"", "Todas"} and item.get("category") != category:
            return False
        if language not in {"", "Todos"} and item.get("language") != language:
            return False
        if level not in {"", "Todos"} and item.get("level") != level:
            return False

        status = str(item.get("status", "") or "")
        progress = _safe_float(item.get("progress_percent", 0.0))
        if state_filter == "Solo descargados" and status not in {"listo", "instalado"}:
            return False
        if state_filter == "Solo disponibles" and status in {"listo", "instalado"}:
            return False
        if state_filter == "En progreso" and not (status in {"listo", "instalado"} and progress > 0.0):
            return False
        if state_filter == "Favoritos" and not bool(item.get("favorite")):
            return False
        return True

    def _matches_query(self, item, query: str) -> bool:
        query_n = normalizar_texto(query or "")
        if query_n == normalizar_texto("Todos los temas"):
            return True
        if not query_n:
            return True
        haystack = " ".join(
            [
                str(item.get("id", "")),
                str(item.get("name", "")),
                str(item.get("language", "")),
                str(item.get("category", "")),
                str(item.get("level", "")),
                str(item.get("description", "")),
                " ".join(item.get("tags", []) or []),
            ]
        )
        return query_n in normalizar_texto(haystack)

    def _refresh_filter_options(self):
        categories = sorted({item.get("category", "") for item in self.catalog_items if item.get("category")})
        languages = sorted({item.get("language", "") for item in self.catalog_items if item.get("language")})
        levels = sorted({item.get("level", "") for item in self.catalog_items if item.get("level")})
        topics = sorted(
            {
                topic
                for item in self.catalog_items
                for topic in ([item.get("category", "")] + list(item.get("tags", []) or []))
                if topic
            }
        )
        self.category_combo.configure(values=["Todas", *categories])
        self.language_combo.configure(values=["Todos", *languages])
        self.level_combo.configure(values=["Todos", *levels])
        if self.catalog_search_combo:
            self.catalog_search_combo.configure(values=["Todos los temas", *topics])
        if self.var_filter_category.get() not in self.category_combo["values"]:
            self.var_filter_category.set("Todas")
        if self.var_filter_language.get() not in self.language_combo["values"]:
            self.var_filter_language.set("Todos")
        if self.var_filter_level.get() not in self.level_combo["values"]:
            self.var_filter_level.set("Todos")

    def _refresh_all(self):
        self.catalog_items = load_catalog()
        self.installed_items = list_installed()
        self._refresh_filter_options()
        self._refresh_overview()
        self._refresh_category_rail()
        self._refresh_catalog()
        self._refresh_library()
        self._refresh_context_panel()
        self._refresh_recommendations()
        self._update_action_states()

    def _snapshot(self):
        installed = self.installed_items
        total_catalog = len(self.catalog_items)
        total_installed = len(installed)
        total_completed = sum(1 for item in installed if _safe_float(item.get("progress_percent", 0.0)) >= 100.0)
        total_in_progress = sum(1 for item in installed if 0.0 < _safe_float(item.get("progress_percent", 0.0)) < 100.0)
        total_favorites = sum(1 for item in self.catalog_items if item.get("favorite"))
        total_lessons = sum(max(1, _lesson_count(item)) for item in installed) if installed else 0
        total_done = sum(int(item.get("completed_lessons", 0) or 0) for item in installed)
        overall_progress = round((total_done / total_lessons) * 100.0, 1) if total_lessons else 0.0
        state = load_state()
        last_course_id = str(state.get("last_course", "") or "")
        recent_course = next((item for item in installed if item.get("id") == last_course_id), None)
        if not recent_course:
            recent_course = sorted(installed, key=lambda item: item.get("last_opened", ""), reverse=True)[0] if installed else None
        highlighted = None
        if recent_course and _safe_float(recent_course.get("progress_percent", 0.0)) < 100.0:
            highlighted = recent_course
        elif total_in_progress:
            highlighted = sorted(
                [item for item in installed if 0.0 < _safe_float(item.get("progress_percent", 0.0)) < 100.0],
                key=lambda item: (_safe_float(item.get("progress_percent", 0.0)), item.get("last_opened", "")),
                reverse=True,
            )[0]
        elif installed:
            highlighted = sorted(installed, key=lambda item: (bool(item.get("favorite")), item.get("last_opened", "")), reverse=True)[0]
        return {
            "total_catalog": total_catalog,
            "total_installed": total_installed,
            "total_completed": total_completed,
            "total_in_progress": total_in_progress,
            "total_favorites": total_favorites,
            "overall_progress": overall_progress,
            "recent_course": recent_course,
            "highlighted": highlighted,
        }

    def _refresh_overview(self):
        snapshot = self._snapshot()
        self.var_progress.set(snapshot["overall_progress"])
        self.var_overview_title.set("Tu espacio de aprendizaje offline")
        self.var_overview_body.set(
            f"Llevas {snapshot['total_installed']} cursos descargados, {snapshot['total_in_progress']} en progreso y {snapshot['total_completed']} terminados."
        )
        recent = snapshot["recent_course"]
        highlighted = snapshot["highlighted"]
        if recent:
            lesson = self._lesson_title_for(recent, recent.get("last_lesson", "")) or "Primera lección"
            self.var_continue_summary.set(
                f"Curso reciente: {recent.get('name', recent.get('id', ''))}\n"
                f"Última lección: {lesson}\n"
                f"Avance actual: {_fmt_percent(recent.get('progress_percent', 0.0))}"
            )
        else:
            self.var_continue_summary.set("Todavía no hay una sesión reciente. Descarga un curso y el sistema recordará en qué parte te quedaste.")

        if highlighted:
            self.var_recommendation.set(
                f"Sigue con “{highlighted.get('name', highlighted.get('id', ''))}”. "
                f"{_motivation_line(_safe_float(highlighted.get('progress_percent', 0.0)))}"
            )
        elif self.catalog_items:
            featured = sorted(self.catalog_items, key=lambda item: (bool(item.get("favorite")), _lesson_count(item)), reverse=True)[0]
            self.var_recommendation.set(
                f"Explora “{featured.get('name', featured.get('id', ''))}”, categoría {featured.get('category', '-')}, nivel {featured.get('level', '-')}. "
                "Puedes descargarlo y estudiarlo offline."
            )
        else:
            self.var_recommendation.set("Sin cursos en catálogo por ahora.")

        self.hero_continue_btn.configure(state="normal" if recent else "disabled")
        self.hero_recent_btn.configure(state="normal" if recent else "disabled")
        self._render_stats(snapshot)

    def _render_stats(self, snapshot):
        self._clear_children(self.stats_container)
        cards = [
            ("Cursos descargados", str(snapshot["total_installed"]), PALETA["accent"], "Tu biblioteca offline lista para estudiar."),
            ("En progreso", str(snapshot["total_in_progress"]), PALETA["accent_alt"], "Cursos que puedes retomar en un clic."),
            ("Completados", str(snapshot["total_completed"]), PALETA["ok"], "Cursos terminados o repasados por completo."),
            ("Favoritos", str(snapshot["total_favorites"]), PALETA["gold"], "Contenidos marcados para volver rápido."),
        ]
        for idx, (title, value, color, subtitle) in enumerate(cards):
            row = idx // 2
            col = idx % 2
            card = tk.Frame(self.stats_container, bg=PALETA["panel_soft_alt"], highlightthickness=1, highlightbackground=PALETA["border"])
            card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            tk.Label(card, text=title, bg=PALETA["panel_soft_alt"], fg=PALETA["text_dim"], font=("Arial", 9, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
            tk.Label(card, text=value, bg=PALETA["panel_soft_alt"], fg=color, font=("Arial", 19, "bold")).pack(anchor="w", padx=12)
            tk.Label(card, text=subtitle, bg=PALETA["panel_soft_alt"], fg=PALETA["text"], justify="left", wraplength=150).pack(anchor="w", padx=12, pady=(2, 10))
            self.stats_container.grid_columnconfigure(col, weight=1)

    def _refresh_category_rail(self):
        self._clear_children(self.categories_container)
        ordered = []
        preferred = [
            "Ciencias",
            "Matematicas",
            "Salud",
            "Primeros auxilios",
            "Agricultura",
            "Autosustentacion",
            "Energia",
            "Reparacion",
            "Comunicacion",
            "Supervivencia",
            "Educacion basica",
            "Formacion tecnica",
            "Oficios",
        ]
        seen = set()
        categories = [item.get("category", "") for item in self.catalog_items if item.get("category")]
        for label in preferred + sorted(categories):
            if label and label not in seen and label in categories:
                ordered.append(label)
                seen.add(label)

        if not ordered:
            tk.Label(self.categories_container, text="No hay categorías visibles todavía.", bg=PALETA["panel"], fg=PALETA["text_dim"]).pack(anchor="w", padx=4)
            return

        tk.Button(
            self.categories_container,
            text="Todas",
            command=lambda: self._set_category_filter("Todas"),
            bg="#dbeafe" if self.var_filter_category.get() == "Todas" else PALETA["panel_soft"],
            fg="#0f172a" if self.var_filter_category.get() == "Todas" else PALETA["text"],
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=4, pady=4)
        for category in ordered:
            selected = self.var_filter_category.get() == category
            tk.Button(
                self.categories_container,
                text=category,
                command=lambda value=category: self._set_category_filter(value),
                bg="#dbeafe" if selected else PALETA["panel_soft"],
                fg="#0f172a" if selected else PALETA["text"],
                relief="flat",
                bd=0,
                padx=14,
                pady=8,
                cursor="hand2",
                font=("Arial", 10, "bold"),
            ).pack(side="left", padx=4, pady=4)

    def _set_category_filter(self, value):
        self.var_filter_category.set(value)
        self._refresh_all()

    def _selected_catalog_item(self):
        return next((item for item in self.catalog_items if item.get("id") == self.selected_course_id), None)

    def _selected_installed_item(self):
        return next((item for item in self.installed_items if item.get("id") == self.selected_course_id), None)

    def _selected_course(self):
        return self._selected_installed_item() or self._selected_catalog_item()

    def _render_empty_state(self, container, title, body):
        card = tk.Frame(container, bg=PALETA["card_alt"], highlightthickness=1, highlightbackground=PALETA["border_soft"])
        card.pack(fill="x", pady=(0, 12))
        tk.Label(card, text=title, bg=PALETA["card_alt"], fg=PALETA["card_text"], font=("Arial", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(card, text=body, bg=PALETA["card_alt"], fg=PALETA["card_dim"], wraplength=410, justify="left").pack(anchor="w", padx=16, pady=(0, 16))

    def _clear_children(self, widget):
        for child in widget.winfo_children():
            child.destroy()

    def _refresh_catalog(self):
        self._clear_children(self.catalog_cards_container)
        self.catalog_cards = {}
        visible = []
        for item in self.catalog_items:
            if not self._matches_filters(item):
                continue
            if not self._matches_query(item, self.var_catalog_search.get()):
                continue
            visible.append(item)

        if not visible:
            self._render_empty_state(
                self.catalog_cards_container,
                "No hay cursos para mostrar",
                "Prueba con otra búsqueda o ajusta categoría, idioma, nivel o estado.",
            )
            return

        for item in visible:
            card = self._build_catalog_course_card(self.catalog_cards_container, item)
            self.catalog_cards[item["id"]] = card
        self._refresh_card_highlights()

    def _build_catalog_course_card(self, parent, item):
        status = str(item.get("status", "") or "")
        selected = self.selected_course_id == item.get("id")
        bg = "#dbeafe" if selected else PALETA["card"]
        border = "#2563eb" if selected else PALETA["border_soft"]

        card = tk.Frame(parent, bg=bg, highlightthickness=2 if selected else 1, highlightbackground=border, cursor="hand2")
        card.pack(fill="x", pady=(0, 12))
        self._bind_select_tree(card, item["id"])

        head = tk.Frame(card, bg=bg)
        head.pack(fill="x", padx=16, pady=(16, 10))
        title_wrap = tk.Frame(head, bg=bg)
        title_wrap.pack(side="left", fill="x", expand=True)
        title = item.get("name", item.get("id", ""))
        if item.get("favorite"):
            title = f"★ {title}"
        tk.Label(title_wrap, text=title, bg=bg, fg=PALETA["card_text"], font=("Arial", 15, "bold"), anchor="w", justify="left", wraplength=320).pack(anchor="w")
        tk.Label(title_wrap, text=f"{item.get('category', '-')} · {item.get('level', '-')} · {str(item.get('language', '-')).upper()}", bg=bg, fg=PALETA["card_dim"], font=("Arial", 10, "bold"), anchor="w").pack(anchor="w", pady=(4, 0))

        badge_bg = "#dcfce7" if status in {"listo", "instalado"} else "#fef3c7" if status in {"descargando", "instalando", "en_cola"} else "#dbeafe"
        badge_fg = "#166534" if status in {"listo", "instalado"} else "#92400e" if status in {"descargando", "instalando", "en_cola"} else "#1e3a8a"
        tk.Label(head, text=_label_status(status), bg=badge_bg, fg=badge_fg, font=("Arial", 9, "bold"), padx=10, pady=4).pack(side="right", anchor="n")

        tk.Label(card, text=item.get("description", ""), bg=bg, fg=PALETA["card_dim"], justify="left", wraplength=370).pack(fill="x", padx=16)

        chips = tk.Frame(card, bg=bg)
        chips.pack(fill="x", padx=16, pady=(12, 8))
        for text in [
            f"Lecciones: {_lesson_count(item)}",
            f"Tiempo: {_course_eta(item)}",
            f"Estado: {_course_state_hint(item)}",
        ]:
            tk.Label(chips, text=text, bg=PALETA["card_alt"], fg=PALETA["card_text"], font=("Arial", 9, "bold"), padx=8, pady=4).pack(side="left", padx=(0, 6))

        if status in {"descargando", "instalando", "en_cola"}:
            progress = ttk.Progressbar(card, maximum=100)
            progress.pack(fill="x", padx=16, pady=(0, 8))
            progress.configure(value=_safe_float(item.get("download_progress", 0.0)))
            tk.Label(card, text=self._compose_download_meta(item), bg=bg, fg=PALETA["card_dim"], anchor="w").pack(fill="x", padx=16)

        actions = tk.Frame(card, bg=bg)
        actions.pack(fill="x", padx=16, pady=(12, 16))
        download_btn = tk.Button(
            actions,
            text="Descargar",
            command=lambda course_id=item["id"]: self._download_by_id(course_id),
            bg=PALETA["accent"],
            fg="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            font=("Arial", 10, "bold"),
            cursor="hand2",
        )
        download_btn.pack(side="left")
        if status in {"listo", "instalado"}:
            download_btn.configure(text="Ya instalado")
        elif status in {"descargando", "instalando", "en_cola"}:
            download_btn.configure(text="En preparación")
        if status in {"listo", "instalado"}:
            tk.Button(
                actions,
                text="Ver curso",
                command=lambda course_id=item["id"]: self._open_course(course_id),
                bg=PALETA["accent_alt"],
                fg="white",
                relief="flat",
                bd=0,
                padx=12,
                pady=8,
                font=("Arial", 10, "bold"),
                cursor="hand2",
            ).pack(side="left", padx=(8, 0))
        tk.Button(
            actions,
            text="Detalles",
            command=lambda course_id=item["id"]: self._select_course(course_id),
            bg=PALETA["panel_soft_alt"],
            fg="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            font=("Arial", 10, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        if status in {"descargando", "instalando", "en_cola", "listo", "instalado"}:
            download_btn.configure(state="disabled")
        return card

    def _refresh_library(self):
        self._clear_children(self.library_cards_container)
        self.library_cards = {}
        visible = []
        for item in self.installed_items:
            if not self._matches_filters(item):
                continue
            if not self._matches_query(item, self.var_library_search.get()):
                continue
            visible.append(item)

        if not visible:
            self._render_empty_state(
                self.library_cards_container,
                "Todavía no tienes cursos descargados",
                "Descarga un curso del catálogo para verlo aquí con progreso, continuidad y accesos de estudio.",
            )
            return

        visible.sort(key=lambda item: (_safe_float(item.get("progress_percent", 0.0)), item.get("last_opened", "")), reverse=True)
        for item in visible:
            card = self._build_library_course_card(self.library_cards_container, item)
            self.library_cards[item["id"]] = card
        self._refresh_card_highlights()

    def _build_library_course_card(self, parent, item):
        selected = self.selected_course_id == item.get("id")
        bg = "#dff7ea" if selected else PALETA["card"]
        border = "#169c72" if selected else PALETA["border_soft"]

        card = tk.Frame(parent, bg=bg, highlightthickness=2 if selected else 1, highlightbackground=border, cursor="hand2")
        card.pack(fill="x", pady=(0, 12))
        self._bind_select_tree(card, item["id"])

        top = tk.Frame(card, bg=bg)
        top.pack(fill="x", padx=16, pady=(16, 8))
        title = item.get("name", item.get("id", ""))
        if item.get("favorite"):
            title = f"★ {title}"
        tk.Label(top, text=title, bg=bg, fg=PALETA["card_text"], font=("Arial", 15, "bold"), anchor="w", wraplength=300, justify="left").pack(side="left", fill="x", expand=True)
        chip_text = "Completado" if _safe_float(item.get("progress_percent", 0.0)) >= 100.0 else _fmt_percent(item.get("progress_percent", 0.0))
        chip_bg = "#dcfce7" if _safe_float(item.get("progress_percent", 0.0)) >= 100.0 else "#dbeafe"
        chip_fg = "#166534" if _safe_float(item.get("progress_percent", 0.0)) >= 100.0 else "#1e3a8a"
        tk.Label(top, text=chip_text, bg=chip_bg, fg=chip_fg, font=("Arial", 10, "bold"), padx=10, pady=4).pack(side="right")

        tk.Label(card, text=f"{item.get('category', '-')} · {item.get('level', '-')} · {str(item.get('language', '-')).upper()}", bg=bg, fg=PALETA["card_dim"], font=("Arial", 10, "bold"), anchor="w").pack(fill="x", padx=16)

        progress = ttk.Progressbar(card, maximum=100)
        progress.pack(fill="x", padx=16, pady=(12, 8))
        progress.configure(value=_safe_float(item.get("progress_percent", 0.0)))

        lesson_name = self._lesson_title_for(item, item.get("last_lesson", "")) or "Empieza desde la primera lección"
        tk.Label(card, text=f"Última lección: {lesson_name}", bg=bg, fg=PALETA["card_dim"], justify="left", wraplength=370).pack(fill="x", padx=16)
        tk.Label(card, text=f"Último acceso: {item.get('last_opened') or 'Sin abrir todavía'}", bg=bg, fg=PALETA["card_dim"], justify="left").pack(fill="x", padx=16, pady=(4, 0))

        info = tk.Frame(card, bg=bg)
        info.pack(fill="x", padx=16, pady=(10, 0))
        for text in [
            f"Lecciones: {_lesson_count(item)}",
            f"Tiempo: {_course_eta(item)}",
            _course_state_hint(item),
        ]:
            tk.Label(info, text=text, bg=PALETA["card_alt"], fg=PALETA["card_text"], font=("Arial", 9, "bold"), padx=8, pady=4).pack(side="left", padx=(0, 6))

        actions = tk.Frame(card, bg=bg)
        actions.pack(fill="x", padx=16, pady=(12, 16))
        tk.Button(actions, text="Continuar", command=lambda course_id=item["id"]: self._open_course(course_id, target_lesson=continue_course(course_id)), bg=PALETA["accent"], fg="white", relief="flat", bd=0, padx=12, pady=8, font=("Arial", 10, "bold"), cursor="hand2").pack(side="left")
        tk.Button(actions, text="Ver curso", command=lambda course_id=item["id"]: self._open_course(course_id), bg=PALETA["accent_alt"], fg="white", relief="flat", bd=0, padx=12, pady=8, font=("Arial", 10, "bold"), cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(actions, text="Eliminar", command=lambda course_id=item["id"]: self._delete_course_direct(course_id), bg=PALETA["danger"], fg="white", relief="flat", bd=0, padx=12, pady=8, font=("Arial", 10, "bold"), cursor="hand2").pack(side="left", padx=(8, 0))
        return card

    def _refresh_card_highlights(self):
        for course_id, card in self.catalog_cards.items():
            selected = course_id == self.selected_course_id
            card.configure(bg="#dbeafe" if selected else PALETA["card"], highlightbackground="#2563eb" if selected else PALETA["border_soft"], highlightthickness=2 if selected else 1)
            for child in card.winfo_children():
                self._recolor_tree(child, "#dbeafe" if selected else PALETA["card"])
        for course_id, card in self.library_cards.items():
            selected = course_id == self.selected_course_id
            card.configure(bg="#dff7ea" if selected else PALETA["card"], highlightbackground="#169c72" if selected else PALETA["border_soft"], highlightthickness=2 if selected else 1)
            for child in card.winfo_children():
                self._recolor_tree(child, "#dff7ea" if selected else PALETA["card"])

    def _recolor_tree(self, widget, bg):
        try:
            current = widget.cget("bg")
        except Exception:
            return
        if current in {PALETA["card"], "#dbeafe", "#dff7ea"}:
            try:
                widget.configure(bg=bg)
            except Exception:
                pass
        for child in widget.winfo_children():
            self._recolor_tree(child, bg)

    def _bind_select_tree(self, widget, course_id: str):
        try:
            widget.bind("<Button-1>", lambda _event, cid=course_id: self._select_course(cid))
        except Exception:
            return
        for child in widget.winfo_children():
            self._bind_select_tree(child, course_id)

    def _course_summary_lines(self, item):
        total_lessons = _lesson_count(item)
        progress = _safe_float(item.get("progress_percent", 0.0))
        completed = int(item.get("completed_lessons", 0) or 0)
        lines = [
            f"Categoría: {item.get('category', '-')}",
            f"Nivel: {item.get('level', '-')}",
            f"Idioma: {str(item.get('language', '-')).upper()}",
            f"Estado: {_label_status(item.get('status', ''))}",
            f"Lecciones: {total_lessons}",
            f"Tiempo estimado: {_course_eta(item)}",
            f"Avance: {progress:.1f}% ({completed}/{max(1, total_lessons)} lecciones completadas)",
        ]
        if item.get("size_human"):
            lines.append(f"Tamaño estimado: {item.get('size_human')}")
        tags = ", ".join(item.get("tags", []) or [])
        if tags:
            lines.append(f"Temas: {tags}")
        return lines

    def _refresh_context_panel(self):
        item = self._selected_course()
        self.course_summary_text.configure(state="normal")
        self.course_summary_text.delete("1.0", "end")

        if not item:
            self.course_selected_title.configure(text="Selecciona un curso")
            self.course_selected_meta.configure(text="Explora el catálogo o elige uno de tus cursos para ver su ficha completa.")
            self.course_summary_progress.configure(value=0)
            self.course_progress_label.configure(text="Progreso del curso: 0.0%")
            self.course_summary_text.insert(
                "1.0",
                "Aquí verás una ficha educativa clara del curso seleccionado.\n\n"
                "Lo que podrás hacer:\n"
                "• Descargar el curso o abrirlo si ya está listo.\n"
                "• Continuar exactamente desde tu última lección.\n"
                "• Entender su progreso, módulos y tiempo estimado.\n"
                "• Entrar a una ventana completa enfocada en estudiar.",
            )
            self.course_summary_text.configure(state="disabled")
            return

        progress = _safe_float(item.get("progress_percent", 0.0))
        self.course_selected_title.configure(text=item.get("name", item.get("id", "")))
        self.course_selected_meta.configure(text=item.get("description", "") or "Este curso no tiene descripción adicional.")
        self.course_summary_progress.configure(value=progress)
        self.course_progress_label.configure(text=f"Progreso del curso: {progress:.1f}%")

        lines = self._course_summary_lines(item)
        last_lesson_name = self._lesson_title_for(item, item.get("last_lesson", ""))
        if last_lesson_name:
            lines.append(f"Última lección vista: {last_lesson_name}")
        if item.get("last_opened"):
            lines.append(f"Último acceso: {item.get('last_opened')}")
        lines.append("")
        lines.append("Cómo se estudia ahora:")
        lines.append("• Ventana completa con encabezado del curso y progreso visible.")
        lines.append("• Navegación lateral por módulos y lecciones.")
        lines.append("• Lectura amplia, cómoda y con continuidad automática.")
        lines.append(f"• Mensaje de avance: {_motivation_line(progress)}")
        self.course_summary_text.insert("1.0", "\n".join(lines))
        self.course_summary_text.configure(state="disabled")

    def _refresh_recommendations(self):
        self._clear_children(self.recommendations_container)
        items = sorted(
            self.catalog_items,
            key=lambda item: (
                item.get("id") == self.selected_course_id,
                bool(item.get("favorite")),
                _safe_float(item.get("progress_percent", 0.0)),
                item.get("last_opened", ""),
                item.get("status") in {"listo", "instalado"},
            ),
            reverse=True,
        )[:3]
        if not items:
            tk.Label(self.recommendations_container, text="No hay sugerencias disponibles.", bg=PALETA["panel"], fg=PALETA["text_dim"]).pack(anchor="w")
            return

        for item in items:
            row = tk.Frame(self.recommendations_container, bg=PALETA["panel_soft"], highlightthickness=1, highlightbackground=PALETA["border"])
            row.pack(fill="x", pady=(0, 8))
            tk.Label(row, text=item.get("name", item.get("id", "")), bg=PALETA["panel_soft"], fg=PALETA["text"], font=("Arial", 11, "bold"), anchor="w", justify="left", wraplength=420).pack(fill="x", padx=12, pady=(10, 2))
            tk.Label(row, text=f"{item.get('category', '-')} · {item.get('level', '-')} · {_course_state_hint(item)}", bg=PALETA["panel_soft"], fg=PALETA["text_dim"], anchor="w", justify="left", wraplength=420).pack(fill="x", padx=12)
            actions = tk.Frame(row, bg=PALETA["panel_soft"])
            actions.pack(fill="x", padx=12, pady=(8, 10))
            tk.Button(actions, text="Seleccionar", command=lambda course_id=item["id"]: self._select_course(course_id), bg=PALETA["accent"], fg="white", relief="flat", bd=0, padx=10, pady=6, cursor="hand2", font=("Arial", 9, "bold")).pack(side="left")
            if str(item.get("status", "") or "") in {"listo", "instalado"}:
                tk.Button(actions, text="Abrir", command=lambda course_id=item["id"]: self._open_course(course_id), bg=PALETA["accent_alt"], fg="white", relief="flat", bd=0, padx=10, pady=6, cursor="hand2", font=("Arial", 9, "bold")).pack(side="left", padx=(8, 0))

    def _lesson_title_for(self, item, lesson_id: str) -> str:
        if not lesson_id:
            return ""
        for module in item.get("modules", []) or []:
            for lesson in module.get("lessons", []) or []:
                if lesson.get("id") == lesson_id:
                    return lesson.get("title", lesson_id)
        return lesson_id

    def _select_course(self, course_id: str):
        self.selected_course_id = course_id
        self._refresh_card_highlights()
        self._refresh_context_panel()
        self._update_action_states()

    def _update_action_states(self):
        selected_catalog = self._selected_catalog_item()
        selected_installed = self._selected_installed_item()
        selected_course = selected_installed or selected_catalog
        worker_busy = bool(self.current_worker and self.current_worker.is_alive())
        status = str((selected_course or {}).get("status", "") or "")
        if selected_catalog and status in {"listo", "instalado"}:
            self.btn_primary_download.configure(text="Ya instalado")
        elif selected_catalog and status in {"descargando", "instalando", "en_cola"}:
            self.btn_primary_download.configure(text="En preparación")
        else:
            self.btn_primary_download.configure(text="Descargar")
        self.btn_primary_download.configure(state=("normal" if selected_catalog and status not in {"descargando", "instalando", "en_cola", "listo", "instalado"} and not worker_busy else "disabled"))
        self.btn_primary_continue.configure(state=("normal" if selected_course and status in {"listo", "instalado"} else "disabled"))
        self.btn_primary_open.configure(state=("normal" if selected_installed else "disabled"))
        self.btn_primary_favorite.configure(state=("normal" if selected_course else "disabled"))
        self.btn_primary_delete.configure(state=("normal" if selected_installed and not worker_busy else "disabled"))
        if selected_course:
            self.btn_primary_favorite.configure(text="Quitar favorito" if bool(selected_course.get("favorite")) else "Marcar favorito")

    def _run_worker(self, target, *, on_error_message):
        if self.current_worker and self.current_worker.is_alive():
            self._show_warning("Operación en curso", "Espera a que termine la operación actual.")
            return False

        def runner():
            try:
                target()
            except DownloadCancelledError as exc:
                self.queue.put({"event": "download_error", "message": str(exc), "error": "cancelado_por_usuario"})
            except Exception as exc:
                self.queue.put({"event": "download_error", "message": f"{on_error_message}: {exc}", "error": str(exc)})

        self.worker_cancel_event = threading.Event()
        self.current_worker = threading.Thread(target=runner, daemon=True)
        self.current_worker.start()
        self._update_action_states()
        return True

    def _apply_download_payload(self, payload):
        course_id = str(payload.get("course_id", "") or "")
        if not course_id:
            return
        for item in self.catalog_items:
            if item.get("id") == course_id:
                item["status"] = str(payload.get("status", item.get("status", "")) or item.get("status", ""))
                item["download_progress"] = float(payload.get("progress", item.get("download_progress", 0.0)) or 0.0)
                item["download_phase"] = str(payload.get("phase", item.get("download_phase", "")) or "")
                item["downloaded_lessons"] = int(payload.get("downloaded_lessons", item.get("downloaded_lessons", 0)) or 0)
                item["total_lessons"] = int(payload.get("total_lessons", item.get("total_lessons", 0)) or 0)
                item["downloaded_bytes"] = int(payload.get("downloaded_bytes", item.get("downloaded_bytes", 0)) or 0)
                item["total_bytes"] = int(payload.get("total_bytes", item.get("total_bytes", 0)) or 0)
                item["activity"] = str(payload.get("activity", item.get("activity", "")) or "")
                item["download_error"] = str(payload.get("error", item.get("download_error", "")) or "")
                break

    def _download_by_id(self, course_id: str):
        self.selected_course_id = course_id
        self._download_selected()

    def _download_selected(self):
        item = self._selected_catalog_item()
        if not item:
            self._show_warning("Selecciona un curso", "Primero elige un curso del catálogo.")
            return
        course_id = item["id"]

        def task():
            result = download_course(
                course_id,
                progress_callback=lambda payload: self.queue.put({"event": "download_progress", **payload}),
                cancel_event=self.worker_cancel_event,
            )
            self.queue.put({"event": "download_done", "course_id": course_id, "message": f"Curso listo: {item.get('name', course_id)}", "result": result})

        self.active_download_course_id = course_id
        self.var_status.set(f"Descargando {item.get('name', course_id)}...")
        self.var_download_meta.set("0.0% · fase: preparando")
        self.var_download_activity.set("Iniciando descarga y preparación del curso.")
        self.var_progress.set(0.0)
        self._apply_download_payload({"course_id": course_id, "status": "en_cola", "progress": 0.0, "phase": "preparando"})
        self._run_worker(task, on_error_message=f"No se pudo descargar {item.get('name', course_id)}")

    def _on_course_viewer_updated(self, course_id: str):
        if self.course_viewer and not self.course_viewer.winfo_exists():
            self.course_viewer = None
        self.selected_course_id = course_id
        self._refresh_all()
        self.var_status.set("Progreso del curso actualizado.")

    def _open_course(self, course_id: str, target_lesson: str = ""):
        try:
            if self.course_viewer and self.course_viewer.winfo_exists():
                if getattr(self.course_viewer, "course_id", "") == course_id:
                    self.course_viewer.lift()
                    self.course_viewer.focus_force()
                    if target_lesson:
                        self.course_viewer.open_lesson(target_lesson)
                    return
                self.course_viewer.destroy()
        except Exception as exc:
            self._log(f"Advertencia UI: no se pudo reciclar la ventana actual del curso: {exc}")

        try:
            self.course_viewer = VentanaCurso(
                self.root,
                course_id,
                initial_lesson=target_lesson,
                on_course_updated=self._on_course_viewer_updated,
            )
        except Exception as exc:
            self._show_error("Abrir curso", str(exc))
            return

        self.selected_course_id = course_id
        self.var_status.set("Curso abierto en modo de estudio.")
        self._refresh_all()

    def _open_selected_course(self):
        item = self._selected_installed_item()
        if not item:
            self._show_warning("Selecciona un curso", "Elige un curso descargado para abrirlo.")
            return
        self._open_course(item["id"])

    def _continue_selected_course(self):
        item = self._selected_installed_item() or self._selected_catalog_item()
        if not item or item.get("status") not in {"listo", "instalado"}:
            self._show_warning("Curso no disponible", "El curso debe estar descargado para poder continuarlo.")
            return
        self._open_course(item["id"], target_lesson=continue_course(item["id"]))

    def _continue_recent_course(self):
        snapshot = self._snapshot()
        recent = snapshot["recent_course"]
        if not recent:
            self._show_warning("Sin sesión reciente", "Todavía no hay un curso reciente para continuar.")
            return
        self._open_course(recent["id"], target_lesson=continue_course(recent["id"]))

    def _open_recent_course(self):
        snapshot = self._snapshot()
        recent = snapshot["recent_course"]
        if not recent:
            self._show_warning("Sin curso reciente", "Todavía no hay un curso reciente para abrir.")
            return
        self._open_course(recent["id"])

    def _reset_to_catalog(self):
        self.var_filter_state.set("Todos")
        self.var_filter_category.set("Todas")
        self.var_filter_language.set("Todos")
        self.var_filter_level.set("Todos")
        self.var_catalog_search.set("Todos los temas")
        self._refresh_all()

    def _toggle_favorite_selected(self):
        item = self._selected_course()
        if not item:
            self._show_warning("Selecciona un curso", "Selecciona un curso para marcarlo como favorito.")
            return
        set_favorite(item["id"], not bool(item.get("favorite")))
        self._refresh_all()

    def _delete_course_direct(self, course_id: str):
        self.selected_course_id = course_id
        self._delete_selected_course()

    def _delete_selected_course(self):
        item = self._selected_installed_item()
        if not item:
            self._show_warning("Selecciona un curso", "Elige un curso descargado para eliminarlo.")
            return
        if not messagebox.askyesno("Eliminar curso", f'¿Eliminar "{item.get("name", item["id"])}"?', parent=self.root):
            return
        if self.course_viewer and self.course_viewer.winfo_exists() and getattr(self.course_viewer, "course_id", "") == item["id"]:
            try:
                self.course_viewer.destroy()
            except Exception as exc:
                self._log(f"Advertencia UI: no se pudo cerrar el visor del curso a eliminar: {exc}")
            self.course_viewer = None
        delete_course(item["id"])
        if self.selected_course_id == item["id"]:
            self.selected_course_id = ""
        self.var_status.set("Curso eliminado.")
        self._refresh_all()
