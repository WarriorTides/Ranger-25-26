#include <Servo.h>
#include <Wire.h>
#include <UIPEthernet.h>
#include "Adafruit_BME680.h"

// === Servo pins ===
const int CLAW1_SERVO_PIN = 8;
const int CLAW1_ROT_PIN   = 6;
const int CLAW2_SERVO_PIN = 34;
const int CLAW2_ROT_PIN   = 32;   // FIXED: different pin
byte servoPin = 11;
const int INCREMENT = 30;

// === Servo angles ===
int angleClaw1 = 0;
int angleClaw1Rot = 0;
int angleClaw2 = 0;
int angleClaw2Rot = 0;

// === Servo definitions ===
Servo claw1Servo;
Servo claw1Rot;
Servo claw2Servo;
Servo claw2Rot;
Servo servo;

EthernetUDP udp;
Adafruit_BME680 bme;

// === Network ===
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};
IPAddress arduinoIP(192, 168, 1, 151);
IPAddress laptopIP(192, 168, 1, 154);
unsigned int port = 8888;

// === Current sensor ===
const int sensorPin = A3;
const float sensitivity = 0.185;
const float Vref = 5.0;
const float offset = Vref / 2;

float prevCurrent = 0;
bool firstSend = true;

// === Timing ===
unsigned long lastSensorSend = 0;
const unsigned long SENSOR_INTERVAL = 500; // ms

void setup() {
  Serial.begin(9600);

  Ethernet.begin(mac, arduinoIP);
  udp.begin(port);

  servo.attach(servoPin);

  claw1Servo.attach(CLAW1_SERVO_PIN);
  claw1Rot.attach(CLAW1_ROT_PIN);
  claw2Servo.attach(CLAW2_SERVO_PIN);
  claw2Rot.attach(CLAW2_ROT_PIN);

  claw1Servo.write(angleClaw1);
  claw1Rot.write(angleClaw1Rot);
  claw2Servo.write(angleClaw2);
  claw2Rot.write(angleClaw2Rot);

  // if (!bme.begin(0x77)) {
  //   Serial.println("BME680 not found!");
  //   while (1);
  // }
  bme.setHumidityOversampling(BME680_OS_2X);

  Serial.println("=== 4-Servo UDP Controller Initialized ===");
  Serial.print("IP: "); Serial.println(Ethernet.localIP());
  Serial.print("Port: "); Serial.println(port);
  Serial.print("WAITING 7 SECONDS PLEASE BE PAIIENT PARTH");
  delay(7000);

}

void loop() {

  /* ===============================
     1) CLAW COMMANDS (HIGH PRIORITY)
     =============================== */
  int packetSize = udp.parsePacket();
  if (packetSize > 0) {
    char packet[255];
    int len = udp.read(packet, 255);
    if (len > 0) packet[len] = 0;

    String msg = String(packet);
    msg.trim();
    Serial.println(msg);
    // === Claw 1 ===
    if (msg == "oc1") {
      angleClaw1 += INCREMENT;
    }
    else if (msg == "cc1") {
      angleClaw1 -= INCREMENT;
    }
    else if (msg == "rc1") {
      angleClaw1Rot += INCREMENT;
    }
    else if (msg == "urc1") {
      angleClaw1Rot -= INCREMENT;
    }

    // === Claw 2 ===
    else if (msg == "oc2") {
      angleClaw2 += INCREMENT;
    }
    else if (msg == "cc2") {
      angleClaw2 -= INCREMENT;
    }
    else if (msg == "rc2") {
      angleClaw2Rot += INCREMENT;
    }
    else if (msg == "urc2") {
      angleClaw2Rot -= INCREMENT;
    }

    // === SAFETY CLAMP (Arduino responsibility only)
    angleClaw1     = constrain(angleClaw1, 0, 180);
    angleClaw1Rot  = constrain(angleClaw1Rot, 0, 180);
    angleClaw2     = constrain(angleClaw2, 0, 180);
    angleClaw2Rot  = constrain(angleClaw2Rot, 0, 180);

    // === Apply once
    claw1Servo.write(angleClaw1);
    claw1Rot.write(angleClaw1Rot);
    claw2Servo.write(angleClaw2);
    claw2Rot.write(angleClaw2Rot);

    // ACK
    udp.beginPacket(udp.remoteIP(), udp.remotePort());
    udp.println("received");
    udp.endPacket();
  }

  /* ===============================
     2) SENSOR TELEMETRY (TIMED)
     =============================== */
  if (millis() - lastSensorSend >= SENSOR_INTERVAL) {
    lastSensorSend = millis();

    // ---- CURRENT SENSOR ----
    long sum = 0;
    const int samples = 20;
    for (int i = 0; i < samples; i++) {
      sum += analogRead(sensorPin);
    }

    float avgAdc = sum / (float)samples;
    float voltage = avgAdc * (Vref / 1024.0);
    float current = (offset - voltage) / sensitivity;

    if (firstSend || abs(current - prevCurrent) > 1.0) {
      char msg[32];
      int w = (int)current;
      int d = abs((int)((current - w) * 100));
      snprintf(msg, sizeof(msg), "CUR:%d.%02d", w, d);

      udp.beginPacket(laptopIP, port);
      udp.write(msg);
      udp.endPacket();

      prevCurrent = current;
      firstSend = false;
    }

    // ---- HUMIDITY SENSOR ----
    if (bme.performReading()) {
      float humidity = bme.humidity;
      char msg[32];
      int w = (int)humidity;
      int d = abs((int)((humidity - w) * 100));
      snprintf(msg, sizeof(msg), "HUM:%d.%02d", w, d);

      udp.beginPacket(laptopIP, port);
      udp.write(msg);
      udp.endPacket();
    }
  }
}

