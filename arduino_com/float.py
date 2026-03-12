



import re
import time
from collections import deque

import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# -----------------------------
# SETTINGS
# -----------------------------
PORT = "/dev/tty.usbserial-02PDC2ZB"     # CHANGE THIS (see notes below)
BAUD = 115200
WINDOW_SECONDS = 120              # show last N seconds on screen
READ_TIMEOUT_S = 0.05

# Matches your receiver line:
# Pressure: 1013.25 mbar | Depth: 0.12 m | Temp: 23.45 C | t=123456 ms
LINE_RE = re.compile(
    r"Pressure:\s*([0-9.+-]+)\s*mbar\s*\|\s*Depth:\s*([0-9.+-]+)\s*m\s*\|\s*Temp:\s*([0-9.+-]+)\s*C\s*\|\s*t=\s*(\d+)\s*ms",
    re.IGNORECASE
)

# -----------------------------
# SERIAL
# -----------------------------
ser = serial.Serial(PORT, BAUD, timeout=READ_TIMEOUT_S)

# -----------------------------
# DATA BUFFERS (ring)
# -----------------------------
t0_wall = time.time()

t = deque()
temp = deque()
press = deque()
depth = deque()

def trim_old(now_s: float):
    while t and (now_s - t[0]) > WINDOW_SECONDS:
        t.popleft()
        temp.popleft()
        press.popleft()
        depth.popleft()

# -----------------------------
# PLOT SETUP
# -----------------------------
plt.ion()
fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

axT, axP, axD = axes

(lineT,) = axT.plot([], [])
(lineP,) = axP.plot([], [])
(lineD,) = axD.plot([], [])

axT.set_ylabel("Temp (°C)")
axP.set_ylabel("Pressure (mbar)")
axD.set_ylabel("Depth (m)")
axD.set_xlabel("Time (s)")

axT.grid(True)
axP.grid(True)
axD.grid(True)

fig.suptitle("MS5837 Live Telemetry")

def update(_frame):
    # Read as many lines as are available quickly
    while True:
        try:
            raw = ser.readline()
        except serial.SerialException:
            break

        if not raw:
            break

        try:
            line = raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            continue

        m = LINE_RE.search(line)
        if not m:
            continue

        p_mbar = float(m.group(1))
        d_m = float(m.group(2))
        temp_c = float(m.group(3))
        t_ms = int(m.group(4))

        # Use sender-provided time if you want absolute consistency:
        # now_s = t_ms / 1000.0
        # Or use wall time since script start (works even if sender restarts):
        now_s = time.time() - t0_wall

        t.append(now_s)
        press.append(p_mbar)
        depth.append(d_m)
        temp.append(temp_c)

    if not t:
        return lineT, lineP, lineD

    now_s = t[-1]
    trim_old(now_s)

    # Update line data
    lineT.set_data(t, temp)
    lineP.set_data(t, press)
    lineD.set_data(t, depth)

    # Autoscale x to sliding window
    xmin = max(0.0, now_s - WINDOW_SECONDS)
    xmax = max(WINDOW_SECONDS, now_s)
    axD.set_xlim(xmin, xmax)

    # Autoscale y nicely (per axis)
    axT.relim(); axT.autoscale_view(scalex=False, scaley=True)
    axP.relim(); axP.autoscale_view(scalex=False, scaley=True)
    axD.relim(); axD.autoscale_view(scalex=False, scaley=True)

    return lineT, lineP, lineD

ani = FuncAnimation(fig, update, interval=100, blit=False)
plt.show()

try:
    while plt.fignum_exists(fig.number):
        plt.pause(0.1)
finally:
    ser.close()