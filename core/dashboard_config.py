import json
from pathlib import Path
from typing import Dict, Any

from core.memoria import DATA_DIR, APP_DIR


RUTA_CONFIG = DATA_DIR / "memoria" / "dashboard_config.json"
RUTA_CONFIG_LEGACY = APP_DIR / "memoria" / "dashboard_config.json"
COLUMNAS_DASHBOARD = 4


def _modulo_default(mod_id: str, titulo: str, icono: str, color: str) -> Dict[str, str]:
    return {
        "titulo": titulo,
        "icono": icono,
        "color": color,
    }


def _categoria_biblioteca_default(
    nombre: str,
    icono: str = "📚",
    color: str = "#1D4ED8",
    descripcion: str = "",
    posicion: int = 0,
) -> Dict[str, Any]:
    return {
        "id": f"biblioteca_{nombre.strip().lower().replace(' ', '_')}",
        "nombre": nombre,
        "icono": icono,
        "color": color,
        "descripcion": descripcion,
        "posicion": posicion,
    }


def config_default() -> Dict[str, Any]:
    return {
        "tema": {
            "fondo": "#0F172A",
            "modulo": "#1E293B",
            "texto": "#FFFFFF",
            "panel_guerra": "#5C005C",
            "panel_hora": "#EAB308"
        },
        "external_urls": {
            "world_monitor": "https://www.worldmonitor.app/?lat=20.0000&lon=0.0000&zoom=1.00&view=global&timeRange=7d&layers=conflicts%2Cbases%2Chotspots%2Cnuclear%2Csanctions%2Cweather%2Ceconomic%2Cwaterways%2Coutages%2Cmilitary%2Cnatural%2CiranAttacks"
        },
        "modulos": [
            {"id": "consulta", "orden": 0},
            {"id": "mapa", "orden": 1},
            {"id": "inventario", "orden": 2},
            {"id": "planes_emergencia", "orden": 3},
            {"id": "biblioteca", "orden": 4},
            {"id": "aprendizaje", "orden": 5},
            {"id": "codigos", "orden": 6},
            {"id": "perfiles", "orden": 7},
            {"id": "herramientas", "orden": 8},
            {"id": "juegos", "orden": 9},
            {"id": "world_monitor", "orden": 10},
        ],
        "custom_modulos": {
            "consulta": _modulo_default("consulta", "Consulta", "🧠", "#1E293B"),
            "mapa": _modulo_default("mapa", "Mapa", "🗺", "#1E293B"),
            "inventario": _modulo_default("inventario", "Inventario", "📦", "#1E293B"),
            "planes_emergencia": _modulo_default("planes_emergencia", "Planes de emergencia", "📋", "#0F766E"),
            "biblioteca": _modulo_default("biblioteca", "Biblioteca", "📚", "#1E293B"),
            "aprendizaje": _modulo_default("aprendizaje", "Aprendizaje", "🎓", "#1E293B"),
            "codigos": _modulo_default("codigos", "Codigos", "🏷", "#B45309"),
            "perfiles": _modulo_default("perfiles", "Perfiles", "👤", "#1E293B"),
            "herramientas": _modulo_default("herramientas", "Herramientas", "🛠", "#1E293B"),
            "juegos": _modulo_default("juegos", "Juegos", "🎮", "#7C3AED"),
            "world_monitor": _modulo_default("world_monitor", "World Monitor", "🌍", "#0F766E"),
        },
        "biblioteca_categorias": [
            _categoria_biblioteca_default("Medicina", "🩺", "#B91C1C", "Guías, manuales y referencias médicas.", 0),
            _categoria_biblioteca_default("Reparación", "🔧", "#0F766E", "Mantenimiento, reparación y diagnóstico.", 1),
            _categoria_biblioteca_default("Autosuficiencia", "🌱", "#4D7C0F", "Huerto, agua, conservación y supervivencia.", 2),
            _categoria_biblioteca_default("Construcción", "🏗️", "#B45309", "Obra, estructuras y sistemas.", 3),
        ],
    }


def _ordenar_por_posicion(items, clave="orden"):
    return sorted(items, key=lambda item: (int(item.get(clave, 0)), str(item.get("id", ""))))


def _normalizar_modulos(cfg: Dict[str, Any], base: Dict[str, Any]) -> None:
    existentes = []
    vistos = set()

    for indice, mod in enumerate(cfg.get("modulos", [])):
        if not isinstance(mod, dict):
            continue
        mod_id = (mod.get("id") or "").strip()
        if not mod_id or mod_id in vistos or mod_id in {"camara", "chat"}:
            continue
        vistos.add(mod_id)
        orden = mod.get("orden")
        if orden is None:
            fila = int(mod.get("fila", 0))
            col = int(mod.get("col", 0))
            orden = fila * COLUMNAS_DASHBOARD + col
        existentes.append({"id": mod_id, "orden": int(orden)})

    orden_actual = len(existentes)
    for mod in base["modulos"]:
        if mod["id"] not in vistos:
            existentes.append({"id": mod["id"], "orden": orden_actual})
            vistos.add(mod["id"])
            orden_actual += 1

    cfg["modulos"] = _ordenar_por_posicion(existentes, "orden")


def _normalizar_custom_modulos(cfg: Dict[str, Any], base: Dict[str, Any]) -> None:
    cfg.setdefault("custom_modulos", {})
    cfg["custom_modulos"].pop("camara", None)
    cfg["custom_modulos"].pop("chat", None)
    for mid, datos in base["custom_modulos"].items():
        actual = cfg["custom_modulos"].setdefault(mid, {})
        actual.setdefault("titulo", datos["titulo"])
        actual.setdefault("icono", datos["icono"])
        actual.setdefault("color", datos["color"])


def _normalizar_biblioteca(cfg: Dict[str, Any], base: Dict[str, Any]) -> None:
    categorias = []
    for indice, categoria in enumerate(cfg.get("biblioteca_categorias", [])):
        if not isinstance(categoria, dict):
            continue
        nombre = (categoria.get("nombre") or "").strip()
        if not nombre:
            continue
        categorias.append(
            {
                "id": categoria.get("id") or f"biblioteca_{indice}",
                "nombre": nombre,
                "icono": categoria.get("icono", "📚"),
                "color": categoria.get("color", "#1D4ED8"),
                "descripcion": categoria.get("descripcion", "").strip(),
                "posicion": int(categoria.get("posicion", indice)),
            }
        )

    if not categorias:
        categorias = base["biblioteca_categorias"]

    cfg["biblioteca_categorias"] = _ordenar_por_posicion(categorias, "posicion")


def cargar_config() -> Dict[str, Any]:
    if not RUTA_CONFIG.exists():
        if RUTA_CONFIG_LEGACY.exists():
            RUTA_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            RUTA_CONFIG.write_text(RUTA_CONFIG_LEGACY.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            cfg = config_default()
            guardar_config(cfg)
            return cfg

    if not RUTA_CONFIG.exists():
        cfg = config_default()
        guardar_config(cfg)
        return cfg

    with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    base = config_default()

    if "tema" not in cfg or not isinstance(cfg["tema"], dict):
        cfg["tema"] = base["tema"]
    if "external_urls" not in cfg or not isinstance(cfg["external_urls"], dict):
        cfg["external_urls"] = {}
    for key, value in base.get("external_urls", {}).items():
        cfg["external_urls"].setdefault(key, value)

    _normalizar_modulos(cfg, base)
    _normalizar_custom_modulos(cfg, base)
    _normalizar_biblioteca(cfg, base)

    guardar_config(cfg)
    return cfg


def guardar_config(cfg: Dict[str, Any]) -> None:
    RUTA_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def siguiente_posicion_modulo(cfg: Dict[str, Any]) -> Dict[str, int]:
    ordenes = [int(m.get("orden", idx)) for idx, m in enumerate(cfg.get("modulos", []))]
    siguiente = max(ordenes, default=-1) + 1
    return {"fila": siguiente // COLUMNAS_DASHBOARD, "col": siguiente % COLUMNAS_DASHBOARD, "orden": siguiente}


def obtener_modulos_ordenados(cfg: Dict[str, Any]):
    return _ordenar_por_posicion(cfg.get("modulos", []), "orden")


def reordenar_modulos(cfg: Dict[str, Any], modulo_id_origen: str, modulo_id_destino: str) -> Dict[str, Any]:
    modulos = obtener_modulos_ordenados(cfg)
    ids = [m["id"] for m in modulos]
    if modulo_id_origen not in ids or modulo_id_destino not in ids or modulo_id_origen == modulo_id_destino:
        return cfg
    ids.insert(ids.index(modulo_id_destino), ids.pop(ids.index(modulo_id_origen)))
    cfg["modulos"] = [{"id": mod_id, "orden": idx} for idx, mod_id in enumerate(ids)]
    guardar_config(cfg)
    return cfg


def obtener_biblioteca_categorias(cfg: Dict[str, Any]):
    return _ordenar_por_posicion(cfg.get("biblioteca_categorias", []), "posicion")


def guardar_biblioteca_categorias(cfg: Dict[str, Any], categorias) -> Dict[str, Any]:
    cfg["biblioteca_categorias"] = [
        {
            "id": categoria.get("id") or f"biblioteca_{idx}",
            "nombre": categoria.get("nombre", "").strip() or f"Categoría {idx + 1}",
            "icono": categoria.get("icono", "📚"),
            "color": categoria.get("color", "#1D4ED8"),
            "descripcion": categoria.get("descripcion", "").strip(),
            "posicion": idx,
        }
        for idx, categoria in enumerate(categorias)
    ]
    guardar_config(cfg)
    return cfg
