from config_loader import cargar_configuracion
from hardware import HardwareManager

config = cargar_configuracion("config.toml")
hw = HardwareManager(config)

try:
    hw.inicializar()
    print("Hardware inicializado correctamente")

    raw = hw.leer_humedad_raw("adc1", 0)
    print("Humedad raw adc1 canal 0:", raw)

    lux = hw.leer_lux("maceta1")
    print("Lux maceta1:", lux)

    temp, hum = hw.leer_dht("maceta1")
    print("DHT maceta1:", temp, hum)

finally:
    hw.apagar_todo()
    hw.cleanup()
    print("GPIO liberados")