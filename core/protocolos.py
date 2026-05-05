from datetime import datetime
from typing import Dict, List

from core.logs import registrar_log
from core.memoria import agregar_a_seccion, obtener_seccion
from core.texto import normalizar_texto


def registrar_protocolo(nombre: str, descripcion: str, pasos: List[str]) -> Dict:
    protocolo = {
        "id": f"PROT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "nombre": nombre,
        "descripcion": descripcion,
        "pasos": pasos,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    agregar_a_seccion("protocolos", protocolo)
    registrar_log("sistema", f"Protocolo registrado: {nombre}", "protocolos")
    return protocolo


def listar_protocolos() -> List[dict]:
    return obtener_seccion("protocolos", [])


def ejecutar_protocolo(nombre: str) -> Dict:
    protocolos = obtener_seccion("protocolos", [])
    for protocolo in protocolos:
        if normalizar_texto(protocolo.get("nombre", "")) == normalizar_texto(nombre):
            registrar_log("protocolo", f"Protocolo ejecutado: {nombre}", "protocolos")
            return {
                "ok": True,
                "mensaje": f"Protocolo ejecutado: {nombre}",
                "protocolo": protocolo
            }

    return {
        "ok": False,
        "mensaje": f"No se encontró el protocolo: {nombre}"
    }
