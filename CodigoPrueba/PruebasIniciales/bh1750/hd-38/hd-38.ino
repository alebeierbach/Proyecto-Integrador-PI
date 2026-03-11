/*
   Test Simple para Sensor de Humedad de Suelo HD-38
   Conexión: Pin AO del sensor al Pin A0 del Arduino
*/

const int sensorPin = A0;  // El pin donde conectaste el cable AO

// VALORES DE CALIBRACIÓN (Ajustalos segun tus pruebas)
// Seco (En el aire) suele ser cercano a 1023
// Mojado (En agua) suele ser cercano a 200-400
const int seco = 1023;
const int mojado = 160; 

void setup() {
  Serial.begin(9600); // Iniciamos la comunicacion con la PC
  Serial.println("--- Iniciando Test de Humedad ---");
}

void loop() {
  // 1. Leer el valor crudo (0 a 1023)
  int valorRaw = analogRead(sensorPin);
  delay(1000);

  // 2. Convertir a Porcentaje (Mapeo)
  // Nota: Es inverso. Mayor valor = Mas seco.
  int porcentaje = map(valorRaw, seco, mojado, 0, 100);

  // 3. Limitar el rango (Clamp) para que no de -10% o 110%
  porcentaje = constrain(porcentaje, 0, 100);

  // 4. Mostrar en pantalla
  Serial.print("Valor Raw: ");
  Serial.print(valorRaw);
  Serial.print(" | Humedad: ");
  Serial.print(porcentaje);
  Serial.println("%");

  delay(1000); // Esperar 1 segundo
}