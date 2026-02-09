import asyncio
import json
import socket
import time
import websockets
import pygame

# =========================
# CONFIG
# =========================
ARDUINO_IP = "192.168.1.151"
ARDUINO_PORT = 8888

WEBSOCKET_PORT = 8765  # GUI connects here: ws://PI_IP:8765

MAX_POWER = 0.30
SEND_HZ = 10  # thruster send rate (10 Hz)

INCREMENT = 30
angleClaw1 = 0
angleClaw1Rot = 0
angleClaw2 = 0
angleClaw2Rot = 0

# Thruster mapping
mapping = [
    {"name": "OFR", "index": 1},
    {"name": "OFL", "index": 6},
    {"name": "OBR", "index": 2},
    {"name": "OBL", "index": 5},
    {"name": "IFL", "index": 7},
    {"name": "IBL", "index": 4},
    {"name": "IBR", "index": 3},
    {"name": "IFR", "index": 0},
]
mapping = sorted(mapping, key=lambda x: x["index"])


def map_thruster(value: float, max_power: float) -> int:
    return int((value * max_power) * 400 + 1500)


def parse_thruster_control(controlData: dict) -> str:
    controlString = "c"

    xythrusters = {
        "OFR": controlData["surge"] - controlData["yaw"] - controlData["sway"],
        "OFL": -(controlData["surge"] + controlData["yaw"] + controlData["sway"]),
        "OBR": controlData["surge"] - controlData["yaw"] + controlData["sway"],
        "OBL": -(controlData["surge"] + controlData["yaw"] - controlData["sway"]),
    }

    zthrusters = {
        "IFL": controlData["heave"] - controlData["roll"] + controlData["pitch"],
        "IBL": -(controlData["heave"] - controlData["roll"] - controlData["pitch"]),
        "IBR": controlData["heave"] + controlData["roll"] - controlData["pitch"],
        "IFR": -controlData["heave"] + controlData["roll"] + controlData["pitch"],
    }

    max_xy = max(abs(v) for v in xythrusters.values())
    if max_xy > 1:
        for k in xythrusters:
            xythrusters[k] /= max_xy

    max_z = max(abs(v) for v in zthrusters.values())
    if max_z > 1:
        for k in zthrusters:
            zthrusters[k] /= max_z

    combined = {**xythrusters, **zthrusters}
    control_array = [combined[item["name"]] for item in mapping]

    for val in control_array:
        controlString += "," + str(map_thruster(val, MAX_POWER))

    controlString += ",0,0"
    return controlString


# =========================
# UDP SOCKET
# =========================
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind(("", ARDUINO_PORT))
udp_sock.setblocking(False)

print(f"[UDP] bound on 0.0.0.0:{ARDUINO_PORT}")
print(f"[UDP] sending commands to {ARDUINO_IP}:{ARDUINO_PORT}")

# =========================
# WEBSOCKET
# =========================
ws_clients = set()


async def ws_handler(websocket, path):
    ws_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        ws_clients.discard(websocket)


async def broadcast(payload: dict):
    if not ws_clients:
        return
    msg = json.dumps(payload)
    for c in list(ws_clients):
        try:
            await c.send(msg)
        except Exception:
            ws_clients.discard(c)


# =========================
# SENSOR LOOP
# =========================
async def udp_sensor_loop():
    while True:
        try:
            data, _ = udp_sock.recvfrom(2048)
        except BlockingIOError:
            await asyncio.sleep(0.01)
            continue

        msg = data.decode(errors="ignore").strip()

        if msg.startswith("HUM:"):
            try:
                await broadcast({"humidity": float(msg[4:])})
            except ValueError:
                pass

        elif msg.startswith("CUR:"):
            try:
                await broadcast({"current": float(msg[4:])})
            except ValueError:
                pass


# =========================
# JOYSTICK LOOP
# =========================
async def joystick_loop():
    print("=== JOYSTICK DEBUG MODE ===")

    pygame.init()
    pygame.joystick.init()

    joystick_count = pygame.joystick.get_count()
    print(f"[JOYSTICK] Count detected: {joystick_count}")

    if joystick_count == 0:
        print("[ERROR] No joystick detected")
        while True:
            await asyncio.sleep(1)

    joy = pygame.joystick.Joystick(0)
    joy.init()

    print(f"[JOYSTICK] Name: {joy.get_name()}")
    print(f"[JOYSTICK] Axes: {joy.get_numaxes()}")
    print(f"[JOYSTICK] Buttons: {joy.get_numbuttons()}")

    while True:
        pygame.event.pump()

        axes = [joy.get_axis(i) for i in range(joy.get_numaxes())]
        buttons = [joy.get_button(i) for i in range(joy.get_numbuttons())]

        print("---- CONTROLLER STATE ----")
        for i, v in enumerate(axes):
            print(f"Axis {i}: {v:.3f}")

        for i, b in enumerate(buttons):
            if b:
                print(f"Button {i}: PRESSED")

        print("--------------------------\n")

        await asyncio.sleep(0.2)


# =========================
# MAIN
# =========================
async def main():
    async with websockets.serve(ws_handler, "0.0.0.0", WEBSOCKET_PORT):
        await asyncio.gather(
            udp_sensor_loop(),
            joystick_loop(),
        )


if __name__ == "__main__":
    asyncio.run(main())
