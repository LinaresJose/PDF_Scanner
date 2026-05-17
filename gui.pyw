import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from pathlib import Path
import sys
import json

# Importar el módulo principal de extracción
import extractor
from modules.config import CONFIG

# Obtener ruta de ejecución persistente (directorio del .exe o script)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.resolve()

SETTINGS_FILE = BASE_DIR / "settings.json"

class TextHandler(logging.Handler):
    """Handler para redirigir los logs de Python a un widget de texto de Tkinter"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

class ScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Escáner de Recolectas")
        self.root.geometry("600x550")
        self.root.minsize(500, 400)
        
        # Configurar estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')  # 'clam' suele verse más moderno y limpio en Windows
        
        # Variables
        self.carpeta_entrada = tk.StringVar()
        self.archivo_salida = tk.StringVar()
        self.archivo_sql = tk.StringVar()
        self.procesando = False
        
        self.cargar_configuracion()
        self.crear_interfaz()
        self.configurar_logs()

    def cargar_configuracion(self):
        # Cargar valores por defecto
        self.carpeta_entrada.set(CONFIG.get("carpeta_pdfs", ""))
        self.archivo_salida.set(CONFIG.get("archivo_excel", ""))
        self.archivo_sql.set(str(Path(CONFIG.get("carpeta_pdfs", "")).parent / "Facturas_Verificar.sql"))
        
        # Sobrescribir con settings.json si existe
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("carpeta_entrada"): self.carpeta_entrada.set(data["carpeta_entrada"])
                    if data.get("archivo_salida"): self.archivo_salida.set(data["archivo_salida"])
                    if data.get("archivo_sql"): self.archivo_sql.set(data["archivo_sql"])
            except Exception as e:
                logging.error(f"Error al leer settings.json: {e}")

    def guardar_configuracion(self):
        data = {
            "carpeta_entrada": self.carpeta_entrada.get(),
            "archivo_salida": self.archivo_salida.get(),
            "archivo_sql": self.archivo_sql.get()
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Error al guardar settings.json: {e}")

    def configurar_logs(self):
        # Configurar para que los logs vayan también al cuadro de texto
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
        extractor.logger.addHandler(text_handler)
        
    def crear_interfaz(self):
        # Contenedor principal con algo de padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        title_label = ttk.Label(main_frame, text="Procesamiento de Facturas PDF", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # --- SECCIÓN ENTRADA ---
        entrada_frame = ttk.LabelFrame(main_frame, text=" 1. Origen de los PDFs ", padding="10")
        entrada_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(entrada_frame, text="Carpeta:").pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_entrada = ttk.Entry(entrada_frame, textvariable=self.carpeta_entrada, state="readonly")
        self.lbl_entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(entrada_frame, text="Examinar...", command=self.seleccionar_carpeta).pack(side=tk.RIGHT)

        # --- SECCIÓN SALIDA ---
        salida_frame = ttk.LabelFrame(main_frame, text=" 2. Destino del Excel ", padding="10")
        salida_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(salida_frame, text="Archivo:").pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_salida = ttk.Entry(salida_frame, textvariable=self.archivo_salida, state="readonly")
        self.lbl_salida.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(salida_frame, text="Examinar...", command=self.seleccionar_archivo).pack(side=tk.RIGHT)

        # --- SECCIÓN FACTURAS ---
        sql_frame = ttk.LabelFrame(main_frame, text=" 3. Lista de Facturas a Verificar (SQL / Excel) ", padding="10")
        sql_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(sql_frame, text="Archivo:").pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_sql = ttk.Entry(sql_frame, textvariable=self.archivo_sql, state="readonly")
        self.lbl_sql.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(sql_frame, text="Examinar...", command=self.seleccionar_sql).pack(side=tk.RIGHT)

        # --- SECCIÓN PROGRESO ---
        self.progreso_frame = ttk.Frame(main_frame)
        self.progreso_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.lbl_status = ttk.Label(self.progreso_frame, text="Listo para iniciar.", font=("Segoe UI", 10))
        self.lbl_status.pack(anchor=tk.W, pady=(0, 5))
        
        # En lugar de ttk.Progressbar, usamos un Canvas personalizado de alta fidelidad
        self.progress_canvas = tk.Canvas(self.progreso_frame, height=24, bg="#e1e1e1", highlightthickness=0)
        self.progress_canvas.pack(fill=tk.X, pady=5)
        
        # Dibujar barra azul de progreso y texto superpuesto vectorialmente
        self.rect_bg = self.progress_canvas.create_rectangle(0, 0, 0, 24, fill="#0078d7", width=0)
        self.text_progress = self.progress_canvas.create_text(0, 12, text="Listo", fill="#000000", font=("Segoe UI", 9, "bold"))
        
        self.progress_value = 0
        self.progress_text_val = "Listo"
        
        def on_canvas_configure(event):
            width = event.width
            self.progress_canvas.coords(self.text_progress, width / 2, 12)
            self.actualizar_barra_canvas(self.progress_value)
            
        self.progress_canvas.bind("<Configure>", on_canvas_configure)

        # --- BOTONES DE ACCIÓN ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 15))
        
        self.btn_procesar = ttk.Button(action_frame, text="Iniciar Procesamiento", command=self.iniciar_proceso)
        self.btn_procesar.pack(side=tk.RIGHT, ipadx=10, ipady=5)
        
        self.btn_coincidencias = ttk.Button(action_frame, text="Ver Coincidencias (0)", command=self.toggle_logs)
        self.btn_coincidencias.pack(side=tk.LEFT)

        # --- SECCIÓN LOGS (Oculta por defecto) ---
        self.log_frame = ttk.Frame(main_frame)
        
        # Contenedor dividido para Matches y Logs
        paned = ttk.PanedWindow(self.log_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Panel superior: Treeview de Coincidencias
        matches_frame = ttk.LabelFrame(paned, text=" Coincidencias Encontradas ")
        paned.add(matches_frame, weight=1)
        
        self.tree_matches = ttk.Treeview(matches_frame, columns=("PDF", "Factura", "Página"), show='headings', height=5)
        self.tree_matches.heading("PDF", text="Archivo Original")
        self.tree_matches.heading("Factura", text="Nº Factura")
        self.tree_matches.heading("Página", text="Página (Hoja)")
        self.tree_matches.column("PDF", width=200)
        self.tree_matches.column("Factura", width=100, anchor=tk.CENTER)
        self.tree_matches.column("Página", width=80, anchor=tk.CENTER)
        
        scroll_tree = ttk.Scrollbar(matches_frame, orient=tk.VERTICAL, command=self.tree_matches.yview)
        self.tree_matches.configure(yscroll=scroll_tree.set)
        self.tree_matches.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_tree.pack(side=tk.RIGHT, fill=tk.Y)

        # Panel inferior: Logs
        text_frame = ttk.Frame(paned)
        paned.add(text_frame, weight=1)
        
        # Scrollbar para el log
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(text_frame, height=5, yscrollcommand=scrollbar.set, state='disabled', font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de PDFs")
        if carpeta:
            self.carpeta_entrada.set(carpeta)
            self.guardar_configuracion()

    def actualizar_barra_canvas(self, valor_porcentaje, texto=None):
        self.progress_value = max(0.0, min(100.0, float(valor_porcentaje)))
        if texto is not None:
            self.progress_text_val = texto
            
        # Obtener el ancho actual del Canvas
        width = self.progress_canvas.winfo_width()
        if width <= 1:
            width = 400  # Fallback inicial
            
        ancho_barra = (self.progress_value / 100.0) * width
        self.progress_canvas.coords(self.rect_bg, 0, 0, ancho_barra, 24)
        
        # Contraste inteligente: si la barra azul cubre más de la mitad, el texto pasa a blanco
        if self.progress_value > 50:
            self.progress_canvas.itemconfig(self.text_progress, fill="#ffffff")
        else:
            self.progress_canvas.itemconfig(self.text_progress, fill="#000000")
            
        self.progress_canvas.itemconfig(self.text_progress, text=self.progress_text_val)

    def seleccionar_archivo(self):
        archivo = filedialog.asksaveasfilename(
            title="Guardar archivo Excel",
            defaultextension=".xlsx",
            filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
        )
        if archivo:
            self.archivo_salida.set(archivo)
            self.guardar_configuracion()

    def seleccionar_sql(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar Lista de Facturas",
            filetypes=[("Base de Datos", "*.sql *.xlsx *.xls"), ("Archivos Excel", "*.xlsx *.xls"), ("Archivos SQL", "*.sql"), ("Todos los archivos", "*.*")]
        )
        if archivo:
            self.archivo_sql.set(archivo)
            self.guardar_configuracion()

    def toggle_logs(self):
        if self.log_frame.winfo_ismapped():
            self.log_frame.pack_forget()
        else:
            self.log_frame.pack(fill=tk.BOTH, expand=True)

    def actualizar_progreso(self, **kwargs):
        def update_ui():
            if "progreso" in kwargs:
                self.actual_pdf = kwargs["progreso"]["actual"]
                self.total_pdfs = kwargs["progreso"]["total"]
                archivo_actual = kwargs["progreso"]["archivo"]
                
                # En lugar de saltar al 100% inmediatamente, la barra empieza en la fracción del PDF actual
                porcentaje_inicial = ((self.actual_pdf - 1) / self.total_pdfs) * 100
                self.actualizar_barra_canvas(porcentaje_inicial, f"Preparando PDF {self.actual_pdf} de {self.total_pdfs}")
                self.lbl_status.config(text=f"Preparando: {archivo_actual} (PDF {self.actual_pdf} de {self.total_pdfs})")
                
            if "progreso_pagina" in kwargs:
                p = kwargs["progreso_pagina"]
                
                # Obtener el estado de archivos procesados, fallback seguro a 1
                actual_pdf = getattr(self, "actual_pdf", 1)
                total_pdfs = getattr(self, "total_pdfs", 1)
                
                # Calcular el porcentaje exacto de avance de la página actual incluyendo su sub-estado interno
                sub_pct = p.get("porcentaje_interno", 0)
                porcentaje_pag = ((p['actual'] - 1) + (sub_pct / 100.0)) / p['total'] * 100
                
                # Calcular progreso global acumulado
                porcentaje_global = ((actual_pdf - 1) / total_pdfs) * 100 + (porcentaje_pag / total_pdfs)
                
                # Mostrar página y porcentaje directamente en la barra Canvas de manera súper explícita
                self.actualizar_barra_canvas(porcentaje_global, f"Pág {p['actual']} de {p['total']} ({int(porcentaje_global)}%)")
                
                # Mostrar el sub-estado (ej: OpenCV, OCR, Regex) de manera clara
                sub_estado = p.get("sub_estado", "Procesando...")
                self.lbl_status.config(text=f"Procesando: {p['archivo']} (Página {p['actual']} de {p['total']}) — {sub_estado}")
            
            if "match" in kwargs:
                m = kwargs["match"]
                self.tree_matches.insert("", "end", values=(m["archivo"], m["factura"], m["pagina"]))
                # Auto-scroll the treeview to the bottom
                self.tree_matches.yview_moveto(1)
                
                # Actualizar el contador del botón
                total_matches = len(self.tree_matches.get_children())
                self.btn_coincidencias.config(text=f"Ver Coincidencias ({total_matches})")
                
                # Expand the log frame to show matches if it's not visible
                if not self.log_frame.winfo_ismapped():
                    self.toggle_logs()

        self.root.after(0, update_ui)

    def iniciar_proceso(self):
        if self.procesando:
            return
            
        carpeta = self.carpeta_entrada.get()
        archivo = self.archivo_salida.get()
        sql = self.archivo_sql.get()
        
        if not carpeta or not archivo:
            messagebox.showwarning("Faltan datos", "Por favor selecciona la carpeta de origen y el archivo de destino.")
            return
            
        # Limpiar logs y matches anteriores
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        for item in self.tree_matches.get_children():
            self.tree_matches.delete(item)
            
        self.btn_coincidencias.config(text="Ver Coincidencias (0)")
        
        self.procesando = True
        self.btn_procesar.config(state=tk.DISABLED)
        self.lbl_status.config(text="Iniciando motor OCR y cargando SQL...")
        self.actualizar_barra_canvas(0, "Iniciando...")
        
        # Ejecutar en hilo separado
        hilo = threading.Thread(target=self._hilo_proceso, args=(carpeta, archivo, sql), daemon=True)
        hilo.start()

    def _hilo_proceso(self, carpeta, archivo, sql):
        try:
            extractor.main(
                carpeta_entrada=carpeta, 
                archivo_salida=archivo, 
                ruta_sql=sql,
                progress_callback=self.actualizar_progreso
            )
            
            # Recolectar resultados para el resumen
            hijos = self.tree_matches.get_children()
            total_coincidencias = len(hijos)
            facturas_coincidentes = []
            
            for item in hijos:
                valores = self.tree_matches.item(item, 'values')
                if valores and len(valores) > 1:
                    facturas_coincidentes.append(valores[1])
            
            if total_coincidencias > 0:
                resumen = f"El procesamiento ha finalizado.\n\n¡Se encontraron {total_coincidencias} coincidencias!\n\nFacturas coincidentes:\n"
                # Mostrar hasta 10 facturas para no saturar el popup
                resumen += ", ".join(facturas_coincidentes[:10])
                if total_coincidencias > 10:
                    resumen += f" ... y {total_coincidencias - 10} más."
            else:
                resumen = "El procesamiento ha finalizado.\n\nNo se encontraron coincidencias con la base de datos SQL."
            
            self.root.after(0, lambda: self.lbl_status.config(text="¡Procesamiento completado con éxito!"))
            self.root.after(0, lambda: messagebox.showinfo("Completado", resumen))
        except Exception as e:
            extractor.logger.error(f"Error crítico en la ejecución: {e}")
            self.root.after(0, lambda: self.lbl_status.config(text="Error durante el procesamiento."))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Ha ocurrido un error:\n{e}"))
        finally:
            self.procesando = False
            self.root.after(0, lambda: self.btn_procesar.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.actualizar_barra_canvas(100, "100% Completado"))

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerGUI(root)
    root.mainloop()
