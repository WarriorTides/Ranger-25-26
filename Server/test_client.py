import websocket
import json
import threading

def on_message(ws, message):
    print("Received:", message)

def on_open(ws):
    print("Connected!")
    ws.send(json.dumps({"test": "hello"}))

ws = websocket.WebSocketApp("ws://localhost:8080",
                            on_message=on_message,
                            on_open=on_open)

threading.Thread(target=ws.run_forever, daemon=True).start()

input("Press Enter to exit...")
