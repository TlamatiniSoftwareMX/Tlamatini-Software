import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageTk

from core.memoria import RUTA_BASE_DATOS
from core.window_geometry import aplicar_geometria_relativa
from interfaz.ventana_consulta import VentanaConsulta


class VentanaCamara(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("TLAMATINI IA - Cámara / Escáner")
        self.configure(bg="#111827")
        aplicar_geometria_relativa(self, master, rel_w=0.92, rel_h=0.9, min_w=1180, min_h=760)

        self.cap = None
        self.camara_activa = False
        self.indice_camara = 0

        self.frame_actual_bgr = None
        self.imagen_cargada_pil = None
        self.imagen_preview_tk = None
        self.ruta_ultima_imagen = ""

        self.directorio_evidencias = RUTA_BASE_DATOS / "imagenes_capturadas"
        self.directorio_evidencias.mkdir(parents=True, exist_ok=True)

        self._crear_interfaz()
        self.protocol("WM_DELETE_WINDOW", self._cerrar_ventana)

    def _crear_interfaz(self):
        frame_principal = tk.Frame(self, bg="#111827")
        frame_principal.pack(fill="both", expand=True, padx=12, pady=12)

        titulo = tk.Label(
            frame_principal,
            text="CÁMARA / ESCÁNER",
            font=("Arial", 20, "bold"),
            bg="#111827",
            fg="white"
        )
        titulo.pack(anchor="w", pady=(0, 10))

        subtitulo = tk.Label(
            frame_principal,
            text="Captura evidencia visual, carga imágenes y formula preguntas sobre la imagen.",
            font=("Arial", 11),
            bg="#111827",
            fg="#D1D5DB"
        )
        subtitulo.pack(anchor="w", pady=(0, 12))

        barra = tk.Frame(frame_principal, bg="#111827")
        barra.pack(fill="x", pady=(0, 10))

        tk.Button(
            barra,
            text="Iniciar cámara",
            font=("Arial", 10, "bold"),
            bg="#2563EB",
            fg="white",
            activebackground="#1D4ED8",
            activeforeground="white",
            command=self.iniciar_camara
        ).pack(side="left", padx=4)

        tk.Button(
            barra,
            text="Detener cámara",
            font=("Arial", 10, "bold"),
            bg="#6B7280",
            fg="white",
            activebackground="#4B5563",
            activeforeground="white",
            command=self.detener_camara
        ).pack(side="left", padx=4)

        tk.Button(
            barra,
            text="Capturar foto",
            font=("Arial", 10, "bold"),
            bg="#059669",
            fg="white",
            activebackground="#047857",
            activeforeground="white",
            command=self.capturar_foto
        ).pack(side="left", padx=4)

        tk.Button(
            barra,
            text="Cargar imagen",
            font=("Arial", 10, "bold"),
            bg="#7C3AED",
            fg="white",
            activebackground="#6D28D9",
            activeforeground="white",
            command=self.cargar_imagen
        ).pack(side="left", padx=4)

        tk.Button(
            barra,
            text="Guardar copia",
            font=("Arial", 10, "bold"),
            bg="#D97706",
            fg="white",
            activebackground="#B45309",
            activeforeground="white",
            command=self.guardar_copia_actual
        ).pack(side="left", padx=4)

        tk.Button(
            barra,
            text="Limpiar vista",
            font=("Arial", 10, "bold"),
            bg="#374151",
            fg="white",
            activebackground="#1F2937",
            activeforeground="white",
            command=self.limpiar_vista
        ).pack(side="left", padx=4)

        cuerpo = tk.Frame(frame_principal, bg="#111827")
        cuerpo.pack(fill="both", expand=True)

        self.frame_preview = tk.Frame(cuerpo, bg="#0B1220")
        self.frame_preview.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.label_preview = tk.Label(
            self.frame_preview,
            text="Sin imagen.\nInicia la cámara o carga un archivo.",
            font=("Arial", 16, "bold"),
            bg="#0B1220",
            fg="white",
            justify="center"
        )
        self.label_preview.pack(fill="both", expand=True)

        self.frame_lateral = tk.Frame(cuerpo, bg="#1F2937", width=420)
        self.frame_lateral.pack(side="right", fill="y")
        self.frame_lateral.pack_propagate(False)

        tk.Label(
            self.frame_lateral,
            text="Panel de control",
            font=("Arial", 16, "bold"),
            bg="#1F2937",
            fg="white"
        ).pack(anchor="w", padx=12, pady=(12, 10))

        tk.Label(
            self.frame_lateral,
            text="Pregunta sobre la imagen",
            font=("Arial", 10, "bold"),
            bg="#1F2937",
            fg="white"
        ).pack(anchor="w", padx=12)

        self.texto_contexto = tk.Text(
            self.frame_lateral,
            height=5,
            wrap="word",
            font=("Arial", 10),
            bg="#111827",
            fg="white"
        )
        self.texto_contexto.pack(fill="x", padx=12, pady=(4, 8))

        barra_pregunta = tk.Frame(self.frame_lateral, bg="#1F2937")
        barra_pregunta.pack(fill="x", padx=12, pady=(0, 10))

        tk.Button(
            barra_pregunta,
            text="Procesar pregunta",
            font=("Arial", 10, "bold"),
            bg="#2563EB",
            fg="white",
            activebackground="#1D4ED8",
            activeforeground="white",
            command=self.procesar_consulta_visual
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            barra_pregunta,
            text="Enviar a Consulta",
            font=("Arial", 10, "bold"),
            bg="#0EA5E9",
            fg="white",
            activebackground="#0284C7",
            activeforeground="white",
            command=self.enviar_a_consulta
        ).pack(side="left")

        tk.Label(
            self.frame_lateral,
            text="Estado",
            font=("Arial", 10, "bold"),
            bg="#1F2937",
            fg="white"
        ).pack(anchor="w", padx=12)

        self.label_estado = tk.Label(
            self.frame_lateral,
            text="Cámara inactiva.",
            font=("Arial", 10),
            bg="#1F2937",
            fg="#D1D5DB",
            justify="left",
            wraplength=380
        )
        self.label_estado.pack(anchor="w", padx=12, pady=(4, 10))

        tk.Label(
            self.frame_lateral,
            text="Ruta actual",
            font=("Arial", 10, "bold"),
            bg="#1F2937",
            fg="white"
        ).pack(anchor="w", padx=12)

        self.label_ruta = tk.Label(
            self.frame_lateral,
            text="Sin archivo.",
            font=("Arial", 9),
            bg="#1F2937",
            fg="#9CA3AF",
            justify="left",
            wraplength=380
        )
        self.label_ruta.pack(anchor="w", padx=12, pady=(4, 10))

        tk.Label(
            self.frame_lateral,
            text="Respuesta operativa",
            font=("Arial", 10, "bold"),
            bg="#1F2937",
            fg="white"
        ).pack(anchor="w", padx=12)

        self.area_respuesta = tk.Text(
            self.frame_lateral,
            height=12,
            wrap="word",
            font=("Arial", 10),
            bg="#111827",
            fg="white"
        )
        self.area_respuesta.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self.area_respuesta.insert(
            "1.0",
            "Aquí aparecerá la respuesta o el procesamiento de tu pregunta sobre la imagen."
        )
        self.area_respuesta.config(state="disabled")

        tk.Label(
            self.frame_lateral,
            text="Notas",
            font=("Arial", 10, "bold"),
            bg="#1F2937",
            fg="white"
        ).pack(anchor="w", padx=12)

        self.texto_notas = tk.Text(
            self.frame_lateral,
            height=7,
            wrap="word",
            font=("Arial", 10),
            bg="#111827",
            fg="white"
        )
        self.texto_notas.pack(fill="both", expand=True, padx=12, pady=(4, 12))

    def iniciar_camara(self):
        if self.camara_activa:
            self.label_estado.config(text="La cámara ya está activa.")
            return

        cap = cv2.VideoCapture(self.indice_camara, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.indice_camara)

        if not cap.isOpened():
            messagebox.showerror(
                "Error de cámara",
                "No se pudo abrir la cámara.\nVerifica que esté conectada o libre."
            )
            return

        self.cap = cap
        self.camara_activa = True
        self.label_estado.config(text="Cámara activa. Vista previa en tiempo real.")
        self._actualizar_preview_camara()

    def detener_camara(self):
        self.camara_activa = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.label_estado.config(text="Cámara detenida.")

    def _actualizar_preview_camara(self):
        if not self.camara_activa or self.cap is None:
            return

        ok, frame = self.cap.read()
        if ok:
            self.frame_actual_bgr = frame
            self._mostrar_frame_bgr(frame)

        self.after(30, self._actualizar_preview_camara)

    def _mostrar_frame_bgr(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen = Image.fromarray(frame_rgb)
        self._mostrar_pil_en_preview(imagen)

    def _mostrar_pil_en_preview(self, imagen_pil):
        ancho_max = max(self.label_preview.winfo_width(), 700)
        alto_max = max(self.label_preview.winfo_height(), 500)

        copia = imagen_pil.copy()
        copia.thumbnail((ancho_max, alto_max))

        self.imagen_preview_tk = ImageTk.PhotoImage(copia)
        self.label_preview.config(image=self.imagen_preview_tk, text="")

    def capturar_foto(self):
        if self.frame_actual_bgr is None:
            messagebox.showwarning("Sin imagen", "No hay imagen actual para capturar.")
            return

        nombre = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        ruta = self.directorio_evidencias / nombre

        try:
            cv2.imwrite(str(ruta), self.frame_actual_bgr)
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo guardar la captura:\n{e}")
            return

        self.ruta_ultima_imagen = str(ruta)
        self.label_ruta.config(text=self.ruta_ultima_imagen)
        self.label_estado.config(text="Foto capturada y guardada correctamente.")
        self.texto_notas.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] Captura guardada: {nombre}\n")

    def cargar_imagen(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imágenes compatibles", "*.png *.jpg *.jpeg *.bmp *.webp"),
                ("Todos los archivos", "*.*")
            ]
        )
        if not ruta:
            return

        try:
            imagen = Image.open(ruta).convert("RGB")
        except Exception as e:
            messagebox.showerror("Error de imagen", f"No se pudo abrir la imagen:\n{e}")
            return

        self.imagen_cargada_pil = imagen
        self.ruta_ultima_imagen = ruta
        self.label_ruta.config(text=ruta)
        self.label_estado.config(text="Imagen cargada correctamente.")
        self._mostrar_pil_en_preview(imagen)

    def guardar_copia_actual(self):
        if self.frame_actual_bgr is None and self.imagen_cargada_pil is None:
            messagebox.showwarning("Sin contenido", "No hay imagen actual para guardar.")
            return

        ruta = filedialog.asksaveasfilename(
            title="Guardar copia de imagen",
            defaultextension=".jpg",
            filetypes=[
                ("JPEG", "*.jpg"),
                ("PNG", "*.png"),
                ("Todos los archivos", "*.*")
            ]
        )
        if not ruta:
            return

        try:
            if self.imagen_cargada_pil is not None:
                self.imagen_cargada_pil.save(ruta)
            else:
                cv2.imwrite(ruta, self.frame_actual_bgr)
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo guardar la copia:\n{e}")
            return

        self.ruta_ultima_imagen = ruta
        self.label_ruta.config(text=ruta)
        self.label_estado.config(text="Copia guardada correctamente.")

    def limpiar_vista(self):
        self.imagen_cargada_pil = None
        self.frame_actual_bgr = None
        self.imagen_preview_tk = None
        self.ruta_ultima_imagen = ""

        self.label_preview.config(
            image="",
            text="Sin imagen.\nInicia la cámara o carga un archivo."
        )
        self.label_ruta.config(text="Sin archivo.")
        self.label_estado.config(text="Vista limpia.")
        self._mostrar_respuesta("Aquí aparecerá la respuesta o el procesamiento de tu pregunta sobre la imagen.")

    def procesar_consulta_visual(self):
        pregunta = self.texto_contexto.get("1.0", "end").strip()

        if not pregunta:
            messagebox.showwarning("Pregunta vacía", "Escribe una pregunta sobre la imagen.")
            return

        if not self.ruta_ultima_imagen and self.imagen_cargada_pil is None and self.frame_actual_bgr is None:
            messagebox.showwarning("Sin imagen", "Primero captura o carga una imagen.")
            return

        origen = "imagen cargada"
        dimensiones = "desconocidas"

        if self.imagen_cargada_pil is not None:
            dimensiones = f"{self.imagen_cargada_pil.width} x {self.imagen_cargada_pil.height}"
        elif self.frame_actual_bgr is not None:
            alto, ancho = self.frame_actual_bgr.shape[:2]
            dimensiones = f"{ancho} x {alto}"
            origen = "captura de cámara"

        archivo = Path(self.ruta_ultima_imagen).name if self.ruta_ultima_imagen else "sin archivo guardado"

        respuesta = (
            "Consulta visual registrada.\n\n"
            f"Pregunta: {pregunta}\n"
            f"Origen: {origen}\n"
            f"Archivo: {archivo}\n"
            f"Dimensiones: {dimensiones}\n\n"
            "Estado actual:\n"
            "- La ventana acepta preguntas y las vincula a la imagen activa.\n"
            "- La base quedó lista para conectar el análisis visual más adelante.\n"
            "- Puedes usar 'Enviar a Consulta' para seguir trabajando la pregunta.\n\n"
            "Sugerencias:\n"
            "• ¿Qué planta puede ser?\n"
            "• ¿Qué lesión se observa?\n"
            "• ¿Qué texto aparece en la etiqueta?\n"
            "• ¿Qué objeto o herramienta se observa?\n"
        )

        self.label_estado.config(text="Pregunta procesada y vinculada a la imagen actual.")
        self._mostrar_respuesta(respuesta)

    def enviar_a_consulta(self):
        pregunta = self.texto_contexto.get("1.0", "end").strip()

        if not pregunta:
            messagebox.showwarning("Pregunta vacía", "Escribe una pregunta antes de enviarla.")
            return

        ventana = VentanaConsulta(self)
        ventana.entrada_pregunta.delete("1.0", "end")
        ventana.entrada_pregunta.insert("1.0", pregunta)

        contexto = "Pregunta enviada al módulo Consulta."
        if self.ruta_ultima_imagen:
            contexto += f"\nImagen asociada: {self.ruta_ultima_imagen}"

        self.label_estado.config(text=contexto)

    def _mostrar_respuesta(self, texto: str):
        self.area_respuesta.config(state="normal")
        self.area_respuesta.delete("1.0", "end")
        self.area_respuesta.insert("1.0", texto)
        self.area_respuesta.config(state="disabled")

    def _cerrar_ventana(self):
        self.detener_camara()
        self.destroy()
