import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from pathlib import Path
import sys

# Importar el módulo principal de extracción
import extractor
from modules.config import CONFIG

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
        self.carpeta_entrada = tk.StringVar(value=CONFIG.get("carpeta_pdfs", ""))
        self.archivo_salida = tk.StringVar(value=CONFIG.get("archivo_excel", ""))
        self.procesando = False
        
        self.crear_interfaz()
        self.configurar_logs()

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
        salida_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(salida_frame, text="Archivo:").pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_salida = ttk.Entry(salida_frame, textvariable=self.archivo_salida, state="readonly")
        self.lbl_salida.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(salida_frame, text="Examinar...", command=self.seleccionar_archivo).pack(side=tk.RIGHT)

        # --- SECCIÓN PROGRESO ---
        self.progreso_frame = ttk.Frame(main_frame)
        self.progreso_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.lbl_status = ttk.Label(self.progreso_frame, text="Listo para iniciar.", font=("Segoe UI", 10))
        self.lbl_status.pack(anchor=tk.W, pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(self.progreso_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        # --- BOTONES DE ACCIÓN ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 15))
        
        self.btn_procesar = ttk.Button(action_frame, text="Iniciar Procesamiento", command=self.iniciar_proceso)
        self.btn_procesar.pack(side=tk.RIGHT, ipadx=10, ipady=5)
        
        self.btn_logs = ttk.Button(action_frame, text="Ver Detalles / Logs", command=self.toggle_logs)
        self.btn_logs.pack(side=tk.LEFT)

        # --- SECCIÓN LOGS (Oculta por defecto) ---
        self.log_frame = ttk.Frame(main_frame)
        
        # Scrollbar para el log
        scrollbar = ttk.Scrollbar(self.log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(self.log_frame, height=10, yscrollcommand=scrollbar.set, state='disabled', font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de PDFs")
        if carpeta:
            self.carpeta_entrada.set(carpeta)

    def seleccionar_archivo(self):
        archivo = filedialog.asksaveasfilename(
            title="Guardar archivo Excel",
            defaultextension=".xlsx",
            filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
        )
        if archivo:
            self.archivo_salida.set(archivo)

    def toggle_logs(self):
        if self.log_frame.winfo_ismapped():
            self.log_frame.pack_forget()
        else:
            self.log_frame.pack(fill=tk.BOTH, expand=True)

    def actualizar_progreso(self, actual, total, archivo_actual):
        porcentaje = (actual / total) * 100
        def update_ui():
            self.progress_bar['value'] = porcentaje
            self.lbl_status.config(text=f"Procesando: {archivo_actual} ({actual}/{total})")
        self.root.after(0, update_ui)

    def iniciar_proceso(self):
        if self.procesando:
            return
            
        carpeta = self.carpeta_entrada.get()
        archivo = self.archivo_salida.get()
        
        if not carpeta or not archivo:
            messagebox.showwarning("Faltan datos", "Por favor selecciona la carpeta de origen y el archivo de destino.")
            return
            
        # Limpiar logs anteriores
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
        self.procesando = True
        self.btn_procesar.config(state=tk.DISABLED)
        self.lbl_status.config(text="Iniciando motor OCR...")
        self.progress_bar['value'] = 0
        
        # Ocultamos temporalmente la sección de progreso y mostramos si queremos
        
        # Ejecutar en hilo separado
        hilo = threading.Thread(target=self._hilo_proceso, args=(carpeta, archivo), daemon=True)
        hilo.start()

    def _hilo_proceso(self, carpeta, archivo):
        try:
            extractor.main(
                carpeta_entrada=carpeta, 
                archivo_salida=archivo, 
                progress_callback=self.actualizar_progreso
            )
            self.root.after(0, lambda: self.lbl_status.config(text="¡Procesamiento completado con éxito!"))
            self.root.after(0, lambda: messagebox.showinfo("Completado", "El procesamiento ha finalizado con éxito."))
        except Exception as e:
            extractor.logger.error(f"Error crítico en la ejecución: {e}")
            self.root.after(0, lambda: self.lbl_status.config(text="Error durante el procesamiento."))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Ha ocurrido un error:\n{e}"))
        finally:
            self.procesando = False
            self.root.after(0, lambda: self.btn_procesar.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress_bar.config(value=100))

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerGUI(root)
    root.mainloop()
