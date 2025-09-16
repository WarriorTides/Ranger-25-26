import websocket
import threading
import json
from PyQt6.QtCore import QObject, pyqtSignal

class SensorClient(QObject):
    data_received = pyqtSignal(dict) 

    def __init__(self, ws_url="ws://<PI_IP>:8765"):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None
        self.connected = False

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.data_received.emit(data)
        except:
            pass

    def on_open(self, ws):
        self.connected = True
        print("Sensor WebSocket connected")

    def on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        print("Sensor WebSocket disconnected")

    def start(self):
        def run_ws():
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self.on_message,
                on_open=self.on_open,
                on_close=self.on_close
            )
            self.ws.run_forever()
        threading.Thread(target=run_ws, daemon=True).start()
