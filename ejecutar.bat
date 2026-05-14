@echo off
REM =========================================================
REM  ESCANER DE RECOLECTAS — Lanzador del programa
REM  Doble clic para procesar todos los PDFs en /pdfs/
REM =========================================================
cd /d "%~dp0"
echo Iniciando Escaner de Recolectas...
python extractor.py
echo.
echo Proceso finalizado. Revisa el archivo recolectas_extraidas.xlsx
pause
