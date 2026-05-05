import re
from datetime import datetime
from typing import Dict
from pathlib import Path

try:
    import cv2
except Exception:
    cv2 = None

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except Exception:
    pyzbar_decode = None

from core.memoria import RUTA_BASE_DATOS

RUTA_FOTOS = RUTA_BASE_DATOS / "inventario_fotos"
VENTANA_CAPTURA_INVENTARIO = "TLAMATINI - Captura inventario"
VENTANA_ESCANER_CODIGO = "TLAMATINI - Escaner de codigo"
DETECTOR_CODIGO = cv2.barcode_BarcodeDetector() if cv2 is not None and hasattr(cv2, "barcode_BarcodeDetector") else None


def _abrir_camara():
    if cv2 is None:
        return None

    backends = []
    if hasattr(cv2, "CAP_DSHOW"):
        backends.append(cv2.CAP_DSHOW)
    backends.append(None)

    for backend in backends:
        try:
            cap = cv2.VideoCapture(0, backend) if backend is not None else cv2.VideoCapture(0)
        except Exception:
            continue
        if cap is not None and cap.isOpened():
            return cap
        try:
            cap.release()
        except Exception:
            pass
    return None


def _preparar_ventana(nombre: str) -> None:
    try:
        cv2.namedWindow(nombre, cv2.WINDOW_NORMAL)
    except Exception:
        return
    try:
        cv2.resizeWindow(nombre, 960, 720)
    except Exception:
        pass


def _tecla_captura() -> int:
    try:
        return cv2.waitKey(20) & 0xFF
    except Exception:
        return -1


def _es_tecla_captura(tecla: int) -> bool:
    return tecla in {32, 10, 13, ord("c"), ord("C"), ord("s"), ord("S")}


def _guardar_frame(frame, prefijo: str) -> str:
    nombre = datetime.now().strftime(f"{prefijo}_%Y%m%d_%H%M%S.jpg")
    ruta = RUTA_FOTOS / nombre
    try:
        guardado = cv2.imwrite(str(ruta), frame)
    except Exception:
        guardado = False
    return str(ruta) if guardado and Path(ruta).exists() else ""


def _variantes_frame_codigo(frame):
    variantes = [frame]
    try:
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variantes.append(gris)
        variantes.append(cv2.GaussianBlur(gris, (3, 3), 0))
        variantes.append(cv2.convertScaleAbs(gris, alpha=1.35, beta=12))
    except Exception:
        pass
    return variantes


def _extraer_codigo_con_pyzbar(frame):
    if pyzbar_decode is None:
        return "", None

    try:
        resultados = pyzbar_decode(frame)
    except Exception:
        return "", None

    for codigo in resultados:
        try:
            codigo_detectado = codigo.data.decode("utf-8").strip()
        except Exception:
            codigo_detectado = str(codigo.data).strip()
        rect = getattr(codigo, "rect", None)
        if not codigo_detectado:
            continue
        if rect is None:
            return codigo_detectado, None
        return codigo_detectado, (rect.left, rect.top, rect.width, rect.height)

    return "", None


def _extraer_codigo_con_opencv(frame):
    if DETECTOR_CODIGO is None:
        return "", None

    for variante in _variantes_frame_codigo(frame):
        try:
            ok, decoded_info, decoded_type, points = DETECTOR_CODIGO.detectAndDecodeWithType(variante)
        except Exception:
            try:
                ok, decoded_info, points = DETECTOR_CODIGO.detectAndDecode(variante)
                decoded_type = None
            except Exception:
                continue

        if not ok:
            continue

        codigo_detectado = ""
        if isinstance(decoded_info, (list, tuple)):
            for item in decoded_info:
                if str(item).strip():
                    codigo_detectado = str(item).strip()
                    break
        elif str(decoded_info).strip():
            codigo_detectado = str(decoded_info).strip()

        if not codigo_detectado:
            continue

        rect = None
        try:
            if points is not None and len(points):
                pts = points[0] if hasattr(points[0], "__len__") and len(points.shape) > 2 else points
                xs = [int(p[0]) for p in pts]
                ys = [int(p[1]) for p in pts]
                rect = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
        except Exception:
            rect = None
        return codigo_detectado, rect

    return "", None


def _leer_codigo_barras(frame):
    codigo_detectado, rect = _extraer_codigo_con_pyzbar(frame)
    if codigo_detectado:
        return codigo_detectado, rect
    return _extraer_codigo_con_opencv(frame)


def capturar_foto_inventario() -> Dict[str, str]:
    return capturar_foto_inventario_configurable(guardar=True)


def capturar_foto_inventario_configurable(guardar: bool = True) -> Dict[str, str]:
    if cv2 is None:
        return {
            "estado": "error",
            "mensaje": "OpenCV no está disponible en TLAMATINI."
        }

    RUTA_FOTOS.mkdir(parents=True, exist_ok=True)

    cap = _abrir_camara()
    if cap is None:
        return {
            "estado": "error",
            "mensaje": "No se pudo abrir la cámara."
        }

    ruta_guardado = ""
    _preparar_ventana(VENTANA_CAPTURA_INVENTARIO)

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        texto = "ESPACIO = capturar | ESC = cancelar"
        cv2.putText(
            frame,
            texto,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imshow(VENTANA_CAPTURA_INVENTARIO, frame)
        tecla = _tecla_captura()

        if tecla == 27:
            cap.release()
            cv2.destroyAllWindows()
            return {
                "estado": "cancelado",
                "mensaje": "Captura cancelada por el usuario."
            }

        if _es_tecla_captura(tecla):
            if guardar:
                ruta_guardado = _guardar_frame(frame, "INV")
                if not ruta_guardado:
                    cap.release()
                    cv2.destroyAllWindows()
                    return {
                        "estado": "error",
                        "mensaje": "No se pudo guardar la foto capturada."
                    }
            break

    cap.release()
    cv2.destroyAllWindows()

    return {
        "estado": "ok",
        "ruta_foto": ruta_guardado,
        "frame_capturado": frame,
        "mensaje": "Foto capturada correctamente."
    }


def capturar_codigo_barras_inventario() -> Dict[str, str]:
    if cv2 is None:
        return {
            "estado": "error",
            "mensaje": "OpenCV no está disponible en TLAMATINI."
        }

    RUTA_FOTOS.mkdir(parents=True, exist_ok=True)

    cap = _abrir_camara()
    if cap is None:
        return {
            "estado": "error",
            "mensaje": "No se pudo abrir la cámara."
        }

    codigo_detectado = ""
    frame_capturado = None
    ultimo_codigo = ""
    lecturas_consecutivas = 0
    _preparar_ventana(VENTANA_ESCANER_CODIGO)

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        frame_original = frame.copy()
        codigo_detectado_frame, rect = _leer_codigo_barras(frame)
        if codigo_detectado_frame:
            codigo_detectado = codigo_detectado_frame
            frame_capturado = frame_original
            if rect is not None:
                x, y, w, h = rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (53, 216, 255), 2)
                cv2.putText(
                    frame,
                    codigo_detectado[:48],
                    (x, max(y - 10, 30)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (53, 216, 255),
                    2,
                )
        else:
            codigo_detectado = ""

        if codigo_detectado:
            if codigo_detectado == ultimo_codigo:
                lecturas_consecutivas += 1
            else:
                ultimo_codigo = codigo_detectado
                lecturas_consecutivas = 1
        else:
            ultimo_codigo = ""
            lecturas_consecutivas = 0

        if lecturas_consecutivas >= 3 and frame_capturado is not None:
            cap.release()
            cv2.destroyAllWindows()
            return {
                "estado": "ok",
                "codigo_barras": codigo_detectado,
                "mensaje": "Código detectado automáticamente."
            }

        texto = "Apunta el codigo a la camara | deteccion automatica | ESC = cancelar"
        cv2.putText(frame, texto, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if codigo_detectado:
            cv2.putText(
                frame,
                f"Detectando: {codigo_detectado[:32]}",
                (20, 78),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (53, 216, 255),
                2,
            )
        cv2.imshow(VENTANA_ESCANER_CODIGO, frame)
        tecla = _tecla_captura()

        if tecla == 27:
            cap.release()
            cv2.destroyAllWindows()
            return {
                "estado": "cancelado",
                "mensaje": "Escaneo cancelado por el usuario."
            }

        if _es_tecla_captura(tecla):
            frame_capturado = frame_capturado if frame_capturado is not None else frame_original
            if codigo_detectado:
                cap.release()
                cv2.destroyAllWindows()
                return {
                    "estado": "ok",
                    "codigo_barras": codigo_detectado,
                    "mensaje": "Código detectado correctamente."
                }
            cap.release()
            cv2.destroyAllWindows()
            return {
                "estado": "error",
                "mensaje": "No se pudo leer el código de barras. Acerca más el empaque o mejora la iluminación."
            }

    cap.release()
    cv2.destroyAllWindows()

    return {
        "estado": "ok",
        "codigo_barras": codigo_detectado,
        "mensaje": "Código detectado correctamente."
    }


def extraer_texto_ocr(ruta_imagen: str) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""

    try:
        texto = pytesseract.image_to_string(Image.open(ruta_imagen), lang="spa+eng")
        return texto.strip()
    except Exception:
        return ""


def extraer_texto_ocr_frame(frame) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""

    if frame is None:
        return ""

    try:
        if len(frame.shape) == 3:
            imagen = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        else:
            imagen = Image.fromarray(frame)
        texto = pytesseract.image_to_string(imagen, lang="spa+eng")
        return texto.strip()
    except Exception:
        return ""


def _normalizar_ocr(texto: str) -> str:
    return re.sub(r"[ \t]+", " ", (texto or "").replace("\r", "\n"))


def _lineas_nutrimentales(texto: str):
    lineas = [l.strip() for l in _normalizar_ocr(texto).splitlines() if l.strip()]
    if not lineas:
        return []

    inicio_patrones = [
        r"informaci[oó]n nutrimental",
        r"declaraci[oó]n nutrimental",
        r"tabla nutrimental",
        r"nutrition facts",
        r"nutrition information",
        r"nutritional facts",
        r"nutritional information",
    ]
    fin_patrones = [
        r"ingredientes",
        r"ingredient[s]?",
        r"contenido neto",
        r"net content",
        r"conservaci[oó]n",
        r"modo de empleo",
        r"instrucciones",
        r"fabricado por",
        r"manufacturer",
        r"distribuido por",
        r"advertencia",
        r"warning",
    ]

    inicio = 0
    for idx, linea in enumerate(lineas):
        if any(re.search(p, linea, flags=re.IGNORECASE) for p in inicio_patrones):
            inicio = idx
            break

    seleccion = []
    for linea in lineas[inicio:]:
        if any(re.search(p, linea, flags=re.IGNORECASE) for p in fin_patrones):
            break
        seleccion.append(linea)

    return seleccion or lineas


def _buscar_valor_nutrimental(lineas, alias):
    patrones_valor = [
        r"(\d+(?:[.,]\d+)?)\s*(kcal|cal|kj|g|gr|mg|mcg|ug|ml)?",
    ]
    for linea in lineas:
        linea_n = linea.lower()
        if not any(a in linea_n for a in alias):
            continue
        for patron in patrones_valor:
            match = re.search(patron, linea, flags=re.IGNORECASE)
            if not match:
                continue
            valor = match.group(1).replace(",", ".")
            unidad = (match.group(2) or "").strip()
            return f"{valor} {unidad}".strip()
    return ""


def analizar_texto_nutrimental(texto: str) -> Dict[str, str]:
    if not texto:
        return {
            "nombre_sugerido": "",
            "peso_sugerido": "",
            "caducidad_sugerida": "",
            "datos_nutrimentales": "",
        }

    lineas = [l.strip() for l in _normalizar_ocr(texto).splitlines() if l.strip()]
    nombre_sugerido = lineas[0] if lineas else ""

    peso = ""
    caducidad = ""

    peso_match = re.search(r"(\d+(?:[.,]\d+)?)\s?(kg|g|gr|ml|l)\b", texto, flags=re.IGNORECASE)
    if peso_match:
        peso = f"{peso_match.group(1)} {peso_match.group(2)}"

    cad_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto)
    if cad_match:
        caducidad = cad_match.group(1)

    datos = []
    lineas_nutrimentales = _lineas_nutrimentales(texto)
    alias_map = {
        "porcion": ["porcion", "porción", "serving", "serv size", "serving size", "portion"],
        "energía": ["energia", "energía", "calorias", "calorías", "calories", "kcal", "energy"],
        "proteína": ["proteina", "proteínas", "proteinas", "protein", "prot"],
        "carbohidratos": ["carbohidratos", "carbohydrate", "carbohydrates", "carbs", "hidratos", "cho"],
        "grasas": ["grasas", "grasa total", "fat", "total fat", "lipidos", "lipids", "lipidos totales"],
        "fibra": ["fibra", "fiber", "dietary fiber", "fibre"],
        "sodio": ["sodio", "sodium", "na"],
        "azucares": ["azucares", "azúcares", "sugars", "sugar"],
    }

    for etiqueta in ["porcion", "energía", "proteína", "carbohidratos", "grasas", "fibra", "sodio", "azucares"]:
        valor = _buscar_valor_nutrimental(lineas_nutrimentales, alias_map[etiqueta])
        if valor:
            datos.append(f"{etiqueta}: {valor}")

    return {
        "nombre_sugerido": nombre_sugerido,
        "peso_sugerido": peso,
        "caducidad_sugerida": caducidad,
        "datos_nutrimentales": "\n".join(datos),
    }


def capturar_y_analizar_inventario() -> Dict[str, str]:
    captura = capturar_foto_inventario_configurable(guardar=False)

    if captura.get("estado") != "ok":
        return captura

    ruta = captura.get("ruta_foto", "")
    texto = extraer_texto_ocr_frame(captura.get("frame_capturado"))
    analisis = analizar_texto_nutrimental(texto)

    return {
        "estado": "ok",
        "mensaje": "Foto capturada y analizada.",
        "ruta_foto": ruta,
        "texto_ocr": texto,
        **analisis,
    }
