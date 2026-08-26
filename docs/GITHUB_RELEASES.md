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
5. Descarga los artefactos separados por sistema:
   - `TLAMATINI-Linux`
   - `TLAMATINI-Windows`
   - `TLAMATINI-macOS`

## Generar paquetes para un release

Desde tu máquina local:

```bash
git tag v5.2.6
git push origin v5.2.6
```

El workflow `Build Full` se ejecuta por el tag `v*` y sube los paquetes al release del tag.

## Artefactos esperados

Linux:

- `TLAMATINI-full-linux-x86_64.tar.gz`
- `tlamatini-5.2.6-amd64.deb`
- `SHA256SUMS-linux.txt`
- `release_metadata-linux.json`

Windows:

- `INSTALAR-TLAMATINI-WINDOWS.cmd` (único archivo para usuarios)
- `INSTALAR-TLAMATINI-WINDOWS.ps1` (descargado automáticamente por el CMD)
- fragmentos `tlamatini-*-windows-installer.chunk-*-of-*`
- `SHA256-WINDOWS-INSTALADOR.txt`
- `SHA256-WINDOWS-PARTES.txt`

macOS:

- `TLAMATINI-full-macos.zip`
- `TLAMATINI-full-macos.dmg`, si `hdiutil` logra generarlo en el runner.
- `SHA256SUMS-macos.txt`
- `release_metadata-macos.json`

Descargas recomendadas para usuarios:

- Windows: `INSTALAR-TLAMATINI-WINDOWS.cmd`. El usuario descarga sólo este
  archivo; el proceso automático obtiene y verifica las partes publicadas.
- Linux Debian/Ubuntu/Mint: un comando con `INSTALAR-TLAMATINI.sh`, que descarga
  y verifica automáticamente las partes publicadas.

Los `.zip` y `.tar.gz` quedan como alternativas tecnicas/portables. Todos los paquetes incluyen:

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
