// === SENSOR DE HUMEDAD DE SUELO ===
// Lee el valor analógico (0–1023) y lo muestra en el Monitor Serie

const int PIN_SOIL = A0;        // pin analógico A0
const unsigned long INTERVALO = 2000; // tiempo entre lecturas (ms)
const int N_SAMPLES = 10;       // cantidad de lecturas para promediar

void setup() {
  Serial.begin(115200);           // inicializa comunicación serie
  pinMode(PIN_SOIL, INPUT);
  Serial.println("Iniciando lectura de humedad de suelo:");
  delay(2000);                  // espera a estabilizar el sensor
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
  int valor = leerPromedio(PIN_SOIL, N_SAMPLES);
  Serial.print("Valor de humedad del suelo: ");
  Serial.println(valor);        // imprime el valor (0–1023)
  delay(INTERVALO);
}
