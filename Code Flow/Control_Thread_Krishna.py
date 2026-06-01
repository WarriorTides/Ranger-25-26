# import socket
# import pygame


# class ControlThread:

#     def __init__(self, arduino_ip="192.168.1.151", arduino_port=8888):
#         self.arduino_ip = arduino_ip
#         self.arduino_port = arduino_port
#         self.running = True

#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#         pygame.display.init()
#         pygame.joystick.init()

#         if pygame.joystick.get_count() == 0:
#             print("[Control] WARNING: No joystick detected — control disabled.")
#             self.joystick_present = False
#             self.joystick = None
#         else:
#             self.joystick = pygame.joystick.Joystick(0)
#             self.joystick.init()
#             self.joystick_present = True
#             print(f"[Control] Joystick: {self.joystick.get_name()}")

#         self.angleClaw1 = 0
#         self.angleClaw1Rot = 0
#         self.angleClaw2 = 0
#         self.angleClaw2Rot = 0
#         self.INCREMENT = 10

#         self.mapping = sorted([
#             {"name": "OFR", "index": 6},
#             {"name": "OFL", "index": 4},
#             {"name": "OBR", "index": 2},
#             {"name": "OBL", "index": 3},
#             {"name": "IFL", "index": 5},
#             {"name": "IBL", "index": 0},
#             {"name": "IBR", "index": 1},
#             {"name": "IFR", "index": 7},
#         ], key=lambda x: x["index"])

#         self.MAX_POWER = 0.5
#         self.DEADZONE = 0.1

#         self.axes = [0.0] * (self.joystick.get_numaxes()
#                              if self.joystick_present else 8)
#         self.buttons = [0] * (self.joystick.get_numbuttons()
#                               if self.joystick_present else 16)

#         self._last_thruster_command = None

#     def process_events(self):
#         """Call from main thread via QTimer (macOS pygame requirement)."""
#         if not self.joystick_present:
#             return

#         try:
#             for event in pygame.event.get():
#                 if event.type == pygame.JOYAXISMOTION:
#                     if event.axis < len(self.axes):
#                         self.axes[event.axis] = event.value
#                 elif event.type == pygame.JOYBUTTONDOWN:
#                     if event.button < len(self.buttons):
#                         self.buttons[event.button] = 1
#                     self._handle_claw_button(event.button)
#                 elif event.type == pygame.JOYBUTTONUP:
#                     if event.button < len(self.buttons):
#                         self.buttons[event.button] = 0
#         except SystemError as e:
#             print(f"[Control] pygame event error (recoverable): {e}")
#             return

#         self._handle_thrusters()

#     def stop(self):
#         self.running = False
#         try:
#             neutral = self._build_command(
#                 {"surge": 0, "sway": 0, "heave": 0,
#                  "yaw": 0, "roll": 0, "pitch": 0}
#             )
#             self._send(neutral)
#         except Exception:
#             pass
#         pygame.joystick.quit()
#         pygame.display.quit()
#         self.sock.close()
#         print("[Control] Stopped")

#     def _dz(self, v: float) -> float:
#         return 0.0 if abs(v) < self.DEADZONE else round(v, 3)

#     def _handle_claw_button(self, button: int):
#         commands = {
#             3:  (lambda: self.angleClaw1 < 180,    "oc1",  "angleClaw1",    +self.INCREMENT),
#             0:  (lambda: self.angleClaw1 > 0,      "cc1",  "angleClaw1",    -self.INCREMENT),
#             2:  (lambda: self.angleClaw1Rot < 180, "rc1",  "angleClaw1Rot", +self.INCREMENT),
#             1:  (lambda: self.angleClaw1Rot > 0,   "urc1", "angleClaw1Rot", -self.INCREMENT),

#             11: (lambda: self.angleClaw2 < 180,    "oc2",  "angleClaw2",    +self.INCREMENT),
#             12: (lambda: self.angleClaw2 > 0,      "cc2",  "angleClaw2",    -self.INCREMENT),
#             13: (lambda: self.angleClaw2Rot < 180, "rc2",  "angleClaw2Rot", +self.INCREMENT),
#             14: (lambda: self.angleClaw2Rot > 0,   "urc2", "angleClaw2Rot", -self.INCREMENT),
#         }

#         if button not in commands:
#             return

#         condition_fn, message, attr, delta = commands[button]

#         # If the movement is allowed:
#         if condition_fn():
#             new_val = getattr(self, attr) + delta

#             # if new_val < 0:
#             #     new_val = 0 
#             # if new_val > 180:
#             #     new_val = 180

#             setattr(self, attr, new_val)
#             self._send(message)
#             print(f"[Control] {message}: {attr}={new_val}")
        
#     def _handle_thrusters(self):
#         axes = [self._dz(a) for a in self.axes]

#         def ax(i): return axes[i] if i < len(axes) else 0.0

#         sway = -ax(2)
#         HEAVE_UP_GAIN = 1.25

#         heave = ax(3)
#         if heave > 0:
#             heave *= HEAVE_UP_GAIN

#         x_held = len(self.buttons) > 0 and self.buttons[0] == 1
#         if not x_held:
#             surge = -ax(0)
#             yaw = -ax(1)
#             roll = pitch = 0.0
#         else:
#             surge = yaw = 0.0
#             roll = -ax(0)
#             pitch = ax(1)

#         ctrl = {"surge": surge, "sway": sway, "heave": heave,
#                 "yaw": yaw,     "roll": roll,  "pitch": pitch}

#         all_zero = all(v == 0.0 for v in ctrl.values())

#         if all_zero:
#             if self._last_thruster_command != "neutral":
#                 self._send(self._build_command(
#                     {"surge": 0, "sway": 0, "heave": 0,
#                      "yaw": 0,   "roll": 0, "pitch": 0}
#                 ))
#                 self._last_thruster_command = "neutral"
#             return

#         command = self._build_command(ctrl)
#         if command != self._last_thruster_command:
#             self._send(command)
#             self._last_thruster_command = command

#     def _build_command(self, ctrl: dict) -> str:
#         xy = {
#             "OFR": (-ctrl["surge"] + ctrl["yaw"] + ctrl["sway"]),
#             "OFL": -1*(ctrl["surge"] + ctrl["yaw"] - ctrl["sway"]),
#             "OBR": -1*(-ctrl["surge"] + ctrl["yaw"] - ctrl["sway"]),
#             "OBL": ctrl["surge"] + ctrl["yaw"] + ctrl["sway"],
             
#         }
#         z = {
#             "IFL":  (-ctrl["heave"] + ctrl["roll"] - ctrl["pitch"]),
#             "IBL": -(-ctrl["heave"] - ctrl["roll"] + ctrl["pitch"]),
#             "IBR":  (-ctrl["heave"] + ctrl["roll"] + ctrl["pitch"]),
#             "IFR": -(-ctrl["heave"] - ctrl["roll"] - ctrl["pitch"]),
#         }

#         max_xy = max(abs(v) for v in xy.values())
#         if max_xy > 1:
#             xy = {k: v / max_xy for k, v in xy.items()}

#         max_z = max(abs(v) for v in z.values())
#         if max_z > 1:
#             z = {k: v / max_z for k, v in z.items()}

#         combined = {**xy, **z}
#         values = [self._to_pwm(combined[t["name"]]) for t in self.mapping]
#         return "c," + ",".join(str(v) for v in values) + ",0,0"

#     def _to_pwm(self, value: float) -> int:
#         return int(value * self.MAX_POWER * 400 + 1500)

#     def _send(self, message: str):
#         try:
#             self.sock.sendto(
#                 message.encode(), (self.arduino_ip, self.arduino_port)
#             )
#         except Exception as e:
#             print(f"[Control] UDP send error: {e}")




import socket
import pygame


class ControlThread:
    def __init__(self, arduino_ip="192.168.1.151", arduino_port=8888):
        self.arduino_ip = arduino_ip
        self.arduino_port = arduino_port
        self.running = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        pygame.init()
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

        # This order must match Arduino thruster index order
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

        # Higher peak power, but protected by ramping + total thrust limiting
        self.MAX_POWER = 0.8 #0.7

        # Limits total motor demand before PWM conversion
        # Lower = safer current draw, higher = stronger movement
        self.MAX_TOTAL_THRUST = 4.0

        # Max PWM change per control update
        # Lower = smoother / safer, higher = more responsive
        self.RAMP_STEP = 8

        self.DEADZONE = 0.1

        self.axes = [0.0] * (
            self.joystick.get_numaxes() if self.joystick_present else 8
        )
        self.buttons = [0] * (
            self.joystick.get_numbuttons() if self.joystick_present else 16
        )

        self._last_thruster_command = None
        self.last_pwm_values = [1500] * 8

    def process_events(self):
        """Call from main thread via QTimer."""
        if not self.joystick_present:
            return

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

            elif event.type == pygame.JOYHATMOTION:
                self._handle_dpad(event.value)

        self._handle_thrusters()

    
    def stop(self):
        self.running = False

        try:
            neutral = "c,1500,1500,1500,1500,1500,1500,1500,1500,0,0"
            self.last_pwm_values = [1500] * 8
            self._send(neutral)
        except Exception:
            pass

        pygame.quit()
        self.sock.close()
        print("[Control] Stopped")

    def _dz(self, v: float) -> float:
        return 0.0 if abs(v) < self.DEADZONE else round(v, 3)

    def _handle_dpad(self, value: tuple):
        x, y = value

        if y == 1:
            if self.angleClaw2 != 180:
                self.angleClaw2 += self.INCREMENT
                self._send("oc2")
                print(f"[Control] oc2: angleClaw2={self.angleClaw2}")

        elif y == -1:
            if self.angleClaw2 != 0:
                self.angleClaw2 -= self.INCREMENT
                self._send("cc2")
                print(f"[Control] cc2: angleClaw2={self.angleClaw2}")

        elif x == -1:
            if self.angleClaw2Rot != 180:
                self.angleClaw2Rot += self.INCREMENT
                self._send("rc2")
                print(f"[Control] rc2: angleClaw2Rot={self.angleClaw2Rot}")

        elif x == 1:
            if self.angleClaw2Rot != 0:
                self.angleClaw2Rot -= self.INCREMENT
                self._send("urc2")
                print(f"[Control] urc2: angleClaw2Rot={self.angleClaw2Rot}")

    def _handle_claw_button(self, button: int):
        commands = {
            3:  (
                lambda: self.angleClaw1 != 180,
                "oc1",
                "angleClaw1",
                +self.INCREMENT,
            ),
            0:  (
                lambda: self.angleClaw1 != 0,
                "cc1",
                "angleClaw1",
                -self.INCREMENT,
            ),
            2:  (
                lambda: self.angleClaw1Rot != 180,
                "rc1",
                "angleClaw1Rot",
                +self.INCREMENT,
            ),
            1:  (
                lambda: self.angleClaw1Rot != 0,
                "urc1",
                "angleClaw1Rot",
                -self.INCREMENT,
            ),
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

        def ax(i):
            return axes[i] if i < len(axes) else 0.0

        sway = -ax(2)

        HEAVE_UP_GAIN = 1.25
        heave = ax(3)

        if heave > 0:
            heave *= HEAVE_UP_GAIN

        x_held = len(self.buttons) > 0 and self.buttons[0] == 1

        if not x_held:
            surge = -ax(0)
            yaw = -ax(1)
            roll = 0.0
            pitch = 0.0
        else:
            surge = 0.0
            yaw = 0.0
            roll = -ax(0)
            pitch = ax(1)

        ctrl = {
            "surge": surge,
            "sway": sway,
            "heave": heave,
            "yaw": yaw,
            "roll": roll,
            "pitch": pitch,
        }

        ctrl = self._apply_priority_scaling(ctrl)

        all_zero = all(v == 0.0 for v in ctrl.values())

        if all_zero:
            neutral = "c,1500,1500,1500,1500,1500,1500,1500,1500,0,0"

            if self._last_thruster_command != neutral:
                self.last_pwm_values = [1500] * 8
                self._send(neutral)
                self._last_thruster_command = neutral

            return


        command = self._build_command(ctrl)

        if command != self._last_thruster_command:
            self._send(command)
            self._last_thruster_command = command

    def _apply_priority_scaling(self, ctrl: dict) -> dict:
        """
        Reduces lower-priority axes when multiple motions are commanded.
        This helps keep the ROV under the 25A limit while preserving useful motion.
        """

        ctrl = dict(ctrl)

        surge_mag = abs(ctrl["surge"])
        sway_mag = abs(ctrl["sway"])
        heave_mag = abs(ctrl["heave"])
        yaw_mag = abs(ctrl["yaw"])
        roll_mag = abs(ctrl["roll"])
        pitch_mag = abs(ctrl["pitch"])

        # If vertical movement is being commanded, preserve heave
        # and reduce sideways/rotation demand.
        if heave_mag > 0.2:
            ctrl["sway"] *= 0.65
            ctrl["yaw"] *= 0.75
            ctrl["roll"] *= 0.75
            ctrl["pitch"] *= 0.75

        # If forward/back movement is being commanded, preserve surge
        # and reduce sideways strafe slightly.
        if surge_mag > 0.2:
            ctrl["sway"] *= 0.75

        # If too many axes are active, reduce low-priority axes more.
        active_axes = sum(
            1
            for v in [
                surge_mag,
                sway_mag,
                heave_mag,
                yaw_mag,
                roll_mag,
                pitch_mag,
            ]
            if v > 0.15
        )

        if active_axes >= 3:
            ctrl["sway"] *= 0.7
            ctrl["yaw"] *= 0.8
            ctrl["roll"] *= 0.8
            ctrl["pitch"] *= 0.8

        return ctrl

    def _build_command(self, ctrl: dict) -> str:
        xy = {
            "OFR": (-ctrl["surge"] + ctrl["yaw"] + ctrl["sway"]),
            "OFL": -1*(ctrl["surge"] + ctrl["yaw"] - ctrl["sway"]),
            "OBR": -1*(-ctrl["surge"] + ctrl["yaw"] - ctrl["sway"]),
            "OBL": ctrl["surge"] + ctrl["yaw"] + ctrl["sway"],
        }

        z = {
            "IFL": (-ctrl["heave"] + ctrl["roll"] - ctrl["pitch"]),
            "IBL": -1*(-ctrl["heave"] - ctrl["roll"] + ctrl["pitch"]),
            "IBR": (-ctrl["heave"] + ctrl["roll"] + ctrl["pitch"]),
            "IFR": -1*(-ctrl["heave"] - ctrl["roll"] - ctrl["pitch"]),
        }

        max_xy = max(abs(v) for v in xy.values())
        if max_xy > 1:
            xy = {k: v / max_xy for k, v in xy.items()}

        max_z = max(abs(v) for v in z.values())
        if max_z > 1:
            z = {k: v / max_z for k, v in z.items()}

        combined = {**xy, **z}

        raw_values = [combined[t["name"]] for t in self.mapping]

        # Total thrust limiter
        total_thrust = sum(abs(v) for v in raw_values)

        if total_thrust > self.MAX_TOTAL_THRUST:
            scale = self.MAX_TOTAL_THRUST / total_thrust
            raw_values = [v * scale for v in raw_values]
        else:
            scale = 1.0

        target_pwm_values = [self._to_pwm(v) for v in raw_values]

        ramped_pwm_values = [
            self._ramp_pwm(self.last_pwm_values[i], target_pwm_values[i])
            for i in range(8)
        ]

        self.last_pwm_values = ramped_pwm_values

        # # Optional debug
        # print(
        #     "[PowerLimit]",
        #     f"total={total_thrust:.2f}",
        #     f"scale={scale:.2f}",
        #     f"pwm={ramped_pwm_values}",
        # )

        return "c," + ",".join(str(v) for v in ramped_pwm_values) + ",0,0"

    def _to_pwm(self, value: float) -> int:
        pwm = int(value * self.MAX_POWER * 400 + 1500)
        return max(1100, min(1900, pwm))

    def _ramp_pwm(self, current: int, target: int) -> int:
        if target > current:
            return min(current + self.RAMP_STEP, target)
        if target < current:
            return max(current - self.RAMP_STEP, target)
        return current

    def _send(self, message: str):
        try:
            self.sock.sendto(
                message.encode(), (self.arduino_ip, self.arduino_port)
            )
        except Exception as e:
            print(f"[Control] UDP send error: {e}")