import tkinter as tk
from tkinter import ttk


class ModuloVista(ttk.Frame):
    def __init__(self, master, titulo, icono_texto, comando=None):
        super().__init__(master, padding=8, style="Modulo.TFrame")
        self.comando = comando

        self.boton = tk.Button(
            self,
            text=f"{icono_texto}\n\n{titulo}",
            font=("Arial", 12, "bold"),
            bg="#1F7A1F",
            fg="white",
            activebackground="#145214",
            activeforeground="white",
            relief="raised",
            bd=2,
            command=self.ejecutar,
            wraplength=140,
            justify="center"
        )
        self.boton.pack(fill="both", expand=True)

    def ejecutar(self):
        if callable(self.comando):
            self.comando()