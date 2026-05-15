@echo off
echo =======================================================
echo   CONSTRUCTOR DE EJECUTABLE - ESCANER DE RECOLECTAS
echo =======================================================
echo.

echo [1/3] Instalando PyInstaller si es necesario...
pip install pyinstaller

echo.
echo [2/3] Limpiando compilaciones anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist\EscanerRecolectas.exe" del /q "dist\EscanerRecolectas.exe"

echo.
echo [3/3] Iniciando empaquetado con PyInstaller...
echo Esto tomara un par de minutos, por favor espera.
echo Se esta empaquetando Poppler dentro del ejecutable...

pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name "EscanerRecolectas" ^
    --add-binary "C:\poppler\poppler-26.02.0\Library\bin;poppler\bin" ^
    --hidden-import winrt.windows.media.ocr ^
    --hidden-import winrt.windows.graphics.imaging ^
    --hidden-import winrt.windows.storage.streams ^
    --exclude-module tzdata ^
    --clean ^
    gui.pyw

echo.
if exist "dist\EscanerRecolectas.exe" (
    echo =======================================================
    echo   ¡EXITO!
    echo   El programa portable se ha generado en la carpeta:
    echo   dist\EscanerRecolectas.exe
    echo =======================================================
) else (
    echo =======================================================
    echo   ERROR: Fallo la generacion del ejecutable.
    echo   Revisa los mensajes de error arriba.
    echo =======================================================
)
pause
