import time

from config_loader import cargar_configuracion
from hardware import HardwareManager

config = cargar_configuracion("config.toml")
hw = HardwareManager(config)

try:
    hw.inicializar()
    print("Prueba de actuadores iniciada")

    maceta1 = config.macetas["maceta1"]

    print("\nLuz maceta1 ON")
    hw.set_luz_maceta(maceta1, True)
    time.sleep(3)
    print("Luz maceta1 OFF")
    hw.set_luz_maceta(maceta1, False)
    time.sleep(1)

    print("\nVentilador maceta1 ON")
    hw.set_ventilador_maceta(maceta1, True)
    time.sleep(3)
    print("Ventilador maceta1 OFF")
    hw.set_ventilador_maceta(maceta1, False)
    time.sleep(1)

    print("\nValvula maceta1 ABIERTA")
    hw.set_valvula_maceta(maceta1, True)
    time.sleep(3)
    print("Valvula maceta1 CERRADA")
    hw.set_valvula_maceta(maceta1, False)
    time.sleep(1)

    print("\nBomba ON")
    hw.set_bomba(True)
    time.sleep(3)
    print("Bomba OFF")
    hw.set_bomba(False)

finally:
    hw.apagar_todo()
    hw.cleanup()
    print("\nGPIO liberados")
