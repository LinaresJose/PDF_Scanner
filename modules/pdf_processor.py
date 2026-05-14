"""
pdf_processor.py — Convierte páginas de un PDF en imágenes PIL.

Usa pdf2image (que internamente utiliza Poppler) para la conversión.
"""

import logging
from pathlib import Path
from typing import List

from PIL import Image

logger = logging.getLogger(__name__)


def convertir_pdf_a_imagenes(ruta_pdf: Path) -> List[Image.Image]:
    """
    Convierte todas las páginas de un PDF en objetos PIL.Image.

    Args:
        ruta_pdf: Ruta completa al archivo PDF.

    Returns:
        Lista de imágenes PIL, una por página.

    Raises:
        ImportError: Si pdf2image no está instalado.
        Exception:   Si el PDF no se puede leer o convertir.
    """
    try:
        from pdf2image import convert_from_path
        from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
    except ImportError:
        raise ImportError(
            "pdf2image no está instalado. Ejecuta: pip install pdf2image"
        )

    # Importar config aquí para evitar importaciones circulares
    from modules.config import CONFIG

    poppler_path = CONFIG.get("poppler_path")
    dpi = CONFIG.get("dpi", 300)

    try:
        imagenes = convert_from_path(
            str(ruta_pdf),
            dpi=dpi,
            poppler_path=poppler_path,
            thread_count=2,
            grayscale=False,  # El preprocesamiento lo hace image_processor
        )
        logger.debug(
            f"PDF '{ruta_pdf.name}' → {len(imagenes)} página(s) @ {dpi} DPI"
        )
        return imagenes

    except PDFInfoNotInstalledError:
        raise RuntimeError(
            "Poppler no encontrado. Instálalo y configura 'poppler_path' en config.py.\n"
            "Descarga: https://github.com/oschwartz10612/poppler-windows/releases"
        )
    except PDFPageCountError as exc:
        raise RuntimeError(f"PDF dañado o protegido con contraseña: {exc}")
    except Exception as exc:
        raise RuntimeError(f"Error al convertir PDF: {exc}")
