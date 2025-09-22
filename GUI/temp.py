import websocket

ws = websocket.WebSocket()
ws.connect("ws://localhost:8765")
ws.send("hello server")
print(ws.recv())
ws.close()
