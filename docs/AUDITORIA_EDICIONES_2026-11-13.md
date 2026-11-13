# Auditoría de las seis ediciones de TLAMATINI — 13 de noviembre de 2026

## Dictamen

**Los seis comandos públicos descargan y verifican los archivos correctos y, después de las correcciones, instalan y abren la edición elegida en los entornos de prueba. Las seis ediciones NO se certifican como completas ni como validadas para 4/8 GB de RAM.**

Las instalaciones y pruebas de IA se ejecutaron en servidores de GitHub, de forma secuencial. No se instalaron estas aplicaciones ni se cargaron sus modelos durante esta auditoría en la computadora del usuario.

## Resultado por edición

| Edición | Descarga e integridad | Instalación y arranque normal | IA: respuesta breve | Pendientes relevantes |
| --- | --- | --- | --- | --- |
| Linux 5.2.6 · Gemma 3 1B · objetivo 4 GB | Aprobadas | Aprobados | Aprobada | PDF/OCR ausentes; dependencias de sistema no declaradas; motores IA duplicados y residentes después del cierre |
| Linux 5.2.6 · Gemma 3 4B · objetivo 8 GB | Aprobadas | Aprobados | Aprobada | PDF/OCR ausentes; dependencias de sistema no declaradas; motores IA duplicados y residentes después del cierre |
| Linux 5.2.6 sin IA | Aprobadas | Aprobados | No aplica | PDF/OCR ausentes; dependencias de sistema no declaradas |
| Windows 5.2.6 · Gemma 3 1B · objetivo 4 GB | Aprobadas | Aprobados | Aprobada | Motor OCR externo no incluido ni instalado por el descargador; motores IA duplicados y residentes después del cierre |
| Windows 5.2.6 · Gemma 3 4B · objetivo 8 GB | Aprobadas | Aprobados | Aprobada | Motor OCR externo no incluido ni instalado por el descargador; motores IA duplicados y residentes después del cierre |
| Windows 5.2.6 sin IA | Aprobadas | Aprobados | No aplica | Motor OCR externo no incluido ni instalado por el descargador |

## Fallos de comandos corregidos

1. **Linux podía anunciar una instalación correcta y conservar otra edición.** Sin IA y Gemma 3 1B comparten la revisión de paquete `5.2.6-6`. En la primera prueba, `apt` indicó que ya estaba instalada la última versión y dejó el ejecutable sin IA. Se añadió reinstalación explícita, autorización de la revisión seleccionada y comprobación del SHA-256 del ejecutable instalado. La segunda prueba instaló correctamente sin IA, luego Gemma 3 1B y después Gemma 3 4B.
2. **Linux con Gemma 3 4B rechazaba el primer fragmento por SHA-256 incorrecto.** Las huellas de los 44 fragmentos y la suma final usadas por el catálogo estaban desactualizadas. Se contrastaron los 44 fragmentos con las huellas calculadas por GitHub y una copia completa que coincide byte por byte, por fragmentos, con lo publicado. Se corrigieron el catálogo público, `SHA256SUMS.txt` de v5.2.6 y su descargador Linux heredado. No se alteró ningún fragmento ni se desactivó la verificación.
3. **No se comprobaba la compatibilidad de glibc.** Los tres ejecutables Linux incluyen una biblioteca Python que necesita al menos glibc 2.38. El descargador ahora rechaza una instalación incompatible antes de bajar el paquete. La descarga para otro equipo sigue disponible con el modo de solo descarga.

SHA-256 correcto del paquete Linux Gemma 3 4B reconstruido:

```text
85c3c6333064986219c8963774e5eb84e8fd41f495cde4f8a9cf58e01e913177
```

## Defectos de las aplicaciones o paquetes pendientes de corregir

### Prioridad alta: motores de IA duplicados y memoria que no se libera al cerrar

Se observó más de un servidor `llama-server` para el mismo modelo durante el arranque normal. En Linux, los registros muestran el primer servidor en un puerto dinámico y otro en el puerto 18437. Las cuatro ediciones con IA dejaron al menos un motor vivo después de la solicitud de cierre de ventana. La auditoría detuvo esos procesos al terminar cada prueba.

La revisión de código localizó un origen: el arranque crea su propia instancia de `LocalInferenceService`, mientras la interfaz utiliza otra; la selección de puertos no conserva de forma consistente el puerto dinámico del primer proceso al reutilizar el PID. Esto permite cargar otro motor y complica el cierre correcto. Hace falta corregir ese ciclo de vida, reconstruir las ediciones con IA y repetir las mediciones.

### Prioridad alta: los tres paquetes Linux carecen de PDF/OCR

La inspección de los ejecutables confirmó la ausencia de `fitz`/PyMuPDF, `pypdf` y `pytesseract`. La lectura de PDF y el OCR no están completos. Instalar un módulo con `pip` en el sistema del usuario no incorpora ese módulo a un ejecutable ya congelado con PyInstaller: estos paquetes requieren regenerarse incluyendo sus dependencias.

Los controles DEB tampoco declaran dependencias de sistema. El funcionamiento observado en Ubuntu 24.04 de GitHub no garantiza un sistema mínimo sin las bibliotecas necesarias.

### Prioridad media/alta: OCR en Windows depende de una instalación adicional

Las tres ediciones Windows incluyen PyMuPDF y el módulo Python `pytesseract`, pero no incluyen el ejecutable Tesseract ni lo preparan desde el descargador. El motor externo no estaba disponible en los entornos de prueba. Hace falta empaquetarlo con sus datos de idiomas o automatizar y verificar esa dependencia para considerar el OCR completo.

### Compatibilidad y presentación

- Linux necesita glibc 2.38 o superior en los paquetes auditados; no basta con que el sistema acepte archivos DEB.
- La interfaz sin IA muestra el aviso “Gemma no disponible”. No significa que falte un modelo que esa edición deba descargar, pero la indicación debería adaptarse a la edición.
- No se detectó corrupción de los cuatro instaladores nuevos. Las copias locales de las dos distribuciones completas históricas no coinciden todas con las publicaciones actuales y no deben sustituirse unas por otras sin comprobar sus sumas.

## Mediciones y límites de interpretación

La respuesta breve pedida fue una suma simple en español. Los cuatro modelos respondieron correctamente. Esto prueba carga e inferencia básica, no calidad general de respuestas ni una sesión prolongada.

| Edición con IA | Pico RSS de un motor aislado | Suma RSS del árbol de procesos al observar el arranque |
| --- | --- | --- |
| linux Gemma 3 1B Q4_K_M | 925 MiB | 1.92 GiB |
| linux Gemma 3 4B Q4_K_M | 4168 MiB | 8.24 GiB |
| windows Gemma 3 1B Q4_K_M | 924 MiB | 1.94 GiB |
| windows Gemma 3 4B Q4_K_M | 4160 MiB | 8.25 GiB |

**La suma RSS puede contar páginas compartidas varias veces. No es una medición de RAM física única ni del consumo de todo el equipo.** No se midió PSS/USS ni se ensayó hardware real limitado a 4 u 8 GB. Las cifras de RAM de las ediciones son objetivos, no capacidades certificadas. La duplicación del motor debe resolverse antes de certificarlas.

## Alcance de las comprobaciones

- Archivos de las seis ediciones y todas sus partes: existencia, tamaño, SHA-256 y reconstrucción cuando corresponde.
- Ejecución de los descargadores publicados, instalación nativa y cambio entre las tres ediciones Linux.
- Confirmación de la edición instalada, ayuda por consola, apertura normal de la interfaz y captura de pantalla.
- Presencia y carga de los modelos GGUF, salud del servidor e inferencia breve.
- Solicitud de cierre de ventana y detección de motores que permanecen vivos.
- Inventario de componentes de PDF y OCR y revisión de compatibilidad Linux.

No se certificaron cámara/GPS físicos, todos los flujos de mapas, todos los módulos, extracción real de PDF/OCR, todas las versiones de Windows/Linux, almacenamiento prolongado ni equipos reales de 4/8 GB.

El primer inventario emitió un aviso de `cv2` ausente al buscar únicamente módulos del archivo PYZ. OpenCV también puede ir empaquetado como archivos externos a PYZ. Se confirmó su presencia en los Linux. Los avisos de cámara de los JSON iniciales no se usan como prueba de un defecto de cámara en Windows; la inspección del auditor se ajustó para normalizar separadores de rutas. La prueba con hardware sigue pendiente.

## Evidencia y repetición

- [Primera auditoría: fallos originales](https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/actions/runs/43484904079).
- [Segunda auditoría: comandos corregidos y arranque normal](https://github.com/TlamatiniSoftwareMX/Tlamatini-Software/actions/runs/43491408556).
- Rama de herramientas: `build/four-editions-20261113`; workflow `Build Full`, modo `audit-editions`.
- Informes JSON, registros y capturas están conservados localmente en `TLAMATINI Versiones/Auditoria-2026-11-13/`.
- Se añadieron pruebas de regresión para reinstalar una revisión idéntica, seleccionar la revisión pedida, no anunciar éxito con un ejecutable distinto y rechazar glibc incompatible.

Que las comprobaciones de descarga/arranque del workflow terminen correctamente no convierte en aprobadas las funciones que figuran aquí como incompletas.

## Orden de reparación recomendado

1. Unificar el servicio de IA y persistir correctamente su endpoint/PID; evitar arranques duplicados y cerrar todos los procesos propios.
2. Incluir las dependencias PDF/OCR en Linux y preparar el motor OCR en Windows; declarar los requisitos de sistema.
3. Regenerar los paquetes afectados y mantener versiones/revisiones distintas y verificables entre ediciones.
4. Repetir la instalación, el uso de módulos y las mediciones en equipos reales con 4/8 GB antes de certificar esas capacidades.
