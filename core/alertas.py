from datetime import datetime
from typing import Dict, List, Optional

from core.logs import registrar_log
from core.memoria import guardar_seccion, obtener_seccion
from core.texto import normalizar_texto


ESTADO_ACTIVA = "activa"
ESTADO_RESUELTA = "resuelta"


def _ahora() -> datetime:
    return datetime.now()


def _timestamp_partes() -> Dict[str, str]:
    ahora = _ahora()
    return {
        "fecha": ahora.strftime("%Y-%m-%d"),
        "hora": ahora.strftime("%H:%M:%S"),
        "timestamp": ahora.isoformat(timespec="seconds"),
    }


def _nivel_desde_prioridad(prioridad: str) -> str:
    prioridad_n = normalizar_texto(prioridad)
    if prioridad_n in {"alta", "critica", "crítica"}:
        return "critico"
    if prioridad_n in {"media", "warning", "advertencia"}:
        return "advertencia"
    return "info"


def _prioridad_desde_nivel(nivel: str) -> str:
    nivel_n = normalizar_texto(nivel)
    if nivel_n == "critico":
        return "alta"
    if nivel_n == "advertencia":
        return "media"
    return "baja"


def _titulo_default(tipo: str) -> str:
    texto = str(tipo or "alerta").replace("_", " ").strip()
    return texto[:1].upper() + texto[1:] if texto else "Alerta"


def _normalizar_alerta(alerta: Dict) -> Dict:
    partes = _timestamp_partes()
    tipo = str(alerta.get("tipo", "general")).strip().lower() or "general"
    mensaje = str(alerta.get("mensaje", alerta.get("descripcion", ""))).strip()
    prioridad = str(alerta.get("prioridad", "")).strip().lower()
    nivel = str(alerta.get("nivel", "")).strip().lower() or _nivel_desde_prioridad(prioridad or "media")
    prioridad = prioridad or _prioridad_desde_nivel(nivel)
    referencia = str(alerta.get("referencia", "")).strip()
    origen = str(alerta.get("origen", "sistema")).strip() or "sistema"
    estado = str(alerta.get("estado", ESTADO_ACTIVA)).strip().lower() or ESTADO_ACTIVA
    alerta_id = str(alerta.get("id", f"ALT-{_ahora().strftime('%Y%m%d%H%M%S%f')}")).strip()

    return {
        "id": alerta_id,
        "clave": str(alerta.get("clave", "")).strip(),
        "tipo": tipo,
        "nivel": nivel,
        "prioridad": prioridad,
        "titulo": str(alerta.get("titulo", _titulo_default(tipo))).strip() or _titulo_default(tipo),
        "descripcion": str(alerta.get("descripcion", mensaje)).strip() or mensaje,
        "mensaje": mensaje or str(alerta.get("descripcion", "")).strip(),
        "origen": origen,
        "referencia": referencia,
        "estado": ESTADO_RESUELTA if estado in {"cerrada", "resuelta"} else ESTADO_ACTIVA,
        "fecha": str(alerta.get("fecha", partes["fecha"])).strip() or partes["fecha"],
        "hora": str(alerta.get("hora", partes["hora"])).strip() or partes["hora"],
        "timestamp": str(alerta.get("timestamp", partes["timestamp"])).strip() or partes["timestamp"],
        "actualizado_en": str(alerta.get("actualizado_en", partes["timestamp"])).strip() or partes["timestamp"],
        "resuelta_en": str(alerta.get("resuelta_en", "")).strip(),
        "auto_generada": bool(alerta.get("auto_generada", False)),
        "panel": str(alerta.get("panel", "general")).strip() or "general",
        "metadata": alerta.get("metadata", {}) if isinstance(alerta.get("metadata", {}), dict) else {},
    }


def _cargar_alertas() -> List[Dict]:
    alertas = obtener_seccion("alertas", [])
    if not isinstance(alertas, list):
        return []
    return [_normalizar_alerta(alerta) for alerta in alertas if isinstance(alerta, dict)]


def _guardar_alertas(alertas: List[Dict]) -> None:
    guardar_seccion("alertas", [_normalizar_alerta(alerta) for alerta in alertas])


def crear_alerta(
    tipo: str,
    mensaje: str,
    prioridad: str = "media",
    origen: str = "sistema",
    referencia: str = "",
    titulo: str = "",
    descripcion: str = "",
    clave: str = "",
    panel: str = "general",
    auto_generada: bool = False,
    metadata: Optional[Dict] = None,
) -> dict:
    alerta = _normalizar_alerta(
        {
            "tipo": tipo,
            "mensaje": mensaje,
            "prioridad": prioridad,
            "nivel": _nivel_desde_prioridad(prioridad),
            "titulo": titulo or _titulo_default(tipo),
            "descripcion": descripcion or mensaje,
            "origen": origen,
            "referencia": referencia,
            "clave": clave,
            "panel": panel,
            "auto_generada": auto_generada,
            "metadata": metadata or {},
        }
    )
    alertas = _cargar_alertas()
    alertas.append(alerta)
    _guardar_alertas(alertas)
    registrar_log("alerta", f"{alerta['titulo']}: {alerta['descripcion']}", "alertas")
    if str(alerta.get("panel", "")).strip() == "dashboard":
        registrar_log("bitacora", f"Alerta generada: {alerta['titulo']} · {alerta['descripcion']}", "alertas")
    return alerta


def upsert_alerta(
    *,
    clave: str,
    tipo: str,
    titulo: str,
    descripcion: str,
    nivel: str = "advertencia",
    origen: str = "sistema",
    referencia: str = "",
    panel: str = "dashboard",
    auto_generada: bool = True,
    metadata: Optional[Dict] = None,
    registrar_en_log: bool = True,
) -> dict:
    alertas = _cargar_alertas()
    partes = _timestamp_partes()
    metadata = metadata or {}

    for alerta in alertas:
        if alerta.get("clave") != clave:
            continue
        cambios = (
            alerta.get("estado") != ESTADO_ACTIVA
            or alerta.get("titulo") != titulo
            or alerta.get("descripcion") != descripcion
            or alerta.get("nivel") != normalizar_texto(nivel)
            or alerta.get("origen") != origen
            or alerta.get("referencia") != referencia
            or alerta.get("metadata") != metadata
        )
        alerta.update(
            _normalizar_alerta(
                {
                    **alerta,
                    "tipo": tipo,
                    "nivel": nivel,
                    "prioridad": _prioridad_desde_nivel(nivel),
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "mensaje": descripcion,
                    "origen": origen,
                    "referencia": referencia,
                    "estado": ESTADO_ACTIVA,
                    "actualizado_en": partes["timestamp"],
                    "resuelta_en": "",
                    "panel": panel,
                    "auto_generada": auto_generada,
                    "metadata": metadata,
                }
            )
        )
        _guardar_alertas(alertas)
        if cambios and registrar_en_log:
            registrar_log("alerta", f"{titulo}: {descripcion}", "alertas")
            if str(panel).strip() == "dashboard":
                registrar_log("bitacora", f"Alerta actualizada: {titulo} · {descripcion}", "alertas")
        return alerta

    return crear_alerta(
        tipo=tipo,
        mensaje=descripcion,
        prioridad=_prioridad_desde_nivel(nivel),
        origen=origen,
        referencia=referencia,
        titulo=titulo,
        descripcion=descripcion,
        clave=clave,
        panel=panel,
        auto_generada=auto_generada,
        metadata=metadata,
    )


def listar_alertas(estado: Optional[str] = None, panel: Optional[str] = None) -> List[dict]:
    alertas = _cargar_alertas()
    resultado = []
    for alerta in alertas:
        if estado:
            estado_n = normalizar_texto(estado)
            alerta_estado = normalizar_texto(alerta.get("estado", ""))
            if estado_n in {"cerrada", "resuelta"}:
                if alerta_estado != ESTADO_RESUELTA:
                    continue
            elif alerta_estado != estado_n:
                continue
        if panel and normalizar_texto(alerta.get("panel", "")) != normalizar_texto(panel):
            continue
        resultado.append(alerta)
    return sorted(resultado, key=lambda item: (item.get("fecha", ""), item.get("hora", ""), item.get("id", "")), reverse=True)


def obtener_alertas_activas(panel: Optional[str] = None) -> List[dict]:
    return listar_alertas(ESTADO_ACTIVA, panel=panel)


def cerrar_alerta(alerta_id: str) -> bool:
    alertas = _cargar_alertas()
    partes = _timestamp_partes()
    cambiado = False
    for alerta in alertas:
        if alerta.get("id") != alerta_id:
            continue
        alerta["estado"] = ESTADO_RESUELTA
        alerta["resuelta_en"] = partes["timestamp"]
        alerta["actualizado_en"] = partes["timestamp"]
        cambiado = True
        break
    if cambiado:
        _guardar_alertas(alertas)
    return cambiado


def cerrar_alerta_por_clave(clave: str) -> bool:
    alertas = _cargar_alertas()
    partes = _timestamp_partes()
    cambiado = False
    for alerta in alertas:
        if alerta.get("clave") != clave or alerta.get("estado") != ESTADO_ACTIVA:
            continue
        alerta["estado"] = ESTADO_RESUELTA
        alerta["resuelta_en"] = partes["timestamp"]
        alerta["actualizado_en"] = partes["timestamp"]
        cambiado = True
    if cambiado:
        _guardar_alertas(alertas)
    return cambiado


def cerrar_alertas_panel(panel: str) -> int:
    alertas = _cargar_alertas()
    partes = _timestamp_partes()
    total = 0
    for alerta in alertas:
        if normalizar_texto(alerta.get("panel", "")) != normalizar_texto(panel):
            continue
        if alerta.get("estado") != ESTADO_ACTIVA:
            continue
        alerta["estado"] = ESTADO_RESUELTA
        alerta["resuelta_en"] = partes["timestamp"]
        alerta["actualizado_en"] = partes["timestamp"]
        total += 1
    if total:
        _guardar_alertas(alertas)
    return total
