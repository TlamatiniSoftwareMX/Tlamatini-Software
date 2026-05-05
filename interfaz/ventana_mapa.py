import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core.window_geometry import aplicar_geometria_relativa

from core.mapa import (
    agregar_punto_interes,
    agregar_poligono_riesgo,
    eliminar_elemento_mapa,
    obtener_configuracion_mapa,
    guardar_configuracion_mapa,
    obtener_mapa,
    listar_elementos_mapa,
    obtener_elemento_mapa
)

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


class VentanaMapa(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("TLAMATINI IA - Mapa táctico")
        self.configure(bg="#111827")
        aplicar_geometria_relativa(self, master, rel_w=0.94, rel_h=0.9, min_w=1200, min_h=780)

        self.modo_actual = tk.StringVar(value="seleccion")
        self.puntos_poligono_temporal = []
        self.item_canvas_a_id = {}

        self.ruta_fondo_actual = ""
        self.fondo_imagen_original = None
        self.fondo_imagen_tk = None
        self.ancho_original = 0
        self.alto_original = 0

        self.zoom_factor = 1.0
        self.zoom_min = 0.25
        self.zoom_max = 4.0
        self.zoom_step = 1.15

        self.arrastrando_mapa = False
        self.movimiento_minimo_drag = 4
        self.drag_inicio_x = 0
        self.drag_inicio_y = 0

        self._crear_interfaz()
        self._configurar_eventos_canvas()
        self._cargar_configuracion_inicial()
        self._redibujar_mapa()

    def _crear_interfaz(self):
        frame_principal = tk.Frame(self, bg="#111827")
        frame_principal.pack(fill="both", expand=True, padx=10, pady=10)

        self._crear_panel_superior(frame_principal)

        cuerpo = tk.Frame(frame_principal, bg="#111827")
        cuerpo.pack(fill="both", expand=True)

        self.frame_izquierdo = tk.Frame(cuerpo, bg="#1F2937", width=320)
        self.frame_izquierdo.pack(side="left", fill="y", padx=(0, 10))
        self.frame_izquierdo.pack_propagate(False)

        self.frame_centro = tk.Frame(cuerpo, bg="#111827")
        self.frame_centro.pack(side="left", fill="both", expand=True)

        self.frame_derecho = tk.Frame(cuerpo, bg="#1F2937", width=320)
        self.frame_derecho.pack(side="right", fill="y", padx=(10, 0))
        self.frame_derecho.pack_propagate(False)

        self._crear_panel_izquierdo()
        self._crear_panel_centro()
        self._crear_panel_derecho()

    def _crear_panel_superior(self, parent):
        barra = tk.Frame(parent, bg="#111827")
        barra.pack(fill="x", pady=(0, 10))

        titulo = tk.Label(
            barra,
            text="MAPA TÁCTICO OPERATIVO",
            font=("Arial", 20, "bold"),
            bg="#111827",
            fg="white"
        )
        titulo.pack(side="left")

        centro = tk.Frame(barra, bg="#111827")
        centro.pack(side="left", padx=20)

        self.label_zoom = tk.Label(
            centro,
            text="Zoom: 100%",
            font=("Arial", 10, "bold"),
            bg="#111827",
            fg="#D1D5DB"
        )
        self.label_zoom.pack(side="left", padx=(0, 10))

        ayuda = tk.Label(
            centro,
            text="Modo selección: arrastra con clic izquierdo | Rueda: zoom",
            font=("Arial", 10),
            bg="#111827",
            fg="#9CA3AF"
        )
        ayuda.pack(side="left")

        botones = tk.Frame(barra, bg="#111827")
        botones.pack(side="right")

        tk.Button(
            botones,
            text="Cargar fondo",
            font=("Arial", 10, "bold"),
            bg="#2563EB",
            fg="white",
            activebackground="#1D4ED8",
            activeforeground="white",
            command=self.cargar_fondo_mapa
        ).pack(side="left", padx=5)

        tk.Button(
            botones,
            text="Ajustar vista",
            font=("Arial", 10, "bold"),
            bg="#0EA5E9",
            fg="white",
            activebackground="#0284C7",
            activeforeground="white",
            command=self.ajustar_vista_inicial
        ).pack(side="left", padx=5)

        tk.Button(
            botones,
            text="Limpiar fondo",
            font=("Arial", 10, "bold"),
            bg="#6B7280",
            fg="white",
            activebackground="#4B5563",
            activeforeground="white",
            command=self.limpiar_fondo_mapa
        ).pack(side="left", padx=5)

        tk.Button(
            botones,
            text="Redibujar",
            font=("Arial", 10, "bold"),
            bg="#059669",
            fg="white",
            activebackground="#047857",
            activeforeground="white",
            command=self._redibujar_mapa
        ).pack(side="left", padx=5)

    def _crear_panel_izquierdo(self):
        titulo = tk.Label(
            self.frame_izquierdo,
            text="Edición",
            font=("Arial", 16, "bold"),
            bg="#1F2937",
            fg="white"
        )
        titulo.pack(anchor="w", padx=12, pady=(12, 10))

        modo_frame = tk.Frame(self.frame_izquierdo, bg="#1F2937")
        modo_frame.pack(fill="x", padx=12, pady=(0, 10))

        opciones = [
            ("Seleccionar", "seleccion"),
            ("Agregar punto", "punto"),
            ("Dibujar polígono", "poligono"),
        ]

        for texto, valor in opciones:
            tk.Radiobutton(
                modo_frame,
                text=texto,
                value=valor,
                variable=self.modo_actual,
                bg="#1F2937",
                fg="white",
                selectcolor="#111827",
                activebackground="#1F2937",
                activeforeground="white",
                font=("Arial", 10, "bold"),
                command=self._cambio_modo
            ).pack(anchor="w", pady=2)

        self.info_modo = tk.Label(
            self.frame_izquierdo,
            text="Modo actual: selección",
            font=("Arial", 10),
            bg="#1F2937",
            fg="#D1D5DB",
            justify="left",
            wraplength=280
        )
        self.info_modo.pack(anchor="w", padx=12, pady=(0, 10))

        separador = ttk.Separator(self.frame_izquierdo, orient="horizontal")
        separador.pack(fill="x", padx=12, pady=8)

        form = tk.Frame(self.frame_izquierdo, bg="#1F2937")
        form.pack(fill="both", expand=True, padx=12, pady=5)

        self.campos = {}

        etiquetas = [
            ("Nombre", "nombre"),
            ("Tipo / categoría", "tipo"),
            ("Nivel de riesgo", "nivel_riesgo"),
            ("Descripción", "descripcion")
        ]

        for texto, clave in etiquetas:
            tk.Label(
                form,
                text=texto,
                font=("Arial", 10, "bold"),
                bg="#1F2937",
                fg="white"
            ).pack(anchor="w", pady=(6, 2))

            if clave == "nivel_riesgo":
                combo = ttk.Combobox(
                    form,
                    values=["bajo", "medio", "alto", "critico"],
                    state="readonly"
                )
                combo.set("bajo")
                combo.pack(fill="x")
                self.campos[clave] = combo
            elif clave == "descripcion":
                txt = tk.Text(form, height=6, wrap="word", font=("Arial", 10))
                txt.pack(fill="x")
                self.campos[clave] = txt
            else:
                entry = tk.Entry(form, font=("Arial", 10))
                entry.pack(fill="x")
                self.campos[clave] = entry

        tk.Label(
            form,
            text="Coordenadas temporales",
            font=("Arial", 10, "bold"),
            bg="#1F2937",
            fg="white"
        ).pack(anchor="w", pady=(10, 2))

        self.label_coord = tk.Label(
            form,
            text="x: -, y: -",
            font=("Arial", 10),
            bg="#1F2937",
            fg="#D1D5DB"
        )
        self.label_coord.pack(anchor="w")

        self.label_poligono = tk.Label(
            form,
            text="Vértices de polígono: 0",
            font=("Arial", 10),
            bg="#1F2937",
            fg="#D1D5DB"
        )
        self.label_poligono.pack(anchor="w", pady=(4, 10))

        botones_form = tk.Frame(form, bg="#1F2937")
        botones_form.pack(fill="x", pady=(10, 0))

        tk.Button(
            botones_form,
            text="Guardar polígono",
            font=("Arial", 10, "bold"),
            bg="#7C3AED",
            fg="white",
            activebackground="#6D28D9",
            activeforeground="white",
            command=self.guardar_poligono_temporal
        ).pack(fill="x", pady=3)

        tk.Button(
            botones_form,
            text="Cancelar polígono",
            font=("Arial", 10, "bold"),
            bg="#6B7280",
            fg="white",
            activebackground="#4B5563",
            activeforeground="white",
            command=self.cancelar_poligono_temporal
        ).pack(fill="x", pady=3)

        tk.Button(
            botones_form,
            text="Limpiar formulario",
            font=("Arial", 10, "bold"),
            bg="#374151",
            fg="white",
            activebackground="#1F2937",
            activeforeground="white",
            command=self.limpiar_formulario
        ).pack(fill="x", pady=3)

    def _crear_panel_centro(self):
        marco = tk.Frame(self.frame_centro, bg="#111827")
        marco.pack(fill="both", expand=True)

        self.scroll_y = tk.Scrollbar(marco, orient="vertical")
        self.scroll_y.pack(side="right", fill="y")

        self.scroll_x = tk.Scrollbar(marco, orient="horizontal")
        self.scroll_x.pack(side="bottom", fill="x")

        self.canvas = tk.Canvas(
            marco,
            bg="#0B1220",
            highlightthickness=1,
            highlightbackground="#374151",
            cursor="cross",
            xscrollcommand=self.scroll_x.set,
            yscrollcommand=self.scroll_y.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scroll_x.config(command=self.canvas.xview)
        self.scroll_y.config(command=self.canvas.yview)

    def _crear_panel_derecho(self):
        titulo = tk.Label(
            self.frame_derecho,
            text="Elementos del mapa",
            font=("Arial", 16, "bold"),
            bg="#1F2937",
            fg="white"
        )
        titulo.pack(anchor="w", padx=12, pady=(12, 10))

        columnas = ("nombre", "tipo", "riesgo")
        self.tabla = ttk.Treeview(
            self.frame_derecho,
            columns=columnas,
            show="headings",
            height=14
        )
        self.tabla.heading("nombre", text="Nombre")
        self.tabla.heading("tipo", text="Tipo")
        self.tabla.heading("riesgo", text="Riesgo")

        self.tabla.column("nombre", width=130, anchor="w")
        self.tabla.column("tipo", width=90, anchor="center")
        self.tabla.column("riesgo", width=70, anchor="center")

        self.tabla.pack(fill="x", padx=12)
        self.tabla.bind("<<TreeviewSelect>>", self._seleccion_tabla)

        botones = tk.Frame(self.frame_derecho, bg="#1F2937")
        botones.pack(fill="x", padx=12, pady=10)

        tk.Button(
            botones,
            text="Eliminar seleccionado",
            font=("Arial", 10, "bold"),
            bg="#DC2626",
            fg="white",
            activebackground="#B91C1C",
            activeforeground="white",
            command=self.eliminar_seleccionado
        ).pack(fill="x")

        detalle_titulo = tk.Label(
            self.frame_derecho,
            text="Detalle",
            font=("Arial", 14, "bold"),
            bg="#1F2937",
            fg="white"
        )
        detalle_titulo.pack(anchor="w", padx=12, pady=(10, 6))

        self.detalle = tk.Text(
            self.frame_derecho,
            height=18,
            wrap="word",
            font=("Arial", 10),
            bg="#111827",
            fg="white",
            relief="flat"
        )
        self.detalle.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.detalle.insert("1.0", "Selecciona un elemento para ver sus datos.")
        self.detalle.config(state="disabled")

    def _configurar_eventos_canvas(self):
        self.canvas.bind("<ButtonPress-1>", self._button_press_izquierdo)
        self.canvas.bind("<B1-Motion>", self._drag_izquierdo)
        self.canvas.bind("<ButtonRelease-1>", self._button_release_izquierdo)

        # Pan alterno con botón central, por si el usuario lo quiere usar
        self.canvas.bind("<ButtonPress-2>", self._iniciar_pan)
        self.canvas.bind("<B2-Motion>", self._mover_pan)

        # Zoom Windows / touchpad cuando el sistema lo traduce
        self.canvas.bind("<MouseWheel>", self._zoom_mousewheel)

        # Zoom Linux
        self.canvas.bind("<Button-4>", self._zoom_linux_in)
        self.canvas.bind("<Button-5>", self._zoom_linux_out)

    def _cargar_configuracion_inicial(self):
        config = obtener_configuracion_mapa()
        ruta_fondo = config.get("fondo_mapa", "")

        if ruta_fondo and os.path.exists(ruta_fondo):
            self._cargar_fondo_desde_archivo(ruta_fondo)

    def _cambio_modo(self):
        modo = self.modo_actual.get()

        if modo == "seleccion":
            self.info_modo.config(text="Modo actual: selección\nArrastra con clic izquierdo para mover el mapa.")
        elif modo == "punto":
            self.info_modo.config(text="Modo actual: agregar punto\nHaz clic sobre el mapa para colocar un punto.")
        elif modo == "poligono":
            self.info_modo.config(text="Modo actual: dibujar polígono\nHaz clic para agregar vértices y luego guarda el polígono.")

    def _button_press_izquierdo(self, event):
        self.drag_inicio_x = event.x
        self.drag_inicio_y = event.y
        self.arrastrando_mapa = False

        if self.modo_actual.get() == "seleccion":
            self._iniciar_pan(event)

    def _drag_izquierdo(self, event):
        if self.modo_actual.get() != "seleccion":
            return

        dx = abs(event.x - self.drag_inicio_x)
        dy = abs(event.y - self.drag_inicio_y)

        if dx >= self.movimiento_minimo_drag or dy >= self.movimiento_minimo_drag:
            self.arrastrando_mapa = True
            self._mover_pan(event)

    def _button_release_izquierdo(self, event):
        modo = self.modo_actual.get()

        if modo == "seleccion":
            self.arrastrando_mapa = False
            return

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        x_real = x / self.zoom_factor
        y_real = y / self.zoom_factor

        self.label_coord.config(text=f"x: {int(x_real)}, y: {int(y_real)}")

        if modo == "punto":
            self._guardar_punto_desde_click(x_real, y_real)
        elif modo == "poligono":
            self._agregar_vertice_poligono(x_real, y_real)

    def _iniciar_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _mover_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _zoom_mousewheel(self, event):
        if event.delta > 0:
            self._cambiar_zoom(self.zoom_step, event.x, event.y)
        elif event.delta < 0:
            self._cambiar_zoom(1 / self.zoom_step, event.x, event.y)

    def _zoom_linux_in(self, event):
        self._cambiar_zoom(self.zoom_step, event.x, event.y)

    def _zoom_linux_out(self, event):
        self._cambiar_zoom(1 / self.zoom_step, event.x, event.y)

    def _cambiar_zoom(self, factor, x_canvas, y_canvas):
        nuevo_zoom = self.zoom_factor * factor
        if nuevo_zoom < self.zoom_min or nuevo_zoom > self.zoom_max:
            return

        x_before = self.canvas.canvasx(x_canvas)
        y_before = self.canvas.canvasy(y_canvas)

        self.zoom_factor = nuevo_zoom
        self.label_zoom.config(text=f"Zoom: {int(self.zoom_factor * 100)}%")
        self._redibujar_mapa()

        x_after = self.canvas.canvasx(x_canvas)
        y_after = self.canvas.canvasy(y_canvas)

        dx = x_after - x_before
        dy = y_after - y_before

        sr = self.canvas.cget("scrollregion")
        if sr:
            x1, y1, x2, y2 = map(float, sr.split())
            ancho_total = max(x2 - x1, 1)
            alto_total = max(y2 - y1, 1)

            vista_x = self.canvas.canvasx(0) + dx
            vista_y = self.canvas.canvasy(0) + dy

            self.canvas.xview_moveto(max(0, min(1, vista_x / ancho_total)))
            self.canvas.yview_moveto(max(0, min(1, vista_y / alto_total)))

    def ajustar_vista_inicial(self):
        self.zoom_factor = 1.0
        self.label_zoom.config(text="Zoom: 100%")
        self._redibujar_mapa()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def _guardar_punto_desde_click(self, x, y):
        nombre = self.campos["nombre"].get().strip()
        tipo = self.campos["tipo"].get().strip() or "punto_interes"
        nivel_riesgo = self.campos["nivel_riesgo"].get().strip() or "bajo"
        descripcion = self.campos["descripcion"].get("1.0", "end").strip()

        if not nombre:
            messagebox.showwarning("Falta nombre", "Debes escribir un nombre antes de colocar el punto.")
            return

        agregar_punto_interes(
            nombre=nombre,
            tipo=tipo,
            descripcion=descripcion,
            x=x,
            y=y,
            nivel_riesgo=nivel_riesgo
        )

        self._redibujar_mapa()
        self._actualizar_lista()
        messagebox.showinfo("Punto agregado", f"Se agregó el punto '{nombre}'.")
        self.limpiar_formulario()

    def _agregar_vertice_poligono(self, x, y):
        self.puntos_poligono_temporal.append({"x": float(x), "y": float(y)})
        self.label_poligono.config(text=f"Vértices de polígono: {len(self.puntos_poligono_temporal)}")
        self._redibujar_mapa()

    def guardar_poligono_temporal(self):
        if len(self.puntos_poligono_temporal) < 3:
            messagebox.showwarning("Polígono incompleto", "Necesitas al menos 3 puntos para guardar un polígono.")
            return

        nombre = self.campos["nombre"].get().strip()
        tipo = self.campos["tipo"].get().strip() or "zona_riesgo"
        nivel_riesgo = self.campos["nivel_riesgo"].get().strip() or "medio"
        descripcion = self.campos["descripcion"].get("1.0", "end").strip()

        if not nombre:
            messagebox.showwarning("Falta nombre", "Debes escribir un nombre antes de guardar el polígono.")
            return

        agregar_poligono_riesgo(
            nombre=nombre,
            nivel_riesgo=nivel_riesgo,
            descripcion=descripcion,
            puntos=self.puntos_poligono_temporal,
            tipo=tipo
        )

        self.puntos_poligono_temporal = []
        self.label_poligono.config(text="Vértices de polígono: 0")
        self._redibujar_mapa()
        self._actualizar_lista()
        messagebox.showinfo("Polígono agregado", f"Se agregó el polígono '{nombre}'.")
        self.limpiar_formulario()

    def cancelar_poligono_temporal(self):
        self.puntos_poligono_temporal = []
        self.label_poligono.config(text="Vértices de polígono: 0")
        self._redibujar_mapa()

    def limpiar_formulario(self):
        self.campos["nombre"].delete(0, "end")
        self.campos["tipo"].delete(0, "end")
        self.campos["nivel_riesgo"].set("bajo")
        self.campos["descripcion"].delete("1.0", "end")
        self.label_coord.config(text="x: -, y: -")

    def cargar_fondo_mapa(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar mapa base",
            filetypes=[
                ("Mapas compatibles", "*.pdf *.png *.jpg *.jpeg *.gif"),
                ("PDF", "*.pdf"),
                ("Imágenes", "*.png *.jpg *.jpeg *.gif"),
                ("Todos los archivos", "*.*")
            ]
        )
        if not ruta:
            return

        self._cargar_fondo_desde_archivo(ruta)
        guardar_configuracion_mapa(fondo_mapa=ruta)
        self.zoom_factor = 1.0
        self.label_zoom.config(text="Zoom: 100%")
        self._redibujar_mapa()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def _cargar_fondo_desde_archivo(self, ruta):
        extension = os.path.splitext(ruta)[1].lower()

        if extension == ".pdf":
            self._cargar_pdf_como_fondo(ruta)
        else:
            self._cargar_imagen_como_fondo(ruta)

        self.ruta_fondo_actual = ruta

    def _cargar_imagen_como_fondo(self, ruta):
        if Image is None or ImageTk is None:
            messagebox.showerror(
                "Dependencia faltante",
                "Necesitas instalar pillow:\n\npip install pillow"
            )
            return

        try:
            imagen = Image.open(ruta).convert("RGB")
            self.fondo_imagen_original = imagen
            self.ancho_original, self.alto_original = imagen.size
            self._actualizar_imagen_zoom()
        except Exception as e:
            self.fondo_imagen_original = None
            self.fondo_imagen_tk = None
            messagebox.showerror("Error de imagen", f"No se pudo cargar la imagen:\n{e}")

    def _cargar_pdf_como_fondo(self, ruta):
        if fitz is None:
            messagebox.showerror(
                "Dependencia faltante",
                "Necesitas instalar pymupdf:\n\npip install pymupdf"
            )
            return

        if Image is None or ImageTk is None:
            messagebox.showerror(
                "Dependencia faltante",
                "Necesitas instalar pillow:\n\npip install pillow"
            )
            return

        try:
            doc = fitz.open(ruta)
            pagina = doc.load_page(0)

            zoom_pdf = 2.0
            matriz = fitz.Matrix(zoom_pdf, zoom_pdf)
            pix = pagina.get_pixmap(matrix=matriz, alpha=False)

            imagen = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.fondo_imagen_original = imagen
            self.ancho_original, self.alto_original = imagen.size
            self._actualizar_imagen_zoom()

            doc.close()
        except Exception as e:
            self.fondo_imagen_original = None
            self.fondo_imagen_tk = None
            messagebox.showerror("Error de PDF", f"No se pudo cargar el PDF como fondo:\n{e}")

    def _actualizar_imagen_zoom(self):
        if self.fondo_imagen_original is None or ImageTk is None:
            self.fondo_imagen_tk = None
            return

        nuevo_ancho = max(1, int(self.ancho_original * self.zoom_factor))
        nuevo_alto = max(1, int(self.alto_original * self.zoom_factor))

        imagen_redimensionada = self.fondo_imagen_original.resize(
            (nuevo_ancho, nuevo_alto),
            Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
        )

        self.fondo_imagen_tk = ImageTk.PhotoImage(imagen_redimensionada)

    def limpiar_fondo_mapa(self):
        self.fondo_imagen_original = None
        self.fondo_imagen_tk = None
        self.ruta_fondo_actual = ""
        self.ancho_original = 0
        self.alto_original = 0
        guardar_configuracion_mapa(fondo_mapa="")
        self._redibujar_mapa()

    def _dibujar_fondo(self):
        self.canvas.delete("all")

        if self.fondo_imagen_original is not None:
            self._actualizar_imagen_zoom()
            self.canvas.create_image(0, 0, anchor="nw", image=self.fondo_imagen_tk)

            ancho = int(self.ancho_original * self.zoom_factor)
            alto = int(self.alto_original * self.zoom_factor)
            self.canvas.config(scrollregion=(0, 0, ancho, alto))
        else:
            ancho = max(self.canvas.winfo_width(), 1200)
            alto = max(self.canvas.winfo_height(), 900)

            paso = max(20, int(50 * self.zoom_factor))
            for x in range(0, ancho, paso):
                self.canvas.create_line(x, 0, x, alto, fill="#1F2937")
            for y in range(0, alto, paso):
                self.canvas.create_line(0, y, ancho, y, fill="#1F2937")

            self.canvas.config(scrollregion=(0, 0, ancho, alto))

    def _escala(self, valor):
        return valor * self.zoom_factor

    def _redibujar_mapa(self):
        self._dibujar_fondo()
        self.item_canvas_a_id = {}

        mapa = obtener_mapa()

        for poligono in mapa.get("poligonos_riesgo", []):
            puntos = poligono.get("puntos", [])
            coords = []
            for p in puntos:
                coords.extend([self._escala(p["x"]), self._escala(p["y"])])

            if len(coords) >= 6:
                item = self.canvas.create_polygon(
                    coords,
                    outline=poligono.get("color", "#F97316"),
                    fill="",
                    width=max(2, int(3 * self.zoom_factor))
                )
                self.item_canvas_a_id[item] = poligono["id"]

                primer = puntos[0]
                label = self.canvas.create_text(
                    self._escala(primer["x"]) + 8,
                    self._escala(primer["y"]) - 8,
                    text=poligono.get("nombre", ""),
                    anchor="nw",
                    fill="white",
                    font=("Arial", max(8, int(10 * self.zoom_factor)), "bold")
                )
                self.item_canvas_a_id[label] = poligono["id"]

        for punto in mapa.get("puntos_interes", []):
            x = self._escala(punto.get("x", 0))
            y = self._escala(punto.get("y", 0))
            color = punto.get("color", "#3B82F6")
            radio = max(4, int(6 * self.zoom_factor))

            item = self.canvas.create_oval(
                x - radio, y - radio, x + radio, y + radio,
                fill=color,
                outline="white",
                width=1
            )
            self.item_canvas_a_id[item] = punto["id"]

            label = self.canvas.create_text(
                x + 10,
                y - 10,
                text=punto.get("nombre", ""),
                anchor="nw",
                fill="white",
                font=("Arial", max(8, int(10 * self.zoom_factor)), "bold")
            )
            self.item_canvas_a_id[label] = punto["id"]

        if self.puntos_poligono_temporal:
            coords = []
            for p in self.puntos_poligono_temporal:
                coords.extend([self._escala(p["x"]), self._escala(p["y"])])

            if len(coords) >= 4:
                self.canvas.create_line(*coords, fill="#A855F7", width=max(2, int(2 * self.zoom_factor)))

            for p in self.puntos_poligono_temporal:
                x = self._escala(p["x"])
                y = self._escala(p["y"])
                radio = max(3, int(4 * self.zoom_factor))
                self.canvas.create_oval(
                    x - radio, y - radio, x + radio, y + radio,
                    fill="#A855F7",
                    outline="white"
                )

        self._actualizar_lista()

    def _actualizar_lista(self):
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        for elemento in listar_elementos_mapa():
            self.tabla.insert(
                "",
                "end",
                iid=elemento["id"],
                values=(
                    elemento.get("nombre", ""),
                    elemento.get("tipo_elemento", ""),
                    elemento.get("nivel_riesgo", "")
                )
            )

    def _seleccion_tabla(self, event=None):
        seleccion = self.tabla.selection()
        if not seleccion:
            return

        elemento_id = seleccion[0]
        self._mostrar_detalle(elemento_id)

    def _mostrar_detalle(self, elemento_id):
        data = obtener_elemento_mapa(elemento_id)
        if not data:
            return

        lineas = [
            f"ID: {data.get('id', '')}",
            f"Tipo de elemento: {data.get('tipo_elemento', '')}",
            f"Nombre: {data.get('nombre', '')}",
            f"Categoría: {data.get('tipo', '')}",
            f"Nivel de riesgo: {data.get('nivel_riesgo', '')}",
            f"Color: {data.get('color', '')}",
            f"Fecha: {data.get('fecha_registro', '')}",
            "",
            "Descripción:",
            data.get("descripcion", "")
        ]

        if data.get("tipo_elemento") == "punto":
            lineas.extend([
                "",
                f"Coordenada X: {data.get('x', '')}",
                f"Coordenada Y: {data.get('y', '')}"
            ])

        if data.get("tipo_elemento") == "poligono":
            puntos = data.get("puntos", [])
            lineas.extend([
                "",
                f"Vértices: {len(puntos)}"
            ])
            for i, p in enumerate(puntos[:10], start=1):
                lineas.append(f"- Punto {i}: ({int(p['x'])}, {int(p['y'])})")

        self.detalle.config(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", "\n".join(lineas))
        self.detalle.config(state="disabled")

    def eliminar_seleccionado(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning("Sin selección", "Selecciona un elemento en la lista.")
            return

        elemento_id = seleccion[0]
        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            "¿Seguro que deseas eliminar el elemento seleccionado?"
        )
        if not confirmar:
            return

        ok = eliminar_elemento_mapa(elemento_id)
        if ok:
            messagebox.showinfo("Eliminado", "Elemento eliminado correctamente.")
            self._redibujar_mapa()
            self.detalle.config(state="normal")
            self.detalle.delete("1.0", "end")
            self.detalle.insert("1.0", "Selecciona un elemento para ver sus datos.")
            self.detalle.config(state="disabled")
        else:
            messagebox.showerror("Error", "No se pudo eliminar el elemento.")
