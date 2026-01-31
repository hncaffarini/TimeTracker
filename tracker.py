import time
import platform
import subprocess
import sqlite3
import ctypes
from datetime import datetime

# --- Configuración ---
CURRENT_OS             = platform.system()
DB_NAME                = "time_tracker.db"
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
    actividad = clasificar_ventana(ventana_cruda)
    
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
            print(f"[{fecha_hoy}] +{INTERVALO}s: {actividad}")
    except Exception as e:
        print(f"Error DB: {e}")

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

if __name__ == "__main__":
    inicializar_db()
    print(f"--- Tracker en {CURRENT_OS} ---")
    print(f"Umbral de inactividad: {TIEMPO_MAX_INACTIVIDAD} segundos")
    
    try:
        while True:
            tiempo_sin_uso = get_idle_time()
            
            if tiempo_sin_uso < TIEMPO_MAX_INACTIVIDAD:
                ventana = get_active_window()
                actualizar_tiempo(ventana)
            else:
                # Imprimimo en consola solo para notificar que el script sigue vivo
                print(f"(Usuario ausente por {int(tiempo_sin_uso)}s - No registrando)", end='\r')
                
            time.sleep(INTERVALO)
            
    except KeyboardInterrupt:
        print("\nTracker detenido.")