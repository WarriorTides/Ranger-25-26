import threading
import pygame
import socket
import time
from pygame.locals import *


class ControlThread(threading.Thread):
    """
    Handles both thruster control and claw control from a single joystick.
    Runs in a separate thread to avoid blocking the GUI.
    """

    def __init__(self, arduino_ip="192.168.1.151", arduino_port=8888):
        super().__init__(daemon=True)
        self.arduino_ip = arduino_ip
        self.arduino_port = arduino_port
        self.running = True

        # UDP socket for sending commands to Arduino
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Initialize joystick
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            print("WARNING: No joystick detected! Control disabled.")
            self.joystick_present = False
            self.joystick = None
        else:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.joystick_present = True
            print(f"Joystick connected: {self.joystick.get_name()}")

        # Claw state tracking
        self.angleClaw1 = 0
        self.angleClaw1Rot = 0
        self.angleClaw2 = 0
        self.angleClaw2Rot = 0
        self.INCREMENT = 30

        # Thruster mapping
        self.mapping = [
            {"name": "OFR", "index": 6},
            {"name": "OFL", "index": 4},
            {"name": "OBR", "index": 2},
            {"name": "OBL", "index": 3},
            {"name": "IFL", "index": 5},
            {"name": "IBL", "index": 0},
            {"name": "IBR", "index": 1},
            {"name": "IFR", "index": 7},
        ]
        self.mapping = sorted(self.mapping, key=lambda x: x["index"])
        self.MAX_POWER = 0.3

        # Control state
        self.axes = []
        self.buttons = []
        if self.joystick_present:
            self.axes = [0.0] * self.joystick.get_numaxes()
            self.buttons = [0] * self.joystick.get_numbuttons()

        self.CTRL_DEADZONES = [0.1] * len(self.axes)

    def run(self):
        """Main thread loop - processes joystick input and sends commands"""
        print("Control thread started")

        while self.running:
            if not self.joystick_present:
                time.sleep(0.1)
                continue

            # Process all pygame events
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False

                elif event.type == JOYAXISMOTION:
                    self.axes[event.axis] = event.value

                elif event.type == JOYBUTTONDOWN:
                    self.buttons[event.button] = 1
                    self.handle_claw_button(event.button)

                elif event.type == JOYBUTTONUP:
                    self.buttons[event.button] = 0

            # Handle continuous thruster control
            self.handle_thrusters()

            time.sleep(0.02)  # 50Hz update rate

        print("Control thread stopped")

    def handle_claw_button(self, button):
        """Handle claw control button presses"""

        # Claw 1 controls
        if button == 3 and self.angleClaw1 != 180:  # Triangle - Open claw1
            message = "oc1"
            self.angleClaw1 += self.INCREMENT
            self.sock.sendto(message.encode(),
                             (self.arduino_ip, self.arduino_port))
            print(f"Claw1 open (triangle): angle {self.angleClaw1}")

        elif button == 0 and self.angleClaw1 != 0:  # X - Close claw1
            message = "cc1"
            self.angleClaw1 -= self.INCREMENT
            self.sock.sendto(message.encode(),
                             (self.arduino_ip, self.arduino_port))
            print(f"Claw1 close (X): angle {self.angleClaw1}")

        elif button == 2 and self.angleClaw1Rot != 180:  # Square - Rotate claw1
            message = "rc1"
            self.angleClaw1Rot += self.INCREMENT
            self.sock.sendto(message.encode(),
                             (self.arduino_ip, self.arduino_port))
            print(f"Claw1 rotate (square): angle {self.angleClaw1Rot}")

        elif button == 1 and self.angleClaw1Rot != 0:  # Circle - Unrotate claw1
            message = "urc1"
            self.angleClaw1Rot -= self.INCREMENT
            self.sock.sendto(message.encode(),
                             (self.arduino_ip, self.arduino_port))
            print(f"Claw1 unrotate (circle): angle {self.angleClaw1Rot}")

        # Claw 2 controls
        elif button == 11 and self.angleClaw2 != 180:  # Up arrow - Open claw2
            message = "oc2"
            self.angleClaw2 += self.INCREMENT
            self.sock.sendto(message.encode(),
                             (self.arduino_ip, self.arduino_port))
            print(f"Claw2 open (up): angle {self.angleClaw2}")

        elif button == 12 and self.angleClaw2 != 0:  # Down arrow - Close claw2
            message = "cc2"
            self.angleClaw2 -= self.INCREMENT
            self.sock.sendto(message.encode(),
                             (self.arduino_ip, self.arduino_port))
            print(f"Claw2 close (down): angle {self.angleClaw2}")

        elif button == 13 and self.angleClaw2Rot != 180:  # Left arrow - Rotate claw2
            message = "rc2"
            self.angleClaw2Rot += self.INCREMENT
            self.sock.sendto(message.encode(),
                             (self.arduino_ip, self.arduino_port))
            print(f"Claw2 rotate (left): angle {self.angleClaw2Rot}")

        elif button == 14 and self.angleClaw2Rot != 0:  # Right arrow - Unrotate claw2
            message = "urc2"
            self.angleClaw2Rot -= self.INCREMENT
            self.sock.sendto(message.encode(),
                             (self.arduino_ip, self.arduino_port))
            print(f"Claw2 unrotate (right): angle {self.angleClaw2Rot}")

    def handle_thrusters(self):
        """Process joystick axes and send thruster commands"""

        # Apply deadzones to all axes
        for i in range(len(self.axes)):
            if abs(self.axes[i]) < self.CTRL_DEADZONES[i]:
                self.axes[i] = 0.0
            self.axes[i] = round(self.axes[i], 2)

        # Read control inputs
        # Right stick left/right
        sway = -self.axes[2] if len(self.axes) > 2 else 0
        # Right stick up/down
        heave = -self.axes[3] if len(self.axes) > 3 else 0

        # Check if X button (button 0) is pressed for pitch/roll mode
        # X button not pressed
        if len(self.buttons) > 0 and self.buttons[0] == 0:
            surge = self.axes[1] if len(
                self.axes) > 1 else 0  # Left stick up/down
            # Left stick left/right
            yaw = -self.axes[0] if len(self.axes) > 0 else 0
            roll = 0
            pitch = 0
        else:  # X button pressed - pitch/roll mode
            surge = 0
            yaw = 0
            roll = -self.axes[0] if len(self.axes) > 0 else 0
            pitch = self.axes[1] if len(self.axes) > 1 else 0

        # Build control data
        controlData = {
            "surge": surge,
            "sway": sway,
            "heave": heave,
            "yaw": yaw,
            "roll": roll,
            "pitch": pitch,
        }

        # Generate thruster command
        command = self.parse_thruster_control(controlData)

        # Send via UDP
        self.sock.sendto(command.encode(),
                         (self.arduino_ip, self.arduino_port))

    def map_thruster(self, value, MAX_POWER):
        """Map a thruster value (-1 to 1) to PWM range"""
        return int((value * MAX_POWER) * 400 + 1500)

    def parse_thruster_control(self, controlData):
        """Convert control inputs to thruster command string"""
        controlString = "c"

        # Calculate XY plane thrusters
        xythrusters = {
            "OFR": controlData["surge"] - controlData["yaw"] - controlData["sway"],
            "OFL": -1 * (controlData["surge"] + controlData["yaw"] + controlData["sway"]),
            "OBR": controlData["surge"] - controlData["yaw"] + controlData["sway"],
            "OBL": -1 * (controlData["surge"] + controlData["yaw"] - controlData["sway"]),
        }

        # Calculate Z plane thrusters
        zthrusters = {
            "IFL": controlData["heave"] - controlData["roll"] + controlData["pitch"],
            "IBL": -1 * (controlData["heave"] - controlData["roll"] - controlData["pitch"]),
            "IBR": controlData["heave"] + controlData["roll"] - controlData["pitch"],
            "IFR": -1 * controlData["heave"] + controlData["roll"] + controlData["pitch"],
        }

        # Normalize XY thrusters
        max_xy = max(abs(v) for v in xythrusters.values())
        if max_xy > 1:
            for k in xythrusters:
                xythrusters[k] /= max_xy

        # Normalize Z thrusters
        max_z = max(abs(v) for v in zthrusters.values())
        if max_z > 1:
            for k in zthrusters:
                zthrusters[k] /= max_z

        # Combine all thrusters
        combined = {**xythrusters, **zthrusters}

        # Build control array based on mapping
        control_array = [combined[item["name"]] for item in self.mapping]

        # Build command string
        for val in control_array:
            controlString += "," + str(self.map_thruster(val, self.MAX_POWER))

        controlString += ",0,0"

        return controlString

    def stop(self):
        """Stop the control thread"""
        self.running = False
        if self.joystick:
            pygame.quit()
        self.sock.close()
