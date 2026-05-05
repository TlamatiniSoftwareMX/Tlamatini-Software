import math
import re
import tkinter as tk
from tkinter import messagebox, ttk

from core.aprendizaje_offline import (
    continue_course,
    get_lesson,
    get_reading_position,
    list_installed,
    load_catalog,
    load_course,
    save_reading_position,
    set_favorite,
    update_progress,
)
from core.logs import registrar_log
from core.window_geometry import aplicar_geometria_relativa, habilitar_scroll_mouse


PALETA = {
    "bg": "#0a1624",
    "sidebar": "#11263d",
    "sidebar_soft": "#18334f",
    "sidebar_soft_alt": "#214266",
    "surface": "#eef4f7",
    "card": "#ffffff",
    "card_alt": "#f5f9fb",
    "border": "#d7e3ea",
    "border_dark": "#294863",
    "text": "#eaf4ff",
    "text_dim": "#9fb6cc",
    "content_text": "#132235",
    "content_dim": "#577086",
    "accent": "#16a36e",
    "accent_soft": "#dcf6ea",
    "accent_dark": "#0f7a52",
    "blue": "#2b6de6",
    "blue_soft": "#dceafe",
    "warn": "#c97911",
    "danger": "#b91c1c",
    "muted": "#334155",
}


def _safe_float(value) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _minutes_from_words(words) -> int:
    try:
        count = max(1, int(words or 0))
    except Exception:
        count = 1
    return max(1, math.ceil(count / 190))


def _course_message(percent: float) -> str:
    if percent >= 100.0:
        return "Curso completado. Puedes repasarlo o avanzar al siguiente."
    if percent >= 75.0:
        return "Último tramo del curso. Ya casi terminas."
    if percent >= 40.0:
        return "Buen avance. Mantén la continuidad."
    if percent > 0.0:
        return "Ya empezaste. Sigue desde tu última lección."
    return "Empieza por la primera lección o usa continuar."


def _lesson_status_text(completed: bool, reading_fraction: float) -> str:
    if completed:
        return "Completada"
    if reading_fraction >= 0.75:
        return "Casi terminada"
    if reading_fraction > 0.0:
        return "En lectura"
    return "Pendiente"


def _short_summary(text: str, limit: int = 180) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    cut = clean[: limit - 1].rsplit(" ", 1)[0].strip()
    return f"{cut}..."


def _split_paragraphs(text: str) -> list[str]:
    raw = re.split(r"\n\s*\n", (text or "").strip())
    paragraphs = []
    for item in raw:
        cleaned = re.sub(r"[ \t]+", " ", item.replace("\r", "")).strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def _extract_bullets(paragraphs: list[str]) -> tuple[list[str], list[str]]:
    bullets = []
    plain = []
    for paragraph in paragraphs:
        if paragraph.startswith("- "):
            chunks = [chunk.strip(" -") for chunk in re.split(r"\n-\s+|-\s+", paragraph) if chunk.strip(" -")]
            bullets.extend(chunks)
        else:
            plain.append(paragraph)
    return bullets, plain


def _didactic_blocks(lesson: dict) -> dict:
    paragraphs = _split_paragraphs(lesson.get("text", ""))
    bullets, plain = _extract_bullets(paragraphs)
    sections = [section.get("line", "").strip() for section in lesson.get("sections", []) or [] if section.get("line")]

    intro = plain[:2]
    learning = bullets[:4]
    if not learning:
        learning = [item for item in sections[:4] if item][:4]
    if not learning:
        learning = [_short_summary(item, 90) for item in plain[:3]]

    remainder = plain[2:] if len(plain) > 2 else plain[1:]
    if not remainder and bullets:
        remainder = [f"- {item}" for item in bullets]

    titled_blocks = []
    chunk_size = 2
    for idx in range(0, len(remainder), chunk_size):
        chunk = remainder[idx : idx + chunk_size]
        if not chunk:
            continue
        title = sections[min(len(titled_blocks), len(sections) - 1)] if sections else ""
        if not title:
            title = "Punto clave" if len(titled_blocks) == 0 else f"Bloque {len(titled_blocks) + 1}"
        titled_blocks.append({"title": title, "items": chunk})

    if bullets:
        titled_blocks.insert(
            0,
            {
                "title": "Puntos clave",
                "items": [f"• {item}" for item in bullets[:6]],
            },
        )

    return {
        "intro": intro,
        "learning": learning,
        "blocks": titled_blocks or [{"title": "Contenido principal", "items": plain[:4] or bullets[:4]}],
    }


class VentanaCurso(tk.Toplevel):
    def __init__(self, master, course_id: str, *, initial_lesson: str = "", on_course_updated=None):
        super().__init__(master)
        self.course_id = course_id
        self.initial_lesson = initial_lesson
        self.on_course_updated = on_course_updated

        self.course_manifest = {}
        self.lesson_order = []
        self.lesson_buttons = {}
        self.selected_lesson_id = ""
        self.lesson_open_in_progress = False
        self.is_closing = False
        self.reading_save_job = None

        self.var_course_title = tk.StringVar(value="Curso")
        self.var_course_meta = tk.StringVar(value="")
        self.var_progress_label = tk.StringVar(value="0%")
        self.var_lesson_title = tk.StringVar(value="Selecciona una lección")
        self.var_lesson_subtitle = tk.StringVar(value="")
        self.var_breadcrumb = tk.StringVar(value="")
        self.var_lesson_counter = tk.StringVar(value="Lección 0 de 0")
        self.var_lesson_state = tk.StringVar(value="Pendiente")
        self.var_reading_progress = tk.StringVar(value="Lectura 0%")
        self.var_general_progress = tk.StringVar(value="0% total")

        self.title("TLAMATINI - Curso")
        self.configure(bg=PALETA["bg"])
        self.minsize(1480, 940)
        aplicar_geometria_relativa(self, master, rel_w=0.96, rel_h=0.96, min_w=1480, min_h=940)
        self.protocol("WM_DELETE_WINDOW", self._close_window)

        self.sidebar_canvas = None
        self.sidebar_container = None
        self.content_canvas = None
        self.content_inner = None
        self.course_progressbar = None
        self.reading_progressbar = None
        self.progress_ring = None
        self.progress_ring_label = None
        self.general_stats_container = None
        self.lesson_buttons_frame = None
        self.btn_prev = None
        self.btn_next = None
        self.btn_complete = None
        self.btn_favorite = None

        self._build_ui()
        self._load_course_view()

    def _log(self, message: str):
        registrar_log("ui", message, "aprendizaje_curso")

    def _show_error(self, title: str, message: str):
        self._log(f"Error UI: {title}: {message}")
        if self.winfo_exists():
            messagebox.showerror(title, message, parent=self)

    def _build_ui(self):
        shell = tk.Frame(self, bg=PALETA["bg"])
        shell.pack(fill="both", expand=True, padx=14, pady=14)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(shell, bg=PALETA["sidebar"], highlightthickness=1, highlightbackground=PALETA["border_dark"])
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.configure(width=332)
        sidebar.grid_propagate(False)

        right = tk.Frame(shell, bg=PALETA["surface"])
        right.grid(row=0, column=1, sticky="nsew", padx=(14, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self._build_sidebar(sidebar)
        self._build_right_area(right)

    def _build_sidebar(self, parent):
        top = tk.Frame(parent, bg=PALETA["sidebar"])
        top.pack(fill="x", padx=16, pady=(16, 10))
        tk.Button(
            top,
            text="← Volver",
            command=self._close_window,
            bg=PALETA["sidebar_soft"],
            fg="white",
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            font=("Arial", 10, "bold"),
            cursor="hand2",
        ).pack(anchor="w")

        tk.Label(parent, text="Ruta del curso", bg=PALETA["sidebar"], fg=PALETA["text"], font=("Arial", 17, "bold"), anchor="w").pack(fill="x", padx=16)

        route_wrap = tk.Frame(parent, bg=PALETA["sidebar"])
        route_wrap.pack(fill="both", expand=True, padx=12, pady=(10, 12))
        canvas = tk.Canvas(route_wrap, bg=PALETA["sidebar"], highlightthickness=0, bd=0, width=320)
        scrollbar = ttk.Scrollbar(route_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        interior = tk.Frame(canvas, bg=PALETA["sidebar"])
        window_id = canvas.create_window((0, 0), window=interior, anchor="nw")

        interior.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
        habilitar_scroll_mouse(route_wrap, canvas)

        self.sidebar_canvas = canvas
        self.sidebar_container = interior

        progress_card = tk.Frame(parent, bg=PALETA["sidebar_soft"], highlightthickness=1, highlightbackground=PALETA["border_dark"])
        progress_card.pack(fill="x", padx=16, pady=(0, 16))
        tk.Label(progress_card, textvariable=self.var_general_progress, bg=PALETA["sidebar_soft"], fg="#8ef2c9", font=("Arial", 11, "bold")).pack(anchor="w", padx=14, pady=(14, 0))
        stats = tk.Frame(progress_card, bg=PALETA["sidebar_soft"])
        stats.pack(fill="x", padx=10, pady=(10, 10))
        self.general_stats_container = stats
        tk.Button(
            progress_card,
            text="Mis cursos",
            command=self._back_to_library,
            bg=PALETA["accent"],
            fg="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=9,
            font=("Arial", 10, "bold"),
            cursor="hand2",
        ).pack(fill="x", padx=14, pady=(0, 14))

    def _build_right_area(self, parent):
        header = tk.Frame(parent, bg=PALETA["surface"])
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)

        left = tk.Frame(header, bg=PALETA["surface"])
        left.grid(row=0, column=0, sticky="nsew")
        tk.Label(left, textvariable=self.var_course_title, bg=PALETA["surface"], fg=PALETA["content_text"], font=("Arial", 27, "bold"), anchor="w", justify="left").pack(fill="x")
        tk.Label(left, textvariable=self.var_breadcrumb, bg=PALETA["surface"], fg=PALETA["blue"], font=("Arial", 11, "bold"), anchor="w").pack(fill="x", pady=(4, 2))
        tk.Label(left, textvariable=self.var_course_meta, bg=PALETA["surface"], fg=PALETA["content_dim"], font=("Arial", 10), anchor="w", justify="left", wraplength=760).pack(fill="x")

        badge_row = tk.Frame(left, bg=PALETA["surface"])
        badge_row.pack(fill="x", pady=(8, 0))
        self.level_badge = tk.Label(badge_row, text="Nivel", bg=PALETA["blue_soft"], fg=PALETA["blue"], font=("Arial", 10, "bold"), padx=12, pady=6)
        self.level_badge.pack(side="left")
        tk.Label(badge_row, textvariable=self.var_progress_label, bg=PALETA["accent_soft"], fg=PALETA["accent_dark"], font=("Arial", 10, "bold"), padx=12, pady=6).pack(side="left", padx=(8, 0))
        self.course_progressbar = ttk.Progressbar(left, maximum=100)
        self.course_progressbar.pack(fill="x", pady=(10, 0))

        ring_wrap = tk.Frame(header, bg=PALETA["surface"])
        ring_wrap.grid(row=0, column=1, sticky="e", padx=(20, 0))
        self.progress_ring = tk.Canvas(ring_wrap, width=110, height=110, bg=PALETA["surface"], highlightthickness=0, bd=0)
        self.progress_ring.pack()
        self.progress_ring_label = tk.Label(ring_wrap, text="0%", bg=PALETA["surface"], fg=PALETA["content_text"], font=("Arial", 16, "bold"))
        self.progress_ring_label.place(relx=0.5, rely=0.5, anchor="center")

        body = tk.Frame(parent, bg=PALETA["surface"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        canvas = tk.Canvas(body, bg=PALETA["surface"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self._scroll_and_track)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        inner = tk.Frame(canvas, bg=PALETA["surface"])
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
        habilitar_scroll_mouse(body, canvas, on_scroll=self._on_scroll_event)

        self.content_canvas = canvas
        self.content_inner = inner

        footer = tk.Frame(parent, bg=PALETA["surface"])
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        footer.grid_columnconfigure(1, weight=1)
        tk.Button(
            footer,
            text="Anterior",
            command=lambda: self._move_lesson(-1),
            bg=PALETA["card"],
            fg=PALETA["content_text"],
            relief="flat",
            bd=0,
            padx=18,
            pady=11,
            font=("Arial", 11, "bold"),
            cursor="hand2",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(footer, textvariable=self.var_lesson_counter, bg=PALETA["surface"], fg=PALETA["content_dim"], font=("Arial", 11, "bold")).grid(row=0, column=1)
        tk.Button(
            footer,
            text="Siguiente",
            command=lambda: self._move_lesson(1),
            bg=PALETA["accent"],
            fg="white",
            relief="flat",
            bd=0,
            padx=18,
            pady=11,
            font=("Arial", 11, "bold"),
            cursor="hand2",
        ).grid(row=0, column=2, sticky="e")

        self.btn_prev = footer.grid_slaves(row=0, column=0)[0]
        self.btn_next = footer.grid_slaves(row=0, column=2)[0]

    def _close_window(self):
        if self.is_closing:
            return
        self.is_closing = True
        self._persist_reading_position()
        if self.reading_save_job:
            try:
                self.after_cancel(self.reading_save_job)
            except Exception:
                pass
            self.reading_save_job = None
        self._notify_host()
        try:
            self.destroy()
        except Exception:
            pass

    def _notify_host(self):
        if self.on_course_updated:
            try:
                self.on_course_updated(self.course_id)
            except Exception as exc:
                self._log(f"Callback de actualización falló: {exc}")

    def _back_to_library(self):
        try:
            if self.master and self.master.winfo_exists():
                self.master.lift()
                self.master.focus_force()
        except Exception:
            pass
        self._close_window()

    def _lesson_count(self) -> int:
        count = 0
        for module in self.course_manifest.get("modules", []) or []:
            count += len(module.get("lessons", []) or [])
        return count

    def _module_completion_ratio(self, module: dict) -> tuple[int, int]:
        completed = self._current_completed()
        lesson_ids = [lesson.get("id", "") for lesson in module.get("lessons", []) or []]
        done = sum(1 for lesson_id in lesson_ids if lesson_id in completed)
        return done, len(lesson_ids)

    def _completed_modules(self) -> tuple[int, int]:
        done = 0
        modules = self.course_manifest.get("modules", []) or []
        for module in modules:
            completed, total = self._module_completion_ratio(module)
            if total and completed == total:
                done += 1
        return done, len(modules)

    def _reload_manifest(self):
        self.course_manifest = load_course(self.course_id)
        for entry in load_catalog():
            if entry.get("id") == self.course_id:
                self.course_manifest["favorite"] = bool(entry.get("favorite"))
                break

    def _current_progress(self) -> dict:
        return self.course_manifest.get("progress", {}) or {}

    def _current_completed(self) -> set:
        return set(self._current_progress().get("completed_lessons", []) or [])

    def _current_module(self) -> dict | None:
        for module in self.course_manifest.get("modules", []) or []:
            for lesson in module.get("lessons", []) or []:
                if lesson.get("id") == self.selected_lesson_id:
                    return module
        return None

    def _lesson_position(self, lesson_id: str) -> tuple[int, int]:
        if lesson_id in self.lesson_order:
            return self.lesson_order.index(lesson_id) + 1, len(self.lesson_order)
        return 0, len(self.lesson_order)

    def _lesson_meta(self, lesson: dict) -> tuple[str, str]:
        position, total = self._lesson_position(lesson.get("id", ""))
        module = self._current_module()
        module_title = lesson.get("module_title", module.get("title", "") if module else "")
        breadcrumb = f"{module_title} > Lección {position} de {total}" if module_title else f"Lección {position} de {total}"
        subtitle = f"En esta lección aprenderás los conceptos esenciales de {lesson.get('title', '').lower()} y cómo aplicarlos de forma clara y progresiva."
        return breadcrumb, subtitle

    def _draw_progress_ring(self, percent: float):
        self.progress_ring.delete("all")
        self.progress_ring.create_oval(10, 10, 100, 100, outline="#d8e4ec", width=10)
        extent = -max(0.0, min(100.0, percent)) * 3.6
        self.progress_ring.create_arc(10, 10, 100, 100, start=90, extent=extent, style="arc", outline=PALETA["accent"], width=10)
        self.progress_ring_label.configure(text=f"{percent:.0f}%")

    def _render_general_progress(self):
        for child in self.general_stats_container.winfo_children():
            child.destroy()
        installed = list_installed()
        in_progress = sum(1 for item in installed if 0.0 < _safe_float(item.get("progress_percent", 0.0)) < 100.0)
        completed = sum(1 for item in installed if _safe_float(item.get("progress_percent", 0.0)) >= 100.0)
        done_lessons = sum(int(item.get("completed_lessons", 0) or 0) for item in installed)
        total_lessons = sum(max(1, int(item.get("lesson_count", 0) or item.get("total_lessons", 0) or 1)) for item in installed) if installed else 0
        percent = round((done_lessons / total_lessons) * 100.0, 1) if total_lessons else 0.0
        self.var_general_progress.set(f"Progreso total: {percent:.1f}%")

        cards = [
            ("En progreso", str(in_progress), "#8ef2c9"),
            ("Completados", str(completed), "#bfdbfe"),
            ("Total", f"{percent:.0f}%", "#fde68a"),
        ]
        for idx, (label, value, color) in enumerate(cards):
            block = tk.Frame(self.general_stats_container, bg=PALETA["sidebar_soft_alt"], highlightthickness=1, highlightbackground=PALETA["border_dark"])
            block.grid(row=0, column=idx, sticky="nsew", padx=4)
            tk.Label(block, text=label, bg=PALETA["sidebar_soft_alt"], fg=PALETA["text_dim"], font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
            tk.Label(block, text=value, bg=PALETA["sidebar_soft_alt"], fg=color, font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=(0, 8))
            self.general_stats_container.grid_columnconfigure(idx, weight=1)

    def _refresh_sidebar(self):
        for child in self.sidebar_container.winfo_children():
            child.destroy()
        self.lesson_buttons = {}
        self.lesson_order = []
        completed = self._current_completed()
        active_module = self._current_module()

        for module_index, module in enumerate(self.course_manifest.get("modules", []) or [], start=1):
            done, total = self._module_completion_ratio(module)
            is_active = bool(active_module and active_module.get("id") == module.get("id"))
            card = tk.Frame(
                self.sidebar_container,
                bg=PALETA["sidebar_soft_alt"] if is_active else PALETA["sidebar_soft"],
                highlightthickness=1,
                highlightbackground="#4cb98a" if is_active else PALETA["border_dark"],
            )
            card.pack(fill="x", pady=(0, 10))
            head = tk.Frame(card, bg=card.cget("bg"))
            head.pack(fill="x", padx=12, pady=(12, 8))
            tk.Button(
                head,
                text=module.get("title", module.get("id", "")),
                command=lambda m=module: self._open_first_lesson_in_module(m),
                bg=card.cget("bg"),
                fg=PALETA["text"],
                activebackground=card.cget("bg"),
                activeforeground=PALETA["text"],
                relief="flat",
                bd=0,
                anchor="w",
                justify="left",
                wraplength=250,
                padx=0,
                pady=0,
                font=("Arial", 12, "bold"),
                cursor="hand2",
            ).pack(fill="x", anchor="w")
            tk.Label(head, text=f"{done}/{total} lecciones", bg=card.cget("bg"), fg=PALETA["text_dim"], font=("Arial", 10)).pack(anchor="w", pady=(4, 0))
            module_bar = ttk.Progressbar(card, maximum=max(1, total), value=done)
            module_bar.pack(fill="x", padx=12, pady=(0, 12))

            for lesson in module.get("lessons", []) or []:
                lesson_id = lesson.get("id", "")
                self.lesson_order.append(lesson_id)

            if not is_active:
                continue

            lessons_wrap = tk.Frame(card, bg=card.cget("bg"))
            lessons_wrap.pack(fill="x", padx=8, pady=(0, 10))
            for lesson in module.get("lessons", []) or []:
                lesson_id = lesson.get("id", "")
                is_selected = lesson_id == self.selected_lesson_id
                is_done = lesson_id in completed
                indicator = "✓" if is_done else "•"
                btn = tk.Button(
                    lessons_wrap,
                    text=f"{indicator} {lesson.get('title', lesson_id)}",
                    command=lambda target=lesson_id: self.open_lesson(target),
                    bg="#dceafe" if is_selected else card.cget("bg"),
                    fg="#12324f" if is_selected else PALETA["text"],
                    activebackground="#dceafe" if is_selected else card.cget("bg"),
                    activeforeground="#12324f" if is_selected else PALETA["text"],
                    relief="flat",
                    bd=0,
                    anchor="w",
                    justify="left",
                    wraplength=255,
                    padx=12,
                    pady=10,
                    font=("Arial", 10, "bold" if is_selected else "normal"),
                    cursor="hand2",
                )
                btn.pack(fill="x", pady=(0, 6))
                self.lesson_buttons[lesson_id] = btn

        self._render_general_progress()

    def _refresh_header(self):
        progress = self._current_progress()
        percent = _safe_float(progress.get("percent", 0.0))
        total = max(1, self._lesson_count())
        completed = len(self._current_completed())
        completed_modules, total_modules = self._completed_modules()

        self.var_course_title.set(self.course_manifest.get("name", self.course_id))
        self.var_course_meta.set(
            f"{self.course_manifest.get('category', '-')} · {str(self.course_manifest.get('language', '-')).upper()} · {total_modules} módulos · {completed}/{total} lecciones completas"
        )
        self.var_progress_label.set(f"{percent:.1f}% completado")
        
        self.course_progressbar.configure(value=percent)
        self.level_badge.configure(text=self.course_manifest.get("level", "Nivel"))
        self._draw_progress_ring(percent)

        favorito = bool(self.course_manifest.get("favorite"))
        if self.btn_favorite:
            self.btn_favorite.configure(text="Quitar favorito" if favorito else "Favorito")

        navigation_ready = bool(self.selected_lesson_id and self.selected_lesson_id in self.lesson_order)
        prev_state = "normal" if navigation_ready and self.lesson_order.index(self.selected_lesson_id) > 0 else "disabled"
        next_state = "normal" if navigation_ready and self.lesson_order.index(self.selected_lesson_id) < len(self.lesson_order) - 1 else "disabled"
        self.btn_prev.configure(state=prev_state)
        self.btn_next.configure(state=next_state)

    def _clear_content(self):
        for child in self.content_inner.winfo_children():
            child.destroy()

    def _render_lesson_view(self, lesson: dict):
        self._clear_content()
        blocks = _didactic_blocks(lesson)
        completed = self.selected_lesson_id in self._current_completed()

        hero = tk.Frame(self.content_inner, bg=PALETA["card"], highlightthickness=1, highlightbackground=PALETA["border"])
        hero.pack(fill="x", pady=(0, 12))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)

        left = tk.Frame(hero, bg=PALETA["card"])
        left.grid(row=0, column=0, sticky="nsew", padx=22, pady=20)
        tk.Label(left, textvariable=self.var_lesson_title, bg=PALETA["card"], fg=PALETA["content_text"], font=("Arial", 24, "bold"), anchor="w", justify="left", wraplength=720).pack(fill="x")
        tk.Label(left, textvariable=self.var_lesson_subtitle, bg=PALETA["card"], fg=PALETA["content_dim"], font=("Arial", 11), anchor="w", justify="left", wraplength=720).pack(fill="x", pady=(6, 10))

        info = tk.Frame(left, bg=PALETA["accent_soft"], highlightthickness=1, highlightbackground="#bfe8d4")
        info.pack(fill="x")
        tk.Label(info, text="Aprenderás", bg=PALETA["accent_soft"], fg=PALETA["accent_dark"], font=("Arial", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        for item in blocks["learning"][:4]:
            tk.Label(info, text=f"• {item}", bg=PALETA["accent_soft"], fg=PALETA["content_text"], anchor="w", justify="left", wraplength=680).pack(fill="x", padx=14, pady=(0, 6))

        visual = tk.Frame(hero, bg=PALETA["card_alt"], highlightthickness=1, highlightbackground=PALETA["border"])
        visual.grid(row=0, column=1, sticky="ne", padx=(0, 22), pady=22)
        canvas = tk.Canvas(visual, width=200, height=160, bg=PALETA["card_alt"], highlightthickness=0, bd=0)
        canvas.pack()
        canvas.create_oval(32, 18, 168, 142, fill=PALETA["blue_soft"], outline="")
        canvas.create_rectangle(66, 52, 134, 104, fill=PALETA["accent_soft"], outline="")
        initials = "".join(word[:1] for word in lesson.get("title", "Lección").split()[:2]).upper() or "L"
        canvas.create_text(100, 80, text=initials, fill=PALETA["accent_dark"], font=("Arial", 26, "bold"))

        action_row = tk.Frame(self.content_inner, bg=PALETA["surface"])
        action_row.pack(fill="x", pady=(0, 12))
        self.btn_favorite = tk.Button(
            action_row,
            text="Favorito",
            command=self._toggle_favorite,
            bg=PALETA["card"],
            fg=PALETA["content_text"],
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            font=("Arial", 10, "bold"),
            cursor="hand2",
        )
        self.btn_favorite.pack(side="left")
        self.btn_complete = tk.Button(
            action_row,
            text="Completar" if not completed else "Quitar completada",
            command=lambda: self._set_completed(not completed),
            bg=PALETA["accent"] if not completed else PALETA["warn"],
            fg="white",
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            font=("Arial", 10, "bold"),
            cursor="hand2",
        )
        self.btn_complete.pack(side="left", padx=(8, 0))

        if blocks["intro"]:
            intro_card = tk.Frame(self.content_inner, bg=PALETA["card"], highlightthickness=1, highlightbackground=PALETA["border"])
            intro_card.pack(fill="x", pady=(0, 12))
            for paragraph in blocks["intro"]:
                tk.Label(intro_card, text=paragraph, bg=PALETA["card"], fg=PALETA["content_text"], justify="left", anchor="w", wraplength=930, font=("Arial", 11)).pack(fill="x", padx=18, pady=(14 if paragraph == blocks["intro"][0] else 0, 10))

        for block in blocks["blocks"]:
            card = tk.Frame(self.content_inner, bg=PALETA["card"], highlightthickness=1, highlightbackground=PALETA["border"])
            card.pack(fill="x", pady=(0, 12))
            tk.Label(card, text=block["title"], bg=PALETA["card"], fg=PALETA["content_text"], font=("Arial", 14, "bold"), anchor="w").pack(fill="x", padx=18, pady=(16, 8))
            for item in block["items"]:
                bg = PALETA["blue_soft"] if str(item).startswith("• ") else PALETA["card"]
                fg = PALETA["content_text"] if bg == PALETA["card"] else "#17406a"
                pad_y = 10 if bg != PALETA["card"] else 0
                label = tk.Label(
                    card,
                    text=item,
                    bg=bg,
                    fg=fg,
                    justify="left",
                    anchor="w",
                    wraplength=930,
                    font=("Arial", 11),
                    padx=14 if bg != PALETA["card"] else 0,
                    pady=pad_y,
                )
                label.pack(fill="x", padx=18, pady=(0, 10))

        spacer = tk.Frame(self.content_inner, bg=PALETA["surface"], height=6)
        spacer.pack(fill="x")
        self._refresh_header()

    def _reading_fraction(self) -> float:
        try:
            first, _last = self.content_canvas.yview()
            return max(0.0, min(1.0, float(first)))
        except Exception:
            return 0.0

    def _reading_label_for_fraction(self, fraction: float) -> str:
        if fraction <= 0.05:
            tramo = "inicio"
        elif fraction >= 0.9:
            tramo = "final"
        else:
            tramo = "avance"
        restante = max(0.0, (1.0 - fraction) * 100)
        return f"Lectura {fraction * 100:.0f}% · {tramo} · falta {restante:.0f}%"

    def _update_reading_indicator(self):
        fraction = self._reading_fraction()
        self.var_reading_progress.set(self._reading_label_for_fraction(fraction))
        completed = self.selected_lesson_id in self._current_completed()
        self.var_lesson_state.set(_lesson_status_text(completed, fraction))

    def _persist_reading_position(self):
        if not self.selected_lesson_id:
            return
        try:
            save_reading_position(self.course_id, self.selected_lesson_id, self._reading_fraction())
        except Exception as exc:
            self._log(f"No se pudo guardar posición de lectura: {exc}")

    def _schedule_reading_save(self):
        self._update_reading_indicator()
        if self.reading_save_job:
            try:
                self.after_cancel(self.reading_save_job)
            except Exception:
                pass
        self.reading_save_job = self.after(350, self._persist_reading_position)

    def _on_scroll_event(self, event=None):
        if not self.content_canvas or not self.content_canvas.winfo_exists():
            return "break"
        delta = getattr(event, "delta", 0) if event is not None else 0
        if delta:
            self.content_canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        else:
            num = getattr(event, "num", None) if event is not None else None
            if num == 4:
                self.content_canvas.yview_scroll(-1, "units")
            elif num == 5:
                self.content_canvas.yview_scroll(1, "units")
        self.after_idle(self._schedule_reading_save)
        return "break"

    def _scroll_and_track(self, *args):
        self.content_canvas.yview(*args)
        self._schedule_reading_save()

    def _restore_reading_position(self, lesson_id: str):
        fraction = get_reading_position(self.course_id, lesson_id)
        if fraction > 0.0:
            try:
                self.content_canvas.yview_moveto(fraction)
            except Exception:
                pass
        else:
            try:
                self.content_canvas.yview_moveto(0.0)
            except Exception:
                pass
        self._update_reading_indicator()

    def _load_course_view(self):
        self._reload_manifest()
        target_lesson = self.initial_lesson or continue_course(self.course_id)
        self._refresh_sidebar()
        self._refresh_header()
        if target_lesson:
            self.open_lesson(target_lesson)
            return
        if self.course_manifest.get("modules"):
            lessons = self.course_manifest["modules"][0].get("lessons", []) or []
            if lessons:
                self.open_lesson(lessons[0].get("id", ""))

    def open_lesson(self, lesson_id: str):
        if self.lesson_open_in_progress or not lesson_id:
            return
        self.lesson_open_in_progress = True
        try:
            if self.selected_lesson_id and self.selected_lesson_id != lesson_id:
                self._persist_reading_position()
            lesson = get_lesson(self.course_id, lesson_id)
            update_progress(self.course_id, lesson_id)
            self._reload_manifest()
            self.selected_lesson_id = lesson_id

            breadcrumb, subtitle = self._lesson_meta(lesson)
            self.var_lesson_title.set(lesson.get("title", lesson_id))
            self.var_lesson_subtitle.set(subtitle)
            self.var_breadcrumb.set(breadcrumb)
            position, total = self._lesson_position(lesson_id)
            self.var_lesson_counter.set(f"Lección {position} de {total}")

            self._refresh_sidebar()
            self._render_lesson_view(lesson)
            self._restore_reading_position(lesson_id)
            self._notify_host()
        except Exception as exc:
            self._show_error("Abrir lección", str(exc))
        finally:
            self.lesson_open_in_progress = False

    def _open_first_lesson_in_module(self, module: dict):
        lessons = module.get("lessons", []) or []
        if lessons:
            self.open_lesson(lessons[0].get("id", ""))

    def _move_lesson(self, step: int):
        if not self.selected_lesson_id or self.selected_lesson_id not in self.lesson_order:
            return
        index = self.lesson_order.index(self.selected_lesson_id) + step
        if index < 0 or index >= len(self.lesson_order):
            return
        self.open_lesson(self.lesson_order[index])

    def _set_completed(self, completed: bool):
        if not self.selected_lesson_id:
            return
        try:
            update_progress(self.course_id, self.selected_lesson_id, completed=completed)
            self._reload_manifest()
            lesson = get_lesson(self.course_id, self.selected_lesson_id)
            self._refresh_sidebar()
            self._render_lesson_view(lesson)
            self._persist_reading_position()
            self._update_reading_indicator()
            self._notify_host()
        except Exception as exc:
            self._show_error("Actualizar progreso", str(exc))

    def _continue_course(self):
        target = continue_course(self.course_id)
        if target:
            self.open_lesson(target)

    def _toggle_favorite(self):
        favorito = not bool(self.course_manifest.get("favorite"))
        try:
            set_favorite(self.course_id, favorito)
            self._reload_manifest()
            lesson = get_lesson(self.course_id, self.selected_lesson_id) if self.selected_lesson_id else None
            self._refresh_sidebar()
            self._refresh_header()
            if lesson:
                self._render_lesson_view(lesson)
            self._notify_host()
        except Exception as exc:
            self._show_error("Favorito", str(exc))
