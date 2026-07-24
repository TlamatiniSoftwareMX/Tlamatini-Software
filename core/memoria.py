import json
import os
import threading
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from core.path_manager import APP_ASSETS_DIR, PROJECT_ROOT, get_paths


APP_DIR = PROJECT_ROOT
BASE_DIR = APP_DIR
_APP_PATHS = get_paths()
DATA_DIR = _APP_PATHS.data_dir
RUTA_BASE_DATOS = DATA_DIR / "base_datos"
RUTA_MEMORIA_JSON = _APP_PATHS.memory_json
RUTA_MEMORIA_AUX = _APP_PATHS.memory_aux_dir
RUTA_LOGS = _APP_PATHS.logs_file
RUTA_CACHE_LIBROS = _APP_PATHS.books_cache_dir

_MEMORIA_LOCK = threading.RLock()


def _set_secure_permissions(path: Path, *, is_dir: bool) -> None:
    if os.name == "nt":
        return
    try:
        os.chmod(path, 0o700 if is_dir else 0o600)
    except Exception:
        pass


ESTRUCTURA_BASE: Dict[str, Any] = {
    "configuracion": {
        "nombre_sistema": "TLAMATINI IA",
        "modo_operacion": "local",
        "version": "5.2.4",
        "tema": {
            "color_principal": "#0F172A",
            "color_secundario": "#111827",
            "color_acento": "#2563EB",
            "color_alerta": "#DC2626",
            "color_exito": "#059669",
            "color_panel": "#1F2937",
            "color_texto": "#FFFFFF",
            "color_texto_secundario": "#D1D5DB"
        },
        "voz": {
            "activacion_por_boton": True,
            "activacion_por_palabra": True,
            "palabra_activacion": "TLAMATINI",
            "voz_genero": "masculina",
            "modo_respuesta": "resumen"
        },
        "vision": {
            "modo_captura": "foto_fija",
            "pregunta_obligatoria": True
        },
        "seguridad": {
            "clave_admin_configurada": False,
            "modulos_protegidos": [
                "core",
                "interfaz",
                "sistema",
                "main.py"
            ]
        }
    },

    "dominios": [
        {
            "id": "DOM-medica",
            "nombre": "medica",
            "descripcion": "Dominio médico general",
            "subdominios": [
                "urgencias",
                "farmacologia",
                "anatomia",
                "fisiologia",
                "ginecologia",
                "pediatria",
                "semiologia",
                "procedimientos",
                "trauma"
            ]
        },
        {
            "id": "DOM-proteccion_civil",
            "nombre": "proteccion_civil",
            "descripcion": "Protección civil y operación táctica",
            "subdominios": [
                "rescate",
                "cuerdas",
                "evacuacion",
                "incendios",
                "materiales_peligrosos",
                "seguridad_e_higiene",
                "gestion_de_riesgos"
            ]
        },
        {
            "id": "DOM-autosuficiencia",
            "nombre": "autosuficiencia",
            "descripcion": "Autosuficiencia y vida operativa",
            "subdominios": [
                "siembra",
                "cria_de_animales",
                "captacion_de_agua",
                "conservacion_de_alimentos",
                "estufas_de_lena",
                "huertos"
            ]
        },
        {
            "id": "DOM-instalacion_mantenimiento_reparacion",
            "nombre": "instalacion_mantenimiento_reparacion",
            "descripcion": "Instalación, mantenimiento y reparación",
            "subdominios": [
                "automovil",
                "motocicleta",
                "residencial",
                "herramientas",
                "equipos_medicos",
                "electricidad",
                "electronica",
                "paneles_solares"
            ]
        },
        {
            "id": "DOM-animales",
            "nombre": "animales",
            "descripcion": "Manejo y control de animales",
            "subdominios": [
                "perros",
                "gallinas",
                "caprinos",
                "bovinos",
                "alimento",
                "agua",
                "sanidad",
                "reproduccion"
            ]
        }
    ],

    "biblioteca": [],
    "conocimiento": [],
    "indices_conocimiento": [],

    "conversacion": {
        "tema_actual": "",
        "ultimo_dominio": "",
        "ultima_intencion": "",
        "historial": []
    },

    "personas": [],
    "animales": [],
    "inventario": [],
    "planes": [],
    "imagenes": [],

    "mapa": {
        "puntos_interes": [],
        "poligonos_riesgo": []
    },

    "nodos": [],
    "sensores": [],
    "lecturas": [],
    "alertas": [],
    "protocolos": [],
    "eventos": [],
    "incidentes": [],
    "reglas": [],
    "papelera": [],
    "logs_sistema": []
}


def fusionar_estructura(base: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fusiona la estructura base con la memoria existente sin perder datos ya guardados.
    """
    resultado = deepcopy(base)

    for clave, valor in data.items():
        if isinstance(valor, dict) and isinstance(resultado.get(clave), dict):
            resultado[clave] = fusionar_estructura(resultado[clave], valor)
        else:
            resultado[clave] = valor

    return resultado


def asegurar_estructura() -> None:
    """
    Garantiza que existan carpetas y archivos mínimos del sistema.
    """
    RUTA_BASE_DATOS.mkdir(parents=True, exist_ok=True)
    RUTA_MEMORIA_AUX.mkdir(parents=True, exist_ok=True)
    RUTA_CACHE_LIBROS.mkdir(parents=True, exist_ok=True)
    _set_secure_permissions(RUTA_BASE_DATOS, is_dir=True)
    _set_secure_permissions(RUTA_MEMORIA_AUX, is_dir=True)
    _set_secure_permissions(RUTA_CACHE_LIBROS, is_dir=True)

    if not RUTA_MEMORIA_JSON.exists():
        _escritura_atomica_json(RUTA_MEMORIA_JSON, deepcopy(ESTRUCTURA_BASE))

    if not RUTA_LOGS.exists():
        RUTA_LOGS.write_text("", encoding="utf-8")
        _set_secure_permissions(RUTA_LOGS, is_dir=False)


def cargar_memoria() -> Dict[str, Any]:
    """
    Carga memoria y completa automáticamente cualquier sección faltante.
    """
    with _MEMORIA_LOCK:
        asegurar_estructura()

        for _ in range(3):
            try:
                with open(RUTA_MEMORIA_JSON, "r", encoding="utf-8") as archivo:
                    data = json.load(archivo)
                break
            except FileNotFoundError:
                data = deepcopy(ESTRUCTURA_BASE)
                guardar_memoria(data)
                return data
            except json.JSONDecodeError:
                # Una lectura inválida suele indicar que otro hilo/proceso está reemplazando
                # el archivo. Reintentamos antes de asumir corrupción real.
                continue
        else:
            data = deepcopy(ESTRUCTURA_BASE)
            guardar_memoria(data)
            return data

        memoria_fusionada = fusionar_estructura(ESTRUCTURA_BASE, data)

        # Si se completaron secciones nuevas, persistir la memoria ya normalizada.
        if memoria_fusionada != data:
            guardar_memoria(memoria_fusionada)

        return memoria_fusionada


def guardar_memoria(data: Dict[str, Any]) -> None:
    """
    Guarda la memoria completa del sistema.
    """
    with _MEMORIA_LOCK:
        asegurar_estructura()
        _escritura_atomica_json(RUTA_MEMORIA_JSON, data)


def _escritura_atomica_json(ruta: Path, data: Dict[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _set_secure_permissions(ruta.parent, is_dir=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(ruta.parent),
        prefix=f"{ruta.name}.",
        suffix=".tmp",
        delete=False,
    ) as archivo:
        temporal = Path(archivo.name)
        json.dump(data, archivo, indent=4, ensure_ascii=False)
        archivo.flush()
        os.fsync(archivo.fileno())
    os.replace(temporal, ruta)
    _set_secure_permissions(ruta, is_dir=False)


def obtener_seccion(nombre_seccion: str, default: Optional[Any] = None) -> Any:
    memoria = cargar_memoria()
    return memoria.get(nombre_seccion, default)


def guardar_seccion(nombre_seccion: str, contenido: Any) -> None:
    memoria = cargar_memoria()
    memoria[nombre_seccion] = contenido
    guardar_memoria(memoria)


def agregar_a_seccion(nombre_seccion: str, item: Any):
    memoria = cargar_memoria()

    if nombre_seccion not in memoria or not isinstance(memoria[nombre_seccion], list):
        memoria[nombre_seccion] = []

    memoria[nombre_seccion].append(item)
    guardar_memoria(memoria)
    return memoria[nombre_seccion]


def actualizar_elemento(
    nombre_seccion: str,
    clave_busqueda: str,
    valor_busqueda: Any,
    nuevos_datos: Dict[str, Any]
) -> bool:
    memoria = cargar_memoria()
    seccion = memoria.get(nombre_seccion, [])

    if not isinstance(seccion, list):
        return False

    for elemento in seccion:
        if elemento.get(clave_busqueda) == valor_busqueda:
            elemento.update(nuevos_datos)
            guardar_memoria(memoria)
            return True

    return False


def eliminar_elemento(nombre_seccion: str, clave_busqueda: str, valor_busqueda: Any) -> Optional[Dict[str, Any]]:
    memoria = cargar_memoria()
    seccion = memoria.get(nombre_seccion, [])

    if not isinstance(seccion, list):
        return None

    eliminado = None
    nueva = []

    for elemento in seccion:
        if eliminado is None and elemento.get(clave_busqueda) == valor_busqueda:
            eliminado = elemento
        else:
            nueva.append(elemento)

    if eliminado is not None:
        memoria[nombre_seccion] = nueva
        guardar_memoria(memoria)

    return eliminado


def buscar_en_seccion(nombre_seccion: str, clave: str, valor: Any):
    seccion = obtener_seccion(nombre_seccion, [])
    if not isinstance(seccion, list):
        return None

    for elemento in seccion:
        if elemento.get(clave) == valor:
            return elemento

    return None
