import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from core.catalogo_dominios import inferir_dominio_desde_texto
from core.consulta import limpiar_contexto_conversacion, transmitir_consulta_local_rapida
from core.consulta_avanzada import (
    indexar_documento,
    listar_documentos_indexados,
    runtime_local_esta_disponible,
)
from core.dominios import agregar_dominio, corregir_nombre_dominio, listar_dominios_ui
from core.ui_theme import FUTURISTA_OSCURO
from core.window_geometry import aplicar_geometria_relativa, crear_contenedor_scrollable


class VentanaConsulta(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.ui = FUTURISTA_OSCURO
        self.session_id = "ventana-consulta"
        self._session_nonce = 0
        self.title("TLAMATINI IA - Consulta")
        self.configure(bg=self.ui["fondo"])
        self.minsize(980, 640)

        self.archivo_pendiente = ""
        self._dialogo_carga = None
        self.ultimo_documento_agregado = ""
        self._panel_derecho_ancho = 260
        self.frame_der = None
        self.lista_docs = None
        self.label_confirmacion_visual = None
        self._dominios_ui = []
        self._consulta_activa_id = 0
        self._prueba_activa_id = 0
        self._consultas_con_stream = set()
        self._after_contexto_id = None

        self._ajustar_a_pantalla()
        self._crear_interfaz()
        self._actualizar_estado_motor_local()
        self.after(120, self._ajustar_paneles)

    def _ajustar_a_pantalla(self):
        aplicar_geometria_relativa(self, self.master, rel_w=0.92, rel_h=0.9, min_w=980, min_h=640)

    def _crear_interfaz(self):
        _, _, contenido = crear_contenedor_scrollable(self, bg=self.ui["fondo"])
        contenido.grid_columnconfigure(0, weight=1)
        contenido.grid_rowconfigure(1, weight=1)

        encabezado = tk.Frame(contenido, bg=self.ui["fondo"])
        encabezado.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        encabezado.grid_columnconfigure(0, weight=1)

        bloque_titulo = tk.Frame(encabezado, bg=self.ui["fondo"])
        bloque_titulo.grid(row=0, column=0, sticky="ew")

        tk.Label(
            bloque_titulo,
            text="CONSULTA",
            font=("Arial", 22, "bold"),
            bg=self.ui["fondo"],
            fg=self.ui["texto"],
        ).pack(anchor="w")

        acciones = tk.Frame(encabezado, bg=self.ui["fondo"])
        acciones.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.label_estado_motor_local = tk.Label(
            acciones,
            text="",
            font=("Arial", 10, "bold"),
            bg=self.ui["fondo"],
            fg="#22C55E",
        )
        self.label_estado_motor_local.pack(side="left")

        cuerpo = tk.Frame(contenido, bg=self.ui["fondo"])
        cuerpo.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.cuerpo = cuerpo

        frame_izq = tk.Frame(cuerpo, bg=self.ui["fondo"])
        frame_izq.pack(fill="both", expand=True)

        frame_izq.grid_rowconfigure(1, weight=1)
        frame_izq.grid_columnconfigure(0, weight=1)

        tarjeta_pregunta = tk.Frame(frame_izq, bg=self.ui["panel"], highlightbackground=self.ui["borde"], highlightthickness=1)
        tarjeta_pregunta.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tarjeta_pregunta.grid_columnconfigure(0, weight=1)

        self.entrada_pregunta = tk.Text(
            tarjeta_pregunta,
            height=5,
            wrap="word",
            font=("Arial", 12),
            bg=self.ui["panel_3"],
            fg=self.ui["texto"],
            insertbackground=self.ui["texto"],
            relief="flat",
            padx=10,
            pady=10,
        )
        self.entrada_pregunta.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 12))
        self.entrada_pregunta.bind("<Control-Return>", lambda _e: self.realizar_consulta())

        barra_botones = tk.Frame(tarjeta_pregunta, bg=self.ui["panel"])
        barra_botones.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        barra_botones.grid_columnconfigure(2, weight=1)

        self.boton_consultar = tk.Button(
            barra_botones,
            text="Consultar",
            font=("Arial", 11, "bold"),
            bg=self.ui["panel_2"],
            fg=self.ui["texto"],
            activebackground=self.ui["borde"],
            activeforeground=self.ui["texto"],
            relief="flat",
            padx=16,
            pady=9,
            command=self.realizar_consulta,
        )
        self.boton_consultar.grid(row=0, column=0, sticky="w", padx=(0, 8))

        tk.Button(
            barra_botones,
            text="Limpiar",
            font=("Arial", 11, "bold"),
            bg=self.ui["panel_3"],
            fg=self.ui["texto"],
            activebackground=self.ui["panel_2"],
            activeforeground=self.ui["texto"],
            relief="flat",
            padx=14,
            pady=9,
            command=self.limpiar_campos,
        ).grid(row=0, column=1, sticky="w")

        self.label_estado_consulta = tk.Label(
            barra_botones,
            text="",
            font=("Arial", 10, "bold"),
            bg=self.ui["panel"],
            fg="#FBBF24",
        )
        self.label_estado_consulta.grid(row=0, column=2, sticky="e")

        tarjeta_salida = tk.Frame(frame_izq, bg=self.ui["panel"], highlightbackground=self.ui["borde"], highlightthickness=1)
        tarjeta_salida.grid(row=1, column=0, sticky="nsew")
        tarjeta_salida.grid_rowconfigure(1, weight=1)
        tarjeta_salida.grid_columnconfigure(0, weight=1)

        tab_respuesta = tk.Frame(tarjeta_salida, bg=self.ui["panel_3"])
        tab_respuesta.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self.area_respuesta = self._crear_area_texto(tab_respuesta, self.ui["panel_3"], self.ui["texto"])

        self._mostrar_respuesta("")

    def _ajustar_paneles(self):
        return

    def _session_id_vigente(self) -> str:
        return f"{self.session_id}-{self._session_nonce}"

    def _crear_area_texto(self, parent, bg, fg):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        area = tk.Text(
            parent,
            wrap="word",
            font=("Arial", 13),
            bg=bg,
            fg=fg,
            insertbackground="white",
            relief="flat",
            padx=16,
            pady=16,
            spacing1=4,
            spacing2=2,
            spacing3=8,
        )
        area.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=area.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        area.configure(yscrollcommand=scroll.set)
        area.config(state="disabled")
        area.tag_configure("titulo", font=("Arial", 15, "bold"), foreground="#F8FAFC", spacing1=8, spacing3=10)
        area.tag_configure("subtitulo", font=("Arial", 14, "bold"), foreground="#93C5FD", spacing1=6, spacing3=6)
        area.tag_configure("normal", font=("Arial", 13), foreground=fg)
        area.tag_configure("referencia", font=("Arial", 12), foreground="#FCD34D", spacing1=4, spacing3=6)
        return area

    def _actualizar_estado_motor_local(self):
        ok, _mensaje = runtime_local_esta_disponible()
        if ok:
            self.label_estado_motor_local.config(text="IA local disponible", fg="#22C55E")
            self.title("TLAMATINI IA - Consulta")
        else:
            self.label_estado_motor_local.config(text="IA local no disponible", fg="#EF4444")
            self.title("TLAMATINI IA - Consulta (motor no disponible)")

    def _nombre_dominio(self, valor: str) -> str:
        valor_n = (valor or "").strip().lower()
        for dominio in self._obtener_dominios_ui():
            if dominio["nombre"] == valor_n:
                return dominio["etiqueta"]
        limpio = (valor or "general").replace("_", " ").strip()
        return " ".join(parte.capitalize() for parte in limpio.split()) or "General"

    def _obtener_dominios_ui(self):
        self._dominios_ui = listar_dominios_ui(include_general=True)
        return self._dominios_ui

    def _dominio_por_etiqueta(self, etiqueta: str):
        etiqueta_n = (etiqueta or "").strip().lower()
        for dominio in self._obtener_dominios_ui():
            if dominio["etiqueta"].lower() == etiqueta_n:
                return dominio
        return next((dominio for dominio in self._obtener_dominios_ui() if dominio["nombre"] == "general"), None)

    def _refrescar_combo_dominios(self, seleccionar: str = ""):
        if not hasattr(self, "combo_dominio") or not self.combo_dominio:
            return
        dominios = self._obtener_dominios_ui()
        etiquetas = [dominio["etiqueta"] for dominio in dominios]
        self.combo_dominio.configure(values=etiquetas)
        dominio_obj = self._dominio_por_etiqueta(seleccionar) if seleccionar else None
        if dominio_obj is None and seleccionar:
            dominio_obj = next((dominio for dominio in dominios if dominio["nombre"] == seleccionar), None)
        if dominio_obj is None:
            dominio_obj = next((dominio for dominio in dominios if dominio["nombre"] in {"medica", "medicina"}), None)
        if dominio_obj is None and dominios:
            dominio_obj = dominios[0]
        if dominio_obj:
            self.combo_dominio.set(dominio_obj["etiqueta"])
        self._actualizar_ayuda_subdominio()

    def _cargar_documentos_en_lista(self):
        if not self.lista_docs:
            return
        docs = listar_documentos_indexados()
        agrupados = {}
        for doc in docs:
            dominio = self._nombre_dominio(doc.get("dominio", "general"))
            agrupados.setdefault(dominio, []).append(doc)

        self.lista_docs.config(state="normal")
        self.lista_docs.delete("1.0", "end")

        if not agrupados:
            self.lista_docs.insert("1.0", "Aún no hay documentos cargados.")
            self.lista_docs.config(state="disabled")
            return

        lineas = []
        for dominio in sorted(agrupados.keys()):
            lineas.append(f"{dominio}")
            lineas.append("-" * len(dominio))
            for doc in sorted(agrupados[dominio], key=lambda item: item.get("fecha_carga", ""), reverse=True):
                subdominio = doc.get("subdominio", "general") or "general"
                marca = " [NUEVO]" if doc.get("nombre", "") == self.ultimo_documento_agregado else ""
                lineas.append(f"• {doc['nombre']}{marca}")
                lineas.append(f"  {subdominio} | {doc['paginas']} pág.")
            lineas.append("")

        self.lista_docs.insert("1.0", "\n".join(lineas).strip())
        self.lista_docs.config(state="disabled")

    def abrir_dialogo_carga(self):
        if self._dialogo_carga and self._dialogo_carga.winfo_exists():
            self._dialogo_carga.deiconify()
            self._dialogo_carga.lift()
            self._dialogo_carga.focus_force()
            return

        self._dialogo_carga = tk.Toplevel(self)
        self._dialogo_carga.title("Agregar documento")
        self._dialogo_carga.configure(bg="#0F172A")
        self._dialogo_carga.minsize(620, 420)
        self._dialogo_carga.resizable(True, True)
        self._dialogo_carga.transient(self)
        self._dialogo_carga.lift()
        self._dialogo_carga.focus_force()
        self._dialogo_carga.grid_rowconfigure(0, weight=1)
        self._dialogo_carga.grid_columnconfigure(0, weight=1)

        ancho = min(760, max(620, int(self.winfo_width() * 0.54)))
        alto = min(520, max(420, int(self.winfo_height() * 0.56)))
        pos_x = self.winfo_rootx() + max(20, (self.winfo_width() - ancho) // 2)
        pos_y = self.winfo_rooty() + max(20, (self.winfo_height() - alto) // 3)
        self._dialogo_carga.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")

        contenedor = tk.Frame(self._dialogo_carga, bg="#0F172A")
        contenedor.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        contenedor.grid_rowconfigure(5, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        tk.Label(
            contenedor,
            text="Agregar documento",
            font=("Arial", 18, "bold"),
            bg="#0F172A",
            fg="white",
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            contenedor,
            text="Selecciona el archivo y asígnalo al dominio correcto para mejorar la precisión de TLAMATINI.",
            font=("Arial", 10),
            bg="#0F172A",
            fg="#CBD5E1",
            justify="left",
            wraplength=650,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 14))

        fila_archivo = tk.Frame(contenedor, bg="#0F172A")
        fila_archivo.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        fila_archivo.grid_columnconfigure(0, weight=1)

        self.label_archivo = tk.Label(
            fila_archivo,
            text="Ningún archivo seleccionado",
            font=("Arial", 10),
            bg="#111827",
            fg="#E2E8F0",
            anchor="w",
            padx=10,
            pady=9,
        )
        self.label_archivo.grid(row=0, column=0, sticky="ew")

        tk.Button(
            fila_archivo,
            text="Buscar...",
            font=("Arial", 10, "bold"),
            bg="#334155",
            fg="white",
            activebackground="#475569",
            activeforeground="white",
            relief="flat",
            command=self._seleccionar_archivo_para_carga,
        ).grid(row=0, column=1, padx=(8, 0))

        fila_dominio = tk.Frame(contenedor, bg="#0F172A")
        fila_dominio.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        fila_dominio.grid_columnconfigure(0, weight=1)
        fila_dominio.grid_columnconfigure(1, weight=1)

        tk.Label(fila_dominio, text="Dominio", font=("Arial", 10, "bold"), bg="#0F172A", fg="white").grid(row=0, column=0, sticky="w")

        self.combo_dominio = ttk.Combobox(
            fila_dominio,
            values=[],
            state="readonly",
            width=28,
        )
        self.combo_dominio.grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.combo_dominio.bind("<<ComboboxSelected>>", self._actualizar_ayuda_subdominio)

        fila_botones_dominio = tk.Frame(fila_dominio, bg="#0F172A")
        fila_botones_dominio.grid(row=2, column=0, sticky="w", pady=(8, 0))

        tk.Button(
            fila_botones_dominio,
            text="Añadir dominio",
            font=("Arial", 9, "bold"),
            bg="#1D4ED8",
            fg="white",
            activebackground="#1E40AF",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=6,
            command=self._agregar_dominio_desde_dialogo,
        ).pack(side="left")

        tk.Button(
            fila_botones_dominio,
            text="Corregir nombre",
            font=("Arial", 9, "bold"),
            bg="#475569",
            fg="white",
            activebackground="#334155",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=6,
            command=self._corregir_dominio_desde_dialogo,
        ).pack(side="left", padx=(8, 0))

        tk.Label(fila_dominio, text="Subdominio o especialidad", font=("Arial", 10, "bold"), bg="#0F172A", fg="white").grid(row=0, column=1, sticky="w", padx=(18, 0))

        self.entry_subdominio = tk.Entry(fila_dominio, font=("Arial", 10), width=30)
        self.entry_subdominio.insert(0, "general")
        self.entry_subdominio.grid(row=1, column=1, sticky="w", padx=(18, 0), pady=(5, 0))

        self.label_subdominio = tk.Label(
            contenedor,
            text="Sugerencias: fisiologia, farmacologia, procedimientos, urgencias",
            font=("Arial", 10),
            bg="#0F172A",
            fg="#93C5FD",
            justify="left",
            wraplength=650,
        )
        self.label_subdominio.grid(row=4, column=0, sticky="ew", pady=(0, 18))

        self.label_dominio_sugerido = tk.Label(
            contenedor,
            text="Dominio sugerido: esperando archivo",
            font=("Arial", 10),
            bg="#0F172A",
            fg="#FBBF24",
            justify="left",
            wraplength=650,
        )
        self.label_dominio_sugerido.grid(row=5, column=0, sticky="ew", pady=(0, 10))

        self.label_estado_carga = tk.Label(
            contenedor,
            text="",
            font=("Arial", 10, "bold"),
            bg="#0F172A",
            fg="#86EFAC",
            justify="left",
            wraplength=650,
        )
        self.label_estado_carga.grid(row=6, column=0, sticky="new", pady=(0, 10))

        fila_acciones = tk.Frame(contenedor, bg="#0F172A")
        fila_acciones.grid(row=7, column=0, sticky="ew", pady=(8, 0))

        self.boton_confirmar_carga = tk.Button(
            fila_acciones,
            text="Agregar documento",
            font=("Arial", 10, "bold"),
            bg="#0F766E",
            fg="white",
            activebackground="#115E59",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=9,
            command=self.cargar_documento,
        )
        self.boton_confirmar_carga.pack(side="left")

        tk.Button(
            fila_acciones,
            text="Cancelar",
            font=("Arial", 10, "bold"),
            bg="#475569",
            fg="white",
            activebackground="#334155",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=9,
            command=self._cerrar_dialogo_carga,
        ).pack(side="left", padx=(8, 0))

        self.archivo_pendiente = ""
        self._refrescar_combo_dominios("medica")
        self._actualizar_ayuda_subdominio()
        self._actualizar_sugerencia_dominio_archivo("")
        self._mostrar_estado_carga("")

    def _cerrar_dialogo_carga(self):
        if self._dialogo_carga and self._dialogo_carga.winfo_exists():
            self._dialogo_carga.destroy()
        self._dialogo_carga = None
        self.archivo_pendiente = ""

    def _seleccionar_archivo_para_carga(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar documento",
            filetypes=[
                ("Documentos compatibles", "*.pdf *.txt *.md *.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not ruta:
            if self._dialogo_carga and self._dialogo_carga.winfo_exists():
                self._dialogo_carga.deiconify()
                self._dialogo_carga.lift()
                self._dialogo_carga.focus_force()
            return

        self.archivo_pendiente = ruta
        nombre = ruta.split("/")[-1]
        self.label_archivo.config(text=nombre)
        sugerencia = inferir_dominio_desde_texto(nombre, include_possible=True)
        dominio_operativo = str(sugerencia.get("operational_domain", "") or "")
        if dominio_operativo:
            self._refrescar_combo_dominios(dominio_operativo)
        self._actualizar_sugerencia_dominio_archivo(nombre)
        self._mostrar_estado_carga("Archivo seleccionado. Ya puedes agregarlo.", "#93C5FD")
        if self._dialogo_carga and self._dialogo_carga.winfo_exists():
            self._dialogo_carga.deiconify()
            self._dialogo_carga.lift()
            self._dialogo_carga.focus_force()

    def _actualizar_sugerencia_dominio_archivo(self, texto: str):
        if not self._dialogo_carga or not self._dialogo_carga.winfo_exists() or not hasattr(self, "label_dominio_sugerido"):
            return
        sugerencia = inferir_dominio_desde_texto(texto, include_possible=True) if texto else {}
        dominio = str(sugerencia.get("domain", "") or "")
        operativo = str(sugerencia.get("operational_domain", "") or "")
        if dominio:
            self.label_dominio_sugerido.config(
                text=f"Dominio sugerido: {dominio} | Dominio operativo: {operativo or dominio}",
                fg="#FBBF24",
            )
        else:
            self.label_dominio_sugerido.config(
                text="Dominio sugerido: sin coincidencias claras",
                fg="#94A3B8",
            )

    def _programar_actualizacion_contexto(self, _evento=None):
        return

    def _actualizar_contexto_consulta(self):
        return

    def _actualizar_ayuda_subdominio(self, _evento=None):
        dominio = self._dominio_por_etiqueta(self.combo_dominio.get().strip())
        sugerencias = dominio.get("subdominios", []) if dominio else []
        sugerencia = ", ".join(sugerencias) if sugerencias else "general"
        self.label_subdominio.config(text=f"Sugerencias: {sugerencia}")

    def _obtener_clave_dominio(self) -> str:
        dominio = self._dominio_por_etiqueta(self.combo_dominio.get().strip())
        return (dominio or {}).get("nombre", "general")

    def _agregar_dominio_desde_dialogo(self):
        parent = self._dialogo_carga or self
        nombre = simpledialog.askstring("Añadir dominio", "Nombre del nuevo dominio:", parent=parent)
        if nombre is None:
            return
        descripcion = simpledialog.askstring(
            "Descripción del dominio",
            "Descripción breve del dominio:",
            parent=parent,
            initialvalue=f"Dominio {nombre.strip()}",
        )
        subdominios_texto = simpledialog.askstring(
            "Subdominios",
            "Subdominios sugeridos separados por comas:",
            parent=parent,
            initialvalue="general",
        )
        subdominios = [item.strip() for item in (subdominios_texto or "").split(",") if item.strip()]
        resultado = agregar_dominio(nombre, descripcion=descripcion or "", subdominios=subdominios)
        if not resultado.get("ok"):
            messagebox.showerror("No se pudo agregar", resultado.get("mensaje", "No se pudo agregar el dominio."), parent=parent)
            return
        nuevo_nombre = (resultado.get("dominio") or {}).get("nombre", "")
        self._refrescar_combo_dominios(nuevo_nombre)
        self._mostrar_estado_carga(resultado.get("mensaje", "Dominio agregado correctamente."), "#86EFAC")
        self._cargar_documentos_en_lista()

    def _corregir_dominio_desde_dialogo(self):
        parent = self._dialogo_carga or self
        dominio_actual = self._obtener_clave_dominio()
        if dominio_actual == "general":
            messagebox.showwarning("No editable", "El dominio general no se puede corregir.", parent=parent)
            return
        nuevo_nombre = simpledialog.askstring(
            "Corregir dominio",
            "Escribe el nombre corregido del dominio:",
            parent=parent,
            initialvalue=dominio_actual,
        )
        if nuevo_nombre is None:
            return
        resultado = corregir_nombre_dominio(dominio_actual, nuevo_nombre)
        if not resultado.get("ok"):
            messagebox.showerror("No se pudo corregir", resultado.get("mensaje", "No se pudo corregir el dominio."), parent=parent)
            return
        nombre_actualizado = (resultado.get("dominio") or {}).get("nombre", "")
        self._refrescar_combo_dominios(nombre_actualizado)
        self._mostrar_estado_carga(resultado.get("mensaje", "Dominio corregido correctamente."), "#86EFAC")
        self._cargar_documentos_en_lista()

    def cargar_documento(self):
        if not self.archivo_pendiente:
            messagebox.showwarning("Falta archivo", "Selecciona un archivo para cargar.", parent=self._dialogo_carga or self)
            return

        dominio = self._obtener_clave_dominio()
        subdominio = self.entry_subdominio.get().strip() or "general"

        self.boton_menu.config(state="disabled")
        if self._dialogo_carga and self._dialogo_carga.winfo_exists():
            self.boton_confirmar_carga.config(state="disabled", text="Indexando...")
        self._mostrar_estado_carga("Indexando documento...", "#FBBF24")
        self._dialogo_carga.lift()
        self._dialogo_carga.focus_force()

        self._mostrar_respuesta("Indexando documento, espera un momento...")

        hilo = threading.Thread(
            target=self._indexar_en_segundo_plano,
            args=(self.archivo_pendiente, dominio, subdominio),
            daemon=True,
        )
        hilo.start()

    def _indexar_en_segundo_plano(self, ruta, dominio, subdominio):
        try:
            resultado = indexar_documento(ruta, dominio=dominio, subdominio=subdominio)
        except Exception as e:
            resultado = {"ok": False, "mensaje": str(e)}

        self.after(0, lambda: self._finalizar_indexado(resultado))

    def _finalizar_indexado(self, resultado):
        self.boton_menu.config(state="normal")

        if self._dialogo_carga and self._dialogo_carga.winfo_exists():
            self.boton_confirmar_carga.config(state="normal", text="Agregar documento")

        if resultado.get("ok"):
            mensaje = resultado.get("mensaje", "Documento cargado.")
            libro = resultado.get("libro") or {}
            self.ultimo_documento_agregado = libro.get("nombre", "") or self.archivo_pendiente.split("/")[-1]
            self._cargar_documentos_en_lista()
            self._mostrar_respuesta(
                f"{mensaje}\nFragmentos generados: {resultado.get('fragmentos', 0)}"
            )
            self._mostrar_estado_carga(f"Documento agregado correctamente. Fragmentos generados: {resultado.get('fragmentos', 0)}", "#86EFAC")
            if self.label_confirmacion_visual:
                self.label_confirmacion_visual.config(
                    text=f"Ultimo documento agregado: {self.ultimo_documento_agregado}\nYa aparece en la biblioteca cargada."
                )
            self.archivo_pendiente = ""
            if self._dialogo_carga and self._dialogo_carga.winfo_exists():
                self.label_archivo.config(text="Ningún archivo seleccionado")
                self._dialogo_carga.lift()
                self._dialogo_carga.focus_force()
        else:
            mensaje = resultado.get("mensaje", "No se pudo indexar el documento.")
            self._mostrar_respuesta(mensaje)
            self._mostrar_estado_carga(mensaje, "#FCA5A5")
            if self.label_confirmacion_visual:
                self.label_confirmacion_visual.config(text=f"Error al agregar documento: {mensaje}", fg="#FCA5A5")
            if self._dialogo_carga and self._dialogo_carga.winfo_exists():
                self._dialogo_carga.lift()
                self._dialogo_carga.focus_force()

    def realizar_consulta(self):
        pregunta = self.entrada_pregunta.get("1.0", "end").strip()
        if not pregunta:
            messagebox.showwarning("Pregunta vacía", "Escribe una pregunta.", parent=self)
            return

        self._consulta_activa_id += 1
        consulta_id = self._consulta_activa_id
        self._consultas_con_stream.discard(consulta_id)
        session_id_actual = self._session_id_vigente()
        self._mostrar_respuesta("Consultando...")
        self._establecer_estado_consulta("Consultando...", "#FBBF24", en_progreso=True)

        hilo = threading.Thread(
            target=self._consultar_en_segundo_plano,
            args=(pregunta, consulta_id, session_id_actual),
            daemon=True,
        )
        hilo.start()

    def _consultar_en_segundo_plano(self, pregunta, consulta_id, session_id_actual):
        try:
            self.after(0, lambda: self._preparar_respuesta_stream_si_vigente(consulta_id))
            respuesta = transmitir_consulta_local_rapida(
                pregunta=pregunta,
                on_chunk=lambda chunk: self.after(
                    0,
                    lambda c=chunk: self._append_respuesta_stream_si_vigente(consulta_id, c),
                ),
                session_id=session_id_actual,
            )
        except Exception as e:
            respuesta = f"Ocurrió un error durante la consulta:\n{e}"

        self.after(0, lambda: self._finalizar_consulta_si_vigente(consulta_id, respuesta))

    def _finalizar_consulta_si_vigente(self, consulta_id: int, respuesta: str):
        if consulta_id != self._consulta_activa_id:
            return
        if (respuesta or "").startswith("Ocurrió un error durante la consulta:"):
            self._establecer_estado_consulta("Error en consulta", "#FCA5A5", en_progreso=False)
            self._mostrar_respuesta(respuesta)
        else:
            self._establecer_estado_consulta("", "#86EFAC", en_progreso=False)
            if consulta_id not in self._consultas_con_stream:
                self._mostrar_respuesta(respuesta)
        self._consultas_con_stream.discard(consulta_id)

    def _mostrar_respuesta(self, texto: str):
        self.area_respuesta.config(state="normal")
        self.area_respuesta.delete("1.0", "end")
        self._insertar_respuesta_formateada(texto)
        self.area_respuesta.config(state="disabled")

    def _insertar_respuesta_formateada(self, texto: str):
        lineas = (texto or "").splitlines()
        if not lineas and texto:
            lineas = [texto]
        for idx, linea in enumerate(lineas):
            contenido = linea + ("\n" if idx < len(lineas) - 1 else "")
            linea_n = linea.strip().lower()
            if linea.strip() in {"Respuesta 1:", "Respuesta 2:", "Referencias:"}:
                self.area_respuesta.insert("end", contenido, "titulo")
            elif linea_n.startswith(("definición:", "signos y síntomas:", "diagnóstico o asociación:", "tratamiento o manejo:", "complicaciones o alarma:", "indicaciones o uso:", "dosis:", "vía o administración:", "contraindicaciones o precauciones:", "efectos adversos o riesgos:", "asociación más probable:", "dato complementario:", "signos de alarma:")):
                self.area_respuesta.insert("end", contenido, "subtitulo")
            elif linea.strip().startswith("- "):
                self.area_respuesta.insert("end", contenido, "referencia")
            else:
                self.area_respuesta.insert("end", contenido, "normal")

    def _preparar_respuesta_stream_si_vigente(self, consulta_id: int):
        if consulta_id != self._consulta_activa_id:
            return
        self.area_respuesta.config(state="normal")
        self.area_respuesta.delete("1.0", "end")
        self.area_respuesta.config(state="disabled")

    def _append_respuesta_stream_si_vigente(self, consulta_id: int, texto: str):
        if consulta_id != self._consulta_activa_id or not texto:
            return
        self._consultas_con_stream.add(consulta_id)
        self._establecer_estado_consulta("Respondiendo...", "#93C5FD", en_progreso=True)
        self.area_respuesta.config(state="normal")
        self.area_respuesta.insert("end", texto, "normal")
        self.area_respuesta.see("end")
        self.area_respuesta.config(state="disabled")

    def _establecer_estado_consulta(self, texto: str, color: str, en_progreso: bool):
        if hasattr(self, "label_estado_consulta") and self.label_estado_consulta:
            self.label_estado_consulta.config(text=texto, fg=color)
        if hasattr(self, "boton_consultar") and self.boton_consultar:
            self.boton_consultar.config(
                state=("disabled" if en_progreso else "normal"),
                text=("Consultando..." if en_progreso else "Consultar"),
            )

    def _mostrar_estado_carga(self, texto: str, color: str = "#86EFAC"):
        if self._dialogo_carga and self._dialogo_carga.winfo_exists() and hasattr(self, "label_estado_carga"):
            self.label_estado_carga.config(text=texto, fg=color)

    def limpiar_campos(self):
        self._consulta_activa_id += 1
        limpiar_contexto_conversacion(self._session_id_vigente())
        self._session_nonce += 1
        self.entrada_pregunta.delete("1.0", "end")
        self._actualizar_contexto_consulta()
        self._establecer_estado_consulta("", "#86EFAC", en_progreso=False)
        self._mostrar_respuesta("")
