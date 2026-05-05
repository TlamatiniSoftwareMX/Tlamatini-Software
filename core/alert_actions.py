from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from core.logs import registrar_log
from core.memoria import cargar_memoria, guardar_memoria, guardar_seccion, obtener_seccion
from core.protocolos import listar_protocolos
from core.texto import normalizar_texto


SECCION_MODO_EMERGENCIA = "dashboard_modo_emergencia"
SECCION_RECORDATORIOS = "herramientas_recordatorios"


def acciones_para_alerta(alerta: Dict, gemma_ok: bool = False) -> List[Dict]:
    tipo = normalizar_texto(alerta.get("tipo", ""))
    acciones: List[Dict] = []

    def add(action_id: str, label: str, confirm: str, style: str = "default") -> None:
        acciones.append(
            {
                "id": action_id,
                "label": label,
                "confirm": confirm,
                "style": style,
            }
        )

    if tipo == "agua":
        add("inventario_agua", "Ver inventario", "¿Quieres abrir el inventario de agua?")
        add("abrir_mapa", "Abrir mapa", "¿Quieres abrir el mapa para revisar puntos de agua?")
        add("abrir_planes", "Planes", "¿Quieres abrir planes de emergencia relacionados?")
        add("abrir_biblioteca", "Biblioteca", "¿Quieres abrir la biblioteca para consultar material relacionado?")
        add("crear_recordatorio", "Recordatorio", "¿Quieres crear un recordatorio de revisión para esta alerta?")
    elif tipo == "comida":
        add("inventario_comida", "Ver inventario", "¿Quieres abrir el inventario de comida?")
        add("abrir_planes", "Planes", "¿Quieres abrir los planes relacionados?")
        add("abrir_aprendizaje", "Aprendizaje", "¿Quieres abrir aprendizaje relacionado?")
        add("crear_registro", "Registrar acción", "¿Quieres registrar esta decisión en bitácora?")
    elif tipo == "medicamentos":
        add("inventario_medico", "Botiquín", "¿Quieres abrir el inventario médico?")
        add("abrir_perfiles", "Ver perfiles", "¿Quieres abrir perfiles relacionados?")
        add("crear_recordatorio", "Recordatorio", "¿Quieres crear un recordatorio de reposición o revisión?")
        add("crear_registro", "Registrar acción", "¿Quieres registrar esta revisión en bitácora?")
    elif tipo == "energia":
        add("inventario_energia", "Ver energía", "¿Quieres abrir el inventario de energía?")
        add("herramienta_energia", "Calculadora", "¿Quieres abrir la calculadora de energía?")
        add("abrir_planes", "Planes", "¿Quieres abrir un plan relacionado?")
        add("crear_registro", "Registrar acción", "¿Quieres registrar el ajuste energético en bitácora?")
    elif tipo in {"salud", "perfil_medico"}:
        add("abrir_perfiles", "Ver perfiles", "¿Quieres abrir perfiles relacionados?")
        add("abrir_planes", "Protocolos", "¿Quieres abrir planes o protocolos relacionados?")
        add("abrir_biblioteca", "Biblioteca", "¿Quieres abrir biblioteca relacionada?")
        add("abrir_aprendizaje", "Aprendizaje", "¿Quieres abrir aprendizaje relacionado?")
    elif tipo == "sistema":
        add("reintentar_dashboard", "Reintentar", "¿Quieres reintentar el módulo o refrescar el dashboard?")
        add("ver_logs", "Ver logs", "¿Quieres abrir el visor de logs de esta alerta?")
        add("crear_registro", "Registrar acción", "¿Quieres registrar el seguimiento técnico en bitácora?")
    elif tipo in {"inventario", "mantenimiento", "evento"}:
        add("abrir_inventario", "Inventario", "¿Quieres abrir el inventario relacionado?")
        add("crear_recordatorio", "Recordatorio", "¿Quieres crear un recordatorio para esta alerta?")
        add("crear_registro", "Registrar acción", "¿Quieres registrar el seguimiento en bitácora?")
    elif tipo in {"emergency", "emergencia"}:
        add("activar_modo_emergencia", "Modo emergencia", "¿Quieres activar el modo emergencia?", style="danger")
        add("abrir_planes", "Planes", "¿Quieres abrir planes de emergencia?")
        add("crear_registro", "Registrar acción", "¿Quieres registrar esta condición crítica en bitácora?")
    else:
        add("crear_registro", "Registrar acción", "¿Quieres registrar esta alerta en bitácora?")

    if gemma_ok:
        acciones.append({"id": "pedir_ia", "label": "Pedir IA", "confirm": "", "style": "accent"})
    return acciones


def obtener_estado_modo_emergencia() -> Dict:
    datos = obtener_seccion(SECCION_MODO_EMERGENCIA, {})
    if not isinstance(datos, dict):
        return {"activo": False}
    return {"activo": bool(datos.get("activo", False)), **datos}


def activar_modo_emergencia(origen: str, resumen: str) -> Dict:
    estado = {
        "activo": True,
        "origen": origen,
        "resumen": resumen,
        "activado_en": datetime.now().isoformat(timespec="seconds"),
    }
    guardar_seccion(SECCION_MODO_EMERGENCIA, estado)
    registrar_log("bitacora", f"Modo emergencia activado: {resumen}", "alertas")
    return estado


def desactivar_modo_emergencia() -> Dict:
    estado = {"activo": False, "desactivado_en": datetime.now().isoformat(timespec="seconds")}
    guardar_seccion(SECCION_MODO_EMERGENCIA, estado)
    registrar_log("bitacora", "Modo emergencia desactivado", "alertas")
    return estado


def crear_recordatorio_desde_alerta(titulo: str, descripcion: str) -> Dict:
    ahora = datetime.now()
    fecha = ahora.strftime("%Y-%m-%d")
    hora = (ahora + timedelta(hours=1)).strftime("%H:%M")
    memoria = cargar_memoria()
    herramientas = memoria.get("herramientas", {})
    if not isinstance(herramientas, dict):
        herramientas = {}
        memoria["herramientas"] = herramientas
    recordatorios = herramientas.get(SECCION_RECORDATORIOS, [])
    if not isinstance(recordatorios, list):
        recordatorios = []
    item = {
        "id": f"REM-{ahora.strftime('%Y%m%d%H%M%S%f')}",
        "titulo": titulo,
        "nota": descripcion,
        "hora": hora,
        "repeticion": "una_vez",
        "fecha": fecha,
        "activa": True,
        "creado_en": ahora.isoformat(timespec="seconds"),
    }
    recordatorios.append(item)
    herramientas[SECCION_RECORDATORIOS] = recordatorios
    guardar_memoria(memoria)
    registrar_log("bitacora", f"Recordatorio creado desde alerta: {titulo}", "alertas")
    return item


def registrar_accion_alerta(alerta: Dict, accion: str, detalle: str = "") -> None:
    titulo = str(alerta.get("titulo", "Alerta")).strip() or "Alerta"
    texto = f"{titulo} · acción: {accion}"
    if detalle:
        texto += f" · {detalle}"
    registrar_log("bitacora", texto, "alertas")


def sugerir_modo_emergencia(alertas: List[Dict]) -> Dict:
    criticas = [alerta for alerta in alertas if normalizar_texto(alerta.get("nivel", "")) == "critico"]
    origenes = sorted({normalizar_texto(alerta.get("origen", "")) for alerta in criticas if str(alerta.get("origen", "")).strip()})
    if len(criticas) < 2 or len(origenes) < 2:
        return {"sugerir": False, "resumen": "", "origenes": origenes, "total": len(criticas)}
    resumen = f"Hay varias condiciones críticas activas: {', '.join(origenes[:4])}."
    return {"sugerir": True, "resumen": resumen, "origenes": origenes, "total": len(criticas)}


def buscar_protocolo_relacionado(alerta: Dict) -> Dict:
    tipo = normalizar_texto(alerta.get("tipo", ""))
    origen = normalizar_texto(alerta.get("origen", ""))
    palabras = {tipo, origen, normalizar_texto(alerta.get("titulo", ""))}
    for protocolo in listar_protocolos():
        texto = " ".join(
            [
                normalizar_texto(protocolo.get("nombre", "")),
                normalizar_texto(protocolo.get("descripcion", "")),
                " ".join(normalizar_texto(paso) for paso in protocolo.get("pasos", []) if isinstance(paso, str)),
            ]
        )
        if any(palabra and palabra in texto for palabra in palabras):
            return protocolo
    return {}
