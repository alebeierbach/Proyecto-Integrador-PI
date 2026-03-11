// === SENSOR DE HUMEDAD DE SUELO Y LUZ (FOTORESISTENCIA) ===
// Envia los valores por el puerto serie cada 2 segundos

const int PIN_SOIL = A0;         // sensor de humedad
const int PIN_LDR  = A1;         // sensor de luz (fotoresistencia)
const unsigned long INTERVALO = 2000; // tiempo entre lecturas (ms)
const int N_SAMPLES = 10;        // cantidad de lecturas para promediar

void setup() {
  Serial.begin(115200);
  pinMode(PIN_SOIL, INPUT);
  pinMode(PIN_LDR, INPUT);

  Serial.println("Iniciando lectura de sensores...");
  delay(2000);
}

int leerPromedio(int pin, int n) {
  long suma = 0;
  for (int i = 0; i < n; i++) {
    suma += analogRead(pin);
    delay(5);
  }
  return suma / n;
}

void loop() {
  int humedad = leerPromedio(PIN_SOIL, N_SAMPLES);
  int luz = leerPromedio(PIN_LDR, N_SAMPLES);

  // Envío en formato CSV (fácil de leer en la Raspberry)
  // Ejemplo: "humedad:523, luz:812"
  Serial.print("humedad:");
  Serial.print(humedad);
  Serial.print(", luz:");
  Serial.println(luz);

  delay(INTERVALO);
}
