import sys
from PyQt5 import QtWidgets
from Qt.MainWindow import MainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt


if __name__ == "__main__":
    # 1. Enabling Global Scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) 

    # 2. Non-Integer Scaling Adaptation
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 4.
    app = QtWidgets.QApplication(sys.argv)

    # 3. Font Rendering Hinting Adaptation
    font = QFont()
    font.setStyleStrategy(QFont.PreferAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    QApplication.setFont(font)

    myapp = MainWindow()
    myapp.show()
    sys.exit(app.exec_())
