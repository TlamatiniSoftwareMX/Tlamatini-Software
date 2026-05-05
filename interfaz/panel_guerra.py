import tkinter as tk
from tkinter import ttk
from datetime import datetime


class PanelGuerra(ttk.Frame):
    def __init__(
        self,
        master,
        obtener_alertas_callback=None,
        limpiar_alertas_callback=None,
        probar_alarma_callback=None,
        abrir_sonidos_callback=None,
    ):
        super().__init__(master, padding=6)
        self.obtener_alertas_callback = obtener_alertas_callback
        self.limpiar_alertas_callback = limpiar_alertas_callback
        self.probar_alarma_callback = probar_alarma_callback
        self.abrir_sonidos_callback = abrir_sonidos_callback
        self.alertas_actuales = []
        self.config(style="PanelGuerra.TFrame")
        self.encabezado = ttk.Frame(self, style="PanelGuerra.TFrame")
        self.encabezado.pack(fill="x", pady=(0, 2))

        self.titulo = ttk.Label(
            self.encabezado,
            text="PANEL DE ALERTAS",
            style="PanelGuerraTitulo.TLabel"
        )
        self.titulo.pack(side="left", anchor="w")

        self.encabezado_derecha = ttk.Frame(self.encabezado, style="PanelGuerra.TFrame")
        self.encabezado_derecha.pack(side="right", anchor="e")

        self.info_superior = ttk.Frame(self, style="PanelGuerra.TFrame")
        self.info_superior.pack(fill="x", pady=(0, 4))

        self.etiqueta_estado = ttk.Label(
            self.info_superior,
            text="Estado general: OPERATIVO",
            style="PanelGuerraTexto.TLabel"
        )
        self.etiqueta_estado.pack(side="left", padx=(0, 20))

        self.etiqueta_actualizacion = ttk.Label(
            self.info_superior,
            text="Última actualización: --:--:--",
            style="PanelGuerraTexto.TLabel"
        )
        self.etiqueta_actualizacion.pack(side="left")

        self.separador = ttk.Separator(self, orient="horizontal")
        self.separador.pack(fill="x", pady=3)

        self.area_alertas = tk.Listbox(
            self,
            height=8,
            bg="#0f172a",
            fg="white",
            relief="flat",
            font=("Arial", 10),
            selectbackground="#2563EB",
            selectforeground="white"
        )
        self.area_alertas.pack(fill="both", expand=True, pady=(4, 0))

        barra_acciones = ttk.Frame(self, style="PanelGuerra.TFrame")
        barra_acciones.pack(fill="x", pady=(6, 0))
        self.btn_probar = ttk.Button(barra_acciones, text="Probar alarma", command=self._probar_alarma)
        self.btn_probar.pack(side="left")
        self.btn_sonidos = ttk.Button(barra_acciones, text="Sonidos alarma", command=self._abrir_sonidos)
        self.btn_sonidos.pack(side="left", padx=(8, 0))
        self.btn_limpiar = ttk.Button(barra_acciones, text="Limpiar panel", command=self._limpiar_panel)
        self.btn_limpiar.pack(side="right")

        self.actualizar_panel()

    def obtener_contenedor_encabezado_derecha(self):
        return self.encabezado_derecha

    def actualizar_panel(self):
        alertas = []
        if callable(self.obtener_alertas_callback):
            try:
                alertas = self.obtener_alertas_callback()
            except Exception as e:
                alertas = [{"id": "", "texto": f"Error al obtener alertas: {e}", "cerrable": False}]

        if not alertas:
            alertas = [{"id": "", "texto": "Sin alertas activas.", "cerrable": False}]

        self.alertas_actuales = alertas
        self.area_alertas.delete(0, tk.END)

        for alerta in alertas:
            texto = alerta.get("texto", "") if isinstance(alerta, dict) else str(alerta)
            self.area_alertas.insert(tk.END, texto)

        ahora = datetime.now().strftime("%I:%M:%S %p")
        self.etiqueta_actualizacion.config(
            text=f"Última actualización: {ahora}"
        )

        self.after(5000, self.actualizar_panel)

    def _limpiar_panel(self):
        alertas_ids = [
            alerta.get("id", "")
            for alerta in self.alertas_actuales
            if isinstance(alerta, dict) and alerta.get("id")
        ]
        if not alertas_ids or not callable(self.limpiar_alertas_callback):
            return
        self.limpiar_alertas_callback(alertas_ids)
        self.actualizar_panel()

    def _probar_alarma(self):
        if callable(self.probar_alarma_callback):
            self.probar_alarma_callback()

    def _abrir_sonidos(self):
        if callable(self.abrir_sonidos_callback):
            self.abrir_sonidos_callback()
