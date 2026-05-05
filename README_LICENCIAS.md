# TLAMATINI Licencias

## Usuario final

1. Abre TLAMATINI.
2. Copia la solicitud de licencia.
3. Envíala después del pago.
4. Recibe un código.
5. Pégalo en `Activar licencia`.
6. TLAMATINI queda activado offline.

La solicitud copiada incluye:

- email
- `installation_id`
- sistema operativo
- versión de TLAMATINI
- estado actual
- plan solicitado

## Administrador

Herramientas privadas:

- `tools_private/generar_claves_tlamatini.py`
- `tools_private/license_generator_core.py`
- `tools_private/generar_codigo_licencia_tlamatini.py`
- `tools_private/generador_licencias_gui.py`
- `tools_private/abrir_generador_licencias.sh`

Flujo:

1. Pegar la solicitud del usuario.
2. Confirmar email e `installation_id`.
3. Elegir plan y duración.
4. Generar licencia.
5. Copiar el código y enviarlo al usuario.

## Seguridad

- No distribuir `tools_private/`.
- No distribuir `private_license_key.pem`.
- Sí distribuir `public_license_key.pem`.
