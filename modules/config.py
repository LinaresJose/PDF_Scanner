"""
config.py — Configuración centralizada del extractor.

Modifica este archivo para adaptar el programa a tu entorno y documentos.
"""

import os

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

    # Ruta a los binarios de Poppler (necesario en Windows)
    # Instalado localmente en la carpeta del proyecto (no requiere admin)
    "poppler_path": r"C:\Users\jlinares\Desktop\Escaner de Recolectas\poppler\Library\bin",

    # ── Preprocesamiento de Imagen ───────────────────────────────────────────
    # Método de umbralización: "otsu" o "adaptativo"
    "metodo_umbral": "otsu",

    # Factor de escala para redimensionar imágenes antes del OCR (1.0 = sin cambio)
    "escala_imagen": 1.5,

    # ── Campos de Salida (orden de columnas en el Excel) ─────────────────────
    "campos_salida": [
        "archivo",
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
}
