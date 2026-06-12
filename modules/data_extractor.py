"""
data_extractor.py — Extracción de campos mediante expresiones regulares.

Busca en el texto OCR los siguientes datos:
  - Fecha          : DD/MM/AAAA, DD-MM-AAAA, etc.
  - Ruta           : Número de 2 dígitos a la derecha de la etiqueta.
  - Estado         : Etiqueta "Estado:" seguida de texto.
  - Ciudad         : Etiqueta "Ciudad:" seguida de texto.
  - Factura        : Número de control o correlativo.
  - Reclamo        : Código que empieza con 'N' seguido de números (derecha).
  - RIF            : Patrón venezolano (V/J/G/E-XXXXXXXX-X).
  - Articulo       : Formato XX-XX-XXX debajo de la etiqueta "Articulo".
  - Vendedor       : Número de hasta 3 cifras a la derecha.
  - Cliente        : Número de varias cifras a la derecha.
"""

import re
import logging
from typing import Dict

from modules.geo_data import ESTADOS_VENEZUELA, CIUDADES_VENEZUELA, CIUDAD_A_RUTA
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

# Ruta: buscar a la derecha de la etiqueta (incluso en la siguiente línea) hasta encontrar un número de exactamente 2 dígitos
RE_RUTA = re.compile(
    r"RUTA\s*[:\-]?[\s\S]{0,80}?(\b\d{2}\b)",
    re.IGNORECASE,
)

# Estado: Buscar el texto después de "ESTADO:" (ignorando si repiten la palabra "ESTADO")
RE_ESTADO = re.compile(
    r"ESTADO\s*[:\-]?\s*(?:ESTADO\s+)?([A-ZÁÉÍÓÚÑ\s]{3,40}?)(?=\s*(?:CIUDAD|MUNICIPIO|FACTURA|FECHA|RUTA|RECLAMO|CLIENTE|RIF|$|\n))",
    re.IGNORECASE,
)

# Ciudad / Municipio: Buscar el texto después de "CIUDAD:"
RE_CIUDAD = re.compile(
    r"(?:CIUDAD|MUNICIPIO|EMPRESA)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ\s]{3,40}?)(?=\s*(?:ESTADO|FACTURA|FECHA|RUTA|RECLAMO|CLIENTE|RIF|$|\n))",
    re.IGNORECASE,
)

# Factura: Buscar número de 5 a 15 dígitos después de la etiqueta (permitiendo texto basura)
RE_FACTURA = re.compile(
    r"(?:FACTURA|CONTROL|CORRELATIVO)\s*[:\-#°N°\s]*[A-Z\s:]*?(\d{5,15})",
    re.IGNORECASE,
)

# Reclamo: buscar a la derecha (o abajo) hasta encontrar valor que empiece con 'N' seguido de hasta 10 números
RE_RECLAMO = re.compile(
    r"(?:RECLAMO|RECLAMACI[OÓ]N)[\s\S]{0,120}?\b(N\s*-?\s*\d{1,10})\b",
    re.IGNORECASE,
)

# Artículo: formato XX-XX-XXX debajo de la etiqueta "Articulo" (en la siguiente línea)
RE_ARTICULO = re.compile(
    r"ART[IÍ]CULO[S]?\s*[:\-]?\s*(?:[^\n]*\n)?\s*(\d{2}-\d{2}-\d{3}(?:-\d+)?)",
    re.IGNORECASE,
)
# Fallback: buscar el patrón XX-XX-XXX directamente en el texto
RE_ARTICULO_DIRECTO = re.compile(
    r"\b(\d{2}-\d{2}-\d{3}(?:-\d+)?)\b",
)

# Vendedor: buscar a la derecha de la etiqueta, número de hasta 3 cifras
RE_VENDEDOR = re.compile(
    r"VENDEDOR\s*[:\-]?\s*(?:[^\n\d]*?)(\b\d{1,3}\b)",
    re.IGNORECASE,
)

# Cliente: buscar a la derecha de la etiqueta, número de varias cifras (4+)
RE_CLIENTE = re.compile(
    r"CLIENTE\s*[:\-]?\s*(?:[^\n\d]*?)(\b\d{4,}\b)",
    re.IGNORECASE,
)

# Empresa / Cliente (para compatibilidad)
RE_EMPRESA_ETIQUETA = re.compile(
    r"(?:RAZ[OÓ]N\s*SOCIAL|PROVEEDOR|NOMBRE)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ0-9\s\.,&]{3,60})(?=\s*(?:RIF|DIRECCI[OÓ]N|TEL[EÉ]F|FECHA|$))",
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


def _buscar_articulo(texto: str) -> str:
    """Busca el artículo con formato XX-XX-XXX debajo de la etiqueta 'Articulo',
    o directamente en el texto si no hay etiqueta."""
    # Primero buscar junto a la etiqueta (en misma línea o siguiente)
    match = RE_ARTICULO.search(texto)
    if match:
        return _limpiar(match.group(1))
    # Fallback: buscar el patrón XX-XX-XXX en cualquier parte del texto
    match = RE_ARTICULO_DIRECTO.search(texto)
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
    estado_val = _buscar_primero(RE_ESTADO, texto)
    if estado_val:
        estado_validado = _buscar_en_lista(estado_val, ESTADOS_VENEZUELA)
        estado_val = estado_validado if estado_validado else ""
        
    if not estado_val:
        estado_val = _buscar_en_lista(texto_geo, ESTADOS_VENEZUELA)
        
    estado_final = estado_val.upper() if estado_val else ""

    # ── CIUDAD ──
    ciudad_val = _buscar_primero(RE_CIUDAD, texto)
    if ciudad_val:
        ciudad_validada = _buscar_en_lista(ciudad_val, CIUDADES_VENEZUELA)
        ciudad_val = ciudad_validada if ciudad_validada else ""
        
    if not ciudad_val:
        ciudad_val = _buscar_en_lista(texto_geo, CIUDADES_VENEZUELA)
        
    ciudad_final = ciudad_val.upper() if ciudad_val else ""
    if ciudad_final and any(tag in ciudad_final for tag in ["CONDUCTOR", "EMPRESA"]):
        ciudad_final = ""

    # ── RUTA ASIGNADA ──
    ruta_asignada = CIUDAD_A_RUTA.get(ciudad_final, "") if ciudad_final else ""

    campos = {
        "grupo":         _buscar_primero(RE_GRUPO, texto, grupo=1),
        "fecha":         _buscar_primero(RE_FECHA, texto),
        "ruta":          _buscar_primero(RE_RUTA, texto),
        "estado":        estado_final,
        "ciudad":        ciudad_final,
        "ruta_asignada": ruta_asignada,
        "factura":       _buscar_primero(RE_FACTURA, texto),
        "reclamo":       _buscar_primero(RE_RECLAMO, texto),
        "articulo":      _buscar_articulo(texto),
        "vendedor":      _buscar_primero(RE_VENDEDOR, texto),
        "cliente":       _buscar_primero(RE_CLIENTE, texto),
    }

    # Log informativo de campos encontrados vs vacíos
    encontrados = [k for k, v in campos.items() if v]
    vacios = [k for k, v in campos.items() if not v]
    if encontrados:
        logger.debug(f"  Campos encontrados: {', '.join(encontrados)}")
    if vacios:
        logger.debug(f"  Campos no encontrados: {', '.join(vacios)}")

    return campos
