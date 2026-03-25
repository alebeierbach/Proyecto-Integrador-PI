from config_loader import cargar_configuracion

config = cargar_configuracion("config.toml")

print("Configuracion cargada correctamente\n")

print("Global:")
print(config.global_config)

print("\nBomba:")
print(config.bomba)

print("\nADCs:")
for nombre, adc in config.adcs.items():
    print(nombre, adc)

print("\nMacetas:")
for nombre, maceta in config.macetas.items():
    print(nombre, maceta)