import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from core.biblioteca import actualizar_libro, listar_libros
from core.indice_consulta import RUTA_DB_CONSULTA
from core.logs import registrar_log
from core.memoria import guardar_seccion, obtener_seccion
from core.texto import normalizar_texto


def _normalizar(nombre: str) -> str:
    return normalizar_texto(nombre or "")


def _etiqueta(nombre: str) -> str:
    limpio = (nombre or "").strip().replace("_", " ")
    return " ".join(parte.capitalize() for parte in limpio.split()) or "General"


def listar_dominios(include_general: bool = True) -> List[Dict]:
    dominios = obtener_seccion("dominios", [])
    resultado = []

    if include_general:
        resultado.append({
            "id": "DOM-general",
            "nombre": "general",
            "descripcion": "Dominio general",
            "subdominios": ["general"],
        })

    for dominio in dominios:
        nombre = _normalizar(dominio.get("nombre", ""))
        if not nombre or (include_general and nombre == "general"):
            continue
        resultado.append({
            "id": dominio.get("id", f"DOM-{nombre}"),
            "nombre": nombre,
            "descripcion": str(dominio.get("descripcion", "")).strip(),
            "subdominios": [
                _normalizar(subdominio)
                for subdominio in dominio.get("subdominios", [])
                if _normalizar(subdominio)
            ],
        })

    return sorted(resultado, key=lambda item: (item.get("nombre") != "general", item.get("nombre", "")))


def listar_dominios_ui(include_general: bool = True) -> List[Dict]:
    return [
        {
            **dominio,
            "etiqueta": _etiqueta(dominio.get("nombre", "")),
        }
        for dominio in listar_dominios(include_general=include_general)
    ]


def agregar_dominio(nombre: str, descripcion: str = "", subdominios: Optional[List[str]] = None) -> Dict:
    nombre_n = _normalizar(nombre)
    if not nombre_n:
        return {"ok": False, "mensaje": "Escribe un nombre de dominio válido."}

    if nombre_n == "general":
        return {"ok": False, "mensaje": "El dominio general ya existe y no se puede duplicar."}

    dominios = obtener_seccion("dominios", [])
    if any(_normalizar(item.get("nombre", "")) == nombre_n for item in dominios):
        return {"ok": False, "mensaje": "Ese dominio ya existe."}

    registro = {
        "id": f"DOM-{nombre_n}",
        "nombre": nombre_n,
        "descripcion": str(descripcion or "").strip() or f"Dominio {nombre_n}",
        "subdominios": [
            _normalizar(subdominio)
            for subdominio in (subdominios or [])
            if _normalizar(subdominio)
        ] or ["general"],
    }
    dominios.append(registro)
    guardar_seccion("dominios", dominios)
    registrar_log("sistema", f"Dominio agregado: {nombre_n}", "dominios")
    return {"ok": True, "mensaje": f"Dominio agregado: {nombre_n}", "dominio": registro}


def _actualizar_cache_libros_dominio(nombre_actual: str, nuevo_nombre: str) -> None:
    for libro in listar_libros():
        if _normalizar(libro.get("dominio", "")) != nombre_actual:
            continue
        ruta_cache = Path(libro.get("cache_json", ""))
        if not ruta_cache.exists():
            continue
        try:
            payload = json.loads(ruta_cache.read_text(encoding="utf-8"))
        except Exception:
            continue
        payload["dominio"] = nuevo_nombre
        try:
            ruta_cache.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


def _actualizar_indice_consulta_dominio(nombre_actual: str, nuevo_nombre: str) -> None:
    if not RUTA_DB_CONSULTA.exists():
        return
    with sqlite3.connect(RUTA_DB_CONSULTA) as conn:
        conn.execute("UPDATE fragmentos SET dominio = ? WHERE dominio = ?", (nuevo_nombre, nombre_actual))
        conn.commit()


def corregir_nombre_dominio(nombre_actual: str, nuevo_nombre: str) -> Dict:
    actual_n = _normalizar(nombre_actual)
    nuevo_n = _normalizar(nuevo_nombre)

    if not actual_n or not nuevo_n:
        return {"ok": False, "mensaje": "Debes indicar el dominio actual y el nuevo nombre."}
    if actual_n == "general":
        return {"ok": False, "mensaje": "El dominio general no se puede editar."}
    if nuevo_n == "general":
        return {"ok": False, "mensaje": "No se puede renombrar un dominio a general."}

    dominios = obtener_seccion("dominios", [])
    objetivo = None
    for dominio in dominios:
        if _normalizar(dominio.get("nombre", "")) == actual_n:
            objetivo = dominio
            break

    if objetivo is None:
        return {"ok": False, "mensaje": "No se encontró el dominio indicado."}

    if any(_normalizar(item.get("nombre", "")) == nuevo_n and item is not objetivo for item in dominios):
        return {"ok": False, "mensaje": "Ya existe otro dominio con ese nombre."}

    objetivo["nombre"] = nuevo_n
    guardar_seccion("dominios", dominios)

    for libro in listar_libros():
        if _normalizar(libro.get("dominio", "")) == actual_n:
            actualizar_libro(libro["id"], {"dominio": nuevo_n})

    _actualizar_cache_libros_dominio(actual_n, nuevo_n)
    _actualizar_indice_consulta_dominio(actual_n, nuevo_n)
    registrar_log("sistema", f"Dominio corregido: {actual_n} -> {nuevo_n}", "dominios")
    return {"ok": True, "mensaje": f"Dominio actualizado: {actual_n} -> {nuevo_n}", "dominio": objetivo}
