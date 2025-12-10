import time
import board
import busio
import adafruit_bh1750
from adafruit_pcf8591.pcf8591 import PCF8591
from adafruit_pcf8591.analog_in import AnalogIn

def leer_canal_estable(canal):
    """Lee el ADC descartando el primer valor para evitar ruido."""
    _ = canal.value
    time.sleep(0.05)
    raw = canal.value
    return int(raw / 256)

def main():
    print("Iniciando sistema con PCF8591 (ADC) y BH1750 (Lux)...")

    try:
        # Inicializamos el BUS I2C una sola vez para todos los sensores
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # 1. Inicializar ADC (PCF8591) - Direccion 0x48
        pcf = PCF8591(i2c)
        
        # 2. Inicializar Luxometro (BH1750) - Direccion 0x23
        sensor_luz = adafruit_bh1750.BH1750(i2c)
        
        print("? Sensores I2C detectados correctamente.")
        
    except Exception as e:
        print(f"? Error I2C: {e}")
        return

    # Definimos las entradas del ADC
    ain0 = AnalogIn(pcf, 0)
    ain1 = AnalogIn(pcf, 1)
    ain2 = AnalogIn(pcf, 2)
    ain3 = AnalogIn(pcf, 3)

    # Encabezado de la tabla
    print("-" * 65)
    print("{:<8} | {:<8} | {:<8} | {:<8} || {:<15}".format("AIN0", "AIN1", "AIN2", "AIN3", "LUX (Luz)"))
    print("-" * 65)

    try:
        while True:
            # Lectura del ADC (Humedad, Potenciometro, etc.)
            v0 = leer_canal_estable(ain0)
            v1 = leer_canal_estable(ain1)
            v2 = leer_canal_estable(ain2)
            v3 = leer_canal_estable(ain3)

            # Lectura del Luxometro
            try:
                valor_lux = sensor_luz.lux
            except:
                valor_lux = -1.0 # Si falla, muestra -1

            # Imprimir todo en una sola linea
            print(f"{v0:<8} | {v1:<8} | {v2:<8} | {v3:<8} || {valor_lux:<8.1f} lx")
            
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nDetenido por usuario.")

if __name__ == "__main__":
    main()