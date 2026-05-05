import hashlib
from typing import Dict

from core.logs import registrar_log_admin
from core.memoria import obtener_seccion, guardar_seccion


def hash_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


def configurar_clave_admin(clave_plana: str) -> Dict:
    configuracion = obtener_seccion("configuracion", {})
    seguridad = configuracion.get("seguridad", {})

    seguridad["clave_admin_hash"] = hash_clave(clave_plana)
    seguridad["clave_admin_configurada"] = True

    configuracion["seguridad"] = seguridad
    guardar_seccion("configuracion", configuracion)

    registrar_log_admin("configurar_clave", "Se configuró la clave administrativa", "seguridad")
    return {"ok": True, "mensaje": "Clave administrativa configurada correctamente."}


def validar_clave_admin(clave_plana: str) -> bool:
    configuracion = obtener_seccion("configuracion", {})
    seguridad = configuracion.get("seguridad", {})
    clave_guardada = seguridad.get("clave_admin_hash", "")

    if not clave_guardada:
        return False

    return hash_clave(clave_plana) == clave_guardada


def requiere_clave_para_ruta(ruta_objetivo: str) -> bool:
    configuracion = obtener_seccion("configuracion", {})
    seguridad = configuracion.get("seguridad", {})
    modulos_protegidos = seguridad.get("modulos_protegidos", [])

    ruta_objetivo = ruta_objetivo.replace("\\", "/").lower()

    for modulo in modulos_protegidos:
        if modulo.lower() in ruta_objetivo:
            return True

    return False