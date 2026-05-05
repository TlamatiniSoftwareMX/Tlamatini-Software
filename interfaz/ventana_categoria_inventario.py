import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from core.inventario import (
    obtener_categoria,
    listar_subcategorias,
    listar_unidades,
    listar_items,
    agregar_item,
    actualizar_item,
    eliminar_item_por_id,
    listar_alertas_inventario,
)
from core.inventario_foto import capturar_y_analizar_inventario
from core.window_geometry import habilitar_scroll_mouse


class VentanaCategoriaInventario(tk.Toplevel):
    def __init__(self, master, categoria_id: str):
        super().__init__(master)
        self.categoria_id = categoria_id
        self.categoria = obtener_categoria(categoria_id)
        self.item_editando_id = None
        self.ultima_foto = ""

        nombre = self.categoria.get("nombre", "Categoría") if self.categoria else "Categoría"
        self.title(f"TLAMATINI - Inventario - {nombre}")
        self.geometry("1380x840")
        self.configure(bg="#111827")

        self.crear_ui()
        self.actualizar_subcategorias()
        self.actualizar_unidades()
        self.refrescar_tabla()
        self.refrescar_alertas()

    def _es_insumos_medicos(self) -> bool:
        nombre = (self.categoria.get("nombre", "") if self.categoria else "").strip().lower()
        return nombre in {"insumos medicos", "insumos médicos"}

    def crear_ui(self):
        nombre_categoria = self.categoria.get("nombre", "Categoría")
        principal = tk.Frame(self, bg="#111827")
        principal.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            principal,
            text=f"INVENTARIO - {nombre_categoria.upper()}",
            font=("Arial", 20, "bold"),
            bg="#111827",
            fg="white"
        ).pack(anchor="w", pady=(0, 8))

        self.label_estado = tk.Label(
            principal,
            text="Listo para capturar información.",
            font=("Arial", 11),
            bg="#111827",
            fg="#93C5FD"
        )
        self.label_estado.pack(anchor="w", pady=(0, 12))

        cuerpo = tk.Frame(principal, bg="#111827")
        cuerpo.pack(fill="both", expand=True)

        panel_izq = tk.Frame(cuerpo, bg="#1F2937", width=440)
        panel_izq.pack(side="left", fill="y", padx=(0, 12))
        panel_izq.pack_propagate(False)

        panel_der = tk.Frame(cuerpo, bg="#111827")
        panel_der.pack(side="left", fill="both", expand=True)

        tk.Label(panel_izq, text="Captura / edición", font=("Arial", 15, "bold"), bg="#1F2937", fg="white").pack(anchor="w", padx=12, pady=(12, 10))

        form = tk.Frame(panel_izq, bg="#1F2937")
        form.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.label_modo = tk.Label(form, text="Modo: nuevo registro", font=("Arial", 10, "bold"), bg="#1F2937", fg="#FBBF24")
        self.label_modo.pack(anchor="w", pady=(0, 8))

        tk.Label(form, text="Subcategoría", bg="#1F2937", fg="white").pack(anchor="w")
        self.combo_subcategoria = ttk.Combobox(form, state="readonly", width=36)
        self.combo_subcategoria.pack(anchor="w", pady=(4, 8))

        if self._es_insumos_medicos():
            fila_1 = tk.Frame(form, bg="#1F2937")
            fila_1.pack(fill="x", pady=(0, 8))
            for col in range(3):
                fila_1.grid_columnconfigure(col, weight=1, uniform="med_form_old")

            tk.Label(fila_1, text="Nombre", bg="#1F2937", fg="white").grid(row=0, column=0, sticky="w")
            tk.Label(fila_1, text="Formula", bg="#1F2937", fg="white").grid(row=0, column=1, sticky="w", padx=(10, 0))
            tk.Label(fila_1, text="Cantidad", bg="#1F2937", fg="white").grid(row=0, column=2, sticky="w", padx=(10, 0))

            self.entry_nombre = tk.Entry(fila_1, font=("Arial", 11), width=12)
            self.entry_nombre.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self.entry_peso = tk.Entry(fila_1, font=("Arial", 11), width=12)
            self.entry_peso.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(4, 0))
            self.entry_cantidad = tk.Entry(fila_1, font=("Arial", 11), width=12)
            self.entry_cantidad.grid(row=1, column=2, sticky="ew", padx=(10, 0), pady=(4, 0))

            fila_2 = tk.Frame(form, bg="#1F2937")
            fila_2.pack(fill="x", pady=(0, 8))
            for col in range(3):
                fila_2.grid_columnconfigure(col, weight=1, uniform="med_form_old")

            tk.Label(fila_2, text="Unidad", bg="#1F2937", fg="white").grid(row=0, column=0, sticky="w")
            tk.Label(fila_2, text="Caducidad", bg="#1F2937", fg="white").grid(row=0, column=1, sticky="w", padx=(10, 0))
            tk.Label(fila_2, text="Stock", bg="#1F2937", fg="white").grid(row=0, column=2, sticky="w", padx=(10, 0))

            self.combo_unidad = ttk.Combobox(fila_2, state="readonly", width=12, values=["Mililitros", "Miligramos", "Gramos"])
            self.combo_unidad.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self.entry_caducidad = tk.Entry(fila_2, font=("Arial", 11), width=12)
            self.entry_caducidad.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(4, 0))
            self.entry_minimo = tk.Entry(fila_2, font=("Arial", 11), width=12)
            self.entry_minimo.grid(row=1, column=2, sticky="ew", padx=(10, 0), pady=(4, 0))
            self.combo_unidad.set("Miligramos")
            self.entry_lote = tk.Entry(form, font=("Arial", 11), width=38)
        else:
            tk.Label(form, text="Nombre del artículo", bg="#1F2937", fg="white").pack(anchor="w")
            self.entry_nombre = tk.Entry(form, font=("Arial", 11), width=38)
            self.entry_nombre.pack(anchor="w", pady=(4, 8))

            fila_cantidad = tk.Frame(form, bg="#1F2937")
            fila_cantidad.pack(fill="x", pady=(0, 8))

            tk.Label(fila_cantidad, text="Cantidad", bg="#1F2937", fg="white").grid(row=0, column=0, sticky="w")
            tk.Label(fila_cantidad, text="Unidad", bg="#1F2937", fg="white").grid(row=0, column=1, sticky="w", padx=(10, 0))
            tk.Label(fila_cantidad, text="Mínimo", bg="#1F2937", fg="white").grid(row=0, column=2, sticky="w", padx=(10, 0))

            self.entry_cantidad = tk.Entry(fila_cantidad, font=("Arial", 11), width=10)
            self.entry_cantidad.grid(row=1, column=0, sticky="w", pady=(4, 0))

            self.combo_unidad = ttk.Combobox(fila_cantidad, state="readonly", width=12)
            self.combo_unidad.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(4, 0))

            self.entry_minimo = tk.Entry(fila_cantidad, font=("Arial", 11), width=10)
            self.entry_minimo.grid(row=1, column=2, sticky="w", padx=(10, 0), pady=(4, 0))

            fila_extra = tk.Frame(form, bg="#1F2937")
            fila_extra.pack(fill="x", pady=(0, 8))

            tk.Label(fila_extra, text="Peso / contenido", bg="#1F2937", fg="white").grid(row=0, column=0, sticky="w")
            tk.Label(fila_extra, text="Caducidad", bg="#1F2937", fg="white").grid(row=0, column=1, sticky="w", padx=(10, 0))
            tk.Label(fila_extra, text="Lote", bg="#1F2937", fg="white").grid(row=0, column=2, sticky="w", padx=(10, 0))

            self.entry_peso = tk.Entry(fila_extra, font=("Arial", 11), width=12)
            self.entry_peso.grid(row=1, column=0, sticky="w", pady=(4, 0))

            self.entry_caducidad = tk.Entry(fila_extra, font=("Arial", 11), width=14)
            self.entry_caducidad.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(4, 0))

            self.entry_lote = tk.Entry(fila_extra, font=("Arial", 11), width=12)
            self.entry_lote.grid(row=1, column=2, sticky="w", padx=(10, 0), pady=(4, 0))

        tk.Label(form, text="Datos nutrimentales", bg="#1F2937", fg="white").pack(anchor="w")
        self.txt_nutricion = ScrolledText(form, width=42, height=5, font=("Arial", 10))
        self.txt_nutricion.pack(anchor="w", pady=(4, 8))

        tk.Label(form, text="Descripcion" if self._es_insumos_medicos() else "Observaciones", bg="#1F2937", fg="white").pack(anchor="w")
        self.txt_observaciones = ScrolledText(form, width=42, height=4, font=("Arial", 10))
        self.txt_observaciones.pack(anchor="w", pady=(4, 8))

        self.label_foto = tk.Label(
            form,
            text="Foto: ninguna",
            bg="#1F2937",
            fg="#93C5FD",
            wraplength=380,
            justify="left"
        )
        self.label_foto.pack(anchor="w", pady=(0, 8))

        barra_botones = tk.Frame(form, bg="#1F2937")
        barra_botones.pack(fill="x", pady=(8, 0))

        tk.Button(barra_botones, text="Guardar artículo", bg="#059669", fg="white", command=self.guardar_articulo).pack(side="left", padx=(0, 8))
        tk.Button(barra_botones, text="Actualizar", bg="#0EA5E9", fg="white", command=self.actualizar_articulo).pack(side="left", padx=(0, 8))
        tk.Button(barra_botones, text="Agregar por foto", bg="#2563EB", fg="white", command=self.agregar_por_foto).pack(side="left", padx=(0, 8))
        tk.Button(barra_botones, text="Limpiar", bg="#6B7280", fg="white", command=self.limpiar_formulario).pack(side="left")

        encabezado = tk.Frame(panel_der, bg="#111827")
        encabezado.pack(fill="x", pady=(0, 8))

        tk.Label(encabezado, text=f"Listado: {nombre_categoria}", font=("Arial", 15, "bold"), bg="#111827", fg="white").pack(side="left")
        tk.Button(encabezado, text="Cargar a edición", bg="#F59E0B", fg="black", command=self.cargar_seleccionado).pack(side="right", padx=(8, 0))
        tk.Button(encabezado, text="Eliminar seleccionado", bg="#DC2626", fg="white", command=self.eliminar_seleccionado).pack(side="right")

        frame_tabla = tk.Frame(panel_der, bg="#111827")
        frame_tabla.pack(fill="both", expand=True)

        columnas = ("nombre", "subcategoria", "cantidad", "unidad", "peso", "caducidad", "minimo")
        self.tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=16)

        for col, txt, w in [
            ("nombre", "Nombre", 180),
            ("subcategoria", "Subcategoría", 140),
            ("cantidad", "Cantidad", 80),
            ("unidad", "Unidad", 80),
            ("peso", "Peso / contenido", 120),
            ("caducidad", "Caducidad", 110),
            ("minimo", "Mínimo", 80),
        ]:
            self.tabla.heading(col, text=txt)
            self.tabla.column(col, width=w, anchor="center" if col not in ("nombre", "subcategoria") else "w")

        self.tabla.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla.yview)
        scroll.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=scroll.set)
        habilitar_scroll_mouse(frame_tabla, self.tabla)

        frame_alertas = tk.Frame(panel_der, bg="#1F2937", height=160)
        frame_alertas.pack(fill="x", pady=(10, 0))
        frame_alertas.pack_propagate(False)

        tk.Label(frame_alertas, text="Alertas de esta categoría", font=("Arial", 13, "bold"), bg="#1F2937", fg="white").pack(anchor="w", padx=10, pady=(10, 6))

        self.lista_alertas = tk.Listbox(
            frame_alertas,
            bg="#111827",
            fg="#FCA5A5",
            selectbackground="#2563EB",
            selectforeground="white",
            font=("Arial", 10),
            height=6
        )
        self.lista_alertas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def actualizar_subcategorias(self):
        nombre_categoria = self.categoria.get("nombre", "")
        opciones = listar_subcategorias(nombre_categoria)
        self.combo_subcategoria["values"] = opciones
        self.combo_subcategoria.set(opciones[0] if opciones else "general")

    def actualizar_unidades(self):
        nombre_categoria = self.categoria.get("nombre", "")
        opciones = listar_unidades(nombre_categoria)
        self.combo_unidad["values"] = opciones
        self.combo_unidad.set(opciones[0] if opciones else "pzas")

    def refrescar_tabla(self):
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        items = listar_items(self.categoria_id)
        for item in items:
            self.tabla.insert(
                "",
                "end",
                iid=item.get("id", ""),
                values=(
                    item.get("nombre", ""),
                    item.get("subcategoria", ""),
                    item.get("cantidad", ""),
                    item.get("unidad", ""),
                    item.get("peso", ""),
                    item.get("caducidad", ""),
                    item.get("minimo", ""),
                )
            )

    def refrescar_alertas(self):
        self.lista_alertas.delete(0, "end")
        alertas = listar_alertas_inventario(self.categoria_id)

        if not alertas:
            self.lista_alertas.insert("end", "Sin alertas por el momento.")
            return

        for alerta in alertas:
            self.lista_alertas.insert("end", f"- {alerta.get('mensaje', '')}")

    def _validar_nombre(self) -> bool:
        if not self.entry_nombre.get().strip():
            self.label_estado.config(text="Escribe el nombre del artículo antes de guardar.", fg="#FCA5A5")
            return False
        return True

    def guardar_articulo(self):
        if not self._validar_nombre():
            return

        agregar_item(
            categoria_id=self.categoria_id,
            subcategoria=self.combo_subcategoria.get().strip(),
            nombre=self.entry_nombre.get().strip(),
            cantidad=self.entry_cantidad.get().strip(),
            unidad=self.combo_unidad.get().strip(),
            peso_contenido=self.entry_peso.get().strip(),
            caducidad=self.entry_caducidad.get().strip(),
            lote=self.entry_lote.get().strip(),
            observaciones=self.txt_observaciones.get("1.0", "end").strip(),
            foto=self.ultima_foto,
            nutrimentales=self.txt_nutricion.get("1.0", "end").strip(),
            minimo=self.entry_minimo.get().strip(),
        )

        self.refrescar_tabla()
        self.refrescar_alertas()
        self.label_estado.config(text="Artículo guardado correctamente.", fg="#86EFAC")
        self.limpiar_formulario()

    def actualizar_articulo(self):
        if not self.item_editando_id:
            self.label_estado.config(text="Primero carga un registro desde la tabla.", fg="#FCA5A5")
            return

        if not self._validar_nombre():
            return

        ok = actualizar_item(
            item_id=self.item_editando_id,
            categoria_id=self.categoria_id,
            subcategoria=self.combo_subcategoria.get().strip(),
            nombre=self.entry_nombre.get().strip(),
            cantidad=self.entry_cantidad.get().strip(),
            unidad=self.combo_unidad.get().strip(),
            peso_contenido=self.entry_peso.get().strip(),
            caducidad=self.entry_caducidad.get().strip(),
            lote=self.entry_lote.get().strip(),
            observaciones=self.txt_observaciones.get("1.0", "end").strip(),
            foto=self.ultima_foto,
            nutrimentales=self.txt_nutricion.get("1.0", "end").strip(),
            minimo=self.entry_minimo.get().strip(),
        )

        if ok:
            self.refrescar_tabla()
            self.refrescar_alertas()
            self.label_estado.config(text="Artículo actualizado correctamente.", fg="#86EFAC")
            self.limpiar_formulario()
        else:
            self.label_estado.config(text="No se pudo actualizar el artículo.", fg="#FCA5A5")

    def agregar_por_foto(self):
        resultado = capturar_y_analizar_inventario()
        estado = resultado.get("estado", "")

        if estado == "cancelado":
            self.label_estado.config(text="Captura cancelada. La ventana sigue abierta y no se perdió nada.", fg="#FBBF24")
            return

        if estado == "error":
            self.label_estado.config(text=resultado.get("mensaje", "No se pudo usar la cámara."), fg="#FCA5A5")
            return

        self.ultima_foto = resultado.get("ruta_foto", "")
        self.label_foto.config(text=f"Foto: {self.ultima_foto if self.ultima_foto else 'ninguna'}")

        nombre = resultado.get("nombre_sugerido", "").strip()
        peso = resultado.get("peso_sugerido", "").strip()
        caducidad = resultado.get("caducidad_sugerida", "").strip()
        nutri = resultado.get("datos_nutrimentales", "").strip()

        if nombre:
            self.entry_nombre.delete(0, "end")
            self.entry_nombre.insert(0, nombre)

        if peso:
            self.entry_peso.delete(0, "end")
            self.entry_peso.insert(0, peso)

        if caducidad:
            self.entry_caducidad.delete(0, "end")
            self.entry_caducidad.insert(0, caducidad)

        if nutri:
            self.txt_nutricion.delete("1.0", "end")
            self.txt_nutricion.insert("1.0", nutri)

        texto_ocr = resultado.get("texto_ocr", "").strip()
        if texto_ocr:
            self.txt_observaciones.delete("1.0", "end")
            self.txt_observaciones.insert("1.0", f"OCR capturado:\n{texto_ocr[:1200]}")

        self.label_estado.config(
            text="Foto analizada. Revisa los campos precargados y guarda cuando estés listo.",
            fg="#93C5FD"
        )

    def cargar_seleccionado(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            self.label_estado.config(text="Selecciona un registro de la tabla para editarlo.", fg="#FBBF24")
            return

        item_id = seleccion[0]
        items = listar_items(self.categoria_id)
        item = next((x for x in items if x.get("id") == item_id), None)

        if not item:
            self.label_estado.config(text="No se encontró el artículo seleccionado.", fg="#FCA5A5")
            return

        self.item_editando_id = item_id
        self.label_modo.config(text=f"Modo: editando {item.get('nombre', '')}")

        self.combo_subcategoria.set(item.get("subcategoria", ""))
        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, item.get("nombre", ""))

        self.entry_cantidad.delete(0, "end")
        self.entry_cantidad.insert(0, item.get("cantidad", ""))

        self.combo_unidad.set(item.get("unidad", ""))

        self.entry_minimo.delete(0, "end")
        self.entry_minimo.insert(0, item.get("minimo", ""))

        self.entry_peso.delete(0, "end")
        self.entry_peso.insert(0, item.get("peso", ""))

        self.entry_caducidad.delete(0, "end")
        self.entry_caducidad.insert(0, item.get("caducidad", ""))

        self.entry_lote.delete(0, "end")
        self.entry_lote.insert(0, item.get("lote", ""))

        self.txt_nutricion.delete("1.0", "end")
        self.txt_nutricion.insert("1.0", item.get("datos_nutrimentales", ""))

        self.txt_observaciones.delete("1.0", "end")
        self.txt_observaciones.insert("1.0", item.get("observaciones", ""))

        self.ultima_foto = item.get("foto", "")
        self.label_foto.config(text=f"Foto: {self.ultima_foto if self.ultima_foto else 'ninguna'}")
        self.label_estado.config(text="Registro cargado en edición.", fg="#93C5FD")

    def eliminar_seleccionado(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            self.label_estado.config(text="Selecciona un registro para eliminar.", fg="#FBBF24")
            return

        item_id = seleccion[0]
        ok = eliminar_item_por_id(item_id)

        if ok:
            self.refrescar_tabla()
            self.refrescar_alertas()
            self.limpiar_formulario()
            self.label_estado.config(text="Registro eliminado correctamente.", fg="#86EFAC")
        else:
            self.label_estado.config(text="No se pudo eliminar el registro.", fg="#FCA5A5")

    def limpiar_formulario(self):
        self.item_editando_id = None
        self.label_modo.config(text="Modo: nuevo registro")
        self.entry_nombre.delete(0, "end")
        self.entry_cantidad.delete(0, "end")
        self.entry_minimo.delete(0, "end")
        self.entry_peso.delete(0, "end")
        self.entry_caducidad.delete(0, "end")
        self.entry_lote.delete(0, "end")
        self.txt_nutricion.delete("1.0", "end")
        self.txt_observaciones.delete("1.0", "end")
        self.ultima_foto = ""
        self.label_foto.config(text="Foto: ninguna")
        self.actualizar_subcategorias()
        self.actualizar_unidades()
