"""
data_extractor.py — Extracción de campos mediante expresiones regulares.

Busca en el texto OCR los siguientes datos:
  - Fecha          : DD/MM/AAAA, DD-MM-AAAA, etc.
  - Ruta           : Etiqueta "Ruta:" seguida de texto.
  - Estado         : Etiqueta "Estado:" seguida de texto.
  - Ciudad         : Etiqueta "Ciudad:" seguida de texto.
  - Factura        : Número de control o correlativo.
  - Reclamo        : Identificador numérico o alfanumérico.
  - Empresa        : Nombre de empresa (etiqueta o posición).
  - RIF            : Patrón venezolano (V/J/G/E-XXXXXXXX-X).
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Patrones Regex compilados (compilar una sola vez mejora el rendimiento)
# ─────────────────────────────────────────────────────────────────────────────

# Fecha: DD/MM/AAAA, DD-MM-AAAA, DD.MM.AAAA (con años de 2 o 4 dígitos)
RE_FECHA = re.compile(
    r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.](?:\d{4}|\d{2}))\b",
    re.IGNORECASE,
)

# Ruta: "Ruta:", "RUTA:", seguida de texto hasta fin de línea
RE_RUTA = re.compile(
    r"RUTA\s*[:\-]?\s*([^\n\r]{2,60})",
    re.IGNORECASE,
)

# Estado: "Estado:", "ESTADO:" seguida de texto
RE_ESTADO = re.compile(
    r"ESTADO\s*[:\-]?\s*([^\n\r]{2,50})",
    re.IGNORECASE,
)

# Ciudad / Municipio: "Ciudad:", "Municipio:"
RE_CIUDAD = re.compile(
    r"(?:CIUDAD|MUNICIPIO)\s*[:\-]?\s*([^\n\r]{2,50})",
    re.IGNORECASE,
)

# Factura: "Factura N°", "Factura #", "N° de Control", "No. Control"
# Captura el número (puede incluir guiones y letras)
RE_FACTURA = re.compile(
    r"(?:FACTURA|N[°o\.]\s*(?:DE\s*)?CONTROL|CORRELATIVO|COMPROBANTE)\s*[:\-#°N°\s]*([A-Z0-9\-]{3,25})",
    re.IGNORECASE,
)

# Reclamo: "Reclamo:", "No. Reclamo", seguido de identificador
RE_RECLAMO = re.compile(
    r"(?:RECLAMO|RECLAMACI[OÓ]N)\s*[:\-#°N°\s]*([A-Z0-9\-]{2,25})",
    re.IGNORECASE,
)

# Empresa: "Empresa:", "Razón Social:", "Proveedor:", o línea con S.A./C.A./R.L.
RE_EMPRESA_ETIQUETA = re.compile(
    r"(?:EMPRESA|RAZ[OÓ]N\s*SOCIAL|PROVEEDOR|CLIENTE|NOMBRE)\s*[:\-]?\s*([^\n\r]{3,80})",
    re.IGNORECASE,
)
RE_EMPRESA_SUFIJO = re.compile(
    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&]{3,60}(?:C\.A\.|S\.A\.|R\.L\.|C\.R\.L\.|S\.R\.L\.|COMPAÑIA|EMPRESA))",
    re.IGNORECASE,
)

# RIF venezolano: V/J/G/E/P-XXXXXXXX-X (con o sin guiones)
RE_RIF = re.compile(
    r"\b([VJGEP])\s*[\-]?\s*(\d{7,9})\s*[\-]?\s*(\d{1})\b",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
def _limpiar(valor: str) -> str:
    """Limpia espacios extra y caracteres no imprimibles de un valor."""
    if not valor:
        return ""
    # Eliminar caracteres de control, espacios múltiples
    valor = re.sub(r"[\x00-\x1F\x7F]", " ", valor)
    valor = re.sub(r"\s{2,}", " ", valor)
    return valor.strip(" .,;:-")


def _buscar_primero(patron: re.Pattern, texto: str, grupo: int = 1) -> str:
    """Retorna el primer match de un patrón, o cadena vacía."""
    match = patron.search(texto)
    if match:
        return _limpiar(match.group(grupo))
    return ""


def _buscar_rif(texto: str) -> str:
    """Formatea el RIF venezolano en el formato estándar X-XXXXXXXX-X."""
    match = RE_RIF.search(texto)
    if match:
        tipo = match.group(1).upper()
        numero = match.group(2).zfill(8)
        digito = match.group(3)
        return f"{tipo}-{numero}-{digito}"
    return ""


def _buscar_empresa(texto: str) -> str:
    """
    Busca el nombre de empresa primero por etiqueta, luego por sufijo legal.
    """
    # Intentar por etiqueta explícita
    valor = _buscar_primero(RE_EMPRESA_ETIQUETA, texto)
    if valor:
        return valor

    # Intentar por sufijo legal (C.A., S.A., etc.)
    match = RE_EMPRESA_SUFIJO.search(texto)
    if match:
        return _limpiar(match.group(1))

    return ""


# ─────────────────────────────────────────────────────────────────────────────
def extraer_campos(texto: str) -> Dict[str, str]:
    """
    Extrae todos los campos relevantes del texto OCR.

    Args:
        texto: Texto completo extraído por el motor OCR.

    Returns:
        Diccionario con los campos extraídos. Los no encontrados son "".
    """
    # Normalizar texto: reemplazar tabulaciones y múltiples saltos por uno
    texto = re.sub(r"\t", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    campos = {
        "fecha":   _buscar_primero(RE_FECHA, texto),
        "ruta":    _buscar_primero(RE_RUTA, texto),
        "estado":  _buscar_primero(RE_ESTADO, texto),
        "ciudad":  _buscar_primero(RE_CIUDAD, texto),
        "factura": _buscar_primero(RE_FACTURA, texto),
        "reclamo": _buscar_primero(RE_RECLAMO, texto),
        "empresa": _buscar_empresa(texto),
        "rif":     _buscar_rif(texto),
    }

    # Log informativo de campos encontrados vs vacíos
    encontrados = [k for k, v in campos.items() if v]
    vacios = [k for k, v in campos.items() if not v]
    if encontrados:
        logger.debug(f"  Campos encontrados: {', '.join(encontrados)}")
    if vacios:
        logger.debug(f"  Campos no encontrados: {', '.join(vacios)}")

    return campos
