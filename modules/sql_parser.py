"""
sql_parser.py — Módulo para parsear el archivo Facturas_Verificar.sql
"""

import re
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)

def cargar_facturas_a_verificar(ruta_sql: Path) -> Set[str]:
    """
    Lee un archivo .sql (ej. volcado de phpMyAdmin) y extrae los números de factura
    que se encuentran dentro de las sentencias INSERT INTO.
    
    Busca patrones como: (1234567) o ('1234567')
    
    Returns:
        set: Conjunto de números de factura como cadenas de texto para búsqueda rápida.
    """
    facturas = set()
    if not ruta_sql or not Path(ruta_sql).exists():
        logger.warning(f"Archivo no encontrado en: {ruta_sql}")
        return facturas

    ruta = Path(ruta_sql)
    ext = ruta.suffix.lower()

    try:
        if ext in ['.xlsx', '.xls']:
            import pandas as pd
            # Cargar todas las hojas del Excel
            df_dict = pd.read_excel(ruta, sheet_name=None)
            for nombre_hoja, df in df_dict.items():
                for col in df.columns:
                    for val in df[col].dropna():
                        # Extraer solo secuencias numéricas (ej. facturas) y descartar números muy cortos como cantidades o fechas sueltas
                        numeros = re.findall(r"\d+", str(val))
                        for num in numeros:
                            if len(num) >= 5:  # Las facturas suelen tener al menos 5 dígitos
                                facturas.add(num.strip())
            logger.info(f"Cargadas {len(facturas)} facturas a verificar desde archivo Excel: {ruta.name}")

        elif ext == '.sql':
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                contenido = f.read()
                
            # La regex captura los números que están dentro de paréntesis, ignorando comillas opcionales
            patron_valores = re.compile(r"\(\s*['\"]?(\d+)['\"]?\s*\)")
            
            # Encontramos todos los bloques que comiencen con INSERT INTO
            bloques_insert = re.finditer(r"INSERT INTO.*?VALUES\s*(.*?)(?:;|$)", contenido, re.IGNORECASE | re.DOTALL)
            
            for bloque in bloques_insert:
                valores_str = bloque.group(1)
                # Extraer cada número dentro del bloque
                numeros = patron_valores.findall(valores_str)
                for num in numeros:
                    facturas.add(num.strip())
                    
            logger.info(f"Cargadas {len(facturas)} facturas a verificar desde archivo SQL: {ruta.name}")
        else:
            logger.warning(f"Formato no soportado para lista de facturas: {ext}")
            
    except Exception as e:
        logger.error(f"Error al leer archivo {ruta}: {e}")
        
    return facturas
