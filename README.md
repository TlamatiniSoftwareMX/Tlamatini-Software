# TLAMATINI 5.2.6

TLAMATINI es una aplicación de escritorio con herramientas de consulta,
organización, mapas, cámara e inteligencia artificial local integrada.

## Descargar

Abre la sección [Releases](https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/latest)
y elige las instrucciones de tu sistema.

## Windows

Descarga en una misma carpeta:

- Los 42 archivos llamados
  `tlamatini-5.2.6-windows-installer.chunk-001-of-042` hasta
  `tlamatini-5.2.6-windows-installer.chunk-042-of-042`.
- `INSTALAR-TLAMATINI-WINDOWS.cmd`.
- `INSTALAR-TLAMATINI-WINDOWS.ps1`.
- `SHA256-WINDOWS-INSTALADOR.txt`.

Haz doble clic en `INSTALAR-TLAMATINI-WINDOWS.cmd`. El asistente comprobará
el instalador y abrirá la instalación de TLAMATINI.

## Linux

### Instalar en Linux

TLAMATINI es compatible con Debian, Ubuntu y Linux Mint de 64 bits. Se
recomiendan al menos 8 GB de memoria RAM y aproximadamente 5 GB de espacio
libre durante la instalación.

Abre una terminal y ejecuta este único comando:

```bash
curl -fsSL https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/releases/latest/download/INSTALAR-TLAMATINI.sh | bash
```

El instalador descargará, unirá y verificará automáticamente las 44 partes.
Después solicitará tu contraseña de administrador e instalará TLAMATINI junto
con sus dependencias.

## Abrir TLAMATINI

Busca **TLAMATINI** en el menú de aplicaciones. También puedes abrirlo desde
una terminal con:

```bash
tlamatini
```

La primera carga de la inteligencia artificial puede tardar más que las
siguientes porque el modelo local se inicia por primera vez.

## Solución de problemas

- Si se interrumpe la descarga, ejecuta nuevamente el mismo comando.
- Si falla la verificación, vuelve a ejecutar el comando para descargar copias nuevas.
- Si la cámara no abre, comprueba que esté conectada y que otra aplicación no
  la esté utilizando.
- Los archivos temporales se eliminan automáticamente al terminar.
