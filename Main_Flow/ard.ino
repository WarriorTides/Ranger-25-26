#include <Servo.h>

// ── Thruster config ────────────────────────────────────────────────────────
const int THRUSTER_COUNT = 8;
Servo thrusters[THRUSTER_COUNT];
const byte thrusterPins[] = {17, 15, 13, 11, 3, 5, 7, 9};

// ── Sensor reporting ───────────────────────────────────────────────────────
// If you have a humidity / current sensor wired up, update readHumidity()
// and readCurrent() below. Arduino sends sensor data to PC port 9000.
// Thruster/claw commands are received on port 8888 (unchanged).

void setup() {
  Serial.begin(9600);

  for (int i = 0; i < THRUSTER_COUNT; i++) {
    thrusters[i].attach(thrusterPins[i]);
    thrusters[i].writeMicroseconds(1500);  // neutral
  }

  Serial.println("[Arduino] Ready. Waiting for commands...");
}

void loop() {
  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();

    if (msg.length() == 0) return;

    // ── Thruster command ───────────────────────────────────────────────
    // FIX: format is now "c <pwm0>,<pwm1>,...,<pwm7>"  (space after 'c')
    // Previously the Python code sent "c,..." which broke parsing.
    if (msg.charAt(0) == 'c' && msg.charAt(1) == ' ') {
      String data = msg.substring(2);  // strip "c "
      int thrusterValues[THRUSTER_COUNT];
      for (int i = 0; i < THRUSTER_COUNT; i++) thrusterValues[i] = 1500;

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
        int val = token.toInt();
        thrusterValues[index++] = val;
      }

      for (int i = 0; i < THRUSTER_COUNT; i++) {
        int value = thrusterValues[i];
        if (value >= 1100 && value <= 1900) {
          thrusters[i].writeMicroseconds(value);
        } else {
          Serial.print("[Arduino] Invalid PWM for thruster ");
          Serial.print(i);
          Serial.print(": ");
          Serial.println(value);
        }
      }

    // ── Claw commands ──────────────────────────────────────────────────
    // These are sent as plain strings e.g. "oc1", "cc1", "rc1", "urc1"
    } else if (msg == "oc1") {
      Serial.println("[Arduino] Claw 1 OPEN");
      // TODO: set servo pin for claw 1

    } else if (msg == "cc1") {
      Serial.println("[Arduino] Claw 1 CLOSE");

    } else if (msg == "rc1") {
      Serial.println("[Arduino] Claw 1 rotate CW");

    } else if (msg == "urc1") {
      Serial.println("[Arduino] Claw 1 rotate CCW");

    } else if (msg == "oc2") {
      Serial.println("[Arduino] Claw 2 OPEN");

    } else if (msg == "cc2") {
      Serial.println("[Arduino] Claw 2 CLOSE");

    } else if (msg == "rc2") {
      Serial.println("[Arduino] Claw 2 rotate CW");

    } else if (msg == "urc2") {
      Serial.println("[Arduino] Claw 2 rotate CCW");

    } else {
      Serial.print("[Arduino] Unknown command: ");
      Serial.println(msg);
    }
  }
}
