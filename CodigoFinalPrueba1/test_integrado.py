from datetime import datetime

from config_loader import cargar_configuracion
from models import MacetaEstado
from control import procesar_maceta
from hardware import HardwareManager


def imprimir_estado(nombre_maceta, estado):
    print(f"\n--- Estado de {nombre_maceta} ---")
    print(f"Humedad raw 1: {estado.humedad_suelo_raw_1}")
    print(f"Humedad raw 2: {estado.humedad_suelo_raw_2}")
    print(f"Humedad 1: {estado.humedad_suelo_1_pct}")
    print(f"Humedad 2: {estado.humedad_suelo_2_pct}")
    print(f"Humedad promedio: {estado.humedad_suelo_promedio_pct}")
    print(f"Lux: {estado.lux}")
    print(f"Temperatura: {estado.temperatura_c}")
    print(f"Humedad ambiente: {estado.humedad_ambiente_pct}")
    print(f"Luz encendida: {estado.luz_encendida}")
    print(f"Ventilador encendido: {estado.ventilador_encendido}")
    print(f"Riego pendiente: {estado.riego_pendiente}")
    print(f"Alertas: {estado.alertas}")


config = cargar_configuracion("config.toml")
hw = HardwareManager(config)

try:
    hw.inicializar()
    print("Hardware inicializado correctamente")

    estados = {}

    for nombre_maceta, maceta in config.macetas.items():
        if not maceta.enabled:
            continue

        estado_anterior = MacetaEstado()

        raw1 = None
        raw2 = None
        lux = None
        temperatura_c = None
        humedad_ambiente_pct = None

        if maceta.sensor_humedad_1.enabled:
            raw1 = hw.leer_humedad_raw(
                maceta.sensor_humedad_1.adc,
                maceta.sensor_humedad_1.canal
            )

        if maceta.sensor_humedad_2.enabled:
            raw2 = hw.leer_humedad_raw(
                maceta.sensor_humedad_2.adc,
                maceta.sensor_humedad_2.canal
            )

        if maceta.bh1750.enabled:
            lux = hw.leer_lux(nombre_maceta)

        if maceta.dht.enabled:
            temperatura_c, humedad_ambiente_pct = hw.leer_dht(nombre_maceta)

        lecturas = {
            "humedad_raw_1": raw1,
            "humedad_raw_2": raw2,
            "lux": lux,
            "temperatura_c": temperatura_c,
            "humedad_ambiente_pct": humedad_ambiente_pct,
        }

        estado_nuevo = procesar_maceta(
            maceta=maceta,
            estado=estado_anterior,
            lecturas=lecturas,
            global_config=config.global_config,
            ahora=datetime.now()
        )

        hw.set_luz_maceta(maceta, estado_nuevo.luz_encendida)
        hw.set_ventilador_maceta(maceta, estado_nuevo.ventilador_encendido)

        estados[nombre_maceta] = estado_nuevo
        imprimir_estado(nombre_maceta, estado_nuevo)

finally:
    hw.apagar_todo()
    hw.cleanup()
    print("\nGPIO liberados")
