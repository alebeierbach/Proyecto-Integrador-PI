import time
import sys
import glob
import serial
import adafruit_dht
import board
import RPi.GPIO as GPIO

# --- CONFIGURACIN ---
DHT_PIN = board.D17

PIN_FOCO = 26       
PIN_BOMBA = 19      
PIN_VENTILADOR = 13

# --- UMBRALES DE CONTROL ---
UMBRAL_LUZ_BAJA = 300     # Valor de LDR para prender el foco
UMBRAL_SUELO_BAJO = 450   # Valor del sensor de humedad del suelo para regar
UMBRAL_AIRE_ALTO = 70.0   # Porcentaje de humedad (del DHT) para ventilar

DHT_READ_PERIOD = 3.0
BAUD = 115200

# --- FUNCIONES AUXILIARES ---
def find_arduino_port():
    """Busca un dispositivo Arduino conectado por USB."""
    candidates = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    return candidates[0] if candidates else None

def open_port(port, baud):
    """Abre el puerto serie y espera a que el Arduino se reinicie."""
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2.0)
    ser.reset_input_buffer()
    return ser

# --- FUNCION PRINCIPAL ---
def main():
    print("Inicializando DHT22...")
    dht = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

# --- Conexion al Arduino ---
    port = find_arduino_port()
    ser = None
    if port:
        try:
            ser = open_port(port, BAUD)
            print(f"? Puerto Arduino conectado: {port} @ {BAUD} baudios")
        except Exception as e:
            print(f"? No se pudo abrir {port} para Arduino: {e}", file=sys.stderr)
    else:
        print("? No se encontr ningn Arduino conectado.")

# --- CONFIGURACIÓN GPIO ---
    print("Inicializando pines GPIO...")
    GPIO.setmode(GPIO.BCM) # Usar numeración de pines BCM
    GPIO.setup(PIN_FOCO, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_BOMBA, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_VENTILADOR, GPIO.OUT, initial=GPIO.LOW)

    print("\nIniciando monitoreo. Ctrl+C para detener.")
    print("--------------------------------------------------------------------------------------------")
    print("Formato: [HumedadSuelo] [Luz] [HumedadAire] [Temp]")

    last_dht_read_time = 0.0
    last_serial_activity_time = time.time()

    humedad_suelo = None
    luz = None
    hum_air = None
    temp_c = None

    try:
        while True:
            now = time.time()

# --- Lectura desde Arduino ---
            if ser is not None and ser.in_waiting:
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if line:
                    # Espera formato: "humedad:523, luz:812"
                    if "humedad" in line and "luz" in line:
                        try:
                            parts = line.replace(" ", "").split(",")
                            humedad_suelo = int(parts[0].split(":")[1])
                            luz = int(parts[1].split(":")[1])
                        except Exception as e:
                            print(f"? Error al parsear datos Arduino: {line} ({e})")

                    last_serial_activity_time = now

            # --- Verifica actividad del puerto ---
            if ser is not None and now - last_serial_activity_time > 3:
                print("No llegan lineas del Arduino. Verifica cable/sketch.", file=sys.stderr)
                last_serial_activity_time = now

# --- Lectura del DHT22 ---
            if now - last_dht_read_time >= DHT_READ_PERIOD:
                try:
                    temp_c = dht.temperature
                    hum_air = dht.humidity
                    last_dht_read_time = now
                except RuntimeError as e:
                    print(f"Error temporal de lectura DHT: {e}. Reintentando...")

# --- Logica de sensores y actuadores ---
                # 1. Control de Iluminación (Foco)
                if luz is not None:
                    if luz < UMBRAL_LUZ_BAJA:
                        GPIO.output(PIN_FOCO, GPIO.HIGH) # Prender foco
                    else:
                        GPIO.output(PIN_FOCO, GPIO.LOW)  # Apagar foco
                # 2. Control de Riego (Bomba)
                if humedad_suelo is not None:
                    # OJO: Verifica tu sensor. Asumo que un valor ALTO = SECO
                    if humedad_suelo > UMBRAL_SUELO_BAJO:
                        GPIO.output(PIN_BOMBA, GPIO.HIGH) # Prender bomba
                    else:
                        GPIO.output(PIN_BOMBA, GPIO.LOW)  # Apagar bomba
                # 3. Control de Ventilación
                if hum_air is not None:
                    if hum_air > UMBRAL_AIRE_ALTO:
                        GPIO.output(PIN_VENTILADOR, GPIO.HIGH) # Prender ventilador
                    else:
                        GPIO.output(PIN_VENTILADOR, GPIO.LOW)  # Apagar ventilador

# --- Salida---
            out_parts = []
            out_parts.append(f"HumedadSuelo={humedad_suelo:4d}" if humedad_suelo is not None else "HumedadSuelo=----")
            out_parts.append(f"Luz={luz:4d}" if luz is not None else "Luz=----")
            out_parts.append(f"HumedadAire={hum_air:5.1f}%" if hum_air is not None else "HumedadAire=---.-%")
            out_parts.append(f"Temp={temp_c:4.1f}C" if temp_c is not None else "Temp=--.-C")

            print(" | ".join(out_parts))
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    finally:
        if ser is not None:
            ser.close()
        GPIO.cleanup()

# --- EJECUCION ---
if _name_ == "_main_":
    main()