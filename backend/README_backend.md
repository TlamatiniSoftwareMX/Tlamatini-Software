# TLAMATINI Backend

Backend preparado para el flujo SaaS de TLAMATINI: usuarios, login seguro, instalaciones, licencias, updates y cobros con Paddle.

## Stack

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL

## Estructura

```text
backend/
  app/
    main.py
    config.py
    database.py
    models/
    routes/
    schemas/
    services/
    utils/
  requirements.txt
  .env.example
  .env.production.example
  README_backend.md
```

## Variables de entorno

Copia:

- `.env.example` para desarrollo local
- `.env.production.example` para despliegue SaaS

Variables importantes:

- `DATABASE_URL`
- `APP_ENV`
- `APP_VERSION`
- `API_BASE_URL`
- `FORCE_HTTPS`
- `ALLOWED_HOSTS`
- `CORS_ALLOW_ORIGINS`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `LICENSE_PRIVATE_KEY`
- `LICENSE_PUBLIC_KEY`
- `LICENSE_SIGNING_ALGORITHM`
- `LICENSE_SIGNING_SECRET`
- `PADDLE_API_KEY`
- `PADDLE_WEBHOOK_SECRET`
- `PADDLE_ENVIRONMENT`
- `PADDLE_PRODUCT_ID`
- `PADDLE_PRICE_ID`
- `ADMIN_API_KEY`
- `TRIAL_DAYS`
- `OFFLINE_GRACE_DAYS`
- `AUTO_CREATE_TABLES`

## Producción SaaS

Mínimos obligatorios:

- `APP_ENV=production`
- `API_BASE_URL=https://...`
- `AUTO_CREATE_TABLES=false`
- `FORCE_HTTPS=true`
- `ALLOWED_HOSTS` con el dominio público real del backend
- `CORS_ALLOW_ORIGINS` solo con frontends permitidos
- `DATABASE_URL` en PostgreSQL
- `ADMIN_API_KEY` fuerte
- `JWT_SECRET` fuerte
- Paddle configurado con credenciales reales
- Firma de licencias preferentemente con `RS256`

No uses en producción:

- `http://127.0.0.1:8000`
- SQLite
- placeholders
- `CORS_ALLOW_ORIGINS=*`
- `AUTO_CREATE_TABLES=true`

## Instalación local

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Ejecutar localmente

```bash
cd backend
uvicorn app.main:app --reload
```

Endpoints base:

- `GET /`
- `GET /health`
- `GET /version`
- `GET /auth/status`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /installations/register`
- `GET /installations`
- `POST /billing/create-checkout`
- `POST /billing/webhook`
- `GET /billing/webhook-events`
- `POST /licenses/trial`
- `GET /licenses/status`
- `POST /licenses/verify`
- `POST /licenses/revoke`
- `GET /updates/check`
- `POST /updates/releases`

## PostgreSQL

Usa una URL estándar en `DATABASE_URL`, por ejemplo:

```text
postgresql+psycopg://usuario:password@localhost:5432/tlamatini_backend
```

Por defecto el backend crea tablas al iniciar si `AUTO_CREATE_TABLES=true`.

## Railway

1. Sube el proyecto con la carpeta `backend/`.
2. Crea un servicio en Railway apuntando a `backend/`.
3. Configura variables de entorno desde Railway.
4. Añade una base PostgreSQL en Railway.
5. Asigna `DATABASE_URL` con la cadena entregada por Railway.
6. Configura además:

- `APP_ENV=production`
- `API_BASE_URL=https://<tu-backend>.up.railway.app` o dominio propio
- `FORCE_HTTPS=true`
- `ALLOWED_HOSTS=<tu-backend>.up.railway.app`
- `CORS_ALLOW_ORIGINS=https://<tu-app-o-dominio>`
- `AUTO_CREATE_TABLES=false`

7. Usa como comando de arranque:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Docker Compose producción

Archivos incluidos:

- [Dockerfile](/home/iralki-ignatieff/1%20Escritorio/TLAMATINI/backend/Dockerfile:1)
- [docker-compose.production.yml](/home/iralki-ignatieff/1%20Escritorio/TLAMATINI/backend/docker-compose.production.yml:1)
- [deploy/Caddyfile](/home/iralki-ignatieff/1%20Escritorio/TLAMATINI/backend/deploy/Caddyfile:1)

Flujo base:

```bash
cd backend
cp .env.production.example .env.production
docker compose -f docker-compose.production.yml up -d --build
```

Variables adicionales esperadas para esa plantilla:

- `POSTGRES_PASSWORD`
- `TLAMATINI_DOMAIN`
- `ACME_EMAIL`

Validación de entorno:

```bash
cd backend
cp .env.production.example .env.production
python scripts/validate_production_env.py
```

Smoke test HTTP:

```bash
sh scripts/smoke_backend.sh https://tu-dominio-backend
```

Doctor backend:

```bash
cd backend
python scripts/doctor_backend.py
```

Smoke de Docker Compose:

```bash
cd backend
sh scripts/smoke_compose_production.sh
```

Si quieres levantar el stack en smoke:

```bash
cd backend
TLAMATINI_SMOKE_UP=1 sh scripts/smoke_compose_production.sh
```

## Checklist antes de cobrar

- Registro y login OK
- Registro de instalación OK
- Trial OK
- Checkout Paddle sandbox OK
- Webhook Paddle firmado OK
- Activación de licencia pagada OK
- Reinicio de la app con licencia local válida OK
- Operación offline OK
- Re-sincronización al volver internet OK

Consulta también: `backend/README_production_hardening.md`

## Flujo de autenticación

### 1. Registrar usuario

`POST /auth/register`

Body JSON:

```json
{
  "email": "persona@example.com",
  "password": "ClaveSegura123",
  "preferred_language": "es"
}
```

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "persona@example.com",
    "password": "ClaveSegura123",
    "preferred_language": "es"
  }'
```

Respuesta:

- valida email
- evita duplicados
- hashea la contraseña con bcrypt vía `passlib`
- nunca devuelve `password_hash`

### 2. Iniciar sesión

`POST /auth/login`

Body JSON:

```json
{
  "email": "persona@example.com",
  "password": "ClaveSegura123"
}
```

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "persona@example.com",
    "password": "ClaveSegura123"
  }'
```

Respuesta:

```json
{
  "access_token": "jwt-aqui",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "persona@example.com",
    "preferred_language": "es",
    "is_active": true
  }
}
```

### 3. Usar token

Todos los endpoints autenticados esperan:

```text
Authorization: Bearer <access_token>
```

Ejemplo para perfil:

```bash
curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

`GET /auth/me` devuelve:

- `id`
- `email`
- `preferred_language`
- `is_active`

## Flujo de instalaciones

### Registrar instalación o dispositivo

`POST /installations/register`

Requiere token.

Body JSON:

```json
{
  "installation_id": "inst-local-001",
  "device_name": "Laptop Operativa",
  "os_name": "Linux",
  "app_version": "0.1.0"
}
```

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/installations/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "installation_id": "inst-local-001",
    "device_name": "Laptop Operativa",
    "os_name": "Linux",
    "app_version": "0.1.0"
  }'
```

Comportamiento:

- asocia la instalación al usuario autenticado
- si ya existe para ese usuario, actualiza `device_name`, `os_name`, `app_version`, `last_seen_at`
- si la misma `installation_id` ya pertenece a otro usuario, responde `409`
- devuelve la instalación registrada

### Listar instalaciones del usuario

`GET /installations`

Ejemplo:

```bash
curl http://127.0.0.1:8000/installations \
  -H "Authorization: Bearer $TOKEN"
```

## Variables nuevas

- `JWT_SECRET`: secreto obligatorio para firmar y verificar JWT
- `JWT_ALGORITHM`: algoritmo del token, por defecto `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES`: duración del access token en minutos
- `LICENSE_SIGNING_ALGORITHM`: algoritmo de firma de licencias, recomendado `RS256`
- `LICENSE_SIGNING_SECRET`: secreto alterno para desarrollo si decides usar `HS256`
- `ADMIN_API_KEY`: clave interna para publicar releases manualmente

## Licencias firmadas

### Configuración de claves

Producción recomendada:

- usa `LICENSE_SIGNING_ALGORITHM=RS256`
- firma con `LICENSE_PRIVATE_KEY`
- verifica con `LICENSE_PUBLIC_KEY`
- esta firma es independiente de `JWT_SECRET`

Ejemplo de generación local de claves RSA:

```bash
openssl genrsa -out license_private.pem 2048
openssl rsa -in license_private.pem -pubout -out license_public.pem
```

Luego copia el contenido PEM a `.env`. Si tu plataforma no maneja saltos de línea reales, puedes guardarlos escapados con `\n`.

Desarrollo simple:

- usa `LICENSE_SIGNING_ALGORITHM=HS256`
- define `LICENSE_SIGNING_SECRET`
- esto sirve para pruebas locales, pero la validación offline final debe migrar o mantenerse con un esquema claro de firma separado del auth JWT

### Payload firmado

El `signed_payload` es un token firmado que contiene al menos:

```json
{
  "license_id": "lic_...",
  "user_id": 1,
  "installation_id": "inst-local-001",
  "plan": "trial",
  "status": "trial",
  "issued_at": "2026-04-24T12:00:00+00:00",
  "expires_at": "2026-05-01T12:00:00+00:00",
  "grace_until": "2026-05-31T12:00:00+00:00",
  "features": ["core_access", "offline_validation_ready"]
}
```

TLAMATINI podrá guardar ese `signed_payload` localmente y validarlo offline más adelante con la clave pública.

### Emitir trial de 7 días

`POST /licenses/trial`

Requiere token y una instalación ya registrada para el usuario.

```bash
curl -X POST http://127.0.0.1:8000/licenses/trial \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"installation_id":"inst-local-001"}'
```

Comportamiento:

- valida que la instalación pertenezca al usuario autenticado
- si ya existe licencia para esa instalación, devuelve la misma
- si no existe, crea una licencia `trial` por `TRIAL_DAYS`
- genera `grace_until` con `OFFLINE_GRACE_DAYS` para el siguiente bloque
- firma el payload y guarda `signed_payload` en base de datos

### Consultar estado de licencia

`GET /licenses/status?installation_id=inst-local-001`

```bash
curl "http://127.0.0.1:8000/licenses/status?installation_id=inst-local-001" \
  -H "Authorization: Bearer $TOKEN"
```

Devuelve:

- `status`
- `plan`
- `license_id`
- `expires_at`
- `grace_until`
- `signed_payload`
- `days_remaining`
- `is_valid`

### Verificar firma

`POST /licenses/verify`

```bash
curl -X POST http://127.0.0.1:8000/licenses/verify \
  -H "Content-Type: application/json" \
  -d '{"signed_payload":"<payload-firmado>"}'
```

Devuelve si la firma es válida y, si lo es, el payload decodificado.

### Revocar licencia

`POST /licenses/revoke`

```bash
curl -X POST http://127.0.0.1:8000/licenses/revoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"installation_id":"inst-local-001"}'
```

Por ahora queda protegido por autenticación y limitado al dueño de la instalación. En el siguiente bloque puede endurecerse con rol admin o flujo interno.

### Integración offline futura

La app TLAMATINI podrá:

1. pedir trial una sola vez por instalación
2. guardar `signed_payload` localmente
3. validar la firma offline con `LICENSE_PUBLIC_KEY`
4. usar `expires_at` y `grace_until` para decidir acceso local en el cliente

## Paddle

### Variables necesarias

- `PADDLE_API_KEY`
- `PADDLE_WEBHOOK_SECRET`
- `PADDLE_ENVIRONMENT`
- `PADDLE_PRODUCT_ID`
- `PADDLE_PRICE_ID`

`PADDLE_ENVIRONMENT=sandbox` usa `https://sandbox-api.paddle.com`.  
`PADDLE_ENVIRONMENT=live` usa `https://api.paddle.com`.

### Cómo funciona la conexión con Paddle

1. TLAMATINI autentica al usuario.
2. TLAMATINI registra la instalación.
3. TLAMATINI llama `POST /billing/create-checkout`.
4. El backend crea cliente, dirección y transacción automática en Paddle.
5. El backend devuelve `checkout_url`.
6. El usuario paga en Paddle Checkout.
7. Paddle envía webhooks firmados a `POST /billing/webhook`.
8. El backend valida `Paddle-Signature`, actualiza `Subscription`, activa o ajusta `License`, y vuelve a firmar `signed_payload`.
9. TLAMATINI sincroniza y sigue funcionando offline con el payload local.

### Crear checkout

`POST /billing/create-checkout`

Requiere token.

```bash
curl -X POST http://127.0.0.1:8000/billing/create-checkout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "installation_id": "inst-local-001",
    "country_code": "MX",
    "postal_code": "91000"
  }'
```

Respuesta:

```json
{
  "checkout_url": "https://sandbox-pay.paddle.com/...",
  "transaction_id": "txn_...",
  "provider_customer_id": "ctm_...",
  "provider_subscription_id": null,
  "status": "ready"
}
```

### Validación del webhook

El backend valida la firma `Paddle-Signature` de forma obligatoria usando el body crudo:

1. extrae `ts` y `h1`
2. construye `ts:raw_body`
3. calcula `HMAC-SHA256` con `PADDLE_WEBHOOK_SECRET`
4. compara con `h1` usando comparación segura

Si no coincide, responde `401`.

Implementado según la documentación oficial de Paddle sobre verificación manual de webhooks y procesamiento del header `Paddle-Signature`:  
https://developer.paddle.com/webhooks/signature-verification

### Idempotencia y auditoría de webhooks

Cada webhook válido de Paddle se registra en `billing_webhook_events` con:

- `provider`
- `event_id`
- `event_type`
- `status`
- `payload`
- `error_message`
- `received_at`
- `processed_at`

Estados usados:

- `received`
- `processed`
- `ignored`
- `failed`

Reglas:

1. Primero se valida la firma.
2. Luego se extrae `event_id`.
3. Si el `event_id` ya existe con `status=processed`, el backend responde `200` y no reprocesa nada.
4. Si existe con `status=failed`, el backend permite reintento seguro.
5. Si no existe, se registra como `received`.
6. Después del procesamiento se marca como `processed`, `ignored` o `failed`.

Esto evita dobles activaciones por reentregas de Paddle y deja rastro claro para depuración.

### Revisar eventos procesados

`GET /billing/webhook-events`

Endpoint interno de depuración, protegido por autenticación básica del backend actual. No es todavía un endpoint admin formal.

```bash
curl "http://127.0.0.1:8000/billing/webhook-events?limit=50" \
  -H "Authorization: Bearer $TOKEN"
```

Sirve para revisar:

- webhooks recibidos
- duplicados ya procesados
- eventos ignorados
- eventos fallidos y su `error_message`

### Eventos manejados

El backend procesa los nombres reales de Paddle:

- `subscription.created`
- `subscription.updated`
- `subscription.activated`
- `subscription.canceled`
- `transaction.paid`
- `transaction.completed`
- `transaction.payment_failed`
- `transaction.past_due`

### Qué actualiza el backend

- `Subscription` por `provider_subscription_id` y cliente Paddle
- `License` por `user_id + installation_id`
- `signed_payload` nuevo tras cada cambio efectivo de estado

## Updates

### Modelo de release

El backend expone releases de aplicación con:

- `version`
- `platform`
- `channel`
- `title`
- `release_notes`
- `download_url`
- `sha256`
- `signature`
- `is_mandatory`
- `min_supported_version`
- `published_at`
- `is_active`

Plataformas válidas:

- `linux`
- `windows`
- `macos`

Canales válidos:

- `stable`
- `beta`
- `dev`

### Consultar actualización disponible

`GET /updates/check`

Parámetros:

- `current_version`
- `platform`
- `channel` opcional, por defecto `stable`

Ejemplo sin update:

```bash
curl "http://127.0.0.1:8000/updates/check?current_version=5.1.0&platform=linux&channel=stable"
```

Respuesta típica:

```json
{
  "update_available": false,
  "latest_version": "5.1.0",
  "is_mandatory": false,
  "title": null,
  "release_notes": null,
  "download_url": null,
  "sha256": null,
  "signature": null,
  "min_supported_version": null,
  "platform": "linux",
  "channel": "stable",
  "published_at": null
}
```

Ejemplo con update:

```bash
curl "http://127.0.0.1:8000/updates/check?current_version=5.1.0&platform=linux&channel=stable"
```

```json
{
  "update_available": true,
  "latest_version": "5.2.0",
  "is_mandatory": true,
  "title": "TLAMATINI 5.2.0",
  "release_notes": "Correcciones y mejoras",
  "download_url": "https://downloads.example.com/tlamatini-linux-5.2.0.zip",
  "sha256": "6f...",
  "signature": "firma-opcional",
  "min_supported_version": "5.0.0",
  "platform": "linux",
  "channel": "stable",
  "published_at": "2026-04-24T12:00:00+00:00"
}
```

Reglas:

- devuelve la release activa más reciente para `platform + channel`
- compara contra `current_version`
- marca `is_mandatory=true` si la release ya es obligatoria o si `current_version < min_supported_version`

### Crear una release manual

`POST /updates/releases`

Protección temporal:

- header `X-Admin-API-Key: <ADMIN_API_KEY>`

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/updates/releases \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: $ADMIN_API_KEY" \
  -d '{
    "version": "5.2.0",
    "platform": "linux",
    "channel": "stable",
    "title": "TLAMATINI 5.2.0",
    "release_notes": "Correcciones, changelog y metadata segura.",
    "download_url": "https://downloads.example.com/tlamatini-linux-5.2.0.zip",
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "signature": "firma-opcional",
    "is_mandatory": false,
    "min_supported_version": "5.0.0",
    "is_active": true
  }'
```

### Cómo probar update check local

1. Levanta el backend.
2. Publica una release `linux/stable` con `POST /updates/releases`.
3. Consulta con la misma versión para comprobar `update_available=false`.
4. Consulta con una versión menor para comprobar `update_available=true`.
5. Publica una release para otra plataforma y verifica que no se mezcle.
6. Marca `is_mandatory=true` o sube `min_supported_version` para comprobar update obligatorio.

### Depuración y uso futuro

- El cliente solo consume metadata de release en este bloque.
- La descarga puede validarse con `sha256` antes de cualquier instalación.
- `signature` queda lista para endurecer firma criptográfica de paquetes más adelante.
- No se ejecutan binarios ni instaladores desde el backend.

- `Subscription`
  - `provider_customer_id`
  - `provider_subscription_id`
  - `status`
  - `current_period_start`
  - `current_period_end`
- `License`
  - `plan`
  - `status`
  - `expires_at`
  - `grace_until`
  - `signed_payload` nuevo

La actualización es idempotente:

- `Subscription` se resuelve por `provider_subscription_id` o por combinación `user_id + installation_id + provider`
- `License` se actualiza por `user_id + installation_id`
- `signed_payload` solo se vuelve a firmar con el estado final, por lo que reentregas del mismo evento no deben crear una segunda licencia

### Compatibilidad offline

- TLAMATINI puede seguir usando `signed_payload` local sin internet.
- Cuando hay internet, sincroniza contra el backend.
- Si el pago entra, el backend firma un nuevo payload.
- Si hay problema de cobro, el backend mueve la licencia a `grace` o `expired` según `grace_until`.

### Probar en sandbox

1. Crea cuenta sandbox de Paddle.
2. Crea `product` y `price` mensual en Paddle sandbox.
3. Copia `PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET`, `PADDLE_PRODUCT_ID`, `PADDLE_PRICE_ID` a `.env`.
4. Define `PADDLE_ENVIRONMENT=sandbox`.
5. Expón tu backend con un túnel si pruebas localmente, por ejemplo `ngrok`, y registra `/billing/webhook` como notification destination.
6. Registra usuario y login en TLAMATINI.
7. Registra instalación.
8. Llama `POST /billing/create-checkout`.
9. Abre `checkout_url` y completa el pago sandbox.
10. Verifica que llegue `transaction.completed` o `subscription.activated`.
11. Consulta `GET /licenses/status?installation_id=...` y confirma `plan=monthly`, `status=active`.
12. Consulta `GET /billing/webhook-events` para confirmar que el evento quedó `processed`.

### Depurar webhooks de Paddle

Si un webhook no tuvo el efecto esperado:

1. revisa que la firma `Paddle-Signature` sea válida
2. revisa `GET /billing/webhook-events`
3. busca el `event_id`
4. verifica `status`
5. si está en `failed`, revisa `error_message`
6. si Paddle reintenta el mismo webhook y el backend ya lo marcó `processed`, se responderá `200` sin aplicar cambios otra vez

Paddle usa entornos y base URLs separados para sandbox y live según su documentación oficial:  
https://developer.paddle.com/build/tools/sandbox  
https://developer.paddle.com/api-reference/overview

## Errores esperados

- usuario duplicado: `409 Ya existe un usuario con ese email.`
- credenciales inválidas: `401 Credenciales inválidas.`
- token inválido/expirado: `401 Token inválido o expirado.`
- token ausente: `401 Token inválido o ausente.`
- instalación ajena o inexistente: `404 Instalación no encontrada para el usuario.`
- firma inválida: respuesta `is_valid=false` en `/licenses/verify`

## Pruebas básicas

Suite local mínima:

```bash
cd backend
pytest
```

Prueba manual paso a paso:

1. Registrar usuario con `POST /auth/register`.
2. Iniciar sesión con `POST /auth/login`.
3. Guardar el `access_token` en `TOKEN`.
4. Consultar perfil con `GET /auth/me`.
5. Registrar la instalación con `POST /installations/register`.
6. Listar instalaciones con `GET /installations`.

## Estado para el siguiente bloque

Este bloque ya deja lista la base para emitir licencias firmadas ligadas a:

- `user_id`
- `installation_id`

Todavía no incluye:

- integración real con Paddle
- cobros
- emisión y firma real de licencias
- verificación online/offline avanzada
