/*
 * RFID Reader - Arduino Uno + RC522 + HC-05 Bluetooth
 * 
 * Connections:
 * RC522 -> Arduino
 * SDA  -> D10
 * SCK  -> D13
 * MOSI -> D11
 * MISO -> D12
 * IRQ  -> Not connected
 * GND  -> GND
 * RST  -> D9
 * 3.3V -> 3.3V
 * 
 * HC-05 -> Arduino (SoftwareSerial)
 * TX -> D2
 * RX -> D3
 * VCC -> 5V
 * GND -> GND
 * 
 * Protocol:
 * - Continuously scans for RFID tags
 * - On detection: sends "RFID:<UID>" via Bluetooth
 * - Receives "WRITE:<UID>:<DATA>" to write to tag
 * - Responds with "WRITE_OK" or "WRITE_FAIL"
 */

#include <SPI.h>
#include <MFRC522.h>
#include <SoftwareSerial.h>

// Pin definitions
#define RST_PIN 9
#define SS_PIN 10
#define BT_RX 2
#define BT_TX 3

// Initialize RFID
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Initialize Bluetooth
SoftwareSerial bluetooth(BT_RX, BT_TX);

// State
String lastUID = "";
unsigned long lastScanTime = 0;
const unsigned long SCAN_COOLDOWN = 2000; // 2 seconds between same tag scans

void setup() {
  // Initialize serial (for debugging)
  Serial.begin(9600);
  
  // Initialize Bluetooth
  bluetooth.begin(9600);
  
  // Initialize SPI
  SPI.begin();
  
  // Initialize RFID
  mfrc522.PCD_Init();
  
  Serial.println("RFID Reader Ready");
  bluetooth.println("RFID Reader Ready");
  
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
  
  // Scan for RFID tags
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String uid = getUID();
    
    // Cooldown check to avoid duplicate scans
    if (uid != lastUID || (millis() - lastScanTime) > SCAN_COOLDOWN) {
      lastUID = uid;
      lastScanTime = millis();
      
      // Send UID via Bluetooth
      bluetooth.print("RFID:");
      bluetooth.println(uid);
      
      Serial.print("Scanned: ");
      Serial.println(uid);
      
      // Beep indicator (if buzzer connected to pin 8)
      // tone(8, 2000, 100);
    }
    
    // Halt PICC
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
  }
  
  delay(100);
}

String getUID() {
  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) {
      uid += "0";
    }
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

void handleCommand(String command) {
  Serial.print("Command: ");
  Serial.println(command);
  
  if (command.startsWith("WRITE:")) {
    // Parse: WRITE:<UID>:<DATA>
    int firstColon = command.indexOf(':');
    int secondColon = command.indexOf(':', firstColon + 1);
    
    if (secondColon > 0) {
      String targetUID = command.substring(firstColon + 1, secondColon);
      String data = command.substring(secondColon + 1);
      
      bool success = writeToTag(targetUID, data);
      
      if (success) {
        bluetooth.println("WRITE_OK");
        Serial.println("Write successful");
      } else {
        bluetooth.println("WRITE_FAIL");
        Serial.println("Write failed");
      }
    }
  }
}

bool writeToTag(String targetUID, String data) {
  // Wait for tag
  unsigned long startTime = millis();
  
  while (millis() - startTime < 5000) { // 5 second timeout
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
      String uid = getUID();
      
      if (uid == targetUID) {
        // Write to block 4 (first writable block in sector 1)
        byte block = 4;
        byte buffer[16];
        
        // Prepare data (max 16 bytes)
        data.getBytes(buffer, 16);
        for (int i = data.length(); i < 16; i++) {
          buffer[i] = 0; // Pad with zeros
        }
        
        // Authenticate
        MFRC522::StatusCode status;
        byte trailerBlock = 7;
        MFRC522::MIFARE_Key key;
        for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF; // Default key
        
        status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, trailerBlock, &key, &(mfrc522.uid));
        
        if (status != MFRC522::STATUS_OK) {
          Serial.print("Auth failed: ");
          Serial.println(mfrc522.GetStatusCodeName(status));
          mfrc522.PICC_HaltA();
          mfrc522.PCD_StopCrypto1();
          return false;
        }
        
        // Write data
        status = mfrc522.MIFARE_Write(block, buffer, 16);
        
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        
        return (status == MFRC522::STATUS_OK);
      }
      
      mfrc522.PICC_HaltA();
      mfrc522.PCD_StopCrypto1();
    }
    
    delay(100);
  }
  
  return false; // Timeout
}