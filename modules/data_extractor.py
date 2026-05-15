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

from modules.geo_data import ESTADOS_VENEZUELA, CIUDADES_VENEZUELA
from modules.config import CONFIG

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Patrones Regex compilados (compilar una sola vez mejora el rendimiento)
# ─────────────────────────────────────────────────────────────────────────────

# Grupo: Febeca, Sillaca, Beval
RE_GRUPO = re.compile(r"\b(Febeca|Sillaca|Beval)\b", re.IGNORECASE)

# Fecha: DD/MM/AAAA
RE_FECHA = re.compile(
    r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.](?:\d{4}|\d{2}))\b",
    re.IGNORECASE,
)

# Ruta
RE_RUTA = re.compile(
    r"RUTA\s*[:\-]?\s*([A-Z0-9ÁÉÍÓÚÑ\s]{2,40})",
    re.IGNORECASE,
)

# Estado: Buscar la palabra después de "ESTADO:" (ignorando posibles ruidos como Factura:)
RE_ESTADO = re.compile(
    r"ESTADO\s*[:\-]?\s*(?:FACTURA\s*[:\-]?\s*)?ESTADO\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ]{3,20})|ESTADO\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ]{3,20})",
    re.IGNORECASE,
)

# Ciudad / Municipio: Buscar después de etiquetas CIUDAD o EMPRESA (a veces el OCR las confunde)
RE_CIUDAD = re.compile(
    r"(?:CIUDAD|MUNICIPIO|EMPRESA)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ]{3,25})",
    re.IGNORECASE,
)

# Factura: Buscar número de 5 a 15 dígitos después de la etiqueta (permitiendo texto basura)
RE_FACTURA = re.compile(
    r"(?:FACTURA|CONTROL|CORRELATIVO)\s*[:\-#°N°\s]*[A-Z\s:]*?(\d{5,15})",
    re.IGNORECASE,
)

# Reclamo
RE_RECLAMO = re.compile(
    r"(?:RECLAMO|RECLAMACI[OÓ]N)\s*[:\-#°N°\s]*([A-Z0-9\-]{4,25})",
    re.IGNORECASE,
)

# Empresa / Cliente
RE_EMPRESA_ETIQUETA = re.compile(
    r"(?:CLIENTE|RAZ[OÓ]N\s*SOCIAL|PROVEEDOR|NOMBRE)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ0-9\s\.,&]{3,60})(?=\s*(?:RIF|DIRECCI[OÓ]N|TEL[EÉ]F|FECHA|$))",
    re.IGNORECASE,
)
RE_EMPRESA_SUFIJO = re.compile(
    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&]{3,60}(?:C\.A\.|S\.A\.|R\.L\.|C\.R\.L\.|S\.R\.L\.|COMPAÑIA|EMPRESA))",
    re.IGNORECASE,
)

# RIF venezolano
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
def _buscar_en_lista(texto: str, lista: list) -> str:
    """Busca palabras exactas de una lista en el texto y retorna la primera encontrada,
    incluyendo un número opcional que le siga SIEMPRE QUE sea menor a 9."""
    texto_limpio = texto.upper()
    for item in lista:
        # Buscar el item y opcionalmente un número (1 o más dígitos)
        patron = re.compile(rf"\b{re.escape(item.upper())}\s*(\d+)?\b")
        match = patron.search(texto_limpio)
        if match:
            num_str = match.group(1)
            if num_str:
                try:
                    # Solo incluir el número si su valor numérico es menor a 9
                    if int(num_str) < 9:
                        return f"{item} {num_str}"
                except ValueError:
                    pass
            return item
    return ""


# ─────────────────────────────────────────────────────────────────────────────
def extraer_campos(texto: str) -> Dict[str, str]:
    """
    Extrae todos los campos relevantes del texto OCR.
    """
    # Normalizar texto
    texto = re.sub(r"\t", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # Crear una versión del texto para búsqueda geográfica (sin direcciones propias)
    texto_geo = texto
    for ignorar in CONFIG.get("textos_a_ignorar", []):
        # Usar escape para caracteres especiales y reemplazar por espacios
        texto_geo = re.sub(re.escape(ignorar), " ", texto_geo, flags=re.IGNORECASE)

    # ── ESTADO ──
    # Intento 1: Por etiqueta (sobre el texto completo)
    estado_match = RE_ESTADO.search(texto)
    estado_val = ""
    if estado_match:
        estado_val = estado_match.group(1) or estado_match.group(2) or ""
        estado_val = _limpiar(estado_val)
    
    # Intento 2: Búsqueda por lista blanca (sobre el texto filtrado)
    estado_desde_lista = _buscar_en_lista(texto_geo, ESTADOS_VENEZUELA)
    estado_final = estado_desde_lista if estado_desde_lista else estado_val

    # ── CIUDAD ──
    # Intento 1: Por etiqueta
    ciudad_val = _buscar_primero(RE_CIUDAD, texto)
    if ciudad_val and any(tag in ciudad_val.upper() for tag in ["CONDUCTOR", "EMPRESA"]):
        ciudad_val = ""
    
    # Intento 2: Búsqueda por lista blanca (sobre el texto filtrado)
    ciudad_desde_lista = _buscar_en_lista(texto_geo, CIUDADES_VENEZUELA)
    ciudad_final = ciudad_desde_lista if ciudad_desde_lista else ciudad_val

    campos = {
        "grupo":   _buscar_primero(RE_GRUPO, texto, grupo=1),
        "fecha":   _buscar_primero(RE_FECHA, texto),
        "ruta":    _buscar_primero(RE_RUTA, texto),
        "estado":  estado_final,
        "ciudad":  ciudad_final,
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
