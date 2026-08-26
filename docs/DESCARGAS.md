# Descargas para usuarios

Usa GitHub Releases como pagina publica de descargas:

```text
https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/latest
```

## Windows

Archivo recomendado para usuarios:

- `INSTALAR-TLAMATINI-WINDOWS.cmd`

El usuario sólo descarga este archivo y hace doble clic. El asistente obtiene
automáticamente las partes de la release, puede continuar una descarga
interrumpida, las verifica y abre el instalador final.

Archivos de soporte técnico:

- fragmentos `tlamatini-*-windows-installer.chunk-*-of-*`

No son la descarga principal: el usuario normal no debe bajarlos manualmente.

## Linux

Instalacion recomendada para usuarios de Ubuntu, Debian, Linux Mint y derivados:

El paquete Linux Full incluye el runtime de IA local y Gemma 3 dentro del instalador.

Un solo comando descarga las partes publicadas, verifica el paquete y lo instala:

```bash
curl -fsSL https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/latest/download/INSTALAR-TLAMATINI.sh | bash
```

Archivo alternativo:

- `TLAMATINI-full-linux-x86_64.tar.gz`

Ese paquete es para distribuciones que no usan `.deb` o para soporte tecnico.

## Verificacion

Publica siempre estos archivos junto a los instaladores:

- `SHA256SUMS-linux.txt`
- `SHA256SUMS-windows.txt`
- `release_metadata-linux.json`
- `release_metadata-windows.json`

No subas instaladores grandes con `git add`. Los instaladores van como archivos de GitHub Release, no dentro del historial del repositorio.
