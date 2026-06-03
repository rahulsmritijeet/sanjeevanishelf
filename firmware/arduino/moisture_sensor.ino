/*
 * Moisture Sensors - Arduino Uno + 4x Soil Moisture Sensors + HC-05 Bluetooth
 * 
 * Connections:
 * Moisture Sensors -> Arduino (Analog)
 * Sensor 1 -> A0
 * Sensor 2 -> A1
 * Sensor 3 -> A2
 * Sensor 4 -> A3
 * VCC -> 5V
 * GND -> GND
 * 
 * HC-05 -> Arduino (SoftwareSerial)
 * TX -> D2
 * RX -> D3
 * VCC -> 5V
 * GND -> GND
 * 
 * Protocol:
 * - Receives "READ" command
 * - Responds with "MOISTURE:<s1>,<s2>,<s3>,<s4>" (percentage values)
 * 
 * Calibration:
 * - Dry air: ~0% moisture (high analog value)
 * - Wet grain: ~100% moisture (low analog value)
 * - Adjust DRY_VALUE and WET_VALUE based on your sensors
 */

#include <SoftwareSerial.h>

// Pin definitions
#define SENSOR1_PIN A0
#define SENSOR2_PIN A1
#define SENSOR3_PIN A2
#define SENSOR4_PIN A3
#define BT_RX 2
#define BT_TX 3

// Initialize Bluetooth
SoftwareSerial bluetooth(BT_RX, BT_TX);

// Calibration values (adjust based on your sensors)
const int DRY_VALUE = 600;   // Analog reading in dry air
const int WET_VALUE = 300;   // Analog reading in wet grain

void setup() {
  // Initialize serial (for debugging)
  Serial.begin(9600);
  
  // Initialize Bluetooth
  bluetooth.begin(9600);
  
  // Set analog reference to default (5V)
  analogReference(DEFAULT);
  
  Serial.println("Moisture Sensor Array Ready");
  bluetooth.println("Moisture Sensor Array Ready");
  
  delay(100);
}

void loop() {
  // Check for incoming Bluetooth commands
  if (bluetooth.available()) {
    String command = bluetooth.readStringUntil('
');
    command.trim();
    handleCommand(command);
  }
  
  delay(100);
}

void handleCommand(String command) {
  Serial.print("Command: ");
  Serial.println(command);
  
  if (command == "READ") {
    readMoisture();
  }
}

void readMoisture() {
  // Read all 4 sensors
  float readings[4];
  
  readings[0] = readSensor(SENSOR1_PIN);
  delay(50);
  readings[1] = readSensor(SENSOR2_PIN);
  delay(50);
  readings[2] = readSensor(SENSOR3_PIN);
  delay(50);
  readings[3] = readSensor(SENSOR4_PIN);
  
  // Send via Bluetooth
  bluetooth.print("MOISTURE:");
  bluetooth.print(readings[0], 2);
  bluetooth.print(",");
  bluetooth.print(readings[1], 2);
  bluetooth.print(",");
  bluetooth.print(readings[2], 2);
  bluetooth.print(",");
  bluetooth.println(readings[3], 2);
  
  // Debug
  Serial.print("Moisture readings: ");
  for (int i = 0; i < 4; i++) {
    Serial.print(readings[i], 2);
    Serial.print("% ");
  }
  Serial.println();
}

float readSensor(int pin) {
  // Take multiple readings and average
  long sum = 0;
  const int samples = 10;
  
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(10);
  }
  
  int avg = sum / samples;
  
  // Convert to percentage
  // Invert: higher analog value = less moisture
  float moisture = map(avg, DRY_VALUE, WET_VALUE, 0, 100);
  
  // Constrain to 0-100%
  if (moisture < 0) moisture = 0;
  if (moisture > 100) moisture = 100;
  
  return moisture;
}