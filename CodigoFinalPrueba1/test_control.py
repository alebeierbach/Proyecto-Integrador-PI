from datetime import datetime

from config_loader import cargar_configuracion
from models import MacetaEstado
from control import procesar_maceta


def imprimir_resultado(titulo, estado):
    print(f"\n--- {titulo} ---")
    print(f"Humedad 1: {estado.humedad_suelo_1_pct}")
    print(f"Humedad 2: {estado.humedad_suelo_2_pct}")
    print(f"Humedad promedio: {estado.humedad_suelo_promedio_pct}")
    print(f"Raw 1: {estado.humedad_suelo_raw_1}")
    print(f"Raw 2: {estado.humedad_suelo_raw_2}")
    print(f"Lux: {estado.lux}")
    print(f"Temperatura: {estado.temperatura_c}")
    print(f"Humedad ambiente: {estado.humedad_ambiente_pct}")
    print(f"Luz encendida: {estado.luz_encendida}")
    print(f"Ventilador encendido: {estado.ventilador_encendido}")
    print(f"Riego pendiente: {estado.riego_pendiente}")
    print(f"Alertas: {estado.alertas}")


config = cargar_configuracion("config.toml")
maceta = config.macetas["maceta1"]

# Caso 1: horario activo + lux bajo
estado_anterior = MacetaEstado()
lecturas = {
    "humedad_raw_1": 120,
    "humedad_raw_2": 125,
    "lux": 300,
    "temperatura_c": 25.0,
    "humedad_ambiente_pct": 60.0,
}
ahora = datetime(2026, 1, 1, 20, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 1 - Horario activo + lux bajo", estado)

# Caso 2: horario activo + lux alto
estado_anterior = MacetaEstado()
lecturas = {
    "humedad_raw_1": 120,
    "humedad_raw_2": 125,
    "lux": 700,
    "temperatura_c": 25.0,
    "humedad_ambiente_pct": 60.0,
}
ahora = datetime(2026, 1, 1, 20, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 2 - Horario activo + lux alto", estado)

# Caso 3: horario inactivo
estado_anterior = MacetaEstado()
lecturas = {
    "humedad_raw_1": 120,
    "humedad_raw_2": 125,
    "lux": 300,
    "temperatura_c": 25.0,
    "humedad_ambiente_pct": 60.0,
}
ahora = datetime(2026, 1, 1, 12, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 3 - Horario inactivo", estado)

# Caso 4: lux invalido y mantener ultimo estado encendido
estado_anterior = MacetaEstado(luz_encendida=True)
lecturas = {
    "humedad_raw_1": 120,
    "humedad_raw_2": 125,
    "lux": None,
    "temperatura_c": 25.0,
    "humedad_ambiente_pct": 60.0,
}
ahora = datetime(2026, 1, 1, 20, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 4 - Lux invalido, mantener luz encendida", estado)

# Caso 5: un sensor de humedad falla
estado_anterior = MacetaEstado()
lecturas = {
    "humedad_raw_1": 120,
    "humedad_raw_2": None,
    "lux": 300,
    "temperatura_c": 25.0,
    "humedad_ambiente_pct": 60.0,
}
ahora = datetime(2026, 1, 1, 20, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 5 - Falla un sensor de humedad", estado)

# Caso 6: fallan ambos sensores de humedad
estado_anterior = MacetaEstado()
lecturas = {
    "humedad_raw_1": None,
    "humedad_raw_2": None,
    "lux": 300,
    "temperatura_c": 25.0,
    "humedad_ambiente_pct": 60.0,
}
ahora = datetime(2026, 1, 1, 20, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 6 - Fallan ambos sensores de humedad", estado)

# Caso 7: DHT invalido
estado_anterior = MacetaEstado()
lecturas = {
    "humedad_raw_1": 120,
    "humedad_raw_2": 125,
    "lux": 300,
    "temperatura_c": None,
    "humedad_ambiente_pct": None,
}
ahora = datetime(2026, 1, 1, 20, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 7 - DHT invalido", estado)

# Caso 8: temperatura alta
estado_anterior = MacetaEstado()
lecturas = {
    "humedad_raw_1": 120,
    "humedad_raw_2": 125,
    "lux": 300,
    "temperatura_c": 33.0,
    "humedad_ambiente_pct": 60.0,
}
ahora = datetime(2026, 1, 1, 20, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 8 - Temperatura alta", estado)

# Caso 9: humedad ambiente alta
estado_anterior = MacetaEstado()
lecturas = {
    "humedad_raw_1": 120,
    "humedad_raw_2": 125,
    "lux": 300,
    "temperatura_c": 25.0,
    "humedad_ambiente_pct": 90.0,
}
ahora = datetime(2026, 1, 1, 20, 0, 0)

estado = procesar_maceta(
    maceta=maceta,
    estado=estado_anterior,
    lecturas=lecturas,
    global_config=config.global_config,
    ahora=ahora
)
imprimir_resultado("Caso 9 - Humedad ambiente alta", estado)