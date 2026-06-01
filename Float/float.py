import tkinter as tk
from tkinter import scrolledtext
import serial
import time
import threading
import re

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

PORT = "/dev/cu.usbserial-02LWALEW"
BAUD = 115200

pattern = re.compile(
    r"Time:\s*([0-9.]+).*Pressure:\s*([0-9.]+).*Depth:\s*([0-9.]+)"
)
fin_pattern = re.compile(
    r"FINISHED FIRST ROUND at Time:\s*([0-9.]+)"
)
test_ok_pattern = re.compile(r"TEST_OK:\s*(.+)")


class FloatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MATE Float Mission Station")
        self.root.geometry("1450x900")
        self.root.minsize(1100, 700)
        self.root.configure(bg="#1f1f1f")

        self.time_data = []
        self.depth_data = []
        self.pressure_data = []
        self.finish_time = None

        self.tx_time_data = []
        self.tx_depth_data = []

        self.ser = None
        self.running = True
        self.packet_count = 0
        self.in_transmit = False

        self.btn_idle = "#4a4a4a"
        self.btn_busy = "#f39c12"
        self.btn_done = "#2ecc71"
        self.bg_panel = "#2a2a2a"
        self.bg_console = "#111111"
        self.fg_text = "white"
        self.fg_subtle = "#cfcfcf"

        self.live_autoscroll = True
        self.tx_autoscroll = True

        self.build_layout()
        self.connect_serial()
        self.start_serial_thread()
        self.update_plot()

    def build_layout(self):
        self.root.grid_rowconfigure(0, weight=3)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)

        # ── Sidebar ──────────────────────────────
        self.sidebar = tk.Frame(self.root, bg=self.bg_panel, width=260)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew",
                          padx=(12, 6), pady=(12, 6))
        self.sidebar.grid_propagate(False)

        tk.Label(self.sidebar, text="Mission Panel",
                 bg=self.bg_panel, fg=self.fg_text,
                 font=("Arial", 18, "bold"), anchor="w"
                 ).pack(fill="x", padx=16, pady=(16, 10))

        self.status_label = tk.Label(
            self.sidebar, text="Serial: connecting...",
            bg=self.bg_panel, fg="#ffd166",
            font=("Arial", 12, "bold"), anchor="w")
        self.status_label.pack(fill="x", padx=16, pady=(0, 10))

        self.packet_label = tk.Label(
            self.sidebar, text="Packets received: 0",
            bg=self.bg_panel, fg=self.fg_subtle,
            font=("Arial", 12), anchor="w")
        self.packet_label.pack(fill="x", padx=16, pady=(0, 10))

        info_box = tk.Frame(self.sidebar, bg="#343434")
        info_box.pack(fill="x", padx=16, pady=(0, 12))
        tk.Label(info_box,
                 text="1. TEST     — verify connection\n"
                      "2. PRIME    — extend actuator 40s\n"
                      "3. UP-DOWN  — retract 45s→wait 5s→extend 45s\n"
                      "4. START    — begin 1 profile\n"
                      "5. STOP     — emergency halt\n"
                      "6. TRANSMIT — replay stored data",
                 bg="#343434", fg=self.fg_subtle,
                 justify="left", anchor="nw",
                 font=("Arial", 11), padx=12, pady=12
                 ).pack(fill="both")

        def btn(text, color, cmd):
            b = tk.Button(self.sidebar, text=text,
                          font=("Arial", 13, "bold"),
                          bg=color, fg="black",
                          relief="flat", bd=0,
                          padx=12, pady=16,
                          command=cmd)
            b.pack(fill="x", padx=16, pady=(0, 6))
            return b

        self.test_btn = btn("TEST",     "#e67e22", self.send_test)
        self.prime_btn = btn("PRIME",    "#1a6fa8", self.send_prime)
        self.updown_btn = btn("UP-DOWN",  "#16a085", self.send_updown)
        self.start_btn = btn("START",    self.btn_idle, self.send_start)
        self.stop_btn = btn("STOP",     "#b0b0b0", self.send_stop)
        self.transmit_btn = btn("TRANSMIT", "#8e44ad", self.send_transmit)

        # ── Graph ────────────────────────────────
        self.main_panel = tk.Frame(self.root, bg=self.bg_panel)
        self.main_panel.grid(row=0, column=1, sticky="nsew",
                             padx=(6, 12), pady=(12, 6))
        self.main_panel.grid_rowconfigure(1, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        topbar = tk.Frame(self.main_panel, bg=self.bg_panel)
        topbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        topbar.grid_columnconfigure(0, weight=1)

        tk.Label(topbar, text="Depth vs Time",
                 bg=self.bg_panel, fg="white",
                 font=("Arial", 18, "bold")
                 ).grid(row=0, column=0, sticky="w")

        self.last_value_label = tk.Label(
            topbar, text="No data yet",
            bg=self.bg_panel, fg=self.fg_subtle,
            font=("Arial", 11))
        self.last_value_label.grid(row=0, column=1, sticky="e")

        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.figure.patch.set_facecolor("white")

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.main_panel)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew",
                                         padx=14, pady=(0, 14))

        # ── Drag sash ─────────────────────────────
        self.sash = tk.Frame(self.root, bg="#555555",
                             height=6, cursor="sb_v_double_arrow")
        self.sash.grid(row=1, column=1, sticky="ew", padx=(6, 12))
        self.sash.bind("<B1-Motion>", self._on_sash_drag)

        # ── Split console ─────────────────────────
        self.console_panel = tk.Frame(self.root, bg=self.bg_panel)
        self.console_panel.grid(row=2, column=1, sticky="nsew",
                                padx=(6, 12), pady=(0, 12))
        self.console_panel.grid_columnconfigure(0, weight=1)
        self.console_panel.grid_columnconfigure(2, weight=1)
        self.console_panel.grid_rowconfigure(1, weight=1)

        # Left header
        left_hdr = tk.Frame(self.console_panel, bg=self.bg_panel)
        left_hdr.grid(row=0, column=0, sticky="ew", padx=(8, 0), pady=(6, 2))
        tk.Label(left_hdr, text="Live Serial Log",
                 bg=self.bg_panel, fg="white",
                 font=("Arial", 11, "bold")).pack(side="left")
        self.live_scroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left_hdr, text="Auto-scroll",
                       variable=self.live_scroll_var,
                       bg=self.bg_panel, fg=self.fg_subtle,
                       selectcolor=self.bg_panel,
                       font=("Arial", 9),
                       command=lambda: setattr(
                           self, 'live_autoscroll',
                           self.live_scroll_var.get())
                       ).pack(side="right")

        tk.Frame(self.console_panel, bg="#555555", width=2
                 ).grid(row=0, column=1, rowspan=2,
                        sticky="ns", padx=4)

        # Right header
        right_hdr = tk.Frame(self.console_panel, bg=self.bg_panel)
        right_hdr.grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=(6, 2))
        tk.Label(right_hdr, text="Transmitted Data",
                 bg=self.bg_panel, fg="#8e44ad",
                 font=("Arial", 11, "bold")).pack(side="left")
        self.tx_scroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(right_hdr, text="Auto-scroll",
                       variable=self.tx_scroll_var,
                       bg=self.bg_panel, fg=self.fg_subtle,
                       selectcolor=self.bg_panel,
                       font=("Arial", 9),
                       command=lambda: setattr(
                           self, 'tx_autoscroll',
                           self.tx_scroll_var.get())
                       ).pack(side="right")

        self.console = scrolledtext.ScrolledText(
            self.console_panel,
            bg=self.bg_console, fg="#e8e8e8",
            insertbackground="white", font=("Menlo", 10),
            relief="flat", bd=0, wrap=tk.WORD)
        self.console.grid(row=1, column=0, sticky="nsew",
                          padx=(8, 0), pady=(0, 8))
        self.console.tag_config("green",  foreground="#2ecc71")
        self.console.tag_config("red",    foreground="#e74c3c")
        self.console.tag_config("orange", foreground="#f39c12")

        self.tx_console = scrolledtext.ScrolledText(
            self.console_panel,
            bg="#0d0d1a", fg="#c8a0f0",
            insertbackground="white", font=("Menlo", 10),
            relief="flat", bd=0, wrap=tk.WORD)
        self.tx_console.grid(row=1, column=2, sticky="nsew",
                             padx=(0, 8), pady=(0, 8))

    def _on_sash_drag(self, event):
        total = self.root.winfo_height()
        y = event.y_root - self.root.winfo_rooty()
        ratio = max(0.2, min(0.8, y / total))
        self.root.grid_rowconfigure(0, weight=int(ratio * 100))
        self.root.grid_rowconfigure(2, weight=int((1 - ratio) * 100))

    def connect_serial(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=0.2)
            time.sleep(1)
            self.ser.reset_input_buffer()
            self.status_label.config(
                text=f"Serial: connected\n{PORT}", fg="#7CFC8A")
            self.log(f"Connected to {PORT} at {BAUD} baud")
        except Exception as e:
            self.status_label.config(
                text="Serial: connection failed", fg="#ff6b6b")
            self.log(f"ERROR: {e}", "red")

    def start_serial_thread(self):
        threading.Thread(target=self.serial_loop, daemon=True).start()

    def serial_loop(self):
        while self.running:
            if self.ser is None:
                time.sleep(0.1)
                continue
            try:
                if self.ser.in_waiting == 0:
                    time.sleep(0.01)
                    continue
                line = self.ser.readline().decode(
                    "utf-8", errors="ignore").strip()
                if not line:
                    continue

                tok = test_ok_pattern.search(line)
                if tok:
                    msg = tok.group(1)
                    self.root.after(0, self.log,
                                    f"✅ GOOD — Received: {msg}", "green")
                    self.root.after(0, self._test_pass)
                    continue

                fin = fin_pattern.search(line)
                if fin:
                    ft = float(fin.group(1))
                    self.finish_time = ft
                    self.root.after(0, self.log,
                                    f"✅ FINISHED FIRST ROUND at {ft:.2f}s", "green")
                    continue

                self.root.after(0, self.log, line)

                m = pattern.search(line)
                if m:
                    t = float(m.group(1))
                    p = float(m.group(2))
                    d = float(m.group(3))

                    if self.in_transmit:
                        self.tx_time_data.append(t)
                        self.tx_depth_data.append(d)
                        self.root.after(0, self.log_tx,
                                        f"Time: {t:.2f}s  Depth: {d:.3f}m  "
                                        f"Pressure: {p:.3f}kPa")
                    else:
                        self.time_data.append(t)
                        self.pressure_data.append(p)
                        self.depth_data.append(d)
                        self.packet_count += 1
                        self.root.after(0, self.update_stats, t, p, d)

            except Exception as e:
                self.root.after(0, self.log, f"ERROR: {e}", "red")
                time.sleep(0.1)

    def _test_pass(self):
        self.test_btn.config(bg="#2ecc71")

    def _test_fail(self):
        self.test_btn.config(bg="#e74c3c")
        self.log("❌ No response from float — check connection", "red")

    def update_stats(self, t, p, d):
        self.packet_label.config(
            text=f"Packets received: {self.packet_count}")
        self.last_value_label.config(
            text=f"Time: {t:.2f}s   Pressure: {p:.3f} kPa   Depth: {d:.3f} m")

    def send_test(self):
        if self.ser is None:
            self.log("ERROR: not connected", "red")
            return
        self.test_btn.config(bg=self.btn_busy)
        ts = time.strftime("%H:%M:%S")
        msg = f"Test message {ts}"
        try:
            self.ser.write(f"TEST:{msg}\n".encode())
            self.ser.flush()
            self.log(f"Sent: {msg}", "orange")
            self.root.after(3000, self._check_test_timeout)
        except Exception as e:
            self.log(f"ERROR: {e}", "red")

    def _check_test_timeout(self):
        if self.test_btn.cget("bg") == self.btn_busy:
            self._test_fail()

    def send_prime(self):
        self._send("PRIME", self.prime_btn, "#2ecc71")

    def send_updown(self):
        self.log("UP-DOWN: retracting 45s → wait 5s → extending 45s", "orange")
        self._send("UPDOWN", self.updown_btn, "#2ecc71")

    def send_start(self):
        self.time_data.clear()
        self.depth_data.clear()
        self.pressure_data.clear()
        self.finish_time = None
        self.packet_count = 0
        self.in_transmit = False
        self._send("START", self.start_btn, "#2ecc71")

    def send_stop(self):
        self.in_transmit = False
        self._send("STOP", self.stop_btn, "#8fd19e")

    def send_transmit(self):
        self.tx_time_data.clear()
        self.tx_depth_data.clear()
        self.tx_console.delete("1.0", tk.END)
        self.in_transmit = True
        self._send("TRANSMIT", self.transmit_btn, "#2ecc71")

    def _send(self, cmd, btn, done_color):
        if self.ser is None:
            self.log("ERROR: not connected", "red")
            return
        try:
            btn.config(bg=self.btn_busy)
            self.ser.write((cmd + "\n").encode())
            self.ser.flush()
            self.log(f"Sent: {cmd}")
            self.root.after(800, lambda: btn.config(bg=done_color))
        except Exception as e:
            self.log(f"ERROR: {e}", "red")

    def log(self, msg, tag=None):
        ts = time.strftime("%H:%M:%S")
        self.console.insert(tk.END, f"[{ts}] {msg}\n", tag or "")
        if self.live_autoscroll:
            self.console.see(tk.END)

    def log_tx(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.tx_console.insert(tk.END, f"[{ts}] {msg}\n")
        if self.tx_autoscroll:
            self.tx_console.see(tk.END)

    def update_plot(self):
        self.ax.clear()
        self.ax.set_title("Depth vs Time")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Depth (m)")
        self.ax.grid(True, alpha=0.3)

        t_data = self.tx_time_data if self.in_transmit else self.time_data
        d_data = self.tx_depth_data if self.in_transmit else self.depth_data
        color = "#e74c3c" if self.in_transmit else "#2980b9"

        if t_data and d_data:
            self.ax.plot(t_data, d_data, linewidth=2, color=color)
            self.ax.axhline(y=2.017, color="red",   linestyle="--",
                            linewidth=1, label="Deep (2.017m)")
            self.ax.axhline(y=0.40,  color="green", linestyle="--",
                            linewidth=1, label="Shallow (0.40m)")
            if self.finish_time is not None:
                self.ax.axvline(x=self.finish_time, color="#2ecc71",
                                linestyle="-", linewidth=2,
                                label=f"✅ Finished ({self.finish_time:.1f}s)")
            self.ax.legend(fontsize=9)

            xmin, xmax = min(t_data), max(t_data)
            ymin, ymax = min(d_data), max(d_data)
            if xmin == xmax:
                xmax = xmin + 1
            if ymin == ymax:
                ymax = ymin + 0.1
            xpad = max((xmax - xmin) * 0.05, 0.5)
            ypad = max((ymax - ymin) * 0.10, 0.05)
            self.ax.set_xlim(xmin - xpad, xmax + xpad)
            self.ax.set_ylim(max(0, ymin - ypad), ymax + ypad)
        else:
            self.ax.text(0.5, 0.5, "Waiting for telemetry...",
                         ha="center", va="center",
                         transform=self.ax.transAxes, fontsize=14)

        self.figure.tight_layout()
        self.canvas.draw()
        self.root.after(300, self.update_plot)

    def on_close(self):
        self.running = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FloatGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
