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
from datetime import datetime

# ── Módulos propios ──────────────────────────────────────────────────────────
from modules.pdf_processor import convertir_pdf_a_imagenes, extraer_paginas_a_pdf
from modules.image_processor import preprocesar_imagen
from modules.ocr_engine import extraer_texto
from modules.data_extractor import extraer_campos
from modules.excel_exporter import exportar_a_excel
from modules.config import CONFIG
from modules.sql_parser import cargar_facturas_a_verificar

# ── Dependencias de terceros ─────────────────────────────────────────────────
try:
    import pandas as pd
    from tqdm import tqdm
except ImportError as e:
    print(f"[ERROR] Dependencia faltante: {e}")
    print("Ejecuta: pip install -r requirements.txt")
    sys.exit(1)

# Obtener ruta base persistente para logs
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.resolve()

# ── Configuración del logger ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "extractor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
def procesar_pdf(ruta_pdf: Path, facturas_sql: set, archivo_salida: Path, progress_callback=None, nombre_mostrar: str = None) -> list:
    """
    Pipeline completo para un único archivo PDF por página.
    Returns:
        list de dicts con los campos extraídos por página.
    """
    nombre_archivo = nombre_mostrar if nombre_mostrar else ruta_pdf.name
    logger.info(f"  Procesando: {nombre_archivo}")
    registros_pdf = []

    campos_vacios = {campo: "" for campo in CONFIG["campos_salida"]}
    campos_vacios["archivo"] = nombre_archivo
    campos_vacios["error"] = ""

    try:
        # Paso 1: PDF → Imágenes
        imagenes = convertir_pdf_a_imagenes(ruta_pdf)
        if not imagenes:
            raise ValueError("No se pudieron extraer imágenes del PDF.")

        paginas_coincidentes = []

        # Procesar página por página
        for idx, imagen in enumerate(imagenes):
            logger.debug(f"    Página {idx + 1}/{len(imagenes)}")
            
            # Sub-estado 1: Preprocesamiento de Imagen
            if progress_callback:
                progress_callback(
                    progreso_pagina={
                        "actual": idx + 1,
                        "total": len(imagenes),
                        "archivo": nombre_archivo,
                        "sub_estado": "Preprocesando imagen (OpenCV)...",
                        "porcentaje_interno": 20
                    }
                )
                
            imagen_procesada = preprocesar_imagen(imagen)
            
            # Sub-estado 2: Ejecución de OCR
            if progress_callback:
                progress_callback(
                    progreso_pagina={
                        "actual": idx + 1,
                        "total": len(imagenes),
                        "archivo": nombre_archivo,
                        "sub_estado": "Ejecutando OCR nativo de Windows...",
                        "porcentaje_interno": 60
                    }
                )
                
            texto_pagina = extraer_texto(imagen_procesada)

            # Sub-estado 3: Extracción de campos
            if progress_callback:
                progress_callback(
                    progreso_pagina={
                        "actual": idx + 1,
                        "total": len(imagenes),
                        "archivo": nombre_archivo,
                        "sub_estado": "Analizando campos y Regex...",
                        "porcentaje_interno": 85
                    }
                )
                
            campos = extraer_campos(texto_pagina)
            campos["archivo"] = f"{nombre_archivo} (Pág {idx+1})"
            campos["pagina"] = idx + 1
            campos["fecha_escaneo"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            campos["error"] = ""
            campos["coincidencia"] = ""

            # Verificación SQL
            factura_extraida = campos.get("factura", "")
            if factura_extraida and facturas_sql and factura_extraida in facturas_sql:
                campos["coincidencia"] = "coincidencia"
                paginas_coincidentes.append(idx)
                # Notificar a la interfaz a través del progress_callback
                if progress_callback:
                    progress_callback(match={"archivo": nombre_archivo, "factura": factura_extraida, "pagina": idx + 1})

            registros_pdf.append(campos)
            
            # Sub-estado 4: Completado de página
            if progress_callback:
                progress_callback(
                    progreso_pagina={
                        "actual": idx + 1,
                        "total": len(imagenes),
                        "archivo": nombre_archivo,
                        "sub_estado": "Página completada",
                        "porcentaje_interno": 100
                    }
                )

        # Si hubo coincidencias, separar esas páginas en un nuevo PDF
        if paginas_coincidentes:
            nombre_coincidencias = f"{ruta_pdf.stem}_coincidencias.pdf"
            ruta_destino = archivo_salida.parent / nombre_coincidencias
            extraer_paginas_a_pdf(ruta_pdf, ruta_destino, paginas_coincidentes)

        return registros_pdf

    except Exception as exc:
        logger.error(f"  [FALLO] {nombre_archivo}: {exc}")
        campos_vacios["error"] = str(exc)
        return [campos_vacios]


# ─────────────────────────────────────────────────────────────────────────────
def main(carpeta_entrada=None, archivo_salida=None, ruta_sql=None, progress_callback=None):
    """Punto de entrada principal del programa."""

    carpeta_entrada = Path(carpeta_entrada) if carpeta_entrada else Path(CONFIG["carpeta_pdfs"])
    archivo_salida = Path(archivo_salida) if archivo_salida else Path(CONFIG["archivo_excel"])
    
    # Cargar base de datos SQL
    ruta_sql = Path(ruta_sql) if ruta_sql else (carpeta_entrada.parent / "Facturas_Verificar.sql")
    facturas_sql = cargar_facturas_a_verificar(ruta_sql)

    # ── Validaciones iniciales ───────────────────────────────────────────────
    if not carpeta_entrada.exists():
        logger.error(f"La carpeta de entrada no existe: {carpeta_entrada}")
        return

    pdfs = sorted(carpeta_entrada.rglob("*.pdf"))
    if not pdfs:
        logger.warning(f"No se encontraron archivos PDF en: {carpeta_entrada}")
        return

    logger.info("=" * 60)
    logger.info("  ESCANER DE RECOLECTAS - Inicio del procesamiento")
    logger.info("=" * 60)
    logger.info(f"  Carpeta entrada : {carpeta_entrada.resolve()}")
    logger.info(f"  Archivo salida  : {archivo_salida.resolve()}")
    logger.info(f"  Archivo SQL     : {ruta_sql.resolve() if ruta_sql.exists() else 'No encontrado'}")
    logger.info(f"  PDFs encontrados: {len(pdfs)}")
    logger.info("=" * 60)

    # ── Procesamiento ────────────────────────────────────────────────────────
    registros = []
    total_pdfs = len(pdfs)
    
    if progress_callback:
        # Modo GUI: usar el callback en lugar de tqdm
        for idx, ruta_pdf in enumerate(pdfs, 1):
            nombre_mostrar = str(ruta_pdf.relative_to(carpeta_entrada))
            progress_callback(progreso={"actual": idx, "total": total_pdfs, "archivo": nombre_mostrar})
            resultados = procesar_pdf(ruta_pdf, facturas_sql, archivo_salida, progress_callback, nombre_mostrar)
            registros.extend(resultados)
    else:
        # Modo CLI: usar tqdm
        with tqdm(
            total=total_pdfs,
            desc="Procesando PDFs",
            unit="archivo",
            colour="cyan",
            bar_format="{l_bar}{bar:30}{r_bar}",
        ) as barra:
            for ruta_pdf in pdfs:
                nombre_mostrar = str(ruta_pdf.relative_to(carpeta_entrada))
                resultados = procesar_pdf(ruta_pdf, facturas_sql, archivo_salida, progress_callback=None, nombre_mostrar=nombre_mostrar)
                registros.extend(resultados)
                barra.update(1)
                barra.set_postfix({"último": nombre_mostrar[:20]})

    # ── Exportar a Excel ─────────────────────────────────────────────────────
    df = pd.DataFrame(registros)
    exportar_a_excel(df, archivo_salida)

    # ── Resumen final ────────────────────────────────────────────────────────
    exitosos = df[df["error"] == ""].shape[0]
    fallidos = df[df["error"] != ""].shape[0]

    logger.info("=" * 60)
    logger.info("  PROCESAMIENTO COMPLETADO")
    logger.info(f"  [OK] Exitosos : {exitosos}")
    logger.info(f"  [XX] Con error: {fallidos}")
    logger.info(f"  Archivo generado: {archivo_salida.resolve()}")
    logger.info("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
