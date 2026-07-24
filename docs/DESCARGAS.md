# Descargas para usuarios

Usa GitHub Releases como pagina publica de descargas:

```text
https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/latest
```

## Windows

Archivo recomendado para usuarios:

- `TLAMATINI-Windows-Instalador-Full.exe`

El usuario solo debe descargar ese archivo, abrirlo y seguir el instalador.

Archivo alternativo:

- `TLAMATINI-full-windows-x86_64.zip`

Ese zip es para soporte tecnico o instalaciones portables. No es la descarga principal para usuarios normales.

## Linux

Archivo recomendado para usuarios de Ubuntu, Debian, Linux Mint y derivados:

- `tlamatini-5.2.4-amd64.deb`

El paquete Linux Full incluye el runtime de IA local y Gemma 3 dentro del instalador.

Instalacion:

```bash
sudo apt install ./tlamatini-5.2.4-amd64.deb
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
