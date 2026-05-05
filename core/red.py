from core.logs import registrar_log
from core.memoria import obtener_seccion, guardar_seccion


def configurar_modo_operacion(modo: str) -> dict:
    configuracion = obtener_seccion("configuracion", {})
    configuracion["modo_operacion"] = modo
    guardar_seccion("configuracion", configuracion)
    registrar_log("sistema", f"Modo de operación configurado: {modo}", "red")
    return configuracion


def obtener_configuracion_red() -> dict:
    return obtener_seccion("configuracion", {})