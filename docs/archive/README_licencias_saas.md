# TLAMATINI SaaS Cliente

Esta integración conecta el cliente de TLAMATINI con el backend SaaS para:

- configurar backend
- registrar/login
- registrar instalación local
- iniciar trial
- abrir Paddle Checkout
- sincronizar licencia pagada
- guardar `signed_payload` local
- validar licencia offline
- revisar actualizaciones
- leer changelog
- descargar paquetes con verificación `sha256`

## Variables de entorno

- `TLAMATINI_BACKEND_URL`
- `TLAMATINI_LICENSE_FILE`
- `TLAMATINI_INSTALLATION_ID_FILE`
- `TLAMATINI_LICENSE_PUBLIC_KEY`
- `TLAMATINI_APP_VERSION` opcional

## Persistencia local

- `TLAMATINI_INSTALLATION_ID_FILE` guarda un `installation_id` fijo por instalación.
- `TLAMATINI_LICENSE_FILE` guarda la licencia local firmada y metadatos de sincronización.
- La sesión del usuario y configuración SaaS se guardan en `memoria.json`, dentro de `configuracion.licenciamiento`.
- El estado de updates también se guarda en `memoria.json`, dentro de `configuracion.licenciamiento.updates`.
- Las descargas verificadas se guardan en la carpeta multiplataforma de updates de TLAMATINI:
  - Linux: `~/.tlamatini/updates/`
  - Windows: `%APPDATA%/TLAMATINI/updates/`
  - macOS: `~/Library/Application Support/TLAMATINI/updates/`

## Flujo recomendado

1. Abrir TLAMATINI.
2. Desde la barra inferior abrir `Licencia`.
3. Configurar `URL backend`.
4. Pegar la clave pública o ruta PEM local si se usa firma `RS256`.
5. Registrar usuario o iniciar sesión.
6. Pulsar `Iniciar prueba de 7 días` o `Activar suscripción`.
7. Si se abre Paddle Checkout, completar el pago en navegador.
8. Volver a TLAMATINI y pulsar `Sincronizar licencia`.

## Validación offline

TLAMATINI valida `signed_payload` local sin depender del backend:

- `HS256`: valida con HMAC-SHA256 si la clave local corresponde al secreto compartido
- `RS256`: valida con `openssl` usando la clave pública local

Estados offline:

- `valid`
- `grace`
- `expired`
- `invalid`
- `missing`

Reglas:

- si `now <= expires_at`: válida
- si `expires_at < now <= grace_until`: gracia
- si `now > grace_until`: expirada
- si la firma falla: inválida
- si no hay licencia local: missing

## Cómo probar trial

1. Configura `TLAMATINI_BACKEND_URL` o guárdalo desde la ventana.
2. Inicia sesión.
3. Pulsa `Iniciar prueba de 7 días`.
4. Verifica que el estado cambie a válido y que se cree el archivo de licencia local.

## Cómo probar Paddle sandbox

1. Configura el backend con Paddle sandbox operativo.
2. Inicia sesión en TLAMATINI.
3. Pulsa `Activar suscripción`.
4. Completa el checkout sandbox.
5. Vuelve a TLAMATINI.
6. Pulsa `Sincronizar licencia`.
7. Verifica que el plan cambie a `monthly`.

## Qué hacer sin internet

- TLAMATINI no debe fallar si el backend no está disponible.
- La ventana de licencia seguirá mostrando el estado local.
- Si existe `signed_payload` válido, TLAMATINI puede seguir operando con licencia offline.

## Actualizaciones

### Cómo configurar backend local

1. Abre TLAMATINI.
2. Desde la barra inferior abre `Actualizaciones`.
3. Guarda la misma `URL backend` usada para licencias.
4. Revisa `Versión actual`, `Plataforma` y `Canal`.

### Cómo probar update check local

1. Publica una release en el backend con `POST /updates/releases`.
2. En TLAMATINI abre `Actualizaciones`.
3. Pulsa `Buscar actualizaciones`.
4. Verifica:
   - `Nueva versión disponible`
   - `Notas de versión`
   - si es `opcional` u `obligatoria`

### Cómo probar descarga segura

1. Asegúrate de que la release tenga `download_url` y `sha256`.
2. Pulsa `Descargar actualización`.
3. TLAMATINI descarga el archivo sin ejecutarlo.
4. Calcula `sha256`.
5. Si coincide, guarda el paquete en la carpeta multiplataforma `updates/` de TLAMATINI.
6. Si no coincide, rechaza la descarga.

### Cómo se usará después con instaladores reales

- Este bloque no reemplaza binarios ni lanza instaladores.
- La metadata ya separa `linux`, `windows` y `macos`.
- `signature` queda preparada para firma criptográfica más fuerte de paquetes.
- El siguiente endurecimiento natural es: firma de artefactos, instaladores reales y flujo controlado de aplicación del update.
