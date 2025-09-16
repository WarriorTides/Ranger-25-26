from PyQt6.QtCore import QObject, pyqtSignal
import random
import time
import threading

class SensorClient(QObject):
    data_received = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

    def start(self):
        def run():
            while True:
                data = {
                    "humidity": round(random.uniform(40,60),1),
                    "current": round(random.uniform(0,5),1)
                }
                self.data_received.emit(data)
                time.sleep(0.1)
        threading.Thread(target=run, daemon=True).start()
