import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

from core.perfiles import (
    actualizar_persona,
    eliminar_persona,
    establecer_medicamentos_requeridos,
    listar_personas,
    registrar_persona,
)
from core.ui_theme import FUTURISTA_OSCURO
from core.window_geometry import aplicar_geometria_relativa, crear_contenedor_scrollable, habilitar_scroll_mouse


class DialogoPerfil(tk.Toplevel):
    def __init__(self, parent, persona=None):
        super().__init__(parent)
        self.persona = persona or {}
        self.resultado = None
        self.medicamentos = [dict(m) for m in self.persona.get("medicamentos_requeridos", [])]

        self.title("Registrar perfil" if not persona else "Editar perfil")
        self.configure(bg="#08152f")
        self.resizable(True, True)
        if parent is not None:
            self.transient(parent)
        aplicar_geometria_relativa(self, parent, rel_w=0.62, rel_h=0.84, min_w=820, min_h=720)

        self._crear_ui()
        self._cargar_persona()
        self._refrescar_medicamentos()
        self._configurar_navegacion_teclado()
        self.update_idletasks()
        self.lift()
        try:
            self.focus_force()
            self.grab_set()
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _crear_ui(self):
        exterior = tk.Frame(self, bg="#08152f")
        exterior.pack(fill="both", expand=True)
        exterior.grid_columnconfigure(0, weight=1)
        exterior.grid_rowconfigure(0, weight=1)

        _, _, cont = crear_contenedor_scrollable(exterior, bg="#08152f")

        tk.Label(
            cont,
            text="Registrar perfil" if not self.persona else "Editar perfil",
            font=("Arial", 24, "bold"),
            bg="#08152f",
            fg="white",
        ).pack(anchor="w", padx=18, pady=(18, 12))

        panel = tk.Frame(cont, bg="#13223f", highlightthickness=1, highlightbackground="#29456f")
        panel.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        fila1 = tk.Frame(panel, bg="#13223f")
        fila1.pack(fill="x", padx=12, pady=(12, 4))
        self.entry_nombre = self._campo_pack(fila1, "Nombre")
        self.entry_fecha_nacimiento = self._campo_pack(fila1, "Fecha de nacimiento")
        self.combo_sexo = self._campo_combo(fila1, "Sexo", ["", "Femenino", "Masculino"])

        fila2 = tk.Frame(panel, bg="#13223f")
        fila2.pack(fill="x", padx=12, pady=4)
        self.entry_peso = self._campo_pack(fila2, "Peso kg")
        self.entry_altura = self._campo_pack(fila2, "Altura cm")
        self.entry_enfermedades = self._campo_pack(fila2, "Enfermedades")

        meds = tk.Frame(panel, bg="#13223f")
        meds.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(meds, text="Medicamentos (opcional)", font=("Arial", 11, "bold"), bg="#13223f", fg="white").pack(anchor="w", pady=(0, 6))

        meds_fila = tk.Frame(meds, bg="#13223f")
        meds_fila.pack(fill="x")
        self.med_nombre = self._campo_pack(meds_fila, "Nombre", font_size=11)
        self.med_formula = self._campo_pack(meds_fila, "Formula", font_size=11)
        self.med_indicacion = self._campo_pack(meds_fila, "Indicacion", font_size=11)
        tk.Button(
            meds_fila,
            text="Agregar",
            font=("Arial", 10, "bold"),
            bg="#169c72",
            fg="white",
            relief="flat",
            command=self._agregar_medicamento,
        ).pack(side="left", padx=(8, 0), pady=(18, 0))

        tabla = tk.Frame(meds, bg="#13223f")
        tabla.pack(fill="x", pady=(10, 0))
        self.tree_meds = ttk.Treeview(tabla, columns=("nombre", "formula", "indicacion"), show="headings", height=5)
        self.tree_meds.pack(fill="x")
        for col, titulo, width in [("nombre", "Medicamento", 220), ("formula", "Formula", 160), ("indicacion", "Indicacion", 220)]:
            self.tree_meds.heading(col, text=titulo)
            self.tree_meds.column(col, width=width, anchor="center")
        tk.Button(tabla, text="Quitar seleccionado", font=("Arial", 10), bg="#8b1e2d", fg="white", relief="flat", command=self._quitar_medicamento).pack(anchor="e", pady=(8, 0))

        obs = tk.Frame(panel, bg="#13223f")
        obs.pack(fill="both", expand=True, padx=12, pady=(12, 4))
        tk.Label(obs, text="Observaciones", font=("Arial", 10), bg="#13223f", fg="white").pack(anchor="w", pady=(0, 4))
        self.txt_obs = tk.Text(obs, height=7, font=("Arial", 11), wrap="word", bg="white", fg="black")
        self.txt_obs.pack(fill="both", expand=True)

        barra = tk.Frame(cont, bg="#08152f")
        barra.pack(fill="x", padx=18, pady=(0, 18))
        tk.Button(barra, text="Guardar", font=("Arial", 11, "bold"), bg="#169c72", fg="white", relief="flat", command=self._guardar).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(barra, text="Cancelar", font=("Arial", 11), bg="#64748b", fg="white", relief="flat", command=self.destroy).pack(side="left", fill="x", expand=True, padx=(4, 0))

    def _campo_pack(self, parent, titulo, font_size=12):
        marco = tk.Frame(parent, bg="#13223f")
        marco.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(marco, text=titulo, font=("Arial", 10), bg="#13223f", fg="white").pack(anchor="w", pady=(0, 4))
        entry = tk.Entry(marco, font=("Arial", font_size))
        entry.pack(fill="x")
        return entry

    def _campo_combo(self, parent, titulo, values):
        marco = tk.Frame(parent, bg="#13223f")
        marco.pack(side="left", fill="x", expand=True)
        tk.Label(marco, text=titulo, font=("Arial", 10), bg="#13223f", fg="white").pack(anchor="w", pady=(0, 4))
        combo = ttk.Combobox(marco, font=("Arial", 11), state="readonly", values=values)
        combo.pack(fill="x")
        return combo

    def _configurar_navegacion_teclado(self):
        self._grid_navegacion = [
            [self.entry_nombre, self.entry_fecha_nacimiento, self.combo_sexo],
            [self.entry_peso, self.entry_altura, self.entry_enfermedades],
            [self.med_nombre, self.med_formula, self.med_indicacion],
            [self.txt_obs],
        ]

        for fila_idx, fila in enumerate(self._grid_navegacion):
            for col_idx, widget in enumerate(fila):
                widget.bind("<Up>", lambda event, r=fila_idx, c=col_idx: self._mover_foco(r, c, -1, 0))
                widget.bind("<Down>", lambda event, r=fila_idx, c=col_idx: self._mover_foco(r, c, 1, 0))
                widget.bind("<Left>", lambda event, r=fila_idx, c=col_idx: self._mover_foco(r, c, 0, -1))
                widget.bind("<Right>", lambda event, r=fila_idx, c=col_idx: self._mover_foco(r, c, 0, 1))

    def _mover_foco(self, fila, col, delta_fila, delta_col):
        destino_fila = max(0, min(fila + delta_fila, len(self._grid_navegacion) - 1))
        fila_widgets = self._grid_navegacion[destino_fila]
        destino_col = max(0, min(col + delta_col, len(fila_widgets) - 1))
        widget = fila_widgets[destino_col]
        try:
            widget.focus_set()
            if isinstance(widget, tk.Entry):
                widget.icursor("end")
            elif isinstance(widget, tk.Text):
                widget.mark_set("insert", "end-1c")
        except Exception:
            pass
        return "break"

    def _cargar_persona(self):
        if not self.persona:
            return
        self.entry_nombre.insert(0, self.persona.get("nombre", ""))
        self.entry_fecha_nacimiento.insert(0, self.persona.get("fecha_nacimiento", ""))
        self.entry_peso.insert(0, self.persona.get("peso_kg", ""))
        self.entry_altura.insert(0, self.persona.get("altura_cm", ""))
        self.combo_sexo.set(self.persona.get("sexo", ""))
        self.entry_enfermedades.insert(0, self.persona.get("enfermedades", ""))
        self.txt_obs.insert("1.0", self.persona.get("observaciones", ""))

    def _calcular_edad_desde_fecha(self, fecha_nacimiento: str) -> int:
        texto = str(fecha_nacimiento or "").strip()
        if not texto:
            return 0
        try:
            nacimiento = datetime.strptime(texto, "%d-%m-%Y").date()
        except ValueError as exc:
            raise ValueError("La fecha de nacimiento debe ir como d-m-a, por ejemplo 07-04-1998.") from exc
        hoy = datetime.now().date()
        if nacimiento > hoy:
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        return max(0, edad)

    def _agregar_medicamento(self):
        nombre = self.med_nombre.get().strip()
        formula = self.med_formula.get().strip()
        indicacion = self.med_indicacion.get().strip()
        if not nombre and not formula and not indicacion:
            return
        if not nombre:
            messagebox.showwarning("Falta dato", "Si agregas un medicamento, escribe al menos su nombre.", parent=self)
            return
        self.medicamentos.append(
            {
                "nombre": nombre,
                "cantidad_diaria": 0,
                "unidad": "",
                "formula": formula,
                "indicacion": indicacion,
                "gramaje": formula,
                "observaciones": "",
            }
        )
        self.med_nombre.delete(0, "end")
        self.med_formula.delete(0, "end")
        self.med_indicacion.delete(0, "end")
        self._refrescar_medicamentos()

    def _quitar_medicamento(self):
        seleccion = self.tree_meds.selection()
        if not seleccion:
            return
        indice = int(seleccion[0])
        if 0 <= indice < len(self.medicamentos):
            self.medicamentos.pop(indice)
        self._refrescar_medicamentos()

    def _refrescar_medicamentos(self):
        for item in self.tree_meds.get_children():
            self.tree_meds.delete(item)
        for indice, medicamento in enumerate(self.medicamentos):
            self.tree_meds.insert(
                "",
                "end",
                iid=str(indice),
                values=(
                    medicamento.get("nombre", ""),
                    medicamento.get("formula", "")
                    or medicamento.get("gramaje", "")
                    or " ".join(x for x in [medicamento.get("gramaje_1", ""), medicamento.get("gramaje_2", "")] if str(x).strip()),
                    medicamento.get("indicacion", ""),
                ),
            )

    def _guardar(self):
        try:
            nombre = self.entry_nombre.get().strip()
            if not nombre:
                raise ValueError("El nombre es obligatorio.")
            fecha_nacimiento = self.entry_fecha_nacimiento.get().strip()
            if not fecha_nacimiento:
                raise ValueError("La fecha de nacimiento es obligatoria.")
            edad = self._calcular_edad_desde_fecha(fecha_nacimiento)
            self.resultado = {
                "nombre": nombre,
                "rol": "",
                "edad": edad,
                "fecha_nacimiento": fecha_nacimiento,
                "peso_kg": float(self.entry_peso.get().strip() or 0),
                "altura_cm": float(self.entry_altura.get().strip() or 0),
                "sexo": self.combo_sexo.get().strip(),
                "enfermedades": self.entry_enfermedades.get().strip(),
                "actividad": "media",
                "agua_litros_dia": None,
                "raciones_comida_dia": None,
                "observaciones": self.txt_obs.get("1.0", "end").strip(),
                "medicamentos_requeridos": list(self.medicamentos),
            }
            self.destroy()
        except Exception as error:
            messagebox.showwarning("Revisa los datos", str(error), parent=self)


class VentanaPerfiles:
    def __init__(self, root):
        self.root = root
        self.root.title("TLAMATINI - Perfiles")
        self.root.configure(bg="#08152f")
        self.root.minsize(1080, 680)
        aplicar_geometria_relativa(self.root, self.root.master, rel_w=0.94, rel_h=0.92, min_w=1080, min_h=680)

        self.ui = FUTURISTA_OSCURO
        self.bg = self.ui["fondo"]
        self.panel = self.ui["panel"]
        self.fg = self.ui["texto"]
        self.borde = self.ui["borde"]
        self.acento = self.ui["acento"]

        self.personas = []
        self.tarjetas = {}

        self._configurar_estilos()
        self._crear_ui()
        self._refrescar_todo()

    def _configurar_estilos(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", rowheight=28, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

    def _crear_ui(self):
        contenedor = tk.Frame(self.root, bg=self.bg)
        contenedor.pack(fill="both", expand=True)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(1, weight=1)

        header = tk.Frame(contenedor, bg=self.bg)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="PERFILES", font=("Arial", 28, "bold"), bg=self.bg, fg=self.fg).grid(row=0, column=0, sticky="w")
        tk.Button(header, text="Registrar", font=("Arial", 11, "bold"), bg=self.acento, fg="white", relief="flat", padx=16, pady=8, command=self._abrir_registro).grid(row=0, column=1, sticky="e")

        area = tk.Frame(contenedor, bg=self.bg)
        area.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        area.grid_columnconfigure(0, weight=1)
        area.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(area, bg=self.bg, highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(area, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.panel_tarjetas = tk.Frame(self.canvas, bg=self.bg)
        self.panel_window = self.canvas.create_window((0, 0), window=self.panel_tarjetas, anchor="nw")
        self.panel_tarjetas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.panel_window, width=e.width))
        habilitar_scroll_mouse(area, self.canvas)

    def _refrescar_todo(self):
        self.personas = listar_personas()
        self._refrescar_tarjetas()

    def _refrescar_tarjetas(self):
        self.tarjetas = {}
        for widget in self.panel_tarjetas.winfo_children():
            widget.destroy()

        if not self.personas:
            vacio = tk.Frame(self.panel_tarjetas, bg=self.panel, highlightthickness=1, highlightbackground=self.borde)
            vacio.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
            tk.Label(vacio, text="No hay perfiles registrados", font=("Arial", 20, "bold"), bg=self.panel, fg=self.fg).pack(anchor="w", padx=18, pady=(18, 6))
            tk.Label(vacio, text="Usa el botón Registrar para agregar un miembro.", font=("Arial", 11), bg=self.panel, fg="#cbd5e1").pack(anchor="w", padx=18, pady=(0, 18))
            return

        columnas = 2
        for col in range(columnas):
            self.panel_tarjetas.grid_columnconfigure(col, weight=1, uniform="perfil_card")

        for idx, persona in enumerate(self.personas):
            fila = idx // columnas
            col = idx % columnas
            tarjeta = tk.Frame(self.panel_tarjetas, bg=self.panel, highlightthickness=1, highlightbackground=self.borde)
            tarjeta.grid(row=fila, column=col, sticky="nsew", padx=10, pady=10)

            cuerpo = tk.Frame(tarjeta, bg=self.panel)
            cuerpo.pack(fill="both", expand=True, padx=16, pady=16)

            tk.Label(cuerpo, text=persona.get("nombre", ""), font=("Arial", 18, "bold"), bg=self.panel, fg=self.fg).pack(anchor="w")
            resumen = [
                f"Fecha de nacimiento: {persona.get('fecha_nacimiento', '') or 'N/D'}",
                f"Edad: {persona.get('edad', 0)}",
                f"Sexo: {persona.get('sexo', '') or 'N/D'}",
                f"Peso: {persona.get('peso_kg', 0)} kg",
                f"Altura: {persona.get('altura_cm', 0)} cm",
                f"Enfermedades: {persona.get('enfermedades', '') or 'Ninguna'}",
                f"Medicamentos: {len(persona.get('medicamentos_requeridos', []))}",
            ]
            for linea in resumen:
                tk.Label(cuerpo, text=linea, font=("Arial", 11), bg=self.panel, fg="#cbd5e1", justify="left", wraplength=420).pack(anchor="w", pady=(6, 0))

            acciones = tk.Frame(cuerpo, bg=self.panel)
            acciones.pack(fill="x", pady=(14, 0))
            tk.Button(acciones, text="Editar", bg="#d18d19", fg="black", relief="flat", command=lambda p=persona: self._abrir_registro(p)).pack(side="left")
            tk.Button(acciones, text="Eliminar", bg="#cc2f2f", fg="white", relief="flat", command=lambda p=persona: self._eliminar_perfil(p)).pack(side="left", padx=8)

    def _abrir_registro(self, persona=None):
        dialogo = DialogoPerfil(self.root, persona=persona)
        self.root.wait_window(dialogo)
        if not dialogo.resultado:
            return

        datos = dialogo.resultado
        medicamentos = datos.pop("medicamentos_requeridos", [])
        try:
            if persona:
                actualizar_persona(persona["id"], **datos)
                establecer_medicamentos_requeridos(persona["id"], medicamentos)
                messagebox.showinfo("Perfil actualizado", f'Se actualizó "{datos["nombre"]}".', parent=self.root)
            else:
                nuevo = registrar_persona(**datos)
                establecer_medicamentos_requeridos(nuevo["id"], medicamentos)
                messagebox.showinfo("Perfil guardado", f'Se registró a "{datos["nombre"]}".', parent=self.root)
            self._refrescar_todo()
        except Exception as error:
            messagebox.showwarning("Revisa los datos", str(error), parent=self.root)

    def _eliminar_perfil(self, persona):
        if not messagebox.askyesno("Eliminar perfil", f'¿Seguro que quieres eliminar a "{persona.get("nombre", "")}"?', parent=self.root):
            return
        eliminar_persona(persona["id"])
        self._refrescar_todo()
