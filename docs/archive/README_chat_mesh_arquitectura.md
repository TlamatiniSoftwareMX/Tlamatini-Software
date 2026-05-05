# Arquitectura del módulo Chat Mesh

## Objetivo

TLAMATINI debe comportarse como un monitor de conversación para una placa de desarrollo con Meshtastic conectada por USB o Bluetooth. La aplicación detecta el dispositivo, mantiene el contexto conversacional y presenta el estado operativo dentro de la UI.

## Capas

### 1. Persistencia

- `core/chat_mesh.py`
- Guarda nodos, conversaciones, mensajes y `runtime`.
- `runtime` conserva el último estado conocido del monitor: adaptador activo, dispositivo detectado, escaneo y estado de sesión.

### 2. Sesión Mesh

- `core/mesh_service.py`
- Expone `MeshSessionService` como punto único del módulo.
- Responsabilidades:
  - Escanear dispositivos candidatos por USB/Bluetooth.
  - Elegir un dispositivo preferido.
  - Mantener un estado de sesión legible por la UI.
  - Publicar eventos del módulo.
  - Registrar mensajes salientes y entrantes.
  - Separar el transporte real del resto del sistema.

### 3. Transporte

- `MeshTransportAdapter` define la interfaz.
- `NullMeshAdapter` permite operar el módulo en modo monitor aunque todavía no exista backend de radio.
- `MeshtasticPythonAdapter` queda reservado como punto de integración futura para hablar con una placa real sin cambiar la UI ni la persistencia.

## Flujo esperado

1. El usuario abre `Chat Mesh`.
2. `MeshSessionService` escanea dispositivos candidatos cada pocos segundos.
3. Si detecta una ruta compatible, actualiza `runtime` y la ventana muestra el estado.
4. La conversación se mantiene por `peer_id`.
5. Cuando exista un adaptador Meshtastic funcional, `send_message()` y la recepción entrante usarán esa capa sin rediseñar la UI.

## Estado actual

- La arquitectura ya no depende solo de un JSON local.
- La ventana ya muestra estado de detección y sesión.
- El envío pasa por un servicio central.
- La radio real todavía no está integrada; hoy opera en modo `monitor-only`.

## Punto de extensión futuro

Para activar conversación real con la placa:

- Implementar `connect()`, `disconnect()` y `send_text()` en `MeshtasticPythonAdapter`.
- Añadir suscripción a mensajes entrantes y mapearlos a `register_inbound_message()`.
- Registrar peers desde telemetría o metadatos reales de Meshtastic.
