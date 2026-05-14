"""
ocr_engine.py — Motor OCR local usando la API nativa de Windows (WinRT).

Totalmente offline, no requiere Tesseract ni APIs externas.
Utiliza el motor de reconocimiento óptico de caracteres integrado en Windows 10/11.
"""

import asyncio
import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

# Intentar importar las librerías nativas de Windows
try:
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    WINRT_AVAILABLE = True
except ImportError:
    WINRT_AVAILABLE = False


async def _extract_text_async(imagen: Image.Image) -> str:
    """Función asíncrona interna para interactuar con la API nativa de Windows."""
    if not WINRT_AVAILABLE:
        raise ImportError(
            "Faltan las dependencias de Windows OCR. Ejecuta:\n"
            "pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage.Streams"
        )

    # El OCR de Windows requiere formatos soportados (PNG/BMP) y preferiblemente RGBA
    if imagen.mode != "RGBA":
        imagen = imagen.convert("RGBA")
    
    # Extraer bytes de la imagen en formato PNG a memoria
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    
    # Crear un stream de memoria estilo Windows
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    
    # Escribir los bytes. write_bytes recibe un buffer u objeto similar a bytes
    writer.write_bytes(list(img_bytes))
    await writer.store_async()
    stream.seek(0)
    
    # Decodificar el stream a un SoftwareBitmap compatible con WinRT
    decoder = await BitmapDecoder.create_async(stream)
    software_bitmap = await decoder.get_software_bitmap_async()
    
    # Crear el motor OCR. Utiliza automáticamente el idioma preferido del usuario del sistema
    engine = OcrEngine.try_create_from_user_profile_languages()
    if not engine:
        raise RuntimeError(
            "No se pudo iniciar el motor OCR de Windows. Es posible que el idioma "
            "necesario no esté instalado en la configuración de Windows."
        )
    
    # Reconocer texto
    resultado = await engine.recognize_async(software_bitmap)
    return resultado.text


def extraer_texto(imagen: Image.Image) -> str:
    """
    Aplica OCR a una imagen PIL usando el motor nativo de Windows y retorna el texto.

    Args:
        imagen: Imagen PIL preprocesada (idealmente binarizada).

    Returns:
        Texto extraído como string. Retorna cadena vacía en caso de error.
    """
    if not WINRT_AVAILABLE:
        logger.error("Dependencias WinRT no encontradas. Instala los paquetes winrt-*.")
        return ""

    try:
        # Obtener o crear un loop de eventos asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        texto = loop.run_until_complete(_extract_text_async(imagen))
        return texto.strip()

    except Exception as exc:
        logger.error(f"Error en OCR Nativo de Windows: {exc}")
        return ""
