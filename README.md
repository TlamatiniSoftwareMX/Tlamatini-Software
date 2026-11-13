# TLAMATINI — descarga e instalación

TLAMATINI es una aplicación de escritorio con herramientas de consulta, organización, mapas y cámara. Puedes elegir una edición con inteligencia artificial local o una edición sin IA.

## Elige tu edición

| Sistema de 64 bits | Versión de TLAMATINI | Inteligencia artificial incluida | RAM objetivo (no certificada) |
| --- | --- | --- | --- |
| Windows | 5.2.6 | Gemma 3 4B | 8 GB |
| Windows | 5.2.6 | Gemma 3 1B | 4 GB |
| Windows | 5.2.6 sin IA | — | — |
| Linux | 5.2.6 | Gemma 3 4B | 8 GB |
| Linux | 5.2.6 | Gemma 3 1B | 4 GB |
| Linux | 5.2.6 sin IA | — | — |

La RAM es la memoria total de tu computadora. Gemma 3 1B es el modelo pequeño para la edición destinada a 4 GB; Gemma 3 4B es el modelo de la edición para la que se recomiendan 8 GB. Los nombres 1B y 4B identifican el tamaño del modelo, no los GB de RAM.

Elige **una edición por computadora**. Las variantes instalan la misma aplicación. El modelo de IA viene incluido y funciona localmente después de la instalación. Para descargar e instalar necesitas conexión a Internet.

La auditoría confirmó los seis comandos de descarga e instalación, pero encontró funciones PDF/OCR pendientes en Linux, un motor OCR externo pendiente en Windows y motores de IA duplicados que pueden permanecer en memoria. Las cifras de RAM son objetivos sin certificar. Consulta el [informe de auditoría](https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/blob/main/docs/AUDITORIA_EDICIONES_2026-11-13.md). Las ediciones sin IA no descargan ni inician modelos.

## Windows: cómo abrir PowerShell

1. Abre **Inicio** y escribe **Windows PowerShell**.
2. Abre **Windows PowerShell**.
3. Elige uno de los tres bloques siguientes, copia **todo el bloque**, pégalo en PowerShell y presiona **Enter**.
4. Espera a que termine la descarga. Cuando Windows solicite permiso, acepta para abrir el asistente y sigue sus pasos.

El comando descarga todo, verifica los archivos y abre el instalador. Al terminar queda **un archivo EXE completo** en `%USERPROFILE%\Downloads\TLAMATINI\`, dentro de la carpeta de la edición elegida. Las partes temporales se unen y eliminan automáticamente; no tienes que descargarlas una por una.

### Windows 5.2.6 — Gemma 3 4B — RAM objetivo: 8 GB

```powershell
$ErrorActionPreference = 'Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$archivo = Join-Path $env:TEMP 'TLAMATINI-instalar.ps1'
Invoke-WebRequest -UseBasicParsing 'https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALAR-TLAMATINI-EDICIONES.ps1' -OutFile $archivo
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $archivo -Edicion ia-8gb
```

### Windows 5.2.6 — Gemma 3 1B — RAM objetivo: 4 GB

```powershell
$ErrorActionPreference = 'Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$archivo = Join-Path $env:TEMP 'TLAMATINI-instalar.ps1'
Invoke-WebRequest -UseBasicParsing 'https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALAR-TLAMATINI-EDICIONES.ps1' -OutFile $archivo
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $archivo -Edicion ia-4gb
```

### Windows 5.2.6 sin IA

```powershell
$ErrorActionPreference = 'Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$archivo = Join-Path $env:TEMP 'TLAMATINI-instalar.ps1'
Invoke-WebRequest -UseBasicParsing 'https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALAR-TLAMATINI-EDICIONES.ps1' -OutFile $archivo
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $archivo -Edicion sin-ia
```

## Linux: cómo abrir la terminal

Estas ediciones usan paquetes **DEB para Linux amd64/x86_64 de 64 bits**, en sistemas con `apt` y **glibc 2.38 o superior**. El descargador comprueba ese requisito antes de instalar.

1. Abre **Terminal** desde el menú de aplicaciones; en Ubuntu y Linux Mint también puedes usar **Ctrl + Alt + T**.
2. Elige **un solo comando** de los tres siguientes, pégalo y presiona **Enter**.
3. Si solicita tu contraseña, escríbela y presiona **Enter**. Es normal que no se muestren caracteres mientras la escribes.

El comando descarga y verifica el instalador completo e inicia su instalación con `apt`. Si necesita partes, las obtiene y une automáticamente. El archivo DEB completo queda en `~/Downloads/TLAMATINI/`, dentro de la carpeta de la edición elegida.

### Linux 5.2.6 — Gemma 3 4B — RAM objetivo: 8 GB

```bash
curl -fsSL https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALAR-TLAMATINI-EDICIONES.sh | bash -s -- ia-8gb
```

### Linux 5.2.6 — Gemma 3 1B — RAM objetivo: 4 GB

```bash
curl -fsSL https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALAR-TLAMATINI-EDICIONES.sh | bash -s -- ia-4gb
```

### Linux 5.2.6 sin IA

```bash
curl -fsSL https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/download/ediciones-2026-11-13/INSTALAR-TLAMATINI-EDICIONES.sh | bash -s -- sin-ia
```

## Después de instalar

- **Windows:** abre **Inicio**, busca **TLAMATINI** y ábrelo.
- **Linux:** busca **TLAMATINI** en el menú de aplicaciones o escribe `tlamatini` en la terminal.

## Si la descarga se interrumpe

Vuelve a ejecutar el mismo bloque o comando. El descargador reutiliza los archivos completos cuya verificación sea correcta. El instalador solo se abre después de verificar el archivo final.

Si Linux muestra `curl: command not found`, instala curl y vuelve a ejecutar el comando de tu edición:

```bash
sudo apt update && sudo apt install -y curl
```

Si falta Python 3, el descargador Linux lo prepara automáticamente. Si indica que una verificación SHA-256 falló, no se instala ese archivo: vuelve a ejecutar el mismo comando.

Conviene disponer de 12 GB libres durante la instalación con Gemma 3 4B, 4 GB con Gemma 3 1B o 1 GB sin IA, para la descarga, los temporales y la aplicación.

## Archivos y verificación

Las seis opciones y estas mismas instrucciones también están en [GitHub Releases](https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/latest). Los fragmentos visibles en Assets son archivos que el descargador administra automáticamente.

Los paquetes Linux con Gemma 3 1B y sin IA llevan la revisión `5.2.6-6`; la versión de la aplicación es `5.2.6` en las seis opciones. Las cuatro ediciones publicadas el 13 de noviembre se compilaron de forma nativa y sus SHA-256 están verificados. La auditoría posterior verificó el arranque normal de las seis ediciones y respuestas breves de los cuatro modelos. Siguen pendientes las reparaciones de PDF/OCR, el ciclo de vida de los motores y la certificación de RAM; el detalle y las pruebas están en el informe de auditoría.
