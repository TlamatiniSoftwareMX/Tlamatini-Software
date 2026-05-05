from datetime import datetime
from typing import List, Optional

from core.memoria import RUTA_LOGS, agregar_a_seccion, asegurar_estructura, obtener_seccion
from core.texto import normalizar_texto


def registrar_log(tipo: str, mensaje: str, modulo: str = "sistema") -> dict:
    asegurar_estructura()

    evento = {
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "hora": datetime.now().strftime("%H:%M:%S"),
        "tipo": normalizar_texto(tipo),
        "modulo": normalizar_texto(modulo),
        "mensaje": mensaje.strip()
    }

    linea = f"[{evento['fecha']} {evento['hora']}] [{evento['tipo'].upper()}] [{evento['modulo'].upper()}] {evento['mensaje']}\n"
    with open(RUTA_LOGS, "a", encoding="utf-8") as archivo:
        archivo.write(linea)

    agregar_a_seccion("logs_sistema", evento)
    return evento


def registrar_log_admin(accion: str, detalle: str, modulo: str = "administracion") -> dict:
    return registrar_log("admin", f"{accion}: {detalle}", modulo)


def leer_logs(tipo: Optional[str] = None, modulo: Optional[str] = None) -> List[dict]:
    logs = obtener_seccion("logs_sistema", [])
    resultado = []

    for log in logs:
        if tipo and normalizar_texto(log.get("tipo", "")) != normalizar_texto(tipo):
            continue
        if modulo and normalizar_texto(log.get("modulo", "")) != normalizar_texto(modulo):
            continue
        resultado.append(log)

    return resultado[-300:]
