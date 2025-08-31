from PyQt6.QtCore import QThread, pyqtSignal
import random
import time

class SensorThread(QThread):
    data_updated = pyqtSignal(dict)  

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while self.running:
            data = {
                "humidity": round(random.uniform(40, 60), 1),
                "depth": round(random.uniform(0, 100), 1),
                "temperature": round(random.uniform(20, 30), 1),
                "leak": round(random.uniform(0, 5), 1)  
            }
            self.data_updated.emit(data)
            time.sleep(1)  

    def stop(self):
        self.running = False
        self.quit()
        self.wait()
