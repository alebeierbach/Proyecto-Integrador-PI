from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class GlobalConfig:
    intervalo_lectura_seg: int
    raw_seco: int
    raw_mojado: int
    discrepancia_humedad_pct: float
    delay_post_bomba_seg: float
    archivo_csv: str


@dataclass
class BombaConfig:
    gpio: int
    activa_bajo: bool
    enabled: bool


@dataclass
class ThingSpeakFieldsConfig:
    humedad_suelo_maceta1: str
    humedad_suelo_maceta2: str
    lux_maceta1: str
    lux_maceta2: str
    temperatura_maceta1: str
    temperatura_maceta2: str
    humedad_ambiente_maceta1: str
    humedad_ambiente_maceta2: str


@dataclass
class ThingSpeakConfig:
    enabled: bool
    api_key: str
    url: str
    fields: ThingSpeakFieldsConfig


@dataclass
class I2CConfig:
    enabled: bool


@dataclass
class ADCConfig:
    nombre: str
    tipo: str
    direccion: int
    enabled: bool


@dataclass
class SensorHumedadConfig:
    enabled: bool
    adc: str
    canal: int


@dataclass
class BH1750Config:
    enabled: bool
    direccion: int


@dataclass
class DHTConfig:
    enabled: bool
    tipo: str
    gpio: int


@dataclass
class ActuadorConfig:
    enabled: bool
    gpio: int
    activa_bajo: bool


@dataclass
class MacetaConfig:
    nombre: str
    enabled: bool
    umbral_humedad_suelo_pct: float
    umbral_humedad_ambiente_pct: float
    umbral_temperatura_c: float
    umbral_lux: float
    modo_luz: str
    hora_inicio_luz: int
    hora_fin_luz: int
    sensor_power_gpio: int
    tiempo_riego_seg: float
    sensor_humedad_1: SensorHumedadConfig
    sensor_humedad_2: SensorHumedadConfig
    bh1750: BH1750Config
    dht: DHTConfig
    luz: ActuadorConfig
    valvula: ActuadorConfig
    ventilador: ActuadorConfig


@dataclass
class SystemConfig:
    global_config: GlobalConfig
    bomba: BombaConfig
    thingspeak: ThingSpeakConfig
    i2c: I2CConfig
    adcs: Dict[str, ADCConfig]
    macetas: Dict[str, MacetaConfig]


@dataclass
class MacetaEstado:
    humedad_suelo_1_pct: Optional[float] = None
    humedad_suelo_2_pct: Optional[float] = None
    humedad_suelo_promedio_pct: Optional[float] = None
    humedad_suelo_raw_1: Optional[int] = None
    humedad_suelo_raw_2: Optional[int] = None
    lux: Optional[float] = None
    temperatura_c: Optional[float] = None
    humedad_ambiente_pct: Optional[float] = None
    luz_encendida: bool = False
    ventilador_encendido: bool = False
    riego_pendiente: bool = False
    alertas: List[str] = field(default_factory=list)


@dataclass
class SystemState:
    macetas: Dict[str, MacetaEstado] = field(default_factory=dict)
