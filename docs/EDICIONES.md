# Cuatro ediciones de TLAMATINI

| Plataforma | Edición | IA incluida |
| --- | --- | --- |
| Windows x64 | no-ai | Ninguna; arranque, descarga y proveedor desactivados |
| Windows x64 | ai-4gb | Gemma 3 1B Q4_K_M, contexto 1024, CPU con dos hilos |
| Linux amd64 | no-ai | Ninguna; arranque, descarga y proveedor desactivados |
| Linux amd64 | ai-4gb | Gemma 3 1B Q4_K_M, contexto 1024, CPU con dos hilos |

El destino de las ediciones ai-4gb es una computadora con 4 GB de RAM total.
Esto requiere una prueba operativa de consumo y arranque; no equivale al número
de parámetros del modelo. El modelo anterior Gemma 3 4B queda fuera de estas
cuatro ediciones. No confundir sus instaladores anteriores con ai-4gb.

El ejecutable lleva una marca de edición embebida; la edición sin IA no
se convierte en una edición con IA por detectar una instalación de Ollama.
Las ediciones de 4 GB desactivan Mistral, limitan los lotes y detienen los
procesos de IA que iniciaron al cerrar la aplicación.

## Construcción secuencial

Se usa Python 3.12 y las dependencias habituales de escritorio del proyecto.
No ejecutar dos compilaciones locales a la vez. En Linux, el script limita
el espacio de direcciones de cada proceso de compilación a 1.5 GiB y fija
las bibliotecas numéricas a un hilo. No se carga el modelo al construir.

```sh
.venv/bin/python scripts/build_edition.py no-ai
TLAMATINI_EDITION=no-ai TLAMATINI_BUNDLE_DIR=dist/no-ai TLAMATINI_PACKAGE_VERSION=5.2.6-6 sh scripts/package_linux_deb.sh
```

Después, para la otra edición:

```sh
.venv/bin/python scripts/build_edition.py ai-4gb --model /ruta/gemma-3-1b-it-Q4_K_M.gguf
TLAMATINI_EDITION=ai-4gb TLAMATINI_BUNDLE_DIR=dist/ai-4gb TLAMATINI_PACKAGE_VERSION=5.2.6-6 sh scripts/package_linux_deb.sh
```

El modelo debe coincidir en tamaño y SHA-256 con el archivo publicado por
[ggml-org](https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF).
El script verifica ambos antes de copiarlo al instalador. No reutiliza el
modelo de 4B ni la configuración rápida de diez hilos.

Windows se compila en Windows. El workflow `Build Windows editions sequentially`
produce primero no-ai y después ai-4gb, con `max-parallel: 1`. Los instaladores
se conservan como artefactos del workflow; no se publican en Releases.
