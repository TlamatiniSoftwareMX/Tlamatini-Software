# Aprendizaje Offline en TLAMATINI

## Estructura local

El módulo guarda todo bajo `TLAMATINI_DATA/local_learning/`:

- `catalog/`: caché del catálogo resuelto.
- `courses/`: cursos instalados.
- `temp/`: descargas parciales `.part`.
- `metadata/`: estado general del módulo.
- `progress/`: reservado para ampliaciones futuras.
- `cache/`: caché auxiliar.
- `favorites/`: reservado para ampliaciones futuras.

Cada curso instalado queda como:

- `courses/<course_id>/course.json`
- `courses/<course_id>/lessons/<lesson_id>.json`

## Formato actual

El motor usa `mediawiki_course`:

- el catálogo define módulos y lecciones
- cada lección apunta a una URL real de Wikipedia u otro MediaWiki compatible
- TLAMATINI descarga la lección, extrae contenido y lo guarda localmente como JSON

## Alcance real del extractor

El extractor actual está fortalecido para páginas `MediaWiki`:

- elimina ruido común de referencias y bloques no didácticos
- convierte la lección a texto legible offline
- tolera variaciones razonables en la estructura del HTML servido por la API

No es un importador universal de cualquier sitio educativo. Si se agrega contenido fuera de MediaWiki, hay que implementar un extractor específico para esa fuente.

## Cómo agregar nuevos cursos

Edita `assets/offline_learning/catalog.json` y añade una entrada con:

- `id`
- `name`
- `language`
- `category`
- `level`
- `size_human`
- `description`
- `format`
- `download_url`
- `source`
- `source_url`
- `version`
- `content_type`
- `tags`
- `modules`

Cada `module` necesita:

- `id`
- `title`
- `lessons`

Cada `lesson` necesita:

- `id`
- `title`
- `source_type`: actualmente `mediawiki`
- `source_url`

## Descarga

La descarga:

1. crea `temp/<course_id>.part/`
2. descarga lecciones una por una
3. guarda cada lección como JSON local
4. crea `course.json`
5. mueve la carpeta temporal a `courses/<course_id>/`
6. verifica que el curso final tenga manifiesto y todas sus lecciones

Si se interrumpe, TLAMATINI puede reanudar tomando las lecciones ya guardadas en `.part`.

## Eliminación

Eliminar desde la UI borra:

- carpeta del curso instalado
- progreso asociado
- favorito asociado
- estado de descarga parcial si existe

## Apertura y estudio

Abrir un curso carga su `course.json`, muestra módulos y lecciones y abre la lección en la misma ventana de Aprendizaje.

## Progreso

Se guarda en `metadata/learning_state.json`:

- cursos instalados
- favoritos
- último curso abierto
- última lección abierta
- lecciones completadas por curso
- porcentaje de progreso

## Offline

Una vez descargado el curso, las lecciones se leen desde `local_learning/courses/` sin depender de Internet.
