def aplicar_geometria_relativa(ventana, parent=None, rel_w=0.92, rel_h=0.9, min_w=980, min_h=640, pad=10):
    try:
        ventana.update_idletasks()
    except Exception:
        pass

    if parent is not None:
        try:
            parent.update_idletasks()
        except Exception:
            pass

    if parent is not None and parent.winfo_ismapped():
        base_w = max(parent.winfo_width(), 320)
        base_h = max(parent.winfo_height(), 240)
        base_x = parent.winfo_rootx()
        base_y = parent.winfo_rooty()
    else:
        base_w = max(ventana.winfo_screenwidth(), 320)
        base_h = max(ventana.winfo_screenheight(), 240)
        base_x = 0
        base_y = 0

    screen_w = max(ventana.winfo_screenwidth(), 320)
    screen_h = max(ventana.winfo_screenheight(), 240)

    if parent is not None and parent.winfo_ismapped():
        max_w = max(320, min(base_w - (pad * 2), screen_w - (pad * 2)))
        max_h = max(240, min(base_h - (pad * 2), screen_h - (pad * 2)))
    else:
        max_w = max(320, screen_w - (pad * 2))
        max_h = max(240, screen_h - (pad * 2))

    min_w_efectivo = min(min_w, max_w)
    min_h_efectivo = min(min_h, max_h)

    ancho = max(min_w_efectivo, int(base_w * rel_w))
    alto = max(min_h_efectivo, int(base_h * rel_h))

    ancho = min(ancho, max_w)
    alto = min(alto, max_h)

    if parent is not None and parent.winfo_ismapped():
        pos_x = base_x + max(pad, (base_w - ancho) // 2)
        pos_y = base_y + max(pad, (base_h - alto) // 2)
    else:
        pos_x = max(pad, (screen_w - ancho) // 2)
        pos_y = max(pad, (screen_h - alto) // 2)

    pos_x = max(0, min(pos_x, screen_w - ancho))
    pos_y = max(0, min(pos_y, screen_h - alto))

    try:
        ventana.maxsize(max_w, max_h)
    except Exception:
        pass
    ventana.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")


def habilitar_scroll_mouse(area_widget, scroll_target, on_scroll=None):
    def _inside_area(widget, area):
        current = widget
        while current is not None:
            if current == area:
                return True
            try:
                current = current.master
            except Exception:
                current = None
        return False

    def _depth(widget):
        depth = 0
        current = widget
        while current is not None:
            depth += 1
            try:
                current = current.master
            except Exception:
                current = None
        return depth

    root = area_widget.winfo_toplevel()
    registry = getattr(root, "_tlamatini_scroll_registry", [])
    registry.append({"area": area_widget, "target": scroll_target, "on_scroll": on_scroll})
    root._tlamatini_scroll_registry = registry

    if getattr(root, "_tlamatini_scroll_bound", False):
        return

    def _dispatch_mousewheel(event):
        registry_local = []
        for item in getattr(root, "_tlamatini_scroll_registry", []):
            area = item.get("area")
            target = item.get("target")
            try:
                if area is not None and target is not None and area.winfo_exists() and target.winfo_exists():
                    registry_local.append(item)
            except Exception:
                continue
        root._tlamatini_scroll_registry = registry_local

        try:
            widget = root.winfo_containing(*root.winfo_pointerxy())
        except Exception:
            widget = None
        if widget is None:
            return

        matches = []
        for item in registry_local:
            area = item["area"]
            if _inside_area(widget, area):
                matches.append((_depth(area), item))
        if not matches:
            return

        _depth_value, selected = max(matches, key=lambda entry: entry[0])
        handler = selected.get("on_scroll")
        if handler is not None:
            return handler(event)

        target = selected["target"]
        delta = getattr(event, "delta", 0)
        if delta:
            target.yview_scroll(int(-1 * (delta / 120)), "units")
        else:
            num = getattr(event, "num", None)
            if num == 4:
                target.yview_scroll(-1, "units")
            elif num == 5:
                target.yview_scroll(1, "units")
        return "break"

    root.bind_all("<MouseWheel>", _dispatch_mousewheel, add="+")
    root.bind_all("<Button-4>", _dispatch_mousewheel, add="+")
    root.bind_all("<Button-5>", _dispatch_mousewheel, add="+")
    root._tlamatini_scroll_bound = True


def crear_contenedor_scrollable(parent, bg="#111827", canvas_bg=None):
    import tkinter as tk
    from tkinter import ttk

    canvas_bg = canvas_bg or bg

    exterior = tk.Frame(parent, bg=bg)
    exterior.pack(fill="both", expand=True)

    canvas = tk.Canvas(exterior, bg=canvas_bg, highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(exterior, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    interior = tk.Frame(canvas, bg=bg)
    window_id = canvas.create_window((0, 0), window=interior, anchor="nw")

    def _actualizar_scroll(event=None):
        try:
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass

    def _ajustar_ancho(event):
        try:
            canvas.itemconfigure(window_id, width=event.width)
        except Exception:
            pass

    interior.bind("<Configure>", _actualizar_scroll)
    canvas.bind("<Configure>", _ajustar_ancho)
    habilitar_scroll_mouse(exterior, canvas)

    return exterior, canvas, interior
