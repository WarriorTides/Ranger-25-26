import threading
import json
import websocket  # from the "websocket-client" package
from PyQt6.QtCore import QObject, pyqtSignal


class SensorClient(QObject):
    data_received = pyqtSignal(dict)

    def __init__(self, ws_url="ws://192.168.2.10:8765"):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None
        self.connected = False
        self.running = True

    def send(self, data: dict):
        if self.ws and self.connected:
            try:
                self.ws.send(json.dumps(data))
                print(f"[SensorClient] Sent: {data}")
            except Exception as e:
                print(f"[SensorClient] Send error: {e}")
        else:
            print("[SensorClient] WebSocket not connected. Cannot send data.")

    def stop(self):
        """Stop the sensor client and close WebSocket connection"""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                print(f"[SensorClient] Close error: {e}")
        print("[SensorClient] Sensor client stopped")

    def start(self):
        def run():
            def on_message(ws, message):
                print("[SensorClient] RAW MESSAGE:", message)
                try:
                    data = json.loads(message)
                    self.data_received.emit(data)
                except Exception as e:
                    print("[SensorClient] JSON ERROR:", e)

            def on_open(ws):
                self.connected = True
                print("[SensorClient] Connected to WebSocket server")

            def on_close(ws, code, msg):
                self.connected = False
                print("[SensorClient] WebSocket closed", code, msg)

            def on_error(ws, error):
                print("[SensorClient] WebSocket error:", error)

            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_open=on_open,
                on_close=on_close,
                on_error=on_error,
            )

            # The library blocks here; run_forever handles the loop
            self.ws.run_forever()

        threading.Thread(target=run, daemon=True).start()
