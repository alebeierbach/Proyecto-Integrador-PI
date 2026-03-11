# -*- coding: utf-8 -*-
import time
import board
import busio
import csv
import os
import requests  # <--- LIBRERIA PARA ThingSpeak
import adafruit_bh1750
import adafruit_dht
from adafruit_pcf8591.pcf8591 import PCF8591
from adafruit_pcf8591.analog_in import AnalogIn
import RPi.GPIO as GPIO
from datetime import datetime

# ==========================================
#        CONFIGURACION DE HARDWARE
# ==========================================
PIN_BOMBA = 23
PIN_VALVULA = 16
PIN_SENSOR_POWER = 27
PIN_LUZ = 26
PIN_LED_ALERTA = 24

# Sensor Ambiental (DHT22)
PIN_DHT = board.D5  

# I2C
CANAL_ADC = 3

# ==========================================
#        CONFIGURACION DE LOGICA
# ==========================================
# ThingSpeak solo permite subir datos cada 15 segundos.
# Si ponemos 10, perderemos datos. Lo subo a 20 para seguridad.
INTERVALO_LECTURA = 20  
# INTERVALO_LECTURA = 3600 # Para produccion (1 hora)

UMBRAL_LUX = 500
UMBRAL_SECO = 50
RAW_SECO = 160 # Medicion sobre tierra seca
RAW_MOJADO = 8 # Medicion sobre tierra recien regada

HORAS_LUZ_MAXIMAS = 12
SEGUNDOS_EN_HORA = 3600
NOMBRE_ARCHIVO = "registro_tesis.csv"

# --- CONFIGURACION IOT ---
THINGSPEAK_API_KEY = "F0EYLJ4TRFHRHDJ1" 
URL_THINGSPEAK = "https://api.thingspeak.com/update"

# ==========================================
#        FUNCIONES
# ==========================================
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_BOMBA, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(PIN_VALVULA, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(PIN_LUZ, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(PIN_SENSOR_POWER, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_LED_ALERTA, GPIO.OUT, initial=GPIO.LOW)
    # Boton de Panico (Para salir si falla CTRL+C) - GPIO 21 a GND para salir
    GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def leer_humedad_suelo_pct(canal_adc): # Funcion que evita la degradacion del sensor
    try:
        GPIO.output(PIN_SENSOR_POWER, GPIO.HIGH)
        time.sleep(0.2)
        raw = canal_adc.value
        GPIO.output(PIN_SENSOR_POWER, GPIO.LOW)
        lectura_8bit = int(raw / 256)
        humedad_pct = int((lectura_8bit - RAW_SECO) * (100 - 0) / (RAW_MOJADO - RAW_SECO) + 0)
        return max(0, min(100, humedad_pct))
    except:
        GPIO.output(PIN_SENSOR_POWER, GPIO.LOW)
        return 0

def leer_ambiente(dht_device):
    try:
        temp = dht_device.temperature
        hum_amb = dht_device.humidity
        if temp is None or hum_amb is None: return 0, 0
        return temp, hum_amb
    except:
        return 0, 0

def guardar_excel(datos):
    existe = os.path.isfile(NOMBRE_ARCHIVO)
    try:
        with open(NOMBRE_ARCHIVO, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not existe:
                writer.writerow(["Fecha", "Hora", "Lux", "Hum Suelo %", "Temp Amb C", "Hum Amb %", "Luz Estado", "Riego Estado"])
            writer.writerow(datos)
            print("-> Guardado Local (Excel)")
    except:
        print("Error Excel")

# --- FUNCION PARA SUBIR A LA NUBE ---
def subir_datos_iot(lux, hum_suelo, temp_amb, hum_amb, esta_regando):
    try:
        # Preparamos el paquete de datos
        payload = {
            'api_key': THINGSPEAK_API_KEY,
            'field1': lux,
            'field2': hum_suelo,
            'field3': temp_amb,
            'field4': hum_amb,
            'field5': 1 if esta_regando else 0
        }
        # Enviamos (Timeout de 5 seg para que no trabe el riego si no hay internet)
        respuesta = requests.post(URL_THINGSPEAK, data=payload, timeout=5)
        
        if respuesta.status_code == 200:
            print(f"-> SUBIDO A NUBE (Entry: {respuesta.text})")
        else:
            print(f"Error Nube: {respuesta.status_code}")
    except Exception as e:
        print(f"Falla de Internet (Sistema sigue funcionando): {e}")

# ==========================================
#                   MAIN
# ==========================================
def main():
    print("--- INICIANDO SISTEMA IOT COMPLETO ---")
    print("TIP: Conecta GPIO 21 a GND para detener el programa de emergencia.")
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pcf = PCF8591(i2c)
        sensor_bh1750 = adafruit_bh1750.BH1750(i2c)
        adc_humedad = AnalogIn(pcf, CANAL_ADC)
        try:
            dht_device = adafruit_dht.DHT22(PIN_DHT)
        except:
            dht_device = None
            print("ALERTA: DHT22 no detectado. Continuando sin el.")

    except Exception as e:
        print(f"ERROR HARDWARE: {e}")
        return

    setup_gpio()

    # Definimos el horario de luz deseado (Ej: 8 AM a 8 PM)
    HORA_INICIO_LUZ = 8
    HORA_FIN_LUZ = 20

    try:
        while True:
            # CHECK DE PARADA DE EMERGENCIA
            if GPIO.input(21) == GPIO.LOW:
                print("\n!!! PARADA DE EMERGENCIA ACTIVADA !!!")
                break

            ahora = datetime.now()
            print(f"\n[{ahora.strftime('%H:%M:%S')}] --- Ciclo ---")

            # 1. LECTURAS
            try: lux = sensor_bh1750.lux
            except: lux = 0
            hum_suelo = leer_humedad_suelo_pct(adc_humedad)
            if dht_device: temp_amb, hum_amb = leer_ambiente(dht_device)
            else: temp_amb, hum_amb = 0, 0

            print(f"Ambiente: {temp_amb:.1f}C / {hum_amb:.0f}% | Suelo: {hum_suelo}% | Lux: {lux:.0f}")

            # 2. LOGICA LUCES (USANDO HORA REAL)
            # Verificamos si la hora actual esta dentro del rango permitido
            hora_actual = ahora.hour
            estado_luz = "OFF"

            es_de_dia = (hora_actual >= HORA_INICIO_LUZ) and (hora_actual < HORA_FIN_LUZ)

            if es_de_dia:
                # Estamos en horario diurno, verificamos si hace falta luz artificial
                if lux < UMBRAL_LUX:
                    GPIO.output(PIN_LUZ, GPIO.LOW) # Prender
                    estado_luz = "ON"
                else:
                    GPIO.output(PIN_LUZ, GPIO.HIGH) # Apagar (Hay sol natural)
                    estado_luz = "OFF (Sol)"
            else:
                # Es de noche (fuera de horario), apagar todo
                GPIO.output(PIN_LUZ, GPIO.HIGH)
                estado_luz = "OFF (Noche)"

            # 3. LOGICA RIEGO
            estado_riego_str = "OFF"
            riego_activo_bool = False
            
            if hum_suelo < UMBRAL_SECO:
                print("  ! RIEGO ACTIVADO !")
                GPIO.output(PIN_LED_ALERTA, GPIO.HIGH)
                GPIO.output(PIN_VALVULA, GPIO.LOW)
                time.sleep(0.5)
                GPIO.output(PIN_BOMBA, GPIO.LOW)
                time.sleep(5)
                GPIO.output(PIN_BOMBA, GPIO.HIGH)
                time.sleep(0.5)
                GPIO.output(PIN_VALVULA, GPIO.HIGH)
                estado_riego_str = "REGANDO"
                riego_activo_bool = True
            else:
                GPIO.output(PIN_LED_ALERTA, GPIO.LOW)

            # 4. GUARDADO DE DATOS
            guardar_excel([
                ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"),
                int(lux), hum_suelo, temp_amb, hum_amb, estado_luz, estado_riego_str
            ])
            
            subir_datos_iot(int(lux), hum_suelo, temp_amb, hum_amb, riego_activo_bool)

            # 5. TIEMPO
            time.sleep(INTERVALO_LECTURA)

    except KeyboardInterrupt:
        print("\nSalida por Teclado.")
    finally:
        if dht_device: dht_device.exit()
        GPIO.cleanup()
        print("GPIO Liberados.")

if __name__ == "__main__":
    main()
