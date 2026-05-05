# Biblioteca Offline de TLAMATINI

## Estructura local

Todo queda bajo `TLAMATINI_DATA/local_library/`:

- `catalog/`
  - `resolved_catalog.json`: catálogo resuelto con estados locales.
- `zim/`
  - archivos `.zim` instalados.
- `temp/`
  - descargas temporales `.part`.
- `metadata/`
  - `library_state.json`: instalados, favoritos, último abierto y estado del lector.
- `cache/`
  - reservado para ampliaciones del lector.
- `indexes/`
  - reservado para índices adicionales.
- `favorites/`
  - reservado para ampliaciones.
- `runtime/kiwix/`
  - runtime local de `kiwix-serve` descargado por TLAMATINI cuando hace falta.

## Catálogo inicial

El catálogo base está en `assets/offline_library/catalog.json`.

Cada entrada incluye:

- `id`
- `name`
- `language`
- `category`
- `size_human`
- `size_bytes`
- `description`
- `format`
- `download_url`
- `filename`
- `version`
- `source`
- `source_url`

## Cómo agregar nuevos contenidos

1. Añade una nueva entrada en `assets/offline_library/catalog.json`.
2. Usa una `download_url` real de Kiwix u otra fuente ZIM compatible.
3. Define `filename` con el nombre final del archivo `.zim`.
4. Reinicia la ventana `Biblioteca` o pulsa `Recargar`.

## Cómo funciona la descarga

- TLAMATINI descarga a `local_library/temp/<archivo>.part`.
- Si el servidor soporta `Range`, reanuda desde el punto anterior.
- Al terminar mueve el archivo a `local_library/zim/`.
- El estado queda persistido en `metadata/library_state.json`.

## Cómo se abre el contenido

- `Iniciar lector` prepara `kiwix-serve` y levanta un servidor local.
- `Abrir lectura` hace lo mismo y además abre el contenido en el navegador local.
- El usuario no tiene que ejecutar `kiwix-serve` manualmente.

## Runtime Kiwix

El backend intenta resolver `kiwix-serve` en este orden:

1. variable de entorno `TLAMATINI_KIWIX_SERVE`
2. runtime ya descargado en `local_library/runtime/kiwix/bin/kiwix-serve`
3. `kiwix-serve` disponible en `PATH`
4. descarga automática del paquete oficial GNU/Linux amd64 de Kiwix Tools

## Eliminación

- `Eliminar` borra el `.zim` instalado.
- También limpia el registro de instalado en `library_state.json`.

## Funcionamiento offline

Después de descargar:

- el archivo `.zim` queda local
- TLAMATINI puede volver a abrirlo sin red
- si el runtime Kiwix ya fue descargado o existe en el sistema, la lectura funciona offline

## Integración

- Acceso desde el dashboard actual mediante `Biblioteca`
- UI principal en `interfaz/ventana_biblioteca.py`
- backend en `core/biblioteca_offline.py`
