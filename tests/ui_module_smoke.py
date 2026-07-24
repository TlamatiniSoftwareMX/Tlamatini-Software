"""Prueba gráfica manual: construye y cierra cada módulo sin tocar datos reales."""

from __future__ import annotations

import os
import sys
import tempfile
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_HOME = Path(tempfile.mkdtemp(prefix="tlamatini-ui-smoke-"))
os.environ["TLAMATINI_HOME"] = str(TEST_HOME)
os.environ["TLAMATINI_AI_AUTO_PULL"] = "0"
os.environ["TLAMATINI_AI_WARMUP_ON_START"] = "0"


def _quiet_dialog(*_args, **_kwargs):
    return None


def _reject_dialog(*_args, **_kwargs):
    return False


for name in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, name, _quiet_dialog)
for name in ("askyesno", "askokcancel", "askretrycancel"):
    setattr(messagebox, name, _reject_dialog)
filedialog.askopenfilename = lambda *_args, **_kwargs: ""
filedialog.askopenfilenames = lambda *_args, **_kwargs: ()
filedialog.askdirectory = lambda *_args, **_kwargs: ""
filedialog.asksaveasfilename = lambda *_args, **_kwargs: ""


def main() -> int:
    from interfaz import dashboard

    root = tk.Tk()
    root.withdraw()
    callback_errors: list[str] = []
    root.report_callback_exception = lambda *_exc: callback_errors.append(traceback.format_exc())

    openers = [
        ("Consulta", dashboard.abrir_consulta),
        ("Mapa", dashboard.abrir_mapa),
        ("Inventario", dashboard.abrir_inventario),
        ("Planes", dashboard.abrir_planes),
        ("Biblioteca", dashboard.abrir_biblioteca),
        ("Aprendizaje", dashboard.abrir_aprendizaje),
        ("Códigos", dashboard.abrir_codigos),
        ("Perfiles", dashboard.abrir_perfiles),
        ("Herramientas", dashboard.abrir_herramientas),
        ("Juegos", dashboard.abrir_juegos),
        ("Actualizaciones", dashboard.abrir_actualizaciones),
    ]
    failures: list[tuple[str, str]] = []

    def _walk(widget):
        yield widget
        for child in widget.winfo_children():
            yield from _walk(child)

    for name, opener in openers:
        before = set(root.winfo_children())
        before_widgets = set(_walk(root))
        try:
            opener(root, root)
            root.update_idletasks()
            root.update()
            created = [child for child in root.winfo_children() if child not in before]
            if not created:
                raise AssertionError("el módulo no creó una ventana")
            buttons = [
                widget
                for widget in _walk(root)
                if widget not in before_widgets
                if widget.winfo_class() in {"Button", "TButton"}
            ]
            unbound = [str(button.cget("text")) for button in buttons if not str(button.cget("command")).strip()]
            if unbound:
                raise AssertionError(f"botones sin acción: {', '.join(unbound)}")
            for child in created:
                if child.winfo_exists():
                    child.destroy()
            root.update_idletasks()
            print(f"OK  {name} ({len(buttons)} botones enlazados)")
        except Exception:
            failures.append((name, traceback.format_exc()))
            print(f"ERROR  {name}")
            for child in list(root.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass

    try:
        from interfaz.ventana_juegos import VentanaJuegos

        menu = VentanaJuegos(root, root)
        for method_name in (
            "_abrir_ajedrez",
            "_abrir_damas",
            "_abrir_serpientes",
            "_abrir_sudoku",
            "_abrir_memoria",
            "_abrir_snake",
            "_abrir_tetris",
        ):
            before = set(root.winfo_children())
            getattr(menu, method_name)()
            root.update_idletasks()
            root.update()
            for child in [item for item in root.winfo_children() if item not in before]:
                child.destroy()
            print(f"OK  Juegos.{method_name.removeprefix('_abrir_')}")
        menu.destroy()
    except Exception:
        failures.append(("Opciones de Juegos", traceback.format_exc()))

    try:
        from interfaz.ventana_herramientas import VentanaHerramientas

        menu = VentanaHerramientas(root, root)
        for item in menu.catalogo_herramientas:
            before = set(_walk(root))
            item["accion"]()
            root.update_idletasks()
            root.update()
            created = [widget for widget in _walk(root) if widget not in before and isinstance(widget, tk.Toplevel)]
            if not created:
                raise AssertionError(f"{item['titulo']} no creó una ventana")
            for child in created:
                child.destroy()
            print(f"OK  Herramientas.{item['id']}")
        menu.destroy()
    except Exception:
        failures.append(("Opciones de Herramientas", traceback.format_exc()))

    root.destroy()
    if callback_errors:
        failures.extend(("callback Tk", detail) for detail in callback_errors)
    for name, detail in failures:
        print(f"\n[{name}]\n{detail}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
