# import asyncio
# import websockets
# import json
# import socket
# import threading
# import serial

# UDP_IP = "127.0.0.1"
# UDP_PORT = 5005

# WS_PORT = 8770
# clients = set()

# claw1_state = "open"
# claw2_state = "open"


# arduino_port = "/dev/tty.usbmodem2101" 
# ser = serial.Serial(arduino_port, 9600, timeout=1)
# print(f"Connected to Arduino on {arduino_port}")

# def udp_listener():
#     global claw1_state, claw2_state
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     sock.bind((UDP_IP, UDP_PORT))
#     print(f"Listening for UDP on port {UDP_PORT}...")

#     while True:
#         data, addr = sock.recvfrom(1024)

#         # print(f"got raw UDP {data} from {addr}") 
#         if not data:
#             continue
#         cmd = data.decode().strip()
#         print(f"UDP Received: {cmd}")

#         if cmd == "o":
#             claw1_state = "open"
#         elif cmd == "c":
#             claw1_state = "closed"

#         ser.write(cmd.encode())
#         print(f"Forwarded to Arduino: {cmd}")

# async def claw_handler(websocket):
#     global claw1_state, claw2_state
#     print("GUI connected to ClawServer")
#     clients.add(websocket)
#     try:
#         while True:
#             data = {
#                 "claw1": claw1_state,
#                 "claw2": claw2_state
#             }
#             await websocket.send(json.dumps(data))
#             await asyncio.sleep(0.5)
#     except websockets.ConnectionClosed:
#         print("GUI disconnected")
#     finally:
#         clients.remove(websocket)

# async def main():
#     threading.Thread(target=udp_listener, daemon=True).start()

#     async with websockets.serve(claw_handler, "localhost", WS_PORT):
#         print(f"Claw WebSocket server running at ws://localhost:{WS_PORT}")
#         await asyncio.Future()

# if __name__ == "__main__":
#     asyncio.run(main())


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
            if event.button == 3:  #Open the claw1 rawr.  button triangle
                message = "oc1"
                sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                print("open tri")
            elif event.button == 0:  #close claw1 rawr. button x
                message = "cc1"
                sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                print("close x")
            elif event.button == 2:  #rotate the claw1 rawr.  button square
                message = "rc1"
                sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                print("rotate sq")
            elif event.button == 1:  #derotate claw1 rawr. button. circle
                message = "urc1"
                sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                print("unrotate c")

            elif event.button == 11:  #Open the claw2 rawr.  uparrow
                message = "oc2"
                sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                print("open up")
            elif event.button == 12:  #close claw2 rawr. downarrow
                message = "cc2"
                sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                print("close down")
            elif event.button == 13:  #rotate the claw2 rawr.  left arrow
                message = "rc2"
                sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                print("rotate lef")
            elif event.button == 14:  #derotate claw2 rawr. right arrow
                message = "urc2"
                sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                print("unrotate righ")



pygame.quit()
sock.close()