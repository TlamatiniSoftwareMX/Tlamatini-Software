from core.alertas import crear_alerta
from core.logs import registrar_log
from core.memoria import buscar_en_seccion


def analizar_lectura(lectura: dict) -> None:
    sensor = buscar_en_seccion("sensores", "id", lectura.get("sensor_id"))
    if not sensor:
        return

    tipo = sensor.get("tipo", "").lower()
    valor = lectura.get("valor")
    zona = sensor.get("zona", "sin zona")

    if not lectura.get("valida", True):
        crear_alerta(
            tipo="dato_invalido",
            mensaje=f"Lectura fuera de rango en sensor {sensor.get('nombre')}: {valor}",
            prioridad="alta",
            origen="sensor",
            referencia=sensor.get("id", "")
        )
        return

    if tipo == "temperatura" and valor >= 60:
        crear_alerta(
            tipo="temperatura_alta",
            mensaje=f"Temperatura elevada en zona {zona}: {valor}",
            prioridad="alta",
            origen="sensor",
            referencia=sensor.get("id", "")
        )

    if tipo == "humo" and valor >= 1:
        crear_alerta(
            tipo="humo_detectado",
            mensaje=f"Detección de humo en zona {zona}",
            prioridad="critica",
            origen="sensor",
            referencia=sensor.get("id", "")
        )

    if tipo == "gas" and valor >= 300:
        crear_alerta(
            tipo="gas_detectado",
            mensaje=f"Posible presencia peligrosa de gas en zona {zona}: {valor}",
            prioridad="critica",
            origen="sensor",
            referencia=sensor.get("id", "")
        )

    registrar_log("sistema", f"Análisis de lectura completado para sensor {sensor.get('nombre')}", "razonamiento")