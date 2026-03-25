import csv
import os
import time
from datetime import datetime
from typing import Dict, Optional

import requests

from config_loader import cargar_configuracion
from control import procesar_maceta
from hardware import HardwareManager
from models import MacetaEstado, SystemState


def valor_csv(valor):
    return "" if valor is None else valor


def crear_estado_inicial(config) -> SystemState:
    estado = SystemState()

    for nombre_maceta, maceta in config.macetas.items():
        if maceta.enabled:
            estado.macetas[nombre_maceta] = MacetaEstado()

    return estado


def leer_maceta(hw: HardwareManager, maceta) -> Dict[str, Optional[float]]:
    raw1 = None
    raw2 = None
    lux = None
    temperatura_c = None
    humedad_ambiente_pct = None

    necesita_humedad = maceta.sensor_humedad_1.enabled or maceta.sensor_humedad_2.enabled

    if necesita_humedad and maceta.sensor_power_gpio >= 0:
        hw.set_sensor_power_maceta(maceta, True)
        time.sleep(2)

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

    if necesita_humedad and maceta.sensor_power_gpio >= 0:
        hw.set_sensor_power_maceta(maceta, False)

    if maceta.bh1750.enabled:
        lux = hw.leer_lux(maceta.nombre)

    if maceta.dht.enabled:
        temperatura_c, humedad_ambiente_pct = hw.leer_dht(maceta.nombre)

    return {
        "humedad_raw_1": raw1,
        "humedad_raw_2": raw2,
        "lux": lux,
        "temperatura_c": temperatura_c,
        "humedad_ambiente_pct": humedad_ambiente_pct,
    }

def imprimir_estado_maceta(nombre_maceta: str, estado: MacetaEstado) -> None:
    print(f"\n--- {nombre_maceta} ---")
    print(
        f"Suelo: {estado.humedad_suelo_1_pct} / {estado.humedad_suelo_2_pct} "
        f"(prom={estado.humedad_suelo_promedio_pct})"
    )
    print(
        f"Raw: {estado.humedad_suelo_raw_1} / {estado.humedad_suelo_raw_2}"
    )
    print(
        f"Lux: {estado.lux} | Temp: {estado.temperatura_c} | "
        f"HumAmb: {estado.humedad_ambiente_pct}"
    )
    print(
        f"Luz: {estado.luz_encendida} | Vent: {estado.ventilador_encendido} | "
        f"Riego: {estado.riego_pendiente}"
    )

    if estado.alertas:
        print("Alertas:")
        for alerta in estado.alertas:
            print(f" - {alerta}")


def guardar_csv(config, estados: Dict[str, MacetaEstado], ahora: datetime) -> None:
    archivo = config.global_config.archivo_csv
    existe = os.path.isfile(archivo)

    with open(archivo, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not existe:
            writer.writerow([
                "fecha",
                "hora",
                "maceta",
                "humedad_raw_1",
                "humedad_raw_2",
                "humedad_pct_1",
                "humedad_pct_2",
                "humedad_pct_promedio",
                "lux",
                "temperatura_c",
                "humedad_ambiente_pct",
                "luz_encendida",
                "ventilador_encendido",
                "riego_pendiente",
                "alertas",
            ])

        for nombre_maceta, estado in estados.items():
            writer.writerow([
                ahora.strftime("%Y-%m-%d"),
                ahora.strftime("%H:%M:%S"),
                nombre_maceta,
                valor_csv(estado.humedad_suelo_raw_1),
                valor_csv(estado.humedad_suelo_raw_2),
                valor_csv(estado.humedad_suelo_1_pct),
                valor_csv(estado.humedad_suelo_2_pct),
                valor_csv(estado.humedad_suelo_promedio_pct),
                valor_csv(estado.lux),
                valor_csv(estado.temperatura_c),
                valor_csv(estado.humedad_ambiente_pct),
                int(estado.luz_encendida),
                int(estado.ventilador_encendido),
                int(estado.riego_pendiente),
                " | ".join(estado.alertas),
            ])


def subir_thingspeak(config, estados: Dict[str, MacetaEstado]) -> None:
    if not config.thingspeak.enabled:
        return

    payload = {
        "api_key": config.thingspeak.api_key,
    }

    field_map = config.thingspeak.fields

    if "maceta1" in estados:
        e = estados["maceta1"]
        if e.humedad_suelo_promedio_pct is not None:
            payload[field_map.humedad_suelo_maceta1] = e.humedad_suelo_promedio_pct
        if e.lux is not None:
            payload[field_map.lux_maceta1] = round(e.lux, 2)
        if e.temperatura_c is not None:
            payload[field_map.temperatura_maceta1] = round(e.temperatura_c, 2)
        if e.humedad_ambiente_pct is not None:
            payload[field_map.humedad_ambiente_maceta1] = round(e.humedad_ambiente_pct, 2)

    if "maceta2" in estados:
        e = estados["maceta2"]
        if e.humedad_suelo_promedio_pct is not None:
            payload[field_map.humedad_suelo_maceta2] = e.humedad_suelo_promedio_pct
        if e.lux is not None:
            payload[field_map.lux_maceta2] = round(e.lux, 2)
        if e.temperatura_c is not None:
            payload[field_map.temperatura_maceta2] = round(e.temperatura_c, 2)
        if e.humedad_ambiente_pct is not None:
            payload[field_map.humedad_ambiente_maceta2] = round(e.humedad_ambiente_pct, 2)

    if len(payload) == 1:
        return

    try:
        respuesta = requests.post(
            config.thingspeak.url,
            data=payload,
            timeout=5
        )
        if respuesta.status_code == 200:
            print(f"\nThingSpeak OK: {respuesta.text}")
        else:
            print(f"\nThingSpeak error HTTP: {respuesta.status_code}")
    except Exception as e:
        print(f"\nThingSpeak fallo: {e}")


def ejecutar_riego_secuencial(config, hw: HardwareManager, macetas_a_regar) -> None:
    for maceta in macetas_a_regar:
        print(f"\nRegando {maceta.nombre}")

        hw.set_valvula_maceta(maceta, True)
        time.sleep(0.5)

        hw.set_bomba(True)
        time.sleep(maceta.tiempo_riego_seg)

        hw.set_bomba(False)
        time.sleep(config.global_config.delay_post_bomba_seg)

        hw.set_valvula_maceta(maceta, False)


def main():
    config = cargar_configuracion("config.toml")
    estado_sistema = crear_estado_inicial(config)
    hw = HardwareManager(config)

    print("Iniciando sistema")
    hw.inicializar()

    try:
        while True:
            ahora = datetime.now()
            print(f"\n===== Ciclo {ahora.strftime('%Y-%m-%d %H:%M:%S')} =====")

            estados_ciclo: Dict[str, MacetaEstado] = {}
            macetas_a_regar = []

            for nombre_maceta, maceta in config.macetas.items():
                if not maceta.enabled:
                    continue

                estado_anterior = estado_sistema.macetas[nombre_maceta]
                lecturas = leer_maceta(hw, maceta)

                nuevo_estado = procesar_maceta(
                    maceta=maceta,
                    estado=estado_anterior,
                    lecturas=lecturas,
                    global_config=config.global_config,
                    ahora=ahora
                )

                hw.set_luz_maceta(maceta, nuevo_estado.luz_encendida)
                hw.set_ventilador_maceta(maceta, nuevo_estado.ventilador_encendido)

                estados_ciclo[nombre_maceta] = nuevo_estado
                estado_sistema.macetas[nombre_maceta] = nuevo_estado

                if nuevo_estado.riego_pendiente:
                    macetas_a_regar.append(maceta)

                imprimir_estado_maceta(nombre_maceta, nuevo_estado)

            if macetas_a_regar:
                ejecutar_riego_secuencial(config, hw, macetas_a_regar)

            guardar_csv(config, estados_ciclo, ahora)
            subir_thingspeak(config, estados_ciclo)

            time.sleep(config.global_config.intervalo_lectura_seg)

    except KeyboardInterrupt:
        print("\nSalida por teclado")

    finally:
        hw.apagar_todo()
        hw.cleanup()
        print("Sistema detenido y GPIO liberados")


if __name__ == "__main__":
    main()
