import socket
import pygame


class ControlThread:

    def __init__(self, arduino_ip="192.168.1.151", arduino_port=8888):
        self.arduino_ip = arduino_ip
        self.arduino_port = arduino_port
        self.running = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        pygame.display.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            print("[Control] WARNING: No joystick detected — control disabled.")
            self.joystick_present = False
            self.joystick = None
        else:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.joystick_present = True
            print(f"[Control] Joystick: {self.joystick.get_name()}")

        self.angleClaw1 = 0
        self.angleClaw1Rot = 0
        self.angleClaw2 = 0
        self.angleClaw2Rot = 0
        self.INCREMENT = 30

        self.mapping = sorted([
            {"name": "OFR", "index": 6},
            {"name": "OFL", "index": 4},
            {"name": "OBR", "index": 2},
            {"name": "OBL", "index": 3},
            {"name": "IFL", "index": 5},
            {"name": "IBL", "index": 0},
            {"name": "IBR", "index": 1},
            {"name": "IFR", "index": 7},
        ], key=lambda x: x["index"])

        self.MAX_POWER = 0.4
        self.DEADZONE = 0.1

        self.axes = [0.0] * (self.joystick.get_numaxes()
                             if self.joystick_present else 8)
        self.buttons = [0] * (self.joystick.get_numbuttons()
                              if self.joystick_present else 16)

        self._last_thruster_command = None

    def process_events(self):
        """Call from main thread via QTimer (macOS pygame requirement)."""
        if not self.joystick_present:
            return

        try:
            for event in pygame.event.get():
                if event.type == pygame.JOYAXISMOTION:
                    if event.axis < len(self.axes):
                        self.axes[event.axis] = event.value
                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.button < len(self.buttons):
                        self.buttons[event.button] = 1
                    self._handle_claw_button(event.button)
                elif event.type == pygame.JOYBUTTONUP:
                    if event.button < len(self.buttons):
                        self.buttons[event.button] = 0
        except SystemError as e:
            print(f"[Control] pygame event error (recoverable): {e}")
            return

        self._handle_thrusters()

    def stop(self):
        self.running = False
        try:
            neutral = self._build_command(
                {"surge": 0, "sway": 0, "heave": 0,
                 "yaw": 0, "roll": 0, "pitch": 0}
            )
            self._send(neutral)
        except Exception:
            pass
        pygame.joystick.quit()
        pygame.display.quit()
        self.sock.close()
        print("[Control] Stopped")

    def _dz(self, v: float) -> float:
        return 0.0 if abs(v) < self.DEADZONE else round(v, 3)

    def _handle_claw_button(self, button: int):
        commands = {
            # Face buttons — claw 1
            3:  (lambda: self.angleClaw1 != 180,    "oc1",  "angleClaw1",    +self.INCREMENT),
            0:  (lambda: self.angleClaw1 != 0,      "cc1",  "angleClaw1",    -self.INCREMENT),
            2:  (lambda: self.angleClaw1Rot != 180, "rc1",  "angleClaw1Rot", +self.INCREMENT),
            1:  (lambda: self.angleClaw1Rot != 0,   "urc1", "angleClaw1Rot", -self.INCREMENT),
            # D-pad (reported as buttons on this controller) — claw 2
            # dpad up
            11: (lambda: self.angleClaw2 != 180,    "oc2",  "angleClaw2",    +self.INCREMENT),
            # dpad down
            12: (lambda: self.angleClaw2 != 0,      "cc2",  "angleClaw2",    -self.INCREMENT),
            # dpad left
            13: (lambda: self.angleClaw2Rot != 180, "rc2",  "angleClaw2Rot", +self.INCREMENT),
            # dpad right
            14: (lambda: self.angleClaw2Rot != 0,   "urc2", "angleClaw2Rot", -self.INCREMENT),
        }

        if button not in commands:
            return

        condition_fn, message, attr, delta = commands[button]
        if condition_fn():
            setattr(self, attr, getattr(self, attr) + delta)
            self._send(message)
            print(f"[Control] {message}: {attr}={getattr(self, attr)}")

    def _handle_thrusters(self):
        axes = [self._dz(a) for a in self.axes]

        def ax(i): return axes[i] if i < len(axes) else 0.0

        sway = -ax(2)
        HEAVE_UP_GAIN = 1.25

        heave = ax(3)
        if heave > 0:
            heave *= HEAVE_UP_GAIN

        x_held = len(self.buttons) > 0 and self.buttons[0] == 1
        if not x_held:
            surge = -ax(0)
            yaw = -ax(1)
            roll = pitch = 0.0
        else:
            surge = yaw = 0.0
            roll = -ax(0)
            pitch = ax(1)

        ctrl = {"surge": surge, "sway": sway, "heave": heave,
                "yaw": yaw,     "roll": roll,  "pitch": pitch}

        all_zero = all(v == 0.0 for v in ctrl.values())

        if all_zero:
            if self._last_thruster_command != "neutral":
                self._send(self._build_command(
                    {"surge": 0, "sway": 0, "heave": 0,
                     "yaw": 0,   "roll": 0, "pitch": 0}
                ))
                self._last_thruster_command = "neutral"
            return

        command = self._build_command(ctrl)
        if command != self._last_thruster_command:
            self._send(command)
            self._last_thruster_command = command

    def _build_command(self, ctrl: dict) -> str:
        xy = {
            "OFR": ctrl["surge"] - ctrl["yaw"] - ctrl["sway"],
            "OFL": ctrl["surge"] + ctrl["yaw"] + ctrl["sway"],
            "OBR": ctrl["surge"] - ctrl["yaw"] + ctrl["sway"],
            "OBL": ctrl["surge"] + ctrl["yaw"] - ctrl["sway"],
        }
        z = {
            "IFL":  (ctrl["heave"] - ctrl["roll"] - ctrl["pitch"]),
            "IBL": -(ctrl["heave"] + ctrl["roll"] + ctrl["pitch"]),
            "IBR":  (ctrl["heave"] + ctrl["roll"] + ctrl["pitch"]),
            "IFR": -(ctrl["heave"] - ctrl["roll"] - ctrl["pitch"]),
        }

        max_xy = max(abs(v) for v in xy.values())
        if max_xy > 1:
            xy = {k: v / max_xy for k, v in xy.items()}

        max_z = max(abs(v) for v in z.values())
        if max_z > 1:
            z = {k: v / max_z for k, v in z.items()}

        combined = {**xy, **z}
        values = [self._to_pwm(combined[t["name"]]) for t in self.mapping]
        return "c," + ",".join(str(v) for v in values) + ",0,0"

    def _to_pwm(self, value: float) -> int:
        return int(value * self.MAX_POWER * 400 + 1500)

    def _send(self, message: str):
        try:
            self.sock.sendto(
                message.encode(), (self.arduino_ip, self.arduino_port)
            )
        except Exception as e:
            print(f"[Control] UDP send error: {e}")
