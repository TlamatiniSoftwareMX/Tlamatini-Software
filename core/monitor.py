from datetime import datetime, timedelta

from core.alertas import crear_alerta
from core.logs import registrar_log
from core.memoria import obtener_seccion


def revisar_sensores_sin_datos(minutos_maximos: int = 60) -> None:
    sensores = obtener_seccion("sensores", [])
    lecturas = obtener_seccion("lecturas", [])
    ahora = datetime.now()

    for sensor in sensores:
        lecturas_sensor = [l for l in lecturas if l.get("sensor_id") == sensor.get("id")]
        if not lecturas_sensor:
            crear_alerta(
                tipo="sensor_sin_datos",
                mensaje=f"Sensor sin lecturas registradas: {sensor.get('nombre')}",
                prioridad="media",
                origen="monitor",
                referencia=sensor.get("id", "")
            )
            continue

        ultima = lecturas_sensor[-1]
        fecha_hora = f"{ultima.get('fecha')} {ultima.get('hora')}"
        try:
            fecha_ultima = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M:%S")
            if ahora - fecha_ultima > timedelta(minutes=minutos_maximos):
                crear_alerta(
                    tipo="sensor_inactivo",
                    mensaje=f"Sensor sin datos recientes: {sensor.get('nombre')}",
                    prioridad="alta",
                    origen="monitor",
                    referencia=sensor.get("id", "")
                )
        except ValueError:
            pass

    registrar_log("sistema", "Monitoreo de sensores ejecutado", "monitor")


def revisar_inventario() -> None:
    inventario = obtener_seccion("inventario", [])
    for item in inventario:
        minimo = item.get("minimo_deseable")
        cantidad = item.get("cantidad")
        nombre = item.get("nombre", "recurso")

        if minimo is not None and cantidad is not None and cantidad <= minimo:
            crear_alerta(
                tipo="inventario_bajo",
                mensaje=f"Inventario bajo: {nombre}",
                prioridad="alta",
                origen="inventario",
                referencia=item.get("id", "")
            )

    registrar_log("sistema", "Monitoreo de inventario ejecutado", "monitor")