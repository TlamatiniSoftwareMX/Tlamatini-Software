import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from core.codigos import (
    buscar_codigo,
    eliminar_codigo,
    generar_codigo_libre,
    listar_codigos,
    listar_items_inventario_para_codigos,
    reaplicar_codigo_a_item,
)
from core.inventario_foto import capturar_codigo_barras_inventario
from core.window_geometry import aplicar_geometria_relativa


class VentanaCodigos:
    def __init__(self, master):
        self.master = master
        self.root = tk.Toplevel(master)
        self.root.title("TLAMATINI - Codigos")
        self.root.configure(bg="#08111f")
        self.root.minsize(960, 620)
        aplicar_geometria_relativa(self.root, master, rel_w=0.96, rel_h=0.94, min_w=960, min_h=620, pad=12)

        self.ui = {
            "fondo": "#08111f",
            "panel": "#0d1a2d",
            "panel_2": "#10233c",
            "borde": "#1d4568",
            "texto": "#edf7ff",
            "texto_dim": "#8aa6bf",
            "acento": "#35d8ff",
            "ok": "#169c72",
            "warn": "#f59e0b",
            "danger": "#dc2626",
        }
        self.items_index = {}
        self.codigos_index = {}
        self.codigo_preview_img = None
        self._configurar_estilos()
        self._crear_ui()
        self._refrescar_todo()

    def _configurar_estilos(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Codigos.Treeview", background="#071321", foreground="white", fieldbackground="#071321", rowheight=28, font=("Arial", 10))
        style.configure("Codigos.Treeview.Heading", background="#0f2239", foreground="white", font=("Arial", 10, "bold"))
        style.map("Codigos.Treeview", background=[("selected", "#1d4e6d")], foreground=[("selected", "white")])

    def _crear_ui(self):
        cont = tk.Frame(self.root, bg=self.ui["fondo"])
        cont.pack(fill="both", expand=True, padx=14, pady=14)
        cont.grid_rowconfigure(1, weight=1)
        cont.grid_rowconfigure(2, weight=1)
        cont.grid_columnconfigure(0, weight=1)
        cont.grid_columnconfigure(1, weight=1)

        tk.Label(cont, text="CODIGOS", font=("Arial", 20, "bold"), bg=self.ui["fondo"], fg=self.ui["texto"]).grid(row=0, column=0, columnspan=2, sticky="w")

        panel_items = tk.Frame(cont, bg=self.ui["panel"], highlightthickness=1, highlightbackground=self.ui["borde"])
        panel_items.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))
        panel_items.grid_rowconfigure(2, weight=1)
        panel_items.grid_columnconfigure(0, weight=1)

        tk.Label(panel_items, text="Inventario", font=("Arial", 14, "bold"), bg=self.ui["panel"], fg=self.ui["texto"]).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.entry_buscar_item = tk.Entry(panel_items, font=("Arial", 11), bg="#071321", fg="white", insertbackground="white", relief="flat")
        self.entry_buscar_item.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.entry_buscar_item.bind("<KeyRelease>", lambda _e: self._refrescar_items())

        self.tree_items = ttk.Treeview(panel_items, columns=("categoria", "nombre", "tipo", "codigo"), show="headings", style="Codigos.Treeview")
        for col, title, width in [
            ("categoria", "Categoría", 140),
            ("nombre", "Nombre", 180),
            ("tipo", "Tipo", 130),
            ("codigo", "Código actual", 130),
        ]:
            self.tree_items.heading(col, text=title)
            self.tree_items.column(col, width=width, anchor="center")
        self.tree_items.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 10))

        barra_items = tk.Frame(panel_items, bg=self.ui["panel"])
        barra_items.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        tk.Button(barra_items, text="Generar", font=("Arial", 11, "bold"), bg=self.ui["ok"], fg="white", relief="flat", command=self._generar_codigo).pack(side="left")

        panel_codigos = tk.Frame(cont, bg=self.ui["panel_2"], highlightthickness=1, highlightbackground=self.ui["borde"])
        panel_codigos.grid(row=1, column=1, sticky="nsew", pady=(10, 0))
        panel_codigos.grid_rowconfigure(2, weight=1)
        panel_codigos.grid_rowconfigure(4, weight=1)
        panel_codigos.grid_columnconfigure(0, weight=1)

        tk.Label(panel_codigos, text="Códigos Generados", font=("Arial", 14, "bold"), bg=self.ui["panel_2"], fg=self.ui["texto"]).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.entry_buscar_codigo = tk.Entry(panel_codigos, font=("Arial", 11), bg="#071321", fg="white", insertbackground="white", relief="flat")
        self.entry_buscar_codigo.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.entry_buscar_codigo.bind("<KeyRelease>", lambda _e: self._refrescar_codigos())

        self.tree_codigos = ttk.Treeview(panel_codigos, columns=("code", "nombre", "categoria", "status"), show="headings", style="Codigos.Treeview")
        for col, title, width in [
            ("code", "Código", 140),
            ("nombre", "Nombre", 170),
            ("categoria", "Categoría", 120),
            ("status", "Estado", 90),
        ]:
            self.tree_codigos.heading(col, text=title)
            self.tree_codigos.column(col, width=width, anchor="center")
        self.tree_codigos.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.tree_codigos.bind("<<TreeviewSelect>>", self._mostrar_detalle_codigo)

        barra_codigos = tk.Frame(panel_codigos, bg=self.ui["panel_2"])
        barra_codigos.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        tk.Button(barra_codigos, text="Escanear y guardar", font=("Arial", 10, "bold"), bg=self.ui["ok"], fg="white", relief="flat", command=self._escanear_y_guardar).pack(side="left", padx=(8, 0))
        tk.Button(barra_codigos, text="Eliminar", font=("Arial", 10, "bold"), bg=self.ui["danger"], fg="white", relief="flat", command=self._eliminar_codigo).pack(side="left", padx=(8, 0))

        panel_detalle = tk.Frame(panel_codigos, bg=self.ui["panel_2"])
        panel_detalle.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))
        panel_detalle.grid_columnconfigure(0, weight=0, minsize=700)
        panel_detalle.grid_columnconfigure(1, weight=1, minsize=320)
        panel_detalle.grid_rowconfigure(0, weight=1)

        self.preview_frame = tk.Frame(
            panel_detalle,
            bg="white",
            width=700,
            height=320,
            relief="flat",
        )
        self.preview_frame.grid(row=0, column=0, sticky="nw", padx=(0, 32))
        self.preview_frame.grid_propagate(False)

        self.lbl_preview = tk.Label(
            self.preview_frame,
            text="Sin vista previa",
            bg="white",
            fg="black",
            relief="flat",
            anchor="center",
        )
        self.lbl_preview.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_detalle = tk.Label(
            panel_detalle,
            text="Selecciona un código para ver su asociación.",
            bg=self.ui["panel_2"],
            fg=self.ui["texto_dim"],
            justify="left",
            wraplength=320,
            font=("Arial", 10),
        )
        self.lbl_detalle.grid(row=0, column=1, sticky="nwe", padx=(24, 0))

    def _refrescar_todo(self):
        self._refrescar_items()
        self._refrescar_codigos()

    def _refrescar_items(self):
        self.items_index = {}
        filtro = self.entry_buscar_item.get().strip().lower() if hasattr(self, "entry_buscar_item") else ""
        for iid in self.tree_items.get_children():
            self.tree_items.delete(iid)
        for item in listar_items_inventario_para_codigos():
            texto = " ".join([item["categoria"], item["nombre"], item["tipo"], item["codigo_barras"], item["especificaciones"]]).lower()
            if filtro and filtro not in texto:
                continue
            iid = item["id"]
            self.items_index[iid] = item
            self.tree_items.insert("", "end", iid=iid, values=(item["categoria"], item["nombre"], item["tipo"], item["codigo_barras"]))

    def _refrescar_codigos(self):
        seleccionado = ""
        seleccion_actual = self.tree_codigos.selection()
        if seleccion_actual:
            seleccionado = seleccion_actual[0]
        self.codigos_index = {}
        filtro = self.entry_buscar_codigo.get().strip().lower() if hasattr(self, "entry_buscar_codigo") else ""
        for iid in self.tree_codigos.get_children():
            self.tree_codigos.delete(iid)
        for registro in listar_codigos():
            texto = " ".join([registro.get("code", ""), registro.get("nombre", ""), registro.get("categoria", ""), registro.get("especificaciones", ""), registro.get("status", "")]).lower()
            if filtro and filtro not in texto:
                continue
            iid = registro.get("code", "")
            self.codigos_index[iid] = registro
            self.tree_codigos.insert("", "end", iid=iid, values=(registro.get("code", ""), registro.get("nombre", ""), registro.get("categoria", ""), registro.get("status", "")))
        if seleccionado and seleccionado in self.codigos_index:
            self.tree_codigos.selection_set(seleccionado)
            self.tree_codigos.focus(seleccionado)
            self.tree_codigos.see(seleccionado)
            self._mostrar_detalle_codigo()
        elif not self.codigos_index:
            self._mostrar_detalle_codigo()

    def _item_seleccionado(self):
        seleccion = self.tree_items.selection()
        if not seleccion:
            return None
        return self.items_index.get(seleccion[0])

    def _codigo_seleccionado(self):
        seleccion = self.tree_codigos.selection()
        if not seleccion:
            return None
        return self.codigos_index.get(seleccion[0])

    def _generar_codigo(self):
        try:
            registro = generar_codigo_libre()
        except Exception as exc:
            messagebox.showwarning("Códigos", str(exc), parent=self.root)
            return
        messagebox.showinfo(
            "Códigos",
            f'Se generó {registro["code"]}. Ya puedes usarlo después en alimentos o inventario; cuando el ítem quede guardado, la imagen se actualizará con el nombre del ítem.',
            parent=self.root,
        )
        self._refrescar_todo()
        if registro["code"] in self.codigos_index:
            self.tree_codigos.selection_set(registro["code"])
            self.tree_codigos.focus(registro["code"])
            self.tree_codigos.see(registro["code"])
            self._mostrar_detalle_codigo()

    def _eliminar_codigo(self):
        registro = self._codigo_seleccionado()
        if not registro:
            messagebox.showwarning("Códigos", "Selecciona un código para eliminar.", parent=self.root)
            return
        confirmar = messagebox.askyesno(
            "Códigos",
            f'¿Eliminar el código "{registro.get("code", "")}"?\nSi estaba asociado a un ítem, también se quitará esa asociación.',
            parent=self.root,
        )
        if not confirmar:
            return
        try:
            eliminar_codigo(registro.get("code", ""))
        except Exception as exc:
            messagebox.showwarning("Códigos", str(exc), parent=self.root)
            return
        self._refrescar_todo()
        messagebox.showinfo("Códigos", "Código eliminado.", parent=self.root)

    def _escanear_y_guardar(self):
        seleccionado = self._codigo_seleccionado()
        resultado = capturar_codigo_barras_inventario()
        estado = resultado.get("estado", "")
        if estado == "cancelado":
            return
        if estado == "error":
            messagebox.showwarning("Escáner", resultado.get("mensaje", "No se pudo usar la cámara."), parent=self.root)
            return
        code = str(resultado.get("codigo_barras", "")).strip().upper()
        if not code:
            messagebox.showwarning("Escáner", "No se detectó un código de barras válido.", parent=self.root)
            return
        if seleccionado and seleccionado.get("code", "") != code:
            messagebox.showwarning("Códigos", f'El código leído ({code}) no coincide con el seleccionado ({seleccionado.get("code", "")}).', parent=self.root)
            return
        try:
            registro = buscar_codigo(code)
            if not registro:
                raise ValueError("Ese código no existe en la lista de códigos generados.")
            item = reaplicar_codigo_a_item(code)
        except Exception as exc:
            messagebox.showwarning("Códigos", str(exc), parent=self.root)
            return
        self._refrescar_todo()
        messagebox.showinfo("Códigos", f'Se guardó "{code}" en el item asociado "{item.get("nombre", "")}".', parent=self.root)

    def _mostrar_detalle_codigo(self, event=None):
        registro = self._codigo_seleccionado()
        if not registro:
            self.lbl_detalle.config(text="Selecciona un código para ver su asociación.")
            self.lbl_preview.config(image="", text="Sin vista previa")
            self.codigo_preview_img = None
            return
        texto = "\n".join(
            [
                f'Código: {registro.get("code", "")}',
                f'Nombre: {registro.get("nombre", "")}',
                f'Categoría: {registro.get("categoria", "")}',
                f'Estado: {registro.get("status", "")}',
                f'Item ID: {registro.get("item_id", "")}',
                f'Especificaciones: {registro.get("especificaciones", "")}',
                "Asociación: se puede generar primero y asociar después al guardar un ítem.",
            ]
        )
        self.lbl_detalle.config(text=texto)
        self._mostrar_preview_codigo(registro)

    def _mostrar_preview_codigo(self, registro):
        ruta = str((registro or {}).get("image_path", "")).strip()
        if not ruta:
            self.lbl_preview.config(image="", text="Sin vista previa")
            self.codigo_preview_img = None
            return
        try:
            image = Image.open(ruta)
            ancho = max(640, self.preview_frame.winfo_width() - 24)
            alto = max(260, self.preview_frame.winfo_height() - 24)
            image.thumbnail((ancho, alto))
            self.codigo_preview_img = ImageTk.PhotoImage(image)
            self.lbl_preview.config(image=self.codigo_preview_img, text="")
        except Exception:
            self.lbl_preview.config(image="", text="Sin vista previa")
            self.codigo_preview_img = None
