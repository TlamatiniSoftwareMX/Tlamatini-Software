import math
import tkinter as tk
from pathlib import Path
from typing import Callable, Dict, Optional

from core.capas_tacticas import cargar_capas_mapa


TILE_SIZE = 256


class OfflineMapCanvas(tk.Frame):
    def __init__(self, master=None, on_feature_selected: Optional[Callable[[str], None]] = None):
        super().__init__(master, bg="#0b1220")
        self.on_feature_selected = on_feature_selected
        self.canvas = tk.Canvas(self, bg="#0b1220", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.status = tk.Label(self, text="Sin mapa activo", anchor="w", bg="#0b1220", fg="#cbd5e1", font=("Arial", 10))
        self.status.pack(fill="x")

        self.map_data: Optional[Dict] = None
        self.zoom = 0
        self.center_lat = 0.0
        self.center_lon = 0.0
        self.dragging = False
        self.drag_start = (0, 0)
        self.drag_center_world = (0.0, 0.0)
        self.image_refs = []
        self.tile_cache: Dict[str, tk.PhotoImage] = {}
        self.overlay_data = {}
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel)
        self.canvas.bind("<Button-5>", self._on_wheel)
        self.canvas.bind("<Configure>", lambda _e: self.render())

    def load_map(self, map_data: Optional[Dict]) -> None:
        self.map_data = map_data
        self.image_refs = []
        self.tile_cache = {}
        if not map_data:
            self.overlay_data = {}
            self.render()
            return
        self.zoom = int(map_data.get("default_zoom", map_data.get("min_zoom", 0)))
        self.center_lat = float(map_data.get("center_lat", 0.0))
        self.center_lon = float(map_data.get("center_lon", 0.0))
        self.overlay_data = cargar_capas_mapa(map_data["id"])
        self.render()

    def refresh_overlays(self) -> None:
        if self.map_data:
            self.overlay_data = cargar_capas_mapa(self.map_data["id"])
            self.render()

    def _on_press(self, event):
        if not self.map_data:
            return
        self.dragging = True
        self.drag_start = (event.x, event.y)
        world = self._lonlat_to_world(self.center_lon, self.center_lat, self.zoom)
        self.drag_center_world = (world[0], world[1])

    def _on_drag(self, event):
        if not self.map_data or not self.dragging:
            return
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        new_world_x = self.drag_center_world[0] - dx
        new_world_y = self.drag_center_world[1] - dy
        self.center_lon, self.center_lat = self._world_to_lonlat(new_world_x, new_world_y, self.zoom)
        self.render()

    def _on_release(self, _event):
        self.dragging = False

    def _on_wheel(self, event):
        if not self.map_data:
            return
        delta = 0
        if getattr(event, "num", None) == 4:
            delta = 1
        elif getattr(event, "num", None) == 5:
            delta = -1
        else:
            delta = 1 if event.delta > 0 else -1
        next_zoom = max(int(self.map_data.get("min_zoom", 0)), min(int(self.map_data.get("max_zoom", 0)), self.zoom + delta))
        if next_zoom == self.zoom:
            return
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        center_world_old = self._lonlat_to_world(self.center_lon, self.center_lat, self.zoom)
        mouse_world_x = center_world_old[0] - width / 2 + event.x
        mouse_world_y = center_world_old[1] - height / 2 + event.y
        mouse_lon, mouse_lat = self._world_to_lonlat(mouse_world_x, mouse_world_y, self.zoom)
        self.zoom = next_zoom
        mouse_world_new = self._lonlat_to_world(mouse_lon, mouse_lat, self.zoom)
        new_center_world_x = mouse_world_new[0] - event.x + width / 2
        new_center_world_y = mouse_world_new[1] - event.y + height / 2
        self.center_lon, self.center_lat = self._world_to_lonlat(new_center_world_x, new_center_world_y, self.zoom)
        self.render()

    def render(self):
        self.canvas.delete("all")
        self.image_refs = []
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        if not self.map_data:
            self.canvas.create_text(width / 2, height / 2, text="No hay mapa activo", fill="#94a3b8", font=("Arial", 18, "bold"))
            self.status.config(text="Sin mapa activo")
            return
        self._render_tiles(width, height)
        self._render_overlays(width, height)
        self.status.config(
            text=f"{self.map_data.get('name', 'Mapa')} | Zoom {self.zoom} | Lat {self.center_lat:.5f} | Lon {self.center_lon:.5f}"
        )

    def _render_tiles(self, width: int, height: int):
        center_world_x, center_world_y = self._lonlat_to_world(self.center_lon, self.center_lat, self.zoom)
        top_left_x = center_world_x - width / 2
        top_left_y = center_world_y - height / 2
        first_tile_x = math.floor(top_left_x / TILE_SIZE)
        first_tile_y = math.floor(top_left_y / TILE_SIZE)
        last_tile_x = math.floor((top_left_x + width) / TILE_SIZE)
        last_tile_y = math.floor((top_left_y + height) / TILE_SIZE)
        tiles_per_axis = 2 ** self.zoom

        for x in range(first_tile_x, last_tile_x + 1):
            for y in range(first_tile_y, last_tile_y + 1):
                if y < 0 or y >= tiles_per_axis:
                    continue
                wrapped_x = ((x % tiles_per_axis) + tiles_per_axis) % tiles_per_axis
                screen_x = x * TILE_SIZE - top_left_x
                screen_y = y * TILE_SIZE - top_left_y
                photo = self._load_tile_image(self.zoom, wrapped_x, y)
                self.canvas.create_image(screen_x, screen_y, image=photo, anchor="nw")
                self.image_refs.append(photo)

    def _tile_path(self, z: int, x: int, y: int) -> Optional[Path]:
        if not self.map_data:
            return None
        tile_format = str(self.map_data.get("tile_format", "png")).strip(".")
        return Path(self.map_data["tiles_path"]) / str(z) / str(x) / f"{y}.{tile_format}"

    def _load_tile_image(self, z: int, x: int, y: int) -> tk.PhotoImage:
        key = f"{z}/{x}/{y}"
        cached = self.tile_cache.get(key)
        if cached:
            return cached
        tile_path = self._tile_path(z, x, y)
        if tile_path and tile_path.exists():
            try:
                photo = tk.PhotoImage(file=str(tile_path))
            except Exception:
                photo = self._placeholder_tile(z, x, y)
        else:
            photo = self._placeholder_tile(z, x, y)
        if len(self.tile_cache) > 180:
            self.tile_cache.pop(next(iter(self.tile_cache)))
        self.tile_cache[key] = photo
        return photo

    def _placeholder_tile(self, z: int, x: int, y: int) -> tk.PhotoImage:
        image = tk.PhotoImage(width=TILE_SIZE, height=TILE_SIZE)
        image.put("#111827", to=(0, 0, TILE_SIZE, TILE_SIZE))
        border = "#1f2937"
        for i in range(TILE_SIZE):
            image.put(border, (i, 0))
            image.put(border, (i, TILE_SIZE - 1))
            image.put(border, (0, i))
            image.put(border, (TILE_SIZE - 1, i))
        cross = "#1e293b"
        for i in range(TILE_SIZE):
            image.put(cross, (i, i))
            image.put(cross, (i, TILE_SIZE - i - 1))
        return image

    def _render_overlays(self, width: int, height: int):
        for group_name in ("poligonos", "imported"):
            for feature in self.overlay_data.get(group_name, {}).get("features", []):
                geom = feature.get("geometry", {})
                geom_type = geom.get("type")
                if geom_type not in {"Polygon", "MultiPolygon"}:
                    continue
                polygons = geom.get("coordinates", [])
                if geom_type == "Polygon":
                    polygons = [geom.get("coordinates", [])]
                for polygon in polygons:
                    if not polygon:
                        continue
                    pts = []
                    for lon, lat in polygon[0]:
                        sx, sy = self._screen_from_lonlat(lon, lat, width, height)
                        pts.extend([sx, sy])
                    item = self.canvas.create_polygon(
                        pts,
                        fill=feature.get("properties", {}).get("color", "#f97316"),
                        outline=feature.get("properties", {}).get("color", "#f97316"),
                        width=2,
                        stipple="gray25",
                    )
                    self.canvas.tag_bind(item, "<Button-1>", lambda _e, f=feature: self._feature_clicked(f))

        for group_name in ("rutas", "imported"):
            for feature in self.overlay_data.get(group_name, {}).get("features", []):
                geom = feature.get("geometry", {})
                geom_type = geom.get("type")
                line_sets = []
                if geom_type == "LineString":
                    line_sets = [geom.get("coordinates", [])]
                elif geom_type == "MultiLineString":
                    line_sets = geom.get("coordinates", [])
                else:
                    continue
                for line in line_sets:
                    pts = []
                    for lon, lat in line:
                        sx, sy = self._screen_from_lonlat(lon, lat, width, height)
                        pts.extend([sx, sy])
                    item = self.canvas.create_line(
                        pts,
                        fill=feature.get("properties", {}).get("color", "#22c55e"),
                        width=3,
                        smooth=True,
                    )
                    self.canvas.tag_bind(item, "<Button-1>", lambda _e, f=feature: self._feature_clicked(f))

        for group_name in ("puntos", "nodos", "refugios", "recursos", "sensores", "imported"):
            radius = 6 if group_name == "puntos" else 7
            for feature in self.overlay_data.get(group_name, {}).get("features", []):
                geom = feature.get("geometry", {})
                if geom.get("type") != "Point":
                    continue
                lon, lat = geom.get("coordinates", [0, 0])
                sx, sy = self._screen_from_lonlat(lon, lat, width, height)
                color = feature.get("properties", {}).get("color", "#ef4444")
                item = self.canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius, fill=color, outline="#ffffff", width=1)
                label = feature.get("properties", {}).get("nombre", "Punto")
                self.canvas.create_text(sx + 12, sy - 10, text=label, fill="#ffffff", anchor="w", font=("Arial", 9, "bold"))
                self.canvas.tag_bind(item, "<Button-1>", lambda _e, f=feature: self._feature_clicked(f))

    def _feature_clicked(self, feature: Dict) -> None:
        props = feature.get("properties", {})
        coords = (feature.get("geometry") or {}).get("coordinates", [])
        text = (
            f"{props.get('nombre', 'Elemento')}\n"
            f"Tipo: {props.get('tipo', 'n/d')}\n"
            f"Categoria: {props.get('categoria', props.get('riesgo', 'n/d'))}\n"
            f"Estado: {props.get('estado', 'n/d')}\n"
            f"Fuente: {props.get('fuente_datos', 'local')}\n"
            f"Coordenadas: {coords}\n"
            f"Descripcion: {props.get('descripcion', '')}"
        )
        if self.on_feature_selected:
            self.on_feature_selected(text)

    def _screen_from_lonlat(self, lon: float, lat: float, width: int, height: int):
        center_world_x, center_world_y = self._lonlat_to_world(self.center_lon, self.center_lat, self.zoom)
        point_world_x, point_world_y = self._lonlat_to_world(lon, lat, self.zoom)
        return point_world_x - center_world_x + width / 2, point_world_y - center_world_y + height / 2

    def _lonlat_to_world(self, lon: float, lat: float, zoom: int):
        scale = TILE_SIZE * (2 ** zoom)
        x = (lon + 180.0) / 360.0 * scale
        siny = math.sin(math.radians(max(min(lat, 85.0511), -85.0511)))
        y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * scale
        return x, y

    def _world_to_lonlat(self, x: float, y: float, zoom: int):
        scale = TILE_SIZE * (2 ** zoom)
        lon = (x / scale) * 360.0 - 180.0
        n = math.pi - 2.0 * math.pi * y / scale
        lat = math.degrees(math.atan(math.sinh(n)))
        return lon, lat
