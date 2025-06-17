import subprocess
import serial
import time
import csv
from flask import Flask, render_template
import threading
import os
import re

# Configuración inicial
CSV_FILE = "registros.csv"
PUERTO_SERIAL = "COM3"  # Cambia esto según tu sistema
BAUDIOS = 9600

# Función para detectar la puerta de enlace predeterminada en Windows
def detectar_gateway():
    try:
        salida = subprocess.check_output("ipconfig", encoding="cp1252")
        for linea in salida.splitlines():
            if "Puerta de enlace predeterminada" in linea:
                partes = re.findall(r"\d+\.\d+\.\d+\.\d+", linea)
                if partes:
                    return partes[0]
    except Exception as e:
        print(f"Error al detectar gateway: {e}")
    return None

GATEWAY = detectar_gateway()
print(f"Puerta de enlace detectada: {GATEWAY}")

# Inicializar conexión serial con Arduino
try:
    arduino = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=1)
    time.sleep(2)
except:
    arduino = None
    print("⚠️ No se pudo conectar con el Arduino. Verifica el puerto.")

# Inicializar Flask
app = Flask(__name__)

# Crear archivo CSV si no existe
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Fecha", "Latencia (ms)", "Estado"])

# Función para hacer ping al gateway detectado
def medir_latencia():
    if not GATEWAY:
        return None
    try:
        resultado = subprocess.check_output(["ping", "-n", "1", GATEWAY], encoding="cp1252")
        for linea in resultado.split("\n"):
            if "tiempo=" in linea or "time=" in linea:
                parte = linea.split("tiempo=")[-1] if "tiempo=" in linea else linea.split("time=")[-1]
                latencia = int(parte.strip().split("ms")[0])
                return latencia
    except Exception as e:
        print(f"Error al medir latencia: {e}")
        return None

# Guardar registro y enviar al Arduino
def procesar_medicion():
    latencia = medir_latencia()
    if latencia is None:
        return

    if latencia <= 100:
        estado = "OK"
    elif latencia <= 200:
        estado = "WARN"
    else:
        estado = "BAD"

    fecha = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([fecha, latencia, estado])

    print(f"[{fecha}] Latencia: {latencia} ms → Estado: {estado}")

    if arduino:
        try:
            arduino.write((estado + "\n").encode())
        except Exception as e:
            print(f"Error al enviar al Arduino: {e}")

# Hilo para hacer mediciones cada 10 segundos
def loop_mediciones():
    while True:
        procesar_medicion()
        time.sleep(4)

threading.Thread(target=loop_mediciones, daemon=True).start()

# Ruta web
@app.route("/")
def index():
    with open(CSV_FILE, newline='') as f:
        reader = csv.reader(f)
        data = list(reader)
    return render_template("index.html", registros=data[::-1])

# Ejecutar servidor Flask
if __name__ == "__main__":
    app.run(debug=True)


# -ejecutar esta linea de comandos en la consola
# pip install flask pyserial
