"""
config.py — Configuración centralizada del extractor.

Modifica este archivo para adaptar el programa a tu entorno y documentos.
"""

import os
import sys

def obtener_ruta_poppler():
    """Obtiene la ruta de los binarios de Poppler.
    Si está empaquetado con PyInstaller, usa _MEIPASS.
    Si no, usa la ruta relativa del proyecto."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'poppler', 'bin')
    return os.path.join(os.path.dirname(__file__), "..", "poppler", "Library", "bin")

CONFIG = {
    # ── Rutas ────────────────────────────────────────────────────────────────
    # Carpeta donde están los PDFs a procesar
    "carpeta_pdfs": os.path.join(os.path.dirname(__file__), "..", "pdfs"),

    # Nombre del archivo Excel de salida
    "archivo_excel": os.path.join(os.path.dirname(__file__), "..", "recolectas_extraidas.xlsx"),

    # ── OCR ──────────────────────────────────────────────────────────────────
    # Ya no se usa Tesseract. El sistema utiliza el motor nativo de Windows (WinRT)
    # que se auto-configura con el idioma principal del sistema.

    # ── pdf2image / Poppler ──────────────────────────────────────────────────
    # DPI para la conversión PDF → imagen (mayor DPI = mejor calidad, más lento)
    "dpi": 300,

    # Ruta base de los binarios de Poppler (requeridos por pdf2image en Windows)
    "poppler_path": obtener_ruta_poppler(),

    # ── Preprocesamiento de Imagen ───────────────────────────────────────────
    # Método de umbralización: "otsu" o "adaptativo"
    "metodo_umbral": "otsu",

    # Factor de escala para redimensionar imágenes antes del OCR (1.0 = sin cambio)
    "escala_imagen": 1.5,

    # ── Campos de Salida (orden de columnas en el Excel) ─────────────────────
    "campos_salida": [
        "archivo",
        "grupo",
        "fecha",
        "ruta",
        "estado",
        "ciudad",
        "factura",
        "reclamo",
        "empresa",
        "rif",
        "error",
    ],

    # ── Exportación Excel ────────────────────────────────────────────────────
    "nombre_hoja": "Recolectas",

    # Color de cabecera en el Excel (formato ARGB hex)
    "color_cabecera": "FF1F3A5F",  # Azul oscuro

    # ── Textos a Ignorar (Direcciones propias, etc.) ─────────────────────────
    "textos_a_ignorar": [
        "Av. Michelena c/c Calle norte-Sur, Nro 05, Zona Ind Municipal Norte Nro 91-100, Valencia, Edo Carabobo",
        "Av. Michelena c/c Calle norte-Sur",
        "Zona Ind Municipal Norte",
    ],
}
