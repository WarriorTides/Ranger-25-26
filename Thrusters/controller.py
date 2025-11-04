import socket
import pygame
import time

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

MAX_POWER = 0.3


def map_thruster(value, MAX_POWER):
    return int((value * MAX_POWER) * 400 + 1500)


def parse_thruster_control(controlData):
    controlString = "c"
    xythrusters = {
        "OFR": controlData["surge"] - controlData["yaw"] - controlData["sway"],
        "OFL": -1 * (controlData["surge"] + controlData["yaw"] + controlData["sway"]),
        "OBR": controlData["surge"] - controlData["yaw"] + controlData["sway"],
        "OBL": -1 * (controlData["surge"] + controlData["yaw"] - controlData["sway"]),
    }
    zthrusters = {
        "IFL": controlData["heave"] - controlData["roll"] + controlData["pitch"],
        "IBL": -1 * (controlData["heave"] - controlData["roll"] - controlData["pitch"]),
        "IBR": controlData["heave"] + controlData["roll"] - controlData["pitch"],
        "IFR": -1 * controlData["heave"] + controlData["roll"] + controlData["pitch"],
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


# UDP Setup
UDP_IP = "192.168.1.151"  # Arduino IP
UDP_PORT = 8888
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Joystick setup
pygame.init()
pygame.joystick.init()
if pygame.joystick.get_count() == 0:
    print("No joystick detected!")
    exit(1)

joystick = pygame.joystick.Joystick(0)
joystick.init()
axes = [0.0] * joystick.get_numaxes()
buttons = [0] * joystick.get_numbuttons()
CTRL_DEADZONES = [0.1] * len(axes)  # adjust deadzone if needed

print("Joystick ready. Sending UDP thruster commands...")

# Main loop
try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYAXISMOTION:
                axes[event.axis] = event.value
            elif event.type == pygame.JOYBUTTONDOWN:
                buttons[event.button] = 1
            elif event.type == pygame.JOYBUTTONUP:
                buttons[event.button] = 0

        # Apply deadzones
        for i in range(len(axes)):
            if abs(axes[i]) < CTRL_DEADZONES[i]:
                axes[i] = 0.0
            axes[i] = round(axes[i], 2)

        sway = -axes[2]  # right stick left/right
        heave = -axes[3]  # right stick up/down

        if buttons[0] == 0:  # x button not pressed
            surge = axes[1]  # left stick up/down
            yaw = -axes[0]   # left stick left/right
            roll = 0
            pitch = 0
        else:  # x button pressed
            surge = 0
            yaw = 0
            roll = -axes[0]
            pitch = axes[1]

        controlData = {
            "surge": surge,
            "sway": sway,
            "heave": heave,
            "yaw": yaw,
            "roll": roll,
            "pitch": pitch,
        }

        command = parse_thruster_control(controlData)

        # Send via UDP
        sock.sendto(command.encode(), (UDP_IP, UDP_PORT))
        print("Sent:", command)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting...")
finally:
    pygame.quit()
    sock.close()
