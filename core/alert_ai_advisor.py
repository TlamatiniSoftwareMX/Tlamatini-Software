from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from core.local_llm import LocalLLMConfig, obtener_local_llm_provider
from core.logs import registrar_log
from core.memoria import guardar_seccion, obtener_seccion
from core.texto import normalizar_texto


SECCION_ALERTAS_AI = "alertas_ai_cache"

SYSTEM_PROMPT = (
    "Eres el asistente operativo offline de TLAMATINI para contexto prepper, SHTF y resiliencia. "
    "Responde breve, práctico y seguro. Usa solo los datos reales recibidos. "
    "No inventes cantidades, recursos ni condiciones. Si faltan datos, dilo claramente. "
    "No des diagnósticos médicos ni instrucciones peligrosas. Prioriza seguridad y confirmación del usuario."
)


PROMPTS_INTERNOS = {
    "agua": (
        "Actúa como asistente operativo de TLAMATINI. Con los siguientes datos reales: agua disponible, "
        "número de personas, consumo estimado y días restantes. Da recomendaciones breves, prácticas y seguras. "
        "No inventes datos. Si falta información, indícalo."
    ),
    "comida": (
        "Con estos datos reales de inventario y perfiles, genera recomendaciones de racionamiento y revisión de "
        "suministros. No inventes alimentos ni cantidades. Mantén la respuesta breve y operativa."
    ),
    "medicamentos": (
        "Da recomendaciones generales y conservadoras. No diagnostiques. No indiques dosis peligrosas. "
        "Sugiere revisar etiqueta, fecha de vencimiento y consultar profesional si es posible."
    ),
    "energia": (
        "Con datos reales de energía, sugiere ahorro, priorización de cargas y revisión de baterías o paneles. "
        "No inventes capacidad ni tiempos si no están presentes."
    ),
    "salud": (
        "Explica riesgos de forma conservadora y segura. No des diagnóstico definitivo. Sugiere revisar plan, "
        "biblioteca o aprendizaje relacionado y buscar ayuda profesional cuando aplique."
    ),
    "sistema": (
        "Resume la alerta técnica sin dramatismo. Sugiere pasos simples y seguros: reintentar, revisar logs o "
        "reiniciar el módulo afectado. No inventes causas."
    ),
    "emergency": (
        "Resume por qué varias alertas críticas justifican sugerir modo emergencia. Da pasos cortos de priorización. "
        "No ordenes activarlo automáticamente."
    ),
    "general": (
        "Resume la alerta y da recomendaciones breves, prácticas y seguras usando solo los datos reales recibidos."
    ),
}


def _cache() -> Dict[str, Dict]:
    datos = obtener_seccion(SECCION_ALERTAS_AI, {})
    return datos if isinstance(datos, dict) else {}


def _guardar_cache(datos: Dict[str, Dict]) -> None:
    guardar_seccion(SECCION_ALERTAS_AI, datos)


def _firma_alerta(alerta: Dict) -> str:
    return "||".join(
        [
            str(alerta.get("clave", "")).strip(),
            str(alerta.get("titulo", "")).strip(),
            str(alerta.get("descripcion", "")).strip(),
            str(alerta.get("actualizado_en", "")).strip() or str(alerta.get("timestamp", "")).strip(),
        ]
    )


def gemma_disponible() -> Tuple[bool, str]:
    try:
        return obtener_local_llm_provider().is_available()
    except Exception as exc:
        return False, f"No se pudo verificar Gemma local: {exc}"


def _prompt_id(alerta: Dict) -> str:
    tipo = normalizar_texto(alerta.get("tipo", ""))
    if tipo in {"agua", "comida", "medicamentos", "energia", "salud", "sistema"}:
        return tipo
    if tipo in {"emergency", "emergencia"}:
        return "emergency"
    if tipo in {"perfil_medico", "medico", "medica"}:
        return "salud"
    return "general"


def recomendaciones_por_reglas(alerta: Dict) -> Dict[str, List[str] | str]:
    tipo = _prompt_id(alerta)
    meta = alerta.get("metadata", {}) if isinstance(alerta.get("metadata", {}), dict) else {}
    titulo = str(alerta.get("titulo", "Alerta")).strip()
    descripcion = str(alerta.get("descripcion", "")).strip()

    if tipo == "agua":
        dias = meta.get("dias_autonomia")
        resumen = descripcion or "Autonomía de agua reducida."
        sugerencias = [
            "Reducir consumo no esencial y revisar racionamiento diario.",
            "Verificar filtros, pastillas potabilizadoras y depósitos disponibles.",
            "Confirmar puntos de agua y rutas seguras antes de mover recursos.",
        ]
        pasos = [
            "Abrir inventario de agua y validar cantidades reales.",
            "Revisar mapa y planes de abastecimiento.",
            "Registrar decisión operativa en bitácora si se aplica racionamiento.",
        ]
        if dias is None:
            resumen += " Faltan datos para una estimación más precisa."
        return {"summary": resumen, "suggestions": sugerencias, "steps": pasos}

    if tipo == "comida":
        return {
            "summary": descripcion or "Reserva de comida reducida para el grupo actual.",
            "suggestions": [
                "Revisar inventario de alimentos y prioridades de consumo.",
                "Separar reservas críticas de consumo inmediato.",
                "Evaluar racionamiento y faltantes antes de reabastecer.",
            ],
            "steps": [
                "Abrir inventario de alimentos.",
                "Revisar plan de abastecimiento o contingencia.",
                "Registrar faltantes o ajustes en bitácora.",
            ],
        }

    if tipo == "medicamentos":
        return {
            "summary": descripcion or "Hay un medicamento o insumo médico próximo a vencer.",
            "suggestions": [
                "Revisar etiqueta, lote y fecha exacta de vencimiento.",
                "Separar insumos vencidos o por vencer del stock vigente.",
                "Programar reposición o recordatorio de revisión.",
            ],
            "steps": [
                "Abrir inventario médico.",
                "Verificar botiquín y reemplazos disponibles.",
                "Registrar la revisión en bitácora si se toma acción.",
            ],
        }

    if tipo == "energia":
        return {
            "summary": descripcion or "Se detectó una condición de energía que requiere atención.",
            "suggestions": [
                "Reducir cargas no críticas y priorizar equipos esenciales.",
                "Revisar baterías, paneles y conexiones antes de aumentar consumo.",
                "Confirmar capacidad útil real con la calculadora de energía.",
            ],
            "steps": [
                "Abrir herramienta de energía.",
                "Revisar inventario de energía y repuestos.",
                "Actualizar decisión operativa en bitácora si se cambia la carga.",
            ],
        }

    if tipo == "salud":
        return {
            "summary": descripcion or titulo or "Se detectó una condición médica o de perfil que requiere seguimiento.",
            "suggestions": [
                "Usar lenguaje conservador y no asumir diagnóstico.",
                "Revisar protocolos, medicamentos requeridos y recursos disponibles.",
                "Consultar profesional si es posible o si la condición empeora.",
            ],
            "steps": [
                "Abrir perfiles relacionados.",
                "Revisar plan o protocolo aplicable.",
                "Consultar biblioteca o aprendizaje relacionado.",
            ],
        }

    if tipo == "sistema":
        return {
            "summary": descripcion or "Se detectó un error interno o fallo operativo.",
            "suggestions": [
                "Reintentar la acción una sola vez antes de escalar.",
                "Revisar logs del sistema para identificar el módulo afectado.",
                "Evitar acciones destructivas hasta confirmar la causa.",
            ],
            "steps": [
                "Reintentar o refrescar el módulo afectado.",
                "Registrar seguimiento técnico en bitácora.",
                "Mantener el resto del sistema operativo si el fallo es aislado.",
            ],
        }

    if tipo == "emergency":
        return {
            "summary": descripcion or "Hay varias condiciones críticas simultáneas.",
            "suggestions": [
                "Priorizar agua, comida, salud y conectividad crítica.",
                "Reducir navegación por módulos no esenciales.",
                "Revisar planes activos antes de mover recursos.",
            ],
            "steps": [
                "Confirmar si procede activar modo emergencia.",
                "Registrar la decisión en bitácora.",
                "Abrir módulos críticos primero.",
            ],
        }

    return {
        "summary": descripcion or titulo or "Alerta operativa.",
        "suggestions": [
            "Verificar el dato real que originó la alerta.",
            "Priorizar seguridad y recursos críticos.",
            "Registrar la decisión si se ejecuta una acción.",
        ],
        "steps": [
            "Abrir el módulo relacionado.",
            "Revisar contexto y recursos disponibles.",
            "Confirmar cualquier acción importante antes de ejecutarla.",
        ],
    }


def _serializar_contexto(alerta: Dict) -> str:
    meta = alerta.get("metadata", {}) if isinstance(alerta.get("metadata", {}), dict) else {}
    lineas = [
        f"Título: {alerta.get('titulo', '')}",
        f"Tipo: {alerta.get('tipo', '')}",
        f"Nivel: {alerta.get('nivel', '')}",
        f"Origen: {alerta.get('origen', '')}",
        f"Descripción: {alerta.get('descripcion', '')}",
    ]
    for clave in (
        "dias_autonomia",
        "litros_disponibles",
        "personas_consideradas",
        "litros_dia_grupo",
        "total_kcal",
        "total_raciones",
        "dias_autonomia_raciones",
        "nombre",
        "perfil",
        "medicamento",
    ):
        if clave in meta and meta.get(clave) not in (None, "", []):
            lineas.append(f"{clave}: {meta.get(clave)}")
    if meta:
        extras = []
        for clave, valor in meta.items():
            if clave in {
                "dias_autonomia",
                "litros_disponibles",
                "personas_consideradas",
                "litros_dia_grupo",
                "total_kcal",
                "total_raciones",
                "dias_autonomia_raciones",
                "nombre",
                "perfil",
                "medicamento",
            }:
                continue
            if isinstance(valor, (str, int, float)) and str(valor).strip():
                extras.append(f"{clave}: {valor}")
        if extras:
            lineas.append("Datos extra:")
            lineas.extend(extras[:8])
    return "\n".join(lineas)


def pedir_recomendacion_ia(alerta: Dict, forzar: bool = False) -> Dict[str, str | bool]:
    clave = str(alerta.get("clave", "")).strip() or str(alerta.get("id", "")).strip()
    firma = _firma_alerta(alerta)
    cache = _cache()
    actual = cache.get(clave, {}) if clave else {}
    if not forzar and actual.get("firma") == firma and str(actual.get("texto", "")).strip():
        return {
            "ok": True,
            "source": actual.get("source", "cache"),
            "texto": actual.get("texto", ""),
            "prompt_id": actual.get("prompt_id", "general"),
            "cached": True,
        }

    disponible, detalle = gemma_disponible()
    if not disponible:
        return {
            "ok": False,
            "source": "fallback",
            "texto": "",
            "detalle": detalle,
            "prompt_id": _prompt_id(alerta),
            "cached": False,
        }

    prompt_id = _prompt_id(alerta)
    prompt = (
        f"{PROMPTS_INTERNOS[prompt_id]}\n\n"
        "Devuelve una respuesta breve con este formato exacto:\n"
        "RESUMEN: ...\n"
        "IMPORTA: ...\n"
        "PASOS: - ... ; - ... ; - ...\n"
        "CHECKLIST: - ... ; - ... ; - ...\n\n"
        f"DATOS REALES:\n{_serializar_contexto(alerta)}"
    )
    try:
        proveedor = obtener_local_llm_provider()
        # Se aumenta el timeout y se deja que el provider maneje el modelo por defecto para mayor estabilidad
        texto = proveedor.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            config=LocalLLMConfig(max_tokens=280, temperature=0.2, top_p=0.85, timeout=30),
        ).strip()
        if not texto:
            raise RuntimeError("Gemma no devolvió texto.")
        if clave:
            cache[clave] = {
                "firma": firma,
                "texto": texto,
                "source": "gemma",
                "prompt_id": prompt_id,
                "generado_en": datetime.now().isoformat(timespec="seconds"),
            }
            _guardar_cache(cache)
        registrar_log("dashboard", f"Consejo IA generado para alerta: {alerta.get('titulo', '')}", "alert_ai")
        return {"ok": True, "source": "gemma", "texto": texto, "prompt_id": prompt_id, "cached": False}
    except Exception as exc:
        # CAMBIO CLAVE: Se degrada a 'warning' para no bloquear el dashboard con alertas rojas si la IA falla
        registrar_log("warning", f"IA Advisor en espera: {exc}", "alert_ai")
        return {
            "ok": False,
            "source": "fallback",
            "texto": "",
            "detalle": str(exc),
            "prompt_id": prompt_id,
            "cached": False,
        }