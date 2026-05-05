from datetime import datetime
from typing import Dict, List, Optional

from core.inventario import listar_inventario
from core.logs import registrar_log
from core.memoria import guardar_seccion, obtener_seccion
from core.texto import normalizar_texto


UNIDADES_EQUIVALENTES = {
    "l": ("l", 1.0),
    "litro": ("l", 1.0),
    "litros": ("l", 1.0),
    "lt": ("l", 1.0),
    "ml": ("l", 0.001),
    "kg": ("kg", 1.0),
    "kilo": ("kg", 1.0),
    "kilos": ("kg", 1.0),
    "g": ("kg", 0.001),
    "gr": ("kg", 0.001),
    "gramo": ("kg", 0.001),
    "gramos": ("kg", 0.001),
    "racion": ("racion", 1.0),
    "raciones": ("racion", 1.0),
    "porcion": ("racion", 1.0),
    "porciones": ("racion", 1.0),
    "unidad": ("unidad", 1.0),
    "unidades": ("unidad", 1.0),
    "pieza": ("unidad", 1.0),
    "piezas": ("unidad", 1.0),
    "pzas": ("unidad", 1.0),
    "tableta": ("unidad", 1.0),
    "tabletas": ("unidad", 1.0),
    "capsula": ("unidad", 1.0),
    "capsulas": ("unidad", 1.0),
    "cápsula": ("unidad", 1.0),
    "cápsulas": ("unidad", 1.0),
    "ampolleta": ("unidad", 1.0),
    "ampolletas": ("unidad", 1.0),
    "frasco": ("unidad", 1.0),
    "frascos": ("unidad", 1.0),
    "mg": ("mg", 1.0),
    "mcg": ("mg", 0.001),
    "ug": ("mg", 0.001),
    "ui": ("ui", 1.0),
    "meq": ("meq", 1.0),
}


PALABRAS_AGUA = ["agua", "hidratacion", "hidratación", "suero", "bebida"]
PALABRAS_ALIMENTO = ["alimento", "comida", "despensa", "racion", "víveres", "viveres"]
PALABRAS_MEDICAMENTO = ["medicamento", "medicina", "farmaco", "fármaco", "botiquin", "botiquín"]


def _normalizar_texto(texto: str) -> str:
    return normalizar_texto(texto)


def _to_float(valor) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except Exception:
        return 0.0


def _obtener_personas() -> List[Dict]:
    personas = obtener_seccion("personas", [])
    return personas if isinstance(personas, list) else []


def _guardar_personas(personas: List[Dict]) -> None:
    guardar_seccion("personas", personas)


def _normalizar_unidad(unidad: str):
    return UNIDADES_EQUIVALENTES.get(_normalizar_texto(unidad))


def _convertir_a_base(cantidad: float, unidad: str):
    datos = _normalizar_unidad(unidad)
    if not datos:
        return None, None
    unidad_base, factor = datos
    return cantidad * factor, unidad_base


def _coincide_palabras(item: Dict, palabras: List[str]) -> bool:
    texto = " ".join(
        [
            _normalizar_texto(item.get("categoria", "")),
            _normalizar_texto(item.get("subcategoria", "")),
            _normalizar_texto(item.get("nombre", "")),
            _normalizar_texto(item.get("tipo", "")),
            _normalizar_texto(item.get("proposito", "")),
        ]
    )
    return any(p in texto for p in palabras)


def _cantidad_item_en_base(item: Dict):
    cantidad = _to_float(item.get("cantidad", 0))
    unidad = item.get("unidad", "")
    return _convertir_a_base(cantidad, unidad)


def _calcular_agua_disponible_litros(inventario: List[Dict]) -> float:
    total = 0.0
    for item in inventario:
        if not _coincide_palabras(item, PALABRAS_AGUA):
            continue
        cantidad_base, unidad_base = _cantidad_item_en_base(item)
        if cantidad_base is None:
            continue
        if unidad_base == "l":
            total += cantidad_base
    return total


def _calcular_comida_disponible_raciones(inventario: List[Dict]) -> float:
    total = 0.0
    for item in inventario:
        if not _coincide_palabras(item, PALABRAS_ALIMENTO):
            continue

        cantidad = _to_float(item.get("cantidad", 0))
        unidad = _normalizar_texto(item.get("unidad", ""))

        if unidad in {"racion", "raciones", "porcion", "porciones"}:
            total += cantidad
        elif unidad in {"pieza", "piezas", "pzas", "unidad", "unidades"}:
            total += cantidad

    return total


def _buscar_stock_medicamento(nombre_medicamento: str, inventario: List[Dict]) -> List[Dict]:
    nombre_n = _normalizar_texto(nombre_medicamento)
    coincidencias = []

    for item in inventario:
        if not _coincide_palabras(item, PALABRAS_MEDICAMENTO):
            continue

        texto = " ".join(
            [
                _normalizar_texto(item.get("nombre", "")),
                _normalizar_texto(item.get("composicion", "")),
                _normalizar_texto(item.get("observaciones", "")),
            ]
        )
        if nombre_n and (nombre_n in texto or texto in nombre_n):
            coincidencias.append(item)

    return coincidencias


def _valores_default_por_actividad(actividad: str):
    actividad_n = _normalizar_texto(actividad)
    if actividad_n == "alta":
        return 3.5, 1.5
    if actividad_n == "baja":
        return 2.0, 0.8
    return 2.7, 1.0


def _calcular_edad_desde_fecha(fecha_nacimiento: str) -> int:
    texto = str(fecha_nacimiento or "").strip()
    if not texto:
        return 0
    try:
        nacimiento = datetime.strptime(texto, "%d-%m-%Y").date()
    except ValueError as exc:
        raise ValueError("La fecha de nacimiento debe ir como d-m-a, por ejemplo 07-04-1998.") from exc
    hoy = datetime.now().date()
    if nacimiento > hoy:
        raise ValueError("La fecha de nacimiento no puede ser futura.")
    edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
    return max(0, edad)


def _peso_referencia(edad: float, altura_cm: float, sexo: str) -> float:
    if altura_cm > 0:
        if edad and edad < 14:
            imc = 17.5
        elif edad and edad < 18:
            imc = 20.5
        else:
            imc = 22.0
        return imc * ((altura_cm / 100.0) ** 2)
    sexo_n = _normalizar_texto(sexo)
    return 70.0 if sexo_n.startswith("m") else 60.0


def estimar_calorias_diarias_persona(persona: Dict) -> float:
    edad = max(0.0, _to_float(persona.get("edad", 0)) or 0.0)
    altura = max(0.0, _to_float(persona.get("altura_cm", 0)) or 0.0)
    peso = max(0.0, _to_float(persona.get("peso_kg", 0)) or 0.0)
    sexo = str(persona.get("sexo", "")).strip().lower()
    actividad = str(persona.get("actividad", "media")).strip().lower()

    if peso <= 0:
        peso = _peso_referencia(edad, altura, sexo)

    if edad < 3:
        base = peso * 95.0
    elif edad < 9:
        base = peso * 78.0
    elif edad < 14:
        base = peso * (55.0 if sexo.startswith("m") else 47.0)
    elif edad < 18:
        base = peso * (45.0 if sexo.startswith("m") else 40.0)
    else:
        if altura <= 0:
            altura = 170.0 if sexo.startswith("m") else 160.0
        if sexo.startswith("m"):
            base = 10 * peso + 6.25 * altura - 5 * edad + 5
        elif sexo.startswith("f"):
            base = 10 * peso + 6.25 * altura - 5 * edad - 161
        else:
            base_m = 10 * peso + 6.25 * altura - 5 * edad + 5
            base_f = 10 * peso + 6.25 * altura - 5 * edad - 161
            base = (base_m + base_f) / 2.0

    factor = {"baja": 1.2, "media": 1.45, "alta": 1.75}.get(actividad, 1.45)
    return max(1200.0, base * factor)


def estimar_agua_litros_diarios_persona(persona: Dict) -> float:
    edad = max(0.0, _to_float(persona.get("edad", 0)) or 0.0)
    altura = max(0.0, _to_float(persona.get("altura_cm", 0)) or 0.0)
    peso = max(0.0, _to_float(persona.get("peso_kg", 0)) or 0.0)
    sexo = str(persona.get("sexo", "")).strip().lower()
    actividad = str(persona.get("actividad", "media")).strip().lower()

    if peso <= 0:
        peso = _peso_referencia(edad, altura, sexo)

    if edad < 4:
        ml_por_kg = 85.0
    elif edad < 9:
        ml_por_kg = 70.0
    elif edad < 14:
        ml_por_kg = 55.0
    elif edad < 18:
        ml_por_kg = 45.0
    else:
        ml_por_kg = 35.0 if sexo.startswith("m") else 31.0 if sexo.startswith("f") else 33.0

    factor = {"baja": 0.95, "media": 1.0, "alta": 1.15}.get(actividad, 1.0)
    litros = (peso * ml_por_kg * factor) / 1000.0
    return max(1.0, round(litros, 2))


def estimar_consumo_diario_grupo(personas: Optional[List[Dict]] = None) -> Dict:
    perfiles = personas if personas is not None else listar_personas()
    perfiles = [persona for persona in perfiles if isinstance(persona, dict)]
    consumo_agua_total = sum(estimar_agua_litros_diarios_persona(persona) for persona in perfiles)
    consumo_comida_total = sum(estimar_calorias_diarias_persona(persona) for persona in perfiles)
    return {
        "personas_total": len(perfiles),
        "consumo_agua_total": consumo_agua_total,
        "consumo_comida_total": consumo_comida_total,
    }


def registrar_persona(
    nombre: str,
    rol: str = "",
    edad: int = 0,
    fecha_nacimiento: str = "",
    peso_kg: float = 0,
    altura_cm: float = 0,
    sexo: str = "",
    enfermedades: str = "",
    actividad: str = "media",
    agua_litros_dia: Optional[float] = None,
    raciones_comida_dia: Optional[float] = None,
    observaciones: str = "",
) -> Dict:
    agua_default, racion_default = _valores_default_por_actividad(actividad)
    fecha_nacimiento = str(fecha_nacimiento or "").strip()
    edad_calculada = _calcular_edad_desde_fecha(fecha_nacimiento) if fecha_nacimiento else int(edad or 0)

    persona = {
        "id": f"PER-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "nombre": nombre.strip(),
        "rol": rol.strip(),
        "edad": edad_calculada,
        "fecha_nacimiento": fecha_nacimiento,
        "peso_kg": float(peso_kg or 0),
        "altura_cm": float(altura_cm or 0),
        "sexo": sexo.strip(),
        "enfermedades": enfermedades.strip(),
        "actividad": actividad.strip().lower() or "media",
        "agua_litros_dia": float(agua_litros_dia if agua_litros_dia not in (None, "") else agua_default),
        "raciones_comida_dia": float(raciones_comida_dia if raciones_comida_dia not in (None, "") else racion_default),
        "observaciones": observaciones.strip(),
        "medicamentos_requeridos": [],
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    personas = _obtener_personas()
    personas.append(persona)
    _guardar_personas(personas)
    registrar_log("sistema", f"Perfil registrado: {persona['nombre']}", "perfiles")
    return persona


def actualizar_persona(
    persona_id: str,
    nombre: str,
    rol: str = "",
    edad: int = 0,
    fecha_nacimiento: str = "",
    peso_kg: float = 0,
    altura_cm: float = 0,
    sexo: str = "",
    enfermedades: str = "",
    actividad: str = "media",
    agua_litros_dia: Optional[float] = None,
    raciones_comida_dia: Optional[float] = None,
    observaciones: str = "",
) -> bool:
    personas = _obtener_personas()
    agua_default, racion_default = _valores_default_por_actividad(actividad)
    fecha_nacimiento = str(fecha_nacimiento or "").strip()
    edad_calculada = _calcular_edad_desde_fecha(fecha_nacimiento) if fecha_nacimiento else int(edad or 0)

    for persona in personas:
        if persona.get("id") != persona_id:
            continue

        persona["nombre"] = nombre.strip()
        persona["rol"] = rol.strip()
        persona["edad"] = edad_calculada
        persona["fecha_nacimiento"] = fecha_nacimiento
        persona["peso_kg"] = float(peso_kg or 0)
        persona["altura_cm"] = float(altura_cm or 0)
        persona["sexo"] = sexo.strip()
        persona["enfermedades"] = enfermedades.strip()
        persona["actividad"] = actividad.strip().lower() or "media"
        persona["agua_litros_dia"] = float(agua_litros_dia if agua_litros_dia not in (None, "") else agua_default)
        persona["raciones_comida_dia"] = float(raciones_comida_dia if raciones_comida_dia not in (None, "") else racion_default)
        persona["observaciones"] = observaciones.strip()
        _guardar_personas(personas)
        registrar_log("sistema", f"Perfil actualizado: {persona['nombre']}", "perfiles")
        return True

    return False


def listar_personas() -> List[Dict]:
    return _obtener_personas()


def obtener_persona(persona_id: str) -> Optional[Dict]:
    for persona in _obtener_personas():
        if persona.get("id") == persona_id:
            return persona
    return None


def eliminar_persona(persona_id: str) -> bool:
    personas = _obtener_personas()
    nuevas = [p for p in personas if p.get("id") != persona_id]
    if len(nuevas) == len(personas):
        return False

    _guardar_personas(nuevas)
    registrar_log("sistema", f"Perfil eliminado: {persona_id}", "perfiles")
    return True


def agregar_medicamento_requerido(
    persona_id: str,
    nombre: str,
    cantidad_diaria: float,
    unidad: str,
    formula: str = "",
    indicacion: str = "",
    gramaje: str = "",
    gramaje_1: str = "",
    gramaje_2: str = "",
    observaciones: str = "",
) -> bool:
    personas = _obtener_personas()

    for persona in personas:
        if persona.get("id") != persona_id:
            continue

        meds = persona.setdefault("medicamentos_requeridos", [])
        meds.append(
            {
                "id": f"PMED-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                "nombre": nombre.strip(),
                "cantidad_diaria": float(cantidad_diaria or 0),
                "unidad": unidad.strip(),
                "formula": formula.strip() or gramaje.strip() or " ".join(x for x in [gramaje_1.strip(), gramaje_2.strip()] if x),
                "indicacion": indicacion.strip(),
                "gramaje": gramaje.strip() or " ".join(x for x in [gramaje_1.strip(), gramaje_2.strip()] if x),
                "gramaje_1": gramaje_1.strip(),
                "gramaje_2": gramaje_2.strip(),
                "observaciones": observaciones.strip(),
            }
        )
        _guardar_personas(personas)
        registrar_log("sistema", f"Medicamento agregado a perfil {persona['nombre']}: {nombre}", "perfiles")
        return True

    return False


def establecer_medicamentos_requeridos(persona_id: str, medicamentos: List[Dict]) -> bool:
    personas = _obtener_personas()
    for persona in personas:
        if persona.get("id") != persona_id:
            continue

        nuevos = []
        for medicamento in medicamentos or []:
            nombre = str(medicamento.get("nombre", "")).strip()
            if not nombre:
                continue
            nuevos.append(
                {
                    "id": medicamento.get("id") or f"PMED-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    "nombre": nombre,
                    "cantidad_diaria": float(medicamento.get("cantidad_diaria", 0) or 0),
                    "unidad": str(medicamento.get("unidad", "")).strip(),
                    "formula": str(medicamento.get("formula", "")).strip()
                    or str(medicamento.get("gramaje", "")).strip()
                    or " ".join(
                        x
                        for x in [
                            str(medicamento.get("gramaje_1", "")).strip(),
                            str(medicamento.get("gramaje_2", "")).strip(),
                        ]
                        if x
                    ),
                    "indicacion": str(medicamento.get("indicacion", "")).strip(),
                    "gramaje": str(medicamento.get("gramaje", "")).strip()
                    or " ".join(
                        x
                        for x in [
                            str(medicamento.get("gramaje_1", "")).strip(),
                            str(medicamento.get("gramaje_2", "")).strip(),
                        ]
                        if x
                    ),
                    "gramaje_1": str(medicamento.get("gramaje_1", "")).strip(),
                    "gramaje_2": str(medicamento.get("gramaje_2", "")).strip(),
                    "observaciones": str(medicamento.get("observaciones", "")).strip(),
                }
            )

        persona["medicamentos_requeridos"] = nuevos
        _guardar_personas(personas)
        registrar_log("sistema", f"Medicamentos actualizados en perfil {persona['nombre']}", "perfiles")
        return True

    return False


def eliminar_medicamento_requerido(persona_id: str, medicamento_id: str) -> bool:
    personas = _obtener_personas()
    for persona in personas:
        if persona.get("id") != persona_id:
            continue

        meds = persona.get("medicamentos_requeridos", [])
        nuevos = [m for m in meds if m.get("id") != medicamento_id]
        if len(nuevos) == len(meds):
            return False

        persona["medicamentos_requeridos"] = nuevos
        _guardar_personas(personas)
        registrar_log("sistema", f"Medicamento eliminado de perfil {persona['nombre']}: {medicamento_id}", "perfiles")
        return True

    return False


def _calcular_dias_cobertura_medicamento(item: Dict, cantidad_diaria: float, unidad_diaria: str) -> Optional[float]:
    stock_base, unidad_base_stock = _cantidad_item_en_base(item)
    diaria_base, unidad_base_diaria = _convertir_a_base(float(cantidad_diaria or 0), unidad_diaria)

    if stock_base is None or diaria_base is None:
        return None
    if unidad_base_stock != unidad_base_diaria:
        return None
    if diaria_base <= 0:
        return None

    return stock_base / diaria_base


def calcular_autonomia_persona(persona_id: str) -> Dict:
    persona = obtener_persona(persona_id)
    if not persona:
        return {"ok": False, "mensaje": "Perfil no encontrado."}

    inventario = listar_inventario()
    agua_total_l = _calcular_agua_disponible_litros(inventario)
    comida_total_raciones = _calcular_comida_disponible_raciones(inventario)

    agua_dias = None
    if persona.get("agua_litros_dia", 0) > 0:
        agua_dias = agua_total_l / float(persona.get("agua_litros_dia", 0))

    comida_dias = None
    if persona.get("raciones_comida_dia", 0) > 0:
        comida_dias = comida_total_raciones / float(persona.get("raciones_comida_dia", 0))

    medicamentos_resultado = []
    for med in persona.get("medicamentos_requeridos", []):
        coincidencias = _buscar_stock_medicamento(med.get("nombre", ""), inventario)
        dias_totales = 0.0
        dias_encontrados = False

        for item in coincidencias:
            dias = _calcular_dias_cobertura_medicamento(
                item=item,
                cantidad_diaria=float(med.get("cantidad_diaria", 0) or 0),
                unidad_diaria=med.get("unidad", ""),
            )
            if dias is not None:
                dias_totales += dias
                dias_encontrados = True

        medicamentos_resultado.append(
            {
                "nombre": med.get("nombre", ""),
                "cantidad_diaria": med.get("cantidad_diaria", 0),
                "unidad": med.get("unidad", ""),
                "dias_cobertura": dias_totales if dias_encontrados else None,
                "coincidencias": [x.get("nombre", "") for x in coincidencias],
            }
        )

    cuellos = []
    if agua_dias is not None:
        cuellos.append(("agua", agua_dias))
    if comida_dias is not None:
        cuellos.append(("comida", comida_dias))
    for med in medicamentos_resultado:
        if med.get("dias_cobertura") is not None:
            cuellos.append((f"medicamento:{med['nombre']}", med["dias_cobertura"]))

    cuello_critico = min(cuellos, key=lambda x: x[1]) if cuellos else None

    return {
        "ok": True,
        "persona": persona,
        "agua_total_l": agua_total_l,
        "comida_total_raciones": comida_total_raciones,
        "agua_dias": agua_dias,
        "comida_dias": comida_dias,
        "medicamentos": medicamentos_resultado,
        "cuello_critico": cuello_critico,
    }


def calcular_autonomia_grupo() -> Dict:
    personas = listar_personas()
    inventario = listar_inventario()
    if not personas:
        return {"ok": False, "mensaje": "No hay perfiles registrados."}

    agua_total_l = _calcular_agua_disponible_litros(inventario)
    comida_total_raciones = _calcular_comida_disponible_raciones(inventario)
    consumo_estimado = estimar_consumo_diario_grupo(personas)
    consumo_agua_total = consumo_estimado["consumo_agua_total"]
    consumo_comida_total = consumo_estimado["consumo_comida_total"]

    agua_dias = (agua_total_l / consumo_agua_total) if consumo_agua_total > 0 else None
    comida_dias = (comida_total_raciones / consumo_comida_total) if consumo_comida_total > 0 else None

    return {
        "ok": True,
        "personas_total": len(personas),
        "agua_total_l": agua_total_l,
        "comida_total_raciones": comida_total_raciones,
        "consumo_agua_total": consumo_agua_total,
        "consumo_comida_total": consumo_comida_total,
        "agua_dias": agua_dias,
        "comida_dias": comida_dias,
        "personas": [
            {
                "id": p.get("id", ""),
                "nombre": p.get("nombre", ""),
                "rol": p.get("rol", ""),
                "agua_litros_dia": p.get("agua_litros_dia", 0),
                "raciones_comida_dia": p.get("raciones_comida_dia", 0),
                "medicamentos_requeridos": len(p.get("medicamentos_requeridos", [])),
            }
            for p in personas
        ],
    }
