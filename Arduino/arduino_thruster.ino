#include <Servo.h>

const int THRUSTER_COUNT = 8;
Servo thrusters[THRUSTER_COUNT];
const byte thrusterPins[] = {17, 15, 13, 11, 3, 5, 7, 9};

void setup() {
  Serial.begin(9600);
  Serial.println("Thruster test ready.");

  for (int i = 0; i < THRUSTER_COUNT; i++) {
    thrusters[i].attach(thrusterPins[i]);
    thrusters[i].writeMicroseconds(1500); 
  }
}

void loop() {
  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();  

    if (msg.length() == 0) return;

    Serial.print("Raw input: ");
    Serial.println(msg);

    if (msg.charAt(0) == 'c') {
      String data = msg.substring(2);
      int thrusterValues[THRUSTER_COUNT] = {1500,1500,1500,1500,1500,1500,1500,1500};

      int index = 0;
      while (data.length() > 0 && index < THRUSTER_COUNT) {
        int comma = data.indexOf(',');
        String token;
        if (comma == -1) {
          token = data;
          data = "";
        } else {
          token = data.substring(0, comma);
          data = data.substring(comma + 1);
        }
        thrusterValues[index] = token.toInt();
        index++;
      }

      for (int i = 0; i < THRUSTER_COUNT; i++) {
        int value = thrusterValues[i];
        if (value >= 1100 && value <= 1900) {
          thrusters[i].writeMicroseconds(value);
          Serial.print("Thruster ");
          Serial.print(i);
          Serial.print(" set to ");
          Serial.println(value);
        } else {
          Serial.print("Thruster ");
          Serial.print(i);
          Serial.print(" got invalid value: ");
          Serial.println(value);
        }
      }
    }
  }
}
