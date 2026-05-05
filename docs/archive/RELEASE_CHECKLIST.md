# Release Checklist

## Cliente desktop

- Build Linux Full terminado.
- Build Windows Full terminado en Windows.
- Build macOS Full terminado en macOS.
- Smoke test de bundle Full aprobado.
- Doctor Full aprobado.
- Checksums de artefactos generados.
- Metadata de release generada.
- Firma de release generada.
- Verificación de firma aprobada.
- Diagnóstico de release generado.
- Instalador Windows generado.
- DMG macOS generado.
- AppImage y/o DEB Linux generado.
- Prueba de instalación limpia en Linux.
- Prueba de instalación limpia en Windows.
- Prueba de instalación limpia en macOS.
- Login validado.
- Licencia online validada.
- Licencia offline validada.
- Updates verificados.
- Arranque de Gemma validado.

## Backend SaaS

- Backend desplegado con HTTPS.
- Docker Compose producción validado o equivalente en proveedor real.
- `ADMIN_API_KEY` real configurada.
- Paddle sandbox validado.
- Paddle producción validado.
- Claves RS256 definitivas cargadas.
- `AUTO_CREATE_TABLES=false` en producción.
- `ALLOWED_HOSTS` y `CORS_ALLOW_ORIGINS` configurados.
- Backups y monitoreo activos.
- Smoke Docker Compose aprobado.

## Comercial

- Precio y plan final definidos.
- Textos de onboarding listos.
- Términos de licencia listos.
- Política de soporte definida.
