import time
import platform
import subprocess
import sqlite3
import threading
import ctypes
from datetime import datetime
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# --- Configuración ---
CURRENT_OS             = platform.system()
DB_NAME                = "time_tracker.db"
RUNNING                = True
INTERVALO              = 5   # Cada cuántos segundos se lee la actividad
TIEMPO_MAX_INACTIVIDAD = 120 # Cantidad de segundos para que deje de contar actividad

# --- Websites ---
# En general, toda la navegación web va a parar a "Navegacion - Otros", con excepción de estos sitios.
# Esto sirve para medir el tiempo que quemo en estas páginas en específico
WEBSITES_LIST = [
    "spotify",
    "reddit",  
    "youtube", 
    "notion", 
    "gmail", 
    "wikipedia", 
    "tareas", 
    "whatsapp",
    "gemini"
]

NAVEGADORES = [
    "mozilla firefox", 
    "vivaldi",
    "microsoft edge", 
    "opera", 
    "brave", 
    "midori", 
    "google chrome"
]

# --- Detección de inactividad ---
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

def get_idle_time():
    """Devuelve los segundos que estás inactivo (sin mover el mouse/teclado)"""
    try:
        if CURRENT_OS == 'Windows':
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return millis / 1000.0
            return 0
            
        elif CURRENT_OS == 'Linux':
            output = subprocess.check_output('xprintidle').strip()
            millis = int(output)
            return millis / 1000.0
            
    except Exception:
        return 0 # Ante la duda, asumo actividad para no romper el script
    return 0

def inicializar_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_tracker (
                fecha TEXT,
                actividad TEXT,
                segundos INTEGER,
                PRIMARY KEY (fecha, actividad)
            )
        ''')
        conn.commit()

def clasificar_ventana(titulo_ventana):
    if not titulo_ventana: return "Desconocido"
    titulo_lower = titulo_ventana.lower()
    
    for sitio in WEBSITES_LIST:
        if sitio in titulo_lower: return sitio.capitalize()
    
    for nav in NAVEGADORES:
        if nav in titulo_lower: return "Navegación - Otros"
            
    if " - " in titulo_ventana:
        return titulo_ventana.split(" - ")[-1].strip()
        
    return titulo_ventana.strip()

def actualizar_tiempo(ventana_cruda):
    now = datetime.now()
    fecha_hoy = now.strftime('%Y-%m-%d')
    
    actividad = ventana_cruda
    titulo_lower = ventana_cruda.lower()
    
    match_encontrado = False
    for sitio in WEBSITES_LIST:
        if sitio in titulo_lower:
            actividad = sitio.capitalize()
            match_encontrado = True
            break
            
    if not match_encontrado:
        for nav in NAVEGADORES:
            if nav in titulo_lower:
                actividad = "Navegación - Otros"
                match_encontrado = True
                break
    
    if not match_encontrado and " - " in ventana_cruda:
        actividad = ventana_cruda.split(" - ")[-1].strip()

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO time_tracker (fecha, actividad, segundos)
                VALUES (?, ?, ?)
                ON CONFLICT(fecha, actividad) 
                DO UPDATE SET segundos = segundos + ?
            ''', (fecha_hoy, actividad, INTERVALO, INTERVALO))
            conn.commit()
    except Exception:
        pass

def get_active_window():
    try:
        if CURRENT_OS == 'Windows':
            import win32gui
            w = win32gui.GetForegroundWindow()
            t = win32gui.GetWindowText(w)
            if t == "Program Manager": return "Escritorio"
            return t if t else "Escritorio"
        elif CURRENT_OS == 'Linux':
            root = subprocess.check_output(['xprop', '-root', '_NET_ACTIVE_WINDOW'], stderr=subprocess.DEVNULL)
            id_ = root.decode('utf-8').strip().split()[-1]
            if id_ == "0x0": return "Escritorio"
            res = subprocess.check_output(['xprop', '-id', id_, 'WM_NAME'], stderr=subprocess.DEVNULL)
            return res.decode('utf-8').strip().split(' = ')[-1].strip('"')
    except:
        return "Sistema"
    return "Desconocido"

def crear_icono():
    width = 64
    height = 64
    color_1 = (0, 0, 0)
    color_2 = (0, 120, 215)
    
    image = Image.new('RGB', (width, height), color_1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color_2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color_2)
    
    return image

def accion_salir(icon, item):
    global corriendo
    corriendo = False
    icon.stop()

def bucle_tracker():
    """Esta función corre en otro hilo separado"""
    inicializar_db()
    
    while corriendo:
        tiempo_sin_uso = get_idle_time()
        
        if tiempo_sin_uso < TIEMPO_MAX_INACTIVIDAD:
            ventana = get_active_window()
            actualizar_tiempo(ventana)

        for _ in range(INTERVALO):
            if not corriendo: break
            time.sleep(1)

if __name__ == "__main__":
    # 1. Iniciamos el tracker en un hilo separado (Background)
    hilo_tracker = threading.Thread(target=bucle_tracker)
    hilo_tracker.daemon = True # Si el programa principal muere, este hilo también
    hilo_tracker.start()
    
    # 2. Iniciamos el icono del sistema (Bloquea el hilo principal)
    image = crear_icono()
    menu = pystray.Menu(
        item('Tracker de Tiempo (Activo)', lambda icon, item: None, enabled=False),
        item('Salir', accion_salir)
    )
    
    icon = pystray.Icon("TrackerApp", image, "Tracker de Tiempo", menu)
    icon.run()