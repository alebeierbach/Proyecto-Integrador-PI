%% calculo de DLI
Ti= 12 ;%%Fotoperiodo en horas
Lux= 5000 ; %% intensidad luminica medida con el bht
F_L = 8.87/100 ; %% Factor de Luminaria
PPFD = Lux* F_L ; %% Conversion de Lux a PPFD;
DLI = 0.0036* PPFD * Ti
%%Para encontrar la cantidad de luz necesaria en base a las caracteristicas de las plantas:
DLI_D = 17.3; %%DLI necesaria de una planta determinada
PPFDc = DLI_D / (0.0036*Ti);
Luxs = PPFDc / F_L
