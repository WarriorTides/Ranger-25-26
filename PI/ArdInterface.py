# ArduinoInterface.py
import serial
import time

class ArduinoInterface:
    def __init__(self, port="/dev/ttyACM0", baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  

    def read_sensors(self):
        """Reads a line from Arduino and returns sensor dict"""
        if self.ser.in_waiting > 0:
            line = self.ser.readline().decode().strip()
            # Expected format: temp,humidity,depth,leak
            try:
                temp, humidity, depth, leak = map(float, line.split(","))
                return {
                    "temperature": temp,
                    "humidity": humidity,
                    "depth": depth,
                    "leak": leak
                }
            except:
                return None
        return None
