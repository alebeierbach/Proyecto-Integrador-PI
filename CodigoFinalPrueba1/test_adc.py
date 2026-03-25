from config_loader import cargar_configuracion
from hardware import HardwareManager

config = cargar_configuracion("config.toml")
hw = HardwareManager(config)

try:
    hw.inicializar()
    print("ADC test\n")

    for canal in range(4):
        valor = hw.leer_humedad_raw("adc1", canal)
        print(f"Canal {canal}: {valor}")

finally:
    hw.apagar_todo()
    hw.cleanup()
    print("\nGPIO liberados")
