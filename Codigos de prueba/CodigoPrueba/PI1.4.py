# -*- coding: utf-8 -*-
import time
import board
import busio
import adafruit_bh1750
from adafruit_pcf8591.pcf8591 import PCF8591
from adafruit_pcf8591.analog_in import AnalogIn
import RPi.GPIO as GPIO

# ==========================================
#        CONFIGURACION
# ==========================================
INTERVALO_SEGUNDOS = 10     
pin_bomba = 23

# --- CALIBRACION --- (En caso de ajuste manual)
#Multiplicamos por 4.8 (promedio calculado) para corregir medicion
#FACTOR_LUX = 7.14 

CONFIG_LUCES = [
    {'nombre': 'Luz 1', 'pin_gpio': 26, 'umbral_lux': 500},
    {'nombre': 'Luz 2', 'pin_gpio': 13, 'umbral_lux': 500},
    {'nombre': 'Luz 3', 'pin_gpio': 6,  'umbral_lux': 500}
]

CONFIG_PLANTAS = [
    {'nombre': 'Cultivo 1', 'canal_adc': 0, 'pin_solenoide': 19, 'pin_power': 17, 'umbral_seco': 130},
    {'nombre': 'Cultivo 2', 'canal_adc': 1, 'pin_solenoide': 20, 'pin_power': 5,  'umbral_seco': 130},
    {'nombre': 'Cultivo 3',  'canal_adc': 2, 'pin_solenoide': 21, 'pin_power': 22, 'umbral_seco': 130},
    {'nombre': 'Cultivo 4',  'canal_adc': 3, 'pin_solenoide': 16, 'pin_power': 27, 'umbral_seco': 130}
]

# ==========================================
#        FUNCIONES
# ==========================================
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for planta in CONFIG_PLANTAS:
        GPIO.setup(planta['pin_power'], GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(planta['pin_solenoide'], GPIO.OUT, initial=GPIO.HIGH)
    for luz in CONFIG_LUCES:
        GPIO.setup(luz['pin_gpio'], GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(pin_bomba, GPIO.OUT, initial=GPIO.HIGH)
    print("GPIO configurados.")

#Funcion para evitar la corrosion de los sensores
#Se prenden en el instante donde mediran, y luego se apagan.
def leer_humedad_protegida(canal_obj, pin_pwr):
    try:
        GPIO.output(pin_pwr, GPIO.HIGH)
        time.sleep(0.2)
        raw = canal_obj.value
        GPIO.output(pin_pwr, GPIO.LOW)
        return int(raw / 256)
    except:
        GPIO.output(pin_pwr, GPIO.LOW)
        return 0
        
# ==========================================
#        MAIN
# ==========================================
def main():
    print("Iniciando Sistema Calibrado...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pcf = PCF8591(i2c)
        sensor_bh1750 = adafruit_bh1750.BH1750(i2c)
        # Usamos configuracion por defecto
    except Exception as e:
        print(f"Error Hardware: {e}")
        return

    setup_gpio()
    canales_adc = [AnalogIn(pcf, i) for i in range(4)]

    try:
        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}] --- Ciclo ---")

            # --- LUCES ---
            try:
                lux_raw = sensor_bh1750.lux
                #lux_real = lux_raw * FACTOR_LUX 
                print(f"Luz: {lux_raw:.0f} lux")
                
                for luz in CONFIG_LUCES:
                    estado = "OFF"
                    if lux_raw < luz['umbral_lux']:
                        GPIO.output(luz['pin_gpio'], GPIO.LOW)
                        estado = "ON"
                    else:
                        GPIO.output(luz['pin_gpio'], GPIO.HIGH)
                    print(f"  -> {luz['nombre']}: {estado}")
            except:
                print("Error Lux")

            print("-" * 20)

            # --- RIEGO ---
            for planta in CONFIG_PLANTAS:
                idx = planta['canal_adc']
                hum = leer_humedad_protegida(canales_adc[idx], planta['pin_power'])
                
                if hum > planta['umbral_seco']:
                    print(f"  -> {planta['nombre']}: SECO ({hum}) -> REGANDO")
                    GPIO.output(planta['pin_solenoide'], GPIO.LOW)
                    time.sleep(0.5)
                    GPIO.output(pin_bomba, GPIO.LOW)
                    time.sleep(15)
                    GPIO.output(pin_bomba, GPIO.HIGH)
                    time.sleep(0.5)
                    GPIO.output(planta['pin_solenoide'], GPIO.HIGH)
                else:
                    print(f"  -> {planta['nombre']}: OK ({hum})")

            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
