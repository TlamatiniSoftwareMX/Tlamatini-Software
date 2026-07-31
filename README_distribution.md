# TLAMATINI Distribution

Guía base para generar builds instalables de TLAMATINI con PyInstaller, manteniendo:

- UI de escritorio
- licencias SaaS y validación offline
- updates
- biblioteca offline
- IA local Full incluida
- rutas multiplataforma con `path_manager`

## Requisitos

- Python 3.11 o 3.12
- entorno virtual con dependencias del cliente
- `pyinstaller`
- Windows: NSIS o Inno Setup si luego quieres instalador `.exe`
- Linux: `appimagetool` y opcional `dpkg-deb`
- macOS: `create-dmg` o `hdiutil` para `.dmg`

Importante:

- Linux se construye en Linux.
- Windows se construye en Windows.
- macOS se construye en macOS.

El repositorio ya trae el pipeline por plataforma, pero PyInstaller no debe tratarse aquí como un sistema de cross-compilación confiable para TLAMATINI Full.

Instalación mínima para empaquetar:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pyinstaller pillow requests pmtiles tkinterdnd2 opencv-contrib-python
```

En Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install pyinstaller pillow requests pmtiles tkinterdnd2 opencv-contrib-python
```

## Estructura que entra al bundle

El build incluye:

- `main.py`
- `core/`
- `interfaz/`
- `sistema/`
- `assets/`
- `map_ui/`
- `local_ai/config/` si existe
- `local_ai/runtime/` si existe
- `local_ai/models/` si existe

Para la edición Full, los modelos también se empaquetan dentro del bundle si están presentes al compilar.

## Edición Full con IA

TLAMATINI puede distribuirse como una sola edición Full donde el usuario:

1. descarga un solo instalador o bundle,
2. concede permisos del sistema,
3. instala todo,
4. inicia sesión,
5. usa la app sin descargar IA aparte.

### Requisitos previos para generar la edición Full

- `local_ai/runtime/bin/llama-server` o `llama-server.exe`
- `local_ai/models/gemma3/model.gguf`

Además, el build Full genera automáticamente:

- `local_ai/config/models.json`
- `local_ai/config/runtime.json`

### Comandos de build Full

```bash
sh scripts/build_full_release_linux.sh
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_full_release_windows.ps1
```

macOS:

```bash
sh scripts/build_full_release_macos.sh
```

Ese flujo:

- valida que Gemma 3 exista,
- valida el runtime local,
- genera configuración Full por defecto,
- ejecuta PyInstaller,
- deja el bundle final en `dist/tlamatini_full/`
- genera un paquete distribuible por plataforma en `dist/`

## Automatización CI

Existe un workflow base en:

- [.github/workflows/build-full.yml](/home/iralki-ignatieff/1%20Escritorio/TLAMATINI/.github/workflows/build-full.yml:1)

Guía de uso:

- [docs/GITHUB_RELEASES.md](/home/iralki-ignatieff/Nueva%20carpeta/1%20Escritorio/TLAMATINI/docs/GITHUB_RELEASES.md:1)

Ese pipeline:

- prepara `venv`
- descarga runtime local y Gemma
- ejecuta el build Full en Linux, Windows y macOS
- sube artefactos por plataforma

Para releases reales, conviene activarlo por `tag` y revisar consumo de almacenamiento porque el bundle Full pesa varios GB.

### Comportamiento esperado al arrancar

Si TLAMATINI detecta runtime + Gemma local empaquetados, usa backend `local` automáticamente en lugar de depender de Ollama.

## Archivo de PyInstaller

Usa:

- [pyinstaller.spec](/home/iralki-ignatieff/Escritorio/TLAMATINI/pyinstaller.spec)

Características del spec:

- modo ventana, sin consola
- inclusión de `assets/` y `map_ui/`
- soporte para `tkinterdnd2`
- soporte opcional para icono por plataforma
- bundle `.app` en macOS

Iconos opcionales esperados:

- `assets/app_icon.ico`
- `assets/app_icon.icns`
- `assets/app_icon.png`

Si no existen, el build sigue sin icono personalizado.

## Comandos exactos

### Build base con PyInstaller

Linux/macOS:

```bash
source .venv/bin/activate
pyinstaller --clean --noconfirm pyinstaller.spec
```

Windows:

```powershell
.venv\Scripts\activate
pyinstaller --clean --noconfirm pyinstaller.spec
```

Salida esperada:

- `dist/TLAMATINI/` en Windows y Linux
- `dist/TLAMATINI.app` en macOS

## Windows

### Ejecutable standalone

Comando:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_full_release_windows.ps1
```

Resultado:

- `dist\tlamatini_full\TLAMATINI.exe` o `dist\tlamatini_full\TLAMATINI`
- `dist\TLAMATINI-full-windows-x86_64.zip`

### Instalador de usuario

El bundle incluye:

- `install.ps1`
- `install.cmd`

Para un instalador profesional firmado todavía conviene empaquetar con NSIS o Inno Setup sobre ese bundle.

Plantilla Inno Setup incluida:

- [installer/windows/TLAMATINI_full.iss](/home/iralki-ignatieff/1%20Escritorio/TLAMATINI/installer/windows/TLAMATINI_full.iss:1)

Contenido mínimo a distribuir:

- `dist\TLAMATINI\TLAMATINI.exe`
- DLLs generadas por PyInstaller
- recursos empaquetados en el mismo directorio

## Linux

### Paquete 5.2.6

Para distribuir el modo de uso libre, usar el paquete:

- `dist/tlamatini-5.2.6-amd64.deb`

Ese paquete no requiere prueba, suscripción ni código de activación para entrar.
Incluye el ejecutable, el runtime local y Gemma 3; no requiere descargar la IA después de instalarlo.

Instalación limpia sobre una versión anterior:

```bash
sudo apt remove -y tlamatini
sudo apt install ./dist/tlamatini-5.2.6-amd64.deb
dpkg -l | grep -i tlamatini
```

La verificación debe mostrar `5.2.6`.

### Build Full

```bash
sh scripts/build_full_release_linux.sh
```

Resultado:

- `dist/tlamatini_full/TLAMATINI`
- `dist/tlamatini_full/install.sh`
- `dist/TLAMATINI-full-linux-x86_64.tar.gz`

### AppImage opcional

1. Genera el build Full.
2. Crea `AppDir/` copiando `dist/tlamatini_full/`.
3. Añade `AppRun` y `.desktop`.
4. Ejecuta `appimagetool`.

Ejemplo base:

```bash
mkdir -p AppDir/usr/bin
cp -r dist/tlamatini_full/* AppDir/usr/bin/
appimagetool AppDir TLAMATINI-x86_64.AppImage
```

Wrapper incluido:

```bash
sh scripts/package_linux_appimage.sh
```

### `.deb` opcional

1. Genera el build Full.
2. Crea estructura:

```text
pkg/
  DEBIAN/control
  opt/tlamatini/
  usr/share/applications/
```

3. Copia `dist/tlamatini_full/` a `/opt/tlamatini/`
4. Empaqueta:

```bash
dpkg-deb --build pkg tlamatini-amd64.deb
```

Wrapper incluido:

```bash
sh scripts/package_linux_deb.sh
```

## macOS

### `.app`

```bash
sh scripts/build_full_release_macos.sh
```

Resultado:

- `dist/tlamatini_full/TLAMATINI.app`
- `dist/tlamatini_full/install.command`
- `dist/TLAMATINI-full-macos.zip`

### `.dmg` opcional

Si `hdiutil` está disponible, el pipeline intentará generar también:

- `dist/TLAMATINI-full-macos.dmg`

Manual:

```bash
hdiutil create -volname TLAMATINI -srcfolder dist/TLAMATINI.app -ov -format UDZO TLAMATINI.dmg
```

Wrapper incluido:

```bash
sh scripts/package_macos_dmg.sh
```

## Post-instalación

Al primer arranque TLAMATINI debe crear automáticamente:

- Linux: `~/.tlamatini/`
- Windows: `%APPDATA%/TLAMATINI/`
- macOS: `~/Library/Application Support/TLAMATINI/`

Subcarpetas:

- `data/`
- `license/`
- `updates/`
- `models/`
- `library/`
- `config/`

El binario distribuido no debe depender del repo original.

## Backend en producción

Variables útiles:

- `TLAMATINI_BACKEND_URL`
- `TLAMATINI_LICENSE_PUBLIC_KEY`
- `TLAMATINI_AI_BACKEND`
- `TLAMATINI_HOME`

Puedes preconfigurar `TLAMATINI_BACKEND_URL` en el instalador o dejar que el usuario lo configure desde UI.

## Cómo probar distribución

Smoke test incluido:

```bash
sh scripts/smoke_release.sh
```

o directamente:

```bash
python3 scripts/verify_release_bundle.py dist/tlamatini_full
```

Eso valida:

- presencia de `release_manifest.json`
- ejecutable o bundle esperado por plataforma
- instalador correspondiente
- tamaño mínimo razonable para edición Full con IA embebida

Doctor de release:

```bash
python3 scripts/local_ai_tool.py doctor_full_release
```

Doctor general del proyecto:

```bash
python3 scripts/doctor_tlamatini.py
```

Diagnóstico de release:

```bash
python3 scripts/collect_release_diagnostics.py
```

Archivo generado:

- `release_diagnostics.json`

Checksums generados al empaquetar:

- `dist/SHA256SUMS.txt`
- `dist/SHA256SUMS.json`
- `dist/release_metadata.json`

Firma de release:

```bash
export TLAMATINI_RELEASE_SIGNING_KEY="tu-clave-secreta-de-release"
python3 scripts/sign_release_artifacts.py
python3 scripts/verify_release_signature.py
```

Archivo generado:

- `dist/SHA256SUMS.sig.json`

Workflow de publicación:

- [.github/workflows/release-publish.yml](/home/iralki-ignatieff/1%20Escritorio/TLAMATINI/.github/workflows/release-publish.yml:1)

Matriz de aceptación archivada:

- [docs/archive/QA_MATRIX.md](/home/iralki-ignatieff/Nueva%20carpeta/1%20Escritorio/TLAMATINI/docs/archive/QA_MATRIX.md:1)

### Validaciones mínimas

1. Abrir la app empaquetada sin ejecutar desde el repo.
2. Confirmar que crea su estructura persistente.
3. Hacer login.
4. Sincronizar licencia.
5. Descargar metadata de updates.
6. Abrir biblioteca offline.
7. Validar IA local según backend configurado.

### Windows

1. Ejecuta `TLAMATINI.exe` en una máquina sin Python global.
2. Verifica que no abra consola.
3. Revisa `%APPDATA%/TLAMATINI/`.

### Linux

1. Ejecuta binario o AppImage.
2. Revisa `~/.tlamatini/`.
3. Confirma permisos de escritura en `updates/`, `license/`, `config/`.

### macOS

1. Abre `TLAMATINI.app`.
2. Revisa `~/Library/Application Support/TLAMATINI/`.
3. Verifica login, licencia y updates.

## Limitaciones actuales

- No genera instaladores finales por sí solo; PyInstaller deja el bundle base.
- Los iconos son opcionales; hay que añadir `assets/app_icon.*` para branding real.
- El peso del bundle Full crecerá varios GB al incluir Gemma.
- Kiwix runtime sigue siendo opcional y dependiente de la plataforma.
- No se implementa firma/codesign/notarización en este bloque.
- Auto-update todavía no reemplaza binarios; solo deja la base para reemplazo manual o siguiente bloque.
