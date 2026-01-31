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
#INTERVALO_LECTURA = 20  
INTERVALO_LECTURA = 3600 # Para produccion (1 hora)

UMBRAL_LUX = 500
UMBRAL_SECO = 50
RAW_SECO = 160 
RAW_MOJADO = 8 

# Horario de luz
HORA_INICIO_LUZ = 8
HORA_FIN_LUZ = 17

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
    GPIO.setup(PIN_LUZ, GPIO.OUT, initial=GPIO.HIGH) # Arranca apagado
    GPIO.setup(PIN_SENSOR_POWER, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_LED_ALERTA, GPIO.OUT, initial=GPIO.LOW)
    # Boton de Panico
    GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def leer_humedad_suelo_pct(canal_adc): 
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
                # Agregamos columas para diferenciar Luz Natural vs Total
                writer.writerow(["Fecha", "Hora", "Lux Natural", "Lux Total", "Hum Suelo %", "Temp Amb C", "Hum Amb %", "Luz Estado", "Riego Estado"])
            writer.writerow(datos)
            print("-> Guardado Local (Excel)")
    except:
        print("Error Excel")

def subir_datos_iot(lux_total, lux_natural, hum_suelo, temp_amb, hum_amb, esta_regando):
    try:
        payload = {
            'api_key': THINGSPEAK_API_KEY,
            'field1': lux_total,   # Luz que recibe la planta (con o sin foco)
            'field2': hum_suelo,
            'field3': temp_amb,
            'field4': hum_amb,
            'field5': 1 if esta_regando else 0,
            'field6': lux_natural  # <--- NUEVO CAMPO: Luz del sol real
        }
        respuesta = requests.post(URL_THINGSPEAK, data=payload, timeout=5)
        
        if respuesta.status_code == 200:
            print(f"-> SUBIDO A NUBE (Entry: {respuesta.text})")
        else:
            print(f"Error Nube: {respuesta.status_code}")
    except Exception as e:
        print(f"Falla de Internet: {e}")

# ==========================================
#        MAIN
# ==========================================
def main():
    print("--- INICIANDO SISTEMA IOT COMPLETO ---")
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pcf = PCF8591(i2c)
        sensor_bh1750 = adafruit_bh1750.BH1750(i2c)
        adc_humedad = AnalogIn(pcf, CANAL_ADC)
        try: dht_device = adafruit_dht.DHT22(PIN_DHT)
        except: dht_device = None
    except Exception as e:
        print(f"ERROR HARDWARE: {e}")
        return

    setup_gpio()

    try:
        while True:
            # CHECK DE PARADA DE EMERGENCIA
            if GPIO.input(21) == GPIO.LOW:
                print("\n!!! PARADA DE EMERGENCIA !!!")
                break

            ahora = datetime.now()
            print(f"\n[{ahora.strftime('%H:%M:%S')}] --- Ciclo ---")

            # -------------------------------------------------------
            # 1. LOGICA DE LUZ INTELIGENTE (Natural vs Artificial)
            # -------------------------------------------------------
            
            # A. Apagamos foco y medimos Luz Natural
            GPIO.output(PIN_LUZ, GPIO.HIGH) 
            time.sleep(1) # Esperamos que el sensor se estabilice sin foco
            try: lux_natural = sensor_bh1750.lux
            except: lux_natural = 0
            
                       # B. Decidimos Estado
            hora_actual = ahora.hour
            es_de_dia = (hora_actual >= HORA_INICIO_LUZ) and (hora_actual < HORA_FIN_LUZ)
            estado_luz = "OFF"

            if es_de_dia:
                if lux_natural < UMBRAL_LUX:
                    GPIO.output(PIN_LUZ, GPIO.LOW) # PRENDER FOCO
                    estado_luz = "ON"
                else:
                    estado_luz = "OFF (Sol)" # Ya hay sol, dejamos apagado
            else:
                estado_luz = "OFF (Noche)"

            # C. Medimos Luz Total (Lo que realmente recibe la planta)
            time.sleep(1) # Esperamos que el foco ilumine bien (si se prendio)
            try: lux_total = sensor_bh1750.lux
            except: lux_total = 0

            # -------------------------------------------------------
            # 2. OTRAS LECTURAS
            # -------------------------------------------------------
            hum_suelo = leer_humedad_suelo_pct(adc_humedad)
            if dht_device: temp_amb, hum_amb = leer_ambiente(dht_device)
            else: temp_amb, hum_amb = 0, 0

            print(f"Ambiente: {temp_amb:.1f}C/{hum_amb:.0f}% | Suelo: {hum_suelo}%")
            print(f"Luz Natural: {lux_natural:.0f} | Luz Total: {lux_total:.0f} ({estado_luz})")

            # -------------------------------------------------------
            # 3. LOGICA RIEGO
            # -------------------------------------------------------
            estado_riego_str = "OFF"
            riego_activo_bool = False
            
            if hum_suelo < UMBRAL_SECO:
                print(" ! RIEGO ACTIVADO !")
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

            # -------------------------------------------------------
            # 4. GUARDADO
            # -------------------------------------------------------
            # Guardamos ambas luces en Excel para tu analisis
            guardar_excel([
                ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"),
                int(lux_natural), int(lux_total), 
                hum_suelo, temp_amb, hum_amb, estado_luz, estado_riego_str
            ])
            
            # A la nube subimos el TOTAL (que es lo que le importa a la planta)
            subir_datos_iot(int(lux_total), int(lux_natural), hum_suelo, temp_amb, hum_amb, riego_activo_bool)

            # 5. ESPERA
            time.sleep(INTERVALO_LECTURA)

    except KeyboardInterrupt:
        print("\nSalida por Teclado.")
    finally:
        if dht_device: dht_device.exit()
        GPIO.cleanup()
        print("GPIO Liberados.")

if __name__ == "__main__":
    main()
