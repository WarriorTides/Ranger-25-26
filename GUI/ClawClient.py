# ClawClient.py
import json
import threading
import websocket
from PyQt6.QtCore import QObject, pyqtSignal


class ClawClient(QObject):
    data_received = pyqtSignal(dict)

    def __init__(self, ws_url="ws://localhost:8770"):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.data_received.emit(data)
        except Exception as e:
            print("Parse error:", e)

    def _on_error(self, ws, error):
        print("WebSocket error:", error)

    def _on_close(self, ws, code, msg):
        print("WebSocket closed")

    def _on_open(self, ws):
        print("Claw WebSocket connected")

    def _run(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )
        self.ws.run_forever()
