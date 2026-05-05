import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from datetime import datetime

from core.inventario import (
    Inventario,
    actualizar_item,
    agregar_item,
    buscar_item_por_codigo_barras,
    buscar_producto_por_nombre,
    consumir_item,
    editar_categoria,
    eliminar_item_por_id,
    incrementar_cantidad_item,
    listar_alertas_inventario,
    listar_categorias_data,
    listar_items,
    listar_subcategorias,
    total_disponible_item,
    listar_unidades,
    marcar_item_consumido,
    reordenar_categorias,
)
from core.inventario_foto import (
    analizar_texto_nutrimental,
    capturar_codigo_barras_inventario,
    capturar_foto_inventario,
    capturar_y_analizar_inventario,
    extraer_texto_ocr,
)
from core.logs import registrar_log
from core.ui_catalogos import EMOJIS_CATEGORIAS
from core.ui_theme import FUTURISTA_OSCURO
from core.window_geometry import aplicar_geometria_relativa, crear_contenedor_scrollable
from core.window_geometry import habilitar_scroll_mouse
from core.texto import normalizar_texto


PERFILES_CATEGORIA = {
    "alimentos": {
        "titulo": "Alimentos",
        "descripcion": "Registra comida, agua y suplementos con cantidades, caducidad y tabla nutrimental.",
        "nombre_label": "Alimento",
        "tipo_label": "Tipo de alimento",
        "uso_label": "Uso / destino",
        "peso_label": "Contenido por unidad",
        "caducidad_label": "Caducidad (YYYY-MM-DD)",
        "lote_label": "Lote",
        "mostrar_nutrimental": True,
        "mostrar_foto": True,
        "mostrar_caducidad": True,
        "mostrar_lote": True,
    },
    "combate": {
        "titulo": "Combate",
        "descripcion": "Controla equipo táctico, protección, comunicación y consumibles de misión.",
        "nombre_label": "Recurso de combate",
        "tipo_label": "Tipo de recurso",
        "uso_label": "Uso / asignación",
        "peso_label": "Modelo / detalle",
        "caducidad_label": "Revisión / vigencia (YYYY-MM-DD)",
        "lote_label": "Serie / lote",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": True,
        "mostrar_lote": True,
    },
    "herramientas": {
        "titulo": "Herramientas",
        "descripcion": "Controla herramientas por tipo, piezas, juegos o kits, con mínimos y notas operativas.",
        "nombre_label": "Herramienta",
        "tipo_label": "Tipo de herramienta",
        "uso_label": "Uso principal",
        "peso_label": "Peso / medida",
        "caducidad_label": "Próxima revisión (YYYY-MM-DD)",
        "lote_label": "Serie / lote",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": True,
        "mostrar_lote": True,
    },
    "insumos medicos": {
        "titulo": "Insumos médicos",
        "descripcion": "Registra medicamentos, curación y consumibles con dosis, lote, caducidad e indicaciones.",
        "nombre_label": "Medicamento / insumo",
        "tipo_label": "Tipo de insumo",
        "uso_label": "Indicación / para qué sirve",
        "peso_label": "Presentación / concentración",
        "caducidad_label": "Caducidad (YYYY-MM-DD)",
        "lote_label": "Lote / serie",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": True,
        "mostrar_lote": True,
    },
    "animales": {
        "titulo": "Animales",
        "descripcion": "Registra animales por tipo, consumo diario y uso productivo o de trabajo.",
        "nombre_label": "Identificación / raza",
        "tipo_label": "Tipo de animal",
        "uso_label": "Uso",
        "peso_label": "Alimento por día",
        "caducidad_label": "Agua por día",
        "lote_label": "Etapa / lote",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": False,
        "mostrar_lote": True,
    },
    "plantas": {
        "titulo": "Plantas",
        "descripcion": "Registra plantas por tipo, variedad, exposición y tiempos de siembra y cosecha.",
        "nombre_label": "Variedad",
        "tipo_label": "Tipo de planta",
        "uso_label": "Ubicación / uso",
        "peso_label": "Riego / frecuencia",
        "caducidad_label": "Tiempo de cosecha",
        "lote_label": "Exposición",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": False,
        "mostrar_lote": True,
    },
    "comunicacion": {
        "titulo": "Comunicacion",
        "descripcion": "Registra radios y equipos de comunicacion con modelo, banda, antenas, bateria y pantalla.",
        "nombre_label": "Modelo",
        "tipo_label": "Tipo de equipo",
        "uso_label": "Bateria",
        "peso_label": "Banda",
        "caducidad_label": "Pantalla",
        "lote_label": "Antenas",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": False,
        "mostrar_lote": True,
    },
    "energia": {
        "titulo": "Energia",
        "descripcion": "Registra paneles solares, baterias recargables e inversores con capacidad y especificaciones electricas.",
        "nombre_label": "Modelo",
        "tipo_label": "Tipo de energia",
        "uso_label": "Salida",
        "peso_label": "Capacidad",
        "caducidad_label": "Voltaje",
        "lote_label": "Entrada",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": False,
        "mostrar_lote": True,
    },
    "higiene": {
        "titulo": "Higiene",
        "descripcion": "Registra insumos de higiene personal y limpieza con cantidad, presentación y reposición mínima.",
        "nombre_label": "Artículo de higiene",
        "tipo_label": "Tipo de higiene",
        "uso_label": "Uso / destino",
        "peso_label": "Presentación / contenido",
        "caducidad_label": "Caducidad / revisión (YYYY-MM-DD)",
        "lote_label": "Lote / marca",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": True,
        "mostrar_lote": True,
    },
    "movilidad": {
        "titulo": "Movilidad",
        "descripcion": "Registra vehículos, mochilas de evacuación, refacciones y equipo de desplazamiento.",
        "nombre_label": "Recurso de movilidad",
        "tipo_label": "Tipo de movilidad",
        "uso_label": "Uso / asignación",
        "peso_label": "Modelo / detalle",
        "caducidad_label": "Revisión / vigencia (YYYY-MM-DD)",
        "lote_label": "Serie / placas / lote",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": True,
        "mostrar_lote": True,
    },
    "cocina y preparacion": {
        "titulo": "Cocina y preparación",
        "descripcion": "Registra estufas, cartuchos de gas, hornos, deshidratadores y equipo para cocinar o preparar.",
        "nombre_label": "Equipo o insumo",
        "tipo_label": "Tipo de cocina / preparación",
        "uso_label": "Uso / preparación",
        "peso_label": "Capacidad / detalle",
        "caducidad_label": "Revisión / vigencia (YYYY-MM-DD)",
        "lote_label": "Lote / serie",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": True,
        "mostrar_lote": True,
    },
    "ropa": {
        "titulo": "Ropa",
        "descripcion": "Registra prendas, botas y equipo textil con tipo, clima, talla o detalle y cantidad.",
        "nombre_label": "Prenda / modelo",
        "tipo_label": "Tipo de ropa",
        "uso_label": "Clima / temporada",
        "peso_label": "Talla / detalle",
        "caducidad_label": "Revisión / reemplazo (YYYY-MM-DD)",
        "lote_label": "Lote / estado",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": False,
        "mostrar_lote": True,
    },
}

USOS_ANIMAL_PREDETERMINADOS = ["trabajo", "carne", "piel", "cuero", "productos varios"]
CLIMAS_ROPA_PREDETERMINADOS = ["Frio", "Calor", "Mixto"]


def _log_inventario_warning(message: str):
    registrar_log("warning", message, "inventario")


def _normalizar_categoria(nombre):
    return normalizar_texto(nombre)


def _perfil_categoria(nombre):
    base = {
        "titulo": nombre,
        "descripcion": "Registra recursos con cantidad, mínimo, observaciones y alertas.",
        "nombre_label": "Recurso",
        "tipo_label": "Tipo / subcategoría",
        "uso_label": "Uso / para qué sirve",
        "peso_label": "Peso / contenido",
        "caducidad_label": "Caducidad / revisión (YYYY-MM-DD)",
        "lote_label": "Lote / serie",
        "mostrar_nutrimental": False,
        "mostrar_foto": False,
        "mostrar_caducidad": True,
        "mostrar_lote": True,
    }
    base.update(PERFILES_CATEGORIA.get(_normalizar_categoria(nombre), {}))
    return base


def _formatear_encabezado_celda(texto, max_linea=14):
    texto = str(texto or "").strip()
    if not texto:
        return ""
    if len(texto) <= max_linea or " " not in texto:
        return texto
    palabras = texto.split()
    linea_1 = []
    linea_2 = []
    longitud = 0
    for palabra in palabras:
        extra = len(palabra) if not linea_1 else len(palabra) + 1
        if longitud + extra <= max_linea or not linea_1:
            linea_1.append(palabra)
            longitud += extra
        else:
            linea_2.append(palabra)
    if not linea_2:
        return texto
    return " ".join(linea_1) + "\n" + " ".join(linea_2)


def _configurar_ttk():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception as exc:
        _log_inventario_warning(f"No se pudo aplicar el tema ttk 'clam': {exc}")
    style.configure(
        "Treeview",
        background="white",
        foreground="black",
        fieldbackground="white",
        rowheight=28,
        font=("Arial", 10),
    )
    style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
    style.map(
        "Treeview",
        background=[("selected", "#2563EB")],
        foreground=[("selected", "white")],
    )
    style.configure(
        "InventarioDark.TCombobox",
        fieldbackground="#07102a",
        background="#07102a",
        foreground="white",
        arrowcolor="white",
        insertcolor="white",
        borderwidth=0,
        relief="flat",
        padding=4,
    )
    style.map(
        "InventarioDark.TCombobox",
        fieldbackground=[("readonly", "#07102a"), ("!disabled", "#07102a")],
        background=[("readonly", "#07102a"), ("!disabled", "#07102a")],
        foreground=[("readonly", "white"), ("!disabled", "white")],
    )


class DialogoCategoriaInventario(tk.Toplevel):
    def __init__(self, parent, categoria=None):
        super().__init__(parent)
        self.resultado = None
        self.title("Categoría de inventario")
        self.configure(bg="#08152f")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        aplicar_geometria_relativa(self, parent, rel_w=0.42, rel_h=0.82, min_w=520, min_h=620, pad=20)

        categoria = categoria or {}
        self.var_nombre = tk.StringVar(value=categoria.get("nombre", ""))
        self.var_icono = tk.StringVar(value=categoria.get("icono", "📦"))
        self.color = categoria.get("color", "#13223f")
        self.campos = [
            {
                "id": campo.get("id", f"campo_{idx + 1}"),
                "label": campo.get("label", ""),
            }
            for idx, campo in enumerate(categoria.get("campos", []) or [])
            if isinstance(campo, dict)
        ]
        self.vars_campos = []
        self.filas_campos = []
        self.drag_campo_index = None
        self.drag_campo_target = None

        tk.Label(self, text="Nombre", bg="#08152f", fg="white").pack(anchor="w", padx=16, pady=(16, 4))
        tk.Entry(self, textvariable=self.var_nombre, font=("Arial", 12), width=28).pack(fill="x", padx=16)

        tk.Label(self, text="Emoji", bg="#08152f", fg="white").pack(anchor="w", padx=16, pady=(10, 4))
        tk.Entry(self, textvariable=self.var_icono, font=("Arial", 14), width=8, justify="center").pack(anchor="w", padx=16)

        barra_color = tk.Frame(self, bg="#08152f")
        barra_color.pack(fill="x", padx=16, pady=(10, 6))
        self.lbl_color = tk.Label(barra_color, text=self.color, bg="#08152f", fg=self.color, font=("Arial", 11, "bold"))
        self.lbl_color.pack(side="left")
        tk.Button(barra_color, text="Elegir color", command=self._elegir_color, bg="#2563EB", fg="white").pack(side="left", padx=8)

        panel = tk.Frame(self, bg="#08152f")
        panel.pack(fill="x", padx=16, pady=(6, 0))
        for idx, emoji in enumerate(EMOJIS_CATEGORIAS):
            tk.Button(
                panel,
                text=emoji,
                width=3,
                bg="#1f2c44",
                fg="white",
                command=lambda e=emoji: self.var_icono.set(e),
            ).grid(row=idx // 10, column=idx % 10, padx=2, pady=2)

        tk.Label(self, text="Celdas de la categoría", bg="#08152f", fg="white", font=("Arial", 11, "bold")).pack(anchor="w", padx=16, pady=(10, 4))
        self.panel_campos = tk.Frame(self, bg="#08152f")
        self.panel_campos.pack(fill="x", padx=16)
        self._refrescar_campos()
        tk.Button(self, text="Agregar celda", command=self._agregar_celda, bg="#2563EB", fg="white").pack(anchor="w", padx=16, pady=(8, 0))

        barra = tk.Frame(self, bg="#08152f")
        barra.pack(fill="x", padx=16, pady=16)
        tk.Button(barra, text="Guardar", command=self._guardar, bg="#169c72", fg="white").pack(side="left")
        tk.Button(barra, text="Cancelar", command=self.destroy, bg="#64748b", fg="white").pack(side="left", padx=8)

        self.wait_window(self)

    def _elegir_color(self):
        color = colorchooser.askcolor(color=self.color, parent=self)[1]
        if color:
            self.color = color
            self.lbl_color.config(text=color, fg=color)

    def _refrescar_campos(self):
        for child in self.panel_campos.winfo_children():
            child.destroy()
        self.vars_campos = []
        self.filas_campos = []
        if not self.campos:
            tk.Label(self.panel_campos, text="Sin celdas configuradas.", bg="#08152f", fg="#9fb4d0").pack(anchor="w")
            return

        for idx, campo in enumerate(self.campos):
            fila = tk.Frame(self.panel_campos, bg="#13223f", highlightthickness=1, highlightbackground="#28496B")
            fila.pack(fill="x", pady=4)
            self.filas_campos.append(fila)
            asa = tk.Label(fila, text="≡", bg="#13223f", fg="#9fb4d0", font=("Arial", 12, "bold"), width=2, cursor="fleur")
            asa.pack(side="left", padx=(6, 4))
            tk.Label(fila, text=f"Celda {idx + 1}", bg="#13223f", fg="white", width=8).pack(side="left", padx=(8, 6))
            var = tk.StringVar(value=campo.get("label", ""))
            self.vars_campos.append(var)
            tk.Entry(fila, textvariable=var, font=("Arial", 11), bg="#07102a", fg="white", insertbackground="white", relief="flat").pack(side="left", fill="x", expand=True, padx=(0, 8), pady=8)
            tk.Button(fila, text="↑", width=3, command=lambda i=idx: self._mover_celda(i, -1), bg="#1d4ed8", fg="white").pack(side="left", padx=2)
            tk.Button(fila, text="↓", width=3, command=lambda i=idx: self._mover_celda(i, 1), bg="#1d4ed8", fg="white").pack(side="left", padx=2)
            tk.Button(fila, text="Eliminar", command=lambda i=idx: self._eliminar_celda(i), bg="#b91c1c", fg="white").pack(side="left", padx=(6, 8))
            for widget in (fila, asa):
                widget.bind("<ButtonPress-1>", lambda event, i=idx: self._iniciar_arrastre_campo(event, i))
                widget.bind("<B1-Motion>", self._arrastrar_campo)
                widget.bind("<ButtonRelease-1>", self._soltar_campo)

    def _sincronizar_campos_desde_vars(self):
        for idx, campo in enumerate(self.campos):
            if idx < len(self.vars_campos):
                campo["label"] = self.vars_campos[idx].get().strip()

    def _agregar_celda(self):
        self._sincronizar_campos_desde_vars()
        nombre = simpledialog.askstring("Agregar celda", "Nombre de la nueva celda:", parent=self)
        if nombre is None:
            return
        nombre = nombre.strip()
        if not nombre:
            messagebox.showwarning("Revisa los datos", "Escribe un nombre para la celda.", parent=self)
            return
        self.campos.append({"id": f"campo_{len(self.campos) + 1}", "label": nombre})
        self._refrescar_campos()

    def _eliminar_celda(self, indice):
        if 0 <= indice < len(self.campos):
            self._sincronizar_campos_desde_vars()
            self.campos.pop(indice)
            self._refrescar_campos()

    def _mover_celda(self, indice, direccion):
        destino = indice + direccion
        if 0 <= indice < len(self.campos) and 0 <= destino < len(self.campos):
            self._sincronizar_campos_desde_vars()
            self.campos[indice], self.campos[destino] = self.campos[destino], self.campos[indice]
            self._refrescar_campos()

    def _iniciar_arrastre_campo(self, event, indice):
        self._sincronizar_campos_desde_vars()
        self.drag_campo_index = indice
        self.drag_campo_target = indice
        self._resaltar_fila_arrastre(indice)

    def _arrastrar_campo(self, event):
        if self.drag_campo_index is None or not self.filas_campos:
            return
        y_root = event.widget.winfo_pointery()
        candidatos = []
        for idx, fila in enumerate(self.filas_campos):
            centro = fila.winfo_rooty() + (fila.winfo_height() / 2)
            candidatos.append((abs(centro - y_root), idx))
        if not candidatos:
            return
        candidatos.sort(key=lambda item: item[0])
        self.drag_campo_target = candidatos[0][1]
        self._resaltar_fila_arrastre(self.drag_campo_target)

    def _soltar_campo(self, event=None):
        if self.drag_campo_index is None:
            return
        origen = self.drag_campo_index
        destino = self.drag_campo_target if self.drag_campo_target is not None else origen
        self.drag_campo_index = None
        self.drag_campo_target = None
        self._resaltar_fila_arrastre(None)
        if destino == origen or not (0 <= destino < len(self.campos)):
            return
        campo = self.campos.pop(origen)
        self.campos.insert(destino, campo)
        self._refrescar_campos()

    def _resaltar_fila_arrastre(self, indice):
        for idx, fila in enumerate(self.filas_campos):
            color = "#2563EB" if indice == idx else "#28496B"
            fila.config(highlightbackground=color, highlightcolor=color)

    def _guardar(self):
        nombre = self.var_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Revisa los datos", "Escribe el nombre de la categoría.", parent=self)
            return
        campos = []
        for idx, campo in enumerate(self.campos):
            etiqueta = self.vars_campos[idx].get().strip() if idx < len(self.vars_campos) else ""
            if not etiqueta:
                continue
            campo_id = campo.get("id", f"campo_{idx + 1}")
            campos.append({"id": campo_id, "label": etiqueta, "posicion": idx})
        self.resultado = {
            "nombre": nombre,
            "icono": self.var_icono.get().strip() or "📦",
            "color": self.color,
            "campos": campos,
        }
        self.destroy()


class VentanaCategoriaInventario:
    def __init__(self, parent, categoria_nombre, on_change=None, on_close=None):
        self.parent = parent
        self.categoria_actual = categoria_nombre
        self.on_change = on_change
        self.on_close = on_close
        self.inventario = Inventario()
        self.alertas_visibles = []
        self.items_visibles = []
        self.item_editando_id = None
        self.ruta_foto_actual = ""
        self.codigo_barras_actual = ""
        self.busqueda_actual = ""
        self.perfil = _perfil_categoria(categoria_nombre)
        self.firma_campos_actual = ""
        self.modo_registro = "general"
        self.combos_catalogo = {}

        self.bg_principal = "#08152f"
        self.bg_panel = "#1f2c44"
        self.bg_panel_2 = "#0b1733"
        self.fg = "#ffffff"
        self.acento = "#2f66d0"
        self.acento_ok = "#169c72"
        self.acento_warn = "#d18d19"
        self.acento_danger = "#cc2f2f"

        self.top = tk.Toplevel()
        self.top.title(f"TLAMATINI - {self.perfil['titulo']}")
        self.top.configure(bg=self.bg_principal)
        self.top.resizable(True, True)
        self.top.minsize(1080, 700)
        self._ajustar_a_pantalla()
        self.top.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.top.bind("<FocusIn>", self._al_recuperar_foco)
        self.top.lift()
        self.top.focus_force()

        _configurar_ttk()
        self._crear_ui()
        self._cargar_opciones_categoria()
        self._refrescar_todo()

    def _ajustar_a_pantalla(self):
        aplicar_geometria_relativa(self.top, self.parent, rel_w=0.94, rel_h=0.92, min_w=1080, min_h=700, pad=20)

    def _crear_ui(self):
        _, _, contenido = crear_contenedor_scrollable(self.top, bg=self.bg_principal)
        contenido.grid_columnconfigure(0, weight=1)

        header = tk.Frame(contenido, bg=self.bg_principal)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        tk.Label(
            header,
            text=self.perfil["titulo"].upper(),
            font=("Arial", 24, "bold"),
            bg=self.bg_principal,
            fg=self.fg,
        ).grid(row=0, column=0, sticky="w")

        cuerpo = tk.Frame(contenido, bg=self.bg_principal)
        cuerpo.grid(row=1, column=0, sticky="nsew", padx=20, pady=(4, 20))
        cuerpo.grid_rowconfigure(0, weight=1)
        cuerpo.grid_rowconfigure(2, weight=1)
        cuerpo.grid_columnconfigure(0, weight=1)

        top_listado = tk.Frame(cuerpo, bg=self.bg_principal)
        top_listado.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top_listado.grid_columnconfigure(0, weight=1)
        top_listado.grid_columnconfigure(1, weight=0)

        self.lbl_listado = tk.Label(top_listado, text="", font=("Arial", 18, "bold"), bg=self.bg_principal, fg=self.fg)
        self.lbl_listado.grid(row=0, column=0, sticky="w")

        acciones = tk.Frame(top_listado, bg=self.bg_principal)
        acciones.grid(row=0, column=1, sticky="ne", padx=(16, 0))
        self.btn_buscar_item = tk.Button(
            acciones,
            text="Buscar",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            activebackground="#2454ad",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=8,
            width=14,
            command=self._buscar_item_por_nombre,
        )
        self.btn_buscar_item.pack(side="left", padx=(0, 6))
        if self._es_categoria_insumos_medicos():
            self.btn_agregar_insumo = tk.Button(
                acciones,
                text="Agregar insumo",
                font=("Arial", 11, "bold"),
                bg=self.acento,
                fg="white",
                activebackground="#2454ad",
                activeforeground="white",
                relief="flat",
                padx=16,
                pady=8,
                width=14,
                command=self._abrir_dialogo_insumo_nuevo_especial,
            )
            self.btn_agregar_insumo.pack(side="left", padx=(0, 6))
        self.btn_agregar_item = tk.Button(
            acciones,
            text="Agregar medicamento" if self._es_categoria_insumos_medicos() else "Agregar",
            font=("Arial", 11, "bold"),
            bg=self.acento_ok,
            fg="white",
            activebackground="#11815e",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=8,
            width=14,
            command=self._abrir_dialogo_medicamento_nuevo if self._es_categoria_insumos_medicos() else self._abrir_dialogo_item_nuevo,
        )
        self.btn_agregar_item.pack(side="left")
        self.btn_consumir_item = tk.Button(acciones, text="Consumir", font=("Arial", 11, "bold"), bg="#ef4444", fg="white", width=14, command=self._consumir_item_seleccionado)
        self.btn_editar_item = tk.Button(acciones, text="Editar", font=("Arial", 11, "bold"), bg=self.acento_warn, fg="black", width=14, command=self._cargar_a_edicion)
        self.btn_eliminar_item = tk.Button(acciones, text="Eliminar", font=("Arial", 11, "bold"), bg=self.acento_danger, fg="white", width=14, command=self._eliminar_producto)

        tabla_frame = tk.Frame(cuerpo, bg=self.bg_panel)
        tabla_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 14))
        tabla_frame.grid_rowconfigure(0, weight=1)
        tabla_frame.grid_columnconfigure(0, weight=1)

        if self._permite_consumo_por_unidades():
            columnas = (
                "nombre",
                "cantidad",
                "unidad",
                "contenido",
                "total",
                "minimo",
                "fecha_ingreso",
                "fecha_compra",
                "caducidad",
            )
            headers = {
                "nombre": "Alimento",
                "cantidad": "Cantidad",
                "unidad": "Unidad",
                "contenido": "Contenido por unidad",
                "total": "Total",
                "minimo": "Mínimo",
                "fecha_ingreso": "Ingreso",
                "fecha_compra": "Producción / compra",
                "caducidad": "Caducidad",
            }
            widths = {
                "nombre": 240,
                "cantidad": 95,
                "unidad": 115,
                "contenido": 210,
                "total": 130,
                "minimo": 95,
                "fecha_ingreso": 120,
                "fecha_compra": 185,
                "caducidad": 120,
            }
        elif self._es_categoria_combate() or self._es_categoria_herramientas():
            columnas = (
                "tipo",
                "nombre",
                "cantidad",
                "minimo",
                "lote",
                "fecha_ingreso",
                "fecha_compra",
                "caducidad",
            )
            headers = {
                "tipo": "Tipo",
                "nombre": "Modelo",
                "cantidad": "Cantidad",
                "minimo": "Mínimo",
                "lote": "Serie / lote",
                "fecha_ingreso": "Ingreso",
                "fecha_compra": "Compra",
                "caducidad": "Caducidad",
            }
            widths = {
                "tipo": 150,
                "nombre": 170,
                "cantidad": 95,
                "minimo": 95,
                "lote": 150,
                "fecha_ingreso": 120,
                "fecha_compra": 120,
                "caducidad": 120,
            }
        elif self._es_categoria_animales():
            columnas = ("tipo", "nombre", "cantidad", "alimento", "agua", "uso", "lote")
            headers = {
                "tipo": "Tipo",
                "nombre": "Identificación / raza",
                "cantidad": "Cantidad",
                "alimento": "Alimento por día",
                "agua": "Agua por día",
                "uso": "Uso",
                "lote": "Etapa / lote",
            }
            widths = {
                "tipo": 150,
                "nombre": 190,
                "cantidad": 90,
                "alimento": 150,
                "agua": 140,
                "uso": 180,
                "lote": 140,
            }
        elif self._es_categoria_comunicacion():
            columnas = ("tipo", "nombre", "cantidad", "banda", "antenas", "bateria", "pantalla")
            headers = {
                "tipo": "Tipo",
                "nombre": "Modelo",
                "cantidad": "Cantidad",
                "banda": "Banda",
                "antenas": "Antenas",
                "bateria": "Bateria",
                "pantalla": "Pantalla",
            }
            widths = {
                "tipo": 150,
                "nombre": 180,
                "cantidad": 90,
                "banda": 150,
                "antenas": 130,
                "bateria": 140,
                "pantalla": 130,
            }
        elif self._es_categoria_energia():
            columnas = ("tipo", "nombre", "cantidad", "capacidad", "voltaje", "entrada", "salida")
            headers = {
                "tipo": "Tipo",
                "nombre": "Modelo",
                "cantidad": "Cantidad",
                "capacidad": "Capacidad",
                "voltaje": "Voltaje",
                "entrada": "Entrada",
                "salida": "Salida",
            }
            widths = {
                "tipo": 160,
                "nombre": 180,
                "cantidad": 90,
                "capacidad": 150,
                "voltaje": 120,
                "entrada": 150,
                "salida": 150,
            }
        elif self._es_categoria_higiene():
            columnas = ("tipo", "nombre", "cantidad", "unidad", "contenido", "minimo", "caducidad", "lote")
            headers = {
                "tipo": "Tipo",
                "nombre": "Artículo",
                "cantidad": "Cantidad",
                "unidad": "Unidad",
                "contenido": "Presentación",
                "minimo": "Mínimo",
                "caducidad": "Caducidad",
                "lote": "Lote / marca",
            }
            widths = {
                "tipo": 150,
                "nombre": 190,
                "cantidad": 90,
                "unidad": 90,
                "contenido": 150,
                "minimo": 90,
                "caducidad": 120,
                "lote": 140,
            }
        elif self._es_categoria_movilidad():
            columnas = ("tipo", "nombre", "cantidad", "capacidad", "autonomia", "uso", "serie")
            headers = {
                "tipo": "Tipo",
                "nombre": "Recurso / modelo",
                "cantidad": "Cantidad",
                "capacidad": "Capacidad / carga",
                "autonomia": "Combustible / autonomía",
                "uso": "Uso / asignación",
                "serie": "Serie / placas",
            }
            widths = {
                "tipo": 150,
                "nombre": 190,
                "cantidad": 90,
                "capacidad": 150,
                "autonomia": 170,
                "uso": 170,
                "serie": 140,
            }
        elif self._es_categoria_cocina_preparacion():
            columnas = ("tipo", "nombre", "cantidad", "unidad", "capacidad", "combustible", "lote")
            headers = {
                "tipo": "Tipo",
                "nombre": "Equipo / insumo",
                "cantidad": "Cantidad",
                "unidad": "Unidad",
                "capacidad": "Capacidad / potencia",
                "combustible": "Combustible / fuente",
                "lote": "Lote / serie",
            }
            widths = {
                "tipo": 150,
                "nombre": 190,
                "cantidad": 90,
                "unidad": 90,
                "capacidad": 160,
                "combustible": 170,
                "lote": 140,
            }
        elif self._es_categoria_ropa():
            columnas = ("tipo", "nombre", "cantidad", "unidad", "clima", "detalle", "lote")
            headers = {
                "tipo": "Tipo",
                "nombre": "Prenda / modelo",
                "cantidad": "Cantidad",
                "unidad": "Unidad",
                "clima": "Clima",
                "detalle": "Talla / detalle",
                "lote": "Lote / estado",
            }
            widths = {
                "tipo": 150,
                "nombre": 190,
                "cantidad": 90,
                "unidad": 90,
                "clima": 110,
                "detalle": 150,
                "lote": 140,
            }
        elif self._es_categoria_plantas():
            columnas = ("tipo", "nombre", "cantidad", "riego", "clima")
            headers = {
                "tipo": "Tipo",
                "nombre": "Variedad",
                "cantidad": "Redundancia",
                "riego": "Riego / frecuencia",
                "clima": "Clima",
            }
            widths = {
                "tipo": 150,
                "nombre": 170,
                "cantidad": 120,
                "riego": 150,
                "clima": 130,
            }
        elif self._usa_campos_personalizados():
            campos = self._campos_personalizados()
            if campos:
                columnas = tuple(campo["id"] for campo in campos)
                headers = {campo["id"]: _formatear_encabezado_celda(campo.get("label", ""), max_linea=16) for campo in campos}
                widths = {campo["id"]: max(150, min(260, len(campo.get("label", "")) * 10)) for campo in campos}
            else:
                columnas = ("__sin_campos__",)
                headers = {"__sin_campos__": "Sin celdas"}
                widths = {"__sin_campos__": 280}
        else:
            columnas = ("nombre", "tipo", "cantidad", "unidad", "minimo", "peso", "caducidad", "lote")
            headers = {
                "nombre": "Nombre",
                "tipo": "Tipo",
                "cantidad": "Cantidad",
                "unidad": "Unidad",
                "minimo": "Mínimo",
                "peso": "Detalle",
                "caducidad": "Fecha",
                "lote": "Lote / serie",
            }
            widths = {"nombre": 220, "tipo": 120, "cantidad": 90, "unidad": 90, "minimo": 90, "peso": 150, "caducidad": 130, "lote": 130}
        self.tree = ttk.Treeview(tabla_frame, columns=columnas, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        for col in columnas:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], minwidth=widths[col], anchor="center")
        yscroll = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._mostrar_detalle_item)
        habilitar_scroll_mouse(tabla_frame, self.tree)

        alertas_top = tk.Frame(cuerpo, bg=self.bg_principal)
        alertas_top.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        alertas_top.grid_columnconfigure(0, weight=1)
        tk.Label(alertas_top, text="Alertas de esta categoría", font=("Arial", 16, "bold"), bg=self.bg_principal, fg=self.fg).grid(row=0, column=0, sticky="w")

        alertas_frame = tk.Frame(cuerpo, bg=self.bg_panel_2, bd=1, relief="solid")
        alertas_frame.grid(row=3, column=0, sticky="nsew")
        alertas_frame.grid_columnconfigure(0, weight=1)
        alertas_frame.grid_rowconfigure(0, weight=1)
        self.lista_alertas = tk.Listbox(alertas_frame, bg="#07102a", fg="#ffb0b0", selectbackground="#2563EB", selectforeground="white", font=("Arial", 11))
        self.lista_alertas.grid(row=0, column=0, sticky="nsew")

        self._crear_dialogo_item()
        if self._es_categoria_insumos_medicos():
            self._crear_dialogo_medicamento()
            self._crear_dialogo_insumo()

    def _crear_dialogo_item(self):
        self.dialogo_item = tk.Toplevel(self.top)
        self.dialogo_item.title(f"{self.perfil['titulo']} - Item")
        self.dialogo_item.configure(bg=self.bg_principal)
        self.dialogo_item.resizable(True, True)
        min_w, min_h = self._tamano_dialogo_item()
        self.dialogo_item.minsize(min_w, min_h)
        self._aplicar_geometria_dialogo_item()
        self.dialogo_item.withdraw()
        self.dialogo_item.transient(self.top)
        self.dialogo_item.protocol("WM_DELETE_WINDOW", self._ocultar_dialogo_item)
        self.panel_form = tk.Frame(self.dialogo_item, bg=self.bg_panel)
        self.panel_form.pack(fill="both", expand=True)
        self._reconstruir_panel_formulario()

    def _reconstruir_panel_formulario(self):
        for child in self.panel_form.winfo_children():
            child.destroy()
        self._crear_panel_formulario()

    def _mostrar_dialogo_item(self, reconstruir=True):
        if reconstruir:
            self._reconstruir_panel_formulario()
        self._aplicar_geometria_dialogo_item()
        self.dialogo_item.deiconify()
        self.dialogo_item.lift()
        self.dialogo_item.focus_force()
        objetivo = getattr(self, "entry_nombre", None)
        if not objetivo and getattr(self, "campos_extra_widgets", None):
            objetivo = next(iter(self.campos_extra_widgets.values()), None)
        if objetivo is not None:
            self.dialogo_item.after(80, lambda: objetivo.focus_set())

    def _ocultar_dialogo_item(self):
        self.dialogo_item.withdraw()
        if self.top.winfo_exists():
            self.top.lift()
            self.top.focus_force()

    def _tamano_dialogo_item(self):
        if self._es_categoria_animales() or self._es_categoria_comunicacion():
            return 980, 760
        return 760, 720

    def _aplicar_geometria_dialogo_item(self):
        min_w, min_h = self._tamano_dialogo_item()
        rel_w = 0.94 if (self._es_categoria_animales() or self._es_categoria_comunicacion()) else 0.76
        rel_h = 0.94 if (self._es_categoria_animales() or self._es_categoria_comunicacion()) else 0.88
        aplicar_geometria_relativa(self.dialogo_item, self.top, rel_w=rel_w, rel_h=rel_h, min_w=min_w, min_h=min_h, pad=20)

    def _crear_dialogo_medicamento(self):
        self.dialogo_medicamento = tk.Toplevel(self.top)
        self.dialogo_medicamento.title(f"{self.perfil['titulo']} - Agregar medicamento")
        self.dialogo_medicamento.configure(bg=self.bg_principal)
        self.dialogo_medicamento.resizable(True, True)
        self.dialogo_medicamento.minsize(760, 560)
        aplicar_geometria_relativa(self.dialogo_medicamento, self.top, rel_w=0.7, rel_h=0.68, min_w=760, min_h=560, pad=20)
        self.dialogo_medicamento.withdraw()
        self.dialogo_medicamento.transient(self.top)
        self.dialogo_medicamento.protocol("WM_DELETE_WINDOW", self._ocultar_dialogo_medicamento)
        self.panel_medicamento = tk.Frame(self.dialogo_medicamento, bg=self.bg_panel)
        self.panel_medicamento.pack(fill="both", expand=True)
        self._crear_panel_dialogo_medicamento()

    def _crear_dialogo_insumo(self):
        self.dialogo_insumo = tk.Toplevel(self.top)
        self.dialogo_insumo.title(f"{self.perfil['titulo']} - Agregar insumo")
        self.dialogo_insumo.configure(bg=self.bg_principal)
        self.dialogo_insumo.resizable(True, True)
        self.dialogo_insumo.minsize(820, 640)
        aplicar_geometria_relativa(self.dialogo_insumo, self.top, rel_w=0.74, rel_h=0.78, min_w=820, min_h=640, pad=20)
        self.dialogo_insumo.withdraw()
        self.dialogo_insumo.transient(self.top)
        self.dialogo_insumo.protocol("WM_DELETE_WINDOW", self._ocultar_dialogo_insumo)
        self.panel_insumo = tk.Frame(self.dialogo_insumo, bg=self.bg_panel)
        self.panel_insumo.pack(fill="both", expand=True)
        self._crear_panel_dialogo_insumo()

    def _crear_panel_dialogo_medicamento(self):
        for child in self.panel_medicamento.winfo_children():
            child.destroy()

        cont = tk.Frame(self.panel_medicamento, bg=self.bg_panel)
        cont.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(cont, text="Agregar medicamento", font=("Arial", 18, "bold"), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(0, 14))

        fila_1 = tk.Frame(cont, bg=self.bg_panel)
        fila_1.pack(fill="x", pady=(0, 10))
        for col in range(3):
            fila_1.grid_columnconfigure(col, weight=1, uniform="medicamento_nuevo")
        self.entry_med_nombre = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_med_formula = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_med_cantidad = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self._crear_campo_grid_medicamento_dialogo(fila_1, 0, "Nombre", self.entry_med_nombre)
        self._crear_campo_grid_medicamento_dialogo(fila_1, 1, "Formula (ej. 860mg 230mg)", self.entry_med_formula, padx=(4, 4))
        self._crear_campo_grid_medicamento_dialogo(fila_1, 2, "Cantidad (caja / ingreso)", self.entry_med_cantidad, padx=(8, 0))

        fila_2 = tk.Frame(cont, bg=self.bg_panel)
        fila_2.pack(fill="x", pady=(0, 10))
        for col in range(3):
            fila_2.grid_columnconfigure(col, weight=1, uniform="medicamento_nuevo")
        self.combo_med_unidad = ttk.Combobox(
            fila_2,
            font=("Arial", 11),
            state="readonly",
            style="InventarioDark.TCombobox",
            values=["Mililitros", "Miligramos", "Gramos"],
        )
        self.entry_med_caducidad = tk.Entry(fila_2, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_med_stock = tk.Entry(fila_2, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self._crear_campo_grid_medicamento_dialogo(fila_2, 0, "Unidad", self.combo_med_unidad)
        self._crear_campo_grid_medicamento_dialogo(fila_2, 1, "Caducidad (DD/MM/AAAA o DD.MM.AAAA)", self.entry_med_caducidad, padx=(4, 4))
        self._crear_campo_grid_medicamento_dialogo(fila_2, 2, "Stock minimo", self.entry_med_stock, padx=(8, 0))
        self.combo_med_unidad.set("Miligramos")

        barra_codigo = tk.Frame(cont, bg=self.bg_panel)
        barra_codigo.pack(fill="x", pady=(0, 10))
        tk.Button(
            barra_codigo,
            text="Escanear codigo",
            font=("Arial", 10, "bold"),
            bg=self.acento,
            fg="white",
            activebackground="#2454ad",
            activeforeground="white",
            relief="flat",
            command=self._escanear_codigo_barras_medicamento,
        ).pack(side="left")
        tk.Button(
            barra_codigo,
            text="Tomar foto",
            font=("Arial", 10, "bold"),
            bg="#0f766e",
            fg="white",
            activebackground="#0b5f5a",
            activeforeground="white",
            relief="flat",
            command=self._capturar_foto_medicamento,
        ).pack(side="left", padx=(8, 0))
        self.lbl_codigo_medicamento = tk.Label(
            barra_codigo,
            text="Sin codigo registrado",
            bg=self.bg_panel,
            fg="#c8d2e6",
            font=("Arial", 10),
            anchor="w",
            justify="left",
        )
        self.lbl_codigo_medicamento.pack(side="left", padx=10)

        tk.Label(cont, text="Descripcion", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(10, 4))
        self.txt_med_descripcion = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_med_descripcion.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_dialogo_medicamento).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_dialogo_medicamento).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_med_cantidad)
        self._configurar_validacion_numerica(self.entry_med_stock)

    def _crear_panel_dialogo_insumo(self):
        for child in self.panel_insumo.winfo_children():
            child.destroy()

        cont = tk.Frame(self.panel_insumo, bg=self.bg_panel)
        cont.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(cont, text="Agregar insumo", font=("Arial", 18, "bold"), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(0, 14))

        fila_1 = tk.Frame(cont, bg=self.bg_panel)
        fila_1.pack(fill="x", pady=(0, 10))
        for col in range(4):
            fila_1.grid_columnconfigure(col, weight=1, uniform="insumo_nuevo")
        self.entry_ins_tipo = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_ins_cantidad = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_ins_contenido = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_ins_unidad = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self._crear_campo_grid_medicamento_dialogo(fila_1, 0, "Tipo", self.entry_ins_tipo)
        self._crear_campo_grid_medicamento_dialogo(fila_1, 1, "Cantidad", self.entry_ins_cantidad, padx=(4, 4))
        self._crear_campo_grid_medicamento_dialogo(fila_1, 2, "Contenido", self.entry_ins_contenido, padx=(4, 4))
        self._crear_campo_grid_medicamento_dialogo(fila_1, 3, "Unidad", self.entry_ins_unidad, padx=(8, 0))

        fila_2 = tk.Frame(cont, bg=self.bg_panel)
        fila_2.pack(fill="x", pady=(0, 10))
        for col in range(2):
            fila_2.grid_columnconfigure(col, weight=1, uniform="insumo_nuevo_2")
        self.entry_ins_caducidad = tk.Entry(fila_2, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_ins_stock = tk.Entry(fila_2, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self._crear_campo_grid_medicamento_dialogo(fila_2, 0, "caducidad (D.M.A)", self.entry_ins_caducidad)
        self._crear_campo_grid_medicamento_dialogo(fila_2, 1, "Stock minimo", self.entry_ins_stock, padx=(8, 0))

        tk.Label(cont, text="Descripcion", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(10, 4))
        self.txt_ins_descripcion = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_ins_descripcion.pack(fill="x")

        barra_codigo = tk.Frame(cont, bg=self.bg_panel)
        barra_codigo.pack(fill="x", pady=(12, 10))
        tk.Button(
            barra_codigo,
            text="Escanear codigo",
            font=("Arial", 10, "bold"),
            bg=self.acento,
            fg="white",
            activebackground="#2454ad",
            activeforeground="white",
            relief="flat",
            command=self._escanear_codigo_barras_insumo,
        ).pack(side="left")
        tk.Button(
            barra_codigo,
            text="Tomar foto",
            font=("Arial", 10, "bold"),
            bg="#0f766e",
            fg="white",
            activebackground="#0b5f5a",
            activeforeground="white",
            relief="flat",
            command=self._capturar_foto_insumo,
        ).pack(side="left", padx=(8, 0))
        self.lbl_codigo_insumo = tk.Label(barra_codigo, text="Sin codigo registrado", bg=self.bg_panel, fg="#c8d2e6", font=("Arial", 10))
        self.lbl_codigo_insumo.pack(side="left", padx=10)

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_dialogo_insumo).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_dialogo_insumo).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_ins_cantidad)
        self._configurar_validacion_numerica(self.entry_ins_stock)

    def _crear_campo_grid_medicamento_dialogo(self, parent, col, titulo, widget, padx=(0, 8)):
        tk.Label(parent, text=titulo, font=("Arial", 10), bg=self.bg_panel, fg="white").grid(row=0, column=col, sticky="w", padx=padx, pady=(0, 4))
        widget.grid(row=1, column=col, sticky="ew", padx=padx)

    def _mostrar_dialogo_medicamento(self):
        aplicar_geometria_relativa(self.dialogo_medicamento, self.top, rel_w=0.7, rel_h=0.68, min_w=760, min_h=560, pad=20)
        self.dialogo_medicamento.deiconify()
        self.dialogo_medicamento.lift()
        self.dialogo_medicamento.focus_force()
        self.dialogo_medicamento.after(80, lambda: self.entry_med_nombre.focus_set())

    def _ocultar_dialogo_medicamento(self):
        self.dialogo_medicamento.withdraw()
        if self.top.winfo_exists():
            self.top.lift()
            self.top.focus_force()

    def _mostrar_dialogo_insumo(self):
        aplicar_geometria_relativa(self.dialogo_insumo, self.top, rel_w=0.74, rel_h=0.78, min_w=820, min_h=640, pad=20)
        self.dialogo_insumo.deiconify()
        self.dialogo_insumo.lift()
        self.dialogo_insumo.focus_force()
        self.dialogo_insumo.after(80, lambda: self.entry_ins_tipo.focus_set())

    def _ocultar_dialogo_insumo(self):
        self.dialogo_insumo.withdraw()
        if self.top.winfo_exists():
            self.top.lift()
            self.top.focus_force()

    def _abrir_dialogo_medicamento_nuevo(self):
        self.item_editando_id = None
        self._limpiar_dialogo_medicamento()
        self._mostrar_dialogo_medicamento()

    def _abrir_dialogo_insumo_nuevo_especial(self):
        self.item_editando_id = None
        self._limpiar_dialogo_insumo()
        self._mostrar_dialogo_insumo()

    def _limpiar_dialogo_medicamento(self):
        self.entry_med_nombre.delete(0, "end")
        self.entry_med_formula.delete(0, "end")
        self.entry_med_cantidad.delete(0, "end")
        self.entry_med_caducidad.delete(0, "end")
        self.entry_med_stock.delete(0, "end")
        self.combo_med_unidad.set("Miligramos")
        self.txt_med_descripcion.delete("1.0", "end")
        self.codigo_barras_actual = ""
        if hasattr(self, "lbl_codigo_medicamento"):
            self.lbl_codigo_medicamento.config(text="Sin codigo registrado")

    def _limpiar_dialogo_insumo(self):
        self.entry_ins_tipo.delete(0, "end")
        self.entry_ins_cantidad.delete(0, "end")
        self.entry_ins_contenido.delete(0, "end")
        self.entry_ins_unidad.delete(0, "end")
        self.entry_ins_caducidad.delete(0, "end")
        self.entry_ins_stock.delete(0, "end")
        self.txt_ins_descripcion.delete("1.0", "end")
        self.codigo_barras_actual = ""
        if hasattr(self, "lbl_codigo_insumo"):
            self.lbl_codigo_insumo.config(text="Sin codigo registrado")

    def _guardar_dialogo_medicamento(self):
        categoria = self._categoria_data_actual()
        if not categoria:
            messagebox.showwarning("Categoría no disponible", "No se encontró la categoría actual.", parent=self.top)
            return
        caducidad = self._normalizar_fecha_caducidad_medicamento(self.entry_med_caducidad.get().strip())
        if caducidad is None:
            messagebox.showwarning("Revisa los datos", "La caducidad debe ir como DD/MM/AAAA, DD.MM.AAAA o YYYY-MM-DD.", parent=self.top)
            return
        datos = {
            "categoria_id": categoria["id"],
            "subcategoria": "medicamento",
            "tipo": "medicamento",
            "nombre": self.entry_med_nombre.get().strip(),
            "codigo_barras": self.codigo_barras_actual,
            "cantidad": self.entry_med_cantidad.get().strip(),
            "unidad": self.combo_med_unidad.get().strip(),
            "minimo": self.entry_med_stock.get().strip(),
            "peso_contenido": self.entry_med_formula.get().strip(),
            "caducidad": caducidad,
            "lote": "",
            "proposito": "",
            "observaciones": self.txt_med_descripcion.get("1.0", "end").strip(),
            "nutrimentales": "",
            "nutrimental": {},
            "foto": "",
            "origen": "manual",
        }
        try:
            if self.item_editando_id:
                actualizar_item(self.item_editando_id, **datos)
                messagebox.showinfo("Actualizado", f'Se actualizó "{datos["nombre"]}".', parent=self.top)
            else:
                agregar_item(**datos)
                messagebox.showinfo("Guardado", f'Se agregó "{datos["nombre"]}".', parent=self.top)
            self._limpiar_dialogo_medicamento()
            self._ocultar_dialogo_medicamento()
            self._refrescar_todo()
            if self.on_change:
                self.on_change()
        except ValueError as e:
            messagebox.showwarning("Revisa los datos", str(e), parent=self.top)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.top)

    def _normalizar_fecha_caducidad_medicamento(self, texto):
        texto = (texto or "").strip()
        if not texto:
            return ""

        candidatos = [
            (texto.replace(".", "/"), "%d/%m/%Y"),
            (texto.replace(".", "/"), "%Y/%m/%d"),
            (texto, "%Y-%m-%d"),
        ]
        for valor, patron in candidatos:
            try:
                return datetime.strptime(valor, patron).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def _guardar_dialogo_insumo(self):
        categoria = self._categoria_data_actual()
        if not categoria:
            messagebox.showwarning("Categoría no disponible", "No se encontró la categoría actual.", parent=self.top)
            return
        caducidad = self._normalizar_fecha_caducidad_medicamento(self.entry_ins_caducidad.get().strip())
        if caducidad is None:
            messagebox.showwarning("Revisa los datos", "La caducidad debe ir como DD/MM/AAAA, DD.MM.AAAA o YYYY-MM-DD.", parent=self.top)
            return
        tipo = self.entry_ins_tipo.get().strip()
        if not tipo:
            messagebox.showwarning("Revisa los datos", "Escribe el tipo del insumo.", parent=self.top)
            return
        unidad = self.entry_ins_unidad.get().strip()
        if not unidad:
            messagebox.showwarning("Revisa los datos", "Escribe la unidad del insumo.", parent=self.top)
            return
        datos = {
            "categoria_id": categoria["id"],
            "subcategoria": tipo,
            "tipo": tipo,
            "nombre": tipo,
            "codigo_barras": self.codigo_barras_actual,
            "cantidad": self.entry_ins_cantidad.get().strip(),
            "unidad": unidad,
            "minimo": self.entry_ins_stock.get().strip(),
            "peso_contenido": self.entry_ins_contenido.get().strip(),
            "caducidad": caducidad,
            "lote": "",
            "proposito": "",
            "observaciones": self.txt_ins_descripcion.get("1.0", "end").strip(),
            "nutrimentales": "",
            "nutrimental": {},
            "foto": "",
            "origen": "codigo_barras" if self.codigo_barras_actual else "manual",
        }
        try:
            if self.item_editando_id:
                actualizar_item(self.item_editando_id, **datos)
                messagebox.showinfo("Actualizado", f'Se actualizó "{datos["nombre"]}".', parent=self.top)
            else:
                coincidencia = buscar_producto_por_nombre(categoria["id"], datos["nombre"])
                if coincidencia and coincidencia[1].get("unidad", "").strip().lower() == unidad.lower():
                    actualizado = incrementar_cantidad_item(coincidencia[1]["id"], datos["cantidad"], origen="manual")
                    messagebox.showinfo("Actualizado", f'Se aumentó "{actualizado.get("nombre", "")}" a {actualizado.get("cantidad", "")}.', parent=self.top)
                else:
                    agregar_item(**datos)
                    messagebox.showinfo("Guardado", f'Se agregó "{datos["nombre"]}".', parent=self.top)
            self._limpiar_dialogo_insumo()
            self._ocultar_dialogo_insumo()
            self._refrescar_todo()
            if self.on_change:
                self.on_change()
        except ValueError as e:
            messagebox.showwarning("Revisa los datos", str(e), parent=self.top)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.top)

    def _escanear_codigo_barras_medicamento(self):
        categoria = self._categoria_data_actual()
        if not categoria:
            messagebox.showwarning("Categoría no disponible", "No se encontró la categoría actual.", parent=self.top)
            return
        resultado = capturar_codigo_barras_inventario()
        estado = resultado.get("estado", "")
        if estado == "cancelado":
            return
        if estado == "error":
            messagebox.showwarning("Escáner", resultado.get("mensaje", "No se pudo usar la cámara."), parent=self.top)
            return
        codigo = str(resultado.get("codigo_barras", "")).strip()
        if not codigo:
            messagebox.showwarning("Escáner", "No se detectó un código de barras válido.", parent=self.top)
            return
        self.codigo_barras_actual = codigo
        self.lbl_codigo_medicamento.config(text=codigo)
        existente = buscar_item_por_codigo_barras(categoria["id"], codigo)
        if existente and existente.get("id") != self.item_editando_id:
            try:
                cantidad_extra = float((self.entry_med_cantidad.get().strip() or "1").replace(",", "."))
                actualizado = incrementar_cantidad_item(existente["id"], cantidad_extra, origen="codigo_barras")
                messagebox.showinfo("Item agregado", f'Se detectó "{actualizado.get("nombre", "")}" y se aumentó su cantidad a {actualizado.get("cantidad", "")}.', parent=self.top)
                self._limpiar_dialogo_medicamento()
                self._ocultar_dialogo_medicamento()
                self._refrescar_todo()
                if self.on_change:
                    self.on_change()
            except ValueError as error:
                messagebox.showwarning("Inventario", str(error), parent=self.top)

    def _capturar_foto_medicamento(self):
        resultado = capturar_foto_inventario()
        estado = resultado.get("estado", "")
        if estado == "cancelado":
            return
        if estado == "error":
            messagebox.showwarning("Foto", resultado.get("mensaje", "No se pudo usar la cámara."), parent=self.top)
            return
        ruta = resultado.get("ruta_foto", "") or ""
        if not ruta:
            messagebox.showwarning("Foto", "No se generó una ruta de foto válida.", parent=self.top)
            return
        texto = extraer_texto_ocr(ruta)
        analisis = analizar_texto_nutrimental(texto)
        nombre = analisis.get("nombre_sugerido") or analisis.get("nombre") or ""
        formula = analisis.get("peso_sugerido", "")
        cad = analisis.get("caducidad_sugerida", "")
        if nombre:
            self.entry_med_nombre.delete(0, "end")
            self.entry_med_nombre.insert(0, nombre)
        if formula:
            self.entry_med_formula.delete(0, "end")
            self.entry_med_formula.insert(0, formula)
        if cad:
            self.entry_med_caducidad.delete(0, "end")
            self.entry_med_caducidad.insert(0, cad)
        if texto:
            self.txt_med_descripcion.delete("1.0", "end")
            self.txt_med_descripcion.insert("1.0", f"OCR capturado:\n{texto[:1500]}")

    def _escanear_codigo_barras_insumo(self):
        categoria = self._categoria_data_actual()
        if not categoria:
            messagebox.showwarning("Categoría no disponible", "No se encontró la categoría actual.", parent=self.top)
            return
        resultado = capturar_codigo_barras_inventario()
        estado = resultado.get("estado", "")
        if estado == "cancelado":
            return
        if estado == "error":
            messagebox.showwarning("Escáner", resultado.get("mensaje", "No se pudo usar la cámara."), parent=self.top)
            return
        codigo = str(resultado.get("codigo_barras", "")).strip()
        if not codigo:
            messagebox.showwarning("Escáner", "No se detectó un código de barras válido.", parent=self.top)
            return
        self.codigo_barras_actual = codigo
        self.lbl_codigo_insumo.config(text=codigo)
        existente = buscar_item_por_codigo_barras(categoria["id"], codigo)
        if existente and existente.get("id") != self.item_editando_id:
            try:
                cantidad_extra = float((self.entry_ins_cantidad.get().strip() or "1").replace(",", "."))
                actualizado = incrementar_cantidad_item(existente["id"], cantidad_extra, origen="codigo_barras")
                messagebox.showinfo("Item agregado", f'Se detectó "{actualizado.get("nombre", "")}" y se aumentó su cantidad a {actualizado.get("cantidad", "")}.', parent=self.top)
                self._limpiar_dialogo_insumo()
                self._ocultar_dialogo_insumo()
                self._refrescar_todo()
                if self.on_change:
                    self.on_change()
            except ValueError as error:
                messagebox.showwarning("Inventario", str(error), parent=self.top)

    def _capturar_foto_insumo(self):
        resultado = capturar_foto_inventario()
        estado = resultado.get("estado", "")
        if estado == "cancelado":
            return
        if estado == "error":
            messagebox.showwarning("Foto", resultado.get("mensaje", "No se pudo usar la cámara."), parent=self.top)
            return
        ruta = resultado.get("ruta_foto", "") or ""
        if not ruta:
            messagebox.showwarning("Foto", "No se generó una ruta de foto válida.", parent=self.top)
            return
        texto = extraer_texto_ocr(ruta)
        analisis = analizar_texto_nutrimental(texto)
        nombre = analisis.get("nombre_sugerido") or analisis.get("nombre") or ""
        cad = analisis.get("caducidad_sugerida", "")
        if nombre:
            self.entry_ins_tipo.delete(0, "end")
            self.entry_ins_tipo.insert(0, nombre)
        if cad:
            self.entry_ins_caducidad.delete(0, "end")
            self.entry_ins_caducidad.insert(0, cad)
        if texto:
            self.txt_ins_descripcion.delete("1.0", "end")
            self.txt_ins_descripcion.insert("1.0", f"OCR capturado:\n{texto[:1500]}")

    def _crear_panel_formulario(self):
        _, _, frm = crear_contenedor_scrollable(self.panel_form, bg=self.bg_panel)

        titulo_registro = "Agregar medicamento" if self._es_formulario_medicamento() else "Registro"
        self.dialogo_item.title(f"{self.perfil['titulo']} - {titulo_registro}")
        tk.Label(frm, text=titulo_registro, font=("Arial", 18, "bold"), bg=self.bg_panel, fg=self.fg).pack(anchor="w", padx=16, pady=(16, 14))

        cont = tk.Frame(frm, bg=self.bg_panel)
        cont.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        campo_cfg = {"font": ("Arial", 12), "bg": "#07102a", "fg": "white", "insertbackground": "white", "relief": "flat"}
        self.combo_tipo = ttk.Combobox(cont, font=("Arial", 11), state="normal")
        self.entry_nombre = tk.Entry(cont, **campo_cfg)
        self.entry_cantidad = tk.Entry(cont, **campo_cfg)
        self.combo_unidad = ttk.Combobox(cont, font=("Arial", 11), state="normal")
        self.entry_minimo = tk.Entry(cont, **campo_cfg)
        self.entry_peso = tk.Entry(cont, **campo_cfg)
        self.entry_caducidad = tk.Entry(cont, **campo_cfg)
        self.entry_lote = tk.Entry(cont, **campo_cfg)

        self.lbl_tipo = tk.Label(cont, text=self.perfil["tipo_label"], font=("Arial", 11), bg=self.bg_panel, fg=self.fg)
        self.lbl_nombre = tk.Label(cont, text=self.perfil["nombre_label"], font=("Arial", 11), bg=self.bg_panel, fg=self.fg)
        self.lbl_peso = tk.Label(cont, text=self.perfil["peso_label"], bg=self.bg_panel, fg=self.fg, font=("Arial", 11))
        self.lbl_caducidad = tk.Label(cont, text=self.perfil["caducidad_label"], bg=self.bg_panel, fg=self.fg, font=("Arial", 11))
        self.lbl_lote = tk.Label(cont, text=self.perfil["lote_label"], bg=self.bg_panel, fg=self.fg, font=("Arial", 11))
        self.campo_caducidad_container = None
        self.campo_lote_container = None
        if self._permite_consumo_por_unidades():
            self._crear_panel_formulario_alimentos(cont)
        elif self._es_categoria_combate() or self._es_categoria_herramientas():
            self._crear_panel_formulario_combate(cont)
        elif self._es_categoria_animales():
            self._crear_panel_formulario_animales(cont)
        elif self._es_categoria_comunicacion():
            self._crear_panel_formulario_comunicacion(cont)
        elif self._es_categoria_energia():
            self._crear_panel_formulario_energia(cont)
        elif self._es_categoria_higiene():
            self._crear_panel_formulario_higiene(cont)
        elif self._es_categoria_movilidad():
            self._crear_panel_formulario_movilidad(cont)
        elif self._es_categoria_cocina_preparacion():
            self._crear_panel_formulario_cocina_preparacion(cont)
        elif self._es_categoria_ropa():
            self._crear_panel_formulario_ropa(cont)
        elif self._es_categoria_plantas():
            self._crear_panel_formulario_plantas(cont)
        elif self._usa_campos_personalizados():
            self._crear_panel_formulario_personalizado(cont)
        elif self._es_formulario_medicamento():
            self._crear_panel_formulario_medicamento(cont)
        elif self._es_categoria_insumos_medicos():
            self._crear_panel_formulario_insumo_medico(cont)
        else:
            self._crear_panel_formulario_general(cont)

        self._aplicar_perfil_visual()

    def _crear_panel_codigo(self, cont, incluir_boton_foto=False):
        self.frame_codigo = tk.Frame(cont, bg=self.bg_panel)
        self.frame_codigo.pack(fill="x", pady=(0, 10))
        tk.Button(
            self.frame_codigo,
            text="Escanear código",
            font=("Arial", 10, "bold"),
            bg=self.acento,
            fg="white",
            activebackground="#2454ad",
            activeforeground="white",
            relief="flat",
            command=self._escanear_codigo_barras,
        ).pack(side="left")
        if incluir_boton_foto:
            tk.Button(
                self.frame_codigo,
                text="Tomar foto",
                font=("Arial", 10, "bold"),
                bg="#0f766e",
                fg="white",
                activebackground="#0b5f5a",
                activeforeground="white",
                relief="flat",
                command=self._capturar_foto_registro,
            ).pack(side="left", padx=(8, 0))
        self.lbl_codigo = tk.Label(
            self.frame_codigo,
            text="Sin código registrado",
            bg=self.bg_panel,
            fg="#c8d2e6",
            font=("Arial", 10),
            anchor="w",
            justify="left",
        )
        self.lbl_codigo.pack(side="left", padx=10)
        self.lbl_foto = tk.Label(
            self.frame_codigo,
            text="Sin foto asociada",
            bg=self.bg_panel,
            fg="#c8d2e6",
            font=("Arial", 10),
            wraplength=240,
            justify="left",
            anchor="w",
        )
        self.lbl_foto.pack(side="left", padx=(10, 0))

    def _crear_panel_formulario_alimentos(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(5):
            grilla.grid_columnconfigure(col, weight=1)
        self.entry_alimento = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_nombre = self.entry_alimento
        self.entry_cantidad = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.combo_unidad = ttk.Combobox(
            grilla,
            font=("Arial", 11),
            state="readonly",
            style="InventarioDark.TCombobox",
            values=["Piezas", "Bolsas", "Cajas", "Botellas", "Latas", "Paquetes"],
        )
        self.frame_contenido = tk.Frame(grilla, bg="#07102a", bd=0, highlightthickness=0)
        self.entry_peso = tk.Entry(
            self.frame_contenido,
            font=("Arial", 12),
            bg="#07102a",
            fg="white",
            insertbackground="white",
            relief="flat",
            bd=0,
        )
        self.entry_peso.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=6)
        self.combo_peso_unidad = ttk.Combobox(
            self.frame_contenido,
            font=("Arial", 11),
            state="readonly",
            style="InventarioDark.TCombobox",
            values=["mg", "gr", "kg", "ml", "l"],
            width=7,
        )
        self.combo_peso_unidad.pack(side="right", padx=(0, 6), pady=4)
        self.combo_peso_unidad.set("gr")
        self.entry_minimo = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        encabezados = ["Alimento", "Cantidad", "Unidad", "Contenido", "Mínimo"]
        if self._permite_consumo_por_unidades():
            encabezados = ["Alimento", "Cantidad de unidades", "Unidad", "Contenido por unidad", "Stock mínimo"]
        for idx, titulo in enumerate(encabezados):
            padx = (0, 8) if idx < 4 else (0, 0)
            tk.Label(
                grilla,
                text=titulo,
                font=("Arial", 10, "bold"),
                bg=self.bg_panel,
                fg=self.fg,
                wraplength=135,
                justify="center",
            ).grid(
                row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4)
            )

        widgets = [self.entry_alimento, self.entry_cantidad, self.combo_unidad, self.frame_contenido, self.entry_minimo]
        for idx, widget in enumerate(widgets):
            padx = (0, 8) if idx < 4 else (0, 0)
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fechas = tk.Frame(cont, bg=self.bg_panel)
        fechas.pack(anchor="w", pady=(0, 8))
        for col in range(3):
            fechas.grid_columnconfigure(col, weight=0)
        self.entry_fecha_ingreso = tk.Entry(fechas, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_fecha_produccion_compra = tk.Entry(fechas, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_caducidad = tk.Entry(fechas, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        for idx, (titulo, widget) in enumerate(
            [
                ("Ingreso", self.entry_fecha_ingreso),
                ("Producción / compra", self.entry_fecha_produccion_compra),
                ("Caducidad", self.entry_caducidad),
            ]
        ):
            padx = (0, 8) if idx < 2 else (0, 0)
            tk.Label(
                fechas,
                text=titulo,
                font=("Arial", 10, "bold"),
                bg=self.bg_panel,
                fg=self.fg,
                wraplength=140,
                justify="center",
                width=18,
            ).grid(row=0, column=idx, sticky="w", padx=padx, pady=(0, 4))
            widget.configure(width=18)
            widget.grid(row=1, column=idx, sticky="w", padx=padx, pady=(0, 12))

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.frame_nutrimental.pack(fill="x")
        self._crear_panel_codigo(cont, incluir_boton_foto=True)
        nutr_frame = tk.Frame(self.frame_nutrimental, bg=self.bg_panel)
        nutr_frame.pack(fill="x")
        for col in range(6):
            nutr_frame.grid_columnconfigure(col, weight=1)
        for idx, (texto, clave) in enumerate(
            [("Porción", "porcion"), ("Calorías", "calorias"), ("Proteínas", "proteinas"), ("Carbohidratos", "carbohidratos"), ("Grasas", "grasas"), ("Fibra", "fibra")]
        ):
            padx = (0, 8) if idx < 5 else (0, 0)
            tk.Label(nutr_frame, text=texto, bg=self.bg_panel, fg=self.fg, font=("Arial", 10)).grid(
                row=0, column=idx, sticky="w", padx=padx, pady=(0, 4)
            )
            entrada = tk.Entry(
                nutr_frame,
                textvariable=self.nutr_vars[clave],
                font=("Arial", 11),
                bg="#07102a",
                fg="white",
                insertbackground="white",
                relief="flat",
            )
            entrada.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))
            self._configurar_validacion_numerica(entrada)

        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(4, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)
        self._configurar_validacion_numerica(self.entry_cantidad)
        self._configurar_validacion_numerica(self.entry_peso)
        self._configurar_validacion_numerica(self.entry_minimo)
        self._configurar_navegacion_flechas_alimentos()

    def _crear_panel_formulario_general(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(3):
            grilla.grid_columnconfigure(col, weight=1)

        def campo_grid(row, col, titulo, widget, padx=(0, 8)):
            marco = tk.Frame(grilla, bg=self.bg_panel)
            marco.grid(row=row, column=col, sticky="ew", padx=padx, pady=(0, 10))
            tk.Label(marco, text=titulo, font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(0, 4))
            widget.pack(fill="x")
            return marco

        campo_grid(0, 0, self.perfil["tipo_label"], self.combo_tipo)
        campo_grid(0, 1, self.perfil["nombre_label"], self.entry_nombre, padx=(4, 4))
        campo_grid(0, 2, "Cantidad", self.entry_cantidad, padx=(8, 0))
        campo_grid(1, 0, "Unidad", self.combo_unidad)
        campo_grid(1, 1, "Mínimo", self.entry_minimo, padx=(4, 4))
        campo_grid(1, 2, self.perfil["peso_label"], self.entry_peso, padx=(8, 0))
        self.campo_caducidad_container = campo_grid(2, 0, self.perfil["caducidad_label"], self.entry_caducidad)
        self.campo_lote_container = campo_grid(2, 1, self.perfil["lote_label"], self.entry_lote, padx=(4, 4))

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        tk.Label(self.frame_nutrimental, text="Tabla nutrimental", font=("Arial", 11, "bold"), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(10, 4))
        nutr_frame = tk.Frame(self.frame_nutrimental, bg=self.bg_panel)
        nutr_frame.pack(fill="x")
        for idx, (texto, clave) in enumerate([("Porción", "porcion"), ("Calorías", "calorias"), ("Proteínas", "proteinas"), ("Carbohidratos", "carbohidratos"), ("Grasas", "grasas"), ("Fibra", "fibra")]):
            frame = tk.Frame(nutr_frame, bg=self.bg_panel)
            frame.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=4, pady=4)
            tk.Label(frame, text=texto, bg=self.bg_panel, fg=self.fg, font=("Arial", 10)).pack(anchor="w")
            tk.Entry(frame, textvariable=self.nutr_vars[clave], font=("Arial", 11), bg="#07102a", fg="white", insertbackground="white", relief="flat").pack(fill="x")
        tk.Label(self.frame_nutrimental, text="Resumen nutrimental libre", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(10, 4))
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=6, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_nutrimentales.pack(fill="x")

        self._crear_panel_codigo(cont)

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)
        menu_foto = tk.Menu(self.frame_foto, tearoff=0)
        menu_foto.add_command(label="Usar cámara", command=self._agregar_por_foto)
        menu_foto.add_command(label="Leer imagen local", command=self._cargar_imagen_local)
        btn_foto = tk.Menubutton(
            self.frame_foto,
            text="Foto",
            font=("Arial", 11),
            bg=self.acento,
            fg="white",
            activebackground="#2454ad",
            activeforeground="white",
            relief="flat",
            menu=menu_foto,
        )
        btn_foto.pack(side="left")
        btn_foto["menu"] = menu_foto
        self.lbl_foto = tk.Label(self.frame_foto, text="Sin foto asociada", bg=self.bg_panel, fg="#c8d2e6", font=("Arial", 10), wraplength=240, justify="left")
        self.lbl_foto.pack(side="left", padx=8)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(10, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

    def _crear_panel_formulario_combate(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(5):
            grilla.grid_columnconfigure(col, weight=1)

        self.frame_tipo_combate = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_combate.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_combate, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.configure(justify="center")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_combate = tk.Button(
            self.frame_tipo_combate,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            activebackground="#2454ad",
            activeforeground="white",
            relief="flat",
            width=3,
            command=self._agregar_tipo_combate,
        )
        self.btn_agregar_tipo_combate.grid(row=0, column=1, padx=(6, 0))
        self.entry_nombre = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_minimo = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_lote = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_combate),
                ("Modelo" if self._es_categoria_herramientas() else "Modelo / calibre", self.entry_nombre),
                ("Cantidad", self.entry_cantidad),
                ("Mínimo", self.entry_minimo),
                ("Serie / lote", self.entry_lote),
            ]
        ):
            padx = (0, 8) if idx < 4 else (0, 0)
            tk.Label(
                grilla,
                text=titulo,
                font=("Arial", 10, "bold"),
                bg=self.bg_panel,
                fg=self.fg,
                wraplength=135,
                justify="center",
            ).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fechas = tk.Frame(cont, bg=self.bg_panel)
        fechas.pack(anchor="w", pady=(0, 8))
        for col in range(3):
            fechas.grid_columnconfigure(col, weight=0)
        self.entry_fecha_ingreso = tk.Entry(fechas, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_fecha_produccion_compra = tk.Entry(fechas, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_caducidad = tk.Entry(fechas, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        for idx, (titulo, widget) in enumerate(
            [
                ("Ingreso", self.entry_fecha_ingreso),
                ("Compra", self.entry_fecha_produccion_compra),
                ("Caducidad", self.entry_caducidad),
            ]
        ):
            padx = (0, 8) if idx < 2 else (0, 0)
            tk.Label(
                fechas,
                text=titulo,
                font=("Arial", 10, "bold"),
                bg=self.bg_panel,
                fg=self.fg,
                wraplength=140,
                justify="center",
                width=18,
            ).grid(row=0, column=idx, sticky="w", padx=padx, pady=(0, 4))
            widget.configure(width=18)
            widget.grid(row=1, column=idx, sticky="w", padx=padx, pady=(0, 12))

        self._crear_panel_codigo(cont)

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)
        self.txt_obs = tk.Text(cont, height=1, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_minimo)

    def _crear_panel_formulario_animales(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(3):
            grilla.grid_columnconfigure(col, weight=1, uniform="animales_form")

        self.frame_tipo_animales = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_animales.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_animales, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_animales = tk.Button(
            self.frame_tipo_animales,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            padx=10,
            pady=4,
            activebackground=self.acento,
            activeforeground="white",
            cursor="hand2",
            command=self._agregar_tipo_animales,
        )
        self.btn_agregar_tipo_animales.grid(row=0, column=1, padx=(6, 0))
        self.entry_nombre = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_uso_animal = ttk.Combobox(grilla, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox", values=USOS_ANIMAL_PREDETERMINADOS)
        self.frame_cantidad_animales = tk.Frame(grilla, bg="#07102a", bd=0, highlightthickness=0)
        self.entry_cantidad = tk.Entry(self.frame_cantidad_animales, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat", bd=0)
        self.entry_cantidad.pack(fill="both", expand=True, padx=8, pady=6)
        self.entry_cantidad.insert(0, "1")
        self.frame_alimento = tk.Frame(grilla, bg="#07102a", bd=0, highlightthickness=0)
        self.entry_alimento_diario = tk.Entry(self.frame_alimento, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat", bd=0)
        self.entry_alimento_diario.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=6)
        self.combo_alimento_unidad = ttk.Combobox(
            self.frame_alimento,
            font=("Arial", 11),
            state="readonly",
            style="InventarioDark.TCombobox",
            values=["kg", "gr"],
            width=6,
        )
        self.combo_alimento_unidad.pack(side="right", padx=(0, 6), pady=4)
        self.combo_alimento_unidad.set("kg")
        self.frame_agua = tk.Frame(grilla, bg="#07102a", bd=0, highlightthickness=0)
        self.entry_agua_diaria = tk.Entry(self.frame_agua, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat", bd=0)
        self.entry_agua_diaria.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=6)
        self.combo_agua_unidad = ttk.Combobox(
            self.frame_agua,
            font=("Arial", 11),
            state="readonly",
            style="InventarioDark.TCombobox",
            values=["lt", "ml"],
            width=6,
        )
        self.combo_agua_unidad.pack(side="right", padx=(0, 6), pady=4)
        self.combo_agua_unidad.set("lt")

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_animales),
                ("Raza", self.entry_nombre),
                ("Uso", self.entry_uso_animal),
            ]
        ):
            padx = (0, 8) if idx < 2 else (0, 0)
            tk.Label(
                grilla,
                text=titulo,
                font=("Arial", 10, "bold"),
                bg=self.bg_panel,
                fg=self.fg,
                wraplength=135,
                justify="center",
            ).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        for idx, (titulo, widget) in enumerate(
            [
                ("Cantidad", self.frame_cantidad_animales),
                ("alimento/dia", self.frame_alimento),
                ("agua/dia", self.frame_agua),
            ]
        ):
            padx = (0, 8) if idx < 2 else (0, 0)
            tk.Label(
                grilla,
                text=titulo,
                font=("Arial", 10, "bold"),
                bg=self.bg_panel,
                fg=self.fg,
                wraplength=135,
                justify="center",
            ).grid(row=2, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=3, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fila_descripcion = tk.Frame(cont, bg=self.bg_panel)
        fila_descripcion.pack(fill="x", pady=(0, 8))
        fila_descripcion.grid_columnconfigure(0, weight=1)
        self.txt_obs = tk.Text(fila_descripcion, height=4, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        tk.Label(
            fila_descripcion,
            text="Descripcion",
            font=("Arial", 10, "bold"),
            bg=self.bg_panel,
            fg=self.fg,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.txt_obs.grid(row=1, column=0, sticky="ew")

        self._crear_panel_codigo(cont)

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_alimento_diario)
        self._configurar_validacion_numerica(self.entry_agua_diaria)

    def _crear_panel_formulario_plantas(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(5):
            grilla.grid_columnconfigure(col, weight=1)

        self.frame_tipo_plantas = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_plantas.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_plantas, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.configure(justify="center")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_plantas = tk.Button(
            self.frame_tipo_plantas,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            activebackground="#2454ad",
            activeforeground="white",
            relief="flat",
            width=3,
            command=self._agregar_tipo_combate,
        )
        self.btn_agregar_tipo_plantas.grid(row=0, column=1, padx=(6, 0))
        self.entry_nombre = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_riego = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.combo_clima = ttk.Combobox(grilla, font=("Arial", 11), state="readonly", style="InventarioDark.TCombobox", values=["Frio", "Templado", "Calido", "Mixto"])
        self.combo_clima.set("Templado")

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_plantas),
                ("Variedad", self.entry_nombre),
                ("Redundancia", self.entry_cantidad),
                ("Riego", self.entry_riego),
                ("Clima", self.combo_clima),
            ]
        ):
            padx = (0, 8) if idx < 4 else (0, 0)
            tk.Label(
                grilla,
                text=titulo,
                font=("Arial", 10, "bold"),
                bg=self.bg_panel,
                fg=self.fg,
                wraplength=135,
                justify="center",
            ).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        self._crear_panel_codigo(cont)

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(8, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

    def _crear_panel_formulario_higiene(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(4):
            grilla.grid_columnconfigure(col, weight=1)

        self.frame_tipo_higiene = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_higiene.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_higiene, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_higiene = tk.Button(
            self.frame_tipo_higiene,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.combo_tipo, "subcategorias", "Nuevo tipo de higiene", "Escribe el tipo de artículo de higiene para agregar a la lista."),
        )
        self.btn_agregar_tipo_higiene.grid(row=0, column=1, padx=(6, 0))
        self.entry_nombre = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.combo_unidad = ttk.Combobox(grilla, font=("Arial", 11), state="readonly", style="InventarioDark.TCombobox", values=["pieza", "pzas", "paquete", "caja", "botella", "rollo", "kit"])
        self.combo_unidad.set("pieza")

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_higiene),
                ("Artículo", self.entry_nombre),
                ("Cantidad", self.entry_cantidad),
                ("Unidad", self.combo_unidad),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(grilla, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fila_secundaria = tk.Frame(cont, bg=self.bg_panel)
        fila_secundaria.pack(fill="x", pady=(0, 8))
        for col in range(4):
            fila_secundaria.grid_columnconfigure(col, weight=1)

        self.entry_peso = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_minimo = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_caducidad = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_lote = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        for idx, (titulo, widget) in enumerate(
            [
                ("Presentación / contenido", self.entry_peso),
                ("Mínimo", self.entry_minimo),
                ("Caducidad", self.entry_caducidad),
                ("Lote / marca", self.entry_lote),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(fila_secundaria, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        self._crear_panel_codigo(cont)
        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(8, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_cantidad)
        self._configurar_validacion_numerica(self.entry_minimo)

    def _crear_panel_formulario_movilidad(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(4):
            grilla.grid_columnconfigure(col, weight=1)

        self.frame_tipo_movilidad = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_movilidad.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_movilidad, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_movilidad = tk.Button(
            self.frame_tipo_movilidad,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.combo_tipo, "subcategorias", "Nuevo tipo de movilidad", "Escribe el tipo de recurso de movilidad para agregar a la lista."),
        )
        self.btn_agregar_tipo_movilidad.grid(row=0, column=1, padx=(6, 0))
        self.entry_nombre = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_peso = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_movilidad),
                ("Recurso / modelo", self.entry_nombre),
                ("Cantidad", self.entry_cantidad),
                ("Capacidad / carga", self.entry_peso),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(grilla, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fila_secundaria = tk.Frame(cont, bg=self.bg_panel)
        fila_secundaria.pack(fill="x", pady=(0, 8))
        for col in range(3):
            fila_secundaria.grid_columnconfigure(col, weight=1)

        self.entry_autonomia_movilidad = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_uso_movilidad = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_lote = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        for idx, (titulo, widget) in enumerate(
            [
                ("Combustible / autonomía", self.entry_autonomia_movilidad),
                ("Uso / asignación", self.entry_uso_movilidad),
                ("Serie / placas", self.entry_lote),
            ]
        ):
            padx = (0, 8) if idx < 2 else (0, 0)
            tk.Label(fila_secundaria, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        self._crear_panel_codigo(cont)
        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(8, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_cantidad)

    def _crear_panel_formulario_cocina_preparacion(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(4):
            grilla.grid_columnconfigure(col, weight=1)

        self.frame_tipo_cocina = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_cocina.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_cocina, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_cocina = tk.Button(
            self.frame_tipo_cocina,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.combo_tipo, "subcategorias", "Nuevo tipo de cocina", "Escribe el tipo de equipo o insumo para agregar a la lista."),
        )
        self.btn_agregar_tipo_cocina.grid(row=0, column=1, padx=(6, 0))
        self.entry_nombre = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.combo_unidad = ttk.Combobox(grilla, font=("Arial", 11), state="readonly", style="InventarioDark.TCombobox", values=["pieza", "pzas", "kit", "caja", "cartucho", "tanque"])
        self.combo_unidad.set("pieza")

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_cocina),
                ("Equipo / insumo", self.entry_nombre),
                ("Cantidad", self.entry_cantidad),
                ("Unidad", self.combo_unidad),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(grilla, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fila_secundaria = tk.Frame(cont, bg=self.bg_panel)
        fila_secundaria.pack(fill="x", pady=(0, 8))
        for col in range(4):
            fila_secundaria.grid_columnconfigure(col, weight=1)

        self.entry_peso = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_combustible_cocina = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_minimo = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_lote = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        for idx, (titulo, widget) in enumerate(
            [
                ("Capacidad / potencia", self.entry_peso),
                ("Combustible / fuente", self.entry_combustible_cocina),
                ("Mínimo", self.entry_minimo),
                ("Lote / serie", self.entry_lote),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(fila_secundaria, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        self._crear_panel_codigo(cont)
        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(8, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_cantidad)
        self._configurar_validacion_numerica(self.entry_minimo)

    def _crear_panel_formulario_ropa(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(4):
            grilla.grid_columnconfigure(col, weight=1)

        self.frame_tipo_ropa = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_ropa.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_ropa, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_ropa = tk.Button(
            self.frame_tipo_ropa,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.combo_tipo, "subcategorias", "Nuevo tipo de ropa", "Escribe el tipo de ropa para agregar a la lista."),
        )
        self.btn_agregar_tipo_ropa.grid(row=0, column=1, padx=(6, 0))

        self.entry_nombre = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.combo_unidad = ttk.Combobox(grilla, font=("Arial", 11), state="readonly", style="InventarioDark.TCombobox", values=["pieza", "pzas", "par", "juego", "kit"])
        self.combo_unidad.set("pieza")

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_ropa),
                ("Prenda / modelo", self.entry_nombre),
                ("Cantidad", self.entry_cantidad),
                ("Unidad", self.combo_unidad),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(grilla, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fila_secundaria = tk.Frame(cont, bg=self.bg_panel)
        fila_secundaria.pack(fill="x", pady=(0, 8))
        for col in range(4):
            fila_secundaria.grid_columnconfigure(col, weight=1)

        self.frame_clima_ropa = tk.Frame(fila_secundaria, bg=self.bg_panel)
        self.frame_clima_ropa.grid_columnconfigure(0, weight=1)
        self.combo_clima_ropa = ttk.Combobox(
            self.frame_clima_ropa,
            font=("Arial", 11),
            state="normal",
            style="InventarioDark.TCombobox",
            values=CLIMAS_ROPA_PREDETERMINADOS,
        )
        self.combo_clima_ropa.grid(row=0, column=0, sticky="ew")
        self.combo_clima_ropa.set("Mixto")
        self.btn_agregar_clima_ropa = tk.Button(
            self.frame_clima_ropa,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.combo_clima_ropa, "climas_ropa", "Nuevo clima", "Escribe la opción de clima para agregar a la lista."),
        )
        self.btn_agregar_clima_ropa.grid(row=0, column=1, padx=(6, 0))
        self.entry_peso = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_minimo = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_lote = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        for idx, (titulo, widget) in enumerate(
            [
                ("Clima", self.frame_clima_ropa),
                ("Talla / detalle", self.entry_peso),
                ("Mínimo", self.entry_minimo),
                ("Lote / estado", self.entry_lote),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(fila_secundaria, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        self._crear_panel_codigo(cont)

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(8, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_cantidad)
        self._configurar_validacion_numerica(self.entry_minimo)

    def _crear_panel_formulario_comunicacion(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(3):
            grilla.grid_columnconfigure(col, weight=1)

        self.frame_tipo_comunicacion = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_comunicacion.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_comunicacion, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_comunicacion = tk.Button(
            self.frame_tipo_comunicacion,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.combo_tipo, "subcategorias", "Nuevo tipo", "Escribe el tipo para agregar a la lista."),
        )
        self.btn_agregar_tipo_comunicacion.grid(row=0, column=1, padx=(6, 0))

        self.frame_modelo_comunicacion = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_modelo_comunicacion.grid_columnconfigure(0, weight=1)
        self.entry_nombre = ttk.Combobox(self.frame_modelo_comunicacion, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.entry_nombre.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_modelo_comunicacion = tk.Button(
            self.frame_modelo_comunicacion,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.entry_nombre, "modelos", "Nuevo modelo", "Escribe el modelo para agregar a la lista."),
        )
        self.btn_agregar_modelo_comunicacion.grid(row=0, column=1, padx=(6, 0))

        self.frame_banda_comunicacion = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_banda_comunicacion.grid_columnconfigure(0, weight=1)
        self.entry_banda = ttk.Combobox(self.frame_banda_comunicacion, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.entry_banda.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_banda_comunicacion = tk.Button(
            self.frame_banda_comunicacion,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.entry_banda, "bandas", "Nueva banda", "Escribe la banda para agregar a la lista."),
        )
        self.btn_agregar_banda_comunicacion.grid(row=0, column=1, padx=(6, 0))
        self.entry_peso = self.entry_banda

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_comunicacion),
                ("Modelo", self.frame_modelo_comunicacion),
                ("Banda", self.frame_banda_comunicacion),
            ]
        ):
            padx = (0, 8) if idx < 2 else (0, 0)
            tk.Label(grilla, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fila_secundaria = tk.Frame(cont, bg=self.bg_panel)
        fila_secundaria.pack(fill="x", pady=(0, 8))
        for col in range(4):
            fila_secundaria.grid_columnconfigure(col, weight=1)

        self.entry_antenas = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_bateria_equipo = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_pantalla = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_lote = self.entry_pantalla

        for idx, (titulo, widget) in enumerate(
            [
                ("Antenas", self.entry_antenas),
                ("Bateria", self.entry_bateria_equipo),
                ("Pantalla", self.entry_pantalla),
                ("Cantidad", self.entry_cantidad),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(fila_secundaria, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        self._crear_panel_codigo(cont)
        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(8, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)
        self._configurar_validacion_numerica(self.entry_cantidad)

    def _crear_panel_formulario_energia(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        grilla = tk.Frame(cont, bg=self.bg_panel)
        grilla.pack(fill="x")
        for col in range(4):
            grilla.grid_columnconfigure(col, weight=1)

        self.frame_tipo_energia = tk.Frame(grilla, bg=self.bg_panel)
        self.frame_tipo_energia.grid_columnconfigure(0, weight=1)
        self.combo_tipo = ttk.Combobox(self.frame_tipo_energia, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.combo_tipo.grid(row=0, column=0, sticky="ew")
        self.btn_agregar_tipo_energia = tk.Button(
            self.frame_tipo_energia,
            text="+",
            font=("Arial", 11, "bold"),
            bg=self.acento,
            fg="white",
            relief="flat",
            width=3,
            command=lambda: self._agregar_valor_catalogo_combo(self.combo_tipo, "subcategorias", "Nuevo tipo", "Escribe el tipo para agregar a la lista."),
        )
        self.btn_agregar_tipo_energia.grid(row=0, column=1, padx=(6, 0))
        self.entry_nombre = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_capacidad = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_voltaje = tk.Entry(grilla, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_peso = self.entry_capacidad
        self.entry_lote = self.entry_voltaje

        for idx, (titulo, widget) in enumerate(
            [
                ("Tipo", self.frame_tipo_energia),
                ("Modelo", self.entry_nombre),
                ("Capacidad", self.entry_capacidad),
                ("Voltaje", self.entry_voltaje),
            ]
        ):
            padx = (0, 8) if idx < 3 else (0, 0)
            tk.Label(grilla, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        fila_secundaria = tk.Frame(cont, bg=self.bg_panel)
        fila_secundaria.pack(fill="x", pady=(0, 8))
        for col in range(3):
            fila_secundaria.grid_columnconfigure(col, weight=1)

        self.entry_entrada_energia = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_salida_energia = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(fila_secundaria, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        for idx, (titulo, widget) in enumerate(
            [
                ("Entrada", self.entry_entrada_energia),
                ("Salida", self.entry_salida_energia),
                ("Cantidad", self.entry_cantidad),
            ]
        ):
            padx = (0, 8) if idx < 2 else (0, 0)
            tk.Label(fila_secundaria, text=titulo, font=("Arial", 10, "bold"), bg=self.bg_panel, fg=self.fg).grid(row=0, column=idx, sticky="ew", padx=padx, pady=(0, 4))
            widget.grid(row=1, column=idx, sticky="ew", padx=padx, pady=(0, 12))

        self._crear_panel_codigo(cont)
        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)

        tk.Label(cont, text="Observaciones", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(8, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)
        self._configurar_validacion_numerica(self.entry_cantidad)

    def _crear_panel_formulario_personalizado(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        self.campos_extra_widgets = {}
        campos = self._campos_personalizados()
        barra_campos = tk.Frame(cont, bg=self.bg_panel)
        barra_campos.pack(fill="x", pady=(0, 10))
        tk.Button(
            barra_campos,
            text="Agregar celda",
            font=("Arial", 10, "bold"),
            bg=self.acento_ok,
            fg="white",
            activebackground="#11815e",
            activeforeground="white",
            relief="flat",
            command=self._agregar_celda_categoria_actual,
        ).pack(side="left")

        if campos:
            grilla = tk.Frame(cont, bg=self.bg_panel)
            grilla.pack(fill="x")
            columnas = min(3, max(1, len(campos)))
            for col in range(columnas):
                grilla.grid_columnconfigure(col, weight=1)

            for idx, campo in enumerate(campos):
                marco = tk.Frame(grilla, bg=self.bg_panel)
                marco.grid(row=(idx // columnas) * 2, column=idx % columnas, sticky="ew", padx=(0 if idx % columnas == 0 else 8, 8 if idx % columnas < columnas - 1 else 0), pady=(0, 10))
                tk.Label(
                    marco,
                    text=_formatear_encabezado_celda(campo.get("label", ""), max_linea=18),
                    font=("Arial", 10, "bold"),
                    bg=self.bg_panel,
                    fg=self.fg,
                    justify="center",
                ).pack(fill="x", pady=(0, 4))
                entrada = tk.Entry(marco, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
                entrada.pack(fill="x")
                self.campos_extra_widgets[campo["id"]] = entrada
            self.entry_nombre = next(iter(self.campos_extra_widgets.values()), None)
        else:
            self.entry_nombre = None
            tk.Label(
                cont,
                text="Esta categoría está vacía.\nUsa \"Agregar celda\" para crear el formulario antes de registrar items.",
                font=("Arial", 12),
                bg=self.bg_panel,
                fg="#c8d2e6",
                justify="left",
            ).pack(anchor="w", pady=(16, 6))

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)
        self.txt_obs = tk.Text(cont, height=1, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")

        if campos:
            botones = tk.Frame(cont, bg=self.bg_panel)
            botones.pack(fill="x", pady=(14, 0))
            tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
            tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

    def _crear_panel_formulario_insumo_medico(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        self.combo_tipo = ttk.Combobox(cont, font=("Arial", 11), state="normal", style="InventarioDark.TCombobox")
        self.entry_nombre = self._campo_stack(cont, "Nombre del insumo")
        self._campo_stack_widget(cont, "Tipo de insumo", self.combo_tipo)
        self.entry_cantidad = self._campo_stack(cont, "Cantidad")
        self.combo_unidad = ttk.Combobox(
            cont,
            font=("Arial", 11),
            state="normal",
            style="InventarioDark.TCombobox",
            values=["pieza", "pzas", "tableta", "capsula", "ampolleta", "frasco", "caja", "kit", "ml", "mg", "g"],
        )
        self._campo_stack_widget(cont, "Unidad", self.combo_unidad)
        self.entry_minimo = self._campo_stack(cont, "Stock mínimo")
        self.entry_peso = self._campo_stack(cont, "Presentación / concentración")
        self.entry_caducidad = self._campo_stack(cont, "Caducidad (YYYY-MM-DD)")
        self.entry_lote = self._campo_stack(cont, "Lote / serie")
        self.entry_indicaciones = self._campo_stack(cont, "Indicaciones / para qué sirve")

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")

        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)
        self.lbl_foto = tk.Label(self.frame_foto, text="Sin foto asociada", bg=self.bg_panel, fg="#c8d2e6", font=("Arial", 10), wraplength=240, justify="left")
        self.lbl_foto.pack(side="left")

        tk.Label(cont, text="Observaciones / para qué es", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(10, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_cantidad)
        self._configurar_validacion_numerica(self.entry_minimo)
        if not self.combo_unidad.get().strip():
            self.combo_unidad.set("pieza")

    def _crear_panel_formulario_medicamento(self, cont):
        self.nutr_vars = {k: tk.StringVar() for k in ("porcion", "calorias", "proteinas", "carbohidratos", "grasas", "fibra")}
        tk.Label(cont, text="Agregar medicamento", font=("Arial", 18, "bold"), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(0, 14))

        fila_1 = tk.Frame(cont, bg=self.bg_panel)
        fila_1.pack(fill="x", pady=(0, 10))
        for col in range(3):
            fila_1.grid_columnconfigure(col, weight=1, uniform="med_form")

        self.entry_nombre = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_peso = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_cantidad = tk.Entry(fila_1, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self._crear_campo_grid_medicamento(fila_1, 0, "Nombre", self.entry_nombre)
        self._crear_campo_grid_medicamento(fila_1, 1, "Formula", self.entry_peso, padx=(4, 4))
        self._crear_campo_grid_medicamento(fila_1, 2, "Cantidad", self.entry_cantidad, padx=(8, 0))

        fila_2 = tk.Frame(cont, bg=self.bg_panel)
        fila_2.pack(fill="x", pady=(0, 10))
        for col in range(3):
            fila_2.grid_columnconfigure(col, weight=1, uniform="med_form")

        self.combo_unidad = ttk.Combobox(
            fila_2,
            font=("Arial", 11),
            state="readonly",
            style="InventarioDark.TCombobox",
            values=["Mililitros", "Miligramos", "Gramos"],
        )
        self.entry_caducidad = tk.Entry(fila_2, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_minimo = tk.Entry(fila_2, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self._crear_campo_grid_medicamento(fila_2, 0, "Unidad", self.combo_unidad)
        self._crear_campo_grid_medicamento(fila_2, 1, "Caducidad", self.entry_caducidad, padx=(4, 4))
        self._crear_campo_grid_medicamento(fila_2, 2, "Stock", self.entry_minimo, padx=(8, 0))
        self.combo_unidad.set("Miligramos")

        self.entry_lote = tk.Entry(cont, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.entry_indicaciones = tk.Entry(cont, font=("Arial", 12), bg="#07102a", fg="white", insertbackground="white", relief="flat")

        self.frame_nutrimental = tk.Frame(cont, bg=self.bg_panel)
        self.txt_nutrimentales = tk.Text(self.frame_nutrimental, height=1, font=("Courier New", 10), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.frame_foto = tk.Frame(cont, bg=self.bg_panel)
        self.lbl_foto = tk.Label(self.frame_foto, text="Sin foto asociada", bg=self.bg_panel, fg="#c8d2e6", font=("Arial", 10), wraplength=240, justify="left")
        self.lbl_foto.pack(side="left")

        tk.Label(cont, text="Descripcion", font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(10, 4))
        self.txt_obs = tk.Text(cont, height=6, font=("Arial", 11), wrap="word", bg="#07102a", fg="white", insertbackground="white", relief="flat")
        self.txt_obs.pack(fill="x")

        botones = tk.Frame(cont, bg=self.bg_panel)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Guardar", font=("Arial", 11, "bold"), bg=self.acento_ok, fg="white", command=self._guardar_producto).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(botones, text="Limpiar", font=("Arial", 11), bg="#6b7280", fg="white", command=self._limpiar_formulario).pack(side="left", fill="x", expand=True, padx=4)

        self._configurar_validacion_numerica(self.entry_cantidad)
        self._configurar_validacion_numerica(self.entry_minimo)

    def _crear_campo_grid_medicamento(self, parent, col, titulo, widget, padx=(0, 8)):
        tk.Label(parent, text=titulo, font=("Arial", 10), bg=self.bg_panel, fg="white").grid(row=0, column=col, sticky="w", padx=padx, pady=(0, 4))
        widget.grid(row=1, column=col, sticky="ew", padx=padx)

    def _campo_stack_widget(self, parent, titulo, widget):
        marco = tk.Frame(parent, bg=self.bg_panel)
        marco.pack(fill="x", pady=(0, 10))
        tk.Label(marco, text=titulo, font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(0, 4))
        widget.pack(in_=marco, fill="x")
        return widget

    def _campo_stack(self, parent, titulo, font_size=12):
        marco = tk.Frame(parent, bg=self.bg_panel)
        marco.pack(fill="x", pady=(0, 10))
        tk.Label(marco, text=titulo, font=("Arial", 11), bg=self.bg_panel, fg=self.fg).pack(anchor="w", pady=(0, 4))
        entry = tk.Entry(marco, font=("Arial", font_size), bg="#07102a", fg="white", insertbackground="white", relief="flat")
        entry.pack(fill="x")
        return entry

    def _aplicar_perfil_visual(self):
        if self.perfil["mostrar_nutrimental"]:
            self.frame_nutrimental.pack(fill="x")
        else:
            self.frame_nutrimental.pack_forget()

        if hasattr(self, "frame_codigo"):
            self.frame_codigo.pack(fill="x", pady=(0, 10))

        if self._permite_consumo_por_unidades():
            self.frame_foto.pack_forget()
        elif self.perfil["mostrar_foto"]:
            self.frame_foto.pack(fill="x", pady=(8, 0))
        else:
            self.frame_foto.pack_forget()

        if not self.perfil["mostrar_caducidad"] and self.campo_caducidad_container is not None:
            self.campo_caducidad_container.grid_remove()
        if not self.perfil["mostrar_lote"] and self.campo_lote_container is not None:
            self.campo_lote_container.grid_remove()

    def _cargar_opciones_categoria(self):
        categoria = next((x for x in listar_categorias_data() if x["nombre"] == self.categoria_actual), None)
        if not categoria:
            return
        self.firma_campos_actual = self._firma_campos_desde_categoria(categoria)
        subcategorias = listar_subcategorias(categoria["id"])
        unidades = listar_unidades(categoria["id"])
        if isinstance(self.combo_tipo, ttk.Combobox):
            opciones_tipo = self._opciones_subcategorias_editables()
            self.combo_tipo["values"] = opciones_tipo
            if opciones_tipo and not self.combo_tipo.get().strip() and not self._permite_consumo_por_unidades():
                self.combo_tipo.set(opciones_tipo[0])
        if self._es_categoria_comunicacion():
            modelos = self._obtener_valores_catalogo("modelos")
            bandas = self._obtener_valores_catalogo("bandas")
            if isinstance(getattr(self, "entry_nombre", None), ttk.Combobox):
                self.entry_nombre["values"] = modelos
            if isinstance(getattr(self, "entry_banda", None), ttk.Combobox):
                self.entry_banda["values"] = bandas
        if self._es_categoria_animales() and isinstance(getattr(self, "entry_uso_animal", None), ttk.Combobox):
            usos_animales = self._obtener_valores_catalogo("usos_animales")
            self.entry_uso_animal["values"] = usos_animales
            if usos_animales and not self.entry_uso_animal.get().strip():
                self.entry_uso_animal.set(usos_animales[0])
        if self._es_categoria_ropa() and isinstance(getattr(self, "combo_clima_ropa", None), ttk.Combobox):
            climas_ropa = self._obtener_valores_catalogo("climas_ropa")
            self.combo_clima_ropa["values"] = climas_ropa
            if climas_ropa and not self.combo_clima_ropa.get().strip():
                self.combo_clima_ropa.set(climas_ropa[0])
        if isinstance(self.combo_unidad, ttk.Combobox):
            if self._permite_consumo_por_unidades():
                self.combo_unidad["values"] = ["Piezas", "Bolsas", "Cajas", "Botellas", "Latas", "Paquetes"]
                if not self.combo_unidad.get().strip():
                    self.combo_unidad.set("Piezas")
            else:
                self.combo_unidad["values"] = unidades
                if unidades and not self.combo_unidad.get().strip():
                    self.combo_unidad.set(unidades[0])
        elif unidades and not self.combo_unidad.get().strip():
            self.combo_unidad.insert(0, unidades[0])
        self._configurar_combos_catalogo()
        self.lbl_listado.config(text="")

    def _categoria_data_actual(self):
        for categoria in listar_categorias_data():
            if categoria["nombre"] == self.categoria_actual:
                return categoria
        return None

    def _firma_campos_desde_categoria(self, categoria):
        campos = list((categoria or {}).get("campos", []) or [])
        return "|".join(f"{campo.get('id', '')}:{campo.get('label', '')}:{idx}" for idx, campo in enumerate(campos))

    def _firma_campos_actual(self):
        return self._firma_campos_desde_categoria(self._categoria_data_actual())

    def _set_valor_campo(self, widget, valor):
        texto = valor or ""
        if isinstance(widget, ttk.Combobox):
            widget.set(texto)
            return
        widget.delete(0, "end")
        widget.insert(0, texto)

    def _mover_foco_grilla(self, posiciones, widget, delta_fila=0, delta_columna=0):
        origen = posiciones.get(widget)
        if origen is None:
            return None

        fila_destino = origen[0] + delta_fila
        col_destino = origen[1] + delta_columna
        for candidato, posicion in posiciones.items():
            if posicion == (fila_destino, col_destino):
                try:
                    candidato.focus_set()
                    if isinstance(candidato, tk.Entry):
                        candidato.icursor("end")
                except Exception:
                    return "break"
                return "break"
        return None

    def _configurar_navegacion_flechas_alimentos(self):
        widgets = {
            self.entry_alimento: (0, 0),
            self.entry_cantidad: (0, 1),
            self.combo_unidad: (0, 2),
            self.entry_peso: (0, 3),
            self.combo_peso_unidad: (0, 4),
            self.entry_minimo: (0, 5),
            self.entry_fecha_ingreso: (1, 0),
            self.entry_fecha_produccion_compra: (1, 1),
            self.entry_caducidad: (1, 2),
        }

        for widget in widgets:
            widget.bind("<Left>", lambda event, w=widget: self._mover_foco_grilla(widgets, w, delta_columna=-1), add="+")
            widget.bind("<Right>", lambda event, w=widget: self._mover_foco_grilla(widgets, w, delta_columna=1), add="+")
            widget.bind("<Up>", lambda event, w=widget: self._mover_foco_grilla(widgets, w, delta_fila=-1), add="+")
            widget.bind("<Down>", lambda event, w=widget: self._mover_foco_grilla(widgets, w, delta_fila=1), add="+")

    def _opciones_subcategorias_editables(self):
        categoria = self._categoria_data_actual() or {}
        opciones = []
        usos_normalizados = {valor.lower() for valor in USOS_ANIMAL_PREDETERMINADOS}
        for valor in list(categoria.get("subcategorias", []) or []):
            texto = (valor or "").strip()
            if not texto or texto.lower() == "general":
                continue
            if self._es_categoria_animales() and texto.lower() in usos_normalizados:
                continue
            if texto not in opciones:
                opciones.append(texto)
        return sorted(opciones, key=str.lower)

    def _opciones_tipo_animales(self):
        return self._opciones_subcategorias_editables()

    def _agregar_tipo_combate(self):
        self._agregar_valor_catalogo_combo(
            self.combo_tipo,
            "subcategorias",
            "Nuevo tipo",
            "Escribe el tipo para agregar a la lista.",
        )

    def _agregar_tipo_animales(self):
        self._agregar_valor_catalogo_combo(
            self.combo_tipo,
            "subcategorias",
            "Nuevo tipo de animal",
            "Escribe el tipo de animal para guardarlo y reutilizarlo.",
        )

    def _configurar_combos_catalogo(self):
        self.combos_catalogo = {}
        if isinstance(getattr(self, "combo_tipo", None), ttk.Combobox):
            self._registrar_combo_catalogo(self.combo_tipo, "subcategorias", "tipo")
        if self._es_categoria_comunicacion():
            if isinstance(getattr(self, "entry_nombre", None), ttk.Combobox):
                self._registrar_combo_catalogo(self.entry_nombre, "modelos", "modelo")
            if isinstance(getattr(self, "entry_banda", None), ttk.Combobox):
                self._registrar_combo_catalogo(self.entry_banda, "bandas", "banda")
        if self._es_categoria_animales() and isinstance(getattr(self, "entry_uso_animal", None), ttk.Combobox):
            self._registrar_combo_catalogo(self.entry_uso_animal, "usos_animales", "uso")
        if self._es_categoria_ropa() and isinstance(getattr(self, "combo_clima_ropa", None), ttk.Combobox):
            self._registrar_combo_catalogo(self.combo_clima_ropa, "climas_ropa", "clima")
        if (
            isinstance(getattr(self, "combo_unidad", None), ttk.Combobox)
            and not self._permite_consumo_por_unidades()
            and not self._es_formulario_medicamento()
        ):
            self._registrar_combo_catalogo(self.combo_unidad, "unidades", "unidad")

    def _registrar_combo_catalogo(self, combo, catalogo, etiqueta):
        self.combos_catalogo[combo] = {"catalogo": catalogo, "etiqueta": etiqueta}
        combo.bind("<Button-3>", self._mostrar_menu_combo_catalogo)
        combo.bind("<Button-2>", self._mostrar_menu_combo_catalogo)

    def _mostrar_menu_combo_catalogo(self, event):
        combo = event.widget
        meta = self.combos_catalogo.get(combo)
        if not meta:
            return
        valor_actual = combo.get().strip()
        valores = self._obtener_valores_catalogo(meta["catalogo"])
        menu = tk.Menu(self.top, tearoff=0)
        menu.add_command(
            label=f'Agregar {meta["etiqueta"]}',
            command=lambda c=combo, m=meta: self._agregar_valor_catalogo_combo(
                c,
                m["catalogo"],
                f'Nuevo {m["etiqueta"]}',
                f'Escribe el {m["etiqueta"]} para agregar a la lista.',
            ),
        )
        if valor_actual and valor_actual in valores:
            menu.add_command(
                label=f'Editar "{valor_actual}"',
                command=lambda c=combo, m=meta: self._editar_valor_catalogo_combo(c, m["catalogo"]),
            )
            menu.add_command(
                label=f'Eliminar "{valor_actual}"',
                command=lambda c=combo, m=meta: self._eliminar_valor_catalogo_combo(c, m["catalogo"]),
            )
        else:
            menu.add_command(label="Editar valor actual", state="disabled")
            menu.add_command(label="Eliminar valor actual", state="disabled")
        menu.tk_popup(event.x_root, event.y_root)

    def _parent_dialogo_actual(self):
        if hasattr(self, "dialogo_item") and self.dialogo_item.winfo_exists():
            return self.dialogo_item
        return self.top

    def _obtener_valores_catalogo(self, catalogo):
        categoria = self._categoria_data_actual() or {}
        if catalogo == "subcategorias":
            return self._opciones_subcategorias_editables()
        if catalogo == "unidades":
            return [str(valor).strip() for valor in list(categoria.get("unidades", []) or []) if str(valor).strip()]
        if catalogo == "usos_animales":
            catalogos = categoria.get("catalogos", {}) or {}
            valores = [str(valor).strip() for valor in list(catalogos.get("usos_animales", []) or []) if str(valor).strip()]
            if not valores:
                valores = list(USOS_ANIMAL_PREDETERMINADOS)
            return valores
        if catalogo == "climas_ropa":
            catalogos = categoria.get("catalogos", {}) or {}
            valores = [str(valor).strip() for valor in list(catalogos.get("climas_ropa", []) or []) if str(valor).strip()]
            if not valores:
                valores = list(CLIMAS_ROPA_PREDETERMINADOS)
            return valores
        if catalogo in {"modelos", "bandas"}:
            catalogos = categoria.get("catalogos", {}) or {}
            return [str(valor).strip() for valor in list(catalogos.get(catalogo, []) or []) if str(valor).strip()]
        return []

    def _guardar_valores_catalogo(self, catalogo, valores):
        categoria = self._categoria_data_actual()
        if not categoria:
            raise ValueError("No se encontró la categoría actual.")
        kwargs = {
            "icono": categoria.get("icono", "📦"),
            "color": categoria.get("color", "#13223f"),
            "campos": categoria.get("campos", []),
            "subcategorias": categoria.get("subcategorias", []),
            "unidades": categoria.get("unidades", []),
            "catalogos": dict(categoria.get("catalogos", {}) or {}),
        }
        if catalogo == "subcategorias":
            if self._es_categoria_animales():
                kwargs["subcategorias"] = list(USOS_ANIMAL_PREDETERMINADOS) + list(valores)
            else:
                kwargs["subcategorias"] = list(valores)
        elif catalogo == "unidades":
            kwargs["unidades"] = list(valores)
        elif catalogo == "usos_animales":
            kwargs["catalogos"]["usos_animales"] = list(valores)
        elif catalogo == "climas_ropa":
            kwargs["catalogos"]["climas_ropa"] = list(valores)
        elif catalogo in {"modelos", "bandas"}:
            kwargs["catalogos"][catalogo] = list(valores)
        self.inventario.editar_categoria_completa(
            categoria["nombre"],
            categoria["nombre"],
            icono=kwargs["icono"],
            color=kwargs["color"],
            campos=kwargs["campos"],
            subcategorias=kwargs["subcategorias"],
            unidades=kwargs["unidades"],
            catalogos=kwargs["catalogos"],
        )

    def _agregar_valor_catalogo_combo(self, combo, catalogo, titulo, mensaje):
        parent_dialogo = self._parent_dialogo_actual()
        nuevo_valor = simpledialog.askstring(titulo, mensaje, parent=parent_dialogo)
        if nuevo_valor is None:
            return
        nuevo_valor = nuevo_valor.strip()
        if not nuevo_valor:
            return
        valores = self._obtener_valores_catalogo(catalogo)
        if any(valor.lower() == nuevo_valor.lower() for valor in valores):
            combo.set(next(valor for valor in valores if valor.lower() == nuevo_valor.lower()))
            return
        valores.append(nuevo_valor)
        valores = sorted(valores, key=str.lower)
        try:
            self._guardar_valores_catalogo(catalogo, valores)
        except Exception as e:
            messagebox.showwarning("No se pudo guardar", str(e), parent=parent_dialogo)
            return
        self._cargar_opciones_categoria()
        combo.set(nuevo_valor)
        if self.on_change:
            self.on_change()

    def _editar_valor_catalogo_combo(self, combo, catalogo):
        parent_dialogo = self._parent_dialogo_actual()
        valor_actual = combo.get().strip()
        valores = self._obtener_valores_catalogo(catalogo)
        if valor_actual not in valores:
            return
        nuevo_valor = simpledialog.askstring(
            "Editar valor",
            "Escribe el nuevo valor para la lista.",
            parent=parent_dialogo,
            initialvalue=valor_actual,
        )
        if nuevo_valor is None:
            return
        nuevo_valor = nuevo_valor.strip()
        if not nuevo_valor:
            return
        for existente in valores:
            if existente.lower() == nuevo_valor.lower() and existente != valor_actual:
                messagebox.showwarning("Valor duplicado", f'"{nuevo_valor}" ya existe en la lista.', parent=parent_dialogo)
                return
        valores = [nuevo_valor if valor == valor_actual else valor for valor in valores]
        valores = sorted(valores, key=str.lower)
        try:
            self._guardar_valores_catalogo(catalogo, valores)
        except Exception as e:
            messagebox.showwarning("No se pudo editar", str(e), parent=parent_dialogo)
            return
        self._cargar_opciones_categoria()
        combo.set(nuevo_valor)
        if self.on_change:
            self.on_change()

    def _eliminar_valor_catalogo_combo(self, combo, catalogo):
        parent_dialogo = self._parent_dialogo_actual()
        valor_actual = combo.get().strip()
        valores = self._obtener_valores_catalogo(catalogo)
        if valor_actual not in valores:
            return
        if not messagebox.askyesno(
            "Eliminar valor",
            f'¿Quieres eliminar "{valor_actual}" de esta lista?',
            parent=parent_dialogo,
        ):
            return
        valores = [valor for valor in valores if valor != valor_actual]
        try:
            self._guardar_valores_catalogo(catalogo, valores)
        except Exception as e:
            messagebox.showwarning("No se pudo eliminar", str(e), parent=parent_dialogo)
            return
        self._cargar_opciones_categoria()
        opciones_actualizadas = self._obtener_valores_catalogo(catalogo)
        combo.set(opciones_actualizadas[0] if opciones_actualizadas else "")
        if self.on_change:
            self.on_change()

    def _separar_contenido_unidad(self, valor):
        texto = (valor or "").strip()
        if not texto:
            return "", "gr"
        partes = texto.split()
        if len(partes) >= 2 and partes[-1].lower() in {"mg", "gr", "kg", "ml", "l"}:
            return " ".join(partes[:-1]), partes[-1].lower()
        return texto, "gr"

    def _separar_valor_unidad(self, valor, unidad_default, unidades_validas):
        texto = (valor or "").strip()
        if not texto:
            return "", unidad_default
        partes = texto.split()
        if len(partes) >= 2 and partes[-1].lower() in {u.lower() for u in unidades_validas}:
            return " ".join(partes[:-1]), partes[-1].lower()
        return texto, unidad_default

    def _validar_numero_parcial(self, valor):
        if valor == "":
            return True
        try:
            float(str(valor).replace(",", "."))
            return True
        except ValueError:
            return False

    def _configurar_validacion_numerica(self, widget):
        validador = (self.top.register(self._validar_numero_parcial), "%P")
        widget.configure(validate="key", validatecommand=validador)

    def _numero_formulario(self, valor):
        if valor in (None, ""):
            return None
        try:
            return float(str(valor).replace(",", "."))
        except ValueError:
            return None

    def _formatear_numero_ui(self, valor):
        if valor is None:
            return "0"
        if float(valor).is_integer():
            return str(int(valor))
        return f"{valor:.2f}".rstrip("0").rstrip(".")

    def _permite_consumo_por_unidades(self):
        return _normalizar_categoria(self.categoria_actual) == "alimentos"

    def _campos_personalizados(self):
        categoria = self._categoria_data_actual() or {}
        return list(categoria.get("campos", []) or [])

    def _usa_campos_personalizados(self):
        return (
            not self._permite_consumo_por_unidades()
            and not self._es_categoria_combate()
            and not self._es_categoria_herramientas()
            and not self._es_categoria_insumos_medicos()
            and not self._es_categoria_animales()
            and not self._es_categoria_plantas()
            and not self._es_categoria_comunicacion()
            and not self._es_categoria_energia()
            and not self._es_categoria_higiene()
            and not self._es_categoria_movilidad()
            and not self._es_categoria_cocina_preparacion()
            and not self._es_categoria_ropa()
        )

    def _es_categoria_personalizable(self):
        return (
            not self._permite_consumo_por_unidades()
            and not self._es_categoria_combate()
            and not self._es_categoria_herramientas()
            and not self._es_categoria_insumos_medicos()
            and not self._es_categoria_animales()
            and not self._es_categoria_plantas()
            and not self._es_categoria_comunicacion()
            and not self._es_categoria_energia()
            and not self._es_categoria_higiene()
            and not self._es_categoria_movilidad()
            and not self._es_categoria_cocina_preparacion()
            and not self._es_categoria_ropa()
        )

    def _es_categoria_combate(self):
        return _normalizar_categoria(self.categoria_actual) == "combate"

    def _es_categoria_herramientas(self):
        return _normalizar_categoria(self.categoria_actual) == "herramientas"

    def _es_categoria_insumos_medicos(self):
        return _normalizar_categoria(self.categoria_actual) == "insumos medicos"

    def _es_categoria_animales(self):
        return _normalizar_categoria(self.categoria_actual) == "animales"

    def _es_categoria_plantas(self):
        return _normalizar_categoria(self.categoria_actual) == "plantas"

    def _es_categoria_comunicacion(self):
        return _normalizar_categoria(self.categoria_actual) == "comunicacion"

    def _es_categoria_energia(self):
        return _normalizar_categoria(self.categoria_actual) == "energia"

    def _es_categoria_higiene(self):
        return _normalizar_categoria(self.categoria_actual) == "higiene"

    def _es_categoria_movilidad(self):
        return _normalizar_categoria(self.categoria_actual) == "movilidad"

    def _es_categoria_cocina_preparacion(self):
        return _normalizar_categoria(self.categoria_actual) == "cocina y preparacion"

    def _es_categoria_ropa(self):
        return _normalizar_categoria(self.categoria_actual) == "ropa"

    def _es_formulario_medicamento(self):
        return self._es_categoria_insumos_medicos() and self.modo_registro == "medicamento"

    def _armar_tabla_nutrimental(self):
        tabla = {clave: var.get().strip() for clave, var in self.nutr_vars.items()}
        filas = [
            f"{etiqueta:<14} | {tabla[clave]}"
            for etiqueta, clave in [("Porcion", "porcion"), ("Calorias", "calorias"), ("Proteinas", "proteinas"), ("Carbohidratos", "carbohidratos"), ("Grasas", "grasas"), ("Fibra", "fibra")]
            if tabla[clave]
        ]
        texto = "TABLA NUTRIMENTAL\n" + "-" * 29
        if filas:
            texto = "\n".join([texto] + filas)
        else:
            texto = self.txt_nutrimentales.get("1.0", "end").strip()
        return tabla, texto

    def _guardar_producto(self):
        categoria = self._categoria_data_actual()
        if not categoria:
            messagebox.showwarning("Categoría no disponible", "No se encontró la categoría actual.", parent=self.top)
            return
        campos_extra = {}
        if self._es_categoria_animales():
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip() or "1"
        elif self._es_categoria_comunicacion():
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip() or "1"
        elif self._es_categoria_energia():
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip()
        elif self._es_categoria_higiene():
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip()
        elif self._es_categoria_movilidad():
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip() or "1"
        elif self._es_categoria_cocina_preparacion():
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip()
        elif self._es_categoria_ropa():
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip()
        elif self._es_categoria_plantas():
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip() or "1"
        elif self._usa_campos_personalizados():
            if not self._campos_personalizados():
                messagebox.showwarning("Configura la categoría", "Primero agrega al menos una celda para poder registrar items.", parent=self.top)
                return
            campos_extra = {campo_id: widget.get().strip() for campo_id, widget in self.campos_extra_widgets.items()}
            nombre = next((valor for valor in campos_extra.values() if valor), "")
            cantidad = "1"
        else:
            nombre = self.entry_nombre.get().strip()
            cantidad = self.entry_cantidad.get().strip()
        tipo_valor = self.combo_tipo.get().strip() if hasattr(self, "combo_tipo") else ""
        if self._permite_consumo_por_unidades():
            tipo_valor = ""
        if not nombre:
            messagebox.showwarning("Revisa los datos", f"Escribe el nombre de {self.perfil['nombre_label'].lower()}.", parent=self.top)
            return
        unidad = self.combo_unidad.get().strip() if hasattr(self, "combo_unidad") else ""
        minimo = self.entry_minimo.get().strip() if hasattr(self, "entry_minimo") else ""
        contenido = self.entry_peso.get().strip() if hasattr(self, "entry_peso") else ""
        if hasattr(self, "combo_peso_unidad") and contenido:
            contenido = f"{contenido} {self.combo_peso_unidad.get().strip()}".strip()
        if self._es_categoria_combate() or self._es_categoria_herramientas():
            unidad = "Pieza"
            minimo = minimo or "0"
            contenido = ""
        elif self._es_categoria_animales():
            unidad = "cabeza"
            minimo = "0"
            contenido = f"{self.entry_alimento_diario.get().strip()} {self.combo_alimento_unidad.get().strip()}".strip()
        elif self._es_categoria_comunicacion():
            unidad = "pieza"
            minimo = "0"
            contenido = self.entry_banda.get().strip()
        elif self._es_categoria_energia():
            unidad = "pieza"
            minimo = "0"
            contenido = self.entry_capacidad.get().strip()
        elif self._es_categoria_higiene():
            unidad = self.combo_unidad.get().strip() or "pieza"
            minimo = self.entry_minimo.get().strip() or "0"
            contenido = self.entry_peso.get().strip()
        elif self._es_categoria_movilidad():
            unidad = "unidad"
            minimo = "0"
            contenido = self.entry_peso.get().strip()
        elif self._es_categoria_cocina_preparacion():
            unidad = self.combo_unidad.get().strip() or "pieza"
            minimo = self.entry_minimo.get().strip() or "0"
            contenido = self.entry_peso.get().strip()
        elif self._es_categoria_ropa():
            unidad = self.combo_unidad.get().strip() or "pieza"
            minimo = self.entry_minimo.get().strip() or "0"
            contenido = self.entry_peso.get().strip()
        elif self._es_categoria_plantas():
            unidad = "planta"
            minimo = "0"
            contenido = self.entry_riego.get().strip()
        elif self._usa_campos_personalizados():
            unidad = "pieza"
            minimo = "0"
            contenido = ""
        nutrimental, nutrimentales_texto = self._armar_tabla_nutrimental()
        datos = {
            "categoria_id": categoria["id"],
            "subcategoria": "medicamento" if self._es_formulario_medicamento() else (tipo_valor or ("medicamento" if self._es_categoria_insumos_medicos() else "general")),
            "tipo": "medicamento" if self._es_formulario_medicamento() else (tipo_valor or ("medicamento" if self._es_categoria_insumos_medicos() else "general")),
            "nombre": nombre,
            "codigo_barras": self.codigo_barras_actual,
            "cantidad": cantidad,
            "unidad": unidad,
            "minimo": minimo,
            "peso_contenido": contenido,
            "fecha_ingreso": self.entry_fecha_ingreso.get().strip() if hasattr(self, "entry_fecha_ingreso") else "",
            "fecha_produccion_compra": self.entry_fecha_produccion_compra.get().strip() if hasattr(self, "entry_fecha_produccion_compra") else "",
            "caducidad": self.entry_caducidad.get().strip() if hasattr(self, "entry_caducidad") else "",
            "lote": self.entry_lote.get().strip() if hasattr(self, "entry_lote") else "",
            "proposito": (
                self.entry_uso_animal.get().strip() if self._es_categoria_animales()
                else self.entry_bateria_equipo.get().strip() if self._es_categoria_comunicacion()
                else self.entry_salida_energia.get().strip() if self._es_categoria_energia()
                else self.entry_uso_movilidad.get().strip() if self._es_categoria_movilidad()
                else "" if self._es_categoria_ropa()
                else "" if self._es_categoria_plantas()
                else self.entry_indicaciones.get().strip() if hasattr(self, "entry_indicaciones") else ""
            ),
            "observaciones": self.txt_obs.get("1.0", "end").strip(),
            "composicion": (
                f"{self.entry_agua_diaria.get().strip()} {self.combo_agua_unidad.get().strip()}".strip() if self._es_categoria_animales()
                else self.entry_antenas.get().strip() if self._es_categoria_comunicacion()
                else self.entry_entrada_energia.get().strip() if self._es_categoria_energia()
                else self.entry_autonomia_movilidad.get().strip() if self._es_categoria_movilidad()
                else self.entry_combustible_cocina.get().strip() if self._es_categoria_cocina_preparacion()
                else self.combo_clima_ropa.get().strip() if self._es_categoria_ropa()
                else self.combo_clima.get().strip() if self._es_categoria_plantas()
                else ""
            ),
            "campos_extra": campos_extra,
            "nutrimentales": nutrimentales_texto if self.perfil["mostrar_nutrimental"] else self.txt_nutrimentales.get("1.0", "end").strip(),
            "nutrimental": nutrimental if self.perfil["mostrar_nutrimental"] else {},
            "foto": self.ruta_foto_actual,
            "origen": "codigo_barras" if self.codigo_barras_actual else ("foto" if self.ruta_foto_actual else "manual"),
        }
        try:
            if self.item_editando_id:
                actualizar_item(self.item_editando_id, **datos)
                messagebox.showinfo("Actualizado", f'Se actualizó "{nombre}".', parent=self.top)
            else:
                agregar_item(**datos)
                messagebox.showinfo("Guardado", f'Se agregó "{nombre}".', parent=self.top)
            self._limpiar_formulario()
            self._ocultar_dialogo_item()
            self._refrescar_todo()
            if self.on_change:
                self.on_change()
        except ValueError as e:
            messagebox.showwarning("Revisa los datos", str(e), parent=self.top)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.top)

    def _refrescar_todo(self):
        firma_actual = self._firma_campos_actual()
        if self.firma_campos_actual and firma_actual != self.firma_campos_actual:
            self._reconstruir_vista_categoria()
            return
        self._refrescar_tabla()
        self._refrescar_alertas()
        self._mostrar_detalle_item()

    def _preparar_nuevo(self):
        self.tree.selection_remove(*self.tree.selection())
        self._limpiar_formulario()
        self._mostrar_detalle_item()
        self._mostrar_dialogo_item(reconstruir=False)

    def _abrir_dialogo_item_nuevo(self):
        self.modo_registro = "medicamento" if self._es_categoria_insumos_medicos() else "general"
        self._preparar_nuevo()

    def _abrir_dialogo_insumo_nuevo(self):
        self.modo_registro = "general"
        self._preparar_nuevo()

    def _refrescar_tabla(self):
        self.items_visibles = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        items = listar_items(self.categoria_actual)
        if self.busqueda_actual:
            filtro = self.busqueda_actual.lower()
            items = [item for item in items if filtro in str(item.get("nombre", "")).lower()]
        self.items_visibles = items
        self._cargar_opciones_categoria()
        for item in items:
            if self._permite_consumo_por_unidades():
                values = (
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("unidad", ""),
                    item.get("peso_contenido", ""),
                    total_disponible_item(item),
                    item.get("minimo", ""),
                    item.get("fecha_ingreso", ""),
                    item.get("fecha_produccion_compra", ""),
                    item.get("caducidad", ""),
                )
            elif self._es_categoria_combate() or self._es_categoria_herramientas():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("minimo", ""),
                    item.get("lote", ""),
                    item.get("fecha_ingreso", ""),
                    item.get("fecha_produccion_compra", ""),
                    item.get("caducidad", ""),
                )
            elif self._es_categoria_animales():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("peso_contenido", ""),
                    item.get("composicion", ""),
                    item.get("proposito", ""),
                    item.get("lote", ""),
                )
            elif self._es_categoria_comunicacion():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("peso_contenido", ""),
                    item.get("composicion", ""),
                    item.get("proposito", ""),
                    item.get("lote", ""),
                )
            elif self._es_categoria_energia():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("peso_contenido", ""),
                    item.get("lote", ""),
                    item.get("composicion", ""),
                    item.get("proposito", ""),
                )
            elif self._es_categoria_higiene():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("unidad", ""),
                    item.get("peso_contenido", ""),
                    item.get("minimo", ""),
                    item.get("caducidad", ""),
                    item.get("lote", ""),
                )
            elif self._es_categoria_movilidad():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("peso_contenido", ""),
                    item.get("composicion", ""),
                    item.get("proposito", ""),
                    item.get("lote", ""),
                )
            elif self._es_categoria_cocina_preparacion():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("unidad", ""),
                    item.get("peso_contenido", ""),
                    item.get("composicion", ""),
                    item.get("lote", ""),
                )
            elif self._es_categoria_ropa():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("unidad", ""),
                    item.get("composicion", ""),
                    item.get("peso_contenido", ""),
                    item.get("lote", ""),
                )
            elif self._es_categoria_plantas():
                values = (
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("nombre", ""),
                    item.get("cantidad", ""),
                    item.get("peso_contenido", ""),
                    item.get("composicion", ""),
                )
            elif self._usa_campos_personalizados():
                campos = self._campos_personalizados()
                if campos:
                    values = tuple(item.get("campos_extra", {}).get(campo["id"], "") for campo in campos)
                else:
                    values = ("Configura celdas para ver la información.",)
            else:
                values = (
                    item.get("nombre", ""),
                    item.get("tipo", item.get("subcategoria", "")),
                    item.get("cantidad", ""),
                    item.get("unidad", ""),
                    item.get("minimo", ""),
                    item.get("peso_contenido", ""),
                    item.get("caducidad", ""),
                    item.get("lote", ""),
                )
            self.tree.insert("", "end", iid=item["id"], values=values)

    def _refrescar_alertas(self):
        self.lista_alertas.delete(0, "end")
        self.alertas_visibles = listar_alertas_inventario(self.categoria_actual)
        if not self.alertas_visibles:
            self.lista_alertas.insert("end", "Sin alertas por el momento.")
            return
        for alerta in self.alertas_visibles:
            self.lista_alertas.insert("end", alerta.get("mensaje", ""))

    def _item_seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            return None
        item_id = seleccion[0]
        for item in self.items_visibles:
            if item["id"] == item_id:
                return item
        return None

    def _buscar_item_por_nombre(self):
        termino = simpledialog.askstring(
            "Buscar item",
            "Escribe el nombre del item a buscar.\nDeja vacío para mostrar todo.",
            parent=self.top,
            initialvalue=self.busqueda_actual,
        )
        if termino is None:
            return
        self.busqueda_actual = termino.strip()
        self.tree.selection_remove(*self.tree.selection())
        self._refrescar_todo()

    def _mostrar_detalle_item(self, event=None):
        item = self._item_seleccionado()
        if not item:
            if self.btn_consumir_item.winfo_manager():
                self.btn_consumir_item.pack_forget()
            if self.btn_editar_item.winfo_manager():
                self.btn_editar_item.pack_forget()
            if self.btn_eliminar_item.winfo_manager():
                self.btn_eliminar_item.pack_forget()
            return
        if (self._permite_consumo_por_unidades() or self._es_categoria_insumos_medicos()) and not self.btn_consumir_item.winfo_manager():
            self.btn_consumir_item.pack(side="left", padx=4)
        elif not self._permite_consumo_por_unidades() and not self._es_categoria_insumos_medicos() and self.btn_consumir_item.winfo_manager():
            self.btn_consumir_item.pack_forget()
        if not self.btn_editar_item.winfo_manager():
            self.btn_editar_item.pack(side="left", padx=4)
        if not self.btn_eliminar_item.winfo_manager():
            self.btn_eliminar_item.pack(side="left", padx=4)

    def _cargar_a_edicion(self):
        item = self._item_seleccionado()
        if not item:
            messagebox.showwarning("Selecciona un recurso", "Primero selecciona un recurso de la tabla.", parent=self.top)
            return
        self.modo_registro = "medicamento" if self._es_categoria_insumos_medicos() and _normalizar_categoria(item.get("tipo", item.get("subcategoria", ""))) == "medicamento" else "general"
        if self._es_formulario_medicamento():
            self.item_editando_id = item["id"]
            self._limpiar_dialogo_medicamento()
            self.entry_med_nombre.insert(0, item.get("nombre", ""))
            self.entry_med_formula.insert(0, item.get("peso_contenido", ""))
            self.entry_med_cantidad.insert(0, item.get("cantidad", ""))
            self.combo_med_unidad.set(item.get("unidad", "") or "Miligramos")
            self.entry_med_caducidad.insert(0, item.get("caducidad", ""))
            self.entry_med_stock.insert(0, item.get("minimo", ""))
            self.txt_med_descripcion.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_medicamento()
            return
        if self._es_categoria_insumos_medicos():
            self.item_editando_id = item["id"]
            self._limpiar_dialogo_insumo()
            self.entry_ins_tipo.insert(0, item.get("nombre", ""))
            self.entry_ins_cantidad.insert(0, item.get("cantidad", ""))
            self.entry_ins_contenido.insert(0, item.get("peso_contenido", ""))
            self.entry_ins_unidad.insert(0, item.get("unidad", ""))
            self.entry_ins_caducidad.insert(0, item.get("caducidad", ""))
            self.entry_ins_stock.insert(0, item.get("minimo", ""))
            self.txt_ins_descripcion.insert("1.0", item.get("observaciones", ""))
            self.codigo_barras_actual = item.get("codigo_barras", "")
            if hasattr(self, "lbl_codigo_insumo"):
                self.lbl_codigo_insumo.config(text=self.codigo_barras_actual or "Sin codigo registrado")
            self._mostrar_dialogo_insumo()
            return
        if self._es_categoria_animales():
            self._limpiar_formulario(solo_campos=True)
            self._reconstruir_panel_formulario()
            self.item_editando_id = item["id"]
            self._set_valor_campo(self.combo_tipo, item.get("tipo", item.get("subcategoria", "")))
            self.entry_nombre.insert(0, item.get("nombre", ""))
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
            alimento_valor, alimento_unidad = self._separar_valor_unidad(item.get("peso_contenido", ""), "kg", ["kg", "gr"])
            agua_valor, agua_unidad = self._separar_valor_unidad(item.get("composicion", ""), "lt", ["lt", "ml"])
            self.entry_alimento_diario.insert(0, alimento_valor)
            self.combo_alimento_unidad.set(alimento_unidad)
            self.entry_agua_diaria.insert(0, agua_valor)
            self.combo_agua_unidad.set(agua_unidad)
            self.entry_uso_animal.insert(0, item.get("proposito", ""))
            self.txt_obs.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        if self._es_categoria_comunicacion():
            self._limpiar_formulario(solo_campos=True)
            self._reconstruir_panel_formulario()
            self.item_editando_id = item["id"]
            self._set_valor_campo(self.combo_tipo, item.get("tipo", item.get("subcategoria", "")))
            self.entry_nombre.insert(0, item.get("nombre", ""))
            self.entry_banda.insert(0, item.get("peso_contenido", ""))
            self.entry_antenas.insert(0, item.get("composicion", ""))
            self.entry_bateria_equipo.insert(0, item.get("proposito", ""))
            self.entry_pantalla.insert(0, item.get("lote", ""))
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
            self.txt_obs.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        if self._es_categoria_energia():
            self._limpiar_formulario(solo_campos=True)
            self._reconstruir_panel_formulario()
            self.item_editando_id = item["id"]
            self._set_valor_campo(self.combo_tipo, item.get("tipo", item.get("subcategoria", "")))
            self.entry_nombre.insert(0, item.get("nombre", ""))
            self.entry_capacidad.insert(0, item.get("peso_contenido", ""))
            self.entry_voltaje.insert(0, item.get("lote", ""))
            self.entry_entrada_energia.insert(0, item.get("composicion", ""))
            self.entry_salida_energia.insert(0, item.get("proposito", ""))
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
            self.txt_obs.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        if self._es_categoria_higiene():
            self._limpiar_formulario(solo_campos=True)
            self._reconstruir_panel_formulario()
            self.item_editando_id = item["id"]
            self._set_valor_campo(self.combo_tipo, item.get("tipo", item.get("subcategoria", "")))
            self.entry_nombre.insert(0, item.get("nombre", ""))
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
            self._set_valor_campo(self.combo_unidad, item.get("unidad", ""))
            self.entry_peso.insert(0, item.get("peso_contenido", ""))
            self.entry_minimo.insert(0, item.get("minimo", ""))
            self.entry_caducidad.insert(0, item.get("caducidad", ""))
            self.entry_lote.insert(0, item.get("lote", ""))
            self.txt_obs.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        if self._es_categoria_movilidad():
            self._limpiar_formulario(solo_campos=True)
            self._reconstruir_panel_formulario()
            self.item_editando_id = item["id"]
            self._set_valor_campo(self.combo_tipo, item.get("tipo", item.get("subcategoria", "")))
            self.entry_nombre.insert(0, item.get("nombre", ""))
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
            self.entry_peso.insert(0, item.get("peso_contenido", ""))
            self.entry_autonomia_movilidad.insert(0, item.get("composicion", ""))
            self.entry_uso_movilidad.insert(0, item.get("proposito", ""))
            self.entry_lote.insert(0, item.get("lote", ""))
            self.txt_obs.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        if self._es_categoria_cocina_preparacion():
            self._limpiar_formulario(solo_campos=True)
            self._reconstruir_panel_formulario()
            self.item_editando_id = item["id"]
            self._set_valor_campo(self.combo_tipo, item.get("tipo", item.get("subcategoria", "")))
            self.entry_nombre.insert(0, item.get("nombre", ""))
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
            self._set_valor_campo(self.combo_unidad, item.get("unidad", ""))
            self.entry_peso.insert(0, item.get("peso_contenido", ""))
            self.entry_combustible_cocina.insert(0, item.get("composicion", ""))
            self.entry_minimo.insert(0, item.get("minimo", ""))
            self.entry_lote.insert(0, item.get("lote", ""))
            self.txt_obs.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        if self._es_categoria_ropa():
            self._limpiar_formulario(solo_campos=True)
            self._reconstruir_panel_formulario()
            self.item_editando_id = item["id"]
            self._set_valor_campo(self.combo_tipo, item.get("tipo", item.get("subcategoria", "")))
            self.entry_nombre.insert(0, item.get("nombre", ""))
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
            self._set_valor_campo(self.combo_unidad, item.get("unidad", ""))
            self._set_valor_campo(self.combo_clima_ropa, item.get("composicion", ""))
            self.entry_peso.insert(0, item.get("peso_contenido", ""))
            self.entry_minimo.insert(0, item.get("minimo", ""))
            self.entry_lote.insert(0, item.get("lote", ""))
            self.txt_obs.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        if self._es_categoria_plantas():
            self._limpiar_formulario(solo_campos=True)
            self._reconstruir_panel_formulario()
            self.item_editando_id = item["id"]
            self._set_valor_campo(self.combo_tipo, item.get("tipo", item.get("subcategoria", "")))
            self.entry_nombre.insert(0, item.get("nombre", ""))
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
            self.entry_riego.insert(0, item.get("peso_contenido", ""))
            self._set_valor_campo(self.combo_clima, item.get("composicion", ""))
            self.txt_obs.insert("1.0", item.get("observaciones", ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        self._limpiar_formulario(solo_campos=True)
        self._reconstruir_panel_formulario()
        self.item_editando_id = item["id"]
        if hasattr(self, "combo_tipo") and not self._es_formulario_medicamento():
            self._set_valor_campo(self.combo_tipo, item.get("subcategoria", "general"))
        if self._usa_campos_personalizados():
            for campo_id, widget in self.campos_extra_widgets.items():
                widget.insert(0, item.get("campos_extra", {}).get(campo_id, ""))
            self._mostrar_dialogo_item(reconstruir=False)
            return
        self.entry_nombre.insert(0, item.get("nombre", ""))
        if hasattr(self, "entry_cantidad"):
            self.entry_cantidad.insert(0, item.get("cantidad", ""))
        if hasattr(self, "combo_unidad"):
            self._set_valor_campo(self.combo_unidad, item.get("unidad", ""))
        if hasattr(self, "entry_minimo"):
            self.entry_minimo.insert(0, item.get("minimo", ""))
        contenido_valor, contenido_unidad = self._separar_contenido_unidad(item.get("peso_contenido", ""))
        self.entry_peso.insert(0, contenido_valor)
        if hasattr(self, "combo_peso_unidad"):
            self.combo_peso_unidad.set(contenido_unidad)
        if hasattr(self, "entry_fecha_ingreso"):
            self.entry_fecha_ingreso.insert(0, item.get("fecha_ingreso", ""))
        if hasattr(self, "entry_fecha_produccion_compra"):
            self.entry_fecha_produccion_compra.insert(0, item.get("fecha_produccion_compra", ""))
        if hasattr(self, "entry_caducidad"):
            self.entry_caducidad.insert(0, item.get("caducidad", ""))
        if hasattr(self, "entry_lote"):
            self.entry_lote.insert(0, item.get("lote", ""))
        if hasattr(self, "entry_indicaciones"):
            self.entry_indicaciones.insert(0, item.get("proposito", ""))
        self.txt_nutrimentales.insert("1.0", item.get("nutrimentales", ""))
        self.txt_obs.insert("1.0", item.get("observaciones", ""))
        for clave, var in self.nutr_vars.items():
            var.set(item.get("nutrimental", {}).get(clave, ""))
        self.ruta_foto_actual = item.get("foto", "")
        self.codigo_barras_actual = item.get("codigo_barras", "")
        if hasattr(self, "lbl_foto"):
            self.lbl_foto.config(text=self.ruta_foto_actual or "Sin foto asociada")
        if hasattr(self, "lbl_codigo"):
            self.lbl_codigo.config(text=self.codigo_barras_actual or "Sin código registrado")
        self._mostrar_dialogo_item(reconstruir=False)

    def _eliminar_producto(self):
        item = self._item_seleccionado()
        if not item:
            messagebox.showwarning("Selecciona un recurso", "Primero selecciona un recurso de la tabla.", parent=self.top)
            return
        if not messagebox.askyesno("Eliminar recurso", f'¿Seguro que quieres eliminar "{item.get("nombre", "")}"?', parent=self.top):
            return
        eliminar_item_por_id(item["id"])
        self._limpiar_formulario()
        self._refrescar_todo()
        if self.on_change:
            self.on_change()

    def _consumir_desde_alerta(self):
        seleccion = self.lista_alertas.curselection()
        if not seleccion or not self.alertas_visibles:
            messagebox.showwarning("Selecciona alerta", "Selecciona una alerta con recurso consumible.", parent=self.top)
            return
        alerta = self.alertas_visibles[seleccion[0]]
        item_id = alerta.get("item_id")
        if not item_id:
            return
        if not messagebox.askyesno("Consumir recurso", "Se eliminará el recurso del inventario y la alerta desaparecerá. ¿Continuar?", parent=self.top):
            return
        marcar_item_consumido(item_id)
        self._refrescar_todo()
        if self.on_change:
            self.on_change()

    def _consumir_item_seleccionado(self):
        item = self._item_seleccionado()
        if not item:
            messagebox.showwarning("Selecciona un item", "Primero selecciona un item del listado.", parent=self.top)
            return

        cantidad_actual = str(item.get("cantidad", "")).strip()
        total_actual = total_disponible_item(item)
        prompt = f'¿Cuántas unidades de "{item.get("nombre", "")}" se consumieron?'
        if self._permite_consumo_por_unidades() and total_actual:
            prompt += f"\nDisponible actual: {total_actual}"
        elif cantidad_actual:
            prompt += f"\nDisponible actual: {cantidad_actual} {item.get('unidad', '')}".rstrip()
        if total_actual:
            prompt += f"\nTotal disponible: {total_actual}"

        consumido = simpledialog.askfloat("Consumir item", prompt, parent=self.top, minvalue=0.000001)
        if consumido is None:
            return

        try:
            resultado = consumir_item(item["id"], consumido)
        except ValueError as error:
            messagebox.showwarning("Consumo no válido", str(error), parent=self.top)
            return

        nombre = item.get("nombre", "")
        restante = resultado.get("cantidad_restante", 0)
        total_restante = resultado.get("total_restante")
        unidad_total = resultado.get("unidad_total", "")
        if resultado.get("eliminado"):
            messagebox.showinfo("Consumo registrado", f'"{nombre}" se consumió por completo.', parent=self.top)
        else:
            if total_restante is not None and unidad_total:
                restante_txt = str(total_restante).rstrip("0").rstrip(".") if isinstance(total_restante, float) else str(total_restante)
                messagebox.showinfo("Consumo registrado", f'Restante de "{nombre}": {restante_txt} {unidad_total}'.rstrip(), parent=self.top)
            else:
                restante_txt = str(restante).rstrip("0").rstrip(".") if isinstance(restante, float) else str(restante)
                messagebox.showinfo("Consumo registrado", f'Restante de "{nombre}": {restante_txt} {item.get("unidad", "")}'.rstrip(), parent=self.top)

        self._refrescar_todo()
        if self.on_change:
            self.on_change()

    def _limpiar_formulario(self, solo_campos=False):
        if hasattr(self, "entry_nombre"):
            self.entry_nombre.delete(0, "end")
        if hasattr(self, "entry_cantidad"):
            self.entry_cantidad.delete(0, "end")
        if hasattr(self, "entry_minimo"):
            self.entry_minimo.delete(0, "end")
        if hasattr(self, "entry_peso"):
            self.entry_peso.delete(0, "end")
        if hasattr(self, "entry_alimento_diario"):
            self.entry_alimento_diario.delete(0, "end")
        if hasattr(self, "entry_agua_diaria"):
            self.entry_agua_diaria.delete(0, "end")
        if hasattr(self, "entry_banda"):
            self.entry_banda.delete(0, "end")
        if hasattr(self, "entry_antenas"):
            self.entry_antenas.delete(0, "end")
        if hasattr(self, "entry_bateria_equipo"):
            self.entry_bateria_equipo.delete(0, "end")
        if hasattr(self, "entry_pantalla"):
            self.entry_pantalla.delete(0, "end")
        if hasattr(self, "entry_capacidad"):
            self.entry_capacidad.delete(0, "end")
        if hasattr(self, "entry_voltaje"):
            self.entry_voltaje.delete(0, "end")
        if hasattr(self, "entry_autonomia_movilidad"):
            self.entry_autonomia_movilidad.delete(0, "end")
        if hasattr(self, "entry_uso_movilidad"):
            self.entry_uso_movilidad.delete(0, "end")
        if hasattr(self, "entry_combustible_cocina"):
            self.entry_combustible_cocina.delete(0, "end")
        if hasattr(self, "entry_entrada_energia"):
            self.entry_entrada_energia.delete(0, "end")
        if hasattr(self, "entry_salida_energia"):
            self.entry_salida_energia.delete(0, "end")
        if hasattr(self, "entry_uso_animal"):
            self.entry_uso_animal.delete(0, "end")
        if hasattr(self, "combo_alimento_unidad"):
            self.combo_alimento_unidad.set("kg")
        if hasattr(self, "combo_agua_unidad"):
            self.combo_agua_unidad.set("lt")
        if hasattr(self, "entry_tiempo_siembra"):
            self.entry_tiempo_siembra.delete(0, "end")
        if hasattr(self, "entry_tiempo_cosecha"):
            self.entry_tiempo_cosecha.delete(0, "end")
        if hasattr(self, "entry_riego"):
            self.entry_riego.delete(0, "end")
        if hasattr(self, "entry_ubicacion_planta"):
            self.entry_ubicacion_planta.delete(0, "end")
        if hasattr(self, "combo_clima"):
            self.combo_clima.set("Templado")
        if hasattr(self, "combo_clima_ropa"):
            self.combo_clima_ropa.set("Mixto")
        if hasattr(self, "combo_peso_unidad"):
            self.combo_peso_unidad.set("gr")
        if hasattr(self, "entry_fecha_ingreso"):
            self.entry_fecha_ingreso.delete(0, "end")
        if hasattr(self, "entry_fecha_produccion_compra"):
            self.entry_fecha_produccion_compra.delete(0, "end")
        if hasattr(self, "entry_caducidad"):
            self.entry_caducidad.delete(0, "end")
        if hasattr(self, "entry_lote"):
            self.entry_lote.delete(0, "end")
        if hasattr(self, "entry_indicaciones"):
            self.entry_indicaciones.delete(0, "end")
        for widget in getattr(self, "campos_extra_widgets", {}).values():
            widget.delete(0, "end")
        if hasattr(self, "txt_nutrimentales"):
            self.txt_nutrimentales.delete("1.0", "end")
        if hasattr(self, "txt_obs"):
            self.txt_obs.delete("1.0", "end")
        self.ruta_foto_actual = ""
        self.codigo_barras_actual = ""
        if hasattr(self, "lbl_foto"):
            self.lbl_foto.config(text="Sin foto asociada")
        if hasattr(self, "lbl_codigo"):
            self.lbl_codigo.config(text="Sin código registrado")
        if hasattr(self, "combo_unidad") and self._es_formulario_medicamento():
            self.combo_unidad.set("Miligramos")
        for var in self.nutr_vars.values():
            var.set("")
        self._cargar_opciones_categoria()
        if not solo_campos:
            self.item_editando_id = None

    def _cantidad_para_incremento_codigo(self):
        texto = self.entry_cantidad.get().strip() or "1"
        try:
            cantidad = float(texto.replace(",", "."))
        except ValueError:
            raise ValueError("La cantidad debe ser numérica para aumentar un item por código.")
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero para aumentar un item por código.")
        return cantidad

    def _incrementar_item_existente(self, item_existente, origen):
        try:
            cantidad_extra = self._cantidad_para_incremento_codigo()
            foto = self.ruta_foto_actual if origen == "foto" else ""
            actualizado = incrementar_cantidad_item(
                item_existente["id"],
                cantidad_extra,
                foto=foto,
                origen=origen,
            )
        except ValueError as error:
            messagebox.showwarning("Inventario", str(error), parent=self.top)
            return False

        try:
            self.top.bell()
            self.top.after(140, self.top.bell)
        except Exception as exc:
            _log_inventario_warning(f"No se pudo reproducir la alerta sonora de inventario: {exc}")

        nombre = actualizado.get("nombre", "Item")
        messagebox.showinfo(
            "Item agregado",
            f'Se detectó "{nombre}" y se aumentó su cantidad a {actualizado.get("cantidad", "")}.',
            parent=self.top,
        )
        self._limpiar_formulario()
        self._ocultar_dialogo_item()
        self._refrescar_todo()
        if self.on_change:
            self.on_change()
        return True

    def _escanear_codigo_barras(self):
        categoria = self._categoria_data_actual()
        if not categoria:
            messagebox.showwarning("Categoría no disponible", "No se encontró la categoría actual.", parent=self.top)
            return

        resultado = capturar_codigo_barras_inventario()
        estado = resultado.get("estado", "")
        if estado == "cancelado":
            return
        if estado == "error":
            messagebox.showwarning("Escáner", resultado.get("mensaje", "No se pudo usar la cámara."), parent=self.top)
            return

        codigo = str(resultado.get("codigo_barras", "")).strip()
        if not codigo:
            messagebox.showwarning("Escáner", "No se detectó un código de barras válido.", parent=self.top)
            return

        self.codigo_barras_actual = codigo
        self.lbl_codigo.config(text=codigo)

        existente = buscar_item_por_codigo_barras(categoria["id"], codigo)
        if existente and existente.get("id") != self.item_editando_id:
            self._incrementar_item_existente(existente, "codigo_barras")

    def _capturar_foto_registro(self):
        resultado = capturar_foto_inventario()
        estado = resultado.get("estado", "")
        if estado == "cancelado":
            return
        if estado == "error":
            messagebox.showwarning("Foto", resultado.get("mensaje", "No se pudo usar la cámara."), parent=self.top)
            return

        ruta = resultado.get("ruta_foto", "") or ""
        if not ruta:
            messagebox.showwarning("Foto", "No se generó una ruta de foto válida.", parent=self.top)
            return

        texto = extraer_texto_ocr(ruta)
        analisis = analizar_texto_nutrimental(texto)
        analisis["texto_ocr"] = texto
        self._aplicar_resultado_foto(analisis, ruta)
        categoria = self._categoria_data_actual()
        nombre_detectado = self.entry_nombre.get().strip()
        if categoria and nombre_detectado and not self.item_editando_id:
            coincidencia = buscar_producto_por_nombre(categoria["id"], nombre_detectado)
            if coincidencia:
                _, item_existente = coincidencia
                if self._incrementar_item_existente(item_existente, "foto"):
                    return
        messagebox.showinfo("Foto", "La foto se capturó y quedó asociada al registro actual.", parent=self.top)

    def _aplicar_resultado_foto(self, resultado, ruta_foto=""):
        if not resultado:
            return
        self.ruta_foto_actual = ruta_foto
        self.lbl_foto.config(text=ruta_foto or "Sin foto asociada")
        nombre = resultado.get("nombre_sugerido") or resultado.get("nombre") or ""
        if nombre:
            self.entry_nombre.delete(0, "end")
            self.entry_nombre.insert(0, nombre)
        peso = resultado.get("peso_sugerido", "")
        cad = resultado.get("caducidad_sugerida", "")
        if peso:
            self.entry_peso.delete(0, "end")
            self.entry_peso.insert(0, peso)
        if cad:
            self.entry_caducidad.delete(0, "end")
            self.entry_caducidad.insert(0, cad)
        nutr_texto = resultado.get("datos_nutrimentales", "")
        if nutr_texto:
            self.txt_nutrimentales.delete("1.0", "end")
            self.txt_nutrimentales.insert("1.0", nutr_texto)
            for clave, terminos in {
                "porcion": ["porcion", "porción", "serving", "serv size", "serving size", "portion"],
                "calorias": ["energia", "energía", "calorias", "calorías", "calories", "kcal", "energy"],
                "proteinas": ["proteina", "proteínas", "proteinas", "protein", "prot"],
                "carbohidratos": ["carbohidratos", "carbohydrate", "carbohydrates", "carbs", "hidratos", "cho"],
                "grasas": ["grasas", "grasa total", "fat", "total fat", "lipidos", "lipids"],
                "fibra": ["fibra", "fiber", "dietary fiber", "fibre"],
            }.items():
                for linea in nutr_texto.splitlines():
                    l = linea.lower()
                    if any(t in l for t in terminos):
                        self.nutr_vars[clave].set(linea.split(":")[-1].strip())
        texto_ocr = resultado.get("texto_ocr", "")
        if texto_ocr:
            self.txt_obs.delete("1.0", "end")
            self.txt_obs.insert("1.0", f"OCR capturado:\n{texto_ocr[:1500]}")

    def _agregar_por_foto(self):
        resultado = capturar_y_analizar_inventario()
        estado = resultado.get("estado", "")
        if estado == "cancelado":
            return
        if estado == "error":
            messagebox.showwarning("Foto", resultado.get("mensaje", "No se pudo usar la cámara."), parent=self.top)
            return
        self._aplicar_resultado_foto(resultado, resultado.get("ruta_foto", ""))

    def _cargar_imagen_local(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("Todos los archivos", "*.*")],
            parent=self.top,
        )
        if not ruta:
            return
        texto = extraer_texto_ocr(ruta)
        resultado = analizar_texto_nutrimental(texto)
        resultado["texto_ocr"] = texto
        self._aplicar_resultado_foto(resultado, ruta)

    def enfocar(self):
        self.top.deiconify()
        self.top.lift()
        self.top.focus_force()

    def _al_recuperar_foco(self, event=None):
        if event is not None and event.widget is not self.top:
            return
        try:
            self._ajustar_a_pantalla()
        except Exception as exc:
            _log_inventario_warning(f"No se pudo reajustar la ventana de categoría al recuperar foco: {exc}")
        self._refrescar_todo()

    def _cerrar(self):
        if hasattr(self, "dialogo_insumo") and self.dialogo_insumo.winfo_exists():
            try:
                self.dialogo_insumo.destroy()
            except Exception as exc:
                _log_inventario_warning(f"No se pudo cerrar el diálogo de insumo: {exc}")
        if hasattr(self, "dialogo_medicamento") and self.dialogo_medicamento.winfo_exists():
            try:
                self.dialogo_medicamento.destroy()
            except Exception as exc:
                _log_inventario_warning(f"No se pudo cerrar el diálogo de medicamento: {exc}")
        if hasattr(self, "dialogo_item") and self.dialogo_item.winfo_exists():
            try:
                self.dialogo_item.destroy()
            except Exception as exc:
                _log_inventario_warning(f"No se pudo cerrar el diálogo de item: {exc}")
        if self.on_close:
            self.on_close(self.categoria_actual)
        self.top.destroy()

    def _configurar_campos_categoria_actual(self):
        categoria = self._categoria_data_actual()
        if not categoria:
            messagebox.showwarning("Categoría no disponible", "No se encontró la categoría actual.", parent=self.top)
            return
        dialogo = DialogoCategoriaInventario(self.top, categoria)
        if not dialogo.resultado:
            return
        try:
            self.inventario.editar_categoria(
                categoria["nombre"],
                categoria["nombre"],
                icono=categoria.get("icono", "📦"),
                color=categoria.get("color", "#13223f"),
                campos=dialogo.resultado["campos"],
            )
            self._reconstruir_vista_categoria()
            if self.on_change:
                self.on_change()
        except Exception as e:
            messagebox.showwarning("No se pudo actualizar", str(e), parent=self.top)

    def _agregar_celda_categoria_actual(self):
        categoria = self._categoria_data_actual()
        if not categoria:
            messagebox.showwarning("Categoría no disponible", "No se encontró la categoría actual.", parent=self.top)
            return
        parent_dialogo = self.dialogo_item if hasattr(self, "dialogo_item") and self.dialogo_item.winfo_exists() else self.top
        nombre = simpledialog.askstring("Agregar celda", "Nombre de la nueva celda:", parent=parent_dialogo)
        if nombre is None:
            return
        nombre = nombre.strip()
        if not nombre:
            messagebox.showwarning("Revisa los datos", "Escribe el nombre de la celda.", parent=parent_dialogo)
            return
        campos = list(categoria.get("campos", []) or [])
        campos.append({"id": f"campo_{len(campos) + 1}", "label": nombre, "posicion": len(campos)})
        try:
            self.inventario.editar_categoria(
                categoria["nombre"],
                categoria["nombre"],
                icono=categoria.get("icono", "📦"),
                color=categoria.get("color", "#13223f"),
                campos=campos,
            )
            self._reconstruir_vista_categoria()
            self._mostrar_dialogo_item(reconstruir=True)
            if self.on_change:
                self.on_change()
        except Exception as e:
            messagebox.showwarning("No se pudo actualizar", str(e), parent=parent_dialogo)

    def _reconstruir_vista_categoria(self):
        if hasattr(self, "dialogo_insumo") and self.dialogo_insumo.winfo_exists():
            self.dialogo_insumo.destroy()
        if hasattr(self, "dialogo_medicamento") and self.dialogo_medicamento.winfo_exists():
            self.dialogo_medicamento.destroy()
        if hasattr(self, "dialogo_item") and self.dialogo_item.winfo_exists():
            self.dialogo_item.destroy()
        for child in self.top.winfo_children():
            child.destroy()
        self.perfil = _perfil_categoria(self.categoria_actual)
        self._crear_ui()
        self._cargar_opciones_categoria()
        self._refrescar_todo()


class VentanaInventario:
    def __init__(self, root):
        self.root = root
        self.root.title("TLAMATINI - Inventario")
        self.ui = FUTURISTA_OSCURO
        self.root.configure(bg=self.ui["fondo"])
        self.root.resizable(True, True)
        self.root.minsize(980, 620)
        self._ajustar_a_pantalla()
        self.inventario = Inventario()
        self.subventanas = {}
        self.drag_categoria_id = None
        self.drag_inicio = None
        self.drag_activo = False
        self.drag_overlay = None
        self.drag_objetivo_id = None
        self.tarjetas_categoria = {}
        self.categoria_seleccionada_id = None
        self.bg_principal = self.ui["fondo"]
        self.bg_panel = self.ui["panel"]
        self.bg_panel_2 = self.ui["panel_2"]
        self.fg = self.ui["texto"]
        self.acento = self.ui["acento"]
        self.acento_ok = self.ui["ok"]
        self.acento_warn = self.ui["aviso"]
        self.acento_danger = self.ui["alerta"]
        _configurar_ttk()
        self._crear_ui()
        self._refrescar_resumen()
        self.root.bind("<FocusIn>", self._al_recuperar_foco)

    def _ajustar_a_pantalla(self):
        aplicar_geometria_relativa(self.root, self.root.master, rel_w=0.84, rel_h=0.82, min_w=980, min_h=620, pad=20)

    def _crear_ui(self):
        _, _, contenido = crear_contenedor_scrollable(self.root, bg=self.bg_principal)
        contenido.grid_columnconfigure(0, weight=1)

        header = tk.Frame(contenido, bg=self.bg_principal)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="INVENTARIO", font=("Arial", 28, "bold"), bg=self.bg_principal, fg=self.fg).grid(row=0, column=0, sticky="w")

        barra = tk.Frame(contenido, bg=self.bg_principal)
        barra.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))
        barra.grid_columnconfigure(0, weight=1)
        acciones = tk.Frame(barra, bg=self.bg_principal)
        acciones.grid(row=0, column=0, sticky="ew")
        tk.Label(
            acciones,
            text="Categorías fijas del sistema",
            font=("Arial", 11, "bold"),
            bg=self.bg_principal,
            fg="#c8d2e6",
        ).pack(side="left")

        cuerpo = tk.Frame(contenido, bg=self.bg_principal)
        cuerpo.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 22))
        cuerpo.grid_rowconfigure(0, weight=1)
        cuerpo.grid_columnconfigure(0, weight=1)

        self.panel_resumen = tk.Frame(cuerpo, bg=self.bg_principal)
        self.panel_resumen.grid(row=0, column=0, sticky="nsew")
        self.frame_tarjetas = tk.Frame(self.panel_resumen, bg=self.bg_principal)
        self.frame_tarjetas.pack(fill="both", expand=True)

    def _refrescar_resumen(self):
        categorias = listar_categorias_data()
        self.tarjetas_categoria = {}
        for widget in self.frame_tarjetas.winfo_children():
            widget.destroy()

        columnas = 4
        for idx, categoria in enumerate(categorias):
            fila = idx // columnas
            col = idx % columnas
            self.frame_tarjetas.grid_columnconfigure(col, weight=1, uniform="cats")
            self.frame_tarjetas.grid_rowconfigure(fila, weight=0)
            nombre = categoria["nombre"]
            color = categoria.get("color", "#13223f")
            card = tk.Frame(self.frame_tarjetas, bg=self.bg_panel, highlightthickness=1, highlightbackground=self.ui["borde"])
            card.grid(row=fila, column=col, sticky="nsew", padx=10, pady=10, ipadx=8, ipady=8)
            card.grid_propagate(False)
            card.configure(width=220, height=170)
            card.categoria_id = categoria["id"]
            card.categoria_nombre = nombre
            card.categoria_color = color
            tk.Frame(card, bg=color, height=4).pack(fill="x")
            cuerpo = tk.Frame(card, bg=self.bg_panel, cursor="hand2")
            cuerpo.pack(fill="both", expand=True, padx=16, pady=14)
            cuerpo.categoria_id = categoria["id"]
            cuerpo.categoria_nombre = nombre
            cuerpo.categoria_color = color
            tk.Label(cuerpo, text=categoria.get('icono', '📦'), font=("Arial", 24), bg=self.bg_panel, fg=self.fg).pack(anchor="w")
            tk.Label(cuerpo, text=nombre, font=("Arial", 15, "bold"), bg=self.bg_panel, fg=self.fg, wraplength=180, justify="left").pack(anchor="w", pady=(8, 2))
            self.tarjetas_categoria[categoria["id"]] = card
            for widget in (card, cuerpo, *cuerpo.winfo_children()):
                widget.categoria_id = categoria["id"]
                widget.categoria_nombre = nombre
                widget.bind("<Button-1>", lambda event, cid=categoria["id"]: self._seleccionar_categoria_visual(cid))
                widget.bind("<Double-Button-1>", lambda event, n=nombre: self._abrir_categoria(n))
                widget.bind("<ButtonPress-1>", lambda event, cid=categoria["id"]: self._iniciar_arrastre(event, cid))
                widget.bind("<B1-Motion>", self._mover_arrastre)
                widget.bind("<ButtonRelease-1>", self._terminar_arrastre)

    def _abrir_categoria(self, nombre):
        existente = self.subventanas.get(nombre)
        if existente:
            existente.enfocar()
            return
        self.subventanas[nombre] = VentanaCategoriaInventario(
            self.root,
            nombre,
            on_change=self._refrescar_resumen,
            on_close=self._cerrar_registro_subventana,
        )

    def _cerrar_registro_subventana(self, nombre):
        self.subventanas.pop(nombre, None)
        self._refrescar_resumen()

    def _cerrar_todas_subventanas(self):
        for nombre, ventana in list(self.subventanas.items()):
            try:
                ventana.top.destroy()
            except Exception as exc:
                _log_inventario_warning(f"No se pudo cerrar la subventana de inventario '{nombre}': {exc}")
            self.subventanas.pop(nombre, None)

    def _iniciar_arrastre(self, event, categoria_id):
        self.drag_categoria_id = categoria_id
        self.drag_inicio = (event.x_root, event.y_root)
        self.drag_activo = False
        self.drag_objetivo_id = None

    def _mover_arrastre(self, event):
        if not self.drag_inicio:
            return
        dx = abs(event.x_root - self.drag_inicio[0])
        dy = abs(event.y_root - self.drag_inicio[1])
        if dx > 8 or dy > 8:
            if not self.drag_activo:
                self.drag_activo = True
                self._mostrar_overlay_arrastre()
            self._mover_overlay_arrastre(event.x_root, event.y_root)
            self._actualizar_objetivo_arrastre(event.x_root, event.y_root)

    def _terminar_arrastre(self, event):
        if self.drag_activo and self.drag_categoria_id:
            categoria_id_destino = self.drag_objetivo_id or self._categoria_destino_mas_cercana(event.x_root, event.y_root)
            if categoria_id_destino and categoria_id_destino != self.drag_categoria_id:
                reordenar_categorias(self.drag_categoria_id, categoria_id_destino)
                self._refrescar_resumen()
        self._ocultar_overlay_arrastre()
        self._limpiar_resaltado_objetivo()
        self.drag_categoria_id = None
        self.drag_inicio = None
        self.drag_activo = False
        self.drag_objetivo_id = None

    def _seleccionar_categoria_visual(self, categoria_id):
        self.categoria_seleccionada_id = categoria_id
        for cid, tarjeta in self.tarjetas_categoria.items():
            if cid == categoria_id:
                tarjeta.config(highlightbackground=self.ui["acento"], highlightthickness=2, highlightcolor=self.ui["acento"])
            else:
                tarjeta.config(highlightbackground=self.ui["borde"], highlightthickness=1, highlightcolor=self.ui["borde"])

    def _mostrar_overlay_arrastre(self):
        tarjeta = self.tarjetas_categoria.get(self.drag_categoria_id)
        if not tarjeta:
            return
        nombre = getattr(tarjeta, "categoria_nombre", "")
        color = getattr(tarjeta, "categoria_color", self.ui["acento"])
        self.drag_overlay = tk.Toplevel(self.root)
        self.drag_overlay.overrideredirect(True)
        self.drag_overlay.attributes("-alpha", 0.82)
        self.drag_overlay.configure(bg=self.ui["borde"])
        marco = tk.Frame(self.drag_overlay, bg=self.bg_panel, highlightthickness=1, highlightbackground=self.ui["acento"])
        marco.pack(padx=1, pady=1)
        tk.Frame(marco, bg=color, height=4).pack(fill="x")
        tk.Label(marco, text=nombre, font=("Arial", 15, "bold"), bg=self.bg_panel, fg=self.fg, padx=18, pady=16).pack()

    def _mover_overlay_arrastre(self, x_root, y_root):
        if self.drag_overlay:
            self.drag_overlay.geometry(f"+{int(x_root + 14)}+{int(y_root + 14)}")

    def _ocultar_overlay_arrastre(self):
        if self.drag_overlay:
            self.drag_overlay.destroy()
            self.drag_overlay = None

    def _actualizar_objetivo_arrastre(self, x_root, y_root):
        objetivo = self._categoria_destino_mas_cercana(x_root, y_root)
        if objetivo == self.drag_categoria_id:
            objetivo = None
        if objetivo == self.drag_objetivo_id:
            return
        self._limpiar_resaltado_objetivo()
        self.drag_objetivo_id = objetivo
        if objetivo and objetivo in self.tarjetas_categoria:
            self.tarjetas_categoria[objetivo].config(highlightthickness=2, highlightbackground=self.ui["acento"], highlightcolor=self.ui["acento"])

    def _limpiar_resaltado_objetivo(self):
        for tarjeta in self.tarjetas_categoria.values():
            tarjeta.config(highlightthickness=1, highlightbackground=self.ui["borde"], highlightcolor=self.ui["borde"])

    def _categoria_destino_mas_cercana(self, x_root, y_root):
        candidatos = []
        for tarjeta in self.tarjetas_categoria.values():
            categoria_id = getattr(tarjeta, "categoria_id", None)
            if not categoria_id:
                continue
            centro_x = tarjeta.winfo_rootx() + (tarjeta.winfo_width() / 2)
            centro_y = tarjeta.winfo_rooty() + (tarjeta.winfo_height() / 2)
            distancia = abs(centro_x - x_root) + abs(centro_y - y_root)
            candidatos.append((distancia, categoria_id))
        if not candidatos:
            return None
        candidatos.sort(key=lambda item: item[0])
        return candidatos[0][1]

    def _al_recuperar_foco(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        try:
            self._ajustar_a_pantalla()
        except Exception as exc:
            _log_inventario_warning(f"No se pudo reajustar la ventana principal de inventario: {exc}")
        self._refrescar_resumen()
