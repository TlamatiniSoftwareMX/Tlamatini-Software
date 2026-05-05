import tkinter as tk
from tkinter import colorchooser, messagebox

from core.dashboard_config import cargar_config, guardar_config, siguiente_posicion_modulo
from core.ui_theme import FUTURISTA_OSCURO
from core.window_geometry import aplicar_geometria_relativa, habilitar_scroll_mouse


MODULOS_BASE = {"consulta", "mapa", "inventario", "biblioteca", "aprendizaje", "perfiles", "herramientas"}

EMOJIS_SUGERIDOS = [
    "🧠", "🗺", "📦", "👤", "🛠", "🔋", "📡", "📋", "🩺",
    "💧", "🌽", "🔦", "🧰", "⚙", "📚", "📝", "📞", "🛰", "🚨",
    "🏥", "🌿", "🔥", "🔌", "🧪", "🛡", "🧭", "📍", "🔍", "🗂"
]


class VentanaConfiguracion(tk.Toplevel):
    def __init__(self, root, on_change=None):
        super().__init__(root)
        self.root_dashboard = root
        self.on_change = on_change
        self.ui = FUTURISTA_OSCURO

        self.title("Configuración TLAMATINI")
        self.minsize(900, 640)
        self.configure(bg=self.ui["fondo"])
        aplicar_geometria_relativa(self, root, rel_w=0.76, rel_h=0.84, min_w=980, min_h=760)

        self.cfg = cargar_config()
        self.modulo_seleccionado_id = None
        self.modo_nuevo = False

        self._asegurar_base_visual()
        self.crear_ui()
        self.refrescar_lista_modulos()
        self.seleccionar_primer_modulo()

    def _asegurar_base_visual(self):
        defaults = {
            "consulta": {"titulo": "Consulta", "icono": "🧠", "color": "#1E293B"},
            "mapa": {"titulo": "Mapa", "icono": "🗺", "color": "#1E293B"},
            "inventario": {"titulo": "Inventario", "icono": "📦", "color": "#1E293B"},
            "biblioteca": {"titulo": "Biblioteca", "icono": "📚", "color": "#1E293B"},
            "aprendizaje": {"titulo": "Aprendizaje", "icono": "🎓", "color": "#1E293B"},
            "perfiles": {"titulo": "Perfiles", "icono": "👤", "color": "#1E293B"},
            "herramientas": {"titulo": "Herramientas", "icono": "🛠", "color": "#1E293B"},
        }

        self.cfg.setdefault("custom_modulos", {})
        self.cfg.setdefault("modulos", [])
        self.cfg.setdefault("tema", {})
        self.cfg["custom_modulos"].pop("camara", None)
        self.cfg["modulos"] = [mod for mod in self.cfg["modulos"] if mod.get("id") != "camara"]

        for mid, datos in defaults.items():
            self.cfg["custom_modulos"].setdefault(mid, {})
            for k, v in datos.items():
                self.cfg["custom_modulos"][mid].setdefault(k, v)

    def crear_ui(self):
        tk.Label(
            self,
            text="Configuración del dashboard",
            font=("Arial", 18, "bold"),
            bg=self.ui["fondo"],
            fg=self.ui["texto"]
        ).pack(anchor="w", padx=15, pady=(12, 8))

        # ===== CONTENEDOR PRINCIPAL =====
        principal = tk.Frame(self, bg=self.ui["fondo"])
        principal.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        panel_izq = tk.Frame(principal, bg=self.ui["panel"], width=340, highlightthickness=1, highlightbackground=self.ui["borde"])
        panel_izq.pack(side="left", fill="y", padx=(0, 12))
        panel_izq.pack_propagate(False)

        # ===== PANEL DERECHO CON SCROLL =====
        panel_der_externo = tk.Frame(principal, bg=self.ui["fondo"])
        panel_der_externo.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(
            panel_der_externo,
            bg=self.ui["fondo"],
            highlightthickness=0
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(panel_der_externo, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.panel_der = tk.Frame(self.canvas, bg=self.ui["fondo"])
        self.canvas_window = self.canvas.create_window((0, 0), window=self.panel_der, anchor="nw")

        self.panel_der.bind("<Configure>", self._actualizar_scroll)
        self.canvas.bind("<Configure>", self._ajustar_ancho_canvas)
        habilitar_scroll_mouse(panel_der_externo, self.canvas)

        # ===== BARRA FIJA INFERIOR =====
        barra_inferior = tk.Frame(self, bg=self.ui["fondo"])
        barra_inferior.pack(fill="x", padx=15, pady=(0, 12))

        self.btn_guardar_modulo = tk.Button(
            barra_inferior,
            text="Guardar módulo",
            font=("Arial", 11, "bold"),
            bg=self.ui["panel"],
            fg=self.ui["texto"],
            activebackground=self.ui["panel_2"],
            activeforeground=self.ui["texto"],
            command=self.guardar_modulo_editado
        )
        self.btn_guardar_modulo.pack(side="left", padx=(0, 10))

        tk.Button(
            barra_inferior,
            text="Guardar todo",
            font=("Arial", 11, "bold"),
            bg=self.ui["panel"],
            fg=self.ui["texto"],
            activebackground=self.ui["panel_2"],
            activeforeground=self.ui["texto"],
            command=self.guardar_todo
        ).pack(side="left")

        # ===== IZQUIERDA =====
        tk.Label(
            panel_izq,
            text="Módulos del dashboard",
            font=("Arial", 14, "bold"),
            bg=self.ui["panel"],
            fg=self.ui["texto"]
        ).pack(anchor="w", padx=12, pady=(12, 6))

        tk.Label(
            panel_izq,
            text="Selecciona uno para editarlo o crea uno nuevo.",
            font=("Arial", 10),
            bg=self.ui["panel"],
            fg=self.ui["texto_dim"],
            wraplength=300,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        self.lista_modulos = tk.Listbox(
            panel_izq,
            bg=self.ui["panel_3"],
            fg=self.ui["texto"],
            selectbackground=self.ui["acento"],
            selectforeground="white",
            font=("Arial", 11),
            height=16
        )
        self.lista_modulos.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.lista_modulos.bind("<<ListboxSelect>>", self.al_seleccionar_modulo)

        barra_modulos = tk.Frame(panel_izq, bg=self.ui["panel"])
        barra_modulos.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(
            barra_modulos,
            text="Nuevo módulo",
            bg=self.ui["panel_2"],
            fg=self.ui["texto"],
            activebackground=self.ui["borde"],
            activeforeground="white",
            command=self.nuevo_modulo
        ).pack(side="left", padx=(0, 6))

        self.btn_eliminar = tk.Button(
            barra_modulos,
            text="Eliminar",
            bg=self.ui["panel_2"],
            fg="white",
            activebackground=self.ui["borde"],
            activeforeground="white",
            command=self.eliminar_modulo
        )
        self.btn_eliminar.pack(side="left")

        # ===== DERECHA =====
        tk.Label(
            self.panel_der,
            text="Tema general",
            font=("Arial", 14, "bold"),
            bg=self.ui["fondo"],
            fg=self.ui["texto"]
        ).pack(anchor="w", pady=(0, 8))

        self.crear_selector_color(self.panel_der, "Fondo", "fondo")
        self.crear_selector_color(self.panel_der, "Color general módulos", "modulo")
        self.crear_selector_color(self.panel_der, "Texto general", "texto")
        self.crear_selector_color(self.panel_der, "Panel de guerra", "panel_guerra")
        self.crear_selector_color(self.panel_der, "Panel de hora", "panel_hora")

        separador = tk.Frame(self.panel_der, bg=self.ui["borde"], height=2)
        separador.pack(fill="x", pady=12)

        tk.Label(
            self.panel_der,
            text="Crear / editar módulo",
            font=("Arial", 14, "bold"),
            bg="#111827",
            fg="white"
        ).pack(anchor="w", pady=(0, 8))

        self.label_modulo_actual = tk.Label(
            self.panel_der,
            text="Ningún módulo seleccionado",
            font=("Arial", 11, "bold"),
            bg="#111827",
            fg="#FBBF24"
        )
        self.label_modulo_actual.pack(anchor="w", pady=(0, 8))

        tk.Label(self.panel_der, text="Nombre visible", bg="#111827", fg="white").pack(anchor="w")
        self.entry_nombre = tk.Entry(self.panel_der, font=("Arial", 12), width=40)
        self.entry_nombre.pack(anchor="w", pady=(3, 8))

        tk.Label(self.panel_der, text="Emoji / icono", bg="#111827", fg="white").pack(anchor="w")
        self.entry_icono = tk.Entry(self.panel_der, font=("Arial", 12), width=12)
        self.entry_icono.pack(anchor="w", pady=(3, 6))

        tk.Label(
            self.panel_der,
            text="Sugerencias rápidas de emoji",
            bg="#111827",
            fg="#D1D5DB"
        ).pack(anchor="w", pady=(2, 4))

        frame_emojis = tk.Frame(self.panel_der, bg="#111827")
        frame_emojis.pack(fill="x", pady=(0, 8))

        for i, emoji in enumerate(EMOJIS_SUGERIDOS):
            tk.Button(
                frame_emojis,
                text=emoji,
                width=3,
                bg="#1F2937",
                fg="white",
                command=lambda e=emoji: self.poner_emoji(e)
            ).grid(row=i // 10, column=i % 10, padx=2, pady=2)

        tk.Label(self.panel_der, text="Color del módulo", bg="#111827", fg="white").pack(anchor="w")
        barra_color_modulo = tk.Frame(self.panel_der, bg="#111827")
        barra_color_modulo.pack(fill="x", pady=(3, 8))

        self.label_color_modulo = tk.Label(
            barra_color_modulo,
            text="Sin color",
            bg="#111827",
            fg="#D1D5DB",
            font=("Arial", 11, "bold")
        )
        self.label_color_modulo.pack(side="left")

        tk.Button(
            barra_color_modulo,
            text="Elegir color",
            bg="#2563EB",
            fg="white",
            activebackground="#1D4ED8",
            activeforeground="white",
            command=self.cambiar_color_modulo
        ).pack(side="left", padx=10)

        tk.Label(self.panel_der, text="Vista previa", bg="#111827", fg="white").pack(anchor="w", pady=(6, 3))
        self.preview_modulo = tk.Label(
            self.panel_der,
            text="🧩\nNuevo módulo",
            font=("Arial", 15, "bold"),
            width=18,
            height=3,
            bg="#334155",
            fg="white",
            relief="raised",
            bd=2
        )
        self.preview_modulo.pack(anchor="w", pady=(0, 12))

        # espacio final para que no quede pegado al borde
        tk.Frame(self.panel_der, bg="#111827", height=30).pack(fill="x")

        self.entry_nombre.bind("<KeyRelease>", lambda e: self.actualizar_preview())
        self.entry_icono.bind("<KeyRelease>", lambda e: self.actualizar_preview())

    def _actualizar_scroll(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _ajustar_ancho_canvas(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        if not self.canvas.winfo_exists():
            return
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(1, "units")

    def crear_selector_color(self, parent, nombre, clave):
        frame = tk.Frame(parent, bg="#111827")
        frame.pack(fill="x", pady=3)

        tk.Label(
            frame,
            text=nombre,
            width=22,
            anchor="w",
            bg="#111827",
            fg="white"
        ).pack(side="left")

        tk.Button(
            frame,
            text="Cambiar color",
            bg="#374151",
            fg="white",
            activebackground="#4B5563",
            activeforeground="white",
            command=lambda: self.cambiar_color_tema(clave)
        ).pack(side="right")

    def cambiar_color_tema(self, clave):
        color = colorchooser.askcolor()[1]
        if color:
            self.cfg["tema"][clave] = color

    def refrescar_lista_modulos(self):
        self.lista_modulos.delete(0, "end")
        for mod in self.cfg.get("modulos", []):
            mod_id = mod["id"]
            custom = self.cfg["custom_modulos"].get(mod_id, {})
            titulo = custom.get("titulo", mod_id)
            icono = custom.get("icono", "📁")
            self.lista_modulos.insert("end", f"{icono} {titulo}")

    def seleccionar_primer_modulo(self):
        if self.lista_modulos.size() > 0:
            self.lista_modulos.selection_clear(0, "end")
            self.lista_modulos.selection_set(0)
            self.lista_modulos.activate(0)
            self.al_seleccionar_modulo()

    def al_seleccionar_modulo(self, event=None):
        seleccion = self.lista_modulos.curselection()
        if not seleccion:
            return

        idx = seleccion[0]
        mod = self.cfg["modulos"][idx]
        mod_id = mod["id"]
        custom = self.cfg["custom_modulos"].get(mod_id, {})

        self.modo_nuevo = False
        self.modulo_seleccionado_id = mod_id
        self.label_modulo_actual.config(text=f"Editando: {custom.get('titulo', mod_id)} [{mod_id}]")

        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, custom.get("titulo", mod_id))

        self.entry_icono.delete(0, "end")
        self.entry_icono.insert(0, custom.get("icono", "📁"))

        color = custom.get("color", self.cfg["tema"].get("modulo", "#1E293B"))
        self.label_color_modulo.config(text=color, fg=color)

        self.btn_eliminar.config(state="disabled" if mod_id in MODULOS_BASE else "normal")
        self.btn_guardar_modulo.config(text="Guardar módulo")
        self.actualizar_preview()

    def poner_emoji(self, emoji):
        self.entry_icono.delete(0, "end")
        self.entry_icono.insert(0, emoji)
        self.actualizar_preview()

    def actualizar_preview(self):
        nombre = self.entry_nombre.get().strip() or "Nuevo módulo"
        icono = self.entry_icono.get().strip() or "🧩"
        color = "#334155"

        if self.modulo_seleccionado_id:
            color = self.cfg["custom_modulos"].get(
                self.modulo_seleccionado_id, {}
            ).get("color", "#334155")

        self.preview_modulo.config(
            text=f"{icono}\n{nombre}",
            bg=color
        )

    def cambiar_color_modulo(self):
        if not self.modulo_seleccionado_id:
            messagebox.showwarning("Selecciona módulo", "Primero crea o selecciona un módulo.")
            return

        color = colorchooser.askcolor()[1]
        if color:
            custom = self.cfg["custom_modulos"].setdefault(self.modulo_seleccionado_id, {})
            custom["color"] = color
            self.label_color_modulo.config(text=color, fg=color)
            self.actualizar_preview()

    def nuevo_modulo(self):
        total = len(self.cfg.get("modulos", [])) + 1
        nuevo_id = f"custom_{total}"

        while nuevo_id in self.cfg["custom_modulos"]:
            total += 1
            nuevo_id = f"custom_{total}"

        pos = siguiente_posicion_modulo(self.cfg)

        self.cfg["modulos"].append({
            "id": nuevo_id,
            "fila": pos["fila"],
            "col": pos["col"],
            "orden": pos["orden"],
        })

        self.cfg["custom_modulos"][nuevo_id] = {
            "titulo": f"Módulo {total}",
            "icono": "🧩",
            "color": "#334155"
        }

        self.modulo_seleccionado_id = nuevo_id
        self.modo_nuevo = True

        self.refrescar_lista_modulos()

        ultimo = self.lista_modulos.size() - 1
        if ultimo >= 0:
            self.lista_modulos.selection_clear(0, "end")
            self.lista_modulos.selection_set(ultimo)
            self.lista_modulos.activate(ultimo)

        self.label_modulo_actual.config(text=f"Creando: {nuevo_id}")
        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, f"Módulo {total}")
        self.entry_icono.delete(0, "end")
        self.entry_icono.insert(0, "🧩")
        self.label_color_modulo.config(text="#334155", fg="#334155")
        self.preview_modulo.config(text="🧩\nMódulo nuevo", bg="#334155")
        self.btn_guardar_modulo.config(text="Guardar módulo nuevo")

        self.entry_nombre.focus_set()
        self.entry_nombre.selection_range(0, "end")

    def guardar_modulo_editado(self):
        if not self.modulo_seleccionado_id:
            messagebox.showwarning("Selecciona módulo", "Primero crea o selecciona un módulo.")
            return

        nombre = self.entry_nombre.get().strip() or self.modulo_seleccionado_id
        icono = self.entry_icono.get().strip() or "📁"

        custom = self.cfg["custom_modulos"].setdefault(self.modulo_seleccionado_id, {})
        custom["titulo"] = nombre
        custom["icono"] = icono
        custom.setdefault("color", self.cfg["tema"].get("modulo", "#1E293B"))

        guardar_config(self.cfg)

        seleccion_actual = self.lista_modulos.curselection()
        self.refrescar_lista_modulos()

        if seleccion_actual:
            idx = seleccion_actual[0]
            if idx < self.lista_modulos.size():
                self.lista_modulos.selection_set(idx)
                self.lista_modulos.activate(idx)
                self.al_seleccionar_modulo()

        texto = "Módulo nuevo guardado correctamente." if self.modo_nuevo else "Módulo guardado correctamente."
        self.modo_nuevo = False
        self.btn_guardar_modulo.config(text="Guardar módulo")
        if self.on_change:
            self.on_change()
        messagebox.showinfo("Módulo", texto)

    def eliminar_modulo(self):
        if not self.lista_modulos.curselection():
            messagebox.showwarning("Selecciona módulo", "Selecciona un módulo para eliminar.")
            return

        idx = self.lista_modulos.curselection()[0]
        mod = self.cfg["modulos"][idx]
        mod_id = mod["id"]

        if mod_id in MODULOS_BASE:
            messagebox.showwarning("Protegido", "Ese módulo base no se puede eliminar.")
            return

        confirmar = messagebox.askyesno(
            "Eliminar módulo",
            f"¿Seguro que quieres eliminar el módulo '{self.cfg['custom_modulos'].get(mod_id, {}).get('titulo', mod_id)}'?"
        )
        if not confirmar:
            return

        self.cfg["modulos"] = [m for m in self.cfg["modulos"] if m["id"] != mod_id]
        self.cfg["custom_modulos"].pop(mod_id, None)

        guardar_config(self.cfg)

        self.modulo_seleccionado_id = None
        self.modo_nuevo = False
        self.label_modulo_actual.config(text="Ningún módulo seleccionado")
        self.entry_nombre.delete(0, "end")
        self.entry_icono.delete(0, "end")
        self.label_color_modulo.config(text="Sin color", fg="#D1D5DB")
        self.preview_modulo.config(text="🧩\nNuevo módulo", bg="#334155")
        self.btn_guardar_modulo.config(text="Guardar módulo")

        self.refrescar_lista_modulos()
        self.seleccionar_primer_modulo()

        if self.on_change:
            self.on_change()
        messagebox.showinfo("Módulo eliminado", f"Se eliminó {mod_id} correctamente.")

    def guardar_todo(self):
        guardar_config(self.cfg)
        if self.on_change:
            self.on_change()
        messagebox.showinfo(
            "Configuración guardada",
            "Los cambios se guardaron correctamente y ya quedaron aplicados."
        )
