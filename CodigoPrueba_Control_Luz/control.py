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

def calcular_y_controlar_dli(
    maceta: MacetaConfig, 
    lux_ambiente: Optional[float],
    dli_acumulado: float,
    luz_esta_encendida: bool,
    dt_segundos: float,
    ahora: datetime
) -> Tuple[bool, float, List[str]]:
    alertas = []
    
    # chequeamos que este habilitada la luz antes de cualquier cosa
    if not maceta.luz.enabled:
        return False, dli_acumulado, alertas

    # Extraemos la configuración diurna de la maceta
    hora_inicio = maceta.hora_inicio_dia
    hora_fin = maceta.hora_fin_dia
    dli_objetivo = maceta.dli_objetivo
    lux_foco = maceta.lux_foco
    F_L = maceta.factor_luminaria

    # Cálculo dinámico de PPFD y suma
    ppfd_foco = lux_foco * F_L
    ppfd_ambiente = (lux_ambiente * F_L) if lux_ambiente is not None else 0.0
    ppfd_total = ppfd_ambiente + (ppfd_foco if luz_esta_encendida else 0.0)

    # Integramos
    horas_transcurridas = dt_segundos / 3600.0
    incremento_dli = 0.0036 * ppfd_total * horas_transcurridas
    nuevo_dli = dli_acumulado + incremento_dli

    # --- EVALUACIÓN DEL FOTOPERIODO ---
    hora_actual_decimal = ahora.hour + (ahora.minute / 60.0)

    # Verificamos si estamos dentro del horario
    if hora_inicio <= hora_actual_decimal < hora_fin:
        en_horario = True
    else:
        en_horario = False

    if not en_horario:
        return False, nuevo_dli, alertas

    # 4. Calculamos Ti restante y evaluamos cuanto le falta
    Ti_restante = hora_fin - hora_actual_decimal
    dli_faltante = dli_objetivo - nuevo_dli
    
    if dli_faltante <= 0:
        return False, nuevo_dli, alertas # Ya se cumplió la meta de hoy
        
    dli_potencial_foco = 0.0036 * ppfd_foco * Ti_restante
    
    # Decisión final de encendido
    encender_foco = dli_potencial_foco <= dli_faltante
    
    return encender_foco, nuevo_dli, alertas


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
    dli_acumulado_actual: float = 0.0, 
    dt_segundos: float = 0.0,          
    ahora: Optional[datetime] = None
) -> Tuple[MacetaEstado, float]:       
    if ahora is None:
        ahora = datetime.now()

    nuevo_estado = MacetaEstado()

    # Extraer lecturas
    raw1 = lecturas.get("humedad_raw_1")
    raw2 = lecturas.get("humedad_raw_2")
    lux = lecturas.get("lux")              
    temperatura_c = lecturas.get("temperatura_c")
    humedad_ambiente_pct = lecturas.get("humedad_ambiente_pct")

    # Procesar humedad de suelo 
    hum1, hum2, promedio, alertas_humedad = procesar_humedad_suelo(
        raw1, raw2, global_config
    )

    nuevo_estado.humedad_suelo_raw_1 = raw1
    nuevo_estado.humedad_suelo_raw_2 = raw2
    nuevo_estado.humedad_suelo_1_pct = hum1
    nuevo_estado.humedad_suelo_2_pct = hum2
    nuevo_estado.humedad_suelo_promedio_pct = promedio
    nuevo_estado.lux = lux

    # Procesar DHT
    
    if lectura_dht_valida(temperatura_c, humedad_ambiente_pct):
        nuevo_estado.temperatura_c = temperatura_c
        nuevo_estado.humedad_ambiente_pct = humedad_ambiente_pct
    else:
        nuevo_estado.temperatura_c = None
        nuevo_estado.humedad_ambiente_pct = None
        if maceta.dht.enabled:
            alertas_humedad.append("Lectura invalida de DHT")

    # --- NUEVA LÓGICA DE LUZ CON DLI ---
    luz_encendida, nuevo_dli, alertas_luz = calcular_y_controlar_dli(
        maceta=maceta,
        lux_ambiente=lux,
        dli_acumulado=dli_acumulado_actual,
        luz_esta_encendida=estado.luz_encendida,
        dt_segundos=dt_segundos,
        ahora=ahora
    )
    
    nuevo_estado.dli_acumulado = nuevo_dli

    # Lógica de ventilación y riego
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

    return nuevo_estado, nuevo_dli