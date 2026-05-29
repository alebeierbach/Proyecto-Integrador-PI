import pandas as pd
import matplotlib.pyplot as plt

# 1. Carga de los datos
# Se asume que el archivo se llama 'telemetria.csv' y esta en la misma carpeta
df = pd.read_csv('telemetria2.csv')

# 2. Preprocesamiento temporal
# Unificamos las columnas de Fecha y Hora en un solo objeto datetime
df['Tiempo'] = pd.to_datetime(df['Fecha'] + ' ' + df['Hora'])

# 3. Preprocesamiento de variables logicas (Actuadores)
# Mapeamos los estados de texto a valores binarios (1 = Encendido, 0 = Apagado)
mapeo_luz = {'ON': 1, 'OFF': 0, 'OFF (Noche)': 0}
mapeo_riego = {'ON': 1, 'OFF': 0, 'REGANDO': 1}

df['Luz Estado'] = df['Luz Estado'].map(mapeo_luz).fillna(0)
df['Riego Estado'] = df['Riego Estado'].map(mapeo_riego).fillna(0)

# 4. Configuracion del lienzo y los subgraficos
# Creamos 4 graficos apilados que comparten el mismo eje X (Tiempo)
fig, axs = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
fig.suptitle('Analisis Dinamico de Telemetria del Prototipo', fontsize=16)

# Subgrafico 1: Variables de Iluminacion
axs[0].plot(df['Tiempo'], df['Lux Total'], label='Lux Total', color='#FF8C00')
axs[0].plot(df['Tiempo'], df['Lux Natural'], label='Lux Natural', color='#FFD700', alpha=0.7)
axs[0].set_ylabel('Iluminacion (Lux)')
axs[0].legend(loc='upper right')
axs[0].grid(True, linestyle=':', alpha=0.7)

# Subgrafico 2: Variables Ambientales (Temperatura y Humedad del Aire)
axs[1].plot(df['Tiempo'], df['Temp Amb C'], label='Temperatura (C)', color='#DC143C')
axs[1].plot(df['Tiempo'], df['Hum Amb %'], label='Humedad Ambiente (%)', color='#4169E1')
axs[1].set_ylabel('Variables de Aire')
axs[1].legend(loc='upper right')
axs[1].grid(True, linestyle=':', alpha=0.7)

# Subgrafico 3: Variables de Suelo
axs[2].plot(df['Tiempo'], df['Hum Suelo %'], label='Humedad de Suelo (%)', color='#228B22')
axs[2].set_ylabel('Suelo (%)')
axs[2].legend(loc='upper right')
axs[2].grid(True, linestyle=':', alpha=0.7)

# Subgrafico 4: Estados Digitales (Controladores)
# Utilizamos step() en lugar de plot() para transiciones cuadradas
axs[3].step(df['Tiempo'], df['Luz Estado'], label='Estado Luminarias', color='#FF8C00', where='post')
axs[3].step(df['Tiempo'], df['Riego Estado'], label='Estado Riego', color='#00CED1', where='post')
axs[3].set_ylabel('Estado (1=ON, 0=OFF)')
axs[3].set_yticks([0, 1])
axs[3].legend(loc='upper right')
axs[3].grid(True, linestyle=':', alpha=0.7)

# 5. Ajustes finales de formato
plt.xlabel('Linea Temporal')
plt.xticks(rotation=45)
plt.tight_layout()

# Guardar la figura en alta resolucion para el informe de LaTeX
plt.savefig('graficos_telemetria.png', dpi=300, bbox_inches='tight')

# Mostrar el grafico en pantalla
plt.show()