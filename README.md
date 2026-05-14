# 📄 Escaner de Recolectas

Programa Python para **extraer datos de PDFs escaneados** y exportarlos a Excel.  
Funciona **100% offline** — sin APIs externas, sin nube.

---

## 🗂️ Estructura del Proyecto

```
Escaner de Recolectas/
│
├── extractor.py                ← Programa principal (punto de entrada)
├── requirements.txt            ← Dependencias Python
├── instalar_dependencias.bat   ← Instalador automático (Windows)
├── ejecutar.bat                ← Lanzador con doble clic
├── extractor.log               ← Log del último proceso (se genera al ejecutar)
│
├── pdfs/                       ← 📁 COLOCA AQUÍ TUS ARCHIVOS PDF
│
├── recolectas_extraidas.xlsx   ← 📊 ARCHIVO DE SALIDA (se genera al ejecutar)
│
└── modules/
    ├── __init__.py
    ├── config.py               ← ⚙️ CONFIGURACIÓN (rutas, DPI, idioma OCR)
    ├── pdf_processor.py        ← Convierte PDF → Imágenes (pdf2image)
    ├── image_processor.py      ← Preprocesamiento con OpenCV (grises + umbral)
    ├── ocr_engine.py           ← Extracción de texto (Tesseract OCR)
    ├── data_extractor.py       ← Búsqueda de patrones con Regex
    └── excel_exporter.py       ← Exportación a .xlsx (openpyxl)
```

---

## 🚀 Instalación Paso a Paso

### Paso 1: Instalar Python 3.9+
Descarga desde [python.org](https://www.python.org/downloads/).  
> ⚠️ Marca **"Add Python to PATH"** durante la instalación.

---

### Paso 2: Motor OCR Nativo de Windows (¡Ya lo tienes!)
El programa utiliza el motor de Inteligencia Artificial OCR nativo integrado en Windows 10/11. No necesitas descargar ni instalar nada extra para el reconocimiento de texto, funciona de forma 100% offline aprovechando la tecnología de tu propio sistema operativo.

---

### Paso 3: Instalar Poppler (para leer PDFs)
1. Descarga la última versión desde:  
   [https://github.com/oschwartz10612/poppler-windows/releases](https://github.com/oschwartz10612/poppler-windows/releases)
2. Extrae el ZIP en una carpeta, por ejemplo: `C:\poppler`
3. Abre `modules\config.py` y configura la ruta:
   ```python
   "poppler_path": r"C:\poppler\Library\bin",
   ```

---

### Paso 4: Instalar librerías Python
Haz doble clic en **`instalar_dependencias.bat`**  
*(o ejecuta en terminal: `pip install -r requirements.txt`)*

---

## ⚙️ Configuración (`modules/config.py`)

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `carpeta_pdfs` | Carpeta con los PDFs | `./pdfs/` |
| `archivo_excel` | Archivo de salida | `./recolectas_extraidas.xlsx` |
| `dpi` | Resolución PDF→imagen | `300` |
| `poppler_path` | Ruta a Poppler | `None` (usa PATH) |
| `metodo_umbral` | `"otsu"` o `"adaptativo"` | `"otsu"` |
| `escala_imagen` | Factor de zoom antes del OCR | `1.5` |

---

## ▶️ Uso

1. Copia tus archivos PDF en la carpeta **`pdfs/`**
2. Ejecuta el programa:
   - **Doble clic** en `ejecutar.bat`  
   - **O en terminal**: `python extractor.py`
3. Al finalizar, abre **`recolectas_extraidas.xlsx`**

---

## 📊 Datos Extraídos

| Campo | Patrón buscado |
|---|---|
| **Fecha** | `DD/MM/AAAA`, `DD-MM-AAAA`, etc. |
| **Ruta** | Texto tras la palabra "Ruta:" |
| **Estado** | Texto tras la palabra "Estado:" |
| **Ciudad** | Texto tras "Ciudad:" o "Municipio:" |
| **Factura** | Número de control, correlativo |
| **Reclamo** | Identificador numérico/alfanumérico |
| **Empresa** | Nombre con etiqueta o sufijo (C.A., S.A., etc.) |
| **RIF** | Formato venezolano `V-12345678-9` |

---

## 🔧 Solución de Problemas

**`Dependencias WinRT no encontradas`**  
→ Asegúrate de haber ejecutado el archivo `instalar_dependencias.bat` para instalar `winrt-Windows.Media.Ocr`.

**`PDFInfoNotInstalledError`**  
→ Poppler no encontrado. Configura `poppler_path` en `config.py`.

**OCR con texto incorrecto / caracteres extraños**  
→ Reduce el `escala_imagen` a `1.0` o cambia `metodo_umbral` a `"adaptativo"`.

**Campos vacíos en el Excel**  
→ El documento puede no tener las palabras clave (Factura:, RIF:, etc.). Revisa `data_extractor.py` para ajustar los patrones Regex.

---

## 📋 Privacidad

✅ **Sin conexión a internet requerida.**  
✅ **Sin APIs de OCR en la nube (Google Vision, AWS Textract, etc.).**  
✅ Todo el procesamiento ocurre localmente en tu máquina.
