"""
=============================================================================
  ESCANER DE RECOLECTAS - Extractor de Datos de PDFs Escaneados
=============================================================================
  Autor    : Desarrollado con Antigravity AI
  Versión  : 1.0.0
  Descripción:
    Procesa todos los PDFs de una carpeta, extrae datos relevantes mediante
    OCR (Tesseract) y exporta los resultados a un archivo Excel (.xlsx).
    100% offline - sin llamadas a APIs externas.
=============================================================================
"""

import os
import sys
import logging
from pathlib import Path

# ── Módulos propios ──────────────────────────────────────────────────────────
from modules.pdf_processor import convertir_pdf_a_imagenes
from modules.image_processor import preprocesar_imagen
from modules.ocr_engine import extraer_texto
from modules.data_extractor import extraer_campos
from modules.excel_exporter import exportar_a_excel
from modules.config import CONFIG

# ── Dependencias de terceros ─────────────────────────────────────────────────
try:
    import pandas as pd
    from tqdm import tqdm
except ImportError as e:
    print(f"[ERROR] Dependencia faltante: {e}")
    print("Ejecuta: pip install -r requirements.txt")
    sys.exit(1)

# ── Configuración del logger ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("extractor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
def procesar_pdf(ruta_pdf: Path) -> dict:
    """
    Pipeline completo para un único archivo PDF.

    Pasos:
      1. Convertir páginas del PDF en imágenes (pdf2image).
      2. Preprocesar cada imagen con OpenCV (gris + umbralización).
      3. Extraer texto con Tesseract OCR.
      4. Buscar patrones de datos relevantes con Regex.

    Returns:
        dict con los campos extraídos, o dict de valores vacíos en error.
    """
    nombre_archivo = ruta_pdf.name
    logger.info(f"  Procesando: {nombre_archivo}")

    campos_vacios = {campo: "" for campo in CONFIG["campos_salida"]}
    campos_vacios["archivo"] = nombre_archivo
    campos_vacios["error"] = ""

    try:
        # Paso 1: PDF → Imágenes
        imagenes = convertir_pdf_a_imagenes(ruta_pdf)
        if not imagenes:
            raise ValueError("No se pudieron extraer imágenes del PDF.")

        # Paso 2 & 3: Preprocesar + OCR por página
        texto_completo = ""
        for idx, imagen in enumerate(imagenes):
            logger.debug(f"    Página {idx + 1}/{len(imagenes)}")
            imagen_procesada = preprocesar_imagen(imagen)
            texto_pagina = extraer_texto(imagen_procesada)
            texto_completo += f"\n--- PÁGINA {idx + 1} ---\n{texto_pagina}"

        logger.debug(f"  Texto extraído ({len(texto_completo)} chars)")

        # Paso 4: Extracción de campos con Regex
        campos = extraer_campos(texto_completo)
        campos["archivo"] = nombre_archivo
        campos["error"] = ""
        return campos

    except Exception as exc:
        logger.error(f"  [FALLO] {nombre_archivo}: {exc}")
        campos_vacios["error"] = str(exc)
        return campos_vacios


# ─────────────────────────────────────────────────────────────────────────────
def main():
    """Punto de entrada principal del programa."""

    carpeta_entrada = Path(CONFIG["carpeta_pdfs"])
    archivo_salida = Path(CONFIG["archivo_excel"])

    # ── Validaciones iniciales ───────────────────────────────────────────────
    if not carpeta_entrada.exists():
        logger.error(f"La carpeta de entrada no existe: {carpeta_entrada}")
        sys.exit(1)

    pdfs = sorted(carpeta_entrada.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"No se encontraron archivos PDF en: {carpeta_entrada}")
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("  ESCANER DE RECOLECTAS - Inicio del procesamiento")
    logger.info("=" * 60)
    logger.info(f"  Carpeta entrada : {carpeta_entrada.resolve()}")
    logger.info(f"  Archivo salida  : {archivo_salida.resolve()}")
    logger.info(f"  PDFs encontrados: {len(pdfs)}")
    logger.info("=" * 60)

    # ── Procesamiento con barra de progreso ──────────────────────────────────
    registros = []
    with tqdm(
        total=len(pdfs),
        desc="Procesando PDFs",
        unit="archivo",
        colour="cyan",
        bar_format="{l_bar}{bar:30}{r_bar}",
    ) as barra:
        for ruta_pdf in pdfs:
            resultado = procesar_pdf(ruta_pdf)
            registros.append(resultado)
            barra.update(1)
            barra.set_postfix({"último": ruta_pdf.stem[:20]})

    # ── Exportar a Excel ─────────────────────────────────────────────────────
    df = pd.DataFrame(registros)
    exportar_a_excel(df, archivo_salida)

    # ── Resumen final ────────────────────────────────────────────────────────
    exitosos = df[df["error"] == ""].shape[0]
    fallidos = df[df["error"] != ""].shape[0]

    logger.info("=" * 60)
    logger.info("  PROCESAMIENTO COMPLETADO")
    logger.info(f"  ✔ Exitosos : {exitosos}")
    logger.info(f"  ✘ Con error: {fallidos}")
    logger.info(f"  Archivo generado: {archivo_salida.resolve()}")
    logger.info("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
