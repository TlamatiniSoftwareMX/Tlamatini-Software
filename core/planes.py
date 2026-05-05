from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.logs import registrar_log
from core.memoria import obtener_seccion, guardar_seccion


SECCION_PLANES = "planes"

SECCIONES_SIMPLE = {
    "datos_generales": [
        "nombre_del_plan",
        "fecha_de_elaboracion",
        "version",
        "elaborado_por",
        "grupo_o_familia",
        "ubicacion_general",
        "escenario_principal",
    ],
    "objetivo_plan": [
        "objetivo_general",
        "objetivos_especificos",
    ],
    "alcance": [
        "personas_cubiertas",
        "periodo_estimado_de_aplicacion",
        "situaciones_en_las_que_aplica",
        "limitaciones_del_plan",
    ],
    "descripcion_zona": [
        "tipo_de_zona",
        "descripcion_general",
        "accesos_y_salidas",
        "puntos_criticos",
        "fuentes_de_agua",
        "areas_de_resguardo",
        "zonas_inseguras",
        "condiciones_climaticas_relevantes",
        "cercania_a_riesgos",
    ],
    "rutas_evac": [
        "ruta_principal",
        "ruta_secundaria",
        "punto_de_reunion_1",
        "punto_de_reunion_2",
        "medios_de_transporte",
        "tiempo_estimado",
        "obstaculos_probables",
        "criterios_para_activar_evac",
        "destino_temporal",
        "destino_alternativo",
        "observaciones",
    ],
    "revisiones": [
        "periodicidad_general",
        "fecha_ultima_revision",
        "proxima_revision",
        "responsable_de_revision",
        "cambios_realizados",
        "lecciones_aprendidas",
    ],
}

SECCIONES_LISTA = {
    "identificacion_riesgos": [
        "tipo_de_riesgo",
        "descripcion",
        "probabilidad",
        "impacto",
        "senales_de_alerta",
        "medidas_preventivas",
        "respuesta_inicial",
    ],
    "organizacion_responsables": [
        "nombre",
        "funcion",
        "lugar_o_puesto",
        "responsabilidad_principal",
        "responsabilidad_secundaria",
        "contacto",
        "observaciones",
    ],
    "recursos_disponibles": [
        "categoria_recurso",
        "nombre_recurso",
        "cantidad",
        "unidad",
        "ubicacion",
        "responsable",
        "estado",
        "fecha_de_revision",
        "observaciones",
    ],
    "procedimientos_actuacion": [
        "escenario",
        "fase",
        "activacion_del_plan",
        "procedimiento_inicial",
        "aseguramiento_de_personas",
        "resguardo_de_recursos_clave",
        "comunicacion_interna",
        "comunicacion_externa",
        "decision_de_permanecer_o_evacuar",
        "procedimiento_de_evac",
        "procedimiento_de_refugio_en_sitio",
        "procedimiento_post_evento",
        "criterios_de_cierre_o_retorno",
    ],
    "simulacros": [
        "tipo_de_simulacro",
        "frecuencia",
        "responsables",
        "ultimo_simulacro",
        "hallazgos",
        "mejoras_requeridas",
    ],
}

ETIQUETAS_SECCIONES = {
    "datos_generales": "1. Datos generales del plan",
    "objetivo_plan": "2. Objetivo del plan",
    "alcance": "3. Alcance",
    "descripcion_zona": "4. Descripción del lugar/zona",
    "identificacion_riesgos": "5. Identificación de riesgos",
    "organizacion_responsables": "6. Organización y responsables",
    "recursos_disponibles": "7. Recursos disponibles",
    "rutas_evac": "8. Rutas de evacuación",
    "procedimientos_actuacion": "9. Procedimientos de actuación",
    "simulacros": "10. Simulacros (frecuencia)",
    "revisiones": "11. Revisiones (periodicidad)",
}


def _ahora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _hoy() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ahora_id(prefijo: str) -> str:
    return f"{prefijo}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _texto(valor) -> str:
    return str(valor or "").strip()


def _normalizar_simple(data: Dict, claves: List[str]) -> Dict[str, str]:
    return {clave: _texto(data.get(clave, "")) for clave in claves}


def _normalizar_lista(items, claves: List[str], prefijo: str) -> List[Dict[str, str]]:
    if not isinstance(items, list):
        return []

    normalizados = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fila = {"id": _texto(item.get("id")) or _ahora_id(prefijo)}
        tiene_contenido = False
        for clave in claves:
            valor = _texto(item.get(clave, ""))
            fila[clave] = valor
            if valor:
                tiene_contenido = True
        if tiene_contenido:
            normalizados.append(fila)
    return normalizados


def crear_plan_vacio() -> Dict:
    return {
        "id": _ahora_id("PLAN"),
        "estado": "borrador",
        "fecha_creacion": _ahora(),
        "fecha_actualizacion": _ahora(),
        "datos_generales": {
            "nombre_del_plan": "",
            "fecha_de_elaboracion": _hoy(),
            "version": "1.0",
            "elaborado_por": "",
            "grupo_o_familia": "",
            "ubicacion_general": "",
            "escenario_principal": "",
        },
        "objetivo_plan": {clave: "" for clave in SECCIONES_SIMPLE["objetivo_plan"]},
        "alcance": {clave: "" for clave in SECCIONES_SIMPLE["alcance"]},
        "descripcion_zona": {clave: "" for clave in SECCIONES_SIMPLE["descripcion_zona"]},
        "identificacion_riesgos": [],
        "organizacion_responsables": [],
        "recursos_disponibles": [],
        "rutas_evac": {clave: "" for clave in SECCIONES_SIMPLE["rutas_evac"]},
        "procedimientos_actuacion": [],
        "simulacros": [],
        "revisiones": {clave: "" for clave in SECCIONES_SIMPLE["revisiones"]},
    }


def normalizar_plan(plan_raw: Optional[Dict]) -> Dict:
    base = crear_plan_vacio()
    plan_raw = plan_raw or {}

    plan = deepcopy(base)
    plan["id"] = _texto(plan_raw.get("id")) or base["id"]
    plan["estado"] = _texto(plan_raw.get("estado")) or "borrador"
    if plan["estado"] not in {"borrador", "guardado"}:
        plan["estado"] = "borrador"
    plan["fecha_creacion"] = _texto(plan_raw.get("fecha_creacion")) or base["fecha_creacion"]
    plan["fecha_actualizacion"] = _texto(plan_raw.get("fecha_actualizacion")) or base["fecha_actualizacion"]

    for seccion, claves in SECCIONES_SIMPLE.items():
        plan[seccion] = _normalizar_simple(plan_raw.get(seccion, {}), claves)

    for seccion, claves in SECCIONES_LISTA.items():
        prefijo = {
            "identificacion_riesgos": "RIESGO",
            "organizacion_responsables": "RESP",
            "recursos_disponibles": "REC",
            "procedimientos_actuacion": "PROC",
            "simulacros": "SIM",
        }[seccion]
        plan[seccion] = _normalizar_lista(plan_raw.get(seccion, []), claves, prefijo)

    return plan


def validar_plan(plan: Dict, estado_destino: str = "guardado") -> Tuple[bool, str]:
    datos = normalizar_plan(plan)
    nombre = datos["datos_generales"].get("nombre_del_plan", "")
    if estado_destino == "guardado" and not nombre:
        return False, "Escribe el nombre del plan antes de guardarlo."
    return True, ""


def listar_planes() -> List[Dict]:
    planes = obtener_seccion(SECCION_PLANES, [])
    if not isinstance(planes, list):
        return []
    normalizados = [normalizar_plan(plan) for plan in planes if isinstance(plan, dict)]
    normalizados.sort(
        key=lambda plan: (
            plan.get("fecha_actualizacion", ""),
            plan.get("datos_generales", {}).get("nombre_del_plan", "").lower(),
        ),
        reverse=True,
    )
    return normalizados


def obtener_plan(plan_id: str) -> Optional[Dict]:
    plan_id = _texto(plan_id)
    if not plan_id:
        return None
    for plan in listar_planes():
        if plan.get("id") == plan_id:
            return plan
    return None


def guardar_plan(plan_raw: Dict, estado_destino: str = "guardado") -> Dict:
    plan = normalizar_plan(plan_raw)
    ok, mensaje = validar_plan(plan, estado_destino=estado_destino)
    if not ok:
        raise ValueError(mensaje)

    plan["estado"] = "guardado" if estado_destino == "guardado" else "borrador"
    plan["fecha_actualizacion"] = _ahora()
    if not plan["fecha_creacion"]:
        plan["fecha_creacion"] = plan["fecha_actualizacion"]

    planes = listar_planes()
    actualizado = False
    for indice, existente in enumerate(planes):
        if existente.get("id") == plan["id"]:
            plan["fecha_creacion"] = existente.get("fecha_creacion", plan["fecha_creacion"])
            planes[indice] = plan
            actualizado = True
            break
    if not actualizado:
        planes.append(plan)

    guardar_seccion(SECCION_PLANES, planes)
    registrar_log(
        "sistema",
        f"Plan de emergencia {'actualizado' if actualizado else 'creado'}: {titulo_plan(plan)}",
        "planes",
    )
    return plan


def eliminar_plan(plan_id: str) -> bool:
    plan_id = _texto(plan_id)
    if not plan_id:
        return False
    planes = listar_planes()
    nuevos = [plan for plan in planes if plan.get("id") != plan_id]
    if len(nuevos) == len(planes):
        return False
    guardar_seccion(SECCION_PLANES, nuevos)
    registrar_log("sistema", f"Plan de emergencia eliminado: {plan_id}", "planes")
    return True


def titulo_plan(plan: Dict) -> str:
    plan = normalizar_plan(plan)
    titulo = plan["datos_generales"].get("nombre_del_plan", "")
    if titulo:
        return titulo
    return "Plan sin nombre"


def resumen_plan(plan: Dict) -> Dict[str, str]:
    plan = normalizar_plan(plan)
    datos = plan["datos_generales"]
    return {
        "id": plan["id"],
        "titulo": titulo_plan(plan),
        "estado": plan.get("estado", "borrador"),
        "escenario_principal": datos.get("escenario_principal", ""),
        "grupo_o_familia": datos.get("grupo_o_familia", ""),
        "fecha_actualizacion": plan.get("fecha_actualizacion", ""),
    }


def _lineas_simple(titulo: str, data: Dict[str, str]) -> List[str]:
    lineas = [titulo]
    for clave, valor in data.items():
        lineas.append(f"- {clave}: {valor or '-'}")
    lineas.append("")
    return lineas


def _lineas_lista(titulo: str, items: List[Dict], claves: List[str]) -> List[str]:
    lineas = [titulo]
    if not items:
        lineas.append("- Sin registros")
        lineas.append("")
        return lineas

    for indice, item in enumerate(items, start=1):
        lineas.append(f"- Registro {indice}")
        for clave in claves:
            lineas.append(f"  {clave}: {item.get(clave, '') or '-'}")
    lineas.append("")
    return lineas


def renderizar_plan_texto(plan: Dict) -> str:
    plan = normalizar_plan(plan)
    lineas: List[str] = []

    for seccion in [
        "datos_generales",
        "objetivo_plan",
        "alcance",
        "descripcion_zona",
        "identificacion_riesgos",
        "organizacion_responsables",
        "recursos_disponibles",
        "rutas_evac",
        "procedimientos_actuacion",
        "simulacros",
        "revisiones",
    ]:
        titulo = ETIQUETAS_SECCIONES[seccion]
        if seccion in SECCIONES_SIMPLE:
            lineas.extend(_lineas_simple(titulo, plan.get(seccion, {})))
        else:
            lineas.extend(_lineas_lista(titulo, plan.get(seccion, []), SECCIONES_LISTA[seccion]))

    return "\n".join(lineas).strip() + "\n"


def exportar_plan_texto(plan: Dict, ruta_destino: Path) -> Path:
    ruta = Path(ruta_destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(renderizar_plan_texto(plan), encoding="utf-8")
    registrar_log("sistema", f"Plan exportado: {ruta}", "planes")
    return ruta
