import time
import sys
import glob
import serial 
import adafruit_dht
import board

DHT_PIN = board.D17
DHT_READ_PERIOD = 3.0
BAUD = 115200

def find_arduino_port():
    candidates = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    if not candidates:
        return None
    return candidates[0]

def open_port(port, baud):
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2.0)          
    ser.reset_input_buffer()
    return ser

def main():
    print("Inicializando DHT22...")
    dht = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

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

    print("\nIniciando monitoreo. Ctrl+C para detener.")
    print("---------------------------------------------------------------------------------")
    print("Formato: [Arduino Raw Data] | HumedadAire(%) | Temp(C)")
    
    last_dht_read_time = 0.0
    last_serial_activity_time = time.time()

    try:
        while True:
            now = time.time()
            
            serial_data = "Serial=----"
            if ser is not None and ser.in_waiting:
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if line:
                    serial_data = f"Serial={line:<12}"
                    last_serial_activity_time = now
            
            if ser is not None and now - last_serial_activity_time > 3:
                 print("?? No llegan lneas del Arduino. Verifica cable/sketch.", file=sys.stderr)
                 last_serial_activity_time = now

            hum_air = None
            temp_c = None
            
            if now - last_dht_read_time >= DHT_READ_PERIOD:
                try:
                    temp_c = dht.temperature
                    hum_air = dht.humidity
                    last_dht_read_time = now
                except RuntimeError as e:
                    print(f"Error temporal de lectura DHT: {e}. Reintentando...")

            out_parts = [serial_data]
            out_parts.append(f"HumedadAire={hum_air:5.1f}%" if hum_air is not None else "HumedadAire=---.-%")
            out_parts.append(f"Temp={temp_c:4.1f}C" if temp_c is not None else "Temp=--.-C")
            
            print(" | ".join(out_parts))

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    finally:
        if ser is not None:
            ser.close()

if __name__ == "__main__":
    main()
