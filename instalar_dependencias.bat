@echo off
REM =========================================================
REM  ESCANER DE RECOLECTAS — Instalador de dependencias
REM  Doble clic para instalar todo automáticamente.
REM =========================================================

echo.
echo =====================================================
echo   ESCANER DE RECOLECTAS - Instalacion de Librerias
echo =====================================================
echo.

REM Verificar que Python esté instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.9+ desde:
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python encontrado.
echo.

REM Actualizar pip
echo [1/3] Actualizando pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip actualizado.
echo.

REM Instalar dependencias
echo [2/3] Instalando librerias Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo al instalar alguna libreria. Revisa el mensaje de error.
    pause
    exit /b 1
)
echo [OK] Librerias instaladas correctamente.
echo.

REM Recordatorio de herramientas externas
echo [3/3] IMPORTANTE - Herramientas externas requeridas:
echo.
echo   1. TESSERACT OCR (motor de reconocimiento de texto)
echo      Descarga: https://github.com/UB-Mannheim/tesseract/wiki
echo      Instala e incluye el paquete de idioma "Spanish".
echo      Ruta por defecto: C:\Program Files\Tesseract-OCR\tesseract.exe
echo.
echo   2. POPPLER (necesario para pdf2image)
echo      Descarga: https://github.com/oschwartz10612/poppler-windows/releases
echo      Extrae el ZIP y configura la ruta en modules\config.py
echo      (variable "poppler_path")
echo.
echo =====================================================
echo   Instalacion completada.
echo   Revisa modules\config.py para ajustar las rutas.
echo =====================================================
echo.
pause
