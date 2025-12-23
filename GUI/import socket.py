import socket
import pygame
from pygame.locals import *

ARDUINO_IP = "192.168.1.151"
ARDUINO_PORT = 8888

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No joystick detected!")
    exit(1)

joystick = pygame.joystick.Joystick(0)
joystick.init()

print("Joystick initialized!")

running = True
while running:
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False

        elif event.type == JOYBUTTONDOWN:
            if event.button == 3:  # Triangle button → open
                sock.sendto(b"oc1", (ARDUINO_IP, ARDUINO_PORT))
                print("Sent: oc1")
            elif event.button == 0:  # X button → close
                sock.sendto(b"cc1", (ARDUINO_IP, ARDUINO_PORT))
                print("Sent: cc1")

pygame.quit()
sock.close()