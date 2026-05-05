from typing import Callable, Dict, Optional


REGISTRO_MODULOS: Dict[str, Dict] = {}


def limpiar_modulos() -> None:
    REGISTRO_MODULOS.clear()


def registrar_modulo(
    id_modulo: str,
    titulo: str,
    icono: str,
    funcion: Callable,
    color: Optional[str] = None,
    tipo: str = "nativo"
) -> None:
    REGISTRO_MODULOS[id_modulo] = {
        "id": id_modulo,
        "titulo": titulo,
        "icono": icono,
        "funcion": funcion,
        "color": color,
        "tipo": tipo
    }


def obtener_modulo(id_modulo: str) -> Optional[Dict]:
    return REGISTRO_MODULOS.get(id_modulo)


def listar_modulos():
    return list(REGISTRO_MODULOS.values())