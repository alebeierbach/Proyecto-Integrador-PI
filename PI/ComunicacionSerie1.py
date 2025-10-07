import serial, time, glob, sys

BAUD = 115200     
PORT = "/dev/ttyACM0"

def open_port(port, baud):
    ser = serial.Serial(port, baud, timeout=1)
    # muchos Arduinos se resetean al abrir; damos tiempo
    time.sleep(2.0)
   
    ser.reset_input_buffer()
    return ser

def main():
    print(f"Usando puerto: {PORT} a {BAUD} baudios")
    try:
        ser = open_port(PORT, BAUD)
    except Exception as e:
        print(f"No se pudo abrir {PORT}: {e}", file=sys.stderr)
        sys.exit(1)

    last_info = time.time()
    try:
        while True:
            line = ser.readline().decode("ascii", errors="ignore").strip()
            if line:
                print(line)
                last_info = time.time()
            else:
                # cada 3 s avisamos que no llegan datos
                if time.time() - last_info > 3:
                    print("??  No llegan lineas. Verifica: BAUD, Serial.println(), cable USB, sketch corriendo")
                    last_info = time.time()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
