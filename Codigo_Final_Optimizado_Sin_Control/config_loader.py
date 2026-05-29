from pathlib import Path

try:
    import tomllib      #En caso que python no soporte la ultima version
except ModuleNotFoundError:
    import tomli as tomllib

from models import (
    GlobalConfig,
    BombaConfig,
    ThingSpeakFieldsConfig,
    ThingSpeakConfig,
    I2CConfig,
    ADCConfig,
    SensorHumedadConfig,
    BH1750Config,
    DHTConfig,
    ActuadorConfig,
    MacetaConfig,
    SystemConfig,
)


def cargar_configuracion(ruta_config: str = "config.toml") -> SystemConfig:
    ruta = Path(ruta_config)

    if not ruta.exists():
        raise FileNotFoundError(f"No se encontro el archivo de configuracion: {ruta_config}")

    with open(ruta, "rb") as f:
        data = tomllib.load(f)

    config = _parsear_configuracion(data)
    _validar_configuracion(config)

    return config


def _parsear_configuracion(data: dict) -> SystemConfig:
    global_data = data["global"]
    bomba_data = data["bomba"]
    thingspeak_data = data["thingspeak"]
    i2c_data = data["i2c"]
    adc_data = data["adc"]
    macetas_data = data["macetas"]

    global_config = GlobalConfig(
        intervalo_lectura_seg=global_data["intervalo_lectura_seg"],
        raw_seco=global_data["raw_seco"],
        raw_mojado=global_data["raw_mojado"],
        discrepancia_humedad_pct=global_data["discrepancia_humedad_pct"],
        delay_post_bomba_seg=global_data["delay_post_bomba_seg"],
        archivo_csv=global_data["archivo_csv"],
    )

    bomba = BombaConfig(
        gpio=bomba_data["gpio"],
        activa_bajo=bomba_data["activa_bajo"],
        enabled=bomba_data["enabled"],
    )

    fields_data = thingspeak_data["fields"]
    thingspeak_fields = ThingSpeakFieldsConfig(
        humedad_suelo_maceta1=fields_data["humedad_suelo_maceta1"],
        humedad_suelo_maceta2=fields_data["humedad_suelo_maceta2"],
        lux_maceta1=fields_data["lux_maceta1"],
        lux_maceta2=fields_data["lux_maceta2"],
        temperatura_maceta1=fields_data["temperatura_maceta1"],
        temperatura_maceta2=fields_data["temperatura_maceta2"],
        humedad_ambiente_maceta1=fields_data["humedad_ambiente_maceta1"],
        humedad_ambiente_maceta2=fields_data["humedad_ambiente_maceta2"],
    )

    thingspeak = ThingSpeakConfig(
        enabled=thingspeak_data["enabled"],
        api_key=thingspeak_data["api_key"],
        url=thingspeak_data["url"],
        fields=thingspeak_fields,
    )

    i2c = I2CConfig(
        enabled=i2c_data["enabled"],
    )

    adcs = {}
    for nombre_adc, adc_cfg in adc_data.items():
        adcs[nombre_adc] = ADCConfig(
            nombre=nombre_adc,
            tipo=adc_cfg["tipo"],
            direccion=adc_cfg["direccion"],
            enabled=adc_cfg["enabled"],
        )

    macetas = {}
    for nombre_maceta, maceta_data in macetas_data.items():
        sensor_humedad_1 = SensorHumedadConfig(
            enabled=maceta_data["humedad_suelo"]["sensor1"]["enabled"],
            adc=maceta_data["humedad_suelo"]["sensor1"]["adc"],
            canal=maceta_data["humedad_suelo"]["sensor1"]["canal"],
        )

        sensor_humedad_2 = SensorHumedadConfig(
            enabled=maceta_data["humedad_suelo"]["sensor2"]["enabled"],
            adc=maceta_data["humedad_suelo"]["sensor2"]["adc"],
            canal=maceta_data["humedad_suelo"]["sensor2"]["canal"],
        )

        bh1750 = BH1750Config(
            enabled=maceta_data["bh1750"]["enabled"],
            direccion=maceta_data["bh1750"]["direccion"],
        )

        dht = DHTConfig(
            enabled=maceta_data["dht"]["enabled"],
            tipo=maceta_data["dht"]["tipo"],
            gpio=maceta_data["dht"]["gpio"],
        )

        luz = ActuadorConfig(
            enabled=maceta_data["actuadores"]["luz"]["enabled"],
            gpio=maceta_data["actuadores"]["luz"]["gpio"],
            activa_bajo=maceta_data["actuadores"]["luz"]["activa_bajo"],
        )

        valvula = ActuadorConfig(
            enabled=maceta_data["actuadores"]["valvula"]["enabled"],
            gpio=maceta_data["actuadores"]["valvula"]["gpio"],
            activa_bajo=maceta_data["actuadores"]["valvula"]["activa_bajo"],
        )

        ventilador = ActuadorConfig(
            enabled=maceta_data["actuadores"]["ventilador"]["enabled"],
            gpio=maceta_data["actuadores"]["ventilador"]["gpio"],
            activa_bajo=maceta_data["actuadores"]["ventilador"]["activa_bajo"],
        )

        macetas[nombre_maceta] = MacetaConfig(
            nombre=maceta_data["nombre"],
            enabled=maceta_data["enabled"],
            umbral_humedad_suelo_pct=maceta_data["umbral_humedad_suelo_pct"],
            umbral_humedad_ambiente_pct=maceta_data["umbral_humedad_ambiente_pct"],
            umbral_temperatura_c=maceta_data["umbral_temperatura_c"],
            umbral_lux=maceta_data["umbral_lux"],
            modo_luz=maceta_data["modo_luz"],
            hora_inicio_luz=maceta_data["hora_inicio_luz"],
            hora_fin_luz=maceta_data["hora_fin_luz"],
            tiempo_riego_seg=maceta_data["tiempo_riego_seg"],
            sensor_power_gpio=maceta_data.get("sensor_power_gpio", -1),
            sensor_humedad_1=sensor_humedad_1,
            sensor_humedad_2=sensor_humedad_2,
            bh1750=bh1750,
            dht=dht,
            luz=luz,
            valvula=valvula,
            ventilador=ventilador,
        )

    return SystemConfig(
        global_config=global_config,
        bomba=bomba,
        thingspeak=thingspeak,
        i2c=i2c,
        adcs=adcs,
        macetas=macetas,
    )


def _validar_configuracion(config: SystemConfig) -> None:
    _validar_global(config)
    _validar_adcs(config)
    _validar_macetas(config)
    _validar_gpios(config)


def _validar_global(config: SystemConfig) -> None:
    g = config.global_config

    if g.intervalo_lectura_seg <= 0:
        raise ValueError("intervalo_lectura_seg debe ser mayor que 0")

    if g.raw_seco == g.raw_mojado:
        raise ValueError("raw_seco y raw_mojado no pueden ser iguales")

    if not (0 <= g.discrepancia_humedad_pct <= 100):
        raise ValueError("discrepancia_humedad_pct debe estar entre 0 y 100")

    if g.delay_post_bomba_seg < 0:
        raise ValueError("delay_post_bomba_seg no puede ser negativo")


def _validar_adcs(config: SystemConfig) -> None:
    direcciones = set()

    for nombre_adc, adc in config.adcs.items():
        if not adc.enabled:
            continue

        if adc.tipo != "PCF8591":
            raise ValueError(f"{nombre_adc}: tipo de ADC no soportado: {adc.tipo}")

        if adc.direccion in direcciones:
            raise ValueError(f"Direccion I2C repetida en ADC: {hex(adc.direccion)}")

        direcciones.add(adc.direccion)


def _validar_macetas(config: SystemConfig) -> None:
    for nombre_maceta, maceta in config.macetas.items():
        if maceta.modo_luz not in ("sensor", "horario"):
            raise ValueError(f"{nombre_maceta}: modo_luz invalido: {maceta.modo_luz}")

        if not (0 <= maceta.umbral_humedad_suelo_pct <= 100):
            raise ValueError(f"{nombre_maceta}: umbral_humedad_suelo_pct fuera de rango")

        if not (0 <= maceta.umbral_humedad_ambiente_pct <= 100):
            raise ValueError(f"{nombre_maceta}: umbral_humedad_ambiente_pct fuera de rango")

        if maceta.tiempo_riego_seg < 0:
            raise ValueError(f"{nombre_maceta}: tiempo_riego_seg no puede ser negativo")

        if not (0 <= maceta.hora_inicio_luz <= 23):
            raise ValueError(f"{nombre_maceta}: hora_inicio_luz fuera de rango")

        if not (0 <= maceta.hora_fin_luz <= 23):
            raise ValueError(f"{nombre_maceta}: hora_fin_luz fuera de rango")

        _validar_sensor_humedad(nombre_maceta, "sensor1", maceta.sensor_humedad_1, config)
        _validar_sensor_humedad(nombre_maceta, "sensor2", maceta.sensor_humedad_2, config)

        if maceta.bh1750.enabled and not config.i2c.enabled:
            raise ValueError(f"{nombre_maceta}: BH1750 habilitado pero I2C deshabilitado")

        if maceta.bh1750.enabled and maceta.modo_luz != "sensor":
            raise ValueError(f"{nombre_maceta}: si BH1750 esta habilitado, modo_luz deberia ser 'sensor'")

        if maceta.modo_luz == "sensor" and not maceta.bh1750.enabled:
            raise ValueError(f"{nombre_maceta}: modo_luz='sensor' requiere BH1750 habilitado")


def _validar_sensor_humedad(nombre_maceta: str, nombre_sensor: str, sensor, config: SystemConfig) -> None:
    if not sensor.enabled:
        return

    if sensor.adc not in config.adcs:
        raise ValueError(f"{nombre_maceta}.{nombre_sensor}: ADC inexistente: {sensor.adc}")

    adc = config.adcs[sensor.adc]

    if not adc.enabled:
        raise ValueError(f"{nombre_maceta}.{nombre_sensor}: ADC deshabilitado: {sensor.adc}")

    if not (0 <= sensor.canal <= 3):
        raise ValueError(f"{nombre_maceta}.{nombre_sensor}: canal ADC fuera de rango: {sensor.canal}")


def _validar_gpios(config: SystemConfig) -> None:
    gpios_usados = {}

    if config.bomba.enabled:
        gpios_usados[config.bomba.gpio] = "bomba"

    for nombre_maceta, maceta in config.macetas.items():
        actuadores = {
            "dht": maceta.dht,
            "luz": maceta.luz,
            "valvula": maceta.valvula,
            "ventilador": maceta.ventilador,
        }

        for nombre, item in actuadores.items():
            if not item.enabled:
                continue

            gpio = item.gpio
            origen = f"{nombre_maceta}.{nombre}"

            if gpio in gpios_usados:
                raise ValueError(f"GPIO repetido: {gpio} usado por {gpios_usados[gpio]} y {origen}")

            gpios_usados[gpio] = origen

        if maceta.sensor_power_gpio >= 0:
            gpio = maceta.sensor_power_gpio
            origen = f"{nombre_maceta}.sensor_power"

            if gpio in gpios_usados:
                raise ValueError(f"GPIO repetido: {gpio} usado por {gpios_usados[gpio]} y {origen}")

            gpios_usados[gpio] = origen
