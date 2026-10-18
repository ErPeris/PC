// Sketch di prova per la scheda di test con Arduino Nano.
//
// Librerie da installare dal gestore librerie dell'IDE Arduino:
//   - "Adafruit BME280 Library" (installa anche "Adafruit Unified Sensor")
// La libreria Servo è già inclusa nell'IDE.
//
// Collegamenti sulla scheda: D8 = buzzer (tramite Q1), D9 = servo,
// A4 = SDA e A5 = SCL del modulo BME280.

#include <Wire.h>
#include <Servo.h>
#include <Adafruit_BME280.h>

const int PIN_BUZZER = 8;
const int PIN_SERVO = 9;

Adafruit_BME280 bme;
Servo servo;
bool bmeTrovato = false;

// Funziona sia con buzzer attivo sia con buzzer passivo.
void beep(int durataMs) {
  tone(PIN_BUZZER, 2000, durataMs);
  delay(durataMs);
}

void setup() {
  Serial.begin(9600);
  pinMode(PIN_BUZZER, OUTPUT);
  servo.attach(PIN_SERVO);

  // A seconda del modulo l'indirizzo I2C è 0x76 oppure 0x77.
  bmeTrovato = bme.begin(0x76) || bme.begin(0x77);
  if (!bmeTrovato) {
    Serial.println("BME280 non trovato: controllare il modulo e l'ordine dei pin");
  }
  beep(200);
}

void loop() {
  if (bmeTrovato) {
    Serial.print("Temperatura: ");
    Serial.print(bme.readTemperature());
    Serial.print(" C   Umidita': ");
    Serial.print(bme.readHumidity());
    Serial.print(" %   Pressione: ");
    Serial.print(bme.readPressure() / 100.0);
    Serial.println(" hPa");
  }

  // il servo passa da 0 a 90 a 180 gradi e torna indietro
  int posizioni[] = {0, 90, 180, 90};
  for (int i = 0; i < 4; i++) {
    servo.write(posizioni[i]);
    delay(500);
  }
  beep(50);
}
