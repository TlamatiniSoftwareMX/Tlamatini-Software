from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from core.alertas import (
    ESTADO_ACTIVA,
    cerrar_alerta,
    cerrar_alerta_por_clave,
    cerrar_alertas_panel,
    listar_alertas,
    upsert_alerta,
)
from core.alert_actions import sugerir_modo_emergencia
from core.inventario import listar_alertas_inventario, listar_inventario
from core.logs import leer_logs
from core.memoria import cargar_memoria, guardar_seccion, obtener_seccion
from core.perfiles import calcular_autonomia_persona, listar_personas
from core.resiliencia import estimar_reserva_agua, estimar_reserva_comida
from core.texto import normalizar_texto


PANEL_DASHBOARD = "dashboard"
NIVEL_CRITICO = "critico"
NIVEL_ADVERTENCIA = "advertencia"
NIVEL_INFO = "info"
UMBRAL_AGUA_CRITICO_DIAS = 3.0
UMBRAL_COMIDA_CRITICO_DIAS = 3.0
UMBRAL_COMIDA_ADVERTENCIA_DIAS = 7.0
UMBRAL_MANTENIMIENTO_DIAS = 3
UMBRAL_EVENTOS_HORAS = 24
UMBRAL_ERRORES_HORAS = 48
PALABRAS_ERROR_SISTEMA = (
    "fallo",
    "falló",
    "error",
    "no se pudo",
    "excepcion",
    "excepción",
    "failed",
)
PALABRAS_SYNC = ("sincron", "sync")
PALABRAS_CARGA = ("carga", "descarga", "runtime", "modulo", "módulo")
MENSAJES_SISTEMA_ESPERADOS = (
    "no hay backend configurado para revisar actualizaciones",
    "backend local de actualizaciones no esta disponible",
    "el backend local solo se usa en modo desarrollo",
    "gemma no respondio para alerta",
    "ia advisor en espera",
)


def _ahora() -> datetime:
    return datetime.now()


def _parse_timestamp(fecha: str, hora: str) -> Optional[datetime]:
    try:
        return datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _memoria_herramientas() -> Dict:
    memoria = cargar_memoria()
    herramientas = memoria.get("herramientas", {})
    return herramientas if isinstance(herramientas, dict) else {}


def _recordatorios_hoy_y_pendientes() -> List[Dict]:
    herramientas = _memoria_herramientas()
    recordatorios = herramientas.get("herramientas_recordatorios", [])
    if not isinstance(recordatorios, list):
        return []
    return [item for item in recordatorios if isinstance(item, dict)]


def _alarmas_programadas() -> List[Dict]:
    herramientas = _memoria_herramientas()
    alarmas = herramientas.get("herramientas_alarmas", [])
    if not isinstance(alarmas, list):
        return []
    return [item for item in alarmas if isinstance(item, dict)]


def _clave(*partes: str) -> str:
    return "::".join(str(parte or "").strip().lower() for parte in partes)


def _firma_alerta(alerta: Dict) -> str:
    partes = (
        str(alerta.get("titulo", "")).strip(),
        str(alerta.get("descripcion", "")).strip(),
        normalizar_texto(alerta.get("nivel", "")),
        str(alerta.get("origen", "")).strip(),
        str(alerta.get("referencia", "")).strip(),
    )
    return "||".join(partes)


def _cargar_silenciadas() -> Dict[str, str]:
    datos = obtener_seccion("alertas_dashboard_silenciadas", {})
    return datos if isinstance(datos, dict) else {}


def _guardar_silenciadas(datos: Dict[str, str]) -> None:
    guardar_seccion("alertas_dashboard_silenciadas", datos)


def _silenciar_alertas(alertas: List[Dict]) -> None:
    silenciadas = _cargar_silenciadas()
    cambios = False
    for alerta in alertas:
        clave = str(alerta.get("clave", "")).strip()
        if not clave:
            continue
        firma = _firma_alerta(alerta)
        if silenciadas.get(clave) == firma:
            continue
        silenciadas[clave] = firma
        cambios = True
    if cambios:
        _guardar_silenciadas(silenciadas)


def _titulo_desde_alerta_inventario(alerta: Dict) -> str:
    tipo = normalizar_texto(alerta.get("tipo", ""))
    if tipo == "stock_minimo":
        return "Inventario crítico"
    if tipo == "stock_cercano":
        return "Inventario bajo"
    if tipo in {"caducado", "caduca_hoy", "caducidad_proxima"}:
        return "Medicamento por vencer" if normalizar_texto(alerta.get("categoria", "")) == "insumos medicos" else "Caducidad próxima"
    return "Inventario"


def _nivel_alerta_inventario(alerta: Dict) -> str:
    tipo = normalizar_texto(alerta.get("tipo", ""))
    if tipo in {"stock_minimo", "caducado", "caduca_hoy"}:
        return NIVEL_CRITICO
    if tipo in {"stock_cercano", "caducidad_proxima"}:
        return NIVEL_ADVERTENCIA
    return NIVEL_INFO


def _resumen_inventario_critico(alertas_inventario: List[Dict]) -> Optional[Dict]:
    criticas = [a for a in alertas_inventario if normalizar_texto(a.get("tipo", "")) in {"stock_minimo", "caducado", "caduca_hoy"}]
    if not criticas:
        return None
    return {
        "clave": _clave("inventario", "critico"),
        "tipo": "inventario",
        "titulo": "Inventario crítico",
        "descripcion": f"Hay {len(criticas)} elemento(s) en estado crítico o vencido.",
        "nivel": NIVEL_CRITICO,
        "origen": "inventario",
        "referencia": "inventario_critico",
    }


def _alerta_agua(items: List[Dict], personas: List[Dict]) -> Optional[Dict]:
    estado = estimar_reserva_agua(items, personas)
    dias = estado.get("dias_autonomia")
    if dias is None or dias > UMBRAL_AGUA_CRITICO_DIAS:
        return None
    return {
        "clave": _clave("agua", "autonomia_baja"),
        "tipo": "agua",
        "titulo": "Agua baja",
        "descripcion": f"Quedan {dias:.1f} día(s) de autonomía con el consumo actual.",
        "nivel": NIVEL_CRITICO,
        "origen": "agua",
        "referencia": "autonomia_agua",
        "metadata": estado,
    }


def _alerta_comida(items: List[Dict], personas: List[Dict]) -> Optional[Dict]:
    estado = estimar_reserva_comida(items, personas)
    dias = estado.get("dias_autonomia")
    if dias is None:
        return None
    if dias <= UMBRAL_COMIDA_CRITICO_DIAS:
        nivel = NIVEL_CRITICO
    elif dias <= UMBRAL_COMIDA_ADVERTENCIA_DIAS:
        nivel = NIVEL_ADVERTENCIA
    else:
        return None
    return {
        "clave": _clave("comida", "autonomia_baja"),
        "tipo": "comida",
        "titulo": "Comida baja",
        "descripcion": f"Quedan {dias:.1f} día(s) de reserva de comida para el grupo actual.",
        "nivel": nivel,
        "origen": "comida",
        "referencia": "autonomia_comida",
        "metadata": estado,
    }


def _alertas_medicamentos(alertas_inventario: List[Dict]) -> List[Dict]:
    resultado = []
    for alerta in alertas_inventario:
        if normalizar_texto(alerta.get("categoria", "")) != "insumos medicos":
            continue
        if normalizar_texto(alerta.get("tipo", "")) not in {"caducado", "caduca_hoy", "caducidad_proxima"}:
            continue
        resultado.append(
            {
                "clave": _clave("medicamentos", alerta.get("item_id", ""), alerta.get("tipo", "")),
                "tipo": "medicamentos",
                "titulo": "Medicamentos por vencer",
                "descripcion": str(alerta.get("mensaje", "")).strip(),
                "nivel": _nivel_alerta_inventario(alerta),
                "origen": "inventario",
                "referencia": str(alerta.get("item_id", "")).strip(),
                "metadata": alerta,
            }
        )
    return resultado


def _alertas_energia(alertas_inventario: List[Dict]) -> List[Dict]:
    resultado = []
    for alerta in alertas_inventario:
        if normalizar_texto(alerta.get("categoria", "")) != "energia":
            continue
        if normalizar_texto(alerta.get("tipo", "")) not in {"stock_minimo", "stock_cercano", "caducado", "caduca_hoy", "caducidad_proxima"}:
            continue
        resultado.append(
            {
                "clave": _clave("energia", alerta.get("item_id", ""), alerta.get("tipo", "")),
                "tipo": "energia",
                "titulo": "Energía baja",
                "descripcion": str(alerta.get("mensaje", "")).strip() or "Hay un recurso energético en estado bajo o crítico.",
                "nivel": _nivel_alerta_inventario(alerta),
                "origen": "inventario",
                "referencia": str(alerta.get("item_id", "")).strip(),
                "metadata": alerta,
            }
        )
    return resultado


def _alertas_perfiles_medicos(personas: List[Dict]) -> List[Dict]:
    resultado = []
    for persona in personas:
        persona_id = str(persona.get("id", "")).strip()
        if not persona_id:
            continue
        try:
            autonomia = calcular_autonomia_persona(persona_id)
        except Exception:
            continue
        if not autonomia.get("ok"):
            continue
        for med in autonomia.get("medicamentos", []):
            dias = med.get("dias_cobertura")
            if dias is None:
                continue
            if dias > 7:
                continue
            nombre = str(med.get("nombre", "")).strip() or "Medicamento"
            perfil = str(persona.get("nombre", "")).strip() or "Perfil"
            nivel = NIVEL_CRITICO if dias <= 3 else NIVEL_ADVERTENCIA
            resultado.append(
                {
                    "clave": _clave("perfil_medico", persona_id, nombre),
                    "tipo": "salud",
                    "titulo": "Alerta médica / perfil",
                    "descripcion": f"{perfil} tiene cobertura estimada de {dias:.1f} día(s) para {nombre}.",
                    "nivel": nivel,
                    "origen": "perfiles",
                    "referencia": persona_id,
                    "metadata": {
                        "perfil": perfil,
                        "medicamento": nombre,
                        "dias_cobertura": dias,
                        "coincidencias": med.get("coincidencias", []),
                    },
                }
            )
    return resultado


def _titulo_alerta_sistema(mensaje_normalizado: str) -> str:
    if any(palabra in mensaje_normalizado for palabra in PALABRAS_SYNC):
        return "Sincronización fallida"
    if any(palabra in mensaje_normalizado for palabra in PALABRAS_CARGA):
        return "Problema de carga"
    return "Error del sistema"


def _alertas_errores_sistema(logs: List[Dict]) -> List[Dict]:
    limite = _ahora() - timedelta(hours=UMBRAL_ERRORES_HORAS)
    resultado = []
    vistos: Set[str] = set()
    for log in reversed(list(logs or [])):
        tipo = normalizar_texto(log.get("tipo", ""))
        modulo = normalizar_texto(log.get("modulo", ""))
        mensaje = str(log.get("mensaje", "")).strip()
        mensaje_n = normalizar_texto(mensaje)
        if not mensaje:
            continue
        if any(fragmento in mensaje_n for fragmento in MENSAJES_SISTEMA_ESPERADOS):
            continue
        if modulo == "alertas" or tipo == "alerta":
            continue
        stamp = _parse_timestamp(log.get("fecha", ""), log.get("hora", ""))
        if stamp is None or stamp < limite:
            continue
        es_error = tipo == "error" or (
            tipo in {"critical", "critico", "fatal"} and any(palabra in mensaje_n for palabra in PALABRAS_ERROR_SISTEMA)
        )
        if not es_error:
            continue
        clave = _clave("sistema", "error", log.get("modulo", ""), mensaje[:120])
        if clave in vistos:
            continue
        vistos.add(clave)
        resultado.append(
            {
                "clave": clave,
                "tipo": "sistema",
                "titulo": _titulo_alerta_sistema(mensaje_n),
                "descripcion": mensaje,
                "nivel": NIVEL_CRITICO,
                "origen": str(log.get("modulo", "sistema")).strip() or "sistema",
                "referencia": f"{log.get('fecha', '')} {log.get('hora', '')}".strip(),
                "metadata": log,
            }
        )
    return resultado[:6]


def _alertas_herramientas_disparadas(logs: List[Dict]) -> List[Dict]:
    limite = _ahora() - timedelta(hours=UMBRAL_EVENTOS_HORAS)
    resultado = []
    for log in reversed(list(logs or [])):
        tipo = normalizar_texto(log.get("tipo", ""))
        if tipo not in {"recordatorio", "alarma"}:
            continue
        stamp = _parse_timestamp(log.get("fecha", ""), log.get("hora", ""))
        if stamp is None or stamp < limite:
            continue
        mensaje = str(log.get("mensaje", "")).strip()
        if not mensaje:
            continue
        resultado.append(
            {
                "clave": _clave("herramientas", tipo, log.get("fecha", ""), log.get("hora", ""), mensaje[:80]),
                "tipo": tipo,
                "titulo": "Alarma disparada" if tipo == "alarma" else "Recordatorio activado",
                "descripcion": mensaje,
                "nivel": NIVEL_CRITICO if tipo == "alarma" else NIVEL_ADVERTENCIA,
                "origen": str(log.get("modulo", "herramientas")).strip() or "herramientas",
                "referencia": f"{log.get('fecha', '')} {log.get('hora', '')}".strip(),
                "auto_generada": False,
                "metadata": log,
            }
        )
    return resultado[:8]


def _alertas_recordatorios() -> List[Dict]:
    ahora = _ahora()
    hoy = ahora.strftime("%Y-%m-%d")
    limite = ahora + timedelta(days=UMBRAL_MANTENIMIENTO_DIAS)
    resultado = []

    for item in _recordatorios_hoy_y_pendientes():
        fecha = str(item.get("fecha", "")).strip()
        hora = str(item.get("hora", "00:00")).strip() or "00:00"
        titulo = str(item.get("titulo", "")).strip()
        nota = str(item.get("nota", "")).strip()
        if not fecha or not titulo:
            continue
        try:
            programado = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        except Exception:
            continue
        if programado > limite:
            continue
        texto = " ".join((titulo, nota)).lower()
        if not any(palabra in texto for palabra in ("mantenimiento", "revision", "revisión", "filtro", "tarea", "pendiente")):
            continue
        nivel = NIVEL_ADVERTENCIA if programado.date() <= ahora.date() else NIVEL_INFO
        descripcion = f"{titulo} · programado para {fecha} {hora}"
        if nota:
            descripcion += f" · {nota}"
        resultado.append(
            {
                "clave": _clave("mantenimiento", item.get("id", ""), fecha, hora),
                "tipo": "mantenimiento",
                "titulo": "Mantenimiento pendiente",
                "descripcion": descripcion,
                "nivel": nivel,
                "origen": "herramientas",
                "referencia": str(item.get("id", "")).strip(),
                "metadata": item,
            }
        )

    for item in _alarmas_programadas():
        if not item.get("activa", True):
            continue
        titulo = str(item.get("titulo", "")).strip()
        nota = str(item.get("nota", "")).strip()
        texto = " ".join((titulo, nota)).lower()
        if not any(palabra in texto for palabra in ("mantenimiento", "revision", "revisión", "filtro", "tarea")):
            continue
        descripcion = f"{titulo} · alarma programada a las {item.get('hora', '--:--')}"
        if nota:
            descripcion += f" · {nota}"
        resultado.append(
            {
                "clave": _clave("alarma", item.get("id", ""), item.get("hora", "")),
                "tipo": "mantenimiento",
                "titulo": "Tarea programada",
                "descripcion": descripcion,
                "nivel": NIVEL_INFO,
                "origen": "herramientas",
                "referencia": str(item.get("id", "")).strip(),
                "metadata": item,
            }
        )
    return resultado


def _alertas_eventos_generales(logs: List[Dict]) -> List[Dict]:
    limite = _ahora() - timedelta(hours=UMBRAL_EVENTOS_HORAS)
    resultado = []
    tipos_validos = {"bitacora", "dashboard", "admin"}
    for log in reversed(list(logs or [])):
        tipo = normalizar_texto(log.get("tipo", ""))
        if tipo not in tipos_validos:
            continue
        if normalizar_texto(log.get("modulo", "")) in {"alertas", "alert_ai"}:
            continue
        stamp = _parse_timestamp(log.get("fecha", ""), log.get("hora", ""))
        if stamp is None or stamp < limite:
            continue
        mensaje = str(log.get("mensaje", "")).strip()
        if not mensaje:
            continue
        resultado.append(
            {
                "clave": _clave("evento", log.get("fecha", ""), log.get("hora", ""), mensaje[:80]),
                "tipo": "evento",
                "titulo": "Evento registrado",
                "descripcion": mensaje,
                "nivel": NIVEL_INFO,
                "origen": str(log.get("modulo", "sistema")).strip() or "sistema",
                "referencia": f"{log.get('fecha', '')} {log.get('hora', '')}".strip(),
                "auto_generada": False,
                "metadata": log,
            }
        )
    return resultado[:5]


def sincronizar_alertas_dashboard() -> List[Dict]:
    items = listar_inventario()
    personas = listar_personas() or obtener_seccion("personas", [])
    inventario_alertas = listar_alertas_inventario()
    logs = leer_logs()

    deseadas: List[Dict] = []
    agua = _alerta_agua(items, personas)
    if agua:
        deseadas.append(agua)
    comida = _alerta_comida(items, personas)
    if comida:
        deseadas.append(comida)
    inventario_resumen = _resumen_inventario_critico(inventario_alertas)
    if inventario_resumen:
        deseadas.append(inventario_resumen)
    deseadas.extend(_alertas_medicamentos(inventario_alertas))
    deseadas.extend(_alertas_energia(inventario_alertas))
    deseadas.extend(_alertas_perfiles_medicos(personas))
    deseadas.extend(_alertas_errores_sistema(logs))
    deseadas.extend(_alertas_recordatorios())
    deseadas.extend(_alertas_herramientas_disparadas(logs))
    deseadas.extend(_alertas_eventos_generales(logs))
    emergencia = sugerir_modo_emergencia(deseadas)
    if emergencia.get("sugerir"):
        deseadas.append(
            {
                "clave": _clave("emergency", "suggested"),
                "tipo": "emergency",
                "titulo": "Modo emergencia sugerido",
                "descripcion": emergencia.get("resumen", "Hay varias condiciones críticas simultáneas."),
                "nivel": NIVEL_CRITICO,
                "origen": "sistema",
                "referencia": "modo_emergencia",
                "metadata": emergencia,
            }
        )

    claves_deseadas = {alerta["clave"] for alerta in deseadas}
    silenciadas = _cargar_silenciadas()
    silenciadas = {clave: firma for clave, firma in silenciadas.items() if clave in claves_deseadas}
    activas_dashboard = listar_alertas(estado=ESTADO_ACTIVA, panel=PANEL_DASHBOARD)
    for alerta in activas_dashboard:
        clave = str(alerta.get("clave", "")).strip()
        if not clave:
            continue
        if not alerta.get("auto_generada", True):
            continue
        if clave not in claves_deseadas:
            cerrar_alerta_por_clave(clave)

    for alerta in deseadas:
        clave = alerta["clave"]
        firma = _firma_alerta(alerta)
        if silenciadas.get(clave) == firma:
            continue
        silenciadas.pop(clave, None)
        upsert_alerta(
            clave=clave,
            tipo=alerta["tipo"],
            titulo=alerta["titulo"],
            descripcion=alerta["descripcion"],
            nivel=alerta.get("nivel", NIVEL_ADVERTENCIA),
            origen=alerta.get("origen", "sistema"),
            referencia=alerta.get("referencia", ""),
            panel=PANEL_DASHBOARD,
            auto_generada=alerta.get("auto_generada", True),
            metadata=alerta.get("metadata", {}),
        )

    _guardar_silenciadas(silenciadas)

    return listar_alertas_panel()


def listar_alertas_panel(nivel: str = "todas", incluir_resueltas: bool = False) -> List[Dict]:
    alertas = listar_alertas(panel=PANEL_DASHBOARD)
    if not incluir_resueltas:
        alertas = [alerta for alerta in alertas if alerta.get("estado") == ESTADO_ACTIVA]
    nivel_n = normalizar_texto(nivel)
    if nivel_n and nivel_n != "todas":
        alertas = [alerta for alerta in alertas if normalizar_texto(alerta.get("nivel", "")) == nivel_n]
    return alertas


def limpiar_panel_alertas() -> int:
    activas = listar_alertas(estado=ESTADO_ACTIVA, panel=PANEL_DASHBOARD)
    _silenciar_alertas(activas)
    return cerrar_alertas_panel(PANEL_DASHBOARD)


def resolver_alerta_panel(alerta_id: str) -> bool:
    activas = listar_alertas(estado=ESTADO_ACTIVA, panel=PANEL_DASHBOARD)
    objetivo = [alerta for alerta in activas if alerta.get("id") == alerta_id]
    if objetivo:
        _silenciar_alertas(objetivo)
    return cerrar_alerta(alerta_id)
