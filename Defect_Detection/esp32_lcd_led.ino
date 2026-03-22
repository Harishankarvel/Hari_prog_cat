#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// For ESP32: SDA=GPIO21, SCL=GPIO22
LiquidCrystal_I2C lcd(0x27, 16, 2);  // Address 0x27, 16x2 display

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n[ESP32] Initializing...");
  
  Wire.begin(21, 22);  // SDA, SCL
  
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ready");
  
  Serial.println("[ESP32] Init complete");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    Serial.println("[RX] " + cmd);
    
    if (cmd == "DEFECTIVE") {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Status: DEFECT");
      lcd.setCursor(0, 1);
      lcd.print("Defective!");
      Serial.println("[LCD] Defective status");
    } 
    else if (cmd == "OK") {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Status: OK");
      lcd.setCursor(0, 1);
      lcd.print("Part is Good!");
      Serial.println("[LCD] OK status");
    }
  }
}


