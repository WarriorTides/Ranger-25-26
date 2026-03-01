import threading
import json
import time
import websocket
from PyQt6.QtCore import QObject, pyqtSignal


class SensorClient(QObject):
    data_received = pyqtSignal(dict)

    RECONNECT_DELAY_BASE = 1.0
    RECONNECT_DELAY_MAX = 10.0

    def __init__(self, ws_url="ws://localhost:8765"):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None
        self.connected = False
        self.running = True
        self._reconnect_delay = self.RECONNECT_DELAY_BASE

    def start(self):
        threading.Thread(
            target=self._run_loop, daemon=True, name="SensorClientThread"
        ).start()

    def stop(self):
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        print("[SensorClient] Stopped")

    def send(self, data: dict):
        if self.ws and self.connected:
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                print(f"[SensorClient] Send error: {e}")

    # ── Private ──────────────────────────────────────────────────────────

    def _run_loop(self):
        while self.running:
            print(f"[SensorClient] Connecting to {self.ws_url}…")
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_message=self._on_message,
                    on_open=self._on_open,
                    on_close=self._on_close,
                    on_error=self._on_error,
                )
                self.ws.run_forever()
            except Exception as e:
                print(f"[SensorClient] Connection exception: {e}")

            if not self.running:
                break

            print(
                f"[SensorClient] Reconnecting in {self._reconnect_delay:.1f}s…")
            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(
                self._reconnect_delay * 2, self.RECONNECT_DELAY_MAX
            )

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            self._reconnect_delay = self.RECONNECT_DELAY_BASE
            self.data_received.emit(data)
        except Exception as e:
            print(f"[SensorClient] JSON parse error: {e}")

    def _on_open(self, ws):
        self.connected = True
        self._reconnect_delay = self.RECONNECT_DELAY_BASE
        print("[SensorClient] Connected")

    def _on_close(self, ws, code, msg):
        self.connected = False
        print(f"[SensorClient] Disconnected (code={code})")

    def _on_error(self, ws, error):
        print(f"[SensorClient] Error: {error}")
