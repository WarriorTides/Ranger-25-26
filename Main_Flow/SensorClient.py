# SensorClient.py
import threading
import json
import websocket  # this is from the "websocket-client" package
from PyQt6.QtCore import QObject, pyqtSignal


class SensorClient(QObject):
    data_received = pyqtSignal(dict)

<<<<<<< HEAD:Main_Flow/SensorClient.py
    def __init__(self, ws_url="ws://192.168.2.10:8765"):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None
        self.connected = False
        self.running = True  # ← ADDED: Track if client should keep running

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.data_received.emit(data)
        except Exception as e:
            print(f"Message parse error: {e}")

    def on_open(self, ws):
        self.connected = True
        print("Sensor WebSocket connected")

    def on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        print("Sensor WebSocket disconnected")
=======
    def __init__(self, ws_url="ws://192.168.1.103:8765"):
        super().__init__()
        self.ws_url = ws_url
>>>>>>> 8847c960a9c8050c2d558a2b7e65d68712b5d4d4:GUI/SensorClient.py

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

<<<<<<< HEAD:Main_Flow/SensorClient.py
    def send(self, data: dict):
        if self.ws and self.connected:
            try:
                self.ws.send(json.dumps(data))
                print(f"Sent: {data}")
            except Exception as e:
                print(f"Send error: {e}")
        else:
            print("WebSocket not connected. Cannot send data.")
    
    # ← ADDED: stop() method
    def stop(self):
        """Stop the sensor client and close WebSocket connection"""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        print("Sensor client stopped")
=======
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
>>>>>>> 8847c960a9c8050c2d558a2b7e65d68712b5d4d4:GUI/SensorClient.py
