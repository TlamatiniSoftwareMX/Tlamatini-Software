import random
import tkinter as tk
import unicodedata
from copy import deepcopy
from tkinter import messagebox, ttk

from core.logs import registrar_log
from core.window_geometry import aplicar_geometria_relativa


UI_JUEGOS = {
    "bg": "#0a1322",
    "panel": "#12243a",
    "panel_alt": "#18314f",
    "border": "#2a4f73",
    "text": "#eff6ff",
    "text_dim": "#adc4da",
    "accent": "#38bdf8",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
}

SNAKES_AND_LADDERS = {
    3: 16,
    15: 37,
    22: 42,
    41: 63,
    49: 70,
    64: 85,
    91: 98,
    12: 2,
    25: 7,
    34: 19,
    47: 30,
    66: 52,
    88: 72,
    95: 76,
    99: 80,
}

SUDOKU_PUZZLES = [
    (
        [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ],
        [
            [5, 3, 4, 6, 7, 8, 9, 1, 2],
            [6, 7, 2, 1, 9, 5, 3, 4, 8],
            [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3],
            [4, 2, 6, 8, 5, 3, 7, 9, 1],
            [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4],
            [2, 8, 7, 4, 1, 9, 6, 3, 5],
            [3, 4, 5, 2, 8, 6, 1, 7, 9],
        ],
    ),
    (
        [
            [0, 2, 0, 6, 0, 8, 0, 0, 0],
            [5, 8, 0, 0, 0, 9, 7, 0, 0],
            [0, 0, 0, 0, 4, 0, 0, 0, 0],
            [3, 7, 0, 0, 0, 0, 5, 0, 0],
            [6, 0, 0, 0, 0, 0, 0, 0, 4],
            [0, 0, 8, 0, 0, 0, 0, 1, 3],
            [0, 0, 0, 0, 2, 0, 0, 0, 0],
            [0, 0, 9, 8, 0, 0, 0, 3, 6],
            [0, 0, 0, 3, 0, 6, 0, 9, 0],
        ],
        [
            [1, 2, 3, 6, 7, 8, 9, 4, 5],
            [5, 8, 4, 2, 3, 9, 7, 6, 1],
            [9, 6, 7, 1, 4, 5, 3, 2, 8],
            [3, 7, 2, 4, 6, 1, 5, 8, 9],
            [6, 9, 1, 5, 8, 3, 2, 7, 4],
            [4, 5, 8, 7, 9, 2, 6, 1, 3],
            [8, 3, 6, 9, 2, 4, 1, 5, 7],
            [2, 1, 9, 8, 5, 7, 4, 3, 6],
            [7, 4, 5, 3, 1, 6, 8, 9, 2],
        ],
    ),
]

MORSE_CODE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
    "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
}
MORSE_WORDS = [
    "AGUA", "AYUDA", "CASA", "CLAVE", "EQUIPO", "FARO", "LUZ", "MAPA", "NORTE",
    "RADIO", "RED", "RUTA", "SALUD", "SEÑAL", "SOL", "TIERRA", "TREN", "VIDA",
]


def _normalize_morse_text(text):
    decomposed = unicodedata.normalize("NFD", str(text or "").upper())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def encode_morse(text):
    words = []
    for word in _normalize_morse_text(text).split():
        encoded = [MORSE_CODE[char] for char in word if char in MORSE_CODE]
        if encoded:
            words.append(" ".join(encoded))
    return " / ".join(words)


def decode_morse(code):
    reverse = {value: key for key, value in MORSE_CODE.items()}
    normalized = " ".join(str(code or "").replace("/", " / ").split())
    words = []
    for group in normalized.split(" / "):
        letters = [reverse.get(symbol, "?") for symbol in group.split()]
        if letters:
            words.append("".join(letters))
    return " ".join(words)


def _log_juegos_warning(message: str):
    registrar_log("warning", message, "juegos")


def _show_window(win):
    try:
        win.lift()
        win.focus_force()
    except Exception as exc:
        _log_juegos_warning(f"No se pudo enfocar una ventana de juego: {exc}")


def _open_game_window(master, focus_parent, title, rel_w=0.7, rel_h=0.8, min_w=900, min_h=700):
    top = tk.Toplevel(master)
    top.title(title)
    top.configure(bg=UI_JUEGOS["bg"])
    aplicar_geometria_relativa(top, focus_parent or master, rel_w=rel_w, rel_h=rel_h, min_w=min_w, min_h=min_h)
    _show_window(top)
    return top


def _panel(parent, title, subtitle=""):
    box = tk.Frame(parent, bg=UI_JUEGOS["panel"], highlightthickness=1, highlightbackground=UI_JUEGOS["border"])
    tk.Label(box, text=title, font=("Arial", 15, "bold"), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["text"]).pack(anchor="w", padx=14, pady=(14, 4))
    if subtitle:
        tk.Label(box, text=subtitle, font=("Arial", 10), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["text_dim"], justify="left", wraplength=520).pack(anchor="w", padx=14, pady=(0, 10))
    return box


class VentanaJuegos(tk.Toplevel):
    def __init__(self, master, focus_parent=None):
        super().__init__(master)
        self.master_root = master
        self.focus_parent = focus_parent or master
        self.title("Juegos")
        self.configure(bg=UI_JUEGOS["bg"])
        aplicar_geometria_relativa(self, self.focus_parent, rel_w=0.72, rel_h=0.78, min_w=1050, min_h=760)
        self._crear_ui()
        _show_window(self)

    def _crear_ui(self):
        header = tk.Frame(self, bg=UI_JUEGOS["bg"])
        header.pack(fill="x", padx=20, pady=(18, 12))
        tk.Label(header, text="Juegos", font=("Arial", 24, "bold"), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text"]).pack(anchor="w")
        tk.Label(header, text="entretenimiento offline", font=("Arial", 11), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self, bg=UI_JUEGOS["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        for col in range(2):
            body.grid_columnconfigure(col, weight=1, uniform="games")
        for row in range(2):
            body.grid_rowconfigure(row, weight=1, uniform="games_rows")

        categorias = [
            (
                "Clásicos",
                "Juegos de tablero básicos para partidas locales.",
                [
                    ("♟", "Ajedrez", "Tablero funcional con movimiento básico de piezas.", self._abrir_ajedrez),
                    ("⛀", "Damas", "Turnos y capturas básicas en tablero de 8x8.", self._abrir_damas),
                    ("🎲", "Serpientes y escaleras", "Avance con dados y lógica de casillas especiales.", self._abrir_serpientes),
                ],
            ),
            (
                "Cartas y lógica",
                "Retos contra la computadora y juegos mentales.",
                [
                    ("★", "Última Carta", "Descarta por color o símbolo contra la computadora.", self._abrir_ultima_carta),
                    ("▦", "Sudoku", "Sudoku simple con validación local.", self._abrir_sudoku),
                    ("🂠", "Memoria", "Voltea cartas y encuentra parejas.", self._abrir_memoria),
                    ("·—", "Misión Morse", "Descifra señales y forma palabras con puntos y rayas.", self._abrir_morse),
                ],
            ),
            (
                "Arcade simple",
                "Arcade offline con teclado.",
                [
                    ("S", "Snake", "Control con flechas y colisiones.", self._abrir_snake),
                    ("T", "Tetris", "Piezas, líneas y caída automática.", self._abrir_tetris),
                    ("🏎", "Carrera Neón", "Esquiva tráfico y aumenta tu velocidad.", self._abrir_carrera),
                ],
            ),
            (
                "Acción",
                "Partidas rápidas con controles de teclado.",
                [
                    ("⚔", "Duelo Arena", "Pelea contra un rival controlado por la computadora.", self._abrir_duelo),
                ],
            ),
        ]

        for index, (title, subtitle, juegos) in enumerate(categorias):
            row, col = divmod(index, 2)
            panel = _panel(body, title, subtitle)
            panel.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            for icon, name, desc, callback in juegos:
                card = tk.Frame(panel, bg=UI_JUEGOS["panel_alt"], highlightthickness=1, highlightbackground=UI_JUEGOS["border"], cursor="hand2")
                card.pack(fill="x", padx=14, pady=(0, 10))
                wrap = tk.Frame(card, bg=UI_JUEGOS["panel_alt"])
                wrap.pack(fill="x", padx=12, pady=12)
                badge = tk.Frame(wrap, bg=UI_JUEGOS["accent"], width=42, height=42)
                badge.pack(side="left")
                badge.pack_propagate(False)
                icon_label = tk.Label(badge, text=icon, font=("Arial", 18, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a")
                icon_label.pack(expand=True)
                text_box = tk.Frame(wrap, bg=UI_JUEGOS["panel_alt"])
                text_box.pack(side="left", fill="both", expand=True, padx=(12, 0))
                name_label = tk.Label(text_box, text=name, font=("Arial", 11, "bold"), bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"])
                name_label.pack(anchor="w")
                desc_label = tk.Label(text_box, text=desc, font=("Arial", 9), bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text_dim"], justify="left", wraplength=240)
                desc_label.pack(anchor="w", pady=(4, 0))
                for widget in (card, wrap, badge, icon_label, text_box, name_label, desc_label):
                    widget.bind("<Double-Button-1>", lambda _event, fn=callback: fn())

        footer = tk.Frame(self, bg=UI_JUEGOS["bg"])
        footer.pack(fill="x", padx=20, pady=(0, 18))
        tk.Button(footer, text="Cerrar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["muted"] if "muted" in UI_JUEGOS else UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"], relief="flat", padx=16, pady=8, command=self.destroy).pack(anchor="e")

    def _abrir_ajedrez(self):
        ChessWindow(self.master_root, self)

    def _abrir_damas(self):
        CheckersWindow(self.master_root, self)

    def _abrir_serpientes(self):
        SnakesAndLaddersWindow(self.master_root, self)

    def _abrir_sudoku(self):
        SudokuWindow(self.master_root, self)

    def _abrir_memoria(self):
        MemoryWindow(self.master_root, self)

    def _abrir_snake(self):
        SnakeWindow(self.master_root, self)

    def _abrir_tetris(self):
        TetrisWindow(self.master_root, self)

    def _abrir_ultima_carta(self):
        LastCardWindow(self.master_root, self)

    def _abrir_carrera(self):
        NeonRaceWindow(self.master_root, self)

    def _abrir_duelo(self):
        ArenaDuelWindow(self.master_root, self)

    def _abrir_morse(self):
        MorseMissionWindow(self.master_root, self)


class BoardGameWindow:
    def __init__(self, master, focus_parent, title, subtitle, size=720):
        self.top = _open_game_window(master, focus_parent, title, rel_w=0.68, rel_h=0.8, min_w=920, min_h=760)
        self.title = title
        header = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        header.pack(fill="x", padx=16, pady=(16, 10))
        tk.Label(header, text=title, font=("Arial", 20, "bold"), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text"]).pack(anchor="w")
        tk.Label(header, text=subtitle, font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(anchor="w", pady=(4, 0))
        body = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        left = tk.Frame(body, bg=UI_JUEGOS["bg"])
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(body, bg=UI_JUEGOS["bg"], width=240)
        right.pack(side="right", fill="y", padx=(16, 0))
        right.pack_propagate(False)
        self.canvas = tk.Canvas(left, width=size, height=size, bg="#f8fafc", highlightthickness=1, highlightbackground=UI_JUEGOS["border"])
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.draw())
        self.side = _panel(right, "Estado")
        self.side.pack(fill="x")
        self.status_var = tk.StringVar(value="")
        tk.Label(self.side, textvariable=self.status_var, font=("Arial", 10), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["text_dim"], justify="left", wraplength=200).pack(anchor="w", padx=14, pady=(0, 12))
        self.action_box = tk.Frame(self.side, bg=UI_JUEGOS["panel"])
        self.action_box.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(right, text="Reiniciar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.reset).pack(fill="x", pady=(12, 8))
        tk.Button(right, text="Cerrar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"], relief="flat", command=self.top.destroy).pack(fill="x")

    def set_status(self, text):
        self.status_var.set(text)

    def reset(self):
        pass


class ChessWindow(BoardGameWindow):
    PIECES = {
        "wp": "♙", "wr": "♖", "wn": "♘", "wb": "♗", "wq": "♕", "wk": "♔",
        "bp": "♟", "br": "♜", "bn": "♞", "bb": "♝", "bq": "♛", "bk": "♚",
    }

    def __init__(self, master, focus_parent):
        self.board = []
        self.turn = "w"
        self.selected = None
        super().__init__(master, focus_parent, "Ajedrez", "Movimiento básico de piezas. Sin enroque, jaque ni IA.")
        self.canvas.bind("<Button-1>", self.on_click)
        self.reset()

    def reset(self):
        self.board = [
            ["br", "bn", "bb", "bq", "bk", "bb", "bn", "br"],
            ["bp"] * 8,
            [""] * 8,
            [""] * 8,
            [""] * 8,
            [""] * 8,
            ["wp"] * 8,
            ["wr", "wn", "wb", "wq", "wk", "wb", "wn", "wr"],
        ]
        self.turn = "w"
        self.selected = None
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        size = min(max(self.canvas.winfo_width(), 640), max(self.canvas.winfo_height(), 640)) / 8
        self.cell = size
        for r in range(8):
            for c in range(8):
                x1, y1 = c * size, r * size
                x2, y2 = x1 + size, y1 + size
                color = "#f0d9b5" if (r + c) % 2 == 0 else "#b58863"
                if self.selected == (r, c):
                    color = "#86efac"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#334155")
                piece = self.board[r][c]
                if piece:
                    self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=self.PIECES[piece], font=("Arial", int(size * 0.46)))
        self.set_status(f"Turno: {'Blancas' if self.turn == 'w' else 'Negras'}")

    def on_click(self, event):
        c = int(event.x // self.cell)
        r = int(event.y // self.cell)
        if not (0 <= r < 8 and 0 <= c < 8):
            return
        piece = self.board[r][c]
        if self.selected is None:
            if piece and piece[0] == self.turn:
                self.selected = (r, c)
                self.draw()
            return
        sr, sc = self.selected
        if (sr, sc) == (r, c):
            self.selected = None
            self.draw()
            return
        if self._valid_move(sr, sc, r, c):
            self.board[r][c] = self.board[sr][sc]
            self.board[sr][sc] = ""
            self.turn = "b" if self.turn == "w" else "w"
        self.selected = None
        self.draw()

    def _clear_path(self, sr, sc, tr, tc):
        dr = 0 if tr == sr else (1 if tr > sr else -1)
        dc = 0 if tc == sc else (1 if tc > sc else -1)
        r, c = sr + dr, sc + dc
        while (r, c) != (tr, tc):
            if self.board[r][c]:
                return False
            r += dr
            c += dc
        return True

    def _valid_move(self, sr, sc, tr, tc):
        piece = self.board[sr][sc]
        target = self.board[tr][tc]
        if not piece or piece[0] != self.turn:
            return False
        if target and target[0] == self.turn:
            return False
        kind = piece[1]
        dr = tr - sr
        dc = tc - sc
        adr, adc = abs(dr), abs(dc)
        if kind == "p":
            direction = -1 if piece[0] == "w" else 1
            start_row = 6 if piece[0] == "w" else 1
            if dc == 0 and not target:
                if dr == direction:
                    return True
                if sr == start_row and dr == 2 * direction and not self.board[sr + direction][sc]:
                    return True
            if adr == 1 and dr == direction and target:
                return True
            return False
        if kind == "r":
            return (dr == 0 or dc == 0) and self._clear_path(sr, sc, tr, tc)
        if kind == "b":
            return adr == adc and self._clear_path(sr, sc, tr, tc)
        if kind == "q":
            return ((dr == 0 or dc == 0) or adr == adc) and self._clear_path(sr, sc, tr, tc)
        if kind == "n":
            return (adr, adc) in {(1, 2), (2, 1)}
        if kind == "k":
            return max(adr, adc) == 1
        return False


class CheckersWindow(BoardGameWindow):
    def __init__(self, master, focus_parent):
        self.board = []
        self.turn = "r"
        self.selected = None
        super().__init__(master, focus_parent, "Damas", "Reglas básicas con movimiento diagonal, coronación y capturas simples.")
        self.canvas.bind("<Button-1>", self.on_click)
        self.reset()

    def reset(self):
        self.board = [[""] * 8 for _ in range(8)]
        for r in range(3):
            for c in range(8):
                if (r + c) % 2 == 1:
                    self.board[r][c] = "b"
        for r in range(5, 8):
            for c in range(8):
                if (r + c) % 2 == 1:
                    self.board[r][c] = "r"
        self.turn = "r"
        self.selected = None
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        size = min(max(self.canvas.winfo_width(), 640), max(self.canvas.winfo_height(), 640)) / 8
        self.cell = size
        for r in range(8):
            for c in range(8):
                x1, y1 = c * size, r * size
                x2, y2 = x1 + size, y1 + size
                color = "#f8fafc" if (r + c) % 2 == 0 else "#78350f"
                if self.selected == (r, c):
                    color = "#86efac"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#334155")
                piece = self.board[r][c]
                if piece:
                    fill = "#ef4444" if piece.lower() == "r" else "#0f172a"
                    self.canvas.create_oval(x1 + 8, y1 + 8, x2 - 8, y2 - 8, fill=fill, outline="#e2e8f0", width=2)
                    if piece.isupper():
                        self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text="K", fill="#f8fafc", font=("Arial", int(size * 0.22), "bold"))
        self.set_status(f"Turno: {'Rojas' if self.turn == 'r' else 'Negras'}")

    def on_click(self, event):
        c = int(event.x // self.cell)
        r = int(event.y // self.cell)
        if not (0 <= r < 8 and 0 <= c < 8):
            return
        piece = self.board[r][c]
        if self.selected is None:
            if piece and piece.lower() == self.turn:
                self.selected = (r, c)
                self.draw()
            return
        sr, sc = self.selected
        if (sr, sc) == (r, c):
            self.selected = None
            self.draw()
            return
        if self._move(sr, sc, r, c):
            self.turn = "b" if self.turn == "r" else "r"
        self.selected = None
        self.draw()

    def _move(self, sr, sc, tr, tc):
        piece = self.board[sr][sc]
        if self.board[tr][tc]:
            return False
        dr, dc = tr - sr, tc - sc
        adr, adc = abs(dr), abs(dc)
        if adc != adr:
            return False
        allowed = []
        if piece == "r":
            allowed = [-1]
        elif piece == "b":
            allowed = [1]
        else:
            allowed = [-1, 1]
        if adr == 1 and (dr // adr) in allowed:
            self.board[tr][tc] = piece
            self.board[sr][sc] = ""
        elif adr == 2 and (dr // adr) in allowed:
            mr, mc = sr + dr // 2, sc + dc // 2
            middle = self.board[mr][mc]
            if not middle or middle.lower() == piece.lower():
                return False
            self.board[tr][tc] = piece
            self.board[sr][sc] = ""
            self.board[mr][mc] = ""
        else:
            return False
        if piece == "r" and tr == 0:
            self.board[tr][tc] = "R"
        if piece == "b" and tr == 7:
            self.board[tr][tc] = "B"
        return True


class SnakesAndLaddersWindow(BoardGameWindow):
    def __init__(self, master, focus_parent):
        self.positions = [1, 1]
        self.turn = 0
        self.last_roll = 0
        super().__init__(master, focus_parent, "Serpientes y escaleras", "Dos jugadores locales. Doble clic en Lanzar dado.")
        self._build_actions()
        self.reset()

    def _build_actions(self):
        self.roll_btn = tk.Button(self.action_box, text="Lanzar dado", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.roll)
        self.roll_btn.pack(fill="x")

    def reset(self):
        self.positions = [1, 1]
        self.turn = 0
        self.last_roll = 0
        self.draw()

    def roll(self):
        self.last_roll = random.randint(1, 6)
        pos = self.positions[self.turn]
        if pos + self.last_roll <= 100:
            pos += self.last_roll
            pos = SNAKES_AND_LADDERS.get(pos, pos)
            self.positions[self.turn] = pos
        if self.positions[self.turn] == 100:
            self.draw()
            messagebox.showinfo("Juego", f"Gana el jugador {self.turn + 1}.", parent=self.top)
            return
        self.turn = 1 - self.turn
        self.draw()

    def _coords(self, pos):
        idx = pos - 1
        row = 9 - (idx // 10)
        col = idx % 10
        if ((9 - row) % 2) == 1:
            col = 9 - col
        return row, col

    def draw(self):
        self.canvas.delete("all")
        size = 64
        colors = ["#fef3c7", "#dbeafe"]
        for pos in range(1, 101):
            row, col = self._coords(pos)
            x1, y1 = col * size, row * size
            x2, y2 = x1 + size, y1 + size
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=colors[(row + col) % 2], outline="#334155")
            self.canvas.create_text(x1 + 10, y1 + 10, text=str(pos), anchor="nw", font=("Arial", 8))
        for start, end in SNAKES_AND_LADDERS.items():
            sr, sc = self._coords(start)
            er, ec = self._coords(end)
            color = UI_JUEGOS["success"] if end > start else UI_JUEGOS["danger"]
            self.canvas.create_line(sc * size + 32, sr * size + 32, ec * size + 32, er * size + 32, fill=color, width=4)
        token_colors = ["#ef4444", "#2563eb"]
        for idx, pos in enumerate(self.positions):
            row, col = self._coords(pos)
            offset = -10 if idx == 0 else 10
            self.canvas.create_oval(col * size + 18 + offset, row * size + 18, col * size + 42 + offset, row * size + 42, fill=token_colors[idx], outline="#f8fafc", width=2)
        self.set_status(
            f"Turno: Jugador {self.turn + 1}\n"
            f"Dado anterior: {self.last_roll or '--'}\n"
            f"Jugador 1: {self.positions[0]}\n"
            f"Jugador 2: {self.positions[1]}"
        )


class SudokuWindow:
    def __init__(self, master, focus_parent):
        self.top = _open_game_window(master, focus_parent, "Sudoku", rel_w=0.56, rel_h=0.8, min_w=760, min_h=820)
        self.entries = []
        self.solution = []
        self.puzzle = []
        self._crear_ui()
        self.reset()

    def _crear_ui(self):
        header = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        header.pack(fill="x", padx=16, pady=(16, 10))
        tk.Label(header, text="Sudoku", font=("Arial", 20, "bold"), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text"]).pack(anchor="w")
        tk.Label(header, text="Rellena los espacios vacíos. Doble clic en Validar para comprobar.", font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(anchor="w", pady=(4, 0))
        panel = _panel(self.top, "Tablero")
        panel.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        grid = tk.Frame(panel, bg=UI_JUEGOS["panel"])
        grid.pack(padx=14, pady=(0, 14))
        self.entries = []
        for r in range(9):
            fila = []
            for c in range(9):
                e = tk.Entry(grid, width=2, justify="center", font=("Arial", 18, "bold"), bg="#f8fafc", fg="#0f172a", relief="solid", bd=1)
                e.grid(row=r, column=c, padx=(2 if c % 3 else 5, 2), pady=(2 if r % 3 else 5, 2), ipadx=4, ipady=6)
                fila.append(e)
            self.entries.append(fila)
        acciones = tk.Frame(panel, bg=UI_JUEGOS["panel"])
        acciones.pack(fill="x", padx=14, pady=(0, 14))
        self.status = tk.StringVar(value="")
        btn_new = tk.Button(acciones, text="Nuevo", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.reset)
        btn_new.pack(side="left")
        btn_check = tk.Button(acciones, text="Validar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["success"], fg="white", relief="flat", command=self.validate)
        btn_check.pack(side="left", padx=8)
        tk.Button(acciones, text="Cerrar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"], relief="flat", command=self.top.destroy).pack(side="right")
        tk.Label(panel, textvariable=self.status, font=("Arial", 10), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["text_dim"]).pack(anchor="w", padx=14, pady=(0, 14))

    def reset(self):
        self.puzzle, self.solution = deepcopy(random.choice(SUDOKU_PUZZLES))
        for r in range(9):
            for c in range(9):
                entry = self.entries[r][c]
                entry.configure(state="normal", disabledforeground="#0f172a")
                entry.delete(0, "end")
                if self.puzzle[r][c]:
                    entry.insert(0, str(self.puzzle[r][c]))
                    entry.configure(state="disabled")
        self.status.set("Juego listo.")

    def validate(self):
        errors = []
        for r in range(9):
            for c in range(9):
                if self.puzzle[r][c]:
                    continue
                value = self.entries[r][c].get().strip()
                if value != str(self.solution[r][c]):
                    errors.append((r, c))
        if errors:
            self.status.set(f"Hay {len(errors)} casilla(s) incorrectas o vacías.")
            return
        self.status.set("Sudoku completado correctamente.")


class MemoryWindow:
    def __init__(self, master, focus_parent):
        self.top = _open_game_window(master, focus_parent, "Juego de memoria", rel_w=0.48, rel_h=0.62, min_w=760, min_h=640)
        self.buttons = []
        self.cards = []
        self.revealed = []
        self.locked = set()
        self.moves = 0
        self._crear_ui()
        self.reset()

    def _crear_ui(self):
        header = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        header.pack(fill="x", padx=16, pady=(16, 10))
        tk.Label(header, text="Juego de memoria", font=("Arial", 20, "bold"), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text"]).pack(anchor="w")
        panel = _panel(self.top, "Parejas")
        panel.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.grid = tk.Frame(panel, bg=UI_JUEGOS["panel"])
        self.grid.pack(padx=14, pady=(0, 14))
        self.status = tk.StringVar(value="")
        footer = tk.Frame(panel, bg=UI_JUEGOS["panel"])
        footer.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(footer, text="Nuevo", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.reset).pack(side="left")
        tk.Label(footer, textvariable=self.status, font=("Arial", 10), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["text_dim"]).pack(side="left", padx=12)

    def reset(self):
        symbols = ["A", "B", "C", "D", "E", "F", "G", "H"]
        self.cards = symbols + symbols
        random.shuffle(self.cards)
        self.revealed = []
        self.locked = set()
        self.moves = 0
        for widget in self.grid.winfo_children():
            widget.destroy()
        self.buttons = []
        for idx, value in enumerate(self.cards):
            r, c = divmod(idx, 4)
            btn = tk.Button(self.grid, text="?", width=6, height=3, font=("Arial", 18, "bold"), bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"], relief="flat", command=lambda i=idx: self.flip(i))
            btn.grid(row=r, column=c, padx=6, pady=6)
            self.buttons.append(btn)
        self.status.set("Movimientos: 0")

    def flip(self, idx):
        if idx in self.locked or idx in self.revealed or len(self.revealed) == 2:
            return
        self.buttons[idx].configure(text=self.cards[idx], bg=UI_JUEGOS["accent"], fg="#05243a")
        self.revealed.append(idx)
        if len(self.revealed) == 2:
            self.moves += 1
            self.status.set(f"Movimientos: {self.moves}")
            self.top.after(450, self._check_pair)

    def _check_pair(self):
        a, b = self.revealed
        if self.cards[a] == self.cards[b]:
            self.locked.update({a, b})
            self.buttons[a].configure(bg=UI_JUEGOS["success"], fg="white")
            self.buttons[b].configure(bg=UI_JUEGOS["success"], fg="white")
            if len(self.locked) == len(self.cards):
                self.status.set(f"Completado en {self.moves} movimientos.")
        else:
            for idx in (a, b):
                self.buttons[idx].configure(text="?", bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"])
        self.revealed = []


class SnakeWindow:
    def __init__(self, master, focus_parent):
        self.top = _open_game_window(master, focus_parent, "Snake", rel_w=0.5, rel_h=0.64, min_w=760, min_h=720)
        self.canvas = tk.Canvas(self.top, width=480, height=480, bg="#020617", highlightthickness=1, highlightbackground=UI_JUEGOS["border"])
        self.canvas.pack(padx=16, pady=(16, 8))
        self.status = tk.StringVar(value="")
        footer = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        footer.pack(fill="x", padx=16, pady=(0, 16))
        tk.Label(footer, textvariable=self.status, font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(side="left")
        tk.Button(footer, text="Reiniciar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.reset).pack(side="right")
        self.top.bind("<Up>", lambda _e: self.change_dir((0, -1)))
        self.top.bind("<Down>", lambda _e: self.change_dir((0, 1)))
        self.top.bind("<Left>", lambda _e: self.change_dir((-1, 0)))
        self.top.bind("<Right>", lambda _e: self.change_dir((1, 0)))
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.running = False
        self.job = None
        self.reset()

    def reset(self):
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception as exc:
                _log_juegos_warning(f"No se pudo cancelar el temporizador de Snake al reiniciar: {exc}")
        self.snake = [(10, 10), (9, 10), (8, 10)]
        self.direction = (1, 0)
        self.food = self._new_food()
        self.score = 0
        self.running = True
        self.draw()
        self.tick()

    def _new_food(self):
        while True:
            pos = (random.randint(0, 19), random.randint(0, 19))
            if pos not in self.snake:
                return pos

    def change_dir(self, new_dir):
        if (new_dir[0] * -1, new_dir[1] * -1) == self.direction:
            return
        self.direction = new_dir

    def tick(self):
        if not self.running or not self.top.winfo_exists():
            return
        head = self.snake[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])
        if not (0 <= new_head[0] < 20 and 0 <= new_head[1] < 20) or new_head in self.snake:
            self.running = False
            self.status.set(f"Fin de partida. Puntaje: {self.score}")
            return
        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 1
            self.food = self._new_food()
        else:
            self.snake.pop()
        self.draw()
        self.job = self.top.after(140, self.tick)

    def draw(self):
        self.canvas.delete("all")
        for y in range(20):
            for x in range(20):
                self.canvas.create_rectangle(x * 24, y * 24, x * 24 + 24, y * 24 + 24, outline="#0f172a")
        for idx, (x, y) in enumerate(self.snake):
            color = UI_JUEGOS["accent"] if idx == 0 else UI_JUEGOS["success"]
            self.canvas.create_rectangle(x * 24 + 2, y * 24 + 2, x * 24 + 22, y * 24 + 22, fill=color, outline="")
        fx, fy = self.food
        self.canvas.create_oval(fx * 24 + 4, fy * 24 + 4, fx * 24 + 20, fy * 24 + 20, fill=UI_JUEGOS["danger"], outline="")
        if self.running:
            self.status.set(f"Puntaje: {self.score}")

    def close(self):
        self.running = False
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception as exc:
                _log_juegos_warning(f"No se pudo cancelar el temporizador de Snake al cerrar: {exc}")
            self.job = None
        self.top.destroy()


class TetrisWindow:
    SHAPES = {
        "I": [((0, 1), (1, 1), (2, 1), (3, 1)), ((2, 0), (2, 1), (2, 2), (2, 3))],
        "O": [((1, 0), (2, 0), (1, 1), (2, 1))],
        "T": [((1, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (1, 1), (2, 1), (1, 2)), ((0, 1), (1, 1), (2, 1), (1, 2)), ((1, 0), (0, 1), (1, 1), (1, 2))],
        "L": [((0, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (2, 0), (1, 1), (1, 2)), ((0, 1), (1, 1), (2, 1), (2, 2)), ((1, 0), (1, 1), (0, 2), (1, 2))],
        "J": [((2, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (1, 1), (1, 2), (2, 2)), ((0, 1), (1, 1), (2, 1), (0, 2)), ((0, 0), (1, 0), (1, 1), (1, 2))],
        "S": [((1, 0), (2, 0), (0, 1), (1, 1)), ((1, 0), (1, 1), (2, 1), (2, 2))],
        "Z": [((0, 0), (1, 0), (1, 1), (2, 1)), ((2, 0), (1, 1), (2, 1), (1, 2))],
    }
    COLORS = {"I": "#38bdf8", "O": "#facc15", "T": "#c084fc", "L": "#fb923c", "J": "#60a5fa", "S": "#4ade80", "Z": "#f87171"}

    def __init__(self, master, focus_parent):
        self.top = _open_game_window(master, focus_parent, "Tetris", rel_w=0.54, rel_h=0.76, min_w=820, min_h=760)
        wrap = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        wrap.pack(fill="both", expand=True, padx=16, pady=16)
        self.canvas = tk.Canvas(wrap, width=300, height=600, bg="#020617", highlightthickness=1, highlightbackground=UI_JUEGOS["border"])
        self.canvas.pack(side="left")
        side = _panel(wrap, "Estado", "Flechas: mover. Arriba: rotar. Abajo: acelerar.")
        side.pack(side="left", fill="y", padx=(16, 0))
        self.status = tk.StringVar(value="")
        tk.Label(side, textvariable=self.status, font=("Arial", 10), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["text_dim"], justify="left").pack(anchor="w", padx=14, pady=(0, 12))
        tk.Button(side, text="Reiniciar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.reset).pack(fill="x", padx=14, pady=(0, 8))
        self.top.bind("<Left>", lambda _e: self.move(-1))
        self.top.bind("<Right>", lambda _e: self.move(1))
        self.top.bind("<Down>", lambda _e: self.drop())
        self.top.bind("<Up>", lambda _e: self.rotate())
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.job = None
        self.reset()

    def reset(self):
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception as exc:
                _log_juegos_warning(f"No se pudo cancelar el temporizador de Tetris al reiniciar: {exc}")
        self.grid = [[""] * 10 for _ in range(20)]
        self.score = 0
        self.game_over = False
        self.current = None
        self.spawn_piece()
        self.draw()
        self.tick()

    def spawn_piece(self):
        shape = random.choice(list(self.SHAPES.keys()))
        self.current = {"shape": shape, "rot": 0, "x": 3, "y": 0}
        if self._collision(self.current["x"], self.current["y"], self.current["rot"]):
            self.game_over = True
            self.status.set(f"Fin de partida. Puntos: {self.score}")

    def _cells(self, x=None, y=None, rot=None):
        x = self.current["x"] if x is None else x
        y = self.current["y"] if y is None else y
        rot = self.current["rot"] if rot is None else rot
        shape = self.current["shape"]
        states = self.SHAPES[shape]
        cells = states[rot % len(states)]
        return [(x + cx, y + cy) for cx, cy in cells]

    def _collision(self, x, y, rot):
        for cx, cy in self._cells(x, y, rot):
            if cx < 0 or cx >= 10 or cy < 0 or cy >= 20:
                return True
            if self.grid[cy][cx]:
                return True
        return False

    def move(self, dx):
        if self.game_over:
            return
        if not self._collision(self.current["x"] + dx, self.current["y"], self.current["rot"]):
            self.current["x"] += dx
            self.draw()

    def rotate(self):
        if self.game_over:
            return
        new_rot = self.current["rot"] + 1
        if not self._collision(self.current["x"], self.current["y"], new_rot):
            self.current["rot"] = new_rot
            self.draw()

    def drop(self):
        if self.game_over:
            return
        if not self._collision(self.current["x"], self.current["y"] + 1, self.current["rot"]):
            self.current["y"] += 1
        else:
            self._lock_piece()
        self.draw()

    def _lock_piece(self):
        color = self.COLORS[self.current["shape"]]
        for x, y in self._cells():
            self.grid[y][x] = color
        new_rows = [row for row in self.grid if any(cell == "" for cell in row)]
        cleared = 20 - len(new_rows)
        for _ in range(cleared):
            new_rows.insert(0, [""] * 10)
        self.grid = new_rows
        self.score += cleared * 100
        self.spawn_piece()

    def tick(self):
        if self.game_over or not self.top.winfo_exists():
            return
        self.drop()
        self.job = self.top.after(340, self.tick)

    def draw(self):
        self.canvas.delete("all")
        for y in range(20):
            for x in range(10):
                fill = self.grid[y][x] or "#0f172a"
                self.canvas.create_rectangle(x * 30, y * 30, x * 30 + 30, y * 30 + 30, fill=fill, outline="#1e293b")
        if not self.game_over:
            color = self.COLORS[self.current["shape"]]
            for x, y in self._cells():
                self.canvas.create_rectangle(x * 30, y * 30, x * 30 + 30, y * 30 + 30, fill=color, outline="#e2e8f0")
        self.status.set(f"Puntos: {self.score}")

    def close(self):
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception as exc:
                _log_juegos_warning(f"No se pudo cancelar el temporizador de Tetris al cerrar: {exc}")
            self.job = None
        self.top.destroy()


CARD_COLORS = {
    "Rojo": "#ef4444",
    "Azul": "#3b82f6",
    "Verde": "#22c55e",
    "Amarillo": "#eab308",
}


def _card_playable(card, top_card):
    return card[0] == top_card[0] or card[1] == top_card[1]


class LastCardWindow:
    def __init__(self, master, focus_parent):
        self.top = _open_game_window(master, focus_parent, "Última Carta", rel_w=0.68, rel_h=0.72, min_w=920, min_h=700)
        self.job = None
        self.deck = []
        self.player = []
        self.computer = []
        self.discard = []
        self.player_turn = True
        self.finished = False
        self._crear_ui()
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.reset()

    def _crear_ui(self):
        header = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        header.pack(fill="x", padx=18, pady=(16, 10))
        tk.Label(header, text="Última Carta", font=("Arial", 21, "bold"), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text"]).pack(anchor="w")
        tk.Label(header, text="Juega una carta del mismo color o símbolo. Gana quien se quede sin cartas.", font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(anchor="w", pady=(4, 0))

        table = tk.Frame(self.top, bg="#064e3b", highlightthickness=1, highlightbackground=UI_JUEGOS["border"])
        table.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        self.computer_var = tk.StringVar(value="")
        tk.Label(table, textvariable=self.computer_var, font=("Arial", 12, "bold"), bg="#064e3b", fg="white").pack(pady=(22, 18))
        center = tk.Frame(table, bg="#064e3b")
        center.pack(expand=True)
        self.top_card = tk.Label(center, text="", width=8, height=4, font=("Arial", 18, "bold"), relief="raised", bd=3)
        self.top_card.pack(side="left", padx=16)
        self.draw_btn = tk.Button(center, text="Robar\ncarta", width=9, height=4, font=("Arial", 11, "bold"), bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"], relief="flat", command=self.draw_card)
        self.draw_btn.pack(side="left", padx=16)
        self.hand_frame = tk.Frame(table, bg="#064e3b")
        self.hand_frame.pack(fill="x", padx=16, pady=(20, 16))

        footer = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        footer.pack(fill="x", padx=18, pady=(0, 16))
        self.status = tk.StringVar(value="")
        tk.Label(footer, textvariable=self.status, font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(side="left")
        tk.Button(footer, text="Nueva partida", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.reset).pack(side="right")

    def _new_deck(self):
        cards = []
        for color in CARD_COLORS:
            cards.extend((color, str(value)) for value in range(10))
            cards.extend((color, action) for action in ("Salta", "+2"))
        return cards * 2

    def reset(self):
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception:
                pass
            self.job = None
        self.deck = self._new_deck()
        random.shuffle(self.deck)
        self.player = [self.deck.pop() for _ in range(7)]
        self.computer = [self.deck.pop() for _ in range(7)]
        first = self.deck.pop()
        while first[1] in {"Salta", "+2"}:
            self.deck.insert(0, first)
            first = self.deck.pop()
        self.discard = [first]
        self.player_turn = True
        self.finished = False
        self.status.set("Tu turno: selecciona una carta o roba.")
        self.draw()

    def _refill_deck(self):
        if self.deck or len(self.discard) <= 1:
            return
        top = self.discard.pop()
        self.deck = self.discard
        random.shuffle(self.deck)
        self.discard = [top]

    def _take(self, hand, amount=1):
        for _ in range(amount):
            self._refill_deck()
            if self.deck:
                hand.append(self.deck.pop())

    def draw(self):
        card = self.discard[-1]
        self.top_card.configure(text=card[1], bg=CARD_COLORS[card[0]], fg="white")
        self.computer_var.set(f"Computadora: {len(self.computer)} carta(s)")
        for widget in self.hand_frame.winfo_children():
            widget.destroy()
        for index, item in enumerate(self.player):
            state = "normal" if self.player_turn and not self.finished and _card_playable(item, card) else "disabled"
            button = tk.Button(
                self.hand_frame,
                text=f"{item[1]}\n{item[0]}",
                width=9,
                height=3,
                font=("Arial", 9, "bold"),
                bg=CARD_COLORS[item[0]],
                fg="white",
                disabledforeground="#cbd5e1",
                relief="raised",
                command=lambda i=index: self.play(i),
                state=state,
            )
            row, column = divmod(index, 8)
            button.grid(row=row, column=column, padx=3, pady=3, sticky="ew")
            self.hand_frame.grid_columnconfigure(column, weight=1)
        self.draw_btn.configure(state="normal" if self.player_turn and not self.finished else "disabled")

    def play(self, index):
        if not self.player_turn or self.finished or not (0 <= index < len(self.player)):
            return
        card = self.player[index]
        if not _card_playable(card, self.discard[-1]):
            return
        self.player.pop(index)
        self.discard.append(card)
        if not self.player:
            self._finish("¡Ganaste la partida!")
            return
        if len(self.player) == 1:
            self.status.set("¡Última carta!")
        if card[1] == "+2":
            self._take(self.computer, 2)
        self.player_turn = card[1] == "Salta"
        self.draw()
        if self.player_turn:
            self.status.set("Saltaste el turno de la computadora. Juegas otra vez.")
        else:
            self.status.set("Turno de la computadora...")
            self.job = self.top.after(650, self._computer_turn)

    def draw_card(self):
        if not self.player_turn or self.finished:
            return
        self._take(self.player)
        self.player_turn = False
        self.status.set("Robaste una carta. Turno de la computadora...")
        self.draw()
        self.job = self.top.after(650, self._computer_turn)

    def _computer_turn(self):
        self.job = None
        if self.finished or not self.top.winfo_exists():
            return
        playable = [index for index, card in enumerate(self.computer) if _card_playable(card, self.discard[-1])]
        if not playable:
            self._take(self.computer)
            playable = [index for index, card in enumerate(self.computer) if _card_playable(card, self.discard[-1])]
        if playable:
            index = random.choice(playable)
            card = self.computer.pop(index)
            self.discard.append(card)
            if not self.computer:
                self._finish("La computadora ganó. ¡Inténtalo de nuevo!")
                return
            if card[1] == "+2":
                self._take(self.player, 2)
            if card[1] == "Salta":
                self.status.set("La computadora saltó tu turno.")
                self.draw()
                self.job = self.top.after(650, self._computer_turn)
                return
        self.player_turn = True
        self.status.set("Tu turno: selecciona una carta o roba.")
        self.draw()

    def _finish(self, text):
        self.finished = True
        self.status.set(text)
        self.draw()
        messagebox.showinfo("Última Carta", text, parent=self.top)

    def close(self):
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception:
                pass
        self.top.destroy()


class NeonRaceWindow:
    WIDTH = 520
    HEIGHT = 620
    LANES = (130, 260, 390)

    def __init__(self, master, focus_parent):
        self.top = _open_game_window(master, focus_parent, "Carrera Neón", rel_w=0.58, rel_h=0.78, min_w=800, min_h=760)
        self.canvas = tk.Canvas(self.top, width=self.WIDTH, height=self.HEIGHT, bg="#020617", highlightthickness=1, highlightbackground=UI_JUEGOS["border"])
        self.canvas.pack(padx=16, pady=(16, 8))
        footer = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        footer.pack(fill="x", padx=16, pady=(0, 16))
        self.status = tk.StringVar(value="")
        tk.Label(footer, textvariable=self.status, font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(side="left")
        tk.Button(footer, text="Reiniciar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.reset).pack(side="right")
        self.top.bind("<Left>", lambda _event: self.move(-1))
        self.top.bind("<Right>", lambda _event: self.move(1))
        self.top.bind("<a>", lambda _event: self.move(-1))
        self.top.bind("<d>", lambda _event: self.move(1))
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.job = None
        self.reset()

    def reset(self):
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception:
                pass
        self.lane = 1
        self.traffic = []
        self.score = 0
        self.frame = 0
        self.running = True
        self.draw()
        self.tick()

    def move(self, direction):
        if self.running:
            self.lane = max(0, min(2, self.lane + direction))
            self.draw()

    def tick(self):
        if not self.running or not self.top.winfo_exists():
            return
        self.frame += 1
        speed = min(15, 7 + self.score // 12)
        if self.frame % max(18, 38 - self.score // 4) == 0:
            available = [lane for lane in range(3) if not any(car[0] == lane and car[1] < 150 for car in self.traffic)]
            if available:
                self.traffic.append([random.choice(available), -90, random.choice(("#f43f5e", "#a855f7", "#f59e0b"))])
        for car in self.traffic:
            car[1] += speed
        passed = [car for car in self.traffic if car[1] > self.HEIGHT]
        self.score += len(passed)
        self.traffic = [car for car in self.traffic if car[1] <= self.HEIGHT]
        player_x = self.LANES[self.lane]
        for lane, y, _color in self.traffic:
            if lane == self.lane and y + 80 >= 520 and y <= 600:
                self.running = False
                self.status.set(f"Choque. Puntaje final: {self.score}")
                self.draw()
                return
        self.draw()
        self.status.set(f"Puntaje: {self.score}  |  Velocidad: {speed}  |  Flechas o A/D")
        self.job = self.top.after(45, self.tick)

    def draw(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(55, 0, 465, self.HEIGHT, fill="#111827", outline="#38bdf8", width=4)
        offset = (self.frame * 12) % 80
        for x in (195, 325):
            for y in range(-80, self.HEIGHT + 80, 80):
                self.canvas.create_rectangle(x - 4, y + offset, x + 4, y + 42 + offset, fill="#e2e8f0", outline="")
        for lane, y, color in self.traffic:
            self._car(self.LANES[lane], y, color)
        self._car(self.LANES[self.lane], 520, UI_JUEGOS["accent"])

    def _car(self, x, y, color):
        self.canvas.create_rectangle(x - 34, y, x + 34, y + 78, fill=color, outline="#f8fafc", width=2)
        self.canvas.create_rectangle(x - 22, y + 12, x + 22, y + 35, fill="#0f172a", outline="")
        for dx in (-39, 39):
            self.canvas.create_rectangle(x + dx - 4, y + 12, x + dx + 4, y + 30, fill="#020617", outline="")
            self.canvas.create_rectangle(x + dx - 4, y + 52, x + dx + 4, y + 70, fill="#020617", outline="")

    def close(self):
        self.running = False
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception:
                pass
        self.top.destroy()


class ArenaDuelWindow:
    WIDTH = 760
    HEIGHT = 460

    def __init__(self, master, focus_parent):
        self.top = _open_game_window(master, focus_parent, "Duelo Arena", rel_w=0.7, rel_h=0.7, min_w=940, min_h=680)
        header = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        header.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(header, text="Duelo Arena", font=("Arial", 20, "bold"), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text"]).pack(anchor="w")
        tk.Label(header, text="A/D: moverte · W: saltar · F: golpear · derrota al rival de la computadora", font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(anchor="w")
        self.canvas = tk.Canvas(self.top, width=self.WIDTH, height=self.HEIGHT, bg="#172554", highlightthickness=1, highlightbackground=UI_JUEGOS["border"])
        self.canvas.pack(padx=16, pady=(0, 8))
        footer = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        footer.pack(fill="x", padx=16, pady=(0, 16))
        self.status = tk.StringVar(value="")
        tk.Label(footer, textvariable=self.status, font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"]).pack(side="left")
        tk.Button(footer, text="Reiniciar", font=("Arial", 10, "bold"), bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", command=self.reset).pack(side="right")
        self.keys = set()
        for key in ("a", "d", "w", "f"):
            self.top.bind(f"<KeyPress-{key}>", lambda _event, value=key: self.key_down(value))
            self.top.bind(f"<KeyRelease-{key}>", lambda _event, value=key: self.keys.discard(value))
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.job = None
        self.reset()

    def reset(self):
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception:
                pass
        self.player = {"x": 130.0, "y": 370.0, "vy": 0.0, "health": 100, "attack": 0, "cooldown": 0}
        self.enemy = {"x": 630.0, "y": 370.0, "vy": 0.0, "health": 100, "attack": 0, "cooldown": 0}
        self.keys.clear()
        self.running = True
        self.status.set("¡Comienza el duelo!")
        self.draw()
        self.tick()

    def key_down(self, key):
        if not self.running:
            return
        self.keys.add(key)
        if key == "w" and self.player["y"] >= 370:
            self.player["vy"] = -15
        if key == "f" and self.player["cooldown"] <= 0:
            self.player["attack"] = 8
            self.player["cooldown"] = 18

    def tick(self):
        if not self.running or not self.top.winfo_exists():
            return
        if "a" in self.keys:
            self.player["x"] -= 6
        if "d" in self.keys:
            self.player["x"] += 6
        self.player["x"] = max(35, min(self.WIDTH - 35, self.player["x"]))
        distance = self.player["x"] - self.enemy["x"]
        if abs(distance) > 82:
            self.enemy["x"] += 3.2 if distance > 0 else -3.2
        elif self.enemy["cooldown"] <= 0 and random.random() < 0.08:
            self.enemy["attack"] = 8
            self.enemy["cooldown"] = 22
        for fighter in (self.player, self.enemy):
            fighter["y"] += fighter["vy"]
            fighter["vy"] += 1.0
            if fighter["y"] >= 370:
                fighter["y"] = 370
                fighter["vy"] = 0
            fighter["attack"] = max(0, fighter["attack"] - 1)
            fighter["cooldown"] = max(0, fighter["cooldown"] - 1)
        if self.player["attack"] == 5 and abs(distance) < 92 and abs(self.player["y"] - self.enemy["y"]) < 65:
            self.enemy["health"] = max(0, self.enemy["health"] - random.randint(8, 14))
            self.enemy["x"] += 20 if distance < 0 else -20
        if self.enemy["attack"] == 5 and abs(distance) < 92 and abs(self.player["y"] - self.enemy["y"]) < 65:
            self.player["health"] = max(0, self.player["health"] - random.randint(6, 12))
            self.player["x"] += 20 if distance > 0 else -20
        if self.player["health"] <= 0 or self.enemy["health"] <= 0:
            self.running = False
            text = "¡Ganaste el duelo!" if self.enemy["health"] <= 0 else "El rival ganó. ¡Revancha!"
            self.status.set(text)
            self.draw()
            messagebox.showinfo("Duelo Arena", text, parent=self.top)
            return
        self.status.set(f"Tu energía: {self.player['health']}  |  Rival: {self.enemy['health']}")
        self.draw()
        self.job = self.top.after(35, self.tick)

    def draw(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 420, self.WIDTH, self.HEIGHT, fill="#713f12", outline="")
        self.canvas.create_rectangle(20, 18, 320, 42, fill="#450a0a", outline="#f8fafc")
        self.canvas.create_rectangle(20, 18, 20 + 3 * self.player["health"], 42, fill=UI_JUEGOS["success"], outline="")
        self.canvas.create_rectangle(440, 18, 740, 42, fill="#450a0a", outline="#f8fafc")
        self.canvas.create_rectangle(740 - 3 * self.enemy["health"], 18, 740, 42, fill=UI_JUEGOS["danger"], outline="")
        self._fighter(self.player, UI_JUEGOS["accent"], facing=1 if self.enemy["x"] > self.player["x"] else -1)
        self._fighter(self.enemy, UI_JUEGOS["danger"], facing=1 if self.player["x"] > self.enemy["x"] else -1)

    def _fighter(self, fighter, color, facing):
        x, y = fighter["x"], fighter["y"]
        self.canvas.create_oval(x - 18, y - 62, x + 18, y - 26, fill="#f1c27d", outline="#0f172a", width=2)
        self.canvas.create_rectangle(x - 22, y - 28, x + 22, y + 28, fill=color, outline="#f8fafc", width=2)
        self.canvas.create_line(x - 12, y + 28, x - 22, y + 50, fill="#f8fafc", width=7)
        self.canvas.create_line(x + 12, y + 28, x + 22, y + 50, fill="#f8fafc", width=7)
        reach = 62 if fighter["attack"] else 34
        self.canvas.create_line(x, y - 12, x + facing * reach, y - 8, fill="#f1c27d", width=9)

    def close(self):
        self.running = False
        if self.job:
            try:
                self.top.after_cancel(self.job)
            except Exception:
                pass
        self.top.destroy()


class MorseMissionWindow:
    def __init__(self, master, focus_parent):
        self.top = _open_game_window(master, focus_parent, "Misión Morse", rel_w=0.68, rel_h=0.82, min_w=920, min_h=720)
        self.score = 0
        self.streak = 0
        self.round = 0
        self.mode = "decode"
        self.word = ""

        header = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        header.pack(fill="x", padx=22, pady=(20, 12))
        tk.Label(header, text="Misión Morse", font=("Arial", 22, "bold"), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text"]).pack(anchor="w")
        tk.Label(
            header,
            text="Alterna entre recibir mensajes y construir palabras con punto y raya.",
            font=("Arial", 10), bg=UI_JUEGOS["bg"], fg=UI_JUEGOS["text_dim"],
        ).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self.top, bg=UI_JUEGOS["bg"])
        body.pack(fill="both", expand=True, padx=22, pady=(0, 18))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        mission = _panel(body, "Reto actual", "Punto = señal corta · Raya = tres unidades")
        mission.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        reference = _panel(body, "Tabla de referencia", "Usa la tabla al aprender; intenta depender menos de ella con cada ronda.")
        reference.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.mode_var = tk.StringVar()
        self.prompt_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.score_var = tk.StringVar()
        tk.Label(mission, textvariable=self.mode_var, font=("Arial", 12, "bold"), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["accent"]).pack(anchor="w", padx=16, pady=(4, 8))
        tk.Label(
            mission, textvariable=self.prompt_var, font=("DejaVu Sans Mono", 22, "bold"),
            bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"], justify="center", wraplength=500,
            padx=16, pady=22,
        ).pack(fill="x", padx=16, pady=(0, 12))

        tk.Label(mission, text="Tu respuesta", font=("Arial", 10, "bold"), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["text_dim"]).pack(anchor="w", padx=16)
        self.answer = tk.Entry(
            mission, font=("DejaVu Sans Mono", 17, "bold"), bg="#07111f", fg=UI_JUEGOS["text"],
            insertbackground="white", relief="flat", justify="center",
        )
        self.answer.pack(fill="x", padx=16, pady=(6, 10), ipady=10)
        self.answer.bind("<Return>", lambda _event: self.check_answer())

        symbols = tk.Frame(mission, bg=UI_JUEGOS["panel"])
        symbols.pack(fill="x", padx=16, pady=(0, 10))
        for label, value in (("Punto  ·", "."), ("Raya  —", "-"), ("Separar letra", " ")):
            tk.Button(
                symbols, text=label, command=lambda token=value: self._append_symbol(token),
                bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["text"], relief="flat", padx=12, pady=8,
            ).pack(side="left", padx=(0, 7))
        tk.Button(symbols, text="Borrar", command=self._backspace, bg=UI_JUEGOS["danger"], fg="white", relief="flat", padx=12, pady=8).pack(side="right")

        actions = tk.Frame(mission, bg=UI_JUEGOS["panel"])
        actions.pack(fill="x", padx=16, pady=(0, 10))
        tk.Button(actions, text="Comprobar", command=self.check_answer, bg=UI_JUEGOS["success"], fg="white", relief="flat", padx=15, pady=9, font=("Arial", 10, "bold")).pack(side="left")
        tk.Button(actions, text="Pista", command=self.show_hint, bg=UI_JUEGOS["warning"], fg="#271400", relief="flat", padx=15, pady=9, font=("Arial", 10, "bold")).pack(side="left", padx=8)
        tk.Button(actions, text="Siguiente", command=self.new_round, bg=UI_JUEGOS["accent"], fg="#05243a", relief="flat", padx=15, pady=9, font=("Arial", 10, "bold")).pack(side="right")

        tk.Label(mission, textvariable=self.status_var, font=("Arial", 10), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["text_dim"], wraplength=520, justify="left").pack(anchor="w", padx=16, pady=(0, 7))
        tk.Label(mission, textvariable=self.score_var, font=("Arial", 11, "bold"), bg=UI_JUEGOS["panel"], fg=UI_JUEGOS["accent"]).pack(anchor="w", padx=16, pady=(0, 16))

        rows = ["A .-     B -...   C -.-.   D -..", "E .      F ..-.   G --.    H ....", "I ..     J .---   K -.-    L .-..", "M --     N -.     O ---    P .--.", "Q --.-   R .-.    S ...    T -", "U ..-    V ...-   W .--    X -..-", "Y -.--   Z --..", "1 .----  2 ..---  3 ...--", "4 ....-  5 .....  6 -....", "7 --...  8 ---..  9 ----.  0 -----"]
        tk.Label(
            reference, text="\n".join(rows), font=("DejaVu Sans Mono", 11), bg=UI_JUEGOS["panel"],
            fg=UI_JUEGOS["text"], justify="left", anchor="nw",
        ).pack(fill="both", expand=True, padx=16, pady=(4, 12))
        tk.Label(
            reference, text="Espacio: separa letras\nBarra /: separa palabras\nSOS: ... --- ...",
            font=("Arial", 10, "bold"), bg=UI_JUEGOS["panel_alt"], fg=UI_JUEGOS["warning"],
            justify="left", padx=12, pady=12,
        ).pack(fill="x", padx=16, pady=(0, 16))

        self.new_round()

    def _append_symbol(self, token):
        self.answer.insert("end", token)
        self.answer.focus_set()

    def _backspace(self):
        value = self.answer.get()
        self.answer.delete(0, "end")
        self.answer.insert(0, value[:-1])
        self.answer.focus_set()

    def new_round(self):
        self.round += 1
        self.word = random.choice([word for word in MORSE_WORDS if word != self.word])
        self.mode = "decode" if self.round % 2 else "encode"
        self.answer.delete(0, "end")
        if self.mode == "decode":
            self.mode_var.set("RECEPCIÓN · Descifra la palabra")
            self.prompt_var.set(encode_morse(self.word))
            self.status_var.set("Escribe la palabra que representa la señal.")
        else:
            self.mode_var.set("TRANSMISIÓN · Construye la señal")
            self.prompt_var.set(_normalize_morse_text(self.word))
            self.status_var.set("Escribe puntos y rayas, separando cada letra con un espacio.")
        self._update_score()
        self.answer.focus_set()

    def check_answer(self):
        raw = self.answer.get().strip()
        expected = _normalize_morse_text(self.word) if self.mode == "decode" else encode_morse(self.word)
        actual = _normalize_morse_text(raw) if self.mode == "decode" else " ".join(raw.replace("/", " / ").split())
        if actual == expected:
            self.score += 10 + min(self.streak * 2, 10)
            self.streak += 1
            self.status_var.set(f"¡Correcto! {self.word} = {encode_morse(self.word)}")
            self.top.after(850, self.new_round)
        else:
            self.streak = 0
            self.status_var.set("Aún no coincide. Revisa cada letra y la separación; puedes pedir una pista.")
        self._update_score()

    def show_hint(self):
        self.score = max(0, self.score - 2)
        if self.mode == "decode":
            self.status_var.set(f"Pista: empieza con {self.word[0]} ({encode_morse(self.word[0])}) y tiene {len(self.word)} letras.")
        else:
            first = _normalize_morse_text(self.word)[0]
            self.status_var.set(f"Pista: {first} se codifica {MORSE_CODE[first]}. Separa todas las letras con espacios.")
        self._update_score()

    def _update_score(self):
        self.score_var.set(f"Puntos: {self.score}   ·   Racha: {self.streak}   ·   Ronda: {self.round}")


__all__ = [
    "VentanaJuegos",
    "MorseMissionWindow",
    "MORSE_CODE",
    "encode_morse",
    "decode_morse",
]
