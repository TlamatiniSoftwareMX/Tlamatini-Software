import tkinter as tk
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core.planes import (
    ETIQUETAS_SECCIONES,
    SECCIONES_LISTA,
    SECCIONES_SIMPLE,
    crear_plan_vacio,
    eliminar_plan,
    exportar_plan_texto,
    guardar_plan,
    listar_planes,
    normalizar_plan,
    renderizar_plan_texto,
    resumen_plan,
    titulo_plan,
)
from core.window_geometry import aplicar_geometria_relativa, crear_contenedor_scrollable, habilitar_scroll_mouse


PALETA = {
    "bg": "#071223",
    "bg_alt": "#0b1a30",
    "panel": "#10243f",
    "panel_2": "#132b48",
    "borde": "#28496B",
    "fg": "#F7FAFC",
    "fg_dim": "#A8C0D8",
    "acento": "#1D4ED8",
    "ok": "#169C72",
    "warn": "#D97706",
    "danger": "#B91C1C",
}

SECCIONES_FORM_SIMPLE = {
    "datos_generales": [
        ("nombre_del_plan", False),
        ("fecha_de_elaboracion", False),
        ("version", False),
        ("elaborado_por", False),
        ("grupo_o_familia", False),
        ("ubicacion_general", False),
        ("escenario_principal", True),
    ],
    "objetivo_plan": [
        ("objetivo_general", True),
        ("objetivos_especificos", True),
    ],
    "alcance": [
        ("personas_cubiertas", True),
        ("periodo_estimado_de_aplicacion", False),
        ("situaciones_en_las_que_aplica", True),
        ("limitaciones_del_plan", True),
    ],
    "descripcion_zona": [
        ("tipo_de_zona", False),
        ("descripcion_general", True),
        ("accesos_y_salidas", True),
        ("puntos_criticos", True),
        ("fuentes_de_agua", True),
        ("areas_de_resguardo", True),
        ("zonas_inseguras", True),
        ("condiciones_climaticas_relevantes", True),
        ("cercania_a_riesgos", True),
    ],
    "rutas_evac": [
        ("ruta_principal", True),
        ("ruta_secundaria", True),
        ("punto_de_reunion_1", False),
        ("punto_de_reunion_2", False),
        ("medios_de_transporte", False),
        ("tiempo_estimado", False),
        ("obstaculos_probables", True),
        ("criterios_para_activar_evac", True),
        ("destino_temporal", False),
        ("destino_alternativo", False),
        ("observaciones", True),
    ],
    "revisiones": [
        ("periodicidad_general", False),
        ("fecha_ultima_revision", False),
        ("proxima_revision", False),
        ("responsable_de_revision", False),
        ("cambios_realizados", True),
        ("lecciones_aprendidas", True),
    ],
}

SECCIONES_FORM_LISTA = {
    "identificacion_riesgos": [
        ("tipo_de_riesgo", False),
        ("descripcion", True),
        ("probabilidad", False),
        ("impacto", False),
        ("senales_de_alerta", True),
        ("medidas_preventivas", True),
        ("respuesta_inicial", True),
    ],
    "organizacion_responsables": [
        ("nombre", False),
        ("funcion", False),
        ("lugar_o_puesto", False),
        ("responsabilidad_principal", True),
        ("responsabilidad_secundaria", True),
        ("contacto", False),
        ("observaciones", True),
    ],
    "recursos_disponibles": [
        ("categoria_recurso", False),
        ("nombre_recurso", False),
        ("cantidad", False),
        ("unidad", False),
        ("ubicacion", False),
        ("responsable", False),
        ("estado", False),
        ("fecha_de_revision", False),
        ("observaciones", True),
    ],
    "procedimientos_actuacion": [
        ("escenario", False),
        ("fase", False),
        ("activacion_del_plan", True),
        ("procedimiento_inicial", True),
        ("aseguramiento_de_personas", True),
        ("resguardo_de_recursos_clave", True),
        ("comunicacion_interna", True),
        ("comunicacion_externa", True),
        ("decision_de_permanecer_o_evacuar", True),
        ("procedimiento_de_evac", True),
        ("procedimiento_de_refugio_en_sitio", True),
        ("procedimiento_post_evento", True),
        ("criterios_de_cierre_o_retorno", True),
    ],
    "simulacros": [
        ("tipo_de_simulacro", False),
        ("frecuencia", False),
        ("responsables", False),
        ("ultimo_simulacro", False),
        ("hallazgos", True),
        ("mejoras_requeridas", True),
    ],
}

CAMPO_ETIQUETAS = {
    "nombre_del_plan": "Nombre del plan",
    "fecha_de_elaboracion": "Fecha de elaboración",
    "version": "Versión",
    "elaborado_por": "Elaborado por",
    "grupo_o_familia": "Grupo o familia",
    "ubicacion_general": "Ubicación general",
    "escenario_principal": "Escenario principal",
    "objetivo_general": "Objetivo general",
    "objetivos_especificos": "Objetivos específicos",
    "personas_cubiertas": "Personas cubiertas",
    "periodo_estimado_de_aplicacion": "Periodo estimado de aplicación",
    "situaciones_en_las_que_aplica": "Situaciones en las que aplica",
    "limitaciones_del_plan": "Limitaciones del plan",
    "tipo_de_zona": "Tipo de zona",
    "descripcion_general": "Descripción general",
    "accesos_y_salidas": "Accesos y salidas",
    "puntos_criticos": "Puntos críticos",
    "fuentes_de_agua": "Fuentes de agua",
    "areas_de_resguardo": "Áreas de resguardo",
    "zonas_inseguras": "Zonas inseguras",
    "condiciones_climaticas_relevantes": "Condiciones climáticas relevantes",
    "cercania_a_riesgos": "Cercanía a riesgos",
    "tipo_de_riesgo": "Tipo de riesgo",
    "descripcion": "Descripción",
    "probabilidad": "Probabilidad",
    "impacto": "Impacto",
    "senales_de_alerta": "Señales de alerta",
    "medidas_preventivas": "Medidas preventivas",
    "respuesta_inicial": "Respuesta inicial",
    "nombre": "Nombre",
    "funcion": "Función",
    "lugar_o_puesto": "Lugar o puesto",
    "responsabilidad_principal": "Responsabilidad principal",
    "responsabilidad_secundaria": "Responsabilidad secundaria",
    "contacto": "Contacto",
    "observaciones": "Observaciones",
    "categoria_recurso": "Categoría del recurso",
    "nombre_recurso": "Nombre del recurso",
    "cantidad": "Cantidad",
    "unidad": "Unidad",
    "ubicacion": "Ubicación",
    "responsable": "Responsable",
    "estado": "Estado",
    "fecha_de_revision": "Fecha de revisión",
    "ruta_principal": "Ruta principal",
    "ruta_secundaria": "Ruta secundaria",
    "punto_de_reunion_1": "Punto de reunión 1",
    "punto_de_reunion_2": "Punto de reunión 2",
    "medios_de_transporte": "Medios de transporte",
    "tiempo_estimado": "Tiempo estimado",
    "obstaculos_probables": "Obstáculos probables",
    "criterios_para_activar_evac": "Criterios para activar evacuación",
    "destino_temporal": "Destino temporal",
    "destino_alternativo": "Destino alternativo",
    "escenario": "Escenario",
    "fase": "Fase",
    "activacion_del_plan": "Activación del plan",
    "procedimiento_inicial": "Procedimiento inicial",
    "aseguramiento_de_personas": "Aseguramiento de personas",
    "resguardo_de_recursos_clave": "Resguardo de recursos clave",
    "comunicacion_interna": "Comunicación interna",
    "comunicacion_externa": "Comunicación externa",
    "decision_de_permanecer_o_evacuar": "Decisión de permanecer o evacuar",
    "procedimiento_de_evac": "Procedimiento de evacuación",
    "procedimiento_de_refugio_en_sitio": "Refugio en sitio",
    "procedimiento_post_evento": "Procedimiento post-evento",
    "criterios_de_cierre_o_retorno": "Criterios de cierre o retorno",
    "tipo_de_simulacro": "Tipo de simulacro",
    "frecuencia": "Frecuencia",
    "responsables": "Responsables",
    "ultimo_simulacro": "Último simulacro",
    "hallazgos": "Hallazgos",
    "mejoras_requeridas": "Mejoras requeridas",
    "periodicidad_general": "Periodicidad general",
    "fecha_ultima_revision": "Fecha última revisión",
    "proxima_revision": "Próxima revisión",
    "responsable_de_revision": "Responsable de revisión",
    "cambios_realizados": "Cambios realizados",
    "lecciones_aprendidas": "Lecciones aprendidas",
}


def _etiqueta_campo(clave: str) -> str:
    return CAMPO_ETIQUETAS.get(clave, clave.replace("_", " ").capitalize())


def _configurar_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Planes.Treeview",
        background="#F8FAFC",
        foreground="#0F172A",
        fieldbackground="#F8FAFC",
        rowheight=28,
        font=("Arial", 10),
    )
    style.configure("Planes.Treeview.Heading", font=("Arial", 10, "bold"))
    style.map(
        "Planes.Treeview",
        background=[("selected", PALETA["acento"])],
        foreground=[("selected", "white")],
    )


class VentanaPlanes:
    def __init__(self, root):
        self.root = root
        self.root.title("TLAMATINI - Planes de emergencia")
        self.root.configure(bg=PALETA["bg"])
        self.root.minsize(1260, 760)
        aplicar_geometria_relativa(self.root, self.root.master, rel_w=0.9, rel_h=0.9, min_w=1240, min_h=760)

        _configurar_style()

        self.planes = []
        self.plan_actual = None
        self.plan_actual_id = None
        self.modo_actual = "vacio"

        self.simple_widgets = {}
        self.list_widgets = {}
        self.preview_text = None
        self.btn_guardar_borrador = None
        self.btn_guardar = None
        self.btn_editar = None
        self.btn_visualizar = None
        self.btn_exportar = None
        self.btn_eliminar = None
        self.lbl_estado = None
        self.lbl_subtitulo = None
        self.tree_planes = None
        self.form_wrap = None
        self.preview_wrap = None
        self.form_scroll = None
        self.form_container = None

        self._crear_ui()
        self._cargar_planes()
        self._mostrar_estado_vacio()

    def _crear_ui(self):
        contenedor = tk.Frame(self.root, bg=PALETA["bg"])
        contenedor.pack(fill="both", expand=True, padx=16, pady=16)
        contenedor.grid_columnconfigure(1, weight=1)
        contenedor.grid_rowconfigure(1, weight=1)

        encabezado = tk.Frame(contenedor, bg=PALETA["bg"])
        encabezado.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        encabezado.grid_columnconfigure(0, weight=1)

        tk.Label(
            encabezado,
            text="Planes de emergencia",
            bg=PALETA["bg"],
            fg=PALETA["fg"],
            font=("Arial", 22, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.lbl_subtitulo = tk.Label(
            encabezado,
            text="Plantilla operativa para familia, individuos, grupos pequeños o comunidad de apoyo.",
            bg=PALETA["bg"],
            fg=PALETA["fg_dim"],
            font=("Arial", 11),
        )
        self.lbl_subtitulo.grid(row=1, column=0, sticky="w", pady=(4, 0))

        barra = tk.Frame(encabezado, bg=PALETA["bg"])
        barra.grid(row=0, column=1, rowspan=2, sticky="e")

        self._crear_boton(barra, "Nuevo", self._nuevo_plan, PALETA["acento"]).pack(side="left", padx=(0, 8))
        self.btn_guardar_borrador = self._crear_boton(barra, "Guardar borrador", self._guardar_borrador, PALETA["warn"])
        self.btn_guardar_borrador.pack(side="left", padx=4)
        self.btn_guardar = self._crear_boton(barra, "Guardar", self._guardar_final, PALETA["ok"])
        self.btn_guardar.pack(side="left", padx=4)
        self.btn_editar = self._crear_boton(barra, "Editar", self._editar_plan, PALETA["acento"])
        self.btn_editar.pack(side="left", padx=4)
        self.btn_visualizar = self._crear_boton(barra, "Visualizar", self._visualizar_plan, PALETA["panel_2"])
        self.btn_visualizar.pack(side="left", padx=4)
        self.btn_exportar = self._crear_boton(barra, "Exportar", self._exportar_plan, PALETA["panel_2"])
        self.btn_exportar.pack(side="left", padx=4)
        self.btn_eliminar = self._crear_boton(barra, "Eliminar", self._eliminar_plan_ui, PALETA["danger"])
        self.btn_eliminar.pack(side="left", padx=(8, 0))

        lateral = tk.Frame(contenedor, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["borde"])
        lateral.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        lateral.configure(width=360)
        lateral.grid_propagate(False)
        lateral.grid_rowconfigure(2, weight=1)
        lateral.grid_columnconfigure(0, weight=1)

        tk.Label(
            lateral,
            text="Lista de planes",
            bg=PALETA["panel"],
            fg=PALETA["fg"],
            font=("Arial", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        self.lbl_estado = tk.Label(
            lateral,
            text="Sin planes cargados.",
            bg=PALETA["panel"],
            fg=PALETA["fg_dim"],
            font=("Arial", 10),
        )
        self.lbl_estado.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        tree_frame = tk.Frame(lateral, bg=PALETA["panel"])
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree_planes = ttk.Treeview(
            tree_frame,
            style="Planes.Treeview",
            columns=("estado", "escenario", "fecha"),
            show="tree headings",
            selectmode="browse",
        )
        self.tree_planes.heading("#0", text="Plan")
        self.tree_planes.heading("estado", text="Estado")
        self.tree_planes.heading("escenario", text="Escenario")
        self.tree_planes.heading("fecha", text="Actualizado")
        self.tree_planes.column("#0", width=170, anchor="w")
        self.tree_planes.column("estado", width=80, anchor="center")
        self.tree_planes.column("escenario", width=100, anchor="w")
        self.tree_planes.column("fecha", width=120, anchor="center")
        self.tree_planes.grid(row=0, column=0, sticky="nsew")
        self.tree_planes.bind("<<TreeviewSelect>>", self._al_seleccionar_plan)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_planes.yview)
        self.tree_planes.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        habilitar_scroll_mouse(tree_frame, self.tree_planes)

        detalle = tk.Frame(contenedor, bg=PALETA["panel"], highlightthickness=1, highlightbackground=PALETA["borde"])
        detalle.grid(row=1, column=1, sticky="nsew")
        detalle.grid_rowconfigure(1, weight=1)
        detalle.grid_columnconfigure(0, weight=1)

        self.info_superior = tk.Frame(detalle, bg=PALETA["panel"])
        self.info_superior.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        self.info_superior.grid_columnconfigure(0, weight=1)

        self.lbl_titulo_detalle = tk.Label(
            self.info_superior,
            text="Sin selección",
            bg=PALETA["panel"],
            fg=PALETA["fg"],
            font=("Arial", 16, "bold"),
        )
        self.lbl_titulo_detalle.grid(row=0, column=0, sticky="w")

        self.lbl_detalle_estado = tk.Label(
            self.info_superior,
            text="Crea un plan nuevo o selecciona uno guardado para verlo.",
            bg=PALETA["panel"],
            fg=PALETA["fg_dim"],
            font=("Arial", 10),
        )
        self.lbl_detalle_estado.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.body = tk.Frame(detalle, bg=PALETA["panel"])
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.form_wrap = tk.Frame(self.body, bg=PALETA["panel"])
        self.preview_wrap = tk.Frame(self.body, bg=PALETA["panel"])

        self._crear_formulario()
        self._crear_preview()

        self._actualizar_botones()

    def _crear_preview(self):
        cont = tk.Frame(self.preview_wrap, bg=PALETA["panel"])
        cont.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        tk.Label(
            cont,
            text="Vista de consulta",
            bg=PALETA["panel"],
            fg=PALETA["fg"],
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            cont,
            text="Modo solo lectura con scroll. Úsalo para revisar, imprimir o exportar.",
            bg=PALETA["panel"],
            fg=PALETA["fg_dim"],
            font=("Arial", 10),
        ).pack(anchor="w", pady=(0, 10))

        frame_texto = tk.Frame(cont, bg=PALETA["panel"])
        frame_texto.pack(fill="both", expand=True)
        frame_texto.grid_rowconfigure(0, weight=1)
        frame_texto.grid_columnconfigure(0, weight=1)

        self.preview_text = tk.Text(
            frame_texto,
            bg="#F8FAFC",
            fg="#0F172A",
            insertbackground="#0F172A",
            relief="flat",
            wrap="word",
            font=("Courier New", 10),
            padx=12,
            pady=12,
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        self.preview_text.config(state="disabled")

        scroll = ttk.Scrollbar(frame_texto, orient="vertical", command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        habilitar_scroll_mouse(frame_texto, self.preview_text)

    def _crear_formulario(self):
        exterior, _canvas, interior = crear_contenedor_scrollable(self.form_wrap, bg=PALETA["panel"], canvas_bg=PALETA["panel"])
        exterior.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.form_scroll = exterior
        self.form_container = interior

        self.simple_widgets = {}
        self.list_widgets = {}

        for seccion in [
            "datos_generales",
            "objetivo_plan",
            "alcance",
            "descripcion_zona",
            "identificacion_riesgos",
            "organizacion_responsables",
            "recursos_disponibles",
            "rutas_evac",
            "procedimientos_actuacion",
            "simulacros",
            "revisiones",
        ]:
            panel = tk.LabelFrame(
                interior,
                text=ETIQUETAS_SECCIONES[seccion],
                bg=PALETA["panel_2"],
                fg=PALETA["fg"],
                bd=1,
                relief="solid",
                padx=12,
                pady=10,
                font=("Arial", 12, "bold"),
            )
            panel.pack(fill="x", expand=True, pady=(0, 12))

            if seccion in SECCIONES_FORM_SIMPLE:
                self._crear_seccion_simple(panel, seccion)
            else:
                self._crear_seccion_lista(panel, seccion)

    def _crear_seccion_simple(self, parent, seccion: str):
        self.simple_widgets[seccion] = {}
        for indice, (clave, multilinea) in enumerate(SECCIONES_FORM_SIMPLE[seccion]):
            columna = indice % 2
            fila = indice // 2
            self._crear_campo(parent, seccion, clave, multilinea, fila, columna)

    def _crear_campo(self, parent, seccion: str, clave: str, multilinea: bool, fila: int, columna: int):
        frame = tk.Frame(parent, bg=PALETA["panel_2"])
        frame.grid(row=fila, column=columna, sticky="nsew", padx=8, pady=6)
        parent.grid_columnconfigure(columna, weight=1)

        tk.Label(
            frame,
            text=_etiqueta_campo(clave),
            bg=PALETA["panel_2"],
            fg=PALETA["fg"],
            font=("Arial", 10, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        if multilinea:
            widget = tk.Text(
                frame,
                height=4,
                bg=PALETA["bg_alt"],
                fg=PALETA["fg"],
                insertbackground=PALETA["fg"],
                relief="flat",
                wrap="word",
                font=("Arial", 10),
            )
            widget.pack(fill="x", expand=True)
            self.simple_widgets[seccion][clave] = {"tipo": "text", "widget": widget}
        else:
            var = tk.StringVar()
            widget = tk.Entry(
                frame,
                textvariable=var,
                bg=PALETA["bg_alt"],
                fg=PALETA["fg"],
                insertbackground=PALETA["fg"],
                relief="flat",
                font=("Arial", 10),
            )
            widget.pack(fill="x", expand=True, ipady=4)
            self.simple_widgets[seccion][clave] = {"tipo": "entry", "var": var, "widget": widget}

    def _crear_seccion_lista(self, parent, seccion: str):
        barra = tk.Frame(parent, bg=PALETA["panel_2"])
        barra.pack(fill="x", pady=(0, 8))

        tk.Label(
            barra,
            text="Registros dinámicos",
            bg=PALETA["panel_2"],
            fg=PALETA["fg_dim"],
            font=("Arial", 10),
        ).pack(side="left")

        self._crear_boton(
            barra,
            "Agregar",
            lambda s=seccion: self._agregar_item_lista(s),
            PALETA["acento"],
        ).pack(side="right")

        contenedor = tk.Frame(parent, bg=PALETA["panel_2"])
        contenedor.pack(fill="x", expand=True)
        self.list_widgets[seccion] = {"contenedor": contenedor, "items": []}

    def _crear_item_lista(self, seccion: str, valores=None):
        valores = valores or {}
        info = self.list_widgets[seccion]
        indice = len(info["items"]) + 1

        frame = tk.Frame(
            info["contenedor"],
            bg=PALETA["bg_alt"],
            highlightthickness=1,
            highlightbackground=PALETA["borde"],
            padx=10,
            pady=10,
        )
        frame.pack(fill="x", expand=True, pady=(0, 8))

        superior = tk.Frame(frame, bg=PALETA["bg_alt"])
        superior.pack(fill="x", pady=(0, 8))

        titulo = tk.Label(
            superior,
            text=f"Registro {indice}",
            bg=PALETA["bg_alt"],
            fg=PALETA["fg"],
            font=("Arial", 11, "bold"),
        )
        titulo.pack(side="left")

        self._crear_boton(
            superior,
            "Quitar",
            lambda f=frame, s=seccion: self._quitar_item_lista(s, f),
            PALETA["danger"],
        ).pack(side="right")

        cuerpo = tk.Frame(frame, bg=PALETA["bg_alt"])
        cuerpo.pack(fill="x", expand=True)

        widgets = {"frame": frame, "titulo": titulo, "campos": {}}
        for idx, (clave, multilinea) in enumerate(SECCIONES_FORM_LISTA[seccion]):
            columna = idx % 2
            fila = idx // 2
            campo = tk.Frame(cuerpo, bg=PALETA["bg_alt"])
            campo.grid(row=fila, column=columna, sticky="nsew", padx=6, pady=5)
            cuerpo.grid_columnconfigure(columna, weight=1)

            tk.Label(
                campo,
                text=_etiqueta_campo(clave),
                bg=PALETA["bg_alt"],
                fg=PALETA["fg"],
                font=("Arial", 10, "bold"),
            ).pack(anchor="w", pady=(0, 4))

            if multilinea:
                widget = tk.Text(
                    campo,
                    height=3,
                    bg=PALETA["panel"],
                    fg=PALETA["fg"],
                    insertbackground=PALETA["fg"],
                    relief="flat",
                    wrap="word",
                    font=("Arial", 10),
                )
                widget.pack(fill="x", expand=True)
                widget.insert("1.0", valores.get(clave, ""))
                widgets["campos"][clave] = {"tipo": "text", "widget": widget}
            else:
                var = tk.StringVar(value=valores.get(clave, ""))
                widget = tk.Entry(
                    campo,
                    textvariable=var,
                    bg=PALETA["panel"],
                    fg=PALETA["fg"],
                    insertbackground=PALETA["fg"],
                    relief="flat",
                    font=("Arial", 10),
                )
                widget.pack(fill="x", expand=True, ipady=4)
                widgets["campos"][clave] = {"tipo": "entry", "var": var, "widget": widget}

        info["items"].append(widgets)
        self._renumerar_items_lista(seccion)

    def _agregar_item_lista(self, seccion: str):
        self._crear_item_lista(seccion, {})

    def _quitar_item_lista(self, seccion: str, frame):
        info = self.list_widgets[seccion]
        info["items"] = [item for item in info["items"] if item["frame"] != frame]
        try:
            frame.destroy()
        except Exception:
            pass
        self._renumerar_items_lista(seccion)

    def _renumerar_items_lista(self, seccion: str):
        for indice, item in enumerate(self.list_widgets[seccion]["items"], start=1):
            item["titulo"].config(text=f"Registro {indice}")

    def _crear_boton(self, parent, texto, comando, color):
        return tk.Button(
            parent,
            text=texto,
            command=comando,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            font=("Arial", 10, "bold"),
            cursor="hand2",
        )

    def _cargar_planes(self):
        self.planes = [resumen_plan(plan) for plan in listar_planes()]
        self.tree_planes.delete(*self.tree_planes.get_children())
        for plan in self.planes:
            estado = "Guardado" if plan["estado"] == "guardado" else "Borrador"
            fecha = plan["fecha_actualizacion"][:16]
            self.tree_planes.insert(
                "",
                "end",
                iid=plan["id"],
                text=plan["titulo"],
                values=(estado, plan["escenario_principal"], fecha),
            )
        self.lbl_estado.config(text=f"{len(self.planes)} plan(es) registrados.")

    def _al_seleccionar_plan(self, _event=None):
        seleccion = self.tree_planes.selection()
        if not seleccion:
            return
        plan_id = seleccion[0]
        planes = {plan["id"]: plan for plan in listar_planes()}
        plan = planes.get(plan_id)
        if not plan:
            return
        self.plan_actual = plan
        self.plan_actual_id = plan["id"]
        if plan.get("estado") == "guardado":
            self._mostrar_plan(plan, modo="view")
        else:
            self._mostrar_plan(plan, modo="edit")

    def _mostrar_plan(self, plan, modo="view"):
        self.plan_actual = normalizar_plan(plan)
        self.plan_actual_id = self.plan_actual["id"]
        self.modo_actual = modo

        self.lbl_titulo_detalle.config(text=titulo_plan(self.plan_actual))
        estado = "guardado" if self.plan_actual.get("estado") == "guardado" else "borrador"
        self.lbl_detalle_estado.config(
            text=f"Estado: {estado}. "
            f"Escenario principal: {self.plan_actual['datos_generales'].get('escenario_principal', '-') or '-'}"
        )

        if modo == "edit":
            self.preview_wrap.grid_forget()
            self.form_wrap.grid(row=0, column=0, sticky="nsew")
            self._cargar_plan_en_formulario(self.plan_actual)
        else:
            self.form_wrap.grid_forget()
            self.preview_wrap.grid(row=0, column=0, sticky="nsew")
            self._cargar_preview(self.plan_actual)

        self._actualizar_botones()

    def _mostrar_estado_vacio(self):
        self.plan_actual = None
        self.plan_actual_id = None
        self.modo_actual = "vacio"
        self.form_wrap.grid_forget()
        self.preview_wrap.grid_forget()
        self.lbl_titulo_detalle.config(text="Sin selección")
        self.lbl_detalle_estado.config(text="Crea un plan nuevo o selecciona uno existente para consultarlo.")
        self._actualizar_botones()

    def _nuevo_plan(self):
        plan = crear_plan_vacio()
        self._mostrar_plan(plan, modo="edit")

    def _cargar_plan_en_formulario(self, plan):
        plan = normalizar_plan(plan)
        for seccion, campos in self.simple_widgets.items():
            valores = plan.get(seccion, {})
            for clave, meta in campos.items():
                if meta["tipo"] == "entry":
                    meta["var"].set(valores.get(clave, ""))
                else:
                    meta["widget"].delete("1.0", "end")
                    meta["widget"].insert("1.0", valores.get(clave, ""))

        for seccion in self.list_widgets:
            cont = self.list_widgets[seccion]
            for item in list(cont["items"]):
                try:
                    item["frame"].destroy()
                except Exception:
                    pass
            cont["items"] = []
            for fila in plan.get(seccion, []):
                self._crear_item_lista(seccion, fila)

    def _leer_formulario(self):
        base = deepcopy(self.plan_actual or crear_plan_vacio())
        for seccion, campos in self.simple_widgets.items():
            base[seccion] = {}
            for clave, meta in campos.items():
                if meta["tipo"] == "entry":
                    base[seccion][clave] = meta["var"].get().strip()
                else:
                    base[seccion][clave] = meta["widget"].get("1.0", "end").strip()

        for seccion, info in self.list_widgets.items():
            base[seccion] = []
            claves = SECCIONES_LISTA[seccion]
            for item in info["items"]:
                fila = {}
                tiene_contenido = False
                for clave in claves:
                    meta = item["campos"][clave]
                    valor = meta["var"].get().strip() if meta["tipo"] == "entry" else meta["widget"].get("1.0", "end").strip()
                    fila[clave] = valor
                    if valor:
                        tiene_contenido = True
                if tiene_contenido:
                    base[seccion].append(fila)

        return normalizar_plan(base)

    def _guardar_borrador(self):
        self._guardar("borrador")

    def _guardar_final(self):
        self._guardar("guardado")

    def _guardar(self, estado_destino: str):
        try:
            plan = self._leer_formulario()
            guardado = guardar_plan(plan, estado_destino=estado_destino)
        except ValueError as exc:
            messagebox.showwarning("Revisa el plan", str(exc), parent=self.root)
            return
        except Exception as exc:
            messagebox.showerror("Planes", f"No se pudo guardar el plan.\n\nDetalle: {exc}", parent=self.root)
            return

        self._cargar_planes()
        self.plan_actual = guardado
        self.plan_actual_id = guardado["id"]
        if guardado["id"] in self.tree_planes.get_children():
            self.tree_planes.selection_set(guardado["id"])
            self.tree_planes.focus(guardado["id"])
            self.tree_planes.see(guardado["id"])

        if estado_destino == "guardado":
            self._mostrar_plan(guardado, modo="view")
            messagebox.showinfo("Planes", "Plan guardado correctamente.", parent=self.root)
        else:
            self._mostrar_plan(guardado, modo="edit")
            messagebox.showinfo("Planes", "Borrador guardado correctamente.", parent=self.root)

    def _editar_plan(self):
        if not self.plan_actual:
            return
        if self.modo_actual == "edit":
            return
        self._mostrar_plan(self.plan_actual, modo="edit")

    def _visualizar_plan(self):
        if not self.plan_actual:
            return
        if self.modo_actual == "edit":
            plan = self._leer_formulario()
        else:
            plan = self.plan_actual
        self._mostrar_plan(plan, modo="view")

    def _cargar_preview(self, plan):
        contenido = renderizar_plan_texto(plan)
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", contenido)
        self.preview_text.config(state="disabled")
        self.preview_text.yview_moveto(0)

    def _exportar_plan(self):
        if not self.plan_actual:
            messagebox.showwarning("Planes", "Selecciona o crea un plan antes de exportarlo.", parent=self.root)
            return
        plan = self._leer_formulario() if self.modo_actual == "edit" else self.plan_actual
        nombre = titulo_plan(plan).replace("/", "-").replace("\\", "-")
        ruta = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar plan",
            defaultextension=".txt",
            initialfile=f"{nombre}.txt",
            filetypes=[("Texto", "*.txt")],
        )
        if not ruta:
            return
        try:
            exportar_plan_texto(plan, Path(ruta))
            messagebox.showinfo("Planes", f"Plan exportado en:\n{ruta}", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Planes", f"No se pudo exportar el plan.\n\nDetalle: {exc}", parent=self.root)

    def _eliminar_plan_ui(self):
        if not self.plan_actual_id:
            return
        if not messagebox.askyesno(
            "Eliminar plan",
            "Se eliminará el plan seleccionado. Esta acción no se puede deshacer desde la interfaz.\n\n¿Deseas continuar?",
            parent=self.root,
        ):
            return
        try:
            ok = eliminar_plan(self.plan_actual_id)
        except Exception as exc:
            messagebox.showerror("Planes", f"No se pudo eliminar el plan.\n\nDetalle: {exc}", parent=self.root)
            return
        if not ok:
            messagebox.showwarning("Planes", "No se encontró el plan para eliminar.", parent=self.root)
            return
        self._cargar_planes()
        self._mostrar_estado_vacio()

    def _actualizar_botones(self):
        hay_plan = self.plan_actual is not None
        en_edicion = self.modo_actual == "edit"
        guardado = bool(hay_plan and self.plan_actual.get("estado") == "guardado")

        self.btn_guardar_borrador.config(state="normal" if en_edicion else "disabled")
        self.btn_guardar.config(state="normal" if en_edicion else "disabled")
        self.btn_editar.config(state="normal" if hay_plan and not en_edicion else "disabled")
        self.btn_visualizar.config(state="normal" if hay_plan and not (guardado and self.modo_actual == "view") else "disabled")
        self.btn_exportar.config(state="normal" if hay_plan else "disabled")
        self.btn_eliminar.config(state="normal" if bool(self.plan_actual_id) and self.plan_actual_id in self.tree_planes.get_children() else "disabled")
