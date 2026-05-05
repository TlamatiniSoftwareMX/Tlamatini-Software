# TLAMATINI GitHub Releases

Este proyecto genera paquetes Full por plataforma con GitHub Actions usando runners nativos:

- Linux: `ubuntu-latest`
- Windows: `windows-latest`
- macOS: `macos-latest`

No se cross-compila. Cada sistema genera su propio ejecutable, runtime local y paquete descargable.

## Requisitos

1. Subir este proyecto a un repositorio de GitHub.
2. Verificar que GitHub Actions esté habilitado.
3. El workflow descarga Gemma desde `TLAMATINI_GEMMA3_URL`, definido en `.github/workflows/build-full.yml`.

El modelo Full pesa varios GB. El workflow puede tardar bastante y consumir almacenamiento de artefactos.

## Generar paquetes manualmente

1. En GitHub abre `Actions`.
2. Selecciona `Build Full`.
3. Pulsa `Run workflow`.
4. Espera a que terminen los jobs de Linux, Windows y macOS.
5. Descarga los artefactos:
   - `TLAMATINI-full-linux`
   - `TLAMATINI-full-windows`
   - `TLAMATINI-full-macos`

## Generar paquetes para un release

Desde tu máquina local:

```bash
git tag v5.2.2
git push origin v5.2.2
```

El workflow `Build Full` se ejecuta por el tag `v*` y sube los paquetes al release del tag.

## Artefactos esperados

Linux:

- `TLAMATINI-full-linux-x86_64.tar.gz`
- `tlamatini-5.2.2-amd64.deb`

Windows:

- `TLAMATINI-full-windows-x86_64.zip`

macOS:

- `TLAMATINI-full-macos.zip`
- `TLAMATINI-full-macos.dmg`, si `hdiutil` logra generarlo en el runner.

Todos los paquetes incluyen:

- ejecutable de TLAMATINI,
- runtime local de `llama.cpp` para la plataforma,
- Gemma 3 GGUF,
- catálogos offline por defecto,
- logo/iconos de TLAMATINI.

No deben incluir datos locales de usuario, licencias, perfiles, logs ni carpetas `TLAMATINI_DATA`.

## Verificación

Cada job ejecuta:

```bash
scripts/verify_release_bundle.py
scripts/local_ai_tool.py doctor_full_release
```

La verificación operativa completa de IA queda omitida por defecto con:

```text
TLAMATINI_SKIP_RUNTIME_VERIFY=1
```

Esto evita que el runner cargue el modelo durante minutos y abra puertos locales en CI. Antes de publicar masivamente, descarga cada paquete en una máquina real de su plataforma y realiza una prueba manual de arranque con IA.
