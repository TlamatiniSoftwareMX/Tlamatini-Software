import ast
import calendar
import re
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

from core.memoria import cargar_memoria, guardar_memoria
from core.path_manager import APP_ASSETS_DIR
from core.window_geometry import aplicar_geometria_relativa, habilitar_scroll_mouse


UI_HERRAMIENTAS = {
    "fondo": "#0B1220",
    "panel": "#132238",
    "panel_alt": "#182B45",
    "borde": "#28496B",
    "texto": "#F8FAFC",
    "texto_dim": "#A9BCD0",
    "acento": "#38BDF8",
    "exito": "#22C55E",
    "alerta": "#F59E0B",
    "error": "#F87171",
}

SECCION_BLOC = "herramientas_bloc_notas"
SECCION_RECORDATORIOS = "herramientas_recordatorios"
SECCION_ALARMAS = "herramientas_alarmas"
SECCION_ALERTAS_DASHBOARD = "herramientas_alertas_dashboard"
SECCION_CANALES_RADIO = "herramientas_canales_radio"
SECCION_ENERGIA_CARGAS = "herramientas_energia_cargas"
SECCION_COORDENADAS = "herramientas_coordenadas"
DIAS_SEMANA = [
    ("lun", "Lun", 0),
    ("mar", "Mar", 1),
    ("mie", "Mié", 2),
    ("jue", "Jue", 3),
    ("vie", "Vie", 4),
    ("sab", "Sáb", 5),
    ("dom", "Dom", 6),
]
MESES_ES = [
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]
SONIDOS_ALERTA = {
    "alarm_clock": {"label": "Despertador clasico", "file": "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"},
    "incoming_call": {"label": "Sirena telefonica", "file": "/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga"},
    "busy_alarm": {"label": "Linea ocupada", "file": "/usr/share/sounds/freedesktop/stereo/phone-outgoing-busy.oga"},
    "calling": {"label": "Llamada saliente", "file": "/usr/share/sounds/freedesktop/stereo/phone-outgoing-calling.oga"},
    "warning": {"label": "Alerta de advertencia", "file": "/usr/share/sounds/Yaru/stereo/dialog-warning.oga"},
    "error": {"label": "Alerta critica", "file": "/usr/share/sounds/Yaru/stereo/dialog-error.oga"},
    "question": {"label": "Pregunta del sistema", "file": "/usr/share/sounds/Yaru/stereo/dialog-question.oga"},
    "info": {"label": "Informacion", "file": "/usr/share/sounds/freedesktop/stereo/dialog-information.oga"},
    "message": {"label": "Notificacion de mensaje", "file": "/usr/share/sounds/Yaru/stereo/message.oga"},
    "instant": {"label": "Mensaje instantaneo", "file": "/usr/share/sounds/Yaru/stereo/message-new-instant.oga"},
    "email": {"label": "Correo nuevo", "file": "/usr/share/sounds/Yaru/stereo/message-new-email.oga"},
    "battery_low": {"label": "Bateria baja", "file": "/usr/share/sounds/Yaru/stereo/battery-low.oga"},
    "bell": {"label": "Campana metalica", "file": "/usr/share/sounds/Yaru/stereo/bell.oga"},
    "complete": {"label": "Proceso completado", "file": "/usr/share/sounds/Yaru/stereo/complete.oga"},
    "system_ready": {"label": "Sistema listo", "file": "/usr/share/sounds/Yaru/stereo/system-ready.oga"},
    "login": {"label": "Inicio de sesion", "file": "/usr/share/sounds/Yaru/stereo/desktop-login.oga"},
    "logoff": {"label": "Cierre de sesion", "file": "/usr/share/sounds/Yaru/stereo/desktop-logoff.oga"},
    "service_login": {"label": "Servicio iniciado", "file": "/usr/share/sounds/freedesktop/stereo/service-login.oga"},
    "service_logout": {"label": "Servicio detenido", "file": "/usr/share/sounds/freedesktop/stereo/service-logout.oga"},
    "device_added": {"label": "Dispositivo conectado", "file": "/usr/share/sounds/Yaru/stereo/device-added.oga"},
    "device_removed": {"label": "Dispositivo desconectado", "file": "/usr/share/sounds/Yaru/stereo/device-removed.oga"},
    "volume_change": {"label": "Cambio de volumen", "file": "/usr/share/sounds/Yaru/stereo/audio-volume-change.oga"},
    "power_plug": {"label": "Conexion de energia", "file": "/usr/share/sounds/Yaru/stereo/power-plug.oga"},
    "power_unplug": {"label": "Desconexion de energia", "file": "/usr/share/sounds/Yaru/stereo/power-unplug.oga"},
    "camera": {"label": "Camara", "file": "/usr/share/sounds/freedesktop/stereo/camera-shutter.oga"},
    "test_signal": {"label": "Senal de prueba", "file": "/usr/share/sounds/freedesktop/stereo/audio-test-signal.oga"},
    "trash_empty": {"label": "Papelera vacia", "file": "/usr/share/sounds/Yaru/stereo/trash-empty.oga"},
    "suspend_error": {"label": "Error de suspension", "file": "/usr/share/sounds/freedesktop/stereo/suspend-error.oga"},
    "click": {"label": "Click suave", "file": "/usr/share/sounds/gnome/default/alerts/click.ogg"},
    "hum": {"label": "Zumbido", "file": "/usr/share/sounds/gnome/default/alerts/hum.ogg"},
    "swing": {"label": "Swing", "file": "/usr/share/sounds/gnome/default/alerts/swing.ogg"},
    "string": {"label": "Cuerda tensa", "file": "/usr/share/sounds/gnome/default/alerts/string.ogg"},
    "trumpet": {"label": "Trompeta de alarma", "file": "/usr/share/sounds/sound-icons/trumpet-1.wav"},
    "trumpet_alt": {"label": "Trompeta corta", "file": "/usr/share/sounds/sound-icons/trumpet-12.wav"},
    "percussion": {"label": "Percusion de impacto", "file": "/usr/share/sounds/sound-icons/percussion-50.wav"},
    "percussion_light": {"label": "Percusion ligera", "file": "/usr/share/sounds/sound-icons/percussion-10.wav"},
    "prompt": {"label": "Prompt clasico", "file": "/usr/share/sounds/sound-icons/prompt.wav"},
    "canary": {"label": "Canario largo", "file": "/usr/share/sounds/sound-icons/canary-long.wav"},
    "xylofon": {"label": "Xilofono", "file": "/usr/share/sounds/sound-icons/xylofon.wav"},
}
SONIDO_ALERTA_DEFAULT = "alarm_clock"
RUTA_SONIDOS_ALERTA = APP_ASSETS_DIR / "sounds"
VELOCIDAD_LUZ_M_S = 299_792_458

CATALOGO_CONVERSIONES = {
    "Longitud": {
        "tipo": "lineal",
        "base": "m",
        "unidades": {
            "mm": 0.001,
            "cm": 0.01,
            "m": 1.0,
            "km": 1000.0,
            "in": 0.0254,
            "ft": 0.3048,
            "yd": 0.9144,
            "mi": 1609.344,
        },
    },
    "Peso / masa": {
        "tipo": "lineal",
        "base": "kg",
        "unidades": {
            "mg": 0.000001,
            "g": 0.001,
            "kg": 1.0,
            "oz": 0.028349523125,
            "lb": 0.45359237,
        },
    },
    "Volumen": {
        "tipo": "lineal",
        "base": "l",
        "unidades": {
            "ml": 0.001,
            "l": 1.0,
            "m3": 1000.0,
            "tsp": 0.00492892,
            "tbsp": 0.0147868,
            "cup": 0.236588,
            "pt": 0.473176,
            "qt": 0.946353,
            "gal_us": 3.78541,
            "fl_oz_us": 0.0295735,
        },
    },
    "Temperatura": {
        "tipo": "temperatura",
        "unidades": {
            "C": (lambda c: c, lambda c: c),
            "F": (lambda f: (f - 32.0) * 5.0 / 9.0, lambda c: (c * 9.0 / 5.0) + 32.0),
            "K": (lambda k: k - 273.15, lambda c: c + 273.15),
        },
    },
    "Velocidad": {
        "tipo": "lineal",
        "base": "m/s",
        "unidades": {
            "m/s": 1.0,
            "km/h": 0.2777777778,
            "mph": 0.44704,
            "kn": 0.514444,
        },
    },
    "Superficie / área": {
        "tipo": "lineal",
        "base": "m2",
        "unidades": {
            "m2": 1.0,
            "ha": 10000.0,
            "km2": 1_000_000.0,
            "ft2": 0.092903,
            "yd2": 0.836127,
            "acre": 4046.8564224,
        },
    },
    "Energía": {
        "tipo": "lineal",
        "base": "J",
        "unidades": {
            "J": 1.0,
            "kJ": 1000.0,
            "Wh": 3600.0,
            "kWh": 3_600_000.0,
            "cal": 4.184,
            "kcal": 4184.0,
        },
    },
    "Potencia": {
        "tipo": "lineal",
        "base": "W",
        "unidades": {
            "W": 1.0,
            "kW": 1000.0,
            "hp": 745.699872,
        },
    },
    "Presión": {
        "tipo": "lineal",
        "base": "Pa",
        "unidades": {
            "Pa": 1.0,
            "kPa": 1000.0,
            "bar": 100000.0,
            "psi": 6894.757293,
            "atm": 101325.0,
        },
    },
    "Tiempo": {
        "tipo": "lineal",
        "base": "s",
        "unidades": {
            "s": 1.0,
            "min": 60.0,
            "h": 3600.0,
            "día": 86400.0,
            "semana": 604800.0,
        },
    },
    "Almacenamiento digital": {
        "tipo": "lineal",
        "base": "B",
        "unidades": {
            "B": 1.0,
            "KB": 1024.0,
            "MB": 1024.0**2,
            "GB": 1024.0**3,
            "TB": 1024.0**4,
        },
    },
    "Cocina / supervivencia": {
        "tipo": "lineal",
        "base": "ml",
        "unidades": {
            "ml": 1.0,
            "l": 1000.0,
            "tsp": 4.92892,
            "tbsp": 14.7868,
            "cup": 236.588,
            "fl_oz_us": 29.5735,
            "oz_peso_agua": 29.5735,
            "jarra": 1000.0,
        },
    },
}

DOSIS_MEDICAS = {
    "Paracetamol": {
        "tipo": "mg_kg",
        "edad_min_meses": 0,
        "pediatrico_kg_dosis": (10.0, 15.0),
        "pediatrico_intervalo": "cada 4 a 6 h",
        "pediatrico_max_mg_kg_dia": 75.0,
        "adulto_dosis_mg": (500, 1000),
        "adulto_intervalo": "cada 6 a 8 h",
        "adulto_max_mg_dia": 3000,
        "nota": "Uso orientativo. Si hay enfermedad hepática, alcoholismo, vómitos persistentes o deshidratación severa, no te fíes de este cálculo sin valoración médica.",
    },
    "Ibuprofeno": {
        "tipo": "mg_kg",
        "edad_min_meses": 6,
        "pediatrico_kg_dosis": (5.0, 10.0),
        "pediatrico_intervalo": "cada 6 a 8 h",
        "pediatrico_max_mg_kg_dia": 40.0,
        "adulto_dosis_mg": (200, 400),
        "adulto_intervalo": "cada 6 a 8 h",
        "adulto_max_mg_dia": 1200,
        "nota": "Evita usarlo si hay deshidratación importante, úlcera, sangrado digestivo, embarazo avanzado o enfermedad renal conocida sin supervisión.",
    },
    "Solución de hidratación oral": {
        "tipo": "rehidratacion",
        "edad_min_meses": 0,
        "nota": "Orientación de primeros auxilios para rehidratación oral. Si hay somnolencia, sangre en heces, incapacidad para beber o signos de choque, esto no sustituye atención médica.",
    },
}


def _mostrar_encima(ventana):
    try:
        ventana.lift()
        ventana.focus_force()
    except Exception:
        pass


def _obtener_bloque_herramientas():
    memoria = cargar_memoria()
    herramientas = memoria.get("herramientas")
    if not isinstance(herramientas, dict):
        herramientas = {}
        memoria["herramientas"] = herramientas
    return memoria, herramientas


def _cargar_lista_herramientas(clave):
    _, herramientas = _obtener_bloque_herramientas()
    datos = herramientas.get(clave, [])
    return list(datos) if isinstance(datos, list) else []


def _guardar_lista_herramientas(clave, valores):
    memoria, herramientas = _obtener_bloque_herramientas()
    herramientas[clave] = list(valores or [])
    guardar_memoria(memoria)


def cargar_canales_radio():
    canales = []
    for item in _cargar_lista_herramientas(SECCION_CANALES_RADIO):
        if not isinstance(item, dict):
            continue
        alias = str(item.get("alias", "")).strip()
        frecuencia = str(item.get("frecuencia", "")).strip()
        unidad = str(item.get("unidad", "MHz")).strip() or "MHz"
        if not alias or not frecuencia:
            continue
        canales.append(
            {
                "id": str(item.get("id", datetime.now().strftime("%Y%m%d%H%M%S%f"))),
                "alias": alias,
                "frecuencia": frecuencia,
                "unidad": unidad,
                "modo": str(item.get("modo", "")).strip(),
                "nota": str(item.get("nota", "")).strip(),
            }
        )
    return canales


def guardar_canales_radio(canales):
    _guardar_lista_herramientas(SECCION_CANALES_RADIO, canales)


def cargar_cargas_energia():
    cargas = []
    for item in _cargar_lista_herramientas(SECCION_ENERGIA_CARGAS):
        if not isinstance(item, dict):
            continue
        cargas.append(
            {
                "id": str(item.get("id", datetime.now().strftime("%Y%m%d%H%M%S%f"))),
                "nombre": str(item.get("nombre", "")).strip(),
                "w": str(item.get("w", "")).strip(),
                "h": str(item.get("h", "")).strip(),
                "cantidad": str(item.get("cantidad", "")).strip() or "1",
            }
        )
    return cargas


def guardar_cargas_energia(cargas):
    _guardar_lista_herramientas(SECCION_ENERGIA_CARGAS, cargas)


def guardar_ultimo_resultado_coordenadas(data):
    memoria, herramientas = _obtener_bloque_herramientas()
    herramientas[SECCION_COORDENADAS] = dict(data or {})
    guardar_memoria(memoria)


def cargar_ultimo_resultado_coordenadas():
    _, herramientas = _obtener_bloque_herramientas()
    data = herramientas.get(SECCION_COORDENADAS, {})
    return data if isinstance(data, dict) else {}


def cargar_bloc_notas():
    _, herramientas = _obtener_bloque_herramientas()
    notas = herramientas.get(SECCION_BLOC, {})
    if not isinstance(notas, dict):
        notas = {}
    items = notas.get("notas", [])
    if not isinstance(items, list):
        items = []
    items_normalizados = []
    for item in items:
        if not isinstance(item, dict):
            continue
        texto = str(item.get("texto", "")).strip()
        if not texto:
            continue
        tipo = str(item.get("tipo", "punto")).strip().lower()
        if tipo not in {"punto", "check"}:
            tipo = "punto"
        items_normalizados.append(
            {
                "id": str(item.get("id", datetime.now().strftime("%Y%m%d%H%M%S%f"))),
                "titulo": str(item.get("titulo", "")).strip(),
                "texto": texto,
                "tipo": tipo,
                "completada": bool(item.get("completada", False)),
                "creado_en": str(item.get("creado_en", "")),
            }
        )
    if not items_normalizados and str(notas.get("contenido", "")).strip():
        for linea in str(notas.get("contenido", "")).splitlines():
            texto = linea.strip()
            if texto:
                items_normalizados.append(
                    {
                        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                        "titulo": "",
                        "texto": texto,
                        "tipo": "punto",
                        "completada": False,
                        "creado_en": "",
                    }
                )
    return {
        "notas": items_normalizados,
        "actualizado_en": notas.get("actualizado_en", ""),
    }


def guardar_bloc_notas(notas):
    memoria, herramientas = _obtener_bloque_herramientas()
    normalizadas = []
    for item in list(notas or []):
        if not isinstance(item, dict):
            continue
        texto = str(item.get("texto", "")).strip()
        if not texto:
            continue
        tipo = str(item.get("tipo", "punto")).strip().lower()
        if tipo not in {"punto", "check"}:
            tipo = "punto"
        normalizadas.append(
            {
                "id": str(item.get("id", datetime.now().strftime("%Y%m%d%H%M%S%f"))),
                "titulo": str(item.get("titulo", "")).strip(),
                "texto": texto,
                "tipo": tipo,
                "completada": bool(item.get("completada", False)),
                "creado_en": str(item.get("creado_en", "")),
            }
        )
    herramientas[SECCION_BLOC] = {
        "notas": normalizadas,
        "actualizado_en": datetime.now().isoformat(timespec="seconds"),
    }
    guardar_memoria(memoria)


def cargar_recordatorios():
    _, herramientas = _obtener_bloque_herramientas()
    recordatorios = herramientas.get(SECCION_RECORDATORIOS, [])
    if not isinstance(recordatorios, list):
        return []
    return sorted(
        [r for r in recordatorios if isinstance(r, dict)],
        key=lambda item: (
            str(item.get("fecha", "")),
            str(item.get("hora", "")),
            str(item.get("titulo", "")),
        ),
    )


def guardar_recordatorios(recordatorios):
    memoria, herramientas = _obtener_bloque_herramientas()
    herramientas[SECCION_RECORDATORIOS] = recordatorios
    guardar_memoria(memoria)


def cargar_alarmas():
    _, herramientas = _obtener_bloque_herramientas()
    alarmas = herramientas.get(SECCION_ALARMAS, [])
    if not isinstance(alarmas, list):
        return []
    normalizadas = []
    for item in alarmas:
        if not isinstance(item, dict):
            continue
        hora = str(item.get("hora", "")).strip()
        if not hora:
            continue
        dias = item.get("dias_semana", [])
        if not isinstance(dias, list):
            dias = []
        normalizadas.append(
            {
                "id": str(item.get("id", datetime.now().strftime("%Y%m%d%H%M%S%f"))),
                "titulo": str(item.get("titulo", "")).strip() or "Alarma",
                "nota": str(item.get("nota", "")).strip(),
                "hora": hora,
                "repeticion": str(item.get("repeticion", "una_vez")).strip() or "una_vez",
                "fecha": str(item.get("fecha", "")).strip(),
                "dias_semana": [int(x) for x in dias if str(x).isdigit()],
                "sonido": normalizar_sonido_alerta(item.get("sonido")),
                "activa": bool(item.get("activa", True)),
                "ultimo_disparo_fecha": str(item.get("ultimo_disparo_fecha", "")).strip(),
                "disparado_en": str(item.get("disparado_en", "")).strip(),
                "alerta_emitida": bool(item.get("alerta_emitida", False)),
                "creado_en": str(item.get("creado_en", "")),
            }
        )
    return sorted(normalizadas, key=lambda item: (item.get("hora", ""), item.get("titulo", ""), item.get("id", "")))


def guardar_alarmas(alarmas):
    memoria, herramientas = _obtener_bloque_herramientas()
    herramientas[SECCION_ALARMAS] = list(alarmas or [])
    guardar_memoria(memoria)


def cargar_sonido_dashboard():
    _, herramientas = _obtener_bloque_herramientas()
    bloque = herramientas.get(SECCION_ALERTAS_DASHBOARD, {})
    if not isinstance(bloque, dict):
        return SONIDO_ALERTA_DEFAULT
    return normalizar_sonido_alerta(bloque.get("sonido"))


def guardar_sonido_dashboard(sonido_id):
    memoria, herramientas = _obtener_bloque_herramientas()
    herramientas[SECCION_ALERTAS_DASHBOARD] = {
        "sonido": normalizar_sonido_alerta(sonido_id),
        "actualizado_en": datetime.now().isoformat(timespec="seconds"),
    }
    guardar_memoria(memoria)


def obtener_opciones_sonido_alerta():
    return [(clave, datos["label"]) for clave, datos in SONIDOS_ALERTA.items()]


def normalizar_sonido_alerta(sonido_id):
    if sonido_id in SONIDOS_ALERTA:
        return sonido_id
    return SONIDO_ALERTA_DEFAULT


def obtener_ruta_sonido_alerta(sonido_id):
    sonido = SONIDOS_ALERTA.get(normalizar_sonido_alerta(sonido_id), SONIDOS_ALERTA[SONIDO_ALERTA_DEFAULT])
    ruta = Path(sonido["file"])
    if ruta.is_absolute():
        return ruta
    return RUTA_SONIDOS_ALERTA / ruta


def etiqueta_sonido_alerta(sonido_id):
    sonido = SONIDOS_ALERTA.get(normalizar_sonido_alerta(sonido_id), SONIDOS_ALERTA[SONIDO_ALERTA_DEFAULT])
    return sonido["label"]


def parsear_hora_recordatorio(hora_texto):
    hora_texto = (hora_texto or "").strip().upper()
    formatos = ("%H:%M", "%I:%M %p", "%I:%M%p")
    for formato in formatos:
        try:
            dt = datetime.strptime(hora_texto, formato)
            return dt.strftime("%H:%M")
        except ValueError:
            continue
    raise ValueError("Hora inválida")


def formatear_hora_ampm(hora_24):
    try:
        return datetime.strptime((hora_24 or "").strip(), "%H:%M").strftime("%I:%M %p").lower()
    except ValueError:
        return hora_24 or "--:--"


def formatear_hora_ampm_segundos(hora_24):
    try:
        return datetime.strptime((hora_24 or "").strip(), "%H:%M:%S").strftime("%I:%M:%S %p").lower()
    except ValueError:
        return hora_24 or "--:--:--"


def parsear_fecha_dma(fecha_texto):
    texto = (fecha_texto or "").strip()
    for formato in ("%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("La fecha debe ir como d-m-a.")


def formatear_fecha_dma(fecha_iso):
    try:
        return datetime.strptime((fecha_iso or "").strip(), "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return fecha_iso or "--"


def etiqueta_repeticion(recordatorio):
    modo = (recordatorio or {}).get("repeticion", "una_vez")
    if modo == "diaria":
        return "Varias veces"
    if modo == "semanal":
        dias = []
        for _, corto, idx in DIAS_SEMANA:
            if idx in (recordatorio or {}).get("dias_semana", []):
                dias.append(corto)
        return " / ".join(dias) if dias else "Semanal"
    return "Una vez"


def siguiente_fecha_para_semana(dias_semana):
    hoy = datetime.now().date()
    dias = sorted({int(x) for x in list(dias_semana or []) if isinstance(x, int) or str(x).isdigit()})
    if not dias:
        return ""
    for offset in range(7):
        candidata = hoy + timedelta(days=offset)
        if candidata.weekday() in dias:
            return candidata.strftime("%Y-%m-%d")
    return hoy.strftime("%Y-%m-%d")


def _evaluar_expresion_segura(expresion):
    operadores_binarios = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a ** b,
    }
    operadores_unarios = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    def resolver(nodo):
        if isinstance(nodo, ast.Expression):
            return resolver(nodo.body)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)):
            return nodo.value
        if isinstance(nodo, ast.Num):
            return nodo.n
        if isinstance(nodo, ast.BinOp) and type(nodo.op) in operadores_binarios:
            return operadores_binarios[type(nodo.op)](resolver(nodo.left), resolver(nodo.right))
        if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in operadores_unarios:
            return operadores_unarios[type(nodo.op)](resolver(nodo.operand))
        raise ValueError("Expresión no permitida")

    arbol = ast.parse(expresion, mode="eval")
    return resolver(arbol)


class VentanaHerramientas(tk.Toplevel):
    def __init__(self, master, focus_parent=None):
        super().__init__(master)
        self.focus_parent = focus_parent or master
        self.title("Herramientas")
        self.configure(bg=UI_HERRAMIENTAS["fondo"])
        aplicar_geometria_relativa(self, self.focus_parent, rel_w=0.74, rel_h=0.78, min_w=1080, min_h=720)
        self.catalogo_herramientas = [
            {
                "id": "calculadora",
                "icono": "🧮",
                "titulo": "Calculadora",
                "detalle": "Operaciones rápidas y expresiones seguras.",
                "color": "#1D4ED8",
                "accion": self._abrir_calculadora,
            },
            {
                "id": "bloc",
                "icono": "📝",
                "titulo": "Bloc de notas",
                "detalle": "Notas rápidas y checklists persistentes.",
                "color": "#0F766E",
                "accion": self._abrir_bloc,
            },
            {
                "id": "calendario",
                "icono": "📅",
                "titulo": "Calendario y recordatorios",
                "detalle": "Agenda offline con recordatorios y seguimiento diario.",
                "color": "#B45309",
                "accion": self._abrir_calendario,
            },
            {
                "id": "alarmas",
                "icono": "⏰",
                "titulo": "Alarmas",
                "detalle": "Alarmas locales integradas con el dashboard y sonidos.",
                "color": "#BE185D",
                "accion": self._abrir_alarmas,
            },
            {
                "id": "comunicaciones",
                "icono": "📡",
                "titulo": "Comunicaciones",
                "detalle": "Calculadora de frecuencia y libreta local de canales/frecuencias.",
                "color": "#0891B2",
                "accion": self._abrir_comunicaciones,
            },
            {
                "id": "conversiones",
                "icono": "🔁",
                "titulo": "Conversiones",
                "detalle": "Conversor multiunidad para campo, cocina, energía y logística.",
                "color": "#7C3AED",
                "accion": self._abrir_conversiones,
            },
            {
                "id": "energia",
                "icono": "🔋",
                "titulo": "Calculadora de energía",
                "detalle": "Autonomía de baterías, carga solar y consumo diario acumulado.",
                "color": "#CA8A04",
                "accion": self._abrir_energia,
            },
            {
                "id": "dosificacion",
                "icono": "🩺",
                "titulo": "Dosificación médica básica",
                "detalle": "Ayuda orientativa por edad, peso y medicamento básico.",
                "color": "#DC2626",
                "accion": self._abrir_dosificacion,
            },
            {
                "id": "coordenadas",
                "icono": "🧭",
                "titulo": "Decodificador de coordenadas",
                "detalle": "Interpreta decimal y DMS, convierte y deja salida lista para mapa.",
                "color": "#10B981",
                "accion": self._abrir_coordenadas,
            },
        ]
        self._crear_ui()
        _mostrar_encima(self)

    def _crear_ui(self):
        shell = tk.Frame(self, bg=UI_HERRAMIENTAS["fondo"])
        shell.pack(fill="both", expand=True, padx=18, pady=18)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        header = tk.Frame(shell, bg=UI_HERRAMIENTAS["fondo"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="Centro de herramientas", font=("Arial", 22, "bold"), bg=UI_HERRAMIENTAS["fondo"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="Operación offline para cálculo, registro y apoyo táctico. Doble clic para abrir una herramienta.",
            font=("Arial", 10),
            bg=UI_HERRAMIENTAS["fondo"],
            fg=UI_HERRAMIENTAS["texto_dim"],
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        contenedor = tk.Frame(
            shell,
            bg=UI_HERRAMIENTAS["panel"],
            highlightthickness=1,
            highlightbackground=UI_HERRAMIENTAS["borde"],
        )
        contenedor.grid(row=1, column=0, sticky="nsew")

        grid = tk.Frame(contenedor, bg=UI_HERRAMIENTAS["panel"])
        grid.pack(fill="both", expand=True, padx=14, pady=14)

        columnas = 3
        for columna in range(columnas):
            grid.grid_columnconfigure(columna, weight=1, uniform="herramientas")

        for indice, item in enumerate(self.catalogo_herramientas):
            fila = indice // columnas
            columna = indice % columnas
            grid.grid_rowconfigure(fila, weight=1, uniform="herramientas_fila")

            tarjeta = tk.Frame(
                grid,
                bg=UI_HERRAMIENTAS["panel_alt"],
                highlightthickness=1,
                highlightbackground=UI_HERRAMIENTAS["borde"],
                cursor="hand2",
            )
            tarjeta.grid(row=fila, column=columna, sticky="nsew", padx=8, pady=8)

            for widget in (tarjeta,):
                widget.bind("<Double-Button-1>", lambda _event, fn=item["accion"]: fn())

            icono = tk.Label(
                tarjeta,
                text=item["icono"],
                font=("Arial", 32),
                bg=UI_HERRAMIENTAS["panel_alt"],
                fg=item["color"],
            )
            icono.pack(anchor="w", padx=16, pady=(16, 8))
            icono.bind("<Double-Button-1>", lambda _event, fn=item["accion"]: fn())

            titulo = tk.Label(
                tarjeta,
                text=item["titulo"],
                font=("Arial", 14, "bold"),
                bg=UI_HERRAMIENTAS["panel_alt"],
                fg=UI_HERRAMIENTAS["texto"],
                justify="left",
                wraplength=240,
            )
            titulo.pack(anchor="w", padx=16, pady=(0, 6))
            titulo.bind("<Double-Button-1>", lambda _event, fn=item["accion"]: fn())

            detalle = tk.Label(
                tarjeta,
                text=item["detalle"],
                font=("Arial", 10),
                bg=UI_HERRAMIENTAS["panel_alt"],
                fg=UI_HERRAMIENTAS["texto_dim"],
                justify="left",
                wraplength=240,
            )
            detalle.pack(anchor="w", padx=16, pady=(0, 16))
            detalle.bind("<Double-Button-1>", lambda _event, fn=item["accion"]: fn())

    def _abrir_calculadora(self):
        VentanaCalculadora(self, self.focus_parent)

    def _abrir_bloc(self):
        VentanaBlocNotas(self, self.focus_parent)

    def _abrir_calendario(self):
        VentanaCalendarioRecordatorios(self, self.focus_parent)

    def _abrir_alarmas(self):
        VentanaAlarmas(self, self.focus_parent)

    def _abrir_comunicaciones(self):
        VentanaComunicaciones(self, self.focus_parent)

    def _abrir_conversiones(self):
        VentanaConversiones(self, self.focus_parent)

    def _abrir_energia(self):
        VentanaEnergia(self, self.focus_parent)

    def _abrir_dosificacion(self):
        VentanaDosificacionMedica(self, self.focus_parent)

    def _abrir_coordenadas(self):
        VentanaCoordenadas(self, self.focus_parent)


class VentanaCalculadora(tk.Toplevel):
    def __init__(self, master, focus_parent=None):
        super().__init__(master)
        self.focus_parent = focus_parent or master
        self.expresion_actual = ""
        self.mapa_teclas = {}
        self.fuente_titulo = tkfont.nametofont("TkDefaultFont").copy()
        self.fuente_titulo.configure(size=11, weight="bold")
        self.fuente_pantalla = tkfont.nametofont("TkFixedFont").copy()
        self.fuente_pantalla.configure(size=24, weight="bold")
        self.fuente_resultado = tkfont.nametofont("TkFixedFont").copy()
        self.fuente_resultado.configure(size=11, weight="bold")
        self.fuente_boton = tkfont.nametofont("TkDefaultFont").copy()
        self.fuente_boton.configure(size=18, weight="bold")
        self.canvas = None
        self.teclas = {}
        self.tecla_presionada = None
        self.title("Calculadora")
        self.configure(bg="#101826")
        self.geometry("430x720")
        self.minsize(430, 720)
        self.resizable(False, False)
        self._crear_ui()
        self.bind("<KeyPress>", self._al_presionar_tecla)
        self.bind("<KeyRelease>", self._al_soltar_tecla)
        self.after(80, self.focus_force)
        _mostrar_encima(self)

    def _crear_ui(self):
        self.canvas = tk.Canvas(
            self,
            width=430,
            height=720,
            bg="#101826",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_rectangle(18, 18, 412, 702, fill="#1A2434", outline="#4B5563", width=3)
        self.canvas.create_text(38, 40, text="TLAMATINI CALCULATOR", anchor="w", fill="#7DD3FC", font=self.fuente_titulo)
        self.canvas.create_text(38, 62, text="DIGITAL FUTURE EDITION", anchor="w", fill="#CBD5E1")

        self.canvas.create_rectangle(36, 86, 394, 190, fill="#BFECCF", outline="#334155", width=3)
        self.entrada = tk.Label(self.canvas, text="0", font=self.fuente_pantalla, bg="#BFECCF", fg="#0B1F16", anchor="e")
        self.resultado = tk.Label(self.canvas, text="Resultado: ", font=self.fuente_resultado, bg="#BFECCF", fg="#234435", anchor="e")
        self.canvas.create_window(50, 102, anchor="nw", width=330, height=48, window=self.entrada)
        self.canvas.create_window(50, 148, anchor="nw", width=330, height=28, window=self.resultado)

        layout = [
            [("CLR", "accion"), ("BK", "accion"), ("%", "operador"), ("/", "operador")],
            [("7", "numero"), ("8", "numero"), ("9", "numero"), ("*", "operador")],
            [("4", "numero"), ("5", "numero"), ("6", "numero"), ("-", "operador")],
            [("1", "numero"), ("2", "numero"), ("3", "numero"), ("+", "operador")],
            [("NEG", "accion"), ("0", "numero"), (".", "numero"), ("=", "igual")],
        ]

        x0 = 36
        y0 = 220
        ancho = 78
        alto = 78
        gap = 10
        for fila, celdas in enumerate(layout):
            for col, (texto, tipo) in enumerate(celdas):
                x1 = x0 + col * (ancho + gap)
                y1 = y0 + fila * (alto + gap)
                self._crear_tecla_canvas(x1, y1, ancho, alto, texto, tipo)

        self.mapa_teclas = {
            "0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
            ".": ".", "+": "+", "-": "-", "/": "/", "%": "%",
            "*": "*",
            "Return": "=",
            "KP_Enter": "=",
            "KP_Add": "+",
            "KP_Subtract": "-",
            "KP_Multiply": "*",
            "KP_Divide": "/",
            "KP_Decimal": ".",
            "BackSpace": "BK",
            "Delete": "CLR",
        }

    def _crear_tecla_canvas(self, x, y, ancho, alto, texto, tipo):
        colores = {
            "numero": ("#E5E7EB", "#111827", "#FFFFFF"),
            "operador": ("#60A5FA", "#0C223F", "#93C5FD"),
            "accion": ("#9CA3AF", "#111827", "#D1D5DB"),
            "igual": ("#34D399", "#052E28", "#6EE7B7"),
        }
        bg, fg, active = colores[tipo]
        sombra = self.canvas.create_rectangle(x + 3, y + 4, x + ancho + 3, y + alto + 4, fill="#0B1220", outline="")
        rect = self.canvas.create_rectangle(x, y, x + ancho, y + alto, fill=bg, outline="#6B7280", width=3)
        text = self.canvas.create_text(x + (ancho / 2), y + (alto / 2), text=texto, fill=fg, font=self.fuente_boton)
        self.teclas[texto] = {
            "rect": rect,
            "text": text,
            "shadow": sombra,
            "bg": bg,
            "fg": fg,
            "active": active,
        }
        for item in (rect, text):
            self.canvas.tag_bind(item, "<ButtonPress-1>", lambda _e, valor=texto: self._presionar_tecla_canvas(valor))
            self.canvas.tag_bind(item, "<ButtonRelease-1>", lambda _e, valor=texto: self._soltar_tecla_canvas(valor))

    def _presionar_tecla_canvas(self, valor):
        self.tecla_presionada = valor
        self._resaltar_tecla(valor, True)

    def _soltar_tecla_canvas(self, valor):
        self._resaltar_tecla(valor, False)
        if self.tecla_presionada == valor:
            self._procesar_boton(valor)
        self.tecla_presionada = None

    def _procesar_boton(self, valor):
        if valor == "CLR":
            self.limpiar()
            return
        if valor == "BK":
            self.expresion_actual = self.expresion_actual[:-1]
            self._refrescar_pantalla()
            return
        if valor == "NEG":
            self._alternar_signo()
            return
        if valor == "=":
            self.calcular()
            return
        self.expresion_actual += valor
        self._refrescar_pantalla()

    def _refrescar_pantalla(self):
        self.entrada.config(text=self.expresion_actual or "0")

    def _parpadear_boton(self, clave):
        if clave not in self.teclas:
            return
        self._resaltar_tecla(clave, True, bg="#FDE68A", fg="#111827")
        self.after(140, lambda: self._resaltar_tecla(clave, False))

    def _resaltar_tecla(self, clave, activa, bg=None, fg=None):
        tecla = self.teclas.get(clave)
        if not tecla:
            return
        color_bg = bg if activa and bg else (tecla["active"] if activa else tecla["bg"])
        color_fg = fg if activa and fg else tecla["fg"]
        self.canvas.itemconfigure(tecla["rect"], fill=color_bg)
        self.canvas.itemconfigure(tecla["text"], fill=color_fg)

    def _alternar_signo(self):
        if not self.expresion_actual:
            self.expresion_actual = "-"
            self._refrescar_pantalla()
            return

        fin = len(self.expresion_actual) - 1
        while fin >= 0 and (self.expresion_actual[fin].isdigit() or self.expresion_actual[fin] == "."):
            fin -= 1
        inicio = fin + 1

        if inicio >= len(self.expresion_actual):
            return

        if fin >= 0 and self.expresion_actual[fin] == "-" and (fin == 0 or self.expresion_actual[fin - 1] in "+-*/%"):
            self.expresion_actual = self.expresion_actual[:fin] + self.expresion_actual[inicio:]
        else:
            self.expresion_actual = self.expresion_actual[:inicio] + "-" + self.expresion_actual[inicio:]
        self._refrescar_pantalla()

    def _al_presionar_tecla(self, event):
        tecla = event.keysym
        char = event.char or ""

        if tecla in self.mapa_teclas:
            valor = self.mapa_teclas[tecla]
        elif char in self.mapa_teclas:
            valor = self.mapa_teclas[char]
        else:
            return

        self._parpadear_boton(valor)
        self._procesar_boton(valor)
        return "break"

    def _al_soltar_tecla(self, event):
        tecla = event.keysym
        char = event.char or ""
        valor = self.mapa_teclas.get(tecla) or self.mapa_teclas.get(char)
        if valor:
            return "break"

    def calcular(self):
        expresion = self.expresion_actual.strip()
        if not expresion:
            self.resultado.config(text="Resultado: ingresa una operación", fg=UI_HERRAMIENTAS["alerta"])
            return
        try:
            valor = _evaluar_expresion_segura(expresion)
            self.resultado.config(text=f"Resultado: {valor}", fg=UI_HERRAMIENTAS["acento"])
            self.expresion_actual = str(valor)
            self._refrescar_pantalla()
        except Exception:
            self.resultado.config(text="Resultado: expresión inválida", fg=UI_HERRAMIENTAS["error"])

    def limpiar(self):
        self.expresion_actual = ""
        self._refrescar_pantalla()
        self.resultado.config(text="Resultado: ", fg=UI_HERRAMIENTAS["acento"])


class VentanaBlocNotas(tk.Toplevel):
    def __init__(self, master, focus_parent=None):
        super().__init__(master)
        self.focus_parent = focus_parent or master
        self.notas = []
        self.nota_editando_id = None
        self.title("Bloc de notas")
        self.configure(bg=UI_HERRAMIENTAS["fondo"])
        aplicar_geometria_relativa(self, self.focus_parent, rel_w=0.64, rel_h=0.76, min_w=920, min_h=700)
        self._crear_ui()
        self._cargar()
        _mostrar_encima(self)

    def _crear_ui(self):
        contenedor = tk.Frame(self, bg=UI_HERRAMIENTAS["fondo"])
        contenedor.pack(fill="both", expand=True, padx=20, pady=18)
        contenedor.grid_columnconfigure(0, weight=3)
        contenedor.grid_columnconfigure(1, weight=2)
        contenedor.grid_rowconfigure(1, weight=1)

        tk.Label(
            contenedor,
            text="Bloc de notas",
            font=("Arial", 18, "bold"),
            bg=UI_HERRAMIENTAS["fondo"],
            fg=UI_HERRAMIENTAS["texto"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        entrada = tk.Frame(
            contenedor,
            bg=UI_HERRAMIENTAS["panel"],
            highlightthickness=1,
            highlightbackground=UI_HERRAMIENTAS["borde"],
        )
        entrada.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        entrada.grid_columnconfigure(0, weight=1)
        entrada.grid_rowconfigure(3, weight=1)

        self.entry_titulo_nota = tk.Entry(
            entrada,
            font=("Arial", 12, "bold"),
            bg=UI_HERRAMIENTAS["panel"],
            fg=UI_HERRAMIENTAS["texto"],
            insertbackground=UI_HERRAMIENTAS["texto"],
            relief="flat",
        )
        tk.Label(entrada, text="Título", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))
        self.entry_titulo_nota.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12), ipady=8)

        tk.Label(entrada, text="Nueva nota", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 6))

        editor = tk.Frame(entrada, bg=UI_HERRAMIENTAS["panel"])
        editor.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 12))
        editor.grid_columnconfigure(1, weight=1)
        editor.grid_rowconfigure(0, weight=1)

        barra_herramientas = tk.Frame(editor, bg=UI_HERRAMIENTAS["panel"])
        barra_herramientas.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        herramientas_nota = [
            ("•", "• "),
            ("◦", "◦ "),
            ("☐", "☐ "),
            ("✓", "✓ "),
            ("1.", "1. "),
            ("- ", "- "),
            ("⭐", "⭐ "),
        ]
        for texto_boton, prefijo in herramientas_nota:
            tk.Button(
                barra_herramientas,
                text=texto_boton,
                font=("Arial", 12, "bold"),
                width=3,
                bg=UI_HERRAMIENTAS["panel_alt"],
                fg=UI_HERRAMIENTAS["texto"],
                activebackground=UI_HERRAMIENTAS["borde"],
                activeforeground=UI_HERRAMIENTAS["texto"],
                relief="flat",
                command=lambda valor=prefijo: self._insertar_prefijo(valor),
            ).pack(fill="x", padx=6, pady=4)

        editor_texto = tk.Frame(editor, bg=UI_HERRAMIENTAS["panel"])
        editor_texto.grid(row=0, column=1, sticky="nsew")
        editor_texto.grid_columnconfigure(0, weight=1)
        editor_texto.grid_rowconfigure(0, weight=1)

        self.texto_nota = tk.Text(
            editor_texto,
            font=("Arial", 12),
            bg=UI_HERRAMIENTAS["panel"],
            fg=UI_HERRAMIENTAS["texto"],
            insertbackground=UI_HERRAMIENTAS["texto"],
            relief="flat",
            wrap="word",
            height=14,
            padx=10,
            pady=10,
        )
        self.texto_nota.grid(row=0, column=0, sticky="nsew")
        scroll_editor = ttk.Scrollbar(editor_texto, orient="vertical", command=self.texto_nota.yview)
        scroll_editor.grid(row=0, column=1, sticky="ns")
        self.texto_nota.configure(yscrollcommand=scroll_editor.set)

        tk.Button(
            entrada,
            text="Guardar nota",
            font=("Arial", 10, "bold"),
            bg="#0F766E",
            fg="white",
            activebackground="#115E59",
            activeforeground="white",
            relief="flat",
            command=self._agregar_nota,
        ).grid(row=4, column=0, sticky="e", padx=16, pady=(0, 16))

        lista_frame = tk.Frame(
            contenedor,
            bg=UI_HERRAMIENTAS["panel"],
            highlightthickness=1,
            highlightbackground=UI_HERRAMIENTAS["borde"],
        )
        lista_frame.grid(row=1, column=1, sticky="nsew")
        lista_frame.grid_columnconfigure(0, weight=1)
        lista_frame.grid_rowconfigure(1, weight=1)

        tk.Label(
            lista_frame,
            text="Notas guardadas",
            font=("Arial", 12, "bold"),
            bg=UI_HERRAMIENTAS["panel"],
            fg=UI_HERRAMIENTAS["texto"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 10))

        self.canvas_notas = tk.Canvas(lista_frame, bg=UI_HERRAMIENTAS["panel"], highlightthickness=0, bd=0)
        self.canvas_notas.grid(row=1, column=0, sticky="nsew", padx=(14, 0), pady=(0, 12))
        self.scroll_notas = ttk.Scrollbar(lista_frame, orient="vertical", command=self.canvas_notas.yview)
        self.scroll_notas.grid(row=1, column=1, sticky="ns", padx=(0, 14), pady=(0, 12))
        self.canvas_notas.configure(yscrollcommand=self.scroll_notas.set)

        self.panel_notas = tk.Frame(self.canvas_notas, bg=UI_HERRAMIENTAS["panel"])
        self.canvas_notas_window = self.canvas_notas.create_window((0, 0), window=self.panel_notas, anchor="nw")
        self.panel_notas.bind("<Configure>", lambda _e: self.canvas_notas.configure(scrollregion=self.canvas_notas.bbox("all")))
        self.canvas_notas.bind("<Configure>", lambda e: self.canvas_notas.itemconfigure(self.canvas_notas_window, width=e.width))
        habilitar_scroll_mouse(lista_frame, self.canvas_notas)

        barra = tk.Frame(contenedor, bg=UI_HERRAMIENTAS["fondo"])
        barra.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        tk.Button(
            barra,
            text="Guardar notas",
            font=("Arial", 10, "bold"),
            bg="#0F766E",
            fg="white",
            activebackground="#115E59",
            activeforeground="white",
            relief="flat",
            command=self.guardar,
        ).pack(side="left")

        tk.Button(
            barra,
            text="Nueva nota",
            font=("Arial", 10, "bold"),
            bg=UI_HERRAMIENTAS["acento"],
            fg="#00111D",
            activebackground="#0EA5E9",
            activeforeground="#00111D",
            relief="flat",
            command=self._preparar_nueva_nota,
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            barra,
            text="Limpiar",
            font=("Arial", 10, "bold"),
            bg=UI_HERRAMIENTAS["panel"],
            fg=UI_HERRAMIENTAS["texto"],
            activebackground=UI_HERRAMIENTAS["panel_alt"],
            activeforeground=UI_HERRAMIENTAS["texto"],
            relief="flat",
            command=self.limpiar,
        ).pack(side="left", padx=(8, 0))

    def _cargar(self):
        notas = cargar_bloc_notas()
        self.notas = list(notas.get("notas", []))
        self._refrescar_lista()

    def _insertar_prefijo(self, prefijo):
        indice = self.texto_nota.index("insert linestart")
        self.texto_nota.insert(indice, prefijo)
        self.texto_nota.focus_set()

    def _agregar_nota(self):
        titulo = self.entry_titulo_nota.get().strip()
        texto = self.texto_nota.get("1.0", "end-1c").strip()
        if not texto:
            messagebox.showwarning("Bloc de notas", "Escribe una nota.", parent=self)
            return
        if self.nota_editando_id:
            for nota in self.notas:
                if nota.get("id") == self.nota_editando_id:
                    nota["titulo"] = titulo
                    nota["texto"] = texto
                    break
        else:
            self.notas.append(
                {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                    "titulo": titulo,
                    "texto": texto,
                    "tipo": "punto",
                    "completada": False,
                    "creado_en": datetime.now().isoformat(timespec="seconds"),
                }
            )
        self._preparar_nueva_nota()
        self._refrescar_lista()

    def _preparar_nueva_nota(self):
        self.nota_editando_id = None
        self.entry_titulo_nota.delete(0, "end")
        self.texto_nota.delete("1.0", "end")
        self.entry_titulo_nota.focus_set()

    def _cargar_en_editor(self, nota_id):
        for nota in self.notas:
            if nota.get("id") != nota_id:
                continue
            self.nota_editando_id = nota_id
            self.entry_titulo_nota.delete(0, "end")
            self.entry_titulo_nota.insert(0, nota.get("titulo", ""))
            self.texto_nota.delete("1.0", "end")
            self.texto_nota.insert("1.0", nota.get("texto", ""))
            self.texto_nota.focus_set()
            return

    def _eliminar_nota(self, nota_id):
        self.notas = [nota for nota in self.notas if nota.get("id") != nota_id]
        if self.nota_editando_id == nota_id:
            self._preparar_nueva_nota()
        self._refrescar_lista()

    def _refrescar_lista(self):
        for child in self.panel_notas.winfo_children():
            child.destroy()
        if not self.notas:
            tk.Label(
                self.panel_notas,
                text="Sin notas. Agrega una con punto o checklist.",
                font=("Arial", 11),
                bg=UI_HERRAMIENTAS["panel"],
                fg=UI_HERRAMIENTAS["texto_dim"],
            ).pack(anchor="w", padx=14, pady=14)
            return

        for nota in self.notas:
            fila = tk.Frame(self.panel_notas, bg=UI_HERRAMIENTAS["panel_alt"], highlightthickness=1, highlightbackground=UI_HERRAMIENTAS["borde"])
            fila.pack(fill="x", padx=10, pady=6)

            tk.Label(
                fila,
                text="📝",
                font=("Arial", 16, "bold"),
                width=3,
                bg=UI_HERRAMIENTAS["panel_alt"],
                fg=UI_HERRAMIENTAS["texto"],
            ).pack(side="left", padx=(10, 6), pady=10)

            cuerpo = tk.Frame(fila, bg=UI_HERRAMIENTAS["panel_alt"])
            cuerpo.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=12)

            titulo = nota.get("titulo", "").strip()
            if titulo:
                tk.Label(
                    cuerpo,
                    text=titulo,
                    font=("Arial", 12, "bold"),
                    bg=UI_HERRAMIENTAS["panel_alt"],
                    fg=UI_HERRAMIENTAS["texto"],
                    justify="left",
                    wraplength=520,
                ).pack(anchor="w", pady=(0, 4))

            tk.Label(
                cuerpo,
                text=nota.get("texto", ""),
                font=("Arial", 12),
                bg=UI_HERRAMIENTAS["panel_alt"],
                fg=UI_HERRAMIENTAS["texto"],
                justify="left",
                wraplength=420,
            ).pack(anchor="w")

            for widget in (fila, cuerpo):
                widget.bind("<Double-Button-1>", lambda _e, nid=nota.get("id"): self._cargar_en_editor(nid))

            tk.Button(
                fila,
                text="Editar",
                font=("Arial", 9, "bold"),
                bg=UI_HERRAMIENTAS["acento"],
                fg="#00111D",
                activebackground="#0EA5E9",
                activeforeground="#00111D",
                relief="flat",
                command=lambda nid=nota.get("id"): self._cargar_en_editor(nid),
            ).pack(side="right", padx=(0, 8), pady=10)

            tk.Button(
                fila,
                text="Eliminar",
                font=("Arial", 9, "bold"),
                bg=UI_HERRAMIENTAS["error"],
                fg="white",
                activebackground="#DC2626",
                activeforeground="white",
                relief="flat",
                command=lambda nid=nota.get("id"): self._eliminar_nota(nid),
            ).pack(side="right", padx=10, pady=10)

    def guardar(self):
        guardar_bloc_notas(self.notas)
        messagebox.showinfo("Bloc de notas", "Notas guardadas.", parent=self)

    def limpiar(self):
        self.notas = []
        self._refrescar_lista()


class VentanaAlarmas(tk.Toplevel):
    def __init__(self, master, focus_parent=None):
        super().__init__(master)
        self.focus_parent = focus_parent or master
        self.alarmas = cargar_alarmas()
        hoy = datetime.now().strftime("%d-%m-%Y")
        self.title("Alarmas")
        self.configure(bg=UI_HERRAMIENTAS["fondo"])
        aplicar_geometria_relativa(self, self.focus_parent, rel_w=0.72, rel_h=0.76, min_w=980, min_h=700)
        self._crear_ui()
        self.var_modo.set("una_vez")
        self.entry_fecha.insert(0, hoy)
        self.entry_hora.insert(0, "07:00")
        self.var_periodo.set("AM")
        self._actualizar_modo()
        self._refrescar_alarmas()
        _mostrar_encima(self)

    def _crear_ui(self):
        encabezado = tk.Frame(self, bg=UI_HERRAMIENTAS["fondo"])
        encabezado.pack(fill="x", padx=18, pady=(18, 10))
        tk.Label(
            encabezado,
            text="Alarmas",
            font=("Arial", 18, "bold"),
            bg=UI_HERRAMIENTAS["fondo"],
            fg=UI_HERRAMIENTAS["texto"],
        ).pack(side="left")

        principal = tk.Frame(self, bg=UI_HERRAMIENTAS["fondo"])
        principal.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        principal.grid_columnconfigure(0, weight=3)
        principal.grid_columnconfigure(1, weight=2)
        principal.grid_rowconfigure(0, weight=1)

        panel_lista = tk.Frame(principal, bg=UI_HERRAMIENTAS["panel"], highlightthickness=1, highlightbackground=UI_HERRAMIENTAS["borde"])
        panel_lista.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(panel_lista, text="Alarmas configuradas", font=("Arial", 14, "bold"), bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w", padx=14, pady=(14, 8))
        self.lista_alarmas = tk.Listbox(
            panel_lista,
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            selectbackground=UI_HERRAMIENTAS["acento"],
            selectforeground="#00111D",
            relief="flat",
            font=("Arial", 11),
        )
        self.lista_alarmas.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        barra = tk.Frame(panel_lista, bg=UI_HERRAMIENTAS["panel"])
        barra.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(barra, text="Activar / pausar", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["alerta"], fg="white", relief="flat", command=self._alternar_activa).pack(side="left")
        tk.Button(barra, text="Eliminar", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["error"], fg="white", relief="flat", command=self._eliminar_alarma).pack(side="left", padx=(8, 0))

        panel_form = tk.Frame(principal, bg=UI_HERRAMIENTAS["panel"], highlightthickness=1, highlightbackground=UI_HERRAMIENTAS["borde"])
        panel_form.grid(row=0, column=1, sticky="nsew")

        form = tk.Frame(panel_form, bg=UI_HERRAMIENTAS["panel"])
        form.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(form, text="Título", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        self.entry_titulo_alarma = tk.Entry(form, bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], insertbackground="white", relief="flat")
        self.entry_titulo_alarma.pack(fill="x", pady=(4, 8), ipady=6)

        tk.Label(form, text="Hora", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        fila_hora = tk.Frame(form, bg=UI_HERRAMIENTAS["panel"])
        fila_hora.pack(fill="x", pady=(4, 8))
        self.entry_hora = tk.Entry(fila_hora, bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], insertbackground="white", relief="flat")
        self.entry_hora.pack(side="left", fill="x", expand=True, ipady=6)
        self.var_periodo = tk.StringVar(value="AM")
        menu_periodo = tk.OptionMenu(fila_hora, self.var_periodo, "AM", "PM")
        menu_periodo.config(width=6, bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], relief="flat", highlightthickness=0)
        menu_periodo["menu"].config(bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], activebackground=UI_HERRAMIENTAS["acento"], activeforeground="#00111D")
        menu_periodo.pack(side="left", padx=(8, 0))

        tk.Label(form, text="Repetición", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        self.var_modo = tk.StringVar(value="una_vez")
        fila_modo = tk.Frame(form, bg=UI_HERRAMIENTAS["panel"])
        fila_modo.pack(fill="x", pady=(4, 8))
        tk.Radiobutton(fila_modo, text="Una vez", value="una_vez", variable=self.var_modo, command=self._actualizar_modo, bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"], selectcolor=UI_HERRAMIENTAS["panel_alt"], activebackground=UI_HERRAMIENTAS["panel"], activeforeground=UI_HERRAMIENTAS["texto"]).pack(side="left")
        tk.Radiobutton(fila_modo, text="Días de la semana", value="semanal", variable=self.var_modo, command=self._actualizar_modo, bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"], selectcolor=UI_HERRAMIENTAS["panel_alt"], activebackground=UI_HERRAMIENTAS["panel"], activeforeground=UI_HERRAMIENTAS["texto"]).pack(side="left", padx=(12, 0))

        self.frame_fecha = tk.Frame(form, bg=UI_HERRAMIENTAS["panel"])
        self.frame_fecha.pack(fill="x", pady=(0, 8))
        tk.Label(self.frame_fecha, text="Fecha (d-m-a)", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        self.entry_fecha = tk.Entry(self.frame_fecha, bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], insertbackground="white", relief="flat")
        self.entry_fecha.pack(fill="x", pady=(4, 0), ipady=6)

        self.frame_dias = tk.Frame(form, bg=UI_HERRAMIENTAS["panel"])
        self.vars_dias = {}
        tk.Label(self.frame_dias, text="Días", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        fila_dias = tk.Frame(self.frame_dias, bg=UI_HERRAMIENTAS["panel"])
        fila_dias.pack(fill="x", pady=(4, 0))
        for clave, etiqueta, idx in DIAS_SEMANA:
            var = tk.BooleanVar(value=False)
            self.vars_dias[clave] = (var, idx)
            tk.Checkbutton(
                fila_dias,
                text=etiqueta,
                variable=var,
                bg=UI_HERRAMIENTAS["panel"],
                fg=UI_HERRAMIENTAS["texto"],
                selectcolor=UI_HERRAMIENTAS["panel_alt"],
                activebackground=UI_HERRAMIENTAS["panel"],
                activeforeground=UI_HERRAMIENTAS["texto"],
            ).pack(side="left")

        tk.Label(form, text="Sonido", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w", pady=(4, 0))
        opciones_sonido = obtener_opciones_sonido_alerta()
        self.mapa_sonidos_por_label_alarmas = {label: clave for clave, label in opciones_sonido}
        self.var_sonido_alarma = tk.StringVar(value=opciones_sonido[0][1])
        menu_sonido = tk.OptionMenu(form, self.var_sonido_alarma, *[label for _, label in opciones_sonido])
        menu_sonido.config(width=24, bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], relief="flat", highlightthickness=0)
        menu_sonido["menu"].config(bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], activebackground=UI_HERRAMIENTAS["acento"], activeforeground="#00111D")
        menu_sonido.pack(anchor="w", pady=(4, 8))

        tk.Label(form, text="Nota", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        self.entry_nota_alarma = tk.Entry(form, bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], insertbackground="white", relief="flat")
        self.entry_nota_alarma.pack(fill="x", pady=(4, 10), ipady=6)

        tk.Button(form, text="Guardar alarma", font=("Arial", 10, "bold"), bg="#BE185D", fg="white", relief="flat", command=self._guardar_alarma).pack(anchor="w")

    def _actualizar_modo(self):
        modo = self.var_modo.get()
        if modo == "una_vez":
            self.frame_dias.pack_forget()
            self.frame_fecha.pack(fill="x", pady=(0, 8))
        else:
            self.frame_fecha.pack_forget()
            self.frame_dias.pack(fill="x", pady=(0, 8))

    def _refrescar_alarmas(self):
        self.lista_alarmas.delete(0, "end")
        if not self.alarmas:
            self.lista_alarmas.insert("end", "Sin alarmas configuradas.")
            return
        for item in self.alarmas:
            hora = formatear_hora_ampm(item.get("hora", ""))
            repeticion = etiqueta_repeticion(item)
            estado = "Activa" if item.get("activa", True) else "Pausada"
            fecha = formatear_fecha_dma(item.get("fecha", ""))
            texto = f"{fecha} | {hora} | {repeticion} | {estado} | {item.get('titulo', 'Alarma')}"
            if item.get("nota"):
                texto += f" | {item['nota']}"
            self.lista_alarmas.insert("end", texto)

    def _guardar_alarma(self):
        titulo = self.entry_titulo_alarma.get().strip() or "Alarma"
        nota = self.entry_nota_alarma.get().strip()
        hora_base = self.entry_hora.get().strip() or "07:00"
        periodo = self.var_periodo.get().strip() or "AM"
        sonido = self.mapa_sonidos_por_label_alarmas.get(self.var_sonido_alarma.get().strip(), SONIDO_ALERTA_DEFAULT)
        try:
            hora = parsear_hora_recordatorio(f"{hora_base} {periodo}")
        except ValueError:
            messagebox.showwarning("Alarmas", "La hora debe tener formato HH:MM y AM/PM.", parent=self)
            return

        modo = self.var_modo.get().strip() or "una_vez"
        fecha = ""
        dias_semana = []
        if modo == "una_vez":
            fecha_dma = self.entry_fecha.get().strip()
            try:
                fecha = parsear_fecha_dma(fecha_dma)
            except ValueError:
                messagebox.showwarning("Alarmas", "La fecha debe ir como d-m-a.", parent=self)
                return
        else:
            dias_semana = [idx for _, (var, idx) in self.vars_dias.items() if var.get()]
            if not dias_semana:
                messagebox.showwarning("Alarmas", "Selecciona al menos un día de la semana.", parent=self)
                return
            fecha = siguiente_fecha_para_semana(dias_semana)

        self.alarmas.append(
            {
                "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "titulo": titulo,
                "nota": nota,
                "hora": hora,
                "repeticion": modo,
                "fecha": fecha,
                "dias_semana": dias_semana,
                "sonido": sonido,
                "activa": True,
                "creado_en": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.alarmas = sorted(self.alarmas, key=lambda item: (item.get("hora", ""), item.get("titulo", ""), item.get("id", "")))
        guardar_alarmas(self.alarmas)
        self.entry_titulo_alarma.delete(0, "end")
        self.entry_nota_alarma.delete(0, "end")
        self.entry_hora.delete(0, "end")
        self.entry_hora.insert(0, "07:00")
        self.var_periodo.set("AM")
        self.var_modo.set("una_vez")
        self._actualizar_modo()
        self.entry_fecha.delete(0, "end")
        self.entry_fecha.insert(0, datetime.now().strftime("%d-%m-%Y"))
        for var, _ in self.vars_dias.values():
            var.set(False)
        self._refrescar_alarmas()

    def _alarma_seleccionada(self):
        seleccion = self.lista_alarmas.curselection()
        if not seleccion or not self.alarmas:
            return None
        indice = seleccion[0]
        if 0 <= indice < len(self.alarmas):
            return self.alarmas[indice]
        return None

    def _eliminar_alarma(self):
        alarma = self._alarma_seleccionada()
        if not alarma:
            messagebox.showinfo("Alarmas", "Selecciona una alarma.", parent=self)
            return
        self.alarmas = [item for item in self.alarmas if item.get("id") != alarma.get("id")]
        guardar_alarmas(self.alarmas)
        self._refrescar_alarmas()

    def _alternar_activa(self):
        alarma = self._alarma_seleccionada()
        if not alarma:
            messagebox.showinfo("Alarmas", "Selecciona una alarma.", parent=self)
            return
        for item in self.alarmas:
            if item.get("id") == alarma.get("id"):
                item["activa"] = not bool(item.get("activa", True))
                break
        guardar_alarmas(self.alarmas)
        self._refrescar_alarmas()


class VentanaCalendarioRecordatorios(tk.Toplevel):
    def __init__(self, master, focus_parent=None):
        super().__init__(master)
        self.focus_parent = focus_parent or master
        hoy = datetime.now()
        self.anio_actual = hoy.year
        self.mes_actual = hoy.month
        self.fecha_seleccionada = hoy.strftime("%Y-%m-%d")
        self.recordatorios = cargar_recordatorios()

        self.title("Calendario y recordatorios")
        self.configure(bg=UI_HERRAMIENTAS["fondo"])
        aplicar_geometria_relativa(self, self.focus_parent, rel_w=0.72, rel_h=0.74, min_w=980, min_h=680)
        self._crear_ui()
        self._refrescar_calendario()
        self._refrescar_recordatorios()
        self._avisar_pendientes_hoy()
        _mostrar_encima(self)

    def _crear_ui(self):
        encabezado = tk.Frame(self, bg=UI_HERRAMIENTAS["fondo"])
        encabezado.pack(fill="x", padx=18, pady=(18, 10))

        tk.Label(
            encabezado,
            text="Calendario con recordatorios",
            font=("Arial", 18, "bold"),
            bg=UI_HERRAMIENTAS["fondo"],
            fg=UI_HERRAMIENTAS["texto"],
        ).pack(side="left")

        principal = tk.Frame(self, bg=UI_HERRAMIENTAS["fondo"])
        principal.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        principal.grid_columnconfigure(0, weight=3)
        principal.grid_columnconfigure(1, weight=2)
        principal.grid_rowconfigure(0, weight=1)

        panel_cal = tk.Frame(
            principal,
            bg=UI_HERRAMIENTAS["panel"],
            highlightthickness=1,
            highlightbackground=UI_HERRAMIENTAS["borde"],
        )
        panel_cal.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        barra_mes = tk.Frame(panel_cal, bg=UI_HERRAMIENTAS["panel"])
        barra_mes.pack(fill="x", padx=14, pady=(14, 8))

        tk.Button(
            barra_mes,
            text="◀",
            font=("Arial", 11, "bold"),
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            activebackground=UI_HERRAMIENTAS["borde"],
            activeforeground=UI_HERRAMIENTAS["texto"],
            relief="flat",
            command=self._mes_anterior,
        ).pack(side="left")

        self.label_mes = tk.Label(
            barra_mes,
            text="",
            font=("Arial", 14, "bold"),
            bg=UI_HERRAMIENTAS["panel"],
            fg=UI_HERRAMIENTAS["texto"],
        )
        self.label_mes.pack(side="left", padx=12)

        tk.Button(
            barra_mes,
            text="▶",
            font=("Arial", 11, "bold"),
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            activebackground=UI_HERRAMIENTAS["borde"],
            activeforeground=UI_HERRAMIENTAS["texto"],
            relief="flat",
            command=self._mes_siguiente,
        ).pack(side="left")

        self.grid_cal = tk.Frame(panel_cal, bg=UI_HERRAMIENTAS["panel"])
        self.grid_cal.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        panel_lat = tk.Frame(
            principal,
            bg=UI_HERRAMIENTAS["panel"],
            highlightthickness=1,
            highlightbackground=UI_HERRAMIENTAS["borde"],
        )
        panel_lat.grid(row=0, column=1, sticky="nsew")

        self.label_fecha = tk.Label(
            panel_lat,
            text="",
            font=("Arial", 14, "bold"),
            bg=UI_HERRAMIENTAS["panel"],
            fg=UI_HERRAMIENTAS["acento"],
        )
        self.label_fecha.pack(anchor="w", padx=14, pady=(14, 8))

        self.lista = tk.Listbox(
            panel_lat,
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            selectbackground=UI_HERRAMIENTAS["acento"],
            selectforeground="#00111D",
            relief="flat",
            height=8,
        )
        self.lista.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        form = tk.Frame(panel_lat, bg=UI_HERRAMIENTAS["panel"])
        form.pack(fill="x", padx=14, pady=(0, 14))

        tk.Label(form, text="Título", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        self.entry_titulo = tk.Entry(form, bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], insertbackground="white", relief="flat")
        self.entry_titulo.pack(fill="x", pady=(4, 8), ipady=6)

        tk.Label(form, text="Hora", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        fila_hora = tk.Frame(form, bg=UI_HERRAMIENTAS["panel"])
        fila_hora.pack(fill="x", pady=(4, 8))
        self.entry_hora = tk.Entry(
            fila_hora,
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            insertbackground="white",
            relief="flat",
        )
        self.entry_hora.insert(0, "09:00")
        self.entry_hora.pack(side="left", fill="x", expand=True, ipady=6)
        self.var_periodo = tk.StringVar(value="AM")
        self.menu_periodo = tk.OptionMenu(
            fila_hora,
            self.var_periodo,
            "AM",
            "PM",
        )
        self.menu_periodo.config(
            width=6,
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            activebackground=UI_HERRAMIENTAS["borde"],
            activeforeground=UI_HERRAMIENTAS["texto"],
            relief="flat",
            highlightthickness=0,
        )
        self.menu_periodo["menu"].config(
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            activebackground=UI_HERRAMIENTAS["acento"],
            activeforeground="#00111D",
        )
        self.menu_periodo.pack(side="left", padx=(8, 0))

        tk.Label(form, text="Repetición", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        self.var_repeticion = tk.StringVar(value="una_vez")
        repeticiones = tk.Frame(form, bg=UI_HERRAMIENTAS["panel"])
        repeticiones.pack(fill="x", pady=(4, 8))
        tk.Radiobutton(
            repeticiones,
            text="Una vez",
            value="una_vez",
            variable=self.var_repeticion,
            bg=UI_HERRAMIENTAS["panel"],
            fg=UI_HERRAMIENTAS["texto"],
            selectcolor=UI_HERRAMIENTAS["panel_alt"],
            activebackground=UI_HERRAMIENTAS["panel"],
            activeforeground=UI_HERRAMIENTAS["texto"],
        ).pack(side="left")
        tk.Radiobutton(
            repeticiones,
            text="Varias veces",
            value="diaria",
            variable=self.var_repeticion,
            bg=UI_HERRAMIENTAS["panel"],
            fg=UI_HERRAMIENTAS["texto"],
            selectcolor=UI_HERRAMIENTAS["panel_alt"],
            activebackground=UI_HERRAMIENTAS["panel"],
            activeforeground=UI_HERRAMIENTAS["texto"],
        ).pack(side="left", padx=(12, 0))

        tk.Label(form, text="Sonido", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        opciones_sonido = obtener_opciones_sonido_alerta()
        self.mapa_sonidos_por_label = {label: clave for clave, label in opciones_sonido}
        self.var_sonido = tk.StringVar(value=opciones_sonido[0][1])
        self.menu_sonido = tk.OptionMenu(
            form,
            self.var_sonido,
            *[label for _, label in opciones_sonido],
        )
        self.menu_sonido.config(
            width=24,
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            activebackground=UI_HERRAMIENTAS["borde"],
            activeforeground=UI_HERRAMIENTAS["texto"],
            relief="flat",
            highlightthickness=0,
        )
        self.menu_sonido["menu"].config(
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            activebackground=UI_HERRAMIENTAS["acento"],
            activeforeground="#00111D",
        )
        self.menu_sonido.pack(anchor="w", pady=(4, 8))

        tk.Label(form, text="Nota", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w")
        self.entry_nota = tk.Entry(form, bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], insertbackground="white", relief="flat")
        self.entry_nota.pack(fill="x", pady=(4, 10), ipady=6)

        acciones = tk.Frame(form, bg=UI_HERRAMIENTAS["panel"])
        acciones.pack(fill="x")

        tk.Button(
            acciones,
            text="Agregar",
            font=("Arial", 10, "bold"),
            bg="#B45309",
            fg="white",
            activebackground="#92400E",
            activeforeground="white",
            relief="flat",
            command=self._agregar_recordatorio,
        ).pack(side="left")

        tk.Button(
            acciones,
            text="Eliminar",
            font=("Arial", 10, "bold"),
            bg=UI_HERRAMIENTAS["panel_alt"],
            fg=UI_HERRAMIENTAS["texto"],
            activebackground=UI_HERRAMIENTAS["borde"],
            activeforeground=UI_HERRAMIENTAS["texto"],
            relief="flat",
            command=self._eliminar_recordatorio,
        ).pack(side="left", padx=(8, 0))

    def _mes_anterior(self):
        if self.mes_actual == 1:
            self.mes_actual = 12
            self.anio_actual -= 1
        else:
            self.mes_actual -= 1
        self._refrescar_calendario()

    def _mes_siguiente(self):
        if self.mes_actual == 12:
            self.mes_actual = 1
            self.anio_actual += 1
        else:
            self.mes_actual += 1
        self._refrescar_calendario()

    def _refrescar_calendario(self):
        for child in self.grid_cal.winfo_children():
            child.destroy()

        nombre_mes = f"{MESES_ES[self.mes_actual]} {self.anio_actual}"
        self.label_mes.config(text=nombre_mes)

        dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for col, dia in enumerate(dias_semana):
            tk.Label(
                self.grid_cal,
                text=dia,
                font=("Arial", 10, "bold"),
                bg=UI_HERRAMIENTAS["panel"],
                fg=UI_HERRAMIENTAS["texto_dim"],
                width=6,
            ).grid(row=0, column=col, padx=2, pady=(0, 6))

        semanas = calendar.Calendar(firstweekday=0).monthdayscalendar(self.anio_actual, self.mes_actual)
        hoy = datetime.now().strftime("%Y-%m-%d")
        fechas_con_recordatorios = {item.get("fecha") for item in self.recordatorios}

        for fila, semana in enumerate(semanas, start=1):
            for col, dia in enumerate(semana):
                if dia == 0:
                    tk.Label(self.grid_cal, text="", bg=UI_HERRAMIENTAS["panel"], width=6).grid(row=fila, column=col, padx=2, pady=2)
                    continue

                fecha = f"{self.anio_actual:04d}-{self.mes_actual:02d}-{dia:02d}"
                texto = str(dia)
                if fecha in fechas_con_recordatorios:
                    texto = f"{dia} •"

                color_bg = UI_HERRAMIENTAS["panel_alt"]
                color_fg = UI_HERRAMIENTAS["texto"]
                if fecha == hoy:
                    color_bg = "#0F766E"
                if fecha == self.fecha_seleccionada:
                    color_bg = UI_HERRAMIENTAS["acento"]
                    color_fg = "#04101D"

                tk.Button(
                    self.grid_cal,
                    text=texto,
                    width=6,
                    height=2,
                    bg=color_bg,
                    fg=color_fg,
                    activebackground=UI_HERRAMIENTAS["borde"],
                    activeforeground=UI_HERRAMIENTAS["texto"],
                    relief="flat",
                    command=lambda valor=fecha: self._seleccionar_fecha(valor),
                ).grid(row=fila, column=col, padx=2, pady=2, sticky="nsew")

        for col in range(7):
            self.grid_cal.grid_columnconfigure(col, weight=1)

    def _seleccionar_fecha(self, fecha):
        self.fecha_seleccionada = fecha
        self._refrescar_calendario()
        self._refrescar_recordatorios()

    def _recordatorios_fecha(self):
        return [item for item in self.recordatorios if item.get("fecha") == self.fecha_seleccionada]

    def _refrescar_recordatorios(self):
        self.label_fecha.config(text=f"Fecha seleccionada: {self.fecha_seleccionada}")
        self.lista.delete(0, "end")
        for item in self._recordatorios_fecha():
            hora = formatear_hora_ampm(item.get("hora", "--:--"))
            titulo = item.get("titulo", "Sin título")
            nota = item.get("nota", "").strip()
            texto = f"{hora} | {etiqueta_repeticion(item)} | {etiqueta_sonido_alerta(item.get('sonido'))} | {titulo}"
            if nota:
                texto += f" | {nota}"
            self.lista.insert("end", texto)

    def _agregar_recordatorio(self):
        titulo = self.entry_titulo.get().strip()
        hora_base = self.entry_hora.get().strip() or "09:00"
        periodo = self.var_periodo.get().strip() or "AM"
        hora_texto = f"{hora_base} {periodo}"
        nota = self.entry_nota.get().strip()
        repeticion = self.var_repeticion.get().strip() or "una_vez"
        sonido_label = self.var_sonido.get().strip()
        sonido = self.mapa_sonidos_por_label.get(sonido_label, SONIDO_ALERTA_DEFAULT)

        if not titulo:
            messagebox.showwarning("Recordatorios", "El título es obligatorio.", parent=self)
            return

        try:
            hora = parsear_hora_recordatorio(hora_texto)
        except ValueError:
            messagebox.showwarning("Recordatorios", "La hora debe tener formato HH:MM o HH:MM AM/PM.", parent=self)
            return

        self.recordatorios.append(
            {
                "fecha": self.fecha_seleccionada,
                "hora": hora,
                "titulo": titulo,
                "nota": nota,
                "repeticion": repeticion,
                "sonido": sonido,
                "creado_en": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.recordatorios = sorted(self.recordatorios, key=lambda item: (item.get("fecha", ""), item.get("hora", ""), item.get("titulo", "")))
        guardar_recordatorios(self.recordatorios)
        self.entry_titulo.delete(0, "end")
        self.entry_nota.delete(0, "end")
        self.entry_hora.delete(0, "end")
        self.entry_hora.insert(0, "09:00")
        self.var_periodo.set("AM")
        self.var_repeticion.set("una_vez")
        self.var_sonido.set(obtener_opciones_sonido_alerta()[0][1])
        self._refrescar_calendario()
        self._refrescar_recordatorios()

    def _eliminar_recordatorio(self):
        seleccion = self.lista.curselection()
        if not seleccion:
            messagebox.showinfo("Recordatorios", "Selecciona un recordatorio para eliminar.", parent=self)
            return

        recordatorios_fecha = self._recordatorios_fecha()
        indice = seleccion[0]
        objetivo = recordatorios_fecha[indice]
        self.recordatorios.remove(objetivo)
        guardar_recordatorios(self.recordatorios)
        self._refrescar_calendario()
        self._refrescar_recordatorios()

    def _avisar_pendientes_hoy(self):
        hoy = datetime.now().strftime("%Y-%m-%d")
        pendientes = [item for item in self.recordatorios if item.get("fecha") == hoy]
        if not pendientes:
            return
        resumen = "\n".join(f'{formatear_hora_ampm(item.get("hora", "--:--"))} - {etiqueta_repeticion(item)} - {item.get("titulo", "Sin título")}' for item in pendientes[:8])
        if len(pendientes) > 8:
            resumen += f"\n... y {len(pendientes) - 8} más."
        messagebox.showinfo("Recordatorios de hoy", resumen, parent=self)


def _crear_ventana_operativa(master, focus_parent, titulo, rel_w=0.62, rel_h=0.74, min_w=900, min_h=640):
    top = tk.Toplevel(master)
    top.title(titulo)
    top.configure(bg=UI_HERRAMIENTAS["fondo"])
    aplicar_geometria_relativa(top, focus_parent or master, rel_w=rel_w, rel_h=rel_h, min_w=min_w, min_h=min_h)
    _mostrar_encima(top)
    return top


def _crear_panel_operativo(parent, titulo, subtitulo=""):
    panel = tk.Frame(parent, bg=UI_HERRAMIENTAS["panel"], highlightthickness=1, highlightbackground=UI_HERRAMIENTAS["borde"])
    tk.Label(panel, text=titulo, font=("Arial", 14, "bold"), bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).pack(anchor="w", padx=14, pady=(14, 4))
    if subtitulo:
        tk.Label(panel, text=subtitulo, font=("Arial", 10), bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto_dim"], justify="left", wraplength=420).pack(anchor="w", padx=14, pady=(0, 10))
    return panel


def _parse_float_ui(valor):
    try:
        return float(str(valor).strip().replace(",", "."))
    except Exception:
        return None


def _formatear_numero_simple(valor, decimales=2):
    if valor is None:
        return "--"
    if abs(valor - round(valor)) < 1e-9:
        return str(int(round(valor)))
    return f"{valor:.{decimales}f}".rstrip("0").rstrip(".")


def _convertir_frecuencia_hz(valor, unidad):
    factor = {"Hz": 1.0, "kHz": 1000.0, "MHz": 1_000_000.0}.get(unidad, 1.0)
    return valor * factor


def _hz_a_unidades(hz):
    return {
        "Hz": hz,
        "kHz": hz / 1000.0,
        "MHz": hz / 1_000_000.0,
    }


def _convertir_unidades(categoria, valor, origen, destino):
    info = CATALOGO_CONVERSIONES[categoria]
    if info["tipo"] == "lineal":
        unidades = info["unidades"]
        base = valor * unidades[origen]
        return base / unidades[destino]
    if info["tipo"] == "temperatura":
        a_base, _ = info["unidades"][origen]
        _, desde_base = info["unidades"][destino]
        return desde_base(a_base(valor))
    raise ValueError("Categoría de conversión no soportada.")


def _formato_decimal(lat, lon):
    return f"{lat:.6f}, {lon:.6f}"


def _decimal_a_dms(valor, latitud=True):
    hemisferio = ("N" if valor >= 0 else "S") if latitud else ("E" if valor >= 0 else "W")
    valor_abs = abs(valor)
    grados = int(valor_abs)
    minutos_float = (valor_abs - grados) * 60.0
    minutos = int(minutos_float)
    segundos = (minutos_float - minutos) * 60.0
    return f"{grados}° {minutos}' {segundos:.2f}\" {hemisferio}"


def _parse_decimal_coords(texto):
    limpio = str(texto or "").strip()
    match = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*[, ]\s*([+-]?\d+(?:\.\d+)?)\s*$", limpio)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def _parse_dms_single(texto, latitud=True):
    patron = r"([NSWE])?\s*(\d{1,3})[°\s]+(\d{1,2})['\s]+(\d{1,2}(?:\.\d+)?)"
    match = re.search(patron, texto.upper())
    if not match:
        return None
    hemisferio = match.group(1) or ""
    grados = float(match.group(2))
    minutos = float(match.group(3))
    segundos = float(match.group(4))
    decimal = grados + minutos / 60.0 + segundos / 3600.0
    if hemisferio in {"S", "W"}:
        decimal *= -1
    if not hemisferio and "-" in texto:
        decimal *= -1
    limite = 90 if latitud else 180
    if decimal > limite or decimal < -limite:
        return None
    return decimal


def _parse_dms_coords(texto):
    partes = [x.strip() for x in re.split(r"[;,]", str(texto or "").strip()) if x.strip()]
    if len(partes) == 2:
        lat = _parse_dms_single(partes[0], latitud=True)
        lon = _parse_dms_single(partes[1], latitud=False)
        if lat is not None and lon is not None:
            return lat, lon
    tokens = re.findall(r"[NS]?\s*\d{1,3}[°\s]+\d{1,2}['\s]+\d{1,2}(?:\.\d+)?(?:\"\s*)?\s*[NSWE]?", str(texto or "").upper())
    if len(tokens) >= 2:
        lat = _parse_dms_single(tokens[0], latitud=True)
        lon = _parse_dms_single(tokens[1], latitud=False)
        if lat is not None and lon is not None:
            return lat, lon
    return None


class VentanaComunicaciones:
    def __init__(self, master, focus_parent=None):
        self.top = _crear_ventana_operativa(master, focus_parent, "Comunicaciones", rel_w=0.66, rel_h=0.76, min_w=980, min_h=680)
        self.canales = cargar_canales_radio()
        self._crear_ui()
        self._refrescar_canales()

    def _crear_ui(self):
        shell = tk.Frame(self.top, bg=UI_HERRAMIENTAS["fondo"])
        shell.pack(fill="both", expand=True, padx=16, pady=16)
        shell.grid_columnconfigure((0, 1), weight=1, uniform="comms")
        shell.grid_rowconfigure(0, weight=1)

        izquierda = tk.Frame(shell, bg=UI_HERRAMIENTAS["fondo"])
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        derecha = tk.Frame(shell, bg=UI_HERRAMIENTAS["fondo"])
        derecha.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        freq_panel = _crear_panel_operativo(izquierda, "Calculadora de frecuencias", "Convierte Hz, kHz y MHz y estima longitud de onda en aire/vacío.")
        freq_panel.pack(fill="x")
        form = tk.Frame(freq_panel, bg=UI_HERRAMIENTAS["panel"])
        form.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(form, text="Frecuencia", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=0, sticky="w")
        self.entry_freq = tk.Entry(form, font=("Arial", 11))
        self.entry_freq.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.combo_freq = ttk.Combobox(form, values=["Hz", "kHz", "MHz"], state="readonly", width=10)
        self.combo_freq.set("MHz")
        self.combo_freq.grid(row=1, column=1, sticky="ew")
        tk.Button(form, text="Calcular", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["acento"], fg="#04101D", relief="flat", command=self._calcular_frecuencia).grid(row=1, column=2, padx=(8, 0))
        form.grid_columnconfigure(0, weight=1)
        self.result_freq = tk.Label(freq_panel, text="Sin cálculo.", justify="left", bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], anchor="w")
        self.result_freq.pack(fill="x", padx=14, pady=(0, 14))

        canales_panel = _crear_panel_operativo(derecha, "Canales y frecuencias guardadas", "Alta manual persistente para alias, frecuencia, modo y nota.")
        canales_panel.pack(fill="both", expand=True)
        self.tree_canales = ttk.Treeview(canales_panel, columns=("alias", "freq", "modo"), show="headings", height=12)
        for col, titulo, ancho in (("alias", "Alias", 160), ("freq", "Frecuencia", 130), ("modo", "Modo", 120)):
            self.tree_canales.heading(col, text=titulo)
            self.tree_canales.column(col, width=ancho, anchor="center")
        self.tree_canales.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        editor = tk.Frame(canales_panel, bg=UI_HERRAMIENTAS["panel"])
        editor.pack(fill="x", padx=14, pady=(0, 12))
        self.entry_alias = tk.Entry(editor, font=("Arial", 11))
        self.entry_alias.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.entry_ch_freq = tk.Entry(editor, font=("Arial", 11))
        self.entry_ch_freq.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.combo_ch_unit = ttk.Combobox(editor, values=["MHz", "kHz", "Hz"], state="readonly", width=8)
        self.combo_ch_unit.set("MHz")
        self.combo_ch_unit.grid(row=1, column=2, sticky="ew", padx=(0, 8))
        self.entry_modo = tk.Entry(editor, font=("Arial", 11))
        self.entry_modo.grid(row=1, column=3, sticky="ew")
        for idx, texto in enumerate(("Alias", "Frecuencia", "Unidad", "Modo")):
            tk.Label(editor, text=texto, bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=idx, sticky="w", pady=(0, 4))
        tk.Label(editor, text="Nota", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=2, column=0, sticky="w", pady=(8, 4))
        self.entry_nota = tk.Entry(editor, font=("Arial", 11))
        self.entry_nota.grid(row=3, column=0, columnspan=4, sticky="ew")
        for idx in range(4):
            editor.grid_columnconfigure(idx, weight=1)
        acciones = tk.Frame(canales_panel, bg=UI_HERRAMIENTAS["panel"])
        acciones.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(acciones, text="Guardar / actualizar", font=("Arial", 10, "bold"), bg="#0F766E", fg="white", relief="flat", command=self._guardar_canal).pack(side="left")
        tk.Button(acciones, text="Cargar selección", font=("Arial", 10), bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], relief="flat", command=self._cargar_seleccion).pack(side="left", padx=8)
        tk.Button(acciones, text="Eliminar", font=("Arial", 10), bg="#7F1D1D", fg="white", relief="flat", command=self._eliminar_seleccion).pack(side="left")

    def _calcular_frecuencia(self):
        valor = _parse_float_ui(self.entry_freq.get())
        if valor is None or valor <= 0:
            self.result_freq.config(text="Ingresa una frecuencia válida mayor que cero.")
            return
        hz = _convertir_frecuencia_hz(valor, self.combo_freq.get())
        datos = _hz_a_unidades(hz)
        onda = VELOCIDAD_LUZ_M_S / hz
        self.result_freq.config(
            text=(
                f"Hz: {_formatear_numero_simple(datos['Hz'], 3)}\n"
                f"kHz: {_formatear_numero_simple(datos['kHz'], 6)}\n"
                f"MHz: {_formatear_numero_simple(datos['MHz'], 6)}\n"
                f"Longitud de onda estimada: {_formatear_numero_simple(onda, 3)} m"
            )
        )

    def _canal_actual(self):
        alias = self.entry_alias.get().strip()
        frecuencia = self.entry_ch_freq.get().strip()
        if not alias or not frecuencia:
            raise ValueError("Alias y frecuencia son obligatorios.")
        valor = _parse_float_ui(frecuencia)
        if valor is None or valor <= 0:
            raise ValueError("La frecuencia debe ser numérica y mayor que cero.")
        seleccionado = self.tree_canales.selection()
        canal_id = seleccionado[0] if seleccionado else datetime.now().strftime("%Y%m%d%H%M%S%f")
        return {
            "id": canal_id,
            "alias": alias,
            "frecuencia": _formatear_numero_simple(valor, 6),
            "unidad": self.combo_ch_unit.get() or "MHz",
            "modo": self.entry_modo.get().strip(),
            "nota": self.entry_nota.get().strip(),
        }

    def _guardar_canal(self):
        try:
            canal = self._canal_actual()
        except Exception as exc:
            messagebox.showwarning("Comunicaciones", str(exc), parent=self.top)
            return
        reemplazado = False
        for idx, item in enumerate(self.canales):
            if item.get("id") == canal["id"]:
                self.canales[idx] = canal
                reemplazado = True
                break
        if not reemplazado:
            self.canales.append(canal)
        guardar_canales_radio(self.canales)
        self._limpiar_editor()
        self._refrescar_canales()

    def _cargar_seleccion(self):
        seleccion = self.tree_canales.selection()
        if not seleccion:
            return
        canal = next((x for x in self.canales if x.get("id") == seleccion[0]), None)
        if not canal:
            return
        self.entry_alias.delete(0, "end")
        self.entry_alias.insert(0, canal.get("alias", ""))
        self.entry_ch_freq.delete(0, "end")
        self.entry_ch_freq.insert(0, canal.get("frecuencia", ""))
        self.combo_ch_unit.set(canal.get("unidad", "MHz"))
        self.entry_modo.delete(0, "end")
        self.entry_modo.insert(0, canal.get("modo", ""))
        self.entry_nota.delete(0, "end")
        self.entry_nota.insert(0, canal.get("nota", ""))

    def _eliminar_seleccion(self):
        seleccion = self.tree_canales.selection()
        if not seleccion:
            return
        self.canales = [x for x in self.canales if x.get("id") != seleccion[0]]
        guardar_canales_radio(self.canales)
        self._limpiar_editor()
        self._refrescar_canales()

    def _limpiar_editor(self):
        for entry in (self.entry_alias, self.entry_ch_freq, self.entry_modo, self.entry_nota):
            entry.delete(0, "end")
        self.combo_ch_unit.set("MHz")
        self.tree_canales.selection_remove(self.tree_canales.selection())

    def _refrescar_canales(self):
        for item in self.tree_canales.get_children():
            self.tree_canales.delete(item)
        for canal in sorted(self.canales, key=lambda x: (x.get("alias", "").lower(), x.get("frecuencia", ""))):
            self.tree_canales.insert("", "end", iid=canal["id"], values=(canal["alias"], f"{canal['frecuencia']} {canal['unidad']}", canal.get("modo", "") or "--"))


class VentanaConversiones:
    def __init__(self, master, focus_parent=None):
        self.top = _crear_ventana_operativa(master, focus_parent, "Conversiones", rel_w=0.46, rel_h=0.54, min_w=720, min_h=520)
        self._crear_ui()
        self._actualizar_unidades()

    def _crear_ui(self):
        panel = _crear_panel_operativo(self.top, "Conversiones útiles", "Selector de categoría, unidad origen, unidad destino y valor.")
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        grilla = tk.Frame(panel, bg=UI_HERRAMIENTAS["panel"])
        grilla.pack(fill="x", padx=14, pady=(0, 12))
        self.combo_categoria = ttk.Combobox(grilla, values=list(CATALOGO_CONVERSIONES.keys()), state="readonly")
        self.combo_categoria.set(next(iter(CATALOGO_CONVERSIONES)))
        self.combo_categoria.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.combo_categoria.bind("<<ComboboxSelected>>", lambda _e: self._actualizar_unidades())
        self.entry_valor = tk.Entry(grilla, font=("Arial", 11))
        self.entry_valor.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.combo_origen = ttk.Combobox(grilla, state="readonly")
        self.combo_origen.grid(row=1, column=2, sticky="ew", padx=(0, 8))
        self.combo_destino = ttk.Combobox(grilla, state="readonly")
        self.combo_destino.grid(row=1, column=3, sticky="ew")
        for idx, texto in enumerate(("Categoría", "Valor", "Origen", "Destino")):
            tk.Label(grilla, text=texto, bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=idx, sticky="w", pady=(0, 4))
            grilla.grid_columnconfigure(idx, weight=1)
        acciones = tk.Frame(panel, bg=UI_HERRAMIENTAS["panel"])
        acciones.pack(fill="x", padx=14, pady=(0, 12))
        tk.Button(acciones, text="Convertir", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["acento"], fg="#04101D", relief="flat", command=self._convertir).pack(side="left")
        self.resultado = tk.Label(panel, text="Sin conversión.", justify="left", bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], anchor="w")
        self.resultado.pack(fill="x", padx=14, pady=(0, 14))

    def _actualizar_unidades(self):
        categoria = self.combo_categoria.get()
        unidades = list(CATALOGO_CONVERSIONES[categoria]["unidades"].keys())
        self.combo_origen.configure(values=unidades)
        self.combo_destino.configure(values=unidades)
        if unidades:
            self.combo_origen.set(unidades[0])
            self.combo_destino.set(unidades[1] if len(unidades) > 1 else unidades[0])

    def _convertir(self):
        valor = _parse_float_ui(self.entry_valor.get())
        if valor is None:
            self.resultado.config(text="Ingresa un valor numérico válido.")
            return
        categoria = self.combo_categoria.get()
        origen = self.combo_origen.get()
        destino = self.combo_destino.get()
        try:
            convertido = _convertir_unidades(categoria, valor, origen, destino)
        except Exception as exc:
            self.resultado.config(text=f"No se pudo convertir: {exc}")
            return
        self.resultado.config(text=f"{_formatear_numero_simple(valor, 6)} {origen} = {_formatear_numero_simple(convertido, 6)} {destino}")


class VentanaEnergia:
    def __init__(self, master, focus_parent=None):
        self.top = _crear_ventana_operativa(master, focus_parent, "Calculadora de energía", rel_w=0.72, rel_h=0.78, min_w=1040, min_h=720)
        self.cargas = cargar_cargas_energia()
        self._crear_ui()
        self._refrescar_cargas()

    def _crear_ui(self):
        notebook = ttk.Notebook(self.top)
        notebook.pack(fill="both", expand=True, padx=16, pady=16)
        self.tab_autonomia = tk.Frame(notebook, bg=UI_HERRAMIENTAS["fondo"])
        self.tab_solar = tk.Frame(notebook, bg=UI_HERRAMIENTAS["fondo"])
        self.tab_cargas = tk.Frame(notebook, bg=UI_HERRAMIENTAS["fondo"])
        notebook.add(self.tab_autonomia, text="Autonomía")
        notebook.add(self.tab_solar, text="Carga solar")
        notebook.add(self.tab_cargas, text="Consumo diario")
        self._crear_tab_autonomia()
        self._crear_tab_solar()
        self._crear_tab_cargas()

    def _crear_tab_autonomia(self):
        panel = _crear_panel_operativo(self.tab_autonomia, "Autonomía de batería", "Calcula duración estimada según capacidad y consumo.")
        panel.pack(fill="both", expand=True, padx=8, pady=8)
        grid = tk.Frame(panel, bg=UI_HERRAMIENTAS["panel"])
        grid.pack(fill="x", padx=14, pady=(0, 12))
        campos = [("Batería (Wh)", "entry_batt_wh"), ("Batería (Ah)", "entry_batt_ah"), ("Voltaje (V)", "entry_batt_v"), ("Carga (W)", "entry_load_w"), ("Eficiencia (%)", "entry_eff")]
        for idx, (texto, attr) in enumerate(campos):
            tk.Label(grid, text=texto, bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0 if idx < 3 else 2, column=idx % 3, sticky="w", pady=(0 if idx < 3 else 8, 4))
            entry = tk.Entry(grid, font=("Arial", 11))
            entry.grid(row=1 if idx < 3 else 3, column=idx % 3, sticky="ew", padx=(0, 8))
            setattr(self, attr, entry)
            grid.grid_columnconfigure(idx % 3, weight=1)
        self.entry_eff.insert(0, "85")
        tk.Button(panel, text="Calcular autonomía", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["acento"], fg="#04101D", relief="flat", command=self._calcular_autonomia).pack(anchor="w", padx=14, pady=(0, 12))
        self.result_autonomia = tk.Label(panel, text="Sin cálculo.", justify="left", bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], anchor="w")
        self.result_autonomia.pack(fill="x", padx=14, pady=(0, 14))

    def _crear_tab_solar(self):
        panel = _crear_panel_operativo(self.tab_solar, "Relación panel / batería / carga", "Estimación simple de recarga con horas solares pico y eficiencia.")
        panel.pack(fill="both", expand=True, padx=8, pady=8)
        grid = tk.Frame(panel, bg=UI_HERRAMIENTAS["panel"])
        grid.pack(fill="x", padx=14, pady=(0, 12))
        campos = [("Panel (W)", "entry_panel_w"), ("Horas solares pico", "entry_sun_h"), ("Batería objetivo (Wh)", "entry_target_wh"), ("Consumo diario (Wh)", "entry_daily_wh"), ("Eficiencia (%)", "entry_solar_eff")]
        for idx, (texto, attr) in enumerate(campos):
            tk.Label(grid, text=texto, bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0 if idx < 3 else 2, column=idx % 3, sticky="w", pady=(0 if idx < 3 else 8, 4))
            entry = tk.Entry(grid, font=("Arial", 11))
            entry.grid(row=1 if idx < 3 else 3, column=idx % 3, sticky="ew", padx=(0, 8))
            setattr(self, attr, entry)
            grid.grid_columnconfigure(idx % 3, weight=1)
        self.entry_solar_eff.insert(0, "80")
        tk.Button(panel, text="Calcular recarga", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["acento"], fg="#04101D", relief="flat", command=self._calcular_solar).pack(anchor="w", padx=14, pady=(0, 12))
        self.result_solar = tk.Label(panel, text="Sin cálculo.", justify="left", bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], anchor="w")
        self.result_solar.pack(fill="x", padx=14, pady=(0, 14))

    def _crear_tab_cargas(self):
        panel = _crear_panel_operativo(self.tab_cargas, "Cargas diarias", "Guarda consumos por equipo. El total diario queda persistente localmente.")
        panel.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree_cargas = ttk.Treeview(panel, columns=("nombre", "w", "h", "cant", "wh"), show="headings", height=12)
        for col, titulo, ancho in (("nombre", "Equipo", 180), ("w", "W", 80), ("h", "h/día", 80), ("cant", "Cantidad", 80), ("wh", "Wh/día", 100)):
            self.tree_cargas.heading(col, text=titulo)
            self.tree_cargas.column(col, width=ancho, anchor="center")
        self.tree_cargas.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        grid = tk.Frame(panel, bg=UI_HERRAMIENTAS["panel"])
        grid.pack(fill="x", padx=14, pady=(0, 10))
        for idx, (texto, attr) in enumerate((("Equipo", "entry_carga_nombre"), ("W", "entry_carga_w"), ("Horas/día", "entry_carga_h"), ("Cantidad", "entry_carga_cantidad"))):
            tk.Label(grid, text=texto, bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=idx, sticky="w", pady=(0, 4))
            entry = tk.Entry(grid, font=("Arial", 11))
            entry.grid(row=1, column=idx, sticky="ew", padx=(0, 8))
            setattr(self, attr, entry)
            grid.grid_columnconfigure(idx, weight=1)
        self.entry_carga_cantidad.insert(0, "1")
        acciones = tk.Frame(panel, bg=UI_HERRAMIENTAS["panel"])
        acciones.pack(fill="x", padx=14, pady=(0, 10))
        tk.Button(acciones, text="Guardar carga", font=("Arial", 10, "bold"), bg="#0F766E", fg="white", relief="flat", command=self._guardar_carga).pack(side="left")
        tk.Button(acciones, text="Cargar selección", font=("Arial", 10), bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], relief="flat", command=self._cargar_carga).pack(side="left", padx=8)
        tk.Button(acciones, text="Eliminar", font=("Arial", 10), bg="#7F1D1D", fg="white", relief="flat", command=self._eliminar_carga).pack(side="left")
        self.result_cargas = tk.Label(panel, text="Sin cargas registradas.", justify="left", bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], anchor="w")
        self.result_cargas.pack(fill="x", padx=14, pady=(0, 14))

    def _calcular_autonomia(self):
        wh = _parse_float_ui(self.entry_batt_wh.get())
        ah = _parse_float_ui(self.entry_batt_ah.get())
        volt = _parse_float_ui(self.entry_batt_v.get())
        carga = _parse_float_ui(self.entry_load_w.get())
        eficiencia = (_parse_float_ui(self.entry_eff.get()) or 100.0) / 100.0
        if wh is None and ah is not None and volt is not None:
            wh = ah * volt
        if wh is None or carga is None or carga <= 0:
            self.result_autonomia.config(text="Ingresa batería en Wh, o Ah con V, y una carga en W.")
            return
        horas = (wh * max(0.0, eficiencia)) / carga
        self.result_autonomia.config(text=f"Energía útil estimada: {_formatear_numero_simple(wh * eficiencia, 2)} Wh\nAutonomía estimada: {_formatear_numero_simple(horas, 2)} horas")

    def _calcular_solar(self):
        panel_w = _parse_float_ui(self.entry_panel_w.get())
        sol_h = _parse_float_ui(self.entry_sun_h.get())
        target_wh = _parse_float_ui(self.entry_target_wh.get())
        consumo_wh = _parse_float_ui(self.entry_daily_wh.get()) or 0.0
        eficiencia = (_parse_float_ui(self.entry_solar_eff.get()) or 100.0) / 100.0
        if panel_w is None or sol_h is None or panel_w <= 0 or sol_h <= 0:
            self.result_solar.config(text="Ingresa potencia del panel y horas solares pico válidas.")
            return
        produccion = panel_w * sol_h * max(0.0, eficiencia)
        lineas = [f"Producción diaria estimada: {_formatear_numero_simple(produccion, 2)} Wh"]
        if target_wh and target_wh > 0:
            dias = target_wh / produccion if produccion > 0 else None
            lineas.append(f"Días para cargar {target_wh:.0f} Wh: {_formatear_numero_simple(dias, 2)}")
        if consumo_wh > 0:
            balance = produccion - consumo_wh
            lineas.append(f"Balance diario frente a {consumo_wh:.0f} Wh de consumo: {_formatear_numero_simple(balance, 2)} Wh")
        self.result_solar.config(text="\n".join(lineas))

    def _guardar_carga(self):
        nombre = self.entry_carga_nombre.get().strip()
        w = _parse_float_ui(self.entry_carga_w.get())
        h = _parse_float_ui(self.entry_carga_h.get())
        cantidad = _parse_float_ui(self.entry_carga_cantidad.get()) or 1.0
        if not nombre or w is None or h is None or cantidad <= 0:
            messagebox.showwarning("Energía", "Captura equipo, W, horas/día y cantidad válidos.", parent=self.top)
            return
        seleccion = self.tree_cargas.selection()
        carga_id = seleccion[0] if seleccion else datetime.now().strftime("%Y%m%d%H%M%S%f")
        nuevo = {"id": carga_id, "nombre": nombre, "w": _formatear_numero_simple(w, 3), "h": _formatear_numero_simple(h, 3), "cantidad": _formatear_numero_simple(cantidad, 3)}
        actualizado = False
        for idx, item in enumerate(self.cargas):
            if item.get("id") == carga_id:
                self.cargas[idx] = nuevo
                actualizado = True
                break
        if not actualizado:
            self.cargas.append(nuevo)
        guardar_cargas_energia(self.cargas)
        self._limpiar_carga()
        self._refrescar_cargas()

    def _cargar_carga(self):
        seleccion = self.tree_cargas.selection()
        if not seleccion:
            return
        item = next((x for x in self.cargas if x.get("id") == seleccion[0]), None)
        if not item:
            return
        self.entry_carga_nombre.delete(0, "end")
        self.entry_carga_nombre.insert(0, item.get("nombre", ""))
        self.entry_carga_w.delete(0, "end")
        self.entry_carga_w.insert(0, item.get("w", ""))
        self.entry_carga_h.delete(0, "end")
        self.entry_carga_h.insert(0, item.get("h", ""))
        self.entry_carga_cantidad.delete(0, "end")
        self.entry_carga_cantidad.insert(0, item.get("cantidad", "1"))

    def _eliminar_carga(self):
        seleccion = self.tree_cargas.selection()
        if not seleccion:
            return
        self.cargas = [x for x in self.cargas if x.get("id") != seleccion[0]]
        guardar_cargas_energia(self.cargas)
        self._limpiar_carga()
        self._refrescar_cargas()

    def _limpiar_carga(self):
        for entry in (self.entry_carga_nombre, self.entry_carga_w, self.entry_carga_h, self.entry_carga_cantidad):
            entry.delete(0, "end")
        self.entry_carga_cantidad.insert(0, "1")

    def _refrescar_cargas(self):
        for item in self.tree_cargas.get_children():
            self.tree_cargas.delete(item)
        total = 0.0
        for carga in self.cargas:
            w = _parse_float_ui(carga.get("w")) or 0.0
            h = _parse_float_ui(carga.get("h")) or 0.0
            cantidad = _parse_float_ui(carga.get("cantidad")) or 1.0
            wh = w * h * cantidad
            total += wh
            self.tree_cargas.insert("", "end", iid=carga["id"], values=(carga.get("nombre", ""), _formatear_numero_simple(w, 2), _formatear_numero_simple(h, 2), _formatear_numero_simple(cantidad, 2), _formatear_numero_simple(wh, 2)))
        self.result_cargas.config(text=f"Consumo diario total estimado: {_formatear_numero_simple(total, 2)} Wh/día")


class VentanaDosificacionMedica:
    def __init__(self, master, focus_parent=None):
        self.top = _crear_ventana_operativa(master, focus_parent, "Dosificación médica básica", rel_w=0.44, rel_h=0.56, min_w=700, min_h=560)
        self._crear_ui()

    def _crear_ui(self):
        panel = _crear_panel_operativo(self.top, "Dosificación médica básica", "Herramienta informativa conservadora. No sustituye valoración clínica ni protocolos formales.")
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        aviso = tk.Label(panel, text="Usa esta salida como orientación básica. Si hay alergia, embarazo, deshidratación severa, vómitos persistentes, hemorragia, estado mental alterado o enfermedad de base relevante, no te apoyes solo en este cálculo.", justify="left", bg="#3A1318", fg="#FECACA", wraplength=620, padx=12, pady=10)
        aviso.pack(fill="x", padx=14, pady=(0, 12))
        grid = tk.Frame(panel, bg=UI_HERRAMIENTAS["panel"])
        grid.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(grid, text="Medicamento", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=0, sticky="w", pady=(0, 4))
        tk.Label(grid, text="Edad (años)", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=1, sticky="w", pady=(0, 4))
        tk.Label(grid, text="Peso (kg)", bg=UI_HERRAMIENTAS["panel"], fg=UI_HERRAMIENTAS["texto"]).grid(row=0, column=2, sticky="w", pady=(0, 4))
        self.combo_medicamento = ttk.Combobox(grid, values=list(DOSIS_MEDICAS.keys()), state="readonly")
        self.combo_medicamento.set("Paracetamol")
        self.combo_medicamento.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.entry_edad = tk.Entry(grid, font=("Arial", 11))
        self.entry_edad.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        self.entry_peso = tk.Entry(grid, font=("Arial", 11))
        self.entry_peso.grid(row=1, column=2, sticky="ew")
        for idx in range(3):
            grid.grid_columnconfigure(idx, weight=1)
        tk.Button(panel, text="Calcular orientación", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["acento"], fg="#04101D", relief="flat", command=self._calcular).pack(anchor="w", padx=14, pady=(0, 12))
        self.resultado = tk.Label(panel, text="Sin cálculo.", justify="left", bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], anchor="w")
        self.resultado.pack(fill="x", padx=14, pady=(0, 14))

    def _calcular(self):
        med = DOSIS_MEDICAS[self.combo_medicamento.get()]
        edad = _parse_float_ui(self.entry_edad.get()) or 0.0
        peso = _parse_float_ui(self.entry_peso.get())
        edad_meses = edad * 12.0
        if edad_meses < med.get("edad_min_meses", 0):
            self.resultado.config(text=f"Este cálculo orientativo no aplica por debajo de {med['edad_min_meses']} meses.\n\n{med['nota']}")
            return
        if med["tipo"] == "mg_kg":
            if peso is None or peso <= 0:
                self.resultado.config(text="Para este medicamento necesitas capturar un peso válido.")
                return
            pediatrico = edad < 12 or peso < 50
            if pediatrico:
                dmin = peso * med["pediatrico_kg_dosis"][0]
                dmax = peso * med["pediatrico_kg_dosis"][1]
                maxdia = peso * med["pediatrico_max_mg_kg_dia"]
                texto = (
                    f"Dosis orientativa: {round(dmin)} a {round(dmax)} mg por toma\n"
                    f"Intervalo: {med['pediatrico_intervalo']}\n"
                    f"Máximo orientativo al día: {round(maxdia)} mg/día\n\n"
                    f"{med['nota']}"
                )
            else:
                texto = (
                    f"Dosis orientativa: {med['adulto_dosis_mg'][0]} a {med['adulto_dosis_mg'][1]} mg por toma\n"
                    f"Intervalo: {med['adulto_intervalo']}\n"
                    f"Máximo orientativo al día: {med['adulto_max_mg_dia']} mg/día\n\n"
                    f"{med['nota']}"
                )
            self.resultado.config(text=texto)
            return
        if med["tipo"] == "rehidratacion":
            if peso is None or peso <= 0:
                self.resultado.config(text="Para la solución de hidratación oral captura peso en kg.")
                return
            if edad < 18:
                inicial = peso * 75.0
                reposicion = peso * 10.0
                texto = (
                    f"Rehidratación inicial orientativa: {round(inicial)} mL en 4 horas\n"
                    f"Reposición orientativa: {round(reposicion)} mL después de cada evacuación o vómito\n\n"
                    f"{med['nota']}"
                )
            else:
                texto = (
                    "Orientación general en adulto: 200 a 400 mL después de cada evacuación o vómito, a sorbos continuos.\n"
                    "Si no tolera líquidos, hay somnolencia, signos de choque o empeora, se necesita atención médica.\n\n"
                    f"{med['nota']}"
                )
            self.resultado.config(text=texto)


class VentanaCoordenadas:
    def __init__(self, master, focus_parent=None):
        self.top = _crear_ventana_operativa(master, focus_parent, "Decodificador de coordenadas", rel_w=0.5, rel_h=0.5, min_w=760, min_h=520)
        self._crear_ui()

    def _crear_ui(self):
        panel = _crear_panel_operativo(self.top, "Decodificador de coordenadas", "Acepta decimal y grados/minutos/segundos. Guarda el último resultado para futura conexión con Mapa.")
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        self.entry_texto = tk.Text(panel, height=5, font=("Arial", 11), bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], insertbackground=UI_HERRAMIENTAS["texto"], relief="flat")
        self.entry_texto.pack(fill="x", padx=14, pady=(0, 12))
        ultimo = cargar_ultimo_resultado_coordenadas()
        if ultimo.get("original"):
            self.entry_texto.insert("1.0", ultimo.get("original", ""))
        acciones = tk.Frame(panel, bg=UI_HERRAMIENTAS["panel"])
        acciones.pack(fill="x", padx=14, pady=(0, 12))
        tk.Button(acciones, text="Interpretar", font=("Arial", 10, "bold"), bg=UI_HERRAMIENTAS["acento"], fg="#04101D", relief="flat", command=self._interpretar).pack(side="left")
        tk.Button(acciones, text="Copiar decimal", font=("Arial", 10), bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], relief="flat", command=lambda: self._copiar("decimal")).pack(side="left", padx=8)
        tk.Button(acciones, text="Copiar DMS", font=("Arial", 10), bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], relief="flat", command=lambda: self._copiar("dms")).pack(side="left")
        self.resultado = tk.Label(panel, text="Sin coordenadas interpretadas.", justify="left", bg=UI_HERRAMIENTAS["panel_alt"], fg=UI_HERRAMIENTAS["texto"], anchor="w")
        self.resultado.pack(fill="x", padx=14, pady=(0, 14))
        self._ultimo = {"decimal": "", "dms": ""}

    def _interpretar(self):
        original = self.entry_texto.get("1.0", "end").strip()
        coords = _parse_decimal_coords(original) or _parse_dms_coords(original)
        if not coords:
            self.resultado.config(text="No se pudo interpretar. Prueba con '19.432608, -99.133209' o '19° 25' 57.39\" N, 99° 7' 59.55\" W'.")
            return
        lat, lon = coords
        decimal = _formato_decimal(lat, lon)
        dms = f"{_decimal_a_dms(lat, True)} | {_decimal_a_dms(lon, False)}"
        self._ultimo = {"decimal": decimal, "dms": dms}
        guardar_ultimo_resultado_coordenadas({"original": original, "decimal": decimal, "dms": dms, "lat": lat, "lon": lon})
        self.resultado.config(text=f"Formato decimal:\n{decimal}\n\nFormato DMS:\n{dms}\n\nListo para integración futura con Mapa.")

    def _copiar(self, clave):
        texto = self._ultimo.get(clave, "")
        if not texto:
            return
        self.top.clipboard_clear()
        self.top.clipboard_append(texto)
