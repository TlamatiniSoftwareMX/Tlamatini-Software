from datetime import datetime

from core.memoria import cargar_memoria, asegurar_estructura


def linea():
    print("============================================")


def resumen_memoria(memoria):
    print("\nEstado de memoria:\n")
    print("Biblioteca:", len(memoria.get("biblioteca", [])))
    print("Conocimiento manual:", len(memoria.get("conocimiento", [])))
    print("Índices documentales:", len(memoria.get("indices_conocimiento", [])))
    print("Personas registradas:", len(memoria.get("personas", [])))
    print("Animales:", len(memoria.get("animales", [])))
    print("Inventario:", len(memoria.get("inventario", [])))
    print("Planes:", len(memoria.get("planes", [])))
    print("Puntos de mapa:", len(memoria.get("mapa", {}).get("puntos_interes", [])))
    print("Polígonos de riesgo:", len(memoria.get("mapa", {}).get("poligonos_riesgo", [])))
    print("Nodos:", len(memoria.get("nodos", [])))
    print("Sensores:", len(memoria.get("sensores", [])))
    print("Lecturas:", len(memoria.get("lecturas", [])))
    print("Alertas:", len(memoria.get("alertas", [])))
    print("Protocolos:", len(memoria.get("protocolos", [])))
    print("Eventos:", len(memoria.get("eventos", [])))
    print("Incidentes:", len(memoria.get("incidentes", [])))
    print("Reglas:", len(memoria.get("reglas", [])))


def iniciar_sistema():
    linea()
    print("INICIANDO TLAMATINI IA")
    linea()

    ahora = datetime.now()
    print("Fecha:", ahora.strftime("%Y-%m-%d"))
    print("Hora:", ahora.strftime("%H:%M:%S"))

    linea()
    print("Verificando estructura del sistema...")

    asegurar_estructura()
    memoria = cargar_memoria()

    print("Estructura y memoria cargadas correctamente.")
    linea()

    resumen_memoria(memoria)

    linea()
    print("Sistema listo para recibir operaciones.")
    print("\nMódulos base disponibles:")
    print("- Consulta documental")
    print("- Biblioteca")
    print("- Inventario")
    print("- Mapa")
    print("- Sensores")
    print("- Conversación")
    linea()