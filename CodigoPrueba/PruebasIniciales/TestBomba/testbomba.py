import RPi.GPIO as GPIO
import time

# --- CONFIGURACION DE PINES (BCM) ---
PIN_BOMBA = 23
PIN_VALVULA = 19  

def main():
    print("--- INICIANDO PRUEBA DE ACTUADORES ---")
    
    # 1. Configurar pines
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_BOMBA, GPIO.OUT)
    GPIO.setup(PIN_VALVULA, GPIO.OUT)

    # Everything starts off (HIGH)
    GPIO.output(PIN_BOMBA, GPIO.HIGH)
    GPIO.output(PIN_VALVULA, GPIO.HIGH)
    print("Sistema en reposo (Todo apagado).")
    time.sleep(1)

    # 2. Turn on pump for 1 sec
    print(f"\n[1] Encendiendo BOMBA (Pin {PIN_BOMBA})...")
    GPIO.output(PIN_BOMBA, GPIO.LOW)  # Relay ON
    time.sleep(1)                     
    GPIO.output(PIN_BOMBA, GPIO.HIGH) # Relay OFF
    print(" -> Bomba APAGADA.")

    # 3. Wait time
    print("\n[2] Esperando 4 segundos...")
    for i in range(4, 0, -1):
        print(f" {i}...", end="", flush=True)
        time.sleep(1)
    print(" Listo!")

    # 4. Turn on Valvula Solenoide
    print(f"\n[3] Encendiendo VALVULA (Pin {PIN_VALVULA})...")
    GPIO.output(PIN_VALVULA, GPIO.LOW) # Relay ON
    
    # Turn on for 2 sec
    time.sleep(2) 
    
    GPIO.output(PIN_VALVULA, GPIO.HIGH) # Relay OFF
    print(" -> Valvula APAGADA.")

    print("\n--- PRUEBA FINALIZADA EXITOSAMENTE ---")

try:
    main()
except KeyboardInterrupt:
    print("\nCancelado por usuario.")
finally:
    GPIO.cleanup()
    print("GPIOs liberados.")
