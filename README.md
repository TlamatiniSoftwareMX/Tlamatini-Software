# TLAMATINI 5.2.5

TLAMATINI es una aplicación de escritorio con herramientas de consulta,
organización, mapas, cámara e inteligencia artificial local integrada.

## Descargar

Abre la sección [Releases](https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/latest)
y elige las instrucciones de tu sistema.

## Windows

Descarga en una misma carpeta:

- Los 42 archivos llamados
  `tlamatini-5.2.5-windows-installer.chunk-001-of-042` hasta
  `tlamatini-5.2.5-windows-installer.chunk-042-of-042`.
- `INSTALAR-TLAMATINI-WINDOWS.cmd`.
- `INSTALAR-TLAMATINI-WINDOWS.ps1`.
- `SHA256-WINDOWS-INSTALADOR.txt`.

Haz doble clic en `INSTALAR-TLAMATINI-WINDOWS.cmd`. El asistente comprobará
el instalador y abrirá la instalación de TLAMATINI.

## Linux

Descarga en una misma carpeta:

- Los 44 archivos llamados
  `tlamatini-5.2.5-linux-amd64.chunk-001-of-044` hasta
  `tlamatini-5.2.5-linux-amd64.chunk-044-of-044`.
- `INSTALAR-TLAMATINI.sh`.

### Instalar en Linux

TLAMATINI es compatible con Debian, Ubuntu y Linux Mint de 64 bits. Se
recomiendan al menos 8 GB de memoria RAM y aproximadamente 5 GB de espacio
libre durante la instalación.

Abre una terminal en la carpeta donde guardaste los archivos y ejecuta:

```bash
bash INSTALAR-TLAMATINI.sh
```

El instalador unirá y verificará automáticamente las 44 partes. Después
solicitará tu contraseña de administrador e instalará TLAMATINI junto con sus
dependencias.

## Abrir TLAMATINI

Busca **TLAMATINI** en el menú de aplicaciones. También puedes abrirlo desde
una terminal con:

```bash
tlamatini
```

La primera carga de la inteligencia artificial puede tardar más que las
siguientes porque el modelo local se inicia por primera vez.

## Solución de problemas

- Si falta una parte, confirma que los 44 fragmentos estén en la misma carpeta.
- Si falla la verificación, vuelve a descargar el fragmento indicado.
- Si la cámara no abre, comprueba que esté conectada y que otra aplicación no
  la esté utilizando.
- Conserva los fragmentos hasta que la instalación termine correctamente.
