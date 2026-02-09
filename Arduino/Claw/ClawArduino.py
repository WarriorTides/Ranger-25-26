##BAUD RATE CHANGED!!!!
# COMBINED ARDUINO CODE IN CLAW SERVER

import socket
import serial

UDP_IP = "0.0.0.0"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

ser = serial.Serial("/dev/tty.usbmodem2101", 9600)  

print(f"Listening for UDP on {UDP_PORT} and forwarding to Arduino...")

while True:
    data, addr = sock.recvfrom(1024)
    if data:
        cmd = data.decode().strip()
        print(f"Received: {cmd}")
        print(f"recieved command")

        ser.write(cmd.encode())