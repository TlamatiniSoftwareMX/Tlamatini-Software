import cv2
import numpy as np
from typing import Dict


def analizar_imagen_basico(ruta_imagen: str) -> Dict:
    try:
        img = cv2.imread(ruta_imagen)

        if img is None:
            return {"ok": False, "error": "No se pudo leer la imagen"}

        alto, ancho = img.shape[:2]

        # brillo promedio
        gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brillo = int(np.mean(gris))

        # contraste aproximado
        contraste = int(np.std(gris))

        # detección muy básica de "tipo"
        tipo = "desconocido"

        if brillo < 60:
            tipo = "oscuro"
        elif brillo > 180:
            tipo = "muy iluminado"
        else:
            tipo = "iluminacion_media"

        # detección simple de colores dominantes
        promedio_color = img.mean(axis=(0, 1))
        b, g, r = promedio_color

        color_dominante = "neutro"
        if g > r and g > b:
            color_dominante = "verde"
        elif r > g and r > b:
            color_dominante = "rojo"
        elif b > r and b > g:
            color_dominante = "azul"

        return {
            "ok": True,
            "ancho": ancho,
            "alto": alto,
            "brillo": brillo,
            "contraste": contraste,
            "tipo_iluminacion": tipo,
            "color_dominante": color_dominante
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}