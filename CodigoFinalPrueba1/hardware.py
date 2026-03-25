from typing import Optional, Dict, Any, Tuple
import time

import board
import busio
import RPi.GPIO as GPIO
import adafruit_dht
import adafruit_bh1750
from adafruit_pcf8591.pcf8591 import PCF8591
from adafruit_pcf8591.analog_in import AnalogIn

from models import SystemConfig, MacetaConfig, ActuadorConfig


class HardwareManager:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.i2c = None
        self.adcs: Dict[str, Any] = {}
        self.bh1750: Dict[str, Any] = {}
        self.dht: Dict[str, Any] = {}

    def inicializar(self) -> None:
        self._inicializar_gpio()
        self._inicializar_i2c()
        self._inicializar_adcs()
        self._inicializar_bh1750()
        self._inicializar_dht()

    def _inicializar_gpio(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        if self.config.bomba.enabled:
            self._configurar_salida(
                self.config.bomba.gpio,
                self.config.bomba.activa_bajo,
                encendido=False
            )

        for maceta in self.config.macetas.values():
            if maceta.sensor_power_gpio >= 0:
                GPIO.setup(maceta.sensor_power_gpio, GPIO.OUT)
                GPIO.output(maceta.sensor_power_gpio, GPIO.LOW)

        for maceta in self.config.macetas.values():
            self._configurar_actuador(maceta.luz)
            self._configurar_actuador(maceta.valvula)
            self._configurar_actuador(maceta.ventilador)

    def _inicializar_i2c(self) -> None:
        if not self.config.i2c.enabled:
            return

        self.i2c = busio.I2C(board.SCL, board.SDA)

    def _inicializar_adcs(self) -> None:
        if self.i2c is None:
            return

        for nombre_adc, adc_cfg in self.config.adcs.items():
            if not adc_cfg.enabled:
                continue

            try:
                self.adcs[nombre_adc] = PCF8591(self.i2c, address=adc_cfg.direccion)
            except Exception:
                self.adcs[nombre_adc] = None

    def _inicializar_bh1750(self) -> None:
        if self.i2c is None:
            return

        for nombre_maceta, maceta in self.config.macetas.items():
            if not maceta.enabled or not maceta.bh1750.enabled:
                continue

            try:
                self.bh1750[nombre_maceta] = adafruit_bh1750.BH1750(
                    self.i2c,
                    address=maceta.bh1750.direccion
                )
            except Exception:
                self.bh1750[nombre_maceta] = None

    def _inicializar_dht(self) -> None:
        for nombre_maceta, maceta in self.config.macetas.items():
            if not maceta.enabled or not maceta.dht.enabled:
                continue

            try:
                pin = self._mapear_pin_board(maceta.dht.gpio)
                self.dht[nombre_maceta] = adafruit_dht.DHT22(pin, use_pulseio=False)
            except Exception:
                self.dht[nombre_maceta] = None

    def _configurar_actuador(self, actuador: ActuadorConfig) -> None:
        if not actuador.enabled:
            return

        self._configurar_salida(
            gpio=actuador.gpio,
            activa_bajo=actuador.activa_bajo,
            encendido=False
        )

    def _configurar_salida(self, gpio: int, activa_bajo: bool, encendido: bool) -> None:
        GPIO.setup(gpio, GPIO.OUT)
        GPIO.output(gpio, self._valor_salida(activa_bajo, encendido))

    def _valor_salida(self, activa_bajo: bool, encendido: bool) -> int:
        if activa_bajo:
            return GPIO.LOW if encendido else GPIO.HIGH
        return GPIO.HIGH if encendido else GPIO.LOW

    def _mapear_pin_board(self, gpio_bcm: int):
        nombre = f"D{gpio_bcm}"
        if not hasattr(board, nombre):
            raise ValueError(f"No existe board.{nombre} para GPIO BCM {gpio_bcm}")
        return getattr(board, nombre)

    def set_sensor_power_maceta(self, maceta: MacetaConfig, encendido: bool) -> None:
        if maceta.sensor_power_gpio < 0:
            return

        GPIO.output(maceta.sensor_power_gpio, GPIO.HIGH if encendido else GPIO.LOW)

    def leer_humedad_raw(self, adc_nombre: str, canal: int, muestras: int = 5) -> Optional[int]:
        adc = self.adcs.get(adc_nombre)
        if adc is None:
            return None

        try:
            canal_adc = AnalogIn(adc, canal)

            _ = canal_adc.value
            time.sleep(0.1)

            valores = []
            for _i in range(muestras):
                valores.append(canal_adc.value)
                time.sleep(0.05)

            raw16 = sum(valores) / len(valores)
            raw8 = int(raw16 / 256)
            return raw8
        except Exception:
            return None

    def leer_lux(self, nombre_maceta: str) -> Optional[float]:
        sensor = self.bh1750.get(nombre_maceta)
        if sensor is None:
            return None

        try:
            return float(sensor.lux)
        except Exception:
            return None

    def leer_dht(self, nombre_maceta: str) -> Tuple[Optional[float], Optional[float]]:
        sensor = self.dht.get(nombre_maceta)
        if sensor is None:
            return None, None

        try:
            temperatura = sensor.temperature
            humedad = sensor.humidity

            if temperatura is None or humedad is None:
                return None, None

            return float(temperatura), float(humedad)
        except Exception:
            return None, None

    def set_bomba(self, encendida: bool) -> None:
        if not self.config.bomba.enabled:
            return

        GPIO.output(
            self.config.bomba.gpio,
            self._valor_salida(self.config.bomba.activa_bajo, encendida)
        )

    def set_luz_maceta(self, maceta: MacetaConfig, encendida: bool) -> None:
        if not maceta.luz.enabled:
            return

        GPIO.output(
            maceta.luz.gpio,
            self._valor_salida(maceta.luz.activa_bajo, encendida)
        )

    def set_valvula_maceta(self, maceta: MacetaConfig, abierta: bool) -> None:
        if not maceta.valvula.enabled:
            return

        GPIO.output(
            maceta.valvula.gpio,
            self._valor_salida(maceta.valvula.activa_bajo, abierta)
        )

    def set_ventilador_maceta(self, maceta: MacetaConfig, encendido: bool) -> None:
        if not maceta.ventilador.enabled:
            return

        GPIO.output(
            maceta.ventilador.gpio,
            self._valor_salida(maceta.ventilador.activa_bajo, encendido)
        )

    def apagar_todo(self) -> None:
        self.set_bomba(False)

        for maceta in self.config.macetas.values():
            self.set_luz_maceta(maceta, False)
            self.set_valvula_maceta(maceta, False)
            self.set_ventilador_maceta(maceta, False)
            self.set_sensor_power_maceta(maceta, False)

    def cleanup(self) -> None:
        for sensor in self.dht.values():
            if sensor is not None:
                try:
                    sensor.exit()
                except Exception:
                    pass

        GPIO.cleanup()
