# coding: utf-8
"""
Configure window for server connection.
"""
from PyQt5 import QtWidgets, QtGui

from ui.mini_window_ui import Ui_new_server_window

class MiniWindow(QtWidgets.QWidget):
    def __init__(self, data, father_app, current_info, parent=None):
        super(MiniWindow, self).__init__()
        self.data = data
        self.current_info = current_info
        self.father = father_app
        self.ui = Ui_new_server_window()
        self.ui.setupUi(self)
        self.ui.port.setValidator(QtGui.QIntValidator())
        self.change_info()
        self.center()
        self.ui.close.clicked.connect(self.close)
        self.ui.create_server.clicked.connect(self.create)

    def change_info(self):
        '''
        用于更新窗口默认的信息栏
        '''
        if self.current_info is not None:
            self.ui.Server_Name.setText(self.current_info[3])
            self.ui.URL.setText(self.current_info[0])
            self.ui.port.setText(str(self.current_info[1]))
            if self.current_info[2]:
                self.ui.kiss_decoder_enable.nextCheckState()

    def create(self):
        name = self.ui.Server_Name.text()
        address = self.ui.URL.text()
        port = self.ui.port.text()
        kiss_enable = self.ui.kiss_decoder_enable.isChecked()
        if self.check_vaild(name, address, port):
            self.data.create(str(name), str(address), int(port), kiss_enable)
            self.father.add_to_list(name)
            self.close()  # shut the window
        else:
            QtWidgets.QMessageBox.information(self, "Warning",
                                          "Check your input!!!")

    # 移动到屏幕中心
    def center(self):
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(int((screen.width() - size.width()) / 2),
                  int((screen.height() - size.height()) / 2))

    def check_vaild(self, name, address, port):
        is_vaild = False
        if port != '':
            port = int(port)
            name = str(name)
            address = str(address)
            if port >= 1000 and port <= 65535:
                if name != '' and address != '':
                    is_vaild = True
        # 检查是否重复的服务器名字
        if name in self.data.show_all_names():
            QtWidgets.QMessageBox.information(
                self, "Warning", "The server name must be different !")
            is_vaild = False
        return is_vaild

