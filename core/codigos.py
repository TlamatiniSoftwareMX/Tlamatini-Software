import html
import json
import webbrowser
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from core.inventario import actualizar_item, buscar_item_por_codigo_barras_global, buscar_item_por_id, listar_items
from core.memoria import DATA_DIR


RUTA_CODIGOS_JSON = DATA_DIR / "memoria" / "codigos.json"
RUTA_CODIGOS_IMG = DATA_DIR / "base_datos" / "codigos_barras"
RUTA_CODIGOS_PRINT = DATA_DIR / "memoria" / "codigos_print"

CODE39 = {
    "0": "nnnwwnwnn",
    "1": "wnnwnnnnw",
    "2": "nnwwnnnnw",
    "3": "wnwwnnnnn",
    "4": "nnnwwnnnw",
    "5": "wnnwwnnnn",
    "6": "nnwwwnnnn",
    "7": "nnnwnnwnw",
    "8": "wnnwnnwnn",
    "9": "nnwwnnwnn",
    "A": "wnnnnwnnw",
    "B": "nnwnnwnnw",
    "C": "wnwnnwnnn",
    "D": "nnnnwwnnw",
    "E": "wnnnwwnnn",
    "F": "nnwnwwnnn",
    "G": "nnnnnwwnw",
    "H": "wnnnnwwnn",
    "I": "nnwnnwwnn",
    "J": "nnnnwwwnn",
    "K": "wnnnnnnww",
    "L": "nnwnnnnww",
    "M": "wnwnnnnwn",
    "N": "nnnnwnnww",
    "O": "wnnnwnnwn",
    "P": "nnwnwnnwn",
    "Q": "nnnnnnwww",
    "R": "wnnnnnwwn",
    "S": "nnwnnnwwn",
    "T": "nnnnwnwwn",
    "U": "wwnnnnnnw",
    "V": "nwwnnnnnw",
    "W": "wwwnnnnnn",
    "X": "nwnnwnnnw",
    "Y": "wwnnwnnnn",
    "Z": "nwwnwnnnn",
    "-": "nwnnnnwnw",
    ".": "wwnnnnwnn",
    " ": "nwwnnnwnn",
    "$": "nwnwnwnnn",
    "/": "nwnwnnnwn",
    "+": "nwnnnwnwn",
    "%": "nnnwnwnwn",
    "*": "nwnnwnwnn",
}

ESTRUCTURA_CODIGOS_BASE = {
    "next_sequence": 1,
    "items": [],
}


def _ahora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _asegurar_archivos() -> None:
    RUTA_CODIGOS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RUTA_CODIGOS_IMG.mkdir(parents=True, exist_ok=True)
    RUTA_CODIGOS_PRINT.mkdir(parents=True, exist_ok=True)
    if not RUTA_CODIGOS_JSON.exists():
        RUTA_CODIGOS_JSON.write_text(json.dumps(ESTRUCTURA_CODIGOS_BASE, indent=4, ensure_ascii=False), encoding="utf-8")


def _normalizar_texto(valor) -> str:
    return str(valor or "").strip()


def _normalizar_registro(registro: Dict) -> Dict:
    return {
        "code": _normalizar_texto(registro.get("code", "")).upper(),
        "item_id": _normalizar_texto(registro.get("item_id", "")),
        "categoria": _normalizar_texto(registro.get("categoria", "")),
        "nombre": _normalizar_texto(registro.get("nombre", "")),
        "especificaciones": _normalizar_texto(registro.get("especificaciones", "")),
        "image_path": _normalizar_texto(registro.get("image_path", "")),
        "status": _normalizar_texto(registro.get("status", "activo")) or "activo",
        "created_at": registro.get("created_at") or _ahora_iso(),
        "updated_at": registro.get("updated_at") or _ahora_iso(),
    }


def _cargar_data() -> Dict:
    _asegurar_archivos()
    try:
        data = json.loads(RUTA_CODIGOS_JSON.read_text(encoding="utf-8"))
    except Exception:
        data = deepcopy(ESTRUCTURA_CODIGOS_BASE)
    items = []
    for registro in list(data.get("items", []) or []):
        if not isinstance(registro, dict):
            continue
        normalizado = _normalizar_registro(registro)
        if normalizado["code"]:
            items.append(normalizado)
    return {
        "next_sequence": max(1, int(data.get("next_sequence", 1))),
        "items": sorted(items, key=lambda item: (item.get("created_at", ""), item.get("code", "")), reverse=True),
    }


def _guardar_data(data: Dict) -> Dict:
    _asegurar_archivos()
    normalizado = {
        "next_sequence": max(1, int(data.get("next_sequence", 1))),
        "items": [_normalizar_registro(registro) for registro in list(data.get("items", []) or []) if _normalizar_texto(registro.get("code", ""))],
    }
    RUTA_CODIGOS_JSON.write_text(json.dumps(normalizado, indent=4, ensure_ascii=False), encoding="utf-8")
    return normalizado


def _codigo_disponible(data: Dict) -> str:
    usados = {registro.get("code", "") for registro in data.get("items", [])}
    while True:
        codigo = f"TLA{data['next_sequence']:09d}"
        data["next_sequence"] += 1
        if codigo not in usados and not buscar_item_por_codigo_barras_global(codigo):
            return codigo


def _extraer_especificaciones_item(item: Dict) -> str:
    partes = []
    for etiqueta, valor in [
        ("Tipo", item.get("tipo", item.get("subcategoria", ""))),
        ("Cantidad", item.get("cantidad", "")),
        ("Unidad", item.get("unidad", "")),
        ("Detalle", item.get("peso_contenido", "")),
        ("Composición", item.get("composicion", "")),
        ("Propósito", item.get("proposito", "")),
        ("Lote", item.get("lote", "")),
    ]:
        texto = _normalizar_texto(valor)
        if texto:
            partes.append(f"{etiqueta}: {texto}")
    return " | ".join(partes)


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def renderizar_codigo_barras(code: str, nombre: str = "", especificaciones: str = "") -> str:
    code = _normalizar_texto(code).upper()
    if not code:
        raise ValueError("El código es obligatorio.")
    payload = f"*{code}*"
    for char in payload:
        if char not in CODE39:
            raise ValueError(f"El código contiene un carácter no soportado para Code39: {char}")

    narrow = 6
    wide = 15
    gap = narrow
    quiet = 48
    bar_height = 180
    label_space = 72
    text_space = 60 if especificaciones else 36
    total_width = quiet * 2
    for idx, char in enumerate(payload):
        patron = CODE39[char]
        for token in patron:
            total_width += wide if token == "w" else narrow
        if idx < len(payload) - 1:
            total_width += gap
    total_height = 20 + bar_height + label_space + text_space

    image = Image.new("RGB", (total_width, total_height), "white")
    draw = ImageDraw.Draw(image)
    x = quiet
    y = 28
    for idx, char in enumerate(payload):
        patron = CODE39[char]
        for pos, token in enumerate(patron):
            ancho = wide if token == "w" else narrow
            if pos % 2 == 0:
                draw.rectangle([x, y, x + ancho - 1, y + bar_height], fill="black")
            x += ancho
        if idx < len(payload) - 1:
            x += gap

    draw.text((quiet, y + bar_height + 12), code, fill="black", font=_font(34))
    if nombre:
        draw.text((quiet, y + bar_height + 48), nombre[:64], fill="black", font=_font(22))
    if especificaciones:
        draw.text((quiet, y + bar_height + 80), especificaciones[:120], fill="black", font=_font(16))

    ruta = RUTA_CODIGOS_IMG / f"{code}.png"
    image.save(ruta, dpi=(300, 300))
    return str(ruta)


def listar_codigos() -> List[Dict]:
    return deepcopy(_cargar_data().get("items", []))


def buscar_codigo(code: str) -> Optional[Dict]:
    code = _normalizar_texto(code).upper()
    if not code:
        return None
    for registro in _cargar_data().get("items", []):
        if registro.get("code") == code:
            return deepcopy(registro)
    return None


def eliminar_codigo(code: str) -> None:
    code = _normalizar_texto(code).upper()
    if not code:
        raise ValueError("El código es obligatorio.")

    data = _cargar_data()
    eliminado = None
    restantes = []
    for registro in data.get("items", []):
        if registro.get("code") == code and eliminado is None:
            eliminado = registro
            continue
        restantes.append(registro)

    if eliminado is None:
        raise ValueError("No se encontró ese código.")

    item_id = _normalizar_texto(eliminado.get("item_id", ""))
    if item_id:
        item = buscar_item_por_id(item_id)
        if item:
            actualizar_item(item_id, codigo_barras="")

    ruta_imagen = Path(_normalizar_texto(eliminado.get("image_path", "")))
    if ruta_imagen.exists():
        try:
            ruta_imagen.unlink()
        except Exception:
            pass

    data["items"] = restantes
    _guardar_data(data)


def generar_codigo_libre(nombre: str = "Sin asignar", especificaciones: str = "Pendiente de asociación") -> Dict:
    data = _cargar_data()
    code = _codigo_disponible(data)
    image_path = renderizar_codigo_barras(code, nombre=_normalizar_texto(nombre), especificaciones=_normalizar_texto(especificaciones))
    registro = _normalizar_registro(
        {
            "code": code,
            "item_id": "",
            "categoria": "",
            "nombre": _normalizar_texto(nombre) or "Sin asignar",
            "especificaciones": _normalizar_texto(especificaciones) or "Pendiente de asociación",
            "image_path": image_path,
            "status": "disponible",
            "created_at": _ahora_iso(),
            "updated_at": _ahora_iso(),
        }
    )
    data["items"].append(registro)
    _guardar_data(data)
    return deepcopy(registro)


def generar_codigo_para_item(item_id: str) -> Dict:
    item = buscar_item_por_id(item_id)
    if not item:
        raise ValueError("No se encontró el item de inventario.")

    data = _cargar_data()
    for registro in data["items"]:
        if registro.get("item_id") == item_id and registro.get("status") == "activo":
            registro["status"] = "reemplazado"
            registro["updated_at"] = _ahora_iso()

    code = _codigo_disponible(data)
    nombre = _normalizar_texto(item.get("nombre", ""))
    categoria = _normalizar_texto(item.get("categoria", ""))
    especificaciones = _extraer_especificaciones_item(item)
    image_path = renderizar_codigo_barras(code, nombre=nombre, especificaciones=especificaciones)

    actualizar_item(item_id, codigo_barras=code)

    registro = _normalizar_registro(
        {
            "code": code,
            "item_id": item_id,
            "categoria": categoria,
            "nombre": nombre,
            "especificaciones": especificaciones,
            "image_path": image_path,
            "status": "activo",
            "created_at": _ahora_iso(),
            "updated_at": _ahora_iso(),
        }
    )
    data["items"].append(registro)
    _guardar_data(data)
    return deepcopy(registro)


def sincronizar_codigo_con_item(item: Dict) -> Optional[Dict]:
    code = _normalizar_texto((item or {}).get("codigo_barras", "")).upper()
    if not code:
        return None
    data = _cargar_data()
    nombre = _normalizar_texto(item.get("nombre", "")) or "Sin asignar"
    categoria = _normalizar_texto(item.get("categoria", ""))
    especificaciones = _extraer_especificaciones_item(item)
    existente = None
    for registro in data["items"]:
        if registro.get("code") == code:
            existente = registro
            break
    if existente is None:
        image_path = renderizar_codigo_barras(code, nombre=nombre, especificaciones=especificaciones)
        existente = {
            "code": code,
            "item_id": "",
            "categoria": "",
            "nombre": "",
            "especificaciones": "",
            "image_path": image_path,
            "status": "disponible",
            "created_at": _ahora_iso(),
            "updated_at": _ahora_iso(),
        }
        data["items"].append(existente)
    else:
        image_path = existente.get("image_path", "")
        if not image_path:
            image_path = renderizar_codigo_barras(code, nombre=nombre, especificaciones=especificaciones)

    for registro in data["items"]:
        if registro is existente:
            continue
        if registro.get("item_id") == item.get("id") and registro.get("status") == "activo":
            registro["status"] = "reemplazado"
            registro["updated_at"] = _ahora_iso()

    existente.update(
        _normalizar_registro(
            {
                "code": code,
                "item_id": item.get("id", ""),
                "categoria": categoria,
                "nombre": nombre,
                "especificaciones": especificaciones,
                "image_path": image_path,
                "status": "activo",
                "created_at": existente.get("created_at") or _ahora_iso(),
                "updated_at": _ahora_iso(),
            }
        )
    )
    _guardar_data(data)
    return deepcopy(existente)


def reaplicar_codigo_a_item(code: str) -> Dict:
    registro = buscar_codigo(code)
    if not registro:
        raise ValueError("Ese código no existe en el registro.")
    item_id = _normalizar_texto(registro.get("item_id", ""))
    if not item_id:
        raise ValueError("Ese código no tiene item asociado.")
    item = buscar_item_por_id(item_id)
    if not item:
        raise ValueError("El item asociado ya no existe en inventario.")
    actualizar_item(item_id, codigo_barras=registro["code"])
    return buscar_item_por_id(item_id) or item


def listar_items_inventario_para_codigos() -> List[Dict]:
    items = []
    for item in listar_items():
        categoria = _normalizar_texto(item.get("categoria", ""))
        nombre = _normalizar_texto(item.get("nombre", ""))
        if not nombre:
            continue
        items.append(
            {
                "id": item.get("id", ""),
                "categoria": categoria,
                "nombre": nombre,
                "tipo": _normalizar_texto(item.get("tipo", item.get("subcategoria", ""))),
                "codigo_barras": _normalizar_texto(item.get("codigo_barras", "")),
                "especificaciones": _extraer_especificaciones_item(item),
                "label": f"{categoria} | {nombre} | {_normalizar_texto(item.get('tipo', item.get('subcategoria', '')))}",
            }
        )
    items.sort(key=lambda item: (item["categoria"].lower(), item["nombre"].lower(), item["id"]))
    return items


def _html_registros(registros: List[Dict], titulo: str) -> str:
    bloques = []
    for registro in registros:
        image_path = Path(registro.get("image_path", "")).resolve()
        image_uri = image_path.as_uri() if image_path.exists() else ""
        bloques.append(
            f"""
            <div class="label">
              <div class="name">{html.escape(registro.get('nombre', 'Sin nombre'))}</div>
              <div class="meta">{html.escape(registro.get('categoria', ''))}</div>
              <img src="{image_uri}" alt="{html.escape(registro.get('code', ''))}">
              <div class="code">{html.escape(registro.get('code', ''))}</div>
              <div class="spec">{html.escape(registro.get('especificaciones', ''))}</div>
            </div>
            """
        )
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{html.escape(titulo)}</title>
      <style>
        body {{ font-family: Arial, sans-serif; background: white; color: black; margin: 18px; }}
        h1 {{ font-size: 20px; margin: 0 0 14px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 18px; }}
        .label {{ border: 1px solid #222; padding: 12px; break-inside: avoid; }}
        .name {{ font-size: 16px; font-weight: bold; }}
        .meta, .spec {{ font-size: 12px; margin-top: 4px; }}
        .code {{ font-size: 16px; font-weight: bold; letter-spacing: 1px; margin-top: 6px; }}
        img {{ width: 100%; max-width: 320px; display: block; margin-top: 8px; }}
        @media print {{
          body {{ margin: 10mm; }}
          .label {{ page-break-inside: avoid; }}
        }}
      </style>
    </head>
    <body>
      <h1>{html.escape(titulo)}</h1>
      <div class="grid">
        {''.join(bloques)}
      </div>
    </body>
    </html>
    """


def abrir_vista_imprimible(code: Optional[str] = None) -> str:
    if code:
        registro = buscar_codigo(code)
        if not registro:
            raise ValueError("No se encontró ese código.")
        registros = [registro]
        titulo = f"Imprimir código {code}"
        nombre_archivo = f"codigo_{code}.html"
    else:
        registros = [registro for registro in listar_codigos() if registro.get("status") == "activo"]
        if not registros:
            raise ValueError("No hay códigos activos para imprimir.")
        titulo = "Imprimir todos los códigos"
        nombre_archivo = "codigos_todos.html"
    ruta = RUTA_CODIGOS_PRINT / nombre_archivo
    ruta.write_text(_html_registros(registros, titulo), encoding="utf-8")
    try:
        webbrowser.open(ruta.resolve().as_uri())
    except Exception:
        pass
    return str(ruta)
