from typing import Dict, List, Optional, Tuple

from core.perfiles import estimar_agua_litros_diarios_persona, estimar_calorias_diarias_persona
from core.texto import normalizar_texto


UNIDADES_RACIONES = {"racion", "raciones", "porcion", "porciones"}
UNIDADES_AGUA_LITROS = {"l", "lt", "litro", "litros"}
UNIDADES_AGUA_ML = {"ml", "mililitro", "mililitros"}


def _texto_item(item: Dict) -> str:
    return " ".join(
        normalizar_texto(item.get(clave, ""))
        for clave in ("categoria", "subcategoria", "nombre", "tipo", "proposito", "observaciones")
    )


def _to_float(valor) -> Optional[float]:
    try:
        return float(str(valor).strip().replace(",", "."))
    except Exception:
        return None


def _parse_measure(texto: str) -> Tuple[Optional[float], str]:
    bruto = str(texto or "").strip().lower().replace(",", ".")
    if not bruto:
        return None, ""

    partes = bruto.split()
    if len(partes) == 2:
        return _to_float(partes[0]), partes[1]

    for unidad in ("kg", "gr", "g", "mg", "ml", "lt", "l"):
        if bruto.endswith(unidad):
            valor = _to_float(bruto[: -len(unidad)].strip())
            return valor, {"gr": "g", "lt": "l"}.get(unidad, unidad)

    return _to_float(bruto), ""


def _personas_validas(personas: List[Dict]) -> List[Dict]:
    return [persona for persona in list(personas or []) if isinstance(persona, dict)]


def _perfiles_agua_litros_dia(persona: Dict) -> float:
    valor = _to_float(persona.get("agua_litros_dia"))
    if valor is not None and valor > 0:
        return valor
    return estimar_agua_litros_diarios_persona(persona)


def _perfiles_calorias_dia(persona: Dict) -> float:
    return estimar_calorias_diarias_persona(persona)


def _perfiles_raciones_dia(persona: Dict) -> float:
    valor = _to_float(persona.get("raciones_comida_dia"))
    if valor is not None and valor > 0:
        return valor
    actividad = normalizar_texto(persona.get("actividad", "media"))
    if actividad == "alta":
        return 1.5
    if actividad == "baja":
        return 0.8
    return 1.0


def estimar_agua_disponible_litros(items: List[Dict]) -> float:
    total = 0.0
    palabras = ("agua", "hidrat", "suero", "bebida")

    for item in list(items or []):
        texto = _texto_item(item)
        if not any(palabra in texto for palabra in palabras):
            continue

        cantidad = _to_float(item.get("cantidad"))
        if cantidad is None or cantidad <= 0:
            continue

        unidad = normalizar_texto(item.get("unidad", ""))
        contenido_valor, contenido_unidad = _parse_measure(item.get("peso_contenido", ""))

        if unidad in UNIDADES_AGUA_LITROS:
            total += cantidad
            continue
        if unidad in UNIDADES_AGUA_ML:
            total += cantidad / 1000.0
            continue

        if contenido_valor is not None and contenido_unidad in {"l", "ml"}:
            litros_por_unidad = contenido_valor if contenido_unidad == "l" else contenido_valor / 1000.0
            total += litros_por_unidad * cantidad

    return round(total, 2)


def estimar_reserva_agua(items: List[Dict], personas: List[Dict]) -> Dict:
    perfiles = _personas_validas(personas)
    litros_disponibles = estimar_agua_disponible_litros(items)

    if not perfiles:
        return {
            "value": f"{litros_disponibles:.1f} L" if litros_disponibles > 0 else "Sin datos",
            "subtitle": "Registra perfiles para calcular autonomía real",
            "percent": None,
            "litros_disponibles": litros_disponibles,
            "personas_consideradas": 0,
            "litros_dia_grupo": 0.0,
            "dias_autonomia": None,
        }

    litros_dia_grupo = round(sum(_perfiles_agua_litros_dia(persona) for persona in perfiles), 2)
    dias = (litros_disponibles / litros_dia_grupo) if litros_dia_grupo > 0 else None
    percent = None if dias is None else min(100, int((dias / 14.0) * 100))

    if dias is None:
        subtitle = f"{len(perfiles)} persona(s) · consumo diario no disponible"
    else:
        subtitle = f"{len(perfiles)} persona(s) · {litros_dia_grupo:.1f} L/día · autonomía {dias:.1f} días"

    return {
        "value": f"{litros_disponibles:.1f} L" if litros_disponibles > 0 else "0.0 L",
        "subtitle": subtitle,
        "percent": percent,
        "litros_disponibles": litros_disponibles,
        "personas_consideradas": len(perfiles),
        "litros_dia_grupo": litros_dia_grupo,
        "dias_autonomia": None if dias is None else round(dias, 2),
    }


def estimar_calorias_item(item: Dict) -> float:
    nutrimental = item.get("nutrimental", {})
    if not isinstance(nutrimental, dict):
        nutrimental = {}

    calorias = _to_float(nutrimental.get("calorias", ""))
    if calorias is None or calorias <= 0:
        return 0.0

    cantidad = _to_float(item.get("cantidad", "")) or 0.0
    porcion = _to_float(nutrimental.get("porcion", ""))
    contenido_valor, contenido_unidad = _parse_measure(item.get("peso_contenido", ""))

    if porcion and contenido_valor and contenido_unidad in {"g", "kg", "ml", "l"}:
        contenido_base = contenido_valor * (1000.0 if contenido_unidad in {"kg", "l"} else 1.0)
        kcal_por_unidad = calorias * (contenido_base / porcion)
        return round(kcal_por_unidad * max(0.0, cantidad), 2)

    if cantidad > 0:
        return round(calorias * cantidad, 2)
    return round(calorias, 2)


def estimar_reserva_comida(items: List[Dict], personas: List[Dict]) -> Dict:
    perfiles = _personas_validas(personas)
    total_kcal = 0.0
    total_raciones = 0.0

    for item in list(items or []):
        if normalizar_texto(item.get("categoria", "")) != "alimentos":
            continue

        total_kcal += estimar_calorias_item(item)

        unidad = normalizar_texto(item.get("unidad", ""))
        cantidad = _to_float(item.get("cantidad")) or 0.0
        if unidad in UNIDADES_RACIONES:
            total_raciones += cantidad

    if not perfiles:
        if total_kcal > 0:
            valor = f"{int(round(total_kcal)):,} kcal".replace(",", ".")
            subtitulo = "Registra perfiles para calcular autonomía"
        elif total_raciones > 0:
            valor = f"{total_raciones:.1f} raciones"
            subtitulo = "Registra perfiles para calcular autonomía"
        else:
            valor = "Sin datos"
            subtitulo = "Registra perfiles y alimentos con datos útiles"
        return {
            "value": valor,
            "subtitle": subtitulo,
            "percent": None,
            "personas_consideradas": 0,
            "total_kcal": round(total_kcal, 2),
            "total_raciones": round(total_raciones, 2),
            "calorias_dia_grupo": 0.0,
            "raciones_dia_grupo": 0.0,
            "dias_autonomia": None,
            "metodo": "sin_perfiles",
        }

    calorias_dia_grupo = round(sum(_perfiles_calorias_dia(persona) for persona in perfiles), 2)
    raciones_dia_grupo = round(sum(_perfiles_raciones_dia(persona) for persona in perfiles), 2)

    dias_kcal = (total_kcal / calorias_dia_grupo) if total_kcal > 0 and calorias_dia_grupo > 0 else None
    dias_raciones = (total_raciones / raciones_dia_grupo) if total_raciones > 0 and raciones_dia_grupo > 0 else None

    if dias_kcal is not None:
        valor = f"{int(round(total_kcal)):,} kcal".replace(",", ".")
        subtitulo = (
            f"{len(perfiles)} persona(s) · {int(round(calorias_dia_grupo)):,} kcal/día"
            f" · autonomía {dias_kcal:.1f} días"
        ).replace(",", ".")
        metodo = "kcal"
        dias = dias_kcal
    elif dias_raciones is not None:
        valor = f"{total_raciones:.1f} raciones"
        subtitulo = (
            f"{len(perfiles)} persona(s) · {raciones_dia_grupo:.1f} raciones/día"
            f" · autonomía {dias_raciones:.1f} días"
        )
        metodo = "raciones"
        dias = dias_raciones
    else:
        valor = "Sin datos"
        subtitulo = "Faltan calorías nutrimentales o raciones explícitas para estimar comida"
        metodo = "insuficiente"
        dias = None

    if dias is not None and dias_raciones is not None and metodo == "kcal":
        subtitulo += f" · respaldo: {dias_raciones:.1f} días por raciones"

    percent = None if dias is None else min(100, int((dias / 14.0) * 100))
    return {
        "value": valor,
        "subtitle": subtitulo,
        "percent": percent,
        "personas_consideradas": len(perfiles),
        "total_kcal": round(total_kcal, 2),
        "total_raciones": round(total_raciones, 2),
        "calorias_dia_grupo": calorias_dia_grupo,
        "raciones_dia_grupo": raciones_dia_grupo,
        "dias_autonomia": None if dias is None else round(dias, 2),
        "dias_autonomia_kcal": None if dias_kcal is None else round(dias_kcal, 2),
        "dias_autonomia_raciones": None if dias_raciones is None else round(dias_raciones, 2),
        "metodo": metodo,
    }
