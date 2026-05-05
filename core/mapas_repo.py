from typing import Dict, List, Optional

from core.mapas_offline import get_offline_maps_service


def listar_mapas() -> List[Dict]:
    return get_offline_maps_service().list_installed_maps()


def obtener_mapa(mapa_id: str) -> Optional[Dict]:
    for mapa in listar_mapas():
        if mapa.get("id") == mapa_id:
            return mapa
    return None


def obtener_mapa_activo() -> Optional[Dict]:
    return get_offline_maps_service().get_active_map()


def registrar_mapa_tiles(
    nombre: str,
    ruta_tiles: str,
    descripcion: str = "",
    lat_centro: float = 19.4326,
    lon_centro: float = -99.1332,
    zoom_inicial: Optional[int] = None,
) -> Dict:
    default_zoom = zoom_inicial if zoom_inicial is not None else 2
    return get_offline_maps_service().import_xyz_folder(
        folder_path=ruta_tiles,
        name=nombre,
        description=descripcion,
        center_lat=lat_centro,
        center_lon=lon_centro,
        default_zoom=default_zoom,
    )


def seleccionar_mapa_activo(mapa_id: str) -> bool:
    return get_offline_maps_service().set_active_map(mapa_id)


def eliminar_mapa(mapa_id: str) -> bool:
    return get_offline_maps_service().delete_map(mapa_id)
