"""
image_processor.py — Preprocesamiento de imágenes con OpenCV.

Mejora la calidad de las imágenes antes de pasarlas a Tesseract OCR:
  1. Conversión a escala de grises.
  2. Escalado opcional.
  3. Umbralización (Otsu o adaptativa).
  4. Eliminación de ruido.
"""

import logging
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def preprocesar_imagen(imagen_pil: Image.Image) -> Image.Image:
    """
    Aplica el pipeline de preprocesamiento sobre una imagen PIL.

    Pasos:
      - Convierte a escala de grises.
      - Redimensiona según el factor de escala configurado.
      - Aplica umbralización para binarizar la imagen.
      - Elimina ruido con morfología.

    Args:
        imagen_pil: Imagen PIL en color o escala de grises.

    Returns:
        Imagen PIL preprocesada, lista para OCR.
    """
    try:
        import cv2
    except ImportError:
        raise ImportError(
            "opencv-python no está instalado. Ejecuta: pip install opencv-python"
        )

    from modules.config import CONFIG

    metodo = CONFIG.get("metodo_umbral", "otsu")
    escala = CONFIG.get("escala_imagen", 1.5)

    # PIL → NumPy (BGR para OpenCV)
    img_np = np.array(imagen_pil)

    # 1. Escala de grises
    if len(img_np.shape) == 3:
        if img_np.shape[2] == 4:  # RGBA
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
        else:  # RGB
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    # Si ya es escala de grises (2D), no se necesita conversión

    # 2. Redimensionado (mejora legibilidad en documentos pequeños)
    if escala != 1.0:
        alto, ancho = img_np.shape
        img_np = cv2.resize(
            img_np,
            (int(ancho * escala), int(alto * escala)),
            interpolation=cv2.INTER_CUBIC,
        )

    # 3. Umbralización
    if metodo == "otsu":
        # Binarización global automática (Otsu)
        _, img_np = cv2.threshold(
            img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    elif metodo == "adaptativo":
        # Umbralización local (útil en documentos con iluminación desigual)
        img_np = cv2.adaptiveThreshold(
            img_np,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=31,
            C=10,
        )
    else:
        logger.warning(
            f"Método de umbralización desconocido '{metodo}'. Usando Otsu."
        )
        _, img_np = cv2.threshold(
            img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

    # 4. Eliminación de ruido morfológico (kernel pequeño)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    img_np = cv2.morphologyEx(img_np, cv2.MORPH_CLOSE, kernel)

    # NumPy → PIL
    return Image.fromarray(img_np)
