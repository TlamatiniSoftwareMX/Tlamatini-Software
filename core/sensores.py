from datetime import datetime
from typing import Dict, List, Optional

from core.logs import registrar_log
from core.memoria import agregar_a_seccion, buscar_en_seccion, obtener_seccion


RANGOS_VALIDOS = {
    "temperatura": (-50, 200),
    "humedad": (0, 100),
    "humo": (0, 1),
    "gas": (0, 10000),
    "presion": (0, 5000),
    "ritmo_cardiaco": (20, 250),
    "glucosa": (20, 1000)
}


def validar_lectura(tipo_sensor: str, valor: float) -> bool:
    rango = RANGOS_VALIDOS.get(tipo_sensor.lower())
    if not rango:
        return True
    return rango[0] <= valor <= rango[1]


def registrar_nodo(nombre: str, ubicacion: str = "", ip: str = "", zona: str = "") -> Dict:
    nodo = {
        "id": f"NODO-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "nombre": nombre,
        "ubicacion": ubicacion,
        "ip": ip,
        "zona": zona,
        "estado": "activo",
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    agregar_a_seccion("nodos", nodo)
    registrar_log("sistema", f"Nodo registrado: {nombre}", "sensores")
    return nodo


def registrar_sensor(
    nombre: str,
    tipo: str,
    nodo_id: str,
    zona: str = "",
    unidad: str = "",
    descripcion: str = ""
) -> Dict:
    sensor = {
        "id": f"SENSOR-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "nombre": nombre,
        "tipo": tipo.lower(),
        "nodo_id": nodo_id,
        "zona": zona,
        "unidad": unidad,
        "descripcion": descripcion,
        "estado": "activo",
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    agregar_a_seccion("sensores", sensor)
    registrar_log("sistema", f"Sensor registrado: {nombre} ({tipo})", "sensores")
    return sensor


def registrar_lectura(sensor_id: str, valor: float) -> Dict:
    sensor = buscar_en_seccion("sensores", "id", sensor_id)
    if not sensor:
        raise ValueError("Sensor no encontrado.")

    lectura = {
        "id": f"LEC-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "sensor_id": sensor_id,
        "tipo_sensor": sensor.get("tipo", ""),
        "valor": valor,
        "valida": validar_lectura(sensor.get("tipo", ""), valor),
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "hora": datetime.now().strftime("%H:%M:%S")
    }

    agregar_a_seccion("lecturas", lectura)
    registrar_log("sensor", f"Lectura registrada en {sensor.get('nombre')}: {valor}", "sensores")
    return lectura


def listar_sensores() -> List[dict]:
    return obtener_seccion("sensores", [])


def listar_lecturas(sensor_id: Optional[str] = None) -> List[dict]:
    lecturas = obtener_seccion("lecturas", [])
    if sensor_id:
        return [l for l in lecturas if l.get("sensor_id") == sensor_id]
    return lecturas