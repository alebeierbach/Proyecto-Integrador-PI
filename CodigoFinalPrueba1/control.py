from datetime import datetime
from typing import Optional, Tuple, List, Dict

from models import MacetaConfig, MacetaEstado, GlobalConfig


def esta_en_horario_activo(hora_actual: int, hora_inicio: int, hora_fin: int) -> bool:
    if hora_inicio < hora_fin:
        return hora_inicio <= hora_actual < hora_fin
    return hora_actual >= hora_inicio or hora_actual < hora_fin


def raw_a_porcentaje(raw_8bit: int, raw_seco: int, raw_mojado: int) -> int:
    humedad = int((raw_8bit - raw_seco) * 100 / (raw_mojado - raw_seco))
    return max(0, min(100, humedad))


def lectura_humedad_valida(raw_8bit: Optional[int]) -> bool:
    if raw_8bit is None:
        return False
    return 0 <= raw_8bit <= 255


def procesar_humedad_suelo(
    raw1: Optional[int],
    raw2: Optional[int],
    global_config: GlobalConfig
) -> Tuple[Optional[int], Optional[int], Optional[int], List[str]]:
    alertas = []

    val1 = lectura_humedad_valida(raw1)
    val2 = lectura_humedad_valida(raw2)

    hum1 = raw_a_porcentaje(raw1, global_config.raw_seco, global_config.raw_mojado) if val1 else None
    hum2 = raw_a_porcentaje(raw2, global_config.raw_seco, global_config.raw_mojado) if val2 else None

    if val1 and val2:
        promedio = int((hum1 + hum2) / 2)

        if abs(hum1 - hum2) > global_config.discrepancia_humedad_pct:
            alertas.append(f"Discrepancia alta entre sensores de humedad: {hum1}% vs {hum2}%")

        return hum1, hum2, promedio, alertas

    if val1 and not val2:
        alertas.append("Fallo sensor de humedad 2, se usa sensor 1")
        return hum1, None, hum1, alertas

    if val2 and not val1:
        alertas.append("Fallo sensor de humedad 1, se usa sensor 2")
        return None, hum2, hum2, alertas

    alertas.append("Fallo en ambos sensores de humedad de suelo")
    return None, None, None, alertas


def lectura_dht_valida(
    temperatura_c: Optional[float],
    humedad_ambiente_pct: Optional[float]
) -> bool:
    if temperatura_c is None or humedad_ambiente_pct is None:
        return False

    if not (-20 <= temperatura_c <= 80):
        return False

    if not (0 <= humedad_ambiente_pct <= 100):
        return False

    return True


def decidir_luz(
    maceta: MacetaConfig,
    lux: Optional[float],
    hora_actual: int,
    estado_anterior_luz: bool
) -> Tuple[bool, List[str]]:
    alertas = []
    en_horario = esta_en_horario_activo(
        hora_actual,
        maceta.hora_inicio_luz,
        maceta.hora_fin_luz
    )

    if not maceta.luz.enabled:
        return False, alertas

    if not en_horario:
        return False, alertas

    if maceta.modo_luz == "horario":
        return True, alertas

    if maceta.modo_luz == "sensor":
        if lux is None:
            alertas.append("No hay lectura valida de lux, se mantiene el ultimo estado de luz")
            return estado_anterior_luz, alertas

        return lux < maceta.umbral_lux, alertas

    alertas.append(f"Modo de luz desconocido: {maceta.modo_luz}")
    return False, alertas


def decidir_ventilacion(
    maceta: MacetaConfig,
    temperatura_c: Optional[float],
    humedad_ambiente_pct: Optional[float]
) -> Tuple[bool, List[str]]:
    alertas = []

    if not maceta.ventilador.enabled:
        return False, alertas

    if not lectura_dht_valida(temperatura_c, humedad_ambiente_pct):
        alertas.append("Lectura invalida de DHT, se omite logica de ventilacion")
        return False, alertas

    if temperatura_c > maceta.umbral_temperatura_c:
        alertas.append(f"Temperatura alta en {maceta.nombre}: {temperatura_c:.1f} C")
        return True, alertas

    if humedad_ambiente_pct > maceta.umbral_humedad_ambiente_pct:
        return True, alertas

    return False, alertas


def decidir_riego(
    maceta: MacetaConfig,
    humedad_suelo_promedio_pct: Optional[int]
) -> Tuple[bool, List[str]]:
    alertas = []

    if not maceta.valvula.enabled:
        return False, alertas

    if humedad_suelo_promedio_pct is None:
        alertas.append("Sin humedad de suelo valida, no se habilita riego automatico")
        return False, alertas

    if humedad_suelo_promedio_pct < maceta.umbral_humedad_suelo_pct:
        return True, alertas

    return False, alertas


def procesar_maceta(
    maceta: MacetaConfig,
    estado: MacetaEstado,
    lecturas: Dict[str, Optional[float]],
    global_config: GlobalConfig,
    ahora: Optional[datetime] = None
) -> MacetaEstado:
    if ahora is None:
        ahora = datetime.now()

    nuevo_estado = MacetaEstado()

    raw1 = lecturas.get("humedad_raw_1")
    raw2 = lecturas.get("humedad_raw_2")
    lux = lecturas.get("lux")
    temperatura_c = lecturas.get("temperatura_c")
    humedad_ambiente_pct = lecturas.get("humedad_ambiente_pct")

    hum1, hum2, promedio, alertas_humedad = procesar_humedad_suelo(
        raw1,
        raw2,
        global_config
    )

    nuevo_estado.humedad_suelo_raw_1 = raw1
    nuevo_estado.humedad_suelo_raw_2 = raw2
    nuevo_estado.humedad_suelo_1_pct = hum1
    nuevo_estado.humedad_suelo_2_pct = hum2
    nuevo_estado.humedad_suelo_promedio_pct = promedio

    if lectura_dht_valida(temperatura_c, humedad_ambiente_pct):
        nuevo_estado.temperatura_c = temperatura_c
        nuevo_estado.humedad_ambiente_pct = humedad_ambiente_pct
    else:
        nuevo_estado.temperatura_c = None
        nuevo_estado.humedad_ambiente_pct = None
        if maceta.dht.enabled:
            alertas_humedad.append("Lectura invalida de DHT")

    nuevo_estado.lux = lux

    luz_encendida, alertas_luz = decidir_luz(
        maceta,
        lux,
        ahora.hour,
        estado.luz_encendida
    )

    ventilador_encendido, alertas_vent = decidir_ventilacion(
        maceta,
        nuevo_estado.temperatura_c,
        nuevo_estado.humedad_ambiente_pct
    )

    riego_pendiente, alertas_riego = decidir_riego(
        maceta,
        nuevo_estado.humedad_suelo_promedio_pct
    )

    nuevo_estado.luz_encendida = luz_encendida
    nuevo_estado.ventilador_encendido = ventilador_encendido
    nuevo_estado.riego_pendiente = riego_pendiente
    nuevo_estado.alertas = alertas_humedad + alertas_luz + alertas_vent + alertas_riego

    return nuevo_estado