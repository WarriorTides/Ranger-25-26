from PyQt6.QtCore import QThread, pyqtSignal
import time

class ClawThread(QThread):
    status_updated = pyqtSignal(str)  

    def __init__(self, claw_name="Claw 1"):
        super().__init__()
        self.running = True
        self.claw_name = claw_name
        self.status = "Closed"

    def run(self):
        while self.running:
            time.sleep(0.5)  
            self.status = "Open" if self.status == "Closed" else "Closed"
            self.status_updated.emit(self.status)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()
