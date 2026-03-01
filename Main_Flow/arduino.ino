#include <Servo.h>
#include <UIPEthernet.h>

const int THRUSTER_COUNT = 8;
Servo thrusters[THRUSTER_COUNT];
const byte thrusterPins[THRUSTER_COUNT] = {29, 27, 25, 23, 19, 17, 15, 13};
const int CLAW1_SERVO_PIN = 2;
const int CLAW1_ROT_PIN   = 8;
const int CLAW2_SERVO_PIN = 6;
const int CLAW2_ROT_PIN   = 9;
const int INCREMENT = 30;

int angleClaw1 = 0;
int angleClaw1Rot = 0;
int angleClaw2 = 0;
int angleClaw2Rot = 0;

Servo claw1Servo;
Servo claw1Rot;
Servo claw2Servo;
Servo claw2Rot;

EthernetUDP udp;
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};
IPAddress arduinoIP(192, 168, 1, 151);
IPAddress laptopIP(192, 168, 1, 119); // Your laptop IP
unsigned int port = 8888;


void setup() {
  Serial.begin(19200);

  Ethernet.begin(mac, arduinoIP);
  udp.begin(port);

  for (int i = 0; i < THRUSTER_COUNT; i++) {
    thrusters[i].attach(thrusterPins[i]);
    thrusters[i].writeMicroseconds(1500); 
  }

  claw1Servo.attach(CLAW1_SERVO_PIN);
  claw1Rot.attach(CLAW1_ROT_PIN);
  claw2Servo.attach(CLAW2_SERVO_PIN);
  claw2Rot.attach(CLAW2_ROT_PIN);
  claw1Servo.write(angleClaw1);
  claw1Rot.write(angleClaw1Rot);
  claw2Servo.write(angleClaw2);
  claw2Rot.write(angleClaw2Rot);

  Serial.println(" READY ");
  delay(7000); 
}

void loop() {
  int packetSize = udp.parsePacket();
  if (packetSize > 0) {
    char packet[255];
    int len = udp.read(packet, 255);
    if (len > 0) packet[len] = 0;
    String msg = String(packet);
    msg.trim();

    Serial.print("UDP RX: ");
    Serial.println(msg);

    if (msg.startsWith("c,")) {
      handleThrusterUDP(msg);
    } else {
      handleClawUDP(msg);
    }
  }
}


void handleThrusterUDP(String msg) {
  String data = msg.substring(2); 
  int thrusterValues[THRUSTER_COUNT] = {1500,1500,1500,1500,1500,1500,1500,1500};

  int idx = 0;
  while (data.length() > 0 && idx < THRUSTER_COUNT) {
    int comma = data.indexOf(',');
    String token;
    if (comma == -1) {
      token = data;
      data = "";
    } else {
      token = data.substring(0, comma);
      data = data.substring(comma + 1);
    }
    thrusterValues[idx] = token.toInt();
    idx++;
  }

  for (int i = 0; i < THRUSTER_COUNT; i++) {
    int value = constrain(thrusterValues[i], 1100, 1900);
    thrusters[i].writeMicroseconds(value);
  }
}

void handleClawUDP(String msg) {
  if (msg == "oc1") angleClaw1 += INCREMENT;
  else if (msg == "cc1") angleClaw1 -= INCREMENT;
  else if (msg == "rc1") angleClaw1Rot += INCREMENT;
  else if (msg == "urc1") angleClaw1Rot -= INCREMENT;
  else if (msg == "oc2") angleClaw2 += INCREMENT;
  else if (msg == "cc2") angleClaw2 -= INCREMENT;
  else if (msg == "rc2") angleClaw2Rot += INCREMENT;
  else if (msg == "urc2") angleClaw2Rot -= INCREMENT;

  angleClaw1     = constrain(angleClaw1, 0, 180);
  angleClaw1Rot  = constrain(angleClaw1Rot, 0, 180);
  angleClaw2     = constrain(angleClaw2, 0, 180);
  angleClaw2Rot  = constrain(angleClaw2Rot, 0, 180);

  claw1Servo.write(angleClaw1);
  claw1Rot.write(angleClaw1Rot);
  claw2Servo.write(angleClaw2);
  claw2Rot.write(angleClaw2Rot);

  udp.beginPacket(udp.remoteIP(), udp.remotePort());
  udp.println("received");
  udp.endPacket();
}
