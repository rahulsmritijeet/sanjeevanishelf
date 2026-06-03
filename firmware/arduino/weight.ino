/*
 * Weight Scale - Arduino Uno + HX711 + Load Cell + HC-05 Bluetooth
 * 
 * Connections:
 * HX711 -> Arduino
 * DT   -> D4
 * SCK  -> D5
 * VCC  -> 5V
 * GND  -> GND
 * 
 * Load Cell -> HX711
 * E+   -> Red
 * E-   -> Black
 * A+   -> White
 * A-   -> Green
 * 
 * HC-05 -> Arduino (SoftwareSerial)
 * TX -> D2
 * RX -> D3
 * VCC -> 5V
 * GND -> GND
 * 
 * Protocol:
 * - Continuously reads weight and sends "WEIGHT:<kg>" every 500ms
 * - Receives "TARE" command to zero the scale
 * - Responds with "TARE_OK"
 */

#include <HX711.h>
#include <SoftwareSerial.h>

// Pin definitions
#define LOADCELL_DOUT_PIN 4
#define LOADCELL_SCK_PIN 5
#define BT_RX 2
#define BT_TX 3

// Initialize HX711
HX711 scale;

// Initialize Bluetooth
SoftwareSerial bluetooth(BT_RX, BT_TX);

// Calibration factor (adjust based on your load cell)
// To calibrate: place known weight and adjust this value
float calibration_factor = 2280.0; // Example value for 100kg load cell

// State
unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL = 500; // Send reading every 500ms

void setup() {
  // Initialize serial (for debugging)
  Serial.begin(9600);
  
  // Initialize Bluetooth
  bluetooth.begin(9600);
  
  // Initialize HX711
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  
  Serial.println("Weight Scale Initializing...");
  
  // Set calibration factor
  scale.set_scale(calibration_factor);
  
  // Tare the scale
  scale.tare();
  
  Serial.println("Weight Scale Ready");
  bluetooth.println("Weight Scale Ready");
  
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
  
  // Send weight reading periodically
  if (millis() - lastSendTime > SEND_INTERVAL) {
    lastSendTime = millis();
    
    if (scale.is_ready()) {
      float weight = scale.get_units(5); // Average of 5 readings
      
      // Convert to kg and ensure non-negative
      weight = weight / 1000.0; // grams to kg
      if (weight < 0) weight = 0;
      
      // Send via Bluetooth
      bluetooth.print("WEIGHT:");
      bluetooth.println(weight, 2);
      
      // Debug
      Serial.print("Weight: ");
      Serial.print(weight, 2);
      Serial.println(" kg");
    } else {
      Serial.println("HX711 not ready");
    }
  }
}

void handleCommand(String command) {
  Serial.print("Command: ");
  Serial.println(command);
  
  if (command == "TARE") {
    scale.tare();
    bluetooth.println("TARE_OK");
    Serial.println("Scale tared");
  }
  else if (command.startsWith("CAL:")) {
    // Calibration command: CAL:<factor>
    float factor = command.substring(4).toFloat();
    if (factor > 0) {
      calibration_factor = factor;
      scale.set_scale(calibration_factor);
      bluetooth.println("CAL_OK");
      Serial.print("Calibration set to: ");
      Serial.println(calibration_factor);
    } else {
      bluetooth.println("CAL_FAIL");
    }
  }
}