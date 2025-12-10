import time
import board
import busio
import adafruit_bh1750
from adafruit_pcf8591.pcf8591 import PCF8591
from adafruit_pcf8591.analog_in import AnalogIn
import RPi.GPIO as GPIO

# ==========================================
#        SECCION DE CONFIGURACION
# ==========================================

# --- TIEMPO DE MUESTREO ---
INTERVALO_SEGUNDOS = 10     
# INTERVALO_SEGUNDOS = 3600 # DESCOMENTAR PARA 1 HORA
pin_bomba = 23

# --- CONFIGURACION DE LUCES ---
CONFIG_LUCES = [
    {'nombre': 'Luz 1',   'pin_gpio': 26, 'umbral_lux': 2000},
    {'nombre': 'Luz 2',     'pin_gpio': 13, 'umbral_lux': 1500},
    {'nombre': 'Luz 3',     'pin_gpio': 6,  'umbral_lux': 1000}
]

# --- CONFIGURACION DE PLANTAS ---
CONFIG_PLANTAS = [
    {'nombre': 'Lechuga 1', 'canal_adc': 0, 'pin_solenoide': 19, 'umbral_seco': 100},
    {'nombre': 'Lechuga 2', 'canal_adc': 1, 'pin_solenoide': 20, 'umbral_seco': 100},
    {'nombre': 'Tomate 1',  'canal_adc': 2, 'pin_solenoide': 21, 'umbral_seco': 100},
    {'nombre': 'Tomate 2',  'canal_adc': 3, 'pin_solenoide': 16, 'umbral_seco': 100}
]

# ==========================================
#           FUNCIONES AUXILIARES
# ==========================================

def setup_gpio():
    """Configura los pines GPIO como salidas y los apaga (HIGH) al inicio."""
    GPIO.setmode(GPIO.BCM)
    
    # Configurar Luces
    for luz in CONFIG_LUCES:
        pin = luz['pin_gpio']
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH) 
    
    # Configurar Valvulas Solenoides
    for planta in CONFIG_PLANTAS:
        pin = planta['pin_solenoide']
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH) 

    # Configurar Bomba (CORREGIDO)
    GPIO.setup(pin_bomba, GPIO.OUT)   
    GPIO.output(pin_bomba, GPIO.HIGH) # <--- AQUI ESTABA EL ERROR (usabas 'pin')
    print("Pines GPIO configurados.")

def leer_adc_estable(canal_obj):
    """Lee el canal ADC descartando la primera lectura para evitar ruido."""
    try:
        _ = canal_obj.value 
        time.sleep(0.05)    
        raw = canal_obj.value
        return int(raw / 256) 
    except Exception as e:
        print(f"Error leyendo ADC: {e}")
        return 0

# ==========================================
#           PROGRAMA PRINCIPAL
# ==========================================

def main():
    print("Iniciando Sistema de Control de Cultivo...")
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pcf = PCF8591(i2c)
        sensor_bh1750 = adafruit_bh1750.BH1750(i2c)
        print("Bus I2C y Sensores detectados.")
    except Exception as e:
        print(f"Error critico I2C: {e}")
        return

    setup_gpio()

    canales_adc = [AnalogIn(pcf, i) for i in range(4)]

    print("-" * 60)
    print(f"Sistema corriendo. Muestreo cada {INTERVALO_SEGUNDOS} segundos.")
    print("-" * 60)

    try:
        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}] --- Iniciando Ciclo de Lectura ---")

            # --- A. CONTROL DE LUCES ---
            try:
                lux_actual = sensor_bh1750.lux
                print(f"Luz Ambiente: {lux_actual:.1f} lx")
                
                for luz in CONFIG_LUCES:
                    if lux_actual < luz['umbral_lux']:
                        GPIO.output(luz['pin_gpio'], GPIO.LOW)
                        estado = "ENCENDIDO"
                    else:
                        GPIO.output(luz['pin_gpio'], GPIO.HIGH)
                        estado = "APAGADO"
                    print(f"  -> {luz['nombre']}: {estado}")

            except Exception as e:
                print(f"Error leyendo Luxometro: {e}")

            print("-" * 30)

            # --- B. CONTROL DE RIEGO (PLANTAS) ---
            for planta in CONFIG_PLANTAS:
                try:
                    idx_canal = planta['canal_adc']
                    humedad_actual = leer_adc_estable(canales_adc[idx_canal])
                    
                    # Logica: Si el valor es MAYOR al umbral -> TIERRA SECA
                    if humedad_actual > planta['umbral_seco']:
                        print(f"  -> {planta['nombre']} (CH{idx_canal}): Valor={humedad_actual} | RIEGO ACTIVO")
                        
                        # --- SECUENCIA DE PROTECCION HIDRAULICA ---
                        
                        # 1. Abrir Valvula Solenoide (Primero abrimos camino)
                        GPIO.output(planta['pin_solenoide'], GPIO.LOW)
                        time.sleep(0.5) # Esperamos medio segundo para que abra bien
                        
                        # 2. Encender Bomba (Empujamos agua)
                        GPIO.output(pin_bomba, GPIO.LOW)
                        
                        # 3. Regar por 15 segundos
                        time.sleep(15)
                        
                        # 4. Apagar Bomba (Dejamos de empujar PRIMERO)
                        GPIO.output(pin_bomba, GPIO.HIGH)
                        time.sleep(0.5) # Esperamos a que baje la presion en la manguera
                        
                        # 5. Cerrar Valvula Solenoide
                        GPIO.output(planta['pin_solenoide'], GPIO.HIGH)
                        
                        print(f"  -> {planta['nombre']}: Riego finalizado.")
                        
                    else:
                        # Todo apagado por seguridad (Redundante pero seguro)
                        GPIO.output(planta['pin_solenoide'], GPIO.HIGH) 
                        GPIO.output(pin_bomba, GPIO.HIGH)
                        print(f"  -> {planta['nombre']} (CH{idx_canal}): Valor={humedad_actual} | Correcto")
                
                except Exception as e:
                    print(f"Error en {planta['nombre']}: {e}")

            # --- C. ESPERA (Sampling) ---
            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        print("\nDeteniendo sistema...")
    finally:
        GPIO.cleanup()
        print("GPIO liberados. Sistema apagado.")

if __name__ == "__main__":
    main()