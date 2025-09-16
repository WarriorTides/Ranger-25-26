from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget
from PyQt6.QtCore import QSize, Qt
import sys

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.showMaximized()
        self.aspect_ratio = 16.0 / 9.0
        size_policy = self.centralWidget().sizePolicy()
        size_policy.setHorizontalPolicy(Qt.QSizePolicy.Policy.Expanding)
        size_policy.setVerticalPolicy(Qt.QSizePolicy.Policy.Expanding)
        self.centralWidget().setSizePolicy(size_policy)


    def resizeEvent(self, event):
        new_size = event.size()
        w = new_size.width()
        h = new_size.height()
        if (w / self.aspect_ratio) > h:
            new_w = int(h * self.aspect_ratio)
            new_h = h
        else:
            new_w = w
            new_h = int(w / self.aspect_ratio)

        x = int((w - new_w) / 2)
        y = int((h - new_h) / 2)
        
        self.centralWidget().setGeometry(x, y, new_w, new_h)
        super().resizeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())