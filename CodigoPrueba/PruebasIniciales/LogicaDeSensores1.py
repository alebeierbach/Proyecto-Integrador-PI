
#chequeos cada hora

if(temp_c>30)
  # encender ventilador

if(line>700)
  # encender bomba de regado

if(line<50)
  # avisar de humedad excesiva

if(light<500) #esta oscureciendo
  if(tiempo_fotoperiodo<=14) #verifico si ya tuvo sus 14h de luz (me aseguro que la planta tenga 14h de luz)
    #encender luz
  else
    #apagar luz


####################################

tiempo_fotoperiodo++

if(tiempo_fotoperiodo==24)
   tiempo_fotoperiodo=0     #se reinicia el fotoperiodo luego de 24 horas

