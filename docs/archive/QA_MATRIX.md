# QA Matrix

## Linux

- Instalar desde `dist/TLAMATINI-full-linux-x86_64.tar.gz`
- Confirmar ejecución de `install.sh`
- Abrir TLAMATINI
- Validar login
- Validar licencia online
- Desconectar internet
- Validar licencia offline
- Ejecutar una consulta con Gemma
- Reabrir la app
- Confirmar que no descarga nada adicional

## Windows

- Build nativo en Windows
- Instalar con `install.ps1` o instalador Inno Setup
- Confirmar acceso directo
- Validar login
- Validar licencia online y offline
- Ejecutar una consulta con Gemma
- Reiniciar Windows y volver a abrir TLAMATINI

## macOS

- Build nativo en macOS
- Instalar `TLAMATINI.app` o `.dmg`
- Confirmar copia a `/Applications`
- Validar login
- Validar licencia online y offline
- Ejecutar una consulta con Gemma
- Reabrir la app tras reinicio

## Backend SaaS

- `doctor_backend.py` OK
- `validate_production_env.py` OK
- `docker compose config` OK
- `/health` responde
- `/version` responde
- Paddle sandbox funcional
- Webhook firmado funcional
- Activación de licencia funcional

## Release

- `doctor_tlamatini.py` OK
- `verify_release_bundle.py` OK
- `verify_release_signature.py` OK
- `SHA256SUMS.txt` y `SHA256SUMS.sig.json` presentes
- `release_metadata.json` presente
