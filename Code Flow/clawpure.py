#"wscat -c ws://127.0.0.1:8765"
import asyncio
import json
import socket
import websockets
import pygame
from pygame.locals import *


UDP_PORT = 8888
WEBSOCKET_PORT = 8765
ARDUINO_IP = "192.168.1.151"
ARDUINO_PORT = 8888

running = True

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", UDP_PORT))
sock.settimeout(0.1)

print(f"Listening on port {UDP_PORT}")

connected_clients = set()


pygame.init()
pygame.joystick.init()

joystick_present = pygame.joystick.get_count() > 0
if joystick_present:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Joystick connected and ready!")
else:
    print("No joystick detected. Claw control disabled.")


async def claw():
    if not joystick_present:
        return

    INCREMENT = 5
    angleClaw1 = 0
    angleClaw1Rot = 0
    angleClaw2 = 0
    angleClaw2Rot = 0
    print("Resetting all servos to 0...")

    # for _ in range(40): # enough steps to guarantee reaching 0
    #     sock.sendto("cc1".encode(), (ARDUINO_IP, ARDUINO_PORT))
    #     sock.sendto("urc1".encode(), (ARDUINO_IP, ARDUINO_PORT))
    #     sock.sendto("cc2".encode(), (ARDUINO_IP, ARDUINO_PORT))
    #     sock.sendto("urc2".encode(), (ARDUINO_IP, ARDUINO_PORT))

    # await asyncio.sleep(0.02)

    # print("All servos initialized to 0")

    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                exit()

            elif event.type == JOYBUTTONDOWN:
                if event.button == 3 and angleClaw1 < 180:  # Open claw1, triangle

                    message = "oc1"
                    angleClaw1 = min(180, angleClaw1 + INCREMENT)
                    sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                    print(f"open tri: angle {angleClaw1}")

                elif event.button == 0 and angleClaw1 > 0:  # Close claw1, x
                    message = "cc1"
                    angleClaw1 = max(0, angleClaw1 - INCREMENT)
                    sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                    print(f"close x: angle {angleClaw1}")

                elif event.button == 2 and angleClaw1Rot < 180:  # Rotate claw1, square
                    angleClaw1Rot = min(180, angleClaw1Rot + INCREMENT)
                    message = "rc1"
                    sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                    print(f"rotate sq: angle {angleClaw1Rot}")

                elif event.button == 1 and angleClaw1Rot > 0:  # Unrotate claw1, circle
                    angleClaw1Rot = max(0, angleClaw1Rot - INCREMENT)
                    message = "urc1"
                    sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                    print(f"unrotate c: angle {angleClaw1Rot}")

                elif event.button == 11 and angleClaw2 < 180:  # Open claw2, up arrow
                    message = "oc2"
                    angleClaw2 = min(180, angleClaw2 + INCREMENT)
                    sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                    print(f"open up: angle {angleClaw2}")

                elif event.button == 12 and angleClaw2 > 0:  # Close claw2, down arrow
                    message = "cc2"
                    angleClaw2 = max(0, angleClaw2 - INCREMENT)
                    sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                    print(f"close down: angle {angleClaw2}")

                elif event.button == 13 and angleClaw2Rot < 180:  # Rotate claw2, left arrow
                    message = "rc2"
                    angleClaw2Rot = min(180, angleClaw2Rot + INCREMENT)
                    sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                    print(f"rotate lef: angle {angleClaw2Rot}")

                elif event.button == 14 and angleClaw2Rot > 0:  # Unrotate claw2, right arrow
                    message = "urc2"
                    angleClaw2Rot = max(0, angleClaw2Rot - INCREMENT)
                    sock.sendto(message.encode(), (ARDUINO_IP, ARDUINO_PORT))
                    print(f"unrotate righ: angle {angleClaw2Rot}")

        await asyncio.sleep(0.1)

    pygame.quit()
    # sock.close()


async def sensor_ws_handler(websocket):
    connected_clients.add(websocket)
    print(f"Client connected ({len(connected_clients)} total)")

    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                msg = data.decode().strip()
                print(f"From {addr}: {msg}")

                payload = None

                if msg.startswith("HUM:"):
                    try:
                        humidity = float(msg[4:])
                        payload = {"humidity": humidity}
                        print(f"Humidity = {humidity}")
                    except:
                        print(f"Bad humidity: {msg}")

                elif msg.startswith("CUR:"):
                    try:
                        current = float(msg[4:])
                        payload = {"current": current}
                        print(f"Current = {current}")
                    except:
                        print(f"Bad current: {msg}")

                if payload:
                    json_msg = json.dumps(payload)
                    dead = []
                    for client in connected_clients:
                        try:
                            await client.send(json_msg)
                        except:
                            dead.append(client)
                    for d in dead:
                        connected_clients.remove(d)

            except socket.timeout:
                pass

            await asyncio.sleep(0.02)

    except websockets.ConnectionClosed:
        print("Client disconnected")
        connected_clients.discard(websocket)


async def main():
    print(f"Websocket server: ws://0.0.0.0:{WEBSOCKET_PORT}")

    async with websockets.serve(sensor_ws_handler, "0.0.0.0", WEBSOCKET_PORT):
        await asyncio.gather(
            claw(),
        )


if __name__ == "__main__":
    asyncio.run(main())