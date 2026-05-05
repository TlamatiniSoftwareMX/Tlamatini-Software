import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from core.chat_mesh import construir_paquete_mesh, listar_conversations, listar_peers, registrar_peer
from core.inventario import listar_items
from core.mesh_service import get_mesh_session_service
from core.window_geometry import aplicar_geometria_relativa


class VentanaChat:
    def __init__(self, master):
        self.master = master
        self.root = tk.Toplevel(master)
        self.root.title("TLAMATINI - Chat Mesh")
        self.root.configure(bg="#08111f")
        self.root.minsize(1100, 720)
        aplicar_geometria_relativa(self.root, master, rel_w=0.86, rel_h=0.86, min_w=1100, min_h=720, pad=20)

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
        }

        self.peer_index = {}
        self.current_peer_id = ""
        self.mesh_service = get_mesh_session_service()
        self._unsubscribe = self.mesh_service.subscribe(self._manejar_evento_mesh)
        self._configurar_estilos()
        self._crear_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._cerrar)
        self._refrescar_estado()
        self._programar_refresco()

    def _configurar_estilos(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Chat.Treeview",
            background="#071321",
            foreground="white",
            fieldbackground="#071321",
            rowheight=28,
            font=("Arial", 10),
        )
        style.configure("Chat.Treeview.Heading", background="#0f2239", foreground="white", font=("Arial", 10, "bold"))
        style.map("Chat.Treeview", background=[("selected", "#1d4e6d")], foreground=[("selected", "white")])

    def _crear_ui(self):
        cont = tk.Frame(self.root, bg=self.ui["fondo"])
        cont.pack(fill="both", expand=True, padx=14, pady=14)
        cont.grid_rowconfigure(1, weight=1)
        cont.grid_columnconfigure(1, weight=1)
        cont.grid_columnconfigure(2, weight=1)

        barra = tk.Frame(cont, bg=self.ui["fondo"])
        barra.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        barra.grid_columnconfigure(0, weight=1)
        tk.Label(barra, text="CHAT MESH", font=("Arial", 20, "bold"), bg=self.ui["fondo"], fg=self.ui["texto"]).grid(row=0, column=0, sticky="w")
        tk.Label(
            barra,
            text="Preparado para interoperar con nodos ESP32 y T114 mediante sobre JSON estable.",
            font=("Arial", 10),
            bg=self.ui["fondo"],
            fg=self.ui["texto_dim"],
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        panel_nodos = tk.Frame(cont, bg=self.ui["panel"], highlightthickness=1, highlightbackground=self.ui["borde"])
        panel_nodos.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        panel_nodos.grid_rowconfigure(4, weight=1)
        panel_nodos.grid_columnconfigure(0, weight=1)

        tk.Label(panel_nodos, text="Nodos", font=("Arial", 14, "bold"), bg=self.ui["panel"], fg=self.ui["texto"]).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.lbl_status = tk.Label(
            panel_nodos,
            text="Buscando una placa Meshtastic...",
            font=("Arial", 10),
            bg=self.ui["panel"],
            fg=self.ui["texto_dim"],
            justify="left",
            wraplength=260,
        )
        self.lbl_status.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        barra_nodos = tk.Frame(panel_nodos, bg=self.ui["panel"])
        barra_nodos.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        tk.Button(barra_nodos, text="Escanear", font=("Arial", 10, "bold"), bg=self.ui["texto_dim"], fg="black", relief="flat", command=self._refrescar_estado).pack(side="left")
        tk.Button(barra_nodos, text="Conectar", font=("Arial", 10, "bold"), bg=self.ui["ok"], fg="white", relief="flat", command=self._conectar_dispositivo).pack(side="left", padx=(8, 0))
        tk.Button(barra_nodos, text="Nuevo nodo", font=("Arial", 10, "bold"), bg=self.ui["acento"], fg="black", relief="flat", command=self._agregar_peer_manual).pack(side="left")
        tk.Button(barra_nodos, text="Importar comunicación", font=("Arial", 10, "bold"), bg=self.ui["warn"], fg="black", relief="flat", command=self._importar_desde_comunicacion).pack(side="left", padx=(8, 0))

        self.tree_peers = ttk.Treeview(panel_nodos, columns=("node", "hw"), show="headings", style="Chat.Treeview")
        self.tree_peers.heading("node", text="Nodo")
        self.tree_peers.heading("hw", text="HW")
        self.tree_peers.column("node", width=190, anchor="w")
        self.tree_peers.column("hw", width=70, anchor="center")
        self.tree_peers.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.tree_peers.bind("<<TreeviewSelect>>", self._seleccionar_peer)

        self.lbl_device = tk.Label(
            panel_nodos,
            text="Sin dispositivo activo.",
            font=("Arial", 10, "bold"),
            bg=self.ui["panel"],
            fg=self.ui["acento"],
            justify="left",
            wraplength=260,
        )
        self.lbl_device.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))

        panel_chat = tk.Frame(cont, bg=self.ui["panel"], highlightthickness=1, highlightbackground=self.ui["borde"])
        panel_chat.grid(row=1, column=1, sticky="nsew", padx=(0, 10))
        panel_chat.grid_rowconfigure(1, weight=1)
        panel_chat.grid_columnconfigure(0, weight=1)

        self.lbl_chat = tk.Label(panel_chat, text="Conversación", font=("Arial", 14, "bold"), bg=self.ui["panel"], fg=self.ui["texto"])
        self.lbl_chat.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.txt_chat = tk.Text(panel_chat, wrap="word", state="disabled", bg="#071321", fg="white", insertbackground="white", relief="flat", font=("Courier New", 10))
        self.txt_chat.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))

        compose = tk.Frame(panel_chat, bg=self.ui["panel"])
        compose.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        compose.grid_columnconfigure(0, weight=1)
        self.entry_message = tk.Text(compose, height=4, wrap="word", bg="#0f2239", fg="white", insertbackground="white", relief="flat", font=("Arial", 11))
        self.entry_message.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        tk.Button(compose, text="Enviar", font=("Arial", 11, "bold"), bg=self.ui["ok"], fg="white", relief="flat", command=self._enviar_mensaje).grid(row=0, column=1, sticky="ns")

        panel_schema = tk.Frame(cont, bg=self.ui["panel_2"], highlightthickness=1, highlightbackground=self.ui["borde"])
        panel_schema.grid(row=1, column=2, sticky="nsew")
        panel_schema.grid_rowconfigure(1, weight=1)
        panel_schema.grid_columnconfigure(0, weight=1)
        tk.Label(panel_schema, text="Paquete Mesh", font=("Arial", 14, "bold"), bg=self.ui["panel_2"], fg=self.ui["texto"]).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.txt_packet = tk.Text(panel_schema, wrap="word", state="disabled", bg="#08111f", fg="#bfeaff", insertbackground="white", relief="flat", font=("Courier New", 10))
        self.txt_packet.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.lbl_schema = tk.Label(
            panel_schema,
            text="Arquitectura preparada para monitorear una placa Meshtastic conectada y mantener conversación desde TLAMATINI.",
            bg=self.ui["panel_2"],
            fg=self.ui["texto_dim"],
            justify="left",
            wraplength=340,
            font=("Arial", 10),
        )
        self.lbl_schema.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

    def _refrescar_peers(self):
        self.peer_index = {}
        for item in self.tree_peers.get_children():
            self.tree_peers.delete(item)

        peers = listar_peers()
        conversations = {conv.get("peer_id"): conv for conv in listar_conversations()}
        for peer in peers:
            node_id = peer.get("node_id", "")
            nombre = peer.get("display_name", "") or node_id
            hw = peer.get("hardware", "").upper()
            ultimo = conversations.get(node_id, {}).get("updated_at", "")
            etiqueta = f"{nombre} ({node_id})" if nombre != node_id else node_id
            iid = node_id or etiqueta
            self.peer_index[iid] = {"peer": peer, "conversation": conversations.get(node_id)}
            self.tree_peers.insert("", "end", iid=iid, values=(etiqueta, hw), tags=(ultimo,))

        if self.current_peer_id and self.current_peer_id in self.peer_index:
            self.tree_peers.selection_set(self.current_peer_id)
            self._seleccionar_peer()
        elif peers:
            primer = peers[0].get("node_id", "")
            if primer:
                self.tree_peers.selection_set(primer)
                self._seleccionar_peer()
        else:
            self.current_peer_id = ""
            self._render_conversation(None)

    def _refrescar_estado(self):
        snapshot = self.mesh_service.refresh_devices(auto_connect=True)
        self._render_runtime(snapshot.get("status", {}))
        self._refrescar_peers()

    def _render_runtime(self, status):
        text = status.get("status_text", "Sin estado.")
        adapter = status.get("adapter_id", "monitor-only")
        device = status.get("detected_device") or {}
        state = status.get("connection_state", "idle").upper()
        self.lbl_status.config(text=f"{state} · {text}\nAdaptador: {adapter}")
        if device:
            self.lbl_device.config(
                text=f"Dispositivo: {device.get('label', '')}\nRuta: {device.get('path', '')}"
            )
        else:
            self.lbl_device.config(text="Sin dispositivo activo.")

    def _conectar_dispositivo(self):
        snapshot = self.mesh_service.connect_preferred_device()
        self._render_runtime(snapshot.get("status", {}))
        self._refrescar_peers()

    def _programar_refresco(self):
        if not self.root.winfo_exists():
            return
        self.root.after(5000, self._tick_refresco)

    def _tick_refresco(self):
        if not self.root.winfo_exists():
            return
        self._refrescar_estado()
        self._programar_refresco()

    def _manejar_evento_mesh(self, event):
        try:
            if not self.root.winfo_exists():
                return
            if event.get("type") not in {"message_received", "message_sent", "session_changed"}:
                return
            self.root.after(0, self._refrescar_estado)
        except Exception:
            return

    def _cerrar(self):
        try:
            if callable(self._unsubscribe):
                self._unsubscribe()
        except Exception:
            pass
        self.root.destroy()

    def _seleccionar_peer(self, event=None):
        seleccion = self.tree_peers.selection()
        if not seleccion:
            self.current_peer_id = ""
            self._render_conversation(None)
            return
        self.current_peer_id = seleccion[0]
        self._render_conversation(self.peer_index.get(self.current_peer_id))

    def _render_conversation(self, data):
        self.txt_chat.configure(state="normal")
        self.txt_chat.delete("1.0", "end")
        self.txt_packet.configure(state="normal")
        self.txt_packet.delete("1.0", "end")

        if not data:
            self.lbl_chat.config(text="Conversación")
            self.txt_chat.insert("1.0", "Sin nodo seleccionado.")
            self.txt_packet.insert("1.0", "Selecciona un nodo para ver el sobre de interoperabilidad.")
            self.txt_chat.configure(state="disabled")
            self.txt_packet.configure(state="disabled")
            return

        peer = data["peer"]
        conversation = data.get("conversation") or {}
        self.lbl_chat.config(text=f'Conversación · {peer.get("display_name", peer.get("node_id", ""))}')
        mensajes = list(conversation.get("messages", []) or [])
        if not mensajes:
            self.txt_chat.insert("1.0", "Sin mensajes todavía.\n")
        else:
            lineas = []
            for item in mensajes:
                direccion = "TX" if item.get("direction") == "outbound" else "RX"
                hora = item.get("timestamp", "").replace("T", " ")
                estado = item.get("status", "")
                cuerpo = item.get("body", "")
                lineas.append(f"[{direccion}] {hora} [{estado}]")
                lineas.append(cuerpo)
                lineas.append("")
            self.txt_chat.insert("1.0", "\n".join(lineas).strip())

        preview = construir_paquete_mesh(peer.get("node_id", ""), self.entry_message.get("1.0", "end").strip() or "Mensaje de prueba")
        self.txt_packet.insert("1.0", json.dumps(preview, indent=2, ensure_ascii=False))
        self.txt_chat.configure(state="disabled")
        self.txt_packet.configure(state="disabled")

    def _agregar_peer_manual(self):
        node_id = simpledialog.askstring("Nuevo nodo", "Node ID del nodo mesh:", parent=self.root)
        if node_id is None:
            return
        node_id = node_id.strip()
        if not node_id:
            return
        display_name = simpledialog.askstring("Nombre", "Nombre visible del nodo:", parent=self.root, initialvalue=node_id) or node_id
        hardware = simpledialog.askstring("Hardware", "Hardware del nodo (esp32 / t114):", parent=self.root, initialvalue="esp32") or "esp32"
        try:
            registrar_peer(node_id=node_id, display_name=display_name.strip(), hardware=hardware.strip().lower(), origin="manual")
        except Exception as exc:
            messagebox.showwarning("Chat", str(exc), parent=self.root)
            return
        self._refrescar_peers()

    def _importar_desde_comunicacion(self):
        items = listar_items("Comunicacion")
        agregados = 0
        for item in items:
            modelo = str(item.get("nombre", "")).strip()
            if not modelo:
                continue
            node_id = modelo.lower().replace(" ", ".")
            hardware = "esp32"
            tipo = str(item.get("tipo", "")).lower()
            observaciones = str(item.get("observaciones", "")).lower()
            if "t114" in tipo or "t114" in observaciones or "t114" in modelo.lower():
                hardware = "t114"
            elif "esp32" in tipo or "esp32" in observaciones or "esp32" in modelo.lower():
                hardware = "esp32"
            registrar_peer(
                node_id=node_id,
                display_name=modelo,
                hardware=hardware,
                origin="inventario_comunicacion",
                notes=f"Tipo: {item.get('tipo', '')} | Banda: {item.get('peso_contenido', '')}",
            )
            agregados += 1
        self._refrescar_peers()
        messagebox.showinfo("Chat", f"Se importaron {agregados} nodo(s) desde Comunicación.", parent=self.root)

    def _enviar_mensaje(self):
        if not self.current_peer_id:
            messagebox.showwarning("Chat", "Selecciona un nodo destino.", parent=self.root)
            return
        body = self.entry_message.get("1.0", "end").strip()
        if not body:
            messagebox.showwarning("Chat", "Escribe un mensaje.", parent=self.root)
            return
        try:
            result = self.mesh_service.send_message(self.current_peer_id, body, requires_ack=True)
        except Exception as exc:
            messagebox.showwarning("Chat", str(exc), parent=self.root)
            return
        self.entry_message.delete("1.0", "end")
        self._refrescar_estado()
        transport = result.get("transport", {})
        if not transport.get("sent"):
            messagebox.showinfo(
                "Chat Mesh",
                (
                    "El mensaje quedó registrado en TLAMATINI y el monitor detectó el dispositivo, "
                    "pero el backend real de Meshtastic todavía no está integrado.\n\n"
                    f"Estado: {transport.get('reason', 'Sin detalle.')}"
                ),
                parent=self.root,
            )
