# TLAMATINI Backend: Hardening para Producción y Pagos

## Reglas mínimas antes de cobrar

- `APP_ENV=production`
- `API_BASE_URL` debe usar `https://`
- `AUTO_CREATE_TABLES=false`
- `ALLOWED_HOSTS` debe listar el dominio real del backend
- `CORS_ALLOW_ORIGINS` debe listar solo orígenes permitidos
- `ADMIN_API_KEY` debe ser fuerte y única
- `JWT_SECRET` debe ser fuerte y única
- `PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET`, `PADDLE_PRODUCT_ID`, `PADDLE_PRICE_ID` no pueden ser placeholders
- La firma de licencias debe usar claves definitivas:
  - preferido: `RS256`
  - requeridas: `LICENSE_PRIVATE_KEY` y `LICENSE_PUBLIC_KEY`

## Despliegue recomendado

1. Backend en dominio HTTPS propio.
2. Base de datos PostgreSQL dedicada.
3. Secretos fuera del repositorio.
4. Webhook de Paddle apuntando al dominio público real.
5. Monitoreo de:
   - errores 5xx,
   - fallos de webhook,
   - activaciones de licencia,
   - intentos fallidos de login,
   - releases de updates.

## No hacer en producción

- No usar `127.0.0.1:8000` como backend SaaS.
- No dejar `AUTO_CREATE_TABLES=true`.
- No usar `CORS_ALLOW_ORIGINS=*`.
- No exponer `billing/webhook-events` sin `ADMIN_API_KEY`.
- No depender de claves placeholder o `.env` de prueba.

## Validación operativa antes de salir

- Registro de usuario
- Login
- Registro de instalación
- Activación de trial
- Checkout
- Webhook firmado de Paddle
- Activación de licencia pagada
- Reinicio de la app con licencia local válida
- Modo offline sin internet
- Re-sincronización al recuperar conectividad
