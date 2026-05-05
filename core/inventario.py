from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.logs import registrar_log
from core.memoria import guardar_seccion, obtener_seccion
from core.texto import normalizar_texto


SECCION_CATEGORIAS = "inventario_categorias"
SECCION_ITEMS = "inventario"
UNIDADES_ALIMENTOS = ["Piezas", "Bolsas", "Cajas", "Botellas", "Latas", "Paquetes"]
UNIDADES_MEDIBLES = {"miligramo", "miligramos", "gramo", "gramos", "kilogramo", "kilogramos", "mililitro", "mililitros", "litro", "litros", "onza", "onzas", "libra", "libras", "mg", "g", "gr", "kg", "ml", "l", "oz", "lb"}
UNIDADES_CONTENIDO = {"miligramo", "miligramos", "gramo", "gramos", "kilogramo", "kilogramos", "mililitro", "mililitros", "litro", "litros", "mg", "g", "gr", "kg", "ml", "l"}


def _ahora_id(prefijo: str) -> str:
    return f"{prefijo}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _normalizar(texto: str) -> str:
    return normalizar_texto(texto)


def _to_float(valor) -> Optional[float]:
    if valor in (None, ""):
        return None

    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


def _formatear_numero(valor: Optional[float]) -> str:
    if valor is None:
        return ""
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.2f}".rstrip("0").rstrip(".")


def _parsear_magnitud(texto: str) -> Tuple[Optional[float], str]:
    limpio = " ".join(str(texto or "").strip().lower().replace(",", ".").split())
    if not limpio:
        return None, ""

    numero = []
    unidad = []
    leyendo_unidad = False
    for char in limpio:
        if not leyendo_unidad and (char.isdigit() or char == "."):
            numero.append(char)
            continue
        if char == " " and not leyendo_unidad:
            leyendo_unidad = True
            continue
        leyendo_unidad = True
        unidad.append(char)

    try:
        valor = float("".join(numero)) if numero else None
    except ValueError:
        valor = None

    return valor, "".join(unidad).strip()


def _es_categoria_alimentos(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "alimentos"


def _es_categoria_insumos_medicos(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "insumos medicos"


def _es_categoria_combate(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "combate"


def _es_categoria_herramientas(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "herramientas"


def _es_categoria_animales(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "animales"


def _es_categoria_plantas(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "plantas"


def _es_categoria_comunicacion(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "comunicacion"


def _es_categoria_energia(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "energia"


def _es_categoria_ropa(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "ropa"


def _es_categoria_higiene(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "higiene"


def _es_categoria_movilidad(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "movilidad"


def _es_categoria_cocina_preparacion(categoria: Dict) -> bool:
    return _normalizar(categoria.get("nombre", "")) == "cocina y preparacion"


def _es_unidad_medible(unidad: str) -> bool:
    return _normalizar(unidad) in UNIDADES_MEDIBLES


def _es_unidad_inventario_alimentos_valida(unidad: str) -> bool:
    return _normalizar(unidad) in {_normalizar(x) for x in UNIDADES_ALIMENTOS}


def _normalizar_texto_valor(valor) -> str:
    return str(valor or "").strip()


def _descripcion_stock_item(item: Dict, cantidad: Optional[float]) -> str:
    if cantidad is None:
        return ""

    categoria_n = _normalizar(item.get("categoria", ""))
    cantidad_txt = _formatear_numero(cantidad)
    unidad = _normalizar_texto_valor(item.get("unidad", ""))
    contenido = _normalizar_texto_valor(item.get("peso_contenido", ""))

    if categoria_n == "insumos medicos":
        if contenido and unidad:
            return f"{cantidad_txt} unidad(es) de {contenido} {unidad}".strip()
        if unidad:
            return f"{cantidad_txt} unidad(es) ({unidad})"
        return f"{cantidad_txt} unidad(es)"

    if unidad:
        return f"{cantidad_txt} {unidad}".strip()
    return cantidad_txt


def _normalizar_campos_categoria(campos_raw) -> List[Dict]:
    if not isinstance(campos_raw, list):
        return []

    normalizados = []
    ids_usados = set()
    for idx, campo in enumerate(campos_raw):
        if not isinstance(campo, dict):
            continue
        etiqueta = _normalizar_texto_valor(campo.get("label", ""))
        if not etiqueta:
            continue
        campo_id = _normalizar_texto_valor(campo.get("id", "")) or f"campo_{idx + 1}"
        base_id = campo_id
        sufijo = 2
        while campo_id in ids_usados:
            campo_id = f"{base_id}_{sufijo}"
            sufijo += 1
        ids_usados.add(campo_id)
        normalizados.append(
            {
                "id": campo_id,
                "label": etiqueta,
                "posicion": int(campo.get("posicion", len(normalizados))),
            }
        )

    normalizados.sort(key=lambda item: (int(item.get("posicion", 0)), item.get("label", "")))
    for idx, campo in enumerate(normalizados):
        campo["posicion"] = idx
    return normalizados


def _normalizar_catalogos_categoria(catalogos_raw) -> Dict[str, List[str]]:
    if not isinstance(catalogos_raw, dict):
        return {}

    normalizados = {}
    for clave, valores in catalogos_raw.items():
        nombre_clave = _normalizar_texto_valor(clave)
        if not nombre_clave or not isinstance(valores, list):
            continue
        vistos = set()
        lista = []
        for valor in valores:
            texto = _normalizar_texto_valor(valor)
            if not texto:
                continue
            texto_n = _normalizar(texto)
            if texto_n in vistos:
                continue
            vistos.add(texto_n)
            lista.append(texto)
        normalizados[nombre_clave] = lista
    return normalizados


def _categoria_default(nombre: str, icono: str, subcategorias: List[str], unidades: List[str]) -> Dict:
    return {
        "id": _ahora_id("CAT"),
        "nombre": nombre,
        "icono": icono,
        "color": "#13223f",
        "subcategorias": subcategorias,
        "unidades": unidades,
        "campos": [],
        "catalogos": {},
        "posicion": 0,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _categorias_base() -> List[Dict]:
    categorias = [
        _categoria_default(
            "Alimentos",
            "🍽",
            ["general", "agua", "grano", "enlatado", "deshidratado", "suplemento"],
            UNIDADES_ALIMENTOS,
        ),
        _categoria_default(
            "Combate",
            "🛡",
            ["proteccion", "municion", "porte", "comunicacion", "tactico"],
            ["pieza", "pzas", "kit", "caja", "juego"],
        ),
        _categoria_default(
            "Herramientas",
            "🛠",
            ["manual", "electrica", "corte", "medicion", "rescate"],
            ["pieza", "pzas", "kit", "caja", "juego"],
        ),
        _categoria_default(
            "Insumos medicos",
            "🩺",
            ["medicamento", "curacion", "jeringa", "equipo", "consumible"],
            ["pieza", "pzas", "tableta", "capsula", "ampolleta", "frasco", "mg", "g", "ml", "l"],
        ),
        _categoria_default(
            "Animales",
            "🐾",
            ["trabajo", "carne", "piel", "cuero", "productos varios"],
            ["cabeza", "animal"],
        ),
        _categoria_default(
            "Plantas",
            "🌿",
            ["hortaliza", "frutal", "medicinal", "ornamental", "forraje"],
            ["planta", "maceta", "charola"],
        ),
        _categoria_default(
            "Comunicacion",
            "📡",
            ["radio portatil", "radio base", "repetidor", "antena", "telefono satelital", "bateria", "pantalla"],
            ["pieza", "pzas", "kit"],
        ),
        _categoria_default(
            "Energia",
            "🔋",
            ["panel solar", "bateria recargable", "inversor", "controlador", "generador"],
            ["pieza", "pzas", "kit"],
        ),
        _categoria_default(
            "Higiene",
            "🧼",
            ["papel higienico", "pasta dental", "cepillo dental", "jabon", "toalla sanitaria", "limpieza corporal", "limpieza general"],
            ["pieza", "pzas", "paquete", "caja", "botella", "rollo", "kit"],
        ),
        _categoria_default(
            "Movilidad",
            "🎒",
            ["vehiculo", "mochila de evacuacion", "transporte", "llanta", "combustible", "refaccion", "accesorio"],
            ["pieza", "pzas", "kit", "juego", "unidad"],
        ),
        _categoria_default(
            "Cocina y preparacion",
            "🍲",
            ["estufa", "cartucho de gas", "horno", "deshidratador", "utensilio", "contenedor", "combustible"],
            ["pieza", "pzas", "kit", "caja", "cartucho", "tanque"],
        ),
        _categoria_default(
            "Ropa",
            "🥾",
            ["chaqueta", "pantalon", "camisa", "guantes", "gorro", "bota", "calcetin", "impermeable"],
            ["pieza", "pzas", "par", "juego", "kit"],
        ),
    ]
    for idx, categoria in enumerate(categorias):
        categoria["posicion"] = idx
        if categoria["nombre"] == "Alimentos":
            categoria["color"] = "#0F766E"
        elif categoria["nombre"] == "Combate":
            categoria["color"] = "#7F1D1D"
        elif categoria["nombre"] == "Herramientas":
            categoria["color"] = "#1D4ED8"
        elif categoria["nombre"] == "Insumos medicos":
            categoria["color"] = "#9333EA"
        elif categoria["nombre"] == "Animales":
            categoria["color"] = "#92400E"
        elif categoria["nombre"] == "Plantas":
            categoria["color"] = "#15803D"
        elif categoria["nombre"] == "Comunicacion":
            categoria["color"] = "#0E7490"
            categoria["catalogos"] = {"modelos": [], "bandas": []}
        elif categoria["nombre"] == "Energia":
            categoria["color"] = "#CA8A04"
        elif categoria["nombre"] == "Higiene":
            categoria["color"] = "#0891B2"
        elif categoria["nombre"] == "Movilidad":
            categoria["color"] = "#2563EB"
        elif categoria["nombre"] == "Cocina y preparacion":
            categoria["color"] = "#C2410C"
        elif categoria["nombre"] == "Ropa":
            categoria["color"] = "#7C3AED"
            categoria["catalogos"] = {"climas_ropa": ["Frio", "Calor", "Mixto"]}
    return categorias


def _normalizar_categorias(raw) -> List[Dict]:
    if not isinstance(raw, list) or not raw:
        categorias = _categorias_base()
        guardar_seccion(SECCION_CATEGORIAS, categorias)
        return categorias

    normalizadas = []
    cambiado = False
    base_por_nombre = {_normalizar(x["nombre"]): x for x in _categorias_base()}

    for categoria in raw:
        if isinstance(categoria, str):
            cambiado = True
            continue

        if not isinstance(categoria, dict):
            cambiado = True
            continue

        nombre_normalizado = _normalizar(categoria.get("nombre", ""))
        if nombre_normalizado not in base_por_nombre:
            cambiado = True
            continue

        color_base = base_por_nombre.get(nombre_normalizado, {}).get("color", "#13223f")
        nombre_categoria = categoria.get("nombre", "General").strip() or "General"
        unidades = list(categoria.get("unidades", ["pieza", "pzas"])) or ["pieza", "pzas"]
        if _normalizar(nombre_categoria) == "alimentos":
            if [_normalizar(u) for u in unidades] != [_normalizar(u) for u in UNIDADES_ALIMENTOS]:
                unidades = list(UNIDADES_ALIMENTOS)
                cambiado = True
        item = {
            "id": categoria.get("id") or _ahora_id("CAT"),
            "nombre": nombre_categoria,
            "icono": categoria.get("icono", "📦"),
            "color": categoria.get("color") or color_base,
            "subcategorias": list(categoria.get("subcategorias", ["general"])) or ["general"],
            "unidades": unidades,
            "campos": _normalizar_campos_categoria(categoria.get("campos", [])),
            "catalogos": _normalizar_catalogos_categoria(categoria.get("catalogos", {})),
            "posicion": int(categoria.get("posicion", len(normalizadas))),
            "fecha_registro": categoria.get("fecha_registro") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        normalizadas.append(item)

    if not normalizadas:
        normalizadas = _categorias_base()
        cambiado = True

    existentes = {_normalizar(x["nombre"]): x for x in normalizadas}
    for nombre_n, categoria_base in base_por_nombre.items():
        if nombre_n not in existentes:
            normalizadas.append(categoria_base)
            cambiado = True

    normalizadas = sorted(normalizadas, key=lambda x: (int(x.get("posicion", 0)), x.get("nombre", "")))
    for idx, categoria in enumerate(normalizadas):
        if categoria.get("posicion") != idx:
            categoria["posicion"] = idx
            cambiado = True

    if cambiado:
        guardar_seccion(SECCION_CATEGORIAS, normalizadas)

    return normalizadas


def _cargar_categorias() -> List[Dict]:
    return _normalizar_categorias(obtener_seccion(SECCION_CATEGORIAS, []))


def _guardar_categorias(categorias: List[Dict]) -> None:
    guardar_seccion(SECCION_CATEGORIAS, categorias)


def _normalizar_items(raw_items, categorias: List[Dict]) -> List[Dict]:
    if not isinstance(raw_items, list):
        return []

    categorias_por_nombre = {_normalizar(x["nombre"]): x for x in categorias}
    items = []
    cambiado = False

    for item in raw_items:
        if not isinstance(item, dict):
            cambiado = True
            continue

        categoria_nombre = item.get("categoria", "").strip()
        categoria = categorias_por_nombre.get(_normalizar(categoria_nombre))
        if not categoria:
            categoria = categorias[0]
            categoria_nombre = categoria["nombre"]
            cambiado = True

        nutrimental = item.get("nutrimental", {})
        if not isinstance(nutrimental, dict):
            nutrimental = {}
            cambiado = True

        normalizado = {
            "id": item.get("id") or _ahora_id("INV"),
            "categoria_id": item.get("categoria_id") or categoria["id"],
            "categoria": categoria_nombre or categoria["nombre"],
            "subcategoria": item.get("subcategoria", "general").strip() or "general",
            "tipo": item.get("tipo", "").strip(),
            "nombre": item.get("nombre", "").strip(),
            "codigo_barras": item.get("codigo_barras", "").strip(),
            "cantidad": item.get("cantidad", ""),
            "unidad": item.get("unidad", "").strip(),
            "minimo": item.get("minimo", ""),
            "peso_contenido": item.get("peso_contenido", item.get("peso", "")),
            "fecha_ingreso": item.get("fecha_ingreso", "").strip(),
            "fecha_produccion_compra": item.get("fecha_produccion_compra", "").strip(),
            "caducidad": item.get("caducidad", "").strip(),
            "lote": item.get("lote", "").strip(),
            "nutrimentales": item.get("nutrimentales", item.get("datos_nutrimentales", "")).strip(),
            "observaciones": item.get("observaciones", "").strip(),
            "origen": item.get("origen", "manual").strip() or "manual",
            "foto": item.get("foto", "").strip(),
            "composicion": item.get("composicion", "").strip(),
            "proposito": item.get("proposito", "").strip(),
            "marcado_consumo": bool(item.get("marcado_consumo", False)),
            "campos_extra": item.get("campos_extra", {}) if isinstance(item.get("campos_extra", {}), dict) else {},
            "nutrimental": {
                "porcion": nutrimental.get("porcion", ""),
                "calorias": nutrimental.get("calorias", ""),
                "proteinas": nutrimental.get("proteinas", ""),
                "carbohidratos": nutrimental.get("carbohidratos", ""),
                "grasas": nutrimental.get("grasas", ""),
                "fibra": nutrimental.get("fibra", ""),
            },
            "fecha_registro": item.get("fecha_registro") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        items.append(normalizado)

    if cambiado:
        guardar_seccion(SECCION_ITEMS, items)

    return items


def _cargar_items() -> List[Dict]:
    categorias = _cargar_categorias()
    return _normalizar_items(obtener_seccion(SECCION_ITEMS, []), categorias)


def _guardar_items(items: List[Dict]) -> None:
    guardar_seccion(SECCION_ITEMS, items)


def _buscar_categoria_por_nombre(nombre: str) -> Optional[Dict]:
    nombre_n = _normalizar(nombre)
    for categoria in _cargar_categorias():
        if _normalizar(categoria["nombre"]) == nombre_n:
            return categoria
    return None


def _buscar_categoria_por_id(categoria_id: str) -> Optional[Dict]:
    for categoria in _cargar_categorias():
        if categoria.get("id") == categoria_id:
            return categoria
    return None


def _evaluar_caducidad(fecha_texto: str) -> Tuple[str, Optional[int]]:
    try:
        fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
    except ValueError:
        return "desconocido", None

    dias = (fecha - datetime.now().date()).days
    if dias < 0:
        return "vencido", dias
    if dias in (10, 5, 1):
        return "aviso", dias
    if dias == 0:
        return "hoy", dias
    if dias < 0:
        return "vencido", dias
    if dias < 10:
        return "proximo", dias
    return "ok", dias


def _formatear_tabla_nutrimental(nutrimental: Dict, fallback: str = "") -> str:
    valores = [
        ("Porcion", nutrimental.get("porcion", "")),
        ("Calorias", nutrimental.get("calorias", "")),
        ("Proteinas", nutrimental.get("proteinas", "")),
        ("Carbohidratos", nutrimental.get("carbohidratos", "")),
        ("Grasas", nutrimental.get("grasas", "")),
        ("Fibra", nutrimental.get("fibra", "")),
    ]

    filas = [f"{etiqueta:<14} | {valor}" for etiqueta, valor in valores if str(valor).strip()]
    if filas:
        encabezado = "TABLA NUTRIMENTAL\n" + "-" * 29
        return "\n".join([encabezado] + filas)

    return fallback.strip()


def listar_categorias_data() -> List[Dict]:
    return deepcopy(_cargar_categorias())


def listar_categorias() -> List[str]:
    return [x["nombre"] for x in _cargar_categorias()]


def agregar_categoria(nombre: str, icono: str = "📦", color: str = "#13223f", campos: Optional[List[Dict]] = None) -> Dict:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la categoría no puede estar vacío.")
    if _buscar_categoria_por_nombre(nombre):
        raise ValueError("Esa categoría ya existe.")

    categorias = _cargar_categorias()
    nueva = _categoria_default(nombre, icono or "📦", ["general"], ["pieza", "pzas", "kg", "g", "l", "ml"])
    nueva["color"] = color or "#13223f"
    nueva["campos"] = _normalizar_campos_categoria(campos or [])
    nueva["posicion"] = len(categorias)
    categorias.append(nueva)
    _guardar_categorias(categorias)
    registrar_log("sistema", f"Categoría de inventario agregada: {nombre}", "inventario")
    return nueva


def editar_categoria(
    nombre_actual: str,
    nuevo_nombre: str,
    icono: Optional[str] = None,
    color: Optional[str] = None,
    campos: Optional[List[Dict]] = None,
    subcategorias: Optional[List[str]] = None,
    unidades: Optional[List[str]] = None,
    catalogos: Optional[Dict[str, List[str]]] = None,
) -> Dict:
    nombre_actual = nombre_actual.strip()
    nuevo_nombre = nuevo_nombre.strip()

    if not nombre_actual or not nuevo_nombre:
        raise ValueError("Los nombres de categoría no pueden estar vacíos.")

    categorias = _cargar_categorias()
    actual = next((x for x in categorias if _normalizar(x["nombre"]) == _normalizar(nombre_actual)), None)
    if not actual:
        raise ValueError("La categoría que quieres editar no existe.")

    if _normalizar(nombre_actual) != _normalizar(nuevo_nombre) and _buscar_categoria_por_nombre(nuevo_nombre):
        raise ValueError("Ya existe otra categoría con ese nombre.")

    actual["nombre"] = nuevo_nombre
    if icono is not None:
        actual["icono"] = icono or "📦"
    if color is not None:
        actual["color"] = color or "#13223f"
    if campos is not None:
        actual["campos"] = _normalizar_campos_categoria(campos)
    if subcategorias is not None:
        normalizadas = []
        vistos = set()
        for subcategoria in subcategorias:
            valor = _normalizar_texto_valor(subcategoria)
            if not valor:
                continue
            clave = _normalizar(valor)
            if clave in vistos:
                continue
            vistos.add(clave)
            normalizadas.append(valor)
        actual["subcategorias"] = normalizadas or ["general"]
    if unidades is not None:
        normalizadas = []
        vistos = set()
        for unidad in unidades:
            valor = _normalizar_texto_valor(unidad)
            if not valor:
                continue
            clave = _normalizar(valor)
            if clave in vistos:
                continue
            vistos.add(clave)
            normalizadas.append(valor)
        actual["unidades"] = normalizadas or ["pieza"]
    if catalogos is not None:
        actual["catalogos"] = _normalizar_catalogos_categoria(catalogos)
    _guardar_categorias(categorias)

    items = _cargar_items()
    for item in items:
        if item.get("categoria_id") == actual["id"]:
            item["categoria"] = nuevo_nombre
    _guardar_items(items)

    registrar_log("sistema", f"Categoría de inventario editada: {nombre_actual} -> {nuevo_nombre}", "inventario")
    return deepcopy(actual)


def eliminar_categoria(nombre: str) -> bool:
    nombre = nombre.strip()
    categorias = _cargar_categorias()
    if len(categorias) <= 1:
        raise ValueError("Debe existir al menos una categoría.")

    categoria = next((x for x in categorias if _normalizar(x["nombre"]) == _normalizar(nombre)), None)
    if not categoria:
        raise ValueError("La categoría no existe.")

    categorias = [x for x in categorias if x.get("id") != categoria["id"]]
    for idx, item in enumerate(categorias):
        item["posicion"] = idx
    _guardar_categorias(categorias)

    items = [x for x in _cargar_items() if x.get("categoria_id") != categoria["id"]]
    _guardar_items(items)

    registrar_log("sistema", f"Categoría de inventario eliminada: {nombre}", "inventario")
    return True


def obtener_categoria(categoria_id: str) -> Optional[Dict]:
    return deepcopy(_buscar_categoria_por_id(categoria_id))


def reordenar_categorias(categoria_id_origen: str, categoria_id_destino: str) -> List[Dict]:
    categorias = _cargar_categorias()
    ids = [x.get("id") for x in categorias]
    if categoria_id_origen not in ids or categoria_id_destino not in ids or categoria_id_origen == categoria_id_destino:
        return deepcopy(categorias)

    ids.insert(ids.index(categoria_id_destino), ids.pop(ids.index(categoria_id_origen)))
    categorias_por_id = {x["id"]: x for x in categorias}
    reordenadas = []
    for idx, categoria_id in enumerate(ids):
        categoria = categorias_por_id[categoria_id]
        categoria["posicion"] = idx
        reordenadas.append(categoria)
    _guardar_categorias(reordenadas)
    registrar_log("sistema", "Categorías de inventario reordenadas.", "inventario")
    return deepcopy(reordenadas)


def listar_subcategorias(categoria_ref: str) -> List[str]:
    categoria = _buscar_categoria_por_id(categoria_ref) or _buscar_categoria_por_nombre(categoria_ref)
    if not categoria:
        return ["general"]
    return list(categoria.get("subcategorias", ["general"])) or ["general"]


def listar_unidades(categoria_ref: str) -> List[str]:
    categoria = _buscar_categoria_por_id(categoria_ref) or _buscar_categoria_por_nombre(categoria_ref)
    if not categoria:
        return ["pieza", "pzas"]
    return list(categoria.get("unidades", ["pieza", "pzas"])) or ["pieza", "pzas"]


def _normalizar_item_entrada(categoria: Dict, datos: Dict) -> Dict:
    nombre = _normalizar_texto_valor(datos.get("nombre", ""))
    if not nombre:
        raise ValueError("El campo alimento es obligatorio.")

    cantidad = _normalizar_texto_valor(datos.get("cantidad", ""))
    if not cantidad:
        raise ValueError("El campo cantidad es obligatorio.")
    if _es_categoria_combate(categoria) or _es_categoria_herramientas(categoria):
        cantidad_num, _ = _parsear_magnitud(cantidad)
        if cantidad_num is None:
            raise ValueError("La cantidad debe comenzar con un número válido, por ejemplo: 22 cajas.")
        if cantidad_num < 0:
            raise ValueError("La cantidad no puede ser negativa.")
    elif _es_categoria_plantas(categoria):
        cantidad_num = _to_float(cantidad)
        if cantidad_num is not None:
            if cantidad_num < 0:
                raise ValueError("La cantidad no puede ser negativa.")
        else:
            cantidad_num = None
    else:
        cantidad_num = _to_float(cantidad)
        if cantidad_num is None:
            raise ValueError("El campo cantidad debe ser numérico.")
        if cantidad_num < 0:
            raise ValueError("La cantidad no puede ser negativa.")

    unidad = _normalizar_texto_valor(datos.get("unidad", ""))
    if not unidad:
        raise ValueError("Debes seleccionar una unidad.")
    if _es_categoria_alimentos(categoria) and not _es_unidad_inventario_alimentos_valida(unidad):
        raise ValueError("La unidad de alimentos debe ser de inventario: Piezas, Bolsas, Cajas, Botellas, Latas o Paquetes.")

    codigo_barras = _normalizar_texto_valor(datos.get("codigo_barras", ""))

    minimo = _normalizar_texto_valor(datos.get("minimo", ""))
    if not minimo:
        raise ValueError("El campo mínimo es obligatorio.")
    minimo_num = _to_float(minimo)
    if minimo_num is None:
        raise ValueError("La cantidad mínima debe ser un número válido.")
    if minimo_num < 0:
        raise ValueError("La cantidad mínima no puede ser negativa.")

    subcategoria = _normalizar_texto_valor(datos.get("subcategoria", "general")) or "general"
    tipo = _normalizar_texto_valor(datos.get("tipo", "")) or subcategoria
    es_medicamento = _es_categoria_insumos_medicos(categoria) and _normalizar(tipo) == "medicamento"

    peso_contenido = _normalizar_texto_valor(datos.get("peso_contenido", datos.get("peso", "")))
    if _es_categoria_alimentos(categoria) and not peso_contenido:
        raise ValueError("El contenido por unidad es obligatorio.")
    if peso_contenido:
        if _es_categoria_alimentos(categoria):
            peso_num, unidad_contenido = _parsear_magnitud(peso_contenido)
            if peso_num is None:
                raise ValueError("El contenido por unidad debe incluir un número válido.")
            if peso_num < 0:
                raise ValueError("El contenido por unidad no puede ser negativo.")
            if not unidad_contenido or _normalizar(unidad_contenido) not in UNIDADES_CONTENIDO:
                raise ValueError("El contenido por unidad debe usar una medida válida: mg, gr, kg, ml o l.")
            peso_contenido = f"{_formatear_numero(peso_num)} {unidad_contenido}"
        elif (
            _es_categoria_animales(categoria)
            or _es_categoria_plantas(categoria)
            or _es_categoria_comunicacion(categoria)
            or _es_categoria_energia(categoria)
            or _es_categoria_higiene(categoria)
            or _es_categoria_movilidad(categoria)
            or _es_categoria_cocina_preparacion(categoria)
            or _es_categoria_ropa(categoria)
        ):
            peso_contenido = _normalizar_texto_valor(peso_contenido)
        else:
            peso_num = _to_float(peso_contenido)
            if peso_num is None and not es_medicamento:
                raise ValueError("El contenido por unidad debe ser numérico.")
            if peso_num is not None and peso_num < 0:
                raise ValueError("El contenido por unidad no puede ser negativo.")

    nutrimental_raw = deepcopy(datos.get("nutrimental", {}))
    nutrimentales = _normalizar_texto_valor(datos.get("nutrimentales", datos.get("datos_nutrimentales", "")))
    nutrimental = {}
    campos_extra_raw = datos.get("campos_extra", {})
    if not isinstance(campos_extra_raw, dict):
        campos_extra_raw = {}
    campos_extra = {}
    for campo in categoria.get("campos", []):
        campo_id = campo.get("id", "")
        if not campo_id:
            continue
        campos_extra[campo_id] = _normalizar_texto_valor(campos_extra_raw.get(campo_id, ""))
    capturo_nutrimental = False
    for clave, etiqueta in [
        ("porcion", "porción"),
        ("calorias", "calorías"),
        ("proteinas", "proteínas"),
        ("carbohidratos", "carbohidratos"),
        ("grasas", "grasas"),
        ("fibra", "fibra"),
    ]:
        valor = _normalizar_texto_valor(nutrimental_raw.get(clave, ""))
        if not valor:
            nutrimental[clave] = ""
            continue
        capturo_nutrimental = True
        numero = _to_float(valor)
        if numero is None:
            raise ValueError(f"El campo {etiqueta} debe ser numérico.")
        if clave == "porcion":
            if numero <= 0:
                raise ValueError("La porción no puede ser cero.")
        elif numero < 0:
            raise ValueError(f"El campo {etiqueta} no puede ser negativo.")
        nutrimental[clave] = _formatear_numero(numero)

    if capturo_nutrimental and not nutrimental.get("porcion"):
        raise ValueError("La porción es obligatoria cuando capturas información nutrimental.")
    if nutrimental and not nutrimentales:
        nutrimentales = _formatear_tabla_nutrimental(nutrimental)

    return {
        "id": datos.get("id") or _ahora_id("INV"),
        "categoria_id": categoria["id"],
        "categoria": categoria["nombre"],
        "subcategoria": subcategoria,
        "tipo": tipo,
        "nombre": nombre,
        "codigo_barras": codigo_barras,
        "cantidad": (
            cantidad
            if (_es_categoria_combate(categoria) or _es_categoria_herramientas(categoria) or (_es_categoria_plantas(categoria) and cantidad_num is None))
            else _formatear_numero(cantidad_num)
        ),
        "unidad": unidad,
        "minimo": _formatear_numero(minimo_num),
        "peso_contenido": _formatear_numero(_to_float(peso_contenido)) if peso_contenido and _to_float(peso_contenido) is not None else peso_contenido,
        "fecha_ingreso": _normalizar_texto_valor(datos.get("fecha_ingreso", "")),
        "fecha_produccion_compra": _normalizar_texto_valor(datos.get("fecha_produccion_compra", "")),
        "caducidad": _normalizar_texto_valor(datos.get("caducidad", "")),
        "lote": _normalizar_texto_valor(datos.get("lote", "")),
        "nutrimentales": nutrimentales,
        "observaciones": _normalizar_texto_valor(datos.get("observaciones", "")),
        "origen": _normalizar_texto_valor(datos.get("origen", "manual")) or "manual",
        "foto": _normalizar_texto_valor(datos.get("foto", "")),
        "composicion": _normalizar_texto_valor(datos.get("composicion", "")),
        "proposito": _normalizar_texto_valor(datos.get("proposito", "")),
        "marcado_consumo": bool(datos.get("marcado_consumo", False)),
        "campos_extra": campos_extra,
        "nutrimental": nutrimental,
        "fecha_registro": datos.get("fecha_registro") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def listar_items(categoria_ref: Optional[str] = None) -> List[Dict]:
    items = _cargar_items()
    if not categoria_ref:
        return deepcopy(items)

    categoria = _buscar_categoria_por_id(categoria_ref) or _buscar_categoria_por_nombre(categoria_ref)
    if not categoria:
        return []

    filtrados = [x for x in items if x.get("categoria_id") == categoria["id"]]
    return deepcopy(filtrados)


def _clave_duplicado_item(item: Dict) -> Tuple[str, str, str, str]:
    return (
        _normalizar(item.get("tipo", item.get("subcategoria", ""))),
        _normalizar(item.get("nombre", "")),
        _normalizar(item.get("unidad", "")),
        _normalizar(item.get("peso_contenido", "")),
    )


def agregar_item(
    categoria_id: str,
    subcategoria: str = "general",
    nombre: str = "",
    codigo_barras: str = "",
    cantidad: str = "",
    unidad: str = "",
    peso_contenido: str = "",
    fecha_ingreso: str = "",
    fecha_produccion_compra: str = "",
    caducidad: str = "",
    lote: str = "",
    observaciones: str = "",
    foto: str = "",
    nutrimentales: str = "",
    minimo: str = "",
    tipo: str = "",
    composicion: str = "",
    proposito: str = "",
    origen: str = "manual",
    nutrimental: Optional[Dict] = None,
    campos_extra: Optional[Dict] = None,
) -> Dict:
    categoria = _buscar_categoria_por_id(categoria_id)
    if not categoria:
        raise ValueError("La categoría no existe.")

    item = _normalizar_item_entrada(
        categoria,
        {
            "subcategoria": subcategoria,
            "nombre": nombre,
            "codigo_barras": codigo_barras,
            "cantidad": cantidad,
            "unidad": unidad,
            "peso_contenido": peso_contenido,
            "fecha_ingreso": fecha_ingreso,
            "fecha_produccion_compra": fecha_produccion_compra,
            "caducidad": caducidad,
            "lote": lote,
            "observaciones": observaciones,
            "foto": foto,
            "nutrimentales": nutrimentales,
            "minimo": minimo,
            "tipo": tipo,
            "composicion": composicion,
            "proposito": proposito,
            "origen": origen,
            "nutrimental": nutrimental or {},
            "campos_extra": campos_extra or {},
        },
    )

    items = _cargar_items()
    if any(x.get("categoria_id") == categoria_id and _clave_duplicado_item(x) == _clave_duplicado_item(item) for x in items):
        raise ValueError("Ya existe un item con el mismo nombre, unidad y presentación en esta categoría.")
    if item.get("codigo_barras") and any(
        x.get("categoria_id") == categoria_id and _normalizar(x.get("codigo_barras", "")) == _normalizar(item["codigo_barras"])
        for x in items
    ):
        raise ValueError("Ya existe un item con ese código de barras en esta categoría.")

    items.append(item)
    _guardar_items(items)
    if item.get("codigo_barras"):
        try:
            from core.codigos import sincronizar_codigo_con_item

            sincronizar_codigo_con_item(item)
        except Exception:
            pass
    registrar_log("sistema", f"Item de inventario agregado: {item['nombre']}", "inventario")
    return deepcopy(item)


def actualizar_item(item_id: str, **kwargs) -> bool:
    items = _cargar_items()
    for idx, item in enumerate(items):
        if item.get("id") != item_id:
            continue

        categoria = _buscar_categoria_por_id(kwargs.get("categoria_id", item.get("categoria_id", "")))
        if not categoria:
            raise ValueError("La categoría no existe.")

        nuevos = deepcopy(item)
        nuevos.update(kwargs)
        normalizado = _normalizar_item_entrada(categoria, nuevos)
        normalizado["id"] = item_id

        for otro in items:
            if otro.get("id") == item_id:
                continue
            if otro.get("categoria_id") == categoria["id"] and _clave_duplicado_item(otro) == _clave_duplicado_item(normalizado):
                raise ValueError("Ya existe otro item con el mismo nombre, unidad y presentación en esta categoría.")
            if normalizado.get("codigo_barras") and otro.get("categoria_id") == categoria["id"]:
                if _normalizar(otro.get("codigo_barras", "")) == _normalizar(normalizado["codigo_barras"]):
                    raise ValueError("Ya existe otro item con ese código de barras en esta categoría.")

        items[idx] = normalizado
        _guardar_items(items)
        if normalizado.get("codigo_barras"):
            try:
                from core.codigos import sincronizar_codigo_con_item

                sincronizar_codigo_con_item(normalizado)
            except Exception:
                pass
        registrar_log("sistema", f"Item de inventario actualizado: {normalizado['nombre']}", "inventario")
        return True

    return False


def eliminar_item_por_id(item_id: str) -> bool:
    items = _cargar_items()
    nuevos = [x for x in items if x.get("id") != item_id]
    if len(nuevos) == len(items):
        return False

    _guardar_items(nuevos)
    registrar_log("sistema", f"Item de inventario eliminado: {item_id}", "inventario")
    return True


def marcar_item_consumido(item_id: str) -> bool:
    return eliminar_item_por_id(item_id)


def consumir_item(item_id: str, cantidad_consumida) -> Dict:
    consumo = _to_float(cantidad_consumida)
    if consumo is None or consumo <= 0:
        raise ValueError("La cantidad consumida debe ser mayor a cero.")

    items = _cargar_items()
    for idx, item in enumerate(items):
        if item.get("id") != item_id:
            continue

        cantidad_actual = _to_float(item.get("cantidad"))
        if cantidad_actual is None:
            raise ValueError("Este item no tiene una cantidad numérica válida para descontar.")

        restante = round(cantidad_actual - consumo, 6)
        restante_total = None
        if restante < 0:
            raise ValueError("No puedes consumir más de lo disponible.")

        if restante == 0:
            eliminado = item.get("nombre", item_id)
            items.pop(idx)
            _guardar_items(items)
            registrar_log("sistema", f"Item de inventario consumido por completo: {eliminado}", "inventario")
            return {
                "eliminado": True,
                "cantidad_restante": 0,
                "total_restante": None,
                "unidad_total": None,
                "item": deepcopy(item),
            }

        item["cantidad"] = _formatear_numero(restante)
        items[idx] = item
        _guardar_items(items)
        registrar_log("sistema", f"Consumo registrado en inventario: {item.get('nombre', item_id)} -> {item['cantidad']}", "inventario")
        return {
            "eliminado": False,
            "cantidad_restante": restante,
            "total_restante": restante_total,
            "unidad_total": None,
            "item": deepcopy(item),
        }

    raise ValueError("El item no existe.")


def total_disponible_item(item: Dict) -> str:
    cantidad = _to_float(item.get("cantidad"))
    if cantidad is None:
        return ""

    unidad = str(item.get("unidad", "")).strip()
    peso_unitario, unidad_peso = _parsear_magnitud(item.get("peso_contenido", ""))
    if peso_unitario is not None and unidad_peso:
        total = cantidad * peso_unitario
        return f"{_formatear_numero(total)} {unidad_peso}"

    if unidad:
        return f"{_formatear_numero(cantidad)} {unidad}"
    return _formatear_numero(cantidad)


def buscar_producto_por_nombre(categoria: str, nombre: str):
    productos = listar_items(categoria)
    nombre_n = _normalizar(nombre)
    for idx, item in enumerate(productos):
        if _normalizar(item.get("nombre", "")) == nombre_n:
            return idx, item
    return None


def buscar_item_por_codigo_barras(categoria_ref: str, codigo_barras: str) -> Optional[Dict]:
    codigo_n = _normalizar(codigo_barras)
    if not codigo_n:
        return None
    for item in listar_items(categoria_ref):
        if _normalizar(item.get("codigo_barras", "")) == codigo_n:
            return deepcopy(item)
    return None


def buscar_item_por_codigo_barras_global(codigo_barras: str) -> Optional[Dict]:
    codigo_n = _normalizar(codigo_barras)
    if not codigo_n:
        return None
    for item in listar_items():
        if _normalizar(item.get("codigo_barras", "")) == codigo_n:
            return deepcopy(item)
    return None


def buscar_item_por_id(item_id: str) -> Optional[Dict]:
    item_id = str(item_id or "").strip()
    if not item_id:
        return None
    for item in listar_items():
        if item.get("id") == item_id:
            return deepcopy(item)
    return None


def incrementar_cantidad_item(item_id: str, cantidad_extra, foto: str = "", origen: str = "") -> Dict:
    extra = _to_float(cantidad_extra)
    if extra is None or extra <= 0:
        raise ValueError("La cantidad a agregar debe ser mayor a cero.")

    items = _cargar_items()
    for idx, item in enumerate(items):
        if item.get("id") != item_id:
            continue
        actual = _to_float(item.get("cantidad"))
        if actual is None:
            raise ValueError("El item no tiene una cantidad numérica válida.")
        item["cantidad"] = _formatear_numero(actual + extra)
        if str(foto or "").strip():
            item["foto"] = str(foto).strip()
        if str(origen or "").strip():
            item["origen"] = str(origen).strip()
        items[idx] = item
        _guardar_items(items)
        registrar_log("sistema", f"Inventario incrementado por codigo: {item.get('nombre', item_id)} -> {item['cantidad']}", "inventario")
        return deepcopy(item)
    raise ValueError("El item no existe.")


def listar_inventario() -> List[Dict]:
    return listar_items()


def listar_alertas_inventario(categoria_ref: Optional[str] = None) -> List[Dict]:
    items = listar_items(categoria_ref)
    alertas = []

    for item in items:
        nombre = item.get("nombre", "Sin nombre")
        categoria = item.get("categoria", "")
        categoria_n = _normalizar(categoria)
        if categoria_n in {"combate", "herramientas"}:
            cantidad, _ = _parsear_magnitud(item.get("cantidad"))
        else:
            cantidad = _to_float(item.get("cantidad"))
        minimo = _to_float(item.get("minimo"))
        unidad = item.get("unidad", "")

        if categoria_n == "alimentos" and not _es_unidad_inventario_alimentos_valida(unidad):
            alertas.append(
                {
                    "tipo": "unidad_invalida",
                    "item_id": item["id"],
                    "categoria": categoria,
                    "mensaje": f"{nombre}: unidad de inventario inválida ({unidad}). Corrige a Piezas, Bolsas, Cajas, Botellas, Latas o Paquetes.",
                }
            )

        if minimo is not None and cantidad is not None:
            if cantidad <= minimo:
                alertas.append(
                    {
                        "tipo": "stock_minimo",
                        "item_id": item["id"],
                        "categoria": categoria,
                        "mensaje": f"{nombre}: stock en {_descripcion_stock_item(item, cantidad)}, por debajo o igual al mínimo ({_formatear_numero(minimo)}).",
                    }
                )
            elif cantidad <= (minimo * 1.25):
                alertas.append(
                    {
                        "tipo": "stock_cercano",
                        "item_id": item["id"],
                        "categoria": categoria,
                        "mensaje": f"{nombre}: stock cercano al mínimo ({_descripcion_stock_item(item, cantidad)}).",
                    }
                )

        caducidad = item.get("caducidad", "").strip()
        if caducidad:
            estado, dias = _evaluar_caducidad(caducidad)
            if estado == "vencido":
                alertas.append(
                    {
                        "tipo": "caducado",
                        "item_id": item["id"],
                        "categoria": categoria,
                        "dias": dias,
                        "accion": "consumir",
                        "mensaje": f"{nombre}: caducado desde hace {abs(dias)} día(s).",
                    }
                )
            elif estado == "hoy":
                alertas.append(
                    {
                        "tipo": "caduca_hoy",
                        "item_id": item["id"],
                        "categoria": categoria,
                        "dias": dias,
                        "accion": "consumir",
                        "mensaje": f"{nombre}: caduca hoy.",
                    }
                )
            elif estado in {"aviso", "proximo"} and dias is not None and dias <= 10:
                alertas.append(
                    {
                        "tipo": "caducidad_proxima",
                        "item_id": item["id"],
                        "categoria": categoria,
                        "dias": dias,
                        "accion": "consumir",
                        "mensaje": f"{nombre}: caduca en {dias} día(s).",
                    }
                )

    return alertas


class Inventario:
    def __init__(self):
        _cargar_categorias()
        _cargar_items()

    def listar_categorias(self):
        return listar_categorias()

    def agregar_categoria(self, nombre, icono="📦", color="#13223f", campos=None):
        return agregar_categoria(nombre, icono=icono, color=color, campos=campos)

    def editar_categoria(self, nombre_actual, nuevo_nombre, icono=None, color=None, campos=None):
        return editar_categoria(nombre_actual, nuevo_nombre, icono=icono, color=color, campos=campos)

    def editar_categoria_completa(self, nombre_actual, nuevo_nombre, icono=None, color=None, campos=None, subcategorias=None, unidades=None, catalogos=None):
        return editar_categoria(
            nombre_actual,
            nuevo_nombre,
            icono=icono,
            color=color,
            campos=campos,
            subcategorias=subcategorias,
            unidades=unidades,
            catalogos=catalogos,
        )

    def eliminar_categoria(self, nombre):
        return eliminar_categoria(nombre)

    def reordenar_categorias(self, categoria_id_origen, categoria_id_destino):
        return reordenar_categorias(categoria_id_origen, categoria_id_destino)

    def agregar_producto(self, categoria, producto):
        categoria_data = _buscar_categoria_por_nombre(categoria)
        if not categoria_data:
            raise ValueError("La categoría no existe.")
        return agregar_item(
            categoria_id=categoria_data["id"],
            subcategoria=producto.get("subcategoria", "general"),
            nombre=producto.get("nombre", ""),
            codigo_barras=producto.get("codigo_barras", ""),
            cantidad=producto.get("cantidad", ""),
            unidad=producto.get("unidad", ""),
            peso_contenido=producto.get("peso_contenido", ""),
            fecha_ingreso=producto.get("fecha_ingreso", ""),
            fecha_produccion_compra=producto.get("fecha_produccion_compra", ""),
            caducidad=producto.get("caducidad", ""),
            lote=producto.get("lote", ""),
            observaciones=producto.get("observaciones", ""),
            foto=producto.get("foto", ""),
            nutrimentales=producto.get("nutrimentales", ""),
            minimo=producto.get("minimo", ""),
            tipo=producto.get("tipo", ""),
            composicion=producto.get("composicion", ""),
            proposito=producto.get("proposito", ""),
            origen=producto.get("origen", "manual"),
            nutrimental=producto.get("nutrimental", {}),
            campos_extra=producto.get("campos_extra", {}),
        )

    def actualizar_producto(self, categoria, indice, producto_actualizado):
        productos = self.obtener_productos(categoria)
        if indice < 0 or indice >= len(productos):
            raise ValueError("Producto no válido.")
        item = productos[indice]
        ok = actualizar_item(item["id"], **producto_actualizado)
        if not ok:
            raise ValueError("Producto no válido.")
        return True

    def eliminar_producto(self, categoria, indice):
        productos = self.obtener_productos(categoria)
        if indice < 0 or indice >= len(productos):
            raise ValueError("Producto no válido.")
        eliminar_item_por_id(productos[indice]["id"])

    def obtener_productos(self, categoria):
        return listar_items(categoria)

    def buscar_producto_por_nombre(self, categoria, nombre):
        return buscar_producto_por_nombre(categoria, nombre)

    def buscar_item_por_codigo_barras(self, categoria, codigo_barras):
        return buscar_item_por_codigo_barras(categoria, codigo_barras)

    def buscar_item_por_codigo_barras_global(self, codigo_barras):
        return buscar_item_por_codigo_barras_global(codigo_barras)

    def buscar_item_por_id(self, item_id):
        return buscar_item_por_id(item_id)

    def incrementar_cantidad_item(self, item_id, cantidad_extra, foto="", origen=""):
        return incrementar_cantidad_item(item_id, cantidad_extra, foto=foto, origen=origen)

    def obtener_alertas(self, categoria=None):
        alertas = listar_alertas_inventario(categoria)
        return [x.get("mensaje", "") for x in alertas]
