import sqlite3
from datetime import datetime

conn = sqlite3.connect('time_tracker.db')
cursor = conn.cursor()
hoy = datetime.now().strftime('%Y-%m-%d')

print(f"--- REPORTE DE TIEMPO: {hoy} ---")
print(f"{'ACTIVIDAD':<30} | {'TIEMPO':<15}")
print("-" * 50)

cursor.execute('''
    SELECT actividad, segundos 
    FROM time_tracker 
    WHERE fecha = ? 
    ORDER BY segundos DESC
''', (hoy,))

total_segundos = 0

for fila in cursor.fetchall():
    actividad = fila[0]
    segundos = fila[1]
    total_segundos += segundos
    
    if segundos >= 3600:
        tiempo_str = f"{segundos/3600:.1f} hs"
    else:
        tiempo_str = f"{segundos/60:.0f} min"
        
    print(f"{actividad:<30} | {tiempo_str}")

print("-" * 50)
print(f"TOTAL REGISTRADO: {total_segundos/3600:.2f} horas")

conn.close()