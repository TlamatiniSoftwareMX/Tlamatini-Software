# Consulta IA Local y Búsqueda Documental

## Resumen

El módulo existente `consulta` ahora trabaja en tres modos:

1. Pregunta nueva sin pedir fuentes:
   - responde con `[Respuesta rápida de IA local]`
2. Seguimiento como `más info`, `profundiza`, `dame citas`:
   - usa el contexto previo de la sesión
   - cambia a respuesta documental o híbrida según el caso
3. Solicitud documental desde la primera pregunta:
   - entra directo a `[Respuesta ampliada basada en documentos]`

## Archivos principales

- `core/local_llm.py`
- `core/intencion_consulta.py`
- `core/tema_consulta.py`
- `core/documentos_tematicos.py`
- `core/consulta.py`
- `core/consulta_avanzada.py`
- `interfaz/ventana_consulta.py`

## Backend local activo

Arquitectura activa:

- `llama-server` como runtime local
- archivos `GGUF` bajo `local_ai/models/.../model.gguf`

Modelo principal esperado:

- `local_ai/models/gemma3/model.gguf`

## Variables de entorno

- `TLAMATINI_LOCAL_LLM_MODEL`
- `TLAMATINI_LOCAL_LLM_TEMPERATURE`
- `TLAMATINI_LOCAL_LLM_TOP_P`
- `TLAMATINI_LOCAL_LLM_MAX_TOKENS`
- `TLAMATINI_LOCAL_LLM_TIMEOUT`
- `TLAMATINI_LOCAL_LLM_CONTEXT`

Valores por defecto actuales:

- `TLAMATINI_LOCAL_LLM_MODEL=gemma3:4b`
- `TLAMATINI_LOCAL_LLM_TEMPERATURE=0.3`
- `TLAMATINI_LOCAL_LLM_TOP_P=0.9`
- `TLAMATINI_LOCAL_LLM_MAX_TOKENS=220`
- `TLAMATINI_LOCAL_LLM_TIMEOUT=90`
- `TLAMATINI_LOCAL_LLM_CONTEXT=4096`

## Cómo configurar el modelo local activo

Ejemplo:

```bash
export TLAMATINI_LOCAL_LLM_MODEL=gemma3:4b
```

O volver al modelo por defecto:

```bash
export TLAMATINI_LOCAL_LLM_MODEL=llama3:latest
```

Nota:

- TLAMATINI no consume modelos instalados solo en Ollama.
- Para usar Gemma en esta arquitectura necesitas un archivo GGUF en `local_ai/models/gemma3/model.gguf`.

## Cómo cargar bibliotecas temáticas

La ingestión documental reutiliza:

- extracción PDF/texto en `core/extractor_documental.py`
- OCR local con `pytesseract`
- registro de libros en `core/biblioteca.py`
- índice local FTS5 en `core/indice_consulta.py`

Mapeo actual de bibliotecas:

- `biblioteca_medica`
- `biblioteca_filosofia`
- `biblioteca_derecho`
- `biblioteca_historia`
- `biblioteca_psicologia`
- `biblioteca_literatura`
- `biblioteca_ingenieria`
- `biblioteca_general`

La carga temática puede hacerse con `DocumentIngestionService` de `core/documentos_tematicos.py`.

Ejemplo:

```python
from core.documentos_tematicos import DocumentIngestionService

servicio = DocumentIngestionService()
resultado = servicio.ingest_document(
    ruta_archivo="libros/mi_libro.pdf",
    biblioteca="biblioteca_medica",
    subdominio="general",
)
print(resultado)
```

## Cómo probar el flujo completo

### 1. Respuesta local inicial

```python
from core.consulta import responder_consulta_inteligente
print(responder_consulta_inteligente("¿Qué es la diabetes?", session_id="demo-1"))
```

### 2. Seguimiento con contexto

```python
from core.consulta import responder_consulta_inteligente

sid = "demo-2"
print(responder_consulta_inteligente("¿Qué es el nihilismo?", session_id=sid))
print(responder_consulta_inteligente("más info", session_id=sid))
```

### 3. Solicitud documental directa

```python
from core.consulta import responder_consulta_inteligente
print(responder_consulta_inteligente("Dame citas sobre hipertensión según los libros", session_id="demo-3"))
```

### 4. Prueba de búsqueda

Desde la ventana `Consulta`, usar el botón `Probar búsqueda`.

También en código:

```python
from core.consulta_avanzada import probar_busqueda_consulta
print(probar_busqueda_consulta("¿Qué es la diabetes?"))
```

## Casos validados

- pregunta general -> respuesta local
- pregunta médica -> respuesta local y tema `medicina`
- pregunta médica + `más info` -> flujo documental en `biblioteca_medica`
- pregunta filosófica + `profundiza` -> flujo documental en `biblioteca_filosofia`
- `Dame citas sobre hipertensión según los libros` -> documental directo
- `más info` sin contexto -> mensaje controlado
- backend local no disponible -> error manejado
- biblioteca temática vacía -> respuesta controlada

## Estado actual del entorno

Durante la validación final, `biblioteca` estaba vacía.

Eso significa:

- el enrutamiento temático funciona
- la respuesta documental funciona
- pero algunas respuestas documentales terminan en mensaje de falta de evidencia hasta que se carguen libros en las bibliotecas temáticas

## Nota operativa

El índice `consulta.db` puede contener fragmentos previos aunque la sección `biblioteca` esté vacía. Conviene mantener sincronizados:

- registros de `biblioteca`
- caché documental
- índice FTS5
