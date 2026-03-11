# -*- coding: utf-8 -*-
import time
import board
import busio
import csv
import os
import adafruit_bh1750
from adafruit_pcf8591.pcf8591 import PCF8591
from adafruit_pcf8591.analog_in import AnalogIn
import RPi.GPIO as GPIO
from datetime import datetime

# ==========================================
#        CONFIGURACION DE HARDWARE
# ==========================================
# Pines GPIO (Basado en tu Cultivo 1 y Luz 1)
PIN_BOMBA = 23
PIN_VALVULA = 16         # Tu antiguo 'pin_solenoide' del Cultivo 1
PIN_SENSOR_POWER = 27    # Tu antiguo 'pin_power' del Cultivo 1
PIN_LUZ = 26             # Tu antiguo 'pin_gpio' de Luz 1
PIN_LED_ALERTA = 24      # Nuevo LED indicador de "Necesito Riego"

# Configuracin I2C
CANAL_ADC = 3            # Canal del PCF8591 donde esta el sensor

# ==========================================
#        CONFIGURACION DE LOGICA
# ==========================================
#INTERVALO_LECTURA = 10   # Segundos entre mediciones (Prueba)
INTERVALO_LECTURA = 3600 # <--- Medicion cada 1hs
 
#Umbrales (Tus valores confirmados)
UMBRAL_LUX = 500
UMBRAL_SECO = 50         # % de humedad
RAW_SECO = 160           # Valor calibrado con tierra seca (0%)
RAW_MOJADO = 8           # Valor calibrado (100%)

# Fotoperiodo
HORAS_LUZ_MAXIMAS = 12
SEGUNDOS_EN_HORA = 3600  # Usar 3600 para vida real
# SEGUNDOS_EN_HORA = 10  # <--- Usar 10 para probar rapido que corta a las "12 horas"

NOMBRE_ARCHIVO = "registro_tesis.csv"

# ==========================================
#        FUNCIONES
# ==========================================
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    # Salidas (Logica Negativa o Positiva segun tus reles)
    GPIO.setup(PIN_BOMBA, GPIO.OUT, initial=GPIO.HIGH)    # Asumo HIGH = Apagado (Rele)
    GPIO.setup(PIN_VALVULA, GPIO.OUT, initial=GPIO.HIGH)  # Asumo HIGH = Cerrado
    GPIO.setup(PIN_LUZ, GPIO.OUT, initial=GPIO.HIGH)      # Asumo HIGH = Apagado
    
    # Pines de Control (Logica Positiva)
    GPIO.setup(PIN_SENSOR_POWER, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_LED_ALERTA, GPIO.OUT, initial=GPIO.LOW)
    print("GPIO configurados correctamente.")
    
def leer_humedad_pct(canal_adc):
    try:
        GPIO.output(PIN_SENSOR_POWER, GPIO.HIGH)
        time.sleep(0.2)
        raw = canal_adc.value
        GPIO.output(PIN_SENSOR_POWER, GPIO.LOW)
        
        lectura_8bit = int(raw / 256)
        
        # --- AGREGA ESTA LINEA AQUI ---
        print(f"DEBUG -> Valor RAW: {lectura_8bit}") 
        # ------------------------------

        # Mapeo usando TUS valores confirmados (160 y 8)
        humedad_pct = int((lectura_8bit - RAW_SECO) * (100 - 0) / (RAW_MOJADO - RAW_SECO) + 0)
        
        return max(0, min(100, humedad_pct))
    except Exception as e:
        print(f"Error leyendo sensor: {e}")
        return 0

def guardar_excel(datos):
    existe = os.path.isfile(NOMBRE_ARCHIVO)
    try:
        with open(NOMBRE_ARCHIVO, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not existe:
                writer.writerow(["Fecha", "Hora", "Lux", "Humedad %", "Luz Estado", "Riego Estado", "Horas Luz Acum"])
            writer.writerow(datos)
            print("-> Guardado en Excel.")
    except Exception as e:
        print(f"Error guardando Excel: {e}")

# ==========================================
#        MAIN
# ==========================================
def main():
    print("--- INICIANDO SISTEMA UNIFICADO ---")
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pcf = PCF8591(i2c)
        sensor_bh1750 = adafruit_bh1750.BH1750(i2c)
        adc_humedad = AnalogIn(pcf, CANAL_ADC)
    except Exception as e:
        print(f"ERROR CRITICO HARDWARE: {e}")
        return

    setup_gpio()

    # Variables de tiempo
    segundos_acumulados = 0
    horas_luz_hoy = 0.0

    try:
        while True:
            ahora = datetime.now()
            print(f"\n[{ahora.strftime('%H:%M:%S')}] --- Ciclo ---")
            

            # 1. Lectura Sensores
            try:
                lux = sensor_bh1750.lux
            except:
                lux = 0
            
            hum = leer_humedad_pct(adc_humedad)
            
            print(f"Lecturas -> Luz: {lux:.0f} lx | Humedad: {hum}%")

            # 2. Logica Luces (12 Horas)
            horas_pasadas = segundos_acumulados / SEGUNDOS_EN_HORA
            estado_luz = "OFF"
            
            if horas_pasadas < HORAS_LUZ_MAXIMAS:
                # Estamos en la ventana de luz (Dia)
                if lux < UMBRAL_LUX:
                    GPIO.output(PIN_LUZ, GPIO.LOW) # Prender (Rele Low Trigger)
                    estado_luz = "ON"
                else:
                    GPIO.output(PIN_LUZ, GPIO.HIGH) # Apagar (Hay sol)
                    estado_luz = "OFF (Sol)"
            else:
                # Ya pasaron las 12 horas (Noche)
                GPIO.output(PIN_LUZ, GPIO.HIGH)
                estado_luz = "OFF (Noche)"

            # Contar horas reales de luz recibida
            if estado_luz == "ON" or lux > UMBRAL_LUX:
                horas_luz_hoy += (INTERVALO_LECTURA / 3600.0)

            # 3. Logica Riego + LED
            estado_riego = "OFF"
            if hum < UMBRAL_SECO:
                print("  ! TIERRA SECA ! -> Iniciando Riego...")
                GPIO.output(PIN_LED_ALERTA, GPIO.HIGH) # Prender LED Rojo
                
                # Secuencia Riego
                GPIO.output(PIN_VALVULA, GPIO.LOW)  # Abrir
                time.sleep(0.5)
                GPIO.output(PIN_BOMBA, GPIO.LOW)    # Prender Bomba
                time.sleep(5)                       # Tiempo de riego (Ajustable)
                GPIO.output(PIN_BOMBA, GPIO.HIGH)   # Apagar Bomba
                time.sleep(0.5)
                GPIO.output(PIN_VALVULA, GPIO.HIGH) # Cerrar
                
                estado_riego = "REGANDO"
            else:
                GPIO.output(PIN_LED_ALERTA, GPIO.LOW) # Apagar LED
                print("  -> Tierra OK.")

            # 4. Guardar Datos
            guardar_excel([
                ahora.strftime("%Y-%m-%d"),
                ahora.strftime("%H:%M:%S"),
                int(lux),
                hum,
                estado_luz,
                estado_riego,
                round(horas_luz_hoy, 2)
            ])

            # 5. Control de Tiempo
            time.sleep(INTERVALO_LECTURA)
            segundos_acumulados += INTERVALO_LECTURA
            
            # Reinicio diario (Simulado a las 24h de ejecucion)
            if segundos_acumulados >= (24 * SEGUNDOS_EN_HORA):
                print("--- NUEVO DIA (RESET) ---")
                segundos_acumulados = 0
                horas_luz_hoy = 0

    except KeyboardInterrupt:
        print("\nSaliendo...")
    finally:
        GPIO.cleanup()
        print("GPIO Liberados.")

if __name__ == "__main__":
    main()
