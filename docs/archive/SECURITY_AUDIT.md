# TLAMATINI Security Audit

Fecha de revisión: 2026-04-30

## Riesgos corregidos

- Se corrigió el instalador Linux para que use el binario incluido en el mismo bundle y no una ruta inválida del proyecto.
- Se añadió `.gitignore` para evitar que se compartan por accidente `backend/.env`, builds, bases de datos locales y cachés.
- Se endureció la validación de backend SaaS en el cliente:
  - backends remotos solo por `https://`
  - rechazo de URLs con rutas, querys o fragmentos
  - `http://` solo permitido para `localhost/127.0.0.1/::1`
- Se endureció la validación de releases de updates en el backend:
  - `download_url` debe usar HTTPS
  - `sha256` debe ser hex válido de 64 caracteres
- Se endureció el webhook de Paddle:
  - tolerancia de timestamp configurable
  - rechazo de firmas expiradas
  - límite de tamaño del payload
  - rechazo explícito de JSON inválido
- Se limitaron detalles devueltos por errores hacia Paddle para evitar exponer respuestas completas en errores 502.
- Se protegió el almacenamiento local sensible con permisos restrictivos cuando el sistema operativo lo permite:
  - memoria
  - licencia local
  - identidad de instalación
  - logs y directorios de estado
- Se rotaron los secretos débiles de `backend/.env` por valores locales fuertes y se dejó `backend/.env.example` sin secretos reutilizables.

## Validaciones ejecutadas

- `python3 -m unittest tests.test_backend_hybrid tests.test_security_hardening`
- `PYTHONPATH=backend ./backend/.venv/bin/python -m pytest -q backend/tests/test_auth_installations.py`
- `python3 scripts/doctor_tlamatini.py`
- `python3 scripts/verify_release_bundle.py dist/tlamatini_full`
- `PYTHONPATH=backend ./backend/.venv/bin/python backend/scripts/validate_production_env.py`

## Riesgos aún pendientes

- El backend SaaS real no está desplegado ni validado con secretos/productos reales.
- La firma del release sigue dependiendo de `TLAMATINI_RELEASE_SIGNING_KEY`; no se pudo refirmar aquí porque no se proporcionó la clave.
- No se pudo reconstruir el bundle Full Linux endurecido porque ya no está disponible el archivo fuente `local_ai/models/gemma3/model.gguf` en el workspace actual, y este entorno no tiene acceso de red para recuperarlo.
- La prueba piloto en otra computadora sigue pendiente en máquina limpia para:
  - login
  - licencia online
  - licencia offline
  - updates
  - arranque real de Gemma

## Recomendación para piloto

- Usar el bundle Linux ya generado solo como prueba funcional preliminar.
- No tratar ese binario actual como release final endurecido hasta reconstruirlo con el código actualizado y volver a generar checksums y firma.
