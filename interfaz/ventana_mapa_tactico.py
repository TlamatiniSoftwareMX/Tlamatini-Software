import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Dict

from core.capas_tacticas import LAYER_DEFS, agregar_poligono_tactico, agregar_punto_tactico, agregar_ruta_tactica, importar_geojson_capa, resumen_capas
from core.mapas_offline import get_offline_maps_service
from core.mapas_repo import obtener_mapa, obtener_mapa_activo, registrar_mapa_tiles
from core.window_geometry import aplicar_geometria_relativa, habilitar_scroll_mouse
from interfaz.mapa_canvas import OfflineMapCanvas
from interfaz.mapa_runtime import open_map_viewer, update_map_runtime


class VentanaMapa(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("TLAMATINI IA - Mapa")
        self.configure(bg="#111827")
        aplicar_geometria_relativa(self, master, rel_w=0.95, rel_h=0.92, min_w=1320, min_h=840)
        self.service = get_offline_maps_service()
        self.catalog_index = {}
        self.installed_index = {}
        self.selected_catalog_id = ""
        self.selected_installed_id = ""
        self._last_task_snapshot = {}
        self.viewer_url = ""
        self.current_active_id = ""
        self.viewer_opened_for = ""
        self.catalog_menu = None
        self.installed_menu = None
        self._build_ui()
        self._refresh_all()
        self.after(500, self._poll_state)

    def _build_ui(self):
        root = tk.Frame(self, bg="#111827")
        root.pack(fill="both", expand=True, padx=12, pady=12)

        header = tk.Frame(root, bg="#111827")
        header.pack(fill="x", pady=(0, 10))

        tk.Label(header, text="MAPA OFFLINE", font=("Arial", 20, "bold"), bg="#111827", fg="white").pack(anchor="w")
        tk.Label(
            header,
            text="Descarga, gestiona y visualiza mapas offline dentro de TLAMATINI.",
            font=("Arial", 10),
            bg="#111827",
            fg="#cbd5e1",
        ).pack(anchor="w", pady=(4, 0))

        body = tk.PanedWindow(root, orient="horizontal", sashwidth=8, bg="#111827")
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg="#111827", width=430)
        center = tk.Frame(body, bg="#111827")
        right = tk.Frame(body, bg="#111827", width=310)
        body.add(left, minsize=390)
        body.add(center, minsize=620)
        body.add(right, minsize=280)

        self._build_left(left)
        self._build_center(center)
        self._build_right(right)

    def _build_left(self, parent):
        active_panel = tk.LabelFrame(parent, text="Mapa activo", bg="#1f2937", fg="white", bd=1, relief="groove")
        active_panel.pack(fill="x", pady=(0, 10))
        self.active_label = tk.Label(active_panel, text="Sin mapa activo", bg="#1f2937", fg="#93c5fd", font=("Arial", 11, "bold"))
        self.active_label.pack(anchor="w", padx=10, pady=(10, 2))
        self.active_meta = tk.Label(active_panel, text="", justify="left", bg="#1f2937", fg="#d1d5db", font=("Arial", 9))
        self.active_meta.pack(anchor="w", padx=10, pady=(0, 10))

        catalog_panel = tk.LabelFrame(parent, text="Catálogo disponible", bg="#1f2937", fg="white", bd=1, relief="groove")
        catalog_panel.pack(fill="both", expand=True, pady=(0, 10))

        self.catalog_tree = ttk.Treeview(catalog_panel, columns=("region", "size", "status"), show="tree headings", height=8)
        self.catalog_tree.heading("#0", text="Mapa")
        self.catalog_tree.column("#0", width=170, stretch=True)
        for col, title, width in [("region", "Región", 100), ("size", "Tamaño", 90), ("status", "Estado", 110)]:
            self.catalog_tree.heading(col, text=title)
            self.catalog_tree.column(col, width=width, stretch=True)
        self.catalog_tree.bind("<<TreeviewSelect>>", self._on_catalog_select)
        self.catalog_tree.bind("<Button-3>", self._show_catalog_menu)
        catalog_scroll = ttk.Scrollbar(catalog_panel, orient="vertical", command=self.catalog_tree.yview)
        self.catalog_tree.configure(yscrollcommand=catalog_scroll.set)
        self.catalog_tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        catalog_scroll.pack(side="right", fill="y", padx=(0, 10), pady=10)
        habilitar_scroll_mouse(catalog_panel, self.catalog_tree)

        installed_panel = tk.LabelFrame(parent, text="Mapas instalados", bg="#1f2937", fg="white", bd=1, relief="groove")
        installed_panel.pack(fill="both", expand=True)
        self.installed_tree = ttk.Treeview(installed_panel, columns=("region", "size", "version"), show="tree headings", height=8)
        self.installed_tree.heading("#0", text="Mapa")
        self.installed_tree.column("#0", width=170, stretch=True)
        for col, title, width in [("region", "Región", 100), ("size", "Tamaño", 90), ("version", "Versión", 90)]:
            self.installed_tree.heading(col, text=title)
            self.installed_tree.column(col, width=width, stretch=True)
        self.installed_tree.bind("<<TreeviewSelect>>", self._on_installed_select)
        self.installed_tree.bind("<Button-3>", self._show_installed_menu)
        installed_scroll = ttk.Scrollbar(installed_panel, orient="vertical", command=self.installed_tree.yview)
        self.installed_tree.configure(yscrollcommand=installed_scroll.set)
        self.installed_tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        installed_scroll.pack(side="right", fill="y", padx=(0, 10), pady=10)
        habilitar_scroll_mouse(installed_panel, self.installed_tree)

    def _build_center(self, parent):
        viewer_panel = tk.LabelFrame(parent, text="Visor", bg="#1f2937", fg="white", bd=1, relief="groove")
        viewer_panel.pack(fill="both", expand=True)
        self.viewer_mode_label = tk.Label(viewer_panel, text="Sin mapa activo", bg="#1f2937", fg="#93c5fd", font=("Arial", 11, "bold"))
        self.viewer_mode_label.pack(anchor="w", padx=12, pady=(12, 4))
        self.viewer_runtime_label = tk.Label(
            viewer_panel,
            text="El visor se sirve localmente desde TLAMATINI.",
            justify="left",
            bg="#1f2937",
            fg="#d1d5db",
            font=("Arial", 9),
        )
        self.viewer_runtime_label.pack(anchor="w", padx=12, pady=(0, 8))
        self.viewer_url_label = tk.Label(viewer_panel, text="", justify="left", bg="#1f2937", fg="#7dd3fc", font=("Arial", 9))
        self.viewer_url_label.pack(anchor="w", padx=12, pady=(0, 8))

        self.viewer_notice = tk.Label(
            viewer_panel,
            text="Activa un mapa para preparar el visor. Las herramientas operativas están dentro del visor web.",
            justify="left",
            bg="#0b1220",
            fg="#cbd5e1",
            font=("Arial", 10),
            padx=12,
            pady=12,
        )
        self.viewer_notice.pack(fill="x", padx=12, pady=(0, 8))

        self.viewer = OfflineMapCanvas(viewer_panel, on_feature_selected=self._show_feature_text)
        self.viewer.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        progress_bar_wrap = tk.Frame(parent, bg="#111827")
        progress_bar_wrap.pack(fill="x", pady=(8, 0))
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(progress_bar_wrap, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x")
        self.progress_label = tk.Label(progress_bar_wrap, text="Sin descargas activas", anchor="w", bg="#111827", fg="#cbd5e1", font=("Arial", 9))
        self.progress_label.pack(fill="x", pady=(4, 0))

    def _select_tree_item_from_event(self, tree, event):
        item_id = tree.identify_row(event.y)
        if not item_id:
            return ""
        tree.selection_set(item_id)
        tree.focus(item_id)
        tree.see(item_id)
        return item_id

    def _show_catalog_menu(self, event):
        item_id = self._select_tree_item_from_event(self.catalog_tree, event)
        menu = tk.Menu(self, tearoff=0)
        if item_id:
            self.selected_catalog_id = item_id
            menu.add_command(label="Descargar mapa", command=self._download_selected)
            menu.add_command(label="Cancelar descarga", command=self._cancel_selected_download)
            menu.add_separator()
        menu.add_command(label="Actualizar catálogo", command=self._refresh_all)
        menu.add_command(label="Importar carpeta XYZ", command=self._import_xyz_folder)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_installed_menu(self, event):
        item_id = self._select_tree_item_from_event(self.installed_tree, event)
        menu = tk.Menu(self, tearoff=0)
        if item_id:
            self.selected_installed_id = item_id
            menu.add_command(label="Activar mapa", command=self._activate_selected)
            menu.add_command(label="Abrir visor", command=self._open_viewer)
            menu.add_command(label="Recargar runtime", command=self._reload_active_map)
            menu.add_command(label="Importar GeoJSON", command=self._import_geojson_layer)
            menu.add_separator()
            menu.add_command(label="Eliminar mapa", command=self._delete_selected)
        else:
            menu.add_command(label="Abrir visor", command=self._open_viewer)
            menu.add_command(label="Recargar runtime", command=self._reload_active_map)
            menu.add_command(label="Importar GeoJSON", command=self._import_geojson_layer)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _build_right(self, parent):
        details_panel = tk.LabelFrame(parent, text="Detalle / Estado", bg="#1f2937", fg="white", bd=1, relief="groove")
        details_panel.pack(fill="both", expand=True, pady=(0, 10))
        self.detail_text = tk.Text(details_panel, wrap="word", bg="#0b1220", fg="white", font=("Arial", 10))
        self.detail_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.detail_text.insert("1.0", "Selecciona un mapa del catálogo o uno instalado.")
        self.detail_text.config(state="disabled")

        feature_panel = tk.LabelFrame(parent, text="Elemento seleccionado", bg="#1f2937", fg="white", bd=1, relief="groove")
        feature_panel.pack(fill="both", expand=True)
        self.feature_text = tk.Text(feature_panel, wrap="word", bg="#0b1220", fg="#e2e8f0", font=("Arial", 10), height=8)
        self.feature_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.feature_text.insert("1.0", "Haz clic en un punto o zona del mapa para ver su detalle.")
        self.feature_text.config(state="disabled")

    def _set_detail_text(self, text: str):
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.config(state="disabled")

    def _show_feature_text(self, text: str):
        self.feature_text.config(state="normal")
        self.feature_text.delete("1.0", "end")
        self.feature_text.insert("1.0", text)
        self.feature_text.config(state="disabled")

    def _refresh_all(self):
        self.service.refresh_catalog(force=True)
        self._refresh_catalog_tree()
        self._refresh_installed_tree()
        self._refresh_active_header()
        self._reload_active_map()
        self._refresh_progress()

    def _refresh_catalog_tree(self):
        current = self.selected_catalog_id
        for item in self.catalog_tree.get_children():
            self.catalog_tree.delete(item)
        self.catalog_index = {}
        for entry in self.service.list_catalog_maps():
            iid = entry["id"]
            label = entry["name"]
            values = (entry.get("region", ""), entry.get("human_size", ""), _catalog_status_label(entry))
            self.catalog_tree.insert("", "end", iid=iid, text=label, values=values)
            self.catalog_index[iid] = entry
        if current and current in self.catalog_index:
            self.catalog_tree.selection_set(current)

    def _refresh_installed_tree(self):
        current = self.selected_installed_id
        for item in self.installed_tree.get_children():
            self.installed_tree.delete(item)
        self.installed_index = {}
        for entry in self.service.list_installed_maps():
            iid = entry["id"]
            label = f"{entry['name']}{' [ACTIVO]' if entry.get('is_active') else ''}"
            values = (entry.get("region", ""), entry.get("human_size", ""), entry.get("version", ""))
            self.installed_tree.insert("", "end", iid=iid, text=label, values=values)
            self.installed_index[iid] = entry
        if current and current in self.installed_index:
            self.installed_tree.selection_set(current)

    def _refresh_active_header(self):
        active = self.service.get_active_map()
        if not active:
            self.active_label.config(text="Sin mapa activo")
            self.active_meta.config(text="Descarga o importa un mapa para comenzar.")
            return
        self.active_label.config(text=active["name"])
        self.active_meta.config(
            text=(
                f"Región: {active.get('region', '')}\n"
                f"Formato: {active.get('format', '')}\n"
                f"Centro: {active.get('center_lat', 0.0):.4f}, {active.get('center_lon', 0.0):.4f}\n"
                f"Zoom: {active.get('min_zoom', 0)}-{active.get('max_zoom', 0)}"
            )
        )

    def _refresh_progress(self):
        active_task = None
        for entry in self.service.list_catalog_maps():
            task = entry.get("download", {})
            if task.get("status") in {"queued", "preparing", "waiting_remote", "downloading", "extracting", "error", "cancelled"}:
                active_task = _safe_task_snapshot(task)
                break
        if not active_task:
            self.progress_var.set(0.0)
            self.progress_label.config(text="Sin descargas activas")
            return
        self.progress_var.set(float(active_task.get("progress", 0.0)))
        status = active_task.get("status", "")
        downloaded = active_task.get("downloaded_bytes", 0)
        total = active_task.get("total_bytes", 0)
        error = active_task.get("error", "")
        text = f"{active_task.get('map_id', '')}: {_task_status_line(status, downloaded, total, active_task.get('progress', 0.0))}"
        if error:
            text += f" | {error}"
        self.progress_label.config(text=text)

    def _poll_state(self):
        self._refresh_catalog_tree()
        self._refresh_installed_tree()
        self._refresh_active_header()
        self._refresh_progress()
        active = self.service.get_active_map()
        active_id = str((active or {}).get("id", "") or "")
        if active_id != self.current_active_id:
            self._reload_active_map()
        self.after(900, self._poll_state)

    def _on_catalog_select(self, _event=None):
        selection = self.catalog_tree.selection()
        if not selection:
            return
        self.selected_catalog_id = selection[0]
        entry = self.catalog_index.get(self.selected_catalog_id)
        if not entry:
            return
        task = entry.get("download", self.service.get_download_status(entry["id"]))
        text = (
            f"Nombre: {entry.get('name', '')}\n"
            f"ID: {entry.get('id', '')}\n"
            f"Región: {entry.get('region', '')}\n"
            f"Formato: {entry.get('format', '')}\n"
            f"Tamaño: {entry.get('human_size', '')}\n"
            f"Versión: {entry.get('version', '')}\n"
            f"Estado: {_catalog_status_label(entry)}\n"
            f"Descripción: {entry.get('description', '')}\n"
            f"Aviso: {entry.get('download_warning', '')}\n"
            f"Centro sugerido: {entry.get('center_lat', 0.0)}, {entry.get('center_lon', 0.0)}\n"
            f"Zoom sugerido: {entry.get('min_zoom', 0)}-{entry.get('max_zoom', 0)}\n"
        )
        if task.get("status") not in {"idle", ""}:
            text += (
                f"\nDescarga:\n"
                f"- Estado: {_task_status_label(task.get('status', ''))}\n"
                f"- Progreso: {task.get('progress', 0.0)}%\n"
                f"- Transferido: {_format_bytes(task.get('downloaded_bytes', 0))} / {_format_bytes(task.get('total_bytes', 0))}\n"
                f"- Error: {task.get('error', '')}\n"
            )
        self._set_detail_text(text)

    def _on_installed_select(self, _event=None):
        selection = self.installed_tree.selection()
        if not selection:
            return
        self.selected_installed_id = selection[0]
        entry = self.installed_index.get(self.selected_installed_id)
        if not entry:
            return
        resumen = resumen_capas(entry["id"])
        capas_texto = "\n".join(f"- {LAYER_DEFS.get(layer_id, {}).get('label', layer_id)}: {count}" for layer_id, count in resumen.items())
        text = (
            f"Nombre: {entry.get('name', '')}\n"
            f"ID: {entry.get('id', '')}\n"
            f"Región: {entry.get('region', '')}\n"
            f"Formato: {entry.get('format', '')}\n"
            f"Versión: {entry.get('version', '')}\n"
            f"Estado: instalado{' / activo' if entry.get('is_active') else ''}\n"
            f"Ruta instalada: {entry.get('installed_path', '')}\n"
            f"Ruta tiles: {entry.get('tiles_path', '')}\n"
            f"Ruta PMTiles: {entry.get('pmtiles_path', '')}\n"
            f"Tamaño: {entry.get('human_size', '')}\n"
            f"Centro: {entry.get('center_lat', 0.0)}, {entry.get('center_lon', 0.0)}\n"
            f"Zoom: {entry.get('min_zoom', 0)}-{entry.get('max_zoom', 0)} (inicial {entry.get('default_zoom', 0)})\n"
            f"Descripción: {entry.get('description', '')}\n\n"
            f"Capas/overlays:\n{capas_texto}"
        )
        self._set_detail_text(text)
        if entry.get("format") != "pmtiles":
            self.viewer.load_map(entry)

    def _download_selected(self):
        if not self.selected_catalog_id:
            messagebox.showwarning("Sin selección", "Selecciona un mapa del catálogo.")
            return
        try:
            self.service.start_download(self.selected_catalog_id)
            self._refresh_progress()
            self._on_catalog_select()
        except Exception as exc:
            messagebox.showerror("Descarga", str(exc))

    def _cancel_selected_download(self):
        target_id = self.selected_catalog_id or self.selected_installed_id
        if not target_id:
            messagebox.showwarning("Sin selección", "Selecciona un mapa del catálogo.")
            return
        if not self.service.cancel_download(target_id):
            messagebox.showinfo("Descarga", "No hay una descarga activa para ese mapa.")
        self._refresh_progress()

    def _activate_selected(self):
        if not self.selected_installed_id:
            messagebox.showwarning("Sin selección", "Selecciona un mapa instalado.")
            return
        if self.service.set_active_map(self.selected_installed_id):
            self._refresh_all()
            messagebox.showinfo("Mapa activo", "Mapa activado correctamente.")

    def _delete_selected(self):
        if not self.selected_installed_id:
            messagebox.showwarning("Sin selección", "Selecciona un mapa instalado.")
            return
        target = self.installed_index.get(self.selected_installed_id)
        if not target:
            return
        if not messagebox.askyesno("Eliminar", f"¿Eliminar el mapa '{target['name']}' del almacenamiento local?"):
            return
        if self.service.delete_map(target["id"]):
            self.selected_installed_id = ""
            self._refresh_all()

    def _import_xyz_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta raíz de tiles XYZ")
        if not folder:
            return
        name = simpledialog.askstring("Nombre del mapa", "Nombre del mapa:", parent=self)
        if not name:
            return
        description = simpledialog.askstring("Descripción", "Descripción:", parent=self) or ""
        lat = simpledialog.askfloat("Latitud centro", "Latitud centro inicial:", parent=self, initialvalue=19.4326)
        lon = simpledialog.askfloat("Longitud centro", "Longitud centro inicial:", parent=self, initialvalue=-99.1332)
        if lat is None or lon is None:
            return
        try:
            registrar_mapa_tiles(nombre=name, ruta_tiles=folder, descripcion=description, lat_centro=lat, lon_centro=lon)
            self._refresh_all()
            messagebox.showinfo("Mapa importado", "Mapa XYZ importado correctamente.")
        except Exception as exc:
            messagebox.showerror("Importación", str(exc))

    def _reload_active_map(self):
        active = self.service.get_active_map()
        self.current_active_id = str((active or {}).get("id", "") or "")
        self.viewer_url = update_map_runtime(active)
        self.viewer_url_label.config(text=f"Visor local: {self.viewer_url}")
        if not active:
            self.viewer_mode_label.config(text="Sin mapa activo")
            self.viewer_runtime_label.config(text="Activa un mapa para preparar el visor local.")
            self.viewer_notice.config(text="No hay un mapa activo. El visor PMTiles quedará disponible cuando actives uno.")
            self.viewer.load_map(None)
            return

        fmt = str(active.get("format", ""))
        viewer_mode = str(active.get("viewer_mode") or fmt)
        self.viewer_mode_label.config(text=f"{active.get('name', 'Mapa')} | modo {viewer_mode}")
        self.viewer_runtime_label.config(
            text=(
                f"Formato: {fmt}\n"
                f"Región: {active.get('region', '')}\n"
                f"Centro: {active.get('center_lat', 0.0):.4f}, {active.get('center_lon', 0.0):.4f}\n"
                f"Zoom: {active.get('min_zoom', 0)}-{active.get('max_zoom', 0)}"
            )
        )

        if fmt == "pmtiles":
            self.viewer_notice.config(
                text=(
                    "Mapa PMTiles activo. El visor corre en un servidor local del proyecto "
                    "y se actualiza con el mapa activo y las capas tácticas."
                )
            )
            self.viewer.load_map(None)
            return

        self.viewer_notice.config(
            text="Mapa legacy XYZ activo. Se mantiene el visor integrado para compatibilidad mientras PMTiles pasa a ser el formato principal."
        )
        self.viewer.load_map(active)

    def _layer_choice(self, title: str, allowed=None, prompt: str = "Elige la capa destino:"):
        layer_ids = allowed or list(LAYER_DEFS.keys())
        labels = [f"{layer_id} - {LAYER_DEFS[layer_id]['label']}" for layer_id in layer_ids]
        answer = simpledialog.askstring(title, f"{prompt}\n" + "\n".join(labels), parent=self, initialvalue=layer_ids[0])
        if not answer:
            return ""
        value = answer.split("-", 1)[0].strip().lower()
        return value if value in layer_ids else ""

    def _open_viewer(self):
        try:
            self.viewer_url = update_map_runtime(self.service.get_active_map())
            open_map_viewer()
            self.viewer_url_label.config(text=f"Visor local: {self.viewer_url}")
            active = self.service.get_active_map()
            self.viewer_opened_for = str((active or {}).get("id", "") or "")
        except Exception as exc:
            messagebox.showerror("Visor", str(exc))

    def agregar_punto_ui(self):
        mapa = obtener_mapa(self.selected_installed_id) or obtener_mapa_activo()
        if not mapa:
            messagebox.showwarning("Sin mapa", "Primero activa un mapa.")
            return
        nombre = simpledialog.askstring("Nombre", "Nombre del punto:", parent=self)
        if not nombre:
            return
        categoria = simpledialog.askstring("Categoría", "Categoría del punto:", parent=self) or "punto_interes"
        riesgo = simpledialog.askstring("Riesgo", "Nivel de riesgo (bajo/medio/alto/critico):", parent=self) or "medio"
        lat = simpledialog.askfloat("Latitud", "Latitud del punto:", parent=self, initialvalue=float(mapa.get("center_lat", 19.4326)))
        lon = simpledialog.askfloat("Longitud", "Longitud del punto:", parent=self, initialvalue=float(mapa.get("center_lon", -99.1332)))
        descripcion = simpledialog.askstring("Descripción", "Descripción del punto:", parent=self) or ""
        layer_id = self._layer_choice("Capa", allowed=["puntos", "refugios", "recursos", "nodos", "sensores"], prompt="Escribe el id de la capa para este marcador:")
        if not layer_id:
            return
        if lat is None or lon is None:
            return
        try:
            agregar_punto_tactico(
                mapa_id=mapa["id"],
                nombre=nombre,
                categoria=categoria,
                descripcion=descripcion,
                riesgo=riesgo,
                lat=lat,
                lon=lon,
                layer_id=layer_id,
            )
            self.viewer.refresh_overlays()
            self._reload_active_map()
            self._on_installed_select()
        except Exception as exc:
            messagebox.showerror("Punto", str(exc))

    def agregar_ruta_ui(self):
        mapa = obtener_mapa(self.selected_installed_id) or obtener_mapa_activo()
        if not mapa:
            messagebox.showwarning("Sin mapa", "Primero activa un mapa.")
            return
        nombre = simpledialog.askstring("Nombre", "Nombre de la ruta:", parent=self)
        if not nombre:
            return
        categoria = simpledialog.askstring("Categoría", "Categoría de la ruta:", parent=self) or "ruta"
        descripcion = simpledialog.askstring("Descripción", "Descripción de la ruta:", parent=self) or ""

        ventana = tk.Toplevel(self)
        ventana.title("Coordenadas de la ruta")
        ventana.geometry("520x420")
        ventana.configure(bg="#111827")
        tk.Label(ventana, text="Escribe una coordenada por línea con formato: lat,lon", bg="#111827", fg="white").pack(anchor="w", padx=12, pady=(12, 8))
        area = tk.Text(ventana, wrap="word", font=("Arial", 10), bg="white", fg="black")
        area.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def guardar():
            texto = area.get("1.0", "end").strip()
            lineas = [line.strip() for line in texto.splitlines() if line.strip()]
            coords = []
            try:
                for linea in lineas:
                    lat_txt, lon_txt = [piece.strip() for piece in linea.split(",")]
                    coords.append([float(lon_txt), float(lat_txt)])
                agregar_ruta_tactica(
                    mapa_id=mapa["id"],
                    nombre=nombre,
                    descripcion=descripcion,
                    categoria=categoria,
                    coordenadas_lon_lat=coords,
                )
                self.viewer.refresh_overlays()
                self._reload_active_map()
                self._on_installed_select()
                ventana.destroy()
            except Exception as exc:
                messagebox.showerror("Ruta", str(exc))

        tk.Button(ventana, text="Guardar ruta", command=guardar, bg="#16a34a", fg="white", relief="flat").pack(fill="x", padx=12, pady=(0, 12))

    def agregar_poligono_ui(self):
        mapa = obtener_mapa(self.selected_installed_id) or obtener_mapa_activo()
        if not mapa:
            messagebox.showwarning("Sin mapa", "Primero activa un mapa.")
            return
        nombre = simpledialog.askstring("Nombre", "Nombre de la zona:", parent=self)
        if not nombre:
            return
        riesgo = simpledialog.askstring("Riesgo", "Nivel de riesgo (bajo/medio/alto/critico):", parent=self) or "alto"
        descripcion = simpledialog.askstring("Descripción", "Descripción de la zona:", parent=self) or ""

        ventana = tk.Toplevel(self)
        ventana.title("Coordenadas de la zona")
        ventana.geometry("520x420")
        ventana.configure(bg="#111827")
        tk.Label(ventana, text="Escribe una coordenada por línea con formato: lat,lon", bg="#111827", fg="white").pack(anchor="w", padx=12, pady=(12, 8))
        area = tk.Text(ventana, wrap="word", font=("Arial", 10), bg="white", fg="black")
        area.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def guardar():
            texto = area.get("1.0", "end").strip()
            lineas = [line.strip() for line in texto.splitlines() if line.strip()]
            coords = []
            try:
                for linea in lineas:
                    lat_txt, lon_txt = [piece.strip() for piece in linea.split(",")]
                    coords.append([float(lon_txt), float(lat_txt)])
                agregar_poligono_tactico(
                    mapa_id=mapa["id"],
                    nombre=nombre,
                    descripcion=descripcion,
                    riesgo=riesgo,
                    coordenadas_lon_lat=coords,
                )
                self.viewer.refresh_overlays()
                self._reload_active_map()
                self._on_installed_select()
                ventana.destroy()
            except Exception as exc:
                messagebox.showerror("Zona", str(exc))

        tk.Button(ventana, text="Guardar zona", command=guardar, bg="#7c3aed", fg="white", relief="flat").pack(fill="x", padx=12, pady=(0, 12))

    def _import_geojson_layer(self):
        mapa = obtener_mapa(self.selected_installed_id) or obtener_mapa_activo()
        if not mapa:
            messagebox.showwarning("Sin mapa", "Primero activa un mapa.")
            return
        ruta = filedialog.askopenfilename(
            title="Seleccionar GeoJSON",
            filetypes=[("GeoJSON", "*.geojson *.json"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        layer_id = self._layer_choice("Importar GeoJSON", allowed=["imported", "rutas", "poligonos", "puntos", "refugios", "recursos", "nodos", "sensores"], prompt="Escribe la capa destino para el GeoJSON:")
        if not layer_id:
            return
        try:
            resultado = importar_geojson_capa(mapa["id"], ruta, layer_id=layer_id, fusionar=True)
            self.viewer.refresh_overlays()
            self._reload_active_map()
            self._on_installed_select()
            messagebox.showinfo("GeoJSON importado", f"Se importaron {resultado['features']} elementos a la capa {layer_id}.")
        except Exception as exc:
            messagebox.showerror("GeoJSON", str(exc))


def _safe_task_snapshot(task: Dict) -> Dict:
    return {
        "map_id": task.get("map_id", ""),
        "status": task.get("status", ""),
        "progress": float(task.get("progress", 0.0) or 0.0),
        "downloaded_bytes": int(task.get("downloaded_bytes", 0) or 0),
        "total_bytes": int(task.get("total_bytes", 0) or 0),
        "error": task.get("error", ""),
    }


def _format_bytes(value: int) -> str:
    size = float(max(0, int(value or 0)))
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024.0
    return f"{int(value or 0)} B"


def _task_status_label(status: str) -> str:
    labels = {
        "idle": "Sin actividad",
        "queued": "En cola",
        "preparing": "Preparando solicitud",
        "waiting_remote": "Generando mapa remoto",
        "downloading": "Descargando archivo",
        "extracting": "Instalando mapa",
        "installed": "Instalado",
        "error": "Error",
        "cancelled": "Cancelado",
    }
    return labels.get(str(status or "").strip(), str(status or "").strip() or "--")


def _task_status_line(status: str, downloaded: int, total: int, progress: float) -> str:
    label = _task_status_label(status)
    if status == "waiting_remote":
        return f"{label} | avance estimado {round(float(progress or 0.0), 1)}%"
    if status == "downloading":
        return f"{label} | {_format_bytes(downloaded)} / {_format_bytes(total)}"
    if status == "extracting":
        return f"{label} | archivo descargado, procesando instalacion"
    return label


def _catalog_status_label(entry: Dict) -> str:
    status = str(entry.get("status", "")).strip()
    if status == "installed":
        return "Instalado"
    return _task_status_label(status or "idle") if status else "--"
