# Mapas Offline en TLAMATINI

## Qué quedó operativo

TLAMATINI conserva el gestor de mapas dentro de la ventana `Mapa`:

- catálogo
- descarga
- progreso
- instalación
- activación
- eliminación
- persistencia

Ahora el formato principal objetivo es `PMTiles`, con visor local estilo NOMAD servido por TLAMATINI con:

- `MapLibre GL JS`
- `pmtiles.js`
- servidor HTTP local del proyecto
- estilos intercambiables `standard`, `dark`, `tactical`
- glyphs locales para etiquetas básicas
- capas tácticas GeoJSON locales

Los mapas `xyz_zip` siguen soportados solo como compatibilidad legacy.

## Estructura local

Los mapas y artefactos offline se almacenan en:

- `TLAMATINI_DATA/local_maps/installed/`
- `TLAMATINI_DATA/local_maps/packages/`
- `TLAMATINI_DATA/local_maps/temp/`
- `TLAMATINI_DATA/local_maps/catalog/`
- `TLAMATINI_DATA/local_maps/metadata/`
- `TLAMATINI_DATA/local_maps/styles/`
- `TLAMATINI_DATA/local_maps/pmtiles/`
- `TLAMATINI_DATA/local_maps/overlays/<map_id>/`

El visor web local usa assets en:

- `map_ui/`
- `map_ui/vendor/`
- `map_ui/runtime/`
- `map_ui/fonts/`

Las capas operativas se guardan por mapa en:

- `TLAMATINI_DATA/local_maps/overlays/<map_id>/puntos.geojson`
- `TLAMATINI_DATA/local_maps/overlays/<map_id>/rutas.geojson`
- `TLAMATINI_DATA/local_maps/overlays/<map_id>/poligonos.geojson`
- `TLAMATINI_DATA/local_maps/overlays/<map_id>/refugios.geojson`
- `TLAMATINI_DATA/local_maps/overlays/<map_id>/recursos.geojson`
- `TLAMATINI_DATA/local_maps/overlays/<map_id>/nodos.geojson`
- `TLAMATINI_DATA/local_maps/overlays/<map_id>/sensores.geojson`
- `TLAMATINI_DATA/local_maps/overlays/<map_id>/imported.geojson`

## Catálogo

El catálogo base vive en:

- `assets/offline_maps/catalog.json`

Entradas iniciales PMTiles reales:

- `xalapa-veracruz`
- `veracruz-estado`
- `mexico-completo`
- `mexico-city-shortbread`
- `madrid-shortbread`
- `berlin-shortbread`

Entradas legacy demo:

- `demo-world-grid`
- `demo-night-grid`

Puedes extender el catálogo con:

- `TLAMATINI_DATA/local_maps/catalog/catalog.json`
- `TLAMATINI_MAPS_CATALOG_URL`

Cada entrada soporta:

- `id`
- `name`
- `region`
- `size_bytes`
- `version`
- `url`
- `destination_file`
- `checksum`
- `format`
- `schema`
- `description`
- `center_lat`
- `center_lon`
- `min_zoom`
- `max_zoom`
- `default_zoom`

Formatos actualmente aceptados por el instalador:

- `pmtiles_zip`
- `pmtiles`
- `xyz_zip`

Además, el catálogo puede declarar un `generator` para producir un enlace real antes de descargarlo. Actualmente quedó integrado:

- `generator.kind = "bbbike_extract"`

## Descarga e instalación

Desde la ventana `Mapa`:

1. Selecciona una entrada en `Catálogo disponible`.
2. Pulsa `Descargar mapa`.
3. TLAMATINI descarga a `temp/<map_id>.part`.
4. Si termina correctamente, mueve el archivo a `packages/`.
5. Si el formato es `pmtiles_zip`, extrae el `.pmtiles` al directorio `installed/<map_id>/`.
6. Si el formato es `pmtiles`, copia el archivo al directorio instalado.
7. Lee metadata y cabecera PMTiles para registrar zooms, centro, bounds y tipo de tile.

Para mapas con generador BBBike:

1. TLAMATINI envía la solicitud real del extracto a `https://extract.bbbike.org/`.
2. BBBike responde con la URL final de descarga.
3. TLAMATINI espera hasta que el artefacto remoto exista.
4. En cuanto queda listo, lo descarga con el mismo flujo `.part`, reanudación y movimiento a `packages/`.

## Activación y visualización

1. Selecciona un mapa en `Mapas instalados`.
2. Pulsa `Activar mapa`.
3. Si el mapa es `PMTiles`, TLAMATINI actualiza el runtime del visor y puede abrir automáticamente el visor local tipo NOMAD.
4. El visor se sirve desde `http://127.0.0.1:<puerto>/` y carga el archivo `.pmtiles` local mediante Range Requests.
5. Las capas tácticas y operativas (`puntos`, `rutas`, `poligonos`, `refugios`, `recursos`, `nodos`, `sensores`, `imported`) se superponen desde GeoJSON local del proyecto.

## Estilos y panel de capas

El visor ahora expone:

- selector de estilo `Estándar`
- selector de estilo `Oscuro`
- selector de estilo `Táctico`
- panel de capas base
- panel de capas operativas
- leyenda
- coordenadas de cursor y centro
- medición básica

Capas base controlables:

- suelo / terreno
- agua
- calles y carreteras
- edificios
- parques / vegetación
- límites administrativos
- etiquetas / nombres

Capas operativas controlables:

- puntos guardados
- rutas
- zonas de riesgo
- refugios
- recursos
- nodos
- sensores
- GeoJSON importado

La visibilidad de capas y el estilo activo se persisten en la sección `mapas_viewer` de la memoria local de TLAMATINI.

## Cómo importar GeoJSON

Desde la ventana `Mapa`:

1. Activa un mapa.
2. Pulsa `Importar GeoJSON`.
3. Selecciona el archivo local.
4. Elige la capa destino.
5. El visor recargará los overlays y el panel de capas mostrará el conteo actualizado.

## Cómo agregar nuevas capas u overlays

Opciones actuales:

- `Agregar punto`: permite guardar puntos, refugios, recursos, nodos o sensores.
- `Agregar ruta`: guarda una línea `LineString` local.
- `Agregar zona`: guarda un polígono local.
- `Importar GeoJSON`: fusiona un `FeatureCollection` sobre la capa elegida.

## Eliminar mapa

1. Selecciona el mapa instalado.
2. Pulsa `Eliminar mapa`.
3. TLAMATINI elimina la instalación local y el paquete descargado.

## Cómo agregar nuevos mapas PMTiles al catálogo

Añade una entrada JSON como esta:

```json
{
  "id": "mi-region",
  "name": "Mi Region PMTiles",
  "region": "Pais / Region",
  "size_bytes": 12345678,
  "version": "2026.04",
  "url": "https://servidor/mi-region.pmtiles.zip",
  "destination_file": "mi-region.pmtiles.zip",
  "format": "pmtiles_zip",
  "schema": "shortbread",
  "description": "Mapa regional PMTiles",
  "center_lat": 0.0,
  "center_lon": 0.0,
  "min_zoom": 0,
  "max_zoom": 14,
  "default_zoom": 10
}
```

Para extractos regionales bajo demanda vía BBBike puedes usar:

```json
{
  "id": "mi-region-real",
  "name": "Mi Region Real PMTiles",
  "region": "Pais / Region",
  "size_bytes": 25000000,
  "version": "2026.04.19",
  "destination_file": "mi-region-real.osm.pmtiles-shortbread.zip",
  "format": "pmtiles_zip",
  "schema": "shortbread",
  "description": "Extracto real PMTiles bajo demanda",
  "center_lat": 0.0,
  "center_lon": 0.0,
  "min_zoom": 0,
  "max_zoom": 14,
  "default_zoom": 10,
  "generator": {
    "kind": "bbbike_extract",
    "request_url": "https://extract.bbbike.org/",
    "request_format": "pmtiles-shortbread.zip",
    "city": "mi-region-real",
    "email": "nobody",
    "estimated_size_mb": 25,
    "wait_timeout_seconds": 900,
    "poll_interval_seconds": 10,
    "bbox": {
      "sw_lng": -1.0,
      "sw_lat": -1.0,
      "ne_lng": 1.0,
      "ne_lat": 1.0
    }
  }
}
```

## Offline

Una vez descargado e instalado un mapa:

- el archivo `.pmtiles` queda local
- el visor usa solo el servidor local de TLAMATINI
- ya no necesita internet para navegar el mapa activo

## Limitaciones técnicas actuales

- La gestión sigue dentro de Tk, pero el visor tipo NOMAD corre en un navegador local porque este entorno no trae un `webview` embebible estable para Tk.
- El estilo local ya es operativo y con capas, pero sigue siendo más simple que una cartografía NOMAD completa.
- Las etiquetas básicas funcionan con glyphs locales mínimos; no cubren todavía todos los idiomas o todos los rangos Unicode posibles.
- Los mapas legacy `xyz_zip` siguen visibles en el canvas integrado, pero PMTiles ya es el camino principal.
