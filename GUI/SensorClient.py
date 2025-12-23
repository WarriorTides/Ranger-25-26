# SensorClient.py
import threading
import json
import websocket  # this is from the "websocket-client" package
from PyQt6.QtCore import QObject, pyqtSignal


class SensorClient(QObject):
    data_received = pyqtSignal(dict)

    def __init__(self, ws_url="ws://192.168.1.103:8765"):
        super().__init__()
        self.ws_url = ws_url

    def start(self):
        def run():
            def on_message(ws, message):
                print("[SensorClient] RAW MESSAGE:", message)  # DEBUG
                try:
                    data = json.loads(message)
                    print("[SensorClient] PARSED DATA:", data)   # DEBUG
                    self.data_received.emit(data)
                except Exception as e:
                    print("[SensorClient] JSON ERROR:", e)

            def on_open(ws):
                print("[SensorClient] Connected to WebSocket server")

            def on_close(ws, code, msg):
                print("[SensorClient] WebSocket closed", code, msg)

            def on_error(ws, error):
                print("[SensorClient] WebSocket error:", error)

            ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_open=on_open,
                on_close=on_close,
                on_error=on_error,
            )
            ws.run_forever()

        threading.Thread(target=run, daemon=True).start()
