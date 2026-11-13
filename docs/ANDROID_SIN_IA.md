# TLAMATINI para Android sin IA — viabilidad inicial

Es viable crear una aplicación Android instalable mediante APK, sin Gemma,
llama.cpp, Ollama ni descarga de modelos de lenguaje. Actualmente el proyecto
no tiene un módulo Android, Gradle ni una configuración de empaquetado APK.

## Qué puede aprovecharse

- Lógica Python de `core/` y `sistema/` que no depende de Tkinter.
- Estructuras de inventario, planes, perfiles y datos offline.
- Catálogos y contenido de consulta, después de revisar qué datos se incluyen.
- Visor web de mapas de `map_ui/`, con adaptación del acceso a archivos,
  almacenamiento, servidor local y permisos del teléfono.

## Qué debe adaptarse

- Pantallas, navegación y tamaño de controles para una pantalla táctil.
- Cámara, selección de archivos, almacenamiento y permisos de Android.
- Lectura de PDF y ubicación; sus implementaciones de escritorio no se copian
  directamente al teléfono.
- Gestión de datos al actualizar o desinstalar la aplicación.
- Dependencias Python con extensiones nativas: requieren versiones compatibles
  con Android o un reemplazo nativo.

La interfaz actual usa Tkinter. Empaquetar el EXE o el DEB no produce un APK.
Es necesario construir una interfaz móvil y conectar las funciones reutilizadas.

## Opciones técnicas por evaluar

- Interfaz nativa Android con Kotlin y, si aporta ventajas, reutilización de
  Python mediante [Chaquopy](https://chaquo.com/chaquopy/documentation/).
- Interfaz Python adaptada a móvil mediante
  [Kivy y su empaquetado Android](https://kivy.org/doc/stable/guide/android.html).

La elección debe basarse en las dependencias que realmente necesita la
primera versión, el tamaño final, la compatibilidad y pruebas en teléfonos.
No se ha comprometido todavía un tamaño de APK ni una RAM mínima.

## Construcción y pruebas

En esta computadora se encontraron Java y Android platform-tools (`adb`).
No se encontró Gradle ni `sdkmanager` en PATH y el SDK disponible contiene
platform-tools. La compilación puede prepararse en GitHub Actions y probarse
en un teléfono físico, evitando un emulador local que sature la RAM.

## Alcance pendiente de definir

Se consultó si la primera versión debe trasladar todos los módulos sin IA
o priorizar consulta offline, inventario y planes de emergencia. El proyecto
APK aún no se ha iniciado y esta nota no implica que ya exista una aplicación
Android funcional.
