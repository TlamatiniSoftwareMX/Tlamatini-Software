import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from tkinter import filedialog, messagebox, ttk

from core.biblioteca import listar_libros
from core.biblioteca_offline import (
    LOCAL_LIBRARY_DIR,
    delete_content,
    download_content,
    list_installed,
    load_catalog,
    open_content,
    reader_state,
    search_catalog,
    set_favorite,
    start_reader,
    stop_reader,
)
from core.ui_theme import FUTURISTA_OSCURO
from core.window_geometry import aplicar_geometria_relativa, habilitar_scroll_mouse


def _fmt_size_bytes(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size_bytes} B"


def _parse_size_to_bytes(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value or "").strip().upper()
    if not text:
        return 0
    parts = text.replace(",", ".").split()
    if not parts:
        return 0
    try:
        amount = float(parts[0])
    except ValueError:
        return 0
    unit = parts[1] if len(parts) > 1 else "B"
    factors = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }
    return int(amount * factors.get(unit, 1))


def _parse_sort_date(value: str):
    text = str(value or "").strip()
    if not text:
        return datetime.min
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.min


SORT_OPTIONS = [
    "Última descarga",
    "Primera descarga",
    "Tamaño más chico",
    "Tamaño más grande",
    "Tipo",
    "A-Z",
    "Z-A",
]


STATUS_LABELS = {
    "no_descargado": "No descargado",
    "descargando": "Descargando",
    "descargado": "Descargado",
    "instalando": "Instalando",
    "listo_para_abrir": "Listo para abrir",
    "lector_iniciando": "Lector iniciando",
    "lector_activo": "Lector activo",
    "error": "Error",
    "cancelado": "Cancelado",
    "inactivo": "Sin lector activo",
}


def _label_status(status: str) -> str:
    return STATUS_LABELS.get(status or "", status or "-")


class VentanaBiblioteca:
    def __init__(self, root):
        self.root = root
        self.root.title("TLAMATINI - Biblioteca")
        self.ui = FUTURISTA_OSCURO
        self.root.configure(bg=self.ui["fondo"])
        self.root.minsize(1260, 760)
        aplicar_geometria_relativa(self.root, self.root.master, rel_w=0.9, rel_h=0.88, min_w=1260, min_h=760)

        self.catalog_items = []
        self.installed_items = []
        self.document_items = []
        self.queue = Queue()
        self.current_worker = None
        self.selected_content_id = ""
        self.selected_document_id = ""

        self.var_catalog_search = tk.StringVar()
        self.var_library_search = tk.StringVar()
        self.var_docs_search = tk.StringVar()
        self.var_filter_category = tk.StringVar(value="Todas")
        self.var_filter_language = tk.StringVar(value="Todos")
        self.var_filter_type = tk.StringVar(value="Todos")
        self.var_catalog_sort = tk.StringVar(value="Última descarga")
        self.var_library_sort = tk.StringVar(value="Última descarga")
        self.var_status = tk.StringVar(value="Biblioteca lista.")
        self.var_reader = tk.StringVar(value="Sin lector activo.")
        self.var_progress = tk.DoubleVar(value=0.0)

        self._build_ui()
        self._refresh_all()
        self._poll_queue()

    def _build_ui(self):
        container = tk.Frame(self.root, bg=self.ui["fondo"])
        container.pack(fill="both", expand=True)

        header = tk.Frame(container, bg=self.ui["fondo"])
        header.pack(fill="x", padx=22, pady=(18, 10))
        tk.Label(
            header,
            text="BIBLIOTECA",
            font=("Arial", 28, "bold"),
            bg=self.ui["fondo"],
            fg=self.ui["texto"],
        ).pack(side="left")
        tk.Label(
            header,
            text="Biblioteca offline",
            font=("Arial", 11),
            bg=self.ui["fondo"],
            fg="#cbd5e1",
        ).pack(side="left", padx=(16, 0), pady=(8, 0))

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        self.tab_offline = tk.Frame(notebook, bg=self.ui["fondo"])
        self.tab_docs = tk.Frame(notebook, bg=self.ui["fondo"])
        notebook.add(self.tab_offline, text="Biblioteca offline")
        notebook.add(self.tab_docs, text="Documentos locales")

        self._build_offline_tab()
        self._build_docs_tab()

        footer = tk.Frame(container, bg=self.ui["fondo"])
        footer.pack(fill="x", padx=22, pady=(0, 16))
        ttk.Progressbar(footer, variable=self.var_progress, maximum=100).pack(fill="x")
        tk.Label(footer, textvariable=self.var_status, bg=self.ui["fondo"], fg="#93c5fd", anchor="w").pack(fill="x", pady=(8, 0))
        tk.Label(footer, textvariable=self.var_reader, bg=self.ui["fondo"], fg="#86efac", anchor="w").pack(fill="x", pady=(2, 0))

    def _build_offline_tab(self):
        wrap = tk.Frame(self.tab_offline, bg=self.ui["fondo"])
        wrap.pack(fill="both", expand=True, padx=8, pady=8)

        filters = tk.Frame(wrap, bg=self.ui["fondo"])
        filters.pack(fill="x", pady=(0, 10))
        tk.Label(filters, text="Categoría", bg=self.ui["fondo"], fg=self.ui["texto"]).pack(side="left")
        self.category_combo = ttk.Combobox(filters, textvariable=self.var_filter_category, state="readonly", width=28, values=["Todas"])
        self.category_combo.pack(side="left", padx=(8, 14))
        self.category_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        tk.Label(filters, text="Idioma", bg=self.ui["fondo"], fg=self.ui["texto"]).pack(side="left")
        self.language_combo = ttk.Combobox(filters, textvariable=self.var_filter_language, state="readonly", width=10, values=["Todos"])
        self.language_combo.pack(side="left", padx=(8, 14))
        self.language_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        tk.Label(filters, text="Tipo", bg=self.ui["fondo"], fg=self.ui["texto"]).pack(side="left")
        self.type_combo = ttk.Combobox(filters, textvariable=self.var_filter_type, state="readonly", width=14, values=["Todos"])
        self.type_combo.pack(side="left", padx=(8, 0))
        self.type_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        panes = tk.PanedWindow(wrap, orient="horizontal", sashrelief="flat", bg=self.ui["fondo"], bd=0)
        panes.pack(fill="both", expand=True)

        catalog_card = self._panel_card(panes, "Catálogo disponible")
        library_card = self._panel_card(panes, "Mi biblioteca")
        detail_card = self._panel_card(panes, "Detalle / Lector")

        panes.add(catalog_card, minsize=360)
        panes.add(library_card, minsize=340)
        panes.add(detail_card, minsize=360)

        self._build_catalog_panel(catalog_card)
        self._build_library_panel(library_card)
        self._build_detail_panel(detail_card)

    def _build_docs_tab(self):
        wrap = tk.Frame(self.tab_docs, bg=self.ui["fondo"])
        wrap.pack(fill="both", expand=True, padx=10, pady=10)
        wrap.grid_columnconfigure(0, weight=3)
        wrap.grid_columnconfigure(1, weight=2)
        wrap.grid_rowconfigure(1, weight=1)

        top = tk.Frame(wrap, bg=self.ui["fondo"])
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        tk.Label(top, text="Buscar documento", bg=self.ui["fondo"], fg=self.ui["texto"]).pack(side="left")
        entry = tk.Entry(top, textvariable=self.var_docs_search, bg="#0b1220", fg="white", insertbackground="white", relief="flat")
        entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        entry.bind("<KeyRelease>", lambda _event: self._refresh_documents())
        tk.Button(top, text="Abrir archivo", command=self._open_selected_document, bg="#2563eb", fg="white", relief="flat", padx=12, pady=6).pack(side="left")

        table_wrap = self._panel_card(wrap, "Documentos indexados")
        table_wrap.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        table_wrap.grid_rowconfigure(1, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        cols = ("nombre", "tipo", "categoria", "fecha")
        self.docs_tree = ttk.Treeview(table_wrap, columns=cols, show="headings")
        for col, title, width in (
            ("nombre", "Documento", 300),
            ("tipo", "Tipo", 90),
            ("categoria", "Categoría", 150),
            ("fecha", "Fecha", 150),
        ):
            self.docs_tree.heading(col, text=title)
            self.docs_tree.column(col, width=width, anchor="w" if col == "nombre" else "center")
        self.docs_tree.grid(row=1, column=0, sticky="nsew")
        self.docs_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_document_detail())
        yscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.docs_tree.yview)
        yscroll.grid(row=1, column=1, sticky="ns")
        self.docs_tree.configure(yscrollcommand=yscroll.set)
        habilitar_scroll_mouse(table_wrap, self.docs_tree)

        detail_wrap = self._panel_card(wrap, "Detalle del documento")
        detail_wrap.grid(row=1, column=1, sticky="nsew")
        detail_wrap.grid_rowconfigure(0, weight=1)
        detail_wrap.grid_columnconfigure(0, weight=1)

        self.docs_detail = tk.Text(detail_wrap, bg="#07102a", fg="white", insertbackground="white", wrap="word", relief="flat")
        self.docs_detail.grid(row=0, column=0, sticky="nsew")
        habilitar_scroll_mouse(detail_wrap, self.docs_detail)

    def _panel_card(self, parent, title):
        frame = tk.LabelFrame(
            parent,
            text=title,
            bg=self.ui["panel"],
            fg=self.ui["texto"],
            bd=1,
            relief="solid",
            labelanchor="nw",
            font=("Arial", 12, "bold"),
            padx=12,
            pady=12,
        )
        return frame

    def _build_catalog_panel(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        search_row = tk.Frame(parent, bg=self.ui["panel"])
        search_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(search_row, text="Buscar", bg=self.ui["panel"], fg=self.ui["texto"]).pack(side="left")
        entry = tk.Entry(search_row, textvariable=self.var_catalog_search, bg="#0b1220", fg="white", insertbackground="white", relief="flat")
        entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        entry.bind("<KeyRelease>", lambda _event: self._refresh_catalog())
        tk.Label(search_row, text="Orden", bg=self.ui["panel"], fg=self.ui["texto"]).pack(side="left", padx=(0, 8))
        sort_combo = ttk.Combobox(search_row, textvariable=self.var_catalog_sort, state="readonly", width=18, values=SORT_OPTIONS)
        sort_combo.pack(side="left", padx=(0, 8))
        sort_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_catalog())
        tk.Button(search_row, text="Recargar", command=self._refresh_catalog, bg="#334155", fg="white", relief="flat", padx=10, pady=6).pack(side="left")

        cols = ("name", "lang", "cat", "size", "status")
        self.catalog_tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col, title, width in (
            ("name", "Contenido", 220),
            ("lang", "Idioma", 60),
            ("cat", "Categoría", 110),
            ("size", "Tamaño", 90),
            ("status", "Estado", 100),
        ):
            self.catalog_tree.heading(col, text=title)
            self.catalog_tree.column(col, width=width, anchor="w" if col == "name" else "center")
        self.catalog_tree.grid(row=1, column=0, sticky="nsew")
        self.catalog_tree.bind("<<TreeviewSelect>>", lambda _event: self._select_from_catalog())
        yscroll = ttk.Scrollbar(parent, orient="vertical", command=self.catalog_tree.yview)
        yscroll.grid(row=1, column=1, sticky="ns")
        self.catalog_tree.configure(yscrollcommand=yscroll.set)
        habilitar_scroll_mouse(parent, self.catalog_tree)

        actions = tk.Frame(parent, bg=self.ui["panel"])
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        tk.Button(actions, text="Descargar", command=self._download_selected, bg="#2563eb", fg="white", relief="flat", padx=12, pady=7).pack(side="left")

    def _build_library_panel(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        search_row = tk.Frame(parent, bg=self.ui["panel"])
        search_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(search_row, text="Buscar", bg=self.ui["panel"], fg=self.ui["texto"]).pack(side="left")
        entry = tk.Entry(search_row, textvariable=self.var_library_search, bg="#0b1220", fg="white", insertbackground="white", relief="flat")
        entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        entry.bind("<KeyRelease>", lambda _event: self._refresh_library())
        tk.Label(search_row, text="Orden", bg=self.ui["panel"], fg=self.ui["texto"]).pack(side="left", padx=(0, 8))
        sort_combo = ttk.Combobox(search_row, textvariable=self.var_library_sort, state="readonly", width=18, values=SORT_OPTIONS)
        sort_combo.pack(side="left", padx=(0, 8))
        sort_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_library())
        tk.Button(search_row, text="Recargar", command=self._refresh_library, bg="#334155", fg="white", relief="flat", padx=10, pady=6).pack(side="left")

        cols = ("fav", "name", "lang", "size", "status")
        self.library_tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col, title, width in (
            ("fav", "★", 40),
            ("name", "Contenido", 220),
            ("lang", "Idioma", 60),
            ("size", "Tamaño", 90),
            ("status", "Estado", 90),
        ):
            self.library_tree.heading(col, text=title)
            self.library_tree.column(col, width=width, anchor="w" if col == "name" else "center")
        self.library_tree.grid(row=1, column=0, sticky="nsew")
        self.library_tree.bind("<<TreeviewSelect>>", lambda _event: self._select_from_library())
        yscroll = ttk.Scrollbar(parent, orient="vertical", command=self.library_tree.yview)
        yscroll.grid(row=1, column=1, sticky="ns")
        self.library_tree.configure(yscrollcommand=yscroll.set)
        habilitar_scroll_mouse(parent, self.library_tree)

        actions = tk.Frame(parent, bg=self.ui["panel"])
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        tk.Button(actions, text="Abrir", command=self._open_selected_content, bg="#0f766e", fg="white", relief="flat", padx=12, pady=7).pack(side="left")

    def _build_detail_panel(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        summary = tk.Frame(parent, bg=self.ui["panel"])
        summary.grid(row=0, column=0, sticky="ew")
        self.detail_title = tk.Label(summary, text="Selecciona un contenido", font=("Arial", 16, "bold"), bg=self.ui["panel"], fg=self.ui["texto"])
        self.detail_title.pack(anchor="w")
        self.detail_meta = tk.Label(summary, text="", bg=self.ui["panel"], fg="#93c5fd", justify="left")
        self.detail_meta.pack(anchor="w", pady=(4, 10))

        self.detail_text = tk.Text(parent, bg="#07102a", fg="white", insertbackground="white", wrap="word", relief="flat")
        self.detail_text.grid(row=1, column=0, sticky="nsew")

        actions = tk.Frame(parent, bg=self.ui["panel"])
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        tk.Button(actions, text="Descargar", command=self._download_selected, bg="#2563eb", fg="white", relief="flat", padx=12, pady=7).pack(side="left")
        tk.Button(actions, text="Iniciar lector", command=self._start_reader_selected, bg="#1d4ed8", fg="white", relief="flat", padx=12, pady=7).pack(side="left", padx=(8, 0))
        tk.Button(actions, text="Abrir lectura", command=self._open_selected_content, bg="#0f766e", fg="white", relief="flat", padx=12, pady=7).pack(side="left", padx=(8, 0))
        tk.Button(actions, text="Detener lector", command=self._stop_reader_ui, bg="#475569", fg="white", relief="flat", padx=12, pady=7).pack(side="left", padx=(8, 0))

        actions2 = tk.Frame(parent, bg=self.ui["panel"])
        actions2.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        tk.Button(actions2, text="Favorito", command=self._toggle_favorite_selected, bg="#7c3aed", fg="white", relief="flat", padx=12, pady=7).pack(side="left")
        tk.Button(actions2, text="Eliminar", command=self._delete_selected, bg="#b91c1c", fg="white", relief="flat", padx=12, pady=7).pack(side="left", padx=(8, 0))
        tk.Button(actions2, text="Abrir carpeta", command=self._open_library_folder, bg="#334155", fg="white", relief="flat", padx=12, pady=7).pack(side="left", padx=(8, 0))

    def _refresh_all(self):
        self._refresh_filter_options()
        self._refresh_catalog()
        self._refresh_library()
        self._refresh_documents()
        self._update_detail_panel()

    def _refresh_filter_options(self):
        entries = load_catalog()
        categories = ["Todas"] + sorted({str(item.get("category", "")).strip() for item in entries if str(item.get("category", "")).strip()})
        languages = ["Todos"] + sorted({str(item.get("language", "")).strip() for item in entries if str(item.get("language", "")).strip()})
        types = ["Todos"] + sorted({str(item.get("content_type", "")).strip() for item in entries if str(item.get("content_type", "")).strip()})

        self.category_combo.configure(values=categories)
        self.language_combo.configure(values=languages)
        self.type_combo.configure(values=types)

        if self.var_filter_category.get() not in categories:
            self.var_filter_category.set("Todas")
        if self.var_filter_language.get() not in languages:
            self.var_filter_language.set("Todos")
        if self.var_filter_type.get() not in types:
            self.var_filter_type.set("Todos")

    def _matches_filters(self, item):
        category = self.var_filter_category.get()
        language = self.var_filter_language.get()
        content_type = self.var_filter_type.get()

        if category not in {"", "Todas"} and str(item.get("category", "")) != category:
            return False
        if language not in {"", "Todos"} and str(item.get("language", "")) != language:
            return False
        if content_type not in {"", "Todos"} and str(item.get("content_type", "")) != content_type:
            return False
        return True

    def _sort_catalog_items(self, items):
        mode = self.var_catalog_sort.get()
        if mode == "Primera descarga":
            return sorted(items, key=lambda item: (_parse_sort_date(item.get("version", "")), str(item.get("name", "")).lower()))
        if mode == "Última descarga":
            return sorted(items, key=lambda item: (_parse_sort_date(item.get("version", "")), str(item.get("name", "")).lower()), reverse=True)
        if mode == "Tamaño más chico":
            return sorted(items, key=lambda item: (_parse_size_to_bytes(item.get("size_bytes") or item.get("size_human")), str(item.get("name", "")).lower()))
        if mode == "Tamaño más grande":
            return sorted(items, key=lambda item: (_parse_size_to_bytes(item.get("size_bytes") or item.get("size_human")), str(item.get("name", "")).lower()), reverse=True)
        if mode == "Tipo":
            return sorted(items, key=lambda item: (str(item.get("content_type", "")).lower(), str(item.get("name", "")).lower()))
        if mode == "Z-A":
            return sorted(items, key=lambda item: str(item.get("name", "")).lower(), reverse=True)
        return sorted(items, key=lambda item: str(item.get("name", "")).lower())

    def _sort_library_items(self, items):
        mode = self.var_library_sort.get()
        if mode == "Primera descarga":
            return sorted(items, key=lambda item: (_parse_sort_date(item.get("installed_at", "")), str(item.get("name", "")).lower()))
        if mode == "Última descarga":
            return sorted(items, key=lambda item: (_parse_sort_date(item.get("installed_at", "")), str(item.get("name", "")).lower()), reverse=True)
        if mode == "Tamaño más chico":
            return sorted(items, key=lambda item: (_parse_size_to_bytes(item.get("size_bytes") or item.get("size_human")), str(item.get("name", "")).lower()))
        if mode == "Tamaño más grande":
            return sorted(items, key=lambda item: (_parse_size_to_bytes(item.get("size_bytes") or item.get("size_human")), str(item.get("name", "")).lower()), reverse=True)
        if mode == "Tipo":
            return sorted(items, key=lambda item: (str(item.get("content_type", item.get("format", ""))).lower(), str(item.get("name", "")).lower()))
        if mode == "Z-A":
            return sorted(items, key=lambda item: str(item.get("name", "")).lower(), reverse=True)
        return sorted(items, key=lambda item: str(item.get("name", "")).lower())

    def _refresh_catalog(self):
        self.catalog_items = [item for item in search_catalog(self.var_catalog_search.get().strip()) if self._matches_filters(item)]
        self.catalog_items = self._sort_catalog_items(self.catalog_items)
        selected = self.selected_content_id
        self.catalog_tree.delete(*self.catalog_tree.get_children())
        for item in self.catalog_items:
            self.catalog_tree.insert(
                "",
                "end",
                iid=item["id"],
                values=(
                    item.get("name", ""),
                    item.get("language", ""),
                    item.get("category", ""),
                    item.get("size_human") or _fmt_size_bytes(int(item.get("size_bytes") or 0)),
                    _label_status(item.get("status", "")),
                ),
            )
        if selected and self.catalog_tree.exists(selected):
            self.catalog_tree.selection_set(selected)

    def _refresh_library(self):
        self.installed_items = [item for item in list_installed(self.var_library_search.get().strip()) if self._matches_filters(item)]
        self.installed_items = self._sort_library_items(self.installed_items)
        selected = self.selected_content_id
        self.library_tree.delete(*self.library_tree.get_children())
        for item in self.installed_items:
            self.library_tree.insert(
                "",
                "end",
                iid=item["id"],
                values=(
                    "★" if item.get("favorite") else "",
                    item.get("name", ""),
                    item.get("language", ""),
                    item.get("size_human") or _fmt_size_bytes(int(item.get("size_bytes") or 0)),
                    _label_status(item.get("status", "")),
                ),
            )
        if selected and self.library_tree.exists(selected):
            self.library_tree.selection_set(selected)

    def _refresh_documents(self):
        query = (self.var_docs_search.get() or "").strip().lower()
        self.document_items = []
        for item in listar_libros():
            haystack = " ".join(
                [
                    str(item.get("nombre", "")),
                    str(item.get("tipo_archivo", "")),
                    str(item.get("categoria_nombre", "")),
                    str(item.get("dominio", "")),
                ]
            ).lower()
            if query and query not in haystack:
                continue
            self.document_items.append(item)

        selected = self.selected_document_id
        self.docs_tree.delete(*self.docs_tree.get_children())
        for item in self.document_items:
            self.docs_tree.insert(
                "",
                "end",
                iid=item["id"],
                values=(
                    item.get("nombre", ""),
                    item.get("tipo_archivo", ""),
                    item.get("categoria_nombre", ""),
                    item.get("fecha_carga", ""),
                ),
            )
        if selected and self.docs_tree.exists(selected):
            self.docs_tree.selection_set(selected)
        self._update_document_detail()

    def _find_current_item(self):
        if not self.selected_content_id:
            return None
        for item in self.installed_items:
            if item.get("id") == self.selected_content_id:
                return item
        for item in self.catalog_items:
            if item.get("id") == self.selected_content_id:
                return item
        return None

    def _select_from_catalog(self):
        selection = self.catalog_tree.selection()
        if not selection:
            return
        self.selected_content_id = selection[0]
        self.library_tree.selection_remove(self.library_tree.selection())
        self._update_detail_panel()

    def _select_from_library(self):
        selection = self.library_tree.selection()
        if not selection:
            return
        self.selected_content_id = selection[0]
        self.catalog_tree.selection_remove(self.catalog_tree.selection())
        self._update_detail_panel()

    def _update_detail_panel(self):
        item = self._find_current_item()
        self.detail_text.delete("1.0", "end")
        if not item:
            self.detail_title.config(text="Selecciona un contenido")
            self.detail_meta.config(text="")
            self.detail_text.insert("1.0", "Selecciona un elemento del catálogo o de la biblioteca instalada.")
            self._refresh_reader_label()
            return

        self.detail_title.config(text=item.get("name", item.get("id", "")))
        meta = [
            f"Idioma: {item.get('language', '-')}",
            f"Categoría: {item.get('category', '-')}",
            f"Tamaño: {item.get('size_human') or _fmt_size_bytes(int(item.get('size_bytes') or 0))}",
            f"Formato: {item.get('format', '-')}",
            f"Estado: {_label_status(item.get('status', '-'))}",
        ]
        self.detail_meta.config(text=" | ".join(meta))

        detail_lines = [f"Descripción: {item.get('description', '')}"]
        if item.get("installed_path"):
            detail_lines.extend(
                [
                    "",
                    f"Ruta local: {item.get('installed_path', '')}",
                    f"Instalado: {item.get('installed_at', '')}",
                ]
            )
        if item.get("download_error"):
            detail_lines.append("")
            detail_lines.append(f"Error: {item.get('download_error')}")
        if item.get("reader_hint") == "pesado":
            detail_lines.append("")
            detail_lines.append("Advertencia: este contenido es pesado y puede tardar tanto en descargar como en abrir.")

        current_reader = reader_state()
        if current_reader.get("content_id") == item.get("id"):
            detail_lines.extend(
                [
                    "",
                    f"Lector activo en: {current_reader.get('url', '')}",
                    "Puedes usar el buscador nativo de Kiwix dentro de la página abierta.",
                ]
            )

        self.detail_text.insert("1.0", "\n".join(detail_lines))
        self._refresh_reader_label()

    def _update_document_detail(self):
        self.docs_detail.delete("1.0", "end")
        selection = self.docs_tree.selection()
        if not selection:
            self.docs_detail.insert("1.0", "Selecciona un documento local para ver su detalle.")
            return
        self.selected_document_id = selection[0]
        item = next((doc for doc in self.document_items if doc.get("id") == self.selected_document_id), None)
        if not item:
            self.docs_detail.insert("1.0", "No se encontró el documento.")
            return
        detail = [
            f"Nombre: {item.get('nombre', '')}",
            f"Ruta: {item.get('ruta', '')}",
            f"Categoría: {item.get('categoria_nombre', '')}",
            f"Tipo: {item.get('tipo_archivo', '')}",
            f"Páginas: {item.get('paginas', '')}",
            f"Fecha de carga: {item.get('fecha_carga', '')}",
            "",
            f"Temas: {', '.join(item.get('temas_detectados', [])) if item.get('temas_detectados') else '-'}",
        ]
        self.docs_detail.insert("1.0", "\n".join(detail))

    def _set_busy(self, message: str):
        self.var_status.set(message)

    def _run_background(self, worker):
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showwarning("Operación en curso", "Ya hay una operación en segundo plano ejecutándose.", parent=self.root)
            return False
        self.current_worker = threading.Thread(target=worker, daemon=True)
        self.current_worker.start()
        return True

    def _download_selected(self):
        item = self._find_current_item()
        if not item:
            messagebox.showwarning("Selecciona contenido", "Selecciona primero un contenido del catálogo o biblioteca.", parent=self.root)
            return
        content_id = item["id"]

        def worker():
            self.queue.put(("status", f"Descargando {item.get('name', content_id)}..."))
            result = download_content(content_id, progress_callback=lambda payload: self.queue.put(("progress", payload)))
            self.queue.put(("download_done", content_id, result))

        self._run_background(worker)

    def _start_reader_selected(self):
        item = self._find_current_item()
        if not item:
            messagebox.showwarning("Selecciona contenido", "Selecciona un contenido instalado.", parent=self.root)
            return
        if not item.get("verified_complete"):
            messagebox.showwarning("Contenido no listo", "El contenido todavía no está verificado y listo para abrir.", parent=self.root)
            return

        def worker():
            self.queue.put(("status", f"Iniciando lector para {item.get('name', item['id'])}..."))
            result = start_reader(item["id"], progress_callback=lambda payload: self.queue.put(("progress", payload)))
            self.queue.put(("reader_done", item["id"], result, False))

        self._run_background(worker)

    def _open_selected_content(self):
        item = self._find_current_item()
        if not item:
            messagebox.showwarning("Selecciona contenido", "Selecciona un contenido instalado.", parent=self.root)
            return
        if not item.get("verified_complete"):
            messagebox.showwarning("Contenido no listo", "El contenido no está descargado y verificado.", parent=self.root)
            return

        def worker():
            self.queue.put(("status", f"Abriendo {item.get('name', item['id'])}..."))
            result = open_content(item["id"], progress_callback=lambda payload: self.queue.put(("progress", payload)))
            self.queue.put(("reader_done", item["id"], result, True))

        self._run_background(worker)

    def _stop_reader_ui(self):
        stop_reader()
        self.var_status.set("Lector detenido.")
        self._refresh_reader_label()
        self._update_detail_panel()

    def _toggle_favorite_selected(self):
        item = self._find_current_item()
        if not item:
            messagebox.showwarning("Selecciona contenido", "Selecciona un contenido para marcarlo como favorito.", parent=self.root)
            return
        favorito_actual = bool(item.get("favorite"))
        set_favorite(item["id"], not favorito_actual)
        self.var_status.set("Favorito actualizado.")
        self._refresh_catalog()
        self._refresh_library()
        self._update_detail_panel()

    def _delete_selected(self):
        item = self._find_current_item()
        if not item or not item.get("installed_path"):
            messagebox.showwarning("Selecciona contenido", "Selecciona un contenido instalado para eliminarlo.", parent=self.root)
            return
        if not messagebox.askyesno("Eliminar contenido", f"¿Eliminar '{item.get('name', item['id'])}' de la biblioteca local?", parent=self.root):
            return
        result = delete_content(item["id"])
        self.var_status.set(result.get("message", ""))
        self._refresh_catalog()
        self._refresh_library()
        self._update_detail_panel()

    def _open_selected_document(self):
        selection = self.docs_tree.selection()
        if not selection:
            messagebox.showwarning("Selecciona documento", "Selecciona un documento local.", parent=self.root)
            return
        item = next((doc for doc in self.document_items if doc.get("id") == selection[0]), None)
        if not item:
            return
        ruta = Path(item.get("ruta", ""))
        if not ruta.exists():
            messagebox.showerror("No encontrado", "El archivo ya no existe en la ruta registrada.", parent=self.root)
            return
        try:
            webbrowser.open(ruta.resolve().as_uri())
        except Exception:
            filedialog.askopenfilename(initialdir=str(ruta.parent), initialfile=ruta.name, parent=self.root)

    def _open_library_folder(self):
        try:
            webbrowser.open(LOCAL_LIBRARY_DIR.resolve().as_uri())
        except Exception:
            pass
        self.var_status.set(f"Carpeta de biblioteca: {LOCAL_LIBRARY_DIR}")

    def _refresh_reader_label(self):
        current = reader_state()
        if current.get("status") == "lector_activo":
            self.var_reader.set(f"Lector activo: {current.get('url', '')}")
        elif current.get("status") == "lector_iniciando":
            self.var_reader.set("Lector iniciando...")
        elif current.get("status") == "error":
            self.var_reader.set(f"Error del lector: {current.get('last_error', 'sin detalle')}")
        else:
            self.var_reader.set("Sin lector activo.")

    def _poll_queue(self):
        try:
            while True:
                event = self.queue.get_nowait()
                self._handle_queue_event(event)
        except Empty:
            pass
        self.root.after(150, self._poll_queue)

    def _handle_queue_event(self, event):
        kind = event[0]
        if kind == "status":
            self.var_status.set(event[1])
            return
        if kind == "progress":
            payload = event[1]
            progress = float(payload.get("progress", 0.0)) * 100.0
            self.var_progress.set(progress)
            status = payload.get("status", "")
            if status == "runtime_descargando":
                self.var_status.set(payload.get("message", "Descargando runtime Kiwix..."))
            elif status == "descargando":
                self.var_status.set(
                    f"Descargando... {progress:.1f}% ({_fmt_size_bytes(int(payload.get('downloaded_bytes', 0)))}/{_fmt_size_bytes(int(payload.get('total_bytes', 0)))})"
                )
            return
        if kind == "download_done":
            _content_id, result = event[1], event[2]
            self.var_progress.set(0.0)
            self.var_status.set(result.get("message", ""))
            self._refresh_catalog()
            self._refresh_library()
            self._update_detail_panel()
            return
        if kind == "reader_done":
            _content_id, result, opened = event[1], event[2], event[3]
            self.var_progress.set(0.0)
            if result.get("ok"):
                action = "abierto" if opened else "iniciado"
                self.var_status.set(f"Lector {action} correctamente.")
            else:
                self.var_status.set(result.get("message", "No se pudo abrir el lector."))
            self._refresh_reader_label()
            self._update_detail_panel()
