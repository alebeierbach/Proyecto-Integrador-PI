import time
import adafruit_dht
import board

DHT_PIN = board.D17 

dht = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

while True:
    try:
        temperatura = dht.temperature
        humedad = dht.humidity
        
        if temperatura is not None and humedad is not None:
            print("Temp={0:0.1f}C Hum={1:0.1f}%".format(temperatura, humedad))
        else:
            print("Falla en la lectura. Revisa el circuito")
            
    except RuntimeError as e:
        print(f"Error temporal de lectura DHT: {e}. Reintentando...")

    time.sleep(3)