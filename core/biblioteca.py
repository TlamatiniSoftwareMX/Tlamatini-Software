import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.logs import registrar_log, registrar_log_admin
from core.memoria import (
    RUTA_CACHE_LIBROS,
    obtener_seccion,
    guardar_seccion,
    eliminar_elemento
)
from core.admin_papelera import enviar_a_papelera
from core.texto import normalizar_texto


EXTENSIONES_VALIDAS = {".pdf", ".txt", ".md"}


def calcular_hash_archivo(ruta_archivo: str) -> str:
    ruta = Path(ruta_archivo)
    md5 = hashlib.md5()

    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(65536), b""):
            md5.update(bloque)

    return md5.hexdigest()


def ruta_cache_por_hash(hash_archivo: str) -> Path:
    return RUTA_CACHE_LIBROS / f"{hash_archivo}.json"


def listar_libros(dominio: str = "", subdominio: str = "", categoria_id: str = "") -> List[Dict]:
    libros = obtener_seccion("biblioteca", [])
    resultado = []

    for libro in libros:
        if libro.get("estado", "activo") != "activo":
            continue
        if categoria_id and libro.get("categoria_id", "") != categoria_id:
            continue
        if dominio and normalizar_texto(libro.get("dominio", "")) != normalizar_texto(dominio):
            continue
        if subdominio and normalizar_texto(libro.get("subdominio", "")) != normalizar_texto(subdominio):
            continue
        resultado.append(libro)

    return resultado


def obtener_libro_por_hash(hash_archivo: str) -> Optional[Dict]:
    libros = obtener_seccion("biblioteca", [])
    for libro in libros:
        if libro.get("hash_archivo") == hash_archivo:
            return libro
    return None


def obtener_libro_por_id(libro_id: str) -> Optional[Dict]:
    libros = obtener_seccion("biblioteca", [])
    for libro in libros:
        if libro.get("id") == libro_id:
            return libro
    return None


def guardar_cache_libro(hash_archivo: str, payload: Dict) -> Path:
    ruta_cache = ruta_cache_por_hash(hash_archivo)
    with open(ruta_cache, "w", encoding="utf-8") as archivo:
        json.dump(payload, archivo, indent=2, ensure_ascii=False)
    return ruta_cache


def cargar_cache_libro(ruta_cache: str) -> Dict:
    ruta = Path(ruta_cache)
    if not ruta.exists():
        return {}

    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return {}


def registrar_libro(
    ruta_archivo: str,
    dominio: str,
    subdominio: str,
    tipo_archivo: str,
    paginas: int,
    caracteres_extraidos: int,
    temas_detectados: Optional[List[str]] = None,
    paginas_indexadas: Optional[List[int]] = None,
    categoria_id: str = "",
    categoria_nombre: str = "",
) -> Dict:
    ruta = Path(ruta_archivo)
    hash_archivo = calcular_hash_archivo(ruta_archivo)

    existente = obtener_libro_por_hash(hash_archivo)
    if existente:
        cambios = {}
        if categoria_id and existente.get("categoria_id", "") != categoria_id:
            cambios["categoria_id"] = categoria_id.strip()
            cambios["categoria_nombre"] = categoria_nombre.strip()
        if dominio and normalizar_texto(existente.get("dominio", "")) != normalizar_texto(dominio):
            cambios["dominio"] = normalizar_texto(dominio)
        if subdominio and normalizar_texto(existente.get("subdominio", "")) != normalizar_texto(subdominio):
            cambios["subdominio"] = normalizar_texto(subdominio)
        if cambios:
            actualizado = actualizar_libro(existente["id"], cambios)
            if actualizado.get("ok"):
                return actualizado.get("libro", existente)
        return existente

    biblioteca = obtener_seccion("biblioteca", [])

    libro = {
        "id": f"LIB-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "nombre": ruta.name,
        "ruta": str(ruta.resolve()),
        "dominio": normalizar_texto(dominio),
        "subdominio": normalizar_texto(subdominio),
        "categoria_id": categoria_id.strip(),
        "categoria_nombre": categoria_nombre.strip(),
        "tipo_archivo": tipo_archivo.lower(),
        "paginas": paginas,
        "caracteres_extraidos": caracteres_extraidos,
        "hash_archivo": hash_archivo,
        "cache_json": str(ruta_cache_por_hash(hash_archivo)),
        "temas_detectados": temas_detectados or [],
        "paginas_indexadas": paginas_indexadas or [],
        "fecha_carga": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado": "activo"
    }

    biblioteca.append(libro)
    guardar_seccion("biblioteca", biblioteca)
    registrar_log("sistema", f"Libro registrado: {libro['nombre']}", "biblioteca")
    return libro


def actualizar_libro(libro_id: str, nuevos_datos: Dict) -> Dict:
    biblioteca = obtener_seccion("biblioteca", [])
    actualizado = None

    for libro in biblioteca:
        if libro.get("id") == libro_id:
            libro.update(nuevos_datos)
            actualizado = libro
            break

    if actualizado is None:
        return {"ok": False, "mensaje": "No se encontró el libro."}

    guardar_seccion("biblioteca", biblioteca)
    registrar_log_admin("actualizar_libro", f"{actualizado.get('nombre', '')}", "biblioteca")
    return {"ok": True, "mensaje": "Libro actualizado correctamente.", "libro": actualizado}


def eliminar_libro(libro_id: str, enviar_papelera: bool = True) -> Dict:
    libro = obtener_libro_por_id(libro_id)
    if not libro:
        return {"ok": False, "mensaje": "No se encontró el libro."}

    if enviar_papelera:
        enviar_a_papelera("libro", "biblioteca", libro)

    eliminado = eliminar_elemento("biblioteca", "id", libro_id)
    if eliminado is None:
        return {"ok": False, "mensaje": "No se pudo eliminar el libro."}

    ruta_cache = Path(libro.get("cache_json", ""))
    if ruta_cache.exists():
        try:
            ruta_cache.unlink()
        except Exception:
            pass

    registrar_log_admin("eliminar_libro", f"{libro.get('nombre', '')}", "biblioteca")
    return {"ok": True, "mensaje": f"Libro eliminado: {libro.get('nombre', '')}"}
